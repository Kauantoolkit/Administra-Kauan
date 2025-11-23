from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from .forms import EmailAuthenticationForm
from django.contrib.auth import login, authenticate,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime
import locale
from django.db.models import Sum
from django.utils import timezone
from vendas.models import Venda, ItemVenda
from clientes.models import Cliente
from vendas.models import Produto


def obter_data_formatada():
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    
    today = datetime.date.today()
    return today.strftime('%d de %B de %Y')


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
                messages.error(request, 'Email ou senha inválidos.')
        else:
            messages.error(request, 'Email ou senha inválidos.')

    else:
        form = EmailAuthenticationForm()

    return render(request, 'login.html', {'form': form})

def calcular_crescimento(atual, anterior):
    if not anterior or anterior == 0:
        return 100.0 if atual > 0 else 0.0
    return ((atual - anterior) / anterior) * 100

@login_required
def dashboard_view(request):
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')

    today = datetime.date.today()
    data_formatada = today.strftime('%d de %B de %Y')

    hoje = timezone.now().date()
    ontem_data = hoje - datetime.timedelta(days=1)

    vendas_hoje = Venda.objects.filter(data_venda__date=hoje).aggregate(Sum('total'))['total__sum'] or 0
    vendas_ontem = Venda.objects.filter(data_venda__date=ontem_data).aggregate(Sum('total'))['total__sum'] or 0
    
    perc_vendas = calcular_crescimento(float(vendas_hoje), float(vendas_ontem))

    prod_hoje = ItemVenda.objects.filter(venda__data_venda__date=hoje).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    prod_ontem = ItemVenda.objects.filter(venda__data_venda__date=ontem_data).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    
    perc_produtos = calcular_crescimento(prod_hoje, prod_ontem)

    clientes_ativos = Cliente.objects.filter(status='ativo').count()
    
    novos_clientes_hoje = Cliente.objects.filter(data_cadastro__date=hoje).count()
    novos_clientes_ontem = Cliente.objects.filter(data_cadastro__date=ontem_data).count()
    perc_clientes = calcular_crescimento(novos_clientes_hoje, novos_clientes_ontem)


    produtos_falta = Produto.objects.filter(estoque_atual__lt=10).count()
    vendas_recentes = Venda.objects.select_related('cliente').order_by('-data_venda')[:5]

    context = {
        'data_hoje': data_formatada,
        
        'vendas_hoje': vendas_hoje,
        'perc_vendas': perc_vendas,
        
        'produtos_vendidos': prod_hoje,
        'perc_produtos': perc_produtos,
        
        'clientes_ativos': clientes_ativos,
        'perc_clientes': perc_clientes, 
        
        'produtos_falta': produtos_falta,
        'vendas_recentes': vendas_recentes,
    }
    
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
        'page_obj': page_obj,
        'search_query': search_query,
        'total_fornecedores': paginator.count,
        'data_hoje': obter_data_formatada(),
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
