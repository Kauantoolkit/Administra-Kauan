"""
Casos de borda encontrados exercitando o sistema pelas telas.

Cada teste aqui corresponde a um defeito que chegou a acontecer: nenhum e
hipotetico.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase

from clientes.models import Cliente
from contas.fields import normalizar_decimal
from contas.models import MovimentoEstoque, Produto, ProdutoVariacao
from vendas.models import ItemVenda, Venda

CustomUser = get_user_model()


class DecimalBrasileiroTests(TestCase):
    """Loja brasileira: digita-se "2,500", nao "2.500"."""

    def test_virgula_como_separador_decimal(self):
        self.assertEqual(normalizar_decimal('2,500'), Decimal('2.500'))
        self.assertEqual(normalizar_decimal('0,750'), Decimal('0.750'))

    def test_ponto_de_milhar_com_virgula_decimal(self):
        self.assertEqual(normalizar_decimal('1.234,56'), Decimal('1234.56'))

    def test_formato_internacional_continua_valendo(self):
        self.assertEqual(normalizar_decimal('1234.56'), Decimal('1234.56'))
        self.assertEqual(normalizar_decimal('2.5'), Decimal('2.5'))

    def test_simbolo_de_moeda_e_espacos_sao_ignorados(self):
        self.assertEqual(normalizar_decimal(' R$ 49,90 '), Decimal('49.90'))

    def test_texto_invalido_e_recusado(self):
        with self.assertRaises(ValidationError):
            normalizar_decimal('abc')


class TelasComDadosTests(TestCase):
    def setUp(self):
        call_command('seed_inicial', '--demo', verbosity=0)
        self.usuario = CustomUser.objects.create_user(
            email='op@loja.com', password='SenhaOper123', nome='Operador'
        )
        self.usuario.is_staff = self.usuario.is_superuser = True
        self.usuario.save()
        self.cliente = Client(SERVER_NAME='localhost')
        self.cliente.login(username='op@loja.com', password='SenhaOper123')

    def test_entrada_de_estoque_aceita_virgula(self):
        produto = Produto.objects.get(sku='HORT-001')
        saldo = produto.quantidade_estoque
        self.cliente.post(f'/contas/produtos/{produto.pk}/adicionar-estoque/', {
            'variacao': '', 'quantidade': '2,500',
            'custo_unitario': '4,20', 'validade': '', 'observacao': '',
        })
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_estoque, saldo + Decimal('2.500'))

    def test_excluir_cliente_com_venda_inativa_em_vez_de_quebrar(self):
        # Antes: ProtectedError subia como erro 500 na cara do usuario.
        cliente = Cliente.objects.create(nome='Com Venda', cpf='999', email='cv@ex.com')
        produto = Produto.objects.get(sku='MERC-001')
        venda = Venda.objects.create(cliente=cliente, status='fechada')
        ItemVenda.objects.create(
            venda=venda, produto=produto, quantidade=1, preco_unitario=produto.venda
        )

        resposta = self.cliente.post(f'/clientes/{cliente.pk}/excluir/')

        self.assertEqual(resposta.status_code, 302)
        cliente.refresh_from_db()
        self.assertEqual(cliente.status, 'inativo')

    def test_cliente_sem_venda_e_realmente_excluido(self):
        cliente = Cliente.objects.create(nome='Sem Venda', cpf='777', email='sv@ex.com')
        self.cliente.post(f'/clientes/{cliente.pk}/excluir/')
        self.assertFalse(Cliente.objects.filter(pk=cliente.pk).exists())

    def test_desconto_maior_que_o_subtotal_e_recusado(self):
        produto = Produto.objects.get(sku='MERC-001')
        antes = Venda.objects.count()
        self.cliente.post('/vendas/criar/', {
            'cliente': '', 'status': 'fechada', 'forma_pagamento': 'pix',
            'desconto': '999999', 'acrescimo': '0', 'observacoes': '',
            'itens-TOTAL_FORMS': '1', 'itens-INITIAL_FORMS': '0',
            'itens-MIN_NUM_FORMS': '0', 'itens-MAX_NUM_FORMS': '1000',
            'itens-0-produto': produto.pk, 'itens-0-quantidade': '1',
            'itens-0-preco_unitario': '', 'itens-0-desconto_item': '0',
            'itens-0-variacao': '',
        })
        self.assertEqual(Venda.objects.count(), antes)

    def test_venda_com_desconto_valido_e_gravada(self):
        produto = Produto.objects.get(sku='MERC-001')
        self.cliente.post('/vendas/criar/', {
            'cliente': '', 'status': 'fechada', 'forma_pagamento': 'dinheiro',
            'desconto': '4,90', 'acrescimo': '0', 'observacoes': '',
            'itens-TOTAL_FORMS': '1', 'itens-INITIAL_FORMS': '0',
            'itens-MIN_NUM_FORMS': '0', 'itens-MAX_NUM_FORMS': '1000',
            'itens-0-produto': produto.pk, 'itens-0-quantidade': '1',
            'itens-0-preco_unitario': '', 'itens-0-desconto_item': '0',
            'itens-0-variacao': '',
        })
        venda = Venda.objects.order_by('-id').first()
        self.assertEqual(venda.desconto, Decimal('4.90'))
        self.assertEqual(venda.total, venda.subtotal - Decimal('4.90'))


class GradeDeVariacoesTests(TestCase):
    def setUp(self):
        self.produto = Produto.objects.create(
            sku='GRADE-1', nome='Camiseta', custo=Decimal('20'), venda=Decimal('50')
        )
        self.p = ProdutoVariacao.objects.create(
            produto=self.produto, sku='GRADE-1-P', tamanho='P'
        )
        self.m = ProdutoVariacao.objects.create(
            produto=self.produto, sku='GRADE-1-M', tamanho='M'
        )

    def test_movimento_sem_variacao_e_recusado(self):
        # Antes: o saldo do pai subia sozinho e deixava de bater com a grade.
        with self.assertRaises(ValidationError):
            MovimentoEstoque.objects.create(
                produto=self.produto, tipo_movimento='ENTRADA',
                quantidade=Decimal('10'),
            )

    def test_saldo_do_pai_bate_com_a_soma_das_variacoes(self):
        MovimentoEstoque.objects.create(
            produto=self.produto, variacao=self.p,
            tipo_movimento='ENTRADA', quantidade=Decimal('10'),
        )
        MovimentoEstoque.objects.create(
            produto=self.produto, variacao=self.m,
            tipo_movimento='ENTRADA', quantidade=Decimal('4'),
        )
        self.produto.refresh_from_db()
        soma = sum(v.quantidade_estoque for v in self.produto.variacoes.all())
        self.assertEqual(self.produto.quantidade_estoque, soma)
        self.assertEqual(self.produto.quantidade_estoque, Decimal('14.000'))

    def test_variacao_de_outro_produto_e_recusada(self):
        outro = Produto.objects.create(
            sku='OUTRO', nome='Outro', custo=Decimal('1'), venda=Decimal('2')
        )
        with self.assertRaises(ValidationError):
            MovimentoEstoque.objects.create(
                produto=outro, variacao=self.p,
                tipo_movimento='ENTRADA', quantidade=Decimal('1'),
            )

    def test_produto_sem_grade_nao_exige_variacao(self):
        simples = Produto.objects.create(
            sku='SIMPLES', nome='Simples', custo=Decimal('1'), venda=Decimal('2')
        )
        MovimentoEstoque.objects.create(
            produto=simples, tipo_movimento='ENTRADA', quantidade=Decimal('3')
        )
        simples.refresh_from_db()
        self.assertEqual(simples.quantidade_estoque, Decimal('3.000'))
