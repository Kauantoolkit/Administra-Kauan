# funcionarios/forms.py
from django import forms
from .models import CustomUser, Funcionario

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ['nome', 'cpf', 'email', 'telefone', 'salario']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input'}),
            'salario': forms.NumberInput(attrs={'class': 'form-input'}),
            'data_admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }
