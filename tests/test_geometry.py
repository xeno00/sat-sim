import math
import unittest

import numpy as np

from jcls_sim.geometry import (
    GroundReference,
    ecef_from_enu_offset_m,
    elevation_deg,
    generate_ue_disk_geometry,
    lla_to_ecef_m,
    manuscript_candidate_geometry,
)


class TestManuscriptCandidateGeometry(unittest.TestCase):
    def test_lla_to_ecef_equator_prime_meridian(self) -> None:
        ecef = lla_to_ecef_m(0.0, 0.0, 0.0)

        np.testing.assert_allclose(ecef, np.array([6_378_137.0, 0.0, 0.0]), rtol=0.0, atol=1e-6)

    def test_enu_offset_distance_is_meter_scaled(self) -> None:
        reference = GroundReference(42.361145, -71.09085, 20.0)
        origin = lla_to_ecef_m(reference.latitude_deg, reference.longitude_deg, reference.altitude_m)
        shifted = ecef_from_enu_offset_m(reference, 300.0, 400.0)

        self.assertAlmostEqual(float(np.linalg.norm(shifted - origin)), 500.0, delta=1e-6)

    def test_ue_disk_geometry_is_reproducible_and_within_radius(self) -> None:
        reference = GroundReference(42.361145, -71.09085, 20.0)
        positions_a, metadata_a = generate_ue_disk_geometry(reference=reference, num_users=7, radius_m=500.0, seed=123)
        positions_b, metadata_b = generate_ue_disk_geometry(reference=reference, num_users=7, radius_m=500.0, seed=123)

        np.testing.assert_allclose(positions_a, positions_b)
        self.assertEqual(metadata_a, metadata_b)
        self.assertEqual(positions_a.shape, (7, 3))
        self.assertTrue(all(record["radius_from_reference_m"] <= 500.0 for record in metadata_a))

    def test_synthetic_visible_satellites_meet_elevation_mask(self) -> None:
        reference = GroundReference(42.361145, -71.09085, 20.0)
        geometry = manuscript_candidate_geometry(
            num_users=3,
            num_satellites=8,
            seed=456,
            reference=reference,
            ue_radius_m=500.0,
            minimum_elevation_deg=30.0,
            satellite_pool_size=24,
            satellite_altitude_km=550.0,
        )

        self.assertEqual(geometry.satellite_positions_km.shape, (8, 3))
        self.assertEqual(geometry.ue_positions_km.shape, (3, 3))
        visibility = geometry.metadata["visibility"]
        self.assertGreaterEqual(visibility["geometrically_visible_satellites"], 8)
        self.assertEqual(visibility["selected_satellites"], 8)
        reference_ecef_m = lla_to_ecef_m(reference.latitude_deg, reference.longitude_deg, reference.altitude_m)
        for satellite in geometry.satellite_positions_km:
            self.assertGreaterEqual(elevation_deg(reference_ecef_m, satellite * 1000.0), 30.0)

    def test_mit_stata_reference_is_finite_and_earth_scaled(self) -> None:
        reference = GroundReference(42.361145, -71.09085, 20.0)
        ecef_km = lla_to_ecef_m(reference.latitude_deg, reference.longitude_deg, reference.altitude_m) / 1000.0

        self.assertTrue(np.all(np.isfinite(ecef_km)))
        self.assertTrue(6300.0 < float(np.linalg.norm(ecef_km)) < 6400.0)


if __name__ == "__main__":
    unittest.main()
