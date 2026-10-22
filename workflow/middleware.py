from django.shortcuts import redirect
from django.urls import reverse

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
