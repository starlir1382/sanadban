import os
import io
import json
import time
import base64
import hashlib
from decimal import Decimal
from typing import Any, List, Dict

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.worksheet import Worksheet

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from PIL import Image, ImageEnhance
import jdatetime

from .models import (
    HousingDossier,
    DossierAttachment,
    DossierFieldChangeLog,
    WorkflowSignatureLog,
    DossierSignature,
    UserProfile,
)
from .stages import (
    STAGE_ROLES,
    STAGE_DETAILS,
    MIN_STAGE,
    MAX_STAGE,
    TOTAL_STAGES,
)
def _check_admin_access(user):
    if not user.is_authenticated:
        return False
    profile = getattr(user, 'profile', None)
    return user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))


def _get_tehran_now():
    return timezone.localtime(timezone.now())


def _format_tehran_jalali(dt=None, fmt="%Y/%m/%d %H:%M"):
    if dt is None:
        dt = _get_tehran_now()
    elif timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return jdatetime.datetime.fromgregorian(datetime=dt).strftime(fmt)


# =========================================================================
# 1. Excel Hub Dashboard View (مرکز مدیریت و عملیات اکسل)
# =========================================================================

@login_required(login_url='login')
def excel_hub_view(request):
    """
    Dedicated enterprise hub for Excel template downloads, mass workflow stage
    signatures, commission spec/price adjustments, and applicant-spouse swaps.
    Strictly restricted to Superadmins and Housing Chief.
    """
    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))

    if not is_admin:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "دسترسی غیرمجاز: مرکز جامع اکسل و اصلاحات ساختاری صرفاً ویژه مدیران ارشد سیستم و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")

    stages_list = [
        {"id": stg_id, "title": info[2], "role": info[1], "unit": info[0]}
        for stg_id, info in sorted(STAGE_ROLES.items())
    ]

    context = {
        "is_admin": is_admin,
        "user_profile": profile,
        "max_stage": MAX_STAGE,
        "stage_roles": STAGE_ROLES,
        "stages_list": stages_list,
        "total_dossiers": HousingDossier.objects.count(),
        "today_jalali": _format_tehran_jalali(fmt="%Y/%m/%d"),
    }
    return render(request, "admin/excel_hub.html", context)


# =========================================================================
# 2. Template Generator for Excel Operations
# =========================================================================

@login_required(login_url='login')
def download_excel_template_view(request, template_type):
    """
    Generates beautifully styled Persian RTL Excel templates for different operational needs:
    - 'stage_signatures': Mass stage approval with stage columns
    - 'commission': Price / plot specification re-evaluation (invalidates stages 2, 4, 5, 8, 18)
    - 'swap_spouse': Bulk swap primary applicant with spouse
    - 'general_dossiers': General import & update template
    - 'stage_<N>': Specific stage template
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.views.sheetView[0].rightToLeft = True

    header_font = Font(name="B Nazanin", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    filename_prefix = "MaskanYar_Template"

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))

    # Security: Commission and Swap Spouse templates are strictly admin-only
    if template_type in ["commission", "swap_spouse"] and not is_admin:
        return HttpResponseForbidden("دسترسی غیرمجاز: دانلود این قالب صرفاً در اختیار مدیران سیستم است.")

    if template_type == "stage_signatures":
        ws.title = "امضای دسته‌جمعی مراحل"
        filename_prefix = "Template_Stage_Signatures"

        # Determine target stages according to user permissions
        if is_admin:
            target_stages = list(range(1, MAX_STAGE + 1))
        else:
            target_stages = profile.get_allowed_stages_list() if profile else []
            if not target_stages:
                return HttpResponseForbidden("هیچ مرحله مجازی در پروفایل شما برای دانلود قالب امضا تعریف نشده است.")

        # Headers: National ID, optional name, and allowed stage columns
        headers = ["کد ملی متقاضی", "نام متقاضی (اختیاری)"]
        for stg in target_stages:
            stg_title = STAGE_ROLES.get(stg, ("", "", f"مرحله {stg}"))[2]
            headers.append(f"مرحله {stg}: {stg_title}")

        ws.append(headers)

        # Style header row (empty template with only headers as requested)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 30 if col_idx > 2 else 22
        ws.row_dimensions[1].height = 35

    elif template_type == "commission":
        ws.title = "کمیسیون تعدیل و بازنگری"
        filename_prefix = "Template_Commission_Adjustment"

        headers = [
            "کد ملی متقاضی",
            "شماره بایگانی پرونده",
            "نام و نام خانوادگی",
            "قیمت تمام شده بدون وام (ریال)",
            "پلاک اصلی",
            "فرعی از",
            "پلاک مفروز",
            "شماره قطعه",
            "کد نوسازی (شهرداری)",
            "متراژ مفید واحد (مترمربع)",
            "توضیحات کمیسیون"
        ]
        ws.append(headers)

        commission_fill = PatternFill(start_color="9A3412", end_color="9A3412", fill_type="solid")
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = commission_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 24

        sample_row = [
            "0371112233", 100001, "علی رضایی",
            4800000000, 2405, 12, 1, 14, "N-8841-B", 85.50,
            "تعدیل قیمت تمام شده طبق مصوبه کمیسیون مورخ ۱۴۰۵/۰۸"
        ]
        ws.append(sample_row)

    elif template_type == "swap_spouse":
        ws.title = "جایگزینی متقاضی با همسر"
        filename_prefix = "Template_Swap_Applicant_Spouse"

        headers = [
            "کد ملی متقاضی فعلی",
            "شماره بایگانی پرونده",
            "نام متقاضی فعلی",
            "کد ملی همسر (متقاضی جدید)",
            "نام همسر (متقاضی جدید)",
            "نام خانوادگی همسر",
            "نام پدر همسر",
            "علت و توضیحات جایگزینی"
        ]
        ws.append(headers)

        swap_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = swap_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 24

        sample_row = [
            "0371112233", 100001, "علی رضایی",
            "0389998877", "فاطمه", "کریمی", "محمد",
            "درخواست کتبی متقاضی جهت انتقال پرونده به نام همسر"
        ]
        ws.append(sample_row)

    elif template_type == "dashboard_sign":
        ws.title = "امضای کارتابل من"
        filename_prefix = "Template_Dashboard_Batch_Sign"

        headers = [
            "کد ملی متقاضی",
            "شماره بایگانی پرونده",
            "نام متقاضی",
            "مرحله جهت تایید",
            "تایید امضا (عدد ۱)",
            "توضیحات و یادداشت امضا"
        ]
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 24

    else:
        # Fallback: Redirect to existing update template generator
        from .views import excel_template_update_view
        return excel_template_update_view(request)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    now_j = _format_tehran_jalali(fmt="%Y%m%d_%H%M")
    filename = f"{filename_prefix}_{now_j}.xlsx"

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# =========================================================================
# 3. Process Mass Stage Signatures Excel Upload
# =========================================================================

@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def process_stage_signatures_excel_view(request):
    """
    Parses uploaded Excel file containing National IDs and Stage columns (1 to 22/24).
    If a column has '1' or 'تایید', signs that stage for the matching dossier,
    validates user stage permissions, creates SHA-256 signature log, and advances the workflow.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return JsonResponse({"status": "error", "message": "هیچ فایل اکسلی ارسال نشده است."}, status=400)

    try:
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            return JsonResponse({"status": "error", "message": "کاربرگ اکسل یافت نشد."}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"فرمت اکسل نامعتبر است: {str(e)}"}, status=400)

    row_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(row_iter)
    except StopIteration:
        return JsonResponse({"status": "error", "message": "فایل اکسل خالی است."}, status=400)

    # Map headers: National ID column and Stage columns
    nid_col_idx = None
    stage_cols: Dict[int, int] = {}  # stage_number -> col_idx

    for idx, cell in enumerate(header_row):
        if not cell:
            continue
        val = str(cell).strip()
        if "کد ملی" in val or "کدملی" in val:
            nid_col_idx = idx
        elif "مرحله" in val:
            # Extract number
            digits = "".join([c for c in val if c.isdigit()])
            if digits:
                stg_num = int(digits)
                if 1 <= stg_num <= MAX_STAGE:
                    stage_cols[stg_num] = idx

    if nid_col_idx is None:
        return JsonResponse({"status": "error", "message": "ستونی با عنوان «کد ملی متقاضی» در فایل اکسل یافت نشد."}, status=400)

    if not stage_cols:
        return JsonResponse({"status": "error", "message": "هیچ ستونی مربوط به مراحل فرآیند (مثال: «مرحله ۳») در فایل یافت نشد."}, status=400)

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
    actor_role = profile.role_title if profile and profile.role_title else "کارشناس اقدام"

    signed_count = 0
    skipped_count = 0
    error_logs = []
    processed_nids = set()

    for row_idx, row in enumerate(row_iter, start=2):
        if not row or len(row) <= nid_col_idx:
            continue
        raw_nid = row[nid_col_idx]
        if not raw_nid:
            continue
        nid = str(raw_nid).strip()
        if len(nid) < 10 and nid.isdigit():
            nid = nid.zfill(10)

        if nid in processed_nids:
            continue
        processed_nids.add(nid)

        try:
            dossier = HousingDossier.objects.select_for_update().filter(national_id=nid).first()
            if not dossier:
                error_logs.append(f"ردیف {row_idx}: کدملی {nid} در سامانه یافت نشد.")
                skipped_count += 1
                continue

            if dossier.is_locked:
                error_logs.append(f"ردیف {row_idx}: پرونده #{dossier.archive_number} قفل/بایگانی شده است.")
                skipped_count += 1
                continue

            # Check each stage (supporting decoupled / disconnected workflow)
            row_signed = False
            stage_to_slots_map = {
                1: ["brokerage"],
                2: ["brokerage"],
                3: ["form_j"],
                4: ["decile_facility", "contractor_settlement", "other_facilities"],
                5: ["applicant_settlement"],
                6: ["bank_facility"],
                7: ["brokerage"],
                8: ["brokerage"],
                9: ["brokerage"],
                10: ["national_housing", "bank_facility"],
                11: ["form_j"],
                12: ["technical"],
                13: ["real_estate"],
                14: ["land_bank"],
                15: ["legal"],
                16: ["evaluation"],
                17: ["decile_facility"],
                18: ["revenue"],
                19: ["contractor_settlement"],
            }

            for stg_num in sorted(stage_cols.keys()):
                col_idx = stage_cols[stg_num]
                if col_idx >= len(row):
                    continue
                cell_val = row[col_idx]
                if cell_val is None:
                    continue

                cell_str = str(cell_val).strip().lower()
                should_sign = cell_str in ["1", "1.0", "تایید", "امضا", "yes", "true", "بله"]

                if should_sign:
                    # Permission check for this specific stage
                    can_sign = is_admin or bool(profile and profile.can_action_stage(stg_num))
                    if not can_sign:
                        error_logs.append(f"ردیف {row_idx}: شما دسترسی مجاز برای امضای مرحله {stg_num} را ندارید.")
                        continue

                    # Record official signature log for stage stg_num
                    stg_title = STAGE_ROLES.get(stg_num, ('', '', f'مرحله {stg_num}'))[2]
                    stg_role = STAGE_ROLES.get(stg_num, ('', 'کارشناس اقدام', ''))[1]

                    raw_stamp = f"EXCEL-{dossier.archive_number}-{stg_num}-{timezone.now().isoformat()}"
                    sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

                    WorkflowSignatureLog.objects.create(
                        dossier=dossier,
                        from_stage=f"مرحله {stg_num}: {stg_title}",
                        to_stage=f"مرحله {stg_num}: {stg_title}",
                        actor=actor_name,
                        role=actor_role,
                        action="SIGN_EXCEL",
                        action_label=f"تایید و امضای الکترونیک مرحله {stg_num} (اکسل)",
                        signature_hash=sig_hash,
                        notes=f"تایید و امضای الکترونیکی گروهی از طریق فایل اکسل توسط کاربر «{actor_name}»"
                    )

                    # Stamp official archival DossierSignature slot with signature scan image
                    target_slots = stage_to_slots_map.get(stg_num, [])
                    now_jalali = _format_tehran_jalali(fmt="%Y/%m/%d %H:%M")
                    for slot_key in target_slots:
                        sig_obj, _ = DossierSignature.objects.get_or_create(dossier=dossier, slot_key=slot_key)
                        sig_obj.signer_name = actor_name
                        sig_obj.signer_title = actor_role
                        sig_obj.signed_date = now_jalali
                        sig_obj.uploaded_by = request.user.username
                        if profile and profile.signature_image:
                            sig_obj.signature_image = profile.signature_image
                        sig_obj.save()

                    row_signed = True

            if row_signed:
                # Recalculate next actionable stage with disconnected jumps
                next_stage = dossier.find_next_actionable_stage()
                if next_stage >= 22:
                    dossier.current_stage = 22
                    dossier.is_locked = True
                    dossier.status = "COMPLETED"
                else:
                    dossier.current_stage = next_stage
                    dossier.status = "IN_PROGRESS"
                    dossier.return_reason = ""
                    dossier.return_by = ""
                    dossier.return_from_stage = None
                dossier.save()
                signed_count += 1
            else:
                skipped_count += 1

        except Exception as e:
            error_logs.append(f"ردیف {row_idx} (کدملی {nid}): خطای پردازش - {str(e)}")

    return JsonResponse({
        "status": "success",
        "message": f"پردازش فایل اکسل با موفقیت انجام شد: {signed_count} مورد امضا گردید، {skipped_count} مورد رد/بدون تغییر ماند.",
        "signed_count": signed_count,
        "skipped_count": skipped_count,
        "errors": error_logs[:20]
    })


# =========================================================================
# 4. Commission Re-evaluation Upload (کمیسیون تعدیل و لغو امضای ۲، ۴، ۵، ۸، ۱۸)
# =========================================================================

@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def process_commission_excel_view(request):
    """
    Processes the Commission Adjustment Excel file.
    Updates modified data (e.g. base_cost_without_loan, plaque, area, renovation_code).
    On any modified record, cancels/resets signatures for stages 2, 4, 5, 8, 18,
    re-routes the dossier back to Stage 2, and creates a full immutable audit log.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    if not is_admin:
        return JsonResponse({"status": "error", "message": "عملیات کمیسیون صرفاً مختص مدیر ارشد سامانه و رئیس مسکن می‌باشد."}, status=403)

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return JsonResponse({"status": "error", "message": "هیچ فایل اکسلی ارسال نشده است."}, status=400)

    try:
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active
        row_iter = ws.iter_rows(values_only=True)
        header_row = next(row_iter)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"خطا در خواندن فایل اکسل: {str(e)}"}, status=400)

    # Column mapping
    col_map = {}
    nid_col_idx = None
    for idx, cell in enumerate(header_row):
        if not cell:
            continue
        norm = str(cell).strip()
        if "کد ملی" in norm or "کدملی" in norm:
            nid_col_idx = idx
        elif "قیمت تمام شده" in norm or "مبلغ تمام شده" in norm:
            col_map["base_cost_without_loan"] = idx
        elif "پلاک اصلی" in norm:
            col_map["main_plaque"] = idx
        elif "فرعی" in norm:
            col_map["sub_plaque"] = idx
        elif "مفروز" in norm:
            col_map["separated_plaque"] = idx
        elif "قطعه" in norm:
            col_map["plot_number"] = idx
        elif "کد نوسازی" in norm:
            col_map["renovation_code"] = idx
        elif "متراژ مفید" in norm:
            col_map["net_unit_area"] = idx

    if nid_col_idx is None:
        return JsonResponse({"status": "error", "message": "ستون «کد ملی متقاضی» در فایل اکسل یافت نشد."}, status=400)

    actor_name = profile.full_name if profile and profile.full_name else request.user.username
    actor_role = profile.role_title if profile and profile.role_title else "دبیرخانه کمیسیون مسکن"

    adjusted_count = 0
    unchanged_count = 0
    errors = []

    for row_idx, row in enumerate(row_iter, start=2):
        if not row or len(row) <= nid_col_idx or not row[nid_col_idx]:
            continue
        nid = str(row[nid_col_idx]).strip()
        if len(nid) < 10 and nid.isdigit():
            nid = nid.zfill(10)

        dossier = HousingDossier.objects.select_for_update().filter(national_id=nid).first()
        if not dossier:
            errors.append(f"ردیف {row_idx}: کدملی {nid} در سیستم یافت نشد.")
            continue

        if dossier.is_locked:
            errors.append(f"ردیف {row_idx}: پرونده #{dossier.archive_number} قفل دائم/بایگانی قطعی شده است و قابل تغییر نمی‌باشد.")
            continue

        changes = []

        # Check base_cost_without_loan
        if "base_cost_without_loan" in col_map and col_map["base_cost_without_loan"] < len(row):
            val = row[col_map["base_cost_without_loan"]]
            if val is not None and str(val).strip():
                try:
                    new_cost = int(float(str(val).replace(",", "").strip()))
                    if new_cost != dossier.base_cost_without_loan:
                        changes.append(("base_cost_without_loan", "قیمت تمام شده بدون وام", str(dossier.base_cost_without_loan), str(new_cost)))
                        dossier.base_cost_without_loan = new_cost
                except ValueError:
                    pass

        # Check plaque fields
        for fld, title in [("main_plaque", "پلاک اصلی"), ("sub_plaque", "فرعی از"), ("separated_plaque", "پلاک مفروز"), ("plot_number", "شماره قطعه")]:
            if fld in col_map and col_map[fld] < len(row):
                val = row[col_map[fld]]
                if val is not None and str(val).strip():
                    try:
                        int_val = int(val)
                        if getattr(dossier, fld) != int_val:
                            changes.append((fld, title, str(getattr(dossier, fld)), str(int_val)))
                            setattr(dossier, fld, int_val)
                    except ValueError:
                        pass

        # Check renovation_code
        if "renovation_code" in col_map and col_map["renovation_code"] < len(row):
            val = str(row[col_map["renovation_code"]] or "").strip()
            if val and val != dossier.renovation_code:
                changes.append(("renovation_code", "کد نوسازی", dossier.renovation_code, val))
                dossier.renovation_code = val

        # Check net_unit_area
        if "net_unit_area" in col_map and col_map["net_unit_area"] < len(row):
            val = row[col_map["net_unit_area"]]
            if val is not None and str(val).strip():
                try:
                    new_area = Decimal(str(val).strip())
                    if new_area != dossier.net_unit_area:
                        changes.append(("net_unit_area", "متراژ مفید واحد", str(dossier.net_unit_area), str(new_area)))
                        dossier.net_unit_area = new_area
                except Exception:
                    pass

        if changes:
            # Data was modified: Reset stages 2, 4, 5, 8, 18
            old_stage = dossier.current_stage

            # Reset official archival signatures tied to these stages
            reset_slots = ["brokerage", "other_facilities", "decile_facility", "applicant_settlement", "revenue"]
            DossierSignature.objects.filter(dossier=dossier, slot_key__in=reset_slots).delete()

            # Remove signature logs for these invalidated stages
            reset_stages = [2, 4, 5, 8, 18]
            for r_stg in reset_stages:
                dossier.audit_logs.filter(
                    action__in=["SIGN", "APPROVE", "SIGN_EXCEL"],
                    from_stage__startswith=f"مرحله {r_stg}:"
                ).delete()

            # Reroute dossier back to earliest unsigned stage
            dossier.current_stage = dossier.find_next_actionable_stage()
            dossier.status = "RETURNED"
            dossier.return_reason = "تعدیل قیمت و مشخصات توسط کمیسیون؛ لغو امضای مراحل ۲، ۴، ۵، ۸، ۱۸"
            dossier.return_by = actor_name
            dossier.return_from_stage = old_stage
            dossier.save()

            # Record Field Change Logs
            now_dt = timezone.now()
            for f_name, f_title, old_v, new_v in changes:
                DossierFieldChangeLog.objects.create(
                    dossier=dossier,
                    field_name=f_name,
                    field_label=f_title,
                    old_value=old_v or "خالی",
                    new_value=new_v,
                    changed_by=actor_name,
                    role=actor_role,
                    stage=dossier.current_stage,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    timestamp=now_dt
                )

            # Record Commission Workflow Signature Log
            change_summary = "، ".join([f"{c[1]}: {c[3]}" for c in changes])
            raw_stamp = f"COMMISSION-{dossier.archive_number}-{old_stage}-2-{now_dt.isoformat()}"
            sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

            WorkflowSignatureLog.objects.create(
                dossier=dossier,
                from_stage=f"مرحله {old_stage}",
                to_stage="مرحله ۲ (بازگشت جهت بررسی مجدد)",
                actor=actor_name,
                role=actor_role,
                action="COMMISSION_RESET",
                action_label="لغو امضاها توسط کمیسیون تعدیل",
                signature_hash=sig_hash,
                notes=f"تعدیل قیمت و مشخصات در کمیسیون ({change_summary}). امضای مراحل ۲، ۴، ۵، ۸، ۱۸ لغو گردید و پرونده جهت ممیزی مجدد ارجاع شد."
            )
            adjusted_count += 1
        else:
            unchanged_count += 1

    return JsonResponse({
        "status": "success",
        "message": f"عملیات کمیسیون با موفقیت اجرا شد: {adjusted_count} پرونده تعدیل و امضاهای مربوطه لغو گردید، {unchanged_count} پرونده بدون مغایرت بود.",
        "adjusted_count": adjusted_count,
        "unchanged_count": unchanged_count,
        "errors": errors[:20]
    })


# =========================================================================
# 5. Swap Applicant with Spouse (تعویض متقاضی با همسر)
# =========================================================================

def _perform_applicant_spouse_swap(dossier: HousingDossier, actor_name: str, actor_role: str, reason: str = "") -> None:
    """
    Atomically swaps applicant and spouse details, reroutes to Stage 3 for Form J re-inquiry,
    and creates full audit and workflow logs.
    """
    old_applicant_full = dossier.full_name
    old_applicant_nid = dossier.national_id
    old_spouse_full = dossier.spouse_full_name
    old_spouse_nid = dossier.spouse_national_id

    # Temporary storage
    t_first = dossier.first_name
    t_last = dossier.last_name
    t_full = dossier.full_name
    t_father = dossier.father_name
    t_nid = dossier.national_id
    t_birth = dossier.birth_date
    t_id_num = dossier.applicant_id_number
    t_birth_place = dossier.applicant_birth_place
    t_j_status = dossier.applicant_form_j_status
    t_j_dir_status = dossier.applicant_form_j_directorate_status
    t_j_red_desc = dossier.applicant_form_j_red_description

    # Swap into Applicant
    dossier.first_name = dossier.spouse_first_name
    dossier.last_name = dossier.spouse_last_name
    dossier.full_name = dossier.spouse_full_name
    dossier.father_name = dossier.spouse_father_name
    dossier.national_id = dossier.spouse_national_id
    dossier.birth_date = dossier.spouse_birth_date
    dossier.applicant_id_number = dossier.spouse_id_number
    dossier.applicant_birth_place = dossier.spouse_birth_place
    dossier.applicant_form_j_status = dossier.spouse_form_j_status
    dossier.applicant_form_j_directorate_status = dossier.spouse_form_j_directorate_status
    dossier.applicant_form_j_red_description = dossier.spouse_form_j_red_description

    # Swap into Spouse
    dossier.spouse_first_name = t_first
    dossier.spouse_last_name = t_last
    dossier.spouse_full_name = t_full
    dossier.spouse_father_name = t_father
    dossier.spouse_national_id = t_nid
    dossier.spouse_birth_date = t_birth
    dossier.spouse_id_number = t_id_num
    dossier.spouse_birth_place = t_birth_place
    dossier.spouse_form_j_status = t_j_status
    dossier.spouse_form_j_directorate_status = t_j_dir_status
    dossier.spouse_form_j_red_description = t_j_red_desc

    old_stage = dossier.current_stage

    # Reroute to Stage 3 (Form J review) if past stage 3
    if dossier.current_stage > 3:
        dossier.current_stage = 3
        dossier.status = "RETURNED"
        dossier.return_reason = "جایگزینی متقاضی اصلی با همسر و ارجاع پرونده جهت استعلام مجدد فرم ج"
        dossier.return_by = actor_name
        dossier.return_from_stage = old_stage

    dossier.save()

    now_dt = timezone.now()
    DossierFieldChangeLog.objects.create(
        dossier=dossier,
        field_name="applicant_spouse_swap",
        field_label="تعویض متقاضی اصلی با همسر",
        old_value=f"متقاضی: {old_applicant_full} ({old_applicant_nid})",
        new_value=f"متقاضی جدید: {old_spouse_full} ({old_spouse_nid})",
        changed_by=actor_name,
        role=actor_role,
        stage=dossier.current_stage,
        timestamp=now_dt
    )

    raw_stamp = f"SWAP-{dossier.archive_number}-{old_stage}-3-{now_dt.isoformat()}"
    sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {old_stage}",
        to_stage="مرحله ۳ (بررسی فرم جیم متقاضی جدید)",
        actor=actor_name,
        role=actor_role,
        action="SWAP_SPOUSE",
        action_label="تعویض متقاضی اصلی با همسر",
        signature_hash=sig_hash,
        notes=f"متقاضی اصلی با همسر جایگزین گردید. دلیل: {reason or 'درخواست رسمی متقاضی'}. پرونده به مرحله ۳ ارجاع شد."
    )


@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def swap_applicant_spouse_view(request, pk):
    """Single dossier swap action triggered from Dossier Detail UI."""
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    if not is_admin:
        return JsonResponse({"status": "error", "message": "عملیات تعویض متقاضی با همسر صرفاً مختص مدیر ارشد سامانه و رئیس مسکن می‌باشد."}, status=403)

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "پرونده قفل دائم/بایگانی شده است و امکان تغییر متقاضی وجود ندارد."}, status=400)

    if not dossier.spouse_national_id:
        return JsonResponse({"status": "error", "message": "اطلاعات همسر در این پرونده ثبت نشده است."}, status=400)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
        reason = body.get("reason", "").strip()
    except Exception:
        reason = request.POST.get("reason", "").strip()

    actor_name = profile.full_name if profile and profile.full_name else request.user.username
    actor_role = profile.role_title if profile and profile.role_title else "مدیر سامانه"

    _perform_applicant_spouse_swap(dossier, actor_name, actor_role, reason)

    return JsonResponse({
        "status": "success",
        "message": f"متقاضی با موفقیت با همسر جایگزین شد و پرونده جهت استعلام مجدد فرم ج به مرحله ۳ ارجاع گردید.",
        "new_applicant": dossier.full_name,
        "new_national_id": dossier.national_id,
        "new_stage": dossier.current_stage
    })


@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def process_swap_spouse_excel_view(request):
    """Bulk swap applicant with spouse from uploaded Excel file."""
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    if not is_admin:
        return JsonResponse({"status": "error", "message": "دسترسی غیرمجاز."}, status=403)

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return JsonResponse({"status": "error", "message": "فایل اکسل یافت نشد."}, status=400)

    try:
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active
        row_iter = ws.iter_rows(values_only=True)
        header_row = next(row_iter)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"خطا در خواندن فایل اکسل: {str(e)}"}, status=400)

    nid_col_idx = 0
    reason_col_idx = None
    for idx, cell in enumerate(header_row):
        val = str(cell or "").strip()
        if "کد ملی" in val or "کدملی" in val:
            nid_col_idx = idx
        elif "توضیحات" in val or "علت" in val:
            reason_col_idx = idx

    actor_name = profile.full_name if profile and profile.full_name else request.user.username
    actor_role = profile.role_title if profile and profile.role_title else "مدیر سامانه"

    swapped_count = 0
    errors = []

    for row_idx, row in enumerate(row_iter, start=2):
        if not row or len(row) <= nid_col_idx or not row[nid_col_idx]:
            continue
        nid = str(row[nid_col_idx]).strip()
        if len(nid) < 10 and nid.isdigit():
            nid = nid.zfill(10)

        reason = str(row[reason_col_idx] or "").strip() if reason_col_idx and reason_col_idx < len(row) else "درخواست کتبی تعویض متقاضی با همسر"

        dossier = HousingDossier.objects.select_for_update().filter(national_id=nid).first()
        if not dossier:
            errors.append(f"ردیف {row_idx}: پرونده با کدملی {nid} یافت نشد.")
            continue
        if dossier.is_locked:
            errors.append(f"ردیف {row_idx}: پرونده #{dossier.archive_number} قفل/بایگانی شده است.")
            continue
        if not dossier.spouse_national_id:
            errors.append(f"ردیف {row_idx}: پرونده #{dossier.archive_number} اطلاعات همسر ندارد.")
            continue

        _perform_applicant_spouse_swap(dossier, actor_name, actor_role, reason)
        swapped_count += 1

    return JsonResponse({
        "status": "success",
        "message": f"عملیات تعویض با موفقیت انجام شد: {swapped_count} متقاضی با همسر جایگزین شدند.",
        "swapped_count": swapped_count,
        "errors": errors[:20]
    })


# =========================================================================
# 6. Dashboard Batch Electronic Sign (امضای دسته‌جمعی کارتابل)
# =========================================================================

@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def batch_sign_dossiers_view(request):
    """
    Handles batch electronic signing of multiple dossiers selected via checkboxes
    on the user dashboard / inbox table.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
        archive_numbers = body.get("archive_numbers", [])
        notes = body.get("notes", "تایید و امضای الکترونیکی گروهی از کارتابل").strip()
    except Exception:
        archive_numbers = request.POST.getlist("archive_numbers")
        notes = request.POST.get("notes", "تایید و امضای الکترونیکی گروهی از کارتابل").strip()

    if not archive_numbers:
        return JsonResponse({"status": "error", "message": "هیچ پرونده‌ای جهت امضا انتخاب نشده است."}, status=400)

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
    actor_role = profile.role_title if profile and profile.role_title else "کارشناس اقدام"

    signed_count = 0
    skipped_count = 0
    errors = []

    now_jalali = _format_tehran_jalali()

    for arch_num in archive_numbers:
        try:
            num = int(arch_num)
            dossier = HousingDossier.objects.select_for_update().filter(archive_number=num).first()
            if not dossier:
                skipped_count += 1
                continue

            if dossier.is_locked:
                errors.append(f"پرونده #{num} قبلاً نهایی و بایگانی قطعی شده است.")
                skipped_count += 1
                continue

            # Permission check for dossier's active stage
            can_sign = is_admin or bool(profile and profile.can_action_stage(dossier.current_stage))
            if not can_sign:
                errors.append(f"پرونده #{num}: عدم دسترسی برای مرحله {dossier.current_stage} ({dossier.current_role})")
                skipped_count += 1
                continue

            current_idx = dossier.current_stage
            current_title = dossier.current_stage_title

            raw_stamp = f"BATCH-{dossier.archive_number}-{current_idx}-{timezone.now().isoformat()}"
            sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

            # Dynamic jump to next unsigned stage
            next_stage = dossier.find_next_actionable_stage(current_signed_stage=current_idx)

            if next_stage >= 22 or current_idx >= MAX_STAGE:
                dossier.current_stage = 22
                dossier.is_locked = True
                dossier.status = "COMPLETED"
                action = "ARCHIVE"
                action_label = "بایگانی قطعی پرونده"
                to_stage_str = f"بایگانی نهایی (مرحله {MAX_STAGE})"
            else:
                dossier.current_stage = next_stage
                dossier.status = "IN_PROGRESS"
                dossier.return_reason = ""
                dossier.return_by = ""
                dossier.return_from_stage = None
                action = "SIGN"
                action_label = "تایید و امضای الکترونیکی گروهی"
                to_stage_str = f"مرحله {next_stage}: {STAGE_ROLES.get(next_stage, ('','',f'مرحله {next_stage}'))[2]}"

            dossier.save()

            WorkflowSignatureLog.objects.create(
                dossier=dossier,
                from_stage=f"مرحله {current_idx}: {current_title}",
                to_stage=to_stage_str,
                actor=actor_name,
                role=actor_role,
                action=action,
                action_label=action_label,
                signature_hash=sig_hash,
                notes=notes
            )

            # Link signature image to slots if configured
            # stage_to_slots mapped below
            stage_to_slots_map = {
                1: ["brokerage"],
                3: ["form_j"],
                4: ["other_facilities", "decile_facility"],
                5: ["applicant_settlement"],
                6: ["bank_facility"],
                8: ["brokerage"],
                9: ["brokerage"],
                10: ["national_housing", "bank_facility"],
                11: ["form_j"],
                12: ["technical"],
                13: ["real_estate"],
                14: ["land_bank"],
                15: ["legal"],
                16: ["evaluation"],
                17: ["decile_facility"],
                18: ["revenue"],
                19: ["contractor_settlement"],
            }
            target_slots = stage_to_slots_map.get(current_idx, [])
            for slot_key in target_slots:
                sig_obj, _ = DossierSignature.objects.get_or_create(dossier=dossier, slot_key=slot_key)
                sig_obj.signer_name = actor_name
                sig_obj.signer_title = actor_role
                sig_obj.signed_date = now_jalali
                sig_obj.uploaded_by = request.user.username
                if profile and profile.signature_image:
                    sig_obj.signature_image = profile.signature_image
                sig_obj.save()

            signed_count += 1

        except Exception as e:
            errors.append(f"پرونده #{arch_num}: {str(e)}")
            skipped_count += 1

    return JsonResponse({
        "status": "success",
        "message": f"امضای گروهی انجام شد: {signed_count} پرونده با موفقیت تایید و امضا شد.",
        "signed_count": signed_count,
        "skipped_count": skipped_count,
        "errors": errors[:15]
    })


# =========================================================================
# 7. Dashboard Excel Export (دانلود پرونده‌های کارتابل جاری)
# =========================================================================

@login_required(login_url='login')
def excel_export_dashboard_view(request):
    """
    Exports all dossiers currently in the logged-in user's active/actionable stages.
    Available to ALL authenticated users without admin restrictions.
    """
    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))

    qs = HousingDossier.objects.all().order_by("-archive_number")

    allowed = []
    if not is_admin:
        if profile and hasattr(profile, 'get_allowed_stages_list'):
            allowed = profile.get_allowed_stages_list()
        elif profile and profile.allowed_stages:
            allowed = [int(s.strip()) for s in profile.allowed_stages.split(',') if s.strip().isdigit()]

        if allowed:
            qs = qs.filter(current_stage__in=allowed, is_locked=False)
        else:
            qs = qs.none()

    stage_param = request.GET.get('stage')
    if stage_param and stage_param.isdigit():
        stg = int(stage_param)
        if is_admin or (profile and profile.can_action_stage(stg)):
            qs = qs.filter(current_stage=stg)

    from .excel_service import generate_dossiers_export
    cache_key = f"dash_u{request.user.id}_stg{profile.allowed_stages if profile else 'none'}_s{stage_param or 'all'}"
    return generate_dossiers_export(qs, cache_key=cache_key)


# =========================================================================
# 8. Attachment Reordering & Interactive Image Editor
# =========================================================================

@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def reorder_attachments_view(request, pk):
    """
    Saves the user-chosen display order of attachments in the scan album.
    Logs the reordering action in DossierFieldChangeLog.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده قفل و بایگانی شده است."}, status=400)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
        ordered_ids = body.get("ordered_ids", [])
    except Exception:
        return JsonResponse({"status": "error", "message": "داده‌های ارسالی نامعتبر است."}, status=400)

    if not ordered_ids:
        return JsonResponse({"status": "error", "message": "لیست چیدمان خالی است."}, status=400)

    for idx, att_id in enumerate(ordered_ids):
        dossier.attachments.filter(id=att_id).update(order=idx)

    profile = getattr(request.user, 'profile', None)
    actor_name = profile.full_name if profile and profile.full_name else request.user.username

    DossierFieldChangeLog.objects.create(
        dossier=dossier,
        field_name="attachment_order",
        field_label="چیدمان و ترتیب آلبوم اسناد",
        old_value="ترتیب قبلی",
        new_value=f"تغییر چیدمان {len(ordered_ids)} سند در آلبوم",
        changed_by=actor_name,
        role=profile.role_title if profile and profile.role_title else "کارشناس",
        stage=dossier.current_stage,
        ip_address=request.META.get('REMOTE_ADDR'),
        timestamp=timezone.now()
    )

    return JsonResponse({"status": "success", "message": "ترتیب جدید اسناد با موفقیت ذخیره شد."})


@csrf_exempt
@login_required(login_url='login')
@transaction.atomic
def edit_attachment_image_view(request, pk, attachment_id):
    """
    Interactive image editor for attachments:
    - rotate: 90 deg clockwise / counter-clockwise
    - crop: box coordinates (x, y, width, height)
    - save_edited: direct base64 image data from client canvas editor
    Overwrites file safely, recalculates SHA-256 hash, and logs the edit action.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده قفل و بایگانی شده است."}, status=400)

    attachment = get_object_or_404(DossierAttachment, id=attachment_id, dossier=dossier)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body = {}

    action = body.get("action") or request.POST.get("action")
    if not action:
        return JsonResponse({"status": "error", "message": "نوع عملیات ویرایش مشخص نشده است."}, status=400)

    nat_id = str(dossier.national_id).strip() or "general"
    nat_id_dir = os.path.join(settings.MEDIA_ROOT, nat_id)
    os.makedirs(nat_id_dir, exist_ok=True)
    file_path = os.path.join(nat_id_dir, attachment.file_name)

    profile = getattr(request.user, 'profile', None)
    actor_name = profile.full_name if profile and profile.full_name else request.user.username

    try:
        if action == "save_edited":
            # Direct base64 payload from client-side canvas
            image_data = body.get("image_data", "")
            if not image_data or not image_data.startswith("data:image"):
                return JsonResponse({"status": "error", "message": "داده تصویر نامعتبر است."}, status=400)

            _, b64_str = image_data.split(",", 1)
            file_bytes = base64.b64decode(b64_str)

            with open(file_path, "wb") as f:
                f.write(file_bytes)

            new_sha = "SHA256: " + hashlib.sha256(file_bytes).hexdigest()[:24]
            attachment.file_sha256 = new_sha
            attachment.preview_url = f"/uploads/{nat_id}/{attachment.file_name}?v={int(time.time())}"
            attachment.save()

            edit_desc = body.get("description", "ویرایش تصویر در بوم دیجیتال")

        elif action == "rotate":
            degrees = int(body.get("degrees", 90))
            if not os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": "فایل تصویر روی سرور یافت نشد."}, status=404)

            with Image.open(file_path) as img:
                # PIL rotates counter-clockwise by default, so -degrees rotates clockwise
                rotated = img.rotate(-degrees, expand=True)
                rotated.save(file_path, quality=95)

            file_bytes = open(file_path, "rb").read()
            new_sha = "SHA256: " + hashlib.sha256(file_bytes).hexdigest()[:24]
            attachment.file_sha256 = new_sha
            attachment.preview_url = f"/uploads/{nat_id}/{attachment.file_name}?v={int(time.time())}"
            attachment.save()

            edit_desc = f"چرخش تصویر ({degrees} درجه)"

        elif action == "crop":
            crop_box = body.get("crop")  # dict: {x, y, width, height}
            if not crop_box or not os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": "مختصات برش نامعتبر است."}, status=400)

            x = int(crop_box.get("x", 0))
            y = int(crop_box.get("y", 0))
            w = int(crop_box.get("width", 0))
            h = int(crop_box.get("height", 0))

            if w <= 0 or h <= 0:
                return JsonResponse({"status": "error", "message": "ابعاد برش نامعتبر است."}, status=400)

            with Image.open(file_path) as img:
                cropped = img.crop((x, y, x + w, y + h))
                cropped.save(file_path, quality=95)

            file_bytes = open(file_path, "rb").read()
            new_sha = "SHA256: " + hashlib.sha256(file_bytes).hexdigest()[:24]
            attachment.file_sha256 = new_sha
            attachment.preview_url = f"/uploads/{nat_id}/{attachment.file_name}?v={int(time.time())}"
            attachment.save()

            edit_desc = f"برش و کادربندی تصویر ({w}x{h})"

        else:
            return JsonResponse({"status": "error", "message": "عملیات ناشناخته است."}, status=400)

        # Audit logging
        DossierFieldChangeLog.objects.create(
            dossier=dossier,
            field_name="attachment_image_edit",
            field_label=f"ویرایش سند: {attachment.title}",
            old_value="تصویر قبلی",
            new_value=f"{edit_desc} (هش جدید: {attachment.file_sha256})",
            changed_by=actor_name,
            role=profile.role_title if profile and profile.role_title else "کارشناس",
            stage=dossier.current_stage,
            ip_address=request.META.get('REMOTE_ADDR'),
            timestamp=timezone.now()
        )

        return JsonResponse({
            "status": "success",
            "message": "تصویر با موفقیت ویرایش و در آرشیو ثبت گردید.",
            "preview_url": attachment.preview_url,
            "sha256": attachment.file_sha256
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": f"خطا در پردازش تصویر: {str(e)}"}, status=500)
