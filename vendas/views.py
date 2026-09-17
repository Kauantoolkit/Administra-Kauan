from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from clientes.views import registrar_log
from contas import permissoes as P
from contas.models import Produto

from . import services
from .forms import ItemVendaFormSet, VendaForm
from .models import Venda


@P.requer(P.VENDER)
def lista_vendas(request):
    vendas_list = Venda.objects.select_related('cliente').prefetch_related('itens')

    busca = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or '').strip()
    if busca:
        vendas_list = vendas_list.filter(
            Q(cliente__nome__icontains=busca) | Q(id__icontains=busca)
        )
    if status:
        vendas_list = vendas_list.filter(status=status)

    paginator = Paginator(vendas_list.order_by('-data_venda'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'vendas/lista_vendas.html', {
        'vendas': page_obj,
        'busca': busca,
        'status': status,
        'status_choices': Venda.STATUS_CHOICES,
    })


def _salvar_venda(request, venda=None):
    """Fluxo compartilhado entre criar e editar, com estoque consistente."""
    editando = venda is not None
    itens_anteriores = services.mapa_itens(venda) if editando else {}
    valor_anterior = services.valor_lancado_no_cliente(venda) if editando else Decimal('0.00')

    form = VendaForm(request.POST, instance=venda)
    formset = ItemVendaFormSet(request.POST, instance=venda)

    if not (form.is_valid() and formset.is_valid()):
        # Sem isto o usuário via a tela recarregar sem explicação nenhuma.
        for erro in formset.non_form_errors():
            messages.error(request, erro)
        for form_item in formset:
            for erro in form_item.non_field_errors():
                messages.error(request, erro)
        messages.error(request, 'Corrija os campos destacados para salvar a venda.')
        return None, form, formset

    erros = services.validar_itens(formset)
    if erros:
        for erro in erros:
            messages.error(request, erro)
        return None, form, formset

    if not any(
        f.cleaned_data and not f.cleaned_data.get('DELETE')
        for f in formset
    ):
        messages.error(request, 'Adicione pelo menos um item à venda.')
        return None, form, formset

    try:
        with transaction.atomic():
            venda = form.save(commit=False)
            if not editando:
                venda.data_venda = timezone.now()
                venda.operador = request.user
            venda.save()

            formset.instance = venda
            formset.save()

            venda.calcular_totais()

            # So aqui o subtotal existe: na validacao do formulario os itens
            # ainda nao foram gravados. Sem esta checagem um desconto maior que
            # a venda era aceito e gravava um total de R$ 0,00 sem aviso.
            if venda.desconto and venda.desconto > venda.subtotal:
                raise ValidationError(
                    f'O desconto (R$ {venda.desconto:.2f}) é maior que o '
                    f'subtotal da venda (R$ {venda.subtotal:.2f}).'
                )

            services.sincronizar_estoque(
                venda, usuario=request.user, itens_anteriores=itens_anteriores
            )
            services.aplicar_efeitos_no_cliente(venda, valor_anterior=valor_anterior)

            registrar_log(
                entidade='VENDA',
                entidade_id=venda.id,
                acao='ALTERACAO' if editando else 'CRIACAO',
                descricao=(
                    f'Venda #{venda.id} {"alterada" if editando else "criada"} '
                    f'para {venda.nome_cliente}. Total: R$ {venda.total:.2f}'
                ),
                usuario=request.user,
            )
    except ValidationError as exc:
        # Estoque insuficiente ou quantidade inválida: nada é gravado.
        for mensagem in exc.messages:
            messages.error(request, mensagem)
        return None, form, formset

    return venda, form, formset


@P.requer(P.VENDER)
def criar_venda(request):
    if request.method == 'POST':
        venda, form, formset = _salvar_venda(request)
        if venda is not None:
            messages.success(request, f'Venda #{venda.id} registrada com sucesso.')
            return redirect('lista_vendas')
    else:
        form = VendaForm()
        formset = ItemVendaFormSet()

    return render(request, 'vendas/criar_venda.html', {
        'form': form,
        'formset': formset,
        'titulo': 'Nova Venda',
    })


@P.requer(P.VENDER)
def editar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        salva, form, formset = _salvar_venda(request, venda=venda)
        if salva is not None:
            messages.success(request, f'Venda #{salva.id} atualizada.')
            return redirect('lista_vendas')
    else:
        form = VendaForm(instance=venda)
        formset = ItemVendaFormSet(instance=venda)

    return render(request, 'vendas/criar_venda.html', {
        'form': form,
        'formset': formset,
        'venda': venda,
        'titulo': f'Editar Venda #{venda.id}',
    })


@P.requer(P.VENDER)
def detalhe_venda(request, pk):
    venda = get_object_or_404(
        Venda.objects.select_related('cliente', 'operador'), pk=pk
    )
    return render(request, 'vendas/detalhe_venda.html', {
        'venda': venda,
        'itens': venda.itens.select_related('produto', 'variacao'),
    })


@P.requer(P.ANULAR_VENDA)
def excluir_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)

    if request.method == 'POST':
        with transaction.atomic():
            services.estornar_venda(venda, usuario=request.user, motivo='Venda excluída')

            valor_anterior = services.valor_lancado_no_cliente(venda)
            venda.status = 'cancelada'
            services.aplicar_efeitos_no_cliente(venda, valor_anterior=valor_anterior)

            venda_id, cliente_nome, valor_total = venda.id, venda.nome_cliente, venda.total
            venda.delete()

            registrar_log(
                entidade='VENDA',
                entidade_id=venda_id,
                acao='EXCLUSAO',
                descricao=(
                    f'Venda #{venda_id} excluída. Cliente: {cliente_nome}. '
                    f'Total: R$ {valor_total:.2f}'
                ),
                usuario=request.user,
            )
        messages.success(request, f'Venda #{venda_id} excluída e estoque estornado.')
        return redirect('lista_vendas')

    return render(request, 'vendas/confirmar_exclusao.html', {'object': venda})


@P.requer(P.ANULAR_VENDA)
@require_POST
def cancelar_venda(request, pk):
    """Cancela sem apagar o histórico — preferível a excluir."""
    venda = get_object_or_404(Venda, pk=pk)
    with transaction.atomic():
        valor_anterior = services.valor_lancado_no_cliente(venda)
        services.estornar_venda(venda, usuario=request.user, motivo='Cancelamento')
        venda.status = 'cancelada'
        venda.save(update_fields=['status'])
        services.aplicar_efeitos_no_cliente(venda, valor_anterior=valor_anterior)
        registrar_log(
            entidade='VENDA', entidade_id=venda.id, acao='ALTERACAO',
            descricao=f'Venda #{venda.id} cancelada e estoque estornado.',
            usuario=request.user,
        )
    messages.success(request, f'Venda #{venda.id} cancelada.')
    return redirect('lista_vendas')


@P.requer(P.VENDER)
def produto_info_json(request, pk):
    """Alimenta a tela de venda: unidade, preço, saldo e variações."""
    produto = get_object_or_404(Produto, pk=pk)
    return JsonResponse({
        'id': produto.id,
        'nome': produto.nome,
        'unidade': produto.unidade_medida,
        'sigla': produto.sigla_unidade,
        'aceita_fracao': produto.aceita_fracao,
        'casas_decimais': produto.casas_decimais,
        'preco': str(produto.venda),
        'estoque': str(produto.quantidade_estoque),
        'estoque_formatado': produto.estoque_formatado,
        'controla_estoque': produto.controla_estoque,
        'quantidade_minima': str(produto.quantidade_minima_venda),
        'incremento': str(produto.incremento_venda),
        'variacoes': [
            {
                'id': v.id,
                'rotulo': v.rotulo,
                'preco': str(v.preco_efetivo),
                'estoque': str(v.quantidade_estoque),
            }
            for v in produto.variacoes.filter(ativo=True)
        ],
    })
