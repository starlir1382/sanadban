import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from workflow.models import (
    HousingDossier,
    DossierAttachment,
    WorkflowSignatureLog,
    DossierFieldChangeLog,
    DossierSignature,
    DossierCheck,
    BankLetter,
)


class Command(BaseCommand):
    help = (
        "Resets all dossiers back to Stage 1 (مرحله ۱ / مرحله ۰ قدیم), "
        "clears all workflow logs, signatures, checks, and scan files, "
        "without touching users or user profiles."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm execution of reset for all dossiers, logs, and scans.",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Completely delete dossier records as well instead of resetting them to Stage 1.",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]
        wipe_mode = options["wipe"]

        self.stdout.write(self.style.WARNING("=================================================="))
        self.stdout.write(self.style.WARNING("       DOSSIER RESET & AUDIT WIPE INSPECTION      "))
        self.stdout.write(self.style.WARNING("=================================================="))

        dossier_count = HousingDossier.objects.count()
        sig_log_count = WorkflowSignatureLog.objects.count()
        change_log_count = DossierFieldChangeLog.objects.count()
        sig_count = DossierSignature.objects.count()
        check_count = DossierCheck.objects.count()
        att_count = DossierAttachment.objects.count()

        self.stdout.write(f"  Housing Dossiers:          {dossier_count} records")
        self.stdout.write(f"  Workflow Signature Logs:   {sig_log_count} records")
        self.stdout.write(f"  Field Change Logs:         {change_log_count} records")
        self.stdout.write(f"  Stage Signatures:          {sig_count} records")
        self.stdout.write(f"  Dossier Checks:            {check_count} records")
        self.stdout.write(f"  Dossier Attachments/Scans: {att_count} records")

        # Media files inspection
        media_root = settings.MEDIA_ROOT
        items_to_delete = []
        protected_items = ["signatures", "avatars", "base_land_rates.csv", "base_land_rates.xlsx"]

        if os.path.exists(media_root):
            for entry in os.listdir(media_root):
                if entry in protected_items:
                    continue
                full_path = os.path.join(media_root, entry)
                items_to_delete.append(full_path)

        self.stdout.write(f"\n  Scan/Document directories to clean under uploads: {len(items_to_delete)}")
        self.stdout.write(f"  Protected items (User signatures, avatars, land rates): {protected_items}")
        self.stdout.write(self.style.SUCCESS("  Users and UserProfiles: 100% PROTECTED (will NOT be touched)\n"))

        if not confirm:
            self.stdout.write(
                self.style.NOTICE(
                    "--------------------------------------------------------------------\n"
                    "[DRY RUN] No data was changed.\n"
                    "To execute this reset, run with --confirm:\n"
                    "  python manage.py reset_dossiers --confirm\n"
                    "  (or to completely wipe dossier rows: python manage.py reset_dossiers --wipe --confirm)\n"
                    "--------------------------------------------------------------------"
                )
            )
            return

        self.stdout.write(self.style.NOTICE("Executing reset with --confirm..."))

        with transaction.atomic():
            # 1. Clear auxiliary logs and checks
            WorkflowSignatureLog.objects.all().delete()
            DossierFieldChangeLog.objects.all().delete()
            DossierSignature.objects.all().delete()
            DossierCheck.objects.all().delete()
            DossierAttachment.objects.all().delete()
            BankLetter.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  ✓ All signature logs, field change logs, checks, bank letters, and attachments wiped."))

            # 2. Reset or Wipe dossiers
            if wipe_mode:
                HousingDossier.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"  ✓ Completely wiped all {dossier_count} housing dossiers."))
            else:
                updated_count = HousingDossier.objects.all().update(
                    current_stage=1,
                    status="IN_PROGRESS",
                    is_locked=False,
                    is_cash_rent_confirmed=False,
                    cash_rent_confirmed_by="",
                    cash_rent_confirmed_at=None,
                    is_preparation_checks_confirmed=False,
                    prep_checks_confirmed_by="",
                    prep_checks_confirmed_at=None,
                    is_decile_loan_confirmed=False,
                    loan_checks_confirmed_by="",
                    loan_checks_confirmed_at=None,
                    return_reason="",
                    return_by="",
                    return_from_stage=None,
                )
                self.stdout.write(self.style.SUCCESS(f"  ✓ All {updated_count} dossiers reset back to Stage 1 (ورود اطلاعات)."))

            # 3. Clean physical scan files
            removed_files_count = 0
            for item_path in items_to_delete:
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        removed_files_count += 1
                    elif os.path.isfile(item_path):
                        os.remove(item_path)
                        removed_files_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Could not remove {item_path}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"  ✓ Removed {removed_files_count} scan folders/files."))
            self.stdout.write(self.style.SUCCESS("  ✓ Users and UserProfiles remain 100% intact."))

        self.stdout.write(self.style.SUCCESS("\nDone! Dossier workflow reset successfully completed."))
