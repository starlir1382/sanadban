"""
workflow/land_rates_views.py
Admin views and APIs for Land Rates & Section 9 Valuation Management.
Provides:
1. Dedicated Admin Page with search, project filter, and interactive inline editing.
2. Excel Upload & Import (re-run whenever rates change).
3. Excel Export of current rates.
4. Bulk Apply to existing dossiers with matching renovation_code.
5. Live calculation API for single dossier view.
"""
import json
import openpyxl
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, models
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, FileResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import LandRate, HousingDossier, UserProfile
from .land_rates import (
    LAND_LEASE_YEAR,
    normalize_code,
    compute_land_values,
    get_rate,
    apply_land_calculation,
    read_rates_from_excel,
    reset_cache,
    _dec,
)


def _check_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and (profile.is_housing_chief or profile.allowed_stages == "all"))


@login_required(login_url="login")
def land_rates_admin_view(request):
    """Admin dashboard for viewing, searching, and editing Land Rates."""
    if not _check_admin(request.user):
        messages.error(request, "دسترسی غیرمجاز: این بخش صرفاً ویژه مدیران ارشد سیستم و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")

    q = request.GET.get("q", "").strip()
    project_filter = request.GET.get("project", "").strip()

    rates_qs = LandRate.objects.all()

    if q:
        norm_q = normalize_code(q)
        rates_qs = rates_qs.filter(
            Q(renovation_code__icontains=norm_q)
            | Q(renovation_code__icontains=q)
            | Q(project_name__icontains=q)
            | Q(block_name__icontains=q)
            | Q(plot_number__icontains=q)
        )

    if project_filter:
        rates_qs = rates_qs.filter(project_name=project_filter)

    # Statistics
    total_rates = LandRate.objects.count()
    distinct_projects = list(
        LandRate.objects.values_list("project_name", flat=True).distinct().order_by("project_name")
    )
    dossiers_with_code = HousingDossier.objects.exclude(renovation_code="").count()

    # Pagination: 50 per page
    paginator = Paginator(rates_qs, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "paginator": paginator,
        "total_rates": total_rates,
        "total_projects": len(distinct_projects),
        "dossiers_with_code": dossiers_with_code,
        "distinct_projects": distinct_projects,
        "selected_project": project_filter,
        "q": q,
        "base_year": LAND_LEASE_YEAR,
        "user_profile": getattr(request.user, "profile", None),
    }
    return render(request, "admin/land_rates.html", context)


@login_required(login_url="login")
@require_http_methods(["POST"])
def land_rates_update_api(request, pk):
    """AJAX API to update a single LandRate row from the admin table."""
    if not _check_admin(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز."}, status=403)

    rate = get_object_or_404(LandRate, pk=pk)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    fields_to_update = []
    if "share_land" in data:
        rate.share_land = _dec(data["share_land"])
        fields_to_update.append("share_land")
    if "share_common" in data:
        rate.share_common = _dec(data["share_common"])
        fields_to_update.append("share_common")
    if "rent_current_per_m2" in data:
        rate.rent_current_per_m2 = _dec(data["rent_current_per_m2"])
        fields_to_update.append("rent_current_per_m2")
    if "rent_to_date_per_m2" in data:
        rate.rent_to_date_per_m2 = _dec(data["rent_to_date_per_m2"])
        fields_to_update.append("rent_to_date_per_m2")
    if "prep_per_m2" in data:
        rate.prep_per_m2 = _dec(data["prep_per_m2"])
        fields_to_update.append("prep_per_m2")
    if "block_name" in data:
        rate.block_name = str(data["block_name"]).strip()
        fields_to_update.append("block_name")
    if "plot_number" in data:
        rate.plot_number = str(data["plot_number"]).strip()
        fields_to_update.append("plot_number")

    if fields_to_update:
        rate.save(update_fields=fields_to_update + ["updated_at"])
        reset_cache()

    return JsonResponse({
        "success": True,
        "message": f"نرخ کد نوسازی «{rate.renovation_code}» با موفقیت بروز شد.",
        "rate": {
            "id": rate.pk,
            "renovation_code": rate.renovation_code,
            "share_land": str(rate.share_land),
            "share_common": str(rate.share_common),
            "rent_current_per_m2": int(rate.rent_current_per_m2),
            "rent_to_date_per_m2": int(rate.rent_to_date_per_m2),
            "prep_per_m2": int(rate.prep_per_m2),
        }
    })


@login_required(login_url="login")
@require_http_methods(["POST"])
def land_rates_upload_excel_api(request):
    """Upload and parse an Excel sheet of land rates, inserting/updating in bulk."""
    if not _check_admin(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز."}, status=403)

    excel_file = request.FILES.get("excel_file") or request.FILES.get("file")
    if not excel_file:
        return JsonResponse({"success": False, "error": "هیچ فایل اکسلی ارسال نشد."}, status=400)

    try:
        rows, problems = read_rates_from_excel(excel_file)
    except Exception as exc:
        return JsonResponse({"success": False, "error": f"خطا در خواندن فایل اکسل: {str(exc)}"}, status=400)

    if not rows:
        return JsonResponse({"success": False, "error": "هیچ ردیف معتبری در فایل اکسل یافت نشد."}, status=400)

    LandRate.objects.bulk_create(
        [LandRate(**r) for r in rows],
        batch_size=500,
        update_conflicts=True,
        unique_fields=["renovation_code"],
        update_fields=[
            "project_name", "plot_number", "block_name", "share_land", "share_common",
            "rent_current_per_m2", "rent_to_date_per_m2", "prep_per_m2",
        ],
    )
    reset_cache()

    return JsonResponse({
        "success": True,
        "message": f"با موفقیت {len(rows)} نرخ نوسازی وارد یا بروزرسانی شدند.",
        "count": len(rows),
        "total_in_db": LandRate.objects.count(),
        "warnings": problems[:15],
    })


@login_required(login_url="login")
def land_rates_export_excel(request):
    """Export current Land Rates database as a formatted Excel spreadsheet."""
    if not _check_admin(request.user):
        return HttpResponseForbidden("دسترسی غیرمجاز")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "نرخ‌های مصوب عرصه"
    ws.views.sheetView[0].rightToLeft = True

    headers = [
        "ردیف", "نام پروژه", "قطعه", "نام بلوک", "کد نوسازی",
        "قدرالسهم از عرصه", "قدرالسهم از مشاع", "مجموع ضریب قدرالسهم",
        "مبلغ اجاره یک متر سال جاری (ریال)", "علی‌الحساب اجاره تا پایان سال جاری (ریال)",
        "مبلغ یک متر هزینه آماده‌سازی (ریال)", "تاریخ آخرین بروزرسانی"
    ]
    ws.append(headers)

    header_fill = openpyxl.styles.PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = openpyxl.styles.Font(color="FFFFFF", bold=True, size=10)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")

    rates = LandRate.objects.all().order_by("project_name", "block_name", "renovation_code")
    for idx, r in enumerate(rates, start=1):
        tot_coeff = float(r.share_land + r.share_common)
        row = [
            idx,
            r.project_name,
            r.plot_number,
            r.block_name,
            r.renovation_code,
            float(r.share_land),
            float(r.share_common),
            tot_coeff,
            int(r.rent_current_per_m2),
            int(r.rent_to_date_per_m2),
            int(r.prep_per_m2),
            r.updated_at.strftime("%Y/%m/%d %H:%M") if r.updated_at else "",
        ]
        ws.append(row)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="MaskanYar_Land_Rates.xlsx"'
    wb.save(response)
    return response


@login_required(login_url="login")
@require_http_methods(["POST"])
def land_rates_bulk_apply_api(request):
    """
    Bulk recalculates Section 9 fields for dossiers using:
    1. کد نوسازی (if present)
    2. Or پروژه + شماره قطعه (extracted from plot_number or project title)
    """
    if not _check_admin(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز."}, status=403)

    project_filter = request.POST.get("project") or ""
    only_empty = request.POST.get("only_empty", "false").lower() in ("true", "1")

    qs = HousingDossier.objects.filter(is_locked=False).filter(
        Q(renovation_code__gt="") | Q(project__gt="")
    )
    if project_filter:
        qs = qs.filter(project=project_filter)

    total_matched = qs.count()
    if total_matched == 0:
        return JsonResponse({
            "success": True,
            "updated_count": 0,
            "message": "هیچ پرونده بازی یافت نشد."
        })

    updated_count = 0
    chunk_size = 100
    fields_to_save = [
        "total_land_share", "current_year_rent", "past_years_rent",
        "preparation_cost", "land_lease_year", "renovation_code",
        "plot_number", "block_name"
    ]

    all_pks = list(qs.values_list("id", flat=True))
    for i in range(0, len(all_pks), chunk_size):
        chunk_pks = all_pks[i : i + chunk_size]
        chunk_dossiers = list(HousingDossier.objects.filter(id__in=chunk_pks))
        batch_to_update = []
        for d in chunk_dossiers:
            if only_empty and d.total_land_share and d.current_year_rent and d.current_year_rent > 0:
                continue
            if apply_land_calculation(d):
                batch_to_update.append(d)
                updated_count += 1

        if batch_to_update:
            with transaction.atomic():
                HousingDossier.objects.bulk_update(batch_to_update, fields=fields_to_save)

    return JsonResponse({
        "success": True,
        "updated_count": updated_count,
        "total_matched": total_matched,
        "message": f"محاسبات بخش ۹ برای {updated_count} پرونده بر اساس نرخ مصوب قطعه و پروژه با موفقیت اعمال و ذخیره شد."
    })


@login_required(login_url="login")
def calculate_land_rates_api(request):
    """
    API endpoint to return calculated Section 9 fields on the fly.
    Accepts GET or POST: code, project, plot, block, net, storage, parking.
    """
    code = request.GET.get("code") or request.POST.get("code") or ""
    project = request.GET.get("project") or request.POST.get("project") or ""
    plot = request.GET.get("plot") or request.POST.get("plot") or ""
    block = (
        request.GET.get("block")
        or request.POST.get("block")
        or request.GET.get("block_code")
        or request.POST.get("block_code")
        or ""
    )
    net = request.GET.get("net") or request.POST.get("net") or 0
    storage = request.GET.get("storage") or request.POST.get("storage") or 0
    parking = request.GET.get("parking") or request.POST.get("parking") or 0

    rate = get_rate(code=code, project=project, plot=plot, block=block)
    if not rate:
        desc = (
            f"کد «{code}»" if code
            else f"پروژه «{project}» - بلوک «{block}»" if block
            else f"پروژه «{project}» - قطعه «{plot}»"
        )
        return JsonResponse({
            "success": False,
            "error": f"نرخ مصوبی برای {desc} در جدول نرخ‌های عرصه یافت نشد.",
            "rate_found": False
        })

    vals = compute_land_values(net, storage, parking, rate)
    from .land_rates import serialize_rate_breakdown
    breakdown = serialize_rate_breakdown(rate) or {}
    return JsonResponse({
        "success": True,
        "rate_found": True,
        "data": {
            **breakdown,
            "total_land_share": float(vals["total_land_share"]),
            "current_year_rent": int(vals["current_year_rent"]),
            "past_years_rent": int(vals["past_years_rent"]),
            "preparation_cost": int(vals["preparation_cost"]),
            "land_lease_year": vals["land_lease_year"],
        }
    })
