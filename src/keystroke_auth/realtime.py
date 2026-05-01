from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .evaluation import Authenticator
from .features import feature_matrix

EXPECTED_LABELS = [
    "period",
    "t",
    "i",
    "e",
    "five",
    "Shift.r",
    "o",
    "a",
    "n",
    "l",
    "Return",
]
PASSWORD_TEXT = ".tie5Roanl"


@dataclass(frozen=True)
class AttemptDecision:
    label: str
    score: float
    threshold: float
    accepted: bool


def stream_dataset_attempts(
    frame: pd.DataFrame,
    authenticator: Authenticator,
    *,
    attempts: int = 12,
    include_impostors: bool = True,
    delay: float = 0.0,
    sink: Callable[[AttemptDecision], None] | None = None,
) -> list[AttemptDecision]:
    user_rows = frame[frame["subject"] == authenticator.subject].iloc[200 : 200 + attempts]
    streams: list[tuple[str, pd.DataFrame]] = [("genuine", user_rows)]

    if include_impostors:
        impostor_rows = (
            frame[frame["subject"] != authenticator.subject]
            .groupby("subject", group_keys=False)
            .head(1)
            .head(attempts)
        )
        streams.append(("impostor", impostor_rows))

    decisions: list[AttemptDecision] = []
    for label, rows in streams:
        matrix, _ = feature_matrix(rows, feature_columns=authenticator.feature_columns)
        scores = authenticator.model.score_samples(matrix)
        for score in scores:
            decision = AttemptDecision(
                label=label,
                score=float(score),
                threshold=authenticator.threshold,
                accepted=authenticator.predict_score(float(score)),
            )
            decisions.append(decision)
            if sink is not None:
                sink(decision)
            if delay > 0:
                time.sleep(delay)
    return decisions


def feature_vector_from_events(
    press_times: dict[str, float],
    release_times: dict[str, float],
    feature_columns: list[str],
) -> dict[str, float]:
    vector: dict[str, float] = {}
    for label in EXPECTED_LABELS:
        if label not in press_times or label not in release_times:
            raise ValueError(f"Missing key timing for {label}.")

    for label in EXPECTED_LABELS:
        vector[f"H.{label}"] = release_times[label] - press_times[label]

    for previous, current in zip(EXPECTED_LABELS, EXPECTED_LABELS[1:]):
        vector[f"DD.{previous}.{current}"] = press_times[current] - press_times[previous]
        vector[f"UD.{previous}.{current}"] = press_times[current] - release_times[previous]

    missing = [column for column in feature_columns if column not in vector]
    if missing:
        raise ValueError(
            "Captured vector cannot provide these dataset features: "
            + ", ".join(missing)
        )
    return vector
