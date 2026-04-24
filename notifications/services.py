from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from applications.utils import generate_qr_base64
from .models import NotificationLog

class NotificationService:
    @staticmethod
    def send_email(
        *,
        to_email,
        subject,
        html_template_name,
        context=None,
        from_email=None,
        fail_silently=False,
        application=None,
    ):
        """
        Send an HTML email with automatic plain-text fallback
        and store the result in NotificationLog.
        """
        context = context or {}
        from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None)

        try:
            html_body = render_to_string(html_template_name, context).strip()
            text_body = strip_tags(html_body).strip()

            if not html_body:
                raise ValueError("Rendered HTML email body is empty.")

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=from_email,
                to=[to_email],
            )
            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=fail_silently)

            NotificationLog.objects.create(
                application=application,
                to_email=to_email,
                subject=subject,
                template_name=html_template_name,
                status="SENT",
            )

            return True

        except Exception as exc:
            NotificationLog.objects.create(
                application=application,
                to_email=to_email,
                subject=subject,
                template_name=html_template_name,
                status="FAILED",
                error=str(exc),
            )

            if not fail_silently:
                raise

            return False

    @staticmethod
    def _build_tracking_url_from_base(base_url, tracking_code):
        if not base_url:
            return None

        base_url = base_url.rstrip("/")
        return f"{base_url}/tracking/result/{tracking_code}/"

    @staticmethod
    def send_application_submitted(application, request_base_url=None):
        subject = f"Application submission confirmation #{application.application_number}"

        tracking_url = NotificationService._build_tracking_url_from_base(
            request_base_url,
            application.tracking_code,
        )
        qr_code_base64 = generate_qr_base64(tracking_url) if tracking_url else None

        context = {
            "application": application,
            "candidate": application.candidate,
            "poste": application.poste,
            "tracking_code": application.tracking_code,
            "tracking_url": tracking_url,
            "qr_code_base64": qr_code_base64,
        }

        return NotificationService.send_email(
            application=application,
            to_email=application.candidate.email,
            subject=subject,
            html_template_name="emails/application_submitted.html",
            context=context,
            fail_silently=True,
        )

    @staticmethod
    def send_application_status_update(application):
        subject = f"Update regarding your application #{application.application_number}"

        context = {
            "application": application,
            "candidate": application.candidate,
            "poste": application.poste,
            "status_display": application.get_status_display(),
            "tracking_code": application.tracking_code,
            "rejection_reason": application.rejection_reason,
            "admin_notes": application.admin_notes,
        }

        return NotificationService.send_email(
            application=application,
            to_email=application.candidate.email,
            subject=subject,
            html_template_name="emails/application_status_update.html",
            context=context,
            fail_silently=True,
        )

    @staticmethod
    def send_interview_scheduled(application):
        subject = f"Interview invitation - application #{application.application_number}"

        interview_schedule = getattr(application, "interview_schedule", None)

        context = {
            "application": application,
            "candidate": application.candidate,
            "poste": application.poste,
            "tracking_code": application.tracking_code,
            "interview_schedule": interview_schedule,
        }

        return NotificationService.send_email(
            application=application,
            to_email=application.candidate.email,
            subject=subject,
            html_template_name="emails/interview_scheduled.html",
            context=context,
            fail_silently=True,
        )

    @staticmethod
    def send_admin_new_application(application, admin_email=None):
        admin_email = admin_email or getattr(settings, "DEFAULT_ADMIN_EMAIL", None)
        if not admin_email:
            return False

        subject = f"New application: {application.application_number}"

        context = {
            "application": application,
            "candidate": application.candidate,
            "poste": application.poste,
            "tracking_code": application.tracking_code,
        }

        return NotificationService.send_email(
            application=application,
            to_email=admin_email,
            subject=subject,
            html_template_name="emails/admin_new_application.html",
            context=context,
            fail_silently=True,
        )