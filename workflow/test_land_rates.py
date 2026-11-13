"""
workflow/test_land_rates.py
Tests for Land Rates auto-calculation, Excel parsing, matching by (project + block_code),
and bulk update behavior.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User

from workflow.models import LandRate, VillaLandRate, HousingDossier, UserProfile
from workflow.land_rates import (
    LAND_LEASE_YEAR,
    normalize_code,
    strip_code,
    normalize_project,
    clean_project_fuzzy,
    normalize_block,
    clean_block_fuzzy,
    normalize_registry_plaque,
    plaque_candidates,
    compute_land_values,
    compute_villa_land_values,
    get_rate,
    get_villa_rate,
    apply_land_calculation,
    read_villa_rates_from_excel,
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
            share_coefficient=Decimal("0.731738046"),
            rent_current_per_m2=Decimal("588800"),
            rent_to_date_per_m2=Decimal("612706"),
            prep_per_m2=Decimal("19733922"),
        )
        self.rate_zanjan = LandRate.objects.create(
            renovation_code="8-806-43-4-1-0-0",
            project_name="زنجان ره گشا",
            plot_number="302",
            block_name="W18",
            share_coefficient=Decimal("0.550000000"),
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
        self.assertEqual(r["share_coefficient"], Decimal("0.654321"))
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
            share_coefficient=Decimal("0.731738046"),
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
            share_coefficient=Decimal("0.7"),
            rent_current_per_m2=Decimal("500000"),
            rent_to_date_per_m2=Decimal("600000"),
            prep_per_m2=Decimal("10000000"),
        )
        LandRate.objects.create(
            renovation_code="8-806-43-4-1-0-0",
            project_name="پروژه ب",
            plot_number="302",
            block_name="W18",
            share_coefficient=Decimal("0.5"),
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
            share_coefficient=Decimal("0.5"),
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
            share_coefficient=Decimal("0.731738046"),
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
        self.assertNotIn("share_land", d)
        self.assertNotIn("share_common", d)
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
        self.assertIn("مجموع ضریب قدرالسهم", html)
        self.assertIn("نرخ‌های مصوب به ازای هر متر مربع (اکسل)", html)
        self.assertIn("آماده‌سازی هر متر (ریال)", html)
        self.assertIn("اجاره سنوات هر متر (ریال)", html)
        self.assertIn("اجاره سال جاری هر متر (ریال)", html)
        self.assertNotIn("قدرالسهم از عرصه", html)
        self.assertNotIn("قدرالسهم از مشاع", html)
        self.assertNotIn("جمع ضریب قدرالسهم", html)
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
            share_coefficient=Decimal("0.692840716"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        LandRate.objects.create(
            renovation_code="8-806-74-2-7",
            project_name="بسیج سازندگی",
            plot_number="5",
            block_name="KK",
            share_coefficient=Decimal("0.740000000"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        LandRate.objects.create(
            renovation_code="8-806-99-1-1",
            project_name="کیمیا بنا پارس",
            plot_number="281",
            block_name="M2",
            share_coefficient=Decimal("0.650000000"),
            rent_current_per_m2=Decimal("441600"),
            rent_to_date_per_m2=Decimal("468550"),
            prep_per_m2=Decimal("19733922"),
        )
        LandRate.objects.create(
            renovation_code="8-806-88-1-1",
            project_name="فاطر سازه ایلیا2",
            plot_number="370",
            block_name="Y5",
            share_coefficient=Decimal("0.620000000"),
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

    def test_read_rates_from_excel_sums_two_share_columns_and_upload(self):
        """If an Excel sheet provides separate land + common/ayan columns, sum both into share_coefficient."""
        import io
        import openpyxl
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse
        from workflow.land_rates import read_rates_from_excel

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "نام پروژه", "قطعه", "نام بلوک", "کد نوسازی",
            "ضریب قدرالسهم عرصه", "ضریب قدرالسهم عیان",
            "مبلغ اجاره یک متر سال جاری (ریال)", "علی‌الحساب اجاره تا پایان سال جاری (ریال)",
            "مبلغ یک متر هزینه آماده‌سازی (ریال)",
        ])
        ws.append([
            "پروژه تجمیع", "12", "B2", "8-806-70-1-1",
            0.600000000, 0.131738046,
            500000, 550000, 19000000,
        ])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        raw_bytes = buf.getvalue()
        parsed, problems = read_rates_from_excel(io.BytesIO(raw_bytes))
        self.assertEqual(problems, [])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["share_coefficient"], Decimal("0.731738046"))

        user = User.objects.create_superuser(username="upload_tester", password="password123")
        client = Client()
        client.force_login(user)
        uploaded = SimpleUploadedFile(
            "rates.xlsx",
            raw_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = client.post(reverse("land_rates_upload_excel_api"), {"excel_file": uploaded})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        saved = LandRate.objects.get(renovation_code="8-806-70-1-1")
        self.assertEqual(saved.share_coefficient, Decimal("0.731738046"))

    def test_land_rates_export_and_update_use_single_share_coefficient(self):
        """Excel export and update API use only share_coefficient ('مجموع ضریب قدرالسهم')."""
        import io
        import json
        import openpyxl
        from django.urls import reverse

        rate = LandRate.objects.create(
            renovation_code="8-806-71-1-1",
            project_name="پروژه خروجی",
            plot_number="44",
            block_name="C3",
            share_coefficient=Decimal("0.650000000"),
            rent_current_per_m2=Decimal("500000"),
            rent_to_date_per_m2=Decimal("600000"),
            prep_per_m2=Decimal("15000000"),
        )
        user = User.objects.create_superuser(username="export_tester", password="password123")
        client = Client()
        client.force_login(user)

        upd = client.post(
            reverse("land_rates_update_api", kwargs={"pk": rate.pk}),
            data=json.dumps({"share_coefficient": "0.750000000"}),
            content_type="application/json",
        )
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.json()["rate"]["share_coefficient"], "0.750000000")
        rate.refresh_from_db()
        self.assertEqual(rate.share_coefficient, Decimal("0.750000000"))

        exp = client.get(reverse("land_rates_export_excel"))
        self.assertEqual(exp.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(exp.content), data_only=True)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertIn("مجموع ضریب قدرالسهم", headers)
        self.assertNotIn("قدرالسهم از عرصه", headers)
        self.assertNotIn("قدرالسهم از مشاع", headers)
        coeff_idx = headers.index("مجموع ضریب قدرالسهم")
        code_idx = headers.index("کد نوسازی")
        matching_rows = [row for row in ws.iter_rows(min_row=2, values_only=True) if row[code_idx] == "8-806-71-1-1"]
        self.assertEqual(len(matching_rows), 1)
        self.assertAlmostEqual(float(matching_rows[0][coeff_idx]), 0.75, places=6)

    def test_appraisal_preparation_80_20_rounding(self):
        """80% installment rounds down to 10,000,000 Rials and the remainder is added to 20% cash."""
        import json
        import shutil
        import subprocess
        from django.conf import settings

        node_bin = shutil.which("node")
        self.assertIsNotNone(node_bin, "Node.js is required to test static/js/sanadban.js")

        js_path = settings.BASE_DIR / "static" / "js" / "sanadban.js"
        node_script = """
const fs = require("fs");
const vm = require("vm");
const listeners = {};
let factory = null;
const noop = () => {};
const ctx = {
  console,
  Math,
  Number,
  String,
  Boolean,
  Array,
  Object,
  JSON,
  Intl,
  Date,
  RegExp,
  Error,
  parseInt,
  parseFloat,
  isNaN,
  setTimeout: noop,
  clearTimeout: noop,
  localStorage: { getItem: () => null, setItem: noop },
  fetch: async () => ({ ok: true, json: async () => ({}) }),
  CustomEvent,
  Alpine: { data: (name, fn) => { if (name === "sanadbanApp") factory = fn; } },
  window: { location: { pathname: "/" }, addEventListener: noop, dispatchEvent: noop, matchMedia: () => ({ matches: false }) },
  document: {
    readyState: "complete",
    cookie: "",
    documentElement: { setAttribute: noop, getAttribute: () => null },
    querySelectorAll: () => [],
    getElementById: () => null,
    addEventListener: (ev, cb) => { listeners[ev] = cb; },
  },
};
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), ctx);
listeners["alpine:init"]();
const app = factory();
app.triggerToast = noop;

const cases = [1517341263, 12500000, 5000000, 0];
const results = cases.map((prep) => {
  app.form.preparation_cost = prep;
  return {
    prep,
    cash: app.getAppraisalCash(),
    installment: app.getAppraisalInstallment(),
  };
});

app.form.preparation_cost = 1517341263;
app.applyAppraisalCash();
app.applyAppraisalInstallment();
console.log(JSON.stringify({
  results,
  appliedCash: app.form.cash_preparation_amount,
  appliedInstallment: app.form.non_cash_preparation_amount,
}));
"""
        proc = subprocess.run(
            [node_bin, "-e", node_script, str(js_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Node failed:\n{proc.stderr}")
        payload = json.loads(proc.stdout)
        by_prep = {row["prep"]: row for row in payload["results"]}

        # 1,517,341,263 -> 80% unrounded 1,213,873,010 -> rounded down 1,210,000,000;
        # remainder 3,873,010 moves to 20% cash: 303,468,253 + 3,873,010 = 307,341,263
        self.assertEqual(by_prep[1517341263]["installment"], 1210000000)
        self.assertEqual(by_prep[1517341263]["cash"], 307341263)
        self.assertEqual(by_prep[1517341263]["cash"] + by_prep[1517341263]["installment"], 1517341263)

        # Exact 10M multiple in 80% keeps exact 80/20 split
        self.assertEqual(by_prep[12500000]["installment"], 10000000)
        self.assertEqual(by_prep[12500000]["cash"], 2500000)

        # Under 10M in 80% floors installment to 0 and shifts full amount to cash
        self.assertEqual(by_prep[5000000]["installment"], 0)
        self.assertEqual(by_prep[5000000]["cash"], 5000000)

        self.assertEqual(by_prep[0]["installment"], 0)
        self.assertEqual(by_prep[0]["cash"], 0)

        self.assertEqual(payload["appliedCash"], 307341263)
        self.assertEqual(payload["appliedInstallment"], 1210000000)

        # Verify bumped cache-buster is rendered on base/login pages
        base_html = (settings.BASE_DIR / "templates" / "base.html").read_text(encoding="utf-8")
        login_html = (settings.BASE_DIR / "templates" / "auth" / "login.html").read_text(encoding="utf-8")
        self.assertIn("sanadban.js' %}?v=3.7", base_html)
        self.assertIn("sanadban.js' %}?v=3.7", login_html)


class VillaLandRatesTestCase(TestCase):
    """Comprehensive tests for ویلایی (پلاک ثبتی) rates, Excel import/export, API, and Section 9."""

    def setUp(self):
        reset_cache()
        self.admin_user = User.objects.create_superuser("villa_admin", "v@example.com", "pass1234")
        UserProfile.objects.update_or_create(
            user=self.admin_user,
            defaults={"is_housing_chief": True, "allowed_stages": "all"},
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

        self.villa_abmo = VillaLandRate.objects.create(
            registry_plaque="11507/957/3825",
            project_name="آبمواسپاد",
            plot_number="2825",
            street_width="خیابان 12 متری",
            land_area=Decimal("197.75"),
            rent_current=Decimal("29186533.5000"),
            rent_to_date=Decimal("40749732.9800"),
            preparation_cost=Decimal("2849930100.0000"),
        )
        self.villa_parnian = VillaLandRate.objects.create(
            registry_plaque="114/4/2151",
            project_name="خانه سازان پویا 3 پرنیان",
            plot_number="101",
            land_area=Decimal("200.00"),
            rent_current=Decimal("15000000"),
            rent_to_date=Decimal("22000000"),
            preparation_cost=Decimal("1800000000"),
        )

    def test_plaque_normalization_and_swapped_order_lookup(self):
        self.assertEqual(normalize_registry_plaque("۱۱۵۰۷\\۹۵۷-۳۸۲۵"), "11507/957/3825")
        cands = plaque_candidates(main_plaque=11507, separated_plaque=3825, sub_plaque=957)
        self.assertIn("11507/957/3825", cands)
        self.assertIn("11507/3825/957", cands)

        # Qanavat swapped order + fuzzy project match: آبمو اسپاد 2 قنوات -> آبمواسپاد
        matched = get_villa_rate(
            project="آبمو اسپاد 2 قنوات",
            main_plaque=11507,
            separated_plaque=3825,
            sub_plaque=957,
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched.pk, self.villa_abmo.pk)

        # Parnian canonical order (main / separated / sub)
        matched_p = get_villa_rate(
            project="خانه سازان پویا 3 پرنیان",
            main_plaque=114,
            separated_plaque=4,
            sub_plaque=2151,
        )
        self.assertIsNotNone(matched_p)
        self.assertEqual(matched_p.pk, self.villa_parnian.pk)

        # Cross-phase protection: پویا 2 must NOT match پویا 3
        wrong_phase = get_villa_rate(
            project="خانه سازان پویا 2 پرنیان",
            main_plaque=114,
            separated_plaque=4,
            sub_plaque=2151,
        )
        self.assertIsNone(wrong_phase)

    def test_exact_values_preserved_and_personal_columns_ignored_in_excel(self):
        import io
        import openpyxl

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "آبمواسپاد"
        ws1.append(["پلاک", "پلاک ثبتی", "مساحت", "معبر", "تعاونی", "اجاره405", "اجاره تا405", "آماده سازی"])
        ws1.append([2695, "11507/957/3695", 197.75, "خیابان 12 متری", "آبمواسپاد", 29186533.5, 40749732.98, 2849930100])
        ws1.append([2694, "11507/957/3694", 200.00, "خیابان 12 متری", "آبمواسپاد", 29518200, 41212800, 2882315800])

        ws2 = wb.create_sheet("Sheet2")
        ws2.append(["شهرک اول"])
        ws2.append(["ردیف", "نام و نام خانوادگی", "کدملی", "شماره تماس", "پلاک ثبتی", "مساحت (مترمربع)", "نحوه واگذاری", "هزینه به ازای هر متر", "هزینه آماده سازی"])
        ws2.append([1, "علی رضایی", "0381234567", "09121234567", "10/223/1234", 200, "فرماندهی انتظامی", 12000000, None])
        ws2.append([2, "سارا محمدی", "0389999999", "09129999999", "10/223/1235", 195, "نیروگاه", 12000000, 2300000000])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        rows, problems = read_villa_rates_from_excel(buf)
        self.assertEqual(len(rows), 4)
        self.assertEqual(problems, [])

        by_key = {(r["project_name"], r["registry_plaque"]): r for r in rows}
        row_3695 = by_key[("آبمواسپاد", "11507/957/3695")]
        # Exact values preserved without re-multiplying rounded 197.75
        self.assertEqual(row_3695["rent_current"], Decimal("29186533.5"))
        self.assertEqual(row_3695["rent_to_date"], Decimal("40749732.98"))
        self.assertEqual(row_3695["preparation_cost"], Decimal("2849930100"))

        row_1234 = by_key[("شهرک اول", "10/223/1234")]
        self.assertEqual(row_1234["preparation_cost"], Decimal("2400000000"))
        self.assertEqual(row_1234["allocation_type"], "فرماندهی انتظامی")
        # Strictly zero personal data keys or content
        for forbidden_key in ("نام", "full_name", "national_id", "کدملی", "mobile", "phone"):
            self.assertNotIn(forbidden_key, row_1234)
        self.assertNotIn("علی رضایی", str(row_1234))

        row_1235 = by_key[("شهرک اول", "10/223/1235")]
        # Explicit preparation total is kept unmodified rather than overridden by 195 * 12M
        self.assertEqual(row_1235["preparation_cost"], Decimal("2300000000"))

    def test_villa_dossier_auto_calc_and_isolation_from_apartment(self):
        # Locked villa dossier must stay unchanged
        locked_v = HousingDossier.objects.create(
            archive_number=990001,
            full_name="تست قفل",
            national_id="0381111111",
            site="قنوات",
            construction_type="ویلایی",
            project="آبمو اسپاد 2 قنوات",
            main_plaque=11507,
            separated_plaque=3825,
            sub_plaque=957,
            is_locked=True,
            current_year_rent=100,
        )
        self.assertEqual(locked_v.current_year_rent, 100)

        # Open Qanavat villa dossier auto-populates exact Section 9 fields
        open_v = HousingDossier.objects.create(
            archive_number=990002,
            full_name="تست قنوات",
            national_id="0382222222",
            site="قنوات",
            construction_type="ویلایی",
            project="آبمو اسپاد 2 قنوات",
            main_plaque=11507,
            separated_plaque=3825,
            sub_plaque=957,
        )
        self.assertEqual(open_v.total_land_share, Decimal("197.75"))
        self.assertEqual(open_v.current_year_rent, 29186534)
        self.assertEqual(open_v.past_years_rent, 40749733)
        self.assertEqual(open_v.preparation_cost, 2849930100)
        self.assertEqual(str(open_v.land_lease_year), "1405")
        self.assertEqual(open_v.plot_number, 2825)

        # Apartment dossier with matching plaque numbers must NOT use VillaLandRate
        apt_d = HousingDossier.objects.create(
            archive_number=990003,
            full_name="تست آپارتمانی",
            national_id="0383333333",
            site="سایت 560 هکتاری",
            construction_type="آپارتمانی",
            project="آبمواسپاد",
            main_plaque=11507,
            separated_plaque=3825,
            sub_plaque=957,
        )
        self.assertEqual(apt_d.current_year_rent, 0)
        self.assertEqual(apt_d.preparation_cost, 0)

    def test_villa_admin_tabs_upload_update_export_bulk_and_detail_api(self):
        import io
        import json
        import openpyxl

        # 1. Admin tab view renders ویلایی rows
        resp = self.client.get("/admin/land-rates/?tab=villa")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("ویلایی (پلاک ثبتی)", html)
        self.assertIn("11507/957/3825", html)
        self.assertIn("/api/land-rates/export-excel/", html)
        self.assertIn("/api/land-rates/villa/export-excel/", html)

        # 2. Inline update API
        up_resp = self.client.post(
            f"/api/land-rates/villa/{self.villa_abmo.pk}/update/",
            data=json.dumps({"street_width": "خیابان ۱۴ متری"}),
            content_type="application/json",
        )
        self.assertEqual(up_resp.status_code, 200)
        self.assertTrue(up_resp.json()["success"])
        self.villa_abmo.refresh_from_db()
        self.assertEqual(self.villa_abmo.street_width, "خیابان ۱۴ متری")

        # 3. Upload Excel API (ignoring personal columns + preserving exact numbers)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ردیف", "نام و نام خانوادگی", "کدملی", "پلاک ثبتی", "مساحت", "هزینه به ازای هر متر", "هزینه آماده سازی"])
        ws.append([1, "متقاضی نمونه", "0387777777", "10/223/888", 210, 10000000, None])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = "villa_upload.xlsx"

        ul_resp = self.client.post(
            "/api/land-rates/villa/upload-excel/",
            {"excel_file": buf, "default_project": "شهرک اول"},
        )
        self.assertEqual(ul_resp.status_code, 200)
        self.assertTrue(ul_resp.json()["success"])
        self.assertTrue(VillaLandRate.objects.filter(registry_plaque="10/223/888", project_name="شهرک اول").exists())

        # 4. Export Excel API contains zero personal data headers
        ex_resp = self.client.get("/api/land-rates/villa/export-excel/")
        self.assertEqual(ex_resp.status_code, 200)
        ex_wb = openpyxl.load_workbook(io.BytesIO(ex_resp.content))
        ex_headers = [c.value for c in ex_wb.active[1]]
        self.assertNotIn("نام و نام خانوادگی", ex_headers)
        self.assertNotIn("کدملی", ex_headers)
        self.assertIn("پلاک ثبتی", ex_headers)

        # 5. Live calculation API for ویلایی
        api_resp = self.client.get(
            "/api/calculate-land-rates/",
            {
                "site": "قنوات",
                "construction_type": "ویلایی",
                "project": "آبمو اسپاد 2 قنوات",
                "main_plaque": "11507",
                "separated_plaque": "3825",
                "sub_plaque": "957",
            },
        )
        self.assertEqual(api_resp.status_code, 200)
        payload = api_resp.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["rate_type"], "villa")
        self.assertEqual(payload["data"]["preparation_cost"], 2849930100)
        self.assertEqual(payload["data"]["rent_current_exact"], "29186533.5")

        # 6. Bulk apply API updates villa dossiers missing Section 9 values
        dossier = HousingDossier.objects.create(
            archive_number=990004,
            full_name="تست گروهی ویلایی",
            national_id="0384444444",
            site="قنوات",
            construction_type="ویلایی",
            project="شهرک اول",
            main_plaque=10,
            separated_plaque=888,
            sub_plaque=223,
        )
        HousingDossier.objects.filter(pk=dossier.pk).update(preparation_cost=0, total_land_share=None)
        ba_resp = self.client.post("/api/land-rates/villa/bulk-apply/", {"project": "شهرک اول"})
        self.assertEqual(ba_resp.status_code, 200)
        self.assertEqual(ba_resp.json()["updated_count"], 1)
        dossier.refresh_from_db()
        self.assertEqual(dossier.preparation_cost, 2100000000)

        # 7. Dossier detail view injects villa land_rate_info cleanly
        det_resp = self.client.get(f"/dossier/{dossier.pk}/")
        self.assertEqual(det_resp.status_code, 200)
        det_html = det_resp.content.decode("utf-8")
        self.assertIn("جزئیات نرخ ویلایی", det_html)
        self.assertIn("10/223/888", det_html)

