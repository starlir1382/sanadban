import io
import re
import hashlib
import jdatetime
from typing import Any, cast
from decimal import Decimal

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from django.http import HttpResponse
from django.db import transaction
from django.utils import timezone
from .models import HousingDossier, WorkflowSignatureLog

# ---------------------------------------------------------
# Comprehensive Mapping for HousingDossier Fields
# (Official Persian Header -> Model Field Name)
# ---------------------------------------------------------
EXCEL_FIELD_SPECS = [
    # Key Identifier
    ("کد ملی متقاضی", "national_id", "str"),
    ("شماره بایگانی پرونده", "archive_number", "int"),
    ("شماره بایگانی", "archive_number", "int"),
    
    # Personal & Family Information
    ("نام و نام خانوادگی متقاضی", "full_name", "str"),
    ("نام پدر", "father_name", "str"),
    ("تاریخ تولد متقاضی (شمسی)", "birth_date", "str"),
    ("شماره همراه متقاضی", "applicant_phone", "str"),
    ("وضعیت تاهل", "marital_status", "str"),
    ("دهک درآمدی (۱ تا ۱۰)", "decile", "int"),
    ("رتبه انتخاب واحد", "selection_rank", "int"),
    
    # Spouse Information
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
    ("متراژ مفید واحد (م²)", "net_unit_area", "decimal"),
    ("متراژ مشاعات (م²)", "common_area", "decimal"),
    ("جمع کل متراژ واحد (م²)", "total_area", "decimal"),
    ("مساحت واحد (م²)", "unit_area", "decimal"),
    ("شماره انباری", "storage_number", "int"),
    ("مساحت انباری (م²)", "storage_area", "decimal"),
    ("شماره پارکینگ", "parking_number", "int"),
    ("مساحت پارکینگ (م²)", "parking_area", "decimal"),
    ("متراژ پارکینگ مسقف (م²)", "covered_parking_area", "decimal"),

    # Registry Plaques
    ("بخش ثبتی", "registration_section", "str"),
    ("پلاک اصلی", "main_plaque", "int"),
    ("پلاک مفروز", "separated_plaque", "int"),
    ("فرعی از (پلاک فرعی)", "sub_plaque", "int"),
    ("شماره قطعه", "plot_number", "int"),

    # Financial & Loans (amounts in Rials)
    ("قیمت تمام شده بدون وام (ریال)", "base_cost_without_loan", "price"),
    ("مبلغ تسهیلات وام بانکی (ریال)", "bank_loan_amount", "price"),
    ("مبلغ وام صندوق (ریال)", "fund_loan_amount", "price"),
    ("مبلغ نامه پیمانکار (ریال)", "contractor_letter_amount", "price"),
    ("مبلغ وام دهک (ریال)", "decile_loan_amount", "price"),
    ("مبلغ آورده نقدی متقاضی (ریال)", "applicant_equity", "price"),
    ("شماره نامه بانک", "bank_letter_number", "str"),
    ("تاریخ نامه بانک (شمسی)", "bank_letter_date", "str"),
    ("ارسال شده به بانک", "is_sent_to_bank", "bool"),
    ("تاریخ ارسال به بانک (شمسی)", "bank_sent_date", "str"),
    ("شماره نامه ارسال به بانک", "bank_sent_letter_number", "str"),
    ("اضافه به لیست ارسالی‌ها به بانک", "is_added_to_bank_shipment_list", "bool"),
    ("بانک عامل تسهیلات دهک", "decile_loan_bank", "str"),
    ("نهاد تحت حمایت", "supported_institution", "str"),

    # Land Lease & Appraisal
    ("جمع کل قدرالسهم (م²)", "total_land_share", "decimal"),
    ("مبلغ اجاره سنوات گذشته (ریال)", "past_years_rent", "price"),
    ("مبلغ اجاره سال جاری (ریال)", "current_year_rent", "price"),
    ("سال اجاره عرصه", "land_lease_year", "str"),
    ("مبلغ پرداختی اجاره عرصه (ریال)", "tenant_price", "price"),
    ("کد پیگیری فیش اجاره", "tenant_code", "str"),

    # Preparation (آماده‌سازی)
    ("مبلغ نقدی آماده‌سازی - ۲۰٪ نقد (ریال)", "cash_preparation_amount", "price"),
    ("مبلغ غیرنقدی آماده‌سازی - ۸۰٪ اقساط (ریال)", "non_cash_preparation_amount", "price"),
    ("کد پیگیری فیش پیش‌پرداخت آماده‌سازی", "prepayment_code", "str"),
    ("تعداد چک‌های آماده‌سازی", "preparation_check_count", "int"),
    ("مجموع مبلغ چک‌های آماده‌سازی (ریال)", "total_preparation_check_amount", "price"),

    # Checks & Commitments
    ("شماره تعهدنامه", "commitment_number", "str"),
    ("تاریخ تعهدنامه (شمسی)", "commitment_date", "str"),
    ("تعداد چک‌های دهک", "check_count", "int"),
    ("مبلغ هر چک دهک (ریال)", "check_amount", "price"),
    ("مبلغ چک آخر دهک (ریال)", "last_check_amount", "price"),
    ("مجموع مبلغ چک‌های دهک (ریال)", "total_check_amount", "price"),

    # Official Letters & Stage Control
    ("شماره نامه راه و شهرسازی", "rah_letter", "str"),
    ("تاریخ نامه راه و شهرسازی (شمسی)", "rah_letter_date", "str"),
    ("مرحله جاری پرونده (۰ تا ۲۱)", "current_stage", "int"),
]

def _normalize_header(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ").strip()
    return " ".join(text.split())

FIELD_BY_NORMALIZED_HEADER = {
    _normalize_header(header): (field_name, field_type)
    for header, field_name, field_type in EXCEL_FIELD_SPECS
}
LABEL_BY_FIELD = {
    field_name: header
    for header, field_name, _ in EXCEL_FIELD_SPECS
}

def normalize_digits(s: Any) -> str:
    if s is None:
        return ""
    s = str(s)
    # Persian digits
    for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        s = s.replace(c, str(i))
    # Arabic digits
    for i, c in enumerate("٠١٢٣٤٥٦٧٨٩"):
        s = s.replace(c, str(i))
    return s.strip()

def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    return str(val).strip()

def _clean_digits(val: Any) -> str:
    s = normalize_digits(_clean_str(val))
    return re.sub(r"[^\d]", "", s)

def _clean_national_id(val: Any) -> str:
    d = _clean_digits(val)
    if d and len(d) < 10:
        d = d.zfill(10)
    return d

def _clean_phone(val: Any) -> str:
    d = _clean_digits(val)
    if d and len(d) == 10 and d.startswith("9"):
        d = "0" + d
    return d


def _clean_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "بله", "دارد", "تایید", "yes")

def _clean_price(val: Any) -> int:
    s = _clean_digits(val)
    try:
        return int(s) if s else 0
    except ValueError:
        return 0

def _clean_int(val: Any) -> int | None:
    s = _clean_digits(val)
    try:
        return int(s) if s else None
    except ValueError:
        return None

def _clean_decimal(val: Any) -> Decimal | None:
    if val is None or str(val).strip() == "":
        return None
    s = normalize_digits(str(val)).replace(",", ".").replace(" ", "")
    try:
        return Decimal(s)
    except Exception:
        return None

# ---------------------------------------------------------
# 1. Download Template for Adding New Dossiers
# ---------------------------------------------------------
def generate_create_template() -> HttpResponse:
    wb = openpyxl.Workbook()
    ws = cast(Worksheet, wb.active)
    ws.title = "قالب ایجاد پرونده‌ها"
    ws.views.sheetView[0].rightToLeft = True

    headers = [spec[0] for spec in EXCEL_FIELD_SPECS]
    ws.append(headers)

    header_fill = PatternFill(start_color="0F2744", end_color="0F2744", fill_type="solid")
    key_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Tahoma", size=9, bold=True, color="FFFFFF")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = key_fill if col_idx == 1 else header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = 22

    # Set column formats to text for ID / phone columns
    for row_num in range(2, 500):
        ws[f"A{row_num}"].number_format = "@"
        ws[f"E{row_num}"].number_format = "@"
        ws[f"K{row_num}"].number_format = "@"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Template_Create_Dossiers.xlsx"'
    return response

# ---------------------------------------------------------
# 2. Download Template for Updating Dossiers (Ref: National ID)
# ---------------------------------------------------------
def generate_update_template() -> HttpResponse:
    wb = openpyxl.Workbook()
    ws = cast(Worksheet, wb.active)
    ws.title = "قالب بروزرسانی پرونده‌ها"
    ws.views.sheetView[0].rightToLeft = True

    headers = [spec[0] for spec in EXCEL_FIELD_SPECS]
    ws.append(headers)

    key_fill = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Tahoma", size=9, bold=True, color="FFFFFF")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = key_fill if col_idx == 1 else header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = 22

    for row_num in range(2, 1000):
        ws[f"A{row_num}"].number_format = "@"
        ws[f"E{row_num}"].number_format = "@"
        ws[f"K{row_num}"].number_format = "@"

    # Guide Sheet
    guide = wb.create_sheet("راهنمای بروزرسانی")
    guide.views.sheetView[0].rightToLeft = True
    guide.column_dimensions["A"].width = 110
    instructions = [
        "راهنمای بروزرسانی دسته‌جمعی پرونده‌ها از طریق اکسل:",
        "۱) ستون اول (کد ملی متقاضی) الزامی و کلید جستجو در سیستم است.",
        "۲) رکوردهایی که کد ملی آن‌ها در سیستم یافت شود، فیلدهای ارسالی‌شان بروزرسانی می‌گردد.",
        "۳) کلیه ستون‌های دیگر اختیاری هستند؛ می‌توانید ستون‌هایی که نمی‌خواهید تغییر دهند را خالی بگذارید یا حذف کنید.",
        "۴) خانه خالی در اکسل به منزله «عدم تغییر» است و مقدار موجود در پایگاه داده هرگز پاک نمی‌شود.",
        "۵) مبالغ مالی را به ریال و به صورت عددی وارد نمایید (بدون حروف ریال یا کاما).",
        "۶) تاریخ‌ها را به فرمت شمسی ۱۴۰۳/۰۵/۱۲ وارد نمایید.",
        "۷) مرحله جاری پرونده را در صورت نیاز به انتقال، عددی بین ۰ تا ۲۱ وارد فرمایید.",
    ]
    for line in instructions:
        guide.append([line])
    guide["A1"].font = Font(name="Tahoma", size=12, bold=True)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Template_Update_Dossiers.xlsx"'
    return response

# ---------------------------------------------------------
# 3. Process Upload & Create New Dossiers
# ---------------------------------------------------------
def process_create_excel(excel_file, user=None, is_preview: bool = False) -> dict[str, Any]:
    try:
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        ws = cast(Worksheet, wb.active)
    except Exception as e:
        return {"success": False, "error": f"فرمت فایل اکسل نامعتبر است: {str(e)}"}

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"success": False, "error": "فایل اکسل ارسالی خالی است."}

    header_row = rows[0]
    col_map: dict[int, tuple[str, str]] = {}
    for idx, cell in enumerate(header_row):
        norm = _normalize_header(cell)
        if norm in FIELD_BY_NORMALIZED_HEADER:
            col_map[idx] = FIELD_BY_NORMALIZED_HEADER[norm]

    if not col_map:
        return {"success": False, "error": "هیچ سرستون منطبقی در فایل اکسل یافت نشد."}

    existing_national_ids = set(HousingDossier.objects.values_list("national_id", flat=True))
    
    # Calculate next archive number
    last_archive = HousingDossier.objects.order_by("-archive_number").values_list("archive_number", flat=True).first()
    next_archive = (last_archive or 100000) + 1

    valid_rows = []
    errors = []
    seen_in_batch = set()

    for row_idx, row_values in enumerate(rows[1:], start=2):
        if not any(row_values):
            continue

        row_data = {}
        for col_idx, (field_name, field_type) in col_map.items():
            if col_idx < len(row_values):
                val = row_values[col_idx]
                if val is not None and str(val).strip() != "":
                    if field_type == "str":
                        row_data[field_name] = _clean_str(val)
                    elif field_type == "int":
                        row_data[field_name] = _clean_int(val)
                    elif field_type == "decimal":
                        row_data[field_name] = _clean_decimal(val)
                    elif field_type == "price":
                        row_data[field_name] = _clean_price(val)
                    elif field_type == "bool":
                        row_data[field_name] = _clean_bool(val)

        nat_id = _clean_national_id(row_data.get("national_id", ""))
        row_errors = []

        if not nat_id:
            row_errors.append("کد ملی متقاضی الزامی است.")
        elif len(nat_id) != 10:
            row_errors.append("کد ملی متقاضی باید دقیقاً ۱۰ رقم باشد.")
        elif nat_id in seen_in_batch:
            row_errors.append("کد ملی در همین فایل اکسل تکراری است.")
        elif nat_id in existing_national_ids:
            row_errors.append("این کد ملی قبلاً در سامانه ثبت شده است.")

        if row_errors:
            errors.append({
                "row": row_idx,
                "national_id": nat_id or "نامشخص",
                "name": row_data.get("full_name", "نامشخص"),
                "reasons": row_errors
            })
        else:
            seen_in_batch.add(nat_id)
            row_data["national_id"] = nat_id
            row_data["archive_number"] = next_archive
            next_archive += 1
            valid_rows.append({"row": row_idx, "data": row_data})

    if is_preview:
        return {
            "success": True,
            "preview": True,
            "valid_count": len(valid_rows),
            "failed_count": len(errors),
            "valid_rows": valid_rows[:50],  # sample preview
            "errors": errors
        }

    # Execute DB Insertion
    created_count = 0
    with transaction.atomic():
        for item in valid_rows:
            d = item["data"]
            dossier = HousingDossier.objects.create(**d)
            # Create Audit Log
            sig_hash = hashlib.sha256(f"excel_create:{dossier.id}:{timezone.now().timestamp()}".encode('utf-8')).hexdigest()
            WorkflowSignatureLog.objects.create(
                dossier=dossier,
                from_stage=f"مرحله {dossier.current_stage}",
                to_stage=f"مرحله {dossier.current_stage}",
                actor=user.get_full_name() or user.username if user else "مدیر ارشد سامانه",
                role="مدیر سیستم (بارگذاری اکسل)",
                action="CREATE",
                action_label="ایجاد پرونده از طریق بارگذاری فایل اکسل",
                signature_hash=sig_hash,
                notes="پرونده به صورت گروهی از طریق ماژول اکسل در سامانه ثبت گردید."
            )
            created_count += 1

    return {
        "success": True,
        "preview": False,
        "created_count": created_count,
        "failed_count": len(errors),
        "errors": errors
    }

# ---------------------------------------------------------
# 4. Process Upload & Bulk Update by National ID
# ---------------------------------------------------------
def process_update_excel(excel_file, user=None, is_preview: bool = False) -> dict[str, Any]:
    try:
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        ws = cast(Worksheet, wb.active)
    except Exception as e:
        return {"success": False, "error": f"فرمت فایل اکسل نامعتبر است: {str(e)}"}

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"success": False, "error": "فایل اکسل ارسالی خالی است."}

    header_row = rows[0]
    
    # Dynamic National ID Column Search (supports both Column A and Column B after archive_number)
    nid_col_idx = None
    for idx, cell in enumerate(header_row):
        norm = _normalize_header(cell)
        if norm in FIELD_BY_NORMALIZED_HEADER and FIELD_BY_NORMALIZED_HEADER[norm][0] == "national_id":
            nid_col_idx = idx
            break
        if "کد ملی" in norm:
            nid_col_idx = idx
            break

    if nid_col_idx is None:
        return {"success": False, "error": "ستونی با سرستون «کد ملی متقاضی» در فایل اکسل یافت نشد."}

    col_map: dict[int, tuple[str, str]] = {}
    for idx, cell in enumerate(header_row):
        norm = _normalize_header(cell)
        if norm in FIELD_BY_NORMALIZED_HEADER:
            col_map[idx] = FIELD_BY_NORMALIZED_HEADER[norm]

    seen_nids = set()
    parsed_rows = []

    for row_idx, row_values in enumerate(rows[1:], start=2):
        if not any(row_values):
            continue

        nid = _clean_national_id(row_values[nid_col_idx]) if len(row_values) > nid_col_idx else ""
        row_errors = []

        if not nid:
            row_errors.append("کد ملی الزامی است.")
        elif len(nid) != 10:
            row_errors.append("کد ملی باید دقیقاً ۱۰ رقم باشد.")
        elif nid in seen_nids:
            row_errors.append("کد ملی در فایل تکرار شده است.")
        else:
            seen_nids.add(nid)

        changes = {}
        for col_idx, (field_name, field_type) in col_map.items():
            if col_idx == nid_col_idx or field_name in ("national_id", "archive_number"):
                continue  # skip identifier fields from update diff
            if col_idx < len(row_values):
                val = row_values[col_idx]
                if val is not None and str(val).strip() != "":
                    if field_type == "str":
                        changes[field_name] = _clean_str(val)
                    elif field_type == "int":
                        parsed_int = _clean_int(val)
                        if parsed_int is not None:
                            changes[field_name] = parsed_int
                    elif field_type == "decimal":
                        parsed_dec = _clean_decimal(val)
                        if parsed_dec is not None:
                            changes[field_name] = parsed_dec
                    elif field_type == "price":
                        changes[field_name] = _clean_price(val)
                    elif field_type == "bool":
                        changes[field_name] = _clean_bool(val)

        parsed_rows.append({
            "row": row_idx,
            "nid": nid,
            "changes": changes,
            "errors": row_errors
        })

    # Query DB for all national IDs in batch
    dossiers_by_nid = {
        d.national_id: d
        for d in HousingDossier.objects.filter(national_id__in=seen_nids)
    }

    errors = []
    to_update = []
    unchanged_count = 0

    for item in parsed_rows:
        row_errors = list(item["errors"])
        nid = item["nid"]
        rec = dossiers_by_nid.get(nid)

        if not row_errors and rec is None:
            row_errors.append("پرونده‌ای با این کد ملی در سامانه یافت نشد.")

        if row_errors or rec is None:
            errors.append({
                "row": item["row"],
                "national_id": nid or "نامشخص",
                "name": rec.full_name if rec else "نامشخص",
                "reasons": row_errors
            })
            continue

        # Check locked status (superusers and housing chiefs may update via excel)
        is_admin_user = bool(user and (user.is_superuser or user.is_staff or getattr(getattr(user, 'profile', None), 'is_housing_chief', False)))
        if rec.is_locked and not is_admin_user:
            errors.append({
                "row": item["row"],
                "national_id": nid,
                "name": rec.full_name,
                "reasons": ["این پرونده قفل نهایی گردیده و غیرقابل ویرایش است."]
            })
            continue

        # Diff comparison: only update fields that actually differ
        diff = {}
        diff_display = []
        for f, new_val in item["changes"].items():
            old_val = getattr(rec, f)
            if old_val != new_val:
                diff[f] = new_val
                diff_display.append({
                    "field": f,
                    "label": LABEL_BY_FIELD.get(f, f),
                    "old": str(old_val if old_val is not None else "-"),
                    "new": str(new_val)
                })

        if not diff:
            unchanged_count += 1
            continue

        to_update.append({
            "record": rec,
            "diff": diff,
            "row": item["row"],
            "national_id": nid,
            "name": rec.full_name,
            "diff_display": diff_display
        })

    if is_preview:
        updates_preview = [
            {
                "row": u["row"],
                "national_id": u["national_id"],
                "name": u["name"],
                "diff_display": u["diff_display"],
            }
            for u in to_update[:50]
        ]
        return {
            "success": True,
            "preview": True,
            "valid_count": len(to_update),
            "unchanged_count": unchanged_count,
            "failed_count": len(errors),
            "updates_preview": updates_preview,
            "errors": errors
        }

    # Execute DB Update
    updated_count = 0
    with transaction.atomic():
        for item in to_update:
            rec = item["record"]
            diff = item["diff"]
            update_fields = []
            for f, val in diff.items():
                setattr(rec, f, val)
                update_fields.append(f)

            rec.save(update_fields=update_fields)

            # Audit Trail Log for changes
            field_names_fa = "، ".join(LABEL_BY_FIELD.get(k, k) for k in diff.keys())
            sig_hash = hashlib.sha256(f"excel_update:{rec.id}:{timezone.now().timestamp()}".encode('utf-8')).hexdigest()
            WorkflowSignatureLog.objects.create(
                dossier=rec,
                from_stage=f"مرحله {rec.current_stage}",
                to_stage=f"مرحله {rec.current_stage}",
                actor=user.get_full_name() or user.username if user else "مدیر ارشد سامانه",
                role="مدیر سیستم (بروزرسانی اکسل)",
                action="UPDATE",
                action_label="بروزرسانی فیلدها از طریق اکسل",
                signature_hash=sig_hash,
                notes=f"فیلدهای زیر از طریق فایل اکسل بروزرسانی گردید: {field_names_fa}"
            )
            updated_count += 1

    return {
        "success": True,
        "preview": False,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "failed_count": len(errors),
        "errors": errors
    }


# ---------------------------------------------------------
# 5. Full Export of All Dossiers with Comprehensive Codes
# ---------------------------------------------------------

EXPORT_COLUMNS = [
    # (Header Title, Field Name / Lambda, Type)
    ("شماره بایگانی پرونده", "archive_number", "int"),
    ("کد ملی متقاضی", "national_id", "str"),
    ("مرحله جاری پرونده (۰ تا ۲۱)", "current_stage", "int"),
    ("عنوان مرحله جاری", lambda d: d.current_stage_title, "str"),
    ("واحد سازمانی مرحله جاری", lambda d: d.current_unit, "str"),
    ("سمت اقدام‌کننده مرحله جاری", lambda d: d.current_role, "str"),
    ("وضعیت گردش کار پرونده", lambda d: d.get_status_display(), "str"),
    ("قفل نهایی پرونده", lambda d: "بله" if d.is_locked else "خیر", "str"),
    
    # Personal & Family Information
    ("نام و نام خانوادگی متقاضی", "full_name", "str"),
    ("نام پدر", "father_name", "str"),
    ("تاریخ تولد متقاضی (شمسی)", "birth_date", "str"),
    ("شماره همراه متقاضی", "applicant_phone", "str"),
    ("وضعیت تاهل", "marital_status", "str"),
    ("تاییدیه تاهل", lambda d: "بله" if d.is_married_confirmed else "خیر", "str"),
    ("دهک درآمدی (۱ تا ۱۰)", "decile", "int"),
    ("رتبه انتخاب واحد", "selection_rank", "int"),
    
    # Spouse Information
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
    ("متراژ مفید واحد (م²)", "net_unit_area", "decimal"),
    ("متراژ مشاعات (م²)", "common_area", "decimal"),
    ("جمع کل متراژ واحد (م²)", "total_area", "decimal"),
    ("مساحت واحد (م²)", "unit_area", "decimal"),
    ("شماره انباری", "storage_number", "int"),
    ("مساحت انباری (م²)", "storage_area", "decimal"),
    ("شماره پارکینگ", "parking_number", "int"),
    ("مساحت پارکینگ (م²)", "parking_area", "decimal"),
    ("متراژ پارکینگ مسقف (م²)", "covered_parking_area", "decimal"),

    # Registry Plaques
    ("بخش ثبتی", "registration_section", "str"),
    ("پلاک اصلی", "main_plaque", "int"),
    ("پلاک مفروز", "separated_plaque", "int"),
    ("فرعی از (پلاک فرعی)", "sub_plaque", "int"),
    ("شماره قطعه", "plot_number", "int"),

    # Financial & Loans (amounts in Rials)
    ("قیمت تمام شده بدون وام (ریال)", "base_cost_without_loan", "price"),
    ("مبلغ تسهیلات وام بانکی (ریال)", "bank_loan_amount", "price"),
    ("مبلغ وام صندوق (ریال)", "fund_loan_amount", "price"),
    ("مبلغ نامه پیمانکار (ریال)", "contractor_letter_amount", "price"),
    ("مبلغ وام دهک (ریال)", "decile_loan_amount", "price"),
    ("مبلغ آورده نقدی متقاضی (ریال)", "applicant_equity", "price"),
    ("تایید تامین آورده نقدی", lambda d: "بله" if d.is_equity_funded else "خیر", "str"),
    ("ارسال پیامک آورده نقدی", lambda d: "بله" if d.is_sms_sent else "خیر", "str"),
    ("شماره نامه بانک", "bank_letter_number", "str"),
    ("تاریخ نامه بانک (شمسی)", "bank_letter_date", "str"),
    ("اضافه به لیست ارسالی‌ها به بانک", lambda d: "بله" if d.is_added_to_bank_shipment_list else "خیر", "str"),
    ("ارسال شده به بانک", lambda d: "بله" if d.is_sent_to_bank else "خیر", "str"),
    ("تاریخ ارسال به بانک (شمسی)", "bank_sent_date", "str"),
    ("شماره نامه ارسال به بانک", "bank_sent_letter_number", "str"),
    ("بانک عامل تسهیلات دهک", "decile_loan_bank", "str"),
    ("نهاد تحت حمایت", "supported_institution", "str"),

    # Land Lease & Appraisal
    ("جمع کل قدرالسهم (م²)", "total_land_share", "decimal"),
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
]


def generate_dossiers_export(queryset=None) -> HttpResponse:
    """
    Generate and stream a comprehensive, professional Excel workbook containing
    all records, codes, plaque numbers, financial values, and tracking metadata.
    """
    if queryset is None:
        queryset = HousingDossier.objects.all().order_by("-archive_number")

    wb = openpyxl.Workbook()
    ws = cast(Worksheet, wb.active)
    ws.title = "پرونده‌های مسکن مسکن‌یار"
    ws.views.sheetView[0].rightToLeft = True

    headers = [col[0] for col in EXPORT_COLUMNS]
    ws.append(headers)

    header_fill = PatternFill(start_color="0F2744", end_color="0F2744", fill_type="solid")
    key_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Tahoma", size=9, bold=True, color="FFFFFF")
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.row_dimensions[1].height = 30

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = key_fill if col_idx <= 2 else header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    # Freeze panes at Column C, Row 2 (archive number and national ID remain frozen)
    ws.freeze_panes = "C2"

    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    data_font = Font(name="Tahoma", size=9)

    for row_idx, dossier in enumerate(queryset, start=2):
        ws.row_dimensions[row_idx].height = 22
        current_fill = zebra_fill if row_idx % 2 == 1 else white_fill

        for col_idx, (col_title, accessor, col_type) in enumerate(EXPORT_COLUMNS, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = border
            cell.fill = current_fill

            if callable(accessor):
                val = accessor(dossier)
            else:
                val = getattr(dossier, accessor, "")

            if val is None:
                val = ""

            if col_type == "int":
                if val != "" and val is not None:
                    try:
                        cell.value = int(val)
                        cell.number_format = "#,##0" if ("مبلغ" in col_title or "ریال" in col_title) else "0"
                    except Exception:
                        cell.value = str(val)
                else:
                    cell.value = ""
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_type == "price":
                if val != "" and val is not None:
                    try:
                        cell.value = int(val)
                        cell.number_format = "#,##0"
                    except Exception:
                        cell.value = str(val)
                else:
                    cell.value = 0
                    cell.number_format = "#,##0"
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif col_type == "decimal":
                if val != "" and val is not None:
                    try:
                        cell.value = float(val)
                        cell.number_format = "0.00"
                    except Exception:
                        cell.value = str(val)
                else:
                    cell.value = ""
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                s_val = str(val).strip() if val is not None else ""
                cell.value = s_val
                cell.number_format = "@"
                if "کد ملی" in col_title or "شماره همراه" in col_title or "تاریخ" in col_title:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="right", vertical="center")

    # Auto-adjust column widths
    for col_idx in range(1, len(headers) + 1):
        letter = get_column_letter(col_idx)
        header_len = len(headers[col_idx - 1])
        ws.column_dimensions[letter].width = max(14, min(36, header_len + 5))

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    now_j = jdatetime.datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"MaskanYar_Dossiers_Export_{now_j}.xlsx"

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
