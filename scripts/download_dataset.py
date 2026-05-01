from __future__ import annotations

import sys

from _path import add_src_to_path

add_src_to_path()

from keystroke_auth.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["download", *sys.argv[1:]]))
