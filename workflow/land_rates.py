"""
workflow/land_rates.py
Auto-calculation for dossier Section 9 (ارزیابی اداره کل، تعیین اجاره و آماده‌سازی).

Rates and share coefficients come from the base Excel, one row per کد نوسازی,
imported into the LandRate table (see import_land_rates command).

Formulas (share = جمع کل قدرالسهم):
    share            = (net_unit_area + storage_area + parking_area) * (قدرالسهم از عرصه + قدرالسهم از مشاع)
    اجاره سال جاری     = share * اجاره یک متر سال جاری (1405)
    اجاره سنوات        = share * علی‌الحساب اجاره یک متر از شروع قرارداد تا 1405
    مبلغ آماده‌سازی    = share * هزینه آماده‌سازی یک متر
    سال اجاره عرصه   = 1405
"""
import re
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

# ---- Base lease year constant -------------------------------------------
LAND_LEASE_YEAR = 1405

# ---- HousingDossier field names -----------------------------------------
F_NET, F_STORAGE, F_PARKING = "net_unit_area", "storage_area", "parking_area"
F_CODE = "renovation_code"
OUT_SHARE = "total_land_share"
OUT_CURRENT_RENT = "current_year_rent"
OUT_PAST_RENT = "past_years_rent"
OUT_PREP = "preparation_cost"
OUT_YEAR = "land_lease_year"
OUTPUT_FIELDS = [OUT_SHARE, OUT_CURRENT_RENT, OUT_PAST_RENT, OUT_PREP, OUT_YEAR]

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_code(value: Any) -> str:
    """کد نوسازی in canonical form: ASCII digits, no spaces, standard hyphens."""
    if value is None:
        return ""
    s = str(value).translate(_DIGITS)
    s = re.sub(r"\s+", "", s)
    return s.replace("–", "-").replace("−", "-").replace("‑", "-").strip()


def normalize_project(p: Any) -> str:
    """Normalizes project name and removes embedded 'قطعه ...'."""
    if not p:
        return ""
    s = str(p).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = re.sub(r"قطعه\s*\d+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_plot(p: Any) -> str:
    """Normalizes plot number to canonical string."""
    if p is None or p == "":
        return ""
    s = str(p).translate(_DIGITS).strip()
    try:
        return str(int(float(s)))
    except Exception:
        return s


def normalize_block(b: Any) -> str:
    """Normalizes block name."""
    if not b:
        return ""
    s = str(b).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").strip().upper()
    return re.sub(r"\s+", "", s)


def _dec(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value).translate(_DIGITS).replace(",", "").strip())
    except Exception:
        return Decimal("0")


def _rial(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_land_values(net: Any, storage: Any, parking: Any, rate: Any) -> Dict[str, Any]:
    """Pure calculation. `rate` needs the five LandRate numeric attributes."""
    area = _dec(net) + _dec(storage) + _dec(parking)
    coefficient = _dec(getattr(rate, "share_land", 0)) + _dec(getattr(rate, "share_common", 0))
    share = (area * coefficient).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        OUT_SHARE: share,
        OUT_CURRENT_RENT: _rial(share * _dec(getattr(rate, "rent_current_per_m2", 0))),
        OUT_PAST_RENT: _rial(share * _dec(getattr(rate, "rent_to_date_per_m2", 0))),
        OUT_PREP: _rial(share * _dec(getattr(rate, "prep_per_m2", 0))),
        OUT_YEAR: LAND_LEASE_YEAR,
    }


# ---- Rate lookup (cached for 60s, supports code OR project+plot) ----------
_CACHE: Dict[str, Any] = {
    "at": 0.0,
    "by_code": {},
    "by_proj_plot_blk": {},
    "by_proj_plot": {},
}
_TTL = 60


def reset_cache():
    _CACHE["at"] = 0.0
    _CACHE["by_code"] = {}
    _CACHE["by_proj_plot_blk"] = {}
    _CACHE["by_proj_plot"] = {}


def _ensure_cache():
    if time.time() - _CACHE["at"] > _TTL or not _CACHE["by_code"]:
        from .models import LandRate
        by_code = {}
        by_proj_plot_blk = {}
        by_proj_plot = {}
        for r in LandRate.objects.all():
            c = normalize_code(r.renovation_code)
            if c:
                by_code[c] = r
            p_norm = normalize_project(r.project_name)
            plot_norm = normalize_plot(r.plot_number)
            blk_norm = normalize_block(r.block_name)
            if p_norm and plot_norm:
                if blk_norm:
                    by_proj_plot_blk[(p_norm, plot_norm, blk_norm)] = r
                if (p_norm, plot_norm) not in by_proj_plot:
                    by_proj_plot[(p_norm, plot_norm)] = r
        _CACHE["by_code"] = by_code
        _CACHE["by_proj_plot_blk"] = by_proj_plot_blk
        _CACHE["by_proj_plot"] = by_proj_plot
        _CACHE["at"] = time.time()


def get_rate(
    code: Any = None,
    project: Any = None,
    plot: Any = None,
    block: Any = None
):
    """
    Finds LandRate using hierarchical lookup:
    1. By exact کد نوسازی (if provided)
    2. By (پروژه + شماره قطعه + بلوک)
    3. By (پروژه + شماره قطعه)
    """
    _ensure_cache()

    # 1. Exact match by renovation_code
    if code:
        norm_c = normalize_code(code)
        if norm_c and norm_c in _CACHE["by_code"]:
            return _CACHE["by_code"][norm_c]

    # If plot is not explicitly provided, try extracting from project string
    p_str = str(project or "")
    plot_str = str(plot or "")
    if not plot_str and "قطعه" in p_str:
        m = re.search(r"قطعه\s*(\d+)", p_str.translate(_DIGITS))
        if m:
            plot_str = m.group(1)

    p_norm = normalize_project(p_str)
    plot_norm = normalize_plot(plot_str)
    blk_norm = normalize_block(block)

    # 2. Match by (project, plot, block)
    if p_norm and plot_norm and blk_norm:
        k_blk = (p_norm, plot_norm, blk_norm)
        if k_blk in _CACHE["by_proj_plot_blk"]:
            return _CACHE["by_proj_plot_blk"][k_blk]

    # 3. Match by (project, plot)
    if p_norm and plot_norm:
        k_plot = (p_norm, plot_norm)
        if k_plot in _CACHE["by_proj_plot"]:
            return _CACHE["by_proj_plot"][k_plot]

    return None


def apply_land_calculation(dossier: Any, skip: Any = ()) -> bool:
    """
    Fills the five Section 9 fields on `dossier` in-memory.
    Supports matching by renovation_code OR by (project + plot_number).
    Returns True if a rate was found; False leaves fields untouched.
    """
    code = getattr(dossier, F_CODE, "")
    proj = getattr(dossier, "project", "")
    plot = getattr(dossier, "plot_number", "")
    blk = getattr(dossier, "block_name", "")

    rate = get_rate(code=code, project=proj, plot=plot, block=blk)
    if rate is None:
        return False

    skip_set = set(skip)

    # If dossier is missing renovation_code or plot_number, auto-fill from matched LandRate
    if not code and rate.renovation_code and "renovation_code" not in skip_set:
        setattr(dossier, "renovation_code", rate.renovation_code)
    if not plot and rate.plot_number and "plot_number" not in skip_set:
        try:
            setattr(dossier, "plot_number", int(float(rate.plot_number)))
        except Exception:
            pass

    net = getattr(dossier, F_NET, 0) or getattr(dossier, "unit_area", 0)
    storage = getattr(dossier, F_STORAGE, 0)
    parking = getattr(dossier, F_PARKING, 0)

    values = compute_land_values(net, storage, parking, rate)
    for field, value in values.items():
        if field not in skip_set:
            setattr(dossier, field, value)
    return True


# ---- Excel reader (used by import command & admin upload) ----------------
def _norm_header(h: Any) -> str:
    return re.sub(r"\s+", " ", str(h or "").replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")).strip()


def read_rates_from_excel(path_or_file: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Returns (rows, problems). Columns are found by header text, not position."""
    from openpyxl import load_workbook
    wb = load_workbook(path_or_file, read_only=True, data_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True)
    try:
        header_row = next(it)
    except StopIteration:
        return [], ["فایل اکسل خالی است."]

    header = [_norm_header(h) for h in header_row]

    def col(*prefixes):
        for i, h in enumerate(header):
            if any(h.startswith(_norm_header(p)) for p in prefixes):
                return i
        raise ValueError("ستون یافت نشد: " + " / ".join(prefixes))

    c_code = col("کد نوسازی")
    c_proj = col("نام پروژه")
    c_plot = col("قطعه")
    c_blk = col("نام بلوک")
    c_sl = col("قدرالسهم از عرصه")
    c_sc = col("قدرالسهم از مشاع")
    c_cur = col("مبلغ اجاره یک متر")
    c_past = col("علی الحساب")
    c_prep = col("مبلغ یک متر هزینه آماده")

    rows: List[Dict[str, Any]] = []
    problems: List[str] = []
    seen: Dict[str, int] = {}

    for n, r in enumerate(it, start=2):
        if not any(c is not None and str(c).strip() for c in r):
            continue
        code = normalize_code(r[c_code])
        if not code:
            problems.append(f"ردیف {n}: کد نوسازی خالی است")
            continue
        if code in seen:
            problems.append(f"ردیف {n}: کد نوسازی {code} تکراری است (ردیف {seen[code]})؛ مقدار ردیف جدید اعمال شد")
        seen[code] = n
        rows.append(dict(
            renovation_code=code,
            project_name=str(r[c_proj] or "").strip(),
            plot_number=str(r[c_plot] or "").strip(),
            block_name=str(r[c_blk] or "").strip(),
            share_land=_dec(r[c_sl]),
            share_common=_dec(r[c_sc]),
            rent_current_per_m2=_dec(r[c_cur]),
            rent_to_date_per_m2=_dec(r[c_past]),
            prep_per_m2=_dec(r[c_prep]),
        ))

    # keep only the last row per renovation_code
    last = {r["renovation_code"]: r for r in rows}
    return list(last.values()), problems
