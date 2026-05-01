from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


REQUIRED_COLUMNS = {
    "subject",
    "far_at_eer",
    "frr_at_eer",
    "eer",
    "operating_far",
    "operating_frr",
}


def subject_sort_key(subject: str) -> tuple[int, str]:
    match = re.search(r"\d+", subject)
    return (int(match.group()) if match else 0, subject)


def load_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

    frame = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Results file is missing columns: {missing}")

    frame = frame.copy()
    frame["subject"] = frame["subject"].astype(str)
    for column in REQUIRED_COLUMNS.difference({"subject"}):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    return frame.sort_values(
        "subject",
        key=lambda series: series.map(subject_sort_key),
    ).reset_index(drop=True)


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_eer_by_subject(frame: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(frame["subject"], frame["eer"] * 100, color="#2f6f9f")
    ax.axhline(frame["eer"].mean() * 100, color="#b23b3b", linewidth=1.5, label="Mean EER")
    ax.set_title("EER by Subject")
    ax.set_xlabel("Subject")
    ax.set_ylabel("EER (%)")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    output = output_dir / "eer_by_subject.png"
    save_figure(fig, output)
    return output


def plot_far_frr_by_subject(frame: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(
        frame["subject"],
        frame["far_at_eer"] * 100,
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="FAR at EER threshold",
    )
    ax.plot(
        frame["subject"],
        frame["frr_at_eer"] * 100,
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="FRR at EER threshold",
    )
    ax.set_title("FAR and FRR by Subject")
    ax.set_xlabel("Subject")
    ax.set_ylabel("Error rate (%)")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    output = output_dir / "far_frr_by_subject.png"
    save_figure(fig, output)
    return output


def plot_operating_far_frr(frame: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(
        frame["subject"],
        frame["operating_far"] * 100,
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="Operating FAR",
    )
    ax.plot(
        frame["subject"],
        frame["operating_frr"] * 100,
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="Operating FRR",
    )
    ax.set_title("Operating FAR and FRR by Subject")
    ax.set_xlabel("Subject")
    ax.set_ylabel("Error rate (%)")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    output = output_dir / "operating_far_frr_by_subject.png"
    save_figure(fig, output)
    return output


def plot_eer_distribution(frame: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(frame["eer"] * 100, bins=12, color="#4f8f6f", edgecolor="white")
    ax.axvline(frame["eer"].mean() * 100, color="#b23b3b", linewidth=1.5, label="Mean EER")
    ax.set_title("EER Distribution")
    ax.set_xlabel("EER (%)")
    ax.set_ylabel("Number of subjects")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    output = output_dir / "eer_distribution.png"
    save_figure(fig, output)
    return output


def plot_summary(frame: pd.DataFrame, output_dir: Path) -> Path:
    labels = [
        "EER",
        "FAR@EER",
        "FRR@EER",
        "Operating FAR",
        "Operating FRR",
    ]
    values = [
        frame["eer"].mean() * 100,
        frame["far_at_eer"].mean() * 100,
        frame["frr_at_eer"].mean() * 100,
        frame["operating_far"].mean() * 100,
        frame["operating_frr"].mean() * 100,
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, values, color=["#2f6f9f", "#6b8f3a", "#b0892f", "#7d5aa6", "#b23b3b"])
    ax.set_title("Mean k-NN Authentication Metrics")
    ax.set_ylabel("Error rate (%)")
    ax.grid(axis="y", alpha=0.25)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    output = output_dir / "summary_metrics.png"
    save_figure(fig, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create plots from k-NN result CSV.")
    parser.add_argument("--input", type=Path, default=Path("reports/knn_results.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/plots"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = load_results(args.input)
    outputs = [
        plot_summary(frame, args.output_dir),
        plot_eer_by_subject(frame, args.output_dir),
        plot_far_frr_by_subject(frame, args.output_dir),
        plot_operating_far_frr(frame, args.output_dir),
        plot_eer_distribution(frame, args.output_dir),
    ]

    print("Created plots:")
    for output in outputs:
        print(f"- {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
