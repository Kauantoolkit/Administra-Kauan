# funcionarios/forms.py
from django import forms
from .models import CustomUser

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['nome', 'email', 'cpf', 'is_active', 'is_staff']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
        }
