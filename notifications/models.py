from django.db import models

class NotificationLog(models.Model):
    class Status(models.TextChoices):
        SENT = "SENT", "تم الإرسال"
        FAILED = "FAILED", "فشل الإرسال"

    to_email = models.EmailField(verbose_name="البريد المرسل إليه")
    subject = models.CharField(max_length=200, verbose_name="الموضوع")
    template_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="القالب"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        verbose_name="الحالة"
    )
    error = models.TextField(
        null=True,
        blank=True,
        verbose_name="تفاصيل الخطأ"
    )

    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
        verbose_name="الطلب المرتبط",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "سجل إشعار"
        verbose_name_plural = "سجلات الإشعارات"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.to_email} - {self.subject} - {self.status}"