from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import json

from workflow.models import (
    HousingDossier,
    UserProfile,
    DossierSignature,
    WorkflowSignatureLog,
)


class Stage1718SigningAndWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Alireza Nazari user
        self.alireza = User.objects.create_user(
            username="alireza_nazari",
            password="password123",
            is_staff=False,
            is_superuser=False,
        )
        self.alireza_profile, _ = UserProfile.objects.get_or_create(user=self.alireza)
        self.alireza_profile.full_name = "علیرضا نظری"
        self.alireza_profile.role_title = "مسئول تسهیلات و آماده‌سازی"
        self.alireza_profile.allowed_stages = "17,18"
        self.alireza_profile.can_sign = True
        self.alireza_profile.is_active_expert = True
        self.alireza_profile.save()

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            password="password123",
            email="admin@example.com",
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin_user)
        self.admin_profile.full_name = "مدیر کل"
        self.admin_profile.allowed_stages = "all"
        self.admin_profile.can_sign = True
        self.admin_profile.is_active_expert = True
        self.admin_profile.save()

        # Create dossiers at Stage 8 (qualifying for archive numbers)
        self.d1 = HousingDossier.objects.create(
            national_id="0011111111",
            first_name="علی",
            last_name="رضایی",
            current_stage=8,
            archive_number=100001,
            is_locked=False,
            is_decile_loan_confirmed=True,
            loan_visit_date="1403/08/10",
        )
        self.d2 = HousingDossier.objects.create(
            national_id="0022222222",
            first_name="رضا",
            last_name="محمدی",
            current_stage=8,
            archive_number=100002,
            is_locked=False,
            is_preparation_checks_confirmed=True,
            prep_visit_date="1403/08/15",
        )
        self.d3 = HousingDossier.objects.create(
            national_id="0033333333",
            first_name="حسین",
            last_name="کریمی",
            current_stage=17,
            archive_number=100003,
            is_locked=False,
        )

    def test_alireza_nazari_can_batch_sign_stage17_without_advancing_stage8(self):
        """
        When Alireza Nazari signs Stage 17 on a dossier currently in Stage 8:
        - Stage 17 signature slot is stamped.
        - WorkflowSignatureLog records Stage 17 signature.
        - Dossier's current_stage remains at 8 (not changed).
        """
        self.client.login(username="alireza_nazari", password="password123")

        url = reverse("dossiers_batch_sign")
        payload = {
            "archive_numbers": [self.d1.archive_number],
            "target_stage": 17,
            "notes": "امضای تسهیلات چک وام دهک توسط علیرضا نظری",
        }
        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["signed_count"], 1)

        self.d1.refresh_from_db()
        # Crucial: current_stage must remain 8
        self.assertEqual(self.d1.current_stage, 8)
        self.assertTrue(self.d1.is_decile_loan_confirmed)

        # Signature slot must be stamped
        sig = DossierSignature.objects.filter(dossier=self.d1, slot_key="decile_facility").first()
        self.assertIsNotNone(sig)
        self.assertEqual(sig.signer_name, "علیرضا نظری")

        # Signature log must exist
        log = WorkflowSignatureLog.objects.filter(dossier=self.d1, from_stage__contains="17").first()
        self.assertIsNotNone(log)

    def test_alireza_nazari_can_batch_sign_stage18_without_advancing_stage8(self):
        """
        When Alireza Nazari signs Stage 18 on a dossier in Stage 8:
        - Stage 18 signature slot is stamped.
        - Dossier remains at Stage 8.
        - Preparation confirmed flags are true.
        """
        self.client.login(username="alireza_nazari", password="password123")

        url = reverse("dossiers_batch_sign")
        payload = {
            "archive_numbers": [self.d2.archive_number],
            "target_stage": 18,
            "notes": "امضای آماده‌سازی توسط علیرضا نظری",
        }
        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        self.d2.refresh_from_db()
        self.assertEqual(self.d2.current_stage, 8)
        self.assertTrue(self.d2.is_preparation_checks_confirmed)
        self.assertTrue(self.d2.is_cash_rent_confirmed)

        sig = DossierSignature.objects.filter(dossier=self.d2, slot_key="revenue").first()
        self.assertIsNotNone(sig)
        self.assertEqual(sig.signer_name, "علیرضا نظری")

    def test_alireza_nazari_can_batch_sign_both_17_and_18(self):
        """Signing with target_stage='both' stamps both stages 17 and 18."""
        self.client.login(username="alireza_nazari", password="password123")

        url = reverse("dossiers_batch_sign")
        payload = {
            "archive_numbers": [self.d1.archive_number],
            "target_stage": "both",
        }
        resp = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.d1.refresh_from_db()
        self.assertEqual(self.d1.current_stage, 8)

        self.assertTrue(DossierSignature.objects.filter(dossier=self.d1, slot_key="decile_facility").exists())
        self.assertTrue(DossierSignature.objects.filter(dossier=self.d1, slot_key="revenue").exists())

    def test_separated_visit_date_filters_and_counts(self):
        """
        has_loan_visit_date and has_prep_visit_date are separate and filter correctly:
        - d1 has loan_visit_date='1403/08/10'
        - d2 has prep_visit_date='1403/08/15'
        """
        self.client.login(username="admin_user", password="password123")

        # Filter loan visit date
        r_loan = self.client.get(reverse("dossier_list"), {"status": "has_loan_visit_date"})
        self.assertEqual(r_loan.status_code, 200)
        loan_dossiers = list(r_loan.context["dossiers"])
        self.assertIn(self.d1, loan_dossiers)
        self.assertNotIn(self.d2, loan_dossiers)
        self.assertEqual(r_loan.context["loan_visit_date_cnt"], 1)

        # Filter prep visit date
        r_prep = self.client.get(reverse("dossier_list"), {"status": "has_prep_visit_date"})
        self.assertEqual(r_prep.status_code, 200)
        prep_dossiers = list(r_prep.context["dossiers"])
        self.assertIn(self.d2, prep_dossiers)
        self.assertNotIn(self.d1, prep_dossiers)
        self.assertEqual(r_prep.context["prep_visit_date_cnt"], 1)

    def test_workflow_track_stage17_and_18_display_two_numbers(self):
        """
        Stages 17 & 18 have both 'count' (docs in stage) and 'signed_count' (docs signed).
        """
        # Sign stage 17 on d1
        DossierSignature.objects.create(
            dossier=self.d1,
            slot_key="decile_facility",
            signer_name="علیرضا نظری",
            signed_date="1403/08/10",
        )
        WorkflowSignatureLog.objects.create(
            dossier=self.d1,
            from_stage="مرحله 17: تسهیلات وام دهک",
            to_stage="تکمیل خارج از نوبت مرحله 17",
            actor="علیرضا نظری",
            action="SIGN",
            signature_hash="TEST17",
        )

        self.client.login(username="admin_user", password="password123")
        resp = self.client.get(reverse("dossier_list"))
        self.assertEqual(resp.status_code, 200)

        stages_meta = resp.context["stages_meta"]
        stg17 = next((s for s in stages_meta if s["id"] == 17), None)
        stg18 = next((s for s in stages_meta if s["id"] == 18), None)

        self.assertIsNotNone(stg17)
        self.assertIsNotNone(stg18)

        # d3 is at stage 17, so count is 1
        self.assertEqual(stg17["count"], 1)
        # d1 has stage 17 signed, so signed_count is >= 1
        self.assertGreaterEqual(stg17["signed_count"], 1)

        # stg18 has count 0 and signed_count
        self.assertEqual(stg18["count"], 0)
        self.assertIsNotNone(stg18["signed_count"])

        # Check rendered HTML
        html = resp.content.decode("utf-8")
        self.assertIn("مراجعه تسهیلات چک (۱۷)", html)
        self.assertIn("مراجعه آماده‌سازی (۱۸)", html)
        self.assertIn("امضاشده:", html)

    def test_shipments_with_dossier_without_archive_number(self):
        """
        Dossiers before Stage 8 (archive_number=None) can be included in shipments,
        viewed on shipments_history, and printed without errors, showing 'ردیف {id}'.
        """
        d_no_arch = HousingDossier.objects.create(
            national_id="0044444444",
            first_name="سارا",
            last_name="امینی",
            current_stage=5,
            archive_number=None,
            is_locked=False,
        )
        self.client.login(username="admin_user", password="password123")

        # Create shipment with dossier without archive number (using d.id)
        url = reverse("directorate_shipment_create")
        payload = {
            "shipment_type": "LOAN",
            "archive_numbers": [d_no_arch.id],
            "note": "محموله آزمایشی با پرونده فاقد شماره بایگانی",
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        s_id = resp.json()["shipment"]["id"]

        # Verify shipment history list page
        r_hist = self.client.get(reverse("directorate_shipments_list"))
        self.assertEqual(r_hist.status_code, 200)
        html_hist = r_hist.content.decode("utf-8")
        self.assertIn(f"/dossier/{d_no_arch.id}/", html_hist)
        self.assertIn(f"ردیف {d_no_arch.id}", html_hist)

        # Verify shipment print page
        r_print = self.client.get(reverse("directorate_shipment_print", kwargs={"shipment_id": s_id}))
        self.assertEqual(r_print.status_code, 200)
        html_print = r_print.content.decode("utf-8")
        self.assertIn(f"ردیف {d_no_arch.id}", html_print)
