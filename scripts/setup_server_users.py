import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from workflow.models import UserProfile
from workflow.stages import STAGE_ROLES

DEFAULT_PASSWORD = "ztk123456"

# Definition of all users per stage as requested
USERS_SPEC = [
    # مرحله ۱
    {
        "username": "rah_azaram1",
        "full_name": "ره آزرم ۱",
        "stage": 1,
        "stages": "1",
        "role_title": "کارشناس ثبت اطلاعات متقاضی و واحد انتخابی",
        "organization": "brokerage",
    },
    # مرحله ۲
    {
        "username": "rah_azaram2",
        "full_name": "ره آزرم ۲",
        "stage": 2,
        "stages": "2",
        "role_title": "کارشناس اطلاعات ثبتی و قیمت تمام‌شده",
        "organization": "brokerage",
    },
    # مرحله ۳
    {
        "username": "vahid_alemi",
        "full_name": "وحید عالمی",
        "stage": 3,
        "stages": "3",
        "role_title": "کارشناس بررسی فرم جیم (عالمی)",
        "organization": "directorate",
    },
    {
        "username": "mohammad_mohammadian",
        "full_name": "محمد محمدیان",
        "stage": 3,
        "stages": "3",
        "role_title": "کارشناس بررسی فرم جیم (محمدیان)",
        "organization": "directorate",
    },
    # مرحله ۴
    {
        "username": "sajjad_heydari",
        "full_name": "سجاد حیدری",
        "stage": 4,
        "stages": "4",
        "role_title": "کارشناس برنامه‌ریزی مسکن (تسهیلات و برآورد)",
        "organization": "directorate",
    },
    # مرحله ۵
    {
        "username": "zahra_behmaram",
        "full_name": "زهرا به مرام",
        "stage": 5,
        "stages": "5",
        "role_title": "کارشناس برنامه‌ریزی مسکن (اطلاع‌رسانی آورده)",
        "organization": "directorate",
    },
    # مرحله ۶
    {
        "username": "melika_vesali",
        "full_name": "ملیکا وصالی",
        "stage": 6,
        "stages": "6",
        "role_title": "کارشناس برنامه‌ریزی مسکن (معرفی به بانک)",
        "organization": "directorate",
    },
    # مرحله ۷
    {
        "username": "rah_azaram3",
        "full_name": "ره آزرم ۳",
        "stage": 7,
        "stages": "7",
        "role_title": "کارشناس تشکیل پرونده کارگزاری و اسکن مدارک",
        "organization": "brokerage",
    },
    # مرحله ۸
    {
        "username": "mojtaba_delavari",
        "full_name": "مجتبی دلاوری",
        "stage": 8,
        "stages": "8",
        "role_title": "مدیرعامل کارگزاری مسکن",
        "organization": "brokerage",
    },
    # مرحله ۹
    {
        "username": "masoumeh_jamshidi",
        "full_name": "معصومه جمشیدی",
        "stage": 9,
        "stages": "9",
        "role_title": "کارشناس نهضت ملی مسکن و استعلام تسهیلات",
        "organization": "directorate",
    },
    {
        "username": "hadiseh_forouzani",
        "full_name": "حدیثه فروزانی",
        "stage": 9,
        "stages": "9",
        "role_title": "کارشناس نهضت ملی مسکن و استعلام تسهیلات",
        "organization": "directorate",
    },
    # مرحله ۱۰
    {
        "username": "tahereh_soltani",
        "full_name": "طاهره سلطانی",
        "stage": 10,
        "stages": "10",
        "role_title": "کارشناس بررسی و ثبت فرم ج اداره کل",
        "organization": "directorate",
    },
    # مرحله ۱۱
    {
        "username": "yahya_pashazadeh",
        "full_name": "یحیی پاشا زاده",
        "stage": 11,
        "stages": "11",
        "role_title": "کارشناس فنی و مهندسی",
        "organization": "directorate",
    },
    {
        "username": "abolghasem_chehraghani",
        "full_name": "ابولقاسم چهرقانی",
        "stage": 11,
        "stages": "11",
        "role_title": "کارشناس فنی و مهندسی",
        "organization": "directorate",
    },
    {
        "username": "hamed_rezaei",
        "full_name": "حامد رضایی",
        "stage": 11,
        "stages": "11",
        "role_title": "کارشناس فنی و مهندسی",
        "organization": "directorate",
    },
    # مرحله ۱۲
    {
        "username": "davood_zare",
        "full_name": "داوود زارع",
        "stage": 12,
        "stages": "12",
        "role_title": "کارشناس املاک اداره کل (بارگذاری سند عرصه)",
        "organization": "directorate",
    },
    # مرحله ۱۳
    {
        "username": "mohammadjavad_haghi",
        "full_name": "محمد جواد حقی",
        "stage": 13,
        "stages": "13",
        "role_title": "کارشناس بانک زمین اداره کل",
        "organization": "directorate",
    },
    # مرحله ۱۴
    {
        "username": "zeinab_motahariniya",
        "full_name": "زینب مطهری نیا",
        "stage": 14,
        "stages": "14",
        "role_title": "کارشناس حقوقی اداره کل",
        "organization": "directorate",
    },
    # مرحله ۱۵
    {
        "username": "fatemeh_seyedebrahimi",
        "full_name": "فاطمه سادات سید ابراهیمی",
        "stage": 15,
        "stages": "15",
        "role_title": "کارشناس ارزیابی قدرالسهم و اجاره",
        "organization": "directorate",
    },
    {
        "username": "hossein_aliaskari",
        "full_name": "حسین علی عسکری",
        "stage": 15,
        "stages": "15",
        "role_title": "کارشناس ارزیابی قدرالسهم و اجاره",
        "organization": "directorate",
    },
    # مرحله ۱۶ و ۱۷ (ztk1)
    {
        "username": "ztk1",
        "full_name": "کارشناس دریافت و کنترل چک‌ها (ztk1)",
        "stage": 16,
        "stages": "16,17",
        "role_title": "متصدی دریافت چک‌های وام دهک، اقساط آماده‌سازی و اجاره",
        "organization": "brokerage",
        "is_check_admin": True,
    },
    # مرحله ۱۸ و ۳ مدیر سامانه (Admins)
    {
        "username": "hamid_jafariani",
        "full_name": "حمید جعفریانی (مدیر سامانه)",
        "stage": 18,
        "stages": "all",
        "role_title": "مدیر ارشد سامانه (رئیس مسکن)",
        "organization": "system",
        "is_superuser": True,
        "is_staff": True,
        "is_housing_chief": True,
    },
    {
        "username": "seyedi",
        "full_name": "سیدی (مدیر سامانه)",
        "stage": 18,
        "stages": "all",
        "role_title": "مدیر ارشد سامانه (رئیس مسکن)",
        "organization": "system",
        "is_superuser": True,
        "is_staff": True,
        "is_housing_chief": True,
    },
    {
        "username": "alireza_nazari",
        "full_name": "علیرضا نظری",
        "stage": 18,
        "stages": "all",
        "role_title": "مدیر سامانه / کارشناس تسویه با پیمانکار",
        "organization": "system",
        "is_superuser": True,
        "is_staff": True,
        "is_housing_chief": True,
    },
    # مدیر کل سیستم پیش‌فرض
    {
        "username": "admin",
        "full_name": "مدیر کل سیستم (Admin)",
        "stage": 18,
        "stages": "all",
        "role_title": "مدیر کل سامانه",
        "organization": "system",
        "is_superuser": True,
        "is_staff": True,
        "is_housing_chief": True,
        "must_change_password": False,
    },
    # مرحله ۱۹
    {
        "username": "ali_hesabi",
        "full_name": "علی حسابی",
        "stage": 19,
        "stages": "19",
        "role_title": "کارشناس صدور نامه محضر اداره کل",
        "organization": "directorate",
    },
    {
        "username": "mobina_khazeni",
        "full_name": "مبینا خازنی",
        "stage": 19,
        "stages": "19",
        "role_title": "کارشناس صدور نامه محضر اداره کل",
        "organization": "directorate",
    },
    # مرحله ۲۰
    {
        "username": "rah_azaram4",
        "full_name": "ره آزرم ۴",
        "stage": 20,
        "stages": "20",
        "role_title": "کارشناس قرارداد اجاره و چاپ فرم‌ها",
        "organization": "directorate",
    },
    # مرحله ۲۱
    {
        "username": "mahmoud_jahanbakhsh",
        "full_name": "محمود جهانبخش",
        "stage": 21,
        "stages": "21",
        "role_title": "کارشناس بایگانی نهایی اداره کل",
        "organization": "directorate",
    },
]


def run_setup():
    print("[1/3] Deleting all existing users and profiles...")
    deleted_count, _ = User.objects.all().delete()
    print(f"      Successfully removed {deleted_count} user-related objects.")

    print("\n[2/3] Creating clean users for all 21 stages with password 'ztk123456'...")
    created_users = []

    for idx, spec in enumerate(USERS_SPEC, 1):
        username = spec["username"]
        is_su = spec.get("is_superuser", False)
        is_staff = spec.get("is_staff", is_su)

        user = User(
            username=username,
            is_superuser=is_su,
            is_staff=is_staff,
            is_active=True
        )
        user.set_password(DEFAULT_PASSWORD)
        user.save()

        # Update or create the profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.full_name = spec["full_name"]
        profile.role_title = spec["role_title"]
        profile.organization = spec.get("organization", "brokerage")
        profile.allowed_stages = spec.get("stages", str(spec.get("stage", "1")))
        profile.is_housing_chief = spec.get("is_housing_chief", False)
        profile.is_check_admin = spec.get("is_check_admin", False)
        profile.must_change_password = spec.get("must_change_password", True)
        profile.can_sign = True
        profile.is_active_expert = True
        profile.save()

        created_users.append((user.username, profile.full_name, profile.allowed_stages, is_su))
        role_type = " [ADMIN/SUPERUSER]" if is_su else ""
        print(f"      {idx:02d}. {user.username:<24} | {profile.full_name:<30} | مراحل: {profile.allowed_stages:<6}{role_type}")

    print(f"\n[3/3] User setup complete! Total {len(created_users)} users created.")
    print(f"      All users can log in with password: {DEFAULT_PASSWORD}")
    return created_users


if __name__ == "__main__":
    run_setup()
