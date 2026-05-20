from django.core.exceptions import ValidationError

from tracking.models import ApplicationTracking

from .models import Application


class ApplicationWorkflowService:

    # =========================
    # TRACKING HELPERS
    # =========================

    @staticmethod
    def create_tracking_entry(
        application,
        status,
        changed_by=None,
        note=None,
        visible_to_candidate=True,
    ):

        latest_entry = (
            application.tracking_entries
            .order_by("-created_at")
            .first()
        )

        # منع التكرار المباشر
        if (
            latest_entry
            and latest_entry.status == status
            and (latest_entry.note or "").strip() == (note or "").strip()
        ):
            return latest_entry

        return ApplicationTracking.objects.create(
            application=application,
            status=status,
            note=note,
            changed_by=changed_by,
            is_visible_to_candidate=visible_to_candidate,
        )

    # =========================
    # MAIN TRANSITION ENGINE
    # =========================

    @staticmethod
    def transition(
        application,
        new_status,
        changed_by=None,
        note=None,
        visible_to_candidate=True,
    ):

        previous_status = application.status

        application.set_status(
            new_status=new_status,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=visible_to_candidate,
        )

        # لا ننشئ tracking إذا لم يحدث تغيير
        if previous_status == new_status:
            return application

        ApplicationWorkflowService.create_tracking_entry(
            application=application,
            status=new_status,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=visible_to_candidate,
        )

        return application

    # =========================
    # PUBLIC SUBMISSION
    # =========================

    @staticmethod
    def submit_application(application):

        if not application.is_ready_for_submission():
            raise ValidationError(
                "الطلب غير جاهز للإرسال."
            )

        note = "تم إرسال طلب الترشح بنجاح."

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.SUBMITTED,
            note=note,
            visible_to_candidate=True,
        )

    # =========================
    # REVIEW STAGES
    # =========================

    @staticmethod
    def mark_under_review(application, user=None):

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.UNDER_REVIEW,
            changed_by=user,
            note="تم تحويل الطلب إلى مرحلة الدراسة.",
        )

    @staticmethod
    def mark_incomplete(
        application,
        user=None,
        note=None,
    ):

        default_note = (
            "تمت ملاحظة نقص أو معلومات تحتاج إلى استكمال."
        )

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.INCOMPLETE,
            changed_by=user,
            note=note or default_note,
            visible_to_candidate=True,
        )

    @staticmethod
    def preselect(application, user=None):

        if not application.can_be_preselected():
            raise ValidationError(
                "الطلب غير جاهز للقبول الأولي."
            )

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.PRESELECTED,
            changed_by=user,
            note="تم قبول الطلب في مرحلة الانتقاء الأولي.",
            visible_to_candidate=True,
        )

    # =========================
    # INTERVIEW
    # =========================

    @staticmethod
    def schedule_interview(
        application,
        user=None,
        note=None,
    ):

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.INTERVIEW_SCHEDULED,
            changed_by=user,
            note=note or "تمت برمجة مقابلة خاصة بهذا الطلب.",
            visible_to_candidate=True,
        )

    @staticmethod
    def complete_interview(
        application,
        user=None,
    ):

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.INTERVIEW_COMPLETED,
            changed_by=user,
            note="تم تسجيل إجراء المقابلة.",
            visible_to_candidate=True,
        )

    @staticmethod
    def mark_no_show(
        application,
        user=None,
    ):

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.NO_SHOW,
            changed_by=user,
            note="تم تسجيل عدم الحضور للمقابلة.",
            visible_to_candidate=True,
        )

    # =========================
    # FINAL DECISIONS
    # =========================

    @staticmethod
    def accept_final(application, user=None):

        if application.evaluation_score is None:

            raise ValidationError(
                "لا يمكن إصدار قرار نهائي دون تقييم."
            )

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.FINAL_ACCEPTED,
            changed_by=user,
            note="صدر القرار النهائي بقبول الطلب.",
            visible_to_candidate=True,
        )

    @staticmethod
    def reject_preliminary(
        application,
        reason,
        user=None,
    ):

        application.rejection_reason = reason
        application.save(update_fields=["rejection_reason"])

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.PRELIMINARY_REJECTED,
            changed_by=user,
            note="تم رفض الطلب في المرحلة الأولية.",
            visible_to_candidate=True,
        )

    @staticmethod
    def reject_final(
        application,
        reason,
        user=None,
    ):

        application.rejection_reason = reason
        application.save(update_fields=["rejection_reason"])

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.FINAL_REJECTED,
            changed_by=user,
            note="صدر القرار النهائي برفض الطلب.",
            visible_to_candidate=True,
        )