# -*- coding: utf-8 -*-
"""
Dashboard Unificado - Página Inicial
Centraliza o acesso aos dashboards setoriais (Produtos Faturados,
Produção Geral e Controle de Corte) em uma única interface.
"""

import os
import sys
from datetime import datetime

import streamlit as st

# Garante que módulos no root (config.py, gid_detector.py) sejam importáveis
# a partir das páginas em pages/
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard de Análise Geral | Central de Setores",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# PALETA DE CORES (inspirada nos 3 dashboards)
# ──────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "bg_deep":      "#0E1117",
    "bg_card":      "#1A1F2E",
    "bg_card_2":    "#22293B",
    "teal":         "#4ECDC4",
    "navy":         "#1D3557",
    "coral":        "#E76F51",
    "gold":         "#F4A261",
    "mint":         "#2A9D8F",
    "sky":          "#45B7D1",
    "lavender":     "#AB47BC",
    "amber":        "#FFA726",
    "text_strong":  "#FFFFFF",
    "text_default": "#E0E0E0",
    "text_muted":   "#A0A0A0",
    "border":       "rgba(255,255,255,0.10)",
    "border_hover": "rgba(78,205,196,0.55)",
}

SECTORS = [
    {
        "key": "faturados",
        "title": "Produtos Faturados",
        "subtitle": "Análise comercial e faturamento",
        "description": (
            "Visão completa de produtos faturados, ranking de clientes, "
            "evolução de receita, mix de produtos e indicadores de venda."
        ),
        "icon": "📦",
        "page_path": "pages/1_Produtos_Faturados.py",
        "color_a": "#1D3557",
        "color_b": "#0C6E74",
        "accent":  "#E76F51",
        "tags": ["Comercial", "Receita", "Clientes"],
    },
    {
        "key": "producao",
        "title": "Produção Geral",
        "subtitle": "Multi-empresas em tempo real",
        "description": (
            "Acompanhamento da produção de todas as empresas do grupo "
            "(Burdays, Camesa, Niazitex, Cortex, Sultan, Decor, Marcelino) "
            "com metas, evolução diária e comparativos."
        ),
        "icon": "🏭",
        "page_path": "pages/2_Producao_Geral.py",
        "color_a": "#0F4C5C",
        "color_b": "#4ECDC4",
        "accent":  "#FFA726",
        "tags": ["Produção", "Multi-empresa", "Metas"],
    },
    {
        "key": "corte",
        "title": "Controle de Corte",
        "subtitle": "Mantas — estações e desempenho",
        "description": (
            "Painel operacional do setor de corte de mantas com metas "
            "diárias por estação (Máquina, Mesa 1, Mesa 2), produção, "
            "OPs e indicadores por operador."
        ),
        "icon": "✂️",
        "page_path": "pages/3_Controle_de_Corte.py",
        "color_a": "#1F3A93",
        "color_b": "#45B7D1",
        "accent":  "#4ECDC4",
        "tags": ["Operação", "Corte", "Metas diárias"],
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# CSS CUSTOMIZADO
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        :root {{
            --bg-deep: {PALETTE['bg_deep']};
            --bg-card: {PALETTE['bg_card']};
            --bg-card-2: {PALETTE['bg_card_2']};
            --teal: {PALETTE['teal']};
            --navy: {PALETTE['navy']};
            --coral: {PALETTE['coral']};
            --gold: {PALETTE['gold']};
            --text-strong: {PALETTE['text_strong']};
            --text-default: {PALETTE['text_default']};
            --text-muted: {PALETTE['text_muted']};
            --border: {PALETTE['border']};
            --border-hover: {PALETTE['border_hover']};
        }}

        footer {{ visibility: hidden; }}
        #MainMenu {{ visibility: hidden; }}

        .stApp {{
            background:
                radial-gradient(circle at 12% 10%, rgba(78,205,196,0.10) 0%, rgba(78,205,196,0) 38%),
                radial-gradient(circle at 88% 14%, rgba(231,111,81,0.10) 0%, rgba(231,111,81,0) 40%),
                radial-gradient(circle at 50% 110%, rgba(69,183,209,0.08) 0%, rgba(69,183,209,0) 45%),
                linear-gradient(180deg, #0B0E14 0%, #0E1117 55%, #11151F 100%);
            color: var(--text-default);
            font-family: 'Space Grotesk', sans-serif;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0C0F16 0%, #141925 100%) !important;
            border-right: 1px solid var(--border);
        }}
        section[data-testid="stSidebar"] * {{
            color: var(--text-default) !important;
            font-family: 'Space Grotesk', sans-serif;
        }}

        .hero {{
            text-align: center;
            padding: 28px 12px 8px 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
        }}
        .hero-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 999px;
            font-size: 0.72rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--teal);
            background: rgba(78,205,196,0.10);
            border: 1px solid rgba(78,205,196,0.30);
            font-weight: 600;
            margin-bottom: 18px;
        }}
        .hero-title {{
            font-family: 'Sora', sans-serif;
            font-size: 3.0rem;
            font-weight: 800;
            line-height: 1.05;
            margin: 0;
            color: var(--text-strong);
            letter-spacing: -0.5px;
        }}
        .hero-title .accent {{
            background: linear-gradient(90deg, var(--teal), #7CDDD6 45%, var(--coral) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .hero-subtitle {{
            font-size: 1.10rem;
            color: var(--text-muted);
            max-width: 760px;
            margin: 14px auto 6px auto;
            line-height: 1.5;
            text-align: center;
            width: 100%;
        }}
        .hero-meta {{
            display: inline-flex;
            gap: 14px;
            justify-content: center;
            margin: 18px 0 8px 0;
            flex-wrap: wrap;
        }}
        .hero-pill {{
            font-size: 0.78rem;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: rgba(255,255,255,0.03);
            color: var(--text-muted);
        }}
        .hero-pill b {{ color: var(--text-strong); font-weight: 600; }}

        .divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border), transparent);
            margin: 22px 0 8px 0;
        }}

        .section-label {{
            font-family: 'Sora', sans-serif;
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--text-strong);
            margin: 14px 0 4px 0;
            text-align: center;
        }}
        .section-helper {{
            color: var(--text-muted);
            margin-bottom: 18px;
            text-align: center;
        }}
        .sectors-container {{
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
            max-width: 1400px;
            margin: 24px auto;
            padding: 0 16px;
        }}
        .sector-card-wrapper {{
            flex: 1;
            min-width: 300px;
            max-width: 420px;
        }}

        [data-testid="stColumn"] {{
            width: 100%;
        }}

        .sector-card {{
            position: relative;
            border-radius: 18px;
            padding: 22px 22px 18px 22px;
            background: linear-gradient(160deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%);
            border: 1px solid var(--border);
            overflow: hidden;
            min-height: 270px;
            transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
        }}
        .sector-card::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(160deg, var(--card-a) 0%, var(--card-b) 100%);
            opacity: 0.18;
            transition: opacity 0.25s ease;
            pointer-events: none;
        }}
        .sector-card:hover {{
            transform: translateY(-4px);
            border-color: var(--card-accent, var(--border-hover));
            box-shadow: 0 12px 30px rgba(0,0,0,0.45),
                        0 0 0 1px var(--card-accent, var(--border-hover));
        }}
        .sector-card:hover::before {{ opacity: 0.32; }}

        .sector-icon-wrap {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 54px;
            height: 54px;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--card-a), var(--card-b));
            font-size: 1.7rem;
            box-shadow: 0 6px 18px rgba(0,0,0,0.35);
            margin: 0 auto 14px auto;
        }}
        .sector-title {{
            font-family: 'Sora', sans-serif;
            font-size: 1.32rem;
            font-weight: 700;
            color: var(--text-strong);
            margin: 0;
            text-align: center;
        }}
        .sector-subtitle {{
            font-size: 0.85rem;
            color: var(--card-accent);
            margin: 2px 0 12px 0;
            font-weight: 600;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            text-align: center;
        }}
        .sector-desc {{
            color: var(--text-default);
            font-size: 0.95rem;
            line-height: 1.55;
            margin-bottom: 14px;
            text-align: center;
        }}
        .sector-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 6px;
            justify-content: center;
        }}
        .sector-tag {{
            font-size: 0.72rem;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: var(--text-muted);
            letter-spacing: 0.02em;
        }}

        /* Botões de navegação (cards e sidebar) */
        .stButton > button {{
            background: linear-gradient(135deg, var(--teal), #2BB3AB) !important;
            color: #0B0E14 !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            padding: 10px 14px !important;
            border: 1px solid rgba(78,205,196,0.55) !important;
            box-shadow: 0 6px 18px rgba(78,205,196,0.25) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease !important;
            width: 100% !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(78,205,196,0.40) !important;
            filter: brightness(1.05);
        }}
        .stButton > button:active,
        .stButton > button:focus {{
            background: linear-gradient(135deg, var(--teal), #2BB3AB) !important;
            color: #0B0E14 !important;
            outline: none !important;
        }}
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {{
            color: #0B0E14 !important;
            font-weight: 700 !important;
        }}
        /* Sidebar: botões em estilo levemente diferente (mais sutis) */
        section[data-testid="stSidebar"] .stButton > button {{
            background: linear-gradient(135deg, rgba(78,205,196,0.18), rgba(78,205,196,0.08)) !important;
            color: var(--teal) !important;
            border: 1px solid rgba(78,205,196,0.35) !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: linear-gradient(135deg, rgba(78,205,196,0.30), rgba(78,205,196,0.14)) !important;
            border-color: var(--teal) !important;
            color: #FFFFFF !important;
            transform: translateY(-1px);
        }}
        section[data-testid="stSidebar"] .stButton > button p,
        section[data-testid="stSidebar"] .stButton > button span {{
            color: inherit !important;
            font-weight: 600 !important;
        }}

        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0,1fr));
            gap: 14px;
            margin: 8px 0 6px 0;
        }}
        @media (max-width: 900px) {{
            .kpi-row {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
        }}
        .kpi {{
            padding: 14px 16px;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: linear-gradient(140deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
        }}
        .kpi-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-muted);
            font-weight: 600;
        }}
        .kpi-value {{
            font-family: 'Sora', sans-serif;
            font-size: 1.55rem;
            font-weight: 700;
            color: var(--text-strong);
            margin-top: 6px;
        }}
        .kpi-accent {{ color: var(--teal); }}

        .footer-note {{
            margin-top: 22px;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.82rem;
        }}
        .footer-note b {{ color: var(--text-default); font-weight: 600; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def _safe_switch(page_path: str) -> None:
    """Tenta navegar para uma página com mensagem amigável se falhar."""
    try:
        st.switch_page(page_path)
    except Exception as e:  # noqa: BLE001
        st.error(
            f"Não foi possível abrir `{page_path}`.\n\n"
            "**Solução:** pare o Streamlit no terminal (Ctrl+C) e rode "
            "`streamlit run app.py` de novo. O Streamlit cacheia a lista "
            "de páginas no startup; renomear arquivos exige reinício."
        )
        with st.expander("Detalhes técnicos"):
            st.code(str(e))

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏢 Dashboard de Análise Geral")
    st.caption("Central de setores — Grupo")
    st.markdown("---")
    st.markdown("**Navegação rápida**")
    # Botões com st.switch_page evitam o bug do st.page_link em algumas
    # versões do Streamlit quando os caminhos contêm emojis.
    if st.button("📦  Produtos Faturados", key="nav_faturados", use_container_width=True):
        _safe_switch("pages/1_Produtos_Faturados.py")
    if st.button("🏭  Produção Geral", key="nav_producao", use_container_width=True):
        _safe_switch("pages/2_Producao_Geral.py")
    if st.button("✂️  Controle de Corte", key="nav_corte", use_container_width=True):
        _safe_switch("pages/3_Controle_de_Corte.py")
    st.markdown("---")
    st.caption(
        f"⏱️ Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        "Use o menu lateral ou os cards abaixo para navegar."
    )

# ──────────────────────────────────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">Central de Análises</div>
        <h1 class="hero-title">Dashboard de <span class="accent"> Análise Geral</span></h1>
        <p class="hero-subtitle">
            Acesse, em um só lugar, todos os painéis setoriais da operação.
            Escolha o setor para visualizar produção, faturamento e desempenho em tempo real.
        </p>
        <div class="hero-meta">
            <span class="hero-pill"><b>3</b> &nbsp;Setores integrados</span>
            <span class="hero-pill"><b>Real-time</b> &nbsp;Atualização contínua</span>
            <span class="hero-pill"><b>Multi-empresa</b> &nbsp;Grupo consolidado</span>
        </div>
    </div>
    <div class="divider"></div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="kpi-row">
        <div class="kpi">
            <div class="kpi-label">Setores</div>
            <div class="kpi-value"><span class="kpi-accent">3</span> ativos</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Empresas Monitoradas</div>
            <div class="kpi-value">7+</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Fonte de Dados</div>
            <div class="kpi-value">Google Sheets</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Cache</div>
            <div class="kpi-value">Automático</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# CARDS DE SETORES (CENTRALIZADOS)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align: center; margin-top: 32px; margin-bottom: 8px;">
        <h2 style="font-family: 'Sora', sans-serif; font-size: 1.45rem; font-weight: 700; 
                   color: var(--text-strong); margin: 0 0 8px 0;">
            Setores Disponíveis
        </h2>
        <p style="color: var(--text-muted); margin: 0 0 24px 0; font-size: 0.98rem;">
            Clique em um cartão para abrir o dashboard do setor
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Layout centralizado com wrapper HTML
st.markdown(
    """
    <div style="
        display: flex;
        justify-content: center;
        align-items: flex-start;
        gap: 20px;
        flex-wrap: wrap;
        width: 100%;
        margin: 0 auto;
        padding: 0 20px;
    ">
    """,
    unsafe_allow_html=True,
)

# Criar cards em colunas individuais, cada uma centralizada
for sector in SECTORS:
    st.markdown(
        f"""
        <div style="flex: 0 1 calc(33.333% - 14px); min-width: 280px; max-width: 360px;">
        """,
        unsafe_allow_html=True,
    )
    
    tags_html = "".join(
        f'<span class="sector-tag">{tag}</span>' for tag in sector["tags"]
    )
    
    st.markdown(
        f"""
        <div class="sector-card" style="
            --card-a: {sector['color_a']};
            --card-b: {sector['color_b']};
            --card-accent: {sector['accent']};
        ">
            <div class="sector-icon-wrap">{sector['icon']}</div>
            <div class="sector-subtitle">{sector['subtitle']}</div>
            <h3 class="sector-title">{sector['title']}</h3>
            <p class="sector-desc">{sector['description']}</p>
            <div class="sector-tags">{tags_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if st.button(
        f"Abrir {sector['title']}  →",
        key=f"open_{sector['key']}",
        use_container_width=True,
    ):
        _safe_switch(sector["page_path"])
    
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# RODAPÉ
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="footer-note">
    <b>Análise de Dados & Programação</b> ·
        Zanattex - Industria e Comercio de Confeccoes Ltda<br>
    </div>
    """,
    unsafe_allow_html=True,
)
