from __future__ import annotations

import argparse
from pathlib import Path

from .data import DEFAULT_DATA_PATH, download_dataset, load_dataset
from .evaluation import evaluate_all_subjects, summarize_results, train_authenticator
from .realtime import stream_dataset_attempts


def cmd_download(args: argparse.Namespace) -> int:
    path = download_dataset(args.output, overwrite=args.overwrite)
    print(f"Dataset ready: {path}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    frame = load_dataset(args.data)
    results = evaluate_all_subjects(
        frame,
        feature_set=args.features,
        k=args.k,
        train_count=args.train_count,
        impostor_count=args.impostor_count,
        operating_quantile=args.operating_quantile,
    )
    summary = summarize_results(results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(output_path, index=False)
        print(f"Per-subject results written: {output_path}")

    print(f"Subjects: {int(summary['subjects'])}")
    print(f"EER mean: {summary['eer_mean']:.4f}")
    print(f"EER std:  {summary['eer_std']:.4f}")
    print(f"FAR@EER mean: {summary['far_at_eer_mean']:.4f}")
    print(f"FRR@EER mean: {summary['frr_at_eer_mean']:.4f}")
    print(f"Operating FAR mean: {summary['operating_far_mean']:.4f}")
    print(f"Operating FRR mean: {summary['operating_frr_mean']:.4f}")
    return 0


def cmd_realtime_sim(args: argparse.Namespace) -> int:
    frame = load_dataset(args.data)
    authenticator = train_authenticator(
        frame,
        args.subject,
        feature_set=args.features,
        k=args.k,
        threshold_source=args.threshold_source,
    )
    print(
        f"Subject={authenticator.subject} "
        f"threshold={authenticator.threshold:.4f} "
        f"source={authenticator.threshold_source}"
    )

    def print_decision(decision) -> None:
        verdict = "ACCEPT" if decision.accepted else "REJECT"
        print(
            f"{decision.label:8s} score={decision.score:.4f} "
            f"threshold={decision.threshold:.4f} {verdict}"
        )

    stream_dataset_attempts(
        frame,
        authenticator,
        attempts=args.attempts,
        include_impostors=not args.genuine_only,
        delay=args.delay,
        sink=print_decision,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CMU keystroke dynamics authentication toolkit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download the CMU CSV dataset.")
    download.add_argument("--output", type=Path, default=DEFAULT_DATA_PATH)
    download.add_argument("--overwrite", action="store_true")
    download.set_defaults(func=cmd_download)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate k-NN with FAR/FRR/EER.")
    evaluate.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    evaluate.add_argument("--features", default="all")
    evaluate.add_argument("--k", type=int, default=5)
    evaluate.add_argument("--train-count", type=int, default=200)
    evaluate.add_argument("--impostor-count", type=int, default=5)
    evaluate.add_argument("--operating-quantile", type=float, default=0.95)
    evaluate.add_argument("--output", type=Path, default=Path("reports/knn_results.csv"))
    evaluate.set_defaults(func=cmd_evaluate)

    realtime = subparsers.add_parser(
        "realtime-sim",
        help="Stream dataset rows one by one as a realtime authentication scenario.",
    )
    realtime.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    realtime.add_argument("--subject", required=True)
    realtime.add_argument("--features", default="all")
    realtime.add_argument("--k", type=int, default=5)
    realtime.add_argument("--attempts", type=int, default=12)
    realtime.add_argument("--delay", type=float, default=0.0)
    realtime.add_argument("--genuine-only", action="store_true")
    realtime.add_argument(
        "--threshold-source",
        choices=["eer", "train-quantile"],
        default="eer",
    )
    realtime.set_defaults(func=cmd_realtime_sim)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
