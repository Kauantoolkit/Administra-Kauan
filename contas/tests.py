"""Testes de acesso: criação do administrador e login por e-mail."""

import os
from unittest import mock

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase

CustomUser = get_user_model()


def com_ambiente(**variaveis):
    return mock.patch.dict(os.environ, variaveis, clear=False)


class CriarAdminTests(TestCase):
    def test_cria_administrador(self):
        with com_ambiente(ADMIN_EMAIL='dono@loja.com', ADMIN_SENHA='SenhaBoa123'):
            call_command('criar_admin')
        usuario = CustomUser.objects.get(email='dono@loja.com')
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.check_password('SenhaBoa123'))

    def test_email_com_maiusculas_e_normalizado(self):
        with com_ambiente(ADMIN_EMAIL='  Dono@Loja.COM ', ADMIN_SENHA='SenhaBoa123'):
            call_command('criar_admin')
        self.assertTrue(CustomUser.objects.filter(email='dono@loja.com').exists())

    def test_senha_curta_falha_o_deploy(self):
        # Antes isto apenas avisava e seguia: o sistema subia sem nenhum
        # usuario e era impossivel entrar, sem indicacao do motivo.
        with com_ambiente(ADMIN_EMAIL='dono@loja.com', ADMIN_SENHA='1234'):
            with self.assertRaises(CommandError):
                call_command('criar_admin')
        self.assertFalse(CustomUser.objects.exists())

    def test_rodar_duas_vezes_atualiza_a_senha(self):
        with com_ambiente(ADMIN_EMAIL='dono@loja.com', ADMIN_SENHA='SenhaBoa123'):
            call_command('criar_admin')
        with com_ambiente(ADMIN_EMAIL='dono@loja.com', ADMIN_SENHA='OutraSenha456'):
            call_command('criar_admin')
        self.assertEqual(CustomUser.objects.filter(email='dono@loja.com').count(), 1)
        self.assertTrue(
            CustomUser.objects.get(email='dono@loja.com').check_password('OutraSenha456')
        )

    def test_sem_variaveis_nao_faz_nada(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            call_command('criar_admin')
        self.assertFalse(CustomUser.objects.exists())


class LoginPorEmailTests(TestCase):
    def setUp(self):
        self.usuario = CustomUser.objects.create_user(
            email='dono@loja.com', password='SenhaBoa123', nome='Dono'
        )

    def test_login_ignora_maiusculas(self):
        # A falha relatada: e-mail gravado em minusculas, digitado com
        # maiuscula no login, e o backend padrao comparava de forma exata.
        for digitado in ('dono@loja.com', 'Dono@Loja.com', 'DONO@LOJA.COM'):
            with self.subTest(digitado=digitado):
                self.assertIsNotNone(
                    authenticate(username=digitado, password='SenhaBoa123')
                )

    def test_login_ignora_espacos_em_volta(self):
        self.assertIsNotNone(
            authenticate(username='  dono@loja.com  ', password='SenhaBoa123')
        )

    def test_senha_errada_continua_recusada(self):
        self.assertIsNone(authenticate(username='dono@loja.com', password='errada'))

    def test_usuario_inexistente_recusado(self):
        self.assertIsNone(authenticate(username='ninguem@loja.com', password='x'))

    def test_usuario_inativo_recusado(self):
        self.usuario.is_active = False
        self.usuario.save()
        self.assertIsNone(
            authenticate(username='dono@loja.com', password='SenhaBoa123')
        )

    def test_login_pela_tela_com_email_em_maiusculas(self):
        cliente = Client(SERVER_NAME='localhost')
        resposta = cliente.post(
            '/contas/login/',
            {'username': 'Dono@Loja.COM', 'password': 'SenhaBoa123'},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers['Location'], '/contas/dashboard/')

    def test_fluxo_completo_admin_criado_e_login(self):
        CustomUser.objects.all().delete()
        with com_ambiente(ADMIN_EMAIL='Kauan@Exemplo.com', ADMIN_SENHA='SenhaDemo123'):
            call_command('criar_admin')

        cliente = Client(SERVER_NAME='localhost')
        resposta = cliente.post(
            '/contas/login/',
            {'username': 'Kauan@Exemplo.com', 'password': 'SenhaDemo123'},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(
            cliente.get('/contas/dashboard/').status_code, 200
        )
