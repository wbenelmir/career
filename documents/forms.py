# documents/forms.py
from django import forms
from .models import ApplicationDocument, DocumentType


class ApplicationDocumentForm(forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ['document_type', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['document_type'].queryset = DocumentType.objects.filter(is_active=True)

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')

        if not uploaded_file:
            raise forms.ValidationError("Please select a file.")

        max_size = 5 * 1024 * 1024
        if uploaded_file.size > max_size:
            raise forms.ValidationError("File size must not exceed 5 MB.")

        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            raise forms.ValidationError(
                "Only PDF, JPG, JPEG, and PNG files are allowed."
            )

        return uploaded_file