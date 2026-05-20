# tracking/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from applications.models import Application

class ApplicationTracking(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='tracking_entries',
        verbose_name="الطلب",
    )

    status = models.CharField(
        max_length=30,
        choices=Application.Status.choices,
        verbose_name="الحالة",
    )

    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظة",
    )

    is_visible_to_candidate = models.BooleanField(
        default=True,
        verbose_name="ظاهر للمترشح",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application_tracking_entries',
        verbose_name="تم التغيير بواسطة",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        ordering = ['created_at']
        verbose_name = "سجل تتبع"
        verbose_name_plural = "سجلات التتبع"
        indexes = [
            models.Index(fields=['application', 'created_at']),
            models.Index(fields=['status']),
        ]

    @property
    def status_meta(self):

        return self.application.STATUS_META.get(
            self.status,
            {
                "icon": "bi-info-circle",
                "color": "secondary",
                "message": "تم تحديث حالة الطلب.",
            }
        )


    @property
    def status_icon(self):

        return self.status_meta["icon"]


    @property
    def status_color(self):

        return self.status_meta["color"]

    @property
    def timeline_message(self):

        base_message = self.status_meta["message"]

        if self.note:

            return (
                f"{base_message}"
            )

        return base_message

    def __str__(self):
        return f"{self.application.application_number} - {self.get_status_display()}"

    def clean(self):
        super().clean()

        if self.application_id and self.status:
            valid_statuses = {choice[0] for choice in Application.Status.choices}
            if self.status not in valid_statuses:
                raise ValidationError({
                    'status': "الحالة المحددة غير صالحة."
                })

class InterviewSchedule(models.Model):
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='interview_schedule',
        verbose_name="الطلب",
    )

    interview_date = models.DateField(verbose_name="تاريخ المقابلة")
    interview_time = models.TimeField(verbose_name="وقت المقابلة")
    location = models.CharField(max_length=255, verbose_name="مكان المقابلة")
    note = models.TextField(blank=True, null=True, verbose_name="ملاحظة")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_interviews',
        verbose_name="أُنشئت بواسطة",
    )

    summons_file = models.FileField(
        upload_to="interview_summons/",
        null=True,
        blank=True,
        verbose_name="ملف الاستدعاء",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        ordering = ['-interview_date', '-interview_time']
        verbose_name = "برمجة مقابلة"
        verbose_name_plural = "برمجة المقابلات"

    def __str__(self):
        return f"{self.application.application_number} Interview"

    def clean(self):
        super().clean()

        if not self.application_id:
            return

        allowed_statuses = {
            Application.Status.PRESELECTED,
            Application.Status.INTERVIEW_SCHEDULED,
        }

        if self.application.status not in allowed_statuses:
            raise ValidationError({
                'application': (
                    "لا يمكن برمجة مقابلة لهذا الطلب في حالته الحالية. "
                    "يجب أن يكون الطلب مقبولًا أوليًا أو تمت برمجة مقابلته مسبقًا."
                )
            })

        interview_datetime = None
        if self.interview_date and self.interview_time:
            interview_datetime = timezone.datetime.combine(
                self.interview_date,
                self.interview_time
            )
            interview_datetime = timezone.make_aware(
                interview_datetime,
                timezone.get_current_timezone()
            )

        if interview_datetime and interview_datetime < timezone.now():
            raise ValidationError({
                'interview_date': "لا يمكن برمجة مقابلة بتاريخ ووقت في الماضي."
            })
        
    def save(self, *args, **kwargs):

        from applications.services import (
            ApplicationWorkflowService
        )

        is_new = self.pk is None

        super().save(*args, **kwargs)

        application = self.application

        if (
            is_new
            and application.status
            == Application.Status.PRESELECTED
        ):

            ApplicationWorkflowService.schedule_interview(
                application=application,
                user=self.created_by,
            )

            