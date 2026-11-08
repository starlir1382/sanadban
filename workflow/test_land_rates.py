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
        self.assertEqual(d1.renovation_code, "8-806-12-5-2")
        self.assertGreater(d1.total_land_share, Decimal("0"))
