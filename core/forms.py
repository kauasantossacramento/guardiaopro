from django import forms
from .models import Transacao, Categoria, Pagador
from django import forms
from django.core.exceptions import ValidationError
from django import forms
from .models import Categoria

class FiltroMensalForm(forms.Form):
    mes = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        label='Mês'
    )
    ano = forms.IntegerField(
        required=False,
        min_value=2000,
        max_value=2100,
        label='Ano'
    )
    tipo = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Selecione...'),
            ('entrada', 'Entrada'),
            ('saida', 'Saída')
        ],
        label='Tipo'
    )
    categoria = forms.MultipleChoiceField(
        required=False,
        choices=[],
        label='Categoria',
        widget=forms.SelectMultiple
    )
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data Início'
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data Fim'
    )

    def __init__(self, *args, **kwargs):
        super(FiltroMensalForm, self).__init__(*args, **kwargs)
        self.fields['categoria'].choices = [
            (str(cat.id), cat.nome) for cat in Categoria.objects.all()
        ]
class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['tipo', 'valor', 'data', 'descricao', 'categoria', 'pagador']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.none()
        self.fields['pagador'].required = False
        if 'tipo' in self.data:
            try:
                tipo = self.data.get('tipo')
                self.fields['categoria'].queryset = Categoria.objects.filter(tipo=tipo)
            except Categoria.DoesNotExist:
                self.fields['categoria'].queryset = Categoria.objects.none()
        elif self.instance.pk:
            self.fields['categoria'].queryset = Categoria.objects.filter(tipo=self.instance.tipo)
        else:
            self.fields['categoria'].queryset = Categoria.objects.none()  # Fallback vazio até o tipo ser selecionado

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo']

class PagadorForm(forms.ModelForm):
    class Meta:
        model = Pagador
        fields = ['nome', 'logo']

class ImportarCSVForm(forms.Form):
    csv_file = forms.FileField(label="Arquivo CSV")

from .models import ContaPagar

class ContaPagarForm(forms.ModelForm):
    class Meta:
        model = ContaPagar
        fields = ['unidade_pagadora', 'instituicao', 'descricao', 'valor', 'vencimento', 'status']
        widgets = {
            'unidade_pagadora': forms.TextInput(attrs={'placeholder': 'Ex: Valença FM'}),
            'instituicao': forms.TextInput(attrs={'placeholder': 'Ex: Banco XYZ'}),
            'descricao': forms.Textarea(attrs={'rows': 2}),
            'vencimento': forms.DateInput(attrs={'type': 'date'}),
        }