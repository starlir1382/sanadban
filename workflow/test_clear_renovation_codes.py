from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from workflow.models import HousingDossier, PreSelectedUnit


class ClearRenovationCodesCommandTest(TestCase):
    def setUp(self):
        self.dossier1 = HousingDossier.objects.create(
            archive_number=990001,
            national_id="0011223344",
            full_name="تست ۱",
            site="رئیسی 560 هکتار",
            project="پروژه تست",
            plot_number=10,
            block_name="B1",
            renovation_code="8-806-10-1-1",
            is_locked=False,
        )
        self.dossier2 = HousingDossier.objects.create(
            archive_number=990002,
            national_id="0011223355",
            full_name="تست ۲",
            site="27 هکتاری",
            project="پروژه دیگر",
            plot_number=20,
            block_name="C2",
            renovation_code="8-806-20-1-1",
            is_locked=True,
        )
        self.psu = PreSelectedUnit.objects.create(
            national_id="0011223344",
            full_name="واحد تست",
            renovation_code="8-806-10-1-1",
        )

    def test_dry_run_does_not_modify(self):
        out = StringIO()
        call_command("clear_renovation_codes", "--dry-run", stdout=out)
        self.dossier1.refresh_from_db()
        self.dossier2.refresh_from_db()
        self.psu.refresh_from_db()

        self.assertEqual(self.dossier1.renovation_code, "8-806-10-1-1")
        self.assertEqual(self.dossier2.renovation_code, "8-806-20-1-1")
        self.assertEqual(self.psu.renovation_code, "8-806-10-1-1")
        self.assertIn("[DRY RUN COMPLETE]", out.getvalue())

    def test_without_confirm_defaults_to_dry_run(self):
        out = StringIO()
        call_command("clear_renovation_codes", stdout=out)
        self.dossier1.refresh_from_db()
        self.assertEqual(self.dossier1.renovation_code, "8-806-10-1-1")
        self.assertIn("[DRY RUN COMPLETE]", out.getvalue())

    def test_confirm_clears_all(self):
        out = StringIO()
        call_command("clear_renovation_codes", "--confirm", stdout=out)
        self.dossier1.refresh_from_db()
        self.dossier2.refresh_from_db()
        self.psu.refresh_from_db()

        self.assertEqual(self.dossier1.renovation_code, "")
        self.assertEqual(self.dossier2.renovation_code, "")
        self.assertEqual(self.psu.renovation_code, "")
        self.assertIn("Successfully cleared renovation codes", out.getvalue())

    def test_site_filter(self):
        out = StringIO()
        call_command("clear_renovation_codes", "--site", "27 هکتاری", "--confirm", stdout=out)
        self.dossier1.refresh_from_db()
        self.dossier2.refresh_from_db()

        # Dossier 1 should be untouched, Dossier 2 should be cleared
        self.assertEqual(self.dossier1.renovation_code, "8-806-10-1-1")
        self.assertEqual(self.dossier2.renovation_code, "")

    def test_exclude_locked(self):
        out = StringIO()
        call_command("clear_renovation_codes", "--exclude-locked", "--confirm", stdout=out)
        self.dossier1.refresh_from_db()
        self.dossier2.refresh_from_db()

        # Dossier 1 (unlocked) cleared, Dossier 2 (locked) preserved
        self.assertEqual(self.dossier1.renovation_code, "")
        self.assertEqual(self.dossier2.renovation_code, "8-806-20-1-1")
