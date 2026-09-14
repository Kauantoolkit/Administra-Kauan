from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('O Email deve ser fornecido'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """Usuário do sistema. O papel define o que ele pode fazer."""

    PAPEL_CHOICES = (
        ('PROPRIETARIO', 'Proprietário'),
        ('GERENTE', 'Gerente'),
        ('OPERADOR', 'Operador de Caixa'),
        ('ESTOQUISTA', 'Estoquista'),
    )

    username = None
    email = models.EmailField(_('endereço de email'), unique=True)
    nome = models.CharField(_('nome completo'), max_length=255, blank=True)
    cpf = models.CharField(_('CPF'), max_length=14, unique=True, null=True, blank=True)
    papel = models.CharField(
        _('papel'), max_length=20, choices=PAPEL_CHOICES, default='OPERADOR'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']
    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def pode_gerenciar(self):
        """Acesso a cadastros sensíveis, relatórios e configuração."""
        return self.is_superuser or self.papel in ('PROPRIETARIO', 'GERENTE')


class ConfiguracaoLoja(models.Model):
    """
    Identidade e regras da loja. Registro único (singleton), usado para
    revender o mesmo sistema para lojas diferentes sem tocar no código.
    """

    nome_loja = models.CharField(max_length=120, default='Administra')
    slogan = models.CharField(max_length=160, blank=True, default='Sistema de Gestão')
    cnpj = models.CharField(max_length=18, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='loja/', blank=True, null=True)
    cor_primaria = models.CharField(max_length=7, default='#1570EF')
    simbolo_moeda = models.CharField(max_length=5, default='R$')
    permite_estoque_negativo = models.BooleanField(
        default=False,
        help_text='Se marcado, permite vender sem saldo em estoque.',
    )
    baixa_estoque_em_orcamento = models.BooleanField(
        default=False,
        help_text='Se marcado, orçamentos também reservam estoque.',
    )

    class Meta:
        verbose_name = 'Configuração da Loja'
        verbose_name_plural = 'Configuração da Loja'

    def __str__(self):
        return self.nome_loja

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obter(cls):
        config, _criada = cls.objects.get_or_create(pk=1)
        return config


class Categoria(models.Model):
    IMAGENS_PADRAO = {
        'Alimentos': 'categorias/alimentos.png',
        'Limpeza': 'categorias/limpeza.png',
        'Higiene': 'categorias/higiene.png',
        'Bebidas': 'categorias/bebidas.png',
        'Eletrônicos': 'categorias/eletronicos.png',
        'Farmácia': 'categorias/farmacia.png',
    }

    nome = models.CharField(max_length=100, unique=True)
    imagem_categoria = models.ImageField(
        upload_to='categorias/', blank=True, null=True,
        verbose_name='Imagem Padrão da Categoria',
    )

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nome']

    def save(self, *args, **kwargs):
        if not self.imagem_categoria:
            self.imagem_categoria = self.IMAGENS_PADRAO.get(
                self.nome, 'categorias/default.png'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class UnidadeMedida(models.TextChoices):
    """Unidades suportadas para venda e para controle de estoque."""

    UNIDADE = 'UN', 'Unidade (un)'
    PECA = 'PC', 'Peça (pç)'
    CAIXA = 'CX', 'Caixa (cx)'
    PACOTE = 'PCT', 'Pacote (pct)'
    DUZIA = 'DZ', 'Dúzia (dz)'
    QUILOGRAMA = 'KG', 'Quilograma (kg)'
    GRAMA = 'G', 'Grama (g)'
    LITRO = 'L', 'Litro (L)'
    MILILITRO = 'ML', 'Mililitro (mL)'
    METRO = 'M', 'Metro (m)'
    CENTIMETRO = 'CM', 'Centímetro (cm)'
    METRO_QUADRADO = 'M2', 'Metro quadrado (m²)'
    METRO_CUBICO = 'M3', 'Metro cúbico (m³)'
    HORA = 'H', 'Hora (h)'


# Unidades que aceitam quantidade fracionada (0,750 kg / 2,5 m).
UNIDADES_FRACIONADAS = {
    UnidadeMedida.QUILOGRAMA, UnidadeMedida.GRAMA,
    UnidadeMedida.LITRO, UnidadeMedida.MILILITRO,
    UnidadeMedida.METRO, UnidadeMedida.CENTIMETRO,
    UnidadeMedida.METRO_QUADRADO, UnidadeMedida.METRO_CUBICO,
    UnidadeMedida.HORA,
}

# Casas decimais exibidas por unidade.
CASAS_DECIMAIS_POR_UNIDADE = {
    UnidadeMedida.QUILOGRAMA: 3,
    UnidadeMedida.GRAMA: 0,
    UnidadeMedida.LITRO: 3,
    UnidadeMedida.MILILITRO: 0,
    UnidadeMedida.METRO: 2,
    UnidadeMedida.CENTIMETRO: 1,
    UnidadeMedida.METRO_QUADRADO: 2,
    UnidadeMedida.METRO_CUBICO: 3,
    UnidadeMedida.HORA: 2,
}


class Produto(models.Model):
    """
    Produto vendável. A `unidade_medida` define como ele é vendido:
    por unidade inteira, por peso, por volume, por comprimento ou por hora.
    Produtos com grade (tamanho/cor) usam `ProdutoVariacao`.
    """

    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('ZERADO', 'Estoque Zerado'),
        ('BAIXO', 'Estoque Baixo'),
    )

    sku = models.CharField(max_length=50, unique=True, verbose_name='SKU (Código)')
    codigo_barras = models.CharField(
        max_length=64, blank=True, null=True, unique=True,
        verbose_name='Código de Barras (EAN/GTIN)',
    )
    nome = models.CharField(max_length=200, verbose_name='Nome do Produto')
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name='Marca')
    descricao = models.TextField(blank=True, null=True, verbose_name='Descrição Detalhada')

    unidade_medida = models.CharField(
        max_length=4, choices=UnidadeMedida.choices, default=UnidadeMedida.UNIDADE,
        verbose_name='Vendido por',
    )
    quantidade_minima_venda = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('1.000'),
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Quantidade mínima por venda',
        help_text='Ex.: 0,100 para vender a partir de 100 g.',
    )
    incremento_venda = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('1.000'),
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Incremento de venda',
        help_text='Passo permitido na quantidade. Ex.: 0,050 para múltiplos de 50 g.',
    )

    quantidade_minima_alerta = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('5.000'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Qtd. Mínima para Alerta',
    )
    imagem = models.ImageField(
        upload_to='produtos/', blank=True, null=True, verbose_name='Imagem do Produto'
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Categoria',
    )
    custo = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Preço de Custo',
    )
    venda = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Preço de Venda',
    )
    quantidade_estoque = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0.000'),
        verbose_name='Quantidade em Estoque',
    )
    controla_estoque = models.BooleanField(
        default=True,
        help_text='Desmarque para serviços e itens sem controle de saldo.',
    )
    ativo = models.BooleanField(default=True, verbose_name='Disponível para venda')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='ATIVO', verbose_name='Status'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome']),
            models.Index(fields=['sku']),
            models.Index(fields=['codigo_barras']),
        ]

    def __str__(self):
        return f'{self.nome} ({self.sku})'

    # ---------- Regras de unidade ----------

    @property
    def aceita_fracao(self):
        return self.unidade_medida in UNIDADES_FRACIONADAS

    @property
    def casas_decimais(self):
        return CASAS_DECIMAIS_POR_UNIDADE.get(self.unidade_medida, 0)

    @property
    def sigla_unidade(self):
        """Sigla curta para exibição: kg, un, m²..."""
        return {
            UnidadeMedida.UNIDADE: 'un', UnidadeMedida.PECA: 'pç',
            UnidadeMedida.CAIXA: 'cx', UnidadeMedida.PACOTE: 'pct',
            UnidadeMedida.DUZIA: 'dz', UnidadeMedida.QUILOGRAMA: 'kg',
            UnidadeMedida.GRAMA: 'g', UnidadeMedida.LITRO: 'L',
            UnidadeMedida.MILILITRO: 'mL', UnidadeMedida.METRO: 'm',
            UnidadeMedida.CENTIMETRO: 'cm', UnidadeMedida.METRO_QUADRADO: 'm²',
            UnidadeMedida.METRO_CUBICO: 'm³', UnidadeMedida.HORA: 'h',
        }.get(self.unidade_medida, self.unidade_medida.lower())

    @property
    def rotulo_preco(self):
        """Ex.: 'R$ 24,90 / kg'."""
        return f'{self.venda} / {self.sigla_unidade}'

    def formatar_quantidade(self, quantidade):
        """Formata uma quantidade no padrão brasileiro, já com a sigla."""
        if quantidade is None:
            quantidade = Decimal('0')
        casas = self.casas_decimais
        valor = Decimal(quantidade).quantize(
            Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP
        )
        texto = f'{valor:.{casas}f}'.replace('.', ',')
        return f'{texto} {self.sigla_unidade}'

    def normalizar_quantidade(self, quantidade):
        """
        Arredonda a quantidade para as casas decimais da unidade e valida
        mínimo e incremento. Levanta ValidationError quando inválida.
        """
        if quantidade is None:
            raise ValidationError('Informe a quantidade.')
        quantidade = Decimal(str(quantidade))

        if quantidade <= 0:
            raise ValidationError('A quantidade deve ser maior que zero.')

        # A fração é recusada ANTES do arredondamento: do contrário "1,5 un"
        # seria silenciosamente convertido em "2 un" e cobrado a mais.
        if not self.aceita_fracao and quantidade != quantidade.to_integral_value():
            raise ValidationError(
                f'"{self.nome}" é vendido por {self.sigla_unidade} e não aceita '
                f'quantidade fracionada.'
            )

        casas = self.casas_decimais
        quantidade = quantidade.quantize(
            Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP
        )

        if quantidade < self.quantidade_minima_venda:
            raise ValidationError(
                f'Quantidade mínima para "{self.nome}" é '
                f'{self.formatar_quantidade(self.quantidade_minima_venda)}.'
            )

        incremento = self.incremento_venda or Decimal('0')
        if incremento > 0:
            resto = (quantidade - self.quantidade_minima_venda) % incremento
            if resto != 0:
                raise ValidationError(
                    f'"{self.nome}" deve ser vendido em múltiplos de '
                    f'{self.formatar_quantidade(incremento)}.'
                )

        return quantidade

    def calcular_subtotal(self, quantidade):
        """Preço final da quantidade informada, arredondado ao centavo."""
        bruto = Decimal(str(quantidade)) * self.venda
        return bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # ---------- Estoque ----------

    @property
    def valor_total_estoque(self):
        return (self.quantidade_estoque * self.custo).quantize(Decimal('0.01'))

    @property
    def preco_venda_total(self):
        return (self.quantidade_estoque * self.venda).quantize(Decimal('0.01'))

    @property
    def estoque_formatado(self):
        return self.formatar_quantidade(self.quantidade_estoque)

    @property
    def tem_variacoes(self):
        return self.variacoes.exists()

    @property
    def get_imagem_url(self):
        if self.imagem and self.imagem.name:
            return self.imagem.url
        if self.categoria and self.categoria.imagem_categoria and self.categoria.imagem_categoria.name:
            return self.categoria.imagem_categoria.url
        return '/static/img/default-product.png'

    def _atualizar_status(self):
        if not self.ativo:
            self.status = 'INATIVO'
        elif not self.controla_estoque:
            self.status = 'ATIVO'
        elif self.quantidade_estoque <= 0:
            self.status = 'ZERADO'
        elif self.quantidade_estoque <= (self.quantidade_minima_alerta or 0):
            self.status = 'BAIXO'
        else:
            self.status = 'ATIVO'

    def clean(self):
        super().clean()
        if not self.aceita_fracao:
            for campo in ('quantidade_minima_venda', 'incremento_venda'):
                valor = getattr(self, campo) or Decimal('0')
                if valor != valor.to_integral_value():
                    raise ValidationError({
                        campo: 'Produtos vendidos por unidade não aceitam valor fracionado.'
                    })

    def save(self, *args, **kwargs):
        self._atualizar_status()
        super().save(*args, **kwargs)


class ProdutoVariacao(models.Model):
    """
    Grade do produto (tamanho, cor, sabor...). Usada por lojas de roupas,
    calçados e afins. Cada variação tem SKU e estoque próprios; o preço
    pode ser herdado do produto ou sobrescrito.
    """

    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name='variacoes'
    )
    sku = models.CharField(max_length=60, unique=True, verbose_name='SKU da Variação')
    codigo_barras = models.CharField(max_length=64, blank=True, null=True)
    tamanho = models.CharField(
        max_length=30, blank=True, verbose_name='Tamanho',
        help_text='Ex.: P, M, G, 38, 42.',
    )
    cor = models.CharField(max_length=30, blank=True, verbose_name='Cor')
    descricao_extra = models.CharField(max_length=60, blank=True)
    preco_venda = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Preço próprio (opcional)',
        help_text='Deixe em branco para usar o preço do produto.',
    )
    quantidade_estoque = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0.000')
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Variação de Produto'
        verbose_name_plural = 'Variações de Produto'
        ordering = ['produto__nome', 'tamanho', 'cor']
        constraints = [
            models.UniqueConstraint(
                fields=['produto', 'tamanho', 'cor', 'descricao_extra'],
                name='variacao_unica_por_produto',
            )
        ]

    def __str__(self):
        return f'{self.produto.nome} — {self.rotulo}'

    @property
    def rotulo(self):
        partes = [p for p in (self.tamanho, self.cor, self.descricao_extra) if p]
        return ' / '.join(partes) or self.sku

    @property
    def preco_efetivo(self):
        return self.preco_venda if self.preco_venda is not None else self.produto.venda


class MovimentoEstoque(models.Model):
    """
    Lançamento de estoque. É a única porta de entrada e saída de saldo:
    o saldo do produto (ou da variação) nunca é editado direto.
    """

    TIPO_MOVIMENTO_CHOICES = (
        ('ENTRADA', 'Entrada (Compra/Ajuste Positivo)'),
        ('SAIDA', 'Saída (Venda/Ajuste Negativo)'),
    )

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, verbose_name='Produto')
    variacao = models.ForeignKey(
        ProdutoVariacao, on_delete=models.CASCADE, null=True, blank=True,
        related_name='movimentos', verbose_name='Variação',
    )
    tipo_movimento = models.CharField(
        max_length=10, choices=TIPO_MOVIMENTO_CHOICES, verbose_name='Tipo de Movimento'
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Quantidade',
    )
    data_movimento = models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora')
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Custo Unitário',
    )
    validade = models.DateField(null=True, blank=True, verbose_name='Data de Validade')
    usuario = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Usuário',
    )

    class Meta:
        verbose_name = 'Movimento de Estoque'
        verbose_name_plural = 'Movimentos de Estoque'
        ordering = ['-data_movimento']
        indexes = [models.Index(fields=['produto', '-data_movimento'])]

    def __str__(self):
        alvo = self.variacao.rotulo if self.variacao else self.produto.nome
        return f'{self.tipo_movimento} de {self.quantidade} {alvo}'

    @property
    def saldo_disponivel(self):
        alvo = self.variacao or self.produto
        return alvo.quantidade_estoque

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not is_new:
            super().save(*args, **kwargs)
            return

        with transaction.atomic():
            produto = Produto.objects.select_for_update().get(pk=self.produto_id)
            variacao = None
            if self.variacao_id:
                variacao = ProdutoVariacao.objects.select_for_update().get(
                    pk=self.variacao_id
                )

            if self.tipo_movimento == 'SAIDA' and produto.controla_estoque:
                disponivel = variacao.quantidade_estoque if variacao else produto.quantidade_estoque
                config = ConfiguracaoLoja.obter()
                if not config.permite_estoque_negativo and self.quantidade > disponivel:
                    alvo = variacao.rotulo if variacao else produto.nome
                    raise ValidationError(
                        f'Estoque insuficiente para "{alvo}". '
                        f'Disponível: {produto.formatar_quantidade(disponivel)}, '
                        f'solicitado: {produto.formatar_quantidade(self.quantidade)}.'
                    )

            super().save(*args, **kwargs)

            if not produto.controla_estoque:
                return

            delta = self.quantidade if self.tipo_movimento == 'ENTRADA' else -self.quantidade

            if variacao is not None:
                ProdutoVariacao.objects.filter(pk=variacao.pk).update(
                    quantidade_estoque=F('quantidade_estoque') + delta
                )
            Produto.objects.filter(pk=produto.pk).update(
                quantidade_estoque=F('quantidade_estoque') + delta
            )

            produto.refresh_from_db()
            if self.tipo_movimento == 'ENTRADA' and self.custo_unitario is not None:
                produto.custo = self.custo_unitario
            produto.save()


class Fornecedor(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
    ]

    nome_fantasia = models.CharField(_('nome fantasia'), max_length=255)
    categoria = models.CharField(
        _('categoria'), max_length=255, help_text='Ex: Eletrônicos e Componentes'
    )
    cnpj = models.CharField(
        _('CNPJ'), max_length=18, unique=True, help_text='Formato: 00.000.000/0000-00'
    )
    contato_principal = models.CharField(
        _('contato principal'), max_length=255, help_text='Nome da pessoa de contato'
    )
    email = models.EmailField(_('email'))
    telefone = models.CharField(
        _('telefone'), max_length=20, help_text='Formato: (00) 00000-0000'
    )
    status = models.CharField(
        _('status'), max_length=10, choices=STATUS_CHOICES, default='ativo'
    )

    data_cadastro = models.DateTimeField(_('data de cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('data de atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Fornecedor')
        verbose_name_plural = _('Fornecedores')
        ordering = ['nome_fantasia']

    def __str__(self):
        return self.nome_fantasia
