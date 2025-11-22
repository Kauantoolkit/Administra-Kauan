from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm, EmailAuthenticationForm, ProdutoForm, BuscaEstoqueForm, MovimentoEstoqueForm, EntradaProdutoEspecificoForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, F, Count
from django.core.paginator import Paginator
from .models import Produto, Categoria, MovimentoEstoque, CustomUser
import datetime
import locale
from django.http import JsonResponse

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
    
    # Adiciona categorias padrão se nenhum usuário tiver feito isso ainda
    _create_default_categories()
    
    context = {
        'data_hoje': data_formatada
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def clientes_view(request):
    return render(request, 'clientes.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# --- Funções de Inicialização ---
def _create_default_categories():
    # Lista expandida de categorias padrão para refletir os exemplos do sistema de estoque.
    default_categories = [
        'Eletrônicos', 
        'Vestuário', # Categoria para Roupas/Camisetas
        'Roupas', # Categoria Roupas vista no exemplo
        'Esportes', # Categoria Esportes vista no exemplo
        'Casa e Jardim', # Categoria Casa e Jardim vista no exemplo
        'Alimentos', 
        'Ferramentas', 
        'Limpeza', 
        'Escritório'
    ]
    for cat_name in default_categories:
        Categoria.objects.get_or_create(nome=cat_name)


# --- VIEWS DE ESTOQUE E PRODUTOS ---

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

    # TOTAIS
    total_de_produtos_cadastrados = Produto.objects.count()
    total_itens_estoque = Produto.objects.aggregate(total=Sum('quantidade_estoque'))['total'] or 0
    valor_total_estoque = Produto.objects.aggregate(total=Sum(F('custo') * F('quantidade_estoque')))['total'] or 0.00
    estoque_baixo_count = Produto.objects.filter(status='BAIXO').count()
    produtos_zerados_count = Produto.objects.filter(status='ZERADO').count()
    total_categorias = Categoria.objects.count()

    # VARIAÇÃO (Simulação simples de produtos novos no último mês)
    trinta_dias_atras = datetime.date.today() - datetime.timedelta(days=30)
    produtos_mes_anterior = Produto.objects.filter(data_criacao__date__lt=trinta_dias_atras).count()
    produtos_mes_atual = Produto.objects.filter(data_criacao__date__gte=trinta_dias_atras).count()
    variacao = produtos_mes_atual - produtos_mes_anterior
    
    # PAGINAÇÃO
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
        # CORREÇÃO: Passar request.FILES para o formulário para salvar a imagem
        form = ProdutoForm(request.POST, request.FILES) 
        if form.is_valid():
            produto = form.save()
            messages.success(request, f'Produto "{produto.nome}" criado com sucesso!')
            return redirect('estoque')
        else:
            messages.error(request, 'Erro ao salvar o produto. Verifique os dados inseridos.')
            
    else:
        form = ProdutoForm()
        messages.info(request, 'Lembre-se: o estoque inicial é 0. Use a função de Entrada para adicionar unidades.')
        
    return render(request, 'novo_produto.html', {'form': form})

@login_required
def editar_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        # CORREÇÃO: Passar request.FILES para o formulário ao editar a imagem
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Produto "{produto.nome}" atualizado com sucesso!')
            return redirect('detalhe_produto', pk=produto.pk)
        else:
             messages.error(request, 'Erro ao atualizar o produto. Verifique os dados inseridos.')
    else:
        form = ProdutoForm(instance=produto)
        
    return render(request, 'editar_produto.html', {'form': form, 'produto': produto})

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
            messages.success(request, f'Entrada de {movimento.quantidade} unidades de {movimento.produto.nome} registrada com sucesso.')
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
            messages.success(request, f'Adicionadas {quantidade} unidades ao estoque de {produto.nome}.')
            return redirect('estoque')
        else:
            messages.error(request, 'Erro ao registrar a entrada. Quantidade inválida.')
    else:
        form = EntradaProdutoEspecificoForm()
        
    return render(request, 'entrada_produto_especifico.html', {'form': form, 'produto': produto})


@login_required
def excluir_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    nome = produto.nome
    produto.delete()
    messages.success(request, f'O produto "{nome}" foi removido com sucesso.')
    return redirect('estoque')

def detalhes_produto_ajax(request, pk):
    p = Produto.objects.get(pk=pk)
    img = p.imagem.url if p.imagem else "/static/img/no-image.png"

    return JsonResponse({
        "nome": p.nome,
        "marca": p.marca,
        "sku": p.sku,
        "categoria": p.categoria.nome if p.categoria else "",
        "venda": f"{p.venda:.2f}",
        "quantidade": p.quantidade_estoque,
        "valor_total": f"{p.valor_total_estoque:.2f}",
        "status": p.status,
        "imagem": img,
    })

def editar_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    categorias = Categoria.objects.all()

    if request.method == "POST":
        produto.nome = request.POST.get("nome")
        produto.sku = request.POST.get("sku")
        produto.marca = request.POST.get("marca")
        produto.descricao = request.POST.get("descricao")
        produto.categoria_id = request.POST.get("categoria")
        produto.custo = request.POST.get("custo")
        produto.venda = request.POST.get("venda")
        produto.quantidade_minima_alerta = request.POST.get("quantidade_minima_alerta")
        produto.unidade_medida = request.POST.get("unidade_medida")
        produto.quantidade = request.POST.get("quantidade")

        produto.save()
        return redirect("estoque")

    return render(request, "edicao_produto.html", {
        "produto": produto,
        "categorias": categorias,
    })