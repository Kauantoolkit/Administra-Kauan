import os
from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager
from django.db.models import F

def get_default_image_path():
    return ''

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('O Email deve ser fornecido'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None 
    email = models.EmailField(_('endereço de email'), unique=True)
    nome = models.CharField(_('nome completo'), max_length=255, blank=True)
    cpf = models.CharField(_('CPF'), max_length=14, unique=True, null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome'] 
    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    imagem_categoria = models.ImageField(upload_to='categorias/', blank=True, null=True, verbose_name="Imagem Padrão da Categoria")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome

class Produto(models.Model):
    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('ZERADO', 'Estoque Zerado'),
        ('BAIXO', 'Estoque Baixo'),
    )

    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU (Código)")
    nome = models.CharField(max_length=200, verbose_name="Nome do Produto")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição Detalhada")
    quantidade_minima_alerta = models.IntegerField(default=5, verbose_name="Qtd. Mínima para Alerta")
    unidade_medida = models.CharField(max_length=10, default='UN', verbose_name="Unidade de Medida")
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True, verbose_name="Imagem do Produto")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoria")
    custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Custo")
    venda = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    quantidade_estoque = models.IntegerField(default=0, verbose_name="Quantidade em Estoque")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVO', verbose_name="Status")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.sku})"

    @property
    def valor_total_estoque(self):
        return self.quantidade_estoque * self.custo

    @property
    def preco_venda_total(self):
        return self.quantidade_estoque * self.venda

    @property
    def get_imagem_url(self):
        if self.imagem and self.imagem.name:
            return self.imagem.url
        elif self.categoria and self.categoria.imagem_categoria and self.categoria.imagem_categoria.name:
            return self.categoria.imagem_categoria.url
        return '/static/img/default-product.png'

    def _atualizar_status(self):
        limite = self.quantidade_minima_alerta if self.quantidade_minima_alerta is not None and self.quantidade_minima_alerta > 0 else 5
        
        if self.quantidade_estoque <= 0:
            self.status = 'ZERADO'
        elif self.quantidade_estoque <= limite:
            self.status = 'BAIXO'
        else:
            self.status = 'ATIVO'

    def save(self, *args, **kwargs):
        self._atualizar_status()
        super().save(*args, **kwargs)

class MovimentoEstoque(models.Model):
    TIPO_MOVIMENTO_CHOICES = (
        ('ENTRADA', 'Entrada (Compra/Ajuste Positivo)'),
        ('SAIDA', 'Saída (Venda/Ajuste Negativo)'),
    )
    
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, verbose_name="Produto")
    tipo_movimento = models.CharField(max_length=10, choices=TIPO_MOVIMENTO_CHOICES, verbose_name="Tipo de Movimento")
    quantidade = models.IntegerField(verbose_name="Quantidade")
    data_movimento = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    
    # NOVOS CAMPOS ADICIONADOS PARA A ENTRADA MÚLTIPLA
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Custo Unitário")
    validade = models.DateField(null=True, blank=True, verbose_name="Data de Validade")
    usuario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário")

    class Meta:
        verbose_name = "Movimento de Estoque"
        verbose_name_plural = "Movimentos de Estoque"
        ordering = ['-data_movimento']

    def __str__(self):
        return f"{self.tipo_movimento} de {self.quantidade}x {self.produto.nome}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            if is_new:
                produto = self.produto
                if self.tipo_movimento == 'ENTRADA':
                    # Usamos update() para garantir que a atualização da quantidade seja segura
                    Produto.objects.filter(pk=produto.pk).update(quantidade_estoque=F('quantidade_estoque') + self.quantidade)
                elif self.tipo_movimento == 'SAIDA':
                    Produto.objects.filter(pk=produto.pk).update(quantidade_estoque=F('quantidade_estoque') - self.quantidade)
                    
                # Após a atualização da quantidade (segura), re-buscamos o produto 
                # e chamamos save() novamente para atualizar o status (ATIVO, BAIXO, ZERADO)
                produto.refresh_from_db()
                
                # Se for ENTRADA e o custo unitário for fornecido, atualizamos o custo do produto
                if self.tipo_movimento == 'ENTRADA' and self.custo_unitario is not None:
                    produto.custo = self.custo_unitario
                
                produto.save() # Isso forçará a atualização do status