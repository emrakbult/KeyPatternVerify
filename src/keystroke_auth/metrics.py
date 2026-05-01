from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ErrorRates:
    threshold: float
    far: float
    frr: float
    eer: float


def far_frr(
    genuine_scores: np.ndarray,
    impostor_scores: np.ndarray,
    threshold: float,
) -> tuple[float, float]:
    genuine_scores = np.asarray(genuine_scores, dtype=float)
    impostor_scores = np.asarray(impostor_scores, dtype=float)

    if genuine_scores.size == 0:
        raise ValueError("At least one genuine score is required.")
    if impostor_scores.size == 0:
        raise ValueError("At least one impostor score is required.")

    false_acceptance_rate = float(np.mean(impostor_scores <= threshold))
    false_rejection_rate = float(np.mean(genuine_scores > threshold))
    return false_acceptance_rate, false_rejection_rate


def equal_error_rate(
    genuine_scores: np.ndarray,
    impostor_scores: np.ndarray,
) -> ErrorRates:
    genuine_scores = np.asarray(genuine_scores, dtype=float)
    impostor_scores = np.asarray(impostor_scores, dtype=float)

    if genuine_scores.size == 0:
        raise ValueError("At least one genuine score is required.")
    if impostor_scores.size == 0:
        raise ValueError("At least one impostor score is required.")

    finite_scores = np.concatenate([genuine_scores, impostor_scores])
    if not np.all(np.isfinite(finite_scores)):
        raise ValueError("Scores must be finite numbers.")

    unique_scores = np.unique(finite_scores)
    thresholds = np.concatenate(
        [
            np.array([unique_scores[0] - 1e-12]),
            unique_scores,
            np.array([unique_scores[-1] + 1e-12]),
        ]
    )

    rates = np.array([far_frr(genuine_scores, impostor_scores, t) for t in thresholds])
    differences = np.abs(rates[:, 0] - rates[:, 1])
    best_index = int(np.argmin(differences))
    far = float(rates[best_index, 0])
    frr = float(rates[best_index, 1])
    return ErrorRates(
        threshold=float(thresholds[best_index]),
        far=far,
        frr=frr,
        eer=(far + frr) / 2.0,
    )
