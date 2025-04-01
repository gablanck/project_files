from django import forms
from .models import Event
from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm  

class EventForm(forms.ModelForm):
    # Use separate date and time fields for better user experience
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text='Select the date for the event'
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        help_text='Select the start time'
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        help_text='Select the end time'
    )
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'start_time', 'end_time']
        
    def clean(self):
        cleaned_data = super().clean()
        # The model will still need datetime objects, so we'll handle that in the view
        return cleaned_data

class RegisterForm(UserCreationForm):  
    email = forms.EmailField(required=True)  

    class Meta:  
        model = User  
        fields = ["username", "email", "password1", "password2"]
