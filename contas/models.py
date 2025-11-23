from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager

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


class Fornecedor(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
    ]
    
    nome_fantasia = models.CharField(_('nome fantasia'), max_length=255)
    categoria = models.CharField(_('categoria'), max_length=255, help_text='Ex: Eletrônicos e Componentes')
    cnpj = models.CharField(_('CNPJ'), max_length=18, unique=True, help_text='Formato: 00.000.000/0000-00')
    contato_principal = models.CharField(_('contato principal'), max_length=255, help_text='Nome da pessoa de contato')
    email = models.EmailField(_('email'))
    telefone = models.CharField(_('telefone'), max_length=20, help_text='Formato: (00) 00000-0000')
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='ativo')
    
    data_cadastro = models.DateTimeField(_('data de cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('data de atualização'), auto_now=True)
    
    class Meta:
        verbose_name = _('Fornecedor')
        verbose_name_plural = _('Fornecedores')
        ordering = ['nome_fantasia']
    
    def __str__(self):
        return self.nome_fantasia