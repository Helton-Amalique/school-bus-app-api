"""
financeiro/pdf_utils.py
=======================
Geração de PDFs para recibos de pagamento de mensalidades.

Usa reportlab (ReportLab Toolkit) para gerar um PDF profissional
com o logótipo, dados do aluno, detalhes do pagamento e código do recibo.

Dependência: reportlab
  pip install reportlab

Função principal:
  gerar_pdf_recibo(mensalidade, recibo) -> bytes
    Devolve os bytes do PDF gerado, prontos para guardar num FileField.

Uso em models.py:
  from financeiro.pdf_utils import gerar_pdf_recibo
  from django.core.files.base import ContentFile

  pdf_bytes = gerar_pdf_recibo(mensalidade, recibo)
  recibo.arquivo_pdf.save(nome, ContentFile(pdf_bytes), save=False)
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta de cores ────────────────────────────────────────────────────────────
COR_PRIMARIA = colors.HexColor('#1a5276')   # azul escuro
COR_SECUNDARIA = colors.HexColor('#2e86c1')   # azul médio
COR_SUCESSO = colors.HexColor('#1e8449')   # verde
COR_FUNDO_LINHA = colors.HexColor('#eaf4fb')   # azul muito claro
COR_CINZA = colors.HexColor('#717d7e')   # cinza texto secundário
COR_BORDA = colors.HexColor('#aed6f1')   # borda tabela


def gerar_pdf_recibo(mensalidade, recibo) -> bytes:
    """
    Gera o PDF de um recibo de pagamento.

    Parâmetros:
        mensalidade — instância de financeiro.Mensalidade (estado=PAGO)
        recibo      — instância de financeiro.Recibo

    Devolve:
        bytes do PDF gerado
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Recibo {recibo.codigo_recibo}",
        author="Sistema de Transporte Escolar",
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Estilos customizados ───────────────────────────────────────────────────

    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Normal'],
        fontSize=20,
        textColor=COR_PRIMARIA,
        fontName='Helvetica-Bold',
        spaceAfter=4,
    )
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COR_SECUNDARIA,
        fontName='Helvetica',
        spaceAfter=2,
    )
    estilo_label = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COR_CINZA,
        fontName='Helvetica',
        spaceAfter=1,
    )
    estilo_valor = ParagraphStyle(
        'Valor',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        spaceAfter=6,
    )
    estilo_total = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=16,
        textColor=COR_SUCESSO,
        fontName='Helvetica-Bold',
        alignment=1,  # centrado
    )
    estilo_codigo = ParagraphStyle(
        'Codigo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COR_CINZA,
        fontName='Helvetica',
        alignment=1,
    )
    estilo_rodape = ParagraphStyle(
        'Rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COR_CINZA,
        fontName='Helvetica',
        alignment=1,
    )

    # ── Cabeçalho ─────────────────────────────────────────────────────────────

    # Tabela de cabeçalho: nome da escola à esquerda, info do recibo à direita
    cabecalho_data = [[
        Paragraph('Sistema de Transporte Escolar', estilo_titulo),
        Paragraph(
            f'RECIBO<br/>'
            f'<font size="9" color="#717d7e">{recibo.codigo_recibo}</font>',
            ParagraphStyle('ReciboCab', parent=estilo_titulo,
                           alignment=2, fontSize=18)
        ),
    ]]
    tabela_cabecalho = Table(cabecalho_data, colWidths=['60%', '40%'])
    tabela_cabecalho.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tabela_cabecalho)

    story.append(HRFlowable(
        width='100%', thickness=2,
        color=COR_PRIMARIA, spaceAfter=12
    ))

    # ── Badge PAGO ────────────────────────────────────────────────────────────

    story.append(Paragraph(
        '<font color="#1e8449"><b>✓ PAGAMENTO CONFIRMADO</b></font>',
        ParagraphStyle('Badge', parent=styles['Normal'],
                       fontSize=12, alignment=1, spaceAfter=16,
                       backColor=colors.HexColor('#eafaf1'),
                       borderColor=COR_SUCESSO, borderWidth=1,
                       borderPadding=6)
    ))

    # ── Dados do aluno e pagamento ─────────────────────────────────────────────

    aluno = mensalidade.aluno
    encarregado = aluno.encarregado

    dados = [
        # Linha 1
        [
            [Paragraph('ALUNO', estilo_label),
             Paragraph(aluno.user.nome, estilo_valor)],
            [Paragraph('ENCARREGADO', estilo_label),
             Paragraph(encarregado.user.nome if encarregado else '—', estilo_valor)],
        ],
        # Linha 2
        [
            [Paragraph('MÊS DE REFERÊNCIA', estilo_label),
             Paragraph(mensalidade.mes_referente.strftime('%B de %Y').title(), estilo_valor)],
            [Paragraph('DATA DE PAGAMENTO', estilo_label),
             Paragraph(
                 mensalidade.data_ultimo_pagamento.strftime('%d/%m/%Y')
                 if mensalidade.data_ultimo_pagamento else date.today().strftime('%d/%m/%Y'),
                 estilo_valor
             )],
        ],
        # Linha 3
        [
            [Paragraph('ESCOLA DESTINO', estilo_label),
             Paragraph(aluno.escola_dest or '—', estilo_valor)],
            [Paragraph('CLASSE', estilo_label),
             Paragraph(str(aluno.classe) if aluno.classe else '—', estilo_valor)],
        ],
    ]

    for linha in dados:
        tabela_linha = Table(
            [[_celula_para_paragrafo(linha[0]), _celula_para_paragrafo(linha[1])]],
            colWidths=['50%', '50%']
        )
        tabela_linha.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COR_FUNDO_LINHA),
            ('ROUNDEDCORNERS', [4]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(tabela_linha)
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))

    # ── Tabela de valores ─────────────────────────────────────────────────────

    linhas_valores = [
        ['Descrição', 'Valor'],
        ['Mensalidade base', f'{mensalidade.valor_base:.2f} MT'],
    ]

    if mensalidade.multa_atraso > 0:
        linhas_valores.append(['Multa de atraso', f'{mensalidade.multa_atraso:.2f} MT'])

    if mensalidade.desconto > 0:
        linhas_valores.append(['Desconto', f'- {mensalidade.desconto:.2f} MT'])

    linhas_valores.append(['TOTAL PAGO', f'{mensalidade.valor_pago_acumulado:.2f} MT'])

    tabela_valores = Table(linhas_valores, colWidths=['70%', '30%'])
    tabela_valores.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        # Linhas de detalhe
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, COR_FUNDO_LINHA]),
        # Linha total
        ('BACKGROUND', (0, -1), (-1, -1), COR_SUCESSO),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        # Padding geral
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, COR_BORDA),
        ('BOX', (0, 0), (-1, -1), 1, COR_PRIMARIA),
    ]))
    story.append(tabela_valores)
    story.append(Spacer(1, 20))

    # ── Rodapé ────────────────────────────────────────────────────────────────

    story.append(HRFlowable(
        width='100%', thickness=1,
        color=COR_BORDA, spaceAfter=8
    ))
    story.append(Paragraph(
        f'Código do recibo: <b>{recibo.codigo_recibo}</b> &nbsp;|&nbsp; '
        f'Emitido em: <b>{recibo.data_emissao.strftime("%d/%m/%Y %H:%M") if recibo.data_emissao else date.today().strftime("%d/%m/%Y")}</b>',
        estilo_codigo
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Este documento é gerado automaticamente pelo Sistema de Transporte Escolar. '
        'Guarde-o como comprovativo de pagamento.',
        estilo_rodape
    ))

    # ── Build ─────────────────────────────────────────────────────────────────

    doc.build(story)
    return buffer.getvalue()


def _celula_para_paragrafo(celula: list) -> 'Table':
    """Converte uma lista de [label, valor] num bloco vertical."""
    return Table(
        [[p] for p in celula],
        colWidths=['100%']
    )
