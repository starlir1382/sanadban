from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import json

from workflow.models import HousingDossier, UserProfile, BankLetter, WorkflowSignatureLog, ProjectBankMapping


class BankBatchingWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin_bank", password="password123")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.full_name = "کارشناس ارشد بانک"
        self.profile.role_title = "کارشناس ارشد بانک"
        self.profile.allowed_stages = "all"
        self.profile.save()
        self.client.login(username="admin_bank", password="password123")

        # Create sample project mapping
        ProjectBankMapping.objects.create(
            project_name="پروژه زیتون",
            bank_code="maskan",
            branch_name="مرکزی"
        )

        # Create sample dossiers in stage 6
        self.d1 = HousingDossier.objects.create(
            archive_number=7001,
            national_id="0371111111",
            full_name="متقاضی اول",
            project="پروژه زیتون",
            current_stage=6,
            is_sent_to_bank=False,
            is_added_to_bank_shipment_list=False,
        )
        self.d2 = HousingDossier.objects.create(
            archive_number=7002,
            national_id="0372222222",
            full_name="متقاضی دوم",
            project="پروژه زیتون",
            current_stage=6,
            is_sent_to_bank=False,
            is_added_to_bank_shipment_list=False,
        )

    def test_create_batch_does_not_fake_letter_number_or_advance_stage(self):
        """Creating a batch marks dossiers in shipment list, keeps them in stage 6, without fake letter numbers."""
        payload = {
            "action": "create_batch",
            "letter_type": "bank",
            "archive_numbers": [7001, 7002],
            "bank_code": "maskan",
            "project_name": "پروژه زیتون",
            "notes": "دسته آزمایشی محموله"
        }
        url = reverse("bank_letter_submit")
        res = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("batch_id", data)

        batch = BankLetter.objects.get(id=data["batch_id"])
        self.assertEqual(batch.status, "PENDING")
        self.assertTrue(batch.batch_code.startswith("BATCH-"))

        # Dossiers check:
        self.d1.refresh_from_db()
        self.d2.refresh_from_db()

        self.assertTrue(self.d1.is_added_to_bank_shipment_list)
        self.assertFalse(self.d1.is_sent_to_bank)
        self.assertEqual(self.d1.current_stage, 6)
        self.assertEqual(self.d1.bank_letter_number, "")
        self.assertEqual(self.d1.bank_letter_date, "")

    def test_finalize_batch_assigns_official_number_and_advances_stage(self):
        """Finalizing batch requires official number and date, transitions dossiers to stage 7."""
        # 1. Create batch
        create_payload = {
            "action": "create_batch",
            "letter_type": "bank",
            "archive_numbers": [7001, 7002],
            "bank_code": "maskan",
            "project_name": "پروژه زیتون",
        }
        url = reverse("bank_letter_submit")
        res_create = self.client.post(url, data=json.dumps(create_payload), content_type="application/json")
        batch_id = res_create.json()["batch_id"]

        # 2. Try finalize with empty fields -> should fail
        fail_payload = {
            "action": "finalize_batch",
            "batch_id": batch_id,
            "letter_number": "",
            "letter_date": ""
        }
        res_fail = self.client.post(url, data=json.dumps(fail_payload), content_type="application/json")
        self.assertEqual(res_fail.status_code, 400)

        # 3. Finalize with official secretariat letter number
        finalize_payload = {
            "action": "finalize_batch",
            "batch_id": batch_id,
            "letter_number": "۳۳۷۹۱",
            "letter_date": "۱۴۰۵/۰۱/۱۵",
            "notes": "ارسال رسمی با مانیفست"
        }
        res_fin = self.client.post(url, data=json.dumps(finalize_payload), content_type="application/json")
        self.assertEqual(res_fin.status_code, 200)
        data = res_fin.json()
        self.assertEqual(data["status"], "success")

        # Batch in DB
        batch = BankLetter.objects.get(id=batch_id)
        self.assertEqual(batch.status, "FINALIZED")
        self.assertEqual(batch.letter_number, "۳۳۷۹۱")
        self.assertEqual(batch.letter_date, "۱۴۰۵/۰۱/۱۵")

        # Dossiers check: advanced to stage 7 with correct number & date
        self.d1.refresh_from_db()
        self.d2.refresh_from_db()

        self.assertTrue(self.d1.is_sent_to_bank)
        self.assertEqual(self.d1.current_stage, 7)
        self.assertEqual(self.d1.bank_letter_number, "۳۳۷۹۱")
        self.assertEqual(self.d1.bank_letter_date, "۱۴۰۵/۰۱/۱۵")

        # Verify audit log created
        log = WorkflowSignatureLog.objects.filter(dossier=self.d1, action="BANK_LETTER").first()
        self.assertIsNotNone(log)
        self.assertIn("۳۳۷۹۱", log.notes)

    def test_cancel_pending_batch(self):
        """Canceling a pending batch unlinks dossiers and deletes the pending batch."""
        create_payload = {
            "action": "create_batch",
            "letter_type": "bank",
            "archive_numbers": [7001],
            "bank_code": "maskan",
        }
        url = reverse("bank_letter_submit")
        res = self.client.post(url, data=json.dumps(create_payload), content_type="application/json")
        batch_id = res.json()["batch_id"]

        cancel_payload = {
            "action": "cancel_batch",
            "batch_id": batch_id
        }
        res_cancel = self.client.post(url, data=json.dumps(cancel_payload), content_type="application/json")
        self.assertEqual(res_cancel.status_code, 200)

        self.assertFalse(BankLetter.objects.filter(id=batch_id).exists())
        self.d1.refresh_from_db()
        self.assertFalse(self.d1.is_added_to_bank_shipment_list)
        self.assertFalse(self.d1.is_sent_to_bank)
        self.assertEqual(self.d1.current_stage, 6)

    def test_detail_view_does_not_leak_premature_letter_number_for_unsent_dossier(self):
        """Dossier detail JSON does not output premature letter numbers when is_sent_to_bank is False."""
        url = reverse("dossier_detail", args=[self.d1.archive_number])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        dossier_data = json.loads(res.context["dossier_json"])
        form_data = dossier_data.get("form", {})
        self.assertEqual(form_data.get("bank_letter_number"), "")
        self.assertEqual(form_data.get("bank_letter_date"), "")
        self.assertFalse(form_data.get("is_sent_to_bank"))
