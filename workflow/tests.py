"""
Unit tests for workflow stages and migration mapping.
"""

from django.test import TestCase
from workflow.stages import (
    STAGE_ROLES,
    STAGE_DETAILS,
    OLD_TO_NEW_STAGE_MAP,
    NEW_TO_OLD_STAGE_MAP,
    MIN_STAGE,
    MAX_STAGE,
    TOTAL_STAGES,
    map_old_to_new_stage,
    map_new_to_old_stage,
    convert_allowed_stages_string,
    STAGE_1_UNIT_SELECTION,
    STAGE_2_PLAQUE_AND_COST,
    STAGE_3_FORM_J_REVIEW,
    STAGE_4_LOANS_AND_CONTRIBUTION,
    STAGE_5_SMS_CONTRIBUTION,
    STAGE_6_BANK_LETTER,
    STAGE_7_SCAN_DOCS_INSTALLMENT,
    STAGE_8_BROKERAGE_CEO,
    STAGE_9_NATIONAL_HOUSING,
    STAGE_10_FORM_J_REGISTRATION,
    STAGE_11_TECHNICAL_ENGINEERING,
    STAGE_12_REAL_ESTATE,
    STAGE_13_LAND_BANK,
    STAGE_14_LEGAL,
    STAGE_15_EVALUATION,
    STAGE_16_DECILE_CHECKS,
    STAGE_17_PREPARATION_RENT,
    STAGE_18_CONTRACTOR_SETTLEMENT,
    STAGE_19_NOTARY_LETTER,
    STAGE_20_LEASE_SCAN_PRINT,
    STAGE_21_ARCHIVE,
)


class StageMappingTestCase(TestCase):
    """Verifies that the new 21-step workflow and mappings are mathematically complete."""

    def test_stage_roles_range_and_structure(self):
        """STAGE_ROLES must have exactly 21 steps from 1 to 21."""
        self.assertEqual(len(STAGE_ROLES), 21)
        self.assertEqual(set(STAGE_ROLES.keys()), set(range(1, 22)))
        self.assertEqual(MIN_STAGE, 1)
        self.assertEqual(MAX_STAGE, 21)
        self.assertEqual(TOTAL_STAGES, 21)

        for stg, (unit, role, title) in STAGE_ROLES.items():
            self.assertIn(unit, ("brokerage", "directorate"))
            self.assertTrue(len(role) > 0)
            self.assertTrue(len(title) > 0)

    def test_stage_details_keys(self):
        """STAGE_DETAILS must match keys 1 to 21 with required descriptive fields."""
        self.assertEqual(len(STAGE_DETAILS), 21)
        self.assertEqual(set(STAGE_DETAILS.keys()), set(range(1, 22)))

        required_keys = {"title", "actor", "action", "next", "notes"}
        for stg, details in STAGE_DETAILS.items():
            self.assertTrue(required_keys.issubset(details.keys()))

    def test_old_to_new_mapping_coverage(self):
        """Every old stage from 0 to 21 must map to a valid new stage between 1 and 21."""
        self.assertEqual(len(OLD_TO_NEW_STAGE_MAP), 22)
        self.assertEqual(set(OLD_TO_NEW_STAGE_MAP.keys()), set(range(0, 22)))

        # Expected mappings per user specification:
        # 1<-0, 2<-1+2, 3<-3, 4<-4+5+6, 5<-7, 6<-8, 7<-9, 8<-10, 9<-11, 10<-16,
        # 11<-12, 12<-13, 13<-14, 14<-15, 15<-17, 16&17<-18, 18<-19, 19<-20, 21<-21
        expected = {
            0: 1,
            1: 2,
            2: 2,
            3: 3,
            4: 4,
            5: 4,
            6: 4,
            7: 5,
            8: 6,
            9: 7,
            10: 8,
            11: 9,
            12: 11,
            13: 12,
            14: 13,
            15: 14,
            16: 10,
            17: 15,
            18: 16,
            19: 18,
            20: 19,
            21: 21,
        }
        for old_stg, expected_new in expected.items():
            mapped = map_old_to_new_stage(old_stg)
            self.assertEqual(mapped, expected_new, f"Old stage {old_stg} mapped to {mapped}, expected {expected_new}")
            self.assertTrue(1 <= mapped <= 21)

    def test_new_to_old_reverse_mapping(self):
        """All new stages 1 to 21 must map back to a valid old stage 0 to 21."""
        self.assertEqual(len(NEW_TO_OLD_STAGE_MAP), 21)
        self.assertEqual(set(NEW_TO_OLD_STAGE_MAP.keys()), set(range(1, 22)))

        for new_stg, old_stg in NEW_TO_OLD_STAGE_MAP.items():
            self.assertTrue(0 <= old_stg <= 21)
            mapped_back = map_new_to_old_stage(new_stg)
            self.assertEqual(mapped_back, old_stg)

    def test_convert_allowed_stages_string(self):
        """Test converting comma-separated allowed stages for UserProfile."""
        # "all" stays "all"
        self.assertEqual(convert_allowed_stages_string("all"), "all")
        self.assertEqual(convert_allowed_stages_string("all", forward=False), "all")

        # Forward conversion: 0,1,2,10 -> 1,2,8
        forward_res = convert_allowed_stages_string("0, 1, 2, 10")
        self.assertEqual(forward_res, "1,2,8")

        # Reverse conversion: 1,2,8 -> 0,2,10
        reverse_res = convert_allowed_stages_string("1, 2, 8", forward=False)
        self.assertEqual(reverse_res, "0,2,10")

        # Empty / whitespace handling
        self.assertEqual(convert_allowed_stages_string(""), "")
        self.assertEqual(convert_allowed_stages_string(None), "all")

    def test_named_constants_values(self):
        """Named constants match their step numbers."""
        self.assertEqual(STAGE_1_UNIT_SELECTION, 1)
        self.assertEqual(STAGE_2_PLAQUE_AND_COST, 2)
        self.assertEqual(STAGE_3_FORM_J_REVIEW, 3)
        self.assertEqual(STAGE_4_LOANS_AND_CONTRIBUTION, 4)
        self.assertEqual(STAGE_5_SMS_CONTRIBUTION, 5)
        self.assertEqual(STAGE_6_BANK_LETTER, 6)
        self.assertEqual(STAGE_7_SCAN_DOCS_INSTALLMENT, 7)
        self.assertEqual(STAGE_8_BROKERAGE_CEO, 8)
        self.assertEqual(STAGE_9_NATIONAL_HOUSING, 9)
        self.assertEqual(STAGE_10_FORM_J_REGISTRATION, 10)
        self.assertEqual(STAGE_11_TECHNICAL_ENGINEERING, 11)
        self.assertEqual(STAGE_12_REAL_ESTATE, 12)
        self.assertEqual(STAGE_13_LAND_BANK, 13)
        self.assertEqual(STAGE_14_LEGAL, 14)
        self.assertEqual(STAGE_15_EVALUATION, 15)
        self.assertEqual(STAGE_16_DECILE_CHECKS, 16)
        self.assertEqual(STAGE_17_PREPARATION_RENT, 17)
        self.assertEqual(STAGE_18_CONTRACTOR_SETTLEMENT, 18)
        self.assertEqual(STAGE_19_NOTARY_LETTER, 19)
        self.assertEqual(STAGE_20_LEASE_SCAN_PRINT, 20)
        self.assertEqual(STAGE_21_ARCHIVE, 21)
