from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)
    full_name = forms.CharField(max_length=100)

    class Meta:
        model = CustomUser
        fields = ['username', 'full_name', 'email', 'role', 'password1', 'password2']
