"""
Autenticação por e-mail sem diferenciar maiúsculas de minúsculas.

O e-mail é gravado normalizado em minúsculas, mas o backend padrão do Django
compara de forma exata. Quem cadastrasse "Kauan@Gmail.com" e digitasse o mesmo
texto no login não conseguia entrar, porque o registro salvo era
"kauan@gmail.com". Endereço de e-mail não distingue caixa na prática, então a
comparação aqui usa `iexact`.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = username or kwargs.get(User.USERNAME_FIELD)
        if email is None or password is None:
            return None

        try:
            usuario = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            # Executa o hasher mesmo sem usuário, para que o tempo de resposta
            # não revele quais e-mails existem na base.
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Base legada com o mesmo e-mail em caixas diferentes: usa o mais
            # antigo, que é o cadastro original.
            usuario = User.objects.filter(email__iexact=email.strip()).order_by('pk').first()

        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
