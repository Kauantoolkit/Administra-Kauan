"""Utilitários sem dependência de locale do sistema operacional."""

import datetime

MESES_PT = (
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
)


def obter_data_formatada(data=None):
    """
    Data por extenso em português, ex.: '14 de setembro de 2026'.

    Antes isto usava `locale.setlocale(LC_TIME, 'pt_BR.UTF-8')`, que derruba o
    dashboard com `locale.Error` em qualquer servidor sem o locale pt_BR
    gerado — o caso normal em containers e VPS enxutas.
    """
    data = data or datetime.date.today()
    return f'{data.day} de {MESES_PT[data.month - 1]} de {data.year}'
