"""
Unit and integration tests for bulk Excel module:
Features: Create, Update, Group Sign, Spouse Swap, Commission permissions, Reports.
"""

import io
import openpyxl
from django.test import TestCase
from django.contrib.auth.models import User
from workflow.models import (
    HousingDossier,
    UserProfile,
    DossierAttachment,
    WorkflowSignatureLog,
)
from workflow.excel_utils import (
    process_excel_create,
    process_excel_update,
    process_excel_group_sign,
    process_excel_spouse_swap,
)


def make_excel_file(headers, rows, sheet_name=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    if sheet_name:
        ws.title = sheet_name
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class ExcelBulkOperationsTestCase(TestCase):
    def setUp(self):
        # Admin user
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            password="password",
            email="admin@test.com"
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={
                "role_title": "مدیر کل مسکن",
                "is_housing_chief": True,
                "can_sign": True,
                "is_active_expert": True,
                "allowed_stages": "all",
                "is_check_admin": True
            }
        )
        self.admin_profile.is_housing_chief = True
        self.admin_profile.can_sign = True
        self.admin_profile.is_active_expert = True
        self.admin_profile.is_check_admin = True
        self.admin_profile.save()

        # Regular staff user (without check admin)
        self.staff_user = User.objects.create_user(
            username="staff_test",
            password="password",
            email="staff@test.com",
            is_staff=True
        )
        self.staff_profile, _ = UserProfile.objects.get_or_create(
            user=self.staff_user,
            defaults={
                "role_title": "کارشناس مسکن",
                "is_housing_chief": False,
                "can_sign": True,
                "is_active_expert": True,
                "allowed_stages": "1,2,3,4,5",
                "is_check_admin": False
            }
        )
        self.staff_profile.is_housing_chief = False
        self.staff_profile.can_sign = True
        self.staff_profile.is_active_expert = True
        self.staff_profile.is_check_admin = False
        self.staff_profile.save()

    def test_create_duplicate_id_rejected(self):
        """Case 1: Creating a dossier with a national_id that already exists or repeats in file is rejected."""
        # Pre-existing dossier
        HousingDossier.objects.create(
            national_id="0011223344",
            first_name="علی",
            last_name="رضایی",
            archive_number=100001
        )

        headers = ["کد ملی متقاضی", "نام متقاضی", "نام خانوادگی متقاضی"]
        rows = [
            ["0011223344", "تکراری", "سیستم"],       # duplicate with DB
            ["0022334455", "محمد", "علوی"],          # valid
            ["0022334455", "محمد ۲", "علوی تکراری"], # duplicate within file
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["created_count"], 1)
        self.assertEqual(res["failed_count"], 2)
        # Verify 0022334455 is created once
        self.assertTrue(HousingDossier.objects.filter(national_id="0022334455").exists())

    def test_create_couple_conflict_rejected(self):
        """Case 2: One dossier per couple conflict check."""
        # Pre-create couple: husband applicant, wife spouse
        HousingDossier.objects.create(
            national_id="0033445566",
            first_name="حسین",
            last_name="کریمی",
            spouse_national_id="0044556677",
            spouse_first_name="زهرا",
            archive_number=100002
        )

        headers = ["کد ملی متقاضی", "نام متقاضی", "کد ملی همسر"]
        rows = [
            # Applicant was already registered as spouse on dossier 100002
            ["0044556677", "زهرا", "0099887766"],
            # Spouse was already registered as applicant on dossier 100002
            ["0088776655", "مهدی", "0033445566"],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["created_count"], 0)
        self.assertEqual(res["failed_count"], 2)
        # Both errors should reference dossier 100002
        err_reasons = " ".join([r for e in res["errors"] for r in e["reasons"]])
        self.assertIn("100002", err_reasons)

    def test_update_nonexistent_id_creates_nothing(self):
        """Case 3: Update with nonexistent id creates NOTHING (count unchanged)."""
        initial_count = HousingDossier.objects.count()

        headers = ["کد ملی متقاضی", "نام متقاضی", "پروژه"]
        rows = [
            ["0000000000", "ناشناس", "پروژه خیالی"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 0)
        self.assertEqual(res["failed_count"], 1)
        self.assertEqual(HousingDossier.objects.count(), initial_count)
        self.assertIn("یافت نشد", res["errors"][0]["reasons"][0])

    def test_update_matched_by_spouse_leaves_identity_untouched(self):
        """Case 4: Update matched via spouse updates project/financial fields, NOT applicant identity."""
        d = HousingDossier.objects.create(
            national_id="0111111111",
            first_name="امیر",
            last_name="شمس",
            spouse_national_id="0222222222",
            spouse_first_name="فاطمه",
            spouse_last_name="مرادی",
            project="پروژه قدیم",
            archive_number=100003
        )

        headers = ["کد ملی متقاضی", "نام متقاضی", "نام خانوادگی متقاضی", "پروژه"]
        rows = [
            ["0222222222", "تغییر یافته", "هویتی نامعتبر", "پروژه آفتاب جدید"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["matched_via_spouse_count"], 1)

        d.refresh_from_db()
        # Applicant identity must remain untouched
        self.assertEqual(d.first_name, "امیر")
        self.assertEqual(d.last_name, "شمس")
        self.assertEqual(d.national_id, "0111111111")
        # Non-identity fields must be updated
        self.assertEqual(d.project, "پروژه آفتاب جدید")

    def test_update_ambiguous_id_rejected(self):
        """Case 5: Ambiguous ID match (matches multiple dossiers as spouse) is rejected."""
        # Two dossiers having same spouse ID
        HousingDossier.objects.create(
            national_id="0333333331",
            first_name="متقاضی یک",
            spouse_national_id="0555555555",
            archive_number=100004
        )
        HousingDossier.objects.create(
            national_id="0333333332",
            first_name="متقاضی دو",
            spouse_national_id="0555555555",
            archive_number=100005
        )

        headers = ["کد ملی متقاضی", "پروژه"]
        rows = [
            ["0555555555", "پروژه مبهم"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 0)
        self.assertEqual(res["failed_count"], 1)
        self.assertIn("ابهام", res["errors"][0]["reasons"][0])

    def test_same_dossier_twice_in_one_update_file_rejected(self):
        """Case 6: Two rows resolving to the same dossier in one update file rejects the second."""
        HousingDossier.objects.create(
            national_id="0666666666",
            first_name="مرد",
            spouse_national_id="0777777777",
            spouse_first_name="زن",
            project="پروژه ۱",
            archive_number=100006
        )

        headers = ["کد ملی متقاضی", "پروژه"]
        rows = [
            ["0666666666", "پروژه جدید الف"],
            ["0777777777", "پروژه جدید ب"],  # Resolves to same dossier via spouse!
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["failed_count"], 1)
        self.assertIn("قبلاً در همین فایل", res["errors"][0]["reasons"][0])

    def test_multi_sheet_workbook_reads_first_sheet(self):
        """Case 7: Workbook with multiple tabs reads the first tab."""
        d = HousingDossier.objects.create(
            national_id="0888888888",
            first_name="تست",
            last_name="چندبرگه",
            project="اولیه",
            archive_number=100007
        )

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "UpdateData"
        ws1.append(["کد ملی متقاضی", "پروژه"])
        ws1.append(["0888888888", "پروژه برگه اول"])

        ws2 = wb.create_sheet(title="OtherSheet")
        ws2.append(["کد ملی متقاضی", "پروژه"])
        ws2.append(["0888888888", "پروژه برگه دوم"])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        res = process_excel_update(buf, user=self.admin_user, preview=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.project, "پروژه برگه اول")

    def test_commission_cells_permission(self):
        """Case 8: Commission cells ignored for normal staff and applied for check_admin."""
        d1 = HousingDossier.objects.create(
            national_id="0999999991",
            first_name="کارمزد ۱",
            check_service_fee=1000,
            preparation_service_fee=2000,
            archive_number=100008
        )
        d2 = HousingDossier.objects.create(
            national_id="0999999992",
            first_name="کارمزد ۲",
            check_service_fee=1000,
            preparation_service_fee=2000,
            archive_number=100009
        )

        headers = ["کد ملی متقاضی", "کارمزد خدمات چک (ریال)", "کارمزد خدمات آماده‌سازی (ریال)"]
        rows = [
            ["0999999991", 5000000, 7000000],
            ["0999999992", 5000000, 7000000],
        ]

        # 1. Normal staff (is_check_admin=False)
        f_staff = make_excel_file(headers, rows)
        res_staff = process_excel_update(f_staff, user=self.staff_user, preview=False)
        self.assertTrue(res_staff["success"])
        self.assertTrue(len(res_staff["warnings"]) > 0)
        self.assertIn("کارمزد", res_staff["warnings"][0])

        d1.refresh_from_db()
        self.assertEqual(d1.check_service_fee, 1000) # unchanged!

        # 2. Admin (is_check_admin=True)
        f_admin = make_excel_file(headers, rows)
        res_admin = process_excel_update(f_admin, user=self.admin_user, preview=False)
        self.assertTrue(res_admin["success"])

        d2.refresh_from_db()
        self.assertEqual(d2.check_service_fee, 5000000)
        self.assertEqual(d2.preparation_service_fee, 7000000)

    def test_group_sign_advances_stage_and_writes_sign_excel(self):
        """Case 9: Group sign advances dossier stage and creates SIGN_EXCEL audit log."""
        d = HousingDossier.objects.create(
            national_id="0123456789",
            first_name="متقاضی",
            last_name="امضا",
            current_stage=1,
            status="IN_PROGRESS",
            archive_number=100010
        )

        headers = ["کد ملی متقاضی", "مرحله", "توضیحات"]
        rows = [
            ["0123456789", 1, "امضای تست اکسل"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_group_sign(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["signed_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.current_stage, 2)

        # Check WorkflowSignatureLog
        log = WorkflowSignatureLog.objects.filter(dossier=d, action="SIGN_EXCEL").first()
        self.assertIsNotNone(log)
        self.assertIn("امضای تست اکسل", log.notes)

    def test_spouse_swap_happy_path(self):
        """Case 10: Spouse swap swaps all identity fields, flips attachment doc_types, keeps archive_number."""
        d = HousingDossier.objects.create(
            national_id="0246813579",
            first_name="بهرام",
            last_name="افشاری",
            full_name="بهرام افشاری",
            father_name="پرویز",
            birth_date="1360/01/01",
            applicant_id_number="123",
            applicant_birth_place="تهران",
            applicant_form_j_status="GREEN",
            spouse_national_id="0135792468",
            spouse_first_name="مریم",
            spouse_last_name="سعیدی",
            spouse_full_name="مریم سعیدی",
            spouse_father_name="احمد",
            spouse_birth_date="1365/02/02",
            spouse_id_number="456",
            spouse_birth_place="شیراز",
            spouse_form_j_status="WHITE",
            archive_number=100011
        )

        att1 = DossierAttachment.objects.create(
            dossier=d,
            doc_type="NATIONAL_ID",
            file_name="applicant_card.jpg",
            stage=1
        )
        att2 = DossierAttachment.objects.create(
            dossier=d,
            doc_type="SPOUSE_ID",
            file_name="spouse_card.jpg",
            stage=1
        )

        headers = ["کد ملی متقاضی (مالک فعلی پرونده)"]
        rows = [
            ["0246813579"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_spouse_swap(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["swapped_count"], 1)

        d.refresh_from_db()
        # Archive number unchanged
        self.assertEqual(d.archive_number, 100011)

        # Applicant is now Maryam Saeedi
        self.assertEqual(d.national_id, "0135792468")
        self.assertEqual(d.first_name, "مریم")
        self.assertEqual(d.last_name, "سعیدی")
        self.assertEqual(d.father_name, "احمد")
        self.assertEqual(d.applicant_form_j_status, "WHITE")

        # Spouse is now Bahram Afshari
        self.assertEqual(d.spouse_national_id, "0246813579")
        self.assertEqual(d.spouse_first_name, "بهرام")
        self.assertEqual(d.spouse_last_name, "افشاری")
        self.assertEqual(d.spouse_father_name, "پرویز")
        self.assertEqual(d.spouse_form_j_status, "GREEN")

        # Attachment doc_types flipped
        att1.refresh_from_db()
        att2.refresh_from_db()
        self.assertEqual(att1.doc_type, "SPOUSE_ID")
        self.assertEqual(att2.doc_type, "NATIONAL_ID")

        # Audit log written
        self.assertTrue(WorkflowSignatureLog.objects.filter(dossier=d, action="EXCEL_SWAP").exists())

    def test_spouse_swap_rejected_if_spouse_id_on_another_dossier(self):
        """Case 11: Spouse swap rejected if the spouse ID already exists as another dossier's applicant."""
        d1 = HousingDossier.objects.create(
            national_id="0987654321",
            first_name="مالک یک",
            spouse_national_id="0543216789",
            spouse_first_name="همسر یک",
            archive_number=100012
        )
        d2 = HousingDossier.objects.create(
            national_id="0543216789", # Already applicant here!
            first_name="همسر یک",
            archive_number=100013
        )

        headers = ["کد ملی متقاضی (مالک فعلی پرونده)"]
        rows = [
            ["0987654321"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_spouse_swap(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["swapped_count"], 0)
        self.assertEqual(res["failed_count"], 1)
        self.assertIn("100013", res["errors"][0]["reasons"][0])

    def test_update_zero_regulation_and_persian_labels(self):
        """Case 12: Zero regulation matches IDs regardless of leading zero, and all diff labels are Persian."""
        d = HousingDossier.objects.create(
            national_id="0381929507", # DB has leading zero
            first_name="علیرضا",
            last_name="موسوی",
            spouse_national_id="0451582330",
            spouse_first_name="فاطمه",
            archive_number=100014,
            project_code="OLD_CODE"
        )

        # Excel has 9 digits without leading zero: 381929507
        headers = ["کد ملی متقاضی", "کد پروژه", "قیمت پایه بدون وام"]
        rows = [
            ["381929507", "NEW_PROJ_99", "5500000000"]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=True)

        self.assertTrue(res["success"])
        self.assertEqual(res["valid_count"], 1)
        self.assertEqual(len(res["updates_preview"]), 1)

        diffs = res["updates_preview"][0]["diff_display"]
        self.assertTrue(len(diffs) >= 2)
        for diff in diffs:
            # Must NOT be raw English
            self.assertNotIn("project_code", diff["label"])
            self.assertNotIn("base_cost_without_loan", diff["label"])
            # Must be Persian
            self.assertTrue(any("؀" <= c <= "ۿ" for c in diff["label"]))

    def test_update_search_spouse_national_id_without_leading_zero(self):
        """Update searching by spouse national ID without leading zero (9 digits)."""
        d = HousingDossier.objects.create(
            national_id="0112233445",
            first_name="آزمایش",
            last_name="متقاضی",
            spouse_national_id="0223344556",
            project="پروژه اولیه",
            archive_number=100091
        )
        # Search via 9 digits (missing leading zero) in primary column
        headers = ["کد ملی متقاضی", "پروژه"]
        rows = [["223344556", "پروژه به روز شده همسر"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["matched_via_spouse_count"], 1)
        d.refresh_from_db()
        self.assertEqual(d.project, "پروژه به روز شده همسر")
        self.assertEqual(d.national_id, "0112233445")

    def test_update_with_spouse_national_id_header_alone(self):
        """Update file where primary key column header is 'کد ملی همسر' without 'کد ملی متقاضی'."""
        d = HousingDossier.objects.create(
            national_id="0556677889",
            first_name="محمد",
            last_name="رضایی",
            spouse_national_id="0667788990",
            project="پروژه قبلی",
            archive_number=100092
        )
        # Header is directly کد ملی همسر, value has 9 digits (no 0)
        headers = ["کد ملی همسر", "پروژه"]
        rows = [["667788990", "پروژه تغییر یافته با هدر همسر"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        d.refresh_from_db()
        self.assertEqual(d.project, "پروژه تغییر یافته با هدر همسر")

    def test_update_normalizes_spouse_national_id_to_10_digits(self):
        """Updating spouse_national_id with 9 digits automatically adds leading zero."""
        d = HousingDossier.objects.create(
            national_id="0778899001",
            first_name="سارا",
            last_name="نوری",
            spouse_national_id="",
            archive_number=100093
        )
        headers = ["کد ملی متقاضی", "کد ملی همسر"]
        rows = [["0778899001", "889900112"]]  # 9 digits without leading zero
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        d.refresh_from_db()
        self.assertEqual(d.spouse_national_id, "0889900112")  # Normalized with leading zero!

    def test_update_composite_plaques_and_custom_headers(self):
        """Updating dossiers with composite plaque column 'فرعی / مفروز ومجزا / اصلی'."""
        d = HousingDossier.objects.create(
            national_id="0998877665",
            first_name="حسین",
            last_name="شکاری",
            archive_number=100094
        )
        headers = [
            "ردیف", "کدملی", "فرعی / مفروز ومجزا / اصلی", "پلاک کارگاهی", "زیر بنا", "سهم آورده متقاضی (ریال)"
        ]
        rows = [
            [1, "0998877665", "26/1353/2288", 2288, 106.66, 4035830640]
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        d.refresh_from_db()
        self.assertEqual(d.main_plaque, 26)
        self.assertEqual(d.separated_plaque, 1353)
        self.assertEqual(d.sub_plaque, 2288)
        self.assertEqual(d.plot_number, 2288)
        self.assertEqual(float(d.unit_area), 106.66)
        self.assertEqual(d.applicant_equity, 4035830640)

        # Test non-flipping of legitimate values: 600/12/3 and 2-part 2405/12
        from workflow.excel_utils import parse_composite_plaques
        self.assertEqual(parse_composite_plaques("600/12/3"), (600, 12, 3, None))
        self.assertEqual(parse_composite_plaques("2405/12"), (2405, None, 12, None))

    def test_update_no_silent_fallback_when_applicant_nid_wrong(self):
        """Bug 1 fix: If applicant NID is invalid/typoed, do not silently fallback to spouse."""
        d = HousingDossier.objects.create(
            national_id="0111222333",
            first_name="علی",
            last_name="احمدی",
            spouse_national_id="0444555666",
            archive_number=100095
        )
        headers = ["کد ملی متقاضی", "کد ملی همسر", "پروژه"]
        # Applicant NID 0999999999 does not exist, spouse 0444555666 exists
        rows = [["0999999999", "0444555666", "پروژه نفوذ نامعتبر"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertEqual(res["failed_count"], 1)
        self.assertEqual(res["updated_count"], 0)
        self.assertIn("کد ملی متقاضی در سامانه یافت نشد", res["errors"][0]["reasons"][0])
        d.refresh_from_db()
        self.assertNotEqual(d.project, "پروژه نفوذ نامعتبر")

    def test_update_cross_couple_contradiction_rejected(self):
        """Bug 3 fix: Applicant NID points to Couple A, Spouse NID points to Couple B."""
        d1 = HousingDossier.objects.create(
            national_id="0111111111",
            first_name="مرد الف",
            spouse_national_id="0222222221",
            archive_number=100096
        )
        d2 = HousingDossier.objects.create(
            national_id="0333333333",
            first_name="مرد ب",
            spouse_national_id="0444444444",
            archive_number=100097
        )
        headers = ["کد ملی متقاضی", "کد ملی همسر", "پروژه"]
        # Applicant is d1, spouse is from d2
        rows = [["0111111111", "0444444444", "پروژه ناسازگار"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertEqual(res["failed_count"], 1)
        self.assertIn("دو پرونده متفاوت", res["errors"][0]["reasons"][0])
        d1.refresh_from_db()
        self.assertEqual(d1.spouse_national_id, "0222222221")  # Not overwritten!

    def test_update_swapped_form_j_orientation(self):
        """Bug 4 fix: In swapped match, applicant_form_j in row maps to spouse_form_j in DB."""
        d = HousingDossier.objects.create(
            national_id="0555666777",
            first_name="احمد",
            last_name="صالحی",
            spouse_national_id="0888999000",
            spouse_first_name="زهرا",
            spouse_last_name="کریمی",
            applicant_form_j_status="سبز",
            spouse_form_j_status="سبز",
            archive_number=100098
        )
        headers = ["کد ملی متقاضی", "وضعیت فرم ج متقاضی"]
        # Row has spouse NID in applicant column, status قرمز
        rows = [["0888999000", "قرمز"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        d.refresh_from_db()
        # Row's "وضعیت فرم ج متقاضی" must be written onto spouse_form_j_status!
        self.assertEqual(d.applicant_form_j_status, "سبز")  # Applicant preserved!
        self.assertEqual(d.spouse_form_j_status, "قرمز")    # Spouse updated!

    def test_spouse_match_without_errors_has_no_failure_report(self):
        """Bug 6 fix: Successful spouse match does not produce failure report."""
        d = HousingDossier.objects.create(
            national_id="0123456780",
            first_name="متقاضی",
            spouse_national_id="0987654320",
            project="پروژه تست گزارش",
            archive_number=100099
        )
        headers = ["کد ملی همسر", "پروژه"]
        rows = [["0987654320", "پروژه جدید"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["failed_count"], 0)
        self.assertIsNone(res["report_url"])  # No failure report!
        self.assertIsNotNone(res["success_report_url"])  # Has success report!

    def test_update_cross_dossier_applicant_and_spouse_ambiguity(self):
        """Gap 1: NID is applicant in dossier A and spouse in dossier B -> rejected as ambiguous."""
        HousingDossier.objects.create(
            national_id="0321654987",
            first_name="امیر در پرونده الف",
            archive_number=100100
        )
        HousingDossier.objects.create(
            national_id="0129873456",
            first_name="متقاضی ب",
            spouse_national_id="0321654987",  # Same NID as spouse in B
            archive_number=100101
        )
        headers = ["کد ملی متقاضی", "پروژه"]
        rows = [["0321654987", "پروژه مبهم بین الف و ب"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertEqual(res["failed_count"], 1)
        self.assertIn("ابهام", res["errors"][0]["reasons"][0])

    def test_update_identical_nid_in_applicant_and_spouse_updates_safely(self):
        """User copied applicant NID into spouse column: update succeeds, spouse identity untouched."""
        d = HousingDossier.objects.create(
            national_id="0776655443",
            first_name="متقاضی اصلی",
            spouse_national_id="0887766554",
            archive_number=100102
        )
        # Row has the exact same applicant NID in both applicant and spouse columns
        headers = ["کد ملی متقاضی", "کد ملی همسر", "پروژه"]
        rows = [["0776655443", "0776655443", "پروژه با کدملی تکراری"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["failed_count"], 0)
        d.refresh_from_db()
        self.assertEqual(d.project, "پروژه با کدملی تکراری")
        # Ensure spouse_national_id is NOT overwritten with applicant's NID
        self.assertEqual(d.spouse_national_id, "0887766554")
        self.assertTrue(any("یکسان درج شده است" in w for w in res["warnings"]))

    def test_update_new_spouse_national_id_collides_with_existing_applicant(self):
        """Gap 3: Updating spouse_national_id to an NID belonging to an applicant elsewhere is prevented."""
        d_target = HousingDossier.objects.create(
            national_id="0101010101",
            first_name="هدف",
            spouse_national_id="",
            archive_number=100103
        )
        d_other = HousingDossier.objects.create(
            national_id="0202020202",
            first_name="مالک کدملی",
            archive_number=100104
        )
        headers = ["کد ملی متقاضی", "کد ملی همسر", "پروژه"]
        # Trying to set d_target's spouse to 0202020202 (d_other's applicant ID)
        rows = [["0101010101", "0202020202", "پروژه هدف"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertEqual(res["failed_count"], 1)
        self.assertIn("دو پرونده متفاوت", res["errors"][0]["reasons"][0])
        d_target.refresh_from_db()
        self.assertEqual(d_target.spouse_national_id, "")  # Collision prevented!

    def test_update_swapped_dropped_columns_warning(self):
        """Gap 4: Swapped row warns user when applicant_phone is dropped."""
        d = HousingDossier.objects.create(
            national_id="0303030303",
            first_name="متقاضی",
            applicant_phone="09121111111",
            spouse_national_id="0404040404",
            spouse_first_name="همسر",
            archive_number=100105
        )
        headers = ["کد ملی متقاضی", "تلفن همراه", "پروژه"]
        # Swapped: row has spouse NID in applicant column, with a phone number
        rows = [["0404040404", "09129999999", "پروژه معکوس"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        d.refresh_from_db()
        self.assertEqual(d.project, "پروژه معکوس")
        self.assertEqual(d.applicant_phone, "09121111111")  # Phone was not overwritten!
        self.assertTrue(any("نادیده گرفته شد" in w for w in res["warnings"]))

    def test_update_errors_contain_no_dynamic_dossier_numbers_for_clean_excel_filtering(self):
        """Standardized error strings without archive/row numbers enable clean Excel AutoFilter grouping."""
        HousingDossier.objects.create(
            national_id="0909090909",
            first_name="تکرار",
            archive_number=100106
        )
        headers = ["کد ملی متقاضی", "پروژه"]
        # Two rows resolving to the same dossier
        rows = [
            ["0909090909", "پروژه ردیف اول"],
            ["0909090909", "پروژه ردیف دوم"],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertEqual(res["failed_count"], 1)
        reason = res["errors"][0]["reasons"][0]
        # Must be exact categorizable string, NO dynamic archive number or row number
        self.assertEqual(reason, "پرونده قبلاً در همین فایل بروزرسانی شده است (تکرار پرونده یا زوجین).")
        self.assertNotIn("100106", reason)
        self.assertNotIn("ردیف", reason)

    def test_update_applicant_priority_over_spouse_regardless_of_row_order(self):
        """When both spouse and applicant appear in the same file, applicant row ALWAYS wins."""
        d = HousingDossier.objects.create(
            national_id="0505050505",
            first_name="شوهر_متقاضی",
            last_name="اصلی",
            spouse_national_id="0606060606",
            spouse_first_name="همسر",
            spouse_last_name="اصلی",
            project="پروژه اولیه",
            archive_number=100107,
        )
        headers = ["کد ملی متقاضی", "پروژه"]
        # Row 1 has Spouse (0606060606), Row 2 has Applicant (0505050505)
        # Even though Row 1 is higher up, Row 2 (Applicant) MUST win!
        rows = [
            ["0606060606", "داده ردیف همسر"],
            ["0505050505", "داده ردیف متقاضی برنده"],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["failed_count"], 1)

        d.refresh_from_db()
        # The applicant's row was the one applied!
        self.assertEqual(d.project, "داده ردیف متقاضی برنده")

        # The spouse row was rejected as duplicate with warning
        self.assertEqual(res["errors"][0]["row"], 2)  # Excel row 2 is the spouse row
        self.assertIn("قبلاً در همین فایل", res["errors"][0]["reasons"][0])
        self.assertTrue(any("اولویت متقاضی اصلی" in w for w in res["warnings"]))

    def test_create_with_total_price_calculates_base_cost_and_default_loan(self):
        """Total price 11B Rials in Excel create auto-calculates base_cost (4.5B) with default 6.5B loan."""
        headers = ["کد ملی متقاضی", "نام متقاضی", "نام خانوادگی متقاضی", "مبلغ کل قرارداد"]
        rows = [["0881122334", "سعید", "کریمی", "11,000,000,000"]]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["created_count"], 1)

        d = HousingDossier.objects.get(national_id="0881122334")
        self.assertEqual(d.bank_loan_amount, 6500000000)
        self.assertEqual(d.base_cost_without_loan, 4500000000)

    def test_create_with_total_price_and_custom_loan(self):
        """Total price 11B with custom loan 5.5B calculates base_cost as 5.5B."""
        headers = ["کد ملی متقاضی", "نام متقاضی", "مبلغ کل قرارداد", "وام ساخت بانک مسکن"]
        rows = [["0881122335", "نادر", "11,000,000,000", "5,500,000,000"]]
        f = make_excel_file(headers, rows)
        res = process_excel_create(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["created_count"], 1)

        d = HousingDossier.objects.get(national_id="0881122335")
        self.assertEqual(d.bank_loan_amount, 5500000000)
        self.assertEqual(d.base_cost_without_loan, 5500000000)

    def test_update_with_total_price_calculates_base_cost(self):
        """Total price in Excel update calculates base_cost against existing loan."""
        d = HousingDossier.objects.create(
            national_id="0881122336",
            first_name="محسن",
            bank_loan_amount=6500000000,
            base_cost_without_loan=4000000000,
            archive_number=100108,
        )
        headers = ["کد ملی متقاضی", "مبلغ کل"]
        # Updating total price to 11B -> base_cost should become 11B - 6.5B = 4.5B
        rows = [["0881122336", "11,000,000,000"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.base_cost_without_loan, 4500000000)
        self.assertEqual(d.bank_loan_amount, 6500000000)

    def test_update_with_total_price_and_custom_loan(self):
        """Updating total price and loan simultaneously computes base_cost accurately."""
        d = HousingDossier.objects.create(
            national_id="0881122337",
            first_name="حامد",
            bank_loan_amount=6500000000,
            base_cost_without_loan=4000000000,
            archive_number=100109,
        )
        headers = ["کد ملی متقاضی", "قیمت تمام شده کل", "وام ساخت"]
        # Setting total to 11B and loan to 5.5B -> base_cost becomes 5.5B
        rows = [["0881122337", "11000000000", "5500000000"]]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.bank_loan_amount, 5500000000)
        self.assertEqual(d.base_cost_without_loan, 5500000000)

    def test_selective_category_export(self):
        """Case 13: Export with selected_categories exports only chosen column groups."""
        from workflow.excel_utils import generate_dossiers_export
        import openpyxl

        resp = generate_dossiers_export(selected_categories=["financial"])
        self.assertEqual(resp.status_code, 200)

        buf = io.BytesIO(resp.content)
        wb = openpyxl.load_workbook(buf, data_only=True)
        ws = wb.worksheets[0]
        headers = [c for c in next(ws.iter_rows(values_only=True)) if c]

        # Financial export should contain financial columns and basic identifiers
        self.assertIn("شماره بایگانی پرونده", headers)
        self.assertIn("کد ملی متقاضی", headers)
        self.assertIn("مبلغ تسهیلات وام بانکی (ریال)", headers)
        # Should NOT contain non-selected categories like spouse details or land area
        self.assertNotIn("نام پدر همسر", headers)
        self.assertNotIn("شماره شناسنامه همسر", headers)

    def test_red_form_j_blocks_advancement(self):
        """Case 14: Stage 3 cannot be signed or advanced if Form J status is red."""
        from workflow.views import execute_dossier_sign

        d = HousingDossier.objects.create(
            national_id="0123987654",
            current_stage=3,
            applicant_form_j_status="قرمز (دارای سابقه مسکن / فاقد شرایط)",
            archive_number=100015
        )

        ok, msg = execute_dossier_sign(d, user=self.admin_user, target_stage=3)
        self.assertFalse(ok)
        self.assertIn("قرمز", msg)

        # Stage should remain 3
        d.refresh_from_db()
        self.assertEqual(d.current_stage, 3)

    def test_print_summary_wipes_subsequent_stage_signatures(self):
        """Case 15: If dossier is at stage 3, signatures for stages >= 3 are not in print summary."""
        from workflow.views import get_dossier_signatures_summary, DossierSignature

        d = HousingDossier.objects.create(
            national_id="0321654987",
            current_stage=12,
            archive_number=100016
        )

        # Add signatures for stage 1 (brokerage) and stage 10 (real_estate)
        DossierSignature.objects.create(
            dossier=d,
            slot_key="brokerage",
            signer_name="مدیرعامل کارگزاری",
            signed_date="1405/08/01 - 10:00"
        )
        DossierSignature.objects.create(
            dossier=d,
            slot_key="real_estate",
            signer_name="کارشناس املاک",
            signed_date="1405/08/05 - 12:00"
        )

        sigs, signed_count = get_dossier_signatures_summary(d)
        # brokerage is from stage 9 < 12, so it should stay
        self.assertIn("brokerage", sigs)
        # real_estate is from stage 13 >= 12, so it MUST be wiped!
        self.assertNotIn("real_estate", sigs)

    def test_22_row_stage_signature_template_and_processing(self):
        """Case 16: Verify group signing template with national_id in col 1 and stages 1..22 in headers."""
        from workflow.excel_utils import generate_group_sign_template, process_excel_group_sign

        # 1. Verify template headers: Col 1 = کد ملی متقاضی, Col 2..23 = مرحله 1..مرحله 22, Col 24 = توضیحات
        buf = generate_group_sign_template()
        wb = openpyxl.load_workbook(buf, data_only=True)
        ws = wb.worksheets[0]
        headers = [c.value for c in ws[1]]
        self.assertEqual(headers[0], "کد ملی متقاضی")
        self.assertEqual(headers[1], "مرحله 1")
        self.assertEqual(headers[22], "مرحله 22")
        self.assertEqual(headers[23], "توضیحات امضا (اختیاری)")

        # 2. Setup dossiers
        dA = HousingDossier.objects.create(
            national_id="0381000001",
            first_name="علی",
            last_name="احمدی",
            current_stage=1,
            status="IN_PROGRESS",
            archive_number=100017
        )
        dB = HousingDossier.objects.create(
            national_id="0381000002",
            first_name="رضا",
            last_name="کریمی",
            current_stage=2,
            status="IN_PROGRESS",
            archive_number=100018
        )
        dC_red = HousingDossier.objects.create(
            national_id="0381000003",
            first_name="محمد",
            last_name="قرمزی",
            current_stage=3,
            applicant_form_j_status="قرمز (دارای سابقه مسکن / فاقد شرایط)",
            status="IN_PROGRESS",
            archive_number=100019
        )
        dD_green = HousingDossier.objects.create(
            national_id="0381000004",
            first_name="حسن",
            last_name="سبزی",
            current_stage=3,
            applicant_form_j_status="سبز (استعلام شده و فاقد سابقه ملکی)",
            status="IN_PROGRESS",
            archive_number=100020
        )

        # 3. Build upload file:
        # Row 2: dA (0381000001) -> mark stage 1 (col 2) and stage 2 (col 3) with 1
        # Row 3: dC_red (0381000003) -> mark stage 3 (col 4) with 1
        # Row 4: dD_green (0381000004) -> mark stage 3 (col 4) with 1
        ws.cell(row=2, column=1, value="0381000001")
        ws.cell(row=2, column=2, value=1) # مرحله 1
        ws.cell(row=2, column=3, value=1) # مرحله 2

        ws.cell(row=3, column=1, value="0381000003")
        ws.cell(row=3, column=4, value=1) # مرحله 3 (Red Form J)

        ws.cell(row=4, column=1, value="0381000004")
        ws.cell(row=4, column=4, value=1) # مرحله 3 (Green Form J)

        upload_buf = io.BytesIO()
        wb.save(upload_buf)
        upload_buf.seek(0)

        # 4. Preview test
        res_preview = process_excel_group_sign(upload_buf, user=self.admin_user, preview=True)
        self.assertTrue(res_preview["success"])
        self.assertTrue(res_preview["preview"])
        self.assertEqual(res_preview["valid_count"], 2) # dA and dD_green
        self.assertEqual(res_preview["failed_count"], 1) # dC_red blocked by Red Form J

        # 5. Confirm test
        upload_buf.seek(0)
        res_confirm = process_excel_group_sign(upload_buf, user=self.admin_user, preview=False)
        self.assertTrue(res_confirm["success"])
        self.assertFalse(res_confirm["preview"])
        self.assertEqual(res_confirm["valid_count"], 2)
        self.assertEqual(res_confirm["failed_count"], 1)

        # Verify dossier stage advancements
        dA.refresh_from_db()
        self.assertEqual(dA.current_stage, 3) # Advanced 1 -> 2 -> 3!

        dB.refresh_from_db()
        self.assertEqual(dB.current_stage, 2) # Not in file, stayed 2

        dC_red.refresh_from_db()
        self.assertEqual(dC_red.current_stage, 3) # Red Form J blocked at stage 3

        dD_green.refresh_from_db()
        self.assertEqual(dD_green.current_stage, 4) # Green Form J advanced 3 -> 4

    def test_update_template_plaque_fields_and_no_duplicates(self):
        """Verify update template has no duplicate columns and has exact 3 separated + 1 composite plaque fields."""
        from workflow.excel_utils import generate_update_template, process_excel_update
        buf = generate_update_template()
        wb = openpyxl.load_workbook(buf, data_only=True)
        ws = wb.worksheets[0]
        headers = [c for c in next(ws.iter_rows(values_only=True)) if c]

        # Check no duplicates
        self.assertEqual(len(headers), len(set(headers)), "Headers in update template must be unique!")

        # Check plaque columns: exactly 3 separated + 1 composite
        self.assertIn("پلاک اصلی", headers)
        self.assertIn("پلاک مفروز", headers)
        self.assertIn("پلاک فرعی", headers)
        self.assertIn("فرعی / مفروز ومجزا / اصلی", headers)

        # Check that old duplicate variants are not in the template headers
        self.assertNotIn("پلاک ثبتی اصلی", headers)
        self.assertNotIn("پلاک ثبتی مفروز و مجزی", headers)
        self.assertNotIn("پلاک ثبتی فرعی", headers)
        self.assertNotIn("فرعی از", headers)
        self.assertNotIn("فرعی از (پلاک فرعی)", headers)

        # Verify update with 3 separated columns works
        d1 = HousingDossier.objects.create(
            national_id="0011223344",
            archive_number=100095
        )
        f_sep = make_excel_file(
            ["کد ملی متقاضی", "پلاک اصلی", "پلاک مفروز", "پلاک فرعی"],
            [["0011223344", 500, 25, 4]]
        )
        res_sep = process_excel_update(f_sep, user=self.admin_user, preview=False)
        self.assertTrue(res_sep["success"])
        d1.refresh_from_db()
        self.assertEqual(d1.main_plaque, 500)
        self.assertEqual(d1.separated_plaque, 25)
        self.assertEqual(d1.sub_plaque, 4)

    def test_update_with_spouse_zero_does_not_fail(self):
        """Verify that rows with spouse national id as 0, '0', or '0000000000' do not throw errors."""
        from workflow.excel_utils import clean_national_id, get_national_id_variants, process_excel_update

        # Unit tests on helpers
        self.assertIsNone(clean_national_id(0))
        self.assertIsNone(clean_national_id("0"))
        self.assertIsNone(clean_national_id(0.0))
        self.assertEqual(get_national_id_variants(0), [])
        self.assertEqual(get_national_id_variants("0"), [])

        d1 = HousingDossier.objects.create(
            national_id="0019876543",
            first_name="سارا",
            last_name="عباسی",
            spouse_national_id="",
            archive_number=100096
        )
        d2 = HousingDossier.objects.create(
            national_id="0029876543",
            first_name="مریم",
            last_name="حسینی",
            spouse_national_id="",
            archive_number=100097
        )

        headers = ["کد ملی متقاضی", "کد ملی همسر", "نام متقاضی", "قیمت پایه بدون وام (ریال)"]
        rows = [
            ["0019876543", 0, "سارا بروز شده", 5000000000],
            ["0029876543", "0", "مریم بروز شده", 5200000000],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 2)
        self.assertEqual(res["failed_count"], 0)

        d1.refresh_from_db()
        self.assertEqual(d1.first_name, "سارا بروز شده")
        self.assertEqual(d1.base_cost_without_loan, 5000000000)
        self.assertEqual(d1.spouse_national_id, "") # Not corrupted to 0000000000

        d2.refresh_from_db()
        self.assertEqual(d2.first_name, "مریم بروز شده")
        self.assertEqual(d2.base_cost_without_loan, 5200000000)
        self.assertEqual(d2.spouse_national_id, "")

    def test_update_rah_letter_headers_and_template(self):
        """Verify that 'شماره نامه راه و شهرسازی' and date are present in template and can be updated."""
        from workflow.excel_utils import generate_update_template, process_excel_update
        buf = generate_update_template()
        wb = openpyxl.load_workbook(buf, data_only=True)
        ws = wb.worksheets[0]
        headers = [c for c in next(ws.iter_rows(values_only=True)) if c]

        self.assertIn("شماره نامه راه و شهرسازی", headers)
        self.assertIn("تاریخ نامه راه و شهرسازی (شمسی)", headers)

        d = HousingDossier.objects.create(
            national_id="0098765432",
            first_name="مهدی",
            last_name="قاسمی",
            archive_number=100098
        )

        update_headers = ["کد ملی متقاضی", "شماره نامه راه و شهرسازی", "تاریخ نامه راه و شهرسازی"]
        update_rows = [
            ["0098765432", "1405/9876/RH", "1405/08/15"]
        ]
        f = make_excel_file(update_headers, update_rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.rah_letter, "1405/9876/RH")
        self.assertEqual(d.rah_letter_date, "1405/08/15")

    def test_update_eleven_digit_national_id_and_shenase_melli_alias(self):
        """Verify that 11-digit national IDs with extra zero match properly and 'شناسه ملی' alias works."""
        from workflow.excel_utils import process_excel_update

        d = HousingDossier.objects.create(
            national_id="0382370651",
            first_name="بهرام",
            last_name="شمشیری",
            archive_number=100099,
            project="پروژه اولیه"
        )

        # Excel has header 'شناسه ملی' and value has 11 digits (double zero 00382370651)
        update_headers = ["شناسه ملی", "نام پروژه مسکونی"]
        update_rows = [
            ["00382370651", "پروژه بهرام تغییر یافته"],
            ["12345678901", "ردیف با شناسه نامعتبر ۱۱ رقمی"]  # Should fail gracefully without breaking file
        ]
        f = make_excel_file(update_headers, update_rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["failed_count"], 1)

        d.refresh_from_db()
        self.assertEqual(d.project, "پروژه بهرام تغییر یافته")

    def test_update_emits_finalizing_sub_progress_and_fast_bulk_roundtrip(self):
        """Verify finalizing sub-progress stages are emitted and Decimal/Bool/Int/Log writes persist accurately."""
        from decimal import Decimal
        from unittest.mock import patch
        from django.core.cache import cache
        from workflow.models import DossierFieldChangeLog
        from workflow import excel_utils

        d = HousingDossier.objects.create(
            national_id="0382370699",
            first_name="سارا",
            last_name="احمدی",
            archive_number=100100,
            net_unit_area=Decimal("80.00"),
            is_equity_funded=False,
            floor_number=1,
        )

        f = make_excel_file(
            ["کد ملی متقاضی", "متراژ مفید واحد (مترمربع)", "شماره طبقه", "تاییدیه تامین آورده نقدی", "شماره همراه متقاضی"],
            [["0382370699", "95.25", "4", "بله", "09121112233"]],
        )

        recorded = []
        orig_set = excel_utils.set_excel_task_progress

        def spy_progress(task_id, stage, percent, message, details="", **kwargs):
            recorded.append((stage, percent, kwargs.get("sub_percent"), kwargs.get("sub_label"), kwargs.get("sub_current"), kwargs.get("sub_total")))
            return orig_set(task_id, stage, percent, message, details, **kwargs)

        task_id = "test_sub_prog_001"
        with patch.object(excel_utils, "set_excel_task_progress", side_effect=spy_progress):
            res = excel_utils.process_excel_update(f, user=self.admin_user, preview=False, task_id=task_id)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)

        stages = [r[0] for r in recorded]
        self.assertIn("finalizing", stages)
        self.assertEqual(stages[-1], "done")
        finalizing_events = [r for r in recorded if r[0] == "finalizing"]
        self.assertTrue(any(r[2] is not None and r[3] for r in finalizing_events))

        # Check cache payload and progress endpoint
        cached = cache.get(f"excel_task_{task_id}")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["percent"], 100)
        self.assertEqual(cached["sub_percent"], 100)

        from django.urls import reverse
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse("excel_upload_progress") + f"?task_id={task_id}")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["percent"], 100)
        self.assertEqual(payload["sub_percent"], 100)

        # Verify persisted field types & audit logs
        d.refresh_from_db()
        self.assertEqual(d.net_unit_area, Decimal("95.25"))
        self.assertEqual(d.floor_number, 4)
        self.assertTrue(d.is_equity_funded)
        self.assertEqual(d.applicant_phone, "09121112233")
        self.assertTrue(WorkflowSignatureLog.objects.filter(dossier=d, action="EXCEL_UPDATE").exists())
        self.assertGreaterEqual(DossierFieldChangeLog.objects.filter(dossier=d).count(), 4)

    def test_failure_report_is_slim_with_reason_summary_sheet(self):
        """Failure report has a grouped reason summary sheet and slim 4-column error rows."""
        from workflow.excel_utils import get_report_file_path

        headers = ["کد ملی متقاضی", "نام متقاضی", "پروژه", "شماره طبقه"]
        rows = [
            ["0999888771", "الف", "پروژه ۱", "2"],
            ["0999888772", "ب", "پروژه ۲", "3"],
            ["", "ج", "پروژه ۳", "1"],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["failed_count"], 3)
        self.assertIsNotNone(res["report_url"])

        report_uuid = res["report_url"].strip("/").split("/")[-1]
        fpath = get_report_file_path(report_uuid, self.admin_user.id)
        self.assertIsNotNone(fpath)

        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        self.assertEqual(wb.sheetnames[:2], ["خلاصه علل رد", "موارد رد شده"])

        sum_rows = list(wb["خلاصه علل رد"].iter_rows(values_only=True))
        self.assertEqual(sum_rows[0], ("علت رد", "تعداد"))
        counts_map = {r[0]: r[1] for r in sum_rows[1:]}
        self.assertEqual(counts_map.get("کد ملی متقاضی در سامانه یافت نشد."), 2)

        err_rows = list(wb["موارد رد شده"].iter_rows(values_only=True))
        self.assertEqual(err_rows[0], ("ردیف اکسل", "کد ملی", "نام متقاضی / همسر", "علت رد"))
        self.assertEqual(len(err_rows), 4)  # header + 3 rejected rows
        wb.close()

    def test_success_report_skips_unchanged_rows_and_original_columns(self):
        """Success report only includes changed dossiers and omits all original Excel columns."""
        from workflow.excel_utils import get_report_file_path

        HousingDossier.objects.create(
            national_id="0441112233",
            first_name="تغییریافته",
            archive_number=100201,
            project="پروژه قدیم",
        )
        HousingDossier.objects.create(
            national_id="0441112244",
            first_name="بدون‌تغییر",
            archive_number=100202,
            project="پروژه ثابت",
        )

        headers = ["کد ملی متقاضی", "نام پروژه مسکونی", "شماره طبقه"]
        rows = [
            ["0441112233", "پروژه جدید", None],
            ["0441112244", "پروژه ثابت", None],
        ]
        f = make_excel_file(headers, rows)
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 1)
        self.assertEqual(res["unchanged_count"], 1)
        self.assertIsNotNone(res["success_report_url"])

        report_uuid = res["success_report_url"].strip("/").split("/")[-1]
        fpath = get_report_file_path(report_uuid, self.admin_user.id)
        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        ws = wb.active
        out_rows = list(ws.iter_rows(values_only=True))
        self.assertEqual(
            out_rows[0],
            ("ردیف اکسل", "شماره بایگانی", "کد ملی", "نام متقاضی", "وضعیت", "توضیحات و تغییرات اعمال‌شده"),
        )
        self.assertEqual(len(out_rows), 2)  # header + 1 updated row only
        self.assertEqual(out_rows[1][2], "0441112233")
        wb.close()

    def test_update_all_unchanged_returns_no_success_report(self):
        """When all valid rows are unchanged, no empty success report workbook is created."""
        HousingDossier.objects.create(
            national_id="0441112255",
            first_name="ثابت",
            archive_number=100203,
            project="پروژه یکسان",
        )
        f = make_excel_file(["کد ملی متقاضی", "نام پروژه مسکونی"], [["0441112255", "پروژه یکسان"]])
        res = process_excel_update(f, user=self.admin_user, preview=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 0)
        self.assertEqual(res["unchanged_count"], 1)
        self.assertIsNone(res["success_report_url"])
