import unittest

import numpy as np

from jcls_sim.estimators import (
    gauss_newton_step,
    information_form_ekf_update,
    levenberg_marquardt_step,
    weighted_normal_equations,
)


class TestWeightedNormalEquations(unittest.TestCase):
    def setUp(self) -> None:
        self.jacobian = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        self.residual = np.array([1.0, 2.0, 3.0])
        self.sigmas = np.array([1.0, 2.0, 4.0])
        self.covariance = np.diag(self.sigmas**2)
        self.precision = np.linalg.inv(self.covariance)

    def test_uses_precision_weighting(self) -> None:
        normal, rhs = weighted_normal_equations(self.jacobian, self.residual, self.sigmas)

        expected_normal = self.jacobian.T @ self.precision @ self.jacobian
        expected_rhs = self.jacobian.T @ self.precision @ self.residual
        covariance_weighted_normal = self.jacobian.T @ self.covariance @ self.jacobian

        np.testing.assert_allclose(normal, expected_normal)
        np.testing.assert_allclose(rhs, expected_rhs)
        self.assertFalse(np.allclose(normal, covariance_weighted_normal))

    def test_bad_dimensions_raise(self) -> None:
        with self.assertRaises(ValueError):
            weighted_normal_equations(np.ones(3), self.residual, self.sigmas)
        with self.assertRaises(ValueError):
            weighted_normal_equations(self.jacobian, self.residual[:2], self.sigmas)
        with self.assertRaises(ValueError):
            weighted_normal_equations(self.jacobian, self.residual, self.sigmas[:2])

    def test_nonpositive_sigma_raises(self) -> None:
        with self.assertRaises(ValueError):
            weighted_normal_equations(self.jacobian, self.residual, np.array([1.0, 0.0, 4.0]))


class TestGaussNewtonStep(unittest.TestCase):
    def test_one_step_linearized_update_uses_precision_weighting(self) -> None:
        x = np.array([10.0, -5.0])
        jacobian = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        residual = np.array([1.0, 2.0, 3.0])
        sigmas = np.array([1.0, 2.0, 4.0])
        precision = np.linalg.inv(np.diag(sigmas**2))

        expected_delta = np.linalg.solve(
            jacobian.T @ precision @ jacobian,
            jacobian.T @ precision @ residual,
        )

        actual = gauss_newton_step(x, residual, jacobian, sigmas)

        np.testing.assert_allclose(actual, x + expected_delta)

    def test_bad_dimensions_raise(self) -> None:
        x = np.array([0.0, 0.0, 0.0])
        jacobian = np.eye(2)
        residual = np.array([1.0, 2.0])
        sigmas = np.array([1.0, 1.0])

        with self.assertRaises(ValueError):
            gauss_newton_step(x, residual, jacobian, sigmas)


class TestLevenbergMarquardtStep(unittest.TestCase):
    def test_one_step_linearized_update_uses_damping_and_precision(self) -> None:
        x = np.array([10.0, -5.0])
        jacobian = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        residual = np.array([1.0, 2.0, 3.0])
        sigmas = np.array([1.0, 2.0, 4.0])
        damping = 2.0
        precision = np.linalg.inv(np.diag(sigmas**2))
        normal = jacobian.T @ precision @ jacobian
        rhs = jacobian.T @ precision @ residual

        expected_delta = np.linalg.solve(normal + damping * np.eye(normal.shape[0]), rhs)
        undamped_delta = np.linalg.solve(normal, rhs)

        actual = levenberg_marquardt_step(x, residual, jacobian, sigmas, damping)

        np.testing.assert_allclose(actual, x + expected_delta)
        self.assertFalse(np.allclose(actual, x + undamped_delta))

    def test_negative_damping_raises(self) -> None:
        with self.assertRaises(ValueError):
            levenberg_marquardt_step(np.zeros(2), np.ones(2), np.eye(2), np.ones(2), -1.0)


class TestInformationFormEkfUpdate(unittest.TestCase):
    def test_one_step_update_matches_information_form_posterior(self) -> None:
        x_pred = np.array([0.0, 0.0])
        p_pred = np.diag([2.0, 3.0])
        h_pred = np.array([0.0, 0.0])
        jacobian = np.eye(2)
        z = np.array([1.0, -2.0])
        sigmas = np.array([0.5, 1.0])

        posterior_x, posterior_p = information_form_ekf_update(x_pred, p_pred, h_pred, jacobian, z, sigmas)

        precision_pred = np.linalg.inv(p_pred)
        measurement_precision = np.linalg.inv(np.diag(sigmas**2))
        expected_precision = precision_pred + jacobian.T @ measurement_precision @ jacobian
        expected_p = np.linalg.inv(expected_precision)
        expected_rhs = precision_pred @ x_pred + jacobian.T @ measurement_precision @ (z - h_pred)
        expected_x = expected_p @ expected_rhs

        np.testing.assert_allclose(posterior_p, expected_p)
        np.testing.assert_allclose(posterior_x, expected_x)

    def test_update_uses_nonzero_innovation(self) -> None:
        x_pred = np.array([0.0, 0.0])
        p_pred = np.diag([2.0, 3.0])
        h_pred = np.array([0.25, -0.5])
        jacobian = np.eye(2)
        z = np.array([1.0, -2.0])
        sigmas = np.array([0.5, 1.0])

        posterior_x, _ = information_form_ekf_update(x_pred, p_pred, h_pred, jacobian, z, sigmas)

        precision_pred = np.linalg.inv(p_pred)
        measurement_precision = np.linalg.inv(np.diag(sigmas**2))
        expected_precision = precision_pred + measurement_precision
        expected_p = np.linalg.inv(expected_precision)
        expected_rhs = measurement_precision @ (z - h_pred)
        expected_x = expected_p @ expected_rhs
        wrong_rhs_without_innovation = measurement_precision @ z
        wrong_x_without_innovation = expected_p @ wrong_rhs_without_innovation

        np.testing.assert_allclose(posterior_x, expected_x)
        self.assertFalse(np.allclose(posterior_x, wrong_x_without_innovation))

    def test_bad_dimensions_raise(self) -> None:
        with self.assertRaises(ValueError):
            information_form_ekf_update(
                np.zeros(3),
                np.eye(2),
                np.zeros(2),
                np.eye(2),
                np.ones(2),
                np.ones(2),
            )

    def test_nonpositive_sigma_raises(self) -> None:
        with self.assertRaises(ValueError):
            information_form_ekf_update(
                np.zeros(2),
                np.eye(2),
                np.zeros(2),
                np.eye(2),
                np.ones(2),
                np.array([1.0, -1.0]),
            )


if __name__ == "__main__":
    unittest.main()
