from __future__ import annotations

import sys
from pathlib import Path


def add_src_to_path() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    return project_root
