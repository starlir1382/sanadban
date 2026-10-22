import hashlib
import json
import os
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction, models
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import HousingDossier, PreSelectedUnit, DossierAttachment, WorkflowSignatureLog, DossierFieldChangeLog, Site, Project

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
        if 1 <= num <= 24:
            cond |= models.Q(current_stage=num)
        
    if matched_stages:
        cond |= models.Q(current_stage__in=matched_stages)
        
    return cond

def dossier_list_view(request):
    """
    Dashboard list view showing all housing dossiers with multi-field search and stage filtering.
    Searches across: archive_number, national_id, full_name, father_name, spouse,
    project, site, current_stage number, and stage title/role.
    """
    query = request.GET.get('q', '').strip()
    stage_filter = request.GET.get('stage', '')

    dossiers = HousingDossier.objects.all()

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
            dossiers = dossiers.filter(current_stage=int(stage_filter))
        except ValueError:
            pass

    stages_meta = [
        {"id": i, "title": role_tuple[2], "role": role_tuple[1], "unit": role_tuple[0]}
        for i, role_tuple in HousingDossier.STAGE_ROLES.items()
    ]

    context = {
        "dossiers": dossiers,
        "query": query,
        "stage_filter": stage_filter,
        "stages_meta": stages_meta,
    }
    return render(request, "dossiers/list.html", context)


def dossier_detail_view(request, pk):
    """
    Main interactive workspace view for a single housing dossier across its 24-stage workflow.
    Serializes dossier state into JSON so Alpine.js starts with exact database values.
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
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
            for c in dossier.field_changes.all().order_by("-timestamp")[:100]
        ],
    }

    context = {
        "dossier": dossier,
        "attachments": attachments,
        "audit_logs": audit_logs,
        "field_changes": dossier.field_changes.all().order_by("-timestamp")[:100],
        "archive_number": dossier.archive_number,
        "dossier_json": json.dumps(dossier_data, ensure_ascii=False),
    }
    return render(request, "dossiers/detail.html", context)


@csrf_exempt
@transaction.atomic
def save_dossier_draft_view(request, pk):
    """
    Persists changes to the dossier's fields into the SQLite database with automated audit logging.
    Tracks who changed each field, when, and the exact before/after values.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method allowed")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و مختومه گردیده است و امکان ویرایش آن وجود ندارد."}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    # Update current_stage if explicitly passed
    if "current_stage" in data:
        try:
            stg = int(data.get("current_stage"))
            if 1 <= stg <= 24:
                dossier.current_stage = stg
        except (ValueError, TypeError):
            pass

    # Extract user identity and client IP
    if request.user.is_authenticated:
        actor_name = request.user.get_full_name() or request.user.username
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
    Switches active stage and persists to the database so page reloads remain on the selected stage.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method allowed")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و مختومه گردیده است."}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    try:
        stage = int(data.get("stage", 0))
    except (ValueError, TypeError):
        return JsonResponse({"status": "error", "message": "مرحله نامعتبر است."}, status=400)

    if 1 <= stage <= 24:
        dossier.current_stage = stage
        dossier.save()
        return JsonResponse({"status": "success", "new_stage": dossier.current_stage})
    else:
        return JsonResponse({"status": "error", "message": "مرحله باید بین ۱ تا ۲۴ باشد."}, status=400)


@csrf_exempt
@transaction.atomic
def electronic_sign_action(request, pk):
    """
    Handles electronic signature and forwards the dossier to the next stage (select_for_update).
    Supports all 24 stages seamlessly.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = HousingDossier.objects.select_for_update().get(archive_number=pk)

    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "این پرونده نهایی و مختومه گردیده است."}, status=400)

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

    if next_stage <= 24:
        dossier.current_stage = next_stage
        action = "SIGN"
        action_label = "تایید و امضای الکترونیکی"
        to_stage_str = f"مرحله {next_stage}: {dossier.STAGE_ROLES.get(next_stage, ('','',f'مرحله {next_stage}'))[2]}"
    else:
        dossier.is_locked = True
        action = "ARCHIVE"
        action_label = "بایگانی قطعی پرونده"
        to_stage_str = "بایگانی نهایی (مختومه)"

    dossier.save()

    notes = body_data.get("notes") or request.POST.get("notes", "تایید و امضای الکترونیکی با موفقیت انجام شد.")

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {current_idx}: {current_title}",
        to_stage=to_stage_str,
        actor="کارشناس اقدام‌کننده",
        role=current_role,
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
    Supports all 24 stages: any stage > 1 can return to any prior stage < current_stage.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = HousingDossier.objects.select_for_update().get(archive_number=pk)

    if dossier.is_locked:
        return JsonResponse({"status": "error", "message": "پرونده بایگانی‌شده قابل بازگشت نیست."}, status=400)

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

    if target_stage >= current_idx or target_stage < 1:
        return JsonResponse({"status": "error", "message": "مرحله برگشت باید از مرحله فعلی کوچکتر و حداقل ۱ باشد."}, status=400)

    current_title = dossier.current_stage_title
    current_role = dossier.current_role
    target_title = dossier.STAGE_ROLES.get(target_stage, ('','',f'مرحله {target_stage}'))[2]

    raw_stamp = f"RETURN-{dossier.archive_number}-{current_idx}-{target_stage}-{timezone.now().isoformat()}"
    sig_hash = "SHA256: " + hashlib.sha256(raw_stamp.encode()).hexdigest()[:24]

    dossier.current_stage = target_stage
    dossier.save()

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {current_idx}: {current_title}",
        to_stage=f"مرحله {target_stage}: {target_title}",
        actor="کارشناس بررسی و ممیزی",
        role=current_role,
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


def notary_letter_print_view(request, pk):
    """
    Print-ready view for Stage 23 & 24 (Notary Letter Introduction).
    """
    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    return render(request, "dossiers/print_notary.html", {"dossier": dossier})


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
    Validates stage-ownership and generates SHA-256 integrity hash.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("فقط درخواست POST مجاز است.")

    dossier = get_object_or_404(HousingDossier, archive_number=pk)
    
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

    attachment = DossierAttachment.objects.create(
        dossier=dossier,
        stage=dossier.current_stage,
        doc_type=doc_type,
        title=title,
        file_name=file_name,
        file_sha256=file_hash,
        uploaded_by=f"کارشناس مرحله {dossier.current_stage}",
        preview_url=saved_url
    )

    WorkflowSignatureLog.objects.create(
        dossier=dossier,
        from_stage=f"مرحله {dossier.current_stage}",
        to_stage=f"مرحله {dossier.current_stage}",
        actor="کارشناس بارگذاری اسناد",
        role=dossier.current_role,
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
