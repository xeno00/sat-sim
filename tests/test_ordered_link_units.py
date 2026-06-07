import unittest

import numpy as np

from jcls_sim.constants import C_KM_PER_S, C_M_PER_S
from jcls_sim.configs import V24ScenarioConfig
from jcls_sim.jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from jcls_sim.measurements import toa_range_model_km
from jcls_sim.parameters import pack_v24_theta


class TestOrderedLinkAndUnits(unittest.TestCase):
    def test_unique_clock_values_detect_receiver_transmitter_swap(self) -> None:
        num_users = 2
        num_satellites = 2
        ue_clocks = np.array([0.11, -0.23])
        sat_clocks = np.array([0.37])
        receiver = 1
        transmitter = 4
        rx_pos = np.array([1.0, 2.0, 3.0])
        tx_pos = np.array([8.0, -1.0, 5.0])

        forward = toa_range_model_km(
            receiver,
            transmitter,
            rx_pos,
            tx_pos,
            ue_clocks,
            sat_clocks,
            num_users,
            num_satellites,
        )
        swapped = toa_range_model_km(
            transmitter,
            receiver,
            tx_pos,
            rx_pos,
            ue_clocks,
            sat_clocks,
            num_users,
            num_satellites,
        )

        self.assertAlmostEqual(forward - swapped, 2.0 * (sat_clocks[0] - ue_clocks[0]))

    def test_jacobian_clock_columns_follow_receiver_transmitter_order(self) -> None:
        num_users = 2
        num_satellites = 2
        theta = pack_v24_theta(
            np.array([[0.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
            np.array([0.1, -0.2]),
            np.array([0.4]),
        )
        sat_pos = np.array([[0.0, 10.0, 0.0], [10.0, 0.0, 0.0]])
        links = ((1, 4), (2, 1))

        jac = analytic_toa_jacobian_km(theta, links, sat_pos, num_users, num_satellites)

        # Theta order is [p1, p2, delta_1, delta_2, delta_4] for Nu=2,Ns=2.
        self.assertEqual(jac[0, 6], -1.0)
        self.assertEqual(jac[0, 8], 1.0)
        self.assertEqual(jac[1, 7], -1.0)
        self.assertEqual(jac[1, 6], 1.0)

    def test_m_seconds_and_km_range_clock_models_match_after_conversion(self) -> None:
        receiver_position_m = np.array([1000.0, 2000.0, 500.0])
        transmitter_position_m = np.array([4000.0, -1000.0, 1500.0])
        receiver_clock_s = 2.0e-9
        transmitter_clock_s = -5.0e-9
        expected_m = np.linalg.norm(receiver_position_m - transmitter_position_m) + C_M_PER_S * (
            transmitter_clock_s - receiver_clock_s
        )

        got_km = toa_range_model_km(
            1,
            3,
            receiver_position_m / 1000.0,
            transmitter_position_m / 1000.0,
            np.array([receiver_clock_s * C_KM_PER_S]),
            np.array([transmitter_clock_s * C_KM_PER_S]),
            1,
            2,
        )

        self.assertAlmostEqual(got_km * 1000.0, expected_m)

    def test_clock_sigma_seconds_to_km_round_trip(self) -> None:
        sigma_s = 1.0e-6
        sigma_km = sigma_s * C_KM_PER_S

        self.assertAlmostEqual(sigma_km / C_KM_PER_S, sigma_s)

    def test_scenario_row_order_matches_measurement_and_jacobian(self) -> None:
        scenario = V24ScenarioConfig(
            scenario_name="ordered_link_test",
            num_users=2,
            num_satellites=2,
            seed=1,
            ue_positions_km=np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 0.5]]),
            satellite_positions_km=np.array([[0.0, 5.0, 10.0], [7.0, 1.0, 12.0]]),
            ue_clock_offsets_km=np.array([0.01, -0.02]),
            non_reference_satellite_clock_offsets_km=np.array([0.05]),
            links=((1, 3), (2, 4), (1, 2), (2, 1)),
            range_std_devs_km=np.ones(4),
        )
        theta = scenario.theta()
        values = toa_range_vector_from_theta_km(
            theta,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        jac = analytic_toa_jacobian_km(
            theta,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )

        self.assertEqual(values.shape, (len(scenario.links),))
        self.assertEqual(jac.shape[0], len(scenario.links))
        self.assertTrue(np.all(np.isfinite(values)))
        self.assertTrue(np.all(np.isfinite(jac)))


if __name__ == "__main__":
    unittest.main()
