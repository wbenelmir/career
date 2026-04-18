# applications/admin.py

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import CandidateProfile, Application, ApplicationChoice


# =========================
# Reject Form
# =========================

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


# =========================
# Candidate Admin
# =========================

@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):

    list_display = (
        "last_name",
        "first_name",
        "national_id_number",
        "email",
        "phone_number",
        "current_position_grade",
        "eligibility_preview",
        "created_at",
    )

    search_fields = (
        "first_name",
        "last_name",
        "national_id_number",
        "email",
        "phone_number",
    )

    list_filter = (
        "gender",
        "wilaya",
        "created_at",
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

    def eligibility_preview(self, obj):
        return "مؤهل مبدئيًا" if obj.is_eligible_for_head_of_office() else "غير مؤهل"
    eligibility_preview.short_description = "الأهلية"


# =========================
# ApplicationChoice Inline
# =========================

class ApplicationChoiceInline(admin.TabularInline):
    model = ApplicationChoice
    extra = 0
    fields = ("priority", "poste")
    ordering = ("priority",)


# =========================
# Application Admin
# =========================

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):

    inlines = [ApplicationChoiceInline]

    # =========================
    # LIST VIEW
    # =========================

    list_display = (
        "application_number",
        "candidate",
        "primary_poste_display",
        "postes_summary",
        "status",
        "motivation_word_count_display",
        "documents_complete",
        "is_eligible",
        "submitted_at",
    )

    list_select_related = ("candidate", "poste")

    search_fields = (
        "application_number",
        "tracking_code",
        "candidate__first_name",
        "candidate__last_name",
        "candidate__national_id_number",
    )

    list_filter = (
        "status",
        "is_eligible",
        "poste",
        "submitted_at",
    )

    # =========================
    # READONLY
    # =========================

    readonly_fields = (
        "application_number",
        "tracking_code",
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
        "motivation_display",
        "motivation_word_count_display",
        "postes_summary",
    )

    autocomplete_fields = ("candidate", "poste")

    # =========================
    # FIELDSETS (EVALUATION READY)
    # =========================

    fieldsets = (

        ("👤 معلومات المترشح", {
            "fields": (
                "candidate",
            )
        }),

        ("📌 المناصب المختارة", {
            "fields": (
                "poste",
                "postes_summary",
            )
        }),

        ("✍️ رسالة التحفيز", {
            "fields": (
                "motivation_display",
                "motivation_word_count_display",
            )
        }),

        ("📄 حالة الملف", {
            "fields": (
                "documents_complete",
                "is_eligible",
            )
        }),

        ("⚙️ القرار الإداري", {
            "fields": (
                "status",
                "rejection_reason",
                "admin_notes",
                "admin_actions_links",
            )
        }),

        ("🧾 التتبع", {
            "fields": (
                "application_number",
                "tracking_code",
            )
        }),

        ("🕓 التواريخ", {
            "fields": (
                "submitted_at",
                "reviewed_at",
                "preselected_at",
                "interview_scheduled_at",
                "interview_completed_at",
                "final_decision_at",
                "created_at",
                "updated_at",
            )
        }),
    )

    ordering = ("-created_at",)

    # =========================
    # DISPLAY HELPERS
    # =========================

    def primary_poste_display(self, obj):
        poste = obj.get_primary_poste()
        return poste.title if poste else "-"
    primary_poste_display.short_description = "المنصب الأساسي"

    def postes_summary(self, obj):
        choices = obj.get_ordered_choices()

        if not choices.exists():
            return "-"

        html = "<br>".join([
            f"{c.priority}. {c.poste.title}"
            for c in choices
        ])

        return format_html(html)

    postes_summary.short_description = "ترتيب المناصب"

    def documents_complete(self, obj):
        return obj.has_all_required_documents()
    documents_complete.boolean = True
    documents_complete.short_description = "الوثائق مكتملة"

    # =========================
    # MOTIVATION
    # =========================

    def motivation_display(self, obj):
        if not obj.motivation_text:
            return format_html('<span style="color:#999;">لا توجد رسالة</span>')

        return format_html(
            '<div style="max-width:800px; line-height:1.8; white-space:pre-line; direction:rtl;">{}</div>',
            obj.motivation_text
        )
    motivation_display.short_description = "رسالة التحفيز"

    def motivation_word_count_display(self, obj):
        count = obj.motivation_word_count()

        color = "#198754" if count >= 100 else "#dc3545"

        return format_html(
            '<strong style="color:{};">{} كلمة</strong>',
            color,
            count
        )
    motivation_word_count_display.short_description = "عدد الكلمات"

    # =========================
    # ADMIN ACTION LINKS
    # =========================

    def admin_actions_links(self, obj):
        if not obj.pk:
            return "احفظ أولًا"

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

    # =========================
    # STATUS ACTIONS
    # =========================

    def _apply_status_action(self, request, queryset, new_status, note, visible_to_candidate=False):
        for application in queryset:
            try:
                application.set_status(
                    new_status,
                    changed_by=request.user,
                    note=note,
                    visible_to_candidate=visible_to_candidate,
                )
            except Exception as e:
                self.message_user(request, str(e), level=messages.ERROR)

    @admin.action(description="قيد الدراسة")
    def action_mark_under_review(self, request, queryset):
        self._apply_status_action(request, queryset, Application.Status.UNDER_REVIEW, "تمت المراجعة")

    @admin.action(description="ملف ناقص")
    def action_mark_incomplete(self, request, queryset):
        self._apply_status_action(request, queryset, Application.Status.INCOMPLETE, "ملف ناقص", True)

    @admin.action(description="قبول أولي")
    def action_preselect(self, request, queryset):
        self._apply_status_action(request, queryset, Application.Status.PRESELECTED, "قبول أولي", True)

    @admin.action(description="قبول نهائي")
    def action_accept_final(self, request, queryset):
        self._apply_status_action(request, queryset, Application.Status.FINAL_ACCEPTED, "قبول نهائي", True)

    @admin.action(description="قائمة الاحتياط")
    def action_move_to_waiting_list(self, request, queryset):
        self._apply_status_action(request, queryset, Application.Status.WAITING_LIST, "قائمة الاحتياط", True)

    actions = (
        "action_mark_under_review",
        "action_mark_incomplete",
        "action_preselect",
        "action_accept_final",
        "action_move_to_waiting_list",
    )

    # =========================
    # REJECT VIEWS (UNCHANGED)
    # =========================

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<int:application_id>/reject/preliminary/", self.admin_site.admin_view(self.reject_preliminary_view)),
            path("<int:application_id>/reject/final/", self.admin_site.admin_view(self.reject_final_view)),
        ]
        return custom_urls + urls

    def _reject_application(self, request, application_id, target_status, page_title):
        application = get_object_or_404(Application, pk=application_id)

        if request.method == "POST":
            form = AdminRejectApplicationForm(request.POST)
            if form.is_valid():
                application.rejection_reason = form.cleaned_data["rejection_reason"]
                application.set_status(
                    target_status,
                    changed_by=request.user,
                    note=form.cleaned_data["note"],
                    visible_to_candidate=form.cleaned_data["visible_to_candidate"],
                )
                return HttpResponseRedirect(
                    reverse("admin:applications_application_change", args=[application.pk])
                )
        else:
            form = AdminRejectApplicationForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": page_title,
            "application_obj": application,
        }

        return render(request, "admin/applications/reject_application.html", context)

    def reject_preliminary_view(self, request, application_id):
        return self._reject_application(request, application_id, Application.Status.PRELIMINARY_REJECTED, "رفض أولي")

    def reject_final_view(self, request, application_id):
        return self._reject_application(request, application_id, Application.Status.FINAL_REJECTED, "رفض نهائي")