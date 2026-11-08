import hashlib
import time
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import jdatetime

from workflow.models import (
    HousingDossier,
    WorkflowSignatureLog,
    DossierSignature,
)
from workflow.stages import STAGE_ROLES, STAGE_TO_SLOTS


class Command(BaseCommand):
    help = (
        "Automated sequential signing and stage advancement for dossiers:\n"
        "1. Dossiers with bank_letter_number are sequentially signed from current_stage to stage 7.\n"
        "2. Dossiers with Section 2 (ثبتی/پلاک) filled are signed to stage 2 (or 3 via --sec2-target-stage).\n"
        "All signature logs record the designated admin user."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Apply changes to the database. Without this flag, runs in dry-run mode.",
        )
        parser.add_argument(
            "--admin-user",
            type=str,
            default="admin",
            help="Username of admin user to attribute signatures and logs to (default: 'admin').",
        )
        parser.add_argument(
            "--sec2-target-stage",
            type=int,
            default=2,
            choices=[2, 3],
            help="Target stage for Section 2 dossiers (default: 2, i.e. signs stage 1. Set to 3 to also sign stage 2).",
        )
        parser.add_argument(
            "--bank-target-stage",
            type=int,
            default=7,
            help="Target stage for dossiers with bank letter number (default: 7, i.e. signs stages 1 through 6).",
        )
        parser.add_argument(
            "--require-plot-number",
            action="store_true",
            help="Strictly require plot_number (شماره قطعه) to be filled for Section 2 (default: False, optional like renovation_code).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for bulk updates (default: 500).",
        )
        parser.add_argument(
            "--archive-number",
            type=int,
            default=None,
            help="Process only a specific dossier by archive number (for testing).",
        )
        parser.add_argument(
            "--project",
            type=str,
            default=None,
            help="Process only dossiers belonging to a specific project name.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of dossiers processed in each category.",
        )

    def resolve_admin_user(self, username):
        """Finds or falls back to an active admin user."""
        admin_user = User.objects.filter(username=username, is_active=True).first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True, is_active=True).first()
        if not admin_user:
            chief_profile = getattr(
                User.objects.filter(profile__is_housing_chief=True, is_active=True).first(),
                "profile",
                None,
            )
            if chief_profile:
                admin_user = chief_profile.user
        if not admin_user:
            admin_user = User.objects.filter(is_staff=True, is_active=True).first()
        if not admin_user:
            raise RuntimeError("هیچ کاربر ادمین یا فعالی در سیستم برای ثبت لاگ‌ها یافت نشد.")

        profile = getattr(admin_user, "profile", None)
        actor_name = ""
        actor_role = ""
        sig_img = None
        if profile:
            actor_name = profile.full_name or ""
            actor_role = profile.role_title or ""
            sig_img = profile.signature_image
            if not profile.can_sign:
                profile.can_sign = True
                profile.save(update_fields=["can_sign"])

        if not actor_name:
            actor_name = admin_user.get_full_name() or admin_user.username
        if not actor_role:
            actor_role = "مدیر کل سامانه"

        return admin_user, actor_name, actor_role, sig_img

    def handle(self, *args, **options):
        confirm = options["confirm"]
        admin_username = options["admin_user"]
        sec2_target = options["sec2_target_stage"]
        bank_target = options["bank_target_stage"]
        require_plot = options["require_plot_number"]
        batch_size = options["batch_size"]
        target_archive = options["archive_number"]
        target_project = options["project"]
        limit = options["limit"]

        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("      پیشروی و امضای خودکار الکترونیکی پرونده‌ها      "))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        admin_user, actor_name, actor_role, sig_img = self.resolve_admin_user(admin_username)
        self.stdout.write(f"  کاربر ثبت‌کننده امضا:  {admin_user.username} ({actor_name} - {actor_role})")
        self.stdout.write(f"  هدف پرونده‌های بانکی:  رسیدن به مرحله {bank_target} (امضای متوالی مراحل ۱ تا {bank_target - 1})")
        self.stdout.write(f"  هدف پرونده‌های بخش ۲:  رسیدن به مرحله {sec2_target} (امضای متوالی مراحل ۱ تا {sec2_target - 1})")
        self.stdout.write(f"  الزام شماره قطعه:     {'بله (اجباری)' if require_plot else 'خیر (اختیاری همانند کد نوسازی)'}")
        self.stdout.write(f"  اندازه دسته‌ها (Batch): {batch_size}")

        # Base active dossier queryset
        base_qs = HousingDossier.objects.filter(is_locked=False).exclude(
            status__in=["DELETED", "REJECTED_RED"]
        )

        if target_archive:
            base_qs = base_qs.filter(archive_number=target_archive)
        if target_project:
            base_qs = base_qs.filter(project__icontains=target_project)

        # 1. Condition Bank Letter: has bank_letter_number and current_stage < bank_target
        has_bank_cond = ~Q(bank_letter_number__isnull=True) & ~Q(bank_letter_number="")
        bank_qs = base_qs.filter(has_bank_cond, current_stage__lt=bank_target).order_by("id")
        if limit:
            bank_qs = bank_qs[:limit]

        # 2. Condition Section 2: no bank letter, all Section 2 filled (registration_section, main, separated, sub plaques)
        no_bank_cond = Q(bank_letter_number__isnull=True) | Q(bank_letter_number="")
        sec2_cond = (
            ~Q(registration_section__isnull=True)
            & ~Q(registration_section="")
            & Q(main_plaque__isnull=False)
            & Q(separated_plaque__isnull=False)
            & Q(sub_plaque__isnull=False)
        )
        if require_plot:
            sec2_cond &= Q(plot_number__isnull=False)

        sec2_qs = base_qs.filter(no_bank_cond, sec2_cond, current_stage__lt=sec2_target).order_by("id")
        if limit:
            sec2_qs = sec2_qs[:limit]

        bank_count = bank_qs.count() if not limit else len(bank_qs)
        sec2_count = sec2_qs.count() if not limit else len(sec2_qs)

        self.stdout.write("\n" + self.style.WARNING("--- آمار مشمولان ---"))
        self.stdout.write(f"  ۱. پرونده‌های دارای شماره نامه بانک (پیشروی به مرحله {bank_target}): {bank_count} مورد")
        self.stdout.write(f"  ۲. پرونده‌های فاقد نامه بانک با بخش ۲ کامل (پیشروی به مرحله {sec2_target}): {sec2_count} مورد")
        self.stdout.write(f"  مجموع پرونده‌های قابل پیشروی: {bank_count + sec2_count} مورد")

        if bank_count == 0 and sec2_count == 0:
            self.stdout.write(self.style.SUCCESS("\nهیچ پرونده‌ای که واجد شرایط پیشروی باشد یافت نشد."))
            return

        # Show samples
        self.stdout.write("\n" + self.style.WARNING("--- نمونه پرونده‌های انتخابی ---"))
        if bank_count > 0:
            self.stdout.write(self.style.NOTICE("  [نمونه دارای نامه بانک]:"))
            for d in bank_qs[:3]:
                self.stdout.write(
                    f"    - بایگانی {d.archive_number} ({d.full_name or 'بدون نام'}) | "
                    f"نامه بانک: {d.bank_letter_number} | مرحله {d.current_stage} -> {bank_target}"
                )
        if sec2_count > 0:
            self.stdout.write(self.style.NOTICE("  [نمونه بخش ۲ کامل]:"))
            for d in sec2_qs[:3]:
                self.stdout.write(
                    f"    - بایگانی {d.archive_number} ({d.full_name or 'بدون نام'}) | "
                    f"بخش ثبتی: {d.registration_section} | پلاک: {d.main_plaque} / {d.separated_plaque} | "
                    f"مرحله {d.current_stage} -> {sec2_target}"
                )

        if not confirm:
            self.stdout.write("\n" + self.style.ERROR("=" * 60))
            self.stdout.write(self.style.ERROR("  حالت پیش‌نمایش (DRY-RUN) - هیچ تغییری در دیتابیس اعمال نشد."))
            self.stdout.write(self.style.ERROR("  جهت اعمال قطعی تغییرات و ثبت امضاها، دستور را با پرچم --confirm اجرا فرمایید:"))
            self.stdout.write(self.style.SUCCESS("  python manage.py auto_advance_dossiers --confirm"))
            self.stdout.write(self.style.ERROR("=" * 60))
            return

        # LIVE EXECUTION
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("شروع ثبت امضاها و پیشروی مراحل..."))
        start_time = time.time()

        total_processed_bank = 0
        total_logs_bank = 0
        total_processed_sec2 = 0
        total_logs_sec2 = 0

        now_dt = timezone.now()
        try:
            now_jalali = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M")
        except Exception:
            now_jalali = now_dt.strftime("%Y/%m/%d %H:%M")

        # Helper function to advance a batch of dossiers
        def advance_dossier_batch(dossier_list, target_st, reason_label):
            logs_to_create = []
            sigs_to_upsert = {}
            docs_to_update = []
            log_counter = 0

            for d in dossier_list:
                current_st = d.current_stage
                if current_st >= target_st:
                    continue

                for st in range(current_st, target_st):
                    next_st = st + 1
                    cur_role = STAGE_ROLES.get(st, ("-", "-", "-"))[1]
                    cur_title = STAGE_ROLES.get(st, ("-", "-", f"مرحله {st}"))[2]
                    next_title = STAGE_ROLES.get(next_st, ("-", "-", f"مرحله {next_st}"))[2]

                    sig_hash = (
                        "SHA256: "
                        + hashlib.sha256(f"SIGN_AUTO:{d.id}:{st}:{uuid.uuid4()}".encode()).hexdigest()[:24]
                    )

                    if "بانک" in reason_label:
                        notes_text = f"تایید و امضای خودکار سیستمی مرحله {st} بر اساس ثبت شماره نامه بانک ({d.bank_letter_number})."
                    else:
                        notes_text = f"تایید و امضای خودکار سیستمی مرحله {st} بر اساس تکمیل اطلاعات ثبتی و پلاک (بخش ۲)."

                    # Stagger timestamp slightly so chronological ordering is preserved
                    log_time = now_dt + timedelta(seconds=log_counter % 60)
                    log_counter += 1

                    logs_to_create.append(
                        WorkflowSignatureLog(
                            dossier=d,
                            from_stage=f"مرحله {st}: {cur_title}",
                            to_stage=f"مرحله {next_st}: {next_title}",
                            actor=actor_name,
                            role=actor_role,
                            action="SIGN",
                            action_label="تایید و امضای الکترونیکی",
                            signature_hash=sig_hash,
                            notes=notes_text,
                            timestamp=log_time,
                        )
                    )

                    target_slots = STAGE_TO_SLOTS.get(st, [])
                    for slot in target_slots:
                        sigs_to_upsert[(d.id, slot)] = DossierSignature(
                            dossier=d,
                            slot_key=slot,
                            signer_name=actor_name,
                            signer_title=actor_role,
                            signed_date=now_jalali,
                            uploaded_by=admin_user.username,
                            signature_image=sig_img,
                        )

                d.current_stage = target_st
                d.status = "IN_PROGRESS"
                d.return_reason = ""
                d.return_by = ""
                d.return_from_stage = None
                d.updated_at = now_dt
                docs_to_update.append(d)

            with transaction.atomic():
                if docs_to_update:
                    HousingDossier.objects.bulk_update(
                        docs_to_update,
                        ["current_stage", "status", "return_reason", "return_by", "return_from_stage", "updated_at"],
                    )
                if logs_to_create:
                    WorkflowSignatureLog.objects.bulk_create(logs_to_create, batch_size=1000)
                if sigs_to_upsert:
                    DossierSignature.objects.bulk_create(
                        list(sigs_to_upsert.values()),
                        update_conflicts=True,
                        unique_fields=["dossier", "slot_key"],
                        update_fields=["signer_name", "signer_title", "signed_date", "uploaded_by", "signature_image"],
                    )

            return len(docs_to_update), len(logs_to_create)

        # 1. Process Bank Letter Dossiers in chunks
        if bank_count > 0:
            self.stdout.write(f"\n[۱/۲] در حال پیشروی پرونده‌های دارای نامه بانک به مرحله {bank_target}...")
            # Query IDs first for efficient chunking
            bank_ids = list(bank_qs.values_list("id", flat=True))
            for i in range(0, len(bank_ids), batch_size):
                chunk_ids = bank_ids[i : i + batch_size]
                chunk_docs = list(HousingDossier.objects.filter(id__in=chunk_ids).order_by("id"))
                processed, logs_created = advance_dossier_batch(chunk_docs, bank_target, "بانک")
                total_processed_bank += processed
                total_logs_bank += logs_created
                self.stdout.write(f"  پیشرفت: {total_processed_bank} / {len(bank_ids)} پرونده ({total_logs_bank} لاگ امضا)")

        # 2. Process Section 2 Dossiers in chunks
        if sec2_count > 0:
            self.stdout.write(f"\n[۲/۲] در حال پیشروی پرونده‌های بخش ۲ به مرحله {sec2_target}...")
            sec2_ids = list(sec2_qs.values_list("id", flat=True))
            for i in range(0, len(sec2_ids), batch_size):
                chunk_ids = sec2_ids[i : i + batch_size]
                chunk_docs = list(HousingDossier.objects.filter(id__in=chunk_ids).order_by("id"))
                processed, logs_created = advance_dossier_batch(chunk_docs, sec2_target, "بخش ۲")
                total_processed_sec2 += processed
                total_logs_sec2 += logs_created
                self.stdout.write(f"  پیشرفت: {total_processed_sec2} / {len(sec2_ids)} پرونده ({total_logs_sec2} لاگ امضا)")

        elapsed = time.time() - start_time
        self.stdout.write("\n" + self.style.SUCCESS("=================================================="))
        self.stdout.write(self.style.SUCCESS("            عملیات با موفقیت به پایان رسید           "))
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(f"  پرونده‌های بانکی پیشروی‌یافته به مرحله {bank_target}: {total_processed_bank} مورد")
        self.stdout.write(f"  لاگ‌های امضای بانکی ثبت‌شده:                 {total_logs_bank} لاگ")
        self.stdout.write(f"  پرونده‌های بخش ۲ پیشروی‌یافته به مرحله {sec2_target}: {total_processed_sec2} مورد")
        self.stdout.write(f"  لاگ‌های امضای بخش ۲ ثبت‌شده:                 {total_logs_sec2} لاگ")
        self.stdout.write(f"  مجموع کل لاگ‌های امضای ایجادشده:             {total_logs_bank + total_logs_sec2} لاگ")
        self.stdout.write(f"  زمان کل اجرا:                              {elapsed:.2f} ثانیه")
        self.stdout.write(self.style.SUCCESS("=================================================="))
