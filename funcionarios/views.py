# funcionarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Funcionario
from .forms import FuncionarioForm
from django.core.paginator import Paginator
from django.contrib import messages

@login_required
def funcionarios_list(request):
    funcionarios = CustomUser.objects.all().order_by('-id')
    

    search = request.GET.get('search', '')
    if search:
        funcionarios = funcionarios.filter(nome__icontains=search)
    
    paginator = Paginator(funcionarios, 5)  # 5 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'funcionarios/funcionarios_list.html', {
        'page_obj': page_obj
    })


@login_required
def funcionario_create(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('funcionarios_list')
    else:
        form = FuncionarioForm()
    
    return render(request, 'funcionarios/funcionario_form.html', {'form': form})


@login_required
def funcionario_edit(request, pk):
    funcionario = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            return redirect('funcionarios_list')
    else:
        form = FuncionarioForm(instance=funcionario)
    
    return render(request, 'funcionarios/funcionario_form.html', {'form': form})



def funcionario_detail(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)
    return render(request, "funcionarios/funcionario_detail.html", {
        "funcionario": funcionario
    })


def funcionario_delete(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)

    # opcional: checar permissão (ex.: apenas staff pode deletar)
    # if not request.user.is_staff:
    #     messages.error(request, "Você não tem permissão para excluir este funcionário.")
    #     return redirect('funcionarios_list')

    if request.method == "POST":
        # se quiser também deletar o usuário vinculado (descomente)
        # if funcionario.user:
        #     funcionario.user.delete()

        funcionario.delete()
        messages.success(request, "Funcionário excluído com sucesso.")
        return redirect('funcionarios_list')

    # GET -> mostrar página de confirmação
    return render(request, "funcionarios/funcionario_confirm_delete.html", {
        "funcionario": funcionario
    })
