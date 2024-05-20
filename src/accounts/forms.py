from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CreateUserForms(UserCreationForm):
    class Meta:
        model: User
        fields: ['username', 'password1', 'password2']
