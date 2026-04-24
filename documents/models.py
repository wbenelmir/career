# documents/models.py
import os
import re
from django.db import models

def _slugify_for_filename(value):
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-z0-9\u0600-\u06FF_-]", "", value)
    return value or "document"

def application_document_upload_to(instance, filename):
    extension = os.path.splitext(filename)[1].lower()

    poste_slug = getattr(instance.application.poste, "slug", None) or f"poste_{instance.application.poste_id}"
    tracking_code = getattr(instance.application, "tracking_code", None) or f"app_{instance.application_id}"
    doc_label = _slugify_for_filename(instance.document_type.name)

    final_name = f"{doc_label}_{tracking_code}{extension}"

    return os.path.join(
        "applications",
        "documents",
        poste_slug,
        tracking_code,
        final_name
    )

class DocumentType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

class PosteDocumentRequirement(models.Model):
    poste = models.ForeignKey(
        'root.Poste',
        on_delete=models.CASCADE,
        related_name='document_requirements',
        verbose_name="المنصب",
    )

    document_type = models.ForeignKey(
        'documents.DocumentType',
        on_delete=models.CASCADE,
        related_name='poste_requirements',
        verbose_name="نوع الوثيقة",
    )

    is_required = models.BooleanField(
        default=True,
        verbose_name="وثيقة مطلوبة"
    )

    allowed_extensions = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="الامتدادات المسموحة",
        help_text="مثال: jpg,jpeg,png"
    )

    max_file_size_mb = models.PositiveIntegerField(
        default=5,
        verbose_name="الحد الأقصى للحجم (MB)"
    )

    help_text = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="نص مساعد"
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب العرض"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name = "متطلب وثيقة لمنصب"
        verbose_name_plural = "متطلبات الوثائق للمناصب"
        constraints = [
            models.UniqueConstraint(
                fields=['poste', 'document_type'],
                name='unique_poste_document_requirement'
            )
        ]

    def __str__(self):
        return f"{self.poste} - {self.document_type.name}"

    def get_allowed_extensions_list(self):
        if not self.allowed_extensions:
            return []
        return [
            ext.strip().lower().lstrip('.')
            for ext in self.allowed_extensions.split(',')
            if ext.strip()
        ]

class ApplicationDocument(models.Model):
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name='application_documents',
    )

    file = models.FileField(upload_to=application_document_upload_to)
    original_filename = models.CharField(max_length=255, blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['document_type__display_order', '-uploaded_at']
        unique_together = ['application', 'document_type']

    def __str__(self):
        return f"{self.application.application_number} - {self.document_type.name}"

    def save(self, *args, **kwargs):
        old_file = None

        if self.pk:
            old_instance = ApplicationDocument.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.file and old_instance.file != self.file:
                old_file = old_instance.file

        super().save(*args, **kwargs)

        if old_file and old_file.name and old_file.storage.exists(old_file.name):
            old_file.storage.delete(old_file.name)