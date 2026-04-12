# tracking/admin.py
from django.contrib import admin

from .models import ApplicationTracking, InterviewSchedule


@admin.register(ApplicationTracking)
class ApplicationTrackingAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "status",
        "is_visible_to_candidate",
        "changed_by",
        "created_at",
    )

    list_filter = (
        "status",
        "is_visible_to_candidate",
        "created_at",
    )

    search_fields = (
        "application__application_number",
        "application__tracking_code",
        "application__candidate__first_name",
        "application__candidate__last_name",
        "note",
    )

    readonly_fields = (
        "application",
        "status",
        "note",
        "is_visible_to_candidate",
        "changed_by",
        "created_at",
    )

    ordering = ("created_at",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request):
        return False


@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "interview_date",
        "interview_time",
        "location",
        "created_by",
        "created_at",
    )

    list_filter = (
        "interview_date",
        "created_at",
    )

    search_fields = (
        "application__application_number",
        "application__tracking_code",
        "application__candidate__first_name",
        "application__candidate__last_name",
        "location",
        "note",
    )

    readonly_fields = (
        "created_by",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "application",
        "created_by",
    )

    ordering = ("-interview_date", "-interview_time")
    date_hierarchy = "interview_date"