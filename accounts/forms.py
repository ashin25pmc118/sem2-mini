from django import forms
from .models import Bakery, User

class BakeryRegistrationForm(forms.ModelForm):
    # Owner specific fields
    owner_username = forms.CharField(max_length=150, required=True, label="Owner Username")
    owner_password = forms.CharField(widget=forms.PasswordInput, required=True, label="Owner Password")
    owner_email = forms.EmailField(required=True, label="Owner Email")
    
    class Meta:
        model = Bakery
        fields = ['name', 'address', 'phone']
        labels = {
            'name': 'Bakery Name',
            'address': 'Bakery Address',
            'phone': 'Bakery Phone',
        }

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
