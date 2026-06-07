import unittest

import numpy as np

from jcls_sim.jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from jcls_sim.parameters import pack_v24_theta, v24_parameter_index, v24_parameter_names


class TestV24Jacobian(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 2
        self.num_satellites = 2
        self.ue_positions = np.array([[0.0, 0.0, 0.0], [3.0, 4.0, 0.0]])
        self.satellite_positions = np.array([[0.0, 0.0, 10.0], [0.0, 0.0, 20.0]])
        self.ue_clocks = np.array([0.1, -0.2])
        self.non_reference_satellite_clocks = np.array([0.5])
        self.theta = pack_v24_theta(
            self.ue_positions,
            self.ue_clocks,
            self.non_reference_satellite_clocks,
        )
        self.links = [(1, 2), (1, 3), (1, 4), (2, 1)]
        self.index = v24_parameter_index(self.num_users, self.num_satellites)

    def test_toa_range_vector_from_theta(self) -> None:
        np.testing.assert_allclose(
            toa_range_vector_from_theta_km(
                self.theta,
                self.links,
                self.satellite_positions,
                self.num_users,
                self.num_satellites,
            ),
            np.array([4.7, 9.9, 20.4, 5.3]),
        )

    def test_jacobian_shape_and_reference_clock_absent(self) -> None:
        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions,
            self.num_users,
            self.num_satellites,
        )
        self.assertEqual(jacobian.shape, (4, 9))
        self.assertNotIn("delta_3", v24_parameter_names(self.num_users, self.num_satellites))

    def test_ue_to_ue_clock_and_position_derivatives(self) -> None:
        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions,
            self.num_users,
            self.num_satellites,
        )
        expected = np.zeros(9)
        expected[[self.index["x_1"], self.index["y_1"], self.index["z_1"]]] = [-0.6, -0.8, 0.0]
        expected[[self.index["x_2"], self.index["y_2"], self.index["z_2"]]] = [0.6, 0.8, 0.0]
        expected[self.index["delta_1"]] = -1.0
        expected[self.index["delta_2"]] = 1.0
        np.testing.assert_allclose(jacobian[0], expected)

    def test_reference_satellite_link_has_no_reference_clock_column(self) -> None:
        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions,
            self.num_users,
            self.num_satellites,
        )
        expected = np.zeros(9)
        expected[[self.index["x_1"], self.index["y_1"], self.index["z_1"]]] = [0.0, 0.0, -1.0]
        expected[self.index["delta_1"]] = -1.0
        np.testing.assert_allclose(jacobian[1], expected)

    def test_non_reference_satellite_link_clock_derivative(self) -> None:
        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions,
            self.num_users,
            self.num_satellites,
        )
        expected = np.zeros(9)
        expected[[self.index["x_1"], self.index["y_1"], self.index["z_1"]]] = [0.0, 0.0, -1.0]
        expected[self.index["delta_1"]] = -1.0
        expected[self.index["delta_4"]] = 1.0
        np.testing.assert_allclose(jacobian[2], expected)

    def test_reverse_ue_to_ue_clock_sign(self) -> None:
        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions,
            self.num_users,
            self.num_satellites,
        )
        self.assertEqual(jacobian[3, self.index["delta_1"]], 1.0)
        self.assertEqual(jacobian[3, self.index["delta_2"]], -1.0)

    def test_invalid_shapes_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "satellite_positions_km"):
            analytic_toa_jacobian_km(self.theta, self.links, np.zeros((1, 3)), 2, 2)
        with self.assertRaisesRegex(ValueError, "theta"):
            analytic_toa_jacobian_km(np.zeros(8), self.links, self.satellite_positions, 2, 2)


if __name__ == "__main__":
    unittest.main()
