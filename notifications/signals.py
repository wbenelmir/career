from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from applications.models import Application
from .services import NotificationService


@receiver(pre_save, sender=Application)
def store_previous_application_status(sender, instance, **kwargs):
    """
    حفظ الحالة السابقة قبل التحديث،
    حتى نتحقق لاحقًا هل تغيّرت فعلًا أم لا.
    """
    instance._previous_status = None

    if instance.pk:
        try:
            previous = Application.objects.only("status").get(pk=instance.pk)
            instance._previous_status = previous.status
        except Application.DoesNotExist:
            instance._previous_status = None


@receiver(post_save, sender=Application)
def send_application_notifications(sender, instance, created, **kwargs):
    """
    قواعد الإرسال:
    1) عند الإنشاء:
       - إذا كان الطلب أُنشئ مباشرة بحالة SUBMITTED نرسل:
         - تأكيد للمترشح
         - إشعار للإدارة

    2) عند التحديث:
       - إذا تغيّرت الحالة نرسل تحديث حالة
       - وإذا أصبحت interview_scheduled نرسل أيضًا استدعاء المقابلة
    """

    current_status = getattr(instance, "status", None)
    previous_status = getattr(instance, "_previous_status", None)

    # عند الإنشاء
    if created:
        if current_status == Application.Status.SUBMITTED:
            NotificationService.send_application_submitted(instance)
            NotificationService.send_admin_new_application(instance)
        return

    # عند التحديث: فقط إذا تغيّرت الحالة
    if previous_status != current_status:

        NotificationService.send_application_status_update(instance)

        if current_status == Application.Status.INTERVIEW_SCHEDULED:
            NotificationService.send_interview_scheduled(instance)