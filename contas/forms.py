# em contas/forms.py

from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import CustomUser
from django import forms
from django.utils.translation import gettext_lazy as _

class CustomUserCreationForm(UserCreationForm):
    """
    Um formulário para criar novos usuários.
    Herda de UserCreationForm, que já cuida da senha e da confirmação.
    """

    # Precisamos redefinir o campo 'email' para garantir que ele seja
    # obrigatório e usado como o principal identificador.
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Obrigatório. Digite um endereço de e-mail válido.'
    )

    class Meta:
        # Informa ao formulário qual modelo usar
        model = CustomUser 

        # Quais campos do modelo devem aparecer no formulário?
        # UserCreationForm já inclui 'password' e 'password2' (confirmação)
        # Nós só precisamos adicionar os nossos.
        # O 'email' nós redefinimos acima para garantir que ele apareça
        # e seja obrigatório, mesmo que não estivesse em USERNAME_FIELD.
        fields = ('email', 'nome', 'cpf') 


class CustomUserChangeForm(UserChangeForm):
    """
    Um formulário para atualizar dados de usuários existentes
    (usado principalmente no /admin).
    """
    class Meta:
        model = CustomUser
        # Mostra os campos que podem ser editados no admin
        fields = ('email', 'nome', 'cpf', 'is_active', 'is_staff')

class EmailAuthenticationForm(AuthenticationForm):
    """
    Formulário de autenticação customizado para usar email em vez de username.
    """
    # Sobrescrevemos o campo 'username' padrão
    username = forms.EmailField(
        label=_("Email"), # O rótulo que o usuário verá
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'seu@email.com'})
    )