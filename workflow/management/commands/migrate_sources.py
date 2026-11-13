import os
import shutil
import sqlite3
import hashlib
from datetime import datetime, date
import jdatetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from workflow.models import (
    HousingDossier,
    DirectorateShipment,
    DossierCheck,
    DossierAttachment,
)


def to_jalali_str(dt_val):
    if not dt_val:
        return ""
    if isinstance(dt_val, str):
        dt_val = dt_val.strip()
        if not dt_val:
            return ""
        # Check if already jalali (starts with 13 or 14)
        if dt_val.startswith("13") or dt_val.startswith("14"):
            return dt_val.replace("-", "/")
        try:
            # Parse ISO date/datetime
            if "T" in dt_val:
                dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
            elif " " in dt_val:
                dt = datetime.strptime(dt_val.split(".")[0], "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(dt_val, "%Y-%m-%d")
            j_date = jdatetime.date.fromgregorian(date=dt.date())
            return j_date.strftime("%Y/%m/%d")
        except Exception:
            return dt_val

    if isinstance(dt_val, datetime):
        j_date = jdatetime.date.fromgregorian(date=dt_val.date())
        return j_date.strftime("%Y/%m/%d")
    elif isinstance(dt_val, date):
        j_date = jdatetime.date.fromgregorian(date=dt_val)
        return j_date.strftime("%Y/%m/%d")
    return str(dt_val)


def parse_dt(dt_val):
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val if timezone.is_aware(dt_val) else timezone.make_aware(dt_val)
    if isinstance(dt_val, str):
        try:
            clean = dt_val.replace("Z", "+00:00")
            if "T" in clean:
                dt = datetime.fromisoformat(clean)
            elif " " in clean:
                dt = datetime.strptime(clean.split(".")[0], "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(clean, "%Y-%m-%d")
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except Exception:
            return None
    return None


class Command(BaseCommand):
    help = "Migrate data from ScanCheck (Stage 17) and Tashilat (Stage 18) strictly into Section 10."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the migration without modifying the database or copying files.",
        )
        parser.add_argument(
            "--scancheck-db",
            default=r"d:\ZaminTarsim\scancheck\scancheck\db.sqlite3",
            help="Path to ScanCheck sqlite3 database.",
        )
        parser.add_argument(
            "--tashilat-db",
            default=r"d:\ZaminTarsim\Tashilat\db.sqlite3",
            help="Path to Tashilat sqlite3 database.",
        )
        parser.add_argument(
            "--scancheck-media",
            default=r"d:\ZaminTarsim\scancheck\scancheck\media",
            help="Path to ScanCheck media directory.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        scancheck_db = options["scancheck_db"]
        tashilat_db = options["tashilat_db"]
        scancheck_media = options["scancheck_media"]

        self.stdout.write(self.style.NOTICE(f"=== Starting Migration (Dry Run: {dry_run}) ==="))

        if not os.path.exists(scancheck_db):
            self.stderr.write(self.style.ERROR(f"ScanCheck DB not found at: {scancheck_db}"))
            return
        if not os.path.exists(tashilat_db):
            self.stderr.write(self.style.ERROR(f"Tashilat DB not found at: {tashilat_db}"))
            return

        with transaction.atomic():
            self.migrate_scancheck(scancheck_db, scancheck_media, dry_run)
            self.migrate_tashilat(tashilat_db, dry_run)

            if dry_run:
                self.stdout.write(self.style.WARNING("\n[DRY RUN] Simulation complete. Rolling back changes..."))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Migration committed successfully!"))

    def migrate_scancheck(self, db_path, media_dir, dry_run):
        self.stdout.write(self.style.NOTICE("\n--- Processing Source 1: ScanCheck (Stage 17 - Decile Loans) ---"))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Fetch Shipments
        cur.execute("SELECT * FROM records_shipment")
        shipments_raw = cur.fetchall()
        shipment_map = {}
        for s in shipments_raw:
            s_code = s["shipment_code"]
            s_date = parse_dt(s["created_at"])
            j_date = to_jalali_str(s_date)
            if not dry_run:
                shipment_obj, _ = DirectorateShipment.objects.get_or_create(
                    shipment_code=s_code,
                    defaults={
                        "shipment_type": "LOAN",
                        "sent_date": j_date,
                        "note": s["note"] or "",
                    },
                )
                shipment_map[s["id"]] = shipment_obj
            else:
                shipment_map[s["id"]] = s_code

        # 2. Fetch Records
        cur.execute("SELECT * FROM records_scanrecord")
        records = cur.fetchall()
        self.stdout.write(f"Total ScanCheck records to evaluate: {len(records)}")

        matched_count = 0
        missing_count = 0
        updated_fields_count = 0

        for r in records:
            raw_nid = str(r["national_id"]).strip()
            nid = raw_nid.zfill(10)

            dossier = HousingDossier.objects.filter(national_id=nid).first()
            if not dossier:
                missing_count += 1
                continue

            matched_count += 1

            # Map Stage 17 & Section 10 fields only:
            dossier.decile_loan_bank = r["appraisal_amel_bank"] or r["amel_bank"] or dossier.decile_loan_bank
            dossier.supported_institution = r["supported_institution"] or dossier.supported_institution
            dossier.check_count = r["check_count"] or dossier.check_count
            dossier.check_amount = r["check_amount"] or dossier.check_amount
            dossier.last_check_amount = r["last_check_amount"] or dossier.last_check_amount
            dossier.total_check_amount = r["total_check_amount"] or dossier.total_check_amount
            if r["service_fee"]:
                dossier.check_service_fee = r["service_fee"]

            dossier.commitment_number = r["commitment_number"] or dossier.commitment_number
            if r["commitment_date"]:
                dossier.commitment_date = to_jalali_str(r["commitment_date"])

            # Registration / Processed Date
            if r["processed_date"]:
                dossier.loan_processed_at = parse_dt(r["processed_date"])

            # Visit Date
            if r["is_visited"]:
                dossier.is_loan_visited = True
                if r["visited_at"]:
                    v_dt = parse_dt(r["visited_at"])
                    dossier.loan_visited_at = v_dt
                    dossier.loan_visit_date = to_jalali_str(v_dt)
                if not dossier.loan_visited_by:
                    dossier.loan_visited_by = "ثبت سامانه وام"

            # Directorate Shipment (Sent Batch)
            if r["is_shipped"]:
                dossier.is_loan_sent_to_directorate = True
                s_id = r["shipment_id"]
                if s_id and s_id in shipment_map:
                    if not dry_run:
                        dossier.loan_directorate_shipment = shipment_map[s_id]
                        dossier.loan_directorate_sent_at = shipment_map[s_id].created_at
                        dossier.loan_directorate_sent_date = shipment_map[s_id].sent_date
                if not dossier.loan_directorate_sent_by:
                    dossier.loan_directorate_sent_by = "سامانه زمین ترسیم"

            if not dry_run:
                dossier.save(update_fields=[
                    "decile_loan_bank",
                    "supported_institution",
                    "check_count",
                    "check_amount",
                    "last_check_amount",
                    "total_check_amount",
                    "check_service_fee",
                    "commitment_number",
                    "commitment_date",
                    "loan_processed_at",
                    "is_loan_visited",
                    "loan_visited_at",
                    "loan_visit_date",
                    "loan_visited_by",
                    "is_loan_sent_to_directorate",
                    "loan_directorate_shipment",
                    "loan_directorate_sent_at",
                    "loan_directorate_sent_date",
                    "loan_directorate_sent_by",
                ])

            # 3. Individual Checks
            cur.execute("SELECT * FROM records_checkdate WHERE record_id = ?", (r["id"],))
            checks = cur.fetchall()
            for chk in checks:
                if not dry_run:
                    DossierCheck.objects.get_or_create(
                        dossier=dossier,
                        check_type="LOAN",
                        sayadi_id=str(chk["check_sayadi_code"] or "").strip(),
                        defaults={
                            "amount": chk["check_amount"] or 0,
                            "due_date": to_jalali_str(chk["cash_date"]),
                            "bank_name": chk["bank_name"] or "",
                        },
                    )

            # 4. Scans & Attachments
            if r["commitment_scan"] and media_dir and not dry_run:
                src_path = os.path.join(media_dir, r["commitment_scan"])
                if os.path.isfile(src_path):
                    target_dir = os.path.join(r"d:\ZaminTarsim\sanadban\uploads", nid)
                    os.makedirs(target_dir, exist_ok=True)
                    fname = os.path.basename(src_path)
                    dst_path = os.path.join(target_dir, fname)
                    if not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)

                    hasher = hashlib.sha256()
                    with open(dst_path, "rb") as sf:
                        for chunk in iter(lambda: sf.read(4096), b""):
                            hasher.update(chunk)
                    f_hash = hasher.hexdigest()

                    DossierAttachment.objects.get_or_create(
                        dossier=dossier,
                        doc_type="COMMITMENT_LETTER",
                        file_name=fname,
                        defaults={
                            "stage": 17,
                            "title": "اسکن تعهدنامه محضری وام دهک",
                            "file_sha256": f_hash,
                            "preview_url": f"/uploads/{nid}/{fname}",
                            "uploaded_by": "انتقال سیستم قبلی",
                        },
                    )

            updated_fields_count += 1

        conn.close()
        self.stdout.write(self.style.SUCCESS(
            f"ScanCheck Result: {matched_count} matched & updated, {missing_count} not found in SanadBan."
        ))

    def migrate_tashilat(self, db_path, dry_run):
        self.stdout.write(self.style.NOTICE("\n--- Processing Source 2: Tashilat (Stage 18 - Preparation & Rent) ---"))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM records_scanrecord")
        records = cur.fetchall()
        self.stdout.write(f"Total Tashilat records to evaluate: {len(records)}")

        matched_count = 0
        missing_count = 0

        for r in records:
            raw_nid = str(r["national_id"]).strip()
            nid = raw_nid.zfill(10)

            dossier = HousingDossier.objects.filter(national_id=nid).first()
            if not dossier:
                missing_count += 1
                continue

            matched_count += 1

            # Map Stage 18 & Section 10 fields only:
            if r["tenant_price"]:
                dossier.tenant_price = r["tenant_price"]
            if r["tenant_code"]:
                dossier.tenant_code = str(r["tenant_code"]).strip()

            if r["prepayment"]:
                dossier.cash_preparation_amount = r["prepayment"]
            if r["prepayment_code"]:
                dossier.prepayment_code = str(r["prepayment_code"]).strip()

            if r["appraisal_installment"]:
                dossier.non_cash_preparation_amount = r["appraisal_installment"]

            if r["service_fee"]:
                dossier.preparation_service_fee = r["service_fee"]

            # Registration / Processed Date
            if r["processed_date"]:
                dossier.prep_processed_at = parse_dt(r["processed_date"])

            # Visit Date
            if r["is_visited"]:
                dossier.is_prep_visited = True
                if r["visited_at"]:
                    v_dt = parse_dt(r["visited_at"])
                    dossier.prep_visited_at = v_dt
                    dossier.prep_visit_date = to_jalali_str(v_dt)
                if not dossier.prep_visited_by:
                    dossier.prep_visited_by = "ثبت سامانه آماده‌سازی"

            # Directorate Shipment (Sent Batch)
            if r["is_shipped"]:
                dossier.is_prep_sent_to_directorate = True
                if not dossier.prep_directorate_sent_by:
                    dossier.prep_directorate_sent_by = "سامانه زمین ترسیم"

            if not dry_run:
                dossier.save(update_fields=[
                    "tenant_price",
                    "tenant_code",
                    "cash_preparation_amount",
                    "prepayment_code",
                    "non_cash_preparation_amount",
                    "preparation_service_fee",
                    "prep_processed_at",
                    "is_prep_visited",
                    "prep_visited_at",
                    "prep_visit_date",
                    "prep_visited_by",
                    "is_prep_sent_to_directorate",
                    "prep_directorate_sent_by",
                ])

        conn.close()
        self.stdout.write(self.style.SUCCESS(
            f"Tashilat Result: {matched_count} matched & updated, {missing_count} not found in SanadBan."
        ))
