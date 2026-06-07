import unittest

import numpy as np

from jcls_sim.estimators import gauss_newton_step, information_form_ekf_update
from jcls_sim.fim import gaussian_fim_from_jacobian, range_covariance_from_std_devs_km
from jcls_sim.gauge import expected_v24_parameter_dim, reference_satellite_node_id
from jcls_sim.jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from jcls_sim.metrics import all_non_reference_clock_error
from jcls_sim.parameters import pack_v24_theta, v24_parameter_index, v24_parameter_names


class TestV24EndToEndSmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 2
        self.num_satellites = 2
        self.ue_positions_km = np.array(
            [
                [0.0, 0.0, 0.0],
                [3.0, 4.0, 0.0],
            ]
        )
        self.satellite_positions_km = np.array(
            [
                [0.0, 0.0, 10.0],
                [0.0, 0.0, 20.0],
            ]
        )
        self.ue_clocks_km = np.array([0.1, -0.2])
        self.non_reference_satellite_clocks_km = np.array([0.5])
        self.theta = pack_v24_theta(
            self.ue_positions_km,
            self.ue_clocks_km,
            self.non_reference_satellite_clocks_km,
        )
        self.links = [(1, 2), (1, 3), (1, 4), (2, 1)]
        self.sigmas_km = np.array([0.2, 0.3, 0.4, 0.5])
        self.index = v24_parameter_index(self.num_users, self.num_satellites)

    def test_v24_measurements_jacobian_and_fim_layers(self) -> None:
        expected_dim = 4 * self.num_users + self.num_satellites - 1

        self.assertEqual(reference_satellite_node_id(self.num_users), 3)
        self.assertEqual(expected_v24_parameter_dim(self.num_users, self.num_satellites), expected_dim)
        self.assertEqual(self.theta.shape, (expected_dim,))

        parameter_names = v24_parameter_names(self.num_users, self.num_satellites)
        self.assertEqual(len(parameter_names), expected_dim)
        self.assertNotIn("delta_3", parameter_names)
        self.assertNotIn("delta_3", self.index)
        self.assertIn("delta_4", self.index)

        measurements = toa_range_vector_from_theta_km(
            self.theta,
            self.links,
            self.satellite_positions_km,
            self.num_users,
            self.num_satellites,
        )
        expected_measurements = np.array(
            [
                5.0 + self.ue_clocks_km[1] - self.ue_clocks_km[0],
                10.0 - self.ue_clocks_km[0],
                20.0 + self.non_reference_satellite_clocks_km[0] - self.ue_clocks_km[0],
                5.0 + self.ue_clocks_km[0] - self.ue_clocks_km[1],
            ]
        )
        np.testing.assert_allclose(measurements, expected_measurements)
        np.testing.assert_allclose(measurements, np.array([4.7, 9.9, 20.4, 5.3]))

        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions_km,
            self.num_users,
            self.num_satellites,
        )
        self.assertEqual(jacobian.shape, (len(self.links), expected_dim))

        r_z = range_covariance_from_std_devs_km(self.sigmas_km)
        np.testing.assert_allclose(r_z, np.diag(self.sigmas_km**2))

        fim = gaussian_fim_from_jacobian(jacobian, self.sigmas_km)
        self.assertEqual(fim.shape, (expected_dim, expected_dim))
        np.testing.assert_allclose(fim, jacobian.T @ np.linalg.inv(r_z) @ jacobian)
        np.testing.assert_allclose(fim, fim.T, atol=1e-12)
        eigenvalues = np.linalg.eigvalsh((fim + fim.T) / 2.0)
        self.assertGreaterEqual(float(np.min(eigenvalues)), -1e-10)

    def test_gauss_newton_smoke_update_uses_precision_weighting(self) -> None:
        x = np.array([0.0])
        jacobian = np.array([[1.0], [1.0]])
        residual = np.array([1.0, 5.0])
        sigmas_km = np.array([1.0, 10.0])
        precision = np.linalg.inv(np.diag(sigmas_km**2))

        updated = gauss_newton_step(x, residual, jacobian, sigmas_km)

        expected_delta = np.linalg.solve(
            jacobian.T @ precision @ jacobian,
            jacobian.T @ precision @ residual,
        )
        unweighted_delta = np.linalg.solve(jacobian.T @ jacobian, jacobian.T @ residual)

        np.testing.assert_allclose(updated, x + expected_delta)
        self.assertFalse(np.allclose(updated, x + unweighted_delta))

    def test_information_form_ekf_smoke_update_matches_linearization(self) -> None:
        jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions_km,
            self.num_users,
            self.num_satellites,
        )
        h_pred = toa_range_vector_from_theta_km(
            self.theta,
            self.links,
            self.satellite_positions_km,
            self.num_users,
            self.num_satellites,
        )
        innovation = np.array([0.01, -0.02, 0.03, -0.04])
        z = h_pred + innovation
        p_pred = np.diag(np.linspace(1.0, 2.0, self.theta.shape[0]))
        precision_pred = np.linalg.inv(p_pred)
        measurement_precision = np.linalg.inv(np.diag(self.sigmas_km**2))

        posterior_x, posterior_p = information_form_ekf_update(
            self.theta,
            p_pred,
            h_pred,
            jacobian,
            z,
            self.sigmas_km,
        )

        expected_precision = precision_pred + jacobian.T @ measurement_precision @ jacobian
        expected_p = np.linalg.inv(expected_precision)
        expected_x = self.theta + expected_p @ (jacobian.T @ measurement_precision @ innovation)

        self.assertEqual(posterior_x.shape, self.theta.shape)
        self.assertEqual(posterior_p.shape, (self.theta.shape[0], self.theta.shape[0]))
        np.testing.assert_allclose(posterior_p, expected_p)
        np.testing.assert_allclose(posterior_x, expected_x)

    def test_clock_metric_is_gauge_consistent_and_excludes_reference_satellite(self) -> None:
        true_full_clocks_km = {1: 0.1, 2: -0.2, 3: 0.0, 4: 0.5}
        estimated_full_clocks_km = {1: 0.3, 2: -0.1, 3: 0.0, 4: 0.4}

        metric = all_non_reference_clock_error(
            true_full_clocks_km,
            estimated_full_clocks_km,
            self.num_users,
            self.num_satellites,
        )

        expected_non_reference_mean = (0.2 + 0.1 + 0.1) / 3.0
        reference_including_mean = (0.2 + 0.1 + 0.0 + 0.1) / 4.0
        self.assertAlmostEqual(metric, expected_non_reference_mean)
        self.assertNotAlmostEqual(metric, reference_including_mean)

        common_shifted_estimate = {
            node_id: clock_km + 1000.0
            for node_id, clock_km in true_full_clocks_km.items()
        }
        self.assertAlmostEqual(
            all_non_reference_clock_error(
                true_full_clocks_km,
                common_shifted_estimate,
                self.num_users,
                self.num_satellites,
            ),
            0.0,
            delta=1e-12,
        )


if __name__ == "__main__":
    unittest.main()
