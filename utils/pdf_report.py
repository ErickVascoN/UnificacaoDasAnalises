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
    estilos['destaque'] = ParagraphStyle(
        'destaque', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=colors.HexColor('#1A5276'), spaceAfter=4,
        leftIndent=8, borderPad=4,
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
            largura=17.0, altura=6.5,
        )
        story.append(_imagem_de_buf(buf_chart, largura_cm=17.0))
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
        # Pizza centralizada
        img_pizza = _imagem_de_buf(buf_pizza, largura_cm=11.0)
        t_centro_p = Table([[img_pizza]], colWidths=[PAGE_W - 2 * MARGIN])
        t_centro_p.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE')]))
        story.append(t_centro_p)
        story.append(Spacer(1, 0.5 * cm))

        # Top cores em largura total
        story.append(_imagem_de_buf(buf_cores, largura_cm=17.0))
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
        titulo_rel='✂  Relatório de Corte · Iacanga Manta',
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
            titulo=f'Produção Diária — Iacanga Manta  |  Meta: {_fmt(meta_total)} pç/dia',
            largura=17.0, altura=6.5,
        )
        story.append(_imagem_de_buf(buf_chart, largura_cm=17.0))
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
            story.append(_imagem_de_buf(buf_tam, largura_cm=17.0))
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

    # Jogos duplos somente das OPs que tiveram fundo (= universo do caseamento)
    _jogo_em_op_fundo_pdf = (int(caseamento_df['JOGO'].sum())
                             if caseamento_df is not None and not caseamento_df.empty else 0)
    # Diferença: jogos duplos de OPs SEM fundo no período (ficam fora do caseamento)
    _jogos_sem_par_pdf = max(0, total_sem_fundo - _jogo_em_op_fundo_pdf)

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
        {'label': _label_pecas,             'valor': _fmt(total_sem_fundo),            'cor': C_TEAL_LT},
        {'label': '🧩 Jogos Duplos (c/ fundo)', 'valor': _fmt(_jogo_em_op_fundo_pdf),  'cor': C_TEAL_LT},
        {'label': '🔄 Fundos de Jogo',      'valor': _fmt(total_fundos),               'cor': C_AMBER_LT},
        {'label': '💰 Total a Pagar/Pago',  'valor': f'R$ {_fmt(total_valor, 2)}',     'cor': C_GREEN_LT},
        {'label': '📆 Dias Trabalhados',    'valor': str(dias_trab),                   'cor': C_GRAY_BG},
        {'label': '📈 Média Diária',        'valor': f'{_fmt(media_diaria, 0)} pç/dia','cor': C_GRAY_BG},
        {'label': '👷 Prestadores',         'valor': str(n_prest),                     'cor': C_GRAY_BG},
        {'label': '🏭 Empresas',            'valor': str(n_emp),                       'cor': C_GRAY_BG},
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
            f'<i>Observação: este caseamento cobre apenas as OPs que tiveram corte de fundo '
            f'({_fmt(_jogo_tot)} jogos duplos). OPs em que só o jogo foi cortado no período '
            f'ficam fora para evitar falsos alarmes.</i>',
            e['nota'],
        ))
        if _jogos_sem_par_pdf > 0:
            story.append(Spacer(1, 0.15*cm))
            story.append(Paragraph(
                f'<b>ℹ  {_fmt(_jogos_sem_par_pdf)} peças fora do caseamento</b> — são jogos '
                f'duplos de OPs que <b>não tiveram corte de fundo neste período</b>. O fundo '
                f'dessas OPs pode ter sido cortado em outro período ou ainda não foi realizado.',
                e['destaque'] if 'destaque' in e else e['corpo'],
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

    # ── Página 3: Produção Diária ────────────────────────────────────────────
    story.append(Paragraph('Análise Visual — Produção Diária', e['titulo_secao']))
    story.append(_linha_divisoria())

    if 'QUANT' in df.columns:
        prod_dia = df.groupby('DATA')['QUANT'].sum().reset_index().sort_values('DATA')
        prod_dia.columns = ['DATA', 'QUANTIDADE']
        buf_dia = _chart_producao_diaria(
            prod_dia, 0,
            titulo='Produção Diária — Lençol',
            largura=17.0, altura=6.5,
        )
        story.append(_imagem_de_buf(buf_dia, largura_cm=17.0))
    story.append(PageBreak())

    # ── Página 4: Distribuição — Prestadores e Empresas ──────────────────────
    story.append(Paragraph('Análise Visual — Prestadores e Empresas', e['titulo_secao']))
    story.append(_linha_divisoria())

    if 'EMPRESA' in df.columns and 'PRESTADOR' in df.columns:
        # Gráfico prestadores (largura total)
        df_prest2 = df.groupby('PRESTADOR').agg(
            Peças=('QUANT', 'sum'), Valor=('VALOR_RECEBER', 'sum')
        ).reset_index()
        buf_prest = _chart_lencol_prestador_valor(df_prest2)
        story.append(_imagem_de_buf(buf_prest, largura_cm=17.0))
        story.append(Spacer(1, 0.6 * cm))

        # Pizza de empresas (centralizada, tamanho generoso)
        dist_emp = df.groupby('EMPRESA')['QUANT'].sum().reset_index()
        buf_emp = _chart_pizza_estacao(dist_emp, 'EMPRESA', 'QUANT', 'Distribuição por Empresa')
        img_emp = _imagem_de_buf(buf_emp, largura_cm=11.0)
        t_centro = Table([[img_emp]], colWidths=[PAGE_W - 2 * MARGIN])
        t_centro.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                      ('VALIGN', (0, 0), (0, 0), 'MIDDLE')]))
        story.append(t_centro)
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
        story.append(_imagem_de_buf(buf_cat, largura_cm=17.0))
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

    # ── Nota sobre Niazittex ─────────────────────────────────────────────────
    _obs_style = ParagraphStyle(
        'obs_titulo', parent=e['corpo'],
        fontName='Helvetica-Bold', fontSize=9,
        textColor=C_AMBER, spaceAfter=3,
    )
    _obs_body_style = ParagraphStyle(
        'obs_body', parent=e['corpo'],
        fontName='Helvetica', fontSize=8.5,
        textColor=C_BLACK, leading=13,
    )
    _obs_content = Table(
        [[
            Paragraph('⚠  Observação', _obs_style),
        ],[
            Paragraph(
                'A <b>Niazittex</b> não estava preenchendo os dados de produção na planilha '
                'do sistema durante o período coberto por este relatório. '
                'A aba correspondente está sendo ajustada para que o acompanhamento '
                'passe a ser registrado corretamente a partir de agora. '
                'Produção registrada manualmente no período:<br/>'
                '&nbsp;&nbsp;• <b>Toque de Seda</b> — 7.242 peças<br/>'
                '&nbsp;&nbsp;• <b>Lençol QE — 180 Fios Elástico</b> — 144 peças<br/>'
                '&nbsp;&nbsp;• <b>Lençol QE — 180 Fios Elástico (2ª Qualidade)</b> — 12 peças<br/>'
                '&nbsp;&nbsp;• <b>Fronha — 300 Fios Avulsa Lisa</b> — 1.190 peças',
                _obs_body_style,
            ),
        ]],
        colWidths=[PAGE_W - 2 * MARGIN],
    )
    _obs_content.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_AMBER_LT),
        ('BOX', (0, 0), (-1, -1), 1.2, C_AMBER),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 8),
    ]))
    story.append(_obs_content)
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

        # Meta/Dia = soma das metas apenas dos pares (Facção, Produto) com produção real.
        # Ignora facções/produtos sem Quantidade > 0 para não inflar a meta.
        meta_col = 'Meta Diaria' if 'Meta Diaria' in df.columns else None
        meta_e = 0.0
        if meta_col:
            _grp_m = [c for c in ['Faccao', 'Produto'] if c in df.columns]
            _pares_ativos = (
                df[df['Quantidade'].fillna(0) > 0][_grp_m].drop_duplicates()
                if _grp_m else None
            )
            _sub_m = df[df[meta_col].fillna(0) > 0]
            if _pares_ativos is not None and not _pares_ativos.empty:
                _sub_m = _sub_m.merge(_pares_ativos, on=_grp_m, how='inner')
            if not _sub_m.empty:
                meta_e = float(
                    _sub_m.groupby(_grp_m)[meta_col].mean().sum()
                    if _grp_m else _sub_m[meta_col].mean()
                )
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
        meta_e = 0.0
        if meta_col:
            _grp_e = [c for c in ['Faccao', 'Produto'] if c in df_emp.columns]
            _pares_ativos_e = (
                df_emp[df_emp['Quantidade'].fillna(0) > 0][_grp_e].drop_duplicates()
                if _grp_e else None
            )
            _sub_e = df_emp[df_emp[meta_col].fillna(0) > 0]
            if _pares_ativos_e is not None and not _pares_ativos_e.empty:
                _sub_e = _sub_e.merge(_pares_ativos_e, on=_grp_e, how='inner')
            if not _sub_e.empty:
                meta_e = float(
                    _sub_e.groupby(_grp_e)[meta_col].mean().sum()
                    if _grp_e else _sub_e[meta_col].mean()
                )
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

            _tem_meta = 'Meta Diaria' in df_emp.columns
            _agg = {'Quantidade': 'sum'}
            if _tem_meta:
                _agg['Meta Diaria'] = 'first'
            tbl_fp = (
                df_emp.groupby(['Faccao', 'Produto'])
                .agg(_agg).reset_index().sort_values('Quantidade', ascending=False)
            )
            tbl_fp = tbl_fp[tbl_fp['Quantidade'] > 0]
            tbl_fp['%'] = (tbl_fp['Quantidade'] / tbl_fp['Quantidade'].sum() * 100).round(1)

            if _tem_meta:
                from datetime import timedelta as _td_fp
                _wdays_fp = sum(
                    1 for _di in range((fim - ini).days + 1)
                    if (ini + _td_fp(days=_di)).weekday() < 5
                )
                _meta_num = pd.to_numeric(tbl_fp['Meta Diaria'], errors='coerce').fillna(0)
                tbl_fp['Meta Periodo'] = _meta_num * _wdays_fp
                tbl_fp['Media Dia'] = tbl_fp['Quantidade'] / max(_wdays_fp, 1)

                cabec_fp = ['Facção', 'Produto', 'Peças', '% Total',
                            'Média/Dia', 'Meta/Dia', 'Meta Período', '% Ating.']
                linhas_fp = []
                for _, row in tbl_fp.head(20).iterrows():
                    meta_d = float(_meta_num[row.name]) if pd.notna(row['Meta Diaria']) else 0
                    meta_p = float(row['Meta Periodo'])
                    media_d = float(row['Media Dia'])
                    pct_a = (row['Quantidade'] / meta_p * 100) if meta_p > 0 else None
                    linhas_fp.append([
                        str(row['Faccao'])[:25], str(row['Produto'])[:25],
                        _fmt(row['Quantidade']), f"{row['%']:.1f}%",
                        _fmt(media_d),
                        _fmt(meta_d) if meta_d > 0 else '—',
                        _fmt(meta_p) if meta_p > 0 else '—',
                        f"{pct_a:.1f}%" if pct_a is not None else '—',
                    ])
                cw_fp = [2.8*cm, 4.0*cm, 1.8*cm, 1.4*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.8*cm]
                t_fp = _tabela_generica(cabec_fp, linhas_fp, e, cw_fp)
                for ri, linha in enumerate(linhas_fp, start=1):
                    try:
                        pct_val = float(linha[7].replace('%', '').replace(',', '.'))
                        cor_s = C_GREEN if pct_val >= 100 else (C_AMBER if pct_val >= 80 else C_RED)
                        t_fp.setStyle(TableStyle([
                            ('TEXTCOLOR', (7, ri), (7, ri), cor_s),
                            ('FONTNAME', (7, ri), (7, ri), 'Helvetica-Bold'),
                        ]))
                    except Exception:
                        pass
            else:
                cabec_fp = ['Facção', 'Produto', 'Peças', '% Total']
                linhas_fp = [
                    [str(row['Faccao'])[:25], str(row['Produto'])[:30],
                     _fmt(row['Quantidade']), f"{row['%']:.1f}%"]
                    for _, row in tbl_fp.head(20).iterrows()
                ]
                cw_fp = [3.5*cm, 6.0*cm, 2.5*cm, 2.0*cm]
                t_fp = _tabela_generica(cabec_fp, linhas_fp, e, cw_fp)

            story.append(t_fp)

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


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — PREVISÃO DE CARGAS
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════

def _chart_cargas_mensal(df_mes: pd.DataFrame) -> io.BytesIO:
    """Barras agrupadas Previsão vs Realizado por mês + linha Aderência %."""
    meses = df_mes['MES'].str[:3].tolist()
    prev  = df_mes['PREVISAO'].tolist()
    real  = df_mes['REALIZADO'].tolist()
    adh   = df_mes['ADERENCIA'].tolist()
    n     = len(meses)
    x     = np.arange(n)
    w     = 0.35

    fig, ax1 = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(MP_BG)
    ax1.set_facecolor(MP_BG)

    bars_p = ax1.bar(x - w / 2, prev, w, label='Previsão',  color='#2AA89A', alpha=0.85)
    bars_r = ax1.bar(x + w / 2, real, w, label='Realizado', color='#45B7D1', alpha=0.85)

    ax2 = ax1.twinx()
    ax2.plot(x, adh, color=MP_META, linewidth=2.5, marker='o', markersize=7,
             label='Aderência %', zorder=5)
    ax2.axhline(100, color=MP_META, linestyle='--', linewidth=1.2, alpha=0.5)
    for xi, v in zip(x, adh):
        if v > 0:
            ax2.text(xi, v + 4, f"{v:.0f}%", ha='center', fontsize=7.5,
                     color=MP_META, fontweight='bold')

    max_v = max(max(prev, default=1), max(real, default=1))
    for bar, v in zip(bars_p, prev):
        if v > 0:
            ax1.text(bar.get_x() + bar.get_width() / 2., v + max_v * 0.01,
                     f"R$ {_fmt(int(v / 1000))}k", ha='center', va='bottom',
                     fontsize=6, color=MP_TEXT, fontweight='bold')
    for bar, v in zip(bars_r, real):
        if v > 0:
            ax1.text(bar.get_x() + bar.get_width() / 2., v + max_v * 0.01,
                     f"R$ {_fmt(int(v / 1000))}k", ha='center', va='bottom',
                     fontsize=6, color=MP_TEXT, fontweight='bold')

    ax1.set_xticks(x)
    ax1.set_xticklabels(meses, fontsize=9, color=MP_TEXT)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"R$ {_fmt(int(v / 1000))}k"))
    ax1.tick_params(colors=MP_TEXT)
    ax1.set_ylabel('Valor (R$)', color=MP_TEXT, fontsize=9)
    ax1.set_title('Previsão vs. Realizado por Mês', fontsize=12, fontweight='bold',
                  color=MP_TEXT, pad=10)
    ax1.grid(axis='y', color=MP_GRID, linewidth=0.7, alpha=0.8)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color(MP_GRID)
    ax1.spines['bottom'].set_color(MP_GRID)

    ax2.set_ylabel('Aderência %', color=MP_META, fontsize=9)
    ax2.set_ylim(0, 160)
    ax2.tick_params(colors=MP_META)
    ax2.spines['right'].set_color(MP_META)

    lines1, labs1 = ax1.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labs1 + labs2, fontsize=8, framealpha=0.9,
               loc='upper left', edgecolor=MP_GRID)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_cargas_destino(df_cargos: pd.DataFrame) -> io.BytesIO:
    """Barras horizontais: top destinos por previsão."""
    df_d = (
        df_cargos[df_cargos['PREVISAO'] > 0]
        .groupby('DESTINO_NORM')['PREVISAO'].sum()
        .reset_index()
        .sort_values('PREVISAO')
        .tail(12)
    )
    n = len(df_d)
    fig, ax = plt.subplots(figsize=(8, max(3.5, n * 0.4)))
    fig.patch.set_facecolor(MP_BG)
    ax.set_facecolor(MP_BG)

    bars = ax.barh(range(n), df_d['PREVISAO'], color='#2AA89A', alpha=0.85, height=0.65)
    ax.set_yticks(range(n))
    ax.set_yticklabels(df_d['DESTINO_NORM'].tolist(), fontsize=7.5, color=MP_TEXT)
    max_v = df_d['PREVISAO'].max() if not df_d.empty else 1
    for bar, v in zip(bars, df_d['PREVISAO']):
        ax.text(v + max_v * 0.01, bar.get_y() + bar.get_height() / 2.,
                f"R$ {_fmt(int(v / 1000))}k", va='center', fontsize=7,
                color=MP_TEXT, fontweight='bold')
    ax.set_title('Previsão de Faturamento por Destino', fontsize=11, fontweight='bold',
                 color=MP_TEXT, pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"R$ {_fmt(int(v / 1000))}k"))
    ax.tick_params(colors=MP_TEXT, labelsize=7.5)
    ax.grid(axis='x', color=MP_GRID, linewidth=0.7, alpha=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(MP_GRID)
    ax.spines['bottom'].set_color(MP_GRID)
    ax.set_xlim(right=max_v * 1.18)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def gerar_pdf_previsao_cargas(
    df_cargos: pd.DataFrame,
    df_realizados: pd.DataFrame,
    df_mes: pd.DataFrame,
    total_prev: float,
    total_real: float,
    diferenca_g: float,
    aderencia_g: float,
    n_canceladas: int,
    n_adiadas: int,
    n_clientes: int,
    sel_meses: list,
) -> bytes:
    """
    Gera o relatório PDF de Previsão de Cargas.

    Parameters
    ----------
    df_cargos     : registros de carga (STATUS != CARGO_REAL), já filtrados
    df_realizados : registros CARGO_REAL por mês
    df_mes        : resumo mensal (MES, MES_NUM, PREVISAO, REALIZADO, ADERENCIA, DIFERENCA)
    total_prev    : previsão total global
    total_real    : realizado total global
    diferenca_g   : realizado - previsão
    aderencia_g   : aderência % (só meses com realizado > 0)
    n_canceladas  : qtd. canceladas
    n_adiadas     : qtd. adiadas
    n_clientes    : destinos únicos
    sel_meses     : lista de meses selecionados
    """
    def _r(v: float) -> str:
        return f"R$ {_fmt(int(v))}"

    e = _estilos()
    meses_str   = ', '.join(sel_meses) if sel_meses else 'Todos'
    gerado_em   = datetime.now().strftime('%d/%m/%Y  %H:%M')

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='🚛  Relatório de Previsão de Cargas',
        subtitulo_rel='Análise Logística · Previsão vs. Realizado',
        periodo=meses_str,
        gerado_em=gerado_em,
    )

    story = []
    story.append(PageBreak())  # capa

    # ── Resumo Executivo ─────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    adh_bg = C_GREEN_LT if aderencia_g >= 95 else (C_AMBER_LT if aderencia_g >= 80 else C_RED_LT)
    dif_bg = C_GREEN_LT if diferenca_g >= 0 else C_RED_LT
    ocorr  = n_canceladas + n_adiadas
    kpis = [
        {'label': '💰 Previsão Total',     'valor': _r(total_prev),        'cor': C_TEAL_LT},
        {'label': '✅ Realizado Total',    'valor': _r(total_real),         'cor': C_TEAL_LT},
        {'label': '⚖️  Diferença',         'valor': _r(abs(diferenca_g)),   'cor': dif_bg},
        {'label': '🎯 Aderência',          'valor': f'{aderencia_g:.1f}%',  'cor': adh_bg},
        {'label': '🚚 Destinos Ativos',    'valor': str(n_clientes),        'cor': C_GRAY_BG},
        {'label': '🚩 Cancel. + Adiadas', 'valor': str(ocorr),             'cor': C_RED_LT if ocorr > 0 else C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=3))
    story.append(Spacer(1, 0.6 * cm))

    # ── Tabela por mês ───────────────────────────────────────────────────────
    story.append(Paragraph('Resumo por Mês', e['subtitulo_secao']))
    cabec_mes = ['Mês', 'Previsão (R$)', 'Realizado (R$)', 'Diferença (R$)', 'Aderência %']
    linhas_mes = []
    for _, row in df_mes.iterrows():
        prev_v = float(row['PREVISAO'])
        real_v = float(row['REALIZADO'])
        dif_v  = float(row['DIFERENCA'])
        adh_v  = float(row['ADERENCIA'])
        dif_s  = ('+' if dif_v >= 0 else '') + _r(abs(dif_v))
        real_s = _r(real_v) if real_v > 0 else '—'
        dif_s  = dif_s if real_v > 0 else '—'
        adh_s  = f'{adh_v:.1f}%' if real_v > 0 else '—'
        linhas_mes.append([row['MES'], _r(prev_v), real_s, dif_s, adh_s])

    cw_mes = [3.0 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm, 3.0 * cm]
    t_mes = _tabela_generica(cabec_mes, linhas_mes, e, cw_mes)
    for ri, row in enumerate(df_mes.itertuples(), start=1):
        adh_v  = float(row.ADERENCIA)
        real_v = float(row.REALIZADO)
        if real_v > 0:
            cor_a = C_GREEN if adh_v >= 95 else (C_AMBER if adh_v >= 80 else C_RED)
            t_mes.setStyle(TableStyle([
                ('TEXTCOLOR', (4, ri), (4, ri), cor_a),
                ('FONTNAME',  (4, ri), (4, ri), 'Helvetica-Bold'),
            ]))
    story.append(t_mes)
    story.append(PageBreak())

    # ── Gráfico Previsão vs Realizado ────────────────────────────────────────
    story.append(Paragraph('Análise Gráfica', e['titulo_secao']))
    story.append(_linha_divisoria())

    try:
        buf_grafico = _chart_cargas_mensal(df_mes)
        story.append(_imagem_de_buf(buf_grafico, largura_cm=16.0))
        story.append(Spacer(1, 0.5 * cm))
    except Exception as ex_g:
        logger.warning(f'Chart cargas mensal: {ex_g}')

    try:
        buf_dest = _chart_cargas_destino(df_cargos)
        story.append(_imagem_de_buf(buf_dest, largura_cm=14.0))
    except Exception as ex_d:
        logger.warning(f'Chart cargas destino: {ex_d}')

    story.append(PageBreak())

    # ── Detalhe de Registros ─────────────────────────────────────────────────
    story.append(Paragraph('Detalhe de Registros', e['titulo_secao']))
    story.append(_linha_divisoria())

    # VALOR_FRETE nunca é zerado (PREVISAO pode ser 0 em meses com previsto oficial).
    # REALIZADO_DIA = total diário do painel direito da planilha (0 se não disponível).
    df_det = df_cargos[df_cargos['VALOR_FRETE'] > 0].copy() if not df_cargos.empty else df_cargos
    cabec_det = ['Mês', 'Data', 'Destino', 'Origem', 'Cliente', 'Previsto (R$)', 'Realizado Dia (R$)', 'Status']
    linhas_det = []
    for row in df_det.itertuples():
        data_s = pd.Timestamp(row.DATA).strftime('%d/%m/%Y') if pd.notna(row.DATA) else ''
        real_dia = float(getattr(row, 'REALIZADO_DIA', 0.0) or 0.0)
        real_s = _r(real_dia) if real_dia > 0 else '—'
        linhas_det.append([
            str(row.MES),
            data_s,
            str(row.DESTINO)[:25],
            str(row.LOCAL),
            str(row.CLIENTE)[:22],
            _r(float(row.VALOR_FRETE)),
            real_s,
            str(row.STATUS),
        ])

    cw_det = [1.6*cm, 1.9*cm, 3.3*cm, 1.6*cm, 2.8*cm, 2.4*cm, 2.4*cm, 1.4*cm]
    t_det = _tabela_generica(cabec_det, linhas_det[:200], e, cw_det)
    for ri, row in enumerate(linhas_det[:200], start=1):
        st = row[7]
        if st == 'Cancelada':
            t_det.setStyle(TableStyle([
                ('TEXTCOLOR', (7, ri), (7, ri), C_RED),
                ('FONTNAME',  (7, ri), (7, ri), 'Helvetica-Bold'),
            ]))
        elif st == 'Adiada':
            t_det.setStyle(TableStyle([
                ('TEXTCOLOR', (7, ri), (7, ri), C_AMBER),
                ('FONTNAME',  (7, ri), (7, ri), 'Helvetica-Bold'),
            ]))
    story.append(t_det)
    if len(linhas_det) > 200:
        story.append(Paragraph(f'... e mais {len(linhas_det) - 200} registros.', e['nota']))

    # ── Ocorrências (se houver) ──────────────────────────────────────────────
    df_ocorr = df_cargos[df_cargos['STATUS'].isin(['Cancelada', 'Adiada'])].copy()
    if not df_ocorr.empty:
        story.append(PageBreak())
        story.append(Paragraph('Ocorrências — Canceladas e Adiadas', e['titulo_secao']))
        story.append(_linha_divisoria(cor=C_RED))

        impacto = df_ocorr['PREVISAO'].sum()
        aviso_html = (
            f'<b>{len(df_ocorr)} ocorrência(s)</b> detectada(s) no período: '
            f'<b>{n_canceladas} cancelada(s)</b> · <b>{n_adiadas} adiada(s)</b>. '
            f'Impacto estimado na previsão: <b>{_r(impacto)}</b>.'
        )
        story.append(Paragraph(aviso_html, e['destaque']))
        story.append(Spacer(1, 0.3 * cm))

        cabec_oc = ['Mês', 'Data', 'Destino', 'Cliente', 'Previsão (R$)', 'Status', 'Obs']
        linhas_oc = []
        for row in df_ocorr.itertuples():
            data_s = pd.Timestamp(row.DATA).strftime('%d/%m/%Y') if pd.notna(row.DATA) else ''
            linhas_oc.append([
                str(row.MES), data_s, str(row.DESTINO)[:28],
                str(row.CLIENTE)[:22], _r(float(row.PREVISAO)),
                str(row.STATUS), str(row.OBS)[:30],
            ])
        cw_oc = [1.8*cm, 2.0*cm, 3.5*cm, 3.0*cm, 2.5*cm, 2.0*cm, 2.5*cm]
        t_oc = _tabela_generica(cabec_oc, linhas_oc, e, cw_oc, cor_header=C_RED)
        for ri, row in enumerate(linhas_oc, start=1):
            cor_st = C_RED if row[5] == 'Cancelada' else C_AMBER
            t_oc.setStyle(TableStyle([
                ('TEXTCOLOR', (5, ri), (5, ri), cor_st),
                ('FONTNAME',  (5, ri), (5, ri), 'Helvetica-Bold'),
            ]))
        story.append(t_oc)

    # ── Conclusão ────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('Conclusão do Período', e['titulo_secao']))
    story.append(_linha_divisoria())

    status_str = ('ADERÊNCIA ATINGIDA ✔' if aderencia_g >= 95
                  else ('PRÓXIMO DA META ⚠' if aderencia_g >= 80 else 'ABAIXO DA META ✘'))
    cor_status = C_GREEN if aderencia_g >= 95 else (C_AMBER if aderencia_g >= 80 else C_RED)

    meses_com_real = int(df_mes[df_mes['REALIZADO'] > 0].shape[0])
    conclusao_html = (
        f'No período de <b>{meses_str}</b>, a previsão total de cargas foi de '
        f'<b>{_r(total_prev)}</b>, com realizado de <b>{_r(total_real)}</b> '
        f'nos <b>{meses_com_real} mês(es) com faturamento lançado</b>. '
        f'A aderência global (realizado / previsto) nos meses concluídos foi de '
        f'<b>{aderencia_g:.1f}%</b>. '
        f'Foram atendidos <b>{n_clientes} destinos/clientes</b> com '
        f'<b>{n_canceladas + n_adiadas} ocorrência(s)</b> de cancelamento ou adiamento.'
    )
    story.append(Paragraph(conclusao_html, e['corpo']))
    story.append(Spacer(1, 0.5 * cm))

    status_p = ParagraphStyle(
        'status_c', parent=e['corpo'],
        fontName='Helvetica-Bold', fontSize=13,
        textColor=cor_status, alignment=TA_CENTER,
        spaceBefore=12, spaceAfter=12,
    )
    story.append(Paragraph(f'STATUS: {status_str}', status_p))
    story.append(_linha_divisoria(cor=cor_status, espessura=2))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Previsão de Cargas  ·  {gerado_em}',
        ParagraphStyle('ass_c', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — CARTEIRA DE PEDIDOS
# ═══════════════════════════════════════════════════════════════════════════════

def _chart_carteira_mensal(df_mes: pd.DataFrame) -> io.BytesIO:
    """Barras de valor mensal + linha acumulada para Carteira de Pedidos."""
    meses = df_mes['MES_LABEL'].tolist()
    vals  = df_mes['VALOR'].tolist()
    acum  = df_mes['ACUMULADO'].tolist()
    n     = len(meses)

    fig, ax1 = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor(MP_BG)
    ax1.set_facecolor(MP_BG)

    bars = ax1.bar(range(n), vals, color='#2AA89A', alpha=0.85, width=0.65, zorder=3)

    ax2 = ax1.twinx()
    ax2.plot(range(n), acum, color='#7C3AED', linewidth=2.5,
             marker='o', markersize=6, zorder=5)

    max_v = max(vals, default=1)
    for bar, v in zip(bars, vals):
        if v > 0 and n <= 20:
            ax1.text(bar.get_x() + bar.get_width() / 2., v + max_v * 0.012,
                     f"R$ {_fmt(int(v / 1000))}k", ha='center', va='bottom',
                     fontsize=6, color=MP_TEXT, fontweight='bold')

    ax1.set_xticks(range(n))
    ax1.set_xticklabels(meses, rotation=45, ha='right', fontsize=7.5, color=MP_TEXT)
    ax1.set_title('Evolução Mensal da Carteira de Pedidos', fontsize=12,
                  fontweight='bold', color=MP_TEXT, pad=10)
    ax1.set_ylabel('Valor Mensal (R$)', fontsize=9, color=MP_TEXT)
    ax1.tick_params(colors=MP_TEXT)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"R$ {_fmt(int(v / 1000))}k"))
    ax1.grid(axis='y', color=MP_GRID, linewidth=0.7, alpha=0.8, zorder=1)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color(MP_GRID)
    ax1.spines['bottom'].set_color(MP_GRID)

    ax2.set_ylabel('Acumulado (R$)', color='#7C3AED', fontsize=9)
    ax2.tick_params(colors='#7C3AED')
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"R$ {_fmt(int(v / 1000))}k"))
    ax2.spines['right'].set_color('#7C3AED')

    patch_bar  = mpatches.Patch(color='#2AA89A', alpha=0.85, label='Valor Mensal')
    patch_acum = mpatches.Patch(color='#7C3AED', label='Acumulado')
    ax1.legend(handles=[patch_bar, patch_acum], fontsize=8,
               framealpha=0.9, edgecolor=MP_GRID, loc='upper left')

    plt.tight_layout()
    buf_c = io.BytesIO()
    fig.savefig(buf_c, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf_c.seek(0)
    return buf_c


def _chart_carteira_pizza_categoria(df_cat: pd.DataFrame) -> io.BytesIO:
    """Pizza por categoria para Carteira de Pedidos."""
    paleta = ['#2AA89A', '#D4860A', '#45B7D1', '#38BDF8', '#7C3AED',
              '#1E8449', '#F472B6', '#CB4335', '#5D6D7E']
    labels = df_cat['CATEGORIA'].tolist()
    values = df_cat['VALOR_TOTAL'].tolist()
    total  = sum(values) or 1

    fig, ax = plt.subplots(figsize=(8, 5.5))
    fig.patch.set_facecolor(MP_BG)

    wedges, _, autotexts = ax.pie(
        values, labels=None,
        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
        colors=paleta[:len(labels)], startangle=90,
        wedgeprops=dict(edgecolor='white', linewidth=2),
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8); at.set_color('white'); at.set_fontweight('bold')

    legend_labels = [
        f'{l}: R$ {_fmt(int(v / 1000))}k ({v / total * 100:.1f}%)'
        for l, v in zip(labels, values)
    ]
    ax.legend(wedges, legend_labels, loc='center left',
              bbox_to_anchor=(1.02, 0.5), fontsize=7.5,
              framealpha=0.9, edgecolor=MP_GRID)
    ax.set_title('Distribuição por Categoria', fontsize=11, fontweight='bold',
                 color=MP_TEXT, pad=10)

    plt.tight_layout()
    buf_c = io.BytesIO()
    fig.savefig(buf_c, format='png', dpi=150, bbox_inches='tight', facecolor=MP_BG)
    plt.close(fig)
    buf_c.seek(0)
    return buf_c


def gerar_pdf_carteira_pedidos(
    df: pd.DataFrame,
    total_valor: float,
    total_pecas: int,
    n_pedidos: int,
    n_clientes: int,
    n_produtos: int,
    ticket_medio: float,
    periodo: str = '',
    filtros_texto: str = '',
) -> bytes:
    """
    Gera o relatório PDF de Carteira de Pedidos.

    Parameters
    ----------
    df            : DataFrame filtrado (ANO_MES, MES_LABEL, CATEGORIA,
                    CLIENTE_CURTO, DESCRICAO, PEDIDO, QUANTIDADE, VALOR_TOTAL)
    total_valor   : soma de VALOR_TOTAL
    total_pecas   : soma de QUANTIDADE
    n_pedidos     : pedidos únicos
    n_clientes    : clientes únicos
    n_produtos    : produtos únicos (COD_PROD)
    ticket_medio  : valor médio por pedido
    periodo       : string do período selecionado
    filtros_texto : filtros ativos em texto
    """
    _MESES_ABR = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                  7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

    def _r(v: float) -> str:
        return f"R$ {_fmt(int(v))}"

    def _rk(v: float) -> str:
        if abs(v) >= 1_000_000:
            return f"R$ {v / 1_000_000:.1f}M"
        if abs(v) >= 1_000:
            return f"R$ {_fmt(int(v / 1000))}k"
        return _r(v)

    e = _estilos()
    gerado_em   = datetime.now().strftime('%d/%m/%Y  %H:%M')
    periodo_str = periodo or datetime.now().strftime('%m/%Y')

    # ── Dados agregados ───────────────────────────────────────────────────────
    df_mes = (
        df.groupby('ANO_MES')
        .agg(VALOR=('VALOR_TOTAL', 'sum'), PECAS=('QUANTIDADE', 'sum'),
             PEDIDOS=('PEDIDO', 'nunique'))
        .reset_index().sort_values('ANO_MES')
    )
    df_mes['MES_LABEL'] = df_mes['ANO_MES'].apply(
        lambda s: f"{_MESES_ABR[int(s.split('-')[1])]}/{s.split('-')[0][2:]}"
    )
    df_mes['ACUMULADO'] = df_mes['VALOR'].cumsum()

    df_cat = (
        df.groupby('CATEGORIA')['VALOR_TOTAL'].sum()
        .reset_index().sort_values('VALOR_TOTAL', ascending=False)
    )
    df_cat_det = (
        df.groupby('CATEGORIA')
        .agg(VALOR=('VALOR_TOTAL', 'sum'), PECAS=('QUANTIDADE', 'sum'))
        .reset_index().sort_values('VALOR', ascending=False)
    )
    df_cli = (
        df.groupby('CLIENTE_CURTO')
        .agg(VALOR=('VALOR_TOTAL', 'sum'), PECAS=('QUANTIDADE', 'sum'),
             PEDIDOS=('PEDIDO', 'nunique'))
        .reset_index().sort_values('VALOR', ascending=False)
    )
    df_prod = (
        df.groupby('DESCRICAO')
        .agg(VALOR=('VALOR_TOTAL', 'sum'), PECAS=('QUANTIDADE', 'sum'))
        .reset_index().sort_values('VALOR', ascending=False)
    )

    # ── Documento ─────────────────────────────────────────────────────────────
    buf_pdf = io.BytesIO()
    doc = _RelatorioDoc(
        buf_pdf,
        titulo_rel='📦  Carteira de Pedidos',
        subtitulo_rel='Análise Comercial · Pedidos em Aberto',
        periodo=periodo_str,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = []
    story.append(PageBreak())

    # ── KPIs ─────────────────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())
    kpis = [
        {'label': '💰 Valor Total',     'valor': _rk(total_valor),  'cor': C_TEAL_LT},
        {'label': '📦 Total de Peças',  'valor': _fmt(total_pecas),  'cor': C_TEAL_LT},
        {'label': '🛒 Pedidos Únicos',  'valor': _fmt(n_pedidos),    'cor': C_AMBER_LT},
        {'label': '🏢 Clientes Ativos', 'valor': str(n_clientes),    'cor': C_AMBER_LT},
        {'label': '🎁 Ticket Médio',    'valor': _rk(ticket_medio),  'cor': C_GREEN_LT},
        {'label': '🏷 SKUs',            'valor': _fmt(n_produtos),   'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=3))
    story.append(Spacer(1, 0.7 * cm))

    # ── Tabela categorias ─────────────────────────────────────────────────────
    story.append(Paragraph('Distribuição por Categoria', e['subtitulo_secao']))
    linhas_cat = [
        [row['CATEGORIA'], _r(row['VALOR']),
         f"{row['VALOR'] / total_valor * 100:.1f}%" if total_valor > 0 else '—',
         _fmt(row['PECAS'])]
        for _, row in df_cat_det.iterrows()
    ]
    cw_cat = [5.5 * cm, 4.0 * cm, 3.0 * cm, 3.0 * cm]
    story.append(_tabela_generica(
        ['Categoria', 'Valor Total (R$)', '% Carteira', 'Peças'],
        linhas_cat, e, cw_cat,
    ))

    # ── Detalhamento de OUTROS ────────────────────────────────────────────────
    df_outros = (
        df[df['CATEGORIA'] == 'OUTROS']
        .groupby('DESCRICAO')
        .agg(VALOR=('VALOR_TOTAL', 'sum'), PECAS=('QUANTIDADE', 'sum'))
        .reset_index()
        .sort_values('VALOR', ascending=False)
    )
    if not df_outros.empty:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(
            'Composição de "Outros" — produtos não classificados nas categorias acima:',
            e['nota'],
        ))
        linhas_outros = [
            [row['DESCRICAO'][:55], _r(row['VALOR']),
             f"{row['VALOR'] / total_valor * 100:.2f}%", _fmt(row['PECAS'])]
            for _, row in df_outros.iterrows()
        ]
        cw_out = [8.5 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm]
        story.append(_tabela_generica(
            ['Produto', 'Valor (R$)', '% Carteira', 'Peças'],
            linhas_outros, e, cw_out,
            cor_header=C_GRAY_TEXT,
        ))

    story.append(PageBreak())

    # ── Gráficos: evolução + pizza ────────────────────────────────────────────
    story.append(Paragraph('Análise Gráfica', e['titulo_secao']))
    story.append(_linha_divisoria())
    try:
        story.append(_imagem_de_buf(_chart_carteira_mensal(df_mes), largura_cm=16.5))
        story.append(Spacer(1, 0.5 * cm))
    except Exception as ex:
        logger.warning(f'Chart carteira mensal: {ex}')

    story.append(Paragraph('Distribuição por Categoria', e['subtitulo_secao']))
    try:
        story.append(_imagem_de_buf(
            _chart_carteira_pizza_categoria(df_cat), largura_cm=14.0))
    except Exception as ex:
        logger.warning(f'Chart carteira pizza: {ex}')

    story.append(PageBreak())

    # ── Gráficos: clientes + produtos ─────────────────────────────────────────
    story.append(Paragraph('Análise por Cliente e Produto', e['titulo_secao']))
    story.append(_linha_divisoria())
    try:
        story.append(_imagem_de_buf(
            _chart_barras_h(df_cli, 'CLIENTE_CURTO', 'VALOR',
                            'Top Clientes — Valor Total (R$)', top_n=10, cor='#45B7D1'),
            largura_cm=16.5,
        ))
        story.append(Spacer(1, 0.5 * cm))
    except Exception as ex:
        logger.warning(f'Chart carteira clientes: {ex}')

    try:
        story.append(_imagem_de_buf(
            _chart_barras_h(df_prod, 'DESCRICAO', 'VALOR',
                            'Top 15 Produtos — Valor Total (R$)', top_n=15, cor='#2AA89A'),
            largura_cm=16.5,
        ))
    except Exception as ex:
        logger.warning(f'Chart carteira produtos: {ex}')

    story.append(PageBreak())

    # ── Tabela por cliente ────────────────────────────────────────────────────
    story.append(Paragraph('Resumo por Cliente', e['titulo_secao']))
    story.append(_linha_divisoria())
    df_cli['PCT']    = (df_cli['VALOR'] / total_valor * 100).round(1) if total_valor > 0 else 0
    df_cli['TICKET'] = (df_cli['VALOR'] / df_cli['PEDIDOS']).fillna(0).round(0)
    linhas_cli = [
        [row['CLIENTE_CURTO'][:30], _fmt(row['PEDIDOS']), _fmt(row['PECAS']),
         _r(row['VALOR']), _r(row['TICKET']), f"{row['PCT']:.1f}%"]
        for _, row in df_cli.head(30).iterrows()
    ]
    cw_cli = [4.5 * cm, 2.0 * cm, 2.5 * cm, 3.5 * cm, 3.5 * cm, 2.5 * cm]
    story.append(_tabela_generica(
        ['Cliente', 'Pedidos', 'Peças', 'Valor Total (R$)', 'Ticket Médio (R$)', '% Carteira'],
        linhas_cli, e, cw_cli,
    ))

    # ── Conclusão ─────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('Conclusão', e['titulo_secao']))
    story.append(_linha_divisoria())

    top_cat     = df_cat_det.iloc[0]['CATEGORIA'] if not df_cat_det.empty else 'N/D'
    top_cli     = df_cli.iloc[0]['CLIENTE_CURTO'] if not df_cli.empty else 'N/D'
    top_pct_cat = (df_cat_det.iloc[0]['VALOR'] / total_valor * 100
                   if not df_cat_det.empty and total_valor > 0 else 0)

    conclusao_html = (
        f'A carteira de pedidos no período <b>{periodo_str}</b> totaliza '
        f'<b>{_rk(total_valor)}</b> em <b>{_fmt(n_pedidos)} pedidos</b>, '
        f'representando <b>{_fmt(total_pecas)} peças</b> para <b>{n_clientes} clientes</b>. '
        f'O ticket médio por pedido é de <b>{_rk(ticket_medio)}</b>. '
        f'A categoria predominante é <b>{top_cat}</b> ({top_pct_cat:.1f}% do valor total) '
        f'e o cliente com maior volume é <b>{top_cli}</b>.'
    )
    story.append(Paragraph(conclusao_html, e['corpo']))
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Carteira de Pedidos  ·  {gerado_em}',
        ParagraphStyle('ass_cp', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf_pdf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — PRODUÇÃO POR FACÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_faccoes(
    tabela: pd.DataFrame,
    df_mes: pd.DataFrame,
    total_mes: int,
    meta_mes_total: int,
    pct_mes: float,
    pct_ritmo: float,
    meta_dia_total: float,
    data_ini: date,
    data_fim: date,
    filtros_texto: str = '',
) -> bytes:
    """
    Relatório PDF de Produção por Facção.

    Parameters
    ----------
    tabela        : DataFrame com colunas Produto, Empresa, Facção, Produzido, Meta Mês, % Meta, Restante
    df_mes        : DataFrame filtrado com DATA, FACCAO, PRODUTO, CLIENTE, QUANTIDADE
    total_mes     : total de peças produzidas no período
    meta_mes_total: meta total do mês
    pct_mes       : % da meta atingida
    pct_ritmo     : % do ritmo esperado
    meta_dia_total: meta diária calculada
    data_ini/fim  : período selecionado
    filtros_texto : string descritiva dos filtros ativos
    """
    e = _estilos()
    periodo_str = (
        f"{data_ini.strftime('%d/%m/%Y')}  até  {data_fim.strftime('%d/%m/%Y')}"
        if data_ini != data_fim else data_ini.strftime('%d/%m/%Y')
    )
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='Relatório de Produção · Facções',
        subtitulo_rel='Acompanhamento de Produção — Facções Externas',
        periodo=periodo_str,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = [PageBreak()]

    # ── Resumo Executivo ─────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    kpis = [
        {'label': 'Producao do Mes',  'valor': _fmt(total_mes),       'cor': C_TEAL_LT},
        {'label': 'Meta Mensal',      'valor': _fmt(meta_mes_total),   'cor': C_GRAY_BG},
        {'label': '% da Meta',        'valor': f'{pct_mes:.1f}%',      'cor': _pct_bg(pct_mes)},
        {'label': 'Ritmo do Mes',     'valor': f'{pct_ritmo:.1f}%',    'cor': _pct_bg(pct_ritmo)},
        {'label': 'Meta Diaria',      'valor': _fmt(meta_dia_total),   'cor': C_AMBER_LT},
        {'label': 'Faccoes Ativas',   'valor': str(df_mes['FACCAO'].nunique()) if not df_mes.empty else '0', 'cor': C_GRAY_BG},
        {'label': 'Produtos',         'valor': str(df_mes['PRODUTO'].nunique()) if not df_mes.empty else '0', 'cor': C_GRAY_BG},
        {'label': 'Clientes',         'valor': str(df_mes['CLIENTE'].nunique()) if not df_mes.empty else '0', 'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=4))
    story.append(Spacer(1, 0.5 * cm))

    # ── Gráfico produção diária ──────────────────────────────────────────────
    if not df_mes.empty:
        prod_diaria = (
            df_mes.groupby('DATA')['QUANTIDADE'].sum()
            .reset_index().sort_values('DATA')
        )
        try:
            buf_chart = _chart_producao_diaria(
                prod_diaria, meta_dia_total,
                titulo=f'Producao Diaria — Faccoes  |  Meta/dia: {_fmt(meta_dia_total)} pc',
                largura=16.0, altura=5.0,
            )
            story.append(_imagem_de_buf(buf_chart, largura_cm=16.5))
            story.append(Spacer(1, 0.4 * cm))
        except Exception as _ex:
            logger.warning('gerar_pdf_faccoes: chart diario: %s', _ex)

    story.append(PageBreak())

    # ── Tabela de progresso ──────────────────────────────────────────────────
    story.append(Paragraph('Progresso por Produto / Empresa / Faccao', e['titulo_secao']))
    story.append(_linha_divisoria())

    cabec = ['Produto', 'Empresa', 'Faccao', 'Produzido', 'Meta Mes', '% Meta', 'Restante']
    cw = [3.0*cm, 2.5*cm, 3.5*cm, 2.0*cm, 2.0*cm, 1.8*cm, 2.0*cm]

    linhas_tab = []
    for _, r in tabela.iterrows():
        pct_v = r.get('% Meta')
        pct_s = f"{pct_v:.1f}%" if pct_v is not None and not (isinstance(pct_v, float) and pd.isna(pct_v)) else '-'
        meta_s = _fmt(r['Meta Mes']) if r.get('Meta Mes') is not None and not (isinstance(r['Meta Mes'], float) and pd.isna(r['Meta Mes'])) else '-'
        rest_s = _fmt(r['Restante']) if r.get('Restante') is not None and not (isinstance(r['Restante'], float) and pd.isna(r['Restante'])) else '-'
        linhas_tab.append([
            str(r['Produto']), str(r['Empresa']), str(r['Faccao']),
            _fmt(r['Produzido']), meta_s, pct_s, rest_s,
        ])

    t_prog = _tabela_generica(cabec, linhas_tab, e, cw, cor_header=colors.HexColor('#065F46'))
    for ri, row in enumerate(linhas_tab, start=1):
        try:
            pct_val = float(row[5].replace('%', ''))
            cor_s = C_GREEN if pct_val >= 100 else (C_AMBER if pct_val >= 75 else C_RED)
            t_prog.setStyle(TableStyle([('TEXTCOLOR', (5, ri), (5, ri), cor_s),
                                        ('FONTNAME', (5, ri), (5, ri), 'Helvetica-Bold')]))
        except Exception:
            pass
    story.append(t_prog)
    story.append(Spacer(1, 0.4 * cm))

    # ── Gráfico top facções ──────────────────────────────────────────────────
    if not df_mes.empty:
        fac_total = df_mes.groupby('FACCAO')['QUANTIDADE'].sum().reset_index()
        try:
            buf_fac = _chart_barras_h(fac_total, 'FACCAO', 'QUANTIDADE',
                                      'Producao Total por Faccao no Periodo', top_n=20)
            story.append(_imagem_de_buf(buf_fac, largura_cm=16.5))
            story.append(Spacer(1, 0.4 * cm))
        except Exception as _ex:
            logger.warning('gerar_pdf_faccoes: chart faccoes: %s', _ex)

    story.append(PageBreak())

    # ── Detalhe por facção ───────────────────────────────────────────────────
    story.append(Paragraph('Detalhe Diario por Faccao', e['titulo_secao']))
    story.append(_linha_divisoria())

    if not df_mes.empty:
        cab_det = ['Data', 'Produto', 'Empresa', 'Qtd']
        cw_det = [2.2*cm, 4.0*cm, 3.5*cm, 2.2*cm]

        for faccao in sorted(df_mes['FACCAO'].unique()):
            df_f = df_mes[df_mes['FACCAO'] == faccao]
            total_fac = int(df_f['QUANTIDADE'].sum())
            det = (df_f.groupby(['DATA', 'PRODUTO', 'CLIENTE'])['QUANTIDADE']
                   .sum().reset_index().sort_values('DATA'))

            _t_hdr = Table([[Paragraph(
                f'{faccao}  -  Total: {_fmt(total_fac)} pcs',
                ParagraphStyle('_fh', parent=e['subtitulo_secao'],
                               textColor=C_WHITE, fontName='Helvetica-Bold',
                               fontSize=9, spaceBefore=0, spaceAfter=0),
            )]], colWidths=[PAGE_W - 2 * MARGIN])
            _t_hdr.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0F4C5C')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(_t_hdr)

            linhas_det = []
            for _, r in det.iterrows():
                linhas_det.append([
                    pd.Timestamp(r['DATA']).strftime('%d/%m/%Y'),
                    str(r['PRODUTO']), str(r['CLIENTE']), _fmt(r['QUANTIDADE']),
                ])
            story.append(_tabela_generica(cab_det, linhas_det, e, cw_det,
                                          cor_header=colors.HexColor('#2A6496')))
            story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        f'Relatorio gerado automaticamente pelo Sistema de Gestao Industrial<br/>'
        f'Producao por Faccao  ·  {gerado_em}',
        ParagraphStyle('ass_fac', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — CONTROLADORIA / PROGRAMAÇÃO DE CORTE
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_programacao(
    df_agg: pd.DataFrame,
    total_ops: int,
    concluidas: int,
    parciais: int,
    pendentes: int,
    aderencia_pct: float,
    total_prog_pcs: int,
    total_cort_pcs: int,
    filtros_texto: str = '',
) -> bytes:
    """
    Relatório PDF de Programação de Corte (Controladoria).

    Parameters
    ----------
    df_agg         : DataFrame agregado por OP — colunas SEMANA, PED. CLIENTE,
                     CLIENTE, LOCAL, PRODUTO, QNT_PROG_TOTAL, QNT_CORTADA,
                     EFICIÊNCIA_PRC, STATUS_CORTE
    total_ops, concluidas, parciais, pendentes, aderencia_pct,
    total_prog_pcs, total_cort_pcs : KPIs já calculados na página
    filtros_texto  : string descritiva dos filtros ativos
    """
    e = _estilos()
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')
    ef_total = (total_cort_pcs / total_prog_pcs * 100) if total_prog_pcs > 0 else 0

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel='Relatorio Programacao de Corte',
        subtitulo_rel='Controladoria — Planejado vs. Realizado',
        periodo=gerado_em,
        gerado_em=gerado_em,
        filtros=filtros_texto,
    )

    story = [PageBreak()]

    # ── KPIs ─────────────────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo', e['titulo_secao']))
    story.append(_linha_divisoria())

    kpis = [
        {'label': 'Total de OPs',      'valor': str(total_ops),          'cor': C_GRAY_BG},
        {'label': 'Concluidas',         'valor': str(concluidas),         'cor': C_GREEN_LT},
        {'label': 'Parciais',           'valor': str(parciais),           'cor': C_AMBER_LT},
        {'label': 'Pendentes',          'valor': str(pendentes),          'cor': C_RED_LT},
        {'label': 'Aderencia',          'valor': f'{aderencia_pct:.1f}%', 'cor': _pct_bg(aderencia_pct)},
        {'label': 'Pecas Programadas',  'valor': _fmt(total_prog_pcs),    'cor': C_GRAY_BG},
        {'label': 'Pecas Cortadas',     'valor': _fmt(total_cort_pcs),    'cor': _pct_bg(ef_total)},
        {'label': 'Eficiencia Geral',   'valor': f'{ef_total:.1f}%',      'cor': _pct_bg(ef_total)},
    ]
    story.append(_bloco_kpis(kpis, e, colunas=4))
    story.append(Spacer(1, 0.6 * cm))

    # ── Gráfico Programado vs Cortado por Semana ──────────────────────────────
    if not df_agg.empty and 'SEMANA' in df_agg.columns:
        try:
            semanas = sorted(df_agg['SEMANA'].dropna().unique())
            sem_data = [
                {
                    'SEMANA': str(s),
                    'Programado': int(df_agg[df_agg['SEMANA'] == s]['QNT_PROG_TOTAL'].sum()),
                    'Cortado': int(df_agg[df_agg['SEMANA'] == s]['QNT_CORTADA'].sum()),
                }
                for s in semanas
            ]
            df_sem = pd.DataFrame(sem_data)

            fig_sem, ax_sem = plt.subplots(figsize=(14, 4.5))
            fig_sem.patch.set_facecolor(MP_BG)
            ax_sem.set_facecolor(MP_BG)
            x = range(len(df_sem))
            w = 0.35
            ax_sem.bar([i - w/2 for i in x], df_sem['Programado'], w,
                       label='Programado', color='#5D6D7E', alpha=0.85)
            ax_sem.bar([i + w/2 for i in x], df_sem['Cortado'], w,
                       label='Cortado', color=MP_BAR_OK, alpha=0.85)
            ax_sem.set_xticks(list(x))
            ax_sem.set_xticklabels(df_sem['SEMANA'].tolist(), fontsize=8, color=MP_TEXT)
            ax_sem.set_title('Programado vs Cortado por Semana', fontsize=11,
                             fontweight='bold', color=MP_TEXT)
            ax_sem.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: _fmt(v)))
            ax_sem.legend(fontsize=8)
            ax_sem.grid(axis='y', color=MP_GRID, linewidth=0.7, alpha=0.8)
            ax_sem.spines['top'].set_visible(False)
            ax_sem.spines['right'].set_visible(False)
            plt.tight_layout()
            buf_sem = io.BytesIO()
            fig_sem.savefig(buf_sem, format='png', dpi=150,
                            bbox_inches='tight', facecolor=MP_BG)
            plt.close(fig_sem)
            buf_sem.seek(0)
            story.append(_imagem_de_buf(buf_sem, largura_cm=16.5))
            story.append(Spacer(1, 0.4 * cm))
        except Exception as _ex:
            logger.warning('gerar_pdf_programacao: chart semanas: %s', _ex)

    story.append(PageBreak())

    # ── Tabela de OPs ────────────────────────────────────────────────────────
    story.append(Paragraph('Resumo por Ordem de Producao (OP)', e['titulo_secao']))
    story.append(_linha_divisoria())

    cabec_op = ['Sem.', 'OP', 'Cliente', 'Local', 'Produto', 'Prog.', 'Cortado', 'Efic.%', 'Status']
    cw_op = [1.0*cm, 2.2*cm, 2.8*cm, 1.8*cm, 3.5*cm, 1.8*cm, 1.8*cm, 1.5*cm, 2.1*cm]

    linhas_op = []
    for _, r in df_agg.iterrows():
        ef = float(r.get('EFICIENCIA_PRC', r.get('EFICIÊNCIA_PRC', 0)))
        status_c = str(r.get('STATUS_CORTE', ''))
        op_val = str(r.get('PED. CLIENTE', '')).strip() or '-'
        linhas_op.append([
            str(r.get('SEMANA', '')),
            op_val,
            str(r.get('CLIENTE', ''))[:20],
            str(r.get('LOCAL', ''))[:12],
            str(r.get('PRODUTO', ''))[:25],
            _fmt(r.get('QNT_PROG_TOTAL', 0)),
            _fmt(r.get('QNT_CORTADA', 0)),
            f'{ef:.1f}%',
            status_c,
        ])

    t_ops = _tabela_generica(cabec_op, linhas_op, e, cw_op,
                             cor_header=colors.HexColor('#1E1B4B'))
    for ri, row in enumerate(linhas_op, start=1):
        status_v = row[8]
        cor_st = C_GREEN if status_v == 'Concluido' else (C_AMBER if status_v == 'Parcial' else C_RED)
        t_ops.setStyle(TableStyle([('TEXTCOLOR', (8, ri), (8, ri), cor_st),
                                   ('FONTNAME', (8, ri), (8, ri), 'Helvetica-Bold')]))
        try:
            ef_num = float(row[7].replace('%', ''))
            cor_ef = C_GREEN if ef_num >= 96 else (C_AMBER if ef_num >= 50 else C_RED)
            t_ops.setStyle(TableStyle([('TEXTCOLOR', (7, ri), (7, ri), cor_ef)]))
        except Exception:
            pass
    story.append(t_ops)

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        f'Relatorio gerado automaticamente pelo Sistema de Gestao Industrial<br/>'
        f'Programacao de Corte  ·  {gerado_em}',
        ParagraphStyle('ass_prog', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR — RELATÓRIO CONSOLIDADO DE CORTE (todas as regiões)
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_corte_consolidado(
    df_manta: pd.DataFrame,
    df_lencol: pd.DataFrame,
    df_iacanga: pd.DataFrame,
    df_itaju: pd.DataFrame,
    ini: date,
    fim: date,
    metas_arealva: dict,
    metas_iacanga: dict,
) -> bytes:
    """
    Relatório mensal consolidado de corte — Arealva Manta, Lençol, Iacanga e Itaju.
    Formato compacto para envio por e-mail.
    """
    from datetime import timedelta as _tdc
    e = _estilos()
    periodo_str = f"{ini.strftime('%d/%m/%Y')}  até  {fim.strftime('%d/%m/%Y')}"
    gerado_em = datetime.now().strftime('%d/%m/%Y  %H:%M')
    meses_pt = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
                7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
    mes_label = meses_pt.get(ini.month, '') + f'/{ini.year}'

    _wdays = sum(1 for i in range((fim - ini).days + 1)
                 if (ini + _tdc(days=i)).weekday() < 5)

    buf = io.BytesIO()
    doc = _RelatorioDoc(
        buf,
        titulo_rel=f'✂  Relatório de Corte · {mes_label}',
        subtitulo_rel='Consolidado — Arealva Manta · Lençol · Iacanga · Itaju',
        periodo=periodo_str,
        gerado_em=gerado_em,
    )
    story = [PageBreak()]  # capa

    # ── helper interno ────────────────────────────────────────────────────────
    def _secao_corte(titulo: str, cor_titulo, df_sec: pd.DataFrame,
                     meta_total: float, col_est: str = 'ESTACAO',
                     col_quant: str = 'QUANTIDADE', col_data: str = 'DATA'):
        """Renderiza uma seção de corte: título + KPIs + gráfico + tabela por estação."""
        if df_sec is None or df_sec.empty:
            story.append(Paragraph(f'{titulo} — sem dados no período', e['nota']))
            story.append(Spacer(1, 0.3*cm))
            return

        total = int(df_sec[col_quant].sum())
        dias  = df_sec[col_data].dt.date.nunique()
        media = total / max(dias, 1)
        pct   = (media / meta_total * 100) if meta_total > 0 else 0

        # Título da seção com fundo colorido
        _t_hdr = Table([[Paragraph(titulo, ParagraphStyle(
            '_sh', parent=e['subtitulo_secao'],
            textColor=C_WHITE, fontName='Helvetica-Bold', fontSize=11,
            spaceBefore=0, spaceAfter=0,
        ))]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        _t_hdr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), cor_titulo),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(_t_hdr)
        story.append(Spacer(1, 0.25*cm))

        # KPIs
        kpis_s = [
            {'label': 'Total Peças', 'valor': _fmt(total), 'cor': C_TEAL_LT},
            {'label': 'Dias Trab.',  'valor': str(dias),   'cor': C_GRAY_BG},
            {'label': 'Média/Dia',   'valor': _fmt(media), 'cor': _pct_bg(pct)},
            {'label': '% Meta',      'valor': f'{pct:.1f}%', 'cor': _pct_bg(pct)},
        ]
        story.append(_bloco_kpis(kpis_s, e, colunas=4))
        story.append(Spacer(1, 0.3*cm))

        # Gráfico diário
        try:
            prod_dia = df_sec.groupby(col_data)[col_quant].sum().reset_index()
            prod_dia.columns = ['DATA', 'QUANTIDADE']
            prod_dia = prod_dia.sort_values('DATA')
            buf_c = _chart_producao_diaria(prod_dia, meta_total,
                                           titulo=f'Produção Diária — {titulo}',
                                           largura=16.0, altura=4.5)
            story.append(_imagem_de_buf(buf_c, largura_cm=16.5))
            story.append(Spacer(1, 0.3*cm))
        except Exception as _ex:
            logger.warning(f'chart {titulo}: {_ex}')

        # Tabela por estação (se disponível)
        if col_est in df_sec.columns:
            est_tab = (df_sec.groupby(col_est)[col_quant]
                       .sum().reset_index().sort_values(col_quant, ascending=False))
            est_tab = est_tab[est_tab[col_quant] > 0]
            if not est_tab.empty:
                est_tab['%'] = (est_tab[col_quant] / total * 100).round(1)
                cab = [col_est.replace('_', ' ').title(), 'Peças', '% Total']
                lins = [
                    [str(r[col_est])[:30], _fmt(r[col_quant]), f"{r['%']:.1f}%"]
                    for _, r in est_tab.iterrows()
                ]
                cw = [8.0*cm, 3.5*cm, 2.5*cm]
                story.append(_tabela_generica(cab, lins, e, cw))

        story.append(Spacer(1, 0.5*cm))

    # ── Resumo Executivo ─────────────────────────────────────────────────────
    story.append(Paragraph('Resumo Executivo — Todos os Cortes', e['titulo_secao']))
    story.append(_linha_divisoria())

    def _safe_total(df, col='QUANTIDADE'):
        return int(df[col].sum()) if df is not None and not df.empty else 0

    tot_manta  = _safe_total(df_manta)
    tot_lencol = _safe_total(df_lencol, 'QUANT') if 'QUANT' in (df_lencol.columns if df_lencol is not None else []) else _safe_total(df_lencol)
    tot_iac    = _safe_total(df_iacanga)
    tot_itaju  = _safe_total(df_itaju)
    tot_geral  = tot_manta + tot_lencol + tot_iac + tot_itaju

    kpis_geral = [
        {'label': '✂ Arealva Manta',  'valor': _fmt(tot_manta),  'cor': C_TEAL_LT},
        {'label': '🧵 Arealva Lençol', 'valor': _fmt(tot_lencol), 'cor': C_AMBER_LT},
        {'label': '✂ Iacanga',         'valor': _fmt(tot_iac),    'cor': C_GREEN_LT},
        {'label': '✂ Itaju',           'valor': _fmt(tot_itaju),  'cor': C_GRAY_BG},
    ]
    story.append(_bloco_kpis(kpis_geral, e, colunas=4))
    story.append(Spacer(1, 0.2*cm))

    _tot_style = ParagraphStyle('_tot', parent=e['corpo'],
                                fontName='Helvetica-Bold', fontSize=11,
                                textColor=C_NAVY, alignment=TA_CENTER)
    story.append(Paragraph(f'Total Geral: {_fmt(tot_geral)} peças no período', _tot_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(_linha_divisoria(cor=C_GRAY_LINE, espessura=0.8))

    # ── Seção Arealva Manta ──────────────────────────────────────────────────
    story.append(Paragraph('1. Arealva — Manta', e['titulo_secao']))
    story.append(_linha_divisoria())
    meta_manta = sum(metas_arealva.get(k, {}).get('_DEFAULT', 0) for k in metas_arealva) if metas_arealva else 0

    _df_manta_mes = df_manta[
        (df_manta['DATA'] >= pd.Timestamp(ini)) &
        (df_manta['DATA'] <= pd.Timestamp(fim))
    ] if df_manta is not None and not df_manta.empty else pd.DataFrame()

    _secao_corte('Arealva — Manta', colors.HexColor('#1F3A93'), _df_manta_mes,
                 meta_manta, col_est='ESTACAO')

    story.append(PageBreak())

    # ── Seção Arealva Lençol ─────────────────────────────────────────────────
    story.append(Paragraph('2. Arealva — Lençol', e['titulo_secao']))
    story.append(_linha_divisoria())

    _df_ln = df_lencol
    if _df_ln is not None and not _df_ln.empty and 'DATA' in _df_ln.columns:
        _df_ln = _df_ln[
            (pd.to_datetime(_df_ln['DATA'], errors='coerce') >= pd.Timestamp(ini)) &
            (pd.to_datetime(_df_ln['DATA'], errors='coerce') <= pd.Timestamp(fim))
        ].copy()
        _df_ln['DATA'] = pd.to_datetime(_df_ln['DATA'], errors='coerce')
        _col_q_ln = 'QUANT' if 'QUANT' in _df_ln.columns else 'QUANTIDADE'
        _df_ln[_col_q_ln] = pd.to_numeric(_df_ln[_col_q_ln], errors='coerce').fillna(0)
        _secao_corte('Arealva — Lençol', colors.HexColor('#5D4037'), _df_ln,
                     meta_total=0, col_est='PRESTADOR' if 'PRESTADOR' in _df_ln.columns else 'ESTACAO',
                     col_quant=_col_q_ln)
    else:
        story.append(Paragraph('Arealva Lençol — sem dados no período.', e['nota']))

    story.append(PageBreak())

    # ── Seção Iacanga ────────────────────────────────────────────────────────
    story.append(Paragraph('3. Iacanga — Manta (Giattex)', e['titulo_secao']))
    story.append(_linha_divisoria())
    meta_iac = sum(
        v.get('CASAL', v.get('_DEFAULT', 0))
        for v in metas_iacanga.values()
    ) if metas_iacanga else 0

    _df_iac = df_iacanga
    if _df_iac is not None and not _df_iac.empty:
        _df_iac = _df_iac[
            (_df_iac['DATA'] >= pd.Timestamp(ini)) &
            (_df_iac['DATA'] <= pd.Timestamp(fim))
        ]
    _secao_corte('Iacanga — Manta', colors.HexColor('#4A0E8F'), _df_iac,
                 meta_iac, col_est='ESTACAO')

    story.append(PageBreak())

    # ── Seção Itaju ──────────────────────────────────────────────────────────
    story.append(Paragraph('4. Itaju — Ponto Palito', e['titulo_secao']))
    story.append(_linha_divisoria())

    _df_it = df_itaju
    if _df_it is not None and not _df_it.empty:
        _df_it = _df_it[
            (_df_it['DATA'] >= pd.Timestamp(ini)) &
            (_df_it['DATA'] <= pd.Timestamp(fim))
        ]
    _secao_corte('Itaju — Ponto Palito', colors.HexColor('#064E3B'), _df_it,
                 meta_total=0, col_est='ESTACAO' if _df_it is not None and 'ESTACAO' in _df_it.columns else 'PRODUTO')

    # ── Rodapé final ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.0*cm))
    story.append(Paragraph(
        f'Relatório gerado automaticamente pelo Sistema de Gestão Industrial<br/>'
        f'Corte Consolidado · {mes_label}  ·  {gerado_em}',
        ParagraphStyle('ass_cc', parent=e['nota'], alignment=TA_CENTER, fontSize=8),
    ))

    doc.build(story)
    return buf.getvalue()
