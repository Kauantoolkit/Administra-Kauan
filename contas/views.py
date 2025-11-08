from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from .forms import EmailAuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Create your views here.
def cadastro_view(request):

    # 1. Se os dados foram enviados (método POST)
    if request.method == 'POST':
        # 2. Crie uma instância do formulário com os dados enviados (request.POST)
        form = CustomUserCreationForm(request.POST)

        # 3. Verifique se o formulário é válido (o Django valida tudo)
        if form.is_valid():
            # 4. Se for válido, salve o usuário no banco de dados.
            # O form.save() cuida do hash da senha automaticamente!
            user = form.save()

            # 5. (Opcional, mas recomendado) Faça o login do usuário
            # login(request, user) 

            # 6. (Opcional) Envie uma mensagem de sucesso
            # messages.success(request, "Cadastro realizado com sucesso!")

            # 7. Redirecione o usuário para outra página (ex: login ou dashboard)
            # Por enquanto, vamos redirecionar para a página de login
            # (que ainda não criamos, mas vamos chamá-la de 'login')
            return redirect('login') # Vamos criar essa rota 'login' depois

    # 8. Se a requisição for GET (o usuário apenas visitou a página)
    else:
        # 9. Crie um formulário em branco
        form = CustomUserCreationForm()

    # 10. Envie o formulário (em branco ou com erros) para o template
    context = {'form': form}
    return render(request, 'cadastro.html', context)

def login_view(request):
    # Se o usuário já estiver logado, manda ele para o dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Se os dados foram enviados (POST)
    if request.method == 'POST':
        # 1. Cria o formulário com os dados enviados
        form = EmailAuthenticationForm(request, data=request.POST)

        # 2. Verifica se o formulário é válido
        if form.is_valid():
            # 3. Pega o email e senha limpos
            email = form.cleaned_data.get('username') # Nosso form chama o email de 'username'
            password = form.cleaned_data.get('password')

            # 4. Tenta autenticar o usuário
            user = authenticate(request, username=email, password=password)

            # 5. Se o usuário for válido...
            if user is not None:
                # 6. Faz o login (cria a sessão)
                login(request, user)
                # 7. Redireciona para o dashboard
                return redirect('dashboard')
            else:
                # 8. Se for inválido, mostra uma mensagem de erro
                messages.error(request, 'Email ou senha inválidos.')
        else:
            # 9. Se o formulário for inválido (ex: campos em branco)
            messages.error(request, 'Email ou senha inválidos.')

    # Se for GET (usuário só abriu a página)
    else:
        form = EmailAuthenticationForm() # Mostra um form em branco

    # Renderiza o template com o formulário (em branco ou com erros)
    return render(request, 'login.html', {'form': form})

@login_required # <-- Isso protege a página!
def dashboard_view(request):
    # O 'user' já vem no 'request' porque o usuário está logado
    return render(request, 'dashboard.html')