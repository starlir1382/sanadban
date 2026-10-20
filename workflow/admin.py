from django.contrib import admin
from .models import Site, Project, PreSelectedUnit, HousingDossier, DossierAttachment, WorkflowSignatureLog

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "total_units")
    list_filter = ("site",)
    search_fields = ("name",)

@admin.register(PreSelectedUnit)
class PreSelectedUnitAdmin(admin.ModelAdmin):
    list_display = ("national_id", "full_name", "site", "project", "unit_number", "base_cost_without_loan")
    search_fields = ("national_id", "full_name", "project__name")
    list_filter = ("site", "decile")

class DossierAttachmentInline(admin.TabularInline):
    model = DossierAttachment
    extra = 0
    readonly_fields = ("stage", "title", "file_name", "file_sha256", "uploaded_by", "uploaded_at")

class WorkflowSignatureLogInLine(admin.TabularInline):
    model = WorkflowSignatureLog
    extra = 0
    readonly_fields = ("from_stage", "to_stage", "actor", "role", "action", "timestamp", "notes", "signature_hash")

@admin.register(HousingDossier)
class HousingDossierAdmin(admin.ModelAdmin):
    list_display = ("archive_number", "national_id", "full_name", "current_stage", "current_unit", "current_role", "is_locked")
    list_filter = ("current_stage", "is_locked", "site")
    search_fields = ("archive_number", "national_id", "full_name")
    inlines = [DossierAttachmentInline, WorkflowSignatureLogInLine]

@admin.register(DossierAttachment)
class DossierAttachmentAdmin(admin.ModelAdmin):
    list_display = ("title", "dossier", "stage", "uploaded_by", "uploaded_at", "file_sha256")
    list_filter = ("stage",)
    search_fields = ("title", "dossier__national_id", "dossier__archive_number")

@admin.register(WorkflowSignatureLog)
class WorkflowSignatureLogAdmin(admin.ModelAdmin):
    list_display = ("dossier", "action", "actor", "role", "timestamp", "signature_hash")
    list_filter = ("action",)
    search_fields = ("dossier__archive_number", "dossier__national_id", "actor")
    readonly_fields = [f.name for f in WorkflowSignatureLog._meta.fields]
