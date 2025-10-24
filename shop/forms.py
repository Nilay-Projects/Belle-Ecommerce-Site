# shop/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Customer_Table
from django.contrib.auth.hashers import make_password
from .models import ContactMessage

class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    address = forms.CharField(widget=forms.Textarea)
    city = forms.CharField(max_length=100)

class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Customer_Table
        fields = ('first_name', 'last_name', 'email', 'password', 'phone', 'address', 'city')

    # Prevent duplicate emails
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Customer_Table.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
    
    def reset_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return password

    def save(self, commit=True):
        customer = super().save(commit=False)
        customer.password = make_password(self.cleaned_data['password'])  # hash password
        if commit:
            customer.save()
        return customer
    

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'id': 'ContactFormName', 'name': 'name', 'placeholder': 'Name'}),
            'email': forms.EmailInput(attrs={'id': 'ContactFormEmail', 'name': 'email', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'id': 'ContactFormPhone', 'name': 'phone', 'placeholder': 'Phone Number'}),
            'subject': forms.TextInput(attrs={'id': 'ContactSubject', 'name': 'subject', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'id': 'ContactFormMessage', 'name': 'message', 'placeholder': 'Your Message', 'rows': 10}),
        }
