import io
import json
import openpyxl
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from workflow.models import DirectorateShipment, DossierCheck, HousingDossier, UserProfile


class Stage1718ExcelTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Target user: alireza_nazari
        self.alireza = User.objects.create_user(username="alireza_nazari", password="password123")
        self.alireza_prof, _ = UserProfile.objects.get_or_create(user=self.alireza)
        self.alireza_prof.allowed_stages = "17,18"
        self.alireza_prof.role_title = "کارشناس پیگیری تسهیلات و آماده‌سازی"
        self.alireza_prof.save()

        # Other user: expert_stage17 (should not have access to Alireza-only excel hub)
        self.other_user = User.objects.create_user(username="expert_stg17", password="password123")
        self.other_prof, _ = UserProfile.objects.get_or_create(user=self.other_user)
        self.other_prof.allowed_stages = "17"
        self.other_prof.save()

        # Sample dossiers in stage 17 and 18
        self.d17 = HousingDossier.objects.create(
            national_id="0381112233",
            full_name="متقاضی مرحله ۱۷",
            archive_number=100171,
            current_stage=17,
            loan_visit_date="1403/08/10",
        )
        self.d18 = HousingDossier.objects.create(
            national_id="0384445566",
            full_name="متقاضی مرحله ۱۸",
            archive_number=100181,
            current_stage=18,
            prep_visit_date="1403/08/15",
        )

    def test_acl_only_alireza_nazari_can_access(self):
        """Only alireza_nazari can open stage 17/18 excel hub; others get 403."""
        # 1. Other user gets 403
        self.client.force_login(self.other_user)
        resp_denied = self.client.get(reverse("stage17_18_excel_hub"))
        self.assertEqual(resp_denied.status_code, 403)

        # 2. Alireza Nazari gets 200
        self.client.force_login(self.alireza)
        resp_ok = self.client.get(reverse("stage17_18_excel_hub"))
        self.assertEqual(resp_ok.status_code, 200)
        html = resp_ok.content.decode("utf-8")
        self.assertIn("مرکز ورود و خروج داده‌های اکسل (مراحل ۱۷ و ۱۸)", html)
        self.assertIn("دانلود قالب اکسل مرحله ۱۷", html)
        self.assertIn("دانلود قالب اکسل مرحله ۱۸", html)

    def test_ui_buttons_visibility(self):
        """UI button 'اکسل مراحل ۱۷ و ۱۸' is rendered for Alireza Nazari and hidden for others."""
        # Alireza sees button in dossier list
        self.client.force_login(self.alireza)
        resp_ali = self.client.get(reverse("dossier_list"))
        self.assertEqual(resp_ali.status_code, 200)
        self.assertIn("اکسل مراحل ۱۷ و ۱۸", resp_ali.content.decode("utf-8"))

        # Other user does not see it
        self.client.force_login(self.other_user)
        resp_other = self.client.get(reverse("dossier_list"))
        self.assertEqual(resp_other.status_code, 200)
        self.assertNotIn("اکسل مراحل ۱۷ و ۱۸", resp_other.content.decode("utf-8"))

    def test_template_download_stage17_and_18(self):
        """Template downloads return valid xlsx files with correct headers and RTL."""
        self.client.force_login(self.alireza)

        # Stage 17 template (strictly per user: national id, commitment_number, commitment_date, supported_institution, decile_loan_bank, checks)
        resp17 = self.client.get(reverse("stage17_18_template_download", kwargs={"stage": 17}))
        self.assertEqual(resp17.status_code, 200)
        self.assertIn("spreadsheetml.sheet", resp17["Content-Type"])
        self.assertIn("template_stage_17_tashilat.xlsx", resp17["Content-Disposition"])

        wb17 = openpyxl.load_workbook(io.BytesIO(resp17.content))
        ws17 = wb17.active
        self.assertTrue(ws17.views.sheetView[0].rightToLeft)
        row17_headers = [c.value for c in ws17[1]]
        self.assertIn("کد ملی", row17_headers)
        self.assertIn("شماره تعهدنامه", row17_headers)
        self.assertIn("تاریخ تعهدنامه", row17_headers)
        self.assertIn("نهاد تحت حمایت", row17_headers)
        self.assertIn("بانک عامل تسهیلات", row17_headers)
        self.assertIn("تاریخ چک 1", row17_headers)
        self.assertIn("مقدار چک 1", row17_headers)
        self.assertIn("کد صیادی چک 1", row17_headers)
        self.assertIn("نام بانک چک 1", row17_headers)

        # Stage 18 template (matches user specifications)
        resp18 = self.client.get(reverse("stage17_18_template_download", kwargs={"stage": 18}))
        self.assertEqual(resp18.status_code, 200)
        self.assertIn("template_stage_18_amadesazi.xlsx", resp18["Content-Disposition"])

        wb18 = openpyxl.load_workbook(io.BytesIO(resp18.content))
        ws18 = wb18.active
        self.assertTrue(ws18.views.sheetView[0].rightToLeft)
        row18_headers = [c.value for c in ws18[1]]
        self.assertIn("کد ملی", row18_headers)
        self.assertIn("نامه راه شهرسازی", row18_headers)
        self.assertIn("مبلغ پیش‌پرداخت", row18_headers)
        self.assertIn("کد پیگیری پیش‌پرداخت", row18_headers)
        self.assertIn("مبلغ اجاره", row18_headers)
        self.assertIn("کد پیگیری اجاره", row18_headers)
        self.assertIn("تاریخ چک 1", row18_headers)
        self.assertIn("مقدار چک 1", row18_headers)
        self.assertIn("کد صیادی چک 1", row18_headers)
        self.assertIn("نام بانک چک 1", row18_headers)
        # Excluded fields must not be present
        self.assertNotIn("تاریخ آخرین وضعیت", row18_headers)
        self.assertNotIn("ارزیابی - دهک", row18_headers)
        self.assertNotIn("اسکن چک", row18_headers)

    def test_data_export_stage17_and_18(self):
        """Exporting existing data returns valid xlsx with records."""
        self.client.force_login(self.alireza)

        resp17 = self.client.get(reverse("stage17_18_data_export", kwargs={"stage": 17}))
        self.assertEqual(resp17.status_code, 200)
        wb17 = openpyxl.load_workbook(io.BytesIO(resp17.content))
        ws17 = wb17.active
        nat_ids17 = [row[1] for row in ws17.iter_rows(min_row=2, values_only=True)]
        self.assertIn("0381112233", nat_ids17)

        resp18 = self.client.get(reverse("stage17_18_data_export", kwargs={"stage": 18}))
        self.assertEqual(resp18.status_code, 200)
        wb18 = openpyxl.load_workbook(io.BytesIO(resp18.content))
        ws18 = wb18.active
        nat_ids18 = [row[2] for row in ws18.iter_rows(min_row=2, values_only=True)]
        self.assertIn("0384445566", nat_ids18)

    def test_stage17_upload_comprehensive(self):
        """Uploading Stage 17 Excel updates commitment_number, commitment_date, supported_institution, decile_loan_bank, and loan checks."""
        self.client.force_login(self.alireza)

        headers = [
            "ردیف", "کد ملی", "شماره تعهدنامه", "تاریخ تعهدنامه", "نهاد تحت حمایت", "بانک عامل تسهیلات",
            "تاریخ چک 1", "مقدار چک 1", "کد صیادی چک 1", "نام بانک چک 1",
            "تاریخ چک 2", "مقدار چک 2", "کد صیادی چک 2", "نام بانک چک 2",
        ]
        row_data = [
            1, "0381112233", "TH-98765", "1403/08/25", "کمیته امداد امام خمینی (ره)", "بانک مسکن",
            "1404/01/15", 500000000, "1234567890123456", "بانک مسکن",
            "1404/07/15", 500000000, "9876543210987654", "بانک مسکن",
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        ws.append(row_data)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        uploaded = SimpleUploadedFile(
            "tashilat_batch.xlsx",
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        resp = self.client.post(
            reverse("stage17_18_excel_upload", kwargs={"stage": 17}),
            {"excel_file": uploaded},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["stage"], 17)
        self.assertEqual(data["updated_count"], 1)

        # Check dossier updates
        self.d17.refresh_from_db()
        self.assertEqual(self.d17.commitment_number, "TH-98765")
        self.assertEqual(self.d17.commitment_date, "1403/08/25")
        self.assertEqual(self.d17.supported_institution, "کمیته امداد امام خمینی (ره)")
        self.assertEqual(self.d17.decile_loan_bank, "بانک مسکن")
        self.assertTrue(self.d17.is_decile_loan_confirmed)
        self.assertEqual(self.d17.check_count, 2)
        self.assertEqual(self.d17.total_check_amount, 1000000000)

        checks_db = DossierCheck.objects.filter(dossier=self.d17, check_type="LOAN").order_by("row_number")
        self.assertEqual(checks_db.count(), 2)
        self.assertEqual(checks_db[0].cash_date, "1404/01/15")
        self.assertEqual(checks_db[0].check_amount, 500000000)
        self.assertEqual(checks_db[0].check_sayadi_code, "1234567890123456")
        self.assertEqual(checks_db[0].bank_name, "بانک مسکن")

    def test_stage18_upload_comprehensive(self):
        """Uploading Stage 18 Excel updates 5 fields, 7 checks, visit date, and batches sent dossiers."""
        self.client.force_login(self.alireza)

        # Build workbook with exact user fields
        headers = [
            "ردیف", "نام", "کد ملی", "شماره تلفن", "پلاک اصلی", "پلاک مفروز", "پلاک فرعی", "قطعه",
            "پیمانکار", "محل پرونده", "نام دفترخانه", "تاریخ تغییر محل پرونده", "وضعیت سند",
            "نامه راه شهرسازی", "مبلغ پیش‌پرداخت", "کد پیگیری پیش‌پرداخت", "مبلغ اجاره", "کد پیگیری اجاره",
            "تاریخ چک 1", "مقدار چک 1", "کد صیادی چک 1", "نام بانک چک 1",
            "تاریخ چک 2", "مقدار چک 2", "کد صیادی چک 2", "نام بانک چک 2",
        ]
        row_data = [
            1, "سید محمد جواد مدنی", "0384445566", "09122526503", "291", "30789", "30833", "",
            "سانیار آفرین ایرانیان", "کارگزاری ثبت چک ها", "", "1405/08/21", "ارسال شده",
            "405/2776", 184280806, "814565286779", 72300128, "814565289051",
            "1406/02/20", 184250000, "9172010094099580", "سپه",
            "1406/08/20", 184250000, "5905010094099581", "سپه",
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        ws.append(row_data)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        uploaded = SimpleUploadedFile(
            "amadesazi_batch.xlsx",
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        resp = self.client.post(
            reverse("stage17_18_excel_upload", kwargs={"stage": 18}),
            {"excel_file": uploaded},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["stage"], 18)
        self.assertEqual(data["updated_count"], 1)
        self.assertEqual(data["shipped_count"], 1)
        self.assertIsNotNone(data["shipment_code"])

        # Check dossier updates
        self.d18.refresh_from_db()
        self.assertEqual(self.d18.rah_letter, "405/2776")
        self.assertEqual(self.d18.cash_preparation_amount, 184280806)
        self.assertEqual(self.d18.prepayment_code, "814565286779")
        self.assertEqual(self.d18.tenant_price, 72300128)
        self.assertEqual(self.d18.tenant_code, "814565289051")
        self.assertEqual(self.d18.prep_visit_date, "1405/08/21")
        self.assertTrue(self.d18.is_prep_visited)

        # Check checks
        self.assertTrue(self.d18.is_preparation_checks_confirmed)
        self.assertEqual(self.d18.preparation_check_count, 2)
        self.assertEqual(self.d18.total_preparation_check_amount, 368500000)

        checks_db = DossierCheck.objects.filter(dossier=self.d18, check_type="PREPARATION").order_by("row_number")
        self.assertEqual(checks_db.count(), 2)
        chk1 = checks_db[0]
        self.assertEqual(chk1.cash_date, "1406/02/20")
        self.assertEqual(chk1.check_amount, 184250000)
        self.assertEqual(chk1.check_sayadi_code, "9172010094099580")
        self.assertEqual(chk1.bank_name, "سپه")

        # Check batch shipment
        self.assertTrue(self.d18.is_prep_sent_to_directorate)
        self.assertIsNotNone(self.d18.prep_directorate_shipment)
        shipment = self.d18.prep_directorate_shipment
        self.assertEqual(shipment.shipment_type, "PREP")
        self.assertEqual(shipment.shipment_code, data["shipment_code"])
        self.assertIn("علیرضا نظری", shipment.note)
