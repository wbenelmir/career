# applications/models.py

from django.db import models, transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError


class CandidateProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'ذكر'),
        ('female', 'أنثى'),
    ]

    first_name = models.CharField(max_length=150, verbose_name="الاسم")
    last_name = models.CharField(max_length=150, verbose_name="اللقب")
    date_of_birth = models.DateField(verbose_name="تاريخ الميلاد")
    place_of_birth = models.CharField(max_length=255, blank=True, null=True, verbose_name="مكان الميلاد")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="الجنس")

    national_id_number = models.CharField(max_length=30, verbose_name="رقم التعريف الوطني")
    email = models.EmailField(verbose_name="البريد الإلكتروني")
    phone_number = models.CharField(max_length=30, verbose_name="رقم الهاتف")

    address = models.TextField(blank=True, null=True, verbose_name="العنوان")
    wilaya = models.ForeignKey('locations.Wilaya', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidate_profiles', verbose_name="الولاية")
    commune = models.ForeignKey('locations.Commune', on_delete=models.SET_NULL, null=True, blank=True, related_name='candidate_profiles', verbose_name="البلدية")

    current_administration = models.CharField(max_length=255, verbose_name="الإدارة الحالية")
    current_position_grade = models.CharField(max_length=255, verbose_name="الرتبة الحالية")
    current_function = models.CharField(max_length=255, blank=True, null=True, verbose_name="الوظيفة الحالية")

    tenure_decision_date = models.DateField(verbose_name="تاريخ قرار الترسيم")

    years_of_seniority = models.PositiveIntegerField(default=0, verbose_name="سنوات الأقدمية")
    years_of_effective_service = models.PositiveIntegerField(default=0, verbose_name="سنوات الخدمة الفعلية")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "ملف مترشح"
        verbose_name_plural = "ملفات المترشحين"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def clean(self):
        super().clean()

        if self.years_of_seniority < 0:
            raise ValidationError({'years_of_seniority': "سنوات الأقدمية لا يمكن أن تكون سالبة."})

        if self.years_of_effective_service < 0:
            raise ValidationError({'years_of_effective_service': "سنوات الخدمة الفعلية لا يمكن أن تكون سالبة."})

        if self.date_of_birth and self.date_of_birth > timezone.now().date():
            raise ValidationError({'date_of_birth': "تاريخ الميلاد غير صحيح."})

        if self.tenure_decision_date and self.tenure_decision_date > timezone.now().date():
            raise ValidationError({'tenure_decision_date': "تاريخ قرار الترسيم لا يمكن أن يكون في المستقبل."})

        if self.wilaya and self.commune and getattr(self.commune, 'wilaya_id', None) != self.wilaya_id:
            raise ValidationError({'commune': "البلدية المختارة لا تنتمي إلى الولاية المحددة."})

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_eligible_for_head_of_office(self):
        grade = (self.current_position_grade or "").strip().lower()

        principal_keywords = ['متصرف رئيسي', 'متصرف رئيسى', 'administrateur principal']
        administrator_keywords = ['متصرف', 'administrateur']

        is_principal = any(keyword in grade for keyword in principal_keywords)
        is_administrator = any(keyword in grade for keyword in administrator_keywords)

        if is_principal and self.years_of_seniority >= 3:
            return True

        if is_administrator and self.years_of_effective_service >= 5:
            return True

        return False


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'مسودة'
        SUBMITTED = 'submitted', 'مرسل'
        UNDER_REVIEW = 'under_review', 'قيد الدراسة'
        INCOMPLETE = 'incomplete', 'ملف ناقص'
        PRESELECTED = 'preselected', 'مقبول أوليًا'
        PRELIMINARY_REJECTED = 'preliminary_rejected', 'مرفوض أوليًا'
        INTERVIEW_SCHEDULED = 'interview_scheduled', 'تمت برمجة المقابلة'
        INTERVIEW_COMPLETED = 'interview_completed', 'أُجريت المقابلة'
        NO_SHOW = 'no_show', 'لم يحضر المقابلة'
        FINAL_ACCEPTED = 'final_accepted', 'مقبول نهائيًا'
        FINAL_REJECTED = 'final_rejected', 'مرفوض نهائيًا'
        WAITING_LIST = 'waiting_list', 'قائمة الاحتياط'

    poste = models.ForeignKey('root.Poste', on_delete=models.PROTECT, related_name='applications', verbose_name="المنصب")
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='applications', verbose_name="المترشح")

    application_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="رقم الطلب")
    tracking_code = models.CharField(max_length=100, unique=True, blank=True, verbose_name="رمز التتبع")

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True, verbose_name="الحالة")

    is_eligible = models.BooleanField(default=True, verbose_name="مؤهل مبدئيًا")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="سبب الرفض")
    admin_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الإدارة")

    motivation_text = models.TextField(verbose_name="Motivation Letter", blank=True)

    submitted_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    preselected_at = models.DateTimeField(blank=True, null=True)
    interview_scheduled_at = models.DateTimeField(blank=True, null=True)
    interview_completed_at = models.DateTimeField(blank=True, null=True)
    final_decision_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "طلب ترشح"
        verbose_name_plural = "طلبات الترشح"

    def __str__(self):
        return self.application_number or f"Application #{self.pk}"

    @staticmethod
    def generate_tracking_code(length=12):
        while True:
            code = get_random_string(length=length).upper()
            if not Application.objects.filter(tracking_code=code).exists():
                return code

    @staticmethod
    def generate_application_number():
        current_year = timezone.now().year
        prefix = f"RBM-{current_year}"

        for _ in range(10):
            count = Application.objects.filter(created_at__year=current_year).count() + 1
            number = f"{prefix}-{count:04d}"
            if not Application.objects.filter(application_number=number).exists():
                return number

        return f"{prefix}-{get_random_string(6).upper()}"

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = self.generate_tracking_code()

        if not self.application_number:
            self.application_number = self.generate_application_number()

        if self.candidate_id:
            self.is_eligible = self.candidate.is_eligible_for_head_of_office()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.status in [self.Status.PRELIMINARY_REJECTED, self.Status.FINAL_REJECTED] and not self.rejection_reason:
            raise ValidationError({'rejection_reason': "سبب الرفض إلزامي عند رفض الطلب."})

    # ========================
    # POSTES HELPERS
    # ========================

    def get_ordered_choices(self):
        return self.choices.select_related('poste').order_by('priority')

    def get_ordered_postes(self):
        return [choice.poste for choice in self.get_ordered_choices()]

    def get_primary_poste(self):
        first = self.get_ordered_choices().first()
        return first.poste if first else self.poste

    def postes_count(self):
        return self.choices.count()

    def get_postes_display(self):
        return " | ".join([
            f"{c.priority}. {c.poste}"
            for c in self.get_ordered_choices()
        ])

    def motivation_word_count(self):
        return len(self.motivation_text.split()) if self.motivation_text else 0

    # ========================
    # DOCUMENT LOGIC
    # ========================

    def _get_active_requirements_queryset(self):
        return self.poste.document_requirements.filter(is_active=True).select_related('document_type')

    def get_required_document_type_ids(self):
        return set(self._get_active_requirements_queryset().filter(is_required=True).values_list('document_type_id', flat=True))

    def get_uploaded_document_type_ids(self):
        return set(self.documents.values_list('document_type_id', flat=True))

    def has_all_required_documents(self):
        return self.get_required_document_type_ids().issubset(self.get_uploaded_document_type_ids())

    # ========================
    # STATUS LOGIC
    # ========================

    def can_transition_to(self, new_status):
        allowed = {
            self.Status.DRAFT: [self.Status.SUBMITTED],
            self.Status.SUBMITTED: [self.Status.UNDER_REVIEW, self.Status.INCOMPLETE, self.Status.PRELIMINARY_REJECTED, self.Status.PRESELECTED],
        }
        return new_status in allowed.get(self.status, [])

    @transaction.atomic
    def set_status(self, new_status, changed_by=None, note=None, visible_to_candidate=True):
        if new_status == self.status:
            return self

        if not self.can_transition_to(new_status):
            raise ValidationError("Invalid status transition.")

        if new_status == self.Status.SUBMITTED:
            if not self.motivation_text:
                raise ValidationError("Motivation is required before submission.")

            if not self.has_all_required_documents():
                raise ValidationError("Missing required documents.")

        self.status = new_status

        if new_status == self.Status.SUBMITTED:
            self.submitted_at = timezone.now()

        self.full_clean()
        self.save()

        return self


class ApplicationChoice(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="choices", verbose_name="الطلب")
    poste = models.ForeignKey('root.Poste', on_delete=models.PROTECT, verbose_name="المنصب")
    priority = models.PositiveSmallIntegerField(verbose_name="الأولوية")

    class Meta:
        unique_together = ('application', 'priority')
        constraints = [
            models.UniqueConstraint(fields=['application', 'poste'], name='unique_poste_per_application')
        ]
        ordering = ['priority']
        verbose_name = "اختيار منصب"
        verbose_name_plural = "اختيارات المناصب"

    def clean(self):
        existing = self.application.choices.exclude(pk=self.pk)

        if existing.count() >= 3:
            raise ValidationError("يمكن اختيار 3 مناصب كحد أقصى.")

        priorities = list(existing.values_list('priority', flat=True)) + [self.priority]
        if sorted(priorities) != list(range(1, len(priorities) + 1)):
            raise ValidationError("الأولوية يجب أن تكون متسلسلة بدون فجوات.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.priority == 1:
            self.application.poste = self.poste
            self.application.save(update_fields=['poste'])

    def __str__(self):
        return f"{self.application} - {self.poste} (#{self.priority})"