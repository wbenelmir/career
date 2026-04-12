# applications/admin.py
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import CandidateProfile, Application


class AdminRejectApplicationForm(forms.Form):
    rejection_reason = forms.CharField(
        label="سبب الرفض",
        widget=forms.Textarea(attrs={"rows": 5, "style": "width: 100%;"}),
        required=True,
    )
    note = forms.CharField(
        label="ملاحظة التتبع",
        widget=forms.Textarea(attrs={"rows": 3, "style": "width: 100%;"}),
        required=False,
    )
    visible_to_candidate = forms.BooleanField(
        label="إظهار الملاحظة للمترشح",
        required=False,
        initial=True,
    )


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "national_id_number",
        "email",
        "phone_number",
        "gender",
        "current_administration",
        "current_position_grade",
        "tenure_decision_date",
        "years_of_seniority",
        "years_of_effective_service",
        "eligibility_preview",
        "created_at",
    )

    search_fields = (
        "first_name",
        "last_name",
        "national_id_number",
        "email",
        "phone_number",
        "current_administration",
        "current_position_grade",
    )

    list_filter = (
        "gender",
        "current_position_grade",
        "wilaya",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "eligibility_preview",
    )

    fieldsets = (
        ("المعلومات الشخصية", {
            "fields": (
                "first_name",
                "last_name",
                "gender",
                "date_of_birth",
                "place_of_birth",
                "national_id_number",
            )
        }),
        ("معلومات الاتصال", {
            "fields": (
                "email",
                "phone_number",
                "address",
                "wilaya",
                "commune",
            )
        }),
        ("المعلومات المهنية", {
            "fields": (
                "current_administration",
                "current_position_grade",
                "current_function",
                "tenure_decision_date",
                "years_of_seniority",
                "years_of_effective_service",
                "eligibility_preview",
            )
        }),
        ("معلومات النظام", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    ordering = ("last_name", "first_name")

    def eligibility_preview(self, obj):
        return "مؤهل مبدئيًا" if obj.is_eligible_for_head_of_office() else "غير مؤهل مبدئيًا"
    eligibility_preview.short_description = "الأهلية الأولية"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "application_number",
        "candidate",
        "poste",
        "status",
        "is_eligible",
        "documents_complete",
        "submitted_at",
        "created_at",
    )

    list_select_related = ("candidate", "poste")

    search_fields = (
        "application_number",
        "tracking_code",
        "candidate__first_name",
        "candidate__last_name",
        "candidate__national_id_number",
        "poste__title",
    )

    list_filter = (
        "status",
        "is_eligible",
        "poste",
        "submitted_at",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "application_number",
        "tracking_code",
        "status",
        "is_eligible",
        "documents_complete",
        "submitted_at",
        "reviewed_at",
        "preselected_at",
        "interview_scheduled_at",
        "interview_completed_at",
        "final_decision_at",
        "created_at",
        "updated_at",
        "admin_actions_links",
    )

    autocomplete_fields = (
        "candidate",
        "poste",
    )

    actions = (
        "action_mark_under_review",
        "action_mark_incomplete",
        "action_preselect",
        "action_mark_interview_completed",
        "action_mark_no_show",
        "action_accept_final",
        "action_move_to_waiting_list",
    )

    fieldsets = (
        ("البيانات الأساسية", {
            "fields": (
                "candidate",
                "poste",
                "status",
                "is_eligible",
                "documents_complete",
            )
        }),
        ("بيانات التتبع", {
            "fields": (
                "application_number",
                "tracking_code",
            )
        }),
        ("القرار الإداري", {
            "fields": (
                "rejection_reason",
                "admin_notes",
                "admin_actions_links",
            )
        }),
        ("تواريخ المعالجة", {
            "fields": (
                "submitted_at",
                "reviewed_at",
                "preselected_at",
                "interview_scheduled_at",
                "interview_completed_at",
                "final_decision_at",
            )
        }),
        ("معلومات النظام", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    ordering = ("-created_at",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:application_id>/reject/preliminary/",
                self.admin_site.admin_view(self.reject_preliminary_view),
                name="applications_application_reject_preliminary",
            ),
            path(
                "<int:application_id>/reject/final/",
                self.admin_site.admin_view(self.reject_final_view),
                name="applications_application_reject_final",
            ),
        ]
        return custom_urls + urls

    def documents_complete(self, obj):
        return obj.has_all_required_documents()
    documents_complete.boolean = True
    documents_complete.short_description = "الوثائق مكتملة"

    def admin_actions_links(self, obj):
        if not obj.pk:
            return "احفظ الطلب أولًا لإظهار الإجراءات السريعة."

        preliminary_url = reverse(
            "admin:applications_application_reject_preliminary",
            args=[obj.pk],
        )
        final_url = reverse(
            "admin:applications_application_reject_final",
            args=[obj.pk],
        )

        return format_html(
            '<a class="button" href="{}" style="margin-left: 8px; background:#dc3545; color:white;">رفض أولي</a>'
            '<a class="button" href="{}" style="background:#6c757d; color:white;">رفض نهائي</a>',
            preliminary_url,
            final_url,
        )
    admin_actions_links.short_description = "إجراءات سريعة"

    def _apply_status_action(self, request, queryset, new_status, note, visible_to_candidate=False):
        success_count = 0
        error_count = 0

        for application in queryset:
            try:
                application.set_status(
                    new_status,
                    changed_by=request.user,
                    note=note,
                    visible_to_candidate=visible_to_candidate,
                )
                success_count += 1

            except ValidationError as exc:
                error_count += 1
                self.message_user(
                    request,
                    f"تعذر تحديث الطلب {application.application_number}: {exc}",
                    level=messages.ERROR,
                )

            except Exception as exc:
                error_count += 1
                self.message_user(
                    request,
                    f"حدث خطأ غير متوقع في الطلب {application.application_number}: {exc}",
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                f"تم تحديث {success_count} طلب(ات) بنجاح.",
                level=messages.SUCCESS,
            )

        if error_count and not success_count:
            self.message_user(
                request,
                "لم يتم تحديث أي طلب بسبب أخطاء في التحقق أو الانتقال بين الحالات.",
                level=messages.WARNING,
            )

    @admin.action(description="تغيير الحالة إلى: قيد الدراسة")
    def action_mark_under_review(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.UNDER_REVIEW,
            note="تم تحويل الطلب إلى قيد الدراسة من طرف الإدارة.",
            visible_to_candidate=False,
        )

    @admin.action(description="تغيير الحالة إلى: ملف ناقص")
    def action_mark_incomplete(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.INCOMPLETE,
            note="تم اعتبار الملف ناقصًا من طرف الإدارة.",
            visible_to_candidate=True,
        )

    @admin.action(description="تغيير الحالة إلى: قبول أولي")
    def action_preselect(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.PRESELECTED,
            note="تم قبول الطلب أوليًا من طرف الإدارة.",
            visible_to_candidate=True,
        )

    @admin.action(description="تغيير الحالة إلى: أُجريت المقابلة")
    def action_mark_interview_completed(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.INTERVIEW_COMPLETED,
            note="تم تسجيل إجراء المقابلة من طرف الإدارة.",
            visible_to_candidate=False,
        )

    @admin.action(description="تغيير الحالة إلى: لم يحضر المقابلة")
    def action_mark_no_show(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.NO_SHOW,
            note="تم تسجيل غياب المترشح عن المقابلة.",
            visible_to_candidate=True,
        )

    @admin.action(description="تغيير الحالة إلى: قبول نهائي")
    def action_accept_final(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.FINAL_ACCEPTED,
            note="تم قبول الطلب نهائيًا من طرف الإدارة.",
            visible_to_candidate=True,
        )

    @admin.action(description="تغيير الحالة إلى: قائمة الاحتياط")
    def action_move_to_waiting_list(self, request, queryset):
        self._apply_status_action(
            request,
            queryset,
            Application.Status.WAITING_LIST,
            note="تم تحويل الطلب إلى قائمة الاحتياط.",
            visible_to_candidate=True,
        )

    def _reject_application(self, request, application_id, target_status, page_title):
        application = get_object_or_404(Application, pk=application_id)

        if request.method == "POST":
            form = AdminRejectApplicationForm(request.POST)
            if form.is_valid():
                try:
                    application.rejection_reason = form.cleaned_data["rejection_reason"]
                    application.set_status(
                        target_status,
                        changed_by=request.user,
                        note=form.cleaned_data["note"] or "تم رفض الطلب من طرف الإدارة.",
                        visible_to_candidate=form.cleaned_data["visible_to_candidate"],
                    )

                    self.message_user(
                        request,
                        f"تم رفض الطلب {application.application_number} بنجاح.",
                        level=messages.SUCCESS,
                    )

                    change_url = reverse(
                        "admin:applications_application_change",
                        args=[application.pk],
                    )
                    return HttpResponseRedirect(change_url)

                except ValidationError as exc:
                    self.message_user(request, str(exc), level=messages.ERROR)
        else:
            form = AdminRejectApplicationForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": application,
            "title": page_title,
            "form": form,
            "application_obj": application,
        }
        return render(request, "admin/applications/reject_application.html", context)

    def reject_preliminary_view(self, request, application_id):
        return self._reject_application(
            request,
            application_id,
            Application.Status.PRELIMINARY_REJECTED,
            page_title="رفض أولي للطلب",
        )

    def reject_final_view(self, request, application_id):
        return self._reject_application(
            request,
            application_id,
            Application.Status.FINAL_REJECTED,
            page_title="رفض نهائي للطلب",
        )