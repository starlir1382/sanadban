"""
workflow/test_print_and_permissions.py
Tests for:
1. Print summary signature rules (only sign papers after مرحله 7; audit log only before مرحله 7).
2. Numbering: shows 'ردیف {id}' before stage 8; official archive_number for stage >= 8.
3. Editability of بخش 1 and بخش 2 for both users of مرحله 8 and مرحله 9.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User

from workflow.models import HousingDossier, UserProfile, WorkflowSignatureLog
from workflow.views import get_dossier_signatures_summary
from workflow.field_permissions import can_user_edit_field, filter_allowed_updates


class PrintSummaryAndPermissionsTestCase(TestCase):
    def setUp(self):
        # Users for stage 8 and stage 9
        self.user_stage_8 = User.objects.create_user(username="expert_stg8", password="password123")
        self.prof_stg8, _ = UserProfile.objects.get_or_create(user=self.user_stage_8)
        self.prof_stg8.allowed_stages = "8"
        self.prof_stg8.full_name = "کارشناس ممیزی ره آزرم"
        self.prof_stg8.save()

        self.user_stage_9 = User.objects.create_user(username="ceo_stg9", password="password123")
        self.prof_stg9, _ = UserProfile.objects.get_or_create(user=self.user_stage_9)
        self.prof_stg9.allowed_stages = "9"
        self.prof_stg9.full_name = "مدیرعامل کارگزاری ره آزرم"
        self.prof_stg9.save()

    def test_signatures_on_paper_only_after_stage_7(self):
        """Before مرحله 7, no one signs paper; only record their log."""
        dossier = HousingDossier.objects.create(
            national_id="0011223344",
            full_name="متقاضی مرحله ۳",
            current_stage=3,
        )
        # Add audit logs for stages 1, 2, 4, 5, 6
        WorkflowSignatureLog.objects.create(
            dossier=dossier,
            from_stage="مرحله 4: ورود تسهیلات و تعیین آورده",
            to_stage="مرحله 5: ارسال پیامک آورده نقدی",
            actor="کارشناس تسهیلات",
            action="SIGN",
            action_label="تایید و امضا",
        )
        WorkflowSignatureLog.objects.create(
            dossier=dossier,
            from_stage="مرحله 6: تایید آورده و معرفی به بانک",
            to_stage="مرحله 7: اسکن مدارک و تشکیل پرونده",
            actor="کارشناس بانک",
            action="SIGN",
            action_label="تایید و امضا",
        )

        # In summary print for dossier at stage 3 (<= 7):
        sigs, count = get_dossier_signatures_summary(dossier)
        self.assertEqual(sigs, {})
        self.assertEqual(count, 0)

        # Now advance dossier to stage 10 (after stage 7) and log stage 9 signature
        dossier.current_stage = 10
        dossier.save()
        WorkflowSignatureLog.objects.create(
            dossier=dossier,
            from_stage="مرحله 9: تأیید مدیرعامل کارگزاری (رئیس)",
            to_stage="مرحله 10: بررسی کارشناس نهضت ملی مسکن",
            actor="مدیرعامل کارگزاری ره آزرم",
            action="SIGN",
            action_label="تایید و امضا",
        )

        sigs_10, count_10 = get_dossier_signatures_summary(dossier)
        # Brokerage stamp (stage 9) should be present
        self.assertIn("brokerage", sigs_10)
        self.assertEqual(sigs_10["brokerage"].signer_name, "مدیرعامل کارگزاری ره آزرم")
        # Stages 4 and 6 should NOT be on the paper
        self.assertNotIn("other_facilities", sigs_10)
        self.assertNotIn("applicant_settlement", sigs_10)

    def test_numbering_before_and_after_stage_8(self):
        """Before stage 8, shows 'ردیف {id}'; after stage 8, shows official archive_number."""
        d_stg1 = HousingDossier.objects.create(
            national_id="0099887766",
            full_name="متقاضی مرحله ۱",
            current_stage=1,
            archive_number=100500,
        )
        self.assertEqual(d_stg1.display_number, f"ردیف {d_stg1.id}")
        self.assertFalse(d_stg1.is_numbered_archive)

        d_stg8 = HousingDossier.objects.create(
            national_id="0099887755",
            full_name="متقاضی مرحله ۸",
            current_stage=8,
            archive_number=100501,
        )
        self.assertEqual(d_stg8.display_number, "100501")
        self.assertTrue(d_stg8.is_numbered_archive)

    def test_section_1_and_2_editable_for_stage_8_and_stage_9(self):
        """Users of stage 8 and stage 9 can edit all fields of بخش ۱ and بخش ۲."""
        section_1_fields = [
            "national_id", "first_name", "last_name", "full_name", "father_name",
            "birth_date", "applicant_phone", "applicant_id_number", "marital_status",
            "spouse_first_name", "spouse_last_name", "spouse_full_name", "spouse_national_id",
            "site", "project", "block_name", "block_code", "floor_number", "unit_number",
            "net_unit_area", "common_area", "total_area", "storage_area", "parking_area",
        ]
        section_2_fields = [
            "registration_section", "main_plaque", "separated_plaque", "sub_plaque",
            "plot_number", "renovation_code", "base_cost_without_loan",
        ]

        # Stage 8 user check
        for f in section_1_fields + section_2_fields:
            self.assertTrue(
                can_user_edit_field(self.user_stage_8, f),
                f"Field '{f}' should be editable by user of stage 8"
            )

        # Stage 9 user check
        for f in section_1_fields + section_2_fields:
            self.assertTrue(
                can_user_edit_field(self.user_stage_9, f),
                f"Field '{f}' should be editable by user of stage 9"
            )

    def test_address_and_new_fields_and_permissions(self):
        """Address and contact fields are editable in stages 1, 8, 9 and persisted."""
        for f in ["applicant_address", "applicant_postal_code", "applicant_landline_phone", "applicant_id_serial", "spouse_id_serial"]:
            self.assertTrue(can_user_edit_field(self.user_stage_8, f), f"Field {f} should be editable in stage 8")
            self.assertTrue(can_user_edit_field(self.user_stage_9, f), f"Field {f} should be editable in stage 9")

        dossier = HousingDossier.objects.create(
            national_id="0088776655",
            full_name="حمیدرضا رحمانی قدسی",
            archive_number=100600,
            current_stage=8,
            applicant_address="قم، بلوار ۱۵ خرداد، کوچه ۱۷، پلاک ۲۰",
            applicant_postal_code="3717665868",
            applicant_landline_phone="02538740652",
            applicant_phone="09126532091",
            applicant_id_serial="819059",
            spouse_id_serial="408929",
            spouse_first_name="مریم",
            spouse_last_name="صمدی",
            project="27 هکتاری سارینا آفرین",
            block_code="22",
            floor_number=3,
            unit_number=12,
        )

        self.assertEqual(dossier.applicant_address, "قم، بلوار ۱۵ خرداد، کوچه ۱۷، پلاک ۲۰")
        self.assertEqual(dossier.applicant_postal_code, "3717665868")

    def test_generate_affidavit_and_info_form_and_print_views(self):
        """Generate doc endpoints add files to attachments, tick checkboxes, and render print views."""
        dossier = HousingDossier.objects.create(
            national_id="0384316468",
            first_name="حمیدرضا",
            last_name="رحمانی قدسی",
            full_name="حمیدرضا رحمانی قدسی",
            father_name="عباس",
            archive_number=100601,
            current_stage=8,
            applicant_address="قم، بلوار ۱۵ خرداد، کوچه ۱۷، پلاک ۲۰",
            applicant_phone="09126532091",
            spouse_first_name="مریم",
            spouse_last_name="صمدی",
            spouse_national_id="0602647908",
            project="27 هکتاری سارینا آفرین",
            block_code="22",
            floor_number=3,
            unit_number=12,
        )

        client = Client()
        client.force_login(self.user_stage_8)

        # 1. Generate Affidavit
        res1 = client.post(f"/dossier/{dossier.archive_number}/generate-doc/affidavit/")
        self.assertEqual(res1.status_code, 200)
        dossier.refresh_from_db()
        self.assertTrue(dossier.has_affidavit)
        att1 = dossier.attachments.filter(doc_type="AFFIDAVIT").first()
        self.assertIsNotNone(att1)
        self.assertIn("affidavit", att1.preview_url)

        # 2. Generate Info Form
        res2 = client.post(f"/dossier/{dossier.archive_number}/generate-doc/info_form/")
        self.assertEqual(res2.status_code, 200)
        dossier.refresh_from_db()
        self.assertTrue(dossier.has_info_form)
        att2 = dossier.attachments.filter(doc_type="INFO_FORM").first()
        self.assertIsNotNone(att2)
        self.assertTrue("info_form" in att2.preview_url or "info-form" in att2.preview_url)

        # 3. Print Affidavit View
        res_print1 = client.get(f"/dossier/{dossier.archive_number}/print/affidavit/")
        self.assertEqual(res_print1.status_code, 200)
        content1 = res_print1.content.decode("utf-8")
        self.assertIn("حمیدرضا رحمانی قدسی", content1)
        self.assertIn("0384316468", content1)
        self.assertIn("قم، بلوار ۱۵ خرداد", content1)
        self.assertIn("27 هکتاری سارینا آفرین", content1)

        # 4. Print Info Form View
        res_print2 = client.get(f"/dossier/{dossier.archive_number}/print/info-form/")
        self.assertEqual(res_print2.status_code, 200)
        content2 = res_print2.content.decode("utf-8")
        self.assertIn("حمیدرضا", content2)
        self.assertIn("رحمانی قدسی", content2)
        self.assertIn("مریم", content2)
        self.assertIn("صمدی", content2)
        self.assertIn("قم، بلوار ۱۵ خرداد", content2)

    def test_naming_convention_with_national_id_and_arse(self):
        """Scans for deed, affidavit, info_form, and checks use national_id and 'arse' naming."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        dossier = HousingDossier.objects.create(
            national_id="0384316468",
            full_name="حمیدرضا رحمانی",
            archive_number=100602,
            current_stage=8,
        )

        client = Client()
        client.force_login(self.user_stage_8)

        # Upload deed (TITLE_DEED) -> must be named {national_id}_arse.jpg
        dummy_file = SimpleUploadedFile("random_sample.jpg", b"dummy image content", content_type="image/jpeg")
        res = client.post(
            f"/dossier/{dossier.archive_number}/upload-scan/",
            {"doc_type": "TITLE_DEED", "files": [dummy_file]}
        )
        self.assertEqual(res.status_code, 200)
        att_deed = dossier.attachments.filter(doc_type="TITLE_DEED").first()
        self.assertIsNotNone(att_deed)
        self.assertIn("0384316468_arse.jpg", att_deed.file_name)
        self.assertIn("اسکن سند عرصه", att_deed.title)

        # Upload check scan (PREP_CHECK)
        chk_file = SimpleUploadedFile("check1.jpg", b"check content", content_type="image/jpeg")
        res_chk = client.post(
            f"/dossier/{dossier.archive_number}/checks/upload-scan-and-create-receipt/",
            {"check_type": "prep", "file": chk_file}
        )
        self.assertEqual(res_chk.status_code, 200)
        att_chk = dossier.attachments.filter(doc_type="PREP_CHECK").first()
        self.assertIsNotNone(att_chk)
        self.assertIn("0384316468_prep_check_1.jpg", att_chk.file_name)
        self.assertIn("چک آماده‌سازی (0384316468)", att_chk.title)

    def test_land_bank_and_checks_print_auto_archive(self):
        """Printing land-bank (سند عرصه) and checks automatically creates attachments in scan album."""
        dossier = HousingDossier.objects.create(
            national_id="0384316468",
            full_name="حمیدرضا رحمانی",
            archive_number=100603,
            current_stage=8,
        )

        client = Client()
        client.force_login(self.user_stage_8)

        # 1. Print Land Bank (سند عرصه)
        res_arse = client.get(f"/dossier/{dossier.archive_number}/print/land-bank/")
        self.assertEqual(res_arse.status_code, 200)
        dossier.refresh_from_db()
        self.assertTrue(dossier.is_land_deed_confirmed)
        att_arse = dossier.attachments.filter(doc_type="TITLE_DEED").first()
        self.assertIsNotNone(att_arse)
        self.assertIn("0384316468_arse", att_arse.file_name)
        self.assertEqual(att_arse.title, "اسکن سند عرصه - 0384316468")

        # 2. Print Checks (چک تسهیلات وام)
        res_chk_loan = client.get(f"/dossier/{dossier.archive_number}/print/checks/?type=loan")
        self.assertEqual(res_chk_loan.status_code, 200)
        att_chk_loan = dossier.attachments.filter(doc_type="LOAN_CHECK", preview_url__contains="/print/checks/").first()
        self.assertIsNotNone(att_chk_loan)
        self.assertEqual(att_chk_loan.file_name, "0384316468_loan_receipt.html")
        self.assertIn("0384316468", att_chk_loan.title)



