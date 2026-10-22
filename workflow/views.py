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
from .models import HousingDossier, PreSelectedUnit, DossierAttachment, WorkflowSignatureLog, DossierFieldChangeLog, Site, Project, UserProfile

DOSSIER_FIELD_LABELS = {
    "full_name": "نام و نام خانوادگی متقاضی",
    "father_name": "نام پدر متقاضی",
    "national_id": "کد ملی متقاضی",
    "birth_date": "تاریخ تولد متقاضی",
    "spouse_full_name": "نام و نام خانوادگی همسر",
    "spouse_father_name": "نام پدر همسر",
    "spouse_national_id": "کد ملی همسر",
    "spouse_birth_date": "تاریخ تولد همسر",
    "spouse_id_number": "شماره شناسنامه همسر",
    "spouse_birth_place": "محل صدور / تولد همسر",
    "spouse_form_j_status": "وضعیت فرم ج همسر",
    "marital_status": "وضعیت تاهل",
    "is_married_confirmed": "احراز زوجیت و تایید تاهل",
    "decile": "دهک درآمدی",
    "site": "نام سایت",
    "project": "نام پروژه",
    "construction_type": "نوع ساخت",
    "block_name": "نام بلوک",
    "floor_number": "شماره طبقه",
    "unit_number": "شماره واحد",
    "unit_area": "مساحت واحد (م²)",
    "storage_number": "شماره انباری",
    "storage_area": "مساحت انباری (م²)",
    "parking_number": "شماره پارکینگ",
    "parking_area": "مساحت پارکینگ (م²)",
    "registration_section": "بخش ثبتی",
    "main_plaque": "پلاک اصلی",
    "separated_plaque": "پلاک مفروز",
    "sub_plaque": "فرعی از",
    "plot_number": "شماره قطعه",
    "base_cost_without_loan": "قیمت پایه بدون وام ۶۵۰ میلیونی (ریال)",
    "fund_loan_amount": "مبلغ وام صندوق (ریال)",
    "contractor_letter_amount": "مبلغ نامه پیمانکار (ریال)",
    "decile_loan_amount": "مبلغ وام دهک (ریال)",
    "applicant_equity": "آورده نقدی متقاضی (ریال)",
    "is_sms_sent": "وضعیت ارسال پیامک",
    "is_equity_funded": "تأیید تأمین آورده نقدی",
    "bank_letter_number": "شماره نامه بانک",
    "bank_letter_date": "تاریخ نامه بانک",
    "total_land_share": "جمع کل قدرالسهم (م²)",
    "past_years_rent": "اجاره سنوات تا پایان سال جاری (ریال)",
    "current_year_rent": "اجاره سال جاری (ریال)",
    "land_lease_year": "سال اجاره عرصه",
    "preparation_cost": "مبلغ آماده سازی (ریال)",
    "cash_preparation_amount": "مبلغ نقدی آماده سازی (ریال)",
    "non_cash_preparation_amount": "مبلغ غیرنقدی آماده سازی (ریال)",
    "is_cash_rent_confirmed": "تایید مبلغ نقدی اجاره",
    "is_decile_loan_confirmed": "تایید چک‌های وام دهک",
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
        if 0 <= num <= 21:
            cond |= models.Q(current_stage=num)
        
    if matched_stages:
        cond |= models.Q(current_stage__in=matched_stages)
        
    return cond

@login_required(login_url='login')
def dossier_list_view(request):
    """
    Dashboard list view showing housing dossiers with strict role-based stage visibility.
    - Regular experts ONLY see dossiers stuck at their assigned stage(s).
    - Admins, superusers, and Housing Chief see ALL dossiers across the 22-stage pipeline and where each dossier is stuck.
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

    dossiers = HousingDossier.objects.all()

    # Stage restriction for regular experts
    user_allowed_stages = []
    if not is_full_admin:
        if profile and profile.allowed_stages:
            user_allowed_stages = [int(s.strip()) for s in profile.allowed_stages.split(',') if s.strip().isdigit()]
        dossiers = dossiers.filter(current_stage__in=user_allowed_stages)

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

    # Compute stuck breakdown for admins to see where dossiers are stuck across all stages
    stage_breakdown = []
    if is_full_admin:
        from django.db.models import Count
        counts_by_stage = dict(HousingDossier.objects.values_list('current_stage').annotate(cnt=Count('id')))
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

    context = {
        "dossiers": dossiers,
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

    if not is_full_admin:
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

    dossier_data = {
        "archive_number": dossier.archive_number,
        "current_stage": dossier.current_stage,
        "is_locked": dossier.is_locked,
        "status": dossier.status,
        "return_reason": dossier.return_reason,
        "return_by": dossier.return_by,
        "return_from_stage": dossier.return_from_stage,
        "form": {
            "full_name": dossier.full_name,
            "father_name": dossier.father_name,
            "national_id": dossier.national_id,
            "birth_date": dossier.birth_date,
            "spouse_full_name": dossier.spouse_full_name,
            "spouse_father_name": dossier.spouse_father_name,
            "spouse_national_id": dossier.spouse_national_id,
            "spouse_birth_date": dossier.spouse_birth_date,
            "spouse_id_number": dossier.spouse_id_number,
            "spouse_birth_place": dossier.spouse_birth_place,
            "spouse_form_j_status": dossier.spouse_form_j_status,
            "marital_status": dossier.marital_status,
            "is_married_confirmed": dossier.is_married_confirmed,
            "decile": dossier.decile,
            "site": dossier.site,
            "project": dossier.project,
            "construction_type": dossier.construction_type,
            "block_name": dossier.block_name,
            "floor_number": dossier.floor_number,
            "unit_number": dossier.unit_number,
            "unit_area": float(dossier.unit_area) if dossier.unit_area else 0.0,
            "storage_number": dossier.storage_number,
            "storage_area": float(dossier.storage_area) if dossier.storage_area else 0.0,
            "parking_number": dossier.parking_number,
            "parking_area": float(dossier.parking_area) if dossier.parking_area else 0.0,
            "registration_section": dossier.registration_section,
            "main_plaque": dossier.main_plaque,
            "separated_plaque": dossier.separated_plaque,
            "sub_plaque": dossier.sub_plaque,
            "plot_number": dossier.plot_number,
            "base_cost_without_loan": dossier.base_cost_without_loan,
            "fund_loan_amount": dossier.fund_loan_amount,
            "contractor_letter_amount": dossier.contractor_letter_amount,
            "decile_loan_amount": dossier.decile_loan_amount,
            "applicant_equity": dossier.applicant_equity,
            "is_sms_sent": dossier.is_sms_sent,
            "is_equity_funded": dossier.is_equity_funded,
            "bank_letter_number": dossier.bank_letter_number,
            "bank_letter_date": dossier.bank_letter_date,
            "total_land_share": float(dossier.total_land_share) if dossier.total_land_share else None,
            "past_years_rent": dossier.past_years_rent,
            "current_year_rent": dossier.current_year_rent,
            "land_lease_year": dossier.land_lease_year,
            "preparation_cost": dossier.preparation_cost,
            "cash_preparation_amount": dossier.cash_preparation_amount,
            "non_cash_preparation_amount": dossier.non_cash_preparation_amount,
            "is_cash_rent_confirmed": dossier.is_cash_rent_confirmed,
            "is_decile_loan_confirmed": dossier.is_decile_loan_confirmed,
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
    for stg_num in range(dossier.current_stage):
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
    dossier_data["current_role"] = dossier.current_role
    dossier_data["current_stage_title"] = dossier.current_stage_title

    context = {
        "dossier": dossier,
        "attachments": attachments,
        "audit_logs": audit_logs,
        "field_changes": dossier.field_changes.all().order_by("-timestamp")[:500],
        "archive_number": dossier.archive_number,
        "dossier_json": json.dumps(dossier_data, ensure_ascii=False),
        "user_can_action": user_can_action,
        "is_chief": is_chief,
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
            if 0 <= stg <= 21:
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
        "full_name", "father_name", "birth_date",
        "spouse_full_name", "spouse_father_name", "spouse_national_id",
        "spouse_birth_date", "spouse_id_number", "spouse_birth_place",
        "spouse_form_j_status", "marital_status",
        "site", "project", "construction_type", "block_name", "registration_section",
        "bank_letter_number", "bank_letter_date", "land_lease_year"
    ]:
        if field in data and data[field] is not None:
            parsed_updates[field] = str(data[field]).strip()

    # Integer fields
    for field in [
        "decile", "floor_number", "unit_number", "storage_number", "parking_number",
        "main_plaque", "separated_plaque", "sub_plaque", "plot_number",
        "base_cost_without_loan", "fund_loan_amount", "contractor_letter_amount",
        "decile_loan_amount", "past_years_rent", "current_year_rent",
        "preparation_cost", "cash_preparation_amount", "non_cash_preparation_amount"
    ]:
        if field in data:
            val = data[field]
            if val is None or val == "":
                if field in ["storage_number", "parking_number", "main_plaque", "separated_plaque", "sub_plaque", "plot_number"]:
                    parsed_updates[field] = None
                else:
                    parsed_updates[field] = 0
            else:
                try:
                    parsed_updates[field] = int(val)
                except (ValueError, TypeError):
                    pass

    # Decimal / Float fields
    for field in ["unit_area", "storage_area", "parking_area", "total_land_share"]:
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
    for field in ["is_sms_sent", "is_equity_funded", "is_cash_rent_confirmed", "is_decile_loan_confirmed", "is_married_confirmed"]:
        if field in data:
            val = data[field]
            parsed_updates[field] = bool(val) if not isinstance(val, str) else val.lower() in ("true", "1")

    # Detect field differences and construct audit change logs
    change_logs_to_create = []
    for field, new_val in parsed_updates.items():
        old_val = getattr(dossier, field, None)

        # Normalize values for fair diff comparison
        old_repr = "" if old_val is None else str(old_val).strip()
        new_repr = "" if new_val is None else str(new_val).strip()

        # For floats/decimals, normalize precision
        if field in ["unit_area", "storage_area", "parking_area", "total_land_share"]:
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
    Supports all 22 stages (0 to 21).
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

    if next_stage <= 21:
        dossier.current_stage = next_stage
        dossier.status = "IN_PROGRESS"
        dossier.return_reason = ""
        dossier.return_by = ""
        dossier.return_from_stage = None
        action = "SIGN"
        action_label = "تایید و امضای الکترونیکی"
        to_stage_str = f"مرحله {next_stage}: {dossier.STAGE_ROLES.get(next_stage, ('','',f'مرحله {next_stage}'))[2]}"
    else:
        dossier.is_locked = True
        dossier.status = "COMPLETED"
        action = "ARCHIVE"
        action_label = "بایگانی قطعی پرونده"
        to_stage_str = "بایگانی نهایی (مختومه)"

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

    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "پرونده بایگانی‌شده قابل بازگشت نیست."}, status=400)

    # Permission check for active stage
    profile = getattr(request.user, 'profile', None)
    user_can_action = request.user.is_superuser or (profile and profile.is_housing_chief) or (profile and profile.can_action_stage(dossier.current_stage))
    if not user_can_action:
        return JsonResponse({
            "status": "error",
            "message": f"شما دسترسی مجاز برای بازگردانی پرونده از مرحله {dossier.current_stage} را ندارید. این اقدام مختص «{dossier.current_role}» یا رئیس مسکن می‌باشد."
        }, status=403)

    try:
        body_data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body_data = {}

    target_stage_val = body_data.get("target_stage") or request.POST.get("target_stage")
    try:
        target_stage = int(target_stage_val)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "مرحله مقصد نامعتبر است."}, status=400)

    notes = (body_data.get("notes") or request.POST.get("notes", "")).strip()
    if len(notes) < 5:
        return JsonResponse({"status": "error", "message": "ثبت توضیحات دلیل برگشت الزامی است (حداقل ۵ کاراکتر)."}, status=400)

    current_idx = dossier.current_stage

    if target_stage >= current_idx or target_stage < 0:
        return JsonResponse({"status": "error", "message": "مرحله برگشت باید از مرحله فعلی کوچکتر و حداقل ۰ باشد."}, status=400)

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
            "spouse_full_name": unit.spouse_full_name,
            "spouse_father_name": unit.spouse_father_name,
            "spouse_national_id": unit.spouse_national_id,
            "spouse_birth_date": unit.spouse_birth_date,
            "spouse_id_number": unit.spouse_id_number,
            "spouse_birth_place": unit.spouse_birth_place,
            "spouse_form_j_status": unit.spouse_form_j_status,
            "marital_status": unit.marital_status,
            "is_married_confirmed": unit.is_married_confirmed,
            "decile": unit.decile,
            "site": unit.site.name if unit.site else "",
            "project": str(unit.project) if unit.project else "",
            "construction_type": unit.construction_type,
            "block_name": unit.block_name,
            "floor_number": unit.floor_number,
            "unit_number": unit.unit_number,
            "unit_area": str(unit.unit_area),
            "storage_number": unit.storage_number,
            "storage_area": str(unit.storage_area),
            "parking_number": unit.parking_number,
            "parking_area": str(unit.parking_area),
            "base_cost_without_loan": unit.base_cost_without_loan,
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


@login_required(login_url='login')
def dossier_summary_print_view(request, pk):
    """
    Print-ready view for Stage 24 (Final Archival Summary Sheet).
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    return render(request, "dossiers/print_summary.html", {"dossier": dossier})


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
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    is_chief_or_admin = request.user.is_superuser or (profile and profile.is_housing_chief)
    user_can_action = is_chief_or_admin or (profile and profile.can_action_stage(dossier.current_stage))

    if not user_can_action:
        return JsonResponse({"status": "error", "message": "عدم دسترسی اقدام: شما مجوز بارگذاری یا تغییر اسناد در مرحله جاری را ندارید."}, status=403)

    # 3. Stage-gated upload check: only Stages 0, 1, 9, 13, 18 are designated scanning stages
    ALLOWED_STAGES = [0, 1, 9, 13, 18]
    if not is_chief_or_admin and dossier.current_stage not in ALLOWED_STAGES:
        return JsonResponse({
            "status": "error",
            "message": f"بارگذاری مدارک در مرحله {dossier.current_stage} مجاز نمی‌باشد. بارگذاری اسناد صرفاً در مراحل ۰، ۱، ۹، ۱۳ و ۱۸ امکان‌پذیر است."
        }, status=400)
    
    title = request.POST.get("title", "").strip() or "مدرک بارگذاری‌شده"
    doc_type = request.POST.get("doc_type", "OTHER")
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
            stage_pills = [{"id": "all", "title": "کلیه ۲۲ مرحله (اختیارات تام)"}]
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
    stage_experts_count = {i: 0 for i in range(22)}
    for ud in users_data:
        raw = ud.get("allowed_stages", "")
        if raw == "all" or ud.get("is_housing_chief") or ud.get("is_superuser"):
            for i in range(22):
                stage_experts_count[i] += 1
        else:
            nums = [int(s.strip()) for s in raw.split(',') if s.strip().isdigit()]
            for s in nums:
                if 0 <= s <= 21:
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
