import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Bakery, User

class BakeryRegistrationForm(forms.ModelForm):
    # Owner specific fields
    owner_username = forms.CharField(max_length=150, required=True, label="Owner Username")
    owner_email = forms.EmailField(required=True, label="Owner Email")
    owner_password = forms.CharField(widget=forms.PasswordInput, required=True, label="Owner Password")
    owner_password_confirm = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirm Password")
    
    class Meta:
        model = Bakery
        fields = ['name', 'address', 'phone']
        labels = {
            'name': 'Bakery Name',
            'address': 'Bakery Address',
            'phone': 'Bakery Phone',
        }

    def clean_owner_username(self):
        username = self.cleaned_data.get('owner_username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(f"The username '{username}' is already taken. Please choose another one.")
        return username

    def clean_owner_email(self):
        email = self.cleaned_data.get('owner_email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Basic regex: allow digits, +, -, spaces, parenthesis
        if not re.match(r'^[\d\+\-\(\) ]{8,20}$', phone):
            raise forms.ValidationError("Please enter a valid phone number (e.g., +1234567890).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('owner_password')
        password_confirm = cleaned_data.get('owner_password_confirm')

        # Check if passwords hit the schema validation
        if password and password_confirm:
            if password != password_confirm:
                self.add_error('owner_password_confirm', "Passwords do not match.")
            else:
                # Use Django's built in password validators
                try:
                    validate_password(password)
                except forms.ValidationError as e:
                    self.add_error('owner_password', e)
        
        return cleaned_data

class StaffCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Assuming staff roles
        roles = [('Manager', 'Manager'), ('Cashier', 'Cashier'), ('Inventory Clerk', 'Inventory Clerk')]
        self.fields['role'].choices = roles

    def save(self, commit=True, bakery=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if bakery:
            user.bakery = bakery
        if commit:
            user.save()
        return user

class StaffEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        roles = [('Manager', 'Manager'), ('Cashier', 'Cashier'), ('Inventory Clerk', 'Inventory Clerk')]
        self.fields['role'].choices = roles

class BakeryEditForm(forms.ModelForm):
    class Meta:
        model = Bakery
        fields = ['name', 'address', 'phone']
        labels = {
            'name': 'Bakery Name',
            'address': 'Bakery Address',
            'phone': 'Contact Phone',
        }
        
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not re.match(r'^[\d\+\-\(\) ]{8,20}$', phone):
            raise forms.ValidationError("Please enter a valid phone number (e.g., +1234567890).")
        return phone

class OwnerProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email
