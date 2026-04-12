from django import forms
from django.core.exceptions import ValidationError

from applications.models import Application
from tracking.models import ApplicationTracking, InterviewSchedule


class ApplicationStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'status',
            'rejection_reason',
            'admin_notes',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'admin_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = getattr(self, 'instance', None)

        if instance and instance.pk:
            allowed_statuses = instance.can_transition_to
            self.fields['status'].choices = [
                (instance.status, instance.get_status_display())
            ] + [
                (value, label)
                for value, label in Application.Status.choices
                if allowed_statuses(value)
            ]
        else:
            self.fields['status'].choices = Application.Status.choices

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = (cleaned_data.get('rejection_reason') or '').strip()

        if status in [
            Application.Status.PRELIMINARY_REJECTED,
            Application.Status.FINAL_REJECTED,
        ] and not rejection_reason:
            raise ValidationError(
                'سبب الرفض إجباري عند رفض الطلب.'
            )

        instance = getattr(self, 'instance', None)
        if instance and instance.pk and status and status != instance.status:
            if not instance.can_transition_to(status):
                raise ValidationError(
                    f"لا يمكن الانتقال من الحالة الحالية إلى الحالة المطلوبة."
                )

        cleaned_data['rejection_reason'] = rejection_reason
        return cleaned_data


class TrackingEntryForm(forms.ModelForm):
    class Meta:
        model = ApplicationTracking
        fields = [
            'status',
            'note',
            'is_visible_to_candidate',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_visible_to_candidate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.application = kwargs.pop('application', None)
        super().__init__(*args, **kwargs)

        if self.application:
            self.fields['status'].choices = [
                (self.application.status, self.application.get_status_display())
            ] + [
                (value, label)
                for value, label in Application.Status.choices
                if self.application.can_transition_to(value)
            ]

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')

        if self.application and status:
            if status != self.application.status and not self.application.can_transition_to(status):
                raise ValidationError("الحالة المختارة غير مسموح بها انطلاقًا من الحالة الحالية.")

        return cleaned_data


class InterviewScheduleForm(forms.ModelForm):
    class Meta:
        model = InterviewSchedule
        fields = [
            'interview_date',
            'interview_time',
            'location',
            'note',
        ]
        widgets = {
            'interview_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'interview_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def clean_location(self):
        location = (self.cleaned_data.get('location') or '').strip()
        if not location:
            raise ValidationError("مكان المقابلة إجباري.")
        return location

    def clean(self):
        cleaned_data = super().clean()
        interview_date = cleaned_data.get('interview_date')
        interview_time = cleaned_data.get('interview_time')

        if not interview_date:
            self.add_error('interview_date', "تاريخ المقابلة إجباري.")

        if not interview_time:
            self.add_error('interview_time', "وقت المقابلة إجباري.")

        return cleaned_data