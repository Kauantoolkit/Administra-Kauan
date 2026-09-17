"""
Permissões por papel.

O campo `papel` existia no modelo mas não barrava nada: qualquer pessoa que
entrasse no sistema via salários, relatórios e podia apagar produtos. Aqui
cada papel recebe um conjunto explícito de capacidades, e as views pedem a
capacidade — não o papel. Assim dá para reorganizar papéis sem caçar
condicionais espalhadas pelo código.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

# Capacidades reconhecidas pelo sistema.
VENDER = 'vender'
ANULAR_VENDA = 'anular_venda'
VER_ESTOQUE = 'ver_estoque'
GERENCIAR_PRODUTOS = 'gerenciar_produtos'
MOVIMENTAR_ESTOQUE = 'movimentar_estoque'
VER_CLIENTES = 'ver_clientes'
GERENCIAR_CLIENTES = 'gerenciar_clientes'
VER_FORNECEDORES = 'ver_fornecedores'
GERENCIAR_FORNECEDORES = 'gerenciar_fornecedores'
VER_FUNCIONARIOS = 'ver_funcionarios'
GERENCIAR_FUNCIONARIOS = 'gerenciar_funcionarios'
VER_RELATORIOS = 'ver_relatorios'
VER_HISTORICO = 'ver_historico'
CONFIGURAR_LOJA = 'configurar_loja'

TODAS = frozenset({
    VENDER, ANULAR_VENDA, VER_ESTOQUE, GERENCIAR_PRODUTOS, MOVIMENTAR_ESTOQUE,
    VER_CLIENTES, GERENCIAR_CLIENTES, VER_FORNECEDORES, GERENCIAR_FORNECEDORES,
    VER_FUNCIONARIOS, GERENCIAR_FUNCIONARIOS, VER_RELATORIOS, VER_HISTORICO,
    CONFIGURAR_LOJA,
})

# Operador de caixa vende e atende cliente. Nao vê salário, relatório de lucro
# nem apaga cadastro. Estoquista cuida de produto e fornecedor, e não vende.
CAPACIDADES_POR_PAPEL = {
    'PROPRIETARIO': TODAS,
    'GERENTE': TODAS - {CONFIGURAR_LOJA},
    'OPERADOR': frozenset({
        VENDER, VER_ESTOQUE, VER_CLIENTES, GERENCIAR_CLIENTES,
    }),
    'ESTOQUISTA': frozenset({
        VER_ESTOQUE, GERENCIAR_PRODUTOS, MOVIMENTAR_ESTOQUE,
        VER_FORNECEDORES, GERENCIAR_FORNECEDORES,
    }),
}


def capacidades(usuario):
    """Conjunto de capacidades do usuário. Superusuário tem todas."""
    if not usuario or not usuario.is_authenticated:
        return frozenset()
    if usuario.is_superuser:
        return TODAS
    return CAPACIDADES_POR_PAPEL.get(getattr(usuario, 'papel', ''), frozenset())


def pode(usuario, capacidade):
    return capacidade in capacidades(usuario)


def requer(*capacidades_exigidas):
    """
    Exige login e ao menos uma das capacidades informadas.

    Quem não tem é mandado para o painel com uma explicação, em vez de ver uma
    tela de erro seca — o operador precisa entender que aquilo não é função
    dele, não que o sistema quebrou.
    """
    def decorador(view):
        @wraps(view)
        def _wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            minhas = capacidades(request.user)
            if not minhas.intersection(capacidades_exigidas):
                messages.error(
                    request,
                    'Seu perfil de acesso não permite esta operação. '
                    'Fale com o responsável pela loja.',
                )
                return redirect('dashboard')
            return view(request, *args, **kwargs)
        return _wrapper
    return decorador
