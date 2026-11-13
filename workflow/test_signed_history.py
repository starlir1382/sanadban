from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from workflow.models import HousingDossier, UserProfile, WorkflowSignatureLog, DossierSignature

User = get_user_model()


class SignedHistoryTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Expert User
        self.expert_user = User.objects.create_user(
            username="expert_legal",
            password="password123",
            first_name="علیرضا",
            last_name="رضایی"
        )
        self.expert_profile, _ = UserProfile.objects.update_or_create(
            user=self.expert_user,
            defaults={
                "full_name": "علیرضا رضایی",
                "role_title": "کارشناس حقوقی",
                "allowed_stages": "8",
                "can_sign": True,
                "is_active_expert": True
            }
        )

        # 2. Create Another Expert User
        self.other_user = User.objects.create_user(
            username="expert_tech",
            password="password123",
            first_name="مهدی",
            last_name="مرادی"
        )
        self.other_profile, _ = UserProfile.objects.update_or_create(
            user=self.other_user,
            defaults={
                "full_name": "مهدی مرادی",
                "role_title": "کارشناس فنی",
                "allowed_stages": "11",
                "can_sign": True,
                "is_active_expert": True
            }
        )

        # 3. Create Admin User
        self.admin_user = User.objects.create_superuser(
            username="admin_chief",
            password="password123",
            email="admin@test.com"
        )
        self.admin_profile, _ = UserProfile.objects.update_or_create(
            user=self.admin_user,
            defaults={
                "full_name": "مدیر ارشد",
                "role_title": "رئیس مسکن",
                "is_housing_chief": True,
                "allowed_stages": "all"
            }
        )

        # 4. Create Dossiers
        # Dossier A: Signed by expert_legal at stage 8, now moved to stage 11
        self.dossier_a = HousingDossier.objects.create(
            archive_number=1001,
            national_id="0011223344",
            full_name="متقاضی اول",
            current_stage=11,
            project="پروژه زیتون",
            site="سایت الف"
        )
        WorkflowSignatureLog.objects.create(
            dossier=self.dossier_a,
            from_stage="مرحله 8: کارشناسی حقوقی",
            to_stage="مرحله 9: تایید درآمد",
            actor="علیرضا رضایی",
            role="کارشناس حقوقی",
            action="SIGN",
            action_label="تایید و امضای الکترونیکی",
            signature_hash="SHA256: 1234567890abcdef"
        )

        # Dossier B: Signed by other_user (مهدی مرادی)
        self.dossier_b = HousingDossier.objects.create(
            archive_number=1002,
            national_id="0099887766",
            full_name="متقاضی دوم",
            current_stage=12,
            project="پروژه نیلوفر",
            site="سایت ب"
        )
        WorkflowSignatureLog.objects.create(
            dossier=self.dossier_b,
            from_stage="مرحله 11: کارشناس فنی",
            to_stage="مرحله 12: کارشناس املاک",
            actor="مهدی مرادی",
            role="کارشناس فنی",
            action="SIGN",
            action_label="تایید و امضای الکترونیکی",
            signature_hash="SHA256: abcdef1234567890"
        )

        # Dossier C: Not signed by anyone
        self.dossier_c = HousingDossier.objects.create(
            archive_number=1003,
            national_id="0044556677",
            full_name="متقاضی سوم",
            current_stage=5,
            project="پروژه نرگس",
            site="سایت ج"
        )

    def test_anonymous_redirect(self):
        """Anonymous user must be redirected to login"""
        resp = self.client.get(reverse("signed_dossiers_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_expert_sees_only_own_signed_dossiers(self):
        """Expert user must only see dossiers they have signed"""
        self.client.force_login(self.expert_user)
        resp = self.client.get(reverse("signed_dossiers_list"))
        self.assertEqual(resp.status_code, 200)

        dossiers_in_context = list(resp.context["dossiers"])
        self.assertIn(self.dossier_a, dossiers_in_context)
        self.assertNotIn(self.dossier_b, dossiers_in_context)
        self.assertNotIn(self.dossier_c, dossiers_in_context)
        self.assertEqual(resp.context["total_signed_count"], 1)

    def test_admin_sees_all_signed_dossiers(self):
        """Admin sees all dossiers that have signatures in the system"""
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse("signed_dossiers_list"))
        self.assertEqual(resp.status_code, 200)

        dossiers_in_context = list(resp.context["dossiers"])
        self.assertIn(self.dossier_a, dossiers_in_context)
        self.assertIn(self.dossier_b, dossiers_in_context)
        self.assertNotIn(self.dossier_c, dossiers_in_context)
        self.assertEqual(resp.context["total_signed_count"], 2)

    def test_admin_filter_by_signer(self):
        """Admin can filter signed dossiers by specific signer"""
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse("signed_dossiers_list") + "?signer=مهدی مرادی")
        self.assertEqual(resp.status_code, 200)

        dossiers_in_context = list(resp.context["dossiers"])
        self.assertNotIn(self.dossier_a, dossiers_in_context)
        self.assertIn(self.dossier_b, dossiers_in_context)
        self.assertEqual(resp.context["dossiers_count"], 1)

    def test_ajax_search(self):
        """AJAX request returns JSON with count and HTML snippet"""
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse("signed_dossiers_list") + "?q=زیتون&ajax=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 1)
        self.assertIn("1001", data["html"])

    def test_detail_view_read_only_access_for_signed_dossier(self):
        """
        Expert whose allowed_stages is 8 CAN open dossier A (currently at stage 11)
        in view_only mode because they previously signed it.
        """
        self.client.force_login(self.expert_user)
        resp = self.client.get(reverse("dossier_detail", kwargs={"pk": 1001}) + "?view_only=1")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_view_only"])
        self.assertFalse(resp.context["user_can_action"])

    def test_detail_view_blocked_for_unsigned_dossier(self):
        """
        Expert whose allowed_stages is 8 CANNOT open dossier B (stage 12)
        because they never signed it and stage 12 is not allowed for them.
        """
        self.client.force_login(self.expert_user)
        resp = self.client.get(reverse("dossier_detail", kwargs={"pk": 1002}))
        # Redirected with access denied
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("dossier_list"))

    def test_expert_cannot_save_or_edit_signed_dossier(self):
        """
        Expert cannot POST changes, uploads, or deletes to a signed dossier that moved out of their stage.
        """
        from workflow.models import DossierAttachment
        self.client.force_login(self.expert_user)
        resp = self.client.post(
            reverse("dossier_save", kwargs={"pk": 1001}),
            data={"full_name": "تغییر غیرمجاز"},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

        # Cannot upload
        resp_up = self.client.post(
            reverse("dossier_upload_scan", kwargs={"pk": 1001}),
            data={"title": "test"}
        )
        self.assertEqual(resp_up.status_code, 403)

        # Cannot delete attachment
        att = DossierAttachment.objects.create(
            dossier=self.dossier_a,
            stage=8,
            title="مدرک نمونه",
            doc_type="OTHER"
        )
        resp_del = self.client.post(
            reverse("dossier_delete_attachment", kwargs={"pk": 1001, "attachment_id": att.id})
        )
        self.assertEqual(resp_del.status_code, 403)

    def test_signed_history_no_status_checkmark_and_day_mode_filters(self):
        """Signed history removes the tick status column and keeps Day Mode filter inputs legible."""
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse("signed_dossiers_list"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertNotIn('title="وضعیت امضا"', html)
        self.assertNotIn("امضا ثبت شده و دارای هش الکترونیکی", html)
        self.assertNotIn('class="dl-status green"', html)
        self.assertIn("dl-signed-filter-input", html)
        self.assertIn("dl-signed-filter-select", html)
        self.assertIn("color-scheme: light;", html)
        self.assertIn("color: #0f172a;", html)

        empty_resp = self.client.get(reverse("signed_dossiers_list") + "?q=__not_found__&ajax=1")
        self.assertEqual(empty_resp.status_code, 200)
        self.assertIn('<td colspan="5">', empty_resp.json()["html"])
        self.assertNotIn("مشاهده سوابق", html)
        self.assertNotIn('<th class="t-center">عملیات</th>', html)
        self.assertNotIn("dossier_summary_print", html)
        self.assertNotIn("چاپ فرم مراحل و امضاها", html)

    def test_navbar_and_admin_pages_hide_admin_links_and_support_day_mode(self):
        """UI hides /admin/ links & duplicate navbar archive link, while land_rates enforces light-mode input contrast."""
        self.client.force_login(self.admin_user)

        home_html = self.client.get(reverse("dossier_list")).content.decode("utf-8")
        self.assertNotIn("پنل ادمین جنگو", home_html)
        self.assertNotIn('href="/admin/"', home_html)
        self.assertNotIn("سوابق و آرشیو اسناد امضا شده", home_html)
        self.assertIn(reverse("signed_dossiers_list"), home_html)

        profile_html = self.client.get(reverse("user_profile")).content.decode("utf-8")
        self.assertNotIn("ورود به پنل ادمین جنگو", profile_html)
        self.assertNotIn('href="/admin/"', profile_html)

        users_html = self.client.get(reverse("users_management")).content.decode("utf-8")
        self.assertNotIn("ادمین تفصیلی جنگو", users_html)
        self.assertNotIn('href="/admin/"', users_html)

        rates_resp = self.client.get(reverse("land_rates_admin"))
        self.assertEqual(rates_resp.status_code, 200)
        rates_html = rates_resp.content.decode("utf-8")
        self.assertIn('html, html[data-theme="light"] { color-scheme: light; }', rates_html)
        self.assertIn(".sb-input-field", rates_html)
        self.assertIn("background-color: #ffffff;", rates_html)
        self.assertIn("color: #0f172a;", rates_html)

    def test_signed_history_hides_in_progress_unit_shows_own_sig_time_and_sorts_by_sig_time(self):
        """Signed history removes 'در حال گردش' and 'واحد ...', shows user signature date+time, and sorts newer/older."""
        from datetime import timedelta
        from django.utils import timezone
        from workflow.views import to_jalali_str

        now = timezone.now()
        t_older = now - timedelta(days=5, hours=3)
        t_newer = now - timedelta(days=1, hours=2)
        t_later_other = now - timedelta(minutes=10)

        # Backdate expert_user's signature on dossier_a to t_older
        WorkflowSignatureLog.objects.filter(
            dossier=self.dossier_a, actor="علیرضا رضایی"
        ).update(timestamp=t_older)

        # Another user later signed dossier_a (must NOT override expert_user's own signature timestamp display)
        WorkflowSignatureLog.objects.create(
            dossier=self.dossier_a,
            from_stage="مرحله 11: کارشناس فنی",
            to_stage="مرحله 12: کارشناس املاک",
            actor="مهدی مرادی",
            role="کارشناس فنی",
            action="SIGN",
            action_label="تایید و امضای الکترونیکی",
            timestamp=t_later_other,
            signature_hash="SHA256: otherlater",
        )

        # expert_user also signed dossier_b more recently (t_newer > t_older)
        WorkflowSignatureLog.objects.create(
            dossier=self.dossier_b,
            from_stage="مرحله 8: کارشناسی حقوقی",
            to_stage="مرحله 9: تایید درآمد",
            actor="علیرضا رضایی",
            role="کارشناس حقوقی",
            action="SIGN",
            action_label="تایید و امضای الکترونیکی",
            timestamp=t_newer,
            signature_hash="SHA256: expertnewer",
        )

        self.client.force_login(self.expert_user)
        resp_desc = self.client.get(reverse("signed_dossiers_list") + "?sort=date_desc")
        self.assertEqual(resp_desc.status_code, 200)
        html_desc = resp_desc.content.decode("utf-8")

        self.assertNotIn("در حال گردش", html_desc)
        self.assertNotIn("واحد directorate", html_desc)
        self.assertNotIn("واحد brokerage", html_desc)
        self.assertNotIn("اطلاعات آخرین امضا", html_desc)
        self.assertNotIn('id="stage-select"', html_desc)
        self.assertNotIn("همه مراحل فعلی", html_desc)
        self.assertIn("تاریخ امضا توسط شما", html_desc)
        self.assertIn("زمان امضا (جدیدتر به قدیمی‌تر)", html_desc)
        self.assertIn("زمان امضا (قدیمی‌تر به جدیدتر)", html_desc)

        expected_old_date = to_jalali_str(t_older, "%Y/%m/%d")
        expected_old_time = to_jalali_str(t_older, "%H:%M")
        expected_new_date = to_jalali_str(t_newer, "%Y/%m/%d")
        expected_new_time = to_jalali_str(t_newer, "%H:%M")
        self.assertIn(expected_old_date, html_desc)
        self.assertIn(f"ساعت {expected_old_time}", html_desc)
        self.assertIn(expected_new_date, html_desc)
        self.assertIn(f"ساعت {expected_new_time}", html_desc)
        # Ensure other user's later signature time is NOT shown to expert_user
        self.assertNotIn(f"ساعت {to_jalali_str(t_later_other, '%H:%M')}", html_desc)

        # Newer to older: dossier_b (t_newer) before dossier_a (t_older)
        desc_ids = [d.archive_number for d in resp_desc.context["dossiers"]]
        self.assertEqual(desc_ids, [1002, 1001])

        # Older to newer: dossier_a (t_older) before dossier_b (t_newer)
        resp_asc = self.client.get(reverse("signed_dossiers_list") + "?sort=date_asc")
        self.assertEqual(resp_asc.status_code, 200)
        asc_ids = [d.archive_number for d in resp_asc.context["dossiers"]]
        self.assertEqual(asc_ids, [1001, 1002])

        # AJAX older-to-newer preserves ordering and clean row HTML
        ajax_asc = self.client.get(reverse("signed_dossiers_list") + "?sort=date_asc&ajax=1")
        self.assertEqual(ajax_asc.status_code, 200)
        ajax_html = ajax_asc.json()["html"]
        self.assertLess(ajax_html.index("1001"), ajax_html.index("1002"))
        self.assertNotIn("در حال گردش", ajax_html)
        self.assertNotIn("واحد brokerage", ajax_html)
        self.assertNotIn("واحد directorate", ajax_html)
        self.assertNotIn("مشاهده سوابق", ajax_html)
        self.assertNotIn("چاپ فرم مراحل و امضاها", ajax_html)

    def test_regular_users_cannot_see_archived_locked_dossiers(self):
        """Non-admin experts and check admins must not see archived/locked (بایگانی) dossiers."""
        archived_22 = HousingDossier.objects.create(
            archive_number=2001,
            national_id="0055667788",
            full_name="متقاضی بایگانی شده",
            current_stage=22,
            is_locked=True,
            status="COMPLETED",
        )
        locked_stage8 = HousingDossier.objects.create(
            archive_number=2002,
            national_id="0055667799",
            full_name="متقاضی قفل شده",
            current_stage=8,
            is_locked=True,
            status="REJECTED_RED",
        )

        # Normal expert (allowed_stages="8"): must NOT see archived/locked dossiers in list or AJAX
        self.client.force_login(self.expert_user)
        resp_list = self.client.get(reverse("dossier_list"))
        self.assertEqual(resp_list.status_code, 200)
        list_ids = [d.archive_number for d in resp_list.context["dossiers"]]
        self.assertNotIn(archived_22.archive_number, list_ids)
        self.assertNotIn(locked_stage8.archive_number, list_ids)

        resp_ajax = self.client.get(reverse("dossier_list") + "?q=2001&ajax=1")
        self.assertEqual(resp_ajax.status_code, 200)
        self.assertEqual(resp_ajax.json()["count"], 0)

        # Unsigned locked dossier must also be blocked on direct detail URL (even with ?view_only=1)
        resp_detail = self.client.get(reverse("dossier_detail", kwargs={"pk": archived_22.archive_number}) + "?view_only=1")
        self.assertEqual(resp_detail.status_code, 302)
        self.assertEqual(resp_detail.url, reverse("dossier_list"))

        # Check-admin (non-full-admin): must NOT see archived/locked dossiers either
        check_user = User.objects.create_user(username="check_admin_user", password="password123")
        UserProfile.objects.update_or_create(
            user=check_user,
            defaults={"full_name": "مدیر چک", "allowed_stages": "17", "is_check_admin": True},
        )
        self.client.force_login(check_user)
        resp_check = self.client.get(reverse("dossier_list"))
        self.assertEqual(resp_check.status_code, 200)
        check_ids = [d.archive_number for d in resp_check.context["dossiers"]]
        self.assertNotIn(archived_22.archive_number, check_ids)

        # Full admin CAN still see archived/locked dossiers
        self.client.force_login(self.admin_user)
        resp_admin = self.client.get(reverse("dossier_list"))
        self.assertEqual(resp_admin.status_code, 200)
        admin_ids = [d.archive_number for d in resp_admin.context["dossiers"]]
        self.assertIn(archived_22.archive_number, admin_ids)



