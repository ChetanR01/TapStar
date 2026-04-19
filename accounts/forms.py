from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import User


class EmailSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # username is required by AbstractUser — derive from email
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
