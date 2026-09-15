"""
Cria (ou atualiza a senha do) usuário administrador a partir de variáveis de
ambiente. Existe porque plataformas de deploy não dão acesso a um shell
interativo, onde normalmente se rodaria `createsuperuser`.

    ADMIN_EMAIL=... ADMIN_SENHA=... python manage.py criar_admin

Sem as variáveis definidas, não faz nada e sai com sucesso — assim pode ficar
no script de build sem quebrar quem instala de outro jeito.
"""

import os

from django.core.management.base import BaseCommand, CommandError

from contas.models import CustomUser


class Command(BaseCommand):
    help = 'Cria o administrador inicial a partir de ADMIN_EMAIL e ADMIN_SENHA.'

    def handle(self, *args, **options):
        email = (os.environ.get('ADMIN_EMAIL') or '').strip().lower()
        senha = os.environ.get('ADMIN_SENHA') or ''

        if not email or not senha:
            self.stdout.write(
                'ADMIN_EMAIL/ADMIN_SENHA não definidos — nenhum admin criado.'
            )
            return

        if len(senha) < 8:
            # Erro de verdade, e nao aviso: antes o deploy terminava "com
            # sucesso" e o sistema subia sem nenhum usuario, impossivel de
            # acessar e sem pista do motivo.
            raise CommandError(
                'ADMIN_SENHA tem menos de 8 caracteres — o administrador NÃO '
                'foi criado. Corrija a variável de ambiente e publique de novo.'
            )

        if '@' not in email:
            raise CommandError(f'ADMIN_EMAIL inválido: "{email}".')

        usuario = CustomUser.objects.filter(email__iexact=email).first()
        criado = usuario is None
        if criado:
            usuario = CustomUser(
                email=email,
                nome=os.environ.get('ADMIN_NOME', 'Administrador'),
            )
        usuario.set_password(senha)
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        usuario.papel = 'PROPRIETARIO'
        usuario.save()

        acao = 'criado' if criado else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Administrador {acao}: {usuario.email} — entre com este e-mail '
            f'(maiúsculas não importam) e a senha de ADMIN_SENHA.'
        ))
