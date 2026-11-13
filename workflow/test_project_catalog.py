import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from workflow.models import HousingDossier, UserProfile
from workflow.project_catalog import (
    CATALOG_BANKS,
    CATALOG_BRANCHES,
    CATALOG_SITES,
    PROJECT_CATALOG,
    resolve_catalog_field,
)

User = get_user_model()


class ProjectCatalogStrictDropdownTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.expert = User.objects.create_user(username="stage1_catalog_user", password="password123")
        UserProfile.objects.update_or_create(
            user=self.expert,
            defaults={
                "full_name": "کارشناس مرحله یک",
                "role_title": "کارشناس ثبت",
                "allowed_stages": "1",
                "can_sign": True,
                "is_active_expert": True,
            },
        )
        self.dossier = HousingDossier.objects.create(
            archive_number=100990,
            national_id="0399990001",
            full_name="متقاضی لیست مجاز",
            current_stage=1,
            site="جعفریه",
            project="اعتمادگستر خاورمیانه جعفریه",
            project_code="1008075887",
            bank_name="بانک صادرات",
            bank_branch="شهید حیدریان",
        )

    def test_catalog_contains_all_96_projects_6_sites_and_5_banks(self):
        self.assertEqual(len(PROJECT_CATALOG), 96)
        self.assertEqual(len(CATALOG_SITES), 6)
        self.assertEqual(len(CATALOG_BANKS), 5)
        self.assertEqual(len(CATALOG_BRANCHES), 42)
        self.assertEqual(resolve_catalog_field("bank_name", "صادرات ایران"), (True, "بانک صادرات"))
        self.assertEqual(
            resolve_catalog_field("site", "سایت آیت الله رئیسی (560 هکتاری)"),
            (True, "رئیسی 560 هکتار"),
        )
        self.assertEqual(resolve_catalog_field("project_code", "۱۰۰۸۰۷۵۸۸۷"), (True, "1008075887"))
        self.assertFalse(resolve_catalog_field("project", "پروژه خارج از لیست")[0])

    def test_detail_view_renders_strict_searchable_dropdowns_and_catalog_json(self):
        self.client.force_login(self.expert)
        resp = self.client.get(reverse("dossier_detail", kwargs={"pk": self.dossier.archive_number}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        for field_id in ("f_site", "f_project", "f_project_code", "f_bank_name", "f_bank_branch", "f_project_code_j"):
            self.assertIn(f'id="{field_id}"', html)
            self.assertIn('class="df-input df-combo-input', html)

        self.assertIn("getCatalogItems(", html)
        self.assertIn("commitCatalogInput(", html)
        self.assertIn("selectCatalogItem(", html)
        self.assertIn("projects_catalog", html)
        self.assertIn("اعتمادگستر خاورمیانه جعفریه", html)
        self.assertIn("isApartmentSite", html)
        self.assertIn("isVillaConstruction", html)
        self.assertIn("مساحت اعیانی (m²)", html)
        self.assertIn("مساحت عرصه (m²)", html)
        self.assertIn("ویلایی (نیمه کاره)", html)

    def test_save_rejects_outside_values_for_all_5_catalog_fields(self):
        self.client.force_login(self.expert)
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})

        invalid_payloads = [
            {"project": "پروژه جعلی متفرقه"},
            {"project_code": "9999999999"},
            {"site": "سایت نامعتبر"},
            {"bank_name": "بانک خصوصی"},
            {"bank_branch": "شعبه خیالی"},
        ]
        for payload in invalid_payloads:
            resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
            self.assertEqual(resp.status_code, 400, f"Expected 400 for {payload}")
            self.assertEqual(resp.json()["status"], "error")

        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.project, "اعتمادگستر خاورمیانه جعفریه")
        self.assertEqual(self.dossier.project_code, "1008075887")
        self.assertEqual(self.dossier.site, "جعفریه")
        self.assertEqual(self.dossier.bank_name, "بانک صادرات")
        self.assertEqual(self.dossier.bank_branch, "شهید حیدریان")

    def test_save_accepts_and_canonicalizes_approved_catalog_values(self):
        self.client.force_login(self.expert)
        url = reverse("dossier_save", kwargs={"pk": self.dossier.archive_number})

        resp = self.client.post(
            url,
            data=json.dumps(
                {
                    "site": "سایت آیت الله رئیسی (560 هکتاری)",
                    "project": "بتن پوشش آگرین 2 قطعه 155 ",
                    "project_code": "۱۰۰۴۸۴۱۵۹۲",
                    "bank_name": "مسکن",
                    "bank_branch": "1404497",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.site, "رئیسی 560 هکتار")
        self.assertEqual(self.dossier.project, "بتن پوشش آگرین 2 قطعه 155")
        self.assertEqual(self.dossier.project_code, "1004841592")
        self.assertEqual(self.dossier.bank_name, "بانک مسکن")
        self.assertEqual(self.dossier.bank_branch, "شهدای قم")

    def test_legacy_non_catalog_project_allows_saving_unrelated_fields(self):
        legacy = HousingDossier.objects.create(
            archive_number=100991,
            national_id="0399990002",
            full_name="متقاضی قدیمی",
            current_stage=1,
            project="عامر مستقل 1",
            site="رئیسی 560 هکتار",
        )
        self.client.force_login(self.expert)
        url = reverse("dossier_save", kwargs={"pk": legacy.archive_number})
        resp = self.client.post(
            url,
            data=json.dumps({"project": "عامر مستقل 1", "father_name": "حسین"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        legacy.refresh_from_db()
        self.assertEqual(legacy.father_name, "حسین")
        self.assertEqual(legacy.project, "عامر مستقل 1")

    def test_villa_always_defaults_and_enforces_north_direction(self):
        villa = HousingDossier.objects.create(
            archive_number=100992,
            national_id="0399990003",
            full_name="متقاضی ویلایی",
            current_stage=1,
            site="قنوات",
            project="اعتمادگستر خاورمیانه قنوات",
            construction_type="ویلایی (نیمه کاره)",
            unit_direction="جنوبی",
        )
        self.assertEqual(villa.unit_direction, "شمالی")

        apt = HousingDossier.objects.create(
            archive_number=100993,
            national_id="0399990004",
            full_name="متقاضی آپارتمانی",
            current_stage=1,
            site="رئیسی 560 هکتار",
            project="داناک پژوه",
            construction_type="آپارتمانی",
            unit_direction="جنوب شرقی",
        )
        self.assertEqual(apt.unit_direction, "جنوب شرقی")

        self.client.force_login(self.expert)
        resp = self.client.get(reverse("dossier_detail", kwargs={"pk": villa.archive_number}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("|| isVillaConstruction()", html)
        self.assertIn('id="f_unit_direction"', html)
        self.assertNotIn("form.construction_type !== 'آپارتمانی'", html)
        self.assertIn('<option value="5">طبقه ۵</option>', html)
        server_start = html.index('<script id="dossier-server-json" type="application/json">')
        server_end = html.index("</script>", server_start)
        payload_json = json.loads(
            html[server_start + len('<script id="dossier-server-json" type="application/json">'):server_end].strip()
        )
        self.assertEqual(payload_json["form"]["unit_direction"], "شمالی")
        js_src = open("static/js/sanadban.js", encoding="utf-8").read()
        self.assertIn("syncUnitDirectionByConstruction", js_src)
