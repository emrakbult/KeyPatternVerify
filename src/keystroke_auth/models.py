from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class KNNConfig:
    n_neighbors: int = 5
    metric: str = "euclidean"
    standardize: bool = True


class KNNAnomalyModel:
    """One-class k-NN model where higher scores mean less user-like timing."""

    def __init__(self, config: KNNConfig | None = None):
        self.config = config or KNNConfig()
        self.scaler_: StandardScaler | None = None
        self.neighbors_: NearestNeighbors | None = None

    def fit(self, matrix: np.ndarray) -> "KNNAnomalyModel":
        matrix = np.asarray(matrix, dtype=float)
        if matrix.ndim != 2:
            raise ValueError("Training matrix must be two-dimensional.")
        if matrix.shape[0] == 0:
            raise ValueError("Training matrix must contain at least one row.")

        transformed = matrix
        if self.config.standardize:
            self.scaler_ = StandardScaler()
            transformed = self.scaler_.fit_transform(matrix)

        neighbor_count = min(self.config.n_neighbors, transformed.shape[0])
        self.neighbors_ = NearestNeighbors(
            n_neighbors=neighbor_count,
            metric=self.config.metric,
        )
        self.neighbors_.fit(transformed)
        return self

    def score_samples(self, matrix: np.ndarray) -> np.ndarray:
        if self.neighbors_ is None:
            raise RuntimeError("Model has not been fitted.")

        matrix = np.asarray(matrix, dtype=float)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.ndim != 2:
            raise ValueError("Score matrix must be one- or two-dimensional.")

        transformed = matrix
        if self.scaler_ is not None:
            transformed = self.scaler_.transform(matrix)

        distances, _ = self.neighbors_.kneighbors(transformed, return_distance=True)
        return distances.mean(axis=1)
