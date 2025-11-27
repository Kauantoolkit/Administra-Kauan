from django.db import models
from contas.models import CustomUser
from django.utils import timezone


class Funcionario(models.Model):
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("ferias", "Férias"),
        ("inativo", "Inativo"),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    cargo = models.CharField(max_length=100)

    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    salario = models.DecimalField(max_digits=10, decimal_places=2)
    data_admissao = models.DateField(default=timezone.now)
    data_atualizacao = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ativo")

    foto_base64 = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} ({self.cargo})"

    @property
    def codigo(self):
        if self.id is None:
            return "Novo"
        return f"F{self.id:03d}"
