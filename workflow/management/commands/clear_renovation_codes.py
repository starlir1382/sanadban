"""
workflow/management/commands/clear_renovation_codes.py

Usage:
    # 1. Preview / simulate (dry-run):
    python manage.py clear_renovation_codes --dry-run
    # (Running without --confirm will also default to inspection/dry-run mode)

    # 2. Confirm and clear all renovation codes:
    python manage.py clear_renovation_codes --confirm

    # 3. Clear renovation codes for a specific site or project:
    python manage.py clear_renovation_codes --site "رئیسی 560 هکتار" --confirm
    python manage.py clear_renovation_codes --project "نام پروژه" --confirm

    # 4. Exclude locked dossiers from being cleared:
    python manage.py clear_renovation_codes --exclude-locked --confirm
"""
import sys
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from workflow.models import HousingDossier, PreSelectedUnit


class Command(BaseCommand):
    help = "Clear all renovation codes (کد نوسازی شهرداری) from housing dossiers and pre-selected units."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm execution and apply changes to the database.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the cleanup without saving changes to the database.",
        )
        parser.add_argument(
            "--site",
            type=str,
            default="",
            help="Filter cleanup to a specific site name.",
        )
        parser.add_argument(
            "--project",
            type=str,
            default="",
            help="Filter cleanup to a specific project name.",
        )
        parser.add_argument(
            "--exclude-locked",
            action="store_true",
            help="Exclude locked dossiers from having their renovation code cleared (default: clears all).",
        )
        parser.add_argument(
            "--clear-financials",
            action="store_true",
            help="Also reset Section 9 calculated financial fields (total_land_share, current_year_rent, past_years_rent, preparation_cost).",
        )

    def handle(self, *args, **options):
        # Configure UTF-8 stdout for Persian console output
        for stream in (sys.stdout, sys.stderr):
            if stream is not None and hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(encoding="utf-8", errors="backslashreplace")
                except Exception:
                    pass

        confirm = options["confirm"]
        dry_run = options["dry_run"]
        site_filter = (options.get("site") or "").strip()
        project_filter = (options.get("project") or "").strip()
        exclude_locked = options["exclude_locked"]
        clear_financials = options["clear_financials"]

        # If --confirm is not provided, enforce dry-run inspection mode
        is_simulation = dry_run or not confirm

        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("         CLEAR RENOVATION CODES (کد نوسازی)       "))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        if is_simulation:
            self.stdout.write(
                self.style.WARNING(">>> RUNNING IN DRY-RUN / INSPECTION MODE (No changes will be saved) <<<\n")
            )
        else:
            self.stdout.write(
                self.style.NOTICE(">>> RUNNING IN LIVE EXECUTION MODE (--confirm supplied) <<<\n")
            )

        start_time = time.time()

        # Build QuerySet for HousingDossier
        qs = HousingDossier.objects.exclude(renovation_code="").exclude(renovation_code__isnull=True)

        if site_filter:
            qs = qs.filter(site__icontains=site_filter)
            self.stdout.write(f"  Filter by Site: {site_filter}")

        if project_filter:
            qs = qs.filter(project__icontains=project_filter)
            self.stdout.write(f"  Filter by Project: {project_filter}")

        if exclude_locked:
            qs = qs.filter(is_locked=False)
            self.stdout.write("  Excluding locked dossiers: Yes")
        else:
            self.stdout.write("  Include locked dossiers: Yes")

        if clear_financials:
            self.stdout.write(self.style.WARNING("  Also clearing Section 9 financial values: Yes"))
        else:
            self.stdout.write("  Also clearing Section 9 financial values: No (keeping calculated rates)")

        total_matching_dossiers = qs.count()

        # PreSelectedUnit count
        psu_qs = PreSelectedUnit.objects.exclude(renovation_code="").exclude(renovation_code__isnull=True)
        total_matching_psu = psu_qs.count()

        self.stdout.write("\nSummary of records found with کد نوسازی:")
        self.stdout.write(f"  - Housing dossiers matching criteria: {total_matching_dossiers}")
        self.stdout.write(f"  - PreSelectedUnit records matching:   {total_matching_psu}")

        if total_matching_dossiers == 0 and total_matching_psu == 0:
            self.stdout.write(self.style.SUCCESS("\nNo dossiers or units currently have a renovation code set. Nothing to clear."))
            return

        # Show a sample of records to be cleared
        sample_records = list(qs.values("archive_number", "full_name", "project", "plot_number", "block_name", "renovation_code")[:5])
        if sample_records:
            self.stdout.write("\nSample records to be cleared:")
            for s in sample_records:
                self.stdout.write(
                    f"  [Archive: {s['archive_number']}] {s['full_name']} | "
                    f"Proj: {s['project']} | Plot: {s['plot_number']} | Block: {s['block_name']} | "
                    f"Code: {s['renovation_code']}"
                )

        if is_simulation:
            self.stdout.write(
                self.style.NOTICE(
                    "\n--------------------------------------------------------------------\n"
                    "[DRY RUN COMPLETE] No records were modified.\n"
                    "To actually clear the renovation codes in the database, run with --confirm:\n"
                    "    python manage.py clear_renovation_codes --confirm\n"
                    "--------------------------------------------------------------------"
                )
            )
            return

        # Live Execution
        self.stdout.write("\nExecuting update...")
        update_fields = {"renovation_code": ""}
        if clear_financials:
            update_fields.update({
                "total_land_share": None,
                "current_year_rent": None,
                "past_years_rent": None,
                "preparation_cost": None,
            })

        with transaction.atomic():
            cleared_dossiers = qs.update(**update_fields)
            cleared_psu = psu_qs.update(renovation_code="")

        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully cleared renovation codes from {cleared_dossiers} housing dossier(s) "
                f"and {cleared_psu} pre-selected unit(s) in {elapsed:.2f} seconds."
            )
        )
