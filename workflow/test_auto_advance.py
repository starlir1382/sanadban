from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command
from io import StringIO
from workflow.models import (
    HousingDossier,
    WorkflowSignatureLog,
)


class AutoAdvanceDossiersTest(TestCase):
    def setUp(self):
        # 1. Admin user setup
        self.admin_user = User.objects.create_user(
            username="admin_test_auto",
            password="password123",
            first_name="مدیر",
            last_name="سامانه",
            is_superuser=True,
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.full_name = "مدیر کل تستی"
        self.admin_profile.role_title = "مدیر ارشد مسکن"
        self.admin_profile.can_sign = True
        self.admin_profile.save()

        # 2. Dossier A: Has bank_letter_number at Stage 1
        self.doc_bank = HousingDossier.objects.create(
            archive_number=900001,
            national_id="1111111111",
            full_name="متقاضی با نامه بانک",
            current_stage=1,
            status="IN_PROGRESS",
            bank_letter_number="BL-998877",
            registration_section="10",
            main_plaque=100,
            separated_plaque=200,
            sub_plaque=300,
        )

        # 3. Dossier B: Has Section 2 filled (no plot number), no bank letter at Stage 1
        self.doc_sec2 = HousingDossier.objects.create(
            archive_number=900002,
            national_id="2222222222",
            full_name="متقاضی بخش ۲ کامل",
            current_stage=1,
            status="IN_PROGRESS",
            bank_letter_number="",
            registration_section="15",
            main_plaque=150,
            separated_plaque=250,
            sub_plaque=350,
            plot_number=None,
        )

        # 4. Dossier C: Has Section 2 filled WITH plot number, no bank letter at Stage 1
        self.doc_sec2_plot = HousingDossier.objects.create(
            archive_number=900003,
            national_id="3333333333",
            full_name="متقاضی بخش ۲ با قطعه",
            current_stage=1,
            status="IN_PROGRESS",
            bank_letter_number="",
            registration_section="20",
            main_plaque=500,
            separated_plaque=600,
            sub_plaque=700,
            plot_number=45,
        )

        # 5. Dossier D: Missing Section 2 fields and no bank letter (should not advance)
        self.doc_incomplete = HousingDossier.objects.create(
            archive_number=900004,
            national_id="4444444444",
            full_name="متقاضی ناقص",
            current_stage=1,
            status="IN_PROGRESS",
            bank_letter_number="",
            registration_section="",
            main_plaque=None,
        )

        # 6. Dossier E: Locked dossier (should never advance)
        self.doc_locked = HousingDossier.objects.create(
            archive_number=900005,
            national_id="5555555555",
            full_name="متقاضی قفل‌شده",
            current_stage=1,
            status="COMPLETED",
            is_locked=True,
            bank_letter_number="BL-LOCKED",
        )

    def test_dry_run_does_not_modify_database(self):
        """Dry-run mode should report counts but make 0 database modifications."""
        out = StringIO()
        call_command(
            "auto_advance_dossiers",
            admin_user="admin_test_auto",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("حالت پیش‌نمایش (DRY-RUN)", output)

        self.doc_bank.refresh_from_db()
        self.doc_sec2.refresh_from_db()
        self.assertEqual(self.doc_bank.current_stage, 1)
        self.assertEqual(self.doc_sec2.current_stage, 1)
        self.assertEqual(WorkflowSignatureLog.objects.count(), 0)

    def test_live_execution_advances_stages_and_creates_admin_logs(self):
        """Confirmed execution advances bank docs to stage 7, sec2 docs to stage 2, and logs admin."""
        out = StringIO()
        call_command(
            "auto_advance_dossiers",
            confirm=True,
            admin_user="admin_test_auto",
            stdout=out,
        )

        # 1. Verify Bank Letter Dossier
        self.doc_bank.refresh_from_db()
        self.assertEqual(self.doc_bank.current_stage, 7)
        self.assertEqual(self.doc_bank.status, "IN_PROGRESS")

        bank_logs = WorkflowSignatureLog.objects.filter(dossier=self.doc_bank).order_by("id")
        self.assertEqual(bank_logs.count(), 6)  # Stages 1->2, 2->3, 3->4, 4->5, 5->6, 6->7

        expected_transitions = [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (6, 7),
        ]
        for log, (s_from, s_to) in zip(bank_logs, expected_transitions):
            self.assertIn(f"مرحله {s_from}", log.from_stage)
            self.assertIn(f"مرحله {s_to}", log.to_stage)
            self.assertEqual(log.actor, "مدیر کل تستی")
            self.assertEqual(log.role, "مدیر ارشد مسکن")
            self.assertEqual(log.action, "SIGN")
            self.assertIn("BL-998877", log.notes)

        # 2. Verify Section 2 Dossier
        self.doc_sec2.refresh_from_db()
        self.assertEqual(self.doc_sec2.current_stage, 2)
        sec2_logs = WorkflowSignatureLog.objects.filter(dossier=self.doc_sec2)
        self.assertEqual(sec2_logs.count(), 1)
        log2 = sec2_logs.first()
        self.assertIn("مرحله 1", log2.from_stage)
        self.assertIn("مرحله 2", log2.to_stage)
        self.assertEqual(log2.actor, "مدیر کل تستی")
        self.assertIn("بخش ۲", log2.notes)

        # 3. Verify Incomplete and Locked dossiers did NOT advance
        self.doc_incomplete.refresh_from_db()
        self.assertEqual(self.doc_incomplete.current_stage, 1)

        self.doc_locked.refresh_from_db()
        self.assertEqual(self.doc_locked.current_stage, 1)

    def test_sec2_target_stage_3(self):
        """When --sec2-target-stage 3 is passed, Section 2 dossiers advance to stage 3."""
        out = StringIO()
        call_command(
            "auto_advance_dossiers",
            confirm=True,
            admin_user="admin_test_auto",
            sec2_target_stage=3,
            archive_number=900002,
            stdout=out,
        )

        self.doc_sec2.refresh_from_db()
        self.assertEqual(self.doc_sec2.current_stage, 3)
        logs = WorkflowSignatureLog.objects.filter(dossier=self.doc_sec2).order_by("id")
        self.assertEqual(logs.count(), 2)  # Stage 1->2 and 2->3
        self.assertIn("مرحله 1", logs[0].from_stage)
        self.assertIn("مرحله 2", logs[0].to_stage)
        self.assertIn("مرحله 2", logs[1].from_stage)
        self.assertIn("مرحله 3", logs[1].to_stage)

    def test_require_plot_number_flag(self):
        """When --require-plot-number is passed, dossiers without plot_number are not advanced."""
        out = StringIO()
        call_command(
            "auto_advance_dossiers",
            confirm=True,
            admin_user="admin_test_auto",
            require_plot_number=True,
            stdout=out,
        )

        # doc_sec2 (no plot_number) should NOT have advanced
        self.doc_sec2.refresh_from_db()
        self.assertEqual(self.doc_sec2.current_stage, 1)

        # doc_sec2_plot (has plot_number=45) should have advanced to 2
        self.doc_sec2_plot.refresh_from_db()
        self.assertEqual(self.doc_sec2_plot.current_stage, 2)
