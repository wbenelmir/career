from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from applications.models import Application
from notifications.services import NotificationService


class Command(BaseCommand):
    help = (
        "Send a test email using one of the notification templates "
        "without going through the full application workflow."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--template",
            type=str,
            required=True,
            choices=[
                "submitted",
                "status_update",
                "interview",
                "admin_new",
            ],
            help="Template to test: submitted, status_update, interview, or admin_new.",
        )
        parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Recipient email address.",
        )
        parser.add_argument(
            "--application-id",
            type=int,
            required=False,
            help="Existing Application ID to use for the test.",
        )
        parser.add_argument(
            "--base-url",
            type=str,
            required=False,
            default="http://127.0.0.1:8000",
            help="Base URL used to build tracking links.",
        )

    def handle(self, *args, **options):
        template = options["template"]
        to_email = options["to"]
        application_id = options.get("application_id")
        base_url = options["base_url"]

        if application_id:
            application = (
                Application.objects
                .select_related("candidate", "poste")
                .filter(id=application_id)
                .first()
            )
            if not application:
                raise CommandError(f"Application with ID {application_id} was not found.")
        else:
            application = (
                Application.objects
                .select_related("candidate", "poste")
                .order_by("-id")
                .first()
            )
            if not application:
                raise CommandError(
                    "No Application records were found in the database. "
                    "Create one first or pass --application-id."
                )

        sent = False

        if template == "submitted":
            original_candidate_email = application.candidate.email
            application.candidate.email = to_email
            try:
                sent = NotificationService.send_application_submitted(
                    application,
                    request_base_url=base_url,
                )
            finally:
                application.candidate.email = original_candidate_email

        elif template == "status_update":
            original_candidate_email = application.candidate.email
            application.candidate.email = to_email
            try:
                sent = NotificationService.send_application_status_update(application)
            finally:
                application.candidate.email = original_candidate_email

        elif template == "interview":
            original_candidate_email = application.candidate.email
            application.candidate.email = to_email
            try:
                if not getattr(application, "interview_schedule", None):
                    application.interview_schedule = (
                        f"Test interview schedule - {timezone.localtime().strftime('%Y-%m-%d %H:%M')}"
                    )

                sent = NotificationService.send_interview_scheduled(application)
            finally:
                application.candidate.email = original_candidate_email

        elif template == "admin_new":
            sent = NotificationService.send_admin_new_application(
                application,
                admin_email=to_email,
            )

        if sent:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Test email sent successfully to: {to_email}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Email was not sent. Check NotificationLog and email settings."
                )
            )