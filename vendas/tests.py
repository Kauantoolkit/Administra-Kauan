"""
Testes das regras que sustentam a venda por peso, unidade e grade.

Cobrem exatamente os defeitos corrigidos: estoque que ficava negativo,
orçamento que baixava estoque, edição que não ajustava saldo e total do
cliente que só crescia.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from clientes.models import Cliente
from contas.models import (
    Categoria, ConfiguracaoLoja, MovimentoEstoque, Produto, ProdutoVariacao,
    UnidadeMedida,
)

from . import services
from .models import ItemVenda, Venda


def criar_produto(**kwargs):
    padrao = dict(
        sku='SKU1', nome='Produto', custo=Decimal('5.00'), venda=Decimal('10.00'),
        unidade_medida=UnidadeMedida.UNIDADE,
    )
    padrao.update(kwargs)
    return Produto.objects.create(**padrao)


def dar_entrada(produto, quantidade, variacao=None):
    MovimentoEstoque.objects.create(
        produto=produto, variacao=variacao, tipo_movimento='ENTRADA',
        quantidade=Decimal(quantidade),
    )
    produto.refresh_from_db()


class UnidadeDeMedidaTests(TestCase):
    def test_produto_por_unidade_recusa_fracao(self):
        produto = criar_produto()
        with self.assertRaises(ValidationError):
            produto.normalizar_quantidade(Decimal('1.5'))

    def test_produto_por_peso_aceita_fracao(self):
        produto = criar_produto(
            unidade_medida=UnidadeMedida.QUILOGRAMA,
            quantidade_minima_venda=Decimal('0.100'),
            incremento_venda=Decimal('0.010'),
        )
        self.assertEqual(produto.normalizar_quantidade('0.750'), Decimal('0.750'))

    def test_quantidade_abaixo_do_minimo_e_recusada(self):
        produto = criar_produto(
            unidade_medida=UnidadeMedida.QUILOGRAMA,
            quantidade_minima_venda=Decimal('0.300'),
            incremento_venda=Decimal('0.100'),
        )
        with self.assertRaises(ValidationError):
            produto.normalizar_quantidade(Decimal('0.200'))

    def test_incremento_fora_do_multiplo_e_recusado(self):
        produto = criar_produto(
            unidade_medida=UnidadeMedida.QUILOGRAMA,
            quantidade_minima_venda=Decimal('0.500'),
            incremento_venda=Decimal('0.500'),
        )
        with self.assertRaises(ValidationError):
            produto.normalizar_quantidade(Decimal('0.750'))

    def test_subtotal_por_peso_arredonda_ao_centavo(self):
        produto = criar_produto(
            unidade_medida=UnidadeMedida.QUILOGRAMA, venda=Decimal('8.99'),
            quantidade_minima_venda=Decimal('0.001'),
            incremento_venda=Decimal('0.001'),
        )
        # 0,347 kg x R$ 8,99 = R$ 3,11953 -> R$ 3,12
        self.assertEqual(produto.calcular_subtotal(Decimal('0.347')), Decimal('3.12'))

    def test_formatacao_usa_padrao_brasileiro(self):
        produto = criar_produto(unidade_medida=UnidadeMedida.QUILOGRAMA)
        self.assertEqual(produto.formatar_quantidade(Decimal('1.5')), '1,500 kg')


class EstoqueTests(TestCase):
    def test_saida_maior_que_saldo_e_bloqueada(self):
        produto = criar_produto()
        dar_entrada(produto, '10')
        with self.assertRaises(ValidationError):
            MovimentoEstoque.objects.create(
                produto=produto, tipo_movimento='SAIDA', quantidade=Decimal('11')
            )
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_estoque, Decimal('10.000'))

    def test_estoque_negativo_permitido_quando_a_loja_autoriza(self):
        config = ConfiguracaoLoja.obter()
        config.permite_estoque_negativo = True
        config.save()

        produto = criar_produto()
        dar_entrada(produto, '1')
        MovimentoEstoque.objects.create(
            produto=produto, tipo_movimento='SAIDA', quantidade=Decimal('5')
        )
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_estoque, Decimal('-4.000'))

    def test_saida_de_variacao_desconta_variacao_e_produto(self):
        produto = criar_produto(sku='VAR1')
        variacao = ProdutoVariacao.objects.create(
            produto=produto, sku='VAR1-P', tamanho='P'
        )
        dar_entrada(produto, '10', variacao=variacao)

        MovimentoEstoque.objects.create(
            produto=produto, variacao=variacao,
            tipo_movimento='SAIDA', quantidade=Decimal('4'),
        )
        produto.refresh_from_db()
        variacao.refresh_from_db()
        self.assertEqual(variacao.quantidade_estoque, Decimal('6.000'))
        self.assertEqual(produto.quantidade_estoque, Decimal('6.000'))

    def test_servico_sem_controle_de_estoque_nao_move_saldo(self):
        servico = criar_produto(
            sku='SERV', unidade_medida=UnidadeMedida.HORA, controla_estoque=False,
            quantidade_minima_venda=Decimal('0.5'), incremento_venda=Decimal('0.5'),
        )
        MovimentoEstoque.objects.create(
            produto=servico, tipo_movimento='SAIDA', quantidade=Decimal('3')
        )
        servico.refresh_from_db()
        self.assertEqual(servico.quantidade_estoque, Decimal('0.000'))


class VendaTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Teste')
        self.produto = criar_produto(categoria=self.categoria)
        dar_entrada(self.produto, '100')
        self.cliente = Cliente.objects.create(
            nome='Cliente', cpf='000.000.000-00', email='c@example.com'
        )

    def _venda_com_item(self, quantidade='2', status='fechada'):
        venda = Venda.objects.create(cliente=self.cliente, status=status)
        ItemVenda.objects.create(
            venda=venda, produto=self.produto, quantidade=Decimal(quantidade),
            preco_unitario=self.produto.venda,
        )
        venda.calcular_totais()
        return venda

    def test_orcamento_nao_baixa_estoque(self):
        venda = self._venda_com_item(status='orcamento')
        services.sincronizar_estoque(venda)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('100.000'))
        self.assertFalse(venda.estoque_baixado)

    def test_venda_fechada_baixa_estoque(self):
        venda = self._venda_com_item(quantidade='3')
        services.sincronizar_estoque(venda)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('97.000'))

    def test_edicao_lanca_apenas_a_diferenca(self):
        venda = self._venda_com_item(quantidade='3')
        services.sincronizar_estoque(venda)

        anteriores = services.mapa_itens(venda)
        item = venda.itens.first()
        item.quantidade = Decimal('5')
        item.save()
        venda.calcular_totais()
        services.sincronizar_estoque(venda, itens_anteriores=anteriores)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('95.000'))

    def test_reduzir_quantidade_devolve_ao_estoque(self):
        venda = self._venda_com_item(quantidade='10')
        services.sincronizar_estoque(venda)

        anteriores = services.mapa_itens(venda)
        item = venda.itens.first()
        item.quantidade = Decimal('4')
        item.save()
        services.sincronizar_estoque(venda, itens_anteriores=anteriores)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('96.000'))

    def test_remover_item_da_venda_devolve_ao_estoque(self):
        venda = self._venda_com_item(quantidade='6')
        services.sincronizar_estoque(venda)

        anteriores = services.mapa_itens(venda)
        venda.itens.all().delete()
        services.sincronizar_estoque(venda, itens_anteriores=anteriores)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('100.000'))

    def test_cancelamento_estorna_estoque(self):
        venda = self._venda_com_item(quantidade='8')
        services.sincronizar_estoque(venda)
        services.estornar_venda(venda)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('100.000'))
        self.assertFalse(venda.estoque_baixado)

    def test_estorno_e_idempotente(self):
        venda = self._venda_com_item(quantidade='8')
        services.sincronizar_estoque(venda)
        services.estornar_venda(venda)
        services.estornar_venda(venda)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('100.000'))

    def test_total_do_cliente_nao_infla_ao_editar(self):
        venda = self._venda_com_item(quantidade='2')
        services.aplicar_efeitos_no_cliente(venda, valor_anterior=Decimal('0.00'))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.valor_total_comprado, Decimal('20.00'))

        anterior = services.valor_lancado_no_cliente(venda)
        item = venda.itens.first()
        item.quantidade = Decimal('5')
        item.save()
        venda.calcular_totais()
        services.aplicar_efeitos_no_cliente(venda, valor_anterior=anterior)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.valor_total_comprado, Decimal('50.00'))

    def test_cancelar_venda_devolve_o_total_do_cliente(self):
        venda = self._venda_com_item(quantidade='4')
        services.aplicar_efeitos_no_cliente(venda, valor_anterior=Decimal('0.00'))

        anterior = services.valor_lancado_no_cliente(venda)
        venda.status = 'cancelada'
        venda.save()
        services.aplicar_efeitos_no_cliente(venda, valor_anterior=anterior)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.valor_total_comprado, Decimal('0.00'))

    def test_desconto_entra_no_total(self):
        venda = self._venda_com_item(quantidade='10')
        venda.desconto = Decimal('15.00')
        venda.calcular_totais()
        self.assertEqual(venda.subtotal, Decimal('100.00'))
        self.assertEqual(venda.total, Decimal('85.00'))

    def test_venda_sem_cliente_e_valida(self):
        venda = Venda.objects.create(cliente=None, status='fechada')
        ItemVenda.objects.create(
            venda=venda, produto=self.produto, quantidade=Decimal('1'),
            preco_unitario=self.produto.venda,
        )
        venda.calcular_totais()
        services.aplicar_efeitos_no_cliente(venda)
        self.assertEqual(venda.nome_cliente, 'Consumidor final')

    def test_item_exige_variacao_quando_produto_tem_grade(self):
        produto = criar_produto(sku='GRADE')
        ProdutoVariacao.objects.create(produto=produto, sku='GRADE-P', tamanho='P')
        venda = Venda.objects.create(cliente=self.cliente)
        item = ItemVenda(
            venda=venda, produto=produto, quantidade=Decimal('1'),
            preco_unitario=produto.venda,
        )
        with self.assertRaises(ValidationError):
            item.clean()
