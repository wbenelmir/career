# root/admin.py
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
        )
        export_order = fields
        import_id_fields = ("reference_number",)
        skip_unchanged = True
        report_skipped = True


@admin.register(LegalReference)
class LegalReferenceAdmin(ImportExportModelAdmin):
    resource_class = LegalReferenceResource

    list_display = (
        "title",
        "reference_number",
        "reference_type_display",
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

    readonly_fields = (
        "created_at",
        "updated_at",
    )

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

    ordering = ("display_order", "-published_date", "title")
    list_per_page = 50
    save_on_top = True

    def reference_type_display(self, obj):
        return obj.get_reference_type_display()
    reference_type_display.short_description = "التصنيف"


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
            "is_open",
            "publish_date",
            "deadline",
            "legal_reference",
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ("slug",)

    def before_import_row(self, row, **kwargs):
        mapping = {
            "وظائف عليا": "transfer",
            "مناصب عليا": "detachment",
            "رتب": "head_office",
        }
        poste_type = row.get("poste_type")
        if poste_type in mapping:
            row["poste_type"] = mapping[poste_type]


@admin.register(Poste)
class PosteAdmin(ImportExportModelAdmin):
    resource_class = PosteResource

    list_display = (
        "id",
        "title",
        "slug",
        "poste_type_display",
        "direction",
        "sub_direction",
        "positions_count",
        "is_open_display",
        "publish_date",
        "deadline",
        "description",
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

    autocomplete_fields = ("legal_reference",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }

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
                "created_at",
                "updated_at",
            )
        }),
    )

    ordering = ("-created_at",)
    list_per_page = 50
    save_on_top = True

    def poste_type_display(self, obj):
        return obj.get_poste_type_display()
    poste_type_display.short_description = "نوع المنصب"

    def is_open_display(self, obj):
        if obj.is_open:
            return format_html('<span style="color: #198754; font-weight: 700;">مفتوح</span>')
        return format_html('<span style="color: #dc3545; font-weight: 700;">مغلق</span>')
    is_open_display.short_description = "الحالة"