from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from workflow.models import HousingDossier
from workflow.excel_utils import clean_national_id


def normalize(value):
    """Return the 10-digit form, or the original value if it can't be normalized."""
    if value is None or str(value).strip() == "":
        return value
    cleaned = clean_national_id(value)
    return cleaned if cleaned else value


class Command(BaseCommand):
    help = "Normalize national_id and spouse_national_id to 10 digits with leading zeros."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write the changes. Without this flag it is a dry run.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        changes = []  # (pk, archive_number, new_nid, new_snid, old_nid, old_snid)
        new_applicant_ids = defaultdict(list)

        for d in HousingDossier.objects.only(
            "pk", "archive_number", "national_id", "spouse_national_id"
        ).iterator():
            new_nid = normalize(d.national_id)
            new_snid = normalize(d.spouse_national_id)
            new_applicant_ids[new_nid].append(d.pk)

            if new_nid != d.national_id or new_snid != d.spouse_national_id:
                changes.append((d.pk, d.archive_number, new_nid, new_snid,
                                d.national_id, d.spouse_national_id))

        # Detect two different dossiers that would end up with the same applicant ID
        duplicates = {k: v for k, v in new_applicant_ids.items() if k and len(v) > 1}
        duplicate_pks = {pk for pks in duplicates.values() for pk in pks}

        self.stdout.write(f"Dossiers needing a fix: {len(changes)}")
        for pk, arch, n, s, old_n, old_s in changes[:30]:
            self.stdout.write(f"  #{arch}: {old_n} -> {n} | spouse: {old_s} -> {s}")
        if len(changes) > 30:
            self.stdout.write(f"  ... and {len(changes) - 30} more")

        if duplicates:
            self.stdout.write(self.style.WARNING(
                f"\nWARNING: {len(duplicates)} national ID(s) would collide and will be SKIPPED:"
            ))
            for nid, pks in duplicates.items():
                archives = list(
                    HousingDossier.objects.filter(pk__in=pks).values_list("archive_number", flat=True)
                )
                self.stdout.write(f"  {nid} is used by archive numbers {archives}")

        if not apply:
            self.stdout.write(self.style.NOTICE("\nDry run only. Re-run with --apply to save."))
            return

        updated = 0
        with transaction.atomic():
            for pk, arch, new_nid, new_snid, old_n, old_s in changes:
                if pk in duplicate_pks:
                    continue
                HousingDossier.objects.filter(pk=pk).update(
                    national_id=new_nid, spouse_national_id=new_snid
                )
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. Updated {updated} dossiers."))