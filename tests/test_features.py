from __future__ import annotations

import unittest

import pandas as pd

from keystroke_auth.features import timing_columns


class FeatureSelectionTest(unittest.TestCase):
    def test_timing_columns_selects_feature_groups(self) -> None:
        frame = pd.DataFrame(
            columns=[
                "subject",
                "H.a",
                "DD.a.b",
                "UD.a.b",
            ]
        )

        self.assertEqual(timing_columns(frame, "hold"), ["H.a"])
        self.assertEqual(timing_columns(frame, "latency"), ["DD.a.b", "UD.a.b"])
        self.assertEqual(timing_columns(frame, "all"), ["H.a", "DD.a.b", "UD.a.b"])


if __name__ == "__main__":
    unittest.main()
