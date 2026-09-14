"""
Regras de negócio da venda.

Todo efeito da venda sobre o estoque passa por aqui. Antes, a criação baixava
estoque mesmo em orçamento, a edição não ajustava saldo nenhum e a exclusão
estornava sem desfazer o histórico do cliente — este módulo centraliza isso.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from contas.models import ConfiguracaoLoja, MovimentoEstoque


def _deve_baixar_estoque(venda):
    """Orçamento só reserva estoque se a loja estiver configurada assim."""
    if venda.status == 'cancelada':
        return False
    if venda.status == 'fechada':
        return True
    return ConfiguracaoLoja.obter().baixa_estoque_em_orcamento


def _saida(item, venda, usuario):
    MovimentoEstoque.objects.create(
        produto=item.produto,
        variacao=item.variacao,
        tipo_movimento='SAIDA',
        quantidade=item.quantidade,
        observacao=f'Venda #{venda.id}',
        usuario=usuario,
    )


def _entrada(produto, variacao, quantidade, venda, usuario, motivo):
    MovimentoEstoque.objects.create(
        produto=produto,
        variacao=variacao,
        tipo_movimento='ENTRADA',
        quantidade=quantidade,
        observacao=f'{motivo} — Venda #{venda.id}',
        usuario=usuario,
    )


@transaction.atomic
def sincronizar_estoque(venda, usuario=None, itens_anteriores=None):
    """
    Deixa o estoque coerente com o estado atual da venda.

    `itens_anteriores` é o mapa {(produto_id, variacao_id): quantidade} de antes
    da edição. Com ele a função lança apenas a diferença, em vez de estornar e
    rebaixar tudo — o histórico de movimentos fica legível.
    """
    itens_anteriores = itens_anteriores or {}
    baixar = _deve_baixar_estoque(venda)

    if not baixar:
        # Venda virou orçamento/cancelada: devolve tudo que havia sido baixado.
        if venda.estoque_baixado:
            for (produto_id, variacao_id), quantidade in itens_anteriores.items():
                item = venda.itens.filter(produto_id=produto_id).first()
                produto = item.produto if item else None
                if produto is None:
                    from contas.models import Produto
                    produto = Produto.objects.get(pk=produto_id)
                variacao = None
                if variacao_id:
                    from contas.models import ProdutoVariacao
                    variacao = ProdutoVariacao.objects.get(pk=variacao_id)
                _entrada(produto, variacao, quantidade, venda, usuario, 'Estorno')
            venda.estoque_baixado = False
            venda.save(update_fields=['estoque_baixado'])
        return

    atuais = {}
    for item in venda.itens.select_related('produto', 'variacao'):
        chave = (item.produto_id, item.variacao_id)
        atuais[chave] = atuais.get(chave, Decimal('0')) + item.quantidade

    base = itens_anteriores if venda.estoque_baixado else {}

    for chave, quantidade in atuais.items():
        anterior = base.get(chave, Decimal('0'))
        delta = quantidade - anterior
        if delta == 0:
            continue
        item = venda.itens.filter(
            produto_id=chave[0], variacao_id=chave[1]
        ).select_related('produto', 'variacao').first()
        if delta > 0:
            MovimentoEstoque.objects.create(
                produto=item.produto, variacao=item.variacao,
                tipo_movimento='SAIDA', quantidade=delta,
                observacao=f'Venda #{venda.id}', usuario=usuario,
            )
        else:
            _entrada(item.produto, item.variacao, -delta, venda, usuario, 'Ajuste')

    # Itens que existiam antes e sumiram da venda: devolve ao estoque.
    for chave, quantidade in base.items():
        if chave in atuais:
            continue
        from contas.models import Produto, ProdutoVariacao
        produto = Produto.objects.get(pk=chave[0])
        variacao = ProdutoVariacao.objects.get(pk=chave[1]) if chave[1] else None
        _entrada(produto, variacao, quantidade, venda, usuario, 'Item removido')

    venda.estoque_baixado = True
    venda.save(update_fields=['estoque_baixado'])


@transaction.atomic
def estornar_venda(venda, usuario=None, motivo='Estorno'):
    """Devolve ao estoque tudo que a venda retirou. Idempotente."""
    if not venda.estoque_baixado:
        return
    for item in venda.itens.select_related('produto', 'variacao'):
        _entrada(item.produto, item.variacao, item.quantidade, venda, usuario, motivo)
    venda.estoque_baixado = False
    venda.save(update_fields=['estoque_baixado'])


def mapa_itens(venda):
    """Fotografia das quantidades atuais, para comparar depois da edição."""
    mapa = {}
    for item in venda.itens.all():
        chave = (item.produto_id, item.variacao_id)
        mapa[chave] = mapa.get(chave, Decimal('0')) + item.quantidade
    return mapa


@transaction.atomic
def aplicar_efeitos_no_cliente(venda, valor_anterior=Decimal('0.00')):
    """
    Mantém o histórico do cliente coerente. Antes, a edição e a exclusão da
    venda deixavam `valor_total_comprado` inflado para sempre.
    """
    cliente = venda.cliente
    if cliente is None:
        return

    valor_atual = venda.total if venda.status == 'fechada' else Decimal('0.00')
    delta = valor_atual - valor_anterior
    if delta:
        cliente.valor_total_comprado = max(
            (cliente.valor_total_comprado or Decimal('0.00')) + delta, Decimal('0.00')
        )
    if venda.status == 'fechada':
        data = venda.data_venda.date()
        if cliente.ultima_compra is None or data > cliente.ultima_compra:
            cliente.ultima_compra = data
    cliente.save(update_fields=['valor_total_comprado', 'ultima_compra'])


def valor_lancado_no_cliente(venda):
    """Quanto desta venda já está somado no total do cliente."""
    return venda.total if venda.status == 'fechada' else Decimal('0.00')


def validar_itens(formset):
    """Roda a validação de unidade/fração de cada item e agrega os erros."""
    erros = []
    for form in formset:
        if not getattr(form, 'cleaned_data', None):
            continue
        if form.cleaned_data.get('DELETE'):
            continue
        item = form.instance
        try:
            item.clean()
        except ValidationError as exc:
            erros.extend(exc.messages)
    return erros
