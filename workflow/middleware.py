import json
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages

class FirstLoginSecurityMiddleware:
    """
    Forces users (especially Admins on initial provisioning) to reset their default password
    and upload their official signature image before accessing any system features.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.must_change_password:
                allowed_paths = [
                    reverse('first_login_setup'),
                    reverse('logout'),
                ]
                current_path = request.path
                is_allowed = (
                    current_path.startswith('/static/') or
                    current_path.startswith('/uploads/') or
                    any(current_path == p or current_path.startswith(p) for p in allowed_paths)
                )
                if not is_allowed:
                    return redirect('first_login_setup')

        return self.get_response(request)


class ReadOnlyAccountMiddleware:
    """
    Guarantees that read-only accounts ('حساب صرفاً جهت نمایش') can ONLY read data (GET, HEAD, OPTIONS).
    Intercepts and blocks any attempt to make POST, PUT, PATCH, DELETE, or any mutating HTTP request,
    preventing any data modification system-wide.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and getattr(profile, 'is_readonly', False):
                # Safe idempotent HTTP methods are allowed
                if request.method in ('GET', 'HEAD', 'OPTIONS'):
                    return self.get_response(request)

                # Safe exemptions (e.g. logging out or toggling client-side ui-mode)
                try:
                    logout_url = reverse('logout')
                except Exception:
                    logout_url = '/logout/'
                try:
                    ui_mode_url = reverse('set_ui_mode')
                except Exception:
                    ui_mode_url = '/profile/ui-mode/'

                allowed_paths = [logout_url, ui_mode_url]
                current_path = request.path
                if any(current_path == p or current_path.startswith(p) for p in allowed_paths):
                    return self.get_response(request)

                # Block all other POST, PUT, PATCH, DELETE requests
                is_ajax_or_json = (
                    request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                    'application/json' in request.headers.get('accept', '') or
                    request.content_type == 'application/json' or
                    request.path.startswith('/api/')
                )
                if is_ajax_or_json:
                    return JsonResponse({
                        'success': False,
                        'status': 'error',
                        'error': 'حساب کاربری شما «صرفاً جهت نمایش» (فقط خواندنی) می‌باشد و امکان ثبت، ویرایش، حذف یا تغییر اطلاعات را ندارد.',
                        'message': 'حساب کاربری شما «صرفاً جهت نمایش» (فقط خواندنی) می‌باشد و امکان ثبت، ویرایش، حذف یا تغییر اطلاعات را ندارد.'
                    }, status=403)

                try:
                    messages.error(request, 'حساب کاربری شما «صرفاً جهت نمایش» (فقط خواندنی) است و امکان ثبت، ویرایش، حذف یا تغییر اطلاعات وجود ندارد.')
                except Exception:
                    pass
                referer = request.META.get('HTTP_REFERER')
                if referer:
                    return redirect(referer)
                return redirect('dossier_list')

        return self.get_response(request)
