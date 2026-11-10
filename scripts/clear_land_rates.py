#!/usr/bin/env python
"""
Clear the Section 9 (بخش ۹) Excel-imported LandRate database table (`workflow_landrate`).

This standalone script is safe to copy directly onto the production server (either inside
`scripts/` or next to `manage.py`) and uses the project's `.env` and `config.settings`
(PostgreSQL on production, SQLite locally).

Usage:
    # 1. Dry-run inspection (default — modifies nothing):
    python scripts/clear_land_rates.py

    # 2. Clear all rows from the LandRate table and reset its primary key sequence:
    python scripts/clear_land_rates.py --confirm

    # 3. Clear only rows belonging to a specific project:
    python scripts/clear_land_rates.py --project "نام پروژه" --confirm
"""

import argparse
import os
import sys
from pathlib import Path


def _configure_stdio() -> None:
    """Ensure UTF-8 console output on Windows so Persian project names never raise encoding errors."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
            except Exception:
                pass


def _resolve_base_dir() -> Path:
    """Locate project root containing manage.py whether placed in scripts/ or project root."""
    here = Path(__file__).resolve().parent
    for candidate in (here, here.parent, here.parent.parent):
        if (candidate / "manage.py").exists() and (candidate / "config" / "settings.py").exists():
            return candidate
    return here.parent


_configure_stdio()
BASE_DIR = _resolve_base_dir()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
from django.apps import apps  # noqa: E402


def _ensure_django() -> None:
    """Initialize Django once when executed as a standalone script."""
    if not apps.ready:
        django.setup()


def _reset_sequence(table_name: str) -> bool:
    """Reset the primary key auto-increment sequence for SQLite or PostgreSQL."""
    from django.db import connection

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
            )
            if cursor.fetchone():
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = %s", [table_name])
                return True
            return False

        if connection.vendor == "postgresql":
            cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table_name])
            row = cursor.fetchone()
            if row and row[0]:
                cursor.execute("SELECT setval(%s, 1, false)", [row[0]])
                return True
            return False

    return False


def _remove_base_rate_files(media_root: str) -> list[str]:
    """Optionally delete stored base_land_rates.{xlsx,csv} files under MEDIA_ROOT."""
    removed: list[str] = []
    for filename in ("base_land_rates.xlsx", "base_land_rates.csv"):
        path = Path(media_root) / filename
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    return removed


def clear_land_rates(
    *,
    confirm: bool = False,
    project: str | None = None,
    delete_base_files: bool = False,
    stdout=None,
) -> dict:
    """
    Inspect or clear the Section 9 LandRate table (`workflow_landrate`).

    Runs in dry-run mode unless `confirm=True`. Never modifies HousingDossier records.
    """
    _ensure_django()

    from django.conf import settings
    from django.db import connection, transaction
    from django.db.models import Count
    from workflow.land_rates import reset_cache
    from workflow.models import LandRate

    out = stdout or sys.stdout
    table_name = LandRate._meta.db_table
    db_cfg = connection.settings_dict
    db_vendor = connection.vendor
    db_name = db_cfg.get("NAME", "")
    db_host = db_cfg.get("HOST", "")

    total_before = LandRate.objects.count()
    qs = LandRate.objects.filter(project_name=project) if project else LandRate.objects.all()
    target_count = qs.count()
    distinct_projects = LandRate.objects.values("project_name").distinct().count()

    print("=" * 64, file=out)
    print("  SanadBan - Clear Section 9 Excel Table (LandRate)", file=out)
    print("=" * 64, file=out)
    host_info = f" @ {db_host}" if db_host else ""
    print(f"  Database   : {db_vendor} ({db_name}{host_info})", file=out)
    print(f"  Table      : {table_name}", file=out)
    print(f"  Total rows : {total_before:,} ({distinct_projects:,} distinct projects)", file=out)
    if project:
        print(f"  Filter     : project_name == {project!r} ({target_count:,} matching rows)", file=out)

    top_projects = list(
        qs.values("project_name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "project_name")[:10]
    )
    if top_projects:
        print("  Top projects in scope:", file=out)
        for item in top_projects:
            pname = item["project_name"] or "<بدون نام پروژه>"
            print(f"    - {pname}: {item['cnt']:,} rows", file=out)
        if distinct_projects > len(top_projects) and not project:
            print(f"    ... and {distinct_projects - len(top_projects):,} more projects", file=out)

    print("  Protected  : HousingDossier, Users, Signatures (untouched)", file=out)

    if not confirm:
        print("\n[DRY RUN] No rows were deleted.", file=out)
        script_hint = sys.argv[0] if sys.argv and sys.argv[0] not in ("", "-") else Path(__file__).name
        flag_hint = f' --project "{project}"' if project else ""
        print(f"Re-run with --confirm to execute:\n  python {script_hint}{flag_hint} --confirm", file=out)
        return {
            "dry_run": True,
            "total_before": total_before,
            "target_count": target_count,
            "deleted_count": 0,
            "remaining_count": total_before,
            "sequence_reset": False,
            "removed_files": [],
        }

    with transaction.atomic():
        deleted_count, _ = qs.delete()
        sequence_reset = False
        if not project:
            sequence_reset = _reset_sequence(table_name)

    reset_cache()

    removed_files: list[str] = []
    if delete_base_files and getattr(settings, "MEDIA_ROOT", None):
        removed_files = _remove_base_rate_files(str(settings.MEDIA_ROOT))

    remaining_count = LandRate.objects.count()
    print(f"\n[OK] Deleted {deleted_count:,} row(s) from {table_name}.", file=out)
    if not project:
        seq_status = "reset to 1" if sequence_reset else "no sequence entry to reset"
        print(f"[OK] Primary key sequence: {seq_status}.", file=out)
    if removed_files:
        print(f"[OK] Removed base files: {', '.join(removed_files)}", file=out)
    print(f"[OK] Remaining rows in {table_name}: {remaining_count:,}.", file=out)
    print(
        "[INFO] If the web server (Waitress/IIS) is running, its in-memory land-rate cache\n"
        "       expires automatically within 60 seconds (or immediately upon new Excel upload / restart).",
        file=out,
    )

    return {
        "dry_run": False,
        "total_before": total_before,
        "target_count": target_count,
        "deleted_count": deleted_count,
        "remaining_count": remaining_count,
        "sequence_reset": sequence_reset,
        "removed_files": removed_files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Clear the Section 9 Excel-imported LandRate table (workflow_landrate)."
    )
    parser.add_argument(
        "--confirm",
        "-y",
        "--yes",
        action="store_true",
        help="Confirm deletion. Without this flag, runs in dry-run inspection mode.",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Optional exact project_name filter; clears only matching rows instead of the whole table.",
    )
    parser.add_argument(
        "--delete-base-files",
        action="store_true",
        help="Also remove base_land_rates.xlsx / base_land_rates.csv from MEDIA_ROOT if present.",
    )
    args = parser.parse_args(argv)

    clear_land_rates(
        confirm=args.confirm,
        project=args.project,
        delete_base_files=args.delete_base_files,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
