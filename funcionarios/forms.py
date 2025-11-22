from django import forms
from .models import Funcionario

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ['nome', 'cpf', 'cargo', 'email', 'telefone', 'salario', 'data_admissao', 'status', 'foto']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input'}),
            'cargo': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input'}),
            'salario': forms.NumberInput(attrs={'class': 'form-input'}),
            'data_admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }
