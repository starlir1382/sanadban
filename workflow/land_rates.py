"""
workflow/land_rates.py
Auto-calculation for dossier Section 9 (ارزیابی اداره کل، تعیین اجاره و آماده‌سازی).

Rates and share coefficients come from the base Excel, one row per کد نوسازی / بلوک,
imported into the LandRate table (see import_land_rates command).

Formulas (share = جمع کل قدرالسهم):
    share            = (net_unit_area + storage_area + parking_area) * مجموع ضریب قدرالسهم
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


_PROJ_STOPWORDS = frozenset({
    "شرکت", "تعاونی", "مسکن", "مهندسی", "سازمان", "گروه",
    "بین", "المللی", "بینالمللی", "ساختمانی", "کارکنان", "ع", "و", "راه",
})


def _project_tokens(p: Any) -> frozenset:
    """Extracts normalized meaningful tokens from a project name for resilient matching."""
    if not p:
        return frozenset()
    s = str(p).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = re.sub(r"قطعه\s*\d+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    tokens = set()
    for raw in s.split():
        tok = raw.strip("_")
        if not tok or tok in _PROJ_STOPWORDS:
            continue
        if len(tok) >= 3 and tok.endswith("ی") and tok[-2] in ("ا", "و"):
            tok = tok[:-1]
        tokens.add(tok)
    return frozenset(tokens)


def clean_project_fuzzy(p: Any) -> str:
    """Strips corporate prefixes to match projects across different naming styles."""
    if not p:
        return ""
    s = str(p).translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = re.sub(r"قطعه\s*\d+", "", s)
    s = re.sub(r"(شرکت|تعاونی|مسکن|مهندسی|راه\s*و\s*ساختمانی|سازمان|گروه|بین\s*المللی|کارکنان|\(ع\)|\bع\b)", "", s)
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


def _fmt_coeff(value: Any) -> str:
    d = _dec(value)
    s = f"{d:f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def compute_land_values(net: Any, storage: Any, parking: Any, rate: Any) -> Dict[str, Any]:
    """Pure calculation. `rate` needs the four LandRate numeric attributes."""
    area = _dec(net) + _dec(storage) + _dec(parking)
    coefficient = _dec(getattr(rate, "share_coefficient", 0))
    share = (area * coefficient).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        OUT_SHARE: share,
        OUT_CURRENT_RENT: _rial(share * _dec(getattr(rate, "rent_current_per_m2", 0))),
        OUT_PAST_RENT: _rial(share * _dec(getattr(rate, "rent_to_date_per_m2", 0))),
        OUT_PREP: _rial(share * _dec(getattr(rate, "prep_per_m2", 0))),
        OUT_YEAR: LAND_LEASE_YEAR,
    }


def serialize_rate_breakdown(rate: Any) -> Optional[Dict[str, Any]]:
    """Serialize matched LandRate coefficient and per-m2 rates for transparent UI display."""
    if rate is None:
        return None
    share_coefficient = _dec(getattr(rate, "share_coefficient", 0))
    return {
        "rate_type": "apartment",
        "renovation_code": getattr(rate, "renovation_code", "") or "",
        "project_name": getattr(rate, "project_name", "") or "",
        "block_name": getattr(rate, "block_name", "") or "",
        "plot_number": getattr(rate, "plot_number", "") or "",
        "share_coefficient": _fmt_coeff(share_coefficient),
        "rent_current_per_m2": _rial(_dec(getattr(rate, "rent_current_per_m2", 0))),
        "rent_to_date_per_m2": _rial(_dec(getattr(rate, "rent_to_date_per_m2", 0))),
        "prep_per_m2": _rial(_dec(getattr(rate, "prep_per_m2", 0))),
    }


# ---- Rate lookup (cached for 60s, supports code OR project+block OR project+plot) ----------
_CACHE: Dict[str, Any] = {
    "at": 0.0,
    "by_code": {},
    "by_proj_plot_blk": {},
    "by_proj_blk": {},
    "by_clean_proj_blk": {},
    "by_proj_plot": {},
    "by_block_fuzzy": {},
    "by_plot_fuzzy": {},
    "all_rates": [],
    "memo": {},
}
_TTL = 60


def reset_cache():
    _CACHE["at"] = 0.0
    _CACHE["by_code"] = {}
    _CACHE["by_proj_plot_blk"] = {}
    _CACHE["by_proj_blk"] = {}
    _CACHE["by_clean_proj_blk"] = {}
    _CACHE["by_proj_plot"] = {}
    _CACHE["by_block_fuzzy"] = {}
    _CACHE["by_plot_fuzzy"] = {}
    _CACHE["all_rates"] = []
    _CACHE["memo"] = {}
    reset_villa_cache()


def _ensure_cache():
    if time.time() - _CACHE["at"] > _TTL or not _CACHE["by_code"]:
        from .models import LandRate
        by_code = {}
        by_proj_plot_blk = {}
        by_proj_blk = {}
        by_clean_proj_blk = {}
        by_proj_plot = {}
        by_block_fuzzy: Dict[str, List[Tuple[Any, str, frozenset]]] = {}
        by_plot_fuzzy: Dict[str, List[Tuple[Any, str, frozenset]]] = {}
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
            p_tokens = _project_tokens(r.project_name)
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

            if clean_p or p_tokens:
                entry = (r, clean_p, p_tokens)
                if clean_b:
                    by_block_fuzzy.setdefault(clean_b, []).append(entry)
                if blk_norm and blk_norm != clean_b:
                    by_block_fuzzy.setdefault(blk_norm, []).append(entry)
                if plot_norm:
                    by_plot_fuzzy.setdefault(plot_norm, []).append(entry)

        _CACHE["by_code"] = by_code
        _CACHE["by_proj_plot_blk"] = by_proj_plot_blk
        _CACHE["by_proj_blk"] = by_proj_blk
        _CACHE["by_clean_proj_blk"] = by_clean_proj_blk
        _CACHE["by_proj_plot"] = by_proj_plot
        _CACHE["by_block_fuzzy"] = by_block_fuzzy
        _CACHE["by_plot_fuzzy"] = by_plot_fuzzy
        _CACHE["all_rates"] = all_rates
        _CACHE["memo"] = {}
        _CACHE["at"] = time.time()


def _project_match_score(
    clean_p: str,
    r_clean_p: str,
    p_tokens: frozenset = frozenset(),
    r_tokens: frozenset = frozenset(),
) -> int:
    """Scores fuzzy project similarity (>0 = match) while preventing cross-phase mismatches."""
    if not ((clean_p and r_clean_p) or (p_tokens and r_tokens)):
        return 0
    p_nums = {t for t in p_tokens if t.isdigit()}
    r_nums = {t for t in r_tokens if t.isdigit()}
    if p_nums and r_nums and not (p_nums <= r_nums or r_nums <= p_nums):
        return 0
    if clean_p and r_clean_p and (r_clean_p in clean_p or clean_p in r_clean_p):
        return 100 + min(len(r_clean_p), len(clean_p))
    if p_tokens and r_tokens and (r_tokens <= p_tokens or p_tokens <= r_tokens):
        return 80 + len(r_tokens & p_tokens)
    if clean_p and r_clean_p and len(clean_p) >= 4 and len(r_clean_p) >= 4 and clean_p[:4] == r_clean_p[:4]:
        return 50
    shared = len(r_tokens & p_tokens) if (p_tokens and r_tokens) else 0
    if shared >= 2:
        return 40 + shared
    return 0


def _project_fuzzy_matches(clean_p: str, r_clean_p: str) -> bool:
    return _project_match_score(clean_p, r_clean_p) > 0


def _pick_best_fuzzy_candidate(candidates, clean_p: str, p_tokens: frozenset):
    best_rate = None
    best_score = 0
    for r, r_clean_p, r_tokens in candidates:
        sc = _project_match_score(clean_p, r_clean_p, p_tokens, r_tokens)
        if sc > best_score:
            best_score = sc
            best_rate = r
    return best_rate


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

    memo_key = (code or "", project or "", plot or "", block or "")
    memo = _CACHE["memo"]
    if memo_key in memo:
        return memo[memo_key]

    result = _get_rate_uncached(code=code, project=project, plot=plot, block=block)
    if len(memo) < 20000:
        memo[memo_key] = result
    return result


def _get_rate_uncached(
    code: Any = None,
    project: Any = None,
    plot: Any = None,
    block: Any = None
):
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
    p_tokens = _project_tokens(p_str)
    plot_norm = normalize_plot(plot_str)
    blk_norm = normalize_block(blk_str)
    clean_b = clean_block_fuzzy(blk_str)

    # 2. Match by (project, plot, block) if plot is provided
    if (p_norm or clean_p) and plot_norm and (blk_norm or clean_b):
        for kp in (p_norm, clean_p):
            for kb in (blk_norm, clean_b):
                if (kp, plot_norm, kb) in _CACHE["by_proj_plot_blk"]:
                    return _CACHE["by_proj_plot_blk"][(kp, plot_norm, kb)]

        # 2b. Fuzzy project matching restricted to exact plot + block before falling back to block-only
        target_b = clean_b or blk_norm
        plot_blk_candidates = [
            entry for entry in _CACHE["by_plot_fuzzy"].get(plot_norm, ())
            if clean_block_fuzzy(entry[0].block_name) == target_b or normalize_block(entry[0].block_name) == blk_norm
        ]
        matched_rate = _pick_best_fuzzy_candidate(plot_blk_candidates, clean_p, p_tokens)
        if matched_rate:
            return matched_rate

    # 3. Match by (project, block) -> GUESS WITH ONLY PROJECT AND BLOCK CODE
    if (p_norm or clean_p or p_tokens) and (blk_norm or clean_b):
        if (p_norm, blk_norm) in _CACHE["by_proj_blk"]:
            return _CACHE["by_proj_blk"][(p_norm, blk_norm)]
        if (clean_p, clean_b) in _CACHE["by_clean_proj_blk"]:
            return _CACHE["by_clean_proj_blk"][(clean_p, clean_b)]
        if (clean_p, blk_norm) in _CACHE["by_clean_proj_blk"]:
            return _CACHE["by_clean_proj_blk"][(clean_p, blk_norm)]
        if (p_norm, clean_b) in _CACHE["by_proj_blk"]:
            return _CACHE["by_proj_blk"][(p_norm, clean_b)]

        # Fuzzy project matching for this block using scored lookup
        target_b = clean_b or blk_norm
        matched_rate = _pick_best_fuzzy_candidate(_CACHE["by_block_fuzzy"].get(target_b, ()), clean_p, p_tokens)
        if matched_rate:
            return matched_rate

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
    if (p_norm or clean_p or p_tokens) and plot_norm:
        if (p_norm, plot_norm) in _CACHE["by_proj_plot"]:
            return _CACHE["by_proj_plot"][(p_norm, plot_norm)]
        if (clean_p, plot_norm) in _CACHE["by_proj_plot"]:
            return _CACHE["by_proj_plot"][(clean_p, plot_norm)]

        matched_rate = _pick_best_fuzzy_candidate(_CACHE["by_plot_fuzzy"].get(plot_norm, ()), clean_p, p_tokens)
        if matched_rate:
            return matched_rate

    return None


def apply_land_calculation(dossier: Any, skip: Any = ()) -> bool:
    """
    Fills the five Section 9 fields on `dossier` in-memory.
    Routes ویلایی dossiers to VillaLandRate lookup by (project + پلاک ثبتی)
    and apartment dossiers to LandRate lookup by کد نوسازی / بلوک / قطعه.
    Returns True if a rate was found; False leaves fields untouched.
    Locked dossiers are strictly immutable.
    """
    if getattr(dossier, "is_locked", False):
        return False

    from .models import is_villa_construction

    skip_set = set(skip)
    proj = getattr(dossier, "project", "")
    plot = getattr(dossier, "plot_number", "")

    if is_villa_construction(getattr(dossier, "site", ""), getattr(dossier, "construction_type", "")):
        vrate = get_villa_rate(
            project=proj,
            main_plaque=getattr(dossier, "main_plaque", None),
            separated_plaque=getattr(dossier, "separated_plaque", None),
            sub_plaque=getattr(dossier, "sub_plaque", None),
        )
        if vrate is None:
            return False
        if not plot and vrate.plot_number and "plot_number" not in skip_set:
            try:
                setattr(dossier, "plot_number", int(float(str(vrate.plot_number).translate(_DIGITS))))
            except Exception:
                pass
        values = compute_villa_land_values(vrate, fallback_area=getattr(dossier, OUT_SHARE, 0))
        for field, value in values.items():
            if field not in skip_set:
                if field == OUT_SHARE and _dec(vrate.land_area) <= 0 and not value:
                    continue
                setattr(dossier, field, value)
        return True

    code = getattr(dossier, F_CODE, "")
    blk = getattr(dossier, "block_name", "") or getattr(dossier, "block_code", "")

    rate = get_rate(code=code, project=proj, plot=plot, block=blk)
    if rate is None:
        return False

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
        for p in prefixes:
            np = _norm_header(p)
            for i, h in enumerate(header):
                if np in h:
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

    c_coeff = col_opt("مجموع ضریب قدرالسهم", "مجموع ضریب", "جمع ضریب قدرالسهم", "جمع ضریب")
    c_sl = col_opt("ضریب قدرالسهم عرصه", "ضریب قدر السهم عرصه", "قدرالسهم از عرصه", "قدرالسهم عرصه", "سهم عرصه")
    c_sc = col_opt("ضریب قدرالسهم عیان", "ضریب قدر السهم عیان", "قدرالسهم از عیان", "قدرالسهم عیان", "ضریب قدرالسهم مشاع", "قدرالسهم از مشاع", "قدرالسهم مشاع", "سهم مشاع")
    if c_coeff is None and c_sl is None and c_sc is None:
        c_coeff = col_opt("ضریب قدرالسهم", "ضریب")

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

        has_coeff_val = c_coeff is not None and r[c_coeff] is not None and str(r[c_coeff]).strip() != ""
        if has_coeff_val:
            share_coefficient = _dec(r[c_coeff])
        else:
            sl_val = _dec(r[c_sl]) if c_sl is not None else Decimal("0")
            sc_val = _dec(r[c_sc]) if c_sc is not None else Decimal("0")
            share_coefficient = sl_val + sc_val

        rows.append(dict(
            renovation_code=code,
            project_name=str(r[c_proj] or "").strip(),
            plot_number=str(r[c_plot] or "").strip(),
            block_name=str(r[c_blk] or "").strip(),
            share_coefficient=share_coefficient,
            rent_current_per_m2=_dec(r[c_cur]),
            rent_to_date_per_m2=_dec(r[c_past]),
            prep_per_m2=_dec(r[c_prep]),
        ))

    # keep only the last row per renovation_code
    last = {r["renovation_code"]: r for r in rows}
    return list(last.values()), problems


# ==========================================================================
# ویلایی (پلاک ثبتی) Land Rates: lookup, calculation, and Excel parsing
# ==========================================================================

_VILLA_CACHE: Dict[str, Any] = {
    "at": 0.0,
    "loaded": False,
    "by_plaque": {},
    "all_rates": [],
    "memo": {},
}


def reset_villa_cache():
    """Clears in-memory VillaLandRate lookup caches."""
    _VILLA_CACHE["at"] = 0.0
    _VILLA_CACHE["loaded"] = False
    _VILLA_CACHE["by_plaque"] = {}
    _VILLA_CACHE["all_rates"] = []
    _VILLA_CACHE["memo"] = {}


def _clean_plaque_part(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).translate(_DIGITS).strip()
    if s in ("", "-", "—", "None", "null"):
        return ""
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s


def normalize_registry_plaque(value: Any) -> str:
    """Normalizes پلاک ثبتی into ASCII slash-delimited segments (e.g. 11507/957/3828)."""
    s = _clean_plaque_part(value)
    if not s:
        return ""
    parts = [p for p in re.split(r"[\s/\\-]+", s) if p]
    return "/".join(parts)


def plaque_candidates(
    plaque: Any = None,
    main_plaque: Any = None,
    separated_plaque: Any = None,
    sub_plaque: Any = None,
) -> List[str]:
    """
    Returns ordered candidate پلاک ثبتی strings.
    Handles swapped فرعی/مفروز ordering (e.g. DB main=11507, sep=3828, sub=957 vs Excel 11507/957/3828).
    """
    ordered: List[str] = []

    def _add(val: str):
        norm = normalize_registry_plaque(val)
        if norm and norm not in ordered:
            ordered.append(norm)

    if plaque:
        norm_p = normalize_registry_plaque(plaque)
        _add(norm_p)
        parts = norm_p.split("/")
        if len(parts) == 3:
            _add(f"{parts[0]}/{parts[2]}/{parts[1]}")
        elif len(parts) == 2:
            _add(f"{parts[1]}/{parts[0]}")

    m = _clean_plaque_part(main_plaque)
    sep = _clean_plaque_part(separated_plaque)
    sub = _clean_plaque_part(sub_plaque)

    if m and sub and sep:
        _add(f"{m}/{sub}/{sep}")
        _add(f"{m}/{sep}/{sub}")
    elif m and sub:
        _add(f"{m}/{sub}")
        _add(f"{sub}/{m}")
    elif m and sep:
        _add(f"{m}/{sep}")
        _add(f"{sep}/{m}")
    elif m:
        _add(m)

    return ordered


def _ensure_villa_cache():
    if time.time() - _VILLA_CACHE["at"] > _TTL or not _VILLA_CACHE["loaded"]:
        from .models import VillaLandRate
        by_plaque: Dict[str, List[Tuple[Any, str, str, frozenset]]] = {}
        all_rates = []
        for r in VillaLandRate.objects.all():
            all_rates.append(r)
            norm_plaque = normalize_registry_plaque(r.registry_plaque)
            if not norm_plaque:
                continue
            entry = (
                r,
                normalize_project(r.project_name),
                clean_project_fuzzy(r.project_name),
                _project_tokens(r.project_name),
            )
            by_plaque.setdefault(norm_plaque, []).append(entry)

        _VILLA_CACHE["by_plaque"] = by_plaque
        _VILLA_CACHE["all_rates"] = all_rates
        _VILLA_CACHE["memo"] = {}
        _VILLA_CACHE["loaded"] = True
        _VILLA_CACHE["at"] = time.time()


def get_villa_rate(
    project: Any = None,
    plaque: Any = None,
    main_plaque: Any = None,
    separated_plaque: Any = None,
    sub_plaque: Any = None,
):
    """Finds VillaLandRate matching پلاک ثبتی (handling فرعی/مفروز order) and پروژه."""
    _ensure_villa_cache()

    memo_key = (
        normalize_registry_plaque(plaque),
        _clean_plaque_part(main_plaque),
        _clean_plaque_part(separated_plaque),
        _clean_plaque_part(sub_plaque),
        str(project or "").strip(),
    )
    memo = _VILLA_CACHE["memo"]
    if memo_key in memo:
        return memo[memo_key]

    result = _get_villa_rate_uncached(
        project=project,
        plaque=plaque,
        main_plaque=main_plaque,
        separated_plaque=separated_plaque,
        sub_plaque=sub_plaque,
    )
    if len(memo) < 20000:
        memo[memo_key] = result
    return result


def _get_villa_rate_uncached(
    project: Any = None,
    plaque: Any = None,
    main_plaque: Any = None,
    separated_plaque: Any = None,
    sub_plaque: Any = None,
):
    cands = plaque_candidates(
        plaque=plaque,
        main_plaque=main_plaque,
        separated_plaque=separated_plaque,
        sub_plaque=sub_plaque,
    )
    if not cands:
        return None

    p_str = str(project or "").strip()
    p_norm = normalize_project(p_str)
    clean_p = clean_project_fuzzy(p_str)
    p_tokens = _project_tokens(p_str)

    entries: List[Tuple[Any, str, str, frozenset]] = []
    for cand in cands:
        entries.extend(_VILLA_CACHE["by_plaque"].get(cand, ()))

    if not entries:
        return None

    if p_norm or clean_p or p_tokens:
        for r, r_norm_p, r_clean_p, _ in entries:
            if (p_norm and r_norm_p == p_norm) or (clean_p and r_clean_p == clean_p):
                return r

        best_rate = _pick_best_fuzzy_candidate(
            [(r, r_clean_p, r_tokens) for r, _, r_clean_p, r_tokens in entries],
            clean_p,
            p_tokens,
        )
        if best_rate is not None:
            return best_rate

        # Fallback only to rows with no project restriction
        for r, r_norm_p, r_clean_p, _ in entries:
            if not r_norm_p and not r_clean_p:
                return r
        return None

    if len(entries) == 1:
        return entries[0][0]
    return entries[0][0]


def compute_villa_land_values(rate: Any, fallback_area: Any = 0) -> Dict[str, Any]:
    """
    Returns exact Section 9 values from a VillaLandRate row without altering approved plot totals.
    Only derives preparation_cost from (land_area * prep_per_m2) when preparation_cost is zero and prep_per_m2 > 0.
    """
    rate_area = _dec(getattr(rate, "land_area", 0))
    eff_area = rate_area if rate_area > 0 else _dec(fallback_area)
    share = eff_area.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    rent_cur = _dec(getattr(rate, "rent_current", 0))
    rent_past = _dec(getattr(rate, "rent_to_date", 0))
    prep_cost = _dec(getattr(rate, "preparation_cost", 0))
    prep_per_m2 = _dec(getattr(rate, "prep_per_m2", 0))
    if prep_cost <= 0 and prep_per_m2 > 0 and eff_area > 0:
        prep_cost = eff_area * prep_per_m2

    return {
        OUT_SHARE: share,
        OUT_CURRENT_RENT: _rial(rent_cur),
        OUT_PAST_RENT: _rial(rent_past),
        OUT_PREP: _rial(prep_cost),
        OUT_YEAR: LAND_LEASE_YEAR,
    }


def serialize_villa_rate_breakdown(rate: Any) -> Optional[Dict[str, Any]]:
    """Serialize matched VillaLandRate values for Section 9 transparency UI (no personal data)."""
    if rate is None:
        return None
    rent_cur = _dec(getattr(rate, "rent_current", 0))
    rent_past = _dec(getattr(rate, "rent_to_date", 0))
    prep_cost = _dec(getattr(rate, "preparation_cost", 0))
    prep_per_m2 = _dec(getattr(rate, "prep_per_m2", 0))
    land_area = _dec(getattr(rate, "land_area", 0))
    if prep_cost <= 0 and prep_per_m2 > 0 and land_area > 0:
        prep_cost = land_area * prep_per_m2
    return {
        "rate_type": "villa",
        "registry_plaque": getattr(rate, "registry_plaque", "") or "",
        "project_name": getattr(rate, "project_name", "") or "",
        "plot_number": getattr(rate, "plot_number", "") or "",
        "street_width": getattr(rate, "street_width", "") or "",
        "allocation_type": getattr(rate, "allocation_type", "") or "",
        "land_area": _fmt_coeff(land_area),
        "prep_per_m2": _rial(prep_per_m2),
        "rent_current": _rial(rent_cur),
        "rent_current_exact": _fmt_coeff(rent_cur),
        "rent_to_date": _rial(rent_past),
        "rent_to_date_exact": _fmt_coeff(rent_past),
        "preparation_cost": _rial(prep_cost),
        "preparation_cost_exact": _fmt_coeff(prep_cost),
    }


_GENERIC_SHEET_RE = re.compile(r"^(sheet\d*|ورق\s*\d*|برگه\s*\d*)$", re.IGNORECASE)


def _find_villa_header_row(ws_rows: List[Tuple[Any, ...]]) -> Tuple[Optional[int], List[str], str]:
    """Scans top rows of a worksheet for the header containing 'پلاک ثبتی' and optional banner project title."""
    banner_project = ""
    for idx, row in enumerate(ws_rows[:15]):
        norm_cells = [_norm_header(c) for c in row]
        if any("پلاک ثبتی" in h or "پلاک‌ثبتی" in h for h in norm_cells if h):
            return idx, norm_cells, banner_project
        non_empty = [c for c in norm_cells if c]
        if len(non_empty) == 1 and not banner_project:
            banner_project = non_empty[0]
    return None, [], banner_project


def _has_value(v: Any) -> bool:
    return v is not None and str(v).strip() not in ("", "-", "—")


def read_villa_rates_from_excel(
    path_or_file: Any,
    default_project: str = "",
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Reads ویلایی rates from Excel worksheets by پلاک ثبتی.
    Supports both full valuation sheets (پلاک ثبتی, مساحت, معبر, تعاونی, اجاره405, اجاره تا405, آماده سازی)
    and prep-only sheets (with pre-header project title, مساحت, نحوه واگذاری, هزینه به ازای هر متر, هزینه آماده سازی).
    Strictly ignores personal columns (نام، کدملی، شماره تماس، موبایل).
    """
    from openpyxl import load_workbook

    wb = load_workbook(path_or_file, read_only=True, data_only=True)
    rows: List[Dict[str, Any]] = []
    problems: List[str] = []
    seen: Dict[Tuple[str, str], int] = {}
    found_any_header = False

    for ws in wb.worksheets:
        all_ws_rows = list(ws.iter_rows(values_only=True))
        if not all_ws_rows:
            continue

        hdr_idx, header, banner_project = _find_villa_header_row(all_ws_rows)
        if hdr_idx is None:
            continue
        found_any_header = True

        def col_opt(*patterns, exclude=()):
            for pat in patterns:
                np = _norm_header(pat)
                for i, h in enumerate(header):
                    if not h:
                        continue
                    if any(_norm_header(ex) in h for ex in exclude):
                        continue
                    if np in h:
                        return i
            return None

        c_plaque = col_opt("پلاک ثبتی", "پلاک‌ثبتی")
        if c_plaque is None:
            continue

        c_plot = col_opt("شماره قطعه", "قطعه", exclude=("ثبتی",))
        if c_plot is None:
            for i, h in enumerate(header):
                if h == "پلاک":
                    c_plot = i
                    break

        c_area = col_opt("مساحت")
        c_street = col_opt("عرض معبر", "معبر")
        c_alloc = col_opt("نحوه واگذاری", "واگذاری")
        c_proj = col_opt("نام شرکت", "نام پروژه", "تعاونی", "پروژه", "شهرک")
        c_rent_past = col_opt("اجاره تا405", "اجاره تا 405", "اجاره تا1405", "اجاره تا 1405", "اجاره سنوات", "تا405", "تا 405")
        c_rent_cur = col_opt("اجاره405", "اجاره 405", "اجاره1405", "اجاره 1405", "اجاره سال جاری", exclude=("تا", "سنوات"))
        c_prep_m2 = col_opt("به ازای هر متر", "آماده سازی هر متر", "هر متر آماده", "هزینه هر متر")
        c_prep_total = col_opt("هزینه آماده سازی", "آماده سازی", "آماده‌سازی", exclude=("هر متر", "به ازای هر متر"))

        sheet_title = _norm_header(getattr(ws, "title", "") or "")
        sheet_proj = sheet_title if (sheet_title and not _GENERIC_SHEET_RE.match(sheet_title)) else ""
        fallback_proj = _norm_header(default_project) or banner_project or sheet_proj

        for offset, r in enumerate(all_ws_rows[hdr_idx + 1:], start=hdr_idx + 2):
            if not any(_has_value(c) for c in r):
                continue
            raw_plaque = r[c_plaque] if c_plaque < len(r) else None
            plaque = normalize_registry_plaque(raw_plaque)
            if not plaque or not any(ch.isdigit() for ch in plaque):
                if _has_value(raw_plaque) and "جمع" not in str(raw_plaque) and "پلاک" not in str(raw_plaque):
                    problems.append(f"برگه {ws.title} ردیف {offset}: پلاک ثبتی نامعتبر ({raw_plaque})")
                continue

            row_proj = _norm_header(r[c_proj]) if (c_proj is not None and c_proj < len(r) and _has_value(r[c_proj])) else fallback_proj
            key = (row_proj, plaque)
            if key in seen:
                problems.append(f"برگه {ws.title} ردیف {offset}: پلاک ثبتی {plaque} ({row_proj or 'بدون پروژه'}) تکراری است؛ مقدار جدید جایگزین شد")
            seen[key] = offset

            land_area = _dec(r[c_area]) if (c_area is not None and c_area < len(r)) else Decimal("0")
            prep_per_m2 = _dec(r[c_prep_m2]) if (c_prep_m2 is not None and c_prep_m2 < len(r)) else Decimal("0")
            raw_prep = r[c_prep_total] if (c_prep_total is not None and c_prep_total < len(r)) else None
            if _has_value(raw_prep):
                preparation_cost = _dec(raw_prep)
            elif prep_per_m2 > 0 and land_area > 0:
                preparation_cost = (land_area * prep_per_m2).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            else:
                preparation_cost = Decimal("0")

            raw_plot = r[c_plot] if (c_plot is not None and c_plot < len(r)) else None
            plot_str = _clean_plaque_part(raw_plot)

            rows.append(dict(
                registry_plaque=plaque,
                project_name=row_proj,
                plot_number=plot_str,
                street_width=str(r[c_street] or "").strip() if (c_street is not None and c_street < len(r)) else "",
                allocation_type=str(r[c_alloc] or "").strip() if (c_alloc is not None and c_alloc < len(r)) else "",
                land_area=land_area.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if land_area > 0 else Decimal("0.00"),
                prep_per_m2=prep_per_m2,
                rent_current=_dec(r[c_rent_cur]) if (c_rent_cur is not None and c_rent_cur < len(r)) else Decimal("0"),
                rent_to_date=_dec(r[c_rent_past]) if (c_rent_past is not None and c_rent_past < len(r)) else Decimal("0"),
                preparation_cost=preparation_cost,
            ))

    if not found_any_header:
        raise ValueError("ستون پلاک ثبتی در هیچ‌یک از برگه‌های فایل اکسل یافت نشد.")

    last = {(r["project_name"], r["registry_plaque"]): r for r in rows}
    return list(last.values()), problems
