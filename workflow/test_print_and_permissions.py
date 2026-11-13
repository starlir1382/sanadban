"""
workflow/test_print_and_permissions.py
Tests for:
1. Print summary signature rules (only sign papers after مرحله 7; audit log only before مرحله 7).
2. Numbering: shows 'ردیف {id}' before stage 8; official archive_number for stage >= 8.
3. Editability of بخش 1 and بخش 2 for both users of مرحله 8 and مرحله 9.
"""
from decimal import Decimal
from io import BytesIO
import json
import tempfile
from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse

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
        html_arse = res_arse.content.decode("utf-8")
        self.assertIn("جمع قدرالسهم از عرصه و مشاعات", html_arse)
        self.assertNotIn(">عرصه</th>", html_arse)
        self.assertNotIn(">مشاعات</th>", html_arse)
        self.assertNotIn(">قدرالسهم از</th>", html_arse)
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

        self.user_stage_2 = User.objects.create_user(username="req_stg2", password="password123")
        p2, _ = UserProfile.objects.get_or_create(user=self.user_stage_2)
        p2.allowed_stages = "2"
        p2.can_sign = True
        p2.full_name = "کارشناس عرصه و متقاضی (مرحله ۲)"
        p2.save()
        self.user_stage_2.refresh_from_db()

        self.user_stage_3 = User.objects.create_user(username="req_stg3", password="password123")
        p3, _ = UserProfile.objects.get_or_create(user=self.user_stage_3)
        p3.allowed_stages = "3"
        p3.can_sign = True
        p3.full_name = "کارشناس فرم ج اداره کل (مرحله ۳)"
        p3.save()
        self.user_stage_3.refresh_from_db()

        self.user_stage_6 = User.objects.create_user(username="req_stg6", password="password123")
        p6, _ = UserProfile.objects.get_or_create(user=self.user_stage_6)
        p6.allowed_stages = "6"
        p6.can_sign = True
        p6.full_name = "کارشناس بانک (مرحله ۶)"
        p6.save()
        self.user_stage_6.refresh_from_db()

        self.user_stage_13 = User.objects.create_user(username="req_stg13", password="password123")
        p13, _ = UserProfile.objects.get_or_create(user=self.user_stage_13)
        p13.allowed_stages = "13"
        p13.can_sign = True
        p13.full_name = "کارشناس املاک (مرحله ۱۳)"
        p13.save()
        self.user_stage_13.refresh_from_db()

        self.user_stage_14 = User.objects.create_user(username="req_stg14", password="password123")
        p14, _ = UserProfile.objects.get_or_create(user=self.user_stage_14)
        p14.allowed_stages = "14"
        p14.can_sign = True
        p14.full_name = "کارشناس بانک زمین (مرحله ۱۴)"
        p14.save()
        self.user_stage_14.refresh_from_db()

        self.user_stage_15 = User.objects.create_user(username="req_stg15", password="password123")
        p15, _ = UserProfile.objects.get_or_create(user=self.user_stage_15)
        p15.allowed_stages = "15"
        p15.can_sign = True
        p15.full_name = "کارشناس حقوقی (مرحله ۱۵)"
        p15.save()
        self.user_stage_15.refresh_from_db()

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
        # Stages 3 and 11 cannot change project_code
        self.assertFalse(can_user_edit_field(self.user_stage_11, "project_code"))
        self.assertFalse(can_user_edit_field(self.user_stage_3, "project_code"))
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
        self.assertIn('"section-cost": [8, 9, 19]', js_text)

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

    def test_workflow_new_requirements_permissions_and_bank_letter(self):
        """Verify:
        1. Stage 2 can edit Section 1, but NOT Section 2 or 4.
        2. Stages 3 and 11 cannot edit project_code.
        3. Stages 13, 14, 15 cannot edit dossier data fields (read-only for review & signature).
        4. Regular bank letters only allowed for current_stage == 6.
        5. Stages 17 and 18 print checks do not show دلاوری, and only show 2 signatures.
        """
        import json

        # 1. Stage 2: Section 1 allowed, Section 2 & 4 prohibited
        sec1_fields = [
            "national_id", "first_name", "last_name", "applicant_phone",
            "applicant_address", "site", "project", "block_name",
            "unit_number", "bedroom_count", "net_unit_area", "bank_name", "bank_branch"
        ]
        for f in sec1_fields:
            self.assertTrue(can_user_edit_field(self.user_stage_2, f), f"Stage 2 should edit {f}")

        sec2_and_4_fields = [
            "registration_section", "main_plaque", "separated_plaque",
            "sub_plaque", "plot_number", "renovation_code",
            "rah_letter", "rah_letter_date", "base_cost_without_loan"
        ]
        for f in sec2_and_4_fields:
            self.assertFalse(can_user_edit_field(self.user_stage_2, f), f"Stage 2 should NOT edit {f}")

        # 2. Stages 3 and 11: cannot edit project_code
        self.assertFalse(can_user_edit_field(self.user_stage_3, "project_code"))
        self.assertFalse(can_user_edit_field(self.user_stage_11, "project_code"))

        # 3. Stages 13, 14, 15: cannot edit deed_number, registration_section, or base_cost_without_loan
        prohibited_for_review_stages = [
            "deed_number", "deed_date", "is_land_deed_confirmed",
            "registration_section", "main_plaque", "plot_number",
            "rah_letter", "base_cost_without_loan"
        ]
        for u in [self.user_stage_13, self.user_stage_14, self.user_stage_15]:
            for f in prohibited_for_review_stages:
                self.assertFalse(can_user_edit_field(u, f), f"User {u.username} should NOT edit {f}")

        # 4. Bank letter submit API: regular bank letter only for current_stage == 6
        d_stage6 = HousingDossier.objects.create(
            national_id="0381112233",
            full_name="متقاضی مرحله ۶",
            archive_number=100961,
            current_stage=6,
        )
        d_stage5 = HousingDossier.objects.create(
            national_id="0381112234",
            full_name="متقاضی مرحله ۵",
            archive_number=100962,
            current_stage=5,
        )
        c_bank = Client()
        c_bank.force_login(self.user_stage_6)

        # Attempt sending d_stage5 -> should be rejected with 400
        res_fail = c_bank.post(
            "/bank-letter/send/",
            data=json.dumps({
                "letter_type": "bank",
                "archive_numbers": [d_stage5.archive_number],
                "letter_number": "1405/B/001",
                "letter_date": "1405/08/23",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_fail.status_code, 400)
        self.assertIn("مرحله ۶", res_fail.json().get("message", ""))

        # Sending d_stage6 -> succeeds and advances
        res_ok = c_bank.post(
            "/bank-letter/send/",
            data=json.dumps({
                "letter_type": "bank",
                "archive_numbers": [d_stage6.archive_number],
                "letter_number": "1405/B/002",
                "letter_date": "1405/08/23",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_ok.status_code, 200)
        d_stage6.refresh_from_db()
        self.assertTrue(d_stage6.is_sent_to_bank)
        self.assertEqual(d_stage6.bank_letter_number, "1405/B/002")
        self.assertEqual(d_stage6.current_stage, 7)

        # 5. Check print (stages 17 & 18): no Delavari, exactly 2 signatures (متصدی and کارگزار)
        d_checks = HousingDossier.objects.create(
            national_id="0381112235",
            full_name="متقاضی چک‌ها",
            archive_number=100963,
            current_stage=17,
        )
        # Set up a profile with Delavari to verify it gets stripped/removed
        c_print = Client()
        c_print.force_login(self.user_stage_8)
        res_print = c_print.get(f"/dossier/{d_checks.archive_number}/print/checks/")
        self.assertEqual(res_print.status_code, 200)
        html_print = res_print.content.decode("utf-8")
        self.assertNotIn("دلاوری", html_print)
        self.assertNotIn("امضاء راه و شهرسازی", html_print)
        self.assertIn("امضاء متصدی", html_print)
        self.assertIn("امضاء کارگزار", html_print)


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

        # 7 columns with centered Stage & Status headers and 4-place location badges
        self.assertIn('<th class="t-center">مرحله و تاریخ ورود</th>', html)
        self.assertIn('<th class="t-center">وضعیت</th>', html)
        self.assertIn('dl-stage-head', html)
        self.assertIn('dl-stage-loc loc-rah_azarm', html)
        self.assertIn('کارگزاری ره آزرم', html)
        self.assertIn('کارشناس اطلاعات و عرصه', html)
        self.assertIn('dl-stage-loc loc-zamin_tarsim', html)
        self.assertIn('کارگزاری زمین ترسیم', html)
        self.assertIn('کارشناس اخذ چک تسهیلات دهک', html)
        self.assertIn('dl-stage-loc loc-directorate', html)
        self.assertIn('اداره کل راه و شهرسازی', html)
        self.assertIn('کارشناس صدور نامه محضر', html)
        self.assertIn('dl-stage-role', html)
        self.assertIn('dl-stage-loc-name', html)
        self.assertIn('flex: 1;', html)
        self.assertIn('align-items: center;', html)
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
        self.assertIn('dl-stage-loc loc-directorate', notary_html)
        self.assertIn('کارشناس صدور نامه محضر', notary_html)

        # Verify all 22 stages + locked/archived map cleanly to the 4 places
        from workflow.stages import get_stage_location
        for s in (1, 2, 7, 8, 9):
            self.assertEqual(get_stage_location(s), ("rah_azarm", "کارگزاری ره آزرم"))
        for s in (17, 18):
            self.assertEqual(get_stage_location(s), ("zamin_tarsim", "کارگزاری زمین ترسیم"))
        for s in (3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16, 19, 20, 21):
            self.assertEqual(get_stage_location(s), ("directorate", "اداره کل راه و شهرسازی"))
        self.assertEqual(get_stage_location(22), ("archive", "بایگانی"))
        self.assertEqual(get_stage_location(3, is_locked=True), ("archive", "بایگانی"))
        self.assertEqual(get_stage_location(3, status="REJECTED_RED"), ("archive", "بایگانی"))

        d_arch = HousingDossier.objects.create(
            national_id="0388880004",
            full_name="متقاضی بایگانی",
            archive_number=100963,
            current_stage=22,
            is_locked=True,
        )
        arch_resp = self.client.get(f"/?q={d_arch.archive_number}&ajax=1")
        self.assertEqual(arch_resp.status_code, 200)
        arch_html = arch_resp.json()["html"]
        self.assertIn('dl-stage-loc loc-archive', arch_html)
        self.assertIn('بایگانی', arch_html)
        self.assertIn('کارشناس بایگانی اداره کل', arch_html)
        self.assertIn("1405/ص/5521", notary_html)
        self.assertIn("1405/08/20", notary_html)
        self.assertEqual(notary_html.count('<span class="dl-extra-chip empty"'), 2)

    def test_print_summary_broker_and_financial_2x3_layout(self):
        from django.urls import reverse

        d = HousingDossier.objects.create(
            national_id="0388880099",
            full_name="متقاضی خلاصه",
            archive_number=100999,
            current_stage=21,
            base_cost_without_loan=10666630000,
            total_land_share="77.05",
            current_year_rent=34025280,
            preparation_check_count=1,
        )
        resp = self.client.get(reverse("dossier_summary_print", kwargs={"pk": d.archive_number}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("broker-panel", html)
        self.assertIn("broker-note", html)
        self.assertIn("مسئولیت کارگزار صرفاً در محدوده صحت اطلاعات واحد انتخابی و اسکن مدارک می‌باشد.", html)
        self.assertIn('<table class="money-grid-table">', html)
        self.assertIn('<tr class="is-full">', html)
        self.assertIn("قیمت علی‌الحساب تمام شده (بدون وام):", html)
        self.assertIn("10,666,630,000 ریال", html)
        self.assertIn("جمع قدرالسهم از عرصه:", html)
        self.assertIn("مبلغ کل چک‌ها:", html)
        grid_block = html[html.index('<table class="money-grid-table">') : html.index('<!-- 6. امضای کارشناسان')]
        self.assertEqual(grid_block.count("<tr"), 4)
        self.assertEqual(grid_block.count("<td>") + grid_block.count('<td colspan="2">'), 7)

    def test_only_uploader_can_delete_attachment(self):
        """Only the user who uploaded an image/attachment can delete it (including same-stage colleagues and superusers)."""
        import json
        import re
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client, override_settings
        from django.urls import reverse

        uploader = User.objects.create_user(username="att_uploader_a", password="password123")
        pa, _ = UserProfile.objects.get_or_create(user=uploader)
        pa.allowed_stages = "8"
        pa.can_sign = True
        pa.full_name = "بارگذار الف"
        pa.save()

        colleague = User.objects.create_user(username="att_colleague_b", password="password123")
        pb, _ = UserProfile.objects.get_or_create(user=colleague)
        pb.allowed_stages = "8"
        pb.can_sign = True
        pb.full_name = "همکار ب"
        pb.save()

        chief_admin = User.objects.create_superuser(username="att_super_c", password="password123")
        pc, _ = UserProfile.objects.get_or_create(user=chief_admin)
        pc.is_housing_chief = True
        pc.full_name = "مدیر ج"
        pc.save()

        dossier = HousingDossier.objects.create(
            national_id="0387771122",
            full_name="متقاضی تست حذف تصویر",
            archive_number=100991,
            current_stage=8,
        )

        with tempfile.TemporaryDirectory() as tmp_media, override_settings(MEDIA_ROOT=tmp_media):
            c_up = Client()
            c_up.force_login(uploader)
            png_bytes = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
                b"\x27\x34\x27\x0a\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            up_resp = c_up.post(
                f"/dossier/{dossier.archive_number}/upload-scan/",
                data={
                    "title": "تصویر اختصاصی",
                    "doc_type": "OTHER",
                    "upload_token": "tok_uploader_rule_1",
                    "files": SimpleUploadedFile("pic.png", png_bytes, content_type="image/png"),
                },
            )
            self.assertEqual(up_resp.status_code, 200)
            att_id = up_resp.json()["attachments"][0]["id"]
            self.assertTrue(up_resp.json()["attachments"][0]["can_delete"])

            att_obj = DossierAttachment.objects.get(id=att_id)
            self.assertEqual(att_obj.uploaded_by_user_id, uploader.id)

            # Colleague in same stage cannot delete and gets can_delete=False
            c_col = Client()
            c_col.force_login(colleague)
            del_col = c_col.post(
                reverse("dossier_delete_attachment", kwargs={"pk": dossier.archive_number, "attachment_id": att_id})
            )
            self.assertEqual(del_col.status_code, 403)
            self.assertTrue(DossierAttachment.objects.filter(id=att_id).exists())

            detail_col_resp = c_col.get(reverse("dossier_detail", kwargs={"pk": dossier.archive_number}))
            col_atts = json.loads(detail_col_resp.context["dossier_json"])["attachments"]
            self.assertEqual(len(col_atts), 1)
            self.assertFalse(col_atts[0]["can_delete"])

            # Superuser / housing chief who did not upload also cannot delete
            c_adm = Client()
            c_adm.force_login(chief_admin)
            del_adm = c_adm.post(
                reverse("dossier_delete_attachment", kwargs={"pk": dossier.archive_number, "attachment_id": att_id})
            )
            self.assertEqual(del_adm.status_code, 403)
            self.assertTrue(DossierAttachment.objects.filter(id=att_id).exists())

            # Legacy attachment without uploaded_by_user still honors matching uploader display name
            legacy_att = DossierAttachment.objects.create(
                dossier=dossier,
                stage=8,
                doc_type="OTHER",
                title="تصویر قدیمی",
                file_name="legacy.png",
                uploaded_by="بارگذار الف",
                preview_url="/uploads/0387771122/legacy.png",
            )
            del_legacy_col = c_col.post(
                reverse("dossier_delete_attachment", kwargs={"pk": dossier.archive_number, "attachment_id": legacy_att.id})
            )
            self.assertEqual(del_legacy_col.status_code, 403)
            del_legacy_up = c_up.post(
                reverse("dossier_delete_attachment", kwargs={"pk": dossier.archive_number, "attachment_id": legacy_att.id})
            )
            self.assertEqual(del_legacy_up.status_code, 200)
            self.assertFalse(DossierAttachment.objects.filter(id=legacy_att.id).exists())

            # Uploader gets can_delete=True and can delete their own image
            detail_up_resp = c_up.get(reverse("dossier_detail", kwargs={"pk": dossier.archive_number}))
            up_atts = json.loads(detail_up_resp.context["dossier_json"])["attachments"]
            self.assertEqual(len(up_atts), 1)
            self.assertTrue(up_atts[0]["can_delete"])

            del_up = c_up.post(
                reverse("dossier_delete_attachment", kwargs={"pk": dossier.archive_number, "attachment_id": att_id})
            )
            self.assertEqual(del_up.status_code, 200)
            self.assertFalse(DossierAttachment.objects.filter(id=att_id).exists())

    def test_album_one_place_side_vs_bottom_dock(self):
        """Photo album launcher appears only on side when closed, and only in bottom dock when minimized."""
        from django.conf import settings
        from django.urls import reverse

        dossier = HousingDossier.objects.create(
            national_id="0387772233",
            full_name="متقاضی تست جایگاه آلبوم",
            archive_number=100992,
            current_stage=8,
        )
        resp = self.client.get(reverse("dossier_detail", kwargs={"pk": dossier.archive_number}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        # Side tab must NOT force display: flex !important (which overrides x-show) and must only show when closed
        css_block = html[html.index(".sticky-scan-tab {") : html.index(".sticky-scan-tab:hover")]
        self.assertIn("display: flex;", css_block)
        self.assertNotIn("display: flex !important;", css_block)
        self.assertIn('class="sticky-scan-tab no-print"\n    x-show="!showAlbumPopup"', html)
        self.assertIn('class="album-minimized-dock"\n        x-show="showAlbumPopup && isAlbumMinimized"', html)
        self.assertIn('class="album-popup-overlay"\n        x-show="showAlbumPopup && !isAlbumMinimized"', html)
        self.assertIn("canDeleteAttachment(item)", html)
        self.assertIn("sanadban.js?v=3.7", html)

        df_check_scans = (settings.BASE_DIR / "templates" / "df" / "_check_scans.html").read_text(encoding="utf-8")
        self.assertIn('x-show="canDeleteAttachment(scan)"', df_check_scans)

    def test_detail_tab_scroll_and_overflow_fix(self):
        """Tab switching uses non-sticky #dt-tabs-anchor, non-colliding panel IDs, and overflow-x: clip."""
        from django.conf import settings
        from django.urls import reverse

        dossier = HousingDossier.objects.create(
            national_id="0387773344",
            full_name="متقاضی تست اسکرول تب‌ها",
            archive_number=100993,
            current_stage=8,
        )
        resp = self.client.get(reverse("dossier_detail", kwargs={"pk": dossier.archive_number}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertIn("html, body { overflow-x: clip !important; max-width: 100vw; }", html)
        self.assertNotIn("html, body { overflow-x: hidden !important;", html)
        self.assertIn('<div id="dt-tabs-anchor"', html)
        self.assertIn('id="tab-panel-map"', html)
        self.assertIn('id="tab-panel-history"', html)
        self.assertNotIn('<div x-show="tab === \'map\'" id="map">', html)
        self.assertNotIn('<div x-show="tab === \'history\'" id="history">', html)

        css_text = (settings.BASE_DIR / "static" / "css" / "sanadban.css").read_text(encoding="utf-8")
        self.assertEqual(css_text.count("overflow-x: clip !important;"), 2)
        self.assertNotIn("overflow-x: hidden !important;", css_text)

        js_text = (settings.BASE_DIR / "static" / "js" / "sanadban.js").read_text(encoding="utf-8")
        self.assertIn('const validTabs = ["form", "map", "history"];', js_text)
        self.assertIn('document.getElementById("dt-tabs-anchor")', js_text)
        self.assertIn("this.$nextTick", js_text)

    def test_dossier_list_session_filter_persistence_and_clear_button(self):
        """List filters stay saved across returning home/back and reset cleanly via clear_filters=1."""
        from django.urls import reverse

        d_stage3 = HousingDossier.objects.create(
            national_id="0387774401",
            full_name="متقاضی مرحله سه",
            archive_number=100994,
            current_stage=3,
        )
        d_stage8 = HousingDossier.objects.create(
            national_id="0387774402",
            full_name="متقاضی مرحله هشت",
            archive_number=100995,
            current_stage=8,
        )
        d_red_pending = HousingDossier.objects.create(
            national_id="0387774403",
            full_name="متقاضی قرمز ارجاعی",
            archive_number=100996,
            current_stage=5,
            status="REJECT_RED_PENDING",
        )

        list_url = reverse("dossier_list")

        # 0. When there is no filter (all dossiers), the clear-filter button must not exist
        r_initial = self.client.get(list_url)
        self.assertEqual(r_initial.status_code, 200)
        self.assertFalse(r_initial.context["has_active_filters"])
        html_initial = r_initial.content.decode("utf-8")
        self.assertNotIn('id="workflow-clear-filters-btn"', html_initial)
        self.assertNotIn('href="/?clear_filters=1"', html_initial)

        # 1. Apply stage filter and verify list + session
        r_stage = self.client.get(list_url, {"stage": "3"})
        self.assertEqual(r_stage.status_code, 200)
        self.assertEqual(r_stage.context["stage_filter"], "3")
        self.assertTrue(r_stage.context["has_active_filters"])
        names = [d.full_name for d in r_stage.context["dossiers"]]
        self.assertIn(d_stage3.full_name, names)
        self.assertNotIn(d_stage8.full_name, names)

        # Red "پاک سازی فیلتر" button is rendered inside گردش کار header linking to ?clear_filters=1
        html_stage = r_stage.content.decode("utf-8")
        self.assertIn('id="workflow-clear-filters-btn"', html_stage)
        self.assertIn("?clear_filters=1", html_stage)
        self.assertIn("پاک سازی فیلتر", html_stage)

        # 2. Simulate entering a dossier and returning Home (bare "/") -> filter persists
        r_detail = self.client.get(reverse("dossier_detail", kwargs={"pk": d_stage3.archive_number}))
        self.assertEqual(r_detail.status_code, 200)

        r_home = self.client.get(list_url)
        self.assertEqual(r_home.status_code, 200)
        self.assertEqual(r_home.context["stage_filter"], "3")
        home_names = [d.full_name for d in r_home.context["dossiers"]]
        self.assertIn(d_stage3.full_name, home_names)
        self.assertNotIn(d_stage8.full_name, home_names)

        # 3. Switch to status=pending_red -> stage=3 must NOT leak into status filter, and status persists on "/"
        r_status = self.client.get(list_url, {"status": "pending_red"})
        self.assertEqual(r_status.status_code, 200)
        self.assertEqual(r_status.context["stage_filter"], "")
        self.assertEqual(r_status.context["status_filter"], "pending_red")
        self.assertEqual([d.full_name for d in r_status.context["dossiers"]], [d_red_pending.full_name])

        r_home2 = self.client.get(list_url)
        self.assertEqual(r_home2.context["status_filter"], "pending_red")
        self.assertEqual([d.full_name for d in r_home2.context["dossiers"]], [d_red_pending.full_name])

        # 4. AJAX search with query + empty stage updates session query and persists on "/"
        r_ajax = self.client.get(
            list_url,
            {"q": "0387774402", "stage": "", "status": "", "sort": "stage_asc", "ajax": "1"},
        )
        self.assertEqual(r_ajax.status_code, 200)
        self.assertEqual(r_ajax.json()["count"], 1)

        r_home3 = self.client.get(list_url)
        self.assertEqual(r_home3.context["query"], "0387774402")
        self.assertEqual([d.full_name for d in r_home3.context["dossiers"]], [d_stage8.full_name])

        # 5. Click "پاک سازی فیلتر" (?clear_filters=1) -> redirects to "/" with cleared session
        r_clear = self.client.get(list_url, {"clear_filters": "1"}, follow=True)
        self.assertRedirects(r_clear, list_url)
        self.assertFalse(r_clear.context["has_active_filters"])
        self.assertEqual(r_clear.context["query"], "")
        self.assertEqual(r_clear.context["stage_filter"], "")
        self.assertEqual(r_clear.context["status_filter"], "")
        cleared_names = [d.full_name for d in r_clear.context["dossiers"]]
        self.assertIn(d_stage3.full_name, cleared_names)
        self.assertIn(d_stage8.full_name, cleared_names)
        html_cleared = r_clear.content.decode("utf-8")
        self.assertNotIn('id="workflow-clear-filters-btn"', html_cleared)
        self.assertNotIn('href="/?clear_filters=1"', html_cleared)




class DirectorateShipmentAndVisitTestCase(TestCase):
    def setUp(self):
        from workflow.models import DirectorateShipment  # ensure model imports cleanly
        self.DirectorateShipment = DirectorateShipment

        self.alireza_user = User.objects.create_user(
            username="alireza_nazari",
            password="password123",
            is_staff=True,
            is_superuser=True,
        )
        p_alireza, _ = UserProfile.objects.get_or_create(user=self.alireza_user)
        p_alireza.full_name = "علیرضا نظری"
        p_alireza.is_housing_chief = True
        p_alireza.organization = "system"
        p_alireza.allowed_stages = "all"
        p_alireza.save()

        self.other_admin = User.objects.create_user(
            username="other_superadmin",
            password="password123",
            is_staff=True,
            is_superuser=True,
        )
        p_other, _ = UserProfile.objects.get_or_create(user=self.other_admin)
        p_other.full_name = "سایر ادمین‌ها"
        p_other.is_housing_chief = True
        p_other.organization = "system"
        p_other.allowed_stages = "all"
        p_other.save()

        self.all_stages_user = User.objects.create_user(username="all_lvl_user", password="password123")
        p_all, _ = UserProfile.objects.get_or_create(user=self.all_stages_user)
        p_all.allowed_stages = "all"
        p_all.full_name = "کاربر دسترسی کامل"
        p_all.save()

        self.user_17_18 = User.objects.create_user(username="expert_stg17_18", password="password123")
        p1718, _ = UserProfile.objects.get_or_create(user=self.user_17_18)
        p1718.allowed_stages = "17,18"
        p1718.is_check_admin = True
        p1718.full_name = "کارشناس اختصاصی ۱۷ و ۱۸"
        p1718.save()

        self.user_17 = User.objects.create_user(username="expert_stg17", password="password123")
        p17, _ = UserProfile.objects.get_or_create(user=self.user_17)
        p17.allowed_stages = "17"
        p17.full_name = "کارشناس تکمیل اسناد ۱۷"
        p17.role_title = "کارشناس چک و اسناد ۱۷"
        p17.save()

        self.user_18 = User.objects.create_user(username="expert_stg18", password="password123")
        p18, _ = UserProfile.objects.get_or_create(user=self.user_18)
        p18.allowed_stages = "18"
        p18.full_name = "کارشناس تطبیق چک ۱۸"
        p18.role_title = "کارشناس بررسی ۱۸"
        p18.save()

        self.mixed_stage_user = User.objects.create_user(username="expert_stg1_17", password="password123")
        p_mix, _ = UserProfile.objects.get_or_create(user=self.mixed_stage_user)
        p_mix.allowed_stages = "1,17"
        p_mix.full_name = "کارشناس غیر اختصاصی"
        p_mix.save()

        self.user_3 = User.objects.create_user(username="expert_stg3_ship", password="password123")
        p3, _ = UserProfile.objects.get_or_create(user=self.user_3)
        p3.allowed_stages = "3"
        p3.full_name = "کارشناس مرحله ۳"
        p3.save()

        for u in (
            self.alireza_user,
            self.other_admin,
            self.all_stages_user,
            self.user_17_18,
            self.user_17,
            self.user_18,
            self.mixed_stage_user,
            self.user_3,
        ):
            u.refresh_from_db()

        self.d17 = HousingDossier.objects.create(
            national_id="0388811001",
            full_name="متقاضی مرحله هفده",
            current_stage=17,
            archive_number=7001,
        )
        self.d18 = HousingDossier.objects.create(
            national_id="0388811002",
            full_name="متقاضی مرحله هجده",
            current_stage=18,
            archive_number=7002,
        )
        self.d3 = HousingDossier.objects.create(
            national_id="0388811004",
            full_name="متقاضی مرحله سه زودرس",
            current_stage=3,
            archive_number=7004,
            check_count=2,
            check_amount=500000000,
            last_check_amount=500000000,
            total_check_amount=1000000000,
            is_decile_loan_confirmed=True,
            tenant_price=100000000,
            tenant_code="12/1234",
            is_cash_rent_confirmed=True,
            cash_preparation_amount=200000000,
            prepayment_code="22/5678",
            non_cash_preparation_amount=800000000,
            preparation_check_count=2,
            total_preparation_check_amount=800000000,
            is_preparation_checks_confirmed=True,
        )
        self.d17_locked = HousingDossier.objects.create(
            national_id="0388811003",
            full_name="متقاضی مختومه ۱۷",
            current_stage=17,
            archive_number=7003,
            is_locked=True,
        )

    def test_shipment_history_page_acl_and_bulk_visit_removed(self):
        from django.urls import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse("dossiers_bulk_mark_visited")

        loan_sh = self.DirectorateShipment.objects.create(
            shipment_type="LOAN",
            sent_date="1405/08/22",
            created_by_user=self.alireza_user,
            created_by="علیرضا نظری",
        )
        prep_sh = self.DirectorateShipment.objects.create(
            shipment_type="PREP",
            sent_date="1405/08/23",
            created_by_user=self.alireza_user,
            created_by="علیرضا نظری",
        )
        self.d17.loan_directorate_shipment = loan_sh
        self.d17.is_loan_sent_to_directorate = True
        self.d17.save(update_fields=["loan_directorate_shipment", "is_loan_sent_to_directorate"])
        self.d18.prep_directorate_shipment = prep_sh
        self.d18.is_prep_sent_to_directorate = True
        self.d18.save(update_fields=["prep_directorate_shipment", "is_prep_sent_to_directorate"])

        history_url = reverse("directorate_shipments_list")
        ca = Client()
        ca.force_login(self.alireza_user)
        self.assertEqual(ca.post("/dossiers/bulk-mark-visited/").status_code, 404)

        r_ali = ca.get(history_url)
        self.assertEqual(r_ali.status_code, 200)
        ali_hist_html = r_ali.content.decode("utf-8")
        self.assertIn(loan_sh.shipment_code, ali_hist_html)
        self.assertIn(prep_sh.shipment_code, ali_hist_html)
        self.assertIn("چاپ ارسالی ها", ali_hist_html)

        # Stage 17-only expert sees only LOAN shipments; Stage 18-only sees only PREP shipments
        c17 = Client()
        c17.force_login(self.user_17)
        r17 = c17.get(history_url)
        self.assertEqual(r17.status_code, 200)
        h17 = r17.content.decode("utf-8")
        self.assertIn(loan_sh.shipment_code, h17)
        self.assertNotIn(prep_sh.shipment_code, h17)

        c18 = Client()
        c18.force_login(self.user_18)
        r18 = c18.get(history_url)
        self.assertEqual(r18.status_code, 200)
        h18 = r18.content.decode("utf-8")
        self.assertIn(prep_sh.shipment_code, h18)
        self.assertNotIn(loan_sh.shipment_code, h18)

        # Other admins / non-17-18 experts are blocked from history page (redirect 302)
        for denied in (self.other_admin, self.all_stages_user, self.mixed_stage_user, self.user_3):
            cd = Client()
            cd.force_login(denied)
            self.assertEqual(cd.get(history_url).status_code, 302)

        # Verify dossier_list navigation renders cleanly without breaking other admins or experts
        list_url = reverse("dossier_list")
        ali_list_resp = ca.get(list_url)
        self.assertEqual(ali_list_resp.status_code, 200)
        ali_list_html = ali_list_resp.content.decode("utf-8")
        self.assertIn('id="nav-directorate-shipments-tab"', ali_list_html)
        self.assertIn("تاریخچه ارسالی‌ها", ali_list_html)

        c_other_admin = Client()
        c_other_admin.force_login(self.other_admin)
        other_admin_resp = c_other_admin.get(list_url)
        self.assertEqual(other_admin_resp.status_code, 200)
        other_admin_html = other_admin_resp.content.decode("utf-8")
        self.assertNotIn('id="nav-directorate-shipments-tab"', other_admin_html)
        self.assertIn("مدیریت کاربران و مراحل", other_admin_html)

        c_expert = Client()
        c_expert.force_login(self.user_17_18)
        expert_resp = c_expert.get(list_url)
        self.assertEqual(expert_resp.status_code, 200)
        expert_html = expert_resp.content.decode("utf-8")
        self.assertIn('id="nav-directorate-shipments-btn"', expert_html)
        self.assertNotIn('id="nav-directorate-shipments-tab"', expert_html)

        c_user3 = Client()
        c_user3.force_login(self.user_3)
        u3_resp = c_user3.get(list_url)
        self.assertEqual(u3_resp.status_code, 200)
        u3_html = u3_resp.content.decode("utf-8")
        self.assertNotIn('id="nav-directorate-shipments-btn"', u3_html)
        self.assertNotIn('id="nav-directorate-shipments-tab"', u3_html)

    def test_stage17_18_split_permissions_visit_date_and_draft_save(self):
        self.user_17.refresh_from_db()
        self.user_18.refresh_from_db()
        self.user_17_18.refresh_from_db()
        self.user_3.refresh_from_db()

        # Both alireza_nazari and dedicated Stage 17/18 experts can edit visit_date;
        # directorate shipment flags/dates are strictly read-only inside individual dossiers ("only tick and send")
        for allowed_user in (self.alireza_user, self.user_17_18, self.user_17, self.user_18):
            self.assertTrue(can_user_edit_field(allowed_user, "visit_date"))
            for ro_field in (
                "is_loan_sent_to_directorate",
                "loan_directorate_sent_date",
                "is_prep_sent_to_directorate",
                "prep_directorate_sent_date",
            ):
                self.assertFalse(can_user_edit_field(allowed_user, ro_field))

        # Separate Stage 17 & Stage 18 visit_date fields obey strict split stage ACL
        self.assertTrue(can_user_edit_field(self.alireza_user, "loan_visit_date"))
        self.assertTrue(can_user_edit_field(self.alireza_user, "prep_visit_date"))
        self.assertTrue(can_user_edit_field(self.user_17_18, "loan_visit_date"))
        self.assertTrue(can_user_edit_field(self.user_17_18, "prep_visit_date"))
        self.assertTrue(can_user_edit_field(self.user_17, "loan_visit_date"))
        self.assertFalse(can_user_edit_field(self.user_17, "prep_visit_date"))
        self.assertTrue(can_user_edit_field(self.user_18, "prep_visit_date"))
        self.assertFalse(can_user_edit_field(self.user_18, "loan_visit_date"))

        all_tracking = [
            "visit_date",
            "loan_visit_date",
            "prep_visit_date",
            "is_loan_sent_to_directorate",
            "loan_directorate_sent_date",
            "is_prep_sent_to_directorate",
            "prep_directorate_sent_date",
        ]
        for f in all_tracking:
            for denied_user in (self.other_admin, self.all_stages_user, self.mixed_stage_user, self.user_3):
                self.assertFalse(can_user_edit_field(denied_user, f))

        for denied_user in (self.user_3, self.other_admin, self.all_stages_user, self.mixed_stage_user):
            filtered = filter_allowed_updates(
                denied_user,
                {
                    "visit_date": "1405/08/20",
                    "is_loan_sent_to_directorate": True,
                    "loan_directorate_sent_date": "1405/08/21",
                    "is_prep_sent_to_directorate": True,
                    "prep_directorate_sent_date": "1405/08/21",
                },
            )
            self.assertEqual(filtered, {})

        # Even authorized Stage 17/18 users only keep visit_date in filter_allowed_updates; shipment fields are stripped
        filtered_ali = filter_allowed_updates(
            self.alireza_user,
            {
                "visit_date": "1405/08/20",
                "is_loan_sent_to_directorate": True,
                "loan_directorate_sent_date": "1405/08/21",
                "is_prep_sent_to_directorate": True,
                "prep_directorate_sent_date": "1405/08/21",
            },
        )
        self.assertEqual(filtered_ali, {"visit_date": "1405/08/20"})

        # Other superadmin cannot save or see tracking blocks on detail page
        c_other = Client()
        c_other.force_login(self.other_admin)
        r_other_save = c_other.post(
            reverse("dossier_save", kwargs={"pk": self.d17.archive_number}),
            data=json.dumps({
                "visit_date": "1405/08/19",
                "is_loan_sent_to_directorate": True,
                "is_prep_sent_to_directorate": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(r_other_save.status_code, 200)
        self.d17.refresh_from_db()
        self.assertEqual(self.d17.visit_date, "")
        self.assertFalse(self.d17.is_loan_sent_to_directorate)
        self.assertFalse(self.d17.is_prep_sent_to_directorate)

        r_other_detail = c_other.get(reverse("dossier_detail", kwargs={"pk": self.d17.archive_number}))
        self.assertEqual(r_other_detail.status_code, 200)
        self.assertFalse(r_other_detail.context["can_manage_directorate_shipments"])
        detail_other_html = r_other_detail.content.decode("utf-8")
        self.assertNotIn("تیک مراجعه شده", detail_other_html)
        self.assertNotIn("ارسال شده به راه و شهرسازی — تسهیلات چک", detail_other_html)
        self.assertNotIn("ارسال شده به راه و شهرسازی — آماده‌سازی", detail_other_html)
        self.assertNotIn("تاریخ ارسال تسهیلات چک به راه و شهرسازی", detail_other_html)
        self.assertNotIn("تاریخ ارسال آماده‌سازی به راه و شهرسازی", detail_other_html)

        # alireza_nazari sees visit_date + read-only Loan/Prep status ("ارسال نشده" before batch send), NO toggle checkboxes
        c_ali = Client()
        c_ali.force_login(self.alireza_user)
        r_ali_detail = c_ali.get(reverse("dossier_detail", kwargs={"pk": self.d17.archive_number}))
        self.assertEqual(r_ali_detail.status_code, 200)
        self.assertTrue(r_ali_detail.context["can_manage_directorate_shipments"])
        ali_html = r_ali_detail.content.decode("utf-8")
        self.assertNotIn("تیک مراجعه شده", ali_html)
        self.assertNotIn("ارسال شده به راه و شهرسازی — تسهیلات چک", ali_html)
        self.assertNotIn("ارسال شده به راه و شهرسازی — آماده‌سازی", ali_html)
        self.assertNotIn("تاریخ مراجعه متقاضی (مراحل ۱۷ و ۱۸)", ali_html)
        self.assertIn("تاریخ مراجعه متقاضی — مرحله ۱۷ (شمسی)", ali_html)
        self.assertIn("تاریخ مراجعه متقاضی — مرحله ۱۸ (شمسی)", ali_html)
        self.assertIn("تاریخ ارسال تسهیلات چک به راه و شهرسازی", ali_html)
        self.assertIn("تاریخ ارسال آماده‌سازی به راه و شهرسازی", ali_html)
        self.assertIn("ارسال نشده", ali_html)

        # Stage 17 saves loan_visit_date (and cannot touch prep_visit_date or direct shipment flags)
        c17 = Client()
        c17.force_login(self.user_17)
        resp1 = c17.post(
            reverse("dossier_save", kwargs={"pk": self.d3.archive_number}),
            data=json.dumps({
                "loan_visit_date": "1405/08/20",
                "prep_visit_date": "1405/08/29",
                "is_loan_sent_to_directorate": True,
                "loan_directorate_sent_date": "1405/08/20",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, 200)
        self.d3.refresh_from_db()
        self.assertTrue(self.d3.is_loan_visited)
        self.assertEqual(self.d3.loan_visit_date, "1405/08/20")
        self.assertEqual(self.d3.loan_visited_by, "کارشناس تکمیل اسناد ۱۷")
        self.assertEqual(self.d3.prep_visit_date, "")
        self.assertTrue(self.d3.is_visited)
        self.assertEqual(self.d3.visit_date, "1405/08/20")
        self.assertFalse(self.d3.is_loan_sent_to_directorate)
        self.assertEqual(self.d3.loan_directorate_sent_date, "")

        # Stage 18 saves its own independent prep_visit_date
        c18_v = Client()
        c18_v.force_login(self.user_18)
        resp1b = c18_v.post(
            reverse("dossier_save", kwargs={"pk": self.d3.archive_number}),
            data=json.dumps({"prep_visit_date": "1405/08/24"}),
            content_type="application/json",
        )
        self.assertEqual(resp1b.status_code, 200)
        self.d3.refresh_from_db()
        self.assertTrue(self.d3.is_prep_visited)
        self.assertEqual(self.d3.prep_visit_date, "1405/08/24")
        self.assertEqual(self.d3.prep_visited_by, "کارشناس تطبیق چک ۱۸")
        self.assertEqual(self.d3.loan_visit_date, "1405/08/20")

        # Clearing loan_visit_date clears loan visit while preserving Stage 18 prep_visit_date
        resp2 = c17.post(
            reverse("dossier_save", kwargs={"pk": self.d3.archive_number}),
            data=json.dumps({"loan_visit_date": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 200)
        self.d3.refresh_from_db()
        self.assertFalse(self.d3.is_loan_visited)
        self.assertEqual(self.d3.loan_visit_date, "")
        self.assertTrue(self.d3.is_prep_visited)
        self.assertEqual(self.d3.prep_visit_date, "1405/08/24")
        self.assertTrue(self.d3.is_visited)
        self.assertEqual(self.d3.visit_date, "1405/08/24")

        # Clearing prep_visit_date clears remaining is_visited & metadata
        resp2b = c18_v.post(
            reverse("dossier_save", kwargs={"pk": self.d3.archive_number}),
            data=json.dumps({"prep_visit_date": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp2b.status_code, 200)
        self.d3.refresh_from_db()
        self.assertFalse(self.d3.is_visited)
        self.assertEqual(self.d3.visit_date, "")

        # Direct prep toggle via dossier_save is also ignored ("only tick and send")
        c18 = Client()
        c18.force_login(self.user_18)
        resp3 = c18.post(
            reverse("dossier_save", kwargs={"pk": self.d18.archive_number}),
            data=json.dumps({"is_prep_sent_to_directorate": True, "prep_directorate_sent_date": "1405/08/20"}),
            content_type="application/json",
        )
        self.assertEqual(resp3.status_code, 200)
        self.d18.refresh_from_db()
        self.assertFalse(self.d18.is_prep_sent_to_directorate)
        self.assertEqual(self.d18.prep_directorate_sent_date, "")

        # Once batch-sent via directorate_shipment_create, dossier detail displays the sent date instead of "ارسال نشده"
        r_batch_loan = c_ali.post(
            reverse("directorate_shipment_create"),
            data=json.dumps({
                "shipment_type": "LOAN",
                "archive_numbers": [self.d17.archive_number],
                "sent_date": "1405/08/25",
            }),
            content_type="application/json",
        )
        self.assertEqual(r_batch_loan.status_code, 200)
        r_ali_sent_detail = c_ali.get(reverse("dossier_detail", kwargs={"pk": self.d17.archive_number}))
        self.assertEqual(r_ali_sent_detail.status_code, 200)
        sent_html = r_ali_sent_detail.content.decode("utf-8")
        self.assertIn("1405/08/25", sent_html)

    def test_no_stage_order_restriction_for_stages_17_and_18(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Dedicated Stage 17/18 check admin can open d3 (current_stage=3) directly with action enabled
        c1718 = Client()
        c1718.force_login(self.user_17_18)
        r_det = c1718.get(reverse("dossier_detail", kwargs={"pk": self.d3.archive_number}))
        self.assertEqual(r_det.status_code, 200)
        self.assertTrue(r_det.context["user_can_action"])

        # Can upload a LOAN_CHECK scan on d3 even though dossier is at Stage 3
        up_file = SimpleUploadedFile("loan_chk.jpg", b"\xff\xd8\xff\xe0test", content_type="image/jpeg")
        r_up = c1718.post(
            reverse("dossier_upload_scan", kwargs={"pk": self.d3.archive_number}),
            {"doc_type": "LOAN_CHECK", "file": up_file},
        )
        self.assertEqual(r_up.status_code, 200)

        # Regular Stage 18 operator (is_check_admin=False) still cannot electronically sign Stage 18
        c18 = Client()
        c18.force_login(self.user_18)
        r_op_sign = c18.post(
            reverse("dossier_sign", kwargs={"pk": self.d3.archive_number}),
            data=json.dumps({"target_stage": 18}),
            content_type="application/json",
        )
        self.assertEqual(r_op_sign.status_code, 403)
        self.assertIn("مدیر کارگزاری چک", r_op_sign.json()["message"])

        # Check admin / alireza can sign Stage 18 FIRST out of order on d17 (current_stage=17) -> stays at 17
        r_sign_18_on_17 = c1718.post(
            reverse("dossier_sign", kwargs={"pk": self.d17.archive_number}),
            data=json.dumps({"target_stage": 18}),
            content_type="application/json",
        )
        self.assertEqual(r_sign_18_on_17.status_code, 200)
        self.d17.refresh_from_db()
        self.assertEqual(self.d17.current_stage, 17)
        self.assertIn(18, self.d17.get_signed_stages_set())

        # When d17 then signs Stage 17, workflow skips already-signed Stage 18 and jumps straight to Stage 19!
        r_sign_17 = c1718.post(
            reverse("dossier_sign", kwargs={"pk": self.d17.archive_number}),
            data=json.dumps({"notes": "تایید مرحله ۱۷"}),
            content_type="application/json",
        )
        self.assertEqual(r_sign_17.status_code, 200)
        self.d17.refresh_from_db()
        self.assertEqual(self.d17.current_stage, 19)

        # Out-of-order Stage 18 sign on d3 (at Stage 3) keeps d3 at Stage 3 and logs Stage 18 signature
        r_sign_18_on_3 = c1718.post(
            reverse("dossier_sign", kwargs={"pk": self.d3.archive_number}),
            data=json.dumps({"target_stage": 18}),
            content_type="application/json",
        )
        self.assertEqual(r_sign_18_on_3.status_code, 200)
        self.d3.refresh_from_db()
        self.assertEqual(self.d3.current_stage, 3)
        self.assertIn(18, self.d3.get_signed_stages_set())

    def test_split_loan_and_prep_shipments_and_print(self):
        # Other admins / 'all'-stage / stage-3 users remain 403 on shipment creation
        for blocked_u in (self.user_3, self.other_admin, self.all_stages_user, self.mixed_stage_user):
            c_blk = Client()
            c_blk.force_login(blocked_u)
            r_blk_post = c_blk.post(
                reverse("directorate_shipment_create"),
                data=json.dumps({"archive_numbers": [self.d17.archive_number], "shipment_type": "LOAN"}),
                content_type="application/json",
            )
            self.assertEqual(r_blk_post.status_code, 403)

        # Stage 17-only expert can send LOAN on d3 (even at stage 3!) but NOT PREP (403)
        c17 = Client()
        c17.force_login(self.user_17)
        r_wrong_type = c17.post(
            reverse("directorate_shipment_create"),
            data=json.dumps({"archive_numbers": [self.d3.archive_number], "shipment_type": "PREP"}),
            content_type="application/json",
        )
        self.assertEqual(r_wrong_type.status_code, 403)

        r_loan_ship = c17.post(
            reverse("directorate_shipment_create"),
            data=json.dumps({
                "archive_numbers": [self.d3.archive_number, self.d18.archive_number],
                "shipment_type": "LOAN",
                "sent_date": "1405/08/22",
                "note": "بسته تسهیلات",
            }),
            content_type="application/json",
        )
        self.assertEqual(r_loan_ship.status_code, 200)
        loan_data = r_loan_ship.json()
        self.assertEqual(loan_data["shipment"]["shipment_type"], "LOAN")
        self.assertEqual(loan_data["shipment"]["record_count"], 2)
        loan_code = loan_data["shipment"]["shipment_code"]

        self.d3.refresh_from_db()
        self.d18.refresh_from_db()
        self.assertTrue(self.d3.is_loan_sent_to_directorate)
        self.assertFalse(self.d3.is_prep_sent_to_directorate)
        self.assertEqual(self.d3.loan_directorate_shipment.shipment_code, loan_code)

        # Duplicate LOAN fails (400), whereas PREP for the SAME dossier d3 succeeds cleanly!
        r_dup_loan = c17.post(
            reverse("directorate_shipment_create"),
            data=json.dumps({"archive_numbers": [self.d3.archive_number], "shipment_type": "LOAN"}),
            content_type="application/json",
        )
        self.assertEqual(r_dup_loan.status_code, 400)

        ca = Client()
        ca.force_login(self.alireza_user)
        r_prep_ship = ca.post(
            reverse("directorate_shipment_create"),
            data=json.dumps({
                "archive_numbers": [self.d3.archive_number],
                "shipment_type": "PREP",
                "sent_date": "1405/08/23",
            }),
            content_type="application/json",
        )
        self.assertEqual(r_prep_ship.status_code, 200)
        prep_data = r_prep_ship.json()
        self.assertEqual(prep_data["shipment"]["shipment_type"], "PREP")
        prep_code = prep_data["shipment"]["shipment_code"]

        self.d3.refresh_from_db()
        self.assertTrue(self.d3.is_loan_sent_to_directorate)
        self.assertTrue(self.d3.is_prep_sent_to_directorate)
        self.assertEqual(self.d3.prep_directorate_shipment.shipment_code, prep_code)
        self.assertNotEqual(loan_code, prep_code)

        # Print view renders type-specific title & manifest; blocked for other_admin
        c_other = Client()
        c_other.force_login(self.other_admin)
        self.assertEqual(c_other.get(prep_data["print_url"]).status_code, 302)

        r_print_prep = ca.get(prep_data["print_url"])
        self.assertEqual(r_print_prep.status_code, 200)
        print_html = r_print_prep.content.decode("utf-8")
        self.assertIn("آماده‌سازی", print_html)
        self.assertIn(prep_code, print_html)
        self.assertIn(self.d3.full_name, print_html)
        self.assertIn("امضا تحویل‌دهنده", print_html)
        self.assertIn("امضا تحویل‌گیرنده", print_html)
        self.assertIn("پیمانکار", print_html)
        self.assertIn("تعداد چک", print_html)

    def test_comma_search_and_dossier_list_split_filters(self):
        loan_sh = self.DirectorateShipment.objects.create(
            shipment_type="LOAN",
            sent_date="1405/08/22",
            created_by_user=self.alireza_user,
            created_by="علیرضا نظری",
        )
        prep_sh = self.DirectorateShipment.objects.create(
            shipment_type="PREP",
            sent_date="1405/08/23",
            created_by_user=self.alireza_user,
            created_by="علیرضا نظری",
        )
        self.d17.visit_date = "1405/08/19"
        self.d17.is_visited = True
        self.d17.is_loan_sent_to_directorate = True
        self.d17.loan_directorate_sent_date = "1405/08/22"
        self.d17.loan_directorate_shipment = loan_sh
        self.d17.save()

        self.d3.is_prep_sent_to_directorate = True
        self.d3.prep_directorate_sent_date = "1405/08/23"
        self.d3.prep_directorate_shipment = prep_sh
        self.d3.save()

        list_url = reverse("dossier_list")

        # Other superadmin does NOT see visit/loan/prep filter pills, batch buttons, or chips
        c_other = Client()
        c_other.force_login(self.other_admin)
        r_other_list = c_other.get(list_url, {"status": "loan_shipped"})
        self.assertEqual(r_other_list.status_code, 200)
        self.assertFalse(r_other_list.context["can_manage_directorate_shipments"])
        self.assertEqual(r_other_list.context["status_filter"], "")
        other_html = r_other_list.content.decode("utf-8")
        self.assertNotIn("batch-ship-loan-btn", other_html)
        self.assertNotIn("batch-ship-prep-btn", other_html)
        self.assertNotIn("batch-visit-btn", other_html)
        self.assertNotIn("loan_shipped", other_html)
        self.assertNotIn("prep_shipped", other_html)
        self.assertNotIn('<div class="dl-track-box">', other_html)
        self.assertNotIn(loan_sh.shipment_code, other_html)

        # Stage 17/18 expert searches multiple national IDs separated by Arabic/Persian ویرگول and English comma
        c1718 = Client()
        c1718.force_login(self.user_17_18)
        r_comma_nids = c1718.get(list_url, {"q": f"{self.d3.national_id}, {self.d18.national_id}"})
        self.assertEqual(r_comma_nids.status_code, 200)
        found_archives = {d.archive_number for d in r_comma_nids.context["dossiers"]}
        self.assertEqual(found_archives, {self.d3.archive_number, self.d18.archive_number})

        # Search by Persian names separated by ویرگول (،)
        r_virgool_names = c1718.get(list_url, {"q": "متقاضی مرحله هفده، متقاضی مرحله سه زودرس"})
        found_by_names = {d.archive_number for d in r_virgool_names.context["dossiers"]}
        self.assertEqual(found_by_names, {self.d17.archive_number, self.d3.archive_number})

        # Dedicated Stage 17/18 user sees split Loan/Prep buttons + 2x2 applicant tracking grid (NO bulk-visit button)
        html_1718 = r_comma_nids.content.decode("utf-8")
        self.assertIn("batch-ship-loan-btn", html_1718)
        self.assertIn("batch-ship-prep-btn", html_1718)
        self.assertIn('<div class="dl-track-box">', html_1718)
        self.assertIn("ارسال آماده‌سازی", html_1718)
        self.assertNotIn("batch-visit-btn", html_1718)

        # Filter pills work cleanly across all stages for alireza_nazari
        ca = Client()
        ca.force_login(self.alireza_user)

        r_vis = ca.get(list_url, {"status": "has_visit_date"})
        self.assertEqual([d.archive_number for d in r_vis.context["dossiers"]], [self.d17.archive_number])
        vis_html = r_vis.content.decode("utf-8")
        self.assertIn("فیلتر: دارای تاریخ مراجعه", vis_html)
        self.assertNotIn("فیلتر: has_visit_date", vis_html)

        r_loan_yes = ca.get(list_url, {"status": "loan_shipped"})
        self.assertEqual([d.archive_number for d in r_loan_yes.context["dossiers"]], [self.d17.archive_number])
        self.assertIn("فیلتر: تسهیلات چک ارسال‌شده", r_loan_yes.content.decode("utf-8"))

        r_prep_yes = ca.get(list_url, {"status": "prep_shipped"})
        self.assertEqual([d.archive_number for d in r_prep_yes.context["dossiers"]], [self.d3.archive_number])
        self.assertIn("فیلتر: آماده‌سازی ارسال‌شده", r_prep_yes.content.decode("utf-8"))

        # ارسال‌نشده counts and filters must only include current_stage >= 17 (17, 18, 19, ...), NOT stage < 17
        d19 = HousingDossier.objects.create(
            national_id="0388811009",
            full_name="متقاضی مرحله نوزده",
            current_stage=19,
            archive_number=7009,
        )
        r_loan_no = ca.get(list_url, {"status": "loan_not_shipped"})
        self.assertEqual(r_loan_no.context["loan_not_shipped_cnt"], 2)  # d18 (stage 18) + d19 (stage 19); excludes d3 (stage 3) & d17 (shipped)
        self.assertEqual({d.archive_number for d in r_loan_no.context["dossiers"]}, {self.d18.archive_number, d19.archive_number})

        r_prep_no = ca.get(list_url, {"status": "prep_not_shipped"})
        self.assertEqual(r_prep_no.context["prep_not_shipped_cnt"], 3)  # d17 (stage 17) + d18 (stage 18) + d19 (stage 19); excludes d3 (stage 3)
        self.assertEqual({d.archive_number for d in r_prep_no.context["dossiers"]}, {self.d17.archive_number, self.d18.archive_number, d19.archive_number})

        r_search_code = ca.get(list_url, {"q": prep_sh.shipment_code, "status": ""})
        self.assertEqual([d.archive_number for d in r_search_code.context["dossiers"]], [self.d3.archive_number])
