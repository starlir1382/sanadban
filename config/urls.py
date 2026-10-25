from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from workflow import views as workflow_views

urlpatterns = [
    # Ensure /admin/bank-letter/ is caught BEFORE Django admin's catch_all_view
    path('admin/bank-letter/', workflow_views.bank_letter_sender_view),
    path('admin/bank-letter/send/', workflow_views.bank_letter_submit_api),
    path('admin/bank-letter/export-excel/', workflow_views.bank_letter_export_excel),

    path('admin/', admin.site.urls),
    path('', include('workflow.urls')),
    path('index.html', lambda req: redirect('dossier_list')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
