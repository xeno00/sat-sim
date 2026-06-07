import unittest

import numpy as np

from jcls_sim.measurements import (
    clock_offset_for_node_km,
    euclidean_range_km,
    toa_range_model_km,
    toa_range_vector_km,
)


class TestV24Measurements(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 2
        self.num_satellites = 2
        self.ue1 = np.array([0.0, 0.0, 0.0])
        self.ue2 = np.array([3.0, 4.0, 0.0])
        self.reference_satellite = np.array([0.0, 0.0, 10.0])
        self.non_reference_satellite = np.array([0.0, 0.0, 20.0])
        self.ue_clocks = np.array([0.1, -0.2])
        self.non_reference_satellite_clocks = np.array([0.5])

    def test_clock_offsets(self) -> None:
        self.assertEqual(
            clock_offset_for_node_km(1, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            0.1,
        )
        self.assertEqual(
            clock_offset_for_node_km(2, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            -0.2,
        )
        self.assertEqual(
            clock_offset_for_node_km(3, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            0.0,
        )
        self.assertEqual(
            clock_offset_for_node_km(4, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            0.5,
        )

    def test_euclidean_ranges(self) -> None:
        self.assertAlmostEqual(euclidean_range_km(self.ue1, self.ue2), 5.0)
        self.assertAlmostEqual(euclidean_range_km(self.ue1, self.reference_satellite), 10.0)
        self.assertAlmostEqual(euclidean_range_km(self.ue1, self.non_reference_satellite), 20.0)

    def test_toa_range_model_receiver_transmitter_sign(self) -> None:
        self.assertAlmostEqual(
            toa_range_model_km(1, 2, self.ue1, self.ue2, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            4.7,
        )
        self.assertAlmostEqual(
            toa_range_model_km(
                1,
                3,
                self.ue1,
                self.reference_satellite,
                self.ue_clocks,
                self.non_reference_satellite_clocks,
                2,
                2,
            ),
            9.9,
        )
        self.assertAlmostEqual(
            toa_range_model_km(
                1,
                4,
                self.ue1,
                self.non_reference_satellite,
                self.ue_clocks,
                self.non_reference_satellite_clocks,
                2,
                2,
            ),
            20.4,
        )
        self.assertAlmostEqual(
            toa_range_model_km(2, 1, self.ue2, self.ue1, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            5.3,
        )

    def test_toa_range_vector(self) -> None:
        links = [
            (1, 2, self.ue1, self.ue2),
            (1, 3, self.ue1, self.reference_satellite),
            (1, 4, self.ue1, self.non_reference_satellite),
            (2, 1, self.ue2, self.ue1),
        ]
        np.testing.assert_allclose(
            toa_range_vector_km(links, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2),
            np.array([4.7, 9.9, 20.4, 5.3]),
        )

    def test_invalid_node_ids_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "node_id"):
            clock_offset_for_node_km(0, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2)
        with self.assertRaisesRegex(ValueError, "node_id"):
            clock_offset_for_node_km(5, self.ue_clocks, self.non_reference_satellite_clocks, 2, 2)

    def test_invalid_clock_vector_lengths_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "ue_clocks_km"):
            clock_offset_for_node_km(1, np.zeros(3), self.non_reference_satellite_clocks, 2, 2)
        with self.assertRaisesRegex(ValueError, "non_reference_satellite_clocks_km"):
            clock_offset_for_node_km(4, self.ue_clocks, np.zeros(2), 2, 2)

    def test_invalid_position_shapes_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "receiver_position_km"):
            euclidean_range_km(np.array([0.0, 0.0]), self.ue2)
        with self.assertRaisesRegex(ValueError, "transmitter_position_km"):
            euclidean_range_km(self.ue1, np.zeros((1, 3)))


if __name__ == "__main__":
    unittest.main()
