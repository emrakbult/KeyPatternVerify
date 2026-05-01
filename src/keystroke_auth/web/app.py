from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from keystroke_auth.custom import (
    custom_feature_vector,
    delete_profile,
    get_profile,
    list_profiles,
    save_profile,
    train_custom_model,
)
from keystroke_auth.data import DEFAULT_DATA_PATH, load_dataset
from keystroke_auth.evaluation import (
    evaluate_all_subjects,
    summarize_results,
    train_authenticator,
)
from keystroke_auth.realtime import (
    EXPECTED_LABELS,
    PASSWORD_TEXT,
    feature_vector_from_events,
    stream_dataset_attempts,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = WEB_ROOT / "static"
INDEX_PATH = STATIC_ROOT / "index.html"
RESULTS_PATH = PROJECT_ROOT / "reports" / "knn_results.csv"
CUSTOM_PROFILES_PATH = PROJECT_ROOT / "models" / "custom_profiles.json"

app = FastAPI(title="KeyPatternVerify")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

_cached_frame: pd.DataFrame | None = None
_cached_dataset_mtime: float | None = None


class EvaluationRequest(BaseModel):
    feature_set: str = "all"
    k: int = Field(default=5, ge=1, le=50)
    train_count: int = Field(default=200, ge=1)
    impostor_count: int = Field(default=5, ge=1)
    operating_quantile: float = Field(default=0.95, ge=0.5, le=0.999)


class AuthRequest(BaseModel):
    subject: str
    feature_set: str = "all"
    k: int = Field(default=5, ge=1, le=50)
    threshold_source: Literal["eer", "train-quantile"] = "train-quantile"
    operating_quantile: float = Field(default=0.95, ge=0.5, le=0.999)
    press_times: dict[str, float]
    release_times: dict[str, float]


class SimulateRequest(BaseModel):
    subject: str
    feature_set: str = "all"
    k: int = Field(default=5, ge=1, le=50)
    threshold_source: Literal["eer", "train-quantile"] = "train-quantile"
    operating_quantile: float = Field(default=0.95, ge=0.5, le=0.999)
    attempts: int = Field(default=8, ge=1, le=50)
    include_impostors: bool = True


class CustomKeyEvent(BaseModel):
    key: str = Field(min_length=1, max_length=1)
    press: float
    release: float


class CustomEnrollRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)
    samples: list[list[CustomKeyEvent]] = Field(min_length=3, max_length=100)
    k: int = Field(default=3, ge=1, le=50)
    operating_quantile: float = Field(default=0.95, ge=0.5, le=0.999)


class CustomVerifyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    sample: list[CustomKeyEvent] = Field(min_length=1, max_length=64)
    k: int = Field(default=3, ge=1, le=50)
    operating_quantile: float = Field(default=0.95, ge=0.5, le=0.999)


def dataset_path() -> Path:
    return PROJECT_ROOT / DEFAULT_DATA_PATH


def load_frame() -> pd.DataFrame:
    global _cached_dataset_mtime, _cached_frame

    path = dataset_path()
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found at {path}. Run the download command first.",
        )

    mtime = path.stat().st_mtime
    if _cached_frame is None or _cached_dataset_mtime != mtime:
        _cached_frame = load_dataset(path)
        _cached_dataset_mtime = mtime
    return _cached_frame


def subject_sort_key(subject: str) -> tuple[int, str]:
    suffix = "".join(ch for ch in subject if ch.isdigit())
    return (int(suffix) if suffix else 0, subject)


def read_results() -> pd.DataFrame | None:
    if not RESULTS_PATH.exists():
        return None
    return pd.read_csv(RESULTS_PATH)


def compact_summary(results: pd.DataFrame | None) -> dict[str, float | int | None]:
    if results is None or results.empty:
        return {
            "subjects": None,
            "eer_mean": None,
            "far_at_eer_mean": None,
            "frr_at_eer_mean": None,
            "operating_far_mean": None,
            "operating_frr_mean": None,
        }
    summary = summarize_results(results)
    return {
        "subjects": int(summary["subjects"]),
        "eer_mean": summary["eer_mean"],
        "far_at_eer_mean": summary["far_at_eer_mean"],
        "frr_at_eer_mean": summary["frr_at_eer_mean"],
        "operating_far_mean": summary["operating_far_mean"],
        "operating_frr_mean": summary["operating_frr_mean"],
    }


def result_rows(results: pd.DataFrame | None) -> list[dict[str, float | str | int]]:
    if results is None or results.empty:
        return []
    rows = results.copy()
    rows["subject"] = rows["subject"].astype(str)
    rows = rows.sort_values(
        "subject",
        key=lambda series: series.map(subject_sort_key),
    )
    return rows.to_dict(orient="records")


def build_authenticator(request: AuthRequest | SimulateRequest):
    frame = load_frame()
    try:
        return train_authenticator(
            frame,
            request.subject,
            feature_set=request.feature_set,
            k=request.k,
            threshold_source=request.threshold_source,
            operating_quantile=request.operating_quantile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def event_sample(sample: list[CustomKeyEvent]) -> list[dict[str, float | str]]:
    return [event.model_dump() for event in sample]


def event_samples(
    samples: list[list[CustomKeyEvent]],
) -> list[list[dict[str, float | str]]]:
    return [event_sample(sample) for sample in samples]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_PATH)


@app.get("/api/status")
def status() -> dict[str, object]:
    frame = load_frame()
    results = read_results()
    subjects = sorted((str(subject) for subject in frame["subject"].unique()), key=subject_sort_key)
    return {
        "dataset": {
            "path": str(dataset_path()),
            "rows": int(len(frame)),
            "subjects": len(subjects),
            "password": PASSWORD_TEXT,
            "expected_labels": EXPECTED_LABELS,
        },
        "subjects": subjects,
        "results": {
            "path": str(RESULTS_PATH),
            "available": results is not None,
            "summary": compact_summary(results),
            "rows": result_rows(results),
        },
        "custom_profiles": {
            "path": str(CUSTOM_PROFILES_PATH),
            "profiles": list_profiles(CUSTOM_PROFILES_PATH),
        },
    }


@app.post("/api/evaluate")
def evaluate(request: EvaluationRequest) -> dict[str, object]:
    frame = load_frame()
    try:
        results = evaluate_all_subjects(
            frame,
            feature_set=request.feature_set,
            k=request.k,
            train_count=request.train_count,
            impostor_count=request.impostor_count,
            operating_quantile=request.operating_quantile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_PATH, index=False)
    return {
        "summary": compact_summary(results),
        "rows": result_rows(results),
        "path": str(RESULTS_PATH),
    }


@app.post("/api/authenticate")
def authenticate(request: AuthRequest) -> dict[str, object]:
    authenticator = build_authenticator(request)
    try:
        vector = feature_vector_from_events(
            request.press_times,
            request.release_times,
            authenticator.feature_columns,
        )
        score = authenticator.score_vector(vector)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    accepted = authenticator.predict_score(score)
    return {
        "subject": authenticator.subject,
        "accepted": accepted,
        "verdict": "ACCEPT" if accepted else "REJECT",
        "score": score,
        "threshold": authenticator.threshold,
        "threshold_source": authenticator.threshold_source,
        "feature_count": len(authenticator.feature_columns),
        "features": [
            {"name": column, "value": float(vector[column])}
            for column in authenticator.feature_columns
        ],
    }


@app.post("/api/simulate")
def simulate(request: SimulateRequest) -> dict[str, object]:
    authenticator = build_authenticator(request)
    decisions = stream_dataset_attempts(
        load_frame(),
        authenticator,
        attempts=request.attempts,
        include_impostors=request.include_impostors,
        delay=0.0,
    )
    return {
        "subject": authenticator.subject,
        "threshold": authenticator.threshold,
        "threshold_source": authenticator.threshold_source,
        "decisions": [asdict(decision) for decision in decisions],
    }


@app.get("/api/custom/profiles")
def custom_profiles() -> dict[str, object]:
    try:
        profiles = list_profiles(CUSTOM_PROFILES_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "path": str(CUSTOM_PROFILES_PATH),
        "profiles": profiles,
    }


@app.post("/api/custom/enroll")
def custom_enroll(request: CustomEnrollRequest) -> dict[str, object]:
    try:
        metadata = save_profile(
            CUSTOM_PROFILES_PATH,
            name=request.name,
            password=request.password,
            samples=event_samples(request.samples),
        )
        profile = get_profile(CUSTOM_PROFILES_PATH, metadata["name"])
        _, threshold, columns, train_scores = train_custom_model(
            profile,
            k=request.k,
            operating_quantile=request.operating_quantile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "profile": metadata,
        "threshold": threshold,
        "feature_count": len(columns),
        "train_score_mean": float(train_scores.mean()),
        "train_score_max": float(train_scores.max()),
    }


@app.post("/api/custom/verify")
def custom_verify(request: CustomVerifyRequest) -> dict[str, object]:
    try:
        profile = get_profile(CUSTOM_PROFILES_PATH, request.name)
        model, threshold, columns, _ = train_custom_model(
            profile,
            k=request.k,
            operating_quantile=request.operating_quantile,
        )
        vector = custom_feature_vector(profile["password"], event_sample(request.sample))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    matrix = [[float(vector[column]) for column in columns]]
    score = float(model.score_samples(matrix)[0])
    accepted = score <= threshold
    return {
        "profile": profile_metadata_response(request.name, profile),
        "accepted": accepted,
        "verdict": "ACCEPT" if accepted else "REJECT",
        "score": score,
        "threshold": threshold,
        "feature_count": len(columns),
        "features": [
            {"name": column, "value": float(vector[column])}
            for column in columns
        ],
    }


@app.delete("/api/custom/profiles/{profile_name}")
def custom_delete(profile_name: str) -> dict[str, object]:
    try:
        deleted = delete_profile(CUSTOM_PROFILES_PATH, profile_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom profile was not found.")
    return {"deleted": True, "profiles": list_profiles(CUSTOM_PROFILES_PATH)}


def profile_metadata_response(name: str, profile: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "password": profile["password"],
        "sample_count": len(profile.get("samples", [])),  # type: ignore[arg-type]
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }
