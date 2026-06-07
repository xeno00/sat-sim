import unittest

import numpy as np

from jcls_sim.bounds import (
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    clock_block_slice,
    clock_parameter_indices,
    clock_std_bounds_from_covariance,
    covariance_from_fim,
    manuscript_crlb_reportability_from_fim,
    non_reference_satellite_clock_block_slice,
    per_user_peb_from_covariance,
    subspace_is_estimable_from_fim,
    ue_clock_block_slice,
    ue_position_parameter_indices,
    ue_position_block_indices,
)
from jcls_sim.configs import tiny_v24_reproducibility_config, v24_crlb_mini_sweep_config
from jcls_sim.constants import C_KM_PER_S
from jcls_sim.fim import gaussian_fim_from_jacobian
from jcls_sim.gauge import expected_v24_parameter_dim
from jcls_sim.jacobian import analytic_toa_jacobian_km


class TestV24BoundIndices(unittest.TestCase):
    def test_block_indices_and_dimensions(self) -> None:
        num_users = 2
        num_satellites = 3

        self.assertEqual(expected_v24_parameter_dim(num_users, num_satellites), 10)
        self.assertEqual(ue_position_block_indices(num_users), [slice(0, 3), slice(3, 6)])
        self.assertEqual(ue_position_parameter_indices(num_users), [0, 1, 2, 3, 4, 5])
        self.assertEqual(clock_block_slice(num_users, num_satellites), slice(6, 10))
        self.assertEqual(clock_parameter_indices(num_users, num_satellites), [6, 7, 8, 9])
        self.assertEqual(clock_parameter_indices(num_users, num_satellites, group="ue"), [6, 7])
        self.assertEqual(
            clock_parameter_indices(num_users, num_satellites, group="satellite_non_reference"),
            [8, 9],
        )
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
        with self.assertRaises(ValueError):
            clock_parameter_indices(2, 3, group="reference")


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


class TestV24CrlbReportability(unittest.TestCase):
    def test_subspace_estimability_detects_nullspace_overlap(self) -> None:
        fim = np.diag([1.0, 0.0, 4.0])

        self.assertTrue(subspace_is_estimable_from_fim(fim, [0, 2]))
        self.assertFalse(subspace_is_estimable_from_fim(fim, [1]))

    def test_rank_deficient_v24_fim_marks_manuscript_bounds_undefined(self) -> None:
        num_users = 2
        num_satellites = 2
        dimension = expected_v24_parameter_dim(num_users, num_satellites)
        fim = np.eye(dimension)
        fim[6, 6] = 0.0

        reportability = manuscript_crlb_reportability_from_fim(fim, num_users, num_satellites)

        self.assertEqual(reportability["dimension"], dimension)
        self.assertEqual(reportability["rank"], dimension - 1)
        self.assertEqual(reportability["nullity"], 1)
        self.assertFalse(reportability["full_rank"])
        self.assertFalse(reportability["clock_subspace_estimable"])
        self.assertFalse(reportability["manuscript_bounds_defined"])
        self.assertEqual(reportability["manuscript_crlb_status"], "undefined_rank_deficient")

    def test_full_rank_v24_fim_marks_manuscript_bounds_finite(self) -> None:
        num_users = 2
        num_satellites = 2
        dimension = expected_v24_parameter_dim(num_users, num_satellites)

        reportability = manuscript_crlb_reportability_from_fim(np.eye(dimension), num_users, num_satellites)

        self.assertTrue(reportability["full_rank"])
        self.assertTrue(reportability["ue_position_subspace_estimable"])
        self.assertTrue(reportability["clock_subspace_estimable"])
        self.assertTrue(reportability["manuscript_bounds_defined"])
        self.assertEqual(reportability["manuscript_crlb_status"], "finite_full_rank")

    def test_seconds_and_range_clock_parameterizations_match_after_conversion(self) -> None:
        num_users = 2
        num_satellites = 6
        config = v24_crlb_mini_sweep_config(num_satellites, seed=20266660)
        theta_km = config.theta()
        jacobian_km = analytic_toa_jacobian_km(
            theta_km,
            config.links,
            config.satellite_positions_km,
            num_users,
            num_satellites,
        )
        fim_km = gaussian_fim_from_jacobian(jacobian_km, config.range_std_devs_km)
        covariance_km, metadata_km = covariance_from_fim(fim_km)
        self.assertEqual(metadata_km["method"], "inverse")

        dimension = expected_v24_parameter_dim(num_users, num_satellites)
        seconds_to_km = np.eye(dimension)
        clock_indices = clock_parameter_indices(num_users, num_satellites)
        seconds_to_km[clock_indices, clock_indices] = C_KM_PER_S
        fim_seconds = seconds_to_km.T @ fim_km @ seconds_to_km
        covariance_seconds = np.linalg.inv(fim_seconds)

        np.testing.assert_allclose(
            covariance_seconds[: 3 * num_users, : 3 * num_users],
            covariance_km[: 3 * num_users, : 3 * num_users],
            rtol=1e-8,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            np.sqrt(np.diag(covariance_seconds)[clock_indices]),
            np.sqrt(np.diag(covariance_km)[clock_indices]) / C_KM_PER_S,
            rtol=1e-8,
            atol=1e-18,
        )

    def test_fixed_parameter_information_addition_is_monotonic(self) -> None:
        initial_jacobian = np.eye(3)
        augmented_jacobian = np.vstack(
            [
                initial_jacobian,
                np.array([1.0, 1.0, 0.0]),
                np.array([0.0, 1.0, 1.0]),
            ]
        )
        initial_fim = gaussian_fim_from_jacobian(initial_jacobian, np.ones(3))
        augmented_fim = gaussian_fim_from_jacobian(augmented_jacobian, np.ones(5))
        initial_covariance, _ = covariance_from_fim(initial_fim)
        augmented_covariance, _ = covariance_from_fim(augmented_fim)

        covariance_reduction = initial_covariance - augmented_covariance
        eigenvalues = np.linalg.eigvalsh((covariance_reduction + covariance_reduction.T) / 2.0)
        self.assertGreaterEqual(float(np.min(eigenvalues)), -1e-12)
        self.assertLessEqual(float(np.trace(augmented_covariance)), float(np.trace(initial_covariance)))


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
