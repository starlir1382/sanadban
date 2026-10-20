from django.urls import path
from . import views

urlpatterns = [
    path("", views.dossier_list_view, name="dossier_list"),
    path("dossier/<int:pk>/", views.dossier_detail_view, name="dossier_detail"),
    path("dossier/<int:pk>/save/", views.save_dossier_draft_view, name="dossier_save"),
    path("dossier/<int:pk>/set-stage/", views.set_dossier_stage_view, name="dossier_set_stage"),
    path("dossier/<int:pk>/sign/", views.electronic_sign_action, name="dossier_sign"),
    path("dossier/<int:pk>/return/", views.return_stage_action, name="dossier_return"),
    path("dossier/<int:pk>/print/notary-letter/", views.notary_letter_print_view, name="notary_letter_print"),
    path("dossier/<int:pk>/print/summary/", views.dossier_summary_print_view, name="dossier_summary_print"),
    path("dossier/<int:pk>/upload-scan/", views.upload_scan_attachment_view, name="dossier_upload_scan"),
    path("api/lookup-unit/", views.lookup_preselected_unit_api, name="lookup_unit_api"),
]
