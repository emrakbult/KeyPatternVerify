from __future__ import annotations

import unittest

import numpy as np

from keystroke_auth.metrics import equal_error_rate, far_frr


class MetricsTest(unittest.TestCase):
    def test_far_frr_uses_lower_scores_as_acceptance(self) -> None:
        genuine = np.array([0.1, 0.2, 0.3])
        impostor = np.array([0.4, 0.5, 0.6])

        far, frr = far_frr(genuine, impostor, threshold=0.35)

        self.assertEqual(far, 0.0)
        self.assertEqual(frr, 0.0)

    def test_equal_error_rate_returns_best_threshold(self) -> None:
        genuine = np.array([0.1, 0.2, 0.9])
        impostor = np.array([0.3, 0.8, 1.0])

        rates = equal_error_rate(genuine, impostor)

        self.assertGreaterEqual(rates.eer, 0.0)
        self.assertLessEqual(rates.eer, 1.0)
        self.assertLessEqual(abs(rates.far - rates.frr), 1.0 / 3.0)


if __name__ == "__main__":
    unittest.main()
