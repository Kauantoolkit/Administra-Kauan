from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('pendente', 'Pendente'),
    )

    nome = models.CharField(max_length=150, verbose_name='Nome Completo')
    cpf = models.CharField(max_length=18, unique=True, verbose_name='CPF/CNPJ')
    email = models.EmailField(unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True)
    cidade = models.CharField(max_length=100, blank=True)

    ultima_compra = models.DateField(null=True, blank=True, verbose_name='Última Compra')
    data_cadastro = models.DateTimeField(default=timezone.now, verbose_name='Data de Cadastro')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ativo')
    valor_total_comprado = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']
        indexes = [models.Index(fields=['nome']), models.Index(fields=['cpf'])]

    def __str__(self):
        return self.nome


class LogAcao(models.Model):
    ACOES = (
        ('CRIACAO', 'Criação'),
        ('ALTERACAO', 'Alteração'),
        ('EXCLUSAO', 'Exclusão'),
    )

    ENTIDADES = (
        ('CLIENTE', 'Cliente'),
        ('PRODUTO', 'Produto'),
        ('ESTOQUE', 'Estoque'),
        ('VENDA', 'Venda'),
        ('FORNECEDOR', 'Fornecedor'),
        ('FUNCIONARIO', 'Funcionário'),
        ('CONFIGURACAO', 'Configuração'),
    )

    entidade = models.CharField(max_length=20, choices=ENTIDADES)
    entidade_id = models.IntegerField(null=True, blank=True)
    acao = models.CharField(max_length=20, choices=ACOES)
    descricao = models.TextField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    datahora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Ação'
        verbose_name_plural = 'Logs de Ações'
        ordering = ['-datahora']
        indexes = [models.Index(fields=['-datahora'])]

    def __str__(self):
        return f'{self.entidade} - {self.acao} - {self.datahora}'
