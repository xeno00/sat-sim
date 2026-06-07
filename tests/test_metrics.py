import unittest

import numpy as np

from jcls_sim.metrics import (
    all_non_reference_clock_error,
    clock_error_relative_to_reference,
    non_reference_satellite_clock_error,
    position_error_m,
    ue_clock_error,
)


class TestV24Metrics(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 3
        self.num_satellites = 4
        self.true = {
            1: 10.0,
            2: 20.0,
            3: 30.0,
            4: 100.0,
            5: 110.0,
            6: 120.0,
            7: 130.0,
        }
        self.estimated = {
            1: 11.0,
            2: 18.0,
            3: 33.0,
            4: 104.0,
            5: 111.0,
            6: 118.0,
            7: 132.0,
        }

    def test_all_non_reference_clock_error(self) -> None:
        self.assertAlmostEqual(
            all_non_reference_clock_error(self.true, self.estimated, self.num_users, self.num_satellites),
            21.0 / 6.0,
        )

    def test_ue_clock_error(self) -> None:
        self.assertAlmostEqual(
            ue_clock_error(self.true, self.estimated, self.num_users, self.num_satellites),
            10.0 / 3.0,
        )

    def test_non_reference_satellite_clock_error(self) -> None:
        self.assertAlmostEqual(
            non_reference_satellite_clock_error(
                self.true,
                self.estimated,
                self.num_users,
                self.num_satellites,
            ),
            11.0 / 3.0,
        )

    def test_common_clock_bias_invariance(self) -> None:
        biased_true = {node_id: value + 1000.0 for node_id, value in self.true.items()}
        biased_estimated = {node_id: value + 1000.0 for node_id, value in self.estimated.items()}
        baseline = all_non_reference_clock_error(
            self.true,
            self.estimated,
            self.num_users,
            self.num_satellites,
        )
        biased = all_non_reference_clock_error(
            biased_true,
            biased_estimated,
            self.num_users,
            self.num_satellites,
        )
        self.assertAlmostEqual(baseline, biased)

    def test_reference_satellite_excluded(self) -> None:
        changed_reference_only = dict(self.estimated)
        changed_reference_only[4] = self.true[4] + 1000.0
        # Reference changes affect relative clocks, but the reference itself is
        # not included as a selected error term.
        with_reference_shift = clock_error_relative_to_reference(
            self.true,
            changed_reference_only,
            self.num_users,
            self.num_satellites,
            clock_ids="all_non_reference",
        )
        self.assertNotEqual(with_reference_shift, 0.0)
        self.assertEqual(
            clock_error_relative_to_reference(
                self.true,
                self.true,
                self.num_users,
                self.num_satellites,
                clock_ids="all_non_reference",
            ),
            0.0,
        )

    def test_invalid_clock_ids_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "clock_ids"):
            clock_error_relative_to_reference(
                self.true,
                self.estimated,
                self.num_users,
                self.num_satellites,
                clock_ids="bad",
            )

    def test_position_error_m_matrix(self) -> None:
        true_positions = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
        est_positions = np.array([[0.003, 0.004, 0.0], [1.0, 2.0, 3.012]])
        np.testing.assert_allclose(position_error_m(true_positions, est_positions), np.array([5.0, 12.0]))

    def test_position_error_m_vector(self) -> None:
        true_position = np.array([0.0, 0.0, 0.0])
        est_position = np.array([0.0, 0.006, 0.008])
        np.testing.assert_allclose(position_error_m(true_position, est_position), np.array([10.0]))


if __name__ == "__main__":
    unittest.main()
