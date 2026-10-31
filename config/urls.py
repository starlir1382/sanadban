from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.conf import settings
from django.views.static import serve
from django.http import FileResponse, HttpResponse
from workflow import views as workflow_views

def favicon_view(request):
    favicon_path = settings.BASE_DIR / 'static' / 'img' / 'favicon.ico'
    if favicon_path.exists():
        return FileResponse(open(favicon_path, 'rb'), content_type='image/x-icon')
    return HttpResponse(status=204)

urlpatterns = [
    # Ensure /admin/bank-letter/ is caught BEFORE Django admin's catch_all_view
    path('admin/bank-letter/', workflow_views.bank_letter_sender_view),
    path('admin/bank-letter/send/', workflow_views.bank_letter_submit_api),
    path('admin/bank-letter/export-excel/', workflow_views.bank_letter_export_excel),

    path('favicon.ico', favicon_view, name='favicon'),

    path('admin/', admin.site.urls),
    path('', include('workflow.urls')),
    path('index.html', lambda req: redirect('dossier_list')),

    # Serve media files (uploaded documents, signatures, check scans) in both debug and production
    re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'), serve, {'document_root': settings.MEDIA_ROOT}),
]
