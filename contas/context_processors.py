from .models import ConfiguracaoLoja, CustomUser
from .permissoes import capacidades


def identidade_loja(request):
    """
    Disponibiliza a identidade da loja (nome, logo, cor, moeda) em todos os
    templates, para que o mesmo sistema seja revendido com a marca do cliente.
    """
    try:
        config = ConfiguracaoLoja.obter()
    except Exception:
        # Antes da primeira migração o banco ainda não tem a tabela.
        config = None
    try:
        instalacao_pendente = not CustomUser.objects.exists()
    except Exception:
        instalacao_pendente = False

    return {
        'loja': config,
        'instalacao_pendente': instalacao_pendente,
        'pode': {c: True for c in capacidades(getattr(request, 'user', None))},
    }
