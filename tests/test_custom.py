from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from keystroke_auth.custom import (
    custom_feature_vector,
    custom_matrix,
    feature_columns_for_password,
    save_profile,
    train_custom_model,
)


def sample_for(password: str, offset: float = 0.0) -> list[dict[str, float | str]]:
    events = []
    for index, key in enumerate(password):
        press = offset + index * 0.2
        events.append(
            {
                "key": key,
                "press": press,
                "release": press + 0.08,
            }
        )
    return events


class CustomProfileTest(unittest.TestCase):
    def test_custom_features_handle_repeated_keys_by_position(self) -> None:
        password = "letter"
        columns = feature_columns_for_password(password)
        vector = custom_feature_vector(password, sample_for(password))

        self.assertEqual(len(columns), len(password) + 2 * (len(password) - 1))
        self.assertEqual(len(set(columns)), len(columns))
        self.assertEqual(set(columns), set(vector))

    def test_custom_model_trains_from_saved_profile(self) -> None:
        password = "verify"
        samples = [sample_for(password, offset=index * 0.01) for index in range(4)]
        matrix, columns = custom_matrix(password, samples)

        profile = {
            "password": password,
            "samples": samples,
        }
        model, threshold, trained_columns, scores = train_custom_model(profile, k=2)

        self.assertEqual(matrix.shape[0], 4)
        self.assertEqual(columns, trained_columns)
        self.assertTrue(np.isfinite(threshold))
        self.assertEqual(scores.shape, (4,))
        self.assertEqual(model.score_samples(matrix[:1]).shape, (1,))

    def test_save_profile_validates_sample_count(self) -> None:
        with self.assertRaises(ValueError):
            save_profile(
                path=Path("unused.json"),
                name="demo",
                password="abc",
                samples=[sample_for("abc")],
            )


if __name__ == "__main__":
    unittest.main()
