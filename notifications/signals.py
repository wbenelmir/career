from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from applications.models import Application
from .services import NotificationService

@receiver(pre_save, sender=Application)
def store_previous_application_status(sender, instance, **kwargs):

    """
    Store the previous status before saving.
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
    Sending rules:
    1) On creation: 
        - If the application is created directly with SUBMITTED status, send:
        - Confirmation to candidate
        - Notification to admin
    2) On update:
        - If the status changed, send status update
        - If the new status is interview_scheduled, also send interview scheduled notification
    """

    current_status = getattr(instance, "status", None)
    previous_status = getattr(instance, "_previous_status", None)

    # in case of creation, we only care if the initial status is SUBMITTED
    if created:
        if current_status == Application.Status.SUBMITTED:
            NotificationService.send_application_submitted(instance)
            NotificationService.send_admin_new_application(instance)
        return

    # in case of update, we check if the status changed
    if previous_status != current_status:

        NotificationService.send_application_status_update(instance)

        if current_status == Application.Status.INTERVIEW_SCHEDULED:
            NotificationService.send_interview_scheduled(instance)