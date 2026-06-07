import unittest

import numpy as np

from jcls_sim.fim import fim_rank, gaussian_fim_from_jacobian, range_covariance_from_std_devs_km
from jcls_sim.gauge import expected_v24_parameter_dim
from jcls_sim.jacobian import analytic_toa_jacobian_km
from jcls_sim.parameters import pack_v24_theta


class TestV24FIM(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 2
        self.num_satellites = 2
        self.theta = pack_v24_theta(
            np.array([[0.0, 0.0, 0.0], [3.0, 4.0, 0.0]]),
            np.array([0.1, -0.2]),
            np.array([0.5]),
        )
        self.satellite_positions = np.array([[0.0, 0.0, 10.0], [0.0, 0.0, 20.0]])
        self.links = [(1, 2), (1, 3), (1, 4), (2, 1)]
        self.jacobian = analytic_toa_jacobian_km(
            self.theta,
            self.links,
            self.satellite_positions,
            self.num_users,
            self.num_satellites,
        )
        self.sigmas = np.array([0.2, 0.3, 0.4, 0.5])

    def test_covariance_from_standard_deviations(self) -> None:
        np.testing.assert_allclose(
            range_covariance_from_std_devs_km(self.sigmas),
            np.diag(self.sigmas**2),
        )

    def test_gaussian_fim_matches_definition(self) -> None:
        fim = gaussian_fim_from_jacobian(self.jacobian, self.sigmas)
        covariance = np.diag(self.sigmas**2)
        expected = self.jacobian.T @ np.linalg.inv(covariance) @ self.jacobian
        np.testing.assert_allclose(fim, expected)

    def test_fim_shape_uses_full_gauged_dimension(self) -> None:
        fim = gaussian_fim_from_jacobian(self.jacobian, self.sigmas)
        expected_dim = expected_v24_parameter_dim(self.num_users, self.num_satellites)
        self.assertEqual(fim.shape, (expected_dim, expected_dim))

    def test_fim_symmetric_positive_semidefinite(self) -> None:
        fim = gaussian_fim_from_jacobian(self.jacobian, self.sigmas)
        np.testing.assert_allclose(fim, fim.T)
        eigenvalues = np.linalg.eigvalsh(fim)
        self.assertGreaterEqual(np.min(eigenvalues), -1e-10)

    def test_rank_is_reported(self) -> None:
        fim = gaussian_fim_from_jacobian(self.jacobian, self.sigmas)
        self.assertEqual(fim_rank(fim), np.linalg.matrix_rank(fim))

    def test_invalid_inputs_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "range_std_devs_km"):
            range_covariance_from_std_devs_km(np.zeros((2, 2)))
        with self.assertRaisesRegex(ValueError, "strictly positive"):
            range_covariance_from_std_devs_km(np.array([0.1, 0.0]))
        with self.assertRaisesRegex(ValueError, "length"):
            gaussian_fim_from_jacobian(self.jacobian, np.array([0.1, 0.2]))
        with self.assertRaisesRegex(ValueError, "2-D"):
            gaussian_fim_from_jacobian(np.zeros(3), self.sigmas)
        with self.assertRaisesRegex(ValueError, "square"):
            fim_rank(np.zeros((2, 3)))


if __name__ == "__main__":
    unittest.main()
