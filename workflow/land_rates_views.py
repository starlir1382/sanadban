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

from .models import LandRate, VillaLandRate, HousingDossier, UserProfile, VILLA_SITE_KEYWORDS, is_villa_construction
from .land_rates import (
    LAND_LEASE_YEAR,
    normalize_code,
    normalize_registry_plaque,
    compute_land_values,
    compute_villa_land_values,
    serialize_rate_breakdown,
    serialize_villa_rate_breakdown,
    get_rate,
    get_villa_rate,
    apply_land_calculation,
    read_rates_from_excel,
    read_villa_rates_from_excel,
    reset_cache,
    reset_villa_cache,
    _dec,
)


def _check_admin(user, allow_readonly_view: bool = False) -> bool:
    if not user.is_authenticated:
        return False
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "is_readonly", False):
        return allow_readonly_view
    if user.is_superuser or user.is_staff:
        return True
    return bool(profile and (profile.is_housing_chief or profile.allowed_stages == "all"))


def _villa_dossier_q() -> Q:
    q_obj = Q(construction_type__icontains="ویلایی")
    for kw in VILLA_SITE_KEYWORDS:
        q_obj |= Q(site__icontains=kw)
    return q_obj


def _excel_num(val: Decimal):
    d = _dec(val)
    return int(d) if d == d.to_integral_value() else float(d)


@login_required(login_url="login")
def land_rates_admin_view(request):
    """Admin dashboard for viewing, searching, and editing Apartment & Villa Land Rates."""
    if not _check_admin(request.user, allow_readonly_view=True):
        messages.error(request, "دسترسی غیرمجاز: این بخش صرفاً ویژه مدیران ارشد سیستم و رئیس مسکن می‌باشد.")
        return redirect("dossier_list")

    active_tab = "villa" if request.GET.get("tab") == "villa" else "apartment"
    q = request.GET.get("q", "").strip()
    project_filter = request.GET.get("project", "").strip()

    if active_tab == "villa":
        rates_qs = VillaLandRate.objects.all()
        if q:
            norm_p = normalize_registry_plaque(q)
            rates_qs = rates_qs.filter(
                Q(registry_plaque__icontains=norm_p or q)
                | Q(registry_plaque__icontains=q)
                | Q(project_name__icontains=q)
                | Q(plot_number__icontains=q)
                | Q(street_width__icontains=q)
                | Q(allocation_type__icontains=q)
            )
        if project_filter:
            rates_qs = rates_qs.filter(project_name=project_filter)
        distinct_projects = list(
            VillaLandRate.objects.exclude(project_name="")
            .values_list("project_name", flat=True)
            .distinct()
            .order_by("project_name")
        )
    else:
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
        distinct_projects = list(
            LandRate.objects.values_list("project_name", flat=True).distinct().order_by("project_name")
        )

    # Statistics for both tabs
    total_rates = LandRate.objects.count()
    apt_projects_count = LandRate.objects.exclude(project_name="").values("project_name").distinct().count()
    dossiers_with_code = HousingDossier.objects.exclude(renovation_code="").count()

    villa_total_rates = VillaLandRate.objects.count()
    villa_projects_count = VillaLandRate.objects.exclude(project_name="").values("project_name").distinct().count()
    villa_dossiers_count = HousingDossier.objects.filter(_villa_dossier_q()).count()

    # Pagination: 50 per page
    paginator = Paginator(rates_qs, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "active_tab": active_tab,
        "page_obj": page_obj,
        "paginator": paginator,
        "total_rates": total_rates,
        "total_projects": apt_projects_count,
        "dossiers_with_code": dossiers_with_code,
        "villa_total_rates": villa_total_rates,
        "villa_total_projects": villa_projects_count,
        "villa_dossiers_count": villa_dossiers_count,
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
    if "share_coefficient" in data:
        rate.share_coefficient = _dec(data["share_coefficient"])
        fields_to_update.append("share_coefficient")
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
            "share_coefficient": str(rate.share_coefficient),
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
            "project_name", "plot_number", "block_name", "share_coefficient",
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
        "مجموع ضریب قدرالسهم",
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
        row = [
            idx,
            r.project_name,
            r.plot_number,
            r.block_name,
            r.renovation_code,
            float(r.share_coefficient),
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

    qs = (
        HousingDossier.objects.filter(is_locked=False)
        .exclude(_villa_dossier_q())
        .filter(Q(renovation_code__gt="") | Q(project__gt=""))
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
@require_http_methods(["POST"])
def villa_rates_update_api(request, pk):
    """AJAX API to update a single VillaLandRate row from the admin ویلایی tab."""
    if not _check_admin(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز."}, status=403)

    rate = get_object_or_404(VillaLandRate, pk=pk)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    fields_to_update = []
    if "registry_plaque" in data and normalize_registry_plaque(data["registry_plaque"]):
        rate.registry_plaque = normalize_registry_plaque(data["registry_plaque"])
        fields_to_update.append("registry_plaque")
    if "project_name" in data:
        rate.project_name = str(data["project_name"] or "").strip()
        fields_to_update.append("project_name")
    if "plot_number" in data:
        rate.plot_number = str(data["plot_number"] or "").strip()
        fields_to_update.append("plot_number")
    if "street_width" in data:
        rate.street_width = str(data["street_width"] or "").strip()
        fields_to_update.append("street_width")
    if "allocation_type" in data:
        rate.allocation_type = str(data["allocation_type"] or "").strip()
        fields_to_update.append("allocation_type")
    if "land_area" in data:
        rate.land_area = _dec(data["land_area"])
        fields_to_update.append("land_area")
    if "prep_per_m2" in data:
        rate.prep_per_m2 = _dec(data["prep_per_m2"])
        fields_to_update.append("prep_per_m2")
    if "rent_current" in data:
        rate.rent_current = _dec(data["rent_current"])
        fields_to_update.append("rent_current")
    if "rent_to_date" in data:
        rate.rent_to_date = _dec(data["rent_to_date"])
        fields_to_update.append("rent_to_date")
    if "preparation_cost" in data:
        rate.preparation_cost = _dec(data["preparation_cost"])
        fields_to_update.append("preparation_cost")

    if fields_to_update:
        rate.save(update_fields=fields_to_update + ["updated_at"])
        reset_villa_cache()

    return JsonResponse({
        "success": True,
        "message": f"نرخ ویلایی پلاک ثبتی «{rate.registry_plaque}» با موفقیت بروز شد.",
        "rate": {
            "id": rate.pk,
            "registry_plaque": rate.registry_plaque,
            "project_name": rate.project_name,
            "land_area": str(rate.land_area),
            "rent_current": _excel_num(rate.rent_current),
            "rent_to_date": _excel_num(rate.rent_to_date),
            "preparation_cost": _excel_num(rate.preparation_cost),
        },
    })


@login_required(login_url="login")
@require_http_methods(["POST"])
def villa_rates_upload_excel_api(request):
    """Upload and parse a ویلایی Excel sheet (by پلاک ثبتی), inserting/updating without personal columns."""
    if not _check_admin(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز."}, status=403)

    excel_file = request.FILES.get("excel_file") or request.FILES.get("file")
    if not excel_file:
        return JsonResponse({"success": False, "error": "هیچ فایل اکسلی ارسال نشد."}, status=400)

    default_project = (request.POST.get("default_project") or "").strip()

    try:
        rows, problems = read_villa_rates_from_excel(excel_file, default_project=default_project)
    except Exception as exc:
        return JsonResponse({"success": False, "error": f"خطا در خواندن فایل اکسل ویلایی: {str(exc)}"}, status=400)

    if not rows:
        return JsonResponse({"success": False, "error": "هیچ ردیف پلاک ثبتی معتبری در فایل اکسل یافت نشد."}, status=400)

    VillaLandRate.objects.bulk_create(
        [VillaLandRate(**r) for r in rows],
        batch_size=500,
        update_conflicts=True,
        unique_fields=["project_name", "registry_plaque"],
        update_fields=[
            "plot_number",
            "street_width",
            "allocation_type",
            "land_area",
            "prep_per_m2",
            "rent_current",
            "rent_to_date",
            "preparation_cost",
        ],
    )
    reset_villa_cache()

    return JsonResponse({
        "success": True,
        "message": f"با موفقیت {len(rows)} پلاک ثبتی ویلایی وارد یا بروزرسانی شدند.",
        "count": len(rows),
        "total_in_db": VillaLandRate.objects.count(),
        "warnings": problems[:15],
    })


@login_required(login_url="login")
def villa_rates_export_excel(request):
    """Export VillaLandRate table as a clean RTL Excel sheet (strictly without personal data)."""
    if not _check_admin(request.user):
        return HttpResponseForbidden("دسترسی غیرمجاز")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "نرخ‌های ویلایی (پلاک ثبتی)"
    ws.views.sheetView[0].rightToLeft = True

    headers = [
        "ردیف",
        "پلاک",
        "پلاک ثبتی",
        "مساحت",
        "معبر",
        "نحوه واگذاری",
        "تعاونی",
        "اجاره405",
        "اجاره تا405",
        "هزینه به ازای هر متر",
        "آماده سازی",
        "تاریخ آخرین بروزرسانی",
    ]
    ws.append(headers)

    header_fill = openpyxl.styles.PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
    header_font = openpyxl.styles.Font(color="FFFFFF", bold=True, size=10)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")

    rates = VillaLandRate.objects.all().order_by("project_name", "registry_plaque")
    for idx, r in enumerate(rates, start=1):
        ws.append([
            idx,
            r.plot_number,
            r.registry_plaque,
            float(r.land_area),
            r.street_width,
            r.allocation_type,
            r.project_name,
            _excel_num(r.rent_current),
            _excel_num(r.rent_to_date),
            _excel_num(r.prep_per_m2),
            _excel_num(r.preparation_cost),
            r.updated_at.strftime("%Y/%m/%d %H:%M") if r.updated_at else "",
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="MaskanYar_Villa_Land_Rates.xlsx"'
    wb.save(response)
    return response


@login_required(login_url="login")
@require_http_methods(["POST"])
def villa_rates_bulk_apply_api(request):
    """Bulk applies Section 9 VillaLandRate values to open ویلایی dossiers matching (project, پلاک ثبتی)."""
    if not _check_admin(request.user):
        return JsonResponse({"success": False, "error": "دسترسی غیرمجاز."}, status=403)

    project_filter = (request.POST.get("project") or "").strip()
    only_empty = request.POST.get("only_empty", "false").lower() in ("true", "1")

    qs = (
        HousingDossier.objects.filter(is_locked=False)
        .filter(_villa_dossier_q())
        .filter(main_plaque__isnull=False)
    )
    total_matched = qs.count()
    if total_matched == 0:
        return JsonResponse({
            "success": True,
            "updated_count": 0,
            "message": "هیچ پرونده ویلایی دارای پلاک ثبتی یافت نشد.",
        })

    updated_count = 0
    chunk_size = 200
    fields_to_save = [
        "total_land_share",
        "current_year_rent",
        "past_years_rent",
        "preparation_cost",
        "land_lease_year",
        "plot_number",
    ]

    all_pks = list(qs.values_list("id", flat=True))
    for i in range(0, len(all_pks), chunk_size):
        chunk_pks = all_pks[i : i + chunk_size]
        chunk_dossiers = list(HousingDossier.objects.filter(id__in=chunk_pks))
        batch_to_update = []
        for d in chunk_dossiers:
            if only_empty and d.current_year_rent and d.current_year_rent > 0:
                continue
            if project_filter:
                vrate = get_villa_rate(
                    project=d.project,
                    main_plaque=d.main_plaque,
                    separated_plaque=d.separated_plaque,
                    sub_plaque=d.sub_plaque,
                )
                if vrate is None or vrate.project_name != project_filter:
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
        "message": f"مبالغ بخش ۹ برای {updated_count} پرونده ویلایی بر اساس پلاک ثبتی و پروژه اعمال و ذخیره شد.",
    })


@login_required(login_url="login")
def calculate_land_rates_api(request):
    """
    API endpoint to return calculated Section 9 fields on the fly.
    Routes ویلایی dossiers to VillaLandRate (by project + پلاک ثبتی)
    and آپارتمانی dossiers to LandRate (by code / block / plot).
    """
    g = lambda k, d="": request.GET.get(k) or request.POST.get(k) or d
    code = g("code")
    project = g("project")
    plot = g("plot")
    block = g("block") or g("block_code")
    site = g("site")
    construction_type = g("construction_type")
    plaque = g("plaque")
    main_plaque = g("main_plaque")
    separated_plaque = g("separated_plaque")
    sub_plaque = g("sub_plaque")
    net = g("net", 0)
    storage = g("storage", 0)
    parking = g("parking", 0)
    land_area_fallback = g("land_area", 0)

    is_villa = is_villa_construction(site, construction_type) or (bool(plaque) and not code and not block)
    if is_villa:
        vrate = get_villa_rate(
            project=project,
            plaque=plaque,
            main_plaque=main_plaque,
            separated_plaque=separated_plaque,
            sub_plaque=sub_plaque,
        )
        if not vrate:
            return JsonResponse({
                "success": False,
                "error": f"نرخ ویلایی برای پلاک ثبتی «{plaque or f'{main_plaque}/{sub_plaque}/{separated_plaque}'.strip('/')}» و پروژه «{project}» یافت نشد.",
                "rate_found": False,
                "rate_type": "villa",
            })
        vals = compute_villa_land_values(vrate, fallback_area=land_area_fallback)
        breakdown = serialize_villa_rate_breakdown(vrate) or {}
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
            },
        })

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
            "rate_found": False,
            "rate_type": "apartment",
        })

    vals = compute_land_values(net, storage, parking, rate)
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
