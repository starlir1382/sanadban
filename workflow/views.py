import hashlib
import json
import os
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction, models
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .field_permissions import (
    FIELD_STAGE_MAP,
    SLOT_TO_STAGES,
    SLOT_TITLES,
    STAGE_TO_DEFAULT_SLOT,
    get_user_allowed_stages_set,
    can_user_edit_field,
    can_user_upload_signature,
    filter_allowed_updates,
)
from .models import DossierSignature
from .models import HousingDossier, PreSelectedUnit, DossierAttachment, WorkflowSignatureLog, DossierFieldChangeLog, Site, Project, UserProfile, DossierCheck, BankLetter

DOSSIER_FIELD_LABELS = {
    "full_name": "نام و نام خانوادگی متقاضی",
    "father_name": "نام پدر متقاضی",
    "national_id": "کد ملی متقاضی",
    "birth_date": "تاریخ تولد متقاضی",
    "applicant_phone": "شماره تماس متقاضی",
    "selection_rank": "رتبه انتخاب واحد",
    "applicant_form_j_status": "وضعیت استعلام فرم ج متقاضی",
    "applicant_form_j_directorate_status": "استعلام اداره کل متقاضی",
    "applicant_form_j_red_description": "علت و توضیحات کد قرمز متقاضی",
    "spouse_full_name": "نام و نام خانوادگی همسر",
    "spouse_father_name": "نام پدر همسر",
    "spouse_national_id": "کد ملی همسر",
    "spouse_birth_date": "تاریخ تولد همسر",
    "spouse_id_number": "شماره شناسنامه همسر",
    "spouse_birth_place": "محل صدور / تولد همسر",
    "spouse_form_j_status": "وضعیت فرم ج همسر",
    "spouse_form_j_directorate_status": "استعلام اداره کل همسر",
    "spouse_form_j_red_description": "علت و توضیحات کد قرمز همسر",
    "marital_status": "وضعیت تاهل",
    "is_married_confirmed": "احراز زوجیت و تایید تاهل",
    "decile": "دهک درآمدی",
    "site": "نام سایت",
    "project": "نام پروژه",
    "construction_type": "نوع ساخت",
    "block_name": "نام بلوک",
    "block_code": "کد بلوک",
    "floor_number": "شماره طبقه",
    "unit_number": "شماره واحد",
    "unit_code": "کد واحد",
    "bedroom_count": "تعداد خواب",
    "unit_direction": "جهت واحد",
    "net_unit_area": "متراژ مفید واحد (م²)",
    "common_area": "متراژ مشاعات (م²)",
    "total_area": "جمع کل متراژ واحد (م²)",
    "unit_area": "مساحت واحد (م²)",
    "storage_number": "شماره انباری",
    "storage_area": "مساحت انباری (م²)",
    "parking_number": "شماره پارکینگ",
    "parking_area": "مساحت پارکینگ (م²)",
    "covered_parking_area": "متراژ پارکینگ مسقف (م²)",
    "registration_section": "بخش ثبتی",
    "main_plaque": "پلاک اصلی",
    "separated_plaque": "پلاک مفروز",
    "sub_plaque": "فرعی از",
    "plot_number": "شماره قطعه",
    "base_cost_without_loan": "قیمت پایه بدون وام بانکی (ریال)",
    "bank_loan_amount": "مبلغ تسهیلات وام بانکی (ریال)",
    "fund_loan_amount": "مبلغ وام صندوق (ریال)",
    "contractor_letter_amount": "مبلغ نامه پیمانکار (ریال)",
    "decile_loan_amount": "مبلغ وام دهک (ریال)",
    "applicant_equity": "آورده نقدی متقاضی (ریال)",
    "is_sms_sent": "وضعیت ارسال پیامک",
    "is_equity_funded": "تأیید تأمین آورده نقدی",
    "bank_letter_number": "شماره نامه بانک",
    "bank_letter_date": "تاریخ نامه بانک",
    "is_added_to_bank_shipment_list": "اضافه کردن به لیست ارسالی‌ها به بانک",
    "is_sent_to_bank": "ارسال شده به بانک",
    "bank_sent_date": "تاریخ ارسال به بانک",
    "bank_sent_letter_number": "شماره نامه ارسال به بانک",
    "total_land_share": "جمع کل قدرالسهم (م²)",
    "past_years_rent": "اجاره سنوات تا پایان سال جاری (ریال)",
    "current_year_rent": "اجاره سال جاری (ریال)",
    "land_lease_year": "سال اجاره عرصه",
    "preparation_cost": "مبلغ آماده سازی (ریال)",
    "cash_preparation_amount": "مبلغ نقدی آماده سازی (۲۰٪ نقد - ریال)",
    "non_cash_preparation_amount": "مبلغ غیرنقدی آماده سازی (۸۰٪ اقساط - ریال)",
    "is_cash_rent_confirmed": "تایید مبلغ نقدی اجاره",
    "is_decile_loan_confirmed": "تایید چک‌های وام دهک",
    "decile_loan_bank": "بانک عامل وام دهک",
    "supported_institution": "نهاد تحت حمایت متقاضی",
    "check_count": "تعداد چک‌های تسهیلات دهک",
    "check_amount": "مبلغ هر فقره چک تسهیلات (ریال)",
    "last_check_amount": "مبلغ چک آخر تسهیلات (ریال)",
    "total_check_amount": "مجموع کل مبالغ چک‌های تسهیلات (ریال)",
    "check_service_fee": "کارمزد خدمات چک (ریال)",
    "commitment_number": "شماره تعهدنامه چک",
    "commitment_date": "تاریخ تعهدنامه چک",
    "tenant_price": "مبلغ پرداختی اجاره عرصه (ریال)",
    "tenant_code": "کد رهگیری فیش اجاره عرصه",
    "prepayment_code": "کد رهگیری فیش پیش‌پرداخت آماده‌سازی",
    "preparation_service_fee": "کارمزد خدمات آماده‌سازی (ریال)",
    "preparation_check_count": "تعداد چک‌های اقساط آماده‌سازی",
    "total_preparation_check_amount": "مجموع مبلغ چک‌های آماده‌سازی (ریال)",
    "is_preparation_checks_confirmed": "تایید چک‌های اقساط آماده‌سازی",
    "rah_letter": "شماره نامه راه و شهرسازی",
    "rah_letter_date": "تاریخ نامه راه و شهرسازی",
}

def normalize_digits(text: str, to_type="ascii") -> str:
    """Converts numerals between Persian/Arabic and ASCII digits, and normalizes Arabic Yeh/Kaf."""
    if not text:
        return ""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    ascii_digits = "0123456789"
    if to_type == "ascii":
        trans = str.maketrans(persian_digits + arabic_digits + "ييكك", ascii_digits + ascii_digits + "یییک")
    else:
        trans = str.maketrans(ascii_digits + "ييكك", persian_digits + "یییک")
    return text.translate(trans)

def get_token_search_condition(token: str):
    """Builds a comprehensive Q-filter for a search token matching any dossier field."""
    clean = token.replace("#", "").replace(",", "").replace("،", "").strip()
    if not clean:
        return models.Q()
    
    t_ascii = normalize_digits(clean, "ascii")
    t_fa = normalize_digits(clean, "persian")
    
    # Check if token matches any stage by number, title, or role
    matched_stages = set()
    for stg_num, (unit, role, title) in HousingDossier.STAGE_ROLES.items():
        stg_str = str(stg_num)
        stg_fa = normalize_digits(stg_str, "persian")
        if t_ascii == stg_str or clean == stg_fa or f"مرحله {stg_str}" in t_ascii or f"مرحله {stg_fa}" in clean:
            matched_stages.add(stg_num)
        if any(w in title.lower() or w in role.lower() or w in unit.lower() for w in [clean.lower(), t_ascii.lower()] if len(w) >= 2):
            matched_stages.add(stg_num)
            
    cond = models.Q()
    for term in {clean, t_ascii, t_fa}:
        if not term:
            continue
        cond |= (
            models.Q(national_id__icontains=term) |
            models.Q(archive_number__icontains=term) |
            models.Q(full_name__icontains=term) |
            models.Q(father_name__icontains=term) |
            models.Q(spouse_full_name__icontains=term) |
            models.Q(spouse_national_id__icontains=term) |
            models.Q(project__icontains=term) |
            models.Q(site__icontains=term) |
            models.Q(block_name__icontains=term) |
            models.Q(bank_letter_number__icontains=term) |
            models.Q(registration_section__icontains=term)
        )
    
    digits = re.sub(r"\D", "", t_ascii)
    if digits:
        num = int(digits)
        cond |= models.Q(archive_number=num)
        if 1 <= num <= 21:
            cond |= models.Q(current_stage=num)
        
    if matched_stages:
        cond |= models.Q(current_stage__in=matched_stages)
        
    return cond

@login_required(login_url='login')
def dossier_list_view(request):
    """
    Dashboard list view showing housing dossiers with strict role-based stage visibility.
    - Regular experts ONLY see dossiers stuck at their assigned stage(s).
    - Admins, superusers, and Housing Chief see ALL dossiers across the 21-stage pipeline and where each dossier is stuck.
    """
    query = request.GET.get('q', '').strip()
    stage_filter = request.GET.get('stage', '')

    profile = getattr(request.user, 'profile', None)
    is_super = request.user.is_superuser
    is_staff = request.user.is_staff
    is_chief = bool(profile and profile.is_housing_chief)
    is_system = bool(profile and profile.organization == 'system')
    is_all_stages = bool(profile and profile.allowed_stages == 'all')
    
    is_full_admin = is_super or is_staff or is_chief or is_system or is_all_stages

    sort = request.GET.get('sort', 'stage_asc').strip()

    dossiers = HousingDossier.objects.all()

    # Stage restriction for regular experts
    user_allowed_stages = []
    if not is_full_admin:
        if profile and profile.allowed_stages:
            user_allowed_stages = [int(s.strip()) for s in profile.allowed_stages.split(',') if s.strip().isdigit()]
        dossiers = dossiers.filter(models.Q(current_stage__in=user_allowed_stages) | models.Q(is_locked=True))

    if query:
        whole_cond = get_token_search_condition(query)
        tokens = [t for t in query.split() if t.strip()]
        meaningful_tokens = [t for t in tokens if t != "مرحله"]
        
        if len(meaningful_tokens) > 1:
            token_cond = models.Q()
            for t in meaningful_tokens:
                token_cond &= get_token_search_condition(t)
            combined = token_cond
        else:
            combined = whole_cond
            
        dossiers = dossiers.filter(combined).distinct()

    if stage_filter != '':
        try:
            stg_val = int(stage_filter)
            if is_full_admin or stg_val in user_allowed_stages:
                dossiers = dossiers.filter(current_stage=stg_val)
            else:
                dossiers = dossiers.none()
        except ValueError:
            pass

    # Build stages_meta
    all_stages = [
        {"id": i, "title": role_tuple[2], "role": role_tuple[1], "unit": role_tuple[0]}
        for i, role_tuple in HousingDossier.STAGE_ROLES.items()
    ]
    if is_full_admin:
        stages_meta = all_stages
    else:
        stages_meta = [stg for stg in all_stages if stg["id"] in user_allowed_stages]

    # Compute stuck breakdown and annotate stages_meta with counts
    from django.db.models import Count
    counts_by_stage = dict(HousingDossier.objects.values_list('current_stage').annotate(cnt=Count('id')))
    for stg in stages_meta:
        stg["count"] = counts_by_stage.get(stg["id"], 0)

    stage_breakdown = []
    for stg in all_stages:
        cnt = counts_by_stage.get(stg["id"], 0)
        if cnt > 0:
            stage_breakdown.append({
                "stage_id": stg["id"],
                "title": stg["title"],
                "role": stg["role"],
                "unit": stg["unit"],
                "count": cnt,
            })

    user_allowed_titles = [f"مرحله {i} ({HousingDossier.STAGE_ROLES[i][2]})" for i in user_allowed_stages if i in HousingDossier.STAGE_ROLES]

    if sort == 'stage_asc':
        dossiers = dossiers.order_by('current_stage', 'archive_number')
    elif sort == 'stage_desc':
        dossiers = dossiers.order_by('-current_stage', 'archive_number')
    elif sort == 'archive_asc':
        dossiers = dossiers.order_by('archive_number')
    elif sort == 'archive_desc':
        dossiers = dossiers.order_by('-archive_number')
    elif sort == 'name_asc':
        dossiers = dossiers.order_by('full_name')
    elif sort == 'date_desc':
        dossiers = dossiers.order_by('-updated_at')
    else:
        dossiers = dossiers.order_by('current_stage', 'archive_number')

    context = {
        "dossiers": dossiers,
        "current_sort": sort,
        "query": query,
        "stage_filter": stage_filter,
        "stages_meta": stages_meta,
        "is_full_admin": is_full_admin,
        "user_profile": profile,
        "user_allowed_stages": user_allowed_stages,
        "user_allowed_titles": user_allowed_titles,
        "stage_breakdown": stage_breakdown,
        "total_all_dossiers": HousingDossier.objects.count() if is_full_admin else dossiers.count(),
    }
    return render(request, "dossiers/list.html", context)


@login_required(login_url='login')
def dossier_detail_view(request, pk):
    """
    Main interactive workspace view for a single housing dossier across its 22-stage workflow.
    Restricts access so experts can ONLY open dossiers currently stuck at their permitted stage.
    Admins, superusers, and Housing Chief have full access to inspect all dossiers.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)

    profile = getattr(request.user, 'profile', None)
    is_super = request.user.is_superuser
    is_staff = request.user.is_staff
    is_chief = bool(profile and profile.is_housing_chief)
    is_system = bool(profile and profile.organization == 'system')
    is_all_stages = bool(profile and profile.allowed_stages == 'all')
    is_full_admin = is_super or is_staff or is_chief or is_system or is_all_stages

    if not is_full_admin and not dossier.is_locked:
        user_allowed = [int(s.strip()) for s in profile.allowed_stages.split(',') if s.strip().isdigit()] if profile and profile.allowed_stages else []
        if dossier.current_stage not in user_allowed:
            messages.warning(
                request,
                f"عدم دسترسی: پرونده شماره #{dossier.archive_number} هم‌اکنون در مرحله {dossier.current_stage} ({dossier.current_stage_title}) متوقف است. شما صرفاً مجاز به کار بر روی پرونده‌های متوقف در مراحل تخصصی خود ({profile.allowed_stages if profile else 'هیچکدام'}) می‌باشید."
            )
            return redirect("dossier_list")
    attachments = dossier.attachments.all().order_by("stage", "-uploaded_at")
    audit_logs = dossier.audit_logs.all().order_by("-timestamp")

    attachments_data = [
        {
            "id": att.id,
            "stage": att.stage,
            "type": att.doc_type,
            "doc_type": att.doc_type,
            "title": att.title,
            "fileName": att.file_name,
            "uploader": att.uploaded_by,
            "uploadDate": att.uploaded_at.strftime("%Y/%m/%d"),
            "sha256": att.file_sha256,
            "preview_url": att.preview_url,
            "immutable": True
        }
        for att in attachments
    ]

    audit_logs_data = [
        {
            "step": int(log.from_stage.split(":")[0].replace("مرحله", "").strip()) if "مرحله" in log.from_stage and log.from_stage.split(":")[0].replace("مرحله", "").strip().isdigit() else dossier.current_stage,
            "fromStage": log.from_stage,
            "toStage": log.to_stage,
            "actor": log.actor,
            "role": log.role,
            "action": log.action,
            "actionLabel": log.action_label,
            "timestamp": log.timestamp.strftime("%Y/%m/%d %H:%M:%S"),
            "hash": log.signature_hash,
            "notes": log.notes
        }
        for log in audit_logs
    ]

    # 1. Check entries for BankCheckTracker (تسهیلات وام دهک)
    check_items_list = []
    for item in dossier.check_items.filter(check_type="LOAN").order_by("row_number", "id"):
        check_items_list.append({
            "id": item.id,
            "row_number": item.row_number,
            "cash_date": item.cash_date,
            "check_amount": item.check_amount,
            "check_sayadi_code": item.check_sayadi_code,
            "bank_name": item.bank_name,
        })
    if not check_items_list and dossier.check_entries_json and dossier.check_entries_json.strip() not in ("[]", ""):
        try:
            check_items_list = json.loads(dossier.check_entries_json)
        except Exception:
            pass
    if not check_items_list:
        check_items_list = [
            {"row_number": 1, "cash_date": "", "check_amount": 0, "check_sayadi_code": "", "bank_name": "بانک مسکن"}
        ]

    # 2. Preparation Check entries for tashilatCheck (اقساط آماده‌سازی)
    prep_check_items_list = []
    for item in dossier.check_items.filter(check_type="PREPARATION").order_by("row_number", "id"):
        prep_check_items_list.append({
            "id": item.id,
            "row_number": item.row_number,
            "cash_date": item.cash_date,
            "check_amount": item.check_amount,
            "check_sayadi_code": item.check_sayadi_code,
            "bank_name": item.bank_name,
        })
    if not prep_check_items_list and dossier.preparation_check_entries_json and dossier.preparation_check_entries_json.strip() not in ("[]", ""):
        try:
            prep_check_items_list = json.loads(dossier.preparation_check_entries_json)
        except Exception:
            pass
    if not prep_check_items_list:
        prep_check_items_list = [
            {"row_number": 1, "cash_date": "", "check_amount": 0, "check_sayadi_code": "", "bank_name": "بانک مسکن"}
        ]

    dossier_data = {
        "archive_number": dossier.archive_number,
        "current_stage": dossier.current_stage,
        "is_locked": dossier.is_locked,
        "status": dossier.status,
        "is_red_form_j": dossier.is_red_form_j,
        "is_rejected": dossier.is_rejected,
        "rejection_letter_number": dossier.rejection_letter_number or "",
        "rejection_letter_date": dossier.rejection_letter_date or "",
        "rejection_reason": dossier.rejection_reason or "",
        "rejected_by": dossier.rejected_by or "",
        "return_reason": dossier.return_reason,
        "return_by": dossier.return_by,
        "return_from_stage": dossier.return_from_stage,
        "form": {
            "full_name": dossier.full_name,
            "father_name": dossier.father_name,
            "national_id": dossier.national_id,
            "birth_date": dossier.birth_date,
            "applicant_phone": dossier.applicant_phone or "",
            "selection_rank": dossier.selection_rank,
            "applicant_form_j_status": dossier.applicant_form_j_status or "سبز (استعلام شده)",
            "applicant_form_j_directorate_status": dossier.applicant_form_j_directorate_status or "تایید نهایی اداره کل",
            "applicant_form_j_red_description": dossier.applicant_form_j_red_description or "",
            "spouse_full_name": dossier.spouse_full_name,
            "spouse_father_name": dossier.spouse_father_name,
            "spouse_national_id": dossier.spouse_national_id,
            "spouse_birth_date": dossier.spouse_birth_date,
            "spouse_id_number": dossier.spouse_id_number,
            "spouse_birth_place": dossier.spouse_birth_place,
            "spouse_form_j_status": dossier.spouse_form_j_status or "سبز (استعلام شده)",
            "spouse_form_j_directorate_status": dossier.spouse_form_j_directorate_status or "تایید نهایی اداره کل",
            "spouse_form_j_red_description": dossier.spouse_form_j_red_description or "",
            "marital_status": dossier.marital_status,
            "is_married_confirmed": dossier.is_married_confirmed,
            "decile": dossier.decile,
            "site": dossier.site,
            "project": dossier.project,
            "construction_type": dossier.construction_type,
            "block_name": dossier.block_name,
            "block_code": dossier.block_code or "",
            "floor_number": dossier.floor_number,
            "unit_number": dossier.unit_number,
            "unit_code": dossier.unit_code or "",
            "bedroom_count": dossier.bedroom_count or 2,
            "unit_direction": dossier.unit_direction or "شمال غربی",
            "net_unit_area": float(dossier.net_unit_area) if dossier.net_unit_area else 0.0,
            "common_area": float(dossier.common_area) if dossier.common_area else 0.0,
            "total_area": float(dossier.total_area) if dossier.total_area else 0.0,
            "unit_area": float(dossier.unit_area) if dossier.unit_area else 0.0,
            "storage_number": dossier.storage_number,
            "storage_area": float(dossier.storage_area) if dossier.storage_area else 0.0,
            "parking_number": dossier.parking_number,
            "parking_area": float(dossier.parking_area) if dossier.parking_area else 0.0,
            "covered_parking_area": float(dossier.covered_parking_area) if dossier.covered_parking_area else 0.0,
            "registration_section": dossier.registration_section,
            "main_plaque": dossier.main_plaque,
            "separated_plaque": dossier.separated_plaque,
            "sub_plaque": dossier.sub_plaque,
            "plot_number": dossier.plot_number,
            "base_cost_without_loan": dossier.base_cost_without_loan,
            "bank_loan_amount": dossier.bank_loan_amount or 6500000000,
            "fund_loan_amount": dossier.fund_loan_amount,
            "contractor_letter_amount": dossier.contractor_letter_amount,
            "decile_loan_amount": dossier.decile_loan_amount,
            "applicant_equity": dossier.applicant_equity,
            "is_sms_sent": dossier.is_sms_sent,
            "is_equity_funded": dossier.is_equity_funded,
            "bank_letter_number": dossier.bank_letter_number,
            "bank_letter_date": dossier.bank_letter_date,
            "is_added_to_bank_shipment_list": dossier.is_added_to_bank_shipment_list,
            "is_sent_to_bank": dossier.is_sent_to_bank,
            "bank_sent_date": dossier.bank_sent_date or "",
            "bank_sent_letter_number": dossier.bank_sent_letter_number or "",
            "total_land_share": float(dossier.total_land_share) if dossier.total_land_share else None,
            "past_years_rent": dossier.past_years_rent,
            "current_year_rent": dossier.current_year_rent,
            "land_lease_year": dossier.land_lease_year,
            "preparation_cost": dossier.preparation_cost,
            "cash_preparation_amount": dossier.cash_preparation_amount,
            "non_cash_preparation_amount": dossier.non_cash_preparation_amount,
            "is_cash_rent_confirmed": dossier.is_cash_rent_confirmed,
            "is_decile_loan_confirmed": dossier.is_decile_loan_confirmed,
            "decile_loan_bank": dossier.decile_loan_bank or "بانک مسکن",
            "supported_institution": dossier.supported_institution or "هیچکدام",
            "check_count": dossier.check_count or len(check_items_list),
            "check_amount": dossier.check_amount,
            "last_check_amount": dossier.last_check_amount,
            "total_check_amount": dossier.total_check_amount or sum(c.get("check_amount", 0) for c in check_items_list),
            "check_service_fee": dossier.check_service_fee or 2000000,
            "commitment_number": dossier.commitment_number or "",
            "commitment_date": dossier.commitment_date or "",
            "check_entries": check_items_list,
            "tenant_price": dossier.tenant_price or 0,
            "tenant_code": dossier.tenant_code or "",
            "prepayment_code": dossier.prepayment_code or "",
            "preparation_service_fee": dossier.preparation_service_fee or 2000000,
            "preparation_check_entries": prep_check_items_list,
            "preparation_check_count": dossier.preparation_check_count or len(prep_check_items_list),
            "total_preparation_check_amount": dossier.total_preparation_check_amount or sum(c.get("check_amount", 0) for c in prep_check_items_list),
            "is_preparation_checks_confirmed": dossier.is_preparation_checks_confirmed,
            "rah_letter": dossier.rah_letter or "",
            "rah_letter_date": dossier.rah_letter_date or "",
        },
        "attachments": attachments_data,
        "audit_logs": audit_logs_data,
        "field_changes": [
            {
                "id": c.id,
                "fieldName": c.field_name,
                "fieldLabel": c.field_label,
                "oldValue": c.old_value if c.old_value is not None else "-",
                "newValue": c.new_value if c.new_value is not None else "-",
                "changedBy": c.changed_by,
                "role": c.role,
                "stage": c.stage,
                "timestamp": c.timestamp.strftime("%Y/%m/%d %H:%M:%S"),
                "ipAddress": c.ip_address or "-"
            }
            for c in dossier.field_changes.all().order_by("-timestamp")[:500]
        ],
    }

    profile = getattr(request.user, 'profile', None)
    is_chief = bool(profile and profile.is_housing_chief)
    is_check_admin = request.user.is_superuser or is_chief or bool(profile and getattr(profile, 'is_check_admin', False))
    user_can_action = request.user.is_superuser or is_chief or (profile and profile.can_action_stage(dossier.current_stage))
    can_view_audit = request.user.is_superuser or is_chief or (profile and profile.can_view_all_audit_logs())

    # Calculate Signatures for every stage: Signer Name + Date & Time
    import re
    import jdatetime
    stage_signatures = {}
    for log in dossier.audit_logs.filter(action__in=["SIGN", "APPROVE", "ARCHIVE"]).order_by("timestamp"):
        m = re.search(r'مرحله\s+(\d+)', log.from_stage)
        if m:
            stg_idx = int(m.group(1))
            try:
                jdt = jdatetime.datetime.fromgregorian(datetime=log.timestamp)
                date_str = jdt.strftime("%Y/%m/%d - %H:%M")
            except Exception:
                date_str = log.timestamp.strftime("%Y/%m/%d %H:%M")

            stage_signatures[stg_idx] = {
                "actor": log.actor,
                "role": log.role or HousingDossier.STAGE_ROLES.get(stg_idx, ("-", "کارشناس اقدام", "-"))[1],
                "date": date_str,
                "action": log.action,
                "action_label": log.action_label,
            }

    # For any stage < current_stage without an explicit signature record:
    for stg_num in range(1, dossier.current_stage):
        if stg_num not in stage_signatures:
            default_role = HousingDossier.STAGE_ROLES.get(stg_num, ("-", "کارشناس اقدام‌کننده", "-"))[1]
            try:
                jdt = jdatetime.datetime.fromgregorian(datetime=dossier.created_at)
                default_date = jdt.strftime("%Y/%m/%d")
            except Exception:
                default_date = dossier.created_at.strftime("%Y/%m/%d")
            actor_name = default_role.split('(')[-1].replace(')', '').strip() if '(' in default_role else "کارشناس اقدام"
            stage_signatures[stg_num] = {
                "actor": actor_name,
                "role": default_role,
                "date": default_date,
                "action": "SIGN",
                "action_label": "تایید و امضای اولیه",
            }

    dossier_data["stage_signatures"] = stage_signatures
    dossier_data["user_can_action"] = user_can_action
    dossier_data["is_chief"] = is_chief
    dossier_data["is_check_admin"] = is_check_admin
    dossier_data["current_role"] = dossier.current_role
    dossier_data["current_stage_title"] = dossier.current_stage_title

    # 14 Archival Signatures & Stage Permission Setup
    user_allowed_stages = get_user_allowed_stages_set(request.user)
    dossier_data["user_allowed_stages"] = "all" if user_allowed_stages == "all" else list(user_allowed_stages)
    dossier_data["is_superuser"] = request.user.is_superuser
    dossier_data["stage_details"] = HousingDossier.STAGE_DETAILS

    context = {
        "dossier": dossier,
        "form_j_attachment": dossier.form_j_attachment,
        "stage_details": HousingDossier.STAGE_DETAILS,
        "attachments": attachments,
        "audit_logs": audit_logs,
        "field_changes": dossier.field_changes.all().order_by("-timestamp")[:500],
        "archive_number": dossier.archive_number,
        "dossier_json": json.dumps(dossier_data, ensure_ascii=False),
        "user_can_action": user_can_action,
        "is_chief": is_chief,
        "is_check_admin": is_check_admin,
        "can_view_audit": can_view_audit,
    }
    return render(request, "dossiers/detail.html", context)


@csrf_exempt
@transaction.atomic
def save_dossier_draft_view(request, pk):
    """
    Persists changes to the dossier's fields into the SQLite database with automated audit logging.
    Tracks who changed each field, when, and the exact before/after values.
    Enforces role-based permissions unless user is Superadmin or Housing Chief.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method allowed")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و مختومه گردیده است و امکان ویرایش آن وجود ندارد."}, status=400)

    profile = getattr(request.user, 'profile', None)
    user_can_action = request.user.is_superuser or (profile and profile.is_housing_chief) or (profile and profile.can_action_stage(dossier.current_stage))
    if not user_can_action:
        return JsonResponse({
            "status": "error",
            "message": f"شما دسترسی مجاز برای ویرایش اطلاعات در مرحله {dossier.current_stage} را ندارید. این مرحله در اختیار «{dossier.current_role}» یا رئیس مسکن می‌باشد."
        }, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    # Update current_stage if explicitly passed
    if "current_stage" in data:
        try:
            stg = int(data.get("current_stage"))
            if 1 <= stg <= 21:
                dossier.current_stage = stg
        except (ValueError, TypeError):
            pass

    # Extract user identity and client IP
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
        actor_role = profile.role_title if profile and profile.role_title else str(data.get("role") or dossier.current_role).strip()
    else:
        actor_name = str(data.get("actor") or "کارشناس اقدام‌کننده").strip()
        actor_role = str(data.get("role") or dossier.current_role).strip()

    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        ip_address = x_forwarded.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    parsed_updates = {}

    # String fields
    for field in [
        "full_name", "father_name", "birth_date", "applicant_phone",
        "applicant_form_j_status", "applicant_form_j_directorate_status", "applicant_form_j_red_description",
        "spouse_full_name", "spouse_father_name", "spouse_national_id",
        "spouse_birth_date", "spouse_id_number", "spouse_birth_place",
        "spouse_form_j_status", "spouse_form_j_directorate_status", "spouse_form_j_red_description",
        "marital_status",
        "site", "project", "construction_type", "block_name", "block_code",
        "unit_code", "unit_direction", "registration_section",
        "bank_letter_number", "bank_letter_date", "land_lease_year",
        "decile_loan_bank", "supported_institution", "commitment_number", "commitment_date",
        "tenant_code", "prepayment_code", "rah_letter", "rah_letter_date",
        "bank_sent_date", "bank_sent_letter_number"
    ]:
        if field in data and data[field] is not None:
            parsed_updates[field] = str(data[field]).strip()

    # Integer fields
    for field in [
        "selection_rank", "decile", "floor_number", "unit_number", "bedroom_count",
        "storage_number", "parking_number",
        "main_plaque", "separated_plaque", "sub_plaque", "plot_number",
        "base_cost_without_loan", "bank_loan_amount", "fund_loan_amount", "contractor_letter_amount",
        "decile_loan_amount", "past_years_rent", "current_year_rent",
        "preparation_cost", "cash_preparation_amount", "non_cash_preparation_amount",
        "check_count", "check_amount", "last_check_amount", "total_check_amount",
        "check_service_fee", "tenant_price", "preparation_service_fee"
    ]:
        if field in data:
            val = data[field]
            if val is None or val == "":
                if field in ["selection_rank", "storage_number", "parking_number", "main_plaque", "separated_plaque", "sub_plaque", "plot_number"]:
                    parsed_updates[field] = None
                elif field == "bank_loan_amount":
                    parsed_updates[field] = 6500000000
                else:
                    parsed_updates[field] = 0
            else:
                try:
                    parsed_updates[field] = int(val)
                except (ValueError, TypeError):
                    pass

    # Decimal / Float fields
    for field in [
        "unit_area", "storage_area", "parking_area", "total_land_share",
        "net_unit_area", "common_area", "total_area", "covered_parking_area"
    ]:
        if field in data:
            val = data[field]
            if val is None or val == "":
                if field == "total_land_share":
                    parsed_updates[field] = None
                else:
                    parsed_updates[field] = 0.0
            else:
                try:
                    parsed_updates[field] = round(float(val), 2)
                except (ValueError, TypeError):
                    pass

    # Boolean fields
    for field in ["is_sms_sent", "is_equity_funded", "is_cash_rent_confirmed", "is_decile_loan_confirmed", "is_married_confirmed", "is_preparation_checks_confirmed", "is_added_to_bank_shipment_list", "is_sent_to_bank"]:
        if field in data:
            val = data[field]
            parsed_updates[field] = bool(val) if not isinstance(val, str) else val.lower() in ("true", "1")

    # Enforce role-based field restrictions: everyone can only change what is related to him
    parsed_updates = filter_allowed_updates(request.user, parsed_updates)

    # Sync and persist Check entries list from BankCheckTracker
    if "check_entries" in data and isinstance(data["check_entries"], list) and can_user_edit_field(request.user, "check_entries_json"):
        entries_data = data["check_entries"]
        cleaned_entries = []
        total_sum = 0
        for idx, entry in enumerate(entries_data):
            c_date = str(entry.get("cash_date") or "").strip()
            c_sayadi = str(entry.get("check_sayadi_code") or "").strip()
            c_bank = str(entry.get("bank_name") or "").strip()
            try:
                c_amount = int(entry.get("check_amount") or 0)
            except (ValueError, TypeError):
                c_amount = 0
            total_sum += c_amount
            cleaned_entries.append({
                "row_number": idx + 1,
                "cash_date": c_date,
                "check_amount": c_amount,
                "check_sayadi_code": c_sayadi,
                "bank_name": c_bank,
            })
        dossier.check_entries_json = json.dumps(cleaned_entries, ensure_ascii=False)
        dossier.check_count = len(cleaned_entries)
        dossier.total_check_amount = total_sum
        if cleaned_entries:
            dossier.check_amount = cleaned_entries[0]["check_amount"]
            dossier.last_check_amount = cleaned_entries[-1]["check_amount"]
        parsed_updates["total_check_amount"] = total_sum
        parsed_updates["check_count"] = len(cleaned_entries)

        # Auto-calculate custody service fee (0.5% rounded half up from BankCheckTracker)
        fee_base = total_sum if total_sum > 0 else (dossier.decile_loan_amount or 0)
        calculated_fee = ((fee_base * 5 + 500) // 1000) if fee_base > 0 else 2000000
        dossier.check_service_fee = calculated_fee
        parsed_updates["check_service_fee"] = calculated_fee

        # Sync relational DossierCheck table for LOAN checks
        dossier.check_items.filter(check_type="LOAN").delete()
        for item in cleaned_entries:
            DossierCheck.objects.create(
                dossier=dossier,
                check_type="LOAN",
                row_number=item["row_number"],
                cash_date=item["cash_date"],
                check_amount=item["check_amount"],
                check_sayadi_code=item["check_sayadi_code"],
                bank_name=item["bank_name"],
            )

    # Sync and persist Preparation Check entries list from tashilatCheck
    if "preparation_check_entries" in data and isinstance(data["preparation_check_entries"], list) and can_user_edit_field(request.user, "preparation_check_entries_json"):
        prep_entries_data = data["preparation_check_entries"]
        cleaned_prep_entries = []
        prep_total_sum = 0
        for idx, entry in enumerate(prep_entries_data):
            c_date = str(entry.get("cash_date") or "").strip()
            c_sayadi = str(entry.get("check_sayadi_code") or "").strip()
            c_bank = str(entry.get("bank_name") or "").strip()
            try:
                c_amount = int(entry.get("check_amount") or 0)
            except (ValueError, TypeError):
                c_amount = 0
            prep_total_sum += c_amount
            cleaned_prep_entries.append({
                "row_number": idx + 1,
                "cash_date": c_date,
                "check_amount": c_amount,
                "check_sayadi_code": c_sayadi,
                "bank_name": c_bank,
            })
        dossier.preparation_check_entries_json = json.dumps(cleaned_prep_entries, ensure_ascii=False)
        dossier.preparation_check_count = len(cleaned_prep_entries)
        dossier.total_preparation_check_amount = prep_total_sum
        parsed_updates["total_preparation_check_amount"] = prep_total_sum
        parsed_updates["preparation_check_count"] = len(cleaned_prep_entries)

        # Sync relational DossierCheck table for PREPARATION checks
        dossier.check_items.filter(check_type="PREPARATION").delete()
        for item in cleaned_prep_entries:
            DossierCheck.objects.create(
                dossier=dossier,
                check_type="PREPARATION",
                row_number=item["row_number"],
                cash_date=item["cash_date"],
                check_amount=item["check_amount"],
                check_sayadi_code=item["check_sayadi_code"],
                bank_name=item["bank_name"],
            )

    # Detect field differences and construct audit change logs
    change_logs_to_create = []
    for field, new_val in parsed_updates.items():
        old_val = getattr(dossier, field, None)

        # Normalize values for fair diff comparison
        old_repr = "" if old_val is None else str(old_val).strip()
        new_repr = "" if new_val is None else str(new_val).strip()

        # For floats/decimals, normalize precision
        if field in ["unit_area", "storage_area", "parking_area", "total_land_share", "net_unit_area", "common_area", "total_area", "covered_parking_area"]:
            try:
                if old_val is not None:
                    old_repr = f"{float(old_val):.2f}"
                if new_val is not None:
                    new_repr = f"{float(new_val):.2f}"
            except (ValueError, TypeError):
                pass

        if old_repr != new_repr:
            field_label = DOSSIER_FIELD_LABELS.get(field, field)
            old_display = old_repr if old_repr != "" else "خالی"
            new_display = new_repr if new_repr != "" else "خالی"

            if isinstance(new_val, bool):
                old_display = "بله (تایید شده)" if old_val else "خیر"
                new_display = "بله (تایید شده)" if new_val else "خیر"

            log_entry = DossierFieldChangeLog(
                dossier=dossier,
                field_name=field,
                field_label=field_label,
                old_value=old_display,
                new_value=new_display,
                changed_by=actor_name,
                role=actor_role,
                stage=dossier.current_stage,
                ip_address=ip_address,
                timestamp=timezone.now()
            )
            change_logs_to_create.append(log_entry)
            setattr(dossier, field, new_val)

    if change_logs_to_create:
        DossierFieldChangeLog.objects.bulk_create(change_logs_to_create)

    dossier.save()

    recent_changes = [
        {
            "id": log.id,
            "fieldName": log.field_name,
            "fieldLabel": log.field_label,
            "oldValue": log.old_value,
            "newValue": log.new_value,
            "changedBy": log.changed_by,
            "role": log.role,
            "stage": log.stage,
            "timestamp": log.timestamp.strftime("%Y/%m/%d %H:%M:%S"),
            "ipAddress": log.ip_address or "-"
        }
        for log in change_logs_to_create
    ]

    return JsonResponse({
        "status": "success",
        "message": f"اطلاعات با موفقیت ذخیره شد. ({len(change_logs_to_create)} مورد تغییر در تاریخچه ثبت گردید)",
        "current_stage": dossier.current_stage,
        "applicant_equity": dossier.applicant_equity,
        "check_service_fee": dossier.check_service_fee,
        "total_check_amount": dossier.total_check_amount,
        "total_preparation_check_amount": dossier.total_preparation_check_amount,
        "preparation_check_count": dossier.preparation_check_count,
        "new_changes": recent_changes
    })


@csrf_exempt
@transaction.atomic
def set_dossier_stage_view(request, pk):
    """
    Direct stage jumping is strictly prohibited to enforce workflow continuity.
    Stages stick to the official record until transitioned via electronic signature or formal return.
    """
    return JsonResponse({
        "status": "error",
        "message": "تغییر مستقیم مرحله بدون طی گردش کار مجاز نمی‌باشد. پرونده باید صرفاً از طریق تایید و امضای الکترونیک یا برگشت جهت اصلاح جابجا شود."
    }, status=403)


@csrf_exempt
@transaction.atomic
def electronic_sign_action(request, pk):
    """
    Handles electronic signature and forwards the dossier to the next stage (select_for_update).
    Supports all 21 stages (1 to 21).
    Enforces role-based permissions unless user is Superadmin or Housing Chief.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = HousingDossier.objects.select_for_update().get(archive_number=pk)

    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و مختومه گردیده است."}, status=400)

    # Permission check for active stage
    profile = getattr(request.user, 'profile', None)
    user_can_action = request.user.is_superuser or (profile and profile.is_housing_chief) or (profile and profile.can_action_stage(dossier.current_stage))
    if not user_can_action:
        return JsonResponse({
            "status": "error",
            "message": f"شما دسترسی مجاز برای تایید و امضای الکترونیک در مرحله {dossier.current_stage} را ندارید. این اقدام مختص «{dossier.current_role}» یا رئیس مسکن می‌باشد."
        }, status=403)

    try:
        body_data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body_data = {}

    current_idx = dossier.current_stage
    current_role = dossier.current_role
    current_title = dossier.current_stage_title

    next_stage = current_idx + 1

    # Generate SHA-256 integrity hash
    raw_stamp = f"{dossier.archive_number}-{current_idx}-{next_stage}-{timezone.now().isoformat()}"
    sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

    if current_idx >= 21:
        dossier.is_locked = True
        dossier.status = "COMPLETED"
        action = "ARCHIVE"
        action_label = "بایگانی قطعی پرونده"
        to_stage_str = "بایگانی نهایی (مختومه)"
    else:
        dossier.current_stage = next_stage
        dossier.status = "IN_PROGRESS"
        dossier.return_reason = ""
        dossier.return_by = ""
        dossier.return_from_stage = None
        action = "SIGN"
        action_label = "تایید و امضای الکترونیکی"
        to_stage_str = f"مرحله {next_stage}: {dossier.STAGE_ROLES.get(next_stage, ('','',f'مرحله {next_stage}'))[2]}"

    dossier.save()

    notes = body_data.get("notes") or request.POST.get("notes", "تایید و امضای الکترونیکی با موفقیت انجام شد.")

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
        actor_role = profile.role_title if profile and profile.role_title else current_role
    else:
        actor_name = "کارشناس اقدام‌کننده"
        actor_role = current_role

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

    # Auto-link expert profile signature to official archival slots (شناسنامه جامع بایگانی)
    stage_to_slots = {
        1: ["brokerage"],
        3: ["form_j"],
        4: ["other_facilities", "decile_facility"],
        5: ["applicant_settlement"],
        6: ["bank_facility"],
        8: ["brokerage"],
        9: ["national_housing", "bank_facility"],
        10: ["form_j"],
        11: ["technical"],
        12: ["real_estate"],
        13: ["land_bank"],
        14: ["legal"],
        15: ["evaluation"],
        16: ["decile_facility"],
        17: ["revenue"],
        18: ["contractor_settlement"],
    }
    target_slots = stage_to_slots.get(current_idx, [])
    import jdatetime
    try:
        now_jalali = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M")
    except Exception:
        now_jalali = timezone.now().strftime("%Y/%m/%d %H:%M")

    for slot_key in target_slots:
        sig_obj, _ = DossierSignature.objects.get_or_create(dossier=dossier, slot_key=slot_key)
        sig_obj.signer_name = actor_name
        sig_obj.signer_title = actor_role
        sig_obj.signed_date = now_jalali
        sig_obj.uploaded_by = request.user.username if request.user.is_authenticated else actor_name
        if profile and profile.signature_image:
            sig_obj.signature_image = profile.signature_image
        sig_obj.save()

    if request.headers.get("HX-Request"):
        return redirect("dossier_detail", pk=dossier.archive_number)

    return JsonResponse({
        "status": "success",
        "new_stage": dossier.current_stage,
        "is_locked": dossier.is_locked,
        "hash": sig_hash,
        "message": f"پرونده با موفقیت به مرحله {dossier.current_stage} منتقل گردید."
    })


@csrf_exempt
@transaction.atomic
def return_stage_action(request, pk):
    """
    Handles backward routing / rejection for correction (select_for_update).
    Supports all 22 stages: any stage > 0 can return to any prior stage >= 0.
    Enforces role-based permissions unless user is Superadmin or Housing Chief.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = HousingDossier.objects.select_for_update().get(archive_number=pk)

    # Permission check for active stage
    profile = getattr(request.user, 'profile', None)
    is_chief_or_admin = request.user.is_superuser or (profile and profile.is_housing_chief)
    user_can_action = is_chief_or_admin or (profile and (profile.can_action_stage(dossier.current_stage) or profile.can_action_stage(3) or profile.can_action_stage(10)))
    if not user_can_action:
        return JsonResponse({
            "status": "error",
            "message": f"شما دسترسی مجاز برای بازگردانی پرونده از مرحله {dossier.current_stage} را ندارید. این اقدام مختص «{dossier.current_role}» یا رئیس مسکن می‌باشد."
        }, status=403)

    if dossier.is_locked:
        # Admin / Chief can unlock and return rejected/red Form J dossiers for correction
        if is_chief_or_admin and (dossier.status == "REJECTED_RED" or dossier.is_red_form_j):
            dossier.is_locked = False
        else:
            return JsonResponse({"status": "error", "message": "پرونده بایگانی‌شده قابل بازگشت نیست."}, status=400)

    try:
        body_data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body_data = {}

    if "target_stage" in body_data:
        target_stage_val = body_data.get("target_stage")
    else:
        target_stage_val = request.POST.get("target_stage")
    try:
        target_stage = int(target_stage_val)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "مرحله مقصد نامعتبر است."}, status=400)

    notes = (body_data.get("notes") or request.POST.get("notes", "")).strip()
    if len(notes) < 5:
        return JsonResponse({"status": "error", "message": "ثبت توضیحات دلیل برگشت الزامی است (حداقل ۵ کاراکتر)."}, status=400)

    current_idx = dossier.current_stage

    if current_idx == 1 and target_stage == 1 and is_chief_or_admin:
        pass
    elif target_stage >= current_idx or target_stage < 1:
        return JsonResponse({"status": "error", "message": "مرحله برگشت باید از مرحله فعلی کوچکتر یا مرحله جاری جهت بازبینی باشد."}, status=400)

    current_title = dossier.current_stage_title
    current_role = dossier.current_role
    target_title = dossier.STAGE_ROLES.get(target_stage, ('','',f'مرحله {target_stage}'))[2]

    raw_stamp = f"RETURN-{dossier.archive_number}-{current_idx}-{target_stage}-{timezone.now().isoformat()}"
    sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
        actor_role = profile.role_title if profile and profile.role_title else current_role
    else:
        actor_name = "کارشناس بررسی و ممیزی"
        actor_role = current_role

    dossier.current_stage = target_stage
    dossier.status = "RETURNED"
    dossier.return_reason = notes
    dossier.return_by = actor_name
    dossier.return_from_stage = current_idx
    dossier.save()

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {current_idx}: {current_title}",
        to_stage=f"مرحله {target_stage}: {target_title}",
        actor=actor_name,
        role=actor_role,
        action="RETURN",
        action_label="برگشت جهت اصلاح",
        signature_hash=sig_hash,
        notes=notes
    )

    if request.headers.get("HX-Request"):
        return redirect("dossier_detail", pk=dossier.archive_number)

    return JsonResponse({
        "status": "success",
        "new_stage": dossier.current_stage,
        "dossier_status": dossier.status,
        "return_reason": dossier.return_reason,
        "return_by": dossier.return_by,
        "return_from_stage": dossier.return_from_stage,
        "hash": sig_hash,
        "message": f"پرونده جهت بازبینی به مرحله {target_stage} برگشت داده شد."
    })


def lookup_preselected_unit_api(request):
    """
    Stage 1 Auto-Population endpoint: queries PreSelectedUnit table by national_id.
    """
    national_id = request.GET.get("national_id", "").strip()
    if not national_id:
        return JsonResponse({"status": "error", "message": "کد ملی الزامی است."}, status=400)

    try:
        unit = PreSelectedUnit.objects.get(national_id=national_id)
        data = {
            "status": "success",
            "full_name": unit.full_name,
            "father_name": unit.father_name,
            "birth_date": unit.birth_date,
            "applicant_phone": unit.applicant_phone or "",
            "selection_rank": unit.selection_rank,
            "applicant_form_j_status": unit.applicant_form_j_status,
            "applicant_form_j_directorate_status": unit.applicant_form_j_directorate_status,
            "applicant_form_j_red_description": unit.applicant_form_j_red_description,
            "spouse_full_name": unit.spouse_full_name,
            "spouse_father_name": unit.spouse_father_name,
            "spouse_national_id": unit.spouse_national_id,
            "spouse_birth_date": unit.spouse_birth_date,
            "spouse_id_number": unit.spouse_id_number,
            "spouse_birth_place": unit.spouse_birth_place,
            "spouse_form_j_status": unit.spouse_form_j_status,
            "spouse_form_j_directorate_status": unit.spouse_form_j_directorate_status,
            "spouse_form_j_red_description": unit.spouse_form_j_red_description,
            "marital_status": unit.marital_status,
            "is_married_confirmed": unit.is_married_confirmed,
            "decile": unit.decile,
            "site": unit.site.name if unit.site else "",
            "project": str(unit.project) if unit.project else "",
            "construction_type": unit.construction_type,
            "block_name": unit.block_name,
            "block_code": unit.block_code,
            "floor_number": unit.floor_number,
            "unit_number": unit.unit_number,
            "unit_code": unit.unit_code,
            "bedroom_count": unit.bedroom_count,
            "unit_direction": unit.unit_direction,
            "net_unit_area": str(unit.net_unit_area),
            "common_area": str(unit.common_area),
            "total_area": str(unit.total_area),
            "unit_area": str(unit.unit_area),
            "storage_number": unit.storage_number,
            "storage_area": str(unit.storage_area),
            "parking_number": unit.parking_number,
            "parking_area": str(unit.parking_area),
            "covered_parking_area": str(unit.covered_parking_area),
            "base_cost_without_loan": unit.base_cost_without_loan,
            "bank_loan_amount": unit.bank_loan_amount,
            "registration_section": unit.registration_section,
            "main_plaque": unit.main_plaque,
            "separated_plaque": unit.separated_plaque,
            "sub_plaque": unit.sub_plaque,
            "plot_number": unit.plot_number,
        }
        return JsonResponse(data)


    except PreSelectedUnit.DoesNotExist:
        return JsonResponse({"status": "not_found", "message": "اطلاعاتی با این کد ملی در بانک انتخاب واحد یافت نشد."}, status=404)


@login_required(login_url='login')
def notary_letter_print_view(request, pk):
    """
    Print-ready view for Stage 23 & 24 (Notary Letter Introduction).
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    return render(request, "dossiers/print_notary.html", {"dossier": dossier})


def get_dossier_signatures_summary(dossier):
    """
    Returns (signatures_map, signed_count) for the 14 official archival slots.
    Prioritizes DossierSignature, and synchronizes from WorkflowSignatureLog and UserProfile.
    """
    import re
    import jdatetime
    
    sigs = {s.slot_key: s for s in dossier.signatures.all()}
    
    stage_to_slots = {
        1: ["brokerage"],
        3: ["form_j"],
        4: ["other_facilities", "decile_facility"],
        5: ["applicant_settlement"],
        6: ["bank_facility"],
        8: ["brokerage"],
        9: ["national_housing", "bank_facility"],
        10: ["form_j"],
        11: ["technical"],
        12: ["real_estate"],
        13: ["land_bank"],
        14: ["legal"],
        15: ["evaluation"],
        16: ["decile_facility"],
        17: ["revenue"],
        18: ["contractor_settlement"],
    }
    
    # Check WorkflowSignatureLog to find if stages were signed
    for log in dossier.audit_logs.filter(action__in=["SIGN", "APPROVE", "ARCHIVE"]).order_by("timestamp"):
        m = re.search(r'مرحله\s+(\d+)', log.from_stage)
        if not m:
            continue
        stg_num = int(m.group(1))
        target_slots = stage_to_slots.get(stg_num, [])
        for slot_key in target_slots:
            sig_obj = sigs.get(slot_key)
            try:
                jdt = jdatetime.datetime.fromgregorian(datetime=log.timestamp)
                date_str = jdt.strftime("%Y/%m/%d - %H:%M")
            except Exception:
                date_str = log.timestamp.strftime("%Y/%m/%d - %H:%M")

            user_profile = UserProfile.objects.filter(full_name=log.actor).first()
            if not user_profile:
                user_match = User.objects.filter(username=log.actor).first()
                if user_match:
                    user_profile = getattr(user_match, 'profile', None)

            if not sig_obj:
                sig_img = user_profile.signature_image if user_profile else None
                sig_obj = DossierSignature(
                    dossier=dossier,
                    slot_key=slot_key,
                    signer_name=log.actor,
                    signer_title=log.role or "کارشناس اقدام‌کننده",
                    signed_date=date_str,
                    signature_image=sig_img,
                    uploaded_by=log.actor
                )
                try:
                    sig_obj.save()
                except Exception:
                    pass
                sigs[slot_key] = sig_obj
            else:
                if not sig_obj.signed_date:
                    sig_obj.signed_date = date_str
                if not sig_obj.signature_image and user_profile and user_profile.signature_image:
                    sig_obj.signature_image = user_profile.signature_image
                    try:
                        sig_obj.save()
                    except Exception:
                        pass

    # Count how many of the 14 slots have been signed
    ALL_SLOTS = [
        "brokerage", "national_housing", "bank_facility", "decile_facility",
        "contractor_settlement", "applicant_settlement", "other_facilities",
        "legal", "form_j", "evaluation", "technical", "real_estate", "land_bank", "revenue"
    ]
    signed_count = sum(1 for k in ALL_SLOTS if k in sigs and sigs[k].signed_date)
    return sigs, signed_count

@login_required(login_url='login')
def dossier_summary_print_view(request, pk):
    """
    Print-ready view for Stage 24 (Final Archival Summary Sheet).
    Passes the 14 official archival signatures and Jalali report date.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    import jdatetime
    try:
        today_jalali = jdatetime.date.today().strftime("%Y/%m/%d")
    except Exception:
        today_jalali = dossier.stage_entry_date_jalali
    
    signatures_map, signed_count = get_dossier_signatures_summary(dossier)
    return render(request, "dossiers/print_summary.html", {
        "dossier": dossier,
        "signatures_map": signatures_map,
        "signed_count": signed_count,
        "today_jalali": today_jalali
    })


def _ensure_check_receipt_attachment(user, dossier, check_type="loan", scan_url=""):
    """
    Creates or retrieves the official check receipt attachment in DossierAttachment
    only when a real physical scan image is provided. Never registers broken HTML print URLs.
    """
    if not scan_url:
        return None

    check_type_norm = "prep" if check_type in ("prep", "preparation", "amadesazi") else "loan"
    doc_type = "PREP_CHECK" if check_type_norm == "prep" else "LOAN_CHECK"
    type_label = "اقساط آماده‌سازی و اجاره" if check_type_norm == "prep" else "تسهیلات وام دهک"
    title = f"اسکن چک‌ها و رسید {type_label}"
    file_name = os.path.basename(scan_url)
    preview_url = scan_url
    
    # Check if this receipt attachment already exists
    att = dossier.attachments.filter(preview_url=preview_url).first()
    if att:
        return att
        
    profile = getattr(user, 'profile', None) if user and user.is_authenticated else None
    if profile and profile.full_name:
        uploader_name = profile.full_name
        uploader_role = profile.role_title or "متصدی دریافت چک"
    elif user and user.is_authenticated:
        uploader_name = user.get_full_name() or user.username
        uploader_role = "متصدی دریافت چک"
    else:
        uploader_name = "متصدی ثبت و دریافت چک"
        uploader_role = "امور چک و تضامین"

    import hashlib
    raw_hash = f"{dossier.archive_number}-CHECK-RECEIPT-{check_type_norm}-{timezone.now().isoformat()}"
    file_sha = "SHA256: " + hashlib.sha256(raw_hash.encode('utf-8')).hexdigest()[:24]

    target_chk_stage = 16 if check_type_norm == "loan" else 17
    att = DossierAttachment.objects.create(
        dossier=dossier,
        stage=target_chk_stage,
        doc_type=doc_type,
        title=title,
        file_name=file_name,
        file_sha256=file_sha,
        uploaded_by=uploader_name,
        preview_url=preview_url
    )

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {target_chk_stage}: دریافت چک‌های {type_label}",
        to_stage=f"مرحله {target_chk_stage}: دریافت چک‌های {type_label}",
        actor=uploader_name,
        role=uploader_role,
        action="PRINT_RECEIPT",
        action_label=f"صدور و بایگانی رسید چک‌های {type_label}",
        signature_hash=file_sha,
        notes=f"رسید رسمی تحویل چک‌های {type_label} با موفقیت صادر و به آلبوم اسناد اسکن‌شده پرونده افزوده شد."
    )
    return att


@login_required(login_url='login')
def dossier_print_checks_view(request, pk):
    """
    Print-ready official check receipt document based on print.ts from BankCheckTracker & tashilatCheck.
    Renders an A4 document with the 2-row overlay header, the check scan image in the center,
    financial summary bar, and official recipient/issuer signature boxes.
    Also ensures the printed receipt is automatically preserved in the DossierAttachment scan album.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    check_type = request.GET.get('type', 'loan').lower()
    check_type_norm = "prep" if check_type in ("prep", "preparation", "amadesazi") else "loan"
    doc_type = "PREP_CHECK" if check_type_norm == "prep" else "LOAN_CHECK"
    auto_archive = request.GET.get('auto_archive', '1') == '1'
    scan_url = request.GET.get('scan_url') or ""

    # Look for existing check scan if scan_url not passed
    if not scan_url:
        existing_scan = dossier.attachments.filter(doc_type=doc_type).exclude(preview_url__contains="/print/checks/").order_by("-id").first()
        if existing_scan and existing_scan.preview_url:
            scan_url = existing_scan.preview_url

    if auto_archive:
        _ensure_check_receipt_attachment(request.user, dossier, check_type_norm, scan_url=scan_url)

    import jdatetime
    now_j = jdatetime.datetime.now().strftime("%Y/%m/%d")

    loan_checks = list(dossier.check_items.filter(check_type="LOAN").order_by("row_number", "id"))
    prep_checks = list(dossier.check_items.filter(check_type="PREPARATION").order_by("row_number", "id"))

    if not loan_checks and dossier.check_entries_json:
        try:
            loan_checks = json.loads(dossier.check_entries_json)
        except Exception:
            loan_checks = []
    if not prep_checks and dossier.preparation_check_entries_json:
        try:
            prep_checks = json.loads(dossier.preparation_check_entries_json)
        except Exception:
            prep_checks = []

    def _calc_sum(items):
        total = 0
        for item in items:
            val = getattr(item, 'check_amount', None)
            if val is None and isinstance(item, dict):
                val = item.get('check_amount', 0)
            try:
                total += int(val or 0)
            except Exception:
                pass
        return total

    total_loan_amount = dossier.total_check_amount or _calc_sum(loan_checks)
    total_prep_amount = dossier.total_preparation_check_amount or _calc_sum(prep_checks)

    context = {
        "dossier": dossier,
        "form_j_attachment": dossier.form_j_attachment,
        "stage_details": HousingDossier.STAGE_DETAILS,
        "check_type": check_type_norm,
        "today_jalali": now_j,
        "loan_checks": loan_checks,
        "prep_checks": prep_checks,
        "total_loan_amount": total_loan_amount,
        "total_prep_amount": total_prep_amount,
        "scan_url": scan_url,
    }
    return render(request, "dossiers/print_checks.html", context)


@login_required(login_url='login')
@csrf_exempt
def archive_check_receipt_api(request, pk):
    """
    API endpoint invoked when the user clicks 'چاپ رسید چک‌ها'.
    Registers the print receipt into DossierAttachment immediately and returns
    JSON so the Alpine frontend adds it to the Scans Album in real time without refreshing.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST or {}

    check_type = data.get('type', 'loan').lower()
    scan_url = data.get('scan_url', '')
    attachment = _ensure_check_receipt_attachment(request.user, dossier, check_type, scan_url=scan_url)

    return JsonResponse({
        "status": "success",
        "attachment": {
            "id": attachment.id,
            "stage": attachment.stage,
            "type": attachment.doc_type,
            "title": attachment.title,
            "fileName": attachment.file_name,
            "uploader": attachment.uploaded_by,
            "uploadDate": attachment.uploaded_at.strftime("%Y/%m/%d"),
            "sha256": attachment.file_sha256,
            "preview_url": attachment.preview_url,
            "immutable": True
        }
    })


@login_required(login_url='login')
@csrf_exempt
def upload_check_scan_and_create_receipt_view(request, pk):
    """
    Endpoint that gets a check scan (upload or existing),
    attaches the official Header & Footer according to print.ts,
    saves that as the official check receipt in DossierAttachment,
    and returns JSON with the created attachments and the print URL.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    check_type = request.POST.get('check_type', 'loan').lower()
    check_type_norm = "prep" if check_type in ("prep", "preparation", "amadesazi") else "loan"
    doc_type = "PREP_CHECK" if check_type_norm == "prep" else "LOAN_CHECK"
    type_label = "اقساط آماده‌سازی و اجاره" if check_type_norm == "prep" else "تسهیلات وام دهک"

    profile = getattr(request.user, 'profile', None) if request.user and request.user.is_authenticated else None
    if profile and profile.full_name:
        uploader_name = profile.full_name
        uploader_role = profile.role_title or "متصدی دریافت چک"
    elif request.user and request.user.is_authenticated:
        uploader_name = request.user.get_full_name() or request.user.username
        uploader_role = "متصدی دریافت چک"
    else:
        uploader_name = "متصدی ثبت و دریافت چک"
        uploader_role = "امور چک و تضامین"

    saved_url = ""
    file_obj = request.FILES.get('file')
    if file_obj:
        nat_id = dossier.national_id or "general"
        upload_dir = os.path.join(settings.MEDIA_ROOT, nat_id, "check_scans")
        os.makedirs(upload_dir, exist_ok=True)

        clean_name = f"check_scan_{dossier.archive_number}_{check_type_norm}_{int(timezone.now().timestamp())}_{file_obj.name}"
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in "._-")
        save_path = os.path.join(upload_dir, clean_name)

        with open(save_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        saved_url = f"{settings.MEDIA_URL}{nat_id}/check_scans/{clean_name}"
    else:
        saved_url = request.POST.get('preview_url') or ""
        if not saved_url:
            existing_scan = dossier.attachments.filter(doc_type=doc_type).exclude(preview_url__contains="/print/checks/").order_by("-id").first()
            if existing_scan:
                saved_url = existing_scan.preview_url

    import hashlib
    raw_hash = f"{dossier.archive_number}-SCAN-{check_type_norm}-{timezone.now().isoformat()}"
    file_sha = "SHA256: " + hashlib.sha256(raw_hash.encode('utf-8')).hexdigest()[:24]

    # 1. Create raw scan attachment if file was uploaded
    target_chk_stage = 16 if check_type_norm == "loan" else 17
    if file_obj and saved_url:
        DossierAttachment.objects.create(
            dossier=dossier,
            stage=target_chk_stage,
            doc_type=doc_type,
            title=f"اسکن اصل چک‌های صیادی {type_label}",
            file_name=file_obj.name,
            file_sha256=file_sha,
            uploaded_by=uploader_name,
            preview_url=saved_url
        )

    # 2. Create the Official Checks Receipt with Header & Footer
    receipt_title = f"رسید رسمی و برگه تحویل چک‌های {type_label} (با تصویر اسکن)"
    receipt_filename = f"check_receipt_{dossier.archive_number}_{check_type_norm}.html"
    receipt_hash = "SHA256: " + hashlib.sha256(f"{dossier.archive_number}-RECEIPT-{check_type_norm}-{timezone.now().isoformat()}".encode('utf-8')).hexdigest()[:24]
    
    import urllib.parse
    preview_query = f"?scan_url={urllib.parse.quote(saved_url)}&type={check_type_norm}&auto_archive=0" if saved_url else f"?type={check_type_norm}&auto_archive=0"
    print_preview_url = f"/dossier/{dossier.archive_number}/print/checks/{preview_query}"

    receipt_att = DossierAttachment.objects.create(
        dossier=dossier,
        stage=target_chk_stage,
        doc_type=doc_type,
        title=receipt_title,
        file_name=receipt_filename,
        file_sha256=receipt_hash,
        uploaded_by=uploader_name,
        preview_url=print_preview_url
    )

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {target_chk_stage}: دریافت چک‌های {type_label}",
        to_stage=f"مرحله {target_chk_stage}: دریافت چک‌های {type_label}",
        actor=uploader_name,
        role=uploader_role,
        action="SUBMIT_AND_PRINT",
        action_label=f"بارگذاری اسکن و صدور رسید چک‌های {type_label}",
        signature_hash=receipt_hash,
        notes=f"تصویر اسکن چک‌های {type_label} دریافت، سربرگ متمرکز و کادر امضاها اضافه و به عنوان رسید رسمی در آلبوم اسکن ذخیره شد."
    )

    print_url = f"/dossier/{dossier.archive_number}/print/checks/{preview_query}&auto_print=1"

    return JsonResponse({
        "status": "success",
        "attachment": {
            "id": receipt_att.id,
            "stage": receipt_att.stage,
            "type": receipt_att.doc_type,
            "title": receipt_att.title,
            "fileName": receipt_att.file_name,
            "uploader": receipt_att.uploaded_by,
            "uploadDate": receipt_att.uploaded_at.strftime("%Y/%m/%d"),
            "sha256": receipt_att.file_sha256,
            "preview_url": receipt_att.preview_url,
            "immutable": True
        },
        "scan_url": saved_url,
        "print_url": print_url
    })


@login_required(login_url='login')
@csrf_exempt
@transaction.atomic
def reject_red_form_j_action(request, pk):
    """
    Action for Housing Chief / Superadmin to formally reject a disqualified dossier
    due to a Red Form J code (past housing subsidy or property ownership).
    Sets status to REJECTED_RED, locks the dossier (archived), and logs the official letter.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    profile = getattr(request.user, 'profile', None)
    is_chief = bool(profile and profile.is_housing_chief)
    if not (request.user.is_superuser or is_chief or request.user.is_staff):
        return JsonResponse({
            "status": "error",
            "message": "تنها رئیس مسکن و مدیران سیستم مجاز به صدور ابلاغیه رد صلاحیت و بایگانی قطعی پرونده‌های دارای فرم «ج» قرمز می‌باشند."
        }, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    letter_num = str(data.get("letter_number") or f"1403/رد/{dossier.archive_number}").strip()
    letter_date = str(data.get("letter_date") or "").strip()
    if not letter_date:
        import jdatetime
        letter_date = jdatetime.datetime.now().strftime("%Y/%m/%d")

    reason = str(data.get("reason") or dossier.applicant_form_j_red_description or dossier.spouse_form_j_red_description or "دارای سابقه مسکن دولتی و فاقد شرایط دریافت واحد").strip()

    actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
    actor_role = profile.role_title if profile and profile.role_title else "رئیس مسکن و شهرسازی"

    # Update dossier state
    old_status = dossier.status
    dossier.status = "REJECTED_RED"
    dossier.is_locked = True
    dossier.rejection_letter_number = letter_num
    dossier.rejection_letter_date = letter_date
    dossier.rejection_reason = reason
    dossier.rejected_by = actor_name
    dossier.save()

    # Log electronic audit trail
    import hashlib
    raw_hash = f"{dossier.archive_number}-REJECT_RED-{letter_num}-{letter_date}-{timezone.now().isoformat()}"
    sig_hash = hashlib.sha256(raw_hash.encode('utf-8')).hexdigest()

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {dossier.current_stage}: {dossier.current_stage_title}",
        to_stage="بایگانی پرونده‌های رد صلاحیت شده (کد قرمز فرم ج)",
        actor=actor_name,
        role=actor_role,
        action="REJECT_RED",
        action_label="رد صلاحیت قطعی و صدور نامه عدم احراز شرایط (فرم ج قرمز)",
        notes=f"شماره ابلاغیه: {letter_num} | تاریخ: {letter_date} | علت: {reason}",
        signature_hash=sig_hash
    )

    DossierFieldChangeLog.objects.create(
        dossier=dossier,
        field_name="status",
        field_label="وضعیت فرآیند",
        old_value=old_status,
        new_value="رد صلاحیت - کد قرمز فرم «ج» (عدم واگذاری واحد)",
        changed_by=actor_name,
        role=actor_role,
        stage=dossier.current_stage,
        ip_address=request.META.get('REMOTE_ADDR'),
        timestamp=timezone.now()
    )

    return JsonResponse({
        "status": "success",
        "message": f"نامه رد صلاحیت به شماره {letter_num} صادر و پرونده با وضعیت فاقد شرایط مسکن بایگانی گردید.",
        "dossier_status": dossier.status,
        "is_locked": dossier.is_locked,
        "is_rejected": True,
        "rejection_letter_number": dossier.rejection_letter_number,
        "rejection_letter_date": dossier.rejection_letter_date,
        "rejection_reason": dossier.rejection_reason,
        "rejected_by": dossier.rejected_by,
    })


@csrf_exempt
@transaction.atomic
def return_red_form_j_action(request, pk):
    """
    Action for Housing Chief / Superadmin to return a Red Form J dossier for correction or re-inquiry.
    Unlocks the dossier if it was locked/archived, resets status to RETURNED,
    sets current_stage to target stage (0 or 1), records the official notes,
    optionally resets Form J status to 'در حال استعلام' for fresh verification,
    and logs the event in WorkflowSignatureLog and DossierFieldChangeLog.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    profile = getattr(request.user, 'profile', None)
    is_chief = bool(profile and profile.is_housing_chief)
    if not (request.user.is_superuser or is_chief or request.user.is_staff):
        return JsonResponse({
            "status": "error",
            "message": "تنها رئیس مسکن و مدیران سیستم مجاز به بازگشت پرونده‌های دارای فرم «ج» قرمز جهت اصلاح و استعلام مجدد می‌باشند."
        }, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    try:
        target_stage = int(data.get("target_stage", 0))
    except (ValueError, TypeError):
        target_stage = 0
    if target_stage not in [0, 1]:
        target_stage = 0

    notes = str(data.get("notes") or "").strip()
    if len(notes) < 5:
        return JsonResponse({
            "status": "error",
            "message": "ثبت توضیحات و دستور اداری بازگشت جهت اصلاح الزامی است (حداقل ۵ کاراکتر)."
        }, status=400)

    reset_form_j = bool(data.get("reset_form_j", True))

    actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
    actor_role = profile.role_title if profile and profile.role_title else "رئیس مسکن و شهرسازی"

    old_status = dossier.status
    old_stage = dossier.current_stage

    # Unlock and update status
    dossier.is_locked = False
    dossier.status = "RETURNED"
    dossier.current_stage = target_stage
    dossier.return_reason = notes
    dossier.return_by = actor_name
    dossier.return_from_stage = old_stage

    # If requested, reset the red Form J status so applicant/brokerage can re-inquire cleanly
    if reset_form_j:
        if "قرمز" in (dossier.applicant_form_j_status or ""):
            dossier.applicant_form_j_status = "در حال استعلام"
        if "قرمز" in (dossier.spouse_form_j_status or ""):
            dossier.spouse_form_j_status = "در حال استعلام"
        dossier.applicant_form_j_red_description = ""
        dossier.spouse_form_j_red_description = ""

    dossier.save()

    # Generate audit hash
    import hashlib
    raw_hash = f"{dossier.archive_number}-RETURN_RED-{old_stage}-{target_stage}-{timezone.now().isoformat()}"
    sig_hash = "SHA256: " + hashlib.sha256(raw_hash.encode('utf-8')).hexdigest()[:24]

    # Log in WorkflowSignatureLog
    target_title = dossier.STAGE_ROLES.get(target_stage, ('','',f'مرحله {target_stage}'))[2]
    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {old_stage}: {dossier.current_stage_title} (کد قرمز فرم «ج»)",
        to_stage=f"مرحله {target_stage}: {target_title}",
        actor=actor_name,
        role=actor_role,
        action="RETURN",
        action_label="بازگشت جهت اصلاح، رفع مغایرت و استعلام مجدد فرم «ج»",
        notes=notes,
        signature_hash=sig_hash
    )

    # Log in DossierFieldChangeLog
    DossierFieldChangeLog.objects.create(
        dossier=dossier,
        field_name="status",
        field_label="وضعیت فرآیند",
        old_value=old_status,
        new_value="برگشت‌خورده جهت اصلاح و استعلام مجدد",
        changed_by=actor_name,
        role=actor_role,
        stage=target_stage,
        ip_address=request.META.get('REMOTE_ADDR'),
        timestamp=timezone.now()
    )

    return JsonResponse({
        "status": "success",
        "message": f"پرونده با موفقیت جهت اصلاح و استعلام مجدد به مرحله {target_stage} بازگردانده شد و قفل آن باز گردید.",
        "new_stage": target_stage,
        "dossier_status": "RETURNED",
        "is_locked": False,
        "is_rejected": False,
        "applicant_form_j_status": dossier.applicant_form_j_status,
        "spouse_form_j_status": dossier.spouse_form_j_status,
        "hash": sig_hash
    })


@login_required(login_url='login')
def red_rejection_letter_print_view(request, pk):
    """
    Print-ready view for Red Form J Rejection & Disqualification Letter.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    import jdatetime
    today_jalali = jdatetime.datetime.now().strftime("%Y/%m/%d")
    return render(request, "dossiers/print_red_rejection.html", {
        "dossier": dossier,
        "today_jalali": today_jalali
    })


@csrf_exempt
def upload_scan_attachment_view(request, pk):
    """
    Handles uploading or scanning a new document attachment for the dossier.
    Saves document physically into the root 'uploads/<national_id>/' folder.
    Validates stage-ownership, allowed stages, and generates SHA-256 integrity hash.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)

    # 1. Dossier lock verification
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و بایگانی شده است و امکان بارگذاری مدارک جدید وجود ندارد."}, status=400)

    # 2. User authorization & role check
    title = request.POST.get("title", "").strip() or "مدرک بارگذاری‌شده"
    doc_type = request.POST.get("doc_type", "OTHER")

    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    is_chief_or_admin = request.user.is_superuser or (profile and (profile.is_housing_chief or profile.organization == 'system' or profile.allowed_stages == 'all'))
    user_can_action = is_chief_or_admin or (profile and (profile.can_action_stage(dossier.current_stage) or (doc_type == "FORM_J" and (profile.can_action_stage(3) or profile.can_action_stage(10)))))

    if not user_can_action:
        return JsonResponse({"status": "error", "message": "عدم دسترسی اقدام: شما مجوز بارگذاری یا تغییر اسناد در مرحله جاری را ندارید."}, status=403)
    preview_url = request.POST.get("preview_url", "")
    uploaded_file = request.FILES.get("file")

    # Target folder: uploads/<national_id>/
    nat_id = str(dossier.national_id).strip() or "general"
    nat_id_dir = os.path.join(settings.MEDIA_ROOT, nat_id)
    os.makedirs(nat_id_dir, exist_ok=True)

    if uploaded_file:
        file_name = uploaded_file.name
        file_path = os.path.join(nat_id_dir, file_name)
        hasher = hashlib.sha256()
        with open(file_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                hasher.update(chunk)
                f.write(chunk)
        file_hash = "SHA256: " + hasher.hexdigest()[:24]
        saved_url = f"/uploads/{nat_id}/{file_name}"
    else:
        file_name = f"scan_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = os.path.join(nat_id_dir, file_name)
        saved_url = f"/uploads/{nat_id}/{file_name}"
        if preview_url and preview_url.startswith("data:"):
            try:
                import base64
                _, encoded = preview_url.split(",", 1)
                file_bytes = base64.b64decode(encoded)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                file_hash = "SHA256: " + hashlib.sha256(file_bytes).hexdigest()[:24]
            except Exception:
                file_hash = "SHA256: " + hashlib.sha256(f"{file_name}-{timezone.now().isoformat()}".encode()).hexdigest()[:24]
        else:
            file_hash = "SHA256: " + hashlib.sha256(f"{file_name}-{timezone.now().isoformat()}".encode()).hexdigest()[:24]

    # Dynamic Actor Attribution
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        uploader_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
        uploader_role = profile.role_title if profile and profile.role_title else dossier.current_role
    else:
        uploader_name = f"کارشناس مرحله {dossier.current_stage}"
        uploader_role = dossier.current_role

    attachment = DossierAttachment.objects.create(
        dossier=dossier,
        stage=dossier.current_stage,
        doc_type=doc_type,
        title=title,
        file_name=file_name,
        file_sha256=file_hash,
        uploaded_by=uploader_name,
        preview_url=saved_url
    )

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {dossier.current_stage}",
        to_stage=f"مرحله {dossier.current_stage}",
        actor=uploader_name,
        role=uploader_role,
        action="SUBMIT",
        action_label=f"بارگذاری سند: {title}",
        signature_hash=file_hash,
        notes=f"سند «{title}» با موفقیت اسکن و در پوشه اختصاصی کد ملی {nat_id} ذخیره گردید."
    )

    data = {
        "status": "success",
        "attachment": {
            "id": attachment.id,
            "stage": attachment.stage,
            "type": attachment.doc_type,
            "doc_type": attachment.doc_type,
            "title": attachment.title,
            "fileName": attachment.file_name,
            "uploader": attachment.uploaded_by,
            "uploadDate": timezone.now().strftime("%Y/%m/%d %H:%M"),
            "sha256": attachment.file_sha256,
            "preview_url": attachment.preview_url,
            "immutable": True
        }
    }
    return JsonResponse(data)


@csrf_exempt
def delete_scan_attachment_view(request, pk, attachment_id):
    """
    Deletes an attachment from the dossier and physically removes the file from disk if present.
    Authorized for housing chief, admin, uploader, or experts assigned to this stage.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و بایگانی شده است و امکان حذف اسناد وجود ندارد."}, status=400)

    attachment = get_object_or_404(DossierAttachment, id=attachment_id, dossier=dossier)
    doc_type = attachment.doc_type

    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    is_chief_or_admin = request.user.is_superuser or (profile and (profile.is_housing_chief or profile.organization == 'system' or profile.allowed_stages == 'all'))
    user_can_action = is_chief_or_admin or (profile and (profile.can_action_stage(dossier.current_stage) or (doc_type == "FORM_J" and (profile.can_action_stage(3) or profile.can_action_stage(10)))))

    if not user_can_action:
        return JsonResponse({"status": "error", "message": "شما مجوز حذف مدارک در این پرونده را ندارید."}, status=403)

    # Physical file cleanup if inside MEDIA_ROOT
    if attachment.preview_url and attachment.preview_url.startswith("/uploads/"):
        rel_path = attachment.preview_url[len("/uploads/"):].lstrip("/")
        file_disk_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        if os.path.exists(file_disk_path) and os.path.isfile(file_disk_path):
            try:
                os.remove(file_disk_path)
            except Exception:
                pass

    att_title = attachment.title
    att_id = attachment.id
    attachment.delete()

    actor_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username if request.user.is_authenticated else "کاربر سامانه")
    actor_role = profile.role_title if profile and profile.role_title else dossier.current_role

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {dossier.current_stage}",
        to_stage=f"مرحله {dossier.current_stage}",
        actor=actor_name,
        role=actor_role,
        action="DELETE",
        action_label=f"حذف مدرک: {att_title}",
        notes=f"مدرک پیوست «{att_title}» (شناسه {att_id}) از پرونده حذف گردید."
    )

    return JsonResponse({"status": "success", "message": f"مدرک «{att_title}» با موفقیت حذف گردید.", "attachment_id": att_id})


# --------------------------------------------------------------------------------------------------
# Enterprise Authentication & Profile Views
# --------------------------------------------------------------------------------------------------

def user_login_view(request):
    """
    Renders login view with branded UI and authenticates staff/experts.
    """
    if request.user.is_authenticated:
        return redirect("dossier_list")

    error = None
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                profile = getattr(user, 'profile', None)
                if profile and profile.must_change_password:
                    return redirect("first_login_setup")
                display_name = profile.full_name if profile and profile.full_name else user.username
                messages.success(request, f"خوش آمدید، {display_name}.")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect("dossier_list")
            else:
                error = "حساب کاربری شما غیرفعال شده است. لطفاً با مدیر سیستم تماس بگیرید."
        else:
            error = "نام کاربری یا کلمه عبور وارد شده نامعتبر است."

    return render(request, "auth/login.html", {"error": error, "next": next_url})


def user_logout_view(request):
    """
    Terminates authenticated session and safely redirects to login page.
    """
    logout(request)
    messages.info(request, "شما با موفقیت از سامانه خارج شدید.")
    return redirect("login")


@login_required(login_url='login')
def user_profile_view(request):
    """
    Displays current user information, organizational credentials, and password management.
    """
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "change_password":
            old_password = request.POST.get("old_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            if not request.user.check_password(old_password):
                messages.error(request, "کلمه عبور فعلی نادرست وارد شده است.")
            elif new_password != confirm_password:
                messages.error(request, "تکرار کلمه عبور جدید مطابقت ندارد.")
            elif len(new_password) < 6:
                messages.error(request, "کلمه عبور جدید باید حداقل ۶ کاراکتر باشد.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "کلمه عبور حساب کاربری شما با موفقیت بروزرسانی گردید.")
                return redirect("user_profile")
        elif action == "update_signature":
            sig_file = request.FILES.get("signature_image")
            if sig_file:
                profile = getattr(request.user, 'profile', None)
                if profile:
                    try:
                        from PIL import Image
                        from io import BytesIO
                        from django.core.files.uploadedfile import InMemoryUploadedFile

                        img = Image.open(sig_file).convert("RGBA")
                        w, h = img.size
                        min_side = min(w, h)
                        left = (w - min_side) // 2
                        top = (h - min_side) // 2
                        cropped = img.crop((left, top, left + min_side, top + min_side)).resize((320, 320), Image.Resampling.LANCZOS)

                        buf = BytesIO()
                        cropped.save(buf, format="PNG")
                        buf.seek(0)

                        processed_file = InMemoryUploadedFile(
                            buf, None, f"sig_{request.user.id}_{int(timezone.now().timestamp())}.png",
                            'image/png', buf.getbuffer().nbytes, None
                        )
                        profile.signature_image = processed_file
                        profile.save()
                        messages.success(request, "تصویر امضای الکترونیکی با نسبت استاندارد ۱:۱ ذخیره و بهینه‌سازی شد.")
                    except Exception:
                        profile.signature_image = sig_file
                        profile.save()
                        messages.success(request, "تصویر امضای الکترونیکی شما با موفقیت بروزرسانی شد.")
            else:
                messages.error(request, "لطفاً یک فایل تصویر امضا انتخاب فرمایید.")
            return redirect("user_profile")

    return render(request, "auth/profile.html", {"user": request.user})


@login_required(login_url='login')
def first_login_setup_view(request):
    """
    Mandatory security onboarding screen for users on initial login:
    Forces setting a private password and uploading or drawing their official signature picture.
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.must_change_password:
        return redirect("dossier_list")

    error = None
    if request.method == "POST":
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        sig_file = request.FILES.get("signature_image")
        canvas_sig = request.POST.get("canvas_signature_data", "").strip()

        if len(new_password) < 6:
            error = "کلمه عبور جدید باید حداقل ۶ کاراکتر باشد."
        elif new_password != confirm_password:
            error = "کلمه عبور جدید با تکرار آن یکسان نیست."
        elif not sig_file and not canvas_sig:
            error = "بارگذاری یا ترسیم تصویر نمونه امضای الکترونیک الزامی است."
        else:
            if sig_file:
                profile.signature_image = sig_file
            elif canvas_sig and "," in canvas_sig:
                import base64
                from django.core.files.base import ContentFile
                try:
                    format_part, imgstr = canvas_sig.split(';base64,')
                    ext = format_part.split('/')[-1]
                    data = ContentFile(base64.b64decode(imgstr), name=f"sig_{request.user.username}.{ext}")
                    profile.signature_image = data
                except Exception as e:
                    error = f"خطا در پردازش تصویر امضا: {str(e)}"

            if not error:
                request.user.set_password(new_password)
                request.user.save()
                profile.must_change_password = False
                profile.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "کلمه عبور امنیتی و تصویر نمونه امضای دیجیتال شما با موفقیت ثبت و تایید گردید.")
                return redirect("dossier_list")

    return render(request, "auth/first_login_setup.html", {"error": error})


# --------------------------------------------------------------------------------------------------
# Staff & User Management Administration Views
# --------------------------------------------------------------------------------------------------

@login_required(login_url='login')
def users_management_view(request):
    """
    Admin control panel to manage registered experts, review access rights, and assign stages.
    Accessible to Superadmin, Staff, and Housing Chief (رئیس مسکن).
    """
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_staff or request.user.is_superuser or (profile and profile.is_housing_chief)):
        messages.error(request, "دسترسی به بخش مدیریت کاربران نیازمند مجوز مدیر سیستم یا رئیس مسکن است.")
        return redirect("dossier_list")

    users = User.objects.all().select_related("profile").order_by("id")
    count_brokerage = 0
    count_directorate = 0
    count_system = 0
    count_chief = 0

    all_stages_meta = [
        {"id": i, "title": role_tuple[2], "role": role_tuple[1], "unit": role_tuple[0]}
        for i, role_tuple in HousingDossier.STAGE_ROLES.items()
    ]

    users_data = []
    for u in users:
        p = getattr(u, 'profile', None)
        org = p.organization if p else "brokerage"
        if org == "brokerage":
            count_brokerage += 1
        elif org == "directorate":
            count_directorate += 1
        else:
            count_system += 1

        is_chief = bool(p and p.is_housing_chief)
        if is_chief:
            count_chief += 1

        allowed_raw = p.allowed_stages if p else "all"
        if allowed_raw == "all" or is_chief or u.is_superuser:
            parsed_stages = "all"
            stage_pills = [{"id": "all", "title": "کلیه ۲۱ مرحله (اختیارات تام)"}]
        else:
            nums = [int(s.strip()) for s in allowed_raw.split(',') if s.strip().isdigit()]
            stage_pills = [{"id": s, "title": f"مرحله {s}: {HousingDossier.STAGE_ROLES.get(s, ('','',f'مرحله {s}'))[2]}"} for s in nums]
            parsed_stages = ",".join(str(s) for s in nums)

        users_data.append({
            "id": u.id,
            "username": u.username,
            "full_name": p.full_name if p and p.full_name else u.username,
            "organization": org,
            "role_title": p.role_title if p and p.role_title else "کارشناس اقدام‌کننده",
            "personnel_code": p.personnel_code if p else "",
            "phone_number": p.phone_number if p else "",
            "national_id": p.national_id if p else "",
            "can_sign": p.can_sign if p else True,
            "is_housing_chief": is_chief,
            "is_superuser": u.is_superuser,
            "is_active": u.is_active,
            "allowed_stages": allowed_raw,
            "parsed_stages": parsed_stages,
            "stage_pills": stage_pills,
        })

    # Calculate stage coverage for control by stage
    stage_experts_count = {i: 0 for i in range(1, 22)}
    for ud in users_data:
        raw = ud.get("allowed_stages", "")
        if raw == "all" or ud.get("is_housing_chief") or ud.get("is_superuser"):
            for i in range(1, 22):
                stage_experts_count[i] += 1
        else:
            nums = [int(s.strip()) for s in raw.split(',') if s.strip().isdigit()]
            for s in nums:
                if 1 <= s <= 21:
                    stage_experts_count[s] += 1

    for stg in all_stages_meta:
        stg["experts_count"] = stage_experts_count.get(stg["id"], 0)

    context = {
        "users": users,
        "users_data": users_data,
        "users_json": json.dumps(users_data, ensure_ascii=False),
        "all_stages_meta": all_stages_meta,
        "count_brokerage": count_brokerage,
        "count_directorate": count_directorate,
        "count_system": count_system,
        "count_chief": count_chief,
    }
    return render(request, "admin/users_manage.html", context)


@login_required(login_url='login')
def edit_user_action(request, user_id):
    """
    Updates profile, organization, roles, housing chief status, and allowed stages for a user.
    Accessible to Superadmin, Staff, and Housing Chief.
    """
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_staff or request.user.is_superuser or (profile and profile.is_housing_chief)):
        return HttpResponseBadRequest("مجوز غیرمجاز")

    if request.method == "POST":
        target_user = get_object_or_404(User, id=user_id)
        target_profile, _ = UserProfile.objects.get_or_create(user=target_user)

        full_name = request.POST.get("full_name", "").strip()
        role_title = request.POST.get("role_title", "").strip()
        organization = request.POST.get("organization", "brokerage").strip()
        personnel_code = request.POST.get("personnel_code", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        national_id = request.POST.get("national_id", "").strip()
        is_housing_chief = bool(request.POST.get("is_housing_chief"))
        can_sign = bool(request.POST.get("can_sign"))
        is_active = bool(request.POST.get("is_active"))

        stages_selected = request.POST.getlist("stages_selected")
        stages_text = request.POST.get("allowed_stages", "").strip()

        if is_housing_chief:
            allowed_stages = "all"
            target_user.is_staff = True
        elif stages_selected:
            if "all" in stages_selected:
                allowed_stages = "all"
            else:
                try:
                    sorted_stages = sorted([int(s) for s in stages_selected if s.isdigit()])
                    allowed_stages = ",".join(str(s) for s in sorted_stages)
                except Exception:
                    allowed_stages = ",".join(stages_selected)
        elif stages_text:
            allowed_stages = stages_text
        else:
            allowed_stages = "0"

        if organization == "system":
            target_user.is_staff = True

        if full_name:
            target_profile.full_name = full_name
        target_profile.role_title = role_title or "کارشناس اقدام‌کننده"
        target_profile.organization = organization
        target_profile.personnel_code = personnel_code
        target_profile.phone_number = phone_number
        target_profile.national_id = national_id
        target_profile.is_housing_chief = is_housing_chief
        target_profile.allowed_stages = allowed_stages
        target_profile.can_sign = can_sign
        target_profile.save()

        # Update user active status (prevent deactivating own account)
        if target_user != request.user:
            target_user.is_active = is_active
        target_user.save()

        messages.success(request, f"دسترسی‌ها، مراحل و مشخصات کاربر «{target_user.username}» با موفقیت بروزرسانی شد.")

    return redirect("users_management")


@login_required(login_url='login')
def create_user_action(request):
    """
    Creates a new expert / staff user account and associated UserProfile with specific stage permissions.
    """
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_staff or request.user.is_superuser or (profile and profile.is_housing_chief)):
        return HttpResponseBadRequest("مجوز غیرمجاز")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        full_name = request.POST.get("full_name", "").strip()
        organization = request.POST.get("organization", "brokerage").strip()
        role_title = request.POST.get("role_title", "").strip()
        personnel_code = request.POST.get("personnel_code", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        can_sign = bool(request.POST.get("can_sign"))
        is_housing_chief = bool(request.POST.get("is_housing_chief"))
        
        stages_selected = request.POST.getlist("stages_selected")
        stages_text = request.POST.get("allowed_stages", "").strip()

        if is_housing_chief:
            allowed_stages = "all"
        elif stages_selected:
            if "all" in stages_selected:
                allowed_stages = "all"
            else:
                try:
                    sorted_stages = sorted([int(s) for s in stages_selected if s.isdigit()])
                    allowed_stages = ",".join(str(s) for s in sorted_stages)
                except Exception:
                    allowed_stages = ",".join(stages_selected)
        elif stages_text:
            allowed_stages = stages_text
        else:
            allowed_stages = "0"

        if not username or not password or not full_name:
            messages.error(request, "تکمیل نام کاربری، کلمه عبور و نام کامل الزامی است.")
            return redirect("users_management")

        if User.objects.filter(username=username).exists():
            messages.error(request, f"نام کاربری «{username}» قبلاً در سامانه ثبت شده است.")
            return redirect("users_management")

        is_staff = (organization == "system" or is_housing_chief)
        new_user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=is_staff
        )
        user_prof, _ = UserProfile.objects.get_or_create(user=new_user)
        user_prof.full_name = full_name
        user_prof.organization = organization
        user_prof.role_title = role_title or "کارشناس"
        user_prof.personnel_code = personnel_code
        user_prof.phone_number = phone_number
        user_prof.can_sign = can_sign
        user_prof.is_housing_chief = is_housing_chief
        user_prof.allowed_stages = allowed_stages if not is_housing_chief else "all"
        user_prof.is_active_expert = True
        user_prof.save()
        messages.success(request, f"کارشناس جدید «{full_name}» با نام کاربری «{username}» با موفقیت افزوده شد.")

    return redirect("users_management")


@login_required(login_url='login')
def toggle_user_status_action(request, user_id):
    """
    Toggles is_active flag for the specified user account.
    """
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_staff or request.user.is_superuser or (profile and profile.is_housing_chief)):
        return HttpResponseBadRequest("مجوز غیرمجاز")

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.warning(request, "امکان غیرفعال‌سازی حساب کاربری جاری خودتان وجود ندارد.")
    else:
        target_user.is_active = not target_user.is_active
        target_user.save()
        st_text = "فعال" if target_user.is_active else "غیرفعال"
        messages.success(request, f"وضعیت حساب کاربر «{target_user.username}» به «{st_text}» تغییر یافت.")

    return redirect("users_management")


@login_required(login_url='login')
def reset_user_password_action(request, user_id):
    """
    Resets the password for a selected user account.
    """
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_staff or request.user.is_superuser or (profile and profile.is_housing_chief)):
        return HttpResponseBadRequest("مجوز غیرمجاز")

    target_user = get_object_or_404(User, id=user_id)
    new_pw = request.POST.get("new_password", "").strip()
    if len(new_pw) < 6:
        messages.error(request, "کلمه عبور جدید باید حداقل ۶ کاراکتر باشد.")
    else:
        target_user.set_password(new_pw)
        target_user.save()
        messages.success(request, f"کلمه عبور کاربر «{target_user.username}» با موفقیت بازنشانی شد.")

    return redirect("users_management")


@login_required(login_url='login')
def audit_logs_view(request):
    """
    Comprehensive System Audit Deck for Super Admin and Housing Chief (رئیس مسکن).
    Displays exhaustive historical logging of all field alterations and electronic signatures across all dossiers.
    """
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (profile and profile.can_view_all_audit_logs())):
        messages.error(request, "مشاهده سیاهه جامع ممیزی مختص مدیر ارشد سامانه و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")

    query = request.GET.get("q", "").strip()
    archive_num = request.GET.get("archive_number", "").strip()

    field_changes = DossierFieldChangeLog.objects.select_related("dossier").order_by("-timestamp")
    signature_logs = WorkflowSignatureLog.objects.select_related("dossier").order_by("-timestamp")

    if archive_num:
        try:
            num = int(archive_num)
            field_changes = field_changes.filter(dossier__archive_number=num)
            signature_logs = signature_logs.filter(dossier__archive_number=num)
        except ValueError:
            pass

    if query:
        field_changes = field_changes.filter(
            models.Q(field_name__icontains=query) |
            models.Q(field_label__icontains=query) |
            models.Q(changed_by__icontains=query) |
            models.Q(old_value__icontains=query) |
            models.Q(new_value__icontains=query)
        )
        signature_logs = signature_logs.filter(
            models.Q(actor__icontains=query) |
            models.Q(action_label__icontains=query) |
            models.Q(notes__icontains=query)
        )

    context = {
        "field_changes": field_changes[:500],
        "signature_logs": signature_logs[:500],
        "total_field_changes": field_changes.count(),
        "total_signature_logs": signature_logs.count(),
        "query": query,
        "archive_number": archive_num,
    }
    return render(request, "admin/audit_logs.html", context)


# =========================================================================
# Excel Bulk Import & Update Management Views (Admin Only)
# =========================================================================

def _check_admin_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, 'profile', None)
    if profile and (profile.is_housing_chief or profile.role == "SYSTEM_ADMIN" or profile.allowed_stages == "ALL"):
        return True
    return False

@login_required
def excel_template_create_view(request):
    """Download Excel template for adding new dossiers."""
    if not _check_admin_access(request.user):
        messages.error(request, "دسترسی غیرمجاز: این قابلیت صرفاً مختص مدیر ارشد سامانه و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")
    from .excel_service import generate_create_template
    return generate_create_template()

@login_required
def excel_template_update_view(request):
    """Download Excel template for bulk-updating existing dossiers by national_id."""
    if not _check_admin_access(request.user):
        messages.error(request, "دسترسی غیرمجاز: این قابلیت صرفاً مختص مدیر ارشد سامانه و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")
    from .excel_service import generate_update_template
    return generate_update_template()

@login_required
def excel_upload_create_view(request):
    """Upload Excel file to create new dossiers."""
    if not _check_admin_access(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز: مختص مدیر ارشد سامانه و رئیس مسکن."}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "متد غیرمجاز است."}, status=405)
    
    excel_file = request.FILES.get("file")
    if not excel_file:
        return JsonResponse({"success": False, "error": "هیچ فایل اکسلی ارسال نشده است."}, status=400)
    
    is_preview = request.POST.get("preview") in ["true", "1", True]
    try:
        from .excel_service import process_create_excel
        res = process_create_excel(excel_file, user=request.user, is_preview=is_preview)
        return JsonResponse(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": f"خطا در ایجاد پرونده‌ها از اکسل: {str(e)}"}, status=500)

@login_required
def excel_upload_update_view(request):
    """Upload Excel file to bulk-update dossiers matched by national_id."""
    if not _check_admin_access(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز: مختص مدیر ارشد سامانه و رئیس مسکن."}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "متد غیرمجاز است."}, status=405)
    
    excel_file = request.FILES.get("file")
    if not excel_file:
        return JsonResponse({"success": False, "error": "هیچ فایل اکسلی ارسال نشده است."}, status=400)
    
    is_preview = request.POST.get("preview") in ["true", "1", True]
    try:
        from .excel_service import process_update_excel
        res = process_update_excel(excel_file, user=request.user, is_preview=is_preview)
        return JsonResponse(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": f"خطا در پردازش فایل بروزرسانی اکسل: {str(e)}"}, status=500)



@login_required
def excel_export_all_view(request):
    """Export all dossiers (with optional search query/stage filter) to comprehensive Excel."""
    if not _check_admin_access(request.user):
        messages.error(request, "دسترسی غیرمجاز: این قابلیت صرفاً مختص مدیر ارشد سامانه و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")

    from .excel_service import generate_dossiers_export
    from django.db.models import Q

    query = request.GET.get("q", "").strip()
    stage_val = request.GET.get("stage", "").strip()

    qs = HousingDossier.objects.all().order_by("-archive_number")
    if query:
        q_filter = (
            Q(national_id__icontains=query)
            | Q(full_name__icontains=query)
            | Q(spouse_national_id__icontains=query)
            | Q(spouse_full_name__icontains=query)
            | Q(project__icontains=query)
            | Q(site__icontains=query)
            | Q(block_name__icontains=query)
            | Q(applicant_phone__icontains=query)
        )
        if query.isdigit():
            q_filter |= Q(archive_number=int(query))
        qs = qs.filter(q_filter)

    if stage_val and stage_val.isdigit():
        qs = qs.filter(current_stage=int(stage_val))

    return generate_dossiers_export(qs)

@csrf_exempt
@login_required(login_url='login')
def upload_dossier_signature_view(request, pk):
    """
    Handles uploading a signature/stamp image for one of the 14 official archival signature slots.
    Enforces role/stage permission matrix: users can only upload for slots related to them.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    profile = getattr(request.user, 'profile', None)
    is_chief_or_admin = request.user.is_superuser or (profile and profile.is_housing_chief)
    if dossier.is_locked and not is_chief_or_admin:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و بایگانی قطعی شده است و تغییرات در آن مسدود می‌باشد."}, status=400)

    slot_key = request.POST.get("slot_key", "").strip()
    if slot_key not in SLOT_TITLES:
        return JsonResponse({"status": "error", "message": f"جایگاه امضای «{slot_key}» نامعتبر است."}, status=400)

    # Permission check: user can only upload signature for what is related to them (or admin/chief)
    if not can_user_upload_signature(request.user, slot_key):
        return JsonResponse({
            "status": "error",
            "message": f"شما دسترسی مجاز برای بارگذاری امضا در جایگاه «{SLOT_TITLES.get(slot_key)}» را ندارید."
        }, status=403)

    profile = getattr(request.user, 'profile', None)
    uploader_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
    signer_name = request.POST.get("signer_name", "").strip() or uploader_name
    signer_title = request.POST.get("signer_title", "").strip() or (profile.role_title if profile else "کارشناس مسئول")
    
    import jdatetime
    try:
        now_jalali = jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    except Exception:
        now_jalali = timezone.now().strftime("%Y/%m/%d %H:%M")
    
    signed_date = request.POST.get("signed_date", "").strip() or now_jalali

    uploaded_file = request.FILES.get("signature_file")
    signature_base64 = request.POST.get("signature_base64", "").strip()

    sig_obj, _ = DossierSignature.objects.get_or_create(dossier=dossier, slot_key=slot_key)
    sig_obj.signer_name = signer_name
    sig_obj.signer_title = signer_title
    sig_obj.signed_date = signed_date
    sig_obj.uploaded_by = uploader_name

    if uploaded_file:
        sig_obj.signature_image = uploaded_file
        sig_obj.save()
    elif signature_base64 and signature_base64.startswith("data:image"):
        try:
            import base64
            from django.core.files.base import ContentFile
            format_part, imgstr = signature_base64.split(';base64,')
            ext = format_part.split('/')[-1]
            data = base64.b64decode(imgstr)
            file_name = f"sig_{dossier.archive_number}_{slot_key}.{ext}"
            sig_obj.signature_image.save(file_name, ContentFile(data), save=True)
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"خطا در پردازش تصویر: {str(e)}"}, status=400)
    else:
        sig_obj.save()

    img_url = sig_obj.signature_image.url if sig_obj.signature_image else ""

    return JsonResponse({
        "status": "success",
        "message": f"امضای «{SLOT_TITLES.get(slot_key)}» با موفقیت ذخیره و در شناسنامه بایگانی درج گردید.",
        "slot_key": slot_key,
        "image_url": img_url,
        "signer_name": sig_obj.signer_name,
        "signed_date": sig_obj.signed_date
    })


# ==================================================================================================
# BANK LETTER SENDER COMPONENT (ارسال دسته جمعی نامه معرفی متقاضیان به بانک مسکن)
# ==================================================================================================

def split_persian_name(full_name):
    if not full_name:
        return ("", "")
    parts = full_name.strip().split()
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    if parts[0] in ["سید", "سیده", "میر", "حاج", "حاجیه"] and len(parts) >= 2:
        return (" ".join(parts[:2]), " ".join(parts[2:]))
    return (parts[0], " ".join(parts[1:]))

@login_required(login_url='login')
def bank_letter_sender_view(request):
    """
    Admin component to prepare, preview and send official Bank Introduction Letter batches.
    Displays the standard selection table exactly matching the official project unit sheet.
    Provides complete historical archive of all issued bank letters.
    """
    profile = getattr(request.user, 'profile', None)
    is_chief_or_admin = request.user.is_superuser or request.user.is_staff or (profile and profile.is_housing_chief)
    can_action_bank = profile and (profile.can_action_stage(6) or profile.can_action_stage(9))
    
    if not (is_chief_or_admin or can_action_bank):
        messages.error(request, "دسترسی به بخش ارسال نامه بانک نیازمند مجوز کارشناس بانک یا مدیر سیستم است.")
        return redirect("dossier_list")

    # All available dossiers
    all_dossiers = HousingDossier.objects.all().order_by("archive_number")
    
    # Projects for dropdown filter
    projects = list(HousingDossier.objects.exclude(project="").values_list("project", flat=True).distinct())

    # Default today Jalali date
    try:
        import jdatetime
        today_jalali = jdatetime.date.today().strftime("%Y/%m/%d")
    except Exception:
        today_jalali = timezone.now().strftime("%Y/%m/%d")

    # Sync any sent dossiers into BankLetter if not already present
    sent_dossiers = HousingDossier.objects.filter(is_sent_to_bank=True).exclude(bank_letter_number="")
    for d in sent_dossiers:
        num = (d.bank_letter_number or d.bank_sent_letter_number or "").strip()
        if num:
            bl_obj, _ = BankLetter.objects.get_or_create(
                letter_number=num,
                defaults={
                    "letter_date": d.bank_letter_date or d.bank_sent_date or today_jalali,
                    "project_name": d.project or "پروژه مسکونی",
                    "sender_name": "کارشناس تسهیلات بانکی",
                    "sender_role": "واحد تسهیلات و بانک مسکن",
                }
            )
            if not bl_obj.dossiers.filter(id=d.id).exists():
                bl_obj.dossiers.add(d)

    # Fetch Letter History
    letters_qs = BankLetter.objects.all().prefetch_related("dossiers").order_by("-created_at", "-id")
    letter_history_list = []
    for l in letters_qs:
        d_objs = list(l.dossiers.all().order_by("archive_number"))
        try:
            import jdatetime
            dt_jalali = jdatetime.datetime.fromgregorian(datetime=l.created_at).strftime("%Y/%m/%d - %H:%M")
        except Exception:
            dt_jalali = l.created_at.strftime("%Y/%m/%d %H:%M") if l.created_at else ""

        letter_history_list.append({
            "id": l.id,
            "letter_number": l.letter_number,
            "letter_date": l.letter_date,
            "project_name": l.project_name or (d_objs[0].project if d_objs else "پروژه مسکونی"),
            "sender_name": l.sender_name or "کارشناس تسهیلات",
            "sender_role": l.sender_role or "واحد تسهیلات و بانک مسکن",
            "notes": l.notes or "",
            "created_at_jalali": dt_jalali,
            "dossier_count": len(d_objs),
            "dossier_archives": [d.archive_number for d in d_objs],
            "dossiers": [
                {
                    "archive_number": d.archive_number,
                    "full_name": d.full_name or "-",
                    "national_id": d.national_id or "-",
                    "block_code": d.block_code or d.block_name or "-",
                    "floor_number": d.floor_number or "-",
                    "unit_code": d.unit_code or d.unit_number or "-",
                    "total_area": str(d.total_area or "-"),
                    "applicant_phone": d.applicant_phone or "-",
                }
                for d in d_objs
            ]
        })

    # Serialize dossiers for Alpine.js store
    dossiers_json_list = []
    for d in all_dossiers:
        fn, ln = split_persian_name(d.full_name)
        dossiers_json_list.append({
            "id": d.id,
            "archive_number": d.archive_number,
            "national_id": d.national_id or "",
            "first_name": fn,
            "last_name": ln,
            "full_name": d.full_name or "",
            "selection_rank": d.selection_rank or "-",
            "applicant_phone": d.applicant_phone or "",
            "block_code": d.block_code or d.block_name or "-",
            "floor_number": d.floor_number or "-",
            "unit_code": d.unit_code or d.unit_number or "-",
            "covered_parking_area": str(d.covered_parking_area or "-"),
            "parking_number": str(d.parking_number or "-"),
            "storage_area": str(d.storage_area or "-"),
            "storage_number": str(d.storage_number or "-"),
            "bedroom_count": str(d.bedroom_count or "-"),
            "common_area": str(d.common_area or "-"),
            "net_unit_area": str(d.net_unit_area or "-"),
            "unit_direction": d.unit_direction or "-",
            "total_area": str(d.total_area or "-"),
            "project": d.project or "",
            "site": d.site or "",
            "current_stage": d.current_stage,
            "current_stage_title": d.current_stage_title,
            "is_sent_to_bank": d.is_sent_to_bank,
            "bank_letter_number": d.bank_letter_number or d.bank_sent_letter_number or "",
            "bank_letter_date": d.bank_letter_date or d.bank_sent_date or "",
        })

    initial_letter = request.GET.get("letter", "").strip()

    context = {
        "dossiers_json": json.dumps(dossiers_json_list, ensure_ascii=False),
        "letters_history_json": json.dumps(letter_history_list, ensure_ascii=False),
        "letters_count": len(letter_history_list),
        "projects": projects,
        "today_jalali": today_jalali,
        "default_project": projects[0] if projects else "پروژه ۲۸۵ واحدی فراگیر ملی سانیار آفرین ایرانیان",
        "initial_letter": initial_letter,
    }
    return render(request, "admin/bank_letter_sender.html", context)


@login_required(login_url='login')
def bank_letter_submit_api(request):
    """
    Processes the batch Bank Letter submission:
    Updates is_sent_to_bank, letter number and date, creates BankLetter archive entity,
    and advances Stage 11 dossiers to Stage 12.
    """
    profile = getattr(request.user, 'profile', None)
    is_chief_or_admin = request.user.is_superuser or request.user.is_staff or (profile and profile.is_housing_chief)
    can_action_bank = profile and (profile.can_action_stage(6) or profile.can_action_stage(9))
    
    if not (is_chief_or_admin or can_action_bank):
        return JsonResponse({"status": "error", "message": "دسترسی غیرمجاز."}, status=403)

    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        body = request.POST

    archive_numbers = body.get("archive_numbers", [])
    letter_number = (body.get("letter_number") or "").strip()
    letter_date = (body.get("letter_date") or "").strip()
    notes = (body.get("notes") or "").strip()

    if not archive_numbers:
        return JsonResponse({"status": "error", "message": "هیچ پرونده‌ای انتخاب نشده است."}, status=400)
    if not letter_number:
        return JsonResponse({"status": "error", "message": "شماره نامه بانک الزامی است."}, status=400)
    if not letter_date:
        return JsonResponse({"status": "error", "message": "تاریخ نامه بانک الزامی است."}, status=400)

    # Normalize archive numbers list
    clean_archives = []
    for item in archive_numbers:
        try:
            clean_archives.append(int(str(item).strip()))
        except ValueError:
            continue

    dossiers = HousingDossier.objects.filter(archive_number__in=clean_archives)
    updated_count = 0
    updated_archives = []

    actor_name = profile.full_name if profile and profile.full_name else request.user.username
    actor_role = profile.role_title if profile and profile.role_title else "کارشناس تسهیلات بانکی"

    for d in dossiers:
        d.is_sent_to_bank = True
        d.bank_letter_number = letter_number
        d.bank_letter_date = letter_date
        d.bank_sent_letter_number = letter_number
        d.bank_sent_date = letter_date
        d.is_added_to_bank_shipment_list = True
        d.bank_shipment_list_added_at = timezone.now()

        from_stage_str = f"مرحله {d.current_stage}: {d.current_stage_title}"
        if d.current_stage == 6:
            d.current_stage = 7
            to_stage_str = f"مرحله ۷: {d.current_stage_title}"
        else:
            to_stage_str = f"مرحله {d.current_stage}: {d.current_stage_title}"

        d.save()
        updated_count += 1
        updated_archives.append(d.archive_number)

        # Log audit trail
        WorkflowSignatureLog.objects.create(
            dossier=d,
            from_stage=from_stage_str,
            to_stage=to_stage_str,
            actor=actor_name,
            role=actor_role,
            action="BANK_LETTER",
            action_label="ارسال نامه معرفی به بانک",
            notes=f"نامه معرفی به بانک صادره به شماره {letter_number} مورخ {letter_date}. {notes}".strip(),
            signature_hash=f"BANK-LETTER-{d.archive_number}-{letter_number}"
        )

    # Record or update BankLetter archive entity
    project_title = dossiers.first().project if dossiers.exists() and dossiers.first().project else "پروژه مسکونی"
    bank_letter, created = BankLetter.objects.get_or_create(
        letter_number=letter_number,
        defaults={
            "letter_date": letter_date,
            "project_name": project_title,
            "sender_user": request.user,
            "sender_name": actor_name,
            "sender_role": actor_role,
            "notes": notes,
        }
    )
    bank_letter.letter_date = letter_date
    if notes:
        bank_letter.notes = notes
    bank_letter.sender_name = actor_name
    bank_letter.sender_role = actor_role
    bank_letter.dossiers.add(*dossiers)
    bank_letter.save()

    return JsonResponse({
        "status": "success",
        "message": f"نامه بانک با شماره {letter_number} برای {updated_count} پرونده با موفقیت ثبت و وضعیت پرونده‌ها به‌روزرسانی شد.",
        "updated_count": updated_count,
        "updated_archives": updated_archives,
        "letter_number": letter_number,
        "letter_date": letter_date,
        "letter_id": bank_letter.id
    })


@login_required(login_url='login')
def bank_letter_export_excel(request):
    """
    Exports the Bank Introduction Letter table to Excel (.xlsx) exactly matching the official project sheet format.
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from django.http import HttpResponse

    archive_str = request.GET.get("archives", "")
    project_title = request.GET.get("project", "پروژه ۲۸۵ واحدی فراگیر ملی سانیار آفرین ایرانیان")
    letter_number = request.GET.get("letter", "").strip()
    letter_date = request.GET.get("date", "").strip()

    if archive_str:
        arch_list = [int(a.strip()) for a in archive_str.split(",") if a.strip().isdigit()]
        dossiers = HousingDossier.objects.filter(archive_number__in=arch_list).order_by("archive_number")
    elif letter_number:
        dossiers = HousingDossier.objects.filter(bank_letter_number=letter_number).order_by("archive_number")
    else:
        dossiers = HousingDossier.objects.all().order_by("archive_number")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "نامه بانک"
    ws.views.sheetView[0].rightToLeft = True

    # Title Banner (Row 1)
    sheet_title = f"محاسبه قیمت تمام شده انتخاب واحد پروژه {project_title}"
    if letter_number:
        sheet_title += f" (نامه رسمی بانک: {letter_number} مورخ {letter_date})"

    ws.merge_cells("A1:R1")
    title_cell = ws["A1"]
    title_cell.value = sheet_title
    title_cell.font = Font(name="Tahoma", size=13, bold=True, color="000000")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    title_cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    ws.row_dimensions[1].height = 36

    # Header Row (Row 2) - Exact 18 columns from image
    headers = [
        "ردیف", "نام", "نام خانوادگی", "رتبه", "کدملی", "شماره تماس",
        "کد بلوک", "طبقه", "کدواحد", "متراژ پارکینگ مسقف", "شماره پارکینگ",
        "متراژ انباری", "شماره انباری", "تعداد خواب", "مشاعات", "متراژ مفید",
        "جهت", "جمع متراژ"
    ]

    thin_border = Border(
        left=Side(style='thin', color='475569'),
        right=Side(style='thin', color='475569'),
        top=Side(style='thin', color='475569'),
        bottom=Side(style='thin', color='475569')
    )

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=h)
        cell.font = Font(name="Tahoma", size=10, bold=True, color="000000")
        cell.fill = PatternFill(start_color="CBD5E1", end_color="CBD5E1", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    ws.row_dimensions[2].height = 28

    # Data Rows
    row_idx = 3
    for idx, d in enumerate(dossiers, 1):
        fn, ln = split_persian_name(d.full_name)
        row_vals = [
            idx,
            fn or d.full_name,
            ln,
            d.selection_rank or "",
            d.national_id or "",
            d.applicant_phone or "",
            d.block_code or d.block_name or "",
            d.floor_number or "",
            d.unit_code or d.unit_number or "",
            float(d.covered_parking_area) if d.covered_parking_area else "",
            d.parking_number or "",
            float(d.storage_area) if d.storage_area else "",
            d.storage_number or "",
            d.bedroom_count or "",
            float(d.common_area) if d.common_area else "",
            float(d.net_unit_area) if d.net_unit_area else "",
            d.unit_direction or "",
            float(d.total_area) if d.total_area else "",
        ]

        for col_idx, val in enumerate(row_vals, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="Tahoma", size=9)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        ws.row_dimensions[row_idx].height = 22
        row_idx += 1

    # Column widths
    col_widths = [8, 14, 18, 10, 16, 16, 12, 8, 10, 16, 14, 14, 14, 12, 12, 12, 14, 14]
    for idx, width in enumerate(col_widths, 1):
        col_letter = openpyxl.utils.get_column_letter(idx)
        ws.column_dimensions[col_letter].width = width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"Bank_Letter_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response
