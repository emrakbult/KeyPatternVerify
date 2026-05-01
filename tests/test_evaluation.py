from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from keystroke_auth.evaluation import (
    evaluate_all_subjects,
    summarize_results,
    train_authenticator,
)


def make_frame() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    for subject_index, subject in enumerate(["s001", "s002", "s003"]):
        center = subject_index * 0.4
        for rep in range(12):
            rows.append(
                {
                    "subject": subject,
                    "sessionIndex": rep // 4 + 1,
                    "rep": rep + 1,
                    "H.a": 0.10 + center + rng.normal(0, 0.01),
                    "DD.a.b": 0.20 + center + rng.normal(0, 0.01),
                    "UD.a.b": 0.10 + center + rng.normal(0, 0.01),
                }
            )
    return (
        pd.DataFrame(rows)
        .sort_values(["subject", "sessionIndex", "rep"])
        .reset_index(drop=True)
    )


class EvaluationTest(unittest.TestCase):
    def test_evaluate_all_subjects_and_train_authenticator(self) -> None:
        frame = make_frame()

        results = evaluate_all_subjects(
            frame,
            train_count=6,
            impostor_count=2,
            k=2,
        )
        summary = summarize_results(results)
        authenticator = train_authenticator(
            frame,
            "s001",
            train_count=6,
            impostor_count=2,
            k=2,
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(summary["subjects"], 3.0)
        self.assertEqual(authenticator.subject, "s001")
        self.assertGreater(len(authenticator.feature_columns), 0)
        self.assertTrue(np.isfinite(authenticator.threshold))


if __name__ == "__main__":
    unittest.main()
