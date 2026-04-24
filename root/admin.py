from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Poste, LegalReference

class LegalReferenceResource(resources.ModelResource):
    class Meta:
        model = LegalReference
        fields = (
            "id",
            "title",
            "reference_number",
            "reference_type",
            "published_date",
            "description",
            "document_url",
            "is_active",
            "display_order",
            "created_at",
            "updated_at",
        )
        export_order = fields
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True

@admin.register(LegalReference)
class LegalReferenceAdmin(ImportExportModelAdmin):
    resource_class = LegalReferenceResource

    list_display = (
        "title",
        "reference_number",
        "reference_type",
        "published_date",
        "is_active",
        "display_order",
    )
    list_filter = (
        "reference_type",
        "is_active",
        "published_date",
    )
    search_fields = (
        "title",
        "reference_number",
        "description",
    )
    list_editable = (
        "is_active",
        "display_order",
    )
    ordering = (
        "display_order",
        "-published_date",
        "title",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_per_page = 50

    fieldsets = (
        ("البيانات الأساسية", {
            "fields": (
                "title",
                "reference_number",
                "reference_type",
                "published_date",
            )
        }),
        ("المحتوى", {
            "fields": (
                "description",
                "document_url",
            )
        }),
        ("إعدادات العرض", {
            "fields": (
                "is_active",
                "display_order",
            )
        }),
        ("معلومات النظام", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

class PosteResource(resources.ModelResource):
    class Meta:
        model = Poste
        fields = (
            "id",
            "title",
            "slug",
            "poste_type",
            "direction",
            "sub_direction",
            "positions_count",
            "description",
            "legal_reference",
            "is_open",
            "publish_date",
            "deadline",
            "created_at",
            "updated_at",
        )
        export_order = fields
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True

@admin.register(Poste)
class PosteAdmin(ImportExportModelAdmin):
    resource_class = PosteResource

    list_display = (
        "title",
        "direction",
        "sub_direction",
        "poste_type",
        "positions_count",
        "status_badge",
        "publish_date",
        "deadline",
    )
    list_filter = (
        "poste_type",
        "is_open",
        "publish_date",
        "deadline",
    )
    search_fields = (
        "title",
        "slug",
        "direction",
        "sub_direction",
        "description",
    )
    ordering = (
        "-publish_date",
        "-created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    prepopulated_fields = {
        "slug": ("title",)
    }
    list_per_page = 50

    fieldsets = (
        ("المعلومات الأساسية", {
            "fields": (
                "title",
                "slug",
                "poste_type",
                "direction",
                "sub_direction",
                "description",
            )
        }),
        ("المعطيات التنظيمية", {
            "fields": (
                "legal_reference",
                "positions_count",
                "is_open",
            )
        }),
        ("التواريخ", {
            "fields": (
                "publish_date",
                "deadline",
            )
        }),
        ("معلومات النظام", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    @admin.display(description="الحالة")
    def status_badge(self, obj):
        if obj.is_open:
            return format_html(
                '<span style="color: #198754; font-weight: 700;">{}</span>',
                "مفتوح"
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: 700;">{}</span>',
            "مغلق"
        )