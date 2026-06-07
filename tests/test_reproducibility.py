import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from jcls_sim.configs import V24ScenarioConfig, tiny_v24_reproducibility_config
from scripts.smoke_v24_package import (
    build_v24_smoke_diagnostics,
    write_v24_smoke_diagnostics,
)


class TestV24ReproducibilityConfig(unittest.TestCase):
    def test_tiny_config_encodes_v24_reference_convention(self) -> None:
        config = tiny_v24_reproducibility_config(seed=123)

        config.validate()

        self.assertEqual(config.num_users, 2)
        self.assertEqual(config.num_satellites, 2)
        self.assertEqual(config.seed, 123)
        self.assertEqual(config.theta().shape, (9,))
        self.assertEqual(config.full_clock_dict_km(), {1: 0.1, 2: -0.2, 3: 0.0, 4: 0.5})
        self.assertEqual(len(config.links), len(config.range_std_devs_km))

    def test_config_validation_rejects_bad_shapes(self) -> None:
        config = tiny_v24_reproducibility_config()
        bad_config = V24ScenarioConfig(
            scenario_name=config.scenario_name,
            num_users=config.num_users,
            num_satellites=config.num_satellites,
            seed=config.seed,
            ue_positions_km=config.ue_positions_km,
            satellite_positions_km=config.satellite_positions_km,
            ue_clock_offsets_km=np.array([0.0]),
            non_reference_satellite_clock_offsets_km=config.non_reference_satellite_clock_offsets_km,
            links=config.links,
            range_std_devs_km=config.range_std_devs_km,
        )

        with self.assertRaisesRegex(ValueError, "ue_clock_offsets_km"):
            bad_config.validate()


class TestV24SmokeRunner(unittest.TestCase):
    def test_repeated_runs_with_same_seed_are_identical(self) -> None:
        config = tiny_v24_reproducibility_config(seed=98765)

        first = build_v24_smoke_diagnostics(config)
        second = build_v24_smoke_diagnostics(config)

        self.assertEqual(first, second)

    def test_different_seed_changes_deterministic_noise(self) -> None:
        first = build_v24_smoke_diagnostics(tiny_v24_reproducibility_config(seed=1))
        second = build_v24_smoke_diagnostics(tiny_v24_reproducibility_config(seed=2))

        self.assertNotEqual(first["measurement_noise_km"], second["measurement_noise_km"])
        self.assertEqual(first["parameter_dim"], second["parameter_dim"])
        self.assertEqual(first["fim_rank"], second["fim_rank"])

    def test_schema_and_v24_gauge_fields(self) -> None:
        payload = build_v24_smoke_diagnostics(tiny_v24_reproducibility_config(seed=101))

        required_keys = {
            "diagnostic_type",
            "schema_version",
            "scenario_name",
            "seed",
            "num_users",
            "num_satellites",
            "reference_clock_convention",
            "used_reference_satellite_node_id",
            "reference_clock_column_present",
            "parameter_dim",
            "expected_parameter_dim",
            "measurement_count",
            "range_std_devs_km",
            "fim_shape",
            "fim_rank",
            "fim_min_eigenvalue",
            "clock_metric_km",
            "gn_update_norm",
            "lm_update_norm",
            "ekf_update_norm",
            "position_error_m",
            "output_note",
        }
        self.assertTrue(required_keys.issubset(payload))
        self.assertEqual(payload["diagnostic_type"], "non_final_v24_package_smoke")
        self.assertEqual(payload["used_reference_satellite_node_id"], 3)
        self.assertFalse(payload["reference_clock_column_present"])
        self.assertEqual(payload["parameter_dim"], 9)
        self.assertEqual(payload["expected_parameter_dim"], 9)
        self.assertEqual(payload["fim_shape"], [9, 9])
        self.assertGreaterEqual(payload["fim_min_eigenvalue"], -1e-10)

    def test_json_write_is_deterministic_and_non_overwriting(self) -> None:
        config = tiny_v24_reproducibility_config(seed=2468)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "smoke.json"

            written = write_v24_smoke_diagnostics(output, config=config)
            first_text = output.read_text(encoding="utf-8")
            loaded = json.loads(first_text)

            self.assertEqual(written, output)
            self.assertEqual(loaded["seed"], 2468)
            self.assertEqual(loaded["scenario_name"], "tiny_v24_package_smoke")
            with self.assertRaises(FileExistsError):
                write_v24_smoke_diagnostics(output, config=config)

            write_v24_smoke_diagnostics(output, config=config, overwrite=True)
            self.assertEqual(output.read_text(encoding="utf-8"), first_text)


if __name__ == "__main__":
    unittest.main()
