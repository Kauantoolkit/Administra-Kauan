# funcionarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Avg

from .models import Funcionario
from .forms import FuncionarioForm


# ---------------------------
# LISTAGEM + ESTATÍSTICAS
# ---------------------------
@login_required
def funcionarios_list(request):
    funcionarios = Funcionario.objects.all().order_by('-id')

    # --- Filtros ---
    search = request.GET.get('search', '')
    if search:
        funcionarios = funcionarios.filter(nome__icontains=search)

    # --- Estatísticas dos cards ---
    total_funcionarios = funcionarios.count()
    ativos_hoje = funcionarios.filter(status="Ativo").count()
    ferias = funcionarios.filter(status="Férias").count()

    salario_medio = funcionarios.aggregate(Avg('salario'))['salario__avg'] or 0
    salario_medio = round(salario_medio, 2)

    cargos = Funcionario.objects.values_list("cargo", flat=True).distinct()

    # --- Paginação ---
    paginator = Paginator(funcionarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "funcionarios/funcionarios_list.html", {
        "page_obj": page_obj,
        "total_funcionarios": total_funcionarios,
        "ativos_hoje": ativos_hoje,
        "ferias": ferias,
        "salario_medio": salario_medio,
        "cargos": cargos,
    })


# ---------------------------
# CRIAR FUNCIONÁRIO
# ---------------------------
@login_required
def funcionario_create(request):
    if request.method == "POST":
        form = FuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionário cadastrado com sucesso!")
            return redirect("funcionarios_list")
    else:
        form = FuncionarioForm()

    return render(request, "funcionarios/funcionario_form.html", {
        "form": form
    })


# ---------------------------
# EDITAR FUNCIONÁRIO
# ---------------------------
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

    return render(request, "funcionarios/funcionario_form.html", {
        "form": form
    })


# ---------------------------
# DETALHES DO FUNCIONÁRIO
# ---------------------------
@login_required
def funcionario_detail(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)
    return render(request, "funcionarios/funcionario_detail.html", {
        "funcionario": funcionario
    })


# ---------------------------
# EXCLUIR FUNCIONÁRIO
# ---------------------------
@login_required
def funcionario_delete(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    if request.method == "POST":
        funcionario.delete()
        messages.success(request, "Funcionário excluído com sucesso.")
        return redirect("funcionarios_list")

    return render(request, "funcionarios/funcionario_confirm_delete.html", {
        "funcionario": funcionario
    })
