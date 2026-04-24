from celery import shared_task

@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_application_submitted_email_task(application_id, request_base_url=None):
    from applications.models import Application
    from .services import NotificationService

    application = (
        Application.objects
        .select_related("candidate", "poste")
        .filter(id=application_id)
        .first()
    )
    if not application:
        return False

    return NotificationService.send_application_submitted(
        application,
        request_base_url=request_base_url,
    )


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_application_status_update_email_task(application_id):
    from applications.models import Application
    from .services import NotificationService

    application = (
        Application.objects
        .select_related("candidate", "poste")
        .filter(id=application_id)
        .first()
    )
    if not application:
        return False

    return NotificationService.send_application_status_update(application)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_interview_scheduled_email_task(application_id):
    from applications.models import Application
    from .services import NotificationService

    application = (
        Application.objects
        .select_related("candidate", "poste")
        .filter(id=application_id)
        .first()
    )
    if not application:
        return False

    return NotificationService.send_interview_scheduled(application)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_admin_new_application_email_task(application_id):
    from applications.models import Application
    from .services import NotificationService

    application = (
        Application.objects
        .select_related("candidate", "poste")
        .filter(id=application_id)
        .first()
    )
    if not application:
        return False

    return NotificationService.send_admin_new_application(application)