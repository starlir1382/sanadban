from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.management import call_command
from workflow.models import HousingDossier, UserProfile


class Stage8ArchiveNumberTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_stage7 = User.objects.create_user(username="expert_stg7_test", password="password123")
        self.prof7, _ = UserProfile.objects.get_or_create(user=self.user_stage7)
        self.prof7.allowed_stages = "7"
        self.prof7.can_sign = True
        self.prof7.full_name = "کارشناس مرحله هفت"
        self.prof7.save()

        self.admin_user = User.objects.create_superuser(username="admin_test", password="password123")

    def test_preliminary_dossier_has_no_archive_number(self):
        """Dossiers created in stages 1 to 7 should NOT have an archive_number assigned."""
        d1 = HousingDossier.objects.create(
            national_id="0380000001",
            full_name="متقاضی مرحله ۱",
            current_stage=1,
        )
        self.assertIsNone(d1.archive_number)
        self.assertEqual(d1.display_number, f"ردیف {d1.id}")
        self.assertEqual(d1.url_pk, d1.id)

        d7 = HousingDossier.objects.create(
            national_id="0380000007",
            full_name="متقاضی مرحله ۷",
            current_stage=7,
        )
        self.assertIsNone(d7.archive_number)
        self.assertEqual(d7.display_number, f"ردیف {d7.id}")
        self.assertEqual(d7.url_pk, d7.id)

    def test_advancing_to_stage_8_allocates_sequential_archive_number(self):
        """When a dossier advances to Stage 8 via electronic sign, it gets the next archive number."""
        dossier = HousingDossier.objects.create(
            national_id="0380000010",
            full_name="متقاضی آماده مرحله ۸",
            current_stage=7,
        )
        self.assertIsNone(dossier.archive_number)

        self.client.force_login(self.user_stage7)
        res = self.client.post(
            f"/dossier/{dossier.id}/sign/",
            data='{"notes": "تایید مرحله ۷ و ارجاع به مرحله ۸"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["new_stage"], 8)
        self.assertEqual(payload["archive_number"], 100001)

        dossier.refresh_from_db()
        self.assertEqual(dossier.current_stage, 8)
        self.assertEqual(dossier.archive_number, 100001)
        self.assertEqual(dossier.display_number, "100001")
        self.assertEqual(dossier.url_pk, 100001)

        # A second dossier signing stage 7 gets 100002
        dossier2 = HousingDossier.objects.create(
            national_id="0380000020",
            full_name="متقاضی دوم مرحله ۸",
            current_stage=7,
        )
        res2 = self.client.post(
            f"/dossier/{dossier2.id}/sign/",
            data='{"notes": "تایید نفر دوم"}',
            content_type="application/json",
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["archive_number"], 100002)

        dossier2.refresh_from_db()
        self.assertEqual(dossier2.archive_number, 100002)

    def test_dossier_detail_accessible_by_id_and_by_archive_number(self):
        """Detail view handles preliminary dossier by id and stage 8+ dossier by archive_number."""
        d_prelim = HousingDossier.objects.create(
            national_id="0380000030",
            full_name="متقاضی بدون بایگانی",
            current_stage=1,
        )
        self.client.force_login(self.admin_user)

        res1 = self.client.get(f"/dossier/{d_prelim.id}/")
        self.assertEqual(res1.status_code, 200)

        d_arch = HousingDossier.objects.create(
            national_id="0380000040",
            full_name="متقاضی دارای بایگانی",
            current_stage=8,
            archive_number=100099,
        )
        res2 = self.client.get(f"/dossier/{d_arch.archive_number}/")
        self.assertEqual(res2.status_code, 200)

    def test_renumber_command_fixes_existing_dossiers(self):
        """Management command correctly clears preliminary archive numbers and renumbers stage >= 8."""
        # 3 preliminary dossiers that incorrectly had old numbers
        HousingDossier.objects.create(national_id="0381111111", current_stage=1, archive_number=100522)
        HousingDossier.objects.create(national_id="0382222222", current_stage=3, archive_number=100608)
        HousingDossier.objects.create(national_id="0383333333", current_stage=7, archive_number=105962)

        # 2 stage 8+ dossiers with scattered old numbers
        d_stg8 = HousingDossier.objects.create(national_id="0384444444", current_stage=8, archive_number=108491)
        d_stg9 = HousingDossier.objects.create(national_id="0385555555", current_stage=9, archive_number=111134)

        call_command("renumber_archive_dossiers", confirm=True, start=100001)

        # Preliminary dossiers must now be None
        d1 = HousingDossier.objects.get(national_id="0381111111")
        d2 = HousingDossier.objects.get(national_id="0382222222")
        d3 = HousingDossier.objects.get(national_id="0383333333")
        self.assertIsNone(d1.archive_number)
        self.assertIsNone(d2.archive_number)
        self.assertIsNone(d3.archive_number)

        # Stage 8+ dossiers must now be 100001 and 100002
        d_stg8.refresh_from_db()
        d_stg9.refresh_from_db()
        self.assertEqual(d_stg8.archive_number, 100001)
        self.assertEqual(d_stg9.archive_number, 100002)
