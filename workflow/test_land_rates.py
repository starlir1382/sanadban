"""
workflow/test_land_rates.py
Tests for Land Rates auto-calculation, Excel parsing, matching by (project + block_code),
and bulk update behavior.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User

from workflow.models import LandRate, HousingDossier, UserProfile
from workflow.land_rates import (
    LAND_LEASE_YEAR,
    normalize_code,
    strip_code,
    normalize_project,
    clean_project_fuzzy,
    normalize_block,
    clean_block_fuzzy,
    compute_land_values,
    get_rate,
    apply_land_calculation,
    reset_cache,
)


class LandRatesMatchingTestCase(TestCase):
    def setUp(self):
        reset_cache()
        # Seed test LandRates
        self.rate_mohanna = LandRate.objects.create(
            renovation_code="8-806-12-5-2-0-0",
            project_name="تدبیر عمران محنا",
            plot_number="307",
            block_name="K46",
            share_land=Decimal("0.731738046"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("588800"),
            rent_to_date_per_m2=Decimal("612706"),
            prep_per_m2=Decimal("19733922"),
        )
        self.rate_zanjan = LandRate.objects.create(
            renovation_code="8-806-43-4-1-0-0",
            project_name="زنجان ره گشا",
            plot_number="302",
            block_name="W18",
            share_land=Decimal("0.550000000"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("500000"),
            rent_to_date_per_m2=Decimal("550000"),
            prep_per_m2=Decimal("15000000"),
        )
        reset_cache()

    def test_strip_and_normalize_code(self):
        self.assertEqual(normalize_code(" 8-806-12-5-2-0-0 "), "8-806-12-5-2-0-0")
        self.assertEqual(strip_code("8-806-12-5-2-0-0"), "8-806-12-5-2")
        self.assertEqual(strip_code("8-806-12-5-2"), "8-806-12-5-2")

    def test_match_by_code_exact_and_stripped(self):
        r1 = get_rate(code="8-806-12-5-2-0-0")
        self.assertIsNotNone(r1)
        self.assertEqual(r1.block_name, "K46")

        r2 = get_rate(code="8-806-12-5-2")
        self.assertIsNotNone(r2)
        self.assertEqual(r2.block_name, "K46")

    def test_match_by_only_project_and_block_code(self):
        """User core requirement: guess information with only project and block_code."""
        # 1. Exact match
        rate = get_rate(project="تدبیر عمران محنا", block="k46")
        self.assertIsNotNone(rate)
        self.assertEqual(rate.renovation_code, "8-806-12-5-2-0-0")
        self.assertEqual(rate.plot_number, "307")
        self.assertEqual(rate.block_name, "K46")

        # 2. Match with corporate title prefix in project name
        rate_fuzzy = get_rate(project="شرکت راه و ساختمانی زنجان رهگشا", block="w18")
        self.assertIsNotNone(rate_fuzzy)
        self.assertEqual(rate_fuzzy.renovation_code, "8-806-43-4-1-0-0")
        self.assertEqual(rate_fuzzy.block_name, "W18")

    def test_apply_land_calculation_populates_missing_fields_and_calculates(self):
        dossier = HousingDossier(
            national_id="0012345678",
            full_name="علی محمدی",
            project="تدبیر عمران محنا",
            block_code="k46",
            net_unit_area=Decimal("90.00"),
            storage_area=Decimal("5.00"),
            parking_area=Decimal("0.00"),
        )
        # Verify initial un-saved state
        self.assertFalse(dossier.block_name)
        self.assertIsNone(dossier.plot_number)
        self.assertFalse(dossier.renovation_code)

        applied = apply_land_calculation(dossier)
        self.assertTrue(applied)

        # Missing dossier metadata should be auto-filled from matched LandRate
        self.assertEqual(dossier.block_name, "K46")
        self.assertEqual(dossier.plot_number, 307)
        self.assertEqual(dossier.renovation_code, "8-806-12-5-2")

        # Section 9 values should be calculated
        # total area = 95.00, coeff = 0.731738046 -> share = 69.52
        self.assertGreater(dossier.total_land_share, 0)
        self.assertGreater(dossier.current_year_rent, 0)
        self.assertGreater(dossier.past_years_rent, 0)
        self.assertGreater(dossier.preparation_cost, 0)
        self.assertEqual(str(dossier.land_lease_year), str(LAND_LEASE_YEAR))

    def test_dossier_save_auto_calculates_when_project_and_block_code_present(self):
        """HousingDossier.save() should automatically calculate Section 9."""
        d = HousingDossier(
            national_id="0098765432",
            full_name="رضا حسینی",
            project="تدبیر عمران محنا",
            block_code="k46",
            net_unit_area=Decimal("88.00"),
        )
        d.save()

        d.refresh_from_db()
        self.assertEqual(d.block_name, "K46")
        self.assertEqual(d.plot_number, 307)
        self.assertEqual(d.renovation_code, "8-806-12-5-2")
        self.assertGreater(d.total_land_share, Decimal("0"))
        self.assertGreater(d.current_year_rent, 0)
        self.assertEqual(str(d.land_lease_year), str(LAND_LEASE_YEAR))

    def test_locked_dossier_is_strictly_immutable(self):
        """Locked/archived dossiers must never be recalculated or modified."""
        d = HousingDossier.objects.create(
            national_id="0098765431",
            full_name="کاربر مختومه",
            project="تدبیر عمران محنا",
            block_code="k46",
            net_unit_area=Decimal("88.00"),
            is_locked=True,
            total_land_share=Decimal("50.00"),
            current_year_rent=1000000,
        )
        # Attempt direct calculation call
        applied = apply_land_calculation(d)
        self.assertFalse(applied)
        self.assertEqual(d.total_land_share, Decimal("50.00"))
        self.assertEqual(d.current_year_rent, 1000000)

        # Attempt recalculation via save
        d.save()
        d.refresh_from_db()
        self.assertEqual(d.total_land_share, Decimal("50.00"))
        self.assertEqual(d.current_year_rent, 1000000)


    def test_read_rates_from_excel_new_format(self):
        """Verify read_rates_from_excel supports 'نام شرکت' and 'جمع ضریب'."""
        import io
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "ردیف", "نام شرکت", "قطعه", "نام بلوک", "کد نوسازی",
            "مساحت بلوک", "زیربنای بلوک با کسر سرپله", "دسترسی به شارع",
            "مساحت قطعات", "مساحت عرصه قطعه منهای جمع مساحت عرصه بلوک",
            "متراژ مفید کل بلوک", "متراژ مفید کل قطعه",
            "جمع ضریب ", "هزینه هر متر اجاره سال جاری ",
            "هزینه هر متر اجاره سنوات تا پایان سال جاری ", "هزینه هر متر آماده سازی"
        ])
        ws.append([
            1, "شرکت آزمایشی نگین", 101, "A1", "8-806-50-1-1-0-0",
            500, 1200, "شارع 20 متری",
            600, 100,
            1000, 5000,
            0.654321, 600000, 650000, 18000000
        ])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        from workflow.land_rates import read_rates_from_excel
        rows, problems = read_rates_from_excel(buf)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["renovation_code"], "8-806-50-1-1-0-0")
        self.assertEqual(r["project_name"], "شرکت آزمایشی نگین")
        self.assertEqual(r["plot_number"], "101")
        self.assertEqual(r["block_name"], "A1")
        self.assertEqual(r["share_land"], Decimal("0.654321"))
        self.assertEqual(r["rent_current_per_m2"], Decimal("600000"))
        self.assertEqual(r["rent_to_date_per_m2"], Decimal("650000"))
        self.assertEqual(r["prep_per_m2"], Decimal("18000000"))


class LandRatesApiTestCase(TestCase):
    def setUp(self):
        reset_cache()
        self.user = User.objects.create_superuser(username="admin_test", password="password123")
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.allowed_stages = "all"
        profile.is_housing_chief = True
        profile.save()

        self.client = Client()
        self.client.force_login(self.user)

        self.rate = LandRate.objects.create(
            renovation_code="8-806-12-5-2-0-0",
            project_name="تدبیر عمران محنا",
            plot_number="307",
            block_name="K46",
            share_land=Decimal("0.731738046"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("588800"),
            rent_to_date_per_m2=Decimal("612706"),
            prep_per_m2=Decimal("19733922"),
        )
        reset_cache()

    def test_calculate_land_rates_api_with_project_and_block(self):
        response = self.client.get("/api/calculate-land-rates/", {
            "project": "تدبیر عمران محنا",
            "block_code": "k46",
            "net": "90.00",
            "storage": "5.00",
            "parking": "0.00",
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("rate_found"))
        self.assertEqual(data["data"]["block_name"], "K46")
        self.assertEqual(data["data"]["plot_number"], "307")
        self.assertGreater(data["data"]["total_land_share"], 0)
        self.assertGreater(data["data"]["current_year_rent"], 0)

    def test_bulk_apply_api(self):
        # Create dossier and reset calculations to simulate empty dossier
        d1 = HousingDossier.objects.create(
            national_id="0011223344",
            full_name="کاربر یک",
            project="تدبیر عمران محنا",
            block_code="k46",
            net_unit_area=Decimal("80.00"),
        )
        HousingDossier.objects.filter(id=d1.id).update(
            total_land_share=None,
            current_year_rent=0,
            block_name="",
            plot_number=None,
            renovation_code="",
        )
        d1.refresh_from_db()
        self.assertFalse(d1.total_land_share)

        response = self.client.post("/api/land-rates/bulk-apply/", {
            "project": "تدبیر عمران محنا",
            "only_empty": "true",
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("updated_count"), 1)

        d1.refresh_from_db()
        self.assertEqual(d1.block_name, "K46")
        self.assertEqual(d1.plot_number, 307)
        self.assertEqual(d1.renovation_code, "8-806-12-5-2")
        self.assertGreater(d1.total_land_share, Decimal("0"))


class ClearLandRatesScriptTestCase(TestCase):
    def setUp(self):
        reset_cache()
        LandRate.objects.create(
            renovation_code="8-806-12-5-2-0-0",
            project_name="پروژه الف",
            plot_number="307",
            block_name="K46",
            share_land=Decimal("0.7"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("500000"),
            rent_to_date_per_m2=Decimal("600000"),
            prep_per_m2=Decimal("10000000"),
        )
        LandRate.objects.create(
            renovation_code="8-806-43-4-1-0-0",
            project_name="پروژه ب",
            plot_number="302",
            block_name="W18",
            share_land=Decimal("0.5"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("400000"),
            rent_to_date_per_m2=Decimal("450000"),
            prep_per_m2=Decimal("9000000"),
        )
        self.dossier = HousingDossier.objects.create(
            national_id="0011223344",
            full_name="تست حفظ پرونده",
            project="پروژه الف",
            block_code="K46",
            net_unit_area=Decimal("80.00"),
        )

    def test_dry_run_does_not_delete(self):
        import io
        from scripts.clear_land_rates import clear_land_rates

        buf = io.StringIO()
        res = clear_land_rates(confirm=False, stdout=buf)
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["deleted_count"], 0)
        self.assertEqual(LandRate.objects.count(), 2)
        self.assertEqual(HousingDossier.objects.count(), 1)

    def test_project_filtered_clear(self):
        import io
        from scripts.clear_land_rates import clear_land_rates

        buf = io.StringIO()
        res = clear_land_rates(confirm=True, project="پروژه الف", stdout=buf)
        self.assertFalse(res["dry_run"])
        self.assertEqual(res["deleted_count"], 1)
        self.assertEqual(res["remaining_count"], 1)
        self.assertFalse(res["sequence_reset"])
        self.assertEqual(LandRate.objects.filter(project_name="پروژه ب").count(), 1)
        self.assertEqual(HousingDossier.objects.count(), 1)

    def test_full_clear_resets_table_and_cache(self):
        import io
        from scripts.clear_land_rates import clear_land_rates

        # Warm the cache first
        self.assertIsNotNone(get_rate(code="8-806-12-5-2-0-0"))

        buf = io.StringIO()
        res = clear_land_rates(confirm=True, stdout=buf)
        self.assertFalse(res["dry_run"])
        self.assertEqual(res["deleted_count"], 2)
        self.assertEqual(res["remaining_count"], 0)
        self.assertEqual(LandRate.objects.count(), 0)
        self.assertEqual(HousingDossier.objects.count(), 1)
        self.assertIsNone(get_rate(code="8-806-12-5-2-0-0"))

        new_rate = LandRate.objects.create(
            renovation_code="8-806-99-1-1",
            project_name="پروژه جدید",
            plot_number="1",
            block_name="A1",
            share_land=Decimal("0.5"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("100000"),
            rent_to_date_per_m2=Decimal("100000"),
            prep_per_m2=Decimal("1000000"),
        )
        self.assertEqual(new_rate.id, 1)

    def test_section9_formula_breakdown_in_api_and_detail_view(self):
        """API and dossier detail view include exact coefficient, area terms, and per-m2 rates for Section 9."""
        from django.contrib.auth import get_user_model
        from django.test import Client
        from django.urls import reverse
        from workflow.models import LandRate

        User = get_user_model()
        user = User.objects.create_user(username="sec9_viewer", password="pw")
        user.profile.allowed_stages = "16"
        user.profile.save()

        LandRate.objects.create(
            renovation_code="8-806-55-1-1",
            project_name="تدبیر عمران محنا",
            plot_number="99",
            block_name="Z9",
            share_land=Decimal("0.600000000"),
            share_common=Decimal("0.131738046"),
            rent_current_per_m2=Decimal("10000000"),
            rent_to_date_per_m2=Decimal("20000000"),
            prep_per_m2=Decimal("30000000"),
        )
        reset_cache()

        dossier = HousingDossier.objects.create(
            archive_number=100995,
            national_id="0399990009",
            full_name="متقاضی فرمول بخش نه",
            current_stage=16,
            renovation_code="8-806-55-1-1",
            net_unit_area=Decimal("88.00"),
            storage_area=Decimal("5.00"),
            parking_area=Decimal("15.00"),
        )

        client = Client()
        client.force_login(user)

        api_resp = client.get(
            reverse("calculate_land_rates_api"),
            {"code": "8-806-55-1-1", "net": "88", "storage": "5", "parking": "15"},
        )
        self.assertEqual(api_resp.status_code, 200)
        d = api_resp.json()["data"]
        self.assertEqual(d["share_land"], "0.6")
        self.assertEqual(d["share_common"], "0.131738046")
        self.assertEqual(d["share_coefficient"], "0.731738046")
        self.assertEqual(d["rent_current_per_m2"], 10000000)
        self.assertEqual(d["rent_to_date_per_m2"], 20000000)
        self.assertEqual(d["prep_per_m2"], 30000000)

        detail_resp = client.get(reverse("dossier_detail", kwargs={"pk": dossier.archive_number}))
        self.assertEqual(detail_resp.status_code, 200)
        html = detail_resp.content.decode("utf-8")
        self.assertIn("df-formula-box", html)
        self.assertIn('class="df-formula-row" dir="ltr"', html)
        self.assertIn('class="df-excel-grid" dir="ltr"', html)
        self.assertIn('class="df-f-rate-expr" dir="ltr"', html)
        self.assertIn("متراژ مفید", html)
        self.assertIn("انباری", html)
        self.assertIn("پارکینگ", html)
        self.assertIn("جمع متراژ", html)
        self.assertIn("ضریب قدرالسهم", html)
        self.assertIn("آماده‌سازی هر متر (ریال)", html)
        self.assertIn("اجاره سنوات هر متر (ریال)", html)
        self.assertIn("اجاره سال جاری هر متر (ریال)", html)
        self.assertIn("قدرالسهم از عرصه", html)
        self.assertIn("قدرالسهم از مشاع", html)
        self.assertIn("جمع ضریب قدرالسهم", html)
        self.assertIn("land_rate_info", html)
        self.assertIn("0.731738046", html)
        self.assertIn("30000000", html)
        sec9_html = html[html.index('id="section-valuation-body"') : html.index('id="section-checks"')]
        self.assertLess(sec9_html.index("form.total_land_share"), sec9_html.index('class="df-formula-box'))

    def test_fuzzy_project_plot_block_lookup_disambiguation(self):
        """Alias/corporate naming variants match exact LandRate without cross-project or cross-phase collisions."""
        from workflow.models import LandRate
        from workflow.land_rates import get_rate

        LandRate.objects.create(
            renovation_code="8-806-78-1-1",
            project_name="تعاونی سپاه علی ابن ابیطالب",
            plot_number="27",
            block_name="KK",
            share_land=Decimal("0.692840716"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        LandRate.objects.create(
            renovation_code="8-806-74-2-7",
            project_name="بسیج سازندگی",
            plot_number="5",
            block_name="KK",
            share_land=Decimal("0.740000000"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        LandRate.objects.create(
            renovation_code="8-806-99-1-1",
            project_name="کیمیا بنا پارس",
            plot_number="281",
            block_name="M2",
            share_land=Decimal("0.650000000"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        LandRate.objects.create(
            renovation_code="8-806-88-1-1",
            project_name="فاطر سازه ایلیا2",
            plot_number="370",
            block_name="Y5",
            share_land=Decimal("0.620000000"),
            share_common=Decimal("0"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        reset_cache()

        r_sepah = get_rate(
            project="تعاونی مسکن پیشتازان سرافراز قم (تعاونی مسکن کارکنان سپاه علی ابن ابیطالب (ع))",
            plot="27",
            block="kk-36",
        )
        self.assertIsNotNone(r_sepah)
        self.assertEqual(r_sepah.renovation_code, "8-806-78-1-1")

        r_basij = get_rate(
            project="سازمان بسیج سازندگی سپاه امام علی ابن ابیطالب (ع)",
            plot="5",
            block="KK",
        )
        self.assertIsNotNone(r_basij)
        self.assertEqual(r_basij.renovation_code, "8-806-74-2-7")

        r_kimia = get_rate(project="شرکت مهندسی کیمیا بنای پارس", plot="281", block="M2")
        self.assertIsNotNone(r_kimia)
        self.assertEqual(r_kimia.renovation_code, "8-806-99-1-1")

        r_fater = get_rate(project="فاطر سازه ایلیا 1 و 2", plot="370", block="Y5")
        self.assertIsNotNone(r_fater)
        self.assertEqual(r_fater.renovation_code, "8-806-88-1-1")
