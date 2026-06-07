import unittest

import numpy as np

from jcls_sim.algorithm import (
    coarse_individual_localization,
    dynamic_soft_information_refinement,
    identity_theta_state_model,
    joint_lm_jcls,
)
from jcls_sim.configs import V24ScenarioConfig, downlink_links, directed_sidelink_links
from jcls_sim.gauge import expected_v24_parameter_dim
from jcls_sim.jacobian import toa_range_vector_from_theta_km
from jcls_sim.parameters import pack_v24_theta, unpack_v24_theta


def _single_user_dl_scenario(num_satellites: int = 4) -> V24ScenarioConfig:
    satellite_positions = np.array(
        [
            [10.0, 0.0, 0.0],
            [0.0, 11.0, 0.0],
            [0.0, 0.0, 12.0],
            [-9.0, -8.0, 7.0],
        ],
        dtype=float,
    )[:num_satellites]
    return V24ScenarioConfig(
        scenario_name="algorithm_single_user_dl",
        num_users=1,
        num_satellites=num_satellites,
        seed=1,
        ue_positions_km=np.zeros((1, 3), dtype=float),
        satellite_positions_km=satellite_positions,
        ue_clock_offsets_km=np.zeros(1, dtype=float),
        non_reference_satellite_clock_offsets_km=np.zeros(num_satellites - 1, dtype=float),
        links=downlink_links(1, num_satellites),
        range_std_devs_km=np.full(num_satellites, 0.01, dtype=float),
    )


def _joint_scenario() -> V24ScenarioConfig:
    num_users = 2
    num_satellites = 6
    satellite_positions = np.array(
        [
            [9.0, 0.0, 11.0],
            [0.0, 8.0, 12.0],
            [-8.0, 0.5, 13.0],
            [1.5, -7.0, 14.0],
            [6.0, 5.5, 15.0],
            [-5.0, -4.5, 16.0],
        ],
        dtype=float,
    )
    links = downlink_links(num_users, num_satellites) + directed_sidelink_links(num_users)
    return V24ScenarioConfig(
        scenario_name="algorithm_joint",
        num_users=num_users,
        num_satellites=num_satellites,
        seed=2,
        ue_positions_km=np.array(
            [
                [0.1, -0.2, 0.05],
                [1.0, 0.8, -0.1],
            ],
            dtype=float,
        ),
        satellite_positions_km=satellite_positions,
        ue_clock_offsets_km=np.array([0.03, -0.02], dtype=float),
        non_reference_satellite_clock_offsets_km=np.array([0.04, -0.03, 0.02, 0.01, -0.015], dtype=float),
        links=links,
        range_std_devs_km=np.full(len(links), 0.02, dtype=float),
    )


class TestV24AlgorithmStages(unittest.TestCase):
    def test_identity_theta_state_model_has_explicit_f_q_pi(self) -> None:
        model = identity_theta_state_model(9, process_noise_std_km=1e-4)

        self.assertEqual(model.f_matrix.shape, (9, 9))
        self.assertEqual(model.pi_matrix.shape, (9, 9))
        np.testing.assert_allclose(model.f_matrix, np.eye(9))
        np.testing.assert_allclose(model.pi_matrix, np.eye(9))
        np.testing.assert_allclose(np.diag(model.q_covariance), np.full(9, 1e-8))
        model.validate(9)

    def test_step1_coarse_dl_localization_uses_precision_and_no_truth_init(self) -> None:
        scenario = _single_user_dl_scenario()
        z = toa_range_vector_from_theta_km(
            scenario.theta(),
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )

        result = coarse_individual_localization(scenario, z)
        positions, ue_clocks, sat_clocks = unpack_v24_theta(
            result.theta,
            scenario.num_users,
            scenario.num_satellites,
        )

        self.assertTrue(result.success)
        self.assertFalse(result.diagnostics["truth_centered_initialization"])
        np.testing.assert_allclose(positions, scenario.ue_positions_km, atol=1e-8)
        np.testing.assert_allclose(ue_clocks, np.zeros(1))
        np.testing.assert_allclose(sat_clocks, np.zeros(3))

    def test_step1_reports_rank_deficient_dl_geometry(self) -> None:
        scenario = _single_user_dl_scenario(num_satellites=2)
        z = toa_range_vector_from_theta_km(
            scenario.theta(),
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )

        result = coarse_individual_localization(scenario, z)

        self.assertFalse(result.success)
        self.assertEqual(result.diagnostics["users"][0]["status"], "rank_deficient_dl_geometry")

    def test_step2_weighted_lm_uses_full_gauged_theta(self) -> None:
        scenario = _joint_scenario()
        truth = scenario.theta()
        z = toa_range_vector_from_theta_km(
            truth,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        initial = truth + np.linspace(0.01, -0.01, truth.size)

        result = joint_lm_jcls(scenario, z, initial)

        self.assertEqual(result.theta.shape, (expected_v24_parameter_dim(2, 6),))
        self.assertTrue(result.success)
        self.assertTrue(result.diagnostics["uses_precision_weighting"])
        self.assertFalse(result.diagnostics["reference_satellite_clock_in_state"])
        self.assertLess(np.linalg.norm(result.theta - truth), np.linalg.norm(initial - truth))

    def test_step3_dynamic_update_uses_f_q_pi_and_innovation(self) -> None:
        scenario = _joint_scenario()
        truth = scenario.theta()
        z = toa_range_vector_from_theta_km(
            truth,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        initial = truth + np.linspace(0.02, -0.02, truth.size)
        initial_cov = 0.1 * np.eye(truth.size)

        result = dynamic_soft_information_refinement(
            scenario,
            [z, z],
            initial,
            initial_covariance=initial_cov,
            process_noise_std_km=1e-4,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.diagnostics["state_model"], "theta_identity_state")
        self.assertEqual(result.diagnostics["pi_shape"], [truth.size, truth.size])
        self.assertTrue(result.diagnostics["uses_innovation_z_minus_h_pred"])
        self.assertFalse(result.diagnostics["truth_derived_covariance"])
        self.assertGreater(result.diagnostics["epochs"][0]["innovation_norm"], 0.0)
        self.assertEqual(result.covariance.shape, (truth.size, truth.size))
        self.assertTrue(np.all(np.isfinite(result.theta)))
        self.assertTrue(np.all(np.isfinite(result.covariance)))


if __name__ == "__main__":
    unittest.main()
