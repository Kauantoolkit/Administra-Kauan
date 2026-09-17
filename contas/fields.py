"""
Campo decimal que entende o jeito brasileiro de escrever números.

O sistema é para lojas no Brasil, onde se digita "2,500" e "1.234,56". O
DecimalField do Django só aceita ponto como separador decimal, então quem
digitava vírgula tinha o valor recusado — ou, em campos `type="number"`, o
próprio navegador considerava a entrada inválida e enviava vazio, resultando
num "campo obrigatório" sem explicação.
"""

from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError


def normalizar_decimal(texto):
    """
    Converte texto em formato brasileiro ou internacional para Decimal.

        "1.234,56" -> 1234.56   (ponto de milhar, vírgula decimal)
        "2,500"    -> 2.5       (vírgula decimal)
        "2.500"    -> 2.5       (ponto decimal, como envia <input type=number>)
        "1234.56"  -> 1234.56
    """
    if texto is None:
        return None
    if isinstance(texto, Decimal):
        return texto
    if isinstance(texto, (int, float)):
        return Decimal(str(texto))

    valor = str(texto).strip().replace(' ', '').replace('R$', '')
    if not valor:
        return None

    tem_ponto, tem_virgula = '.' in valor, ',' in valor

    if tem_ponto and tem_virgula:
        # O último separador que aparece é o decimal.
        if valor.rfind(',') > valor.rfind('.'):
            valor = valor.replace('.', '').replace(',', '.')
        else:
            valor = valor.replace(',', '')
    elif tem_virgula:
        # Só vírgula: é o separador decimal. Múltiplas viram milhar.
        if valor.count(',') > 1:
            valor = valor.replace(',', '')
        else:
            valor = valor.replace(',', '.')
    elif valor.count('.') > 1:
        # Só pontos, mais de um: só podem ser milhar ("1.234.567").
        valor = valor.replace('.', '')

    try:
        return Decimal(valor)
    except InvalidOperation as exc:
        raise ValidationError('Informe um número válido.') from exc


class DecimalBrField(forms.DecimalField):
    """
    DecimalField que aceita vírgula como separador decimal.

    Usa TextInput em vez de NumberInput de propósito: `<input type="number">`
    recusa a vírgula no próprio navegador, e o valor digitado nem chega ao
    servidor. `inputmode="decimal"` mantém o teclado numérico no celular.
    """

    widget = forms.TextInput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs.setdefault('inputmode', 'decimal')

    def to_python(self, value):
        if value in self.empty_values:
            return None
        return super().to_python(normalizar_decimal(value))
