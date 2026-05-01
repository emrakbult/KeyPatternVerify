from __future__ import annotations

import argparse

from _path import add_src_to_path

add_src_to_path()

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local keystroke web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(f"UI: http://{args.host}:{args.port}")
    uvicorn.run(
        "keystroke_auth.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

