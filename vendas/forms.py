from django import forms
from django.forms import inlineformset_factory
from .models import Venda, ItemVenda

class VendaForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=Venda.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Venda
        fields = ['cliente', 'observacoes', 'status']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'quantidade']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

ItemVendaFormSet = inlineformset_factory(
    Venda,
    ItemVenda, 
    form=ItemVendaForm,
    extra=1,
    can_delete=True
)