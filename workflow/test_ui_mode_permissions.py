import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from workflow.models import UserProfile


class UiModePermissionsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Superuser / Admin
        self.admin_user = User.objects.create_superuser(
            username="admin_test_mode",
            password="admin_password123",
            email="admin@example.com"
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={"full_name": "مدیر سیستم", "ui_mode": "advanced", "can_change_ui_mode": True}
        )

        # 2. Regular user locked to simple mode
        self.regular_user = User.objects.create_user(
            username="regular_expert",
            password="user_password123"
        )
        self.regular_profile, _ = UserProfile.objects.get_or_create(
            user=self.regular_user,
            defaults={"full_name": "کارشناس عادی", "ui_mode": "simple", "can_change_ui_mode": False}
        )

        # 3. Regular user with explicit permission
        self.permitted_user = User.objects.create_user(
            username="permitted_expert",
            password="user_password123"
        )
        self.permitted_profile, _ = UserProfile.objects.get_or_create(
            user=self.permitted_user,
            defaults={"full_name": "کارشناس مجاز", "ui_mode": "simple"}
        )
        self.permitted_profile.can_change_ui_mode = True
        self.permitted_profile.save()

    def test_regular_user_cannot_change_ui_mode(self):
        """A user without can_change_ui_mode cannot change their UI mode via API."""
        self.client.login(username="regular_expert", password="user_password123")
        url = reverse("set_ui_mode")
        res = self.client.post(
            url,
            data=json.dumps({"mode": "advanced"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 403)
        self.regular_profile.refresh_from_db()
        self.assertEqual(self.regular_profile.ui_mode, "simple")

    def test_permitted_user_can_change_ui_mode(self):
        """A user with can_change_ui_mode=True can change their UI mode."""
        self.client.login(username="permitted_expert", password="user_password123")
        url = reverse("set_ui_mode")
        res = self.client.post(
            url,
            data=json.dumps({"mode": "advanced"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.permitted_profile.refresh_from_db()
        self.assertEqual(self.permitted_profile.ui_mode, "advanced")

    def test_admin_can_always_change_ui_mode(self):
        """Superuser/staff can change their mode freely."""
        self.client.login(username="admin_test_mode", password="admin_password123")
        url = reverse("set_ui_mode")
        res = self.client.post(
            url,
            data=json.dumps({"mode": "simple"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.admin_profile.refresh_from_db()
        self.assertEqual(self.admin_profile.ui_mode, "simple")

    def test_admin_can_create_user_with_ui_mode_and_permission(self):
        """Admin creating a user in users_management sets ui_mode and can_change_ui_mode."""
        self.client.login(username="admin_test_mode", password="admin_password123")
        url = reverse("create_user_action")
        data = {
            "username": "new_created_user",
            "password": "Password123!",
            "full_name": "کاربر جدید تست",
            "organization": "brokerage",
            "role_title": "کارشناس",
            "personnel_code": "99001",
            "phone_number": "09120000000",
            "can_sign": "1",
            "ui_mode": "simple",
            # can_change_ui_mode omitted -> should default to False
            "stages_selected": ["1", "2"]
        }
        res = self.client.post(url, data=data)
        self.assertEqual(res.status_code, 302)

        new_user = User.objects.get(username="new_created_user")
        self.assertEqual(new_user.profile.ui_mode, "simple")
        self.assertFalse(new_user.profile.can_change_ui_mode)

    def test_admin_can_edit_user_ui_mode_and_grant_permission(self):
        """Admin can change target user's assigned mode and grant permission to change."""
        self.client.login(username="admin_test_mode", password="admin_password123")
        url = reverse("edit_user_action", kwargs={"user_id": self.regular_user.id})
        data = {
            "full_name": "کارشناس ارتقایافته",
            "role_title": "کارشناس ارشد",
            "organization": "brokerage",
            "personnel_code": "12345",
            "phone_number": "09121111111",
            "national_id": "0123456789",
            "can_sign": "1",
            "is_active": "1",
            "ui_mode": "advanced",
            "can_change_ui_mode": "1",
            "stages_selected": ["1", "2", "3"]
        }
        res = self.client.post(url, data=data)
        self.assertEqual(res.status_code, 302)

        self.regular_profile.refresh_from_db()
        self.assertEqual(self.regular_profile.ui_mode, "advanced")
        self.assertTrue(self.regular_profile.can_change_ui_mode)

    def test_users_management_view_contains_ui_mode_data(self):
        """users_management_view passes ui_mode and can_change_ui_mode in json data."""
        self.client.login(username="admin_test_mode", password="admin_password123")
        url = reverse("users_management")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        users_data = res.context["users_data"]
        regular_entry = next((u for u in users_data if u["username"] == "regular_expert"), None)
        self.assertIsNotNone(regular_entry)
        self.assertEqual(regular_entry["ui_mode"], "simple")
        self.assertFalse(regular_entry["can_change_ui_mode"])
        self.assertFalse(regular_entry["allowed_to_change_ui_mode"])
