from django.shortcuts import render, redirect
from .models import Venda
from .forms import VendaForm, ItemVendaFormSet
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

@login_required
def lista_vendas(request):
    vendas = Venda.objects.all()
    return render(request, 'vendas/lista_vendas.html', {'vendas': vendas})

@login_required
def criar_venda(request):
    if request.method == 'POST':
        form = VendaForm(request.POST)
        formset = ItemVendaFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                venda = form.save(commit=False)
                venda.data_venda = timezone.now()
                venda.status = 'fechada'
                venda.save()
                
                items = formset.save(commit=False)
                total_venda = 0
                
                for item in items:
                    item.venda = venda
                    item.preco_unitario = item.produto.preco 
                    item.save()
                    total_venda += item.subtotal()
                
                venda.total = total_venda
                venda.save()
                
                cliente = venda.cliente
                cliente.ultima_compra = venda.data_venda.date()
                cliente.valor_total_comprado += total_venda 
                cliente.save()
                
                return redirect('lista_vendas')
    else:
        form = VendaForm()
        formset = ItemVendaFormSet()
    
    return render(request, 'vendas/criar_venda.html', {
        'form': form, 
        'formset': formset
    })

@login_required
def editar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    
    if request.method == 'POST':
        form = VendaForm(request.POST, instance=venda)
        formset = ItemVendaFormSet(request.POST, instance=venda)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                items = formset.save(commit=False)
                
                for obj in formset.deleted_objects:
                    obj.delete()
                
                for item in items:
                    item.venda = venda
                    if not item.preco_unitario:
                        item.preco_unitario = item.produto.preco
                    item.save()
                
                venda.total = sum([item.subtotal() for item in venda.itens.all()])
                venda.save()
                
                return redirect('lista_vendas')
    else:
        form = VendaForm(instance=venda)
        formset = ItemVendaFormSet(instance=venda)
    
    return render(request, 'vendas/criar_venda.html', {
        'form': form, 
        'formset': formset,
        'titulo': 'Editar Venda'
    })

@login_required
def excluir_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        venda.delete()
        return redirect('lista_vendas')
    
    return render(request, 'vendas/confirmar_exclusao.html', {'object': venda})