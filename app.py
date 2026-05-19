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
    page_title="Central de Análise Zanattex | Setores",
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

# ──────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ──────────────────────────────────────────────────────────────────────────────
SENHA_USUARIO = "0102"
SENHA_ADMIN = "adm0102"

def verificar_acesso(senha: str) -> str:
    """Verifica a senha e retorna o nível de acesso: 'admin', 'usuario' ou 'negado'."""
    if senha == SENHA_ADMIN:
        return "admin"
    elif senha == SENHA_USUARIO:
        return "usuario"
    else:
        return "negado"

def pode_acessar(card_key: str, nivel_acesso: str) -> bool:
    """Verifica se o usuário pode acessar um card específico."""
    if nivel_acesso == "admin":
        return True
    if nivel_acesso == "usuario":
        # Usuário normal não pode acessar Faturamento
        return card_key != "faturados"
    return False

# Inicializar session_state de autenticação
if "auth_nivel" not in st.session_state:
    st.session_state.auth_nivel = ""
if "auth_target" not in st.session_state:
    st.session_state.auth_target = None  # key do setor que pediu acesso

SECTORS = [
    {
        "key": "apontador_gut",
        "title": "Central de Controle GUT",
        "subtitle": "Apontador Zanattex — Controle de eficiência",
        "description": (
            "Painel de acompanhamento em tempo real do GUT (Giattex) com dados de "
            "eficiência, horas, operadores e performance. Controle operacional integrado."
        ),
        "icon": "⏱️",
        "external_url": "https://www.appsheet.com/start/6ab5d5b4-6ceb-4641-be36-26a273f1f303#appName=ApontadorZanattex-819603934&group=%5B%7B\"Column\"%3A\"Data\"%2C\"Order\"%3A\"Descending\"%7D%5D&page=fastTable&sort=%5B%7B\"Column\"%3A\"Hora\"%2C\"Order\"%3A\"Descending\"%7D%2C%7B\"Column\"%3A\"Eficiência\"%2C\"Order\"%3A\"Descending\"%7D%5D&table=GIATTEX&view=GIATTEX",
        "color_a": "#1F4A5A",
        "color_b": "#2E8B9E",
        "accent":  "#26D0CE",
        "tags": ["GUT", "Eficiência", "Real-time"],
        "requires_auth": True,
    },
    {
        "key": "analise_dados_gut",
        "title": "Análise de Dados GUT",
        "subtitle": "Dashboard analítico — Insights e tendências",
        "description": (
            "Análise completa dos dados do GUT em formato de dashboard interativo. "
            "Visualize tendências, indicadores de desempenho e insights estratégicos."
        ),
        "icon": "📈",
        "external_url": "https://datastudio.google.com/u/0/reporting/720db0c0-be65-40d9-ae9d-7627741385ce/page/p_si214uowdd",
        "color_a": "#3D2817",
        "color_b": "#D97706",
        "accent":  "#FBBF24",
        "tags": ["Análise", "GUT", "Insights"],
        "requires_auth": True,
    },
    {
        "key": "faturados",
        "title": "Análise de Faturamento",
        "subtitle": "Análise comercial e faturamento",
        "description": (
            "Visão completa de produtos faturados, ranking de clientes, "
            "evolução de receita, Acompanhamento comercial para tomada de decisões estratégicas."
        ),
        "icon": "📊",
        "page_path": "pages/1_Produtos_Faturados.py",
        "color_a": "#1D3557",
        "color_b": "#0C6E74",
        "accent":  "#E76F51",
        "tags": ["Comercial", "Receita", "Clientes"],
        "requires_auth": True,
    },
    {
        "key": "producao",
        "title": "Análise de Produção",
        "subtitle": "Multi-empresas em tempo real",
        "description": (
            "Acompanhamento da produção de todas as empresas do grupo "
            "(Burdays, Camesa, Niazitex, Cortex, Sultan, Decor, Marcelino) "
            "com metas e evolução diária. "
        ),
        "icon": "🏭",
        "page_path": "pages/2_Producao_Geral.py",
        "color_a": "#0F4C5C",
        "color_b": "#4ECDC4",
        "accent":  "#FFA726",
        "tags": ["Produção", "Multi-empresa", "Metas"],
        "requires_auth": True,
    },
    {
        "key": "corte",
        "title": "Análise de Corte",
        "subtitle": "Mantas/ Lençol — estações e desempenho",
        "description": (
            "Painel operacional dos setores de corte com metas "
            "diárias por estação, produção, "
            "OPs, Cores, indicadores por operador "
            "e Ranking de desempenho."
        ),
        "icon": "✂️",
        "page_path": "pages/3_Controle_de_Corte.py",
        "color_a": "#1F3A93",
        "color_b": "#45B7D1",
        "accent":  "#4ECDC4",
        "tags": ["Operação", "Corte", "Metas diárias"],
        "requires_auth": True,
    },

    {
        "key": "Almoxarifado",
        "title": "Análise de Almoxarife",
        "subtitle": "Insumos/ Materiais — controle e desempenho",
        "description": (
            "Em Breve..."
        ),
        "icon": "📦",
        "page_path": "EM BREVE!",
        "color_a": "#1F3A93",
        "color_b": "#3974E2",
        "accent":  "#74C4BE",
        "tags": ["Operação", "Almoxarifado", "Controle"],
        "requires_auth": False,
    },

    {
        "key": "Inventario",
        "title": "Análise de Inventário",
        "subtitle": "Inventário — controle e desempenho de consumo",
        "description": (
            "Em Breve..."
        ),
        "icon": "📦",
        "page_path": "EM BREVE!",
        "color_a": "#1F3A93",
        "color_b": "#4EB9C3",
        "accent":  "#74C4BE",
        "tags": ["Mapa", "Inventário", "Estoque"],
        "requires_auth": False,
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

        /* Faz as colunas do Streamlit se esticarem igualmente na mesma linha */
        [data-testid="stHorizontalBlock"] {{
            align-items: stretch !important;
        }}
        [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {{
            height: 100%;
            display: flex;
            flex-direction: column;
        }}
        [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stMarkdownContainer"] {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stMarkdownContainer"] > div {{
            height: 100%;
        }}

        .sector-card {{
            position: relative;
            border-radius: 14px;
            padding: 14px 16px 12px 16px;
            background: linear-gradient(160deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%);
            border: 1px solid var(--border);
            overflow: hidden;
            height: 100%;
            box-sizing: border-box;
            transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
        }}
        .sector-card::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(160deg, var(--card-a) 0%, var(--card-b) 100%);
            opacity: 0.16;
            transition: opacity 0.22s ease;
            pointer-events: none;
        }}
        .sector-card:hover {{
            transform: translateY(-3px);
            border-color: var(--card-accent, var(--border-hover));
            box-shadow: 0 10px 24px rgba(0,0,0,0.40),
                        0 0 0 1px var(--card-accent, var(--border-hover));
        }}
        .sector-card:hover::before {{ opacity: 0.28; }}

        .sector-card-inner {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            height: 100%;
        }}
        .sector-icon-wrap {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            width: 42px;
            height: 42px;
            border-radius: 11px;
            background: linear-gradient(135deg, var(--card-a), var(--card-b));
            font-size: 1.25rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.30);
            margin-top: 2px;
        }}
        .sector-card-body {{
            flex: 1;
            min-width: 0;
        }}
        .sector-title {{
            font-family: 'Sora', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-strong);
            margin: 0 0 1px 0;
            line-height: 1.2;
        }}
        .sector-subtitle {{
            font-size: 0.70rem;
            color: var(--card-accent);
            margin: 0 0 6px 0;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .sector-desc {{
            color: var(--text-muted);
            font-size: 0.80rem;
            line-height: 1.45;
            margin-bottom: 8px;
        }}
        .sector-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-bottom: 0;
        }}
        .sector-tag {{
            font-size: 0.65rem;
            padding: 2px 8px;
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
            font-size: 0.82rem !important;
            border-radius: 10px !important;
            padding: 7px 12px !important;
            border: 1px solid rgba(78,205,196,0.55) !important;
            box-shadow: 0 4px 14px rgba(78,205,196,0.22) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease !important;
            width: 100% !important;
            margin-top: 6px !important;
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
    st.markdown("### 🏢 Central de Análise Zanattex")
    st.caption("setores — Grupo")
    
    # Status de autenticação
    if st.session_state.auth_nivel:
        nivel_label = "👑 Admin" if st.session_state.auth_nivel == "admin" else "👤 Usuário"
        st.success(f"{nivel_label} · Autenticado")
        if st.button("🚪 Fazer Logout", use_container_width=True):
            st.session_state.auth_nivel = ""
            st.rerun()
    else:
        st.info("🔓 Não autenticado")
    
    st.markdown("---")
    st.markdown("**Navegação rápida**")
    st.link_button("⏱️ Central de Controle GUT", "https://www.appsheet.com/start/6ab5d5b4-6ceb-4641-be36-26a273f1f303#appName=ApontadorZanattex-819603934&group=%5B%7B\"Column\"%3A\"Data\"%2C\"Order\"%3A\"Descending\"%7D%5D&page=fastTable&sort=%5B%7B\"Column\"%3A\"Hora\"%2C\"Order\"%3A\"Descending\"%7D%2C%7B\"Column\"%3A\"Eficiência\"%2C\"Order\"%3A\"Descending\"%7D%5D&table=GIATTEX&view=GIATTEX", use_container_width=True)
    st.link_button("📈 Análise de Dados GUT", "https://datastudio.google.com/u/0/reporting/720db0c0-be65-40d9-ae9d-7627741385ce/page/p_si214uowdd", use_container_width=True)
    st.markdown("---")

    _nav_nivel = st.session_state.auth_nivel
    if _nav_nivel:
        # Faturamento só para admin
        if _nav_nivel == "admin":
            if st.button("📦 Faturamento", key="nav_faturados", use_container_width=True):
                _safe_switch("pages/1_Produtos_Faturados.py")
        else:
            st.button("📦 Faturamento 🔒", key="nav_faturados",
                      use_container_width=True, disabled=True)
        if st.button("🏭 Produção", key="nav_producao", use_container_width=True):
            _safe_switch("pages/2_Producao_Geral.py")
        if st.button("✂️ Corte", key="nav_corte", use_container_width=True):
            _safe_switch("pages/3_Controle_de_Corte.py")
    else:
        st.caption("🔒 Faça login para acessar os dashboards.")

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
        <div class="hero-badge">Grupo Zanattex</div>
        <h1 class="hero-title">Central de Análise <span class="accent"> Zanattex</span></h1>
        <p class="hero-subtitle">
            Acesse, em um só lugar, todos os painéis setoriais da operação.
            Escolha o setor para visualizar produção, faturamento e desempenho em tempo real.
        </p>
        <div class="hero-meta">
            <span class="hero-pill"><b>5</b> &nbsp;Painéis integrados</span>
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
            <div class="kpi-label">Painéis</div>
            <div class="kpi-value"><span class="kpi-accent">5</span> ativos</div>
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

# ──────────────────────────────────────────────────────────────────────────────
# CARDS DE SETORES — sempre visíveis
# ──────────────────────────────────────────────────────────────────────────────
nivel_acesso = st.session_state.auth_nivel
COLS_PER_ROW = 3
rows = [SECTORS[i : i + COLS_PER_ROW] for i in range(0, len(SECTORS), COLS_PER_ROW)]

for row_sectors in rows:
    padding = COLS_PER_ROW - len(row_sectors)
    cols = st.columns(COLS_PER_ROW, gap="medium")

    for idx, (col, sector) in enumerate(zip(cols, row_sectors)):
        with col:
            # Faturamento bloqueado para nível usuário (libera só com admin)
            locked = sector['key'] == 'faturados' and nivel_acesso not in ('', 'admin')

            tags_html = "".join(
                f'<span class="sector-tag">{tag}</span>' for tag in sector["tags"]
            )
            lock_badge = (
                '<div style="position:absolute;top:10px;right:12px;'
                'background:rgba(231,111,81,0.18);border:1px solid rgba(231,111,81,0.45);'
                'border-radius:6px;padding:2px 8px;font-size:.63rem;'
                'color:#E76F51;font-weight:700;letter-spacing:.04em">🔒 ADMIN</div>'
            ) if locked else ""

            card_style = (
                f"--card-a:{sector['color_a']};--card-b:{sector['color_b']};"
                f"--card-accent:{sector['accent']};"
                + ("opacity:.45;pointer-events:none;" if locked else "")
            )

            card_html = (
                f'<div class="sector-card" style="{card_style}">'
                f'{lock_badge}'
                f'<div class="sector-card-inner">'
                f'<div class="sector-icon-wrap">{sector["icon"]}</div>'
                f'<div class="sector-card-body">'
                f'<div class="sector-subtitle">{sector["subtitle"]}</div>'
                f'<h3 class="sector-title">{sector["title"]}</h3>'
                f'<p class="sector-desc">{sector["description"]}</p>'
                f'<div class="sector-tags">{tags_html}</div>'
                f'</div></div></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            # ── Botão / form inline do card ──────────────────────────────
            if locked:
                st.button("🔒 Acesso restrito — Admin",
                          key=f"open_{sector['key']}",
                          use_container_width=True, disabled=True)

            elif nivel_acesso:
                # Já autenticado — abre direto
                if "external_url" in sector:
                    st.link_button(f"Abrir {sector['title']}  →",
                                   sector["external_url"], use_container_width=True)
                else:
                    if st.button(f"Abrir {sector['title']}  →",
                                 key=f"open_{sector['key']}", use_container_width=True):
                        _safe_switch(sector["page_path"])

            elif st.session_state.auth_target == sector['key']:
                # Form de senha inline, direto sob o card clicado
                senha_input = st.text_input(
                    "Senha", type="password",
                    key=f"senha_{sector['key']}",
                    placeholder="Digite a senha...",
                    label_visibility="collapsed",
                )
                col_ok, col_x = st.columns([4, 1])
                with col_ok:
                    if st.button("Entrar  →", key=f"ok_{sector['key']}",
                                 use_container_width=True):
                        if not senha_input:
                            st.warning("⚠️ Digite a senha.")
                        else:
                            nivel = verificar_acesso(senha_input)
                            if nivel == "negado":
                                st.error("❌ Senha incorreta.")
                            elif sector['key'] == 'faturados' and nivel != 'admin':
                                st.error("🔒 Faturamento requer senha Admin.")
                            else:
                                st.session_state.auth_nivel = nivel
                                st.session_state.auth_target = None
                                if "page_path" in sector:
                                    _safe_switch(sector["page_path"])
                                else:
                                    st.rerun()
                with col_x:
                    if st.button("✕", key=f"cancel_{sector['key']}",
                                 use_container_width=True):
                        st.session_state.auth_target = None
                        st.rerun()

            else:
                # Não autenticado — ao clicar, abre o form inline
                if st.button(f"🔒 Abrir {sector['title']}  →",
                             key=f"open_{sector['key']}", use_container_width=True):
                    st.session_state.auth_target = sector['key']
                    st.rerun()

    for i in range(padding):
        with cols[len(row_sectors) + i]:
            st.empty()

# ──────────────────────────────────────────────────────────────────────────────
# RODAPÉ
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div class="footer-note">
    <b>Análise de Dados & Programação</b> ·
        Zanattex - Industria e Comercio de Confeccoes Ltda<br>
    </div>
    """,
    unsafe_allow_html=True,
)
