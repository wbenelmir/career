from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from captcha.fields import CaptchaField
import re

from root.models import Poste
from .models import CandidateProfile
from locations.models import Commune


# =========================
# Motivation Form (STEP 3)
# =========================

class MotivationForm(forms.Form):
    motivation_text = forms.CharField(
        label="الرسالة التحفيزية",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 8,
            "placeholder": "اكتب رسالة تحفيزية تشرح أسباب ترشحك..."
        }),
    )

    MIN_WORDS = 100
    MAX_WORDS = 500

    def clean_motivation_text(self):
        text = (self.cleaned_data.get("motivation_text") or "").strip()

        # normalize spaces
        text = " ".join(text.split())

        word_count = len(text.split())

        if word_count < self.MIN_WORDS:
            raise forms.ValidationError(
                f"يجب أن تحتوي الرسالة على الأقل على {self.MIN_WORDS} كلمة."
            )

        if word_count > self.MAX_WORDS:
            raise forms.ValidationError(
                f"يجب ألا تتجاوز الرسالة {self.MAX_WORDS} كلمة."
            )

        return text


# =========================
# Application Form (STEP 1)
# =========================

class ApplicationForm(forms.Form):

    poste_1 = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label="المنصب (الأولوية الأولى)",
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
        error_messages={
            "required": "يرجى اختيار المنصب الأساسي (الأولوية الأولى)."
        }
    )

    poste_2 = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="المنصب (الأولوية الثانية - اختياري)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    poste_3 = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="المنصب (الأولوية الثالثة - اختياري)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    declaration_confirmation = forms.BooleanField(
        required=True,
        label="",
        error_messages={
            "required": "يجب الموافقة على التصريح قبل بدء الترشح."
        }
    )

    captcha = CaptchaField(
        label="رمز التحقق",
        error_messages={
            "invalid": "رمز التحقق غير صحيح، يرجى المحاولة مرة أخرى.",
            "required": "يرجى إدخال رمز التحقق.",
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()

        qs = Poste.objects.filter(
            is_open=True
        ).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=today)
        )

        for field in ["poste_1", "poste_2", "poste_3"]:
            self.fields[field].queryset = qs
            self.fields[field].empty_label = "اختر المنصب"

        self.fields["poste_1"].empty_label = "اختر المنصب (إجباري)"

        self.fields["declaration_confirmation"].widget.attrs.update({
            "class": "form-check-input",
            "id": "id_declaration_confirmation",
        })

        self.fields["captcha"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "- - - - -",
            "autocomplete": "off",
            "dir": "ltr",
        })

    # =========================
    # HELPERS
    # =========================

    def get_selected_postes(self):
        return [
            self.cleaned_data.get("poste_1"),
            self.cleaned_data.get("poste_2"),
            self.cleaned_data.get("poste_3"),
        ]

    def get_ordered_postes(self):
        return [p for p in self.get_selected_postes() if p]

    # =========================
    # VALIDATION
    # =========================

    def clean(self):
        cleaned_data = super().clean()

        poste_1 = cleaned_data.get("poste_1")
        poste_2 = cleaned_data.get("poste_2")
        poste_3 = cleaned_data.get("poste_3")

        postes = [poste_1, poste_2, poste_3]
        selected = [p for p in postes if p]

        # no duplicates
        if len(selected) != len(set(selected)):
            raise ValidationError("لا يمكن اختيار نفس المنصب أكثر من مرة.")

        # enforce order logic
        if not poste_1 and (poste_2 or poste_3):
            raise ValidationError("يجب اختيار المنصب الأول قبل باقي الاختيارات.")

        # safety check (poste still open)
        today = timezone.localdate()
        for poste in selected:
            if not poste.is_open or (poste.deadline and poste.deadline < today):
                raise ValidationError(
                    f"المنصب '{poste}' لم يعد متاحًا."
                )

        return cleaned_data


# =========================
# Candidate Profile Form
# =========================

class CandidateProfileForm(forms.ModelForm):
    ARABIC_ALLOWED_PATTERN = re.compile(r'^[\u0600-\u06FF0-9\s\-\./:,]+$')

    class Meta:
        model = CandidateProfile
        fields = [
            'first_name',
            'last_name',
            'gender',
            'date_of_birth',
            'place_of_birth',
            'national_id_number',
            'email',
            'phone_number',
            'address',
            'wilaya',
            'commune',
            'current_administration',
            'current_position_grade',
            'current_function',
            'tenure_decision_date',
            'years_of_seniority',
            'years_of_effective_service',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tenure_decision_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.existing_candidate = kwargs.pop('existing_candidate', None)
        super().__init__(*args, **kwargs)

        # =========================
        # UI Classes
        # =========================
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

        self.fields['wilaya'].widget.attrs["class"] = "form-select"
        self.fields['commune'].widget.attrs["class"] = "form-select"

        # =========================
        # REQUIRED FIELDS
        # =========================
        for field in self.fields:
            self.fields[field].required = True

        # =========================
        # LABELS
        # =========================
        self.fields['wilaya'].label = "ولاية الإقامة"

        # =========================
        # ERROR MESSAGES
        # =========================
        error_map = {
            'first_name': "الاسم إجباري.",
            'last_name': "اللقب إجباري.",
            'gender': "الجنس إجباري.",
            'date_of_birth': "تاريخ الميلاد إجباري.",
            'place_of_birth': "مكان الميلاد إجباري.",
            'national_id_number': "رقم التعريف الوطني إجباري.",
            'email': "البريد الإلكتروني إجباري.",
            'phone_number': "رقم الهاتف إجباري.",
            'address': "العنوان إجباري.",
            'wilaya': "ولاية الإقامة إجبارية.",
            'commune': "البلدية إجبارية.",
            'current_administration': "الإدارة الحالية إجبارية.",
            'current_position_grade': "الرتبة الحالية إجبارية.",
            'current_function': "الوظيفة الحالية إجبارية.",
            'tenure_decision_date': "تاريخ قرار الترسيم إجباري.",
            'years_of_seniority': "سنوات الأقدمية إجبارية.",
            'years_of_effective_service': "سنوات الخدمة الفعلية إجبارية.",
        }

        for field, msg in error_map.items():
            self.fields[field].error_messages['required'] = msg

        # =========================
        # PLACEHOLDERS
        # =========================
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'مثال: محمد أمين',
            'data-arabic-only': 'true',
        })

        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'مثال: بن علي',
            'data-arabic-only': 'true',
        })

        self.fields['place_of_birth'].widget.attrs.update({
            'placeholder': 'مثال: الجزائر العاصمة',
            'data-arabic-only': 'true',
        })

        self.fields['national_id_number'].widget.attrs.update({
            'placeholder': '18 رقم',
            'dir': 'ltr',
            'maxlength': '18',
        })

        self.fields['email'].widget.attrs.update({
            'placeholder': 'example@email.com',
            'dir': 'ltr',
        })

        self.fields['phone_number'].widget.attrs.update({
            'placeholder': '0550123456',
            'dir': 'ltr',
        })

        self.fields['address'].widget.attrs.update({
            'placeholder': 'العنوان الكامل',
            'data-arabic-only': 'true',
        })

        # =========================
        # COMMUNE FILTER
        # =========================
        self.fields['commune'].queryset = Commune.objects.none()

        wilaya_id = self.data.get('wilaya') if self.is_bound else getattr(self.instance, 'wilaya_id', None)

        if wilaya_id:
            self.fields['commune'].queryset = Commune.objects.filter(wilaya_id=wilaya_id)

    # =========================
    # VALIDATION
    # =========================

    def _validate_arabic_text(self, value, label):
        value = (value or '').strip()

        if not value:
            raise ValidationError(f"{label} إجباري.")

        if not self.ARABIC_ALLOWED_PATTERN.match(value):
            raise ValidationError(f"{label} يجب أن يكون بالعربية فقط.")

        return value

    def clean_first_name(self):
        return self._validate_arabic_text(self.cleaned_data.get('first_name'), "الاسم")

    def clean_last_name(self):
        return self._validate_arabic_text(self.cleaned_data.get('last_name'), "اللقب")

    def clean_place_of_birth(self):
        return self._validate_arabic_text(self.cleaned_data.get('place_of_birth'), "مكان الميلاد")

    def clean_address(self):
        return self._validate_arabic_text(self.cleaned_data.get('address'), "العنوان")

    def clean_national_id_number(self):
        value = (self.cleaned_data.get('national_id_number') or '').strip()

        if not value.isdigit() or len(value) != 18:
            raise ValidationError("رقم التعريف الوطني يجب أن يكون 18 رقمًا.")

        if CandidateProfile.objects.filter(national_id_number=value).exists():
            raise ValidationError("يوجد مترشح بنفس الرقم.")

        return value

    def clean(self):
        cleaned = super().clean()

        if (
            cleaned.get('years_of_effective_service') is not None and
            cleaned.get('years_of_seniority') is not None and
            cleaned['years_of_effective_service'] < cleaned['years_of_seniority']
        ):
            self.add_error('years_of_effective_service', "غير منسجمة مع الأقدمية.")

        return cleaned