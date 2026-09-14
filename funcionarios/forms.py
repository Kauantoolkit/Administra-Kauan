import base64

from django import forms
from django.core.exceptions import ValidationError

from contas.forms import formatar_cpf, validar_cpf
from .models import Funcionario

# A foto vai para o banco em base64: sem limite, um upload grande incha a
# tabela e a resposta de toda tela que lista funcionarios.
TAMANHO_MAXIMO_FOTO = 2 * 1024 * 1024  # 2 MB
TIPOS_FOTO_ACEITOS = ('image/jpeg', 'image/png', 'image/webp')

class FuncionarioForm(forms.ModelForm):

    foto_upload = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-input', 'id': 'id_foto', 'accept': 'image/*',
        }),
        help_text='JPEG, PNG ou WebP, até 2 MB.',
    )

    def clean_foto_upload(self):
        arquivo = self.cleaned_data.get('foto_upload')
        if not arquivo:
            return arquivo
        if arquivo.size > TAMANHO_MAXIMO_FOTO:
            raise ValidationError('A foto deve ter no máximo 2 MB.')
        if getattr(arquivo, 'content_type', None) not in TIPOS_FOTO_ACEITOS:
            raise ValidationError('Envie uma imagem JPEG, PNG ou WebP.')
        return arquivo

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not validar_cpf(cpf):
            raise ValidationError('CPF inválido.')
        cpf = formatar_cpf(cpf)
        existentes = Funcionario.objects.filter(cpf=cpf)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise ValidationError('Já existe um funcionário com este CPF.')
        return cpf

    def clean_salario(self):
        salario = self.cleaned_data.get('salario')
        if salario is not None and salario < 0:
            raise ValidationError('O salário não pode ser negativo.')
        return salario

    class Meta:
        model = Funcionario
        fields = [
            'nome',
            'cpf',
            'cargo',
            'email',
            'telefone',
            'salario',
            'data_admissao',
            'status',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input'}),
            'cargo': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input'}),
            'salario': forms.NumberInput(attrs={'class': 'form-input'}),
            'data_admissao': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)

        arquivo = self.cleaned_data.get("foto_upload")

        if arquivo:
            arquivo.seek(0)
            data = arquivo.read()
            instance.foto_base64 = base64.b64encode(data).decode("utf-8")

        if commit:
            instance.save()

        return instance
