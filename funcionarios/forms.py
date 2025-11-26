from django import forms
from .models import Funcionario
import base64

class FuncionarioForm(forms.ModelForm):

    foto_upload = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-input', 'id': 'id_foto'})
    )

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

        arquivo = self.files.get("foto_upload")

        if arquivo:
            data = arquivo.read()
            instance.foto_base64 = base64.b64encode(data).decode("utf-8")

        if commit:
            instance.save()

        return instance
