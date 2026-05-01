from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import pandas as pd

CMU_DATASET_URL = "https://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv"
CMU_DATASET_MD5 = "470235f96568f28f9ea0da62234ec857"
DEFAULT_DATA_PATH = Path("data") / "DSL-StrongPasswordData.csv"
METADATA_COLUMNS = ("subject", "sessionIndex", "rep")


def md5_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_dataset(
    output_path: str | Path = DEFAULT_DATA_PATH,
    *,
    overwrite: bool = False,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        digest = md5_file(output_path)
        if digest != CMU_DATASET_MD5:
            raise ValueError(
                f"Existing file has MD5 {digest}, expected {CMU_DATASET_MD5}. "
                "Use --overwrite to replace it."
            )
        return output_path

    temporary_path = output_path.with_suffix(output_path.suffix + ".part")
    urllib.request.urlretrieve(CMU_DATASET_URL, temporary_path)

    digest = md5_file(temporary_path)
    if digest != CMU_DATASET_MD5:
        temporary_path.unlink(missing_ok=True)
        raise ValueError(
            f"Downloaded file has MD5 {digest}, expected {CMU_DATASET_MD5}."
        )

    temporary_path.replace(output_path)
    return output_path


def load_dataset(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run the download command first."
        )

    frame = pd.read_csv(path)
    missing = [column for column in METADATA_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    timing_columns = [
        column
        for column in frame.columns
        if column.startswith(("H.", "DD.", "UD."))
    ]
    if not timing_columns:
        raise ValueError("Dataset does not contain CMU timing feature columns.")

    return frame.sort_values(list(METADATA_COLUMNS)).reset_index(drop=True)
