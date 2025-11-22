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

def cadastro_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            _create_default_categories()
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

def logout_view(request):
    logout(request)
    return redirect('login')

def _create_default_categories():
    default_categories = [
        'Eletrônicos', 
        'Vestuário',
        'Roupas',
        'Esportes',
        'Casa e Jardim',
        'Alimentos', 
        'Ferramentas', 
        'Limpeza', 
        'Escritório'
    ]
    for cat_name in default_categories:
        Categoria.objects.get_or_create(nome=cat_name)

@login_required
def estoque_view(request):
    form = BuscaEstoqueForm(request.GET)
    produtos_list = Produto.objects.all()
    if form.is_valid():
        if form.cleaned_data['busca_nome']:
            produtos_list = produtos_list.filter(nome__icontains=form.cleaned_data['busca_nome'])
        if form.cleaned_data['busca_sku']:
            produtos_list = produtos_list.filter(sku__icontains=form.cleaned_data['busca_sku'])
        if form.cleaned_data['categoria']:
            produtos_list = produtos_list.filter(categoria=form.cleaned_data['categoria'])
        if form.cleaned_data['status']:
            produtos_list = produtos_list.filter(status=form.cleaned_data['status'])
    produtos_list = produtos_list.order_by('nome')
    total_de_produtos_cadastrados = Produto.objects.count()
    total_itens_estoque = Produto.objects.aggregate(total=Sum('quantidade_estoque'))['total'] or 0
    valor_total_estoque = Produto.objects.aggregate(total=Sum(F('custo') * F('quantidade_estoque')))['total'] or 0.00
    estoque_baixo_count = Produto.objects.filter(status='BAIXO').count()
    produtos_zerados_count = Produto.objects.filter(status='ZERADO').count()
    total_categorias = Categoria.objects.count()
    trinta_dias_atras = datetime.date.today() - datetime.timedelta(days=30)
    produtos_mes_anterior = Produto.objects.filter(data_criacao__date__lt=trinta_dias_atras).count()
    produtos_mes_atual = Produto.objects.filter(data_criacao__date__gte=trinta_dias_atras).count()
    variacao = produtos_mes_atual - produtos_mes_anterior
    itens_por_pagina = 10
    paginator = Paginator(produtos_list, itens_por_pagina)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'produtos': page_obj.object_list,
        'form': form,
        'total_produtos_cadastrados': total_de_produtos_cadastrados,
        'valor_total_estoque': valor_total_estoque,
        'estoque_baixo_count': estoque_baixo_count,
        'produtos_zerados_count': produtos_zerados_count,
        'total_categorias': total_categorias,
        'total_itens_estoque': total_itens_estoque,
        'variacao': variacao,
    }
    return render(request, 'estoque.html', context)

@login_required
def novo_produto_view(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save()
            add_estoque_message(request, f'Produto "{produto.nome}" criado com sucesso!', level=SUCCESS)
            return redirect('estoque')
        else:
            add_estoque_message(request, 'Erro ao salvar o produto. Verifique os dados inseridos.', level=ERROR)
    else:
        form = ProdutoForm()
        add_estoque_message(request, 'Lembre-se: o estoque inicial é 0. Use a função de Entrada para adicionar unidades.', level=INFO)
    return render(request, 'novo_produto.html', {'form': form})

@login_required
def detalhe_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    historico = MovimentoEstoque.objects.filter(produto=produto).order_by('-data_movimento')[:10]
    return render(request, 'detalhe_produto.html', {'produto': produto, 'historico': historico})

@login_required
def entrada_estoque_geral_view(request):
    if request.method == 'POST':
        form = MovimentoEstoqueForm(request.POST)
        if form.is_valid():
            movimento = form.save(commit=False)
            movimento.tipo_movimento = 'ENTRADA'
            movimento.save()
            add_estoque_message(request, f'Entrada de {movimento.quantidade} unidades de {movimento.produto.nome} registrada com sucesso.', level=SUCCESS)
            return redirect('estoque')
    else:
        form = MovimentoEstoqueForm()
    return render(request, 'entrada_estoque_geral.html', {'form': form})

@login_required
def adicionar_estoque_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = EntradaProdutoEspecificoForm(request.POST)
        if form.is_valid():
            quantidade = form.cleaned_data['quantidade']
            observacao = form.cleaned_data['observacao']
            MovimentoEstoque.objects.create(
                produto=produto,
                tipo_movimento='ENTRADA',
                quantidade=quantidade,
                observacao=observacao
            )
            add_estoque_message(request, f'Adicionadas {quantidade} unidades ao estoque de {produto.nome}.', level=SUCCESS)
            return redirect('estoque')
        else:
            add_estoque_message(request, 'Erro ao registrar a entrada. Quantidade inválida.', level=ERROR)
    else:
        form = EntradaProdutoEspecificoForm()
    return render(request, 'entrada_produto_especifico.html', {'form': form, 'produto': produto})

@login_required
def excluir_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    nome = produto.nome
    produto.delete()
    add_estoque_message(request, f'O produto "{nome}" foi removido com sucesso.', level=SUCCESS)
    return redirect('estoque')

def detalhes_produto_ajax(request, pk):
    p = Produto.objects.get(pk=pk)
    img = p.imagem.url if p.imagem else "/static/img/no-image.png"
    return JsonResponse({
        "nome": p.nome,
        "sku": p.sku,
        "categoria": p.categoria.nome if p.categoria else "",
        "descricao": p.descricao or "",
        "custo": f"{p.custo:.2f}",
        "venda": f"{p.venda:.2f}",
        "quantidade": p.quantidade_estoque,
        "quantidade_minima": p.quantidade_minima_alerta,
        "status": p.status,
    })

def editar_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    categorias = Categoria.objects.all()
    if request.method == "POST":
        produto.nome = request.POST.get("nome")
        produto.sku = request.POST.get("sku")
        produto.marca = request.POST.get("marca")
        produto.descricao = request.POST.get("descricao")
        cat_id = request.POST.get("categoria")
        if cat_id:
            produto.categoria_id = int(cat_id)
        else:
            produto.categoria = None
        try:
            produto.custo = float(request.POST.get("custo", 0))
        except ValueError:
            produto.custo = 0
        try:
            produto.venda = float(request.POST.get("venda", 0))
        except ValueError:
            produto.venda = 0
        try:
            produto.quantidade_minima_alerta = int(request.POST.get("quantidade_minima_alerta", 0))
        except ValueError:
            produto.quantidade_minima_alerta = 0
        produto.unidade_medida = request.POST.get("unidade_medida")
        try:
            produto.quantidade_estoque = int(request.POST.get("quantidade", 0))
        except ValueError:
            produto.quantidade_estoque = 0
        produto.save()
        add_estoque_message(request, f'Produto "{produto.nome}" atualizado com sucesso!', level=SUCCESS)
        return redirect("estoque")
    return render(request, "edicao_produto.html", {"produto": produto, "categorias": categorias})
