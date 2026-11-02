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
import jdatetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from django.conf import settings
from django.db import transaction, IntegrityError, models
from django.db.models import Case, When, Value
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
    ("کد ملی متقاضی", "national_id", "str"),

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
    ("کد ملی همسر", "spouse_national_id", "str"),
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
    ("پلاک ثبتی اصلی", "main_plaque", "str"),
    ("پلاک ثبتی مفروز و مجزی", "separated_plaque", "str"),
    ("پلاک ثبتی فرعی", "sub_plaque", "str"),
    ("شماره قطعه", "plot_number", "str"),
    ("کد نوسازی شهرداری", "municipality_code", "str"),
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
    ("قیمت پایه بدون وام (ریال)", "base_cost_without_loan", "price"),
    ("سهم آورده نقدی متقاضی (ریال)", "applicant_equity", "price"),
    ("مبلغ وام صندوق ملی مسکن (ریال)", "fund_loan_amount", "price"),
    ("مبلغ کسر نامه پیمانکار (ریال)", "contractor_letter_amount", "price"),
    ("مبلغ وام دهک‌های درآمدی (ریال)", "decile_loan_amount", "price"),
    ("مبلغ وام بانکی (ریال)", "bank_loan_amount", "price"),

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

    # Directorate Final Letters
    ("شماره نامه معرفی به محضر اداره کل", "rah_letter", "str"),
    ("تاریخ نامه معرفی به محضر اداره کل (شمسی)", "rah_letter_date", "str"),
]

# Aliases dictionary to tolerate historical file headers
HEADER_ALIASES: Dict[str, str] = {
    "کد ملی": "national_id",
    "کدملی": "national_id",
    "کد ملی متقاضی": "national_id",
    "کدملی متقاضی": "national_id",
    "نام": "first_name",
    "نام خانوادگی": "last_name",
    "نام و نام خانوادگی": "full_name",
    "نام کامل": "full_name",
    "تلفن همراه": "applicant_phone",
    "شماره همراه": "applicant_phone",
    "موبایل": "applicant_phone",
    "کد ملی همسر": "spouse_national_id",
    "کدملی همسر": "spouse_national_id",
    "قیمت پایه": "base_cost_without_loan",
    "آورده نقدی": "applicant_equity",
    "سهم آورده": "applicant_equity",
    "وام صندوق": "fund_loan_amount",
    "کسر نامه پیمانکار": "contractor_letter_amount",
    "وام دهک": "decile_loan_amount",
    "وام بانکی": "bank_loan_amount",
    "کارمزد چک": "check_service_fee",
    "کارمزد آماده سازی": "preparation_service_fee",
    "کارمزد آماده‌سازی": "preparation_service_fee",
    "پروژه": "project",
    "نام پروژه": "project",
    "پروژه مسکونی": "project",
    "ثبت دستی": "form_j_registration_type",
    "ثبت خودکار": "form_j_registration_type",
    "نوع ثبت فرم ج": "form_j_registration_type",
    "نحوه ثبت فرم ج": "form_j_registration_type",
    "تاریخ ارسال پیامک": "sms_sent_date",
    "تاریخ ارسال پیامک آورده نقدی": "sms_sent_date",
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
    s = clean_digits(val)
    if not s:
        return None
    # If Excel parsed 0012345678 as float 12345678.0
    if "." in s:
        try:
            s = str(int(float(s)))
        except ValueError:
            return None
    if s.isdigit():
        s = s.zfill(10)
        if len(s) == 10:
            return s
    return None

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

    if field_type == "price":
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
    _style_headers(ws2, 1, fill=_GUIDE_FILL)
    ws2.column_dimensions["A"].width = 75

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def generate_group_sign_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "امضای گروهی مراحل"
    ws.views.sheetView[0].rightToLeft = True

    headers = ["کد ملی متقاضی", "مرحله (۱ تا ۲۱)", "توضیحات امضا"]
    ws.append(headers)
    _style_headers(ws, len(headers))

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
    Matches raw sheet headers to TEMPLATE_FIELD_SPECS and aliases.
    Ensures EXACT matching for national_id ("کد ملی متقاضی" or alias "کد ملی"), never substring.
    Returns (col_idx_to_spec, national_id_col_idx).
    """
    col_map: Dict[int, Tuple[str, str, str]] = {}
    nid_col: Optional[int] = None

    spec_by_header = {normalize_header(spec[0]): spec for spec in TEMPLATE_FIELD_SPECS}

    for idx, raw in enumerate(raw_headers):
        if not raw:
            continue
        norm = normalize_header(raw)

        # Check exact national_id matches
        if norm in ("کد ملی متقاضی", "کدملی متقاضی", "کد ملی", "کدملی"):
            col_map[idx] = ("کد ملی متقاضی", "national_id", "str")
            if nid_col is None:
                nid_col = idx
            continue

        # Check exact spec title
        if norm in spec_by_header:
            col_map[idx] = spec_by_header[norm]
            continue

        # Check aliases
        if norm in HEADER_ALIASES:
            field_name = HEADER_ALIASES[norm]
            # find matching spec
            for spec in TEMPLATE_FIELD_SPECS:
                if spec[1] == field_name:
                    col_map[idx] = spec
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

    ws = wb.worksheets[0]
    row_iter = ws.iter_rows(values_only=True)

    try:
        header_row = next(row_iter)
    except StopIteration:
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

    row_num = 1
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
            header_title, field_name, field_type = col_map[c_idx]

            # Commission permission check
            if field_name in ("check_service_fee", "preparation_service_fee"):
                if not is_check_admin:
                    if not commission_warned:
                        warnings.append("ستون‌های کارمزد برای شما مجاز نیست و نادیده گرفته شد.")
                        commission_warned = True
                    continue

            # Special cleaners
            if field_name == "national_id":
                c_val = cleaned_nid
                err = None
            elif field_name == "spouse_national_id":
                c_val = clean_national_id(val)
                err = None if (c_val or not str(val).strip()) else "کد ملی همسر باید ۱۰ رقم باشد."
            elif field_name == "applicant_phone":
                c_val = clean_phone(val)
                err = None
            else:
                c_val, err = clean_field_value(field_name, field_type, val)

            if err:
                row_errors.append(f"ستون «{header_title}»: {err}")
            elif c_val is not None:
                parsed_data[field_name] = c_val

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

    ws = wb.worksheets[0]
    row_iter = ws.iter_rows(values_only=True)

    try:
        header_row = next(row_iter)
    except StopIteration:
        return {"success": False, "error": "فایل اکسل خالی است."}

    raw_headers = list(header_row or [])
    col_map, nid_col = _build_header_map(raw_headers)

    if nid_col is None:
        return {"success": False, "error": "ستون کلیدی «کد ملی متقاضی» در فایل اکسل یافت نشد."}

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
            row_errors.append("کد ملی نامعتبر یا خالی است (باید دقیقاً ۱۰ رقم باشد).")

        parsed_data: Dict[str, Any] = {}
        parsed_labels: Dict[str, str] = {}
        for c_idx, val in enumerate(row_cells):
            if c_idx not in col_map or val is None:
                continue
            header_title, field_name, field_type = col_map[c_idx]

            # Commission permission check
            if field_name in ("check_service_fee", "preparation_service_fee"):
                if not is_check_admin:
                    if not commission_warned:
                        warnings.append("ستون‌های کارمزد برای شما مجاز نیست و نادیده گرفته شد.")
                        commission_warned = True
                    continue

            # National ID and archive number are NEVER updated
            if field_name in ("national_id", "archive_number"):
                continue

            # Special cleaners
            if field_name == "spouse_national_id":
                c_val = clean_national_id(val)
                err = None if (c_val or not str(val).strip()) else "کد ملی همسر باید ۱۰ رقم باشد."
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

        if cleaned_nid:
            all_nids.add(cleaned_nid)

        parsed_rows.append({
            "row": row_num,
            "national_id": cleaned_nid or str(raw_nid or ""),
            "data": parsed_data,
            "labels": parsed_labels,
            "original_cells": list(row_cells),
            "reasons": row_errors,
        })

    # Query DB in chunks for matching order:
    # 1. HousingDossier.national_id == id
    # 2. HousingDossier.spouse_national_id == id
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
    updates_preview: List[Dict[str, Any]] = []
    dossiers_to_update: List[HousingDossier] = []
    field_changes_by_dossier: Dict[int, List[Dict[str, Any]]] = {}
    modified_fields_set: Set[str] = set()
    spouse_matched_rows: List[Dict[str, Any]] = []

    valid_count = 0
    unchanged_count = 0
    updated_count = 0

    for item in parsed_rows:
        nid = item["national_id"]
        if item["reasons"]:
            errors.append(item)
            continue

        d_as_app = app_matches.get(nid)
        d_as_spouses = spouse_matches.get(nid, [])

        # Ambiguity check
        if d_as_app and d_as_spouses:
            item["reasons"].append("کد ملی هم به عنوان متقاضی و هم به عنوان همسر در پرونده‌های مختلف تطبیق دارد (ابهام در شناسایی پرونده).")
            errors.append(item)
            continue
        elif not d_as_app and len(d_as_spouses) > 1:
            item["reasons"].append("کد ملی به عنوان همسر در چندین پرونده مختلف ثبت شده است (ابهام در شناسایی پرونده).")
            errors.append(item)
            continue
        elif not d_as_app and not d_as_spouses:
            item["reasons"].append("کد ملی نه به عنوان متقاضی و نه به عنوان همسر در سامانه یافت نشد.")
            errors.append(item)
            continue

        if d_as_app:
            dossier = d_as_app
            matched_via = "applicant"
        else:
            dossier = d_as_spouses[0]
            matched_via = "spouse"

        # Check locked dossiers
        if dossier.is_locked and not is_admin:
            item["reasons"].append(f"پرونده {dossier.archive_number} مختومه و قفل است و دسترسی ویرایش ندارید.")
            errors.append(item)
            continue

        # Two rows resolving to same dossier
        if dossier.id in seen_dossier_ids:
            item["reasons"].append("پرونده قبلاً در همین فایل بروزرسانی شده است.")
            errors.append(item)
            continue
        seen_dossier_ids.add(dossier.id)

        valid_count += 1
        item["name"] = dossier.full_name
        item["archive_number"] = dossier.archive_number

        # Calculate diffs
        data_to_apply = dict(item["data"])
        if matched_via == "spouse":
            # Strip identity fields
            for id_field in IDENTITY_FIELDS:
                data_to_apply.pop(id_field, None)

        diffs: List[Dict[str, Any]] = []
        for f_name, new_val in data_to_apply.items():
            old_val = getattr(dossier, f_name, None)
            if old_val != new_val:
                label = item["labels"].get(f_name, f_name)
                diffs.append({
                    "field": f_name,
                    "label": label,
                    "old": str(old_val) if old_val is not None else "",
                    "new": str(new_val) if new_val is not None else "",
                })
                setattr(dossier, f_name, new_val)
                modified_fields_set.add(f_name)

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
        if matched_via == "spouse":
            spouse_matched_rows.append(preview_entry)

        if len(updates_preview) < 50:
            updates_preview.append(preview_entry)

    report_url = None
    if errors or spouse_matched_rows:
        r_uuid = generate_failure_report(user.id, raw_headers, errors, spouse_matched_rows)
        report_url = f"/excel/report/{r_uuid}/"

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
            "errors": errors[:100],
            "updates_preview": updates_preview,
        }

    # Confirm mode: Bulk update modified dossiers
    if dossiers_to_update:
        now_dt = timezone.now()
        for d in dossiers_to_update:
            d.updated_at = now_dt

        # Ensure derived fields are saved
        all_update_fields = list(modified_fields_set.union({
            "updated_at", "applicant_equity", "check_service_fee",
            "full_name", "first_name", "last_name",
            "spouse_full_name", "spouse_first_name", "spouse_last_name",
            "bank_name", "project_code", "bank_branch"
        }))

        for i in range(0, len(dossiers_to_update), CHUNK_WRITE_SIZE):
            chunk = dossiers_to_update[i : i + CHUNK_WRITE_SIZE]
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

        for i in range(0, len(sig_logs), CHUNK_WRITE_SIZE):
            WorkflowSignatureLog.objects.bulk_create(sig_logs[i : i + CHUNK_WRITE_SIZE])
        for i in range(0, len(change_logs), CHUNK_WRITE_SIZE):
            DossierFieldChangeLog.objects.bulk_create(change_logs[i : i + CHUNK_WRITE_SIZE])

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
        "errors": errors[:100],
        "updates_preview": updates_preview,
    }

# -------------------------------------------------------------------------
# Feature 5: Process Excel Group Sign (امضای گروهی)
# -------------------------------------------------------------------------
def process_excel_group_sign(file_obj: Any, user: Any, preview: bool = False, is_preview: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
    if is_preview is not None:
        preview = is_preview
    from .views import execute_dossier_sign

    profile = getattr(user, "profile", None)
    if profile and not profile.can_sign and not user.is_superuser:
        return {"success": False, "error": "حق امضای الکترونیکی برای حساب کاربری شما فعال نیست."}

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
    stage_col: Optional[int] = None
    notes_col: Optional[int] = None

    for idx, h in enumerate(raw_headers):
        norm = normalize_header(h)
        if norm in ("کد ملی متقاضی", "کدملی متقاضی", "کد ملی", "کدملی"):
            nid_col = idx
        elif "مرحله" in norm:
            stage_col = idx
        elif "توضیح" in norm or "یادداشت" in norm:
            notes_col = idx

    if nid_col is None:
        return {"success": False, "error": "ستون «کد ملی متقاضی» در فایل امضای گروهی یافت نشد."}

    parsed_rows: List[Dict[str, Any]] = []
    all_nids: Set[str] = set()
    errors: List[Dict[str, Any]] = []

    row_num = 1
    for row_cells in row_iter:
        row_num += 1
        if not any(c is not None and str(c).strip() for c in row_cells):
            continue

        if row_num > GROUP_SIGN_MAX_ROWS + 1:
            errors.append({
                "row": row_num,
                "national_id": "",
                "name": "",
                "reasons": [f"تعداد ردیف‌های فایل بیش از حد مجاز ({GROUP_SIGN_MAX_ROWS} ردیف) است."],
                "original_cells": list(row_cells),
            })
            break

        raw_nid = row_cells[nid_col] if nid_col < len(row_cells) else None
        cleaned_nid = clean_national_id(raw_nid)

        req_stage = None
        if stage_col is not None and stage_col < len(row_cells) and row_cells[stage_col] is not None:
            s_val = clean_digits(row_cells[stage_col])
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

    # Preload matching dossiers
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
    updates_preview: List[Dict[str, Any]] = []
    valid_sign_tasks: List[Tuple[HousingDossier, int, str, Dict[str, Any]]] = []

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

        # Permissions & stage validation
        if dossier.is_locked:
            item["reasons"].append(f"پرونده {dossier.archive_number} مختومه و قفل است.")
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
                    "new": f"مرحله {next_stage}" if next_stage <= 22 else "بایگانی نهایی (مختومه)",
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
            "updated_count": len(valid_sign_tasks),
            "signed_count": len(valid_sign_tasks),
            "valid_count": len(valid_sign_tasks),
            "unchanged_count": 0,
            "failed_count": len(errors),
            "matched_via_spouse_count": 0,
            "warnings": [],
            "report_url": report_url,
            "errors": errors[:100],
            "updates_preview": updates_preview,
        }

    # Confirm mode: Execute row-by-row in savepoints
    signed_count = 0
    for d, stg, note_text, item in valid_sign_tasks:
        try:
            with transaction.atomic():
                ok, res_stage = execute_dossier_sign(
                    dossier=d,
                    user=user,
                    notes=note_text or "امضای گروهی از طریق فایل اکسل",
                    action="SIGN_EXCEL",
                    target_stage=stg
                )
                if ok:
                    signed_count += 1
                else:
                    item["reasons"].append(str(res_stage))
                    errors.append(item)
        except Exception as sign_err:
            item["reasons"].append(f"خطای سیستمی در ثبت امضا: {str(sign_err)}")
            errors.append(item)

    if errors and not report_url:
        r_uuid = generate_failure_report(user.id, raw_headers, errors)
        report_url = f"/excel/report/{r_uuid}/"

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
        "errors": errors[:100],
        "updates_preview": updates_preview,
    }

# -------------------------------------------------------------------------
# Feature 6: Process Excel Spouse Swap (جابجایی با همسر)
# -------------------------------------------------------------------------
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
            item["reasons"].append(f"پرونده {dossier.archive_number} مختومه و قفل است.")
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
    ("مرحله جاری پرونده (۱ تا ۲۱)", "current_stage", "int"),
    ("عنوان مرحله جاری", lambda d: d.current_stage_title, "str"),
    ("واحد سازمانی مرحله جاری", lambda d: d.current_unit, "str"),
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
    ("کد ملی همسر", "spouse_national_id", "str"),
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
    ("متراژ پارکینگ مسقف (مترمربع)", "covered_parking_area", "decimal"),

    # Registry Plaques
    ("بخش ثبتی", "registration_section", "str"),
    ("پلاک اصلی", "main_plaque", "int"),
    ("پلاک مفروز", "separated_plaque", "int"),
    ("فرعی از (پلاک فرعی)", "sub_plaque", "int"),
    ("شماره قطعه", "plot_number", "int"),
    ("کد نوسازی", "renovation_code", "str"),

    # Financial & Loans (amounts in Rials)
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
    ("تاریخ تشکیل پرونده", lambda d: jdatetime.datetime.fromgregorian(datetime=d.created_at).strftime('%Y/%m/%d %H:%M') if d.created_at else "", "str"),
    ("تاریخ آخرین بروزرسانی", lambda d: jdatetime.datetime.fromgregorian(datetime=d.updated_at).strftime('%Y/%m/%d %H:%M') if d.updated_at else "", "str"),
    ("کارمزد خدمات چک (ریال)", "check_service_fee", "price"),
    ("کارمزد خدمات آماده‌سازی (ریال)", "preparation_service_fee", "price"),
]

def generate_dossiers_export(queryset=None, cache_key: str | None = None) -> HttpResponse:
    """
    Generate and stream a comprehensive, professional Excel workbook containing
    all records, codes, plaque numbers, financial values, and tracking metadata.
    Optimized with write_only streaming and server-side debounce caching to prevent 502 crashes.
    """
    if queryset is None:
        queryset = HousingDossier.objects.all().order_by("-archive_number")
        if not cache_key:
            cache_key = "all"

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

        headers = [col[0] for col in EXPORT_COLUMNS]
        ws.append(headers)

        for dossier in queryset.iterator(chunk_size=2000):
            row = []
            for col_title, accessor, col_type in EXPORT_COLUMNS:
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

