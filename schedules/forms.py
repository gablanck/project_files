from django import forms
from .models import Event
from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm  

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_time', 'end_time']

class RegisterForm(UserCreationForm):  
    email = forms.EmailField(required=True)  

    class Meta:  
        model = User  
        fields = ["username", "email", "password1", "password2"]
