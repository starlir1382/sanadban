import os
import shutil
import hashlib
from datetime import datetime, date
import jdatetime

from django.conf import settings
from django.db import migrations
from django.utils import timezone


def _pg_connect(dbname):
    """Open a read connection to another database on the same PostgreSQL server.
    Rows come back as dicts, so r["column"] works exactly like it did with sqlite3.Row."""
    params = dict(
        dbname=dbname,
        user=os.environ.get("LEGACY_DB_USER") or os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("LEGACY_DB_PASSWORD") or os.environ.get("DB_PASSWORD", ""),
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=os.environ.get("DB_PORT", "5432"),
    )
    try:
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **params)
    except ImportError:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(row_factory=dict_row, **params)


def _connect_legacy_db(dbname_or_path):
    """Connect to PostgreSQL or SQLite legacy database depending on the parameter."""
    if not dbname_or_path:
        return None
    if os.path.exists(dbname_or_path) or str(dbname_or_path).endswith((".sqlite3", ".db")):
        import sqlite3
        conn = sqlite3.connect(dbname_or_path)
        conn.row_factory = sqlite3.Row
        return conn
    return _pg_connect(dbname_or_path)


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
        if timezone.is_aware(dt_val):
            dt_val = timezone.localtime(dt_val)
        j_date = jdatetime.date.fromgregorian(date=dt_val.date())
        return j_date.strftime("%Y/%m/%d")
    elif isinstance(dt_val, date):
        j_date = jdatetime.date.fromgregorian(date=dt_val)
        return j_date.strftime("%Y/%m/%d")
    return str(dt_val)


def parse_dt(dt_val):
    if not dt_val:
        return None
    if isinstance(dt_val, date) and not isinstance(dt_val, datetime):
        dt_val = datetime.combine(dt_val, datetime.min.time())
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


def _copy_and_hash(src_path, target_dir, fname):
    """Copy a scan into the uploads folder (if not already there) and return its SHA-256."""
    os.makedirs(target_dir, exist_ok=True)
    dst_path = os.path.join(target_dir, fname)
    if not os.path.exists(dst_path):
        shutil.copy2(src_path, dst_path)
    hasher = hashlib.sha256()
    with open(dst_path, "rb") as sf:
        for chunk in iter(lambda: sf.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_tashilat_migration(apps, schema_editor):
    # Escape hatch for fresh installs or CI/dev environments where legacy DB is absent
    if os.environ.get("SKIP_LEGACY_IMPORT") == "1":
        return

    HousingDossier = apps.get_model("workflow", "HousingDossier")
    DirectorateShipment = apps.get_model("workflow", "DirectorateShipment")
    DossierCheck = apps.get_model("workflow", "DossierCheck")
    DossierAttachment = apps.get_model("workflow", "DossierAttachment")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parent_dir = os.path.dirname(base_dir)

    # PostgreSQL database name or SQLite path for Tashilat / آماده سازی
    tashilat_db = (
        os.environ.get("TASHILAT_PG_DB")
        or os.environ.get("TASHILAT_DB")
        or "TashilatCheck"
    )

    tashilat_media = (
        os.environ.get("TASHILAT_MEDIA_PATH")
        or os.environ.get("TENANT_MEDIA_PATH")
        or r"C:\inetpub\wwwroot\Tashilat\media"
    )
    if not os.path.isdir(tashilat_media):
        candidate_alt = os.path.join(parent_dir, "Tashilat", "media")
        if os.path.isdir(candidate_alt):
            tashilat_media = candidate_alt

    uploads_dir = str(settings.MEDIA_ROOT)

    try:
        conn = _connect_legacy_db(tashilat_db)
    except Exception as exc:
        print(f"[0056_migrate_tashilat_prep] Notice: Cannot connect to legacy Tashilat database '{tashilat_db}': {exc}. Skipping.")
        return

    if not conn:
        return

    is_sqlite = hasattr(conn, "text_factory")
    param = "?" if is_sqlite else "%s"

    try:
        cur = conn.cursor()

        # ------------------------------------------------------------------
        # 1. Directorate Shipments (PREP)
        # ------------------------------------------------------------------
        shipment_map = {}
        try:
            cur.execute("SELECT * FROM records_shipment")
            shipments_raw = cur.fetchall()
            for raw_s in shipments_raw:
                s = dict(raw_s)
                s_code = s["shipment_code"]
                s_date = parse_dt(s.get("created_at"))
                j_date = to_jalali_str(s_date)
                shipment_obj, _ = DirectorateShipment.objects.get_or_create(
                    shipment_code=s_code,
                    defaults={
                        "shipment_type": "PREP",
                        "sent_date": j_date,
                        "note": s.get("note") or "",
                    },
                )
                shipment_map[s["id"]] = shipment_obj
        except Exception as exc:
            print(f"[0056_migrate_tashilat_prep] Note: Could not query records_shipment: {exc}")

        # ------------------------------------------------------------------
        # 2. Dossiers, Checks, and Attachments
        # ------------------------------------------------------------------
        cur.execute("SELECT * FROM records_scanrecord")
        records = cur.fetchall()

        for raw_r in records:
            r = dict(raw_r)
            raw_nid = str(r.get("national_id") or "").strip()
            if not raw_nid:
                continue
            nid = raw_nid.zfill(10)
            dossier = HousingDossier.objects.filter(national_id=nid).first()
            if not dossier:
                continue

            # Financial fields
            if r["tenant_price"]:
                dossier.tenant_price = r["tenant_price"]
            elif r.get("appraisal_rent") and not dossier.tenant_price:
                dossier.tenant_price = r["appraisal_rent"]

            if r["tenant_code"]:
                dossier.tenant_code = str(r["tenant_code"]).strip()

            if r["prepayment"]:
                dossier.cash_preparation_amount = r["prepayment"]
            elif r.get("appraisal_cash") and not dossier.cash_preparation_amount:
                dossier.cash_preparation_amount = r["appraisal_cash"]

            if r["prepayment_code"]:
                dossier.prepayment_code = str(r["prepayment_code"]).strip()

            if r.get("appraisal_installment"):
                dossier.non_cash_preparation_amount = r["appraisal_installment"]

            if r.get("service_fee"):
                dossier.preparation_service_fee = r["service_fee"]

            # Letters and Notary Office
            if r.get("rah_letter"):
                dossier.rah_letter = str(r["rah_letter"]).strip()
            if r.get("rah_letter_date"):
                dossier.rah_letter_date = to_jalali_str(r["rah_letter_date"])

            if r.get("commitment_number"):
                dossier.commitment_number = str(r["commitment_number"]).strip()
            if r.get("commitment_date"):
                dossier.commitment_date = to_jalali_str(r["commitment_date"])

            if r.get("notary_office_name"):
                dossier.notary_office_number = str(r["notary_office_name"]).strip()
            if r.get("notary_code"):
                dossier.notary_letter_number = str(r["notary_code"]).strip()
            if r.get("notary_date"):
                dossier.notary_letter_date = to_jalali_str(r["notary_date"])

            # Applicant phone & decile if missing on dossier
            if r.get("phone_number") and not dossier.applicant_phone:
                dossier.applicant_phone = str(r["phone_number"]).strip()
            if r.get("appraisal_dahak") and not dossier.decile:
                dossier.decile = r["appraisal_dahak"]

            # Processed date
            if r.get("processed_date"):
                dossier.prep_processed_at = parse_dt(r["processed_date"])

            # Cash and rent confirmation
            if dossier.tenant_price or dossier.cash_preparation_amount or dossier.prepayment_code or dossier.tenant_code:
                dossier.is_cash_rent_confirmed = True
                if not dossier.cash_rent_confirmed_by:
                    dossier.cash_rent_confirmed_by = "مهاجرت سیستم آماده‌سازی"
                if not dossier.cash_rent_confirmed_at:
                    dossier.cash_rent_confirmed_at = dossier.prep_processed_at or timezone.now()

            # Visit tracking
            if r.get("is_visited"):
                dossier.is_prep_visited = True
                if r.get("visited_at"):
                    v_dt = parse_dt(r["visited_at"])
                    dossier.prep_visited_at = v_dt
                    dossier.prep_visit_date = to_jalali_str(v_dt)
                if not dossier.prep_visited_by:
                    dossier.prep_visited_by = "ثبت سامانه آماده‌سازی"

            # Shipment tracking
            if r.get("is_shipped"):
                dossier.is_prep_sent_to_directorate = True
                s_id = r.get("shipment_id")
                if s_id and s_id in shipment_map:
                    dossier.prep_directorate_shipment = shipment_map[s_id]
                    dossier.prep_directorate_sent_at = shipment_map[s_id].created_at
                    dossier.prep_directorate_sent_date = shipment_map[s_id].sent_date
                if not dossier.prep_directorate_sent_by:
                    dossier.prep_directorate_sent_by = "سامانه زمین ترسیم"

            # ------------------------------------------------------------------
            # Checks (CheckDate)
            # ------------------------------------------------------------------
            prep_checks_total = 0
            prep_checks_count = 0
            try:
                cur.execute(f"SELECT * FROM records_checkdate WHERE record_id = {param}", (r["id"],))
                checks = cur.fetchall()
                for idx, raw_chk in enumerate(checks):
                    chk = dict(raw_chk)
                    sayadi = str(chk.get("check_sayadi_code") or "").strip()
                    chk_amount = chk.get("check_amount") or 0
                    chk_date_str = to_jalali_str(chk.get("cash_date"))
                    chk_bank = str(chk.get("bank_name") or "").strip()
                    DossierCheck.objects.get_or_create(
                        dossier=dossier,
                        check_type="PREPARATION",
                        check_sayadi_code=sayadi,
                        defaults={
                            "row_number": idx + 1,
                            "check_amount": chk_amount,
                            "cash_date": chk_date_str,
                            "bank_name": chk_bank,
                        },
                    )
                    prep_checks_count += 1
                    prep_checks_total += chk_amount
            except Exception as exc:
                print(f"[0056_migrate_tashilat_prep] Note: Error checking records_checkdate for {nid}: {exc}")

            if prep_checks_count > 0:
                dossier.preparation_check_count = prep_checks_count
                dossier.total_preparation_check_amount = prep_checks_total
                dossier.is_preparation_checks_confirmed = True
                if not dossier.prep_checks_confirmed_by:
                    dossier.prep_checks_confirmed_by = "مهاجرت سیستم آماده‌سازی"
                if not dossier.prep_checks_confirmed_at:
                    dossier.prep_checks_confirmed_at = dossier.prep_processed_at or timezone.now()

            dossier.save(update_fields=[
                "tenant_price",
                "tenant_code",
                "cash_preparation_amount",
                "prepayment_code",
                "non_cash_preparation_amount",
                "preparation_service_fee",
                "rah_letter",
                "rah_letter_date",
                "commitment_number",
                "commitment_date",
                "notary_office_number",
                "notary_letter_number",
                "notary_letter_date",
                "applicant_phone",
                "decile",
                "is_cash_rent_confirmed",
                "cash_rent_confirmed_by",
                "cash_rent_confirmed_at",
                "preparation_check_count",
                "total_preparation_check_amount",
                "is_preparation_checks_confirmed",
                "prep_checks_confirmed_by",
                "prep_checks_confirmed_at",
                "prep_processed_at",
                "is_prep_visited",
                "prep_visited_at",
                "prep_visit_date",
                "prep_visited_by",
                "is_prep_sent_to_directorate",
                "prep_directorate_shipment",
                "prep_directorate_sent_at",
                "prep_directorate_sent_date",
                "prep_directorate_sent_by",
            ])

            # ------------------------------------------------------------------
            # Scans & Attachments
            # ------------------------------------------------------------------
            target_dir = os.path.join(uploads_dir, nid)

            # 1. Commitment scan
            if r.get("commitment_scan") and os.path.isdir(tashilat_media):
                src_path = os.path.join(tashilat_media, str(r["commitment_scan"]))
                if os.path.isfile(src_path):
                    fname = os.path.basename(src_path)
                    f_hash = _copy_and_hash(src_path, target_dir, fname)
                    DossierAttachment.objects.get_or_create(
                        dossier=dossier,
                        doc_type="COMMITMENT_LETTER",
                        file_name=fname,
                        defaults={
                            "stage": 18,
                            "title": "اسکن تعهدنامه محضری آماده‌سازی",
                            "file_sha256": f_hash,
                            "preview_url": f"/uploads/{nid}/{fname}",
                            "uploaded_by": "انتقال سیستم قبلی",
                        },
                    )

            # 2. Check scans
            try:
                cur.execute(f"SELECT * FROM records_checkscan WHERE record_id = {param}", (r["id"],))
                scans = cur.fetchall()
                for raw_sc in scans:
                    sc = dict(raw_sc)
                    if sc.get("scanned_file") and os.path.isdir(tashilat_media):
                        sc_src = os.path.join(tashilat_media, str(sc["scanned_file"]))
                        if os.path.isfile(sc_src):
                            sc_fname = os.path.basename(sc_src)
                            sc_hash = _copy_and_hash(sc_src, target_dir, sc_fname)
                            DossierAttachment.objects.get_or_create(
                                dossier=dossier,
                                doc_type="PREP_CHECK",
                                file_name=sc_fname,
                                defaults={
                                    "stage": 18,
                                    "title": "اسکن چک آماده‌سازی",
                                    "file_sha256": sc_hash,
                                    "preview_url": f"/uploads/{nid}/{sc_fname}",
                                    "uploaded_by": "انتقال سیستم قبلی",
                                },
                            )
            except Exception as exc:
                print(f"[0056_migrate_tashilat_prep] Note: Error checking records_checkscan for {nid}: {exc}")

    finally:
        conn.close()


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0055_auto_migrate_sources"),
    ]

    operations = [
        migrations.RunPython(run_tashilat_migration, reverse_code=migrations.RunPython.noop),
    ]
