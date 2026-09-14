import csv
import datetime
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDay
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from clientes.models import Cliente, LogAcao
from clientes.views import registrar_log
from vendas.models import ItemVenda, Venda

from .forms import (
    CustomUserCreationForm, EmailAuthenticationForm, EntradaProdutoEspecificoForm,
    FornecedorForm, MovimentoEstoqueForm, ProdutoForm,
)
from .models import Categoria, Fornecedor, MovimentoEstoque, Produto
from .utils import obter_data_formatada


def cadastro_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta criada com sucesso. Faça login.')
            return redirect('login')
        messages.error(request, 'Verifique os dados informados.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'cadastro.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password'),
            )
            if user is not None:
                login(request, user)
                destino = request.GET.get('next') or 'dashboard'
                return redirect(destino)
        messages.error(request, 'Email ou senha inválidos.')
    else:
        form = EmailAuthenticationForm()

    return render(request, 'login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


def calcular_crescimento(atual, anterior):
    if not anterior:
        return 100.0 if atual > 0 else 0.0
    return ((atual - anterior) / anterior) * 100


@login_required
def dashboard_view(request):
    hoje = timezone.localdate()
    ontem = hoje - datetime.timedelta(days=1)

    fechadas = Venda.objects.filter(status='fechada')

    vendas_hoje = fechadas.filter(data_venda__date=hoje).aggregate(
        t=Sum('total'))['t'] or Decimal('0')
    vendas_ontem = fechadas.filter(data_venda__date=ontem).aggregate(
        t=Sum('total'))['t'] or Decimal('0')

    itens = ItemVenda.objects.filter(venda__status='fechada')
    prod_hoje = itens.filter(venda__data_venda__date=hoje).aggregate(
        t=Sum('quantidade'))['t'] or Decimal('0')
    prod_ontem = itens.filter(venda__data_venda__date=ontem).aggregate(
        t=Sum('quantidade'))['t'] or Decimal('0')

    novos_hoje = Cliente.objects.filter(data_cadastro__date=hoje).count()
    novos_ontem = Cliente.objects.filter(data_cadastro__date=ontem).count()

    context = {
        'data_hoje': obter_data_formatada(hoje),
        'vendas_hoje': vendas_hoje,
        'perc_vendas': calcular_crescimento(float(vendas_hoje), float(vendas_ontem)),
        'produtos_vendidos': prod_hoje,
        'perc_produtos': calcular_crescimento(float(prod_hoje), float(prod_ontem)),
        'clientes_ativos': Cliente.objects.filter(status='ativo').count(),
        'perc_clientes': calcular_crescimento(novos_hoje, novos_ontem),
        'produtos_falta': Produto.objects.filter(
            controla_estoque=True,
            quantidade_estoque__lte=F('quantidade_minima_alerta'),
        ).count(),
        'vendas_recentes': Venda.objects.select_related('cliente').order_by('-data_venda')[:5],
    }
    return render(request, 'dashboard.html', context)


def _filtrar_produtos(request, queryset):
    """Filtros compartilhados entre a listagem e as exportações."""
    nome = request.GET.get('nome')
    sku = request.GET.get('sku')
    categoria = request.GET.get('categoria')
    status = request.GET.get('status')

    if nome:
        queryset = queryset.filter(
            Q(nome__icontains=nome) | Q(marca__icontains=nome)
        )
    if sku:
        queryset = queryset.filter(
            Q(sku__icontains=sku) | Q(codigo_barras__icontains=sku)
        )
    if categoria:
        queryset = queryset.filter(categoria_id=categoria)

    if status == 'ok':
        queryset = queryset.filter(quantidade_estoque__gt=F('quantidade_minima_alerta'))
    elif status == 'baixo':
        queryset = queryset.filter(
            quantidade_estoque__gt=0,
            quantidade_estoque__lte=F('quantidade_minima_alerta'),
        )
    elif status == 'zerado':
        queryset = queryset.filter(quantidade_estoque__lte=0)

    return queryset


@login_required
def estoque_view(request):
    produtos_list = _filtrar_produtos(
        request, Produto.objects.select_related('categoria')
    ).order_by('nome')

    agregados = Produto.objects.aggregate(
        total_itens=Sum('quantidade_estoque'),
        valor_total=Sum(F('custo') * F('quantidade_estoque')),
    )

    trinta_dias_atras = timezone.localdate() - datetime.timedelta(days=30)
    produtos_mes_atual = Produto.objects.filter(
        data_criacao__date__gte=trinta_dias_atras).count()
    produtos_mes_anterior = Produto.objects.filter(
        data_criacao__date__lt=trinta_dias_atras).count()

    paginator = Paginator(produtos_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'produtos': page_obj.object_list,
        'nome': request.GET.get('nome'),
        'sku': request.GET.get('sku'),
        'categoria': request.GET.get('categoria'),
        'status': request.GET.get('status'),
        'total_produtos_cadastrados': Produto.objects.count(),
        'valor_total_estoque': agregados['valor_total'] or Decimal('0.00'),
        'total_itens_estoque': agregados['total_itens'] or Decimal('0.000'),
        'estoque_baixo_count': Produto.objects.filter(
            controla_estoque=True,
            quantidade_estoque__gt=0,
            quantidade_estoque__lte=F('quantidade_minima_alerta'),
        ).count(),
        'sem_estoque_count': Produto.objects.filter(
            controla_estoque=True, quantidade_estoque__lte=0).count(),
        'total_categorias': Categoria.objects.count(),
        'variacao': produtos_mes_atual - produtos_mes_anterior,
        'categorias': Categoria.objects.all(),
        'data_hoje': obter_data_formatada(),
    }
    return render(request, 'estoque.html', context)


@login_required
def detalhe_produto_view(request, pk):
    produto = get_object_or_404(Produto.objects.select_related('categoria'), pk=pk)
    return render(request, 'detalhe_produto.html', {
        'produto': produto,
        'variacoes': produto.variacoes.all(),
        'historico': MovimentoEstoque.objects.filter(
            produto=produto).select_related('usuario')[:20],
        'data_hoje': obter_data_formatada(),
    })


@login_required
def novo_produto_view(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save()
            registrar_log(
                entidade='PRODUTO', entidade_id=produto.id, acao='CRIACAO',
                descricao=f'Produto "{produto.nome}" foi criado.',
                usuario=request.user,
            )
            messages.success(
                request,
                f'Produto "{produto.nome}" criado. Use "Entrada de Estoque" '
                f'para lançar o saldo inicial.',
            )
            return redirect('estoque')
        messages.error(request, 'Erro ao salvar o produto. Verifique os dados.')
    else:
        form = ProdutoForm()

    return render(request, 'novo_produto.html', {'form': form})


@login_required
def editar_produto_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            produto = form.save()
            registrar_log(
                entidade='PRODUTO', entidade_id=produto.id, acao='ALTERACAO',
                descricao=f'Produto "{produto.nome}" foi alterado.',
                usuario=request.user,
            )
            messages.success(request, f'Produto "{produto.nome}" atualizado.')
            return redirect('estoque')
        messages.error(request, 'Não foi possível salvar. Verifique os campos.')
    else:
        form = ProdutoForm(instance=produto)

    return render(request, 'edicao_produto.html', {
        'form': form,
        'produto': produto,
        'categorias': Categoria.objects.all(),
    })


@login_required
@require_POST
def excluir_produto_view(request, pk):
    """Exclusão só por POST: antes, um GET qualquer apagava o produto."""
    produto = get_object_or_404(Produto, pk=pk)
    nome = produto.nome

    if ItemVenda.objects.filter(produto=produto).exists():
        produto.ativo = False
        produto.save()
        messages.warning(
            request,
            f'"{nome}" tem vendas registradas e foi desativado em vez de excluído, '
            f'para preservar o histórico.',
        )
    else:
        produto.delete()
        messages.success(request, f'O produto "{nome}" foi removido.')

    registrar_log(
        entidade='PRODUTO', entidade_id=pk, acao='EXCLUSAO',
        descricao=f'Produto "{nome}" foi removido/desativado.',
        usuario=request.user,
    )
    return redirect('estoque')


@login_required
def entrada_estoque_geral_view(request):
    if request.method == 'POST':
        form = MovimentoEstoqueForm(request.POST)
        if form.is_valid():
            movimento = form.save(commit=False)
            movimento.tipo_movimento = 'ENTRADA'
            movimento.usuario = request.user
            movimento.save()
            registrar_log(
                entidade='ESTOQUE', entidade_id=movimento.produto.id, acao='ALTERACAO',
                descricao=(
                    f'Entrada de {movimento.produto.formatar_quantidade(movimento.quantidade)} '
                    f'do produto "{movimento.produto.nome}".'
                ),
                usuario=request.user,
            )
            messages.success(
                request,
                f'Entrada de {movimento.produto.formatar_quantidade(movimento.quantidade)} '
                f'de {movimento.produto.nome} registrada.',
            )
            return redirect('estoque')
        messages.error(request, 'Não foi possível registrar a entrada.')
    else:
        form = MovimentoEstoqueForm()

    return render(request, 'entrada_estoque_geral.html', {'form': form})


@login_required
def adicionar_estoque_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    if request.method == 'POST':
        form = EntradaProdutoEspecificoForm(request.POST, produto=produto)
        if form.is_valid():
            movimento = form.save(commit=False)
            movimento.produto = produto
            movimento.tipo_movimento = 'ENTRADA'
            movimento.usuario = request.user
            movimento.save()
            messages.success(
                request,
                f'Adicionado {produto.formatar_quantidade(movimento.quantidade)} '
                f'ao estoque de {produto.nome}.',
            )
            return redirect('estoque')
        messages.error(request, 'Quantidade inválida para esta unidade de medida.')
    else:
        form = EntradaProdutoEspecificoForm(produto=produto)

    return render(request, 'entrada_produto_especifico.html', {
        'form': form,
        'produto': produto,
    })


@login_required
def detalhes_produto_ajax(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    return JsonResponse({
        'nome': produto.nome,
        'sku': produto.sku,
        'categoria': produto.categoria.nome if produto.categoria else '',
        'descricao': produto.descricao or '',
        'custo': f'{produto.custo:.2f}',
        'venda': f'{produto.venda:.2f}',
        'unidade': produto.get_unidade_medida_display(),
        'sigla': produto.sigla_unidade,
        'quantidade': produto.estoque_formatado,
        'quantidade_minima': produto.formatar_quantidade(produto.quantidade_minima_alerta),
        'status': produto.get_status_display(),
    })


@login_required
def fornecedores_view(request):
    fornecedores = Fornecedor.objects.all()
    search_query = (request.GET.get('search') or '').strip()

    if search_query:
        fornecedores = fornecedores.filter(
            Q(nome_fantasia__icontains=search_query)
            | Q(cnpj__icontains=search_query)
            | Q(contato_principal__icontains=search_query)
        )

    paginator = Paginator(fornecedores, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'fornecedores.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_fornecedores': paginator.count,
        'data_hoje': obter_data_formatada(),
    })


@login_required
def fornecedor_criar(request):
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            fornecedor = form.save()
            registrar_log(
                entidade='FORNECEDOR', entidade_id=fornecedor.id, acao='CRIACAO',
                descricao=f'Fornecedor "{fornecedor.nome_fantasia}" criado.',
                usuario=request.user,
            )
            messages.success(request, 'Fornecedor cadastrado com sucesso!')
            return redirect('fornecedores')
    else:
        form = FornecedorForm()

    return render(request, 'fornecedor_form.html', {
        'form': form,
        'titulo': 'Novo Fornecedor',
        'action': 'criar',
        'data_hoje': obter_data_formatada(),
    })


@login_required
def fornecedor_editar(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)

    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            fornecedor = form.save()
            registrar_log(
                entidade='FORNECEDOR', entidade_id=fornecedor.id, acao='ALTERACAO',
                descricao=f'Fornecedor "{fornecedor.nome_fantasia}" editado.',
                usuario=request.user,
            )
            messages.success(request, 'Fornecedor atualizado com sucesso!')
            return redirect('fornecedores')
    else:
        form = FornecedorForm(instance=fornecedor)

    return render(request, 'fornecedor_form.html', {
        'form': form,
        'titulo': 'Editar Fornecedor',
        'action': 'editar',
        'fornecedor': fornecedor,
        'data_hoje': obter_data_formatada(),
    })


@login_required
def fornecedor_deletar(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)

    if request.method == 'POST':
        nome, id_antigo = fornecedor.nome_fantasia, fornecedor.id
        fornecedor.delete()
        registrar_log(
            entidade='FORNECEDOR', entidade_id=id_antigo, acao='EXCLUSAO',
            descricao=f'Fornecedor "{nome}" foi excluído.',
            usuario=request.user,
        )
        messages.success(request, f'Fornecedor "{nome}" deletado com sucesso!')
        return redirect('fornecedores')

    return render(request, 'fornecedor_confirmar_delete.html', {
        'fornecedor': fornecedor,
        'data_hoje': obter_data_formatada(),
    })


def _escrever_csv(nome_arquivo, cabecalho, linhas):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    response.write('﻿')
    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(cabecalho)
    writer.writerows(linhas)
    return response


@login_required
def exportar_estoque_csv(request):
    produtos = _filtrar_produtos(
        request, Produto.objects.select_related('categoria')
    ).order_by('nome')

    linhas = [
        [
            p.nome, p.sku, p.codigo_barras or '',
            p.categoria.nome if p.categoria else 'N/A',
            p.marca or '',
            p.get_unidade_medida_display(),
            f'{p.custo:.2f}'.replace('.', ','),
            f'{p.venda:.2f}'.replace('.', ','),
            p.estoque_formatado,
            p.get_status_display(),
        ]
        for p in produtos
    ]
    return _escrever_csv(
        'estoque.csv',
        ['Produto', 'SKU', 'Cód. Barras', 'Categoria', 'Marca', 'Unidade',
         'Custo', 'Venda', 'Estoque', 'Status'],
        linhas,
    )


@login_required
def imprimir_codigos_estoque(request):
    produtos = _filtrar_produtos(request, Produto.objects.all()).order_by('nome')
    linhas = [[p.nome, p.sku, p.codigo_barras or ''] for p in produtos]
    return _escrever_csv('lista_skus.csv', ['Produto', 'SKU', 'Cód. Barras'], linhas)


@login_required
def relatorios(request):
    hoje = timezone.now()
    try:
        dias = max(1, min(int(request.GET.get('dias', 30)), 365))
    except (TypeError, ValueError):
        dias = 30
    inicio = hoje - datetime.timedelta(days=dias)

    vendas_periodo = Venda.objects.filter(
        data_venda__range=[inicio, hoje], status='fechada'
    )
    itens_periodo = ItemVenda.objects.filter(
        venda__in=vendas_periodo
    ).select_related('produto')

    kpi_total_vendas = vendas_periodo.aggregate(Sum('total'))['total__sum'] or Decimal('0')
    qtd_vendas = vendas_periodo.count()

    kpi_lucro = sum(
        ((item.preco_unitario - (item.produto.custo or 0)) * item.quantidade
         for item in itens_periodo),
        Decimal('0'),
    )

    vendas_por_dia = (
        vendas_periodo.annotate(day=TruncDay('data_venda'))
        .values('day').annotate(total=Sum('total')).order_by('day')
    )
    vendas_por_cat = (
        itens_periodo.values('produto__categoria__nome')
        .annotate(total=Sum(F('quantidade') * F('preco_unitario')))
        .order_by('-total')
    )

    context = {
        'dias': dias,
        'kpi_total_vendas': kpi_total_vendas,
        'kpi_lucro': kpi_lucro,
        'kpi_novos_clientes': Cliente.objects.filter(
            data_cadastro__range=[inicio, hoje]).count(),
        'kpi_ticket_medio': (kpi_total_vendas / qtd_vendas) if qtd_vendas else Decimal('0'),
        'chart_dates': json.dumps([v['day'].strftime('%d/%m') for v in vendas_por_dia]),
        'chart_values': json.dumps([float(v['total']) for v in vendas_por_dia]),
        'cat_labels': json.dumps([
            item['produto__categoria__nome'] or 'Sem Categoria' for item in vendas_por_cat
        ]),
        'cat_values': json.dumps([float(item['total']) for item in vendas_por_cat]),
        'top_produtos': itens_periodo.values('produto__nome', 'produto__id').annotate(
            qtd=Sum('quantidade'), val=Sum(F('quantidade') * F('preco_unitario'))
        ).order_by('-val')[:5],
        'top_clientes': vendas_periodo.exclude(cliente=None).values('cliente__nome').annotate(
            total_comprado=Sum('total'), qtd_compras=Count('id')
        ).order_by('-total_comprado')[:5],
        'data_hoje': obter_data_formatada(),
    }
    return render(request, 'relatorios.html', context)
