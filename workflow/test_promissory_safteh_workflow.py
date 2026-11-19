from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from workflow.models import HousingDossier, UserProfile, DossierFieldChangeLog
import json


class PromissorySaftehWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Operator with access to stages 17 and 18
        self.operator_user = User.objects.create_user(
            username="operator_tashilat",
            password="password123",
            first_name="کارشناس",
            last_name="تسهیلات"
        )
        self.operator_profile = self.operator_user.profile
        self.operator_profile.full_name = "کارشناس تسهیلات"
        self.operator_profile.allowed_stages = "17,18"
        self.operator_profile.can_sign = True
        self.operator_profile.save()

        # Test Dossier at Stage 17
        self.dossier = HousingDossier.objects.create(
            archive_number=100060,
            national_id="0099887766",
            full_name="علی رضایی",
            current_stage=17,
            status="IN_PROGRESS",
            is_locked=False,
            decile_loan_amount=4000000000,
            non_cash_preparation_amount=200000000,
        )

    def test_save_promissory_note_and_commitment_loan(self):
        """Test saving promissory note instead of checks for loan/tashilat."""
        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})

        payload = {
            "current_stage": 17,
            "loan_has_promissory_note": True,
            "loan_promissory_number": "س/۹۹۸۸۷۷",
            "loan_promissory_amount": 4000000000,
            "loan_promissory_date": "۱۴۰۵/۰۶/۲۰",
            "commitment_number": "۱۲۴۰۵/ت",
            "commitment_date": "۱۴۰۵/۰۶/۲۰",
            "loan_has_commitment_letter": True,
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        # Verify in DB
        self.dossier.refresh_from_db()
        self.assertTrue(self.dossier.loan_has_promissory_note)
        self.assertEqual(self.dossier.loan_promissory_number, "س/۹۹۸۸۷۷")
        self.assertEqual(self.dossier.loan_promissory_amount, 4000000000)
        self.assertEqual(self.dossier.loan_promissory_date, "۱۴۰۵/۰۶/۲۰")
        self.assertEqual(self.dossier.commitment_number, "۱۲۴۰۵/ت")
        self.assertEqual(self.dossier.commitment_date, "۱۴۰۵/۰۶/۲۰")
        self.assertTrue(self.dossier.loan_has_commitment_letter)

    def test_save_promissory_note_and_commitment_prep(self):
        """Test saving promissory note instead of checks for preparation."""
        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})

        payload = {
            "current_stage": 18,
            "prep_has_promissory_note": True,
            "prep_promissory_number": "س/۱۱۲۲۳۳",
            "prep_promissory_amount": 200000000,
            "prep_promissory_date": "۱۴۰۵/۰۷/۱۵",
            "prep_commitment_number": "۵۵۴۴۳/ت",
            "prep_commitment_date": "۱۴۰۵/۰۷/۱۵",
            "prep_has_commitment_letter": True,
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        # Verify in DB
        self.dossier.refresh_from_db()
        self.assertTrue(self.dossier.prep_has_promissory_note)
        self.assertEqual(self.dossier.prep_promissory_number, "س/۱۱۲۲۳۳")
        self.assertEqual(self.dossier.prep_promissory_amount, 200000000)
        self.assertEqual(self.dossier.prep_promissory_date, "۱۴۰۵/۰۷/۱۵")
        self.assertEqual(self.dossier.prep_commitment_number, "۵۵۴۴۳/ت")
        self.assertEqual(self.dossier.prep_commitment_date, "۱۴۰۵/۰۷/۱۵")
        self.assertTrue(self.dossier.prep_has_commitment_letter)

    def test_detail_view_includes_promissory_fields(self):
        """Test dossier detail view includes all promissory and commitment fields in initial form data."""
        self.dossier.loan_has_promissory_note = True
        self.dossier.loan_promissory_number = "س/۷۷۶۶۵۵"
        self.dossier.loan_promissory_amount = 3500000000
        self.dossier.loan_promissory_date = "۱۴۰۵/۰۱/۰۱"
        self.dossier.loan_has_commitment_letter = True
        self.dossier.prep_has_promissory_note = True
        self.dossier.prep_promissory_number = "س/۴۴۳۳۲۲"
        self.dossier.prep_promissory_amount = 180000000
        self.dossier.prep_promissory_date = "۱۴۰۵/۰۲/۰۲"
        self.dossier.prep_commitment_number = "۹۹۸۸/ت"
        self.dossier.prep_commitment_date = "۱۴۰۵/۰۲/۰۲"
        self.dossier.prep_has_commitment_letter = True
        self.dossier.save()

        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_detail", kwargs={"pk": self.dossier.archive_number})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        dossier_json = resp.context.get("dossier_json")
        self.assertIsNotNone(dossier_json)
        dossier_data = json.loads(dossier_json)
        form = dossier_data.get("form")
        self.assertIsNotNone(form)
        self.assertTrue(form["loan_has_promissory_note"])
        self.assertEqual(form["loan_promissory_number"], "س/۷۷۶۶۵۵")
        self.assertEqual(form["loan_promissory_amount"], 3500000000)
        self.assertEqual(form["loan_promissory_date"], "۱۴۰۵/۰۱/۰۱")
        self.assertTrue(form["loan_has_commitment_letter"])

        self.assertTrue(form["prep_has_promissory_note"])
        self.assertEqual(form["prep_promissory_number"], "س/۴۴۳۳۲۲")
        self.assertEqual(form["prep_promissory_amount"], 180000000)
        self.assertEqual(form["prep_promissory_date"], "۱۴۰۵/۰۲/۰۲")
        self.assertEqual(form["prep_commitment_number"], "۹۹۸۸/ت")
        self.assertEqual(form["prep_commitment_date"], "۱۴۰۵/۰۲/۰۲")
        self.assertTrue(form["prep_has_commitment_letter"])

    def test_dossier_get_check_entries_helpers(self):
        """Test get_check_entries and get_preparation_check_entries methods."""
        self.dossier.check_entries_json = json.dumps([
            {"row_number": 1, "cash_date": "۱۴۰۶/۰۱/۰۱", "check_amount": 1000000000, "check_sayadi_code": "", "bank_name": ""}
        ])
        self.dossier.preparation_check_entries_json = json.dumps([
            {"row_number": 1, "cash_date": "۱۴۰۵/۰۸/۰۱", "check_amount": 50000000, "check_sayadi_code": "", "bank_name": ""}
        ])
        self.dossier.save()

        loan_entries = self.dossier.get_check_entries()
        prep_entries = self.dossier.get_preparation_check_entries()

        self.assertEqual(len(loan_entries), 1)
        self.assertEqual(loan_entries[0]["cash_date"], "۱۴۰۶/۰۱/۰۱")
        self.assertEqual(loan_entries[0]["check_amount"], 1000000000)

        self.assertEqual(len(prep_entries), 1)
        self.assertEqual(prep_entries[0]["cash_date"], "۱۴۰۵/۰۸/۰۱")
        self.assertEqual(prep_entries[0]["check_amount"], 50000000)

    def test_checks_deleted_when_promissory_selected_loan(self):
        """Test that checks are deleted and cannot be re-created when loan promissory note is selected."""
        from workflow.models import DossierCheck
        # Create existing checks
        DossierCheck.objects.create(
            dossier=self.dossier, check_type="LOAN", row_number=1, cash_date="۱۴۰۶/۰۱/۰۱",
            check_amount=2000000000, check_sayadi_code="1234567890123456", bank_name="بانک ملی"
        )
        self.dossier.check_entries_json = json.dumps([
            {"row_number": 1, "cash_date": "۱۴۰۶/۰۱/۰۱", "check_amount": 2000000000, "check_sayadi_code": "1234567890123456", "bank_name": "بانک ملی"}
        ])
        self.dossier.check_count = 1
        self.dossier.total_check_amount = 2000000000
        self.dossier.save()

        self.assertEqual(self.dossier.check_items.filter(check_type="LOAN").count(), 1)

        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})

        payload = {
            "current_stage": 17,
            "loan_has_promissory_note": True,
            "loan_promissory_number": "س/۵۵۴۴۳۳",
            "loan_promissory_amount": 4000000000,
            "loan_promissory_date": "۱۴۰۵/۰۶/۲۰",
            "loan_has_commitment_letter": True,
            "loan_promissory_installments": [
                {"row_number": 1, "due_date": "۱۴۰۶/۰۶/۲۰", "amount": 2000000000},
                {"row_number": 2, "due_date": "۱۴۰۷/۰۶/۲۰", "amount": 2000000000},
            ],
            # Even if frontend payload still had check_entries, they MUST be wiped
            "check_entries": [
                {"row_number": 1, "cash_date": "۱۴۰۶/۰۱/۰۱", "check_amount": 2000000000}
            ],
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        self.dossier.refresh_from_db()
        self.assertTrue(self.dossier.loan_has_promissory_note)
        self.assertEqual(self.dossier.check_items.filter(check_type="LOAN").count(), 0)
        self.assertEqual(self.dossier.check_entries_json, "[]")
        self.assertEqual(self.dossier.check_count, 0)
        self.assertEqual(self.dossier.total_check_amount, 0)
        self.assertEqual(len(self.dossier.get_loan_promissory_installments()), 2)

    def test_checks_deleted_when_promissory_selected_prep(self):
        """Test that preparation checks are deleted when prep promissory note is selected."""
        from workflow.models import DossierCheck
        DossierCheck.objects.create(
            dossier=self.dossier, check_type="PREPARATION", row_number=1, cash_date="۱۴۰۵/۰۵/۱۵",
            check_amount=100000000, check_sayadi_code="9876543210987654", bank_name="بانک مسکن"
        )
        self.dossier.preparation_check_entries_json = json.dumps([
            {"row_number": 1, "cash_date": "۱۴۰۵/۰۵/۱۵", "check_amount": 100000000}
        ])
        self.dossier.preparation_check_count = 1
        self.dossier.total_preparation_check_amount = 100000000
        self.dossier.save()

        self.assertEqual(self.dossier.check_items.filter(check_type="PREPARATION").count(), 1)

        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})

        payload = {
            "current_stage": 18,
            "prep_has_promissory_note": True,
            "prep_promissory_number": "س/۹۹۸۸۰۰",
            "prep_promissory_amount": 200000000,
            "prep_promissory_date": "۱۴۰۵/۰۲/۱۵",
            "prep_has_commitment_letter": True,
            "prep_promissory_installments": [
                {"row_number": 1, "due_date": "۱۴۰۵/۰۸/۱۵", "amount": 100000000},
                {"row_number": 2, "due_date": "۱۴۰۶/۰۲/۱۵", "amount": 100000000},
            ],
            "preparation_check_entries": [
                {"row_number": 1, "cash_date": "۱۴۰۵/۰۵/۱۵", "check_amount": 100000000}
            ],
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        self.dossier.refresh_from_db()
        self.assertTrue(self.dossier.prep_has_promissory_note)
        self.assertEqual(self.dossier.check_items.filter(check_type="PREPARATION").count(), 0)
        self.assertEqual(self.dossier.preparation_check_entries_json, "[]")
        self.assertEqual(self.dossier.preparation_check_count, 0)
        self.assertEqual(self.dossier.total_preparation_check_amount, 0)
        self.assertEqual(len(self.dossier.get_prep_promissory_installments()), 2)

    def test_print_promissory_commitment_views(self):
        """Test printing commitment letter for both loan and prep."""
        self.dossier.loan_has_promissory_note = True
        self.dossier.loan_promissory_number = "س/۸۸۷۷۶۶"
        self.dossier.loan_promissory_amount = 4000000000
        self.dossier.loan_promissory_date = "۱۴۰۵/۰۳/۰۱"
        self.dossier.loan_promissory_installments_json = json.dumps([
            {"row_number": 1, "due_date": "۱۴۰۶/۰۳/۰۱", "amount": 2000000000},
            {"row_number": 2, "due_date": "۱۴۰۷/۰۳/۰۱", "amount": 2000000000},
        ])

        self.dossier.prep_has_promissory_note = True
        self.dossier.prep_promissory_number = "س/۳۳۲۲۱۱"
        self.dossier.prep_promissory_amount = 300000000
        self.dossier.prep_promissory_date = "۱۴۰۵/۰۴/۰۱"
        self.dossier.prep_promissory_installments_json = json.dumps([
            {"row_number": 1, "due_date": "۱۴۰۵/۱۰/۰۱", "amount": 150000000},
            {"row_number": 2, "due_date": "۱۴۰۶/۰۴/۰۱", "amount": 150000000},
        ])
        self.dossier.save()

        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_print_promissory_commitment", kwargs={"pk": self.dossier.archive_number})

        # Test Loan print
        resp_loan = self.client.get(f"{url}?type=loan")
        self.assertEqual(resp_loan.status_code, 200)
        self.assertContains(resp_loan, "س/۸۸۷۷۶۶")
        self.assertContains(resp_loan, "تسهیلات وام دهک")
        self.assertContains(resp_loan, "تعهدنامه اقساط و سفته تضمین")
        self.assertContains(resp_loan, "امضاء و اثر انگشت متقاضی")

        # Test Prep print
        resp_prep = self.client.get(f"{url}?type=prep")
        self.assertEqual(resp_prep.status_code, 200)
        self.assertContains(resp_prep, "س/۳۳۲۲۱۱")
        self.assertContains(resp_prep, "آماده‌سازی")
        self.assertContains(resp_prep, "امضاء و اثر انگشت متقاضی")

    def test_upload_promissory_and_commitment_scans(self):
        """Test uploading commitment letter and promissory note scans via upload_scan_attachment_view."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username="operator_tashilat", password="password123")
        url = reverse("dossier_upload_scan", kwargs={"pk": self.dossier.archive_number})

        test_file = SimpleUploadedFile("commitment.jpg", b"fake image bytes", content_type="image/jpeg")

        resp = self.client.post(url, {
            "file": test_file,
            "doc_type": "COMMITMENT_LETTER",
            "stage": 17,
            "title": "تعهدنامه امضا شده متقاضی (تسهیلات)"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["attachment"]["doc_type"], "COMMITMENT_LETTER")

        test_file_2 = SimpleUploadedFile("safteh.jpg", b"fake promissory image bytes", content_type="image/jpeg")
        resp2 = self.client.post(url, {
            "file": test_file_2,
            "doc_type": "PROMISSORY_NOTE",
            "stage": 18,
            "title": "اسکن سفته تضمین (آماده‌سازی)"
        })
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "success")
        self.assertEqual(data2["attachment"]["doc_type"], "PROMISSORY_NOTE")
