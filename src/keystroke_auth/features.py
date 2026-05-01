from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd


def timing_columns(
    columns_or_frame: Iterable[str] | pd.DataFrame,
    feature_set: str = "all",
) -> list[str]:
    columns = (
        list(columns_or_frame.columns)
        if isinstance(columns_or_frame, pd.DataFrame)
        else list(columns_or_frame)
    )
    feature_set = feature_set.lower()

    if feature_set in {"hold", "dwell"}:
        prefixes = ("H.",)
    elif feature_set in {"latency", "flight"}:
        prefixes = ("DD.", "UD.")
    elif feature_set == "dd":
        prefixes = ("DD.",)
    elif feature_set == "ud":
        prefixes = ("UD.",)
    elif feature_set == "all":
        prefixes = ("H.", "DD.", "UD.")
    else:
        raise ValueError(
            "Unknown feature set. Use one of: hold, dwell, latency, dd, ud, all."
        )

    selected = [column for column in columns if column.startswith(prefixes)]
    if not selected:
        raise ValueError(f"No columns found for feature set {feature_set!r}.")
    return selected


def feature_matrix(
    frame: pd.DataFrame,
    *,
    feature_set: str = "all",
    feature_columns: Sequence[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    selected_columns = (
        list(feature_columns)
        if feature_columns is not None
        else timing_columns(frame, feature_set)
    )
    missing = [column for column in selected_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Frame is missing feature columns: {missing}")

    matrix = frame.loc[:, selected_columns].astype(float).to_numpy()
    return matrix, selected_columns
