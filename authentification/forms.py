from django import forms
from django.contrib.auth.forms import AuthenticationForm


class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)