import unittest

import numpy as np

from jcls_sim.configs import directed_sidelink_links, downlink_links
from jcls_sim.noise import (
    LinkBudgetConfig,
    fspl_db,
    range_sigma_km_from_snr,
    range_sigmas_for_links,
)


class TestManuscriptCandidateNoise(unittest.TestCase):
    def test_fspl_known_scale(self) -> None:
        self.assertAlmostEqual(fspl_db(1.0, 1.0e9), 92.44, delta=0.05)

    def test_range_sigma_formula_is_meter_then_kilometer_scaled(self) -> None:
        sigma_km = range_sigma_km_from_snr(100.0, 20.0e6)

        self.assertGreater(sigma_km, 0.0)
        self.assertLess(sigma_km * 1000.0, 1.0)

    def test_dl_sl_link_budget_sigmas_are_positive_and_ordered(self) -> None:
        ue_positions = np.array([[0.0, 0.0, 0.0], [0.3, 0.0, 0.0]], dtype=float)
        satellite_positions = np.array([[500.0, 0.0, 550.0], [600.0, 50.0, 560.0]], dtype=float)
        links = downlink_links(2, 2) + directed_sidelink_links(2)

        sigmas, records, summary = range_sigmas_for_links(
            ue_positions_km=ue_positions,
            satellite_positions_km=satellite_positions,
            links=links,
            num_users=2,
            config=LinkBudgetConfig(),
        )

        self.assertEqual(sigmas.shape, (len(links),))
        self.assertTrue(np.all(sigmas > 0.0))
        self.assertEqual([record["link_index"] for record in records], list(range(len(links))))
        self.assertIn("dl_range_sigma_m_min", summary)
        self.assertIn("sl_range_sigma_m_min", summary)
        self.assertNotEqual(summary["dl_range_sigma_km_min"], summary["sl_range_sigma_km_min"])

    def test_no_double_c_in_sigma_seconds_conversion(self) -> None:
        sigma_km = range_sigma_km_from_snr(10.0, 40.0e6)

        self.assertLess(sigma_km, 1e-3)


if __name__ == "__main__":
    unittest.main()
