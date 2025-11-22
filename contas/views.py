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

@login_required
def dashboard_view(request):
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')

    today = datetime.date.today()
    data_formatada = today.strftime('%d de %B de %Y')

    hoje = timezone.now().date()
    
    total_hoje = Venda.objects.filter(data_venda__date=hoje).aggregate(Sum('total'))['total__sum'] or 0
    
    produtos_vendidos = ItemVenda.objects.filter(venda__data_venda__date=hoje).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    
    try:
        clientes_ativos = Cliente.objects.filter(status='ativo').count()
    except:
        clientes_ativos = 0

    try:
        produtos_falta = Produto.objects.filter(estoque_atual__lt=10).count()
    except:
        produtos_falta = 0
        
    context = {
        'data_hoje': data_formatada,
        'vendas_hoje': total_hoje,
        'produtos_vendidos': produtos_vendidos,
        'clientes_ativos': clientes_ativos,
        'produtos_falta': produtos_falta,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def clientes_view(request):
    return render(request, 'listar_clientes.html')

def logout_view(request):
    logout(request)
    return redirect('login')