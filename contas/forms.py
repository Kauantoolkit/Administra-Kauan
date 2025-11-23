from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import CustomUser, Fornecedor
from django import forms
from django.utils.translation import gettext_lazy as _
import re

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Obrigatório. Digite um endereço de e-mail válido.'
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'nome', 'cpf') 


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'nome', 'cpf', 'is_active', 'is_staff')


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'seu@email.com'})
    )


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['nome_fantasia', 'categoria', 'cnpj', 'contato_principal', 'email', 'telefone', 'status']
        widgets = {
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Tech Distribuidora'
            }),
            'categoria': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Eletrônicos e Componentes'
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00.000.000/0000-00',
                'maxlength': '18'
            }),
            'contato_principal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do contato'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemplo.com'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000',
                'maxlength': '20'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        cnpj_numeros = re.sub(r'\D', '', cnpj)
        
        if len(cnpj_numeros) != 14:
            raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
        
        cnpj_formatado = f"{cnpj_numeros[:2]}.{cnpj_numeros[2:5]}.{cnpj_numeros[5:8]}/{cnpj_numeros[8:12]}-{cnpj_numeros[12:]}"
        return cnpj_formatado
    
    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        telefone_numeros = re.sub(r'\D', '', telefone)
        
        if len(telefone_numeros) not in [10, 11]:
            raise forms.ValidationError('Telefone deve conter 10 ou 11 dígitos.')
        
        if len(telefone_numeros) == 11:
            telefone_formatado = f"({telefone_numeros[:2]}) {telefone_numeros[2:7]}-{telefone_numeros[7:]}"
        else:
            telefone_formatado = f"({telefone_numeros[:2]}) {telefone_numeros[2:6]}-{telefone_numeros[6:]}"
        
        return telefone_formatado
