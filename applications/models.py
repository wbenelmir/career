# applications/models.py

from turtle import circle

from django.db import models, transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from django.conf import settings

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
        return True
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

        SUBMITTED = 'submitted', 'تم استلام الطلب'

        UNDER_REVIEW = 'under_review', 'قيد دراسة الملف'

        INCOMPLETE = 'incomplete', 'الملف بحاجة إلى استكمال'

        PRESELECTED = (
            'preselected',
            'تم قبول ملفكم لاجتياز مرحلة المقابلة'
        )

        PRELIMINARY_REJECTED = (
            'preliminary_rejected',
            'لم يتم قبول ملفكم ضمن نتائج الانتقاء الأولي'
        )

        INTERVIEW_SCHEDULED = (
            'interview_scheduled',
            'تم تحديد موعد المقابلة'
        )

        INTERVIEW_COMPLETED = (
            'interview_completed',
            'تم إجراء المقابلة'
        )

        NO_SHOW = (
            'no_show',
            'تم إقصاء الملف بسبب الغياب عن المقابلة'
        )

        FINAL_ACCEPTED = (
            'final_accepted',
            'تم إدراجكم ضمن القائمة النهائية للناجحين'
        )

        FINAL_REJECTED = (
            'final_rejected',
            'لم يتم اختيار ملفكم ضمن القائمة النهائية'
        )

        WAITING_LIST = (
            'waiting_list',
            'تم إدراج ملفكم ضمن قائمة الاحتياط'
        )

    poste = models.ForeignKey('root.Poste', on_delete=models.PROTECT, related_name='applications', verbose_name="المنصب")
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='applications', verbose_name="المترشح")

    application_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="رقم الطلب")
    tracking_code = models.CharField(max_length=100, unique=True, blank=True, verbose_name="رمز التتبع")

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True, verbose_name="الحالة")

    is_eligible = models.BooleanField(default=True, verbose_name="مؤهل مبدئيًا")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="سبب الرفض")
    admin_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الإدارة")

    motivation_text = models.TextField(verbose_name="Motivation Letter", blank=True)

    evaluation_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="علامة التقييم",
    )

    evaluation_comment = models.TextField(
        blank=True,
        verbose_name="تعليق التقييم",
    )

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

        permissions = [

            (
                "can_review_applications",
                "Can review applications",
            ),

            (
                "can_score_applications",
                "Can score applications",
            ),

            (
                "can_manage_interviews",
                "Can manage interviews",
            ),

            (
                "can_finalize_applications",
                "Can finalize applications",
            ),
        ]

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

    FINAL_STATUSES = [
        Status.FINAL_ACCEPTED,
        Status.FINAL_REJECTED,
    ]

    TRANSITIONS = {

        Status.DRAFT: [
            Status.SUBMITTED,
        ],

        Status.SUBMITTED: [
            Status.UNDER_REVIEW,
            Status.INCOMPLETE,
            Status.PRELIMINARY_REJECTED,
        ],

        Status.INCOMPLETE: [
            Status.SUBMITTED,
            Status.PRELIMINARY_REJECTED,
        ],

        Status.UNDER_REVIEW: [
            Status.PRESELECTED,
            Status.PRELIMINARY_REJECTED,
        ],

        Status.PRESELECTED: [
            Status.INTERVIEW_SCHEDULED,
            Status.FINAL_ACCEPTED,
            Status.WAITING_LIST,
            Status.FINAL_REJECTED,
        ],

        Status.INTERVIEW_SCHEDULED: [
            Status.INTERVIEW_COMPLETED,
            Status.NO_SHOW,
        ],

        Status.INTERVIEW_COMPLETED: [
            Status.FINAL_ACCEPTED,
            Status.FINAL_REJECTED,
            Status.WAITING_LIST,
        ],

        Status.NO_SHOW: [
            Status.FINAL_REJECTED,
        ],

        Status.WAITING_LIST: [
            Status.FINAL_ACCEPTED,
            Status.FINAL_REJECTED,
        ],
    }


    def is_finalized(self):
        return self.status in self.FINAL_STATUSES


    def is_ready_for_submission(self):

        return (
            bool(self.motivation_text)
            and self.has_all_required_documents()
            and self.is_eligible
        )


    def is_ready_for_review(self):

        return (
            self.status == self.Status.SUBMITTED
            and self.is_ready_for_submission()
        )


    def can_be_preselected(self):

        return (
            self.status == self.Status.UNDER_REVIEW
            and self.is_ready_for_submission()
        )


    def can_transition_to(self, new_status):

        if self.is_finalized():
            return False

        allowed = self.TRANSITIONS.get(
            self.status,
            []
        )

        return new_status in allowed

    def set_status(
        self,
        new_status,
        changed_by=None,
        note=None,
        visible_to_candidate=True,
    ):

        if new_status not in dict(self.Status.choices):

            raise ValidationError(
                "الحالة المحددة غير صالحة."
            )

        old_status = self.status

        if old_status == new_status:
            return

        self.status = new_status

        now = timezone.now()

        if new_status == self.Status.SUBMITTED:

            if not self.submitted_at:
                self.submitted_at = now

        elif new_status == self.Status.UNDER_REVIEW:

            self.reviewed_at = now

        elif new_status == self.Status.PRESELECTED:

            self.preselected_at = now

        elif new_status == self.Status.INTERVIEW_SCHEDULED:

            self.interview_scheduled_at = now

        elif new_status == self.Status.INTERVIEW_COMPLETED:

            self.interview_completed_at = now

        elif new_status in [
            self.Status.FINAL_ACCEPTED,
            self.Status.FINAL_REJECTED,
        ]:

            self.final_decision_at = now

        self.save()

    STATUS_META = {

        "submitted": {
            "icon": "bi-send-check",
            "color": "info",
            "message": (
                    "تم استلام طلبكم بنجاح.\n"
                    "المرحلة التالية: دراسة ملف الترشح "
                    "من طرف اللجنة المختصة."
                ),
        },

        "under_review": {
            "icon": "bi-search",
            "color": "primary",
            "message": (
                "ملف الترشح قيد الدراسة حاليًا "
                "من طرف اللجنة المختصة."
            ),
        },

        "incomplete": {
            "icon": "bi-exclamation-triangle",
            "color": "warning",
            "message": (
                "يتطلب ملف الترشح استكمال بعض "
                "الوثائق أو المعلومات.\n"
                "يرجى الاطلاع على الملاحظات "
                "المرفقة ومتابعة استكمال الطلب."
            ),
        },

        "preselected": {
            "icon": "bi-check-circle",
            "color": "success",
            "message": (
                "تم قبول ملفكم لاجتياز مرحلة المقابلة.\n"
                "سيتم تحديد موعد المقابلة "
                "وإشعاركم بذلك عبر هذا الفضاء."
            ),
        },

        "preliminary_rejected": {
            "icon": "bi-x-circle",
            "color": "danger",
            "message": (
                "بعد استكمال دراسة ملفات الترشح، "
                "تعذر قبول ملفكم "
                "ضمن هذه المرحلة من عملية الانتقاء."
            ),
        },

        "interview_scheduled": {
            "icon": "bi-calendar-event",
            "color": "info",
            "message": (
                "تم تحديد موعد لإجراء المقابلة.\n"
                "يرجى الاطلاع على تفاصيل الموعد "
                "والالتزام بالحضور في التاريخ المحدد."
            ),
        },

        "interview_completed": {
            "icon": "bi-check2-square",
            "color": "primary",
            "message": (
                "تم إجراء المقابلة بنجاح.\n"
                "ويجري حاليًا استكمال دراسة الملف "
                "في انتظار الإعلان عن النتائج النهائية."
            ),
        },

        "no_show": {
            "icon": "bi-person-x",
            "color": "warning",
            "message": (
                "تم إقصاء ملف الترشح "
                "بسبب عدم الحضور للمقابلة "
                "في الموعد المحدد."
            ),
        },

        "final_accepted": {
            "icon": "bi-patch-check",
            "color": "success",
            "message": (
                "نهنئكم، لقد تم إدراجكم "
                "ضمن قائمة المترشحين الناجحين.\n"
                "يرجى متابعة الفضاء الخاص بكم، "
                "وسيتم التواصل معكم "
                "لاستكمال الإجراءات الإدارية اللازمة."
            ),
        },

        "final_rejected": {
            "icon": "bi-slash-circle",
            "color": "danger",
            "message": (
                "نشكركم على اهتمامكم بالمشاركة، "
                "غير أنه لم يتم اختيار ملفكم "
                "ضمن القائمة النهائية "
                "للمترشحين الناجحين."
            ),
        },

        "waiting_list": {
            "icon": "bi-hourglass-split",
            "color": "secondary",
            "message": (
                "تم إدراج ملفكم ضمن قائمة الاحتياط.\n"
                "وسيتم التواصل معكم "
                "عند توفر مستجدات."
            ),
        },
    }

    @property
    def status_meta(self):

        return self.STATUS_META.get(
            self.status,
            {
                "icon": "bi-info-circle",
                "color": "secondary",
                "message": (
                    "يمكنكم متابعة تطور معالجة "
                    "الطلب من خلال هذا الفضاء."
                ),
            }
        )


    @property
    def status_icon(self):

        return self.status_meta["icon"]


    @property
    def status_color(self):

        return self.status_meta["color"]


    @property
    def status_message(self):

        return self.status_meta["message"]

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
    
class CompletionRequest(models.Model):

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="completion_requests",
        verbose_name="الطلب",
    )

    message = models.TextField(
        verbose_name="الوثائق أو المعلومات المطلوبة",
    )

    deadline = models.DateTimeField(
        verbose_name="آخر أجل للاستكمال",
    )

    is_resolved = models.BooleanField(
        default=False,
        verbose_name="تم الاستكمال",
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ الاستكمال",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تم الإنشاء بواسطة",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "طلب استكمال"

        verbose_name_plural = "طلبات الاستكمال"

    def __str__(self):

        return (
            f"طلب استكمال - "
            f"{self.application.application_number}"
        )

class EvaluationNote(models.Model):

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="evaluation_notes",
        verbose_name="الطلب",
    )

    note = models.TextField(
        verbose_name="ملاحظة التقييم",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تمت بواسطة",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "ملاحظة تقييم"

        verbose_name_plural = "ملاحظات التقييم"

    def __str__(self):

        return (
            f"Evaluation Note - "
            f"{self.application.application_number}"
        )