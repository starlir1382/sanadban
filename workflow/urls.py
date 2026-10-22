from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Dossier Management
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

    # Enterprise Authentication & Profile
    path("login/", views.user_login_view, name="login"),
    path("logout/", views.user_logout_view, name="logout"),
    path("profile/", views.user_profile_view, name="user_profile"),

    # Staff & User Access Administration
    path("users/", views.users_management_view, name="users_management"),
    path("users/create/", views.create_user_action, name="create_user_action"),
    path("users/<int:user_id>/toggle-status/", views.toggle_user_status_action, name="toggle_user_status_action"),
    path("users/<int:user_id>/reset-password/", views.reset_user_password_action, name="reset_user_password_action"),

    # Comprehensive System Audit Trail (Super Admin & Housing Chief)
    path("audit-logs/", views.audit_logs_view, name="audit_logs"),
]
