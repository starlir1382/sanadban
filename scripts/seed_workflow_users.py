import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from workflow.models import UserProfile, HousingDossier

USERS_DATA = [
    {
        "username": "housing_chief",
        "password": "chief1234",
        "full_name": "دکتر محمدرضا مسعودی",
        "role_title": "رئیس مسکن و شهرسازی (دسترسی تام)",
        "organization": "directorate",
        "personnel_code": "CHIEF-01",
        "phone_number": "09121000001",
        "is_housing_chief": True,
        "is_staff": True,
        "is_superuser": False,
        "allowed_stages": "all",
    },
    {
        "username": "admin",
        "password": "admin1234",
        "full_name": "مهندس علیرضا رضایی پور",
        "role_title": "مدیر ارشد سامانه و امنیت",
        "organization": "system",
        "personnel_code": "SYS-001",
        "phone_number": "09120000000",
        "is_housing_chief": True,
        "is_staff": True,
        "is_superuser": True,
        "allowed_stages": "all",
    },
    {
        "username": "broker_info",
        "password": "broker1234",
        "full_name": "احمد صادقی",
        "role_title": "کارشناس ثبت اطلاعات و پلاک ثبتی کارگزاری",
        "organization": "brokerage",
        "personnel_code": "BRK-101",
        "phone_number": "09122000101",
        "allowed_stages": "0,1,2",
    },
    {
        "username": "alemi",
        "password": "alemi1234",
        "full_name": "دکتر جواد عالمی",
        "role_title": "کارشناس بررسی فرم ج (عالمی)",
        "organization": "directorate",
        "personnel_code": "DIR-301",
        "phone_number": "09123000301",
        "allowed_stages": "3,16",
    },
    {
        "username": "heydari",
        "password": "heydari1234",
        "full_name": "مهندس سعید حیدری",
        "role_title": "کارشناس برنامه ریزی مسکن (حیدری)",
        "organization": "directorate",
        "personnel_code": "DIR-401",
        "phone_number": "09124000401",
        "allowed_stages": "4,5,6,8",
    },
    {
        "username": "vesali",
        "password": "vesali1234",
        "full_name": "مهندس فرهاد وصالی",
        "role_title": "کارشناس برنامه ریزی مسکن (وصالی)",
        "organization": "directorate",
        "personnel_code": "DIR-701",
        "phone_number": "09127000701",
        "allowed_stages": "7,8",
    },
    {
        "username": "broker_dossier",
        "password": "broker1234",
        "full_name": "خانم نرگس داوودی",
        "role_title": "کارشناس تشکیل پرونده و اسکن مدارک اقساط",
        "organization": "brokerage",
        "personnel_code": "BRK-901",
        "phone_number": "09129000901",
        "allowed_stages": "9",
    },
    {
        "username": "broker_manager",
        "password": "broker1234",
        "full_name": "مهندس محمد تقوی",
        "role_title": "مدیرعامل کارگزاری مسکن",
        "organization": "brokerage",
        "personnel_code": "BRK-100",
        "phone_number": "09121000100",
        "allowed_stages": "0,1,2,9,10",
    },
    {
        "username": "bank_inquiry_expert",
        "password": "bank1234",
        "full_name": "مهندس کاوه رضایی",
        "role_title": "کارشناس نهضت ملی مسکن و تسهیلات بانکی",
        "organization": "directorate",
        "personnel_code": "DIR-110",
        "phone_number": "09121100110",
        "allowed_stages": "11",
    },
    {
        "username": "technical_expert",
        "password": "tech1234",
        "full_name": "مهندس مسعود کریمی",
        "role_title": "کارشناس فنی و مهندسی اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-120",
        "phone_number": "09121200120",
        "allowed_stages": "12",
    },
    {
        "username": "realestate_expert",
        "password": "melk1234",
        "full_name": "مهندس مریم حسینی",
        "role_title": "کارشناس املاک اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-130",
        "phone_number": "09121300130",
        "allowed_stages": "13",
    },
    {
        "username": "land_bank_expert",
        "password": "zamin1234",
        "full_name": "مهندس رضا یوسفی",
        "role_title": "کارشناس بانک زمین اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-140",
        "phone_number": "09121400140",
        "allowed_stages": "14",
    },
    {
        "username": "legal_expert",
        "password": "legal1234",
        "full_name": "دکتر علی موسوی",
        "role_title": "کارشناس حقوقی اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-150",
        "phone_number": "09121500150",
        "allowed_stages": "15",
    },
    {
        "username": "form_j_expert",
        "password": "form1234",
        "full_name": "خانم الهام کاظمی",
        "role_title": "کارشناس فرم ج اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-160",
        "phone_number": "09121600160",
        "allowed_stages": "16",
    },
    {
        "username": "evaluation_expert",
        "password": "arzyabi1234",
        "full_name": "مهندس کیان پیشرو",
        "role_title": "کارشناس ارزیابی قدرالسهم و اجاره اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-170",
        "phone_number": "09121700170",
        "allowed_stages": "17",
    },
    {
        "username": "rent_prep_expert",
        "password": "ejareh1234",
        "full_name": "مرتضی نجفی",
        "role_title": "کارشناس اخذ اجاره، آماده سازی و تسهیلات دهک",
        "organization": "brokerage",
        "personnel_code": "BRK-180",
        "phone_number": "09121800180",
        "allowed_stages": "18",
    },
    {
        "username": "contractor_settle_expert",
        "password": "settle1234",
        "full_name": "مهندس بهزاد نوری",
        "role_title": "کارشناس تسویه با پیمانکار اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-190",
        "phone_number": "09121900190",
        "allowed_stages": "19",
    },
    {
        "username": "notary_letter_expert",
        "password": "mahzar1234",
        "full_name": "خانم آرزو باقری",
        "role_title": "کارشناس صدور نامه محضر اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-200",
        "phone_number": "09122000200",
        "allowed_stages": "20",
    },
    {
        "username": "archivist",
        "password": "archive1234",
        "full_name": "مجید مرادی",
        "role_title": "کارشناس بایگانی اداره کل",
        "organization": "directorate",
        "personnel_code": "DIR-210",
        "phone_number": "09122100210",
        "allowed_stages": "21",
    },
]

print("Seeding Enterprise Users...")
for udata in USERS_DATA:
    username = udata["username"]
    user, created = User.objects.get_or_create(username=username)
    user.set_password(udata["password"])
    user.is_staff = udata.get("is_staff", False)
    user.is_superuser = udata.get("is_superuser", False)
    user.is_active = True
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.full_name = udata["full_name"]
    profile.role_title = udata["role_title"]
    profile.organization = udata["organization"]
    profile.personnel_code = udata["personnel_code"]
    profile.phone_number = udata["phone_number"]
    profile.is_housing_chief = udata.get("is_housing_chief", False)
    profile.allowed_stages = udata.get("allowed_stages", "all")
    profile.can_sign = True
    profile.is_active_expert = True
    profile.save()

    chief_note = " *** REIS MASKAN (FULL AUTH) ***" if profile.is_housing_chief else ""
    print(f" [+] User '{username}' ready: {profile.full_name} ({profile.role_title}) [Stages: {profile.allowed_stages}]{chief_note}")

# Make sure existing dossiers are set to valid stages within 0-21
for d in HousingDossier.objects.all():
    if d.current_stage > 21:
        d.current_stage = 21
        d.save()

print("\nAll enterprise users seeded successfully!")
