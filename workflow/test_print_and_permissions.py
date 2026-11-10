"""
workflow/test_print_and_permissions.py
Tests for:
1. Print summary signature rules (only sign papers after مرحله 7; audit log only before مرحله 7).
2. Numbering: shows 'ردیف {id}' before stage 8; official archive_number for stage >= 8.
3. Editability of بخش 1 and بخش 2 for both users of مرحله 8 and مرحله 9.
"""
from decimal import Decimal
from io import BytesIO
import tempfile
from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User

from workflow.models import DossierAttachment, HousingDossier, UserProfile, WorkflowSignatureLog
from workflow.views import (
    _begin_upload_token,
    _release_upload_token,
    get_dossier_signatures_summary,
)
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

    def test_stage_7_sign_returns_archive_number_for_post_sign_display(self):
        """Signing Stage 7 advances to Stage 8 and returns archive_number & prev_stage for modal display."""
        user_stg7 = User.objects.create_user(username="expert_stg7", password="password123")
        prof7, _ = UserProfile.objects.get_or_create(user=user_stg7)
        prof7.allowed_stages = "7"
        prof7.can_sign = True
        prof7.full_name = "کارشناس تشکیل پرونده"
        prof7.save()

        d = HousingDossier.objects.create(
            national_id="0387777771",
            full_name="متقاضی مرحله هفت",
            archive_number=100777,
            current_stage=7,
        )
        self.assertFalse(d.is_numbered_archive)

        client = Client()
        client.force_login(user_stg7)
        res = client.post(
            f"/dossier/{d.archive_number}/sign/",
            data='{"notes": "تایید مرحله ۷"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["prev_stage"], 7)
        self.assertEqual(payload["new_stage"], 8)
        self.assertEqual(payload["archive_number"], 100777)
        self.assertEqual(payload["full_name"], "متقاضی مرحله هفت")

        d.refresh_from_db()
        self.assertEqual(d.current_stage, 8)
        self.assertTrue(d.is_numbered_archive)

    def test_stage_7_batch_sign_returns_signed_dossiers_archive_numbers(self):
        """Batch signing Stage 7 dossiers returns archive_number and stage transition metadata."""
        user_stg7 = User.objects.create_user(username="expert_stg7_batch", password="password123")
        prof7, _ = UserProfile.objects.get_or_create(user=user_stg7)
        prof7.allowed_stages = "7"
        prof7.can_sign = True
        prof7.full_name = "کارشناس تشکیل پرونده گروهی"
        prof7.save()

        d = HousingDossier.objects.create(
            national_id="0387777772",
            full_name="متقاضی امضای گروهی",
            archive_number=100778,
            current_stage=7,
        )

        client = Client()
        client.force_login(user_stg7)
        res = client.post(
            "/dossiers/batch-sign/",
            data='{"archive_numbers": [100778]}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["signed_count"], 1)
        self.assertEqual(len(payload["signed_dossiers"]), 1)
        entry = payload["signed_dossiers"][0]
        self.assertEqual(entry["archive_number"], 100778)
        self.assertEqual(entry["from_stage"], 7)
        self.assertEqual(entry["to_stage"], 8)
        self.assertEqual(entry["full_name"], "متقاضی امضای گروهی")


class ScanUploadIdempotencyTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="uploader_u1", password="password123")
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.prof.allowed_stages = "8,16"
        self.prof.can_upload = True
        self.prof.full_name = "کارشناس بارگذاری اسکن"
        self.prof.save()
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    @staticmethod
    def _make_png_file(name="test_scan.png"):
        buf = BytesIO()
        Image.new("RGB", (8, 8), color=(24, 90, 180)).save(buf, format="PNG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

    def test_upload_scan_idempotency_token_prevents_duplicate_attachments(self):
        dossier = HousingDossier.objects.create(
            national_id="0389990001",
            full_name="متقاضی تست اسکن تکراری",
            archive_number=100888,
            current_stage=8,
        )
        with tempfile.TemporaryDirectory() as tmp_media, override_settings(MEDIA_ROOT=tmp_media):
            res1 = self.client.post(
                "/dossier/100888/upload-scan/",
                data={
                    "title": "اسکن آزمایشی",
                    "doc_type": "OTHER",
                    "upload_token": "tok_scan_123",
                    "files": self._make_png_file("scan1.png"),
                },
            )
            self.assertEqual(res1.status_code, 200)
            p1 = res1.json()
            self.assertEqual(p1["status"], "success")
            self.assertEqual(DossierAttachment.objects.filter(dossier=dossier).count(), 1)

            # Duplicate request with identical upload_token returns cached payload without duplicating DB row
            res2 = self.client.post(
                "/dossier/100888/upload-scan/",
                data={
                    "title": "اسکن آزمایشی",
                    "doc_type": "OTHER",
                    "upload_token": "tok_scan_123",
                    "files": self._make_png_file("scan1_retry.png"),
                },
            )
            self.assertEqual(res2.status_code, 200)
            p2 = res2.json()
            self.assertEqual(p2["status"], "success")
            self.assertEqual(DossierAttachment.objects.filter(dossier=dossier).count(), 1)
            self.assertEqual(p2["attachments"][0]["id"], p1["attachments"][0]["id"])

    def test_upload_scan_inflight_token_returns_409_conflict(self):
        dossier = HousingDossier.objects.create(
            national_id="0389990002",
            full_name="متقاضی تست همزمانی اسکن",
            archive_number=100889,
            current_stage=8,
        )
        err_resp, inflight_key = _begin_upload_token(dossier.id, "tok_inflight_scan")
        self.assertIsNone(err_resp)
        self.assertIsNotNone(inflight_key)
        try:
            with tempfile.TemporaryDirectory() as tmp_media, override_settings(MEDIA_ROOT=tmp_media):
                res = self.client.post(
                    "/dossier/100889/upload-scan/",
                    data={
                        "title": "اسکن همزمان",
                        "doc_type": "OTHER",
                        "upload_token": "tok_inflight_scan",
                        "files": self._make_png_file("scan_dup.png"),
                    },
                )
            self.assertEqual(res.status_code, 409)
            self.assertEqual(res.json()["status"], "error")
            self.assertEqual(DossierAttachment.objects.filter(dossier=dossier).count(), 0)
        finally:
            _release_upload_token(inflight_key)

    def test_upload_check_scan_idempotency_and_inflight_conflict(self):
        dossier = HousingDossier.objects.create(
            national_id="0389990003",
            full_name="متقاضی تست اسکن چک",
            archive_number=100890,
            current_stage=16,
        )
        with tempfile.TemporaryDirectory() as tmp_media, override_settings(MEDIA_ROOT=tmp_media):
            res1 = self.client.post(
                "/dossier/100890/checks/upload-scan-and-create-receipt/",
                data={
                    "check_type": "loan",
                    "upload_token": "tok_chk_1",
                    "files": self._make_png_file("check1.png"),
                },
            )
            self.assertEqual(res1.status_code, 200)
            self.assertEqual(res1.json()["status"], "success")
            initial_count = DossierAttachment.objects.filter(dossier=dossier).count()
            self.assertGreaterEqual(initial_count, 1)

            res2 = self.client.post(
                "/dossier/100890/checks/upload-scan-and-create-receipt/",
                data={
                    "check_type": "loan",
                    "upload_token": "tok_chk_1",
                    "files": self._make_png_file("check1_retry.png"),
                },
            )
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(DossierAttachment.objects.filter(dossier=dossier).count(), initial_count)

            err_resp, inflight_key = _begin_upload_token(dossier.id, "tok_chk_inflight")
            self.assertIsNone(err_resp)
            try:
                res3 = self.client.post(
                    "/dossier/100890/checks/upload-scan-and-create-receipt/",
                    data={
                        "check_type": "loan",
                        "upload_token": "tok_chk_inflight",
                        "files": self._make_png_file("check_inflight.png"),
                    },
                )
                self.assertEqual(res3.status_code, 409)
                self.assertEqual(DossierAttachment.objects.filter(dossier=dossier).count(), initial_count)
            finally:
                _release_upload_token(inflight_key)


class WorkflowRequirementsTestCase(TestCase):
    def setUp(self):
        self.user_stage_7 = User.objects.create_user(username="req_stg7", password="password123")
        p7, _ = UserProfile.objects.get_or_create(user=self.user_stage_7)
        p7.allowed_stages = "7"
        p7.can_sign = True
        p7.full_name = "کارشناس مرحله ۷"
        p7.save()
        self.user_stage_7.refresh_from_db()

        self.user_stage_8 = User.objects.create_user(username="req_stg8", password="password123")
        p8, _ = UserProfile.objects.get_or_create(user=self.user_stage_8)
        p8.allowed_stages = "8"
        p8.can_sign = True
        p8.ui_mode = "simple"
        p8.full_name = "معاون کارگزاری (مرحله ۸)"
        p8.save()
        self.user_stage_8.refresh_from_db()

        self.user_stage_9 = User.objects.create_user(username="req_stg9", password="password123")
        p9, _ = UserProfile.objects.get_or_create(user=self.user_stage_9)
        p9.allowed_stages = "9"
        p9.can_sign = True
        p9.ui_mode = "simple"
        p9.full_name = "مدیر کارگزاری (مرحله ۹)"
        p9.save()
        self.user_stage_9.refresh_from_db()

        self.user_stage_11 = User.objects.create_user(username="req_stg11", password="password123")
        p11, _ = UserProfile.objects.get_or_create(user=self.user_stage_11)
        p11.allowed_stages = "11"
        p11.can_sign = True
        p11.full_name = "کارشناس فرم ج اداره کل (مرحله ۱۱)"
        p11.save()
        self.user_stage_11.refresh_from_db()

    def test_form_j_number_and_questionnaire_number_sync(self):
        import json
        dossier = HousingDossier.objects.create(
            national_id="0385550001",
            full_name="متقاضی همگام سازی فرم ج",
            archive_number=100910,
            current_stage=7,
        )

        # 1. Stage 7 updates form_j_number -> syncs form_j_questionnaire_number too
        client = Client()
        client.force_login(self.user_stage_7)
        res = client.post(
            f"/dossier/{dossier.archive_number}/save/",
            data=json.dumps({"form_j_number": "1405/J/777", "form_j_questionnaire_number": ""}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.form_j_number, "1405/J/777")
        self.assertEqual(dossier.form_j_questionnaire_number, "1405/J/777")

        # 2. Direct ORM save changing questionnaire number syncs form_j_number
        dossier.form_j_questionnaire_number = "1405/J/888"
        dossier.save()
        dossier.refresh_from_db()
        self.assertEqual(dossier.form_j_number, "1405/J/888")
        self.assertEqual(dossier.form_j_questionnaire_number, "1405/J/888")

    def test_stage_11_can_edit_computer_code_and_form_j_fields(self):
        import json
        for field in [
            "computer_code",
            "form_j_questionnaire_number",
            "form_j_number",
            "form_j_registration_type",
            "project_code",
            "applicant_form_j_status",
            "applicant_form_j_directorate_status",
            "applicant_form_j_red_description",
            "spouse_form_j_status",
            "spouse_form_j_directorate_status",
            "spouse_form_j_red_description",
        ]:
            self.assertTrue(
                can_user_edit_field(self.user_stage_11, field),
                f"Stage 11 must be able to edit '{field}'",
            )
        self.assertFalse(can_user_edit_field(self.user_stage_8, "computer_code"))

        dossier = HousingDossier.objects.create(
            national_id="0385550002",
            full_name="متقاضی مرحله ۱۱",
            archive_number=100911,
            current_stage=11,
        )
        client = Client()
        client.force_login(self.user_stage_11)
        res = client.post(
            f"/dossier/{dossier.archive_number}/save/",
            data=json.dumps({
                "computer_code": "CMP-11-9042",
                "form_j_questionnaire_number": "FJ-Q-5544",
                "form_j_registration_type": "دستی",
                "applicant_form_j_status": "قرمز (دارای سابقه مسکن / فاقد شرایط)",
                "applicant_form_j_red_description": "تست توضیح فرم ج",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.computer_code, "CMP-11-9042")
        self.assertEqual(dossier.form_j_questionnaire_number, "FJ-Q-5544")
        self.assertEqual(dossier.form_j_number, "FJ-Q-5544")
        self.assertNotEqual(dossier.computer_code, dossier.form_j_questionnaire_number)
        self.assertEqual(dossier.form_j_registration_type, "دستی")
        self.assertEqual(dossier.applicant_form_j_red_description, "تست توضیح فرم ج")

    def test_stage_8_and_9_can_see_all_of_sections_1_2_4(self):
        from pathlib import Path
        dossier = HousingDossier.objects.create(
            national_id="0385550003",
            full_name="متقاضی رویت بخش ۱ و ۲ و ۴",
            archive_number=100912,
            current_stage=8,
            site="پرنیان",
            project="پروژه نمونه",
        )
        for user, expected_stage in [(self.user_stage_8, 8), (self.user_stage_9, 9)]:
            dossier.current_stage = expected_stage
            dossier.save(update_fields=["current_stage"])
            client = Client()
            client.force_login(user)
            resp = client.get(f"/dossier/{dossier.archive_number}/")
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            self.assertIn('id="section-applicant"', html)
            self.assertIn('id="section-plot"', html)
            self.assertIn('id="section-cost"', html)
            self.assertIn("!canSeeFullSection1()", html)

        js_text = Path("static/js/sanadban.js").read_text(encoding="utf-8")
        self.assertIn('"section-cost": [2, 8, 9, 19]', js_text)

    def test_stage_8_cannot_sign_if_registry_or_base_cost_empty(self):
        import json
        dossier = HousingDossier.objects.create(
            national_id="0385550004",
            full_name="متقاضی کنترل امضای مرحله ۸",
            archive_number=100913,
            current_stage=8,
            registration_section="3",
            main_plaque=100,
            separated_plaque=12,
            sub_plaque=44,
            plot_number=7,
            base_cost_without_loan=4500000000,
        )
        client = Client()
        client.force_login(self.user_stage_8)

        # Each required field cleared individually must block signing (GUI sign + batch sign)
        blank_cases = [
            ("registration_section", ""),
            ("main_plaque", None),
            ("separated_plaque", None),
            ("sub_plaque", None),
            ("plot_number", None),
            ("base_cost_without_loan", 0),
        ]
        for field_name, empty_val in blank_cases:
            orig_val = getattr(dossier, field_name)
            setattr(dossier, field_name, empty_val)
            dossier.save()

            res_sign = client.post(
                f"/dossier/{dossier.archive_number}/sign/",
                data=json.dumps({"notes": "تلاش برای امضا"}),
                content_type="application/json",
            )
            self.assertEqual(res_sign.status_code, 400, f"Expected 400 when {field_name} is empty")
            dossier.refresh_from_db()
            self.assertEqual(dossier.current_stage, 8)

            res_batch = client.post(
                "/dossiers/batch-sign/",
                data=json.dumps({"archive_numbers": [dossier.archive_number]}),
                content_type="application/json",
            )
            self.assertEqual(res_batch.status_code, 200)
            b_payload = res_batch.json()
            self.assertEqual(b_payload["signed_count"], 0)
            self.assertEqual(b_payload["skipped_count"], 1)
            self.assertTrue(b_payload["errors"])

            setattr(dossier, field_name, orig_val)
            dossier.save()

        # Once all 6 fields are populated, Stage 8 user can sign and advance to Stage 9
        res_ok = client.post(
            f"/dossier/{dossier.archive_number}/sign/",
            data=json.dumps({"notes": "تایید کامل مرحله ۸"}),
            content_type="application/json",
        )
        self.assertEqual(res_ok.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.current_stage, 9)


class DecileBankLetterTestCase(TestCase):
    """Tests for «نامه بانک دهک» across stages, Excel import/export, check print, and BankLetter sender."""

    def _make_user(self, username: str, stages: str, chief: bool = False):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username=username, password="pass123456")
        prof = user.profile
        prof.organization = "brokerage"
        prof.allowed_stages = stages
        prof.is_housing_chief = chief
        prof.full_name = username
        prof.save()
        return user

    def setUp(self):
        self.user_stage_6 = self._make_user("bank_s6", "6")
        self.user_stage_17 = self._make_user("decile_s17", "17")
        self.user_stage_18 = self._make_user("decile_s18", "18")
        self.user_chief = self._make_user("chief_user", "all", chief=True)

    def test_permissions_and_stage_17_18_draft_save(self):
        import json
        from pathlib import Path
        from workflow.field_permissions import FIELD_STAGE_MAP, can_user_edit_field

        self.assertEqual(FIELD_STAGE_MAP["decile_bank_letter_number"], [17, 18])
        self.assertEqual(FIELD_STAGE_MAP["decile_bank_letter_date"], [17, 18])
        js_text = Path("static/js/sanadban.js").read_text(encoding="utf-8")
        self.assertIn("decile_bank_letter_number: [17, 18]", js_text)
        self.assertIn("decile_bank_letter_date: [17, 18]", js_text)

        dossier = HousingDossier.objects.create(
            national_id="0387770001",
            full_name="متقاضی وام دهک تست",
            archive_number=100950,
            current_stage=17,
            rah_letter="R-100",
            bank_letter_number="B-200",
        )
        self.assertTrue(can_user_edit_field(self.user_stage_17, "decile_bank_letter_number"))
        self.assertTrue(can_user_edit_field(self.user_stage_18, "decile_bank_letter_date"))
        self.assertFalse(can_user_edit_field(self.user_stage_6, "decile_bank_letter_number"))
        self.assertFalse(can_user_edit_field(self.user_stage_6, "decile_bank_letter_date"))

        # Stage 6 user attempt via draft endpoint must not overwrite decile letter
        c6 = Client()
        c6.force_login(self.user_stage_6)
        resp6 = c6.post(
            f"/dossier/{dossier.archive_number}/save/",
            data=json.dumps({"decile_bank_letter_number": "SHOULD-NOT-SAVE"}),
            content_type="application/json",
        )
        self.assertIn(resp6.status_code, (200, 403))
        dossier.refresh_from_db()
        self.assertEqual(dossier.decile_bank_letter_number, "")

        # Stage 17 saves decile_bank_letter_number and date
        c17 = Client()
        c17.force_login(self.user_stage_17)
        resp17 = c17.post(
            f"/dossier/{dossier.archive_number}/save/",
            data=json.dumps({
                "decile_bank_letter_number": "D-1405-77",
                "decile_bank_letter_date": "1405/03/10",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp17.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.decile_bank_letter_number, "D-1405-77")
        self.assertEqual(dossier.decile_bank_letter_date, "1405/03/10")
        # Separate from rah_letter and bank_letter_number
        self.assertEqual(dossier.rah_letter, "R-100")
        self.assertEqual(dossier.bank_letter_number, "B-200")

        # Stage 18 edits decile_bank_letter fields too
        dossier.current_stage = 18
        dossier.save()
        c18 = Client()
        c18.force_login(self.user_stage_18)
        resp18 = c18.post(
            f"/dossier/{dossier.archive_number}/save/",
            data=json.dumps({"decile_bank_letter_number": "D-1405-88"}),
            content_type="application/json",
        )
        self.assertEqual(resp18.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.decile_bank_letter_number, "D-1405-88")

    def test_excel_end_columns_update_and_export(self):
        import io
        import openpyxl
        from workflow.excel_utils import (
            TEMPLATE_FIELD_SPECS,
            EXPORT_COLUMNS,
            process_excel_update,
            generate_dossiers_export,
        )

        # Added at the very end of both TEMPLATE_FIELD_SPECS and EXPORT_COLUMNS
        self.assertEqual(
            [f for _, f, _ in TEMPLATE_FIELD_SPECS[-2:]],
            ["decile_bank_letter_number", "decile_bank_letter_date"],
        )
        self.assertEqual(
            [f for _, f, _ in EXPORT_COLUMNS[-2:]],
            ["decile_bank_letter_number", "decile_bank_letter_date"],
        )

        dossier = HousingDossier.objects.create(
            national_id="0387770002",
            full_name="متقاضی اکسل دهک",
            archive_number=100951,
            current_stage=17,
        )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["کد ملی متقاضی", "شماره نامه بانک دهک", "تاریخ نامه بانک دهک (شمسی)"])
        ws.append(["0387770002", "D-EXCEL-1405", "1405/04/22"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        res = process_excel_update(buf, self.user_chief, preview=False)
        self.assertTrue(res.get("success"), res)
        dossier.refresh_from_db()
        self.assertEqual(dossier.decile_bank_letter_number, "D-EXCEL-1405")
        self.assertEqual(dossier.decile_bank_letter_date, "1405/04/22")

        export_resp = generate_dossiers_export(HousingDossier.objects.filter(id=dossier.id))
        wb_out = openpyxl.load_workbook(io.BytesIO(export_resp.content))
        ws_out = wb_out.active
        headers = [c.value for c in ws_out[1]]
        values = [c.value for c in ws_out[2]]
        self.assertEqual(headers[-2:], ["شماره نامه بانک دهک", "تاریخ نامه بانک دهک (شمسی)"])
        self.assertEqual(values[-2:], ["D-EXCEL-1405", "1405/04/22"])

    def test_print_checks_displays_decile_bank_letter_for_loan_only(self):
        dossier = HousingDossier.objects.create(
            national_id="0387770003",
            full_name="متقاضی چاپ چک دهک",
            archive_number=100952,
            current_stage=17,
            rah_letter="RAH-999",
            commitment_number="COM-888",
            decile_bank_letter_number="DECILE-777",
            decile_bank_letter_date="1405/06/01",
        )
        client = Client()
        client.force_login(self.user_stage_17)

        res_loan = client.get(f"/dossier/{dossier.archive_number}/print/checks/?type=loan&auto_archive=0")
        self.assertEqual(res_loan.status_code, 200)
        loan_html = res_loan.content.decode("utf-8")
        self.assertIn("شماره نامه بانک دهک:", loan_html)
        self.assertIn("DECILE-777 (1405/06/01)", loan_html)

        res_prep = client.get(f"/dossier/{dossier.archive_number}/print/checks/?type=prep&auto_archive=0")
        self.assertEqual(res_prep.status_code, 200)
        prep_html = res_prep.content.decode("utf-8")
        self.assertIn("RAH-999", prep_html)
        self.assertNotIn("DECILE-777", prep_html)

    def test_bank_letter_sender_decile_flow_and_export(self):
        import json
        import openpyxl
        import io
        from workflow.models import BankLetter, WorkflowSignatureLog

        dossier = HousingDossier.objects.create(
            national_id="0387770004",
            full_name="متقاضی ارسال نامه دهک",
            archive_number=100953,
            current_stage=17,
            decile_loan_amount=2000000000,
            decile_loan_bank="بانک مسکن",
            bank_letter_number="BANK-ORIG-1",
            is_sent_to_bank=True,
        )

        # Stage 17 specialist can view bank-letter?type=decile
        c17 = Client()
        c17.force_login(self.user_stage_17)
        view_res = c17.get("/bank-letter/?type=decile")
        self.assertEqual(view_res.status_code, 200)
        self.assertEqual(view_res.context["default_letter_type"], "decile")
        self.assertTrue(view_res.context["can_send_decile"])
        self.assertFalse(view_res.context["can_send_bank"])

        # Stage 17 cannot submit a regular bank letter (Stage 6/10 only)
        forbidden_bank = c17.post(
            "/bank-letter/send/",
            data=json.dumps({
                "letter_type": "bank",
                "archive_numbers": [dossier.archive_number],
                "letter_number": "B-BAD",
                "letter_date": "1405/07/01",
                "bank_code": "maskan",
            }),
            content_type="application/json",
        )
        self.assertEqual(forbidden_bank.status_code, 403)

        # Stage 6 user cannot submit decile letter
        c6 = Client()
        c6.force_login(self.user_stage_6)
        forbidden_decile = c6.post(
            "/bank-letter/send/",
            data=json.dumps({
                "letter_type": "decile",
                "archive_numbers": [dossier.archive_number],
                "letter_number": "D-BAD",
                "letter_date": "1405/07/01",
                "bank_code": "maskan",
            }),
            content_type="application/json",
        )
        self.assertEqual(forbidden_decile.status_code, 403)

        # Stage 17 submits decile bank letter cleanly
        ok_res = c17.post(
            "/bank-letter/send/",
            data=json.dumps({
                "letter_type": "decile",
                "archive_numbers": [dossier.archive_number],
                "letter_number": "D-1405-555",
                "letter_date": "1405/07/12",
                "bank_code": "maskan",
                "notes": "نامه معرفی وام دهک",
            }),
            content_type="application/json",
        )
        self.assertEqual(ok_res.status_code, 200)
        payload = ok_res.json()
        self.assertEqual(payload["letter_type"], "decile")
        self.assertEqual(payload["updated_count"], 1)

        dossier.refresh_from_db()
        self.assertEqual(dossier.decile_bank_letter_number, "D-1405-555")
        self.assertEqual(dossier.decile_bank_letter_date, "1405/07/12")
        # Regular bank_letter and workflow stage untouched
        self.assertEqual(dossier.bank_letter_number, "BANK-ORIG-1")
        self.assertEqual(dossier.current_stage, 17)

        bl = BankLetter.objects.get(letter_number="D-1405-555")
        self.assertEqual(bl.letter_type, "decile")
        self.assertIn(dossier, bl.dossiers.all())
        self.assertTrue(
            WorkflowSignatureLog.objects.filter(
                dossier=dossier, action="BANK_LETTER", notes__icontains="D-1405-555"
            ).exists()
        )

        # Excel export for decile bank letter
        exp_res = c17.get("/bank-letter/export-excel/?bank=all&letter_type=decile&letter=D-1405-555&date=1405/07/12")
        self.assertEqual(exp_res.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(exp_res.content))
        self.assertEqual(wb.active.title, "نامه بانک دهک")
        self.assertEqual(wb.active.cell(row=2, column=19).value, "بانک عامل دهک")
        self.assertEqual(wb.active.cell(row=2, column=21).value, "شماره نامه بانک دهک")
        self.assertEqual(wb.active.cell(row=3, column=21).value, "D-1405-555")


class DossierListLayoutAndExtrasTestCase(TestCase):
    """Tests for right-aligned Stage/Date column and optional Letter/Payment column on dossier list."""

    def setUp(self):
        from django.contrib.auth.models import User

        self.admin = User.objects.create_user(username="list_chief", password="pass123456")
        prof = self.admin.profile
        prof.organization = "brokerage"
        prof.allowed_stages = "all"
        prof.is_housing_chief = True
        prof.save()
        self.client = Client()
        self.client.force_login(self.admin)

    def test_optional_column_states_and_right_aligned_stage(self):
        from django.utils import timezone
        import datetime
        import jdatetime
        from workflow.models import WorkflowSignatureLog

        ts_decile = timezone.make_aware(datetime.datetime(2026, 6, 15, 10, 30))
        j_decile = jdatetime.datetime.fromgregorian(datetime=timezone.localtime(ts_decile)).strftime("%Y/%m/%d")
        ts_prep = timezone.make_aware(datetime.datetime(2026, 6, 20, 14, 0))
        j_prep = jdatetime.datetime.fromgregorian(datetime=timezone.localtime(ts_prep)).strftime("%Y/%m/%d")

        # 1. Empty row (none of bank code, decile, prep, or notary letter code) -> 4-subplace light-gray 'ندارد' box
        d_empty = HousingDossier.objects.create(
            national_id="0388880001",
            full_name="متقاضی خالی لیست",
            archive_number=100960,
            current_stage=2,
            bank_letter_date="1405/01/05",    # Date without bank_letter_number code must count as ندارد
            notary_letter_date="1405/01/06",  # Date without notary_letter_number code must count as ندارد
        )

        # 2. Has bank letter code + date AND confirmed decile loan
        d_paid = HousingDossier.objects.create(
            national_id="0388880002",
            full_name="متقاضی بانک و دهک",
            archive_number=100961,
            current_stage=17,
            bank_letter_number="BL-405-9",
            bank_letter_date="1405/02/15",
            is_decile_loan_confirmed=True,
            loan_checks_confirmed_at=ts_decile,
        )

        # 3. Signed Stage 17 (returned before 17, so no longer active), Signed Stage 18 (prep) via log, and Notary letter
        d_signed = HousingDossier.objects.create(
            national_id="0388880003",
            full_name="متقاضی امضای آماده‌سازی",
            archive_number=100962,
            current_stage=20,
            notary_office_number="12",
            notary_letter_number="1405/ص/5521",
            notary_letter_date="1405/08/20",
        )
        WorkflowSignatureLog.objects.create(
            dossier=d_signed,
            from_stage="مرحله ۱۷: دریافت و اسکن چک‌های تسهیلات وام دهک",
            to_stage="مرحله ۱۸: دریافت نقد و اقساط آماده‌سازی و اجاره عرصه",
            actor="کارشناس ۱۷",
            role="کارشناس دهک",
            action="SIGN",
            action_label="تایید و امضای الکترونیکی",
            signature_hash="H17",
            timestamp=ts_decile,
        )
        # Returned to Stage 17 -> cancels stage 17 sign badge on d_signed
        WorkflowSignatureLog.objects.create(
            dossier=d_signed,
            from_stage="مرحله ۱۸: ...",
            to_stage="مرحله ۱۷: بازگشت",
            actor="کارشناس",
            role="کارشناس",
            action="RETURN",
            action_label="برگشت",
            signature_hash="R17",
            timestamp=ts_decile + datetime.timedelta(hours=1),
        )
        l18 = WorkflowSignatureLog.objects.create(
            dossier=d_signed,
            from_stage="مرحله ۱۸: دریافت نقد و اقساط آماده‌سازی و اجاره عرصه",
            to_stage="مرحله ۱۹: بررسی کارشناس تسویه با پیمانکار",
            actor="کارشناس ۱۸",
            role="کارشناس وصول",
            action="SIGN",
            action_label="تایید و امضای الکترونیکی",
            signature_hash="H18",
        )
        WorkflowSignatureLog.objects.filter(pk=l18.pk).update(timestamp=ts_prep)

        # Verify full page response
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        # 7 columns with right-aligned Stage header and centered «وضعیت» header
        self.assertIn("<th>مرحله و تاریخ ورود</th>", html)
        self.assertIn('<th class="t-center">وضعیت</th>', html)
        self.assertNotIn('<th class="t-center">مرحله و تاریخ ورود</th>', html)
        self.assertIn('align-items: flex-start;', html)
        self.assertIn('width: 25%;', html)
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', html)
        self.assertIn('flex-direction: column;', html)
        self.assertIn('margin-inline: auto;', html)
        self.assertIn('dl-extra-main', html)
        self.assertIn('.dl-extra-chip.notary', html)
        self.assertIn('.dl-extra-chip.empty', html)
        self.assertIn('<td colspan="7">', html)

        # Every row renders a 4-subplace box: 3 rows -> 12 total chips (8 unfilled 'ندارد' across the 3 rows)
        self.assertEqual(html.count('<div class="dl-extras-list">'), 3)
        self.assertEqual(html.count('<span class="dl-extra-chip empty"'), 8)

        # Row 2: bank letter + code + date, decile loan paid + date
        self.assertIn("نامه بانک:", html)
        self.assertIn("BL-405-9", html)
        self.assertIn("1405/02/15", html)
        self.assertIn("تسهیلات دهک : پرداخت شده", html)
        self.assertIn(j_decile, html)

        # Row 3: Stage 18 signed (prep) + Notary letter code & date
        self.assertIn("آماده‌سازی : پرداخت شده", html)
        self.assertIn(j_prep, html)
        self.assertIn("نامه دفترخانه:", html)
        self.assertIn("1405/ص/5521", html)
        self.assertIn("1405/08/20", html)

        # Verify AJAX table_rows.html matches 4-subplace layout and notary letter search
        ajax_paid = self.client.get("/?q=100961&ajax=1")
        self.assertEqual(ajax_paid.status_code, 200)
        ajax_html = ajax_paid.json()["html"]
        self.assertIn("BL-405-9", ajax_html)
        self.assertIn("تسهیلات دهک : پرداخت شده", ajax_html)
        self.assertNotIn("آماده‌سازی : پرداخت شده", ajax_html)
        self.assertEqual(ajax_html.count('<span class="dl-extra-chip empty"'), 2)

        ajax_empty = self.client.get("/?q=100960&ajax=1")
        self.assertEqual(ajax_empty.status_code, 200)
        empty_html = ajax_empty.json()["html"]
        self.assertEqual(empty_html.count('<span class="dl-extra-chip empty"'), 4)
        self.assertEqual(empty_html.count('<span class="dt">ندارد</span>'), 4)

        ajax_notary = self.client.get("/?q=1405/ص/5521&ajax=1")
        self.assertEqual(ajax_notary.status_code, 200)
        notary_html = ajax_notary.json()["html"]
        self.assertIn("100962", notary_html)
        self.assertIn("نامه دفترخانه:", notary_html)
        self.assertIn("1405/ص/5521", notary_html)
        self.assertIn("1405/08/20", notary_html)
        self.assertEqual(notary_html.count('<span class="dl-extra-chip empty"'), 2)


