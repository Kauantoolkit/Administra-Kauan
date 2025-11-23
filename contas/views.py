from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm, EmailAuthenticationForm, ProdutoForm, BuscaEstoqueForm, MovimentoEstoqueForm, EntradaProdutoEspecificoForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.core.paginator import Paginator
import datetime
import locale
from django.http import JsonResponse
from .models import Categoria, Produto, MovimentoEstoque
from .messages.estoque_storage import EstoqueStorage
from django.contrib.messages.constants import INFO, SUCCESS, ERROR

def add_estoque_message(request, message, level=INFO):
    storage = EstoqueStorage(request)
    storage.add(level, message)
    storage.update(None)


def obter_data_formatada():
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    
    today = datetime.date.today()
    return today.strftime('%d de %B de %Y')

def cadastro_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    context = {'form': form}
    return render(request, 'cadastro.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                add_estoque_message(request, 'Email ou senha inválidos.', level=ERROR)
        else:
            add_estoque_message(request, 'Email ou senha inválidos.', level=ERROR)
    else:
        form = EmailAuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def dashboard_view(request):
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    today = datetime.date.today()
    data_formatada = today.strftime('%d de %B de %Y')
    context = {'data_hoje': data_formatada}
    return render(request, 'dashboard.html', context)

@login_required
def clientes_view(request):
    return render(request, 'listar_clientes.html')

@login_required
def fornecedores_view(request):
    from .models import Fornecedor
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    search_query = request.GET.get('search', '')
    fornecedores = Fornecedor.objects.all()
    
    if search_query:
        fornecedores = fornecedores.filter(
            Q(nome_fantasia__icontains=search_query) |
            Q(cnpj__icontains=search_query) |
            Q(contato_principal__icontains=search_query)
        )
    
    paginator = Paginator(fornecedores, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'data_hoje': data_formatada
    }
    
    return render(request, 'fornecedores.html', context)


@login_required
def fornecedor_criar(request):
    from .forms import FornecedorForm
    
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor cadastrado com sucesso!')
            return redirect('fornecedores')
    else:
        form = FornecedorForm()
    
    context = {
        'form': form,
        'titulo': 'Novo Fornecedor',
        'action': 'criar',
        'data_hoje': obter_data_formatada(),
    }
    
    return render(request, 'fornecedor_form.html', context)


@login_required
def fornecedor_editar(request, pk):
    from .models import Fornecedor
    from .forms import FornecedorForm
    from django.shortcuts import get_object_or_404
    
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor atualizado com sucesso!')
            return redirect('fornecedores')
    else:
        form = FornecedorForm(instance=fornecedor)
    
    context = {
        'form': form,
        'titulo': 'Editar Fornecedor',
        'action': 'editar',
        'fornecedor': fornecedor,
        'data_hoje': obter_data_formatada(),
    }
    
    return render(request, 'fornecedor_form.html', context)


@login_required
def fornecedor_deletar(request, pk):
    from .models import Fornecedor
    from django.shortcuts import get_object_or_404
    
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    
    if request.method == 'POST':
        nome = fornecedor.nome_fantasia
        fornecedor.delete()
        messages.success(request, f'Fornecedor "{nome}" deletado com sucesso!')
        return redirect('fornecedores')
    
    context = {
        'fornecedor': fornecedor,
        'data_hoje': obter_data_formatada(),
    }
    
    return render(request, 'fornecedor_confirmar_delete.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')
@login_required
def relatorios(request):
    return render(request, 'relatorios.html')
