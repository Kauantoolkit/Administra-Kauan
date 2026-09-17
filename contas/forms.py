import re
from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .fields import DecimalBrField
from .models import (
    Categoria, ConfiguracaoLoja, CustomUser, Fornecedor, MovimentoEstoque,
    Produto, ProdutoVariacao, UNIDADES_FRACIONADAS,
)


def _somente_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def validar_cpf(cpf):
    """Validação real de CPF (dígitos verificadores), não só contagem."""
    numeros = _somente_digitos(cpf)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(
            int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho)
        )
        digito = (soma * 10) % 11
        digito = 0 if digito == 10 else digito
        if digito != int(numeros[tamanho]):
            return False
    return True


def validar_cnpj(cnpj):
    numeros = _somente_digitos(cnpj)
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False
    for tamanho in (12, 13):
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(numeros[i]) * pesos[i] for i in range(tamanho))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(numeros[tamanho]):
            return False
    return True


def formatar_cpf(cpf):
    n = _somente_digitos(cpf)
    return f'{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}' if len(n) == 11 else cpf


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254, required=True,
        help_text='Obrigatório. Digite um endereço de e-mail válido.',
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'nome', 'cpf')

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').lower().strip()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError('Este email já está cadastrado no sistema.')
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not cpf:
            return None
        if not validar_cpf(cpf):
            raise ValidationError('CPF inválido.')
        cpf = formatar_cpf(cpf)
        if CustomUser.objects.filter(cpf=cpf).exists():
            raise ValidationError('Este CPF já está cadastrado no sistema.')
        return cpf


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'nome', 'cpf', 'papel', 'is_active', 'is_staff')


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'seu@email.com'}),
    )


class ProdutoForm(forms.ModelForm):
    # Aceitam virgula; por isso texto com inputmode, e nao type="number".
    def _campo_br(rotulo, minimo, exemplo):
        return DecimalBrField(
            label=rotulo, min_value=Decimal(minimo),
            widget=forms.TextInput(attrs={'class': 'form-control',
                                          'placeholder': exemplo}))

    custo = _campo_br('Preço de Custo (R$)', '0', '0,00')
    venda = _campo_br('Preço de Venda (R$)', '0', '0,00')
    quantidade_minima_venda = _campo_br('Quantidade mínima por venda', '0.001', '1,000')
    incremento_venda = _campo_br('Incremento permitido', '0.001', '1,000')
    quantidade_minima_alerta = _campo_br('Qtd. Mínima para Alerta', '0', '5')

    class Meta:
        model = Produto
        fields = [
            'sku', 'codigo_barras', 'nome', 'marca', 'descricao', 'categoria',
            'unidade_medida', 'quantidade_minima_venda', 'incremento_venda',
            'custo', 'venda', 'quantidade_minima_alerta',
            'controla_estoque', 'ativo', 'imagem',
        ]
        labels = {
            'sku': 'SKU (Código Único)',
            'codigo_barras': 'Código de Barras (EAN/GTIN)',
            'nome': 'Nome do Produto',
            'marca': 'Marca do Produto',
            'descricao': 'Descrição Detalhada',
            'categoria': 'Categoria',
            'unidade_medida': 'Vendido por',
            'quantidade_minima_venda': 'Quantidade mínima por venda',
            'incremento_venda': 'Incremento permitido',
            'custo': 'Preço de Custo (R$)',
            'venda': 'Preço de Venda (R$ por unidade de medida)',
            'quantidade_minima_alerta': 'Qtd. Mínima para Alerta',
            'controla_estoque': 'Controlar estoque',
            'ativo': 'Disponível para venda',
            'imagem': 'Imagem do Produto',
        }
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código único'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7891000000000'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do produto'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da marca'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select', 'id': 'id_unidade_medida'}),
            'quantidade_minima_venda': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '1,000'}),
            'incremento_venda': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '1,000'}),
            'custo': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,00'}),
            'venda': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,00'}),
            'quantidade_minima_alerta': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '5'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control-file', 'accept': 'image/*'}),
        }

    def clean_codigo_barras(self):
        codigo = (self.cleaned_data.get('codigo_barras') or '').strip()
        return codigo or None

    def clean(self):
        dados = super().clean()
        unidade = dados.get('unidade_medida')
        custo, venda = dados.get('custo'), dados.get('venda')

        if custo is not None and venda is not None and venda < custo:
            self.add_error(
                'venda', 'O preço de venda está abaixo do custo. Confirme os valores.'
            )

        if unidade and unidade not in UNIDADES_FRACIONADAS:
            for campo in ('quantidade_minima_venda', 'incremento_venda'):
                valor = dados.get(campo)
                if valor is not None and valor != valor.to_integral_value():
                    self.add_error(
                        campo,
                        'Produtos vendidos por unidade inteira não aceitam fração.',
                    )
        return dados


class ProdutoVariacaoForm(forms.ModelForm):
    class Meta:
        model = ProdutoVariacao
        fields = ['sku', 'codigo_barras', 'tamanho', 'cor', 'descricao_extra',
                  'preco_venda', 'ativo']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control'}),
            'tamanho': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'P / M / G / 42'}),
            'cor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Azul'}),
            'descricao_extra': forms.TextInput(attrs={'class': 'form-control'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }


class BuscaEstoqueForm(forms.Form):
    busca_nome = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'placeholder': 'Nome do produto...'})
    )
    busca_sku = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'placeholder': 'Código / SKU...'})
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(), required=False, empty_label='Todas Categorias'
    )
    status = forms.ChoiceField(
        choices=[('', 'Todos Status')] + list(Produto.STATUS_CHOICES), required=False
    )


class _QuantidadePorUnidadeMixin:
    """Valida a quantidade conforme a unidade de medida do produto escolhido."""

    def _validar_quantidade(self, produto, quantidade):
        if produto is None or quantidade is None:
            return quantidade
        try:
            return produto.normalizar_quantidade(quantidade)
        except ValidationError as exc:
            raise ValidationError(exc.messages) from exc


class MovimentoEstoqueForm(_QuantidadePorUnidadeMixin, forms.ModelForm):
    quantidade = DecimalBrField(
        label='Quantidade', min_value=Decimal('0.001'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,000'}))
    custo_unitario = DecimalBrField(
        label='Custo Unitário', min_value=Decimal('0'), required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,00'}))

    class Meta:
        model = MovimentoEstoque
        fields = ['produto', 'variacao', 'quantidade', 'custo_unitario',
                  'validade', 'observacao']
        widgets = {
            'quantidade': forms.TextInput(attrs={'inputmode': 'decimal', 'placeholder': '0,000'}),
            'custo_unitario': forms.TextInput(attrs={'inputmode': 'decimal', 'placeholder': '0,00'}),
            'validade': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.order_by('nome')
        self.fields['variacao'].required = False
        for field in self.fields.values():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{css} form-control'.strip()

    def clean(self):
        dados = super().clean()
        produto, quantidade = dados.get('produto'), dados.get('quantidade')
        if produto and quantidade is not None:
            try:
                dados['quantidade'] = self._validar_quantidade(produto, quantidade)
                self.instance.quantidade = dados['quantidade']
            except ValidationError as exc:
                self.add_error('quantidade', exc)

        variacao = dados.get('variacao')
        if variacao and produto and variacao.produto_id != produto.id:
            self.add_error('variacao', 'Esta variação não pertence ao produto escolhido.')
        elif produto and not variacao and produto.variacoes.exists():
            self.add_error(
                'variacao',
                f'"{produto.nome}" tem grade (tamanho/cor). Escolha qual variação movimentar.',
            )
        return dados


class EntradaProdutoEspecificoForm(_QuantidadePorUnidadeMixin, forms.ModelForm):
    quantidade = DecimalBrField(
        label='Quantidade', min_value=Decimal('0.001'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,000'}))
    custo_unitario = DecimalBrField(
        label='Custo Unitário', min_value=Decimal('0'), required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0,00'}))

    class Meta:
        model = MovimentoEstoque
        fields = ['variacao', 'quantidade', 'custo_unitario', 'validade', 'observacao']
        widgets = {
            'quantidade': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,000'}),
            'custo_unitario': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'placeholder': '0,00'}),
            'validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, produto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.produto = produto
        if produto is not None:
            self.fields['variacao'].queryset = produto.variacoes.filter(ativo=True)
            casas = produto.casas_decimais
            exemplo = ('0,' + '0' * casas) if casas else '0'
            self.fields['quantidade'].widget.attrs['placeholder'] = exemplo
        self.fields['variacao'].required = False

    def clean_quantidade(self):
        return self._validar_quantidade(self.produto, self.cleaned_data.get('quantidade'))

    def clean_variacao(self):
        variacao = self.cleaned_data.get('variacao')
        if self.produto is None:
            return variacao
        if variacao is None and self.produto.variacoes.exists():
            raise ValidationError(
                f'"{self.produto.nome}" tem grade (tamanho/cor). '
                f'Escolha qual variação movimentar.'
            )
        return variacao


class ConfiguracaoLojaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoLoja
        fields = [
            'nome_loja', 'slogan', 'cnpj', 'telefone', 'endereco', 'logo',
            'cor_primaria', 'simbolo_moeda',
            'permite_estoque_negativo', 'baixa_estoque_em_orcamento',
        ]
        widgets = {
            'nome_loja': forms.TextInput(attrs={'class': 'form-control'}),
            'slogan': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cor_primaria': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'simbolo_moeda': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['nome_fantasia', 'categoria', 'cnpj', 'contato_principal',
                  'email', 'telefone', 'status']
        widgets = {
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Tech Distribuidora'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Eletrônicos e Componentes'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00', 'maxlength': '18'}),
            'contato_principal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do contato'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000', 'maxlength': '20'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if not validar_cnpj(cnpj):
            raise ValidationError('CNPJ inválido.')
        n = _somente_digitos(cnpj)
        return f'{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}'

    def clean_telefone(self):
        n = _somente_digitos(self.cleaned_data.get('telefone'))
        if len(n) not in (10, 11):
            raise ValidationError('Telefone deve conter 10 ou 11 dígitos.')
        if len(n) == 11:
            return f'({n[:2]}) {n[2:7]}-{n[7:]}'
        return f'({n[:2]}) {n[2:6]}-{n[6:]}'
