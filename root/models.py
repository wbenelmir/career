from django.db import models
from django.utils.text import slugify


class LegalReferenceType(models.TextChoices):
    GENERAL = "general", "نصوص عامة"
    RECRUITMENT = "recruitment", "الترشح والتوظيف"
    SENIOR_POSITIONS = "senior_positions", "الوظائف والمناصب العليا"
    DOCUMENTS = "documents", "الوثائق والملفات"
    DATA_PROTECTION = "data_protection", "حماية المعطيات"
    INTERVIEWS = "interviews", "المقابلات والإجراءات"

class LegalReference(models.Model):
    title = models.CharField(max_length=255, verbose_name="العنوان")
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="رقم المرجع")
    published_date = models.DateField(blank=True, null=True, verbose_name="تاريخ النشر")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    document_url = models.URLField(blank=True, null=True, verbose_name="رابط الوثيقة")
    reference_type = models.CharField(
        max_length=50,
        choices=LegalReferenceType.choices,
        default=LegalReferenceType.GENERAL,
        verbose_name="نوع المرجع"
    )

    is_active = models.BooleanField(default=True, verbose_name="نشط")
    display_order = models.PositiveIntegerField(default=0, verbose_name="ترتيب الظهور")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "مرجع قانوني"
        verbose_name_plural = "المراجع القانونية"
        ordering = ["display_order", "-published_date", "title"]

    def __str__(self):
        if self.reference_number:
            return f"{self.title} ({self.reference_number})"
        return self.title


class Poste(models.Model):

    class PosteType(models.TextChoices):
        TRANSFER = "transfer", "وظائف عليا"
        DETACHMENT = "detachment", "مناصب عليا"
        HEAD_OFFICE = "head_office", "رتب"

    title = models.CharField(max_length=255, verbose_name="عنوان المنصب")
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="المعرّف النصي"
    )
    direction = models.CharField(max_length=255, verbose_name="المديرية / الهيكل")
    sub_direction = models.CharField(max_length=255, verbose_name="المديرية الفرعية / الهيكل", blank=True, null=True)
    positions_count = models.PositiveIntegerField(
        default=1,
        verbose_name="عدد المناصب"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف"
    )

    poste_type = models.CharField(
        max_length=20,
        choices=PosteType.choices,
        default=PosteType.HEAD_OFFICE,
        verbose_name="نوع المنصب"
    )

    legal_reference = models.ForeignKey(
        LegalReference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="postes",
        verbose_name="المرجع القانوني"
    )

    is_open = models.BooleanField(default=True, verbose_name="مفتوح للترشح")
    publish_date = models.DateField(verbose_name="تاريخ النشر")
    deadline = models.DateField(
        blank=True,
        null=True,
        verbose_name="آخر أجل للترشح"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "منصب / وظيفة"
        verbose_name_plural = "المناصب والوظائف"
        ordering = ["-publish_date", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.direction}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=False)

            if not base_slug:
                base_slug = "poste"

            slug = base_slug
            counter = 1

            while Poste.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

