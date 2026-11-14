import os
import shutil
import sqlite3
import hashlib
from datetime import datetime, date
import jdatetime

from django.db import migrations
from django.utils import timezone


def to_jalali_str(dt_val):
    if not dt_val:
        return ""
    if isinstance(dt_val, str):
        dt_val = dt_val.strip()
        if not dt_val:
            return ""
        if dt_val.startswith("13") or dt_val.startswith("14"):
            return dt_val.replace("-", "/")
        try:
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


def run_auto_migration(apps, schema_editor):
    HousingDossier = apps.get_model("workflow", "HousingDossier")
    DirectorateShipment = apps.get_model("workflow", "DirectorateShipment")
    DossierCheck = apps.get_model("workflow", "DossierCheck")
    DossierAttachment = apps.get_model("workflow", "DossierAttachment")

    # Locate source databases (support env vars or default paths)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parent_dir = os.path.dirname(base_dir)

    scancheck_db = os.environ.get("SCANCHECK_DB_PATH") or os.path.join(parent_dir, "scancheck", "scancheck", "db.sqlite3")
    tashilat_db = os.environ.get("TASHILAT_DB_PATH") or os.path.join(parent_dir, "Tashilat", "db.sqlite3")
    scancheck_media = os.environ.get("SCANCHECK_MEDIA_PATH") or os.path.join(parent_dir, "scancheck", "scancheck", "media")
    uploads_dir = os.path.join(base_dir, "uploads")

    # 1. Migrate ScanCheck if available
    if os.path.isfile(scancheck_db):
        conn = sqlite3.connect(scancheck_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM records_shipment")
        shipments_raw = cur.fetchall()
        shipment_map = {}
        for s in shipments_raw:
            s_code = s["shipment_code"]
            s_date = parse_dt(s["created_at"])
            j_date = to_jalali_str(s_date)
            shipment_obj, _ = DirectorateShipment.objects.get_or_create(
                shipment_code=s_code,
                defaults={
                    "shipment_type": "LOAN",
                    "sent_date": j_date,
                    "note": s["note"] or "",
                },
            )
            shipment_map[s["id"]] = shipment_obj

        cur.execute("SELECT * FROM records_scanrecord")
        records = cur.fetchall()
        for r in records:
            raw_nid = str(r["national_id"]).strip()
            nid = raw_nid.zfill(10)
            dossier = HousingDossier.objects.filter(national_id=nid).first()
            if not dossier:
                continue

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

            if r["processed_date"]:
                dossier.loan_processed_at = parse_dt(r["processed_date"])

            if r["is_visited"]:
                dossier.is_loan_visited = True
                if r["visited_at"]:
                    v_dt = parse_dt(r["visited_at"])
                    dossier.loan_visited_at = v_dt
                    dossier.loan_visit_date = to_jalali_str(v_dt)
                if not dossier.loan_visited_by:
                    dossier.loan_visited_by = "ثبت سامانه وام"

            if r["is_shipped"]:
                dossier.is_loan_sent_to_directorate = True
                s_id = r["shipment_id"]
                if s_id and s_id in shipment_map:
                    dossier.loan_directorate_shipment = shipment_map[s_id]
                    dossier.loan_directorate_sent_at = shipment_map[s_id].created_at
                    dossier.loan_directorate_sent_date = shipment_map[s_id].sent_date
                if not dossier.loan_directorate_sent_by:
                    dossier.loan_directorate_sent_by = "سامانه زمین ترسیم"

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

            cur.execute("SELECT * FROM records_checkdate WHERE record_id = ?", (r["id"],))
            checks = cur.fetchall()
            for idx, chk in enumerate(checks):
                sayadi = str(chk["check_sayadi_code"] or "").strip()
                DossierCheck.objects.get_or_create(
                    dossier=dossier,
                    check_type="LOAN",
                    check_sayadi_code=sayadi,
                    defaults={
                        "row_number": idx + 1,
                        "check_amount": chk["check_amount"] or 0,
                        "cash_date": to_jalali_str(chk["cash_date"]),
                        "bank_name": chk["bank_name"] or "",
                    },
                )

            if r["commitment_scan"] and os.path.isdir(scancheck_media):
                src_path = os.path.join(scancheck_media, r["commitment_scan"])
                if os.path.isfile(src_path):
                    target_dir = os.path.join(uploads_dir, nid)
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

            cur.execute("SELECT * FROM records_checkscan WHERE record_id = ?", (r["id"],))
            scans = cur.fetchall()
            for sc in scans:
                if sc["scanned_file"] and os.path.isdir(scancheck_media):
                    sc_src = os.path.join(scancheck_media, sc["scanned_file"])
                    if os.path.isfile(sc_src):
                        target_dir = os.path.join(uploads_dir, nid)
                        os.makedirs(target_dir, exist_ok=True)
                        sc_fname = os.path.basename(sc_src)
                        sc_dst = os.path.join(target_dir, sc_fname)
                        if not os.path.exists(sc_dst):
                            shutil.copy2(sc_src, sc_dst)

                        hasher = hashlib.sha256()
                        with open(sc_dst, "rb") as sf:
                            for chunk in iter(lambda: sf.read(4096), b""):
                                hasher.update(chunk)
                        sc_hash = hasher.hexdigest()

                        DossierAttachment.objects.get_or_create(
                            dossier=dossier,
                            doc_type="LOAN_CHECK",
                            file_name=sc_fname,
                            defaults={
                                "stage": 17,
                                "title": "اسکن چک وام دهک",
                                "file_sha256": sc_hash,
                                "preview_url": f"/uploads/{nid}/{sc_fname}",
                                "uploaded_by": "انتقال سیستم قبلی",
                            },
                        )

        conn.close()

    # 2. Migrate Tashilat if available
    if os.path.isfile(tashilat_db):
        conn = sqlite3.connect(tashilat_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM records_scanrecord")
        records = cur.fetchall()
        for r in records:
            raw_nid = str(r["national_id"]).strip()
            nid = raw_nid.zfill(10)
            dossier = HousingDossier.objects.filter(national_id=nid).first()
            if not dossier:
                continue

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

            if r["processed_date"]:
                dossier.prep_processed_at = parse_dt(r["processed_date"])

            if r["is_visited"]:
                dossier.is_prep_visited = True
                if r["visited_at"]:
                    v_dt = parse_dt(r["visited_at"])
                    dossier.prep_visited_at = v_dt
                    dossier.prep_visit_date = to_jalali_str(v_dt)
                if not dossier.prep_visited_by:
                    dossier.prep_visited_by = "ثبت سامانه آماده‌سازی"

            if r["is_shipped"]:
                dossier.is_prep_sent_to_directorate = True
                if not dossier.prep_directorate_sent_by:
                    dossier.prep_directorate_sent_by = "سامانه زمین ترسیم"

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


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0054_alter_housingdossier_archive_number_nullable"),
    ]

    operations = [
        migrations.RunPython(run_auto_migration, reverse_code=migrations.RunPython.noop),
    ]
