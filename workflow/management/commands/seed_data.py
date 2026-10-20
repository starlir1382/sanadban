from django.core.management.base import BaseCommand
from django.utils import timezone
from workflow.models import Site, Project, PreSelectedUnit, HousingDossier, DossierAttachment, WorkflowSignatureLog

class Command(BaseCommand):
    help = "Seed initial sites, projects, pre-selected units and test dossiers for SanadBan across 24 stages."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding SanadBan database with 24-Stage Workflow & Document Scans...")

        # 1. Create Sites
        site_names = ["شهید رئیسی", "27 هکتاری", "قنوات", "پرنیان", "جعفریه"]
        sites = {}
        for s_name in site_names:
            site_obj, _ = Site.objects.get_or_create(name=s_name, defaults={"code": f"SITE-{s_name[:3]}"})
            sites[s_name] = site_obj

        # 2. Create Projects
        p1, _ = Project.objects.get_or_create(
            site=sites["شهید رئیسی"],
            name="پروژه ۵۶۰ هکتاری فاز ۲ (۳۲۰ واحدی)",
            defaults={"total_units": 320}
        )
        p2, _ = Project.objects.get_or_create(
            site=sites["پرنیان"],
            name="پروژه ویلایی پرنیان فاز ۱ (۱۵۰ واحدی)",
            defaults={"total_units": 150}
        )

        # 3. Create PreSelectedUnits
        units_data = [
            {
                "national_id": "0012345678",
                "full_name": "علیرضا رضایی پور",
                "father_name": "محمدرضا",
                "birth_date": "1365/04/15",
                "spouse_full_name": "فاطمه السادات موسوی",
                "spouse_national_id": "0029876543",
                "decile": 4,
                "site": sites["شهید رئیسی"],
                "project": p1,
                "construction_type": "آپارتمانی",
                "block_name": "بلوک B-14",
                "floor_number": 3,
                "unit_number": 12,
                "unit_area": 85.50,
                "storage_number": 12,
                "storage_area": 3.20,
                "parking_number": 12,
                "parking_area": 12.50,
                "base_cost_without_loan": 4500000000,
                "registration_section": "بخش ۱ ثبتی قم",
                "main_plaque": 1420,
                "separated_plaque": 85,
                "sub_plaque": 312,
                "plot_number": 48
            },
            {
                "national_id": "0098765432",
                "full_name": "زهرا سادات حسینی",
                "father_name": "سید احمد",
                "birth_date": "1370/08/22",
                "spouse_full_name": "محمدعلی میرزایی",
                "spouse_national_id": "0044558877",
                "decile": 2,
                "site": sites["پرنیان"],
                "project": p2,
                "construction_type": "ویلایی",
                "block_name": "قطعه A-04",
                "floor_number": 1,
                "unit_number": 4,
                "unit_area": 110.00,
                "storage_number": 4,
                "storage_area": 5.00,
                "parking_number": 4,
                "parking_area": 15.00,
                "base_cost_without_loan": 5200000000,
                "registration_section": "بخش ۴ ثبتی",
                "main_plaque": 890,
                "separated_plaque": 12,
                "sub_plaque": 45,
                "plot_number": 104
            }
        ]

        for u in units_data:
            PreSelectedUnit.objects.update_or_create(national_id=u["national_id"], defaults=u)

        # 4. Create Sample Dossiers across 24 stages
        dossiers_spec = [
            {
                "archive_number": 100001,
                "national_id": "0012345678",
                "full_name": "علیرضا رضایی پور",
                "father_name": "محمدرضا",
                "birth_date": "1365/04/15",
                "spouse_full_name": "فاطمه السادات موسوی",
                "spouse_national_id": "0029876543",
                "decile": 4,
                "site": "شهید رئیسی",
                "project": "پروژه ۵۶۰ هکتاری فاز ۲ (۳۲۰ واحدی)",
                "construction_type": "آپارتمانی",
                "block_name": "بلوک B-14",
                "floor_number": 3,
                "unit_number": 12,
                "unit_area": 85.50,
                "storage_number": 12,
                "storage_area": 3.20,
                "parking_number": 12,
                "parking_area": 12.50,
                "base_cost_without_loan": 4500000000,
                "fund_loan_amount": 500000000,
                "decile_loan_amount": 1000000000,
                "applicant_equity": 3000000000,
                "registration_section": "بخش ۱ ثبتی قم",
                "main_plaque": 1420,
                "separated_plaque": 85,
                "sub_plaque": 312,
                "plot_number": 48,
                "current_stage": 1, # Stage 1
                "is_locked": False,
            },
            {
                "archive_number": 100002,
                "national_id": "0098765432",
                "full_name": "زهرا سادات حسینی",
                "father_name": "سید احمد",
                "birth_date": "1370/08/22",
                "spouse_full_name": "محمدعلی میرزایی",
                "spouse_national_id": "0044558877",
                "decile": 2,
                "site": "پرنیان",
                "project": "پروژه ویلایی پرنیان فاز ۱ (۱۵۰ واحدی)",
                "construction_type": "ویلایی",
                "block_name": "قطعه A-04",
                "floor_number": 1,
                "unit_number": 4,
                "unit_area": 110.00,
                "storage_number": 4,
                "storage_area": 5.00,
                "parking_number": 4,
                "parking_area": 15.00,
                "base_cost_without_loan": 5200000000,
                "registration_section": "بخش ۴ ثبتی",
                "main_plaque": 890,
                "separated_plaque": 12,
                "sub_plaque": 45,
                "plot_number": 104,
                "current_stage": 9, # Stage 9: SMS & Equity Determination
                "is_locked": False,
            },
            {
                "archive_number": 100003,
                "national_id": "0044556677",
                "full_name": "محمد کریمی دستجردی",
                "father_name": "حسین",
                "birth_date": "1360/02/10",
                "spouse_full_name": "مریم رضوان پور",
                "spouse_national_id": "0055667788",
                "decile": 5,
                "site": "شهید رئیسی",
                "project": "پروژه ۵۶۰ هکتاری فاز ۲ (۳۲۰ واحدی)",
                "construction_type": "آپارتمانی",
                "block_name": "بلوک C-08",
                "floor_number": 4,
                "unit_number": 16,
                "unit_area": 88.00,
                "storage_number": 16,
                "storage_area": 3.50,
                "parking_number": 16,
                "parking_area": 12.50,
                "base_cost_without_loan": 4800000000,
                "fund_loan_amount": 500000000,
                "decile_loan_amount": 1000000000,
                "applicant_equity": 3300000000,
                "bank_letter_number": "1403/BM/88412",
                "bank_letter_date": "1403/05/18",
                "current_stage": 12, # Stage 12: Scanning installment booklet
                "is_locked": False,
            },
            {
                "archive_number": 100004,
                "national_id": "0077889900",
                "full_name": "سهراب نادری دهکردی",
                "father_name": "اسفندیار",
                "birth_date": "1358/11/30",
                "spouse_full_name": "پروانه شیرازی",
                "spouse_national_id": "0088991122",
                "decile": 3,
                "site": "شهید رئیسی",
                "project": "پروژه ۵۶۰ هکتاری فاز ۲ (۳۲۰ واحدی)",
                "construction_type": "آپارتمانی",
                "block_name": "بلوک A-01",
                "floor_number": 2,
                "unit_number": 6,
                "unit_area": 86.00,
                "base_cost_without_loan": 4600000000,
                "decile_loan_amount": 1800000000,
                "applicant_equity": 2800000000,
                "cash_preparation_amount": 140000000,
                "non_cash_preparation_amount": 200000000,
                "is_cash_rent_confirmed": True,
                "is_decile_loan_confirmed": True,
                "current_stage": 23, # Stage 23: Notary Letter Print
                "is_locked": False,
            },
            {
                "archive_number": 100005,
                "national_id": "0033221144",
                "full_name": "فرشید بهرامیان",
                "father_name": "غلامعلی",
                "birth_date": "1362/06/19",
                "spouse_full_name": "لیلا مرادی",
                "spouse_national_id": "0099887766",
                "decile": 6,
                "site": "قنوات",
                "project": "پروژه ویلایی قنوات",
                "construction_type": "ویلایی",
                "block_name": "قطعه B-12",
                "floor_number": 1,
                "unit_number": 1,
                "unit_area": 120.00,
                "base_cost_without_loan": 5500000000,
                "applicant_equity": 5500000000,
                "current_stage": 24, # Stage 24: Final Archive
                "is_locked": True,
            }
        ]

        for d in dossiers_spec:
            dossier_obj, _ = HousingDossier.objects.update_or_create(
                archive_number=d["archive_number"],
                defaults=d
            )

            # Rich Document Scans
            DossierAttachment.objects.update_or_create(
                dossier=dossier_obj,
                stage=1,
                doc_type="NATIONAL_ID",
                defaults={
                    "title": "اسکن کارت ملی هوشمند متقاضی",
                    "file_name": f"national_id_{dossier_obj.national_id}.jpg",
                    "file_sha256": "9f83c12a76f24d8b9e1a3c5e",
                    "uploaded_by": "احمد صادقی (کارشناس ثبت کارگزاری)"
                }
            )

            DossierAttachment.objects.update_or_create(
                dossier=dossier_obj,
                stage=1,
                doc_type="SPOUSE_ID",
                defaults={
                    "title": "اسکن مدارک هویتی همسر متقاضی",
                    "file_name": f"spouse_id_{dossier_obj.spouse_national_id}.jpg",
                    "file_sha256": "4e91c7810aa4921f7b8c2d1e",
                    "uploaded_by": "احمد صادقی (کارشناس ثبت کارگزاری)"
                }
            )

            DossierAttachment.objects.update_or_create(
                dossier=dossier_obj,
                stage=1,
                doc_type="UNIT_SELECTION",
                defaults={
                    "title": "برگه انتخاب واحد تاییدشده کارگزاری",
                    "file_name": f"unit_selection_{dossier_obj.archive_number}.pdf",
                    "file_sha256": "e3b0c44298fc3e8b8c2d1e9f",
                    "uploaded_by": "احمد صادقی (کارشناس ثبت کارگزاری)"
                }
            )

            DossierAttachment.objects.update_or_create(
                dossier=dossier_obj,
                stage=12,
                doc_type="BANK_BOOKLET",
                defaults={
                    "title": "اسکن دفترچه اقساط تسهیلات بانک مسکن",
                    "file_name": "bank_installment_booklet.pdf",
                    "file_sha256": "c2b6f12019ab991a8f7e6d5c",
                    "uploaded_by": "مهدی نوری (کارشناس اسکن کارگزاری)"
                }
            )

            DossierAttachment.objects.update_or_create(
                dossier=dossier_obj,
                stage=16,
                doc_type="TITLE_DEED",
                defaults={
                    "title": "اسکن سند مالکیت تک‌برگ کاداستری",
                    "file_name": "title_deed_cadastral.pdf",
                    "file_sha256": "7f83b1657ff148a21b3c5e7a",
                    "uploaded_by": "حمید حسینی (کارشناس املاک اداره کل)"
                }
            )

            DossierAttachment.objects.update_or_create(
                dossier=dossier_obj,
                stage=20,
                doc_type="LOAN_CHECK",
                defaults={
                    "title": "اسکن چک صیادی تسهیلات دهک درآمدی",
                    "file_name": "sayad_check_decile.jpg",
                    "file_sha256": "109fa883cb0174aa541098ef",
                    "uploaded_by": "حسین رستمی (کارشناس وصول کارگزاری)"
                }
            )

            # Initial Audit Log
            WorkflowSignatureLog.objects.get_or_create(
                dossier=dossier_obj,
                from_stage="ورود اطلاعات",
                to_stage="مرحله ۱: ورود اطلاعات متقاضی، همسر، واحد و پروژه",
                action="SUBMIT",
                defaults={
                    "actor": "احمد صادقی",
                    "role": "کارشناس ثبت درخواست کارگزاری",
                    "action_label": "ثبت اولیه پرونده",
                    "signature_hash": "SHA256: 7f83b1657ff1...48a2",
                    "notes": "پرونده بر اساس اطلاعات انتخاب واحد با موفقیت در سامانه سندبان ثبت گردید."
                }
            )

        self.stdout.write(self.style.SUCCESS("Database seeded with 24 stages and rich visual scan attachments!"))
