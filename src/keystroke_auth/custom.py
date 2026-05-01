from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .models import KNNAnomalyModel, KNNConfig

MIN_ENROLLMENT_SAMPLES = 3


def validate_password(password: str) -> str:
    password = password.strip()
    if not password:
        raise ValueError("Password is required.")
    if len(password) > 64:
        raise ValueError("Password must be 64 characters or fewer.")
    if any(character in password for character in "\r\n\t"):
        raise ValueError("Password cannot contain tab or newline characters.")
    return password


def normalize_profile_name(name: str) -> str:
    name = " ".join(name.strip().split())
    if not name:
        raise ValueError("Profile name is required.")
    if len(name) > 64:
        raise ValueError("Profile name must be 64 characters or fewer.")
    return name


def key_token(key: str, index: int) -> str:
    return f"{index + 1:02d}.u{ord(key):04x}"


def feature_columns_for_password(password: str) -> list[str]:
    columns: list[str] = []
    keys = list(password)
    tokens = [key_token(key, index) for index, key in enumerate(keys)]

    columns.extend(f"H.{token}" for token in tokens)
    for previous, current in zip(tokens, tokens[1:]):
        columns.append(f"DD.{previous}.{current}")
        columns.append(f"UD.{previous}.{current}")
    return columns


def validate_sample(password: str, sample: list[dict[str, Any]]) -> list[dict[str, float | str]]:
    password = validate_password(password)
    if len(sample) != len(password):
        raise ValueError(
            f"Attempt must contain {len(password)} key events for the selected password."
        )

    validated: list[dict[str, float | str]] = []
    for index, expected_key in enumerate(password):
        event = sample[index]
        key = str(event.get("key", ""))
        if key != expected_key:
            raise ValueError(
                f"Key {index + 1} must be {expected_key!r}, got {key!r}."
            )

        press = float(event.get("press", math.nan))
        release = float(event.get("release", math.nan))
        if not math.isfinite(press) or not math.isfinite(release):
            raise ValueError("Key timings must be finite numbers.")
        if release < press:
            raise ValueError("Key release time cannot be before press time.")

        validated.append({"key": key, "press": press, "release": release})
    return validated


def custom_feature_vector(
    password: str,
    sample: list[dict[str, Any]],
) -> dict[str, float]:
    events = validate_sample(password, sample)
    keys = list(password)
    tokens = [key_token(key, index) for index, key in enumerate(keys)]

    vector: dict[str, float] = {}
    for token, event in zip(tokens, events):
        vector[f"H.{token}"] = float(event["release"]) - float(event["press"])

    for index, (previous, current) in enumerate(zip(tokens, tokens[1:])):
        previous_event = events[index]
        current_event = events[index + 1]
        vector[f"DD.{previous}.{current}"] = (
            float(current_event["press"]) - float(previous_event["press"])
        )
        vector[f"UD.{previous}.{current}"] = (
            float(current_event["press"]) - float(previous_event["release"])
        )
    return vector


def custom_matrix(
    password: str,
    samples: list[list[dict[str, Any]]],
) -> tuple[np.ndarray, list[str]]:
    columns = feature_columns_for_password(validate_password(password))
    rows = []
    for sample in samples:
        vector = custom_feature_vector(password, sample)
        rows.append([float(vector[column]) for column in columns])
    return np.asarray(rows, dtype=float), columns


def train_custom_model(
    profile: dict[str, Any],
    *,
    k: int = 3,
    operating_quantile: float = 0.95,
) -> tuple[KNNAnomalyModel, float, list[str], np.ndarray]:
    password = validate_password(str(profile["password"]))
    samples = profile.get("samples", [])
    if len(samples) < MIN_ENROLLMENT_SAMPLES:
        raise ValueError(
            f"At least {MIN_ENROLLMENT_SAMPLES} enrollment samples are required."
        )

    matrix, columns = custom_matrix(password, samples)
    model = KNNAnomalyModel(KNNConfig(n_neighbors=k)).fit(matrix)
    train_scores = model.score_samples(matrix)
    threshold = float(np.quantile(train_scores, operating_quantile))
    return model, threshold, columns, train_scores


def empty_store() -> dict[str, dict[str, Any]]:
    return {"profiles": {}}


def load_profile_store(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return empty_store()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Custom profile store is not valid JSON: {path}") from exc
    if not isinstance(loaded, dict) or not isinstance(loaded.get("profiles"), dict):
        raise ValueError(f"Custom profile store has an invalid shape: {path}")
    return loaded


def save_profile_store(path: Path, store: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(store, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def profile_metadata(name: str, profile: dict[str, Any]) -> dict[str, Any]:
    password = validate_password(str(profile["password"]))
    return {
        "name": name,
        "password": password,
        "sample_count": len(profile.get("samples", [])),
        "feature_count": len(feature_columns_for_password(password)),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }


def list_profiles(path: Path) -> list[dict[str, Any]]:
    store = load_profile_store(path)
    return [
        profile_metadata(name, profile)
        for name, profile in sorted(store["profiles"].items())
    ]


def get_profile(path: Path, name: str) -> dict[str, Any]:
    normalized_name = normalize_profile_name(name)
    store = load_profile_store(path)
    profile = store["profiles"].get(normalized_name)
    if profile is None:
        raise ValueError(f"Custom profile {normalized_name!r} was not found.")
    return profile


def save_profile(
    path: Path,
    *,
    name: str,
    password: str,
    samples: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    normalized_name = normalize_profile_name(name)
    password = validate_password(password)
    if len(samples) < MIN_ENROLLMENT_SAMPLES:
        raise ValueError(
            f"At least {MIN_ENROLLMENT_SAMPLES} enrollment samples are required."
        )

    validated_samples = [validate_sample(password, sample) for sample in samples]
    store = load_profile_store(path)
    now = datetime.now(timezone.utc).isoformat()
    previous = store["profiles"].get(normalized_name, {})
    store["profiles"][normalized_name] = {
        "password": password,
        "samples": validated_samples,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
    }
    save_profile_store(path, store)
    return profile_metadata(normalized_name, store["profiles"][normalized_name])


def delete_profile(path: Path, name: str) -> bool:
    normalized_name = normalize_profile_name(name)
    store = load_profile_store(path)
    existed = normalized_name in store["profiles"]
    if existed:
        del store["profiles"][normalized_name]
        save_profile_store(path, store)
    return existed
