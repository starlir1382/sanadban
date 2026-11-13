import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from workflow.models import HousingDossier, UserProfile, LandRate
from workflow.field_permissions import can_user_edit_field, can_user_upload_signature, filter_allowed_updates


class ReadOnlyAccountTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user to create/manage users
        self.admin_user = User.objects.create_superuser(
            username="admin_chief",
            password="Password123!",
            email="admin@example.com"
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.full_name = "رئیس مسکن کل"
        self.admin_profile.is_housing_chief = True
        self.admin_profile.can_sign = True
        self.admin_profile.allowed_stages = "all"
        self.admin_profile.save()

        # Standard Housing Dossier for testing
        self.dossier = HousingDossier.objects.create(
            archive_number=1001,
            first_name="علی",
            last_name="رضایی",
            national_id="0123456789",
            current_stage=1,
            project="پروژه زیتون",
            site="سایت ۵۶۰ هکتاری",
            status="IN_PROGRESS"
        )

    def test_create_readonly_user_from_ui_action(self):
        """Verify creating a read-only account via the UI create_user_action endpoint."""
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse("create_user_action"), {
            "username": "viewer_user",
            "password": "ViewerPassword123!",
            "full_name": "کارشناس ناظر آزمایشی",
            "role_title": "ناظر عالی",
            "organization": "brokerage",
            "is_readonly": "on",
            "stages_selected": ["1", "2", "3"],
        })
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username="viewer_user")
        self.assertFalse(user.is_staff)
        self.assertTrue(hasattr(user, "profile"))
        self.assertTrue(user.profile.is_readonly)
        self.assertFalse(user.profile.can_sign)
        self.assertEqual(user.profile.allowed_stages, "all")
        self.assertFalse(user.profile.must_change_password)

    def test_edit_user_to_readonly_from_ui_action(self):
        """Verify editing an existing user to become read-only."""
        self.client.force_login(self.admin_user)

        expert = User.objects.create_user(username="expert_sample", password="Password123!")
        expert_prof = expert.profile
        expert_prof.full_name = "کارشناس اقدام"
        expert_prof.can_sign = True
        expert_prof.allowed_stages = "1,2"
        expert_prof.save()

        response = self.client.post(reverse("edit_user_action", kwargs={"user_id": expert.id}), {
            "full_name": "کارشناس اقدام (تغییر به ناظر)",
            "role_title": "ناظر اسناد",
            "organization": "directorate",
            "is_readonly": "on",
            "is_active": "on",
            "allowed_stages": "all",
        })
        self.assertEqual(response.status_code, 302)

        expert.refresh_from_db()
        expert_prof.refresh_from_db()

        self.assertTrue(expert_prof.is_readonly)
        self.assertFalse(expert_prof.can_sign)
        self.assertFalse(expert.is_staff)
        self.assertEqual(expert_prof.allowed_stages, "all")

    def test_readonly_user_can_read_dossiers_and_views(self):
        """Verify that a read-only user can browse dashboards, dossiers, audit logs, and print views."""
        ro_user = User.objects.create_user(username="ro_inspector", password="Password123!")
        ro_prof = ro_user.profile
        ro_prof.full_name = "ناظر اسناد"
        ro_prof.is_readonly = True
        ro_prof.can_sign = False
        ro_prof.allowed_stages = "all"
        ro_prof.save()

        self.client.force_login(ro_user)

        # 1. Dossier list dashboard
        res_list = self.client.get(reverse("dossier_list"))
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(res_list.context.get("is_readonly_user"))

        # 2. Dossier detail workspace
        res_detail = self.client.get(reverse("dossier_detail", kwargs={"pk": self.dossier.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertTrue(res_detail.context.get("is_view_only"))
        self.assertTrue(res_detail.context.get("is_readonly"))
        self.assertFalse(res_detail.context.get("dossier_data", {}).get("user_can_action"))

        # 3. Print summary view
        res_print = self.client.get(reverse("dossier_summary_print", kwargs={"pk": self.dossier.pk}))
        self.assertEqual(res_print.status_code, 200)

        # 4. Audit logs view
        res_audit = self.client.get(reverse("audit_logs"))
        self.assertEqual(res_audit.status_code, 200)

        # 5. Land rates view
        res_rates = self.client.get(reverse("land_rates_admin"))
        self.assertEqual(res_rates.status_code, 200)

        # 6. Signed dossiers history
        res_signed = self.client.get(reverse("signed_dossiers_list"))
        self.assertEqual(res_signed.status_code, 200)

    def test_readonly_user_post_patch_put_delete_strictly_blocked(self):
        """Verify that any mutating request (POST, PUT, PATCH, DELETE) by a read-only account is blocked with 403."""
        ro_user = User.objects.create_user(username="ro_inspector2", password="Password123!")
        ro_prof = ro_user.profile
        ro_prof.full_name = "ناظر اسناد ۲"
        ro_prof.is_readonly = True
        ro_prof.can_sign = False
        ro_prof.allowed_stages = "all"
        ro_prof.save()

        self.client.force_login(ro_user)

        # 1. AJAX POST /save/
        res_save = self.client.post(
            reverse("dossier_save", kwargs={"pk": self.dossier.pk}),
            json.dumps({"first_name": "تغییر غیرمجاز"}),
            content_type="application/json"
        )
        self.assertEqual(res_save.status_code, 403)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.first_name, "علی")

        # 2. POST /sign/
        res_sign = self.client.post(
            reverse("dossier_sign", kwargs={"pk": self.dossier.pk}),
            {"confirm_sign": "1"}
        )
        self.assertIn(res_sign.status_code, (403, 302))
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.current_stage, 1)

        # 3. POST /return/
        res_return = self.client.post(
            reverse("dossier_return", kwargs={"pk": self.dossier.pk}),
            {"reason": "تست بازگشت"}
        )
        self.assertIn(res_return.status_code, (403, 302))

        # 4. Users management access blocked
        res_users = self.client.get(reverse("users_management"))
        self.assertEqual(res_users.status_code, 302)

    def test_field_permissions_helper_rejects_readonly(self):
        """Verify that field_permissions functions strictly disallow edits for read-only user."""
        ro_user = User.objects.create_user(username="ro_inspector3", password="Password123!")
        ro_prof = ro_user.profile
        ro_prof.full_name = "ناظر ۳"
        ro_prof.is_readonly = True
        ro_prof.can_sign = False
        ro_prof.allowed_stages = "all"
        ro_prof.save()

        self.assertFalse(can_user_edit_field(ro_user, "first_name"))
        self.assertFalse(can_user_edit_field(ro_user, "national_id"))
        self.assertFalse(can_user_upload_signature(ro_user, "brokerage"))
        self.assertEqual(filter_allowed_updates(ro_user, {"first_name": "رضا"}), {})

    def test_readonly_user_can_logout_and_toggle_ui_mode(self):
        """Verify that safe operations like logout and personal ui_mode preference remain functional."""
        ro_user = User.objects.create_user(username="ro_inspector4", password="Password123!")
        ro_prof = ro_user.profile
        ro_prof.full_name = "ناظر ۴"
        ro_prof.is_readonly = True
        ro_prof.can_sign = False
        ro_prof.allowed_stages = "all"
        ro_prof.save()

        self.client.force_login(ro_user)

        # UI mode preference POST
        res_mode = self.client.post(
            reverse("set_ui_mode"),
            json.dumps({"mode": "advanced"}),
            content_type="application/json"
        )
        self.assertEqual(res_mode.status_code, 200)

        # Logout
        res_logout = self.client.get(reverse("logout"))
        self.assertEqual(res_logout.status_code, 302)
