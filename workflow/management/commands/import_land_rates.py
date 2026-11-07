"""
workflow/management/commands/import_land_rates.py

Usage:
    python manage.py import_land_rates "uploads/base_land_rates.xlsx"

Creates or updates one LandRate row per کد نوسازی. Safe to re-run whenever base rates change.
"""
from django.core.management.base import BaseCommand, CommandError
from workflow.land_rates import read_rates_from_excel, reset_cache
from workflow.models import LandRate


class Command(BaseCommand):
    help = "Import land share coefficients and per-m2 prices from base Excel."

    def add_arguments(self, parser):
        parser.add_argument("excel_path", help="Path to the Excel file (.xlsx)")

    def handle(self, *args, **options):
        excel_path = options["excel_path"]
        self.stdout.write(f"Reading land rates from: {excel_path}")
        try:
            rows, problems = read_rates_from_excel(excel_path)
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc))

        if not rows:
            self.stdout.write(self.style.WARNING("No valid rows found in Excel."))
            return

        LandRate.objects.bulk_create(
            [LandRate(**r) for r in rows],
            batch_size=500,
            update_conflicts=True,
            unique_fields=["renovation_code"],
            update_fields=[
                "project_name", "plot_number", "block_name", "share_land", "share_common",
                "rent_current_per_m2", "rent_to_date_per_m2", "prep_per_m2",
            ],
        )
        reset_cache()
        for p in problems[:20]:
            self.stdout.write(self.style.WARNING(p))
        if len(problems) > 20:
            self.stdout.write(self.style.WARNING(f"... and {len(problems) - 20} more warnings"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported/updated {len(rows)} rates. Total rates in DB: {LandRate.objects.count()}"
            )
        )
