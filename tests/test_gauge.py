import unittest

import numpy as np

from jcls_sim.gauge import (
    all_clock_node_ids,
    expected_v24_parameter_dim,
    reference_satellite_node_id,
    relative_clock_dict,
    v24_clock_node_ids,
    v24_clock_vector_from_full,
)


class TestV24Gauge(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 3
        self.num_satellites = 4
        self.full = {
            1: 10.0,
            2: 20.0,
            3: 30.0,
            4: 100.0,
            5: 110.0,
            6: 120.0,
            7: 130.0,
        }

    def test_reference_satellite_node_id(self) -> None:
        self.assertEqual(reference_satellite_node_id(self.num_users), 4)

    def test_all_clock_node_ids(self) -> None:
        self.assertEqual(all_clock_node_ids(self.num_users, self.num_satellites), [1, 2, 3, 4, 5, 6, 7])

    def test_v24_clock_node_ids(self) -> None:
        self.assertEqual(v24_clock_node_ids(self.num_users, self.num_satellites), [1, 2, 3, 5, 6, 7])

    def test_expected_v24_parameter_dim(self) -> None:
        self.assertEqual(expected_v24_parameter_dim(self.num_users, self.num_satellites), 15)

    def test_relative_clock_dict(self) -> None:
        expected = {
            1: -90.0,
            2: -80.0,
            3: -70.0,
            4: 0.0,
            5: 10.0,
            6: 20.0,
            7: 30.0,
        }
        self.assertEqual(relative_clock_dict(self.full, self.num_users, self.num_satellites), expected)

    def test_v24_clock_vector_from_full(self) -> None:
        expected = np.array([-90.0, -80.0, -70.0, 10.0, 20.0, 30.0])
        np.testing.assert_array_equal(
            v24_clock_vector_from_full(self.full, self.num_users, self.num_satellites),
            expected,
        )

    def test_missing_reference_clock_raises(self) -> None:
        missing_reference = dict(self.full)
        del missing_reference[4]
        with self.assertRaisesRegex(ValueError, "missing required node id"):
            relative_clock_dict(missing_reference, self.num_users, self.num_satellites)

    def test_invalid_sizes_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "num_users"):
            reference_satellite_node_id(0)
        with self.assertRaisesRegex(ValueError, "num_satellites"):
            all_clock_node_ids(self.num_users, 0)


if __name__ == "__main__":
    unittest.main()
