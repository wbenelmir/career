from django import forms
from django.contrib import admin, messages
from django.utils import timezone
import openpyxl
from django.http import HttpResponse

from datetime import timedelta
from django.http import HttpResponseRedirect
from django.db.models import Avg
from django.shortcuts import render, get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from notifications.services import NotificationService

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from .models import CandidateProfile, Application, ApplicationChoice, CompletionRequest, EvaluationNote
from .services import ApplicationWorkflowService
from tracking.models import ApplicationTracking

MAX_EXPORT_ROWS = 5000

# =========================================================
# REJECT FORM
# =========================================================

class AdminRejectApplicationForm(forms.Form):

    rejection_reason = forms.CharField(
        label="سبب الرفض",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "style": "width: 100%;",
            }
        ),
        required=True,
    )

    note = forms.CharField(
        label="ملاحظة التتبع",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "style": "width: 100%;",
            }
        ),
        required=False,
    )

    visible_to_candidate = forms.BooleanField(
        label="إظهار الملاحظة للمترشح",
        required=False,
        initial=True,
    )


# =========================================================
# CANDIDATE PROFILE ADMIN
# =========================================================

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
        return (
            "مؤهل مبدئيًا"
            if obj.is_eligible_for_head_of_office()
            else "غير مؤهل"
        )

    eligibility_preview.short_description = "الأهلية"


# =========================================================
# EVALUATION FILTERS
# =========================================================

class EvaluationReadinessFilter(admin.SimpleListFilter):

    title = "جاهزية التقييم"
    parameter_name = "evaluation_ready"

    def lookups(self, request, model_admin):
        return (
            ("ready", "جاهز للتقييم"),
            ("not_ready", "غير جاهز"),
        )

    def queryset(self, request, queryset):

        ready_ids = []

        for application in queryset:

            is_ready = (
                application.status == Application.Status.SUBMITTED
                and application.is_eligible
                and application.has_all_required_documents()
                and bool(application.motivation_text)
            )

            if is_ready:
                ready_ids.append(application.id)

        if self.value() == "ready":
            return queryset.filter(id__in=ready_ids)

        if self.value() == "not_ready":
            return queryset.exclude(id__in=ready_ids)

        return queryset


class MotivationQualityFilter(admin.SimpleListFilter):

    title = "جودة الدافع"
    parameter_name = "motivation_quality"

    def lookups(self, request, model_admin):
        return (
            ("weak", "ضعيف"),
            ("acceptable", "مقبول"),
            ("good", "جيد"),
        )

    def queryset(self, request, queryset):

        weak_ids = []
        acceptable_ids = []
        good_ids = []

        for application in queryset:

            count = application.motivation_word_count()

            if count < 80:
                weak_ids.append(application.id)

            elif count < 150:
                acceptable_ids.append(application.id)

            else:
                good_ids.append(application.id)

        if self.value() == "weak":
            return queryset.filter(id__in=weak_ids)

        if self.value() == "acceptable":
            return queryset.filter(id__in=acceptable_ids)

        if self.value() == "good":
            return queryset.filter(id__in=good_ids)

        return queryset


class DocumentsCompletenessFilter(admin.SimpleListFilter):

    title = "حالة الملف"
    parameter_name = "documents_complete"

    def lookups(self, request, model_admin):
        return (
            ("complete", "ملف مكتمل"),
            ("incomplete", "ملف ناقص"),
        )

    def queryset(self, request, queryset):

        complete_ids = []
        incomplete_ids = []

        for application in queryset:

            if application.has_all_required_documents():
                complete_ids.append(application.id)
            else:
                incomplete_ids.append(application.id)

        if self.value() == "complete":
            return queryset.filter(id__in=complete_ids)

        if self.value() == "incomplete":
            return queryset.filter(id__in=incomplete_ids)

        return queryset


# =========================================================
# INLINE
# =========================================================

class ApplicationChoiceInline(admin.TabularInline):

    model = ApplicationChoice

    extra = 0

    fields = (
        "priority",
        "poste",
    )

    readonly_fields = (
        "priority",
        "poste",
    )

    can_delete = False

    ordering = ("priority",)

class CompletionRequestInline(admin.TabularInline):

    model = CompletionRequest

    extra = 0

    fields = (
        "message",
        "deadline",
        "is_resolved",
        "resolved_at",
        "created_by",
        "created_at",
    )

    readonly_fields = (
        "resolved_at",
        "created_by",
        "created_at",
    )

    ordering = ("-created_at",)

    can_delete = False

class EvaluationNoteInline(admin.TabularInline):

    model = EvaluationNote

    extra = 0

    fields = (
        "note",
        "created_by",
        "created_at",
    )

    readonly_fields = (
        "created_by",
        "created_at",
    )

    ordering = ("-created_at",)

    can_delete = False

    def has_add_permission(
        self,
        request,
        obj=None
    ):

        if obj and obj.is_finalized():
            return False

        return super().has_add_permission(
            request,
            obj,
        )

    def has_change_permission(
        self,
        request,
        obj=None
    ):

        if obj and obj.is_finalized():
            return False

        return super().has_change_permission(
            request,
            obj
        )
    
    def has_delete_permission(
        self,
        request,
        obj=None
    ):

        if obj and obj.is_finalized():
            return False

        return super().has_delete_permission(
            request,
            obj
        )
    
# =========================================================
# APPLICATION ADMIN
# =========================================================

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):

    class Media:

        css = {
            "all": (
                "admin/css/application_admin.css",
            )
        }

        change_list_template = (
            "admin/applications/application/change_list.html"
        )

    inlines = [
        ApplicationChoiceInline,
        CompletionRequestInline,
        EvaluationNoteInline,
    ]

    # =====================================================
    # LIST PAGE
    # =====================================================

    list_display = (
        "application_number",
        "candidate",
        "primary_poste_display",
        "evaluation_readiness_badge",
        "documents_status_badge",
        "motivation_quality_badge",

        "evaluation_score_display",
        "ranking_display",
        "decision_recommendation",

        "status_badge",
        "submitted_at",
    )

    list_select_related = ("candidate",)

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
        "evaluation_score",

        "poste",
        "poste__direction",

        DocumentsCompletenessFilter,
        EvaluationReadinessFilter,
        MotivationQualityFilter,

        "submitted_at",
    )

    ordering = ("-created_at","-evaluation_score","submitted_at")

    # =====================================================
    # READONLY
    # =====================================================

    readonly_fields = (
        "application_number",
        "tracking_code",
        "evaluation_summary",
        "candidate_overview",
        "documents_complete_display",
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

    autocomplete_fields = ("candidate",)

    # =====================================================
    # FIELDSETS
    # =====================================================

    fieldsets = (

        ("ملخص التقييم", {
            "fields": (
                "evaluation_summary",
            )
        }),

        ("معلومات المترشح", {
            "fields": (
                "candidate",
                "candidate_overview",
            )
        }),

        ("المناصب المختارة", {
            "fields": (
                "postes_summary",
            )
        }),

        ("رسالة التحفيز", {
            "fields": (
                "motivation_display",
                "motivation_word_count_display",
            )
        }),

        ("حالة الملف", {
            "fields": (
                "documents_complete_display",
                "is_eligible",
            )
        }),

        ("التقييم", {
            "fields": (
                "evaluation_score",
                "evaluation_comment",
            )
        }),

        ("القرار الإداري", {
            "fields": (
                "status",
                "rejection_reason",
                "admin_notes",
                "admin_actions_links",
            )
        }),

        ("التتبع", {
            "fields": (
                "application_number",
                "tracking_code",
            )
        }),

        ("التواريخ", {
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

    # =====================================================
    # POSTES
    # =====================================================

    def save_formset(
        self,
        request,
        form,
        formset,
        change
    ):

        instances = formset.save(commit=False)

        for instance in instances:

            if hasattr(instance, "created_by"):

                if not instance.created_by:
                    instance.created_by = request.user

            instance.save()

        formset.save_m2m()

    def primary_poste_display(self, obj):

        poste = obj.get_primary_poste()

        return poste.title if poste else "-"

    primary_poste_display.short_description = "المنصب الأساسي"

    def postes_summary(self, obj):

        choices = obj.get_ordered_choices()

        if not choices.exists():

            return mark_safe(
                '''
                <div class="app-admin-card">
                    لا توجد مناصب مختارة.
                </div>
                '''
            )

        rows = []

        for choice in choices:

            is_primary = choice.priority == 1

            badge_class = (
                "app-badge-info"
                if is_primary
                else "app-badge"
            )

            label = (
                "الاختيار الأساسي"
                if is_primary
                else f"الخيار رقم {choice.priority}"
            )

            rows.append(
                f'''
                <div class="app-poste-item">

                    <div class="app-poste-title">
                        {choice.poste.title}
                    </div>

                    <span class="app-badge {badge_class}">
                        {label}
                    </span>

                </div>
                '''
            )

        return mark_safe(
            f'''
            <div class="app-poste-list">
                {"".join(rows)}
            </div>
            '''
        )

    postes_summary.short_description = "ترتيب المناصب"

    def evaluation_score_display(self, obj):

        if obj.evaluation_score is None:

            return mark_safe(
                '<span class="app-badge">غير مقيم</span>'
            )

        score = float(obj.evaluation_score)

        if score >= 15:

            badge = "app-badge-success"

        elif score >= 10:

            badge = "app-badge-warning"

        else:

            badge = "app-badge-danger"

        return mark_safe(
            f'''
            <span class="app-badge {badge}">
                {score}/20
            </span>
            '''
        )

    evaluation_score_display.short_description = "التقييم"

    # =====================================================
    # EVALUATION BADGES
    # =====================================================

    def ranking_display(self, obj):

        if obj.evaluation_score is None:

            return mark_safe(
                '<span class="app-badge">—</span>'
            )

        higher_scores = Application.objects.filter(
            poste=obj.poste,
            evaluation_score__gt=obj.evaluation_score,
        ).count()

        rank = higher_scores + 1

        return mark_safe(
            f'''
            <span class="app-badge app-badge-primary">
                #{rank}
            </span>
            '''
        )

    ranking_display.short_description = "الترتيب"

    def evaluation_readiness_badge(self, obj):

        is_ready = (
            obj.status == Application.Status.SUBMITTED
            and obj.is_eligible
            and obj.has_all_required_documents()
            and bool(obj.motivation_text)
        )

        if is_ready:

            return mark_safe(
                '''
                <span class="app-badge app-badge-success">
                    جاهز للتقييم
                </span>
                '''
            )

        return mark_safe(
            '''
            <span class="app-badge app-badge-danger">
                غير جاهز
            </span>
            '''
        )

    evaluation_readiness_badge.short_description = "جاهزية التقييم"


    def documents_status_badge(self, obj):

        if obj.has_all_required_documents():

            return mark_safe(
                '''
                <span class="app-badge app-badge-success">
                    مكتمل
                </span>
                '''
            )

        return mark_safe(
            '''
            <span class="app-badge app-badge-warning">
                ناقص
            </span>
            '''
        )

    documents_status_badge.short_description = "الملف"


    def motivation_quality_badge(self, obj):

        count = obj.motivation_word_count()

        if count < 80:

            return mark_safe(
                '''
                <span class="app-badge app-badge-danger">
                    ضعيف
                </span>
                '''
            )

        elif count < 150:

            return mark_safe(
                '''
                <span class="app-badge app-badge-warning">
                    مقبول
                </span>
                '''
            )

        return mark_safe(
            '''
            <span class="app-badge app-badge-success">
                جيد
            </span>
            '''
        )

    motivation_quality_badge.short_description = "الدافع"


    def status_badge(self, obj):

        mapping = {

            Application.Status.DRAFT: (
                "app-badge",
                "مسودة",
            ),

            Application.Status.SUBMITTED: (
                "app-badge-info",
                "مُرسل",
            ),

            Application.Status.UNDER_REVIEW: (
                "app-badge-warning",
                "قيد الدراسة",
            ),

            Application.Status.PRESELECTED: (
                "app-badge-purple",
                "مقبول أوليًا",
            ),

            Application.Status.FINAL_ACCEPTED: (
                "app-badge-success",
                "مقبول نهائيًا",
            ),

            Application.Status.WAITING_LIST: (
                "app-badge-purple",
                "قائمة الاحتياط",
            ),

            Application.Status.INCOMPLETE: (
                "app-badge-warning",
                "ملف ناقص",
            ),

            Application.Status.PRELIMINARY_REJECTED: (
                "app-badge-danger",
                "مرفوض أوليًا",
            ),

            Application.Status.FINAL_REJECTED: (
                "app-badge-danger",
                "مرفوض نهائيًا",
            ),
        }

        badge_class, label = mapping.get(
            obj.status,
            ("app-badge", obj.status)
        )

        return mark_safe(
            f'''
            <span class="app-badge {badge_class}">
                {label}
            </span>
            '''
        )

    status_badge.short_description = "الحالة"

    def evaluation_summary(self, obj):

        is_ready = (
            obj.status == Application.Status.SUBMITTED
            and obj.is_eligible
            and obj.has_all_required_documents()
            and bool(obj.motivation_text)
        )

        readiness_label = (
            "جاهز للتقييم"
            if is_ready
            else "غير جاهز"
        )

        documents_label = (
            "ملف مكتمل"
            if obj.has_all_required_documents()
            else "ملف ناقص"
        )

        eligibility_label = (
            "مؤهل"
            if obj.is_eligible
            else "غير مؤهل"
        )

        return mark_safe(
            f'''
            <div class="app-summary-grid">

                <div class="app-summary-box">
                    <div class="app-summary-title">
                        جاهزية التقييم
                    </div>

                    <div class="app-summary-value">
                        {readiness_label}
                    </div>
                </div>

                <div class="app-summary-box">
                    <div class="app-summary-title">
                        حالة الملف
                    </div>

                    <div class="app-summary-value">
                        {documents_label}
                    </div>
                </div>

                <div class="app-summary-box">
                    <div class="app-summary-title">
                        الأهلية
                    </div>

                    <div class="app-summary-value">
                        {eligibility_label}
                    </div>
                </div>

            </div>
            '''
        )

    evaluation_summary.short_description = "ملخص التقييم"

    def candidate_overview(self, obj):

        candidate = obj.candidate

        return mark_safe(
            f'''
            <div class="app-admin-card">

                <div class="app-candidate-name">
                    {candidate.first_name} {candidate.last_name}
                </div>

                <div class="app-candidate-meta">

                    <div>
                        <strong>البريد الإلكتروني:</strong>
                        {candidate.email}
                    </div>

                    <div>
                        <strong>رقم التعريف الوطني:</strong>
                        {candidate.national_id_number}
                    </div>

                    <div>
                        <strong>رقم الهاتف:</strong>
                        {candidate.phone_number}
                    </div>

                    <div>
                        <strong>الرتبة الحالية:</strong>
                        {candidate.current_position_grade}
                    </div>

                </div>

            </div>
            '''
        )

    candidate_overview.short_description = "ملخص المترشح"

    def changelist_view(
        self,
        request,
        extra_context=None
    ):

        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )

        try:

            qs = response.context_data["cl"].queryset

            total = qs.count()

            under_review = qs.filter(
                status=Application.Status.UNDER_REVIEW
            ).count()

            incomplete = qs.filter(
                status=Application.Status.INCOMPLETE
            ).count()

            accepted = qs.filter(
                status=Application.Status.FINAL_ACCEPTED
            ).count()

            scored_qs = qs.exclude(
                evaluation_score__isnull=True
            )

            average_score = (
                round(
                    scored_qs.aggregate(
                        Avg("evaluation_score")
                    )["evaluation_score__avg"] or 0,
                    2
                )
            )

            response.context_data[
                "evaluation_stats"
            ] = {

                "total": total,

                "under_review": under_review,

                "incomplete": incomplete,

                "accepted": accepted,

                "average_score": average_score,
            }

        except Exception:
            pass

        return response

    # =====================================================
    # DOCUMENTS
    # =====================================================

    def documents_complete(self, obj):
        return obj.has_all_required_documents()

    documents_complete.boolean = True
    documents_complete.short_description = "الوثائق مكتملة"

    def documents_complete_display(self, obj):

        if obj.has_all_required_documents():

            return mark_safe(
                '<span class="app-badge app-badge-success">✔ ملف مكتمل</span>'
            )

        return mark_safe(
            '<span class="app-badge app-badge-danger">✘ ملف ناقص</span>'
        )

    documents_complete_display.short_description = "حالة الملف"

    # =====================================================
    # MOTIVATION
    # =====================================================

    def motivation_display(self, obj):

        if not obj.motivation_text:

            return mark_safe(
                '''
                <div class="app-admin-card">
                    لا توجد رسالة تحفيز.
                </div>
                '''
            )

        word_count = obj.motivation_word_count()

        quality_label = (
            "جيد"
            if word_count >= 150
            else "مقبول"
            if word_count >= 80
            else "ضعيف"
        )

        quality_class = (
            "app-badge-success"
            if word_count >= 150
            else "app-badge-warning"
            if word_count >= 80
            else "app-badge-danger"
        )

        return mark_safe(
            f'''
            <div class="app-motivation-wrapper">

                <div class="app-motivation-header">

                    <div>
                        <strong>رسالة التحفيز</strong>
                    </div>

                    <div style="display:flex;gap:10px;">

                        <span class="app-badge">
                            {word_count} كلمة
                        </span>

                        <span class="app-badge {quality_class}">
                            {quality_label}
                        </span>

                    </div>

                </div>

                <div class="app-motivation-body">
                    {obj.motivation_text}
                </div>

            </div>
            '''
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

    # =====================================================
    # ADMIN ACTION LINKS
    # =====================================================

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

    # =====================================================
    # STATUS ACTIONS
    # =====================================================

    def _apply_status_action(
        self,
        request,
        queryset,
        new_status,
        note,
        visible_to_candidate=False
    ):

        for application in queryset:

            try:

                ApplicationWorkflowService.transition(
                    application=application,
                    new_status=new_status,
                    changed_by=request.user,
                    note=note,
                    visible_to_candidate=visible_to_candidate,
                )

            except Exception as e:

                self.message_user(
                    request,
                    str(e),
                    level=messages.ERROR,
                )

    @admin.action(description="قيد الدراسة")
    def action_mark_under_review(self, request, queryset):

        for application in queryset:

            try:

                ApplicationWorkflowService.mark_under_review(
                    application,
                    request.user,
                )

            except Exception as e:

                self.message_user(
                    request,
                    str(e),
                    level=messages.ERROR,
                )


    @admin.action(description="ملف ناقص")
    def action_mark_incomplete(self, request, queryset):

        for application in queryset:

            try:

                ApplicationWorkflowService.mark_incomplete(
                    application,
                    request.user,
                )

            except Exception as e:

                self.message_user(
                    request,
                    str(e),
                    level=messages.ERROR,
                )

    @admin.action(description="طلب استكمال الملف")
    def action_request_completion(
        self,
        request,
        queryset
    ):

        for application in queryset:

            try:

                if application.is_finalized():

                    self.message_user(
                        request,
                        f"الطلب {application.application_number} نهائي ولا يمكن تعديله.",
                        level=messages.ERROR,
                    )

                    continue

                completion_request = (
                    CompletionRequest.objects.create(

                        application=application,

                        message=(
                            "يرجى استكمال الوثائق أو المعلومات "
                            "الناقصة ثم إعادة إرسال الطلب."
                        ),

                        deadline=timezone.now() + timedelta(days=7),

                        created_by=request.user,
                    )
                )

                # ApplicationTracking.objects.create(
                #     application=application,
                #     status=Application.Status.INCOMPLETE,
                #     note=(
                #         "تم طلب استكمال بعض الوثائق أو المعلومات "
                #         "الخاصة بالملف."
                #     ),
                #     changed_by=request.user,
                #     is_visible_to_candidate=True,
                # )

                try:

                    NotificationService.send_completion_request_notification(
                        application,
                        completion_request,
                    )

                except Exception:

                    pass

                ApplicationWorkflowService.mark_incomplete(
                    application=application,
                    user=request.user,
                    note=(
                        "تم طلب استكمال بعض الوثائق أو المعلومات "
                        "الخاصة بالملف."
                    ),
                )

                self.message_user(
                    request,
                    f"تم إرسال طلب استكمال للطلب {application.application_number}.",
                    level=messages.SUCCESS,
                )

            except Exception as e:

                self.message_user(
                    request,
                    str(e),
                    level=messages.ERROR,
                )

    @admin.action(description="قبول أولي")
    def action_preselect(self, request, queryset):

        for application in queryset:

            try:

                ApplicationWorkflowService.preselect(
                    application,
                    request.user,
                )

            except Exception as e:

                self.message_user(
                    request,
                    str(e),
                    level=messages.ERROR,
                )


    @admin.action(description="قبول نهائي")
    def action_accept_final(self, request, queryset):

        for application in queryset:

            try:

                ApplicationWorkflowService.accept_final(
                    application,
                    request.user,
                )

            except Exception as e:

                self.message_user(
                    request,
                    str(e),
                    level=messages.ERROR,
                )

    @admin.action(description="قائمة الاحتياط")
    def action_move_to_waiting_list(self, request, queryset):

        self._apply_status_action(
            request,
            queryset,
            Application.Status.WAITING_LIST,
            "قائمة الاحتياط",
            True
        )

    actions = (
        "action_mark_under_review",
        "action_mark_incomplete",
        "action_preselect",
        "action_accept_final",
        "action_move_to_waiting_list",
        "action_request_completion",
        "action_export_excel",
        "action_export_accepted_pdf",
    )

    # =====================================================
    # CUSTOM URLS
    # =====================================================

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [

            path(
                "<int:application_id>/reject/preliminary/",
                self.admin_site.admin_view(
                    self.reject_preliminary_view
                ),
                name="applications_application_reject_preliminary",
            ),

            path(
                "<int:application_id>/reject/final/",
                self.admin_site.admin_view(
                    self.reject_final_view
                ),
                name="applications_application_reject_final",
            ),
        ]

        return custom_urls + urls

    # =====================================================
    # REJECT WORKFLOW
    # =====================================================

    def _reject_application(
        self,
        request,
        application_id,
        target_status,
        page_title
    ):

        application = get_object_or_404(
            Application,
            pk=application_id,
        )

        if request.method == "POST":

            form = AdminRejectApplicationForm(request.POST)

            if form.is_valid():

                rejection_reason = form.cleaned_data[
                    "rejection_reason"
                ]

                note = form.cleaned_data["note"]

                visible_to_candidate = form.cleaned_data[
                    "visible_to_candidate"
                ]

                if target_status == Application.Status.PRELIMINARY_REJECTED:

                    ApplicationWorkflowService.reject_preliminary(
                        application=application,
                        reason=rejection_reason,
                        user=request.user,
                    )

                else:

                    ApplicationWorkflowService.reject_final(
                        application=application,
                        reason=rejection_reason,
                        user=request.user,
                    )

                if note:

                    ApplicationWorkflowService.create_tracking_entry(
                        application=application,
                        status=target_status,
                        changed_by=request.user,
                        note=note,
                        visible_to_candidate=visible_to_candidate,
                    )

                return HttpResponseRedirect(
                    reverse(
                        "admin:applications_application_change",
                        args=[application.pk]
                    )
                )

        else:

            form = AdminRejectApplicationForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": page_title,
            "application_obj": application,
        }

        return render(
            request,
            "admin/applications/reject_application.html",
            context,
        )

    def reject_preliminary_view(
        self,
        request,
        application_id
    ):

        return self._reject_application(
            request,
            application_id,
            Application.Status.PRELIMINARY_REJECTED,
            "رفض أولي"
        )

    def reject_final_view(
        self,
        request,
        application_id
    ):

        return self._reject_application(
            request,
            application_id,
            Application.Status.FINAL_REJECTED,
            "رفض نهائي"
        )

    def decision_recommendation(self, obj):

        if obj.status == Application.Status.INCOMPLETE:

            return mark_safe(
                '<span class="app-badge app-badge-warning">'
                'استكمال مطلوب'
                '</span>'
            )

        if obj.evaluation_score is None:

            return mark_safe(
                '<span class="app-badge">'
                'بانتظار التقييم'
                '</span>'
            )

        score = float(obj.evaluation_score)

        if score >= 15:

            return mark_safe(
                '<span class="app-badge app-badge-success">'
                'موصى بالقبول'
                '</span>'
            )

        if score >= 10:

            return mark_safe(
                '<span class="app-badge app-badge-primary">'
                'قابل للدراسة'
                '</span>'
            )

        return mark_safe(
            '<span class="app-badge app-badge-danger">'
            'موصى بالرفض'
            '</span>'
        )

    decision_recommendation.short_description = "التوصية"

    @admin.action(description="تصدير Excel")
    def action_export_excel(
        self,
        request,
        queryset
    ):

        workbook = openpyxl.Workbook()

        sheet = workbook.active

        sheet.title = "Applications"

        headers = [
            "رقم الطلب",
            "المترشح",
            "المنصب",
            "الحالة",
            "العلامة",
            "الترتيب",
        ]

        sheet.append(headers)

        for application in queryset:

            ranking = "—"

            if application.evaluation_score is not None:

                higher_scores = (
                    Application.objects.filter(
                        poste=application.poste,
                        evaluation_score__gt=
                            application.evaluation_score,
                    ).count()
                )

                ranking = higher_scores + 1

            candidate_name = ""

            if application.candidate:

                candidate_name = (
                    application.candidate.full_name
                )

            sheet.append([
                application.application_number,
                candidate_name,
                str(application.poste),
                application.get_status_display(),
                application.evaluation_score or "",
                ranking,
            ])

        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        response[
            "Content-Disposition"
        ] = (
            'attachment; filename="applications.xlsx"'
        )

        workbook.save(response)

        return response

    @admin.action(description="تصدير PDF للمقبولين")
    def action_export_accepted_pdf(
        self,
        request,
        queryset
    ):

        if queryset.count() > MAX_EXPORT_ROWS:

            self.message_user(
                request,
                (
                    f"لا يمكن تصدير أكثر من "
                    f"{MAX_EXPORT_ROWS} طلب دفعة واحدة."
                ),
                level=messages.ERROR,
            )

            return

        accepted = queryset.filter(
            status=Application.Status.FINAL_ACCEPTED
        )

        response = HttpResponse(
            content_type="application/pdf"
        )

        response[
            "Content-Disposition"
        ] = (
            'attachment; filename="accepted_candidates.pdf"'
        )

        pdfmetrics.registerFont(
            UnicodeCIDFont('HYSMyeongJo-Medium')
        )

        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )

        styles = getSampleStyleSheet()

        elements = []

        title = Paragraph(
            "قائمة المترشحين المقبولين نهائيًا",
            styles["Title"]
        )

        elements.append(title)

        elements.append(Spacer(1, 20))

        data = [[
            "الترتيب",
            "العلامة",
            "المنصب",
            "المترشح",
            "رقم الطلب",
        ]]

        ranked = []

        for application in accepted:

            rank = "—"

            if application.evaluation_score is not None:

                higher_scores = (
                    Application.objects.filter(
                        poste=application.poste,
                        evaluation_score__gt=
                            application.evaluation_score,
                    ).count()
                )

                rank = higher_scores + 1

            ranked.append([
                rank,
                application.evaluation_score or "",
                str(application.poste),
                (
                    application.candidate.full_name
                    if application.candidate
                    else ""
                ),
                application.application_number,
            ])

        data.extend(ranked)

        table = Table(data)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

            ('GRID', (0, 0), (-1, -1), 1, colors.grey),

            ('FONTNAME', (0, 0), (-1, -1), 'HYSMyeongJo-Medium'),

            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),

            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),

            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ]))

        elements.append(table)

        doc.build(elements)

        return response
    
    def get_readonly_fields(
        self,
        request,
        obj=None
    ):

        readonly = list(super().get_readonly_fields(
            request,
            obj
        ))

        if not obj:
            return readonly

        if obj.is_finalized():

            protected_fields = [

                field.name

                for field in obj._meta.fields

                if field.name not in [
                    "admin_notes",
                ]
            ]

            readonly.extend(protected_fields)

        return readonly
    
    def get_actions(
        self,
        request
    ):

        actions = super().get_actions(request)

        protected_actions = [

            "action_accept_final",
            "action_preselect",
            "action_mark_under_review",
            "action_mark_incomplete",
            "action_request_completion",
        ]

        if not request.user.has_perm("applications.can_finalize_applications"):
            for action in protected_actions:
                actions.pop(action, None)

        return actions

    def has_add_permission(
        self,
        request,
        obj=None
    ):
        
        if obj and obj.is_finalized():
            return False

        return super().has_add_permission(
            request
        )

    def has_change_permission(
        self,
        request,
        obj=None
    ):

        if obj and obj.is_finalized():
            return False

        return super().has_change_permission(
            request,
            obj
        )
    
    def has_delete_permission(
        self,
        request,
        obj=None
    ):

        if obj and obj.is_finalized():
            return False

        return super().has_delete_permission(
            request,
            obj
        )
    
    def get_queryset(
        self,
        request
    ):

        qs = super().get_queryset(request)

        return qs.select_related(
            "candidate",
            "poste",
        ).prefetch_related(
            "completion_requests",
            "evaluation_notes",
        )
    
    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        if not change:

            return super().save_model(
                request,
                obj,
                form,
                change
            )

        previous_obj = Application.objects.get(
            pk=obj.pk
        )

        previous_status = previous_obj.status

        new_status = obj.status

        status_changed = (
            previous_status != new_status
        )

        # نرجع الحالة القديمة مؤقتًا
        # حتى transition يكتشف التغيير
        if status_changed:

            obj.status = previous_status

            super().save_model(
                request,
                obj,
                form,
                change
            )

            ApplicationWorkflowService.transition(
                application=obj,
                new_status=new_status,
                changed_by=request.user,
                note="تم تحديث حالة الطلب إداريًا.",
                visible_to_candidate=True,
            )

        else:

            super().save_model(
                request,
                obj,
                form,
                change
            )