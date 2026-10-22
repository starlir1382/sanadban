import os
import sys
import django
import json
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from workflow.models import HousingDossier, UserProfile, WorkflowSignatureLog

print('========================================================')
print('TESTING RETURN WORKFLOW, STAGE STICKINESS & FIRST LOGIN')
print('========================================================')

client = Client()

chief = User.objects.get(username='housing_chief')
admin = User.objects.get(username='admin')
broker_info = User.objects.get(username='broker_info')
heydari = User.objects.get(username='heydari')

# ----------------------------------------------------
# 1. TEST DIRECT STAGE JUMP PREVENTION (STICKY STAGES)
# ----------------------------------------------------
dossier, _ = HousingDossier.objects.get_or_create(archive_number=100001)
dossier.current_stage = 4
dossier.status = 'IN_PROGRESS'
dossier.save()

client.force_login(chief)
res_jump = client.post(
    f'/dossier/{dossier.archive_number}/set-stage/',
    data=json.dumps({"stage": 15}),
    content_type='application/json'
)
print(f"[TEST 1] Arbitrary stage jump attempt: status={res_jump.status_code}")
assert res_jump.status_code == 403
dossier.refresh_from_db()
assert dossier.current_stage == 4
print("[OK] Dossier stage strictly stuck to Stage 4 (Arbitrary jumps prevented).")

# ----------------------------------------------------
# 2. TEST RETURN ACTION & DOCUMENT STATE
# ----------------------------------------------------
# Heydari is authorized for stage 4. Heydari returns dossier to stage 1 with notes.
client.force_login(heydari)
return_payload = json.dumps({
    "target_stage": 1,
    "notes": "نقص در مدارک پلاک ثبتی و مشخصات هویتی همسر"
})
res_return = client.post(
    f'/dossier/{dossier.archive_number}/return/',
    data=return_payload,
    content_type='application/json'
)
print(f"[TEST 2] Return action: status={res_return.status_code}")
assert res_return.status_code == 200

dossier.refresh_from_db()
print(f"[OK] Dossier current_stage={dossier.current_stage}, status={dossier.status}")
assert dossier.current_stage == 1
assert dossier.status == "RETURNED"
assert dossier.return_reason == "نقص در مدارک پلاک ثبتی و مشخصات هویتی همسر"
assert dossier.return_from_stage == 4

# Check return signature log
last_return_log = WorkflowSignatureLog.objects.filter(dossier=dossier, action="RETURN").first()
assert last_return_log is not None
print(f"[OK] Logged return event: {last_return_log.from_stage} -> {last_return_log.to_stage}")

# ----------------------------------------------------
# 3. TEST RE-SIGNING ADVANCES AND CLEARS RETURN STATE
# ----------------------------------------------------
# Broker info is authorized for Stage 1 (allowed: 0,1,2).
client.force_login(broker_info)
res_sign = client.post(
    f'/dossier/{dossier.archive_number}/sign/',
    data=json.dumps({"notes": "پلاک ثبتی و اطلاعات همسر اصلاح و تایید گردید."}),
    content_type='application/json'
)
print(f"[TEST 3] Re-signing Stage 1: status={res_sign.status_code}")
assert res_sign.status_code == 200

dossier.refresh_from_db()
print(f"[OK] Dossier advanced to Stage {dossier.current_stage}, status={dossier.status}")
assert dossier.current_stage == 2
assert dossier.status == "IN_PROGRESS"
assert dossier.return_reason == ""

# ----------------------------------------------------
# 4. TEST FIRST LOGIN SECURITY & SIGNATURE UPLOAD
# ----------------------------------------------------
admin.profile.must_change_password = True
admin.profile.save()

client.force_login(admin)
# Attempt to visit dashboard
res_dash = client.get('/')
print(f"[TEST 4a] Attempt dashboard with must_change_password=True: status={res_dash.status_code}")
assert res_dash.status_code == 302
assert '/security/first-login-setup/' in res_dash.url

# Create in-memory dummy signature image
img = Image.new('RGB', (200, 60), color=(255, 255, 255))
img_io = BytesIO()
img.save(img_io, format='PNG')
img_io.seek(0)
sig_file = SimpleUploadedFile("my_signature.png", img_io.read(), content_type="image/png")

# Complete setup
res_setup = client.post(
    '/security/first-login-setup/',
    data={
        "new_password": "newSecurePassword123",
        "confirm_password": "newSecurePassword123",
        "signature_image": sig_file
    }
)
print(f"[TEST 4b] Post first-login setup: status={res_setup.status_code}")
assert res_setup.status_code == 302

admin.refresh_from_db()
assert admin.profile.must_change_password is False
assert bool(admin.profile.signature_image) is True
assert admin.check_password("newSecurePassword123") is True
print(f"[OK] Admin password updated and signature stored at: {admin.profile.signature_image.url}")

# Now dashboard is accessible
res_dash_after = client.get('/')
print(f"[TEST 4c] Visit dashboard after setup: status={res_dash_after.status_code}")
assert res_dash_after.status_code == 200

# Reset admin password back for future user convenience
admin.set_password("admin1234")
admin.profile.must_change_password = True
admin.profile.save()

print('\n========================================================')
print('ALL RETURN WORKFLOW & FIRST LOGIN TESTS PASSED CLEANLY!')
print('========================================================')
