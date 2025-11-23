from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from datetime import timedelta

from .models import Cliente
from .forms import ClienteForm


def lista_clientes(request):
    clientes_qs = Cliente.objects.all().order_by('-data_cadastro')

    total_clientes = clientes_qs.count()
    clientes_ativos = clientes_qs.filter(status='ativo').count()

    hoje = timezone.localdate()
    novos_hoje = clientes_qs.filter(data_cadastro__date=hoje).count()

    ticket_medio = 87.50

    now = timezone.now()
    mes_atual = now.month
    ano_atual = now.year

    mes_passado = mes_atual - 1 if mes_atual > 1 else 12
    ano_passado = ano_atual if mes_atual > 1 else ano_atual - 1

    clientes_mes_atual = clientes_qs.filter(
        data_cadastro__month=mes_atual,
        data_cadastro__year=ano_atual
    ).count()

    clientes_mes_passado = clientes_qs.filter(
        data_cadastro__month=mes_passado,
        data_cadastro__year=ano_passado
    ).count()

    diff_mes = clientes_mes_atual - clientes_mes_passado
    txt_total_mes = f"{diff_mes:+} este mês"

    ontem = hoje - timedelta(days=1)
    novos_ontem = clientes_qs.filter(data_cadastro__date=ontem).count()

    diff_hoje = novos_hoje - novos_ontem
    txt_novos_hoje = f"{diff_hoje:+} vs ontem"

    ticket_mes_passado = 82.50
    perc_variacao = ((ticket_medio - ticket_mes_passado) / ticket_mes_passado) * 100
    txt_ticket_mes = f"{perc_variacao:+.0f}% vs mês anterior"

    clientes_ativos_ontem = clientes_qs.filter(
        status='ativo',
        data_cadastro__date__lte=ontem
    ).count()

    diff_ativos = clientes_ativos - clientes_ativos_ontem

    clientes_para_tabela = clientes_qs

    termo_nome = request.GET.get('nome')
    termo_cpf = request.GET.get('cpf')
    termo_email = request.GET.get('email')

    if termo_nome:
        clientes_para_tabela = clientes_para_tabela.filter(nome__icontains=termo_nome)
    
    if termo_cpf:
        clientes_para_tabela = clientes_para_tabela.filter(cpf__icontains=termo_cpf)

    if termo_email:
        clientes_para_tabela = clientes_para_tabela.filter(email__icontains=termo_email)

    paginator = Paginator(clientes_para_tabela, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'request': request, 
        'total_clientes': total_clientes,
        'clientes_ativos': clientes_ativos,
        'novos_hoje': novos_hoje,
        'ticket_medio': ticket_medio,
        'txt_total_mes': txt_total_mes,
        'txt_novos_hoje': txt_novos_hoje,
        'txt_ticket_mes': txt_ticket_mes,
        'txt_ativos_30dias': f"{diff_ativos:+} vs ontem",
    }

    return render(request, 'clientes/lista_clientes.html', context)


def novo_cliente(request):
    if request.method == 'POST':

        print("=== RAW POST DATA ===")
        print(request.POST)

        form = ClienteForm(request.POST)

        print("\n=== FORM.cleaned_data (antes de validar) ===")
        if form.is_valid():
            print(form.cleaned_data)
            form.save()
            return redirect('lista_clientes')

        print("\n=== FORM ERRORS ===")
        print(form.errors)

    else:
        form = ClienteForm()

    return render(request, 'clientes/novo_cliente.html', {'form': form})



def ver_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, "clientes/ver_cliente.html", {"cliente": cliente})

@login_required
def clientes_view(request):
    return render(request, 'clientes.html')


def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect("lista_clientes")
    else:
        form = ClienteForm(instance=cliente)

    return render(request, "clientes/editar_cliente.html", {"form": form, "cliente": cliente})


def excluir_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        cliente.delete()
        return redirect("lista_clientes")

    return render(request, "clientes/excluir_cliente.html", {"cliente": cliente})
