import json
import unittest

from jcls_sim.benchmark.standard_cases import (
    PRIMARY_STANDARD_CASE_ID,
    SECONDARY_LOW_SATELLITE_STRESS_CASE_ID,
    StandardCaseSpec,
    get_standard_case,
    is_primary_standard_case,
    primary_standard_case,
    secondary_low_satellite_stress_case,
    standard_cases,
)


class StandardCaseTests(unittest.TestCase):
    def test_primary_standard_case_is_nu3_ns10(self) -> None:
        case = primary_standard_case()

        self.assertEqual(case.case_id, PRIMARY_STANDARD_CASE_ID)
        self.assertEqual(case.role, "primary_standard")
        self.assertEqual(case.num_users, 3)
        self.assertEqual(case.num_satellites, 10)
        self.assertEqual(case.sidelink_graph, "full_mesh")
        self.assertEqual(case.clock_std_seconds, 1.0e-6)
        self.assertEqual(case.seed, 0)
        self.assertEqual(case.operation_time_seconds, 0.5)
        self.assertEqual(case.trial_count, 1)
        json.dumps(case.to_dict())

    def test_secondary_stress_case_is_not_primary(self) -> None:
        case = secondary_low_satellite_stress_case()

        self.assertEqual(case.case_id, SECONDARY_LOW_SATELLITE_STRESS_CASE_ID)
        self.assertEqual(case.role, "secondary_low_satellite_stress")
        self.assertEqual(case.num_users, 3)
        self.assertEqual(case.num_satellites, 4)
        self.assertFalse(is_primary_standard_case(case.case_id))
        self.assertNotEqual(primary_standard_case().case_id, case.case_id)

    def test_standard_cases_are_distinct_and_lookupable(self) -> None:
        cases = standard_cases()
        case_ids = {case.case_id for case in cases}

        self.assertEqual(case_ids, {PRIMARY_STANDARD_CASE_ID, SECONDARY_LOW_SATELLITE_STRESS_CASE_ID})
        self.assertEqual(get_standard_case(PRIMARY_STANDARD_CASE_ID).role, "primary_standard")
        self.assertEqual(get_standard_case(SECONDARY_LOW_SATELLITE_STRESS_CASE_ID).role, "secondary_low_satellite_stress")
        with self.assertRaisesRegex(KeyError, "Unknown standard case"):
            get_standard_case("not_a_case")

    def test_standard_case_validation_rejects_bad_role_and_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "role"):
            StandardCaseSpec(
                case_id="bad",
                role="primary",
                num_users=3,
                num_satellites=10,
                sidelink_graph="full_mesh",
                clock_std_seconds=1.0e-6,
                seed=0,
                operation_time_seconds=0.5,
                trial_count=1,
                channel_model="LOS/Rician when supported",
                geometry_model="manuscript-like",
                notes="bad role",
            )
        with self.assertRaisesRegex(ValueError, "clock_std_seconds"):
            StandardCaseSpec(
                case_id="bad",
                role="diagnostic",
                num_users=3,
                num_satellites=10,
                sidelink_graph="full_mesh",
                clock_std_seconds=0.0,
                seed=0,
                operation_time_seconds=0.5,
                trial_count=1,
                channel_model="LOS/Rician when supported",
                geometry_model="manuscript-like",
                notes="bad clock",
            )


if __name__ == "__main__":
    unittest.main()
