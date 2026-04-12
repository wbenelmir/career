# applications/services.py

from django.core.exceptions import ValidationError


class ApplicationService:
    @staticmethod
    def submit_application(application, changed_by=None, note="تم إرسال الطلب بنجاح."):
        if application.status != application.Status.DRAFT:
            raise ValidationError("لا يمكن إرسال طلب ليس في حالة مسودة.")

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