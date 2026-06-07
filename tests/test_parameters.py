import unittest

import numpy as np

from jcls_sim.parameters import (
    non_reference_satellite_clock_param_names,
    pack_v24_theta,
    ue_clock_param_names,
    ue_position_param_names,
    unpack_v24_theta,
    v24_parameter_index,
    v24_parameter_names,
)


class TestV24Parameters(unittest.TestCase):
    def test_parameter_names_and_count(self) -> None:
        expected = [
            "x_1",
            "y_1",
            "z_1",
            "x_2",
            "y_2",
            "z_2",
            "x_3",
            "y_3",
            "z_3",
            "delta_1",
            "delta_2",
            "delta_3",
            "delta_5",
            "delta_6",
            "delta_7",
        ]
        names = v24_parameter_names(3, 4)
        self.assertEqual(names, expected)
        self.assertEqual(len(names), 15)
        self.assertNotIn("delta_4", names)

    def test_component_name_helpers(self) -> None:
        self.assertEqual(ue_position_param_names(2), ["x_1", "y_1", "z_1", "x_2", "y_2", "z_2"])
        self.assertEqual(ue_clock_param_names(2), ["delta_1", "delta_2"])
        self.assertEqual(non_reference_satellite_clock_param_names(2, 3), ["delta_4", "delta_5"])

    def test_parameter_index(self) -> None:
        index = v24_parameter_index(3, 4)
        self.assertEqual(index["x_1"], 0)
        self.assertEqual(index["delta_1"], 9)
        self.assertEqual(index["delta_7"], 14)

    def test_pack_unpack_round_trip(self) -> None:
        ue_positions = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        ue_clocks = np.array([0.1, 0.2, 0.3])
        satellite_clocks = np.array([0.5, 0.6, 0.7])
        theta = pack_v24_theta(ue_positions, ue_clocks, satellite_clocks)
        np.testing.assert_allclose(
            theta,
            np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 0.1, 0.2, 0.3, 0.5, 0.6, 0.7]),
        )
        unpacked_positions, unpacked_ue_clocks, unpacked_satellite_clocks = unpack_v24_theta(theta, 3, 4)
        np.testing.assert_allclose(unpacked_positions, ue_positions)
        np.testing.assert_allclose(unpacked_ue_clocks, ue_clocks)
        np.testing.assert_allclose(unpacked_satellite_clocks, satellite_clocks)

    def test_invalid_shapes_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "ue_positions_km"):
            pack_v24_theta(np.array([1.0, 2.0, 3.0]), np.array([0.1]), np.array([0.2]))
        with self.assertRaisesRegex(ValueError, "ue_clocks_km"):
            pack_v24_theta(np.zeros((2, 3)), np.zeros(3), np.zeros(1))
        with self.assertRaisesRegex(ValueError, "non_reference_satellite_clocks_km"):
            pack_v24_theta(np.zeros((2, 3)), np.zeros(2), np.zeros((1, 1)))
        with self.assertRaisesRegex(ValueError, "theta"):
            unpack_v24_theta(np.zeros(14), 3, 4)

    def test_invalid_sizes_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "num_users"):
            v24_parameter_names(0, 4)
        with self.assertRaisesRegex(ValueError, "num_satellites"):
            v24_parameter_names(3, 0)


if __name__ == "__main__":
    unittest.main()
