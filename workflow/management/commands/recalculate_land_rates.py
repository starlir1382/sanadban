"""
workflow/management/commands/recalculate_land_rates.py

Usage:
    python manage.py recalculate_land_rates [--dry-run] [--all] [--fix-parcel-243]

Audits and fixes:
1. Known parcel 243 (B116) typo in LandRate table.
2. Contaminated/guessed renovation_code on HousingDossier records.
3. Recalculates Section 9 values (total_land_share, current_year_rent, past_years_rent, preparation_cost)
   for unlocked dossiers using the verified lookup rules.
"""
from decimal import Decimal
import re
import time

from django.core.management.base import BaseCommand
from django.db import transaction

from workflow.models import HousingDossier, LandRate
from workflow.land_rates import (
    _ensure_cache,
    _CACHE,
    reset_cache,
    strip_code,
    normalize_code,
    normalize_project,
    clean_project_fuzzy,
    normalize_plot,
    normalize_block,
    clean_block_fuzzy,
    get_rate_status,
    apply_land_calculation,
)


class Command(BaseCommand):
    help = "Audit and fix contaminated renovation codes, fix parcel 243 typo, and recalculate Section 9 land values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the cleanup and recalculation without saving changes to the database.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Recalculate Section 9 for all unlocked dossiers, not just mismatched ones.",
        )
        parser.add_argument(
            "--fix-parcel-243",
            action="store_true",
            default=True,
            help="Fix the known row 964 (B116) share coefficient typo in parcel 243 (default: True).",
        )
        parser.add_argument(
            "--no-fix-parcel-243",
            dest="fix_parcel_243",
            action="store_false",
            help="Skip fixing the parcel 243 B116 typo.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        recalculate_all = options["all"]
        fix_243 = options["fix_parcel_243"]

        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("     AUDIT & RECALCULATE LAND RATES & CODES       "))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        if dry_run:
            self.stdout.write(self.style.WARNING(">>> RUNNING IN DRY-RUN MODE (No changes will be saved) <<<\n"))

        start_time = time.time()

        # Step 1: Fix parcel 243 typo if present
        if fix_243:
            p243_fixed = 0
            for r in LandRate.objects.filter(plot_number="243", block_name__iexact="B116"):
                if r.share_coefficient and r.share_coefficient > Decimal("0.62851"):
                    self.stdout.write(
                        f"Fixing parcel 243 typo for {r.block_name} (ID: {r.id}): {r.share_coefficient} -> 0.6285087311187618"
                    )
                    if not dry_run:
                        r.share_coefficient = Decimal("0.6285087311187618")
                        r.save(update_fields=["share_coefficient"])
                    p243_fixed += 1
            if p243_fixed:
                self.stdout.write(self.style.SUCCESS(f"Fixed {p243_fixed} row(s) for parcel 243."))
                reset_cache()
            else:
                self.stdout.write("Parcel 243 data is already consistent.")

        _ensure_cache()

        # Step 2: Audit dossiers for mismatched renovation codes
        self.stdout.write("\nAuditing dossiers for mismatched or contaminated renovation codes...")

        mismatched_dossiers = []
        dossiers_qs = (
            HousingDossier.objects.filter(is_locked=False)
            .exclude(renovation_code="")
        )

        for d in dossiers_qs.iterator(chunk_size=1000):
            norm_c = normalize_code(d.renovation_code)
            r = _CACHE["by_code"].get(norm_c) or _CACHE["by_code"].get(strip_code(norm_c))
            if not r:
                mismatched_dossiers.append(d)
                continue

            d_plot = normalize_plot(d.plot_number)
            r_plot = normalize_plot(r.plot_number)
            plot_mismatch = bool(d_plot and r_plot and d_plot != r_plot)

            d_blk = normalize_block(d.block_name or d.block_code)
            r_blk = normalize_block(r.block_name)
            d_clean_b = clean_block_fuzzy(d_blk)
            r_clean_b = clean_block_fuzzy(r_blk)

            block_mismatch = False
            if d_blk and r_blk:
                m_sep = re.match(r"^([A-Z0-9]+)[\/\-]", d_blk)
                pref = clean_block_fuzzy(m_sep.group(1)) if m_sep else ""
                if not (
                    d_blk == r_blk
                    or d_clean_b == r_clean_b
                    or (pref and pref == r_clean_b)
                    or d_blk in r_blk
                    or r_blk in d_blk
                ):
                    block_mismatch = True

            if plot_mismatch or block_mismatch:
                mismatched_dossiers.append(d)

        self.stdout.write(f"Found {len(mismatched_dossiers)} dossier(s) with mismatched renovation codes.")

        corrected_codes = 0
        wiped_codes = 0
        to_update = []

        for d in mismatched_dossiers:
            proj = d.project or ""
            plot = str(d.plot_number).strip() if d.plot_number is not None else ""
            blk = d.block_name or d.block_code or ""

            true_rate, status, msg = get_rate_status(project=proj, plot=plot, block=blk)

            if (
                status == "ok"
                and true_rate
                and true_rate.renovation_code
                and getattr(true_rate, "match_tier", None) == "project_plot_block"
            ):
                d.renovation_code = strip_code(true_rate.renovation_code)
                corrected_codes += 1
            else:
                d.renovation_code = ""
                wiped_codes += 1

            apply_land_calculation(d, skip=("renovation_code",))
            to_update.append(d)

        # Step 3: Handle --all if requested
        if recalculate_all:
            self.stdout.write("\nRecalculating Section 9 for all unlocked dossiers...")
            already_ids = {d.id for d in to_update}
            all_unlocked = HousingDossier.objects.filter(is_locked=False).exclude(id__in=already_ids)
            all_count = 0
            for d in all_unlocked.iterator(chunk_size=1000):
                if apply_land_calculation(d):
                    to_update.append(d)
                    all_count += 1
            self.stdout.write(f"Prepared {all_count} additional dossier(s) for recalculation.")

        self.stdout.write(
            f"\nSummary of changes to apply:\n"
            f"  - Contaminated codes corrected: {corrected_codes}\n"
            f"  - Contaminated codes wiped clean: {wiped_codes}\n"
            f"  - Total dossiers to save: {len(to_update)}"
        )

        if not dry_run and to_update:
            self.stdout.write("Saving updates to database in chunks of 500...")
            chunk_size = 500
            for i in range(0, len(to_update), chunk_size):
                batch = to_update[i : i + chunk_size]
                with transaction.atomic():
                    HousingDossier.objects.bulk_update(
                        batch,
                        fields=[
                            "renovation_code",
                            "total_land_share",
                            "current_year_rent",
                            "past_years_rent",
                            "preparation_cost",
                            "land_lease_year",
                        ],
                    )
            self.stdout.write(self.style.SUCCESS("All changes successfully saved to database."))
        elif dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete. No records were modified."))

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"\nFinished in {elapsed:.2f} seconds."))
