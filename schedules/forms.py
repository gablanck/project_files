from django import forms
from .models import Event
from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm  
from datetime import datetime, time

class EventForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text='Select the date for the event'
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'step': '60'}),  # Disables seconds input
        help_text='Select the start time'
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'step': '60'}),  # Disables seconds input
        help_text='Select the end time'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].widget.attrs.update({'placeholder': 'HH:MM'})
        self.fields['end_time'].widget.attrs.update({'placeholder': 'HH:MM'})
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'start_time', 'end_time']
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class RegisterForm(UserCreationForm):  
    email = forms.EmailField(required=True)  

    class Meta:  
        model = User  
        fields = ["username", "email", "password1", "password2"]
