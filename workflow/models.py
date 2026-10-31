import hashlib
import hmac
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from workflow.stages import STAGE_ROLES as WORKFLOW_STAGE_ROLES, STAGE_DETAILS as WORKFLOW_STAGE_DETAILS

_SIGNED_AT_RE = re.compile(r"^\s*(\d{4}/\d{1,2}/\d{1,2})(?:\s*[-–]?\s*(\d{1,2}:\d{2}))?")

class Site(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام سایت")
    code = models.CharField(max_length=20, blank=True, verbose_name="کد سایت")

    class Meta:
        verbose_name = "سایت مسکونی"
        verbose_name_plural = "سایت‌های مسکونی"

    def __str__(self):
        return self.name

class Project(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="projects", verbose_name="سایت")
    name = models.CharField(max_length=150, verbose_name="نام پروژه")
    total_units = models.PositiveIntegerField(default=100, verbose_name="تعداد کل واحدها")

    class Meta:
        verbose_name = "پروژه مسکونی"
        verbose_name_plural = "پروژه‌های مسکونی"

    def __str__(self):
        return f"{self.name} (تعداد واحد: {self.total_units})"

class PreSelectedUnit(models.Model):
    """
    Pre-imported records queried in Stage 1 by national_id to auto-fill applicant, spouse, and unit details.
    """
    national_id = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="کد ملی متقاضی")
    first_name = models.CharField(max_length=80, blank=True, verbose_name="نام متقاضی")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی متقاضی")
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی متقاضی")
    father_name = models.CharField(max_length=100, verbose_name="نام پدر")
    birth_date = models.CharField(max_length=30, blank=True, verbose_name="تاریخ تولد (شمسی)")
    applicant_id_number = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره شناسنامه متقاضی")
    applicant_birth_place = models.CharField(max_length=100, blank=True, default="", verbose_name="محل صدور شناسنامه متقاضی")
    project_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد پروژه")
    bank_name = models.CharField(max_length=100, blank=True, default="", verbose_name="نام بانک متقاضی")
    bank_branch = models.CharField(max_length=150, blank=True, default="", verbose_name="شعبه بانک متقاضی")
    
    applicant_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس متقاضی")
    selection_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="رتبه انتخاب واحد")
    
    # Form J Inquiries & Status
    form_j_questionnaire_number = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره پرسش نامه فرم ج")
    applicant_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج متقاضی")
    applicant_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل متقاضی")
    applicant_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج متقاضی")

    # Spouse fields (Crucial for Couples Scheme - طرح زوجین)
    spouse_first_name = models.CharField(max_length=80, blank=True, verbose_name="نام همسر")
    spouse_last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی همسر")
    spouse_full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی همسر")
    spouse_father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر همسر")
    spouse_national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی همسر")
    spouse_birth_date = models.CharField(max_length=30, blank=True, verbose_name="تاریخ تولد همسر")
    spouse_id_number = models.CharField(max_length=20, blank=True, verbose_name="شماره شناسنامه همسر")
    spouse_birth_place = models.CharField(max_length=100, blank=True, verbose_name="محل تولد / صدور همسر")
    spouse_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج همسر")
    spouse_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل همسر")
    spouse_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج همسر")
    marital_status = models.CharField(max_length=50, default="متاهل (واجد شرایط طرح زوجین)", blank=True, verbose_name="وضعیت تاهل")
    is_married_confirmed = models.BooleanField(default=True, verbose_name="احراز زوجیت و تایید تاهل")
    
    decile = models.PositiveSmallIntegerField(null=True, blank=True, default=None, verbose_name="دهک درآمدی")

    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, verbose_name="سایت")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, verbose_name="پروژه")
    construction_type = models.CharField(max_length=50, default="آپارتمانی", verbose_name="نوع ساخت")
    block_name = models.CharField(max_length=50, blank=True, verbose_name="نام بلوک")
    block_code = models.CharField(max_length=50, blank=True, verbose_name="کد بلوک")
    floor_number = models.PositiveSmallIntegerField(default=1, verbose_name="شماره طبقه")
    unit_number = models.PositiveIntegerField(default=1, verbose_name="شماره واحد")
    unit_code = models.CharField(max_length=50, blank=True, verbose_name="کد واحد")
    bedroom_count = models.PositiveSmallIntegerField(default=2, verbose_name="تعداد خواب")
    unit_direction = models.CharField(max_length=50, default="شمال غربی", blank=True, verbose_name="جهت واحد")
    net_unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("85.00"), verbose_name="متراژ مفید واحد (مترمربع)")
    common_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("25.00"), verbose_name="متراژ مشاعات (مترمربع)")
    total_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("110.00"), verbose_name="جمع کل متراژ واحد (مترمربع)")
    unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("85.00"), verbose_name="مساحت واحد")

    storage_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره انباری")
    storage_area = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"), verbose_name="مساحت انباری")
    parking_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره پارکینگ")
    parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"), verbose_name="مساحت پارکینگ")
    covered_parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("11.25"), verbose_name="متراژ پارکینگ مسقف (مترمربع)")
    base_cost_without_loan = models.BigIntegerField(default=4500000000, verbose_name="قیمت پایه بدون وام بانکی (ریال)")
    bank_loan_amount = models.BigIntegerField(default=6500000000, verbose_name="مبلغ وام بانکی مسکن (ریال)")

    registration_section = models.CharField(max_length=100, blank=True, verbose_name="بخش ثبتی")
    main_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک اصلی")
    separated_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک مفروز")
    sub_plaque = models.IntegerField(null=True, blank=True, verbose_name="فرعی از")
    plot_number = models.IntegerField(null=True, blank=True, verbose_name="شماره قطعه")
    renovation_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد نوسازی (شهرداری)")

    class Meta:
        verbose_name = "اطلاعات انتخاب واحد متقاضی"
        verbose_name_plural = "بانک اطلاعات انتخاب واحد (پیش‌ثبت‌نام)"

    def save(self, *args, **kwargs):
        if self.first_name or self.last_name:
            self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        elif self.full_name and not (self.first_name and self.last_name):
            parts = self.full_name.strip().split(maxsplit=1)
            self.first_name = parts[0] if parts else ""
            self.last_name = parts[1] if len(parts) > 1 else ""

        if self.spouse_first_name or self.spouse_last_name:
            self.spouse_full_name = f"{self.spouse_first_name or ''} {self.spouse_last_name or ''}".strip()
        elif self.spouse_full_name and not (self.spouse_first_name and self.spouse_last_name):
            parts = self.spouse_full_name.strip().split(maxsplit=1)
            self.spouse_first_name = parts[0] if parts else ""
            self.spouse_last_name = parts[1] if len(parts) > 1 else ""
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.national_id})"

class HousingDossier(models.Model):
    """
    Main dossier tracking the complete 21-Stage Workflow (Stages 1 to 21).
    Merged from Excel specifications & National Housing Directorate stages.
    """
    STAGE_ROLES = WORKFLOW_STAGE_ROLES
    STAGE_DETAILS = WORKFLOW_STAGE_DETAILS

    if TYPE_CHECKING:
        id: int
        attachments: Any
        audit_logs: Any
        check_items: Any
        field_changes: Any
        signatures: Any
        bank_letters: Any

    # Identifiers
    national_id = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="کدملی / شماره پیشنویس")
    archive_number = models.PositiveIntegerField(unique=True, db_index=True, verbose_name="شماره بایگانی")
    current_stage = models.PositiveSmallIntegerField(default=1, db_index=True, verbose_name="مرحله جاری (۱ تا ۲۱)")
    is_locked = models.BooleanField(default=False, verbose_name="قفل نهایی بایگانی")

    # Workflow Document State
    STATUS_CHOICES = [
        ("IN_PROGRESS", "در جریان اقدام"),
        ("RETURNED", "برگشت‌خورده جهت اصلاح و بازبینی"),
        ("COMPLETED", "نهایی و بایگانی قطعی"),
        ("REJECTED_RED", "رد صلاحیت - کد قرمز فرم «ج» (عدم واگذاری واحد)"),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="IN_PROGRESS", db_index=True, verbose_name="وضعیت فرآیند")
    return_reason = models.TextField(blank=True, verbose_name="علت آخرین برگشت پرونده")
    return_by = models.CharField(max_length=150, blank=True, verbose_name="برگشت‌دهنده")
    return_from_stage = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="مرحله برگشت‌دهنده")
    
    # Red Form J Disqualification & Official Rejection Fields
    rejection_letter_number = models.CharField(max_length=100, blank=True, verbose_name="شماره نامه رد صلاحیت")
    rejection_letter_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ نامه رد صلاحیت")
    rejection_reason = models.TextField(blank=True, verbose_name="علت و شرح رد صلاحیت")
    rejected_by = models.CharField(max_length=150, blank=True, verbose_name="رد صلاحیت کننده")

    # Stage 1: Applicant, Spouse & Unit
    first_name = models.CharField(max_length=80, blank=True, verbose_name="نام متقاضی")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی متقاضی")
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی متقاضی")
    father_name = models.CharField(max_length=100, verbose_name="نام پدر")
    birth_date = models.CharField(max_length=30, blank=True, verbose_name="تاریخ تولد (شمسی)")
    applicant_id_number = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره شناسنامه متقاضی")
    applicant_birth_place = models.CharField(max_length=100, blank=True, default="", verbose_name="محل صدور شناسنامه متقاضی")
    applicant_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس متقاضی")
    selection_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="رتبه انتخاب واحد")

    # Form J Inquiries & Status
    form_j_questionnaire_number = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره پرسش نامه فرم ج")
    applicant_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج متقاضی")
    applicant_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل متقاضی")
    applicant_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج متقاضی")
    
    # Specific Spouse Fields (Crucial for Couples Scheme - طرح زوجین)
    spouse_first_name = models.CharField(max_length=80, blank=True, verbose_name="نام همسر")
    spouse_last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی همسر")
    spouse_full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی همسر")
    spouse_father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر همسر")
    spouse_national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی همسر")
    spouse_birth_date = models.CharField(max_length=30, blank=True, verbose_name="تاریخ تولد همسر")
    spouse_id_number = models.CharField(max_length=20, blank=True, verbose_name="شماره شناسنامه همسر")
    spouse_birth_place = models.CharField(max_length=100, blank=True, verbose_name="محل تولد / صدور همسر")
    spouse_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج همسر")
    spouse_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل همسر")
    spouse_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج همسر")
    marital_status = models.CharField(max_length=50, default="متاهل (واجد شرایط طرح زوجین)", blank=True, verbose_name="وضعیت تاهل")
    is_married_confirmed = models.BooleanField(default=True, verbose_name="احراز زوجیت و تایید تاهل")

    decile = models.PositiveSmallIntegerField(null=True, blank=True, default=None, verbose_name="دهک درآمدی (۱ تا ۱۰)")

    site = models.CharField(max_length=100, verbose_name="سایت")
    project = models.CharField(max_length=200, verbose_name="نام پروژه")
    project_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد پروژه")
    bank_name = models.CharField(max_length=100, blank=True, default="", verbose_name="نام بانک متقاضی")
    bank_branch = models.CharField(max_length=150, blank=True, default="", verbose_name="شعبه بانک متقاضی")
    construction_type = models.CharField(max_length=50, default="آپارتمانی", verbose_name="نوع ساخت")
    block_name = models.CharField(max_length=50, blank=True, verbose_name="نام بلوک")
    block_code = models.CharField(max_length=50, blank=True, verbose_name="کد بلوک")
    floor_number = models.PositiveSmallIntegerField(default=1, verbose_name="شماره طبقه")
    unit_number = models.PositiveIntegerField(default=1, verbose_name="شماره واحد")
    unit_code = models.CharField(max_length=50, blank=True, verbose_name="کد واحد")
    bedroom_count = models.PositiveSmallIntegerField(default=2, verbose_name="تعداد خواب")
    unit_direction = models.CharField(max_length=50, default="شمال غربی", blank=True, verbose_name="جهت واحد")
    net_unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("85.00"), verbose_name="متراژ مفید واحد (مترمربع)")
    common_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("25.00"), verbose_name="متراژ مشاعات (مترمربع)")
    total_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("110.00"), verbose_name="جمع کل متراژ واحد (مترمربع)")
    unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("85.00"), verbose_name="مساحت واحد")
    storage_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره انباری")
    storage_area = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"), verbose_name="مساحت انباری")
    parking_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره پارکینگ")
    parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"), verbose_name="مساحت پارکینگ")
    covered_parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("11.25"), verbose_name="متراژ پارکینگ مسقف (مترمربع)")

    # Stage 2 & 18: Plot & Registry Fields
    registration_section = models.CharField(max_length=100, blank=True, verbose_name="بخش ثبتی")
    main_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک اصلی")
    separated_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک مفروز")
    sub_plaque = models.IntegerField(null=True, blank=True, verbose_name="فرعی از")
    plot_number = models.IntegerField(null=True, blank=True, verbose_name="شماره قطعه")
    renovation_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد نوسازی (شهرداری)")

    # Stage 3: Base Cost without Bank Loan & Bank Loan Amount (Default 650M, can be 550M or custom)
    base_cost_without_loan = models.BigIntegerField(default=4500000000, verbose_name="قیمت تمام شده بدون وام بانکی (ریال)")
    bank_loan_amount = models.BigIntegerField(default=6500000000, verbose_name="مبلغ تسهیلات وام بانکی (ریال)")

    # Stage 6: Fund Loan Amount
    fund_loan_amount = models.BigIntegerField(default=0, verbose_name="مبلغ وام صندوق (ریال)")

    # Stage 7: Contractor Letter Amount
    contractor_letter_amount = models.BigIntegerField(default=0, verbose_name="مبلغ نامه پیمانکار (ریال)")

    # Stage 8: Decile Loan Amount
    decile_loan_amount = models.BigIntegerField(default=0, verbose_name="مبلغ وام دهک (ریال)")

    # Stage 9: Applicant Cash Equity & SMS
    applicant_equity = models.BigIntegerField(default=0, verbose_name="مبلغ آورده نقدی متقاضی (ریال)")
    is_sms_sent = models.BooleanField(default=False, verbose_name="ارسال پیامک تعیین آورده")
    sms_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان ارسال پیامک")

    # Stage 10: Confirmation of equity funding
    is_equity_funded = models.BooleanField(default=False, verbose_name="تأیید تأمین مبلغ آورده متقاضی")

    # Stage 11: Bank Letter
    bank_letter_number = models.CharField(max_length=100, blank=True, verbose_name="شماره نامه بانک")
    bank_letter_date = models.CharField(max_length=30, blank=True, verbose_name="تاریخ نامه بانک (شمسی)")

    # Bank Shipment & Tracking Ticks (Two-stage Bank Workflow)
    is_added_to_bank_shipment_list = models.BooleanField(default=False, verbose_name="اضافه کردن به لیست ارسالی‌ها به بانک")
    bank_shipment_list_added_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان افزودن به لیست ارسالی‌ها")
    is_sent_to_bank = models.BooleanField(default=False, verbose_name="به بانک ارسال شده")
    bank_sent_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ ارسال به بانک (شمسی)")
    bank_sent_letter_number = models.CharField(max_length=50, blank=True, verbose_name="شماره نامه ارسال به بانک")

    # Stage 7: تشکیل پرونده کارگزاری، ثبت شماره فرم ج و چک‌باکس مدارک فیزیکی
    form_j_number = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره فرم ج")
    has_installment_booklet = models.BooleanField(default=False, verbose_name="دفترچه اقساط")
    has_info_form = models.BooleanField(default=False, verbose_name="فرم اطلاعات")
    has_form_j = models.BooleanField(default=False, verbose_name="فرم ج")
    has_affidavit = models.BooleanField(default=False, verbose_name="اقرارنامه")
    has_sana = models.BooleanField(default=False, verbose_name="ثنا")
    has_national_id_doc = models.BooleanField(default=False, verbose_name="شناسنامه و کارت ملی")

    # Stage 9: تأیید صحت دفترچه قسط کارشناس نهضت ملی
    is_installment_booklet_confirmed = models.BooleanField(default=False, verbose_name="تأیید صحت دفترچه قسط بانک مسکن")

    # Stage 11: تأیید سند عرصه
    is_land_deed_confirmed = models.BooleanField(default=False, verbose_name="تأیید سند مالکیت عرصه")

    # Stage 19: Valuation Fields
    total_land_share = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="جمع کل قدرالسهم (مترمربع)")
    past_years_rent = models.BigIntegerField(default=0, verbose_name="مبلغ اجاره سنوات تا پایان سال جاری")
    current_year_rent = models.BigIntegerField(default=0, verbose_name="مبلغ اجاره سال جاری")
    land_lease_year = models.CharField(max_length=4, default="", blank=True, verbose_name="سال اجاره عرصه")
    preparation_cost = models.BigIntegerField(default=0, verbose_name="مبلغ آماده سازی")

    # Stage 18: BankCheckTracker & TashilatCheck Fields (وام دهک، چک‌ها، آماده‌سازی و اجاره)
    # 1. BankCheckTracker: Decile Loan Check Fields
    decile_loan_bank = models.CharField(max_length=50, blank=True, default="", verbose_name="بانک عامل تسهیلات دهک")
    supported_institution = models.CharField(max_length=100, blank=True, default="", verbose_name="نهاد تحت حمایت")
    check_count = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="تعداد چک‌ها")
    check_amount = models.BigIntegerField(default=0, blank=True, verbose_name="مبلغ هر چک (ریال)")
    last_check_amount = models.BigIntegerField(default=0, blank=True, verbose_name="مبلغ چک آخر (ریال)")
    total_check_amount = models.BigIntegerField(default=0, blank=True, verbose_name="مجموع مبلغ چک‌ها (ریال)")
    check_service_fee = models.BigIntegerField(default=2000000, blank=True, verbose_name="کارمزد خدمات چک (ریال)")
    commitment_number = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره تعهدنامه")
    commitment_date = models.CharField(max_length=20, blank=True, default="", verbose_name="تاریخ تعهدنامه (شمسی)")
    check_entries_json = models.TextField(default="[]", blank=True, verbose_name="اطلاعات اقلام چک‌ها (JSON)")

    # 2. TashilatCheck: Rent & 20%/80% Preparation Fields
    tenant_price = models.BigIntegerField(default=0, blank=True, verbose_name="مبلغ پرداختی اجاره عرصه (ریال)")
    tenant_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد پیگیری فیش اجاره")
    cash_preparation_amount = models.BigIntegerField(default=0, verbose_name="مبلغ نقدی آماده سازی (۲۰٪ نقد)")
    prepayment_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد پیگیری فیش پیش‌پرداخت آماده‌سازی")
    non_cash_preparation_amount = models.BigIntegerField(default=0, verbose_name="مبلغ غیرنقدی آماده سازی (۸۰٪ اقساط)")
    preparation_service_fee = models.BigIntegerField(default=2000000, blank=True, verbose_name="کارمزد خدمات آماده‌سازی (ریال)")
    preparation_check_count = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name="تعداد چک‌های آماده‌سازی")
    total_preparation_check_amount = models.BigIntegerField(default=0, blank=True, verbose_name="مجموع مبلغ چک‌های آماده‌سازی (ریال)")
    preparation_check_entries_json = models.TextField(default="[]", blank=True, verbose_name="اطلاعات اقلام چک‌های آماده‌سازی (JSON)")
    rah_letter = models.CharField(max_length=50, blank=True, default="", verbose_name="شماره نامه راه و شهرسازی")
    rah_letter_date = models.CharField(max_length=20, blank=True, default="", verbose_name="تاریخ نامه راه و شهرسازی (شمسی)")
    is_cash_rent_confirmed = models.BooleanField(default=False, verbose_name="تایید مبلغ نقدی اجاره")
    is_decile_loan_confirmed = models.BooleanField(default=False, verbose_name="تایید چک‌های وام دهک")
    is_preparation_checks_confirmed = models.BooleanField(default=False, verbose_name="تایید دریافت چک‌های اقساط آماده‌سازی")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تشکیل پرونده")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    @property
    def bank_display_name(self) -> str:
        if self.bank_name and self.bank_name.strip():
            return self.bank_name.strip()
        try:
            from .models import ProjectBankMapping
            m = ProjectBankMapping.objects.filter(project_name=self.project).first()
            if m:
                return m.get_bank_code_display()
        except Exception:
            pass
        return "بانک مسکن"

    @property
    def project_code_display(self) -> str:
        if self.project_code and self.project_code.strip():
            return self.project_code.strip()
        try:
            from .models import ProjectBankMapping
            m = ProjectBankMapping.objects.filter(project_name=self.project).first()
            if m and m.project_code:
                return m.project_code.strip()
        except Exception:
            pass
        return ""

    @property
    def bank_branch_display(self) -> str:
        if self.bank_branch and self.bank_branch.strip():
            return self.bank_branch.strip()
        try:
            from .models import ProjectBankMapping
            m = ProjectBankMapping.objects.filter(project_name=self.project).first()
            if m and m.branch_name:
                return m.branch_name.strip()
        except Exception:
            pass
        return ""

    class Meta:
        verbose_name = "پرونده مسکن متقاضی"
        verbose_name_plural = "پرونده‌های مسکن متقاضیان"
        ordering = ["-archive_number"]

    def save(self, *args, **kwargs):
        # Auto-fill bank_name, project_code, bank_branch from ProjectBankMapping if empty
        if self.project and (not self.bank_name or not self.project_code or not self.bank_branch):
            try:
                from .models import ProjectBankMapping
                m = ProjectBankMapping.objects.filter(project_name=self.project).first()
                if m:
                    if not self.bank_name:
                        self.bank_name = m.get_bank_code_display()
                    if not self.project_code and m.project_code:
                        self.project_code = m.project_code
                    if not self.bank_branch and m.branch_name:
                        self.bank_branch = m.branch_name
            except Exception:
                pass

        # Auto-increment archive_number starting strictly from 100001
        if not self.archive_number:
            max_num = HousingDossier.objects.aggregate(models.Max('archive_number'))['archive_number__max']
            self.archive_number = (max_num + 1) if max_num else 100001

        # Auto-sync full names and separated names
        if self.first_name or self.last_name:
            self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        elif self.full_name and not (self.first_name and self.last_name):
            parts = self.full_name.strip().split(maxsplit=1)
            self.first_name = parts[0] if parts else ""
            self.last_name = parts[1] if len(parts) > 1 else ""

        if self.spouse_first_name or self.spouse_last_name:
            self.spouse_full_name = f"{self.spouse_first_name or ''} {self.spouse_last_name or ''}".strip()
        elif self.spouse_full_name and not (self.spouse_first_name and self.spouse_last_name):
            parts = self.spouse_full_name.strip().split(maxsplit=1)
            self.spouse_first_name = parts[0] if parts else ""
            self.spouse_last_name = parts[1] if len(parts) > 1 else ""

        # Calculate Applicant Equity: Base Cost - Total Applicable Loans
        base_cost = self.base_cost_without_loan or 0
        total_loans = (self.fund_loan_amount or 0) + (self.decile_loan_amount or 0)
        self.applicant_equity = max(0, base_cost - total_loans)

        # Auto-calculate Check Service Fee (0.5% custody fee from BankCheckTracker: 5 per 1000)
        fee_base = self.total_check_amount if (self.total_check_amount and self.total_check_amount > 0) else (self.decile_loan_amount or 0)
        if fee_base > 0:
            self.check_service_fee = (fee_base * 5 + 500) // 1000
        elif not self.check_service_fee:
            self.check_service_fee = 2000000

        super().save(*args, **kwargs)

    @property
    def current_unit(self):
        return self.STAGE_ROLES.get(self.current_stage, ("-", "-", "-"))[0]

    @property
    def current_role(self):
        return self.STAGE_ROLES.get(self.current_stage, ("-", "-", "-"))[1]

    @property
    def form_j_attachment(self):
        return self.attachments.filter(doc_type="FORM_J").order_by("-uploaded_at").first()

    @property
    def current_stage_title(self):
        return self.STAGE_ROLES.get(self.current_stage, ("-", "-", "-"))[2]

    @property
    def is_red_form_j(self):
        return "قرمز" in (self.applicant_form_j_status or "")

    @property
    def is_rejected(self):
        return self.status == "REJECTED_RED"

    @property
    def created_at_jalali(self):
        """Returns the Jalali date when the dossier was created."""
        try:
            import jdatetime
            dt = self.created_at
            if dt:
                return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
        except Exception:
            pass
        return ""

    @property
    def stage_entry_date_jalali(self):
        """Returns the Jalali date when the dossier arrived at the current stage."""
        try:
            import jdatetime
            latest_log = self.audit_logs.first()
            dt = latest_log.timestamp if latest_log and latest_log.timestamp else (self.updated_at or self.created_at)
            if dt:
                return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
        except Exception:
            pass
        return ""

    @property
    def formatted_equity(self):
        val = self.applicant_equity if self.applicant_equity is not None else self.base_cost_without_loan
        if val is None:
            return "0"
        return f"{val:,}"

    @property
    def signatures_map(self):
        """
        Returns a dict of slot_key -> DossierSignature instance.
        """
        return {s.slot_key: s for s in self.signatures.all()}

    def get_signed_stages_set(self):
        """
        Returns the set of integer stage numbers (1..21) that have been successfully signed and not returned.
        Handles disconnected / decoupled workflow stages.
        """
        import re
        signed = set()
        for log in self.audit_logs.all().order_by("timestamp", "id"):
            if log.action in ["SIGN", "APPROVE", "SIGN_EXCEL", "ARCHIVE", "BANK_LETTER"]:
                m = re.search(r'مرحله\s+(\d+)', log.from_stage)
                if m:
                    signed.add(int(m.group(1)))
                elif log.action_label and "مرحله" in log.action_label:
                    m2 = re.search(r'مرحله\s+(\d+)', log.action_label)
                    if m2:
                        signed.add(int(m2.group(1)))
            elif log.action == "RETURN":
                m = re.search(r'مرحله\s+(\d+)', log.to_stage)
                if m:
                    target_stage = int(m.group(1))
                    signed = {s for s in signed if s < target_stage}
        return signed

    def find_next_actionable_stage(self, current_signed_stage=None):
        """
        Determines the next stage that requires action/signature.
        If stages are decoupled, jumps past already-signed stages directly to the next unsigned stage.
        If current_signed_stage is provided, advances forward from current_signed_stage + 1 upwards to 21.
        If all subsequent stages up to 21 are signed, returns 22 (Final Archive).
        """
        signed = self.get_signed_stages_set()
        if current_signed_stage is not None:
            signed.add(int(current_signed_stage))
            start_stg = int(current_signed_stage) + 1
        else:
            start_stg = self.current_stage

        for stg in range(start_stg, 22):
            if stg not in signed:
                return stg
        return 22

    def __str__(self):
        return f"{self.full_name} (#{self.archive_number} - کد: {self.national_id})"

class DossierCheck(models.Model):
    """
    Individual promissory / sayadi checks for decile loans (BankCheckTracker) & preparation installments (tashilatCheck).
    """
    CHECK_TYPE_CHOICES = [
        ("LOAN", "تسهیلات وام دهک"),
        ("PREPARATION", "اقساط آماده‌سازی"),
    ]
    dossier = models.ForeignKey(HousingDossier, on_delete=models.CASCADE, related_name='check_items', verbose_name="پرونده")
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES, default="LOAN", db_index=True, verbose_name="نوع چک")
    row_number = models.PositiveSmallIntegerField(default=1, verbose_name="شماره ردیف چک")
    cash_date = models.CharField(max_length=20, blank=True, default="", verbose_name="تاریخ سررسید (شمسی)")
    check_amount = models.BigIntegerField(default=0, verbose_name="مبلغ چک (ریال)")
    check_sayadi_code = models.CharField(max_length=50, blank=True, default="", verbose_name="کد صیادی (۱۶ رقم)")
    bank_name = models.CharField(max_length=50, blank=True, default="", verbose_name="نام بانک صادرکننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        ordering = ["check_type", "row_number", "id"]
        verbose_name = "چک صیادی پرونده مسکن"
        verbose_name_plural = "چک‌های صیادی پرونده‌های مسکن"

    def __str__(self):
        type_lbl = "دهک" if self.check_type == "LOAN" else "آماده‌سازی"
        return f"چک {type_lbl} {self.row_number} پرونده #{self.dossier.archive_number} - {self.check_amount:,} ریال"


class DossierAttachment(models.Model):
    """
    Immutable stage-owned attachments with built-in Scan Viewer data.
    Documents uploaded in any stage CANNOT be deleted by users in other stages.
    """
    if TYPE_CHECKING:
        id: int
    DOC_TYPES = [
        ("NATIONAL_ID", "اسکن کارت ملی و شناسنامه متقاضی"),
        ("SPOUSE_ID", "اسکن مدارک هویتی همسر"),
        ("UNIT_SELECTION", "برگه انتخاب واحد تاییدشده"),
        ("FORM_J", "تصویر و استعلام رسمی فرم (ج) اداره کل"),
        ("BANK_BOOKLET", "اسکن دفترچه اقساط بانک مسکن"),
        ("BANK_LETTER", "نامه معرفی تسهیلات بانک"),
        ("TITLE_DEED", "اسکن سند مالکیت تک‌برگ عرصه و اعیان"),
        ("PREP_CHECK", "چک‌های آماده‌سازی"),
        ("LOAN_CHECK", "چک‌های تسهیلات دهک"),
        ("COMMITMENT_LETTER", "تعهدنامه محضری / ثبتی"),
        ("OTHER", "سایر مستندات و ضمائم"),
    ]

    dossier = models.ForeignKey(HousingDossier, on_delete=models.CASCADE, related_name="attachments")
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name="ترتیب نمایش")
    stage = models.PositiveSmallIntegerField(verbose_name="مرحله بارگذاری (۱ تا ۲۱)")
    doc_type = models.CharField(max_length=30, choices=DOC_TYPES, default="NATIONAL_ID", verbose_name="نوع مدرک")
    title = models.CharField(max_length=200, verbose_name="عنوان مدرک")
    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_sha256 = models.CharField(max_length=64, blank=True, verbose_name="هش SHA-256")
    uploaded_by = models.CharField(max_length=150, verbose_name="بارگذاری‌کننده")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان بارگذاری")
    preview_url = models.TextField(blank=True, verbose_name="پیش‌نمایش تصویر / دیتا")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "پیوست و سند پرونده"
        verbose_name_plural = "پیوست‌های پرونده"

    def delete(self, *args, **kwargs):
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.title} (مرحله {self.stage})"

class WorkflowSignatureLog(models.Model):
    """
    Immutable audit trail for electronic signatures and stage transitions across the 24 stages.
    """
    ACTION_CHOICES = [
        ("SUBMIT", "ثبت و ارسال"),
        ("SIGN", "تایید و امضا"),
        ("RETURN", "برگشت جهت اصلاح"),
        ("SMS", "ارسال پیامک اطلاع‌رسانی"),
        ("ARCHIVE", "بایگانی قطعی"),
        ("REJECT_RED", "رد صلاحیت و بایگانی (فرم ج قرمز)"),
    ]

    dossier = models.ForeignKey(HousingDossier, on_delete=models.CASCADE, related_name="audit_logs")
    from_stage = models.CharField(max_length=150, verbose_name="از مرحله")
    to_stage = models.CharField(max_length=150, verbose_name="به مرحله")
    actor = models.CharField(max_length=150, verbose_name="کاربر اقدام‌کننده")
    role = models.CharField(max_length=150, verbose_name="سمت کاربری")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="نوع اقدام")
    action_label = models.CharField(max_length=100, verbose_name="عنوان اقدام")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="زمان ثبت")
    notes = models.TextField(blank=True, verbose_name="توضیحات و علل اقدام")
    signature_hash = models.CharField(max_length=64, verbose_name="هش الکترونیکی SHA-256")

    class Meta:
        verbose_name = "لاگ گردش کار و امضای الکترونیکی"
        verbose_name_plural = "تاریخچه امضاهای الکترونیکی"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.dossier.archive_number}: {self.action_label} توسط {self.actor}"

class DossierFieldChangeLog(models.Model):
    """
    Detailed audit log tracking exact field-level changes: who, when, field name, old value, new value.
    Ensures complete accountability when any user modifies any field across the workflow.
    """
    dossier = models.ForeignKey(HousingDossier, on_delete=models.CASCADE, related_name="field_changes")
    field_name = models.CharField(max_length=100, verbose_name="نام سیستمی فیلد")
    field_label = models.CharField(max_length=150, verbose_name="عنوان فارسی فیلد")
    old_value = models.TextField(blank=True, null=True, verbose_name="مقدار قبلی")
    new_value = models.TextField(blank=True, null=True, verbose_name="مقدار جدید")
    changed_by = models.CharField(max_length=150, default="کاربر سامانه", verbose_name="اقدام‌کننده")
    role = models.CharField(max_length=150, blank=True, verbose_name="سمت / نقش کاربر")
    stage = models.PositiveSmallIntegerField(default=1, verbose_name="مرحله هنگام ویرایش")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="زمان ویرایش")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="آدرس IP")

    class Meta:
        verbose_name = "لاگ تغییر فیلد"
        verbose_name_plural = "تاریخچه تغییرات فیلدها"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.dossier.archive_number}: {self.field_label} ({self.old_value} -> {self.new_value}) توسط {self.changed_by}"



class DossierSignature(models.Model):
    """
    Tracks the 14 official archival signatures and uploaded signature/stamp images
    for the comprehensive archival summary sheet (شناسنامه جامع بایگانی).
    """
    SLOT_CHOICES = [
        ("brokerage", "۱. مهر و امضاء کارگزاری (مهندسین مشاور ره آزرم بین‌الملل)"),
        ("national_housing", "۲. کارشناس نهضت ملی"),
        ("bank_facility", "۳. استعلام تسهیلات بانکی"),
        ("decile_facility", "۴. تسهیلات دهک"),
        ("contractor_settlement", "۵. تسویه با پیمانکار"),
        ("applicant_settlement", "۶. تسویه با متقاضی"),
        ("other_facilities", "۷. سایر تسهیلات"),
        ("legal", "۸. کارشناس حقوقی"),
        ("form_j", "۹. کارشناس فرم ج"),
        ("evaluation", "۱۰. کارشناس ارزیابی"),
        ("technical", "۱۱. کارشناس فنی و مهندسی"),
        ("real_estate", "۱۲. کارشناس املاک"),
        ("land_bank", "۱۳. کارشناس بانک زمین"),
        ("revenue", "۱۴. اداره درآمد (مسئول وصول و درآمد)"),
    ]

    SLOT_TO_STAGES = {
        "brokerage": [1, 2, 7, 8, 9],
        "national_housing": [10],
        "bank_facility": [6, 10],
        "decile_facility": [4, 17],
        "contractor_settlement": [4, 19],
        "applicant_settlement": [5],
        "other_facilities": [4],
        "legal": [15],
        "form_j": [3, 11],
        "evaluation": [16],
        "technical": [12],
        "real_estate": [13],
        "land_bank": [14],
        "revenue": [18],
    }

    dossier = models.ForeignKey(HousingDossier, on_delete=models.CASCADE, related_name="signatures", verbose_name="پرونده")
    slot_key = models.CharField(max_length=50, choices=SLOT_CHOICES, db_index=True, verbose_name="جایگاه امضا")
    signer_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی امضاکننده")
    signer_title = models.CharField(max_length=150, blank=True, verbose_name="سمت / نقش سازمانی")
    signed_date = models.CharField(max_length=50, blank=True, verbose_name="تاریخ و ساعت امضا")
    signature_image = models.ImageField(upload_to="dossier_signatures/", blank=True, null=True, verbose_name="تصویر امضا / مهر")
    uploaded_by = models.CharField(max_length=150, blank=True, verbose_name="کاربر بارگذاری‌کننده")
    uploaded_at = models.DateTimeField(auto_now=True, verbose_name="زمان بارگذاری")

    class Meta:
        verbose_name = "امضای پرونده مسکن"
        verbose_name_plural = "امضاهای ۱۴ گانه پرونده مسکن"
        unique_together = ("dossier", "slot_key")

    def get_slot_key_display(self) -> str:
        return dict(self.SLOT_CHOICES).get(self.slot_key, self.slot_key)

    @property
    def date_part(self):
        m = _SIGNED_AT_RE.match(self.signed_date or "")
        return m.group(1) if m else (self.signed_date or "")

    @property
    def time_part(self):
        m = _SIGNED_AT_RE.match(self.signed_date or "")
        return (m.group(2) or "") if m else ""

    @property
    def ref_code(self):
        """Short tamper-evident reference (HMAC with SECRET_KEY). Changes if name/date/slot is edited."""
        if not (self.signer_name and self.signed_date):
            return ""
        msg = f"{self.dossier.archive_number}|{self.slot_key}|{self.signer_name}|{self.signed_date}"
        return hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()[:8].upper()

    def __str__(self):
        return f"امضای {self.get_slot_key_display()} پرونده #{self.dossier.archive_number}"


class UserProfile(models.Model):
    """
    Expert and Administrator user profile tracking organization, role, credentials, and signing rights.
    """
    ORGANIZATION_CHOICES = [
        ("brokerage", "واحد کارگزاری مسکن"),
        ("directorate", "اداره کل راه و شهرسازی"),
        ("system", "مدیریت فناوری و امنیت سامانه"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="حساب کاربری")
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")
    personnel_code = models.CharField(max_length=30, blank=True, verbose_name="کد پرسنلی / نظام مهندسی")
    organization = models.CharField(max_length=20, choices=ORGANIZATION_CHOICES, default="brokerage", verbose_name="سازمان / نهاد متبوع")
    role_title = models.CharField(max_length=100, default="کارشناس اقدام‌کننده", verbose_name="سمت / نقش سازمانی")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس همراه")
    national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی کارشناس")
    can_sign = models.BooleanField(default=True, verbose_name="مجوز امضای الکترونیکی")
    is_active_expert = models.BooleanField(default=True, verbose_name="وضعیت فعالیت کارشناس")

    # Access Level Management & Housing Chief (رئیس مسکن)
    is_housing_chief = models.BooleanField(default=False, verbose_name="رئیس مسکن (اختیارات و دسترسی تام)")
    is_check_admin = models.BooleanField(default=False, verbose_name="مدیر کارگزاری چک (دسترسی به کارمزد و امور مالی چک)")
    allowed_stages = models.CharField(max_length=150, default="all", verbose_name="مراحل مجاز (مثال: 0,1,2 یا all)")

    UI_MODE_CHOICES = [
        ("advanced", "حالت پیشرفته"),
        ("simple", "حالت ساده"),
    ]
    ui_mode = models.CharField(
        max_length=10,
        choices=UI_MODE_CHOICES,
        default="advanced",
        verbose_name="حالت نمایش صفحه پرونده",
    )

    @property
    def date_joined_jalali(self):
        """Returns the Jalali date when the user joined."""
        try:
            import jdatetime
            dt = self.user.date_joined if self.user else None
            if dt:
                return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
            return "-"
        except Exception:
            return "-"

    # Mandatory Security Onboarding & Signature
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="تصویر پروفایل کارشناس")
    must_change_password = models.BooleanField(default=False, verbose_name="الزام به تغییر کلمه عبور در ورود اول")
    signature_image = models.ImageField(upload_to="signatures/", blank=True, null=True, verbose_name="تصویر نمونه امضای الکترونیک")

    class Meta:
        verbose_name = "پروفایل کارشناس و کاربر"
        verbose_name_plural = "کاربران و کارشناسان سامانه"

    def get_allowed_stages_list(self):
        """
        Returns a list of integer stage IDs this user is authorized to action.
        Superadmin, Housing Chief, system managers, or 'all' have access to all stages (1 to 22).
        Handles both comma-separated strings ('1,2,3' or 'all') and old-to-new stage mappings.
        """
        if not self.is_active_expert or not self.user.is_active:
            return []
        if self.user.is_superuser or self.is_housing_chief or self.organization == 'system' or self.allowed_stages == 'all':
            return list(range(1, 23))
        if not self.allowed_stages:
            return []
        try:
            raw = [int(s.strip()) for s in self.allowed_stages.split(',') if s.strip().isdigit()]
            from .stages import map_old_to_new_stage
            result = set()
            for s in raw:
                result.add(s)
                result.add(map_old_to_new_stage(s))
            return sorted(result)
        except Exception:
            return []

    def can_action_stage(self, stage_number):
        """
        Determines whether this expert can edit, sign, or return a dossier at the given stage.
        Superadmin, Housing Chief (رئیس مسکن), and system managers have unrestricted authority.
        """
        if not self.is_active_expert or not self.user.is_active:
            return False
        if self.user.is_superuser or self.is_housing_chief or self.organization == 'system' or self.allowed_stages == 'all':
            return True
        try:
            return int(stage_number) in self.get_allowed_stages_list()
        except Exception:
            return False

    def can_view_all_audit_logs(self):
        """
        Grants full visibility to the system-wide audit trail and field logs.
        """
        return self.user.is_superuser or self.is_housing_chief or self.organization == 'system'

    def __str__(self):
        chief_tag = " [رئیس مسکن]" if self.is_housing_chief else ""
        return f"{self.full_name} ({self.role_title}){chief_tag}"


class BankLetter(models.Model):
    """
    Official Bank Introduction Letters archive and batch tracking.
    """
    if TYPE_CHECKING:
        id: int
        dossiers: Any
    letter_number = models.CharField(max_length=100, unique=True, verbose_name="شماره نامه رسمی بانک")
    letter_date = models.CharField(max_length=20, verbose_name="تاریخ نامه بانک (شمسی)")
    bank_code = models.CharField(max_length=20, blank=True, verbose_name="کد بانک عامل")
    bank_name = models.CharField(max_length=100, blank=True, verbose_name="نام بانک عامل")
    project_name = models.CharField(max_length=250, blank=True, verbose_name="عنوان پروژه")
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="کاربر ثبت‌کننده")
    sender_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی ثبت‌کننده")
    sender_role = models.CharField(max_length=150, blank=True, verbose_name="سمت اداری ثبت‌کننده")
    notes = models.TextField(blank=True, verbose_name="توضیحات و رونوشت")
    dossiers = models.ManyToManyField(HousingDossier, related_name="bank_letters", blank=True, verbose_name="پرونده‌های این نامه")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت در سامانه")

    class Meta:
        verbose_name = "نامه معرفی به بانک"
        verbose_name_plural = "سوابق و بایگانی نامه‌های بانک"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"نامه {self.letter_number} مورخ {self.letter_date}"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            full_name=instance.get_full_name() or instance.username,
            role_title="مدیر سیستم (ادمین)" if instance.is_superuser else "کارشناس اقدام‌کننده",
            organization="system" if instance.is_superuser else "brokerage"
        )




class ProjectBankMapping(models.Model):
    """
    Maps each of the 96 housing projects to one of the 5 financing banks:
    مسکن، ملی، ملت، صادرات، تجارت
    """
    BANK_CHOICES = [
        ("maskan", "بانک مسکن"),
        ("melli", "بانک ملی"),
        ("mellat", "بانک ملت"),
        ("saderat", "بانک صادرات"),
        ("tejarat", "بانک تجارت"),
    ]
    BANK_NAMES = {
        "maskan": "بانک مسکن",
        "melli": "بانک ملی",
        "mellat": "بانک ملت",
        "saderat": "بانک صادرات",
        "tejarat": "بانک تجارت",
    }
    project_code = models.CharField(max_length=50, blank=True, verbose_name="کد پروژه")
    project_name = models.CharField(max_length=250, unique=True, verbose_name="نام پروژه")
    bank_code = models.CharField(max_length=20, choices=BANK_CHOICES, default="maskan", verbose_name="بانک عامل")
    branch_code = models.CharField(max_length=50, blank=True, verbose_name="کد شعبه")
    branch_name = models.CharField(max_length=150, blank=True, verbose_name="نام شعبه")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        id: int

    def get_bank_code_display(self) -> str:
        return self.BANK_NAMES.get(self.bank_code, self.bank_code)

    class Meta:
        verbose_name = "تخصیص پروژه به بانک عامل"
        verbose_name_plural = "تخصیص پروژه‌ها به بانک‌های عامل"

    def __str__(self):
        return f"{self.project_name} -> {self.get_bank_code_display()}"
