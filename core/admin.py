from django.contrib import admin
from .models import Categoria, Pagador, Emitente, Transacao

admin.site.register(Categoria)
admin.site.register(Pagador)
admin.site.register(Emitente)
admin.site.register(Transacao)