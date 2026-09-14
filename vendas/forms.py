from django import forms
from django.forms import inlineformset_factory

from contas.models import Produto, ProdutoVariacao
from .models import ItemVenda, Venda


class VendaForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = ['cliente', 'status', 'forma_pagamento', 'desconto', 'acrescimo', 'observacoes']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'acrescimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].required = False
        self.fields['cliente'].empty_label = 'Consumidor final (sem cadastro)'


class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'variacao', 'quantidade', 'preco_unitario', 'desconto_item']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control js-produto'}),
            'variacao': forms.Select(attrs={'class': 'form-control js-variacao'}),
            'quantidade': forms.NumberInput(attrs={
                'class': 'form-control js-quantidade',
                'step': '0.001', 'min': '0.001', 'inputmode': 'decimal',
            }),
            'preco_unitario': forms.NumberInput(attrs={
                'class': 'form-control js-preco', 'step': '0.01', 'min': '0',
            }),
            'desconto_item': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('nome')
        self.fields['variacao'].queryset = ProdutoVariacao.objects.filter(
            ativo=True
        ).select_related('produto')
        self.fields['variacao'].required = False
        # Preenchido automaticamente a partir do produto quando em branco.
        self.fields['preco_unitario'].required = False

    def clean(self):
        dados = super().clean()
        produto = dados.get('produto')
        if produto and not dados.get('preco_unitario'):
            variacao = dados.get('variacao')
            dados['preco_unitario'] = (
                variacao.preco_efetivo if variacao else produto.venda
            )
            self.instance.preco_unitario = dados['preco_unitario']
        return dados


ItemVendaFormSet = inlineformset_factory(
    Venda,
    ItemVenda,
    form=ItemVendaForm,
    extra=1,
    can_delete=True,
)
