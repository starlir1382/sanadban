"""
workflow/field_permissions.py
Centralized Field & Action Authorization Matrix.
Enforces the principle: "Everyone should only be able to change what is related to him".
Official 21-Stage Workflow Architecture (Stages 1 to 21).
"""

# 1. Field to Stage Mapping (Stages 1 to 21)
FIELD_STAGE_MAP = {
    # Step 1: ورود اطلاعات انتخاب واحد (قابل ویرایش توسط کارشناس مرحله 1 و مدیرعامل کارگزاری در مرحله 8)
    "national_id": [1, 8],
    "full_name": [1, 8],
    "father_name": [1, 8],
    "birth_date": [1, 8],
    "applicant_phone": [1, 8],
    "selection_rank": [1, 8],
    "decile": [1, 4],
    "marital_status": [1, 8],
    "is_married_confirmed": [1, 8],

    # Spouse fields (Step 1 & Step 8)
    "spouse_full_name": [1, 8],
    "spouse_father_name": [1, 8],
    "spouse_national_id": [1, 8],
    "spouse_birth_date": [1, 8],
    "spouse_id_number": [1, 8],
    "spouse_birth_place": [1, 8],

    # Unit specifications (Step 1 & Step 8)
    "site": [1, 8],
    "project": [1, 8],
    "construction_type": [1, 8],
    "block_name": [1, 8],
    "block_code": [1, 8],
    "floor_number": [1, 8],
    "unit_number": [1, 8],
    "unit_code": [1, 8],
    "bedroom_count": [1, 8],
    "unit_direction": [1, 8],
    "net_unit_area": [1, 8],
    "common_area": [1, 8],
    "total_area": [1, 8],
    "unit_area": [1, 8],
    "storage_number": [1, 8],
    "storage_area": [1, 8],
    "parking_number": [1, 8],
    "parking_area": [1, 8],
    "covered_parking_area": [1, 8],

    # Step 2: ورود پلاک ثبتی و قیمت تمام شده
    # پلاک ثبتی: مرحله 2، مرحله 11 (کارشناس فنی و مهندسی)، مرحله 13 (بانک زمین)
    "registration_section": [2, 11, 13],
    "main_plaque": [2, 11, 13],
    "separated_plaque": [2, 11, 13],
    "sub_plaque": [2, 11, 13],
    "plot_number": [2, 11, 13],
    # قیمت تمام شده پایه بدون وام: مرحله 2 و مرحله 18 (کارشناس تسویه با پیمانکار)
    "base_cost_without_loan": [2, 18],

    # Step 3 & Step 10: کارشناس بررسی فرم ج (عالمی) / کارشناس ثبت فرم ج اداره کل
    "applicant_form_j_status": [3, 10],
    "applicant_form_j_directorate_status": [3, 10],
    "applicant_form_j_red_description": [3, 10],
    "spouse_form_j_status": [3, 10],
    "spouse_form_j_directorate_status": [3, 10],
    "spouse_form_j_red_description": [3, 10],

    # Step 4: وام صندوق، نامه پیمانکار، تسهیلات دهک (قابل ویرایش در مرحله 4 و تسویه پیمانکار مرحله 18)
    "fund_loan_amount": [4, 18],
    "contractor_letter_amount": [4, 18],
    "decile_loan_amount": [4, 18],

    # Step 5: ارسال پیامک تعیین آورده نقدی و ثبت تاریخ (وصالی)
    "applicant_equity": [5],
    "is_sms_sent": [5],
    "sms_sent_at": [5],
    "is_equity_funded": [5],

    # Step 6 & Step 9: تایید واریز و ثبت نامه معرفی به بانک / استعلام تسهیلات نهضت ملی
    "bank_loan_amount": [6, 9],
    "bank_letter_number": [6, 9],
    "bank_letter_date": [6, 9],
    "is_added_to_bank_shipment_list": [6, 9],
    "is_sent_to_bank": [6, 9],
    "bank_sent_date": [6, 9],
    "bank_sent_letter_number": [6, 9],

    # Step 15: کارشناس ارزیابی (قدرالسهم، اجاره و آماده‌سازی)
    "total_land_share": [15],
    "past_years_rent": [15],
    "current_year_rent": [15],
    "land_lease_year": [15],
    "preparation_cost": [15],

    # Step 16: دریافت چک‌های وام دهک
    "decile_loan_bank": [16],
    "supported_institution": [16],
    "check_count": [16],
    "check_amount": [16],
    "last_check_amount": [16],
    "total_check_amount": [16],
    "check_service_fee": [16],
    "commitment_number": [16],
    "commitment_date": [16],
    "check_entries_json": [16],
    "is_decile_loan_confirmed": [16],

    # Step 17: دریافت نقد و اقساط آماده سازی و اجاره
    "tenant_price": [17],
    "tenant_code": [17],
    "is_cash_rent_confirmed": [17],
    "cash_preparation_amount": [17],
    "prepayment_code": [17],
    "non_cash_preparation_amount": [17],
    "preparation_service_fee": [17],
    "preparation_check_count": [17],
    "total_preparation_check_amount": [17],
    "preparation_check_entries_json": [17],
    "is_preparation_checks_confirmed": [17],

    # Step 19: صدور و ثبت نامه محضر اداره کل
    "rah_letter": [19],
    "rah_letter_date": [19],
}

# 2. 14 Archival Signatures Slot to Stage Mapping (Official 21-step workflow)
SLOT_TO_STAGES = {
    "brokerage": [1, 2, 7, 8],
    "national_housing": [9],
    "bank_facility": [6, 9],
    "decile_facility": [4, 16],
    "contractor_settlement": [4, 18],
    "applicant_settlement": [5],
    "other_facilities": [4],
    "legal": [14],
    "form_j": [3, 10],
    "evaluation": [15],
    "technical": [11],
    "real_estate": [12],
    "land_bank": [13],
    "revenue": [17],
}

SLOT_TITLES = {
    "brokerage": "۱. مهر و امضاء کارگزاری (مهندسین مشاور ره آزرم بین‌الملل)",
    "national_housing": "۲. کارشناس نهضت ملی مسکن",
    "bank_facility": "۳. استعلام و معرفی تسهیلات بانکی",
    "decile_facility": "۴. تسهیلات دهک",
    "contractor_settlement": "۵. تسویه با پیمانکار",
    "applicant_settlement": "۶. تسویه با متقاضی",
    "other_facilities": "۷. سایر تسهیلات و وام صندوق",
    "legal": "۸. کارشناس حقوقی",
    "form_j": "۹. کارشناس فرم ج اداره کل",
    "evaluation": "۱۰. کارشناس ارزیابی (قدرالسهم و اجاره)",
    "technical": "۱۱. کارشناس فنی و مهندسی",
    "real_estate": "۱۲. کارشناس املاک",
    "land_bank": "۱۳. کارشناس بانک زمین",
    "revenue": "۱۴. کارشناس اخذ اجاره، آماده‌سازی و چک‌های دهک",
}

STAGE_TO_DEFAULT_SLOT = {
    1: "brokerage",
    2: "brokerage",
    3: "form_j",
    4: "other_facilities",
    5: "applicant_settlement",
    6: "bank_facility",
    7: "brokerage",
    8: "brokerage",
    9: "national_housing",
    10: "form_j",
    11: "technical",
    12: "real_estate",
    13: "land_bank",
    14: "legal",
    15: "evaluation",
    16: "decile_facility",
    17: "revenue",
    18: "contractor_settlement",
    19: "national_housing",
    20: "national_housing",
    21: "national_housing",
}

def get_user_allowed_stages_set(user):
    """
    Returns a set of integer stages allowed for this user, or 'all' if unrestricted.
    """
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return "all"
    profile = getattr(user, 'profile', None)
    if not profile or not profile.is_active_expert:
        return set()
    if profile.is_housing_chief or profile.allowed_stages == 'all' or profile.organization == 'system':
        return "all"
    try:
        stages = [int(s.strip()) for s in str(profile.allowed_stages).split(',') if s.strip().isdigit()]
        return set(stages)
    except Exception:
        return set()

def can_user_edit_field(user, field_name):
    """
    Checks if the user has permission to modify the given field.
    """
    allowed_stages = get_user_allowed_stages_set(user)
    if allowed_stages == "all":
        return True
    if not allowed_stages:
        return False
    
    stages_for_field = FIELD_STAGE_MAP.get(field_name)
    if not stages_for_field:
        # Fields not explicitly mapped require admin / chief
        return False
    
    return bool(allowed_stages.intersection(stages_for_field))

def can_user_upload_signature(user, slot_key):
    """
    Checks if the user is authorized to upload or edit the signature for a given slot.
    """
    allowed_stages = get_user_allowed_stages_set(user)
    if allowed_stages == "all":
        return True
    if not allowed_stages:
        return False
    
    slot_stages = SLOT_TO_STAGES.get(slot_key, [])
    return bool(allowed_stages.intersection(slot_stages))

def filter_allowed_updates(user, data_dict):
    """
    Filters incoming draft update dictionary, stripping any fields that the user is not authorized to edit.
    """
    allowed_stages = get_user_allowed_stages_set(user)
    if allowed_stages == "all":
        return data_dict
    
    filtered = {}
    for key, value in data_dict.items():
        if can_user_edit_field(user, key):
            filtered[key] = value
    return filtered
