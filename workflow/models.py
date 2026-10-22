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
    
    # Spouse fields (Crucial for Couples Scheme - طرح زوجین)
    spouse_full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی همسر")
    spouse_father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر همسر")
    spouse_national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی همسر")
    spouse_birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد همسر")
    spouse_id_number = models.CharField(max_length=20, blank=True, verbose_name="شماره شناسنامه همسر")
    spouse_birth_place = models.CharField(max_length=100, blank=True, verbose_name="محل تولد / صدور همسر")
    spouse_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج همسر")
    marital_status = models.CharField(max_length=50, default="متاهل (واجد شرایط طرح زوجین)", blank=True, verbose_name="وضعیت تاهل")
    is_married_confirmed = models.BooleanField(default=True, verbose_name="احراز زوجیت و تایید تاهل")
    
    decile = models.PositiveSmallIntegerField(default=1, verbose_name="دهک درآمدی")

    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, verbose_name="سایت")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, verbose_name="پروژه")
    construction_type = models.CharField(max_length=50, default="آپارتمانی", verbose_name="نوع ساخت")
    block_name = models.CharField(max_length=50, blank=True, verbose_name="نام بلوک")
    floor_number = models.PositiveSmallIntegerField(default=1, verbose_name="شماره طبقه")
    unit_number = models.PositiveIntegerField(default=1, verbose_name="شماره واحد")
    unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=85.00, verbose_name="مساحت واحد")

    storage_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره انباری")
    storage_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت انباری")
    parking_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره پارکینگ")
    parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت پارکینگ")
    base_cost_without_loan = models.BigIntegerField(default=4500000000, verbose_name="قیمت پایه بدون وام ۶۵۰ میلیونی (ریال)")

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
    Main dossier tracking the complete 24-Stage Workflow (Stages 1 to 24).
    Merged from Excel specifications & 24 rental agreement stages.
    """
    STAGE_ROLES = {
        1: ("کارگزاری", "کارشناس ثبت درخواست کارگزاری", "ورود اطلاعات متقاضی، همسر، واحد و پروژه"),
        2: ("کارگزاری", "کارشناس ثبتی کارگزاری", "ورود اطلاعات ثبتی عرصه و پلاک"),
        3: ("کارگزاری", "کارشناس مالی کارگزاری", "ورود مبلغ تمام‌شده بدون وام ۶۵۰ میلیون تومانی"),
        4: ("کارگزاری", "مدیرعامل کارگزاری", "تأیید مدیرعامل کارگزاری"),
        5: ("اداره کل", "کارشناس بررسی فرم جیم", "کارشناس بررسی فرم جیم"),
        6: ("کارگزاری", "کارشناس مالی کارگزاری", "ورود مبلغ وام صندوق"),
        7: ("اداره کل", "کارشناس پیمانکاران اداره کل", "ورود مبلغ نامه پیمانکار"),
        8: ("اداره کل", "کارشناس تسهیلات دهک اداره کل", "ورود مبلغ وام دهک"),
        9: ("کارگزاری", "کارشناس امور متقاضیان", "تعیین مبلغ آورده نقدی متقاضی و ارسال پیامک"),
        10: ("کارگزاری", "کارشناس مالی کارگزاری", "تأیید تأمین مبلغ آورده متقاضی"),
        11: ("کارگزاری", "کارشناس امور بانکی", "ارسال و درج شماره نامه بانک"),
        12: ("کارگزاری", "کارشناس اسکن و بایگانی کارگزاری", "اسکن مدارک و دفترچه قسط"),
        13: ("اداره کل", "کارشناس نهضت ملی مسکن", "کارشناس نهضت ملی مسکن"),
        14: ("اداره کل", "کارشناس ثبت فرم ج", "کارشناس ثبت فرم ج"),
        15: ("اداره کل", "کارشناس فنی و مهندسی", "کارشناس فنی و مهندسی"),
        16: ("اداره کل", "کارشناس املاک", "کارشناس املاک"),
        17: ("اداره کل", "کارشناس بانک زمین", "کارشناس بانک زمین"),
        18: ("اداره کل", "کارشناس حقوقی", "کارشناس حقوقی"),
        19: ("اداره کل", "کارشناس ارزیابی", "کارشناس ارزیابی (تعیین اجاره و آماده‌سازی)"),
        20: ("کارگزاری", "کارشناس وصول کارگزاری", "دریافت چک‌های وام دهک"),
        21: ("کارگزاری", "کارشناس مالی کارگزاری", "دریافت نقد و اقساط آماده‌سازی و اجاره"),
        22: ("اداره کل", "کارشناس تسویه با پیمانکار", "کارشناس تسویه با پیمانکار سازنده"),
        23: ("اداره کل", "کارشناس صدور نامه محضر", "چاپ فرم مراحل و نامه محضر"),
        24: ("اداره کل", "کارشناس بایگانی اداره کل", "بایگانی نهایی پرونده"),
    }

    # Identifiers
    national_id = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="کدملی / شماره پیشنویس")
    archive_number = models.PositiveIntegerField(unique=True, db_index=True, verbose_name="شماره بایگانی")
    current_stage = models.PositiveSmallIntegerField(default=1, db_index=True, verbose_name="مرحله جاری (۱ تا ۲۴)")
    is_locked = models.BooleanField(default=False, verbose_name="قفل نهایی بایگانی")

    # Stage 1: Applicant, Spouse & Unit
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی متقاضی")
    father_name = models.CharField(max_length=100, verbose_name="نام پدر")
    birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد (شمسی)")
    
    # Specific Spouse Fields (Crucial for Couples Scheme - طرح زوجین)
    spouse_full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی همسر")
    spouse_father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر همسر")
    spouse_national_id = models.CharField(max_length=10, blank=True, verbose_name="کد ملی همسر")
    spouse_birth_date = models.CharField(max_length=10, blank=True, verbose_name="تاریخ تولد همسر")
    spouse_id_number = models.CharField(max_length=20, blank=True, verbose_name="شماره شناسنامه همسر")
    spouse_birth_place = models.CharField(max_length=100, blank=True, verbose_name="محل تولد / صدور همسر")
    spouse_form_j_status = models.CharField(max_length=50, default="سبز (استعلام شده)", blank=True, verbose_name="وضعیت فرم ج همسر")
    marital_status = models.CharField(max_length=50, default="متاهل (واجد شرایط طرح زوجین)", blank=True, verbose_name="وضعیت تاهل")
    is_married_confirmed = models.BooleanField(default=True, verbose_name="احراز زوجیت و تایید تاهل")

    decile = models.PositiveSmallIntegerField(default=1, verbose_name="دهک درآمدی (۱ تا ۱۰)")

    site = models.CharField(max_length=100, verbose_name="سایت")
    project = models.CharField(max_length=200, verbose_name="نام پروژه")
    construction_type = models.CharField(max_length=50, default="آپارتمانی", verbose_name="نوع ساخت")
    block_name = models.CharField(max_length=50, blank=True, verbose_name="نام بلوک")
    floor_number = models.PositiveSmallIntegerField(default=1, verbose_name="شماره طبقه")
    unit_number = models.PositiveIntegerField(default=1, verbose_name="شماره واحد")
    unit_area = models.DecimalField(max_digits=7, decimal_places=2, default=85.00, verbose_name="مساحت واحد")
    storage_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره انباری")
    storage_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت انباری")
    parking_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="شماره پارکینگ")
    parking_area = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="مساحت پارکینگ")

    # Stage 2 & 18: Plot & Registry Fields
    registration_section = models.CharField(max_length=100, blank=True, verbose_name="بخش ثبتی")
    main_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک اصلی")
    separated_plaque = models.IntegerField(null=True, blank=True, verbose_name="پلاک مفروز")
    sub_plaque = models.IntegerField(null=True, blank=True, verbose_name="فرعی از")
    plot_number = models.IntegerField(null=True, blank=True, verbose_name="شماره قطعه")

    # Stage 3: Base Cost without 650M Toman loan
    base_cost_without_loan = models.BigIntegerField(default=4500000000, verbose_name="قیمت تمام شده بدون وام ۶۵۰ میلیونی (ریال)")

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

    # Stage 22: Cash & Non-cash Prep & Rent Installments
    cash_preparation_amount = models.BigIntegerField(default=0, verbose_name="مبلغ نقدی آماده سازی")
    non_cash_preparation_amount = models.BigIntegerField(default=0, verbose_name="مبلغ غیرنقدی آماده سازی")
    is_cash_rent_confirmed = models.BooleanField(default=False, verbose_name="تایید مبلغ نقدی اجاره")
    is_decile_loan_confirmed = models.BooleanField(default=False, verbose_name="تایید چک‌های وام دهک")

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
    def formatted_equity(self):
        val = self.applicant_equity if self.applicant_equity is not None else self.base_cost_without_loan
        if val is None:
            return "0"
        return f"{val:,}"

    def __str__(self):
        return f"{self.full_name} (#{self.archive_number} - کد: {self.national_id})"

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

    class Meta:
        verbose_name = "پروفایل کارشناس و کاربر"
        verbose_name_plural = "کاربران و کارشناسان سامانه"

    def __str__(self):
        return f"{self.full_name} ({self.role_title})"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            full_name=instance.get_full_name() or instance.username,
            role_title="مدیر سیستم (ادمین)" if instance.is_superuser else "کارشناس اقدام‌کننده",
            organization="system" if instance.is_superuser else "brokerage"
        )


