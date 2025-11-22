
from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
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
            'ultima_compra': forms.DateInput(attrs={'type': 'date'}),
            'status': forms.Select(),
        }
