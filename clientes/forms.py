from django import forms
from .models import Cliente
from decimal import Decimal

class ClienteForm(forms.ModelForm):
    valor_total_comprado = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Cliente
        fields = [
            'nome',
            'cpf',
            'email',
            'telefone',
            'cidade',
            'status',
            'ultima_compra',
            'valor_total_comprado',
        ]

        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input'}),
            'cidade': forms.TextInput(attrs={'class': 'form-input'}),
            'ultima_compra': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_valor_total_comprado(self):
        valor = self.cleaned_data.get('valor_total_comprado')

        if not valor:
            return Decimal('0.00')

        if isinstance(valor, str):
            valor = valor.replace('.', '')
            valor = valor.replace(',', '.')

        try:
            return Decimal(valor)
        except:
            raise forms.ValidationError("Informe um valor numérico válido.")