import hashlib
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی متقاضی")
    father_name = models.CharField(max_length=100, verbose_name="نام پدر")
    birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد (شمسی)")
    
    applicant_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس متقاضی")
    selection_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="رتبه انتخاب واحد")
    
    # Form J Inquiries & Status
    applicant_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج متقاضی")
    applicant_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل متقاضی")
    applicant_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج متقاضی")

    # Spouse fields (Crucial for Couples Scheme - طرح زوجین)
    spouse_full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی همسر")
    spouse_father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر همسر")
    spouse_national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی همسر")
    spouse_birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد همسر")
    spouse_id_number = models.CharField(max_length=20, blank=True, verbose_name="شماره شناسنامه همسر")
    spouse_birth_place = models.CharField(max_length=100, blank=True, verbose_name="محل تولد / صدور همسر")
    spouse_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج همسر")
    spouse_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل همسر")
    spouse_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج همسر")
    marital_status = models.CharField(max_length=50, default="متاهل (واجد شرایط طرح زوجین)", blank=True, verbose_name="وضعیت تاهل")
    is_married_confirmed = models.BooleanField(default=True, verbose_name="احراز زوجیت و تایید تاهل")
    
    decile = models.PositiveSmallIntegerField(default=1, verbose_name="دهک درآمدی")

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
    net_unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=85.00, verbose_name="متراژ مفید واحد (م²)")
    common_area = models.DecimalField(max_digits=7, decimal_places=2, default=25.00, verbose_name="متراژ مشاعات (م²)")
    total_area = models.DecimalField(max_digits=7, decimal_places=2, default=110.00, verbose_name="جمع کل متراژ واحد (م²)")
    unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=85.00, verbose_name="مساحت واحد")

    storage_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره انباری")
    storage_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت انباری")
    parking_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره پارکینگ")
    parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت پارکینگ")
    covered_parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=11.25, verbose_name="متراژ پارکینگ مسقف (م²)")
    base_cost_without_loan = models.BigIntegerField(default=4500000000, verbose_name="قیمت پایه بدون وام بانکی (ریال)")
    bank_loan_amount = models.BigIntegerField(default=6500000000, verbose_name="مبلغ وام بانکی مسکن (ریال)")

    registration_section = models.CharField(max_length=100, blank=True, verbose_name="بخش ثبتی")
    main_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک اصلی")
    separated_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک مفروز")
    sub_plaque = models.IntegerField(null=True, blank=True, verbose_name="فرعی از")
    plot_number = models.IntegerField(null=True, blank=True, verbose_name="شماره قطعه")

    class Meta:
        verbose_name = "اطلاعات انتخاب واحد متقاضی"
        verbose_name_plural = "بانک اطلاعات انتخاب واحد (پیش‌ثبت‌نام)"

    def __str__(self):
        return f"{self.full_name} ({self.national_id})"

class HousingDossier(models.Model):
    """
    Main dossier tracking the complete 22-Stage Workflow (Stages 0 to 21).
    Merged from Excel specifications & National Housing Directorate stages.
    """
    STAGE_ROLES = {
        0: ("brokerage", "کارشناس ثبت متقاضی و واحد انتخابی", "ثبت اطلاعات متقاضی و واحد"),
        1: ("brokerage", "کارشناس اطلاعات", "کنترل اطلاعات پلاک ثبتی"),
        2: ("brokerage", "کارشناس اطلاعات (کارگزاری)", "ورود مبلغ تمام شده"),
        3: ("directorate", "کارشناس بررسی فرم ج (عالمی)", "بررسی فرم ج"),
        4: ("directorate", "کارشناس برنامه ریزی مسکن (حیدری)", "ورود مبلغ وام صندوق"),
        5: ("directorate", "کارشناس برنامه ریزی مسکن (حیدری)", "مبلغ نامه (کسر یا تخفیف) پیمانکار"),
        6: ("directorate", "کارشناس برنامه ریزی مسکن (حیدری)", "مبلغ تسهیلات دهک"),
        7: ("directorate", "کارشناس برنامه ریزی مسکن (وصالی)", "تعیین مبلغ باقیمانده نقدی مورد نیاز"),
        8: ("directorate", "کارشناس برنامه ریزی مسکن (وصالی / حیدری)", "ارسال و درج شماره و تاریخ نامه بانک"),
        9: ("brokerage", "کارشناس تشکیل پرونده کارگزاری", "اسکن مدارک و دفترچه اقساط"),
        10: ("brokerage", "مدیرعامل کارگزاری", "تأیید مدیرعامل کارگزاری"),
        11: ("directorate", "کارشناس نهضت ملی مسکن و استعلام تسهیلات بانکی", "بررسی استعلام تسهیلات بانکی"),
        12: ("directorate", "کارشناس فنی و مهندسی", "بررسی مشخصات فنی، پلاک و عرصه"),
        13: ("directorate", "کارشناس املاک", "بررسی و بارگذاری سند املاک"),
        14: ("directorate", "کارشناس بانک زمین", "بررسی اطلاعات بانک زمین"),
        15: ("directorate", "کارشناس حقوقی", "بررسی حقوقی و استعلامات اراضی"),
        16: ("directorate", "کارشناس فرم ج", "تطبیق نهایی فرم ج اداره کل"),
        17: ("directorate", "کارشناس ارزیابی", "ارزیابی قدرالسهم و اجاره عرصه"),
        18: ("brokerage", "کارشناس اخذ اجاره و آماده سازی و تسهیلات دهک", "اخذ اجاره، آماده‌سازی و چک دهک"),
        19: ("directorate", "کارشناس تسویه با پیمانکار", "تسویه حساب با پیمانکار سازنده"),
        20: ("directorate", "کارشناس صدور نامه محضر", "صدور نامه معرفی به دفتر اسناد رسمی (محضر)"),
        21: ("directorate", "کارشناس بایگانی", "مشاهده فرم نهایی و بایگانی قطعی پرونده"),
    }

    # Identifiers
    national_id = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="کدملی / شماره پیشنویس")
    archive_number = models.PositiveIntegerField(unique=True, db_index=True, verbose_name="شماره بایگانی")
    current_stage = models.PositiveSmallIntegerField(default=0, db_index=True, verbose_name="مرحله جاری (۰ تا ۲۱)")
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
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی متقاضی")
    father_name = models.CharField(max_length=100, verbose_name="نام پدر")
    birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد (شمسی)")
    applicant_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس متقاضی")
    selection_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="رتبه انتخاب واحد")

    # Form J Inquiries & Status
    applicant_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج متقاضی")
    applicant_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل متقاضی")
    applicant_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج متقاضی")
    
    # Specific Spouse Fields (Crucial for Couples Scheme - طرح زوجین)
    spouse_full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی همسر")
    spouse_father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر همسر")
    spouse_national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی همسر")
    spouse_birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد همسر")
    spouse_id_number = models.CharField(max_length=20, blank=True, verbose_name="شماره شناسنامه همسر")
    spouse_birth_place = models.CharField(max_length=100, blank=True, verbose_name="محل تولد / صدور همسر")
    spouse_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج همسر")
    spouse_form_j_directorate_status = models.CharField(max_length=50, default="تایید نهایی اداره کل", blank=True, verbose_name="استعلام اداره کل همسر")
    spouse_form_j_red_description = models.TextField(blank=True, verbose_name="علت و توضیحات کد قرمز فرم ج همسر")
    marital_status = models.CharField(max_length=50, default="متاهل (واجد شرایط طرح زوجین)", blank=True, verbose_name="وضعیت تاهل")
    is_married_confirmed = models.BooleanField(default=True, verbose_name="احراز زوجیت و تایید تاهل")

    decile = models.PositiveSmallIntegerField(default=1, verbose_name="دهک درآمدی (۱ تا ۱۰)")

    site = models.CharField(max_length=100, verbose_name="سایت")
    project = models.CharField(max_length=200, verbose_name="نام پروژه")
    construction_type = models.CharField(max_length=50, default="آپارتمانی", verbose_name="نوع ساخت")
    block_name = models.CharField(max_length=50, blank=True, verbose_name="نام بلوک")
    block_code = models.CharField(max_length=50, blank=True, verbose_name="کد بلوک")
    floor_number = models.PositiveSmallIntegerField(default=1, verbose_name="شماره طبقه")
    unit_number = models.PositiveIntegerField(default=1, verbose_name="شماره واحد")
    unit_code = models.CharField(max_length=50, blank=True, verbose_name="کد واحد")
    bedroom_count = models.PositiveSmallIntegerField(default=2, verbose_name="تعداد خواب")
    unit_direction = models.CharField(max_length=50, default="شمال غربی", blank=True, verbose_name="جهت واحد")
    net_unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=85.00, verbose_name="متراژ مفید واحد (م²)")
    common_area = models.DecimalField(max_digits=7, decimal_places=2, default=25.00, verbose_name="متراژ مشاعات (م²)")
    total_area = models.DecimalField(max_digits=7, decimal_places=2, default=110.00, verbose_name="جمع کل متراژ واحد (م²)")
    unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=85.00, verbose_name="مساحت واحد")
    storage_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره انباری")
    storage_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت انباری")
    parking_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره پارکینگ")
    parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت پارکینگ")
    covered_parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=11.25, verbose_name="متراژ پارکینگ مسقف (م²)")

    # Stage 2 & 18: Plot & Registry Fields
    registration_section = models.CharField(max_length=100, blank=True, verbose_name="بخش ثبتی")
    main_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک اصلی")
    separated_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک مفروز")
    sub_plaque = models.IntegerField(null=True, blank=True, verbose_name="فرعی از")
    plot_number = models.IntegerField(null=True, blank=True, verbose_name="شماره قطعه")

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
    bank_letter_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ نامه بانک (شمسی)")

    # Stage 19: Valuation Fields
    total_land_share = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="جمع کل قدرالسهم (م²)")
    past_years_rent = models.BigIntegerField(default=0, verbose_name="مبلغ اجاره سنوات تا پایان سال جاری")
    current_year_rent = models.BigIntegerField(default=0, verbose_name="مبلغ اجاره سال جاری")
    land_lease_year = models.CharField(max_length=4, default="1403", blank=True, verbose_name="سال اجاره عرصه")
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

    class Meta:
        verbose_name = "پرونده مسکن متقاضی"
        verbose_name_plural = "پرونده‌های مسکن متقاضیان"
        ordering = ["-archive_number"]

    def save(self, *args, **kwargs):
        # Auto-increment archive_number starting strictly from 100001
        if not self.archive_number:
            max_num = HousingDossier.objects.aggregate(models.Max('archive_number'))['archive_number__max']
            self.archive_number = (max_num + 1) if max_num else 100001

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
    def current_stage_title(self):
        return self.STAGE_ROLES.get(self.current_stage, ("-", "-", "-"))[2]

    @property
    def is_red_form_j(self):
        return ("قرمز" in (self.applicant_form_j_status or "")) or ("قرمز" in (self.spouse_form_j_status or ""))

    @property
    def is_rejected(self):
        return self.status == "REJECTED_RED"

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
    DOC_TYPES = [
        ("NATIONAL_ID", "اسکن کارت ملی و شناسنامه متقاضی"),
        ("SPOUSE_ID", "اسکن مدارک هویتی همسر"),
        ("UNIT_SELECTION", "برگه انتخاب واحد تاییدشده"),
        ("BANK_BOOKLET", "اسکن دفترچه اقساط بانک مسکن"),
        ("BANK_LETTER", "نامه معرفی تسهیلات بانک"),
        ("TITLE_DEED", "اسکن سند مالکیت تک‌برگ عرصه و اعیان"),
        ("PREP_CHECK", "چک‌های آماده‌سازی"),
        ("LOAN_CHECK", "چک‌های تسهیلات دهک"),
        ("COMMITMENT_LETTER", "تعهدنامه محضری / ثبتی"),
        ("OTHER", "سایر مستندات و ضمائم"),
    ]

    dossier = models.ForeignKey(HousingDossier, on_delete=models.CASCADE, related_name="attachments")
    stage = models.PositiveSmallIntegerField(verbose_name="مرحله بارگذاری (۱ تا ۲۴)")
    doc_type = models.CharField(max_length=30, choices=DOC_TYPES, default="NATIONAL_ID", verbose_name="نوع مدرک")
    title = models.CharField(max_length=200, verbose_name="عنوان مدرک")
    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_sha256 = models.CharField(max_length=64, blank=True, verbose_name="هش SHA-256")
    uploaded_by = models.CharField(max_length=150, verbose_name="بارگذاری‌کننده")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان بارگذاری")
    preview_url = models.TextField(blank=True, verbose_name="پیش‌نمایش تصویر / دیتا")

    class Meta:
        verbose_name = "پیوست و سند پرونده"
        verbose_name_plural = "پیوست‌های پرونده"

    def delete(self, *args, **kwargs):
        # Strict Rule: Documents uploaded in any stage CANNOT be deleted by other stages
        if self.dossier.current_stage != self.stage:
            raise ValidationError(f"مدارک بارگذاری شده در مرحله {self.stage} توسط سایر مراحل قابل حذف نمی‌باشد.")
        super().delete(*args, **kwargs)

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

    # Mandatory Security Onboarding & Signature
    must_change_password = models.BooleanField(default=False, verbose_name="الزام به تغییر کلمه عبور در ورود اول")
    signature_image = models.ImageField(upload_to="signatures/", blank=True, null=True, verbose_name="تصویر نمونه امضای الکترونیک")

    class Meta:
        verbose_name = "پروفایل کارشناس و کاربر"
        verbose_name_plural = "کاربران و کارشناسان سامانه"

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
            allowed = [int(s.strip()) for s in self.allowed_stages.split(',') if s.strip().isdigit()]
            return int(stage_number) in allowed
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


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            full_name=instance.get_full_name() or instance.username,
            role_title="مدیر سیستم (ادمین)" if instance.is_superuser else "کارشناس اقدام‌کننده",
            organization="system" if instance.is_superuser else "brokerage"
        )


