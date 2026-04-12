from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from captcha.fields import CaptchaField
import re

from .models import CandidateProfile, Application
from locations.models import Commune


class ApplicationForm(forms.ModelForm):
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

    class Meta:
        model = Application
        fields = ["poste"]
        widgets = {
            "poste": forms.Select(attrs={"class": "form-select form-select-lg"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()

        self.fields["poste"].queryset = self.fields["poste"].queryset.filter(
            is_open=True
        ).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=today)
        )

        self.fields["poste"].empty_label = "اختر المنصب المطلوب"
        self.fields["poste"].error_messages["required"] = "يرجى اختيار الوظيفة أو المنصب المطلوب."

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

    def clean_poste(self):
        poste = self.cleaned_data.get("poste")

        if not poste:
            raise ValidationError("يرجى اختيار الوظيفة أو المنصب المطلوب.")

        today = timezone.localdate()

        if not getattr(poste, "is_open", False):
            raise ValidationError("هذا المنصب غير مفتوح حاليًا للتسجيل.")

        if poste.deadline and poste.deadline < today:
            raise ValidationError("انتهى آخر أجل للترشح لهذا المنصب.")

        return poste


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
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'place_of_birth': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'wilaya': forms.Select(attrs={'class': 'form-select', 'id': 'id_wilaya'}),
            'commune': forms.Select(attrs={'class': 'form-select', 'id': 'id_commune'}),
            'current_administration': forms.TextInput(attrs={'class': 'form-control'}),
            'current_position_grade': forms.TextInput(attrs={'class': 'form-control'}),
            'current_function': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_seniority': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'years_of_effective_service': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        self.existing_candidate = kwargs.pop('existing_candidate', None)
        super().__init__(*args, **kwargs)

        required_fields = [
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
        for field_name in required_fields:
            self.fields[field_name].required = True

        self.fields['wilaya'].label = "ولاية الإقامة"

        self.fields['first_name'].error_messages['required'] = "الاسم إجباري."
        self.fields['last_name'].error_messages['required'] = "اللقب إجباري."
        self.fields['gender'].error_messages['required'] = "الجنس إجباري."
        self.fields['date_of_birth'].error_messages['required'] = "تاريخ الميلاد إجباري."
        self.fields['place_of_birth'].error_messages['required'] = "مكان الميلاد إجباري."
        self.fields['national_id_number'].error_messages['required'] = "رقم التعريف الوطني إجباري."
        self.fields['email'].error_messages['required'] = "البريد الإلكتروني إجباري."
        self.fields['phone_number'].error_messages['required'] = "رقم الهاتف إجباري."
        self.fields['address'].error_messages['required'] = "العنوان إجباري."
        self.fields['wilaya'].error_messages['required'] = "ولاية الإقامة إجبارية."
        self.fields['commune'].error_messages['required'] = "البلدية إجبارية."
        self.fields['current_administration'].error_messages['required'] = "الإدارة الحالية إجبارية."
        self.fields['current_position_grade'].error_messages['required'] = "الرتبة الحالية إجبارية."
        self.fields['current_function'].error_messages['required'] = "الوظيفة الحالية إجبارية."
        self.fields['tenure_decision_date'].error_messages['required'] = "تاريخ قرار الترسيم إجباري."
        self.fields['years_of_seniority'].error_messages['required'] = "سنوات الأقدمية إجبارية."
        self.fields['years_of_effective_service'].error_messages['required'] = "سنوات الخدمة الفعلية إجبارية."

        self.fields['wilaya'].empty_label = "اختر الولاية"
        self.fields['commune'].empty_label = "اختر البلدية"

        self.fields['commune'].queryset = Commune.objects.none()

        wilaya_id = None
        if self.is_bound:
            wilaya_id = self.data.get('wilaya')
        else:
            wilaya_id = self.initial.get('wilaya') or getattr(self.instance, 'wilaya_id', None)

        if wilaya_id:
            try:
                self.fields['commune'].queryset = Commune.objects.filter(
                    wilaya_id=wilaya_id
                ).order_by('name_fr')
            except (ValueError, TypeError):
                self.fields['commune'].queryset = Commune.objects.none()

        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'مثال: محمد أمين',
            'autocomplete': 'given-name',
            'data-arabic-only': 'true',
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'مثال: بن علي',
            'autocomplete': 'family-name',
            'data-arabic-only': 'true',
        })
        self.fields['date_of_birth'].widget.attrs.update({
            'placeholder': 'اختر تاريخ الميلاد',
        })
        self.fields['place_of_birth'].widget.attrs.update({
            'placeholder': 'مثال: بلدية المحمدية ولاية الجزائر العاصمة',
            'data-arabic-only': 'true',
        })
        self.fields['national_id_number'].widget.attrs.update({
            'placeholder': 'أدخل رقم التعريف الوطني',
            'dir': 'ltr',
            'inputmode': 'numeric',
            'maxlength': '18',
            'pattern': r'\d{18}',
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'example@email.com',
            'dir': 'ltr',
            'autocomplete': 'email',
        })
        self.fields['phone_number'].widget.attrs.update({
            'placeholder': 'مثال: 0550123456',
            'dir': 'ltr',
            'autocomplete': 'tel',
        })
        self.fields['address'].widget.attrs.update({
            'placeholder': 'أدخل العنوان الكامل',
            'data-arabic-only': 'true',
        })
        self.fields['current_administration'].widget.attrs.update({
            'placeholder': 'مثال: مديرية الرقمنة',
            'data-arabic-only': 'true',
        })
        self.fields['current_position_grade'].widget.attrs.update({
            'placeholder': 'مثال: متصرف رئيسي',
            'data-arabic-only': 'true',
        })
        self.fields['current_function'].widget.attrs.update({
            'placeholder': 'مثال: رئيس مصلحة',
            'data-arabic-only': 'true',
        })
        self.fields['tenure_decision_date'].widget.attrs.update({
            'placeholder': 'اختر تاريخ قرار الترسيم',
        })
        self.fields['years_of_seniority'].widget.attrs.update({
            'placeholder': '0',
            'inputmode': 'numeric',
            'dir': 'ltr',
        })
        self.fields['years_of_effective_service'].widget.attrs.update({
            'placeholder': '0',
            'inputmode': 'numeric',
            'dir': 'ltr',
        })

        gender_choices = list(self.fields['gender'].choices)
        if gender_choices and gender_choices[0][0] == '':
            gender_choices[0] = ('', 'اختر الجنس')
        self.fields['gender'].choices = gender_choices

    def _validate_arabic_text(self, value, field_label):
        value = (value or '').strip()
        if not value:
            raise ValidationError(f"{field_label} إجباري.")

        if not self.ARABIC_ALLOWED_PATTERN.match(value):
            raise ValidationError(
                f"{field_label} يجب أن يحتوي على حروف عربية وأرقام فقط، مع السماح بالرموز: - / . : ,"
            )

        return value

    def clean_first_name(self):
        return self._validate_arabic_text(self.cleaned_data.get('first_name'), "الاسم")

    def clean_last_name(self):
        return self._validate_arabic_text(self.cleaned_data.get('last_name'), "اللقب")

    def clean_place_of_birth(self):
        return self._validate_arabic_text(self.cleaned_data.get('place_of_birth'), "مكان الميلاد")

    def clean_address(self):
        return self._validate_arabic_text(self.cleaned_data.get('address'), "العنوان")

    def clean_current_administration(self):
        return self._validate_arabic_text(self.cleaned_data.get('current_administration'), "الإدارة الحالية")

    def clean_current_position_grade(self):
        return self._validate_arabic_text(self.cleaned_data.get('current_position_grade'), "الرتبة الحالية")

    def clean_current_function(self):
        return self._validate_arabic_text(self.cleaned_data.get('current_function'), "الوظيفة الحالية")

    def clean_national_id_number(self):
        national_id_number = (self.cleaned_data.get('national_id_number') or '').strip()

        if not national_id_number:
            raise ValidationError("رقم التعريف الوطني إجباري.")

        if not national_id_number.isdigit():
            raise ValidationError("رقم التعريف الوطني يجب أن يحتوي على أرقام فقط.")

        if len(national_id_number) != 18:
            raise ValidationError("رقم التعريف الوطني يجب أن يتكون من 18 رقمًا بالضبط.")

        qs = CandidateProfile.objects.filter(national_id_number=national_id_number)

        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("يوجد مترشح مسجل مسبقًا بنفس رقم التعريف الوطني.")

        return national_id_number

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip().replace(' ', '')

        if not phone_number:
            raise ValidationError("رقم الهاتف إجباري.")

        allowed_chars = set("0123456789+ ")
        if any(char not in allowed_chars for char in phone_number):
            raise ValidationError("رقم الهاتف يجب أن يحتوي على أرقام فقط، مع إمكانية استعمال + في البداية.")

        if len(phone_number.replace(' ', '')) < 8:
            raise ValidationError("رقم الهاتف قصير جدًا.")

        return phone_number

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()

        if not email:
            raise ValidationError("البريد الإلكتروني إجباري.")

        return email

    def clean_tenure_decision_date(self):
        tenure_decision_date = self.cleaned_data.get('tenure_decision_date')

        if not tenure_decision_date:
            raise ValidationError("تاريخ قرار الترسيم إجباري.")

        if tenure_decision_date > timezone.now().date():
            raise ValidationError("تاريخ قرار الترسيم لا يمكن أن يكون في المستقبل.")

        return tenure_decision_date

    def clean_years_of_seniority(self):
        years_of_seniority = self.cleaned_data.get('years_of_seniority')

        if years_of_seniority is None:
            raise ValidationError("سنوات الأقدمية إجبارية.")

        if years_of_seniority < 0:
            raise ValidationError("سنوات الأقدمية لا يمكن أن تكون سالبة.")

        return years_of_seniority

    def clean_years_of_effective_service(self):
        years_of_effective_service = self.cleaned_data.get('years_of_effective_service')

        if years_of_effective_service is None:
            raise ValidationError("سنوات الخدمة الفعلية إجبارية.")

        if years_of_effective_service < 0:
            raise ValidationError("سنوات الخدمة الفعلية لا يمكن أن تكون سالبة.")

        return years_of_effective_service

    def clean(self):
        cleaned_data = super().clean()

        wilaya = cleaned_data.get('wilaya')
        commune = cleaned_data.get('commune')
        years_of_seniority = cleaned_data.get('years_of_seniority')
        years_of_effective_service = cleaned_data.get('years_of_effective_service')
        tenure_decision_date = cleaned_data.get('tenure_decision_date')

        if commune and wilaya and getattr(commune, 'wilaya_id', None) != wilaya.id:
            self.add_error('commune', "البلدية المختارة لا تنتمي إلى الولاية المحددة.")

        if (
            years_of_seniority is not None and
            years_of_effective_service is not None and
            years_of_effective_service < years_of_seniority
        ):
            self.add_error(
                'years_of_effective_service',
                "سنوات الخدمة الفعلية لا ينبغي أن تكون أقل من سنوات الأقدمية."
            )

        if (
            tenure_decision_date is not None and
            years_of_effective_service is not None
        ):
            min_service_years = (timezone.now().date() - tenure_decision_date).days / 365.25
            if years_of_effective_service > int(min_service_years) + 1:
                self.add_error(
                    'years_of_effective_service',
                    "سنوات الخدمة الفعلية تبدو غير منسجمة مع تاريخ قرار الترسيم."
                )

        return cleaned_data