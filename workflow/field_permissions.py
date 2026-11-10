from .stages import SLOT_TO_STAGES
"""
workflow/field_permissions.py
Centralized Field & Action Authorization Matrix.
Enforces the principle: "Everyone should only be able to change what is related to him".
Official 21-Stage Workflow Architecture (Stages 1 to 21).
"""

# 1. Field to Stage Mapping (Stages 1 to 21)
FIELD_STAGE_MAP = {
    # Step 1 (بخش ۱): متقاضی، همسر، پروژه و واحد (قابل ویرایش توسط کارشناس مرحله ۱ و هر دو کاربر مراحل ۸ و ۹)
    "national_id": [1, 8, 9],
    "first_name": [1, 8, 9],
    "last_name": [1, 8, 9],
    "full_name": [1, 8, 9],
    "father_name": [1, 8, 9],
    "birth_date": [1, 8, 9],
    "applicant_phone": [1, 8, 9],
    "applicant_address": [1, 8, 9],
    "applicant_postal_code": [1, 8, 9],
    "applicant_landline_phone": [1, 8, 9],
    "applicant_id_serial": [1, 8, 9],
    "applicant_id_number": [1, 8, 9],
    "applicant_birth_place": [1, 8, 9],
    "selection_rank": [1, 8, 9],
    "decile": [1, 4, 8, 9],
    "marital_status": [1, 8, 9],
    "is_married_confirmed": [1, 8, 9, 10],
    "is_installment_booklet_confirmed": [7, 8, 9, 10],
    "is_land_deed_confirmed": [8, 9, 12, 13],

    # Spouse fields (Step 1 & Steps 8, 9)
    "spouse_first_name": [1, 8, 9],
    "spouse_last_name": [1, 8, 9],
    "spouse_full_name": [1, 8, 9],
    "spouse_father_name": [1, 8, 9],
    "spouse_national_id": [1, 8, 9],
    "spouse_birth_date": [1, 8, 9],
    "spouse_id_number": [1, 8, 9],
    "spouse_id_serial": [1, 8, 9],
    "spouse_birth_place": [1, 8, 9],

    # Unit specifications (Step 1 & Steps 8, 9)
    "site": [1, 8, 9],
    "project": [1, 8, 9],
    "project_code": [1, 2, 3, 8, 9, 10, 11],
    "construction_type": [1, 8, 9],
    "block_name": [1, 8, 9],
    "block_code": [1, 8, 9],
    "floor_number": [1, 8, 9],
    "unit_number": [1, 8, 9],
    "unit_code": [1, 8, 9],
    "bedroom_count": [1, 8, 9],
    "unit_direction": [1, 8, 9],
    "net_unit_area": [1, 8, 9],
    "common_area": [1, 8, 9],
    "total_area": [1, 8, 9],
    "unit_area": [1, 8, 9],
    "storage_number": [1, 8, 9],
    "storage_area": [1, 8, 9],
    "parking_number": [1, 8, 9],
    "parking_area": [1, 8, 9],
    "bank_name": [1, 6, 8, 9],
    "bank_branch": [1, 6, 8, 9],

    # Step 2 (بخش ۲): اطلاعات ثبتی، پلاک و قیمت تمام شده (قابل ویرایش در مرحله ۲ و هر دو کاربر مراحل ۸ و ۹)
    "registration_section": [2, 8, 9, 12, 13, 14],
    "main_plaque": [2, 8, 9, 12, 13, 14],
    "separated_plaque": [2, 8, 9, 12, 13, 14],
    "sub_plaque": [2, 8, 9, 12, 13, 14],
    "plot_number": [2, 8, 9, 12, 13, 14],
    "renovation_code": [2, 8, 9, 12, 13, 14],
    "base_cost_without_loan": [2, 8, 9, 19],

    # Step 3 & Step 11: کارشناس بررسی فرم ج (عالمی) / کارشناس ثبت فرم ج اداره کل
    "applicant_form_j_status": [3, 11],
    "applicant_form_j_directorate_status": [3, 11],
    "applicant_form_j_red_description": [3, 11],
    "spouse_form_j_status": [3, 11],
    "spouse_form_j_directorate_status": [3, 11],
    "spouse_form_j_red_description": [3, 11],
    "form_j_registration_type": [3, 10, 11],
    "form_j_questionnaire_number": [1, 3, 7, 8, 11],
    "computer_code": [11],

    # Step 4: وام صندوق، نامه پیمانکار، تسهیلات دهک (قابل ویرایش در مرحله 4 و تسویه پیمانکار مرحله 18)
    "fund_loan_amount": [4, 19],
    "contractor_letter_amount": [4, 19],
    "decile_loan_amount": [4, 19],

    # Step 5: ارسال پیامک تعیین آورده نقدی و ثبت تاریخ (وصالی)
    "applicant_equity": [5],
    "is_sms_sent": [5],
    "sms_sent_at": [5],
    "sms_sent_date": [5],
    "is_equity_funded": [5],

    # Step 6 & Step 9: تایید واریز و ثبت نامه معرفی به بانک / استعلام تسهیلات نهضت ملی
    "bank_loan_amount": [6, 10],
    "bank_letter_number": [6, 10],
    "bank_letter_date": [6, 10],
    "is_added_to_bank_shipment_list": [6, 10],
    "is_sent_to_bank": [6, 10],
    "bank_sent_date": [6, 10],
    "bank_sent_letter_number": [6, 10],

    # Step 7: تشکیل پرونده کارگزاری، ثبت شماره فرم ج و چک‌باکس مدارک فیزیکی
    "form_j_number": [1, 3, 7, 8, 11],
    "has_installment_booklet": [7, 8],
    "has_info_form": [7, 8],
    "has_form_j": [7, 8],
    "has_affidavit": [7, 8],
    "has_sana": [7, 8],
    "has_national_id_doc": [7, 8],

    # Step 13: کارشناس املاک (مشخصات و تأیید سند مالکیت عرصه)
    "deed_number": [13],
    "deed_date": [13],
    "is_land_deed_confirmed": [13],

    # Step 15: کارشناس ارزیابی (قدرالسهم، اجاره و آماده‌سازی)
    "total_land_share": [16],
    "past_years_rent": [16],
    "current_year_rent": [16],
    "land_lease_year": [16],
    "preparation_cost": [16],

    # Step 17: دریافت چک‌های وام دهک
    "decile_loan_bank": [17, 18],
    "decile_bank_letter_number": [17, 18],
    "decile_bank_letter_date": [17, 18],
    "supported_institution": [17, 18],
    "check_count": [17, 18],
    "check_amount": [17, 18],
    "last_check_amount": [17, 18],
    "total_check_amount": [17, 18],
    "check_service_fee": [17, 18],
    "commitment_number": [17, 18],
    "commitment_date": [17, 18],
    "check_entries_json": [17, 18],
    "is_decile_loan_confirmed": [17, 18],

    # Step 18: دریافت نقد و اقساط آماده سازی و اجاره
    "tenant_price": [17, 18],
    "tenant_code": [17, 18],
    "is_cash_rent_confirmed": [17, 18],
    "cash_preparation_amount": [17, 18],
    "prepayment_code": [17, 18],
    "non_cash_preparation_amount": [17, 18],
    "preparation_service_fee": [17, 18],
    "preparation_check_count": [17, 18],
    "total_preparation_check_amount": [17, 18],
    "preparation_check_entries_json": [17, 18],
    "is_preparation_checks_confirmed": [17, 18],

    # Step 2 & 20: شماره و تاریخ نامه راه و شهرسازی (قابل ویرایش در بخش ۲ و مرحله ۲۰)
    "rah_letter": [2, 8, 9, 12, 13, 14, 20],
    "rah_letter_date": [2, 8, 9, 12, 13, 14, 20],
    "notary_office_number": [20],
    "notary_letter_number": [20],
    "notary_letter_date": [20],
}

# 2. 14 Archival Signatures Slot to Stage Mapping (imported from stages.py)

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
    1: "brokerage", 2: "brokerage", 3: "form_j", 4: "other_facilities",
    5: "applicant_settlement", 6: "bank_facility", 7: "brokerage",
    9: "brokerage", 10: "national_housing", 11: "form_j", 12: "technical",
    13: "real_estate", 14: "land_bank", 15: "legal", 16: "evaluation",
    17: "decile_facility", 18: "revenue", 19: "contractor_settlement",
    20: "national_housing", 21: "national_housing", 22: "national_housing",
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
