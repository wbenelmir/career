# applications/services.py

from django.core.exceptions import ValidationError
from .models import Application


class ApplicationService:
    @staticmethod
    def submit_application(application, changed_by=None, note="تم إرسال الطلب بنجاح."):
        if application.status != application.Status.DRAFT:
            raise ValidationError("لا يمكن إرسال طلب ليس في حالة مسودة.")

        # Check if the candidate already has an active application before allowing submission
        if ApplicationService.check_candidate_has_active_application(application.candidate):
            raise ValidationError("لديك طلب نشط بالفعل.")
    
        return application.set_status(
            application.Status.SUBMITTED,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=True,
        )

    @staticmethod
    def mark_under_review(application, changed_by=None, note="تم تحويل الطلب إلى قيد الدراسة."):
        return application.set_status(
            application.Status.UNDER_REVIEW,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=False,
        )

    @staticmethod
    def mark_incomplete(application, changed_by=None, note="الملف ناقص ويحتاج إلى استكمال."):
        return application.set_status(
            application.Status.INCOMPLETE,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=True,
        )

    @staticmethod
    def preselect(application, changed_by=None, note="تم قبول الطلب أوليًا."):
        return application.set_status(
            application.Status.PRESELECTED,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=True,
        )

    @staticmethod
    def reject_preliminary(application, rejection_reason, changed_by=None, note="تم رفض الطلب أوليًا."):
        application.rejection_reason = rejection_reason
        return application.set_status(
            application.Status.PRELIMINARY_REJECTED,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=True,
        )

    @staticmethod
    def accept_final(application, changed_by=None, note="تم قبول الطلب نهائيًا."):
        return application.set_status(
            application.Status.FINAL_ACCEPTED,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=True,
        )

    @staticmethod
    def reject_final(application, rejection_reason, changed_by=None, note="تم رفض الطلب نهائيًا."):
        application.rejection_reason = rejection_reason
        return application.set_status(
            application.Status.FINAL_REJECTED,
            changed_by=changed_by,
            note=note,
            visible_to_candidate=True,
        )
    @staticmethod
    def check_candidate_has_active_application(candidate):
        return Application.objects.filter(
            candidate=candidate,
            status__in=[
                Application.Status.SUBMITTED,
                Application.Status.UNDER_REVIEW,
                Application.Status.PRESELECTED,
                Application.Status.INTERVIEW_SCHEDULED,
                Application.Status.INTERVIEW_COMPLETED,
            ]
        ).exists()