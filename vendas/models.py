from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from clientes.models import Cliente
from contas.models import Produto, ProdutoVariacao


class Venda(models.Model):
    STATUS_CHOICES = (
        ('orcamento', 'Orçamento'),
        ('fechada', 'Venda Fechada'),
        ('cancelada', 'Cancelada'),
    )

    FORMA_PAGAMENTO_CHOICES = (
        ('dinheiro', 'Dinheiro'),
        ('pix', 'PIX'),
        ('debito', 'Cartão de Débito'),
        ('credito', 'Cartão de Crédito'),
        ('boleto', 'Boleto'),
        ('crediario', 'Crediário / Fiado'),
    )

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name='vendas',
        null=True, blank=True,
        help_text='Opcional: venda de balcão pode não ter cliente identificado.',
    )
    data_venda = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    desconto = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Desconto (R$)',
    )
    acrescimo = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Acréscimo (R$)',
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='orcamento')
    forma_pagamento = models.CharField(
        max_length=20, choices=FORMA_PAGAMENTO_CHOICES, default='dinheiro'
    )
    observacoes = models.TextField(blank=True, null=True)
    estoque_baixado = models.BooleanField(
        default=False,
        help_text='Indica se esta venda já retirou os itens do estoque.',
    )
    operador = models.ForeignKey(
        'contas.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vendas_registradas',
    )

    class Meta:
        ordering = ['-data_venda']
        indexes = [models.Index(fields=['-data_venda', 'status'])]

    def __str__(self):
        nome = self.cliente.nome if self.cliente else 'Consumidor final'
        return f'Venda #{self.id} - {nome}'

    @property
    def nome_cliente(self):
        return self.cliente.nome if self.cliente else 'Consumidor final'

    def calcular_totais(self, salvar=True):
        """Recalcula subtotal e total a partir dos itens. Fonte única da verdade."""
        subtotal = sum(
            (item.subtotal for item in self.itens.all()), Decimal('0.00')
        )
        self.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = self.subtotal - (self.desconto or 0) + (self.acrescimo or 0)
        self.total = max(total, Decimal('0.00')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        if salvar:
            self.save(update_fields=['subtotal', 'total'])
        return self.total

    def clean(self):
        super().clean()
        if self.desconto and self.subtotal and self.desconto > self.subtotal:
            raise ValidationError(
                {'desconto': 'O desconto não pode ser maior que o subtotal.'}
            )


class ItemVenda(models.Model):
    """
    Item de uma venda. A quantidade é decimal para suportar venda por peso,
    volume ou comprimento; o preço unitário é congelado no momento da venda.
    """

    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    variacao = models.ForeignKey(
        ProdutoVariacao, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='Variação (tamanho/cor)',
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('1.000'),
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    unidade_medida = models.CharField(
        max_length=4, blank=True,
        help_text='Unidade registrada no momento da venda.',
    )
    preco_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))]
    )
    desconto_item = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
    )

    class Meta:
        verbose_name = 'Item da Venda'
        verbose_name_plural = 'Itens da Venda'

    def __str__(self):
        return f'{self.quantidade_formatada} de {self.produto.nome}'

    @property
    def subtotal(self):
        bruto = (self.quantidade or 0) * (self.preco_unitario or 0)
        liquido = Decimal(bruto) - (self.desconto_item or 0)
        return max(liquido, Decimal('0.00')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    @property
    def quantidade_formatada(self):
        return self.produto.formatar_quantidade(self.quantidade)

    @property
    def descricao_completa(self):
        if self.variacao:
            return f'{self.produto.nome} ({self.variacao.rotulo})'
        return self.produto.nome

    def clean(self):
        super().clean()
        if not self.produto_id:
            return

        # Valida fração, mínimo e incremento conforme a unidade do produto.
        self.quantidade = self.produto.normalizar_quantidade(self.quantidade)

        if self.variacao_id and self.variacao.produto_id != self.produto_id:
            raise ValidationError(
                {'variacao': 'A variação escolhida não pertence a este produto.'}
            )
        if self.produto.tem_variacoes and not self.variacao_id:
            raise ValidationError(
                {'variacao': f'Escolha uma variação para "{self.produto.nome}".'}
            )

    def save(self, *args, **kwargs):
        if not self.unidade_medida and self.produto_id:
            self.unidade_medida = self.produto.unidade_medida
        if self.preco_unitario is None and self.produto_id:
            self.preco_unitario = (
                self.variacao.preco_efetivo if self.variacao_id else self.produto.venda
            )
        super().save(*args, **kwargs)
