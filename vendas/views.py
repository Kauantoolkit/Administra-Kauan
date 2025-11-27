from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from .models import Venda, ItemVenda
from .forms import VendaForm, ItemVendaFormSet
from contas.models import MovimentoEstoque
from django.core.paginator import Paginator
from clientes.views import registrar_log

@login_required
def lista_vendas(request):
    vendas_list = Venda.objects.all().order_by('-data_venda')
    paginator = Paginator(vendas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'vendas/lista_vendas.html', {'vendas': page_obj})

@login_required
def criar_venda(request):
    if request.method == 'POST':
        form = VendaForm(request.POST)
        formset = ItemVendaFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                venda = form.save(commit=False)
                venda.data_venda = timezone.now()
                venda.save()
                items = formset.save(commit=False)
                total_venda = 0
                for item in items:
                    item.venda = venda
                    item.preco_unitario = item.produto.venda
                    item.save()
                    total_venda += item.subtotal()
                    MovimentoEstoque.objects.create(
                        produto=item.produto,
                        tipo_movimento='SAIDA',
                        quantidade=item.quantidade,
                        observacao=f"Venda #{venda.id}",
                        usuario=request.user
                    )
                venda.total = total_venda
                venda.save()
                cliente = venda.cliente
                cliente.ultima_compra = venda.data_venda.date()
                cliente.valor_total_comprado += total_venda
                cliente.save()

                registrar_log(
                    entidade='VENDA',
                    entidade_id=venda.id,
                    acao='CRIACAO',
                    descricao=f"Venda #{venda.id} criada para o cliente {cliente.nome} no valor de R$ {total_venda:.2f}",
                    usuario=request.user
                )
                return redirect('lista_vendas')
    else:
        form = VendaForm()
        formset = ItemVendaFormSet()
    return render(request, 'vendas/criar_venda.html', {
        'form': form,
        'formset': formset,
        'titulo': 'Nova Venda'
    })

@login_required
def editar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        form = VendaForm(request.POST, instance=venda)
        formset = ItemVendaFormSet(request.POST, instance=venda)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()  # salva status, cliente e observações
                items = formset.save(commit=False)
                for item in items:
                    item.venda = venda
                    if not item.preco_unitario:
                        item.preco_unitario = item.produto.venda
                    item.save()
                # Remover itens marcados para exclusão
                for item in formset.deleted_objects:
                    item.delete()
                venda.total = sum([i.subtotal() for i in venda.itens.all()])
                venda.save()

                registrar_log(
                    entidade='VENDA',
                    entidade_id=venda.id,
                    acao='ALTERACAO',
                    descricao=f"Venda #{venda.id} alterada. Novo total: R$ {venda.total:.2f}",
                    usuario=request.user
                )
                return redirect('lista_vendas')
    else:
        form = VendaForm(instance=venda)
        formset = ItemVendaFormSet(instance=venda)
    return render(request, 'vendas/criar_venda.html', {
        'form': form,
        'formset': formset,
        'titulo': f'Editar Venda #{venda.id}'
    })

@login_required
def excluir_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            for item in venda.itens.all():
                MovimentoEstoque.objects.create(
                    produto=item.produto,
                    tipo_movimento='ENTRADA',
                    quantidade=item.quantidade,
                    observacao=f"Estorno de Venda Excluída #{venda.id}",
                    usuario=request.user
                )

            venda_id = venda.id
            cliente_nome = venda.cliente.nome
            valor_total = venda.total
            venda.delete()

            registrar_log(
                entidade='VENDA',
                entidade_id=venda_id,
                acao='EXCLUSAO',
                descricao=f"Venda #{venda_id} excluída. Cliente: {cliente_nome}. Total: R$ {valor_total:.2f}",
                usuario=request.user
            )
        return redirect('lista_vendas')
    return render(request, 'vendas/confirmar_exclusao.html', {'object': venda})