from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import Categoria, CustomUser, MovimentoEstoque, Produto
from django import forms
from django.utils.translation import gettext_lazy as _

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

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['sku', 'nome', 'marca', 'descricao', 'categoria', 'custo', 'venda', 'quantidade_minima_alerta', 'unidade_medida', 'imagem']
        labels = {
            'sku': 'SKU (Código Único)',
            'nome': 'Nome do Produto',
            'marca': 'Marca do Produto',
            'descricao': 'Descrição Detalhada',
            'categoria': 'Categoria',
            'custo': 'Preço de Custo (R$)',
            'venda': 'Preço de Venda (R$)',
            'quantidade_minima_alerta': 'Qtd. Mínima para Alerta (Estoque Baixo)',
            'unidade_medida': 'Unidade de Medida (Ex: UN, KG)',
            'imagem': 'Imagem do Produto',
        }
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Único do Produto'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Completo do Produto'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da marca'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalhes, cores, dimensões, etc.'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'quantidade_minima_alerta': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: UN, KG, L'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

class BuscaEstoqueForm(forms.Form):
    busca_nome = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Nome do produto...'})
    )
    
    busca_sku = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Código / SKU...'})
    )

    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        empty_label='Todas Categorias',
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos Status')] + list(Produto.STATUS_CHOICES),
        required=False,
    )

class MovimentoEstoqueForm(forms.ModelForm):
    """
    Formulário para registrar Movimentos de Estoque em geral (Entrada/Saída).
    Usado na view simples (Movimento de Estoque Simples).
    """
    class Meta:
        model = MovimentoEstoque
        fields = ['produto', 'tipo_movimento', 'quantidade', 'observacao']
        widgets = {
            'tipo_movimento': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(status__in=['ATIVO', 'BAIXO', 'ZERADO'])
        self.fields['produto'].widget.attrs.update({'class': 'form-control'})

class EntradaProdutoEspecificoForm(forms.ModelForm):
    """
    Formulário para adicionar estoque a um produto específico (usado na tela de detalhe do produto).
    """
    class Meta:
        model = MovimentoEstoque
        fields = ['quantidade', 'observacao']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class EntradaEstoqueMultiplaForm(forms.Form):
    """
    Formulário base para o FormSet de Entrada de Estoque Múltipla. 
    Contém campos de custo e validade que agora existem no Model MovimentoEstoque.
    """
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.all().order_by('nome'),
        label="Produto",
        empty_label="Selecione um produto...",
        widget=forms.Select(attrs={'class': 'form-control select-produto'}),
        required=True
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qtd. a adicionar', 'min': '1', 'required': 'required'}),
        required=True
    )
    custo_unitario = forms.DecimalField(
        label="Custo Unitário (R$)",
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0.01', 'required': 'required'}),
        required=True
    )
    validade = forms.DateField(
        label="Validade (Opcional)",
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )