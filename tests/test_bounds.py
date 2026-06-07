import unittest

import numpy as np

from jcls_sim.bounds import (
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    clock_block_slice,
    clock_std_bounds_from_covariance,
    covariance_from_fim,
    non_reference_satellite_clock_block_slice,
    per_user_peb_from_covariance,
    ue_clock_block_slice,
    ue_position_block_indices,
)
from jcls_sim.configs import tiny_v24_reproducibility_config
from jcls_sim.fim import gaussian_fim_from_jacobian
from jcls_sim.gauge import expected_v24_parameter_dim
from jcls_sim.jacobian import analytic_toa_jacobian_km


class TestV24BoundIndices(unittest.TestCase):
    def test_block_indices_and_dimensions(self) -> None:
        num_users = 2
        num_satellites = 3

        self.assertEqual(expected_v24_parameter_dim(num_users, num_satellites), 10)
        self.assertEqual(ue_position_block_indices(num_users), [slice(0, 3), slice(3, 6)])
        self.assertEqual(clock_block_slice(num_users, num_satellites), slice(6, 10))
        self.assertEqual(ue_clock_block_slice(num_users, num_satellites), slice(6, 8))
        self.assertEqual(
            non_reference_satellite_clock_block_slice(num_users, num_satellites),
            slice(8, 10),
        )

    def test_invalid_counts_raise(self) -> None:
        with self.assertRaises(ValueError):
            ue_position_block_indices(0)
        with self.assertRaises(ValueError):
            clock_block_slice(2, 0)


class TestV24BoundsFromCovariance(unittest.TestCase):
    def setUp(self) -> None:
        self.num_users = 2
        self.num_satellites = 3
        self.diagonal = np.array([1.0, 4.0, 9.0, 16.0, 25.0, 36.0, 0.01, 0.04, 0.09, 0.16])
        self.covariance = np.diag(self.diagonal)

    def test_per_user_peb_extraction(self) -> None:
        expected_pebs = np.array([np.sqrt(14.0), np.sqrt(77.0)])

        actual_pebs = per_user_peb_from_covariance(
            self.covariance,
            self.num_users,
            self.num_satellites,
        )

        np.testing.assert_allclose(actual_pebs, expected_pebs)
        self.assertAlmostEqual(
            average_ue_peb_from_covariance(
                self.covariance,
                self.num_users,
                self.num_satellites,
            ),
            float(np.mean(expected_pebs)),
        )

    def test_clock_bounds(self) -> None:
        np.testing.assert_allclose(
            clock_std_bounds_from_covariance(
                self.covariance,
                self.num_users,
                self.num_satellites,
            ),
            np.array([0.1, 0.2, 0.3, 0.4]),
        )
        np.testing.assert_allclose(
            clock_std_bounds_from_covariance(
                self.covariance,
                self.num_users,
                self.num_satellites,
                group="ue",
            ),
            np.array([0.1, 0.2]),
        )
        np.testing.assert_allclose(
            clock_std_bounds_from_covariance(
                self.covariance,
                self.num_users,
                self.num_satellites,
                group="satellite_non_reference",
            ),
            np.array([0.3, 0.4]),
        )
        self.assertAlmostEqual(
            average_clock_bound_from_covariance(
                self.covariance,
                self.num_users,
                self.num_satellites,
            ),
            0.25,
        )

    def test_negative_covariance_diagonal_raises(self) -> None:
        covariance = self.covariance.copy()
        covariance[6, 6] = -0.01

        with self.assertRaises(ValueError):
            clock_std_bounds_from_covariance(covariance, self.num_users, self.num_satellites)


class TestCovarianceFromFIM(unittest.TestCase):
    def test_full_rank_fim_uses_inverse(self) -> None:
        covariance = np.diag([1.0, 2.0, 4.0])
        fim = np.diag(1.0 / np.diag(covariance))

        actual_covariance, metadata = covariance_from_fim(fim)

        np.testing.assert_allclose(actual_covariance, covariance)
        self.assertEqual(metadata["method"], "inverse")
        self.assertEqual(metadata["rank"], 3)
        self.assertTrue(metadata["full_rank"])

    def test_rank_deficient_fim_uses_pseudoinverse(self) -> None:
        fim = np.diag([1.0, 0.0, 4.0])

        covariance, metadata = covariance_from_fim(fim)

        np.testing.assert_allclose(covariance, np.diag([1.0, 0.0, 0.25]))
        self.assertEqual(metadata["method"], "pinv")
        self.assertLess(metadata["rank"], metadata["dimension"])
        self.assertFalse(metadata["full_rank"])

    def test_invalid_fim_and_rcond_raise(self) -> None:
        with self.assertRaises(ValueError):
            covariance_from_fim(np.zeros((2, 3)))
        with self.assertRaises(ValueError):
            covariance_from_fim(np.eye(2), rcond=0.0)


class TestV24BoundIntegration(unittest.TestCase):
    def test_full_gauged_fim_integration_reports_rank_and_bounds(self) -> None:
        config = tiny_v24_reproducibility_config()
        theta = config.theta()
        jacobian = analytic_toa_jacobian_km(
            theta,
            config.links,
            config.satellite_positions_km,
            config.num_users,
            config.num_satellites,
        )
        fim = gaussian_fim_from_jacobian(jacobian, config.range_std_devs_km)

        covariance, metadata = covariance_from_fim(fim)
        pebs = per_user_peb_from_covariance(
            covariance,
            config.num_users,
            config.num_satellites,
        )
        clock_bounds = clock_std_bounds_from_covariance(
            covariance,
            config.num_users,
            config.num_satellites,
        )

        self.assertEqual(fim.shape, (9, 9))
        self.assertEqual(covariance.shape, (9, 9))
        self.assertEqual(metadata["dimension"], 9)
        self.assertEqual(metadata["rank"], np.linalg.matrix_rank(fim, tol=1e-12))
        self.assertIn(metadata["method"], {"inverse", "pinv"})
        self.assertEqual(pebs.shape, (2,))
        self.assertEqual(clock_bounds.shape, (3,))
        self.assertTrue(np.all(np.isfinite(pebs)))
        self.assertTrue(np.all(pebs >= 0.0))
        self.assertTrue(np.all(np.isfinite(clock_bounds)))
        self.assertTrue(np.all(clock_bounds >= 0.0))

    def test_invalid_dimensions_and_groups_raise(self) -> None:
        covariance = np.eye(10)

        with self.assertRaises(ValueError):
            clock_std_bounds_from_covariance(covariance[:9, :9], 2, 3)
        with self.assertRaises(ValueError):
            clock_std_bounds_from_covariance(covariance, 2, 3, group="reference")
        with self.assertRaises(ValueError):
            per_user_peb_from_covariance(np.eye(5), 2, 3)
        with self.assertRaises(ValueError):
            per_user_peb_from_covariance(np.eye(6), 2, 3)


if __name__ == "__main__":
    unittest.main()
