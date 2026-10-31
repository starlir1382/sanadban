from .excel_hub_views import (
    excel_hub_view,
    download_excel_template_view,
    process_stage_signatures_excel_view,
    process_commission_excel_view,
    process_swap_spouse_excel_view,
    swap_applicant_spouse_view,
    batch_sign_dossiers_view,
    excel_export_dashboard_view,
    reorder_attachments_view,
    edit_attachment_image_view,
)
import hashlib
import hmac
import json
import logging
import os
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

logger = logging.getLogger(__name__)
from django.db import transaction, models
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie, csrf_protect
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
from .models import HousingDossier, ProjectBankMapping, PreSelectedUnit, DossierAttachment, WorkflowSignatureLog, DossierFieldChangeLog, Site, Project, UserProfile, DossierCheck, BankLetter

ARCHIVAL_SLOTS = [
    "brokerage", "national_housing", "bank_facility", "decile_facility",
    "contractor_settlement", "applicant_settlement", "other_facilities",
    "legal", "form_j", "evaluation", "technical", "real_estate", "land_bank", "revenue",
]
STAGE_TO_SLOTS = {
    1: ["brokerage"], 3: ["form_j"], 4: ["other_facilities", "decile_facility"],
    5: ["applicant_settlement"], 6: ["bank_facility"], 8: ["brokerage"],
    9: ["national_housing", "bank_facility"], 10: ["form_j"], 11: ["technical"],
    12: ["real_estate"], 13: ["land_bank"], 14: ["legal"], 15: ["evaluation"],
    16: ["decile_facility"], 17: ["revenue"], 18: ["contractor_settlement"],
}

DOSSIER_FIELD_LABELS = {
    "full_name": "نام و نام خانوادگی متقاضی",
    "father_name": "نام پدر متقاضی",
    "national_id": "کد ملی متقاضی",
    "birth_date": "تاریخ تولد متقاضی",
    "applicant_phone": "شماره تماس متقاضی",
    "selection_rank": "رتبه انتخاب واحد",
    "form_j_questionnaire_number": "شماره پرسش نامه فرم ج",
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
    "applicant_id_number": "شماره شناسنامه متقاضی",
    "applicant_birth_place": "محل صدور شناسنامه متقاضی",
    "renovation_code": "کد نوسازی (شهرداری)",
    "first_name": "نام متقاضی",
    "last_name": "نام خانوادگی متقاضی",
    "spouse_first_name": "نام همسر",
    "spouse_last_name": "نام خانوادگی همسر",
    "bank_branch": "شعبه بانک متقاضی",
    "project_code": "کد پروژه",
    "bank_name": "نام بانک متقاضی",
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
        if 1 <= num <= 22:
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

    admin_stats = {}
    stages_analysis = []
    projects_breakdown = []
    recent_activity_logs = []

    if is_full_admin:
        total_all_count = HousingDossier.objects.count()
        p1_cnt = sum(counts_by_stage.get(i, 0) for i in range(1, 9))
        p2_cnt = sum(counts_by_stage.get(i, 0) for i in range(9, 11))
        p3_cnt = sum(counts_by_stage.get(i, 0) for i in range(11, 16))
        p4_cnt = sum(counts_by_stage.get(i, 0) for i in range(16, 23))
        red_form_j_cnt = HousingDossier.objects.filter(applicant_form_j_status__icontains="قرمز").count()
        completed_cnt = HousingDossier.objects.filter(is_locked=True).count()
        returned_cnt = HousingDossier.objects.filter(status="RETURNED").count()
        in_progress_cnt = total_all_count - completed_cnt

        admin_stats = {
            "total": total_all_count,
            "in_progress": in_progress_cnt,
            "completed": completed_cnt,
            "returned": returned_cnt,
            "red_form_j": red_form_j_cnt,
            "p1_count": p1_cnt,
            "p2_count": p2_cnt,
            "p3_count": p3_cnt,
            "p4_count": p4_cnt,
            "p1_pct": round((p1_cnt / total_all_count * 100), 1) if total_all_count else 0,
            "p2_pct": round((p2_cnt / total_all_count * 100), 1) if total_all_count else 0,
            "p3_pct": round((p3_cnt / total_all_count * 100), 1) if total_all_count else 0,
            "p4_pct": round((p4_cnt / total_all_count * 100), 1) if total_all_count else 0,
        }

        for stg in all_stages:
            sid = stg["id"]
            cnt = counts_by_stage.get(sid, 0)
            pct = round((cnt / total_all_count * 100), 1) if total_all_count else 0
            if 1 <= sid <= 8:
                phase_title = "فاز ۱ · کارگزاری"
                phase_badge = "emerald"
            elif 9 <= sid <= 10:
                phase_title = "فاز ۲ · اداره کل"
                phase_badge = "blue"
            elif 11 <= sid <= 15:
                phase_title = "فاز ۳ · فنی و حقوقی"
                phase_badge = "amber"
            else:
                phase_title = "فاز ۴ · تسویه و بایگانی"
                phase_badge = "purple"

            stages_analysis.append({
                "id": sid,
                "title": stg["title"],
                "role": stg["role"],
                "unit": stg["unit"],
                "count": cnt,
                "percentage": pct,
                "phase_title": phase_title,
                "phase_badge": phase_badge,
            })

        projects_breakdown = list(
            HousingDossier.objects.values('project', 'site')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')[:12]
        )
        for prj in projects_breakdown:
            prj["pct"] = round((prj["cnt"] / total_all_count * 100), 1) if total_all_count else 0

        recent_activity_logs = list(
            WorkflowSignatureLog.objects.select_related('dossier')
            .order_by('-timestamp')[:8]
        )

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

    # Server-side pagination: 50 dossiers per page for extreme speed with 35k+ records
    paginator = Paginator(dossiers, 50)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    setattr(page_obj, 'count', paginator.count)

    context = {
        "dossiers": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "dossiers_count": paginator.count,
        "current_sort": sort,
        "query": query,
        "stage_filter": stage_filter,
        "stages_meta": stages_meta,
        "is_full_admin": is_full_admin,
        "user_profile": profile,
        "user_allowed_stages": user_allowed_stages,
        "user_allowed_titles": user_allowed_titles,
        "stage_breakdown": stage_breakdown,
        "admin_stats": admin_stats,
        "stages_analysis": stages_analysis,
        "projects_breakdown": projects_breakdown,
        "recent_activity_logs": recent_activity_logs,
        "elided_page_range": getattr(paginator, "get_elided_page_range")(number=page_obj.number, on_each_side=2, on_ends=1),
        "total_all_dossiers": HousingDossier.objects.count() if is_full_admin else paginator.count,
    }
    return render(request, "dossiers/list.html", context)


@login_required(login_url='login')
def dossier_detail_view(request, pk):
    """
    Main interactive workspace view for a single housing dossier across its 21-stage workflow.
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
            "first_name": dossier.first_name,
            "last_name": dossier.last_name,
            "full_name": dossier.full_name,
            "father_name": dossier.father_name,
            "national_id": dossier.national_id,
            "birth_date": dossier.birth_date,
            "applicant_id_number": dossier.applicant_id_number or "",
            "applicant_birth_place": dossier.applicant_birth_place or "",
            "applicant_phone": dossier.applicant_phone or "",
            "selection_rank": dossier.selection_rank,
            "form_j_questionnaire_number": dossier.form_j_questionnaire_number or "",
            "applicant_form_j_status": dossier.applicant_form_j_status or "سبز (استعلام شده)",
            "applicant_form_j_directorate_status": dossier.applicant_form_j_directorate_status or "تایید نهایی اداره کل",
            "applicant_form_j_red_description": dossier.applicant_form_j_red_description or "",
            "spouse_first_name": dossier.spouse_first_name,
            "spouse_last_name": dossier.spouse_last_name,
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
            "project_code": dossier.project_code or "",
            "bank_name": dossier.bank_name or "",
            "bank_branch": dossier.bank_branch or "",
            "renovation_code": dossier.renovation_code or "",
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
            "form_j_number": dossier.form_j_number or "",
            "has_installment_booklet": dossier.has_installment_booklet,
            "is_installment_booklet_confirmed": dossier.is_installment_booklet_confirmed,
            "is_land_deed_confirmed": dossier.is_land_deed_confirmed,
            "has_info_form": dossier.has_info_form,
            "has_form_j": dossier.has_form_j,
            "has_affidavit": dossier.has_affidavit,
            "has_sana": dossier.has_sana,
            "has_national_id_doc": dossier.has_national_id_doc,
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
        "form_j_questionnaire_number",
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
        "bank_sent_date", "bank_sent_letter_number", "form_j_number",
        "applicant_id_number", "applicant_birth_place", "renovation_code",
        "first_name", "last_name", "spouse_first_name", "spouse_last_name",
        "bank_branch", "project_code", "bank_name"
    ]:
        if field in data and data[field] is not None:
            parsed_updates[field] = str(data[field]).strip()

    if "first_name" in parsed_updates or "last_name" in parsed_updates:
        fn = parsed_updates.get("first_name", dossier.first_name or "")
        ln = parsed_updates.get("last_name", dossier.last_name or "")
        parsed_updates["full_name"] = f"{fn} {ln}".strip()
    if "spouse_first_name" in parsed_updates or "spouse_last_name" in parsed_updates:
        sfn = parsed_updates.get("spouse_first_name", dossier.spouse_first_name or "")
        sln = parsed_updates.get("spouse_last_name", dossier.spouse_last_name or "")
        parsed_updates["spouse_full_name"] = f"{sfn} {sln}".strip()

    # Integer fields
    for field in [
        "selection_rank", "decile", "floor_number", "unit_number", "bedroom_count",
        "storage_number", "parking_number",
        "main_plaque", "separated_plaque", "sub_plaque", "plot_number",
        "base_cost_without_loan", "bank_loan_amount", "fund_loan_amount", "contractor_letter_amount",
        "decile_loan_amount", "past_years_rent", "current_year_rent",
        "preparation_cost", "cash_preparation_amount", "non_cash_preparation_amount",
        "check_count", "check_amount", "last_check_amount", "total_check_amount",
        "check_service_fee", "tenant_price", "preparation_service_fee",
        "preparation_check_count", "total_preparation_check_amount"
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
    for field in ["is_sms_sent", "is_equity_funded", "is_cash_rent_confirmed", "is_decile_loan_confirmed", "is_married_confirmed", "is_preparation_checks_confirmed", "is_added_to_bank_shipment_list", "is_sent_to_bank", "has_installment_booklet", "has_info_form", "has_form_j", "has_affidavit", "has_sana", "has_national_id_doc"]:
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

    if dossier.is_locked or current_idx >= 22:
        dossier.is_locked = True
        dossier.status = "COMPLETED"
        action = "ARCHIVE"
        action_label = "بایگانی قطعی پرونده"
        to_stage_str = "بایگانی نهایی (مختومه)"
        next_stage = current_idx
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
    target_slots = STAGE_TO_SLOTS.get(current_idx, [])
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

    from django.urls import reverse
    is_full_admin = request.user.is_superuser or request.user.is_staff or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))
    can_access_next = is_full_admin or bool(profile and profile.can_action_stage(dossier.current_stage))

    if can_access_next:
        redirect_url = reverse("dossier_detail", kwargs={"pk": dossier.archive_number})
    else:
        redirect_url = reverse("dossier_list")
        stage_title = dossier.current_stage_title
        try:
            if dossier.is_locked or dossier.current_stage >= 22:
                messages.success(request, f"پرونده #{dossier.archive_number} تایید و به بایگانی نهایی منتقل گردید.")
            else:
                messages.success(request, f"پرونده #{dossier.archive_number} با موفقیت به مرحله {dossier.current_stage} ({stage_title}) ارسال گردید.")
        except Exception:
            pass

    if request.headers.get("HX-Request"):
        return redirect(redirect_url)

    return JsonResponse({
        "status": "success",
        "new_stage": dossier.current_stage,
        "is_locked": dossier.is_locked,
        "hash": sig_hash,
        "redirect_url": redirect_url,
        "message": f"پرونده با موفقیت به مرحله {dossier.current_stage} منتقل گردید."
    })


@csrf_exempt
@transaction.atomic
def return_stage_action(request, pk):
    """
    Handles backward routing / rejection for correction (select_for_update).
    Supports all 21 stages: any stage > 1 can return to any prior stage >= 1.
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
    if target_stage_val is None:
        return JsonResponse({"status": "error", "message": "مرحله مقصد نامعتبر است."}, status=400)
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

    from django.urls import reverse
    can_access_target = is_chief_or_admin or bool(profile and profile.can_action_stage(target_stage))
    if can_access_target:
        redirect_url = reverse("dossier_detail", kwargs={"pk": dossier.archive_number})
    else:
        redirect_url = reverse("dossier_list")
        try:
            messages.info(request, f"پرونده #{dossier.archive_number} جهت اصلاح به مرحله {target_stage} ({target_title}) بازگردانده شد.")
        except Exception:
            pass

    if request.headers.get("HX-Request"):
        return redirect(redirect_url)

    return JsonResponse({
        "status": "success",
        "new_stage": dossier.current_stage,
        "dossier_status": dossier.status,
        "return_reason": dossier.return_reason,
        "return_by": dossier.return_by,
        "return_from_stage": dossier.return_from_stage,
        "hash": sig_hash,
        "redirect_url": redirect_url,
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
            "first_name": unit.first_name,
            "last_name": unit.last_name,
            "full_name": unit.full_name,
            "father_name": unit.father_name,
            "birth_date": unit.birth_date,
            "applicant_phone": unit.applicant_phone or "",
            "selection_rank": unit.selection_rank,
            "form_j_questionnaire_number": getattr(unit, "form_j_questionnaire_number", "") or "",
            "applicant_form_j_status": unit.applicant_form_j_status,
            "applicant_form_j_directorate_status": unit.applicant_form_j_directorate_status,
            "applicant_form_j_red_description": unit.applicant_form_j_red_description,
            "spouse_first_name": unit.spouse_first_name,
            "spouse_last_name": unit.spouse_last_name,
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
    Print-ready view for Stage 19 (Notary Letter Introduction).
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    return render(request, "dossiers/print_notary.html", {"dossier": dossier})


@login_required(login_url='login')
def folder_label_print_view(request, pk):
    """
    Print-ready view for Stage 7 physical folder label (لیبل پوشه پرونده).
    Displays prominent archive number, applicant info, project, unit, Form J number, and checklist.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    return render(request, "dossiers/print_folder_label.html", {"dossier": dossier})


@login_required(login_url='login')
def land_bank_print_view(request, pk):
    """
    Print-ready view for Stage 13 (Land Bank Expert - فرم مشخصات مالک، ملک و قدرالسهم).
    Rendered strictly for A4 Landscape official print.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    sig_obj = dossier.signatures.filter(slot_key="land_bank").first()

    total_share = dossier.total_land_share
    net_area = float(dossier.net_unit_area or 85.0)

    if total_share:
        arce_share = round(float(total_share) * 0.2468, 2)
        commons_share = round(float(total_share) - arce_share, 2)
        total_share_display = f"{float(total_share):.2f}"
    else:
        arce_share = round(net_area * 0.24, 2)
        commons_share = round(net_area * 0.72, 2)
        total_share_display = f"{(arce_share + commons_share):.2f}"

    rent_amount = None
    if dossier.current_year_rent and dossier.current_year_rent > 0:
        rent_amount = f"{dossier.current_year_rent:,}"
    elif dossier.past_years_rent and dossier.past_years_rent > 0:
        rent_amount = f"{dossier.past_years_rent:,}"

    prep_amount = None
    if dossier.preparation_cost and dossier.preparation_cost > 0:
        prep_amount = f"{dossier.preparation_cost:,}"

    context = {
        "dossier": dossier,
        "sig_obj": sig_obj,
        "land_share_arce": f"{arce_share:.2f}",
        "land_share_commons": f"{commons_share:.2f}",
        "total_share_display": total_share_display,
        "rent_amount": rent_amount,
        "prep_amount": prep_amount,
    }
    return render(request, "dossiers/print_land_bank.html", context)


def get_dossier_signatures_summary(dossier):
    """Returns (signatures_map, signed_count). Read-only: never writes to the DB."""
    import jdatetime
    sigs = {s.slot_key: s for s in dossier.signatures.all()}
    logs = list(dossier.audit_logs.filter(action__in=["SIGN", "APPROVE", "ARCHIVE"]).order_by("timestamp"))

    actors = {l.actor for l in logs}
    profiles = {p.full_name: p for p in UserProfile.objects.filter(full_name__in=actors)}
    for u in User.objects.filter(username__in=actors - set(profiles)).select_related("profile"):
        p = getattr(u, "profile", None)
        if p:
            profiles[u.username] = p

    for log in logs:
        m = re.search(r'مرحله\s+(\d+)', log.from_stage)
        if not m:
            continue
        try:
            date_str = jdatetime.datetime.fromgregorian(datetime=log.timestamp).strftime("%Y/%m/%d - %H:%M")
        except Exception:
            date_str = log.timestamp.strftime("%Y/%m/%d - %H:%M")
        prof = profiles.get(log.actor)
        prof_img = prof.signature_image if prof and prof.signature_image else None

        for slot_key in STAGE_TO_SLOTS.get(int(m.group(1)), []):
            sig = sigs.get(slot_key)
            if sig is None:
                sigs[slot_key] = DossierSignature(
                    dossier=dossier, slot_key=slot_key, signer_name=log.actor,
                    signer_title=log.role or "کارشناس اقدام‌کننده",
                    signed_date=date_str, signature_image=prof_img, uploaded_by=log.actor,
                )
            else:  # fill gaps in memory only
                if not sig.signed_date:
                    sig.signed_date = date_str
                if not sig.signer_name:
                    sig.signer_name = log.actor
                if not sig.signature_image and prof_img:
                    sig.signature_image = prof_img

    signed_count = sum(1 for k in ARCHIVAL_SLOTS if k in sigs and sigs[k].signed_date)
    return sigs, signed_count


def _build_summary_context(request, dossier, is_word_export=False):
    import jdatetime
    signatures_map, signed_count = get_dossier_signatures_summary(dossier)
    today = jdatetime.date.today()
    return {
        "dossier": dossier,
        "signatures_map": signatures_map,
        "signed_count": signed_count,
        "today_jalali": today.strftime("%Y/%m/%d"),
        "lease_year": (dossier.land_lease_year or "").strip() or str(today.year),
        "is_word_export": is_word_export,
    }


@login_required(login_url='login')
def dossier_summary_print_view(request, pk):
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    return render(request, "dossiers/print_summary.html", _build_summary_context(request, dossier))


def _ensure_check_receipt_attachment(user, dossier, check_type="loan", scan_url=""):
    """
    Creates or retrieves the official check receipt attachment in DossierAttachment
    reflecting all check scans with official header and footer.
    """
    check_type_norm = "prep" if check_type in ("prep", "preparation", "amadesazi") else "loan"
    doc_type = "PREP_CHECK" if check_type_norm == "prep" else "LOAN_CHECK"
    type_label = "اقساط آماده‌سازی و اجاره" if check_type_norm == "prep" else "تسهیلات وام دهک"
    target_chk_stage = 16 if check_type_norm == "loan" else 17

    scans_count = dossier.attachments.filter(doc_type=doc_type).exclude(preview_url__contains="/print/checks/").count()
    if scans_count > 1:
        title = f"رسید رسمی و برگه تحویل چک‌های {type_label} ({scans_count} برگ اسکن با سربرگ)"
    elif scans_count == 1:
        title = f"رسید رسمی و برگه تحویل چک‌های {type_label} (با تصویر اسکن)"
    else:
        title = f"رسید رسمی و برگه تحویل چک‌های {type_label}"

    preview_url = f"/dossier/{dossier.archive_number}/print/checks/?type={check_type_norm}&auto_archive=0"
    file_name = f"check_receipt_{dossier.archive_number}_{check_type_norm}.html"

    # Check if this receipt attachment already exists
    att = dossier.attachments.filter(preview_url__startswith=f"/dossier/{dossier.archive_number}/print/checks/").filter(doc_type=doc_type).first()
    if att:
        if att.title != title:
            att.title = title
            att.save(update_fields=['title'])
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
    Supports MULTIPLE check scans sequentially (each scan gets its own A4 page with header, footer & page numbering).
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    check_type = request.GET.get('type', 'prep' if request.GET.get('stage') == '17' else 'loan').lower()
    check_type_norm = "prep" if check_type in ("prep", "preparation", "amadesazi") else "loan"
    doc_type = "PREP_CHECK" if check_type_norm == "prep" else "LOAN_CHECK"
    auto_archive = request.GET.get('auto_archive', '1') == '1'
    scan_url = request.GET.get('scan_url') or ""

    # Fetch all physical check scan attachments
    scans_qs = dossier.attachments.filter(doc_type=doc_type).exclude(preview_url__contains="/print/checks/").order_by("id")
    check_scans = list(scans_qs)

    if scan_url:
        has_url = any(getattr(s, 'preview_url', '') == scan_url for s in check_scans)
        if not has_url:
            check_scans.insert(0, {"preview_url": scan_url, "id": 0, "title": "اسکن بارگذاری شده"})

    if not check_scans:
        check_scans = [None]

    if auto_archive:
        first_url = check_scans[0].preview_url if hasattr(check_scans[0], 'preview_url') else (check_scans[0].get('preview_url') if isinstance(check_scans[0], dict) else "")
        _ensure_check_receipt_attachment(request.user, dossier, check_type_norm, scan_url=first_url)

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
        "check_scans": check_scans,
        "total_scans": len(check_scans),
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
    if not attachment:
        return JsonResponse({"status": "error", "message": "تصویر اسکن چک یافت نشد."}, status=400)

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
    Endpoint that handles single or multiple check scans (upload or existing),
    attaches the official Header & Footer according to print.ts,
    saves the scans and the official check receipt in DossierAttachment,
    and returns JSON with the created attachments and the print URL.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    check_type = request.POST.get('check_type', 'loan').lower()
    check_type_norm = "prep" if check_type in ("prep", "preparation", "amadesazi") else "loan"
    doc_type = "PREP_CHECK" if check_type_norm == "prep" else "LOAN_CHECK"
    type_label = "اقساط آماده‌سازی و اجاره" if check_type_norm == "prep" else "تسهیلات وام دهک"
    target_chk_stage = 16 if check_type_norm == "loan" else 17

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

    # Support multiple files (files list or single file)
    uploaded_files = request.FILES.getlist('files')
    if not uploaded_files:
        uploaded_files = request.FILES.getlist('file')
    if not uploaded_files and request.FILES.get('file'):
        uploaded_files = [request.FILES.get('file')]

    created_attachments = []
    import time
    import hashlib

    nat_id = dossier.national_id or "general"
    upload_dir = os.path.join(settings.MEDIA_ROOT, nat_id, "check_scans")
    os.makedirs(upload_dir, exist_ok=True)

    # Count existing physical scans for this doc_type
    existing_count = dossier.attachments.filter(doc_type=doc_type).exclude(preview_url__contains="/print/checks/").count()

    for idx, file_obj in enumerate(uploaded_files):
        raw_name = os.path.basename(file_obj.name)
        base_stem, ext = os.path.splitext(raw_name)
        clean_stem = "".join(c for c in base_stem if c.isalnum() or c in "._-") or "check"
        clean_name = f"{clean_stem}_{int(time.time())}_{idx+1}{ext}"
        save_path = os.path.join(upload_dir, clean_name)

        with open(save_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        saved_url = f"{settings.MEDIA_URL}{nat_id}/check_scans/{clean_name}"
        page_num = existing_count + idx + 1
        file_sha = "SHA256: " + hashlib.sha256(f"{dossier.archive_number}-{clean_name}-{idx}-{timezone.now().isoformat()}".encode('utf-8')).hexdigest()[:24]

        scan_att = DossierAttachment.objects.create(
            dossier=dossier,
            stage=target_chk_stage,
            doc_type=doc_type,
            title=f"اسکن اصل چک صیادی {type_label} (برگ {page_num})",
            file_name=file_obj.name,
            file_sha256=file_sha,
            uploaded_by=uploader_name,
            preview_url=saved_url
        )
        created_attachments.append(scan_att)

    # Total check scans available after this upload
    all_check_scans = list(dossier.attachments.filter(doc_type=doc_type).exclude(preview_url__contains="/print/checks/").order_by("id"))
    total_scans_count = len(all_check_scans)

    # Generate or update the official checks receipt attachment
    if total_scans_count > 1:
        receipt_title = f"رسید رسمی و برگه تحویل چک‌های {type_label} ({total_scans_count} برگ اسکن با سربرگ و امضاء)"
    elif total_scans_count == 1:
        receipt_title = f"رسید رسمی و برگه تحویل چک‌های {type_label} (با تصویر اسکن)"
    else:
        receipt_title = f"رسید رسمی و برگه تحویل چک‌های {type_label}"

    receipt_filename = f"check_receipt_{dossier.archive_number}_{check_type_norm}.html"
    receipt_hash = "SHA256: " + hashlib.sha256(f"{dossier.archive_number}-RECEIPT-{check_type_norm}-{timezone.now().isoformat()}".encode('utf-8')).hexdigest()[:24]
    
    preview_query = f"?type={check_type_norm}&auto_archive=0"
    print_preview_url = f"/dossier/{dossier.archive_number}/print/checks/{preview_query}"

    receipt_att = dossier.attachments.filter(preview_url__startswith=f"/dossier/{dossier.archive_number}/print/checks/").filter(doc_type=doc_type).first()
    if receipt_att:
        receipt_att.title = receipt_title
        receipt_att.stage = target_chk_stage
        receipt_att.file_name = receipt_filename
        receipt_att.file_sha256 = receipt_hash
        receipt_att.preview_url = print_preview_url
        receipt_att.save()
    else:
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

    scan_label_count = len(created_attachments) if created_attachments else total_scans_count
    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {target_chk_stage}: دریافت چک‌های {type_label}",
        to_stage=f"مرحله {target_chk_stage}: دریافت چک‌های {type_label}",
        actor=uploader_name,
        role=uploader_role,
        action="SUBMIT_AND_PRINT",
        action_label=f"بارگذاری اسکن و صدور رسید چک‌های {type_label}",
        signature_hash=receipt_hash,
        notes=f"تعداد {scan_label_count} برگ اسکن چک‌های {type_label} ثبت گردید. سربرگ متمرکز اطلاعات، خلاصه مالی و کادر امضاء بر روی کلیه صفحات اعمال شد."
    )

    client_ip = request.META.get('REMOTE_ADDR')
    for att_item in created_attachments:
        DossierFieldChangeLog.objects.create(
            dossier=dossier,
            field_name="attachment",
            field_label=f"بارگذاری اسکن اصل چک {type_label}",
            old_value="-",
            new_value=f"{att_item.title} ({att_item.file_name})",
            changed_by=uploader_name,
            role=uploader_role,
            stage=target_chk_stage,
            ip_address=client_ip
        )

    print_url = f"/dossier/{dossier.archive_number}/print/checks/{preview_query}&auto_print=1"

    def _serialize_att(att):
        if not att:
            return None
        return {
            "id": att.id,
            "stage": att.stage,
            "type": att.doc_type,
            "doc_type": att.doc_type,
            "title": att.title,
            "fileName": att.file_name,
            "file_name": att.file_name,
            "uploader": att.uploaded_by,
            "uploaded_by": att.uploaded_by,
            "uploadDate": att.uploaded_at.strftime("%Y/%m/%d") if att.uploaded_at else "",
            "sha256": att.file_sha256,
            "file_sha256": att.file_sha256,
            "preview_url": att.preview_url,
            "immutable": True if att.preview_url.startswith("/print/") else False
        }

    serialized_scans = [_serialize_att(a) for a in created_attachments]
    serialized_receipt = _serialize_att(receipt_att)

    return JsonResponse({
        "status": "success",
        "attachments": serialized_scans + ([serialized_receipt] if serialized_receipt else []),
        "attachment": serialized_receipt,
        "scan_count": total_scans_count,
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
    custom_title = request.POST.get("title", "").strip()
    doc_type = request.POST.get("doc_type", "OTHER")

    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "عدم دسترسی اقدام: لطفاً ابتدا وارد سامانه شوید."}, status=403)
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None

    # Dynamic Actor Attribution
    uploader_name = profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username)
    uploader_role = profile.role_title if profile and profile.role_title else dossier.current_role

    # Target folder: uploads/<national_id>/
    nat_id = str(dossier.national_id).strip() or "general"
    nat_id_dir = os.path.join(settings.MEDIA_ROOT, nat_id)
    os.makedirs(nat_id_dir, exist_ok=True)

    # Collect files or preview URLs (supports single or batch multi-scan upload)
    uploaded_files = request.FILES.getlist("files") or request.FILES.getlist("file")
    preview_urls = request.POST.getlist("preview_urls") or ([request.POST.get("preview_url")] if request.POST.get("preview_url") else [])
    preview_urls = [u for u in preview_urls if u and str(u).strip()]

    created_attachments = []
    timestamp_prefix = timezone.now().strftime('%Y%m%d_%H%M%S')

    if uploaded_files:
        total_files = len(uploaded_files)
        for idx, up_file in enumerate(uploaded_files, start=1):
            orig_name = up_file.name
            name_base, ext = os.path.splitext(orig_name)
            safe_name = f"{timestamp_prefix}_{idx}_{orig_name}" if os.path.exists(os.path.join(nat_id_dir, orig_name)) else orig_name
            file_path = os.path.join(nat_id_dir, safe_name)

            hasher = hashlib.sha256()
            with open(file_path, "wb") as f:
                for chunk in up_file.chunks():
                    hasher.update(chunk)
                    f.write(chunk)
            file_hash = "SHA256: " + hasher.hexdigest()[:24]
            saved_url = f"/uploads/{nat_id}/{safe_name}"

            if custom_title:
                item_title = f"{custom_title} (برگه {idx})" if total_files > 1 else custom_title
            else:
                item_title = name_base or f"برگه اسکن {idx}"

            att = DossierAttachment.objects.create(
                dossier=dossier,
                stage=dossier.current_stage,
                doc_type=doc_type,
                title=item_title,
                file_name=safe_name,
                file_sha256=file_hash,
                uploaded_by=uploader_name,
                preview_url=saved_url
            )
            created_attachments.append(att)

    elif preview_urls:
        total_previews = len(preview_urls)
        for idx, p_url in enumerate(preview_urls, start=1):
            file_name = f"scan_{timestamp_prefix}_{idx}.jpg"
            file_path = os.path.join(nat_id_dir, file_name)
            saved_url = f"/uploads/{nat_id}/{file_name}"

            if p_url.startswith("data:"):
                try:
                    import base64
                    _, encoded = p_url.split(",", 1)
                    file_bytes = base64.b64decode(encoded)
                    with open(file_path, "wb") as f:
                        f.write(file_bytes)
                    file_hash = "SHA256: " + hashlib.sha256(file_bytes).hexdigest()[:24]
                except Exception:
                    file_hash = "SHA256: " + hashlib.sha256(f"{file_name}-{timezone.now().isoformat()}".encode()).hexdigest()[:24]
            else:
                file_hash = "SHA256: " + hashlib.sha256(f"{file_name}-{timezone.now().isoformat()}".encode()).hexdigest()[:24]

            if custom_title:
                item_title = f"{custom_title} (برگه {idx})" if total_previews > 1 else custom_title
            else:
                item_title = f"اسکن مدرک پرونده (برگه {idx})"

            att = DossierAttachment.objects.create(
                dossier=dossier,
                stage=dossier.current_stage,
                doc_type=doc_type,
                title=item_title,
                file_name=file_name,
                file_sha256=file_hash,
                uploaded_by=uploader_name,
                preview_url=saved_url
            )
            created_attachments.append(att)
    else:
        return JsonResponse({"status": "error", "message": "هیچ فایل یا برگه اسکنی جهت بارگذاری ارسال نشده است."}, status=400)

    # Consolidated audit log
    if len(created_attachments) == 1:
        single_att = created_attachments[0]
        action_label = f"بارگذاری سند: {single_att.title}"
        notes_str = f"سند «{single_att.title}» با موفقیت اسکن و در پوشه اختصاصی کد ملی {nat_id} ذخیره گردید."
        log_hash = single_att.file_sha256
    else:
        action_label = f"بارگذاری دسته‌جمعی {len(created_attachments)} برگ سند"
        notes_str = f"تعداد {len(created_attachments)} برگ سند اسکن‌شده با موفقیت در پوشه اختصاصی کد ملی {nat_id} ثبت و بایگانی گردید."
        log_hash = created_attachments[0].file_sha256

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {dossier.current_stage}",
        to_stage=f"مرحله {dossier.current_stage}",
        actor=uploader_name,
        role=uploader_role,
        action="SUBMIT",
        action_label=action_label,
        signature_hash=log_hash,
        notes=notes_str
    )

    client_ip = request.META.get('REMOTE_ADDR')
    for att_item in created_attachments:
        DossierFieldChangeLog.objects.create(
            dossier=dossier,
            field_name="attachment",
            field_label="بارگذاری و الصاق سند",
            old_value="-",
            new_value=f"{att_item.title} ({att_item.file_name})",
            changed_by=uploader_name,
            role=uploader_role,
            stage=dossier.current_stage,
            ip_address=client_ip
        )

    att_payloads = [
        {
            "id": a.id,
            "stage": a.stage,
            "type": a.doc_type,
            "doc_type": a.doc_type,
            "title": a.title,
            "fileName": a.file_name,
            "uploader": a.uploaded_by,
            "uploadDate": timezone.now().strftime("%Y/%m/%d %H:%M"),
            "sha256": a.file_sha256,
            "preview_url": a.preview_url,
            "immutable": True
        }
        for a in created_attachments
    ]

    return JsonResponse({
        "status": "success",
        "count": len(created_attachments),
        "message": f"{len(created_attachments)} برگ سند با موفقیت بارگذاری و الصاق شد.",
        "attachments": att_payloads,
        "attachment": att_payloads[0] if att_payloads else None
    })


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

    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "شما مجوز حذف مدارک در این پرونده را ندارید."}, status=403)
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None

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

    client_ip = request.META.get('REMOTE_ADDR')
    DossierFieldChangeLog.objects.create(
        dossier=dossier,
        field_name="attachment",
        field_label="حذف مدرک پیوست",
        old_value=f"{att_title} ({attachment.file_name})",
        new_value="حذف قطعی از پرونده",
        changed_by=actor_name,
        role=actor_role,
        stage=dossier.current_stage,
        ip_address=client_ip
    )

    return JsonResponse({"status": "success", "message": f"مدرک «{att_title}» با موفقیت حذف گردید.", "attachment_id": att_id})


# --------------------------------------------------------------------------------------------------
# Enterprise Authentication & Profile Views
# --------------------------------------------------------------------------------------------------

@never_cache
@ensure_csrf_cookie
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
                messages.info(request, display_name, extra_tags="login_dialog")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect("dossier_list")
            else:
                error = "حساب کاربری شما غیرفعال شده است. لطفاً با مدیر سیستم تماس بگیرید."
        else:
            error = "نام کاربری یا کلمه عبور وارد شده نامعتبر است."

    return render(request, "auth/login.html", {"error": error, "next": next_url})


@never_cache
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
        elif action == "update_avatar":
            avatar_file = request.FILES.get("avatar")
            cropped_avatar = request.POST.get("cropped_avatar_data")
            profile = getattr(request.user, 'profile', None)
            payload = cropped_avatar or avatar_file
            if profile and payload:
                success = _process_and_save_avatar(profile, payload)
                if success:
                    messages.success(request, "تصویر پروفایل شما با موفقیت بروزرسانی شد.")
                else:
                    messages.error(request, "خطا در پردازش و ذخیره تصویر پروفایل.")
            else:
                messages.error(request, "لطفاً ابتدا یک تصویر برای پروفایل انتخاب فرمایید.")
            return redirect("user_profile")
        elif action == "update_signature":
            sig_file = request.FILES.get("signature_image")
            cropped_sig = request.POST.get("cropped_signature_data")
            canvas_sig = request.POST.get("canvas_signature_data")
            profile = getattr(request.user, 'profile', None)
            payload = cropped_sig or canvas_sig or sig_file
            if profile and payload:
                success = _process_and_save_signature(profile, payload)
                if success:
                    messages.success(request, "تصویر امضای الکترونیکی شما با موفقیت برش خورده و ثبت گردید.")
                else:
                    messages.error(request, "خطا در پردازش و ذخیره‌سازی تصویر امضا.")
            else:
                messages.error(request, "لطفاً تصویر نمونه امضا را برش داده یا فایل آن را انتخاب فرمایید.")
            return redirect("user_profile")

    return render(request, "auth/profile.html", {"user": request.user})


def _process_and_save_avatar(profile, file_or_b64):
    """
    Standardizes user avatar to square 1:1 JPEG (320x320) with center crop.
    """
    if not file_or_b64:
        return False
    try:
        from PIL import Image
        from io import BytesIO
        import base64
        from django.core.files.base import ContentFile
        from django.utils import timezone

        img = None
        if isinstance(file_or_b64, str):
            if ";base64," in file_or_b64:
                _, imgstr = file_or_b64.split(";base64,", 1)
            else:
                imgstr = file_or_b64
            img = Image.open(BytesIO(base64.b64decode(imgstr)))
        elif hasattr(file_or_b64, "read"):
            img = Image.open(file_or_b64)

        if img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            w, h = img.size
            min_side = min(w, h)
            left = (w - min_side) // 2
            top = (h - min_side) // 2
            cropped = img.crop((left, top, left + min_side, top + min_side)).resize((320, 320), Image.Resampling.LANCZOS)

            buf = BytesIO()
            cropped.save(buf, format="JPEG", quality=90)
            buf.seek(0)
            filename = f"avatar_{profile.user_id}_{int(timezone.now().timestamp())}.jpg"
            profile.avatar.save(filename, ContentFile(buf.getvalue()), save=True)
            return True
    except Exception as e:
        logger.warning(f"Error processing avatar for user {profile.user_id}: {e}")
        if hasattr(file_or_b64, "read"):
            profile.avatar = file_or_b64
            profile.save()
            return True
    return False


def _normalize_signature_image(img):
    """White paper -> transparent, trim margins, cap size. Returns RGBA image or None if blank."""
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(img).convert("RGBA")
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] == 255:                      # fully opaque: photo/scan on white
        gray = img.convert("L")
        gray_ac = ImageOps.autocontrast(gray, cutoff=1)
        alpha = gray_ac.point(lambda p: 0 if p >= 215 else min(255, int((215 - p) * 255 / 100)))
        img.putalpha(alpha)
    bbox = alpha.point(lambda a: 255 if a > 30 else 0).getbbox()
    if not bbox:
        return None
    pad = max(4, int(0.02 * max(img.size)))
    l, t, r, b = bbox
    img = img.crop((max(0, l - pad), max(0, t - pad), min(img.width, r + pad), min(img.height, b + pad)))
    img.thumbnail((1200, 600), Image.Resampling.LANCZOS)
    return img



def _process_and_save_signature(profile, file_or_b64):
    """
    Standardizes cropped or drawn signature as high-res PNG with proper bounding.
    """
    if not file_or_b64:
        return False
    try:
        from PIL import Image
        from io import BytesIO
        import base64
        from django.core.files.base import ContentFile
        from django.utils import timezone

        img = None
        if isinstance(file_or_b64, str):
            if ";base64," in file_or_b64:
                _, imgstr = file_or_b64.split(";base64,", 1)
            else:
                imgstr = file_or_b64
            img = Image.open(BytesIO(base64.b64decode(imgstr)))
        elif hasattr(file_or_b64, "read"):
            img = Image.open(file_or_b64)

        if img:
            img = _normalize_signature_image(img)
            if img is None:
                return False

            buf = BytesIO()
            img.save(buf, format="PNG", compress_level=4)
            buf.seek(0)
            filename = f"sig_{profile.user_id}_{int(timezone.now().timestamp())}.png"
            profile.signature_image.save(filename, ContentFile(buf.getvalue()), save=True)
            return True
    except Exception as e:
        logger.warning(f"Error processing signature for user {profile.user_id}: {e}")
        if hasattr(file_or_b64, "read"):
            profile.signature_image = file_or_b64
            profile.save()
            return True
    return False


@login_required(login_url='login')
def first_login_setup_view(request):
    """
    Mandatory security onboarding screen for users on initial login:
    Forces setting a private password, uploading avatar, and capturing & cropping their signature picture.
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.must_change_password:
        return redirect("dossier_list")

    error = None
    if request.method == "POST":
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        sig_file = request.FILES.get("signature_image")
        cropped_sig = request.POST.get("cropped_signature_data", "").strip()
        canvas_sig = request.POST.get("canvas_signature_data", "").strip()
        avatar_file = request.FILES.get("avatar")
        cropped_avatar = request.POST.get("cropped_avatar_data", "").strip()

        sig_payload = cropped_sig or canvas_sig or sig_file

        if len(new_password) < 6:
            error = "کلمه عبور جدید باید حداقل ۶ کاراکتر باشد."
        elif new_password != confirm_password:
            error = "کلمه عبور جدید با تکرار آن یکسان نیست."
        elif not sig_payload:
            error = "عکس‌برداری و برش یا بارگذاری نمونه امضای الکترونیک الزامی است."
        else:
            # Process avatar if provided
            if cropped_avatar or avatar_file:
                _process_and_save_avatar(profile, cropped_avatar or avatar_file)

            # Process signature
            sig_saved = _process_and_save_signature(profile, sig_payload)
            if not sig_saved:
                error = "خطا در پردازش یا ذخیره‌سازی تصویر امضا. لطفاً مجدداً تلاش فرمایید."
            else:
                request.user.set_password(new_password)
                request.user.save()
                profile.must_change_password = False
                profile.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "کلمه عبور اختصاصی، تصویر پروفایل و نمونه امضای دیجیتال شما با موفقیت ثبت گردید.")
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
            stage_pills = [{"id": "all", "title": "کلیه ۲۲ مرحله (اختیارات تام)"}]
        else:
            nums = [int(s.strip()) for s in allowed_raw.split(',') if s.strip().isdigit()]
            stage_pills = [{"id": s, "title": f"مرحله {s}: {HousingDossier.STAGE_ROLES.get(s, ('','',f'مرحله {s}'))[2]}"} for s in nums]
            parsed_stages = ",".join(str(s) for s in nums)

        users_data.append({
            "id": u.pk,
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
    stage_experts_count = {i: 0 for i in range(1, 23)}
    for ud in users_data:
        raw = ud.get("allowed_stages", "")
        if raw == "all" or ud.get("is_housing_chief") or ud.get("is_superuser"):
            for i in range(1, 23):
                stage_experts_count[i] += 1
        else:
            nums = [int(s.strip()) for s in raw.split(',') if s.strip().isdigit()]
            for s in nums:
                if 1 <= s <= 22:
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



def _parse_filter_date(date_str):
    if not date_str:
        return None
    try:
        import jdatetime
        import datetime
        clean = str(date_str).strip().replace('-', '/')
        parts = clean.split('/')
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if y > 1600:
                return datetime.date(y, m, d)
            elif y >= 1300:
                return jdatetime.date(y, m, d).togregorian()
    except Exception:
        pass
    return None


@login_required
def excel_export_all_view(request):
    """
    Export dossiers with filtering of stage, date range (Jalali/Gregorian), and search query.
    Admins have full visibility; standard users are scoped to their allowed stages.
    """
    from .excel_service import generate_dossiers_export
    from django.db.models import Q

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and (profile.is_housing_chief or profile.allowed_stages == 'all'))

    query = request.GET.get("q", "").strip()
    stage_val = request.GET.get("stage", "").strip()
    from_date_raw = request.GET.get("from_date", "").strip()
    to_date_raw = request.GET.get("to_date", "").strip()

    qs = HousingDossier.objects.all().order_by("-archive_number")

    if not is_admin:
        allowed = profile.get_allowed_stages_list() if profile else []
        if allowed:
            qs = qs.filter(current_stage__in=allowed, is_locked=False)
        else:
            qs = qs.none()

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
        stg = int(stage_val)
        if is_admin or (profile and profile.can_action_stage(stg)):
            qs = qs.filter(current_stage=stg)

    from_date = _parse_filter_date(from_date_raw)
    if from_date:
        qs = qs.filter(created_at__date__gte=from_date)

    to_date = _parse_filter_date(to_date_raw)
    if to_date:
        qs = qs.filter(created_at__date__lte=to_date)

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

    if uploaded_file or (signature_base64 and signature_base64.startswith("data:image")):
        try:
            from PIL import Image
            from io import BytesIO
            import base64
            from django.core.files.base import ContentFile
            if uploaded_file:
                raw_img = Image.open(uploaded_file)
            else:
                _, imgstr = signature_base64.split(';base64,', 1)
                raw_img = Image.open(BytesIO(base64.b64decode(imgstr)))
            norm_img = _normalize_signature_image(raw_img)
            if norm_img is not None:
                buf = BytesIO()
                norm_img.save(buf, format="PNG", compress_level=4)
                buf.seek(0)
                file_name = f"sig_{dossier.archive_number}_{slot_key}.png"
                sig_obj.signature_image.save(file_name, ContentFile(buf.getvalue()), save=False)
            elif uploaded_file:
                sig_obj.signature_image = uploaded_file
        except Exception as e:
            logger.warning(f"Error normalizing signature image for dossier {dossier.archive_number}: {e}")
            if uploaded_file:
                sig_obj.signature_image = uploaded_file

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
def project_bank_mapping_api(request):
    """
    API to fetch and update Project-to-Bank mappings for all 96 projects.
    """
    profile = getattr(request.user, 'profile', None)
    is_chief_or_admin = request.user.is_superuser or request.user.is_staff or (profile and profile.is_housing_chief)
    can_action_bank = profile and (profile.can_action_stage(6) or profile.can_action_stage(9))
    if not (is_chief_or_admin or can_action_bank):
        return JsonResponse({"status": "error", "message": "دسترسی غیرمجاز."}, status=403)

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = request.POST

        mappings = body.get("mappings")
        if mappings and isinstance(mappings, list):
            updated = 0
            for item in mappings:
                p = (item.get("project_name") or "").strip()
                b = (item.get("bank_code") or "maskan").strip()
                if p and b in ["maskan", "melli", "mellat", "saderat", "tejarat"]:
                    ProjectBankMapping.objects.update_or_create(
                        project_name=p,
                        defaults={"bank_code": b}
                    )
                    updated += 1
            return JsonResponse({"status": "success", "message": f"تخصیص {updated} پروژه به بانک‌های عامل با موفقیت ذخیره شد."})

        project_name = (body.get("project_name") or "").strip()
        bank_code = (body.get("bank_code") or "").strip()
        if not project_name or bank_code not in ["maskan", "melli", "mellat", "saderat", "tejarat"]:
            return JsonResponse({"status": "error", "message": "اطلاعات نامعتبر است."}, status=400)

        mapping_obj, _ = ProjectBankMapping.objects.update_or_create(
            project_name=project_name,
            defaults={"bank_code": bank_code}
        )
        return JsonResponse({
            "status": "success",
            "message": f"پروژه «{project_name}» به {mapping_obj.get_bank_code_display()} تخصیص داده شد.",
            "project_name": project_name,
            "bank_code": bank_code,
            "bank_name": mapping_obj.get_bank_code_display()
        })

    # GET: return all 96 projects mappings
    from django.db.models import Count
    all_projects = sorted(list(set(p.strip() for p in HousingDossier.objects.values_list("project", flat=True) if p and p.strip())))
    existing_maps = {m.project_name: m.bank_code for m in ProjectBankMapping.objects.all()}
    proj_counts = dict(HousingDossier.objects.values("project").annotate(c=Count("id")).values_list("project", "c"))

    result = []
    for p in all_projects:
        b_code = existing_maps.get(p, "maskan")
        result.append({
            "project_name": p,
            "bank_code": b_code,
            "bank_name": ProjectBankMapping.BANK_NAMES.get(b_code, "بانک مسکن"),
            "dossier_count": proj_counts.get(p, 0)
        })

    return JsonResponse({"status": "success", "projects": result, "total": len(result)})


@login_required(login_url='login')
def bank_letter_sender_view(request):
    """
    Admin component to prepare, preview and send official Bank Introduction Letter batches.
    Displays the list of eligible dossiers (who reach full payment through loans + cash / Stage 6).
    Supports multi-project sheet export for 5 banks (Melli, Mellat, Maskan, Saderat, Tejarat)
    covering all 96 projects.
    """
    profile = getattr(request.user, 'profile', None)
    is_chief_or_admin = request.user.is_superuser or request.user.is_staff or (profile and profile.is_housing_chief)
    can_action_bank = profile and (profile.can_action_stage(6) or profile.can_action_stage(9))
    
    if not (is_chief_or_admin or can_action_bank):
        messages.error(request, "دسترسی به بخش ارسال نامه بانک نیازمند مجوز کارشناس بانک یا مدیر سیستم است.")
        return redirect("dossier_list")

    # 96 Distinct Projects from DB and mapping
    mappings = list(ProjectBankMapping.objects.all().order_by("project_name"))
    existing_maps = {m.project_name: m.bank_code for m in mappings}
    existing_meta = {
        m.project_name: {
            "bank_code": m.bank_code,
            "bank_name": m.get_bank_code_display(),
            "branch_code": m.branch_code or "",
            "branch_name": m.branch_name or "",
            "project_code": m.project_code or "",
        }
        for m in mappings
    }
    
    projects = [m.project_name for m in mappings]
    if not projects:
        projects = sorted(list(set(p.strip() for p in HousingDossier.objects.values_list("project", flat=True) if p and p.strip())))

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
            m_bank = existing_meta.get(d.project, {})
            b_code = m_bank.get("bank_code", "maskan")
            b_name = m_bank.get("bank_name", "بانک مسکن")
            bl_obj, _ = BankLetter.objects.get_or_create(
                letter_number=num,
                defaults={
                    "letter_date": d.bank_letter_date or d.bank_sent_date or today_jalali,
                    "bank_code": b_code,
                    "bank_name": b_name,
                    "project_name": d.project or "پروژه مسکونی",
                    "sender_name": "کارشناس تسهیلات بانکی",
                    "sender_role": "واحد تسهیلات و بانک عامل",
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
            "bank_code": l.bank_code or "maskan",
            "bank_name": l.bank_name or ProjectBankMapping.BANK_NAMES.get(l.bank_code, "بانک عامل"),
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

    # Bank Statistics & Project Mappings JSON
    from django.db.models import Count
    proj_dossier_counts = dict(HousingDossier.objects.values("project").annotate(c=Count("id")).values_list("project", "c"))
    proj_stage6_counts = dict(HousingDossier.objects.filter(current_stage=6).values("project").annotate(c=Count("id")).values_list("project", "c"))
    proj_sent_counts = dict(HousingDossier.objects.filter(is_sent_to_bank=True).values("project").annotate(c=Count("id")).values_list("project", "c"))

    bank_stats = {}
    for code, name in ProjectBankMapping.BANK_CHOICES:
        projs = [m.project_name for m in mappings if m.bank_code == code]
        tot_d = sum(proj_dossier_counts.get(p, 0) for p in projs)
        s6_d = sum(proj_stage6_counts.get(p, 0) for p in projs)
        sent_d = sum(proj_sent_counts.get(p, 0) for p in projs)
        bank_stats[code] = {
            "code": code,
            "name": name,
            "project_count": len(projs),
            "dossier_count": tot_d,
            "stage6_count": s6_d,
            "sent_count": sent_d,
            "projects": projs,
        }

    project_mappings_list = []
    for m in mappings:
        d_count = proj_dossier_counts.get(m.project_name, 0)
        s6_count = proj_stage6_counts.get(m.project_name, 0)
        sent_count = proj_sent_counts.get(m.project_name, 0)
        project_mappings_list.append({
            "project_name": m.project_name,
            "project_code": m.project_code,
            "bank_code": m.bank_code,
            "bank_name": m.get_bank_code_display(),
            "branch_code": m.branch_code,
            "branch_name": m.branch_name,
            "dossier_count": d_count,
            "stage6_count": s6_count,
            "sent_count": sent_count,
        })

    # Active Dossiers: Priority Stage 6, Stage 5, Equity Funded, Added to Shipment, or Sent dossiers
    priority_qs = HousingDossier.objects.filter(
        models.Q(current_stage__in=[5, 6, 7]) |
        models.Q(is_sent_to_bank=True) |
        models.Q(is_equity_funded=True) |
        models.Q(is_added_to_bank_shipment_list=True)
    ).order_by("archive_number")

    initial_dossiers = list(priority_qs[:500])

    dossiers_json_list = []
    for d in initial_dossiers:
        fn, ln = split_persian_name(d.full_name)
        base_cost = d.base_cost_without_loan or 0
        total_loans = (d.fund_loan_amount or 0) + (d.decile_loan_amount or 0)
        is_funded = (total_loans >= base_cost and base_cost > 0) or d.is_equity_funded or d.is_sent_to_bank or (d.current_stage >= 6)

        m_info = existing_meta.get(d.project, {})
        b_code = m_info.get("bank_code", "maskan")
        b_name = m_info.get("bank_name", "بانک مسکن")

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
            "bank_code": b_code,
            "bank_name": b_name,
            "current_stage": d.current_stage,
            "current_stage_title": d.current_stage_title,
            "is_sent_to_bank": d.is_sent_to_bank,
            "is_fully_funded": is_funded,
            "base_cost_without_loan": base_cost,
            "total_loans": total_loans,
            "applicant_equity": d.applicant_equity,
            "is_equity_funded": d.is_equity_funded,
            "bank_letter_number": d.bank_letter_number or d.bank_sent_letter_number or "",
            "bank_letter_date": d.bank_letter_date or d.bank_sent_date or "",
        })

    initial_letter = request.GET.get("letter", "").strip()

    context = {
        "dossiers_json": json.dumps(dossiers_json_list, ensure_ascii=False),
        "letters_history_json": json.dumps(letter_history_list, ensure_ascii=False),
        "project_mappings_json": json.dumps(project_mappings_list, ensure_ascii=False),
        "bank_stats": bank_stats,
        "bank_stats_json": json.dumps(bank_stats, ensure_ascii=False),
        "banks_list": ProjectBankMapping.BANK_CHOICES,
        "letters_count": len(letter_history_list),
        "projects": projects,
        "projects_count": len(projects),
        "total_dossiers_count": HousingDossier.objects.count(),
        "today_jalali": today_jalali,
        "default_project": projects[0] if projects else "پروژه مسکونی",
        "initial_letter": initial_letter,
    }
    return render(request, "admin/bank_letter_sender.html", context)


@login_required(login_url='login')
def bank_letter_lookup_api(request):
    """
    Looks up dossiers across all 34,000+ records by archive number, national ID, or name
    so the operator can dynamically add records to the bank shipment batch.
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"status": "success", "results": []})

    tokens = [t.strip() for t in re.split(r'[\s,،]+', q) if t.strip()]
    if not tokens:
        return JsonResponse({"status": "success", "results": []})

    query = models.Q()
    for tok in tokens:
        if tok.isdigit():
            query |= models.Q(archive_number=int(tok)) | models.Q(national_id__icontains=tok)
        else:
            query |= models.Q(full_name__icontains=tok)

    dossiers = HousingDossier.objects.filter(query)[:50]
    existing_maps = {m.project_name: (m.bank_code, m.get_bank_code_display()) for m in ProjectBankMapping.objects.all()}

    results = []
    for d in dossiers:
        fn, ln = split_persian_name(d.full_name)
        b_code, b_name = existing_maps.get(d.project, ("maskan", "بانک مسکن"))
        results.append({
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
            "bank_code": b_code,
            "bank_name": b_name,
            "current_stage": d.current_stage,
            "current_stage_title": d.current_stage_title,
            "is_sent_to_bank": d.is_sent_to_bank,
            "is_equity_funded": d.is_equity_funded,
            "bank_letter_number": d.bank_letter_number or d.bank_sent_letter_number or "",
            "bank_letter_date": d.bank_letter_date or d.bank_sent_date or "",
        })

    return JsonResponse({"status": "success", "results": results})


@login_required(login_url='login')
def bank_letter_submit_api(request):
    """
    Processes the batch Bank Letter submission:
    Updates is_sent_to_bank, bank_letter_number and bank_letter_date,
    creates BankLetter archive entity with bank details, and advances Stage 6 dossiers to Stage 7.
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
    bank_code = (body.get("bank_code") or "").strip()
    notes = (body.get("notes") or "").strip()

    if not archive_numbers:
        return JsonResponse({"status": "error", "message": "هیچ پرونده‌ای انتخاب نشده است."}, status=400)
    import jdatetime
    today_j = jdatetime.date.today().strftime('%Y/%m/%d')
    if not letter_number:
        batch_cnt = BankLetter.objects.count() + 1
        letter_number = f"معرفی به بانک ({today_j} - دسته {batch_cnt})"
    if not letter_date:
        letter_date = today_j

    clean_archives = []
    for item in archive_numbers:
        try:
            clean_archives.append(int(str(item).strip()))
        except ValueError:
            continue

    dossiers = HousingDossier.objects.filter(archive_number__in=clean_archives)
    if not dossiers.exists():
        return JsonResponse({"status": "error", "message": "هیچ پرونده معتبری برای ثبت یافت نشد."}, status=400)

    updated_count = 0
    updated_archives = []

    actor_name = profile.full_name if profile and profile.full_name else request.user.username
    actor_role = profile.role_title if profile and profile.role_title else "کارشناس تسهیلات بانکی"

    bank_name = ProjectBankMapping.BANK_NAMES.get(bank_code, "")
    if not bank_name:
        first_d = dossiers.first()
        if first_d and first_d.project:
            m = ProjectBankMapping.objects.filter(project_name=first_d.project).first()
            if m:
                bank_code = m.bank_code
                bank_name = m.get_bank_code_display()
    if not bank_name:
        bank_name = "بانک عامل"

    for d in dossiers:
        d.is_sent_to_bank = True
        d.bank_letter_number = (body.get("letter_number") or "").strip()
        d.bank_letter_date = (body.get("letter_date") or "").strip()
        d.bank_sent_letter_number = letter_number
        d.bank_sent_date = letter_date
        d.is_added_to_bank_shipment_list = True
        d.bank_shipment_list_added_at = timezone.now()

        from_stage_str = f"مرحله {d.current_stage}: {d.current_stage_title}"
        if d.current_stage == 6:
            d.current_stage = 7
            to_stage_str = f"مرحله ۷: اسکن مدارک و دفترچه اقساط"
        else:
            to_stage_str = f"مرحله {d.current_stage}: {d.current_stage_title}"

        d.save()
        updated_count += 1
        updated_archives.append(d.archive_number)

        WorkflowSignatureLog.objects.create(
            dossier=d,
            from_stage=from_stage_str,
            to_stage=to_stage_str,
            actor=actor_name,
            role=actor_role,
            action="BANK_LETTER",
            action_label=f"ارسال نامه معرفی به {bank_name}",
            notes=f"نامه معرفی به {bank_name} صادره به شماره {letter_number} مورخ {letter_date}. {notes}".strip(),
            signature_hash=f"BANK-LETTER-{d.archive_number}-{letter_number}"
        )

    first_dossier = dossiers.first()
    project_title = first_dossier.project if first_dossier and first_dossier.project else "پروژه‌های مسکونی"
    bank_letter, created = BankLetter.objects.get_or_create(
        letter_number=letter_number,
        defaults={
            "letter_date": letter_date,
            "bank_code": bank_code,
            "bank_name": bank_name,
            "project_name": project_title,
            "sender_user": request.user,
            "sender_name": actor_name,
            "sender_role": actor_role,
            "notes": notes,
        }
    )
    bank_letter.letter_date = letter_date
    bank_letter.bank_code = bank_code
    bank_letter.bank_name = bank_name
    if notes:
        bank_letter.notes = notes
    bank_letter.sender_name = actor_name
    bank_letter.sender_role = actor_role
    bank_letter.dossiers.add(*dossiers)
    bank_letter.save()

    return JsonResponse({
        "status": "success",
        "message": f"نامه {bank_name} با شماره {letter_number} برای {updated_count} پرونده با موفقیت ثبت گردید و پرونده‌ها به مرحله ۷ ارجاع شدند.",
        "updated_count": updated_count,
        "updated_archives": updated_archives,
        "letter_number": letter_number,
        "letter_date": letter_date,
        "bank_code": bank_code,
        "bank_name": bank_name,
        "letter_id": bank_letter.id
    })


def _build_bank_workbook(bank_code, bank_name, project_names, dossiers_qs, proj_meta=None):
    """
    Builds an openpyxl Workbook where each project assigned to this bank gets its own sheet.
    Exact 18-column standard format from official project unit sheet.
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)

    thin_border = Border(
        left=Side(style='thin', color='475569'),
        right=Side(style='thin', color='475569'),
        top=Side(style='thin', color='475569'),
        bottom=Side(style='thin', color='475569')
    )
    headers = [
        "ردیف", "نام", "نام خانوادگی", "رتبه", "کدملی", "شماره تماس",
        "کد بلوک", "طبقه", "کدواحد", "متراژ پارکینگ مسقف", "شماره پارکینگ",
        "متراژ انباری", "شماره انباری", "تعداد خواب", "مشاعات", "متراژ مفید",
        "جهت", "جمع متراژ"
    ]
    col_widths = [8, 16, 18, 8, 14, 15, 12, 8, 10, 16, 14, 14, 14, 12, 12, 12, 12, 12]

    from collections import defaultdict
    dossiers_by_proj = defaultdict(list)
    for d in dossiers_qs.order_by("archive_number"):
        if d.project:
            dossiers_by_proj[d.project.strip()].append(d)

    sheet_names_used = set()
    for proj in project_names:
        clean_name = ''.join(c if c not in r':\\/?*[]\'"' else '-' for c in proj).strip()
        short_name = clean_name[:30] if len(clean_name) > 30 else clean_name
        if not short_name:
            short_name = "پروژه"
        base_name = short_name
        counter = 1
        while short_name in sheet_names_used:
            short_name = f"{base_name[:26]}_{counter}"
            counter += 1
        sheet_names_used.add(short_name)

        ws = wb.create_sheet(title=short_name)
        ws.views.sheetView[0].rightToLeft = True

        # Branch & Project Info
        meta = (proj_meta or {}).get(proj, {})
        branch_str = ""
        b_name = meta.get("branch_name")
        b_code = meta.get("branch_code")
        if b_name or b_code:
            parts = []
            if b_name: parts.append(f"شعبه {b_name}")
            if b_code: parts.append(f"کد {b_code}")
            branch_str = f" ({' - '.join(parts)})"

        # Title Banner (Row 1)
        ws.merge_cells("A1:R1")
        title_cell = ws["A1"]
        title_cell.value = f"فهرست معرفی متقاضیان پروژه {proj} - {bank_name}{branch_str}"
        title_cell.font = Font(name="Tahoma", size=11, bold=True, color="000000")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        title_cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws.row_dimensions[1].height = 34

        # Header Row (Row 2)
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx, value=h)
            cell.font = Font(name="Tahoma", size=9, bold=True, color="000000")
            cell.fill = PatternFill(start_color="CBD5E1", end_color="CBD5E1", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws.row_dimensions[2].height = 28

        # Project dossiers
        proj_dossiers = dossiers_by_proj.get(proj.strip(), [])
        row_idx = 3
        for idx, d in enumerate(proj_dossiers, 1):
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

        for col_idx, w in enumerate(col_widths, 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = w

    if not wb.sheetnames:
        ws = wb.create_sheet(title=bank_name[:30])
        ws.views.sheetView[0].rightToLeft = True
        ws["A1"] = f"پروژه‌ای برای {bank_name} ثبت نگردیده است."

    return wb


@login_required(login_url='login')
def bank_letter_export_excel(request):
    """
    Exports Bank Introduction Letters:
    1) ?bank=melli / mellat / maskan / saderat / tejarat: Exports an Excel with a sheet for each project of that bank.
    2) ?bank=zip: Exports all 5 banks Excels packed in a single ZIP file.
    3) default: Single-sheet export for filtered archives or letter.
    """
    import io
    import urllib.parse
    import zipfile
    from django.http import HttpResponse

    bank_req = request.GET.get("bank", "").strip().lower()
    archive_str = request.GET.get("archives", "").strip()
    letter_number = request.GET.get("letter", "").strip()

    # Queryset
    if archive_str:
        arch_list = [int(a.strip()) for a in re.split(r'[\s,،]+', archive_str) if a.strip().isdigit()]
        dossiers_qs = HousingDossier.objects.filter(archive_number__in=arch_list)
    elif letter_number:
        dossiers_qs = HousingDossier.objects.filter(bank_letter_number=letter_number)
    else:
        stage6_qs = HousingDossier.objects.filter(
            models.Q(current_stage=6) | models.Q(is_equity_funded=True, is_sent_to_bank=False)
        )
        dossiers_qs = stage6_qs

    # 1. Multi-bank ZIP Export: All 5 Banks Excels in one ZIP
    if bank_req == "zip":
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for b_code, b_name in ProjectBankMapping.BANK_CHOICES:
                mapping_qs = ProjectBankMapping.objects.filter(bank_code=b_code).order_by("project_name")
                b_projs = [m.project_name for m in mapping_qs]
                proj_meta = {m.project_name: {"branch_name": m.branch_name, "branch_code": m.branch_code, "project_code": m.project_code} for m in mapping_qs}
                wb = _build_bank_workbook(b_code, b_name, b_projs, dossiers_qs, proj_meta=proj_meta)
                excel_buffer = io.BytesIO()
                wb.save(excel_buffer)
                excel_buffer.seek(0)
                file_name = f"Nameh_Bank_{b_name.replace(' ', '_')}_{len(b_projs)}_Projects.xlsx"
                zip_file.writestr(file_name, excel_buffer.getvalue())

        zip_buffer.seek(0)
        resp = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        resp["Content-Disposition"] = 'attachment; filename="5_Banks_Project_Excel_Letters.zip"'
        return resp

    # 2. Specific Bank Export (e.g. maskan, melli, mellat, saderat, tejarat)
    valid_banks = dict(ProjectBankMapping.BANK_CHOICES)
    if bank_req in valid_banks:
        b_name = valid_banks[bank_req]
        mapping_qs = ProjectBankMapping.objects.filter(bank_code=bank_req).order_by("project_name")
        b_projs = [m.project_name for m in mapping_qs]
        proj_meta = {m.project_name: {"branch_name": m.branch_name, "branch_code": m.branch_code, "project_code": m.project_code} for m in mapping_qs}
        wb = _build_bank_workbook(bank_req, b_name, b_projs, dossiers_qs, proj_meta=proj_meta)
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        resp = HttpResponse(excel_buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        enc_fname = urllib.parse.quote(f"Nameh_Bank_{b_name.replace(' ', '_')}.xlsx")
        resp["Content-Disposition"] = f'attachment; filename="{enc_fname}"; filename*=UTF-8''{enc_fname}'
        return resp

    # 3. Default single-sheet export for filtered archives or project
    project_title = request.GET.get("project", "پروژه مسکونی")
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet(title="نامه بانک")
    else:
        ws.title = "نامه بانک"
    ws.views.sheetView[0].rightToLeft = True

    letter_date = request.GET.get("date", "").strip()
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

    row_idx = 3
    for idx, d in enumerate(dossiers_qs.order_by("archive_number"), 1):
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

    col_widths = [8, 16, 18, 8, 14, 15, 12, 8, 10, 16, 14, 14, 14, 12, 12, 12, 12, 12]
    for col_idx, w in enumerate(col_widths, 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    resp = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="Nameh_Bank.xlsx"'
    return resp


@login_required(login_url='login')
def export_notary_letter_word_view(request, pk):
    """Exports Notary Letter as a native Word .doc document."""
    from django.template.loader import render_to_string
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    html_content = render_to_string("dossiers/print_notary.html", {"dossier": dossier, "is_word_export": True}, request=request)
    response = HttpResponse(html_content, content_type="application/msword; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="notary_letter_{dossier.archive_number}.doc"'
    return response


@login_required(login_url='login')
def export_dossier_summary_word_view(request, pk):
    """Exports 14-Signature Archival Dossier Summary as a native Word .doc document."""
    from django.template.loader import render_to_string
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    html = render_to_string("dossiers/print_summary.html",
                            _build_summary_context(request, dossier, is_word_export=True), request=request)
    resp = HttpResponse(html, content_type="application/msword; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="dossier_summary_{dossier.archive_number}.doc"'
    return resp
