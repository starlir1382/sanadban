import io
import openpyxl
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from workflow.models import HousingDossier, UserProfile
from workflow.excel_utils import (
    TEMPLATE_FIELD_SPECS,
    generate_create_template,
    generate_update_template,
    process_excel_create,
    process_excel_update,
    generate_dossiers_export,
    clean_field_value,
)
from workflow.field_permissions import FIELD_STAGE_MAP, can_user_edit_field

User = get_user_model()


def make_excel_file(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class NewExcelFieldsAndDetailSortingTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            password="admin_password",
            email="admin@example.com"
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.admin_user)
        profile.is_housing_chief = True
        profile.allowed_stages = "all"
        profile.save()

    def test_parking_area_and_number_present_in_templates(self):
        """Verify parking area and number are present in create and update templates."""
        for gen_fn in (generate_create_template, generate_update_template):
            buf = gen_fn()
            wb = openpyxl.load_workbook(buf, data_only=True)
            ws = wb.worksheets[0]
            headers = [c for c in next(ws.iter_rows(values_only=True)) if c]

            self.assertIn("شماره پارکینگ", headers)
            self.assertIn("مساحت پارکینگ (مترمربع)", headers)
            # Ensure headers are all unique
            self.assertEqual(len(headers), len(set(headers)), "Headers must be unique")

    def test_sorting_matches_detail_view_sections(self):
        """Verify fields follow the exact sequence of detail sections 1 to 11."""
        buf = generate_create_template()
        wb = openpyxl.load_workbook(buf, data_only=True)
        headers = [c for c in next(wb.worksheets[0].iter_rows(values_only=True)) if c]

        # Section 1 checks
        idx_nid = headers.index("کد ملی متقاضی")
        idx_name = headers.index("نام متقاضی")
        idx_spouse_nid = headers.index("کد ملی همسر")
        idx_project = headers.index("نام پروژه مسکونی")
        idx_parking = headers.index("مساحت پارکینگ (مترمربع)")

        self.assertLess(idx_nid, idx_name)
        self.assertLess(idx_name, idx_spouse_nid)
        self.assertLess(idx_spouse_nid, idx_project)
        self.assertLess(idx_project, idx_parking)

        # Section 2 checks: registry plaques, deed, and rah_letter
        idx_reg = headers.index("بخش ثبتی")
        idx_main_plaque = headers.index("پلاک اصلی")
        idx_rah_letter = headers.index("شماره نامه راه و شهرسازی")
        idx_rah_letter_date = headers.index("تاریخ نامه راه و شهرسازی (شمسی)")

        self.assertLess(idx_parking, idx_reg)
        self.assertLess(idx_reg, idx_main_plaque)
        self.assertLess(idx_main_plaque, idx_rah_letter)
        self.assertLess(idx_rah_letter, idx_rah_letter_date)

        # Section 3 checks: Form J
        idx_form_j = headers.index("وضعیت فرم ج متقاضی")
        self.assertLess(idx_rah_letter_date, idx_form_j)

        # Section 4 checks: Financial
        idx_price = headers.index("قیمت پایه بدون وام (ریال)")
        self.assertLess(idx_form_j, idx_price)

        # Section 10 checks: Checks & Preparation
        idx_checks = headers.index("مبلغ کل چک‌های وام دهک (ریال)")
        self.assertLess(idx_price, idx_checks)

        # Section 11 checks: Notary Office
        idx_notary = headers.index("شماره دفترخانه اسناد رسمی")
        self.assertLess(idx_checks, idx_notary)

    def test_process_excel_create_with_parking_and_rah_letter(self):
        """Verify creating dossiers via Excel sets parking_area, parking_number, and rah_letter."""
        headers = [
            "کد ملی متقاضی",
            "نام متقاضی",
            "نام خانوادگی متقاضی",
            "شماره پارکینگ",
            "مساحت پارکینگ (مترمربع)",
            "شماره نامه راه و شهرسازی",
            "تاریخ نامه راه و شهرسازی (شمسی)",
            "آدرس محل سکونت متقاضی",
        ]
        rows = [
            [
                "0012345678",
                "علی",
                "محمدی",
                12,
                15.5,
                "RH-9988",
                "1403/05/20",
                "قم، بلوار الغدیر، کوچه ۱۰",
            ]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"], f"Failed create: {res.get('error')}")
        self.assertEqual(res["created_count"], 1)

        d = HousingDossier.objects.get(national_id="0012345678")
        self.assertEqual(d.first_name, "علی")
        self.assertEqual(d.last_name, "محمدی")
        self.assertEqual(d.parking_number, 12)
        self.assertEqual(d.parking_area, Decimal("15.50"))
        self.assertEqual(d.rah_letter, "RH-9988")
        self.assertEqual(d.rah_letter_date, "1403/05/20")
        self.assertEqual(d.applicant_address, "قم، بلوار الغدیر، کوچه 10")

    def test_process_excel_update_with_parking_and_rah_letter(self):
        """Verify updating dossiers via Excel updates parking_area, parking_number, and rah_letter."""
        d = HousingDossier.objects.create(
            national_id="0023456789",
            first_name="حسین",
            last_name="رضایی",
            archive_number=100999,
            parking_number=5,
            parking_area=Decimal("12.00"),
        )

        headers = [
            "کد ملی متقاضی",
            "شماره پارکینگ",
            "مساحت پارکینگ (مترمربع)",
            "شماره نامه راه و شهرسازی",
            "تاریخ نامه راه و شهرسازی (شمسی)",
            "کد پستی متقاضی",
        ]
        rows = [
            [
                "0023456789",
                25,
                18.75,
                "1403/راه/554",
                "1403/09/10",
                "3715512345",
            ]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"], f"Failed update: {res.get('error')}")
        self.assertEqual(res["updated_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.parking_number, 25)
        self.assertEqual(d.parking_area, Decimal("18.75"))
        self.assertEqual(d.rah_letter, "1403/راه/554")
        self.assertEqual(d.rah_letter_date, "1403/09/10")
        self.assertEqual(d.applicant_postal_code, "3715512345")

    def test_rah_letter_stage_permissions(self):
        """Verify rah_letter and rah_letter_date are editable in stage 2 and stage 20."""
        # Stage 2 (بخش ۲) should be in FIELD_STAGE_MAP
        self.assertIn(2, FIELD_STAGE_MAP["rah_letter"])
        self.assertIn(2, FIELD_STAGE_MAP["rah_letter_date"])
        # Review stages 8 and 9 should be included
        self.assertIn(8, FIELD_STAGE_MAP["rah_letter"])
        self.assertIn(9, FIELD_STAGE_MAP["rah_letter"])
        # Stage 20 (محضر) should remain included
        self.assertIn(20, FIELD_STAGE_MAP["rah_letter"])
        self.assertIn(20, FIELD_STAGE_MAP["rah_letter_date"])

        # Test user with stage 2 permission
        user_stg2 = User.objects.create_user(username="stage2_user", password="password")
        p2, _ = UserProfile.objects.get_or_create(user=user_stg2)
        p2.allowed_stages = "2"
        p2.is_active_expert = True
        p2.save()
        self.assertTrue(can_user_edit_field(user_stg2, "rah_letter"))
        self.assertTrue(can_user_edit_field(user_stg2, "rah_letter_date"))

        # Test user with stage 20 permission
        user_stg20 = User.objects.create_user(username="stage20_user", password="password")
        p20, _ = UserProfile.objects.get_or_create(user=user_stg20)
        p20.allowed_stages = "20"
        p20.is_active_expert = True
        p20.save()
        self.assertTrue(can_user_edit_field(user_stg20, "rah_letter"))
        self.assertTrue(can_user_edit_field(user_stg20, "rah_letter_date"))

    def test_excel_create_with_identical_applicant_and_spouse_nid(self):
        """Verify that Excel create allows rows where applicant and spouse share the same national ID."""
        headers = ["کد ملی متقاضی", "نام متقاضی", "کد ملی همسر", "نام پروژه مسکونی"]
        rows = [
            ["0031112223", "مهدی", "0031112223", "پروژه بهاران"],
            ["0042223334", "سعید", "0042223334", "پروژه گلستان"],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"], f"Excel create failed: {res.get('error')}")
        self.assertEqual(res["created_count"], 2)
        self.assertEqual(res["failed_count"], 0)

        d1 = HousingDossier.objects.get(national_id="0031112223")
        self.assertEqual(d1.first_name, "مهدی")
        self.assertEqual(d1.spouse_national_id, "0031112223")
        self.assertEqual(d1.project, "پروژه بهاران")

        d2 = HousingDossier.objects.get(national_id="0042223334")
        self.assertEqual(d2.first_name, "سعید")
        self.assertEqual(d2.spouse_national_id, "0042223334")
        self.assertEqual(d2.project, "پروژه گلستان")

    def test_excel_create_still_detects_inter_row_couple_conflict(self):
        """Verify that while identical applicant/spouse within the same row is allowed, cross-row couple conflict is blocked."""
        headers = ["کد ملی متقاضی", "نام متقاضی", "کد ملی همسر"]
        rows = [
            ["0051111111", "احمد", "0052222222"],
            ["0052222222", "مریم", "0053333333"],  # Applicant in row 2 is spouse in row 1!
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["failed_count"], 1)
        self.assertTrue(any("همسر" in r or "متقاضی" in r for r in res["errors"][0]["reasons"]))

