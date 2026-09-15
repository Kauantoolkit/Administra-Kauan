"""
Imprime o estado real de acesso na partida do serviço.

Existe porque no plano gratuito não há shell: sem isto, quando o login falha,
não há como distinguir "o administrador não foi criado" de "foi criado com
outro e-mail" ou de "existe e a senha é outra". Não imprime senha alguma —
apenas se a variável veio preenchida e o comprimento dela.
"""

import os

from django.core.management.base import BaseCommand

from contas.models import CustomUser


class Command(BaseCommand):
    help = 'Mostra usuários existentes e o estado das variáveis de acesso.'

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL')
        senha = os.environ.get('ADMIN_SENHA')

        linhas = [
            '',
            '=' * 62,
            'DIAGNÓSTICO DE ACESSO',
            '=' * 62,
            f'ADMIN_EMAIL definido : {"SIM" if email else "NÃO"}'
            + (f'  -> "{email}"' if email else ''),
            f'ADMIN_SENHA definida : {"SIM" if senha else "NÃO"}'
            + (f'  ({len(senha)} caracteres)' if senha else ''),
            '-' * 62,
        ]

        usuarios = CustomUser.objects.order_by('pk')
        if not usuarios:
            linhas.append('NENHUM usuário no banco — não há como entrar.')
        else:
            linhas.append(f'{usuarios.count()} usuário(s) no banco:')
            for u in usuarios:
                linhas.append(
                    f'  - "{u.email}" | ativo={u.is_active} '
                    f'| superuser={u.is_superuser} '
                    f'| senha_utilizavel={u.has_usable_password()}'
                )

        if email:
            confere = CustomUser.objects.filter(email__iexact=email.strip()).first()
            linhas.append('-' * 62)
            if confere is None:
                linhas.append(
                    f'ATENÇÃO: nenhum usuário corresponde a ADMIN_EMAIL '
                    f'("{email}").'
                )
            elif senha:
                ok = confere.check_password(senha)
                linhas.append(
                    f'Senha de ADMIN_SENHA confere com o usuário '
                    f'"{confere.email}": {"SIM" if ok else "NÃO"}'
                )

        linhas += ['=' * 62, '']
        self.stdout.write('\n'.join(linhas))
