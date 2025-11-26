from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from datetime import timedelta

from .models import Cliente, LogAcao
from .forms import ClienteForm
import csv
from django.http import HttpResponse


def lista_clientes(request):
    clientes_qs = Cliente.objects.all().order_by('-data_cadastro')

    status_filter = request.GET.get('status')
    cidade_filter = request.GET.get('cidade')

    if status_filter:
        clientes_qs = clientes_qs.filter(status=status_filter)
    
    if cidade_filter:
        clientes_qs = clientes_qs.filter(cidade__icontains=cidade_filter)
    
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

    paginator = Paginator(clientes_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
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

        form = ClienteForm(request.POST)

        if form.is_valid():
            cliente = form.save()
            registrar_log(
                entidade='CLIENTE',
                entidade_id=cliente.id,
                acao='CRIACAO',
                descricao=f"Cliente '{cliente.nome}' foi criado.",
                usuario=request.user if request.user.is_authenticated else None
            )
            return redirect('lista_clientes')

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
           cliente_editado = form.save()
        registrar_log(
                entidade='CLIENTE',
                entidade_id=cliente_editado.id,
                acao='ALTERACAO',
                descricao=f"Cliente '{cliente_editado.nome}' foi alterado.",
                usuario=request.user if request.user.is_authenticated else None
        )
        return redirect("lista_clientes")
    else:
        form = ClienteForm(instance=cliente)

    return render(request, "clientes/editar_cliente.html", {"form": form, "cliente": cliente})


def excluir_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':

        id_cliente = cliente.id
        nome_cliente = cliente.nome
        
        cliente.delete()

        registrar_log(
            entidade='CLIENTE',
            entidade_id=id_cliente,
            acao='EXCLUSAO',
            descricao=f"Cliente '{nome_cliente}' foi excluído.",
            usuario=request.user if request.user.is_authenticated else None
        )

        return redirect("lista_clientes")

    return render(request, "clientes/excluir_cliente.html", {"cliente": cliente})

def exportar_clientes_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clientes.csv"'

    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    writer.writerow(['Nome', 'CPF', 'Email', 'Telefone', 'Cidade', 'Status', 'Data Cadastro'])

    clientes = Cliente.objects.all()
    
    nome = request.GET.get('nome')
    cpf = request.GET.get('cpf')
    email = request.GET.get('email')

    if nome:
        clientes = clientes.filter(nome__icontains=nome)
    if cpf:
        clientes = clientes.filter(cpf__icontains=cpf)
    if email:
        clientes = clientes.filter(email__icontains=email)

    for cliente in clientes:
        writer.writerow([
            cliente.nome,
            cliente.cpf,
            cliente.email,
            cliente.telefone,
            cliente.cidade,
            cliente.get_status_display(),
            cliente.data_cadastro.strftime('%d/%m/%Y')
        ])

    return response

def historico_logs(request):
    logs = LogAcao.objects.all().order_by('-datahora') 
    return render(request, 'historico_sistema.html', {'logs': logs})

def registrar_log(entidade, entidade_id, acao, descricao, usuario):
    LogAcao.objects.create(
        entidade=entidade,
        entidade_id=entidade_id,
        acao=acao,
        descricao=descricao,
        usuario=usuario
    )


