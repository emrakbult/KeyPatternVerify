from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .features import feature_matrix
from .metrics import equal_error_rate, far_frr
from .models import KNNAnomalyModel, KNNConfig


@dataclass(frozen=True)
class SubjectResult:
    subject: str
    n_train: int
    n_genuine_test: int
    n_impostor_test: int
    threshold_eer: float
    far_at_eer: float
    frr_at_eer: float
    eer: float
    operating_threshold: float
    operating_far: float
    operating_frr: float


@dataclass
class Authenticator:
    subject: str
    model: KNNAnomalyModel
    feature_columns: list[str]
    threshold: float
    threshold_source: str

    def score_frame(self, frame: pd.DataFrame) -> np.ndarray:
        matrix, _ = feature_matrix(frame, feature_columns=self.feature_columns)
        return self.model.score_samples(matrix)

    def score_vector(self, vector: dict[str, float]) -> float:
        missing = [column for column in self.feature_columns if column not in vector]
        if missing:
            raise ValueError(f"Vector is missing feature values: {missing}")
        matrix = np.array([[float(vector[column]) for column in self.feature_columns]])
        return float(self.model.score_samples(matrix)[0])

    def predict_score(self, score: float) -> bool:
        return score <= self.threshold


def split_subject_data(
    frame: pd.DataFrame,
    subject: str,
    *,
    train_count: int = 200,
    impostor_count: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subjects = set(frame["subject"].unique())
    if subject not in subjects:
        raise ValueError(f"Subject {subject!r} not found in dataset.")

    user_frame = frame[frame["subject"] == subject]
    if len(user_frame) <= train_count:
        raise ValueError(
            f"Subject {subject!r} has {len(user_frame)} rows, "
            f"but {train_count + 1} or more are required."
        )

    train_frame = user_frame.iloc[:train_count]
    genuine_test_frame = user_frame.iloc[train_count:]
    impostor_test_frame = (
        frame[frame["subject"] != subject]
        .groupby("subject", group_keys=False)
        .head(impostor_count)
    )
    return train_frame, genuine_test_frame, impostor_test_frame


def train_authenticator(
    frame: pd.DataFrame,
    subject: str,
    *,
    feature_set: str = "all",
    k: int = 5,
    train_count: int = 200,
    impostor_count: int = 5,
    threshold_source: str = "eer",
    operating_quantile: float = 0.95,
) -> Authenticator:
    train_frame, genuine_test_frame, impostor_test_frame = split_subject_data(
        frame,
        subject,
        train_count=train_count,
        impostor_count=impostor_count,
    )
    train_matrix, feature_columns = feature_matrix(train_frame, feature_set=feature_set)
    genuine_matrix, _ = feature_matrix(genuine_test_frame, feature_columns=feature_columns)
    impostor_matrix, _ = feature_matrix(impostor_test_frame, feature_columns=feature_columns)

    model = KNNAnomalyModel(KNNConfig(n_neighbors=k)).fit(train_matrix)
    genuine_scores = model.score_samples(genuine_matrix)
    impostor_scores = model.score_samples(impostor_matrix)
    train_scores = model.score_samples(train_matrix)

    threshold_source = threshold_source.lower()
    if threshold_source == "eer":
        threshold = equal_error_rate(genuine_scores, impostor_scores).threshold
    elif threshold_source == "train-quantile":
        threshold = float(np.quantile(train_scores, operating_quantile))
    else:
        raise ValueError("threshold_source must be 'eer' or 'train-quantile'.")

    return Authenticator(
        subject=subject,
        model=model,
        feature_columns=feature_columns,
        threshold=threshold,
        threshold_source=threshold_source,
    )


def evaluate_subject(
    frame: pd.DataFrame,
    subject: str,
    *,
    feature_set: str = "all",
    k: int = 5,
    train_count: int = 200,
    impostor_count: int = 5,
    operating_quantile: float = 0.95,
) -> SubjectResult:
    train_frame, genuine_test_frame, impostor_test_frame = split_subject_data(
        frame,
        subject,
        train_count=train_count,
        impostor_count=impostor_count,
    )
    train_matrix, feature_columns = feature_matrix(train_frame, feature_set=feature_set)
    genuine_matrix, _ = feature_matrix(genuine_test_frame, feature_columns=feature_columns)
    impostor_matrix, _ = feature_matrix(impostor_test_frame, feature_columns=feature_columns)

    model = KNNAnomalyModel(KNNConfig(n_neighbors=k)).fit(train_matrix)
    genuine_scores = model.score_samples(genuine_matrix)
    impostor_scores = model.score_samples(impostor_matrix)
    train_scores = model.score_samples(train_matrix)

    eer_rates = equal_error_rate(genuine_scores, impostor_scores)
    operating_threshold = float(np.quantile(train_scores, operating_quantile))
    operating_far, operating_frr = far_frr(
        genuine_scores,
        impostor_scores,
        operating_threshold,
    )

    return SubjectResult(
        subject=subject,
        n_train=len(train_frame),
        n_genuine_test=len(genuine_test_frame),
        n_impostor_test=len(impostor_test_frame),
        threshold_eer=eer_rates.threshold,
        far_at_eer=eer_rates.far,
        frr_at_eer=eer_rates.frr,
        eer=eer_rates.eer,
        operating_threshold=operating_threshold,
        operating_far=operating_far,
        operating_frr=operating_frr,
    )


def evaluate_all_subjects(
    frame: pd.DataFrame,
    *,
    feature_set: str = "all",
    k: int = 5,
    train_count: int = 200,
    impostor_count: int = 5,
    operating_quantile: float = 0.95,
) -> pd.DataFrame:
    rows = [
        asdict(
            evaluate_subject(
                frame,
                str(subject),
                feature_set=feature_set,
                k=k,
                train_count=train_count,
                impostor_count=impostor_count,
                operating_quantile=operating_quantile,
            )
        )
        for subject in sorted(frame["subject"].unique())
    ]
    return pd.DataFrame(rows)


def summarize_results(results: pd.DataFrame) -> dict[str, float]:
    return {
        "subjects": float(len(results)),
        "eer_mean": float(results["eer"].mean()),
        "eer_std": float(results["eer"].std(ddof=1)),
        "far_at_eer_mean": float(results["far_at_eer"].mean()),
        "frr_at_eer_mean": float(results["frr_at_eer"].mean()),
        "operating_far_mean": float(results["operating_far"].mean()),
        "operating_frr_mean": float(results["operating_frr"].mean()),
    }
