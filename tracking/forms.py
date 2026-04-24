from django import forms

class TrackingForm(forms.Form):
    tracking_code = forms.CharField(
        label="رمز التتبع",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "أدخل رمز التتبع",
            "autocomplete": "off",
        }),
        help_text="أدخل الرمز كما تم منحه لك بعد إرسال الطلب."
    )