from django.db import models
from solo.models import SingletonModel

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=[('entrada', 'Entrada'), ('saida', 'Saída')])

    def __str__(self):
        return self.nome

class Pagador(models.Model):
    nome = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='pagadores/', blank=True, null=True)

    def __str__(self):
        return self.nome

class Emitente(SingletonModel):
    nome = models.CharField(max_length=100, default='Minha Empresa')
    logo = models.ImageField(upload_to='emitentes/', blank=True, null=True)

    def __str__(self):
        return self.nome

class Transacao(models.Model):
    TIPO_CHOICES = [('entrada', 'Entrada'), ('saida', 'Saída')]
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    descricao = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True, default=None)
    pagador = models.ForeignKey(Pagador, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.tipo} - R${self.valor} ({self.data})"
    
class DocumentoComprobatório(models.Model):
    transacao = models.ForeignKey(Transacao, on_delete=models.CASCADE, related_name='documentos')
    arquivo = models.FileField(upload_to='comprovantes/')
    data_envio = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Documento para {self.transacao} enviado em {self.data_envio}"

from django.db import models

class UnidadePagadora(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome

class Instituicao(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome
    
class ContaPagar(models.Model):
    unidade_pagadora = models.CharField(max_length=100)
    instituicao = models.CharField(max_length=100)
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    vencimento = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('atrasado', 'Atrasado')
    ], default='pendente')

    def __str__(self):
        return f"{self.descricao} - R${self.valor:.2f}"