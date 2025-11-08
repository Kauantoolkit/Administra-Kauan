from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

# Importante: Precisamos de um Manager personalizado 
# para lidar com a criação de usuários via email.
from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
    """
    Manager de usuário personalizado onde o email é o identificador
    único para autenticação em vez de usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Cria e salva um usuário com o email e senha fornecidos.
        """
        if not email:
            raise ValueError(_('O Email deve ser fornecido'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Cria e salva um Superusuário com o email e senha fornecidos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Modelo de Usuário Personalizado.
    Herda de AbstractUser e remove o campo username.
    Usa 'email' como o campo de login principal.
    Adiciona os campos 'nome' e 'cpf' da sua imagem.
    """
    # Remove o campo username padrão
    username = None 
    
    # Define email como único e o campo de login
    email = models.EmailField(_('endereço de email'), unique=True)
    
    # Adiciona os campos do seu formulário
    nome = models.CharField(_('nome completo'), max_length=255, blank=True)
    cpf = models.CharField(_('CPF'), max_length=14, unique=True, null=True, blank=True) # Max 14 para "000.000.000-00"

    # Define o campo que será usado para login
    USERNAME_FIELD = 'email'
    
    # Campos obrigatórios ao criar um superusuário (além de email e senha)
    REQUIRED_FIELDS = ['nome'] 

    # Informa ao Django para usar o CustomUserManager
    objects = CustomUserManager()

    # Campos que o AbstractUser já nos dá (e que vamos usar):
    # - password
    # - first_name, last_name (vamos usar 'nome' em vez disso)
    # - is_staff, is_active, is_superuser
    # - last_login, date_joined

    def __str__(self):
        return self.email