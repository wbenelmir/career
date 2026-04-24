from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import NotificationLog

class NotificationLogResource(resources.ModelResource):
    class Meta:
        model = NotificationLog
        fields = (
            "id",
            "application",
            "to_email",
            "subject",
            "template_name",
            "status",
            "error",
            "created_at",
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True


@admin.register(NotificationLog)
class NotificationLogAdmin(ImportExportModelAdmin):
    resource_class = NotificationLogResource

    list_display = (
        "created_at",
        "to_email",
        "subject",
        "application",
        "template_name",
        "status",
        "error_preview",
    )

    list_filter = (
        "status",
        "template_name",
        "created_at",
    )

    search_fields = (
        "to_email",
        "subject",
        "template_name",
        "error",
        "application__application_number",
        "application__tracking_code",
    )

    readonly_fields = (
        "application",
        "to_email",
        "subject",
        "template_name",
        "status",
        "error",
        "created_at",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    save_on_top = True

    fieldsets = (
        ("معلومات الإشعار", {
            "fields": (
                "application",
                "to_email",
                "subject",
                "template_name",
                "status",
            )
        }),
        ("تفاصيل الخطأ", {
            "fields": ("error",)
        }),
        ("معلومات النظام", {
            "fields": ("created_at",)
        }),
    )

    def error_preview(self, obj):
        if not obj.error:
            return "-"
        return (obj.error[:80] + "...") if len(obj.error) > 80 else obj.error
    error_preview.short_description = "معاينة الخطأ"

    # Logs should not be editable manually
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False