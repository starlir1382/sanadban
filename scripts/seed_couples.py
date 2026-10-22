import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
import openpyxl

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workflow.models import Site, Project, PreSelectedUnit, HousingDossier

excel_path = r'C:\Users\AlirezaRezaei\.gemini\antigravity\brain\44dd39cf-ce14-44e6-91e9-5dbe5cc7373c\.user_uploaded\media_1792653262870_e86ad704.xlsx'
wb = openpyxl.load_workbook(excel_path)
sheet = wb.active

archive_start = 100001

for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=1):
    nat_id = str(row[3]).strip().zfill(10)
    first_name = str(row[1] or '').strip()
    last_name = str(row[2] or '').strip()
    full_name = f"{first_name} {last_name}".strip()
    father_name = str(row[49] or '').strip()
    birth_date = str(row[51] or '').strip()
    
    spouse_fn = str(row[56] or '').strip()
    spouse_ln = str(row[57] or '').strip()
    spouse_full_name = f"{spouse_fn} {spouse_ln}".strip()
    spouse_father_name = str(row[58] or '').strip()
    spouse_id_number = str(row[59] or '').strip()
    spouse_nat_id = str(row[60] or '').strip().zfill(10) if row[60] else ''
    spouse_birth_date = str(row[61] or '').strip()
    spouse_birth_place = str(row[62] or '').strip()
    
    proj_name = str(row[13] or 'پروژه ۵۶۰ هکتاری').strip()
    city = str(row[10] or 'قم').strip()
    site_name = 'جعفریه' if 'جعفریه' in proj_name or 'جعفریه' in city else 'شهید رئیسی'
    decile_val = int(row[23]) if row[23] and str(row[23]).isdigit() else (idx + 1)
    
    site_obj, _ = Site.objects.get_or_create(name=site_name)
    proj_obj, _ = Project.objects.get_or_create(site=site_obj, name=proj_name, defaults={'total_units': 320})
    
    # 1. Update/Create PreSelectedUnit for Stage 1 lookup
    unit_obj, _ = PreSelectedUnit.objects.update_or_create(
        national_id=nat_id,
        defaults={
            'full_name': full_name,
            'father_name': father_name,
            'birth_date': birth_date,
            'spouse_full_name': spouse_full_name,
            'spouse_father_name': spouse_father_name,
            'spouse_national_id': spouse_nat_id,
            'spouse_birth_date': spouse_birth_date,
            'spouse_id_number': spouse_id_number,
            'spouse_birth_place': spouse_birth_place,
            'spouse_form_j_status': 'سبز (استعلام شده)',
            'marital_status': 'متاهل (واجد شرایط طرح زوجین)',
            'is_married_confirmed': True,
            'decile': decile_val,
            'site': site_obj,
            'project': proj_obj,
            'construction_type': 'آپارتمانی',
            'block_name': f'بلوک {chr(64 + idx)}',
            'floor_number': (idx % 4) + 1,
            'unit_number': idx * 4,
            'unit_area': 85.50,
            'storage_number': idx * 4,
            'storage_area': 3.50,
            'parking_number': idx * 4,
            'parking_area': 12.50,
            'base_cost_without_loan': 4500000000,
            'registration_section': 'بخش ۱ ثبتی قم',
            'main_plaque': 1400 + idx,
            'separated_plaque': 50 + idx,
            'sub_plaque': 200 + idx,
            'plot_number': 30 + idx
        }
    )
    
    # 2. Update/Create HousingDossier for existing dossier view and workflow
    arch_no = archive_start + idx - 1
    # Check if a dossier with this national_id exists
    dossier = HousingDossier.objects.filter(national_id=nat_id).first()
    if not dossier:
        dossier = HousingDossier.objects.filter(archive_number=arch_no).first()
        
    if not dossier:
        dossier = HousingDossier(archive_number=arch_no, national_id=nat_id)
        
    dossier.national_id = nat_id
    dossier.archive_number = arch_no
    dossier.full_name = full_name
    dossier.father_name = father_name
    dossier.birth_date = birth_date
    dossier.spouse_full_name = spouse_full_name
    dossier.spouse_father_name = spouse_father_name
    dossier.spouse_national_id = spouse_nat_id
    dossier.spouse_birth_date = spouse_birth_date
    dossier.spouse_id_number = spouse_id_number
    dossier.spouse_birth_place = spouse_birth_place
    dossier.spouse_form_j_status = 'سبز (استعلام شده)'
    dossier.marital_status = 'متاهل (واجد شرایط طرح زوجین)'
    dossier.is_married_confirmed = True
    dossier.decile = decile_val
    dossier.site = site_name
    dossier.project = proj_name
    dossier.construction_type = 'آپارتمانی'
    dossier.block_name = f'بلوک {chr(64 + idx)}'
    dossier.floor_number = (idx % 4) + 1
    dossier.unit_number = idx * 4
    dossier.unit_area = 85.50
    dossier.storage_number = idx * 4
    dossier.storage_area = 3.50
    dossier.parking_number = idx * 4
    dossier.parking_area = 12.50
    dossier.registration_section = 'بخش ۱ ثبتی قم'
    dossier.main_plaque = 1400 + idx
    dossier.separated_plaque = 50 + idx
    dossier.sub_plaque = 200 + idx
    dossier.plot_number = 30 + idx
    dossier.base_cost_without_loan = 4500000000
    dossier.fund_loan_amount = 500000000
    dossier.decile_loan_amount = 1000000000 if decile_val <= 4 else 0
    dossier.save()
    
    print(f"[{idx}] Dossier #{dossier.archive_number}: {dossier.full_name} & {dossier.spouse_full_name} (Spouse NatID: {dossier.spouse_national_id}, Father: {dossier.spouse_father_name}) saved successfully.")

print("All real couples from Excel seeded successfully!")
