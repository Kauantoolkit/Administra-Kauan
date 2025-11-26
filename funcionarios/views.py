from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Avg

from .models import Funcionario
from .forms import FuncionarioForm

import base64

def file_to_base64(file):
    return base64.b64encode(file.read()).decode('utf-8')


# ---------------------------
# LISTAGEM + ESTATÍSTICAS
# ---------------------------
@login_required
def funcionarios_list(request):
    qs_base = Funcionario.objects.all()

    hoje = timezone.now().date()
    ontem = hoje - timedelta(days=1)

    total_funcionarios = qs_base.count()

    mes_passado = hoje.replace(day=1) - timedelta(days=1)
    inicio_mes_passado = mes_passado.replace(day=1)

    funcionarios_mes_passado = qs_base.filter(
        data_admissao__month=inicio_mes_passado.month,
        data_admissao__year=inicio_mes_passado.year,
    ).count()

    if funcionarios_mes_passado > 0:
        aumento_mes = round(
            ((total_funcionarios - funcionarios_mes_passado) / funcionarios_mes_passado) * 100,
            1
        )
    else:
        aumento_mes = 0

    ativos_hoje = qs_base.filter(status="ativo").count()

    ativos_ontem = qs_base.filter(
        status="ativo",
        data_atualizacao__date=ontem,
    ).count()

    ferias_hoje = qs_base.filter(status="ferias").count()

    ferias_mes_passado = qs_base.filter(
        status="ferias",
        data_atualizacao__date__gte=inicio_mes_passado,
        data_atualizacao__date__lte=mes_passado,
    ).count()

    salario_medio = qs_base.aggregate(avg=Avg("salario"))["avg"] or 0
    salario_medio = round(salario_medio, 2)

    salario_medio_mes_passado = qs_base.filter(
        data_atualizacao__date__gte=inicio_mes_passado,
        data_atualizacao__date__lte=mes_passado,
    ).aggregate(avg=Avg("salario"))["avg"] or 0

    if salario_medio_mes_passado > 0:
        aumento_salarial = round(
            ((salario_medio - salario_medio_mes_passado) / salario_medio_mes_passado) * 100,
            1
        )
    else:
        aumento_salarial = 0

    funcionarios = qs_base.order_by('-id')

    nome = request.GET.get('nome', '')
    cpf = request.GET.get('cpf', '')
    cargo = request.GET.get('cargo', '')
    status = request.GET.get('status', '')

    if nome:
        funcionarios = funcionarios.filter(nome__icontains=nome)
    if cpf:
        funcionarios = funcionarios.filter(cpf__icontains=cpf)
    if cargo:
        funcionarios = funcionarios.filter(cargo=cargo)
    if status:
        funcionarios = funcionarios.filter(status=status)

    paginator = Paginator(funcionarios, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    cargos = qs_base.values_list("cargo", flat=True).distinct()

    return render(request, "funcionarios/funcionarios_list.html", {
        "page_obj": page_obj,
        "total_funcionarios": total_funcionarios,
        "aumento_mes": aumento_mes,
        "ativos_hoje": ativos_hoje,
        "ativos_ontem": ativos_ontem,
        "ferias": ferias_hoje,
        "ferias_mes_passado": ferias_mes_passado,
        "salario_medio": salario_medio,
        "aumento_salarial": aumento_salarial,
        "cargos": cargos,
    })



@login_required
def funcionario_create(request):
    if request.method == "POST":
        form = FuncionarioForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()  # o form já converte foto para base64
            messages.success(request, "Funcionário cadastrado com sucesso!")
            return redirect("funcionarios_list")
    else:
        form = FuncionarioForm()

    return render(request, "funcionarios/funcionario_create.html", {"form": form})



@login_required
def funcionario_edit(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        form = FuncionarioForm(request.POST, request.FILES, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionário atualizado!")
            return redirect("funcionarios_list")
    else:
        form = FuncionarioForm(instance=funcionario)

    return render(request, "funcionarios/funcionario_edit.html", {"form": form})



@login_required
def funcionario_detail(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)
    return render(request, "funcionarios/funcionario_detail.html", {"funcionario": funcionario})



@login_required
def funcionario_delete(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        funcionario.delete()
        messages.success(request, "Funcionário excluído com sucesso.")
        return redirect("funcionarios_list")

    return render(request, "funcionarios/funcionario_confirm_delete.html", {"funcionario": funcionario})
