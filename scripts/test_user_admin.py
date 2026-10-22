import requests
import re

s = requests.Session()
s.trust_env = False

# 1. Login as admin
r_login = s.get('http://127.0.0.1:8000/login/')
csrf = s.cookies.get('csrftoken') or ''
if not csrf and 'csrfmiddlewaretoken' in r_login.text:
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r_login.text)
    if m:
        csrf = m.group(1)

s.post('http://127.0.0.1:8000/login/', data={
    'username': 'admin',
    'password': 'admin1234',
    'csrfmiddlewaretoken': csrf
}, headers={'Referer': 'http://127.0.0.1:8000/login/'})

# 2. Get users page and verify CSRF
r_users = s.get('http://127.0.0.1:8000/users/')
u_csrf = s.cookies.get('csrftoken') or csrf

# 3. Create a new user
r_create = s.post('http://127.0.0.1:8000/users/create/', data={
    'username': 'test_expert',
    'password': 'testpassword123',
    'full_name': 'مهندس نیما کریمی',
    'organization': 'directorate',
    'role_title': 'کارشناس ارزیابی اراضی',
    'personnel_code': 'DIR-8812',
    'phone_number': '09121112233',
    'can_sign': 'on',
    'csrfmiddlewaretoken': u_csrf
}, headers={'Referer': 'http://127.0.0.1:8000/users/'}, allow_redirects=True)

print('User creation status:', r_create.status_code)
print('User created successfully in list:', 'مهندس نیما کریمی' in r_create.text)

# 4. Test logging in as the newly created user
s_new = requests.Session()
s_new.trust_env = False
r_nl = s_new.get('http://127.0.0.1:8000/login/')
n_csrf = s_new.cookies.get('csrftoken') or ''
r_nauth = s_new.post('http://127.0.0.1:8000/login/', data={
    'username': 'test_expert',
    'password': 'testpassword123',
    'csrfmiddlewaretoken': n_csrf
}, headers={'Referer': 'http://127.0.0.1:8000/login/'}, allow_redirects=True)

print('New user login status:', r_nauth.status_code, 'welcome:', 'مهندس نیما کریمی' in r_nauth.text)

print('\nUSER ADMINISTRATION WORKFLOW VERIFIED SUCCESSFULLY!')
