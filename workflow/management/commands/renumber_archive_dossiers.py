import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from workflow.models import HousingDossier


class Command(BaseCommand):
    help = (
        "Renumbers archive numbers so that only dossiers at Stage >= 8 (or locked) "
        "have official archive numbers (100001, 100002, ...), and all dossiers in "
        "preliminary stages (< 8) have archive_number set to None (using 'ردیف' instead)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually apply changes to the database. Without this flag, runs in dry-run mode.",
        )
        parser.add_argument(
            "--start",
            type=int,
            default=100001,
            help="Starting archive number (default: 100001).",
        )

    def _safe_write(self, msg, style_func=None):
        if style_func:
            msg = style_func(msg)
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            clean_msg = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(clean_msg)

    def handle(self, *args, **options):
        confirm = options["confirm"]
        start_number = options["start"]

        self._safe_write("=" * 65, self.style.WARNING)
        self._safe_write("  RENUMBER ARCHIVE NUMBERS (STAGE >= 8 NUMBERING)", self.style.WARNING)
        self._safe_write("=" * 65, self.style.WARNING)

        # Query all dossiers
        all_dossiers = HousingDossier.objects.all().order_by("id")
        total_count = all_dossiers.count()

        # Qualifying dossiers for archive numbers: current_stage >= 8 or is_locked
        qualifying_qs = HousingDossier.objects.filter(
            Q(current_stage__gte=8) | Q(is_locked=True)
        ).order_by("id")
        qualifying_count = qualifying_qs.count()

        # Preliminary dossiers (< 8 and not locked)
        preliminary_qs = HousingDossier.objects.filter(
            current_stage__lt=8, is_locked=False
        )
        preliminary_count = preliminary_qs.count()

        self._safe_write(f"Total dossiers in system: {total_count:,}")
        self._safe_write(
            f"Dossiers at Stage >= 8 or Locked (will receive official archive numbers): {qualifying_count}",
            self.style.SUCCESS
        )
        self._safe_write(
            f"Dossiers in preliminary stages (< 8) (archive_number will be cleared to None): {preliminary_count:,}\n"
        )

        # Plan the mapping for qualifying dossiers
        renumber_plan = []
        cur_num = start_number
        for d in qualifying_qs:
            renumber_plan.append((d, cur_num))
            cur_num += 1

        self._safe_write("Proposed archive numbers for qualifying dossiers:")
        for d, new_num in renumber_plan:
            name_display = d.full_name or "بدون نام"
            self._safe_write(
                f"  - Dossier ID {d.id} | NID: {d.national_id} | Name: {name_display} | "
                f"Stage: {d.current_stage} | Old: {d.archive_number} -> New: {new_num}"
            )

        if not confirm:
            self._safe_write(
                "\n[DRY RUN] No changes were written to the database. "
                "Run with '--confirm' to execute this renumbering.",
                self.style.NOTICE
            )
            return

        # Execute in atomic transaction
        with transaction.atomic():
            # Step 1: Clear all archive numbers to None to avoid unique constraint collisions
            self._safe_write("\nStep 1: Clearing archive numbers to avoid unique conflicts...")
            HousingDossier.objects.all().update(archive_number=None)

            # Step 2: Assign sequential archive numbers to qualifying dossiers
            self._safe_write(f"Step 2: Assigning {qualifying_count} sequential archive numbers starting from {start_number}...")
            for d, new_num in renumber_plan:
                HousingDossier.objects.filter(id=d.id).update(archive_number=new_num)

        self._safe_write(
            f"\nSUCCESS! {qualifying_count} dossiers renumbered sequentially from {start_number} to {start_number + qualifying_count - 1}. "
            f"{preliminary_count:,} preliminary dossiers now have archive_number=None (displaying 'ردیف').",
            self.style.SUCCESS
        )
