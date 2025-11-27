from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm, EmailAuthenticationForm, ProdutoForm, BuscaEstoqueForm, MovimentoEstoqueForm, EntradaProdutoEspecificoForm, FornecedorForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Q, Count
from django.core.paginator import Paginator
import datetime
import locale
from django.http import JsonResponse
from .models import Categoria, Produto, MovimentoEstoque, Fornecedor
from .messages.estoque_storage import EstoqueStorage
from django.contrib.messages.constants import INFO, SUCCESS, ERROR
from django.db.models import Sum
from django.utils import timezone
from vendas.models import Venda, ItemVenda
from clientes.models import Cliente, LogAcao
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.db.models.functions import TruncDay
import json

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

@login_required
def estoque_view(request): 
    search_query = request.GET.get('search', '')
    produtos = Produto.objects.all()

    if search_query:
        produtos = produtos.filter(
            Q(nome__icontains=search_query) | 
            Q(sku__icontains=search_query)
        )

    paginator = Paginator(produtos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    return render(request, 'estoque.html', context)

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
def entrada_estoque_geral_view(request):
    from .forms import MovimentoEstoqueForm 
    
    if request.method == 'POST':
        form = MovimentoEstoqueForm(request.POST)
        if form.is_valid():
            movimento = form.save(commit=False)
            movimento.tipo_movimento = 'ENTRADA'
            movimento.save()
            LogAcao.objects.create(
                entidade="ESTOQUE",
                entidade_id=movimento.produto.id,
                acao="ALTERACAO",
                descricao=f'Entrada de {movimento.quantidade} unidades para o produto "{movimento.produto.nome}".',
                usuario=request.user
            )

            return redirect('estoque')
    else:
        form = MovimentoEstoqueForm()
    
    return render(request, 'contas/entrada_estoque_geral.html', {'form': form})

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

    produtos_falta = Produto.objects.filter(
        quantidade_estoque__lte=F('quantidade_minima_alerta')
    ).count()

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
def novo_produto_view(request):
    from .forms import ProdutoForm 

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save()

            LogAcao.objects.create(
                entidade="PRODUTO",
                entidade_id=produto.id,
                acao="CRIACAO",
                descricao=f'Produto "{produto.nome}" foi criado.',
                usuario=request.user
            )
            return redirect('estoque')
    else:
        form = ProdutoForm()
    
    return render(request, 'contas/novo_produto.html', {'form': form})
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
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            # Salva o fornecedor e guarda a instância criada na variável 'fornecedor'
            fornecedor = form.save()
            
            # Agora sim podemos acessar fornecedor.nome_fantasia
            LogAcao.objects.create(
                entidade="FORNECEDOR",
                entidade_id=fornecedor.id, # Agora funciona!
                acao="CRIACAO",
                descricao=f'Fornecedor "{fornecedor.nome_fantasia}" criado.',
                usuario=request.user
            )
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
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            fornecedor_salvo = form.save()
            
            LogAcao.objects.create(
                entidade="FORNECEDOR",
                entidade_id=fornecedor_salvo.id,
                acao="ALTERACAO",
                descricao=f'Fornecedor "{fornecedor_salvo.nome_fantasia}" editado.',
                usuario=request.user
            )
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
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    
    if request.method == 'POST':
        nome = fornecedor.nome_fantasia
        # Salva o ID antes de deletar para usar no log (opcional, mas boa prática)
        id_antigo = fornecedor.id 
        
        fornecedor.delete()
        
        LogAcao.objects.create(
            entidade="FORNECEDOR",
            entidade_id=id_antigo,
            acao="EXCLUSAO",
            descricao=f'Fornecedor "{nome}" foi excluído.',
            usuario=request.user
        )
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
    nome = request.GET.get("nome")
    sku = request.GET.get("sku")
    categoria = request.GET.get("categoria")
    status = request.GET.get("status")

    produtos_list = Produto.objects.all()

    if nome:
        produtos_list = produtos_list.filter(nome__icontains=nome)

    if sku:
        produtos_list = produtos_list.filter(sku__icontains=sku)

    if categoria:
        produtos_list = produtos_list.filter(categoria_id=categoria)

    if status:
        if status == "ok":
            produtos_list = produtos_list.filter(
                quantidade_estoque__gt=F("quantidade_minima_alerta")
            )
        elif status == "baixo":
            produtos_list = produtos_list.filter(
                quantidade_estoque__gt=0,
                quantidade_estoque__lte=F("quantidade_minima_alerta")
            )
        elif status == "zerado":
            produtos_list = produtos_list.filter(quantidade_estoque=0)

    produtos_list = produtos_list.order_by('nome')

    total_de_produtos_cadastrados = Produto.objects.count()
    total_itens_estoque = Produto.objects.aggregate(total=Sum('quantidade_estoque'))['total'] or 0
    valor_total_estoque = Produto.objects.aggregate(total=Sum(F('custo') * F('quantidade_estoque')))['total'] or 0.00

    estoque_baixo_count = Produto.objects.filter(
        quantidade_estoque__gt=0,
        quantidade_estoque__lte=F("quantidade_minima_alerta")
    ).count()

    produtos_zerados_count = Produto.objects.filter(
        quantidade_estoque=0
    ).count()

    total_categorias = Categoria.objects.count()

    trinta_dias_atras = datetime.date.today() - datetime.timedelta(days=30)

    produtos_mes_anterior = Produto.objects.filter(data_criacao__date__lt=trinta_dias_atras).count()
    produtos_mes_atual = Produto.objects.filter(data_criacao__date__gte=trinta_dias_atras).count()
    variacao = produtos_mes_atual - produtos_mes_anterior

    paginator = Paginator(produtos_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'produtos': page_obj.object_list,
        'nome': nome,
        'sku': sku,
        'categoria': categoria,
        'status': status,
        'total_produtos_cadastrados': total_de_produtos_cadastrados,
        'valor_total_estoque': valor_total_estoque,
        'estoque_baixo_count': estoque_baixo_count,
        'sem_estoque_count': produtos_zerados_count,
        'total_categorias': total_categorias,
        'total_itens_estoque': total_itens_estoque,
        'variacao': variacao,
        'categorias': Categoria.objects.all(),
    }

    return render(request, 'estoque.html', context)

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
            LogAcao.objects.create(
                entidade="ESTOQUE",
                entidade_id=movimento.produto.id,
                acao="ALTERACAO",
                descricao=f'Movimento de estoque: {movimento.tipo_movimento} — {movimento.quantidade} unidades do produto "{movimento.produto.nome}".',
                usuario=request.user
            )
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
    LogAcao.objects.create(
        entidade="PRODUTO",
        entidade_id=pk,
        acao="EXCLUSAO",
        descricao=f'Produto "{nome}" foi excluído do sistema.',
        usuario=request.user
    )
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

        LogAcao.objects.create(
            entidade="PRODUTO",
            entidade_id=produto.id,
            acao="ALTERACAO",
            descricao=f'Produto "{produto.nome}" foi alterado.',
            usuario=request.user
        )
        add_estoque_message(request, f'Produto "{produto.nome}" atualizado com sucesso!', level=SUCCESS)
        return redirect("estoque")
    return render(request, "edicao_produto.html", {"produto": produto, "categorias": categorias})

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
def relatorios(request):
    return render(request, 'relatorios.html')

@login_required
def exportar_estoque_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="estoque.csv"'
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Produto', 'SKU', 'Categoria', 'Marca', 'Custo', 'Venda', 'Estoque', 'Status'])

    produtos = Produto.objects.all().order_by('nome')
    
    nome = request.GET.get("nome")
    sku = request.GET.get("sku")
    categoria = request.GET.get("categoria")
    status = request.GET.get("status")

    if nome:
        produtos = produtos.filter(nome__icontains=nome)
    if sku:
        produtos = produtos.filter(sku__icontains=sku)
    if categoria:
        produtos = produtos.filter(categoria_id=categoria)
    if status:
        if status == "ok":
            produtos = produtos.filter(quantidade_estoque__gt=F("quantidade_minima_alerta"))
        elif status == "baixo":
            produtos = produtos.filter(quantidade_estoque__gt=0, quantidade_estoque__lte=F("quantidade_minima_alerta"))
        elif status == "zerado":
            produtos = produtos.filter(quantidade_estoque=0)

    for p in produtos:
        writer.writerow([
            p.nome,
            p.sku,
            p.categoria.nome if p.categoria else 'N/A',
            p.marca or '',
            f"{p.custo:.2f}".replace('.', ','),
            f"{p.venda:.2f}".replace('.', ','),
            p.quantidade_estoque,
            p.get_status_display()
        ])

    return response

@login_required
def imprimir_codigos_estoque(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lista_skus.csv"'
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow(['Produto', 'SKU'])

    produtos = Produto.objects.all().order_by('nome')
    
    nome = request.GET.get("nome")
    sku = request.GET.get("sku")
    categoria = request.GET.get("categoria")
    status = request.GET.get("status")

    if nome:
        produtos = produtos.filter(nome__icontains=nome)
    if sku:
        produtos = produtos.filter(sku__icontains=sku)
    if categoria:
        produtos = produtos.filter(categoria_id=categoria)
    if status:
        if status == "ok":
            produtos = produtos.filter(quantidade_estoque__gt=F("quantidade_minima_alerta"))
        elif status == "baixo":
            produtos = produtos.filter(quantidade_estoque__gt=0, quantidade_estoque__lte=F("quantidade_minima_alerta"))
        elif status == "zerado":
            produtos = produtos.filter(quantidade_estoque=0)

    for p in produtos:
        writer.writerow([
            p.nome,
            p.sku,
        ])

    return response

@login_required
def relatorios(request):
    hoje = timezone.now()
    inicio_mes = hoje - datetime.timedelta(days=30)
    
    vendas_periodo = Venda.objects.filter(data_venda__range=[inicio_mes, hoje], status='fechada')
    itens_periodo = ItemVenda.objects.filter(venda__in=vendas_periodo)
    
    kpi_total_vendas = vendas_periodo.aggregate(Sum('total'))['total__sum'] or 0
    
    qtd_vendas = vendas_periodo.count()
    kpi_ticket_medio = kpi_total_vendas / qtd_vendas if qtd_vendas > 0 else 0
    
    kpi_novos_clientes = Cliente.objects.filter(data_cadastro__range=[inicio_mes, hoje]).count()
    
    kpi_lucro = 0
    for item in itens_periodo:
        custo = item.produto.custo or 0
        receita = item.preco_unitario
        qtd = item.quantidade
        kpi_lucro += (receita - custo) * qtd

    vendas_por_dia = vendas_periodo.annotate(day=TruncDay('data_venda')) \
        .values('day') \
        .annotate(total=Sum('total')) \
        .order_by('day')
    
    chart_dates = [v['day'].strftime('%d/%m') for v in vendas_por_dia]
    chart_values = [float(v['total']) for v in vendas_por_dia]

    vendas_por_cat = itens_periodo.values('produto__categoria__nome') \
        .annotate(total=Sum(F('quantidade') * F('preco_unitario'))) \
        .order_by('-total')
    
    cat_labels = [item['produto__categoria__nome'] if item['produto__categoria__nome'] else 'Sem Categoria' for item in vendas_por_cat]
    cat_values = [float(item['total']) for item in vendas_por_cat]

    top_produtos = itens_periodo.values('produto__nome', 'produto__id') \
        .annotate(qtd=Sum('quantidade'), val=Sum(F('quantidade') * F('preco_unitario'))) \
        .order_by('-val')[:5]

    top_clientes = vendas_periodo.values('cliente__nome') \
        .annotate(total_comprado=Sum('total'), qtd_compras=Count('id')) \
        .order_by('-total_comprado')[:5]

    context = {
        'kpi_total_vendas': kpi_total_vendas,
        'kpi_lucro': kpi_lucro,
        'kpi_novos_clientes': kpi_novos_clientes,
        'kpi_ticket_medio': kpi_ticket_medio,
        
        'chart_dates': json.dumps(chart_dates),
        'chart_values': json.dumps(chart_values),
        'cat_labels': json.dumps(cat_labels),
        'cat_values': json.dumps(cat_values),
        
        'top_produtos': top_produtos,
        'top_clientes': top_clientes,
        
        'data_hoje': obter_data_formatada(),
    }
    
    return render(request, 'relatorios.html', context)
