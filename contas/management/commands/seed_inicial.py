"""
Popula o banco para a primeira execução ou para uma demonstração.

Substitui o antigo `ContasConfig.ready()`, que executava consultas no banco a
cada inicialização do processo — custo em todo boot de worker e quebra em
banco ainda não migrado.

    python manage.py seed_inicial            # categorias + configuração
    python manage.py seed_inicial --demo     # também cria produtos de exemplo
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from contas.models import (
    Categoria, ConfiguracaoLoja, MovimentoEstoque, Produto, ProdutoVariacao,
    UnidadeMedida,
)

CATEGORIAS_PADRAO = [
    'Alimentos', 'Bebidas', 'Hortifruti', 'Açougue', 'Padaria',
    'Limpeza', 'Higiene', 'Farmácia', 'Eletrônicos', 'Vestuário',
    'Calçados', 'Casa e Jardim', 'Ferramentas', 'Papelaria', 'Serviços',
]

# Um produto de cada modo de venda, para demonstrar o sistema em qualquer ramo.
PRODUTOS_DEMO = [
    # (sku, nome, categoria, unidade, custo, venda, min_venda, incremento, estoque)
    ('MERC-001', 'Arroz Tipo 1 5kg', 'Alimentos', UnidadeMedida.UNIDADE,
     '18.00', '24.90', '1', '1', '120'),
    ('HORT-001', 'Tomate Italiano', 'Hortifruti', UnidadeMedida.QUILOGRAMA,
     '4.20', '8.99', '0.100', '0.010', '45.500'),
    ('ACOU-001', 'Picanha Bovina', 'Açougue', UnidadeMedida.QUILOGRAMA,
     '52.00', '89.90', '0.300', '0.050', '18.750'),
    ('PADA-001', 'Pão Francês', 'Padaria', UnidadeMedida.QUILOGRAMA,
     '7.00', '14.90', '0.050', '0.050', '30.000'),
    ('BEBI-001', 'Chope Artesanal', 'Bebidas', UnidadeMedida.LITRO,
     '9.00', '19.90', '0.300', '0.100', '80.000'),
    ('CASA-001', 'Tecido Algodão Cru', 'Casa e Jardim', UnidadeMedida.METRO,
     '12.00', '27.50', '0.50', '0.10', '240.00'),
    ('CASA-002', 'Porcelanato Acetinado', 'Casa e Jardim', UnidadeMedida.METRO_QUADRADO,
     '38.00', '74.90', '1.00', '1.00', '360.00'),
    ('SERV-001', 'Instalação Técnica', 'Serviços', UnidadeMedida.HORA,
     '0.00', '120.00', '0.50', '0.50', '0.000'),
]

# Produto com grade de tamanho/cor — caso das lojas de roupa.
VARIACOES_DEMO = [
    ('P', 'Preta'), ('M', 'Preta'), ('G', 'Preta'),
    ('P', 'Branca'), ('M', 'Branca'), ('G', 'Branca'),
]


class Command(BaseCommand):
    help = 'Cria categorias, configuração da loja e (opcionalmente) dados de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo', action='store_true',
            help='Também cria produtos de exemplo com todos os modos de venda.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        for nome in CATEGORIAS_PADRAO:
            Categoria.objects.get_or_create(nome=nome)
        self.stdout.write(self.style.SUCCESS(
            f'{len(CATEGORIAS_PADRAO)} categorias garantidas.'
        ))

        ConfiguracaoLoja.obter()
        self.stdout.write(self.style.SUCCESS('Configuração da loja pronta.'))

        if not options['demo']:
            return

        for sku, nome, categoria, unidade, custo, venda, minimo, incr, estoque in PRODUTOS_DEMO:
            produto, criado = Produto.objects.get_or_create(
                sku=sku,
                defaults=dict(
                    nome=nome,
                    categoria=Categoria.objects.get(nome=categoria),
                    unidade_medida=unidade,
                    custo=Decimal(custo),
                    venda=Decimal(venda),
                    quantidade_minima_venda=Decimal(minimo),
                    incremento_venda=Decimal(incr),
                    quantidade_minima_alerta=Decimal('5'),
                    controla_estoque=(unidade != UnidadeMedida.HORA),
                ),
            )
            if criado and Decimal(estoque) > 0:
                MovimentoEstoque.objects.create(
                    produto=produto, tipo_movimento='ENTRADA',
                    quantidade=Decimal(estoque),
                    custo_unitario=Decimal(custo),
                    observacao='Carga inicial de demonstração',
                )

        camiseta, criada = Produto.objects.get_or_create(
            sku='VEST-001',
            defaults=dict(
                nome='Camiseta Básica',
                categoria=Categoria.objects.get(nome='Vestuário'),
                unidade_medida=UnidadeMedida.UNIDADE,
                custo=Decimal('22.00'), venda=Decimal('59.90'),
                quantidade_minima_alerta=Decimal('3'),
            ),
        )
        if criada:
            for tamanho, cor in VARIACOES_DEMO:
                variacao = ProdutoVariacao.objects.create(
                    produto=camiseta, tamanho=tamanho, cor=cor,
                    sku=f'VEST-001-{tamanho}-{cor[:3].upper()}',
                )
                MovimentoEstoque.objects.create(
                    produto=camiseta, variacao=variacao,
                    tipo_movimento='ENTRADA', quantidade=Decimal('10'),
                    custo_unitario=Decimal('22.00'),
                    observacao='Carga inicial de demonstração',
                )

        self.stdout.write(self.style.SUCCESS(
            'Dados de demonstração criados: venda por unidade, peso, volume, '
            'metro, m², hora e grade de tamanho/cor.'
        ))
