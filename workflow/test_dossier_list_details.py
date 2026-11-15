from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from workflow.models import HousingDossier, DossierCheck

User = get_user_model()

class DossierListDetailsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="testadmin",
            password="password123",
            email="testadmin@example.com"
        )
        self.profile = self.user.profile
        self.profile.allowed_stages = "all"
        self.profile.allowed_projects = "ALL"
        self.profile.save()

        self.client = Client()
        self.client.login(username="testadmin", password="password123")

        # Dossier 1: With valid phone, plaque, bank, REAL check, notary office, and visit date
        self.dossier = HousingDossier.objects.create(
            first_name="علی",
            last_name="احمدی رضایی",
            national_id="0012345678",
            archive_number=1001,
            applicant_phone="09123456789",
            father_name="محمد",
            main_plaque="1234",
            bank_name="بانک مسکن",
            bank_loan_amount=6500000000,
            block_code="B12",
            unit_number="104",
            current_stage=6,
            project="پروژه زیتون",
            site="سایت ۵",
            decile=4,
            notary_office_number="24",
            loan_visit_date="1403/07/20",
            applicant_form_j_status="سبز (استعلام شده)"
        )
        DossierCheck.objects.create(
            dossier=self.dossier,
            row_number=1,
            check_type="LOAN",
            check_amount=250000000,
            check_sayadi_code="1234567890123456",
            cash_date="1403/08/15",
            bank_name="ملی"
        )

        # Dossier 2: With placeholder 0-amount checks (should NOT show checks or green Form J)
        self.dossier_empty_checks = HousingDossier.objects.create(
            first_name="حسن",
            last_name="اکبری",
            national_id="0098765432",
            archive_number=1002,
            applicant_phone="09998887766",
            bank_name="بانک ملی",
            current_stage=4,
            project="پروژه بهار",
            site="سایت ۲",
            applicant_form_j_status="سبز (استعلام شده)"
        )
        DossierCheck.objects.create(
            dossier=self.dossier_empty_checks,
            row_number=1,
            check_type="LOAN",
            check_amount=0,
            check_sayadi_code="",
            cash_date="",
            bank_name="بانک مسکن"
        )
        DossierCheck.objects.create(
            dossier=self.dossier_empty_checks,
            row_number=2,
            check_type="LOAN",
            check_amount=0,
            check_sayadi_code="",
            cash_date="",
            bank_name="بانک مسکن"
        )

    def test_dossier_list_renders_details_drawer(self):
        url = reverse('dossier_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")

        # 1. Check detail row presence for dossier 1
        self.assertIn(f'id="dossier-detail-{self.dossier.id}"', content)
        self.assertIn('09123456789', content)
        self.assertIn('بانک مسکن', content)
        self.assertIn('1234', content)
        self.assertIn('دهک <strong style="color: #4338ca;">4</strong>', content)
        # Checks are omitted from details drawer per user request
        self.assertNotIn('اطلاعات چک‌های صیادی', content)

        # 2. Notary office number is rendered on the row
        self.assertIn('دفترخانه 24', content)

        # 3. پیگیری راه و شهرسازی is inside details drawer with clear meaningful names
        self.assertIn('تاریخ‌های پیگیری اداره کل:', content)
        self.assertIn('مراجعه تسهیلات:', content)
        self.assertIn('1403/07/20', content)

        # 4. Standalone table column header for tracking is removed from main table
        self.assertNotIn('<th class="t-center" style="font-size: 0.8rem;">پیگیری راه و شهرسازی</th>', content)

        # 5. Bank loan amount is omitted
        self.assertNotIn('مبلغ تسهیلات وام بانکی', content)
        self.assertNotIn('مبلغ وام بانکی مسکن', content)

        # 6. Green form J is NOT shown
        self.assertNotIn('✓ سبز (استعلام شده)', content)

        # 7. For dossier 2: empty 0-amount placeholder checks are NOT shown
        self.assertEqual(len(self.dossier_empty_checks.valid_check_items), 0)
        pos = content.find(f'id="dossier-detail-{self.dossier_empty_checks.id}"')
        self.assertNotEqual(pos, -1)
        sub_content = content[pos:pos+1500]
        self.assertNotIn('۰ ریال', sub_content)
        self.assertNotIn('(2 فقره چک)', sub_content)

    def test_dossier_list_search_by_phone_and_bank(self):
        url = reverse('dossier_list')
        # Search by phone
        resp_phone = self.client.get(f"{url}?q=09123456789")
        self.assertEqual(resp_phone.status_code, 200)
        self.assertIn("علی", resp_phone.content.decode("utf-8"))

        # Search by bank
        resp_bank = self.client.get(f"{url}?q=بانک مسکن")
        self.assertEqual(resp_bank.status_code, 200)
        self.assertIn("علی", resp_bank.content.decode("utf-8"))

        # Search by notary office
        resp_notary = self.client.get(f"{url}?q=24")
        self.assertEqual(resp_notary.status_code, 200)
        self.assertIn("علی", resp_notary.content.decode("utf-8"))
