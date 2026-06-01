"""
Gerador de Relatórios PDF — Dashboards de Corte e Produção
==========================================================
Usa ReportLab (Platypus) para layout e Matplotlib para gráficos.
Compatível com impressão e envio em fechamento de mês.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether, PageBreak,
)
from reportlab.pdfbase import pdfmetrics

logger = logging.getLogger(__name__)

# ─── Paleta de cores ──────────────────────────────────────────────────────────
C_NAVY      = colors.HexColor('#0D2B4E')
C_TEAL      = colors.HexColor('#2AA89A')
C_TEAL_LT   = colors.HexColor('#E8F7F6')
C_AMBER     = colors.HexColor('#D4860A')
C_AMBER_LT  = colors.HexColor('#FEF3DF')
C_GREEN     = colors.HexColor('#1E8449')
C_GREEN_LT  = colors.HexColor('#E9F7EF')
C_RED       = colors.HexColor('#CB4335')
C_RED_LT    = colors.HexColor('#FDECEA')
C_GRAY_BG   = colors.HexColor('#F4F6F8')
C_GRAY_LINE = colors.HexColor('#D5D8DC')
C_GRAY_TEXT = colors.HexColor('#5D6D7E')
C_WHITE     = colors.white
C_BLACK     = colors.HexColor('#1C2833')

# Cores matplotlib (tema claro, bom para impressão)
MP_BG       = '#F8F9FA'
MP_GRID     = '#DEE2E6'
MP_BAR_OK   = '#2AA89A'
MP_BAR_NOK  = '#CB4335'
MP_META     = '#D4860A'
MP_TREND    = '#1E8449'
MP_TEXT     = '#1C2833'

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


# ─── Estilos de parágrafo ─────────────────────────────────────────────────────
def _estilos():
    base = getSampleStyleSheet()
    estilos = {}

    estilos['titulo_capa'] = ParagraphStyle(
        'titulo_capa', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=28,
        textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=6,
    )
    estilos['subtitulo_capa'] = ParagraphStyle(
        'subtitulo_capa', parent=base['Normal'],
        fontName='Helvetica', fontSize=14,
        textColor=colors.HexColor('#AED6F1'), alignment=TA_CENTER, spaceAfter=4,
    )
    estilos['periodo_capa'] = ParagraphStyle(
        'periodo_capa', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=16,
        textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=4,
    )
    estilos['emissao_capa'] = ParagraphStyle(
        'emissao_capa', parent=base['Normal'],
        fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#85C1E9'), alignment=TA_CENTER,
    )
    estilos['titulo_secao'] = ParagraphStyle(
        'titulo_secao', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=13,
        textColor=C_NAVY, spaceBefore=14, spaceAfter=6, borderPad=0,
    )
    estilos['subtitulo_secao'] = ParagraphStyle(
        'subtitulo_secao', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=C_TEAL, spaceBefore=8, spaceAfter=4,
    )
    estilos['corpo'] = ParagraphStyle(
        'corpo', parent=base['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=C_BLACK, leading=13, spaceAfter=4,
    )
    estilos['nota'] = ParagraphStyle(
        'nota', parent=base['Normal'],
        fontName='Helvetica-Oblique', fontSize=8,
        textColor=C_GRAY_TEXT, spaceAfter=4,
    )
    estilos['tabela_header'] = ParagraphStyle(
        'tabela_header', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8,
        textColor=C_WHITE, alignment=TA_CENTER,
    )
    estilos['tabela_cell'] = ParagraphStyle(
        'tabela_cell', parent=base['Normal'],
        fontName='Helvetica', fontSize=8,
        textColor=C_BLACK, alignment=TA_CENTER,
    )
    estilos['tabela_cell_left'] = ParagraphStyle(
        'tabela_cell_left', parent=base['Normal'],
        fontName='Helvetica', fontSize=8,
        textColor=C_BLACK, alignment=TA_LEFT,
    )
    estilos['kpi_valor'] = ParagraphStyle(
        'kpi_valor', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=18,
        textColor=C_NAVY, alignment=TA_CENTER,
    )
    estilos['kpi_label'] = ParagraphStyle(
        'kpi_label', parent=base['Normal'],
        fontName='Helvetica', fontSize=8,
        textColor=C_GRAY_TEXT, alignment=TA_CENTER,
    )
    return estilos


# ─── Helpers de formatação ────────────────────────────────────────────────────
def _fmt(v, dec=0):
    """Formata número no padrão brasileiro (ponto como milhar, vírgula decimal)."""
    try:
        v = float(v)
        if dec == 0:
            return f"{int(v):,}".replace(',', '.')
        return f"{v:,.{dec}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return str(v)


def _pct_cor(pct: float):
    """Retorna cor para % de meta."""
    if pct >= 100:
        return C_GREEN
    if pct >= 80:
        return C_AMBER
    return C_RED


def _pct_bg(pct: float):
    """Retorna cor de fundo para % de meta."""
    if pct >= 100:
        return C_GREEN_LT
    if pct >= 80:
        return C_AMBER_LT
    return C_RED_LT


# ─── Gerador de gráficos matplotlib → BytesIO ────────────────────────────────

def _chart_producao_diaria(
    prod_diaria: pd.DataFrame,
    meta_total: float,
    titulo: str = "Produção Diária",
    largura: float = 14.0,
    altura: float = 4.5,
) -> io.BytesIO:
    """Gráfico de barras diário com linha de meta e tendência."""
    fig, ax = plt.subplots(figsize=(largura, altura))
    fig.patch.set_facecolor(MP_BG)
    ax.set_facecolor(MP_BG)

    datas = prod_diaria['DATA'].tolist()
    qtds = prod_diaria['QUANTIDADE'].tolist()
    n = len(datas)
    if n == 0:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=130); plt.close(fig); buf.seek(0)
        return buf

    cores_bar = [MP_BAR_OK if q >= meta_total else MP_BAR_NOK for q in qtds]
    bars = ax.bar(range(n), qtds, color=cores_bar, alpha=0.85, width=0.65, zorder=3)

    if meta_total > 0:
        ax.axhline(meta_total, color=MP_META, linestyle='--', linewidth=2.2, zorder=4,
                   label=f'Meta: {_fmt(meta_total)}')

    if n >= 5:
        mm5 = pd.Series(qtds).rolling(5, min_periods=1).mean().tolist()
        ax.plot(range(n), mm5, color=MP_TREND, linewidth=2.5, zorder=5,
                label='Tendência (5d)', marker='o', markersize=3.5)

    max_q = max(qtds) if qtds else 1
    for i, (bar, q) in enumerate(zip(bars, qtds)):
        if q > 0 and n <= 40:
            ax.text(bar.get_x() + bar.get_width() / 2., q + max_q * 0.012,
                    _fmt(q), ha='center', va='bottom', fontsize=6.5,
                    color=MP_TEXT, fontweight='bold')

    ax.set_xticks(range(n))
    fmt_data = []
    for d in datas:
        try:
            fmt_data.append(pd.Timestamp(d).strftime('%d/%m'))
        except Exception:
            fmt_data.append(str(d))
    ax.set_xticklabels(fmt_data, rotation=45, ha='right', fontsize=7.5, color=MP_TEXT)
    ax.set_title(titulo, fontsize=12, fontweight='bold', color=MP_TEXT, pad=10)
    ax.set_ylabel('Peças', fontsize=9, color=MP_TEXT)
    ax.tick_params(colors=MP_TEXT)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt(x)))
    ax.grid(axis='y', color=MP_GRID, linewidth=0.7, alpha=0.8, zorder=1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(MP_GRID)
    ax.spines['bottom'].set_color(MP_GRID)
    if meta_total > 0 or n >= 5:
        leg = ax.legend(fontsize=8, framealpha=0.9, edgecolor=MP_GRID)
        for t in leg.get_texts(): t.set_color(MP_TEXT)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_pizza_estacao(
    dist: pd.DataFrame,
    col_nome: str,
    col_valor: str,
    titulo: str = "Distribuição por Estação",
) -> io.BytesIO:
    """Gráfico de pizza de distribuição."""
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor(MP_BG)
    paleta = ['#2AA89A', '#D4860A', '#1E8449', '#CB4335', '#5D6D7E', '#AED6F1']
    labels = dist[col_nome].tolist()
    values = dist[col_valor].tolist()
    wedges, texts, autotexts = ax.pie(
        values, labels=None,
        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
        colors=paleta[:len(labels)], startangle=90,
        wedgeprops=dict(edgecolor='white', linewidth=2),
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8); at.set_color('white'); at.set_fontweight('bold')

    # Legenda lateral
    legend_labels = [f'{l}: {_fmt(v)} pç' for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc='center left',
              bbox_to_anchor=(1.02, 0.5), fontsize=8,
              framealpha=0.9, edgecolor=MP_GRID)
    ax.set_title(titulo, fontsize=11, fontweight='bold', color=MP_TEXT, pad=10)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_barras_h(
    df: pd.DataFrame,
    col_nome: str,
    col_valor: str,
    titulo: str,
    top_n: int = 15,
    cor: str = MP_BAR_OK,
) -> io.BytesIO:
    """Gráfico de barras horizontais (top-N)."""
    df_top = df.nlargest(top_n, col_valor)[[col_nome, col_valor]].sort_values(col_valor)
    n = len(df_top)
    fig, ax = plt.subplots(figsize=(8, max(3.5, n * 0.38)))
    fig.patch.set_facecolor(MP_BG)
    ax.set_facecolor(MP_BG)

    bars = ax.barh(range(n), df_top[col_valor], color=cor, alpha=0.85, height=0.65)
    ax.set_yticks(range(n))
    ax.set_yticklabels(df_top[col_nome].tolist(), fontsize=7.5, color=MP_TEXT)

    max_v = df_top[col_valor].max() if not df_top.empty else 1
    for bar, v in zip(bars, df_top[col_valor]):
        ax.text(v + max_v * 0.01, bar.get_y() + bar.get_height() / 2.,
                _fmt(v), va='center', fontsize=7, color=MP_TEXT, fontweight='bold')

    ax.set_title(titulo, fontsize=11, fontweight='bold', color=MP_TEXT, pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt(x)))
    ax.tick_params(colors=MP_TEXT, labelsize=7.5)
    ax.grid(axis='x', color=MP_GRID, linewidth=0.7, alpha=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(MP_GRID)
    ax.spines['bottom'].set_color(MP_GRID)
    ax.set_xlim(right=max_v * 1.14)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_lencol_prestador_valor(df_prest: pd.DataFrame) -> io.BytesIO:
    """Gráfico duplo: peças + valor por prestador."""
    df_s = df_prest.sort_values('Peças', ascending=True)
    n = len(df_s)
    fig, axes = plt.subplots(1, 2, figsize=(12, max(3.5, n * 0.45)))
    fig.patch.set_facecolor(MP_BG)
    paleta = ['#2AA89A', '#D4860A', '#1E8449', '#CB4335', '#5D6D7E',
              '#AED6F1', '#7FB3D3', '#F0B27A', '#82E0AA', '#F1948A']

    for ax, (col, titulo, cor_idx) in zip(axes, [
        ('Peças', 'Peças Cortadas', 0), ('Valor', 'Valor (R$)', 1)
    ]):
        ax.set_facecolor(MP_BG)
        cores_bar = [paleta[i % len(paleta)] for i in range(n)]
        ax.barh(range(n), df_s[col], color=cores_bar, alpha=0.85, height=0.65)
        ax.set_yticks(range(n))
        ax.set_yticklabels(df_s['PRESTADOR'].tolist(), fontsize=7.5, color=MP_TEXT)
        max_v = df_s[col].max() if not df_s.empty else 1
        for i, v in enumerate(df_s[col]):
            label = _fmt(v) if col == 'Peças' else f"R$ {_fmt(v, 2)}"
            ax.text(v + max_v * 0.01, i, label, va='center',
                    fontsize=6.5, color=MP_TEXT, fontweight='bold')
        ax.set_title(titulo, fontsize=10, fontweight='bold', color=MP_TEXT)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt(x)))
        ax.tick_params(colors=MP_TEXT, labelsize=7)
        ax.grid(axis='x', color=MP_GRID, linewidth=0.7, alpha=0.8)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(MP_GRID); ax.spines['bottom'].set_color(MP_GRID)
        ax.set_xlim(right=max_v * 1.16)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


# ─── Componentes de layout (flowables) ───────────────────────────────────────

def _linha_divisoria(largura=None, cor=C_TEAL, espessura=1.5, espaco_acima=4, espaco_abaixo=8):
    return HRFlowable(
        width=largura or '100%', thickness=espessura,
        color=cor, spaceAfter=espaco_abaixo, spaceBefore=espaco_acima,
    )


def _bloco_kpis(kpis: list[dict], estilos: dict, colunas: int = 4) -> Table:
    """
    kpis = [{'label': 'Total Peças', 'valor': '85.230', 'cor': C_TEAL_LT}, ...]
    """
    largura_col = (PAGE_W - 2 * MARGIN) / colunas
    dados = []
    linha_vals = []
    linha_labels = []
    for i, kpi in enumerate(kpis):
        cor_bg = kpi.get('cor', C_TEAL_LT)
        linha_vals.append(Paragraph(kpi['valor'], estilos['kpi_valor']))
        linha_labels.append(Paragraph(kpi['label'], estilos['kpi_label']))
        if (i + 1) % colunas == 0:
            dados.append(linha_vals)
            dados.append(linha_labels)
            linha_vals, linha_labels = [], []

    # Preencher última linha incompleta
    while len(linha_vals) > 0 and len(linha_vals) < colunas:
        linha_vals.append(Paragraph('', estilos['kpi_valor']))
        linha_labels.append(Paragraph('', estilos['kpi_label']))
    if linha_vals:
        dados.append(linha_vals)
        dados.append(linha_labels)

    col_widths = [largura_col] * colunas
    t = Table(dados, colWidths=col_widths, rowHeights=None)

    # Estilos da tabela
    ts_cmds = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, C_GRAY_LINE),
    ]
    # Colorir backgrounds por colunas alternadas
    bg_cols = [C_TEAL_LT, C_AMBER_LT, C_GREEN_LT, C_GRAY_BG]
    n_linhas = len(dados)
    for col_i in range(colunas):
        for row_i in range(0, n_linhas, 2):
            cor_bg = bg_cols[col_i % len(bg_cols)]
            for offset in range(2):
                if row_i + offset < n_linhas:
                    ts_cmds.append(('BACKGROUND', (col_i, row_i + offset),
                                    (col_i, row_i + offset), cor_bg))

    t.setStyle(TableStyle(ts_cmds))
    return t


def _tabela_generica(
    cabecalho: list[str],
    linhas: list[list],
    estilos: dict,
    col_widths: Optional[list] = None,
    cor_header: colors.Color = None,
) -> Table:
    """Tabela com cabeçalho colorido e linhas alternadas."""
    cor_header = cor_header or C_NAVY

    # Monta dados
    dados = [[Paragraph(c, estilos['tabela_header']) for c in cabecalho]]
    for i, linha in enumerate(linhas):
        row = []
        for cell in linha:
            row.append(Paragraph(str(cell), estilos['tabela_cell']))
        dados.append(row)

    n_cols = len(cabecalho)
    if col_widths is None:
        larg_total = PAGE_W - 2 * MARGIN
        col_widths = [larg_total / n_cols] * n_cols

    t = Table(dados, colWidths=col_widths, repeatRows=1)
    ts_cmds = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), cor_header),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        # Corpo
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, C_GRAY_BG]),
        ('GRID', (0, 0), (-1, -1), 0.4, C_GRAY_LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    t.setStyle(TableStyle(ts_cmds))
    return t


def _imagem_de_buf(buf: io.BytesIO, largura_cm: float = 15.0) -> Image:
    """Converte BytesIO de imagem em Flowable Image do ReportLab."""
    from PIL import Image as PILImage
    buf.seek(0)
    pil = PILImage.open(buf)
    w_px, h_px = pil.size
    largura = largura_cm * cm
    altura = largura * h_px / w_px
    return Image(buf, width=largura, height=altura)


# ─── Template de página (cabeçalho + rodapé) ─────────────────────────────────

def _make_page_template(doc, titulo_relatorio: str, periodo: str):
    """Cria PageTemplate com header/footer automáticos."""

    def _header_footer(canvas, doc):
        canvas.saveState()
        w = PAGE_W

        # Faixa de cabeçalho
        canvas.setFillColor(C_NAVY)
        canvas.rect(0, PAGE_H - 1.4 * cm, w, 1.4 * cm, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(MARGIN, PAGE_H - 0.95 * cm, titulo_relatorio)
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(w - MARGIN, PAGE_H - 0.95 * cm, periodo)

        # Faixa de rodapé
        canvas.setFillColor(C_GRAY_BG)
        canvas.rect(0, 0, w, 1.1 * cm, fill=1, stroke=0)
        canvas.setFillColor(C_GRAY_TEXT)
        canvas.setFont('Helvetica', 7.5)
        canvas.drawString(MARGIN, 0.4 * cm,
                          f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Sistema de Gestão Industrial")
        canvas.setFont('Helvetica-Bold', 8)
        canvas.drawRightString(w - MARGIN, 0.4 * cm, f"Pág. {doc.page}")

        canvas.restoreState()

    frame = Frame(
        MARGIN, 1.4 * cm,
        PAGE_W - 2 * MARGIN, PAGE_H - 2.8 * cm,
        id='normal',
    )
    return PageTemplate(id='main', frames=[frame], onPage=_header_footer)


def _make_cover(titulo: str, subtitulo: str, periodo: str, gerado_em: str, filtros: str = '') -> list:
    """Gera flowables da capa (página 1)."""

    class _CapaCanvas:
        pass

    # Usamos uma tabela de uma célula para simular a capa
    estilos = _estilos()
    linhas_capa = [
        Spacer(1, 3.5 * cm),
        Paragraph(titulo, estilos['titulo_capa']),
        Spacer(1, 0.3 * cm),
        Paragraph(subtitulo, estilos['subtitulo_capa']),
        Spacer(1, 1.2 * cm),
        _linha_divisoria(cor=C_TEAL, espessura=3, espaco_acima=2, espaco_abaixo=12),
        Paragraph(f"Período: {periodo}", estilos['periodo_capa']),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Gerado em: {gerado_em}", estilos['emissao_capa']),
    ]
    if filtros:
        linhas_capa.append(Spacer(1, 0.5 * cm))
        linhas_capa.append(Paragraph(f"Filtros ativos: {filtros}", estilos['emissao_capa']))

    linhas_capa.append(PageBreak())
    return linhas_capa


# ─── CAPA com fundo azul-marinho ─────────────────────────────────────────────

def _cover_page_template(canvas_obj, doc, titulo: str, subtitulo: str,
                         periodo: str, gerado_em: str, filtros: str = ''):
    """Página de capa com fundo navy."""
    w, h = PAGE_W, PAGE_H
    canvas_obj.saveState()

    # Fundo navy
    canvas_obj.setFillColor(C_NAVY)
    canvas_obj.rect(0, 0, w, h, fill=1, stroke=0)

    # Faixa teal no topo
    canvas_obj.setFillColor(C_TEAL)
    canvas_obj.rect(0, h - 0.7 * cm, w, 0.7 * cm, fill=1, stroke=0)

    # Faixa teal embaixo
    canvas_obj.rect(0, 0, w, 0.7 * cm, fill=1, stroke=0)

    # Conteúdo textual da capa
    cy = h * 0.72
    canvas_obj.setFillColor(C_WHITE)
    canvas_obj.setFont('Helvetica-Bold', 30)
    canvas_obj.drawCentredString(w / 2, cy, titulo)

    cy -= 1.2 * cm
    canvas_obj.setFont('Helvetica', 15)
    canvas_obj.setFillColor(colors.HexColor('#AED6F1'))
    canvas_obj.drawCentredString(w / 2, cy, subtitulo)

    cy -= 1.6 * cm
    canvas_obj.setFillColor(C_TEAL)
    canvas_obj.rect(MARGIN, cy, w - 2 * MARGIN, 0.15 * cm, fill=1, stroke=0)

    cy -= 1.0 * cm
    canvas_obj.setFillColor(C_WHITE)
    canvas_obj.setFont('Helvetica-Bold', 18)
    canvas_obj.drawCentredString(w / 2, cy, f"Período: {periodo}")

    cy -= 0.9 * cm
    canvas_obj.setFont('Helvetica', 12)
    canvas_obj.setFillColor(colors.HexColor('#85C1E9'))
    canvas_obj.drawCentredString(w / 2, cy, f"Gerado em: {gerado_em}")

    if filtros:
        cy -= 0.7 * cm
        canvas_obj.setFont('Helvetica', 10)
        canvas_obj.setFillColor(colors.HexColor('#7FB3D3'))
        canvas_obj.drawCentredString(w / 2, cy, f"Filtros: {filtros}")

    # Label inferior
    canvas_obj.setFillColor(colors.HexColor('#AED6F1'))
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.drawCentredString(w / 2, 1.1 * cm,
                                  'Sistema de Gestão Industrial  |  Relatório Confidencial')

    canvas_obj.restoreState()


# ─── Classe principal do documento ───────────────────────────────────────────

class _RelatorioDoc(BaseDocTemplate):
    """BaseDocTemplate personalizado que suporta capa navy + páginas normais."""

    def __init__(self, buf: io.BytesIO, titulo_rel: str, subtitulo_rel: str,
                 periodo: str, gerado_em: str, filtros: str = ''):
        super().__init__(buf, pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN,
                         topMargin=MARGIN + 1.0 * cm, bottomMargin=MARGIN + 0.8 * cm)
        self._titulo_rel = titulo_rel
        self._subtitulo_rel = subtitulo_rel
        self._periodo = periodo
        self._gerado_em = gerado_em
        self._filtros = filtros
        self._is_capa = True

        frame_normal = Frame(
            MARGIN, 1.6 * cm,
            PAGE_W - 2 * MARGIN, PAGE_H - 3.2 * cm,
            id='normal_f',
        )

        def on_page(canvas_obj, doc):
            if self._is_capa:
                _cover_page_template(
                    canvas_obj, doc,
                    self._titulo_rel, self._subtitulo_rel,
                    self._periodo, self._gerado_em, self._filtros,
                )
                self._is_capa = False
            else:
                _header_footer_normal(canvas_obj, doc,
                                      self._titulo_rel, self._periodo)

        self.addPageTemplates([
            PageTemplate(id='main', frames=[frame_normal], onPage=on_page),
        ])


def _header_footer_normal(canvas_obj, doc, titulo_relatorio: str, periodo: str):
    canvas_obj.saveState()
    w = PAGE_W

    canvas_obj.setFillColor(C_NAVY)
    canvas_obj.rect(0, PAGE_H - 1.35 * cm, w, 1.35 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(C_WHITE)
    canvas_obj.setFont('Helvetica-Bold', 9.5)
    canvas_obj.drawString(MARGIN, PAGE_H - 0.88 * cm, titulo_relatorio)
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.drawRightString(w - MARGIN, PAGE_H - 0.88 * cm, periodo)

    canvas_obj.setFillColor(C_GRAY_BG)
    canvas_obj.rect(0, 0, w, 1.15 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(C_GRAY_TEXT)
    canvas_obj.setFont('Helvetica', 7.5)
    canvas_obj.drawString(MARGIN, 0.42 * cm,
                          f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Sistema de Gestão Industrial")
    canvas_obj.setFont('Helvetica-Bold', 8)
    canvas_obj.drawRightString(w - MARGIN, 0.42 * cm, f"Página {doc.page}")

    canvas_obj.restoreState()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — AREALVA MANTA
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_arealva_manta(
    df: pd.DataFrame,
    ini: date,
    fim: date,
    meta_total: float,
    metas: dict,
    filtros_texto: str = '',
) -> bytes:
    """
    Gera o relatório PDF de fechamento do Arealva Manta.

    Parameters
    ----------
    df            : DataFrame filtrado (DATA, OP, COR, QUANTIDADE, ESTACAO, PRODUTO, TAMANHO)
    ini / fim     : período selecionado
    meta_total    : meta diária total ponderada do período
    metas         : dict {estacao: meta_diaria}, ex: {'MAQUINA': 7000, 'MESA 1': 4000}
    filtros_texto : descrição textual dos filtros ativos (ex: "OP: 1234, Tamanho: CASAL")
    """
    e = _estilos()
    periodo_str = f"{ini.strftime('%d/%m/%Y')}  até  {fim.strftime('%d/%m/%Y')}"
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='✂  Relatório de Corte · Arealva Manta',
        subtitulo_rel='Controle de Produção — Manta',
        periodo=periodo_str,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = []

    # ── Capa (página vazia — pintada pelo onPage) ────────────────────────────
    story.append(PageBreak())

    # ── Página 2: Resumo Executivo ──────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    total_pecas = int(df['QUANTIDADE'].sum())
    dias_trab = df['DATA'].dt.date.nunique()
    total_ops = df['OP'].nunique()
    total_cores = df['COR'].nunique()
    media_dia = total_pecas / max(dias_trab, 1)
    pct_meta = (media_dia / meta_total * 100) if meta_total > 0 else 0

    kpis = [
        {'label': '✂  Total de Peças', 'valor': _fmt(total_pecas), 'cor': C_TEAL_LT},
        {'label': '📆 Dias Trabalhados', 'valor': str(dias_trab), 'cor': C_GRAY_BG},
        {'label': '⚡ Média Peças/Dia', 'valor': _fmt(media_dia), 'cor': _pct_bg(pct_meta)},
        {'label': '🎯 % da Meta', 'valor': f'{pct_meta:.1f}%', 'cor': _pct_bg(pct_meta)},
        {'label': '📋 Total de OPs', 'valor': str(total_ops), 'cor': C_GRAY_BG},
        {'label': '🎨 Cores', 'valor': str(total_cores), 'cor': C_GRAY_BG},
        {'label': '🎯 Meta Total/Dia', 'valor': _fmt(meta_total), 'cor': C_AMBER_LT},
        {'label': '📅 Período', 'valor': f'{ini.strftime("%d/%m")}–{fim.strftime("%d/%m/%Y")}',
         'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=4))
    story.append(Spacer(1, 0.6 * cm))

    # ── Tabela por Estação ───────────────────────────────────────────────────
    story.append(Paragraph('Desempenho por Estação', e['subtitulo_secao']))

    cabec_est = ['Estação', 'Meta Diária', 'Total Peças', 'Dias', 'Média/Dia',
                 '% Meta', 'Dias ≥ Meta', 'Status']
    linhas_est = []
    prod_dia_geral = df.groupby('DATA')['QUANTIDADE'].sum()

    for est, meta_est in metas.items():
        df_est = df[df['ESTACAO'] == est]
        if df_est.empty:
            continue
        total_e = int(df_est['QUANTIDADE'].sum())
        dias_e = df_est['DATA'].dt.date.nunique()
        media_e = total_e / max(dias_e, 1)
        pct_e = (media_e / meta_est * 100) if meta_est > 0 else 0
        prod_est_dia = df_est.groupby('DATA')['QUANTIDADE'].sum()
        dias_acima_e = (prod_est_dia >= meta_est).sum()
        status = '✔ META' if pct_e >= 100 else ('~ PERTO' if pct_e >= 80 else '✘ ABAIXO')
        linhas_est.append([
            est, _fmt(meta_est), _fmt(total_e), str(dias_e),
            _fmt(media_e), f'{pct_e:.1f}%',
            f'{dias_acima_e}/{dias_e}', status,
        ])

    larg_total = PAGE_W - 2 * MARGIN
    cw_est = [2.8*cm, 2.2*cm, 2.2*cm, 1.4*cm, 2.2*cm, 1.8*cm, 2.2*cm, 2.5*cm]
    t_est = _tabela_generica(cabec_est, linhas_est, e, cw_est)

    # Colorir linha de status
    for ri, linha in enumerate(linhas_est, start=1):
        pct_val = float(linha[5].replace('%', '').replace(',', '.'))
        cor_s = C_GREEN if pct_val >= 100 else (C_AMBER if pct_val >= 80 else C_RED)
        t_est.setStyle(TableStyle([
            ('TEXTCOLOR', (7, ri), (7, ri), cor_s),
            ('FONTNAME', (7, ri), (7, ri), 'Helvetica-Bold'),
        ]))
    story.append(t_est)
    story.append(Spacer(1, 0.4 * cm))

    # ── Observações sobre dias ────────────────────────────────────────────────
    from datetime import timedelta as _td
    datas_set = set(df['DATA'].dt.date.unique())
    dias_uteis = [ini + _td(days=i) for i in range((fim - ini).days + 1)
                  if (ini + _td(days=i)).weekday() < 5]
    dias_sabado = [ini + _td(days=i) for i in range((fim - ini).days + 1)
                   if (ini + _td(days=i)).weekday() == 5]
    sabados_trab = [d for d in dias_sabado if d in datas_set]
    dias_ausentes = [d for d in dias_uteis if d not in datas_set]

    obs_parts = []
    if sabados_trab:
        obs_parts.append(f"<b>Sábados trabalhados ({len(sabados_trab)}):</b> "
                         + ', '.join(d.strftime('%d/%m') for d in sabados_trab))
    if dias_ausentes:
        obs_parts.append(f"<b>Dias úteis sem registro ({len(dias_ausentes)}):</b> "
                         + ', '.join(d.strftime('%d/%m') for d in dias_ausentes[:20])
                         + (' ...' if len(dias_ausentes) > 20 else ''))
    if obs_parts:
        story.append(Paragraph('<br/>'.join(obs_parts), e['nota']))

    story.append(PageBreak())

    # ── Página 3: Produção Diária ────────────────────────────────────────────
    story.append(Paragraph('Produção Diária', e['titulo_secao']))
    story.append(_linha_divisoria())

    prod_diaria = df.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
    if not prod_diaria.empty:
        buf_chart = _chart_producao_diaria(
            prod_diaria, meta_total,
            titulo=f'Produção Diária — Arealva Manta  |  Meta: {_fmt(meta_total)} pç/dia',
        )
        story.append(_imagem_de_buf(buf_chart, largura_cm=16.5))
        story.append(Spacer(1, 0.5 * cm))

    # Tabela de produção diária
    story.append(Paragraph('Detalhamento Diário', e['subtitulo_secao']))
    cabec_dd = ['Data', 'Dia', 'Peças', 'vs Meta', '% Meta', 'MAQUINA', 'MESA 1']
    linhas_dd = []
    dias_semana_pt = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    for _, row in prod_diaria.iterrows():
        d = pd.Timestamp(row['DATA'])
        q = int(row['QUANTIDADE'])
        vs = q - meta_total if meta_total > 0 else 0
        pct = (q / meta_total * 100) if meta_total > 0 else 0
        maq = int(df[(df['DATA'] == row['DATA']) & (df['ESTACAO'] == 'MAQUINA')]['QUANTIDADE'].sum())
        mesa = int(df[(df['DATA'] == row['DATA']) & (df['ESTACAO'] == 'MESA 1')]['QUANTIDADE'].sum())
        linhas_dd.append([
            d.strftime('%d/%m/%Y'),
            dias_semana_pt.get(d.weekday(), ''),
            _fmt(q),
            f'{vs:+,.0f}'.replace(',', '.'),
            f'{pct:.1f}%',
            _fmt(maq),
            _fmt(mesa),
        ])

    cw_dd = [2.2*cm, 1.2*cm, 2.0*cm, 2.0*cm, 1.6*cm, 2.2*cm, 2.2*cm]
    t_dd = _tabela_generica(cabec_dd, linhas_dd, e, cw_dd)
    # Colorir % Meta
    for ri, linha in enumerate(linhas_dd, start=1):
        try:
            pct_val = float(linha[4].replace('%', '').replace(',', '.'))
            cor_s = C_GREEN if pct_val >= 100 else (C_AMBER if pct_val >= 80 else C_RED)
            t_dd.setStyle(TableStyle([
                ('TEXTCOLOR', (4, ri), (4, ri), cor_s),
                ('FONTNAME', (4, ri), (4, ri), 'Helvetica-Bold'),
            ]))
        except Exception:
            pass
    story.append(t_dd)
    story.append(PageBreak())

    # ── Página 4: Distribuição & Top Cores ─────────────────────────────────
    story.append(Paragraph('Distribuição por Estação e Cores', e['titulo_secao']))
    story.append(_linha_divisoria())

    # Gráficos lado a lado
    dist_estacao = df.groupby('ESTACAO')['QUANTIDADE'].sum().reset_index()
    prod_cor = df.groupby('COR')['QUANTIDADE'].sum().reset_index()

    if not dist_estacao.empty:
        buf_pizza = _chart_pizza_estacao(
            dist_estacao, 'ESTACAO', 'QUANTIDADE', 'Distribuição por Estação de Corte',
        )
        buf_cores = _chart_barras_h(
            prod_cor, 'COR', 'QUANTIDADE', 'Top 15 Cores Mais Cortadas', top_n=15,
        )
        img_pizza = _imagem_de_buf(buf_pizza, largura_cm=8.0)
        img_cores = _imagem_de_buf(buf_cores, largura_cm=8.0)

        t_imgs = Table([[img_pizza, img_cores]],
                       colWidths=[(PAGE_W - 2 * MARGIN) / 2] * 2)
        t_imgs.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(t_imgs)
        story.append(Spacer(1, 0.5 * cm))

    # Top 20 cores em tabela
    story.append(Paragraph('Top 20 Cores por Volume', e['subtitulo_secao']))
    cor_tab = prod_cor.sort_values('QUANTIDADE', ascending=False).head(20)
    cor_tab['%'] = (cor_tab['QUANTIDADE'] / cor_tab['QUANTIDADE'].sum() * 100).round(1)
    cabec_cor = ['#', 'Cor', 'Peças', '% do Total']
    linhas_cor = [
        [str(i + 1), row['COR'], _fmt(row['QUANTIDADE']), f"{row['%']:.1f}%"]
        for i, (_, row) in enumerate(cor_tab.iterrows())
    ]
    cw_cor = [1.0*cm, 7.0*cm, 3.0*cm, 2.5*cm]
    story.append(_tabela_generica(cabec_cor, linhas_cor, e, cw_cor))
    story.append(PageBreak())

    # ── Página 5: Análise de OPs ─────────────────────────────────────────────
    story.append(Paragraph('Análise por Ordem de Produção (OP)', e['titulo_secao']))
    story.append(_linha_divisoria())

    resumo_op = df.groupby('OP').agg(
        Total=('QUANTIDADE', 'sum'),
        Cores=('COR', 'nunique'),
        Produto=('PRODUTO', 'first'),
        Inicio=('DATA', 'min'),
        Fim=('DATA', 'max'),
        Dias=('DATA', lambda x: x.dt.date.nunique()),
    ).reset_index().sort_values('Total', ascending=False)

    cabec_op = ['OP', 'Produto', 'Total Peças', 'Cores', 'Início', 'Fim', 'Dias']
    linhas_op = []
    for row in resumo_op.itertuples():
        linhas_op.append([
            str(row.OP),
            str(row.Produto)[:28],
            _fmt(row.Total),
            str(row.Cores),
            pd.Timestamp(row.Inicio).strftime('%d/%m/%Y') if pd.notna(row.Inicio) else '',
            pd.Timestamp(row.Fim).strftime('%d/%m/%Y') if pd.notna(row.Fim) else '',
            str(row.Dias),
        ])
    cw_op = [2.0*cm, 5.5*cm, 2.4*cm, 1.4*cm, 2.0*cm, 2.0*cm, 1.2*cm]
    story.append(_tabela_generica(cabec_op, linhas_op[:50], e, cw_op))
    if len(linhas_op) > 50:
        story.append(Paragraph(f'... e mais {len(linhas_op) - 50} OPs.', e['nota']))
    story.append(PageBreak())

    # ── Página 6: Tamanhos (se disponível) ──────────────────────────────────
    if 'TAMANHO' in df.columns:
        tamanhos_validos = df[
            df['TAMANHO'].notna() &
            (df['TAMANHO'].astype(str).str.strip() != '') &
            (df['TAMANHO'].astype(str).str.lower() != 'nan')
        ]
        if not tamanhos_validos.empty:
            story.append(Paragraph('Análise por Tamanho', e['titulo_secao']))
            story.append(_linha_divisoria())

            # Por tamanho geral
            tam_geral = tamanhos_validos.groupby('TAMANHO')['QUANTIDADE'].sum().reset_index()
            tam_geral['%'] = (tam_geral['QUANTIDADE'] / tam_geral['QUANTIDADE'].sum() * 100).round(1)
            tam_geral = tam_geral.sort_values('QUANTIDADE', ascending=False)
            cabec_tam = ['Tamanho', 'Peças', '% do Total']
            linhas_tam = [
                [row['TAMANHO'], _fmt(row['QUANTIDADE']), f"{row['%']:.1f}%"]
                for _, row in tam_geral.iterrows()
            ]
            cw_tam = [4*cm, 4*cm, 3*cm]
            story.append(Paragraph('Volume Total por Tamanho', e['subtitulo_secao']))
            story.append(_tabela_generica(cabec_tam, linhas_tam, e, cw_tam))
            story.append(Spacer(1, 0.5*cm))

            # Por estação × tamanho
            story.append(Paragraph('Volume por Estação × Tamanho', e['subtitulo_secao']))
            tam_est = (tamanhos_validos.groupby(['ESTACAO', 'TAMANHO'])['QUANTIDADE']
                       .sum().reset_index().sort_values('QUANTIDADE', ascending=False))
            cabec_et = ['Estação', 'Tamanho', 'Peças', '% do Total']
            linhas_et = [
                [row['ESTACAO'], row['TAMANHO'], _fmt(row['QUANTIDADE']),
                 f"{row['QUANTIDADE'] / tamanhos_validos['QUANTIDADE'].sum() * 100:.1f}%"]
                for _, row in tam_est.iterrows()
            ]
            cw_et = [3*cm, 3.5*cm, 3*cm, 2.5*cm]
            story.append(_tabela_generica(cabec_et, linhas_et, e, cw_et))
            story.append(PageBreak())

    # ── Página final: Conclusão ──────────────────────────────────────────────
    story.append(Paragraph('Conclusão do Período', e['titulo_secao']))
    story.append(_linha_divisoria())

    status_geral = 'META ATINGIDA ✔' if pct_meta >= 100 else ('PRÓXIMO DA META ⚠' if pct_meta >= 80 else 'ABAIXO DA META ✘')
    cor_status = C_GREEN if pct_meta >= 100 else (C_AMBER if pct_meta >= 80 else C_RED)

    conclusao_html = (
        f'No período de <b>{ini.strftime("%d/%m/%Y")}</b> a <b>{fim.strftime("%d/%m/%Y")}</b>, '
        f'o setor de Corte Manta em Arealva registrou <b>{_fmt(total_pecas)} peças</b> '
        f'ao longo de <b>{dias_trab} dias trabalhados</b>, resultando em uma média diária de '
        f'<b>{_fmt(media_dia)} peças/dia</b> ({pct_meta:.1f}% da meta de {_fmt(meta_total)} pç/dia). '
        f'Foram processadas <b>{total_ops} OPs</b> em <b>{total_cores} cores</b> distintas.'
    )
    story.append(Paragraph(conclusao_html, e['corpo']))
    story.append(Spacer(1, 0.4*cm))

    status_p = ParagraphStyle(
        'status', parent=e['corpo'],
        fontName='Helvetica-Bold', fontSize=13,
        textColor=cor_status, alignment=TA_CENTER,
        spaceBefore=12, spaceAfter=12,
    )
    story.append(Paragraph(f'STATUS GERAL: {status_geral}', status_p))
    story.append(_linha_divisoria(cor=cor_status, espessura=2))

    story.append(Spacer(1, 1.0*cm))
    assinatura = ParagraphStyle(
        'assinatura', parent=e['nota'],
        alignment=TA_CENTER, fontSize=8,
    )
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Arealva Manta  ·  {gerado_em}',
        assinatura,
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — IACANGA MANTA
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_iacanga_manta(
    df: pd.DataFrame,
    ini: date,
    fim: date,
    meta_total: float,
    metas_por_grupo: dict,
    filtros_texto: str = '',
) -> bytes:
    """
    Gera o relatório PDF de fechamento do Iacanga Manta.

    Parameters
    ----------
    df              : DataFrame filtrado (DATA, OP, COR, QUANTIDADE, ESTACAO, PRODUTO, TAMANHO)
    ini / fim       : período selecionado
    meta_total      : meta diária total ponderada do período
    metas_por_grupo : dict {grupo: {tamanho: meta}}, ex: METAS_POR_TAMANHO
    filtros_texto   : descrição textual dos filtros ativos
    """
    e = _estilos()
    periodo_str = f"{ini.strftime('%d/%m/%Y')}  até  {fim.strftime('%d/%m/%Y')}"
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='✂  Relatório de Corte · Iacanga — Mantas Giattex',
        subtitulo_rel='Controle de Produção — Manta (Giattex)',
        periodo=periodo_str,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = []
    story.append(PageBreak())  # capa

    # ── Resumo Executivo ─────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    total_pecas = int(df['QUANTIDADE'].sum())
    dias_trab = df['DATA'].dt.date.nunique()
    total_ops = df['OP'].nunique()
    total_cores = df['COR'].nunique() if 'COR' in df.columns else 0
    media_dia = total_pecas / max(dias_trab, 1)
    pct_meta = (media_dia / meta_total * 100) if meta_total > 0 else 0

    kpis = [
        {'label': '✂  Total de Peças', 'valor': _fmt(total_pecas), 'cor': C_TEAL_LT},
        {'label': '📆 Dias Trabalhados', 'valor': str(dias_trab), 'cor': C_GRAY_BG},
        {'label': '⚡ Média Peças/Dia', 'valor': _fmt(media_dia), 'cor': _pct_bg(pct_meta)},
        {'label': '🎯 % da Meta', 'valor': f'{pct_meta:.1f}%', 'cor': _pct_bg(pct_meta)},
        {'label': '📋 Total de OPs', 'valor': str(total_ops), 'cor': C_GRAY_BG},
        {'label': '🎨 Cores', 'valor': str(total_cores), 'cor': C_GRAY_BG},
        {'label': '🎯 Meta Total/Dia', 'valor': _fmt(meta_total), 'cor': C_AMBER_LT},
        {'label': '📏 Tamanhos', 'valor': str(df['TAMANHO'].nunique()) if 'TAMANHO' in df.columns else '–',
         'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=4))
    story.append(Spacer(1, 0.5*cm))

    # Tabela por estação
    story.append(Paragraph('Desempenho por Estação', e['subtitulo_secao']))
    estacoes_iac = df['ESTACAO'].dropna().unique().tolist()
    cabec_est = ['Estação', 'Grupo Meta', 'Total Peças', 'Dias', 'Média/Dia', '% Meta Ref.']
    linhas_est = []
    GRUPOS_IAC = {
        'MAQUINA': 'MAQUINA', 'MESA': 'MESA', 'BURDAY': 'BURDAY',
    }
    for est in sorted(estacoes_iac):
        df_est = df[df['ESTACAO'] == est]
        total_e = int(df_est['QUANTIDADE'].sum())
        dias_e = df_est['DATA'].dt.date.nunique()
        media_e = total_e / max(dias_e, 1)
        # Referência de meta (usando _DEFAULT ou CASAL como base)
        grupo = 'MAQUINA' if 'MAQUINA' in est.upper() else ('BURDAY' if 'BURDAY' in est.upper() else 'MESA')
        metas_g = metas_por_grupo.get(grupo, {})
        meta_ref = metas_g.get('CASAL', metas_g.get('_DEFAULT', 0))
        pct_e = (media_e / meta_ref * 100) if meta_ref > 0 else 0
        linhas_est.append([
            est[:20], grupo, _fmt(total_e), str(dias_e),
            _fmt(media_e), f'{pct_e:.1f}% (ref. CASAL)',
        ])
    cw_est_i = [3.5*cm, 2.2*cm, 2.2*cm, 1.4*cm, 2.2*cm, 4.5*cm]
    story.append(_tabela_generica(cabec_est, linhas_est, e, cw_est_i))
    story.append(Spacer(1, 0.4*cm))

    # Metas por Tamanho (tabela de referência)
    story.append(Paragraph('Tabela de Metas por Tamanho (Referência)', e['subtitulo_secao']))
    tam_ref_cabec = ['Grupo', 'Solteiro', 'Casal', 'Queen', 'King']
    tam_ref_linhas = []
    for grupo, metas_g in metas_por_grupo.items():
        tam_ref_linhas.append([
            grupo,
            _fmt(metas_g.get('SOLTEIRO', metas_g.get('_DEFAULT', '—'))),
            _fmt(metas_g.get('CASAL', metas_g.get('_DEFAULT', '—'))),
            _fmt(metas_g.get('QUEEN', metas_g.get('_DEFAULT', '—'))),
            _fmt(metas_g.get('KING', metas_g.get('_DEFAULT', '—'))),
        ])
    cw_tr = [3*cm, 3*cm, 3*cm, 3*cm, 3*cm]
    story.append(_tabela_generica(tam_ref_cabec, tam_ref_linhas, e, cw_tr))

    story.append(PageBreak())

    # ── Produção Diária ──────────────────────────────────────────────────────
    story.append(Paragraph('Produção Diária', e['titulo_secao']))
    story.append(_linha_divisoria())

    prod_diaria = df.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
    if not prod_diaria.empty:
        buf_chart = _chart_producao_diaria(
            prod_diaria, meta_total,
            titulo=f'Produção Diária — Iacanga Mantas Giattex  |  Meta (ponderada): {_fmt(meta_total)} pç/dia',
        )
        story.append(_imagem_de_buf(buf_chart, largura_cm=16.5))
        story.append(Spacer(1, 0.4*cm))

    # Tabela diária
    cabec_dd = ['Data', 'Dia', 'Peças', 'vs Meta', '% Meta']
    dias_semana_pt = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    linhas_dd = []
    for _, row in prod_diaria.iterrows():
        d = pd.Timestamp(row['DATA'])
        q = int(row['QUANTIDADE'])
        vs = q - meta_total if meta_total > 0 else 0
        pct = (q / meta_total * 100) if meta_total > 0 else 0
        linhas_dd.append([
            d.strftime('%d/%m/%Y'),
            dias_semana_pt.get(d.weekday(), ''),
            _fmt(q),
            f'{vs:+,.0f}'.replace(',', '.'),
            f'{pct:.1f}%',
        ])
    cw_dd = [2.5*cm, 1.4*cm, 2.5*cm, 2.5*cm, 2.0*cm]
    t_dd = _tabela_generica(cabec_dd, linhas_dd, e, cw_dd)
    for ri, linha in enumerate(linhas_dd, start=1):
        try:
            pct_val = float(linha[4].replace('%', '').replace(',', '.'))
            cor_s = C_GREEN if pct_val >= 100 else (C_AMBER if pct_val >= 80 else C_RED)
            t_dd.setStyle(TableStyle([
                ('TEXTCOLOR', (4, ri), (4, ri), cor_s),
                ('FONTNAME', (4, ri), (4, ri), 'Helvetica-Bold'),
            ]))
        except Exception:
            pass
    story.append(t_dd)
    story.append(PageBreak())

    # ── Análise por Tamanho ──────────────────────────────────────────────────
    if 'TAMANHO' in df.columns:
        tam_validos = df[
            df['TAMANHO'].notna() &
            (df['TAMANHO'].astype(str).str.strip() != '') &
            (df['TAMANHO'].astype(str).str.lower() != 'nan')
        ]
        if not tam_validos.empty:
            story.append(Paragraph('Análise por Tamanho', e['titulo_secao']))
            story.append(_linha_divisoria())

            buf_tam = _chart_barras_h(
                tam_validos.groupby('TAMANHO')['QUANTIDADE'].sum().reset_index(),
                'TAMANHO', 'QUANTIDADE', 'Volume por Tamanho de Manta', top_n=10, cor='#D4860A',
            )
            story.append(_imagem_de_buf(buf_tam, largura_cm=12))
            story.append(Spacer(1, 0.4*cm))

            # Tabela est × tamanho
            story.append(Paragraph('Estação × Tamanho', e['subtitulo_secao']))
            tam_est = (tam_validos.groupby(['ESTACAO', 'TAMANHO'])['QUANTIDADE']
                       .sum().reset_index().sort_values('QUANTIDADE', ascending=False))
            tam_total = tam_validos['QUANTIDADE'].sum()
            cabec_et = ['Estação', 'Tamanho', 'Peças', '% Total']
            linhas_et = [
                [row['ESTACAO'][:20], row['TAMANHO'],
                 _fmt(row['QUANTIDADE']),
                 f"{row['QUANTIDADE'] / tam_total * 100:.1f}%"]
                for _, row in tam_est.iterrows()
            ]
            cw_et = [3.5*cm, 3.5*cm, 3*cm, 2.5*cm]
            story.append(_tabela_generica(cabec_et, linhas_et, e, cw_et))
            story.append(PageBreak())

    # ── OPs ──────────────────────────────────────────────────────────────────
    story.append(Paragraph('Análise por Ordem de Produção (OP)', e['titulo_secao']))
    story.append(_linha_divisoria())

    resumo_op = df.groupby('OP').agg(
        Total=('QUANTIDADE', 'sum'),
        Cores=('COR', 'nunique') if 'COR' in df.columns else ('QUANTIDADE', 'count'),
        Tamanhos=('TAMANHO', lambda x: ', '.join(sorted(x.dropna().unique()))) if 'TAMANHO' in df.columns else ('QUANTIDADE', 'count'),
        Inicio=('DATA', 'min'),
        Fim=('DATA', 'max'),
        Dias=('DATA', lambda x: x.dt.date.nunique()),
    ).reset_index().sort_values('Total', ascending=False)

    cabec_op = ['OP', 'Total Peças', 'Cores', 'Tamanhos', 'Início', 'Fim', 'Dias']
    linhas_op = []
    for row in resumo_op.itertuples():
        tam_str = str(getattr(row, 'Tamanhos', ''))[:25]
        linhas_op.append([
            str(row.OP),
            _fmt(row.Total),
            str(getattr(row, 'Cores', '')),
            tam_str,
            pd.Timestamp(row.Inicio).strftime('%d/%m/%Y') if pd.notna(row.Inicio) else '',
            pd.Timestamp(row.Fim).strftime('%d/%m/%Y') if pd.notna(row.Fim) else '',
            str(row.Dias),
        ])
    cw_op = [2.2*cm, 2.5*cm, 1.5*cm, 3.5*cm, 2.0*cm, 2.0*cm, 1.3*cm]
    story.append(_tabela_generica(cabec_op, linhas_op[:50], e, cw_op))
    if len(linhas_op) > 50:
        story.append(Paragraph(f'... e mais {len(linhas_op) - 50} OPs.', e['nota']))
    story.append(PageBreak())

    # ── Conclusão ────────────────────────────────────────────────────────────
    story.append(Paragraph('Conclusão do Período', e['titulo_secao']))
    story.append(_linha_divisoria())

    conclusao_html = (
        f'No período de <b>{ini.strftime("%d/%m/%Y")}</b> a <b>{fim.strftime("%d/%m/%Y")}</b>, '
        f'o setor de Corte Manta em Iacanga (Giattex) registrou <b>{_fmt(total_pecas)} peças</b> '
        f'em <b>{dias_trab} dias trabalhados</b>, com média de '
        f'<b>{_fmt(media_dia)} peças/dia</b> ({pct_meta:.1f}% da meta ponderada de {_fmt(meta_total)} pç/dia). '
        f'Foram processadas <b>{total_ops} OPs</b>.'
    )
    story.append(Paragraph(conclusao_html, e['corpo']))
    story.append(Spacer(1, 0.4*cm))

    status_geral = 'META ATINGIDA ✔' if pct_meta >= 100 else ('PRÓXIMO DA META ⚠' if pct_meta >= 80 else 'ABAIXO DA META ✘')
    cor_status = C_GREEN if pct_meta >= 100 else (C_AMBER if pct_meta >= 80 else C_RED)
    status_p = ParagraphStyle('status_i', parent=e['corpo'],
                               fontName='Helvetica-Bold', fontSize=13,
                               textColor=cor_status, alignment=TA_CENTER, spaceBefore=12)
    story.append(Paragraph(f'STATUS GERAL: {status_geral}', status_p))
    story.append(_linha_divisoria(cor=cor_status, espessura=2))
    story.append(Spacer(1, 1.0*cm))
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Iacanga · Mantas Giattex  ·  {gerado_em}',
        ParagraphStyle('ass_i', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — LENÇOL
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_lencol(
    df: pd.DataFrame,
    ini: date,
    fim: date,
    filtros_texto: str = '',
    caseamento_df: Optional[pd.DataFrame] = None,
    totais_jf: Optional[dict] = None,
) -> bytes:
    """
    Gera o relatório PDF de fechamento do Corte de Lençol.

    Parameters
    ----------
    df            : DataFrame filtrado (DATA, PRESTADOR, OP, CATEGORIA, EMPRESA,
                    TECIDO, QUANT, VALOR_PECA, VALOR_RECEBER, CAT_BASE, ANO_MES, MES_NOME)
    ini / fim     : período selecionado
    filtros_texto : descrição textual dos filtros ativos
    caseamento_df : DataFrame de caseamento jogo×fundo (OP, TAMANHO, JOGO, FUNDO,
                    DIFERENCA, STATUS). Quando fornecido, adiciona a seção de caseamento.
    totais_jf     : dict com total_pecas, total_sem_fundo, total_fundos, total_jogos_duplo.
    """
    e = _estilos()
    periodo_str = f"{ini.strftime('%d/%m/%Y')}  até  {fim.strftime('%d/%m/%Y')}"
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='✂  Relatório de Corte · Lençol',
        subtitulo_rel='Controle de Produção — Lençol',
        periodo=periodo_str,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = []
    story.append(PageBreak())  # capa

    # Métricas globais
    total_pecas = int(df['QUANT'].sum()) if 'QUANT' in df.columns else 0
    total_valor = df['VALOR_RECEBER'].sum() if 'VALOR_RECEBER' in df.columns else 0

    # Totais de caseamento (jogo × fundo)
    if totais_jf:
        total_fundos = int(totais_jf.get('total_fundos', 0))
        total_sem_fundo = int(totais_jf.get('total_sem_fundo', total_pecas - total_fundos))
        total_jogos_duplo = int(totais_jf.get('total_jogos_duplo', 0))
    else:
        total_fundos = 0
        total_sem_fundo = total_pecas
        total_jogos_duplo = 0

    dias_trab = df['DATA'].dt.date.nunique()
    media_diaria = total_sem_fundo / max(dias_trab, 1)
    n_prest = df['PRESTADOR'].nunique() if 'PRESTADOR' in df.columns else 0
    n_emp = df['EMPRESA'].nunique() if 'EMPRESA' in df.columns else 0
    ticket_medio = total_valor / total_pecas if total_pecas > 0 else 0
    n_ops = df['OP'].nunique() if 'OP' in df.columns else 0

    top_prest = (df.groupby('PRESTADOR')['QUANT'].sum().idxmax()
                 if 'PRESTADOR' in df.columns and not df.empty else '—')
    top_emp = (df.groupby('EMPRESA')['QUANT'].sum().idxmax()
               if 'EMPRESA' in df.columns and not df.empty else '—')

    # ── Resumo Executivo ─────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    _label_pecas = '🧵 Peças (s/ fundo)' if total_fundos > 0 else '🧵 Total de Peças'
    kpis = [
        {'label': _label_pecas, 'valor': _fmt(total_sem_fundo), 'cor': C_TEAL_LT},
        {'label': '🔄 Fundos de Jogo', 'valor': _fmt(total_fundos), 'cor': C_AMBER_LT},
        {'label': '💰 Total a Pagar/Pago', 'valor': f'R$ {_fmt(total_valor, 2)}', 'cor': C_GREEN_LT},
        {'label': '📆 Dias Trabalhados', 'valor': str(dias_trab), 'cor': C_GRAY_BG},
        {'label': '📈 Média Diária', 'valor': f'{_fmt(media_diaria, 0)} pç/dia', 'cor': C_GRAY_BG},
        {'label': '👷 Prestadores', 'valor': str(n_prest), 'cor': C_GRAY_BG},
        {'label': '🏭 Empresas', 'valor': str(n_emp), 'cor': C_GRAY_BG},
        {'label': '💲 Ticket Médio', 'valor': f'R$ {_fmt(ticket_medio, 4)}', 'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=4))
    story.append(Spacer(1, 0.4*cm))

    # Destaques
    story.append(Paragraph(
        f'🥇 Top Prestador: <b>{top_prest}</b>   |   🏆 Top Empresa: <b>{top_emp}</b>   |   '
        f'📋 OPs: <b>{n_ops}</b>',
        e['corpo'],
    ))
    story.append(Spacer(1, 0.3*cm))

    # ── Caseamento Jogo Duplo × Fundo ────────────────────────────────────────
    if caseamento_df is not None and not caseamento_df.empty:
        story.append(Paragraph('Caseamento Jogo Duplo × Fundo', e['subtitulo_secao']))
        _jogo_tot = int(caseamento_df['JOGO'].sum())
        _fundo_tot = int(caseamento_df['FUNDO'].sum())
        # Saldo de fundos = FUNDO − JOGO (negativo = faltam fundos)
        _dif_tot = _fundo_tot - _jogo_tot
        _div = caseamento_df[caseamento_df['DIFERENCA'] != 0]
        _n_div = len(_div)
        _n_ok = int((caseamento_df['DIFERENCA'] == 0).sum())

        resumo_cas = (
            f'Considerando apenas as OPs que tiveram corte de fundo: '
            f'<b>{_fmt(_jogo_tot)} jogos duplos</b> vs <b>{_fmt(_fundo_tot)} fundos</b>. '
        )
        if _dif_tot == 0:
            resumo_cas += 'Tudo <b>caseado</b> ✔'
        elif _dif_tot < 0:
            resumo_cas += f'<b>Faltam {_fmt(abs(_dif_tot))} fundos</b> para casear ✘'
        else:
            resumo_cas += f'<b>Sobram {_fmt(_dif_tot)} fundos</b> ✘'
        resumo_cas += f'  ({_n_div} par(es) divergente(s), {_n_ok} caseado(s)).'
        story.append(Paragraph(resumo_cas, e['corpo']))
        story.append(Paragraph(
            f'<i>Observação: este caseamento cobre apenas os jogos duplos das OPs que tiveram '
            f'fundo. O KPI "Peças (s/ fundo)" ({_fmt(total_sem_fundo)}) é mais amplo — inclui '
            f'também jogos simples e outros produtos (fronha, lençol avulso), por isso é maior '
            f'que os {_fmt(_jogo_tot)} jogos duplos mostrados aqui.</i>',
            e['nota'],
        ))
        story.append(Spacer(1, 0.2*cm))

        # Tabela de divergências (ou todos se poucos)
        _tab_cas = _div if _n_div > 0 else caseamento_df
        cabec_cas = ['OP', 'Tamanho', 'Jogo', 'Fundo', 'Diferença', 'Status']
        linhas_cas = []
        for _, r in _tab_cas.head(40).iterrows():
            _d = int(r['DIFERENCA'])
            _st = str(r['STATUS']).replace('🔴', '').replace('🟠', '').replace('✅', '').strip()
            linhas_cas.append([
                str(r['OP']), str(r['TAMANHO']),
                _fmt(int(r['JOGO'])), _fmt(int(r['FUNDO'])),
                f"{'+' if _d > 0 else ''}{_fmt(_d)}", _st,
            ])
        cw_cas = [2.5*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 3.5*cm]
        t_cas = _tabela_generica(cabec_cas, linhas_cas, e, cw_cas)
        # Colorir diferença (negativo = faltam fundos = vermelho)
        for ri, (_, r) in enumerate(_tab_cas.head(40).iterrows(), start=1):
            _d = int(r['DIFERENCA'])
            cor_s = C_GREEN if _d == 0 else (C_RED if _d < 0 else C_AMBER)
            t_cas.setStyle(TableStyle([
                ('TEXTCOLOR', (4, ri), (4, ri), cor_s),
                ('FONTNAME', (4, ri), (4, ri), 'Helvetica-Bold'),
            ]))
        story.append(t_cas)
        if _n_div > 40:
            story.append(Paragraph(f'... e mais {_n_div - 40} divergência(s).', e['nota']))
        story.append(Paragraph(
            'Faltam fundos = jogo cortado sem fundo suficiente.  '
            'Sobram fundos = fundo cortado a mais que o jogo.', e['nota'],
        ))
    story.append(Spacer(1, 0.3*cm))

    # ── Tabela por Prestador ─────────────────────────────────────────────────
    story.append(Paragraph('Desempenho por Prestador', e['subtitulo_secao']))
    if 'PRESTADOR' in df.columns:
        df_prest = (
            df.groupby('PRESTADOR')
            .agg(Peças=('QUANT', 'sum'), Valor=('VALOR_RECEBER', 'sum'),
                 Dias=('DATA', 'nunique'))
            .reset_index().sort_values('Peças', ascending=False)
        )
        df_prest['Média/Dia'] = (df_prest['Peças'] / df_prest['Dias']).round(0).astype(int)
        df_prest['R$/Peça'] = (df_prest['Valor'] / df_prest['Peças']).round(4)
        df_prest['%'] = (df_prest['Peças'] / df_prest['Peças'].sum() * 100).round(1)

        cabec_pr = ['Prestador', 'Peças', '% Total', 'Valor (R$)', 'Dias', 'Média/Dia', 'R$/Peça']
        linhas_pr = [
            [row['PRESTADOR'][:28], _fmt(row['Peças']), f"{row['%']:.1f}%",
             f"R$ {_fmt(row['Valor'], 2)}", str(row['Dias']),
             _fmt(row['Média/Dia']), f"R$ {_fmt(row['R$/Peça'], 4)}"]
            for _, row in df_prest.iterrows()
        ]
        cw_pr = [3.5*cm, 2.0*cm, 1.8*cm, 2.8*cm, 1.2*cm, 2.0*cm, 2.2*cm]
        story.append(_tabela_generica(cabec_pr, linhas_pr, e, cw_pr))
    story.append(PageBreak())

    # ── Página 3: Gráficos ───────────────────────────────────────────────────
    story.append(Paragraph('Análise Visual', e['titulo_secao']))
    story.append(_linha_divisoria())

    # Gráfico produção diária
    if 'QUANT' in df.columns:
        prod_dia = df.groupby('DATA')['QUANT'].sum().reset_index().sort_values('DATA')
        prod_dia.columns = ['DATA', 'QUANTIDADE']
        buf_dia = _chart_producao_diaria(
            prod_dia, 0,
            titulo='Produção Diária — Lençol',
        )
        story.append(_imagem_de_buf(buf_dia, largura_cm=16.5))
        story.append(Spacer(1, 0.4*cm))

    # Gráficos: empresa + prestador
    if 'EMPRESA' in df.columns and 'PRESTADOR' in df.columns:
        dist_emp = df.groupby('EMPRESA')['QUANT'].sum().reset_index()
        buf_emp = _chart_pizza_estacao(dist_emp, 'EMPRESA', 'QUANT', 'Distribuição por Empresa')

        df_prest2 = df.groupby('PRESTADOR').agg(
            Peças=('QUANT', 'sum'), Valor=('VALOR_RECEBER', 'sum')
        ).reset_index()
        buf_prest = _chart_lencol_prestador_valor(df_prest2)

        img_emp = _imagem_de_buf(buf_emp, largura_cm=7.0)
        img_prest = _imagem_de_buf(buf_prest, largura_cm=9.0)
        t_imgs = Table([[img_emp, img_prest]],
                       colWidths=[7.5*cm, (PAGE_W - 2*MARGIN - 7.5*cm)])
        t_imgs.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(t_imgs)
    story.append(PageBreak())

    # ── Página 4: Categorias ─────────────────────────────────────────────────
    story.append(Paragraph('Análise por Categoria', e['titulo_secao']))
    story.append(_linha_divisoria())

    cat_col = 'CAT_BASE' if 'CAT_BASE' in df.columns else 'CATEGORIA'
    if cat_col in df.columns:
        df_cat = (df.groupby(cat_col)['QUANT'].sum()
                  .reset_index().sort_values('QUANT', ascending=False))
        df_cat['%'] = (df_cat['QUANT'] / df_cat['QUANT'].sum() * 100).round(1)

        buf_cat = _chart_barras_h(df_cat, cat_col, 'QUANT', 'Peças por Categoria', top_n=12)
        story.append(_imagem_de_buf(buf_cat, largura_cm=14))
        story.append(Spacer(1, 0.4*cm))

        cabec_cat = ['Categoria', 'Peças', '% Total', 'Valor (R$)']
        if 'VALOR_RECEBER' in df.columns:
            df_cat_v = df.groupby(cat_col).agg(
                QUANT=('QUANT', 'sum'), VALOR=('VALOR_RECEBER', 'sum')
            ).reset_index().sort_values('QUANT', ascending=False)
            df_cat_v['%'] = (df_cat_v['QUANT'] / df_cat_v['QUANT'].sum() * 100).round(1)
            linhas_cat = [
                [str(row[cat_col])[:30], _fmt(row['QUANT']),
                 f"{row['%']:.1f}%", f"R$ {_fmt(row['VALOR'], 2)}"]
                for _, row in df_cat_v.iterrows()
            ]
        else:
            linhas_cat = [
                [str(row[cat_col])[:30], _fmt(row['QUANT']), f"{row['%']:.1f}%", '—']
                for _, row in df_cat.iterrows()
            ]
        cw_cat = [5.0*cm, 2.5*cm, 2.0*cm, 3.5*cm]
        story.append(_tabela_generica(cabec_cat, linhas_cat, e, cw_cat))
    story.append(PageBreak())

    # ── Página 5: OPs ────────────────────────────────────────────────────────
    story.append(Paragraph('Análise por Ordem de Produção (OP)', e['titulo_secao']))
    story.append(_linha_divisoria())

    if 'OP' in df.columns:
        agg_d = {'Peças': ('QUANT', 'sum'), 'Dias': ('DATA', 'nunique')}
        if 'VALOR_RECEBER' in df.columns: agg_d['Valor'] = ('VALOR_RECEBER', 'sum')
        if 'PRESTADOR' in df.columns: agg_d['Prestadores'] = ('PRESTADOR', 'nunique')
        if 'EMPRESA' in df.columns: agg_d['Empresa'] = ('EMPRESA', 'first')
        resumo_op = df.groupby('OP').agg(**agg_d).reset_index().sort_values('Peças', ascending=False)

        cabec_op = ['OP', 'Peças']
        if 'Valor' in resumo_op.columns: cabec_op.append('Valor (R$)')
        if 'Empresa' in resumo_op.columns: cabec_op.append('Empresa')
        if 'Prestadores' in resumo_op.columns: cabec_op.append('Prestadores')
        cabec_op.append('Dias')

        linhas_op = []
        for row in resumo_op.itertuples():
            linha = [str(row.OP), _fmt(row.Peças)]
            if 'Valor' in resumo_op.columns: linha.append(f"R$ {_fmt(row.Valor, 2)}")
            if 'Empresa' in resumo_op.columns: linha.append(str(row.Empresa)[:20])
            if 'Prestadores' in resumo_op.columns: linha.append(str(row.Prestadores))
            linha.append(str(row.Dias))
            linhas_op.append(linha)

        n_extra_cols = len(cabec_op) - 3
        base_w = PAGE_W - 2 * MARGIN
        cw_op = [2.5*cm, 2.5*cm]
        if 'Valor (R$)' in cabec_op: cw_op.append(3.0*cm)
        if 'Empresa' in cabec_op: cw_op.append(3.5*cm)
        if 'Prestadores' in cabec_op: cw_op.append(2.0*cm)
        cw_op.append(1.5*cm)

        story.append(_tabela_generica(cabec_op, linhas_op[:60], e, cw_op))
        if len(linhas_op) > 60:
            story.append(Paragraph(f'... e mais {len(linhas_op) - 60} OPs.', e['nota']))
    story.append(PageBreak())

    # ── Conclusão ────────────────────────────────────────────────────────────
    story.append(Paragraph('Conclusão do Período', e['titulo_secao']))
    story.append(_linha_divisoria())

    is_pago = fim < date.today()
    status_fin = 'PAGO' if is_pago else 'A PAGAR'
    _pecas_txt = (
        f'<b>{_fmt(total_sem_fundo)} peças (exceto fundos)</b> '
        f'+ <b>{_fmt(total_fundos)} fundos de jogo</b>'
        if total_fundos > 0 else f'<b>{_fmt(total_pecas)} peças cortadas</b>'
    )
    conclusao_html = (
        f'No período de <b>{ini.strftime("%d/%m/%Y")}</b> a <b>{fim.strftime("%d/%m/%Y")}</b>, '
        f'o setor de Corte de Lençol registrou {_pecas_txt} '
        f'por <b>{n_prest} prestador(es)</b> de <b>{n_emp} empresa(s)</b>, '
        f'ao longo de <b>{dias_trab} dias trabalhados</b>. '
        f'A média diária foi de <b>{_fmt(media_diaria, 0)} peças/dia</b>. '
        f'Valor total ({status_fin}): <b>R$ {_fmt(total_valor, 2)}</b>, '
        f'com ticket médio de <b>R$ {_fmt(ticket_medio, 4)}/peça</b>.'
    )
    story.append(Paragraph(conclusao_html, e['corpo']))
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Arealva · Lençol  ·  {gerado_em}',
        ParagraphStyle('ass_ln', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()


# ─── Utilidade: nome de arquivo padrão ───────────────────────────────────────

def nome_arquivo_pdf(dashboard: str, ini: date, fim: date) -> str:
    """Gera nome de arquivo sugerido para o PDF."""
    slug = dashboard.lower().replace(' ', '_').replace('/', '_')
    return f"relatorio_{slug}_{ini.strftime('%Y%m%d')}_{fim.strftime('%Y%m%d')}.pdf"


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — PRODUÇÃO GERAL (Por Cliente)
# ═══════════════════════════════════════════════════════════════════════════════

def _chart_empresas_comparativo(filtered_data: dict, cor_map: dict = None) -> io.BytesIO:
    """Gráfico de barras horizontal comparando empresas."""
    emps = []
    totais = []
    for emp, df in sorted(filtered_data.items(), key=lambda x: x[1]['Quantidade'].sum()):
        emps.append(emp)
        totais.append(int(df['Quantidade'].sum()))

    paleta_emp = ['#2AA89A', '#D4860A', '#1E8449', '#CB4335', '#5D6D7E',
                  '#AED6F1', '#7FB3D3', '#F0B27A', '#82E0AA', '#F1948A']
    n = len(emps)
    fig, ax = plt.subplots(figsize=(10, max(3.5, n * 0.55)))
    fig.patch.set_facecolor(MP_BG)
    ax.set_facecolor(MP_BG)

    cores = [paleta_emp[i % len(paleta_emp)] for i in range(n)]
    bars = ax.barh(range(n), totais, color=cores, alpha=0.85, height=0.6)
    ax.set_yticks(range(n))
    ax.set_yticklabels(emps, fontsize=8.5, color=MP_TEXT)
    max_v = max(totais) if totais else 1
    for bar, v in zip(bars, totais):
        ax.text(v + max_v * 0.01, bar.get_y() + bar.get_height() / 2.,
                _fmt(v), va='center', fontsize=8, color=MP_TEXT, fontweight='bold')

    ax.set_title('Produção Total por Empresa no Período', fontsize=12, fontweight='bold', color=MP_TEXT, pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt(x)))
    ax.tick_params(colors=MP_TEXT, labelsize=8)
    ax.grid(axis='x', color=MP_GRID, linewidth=0.7, alpha=0.8)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(MP_GRID); ax.spines['bottom'].set_color(MP_GRID)
    ax.set_xlim(right=max_v * 1.15)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_producao_mensal_empresas(all_dfs: list[tuple], meses_pt: dict) -> io.BytesIO:
    """Gráfico de linha — evolução mensal por empresa."""
    paleta_emp = ['#2AA89A', '#D4860A', '#1E8449', '#CB4335', '#5D6D7E',
                  '#AED6F1', '#7FB3D3', '#F0B27A', '#82E0AA', '#F1948A']
    fig, ax = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor(MP_BG)
    ax.set_facecolor(MP_BG)

    for idx, (emp, df) in enumerate(all_dfs):
        mensal = (df.groupby(['Ano', 'Mes'])['Quantidade'].sum()
                  .reset_index().sort_values(['Ano', 'Mes']))
        if mensal.empty:
            continue
        mensal['AnoMes'] = mensal.apply(
            lambda r: f"{meses_pt.get(int(r['Mes']), str(r['Mes']))[:3]}/{int(r['Ano'])}", axis=1
        )
        cor = paleta_emp[idx % len(paleta_emp)]
        ax.plot(range(len(mensal)), mensal['Quantidade'],
                marker='o', markersize=5, linewidth=2,
                color=cor, label=emp[:25], alpha=0.9)
        ax.set_xticks(range(len(mensal)))
        ax.set_xticklabels(mensal['AnoMes'].tolist(), rotation=45, ha='right', fontsize=7.5)

    ax.set_title('Evolução Mensal por Empresa', fontsize=12, fontweight='bold', color=MP_TEXT, pad=10)
    ax.set_ylabel('Peças', fontsize=9, color=MP_TEXT)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt(x)))
    ax.grid(color=MP_GRID, linewidth=0.7, alpha=0.8)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(MP_GRID); ax.spines['bottom'].set_color(MP_GRID)
    ax.tick_params(colors=MP_TEXT, labelsize=7.5)
    leg = ax.legend(fontsize=8, framealpha=0.9, edgecolor=MP_GRID, loc='upper left')
    for t in leg.get_texts(): t.set_color(MP_TEXT)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def gerar_pdf_producao_geral(
    filtered_data: dict,
    ini: date,
    fim: date,
    filtros_texto: str = '',
) -> bytes:
    """
    Gera o relatório PDF de fechamento da Produção Geral (por cliente).

    Parameters
    ----------
    filtered_data : dict {empresa: DataFrame com Data, Quantidade, Faccao, Produto,
                          Meta Diaria, Ano, Mes, DiaSemana}
    ini / fim     : período selecionado
    filtros_texto : descrição textual dos filtros ativos (anos, meses, etc.)
    """
    e = _estilos()
    periodo_str = f"{ini.strftime('%d/%m/%Y')}  até  {fim.strftime('%d/%m/%Y')}"
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='🏭  Relatório de Produção Geral',
        subtitulo_rel='Controle de Produção — Todas as Empresas',
        periodo=periodo_str,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = []
    story.append(PageBreak())  # capa

    # Métricas globais
    total_geral = sum(df['Quantidade'].sum() for df in filtered_data.values())
    n_empresas = len(filtered_data)
    dias_total = max(
        (df[df['Quantidade'] > 0]['Data'].nunique() for df in filtered_data.values()),
        default=0
    )

    # ── Resumo Executivo ─────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    media_geral = total_geral / dias_total if dias_total else 0
    top_emp = max(filtered_data.items(), key=lambda x: x[1]['Quantidade'].sum())[0] if filtered_data else '—'

    kpis = [
        {'label': '🏭 Empresas Ativas', 'valor': str(n_empresas), 'cor': C_TEAL_LT},
        {'label': '📦 Produção Total', 'valor': _fmt(total_geral), 'cor': C_TEAL_LT},
        {'label': '📆 Dias com Dados', 'valor': str(dias_total), 'cor': C_GRAY_BG},
        {'label': '⚡ Média Diária Geral', 'valor': _fmt(media_geral), 'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=4))
    story.append(Spacer(1, 0.5*cm))

    # ── Tabela resumo por empresa ────────────────────────────────────────────
    story.append(Paragraph('Desempenho por Empresa', e['subtitulo_secao']))

    resumo_rows = []
    for emp, df in filtered_data.items():
        total_e = int(df['Quantidade'].sum())
        dias_e = df[df['Quantidade'] > 0]['Data'].nunique()
        media_e = total_e / dias_e if dias_e > 0 else 0
        pct_total = total_e / total_geral * 100 if total_geral > 0 else 0
        n_facc = df['Faccao'].nunique() if 'Faccao' in df.columns else 0
        n_prod = df['Produto'].nunique() if 'Produto' in df.columns else 0

        # Meta (se disponível)
        meta_col = 'Meta Diaria' if 'Meta Diaria' in df.columns else None
        meta_e = 0
        if meta_col:
            meta_vals = df[meta_col].dropna()
            if not meta_vals.empty:
                meta_e = meta_vals.mean()
        pct_meta = (media_e / meta_e * 100) if meta_e > 0 else 0

        resumo_rows.append({
            'Empresa': emp,
            'total': total_e,
            'dias': dias_e,
            'media': media_e,
            'pct_total': pct_total,
            'n_facc': n_facc,
            'n_prod': n_prod,
            'meta_e': meta_e,
            'pct_meta': pct_meta,
        })

    resumo_rows.sort(key=lambda x: x['total'], reverse=True)

    cabec_res = ['Empresa', 'Total Peças', '% Geral', 'Dias', 'Média/Dia', 'Meta/Dia', '% Meta', 'Facções']
    linhas_res = []
    for r in resumo_rows:
        linhas_res.append([
            r['Empresa'][:28],
            _fmt(r['total']),
            f"{r['pct_total']:.1f}%",
            str(r['dias']),
            _fmt(r['media']),
            _fmt(r['meta_e']) if r['meta_e'] > 0 else '—',
            f"{r['pct_meta']:.1f}%" if r['meta_e'] > 0 else '—',
            str(r['n_facc']),
        ])

    cw_res = [3.5*cm, 2.3*cm, 1.8*cm, 1.3*cm, 2.0*cm, 2.0*cm, 1.8*cm, 1.8*cm]
    t_res = _tabela_generica(cabec_res, linhas_res, e, cw_res)
    # Colorir % Meta
    for ri, row in enumerate(resumo_rows, start=1):
        if row['meta_e'] > 0:
            cor_s = C_GREEN if row['pct_meta'] >= 100 else (C_AMBER if row['pct_meta'] >= 80 else C_RED)
            t_res.setStyle(TableStyle([
                ('TEXTCOLOR', (6, ri), (6, ri), cor_s),
                ('FONTNAME', (6, ri), (6, ri), 'Helvetica-Bold'),
            ]))
    story.append(t_res)
    story.append(PageBreak())

    # ── Página 3: Gráfico comparativo ───────────────────────────────────────
    story.append(Paragraph('Análise Comparativa', e['titulo_secao']))
    story.append(_linha_divisoria())

    buf_emp_chart = _chart_empresas_comparativo(filtered_data)
    story.append(_imagem_de_buf(buf_emp_chart, largura_cm=16.5))
    story.append(Spacer(1, 0.5*cm))

    # Gráfico de evolução mensal
    MESES_NOME_PT = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                     7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    try:
        buf_mensal = _chart_producao_mensal_empresas(
            list(filtered_data.items()), MESES_NOME_PT
        )
        story.append(_imagem_de_buf(buf_mensal, largura_cm=16.5))
    except Exception as ex_m:
        logger.warning(f"Chart mensal: {ex_m}")
    story.append(PageBreak())

    # ── Páginas por empresa ──────────────────────────────────────────────────
    for emp, df_emp in filtered_data.items():
        story.append(Paragraph(f'Empresa: {emp}', e['titulo_secao']))
        story.append(_linha_divisoria(cor=C_TEAL))

        total_e = int(df_emp['Quantidade'].sum())
        dias_e = df_emp[df_emp['Quantidade'] > 0]['Data'].nunique()
        media_e = total_e / dias_e if dias_e > 0 else 0

        meta_col = 'Meta Diaria' if 'Meta Diaria' in df_emp.columns else None
        meta_e = 0
        if meta_col:
            meta_vals = df_emp[meta_col].dropna()
            if not meta_vals.empty:
                meta_e = float(meta_vals.mean())
        meta_periodo_e = meta_e * dias_e if meta_e > 0 else 0
        pct_e = (media_e / meta_e * 100) if meta_e > 0 else 0
        saldo_e = total_e - meta_periodo_e if meta_periodo_e > 0 else 0

        kpis_e = [
            {'label': '📦 Total', 'valor': _fmt(total_e), 'cor': C_TEAL_LT},
            {'label': '📆 Dias', 'valor': str(dias_e), 'cor': C_GRAY_BG},
            {'label': '⚡ Média/Dia', 'valor': _fmt(media_e), 'cor': _pct_bg(pct_e) if meta_e > 0 else C_GRAY_BG},
            {'label': '🎯 % Meta', 'valor': f'{pct_e:.1f}%' if meta_e > 0 else '—', 'cor': _pct_bg(pct_e) if meta_e > 0 else C_GRAY_BG},
        ]
        story.append(_bloco_kpis(kpis_e, e, colunas=4))
        story.append(Spacer(1, 0.3*cm))

        if meta_e > 0:
            saldo_html = (
                f'Meta período: <b>{_fmt(meta_periodo_e)}</b>  |  '
                f'Saldo: <b>{saldo_e:+,.0f}</b>'.replace(',', '.')
            )
            story.append(Paragraph(saldo_html, e['corpo']))
            story.append(Spacer(1, 0.2*cm))

        # Gráfico diário desta empresa
        try:
            prod_dia_e = df_emp.groupby('Data')['Quantidade'].sum().reset_index().sort_values('Data')
            prod_dia_e.columns = ['DATA', 'QUANTIDADE']
            buf_e = _chart_producao_diaria(
                prod_dia_e, meta_e,
                titulo=f'Produção Diária — {emp}',
                largura=13.0, altura=4.0,
            )
            story.append(_imagem_de_buf(buf_e, largura_cm=14.5))
        except Exception as ex_e:
            logger.warning(f"Chart {emp}: {ex_e}")

        # Tabela por facção/produto (se disponível)
        if 'Faccao' in df_emp.columns and 'Produto' in df_emp.columns:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph('Produção por Facção / Produto', e['subtitulo_secao']))
            tbl_fp = (
                df_emp.groupby(['Faccao', 'Produto'])['Quantidade']
                .sum().reset_index().sort_values('Quantidade', ascending=False)
            )
            tbl_fp['%'] = (tbl_fp['Quantidade'] / tbl_fp['Quantidade'].sum() * 100).round(1)
            cabec_fp = ['Facção', 'Produto', 'Peças', '% Total']
            linhas_fp = [
                [str(row['Faccao'])[:25], str(row['Produto'])[:30],
                 _fmt(row['Quantidade']), f"{row['%']:.1f}%"]
                for _, row in tbl_fp.head(20).iterrows()
            ]
            cw_fp = [3.5*cm, 6.0*cm, 2.5*cm, 2.0*cm]
            story.append(_tabela_generica(cabec_fp, linhas_fp, e, cw_fp))

        story.append(PageBreak())

    # ── Conclusão ────────────────────────────────────────────────────────────
    story.append(Paragraph('Conclusão do Período', e['titulo_secao']))
    story.append(_linha_divisoria())

    conclusao_html = (
        f'No período de <b>{ini.strftime("%d/%m/%Y")}</b> a <b>{fim.strftime("%d/%m/%Y")}</b>, '
        f'<b>{n_empresas} empresa(s)</b> registraram uma produção total de '
        f'<b>{_fmt(total_geral)} peças</b> ao longo de <b>{dias_total} dias com registros</b>, '
        f'com média geral de <b>{_fmt(media_geral)} peças/dia</b>. '
        f'Empresa líder: <b>{top_emp}</b>.'
    )
    story.append(Paragraph(conclusao_html, e['corpo']))
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Produção Geral  ·  {gerado_em}',
        ParagraphStyle('ass_pg', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()
