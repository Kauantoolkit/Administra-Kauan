from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from contas.fields import DecimalBrField
from contas.models import Produto, ProdutoVariacao
from .models import ItemVenda, Venda


class VendaForm(forms.ModelForm):
    desconto = DecimalBrField(
        label='Desconto (R$)', min_value=Decimal('0'), required=False,
        initial=Decimal('0.00'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,00'}))
    acrescimo = DecimalBrField(
        label='Acréscimo (R$)', min_value=Decimal('0'), required=False,
        initial=Decimal('0.00'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,00'}))

    class Meta:
        model = Venda
        fields = ['cliente', 'status', 'forma_pagamento', 'desconto', 'acrescimo', 'observacoes']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'desconto': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,00'}),
            'acrescimo': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,00'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].required = False
        self.fields['cliente'].empty_label = 'Consumidor final (sem cadastro)'

    def clean_desconto(self):
        return self.cleaned_data.get('desconto') or Decimal('0.00')

    def clean_acrescimo(self):
        return self.cleaned_data.get('acrescimo') or Decimal('0.00')


class ItemVendaForm(forms.ModelForm):
    quantidade = DecimalBrField(
        label='Quantidade', min_value=Decimal('0.001'),
        widget=forms.TextInput(attrs={'class': 'form-control js-quantidade',
                                      'placeholder': '1'}))
    preco_unitario = DecimalBrField(
        label='Preço unitário', min_value=Decimal('0'), required=False,
        widget=forms.TextInput(attrs={'class': 'form-control js-preco',
                                      'placeholder': '0,00'}))
    desconto_item = DecimalBrField(
        label='Desconto', min_value=Decimal('0'), required=False,
        initial=Decimal('0.00'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,00'}))

    class Meta:
        model = ItemVenda
        fields = ['produto', 'variacao', 'quantidade', 'preco_unitario', 'desconto_item']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control js-produto'}),
            'variacao': forms.Select(attrs={'class': 'form-control js-variacao'}),
            'quantidade': forms.TextInput(attrs={
                'class': 'form-control js-quantidade',
                'inputmode': 'decimal', 'placeholder': '1',
            }),
            'preco_unitario': forms.TextInput(attrs={
                'class': 'form-control js-preco',
                'inputmode': 'decimal', 'placeholder': '0,00',
            }),
            'desconto_item': forms.TextInput(attrs={
                'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,00',
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
        dados['desconto_item'] = dados.get('desconto_item') or Decimal('0.00')
        self.instance.desconto_item = dados['desconto_item']
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
