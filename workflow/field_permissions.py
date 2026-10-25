# workflow/field_permissions.py
"""
Centralized Field & Action Authorization Matrix.
Enforces the principle: "Everyone should only be able to change what is related to him".
Full 22-Stage Workflow Architecture (Stages 0 to 21).
"""

# 1. Field to Stage Mapping (Stages 0 to 21)
FIELD_STAGE_MAP = {
    # Stage 0: کارشناس ثبت اطلاعات متقاضی و واحد انتخابی و پلاک ثبتی
    # Note: Allowed also in stages 1, 2, and 10 as per rules ("قابلیت ویرایش مرحله صفر وجود دارد")
    "national_id": [0, 1, 2, 10],
    "full_name": [0, 1, 2, 10],
    "father_name": [0, 1, 2, 10],
    "birth_date": [0, 1, 2, 10],
    "applicant_phone": [0, 1, 2, 10],
    "selection_rank": [0, 1, 2, 10],
    "decile": [0, 6],
    "marital_status": [0, 1, 2, 10],
    "is_married_confirmed": [0, 1, 2, 10],

    # Spouse fields (Stage 0)
    "spouse_full_name": [0, 1, 2, 10],
    "spouse_father_name": [0, 1, 2, 10],
    "spouse_national_id": [0, 1, 2, 10],
    "spouse_birth_date": [0, 1, 2, 10],
    "spouse_id_number": [0, 1, 2, 10],
    "spouse_birth_place": [0, 1, 2, 10],

    # Unit specifications (Stage 0)
    "site": [0, 1, 2, 10],
    "project": [0, 1, 2, 10],
    "construction_type": [0, 1, 2, 10],
    "block_name": [0, 1, 2, 10],
    "block_code": [0, 1, 2, 10],
    "floor_number": [0, 1, 2, 10],
    "unit_number": [0, 1, 2, 10],
    "unit_code": [0, 1, 2, 10],
    "bedroom_count": [0, 1, 2, 10],
    "unit_direction": [0, 1, 2, 10],
    "net_unit_area": [0, 1, 2, 10],
    "common_area": [0, 1, 2, 10],
    "total_area": [0, 1, 2, 10],
    "unit_area": [0, 1, 2, 10],
    "storage_number": [0, 1, 2, 10],
    "storage_area": [0, 1, 2, 10],
    "parking_number": [0, 1, 2, 10],
    "parking_area": [0, 1, 2, 10],
    "covered_parking_area": [0, 1, 2, 10],

    # Stage 1, 12, 14: کارشناس اطلاعات (پلاک ثبتی) / کارشناس فنی و مهندسی / کارشناس بانک زمین
    "registration_section": [0, 1, 12, 14],
    "main_plaque": [0, 1, 12, 14],
    "separated_plaque": [0, 1, 12, 14],
    "sub_plaque": [0, 1, 12, 14],
    "plot_number": [0, 1, 12, 14],

    # Stage 2: ورود مبلغ تمام شده (کارشناس اطلاعات / کارگزاری)
    "base_cost_without_loan": [0, 2],

    # Stage 3, 16: کارشناس بررسی فرم ج (عالمی) / کارشناس فرم ج اداره کل
    "applicant_form_j_status": [3, 16],
    "applicant_form_j_directorate_status": [3, 16],
    "applicant_form_j_red_description": [3, 16],
    "spouse_form_j_status": [3, 16],
    "spouse_form_j_directorate_status": [3, 16],
    "spouse_form_j_red_description": [3, 16],

    # Stage 4: ورود مبلغ وام صندوق (حیدری)
    "fund_loan_amount": [4],

    # Stage 5, 19: مبلغ نامه پیمانکار (حیدری) / کارشناس تسویه با پیمانکار
    "contractor_letter_amount": [5, 19],

    # Stage 6: ورود مبلغ تسهیلات دهک (حیدری)
    "decile_loan_amount": [6],

    # Stage 7: تعیین مبلغ باقیمانده نقدی مورد نیاز و ارسال پیامک (وصالی)
    "applicant_equity": [7],
    "is_sms_sent": [7],
    "sms_sent_at": [7],
    "is_equity_funded": [7],

    # Stage 8, 11: ارسال و درج شماره نامه معرفی به بانک (وصالی / حیدری) / استعلام بانک اداره کل
    "bank_loan_amount": [8, 11],
    "bank_letter_number": [8, 11],
    "bank_letter_date": [8, 11],
    "is_added_to_bank_shipment_list": [8, 11],
    "is_sent_to_bank": [8, 11],
    "bank_sent_date": [8, 11],
    "bank_sent_letter_number": [8, 11],

    # Stage 17: کارشناس ارزیابی (قدرالسهم، اجاره و آماده‌سازی)
    "total_land_share": [17],
    "past_years_rent": [17],
    "current_year_rent": [17],
    "land_lease_year": [17],
    "preparation_cost": [17],

    # Stage 18: وصول نقد، اقساط، چک‌های دهک و آماده‌سازی (کارگزاری)
    "decile_loan_bank": [18],
    "supported_institution": [18],
    "check_count": [18],
    "check_amount": [18],
    "last_check_amount": [18],
    "total_check_amount": [18],
    "check_service_fee": [18],
    "commitment_number": [18],
    "commitment_date": [18],
    "check_entries_json": [18],
    "is_decile_loan_confirmed": [18],

    "tenant_price": [18],
    "tenant_code": [18],
    "is_cash_rent_confirmed": [18],
    "cash_preparation_amount": [18],
    "prepayment_code": [18],
    "non_cash_preparation_amount": [18],
    "preparation_service_fee": [18],
    "preparation_check_count": [18],
    "total_preparation_check_amount": [18],
    "preparation_check_entries_json": [18],
    "is_preparation_checks_confirmed": [18],

    # Stage 20: صدور و ثبت نامه محضر
    "rah_letter": [20],
    "rah_letter_date": [20],
}

# 2. 14 Archival Signatures Slot to Stage Mapping (Stages 0 to 21)
SLOT_TO_STAGES = {
    "brokerage": [0, 1, 2, 9, 10],
    "national_housing": [11],
    "bank_facility": [8, 11],
    "decile_facility": [6, 18],
    "contractor_settlement": [5, 19],
    "applicant_settlement": [7],
    "other_facilities": [4],
    "legal": [15],
    "form_j": [3, 16],
    "evaluation": [17],
    "technical": [12],
    "real_estate": [13],
    "land_bank": [14],
    "revenue": [18],
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
    0: "brokerage",
    1: "brokerage",
    2: "brokerage",
    3: "form_j",
    4: "other_facilities",
    5: "contractor_settlement",
    6: "decile_facility",
    7: "applicant_settlement",
    8: "bank_facility",
    9: "brokerage",
    10: "brokerage",
    11: "national_housing",
    12: "technical",
    13: "real_estate",
    14: "land_bank",
    15: "legal",
    16: "form_j",
    17: "evaluation",
    18: "revenue",
    19: "contractor_settlement",
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
