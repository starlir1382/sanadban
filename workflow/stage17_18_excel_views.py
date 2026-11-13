import io
import json
import re
from typing import Any
import jdatetime
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .field_permissions import is_alireza_nazari_user
from .models import DirectorateShipment, DossierCheck, HousingDossier, normalize_national_id


def _enforce_alireza_nazari(user):
    if not is_alireza_nazari_user(user):
        raise PermissionDenied("دسترسی به این بخش منحصراً برای کاربر علیرضا نظری مجاز است.")


def _resolve_actor(user):
    profile = getattr(user, "profile", None)
    actor_name = profile.full_name if (profile and profile.full_name) else (user.get_full_name() or user.username)
    actor_role = profile.role_title if (profile and profile.role_title) else "کارشناس"
    return actor_name, actor_role


def _today_jalali_date() -> str:
    return jdatetime.datetime.fromgregorian(datetime=timezone.localtime(timezone.now())).strftime("%Y/%m/%d")


_FA_AR_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _to_clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).translate(_FA_AR_DIGITS).strip()


def _to_int(val: Any) -> int:
    if val is None:
        return 0
    s = str(val).translate(_FA_AR_DIGITS)
    s = re.sub(r"[^\d-]", "", s)
    try:
        return int(s)
    except Exception:
        return 0


def _norm_hdr(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).replace("ي", "ی").replace("ك", "ک").replace("\u200c", "").replace(" ", "").replace("_", "").replace("-", "").strip()
    return s.translate(_FA_AR_DIGITS).lower()


@login_required(login_url="login")
def stage17_18_excel_hub_view(request):
    """
    Dedicated dashboard for Alireza Nazari to manage Excel uploads, template downloads,
    and data exports for Stage 17 (تسهیلات چک) and Stage 18 (آماده‌سازی).
    """
    _enforce_alireza_nazari(request.user)

    # Stats for Stage 17 (تسهیلات چک)
    stage17_total = HousingDossier.objects.filter(current_stage=17).count()
    stage17_visited = HousingDossier.objects.filter(
        models.Q(loan_visit_date__gt="") | models.Q(visit_date__gt=""),
        current_stage=17,
    ).count()
    stage17_shipped = HousingDossier.objects.filter(
        models.Q(is_loan_sent_to_directorate=True) | models.Q(loan_directorate_shipment__isnull=False),
        current_stage=17,
    ).count()

    # Stats for Stage 18 (آماده‌سازی)
    stage18_total = HousingDossier.objects.filter(current_stage=18).count()
    stage18_visited = HousingDossier.objects.filter(
        models.Q(prep_visit_date__gt="") | models.Q(visit_date__gt=""),
        current_stage=18,
    ).count()
    stage18_shipped = HousingDossier.objects.filter(
        models.Q(is_prep_sent_to_directorate=True) | models.Q(prep_directorate_shipment__isnull=False),
        current_stage=18,
    ).count()

    context = {
        "stage17_total": stage17_total,
        "stage17_visited": stage17_visited,
        "stage17_shipped": stage17_shipped,
        "stage18_total": stage18_total,
        "stage18_visited": stage18_visited,
        "stage18_shipped": stage18_shipped,
    }
    return render(request, "dossiers/stage17_18_excel.html", context)


# ---- Stage 17 Headers: مرحله وام دهک (مشخصات و چک‌ها) -----------------
# Strictly per user specification: national id, شماره تعهدنامه, تاریخ تعهدنامه, نهاد تحت حمایت, بانک عامل تسهیلات, and checks
STAGE_17_HEADERS = [
    "ردیف",
    "کد ملی",
    "شماره تعهدنامه",
    "تاریخ تعهدنامه",
    "نهاد تحت حمایت",
    "بانک عامل تسهیلات",
    "تاریخ چک 1", "مقدار چک 1", "کد صیادی چک 1", "نام بانک چک 1",
    "تاریخ چک 2", "مقدار چک 2", "کد صیادی چک 2", "نام بانک چک 2",
    "تاریخ چک 3", "مقدار چک 3", "کد صیادی چک 3", "نام بانک چک 3",
    "تاریخ چک 4", "مقدار چک 4", "کد صیادی چک 4", "نام بانک چک 4",
    "تاریخ چک 5", "مقدار چک 5", "کد صیادی چک 5", "نام بانک چک 5",
    "تاریخ چک 6", "مقدار چک 6", "کد صیادی چک 6", "نام بانک چک 6",
    "تاریخ چک 7", "مقدار چک 7", "کد صیادی چک 7", "نام بانک چک 7",
]


# ---- Stage 18 Headers (Strictly per user specification) -----------------
STAGE_18_HEADERS = [
    "ردیف",
    "نام",
    "کد ملی",
    "شماره تلفن",
    "پلاک اصلی",
    "پلاک مفروز",
    "پلاک فرعی",
    "قطعه",
    "پیمانکار",
    "محل پرونده",
    "نام دفترخانه",
    "تاریخ تغییر محل پرونده",
    "وضعیت سند",
    "نامه راه شهرسازی",
    "مبلغ پیش‌پرداخت",
    "کد پیگیری پیش‌پرداخت",
    "مبلغ اجاره",
    "کد پیگیری اجاره",
    "تاریخ چک 1", "مقدار چک 1", "کد صیادی چک 1", "نام بانک چک 1",
    "تاریخ چک 2", "مقدار چک 2", "کد صیادی چک 2", "نام بانک چک 2",
    "تاریخ چک 3", "مقدار چک 3", "کد صیادی چک 3", "نام بانک چک 3",
    "تاریخ چک 4", "مقدار چک 4", "کد صیادی چک 4", "نام بانک چک 4",
    "تاریخ چک 5", "مقدار چک 5", "کد صیادی چک 5", "نام بانک چک 5",
    "تاریخ چک 6", "مقدار چک 6", "کد صیادی چک 6", "نام بانک چک 6",
    "تاریخ چک 7", "مقدار چک 7", "کد صیادی چک 7", "نام بانک چک 7",
]


def _build_styled_workbook(title: str, headers: list[str]) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.views.sheetView[0].rightToLeft = True

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Tahoma", size=10, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = 18

    return wb


@login_required(login_url="login")
def stage17_18_template_download_view(request, stage: int):
    """
    Download Excel template for Stage 17 or Stage 18.
    """
    _enforce_alireza_nazari(request.user)

    if stage == 17:
        title = "قالب ورود اطلاعات مرحله ۱۷"
        headers = STAGE_17_HEADERS
        filename = "template_stage_17_tashilat.xlsx"
    elif stage == 18:
        title = "قالب ورود اطلاعات مرحله ۱۸"
        headers = STAGE_18_HEADERS
        filename = "template_stage_18_amadesazi.xlsx"
    else:
        return JsonResponse({"error": "مرحله نامعتبر است. فقط ۱۷ و ۱۸ مجاز است."}, status=400)

    wb = _build_styled_workbook(title, headers)

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)

    response = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="login")
def stage17_18_data_export_view(request, stage: int):
    """
    Export existing dossier data for Stage 17 or Stage 18.
    """
    _enforce_alireza_nazari(request.user)

    if stage == 17:
        title = "داده‌های مرحله ۱۷ - تسهیلات"
        headers = STAGE_17_HEADERS
        filename = "export_stage_17_tashilat.xlsx"
        dossiers = HousingDossier.objects.filter(current_stage=17).select_related("loan_directorate_shipment")
    elif stage == 18:
        title = "داده‌های مرحله ۱۸ - آماده‌سازی"
        headers = STAGE_18_HEADERS
        filename = "export_stage_18_amadesazi.xlsx"
        dossiers = HousingDossier.objects.filter(current_stage=18).select_related("prep_directorate_shipment")
    else:
        return JsonResponse({"error": "مرحله نامعتبر است."}, status=400)

    wb = _build_styled_workbook(title, headers)
    ws = wb.active

    for idx, d in enumerate(dossiers, start=1):
        if stage == 17:
            row = [
                idx,
                d.national_id or "",
                d.commitment_number or "",
                d.commitment_date or "",
                d.supported_institution or "",
                d.decile_loan_bank or d.bank_name or "",
            ]
            # Fetch checks for Stage 17 (up to 7)
            checks_list = []
            if d.check_entries_json and d.check_entries_json.strip() not in ("[]", ""):
                try:
                    checks_list = json.loads(d.check_entries_json)
                except Exception:
                    checks_list = []
            if not checks_list:
                rel_checks = d.check_items.filter(check_type="LOAN").order_by("row_number")
                for c in rel_checks:
                    checks_list.append({
                        "cash_date": c.cash_date,
                        "check_amount": c.check_amount,
                        "check_sayadi_code": c.check_sayadi_code,
                        "bank_name": c.bank_name,
                    })

            for i in range(7):
                if i < len(checks_list):
                    c = checks_list[i]
                    row.extend([
                        c.get("cash_date") or "",
                        c.get("check_amount") or "",
                        c.get("check_sayadi_code") or "",
                        c.get("bank_name") or "",
                    ])
                else:
                    row.extend(["", "", "", ""])
        else:
            shipped_str = "ارسال شده" if d.is_prep_sent_to_directorate or d.prep_directorate_shipment else "در انتظار اسکن"
            row = [
                idx,
                d.full_name or "",
                d.national_id or "",
                d.applicant_phone or "",
                d.main_plaque or "",
                d.block_code or d.block_name or "",
                d.sub_plaque or "",
                d.plot_number or "",
                d.project or "",
                d.current_location_display or "کارگزاری ثبت چک ها",
                getattr(d, "notary_office_name", "") or "",
                d.prep_visit_date or d.visit_date or "",
                shipped_str,
                d.rah_letter or "",
                d.cash_preparation_amount or "",
                d.prepayment_code or "",
                d.tenant_price or "",
                d.tenant_code or "",
            ]

            # Fetch checks for Stage 18 (up to 7)
            checks_list = []
            if d.preparation_check_entries_json and d.preparation_check_entries_json.strip() not in ("[]", ""):
                try:
                    checks_list = json.loads(d.preparation_check_entries_json)
                except Exception:
                    checks_list = []
            if not checks_list:
                rel_checks = d.check_items.filter(check_type="PREPARATION").order_by("row_number")
                for c in rel_checks:
                    checks_list.append({
                        "cash_date": c.cash_date,
                        "check_amount": c.check_amount,
                        "check_sayadi_code": c.check_sayadi_code,
                        "bank_name": c.bank_name,
                    })

            for i in range(7):
                if i < len(checks_list):
                    c = checks_list[i]
                    row.extend([
                        c.get("cash_date") or "",
                        c.get("check_amount") or "",
                        c.get("check_sayadi_code") or "",
                        c.get("bank_name") or "",
                    ])
                else:
                    row.extend(["", "", "", ""])

        ws.append(row)

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)

    response = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="login")
@require_POST
def stage17_18_excel_upload_view(request, stage: int):
    """
    Upload and update dossiers from Excel for Stage 17 or Stage 18.
    For Stage 18 (آماده‌سازی):
      - References and updates records strictly by national ID
      - Updates rah_letter, cash_preparation_amount, prepayment_code, tenant_price, tenant_code
      - Updates up to 7 checks (cash_date, check_amount, check_sayadi_code, bank_name)
      - If 'وضعیت سند' == 'ارسال شده', marks dossier as sent to Directorate and aggregates into a single batch!
    """
    _enforce_alireza_nazari(request.user)

    if stage not in (17, 18):
        return JsonResponse({"success": False, "error": "مرحله نامعتبر است."}, status=400)

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return JsonResponse({"success": False, "error": "هیچ فایلی ارسال نشده است."}, status=400)

    if not excel_file.name.lower().endswith((".xlsx", ".xls")):
        return JsonResponse({"success": False, "error": "فرمت فایل نامعتبر است. فقط فایل‌های اکسل (.xlsx) پذیرفته می‌شوند."}, status=400)

    actor_name, _ = _resolve_actor(request.user)

    try:
        wb = openpyxl.load_workbook(excel_file, data_only=True, read_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return JsonResponse({"success": False, "error": "فایل اکسل ارسالی خالی است."}, status=400)

        header_row = [_norm_hdr(c) for c in rows[0]]

        # Helper to find column index by multiple keyword variants (exact match first, then substring)
        def find_col(*variants):
            norm_variants = [_norm_hdr(v) for v in variants]
            # Exact match first
            for i, h in enumerate(header_row):
                for nv in norm_variants:
                    if h == nv:
                        return i
            # Fallback: substring match
            for i, h in enumerate(header_row):
                for nv in norm_variants:
                    if nv and nv in h:
                        return i
            return None

        # Resolve column indices
        c_nat_id = find_col("کدملی", "nationalid")
        if c_nat_id is None:
            return JsonResponse({"success": False, "error": "ستون «کد ملی» در فایل اکسل یافت نشد."}, status=400)

        c_status = find_col("وضعیتسند", "وضعیت")
        c_date_change = find_col("تاریختغییرمحلپرونده", "تاریختغییرمحل", "تاریخمراجعه")
        c_rah = find_col("نامه‌راهشهرسازی", "نامه‌راهوشهرسازی", "نامه‌راه", "نامهراه")
        c_prep_cash = find_col("مبلغپیشپرداخت", "پیشپرداخت", "مبلغنقدیآماده")
        c_prep_code = find_col("کدپیگیریپیشپرداخت", "شناسهپیشپرداخت", "کدپیشپرداخت")
        c_rent_price = find_col("مبلاجار", "مبلغاجاره", "اجاره")
        c_rent_code = find_col("کدپیگیریاجاره", "شناسهاجاره", "پیگیریاجاره")

        # Stage 17 specific columns (وام دهک: مشخصات و چک‌ها)
        c_commit_num = find_col("شمارهتعهدنامه", "شمارهتعهد", "تعهدنامه", "شمارهتعهدنامهمحضری", "commitmentnumber")
        c_commit_date = find_col("تاریختعهدنامه", "تاریختعهد", "commitmentdate")
        c_institution = find_col("نهادتحتحمایت", "نهادتکفلت", "تحتحمایت", "نهادحمایتی", "نهاد", "supportedinstitution")
        c_bank_agent = find_col("بانکعاملتسهیلات", "بانکعامل", "بانکتسهیلات", "بانکعاملتسهیلاتدهک", "decileloanbank", "بانک")

        # Resolve 7 checks columns
        chk_cols = []
        for i in range(1, 8):
            c_date = find_col(f"تاریخچک{i}", f"سررسیدچک{i}")
            c_amt = find_col(f"مقدارچک{i}", f"مبلغچک{i}")
            c_sayadi = find_col(f"کدصیادیچک{i}", f"صیادیچک{i}", f"کدصیادی{i}")
            c_bank = find_col(f"نامبانکچک{i}", f"بانکچک{i}")
            chk_cols.append({
                "num": i,
                "date": c_date,
                "amount": c_amt,
                "sayadi": c_sayadi,
                "bank": c_bank,
            })

        updated_count = 0
        shipped_dossiers = []
        not_found_list = []
        now_ts = timezone.now()
        today_jalali = _today_jalali_date()

        with transaction.atomic():
            for row in rows[1:]:
                if not any(c is not None and str(c).strip() for c in row):
                    continue

                raw_nat_id = _to_clean_str(row[c_nat_id])
                if not raw_nat_id or len(raw_nat_id) < 5:
                    continue

                clean_nat_id = normalize_national_id(raw_nat_id)

                dossier = (
                    HousingDossier.objects.select_for_update().filter(national_id=clean_nat_id).first()
                    or HousingDossier.objects.select_for_update().filter(national_id=raw_nat_id).first()
                )

                if not dossier:
                    not_found_list.append(clean_nat_id)
                    continue

                update_fields = []

                # 1. Update Core Fields per stage
                if stage == 17:
                    if c_commit_num is not None and row[c_commit_num] is not None:
                        v = _to_clean_str(row[c_commit_num])
                        if v:
                            dossier.commitment_number = v
                            update_fields.append("commitment_number")

                    if c_commit_date is not None and row[c_commit_date] is not None:
                        v = _to_clean_str(row[c_commit_date])
                        if v:
                            dossier.commitment_date = v
                            update_fields.append("commitment_date")

                    if c_institution is not None and row[c_institution] is not None:
                        v = _to_clean_str(row[c_institution])
                        if v:
                            dossier.supported_institution = v
                            update_fields.append("supported_institution")

                    if c_bank_agent is not None and row[c_bank_agent] is not None:
                        v = _to_clean_str(row[c_bank_agent])
                        if v:
                            dossier.decile_loan_bank = v
                            update_fields.append("decile_loan_bank")
                            if not dossier.bank_name:
                                dossier.bank_name = v
                                update_fields.append("bank_name")
                else:
                    if c_rah is not None and row[c_rah] is not None:
                        v = _to_clean_str(row[c_rah])
                        if v:
                            dossier.rah_letter = v
                            update_fields.append("rah_letter")

                    if c_prep_cash is not None and row[c_prep_cash] is not None:
                        v = _to_int(row[c_prep_cash])
                        if v > 0:
                            dossier.cash_preparation_amount = v
                            update_fields.append("cash_preparation_amount")

                    if c_prep_code is not None and row[c_prep_code] is not None:
                        v = _to_clean_str(row[c_prep_code])
                        if v:
                            dossier.prepayment_code = v
                            update_fields.append("prepayment_code")

                    if c_rent_price is not None and row[c_rent_price] is not None:
                        v = _to_int(row[c_rent_price])
                        if v > 0:
                            dossier.tenant_price = v
                            update_fields.append("tenant_price")

                    if c_rent_code is not None and row[c_rent_code] is not None:
                        v = _to_clean_str(row[c_rent_code])
                        if v:
                            dossier.tenant_code = v
                            update_fields.append("tenant_code")

                # Visit date from 'تاریخ تغییر محل پرونده'
                if c_date_change is not None and row[c_date_change] is not None:
                    v = _to_clean_str(row[c_date_change])
                    if v and len(v) >= 8:
                        if stage == 18:
                            dossier.prep_visit_date = v
                            dossier.is_prep_visited = True
                            dossier.prep_visited_by = actor_name
                            dossier.prep_visited_at = now_ts
                            update_fields.extend(["prep_visit_date", "is_prep_visited", "prep_visited_by", "prep_visited_at"])
                        else:
                            dossier.loan_visit_date = v
                            dossier.is_loan_visited = True
                            dossier.loan_visited_by = actor_name
                            dossier.loan_visited_at = now_ts
                            update_fields.extend(["loan_visit_date", "is_loan_visited", "loan_visited_by", "loan_visited_at"])

                # 2. Extract and update 7 checks
                prep_checks_entries = []
                total_prep_chk_amount = 0
                for item in chk_cols:
                    c_date_val = _to_clean_str(row[item["date"]]) if item["date"] is not None else ""
                    c_amt_val = _to_int(row[item["amount"]]) if item["amount"] is not None else 0
                    c_sayadi_val = _to_clean_str(row[item["sayadi"]]) if item["sayadi"] is not None else ""
                    c_bank_val = _to_clean_str(row[item["bank"]]) if item["bank"] is not None else ""

                    if c_amt_val > 0 or c_date_val or c_sayadi_val:
                        prep_checks_entries.append({
                            "row_number": len(prep_checks_entries) + 1,
                            "cash_date": c_date_val,
                            "check_amount": c_amt_val,
                            "check_sayadi_code": c_sayadi_val,
                            "bank_name": c_bank_val,
                        })
                        total_prep_chk_amount += c_amt_val

                if prep_checks_entries:
                    if stage == 18:
                        dossier.preparation_check_entries_json = json.dumps(prep_checks_entries, ensure_ascii=False)
                        dossier.preparation_check_count = len(prep_checks_entries)
                        dossier.total_preparation_check_amount = total_prep_chk_amount
                        dossier.is_preparation_checks_confirmed = True
                        update_fields.extend([
                            "preparation_check_entries_json",
                            "preparation_check_count",
                            "total_preparation_check_amount",
                            "is_preparation_checks_confirmed",
                        ])
                        # Sync relational table DossierCheck
                        dossier.check_items.filter(check_type="PREPARATION").delete()
                        for chk in prep_checks_entries:
                            DossierCheck.objects.create(
                                dossier=dossier,
                                check_type="PREPARATION",
                                row_number=chk["row_number"],
                                cash_date=chk["cash_date"],
                                check_amount=chk["check_amount"],
                                check_sayadi_code=chk["check_sayadi_code"],
                                bank_name=chk["bank_name"],
                            )
                    else:
                        dossier.check_entries_json = json.dumps(prep_checks_entries, ensure_ascii=False)
                        dossier.check_count = len(prep_checks_entries)
                        dossier.total_check_amount = total_prep_chk_amount
                        if prep_checks_entries:
                            dossier.check_amount = prep_checks_entries[0]["check_amount"]
                            dossier.last_check_amount = prep_checks_entries[-1]["check_amount"]
                        dossier.is_decile_loan_confirmed = True
                        dossier.loan_checks_confirmed_by = actor_name
                        dossier.loan_checks_confirmed_at = now_ts
                        update_fields.extend([
                            "check_entries_json",
                            "check_count",
                            "total_check_amount",
                            "check_amount",
                            "last_check_amount",
                            "is_decile_loan_confirmed",
                            "loan_checks_confirmed_by",
                            "loan_checks_confirmed_at",
                        ])
                        dossier.check_items.filter(check_type="LOAN").delete()
                        for chk in prep_checks_entries:
                            DossierCheck.objects.create(
                                dossier=dossier,
                                check_type="LOAN",
                                row_number=chk["row_number"],
                                cash_date=chk["cash_date"],
                                check_amount=chk["check_amount"],
                                check_sayadi_code=chk["check_sayadi_code"],
                                bank_name=chk["bank_name"],
                            )

                # 3. Check 'وضعیت سند' == 'ارسال شده'
                if c_status is not None and row[c_status] is not None:
                    status_str = _to_clean_str(row[c_status])
                    if "ارسال" in status_str:
                        if stage == 18:
                            # Double-ship guard: skip if already marked sent
                            if dossier.is_prep_sent_to_directorate:
                                pass  # already shipped, do not overwrite
                            else:
                                dossier.is_prep_sent_to_directorate = True
                                dossier.prep_directorate_sent_date = dossier.prep_visit_date or today_jalali
                                dossier.prep_directorate_sent_by = actor_name
                                dossier.prep_directorate_sent_at = now_ts
                                update_fields.extend([
                                    "is_prep_sent_to_directorate",
                                    "prep_directorate_sent_date",
                                    "prep_directorate_sent_by",
                                    "prep_directorate_sent_at",
                                ])
                                shipped_dossiers.append(dossier)
                        else:
                            # Double-ship guard: skip if already marked sent
                            if dossier.is_loan_sent_to_directorate:
                                pass  # already shipped, do not overwrite
                            else:
                                dossier.is_loan_sent_to_directorate = True
                                dossier.loan_directorate_sent_date = dossier.loan_visit_date or today_jalali
                                dossier.loan_directorate_sent_by = actor_name
                                dossier.loan_directorate_sent_at = now_ts
                                update_fields.extend([
                                    "is_loan_sent_to_directorate",
                                    "loan_directorate_sent_date",
                                    "loan_directorate_sent_by",
                                    "loan_directorate_sent_at",
                                ])
                                shipped_dossiers.append(dossier)

                if update_fields:
                    dossier.save(update_fields=list(set(update_fields)))
                    updated_count += 1

            # 4. Create single batch shipment for all uploaded records marked 'ارسال شده'
            created_shipment = None
            if shipped_dossiers:
                shipment_type = "PREP" if stage == 18 else "LOAN"
                batch_note = f"ثبت دسته‌جمعی از فایل اکسل {excel_file.name} (علیرضا نظری)"
                created_shipment = DirectorateShipment.objects.create(
                    shipment_type=shipment_type,
                    sent_date=today_jalali,
                    note=batch_note,
                    created_by_user=request.user,
                    created_by=actor_name,
                )
                fk_field = "prep_directorate_shipment" if stage == 18 else "loan_directorate_shipment"
                # Single save per dossier: assign FK directly in one update_fields call
                for d in shipped_dossiers:
                    setattr(d, fk_field, created_shipment)
                    d.save(update_fields=[fk_field])

        shipment_msg = ""
        if created_shipment:
            shipment_msg = f" و محموله {created_shipment.shipment_code} برای {len(shipped_dossiers)} پرونده ارسال‌شده ایجاد گردید."

        return JsonResponse({
            "success": True,
            "stage": stage,
            "updated_count": updated_count,
            "shipped_count": len(shipped_dossiers),
            "shipment_code": created_shipment.shipment_code if created_shipment else None,
            "not_found_count": len(not_found_list),
            "not_found_list": not_found_list[:20],
            "message": f"پردازش با موفقیت انجام شد: {updated_count} پرونده بر اساس کد ملی بروزرسانی شد{shipment_msg}",
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": f"خطا در پردازش فایل اکسل: {str(e)}"}, status=500)
