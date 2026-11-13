import json
import re
import jdatetime
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .field_permissions import (
    can_user_manage_stage17_18_tracking as can_manage_stage17_18_tracking,
    get_stage17_18_allowed_stages_set,
)
from .models import (
    DirectorateShipment,
    HousingDossier,
    WorkflowSignatureLog,
)


SHIPMENT_TYPE_META = {
    "LOAN": {
        "required_stage": 17,
        "title": "تسهیلات چک",
        "full_label": "تسهیلات چک (مرحله ۱۷)",
        "bool_field": "is_loan_sent_to_directorate",
        "date_field": "loan_directorate_sent_date",
        "by_field": "loan_directorate_sent_by",
        "at_field": "loan_directorate_sent_at",
        "fk_field": "loan_directorate_shipment",
    },
    "PREP": {
        "required_stage": 18,
        "title": "آماده‌سازی",
        "full_label": "آماده‌سازی و اجاره (مرحله ۱۸)",
        "bool_field": "is_prep_sent_to_directorate",
        "date_field": "prep_directorate_sent_date",
        "by_field": "prep_directorate_sent_by",
        "at_field": "prep_directorate_sent_at",
        "fk_field": "prep_directorate_shipment",
    },
}


def _resolve_actor(user):
    profile = getattr(user, "profile", None)
    actor_name = (profile.full_name if profile and profile.full_name else user.get_full_name() or user.username)
    actor_role = (profile.role_title if profile and profile.role_title else "کارشناس / مدیر")
    return actor_name, actor_role


def _today_jalali_date() -> str:
    return jdatetime.datetime.fromgregorian(datetime=timezone.localtime(timezone.now())).strftime("%Y/%m/%d")


def _shipment_dossier_payload(d: HousingDossier, shipment_type: str = "LOAN") -> dict:
    loan_cnt = len(d.get_check_entries()) if hasattr(d, "get_check_entries") else (d.check_count or 0)
    prep_cnt = len(d.get_preparation_check_entries()) if hasattr(d, "get_preparation_check_entries") else (d.preparation_check_count or 0)
    is_prep = shipment_type == "PREP"
    type_check_cnt = prep_cnt if is_prep else loan_cnt
    stage_visit_date = (
        (d.prep_visit_date_display or d.visit_date_display)
        if is_prep
        else (d.loan_visit_date_display or d.visit_date_display)
    )
    contractor_display = f"{d.project} ({d.site})" if (d.project and d.site) else (d.project or d.site or "-")
    return {
        "id": d.id,
        "archive_number": d.archive_number,
        "full_name": d.full_name,
        "national_id": d.national_id,
        "applicant_phone": d.applicant_phone or "—",
        "project": d.project or "—",
        "site": d.site or "—",
        "contractor_display": contractor_display,
        "current_stage": d.current_stage,
        "visit_date": stage_visit_date,
        "loan_visit_date": d.loan_visit_date_display,
        "prep_visit_date": d.prep_visit_date_display,
        "is_loan_sent_to_directorate": d.is_loan_sent_to_directorate,
        "loan_directorate_sent_date": d.loan_directorate_sent_date_display,
        "is_prep_sent_to_directorate": d.is_prep_sent_to_directorate,
        "prep_directorate_sent_date": d.prep_directorate_sent_date_display,
        "check_count_type": type_check_cnt,
        "check_count_total": loan_cnt + prep_cnt,
    }


def _extract_archive_numbers(payload: dict) -> list[int]:
    raw_nums = payload.get("archive_numbers") or payload.get("recordIds") or []
    result = []
    for val in raw_nums:
        try:
            num = int(val)
            if num not in result:
                result.append(num)
        except (TypeError, ValueError):
            continue
    return result


@login_required(login_url="login")
def directorate_shipments_list_view(request):
    """
    History page of all LOAN (Stage 17) & PREP (Stage 18) shipment batches sent to راه و شهرسازی.
    Strictly accessible only to alireza_nazari and dedicated Stage 17/18 experts.
    """
    if not can_manage_stage17_18_tracking(request.user):
        return redirect("dossier_list")

    allowed_stages = get_stage17_18_allowed_stages_set(request.user)
    allowed_types = []
    if 17 in allowed_stages:
        allowed_types.append("LOAN")
    if 18 in allowed_stages:
        allowed_types.append("PREP")

    type_filter = str(request.GET.get("type") or "ALL").strip().upper()
    if type_filter not in ("ALL", "LOAN", "PREP"):
        type_filter = "ALL"

    query = str(request.GET.get("q") or "").strip()

    base_qs = DirectorateShipment.objects.filter(
        shipment_type__in=allowed_types
    ).prefetch_related("loan_dossiers", "prep_dossiers").order_by("-created_at", "-id")

    loan_count = base_qs.filter(shipment_type="LOAN").count()
    prep_count = base_qs.filter(shipment_type="PREP").count()
    total_count = base_qs.count()

    filtered_qs = base_qs
    if type_filter in ("LOAN", "PREP") and type_filter in allowed_types:
        filtered_qs = filtered_qs.filter(shipment_type=type_filter)

    if query:
        terms = [t.strip() for t in re.split(r"[,،\n]+", query) if t.strip()]
        term_q = models.Q()
        for term in terms:
            sub_q = (
                models.Q(shipment_code__icontains=term)
                | models.Q(note__icontains=term)
                | models.Q(created_by__icontains=term)
                | models.Q(sent_date__icontains=term)
                | models.Q(loan_dossiers__national_id__icontains=term)
                | models.Q(loan_dossiers__full_name__icontains=term)
                | models.Q(prep_dossiers__national_id__icontains=term)
                | models.Q(prep_dossiers__full_name__icontains=term)
            )
            if term.isdigit():
                sub_q |= models.Q(loan_dossiers__archive_number=int(term)) | models.Q(prep_dossiers__archive_number=int(term))
            term_q |= sub_q
        filtered_qs = filtered_qs.filter(term_q).distinct()

    shipment_cards = []
    for s in filtered_qs:
        meta = SHIPMENT_TYPE_META.get(s.shipment_type, SHIPMENT_TYPE_META["LOAN"])
        dossiers = list(
            (s.prep_dossiers if s.shipment_type == "PREP" else s.loan_dossiers).all()
        )
        dossiers.sort(key=lambda d: (d.current_stage, d.archive_number))
        shipment_cards.append({
            "id": s.id,
            "shipment_code": s.shipment_code,
            "shipment_type": s.shipment_type,
            "shipment_type_label": meta["full_label"],
            "shipment_short_label": meta["title"],
            "sent_date": s.sent_date or s.created_at_jalali,
            "created_at_jalali": s.created_at_jalali,
            "created_by": s.created_by,
            "note": s.note,
            "record_count": len(dossiers),
            "print_url": reverse("directorate_shipment_print", kwargs={"shipment_id": s.id}),
            "dossiers": [_shipment_dossier_payload(d, shipment_type=s.shipment_type) for d in dossiers],
        })

    return render(
        request,
        "dossiers/shipments_history.html",
        {
            "shipments": shipment_cards,
            "total_count": total_count,
            "loan_count": loan_count,
            "prep_count": prep_count,
            "type_filter": type_filter,
            "allowed_types": allowed_types,
            "query": query,
        },
    )


@login_required(login_url="login")
@require_POST
def directorate_shipment_create_api(request):
    """Create a LOAN or PREP DirectorateShipment batch for selected dossiers (no stage-order block)."""
    if not can_manage_stage17_18_tracking(request.user):
        return JsonResponse({"status": "error", "message": "دسترسی مجاز به ایجاد محموله راه و شهرسازی ندارید."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "message": "ساختار درخواست نامعتبر است."}, status=400)

    shipment_type = str(payload.get("shipment_type") or "").strip().upper()
    if shipment_type not in SHIPMENT_TYPE_META:
        return JsonResponse({"status": "error", "message": "نوع محموله باید «تسهیلات چک (LOAN)» یا «آماده‌سازی (PREP)» باشد."}, status=400)

    meta = SHIPMENT_TYPE_META[shipment_type]
    allowed_stages = get_stage17_18_allowed_stages_set(request.user)
    if meta["required_stage"] not in allowed_stages:
        return JsonResponse(
            {"status": "error", "message": f"دسترسی به ارسال محموله {meta['title']} ندارید."},
            status=403,
        )

    archive_numbers = _extract_archive_numbers(payload)
    if not archive_numbers:
        return JsonResponse({"status": "error", "message": "حداقل یک پرونده باید انتخاب شود."}, status=400)

    sent_date = str(payload.get("sent_date") or "").strip() or _today_jalali_date()
    note = str(payload.get("note") or "").strip()[:300]
    actor_name, actor_role = _resolve_actor(request.user)
    now_ts = timezone.now()

    with transaction.atomic():
        locked_qs = HousingDossier.objects.select_for_update().filter(archive_number__in=archive_numbers)
        dossiers = list(locked_qs.order_by("current_stage", "archive_number"))
        if not dossiers:
            return JsonResponse({"status": "error", "message": "پرونده‌ای با شماره‌های انتخابی یافت نشد."}, status=404)

        already_shipped = []
        locked_closed = []
        fk_id_attr = f"{meta['fk_field']}_id"
        for d in dossiers:
            if d.is_locked or d.status in ("REJECTED_RED", "DELETED"):
                locked_closed.append(f"{d.full_name} ({d.archive_number})")
            elif getattr(d, meta["bool_field"]) or getattr(d, fk_id_attr):
                already_shipped.append(f"{d.full_name} ({d.national_id})")

        if locked_closed:
            return JsonResponse(
                {"status": "error", "message": "پرونده‌های مختومه یا حذفی قابل ارسال نیستند: " + "، ".join(locked_closed)},
                status=400,
            )
        if already_shipped:
            return JsonResponse(
                {"status": "error", "message": f"ارسال «{meta['title']}» برای پرونده‌های زیر قبلاً ثبت شده است: " + "، ".join(already_shipped)},
                status=400,
            )

        shipment = DirectorateShipment.objects.create(
            shipment_type=shipment_type,
            sent_date=sent_date,
            note=note,
            created_by_user=request.user,
            created_by=actor_name,
        )

        logs_to_create = []
        for d in dossiers:
            setattr(d, meta["bool_field"], True)
            setattr(d, meta["date_field"], sent_date)
            setattr(d, meta["by_field"], actor_name)
            setattr(d, meta["at_field"], now_ts)
            setattr(d, meta["fk_field"], shipment)
            d.save(update_fields=[
                meta["bool_field"],
                meta["date_field"],
                meta["by_field"],
                meta["at_field"],
                meta["fk_field"],
                "updated_at",
            ])
            logs_to_create.append(
                WorkflowSignatureLog(
                    dossier=d,
                    from_stage=f"مرحله {d.current_stage}: {d.current_stage_title}",
                    to_stage=f"مرحله {d.current_stage}: {d.current_stage_title}",
                    actor=actor_name,
                    role=actor_role,
                    action="DIRECTORATE_SHIP",
                    action_label=f"ارسال {meta['title']} به راه و شهرسازی ({shipment.shipment_code})",
                    signature_hash="",
                    notes=f"بخش «{meta['title']}» در محموله {shipment.shipment_code} به تاریخ {sent_date} به راه و شهرسازی ارسال شد." + (f" ({note})" if note else ""),
                )
            )
        WorkflowSignatureLog.objects.bulk_create(logs_to_create)

    print_url = reverse("directorate_shipment_print", kwargs={"shipment_id": shipment.id})
    return JsonResponse(
        {
            "status": "success",
            "message": f"محموله «{meta['title']}» ({shipment.shipment_code}) شامل {len(dossiers)} پرونده با موفقیت ثبت شد.",
            "print_url": print_url,
            "shipment": {
                "id": shipment.id,
                "shipment_type": shipment.shipment_type,
                "shipment_type_label": meta["full_label"],
                "shipment_code": shipment.shipment_code,
                "sent_date": shipment.sent_date,
                "created_at_jalali": shipment.created_at_jalali,
                "created_by": shipment.created_by,
                "note": shipment.note,
                "record_count": len(dossiers),
                "print_url": print_url,
                "dossiers": [_shipment_dossier_payload(d, shipment_type=shipment_type) for d in dossiers],
            },
        }
    )


@login_required(login_url="login")
def directorate_shipment_print_view(request, shipment_id: int):
    """Render official RTL A4 manifest of a LOAN or PREP DirectorateShipment batch."""
    if not can_manage_stage17_18_tracking(request.user):
        return redirect("dossier_list")

    shipment = get_object_or_404(DirectorateShipment, id=shipment_id)
    meta = SHIPMENT_TYPE_META.get(shipment.shipment_type, SHIPMENT_TYPE_META["LOAN"])
    allowed_stages = get_stage17_18_allowed_stages_set(request.user)
    if meta["required_stage"] not in allowed_stages:
        return redirect("dossier_list")

    rel = shipment.prep_dossiers if shipment.shipment_type == "PREP" else shipment.loan_dossiers
    dossiers = list(rel.all().order_by("current_stage", "archive_number"))
    rows = [_shipment_dossier_payload(d, shipment_type=shipment.shipment_type) for d in dossiers]
    return render(
        request,
        "dossiers/print_directorate_shipment.html",
        {
            "shipment": shipment,
            "shipment_type_label": meta["full_label"],
            "shipment_short_label": meta["title"],
            "rows": rows,
            "print_date": _today_jalali_date(),
        },
    )
