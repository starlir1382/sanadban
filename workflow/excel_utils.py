"""
workflow/excel_utils.py
Enterprise Bulk Excel Engine for MaskanYar Housing Dossiers.
Rebuilt from scratch per architectural specification.
Handles 35,000+ rows, write-only streaming, chunked DB operations,
previews, atomic writes, couple validation, commission access control,
group signing, spouse swapping, and secure per-user failure reports.
"""

import os
import io
import re
import time
import uuid
import tempfile
import hashlib
import itertools
import jdatetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from django.conf import settings
from django.db import transaction, IntegrityError, models
from django.db.models import Case, When, Value, Q
from django.http import HttpResponse, Http404, FileResponse
from django.utils import timezone

from .models import (
    HousingDossier,
    WorkflowSignatureLog,
    DossierFieldChangeLog,
    DossierSignature,
    DossierAttachment,
    ProjectBankMapping,
    UserProfile,
)
from .stages import STAGE_TO_SLOTS, TOTAL_STAGES, MAX_STAGE

# -------------------------------------------------------------------------
# Architectural Constants
# -------------------------------------------------------------------------
CHECK_COUPLE_CONFLICT = True
SWAP_ATTACHMENT_DOC_TYPES = True
CHUNK_QUERY_SIZE = 500
CHUNK_WRITE_SIZE = 1000
GROUP_SIGN_MAX_ROWS = 2000
REPORT_RETENTION_SECONDS = 6 * 3600  # 6 hours

# Module-level export cache and lock for generate_dossiers_export
import threading
_export_lock = threading.Lock()
_export_cache: Dict[str, Tuple[str, float, int]] = {}

# -------------------------------------------------------------------------
# Single Import Header Spec (Headers -> Model Field, Type)
# No duplicate headers, no lambda display rows, includes commission cols
# -------------------------------------------------------------------------
TEMPLATE_FIELD_SPECS = [
    # Required Primary Key Identifier
    ("کد ملی متقاضی", "national_id", "national_id"),

    # Personal & Demographic Information
    ("نام متقاضی", "first_name", "str"),
    ("نام خانوادگی متقاضی", "last_name", "str"),
    ("نام و نام خانوادگی متقاضی", "full_name", "str"),
    ("نام پدر", "father_name", "str"),
    ("تاریخ تولد متقاضی (شمسی)", "birth_date", "str"),
    ("شماره شناسنامه متقاضی", "applicant_id_number", "str"),
    ("محل صدور متقاضی", "applicant_birth_place", "str"),
    ("شماره همراه متقاضی", "applicant_phone", "str"),
    ("وضعیت تاهل", "marital_status", "str"),
    ("تاییدیه تاهل", "is_married_confirmed", "bool"),
    ("دهک درآمدی (۱ تا ۱۰)", "decile", "int"),

    # Spouse Information
    ("نام همسر", "spouse_first_name", "str"),
    ("نام خانوادگی همسر", "spouse_last_name", "str"),
    ("نام و نام خانوادگی همسر", "spouse_full_name", "str"),
    ("نام پدر همسر", "spouse_father_name", "str"),
    ("کد ملی همسر", "spouse_national_id", "national_id"),
    ("تاریخ تولد همسر (شمسی)", "spouse_birth_date", "str"),
    ("شماره شناسنامه همسر", "spouse_id_number", "str"),
    ("محل صدور همسر", "spouse_birth_place", "str"),

    # Unit Selection & Project Details
    ("نام سایت مسکونی", "site", "str"),
    ("نام پروژه مسکونی", "project", "str"),
    ("کد پروژه مسکونی", "project_code", "str"),
    ("شماره بلوک", "block_number", "str"),
    ("شماره طبقه", "floor_number", "str"),
    ("شماره واحد", "unit_number", "str"),
    ("رتبه انتخابی متقاضی", "selection_rank", "int"),
    ("نام بانک عامل", "bank_name", "str"),
    ("شعبه بانک عامل", "bank_branch", "str"),

    # Registration & Plaque Specifications
    ("بخش ثبتی", "registration_section", "str"),
    ("پلاک اصلی", "main_plaque", "int"),
    ("پلاک مفروز", "separated_plaque", "int"),
    ("پلاک فرعی", "sub_plaque", "int"),
    ("فرعی / مفروز ومجزا / اصلی", "composite_plaques", "composite_plaques"),
    ("شماره قطعه", "plot_number", "int"),
    ("کد نوسازی", "renovation_code", "str"),
    ("مساحت مفید واحد (مترمربع)", "unit_area", "decimal"),
    ("مساحت تراس / بالکن (مترمربع)", "balcony_area", "decimal"),
    ("مساحت انباری (مترمربع)", "storage_area", "decimal"),
    ("مساحت کل عرصه پروژه (مترمربع)", "total_land_area", "decimal"),
    ("سهم‌العرصه واحد مسکونی (مترمربع)", "total_land_share", "decimal"),
    ("قیمت کارشناسی عرصه (ریال)", "land_expert_price", "price"),
    ("تاییدیه سند عرصه", "is_land_deed_confirmed", "bool"),

    # Form J Statuses
    ("شماره فرم ج", "form_j_number", "str"),
    ("شماره پرسش‌نامه فرم ج", "form_j_questionnaire_number", "str"),
    ("صفحه فرم ج", "form_j_page", "str"),
    ("وضعیت فرم ج متقاضی", "applicant_form_j_status", "str"),
    ("استعلام اداره کل متقاضی", "applicant_form_j_directorate_status", "str"),
    ("توضیحات فرم ج متقاضی", "applicant_form_j_red_description", "str"),
    ("وضعیت فرم ج همسر", "spouse_form_j_status", "str"),
    ("استعلام اداره کل همسر", "spouse_form_j_directorate_status", "str"),
    ("توضیحات فرم ج همسر", "spouse_form_j_red_description", "str"),
    ("نحوه ثبت فرم ج", "form_j_registration_type", "str"),

    # Financials & Loans
    ("مبلغ کل قرارداد (ریال)", "total_price", "price"),
    ("قیمت پایه بدون وام (ریال)", "base_cost_without_loan", "price"),
    ("مبلغ وام بانکی (ریال)", "bank_loan_amount", "price"),
    ("سهم آورده نقدی متقاضی (ریال)", "applicant_equity", "price"),
    ("مبلغ وام صندوق ملی مسکن (ریال)", "fund_loan_amount", "price"),
    ("مبلغ کسر نامه پیمانکار (ریال)", "contractor_letter_amount", "price"),
    ("مبلغ وام دهک‌های درآمدی (ریال)", "decile_loan_amount", "price"),

    # Bank Shipment & Intro Letter
    ("تاییدیه دفترچه اقساط", "is_installment_booklet_confirmed", "bool"),
    ("افزودن به لیست محموله بانک", "is_added_to_bank_shipment_list", "bool"),
    ("شماره نامه معرفی به بانک", "bank_letter_number", "str"),
    ("تاریخ نامه معرفی به بانک (شمسی)", "bank_letter_date", "str"),
    ("معرفی شده به بانک", "is_sent_to_bank", "bool"),
    ("تاریخ ارسال به بانک (شمسی)", "bank_sent_date", "str"),
    ("شماره نامه ارسال به بانک", "bank_sent_letter_number", "str"),
    ("تاریخ ارسال پیامک آورده نقدی (شمسی)", "sms_sent_date", "str"),

    # Rent & Preparation Costs
    ("اجاره سال‌های قبل (ریال)", "past_years_rent", "price"),
    ("اجاره سال جاری (ریال)", "current_year_rent", "price"),
    ("سال اجاره عرصه", "land_lease_year", "int"),
    ("هزینه آماده‌سازی (ریال)", "preparation_cost", "price"),

    # Commission Columns (Feature 4)
    ("کارمزد خدمات چک (ریال)", "check_service_fee", "price"),
    ("کارمزد خدمات آماده‌سازی (ریال)", "preparation_service_fee", "price"),

    # Decile Checks & Receipts
    ("بانک عامل تسهیلات دهک", "decile_loan_bank", "str"),
    ("شعبه تسهیلات دهک", "decile_loan_branch", "str"),
    ("شماره حساب تسهیلات دهک", "decile_loan_account_number", "str"),
    ("ضامن تسهیلات دهک", "decile_loan_guarantor", "str"),
    ("چک صیادی وام دهک دریافت شد", "decile_loan_check_received", "bool"),
    ("تعداد چک‌های صیادی وام دهک", "decile_loan_check_count", "int"),
    ("مبلغ کل چک‌های وام دهک (ریال)", "decile_loan_check_amount", "price"),
    ("تاییدیه چک‌های وام دهک", "is_decile_loan_confirmed", "bool"),

    # Preparation & Rent Checks
    ("قیمت پذیره متقاضی (ریال)", "tenant_price", "price"),
    ("مبلغ نقد آماده‌سازی (ریال)", "preparation_cash_amount", "price"),
    ("تعداد چک‌های آماده‌سازی", "preparation_check_count", "int"),
    ("مبلغ کل چک‌های آماده‌سازی (ریال)", "preparation_check_amount", "price"),
    ("مبلغ نقد اجاره عرصه (ریال)", "land_rent_cash_amount", "price"),
    ("تعداد چک‌های اجاره عرصه", "land_rent_check_count", "int"),
    ("مبلغ کل چک‌های اجاره عرصه (ریال)", "land_rent_check_amount", "price"),
    ("تسویه اجاره انجام شد", "is_rent_settled", "bool"),
    ("تاییدیه نقد و چک‌های آماده‌سازی و اجاره", "is_preparation_checks_confirmed", "bool"),

    # Directorate Final Letters / Road & Housing & Notary
    ("شماره نامه راه و شهرسازی", "rah_letter", "str"),
    ("تاریخ نامه راه و شهرسازی (شمسی)", "rah_letter_date", "str"),
    ("شماره دفترخانه اسناد رسمی", "notary_office_number", "str"),
    ("شماره نامه معرفی به محضر", "notary_letter_number", "str"),
    ("تاریخ نامه معرفی به محضر (شمسی)", "notary_letter_date", "str"),
]

# Aliases dictionary to tolerate historical file headers
HEADER_ALIASES: Dict[str, str] = {
    "کد ملی": "national_id",
    "کدملی": "national_id",
    "کد ملی متقاضی": "national_id",
    "کدملی متقاضی": "national_id",
    "شماره ملی": "national_id",
    "شماره ملی متقاضی": "national_id",
    "شماره‌ملی": "national_id",
    "شماره‌ملی متقاضی": "national_id",
    "شناسه ملی": "national_id",
    "شناسه ملی متقاضی": "national_id",
    "شناسه‌ملی": "national_id",
    "شناسه‌ملی متقاضی": "national_id",
    "کد/شناسه ملی": "national_id",
    "کد / شناسه ملی": "national_id",
    "کد / شناسه ملی متقاضی": "national_id",
    "کدملی/شناسه ملی": "national_id",
    "نام": "first_name",
    "نام خانوادگی": "last_name",
    "نام و نام خانوادگی": "full_name",
    "نام کامل": "full_name",
    "تلفن همراه": "applicant_phone",
    "شماره همراه": "applicant_phone",
    "موبایل": "applicant_phone",
    "کد ملی همسر": "spouse_national_id",
    "کدملی همسر": "spouse_national_id",
    "شماره ملی همسر": "spouse_national_id",
    "شماره‌ملی همسر": "spouse_national_id",
    "شناسه ملی همسر": "spouse_national_id",
    "شناسه‌ملی همسر": "spouse_national_id",
    "قیمت پایه": "base_cost_without_loan",
    "قیمت پایه بدون وام": "base_cost_without_loan",
    "قیمت تمام شده بدون وام": "base_cost_without_loan",
    "قیمت تمام‌شده بدون وام": "base_cost_without_loan",
    "قیمت تمام شده بدون وام بانکی": "base_cost_without_loan",
    "قیمت تمام‌شده بدون وام بانکی": "base_cost_without_loan",
    "قیمت بدون وام": "base_cost_without_loan",
    "مبلغ بدون وام": "base_cost_without_loan",
    "مبلغ کل": "total_price",
    "قیمت کل": "total_price",
    "مبلغ کل (ریال)": "total_price",
    "قیمت کل (ریال)": "total_price",
    "مبلغ کل قرارداد": "total_price",
    "قیمت کل قرارداد": "total_price",
    "مبلغ کل قرارداد (ریال)": "total_price",
    "قیمت کل قرارداد (ریال)": "total_price",
    "مبلغ نهایی": "total_price",
    "قیمت نهایی": "total_price",
    "مبلغ نهایی (ریال)": "total_price",
    "قیمت نهایی (ریال)": "total_price",
    "قیمت تمام شده کل": "total_price",
    "قیمت تمام‌شده کل": "total_price",
    "قیمت تمام شده کل (ریال)": "total_price",
    "قیمت تمام‌شده کل (ریال)": "total_price",
    "قیمت کل تمام شده": "total_price",
    "قیمت کل تمام‌شده": "total_price",
    "قیمت تمام شده با وام": "total_price",
    "قیمت تمام‌شده با وام": "total_price",
    "مبلغ با وام": "total_price",
    "مبلغ تمام شده با وام": "total_price",
    "مبلغ تمام‌شده با وام": "total_price",
    "جمع کل قرارداد": "total_price",
    "جمع کل قرارداد (ریال)": "total_price",
    "قیمت تمام شده بدون وام + وام بانکی": "total_price",
    "قیمت تمام‌شده بدون وام + وام بانکی": "total_price",
    "total_price": "total_price",
    "total_cost": "total_price",
    "total_amount": "total_price",
    "آورده نقدی": "applicant_equity",
    "سهم آورده": "applicant_equity",
    "وام صندوق": "fund_loan_amount",
    "کسر نامه پیمانکار": "contractor_letter_amount",
    "وام دهک": "decile_loan_amount",
    "وام بانکی": "bank_loan_amount",
    "وام ساخت بانک مسکن": "bank_loan_amount",
    "وام ساخت مسکن": "bank_loan_amount",
    "وام بانک مسکن": "bank_loan_amount",
    "وام ساخت": "bank_loan_amount",
    "مبلغ وام ساخت": "bank_loan_amount",
    "تسهیلات بانکی": "bank_loan_amount",
    "مبلغ تسهیلات بانکی": "bank_loan_amount",
    "مبلغ تسهیلات وام بانکی": "bank_loan_amount",
    "مبلغ تسهیلات وام بانکی (ریال)": "bank_loan_amount",
    "تسهیلات بانک مسکن": "bank_loan_amount",
    "کارمزد چک": "check_service_fee",
    "کارمزد آماده سازی": "preparation_service_fee",
    "کارمزد آماده‌سازی": "preparation_service_fee",
    "پروژه": "project",
    "نام پروژه": "project",
    "پروژه مسکونی": "project",
    "کد پروژه": "project_code",
    "کد پروژه مسکونی": "project_code",
    "ثبت دستی": "form_j_registration_type",
    "ثبت خودکار": "form_j_registration_type",
    "نوع ثبت فرم ج": "form_j_registration_type",
    "نحوه ثبت فرم ج": "form_j_registration_type",
    "تاریخ ارسال پیامک": "sms_sent_date",
    "تاریخ ارسال پیامک آورده نقدی": "sms_sent_date",
    "کد نوسازی": "renovation_code",
    "کد نوسازی شهرداری": "renovation_code",
    "کدنوسازی": "renovation_code",
    "کدنوسازی شهرداری": "renovation_code",
    "renovation_code": "renovation_code",
    "municipality_code": "renovation_code",

    # Registry Plaques & Units
    "پلاک اصلی": "main_plaque",
    "پلاک ثبتی اصلی": "main_plaque",
    "اصلی": "main_plaque",
    "پلاک مفروز": "separated_plaque",
    "پلاک ثبتی مفروز": "separated_plaque",
    "پلاک ثبتی مفروز و مجزی": "separated_plaque",
    "پلاک ثبتی مفروز ومجزی": "separated_plaque",
    "پلاک ثبتی مفروز و مجزا": "separated_plaque",
    "پلاک ثبتی مفروز ومجزا": "separated_plaque",
    "مفروز": "separated_plaque",
    "مفروز و مجزا": "separated_plaque",
    "مفروز ومجزا": "separated_plaque",
    "پلاک فرعی": "sub_plaque",
    "پلاک ثبتی فرعی": "sub_plaque",
    "فرعی": "sub_plaque",
    "فرعی از": "sub_plaque",
    "فرعی از (پلاک فرعی)": "sub_plaque",
    "فرعی / مفروز ومجزا / اصلی": "composite_plaques",
    "مفروزی و مجزا": "separated_plaque",
    "مفروز و مجزی": "separated_plaque",
    "مفروزی ومجزا": "separated_plaque",
    "مفروز ومجزی": "separated_plaque",
    "سهم آورده متقاضی": "applicant_equity",
    "سهم آورده متقاضی با کسر وام (ریال)": "applicant_equity",
    "شماره نامه معرفی (کارگزاری به راه و شهرسازی)": "rah_letter",
    "تاریخ نامه معرفی (کارگزاری به راه و شهرسازی)": "rah_letter_date",

    "فرعی / مفروز و مجزا / اصلی": "composite_plaques",
    "فرعی / مفروز ومجزّا / اصلی": "composite_plaques",
    "فرعی/مفروز ومجزا/اصلی": "composite_plaques",
    "فرعی/مفروز و مجزا/اصلی": "composite_plaques",
    "اصلی / مفروز / فرعی": "composite_plaques",
    "اصلی/مفروز/فرعی": "composite_plaques",
    "فرعی / مفروز / اصلی": "composite_plaques",
    "فرعی/مفروز/اصلی": "composite_plaques",
    "پلاک کارگاهی": "plot_number",
    "شماره قطعه": "plot_number",
    "قطعه": "plot_number",
    "مساحت تقریبی زمین": "total_land_area",
    "مساحت زمین": "total_land_area",
    "عرصه": "total_land_area",
    "زیر بنا": "unit_area",
    "زیربنا": "unit_area",
    "مساحت مفید": "unit_area",
    "متراژ مفید": "unit_area",
    "مساحت واحد": "unit_area",
    "متراژ واحد": "unit_area",
    "سهم آورده متقاضی": "applicant_equity",
    "سهم آورده متقاضی (ریال)": "applicant_equity",

    # Road & Housing Letters & Notary Aliases
    "شماره نامه راه و شهرسازی": "rah_letter",
    "شماره نامه راه وشهرسازی": "rah_letter",
    "شماره نامه اداره کل": "rah_letter",
    "شماره نامه راه": "rah_letter",
    "شماره نامه راه شهرسازی": "rah_letter",
    "شماره نامه معرفی به محضر اداره کل": "rah_letter",
    "نامه راه و شهرسازی": "rah_letter",
    "نامه راه": "rah_letter",
    "تاریخ نامه راه و شهرسازی": "rah_letter_date",
    "تاریخ نامه راه وشهرسازی": "rah_letter_date",
    "تاریخ نامه راه و شهرسازی (شمسی)": "rah_letter_date",
    "تاریخ نامه راه": "rah_letter_date",
    "تاریخ نامه اداره کل": "rah_letter_date",
    "تاریخ نامه معرفی به محضر اداره کل": "rah_letter_date",
    "تاریخ نامه معرفی به محضر اداره کل (شمسی)": "rah_letter_date",
    "شماره دفترخانه": "notary_office_number",
    "شماره دفترخانه اسناد رسمی": "notary_office_number",
    "دفترخانه": "notary_office_number",
    "شماره نامه معرفی به محضر": "notary_letter_number",
    "شماره نامه محضر": "notary_letter_number",
    "تاریخ نامه معرفی به محضر": "notary_letter_date",
    "تاریخ نامه معرفی به محضر (شمسی)": "notary_letter_date",
    "تاریخ نامه محضر": "notary_letter_date",
}

# -------------------------------------------------------------------------
# Normalization & Data Cleaning Utilities
# -------------------------------------------------------------------------
FA_AR_DIGITS_TRANS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def clean_digits(val: Any) -> str:
    """Converts Persian and Arabic digits to ASCII digits and strips."""
    if val is None:
        return ""
    s = str(val).translate(FA_AR_DIGITS_TRANS).strip()
    return s

def normalize_header(header: Any) -> str:
    """
    Normalizes Persian header text:
    - ي -> ی
    - ك -> ک
    - ZWNJ (‌) -> space
    - Collapses multiple whitespace
    - Lowercase & strip
    """
    if header is None:
        return ""
    s = str(header).translate(FA_AR_DIGITS_TRANS)
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("‌", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def clean_national_id(val: Any) -> Optional[str]:
    """Cleans national ID to strictly 10 digits with leading zeros."""
    if val is None:
        return None
    s = clean_digits(val)
    if not s:
        return None
    # Handle scientific notation like 3.86747E+08
    if "e" in s.lower():
        try:
            s = f"{float(s):.0f}"
        except (ValueError, OverflowError):
            pass
    elif "." in s:
        try:
            s = str(int(float(s)))
        except (ValueError, OverflowError):
            pass
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    # Real Iranian national IDs have between 8 and 10 digits.
    # If Excel or a user added extra leading zero(s) (e.g. '00382370651' - 11 chars),
    # stripping leading zeros leaves 8 to 10 digits, which is the real national ID:
    unpadded = digits.lstrip("0")
    if unpadded and 8 <= len(unpadded) <= 10:
        return unpadded.zfill(10)
    if len(digits) > 10 or len(digits) < 8 or digits == "0":
        return None
    return digits.zfill(10)

def get_national_id_variants(val: Any) -> List[str]:
    """
    Returns candidate representations of a national ID handling leading zeros:
    e.g. for '381929507' -> ['0381929507', '381929507']
    Allows seamless matching across Excel and DB regardless of dropped or extra leading zeros.
    """
    if val is None:
        return []
    s = clean_digits(val)
    if not s:
        return []
    if "e" in s.lower():
        try:
            s = f"{float(s):.0f}"
        except (ValueError, OverflowError):
            pass
    elif "." in s:
        try:
            s = str(int(float(s)))
        except (ValueError, OverflowError):
            pass
    digits = re.sub(r"\D", "", s)
    if not digits or len(digits) < 8 or digits == "0":
        return []
    variants = []
    unpadded = digits.lstrip("0")
    if unpadded and 8 <= len(unpadded) <= 10:
        variants.append(unpadded.zfill(10))
        variants.append(unpadded)
    if len(digits) <= 10:
        variants.append(digits.zfill(10))
    variants.append(digits)
    if unpadded:
        variants.append(unpadded)
    seen = set()
    result = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result

# Comprehensive Persian labels dictionary for every field in HousingDossier
PERSIAN_FIELD_LABELS: Dict[str, str] = {
    f.name: str(getattr(f, "verbose_name", f.name))
    for f in HousingDossier._meta.get_fields()
    if hasattr(f, "verbose_name") and getattr(f, "verbose_name", None)
}
PERSIAN_FIELD_LABELS.update({
    "national_id": "کد ملی متقاضی",
    "archive_number": "شماره بایگانی",
    "first_name": "نام متقاضی",
    "last_name": "نام خانوادگی متقاضی",
    "full_name": "نام و نام خانوادگی متقاضی",
    "father_name": "نام پدر متقاضی",
    "birth_date": "تاریخ تولد متقاضی",
    "applicant_id_number": "شماره شناسنامه متقاضی",
    "applicant_birth_place": "محل صدور شناسنامه متقاضی",
    "applicant_phone": "شماره همراه متقاضی",
    "project_code": "کد پروژه",
    "bank_name": "نام بانک متقاضی",
    "bank_branch": "شعبه بانک متقاضی",
    "form_j_questionnaire_number": "شماره پرسش نامه فرم ج",
    "applicant_form_j_status": "وضعیت فرم ج متقاضی",
    "applicant_form_j_directorate_status": "استعلام اداره کل متقاضی",
    "applicant_form_j_red_description": "علت کد قرمز فرم ج متقاضی",
    "form_j_registration_type": "نحوه ثبت فرم ج",
    "spouse_first_name": "نام همسر",
    "spouse_last_name": "نام خانوادگی همسر",
    "spouse_full_name": "نام و نام خانوادگی همسر",
    "spouse_father_name": "نام پدر همسر",
    "spouse_national_id": "کد ملی همسر",
    "spouse_birth_date": "تاریخ تولد همسر",
    "spouse_id_number": "شماره شناسنامه همسر",
    "spouse_birth_place": "محل تولد / صدور همسر",
    "spouse_form_j_status": "وضعیت فرم ج همسر",
    "spouse_form_j_directorate_status": "استعلام اداره کل همسر",
    "spouse_form_j_red_description": "علت کد قرمز فرم ج همسر",
    "marital_status": "وضعیت تاهل",
    "is_married_confirmed": "احراز زوجیت",
    "decile": "دهک درآمدی",
    "selection_rank": "رتبه انتخاب واحد",
    "site": "نام سایت / منطقه",
    "site_name": "نام سایت / منطقه",
    "project": "نام پروژه مسکونی",
    "project_name": "نام پروژه مسکونی",
    "construction_type": "نوع ساخت",
    "block_name": "نام بلوک",
    "block_code": "کد بلوک",
    "floor_number": "شماره طبقه",
    "unit_number": "شماره واحد",
    "unit_code": "کد واحد",
    "bedroom_count": "تعداد خواب",
    "unit_direction": "جهت واحد",
    "net_unit_area": "متراژ مفید واحد (مترمربع)",
    "common_area": "متراژ مشاعات (مترمربع)",
    "total_area": "جمع کل متراژ واحد (مترمربع)",
    "unit_area": "مساحت واحد (مترمربع)",
    "storage_number": "شماره انباری",
    "storage_area": "مساحت انباری (مترمربع)",
    "parking_number": "شماره پارکینگ",
    "parking_area": "مساحت پارکینگ (مترمربع)",
    "total_price": "مبلغ کل قرارداد (ریال)",
    "base_cost_without_loan": "قیمت پایه بدون وام (ریال)",
    "bank_loan_amount": "مبلغ وام بانکی مسکن (ریال)",
    "fund_loan_amount": "مبلغ وام صندوق (ریال)",
    "contractor_letter_amount": "مبلغ نامه پیمانکار (ریال)",
    "decile_loan_amount": "مبلغ وام دهک (ریال)",
    "applicant_equity": "آورده نقدی متقاضی (ریال)",
    "total_paid_amount": "کل مبالغ پرداختی (ریال)",
    "remaining_balance": "مانده بدهی (ریال)",
    "final_total_price": "قیمت تمام شده نهایی (ریال)",
    "is_equity_funded": "تایید تامین آورده نقدی",
    "is_sms_sent": "ارسال پیامک آورده نقدی",
    "sms_tracking_code": "کد رهگیری پیامک",
    "sms_sent_date": "تاریخ ارسال پیامک",
    "bank_letter_number": "شماره نامه بانک",
    "bank_letter_date": "تاریخ نامه بانک",
    "is_added_to_bank_shipment_list": "اضافه به لیست ارسالی به بانک",
    "is_sent_to_bank": "ارسال شده به بانک",
    "bank_sent_date": "تاریخ ارسال به بانک",
    "bank_sent_letter_number": "شماره نامه ارسال به بانک",
    "decile_loan_bank": "بانک عامل تسهیلات دهک",
    "supported_institution": "نهاد تحت حمایت",
    "total_land_share": "جمع کل قدرالسهم (مترمربع)",
    "past_years_rent": "مبلغ اجاره سنوات گذشته (ریال)",
    "current_year_rent": "مبلغ اجاره سال جاری (ریال)",
    "land_lease_year": "سال اجاره عرصه",
    "tenant_price": "مبلغ پرداختی اجاره عرصه (ریال)",
    "tenant_code": "کد پیگیری فیش اجاره",
    "is_cash_rent_confirmed": "تایید نقدی اجاره",
    "cash_preparation_amount": "مبلغ نقدی آماده‌سازی (ریال)",
    "non_cash_preparation_amount": "مبلغ اقساط آماده‌سازی (ریال)",
    "prepayment_code": "کد پیگیری پیش‌پرداخت آماده‌سازی",
    "preparation_check_count": "تعداد چک‌های آماده‌سازی",
    "total_preparation_check_amount": "مجموع چک‌های آماده‌سازی (ریال)",
    "is_preparation_checks_confirmed": "تایید چک‌های آماده‌سازی",
    "commitment_number": "شماره تعهدنامه",
    "commitment_date": "تاریخ تعهدنامه",
    "check_count": "تعداد چک‌های دهک",
    "check_amount": "مبلغ هر چک دهک (ریال)",
    "last_check_amount": "مبلغ چک آخر دهک (ریال)",
    "total_check_amount": "مجموع مبلغ چک‌های دهک (ریال)",
    "is_decile_loan_confirmed": "تایید چک‌های دهک",
    "rah_letter": "شماره نامه راه و شهرسازی",
    "rah_letter_date": "تاریخ نامه راه و شهرسازی",
    "check_service_fee": "کارمزد خدمات چک (ریال)",
    "preparation_service_fee": "کارمزد خدمات آماده‌سازی (ریال)",
    "contract_registration_number": "شماره ثبت قرارداد",
    "contract_registration_date": "تاریخ ثبت قرارداد",
    "handover_letter_number": "شماره صورتجلسه تحویل",
    "handover_letter_date": "تاریخ صورتجلسه تحویل",
})

def clean_phone(val: Any) -> str:
    s = clean_digits(val)
    s = re.sub(r"[\s\-\(\)\+]", "", s)
    if s.startswith("98"):
        s = "0" + s[2:]
    return s

def parse_price(val: Any) -> int:
    s = clean_digits(val).replace(",", "").replace("/", "").replace("_", "")
    if not s:
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0

def parse_decimal(val: Any) -> Decimal:
    s = clean_digits(val).replace(",", "")
    if not s:
        return Decimal("0.00")
    try:
        return Decimal(str(float(s))).quantize(Decimal("0.01"))
    except (ValueError, TypeError):
        return Decimal("0.00")

def parse_int(val: Any) -> int:
    s = clean_digits(val)
    if not s:
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0

def parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = normalize_header(val).lower()
    return s in ("بله", "1", "true", "yes", "تایید", "صحیح", "دارد")

# Cache model field max_lengths to prevent redundant meta lookups
FIELD_MAX_LENGTHS: Dict[str, Optional[int]] = {}
for f in HousingDossier._meta.get_fields():
    if hasattr(f, "max_length") and getattr(f, "name", None):
        FIELD_MAX_LENGTHS[f.name] = getattr(f, "max_length", None)

def clean_field_value(field_name: str, field_type: str, val: Any) -> Tuple[Optional[Any], Optional[str]]:
    """
    Cleans and validates a field value according to its spec type and model max_length.
    Returns (cleaned_val, error_message).
    If val is empty/whitespace, returns (None, None) indicating no-change/skip.
    """
    if val is None:
        return None, None
    if isinstance(val, str) and not val.strip():
        return None, None

    if field_type == "national_id" or field_name in ("national_id", "spouse_national_id") or "national_id" in field_name:
        is_zero_or_blank = not val or clean_digits(val).strip("0") == ""
        if is_zero_or_blank:
            return None, None
        c_nid = clean_national_id(val)
        if not c_nid:
            return None, "کد ملی باید ۸ تا ۱۰ رقم عددی باشد."
        return c_nid, None
    elif field_type == "price":
        p = parse_price(val)
        return p, None
    elif field_type == "int":
        i = parse_int(val)
        return i, None
    elif field_type == "decimal":
        d = parse_decimal(val)
        return d, None
    elif field_type == "bool":
        b = parse_bool(val)
        return b, None
    else:
        # String cleaner
        s = clean_digits(val).strip()
        max_len = FIELD_MAX_LENGTHS.get(field_name)
        if max_len and len(s) > max_len:
            return None, f"طول متن ({len(s)}) بیشتر از حد مجاز فیلد ({max_len} کاراکتر) است."
        return s, None

def parse_composite_plaques(val: Any) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[str]]:
    """
    Parses composite registry plaque string into (main_plaque, separated_plaque, sub_plaque, error_message).
    Supports both:
      - 'فرعی / مفروز ومجزا / اصلی' (e.g. '33011/32946/291')
      - 'اصلی / مفروز / فرعی' (e.g. '291/32946/33011')
    """
    if val is None or (isinstance(val, str) and not val.strip()):
        return None, None, None, None

    s = clean_digits(val)
    raw_parts = re.split(r"[/\\–—\-]", s)
    parts: List[int] = []
    for p in raw_parts:
        digits = re.sub(r"\D", "", p.strip())
        if digits:
            try:
                parts.append(int(digits))
            except (ValueError, TypeError):
                pass

    if not parts:
        return None, None, None, None

    if len(parts) == 3:
        # Strictly: main_plaque / separated_plaque / sub_plaque
        return parts[0], parts[1], parts[2], None
    elif len(parts) == 2:
        # Strictly: main_plaque / sub_plaque
        return parts[0], None, parts[1], None
    elif len(parts) == 1:
        # Strictly: main_plaque
        return parts[0], None, None, None
    else:
        return None, None, None, f"فرمت پلاک نامعتبر است ({val})"

# -------------------------------------------------------------------------
# Failure & Spouse Match Report Generation (write_only openpyxl)
# -------------------------------------------------------------------------
def get_reports_dir() -> str:
    r_dir = os.path.join(tempfile.gettempdir(), "dossier_excel_reports")
    os.makedirs(r_dir, exist_ok=True)
    return r_dir

def cleanup_old_reports():
    """Removes Excel reports older than 6 hours."""
    try:
        r_dir = get_reports_dir()
        now = time.time()
        for fname in os.listdir(r_dir):
            if fname.endswith(".xlsx"):
                fpath = os.path.join(r_dir, fname)
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > REPORT_RETENTION_SECONDS:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
    except Exception:
        pass

def generate_failure_report(user_id: int, original_headers: List[str], error_rows: List[Dict[str, Any]], spouse_rows: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Generates a write_only RTL failure workbook.
    Sheet 1: خطاها و موارد رد شده
    Sheet 2 (optional): تطبیق از طریق همسر
    Returns the report UUID.
    """
    cleanup_old_reports()
    report_uuid = str(uuid.uuid4())
    r_dir = get_reports_dir()
    filepath = os.path.join(r_dir, f"{report_uuid}_{user_id}.xlsx")

    wb = openpyxl.Workbook(write_only=True)

    # Sheet 1: Errors
    ws_errors = wb.create_sheet(title="موارد رد شده و خطاها")
    ws_errors.views.sheetView[0].rightToLeft = True

    err_headers = ["ردیف اکسل", "کد ملی", "نام متقاضی / همسر", "علت رد و خطا"] + [str(h or "") for h in original_headers]
    ws_errors.append(err_headers)

    for item in error_rows:
        reasons_str = " | ".join(item.get("reasons", []))
        orig_cells = item.get("original_cells", [])
        row_vals = [
            item.get("row", ""),
            item.get("national_id", ""),
            item.get("name", ""),
            reasons_str,
        ] + [str(c if c is not None else "") for c in orig_cells]
        ws_errors.append(row_vals)

    # Sheet 2: Spouse Matched (for Update)
    if spouse_rows:
        ws_spouse = wb.create_sheet(title="تطبیق از طریق همسر")
        ws_spouse.views.sheetView[0].rightToLeft = True
        ws_spouse.append(["ردیف اکسل", "کد ملی همسر ورودی", "نام پرونده", "شماره بایگانی", "تغییرات اعمال‌شده"])
        for item in spouse_rows:
            diff_text = " ، ".join([f"{d.get('label', '')}: {d.get('old', '')} -> {d.get('new', '')}" for d in item.get("diff_display", [])])
            ws_spouse.append([
                item.get("row", ""),
                item.get("national_id", ""),
                item.get("name", ""),
                item.get("archive_number", ""),
                diff_text or "بدون تغییر",
            ])

    wb.save(filepath)
    return report_uuid

def generate_success_report(user_id: int, original_headers: List[str], success_rows: List[Dict[str, Any]], title: str = "پرونده‌های تایید و بروزرسانی‌شده") -> str:
    """
    Generates a write_only RTL success workbook for accepted / updated dossiers.
    Returns the report UUID.
    """
    cleanup_old_reports()
    report_uuid = str(uuid.uuid4())
    r_dir = get_reports_dir()
    filepath = os.path.join(r_dir, f"{report_uuid}_{user_id}.xlsx")

    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet(title=title[:30])
    ws.views.sheetView[0].rightToLeft = True

    base_headers = ["ردیف اکسل", "شماره بایگانی", "کد ملی", "نام متقاضی", "وضعیت", "توضیحات و تغییرات اعمال‌شده"]
    if original_headers:
        full_headers = base_headers + [str(h or "") for h in original_headers]
    else:
        full_headers = base_headers
    ws.append(full_headers)

    for item in success_rows:
        if isinstance(item, (list, tuple)):
            ws.append(list(item))
            continue
        orig_cells = item.get("original_cells", [])
        row_vals = [
            item.get("row", ""),
            item.get("archive_number", ""),
            item.get("national_id", ""),
            item.get("name", ""),
            item.get("status", "موفق"),
            item.get("diff_summary", "") or item.get("notes", ""),
        ]
        if orig_cells:
            row_vals.extend([str(c if c is not None else "") for c in orig_cells])
        ws.append(row_vals)

    wb.save(filepath)
    return report_uuid

def get_report_file_path(report_id: str, user_id: int) -> Optional[str]:
    r_dir = get_reports_dir()
    expected_filename = f"{report_id}_{user_id}.xlsx"
    fpath = os.path.join(r_dir, expected_filename)
    if os.path.isfile(fpath):
        return fpath
    return None

# -------------------------------------------------------------------------
# Template Generators
# -------------------------------------------------------------------------
_HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
_GUIDE_FILL = PatternFill(start_color="047857", end_color="047857", fill_type="solid")
_HEADER_FONT = Font(name="Tahoma", size=10, bold=True, color="FFFFFF")
_DATA_FONT = Font(name="Tahoma", size=10)
_ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
_ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

def _style_headers(ws: Worksheet, col_count: int, fill=_HEADER_FILL):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = fill
        cell.font = _HEADER_FONT
        cell.alignment = _ALIGN_CENTER
        ws.column_dimensions[get_column_letter(col)].width = 24

def generate_create_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ورود پرونده‌های جدید"
    ws.views.sheetView[0].rightToLeft = True

    headers = [spec[0] for spec in TEMPLATE_FIELD_SPECS]
    ws.append(headers)
    _style_headers(ws, len(headers))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def generate_update_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "بروزرسانی پرونده‌ها"
    ws1.views.sheetView[0].rightToLeft = True

    headers = [spec[0] for spec in TEMPLATE_FIELD_SPECS]
    ws1.append(headers)
    _style_headers(ws1, len(headers))

    # Sheet 2: Guide
    ws2 = wb.create_sheet(title="راهنمای بروزرسانی")
    ws2.views.sheetView[0].rightToLeft = True
    ws2.append(["راهنمای مهم بروزرسانی دسته‌جمعی پرونده‌ها"])
    ws2.append(["۱. ستون کلیدی برای انطباق، «کد ملی متقاضی» است."])
    ws2.append(["۲. سیستم ابتدا کد ملی را با متقاضی اصلی و در صورت عدم تطبیق، با همسر تطبیق می‌دهد."])
    ws2.append(["۳. سلول‌های خالی دست‌نخورده باقی می‌مانند و هیچ داده‌ای پاک نمی‌شود."])
    ws2.append(["۴. این بخش فقط پرونده‌های موجود را بروزرسانی می‌کند و هرگز پرونده جدید نمی‌سازد."])
    ws2.append(["۵. در تطبیق از طریق همسر، مشخصات هویتی متقاضی دست‌نخورده باقی می‌ماند."])
    ws2.append(["۶. در صورت درج ستون «مبلغ کل قرارداد»، سیستم به صورت خودکار مبلغ وام بانکی (پیش‌فرض ۶۵۰ میلیون ریال یا مقدار درج‌شده در فایل) را از آن کسر کرده و «قیمت تمام‌شده بدون وام بانکی» را محاسبه و ثبت می‌نماید."])
    ws2.append(["۷. برای مشخصات پلاک‌های ثبتی می‌توانید از ۳ ستون مجزای «پلاک اصلی»، «پلاک مفروز» و «پلاک فرعی» استفاده نمایید یا مشخصات را در ستون ترکیبی «فرعی / مفروز ومجزا / اصلی» درج فرمایید."])
    _style_headers(ws2, 1, fill=_GUIDE_FILL)
    ws2.column_dimensions["A"].width = 75

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def generate_group_sign_template() -> io.BytesIO:
    """
    Generates a workflow group signing Excel template where:
    - Column 1: کد ملی متقاضی (National ID)
    - Columns 2 to 23: مرحله 1 تا مرحله 22 (Workflow Stages 1 to 22)
    - Column 24: توضیحات امضا (اختیاری) (Optional Notes)
    The user enters national IDs in Column 1, and places '1' under whichever stage(s) need to be signed.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "امضای دسته‌جمعی مراحل"
    ws.views.sheetView[0].rightToLeft = True
    ws.freeze_panes = "B2"

    headers = ["کد ملی متقاضی"] + [f"مرحله {i}" for i in range(1, 23)] + ["توضیحات امضا (اختیاری)"]
    ws.append(headers)

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="B Nazanin", size=10, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    ws.column_dimensions["A"].width = 18
    for col_idx in range(2, 24):
        ws.column_dimensions[get_column_letter(col_idx)].width = 11
    ws.column_dimensions[get_column_letter(24)].width = 25

    ws2 = wb.create_sheet(title="راهنمای امضای گروهی")
    ws2.views.sheetView[0].rightToLeft = True
    guide_lines = [
        "راهنمای تکمیل قالب امضای دسته‌جمعی مراحل گردش کار",
        "۱. در ستون اول («کد ملی متقاضی»)، کد ملی متقاضی یا همسر را وارد نمایید.",
        "۲. در سرستون‌های مراحل ۱ تا ۲۲، زیر هر مرحله‌ای که مایل به امضا و تایید آن هستید عدد ۱ را درج کنید.",
        "۳. امکان امضای هم‌زمان چند مرحله متوالی برای یک پرونده با قرار دادن عدد ۱ در هر یک از مراحل مربوطه وجود دارد.",
        "۴. مراحل انتخابی به ترتیب بررسی شده و پس از ثبت امضای الکترونیک، پرونده به مرحله بعد هدایت می‌شود.",
        "۵. در صورتی که وضعیت استعلام فرم «ج» پرونده قرمز باشد، سیستم از تایید مرحله ۳ ممانعت خواهد کرد.",
        "۶. ستون توضیحات اختیاری بوده و یادداشت ثبت‌شده در لاگ ممیزی و تاریخچه پرونده درج می‌شود."
    ]
    for line in guide_lines:
        ws2.append([line])
    _style_headers(ws2, 1, fill=_GUIDE_FILL)
    ws2.column_dimensions["A"].width = 85

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def generate_spouse_swap_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "جابجایی متقاضی با همسر"
    ws.views.sheetView[0].rightToLeft = True

    headers = ["کد ملی متقاضی (مالک فعلی پرونده)"]
    ws.append(headers)
    _style_headers(ws, len(headers))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

# -------------------------------------------------------------------------
# Header Mapping Helper
# -------------------------------------------------------------------------
def _build_header_map(raw_headers: List[Any]) -> Tuple[Dict[int, Tuple[str, str, str]], Optional[int]]:
    """
    Builds column mapping using pre-known template indexes as well as header title & alias matching.
    Ensures 'ردیف' and row sequence columns are never mapped to national_id or other fields.
    Returns (col_map, national_id_col_idx).
    """
    col_map: Dict[int, Tuple[str, str, str]] = {}
    nid_col: Optional[int] = None
    spec_by_header = {normalize_header(spec[0]): spec for spec in TEMPLATE_FIELD_SPECS}

    # Step 1: Match by exact titles and aliases
    for idx, raw in enumerate(raw_headers):
        if not raw:
            continue
        norm = normalize_header(raw)

        # Explicitly skip row numbering headers
        if norm in ("ردیف", "ردیف ", "شماره ردیف", "ردیف پرونده", "row", "id", "شماره"):
            continue

        # Check national_id aliases
        if norm in ("کد ملی متقاضی", "کدملی متقاضی", "کد ملی", "کدملی", "شماره ملی", "شماره ملی متقاضی", "شماره‌ملی", "شماره‌ملی متقاضی", "شناسه ملی", "شناسه ملی متقاضی", "شناسه‌ملی", "شناسه‌ملی متقاضی", "کد/شناسه ملی", "کد / شناسه ملی", "کد / شناسه ملی متقاضی", "کدملی/شناسه ملی"):
            col_map[idx] = ("کد ملی متقاضی", "national_id", "national_id")
            if nid_col is None:
                nid_col = idx
            continue

        # Check composite plaque header (e.g. اصلی / مفروز / فرعی or فرعی / مفروز ومجزا / اصلی)
        if (("اصلی" in norm and "فرعی" in norm) or ("مفروز" in norm and ("اصلی" in norm or "فرعی" in norm)) or "/" in norm):
            if any(p in norm for p in ["اصلی", "فرعی", "مفروز", "مفروزی", "مجزی", "مجزا"]):
                col_map[idx] = ("فرعی / مفروز ومجزا / اصلی", "composite_plaques", "composite_plaques")
                continue

        # Check exact spec title
        if norm in spec_by_header:
            col_map[idx] = spec_by_header[norm]
            if spec_by_header[norm][1] == "national_id" and nid_col is None:
                nid_col = idx
            continue

        # Check aliases
        if norm in HEADER_ALIASES:
            field_name = HEADER_ALIASES[norm]
            for spec in TEMPLATE_FIELD_SPECS:
                if spec[1] == field_name:
                    col_map[idx] = spec
                    if field_name == "national_id" and nid_col is None:
                        nid_col = idx
                    break
            continue

    # Step 2: Template Index Fallback
    # If the sheet is formatted as our standard template (e.g. index 0 is national_id or col 0 title is کد ملی متقاضی),
    # fill any missing unmapped columns according to TEMPLATE_FIELD_SPECS
    is_template_layout = (nid_col == 0 or (0 in col_map and col_map[0][1] == "national_id"))
    if is_template_layout:
        for idx in range(min(len(TEMPLATE_FIELD_SPECS), len(raw_headers))):
            if idx not in col_map:
                raw_val = raw_headers[idx]
                norm = normalize_header(raw_val) if raw_val else ""
                if norm not in ("ردیف", "شماره ردیف", "row", "id", "شماره"):
                    col_map[idx] = TEMPLATE_FIELD_SPECS[idx]

    # If nid_col is still None, scan col_map for national_id
    if nid_col is None:
        for idx, spec in col_map.items():
            if spec[1] == "national_id":
                nid_col = idx
                break

    return col_map, nid_col

# -------------------------------------------------------------------------
# Feature 1: Process Excel Create
# -------------------------------------------------------------------------
def process_excel_create(file_obj: Any, user: Any, preview: bool = False, is_preview: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
    if is_preview is not None:
        preview = is_preview
    profile = getattr(user, "profile", None)
    is_admin = user.is_superuser or user.is_staff or (profile and profile.is_housing_chief)
    if not is_admin:
        return {"success": False, "error": "شما دسترسی مجاز برای ایجاد پرونده‌های جدید ندارید."}

    is_check_admin = user.is_superuser or (profile and getattr(profile, "is_check_admin", False))
    warnings: List[str] = []
    commission_warned = False

    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    except Exception as e:
        return {"success": False, "error": f"فایل اکسل معتبر نیست یا خراب است: {str(e)}"}

    # Target data worksheet (skip guide sheet if present)
    target_ws = wb.worksheets[0]
    if len(wb.worksheets) > 1 and "راهنما" in (target_ws.title or ""):
        target_ws = wb.worksheets[1]

    row_iter = target_ws.iter_rows(values_only=True)
    header_row = None
    header_row_num = 0
    for r in row_iter:
        header_row_num += 1
        if r and any(c is not None and str(c).strip() for c in r):
            header_row = r
            break

    if not header_row:
        return {"success": False, "error": "فایل اکسل خالی است."}

    raw_headers = list(header_row or [])
    col_map, nid_col = _build_header_map(raw_headers)

    if nid_col is None:
        return {"success": False, "error": "ستون اجباری «کد ملی متقاضی» در فایل اکسل یافت نشد."}

    # Preload ProjectBankMapping
    bank_mappings = {m.project_name: m for m in ProjectBankMapping.objects.all()}

    # First pass: parse rows and collect candidate national IDs
    parsed_rows: List[Dict[str, Any]] = []
    all_nids: Set[str] = set()
    all_snids: Set[str] = set()
    errors: List[Dict[str, Any]] = []

    seen_file_nids: Dict[str, int] = {}
    seen_file_snids: Dict[str, int] = {}

    row_num = header_row_num
    for row_cells in row_iter:
        row_num += 1
        if not any(c is not None and str(c).strip() for c in row_cells):
            continue

        raw_nid = row_cells[nid_col] if nid_col < len(row_cells) else None
        cleaned_nid = clean_national_id(raw_nid)

        row_errors: List[str] = []
        if not cleaned_nid:
            row_errors.append("کد ملی متقاضی نامعتبر یا خالی است (باید دقیقاً ۱۰ رقم باشد).")

        # Parse fields
        parsed_data: Dict[str, Any] = {}
        for c_idx, val in enumerate(row_cells):
            if c_idx not in col_map or val is None:
                 continue
            if isinstance(val, str) and val.strip().upper() in ("#N/A", "#VALUE!", "#REF!", "#NAME?", "#DIV/0!", "#NUM!", "#NULL!"):
                    continue
            header_title, field_name, field_type = col_map[c_idx]

            # Commission permission check
            if field_name in ("check_service_fee", "preparation_service_fee"):
                if not is_check_admin:
                    if not commission_warned:
                        warnings.append("ستون‌های کارمزد برای شما مجاز نیست و نادیده گرفته شد.")
                        commission_warned = True
                    continue

            # Special handlers
            if field_name == "composite_plaques":
                p_main, p_sep, p_sub, err = parse_composite_plaques(val)
                if err:
                    row_errors.append(f"ستون «{header_title}»: {err}")
                else:
                    if p_main is not None and "main_plaque" not in parsed_data:
                        parsed_data["main_plaque"] = p_main
                        parsed_labels["main_plaque"] = "پلاک اصلی"
                    if p_sep is not None and "separated_plaque" not in parsed_data:
                        parsed_data["separated_plaque"] = p_sep
                        parsed_labels["separated_plaque"] = "پلاک مفروز"
                    if p_sub is not None and "sub_plaque" not in parsed_data:
                        parsed_data["sub_plaque"] = p_sub
                        parsed_labels["sub_plaque"] = "پلاک فرعی"
                continue

            # Special cleaners
            if field_name == "national_id":
                c_val = cleaned_nid
                err = None
            elif field_name == "spouse_national_id":
                is_zero_or_blank = not val or clean_digits(val).strip("0") == ""
                if is_zero_or_blank:
                    c_val = None
                    err = None
                else:
                    c_val = clean_national_id(val)
                    err = None if c_val else "کد ملی همسر باید ۸ تا ۱۰ رقم باشد."
            elif field_name == "applicant_phone":
                c_val = clean_phone(val)
                err = None
            else:
                c_val, err = clean_field_value(field_name, field_type, val)

            if err:
                row_errors.append(f"ستون «{header_title}»: {err}")
            elif c_val is not None:
                parsed_data[field_name] = c_val

        # Total price auto-calculation for CREATE:
        # total_price = base_cost_without_loan + bank_loan_amount
        # base_cost_without_loan = total_price - bank_loan_amount
        if "total_price" in parsed_data:
            tot_price = parsed_data.pop("total_price")
            if tot_price and tot_price > 0:
                loan_val = parsed_data.get("bank_loan_amount")
                if not loan_val or loan_val <= 0:
                    loan_val = 6500000000
                    parsed_data["bank_loan_amount"] = loan_val

                if tot_price < loan_val:
                    row_errors.append(
                        f"مبلغ کل قرارداد ({tot_price:,} ریال) نمی‌تواند کمتر از مبلغ وام بانکی ({loan_val:,} ریال) باشد."
                    )
                else:
                    parsed_data["base_cost_without_loan"] = tot_price - loan_val

        if cleaned_nid:
            # Duplicate inside file check
            if cleaned_nid in seen_file_nids:
                row_errors.append(f"کد ملی در همین فایل با ردیف {seen_file_nids[cleaned_nid]} تکراری است.")
            else:
                seen_file_nids[cleaned_nid] = row_num

            # Couple conflict inside file check
            if CHECK_COUPLE_CONFLICT:
                snid = parsed_data.get("spouse_national_id")
                if snid:
                    if snid in seen_file_nids:
                        row_errors.append(f"کد ملی همسر در همین فایل به عنوان متقاضی در ردیف {seen_file_nids[snid]} وجود دارد.")
                    if cleaned_nid in seen_file_snids:
                        row_errors.append(f"کد ملی متقاضی در همین فایل به عنوان همسر در ردیف {seen_file_snids[cleaned_nid]} وجود دارد.")
                    seen_file_snids[snid] = row_num

            all_nids.add(cleaned_nid)
            snid_val = parsed_data.get("spouse_national_id")
            if snid_val:
                all_snids.add(snid_val)

        row_item = {
            "row": row_num,
            "national_id": cleaned_nid or str(raw_nid or ""),
            "name": parsed_data.get("full_name") or f"{parsed_data.get('first_name', '')} {parsed_data.get('last_name', '')}".strip(),
            "data": parsed_data,
            "original_cells": list(row_cells),
            "reasons": row_errors,
        }
        parsed_rows.append(row_item)

    # Chunked DB uniqueness & couple queries
    existing_app_nids: Set[str] = set()
    existing_spouse_to_archive: Dict[str, int] = {}
    existing_app_to_archive_for_spouse: Dict[str, int] = {}

    all_nids_list = list(all_nids)
    for i in range(0, len(all_nids_list), CHUNK_QUERY_SIZE):
        chunk = all_nids_list[i : i + CHUNK_QUERY_SIZE]
        for nid in HousingDossier.objects.filter(national_id__in=chunk).values_list("national_id", flat=True):
            existing_app_nids.add(nid)
        if CHECK_COUPLE_CONFLICT:
            for snid, arch in HousingDossier.objects.filter(spouse_national_id__in=chunk).exclude(spouse_national_id="").values_list("spouse_national_id", "archive_number"):
                existing_spouse_to_archive[snid] = arch

    if CHECK_COUPLE_CONFLICT and all_snids:
        all_snids_list = list(all_snids)
        for i in range(0, len(all_snids_list), CHUNK_QUERY_SIZE):
            chunk = all_snids_list[i : i + CHUNK_QUERY_SIZE]
            for nid, arch in HousingDossier.objects.filter(national_id__in=chunk).values_list("national_id", "archive_number"):
                existing_app_to_archive_for_spouse[nid] = arch

    # Validate against DB
    valid_rows: List[Dict[str, Any]] = []
    for item in parsed_rows:
        nid = item["data"].get("national_id")
        snid = item["data"].get("spouse_national_id")

        if nid in existing_app_nids:
            item["reasons"].append("کد ملی متقاضی قبلاً در سامانه ثبت شده است.")

        if CHECK_COUPLE_CONFLICT:
            if nid in existing_spouse_to_archive:
                item["reasons"].append(f"کد ملی متقاضی به عنوان همسر در پرونده {existing_spouse_to_archive[nid]} ثبت شده است.")
            if snid and snid in existing_app_to_archive_for_spouse:
                item["reasons"].append(f"کد ملی همسر به عنوان متقاضی در پرونده {existing_app_to_archive_for_spouse[snid]} ثبت شده است.")

        if item["reasons"]:
            errors.append(item)
        else:
            valid_rows.append(item)

    report_url = None
    if errors:
        r_uuid = generate_failure_report(user.id, raw_headers, errors)
        report_url = f"/excel/report/{r_uuid}/"

    if preview:
        return {
            "success": True,
            "error": None,
            "preview": True,
            "created_count": 0,
            "updated_count": 0,
            "valid_count": len(valid_rows),
            "unchanged_count": 0,
            "failed_count": len(errors),
            "matched_via_spouse_count": 0,
            "warnings": warnings,
            "report_url": report_url,
            "errors": errors[:100],
            "updates_preview": [],
        }

    # Confirm mode: Bulk create dossiers with auto-assigned archive_numbers
    created_count = 0
    if valid_rows:
        max_num = HousingDossier.objects.aggregate(models.Max("archive_number"))["archive_number__max"] or 100000

        instances_to_create: List[HousingDossier] = []
        for item in valid_rows:
            max_num += 1
            data = dict(item["data"])
            data.pop("archive_number", None)

            dossier = HousingDossier(**data)
            dossier.archive_number = max_num

            # Auto-fill bank from ProjectBankMapping if empty
            if dossier.project and dossier.project in bank_mappings:
                m = bank_mappings[dossier.project]
                if not dossier.bank_name:
                    dossier.bank_name = m.get_bank_code_display()
                if not dossier.project_code and m.project_code:
                    dossier.project_code = m.project_code
                if not dossier.bank_branch and m.branch_name:
                    dossier.bank_branch = m.branch_name

            explicit_set = set(data.keys())
            dossier.recompute_derived_fields(skip=explicit_set)
            instances_to_create.append(dossier)

        # Chunked write
        for i in range(0, len(instances_to_create), CHUNK_WRITE_SIZE):
            chunk = instances_to_create[i : i + CHUNK_WRITE_SIZE]
            try:
                with transaction.atomic():
                    HousingDossier.objects.bulk_create(chunk)
                    created_count += len(chunk)
            except IntegrityError:
                # Row-by-row fallback
                for d in chunk:
                    try:
                        with transaction.atomic():
                            d.save()
                            created_count += 1
                    except Exception as row_err:
                        err_item = {
                            "row": d.archive_number,
                            "national_id": d.national_id,
                            "name": d.full_name,
                            "reasons": [f"خطای پایگاه داده در ذخیره رکورد: {str(row_err)}"],
                            "original_cells": [],
                        }
                        errors.append(err_item)

        # Audit logs: re-query by national_id__in to ensure PKs
        all_created_nids = [d.national_id for d in instances_to_create]
        actor_name = profile.full_name if profile and profile.full_name else (user.get_full_name() or user.username)
        actor_role = profile.role_title if profile and profile.role_title else "مدیر سیستم"

        for i in range(0, len(all_created_nids), CHUNK_QUERY_SIZE):
            n_chunk = all_created_nids[i : i + CHUNK_QUERY_SIZE]
            saved_dossiers = list(HousingDossier.objects.filter(national_id__in=n_chunk))
            logs = []
            for d in saved_dossiers:
                s_hash = "SHA256: " + hashlib.sha256(f"EXCEL_CREATE:{d.id}:{uuid.uuid4()}".encode()).hexdigest()[:24]
                logs.append(WorkflowSignatureLog(
                    dossier=d,
                    from_stage="مرحله ۱: ورود اطلاعات انتخاب واحد",
                    to_stage="مرحله ۱: ورود اطلاعات انتخاب واحد",
                    actor=actor_name,
                    role=actor_role,
                    action="EXCEL_CREATE",
                    action_label="ایجاد گروهی از طریق اکسل",
                    signature_hash=s_hash,
                    notes="ایجاد پرونده از طریق فایل اکسل"
                ))
            WorkflowSignatureLog.objects.bulk_create(logs)

    if errors and not report_url:
        r_uuid = generate_failure_report(user.id, raw_headers, errors)
        report_url = f"/excel/report/{r_uuid}/"

    return {
        "success": True,
        "error": None,
        "preview": False,
        "created_count": created_count,
        "updated_count": 0,
        "valid_count": created_count,
        "unchanged_count": 0,
        "failed_count": len(errors),
        "matched_via_spouse_count": 0,
        "warnings": warnings,
        "report_url": report_url,
        "errors": errors[:100],
        "updates_preview": [],
    }

# -------------------------------------------------------------------------
# Feature 2: Process Excel Update (NEVER CREATES)
# -------------------------------------------------------------------------
IDENTITY_FIELDS = {
    "first_name", "last_name", "full_name", "father_name", "birth_date",
    "applicant_id_number", "applicant_birth_place", "applicant_phone",
    "national_id", "archive_number",
    "spouse_first_name", "spouse_last_name", "spouse_full_name",
    "spouse_father_name", "spouse_national_id", "spouse_birth_date",
    "spouse_id_number", "spouse_birth_place",
}

SWAP_FIELD_PAIRS = [
    ("national_id", "spouse_national_id"),
    ("first_name", "spouse_first_name"),
    ("last_name", "spouse_last_name"),
    ("full_name", "spouse_full_name"),
    ("father_name", "spouse_father_name"),
    ("birth_date", "spouse_birth_date"),
    ("applicant_id_number", "spouse_id_number"),
    ("applicant_birth_place", "spouse_birth_place"),
    ("applicant_form_j_status", "spouse_form_j_status"),
    ("applicant_form_j_directorate_status", "spouse_form_j_directorate_status"),
    ("applicant_form_j_red_description", "spouse_form_j_red_description"),
]


def process_excel_update(file_obj: Any, user: Any, preview: bool = False, is_preview: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
    if is_preview is not None:
        preview = is_preview
    profile = getattr(user, "profile", None)
    is_admin = user.is_superuser or user.is_staff or (profile and profile.is_housing_chief)
    if not is_admin:
        return {"success": False, "error": "شما دسترسی مجاز برای بروزرسانی دسته‌جمعی پرونده‌ها را ندارید."}

    is_check_admin = user.is_superuser or (profile and getattr(profile, "is_check_admin", False))
    warnings: List[str] = []
    commission_warned = False

    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    except Exception as e:
        return {"success": False, "error": f"فایل اکسل معتبر نیست یا خراب است: {str(e)}"}

    # Multi-sheet support: filter out guidance sheets
    sheets_to_process = []
    for ws in wb.worksheets:
        ws_title = ws.title or ""
        if "راهنما" in ws_title or "guide" in ws_title.lower():
            continue
        sheets_to_process.append(ws)

    if not sheets_to_process:
        sheets_to_process = [wb.worksheets[0]]

    parsed_rows: List[Dict[str, Any]] = []
    all_nids: Set[str] = set()
    errors: List[Dict[str, Any]] = []
    raw_headers_master: List[Any] = []
    global_row_counter = 0

    for ws in sheets_to_process:
        row_iter = ws.iter_rows(values_only=True)
        buffered_rows = []
        for _ in range(10):
            try:
                buffered_rows.append(next(row_iter))
            except StopIteration:
                break

        if not buffered_rows:
            continue

        # Header scan: look in first 10 rows for national_id column
        header_row = None
        header_row_num = 0
        for r_idx, r in enumerate(buffered_rows):
            if not r:
                continue
            r_str = " ".join(str(c) for c in r if c is not None)
            if any(t in r_str for t in ["کدملی", "کد ملی", "شماره ملی", "شناسه ملی", "کد ملی متقاضی", "کد ملی همسر"]):
                header_row = r
                header_row_num = r_idx + 1
                break

        if not header_row:
            # Fallback to first non-empty row
            for r_idx, r in enumerate(buffered_rows):
                if r and any(c is not None and str(c).strip() for c in r):
                    header_row = r
                    header_row_num = r_idx + 1
                    break

        if not header_row:
            continue

        raw_headers = list(header_row or [])
        if not raw_headers_master:
            raw_headers_master = raw_headers

        col_map, nid_col = _build_header_map(raw_headers)

        spouse_nid_col = None
        for c_idx, spec in col_map.items():
            if spec[1] == "spouse_national_id":
                spouse_nid_col = c_idx
                break

        if nid_col is None and spouse_nid_col is None:
            continue

        sheet_row_num = header_row_num
        row_stream = itertools.chain(buffered_rows[header_row_num:], row_iter)
        for row_cells in row_stream:
            sheet_row_num += 1
            global_row_counter += 1
            if not any(c is not None and str(c).strip() for c in row_cells):
                continue

            raw_nid = row_cells[nid_col] if (nid_col is not None and nid_col < len(row_cells)) else None
            cleaned_nid = clean_national_id(raw_nid)
            app_variants = get_national_id_variants(raw_nid)

            raw_snid = row_cells[spouse_nid_col] if (spouse_nid_col is not None and spouse_nid_col < len(row_cells)) else None
            is_spouse_zero_or_empty = not raw_snid or clean_digits(raw_snid).strip("0") == ""
            if is_spouse_zero_or_empty:
                cleaned_snid = None
                spouse_variants = []
            else:
                cleaned_snid = clean_national_id(raw_snid)
                spouse_variants = get_national_id_variants(raw_snid) if raw_snid else []

            row_errors: List[str] = []
            if not app_variants and not spouse_variants:
                row_errors.append("کد ملی متقاضی یا همسر نامعتبر یا خالی است.")

            parsed_data: Dict[str, Any] = {}
            parsed_labels: Dict[str, str] = {}
            for c_idx, val in enumerate(row_cells):
                if c_idx not in col_map or val is None:
                    continue
                if isinstance(val, str) and val.strip().upper() in ("#N/A", "#VALUE!", "#REF!", "#NAME?", "#DIV/0!", "#NUM!", "#NULL!"):
                    continue
                header_title, field_name, field_type = col_map[c_idx]

                # Commission permission check
                if field_name in ("check_service_fee", "preparation_service_fee"):
                    if not is_check_admin:
                        if not commission_warned:
                            warnings.append("ستون‌های کارمزد برای شما مجاز نیست و نادیده گرفته شد.")
                            commission_warned = True
                        continue

                # National ID and archive number are NEVER updated directly
                if field_name in ("national_id", "archive_number"):
                    continue

                # Special handlers
                if field_name == "composite_plaques":
                    p_main, p_sep, p_sub, err = parse_composite_plaques(val)
                    if err:
                        row_errors.append(f"ستون «{header_title}»: {err}")
                    else:
                        if p_main is not None and "main_plaque" not in parsed_data:
                            parsed_data["main_plaque"] = p_main
                            parsed_labels["main_plaque"] = "پلاک اصلی"
                        if p_sep is not None and "separated_plaque" not in parsed_data:
                            parsed_data["separated_plaque"] = p_sep
                            parsed_labels["separated_plaque"] = "پلاک مفروز"
                        if p_sub is not None and "sub_plaque" not in parsed_data:
                            parsed_data["sub_plaque"] = p_sub
                            parsed_labels["sub_plaque"] = "پلاک فرعی"
                    continue

                # Special cleaners
                if field_name == "spouse_national_id":
                    is_zero_or_blank = not val or clean_digits(val).strip("0") == ""
                    if is_zero_or_blank:
                        c_val = None
                        err = None
                    else:
                        c_val = clean_national_id(val)
                        err = None if c_val else "کد ملی همسر باید ۸ تا ۱۰ رقم باشد."
                elif field_name == "applicant_phone":
                    c_val = clean_phone(val)
                    err = None
                else:
                    c_val, err = clean_field_value(field_name, field_type, val)

                if err:
                    row_errors.append(f"ستون «{header_title}»: {err}")
                elif c_val is not None:
                    parsed_data[field_name] = c_val
                    parsed_labels[field_name] = header_title

            if not spouse_variants and parsed_data.get("spouse_national_id"):
                spouse_variants = get_national_id_variants(parsed_data["spouse_national_id"])

            for v in app_variants:
                all_nids.add(v)
            for v in spouse_variants:
                all_nids.add(v)

            display_nid = cleaned_nid or cleaned_snid or (app_variants[0] if app_variants else (spouse_variants[0] if spouse_variants else str(raw_nid or raw_snid or "")))

            parsed_rows.append({
                "row": sheet_row_num,
                "global_row": global_row_counter,
                "national_id": display_nid,
                "cleaned_nid": cleaned_nid,
                "cleaned_snid": cleaned_snid,
                "raw_nid": raw_nid,
                "raw_snid": raw_snid,
                "app_variants": app_variants,
                "spouse_variants": spouse_variants,
                "data": parsed_data,
                "labels": parsed_labels,
                "original_cells": list(row_cells),
                "reasons": row_errors,
            })

    if not parsed_rows:
        return {"success": False, "error": "ستون کلیدی «کد ملی متقاضی» یا «کد ملی همسر» در فایل اکسل یافت نشد یا هیچ ردیف داده‌ای وجود ندارد."}

    raw_headers = raw_headers_master

    # Preload DB dossiers in chunks matching any variant in national_id or spouse_national_id
    app_matches: Dict[str, HousingDossier] = {}
    spouse_matches: Dict[str, List[HousingDossier]] = {}
    loaded_pks: Set[int] = set()

    all_nids_list = list(all_nids)
    for i in range(0, len(all_nids_list), CHUNK_QUERY_SIZE):
        chunk = all_nids_list[i : i + CHUNK_QUERY_SIZE]
        for d in HousingDossier.objects.filter(Q(national_id__in=chunk) | Q(spouse_national_id__in=chunk)):
            if d.pk in loaded_pks:
                continue
            loaded_pks.add(d.pk)
            for v in get_national_id_variants(d.national_id):
                app_matches[v] = d
            if d.spouse_national_id and clean_digits(d.spouse_national_id).strip("0") != "":
                for v in get_national_id_variants(d.spouse_national_id):
                    spouse_matches.setdefault(v, []).append(d)

    seen_dossiers_info: Dict[int, Dict[str, Any]] = {}
    updates_preview: List[Dict[str, Any]] = []
    dossiers_to_update: List[HousingDossier] = []
    field_changes_by_dossier: Dict[int, List[Dict[str, Any]]] = {}
    modified_fields_set: Set[str] = set()
    spouse_matched_rows: List[Dict[str, Any]] = []
    valid_updated_records: List[Dict[str, Any]] = []

    valid_count = 0
    unchanged_count = 0
    updated_count = 0

    for item in parsed_rows:
        nid = item["national_id"]
        if item["reasons"]:
            errors.append(item)
            continue

        # Pre-check: Cross-couple contradiction if both applicant and spouse NID provided in row
        d_app = None
        for v in item["app_variants"]:
            if v in app_matches:
                d_app = app_matches[v]
                break

        d_spo = None
        for v in item["spouse_variants"]:
            if v in app_matches:
                d_spo = app_matches[v]
                break
            elif v in spouse_matches and len(spouse_matches[v]) == 1:
                d_spo = spouse_matches[v][0]
                break

        if d_app and d_spo and d_app.id != d_spo.id:
            item["reasons"].append("کد ملی متقاضی و همسر متعلق به دو پرونده متفاوت است (تناقض در اطلاعات).")
            errors.append(item)
            continue

        # Safeguard: Typo in applicant national ID (no silent fallback to spouse)
        has_applicant_col_val = bool(item["raw_nid"] and clean_digits(item["raw_nid"]).strip("0") != "")
        if has_applicant_col_val and not d_app:
            # Check if applicant NID matched in spouse field
            matched_app_in_spouse = any(v in spouse_matches for v in item["app_variants"])
            if not matched_app_in_spouse:
                item["reasons"].append("کد ملی متقاضی در سامانه یافت نشد.")
                errors.append(item)
                continue

        dossier = None
        matched_via = None

        # 1. Search applicant national ID in DB applicant field
        for v in item["app_variants"]:
            if v in app_matches:
                dossier = app_matches[v]
                matched_via = "applicant"
                break

        # 2. If not found, search applicant national ID in DB spouse field
        if not dossier:
            for v in item["app_variants"]:
                if v in spouse_matches:
                    s_list = spouse_matches[v]
                    if len(s_list) > 1:
                        item["reasons"].append("کد ملی متقاضی به عنوان همسر در چندین پرونده مختلف ثبت شده است (ابهام در شناسایی پرونده).")
                        break
                    dossier = s_list[0]
                    matched_via = "spouse"
                    break

        # 3. If not found, take spouse national ID from row and search in DB applicant field
        if not dossier and not item["reasons"] and item["spouse_variants"]:
            for v in item["spouse_variants"]:
                if v in app_matches:
                    dossier = app_matches[v]
                    matched_via = "spouse_as_applicant"
                    break

        # 4. If not found, search spouse national ID from row in DB spouse field
        if not dossier and not item["reasons"] and item["spouse_variants"]:
            for v in item["spouse_variants"]:
                if v in spouse_matches:
                    s_list = spouse_matches[v]
                    if len(s_list) > 1:
                        item["reasons"].append("کد ملی همسر در چندین پرونده مختلف ثبت شده است (ابهام در شناسایی پرونده).")
                        break
                    dossier = s_list[0]
                    matched_via = "spouse"
                    break

        # Check cross-dossier ambiguity where NID is applicant in dossier A and spouse in dossier B
        if dossier and not item["reasons"]:
            primary_v = item["app_variants"][0] if item["app_variants"] else (item["spouse_variants"][0] if item["spouse_variants"] else None)
            if primary_v and primary_v in app_matches and primary_v in spouse_matches:
                # If they belong to two different dossiers, reject as ambiguous
                if any(s.id != app_matches[primary_v].id for s in spouse_matches[primary_v]):
                    item["reasons"].append("کد ملی همزمان در یک پرونده به عنوان متقاضی و در پرونده‌ای دیگر به عنوان همسر ثبت شده است (ابهام در شناسایی).")
                    errors.append(item)
                    continue

        if not dossier and not item["reasons"]:
            item["reasons"].append("کد ملی متقاضی و همسر در سامانه یافت نشد.")
            errors.append(item)
            continue

        if item["reasons"]:
            errors.append(item)
            continue

        # Check locked dossiers
        if dossier.is_locked and not is_admin:
            item["reasons"].append(f"پرونده {dossier.archive_number} مختومه و قفل است و دسترسی ویرایش ندارید.")
            errors.append(item)
            continue

        # Duplicate row handling & Applicant priority over spouse
        if dossier.id in seen_dossiers_info:
            prev_info = seen_dossiers_info[dossier.id]
            if prev_info["matched_via"] in ("spouse", "spouse_as_applicant") and matched_via == "applicant":
                # Current applicant row takes priority over previous spouse row!
                prev_record = prev_info["record"]
                # Convert previous record to error
                errors.append({
                    "row": prev_info["row"],
                    "national_id": prev_info["national_id"],
                    "reasons": ["پرونده قبلاً در همین فایل بروزرسانی شده است (تکرار پرونده یا زوجین)."]
                })
                warnings.append(f"ردیف {item['row']} به دلیل اولویت متقاضی اصلی جایگزین ردیف همسر قبلی شد.")
                # Rollback previous diffs from valid lists
                if prev_record in valid_updated_records:
                    valid_updated_records.remove(prev_record)
                if prev_info.get("preview_entry") in updates_preview:
                    updates_preview.remove(prev_info["preview_entry"])
                if prev_info.get("preview_entry") in spouse_matched_rows:
                    spouse_matched_rows.remove(prev_info["preview_entry"])
                if prev_info.get("had_diffs"):
                    updated_count -= 1
                    if dossier in dossiers_to_update:
                        dossiers_to_update.remove(dossier)
                else:
                    unchanged_count -= 1
                valid_count -= 1
            else:
                item["reasons"].append("پرونده قبلاً در همین فایل بروزرسانی شده است (تکرار پرونده یا زوجین).")
                errors.append(item)
                continue

        valid_count += 1
        item["name"] = dossier.full_name
        item["archive_number"] = dossier.archive_number

        raw_data = dict(item["data"])

        # Auto-compute base_cost_without_loan if total_price is present
        if "total_price" in raw_data:
            tot_price = raw_data.pop("total_price")
            if tot_price and tot_price > 0:
                loan_val = raw_data.get("bank_loan_amount") or dossier.bank_loan_amount or 6500000000
                if "bank_loan_amount" not in raw_data and not dossier.bank_loan_amount:
                    raw_data["bank_loan_amount"] = loan_val
                if tot_price >= loan_val:
                    raw_data["base_cost_without_loan"] = tot_price - loan_val

        # Check collision when updating spouse_national_id
        if "spouse_national_id" in raw_data:
            new_snid = raw_data["spouse_national_id"]
            if new_snid and new_snid == dossier.national_id:
                # User copied applicant NID into spouse column: keep spouse untouched
                raw_data.pop("spouse_national_id", None)
                warnings.append(f"کد ملی همسر با کد ملی متقاضی در ردیف {item['row']} یکسان درج شده است و نادیده گرفته شد.")
            elif new_snid and any(
                v in app_matches and app_matches[v].id != dossier.id
                for v in get_national_id_variants(new_snid)
            ):
                item["reasons"].append(f"کد ملی همسر {new_snid} قبلاً به عنوان متقاضی در پرونده دیگری ثبت شده است.")
                errors.append(item)
                valid_count -= 1
                continue

        # Protect identity fields & handle Form J orientation if matched via spouse
        data_to_apply = raw_data
        if matched_via in ("spouse", "spouse_as_applicant"):
            if "applicant_form_j_status" in data_to_apply:
                data_to_apply["spouse_form_j_status"] = data_to_apply.pop("applicant_form_j_status")
                item["labels"]["spouse_form_j_status"] = "وضعیت فرم ج همسر"
            if "applicant_form_j_directorate_status" in data_to_apply:
                data_to_apply["spouse_form_j_directorate_status"] = data_to_apply.pop("applicant_form_j_directorate_status")
                item["labels"]["spouse_form_j_directorate_status"] = "استعلام اداره کل همسر"
            if "applicant_form_j_red_description" in data_to_apply:
                data_to_apply["spouse_form_j_red_description"] = data_to_apply.pop("applicant_form_j_red_description")
                item["labels"]["spouse_form_j_red_description"] = "علت کد قرمز فرم ج همسر"

            if "applicant_phone" in data_to_apply:
                data_to_apply.pop("applicant_phone")
                warnings.append(f"شماره تماس متقاضی در ردیف {item['row']} به دلیل تطبیق از طریق همسر نادیده گرفته شد.")

            for id_field in IDENTITY_FIELDS:
                data_to_apply.pop(id_field, None)

        diffs: List[Dict[str, Any]] = []
        for f_name, new_val in data_to_apply.items():
            old_val = getattr(dossier, f_name, None)
            if old_val != new_val:
                label = item["labels"].get(f_name) or PERSIAN_FIELD_LABELS.get(f_name, f_name)
                diffs.append({
                    "field": f_name,
                    "label": label,
                    "old": str(old_val) if old_val is not None else "",
                    "new": str(new_val) if new_val is not None else "",
                })
                setattr(dossier, f_name, new_val)
                modified_fields_set.add(f_name)

        had_diffs = bool(diffs)
        if not diffs:
            unchanged_count += 1
        else:
            updated_count += 1
            explicit_keys = set(data_to_apply.keys())
            dossier.recompute_derived_fields(skip=explicit_keys)
            dossiers_to_update.append(dossier)
            field_changes_by_dossier[dossier.id] = diffs

        preview_entry = {
            "row": item["row"],
            "national_id": nid,
            "name": dossier.full_name,
            "archive_number": dossier.archive_number,
            "matched_via": matched_via,
            "diff_display": diffs,
        }
        if matched_via in ("spouse", "spouse_as_applicant"):
            spouse_matched_rows.append(preview_entry)

        if len(updates_preview) < 50:
            updates_preview.append(preview_entry)

        record_entry = {
            "item": item,
            "dossier": dossier,
            "diffs": diffs,
        }
        valid_updated_records.append(record_entry)

        seen_dossiers_info[dossier.id] = {
            "matched_via": matched_via,
            "row": item["row"],
            "national_id": nid,
            "record": record_entry,
            "preview_entry": preview_entry,
            "had_diffs": had_diffs
        }

    report_url = None
    if errors:
        r_uuid = generate_failure_report(user.id, raw_headers, errors, spouse_matched_rows)
        report_url = f"/excel/report/{r_uuid}/"

    success_report_url = None
    if valid_updated_records:
        success_rows = []
        for rec in valid_updated_records:
            d = rec["dossier"]
            it = rec["item"]
            dfs = rec["diffs"]
            diff_text = " ، ".join([f"{df['label']}: {df['old']} -> {df['new']}" for df in dfs]) if dfs else "بدون تغییر داده"
            success_rows.append({
                "row": it.get("row", ""),
                "archive_number": d.archive_number,
                "national_id": d.national_id,
                "name": d.full_name,
                "status": "بروزرسانی شد" if dfs else "بدون تغییر",
                "diff_summary": diff_text,
                "original_cells": it.get("original_cells", []),
            })
        s_uuid = generate_success_report(user.id, raw_headers, success_rows, title="پرونده‌های بروزرسانی‌شده")
        success_report_url = f"/excel/report/{s_uuid}/"

    if preview:
        return {
            "success": True,
            "error": None,
            "preview": True,
            "created_count": 0,
            "updated_count": updated_count,
            "valid_count": valid_count,
            "unchanged_count": unchanged_count,
            "failed_count": len(errors),
            "matched_via_spouse_count": len(spouse_matched_rows),
            "warnings": warnings,
            "report_url": report_url,
            "success_report_url": success_report_url,
            "errors": errors[:100],
            "updates_preview": updates_preview,
        }

    # Confirm mode: Bulk update modified dossiers
    if dossiers_to_update:
        now_dt = timezone.now()
        for d in dossiers_to_update:
            d.updated_at = now_dt

        # Ensure derived fields are saved
        candidate_fields = modified_fields_set.union({
            "updated_at", "applicant_equity", "check_service_fee",
            "full_name", "first_name", "last_name",
            "spouse_full_name", "spouse_first_name", "spouse_last_name",
            "bank_name", "project_code", "bank_branch",
            "total_land_share", "current_year_rent", "past_years_rent",
            "preparation_cost", "land_lease_year",
            "main_plaque", "separated_plaque", "sub_plaque", "plot_number",
            "unit_area"
        })
        model_fields = {f.name for f in HousingDossier._meta.get_fields() if hasattr(f, "column")}
        all_update_fields = list(candidate_fields.intersection(model_fields))

        # Safe batch size to prevent SQLite 'too many SQL variables' (max 32766 variables)
        SAFE_BATCH_SIZE = max(10, min(100, 25000 // (2 * max(1, len(all_update_fields)) + 1)))

        for i in range(0, len(dossiers_to_update), SAFE_BATCH_SIZE):
            chunk = dossiers_to_update[i : i + SAFE_BATCH_SIZE]
            with transaction.atomic():
                HousingDossier.objects.bulk_update(chunk, fields=all_update_fields)

        # Audit logs and field change logs
        actor_name = profile.full_name if profile and profile.full_name else (user.get_full_name() or user.username)
        actor_role = profile.role_title if profile and profile.role_title else "مدیر سیستم"

        sig_logs = []
        change_logs = []
        for d in dossiers_to_update:
            diffs = field_changes_by_dossier.get(d.id, [])
            changed_labels = [diff["label"] for diff in diffs]
            notes = f"بروزرسانی فیلدهای: {', '.join(changed_labels)}" if changed_labels else "بروزرسانی از طریق اکسل"
            s_hash = "SHA256: " + hashlib.sha256(f"EXCEL_UPDATE:{d.id}:{uuid.uuid4()}".encode()).hexdigest()[:24]

            sig_logs.append(WorkflowSignatureLog(
                dossier=d,
                from_stage=f"مرحله {d.current_stage}: {d.current_stage_title}",
                to_stage=f"مرحله {d.current_stage}: {d.current_stage_title}",
                actor=actor_name,
                role=actor_role,
                action="EXCEL_UPDATE",
                action_label="بروزرسانی گروهی از طریق اکسل",
                signature_hash=s_hash,
                notes=notes
            ))

            for diff in diffs:
                change_logs.append(DossierFieldChangeLog(
                    dossier=d,
                    field_name=diff["field"],
                    field_label=diff["label"],
                    old_value=diff["old"],
                    new_value=diff["new"],
                    changed_by=user,
                    stage=d.current_stage
                ))

        for i in range(0, len(sig_logs), 200):
            WorkflowSignatureLog.objects.bulk_create(sig_logs[i : i + 200])
        for i in range(0, len(change_logs), 200):
            DossierFieldChangeLog.objects.bulk_create(change_logs[i : i + 200])

    return {
        "success": True,
        "error": None,
        "preview": False,
        "created_count": 0,
        "updated_count": updated_count,
        "valid_count": valid_count,
        "unchanged_count": unchanged_count,
        "failed_count": len(errors),
        "matched_via_spouse_count": len(spouse_matched_rows),
        "warnings": warnings,
        "report_url": report_url,
        "success_report_url": success_report_url,
        "errors": errors[:100],
        "updates_preview": updates_preview,
    }

def process_excel_group_sign(file_obj: Any, user: Any, preview: bool = False, is_preview: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
    if is_preview is not None:
        preview = is_preview
    from .views import execute_dossier_sign
    from .stages import STAGE_ROLES, MAX_STAGE

    profile = getattr(user, "profile", None)
    is_admin = user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    if not is_admin and (not profile or not profile.can_sign):
        return {"success": False, "error": "حق امضای الکترونیکی برای حساب کاربری شما فعال نیست."}

    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    except Exception as e:
        return {"success": False, "error": f"فایل اکسل نامعتبر است: {str(e)}"}

    ws = wb.worksheets[0]
    all_rows = list(ws.iter_rows(values_only=True))

    if not all_rows:
        return {"success": False, "error": "فایل اکسل خالی است."}

    header_row = list(all_rows[0] or [])
    data_rows = all_rows[1:]

    # Detect header columns
    nid_col: Optional[int] = None
    notes_col: Optional[int] = None
    stage_cols: Dict[int, int] = {}  # col_idx -> stage_number (1..22)
    legacy_single_stg_col: Optional[int] = None

    for idx, h in enumerate(header_row):
        if h is None:
            continue
        h_str = str(h).strip()
        norm = normalize_header(h_str)

        if norm in ("کد ملی متقاضی", "کدملی متقاضی", "کد ملی", "کدملی", "national_id", "national id"):
            nid_col = idx
            continue

        if any(k in norm for k in ("توضیح", "یادداشت", "notes", "شرح")):
            notes_col = idx
            continue

        h_digits = clean_digits(h_str)
        m_stg = re.search(r"مرحله\s*(\d+)", h_digits)
        if m_stg:
            s_num = int(m_stg.group(1))
            if 1 <= s_num <= MAX_STAGE:
                stage_cols[idx] = s_num
                continue

        if h_digits.isdigit():
            s_num = int(h_digits)
            if 1 <= s_num <= MAX_STAGE:
                stage_cols[idx] = s_num
                continue

        if norm in ("شماره مرحله", "مرحله", "مرحله گردش کار"):
            legacy_single_stg_col = idx

    if nid_col is None and header_row:
        if 0 not in stage_cols and 0 != notes_col:
            nid_col = 0

    if nid_col is None:
        return {"success": False, "error": "ستون «کد ملی متقاضی» در فایل اکسل یافت نشد."}

    # -------------------------------------------------------------------------
    # Format A: Matrix Format (National ID in Col 1, Stage 1..22 in Headers)
    # -------------------------------------------------------------------------
    if stage_cols:
        parsed_rows: List[Dict[str, Any]] = []
        all_nids: Set[str] = set()
        errors: List[Dict[str, Any]] = []

        for row_num, row_cells in enumerate(data_rows, start=2):
            if not any(c is not None and str(c).strip() for c in row_cells):
                continue

            raw_nid = row_cells[nid_col] if nid_col < len(row_cells) else None
            cleaned_nid = clean_national_id(raw_nid)
            app_variants = get_national_id_variants(raw_nid)

            row_errors: List[str] = []
            if not app_variants:
                row_errors.append("کد ملی متقاضی نامعتبر یا خالی است.")
            else:
                all_nids.update(app_variants)

            marked_stages: List[int] = []
            for c_idx, s_num in stage_cols.items():
                if c_idx < len(row_cells):
                    val = row_cells[c_idx]
                    if val is not None:
                        s_val = clean_digits(val).strip().lower()
                        if s_val in ("1", "1.0", "true", "تایید", "امضا", "yes", "بله", "✓", "+") or val in (1, 1.0, True):
                            marked_stages.append(s_num)

            if not row_errors and not marked_stages:
                row_errors.append("هیچ مرحله‌ای با درج عدد ۱ برای امضا مشخص نشده است.")

            row_notes = ""
            if notes_col is not None and notes_col < len(row_cells) and row_cells[notes_col] is not None:
                row_notes = str(row_cells[notes_col]).strip()

            parsed_rows.append({
                "row": row_num,
                "raw_nid": raw_nid,
                "cleaned_nid": cleaned_nid or str(raw_nid or ""),
                "app_variants": app_variants,
                "marked_stages": sorted(list(set(marked_stages))),
                "notes": row_notes,
                "original_cells": list(row_cells),
                "reasons": row_errors,
            })

        app_matches: Dict[str, HousingDossier] = {}
        spouse_matches: Dict[str, List[HousingDossier]] = {}
        loaded_pks: Set[int] = set()

        all_nids_list = list(all_nids)
        for i in range(0, len(all_nids_list), CHUNK_QUERY_SIZE):
            chunk = all_nids_list[i : i + CHUNK_QUERY_SIZE]
            for d in HousingDossier.objects.filter(Q(national_id__in=chunk) | Q(spouse_national_id__in=chunk)):
                if d.pk in loaded_pks:
                    continue
                loaded_pks.add(d.pk)
                for v in get_national_id_variants(d.national_id):
                    app_matches[v] = d
                for v in get_national_id_variants(d.spouse_national_id):
                    spouse_matches.setdefault(v, []).append(d)

        seen_dossier_ids: Set[int] = set()
        valid_count = 0
        failed_count = 0
        signed_dossiers_info: List[Dict[str, Any]] = []
        updates_preview: List[Dict[str, Any]] = []

        for item in parsed_rows:
            if item["reasons"]:
                failed_count += 1
                errors.append({
                    "row": item["row"],
                    "national_id": item["cleaned_nid"],
                    "name": "-",
                    "archive_number": "-",
                    "reasons": item["reasons"],
                    "original_cells": item["original_cells"]
                })
                continue

            dossier: Optional[HousingDossier] = None
            for v in item["app_variants"]:
                if v in app_matches:
                    dossier = app_matches[v]
                    break
            if not dossier:
                for v in item["app_variants"]:
                    if v in spouse_matches:
                        s_list = spouse_matches[v]
                        if len(s_list) > 1:
                            break
                        dossier = s_list[0]
                        break

            if not dossier:
                failed_count += 1
                errors.append({
                    "row": item["row"],
                    "national_id": item["cleaned_nid"],
                    "name": "-",
                    "archive_number": "-",
                    "reasons": ["پرونده‌ای با این کد ملی در سامانه یافت نشد."],
                    "original_cells": item["original_cells"]
                })
                continue

            item["name"] = dossier.full_name
            item["archive_number"] = dossier.archive_number

            if dossier.id in seen_dossier_ids:
                failed_count += 1
                errors.append({
                    "row": item["row"],
                    "national_id": dossier.national_id,
                    "name": dossier.full_name,
                    "archive_number": dossier.archive_number,
                    "reasons": ["پرونده بیش از یک بار در این فایل تکرار شده است."],
                    "original_cells": item["original_cells"]
                })
                continue
            seen_dossier_ids.add(dossier.id)

            if dossier.is_locked:
                failed_count += 1
                errors.append({
                    "row": item["row"],
                    "national_id": dossier.national_id,
                    "name": dossier.full_name,
                    "archive_number": dossier.archive_number,
                    "reasons": ["پرونده مختومه و قفل است."],
                    "original_cells": item["original_cells"]
                })
                continue

            if dossier.status == "COMPLETED":
                failed_count += 1
                errors.append({
                    "row": item["row"],
                    "national_id": dossier.national_id,
                    "name": dossier.full_name,
                    "archive_number": dossier.archive_number,
                    "reasons": ["پرونده قبلاً خاتمه یافته است."],
                    "original_cells": item["original_cells"]
                })
                continue

            stg_errors: List[str] = []
            for stg in item["marked_stages"]:
                can_sign_stage = is_admin or bool(profile and profile.can_action_stage(stg))
                if not can_sign_stage:
                    stg_title = STAGE_ROLES.get(stg, ("", "", f"مرحله {stg}"))[2]
                    stg_errors.append(f"کاربر جاری دسترسی لازم برای امضای مرحله {stg} ({stg_title}) را ندارد.")

                if stg == 3:
                    is_red_j = (
                        ("قرمز" in (dossier.applicant_form_j_status or "")) or
                        ("قرمز" in (dossier.spouse_form_j_status or "")) or
                        dossier.status == "REJECTED_RED"
                    )
                    if is_red_j:
                        stg_errors.append("وضعیت استعلام فرم «ج» پرونده قرمز (دارای سابقه مسکن / عدم احراز صلاحیت) است و امکان تایید و امضای مرحله ۳ وجود ندارد.")

            if stg_errors:
                failed_count += 1
                errors.append({
                    "row": item["row"],
                    "national_id": dossier.national_id,
                    "name": dossier.full_name,
                    "archive_number": dossier.archive_number,
                    "reasons": stg_errors,
                    "original_cells": item["original_cells"]
                })
                continue

            orig_stage = dossier.current_stage
            orig_stage_title = STAGE_ROLES.get(orig_stage, ("", "", f"مرحله {orig_stage}"))[2]

            if preview:
                sim_stage = orig_stage
                signed_labels = []
                for stg in item["marked_stages"]:
                    signed_labels.append(f"مرحله {stg}")
                    sim_stage = dossier.find_next_actionable_stage(stg)

                target_stage_title = STAGE_ROLES.get(sim_stage, ("", "", f"مرحله {sim_stage}"))[2] if sim_stage <= MAX_STAGE else "بایگانی نهایی (مختومه)"
                valid_count += 1
                signed_dossiers_info.append({
                    "row": item["row"],
                    "archive_number": dossier.archive_number,
                    "national_id": dossier.national_id,
                    "name": dossier.full_name,
                    "from_stage": f"مرحله {orig_stage}: {orig_stage_title}",
                    "to_stage": target_stage_title,
                    "stages_signed": "، ".join(signed_labels)
                })
                if len(updates_preview) < 50:
                    updates_preview.append({
                        "row": item["row"],
                        "archive_number": dossier.archive_number,
                        "national_id": dossier.national_id,
                        "name": dossier.full_name,
                        "from_stage": f"مرحله {orig_stage}",
                        "to_stage": target_stage_title,
                        "diff_display": [{
                            "field": "current_stage",
                            "label": f"امضای {len(signed_labels)} مرحله ({', '.join(signed_labels)})",
                            "old": f"مرحله {orig_stage}: {orig_stage_title}",
                            "new": target_stage_title
                        }]
                    })
            else:
                sid = transaction.savepoint()
                row_failed = False
                row_exec_errors = []
                signed_labels = []

                for stg in item["marked_stages"]:
                    note_text = item["notes"] or f"امضای گروهی مرحله {stg} از طریق اکسل"
                    ok, res_stage = execute_dossier_sign(
                        dossier=dossier,
                        user=user,
                        notes=note_text,
                        action="SIGN_EXCEL",
                        target_stage=stg
                    )
                    if ok:
                        signed_labels.append(f"مرحله {stg}")
                    else:
                        row_failed = True
                        row_exec_errors.append(str(res_stage))
                        break

                if row_failed:
                    transaction.savepoint_rollback(sid)
                    failed_count += 1
                    errors.append({
                        "row": item["row"],
                        "national_id": dossier.national_id,
                        "name": dossier.full_name,
                        "archive_number": dossier.archive_number,
                        "reasons": row_exec_errors,
                        "original_cells": item["original_cells"]
                    })
                else:
                    transaction.savepoint_commit(sid)
                    valid_count += 1
                    dossier.refresh_from_db()
                    end_stage = dossier.current_stage
                    end_stage_title = STAGE_ROLES.get(end_stage, ("", "", f"مرحله {end_stage}"))[2] if not dossier.is_locked else "بایگانی نهایی (مختومه)"

                    signed_dossiers_info.append({
                        "row": item["row"],
                        "archive_number": dossier.archive_number,
                        "national_id": dossier.national_id,
                        "name": dossier.full_name,
                        "from_stage": f"مرحله {orig_stage}: {orig_stage_title}",
                        "to_stage": end_stage_title,
                        "stages_signed": "، ".join(signed_labels)
                    })
                    if len(updates_preview) < 50:
                        updates_preview.append({
                            "row": item["row"],
                            "archive_number": dossier.archive_number,
                            "national_id": dossier.national_id,
                            "name": dossier.full_name,
                            "from_stage": f"مرحله {orig_stage}",
                            "to_stage": end_stage_title,
                            "diff_display": [{
                                "field": "current_stage",
                                "label": f"امضای {len(signed_labels)} مرحله ({', '.join(signed_labels)})",
                                "old": f"مرحله {orig_stage}: {orig_stage_title}",
                                "new": end_stage_title
                            }]
                        })

        report_url = None
        if errors:
            r_uuid = generate_failure_report(user.id, ["ردیف", "شماره بایگانی", "کد ملی", "نام متقاضی", "علت رد"], errors)
            report_url = f"/excel/report/{r_uuid}/"

        success_report_url = None
        if valid_count > 0 and not preview:
            success_rows = [
                {
                    "row": item["row"],
                    "archive_number": item["archive_number"],
                    "national_id": item["national_id"],
                    "name": item["name"],
                    "status": "تایید و امضا شد",
                    "notes": f"مراحل امضا شده: {item.get('stages_signed', '')} | انتقال از {item.get('from_stage', '')} به {item.get('to_stage', '')}",
                    "original_cells": []
                }
                for item in signed_dossiers_info
            ]
            s_uuid = generate_success_report(user.id, ["مراحل امضاشده", "مرحله مقصد"], success_rows, title="امضاهای تاییدشده")
            success_report_url = f"/excel/report/{s_uuid}/"

        return {
            "success": True,
            "error": None,
            "preview": preview,
            "created_count": 0,
            "updated_count": valid_count,
            "signed_count": valid_count,
            "valid_count": valid_count,
            "unchanged_count": 0,
            "failed_count": failed_count,
            "matched_via_spouse_count": 0,
            "warnings": [],
            "report_url": report_url,
            "success_report_url": success_report_url,
            "errors": errors[:100],
            "updates_preview": updates_preview,
        }

    # -------------------------------------------------------------------------
    # Format B: Legacy Single Stage Column Fallback (کد ملی متقاضی، مرحله، توضیحات)
    # -------------------------------------------------------------------------
    if legacy_single_stg_col is None:
        return {"success": False, "error": "ستون‌های مرحله (مرحله ۱ تا ۲۲) در سربرگ اکسل یافت نشد."}

    parsed_rows: List[Dict[str, Any]] = []
    all_nids: Set[str] = set()
    errors: List[Dict[str, Any]] = []

    for row_num, row_cells in enumerate(data_rows, start=2):
        if not any(c is not None and str(c).strip() for c in row_cells):
            continue

        raw_nid = row_cells[nid_col] if nid_col < len(row_cells) else None
        cleaned_nid = clean_national_id(raw_nid)

        req_stage = None
        if legacy_single_stg_col is not None and legacy_single_stg_col < len(row_cells) and row_cells[legacy_single_stg_col] is not None:
            s_val = clean_digits(row_cells[legacy_single_stg_col])
            m_stg = re.search(r"\d+", s_val)
            if m_stg:
                req_stage = int(m_stg.group(0))

        notes = ""
        if notes_col is not None and notes_col < len(row_cells) and row_cells[notes_col] is not None:
            notes = str(row_cells[notes_col]).strip()

        row_errors: List[str] = []
        if not cleaned_nid:
            row_errors.append("کد ملی نامعتبر یا خالی است.")
        else:
            all_nids.add(cleaned_nid)

        parsed_rows.append({
            "row": row_num,
            "national_id": cleaned_nid or str(raw_nid or ""),
            "req_stage": req_stage,
            "notes": notes,
            "original_cells": list(row_cells),
            "reasons": row_errors,
        })

    app_matches = {}
    spouse_matches = {}

    all_nids_list = list(all_nids)
    for i in range(0, len(all_nids_list), CHUNK_QUERY_SIZE):
        chunk = all_nids_list[i : i + CHUNK_QUERY_SIZE]
        for d in HousingDossier.objects.filter(national_id__in=chunk):
            app_matches[d.national_id] = d
        for d in HousingDossier.objects.filter(spouse_national_id__in=chunk).exclude(spouse_national_id=""):
            spouse_matches.setdefault(d.spouse_national_id, []).append(d)

    seen_dossier_ids = set()
    updates_preview = []
    valid_sign_tasks = []

    for item in parsed_rows:
        nid = item["national_id"]
        if item["reasons"]:
            errors.append(item)
            continue

        d_as_app = app_matches.get(nid)
        d_as_spouses = spouse_matches.get(nid, [])

        if d_as_app and d_as_spouses:
            item["reasons"].append("کد ملی دارای ابهام در انطباق است.")
            errors.append(item)
            continue
        elif not d_as_app and len(d_as_spouses) > 1:
            item["reasons"].append("کد ملی به عنوان همسر در چندین پرونده وجود دارد.")
            errors.append(item)
            continue
        elif not d_as_app and not d_as_spouses:
            item["reasons"].append("پرونده‌ای با این کد ملی یافت نشد.")
            errors.append(item)
            continue

        dossier = d_as_app if d_as_app else d_as_spouses[0]
        item["name"] = dossier.full_name

        if dossier.id in seen_dossier_ids:
            item["reasons"].append("این پرونده قبلاً در همین فایل بررسی شده است.")
            errors.append(item)
            continue
        seen_dossier_ids.add(dossier.id)

        target_stage = item["req_stage"] if item["req_stage"] is not None else dossier.current_stage

        if dossier.is_locked:
            item["reasons"].append("پرونده مختومه و قفل است.")
            errors.append(item)
            continue

        if dossier.status != "IN_PROGRESS":
            item["reasons"].append(f"وضعیت پرونده ({dossier.get_status_display()}) در جریان اقدام نیست.")
            errors.append(item)
            continue

        if target_stage != dossier.current_stage:
            item["reasons"].append(f"مرحله فعلی پرونده {dossier.current_stage} است اما در فایل مرحله {target_stage} قید شده است.")
            errors.append(item)
            continue

        is_allowed = user.is_superuser or (profile and profile.is_housing_chief) or (profile and profile.can_action_stage(target_stage))
        if not is_allowed:
            item["reasons"].append(f"شما دسترسی اقدام و امضا در مرحله {target_stage} را ندارید.")
            errors.append(item)
            continue

        if target_stage in dossier.get_signed_stages_set():
            item["reasons"].append(f"مرحله {target_stage} قبلاً برای این پرونده امضا و تایید شده است.")
            errors.append(item)
            continue

        next_stage = dossier.find_next_actionable_stage(target_stage)
        valid_sign_tasks.append((dossier, target_stage, item["notes"], item))

        if len(updates_preview) < 50:
            updates_preview.append({
                "row": item["row"],
                "national_id": nid,
                "name": dossier.full_name,
                "archive_number": dossier.archive_number,
                "diff_display": [{
                    "field": "current_stage",
                    "label": "انتقال مرحله",
                    "old": f"مرحله {target_stage}",
                    "new": f"مرحله {next_stage}" if next_stage <= MAX_STAGE else "بایگانی نهایی (مختومه)",
                }]
            })

    report_url = None
    if errors:
        r_uuid = generate_failure_report(user.id, header_row, errors)
        report_url = f"/excel/report/{r_uuid}/"

    if preview:
        return {
            "success": True,
            "error": None,
            "preview": True,
            "created_count": 0,
            "updated_count": len(valid_sign_tasks),
            "signed_count": len(valid_sign_tasks),
            "valid_count": len(valid_sign_tasks),
            "unchanged_count": 0,
            "failed_count": len(errors),
            "matched_via_spouse_count": 0,
            "warnings": [],
            "report_url": report_url,
            "success_report_url": None,
            "errors": errors[:100],
            "updates_preview": updates_preview,
        }

    signed_count = 0
    signed_dossiers_info = []

    for dossier, target_stage, note, item in valid_sign_tasks:
        orig_stage = dossier.current_stage
        orig_stage_title = STAGE_ROLES.get(orig_stage, ("", "", f"مرحله {orig_stage}"))[2]
        note_text = note or f"امضای گروهی مرحله {target_stage} از طریق اکسل"

        ok, res_stage = execute_dossier_sign(
            dossier=dossier,
            user=user,
            notes=note_text,
            action="SIGN_EXCEL",
            target_stage=target_stage
        )
        if ok:
            signed_count += 1
            dossier.refresh_from_db()
            end_stage = dossier.current_stage
            end_stage_title = STAGE_ROLES.get(end_stage, ("", "", f"مرحله {end_stage}"))[2] if not dossier.is_locked else "بایگانی نهایی (مختومه)"
            signed_dossiers_info.append({
                "archive_number": dossier.archive_number,
                "national_id": dossier.national_id,
                "name": dossier.full_name,
                "from_stage": f"مرحله {orig_stage}: {orig_stage_title}",
                "to_stage": end_stage_title
            })
        else:
            item["reasons"].append(str(res_stage))
            errors.append(item)

    success_report_url = None
    if signed_count > 0:
        success_rows = [
            {
                "row": item.get("from_stage", ""),
                "archive_number": item["archive_number"],
                "national_id": item["national_id"],
                "name": item["name"],
                "status": "تایید و امضا شد",
                "notes": f"انتقال از {item.get('from_stage', '')} به {item.get('to_stage', '')}",
                "original_cells": []
            }
            for item in signed_dossiers_info
        ]
        s_uuid = generate_success_report(user.id, ["مرحله مبدأ", "مرحله مقصد"], success_rows, title="امضاهای تاییدشده")
        success_report_url = f"/excel/report/{s_uuid}/"

    return {
        "success": True,
        "error": None,
        "preview": False,
        "created_count": 0,
        "updated_count": signed_count,
        "signed_count": signed_count,
        "valid_count": signed_count,
        "unchanged_count": 0,
        "failed_count": len(errors),
        "matched_via_spouse_count": 0,
        "warnings": [],
        "report_url": report_url,
        "success_report_url": success_report_url,
        "errors": errors[:100],
        "updates_preview": updates_preview,
    }



def process_excel_spouse_swap(file_obj: Any, user: Any, preview: bool = False, is_preview: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
    if is_preview is not None:
        preview = is_preview
    profile = getattr(user, "profile", None)
    is_admin = user.is_superuser or user.is_staff or (profile and profile.is_housing_chief)
    if not is_admin:
        return {"success": False, "error": "شما دسترسی مجاز برای جابجایی متقاضی با همسر را ندارید."}

    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    except Exception as e:
        return {"success": False, "error": f"فایل اکسل نامعتبر است: {str(e)}"}

    ws = wb.worksheets[0]
    row_iter = ws.iter_rows(values_only=True)

    try:
        header_row = next(row_iter)
    except StopIteration:
        return {"success": False, "error": "فایل اکسل خالی است."}

    raw_headers = list(header_row or [])
    nid_col: Optional[int] = None
    for idx, h in enumerate(raw_headers):
        norm = normalize_header(h)
        if "کد ملی" in norm or "کدملی" in norm:
            nid_col = idx
            break

    if nid_col is None:
        nid_col = 0  # fallback to first column

    parsed_rows: List[Dict[str, Any]] = []
    all_nids: Set[str] = set()
    errors: List[Dict[str, Any]] = []

    row_num = 1
    for row_cells in row_iter:
        row_num += 1
        if not any(c is not None and str(c).strip() for c in row_cells):
            continue

        raw_nid = row_cells[nid_col] if nid_col < len(row_cells) else None
        cleaned_nid = clean_national_id(raw_nid)

        row_errors: List[str] = []
        if not cleaned_nid:
            row_errors.append("کد ملی نامعتبر یا خالی است.")
        else:
            all_nids.add(cleaned_nid)

        parsed_rows.append({
            "row": row_num,
            "national_id": cleaned_nid or str(raw_nid or ""),
            "original_cells": list(row_cells),
            "reasons": row_errors,
        })

    # Preload dossiers
    app_matches: Dict[str, HousingDossier] = {}
    spouse_matches: Dict[str, List[HousingDossier]] = {}

    all_nids_list = list(all_nids)
    for i in range(0, len(all_nids_list), CHUNK_QUERY_SIZE):
        chunk = all_nids_list[i : i + CHUNK_QUERY_SIZE]
        for d in HousingDossier.objects.filter(national_id__in=chunk):
            app_matches[d.national_id] = d
        for d in HousingDossier.objects.filter(spouse_national_id__in=chunk).exclude(spouse_national_id=""):
            spouse_matches.setdefault(d.spouse_national_id, []).append(d)

    seen_dossier_ids: Set[int] = set()
    valid_swap_rows: List[Tuple[HousingDossier, Dict[str, Any], str]] = []
    updates_preview: List[Dict[str, Any]] = []

    # Collect candidate spouse IDs to check conflicts against existing applicant IDs
    candidate_spouses_to_check: Set[str] = set()
    for item in parsed_rows:
        nid = item["national_id"]
        if item["reasons"]:
            continue
        d = app_matches.get(nid) or (spouse_matches.get(nid, [None])[0])
        if d and d.spouse_national_id:
            candidate_spouses_to_check.add(d.spouse_national_id)

    conflict_spouses_in_db: Dict[str, int] = {}
    if candidate_spouses_to_check:
        c_list = list(candidate_spouses_to_check)
        for i in range(0, len(c_list), CHUNK_QUERY_SIZE):
            chunk = c_list[i : i + CHUNK_QUERY_SIZE]
            for snid, arch in HousingDossier.objects.filter(national_id__in=chunk).values_list("national_id", "archive_number"):
                conflict_spouses_in_db[snid] = arch

    for item in parsed_rows:
        nid = item["national_id"]
        if item["reasons"]:
            errors.append(item)
            continue

        d_as_app = app_matches.get(nid)
        d_as_spouses = spouse_matches.get(nid, [])

        if d_as_app and d_as_spouses:
            item["reasons"].append("کد ملی دارای ابهام در انطباق است.")
            errors.append(item)
            continue
        elif not d_as_app and len(d_as_spouses) > 1:
            item["reasons"].append("کد ملی به عنوان همسر در چندین پرونده وجود دارد.")
            errors.append(item)
            continue
        elif not d_as_app and not d_as_spouses:
            item["reasons"].append("پرونده‌ای با این کد ملی یافت نشد.")
            errors.append(item)
            continue

        dossier = d_as_app if d_as_app else d_as_spouses[0]
        matched_via = "applicant" if d_as_app else "spouse"
        item["name"] = dossier.full_name

        if dossier.id in seen_dossier_ids:
            item["reasons"].append("این پرونده قبلاً در همین فایل جهت جابجایی ثبت شده است.")
            errors.append(item)
            continue
        seen_dossier_ids.add(dossier.id)

        if dossier.is_locked and not is_admin:
            item["reasons"].append("پرونده مختومه و قفل است.")
            errors.append(item)
            continue

        # Spouse validations
        s_nid = clean_national_id(dossier.spouse_national_id)
        if not s_nid:
            item["reasons"].append("کد ملی همسر در این پرونده ثبت نشده یا ۱۰ رقمی نیست.")
            errors.append(item)
            continue

        s_name = (dossier.spouse_full_name or f"{dossier.spouse_first_name or ''} {dossier.spouse_last_name or ''}").strip()
        if not s_name:
            item["reasons"].append("نام و مشخصات هویتی همسر در پرونده ناقص است.")
            errors.append(item)
            continue

        # Check if spouse national_id belongs to another dossier as applicant
        conflict_arch = conflict_spouses_in_db.get(s_nid)
        if conflict_arch and conflict_arch != dossier.archive_number:
            item["reasons"].append(f"کد ملی همسر ({s_nid}) قبلاً به عنوان متقاضی در پرونده {conflict_arch} ثبت شده است.")
            errors.append(item)
            continue

        old_owner_str = f"{dossier.full_name} ({dossier.national_id})"
        new_owner_str = f"{s_name} ({s_nid})"

        valid_swap_rows.append((dossier, item, matched_via))

        if len(updates_preview) < 50:
            updates_preview.append({
                "row": item["row"],
                "national_id": nid,
                "name": dossier.full_name,
                "archive_number": dossier.archive_number,
                "matched_via": matched_via,
                "diff_display": [{
                    "field": "owner_swap",
                    "label": "انتقال مالکیت به همسر",
                    "old": old_owner_str,
                    "new": new_owner_str,
                }]
            })

    report_url = None
    if errors:
        r_uuid = generate_failure_report(user.id, raw_headers, errors)
        report_url = f"/excel/report/{r_uuid}/"

    if preview:
        return {
            "success": True,
            "error": None,
            "preview": True,
            "created_count": 0,
            "updated_count": len(valid_swap_rows),
            "swapped_count": len(valid_swap_rows),
            "valid_count": len(valid_swap_rows),
            "unchanged_count": 0,
            "failed_count": len(errors),
            "matched_via_spouse_count": sum(1 for _, _, m in valid_swap_rows if m == "spouse"),
            "warnings": [],
            "report_url": report_url,
            "errors": errors[:100],
            "updates_preview": updates_preview,
        }

    # Confirm mode: Execute spouse swap
    swapped_count = 0
    actor_name = profile.full_name if profile and profile.full_name else (user.get_full_name() or user.username)
    actor_role = profile.role_title if profile and profile.role_title else "مدیر سیستم"

    for d, item, matched_via in valid_swap_rows:
        try:
            with transaction.atomic():
                # Swap attributes
                for app_f, sp_f in SWAP_FIELD_PAIRS:
                    app_val = getattr(d, app_f, None)
                    sp_val = getattr(d, sp_f, None)
                    setattr(d, app_f, sp_val)
                    setattr(d, sp_f, app_val)

                d.recompute_derived_fields(skip={"national_id", "spouse_national_id", "full_name", "spouse_full_name"})
                d.updated_at = timezone.now()
                d.save()

                # Flip attachment doc_types if configured
                if SWAP_ATTACHMENT_DOC_TYPES:
                    d.attachments.filter(doc_type__in=["NATIONAL_ID", "SPOUSE_ID"]).update(
                        doc_type=Case(
                            When(doc_type="NATIONAL_ID", then=Value("SPOUSE_ID")),
                            When(doc_type="SPOUSE_ID", then=Value("NATIONAL_ID")),
                            default="doc_type"
                        )
                    )

                s_hash = "SHA256: " + hashlib.sha256(f"EXCEL_SWAP:{d.id}:{uuid.uuid4()}".encode()).hexdigest()[:24]
                WorkflowSignatureLog.objects.create(
                    dossier=d,
                    from_stage=f"مرحله {d.current_stage}: {d.current_stage_title}",
                    to_stage=f"مرحله {d.current_stage}: {d.current_stage_title}",
                    actor=actor_name,
                    role=actor_role,
                    action="EXCEL_SWAP",
                    action_label="جابجایی با همسر از طریق اکسل",
                    signature_hash=s_hash,
                    notes=f"جابجایی متقاضی اصلی ({d.spouse_full_name}) با همسر ({d.full_name}) از طریق اکسل"
                )

                DossierFieldChangeLog.objects.create(
                    dossier=d,
                    field_name="national_id",
                    field_label="جابجایی کدملی متقاضی و همسر",
                    old_value=str(d.spouse_national_id),
                    new_value=str(d.national_id),
                    changed_by=user,
                    stage=d.current_stage
                )
                swapped_count += 1
        except Exception as swap_err:
            item["reasons"].append(f"خطای ذخیره‌سازی جابجایی: {str(swap_err)}")
            errors.append(item)

    if errors and not report_url:
        r_uuid = generate_failure_report(user.id, raw_headers, errors)
        report_url = f"/excel/report/{r_uuid}/"

    return {
        "success": True,
        "error": None,
        "preview": False,
        "created_count": 0,
        "updated_count": swapped_count,
        "swapped_count": swapped_count,
        "valid_count": swapped_count,
        "unchanged_count": 0,
        "failed_count": len(errors),
        "matched_via_spouse_count": sum(1 for _, _, m in valid_swap_rows if m == "spouse"),
        "warnings": [],
        "report_url": report_url,
        "errors": errors[:100],
        "updates_preview": updates_preview,
    }

# -------------------------------------------------------------------------
# Verbatim EXPORT_COLUMNS and generate_dossiers_export
# -------------------------------------------------------------------------
EXPORT_COLUMNS = [
    # (Header Title, Field Name / Lambda, Type)
    ("شماره بایگانی پرونده", "archive_number", "int"),
    ("کد ملی متقاضی", "national_id", "str"),
    ("مرحله جاری پرونده (۱ تا ۲۲)", "current_stage", "int"),
    ("عنوان مرحله جاری", lambda d: d.current_stage_title, "str"),
    ("سمت اقدام‌کننده مرحله جاری", lambda d: d.current_role, "str"),
    ("وضعیت گردش کار پرونده", lambda d: d.get_status_display(), "str"),
    ("قفل نهایی پرونده", lambda d: "بله" if d.is_locked else "خیر", "str"),
    
    # Personal & Family Information
    ("نام متقاضی", "first_name", "str"),
    ("نام خانوادگی متقاضی", "last_name", "str"),
    ("نام و نام خانوادگی متقاضی", "full_name", "str"),
    ("نام پدر", "father_name", "str"),
    ("تاریخ تولد متقاضی (شمسی)", "birth_date", "str"),
    ("شماره شناسنامه متقاضی", "applicant_id_number", "str"),
    ("محل صدور متقاضی", "applicant_birth_place", "str"),
    ("شماره همراه متقاضی", "applicant_phone", "str"),
    ("وضعیت تاهل", "marital_status", "str"),
    ("تاییدیه تاهل", lambda d: "بله" if d.is_married_confirmed else "خیر", "str"),
    ("دهک درآمدی (۱ تا ۱۰)", "decile", "int"),
    ("رتبه انتخاب واحد", "selection_rank", "int"),
    
    # Spouse Information
    ("نام همسر", "spouse_first_name", "str"),
    ("نام خانوادگی همسر", "spouse_last_name", "str"),
    ("نام و نام خانوادگی همسر", "spouse_full_name", "str"),
    ("نام پدر همسر", "spouse_father_name", "str"),
    ("کد ملی همسر", "spouse_national_id", "national_id"),
    ("تاریخ تولد همسر (شمسی)", "spouse_birth_date", "str"),
    ("شماره شناسنامه همسر", "spouse_id_number", "str"),
    ("محل صدور شناسنامه همسر", "spouse_birth_place", "str"),
    
    # Form J Inquiries
    ("وضعیت فرم ج متقاضی", "applicant_form_j_status", "str"),
    ("استعلام اداره کل فرم ج متقاضی", "applicant_form_j_directorate_status", "str"),
    ("توضیحات فرم ج متقاضی", "applicant_form_j_red_description", "str"),
    ("وضعیت فرم ج همسر", "spouse_form_j_status", "str"),
    ("استعلام اداره کل فرم ج همسر", "spouse_form_j_directorate_status", "str"),
    ("توضیحات فرم ج همسر", "spouse_form_j_red_description", "str"),
    ("نحوه ثبت فرم ج", "form_j_registration_type", "str"),

    # Project & Unit Specifications
    ("نام پروژه", "project", "str"),
    ("سایت", "site", "str"),
    ("نوع ساخت", "construction_type", "str"),
    ("نام بلوک", "block_name", "str"),
    ("کد بلوک", "block_code", "str"),
    ("شماره طبقه", "floor_number", "int"),
    ("شماره واحد", "unit_number", "int"),
    ("کد واحد", "unit_code", "str"),
    ("تعداد خواب", "bedroom_count", "int"),
    ("جهت واحد", "unit_direction", "str"),
    ("متراژ مفید واحد (مترمربع)", "net_unit_area", "decimal"),
    ("متراژ مشاعات (مترمربع)", "common_area", "decimal"),
    ("جمع کل متراژ واحد (مترمربع)", "total_area", "decimal"),
    ("مساحت واحد (مترمربع)", "unit_area", "decimal"),
    ("شماره انباری", "storage_number", "int"),
    ("مساحت انباری (مترمربع)", "storage_area", "decimal"),
    ("شماره پارکینگ", "parking_number", "int"),
    ("مساحت پارکینگ (مترمربع)", "parking_area", "decimal"),

    # Registry Plaques
    ("بخش ثبتی", "registration_section", "str"),
    ("پلاک اصلی", "main_plaque", "int"),
    ("پلاک مفروز", "separated_plaque", "int"),
    ("فرعی از (پلاک فرعی)", "sub_plaque", "int"),
    ("شماره قطعه", "plot_number", "int"),
    ("کد نوسازی", "renovation_code", "str"),

    # Financial & Loans (amounts in Rials)
    ("مبلغ کل قرارداد (ریال)", lambda d: (d.base_cost_without_loan or 0) + (d.bank_loan_amount or 0), "price"),
    ("قیمت تمام شده بدون وام (ریال)", "base_cost_without_loan", "price"),
    ("مبلغ تسهیلات وام بانکی (ریال)", "bank_loan_amount", "price"),
    ("مبلغ وام صندوق (ریال)", "fund_loan_amount", "price"),
    ("مبلغ نامه پیمانکار (ریال)", "contractor_letter_amount", "price"),
    ("مبلغ وام دهک (ریال)", "decile_loan_amount", "price"),
    ("مبلغ آورده نقدی متقاضی (ریال)", "applicant_equity", "price"),
    ("تایید تامین آورده نقدی", lambda d: "بله" if d.is_equity_funded else "خیر", "str"),
    ("ارسال پیامک آورده نقدی", lambda d: "بله" if d.is_sms_sent else "خیر", "str"),
    ("تاریخ ارسال پیامک آورده نقدی (شمسی)", "sms_sent_date", "str"),
    ("شماره نامه بانک", "bank_letter_number", "str"),
    ("تاریخ نامه بانک (شمسی)", "bank_letter_date", "str"),
    ("اضافه به لیست ارسالی‌ها به بانک", lambda d: "بله" if d.is_added_to_bank_shipment_list else "خیر", "str"),
    ("ارسال شده به بانک", lambda d: "بله" if d.is_sent_to_bank else "خیر", "str"),
    ("تاریخ ارسال به بانک (شمسی)", "bank_sent_date", "str"),
    ("شماره نامه ارسال به بانک", "bank_sent_letter_number", "str"),
    ("بانک عامل تسهیلات دهک", "decile_loan_bank", "str"),
    ("نهاد تحت حمایت", "supported_institution", "str"),

    # Land Lease & Appraisal
    ("جمع کل قدرالسهم (مترمربع)", "total_land_share", "decimal"),
    ("مبلغ اجاره سنوات گذشته (ریال)", "past_years_rent", "price"),
    ("مبلغ اجاره سال جاری (ریال)", "current_year_rent", "price"),
    ("سال اجاره عرصه", "land_lease_year", "str"),
    ("مبلغ پرداختی اجاره عرصه (ریال)", "tenant_price", "price"),
    ("کد پیگیری فیش اجاره", "tenant_code", "str"),
    ("تایید نقدی اجاره", lambda d: "بله" if d.is_cash_rent_confirmed else "خیر", "str"),

    # Preparation (آماده‌سازی)
    ("مبلغ نقدی آماده‌سازی - ۲۰٪ نقد (ریال)", "cash_preparation_amount", "price"),
    ("مبلغ غیرنقدی آماده‌سازی - ۸۰٪ اقساط (ریال)", "non_cash_preparation_amount", "price"),
    ("کد پیگیری فیش پیش‌پرداخت آماده‌سازی", "prepayment_code", "str"),
    ("تعداد چک‌های آماده‌سازی", "preparation_check_count", "int"),
    ("مجموع مبلغ چک‌های آماده‌سازی (ریال)", "total_preparation_check_amount", "price"),
    ("تایید دریافت چک‌های آماده‌سازی", lambda d: "بله" if d.is_preparation_checks_confirmed else "خیر", "str"),

    # Checks & Commitments
    ("شماره تعهدنامه", "commitment_number", "str"),
    ("تاریخ تعهدنامه (شمسی)", "commitment_date", "str"),
    ("تعداد چک‌های دهک", "check_count", "int"),
    ("مبلغ هر چک دهک (ریال)", "check_amount", "price"),
    ("مبلغ چک آخر دهک (ریال)", "last_check_amount", "price"),
    ("مجموع مبلغ چک‌های دهک (ریال)", "total_check_amount", "price"),
    ("تایید چک‌های تسهیلات دهک", lambda d: "بله" if d.is_decile_loan_confirmed else "خیر", "str"),

    # Official Letters & Stage Control
    ("شماره نامه راه و شهرسازی", "rah_letter", "str"),
    ("تاریخ نامه راه و شهرسازی (شمسی)", "rah_letter_date", "str"),
    ("شماره دفترخانه اسناد رسمی", "notary_office_number", "str"),
    ("شماره نامه معرفی به محضر", "notary_letter_number", "str"),
    ("تاریخ نامه معرفی به محضر (شمسی)", "notary_letter_date", "str"),
    ("تاریخ تشکیل پرونده", lambda d: jdatetime.datetime.fromgregorian(datetime=d.created_at).strftime('%Y/%m/%d %H:%M') if d.created_at else "", "str"),
    ("تاریخ آخرین بروزرسانی", lambda d: jdatetime.datetime.fromgregorian(datetime=d.updated_at).strftime('%Y/%m/%d %H:%M') if d.updated_at else "", "str"),
    ("کارمزد خدمات چک (ریال)", "check_service_fee", "price"),
    ("کارمزد خدمات آماده‌سازی (ریال)", "preparation_service_fee", "price"),
]

EXPORT_CATEGORY_MAP: Dict[str, Tuple[str, Set[str]]] = {
    "applicant": ("اطلاعات هویتی متقاضی", {
        "first_name", "last_name", "full_name", "father_name", "birth_date",
        "applicant_id_number", "applicant_birth_place", "applicant_phone",
        "marital_status", "is_married_confirmed", "decile", "selection_rank"
    }),
    "spouse": ("مشخصات هویتی همسر", {
        "spouse_first_name", "spouse_last_name", "spouse_full_name", "spouse_father_name",
        "spouse_national_id", "spouse_birth_date", "spouse_id_number", "spouse_birth_place"
    }),
    "property": ("اطلاعات پروژه و مشخصات ثبتی", {
        "project", "site", "construction_type", "block_name", "block_code",
        "floor_number", "unit_number", "unit_code", "bedroom_count", "unit_direction",
        "net_unit_area", "common_area", "total_area", "unit_area", "storage_number",
        "storage_area", "parking_number", "parking_area",
        "registration_section", "main_plaque", "separated_plaque", "sub_plaque",
        "plot_number", "renovation_code", "deed_number", "deed_date", "is_land_deed_confirmed"
    }),
    "financial": ("اطلاعات مالی و تسهیلات بانکی", {
        "base_cost_without_loan", "bank_loan_amount", "fund_loan_amount",
        "contractor_letter_amount", "decile_loan_amount", "applicant_equity",
        "is_equity_funded", "is_sms_sent", "sms_sent_date", "bank_letter_number",
        "bank_letter_date", "is_added_to_bank_shipment_list", "is_sent_to_bank",
        "bank_sent_date", "bank_sent_letter_number", "decile_loan_bank", "supported_institution"
    }),
    "lease_prep_checks": ("تسهیلات دهک، چک‌ها و کارمزدها", {
        "total_land_share", "past_years_rent", "current_year_rent", "land_lease_year",
        "tenant_price", "tenant_code", "is_cash_rent_confirmed", "cash_preparation_amount",
        "non_cash_preparation_amount", "prepayment_code", "preparation_check_count",
        "total_preparation_check_amount", "is_preparation_checks_confirmed",
        "commitment_number", "commitment_date", "check_count", "check_amount",
        "last_check_amount", "total_check_amount", "is_decile_loan_confirmed",
        "rah_letter", "rah_letter_date", "notary_office_number", "notary_letter_number", "notary_letter_date", "check_service_fee", "preparation_service_fee"
    }),
    "form_j": ("وضعیت‌های فرم ج", {
        "applicant_form_j_status", "applicant_form_j_directorate_status",
        "applicant_form_j_red_description", "spouse_form_j_status",
        "spouse_form_j_directorate_status", "spouse_form_j_red_description",
        "form_j_registration_type"
    }),
    "workflow": ("اطلاعات گردش کار و امضاها", {
        "current_stage", "current_stage_title", "current_role",
        "status", "is_locked", "created_at", "updated_at"
    }),
}

def generate_dossiers_export(queryset=None, cache_key: str | None = None, selected_categories: Optional[List[str]] = None) -> HttpResponse:
    """
    Generate and stream a comprehensive, professional Excel workbook containing
    records, codes, plaque numbers, financial values, and tracking metadata.
    Supports selective category exports (e.g. applicant, financial, property, etc.).
    Optimized with write_only streaming and server-side debounce caching.
    """
    if queryset is None:
        queryset = HousingDossier.objects.all().order_by("-archive_number")
        if not cache_key:
            cache_key = "all"

    # Filter columns by selected categories if provided
    active_columns = EXPORT_COLUMNS
    if selected_categories and "all" not in selected_categories:
        allowed_fields: Set[str] = set()
        for cat in selected_categories:
            if cat in EXPORT_CATEGORY_MAP:
                allowed_fields.update(EXPORT_CATEGORY_MAP[cat][1])

        # Essential identification columns always preserved
        allowed_fields.update({"archive_number", "national_id", "full_name"})

        filtered = []
        for col in EXPORT_COLUMNS:
            col_title, accessor, col_type = col
            field_name = accessor if isinstance(accessor, str) else None
            if field_name and field_name in allowed_fields:
                filtered.append(col)
            elif not field_name:
                # Lambda column category matching
                if "workflow" in selected_categories and col_title in ("عنوان مرحله جاری", "سمت اقدام‌کننده مرحله جاری", "وضعیت گردش کار پرونده", "قفل نهایی پرونده", "تاریخ تشکیل پرونده", "تاریخ آخرین بروزرسانی"):
                    filtered.append(col)
                elif "applicant" in selected_categories and col_title == "تاییدیه تاهل":
                    filtered.append(col)
                elif "financial" in selected_categories and col_title in ("تایید تامین آورده نقدی", "ارسال پیامک آورده نقدی", "اضافه به لیست ارسالی‌ها به بانک", "ارسال شده به بانک"):
                    filtered.append(col)
                elif "lease_prep_checks" in selected_categories and col_title in ("تایید نقدی اجاره", "تایید دریافت چک‌های آماده‌سازی", "تایید چک‌های تسهیلات دهک"):
                    filtered.append(col)
        if filtered:
            active_columns = filtered

    if selected_categories:
        cache_key = f"{cache_key or 'export'}_{'_'.join(sorted(selected_categories))}"

    now_ts = time.time()
    if cache_key:
        cached = _export_cache.get(cache_key)
        if cached:
            c_path, c_ts, c_size = cached
            if os.path.exists(c_path) and (now_ts - c_ts) < 90:
                with open(c_path, "rb") as f:
                    file_bytes = f.read()
                now_j = jdatetime.datetime.now().strftime('%Y%m%d_%H%M')
                filename = f"MaskanYar_Dossiers_Export_{now_j}.xlsx"
                response = HttpResponse(
                    file_bytes,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                response["Content-Length"] = str(len(file_bytes))
                return response

    with _export_lock:
        now_ts = time.time()
        if cache_key:
            cached = _export_cache.get(cache_key)
            if cached:
                c_path, c_ts, c_size = cached
                if os.path.exists(c_path) and (now_ts - c_ts) < 90:
                    with open(c_path, "rb") as f:
                        file_bytes = f.read()
                    now_j = jdatetime.datetime.now().strftime('%Y%m%d_%H%M')
                    filename = f"MaskanYar_Dossiers_Export_{now_j}.xlsx"
                    response = HttpResponse(
                        file_bytes,
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    response["Content-Disposition"] = f'attachment; filename="{filename}"'
                    response["Content-Length"] = str(len(file_bytes))
                    return response

        # Use write_only streaming for blazing fast, low-RAM generation
        wb = openpyxl.Workbook(write_only=True)
        ws = wb.create_sheet(title="پرونده‌های مسکن مسکن‌یار")
        ws.views.sheetView[0].rightToLeft = True

        headers = [col[0] for col in active_columns]
        ws.append(headers)

        for dossier in queryset.iterator(chunk_size=2000):
            row = []
            for col_title, accessor, col_type in active_columns:
                if callable(accessor):
                    val = accessor(dossier)
                else:
                    val = getattr(dossier, accessor, "")

                if val is None:
                    val = ""

                if col_type == "int":
                    if val != "" and val is not None:
                        try:
                            val = int(val)
                        except Exception:
                            val = str(val)
                    else:
                        val = ""
                elif col_type == "price":
                    if val != "" and val is not None:
                        try:
                            val = int(val)
                        except Exception:
                            val = str(val)
                    else:
                        val = 0
                elif col_type == "decimal":
                    if val != "" and val is not None:
                        try:
                            val = float(val)
                        except Exception:
                            val = str(val)
                    else:
                        val = ""
                else:
                    val = str(val).strip() if val is not None else ""
                row.append(val)
            ws.append(row)

        temp_dir = tempfile.gettempdir()
        temp_export_path = os.path.join(temp_dir, f"sanadban_export_{cache_key or 'export'}.xlsx")
        wb.save(temp_export_path)

        with open(temp_export_path, "rb") as f:
            file_bytes = f.read()

        if cache_key:
            _export_cache[cache_key] = (temp_export_path, now_ts, len(file_bytes))

        now_j = jdatetime.datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"MaskanYar_Dossiers_Export_{now_j}.xlsx"

        response = HttpResponse(
            file_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = str(len(file_bytes))
        return response

# Backwards-compatibility aliases
process_create_excel = process_excel_create
process_update_excel = process_excel_update

