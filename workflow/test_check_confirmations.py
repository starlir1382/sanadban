from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from workflow.models import HousingDossier, UserProfile, WorkflowSignatureLog, DossierFieldChangeLog
import json


class CheckConfirmationWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Normal Operator for Stage 18
        self.operator_user = User.objects.create_user(
            username="operator_prep",
            password="password123",
            first_name="کارشناس",
            last_name="آماده‌سازی"
        )
        self.operator_profile = self.operator_user.profile
        self.operator_profile.full_name = "کارشناس آماده‌سازی"
        self.operator_profile.allowed_stages = "18"
        self.operator_profile.can_sign = True
        self.operator_profile.is_check_admin = False
        self.operator_profile.is_housing_chief = False
        self.operator_profile.save()

        # 2. Check Admin
        self.check_admin_user = User.objects.create_user(
            username="check_admin",
            password="password123",
            first_name="مدیر",
            last_name="چک‌ها"
        )
        self.check_admin_profile = self.check_admin_user.profile
        self.check_admin_profile.full_name = "مدیر چک‌ها"
        self.check_admin_profile.allowed_stages = "17,18"
        self.check_admin_profile.can_sign = True
        self.check_admin_profile.is_check_admin = True
        self.check_admin_profile.is_housing_chief = False
        self.check_admin_profile.save()

        # 3. Test Dossier at Stage 18
        self.dossier = HousingDossier.objects.create(
            archive_number=100050,
            national_id="0011223344",
            full_name="محمد تست",
            current_stage=18,
            status="IN_PROGRESS",
            is_locked=False,
            is_cash_rent_confirmed=False,
            is_preparation_checks_confirmed=False,
            is_decile_loan_confirmed=False
        )

    def test_operator_ticks_check_confirmations_and_records_audit_logs(self):
        self.client.login(username="operator_prep", password="password123")
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})
        
        # Operator ticks both cash rent confirmed and prep checks confirmed
        payload = {
            "current_stage": 18,
            "is_cash_rent_confirmed": True,
            "is_preparation_checks_confirmed": True,
            "tenant_price": 50000000,
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        # Verify response returned the confirmer info
        self.assertEqual(data["cash_rent_confirmed_by"], "کارشناس آماده‌سازی")
        self.assertTrue(data["cash_rent_confirmed_at"])
        self.assertEqual(data["prep_checks_confirmed_by"], "کارشناس آماده‌سازی")
        self.assertTrue(data["prep_checks_confirmed_at"])

        # Reload dossier from DB and verify fields
        self.dossier.refresh_from_db()
        self.assertTrue(self.dossier.is_cash_rent_confirmed)
        self.assertEqual(self.dossier.cash_rent_confirmed_by, "کارشناس آماده‌سازی")
        self.assertIsNotNone(self.dossier.cash_rent_confirmed_at)
        self.assertTrue(self.dossier.is_preparation_checks_confirmed)
        self.assertEqual(self.dossier.prep_checks_confirmed_by, "کارشناس آماده‌سازی")
        self.assertIsNotNone(self.dossier.prep_checks_confirmed_at)
        self.assertTrue(self.dossier.has_confirmed_checks)
        self.assertTrue(self.dossier.has_pending_check_signature)

        # Verify WorkflowSignatureLog was created with CONFIRM_CHECK
        sig_logs = WorkflowSignatureLog.objects.filter(dossier=self.dossier, action="CONFIRM_CHECK")
        self.assertEqual(sig_logs.count(), 2)
        self.assertTrue(any("اجاره" in log.notes for log in sig_logs))
        self.assertTrue(any("آماده‌سازی" in log.notes for log in sig_logs))

        # Verify DossierFieldChangeLog was created
        change_logs = DossierFieldChangeLog.objects.filter(dossier=self.dossier)
        self.assertTrue(change_logs.filter(field_name="is_cash_rent_confirmed").exists())
        self.assertTrue(change_logs.filter(field_name="is_preparation_checks_confirmed").exists())

    def test_operator_cannot_sign_stage_18(self):
        # Operator cannot electronically sign to advance stage 18
        self.client.login(username="operator_prep", password="password123")
        url = reverse("dossier_sign", kwargs={"pk": self.dossier.archive_number})
        resp = self.client.post(url, data=json.dumps({"notes": "تایید اپراتور"}), content_type="application/json")
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("مدیر کارگزاری چک", data["message"])

        # Stage remains 18
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.current_stage, 18)

    def test_check_admin_can_sign_stage_18_and_advance(self):
        # First tick the boxes
        self.dossier.is_cash_rent_confirmed = True
        self.dossier.cash_rent_confirmed_by = "کارشناس آماده‌سازی"
        self.dossier.is_preparation_checks_confirmed = True
        self.dossier.prep_checks_confirmed_by = "کارشناس آماده‌سازی"
        self.dossier.save()

        # Check Admin logs in and signs
        self.client.login(username="check_admin", password="password123")
        url = reverse("dossier_sign", kwargs={"pk": self.dossier.archive_number})
        resp = self.client.post(url, data=json.dumps({"notes": "تایید نهایی چک‌ها توسط مدیر چک"}), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        # Dossier advanced to Stage 19 (تسویه با پیمانکار)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.current_stage, 19)

    def test_checks_ticked_list_filter(self):
        # Dossier A: Stage 18, ticked -> should appear in filter
        self.dossier.is_cash_rent_confirmed = True
        self.dossier.save()

        # Dossier B: Stage 18, unticked -> should NOT appear
        dossier_b = HousingDossier.objects.create(
            archive_number=100051,
            national_id="0011223355",
            full_name="علی تست",
            current_stage=18,
            status="IN_PROGRESS",
            is_locked=False,
            is_cash_rent_confirmed=False
        )

        # Check Admin requests status=checks_ticked
        self.client.login(username="check_admin", password="password123")
        resp = self.client.get(reverse("dossier_list") + "?status=checks_ticked")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "100050")
        self.assertNotContains(resp, "100051")
