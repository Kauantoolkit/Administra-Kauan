from .models import ConfiguracaoLoja


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
    return {'loja': config}
