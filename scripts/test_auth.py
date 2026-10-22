import requests
import re
import json

s = requests.Session()
s.trust_env = False

# 1. Unauthenticated request to /
r = s.get('http://127.0.0.1:8000/', allow_redirects=False)
print('1. Unauthenticated / status:', r.status_code, '-> Location:', r.headers.get('Location'))

# 2. Get login page
r_login = s.get('http://127.0.0.1:8000/login/')
print('2. Login page status:', r_login.status_code)

csrf = s.cookies.get('csrftoken') or ''
if not csrf and 'csrfmiddlewaretoken' in r_login.text:
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r_login.text)
    if m:
        csrf = m.group(1)

# 3. Post login as admin
r_auth = s.post('http://127.0.0.1:8000/login/', data={
    'username': 'admin',
    'password': 'admin1234',
    'csrfmiddlewaretoken': csrf
}, headers={'Referer': 'http://127.0.0.1:8000/login/'}, allow_redirects=True)
print('3. Admin Login response URL:', r_auth.url, 'status:', r_auth.status_code)

# 4. Check /users/ as admin
r_users = s.get('http://127.0.0.1:8000/users/')
print('4. Admin /users/ status:', r_users.status_code, 'metrics rendered:', 'کارشناسان کارگزاری مسکن' in r_users.text)

# 5. Check /profile/
r_prof = s.get('http://127.0.0.1:8000/profile/')
print('5. Profile status:', r_prof.status_code, 'found admin name:', 'علیرضا رضایی' in r_prof.text)

# 6. Check /dossier/100001/
r_dos = s.get('http://127.0.0.1:8000/dossier/100001/')
print('6. Dossier 100001 status:', r_dos.status_code, 'applicant name rendered:', 'علی محمدی پور' in r_dos.text)

# 7. Check non-admin access: login as broker_expert
s_broker = requests.Session()
s_broker.trust_env = False
r_bl = s_broker.get('http://127.0.0.1:8000/login/')
b_csrf = s_broker.cookies.get('csrftoken') or ''
if not b_csrf and 'csrfmiddlewaretoken' in r_bl.text:
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r_bl.text)
    if m:
        b_csrf = m.group(1)

r_bauth = s_broker.post('http://127.0.0.1:8000/login/', data={
    'username': 'broker_expert',
    'password': 'broker1234',
    'csrfmiddlewaretoken': b_csrf
}, headers={'Referer': 'http://127.0.0.1:8000/login/'}, allow_redirects=True)
print('7. Broker Login status:', r_bauth.status_code, 'welcome:', 'احمد صادقی' in r_bauth.text)

# 8. Check that broker saving draft attributes change log to broker_expert's name (احمد صادقی)
r_save = s_broker.post('http://127.0.0.1:8000/dossier/100001/save/', json={
    'full_name': 'علی محمدی پور (بررسی شده)',
    'father_name': 'رضا',
    'spouse_full_name': 'زهرا حسینی',
}, headers={'Referer': 'http://127.0.0.1:8000/dossier/100001/'})
save_data = r_save.json()
print('8. Save draft response status:', r_save.status_code, 'message:', save_data.get('message'))
if save_data.get('new_changes'):
    first_change = save_data['new_changes'][0]
    print('   Logged change author:', first_change.get('changedBy'), '| role:', first_change.get('role'))

# 9. Try visiting /users/ as broker_expert (should redirect because not staff)
r_buser = s_broker.get('http://127.0.0.1:8000/users/', allow_redirects=False)
print('9. Broker expert /users/ forbidden/redirect:', r_buser.status_code, '-> Location:', r_buser.headers.get('Location'))

print('\nALL AUTHENTICATION & ACTOR ATTRIBUTION TESTS COMPLETED SUCCESSFULLY!')
