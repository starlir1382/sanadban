from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from workflow.models import (
    HousingDossier,
    UserProfile,
    DossierFieldChangeLog,
    WorkflowSignatureLog,
)


class AuditLogsArchiveNumberTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.superadmin = User.objects.create_superuser(
            username="super_audit_test",
            password="password123",
            email="audit@example.com"
        )
        self.chief_user = User.objects.create_user(
            username="chief_audit_test",
            password="password123"
        )
        self.chief_prof, _ = UserProfile.objects.get_or_create(user=self.chief_user)
        self.chief_prof.is_housing_chief = True
        self.chief_prof.allowed_stages = "all"
        self.chief_prof.save()

        # Preliminary dossier (stage 1, archive_number=None)
        self.prelim_dossier = HousingDossier.objects.create(
            national_id="0381111111",
            full_name="متقاضی مقدماتی بدون شماره بایگانی",
            current_stage=1,
            archive_number=None,
        )

        # Official dossier (stage 8, archive_number=100055)
        self.official_dossier = HousingDossier.objects.create(
            national_id="0382222222",
            full_name="متقاضی نهایی با شماره بایگانی",
            current_stage=8,
            archive_number=100055,
        )

        # Add field changes and signature logs to preliminary dossier
        self.prelim_fc = DossierFieldChangeLog.objects.create(
            dossier=self.prelim_dossier,
            field_name="full_name",
            field_label="نام و نام خانوادگی",
            old_value="نام قبلی",
            new_value="نام جدید",
            changed_by="کارشناس آزمایشی",
            stage=1,
        )
        self.prelim_sig = WorkflowSignatureLog.objects.create(
            dossier=self.prelim_dossier,
            from_stage="مرحله ۱",
            to_stage="مرحله ۲",
            actor="کارشناس اقدام",
            role="کارشناس مرحله یک",
            action="SIGN",
            action_label="تایید و امضا",
            signature_hash="abcd1234efgh5678",
            notes="یادداشت تست پرونده مقدماتی"
        )

        # Add field changes and signature logs to official dossier
        self.official_fc = DossierFieldChangeLog.objects.create(
            dossier=self.official_dossier,
            field_name="project",
            field_label="پروژه مسکونی",
            old_value="پروژه A",
            new_value="پروژه B",
            changed_by="مدیر ارشد",
            stage=8,
        )
        self.official_sig = WorkflowSignatureLog.objects.create(
            dossier=self.official_dossier,
            from_stage="مرحله ۷",
            to_stage="مرحله ۸",
            actor="کارشناس مرحله هفت",
            role="کارشناس اسناد",
            action="SIGN",
            action_label="تایید و امضا",
            signature_hash="8765hgfe4321dcba",
            notes="یادداشت تست پرونده نهایی"
        )

    def test_audit_logs_view_renders_successfully_with_null_archive_numbers(self):
        """Audit log page should render HTTP 200 without NoReverseMatch when dossiers lack archive numbers."""
        self.client.force_login(self.superadmin)
        res = self.client.get(reverse("audit_logs"))
        self.assertEqual(res.status_code, 200)

        content = res.content.decode("utf-8")
        # Should contain display numbers
        self.assertIn(f"ردیف {self.prelim_dossier.id}", content)
        self.assertIn("100055", content)
        self.assertIn(f"/dossier/{self.prelim_dossier.id}/", content)
        self.assertIn("/dossier/100055/", content)

    def test_audit_logs_search_by_official_archive_number(self):
        """Searching by archive_number=100055 returns official dossier logs."""
        self.client.force_login(self.superadmin)
        res = self.client.get(reverse("audit_logs") + "?archive_number=100055")
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        self.assertIn("100055", content)
        self.assertNotIn(f"ردیف {self.prelim_dossier.id}", content)

    def test_audit_logs_search_by_preliminary_id(self):
        """Searching by archive_number or archive param using preliminary dossier ID works."""
        self.client.force_login(self.superadmin)
        res = self.client.get(reverse("audit_logs") + f"?archive_number={self.prelim_dossier.id}")
        self.assertEqual(res.status_code, 200)
        content = res.content.decode("utf-8")
        self.assertIn(f"ردیف {self.prelim_dossier.id}", content)
        self.assertNotIn("100055", content)

        # Also test with ?archive=
        res_arch = self.client.get(reverse("audit_logs") + f"?archive={self.prelim_dossier.id}")
        self.assertEqual(res_arch.status_code, 200)
        content_arch = res_arch.content.decode("utf-8")
        self.assertIn(f"ردیف {self.prelim_dossier.id}", content_arch)

    def test_audit_logs_search_by_national_id_and_name(self):
        """Searching by national id or applicant name finds logs."""
        self.client.force_login(self.superadmin)
        res_nid = self.client.get(reverse("audit_logs") + "?q=0381111111")
        self.assertEqual(res_nid.status_code, 200)
        content_nid = res_nid.content.decode("utf-8")
        self.assertIn(f"ردیف {self.prelim_dossier.id}", content_nid)

        res_name = self.client.get(reverse("audit_logs") + "?q=نهایی")
        self.assertEqual(res_name.status_code, 200)
        content_name = res_name.content.decode("utf-8")
        self.assertIn("100055", content_name)

    def test_print_views_render_for_dossier_without_archive_number(self):
        """Print views shouldn't break when archive_number is None."""
        self.client.force_login(self.superadmin)
        pk = self.prelim_dossier.url_pk  # this is d.id

        for view_name in [
            "land_bank_print",
            "dossier_summary_print",
            "folder_label_print",
            "dossier_print_affidavit",
            "dossier_print_info_form",
            "dossier_print_checks",
            "red_rejection_letter_print",
            "notary_letter_print",
        ]:
            res = self.client.get(reverse(view_name, kwargs={"pk": pk}))
            self.assertEqual(res.status_code, 200, f"View {view_name} failed with status {res.status_code}")
