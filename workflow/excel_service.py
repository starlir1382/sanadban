import os
import tempfile
import threading
import time
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
from .models import HousingDossier, WorkflowSignatureLog, ProjectBankMapping

# ---------------------------------------------------------
# Comprehensive Mapping for HousingDossier Fields
# (Official Persian Header -> Model Field Name)
# ---------------------------------------------------------
TEMPLATE_FIELD_SPECS = [
    # Key Identifier
    ("کد ملی متقاضی", "national_id", "str"),
    ("شماره بایگانی پرونده", "archive_number", "int"),
    
    # Personal & Family Information
    ("نام متقاضی", "first_name", "str"),
    ("نام خانوادگی متقاضی", "last_name", "str"),
    ("نام پدر", "father_name", "str"),
    ("تاریخ تولد متقاضی (شمسی)", "birth_date", "str"),
    ("شماره شناسنامه متقاضی", "applicant_id_number", "str"),
    ("محل صدور شناسنامه متقاضی", "applicant_birth_place", "str"),
    ("شماره همراه متقاضی", "applicant_phone", "str"),
    ("وضعیت تاهل", "marital_status", "str"),
    ("دهک درآمدی (۱ تا ۱۰)", "decile", "int"),
    ("رتبه انتخاب واحد", "selection_rank", "int"),
    
    # Spouse Information
    ("نام همسر", "spouse_first_name", "str"),
    ("نام خانوادگی همسر", "spouse_last_name", "str"),
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
    ("کد پروژه", lambda d: d.project_code_display, "str"),
    ("نام بانک متقاضی", lambda d: d.bank_display_name, "str"),
    ("شعبه بانک متقاضی", lambda d: d.bank_branch_display, "str"),
    ("کد پروژه", "project_code", "str"),
    ("نام بانک متقاضی", "bank_name", "str"),
    ("شعبه بانک متقاضی", "bank_branch", "str"),
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
    ("شماره نامه بانک", "bank_letter_number", "str"),
    ("تاریخ نامه بانک (شمسی)", "bank_letter_date", "str"),
    ("ارسال شده به بانک", "is_sent_to_bank", "bool"),
    ("تاریخ ارسال به بانک (شمسی)", "bank_sent_date", "str"),
    ("شماره نامه ارسال به بانک", "bank_sent_letter_number", "str"),
    ("اضافه به لیست ارسالی‌ها به بانک", "is_added_to_bank_shipment_list", "bool"),
    ("بانک عامل تسهیلات دهک", "decile_loan_bank", "str"),
    ("نهاد تحت حمایت", "supported_institution", "str"),

    # Land Lease & Appraisal
    ("جمع کل قدرالسهم (مترمربع)", "total_land_share", "decimal"),
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
    ("مرحله جاری پرونده (۱ تا ۲۱)", "current_stage", "int"),
]

# EXCEL_FIELD_SPECS contains canonical template fields plus backward-compatible aliases
EXCEL_FIELD_SPECS = TEMPLATE_FIELD_SPECS + [
    ("شماره بایگانی", "archive_number", "int"),
    ("نام", "first_name", "str"),
    ("نام خانوادگی", "last_name", "str"),
    ("نام متقاضی", "first_name", "str"),
    ("نام خانوادگی متقاضی", "last_name", "str"),
    ("نام و نام خانوادگی", "full_name", "str"),
    ("نام و نام خانوادگی متقاضی", "full_name", "str"),
    ("نام کامل متقاضی", "full_name", "str"),
    ("نام همسر", "spouse_first_name", "str"),
    ("نام خانوادگی همسر", "spouse_last_name", "str"),
    ("نام و نام خانوادگی همسر", "spouse_full_name", "str"),
    ("شماره شناسنامه", "applicant_id_number", "str"),
    ("شناسنامه متقاضی", "applicant_id_number", "str"),
    ("شناسنامه", "applicant_id_number", "str"),
    ("محل صدور متقاضی", "applicant_birth_place", "str"),
    ("محل صدور", "applicant_birth_place", "str"),
    ("محل صدور شناسنامه", "applicant_birth_place", "str"),
    ("محل تولد متقاضی", "applicant_birth_place", "str"),
    ("کد پروژه ساختمانی", "project_code", "str"),
    ("کد طرح", "project_code", "str"),
    ("بانک متقاضی", "bank_name", "str"),
    ("نام بانک", "bank_name", "str"),
    ("بانک عامل", "bank_name", "str"),
    ("بانک", "bank_name", "str"),
    ("شعبه بانک", "bank_branch", "str"),
    ("نام شعبه", "bank_branch", "str"),
    ("کد شعبه", "bank_branch", "str"),
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
    return d[:10] if d else ""

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

    headers = [spec[0] for spec in TEMPLATE_FIELD_SPECS]
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

    headers = [spec[0] for spec in TEMPLATE_FIELD_SPECS]
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
        "۷) مرحله جاری پرونده را در صورت نیاز به انتقال، عددی بین ۱ تا ۲۱ وارد فرمایید.",
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
    wb = None
    try:
        # Use read_only=True for memory efficiency on massive datasets (e.g. 35,000+ rows)
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = cast(Worksheet, wb.active)
        if ws is None:
            return {"success": False, "error": "کاربرگ اکسل یافت نشد."}
    except Exception as e:
        return {"success": False, "error": f"فرمت فایل اکسل نامعتبر است: {str(e)}"}

    try:
        row_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(row_iter)
        except StopIteration:
            return {"success": False, "error": "فایل اکسل ارسالی خالی است."}

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

        project_bank_map = {m.project_name: m for m in ProjectBankMapping.objects.all()}
        valid_rows = []
        errors = []
        seen_in_batch = set()

        for row_idx, row_values in enumerate(row_iter, start=2):
            if not row_values or not any(row_values):
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

            # Synchronize applicant names (نام و نام خانوادگی متقاضی)
            fn = row_data.get("first_name", "").strip()
            ln = row_data.get("last_name", "").strip()
            fln = row_data.get("full_name", "").strip()

            if fn or ln:
                row_data["first_name"] = fn
                row_data["last_name"] = ln
                row_data["full_name"] = f"{fn} {ln}".strip()
            elif fln:
                parts = fln.split(maxsplit=1)
                row_data["first_name"] = parts[0] if parts else ""
                row_data["last_name"] = parts[1] if len(parts) > 1 else ""
                row_data["full_name"] = fln

            # Synchronize spouse names (نام و نام خانوادگی همسر)
            sfn = row_data.get("spouse_first_name", "").strip()
            sln = row_data.get("spouse_last_name", "").strip()
            sfln = row_data.get("spouse_full_name", "").strip()

            if sfn or sln:
                row_data["spouse_first_name"] = sfn
                row_data["spouse_last_name"] = sln
                row_data["spouse_full_name"] = f"{sfn} {sln}".strip()
            elif sfln:
                parts = sfln.split(maxsplit=1)
                row_data["spouse_first_name"] = parts[0] if parts else ""
                row_data["spouse_last_name"] = parts[1] if len(parts) > 1 else ""
                row_data["spouse_full_name"] = sfln

            # Auto-resolve bank details from ProjectBankMapping if empty
            proj = row_data.get("project", "").strip()
            if proj and proj in project_bank_map:
                m = project_bank_map[proj]
                if not row_data.get("bank_name"):
                    row_data["bank_name"] = m.get_bank_code_display()
                if not row_data.get("project_code") and m.project_code:
                    row_data["project_code"] = m.project_code
                if not row_data.get("bank_branch") and m.branch_name:
                    row_data["bank_branch"] = m.branch_name

            # Sanitize dates and national IDs against Postgres string overflow
            for dt_field in ["birth_date", "spouse_birth_date", "bank_letter_date"]:
                if dt_field in row_data and row_data[dt_field]:
                    row_data[dt_field] = str(row_data[dt_field]).strip()[:30]
            if "spouse_national_id" in row_data and row_data["spouse_national_id"]:
                row_data["spouse_national_id"] = _clean_national_id(row_data["spouse_national_id"])

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

        capped_errors = errors[:100]
        if len(errors) > 100:
            capped_errors.append({
                "row": "...",
                "national_id": "...",
                "name": "",
                "reasons": [f"و {len(errors) - 100} خطای دیگر..."]
            })

        if is_preview:
            return {
                "success": True,
                "preview": True,
                "valid_count": len(valid_rows),
                "failed_count": len(errors),
                "valid_rows": valid_rows[:50],  # sample preview
                "errors": capped_errors
            }

        # Execute DB Insertion in Batches of 1,000 to avoid DB locks & memory pressure
        created_count = 0
        CHUNK_SIZE = 1000
        actor_name = user.get_full_name() or user.username if user else "مدیر ارشد سامانه"
        
        for i in range(0, len(valid_rows), CHUNK_SIZE):
            chunk = valid_rows[i:i + CHUNK_SIZE]
            with transaction.atomic():
                dossier_objs = [HousingDossier(**item["data"]) for item in chunk]
                # batch_size=500 keeps parameter count well below SQLite limit
                created_dossiers = HousingDossier.objects.bulk_create(dossier_objs, batch_size=500)

                # Bulk create signature logs
                now_ts = timezone.now().timestamp()
                log_objs = []
                for dossier in created_dossiers:
                    sig_hash = hashlib.sha256(f"excel_create:{dossier.id}:{now_ts}".encode('utf-8')).hexdigest()
                    log_objs.append(WorkflowSignatureLog(
                        dossier=dossier,
                        from_stage=f"مرحله {dossier.current_stage}",
                        to_stage=f"مرحله {dossier.current_stage}",
                        actor=actor_name,
                        role="مدیر سیستم (بارگذاری اکسل)",
                        action="CREATE",
                        action_label="ایجاد پرونده از طریق بارگذاری فایل اکسل",
                        signature_hash=sig_hash,
                        notes="پرونده به صورت گروهی از طریق ماژول اکسل در سامانه ثبت گردید."
                    ))
                WorkflowSignatureLog.objects.bulk_create(log_objs, batch_size=500)
                created_count += len(created_dossiers)

        return {
            "success": True,
            "preview": False,
            "created_count": created_count,
            "failed_count": len(errors),
            "errors": capped_errors
        }
    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass

# ---------------------------------------------------------
# 4. Process Upload & Bulk Update by National ID
# ---------------------------------------------------------
def process_update_excel(excel_file, user=None, is_preview: bool = False) -> dict[str, Any]:
    wb = None
    try:
        # Use read_only=True for memory efficiency on massive datasets (e.g. 35,000+ rows)
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = cast(Worksheet, wb.active)
        if ws is None:
            return {"success": False, "error": "کاربرگ اکسل یافت نشد."}
    except Exception as e:
        return {"success": False, "error": f"فرمت فایل اکسل نامعتبر است: {str(e)}"}

    try:
        row_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(row_iter)
        except StopIteration:
            return {"success": False, "error": "فایل اکسل ارسالی خالی است."}

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

        for row_idx, row_values in enumerate(row_iter, start=2):
            if not row_values or not any(row_values):
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

        # Query DB in chunks of 1000 to prevent SQLite "too many SQL variables" operational error
        dossiers_by_nid = {}
        seen_nids_list = list(seen_nids)
        CHUNK_QUERY = 1000
        for i in range(0, len(seen_nids_list), CHUNK_QUERY):
            chunk_nids = seen_nids_list[i:i + CHUNK_QUERY]
            for d in HousingDossier.objects.filter(national_id__in=chunk_nids):
                dossiers_by_nid[d.national_id] = d

        errors = []
        to_update = []
        unchanged_count = 0
        is_admin_user = bool(user and (user.is_superuser or user.is_staff or getattr(getattr(user, 'profile', None), 'is_housing_chief', False)))

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

            if rec.is_locked and not is_admin_user:
                errors.append({
                    "row": item["row"],
                    "national_id": nid,
                    "name": rec.full_name,
                    "reasons": ["این پرونده قفل نهایی گردیده و غیرقابل ویرایش است."]
                })
                continue

            # Auto-resolve bank if project was updated or missing
            proj = item["changes"].get("project", rec.project or "").strip()
            project_bank_map = {m.project_name: m for m in ProjectBankMapping.objects.all()}
            if proj and proj in project_bank_map:
                m = project_bank_map[proj]
                if not item["changes"].get("bank_name") and not rec.bank_name:
                    item["changes"]["bank_name"] = m.get_bank_code_display()
                if not item["changes"].get("project_code") and not rec.project_code and m.project_code:
                    item["changes"]["project_code"] = m.project_code
                if not item["changes"].get("bank_branch") and not rec.bank_branch and m.branch_name:
                    item["changes"]["bank_branch"] = m.branch_name

            for dt_field in ["birth_date", "spouse_birth_date", "bank_letter_date"]:
                if dt_field in item["changes"] and item["changes"][dt_field]:
                    item["changes"][dt_field] = str(item["changes"][dt_field]).strip()[:30]
            if "spouse_national_id" in item["changes"] and item["changes"]["spouse_national_id"]:
                item["changes"]["spouse_national_id"] = _clean_national_id(item["changes"]["spouse_national_id"])

            # Synchronize applicant names in update diff
            if "first_name" in item["changes"] or "last_name" in item["changes"]:
                new_fn = item["changes"].get("first_name", rec.first_name or "")
                new_ln = item["changes"].get("last_name", rec.last_name or "")
                item["changes"]["first_name"] = new_fn
                item["changes"]["last_name"] = new_ln
                item["changes"]["full_name"] = f"{new_fn} {new_ln}".strip()
            elif "full_name" in item["changes"]:
                parts = str(item["changes"]["full_name"]).strip().split(maxsplit=1)
                item["changes"]["first_name"] = parts[0] if parts else ""
                item["changes"]["last_name"] = parts[1] if len(parts) > 1 else ""

            # Synchronize spouse names in update diff
            if "spouse_first_name" in item["changes"] or "spouse_last_name" in item["changes"]:
                new_sfn = item["changes"].get("spouse_first_name", rec.spouse_first_name or "")
                new_sln = item["changes"].get("spouse_last_name", rec.spouse_last_name or "")
                item["changes"]["spouse_first_name"] = new_sfn
                item["changes"]["spouse_last_name"] = new_sln
                item["changes"]["spouse_full_name"] = f"{new_sfn} {new_sln}".strip()
            elif "spouse_full_name" in item["changes"]:
                parts = str(item["changes"]["spouse_full_name"]).strip().split(maxsplit=1)
                item["changes"]["spouse_first_name"] = parts[0] if parts else ""
                item["changes"]["spouse_last_name"] = parts[1] if len(parts) > 1 else ""

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

        capped_errors = errors[:100]
        if len(errors) > 100:
            capped_errors.append({
                "row": "...",
                "national_id": "...",
                "name": "",
                "reasons": [f"و {len(errors) - 100} خطای دیگر..."]
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
                "errors": capped_errors
            }

        # Execute DB Update in chunks of 1000 with bulk_update and bulk audit logs
        updated_count = 0
        CHUNK_SIZE = 1000
        actor_name = user.get_full_name() or user.username if user else "مدیر ارشد سامانه"

        for i in range(0, len(to_update), CHUNK_SIZE):
            chunk = to_update[i:i + CHUNK_SIZE]
            with transaction.atomic():
                chunk_records = []
                fields_to_update = set()
                log_objs = []
                now_ts = timezone.now().timestamp()

                for item in chunk:
                    rec = item["record"]
                    diff = item["diff"]
                    for f, val in diff.items():
                        setattr(rec, f, val)
                        fields_to_update.add(f)
                    chunk_records.append(rec)

                    field_names_fa = "، ".join(LABEL_BY_FIELD.get(k, k) for k in diff.keys())
                    sig_hash = hashlib.sha256(f"excel_update:{rec.id}:{now_ts}".encode('utf-8')).hexdigest()
                    log_objs.append(WorkflowSignatureLog(
                        dossier=rec,
                        from_stage=f"مرحله {rec.current_stage}",
                        to_stage=f"مرحله {rec.current_stage}",
                        actor=actor_name,
                        role="مدیر سیستم (بروزرسانی اکسل)",
                        action="UPDATE",
                        action_label="بروزرسانی فیلدها از طریق اکسل",
                        signature_hash=sig_hash,
                        notes=f"فیلدهای زیر از طریق فایل اکسل بروزرسانی گردید: {field_names_fa}"
                    ))

                if fields_to_update:
                    HousingDossier.objects.bulk_update(chunk_records, fields=list(fields_to_update), batch_size=500)
                WorkflowSignatureLog.objects.bulk_create(log_objs, batch_size=500)
                updated_count += len(chunk_records)

        return {
            "success": True,
            "preview": False,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "failed_count": len(errors),
            "errors": capped_errors
        }
    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass


# ---------------------------------------------------------
# 5. Full Export of All Dossiers with Comprehensive Codes
# ---------------------------------------------------------

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
]


# Concurrency guard & file cache for full exports
_export_lock = threading.Lock()
_export_cache = {}  # cache_key -> (file_path, timestamp, file_size)

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
