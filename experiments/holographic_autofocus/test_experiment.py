import unittest

import numpy as np

from experiment import (
    add_camera_noise,
    clean_hologram,
    estimate_focus,
    focus_score,
    make_model,
    propagate,
)


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = make_model()

    def test_zero_distance_is_identity(self):
        field = self.model["object_field"]
        result = propagate(field, 0.0, self.model)
        np.testing.assert_array_equal(result, field)

    def test_periodic_propagation_round_trip(self):
        field = self.model["object_field"]
        forward = propagate(field, 0.004, self.model)
        backward = propagate(forward, -0.004, self.model)

        np.testing.assert_allclose(
            backward,
            field,
            rtol=1e-10,
            atol=1e-10,
        )

    def test_clean_hologram(self):
        hologram = clean_hologram(self.model)
        self.assertTrue(np.isfinite(hologram).all())
        self.assertTrue((hologram >= 0).all())

    def test_carrier_and_mask_fit_sampling_grid(self):
        carrier = self.model["carrier_bins"] / self.model["n"]
        radius = self.model["filter_radius_bins"] / self.model["n"]

        self.assertLess(carrier + radius, 0.5)
        self.assertLess(radius, carrier)

    def test_noise_is_reproducible(self):
        hologram = clean_hologram(self.model)

        first = add_camera_noise(
            hologram,
            np.random.default_rng(123),
            peak_electrons=200,
        )
        second = add_camera_noise(
            hologram,
            np.random.default_rng(123),
            peak_electrons=200,
        )

        np.testing.assert_array_equal(first, second)

    def test_invalid_noise_level_is_rejected(self):
        with self.assertRaises(ValueError):
            add_camera_noise(
                clean_hologram(self.model),
                np.random.default_rng(42),
                peak_electrons=0,
            )

    def test_focus_metric_ignores_overall_scale(self):
        field = self.model["object_field"]

        self.assertAlmostEqual(
            focus_score(field),
            focus_score(3.0 * field),
            places=12,
        )

    def test_clean_focus_matches_known_scene(self):
        estimate = estimate_focus(
            clean_hologram(self.model),
            self.model,
        )

        self.assertFalse(estimate["at_scan_edge"])
        self.assertLessEqual(
            abs(estimate["distance_m"] + 0.004),
            0.000125,
        )


if __name__ == "__main__":
    unittest.main()
