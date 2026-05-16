from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Application


class ApplicationWorkflowService:

    @staticmethod
    def transition(
        application,
        new_status,
        changed_by=None,
        note=None,
        visible_to_candidate=True,
    ):

        application.set_status(
            new_status=new_status,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=visible_to_candidate,
        )

        return application

    @staticmethod
    def submit_application(application):

        if not application.is_ready_for_submission():
            raise ValidationError(
                "الطلب غير جاهز للإرسال."
            )

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.SUBMITTED,
        )

    @staticmethod
    def mark_under_review(application, user=None):

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.UNDER_REVIEW,
            changed_by=user,
        )

    @staticmethod
    def mark_incomplete(application, user=None):

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.INCOMPLETE,
            changed_by=user,
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
            visible_to_candidate=True,
        )

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
            visible_to_candidate=True,
        )

    @staticmethod
    def reject_preliminary(
        application,
        reason,
        user=None,
    ):

        application.rejection_reason = reason

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.PRELIMINARY_REJECTED,
            changed_by=user,
            visible_to_candidate=True,
        )

    @staticmethod
    def reject_final(
        application,
        reason,
        user=None,
    ):

        application.rejection_reason = reason

        return ApplicationWorkflowService.transition(
            application,
            Application.Status.FINAL_REJECTED,
            changed_by=user,
            visible_to_candidate=True,
        )