from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import TransacaoForm, CategoriaForm, PagadorForm, FiltroMensalForm
from .models import Transacao, Categoria, Pagador, Emitente, DocumentoComprobatório
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from django.conf import settings
import datetime
import logging
import io
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse


# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from django.utils.timezone import now
from collections import defaultdict
from django.db.models.functions import ExtractYear
from django.db.models import Sum
import json
from .models import ContaPagar
from .forms import ContaPagarForm

from django.shortcuts import get_object_or_404, redirect

'''
def contas_a_pagar(request):
    # Inicializa o formulário
    form = ContaPagarForm(request.POST or None)

    # Salva se for POST e válido
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('contas_a_pagar')

    # Busca todas as contas
    contas = ContaPagar.objects.all().order_by('vencimento')

    # Soma total dos valores
    soma = ContaPagar.objects.aggregate(total=Sum('valor'))['total']
    total_pendente = float(soma) if soma else 0.0

    # Teste de valor fixo para garantir que o template está funcionando
    valor_teste = 999.99

    context = {
        'form': form,
        'contas': contas,
        'total_pendente': total_pendente,
        'valor_teste': valor_teste
    }

    return render(request, 'contas_a_pagar.html', context)
'''


def contas_a_pagar(request):
    context = {
        'valor_teste': 999.99,
        'total_pendente': 1234.56
    }
    return render(request, 'contas_a_pagar.html', context)

def excluir_conta(request, conta_id):
    conta = get_object_or_404(ContaPagar, id=conta_id)
    conta.delete()
    return redirect('contas_a_pagar')

def marcar_como_paga(request, conta_id):
    conta = get_object_or_404(ContaPagar, id=conta_id)
    conta.status = 'pago'
    conta.save()
    return redirect('contas_a_pagar')

def contas_a_pagar(request):
    if request.method == 'POST':
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contas_a_pagar')
    else:
        form = ContaPagarForm()

    contas = ContaPagar.objects.order_by('vencimento')
    return render(request, 'contas_a_pagar.html', {'form': form, 'contas': contas})

def relatorio_financeiro(request):
    ano_selecionado = request.GET.get('ano')
    try:
        ano = int(ano_selecionado) if ano_selecionado else now().year
    except ValueError:
        ano = now().year

    transacoes = Transacao.objects.filter(data__year=ano)

    # Lista de anos disponíveis no banco
    anos_disponiveis = (
        Transacao.objects
        .annotate(ano=ExtractYear('data'))
        .values_list('ano', flat=True)
        .distinct()
        .order_by('-ano')
    )

    # Entradas e saídas por mês
    entradas_por_mes = [0] * 12
    saidas_por_mes = [0] * 12
    for transacao in transacoes:
        mes = transacao.data.month - 1
        if transacao.tipo == 'entrada':
            entradas_por_mes[mes] += float(transacao.valor)
        elif transacao.tipo == 'saida':
            saidas_por_mes[mes] += float(transacao.valor)

    # Gasto por categoria (convertendo Decimal para float)
    categorias_raw = (
        transacoes.filter(tipo='saida')
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )
    categorias_gasto = [
        {
            'categoria__nome': item['categoria__nome'],
            'total': float(item['total']) if item['total'] is not None else 0
        }
        for item in categorias_raw
    ]
    categoria_top = categorias_gasto[0] if categorias_gasto else None

    context = {
        'ano': ano,
        'anos_disponiveis': anos_disponiveis,
        'entradas_por_mes': entradas_por_mes,
        'saidas_por_mes': saidas_por_mes,
        'categorias_gasto': json.dumps(categorias_gasto),  # 👈 JSON seguro para o template
        'categoria_top': categoria_top,
    }
    return render(request, 'relatorio_financeiro.html', context)

from .forms import ImportarCSVForm
import csv
from io import TextIOWrapper, StringIO, BytesIO

@login_required
def importar_csv(request):
    if request.method == 'POST':
        form = ImportarCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, 'Nenhum arquivo foi enviado.')
                return render(request, 'importar_csv.html', {'form': form})

            file_content = csv_file.read()
            encodings = ['utf-8', 'windows-1252', 'latin-1']
            decoded_content = None

            for encoding in encodings:
                try:
                    decoded_content = TextIOWrapper(BytesIO(file_content), encoding=encoding).read()
                    break
                except UnicodeDecodeError:
                    continue

            if decoded_content is None:
                messages.error(request, 'Não foi possível decodificar o arquivo CSV. Verifique a codificação.')
                return render(request, 'importar_csv.html', {'form': form})

            csv_file = StringIO(decoded_content)
            reader = csv.DictReader(csv_file)

            linhas_processadas = 0
            erros = []

            for i, row in enumerate(reader, start=1):
                try:
                    tipo = row.get('tipo', '').strip().lower()
                    categoria_nome = row.get('categoria', '').strip()
                    pagador_nome = row.get('pagador', '').strip()
                    valor_str = row.get('valor', '0').replace(',', '.').strip()
                    valor = float(valor_str)
                    data_str = row.get('data', datetime.datetime.now().strftime('%d/%m/%Y')).strip()
                    data = datetime.datetime.strptime(data_str, '%d/%m/%Y').date()
                    descricao = row.get('descricao', '').strip()

                    if not tipo or not categoria_nome or not pagador_nome:
                        raise ValueError(f"Dados obrigatórios ausentes na linha {i}")

                    categoria, _ = Categoria.objects.get_or_create(nome=categoria_nome, tipo=tipo)
                    pagador, _ = Pagador.objects.get_or_create(nome=pagador_nome)

                    Transacao.objects.create(
                        tipo=tipo,
                        valor=valor,
                        data=data,
                        descricao=descricao,
                        categoria=categoria,
                        pagador=pagador
                    )

                    linhas_processadas += 1

                except Exception as e:
                    erros.append(f"Linha {i}: {str(e)}")

            if erros:
                messages.warning(request, f"{linhas_processadas} linhas importadas com sucesso. {len(erros)} erros encontrados.")
                for erro in erros:
                    messages.error(request, erro)
            else:
                messages.success(request, f"Todos os dados ({linhas_processadas}) foram importados com sucesso!")

            return redirect('dashboard')
    else:
        form = ImportarCSVForm()

    return render(request, 'importar_csv.html', {'form': form})




from django.contrib.auth import logout
from django.shortcuts import redirect

def sair(request):
    logout(request)
    return redirect('login') 

@login_required
def dashboard(request):
    form = FiltroMensalForm(request.GET or None)
    categorias = Categoria.objects.all().values('id', 'nome')

    # Inicializa variáveis
    transacoes = Transacao.objects.none()
    entradas_ultimo_mes = '--'
    saidas_ultimo_mes = '--'
    saldo_ultimo_mes = '--'
    ultimas_entradas = []
    ultimas_saidas = []
    categoria_saidas = {}

    if form.is_valid():
        mes = form.cleaned_data.get('mes')
        ano = form.cleaned_data.get('ano')
        tipo = form.cleaned_data.get('tipo')
        categoria_ids = form.cleaned_data.get('categoria') or []

        logger.debug(f"Filtros recebidos: mes={mes}, ano={ano}, tipo={tipo}, categorias={categoria_ids}")

        # Só aplica filtros se mês e ano forem definidos
        if mes and ano:
            transacoes = Transacao.objects.filter(data__month=mes, data__year=ano)

            tipo = form.cleaned_data.get('tipo')
            if tipo:
                transacoes = transacoes.filter(tipo=tipo)

            categoria_ids = [int(cid) for cid in form.cleaned_data.get('categoria', []) if cid.strip()]
            if categoria_ids:
                transacoes = transacoes.filter(categoria_id__in=categoria_ids)
            # Totais
            entradas_ultimo_mes = transacoes.filter(tipo='entrada').aggregate(total=Sum('valor'))['total'] or 0
            saidas_ultimo_mes = transacoes.filter(tipo='saida').aggregate(total=Sum('valor'))['total'] or 0
            saldo_ultimo_mes = entradas_ultimo_mes - saidas_ultimo_mes

            # Saídas por categoria
            for cid in categoria_ids:
                saidas_categoria = transacoes.filter(tipo='saida', categoria_id=int(cid)).aggregate(total=Sum('valor'))['total'] or 0
                if saidas_categoria > 0:
                    categoria_saidas[int(cid)] = saidas_categoria

            # Últimas transações
            if tipo == 'entrada':
                ultimas_entradas = transacoes.filter(tipo='entrada')
                ultimas_saidas = []
            elif tipo == 'saida':
                ultimas_saidas = transacoes.filter(tipo='saida')
                ultimas_entradas = []
            else:
                ultimas_entradas = transacoes.filter(tipo='entrada')
                ultimas_saidas = transacoes.filter(tipo='saida')

    context = {
        'form': form,
        'transacoes': transacoes,
        'entradas_ultimo_mes': entradas_ultimo_mes,
        'saidas_ultimo_mes': saidas_ultimo_mes,
        'saldo_ultimo_mes': saldo_ultimo_mes,
        'ultimas_entradas': ultimas_entradas,
        'ultimas_saidas': ultimas_saidas,
        'categorias': categorias,
        'categoria_saidas': categoria_saidas,
        'ultimo_mes_nome': 'Setembro',
    }

    return render(request, 'dashboard.html', context)

@login_required
def relatorio_mensal(request, ano, mes):
    transacoes = Transacao.objects.filter(data__year=ano, data__month=mes)
    entradas = transacoes.filter(tipo='entrada').aggregate(total=Sum('valor'))['total'] or 0
    saidas = transacoes.filter(tipo='saida').aggregate(total=Sum('valor'))['total'] or 0
    saldo = entradas - saidas
    
    context = {
        'transacoes': transacoes,
        'entradas': entradas,
        'saidas': saidas,
        'saldo': saldo,
        'mes': f"{mes}/{ano}",
    }
    
    return render(request, 'relatorio.html', context)

@login_required
def adicionar_transacao(request):
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        arquivos = request.FILES.getlist('documentos')  # Captura múltiplos arquivos enviados

        if form.is_valid():
            transacao = form.save()

            # Salva cada documento vinculado à transação
            for arquivo in arquivos:
                DocumentoComprobatório.objects.create(transacao=transacao, arquivo=arquivo)

            return redirect('dashboard')
    else:
        form = TransacaoForm()
    messages.success(request, 'Transação adicionada com sucesso!')
    return render(request, 'adicionar_transacao.html', {'form': form})

@login_required
def configurar_categorias(request):
    categorias = Categoria.objects.all()
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('configurar_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'configurar_categorias.html', {'form': form, 'categorias': categorias})

@login_required
def adicionar_pagador(request):
    if request.method == 'POST':
        form = PagadorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor/Pagador adicionado com sucesso!')
            return redirect('dashboard')
    else:
        form = PagadorForm()
    return render(request, 'adicionar_pagador.html', {'form': form})

@login_required
def get_categorias(request):
    tipo = request.GET.get('tipo')
    categorias = Categoria.objects.filter(tipo=tipo).values('id', 'nome')
    return JsonResponse(list(categorias), safe=False)

@login_required
def exportar_pdf(request):
    logger.debug("Entrando na view exportar_pdf")
    logger.debug(f"Requisição recebida: {request.method} {request.get_full_path()}")

    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    logger.debug(f"Parâmetros recebidos - mes: {mes}, ano: {ano}")

    transacoes = Transacao.objects.all().order_by('-data')
    if mes and ano:
        transacoes = transacoes.filter(data__month=mes, data__year=ano)
    logger.debug(f"Número de transações filtradas: {transacoes.count()}")

    entradas_total = transacoes.filter(tipo='entrada').aggregate(total=Sum('valor'))['total'] or 0
    saidas_total = transacoes.filter(tipo='saida').aggregate(total=Sum('valor'))['total'] or 0
    saldo_total = entradas_total - saidas_total

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    custom_style = ParagraphStyle(
        'Custom',
        parent=normal_style,
        fontSize=12,
        leading=16,
        spaceAfter=12,
        wordWrap='CJK'
    )

    emitente = Emitente.get_solo()
    if emitente.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(emitente.logo))
        if os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=250, height=100)
                elements.append(logo_img)
                logger.debug("Logo do emitente adicionada ao cabeçalho")
            except Exception as e:
                logger.error(f"Erro ao carregar a logo do emitente: {str(e)}")
        else:
            logger.debug("Caminho da logo do emitente inválido")
    elements.append(Spacer(1, 12))

    periodo = f"{mes}/{ano}" if mes and ano else "Todos"
    title = Paragraph(f"Relatório de Finanças - {periodo}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    widget_data = [[
        Paragraph("ENTRADA", custom_style),
        Paragraph(f"R${entradas_total:.2f}", custom_style),
        "",
        Paragraph("SAÍDA", custom_style),
        Paragraph(f"R${saidas_total:.2f}", custom_style),
        "",
        Paragraph("SALDO", custom_style),
        Paragraph(f"R${saldo_total:.2f}", custom_style)
    ]]
    widget_table = Table(widget_data, colWidths=[100, 100, 10, 100, 100, 10, 80, 80], style=[
        ('BACKGROUND', (0, 0), (1, 0), '#90EE90'),
        ('BACKGROUND', (3, 0), (4, 0), '#FF6347'),
        ('BACKGROUND', (6, 0), (7, 0), '#4682B4'),
        ('BOX', (0, 0), (1, 0), 2, '#ffffff'),
        ('BOX', (3, 0), (4, 0), 2, '#ffffff'),
        ('BOX', (6, 0), (7, 0), 2, '#ffffff'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
    ])
    elements.append(widget_table)
    elements.append(Spacer(1, 24))

    data_geracao = datetime.datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"Gerado automaticamente com o sistema de finanças Guardião em {data_geracao}", custom_style))
    elements.append(Spacer(1, 24))

    # Entradas
    elements.append(Paragraph("ENTRADAS", styles['Heading2']))
    entradas = transacoes.filter(tipo='entrada')
    if entradas.exists():
        table_data = [['Data', 'Valor (R$)', 'Descrição', 'Fornecedor']]
        for transacao in entradas:
            fornecedor = transacao.pagador.nome if transacao.pagador else 'Nenhum'
            table_data.append([
                Paragraph(transacao.data.strftime('%d/%m/%Y'), custom_style),
                Paragraph(f"{transacao.valor:.2f}", custom_style),
                Paragraph(transacao.descricao or 'Sem descrição', custom_style),
                Paragraph(fornecedor, custom_style)
            ])
        table = Table(table_data, colWidths=[80, 80, 150, 100], style=[
            ('BACKGROUND', (0, 0), (-1, 0), '#90EE90'),
            ('TEXTCOLOR', (0, 0), (-1, 0), '#000000'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), '#FFFFFF'),
            ('TEXTCOLOR', (0, 1), (-1, -1), '#000000'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, '#DCDCDC'),
            ('WORDWRAP', (0, 0), (-1, -1), 1)
        ])
        elements.append(table)
    else:
        elements.append(Paragraph("Nenhuma entrada registrada.", custom_style))
    elements.append(Spacer(1, 12))

    # Saídas
    elements.append(Paragraph("SAÍDAS", styles['Heading2']))
    saidas = transacoes.filter(tipo='saida')
    if saidas.exists():
        table_data = [['', 'Data', 'Valor (R$)', 'Descrição', 'Fornecedor']]
        for transacao in saidas:
            fornecedor = transacao.pagador.nome if transacao.pagador else 'Nenhum'
            imagem = ''
            if transacao.pagador and transacao.pagador.logo:
                logo_path = os.path.join(settings.MEDIA_ROOT, str(transacao.pagador.logo))
                if os.path.exists(logo_path):
                    try:
                        imagem = Image(logo_path, width=30, height=30)
                        imagem.hAlign = 'LEFT'
                    except Exception as e:
                        logger.error(f"Erro ao carregar a imagem do pagador {transacao.pagador.nome}: {str(e)}")
            table_data.append([
                imagem if imagem else Paragraph('', custom_style),
                Paragraph(transacao.data.strftime('%d/%m/%Y'), custom_style),
                Paragraph(f"{transacao.valor:.2f}", custom_style),
                Paragraph(transacao.descricao or 'Sem descrição', custom_style),
                Paragraph(fornecedor, custom_style)
            ])
        table = Table(table_data, colWidths=[40, 80, 80, 150, 100], style=[
            ('BACKGROUND', (1, 0), (-1, 0), '#FF6347'),
            ('TEXTCOLOR', (1, 0), (-1, 0), '#000000'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (1, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), '#FFFFFF'),
            ('TEXTCOLOR', (0, 1), (-1, -1), '#000000'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, "#DCDCDC"),
            ('WORDWRAP', (0, 0), (-1, -1), 1)
        ])
        elements.append(table)
    else:
        elements.append(Paragraph("Nenhuma saída registrada.", custom_style))
    try:
        doc.build(elements)
        buffer.seek(0)
        logger.debug("PDF construído com sucesso")
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{mes or "todos"}_{ano or "todos"}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        logger.debug("Resposta HTTP preparada para download")
        return response
    except Exception as e:
        logger.error(f"Erro ao construir o PDF: {str(e)}")
        return HttpResponse(f"Erro ao gerar PDF: {str(e)}", status=500)


def transacao_json(request, transacao_id):
    transacao = Transacao.objects.get(id=transacao_id)
    documentos = [
        {
            'url': doc.arquivo.url,
            'data_envio': doc.data_envio.strftime('%d/%m/%Y')
        }
        for doc in transacao.documentos.all()
    ]
    data = {
        'tipo': transacao.tipo,
        'valor': float(transacao.valor),
        'data': transacao.data.strftime('%d/%m/%Y'),
        'descricao': transacao.descricao,
        'categoria': transacao.categoria.nome if transacao.categoria else '',
        'pagador': transacao.pagador.nome if transacao.pagador else '',
        'documentos': documentos
    }
    return JsonResponse(data)

def adicionar_comprovante(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)
    if request.method == 'POST':
        for arquivo in request.FILES.getlist('documentos'):
            DocumentoComprobatório.objects.create(transacao=transacao, arquivo=arquivo)
        messages.success(request, 'Comprovantes adicionados com sucesso!')
    query_string = request.META.get('HTTP_REFERER', '')
    return HttpResponseRedirect(query_string or reverse('dashboard'))

def editar_transacao(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)

    if request.method == 'POST':
        form = TransacaoForm(request.POST, instance=transacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação editada com sucesso!')
            referer = request.META.get('HTTP_REFERER', '')
            return HttpResponseRedirect(referer or reverse('dashboard'))
    else:
        form = TransacaoForm(instance=transacao)
        form.fields.pop('data')  # Remove o campo da edição

    return render(request, 'editar_transacao.html', {
        'form': form,
        'transacao': transacao
    })

def anular_transacao(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)
    transacao.delete()
    messages.success(request, 'Transação anulada com sucesso!')
    query_string = request.META.get('HTTP_REFERER', '')
    return HttpResponseRedirect(query_string or reverse('dashboard'))