from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from .forms import EmailAuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime
import locale

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
    
    context = {
        'data_hoje': data_formatada
        # TODO adicionar valores para que v'ao vir das proximas telas
        # 'vendas_hoje': 2847,
        # 'produtos_vendidos': 147,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def clientes_view(request):
    return render(request, 'clientes.html')