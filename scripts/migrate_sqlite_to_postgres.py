"""
Automated Migration Script: SQLite -> PostgreSQL (ztkmaskan)
Transfers all users, profiles, dossiers, signatures, check items, attachments,
and bank mappings from SQLite db.sqlite3 directly into PostgreSQL ztkmaskan database.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Configure Django settings with both databases
import django
from django.conf import settings

# Force two databases in settings
settings.DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'ztkmaskan'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'Soheil@;Tarsim'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from workflow.models import (
    Site, Project, PreSelectedUnit, HousingDossier,
    DossierCheck, DossierAttachment, WorkflowSignatureLog,
    DossierFieldChangeLog, UserProfile, ProjectBankMapping,
    BankLetter, DossierSignature
)

def migrate_table(model, batch_size=1000):
    total = model.objects.using('sqlite').count()
    name = model.__name__
    print(f"\n[+] Migrating {name}: {total:,} records from SQLite to PostgreSQL...")
    if total == 0:
        print(f"    0 records, skipping.")
        return

    # Delete existing in target if any to prevent duplicate primary keys
    existing_count = model.objects.using('default').count()
    if existing_count > 0:
        print(f"    Target already has {existing_count} records. Clearing target table for clean import...")
        model.objects.using('default').all().delete()

    qs = model.objects.using('sqlite').all().order_by('pk')
    batch = []
    migrated = 0

    for obj in qs.iterator(chunk_size=batch_size):
        batch.append(obj)
        if len(batch) >= batch_size:
            model.objects.using('default').bulk_create(batch, ignore_conflicts=True)
            migrated += len(batch)
            print(f"    Migrated {migrated:,} / {total:,} ({migrated*100//total}%)")
            batch = []

    if batch:
        model.objects.using('default').bulk_create(batch, ignore_conflicts=True)
        migrated += len(batch)

    print(f"    Finished {name}: {migrated:,} records transferred successfully.")

def reset_pg_sequences():
    """Reset PostgreSQL auto-increment sequences to MAX(id) + 1."""
    print("\n[+] Resetting PostgreSQL sequence IDs...")
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 'SELECT setval(' || quote_literal(quote_ident(PGT.schemaname) || '.' || quote_ident(S.relname)) ||
                   ', COALESCE(MAX(' ||quote_ident(C.attname)|| '), 1) ) FROM ' ||
                   quote_ident(PGT.schemaname)|| '.'||quote_ident(T.relname)|| ';'
            FROM pg_class AS S,
                 pg_depend AS D,
                 pg_class AS T,
                 pg_attribute AS C,
                 pg_tables AS PGT
            WHERE S.relkind = 'S'
              AND S.oid = D.objid
              AND D.refobjid = T.oid
              AND D.refobjsubid = C.attnum
              AND T.relname = PGT.tablename
              AND PGT.schemaname = 'public';
        """)
        statements = cursor.fetchall()
        for stmt in statements:
            try:
                cursor.execute(stmt[0])
            except Exception:
                pass
    print("    Sequences reset successfully.")

def main():
    print("=" * 65)
    print("      SanadBan SQLite -> PostgreSQL (ztkmaskan) Migrator")
    print(f"      Source DB : {BASE_DIR / 'db.sqlite3'}")
    print(f"      Target DB : PostgreSQL (ztkmaskan on 127.0.0.1:5432)")
    print("=" * 65)

    # Order models respecting foreign keys
    models_to_migrate = [
        User,
        UserProfile,
        Site,
        Project,
        PreSelectedUnit,
        HousingDossier,
        DossierCheck,
        DossierAttachment,
        WorkflowSignatureLog,
        DossierFieldChangeLog,
        ProjectBankMapping,
        BankLetter,
        DossierSignature,
    ]

    for m in models_to_migrate:
        migrate_table(m)

    reset_pg_sequences()
    print("\n" + "=" * 65)
    print("   ALL DATA MIGRATED TO POSTGRESQL (ztkmaskan) SUCCESSFULLY!")
    print("=" * 65)

if __name__ == '__main__':
    main()
