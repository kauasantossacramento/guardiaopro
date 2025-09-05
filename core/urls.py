from django.urls import path
from .views import dashboard, relatorio_mensal, adicionar_transacao, configurar_categorias, adicionar_pagador, exportar_pdf, get_categorias, transacao_json, adicionar_comprovante, editar_transacao, anular_transacao, importar_csv, relatorio_financeiro, contas_a_pagar, excluir_conta, marcar_como_paga, sair # Adicione exportar_pdf aqui

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('relatorio/<int:ano>/<int:mes>/', relatorio_mensal, name='relatorio_mensal'),
    path('adicionar-transacao/', adicionar_transacao, name='adicionar_transacao'),
    path('configurar-categorias/', configurar_categorias, name='configurar_categorias'),
    path('adicionar-pagador/', adicionar_pagador, name='adicionar_pagador'),
    path('exportar-pdf/', exportar_pdf, name='exportar_pdf'),  # Adicione esta linha
    path('get-categorias/', get_categorias, name='get_categorias'),
    path('transacao/<int:transacao_id>/json/', transacao_json, name='transacao_json'),
    path('transacao/<int:transacao_id>/adicionar-comprovante/', adicionar_comprovante, name='adicionar_comprovante'),
    path('transacao/<int:transacao_id>/editar/', editar_transacao, name='editar_transacao'),
    path('transacao/<int:transacao_id>/anular/', anular_transacao, name='anular_transacao'),
    path('importar-csv/', importar_csv, name='importar_csv'),
    path('relatorio/', relatorio_financeiro, name='relatorio_financeiro'),
    path('contas-a-pagar/', contas_a_pagar, name='contas_a_pagar'),
    path('conta/<int:conta_id>/excluir/', excluir_conta, name='excluir_conta'),
    path('conta/<int:conta_id>/pagar/', marcar_como_paga, name='marcar_como_paga'),
    path('sair/', sair, name='sair'),
]