import os
import sys
import django
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from workflow.models import HousingDossier, UserProfile, DossierFieldChangeLog, WorkflowSignatureLog

print('========================================')
print('SANADBAN WORKFLOW & AUDIT INTEGRITY TEST')
print('========================================')

chief = User.objects.get(username='housing_chief')
alemi = User.objects.get(username='alemi')
heydari = User.objects.get(username='heydari')
admin = User.objects.get(username='admin')

print(f"Chief: {chief.username}, is_housing_chief={chief.profile.is_housing_chief}, can_action(0)={chief.profile.can_action_stage(0)}, can_action(21)={chief.profile.can_action_stage(21)}")
print(f"Alemi: {alemi.username}, allowed={alemi.profile.allowed_stages}, can_action(3)={alemi.profile.can_action_stage(3)}, can_action(4)={alemi.profile.can_action_stage(4)}")
print(f"Heydari: {heydari.username}, allowed={heydari.profile.allowed_stages}, can_action(4)={heydari.profile.can_action_stage(4)}, can_action(3)={heydari.profile.can_action_stage(3)}")

assert chief.profile.is_housing_chief is True
assert chief.profile.can_action_stage(0) is True
assert chief.profile.can_action_stage(21) is True

assert alemi.profile.can_action_stage(3) is True
assert alemi.profile.can_action_stage(16) is True
assert alemi.profile.can_action_stage(4) is False

assert heydari.profile.can_action_stage(4) is True
assert heydari.profile.can_action_stage(8) is True
assert heydari.profile.can_action_stage(3) is False

client = Client()

# Prepare Test Dossier
dossier, created = HousingDossier.objects.get_or_create(archive_number=100001)
dossier.current_stage = 3
dossier.is_locked = False
dossier.save()
print(f"[OK] Dossier reset to stage {dossier.current_stage}")

# 1. Alemi signs stage 3 -> should succeed
client.force_login(alemi)
res_sign = client.post(
    f'/dossier/{dossier.archive_number}/sign/',
    data=json.dumps({"notes": "تایید فرم ج توسط عالمی"}),
    content_type='application/json'
)
print(f"[TEST 1] Alemi sign stage 3: status={res_sign.status_code}")
assert res_sign.status_code == 200

dossier.refresh_from_db()
print(f"[OK] Dossier advanced to stage {dossier.current_stage}")
assert dossier.current_stage == 4

# 2. Alemi at stage 4 -> Forbidden (403)
res_forbidden = client.post(
    f'/dossier/{dossier.archive_number}/sign/',
    data=json.dumps({"notes": "تلاش غیرمجاز"}),
    content_type='application/json'
)
print(f"[TEST 2] Alemi sign stage 4 (forbidden): status={res_forbidden.status_code}")
assert res_forbidden.status_code == 403

# 3. Heydari at stage 4 -> Authorized (200)
client.force_login(heydari)
res_heydari = client.post(
    f'/dossier/{dossier.archive_number}/sign/',
    data=json.dumps({"notes": "ورود وام صندوق توسط حیدری"}),
    content_type='application/json'
)
print(f"[TEST 3] Heydari sign stage 4: status={res_heydari.status_code}")
assert res_heydari.status_code == 200

dossier.refresh_from_db()
print(f"[OK] Dossier advanced to stage {dossier.current_stage}")
assert dossier.current_stage == 5

# 4. Housing Chief at stage 5 -> Full authority (200)
client.force_login(chief)
res_chief = client.post(
    f'/dossier/{dossier.archive_number}/sign/',
    data=json.dumps({"notes": "تایید با اختیارات تام رئیس مسکن"}),
    content_type='application/json'
)
print(f"[TEST 4] Chief sign stage 5: status={res_chief.status_code}")
assert res_chief.status_code == 200

dossier.refresh_from_db()
print(f"[OK] Dossier advanced to stage {dossier.current_stage}")
assert dossier.current_stage == 6

# 5. Field change log test with delta tracking
save_payload = json.dumps({
    'archive_number': dossier.archive_number,
    'wife_national_id': '0012345678',
    'wife_first_name': 'فاطمه',
    'wife_last_name': 'رضایی',
    'price_total': 18500000000
})
res_save = client.post(
    f'/dossier/{dossier.archive_number}/save/',
    data=save_payload,
    content_type='application/json'
)
print(f"[TEST 5] Save draft status: {res_save.status_code}")
assert res_save.status_code == 200

recent_logs = DossierFieldChangeLog.objects.filter(dossier=dossier).order_by('-timestamp')[:4]
print(f"[OK] Logged field changes count: {recent_logs.count()}")
for l in recent_logs:
    print(f"   --> [{l.field_name}] Old: '{l.old_value}' | New: '{l.new_value}' | Actor: {l.changed_by} | Stage: {l.stage}")

# 6. Audit logs view test
res_audit_chief = client.get('/audit-logs/')
print(f"[TEST 6a] Audit logs page for Chief: status={res_audit_chief.status_code}")
assert res_audit_chief.status_code == 200

client.force_login(admin)
res_audit_admin = client.get('/audit-logs/')
print(f"[TEST 6b] Audit logs page for Superadmin: status={res_audit_admin.status_code}")
assert res_audit_admin.status_code == 200

client.force_login(alemi)
res_audit_alemi = client.get('/audit-logs/')
print(f"[TEST 6c] Audit logs page for Alemi (forbidden, redirected): status={res_audit_alemi.status_code}")
assert res_audit_alemi.status_code == 302

print('\n=============================================')
print('ALL INTEGRITY AND ACCESS CONTROL TESTS PASSED')
print('=============================================')
