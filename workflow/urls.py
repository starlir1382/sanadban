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
    path("dossier/<int:pk>/reject-red/", views.reject_red_form_j_action, name="dossier_reject_red"),
    path("dossier/<int:pk>/return-red/", views.return_red_form_j_action, name="dossier_return_red"),
    path("dossier/<int:pk>/print/notary-letter/", views.notary_letter_print_view, name="notary_letter_print"),
    path("dossier/<int:pk>/print/summary/", views.dossier_summary_print_view, name="dossier_summary_print"),
    path("dossier/<int:pk>/print/rejection-letter/", views.red_rejection_letter_print_view, name="red_rejection_letter_print"),
    path("dossier/<int:pk>/print/checks/", views.dossier_print_checks_view, name="dossier_print_checks"),
    path("dossier/<int:pk>/checks/archive-receipt/", views.archive_check_receipt_api, name="archive_check_receipt_api"),
    path("dossier/<int:pk>/checks/upload-scan-and-create-receipt/", views.upload_check_scan_and_create_receipt_view, name="upload_check_scan_and_create_receipt"),
    path("dossier/<int:pk>/upload-scan/", views.upload_scan_attachment_view, name="dossier_upload_scan"),
    path("dossier/<int:pk>/attachment/<int:attachment_id>/delete/", views.delete_scan_attachment_view, name="dossier_delete_attachment"),
    path("dossier/<int:pk>/upload-signature/", views.upload_dossier_signature_view, name="dossier_upload_signature"),
    path("api/lookup-unit/", views.lookup_preselected_unit_api, name="lookup_unit_api"),

    # Enterprise Authentication & Profile
    path("login/", views.user_login_view, name="login"),
    path("logout/", views.user_logout_view, name="logout"),
    path("profile/", views.user_profile_view, name="user_profile"),
    path("security/first-login-setup/", views.first_login_setup_view, name="first_login_setup"),

    # Staff & User Access Administration
    path("users/", views.users_management_view, name="users_management"),
    path("users/create/", views.create_user_action, name="create_user_action"),
    path("users/<int:user_id>/edit/", views.edit_user_action, name="edit_user_action"),
    path("users/<int:user_id>/toggle-status/", views.toggle_user_status_action, name="toggle_user_status_action"),
    path("users/<int:user_id>/reset-password/", views.reset_user_password_action, name="reset_user_password_action"),

    # Comprehensive System Audit Trail (Super Admin & Housing Chief)
    path("audit-logs/", views.audit_logs_view, name="audit_logs"),

    # Bulk Excel Dossier Operations (Admin & Housing Chief Only)
    path("excel/template/create/", views.excel_template_create_view, name="excel_template_create"),
    path("excel/template/update/", views.excel_template_update_view, name="excel_template_update"),
    path("excel/upload/create/", views.excel_upload_create_view, name="excel_upload_create"),
    path("excel/upload/update/", views.excel_upload_update_view, name="excel_upload_update"),
path("excel/export/", views.excel_export_all_view, name="excel_export_all"),
    # Bank Letter Sender Component (ارسال دسته جمعی نامه بانک)
    path("bank-letter/", views.bank_letter_sender_view, name="bank_letter_sender"),
    path("bank-letter/send/", views.bank_letter_submit_api, name="bank_letter_submit"),
    path("bank-letter/export-excel/", views.bank_letter_export_excel, name="bank_letter_export_excel"),

]
