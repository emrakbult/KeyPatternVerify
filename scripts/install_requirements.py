from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(project_root / "requirements.txt"),
        ],
        cwd=project_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
