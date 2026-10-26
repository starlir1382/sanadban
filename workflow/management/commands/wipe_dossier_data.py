import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection, transaction
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
    help = "Wipes all housing dossier data, logs, attachments, checks, bank letters, and associated media files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm irreversible deletion of all dossier records and uploaded dossier media.",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]

        dossier_models = [
            ("DossierSignature", DossierSignature),
            ("WorkflowSignatureLog", WorkflowSignatureLog),
            ("DossierFieldChangeLog", DossierFieldChangeLog),
            ("DossierAttachment", DossierAttachment),
            ("DossierCheck", DossierCheck),
            ("BankLetter", BankLetter),
            ("HousingDossier", HousingDossier),
        ]

        table_names = [
            "workflow_dossiersignature",
            "workflow_workflowsignaturelog",
            "workflow_dossierfieldchangelog",
            "workflow_dossierattachment",
            "workflow_dossiercheck",
            "workflow_bankletter_dossiers",
            "workflow_bankletter",
            "workflow_housingdossier",
        ]

        self.stdout.write(self.style.WARNING("=== DOSSIER DATA WIPE INSPECTION ==="))

        # 1. Inspect database records
        counts = {}
        for name, model in dossier_models:
            cnt = model.objects.count()
            counts[name] = cnt
            self.stdout.write(f"  {name}: {cnt} rows")

        # 2. Inspect media files to delete
        media_root = settings.MEDIA_ROOT
        items_to_delete = []
        protected_items = ["signatures"]

        if os.path.exists(media_root):
            for entry in os.listdir(media_root):
                if entry in protected_items:
                    continue
                full_path = os.path.join(media_root, entry)
                items_to_delete.append(full_path)

        self.stdout.write(f"\nMedia items under {media_root} to remove ({len(items_to_delete)} items):")
        for p in items_to_delete:
            self.stdout.write(f"  - {p}")

        self.stdout.write(f"\nProtected media items (will NOT be touched):")
        for p in protected_items:
            self.stdout.write(f"  - {os.path.join(media_root, p)}")

        # Dry-run check
        if not confirm:
            self.stdout.write(
                self.style.NOTICE(
                    "\n[DRY RUN] No records or files were deleted. Re-run with --confirm to perform actual wipe."
                )
            )
            return

        # Execute wipe
        self.stdout.write(self.style.NOTICE("\nExecuting wipe with --confirm..."))

        with transaction.atomic():
            # Delete in foreign-key safe order
            for name, model in dossier_models:
                deleted_cnt, _ = model.objects.all().delete()
                self.stdout.write(f"  Deleted {deleted_cnt} records from {name}")

            # Reset SQLite autoincrement sequences
            with connection.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(table_names))
                cursor.execute(
                    f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
                    table_names,
                )
                self.stdout.write(f"  Reset sqlite_sequence for: {', '.join(table_names)}")

        # Delete media files/directories
        deleted_media_count = 0
        for p in items_to_delete:
            if os.path.isdir(p):
                shutil.rmtree(p)
                deleted_media_count += 1
                self.stdout.write(f"  Removed directory: {p}")
            elif os.path.isfile(p):
                os.remove(p)
                deleted_media_count += 1
                self.stdout.write(f"  Removed file: {p}")

        # Re-create empty dossier_signatures directory if needed
        dossier_sig_dir = os.path.join(media_root, "dossier_signatures")
        os.makedirs(dossier_sig_dir, exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully wiped all dossier data and {deleted_media_count} media paths."))
        self.stdout.write(self.style.SUCCESS("All dossier counters and primary keys have been reset to 1."))
