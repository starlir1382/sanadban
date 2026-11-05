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
            current_stage=3,
            archive_number=100016
        )

        # Add signatures for stage 1 (brokerage) and stage 10 (national_housing)
        DossierSignature.objects.create(
            dossier=d,
            slot_key="brokerage",
            signer_name="کارشناس کارگزاری",
            signed_date="1405/08/01 - 10:00"
        )
        DossierSignature.objects.create(
            dossier=d,
            slot_key="national_housing",
            signer_name="رئیس مسکن",
            signed_date="1405/08/05 - 12:00"
        )

        sigs, signed_count = get_dossier_signatures_summary(d)
        # brokerage is from stage 1 < 3, so it should stay
        self.assertIn("brokerage", sigs)
        # national_housing is from stage 10 >= 3, so it MUST be wiped!
        self.assertNotIn("national_housing", sigs)

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
