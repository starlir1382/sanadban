"""
workflow/land_rates.py
Auto-calculation for dossier Section 9 (ارزیابی اداره کل، تعیین اجاره و آماده‌سازی).

Rates and share coefficients come from the base Excel, one row per کد نوسازی / بلوک,
imported into the LandRate table (see import_land_rates command).

Formulas (share = جمع کل قدرالسهم):
    share            = (net_unit_area + storage_area + parking_area) * (قدرالسهم از عرصه + قدرالسهم از مشاع / جمع ضریب)
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


def strip_code(c: str) -> str:
    """Strips trailing '-0-0' or '-0' from renovation codes."""
    return re.sub(r"(-0)+$", "", c) if c else ""


def normalize_project(p: Any) -> str:
    """Normalizes project name and removes embedded 'قطعه ...'."""
    if not p:
        return ""
    s = str(p).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = re.sub(r"قطعه\s*\d+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_project_fuzzy(p: Any) -> str:
    """Strips corporate prefixes to match projects across different naming styles."""
    if not p:
        return ""
    s = str(p).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = re.sub(r"قطعه\s*\d+", "", s)
    s = re.sub(r"(شرکت|تعاونی|مسکن|راه\s*و\s*ساختمانی|سازمان|گروه|بین\s*المللی|سپاه|امام|علی\s*ابن\s*ابیطالب|\(ع\)|\bع\b)", "", s)
    s = re.sub(r"\s+", "", s)
    return s.strip()


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


def clean_block_fuzzy(b: Any) -> str:
    """Strips punctuation/street suffixes like '-16' or '-2' or '/1'."""
    if not b:
        return ""
    s = str(b).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").strip().upper()
    m = re.match(r"^([A-Z0-9]+)", re.sub(r"[^A-Z0-9-]", "", s))
    if m:
        s = m.group(1)
    return re.sub(r"[^A-Z0-9]", "", s)


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


# ---- Rate lookup (cached for 60s, supports code OR project+block OR project+plot) ----------
_CACHE: Dict[str, Any] = {
    "at": 0.0,
    "by_code": {},
    "by_proj_plot_blk": {},
    "by_proj_blk": {},
    "by_clean_proj_blk": {},
    "by_proj_plot": {},
    "all_rates": [],
}
_TTL = 60


def reset_cache():
    _CACHE["at"] = 0.0
    _CACHE["by_code"] = {}
    _CACHE["by_proj_plot_blk"] = {}
    _CACHE["by_proj_blk"] = {}
    _CACHE["by_clean_proj_blk"] = {}
    _CACHE["by_proj_plot"] = {}
    _CACHE["all_rates"] = []


def _ensure_cache():
    if time.time() - _CACHE["at"] > _TTL or not _CACHE["by_code"]:
        from .models import LandRate
        by_code = {}
        by_proj_plot_blk = {}
        by_proj_blk = {}
        by_clean_proj_blk = {}
        by_proj_plot = {}
        all_rates = []

        for r in LandRate.objects.all():
            all_rates.append(r)
            c = normalize_code(r.renovation_code)
            if c:
                by_code[c] = r
                sc = strip_code(c)
                if sc and sc not in by_code:
                    by_code[sc] = r

            p_norm = normalize_project(r.project_name)
            clean_p = clean_project_fuzzy(r.project_name)
            plot_norm = normalize_plot(r.plot_number)
            blk_norm = normalize_block(r.block_name)
            clean_b = clean_block_fuzzy(r.block_name)

            if p_norm and plot_norm and blk_norm:
                by_proj_plot_blk[(p_norm, plot_norm, blk_norm)] = r

            if clean_p and plot_norm and clean_b:
                by_proj_plot_blk[(clean_p, plot_norm, clean_b)] = r

            if p_norm and blk_norm and (p_norm, blk_norm) not in by_proj_blk:
                by_proj_blk[(p_norm, blk_norm)] = r

            if clean_p and clean_b and (clean_p, clean_b) not in by_clean_proj_blk:
                by_clean_proj_blk[(clean_p, clean_b)] = r

            if p_norm and plot_norm and (p_norm, plot_norm) not in by_proj_plot:
                by_proj_plot[(p_norm, plot_norm)] = r

            if clean_p and plot_norm and (clean_p, plot_norm) not in by_proj_plot:
                by_proj_plot[(clean_p, plot_norm)] = r

        _CACHE["by_code"] = by_code
        _CACHE["by_proj_plot_blk"] = by_proj_plot_blk
        _CACHE["by_proj_blk"] = by_proj_blk
        _CACHE["by_clean_proj_blk"] = by_clean_proj_blk
        _CACHE["by_proj_plot"] = by_proj_plot
        _CACHE["all_rates"] = all_rates
        _CACHE["at"] = time.time()


def get_rate(
    code: Any = None,
    project: Any = None,
    plot: Any = None,
    block: Any = None
):
    """
    Finds LandRate using hierarchical lookup:
    1. By exact or stripped کد نوسازی (with or without -0-0)
    2. By (پروژه + شماره قطعه + بلوک)
    3. By (پروژه + بلوک) -> guess & calculate with only project and block!
    4. By (پروژه + شماره قطعه)
    5. Fuzzy project & block matching
    """
    _ensure_cache()

    # 1. Match by renovation_code
    if code:
        norm_c = normalize_code(code)
        if norm_c in _CACHE["by_code"]:
            return _CACHE["by_code"][norm_c]
        stripped_c = strip_code(norm_c)
        if stripped_c in _CACHE["by_code"]:
            return _CACHE["by_code"][stripped_c]

    p_str = str(project or "")
    plot_str = str(plot or "")
    blk_str = str(block or "")

    # If plot is not explicitly provided, try extracting from project string
    if not plot_str and "قطعه" in p_str:
        m = re.search(r"قطعه\s*(\d+)", p_str.translate(_DIGITS))
        if m:
            plot_str = m.group(1)

    p_norm = normalize_project(p_str)
    clean_p = clean_project_fuzzy(p_str)
    plot_norm = normalize_plot(plot_str)
    blk_norm = normalize_block(blk_str)
    clean_b = clean_block_fuzzy(blk_str)

    # 2. Match by (project, plot, block) if plot is provided
    if (p_norm or clean_p) and plot_norm and (blk_norm or clean_b):
        for kp in (p_norm, clean_p):
            for kb in (blk_norm, clean_b):
                if (kp, plot_norm, kb) in _CACHE["by_proj_plot_blk"]:
                    return _CACHE["by_proj_plot_blk"][(kp, plot_norm, kb)]

    # 3. Match by (project, block) -> GUESS WITH ONLY PROJECT AND BLOCK CODE
    if (p_norm or clean_p) and (blk_norm or clean_b):
        if (p_norm, blk_norm) in _CACHE["by_proj_blk"]:
            return _CACHE["by_proj_blk"][(p_norm, blk_norm)]
        if (clean_p, clean_b) in _CACHE["by_clean_proj_blk"]:
            return _CACHE["by_clean_proj_blk"][(clean_p, clean_b)]
        if (clean_p, blk_norm) in _CACHE["by_clean_proj_blk"]:
            return _CACHE["by_clean_proj_blk"][(clean_p, blk_norm)]
        if (p_norm, clean_b) in _CACHE["by_proj_blk"]:
            return _CACHE["by_proj_blk"][(p_norm, clean_b)]

        # Fuzzy project matching for this block
        target_b = clean_b or blk_norm
        for r in _CACHE["all_rates"]:
            r_clean_b = clean_block_fuzzy(r.block_name)
            if r_clean_b == target_b or normalize_block(r.block_name) == target_b:
                r_clean_p = clean_project_fuzzy(r.project_name)
                if r_clean_p and (r_clean_p in clean_p or clean_p in r_clean_p or (len(clean_p) >= 4 and len(r_clean_p) >= 4 and clean_p[:4] == r_clean_p[:4])):
                    return r

    # 4. Fallback: Check if block has embedded plot e.g. HH180 -> blk HH, plot 180
    if not plot_norm and clean_b:
        m_split = re.match(r"^([A-Z]+)(\d+)$", clean_b)
        if m_split:
            cand_b, cand_plot = m_split.group(1), m_split.group(2)
            rate_cand = (
                _CACHE["by_proj_plot_blk"].get((clean_p, cand_plot, cand_b))
                or _CACHE["by_proj_plot_blk"].get((p_norm, cand_plot, cand_b))
            )
            if rate_cand:
                return rate_cand

    # Check if block is numeric e.g. '68' -> treat as plot if no block matched
    if not plot_norm and clean_b.isdigit():
        plot_norm = clean_b

    # 5. Match by (project, plot)
    if (p_norm or clean_p) and plot_norm:
        if (p_norm, plot_norm) in _CACHE["by_proj_plot"]:
            return _CACHE["by_proj_plot"][(p_norm, plot_norm)]
        if (clean_p, plot_norm) in _CACHE["by_proj_plot"]:
            return _CACHE["by_proj_plot"][(clean_p, plot_norm)]

        for r in _CACHE["all_rates"]:
            if normalize_plot(r.plot_number) == plot_norm:
                r_clean_p = clean_project_fuzzy(r.project_name)
                if r_clean_p and (r_clean_p in clean_p or clean_p in r_clean_p or (len(clean_p) >= 4 and len(r_clean_p) >= 4 and clean_p[:4] == r_clean_p[:4])):
                    return r

    return None


def apply_land_calculation(dossier: Any, skip: Any = ()) -> bool:
    """
    Fills the five Section 9 fields on `dossier` in-memory.
    Supports matching by renovation_code OR by (project + block_code/block_name)
    OR by (project + plot_number).
    Returns True if a rate was found; False leaves fields untouched.
    Locked dossiers are strictly immutable.
    """
    if getattr(dossier, "is_locked", False):
        return False

    code = getattr(dossier, F_CODE, "")
    proj = getattr(dossier, "project", "")
    plot = getattr(dossier, "plot_number", "")
    blk = getattr(dossier, "block_name", "") or getattr(dossier, "block_code", "")

    rate = get_rate(code=code, project=proj, plot=plot, block=blk)
    if rate is None:
        return False

    skip_set = set(skip)

    # Auto-fill missing dossier details from matched LandRate
    if not code and rate.renovation_code and "renovation_code" not in skip_set:
        setattr(dossier, "renovation_code", strip_code(rate.renovation_code))
    if not plot and rate.plot_number and "plot_number" not in skip_set:
        try:
            setattr(dossier, "plot_number", int(float(rate.plot_number)))
        except Exception:
            pass
    if not getattr(dossier, "block_name", "") and rate.block_name and "block_name" not in skip_set:
        setattr(dossier, "block_name", rate.block_name)

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
    """
    Reads land rates from Excel supporting both legacy and new column formats.
    Returns (rows, problems).
    """
    from openpyxl import load_workbook
    wb = load_workbook(path_or_file, read_only=True, data_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True)
    try:
        header_row = next(it)
    except StopIteration:
        return [], ["فایل اکسل خالی است."]

    header = [_norm_header(h) for h in header_row]

    def col_opt(*prefixes):
        for i, h in enumerate(header):
            if any(_norm_header(p) in h for p in prefixes):
                return i
        return None

    def col(*prefixes):
        idx = col_opt(*prefixes)
        if idx is not None:
            return idx
        raise ValueError("ستون یافت نشد: " + " / ".join(prefixes))

    c_code = col("کد نوسازی", "نوسازی")
    c_proj = col("نام شرکت", "نام پروژه", "شرکت", "پروژه")
    c_plot = col("قطعه", "شماره قطعه")
    c_blk = col("نام بلوک", "کد بلوک", "بلوک")

    c_coeff = col_opt("جمع ضریب", "ضریب")
    c_sl = col_opt("قدرالسهم از عرصه", "سهم عرصه")
    c_sc = col_opt("قدرالسهم از مشاع", "سهم مشاع")

    c_cur = col("هزینه هر متر اجاره سال جاری", "مبلغ اجاره یک متر", "اجاره سال جاری", "اجاره 1405")
    c_past = col("هزینه هر متر اجاره سنوات", "علی الحساب", "اجاره سنوات")
    c_prep = col("هزینه هر متر آماده سازی", "مبلغ یک متر هزینه آماده", "آماده سازی", "آماده‌سازی")

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

        if c_coeff is not None and r[c_coeff] is not None:
            share_land = _dec(r[c_coeff])
            share_common = Decimal("0")
        else:
            share_land = _dec(r[c_sl]) if c_sl is not None else Decimal("0")
            share_common = _dec(r[c_sc]) if c_sc is not None else Decimal("0")

        rows.append(dict(
            renovation_code=code,
            project_name=str(r[c_proj] or "").strip(),
            plot_number=str(r[c_plot] or "").strip(),
            block_name=str(r[c_blk] or "").strip(),
            share_land=share_land,
            share_common=share_common,
            rent_current_per_m2=_dec(r[c_cur]),
            rent_to_date_per_m2=_dec(r[c_past]),
            prep_per_m2=_dec(r[c_prep]),
        ))

    # keep only the last row per renovation_code
    last = {r["renovation_code"]: r for r in rows}
    return list(last.values()), problems
