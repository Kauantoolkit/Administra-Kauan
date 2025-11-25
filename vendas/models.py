from django.db import models
from django.utils import timezone
from contas.models import Produto 
from clientes.models import Cliente 

class Venda(models.Model):
    STATUS_CHOICES = (
        ('orcamento', 'Orçamento'),
        ('fechada', 'Venda Fechada'),
        ('cancelada', 'Cancelada'),
    )
    
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='vendas')
    data_venda = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='orcamento')
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-data_venda']

    def __str__(self):
        return f"Venda #{self.id} - {self.cliente.nome}"

class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.IntegerField(default=1)
    
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    def subtotal(self):
        return self.quantidade * self.preco_unitario