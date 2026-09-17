"""
Permissões por papel.

O campo `papel` existia mas não barrava nada: um operador de caixa via a folha
salarial e podia apagar produtos. Cada teste aqui fixa uma dessas fronteiras.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase

from contas import permissoes as P
from contas.models import Produto

CustomUser = get_user_model()

# (papel, url, deve_ter_acesso)
MATRIZ = [
    # Operador de caixa: vende e atende cliente, e so.
    ('OPERADOR', '/vendas/criar/', True),
    ('OPERADOR', '/vendas/', True),
    ('OPERADOR', '/clientes/', True),
    ('OPERADOR', '/clientes/novo/', True),
    ('OPERADOR', '/contas/estoque/', True),
    ('OPERADOR', '/funcionarios/', False),          # salarios
    ('OPERADOR', '/contas/relatorios/', False),     # lucro
    ('OPERADOR', '/contas/produtos/novo/', False),
    ('OPERADOR', '/contas/estoque/entrada/', False),
    ('OPERADOR', '/clientes/historico/', False),
    ('OPERADOR', '/contas/fornecedores/', False),

    # Estoquista: produto e fornecedor, sem vender nem ver dinheiro.
    ('ESTOQUISTA', '/contas/estoque/', True),
    ('ESTOQUISTA', '/contas/produtos/novo/', True),
    ('ESTOQUISTA', '/contas/estoque/entrada/', True),
    ('ESTOQUISTA', '/contas/fornecedores/', True),
    ('ESTOQUISTA', '/vendas/criar/', False),
    ('ESTOQUISTA', '/funcionarios/', False),
    ('ESTOQUISTA', '/contas/relatorios/', False),
    ('ESTOQUISTA', '/clientes/', False),

    # Gerente: tudo do dia a dia.
    ('GERENTE', '/contas/relatorios/', True),
    ('GERENTE', '/funcionarios/', True),
    ('GERENTE', '/vendas/criar/', True),
    ('GERENTE', '/clientes/historico/', True),
    ('GERENTE', '/contas/estoque/entrada/', True),

    # Proprietario: tudo.
    ('PROPRIETARIO', '/contas/relatorios/', True),
    ('PROPRIETARIO', '/funcionarios/', True),
    ('PROPRIETARIO', '/vendas/criar/', True),
]


def criar_usuario(papel, email=None):
    usuario = CustomUser.objects.create_user(
        email=email or f'{papel.lower()}@loja.com',
        password='SenhaForte123',
        nome=papel.title(),
    )
    usuario.papel = papel
    usuario.save()
    return usuario


class MatrizDeAcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_inicial', verbosity=0)

    def test_matriz_de_acesso(self):
        for papel, url, permitido in MATRIZ:
            with self.subTest(papel=papel, url=url):
                CustomUser.objects.filter(email=f'{papel.lower()}@loja.com').delete()
                criar_usuario(papel)
                cliente = Client(SERVER_NAME='localhost')
                cliente.login(username=f'{papel.lower()}@loja.com',
                              password='SenhaForte123')
                resposta = cliente.get(url)
                if permitido:
                    self.assertEqual(
                        resposta.status_code, 200,
                        f'{papel} deveria acessar {url}',
                    )
                else:
                    self.assertEqual(
                        resposta.status_code, 302,
                        f'{papel} NAO deveria acessar {url}',
                    )
                    self.assertIn('/contas/dashboard/', resposta.headers['Location'])


class CapacidadesTests(TestCase):
    def test_superusuario_tem_tudo(self):
        usuario = criar_usuario('OPERADOR', 'chefe@loja.com')
        usuario.is_superuser = True
        usuario.save()
        self.assertEqual(P.capacidades(usuario), P.TODAS)

    def test_anonimo_nao_tem_nada(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(P.capacidades(AnonymousUser()), frozenset())

    def test_so_proprietario_configura_a_loja(self):
        self.assertTrue(P.pode(criar_usuario('PROPRIETARIO'), P.CONFIGURAR_LOJA))
        self.assertFalse(P.pode(criar_usuario('GERENTE'), P.CONFIGURAR_LOJA))
        self.assertTrue(P.pode(CustomUser.objects.get(email='gerente@loja.com'),
                               P.VER_RELATORIOS))

    def test_operador_vende_mas_nao_anula_venda(self):
        operador = criar_usuario('OPERADOR')
        self.assertTrue(P.pode(operador, P.VENDER))
        self.assertFalse(P.pode(operador, P.ANULAR_VENDA))

    def test_papel_desconhecido_nao_recebe_nada(self):
        usuario = criar_usuario('OPERADOR', 'x@loja.com')
        usuario.papel = 'INVENTADO'
        usuario.save()
        self.assertEqual(P.capacidades(usuario), frozenset())


class AcaoDestrutivaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_inicial', verbosity=0)

    def test_operador_nao_exclui_produto(self):
        produto = Produto.objects.create(
            sku='X1', nome='Alvo', custo=Decimal('1'), venda=Decimal('2')
        )
        criar_usuario('OPERADOR')
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username='operador@loja.com', password='SenhaForte123')

        resposta = cliente.post(f'/contas/produtos/{produto.pk}/excluir/')

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Produto.objects.filter(pk=produto.pk).exists())

    def test_operador_nao_ve_salario_no_menu(self):
        criar_usuario('OPERADOR')
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username='operador@loja.com', password='SenhaForte123')
        corpo = cliente.get('/contas/dashboard/').content.decode()
        self.assertNotIn('Funcionários', corpo)
        self.assertNotIn('Relatórios', corpo)

    def test_gerente_ve_o_menu_completo(self):
        criar_usuario('GERENTE')
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username='gerente@loja.com', password='SenhaForte123')
        corpo = cliente.get('/contas/dashboard/').content.decode()
        self.assertIn('Funcionários', corpo)
        self.assertIn('Relatórios', corpo)


class DashboardPorPapelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_inicial', verbosity=0)

    def _corpo(self, papel):
        criar_usuario(papel)
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username=f'{papel.lower()}@loja.com', password='SenhaForte123')
        return cliente.get('/contas/dashboard/').content.decode()

    def test_estoquista_nao_ve_faturamento(self):
        self.assertNotIn('Vendas Hoje', self._corpo('ESTOQUISTA'))

    def test_operador_ve_faturamento(self):
        self.assertIn('Vendas Hoje', self._corpo('OPERADOR'))

    def test_estoquista_ve_atalho_de_estoque_e_nao_de_venda(self):
        corpo = self._corpo('ESTOQUISTA')
        self.assertIn('Entrada de Estoque', corpo)
        self.assertNotIn('Nova Venda', corpo)

    def test_papel_aparece_no_rodape(self):
        self.assertIn('Operador de Caixa', self._corpo('OPERADOR'))


class CadastroDeAcessosTests(TestCase):
    """
    Antes, /contas/cadastro/ ficava aberto para sempre: qualquer visitante
    criava conta e saía registrando vendas e exportando a base de clientes.
    """

    def test_primeira_instalacao_fica_aberta(self):
        self.assertFalse(CustomUser.objects.exists())
        cliente = Client(SERVER_NAME='localhost')
        self.assertEqual(cliente.get('/contas/cadastro/').status_code, 200)

    def test_primeiro_usuario_vira_proprietario(self):
        cliente = Client(SERVER_NAME='localhost')
        cliente.post('/contas/cadastro/', {
            'email': 'dono@loja.com', 'nome': 'Dono', 'cpf': '',
            'password1': 'SenhaDono1234', 'password2': 'SenhaDono1234',
        })
        dono = CustomUser.objects.get(email='dono@loja.com')
        self.assertEqual(dono.papel, 'PROPRIETARIO')
        self.assertTrue(dono.is_superuser)

    def test_anonimo_nao_cadastra_depois_da_primeira_conta(self):
        criar_usuario('PROPRIETARIO')
        cliente = Client(SERVER_NAME='localhost')

        resposta = cliente.get('/contas/cadastro/')
        self.assertEqual(resposta.status_code, 302)

        cliente.post('/contas/cadastro/', {
            'email': 'invasor@fora.com', 'nome': 'Invasor', 'cpf': '',
            'password1': 'SenhaQualquer987', 'password2': 'SenhaQualquer987',
        })
        self.assertFalse(CustomUser.objects.filter(email='invasor@fora.com').exists())

    def test_operador_logado_nao_cria_acessos(self):
        criar_usuario('PROPRIETARIO')
        criar_usuario('OPERADOR')
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username='operador@loja.com', password='SenhaForte123')

        cliente.post('/contas/cadastro/', {
            'email': 'amigo@fora.com', 'nome': 'Amigo', 'cpf': '',
            'password1': 'SenhaQualquer987', 'password2': 'SenhaQualquer987',
        })
        self.assertFalse(CustomUser.objects.filter(email='amigo@fora.com').exists())

    def test_gerente_cria_acesso_escolhendo_o_papel(self):
        criar_usuario('GERENTE')
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username='gerente@loja.com', password='SenhaForte123')

        cliente.post('/contas/cadastro/', {
            'email': 'caixa@loja.com', 'nome': 'Caixa', 'cpf': '',
            'papel': 'OPERADOR',
            'password1': 'SenhaCaixa1234', 'password2': 'SenhaCaixa1234',
        })
        novo = CustomUser.objects.get(email='caixa@loja.com')
        self.assertEqual(novo.papel, 'OPERADOR')
        self.assertFalse(novo.is_superuser)

    def test_gerente_nao_cria_outro_proprietario_por_acidente(self):
        criar_usuario('GERENTE')
        cliente = Client(SERVER_NAME='localhost')
        cliente.login(username='gerente@loja.com', password='SenhaForte123')
        cliente.post('/contas/cadastro/', {
            'email': 'novo@loja.com', 'nome': 'Novo', 'cpf': '',
            'papel': 'ESTOQUISTA',
            'password1': 'SenhaNova1234', 'password2': 'SenhaNova1234',
        })
        self.assertEqual(CustomUser.objects.get(email='novo@loja.com').papel, 'ESTOQUISTA')


class ConviteDeCadastroTests(TestCase):
    def test_login_convida_a_criar_o_proprietario_na_instalacao(self):
        corpo = Client(SERVER_NAME='localhost').get('/contas/login/').content.decode()
        self.assertIn('Criar a conta do proprietário', corpo)

    def test_login_nao_convida_depois_que_existe_usuario(self):
        criar_usuario('PROPRIETARIO')
        corpo = Client(SERVER_NAME='localhost').get('/contas/login/').content.decode()
        self.assertNotIn('Criar a conta', corpo)
        self.assertIn('Fale com o responsável', corpo)
