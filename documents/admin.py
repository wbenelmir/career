# documents/admin.py
from django.contrib import admin

from .models import DocumentType, ApplicationDocument, PosteDocumentRequirement


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_required",
        "is_active",
        "display_order",
    )
    list_filter = (
        "is_required",
        "is_active",
    )
    search_fields = (
        "name",
    )
    ordering = (
        "display_order",
        "name",
    )


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "document_type",
        "uploaded_at",
    )
    list_filter = (
        "document_type",
        "uploaded_at",
    )
    search_fields = (
        "application__application_number",
        "application__tracking_code",
        "document_type__name",
    )
    ordering = ("-uploaded_at",)
    autocomplete_fields = ("application", "document_type")


@admin.register(PosteDocumentRequirement)
class PosteDocumentRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "poste",
        "document_type",
        "is_required",
        "allowed_extensions",
        "max_file_size_mb",
        "is_active",
    )
    list_filter = (
        "poste",
        "is_required",
        "is_active",
    )
    search_fields = (
        "poste__title",
        "document_type__name",
    )
    ordering = ("poste", "display_order")
    autocomplete_fields = ("poste", "document_type")