# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import locale
import io
import os
import sys
import urllib.request
from urllib.error import HTTPError, URLError

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from config import GOOGLE_SHEETS_ID, GOOGLE_SHEETS_GID, METAS, META_TOTAL, CACHE_TTL
except ImportError:
    GOOGLE_SHEETS_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
    GOOGLE_SHEETS_GID = None
    METAS = {'MAQUINA': 7000, 'MESA 1': 4000, 'MESA 2': 3000}
    META_TOTAL = sum(METAS.values())
    CACHE_TTL = 60

# =====================================================================
# CONFIG IACANGA (Setor 2 — Mantas Giattex)
# =====================================================================
GOOGLE_SHEETS_ID_IACANGA = "14OFOAxrV_DkyrwG6KG8NZT-PeXUV4jezPrPO90rh1DU"
GOOGLE_SHEETS_GID_IACANGA = "1362699684"

# Colunas obrigatórias usadas pelo dashboard do Iacanga
COLUNAS_USADAS_IACANGA = [
    'DATA', 'OP', 'COR', 'QUANTIDADE',
    'ESTAÇÃO DE CORTE', 'PRODUTO', 'TAMANHO',
]

# Metas variáveis por (grupo de estação, tamanho de manta)
METAS_POR_TAMANHO = {
    "MAQUINA": {"SOLTEIRO": 8000, "CASAL": 7000, "QUEEN": 5500, "KING": 4500},
    "MESA":    {"SOLTEIRO": 3500, "CASAL": 3000, "QUEEN": 2600, "KING": 2300},
    "BURDAY":  {"SOLTEIRO": 9000, "CASAL": 9000, "QUEEN": 9000, "KING": 9000, "_DEFAULT": 9000},
}


# =====================================================================
# HELPERS IACANGA — normalização + meta variável
# =====================================================================
def _norm_iacanga(texto: str) -> str:
    """Normaliza texto: trim + upper + remove acentos."""
    if pd.isna(texto):
        return ""
    s = str(texto).strip().upper()
    repl = {
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
        'É': 'E', 'Ê': 'E', 'È': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ò': 'O', 'Ö': 'O',
        'Ú': 'U', 'Û': 'U', 'Ù': 'U', 'Ü': 'U', 'Ç': 'C',
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def identifica_grupo_estacao_iacanga(estacao: str) -> str:
    """Mapeia o nome livre da estação -> grupo de meta (MAQUINA/MESA/BURDAY)."""
    s = _norm_iacanga(estacao)
    if "BURDAY" in s:
        return "BURDAY"
    if "MAQUINA" in s or s.startswith("MAQ"):
        return "MAQUINA"
    if "MESA" in s:
        return "MESA"
    return "OUTRO"


def normaliza_tamanho_iacanga(tam: str) -> str:
    """Normaliza tamanho -> SOLTEIRO/CASAL/QUEEN/KING (ou string normalizada)."""
    s = _norm_iacanga(tam)
    if "SOLT" in s:
        return "SOLTEIRO"
    if "CASAL" in s or "DUPLO" in s:
        return "CASAL"
    if "QUEEN" in s or s == "Q":
        return "QUEEN"
    if "KING" in s or s == "K":
        return "KING"
    return s


def meta_por_registro_iacanga(estacao: str, tamanho: str) -> float:
    """Meta diária para um par (estação, tamanho)."""
    grupo = identifica_grupo_estacao_iacanga(estacao)
    tam = normaliza_tamanho_iacanga(tamanho)
    if grupo not in METAS_POR_TAMANHO:
        return 0
    metas_g = METAS_POR_TAMANHO[grupo]
    return metas_g.get(tam, metas_g.get("_DEFAULT", 0))


def meta_ponderada_iacanga(df_subset: pd.DataFrame) -> float:
    """Meta ponderada pelo mix real de tamanhos cortados no subset."""
    if df_subset.empty:
        return 0.0
    total = df_subset['QUANTIDADE'].sum()
    if total <= 0:
        return 0.0
    soma = 0.0
    for (est, tam), grupo in df_subset.groupby(['ESTACAO', 'TAMANHO']):
        qtd = grupo['QUANTIDADE'].sum()
        soma += meta_por_registro_iacanga(est, tam) * (qtd / total)
    return soma


def meta_diaria_por_estacao_iacanga(df_subset: pd.DataFrame, estacao: str) -> float:
    """Meta ponderada restrita a uma estação específica."""
    return meta_ponderada_iacanga(df_subset[df_subset['ESTACAO'] == estacao])


def calcular_meta_total_ponderada_iacanga(df_subset: pd.DataFrame) -> float:
    """Soma das metas ponderadas de cada estação presente no subset."""
    if df_subset.empty:
        return 0.0
    total = 0.0
    for est in df_subset['ESTACAO'].unique():
        total += meta_diaria_por_estacao_iacanga(df_subset, est)
    return total


try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

st.set_page_config(
    page_title="Controle de Corte",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# CSS
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    .stApp {
        background:
            radial-gradient(circle at 15% 15%, rgba(78,205,196,0.08) 0%, transparent 42%),
            radial-gradient(circle at 85% 20%, rgba(69,183,209,0.07) 0%, transparent 42%),
            linear-gradient(180deg, #0B0E14 0%, #0E1117 55%, #11151F 100%);
        color: #E0E0E0;
        font-family: 'Space Grotesk', sans-serif;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0C0F16 0%, #141925 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.10);
    }
    section[data-testid="stSidebar"] * {
        color: #E0E0E0 !important;
        font-family: 'Space Grotesk', sans-serif;
    }

    /* ---- PAGE HEADER ---- */
    .page-header {
        text-align: center;
        padding: 40px 12px 8px 12px;
    }
    .page-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 999px;
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #4ECDC4;
        background: rgba(78,205,196,0.10);
        border: 1px solid rgba(78,205,196,0.30);
        font-weight: 600;
        margin-bottom: 20px;
    }
    .page-title {
        font-family: 'Sora', sans-serif;
        font-size: 2.7rem;
        font-weight: 800;
        line-height: 1.05;
        margin: 0 0 14px 0;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }
    .page-title .accent {
        background: linear-gradient(90deg, #4ECDC4, #7CDDD6 45%, #45B7D1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .page-subtitle {
        font-size: 1.05rem;
        color: #A0A0A0;
        max-width: 580px;
        margin: 0 auto 10px auto;
        line-height: 1.55;
    }
    .page-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.10), transparent);
        margin: 28px 0 36px 0;
    }

    /* ---- REGION / PRODUCT CARDS ---- */
    .region-card {
        position: relative;
        border-radius: 20px;
        padding: 32px 26px 26px 26px;
        background: linear-gradient(160deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.10);
        overflow: hidden;
        text-align: center;
        min-height: 320px;
        transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
        margin-bottom: 4px;
    }
    .region-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(160deg, var(--rc-a) 0%, var(--rc-b) 100%);
        opacity: 0.16;
        transition: opacity 0.25s ease;
        pointer-events: none;
    }
    .region-card:hover {
        transform: translateY(-5px);
        border-color: var(--rc-accent, rgba(78,205,196,0.55));
        box-shadow: 0 18px 44px rgba(0,0,0,0.55), 0 0 0 1px var(--rc-accent, rgba(78,205,196,0.4));
    }
    .region-card:hover::before { opacity: 0.28; }
    .region-card.disabled {
        opacity: 0.55;
    }
    .region-card.disabled:hover {
        transform: none !important;
        border-color: rgba(255,255,255,0.10) !important;
        box-shadow: none !important;
    }
    .rc-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 72px;
        height: 72px;
        border-radius: 18px;
        background: linear-gradient(135deg, var(--rc-a), var(--rc-b));
        font-size: 2.2rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.40);
        margin: 0 auto 20px auto;
    }
    .rc-label {
        font-size: 0.76rem;
        color: var(--rc-accent, #4ECDC4);
        font-weight: 600;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .rc-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.65rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0 0 12px 0;
    }
    .rc-desc {
        color: #C0C0C0;
        font-size: 0.93rem;
        line-height: 1.57;
        margin-bottom: 18px;
    }
    .rc-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        justify-content: center;
    }
    .rc-tag {
        font-size: 0.72rem;
        padding: 4px 11px;
        border-radius: 999px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.13);
        color: #A0A0A0;
    }
    .rc-tag-soon {
        font-size: 0.72rem;
        padding: 4px 11px;
        border-radius: 999px;
        background: rgba(255,167,38,0.10);
        border: 1px solid rgba(255,167,38,0.32);
        color: #FFA726;
    }

    /* ---- BREADCRUMB ---- */
    .breadcrumb {
        font-size: 0.85rem;
        color: #606878;
        margin-bottom: 6px;
        padding: 0 2px;
    }
    .breadcrumb .bc-sep { margin: 0 6px; color: rgba(255,255,255,0.18); }
    .breadcrumb .bc-active { color: #4ECDC4; font-weight: 600; }
    .breadcrumb .bc-link { color: #7A8899; }

    /* ---- DASHBOARD (existing styles kept) ---- */
    .dash-header {
        font-family: 'Sora', sans-serif;
        font-size: 1.9rem;
        font-weight: 800;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 4px;
    }
    .dash-sub {
        font-size: 0.95rem;
        color: #A0A0A0;
        text-align: center;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; font-weight: 600; }
    div[data-testid="stMetric"] {
        background-color: rgba(128,128,128,0.08);
        border: 1px solid rgba(128,128,128,0.15);
        border-radius: 10px;
        padding: 12px 16px;
    }

    /* ---- BUTTONS ---- */
    .stButton > button {
        background: linear-gradient(135deg, #4ECDC4, #2BB3AB) !important;
        color: #0B0E14 !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        border: 1px solid rgba(78,205,196,0.55) !important;
        box-shadow: 0 6px 18px rgba(78,205,196,0.22) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 26px rgba(78,205,196,0.38) !important;
    }
    .stButton > button:active, .stButton > button:focus {
        background: linear-gradient(135deg, #4ECDC4, #2BB3AB) !important;
        color: #0B0E14 !important;
        outline: none !important;
    }
    .stButton > button p, .stButton > button span, .stButton > button div {
        color: #0B0E14 !important;
        font-weight: 700 !important;
    }
    .stButton > button:disabled {
        background: rgba(255,255,255,0.05) !important;
        color: #555 !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, rgba(78,205,196,0.16), rgba(78,205,196,0.07)) !important;
        color: #4ECDC4 !important;
        border: 1px solid rgba(78,205,196,0.35) !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, rgba(78,205,196,0.28), rgba(78,205,196,0.14)) !important;
        border-color: #4ECDC4 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
    }
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stButton > button span {
        color: inherit !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# DATA LOADING
# =====================================================================
def baixar_csv_google_sheets():
    headers = {'User-Agent': 'Mozilla/5.0'}
    urls_padrao = [
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq?tqx=out:csv",
    ]
    gids_fallback = ["206085601", "0"]
    urls_fallback = []
    for gid in gids_fallback:
        urls_fallback.extend([
            f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv&gid={gid}",
            f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq?tqx=out:csv&gid={gid}",
        ])
    todas_urls = urls_padrao + urls_fallback
    ultimo_erro = None
    for url in todas_urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                conteudo = response.read().decode('utf-8')
                if conteudo.strip():
                    return io.StringIO(conteudo)
        except (HTTPError, URLError, TimeoutError) as erro:
            ultimo_erro = erro
            continue
    raise RuntimeError(f"Falha ao baixar CSV do Google Sheets. Último erro: {ultimo_erro}")


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados():
    csv_data = baixar_csv_google_sheets()
    df_corte = pd.read_csv(csv_data, header=0)
    df_corte.columns = df_corte.columns.str.strip()
    df_corte = df_corte.drop(
        columns=[col for col in df_corte.columns if 'Unnamed' in col or 'Coluna' in col],
        errors='ignore'
    )
    colunas_obrigatorias = ['DATA', 'OP', 'COR', 'QUANTIDADE', 'ESTAÇÃO DE CORTE', 'PRODUTO']
    colunas_faltantes = [c for c in colunas_obrigatorias if c not in df_corte.columns]
    if colunas_faltantes:
        raise KeyError(
            f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}. "
            f"Disponíveis: {', '.join(df_corte.columns.tolist())}"
        )
    data_raw = df_corte['DATA'].astype(str).str.split(' ').str[0].str.strip()
    df_corte['DATA'] = pd.to_datetime(data_raw, format='mixed', dayfirst=True, errors='coerce')
    df_corte = df_corte[df_corte['DATA'] <= pd.Timestamp.now()]
    df_corte = df_corte.dropna(subset=['DATA', 'OP'])
    df_corte = df_corte[df_corte['OP'].astype(str).str.strip() != '']
    df_corte['OP'] = df_corte['OP'].astype(str).str.strip()
    df_corte['COR'] = df_corte['COR'].astype(str).str.strip().str.upper()
    df_corte['QUANTIDADE'] = pd.to_numeric(df_corte['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
    df_corte['ESTACAO'] = df_corte['ESTAÇÃO DE CORTE'].astype(str).str.strip()
    df_corte['PRODUTO'] = df_corte['PRODUTO'].astype(str).str.strip()
    df_corte['SEMANA'] = df_corte['DATA'].dt.isocalendar().week.astype(int)
    df_corte['MES'] = df_corte['DATA'].dt.month
    df_corte['DIA_SEMANA'] = df_corte['DATA'].dt.day_name()
    return df_corte


# =====================================================================
# DATA LOADING — IACANGA (planilha própria)
# =====================================================================
def baixar_csv_google_sheets_iacanga():
    headers = {'User-Agent': 'Mozilla/5.0'}
    urls = [
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID_IACANGA}/export?format=csv&gid={GOOGLE_SHEETS_GID_IACANGA}",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID_IACANGA}/gviz/tq?tqx=out:csv&gid={GOOGLE_SHEETS_GID_IACANGA}",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID_IACANGA}/export?format=csv",
    ]
    ultimo_erro = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                conteudo = response.read().decode('utf-8')
                if conteudo.strip():
                    return io.StringIO(conteudo)
        except (HTTPError, URLError, TimeoutError) as erro:
            ultimo_erro = erro
            continue
    raise RuntimeError(f"Falha ao baixar CSV do Iacanga. Último erro: {ultimo_erro}")


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados_iacanga():
    csv_data = baixar_csv_google_sheets_iacanga()
    df_full = pd.read_csv(csv_data, header=0)
    df_full.columns = df_full.columns.str.strip()

    faltantes = [c for c in COLUNAS_USADAS_IACANGA if c not in df_full.columns]
    if faltantes:
        raise KeyError(
            f"Colunas obrigatórias faltando: {', '.join(faltantes)}. "
            f"Disponíveis: {', '.join(df_full.columns.tolist())}"
        )

    # Mantém apenas as colunas usadas (descarta CLIENTE, PEÇAS OP, KG OP,
    # META DIARIA, DIFERENÇA, QUEBRA TECIDO e quaisquer outras)
    df = df_full[COLUNAS_USADAS_IACANGA].copy()

    data_raw = df['DATA'].astype(str).str.split(' ').str[0].str.strip()
    df['DATA'] = pd.to_datetime(data_raw, format='mixed', dayfirst=True, errors='coerce')
    df = df[df['DATA'] <= pd.Timestamp.now()]
    df = df.dropna(subset=['DATA', 'OP'], how='any')
    df = df[df['OP'].astype(str).str.strip() != '']
    df['OP'] = df['OP'].astype(str).str.strip()
    df['COR'] = df['COR'].astype(str).str.strip().str.upper()
    df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
    df['ESTACAO'] = df['ESTAÇÃO DE CORTE'].astype(str).str.strip()
    df['PRODUTO'] = df['PRODUTO'].astype(str).str.strip()
    df['TAMANHO'] = df['TAMANHO'].astype(str).str.strip().apply(normaliza_tamanho_iacanga)
    df['GRUPO_ESTACAO'] = df['ESTACAO'].apply(identifica_grupo_estacao_iacanga)
    df['SEMANA'] = df['DATA'].dt.isocalendar().week.astype(int)
    df['MES'] = df['DATA'].dt.month
    df['DIA_SEMANA'] = df['DATA'].dt.day_name()
    return df


# =====================================================================
# NAVIGATION HELPERS
# =====================================================================
if 'corte_screen' not in st.session_state:
    st.session_state.corte_screen = 'regions'


def _go(screen: str):
    st.session_state.corte_screen = screen
    st.rerun()


# =====================================================================
# SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown("### ✂️ Controle de Corte")
    st.markdown("---")
    if st.button("🏢  Início", key="sb_home", use_container_width=True):
        st.switch_page("app.py")

    screen = st.session_state.corte_screen
    if screen == 'arealva_products':
        if st.button("← Regiões", key="sb_back1", use_container_width=True):
            _go('regions')
    elif screen == 'arealva_manta':
        if st.button("← Produtos", key="sb_back2", use_container_width=True):
            _go('arealva_products')
        if st.button("← Regiões", key="sb_back3", use_container_width=True):
            _go('regions')
    elif screen == 'iacanga':
        if st.button("← Regiões", key="sb_back4", use_container_width=True):
            _go('regions')

    # Filters injected below only for the dashboard screens
    if screen in ('arealva_manta', 'iacanga'):
        st.markdown("---")
        st.header("🔍 Filtros")


# =====================================================================
# SCREEN — REGION SELECTOR
# =====================================================================
screen = st.session_state.corte_screen

if screen == 'regions':
    st.markdown("""
    <div class="page-header">
        <div class="page-badge">✂️ Controle de Corte</div>
        <h1 class="page-title">Selecione a <span class="accent">Região</span></h1>
        <p class="page-subtitle">Escolha a unidade de corte para acessar o painel de produção</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    _, col_arealva, col_iacanga, _ = st.columns([0.5, 3, 3, 0.5])

    with col_arealva:
        st.markdown("""
        <div class="region-card" style="--rc-a:#1F3A93; --rc-b:#45B7D1; --rc-accent:#4ECDC4;">
            <div class="rc-icon">🏭</div>
            <div class="rc-label">Unidades · Zanattex e Oficina</div>
            <div class="rc-title">Arealva</div>
            <div class="rc-desc">
                Análise das estações de Corte em Arealva (Manta e Lençol). Metas diárias e acompanhamento por OP.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Manta</span>
                <span class="rc-tag">Lençol</span>
                <span class="rc-tag">Estações</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Arealva  →", key="btn_arealva", use_container_width=True):
            _go('arealva_products')

    with col_iacanga:
        st.markdown("""
        <div class="region-card" style="--rc-a:#4A0E8F; --rc-b:#7B2FBE; --rc-accent:#AB47BC;">
            <div class="rc-icon">✂️</div>
            <div class="rc-label">Unidade · Ebel</div>
            <div class="rc-title">Iacanga</div>
            <div class="rc-desc">
                Análise das estações de Corte Giattex. Metas Diarias e acompanhamento por OP. 
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Manta</span>
                <span class="rc-tag">Máquina</span>
                <span class="rc-tag">Mesa</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Iacanga  →", key="btn_iacanga", use_container_width=True):
            _go('iacanga')


# =====================================================================
# SCREEN — AREALVA PRODUCT SELECTOR
# =====================================================================
elif screen == 'arealva_products':
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Arealva</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-top:20px;">
        <div class="page-badge">🏭 Arealva</div>
        <h1 class="page-title">Selecione o <span class="accent">Produto</span></h1>
        <p class="page-subtitle">Escolha o tipo de produto para visualizar o painel de corte</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    _, col_manta, col_lencol, _ = st.columns([0.5, 3, 3, 0.5])

    with col_manta:
        st.markdown("""
        <div class="region-card" style="--rc-a:#0F4C5C; --rc-b:#4ECDC4; --rc-accent:#2CA02C;">
            <div class="rc-icon">🛏️</div>
            <div class="rc-label">Produto · Arealva</div>
            <div class="rc-title">Manta</div>
            <div class="rc-desc">
                Painel completo com metas diárias por estação, acompanhamento
                por OP, indicadores de produção e análise por cor.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Máquina</span>
                <span class="rc-tag">Mesa 1</span>
                <span class="rc-tag">Mesa 2</span>
                <span class="rc-tag">OPs</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_manta", use_container_width=True):
            _go('arealva_manta')

    with col_lencol:
        st.markdown("""
        <div class="region-card disabled" style="--rc-a:#5D4037; --rc-b:#8D6E63; --rc-accent:#FFA726;">
            <div class="rc-icon">📏</div>
            <div class="rc-label">Produto · Arealva</div>
            <div class="rc-title">Lençol</div>
            <div class="rc-desc">
                Dashboard de corte de lençol em desenvolvimento.
                Disponível em breve.
            </div>
            <div class="rc-tags">
                <span class="rc-tag-soon">🚧 Em breve</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.button("Em breve", key="btn_lencol", use_container_width=True, disabled=True)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("← Voltar às Regiões", key="back_to_regions", use_container_width=True):
            _go('regions')


# =====================================================================
# SCREEN — IACANGA — DASHBOARD MANTAS GIATTEX
# =====================================================================
elif screen == 'iacanga':

    # --- Breadcrumb ---
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Iacanga · Mantas Giattex</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Load data ---
    try:
        df_corte_iac = carregar_dados_iacanga()
    except KeyError as e:
        st.error(f"❌ Erro de coluna: {e}")
        st.error("📋 Colunas obrigatórias: DATA, OP, COR, QUANTIDADE, ESTAÇÃO DE CORTE, PRODUTO, TAMANHO")
        st.info("📡 Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link'.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao carregar a planilha do Iacanga: {e}")
        st.info("📡 Verifique se a planilha Google Sheets está acessível.")
        st.stop()

    # --- Sidebar filters ---
    with st.sidebar:
        if not df_corte_iac.empty:
            st.info(
                f"📅 {df_corte_iac['DATA'].min().strftime('%d/%m/%Y')} → "
                f"{df_corte_iac['DATA'].max().strftime('%d/%m/%Y')}"
            )
        if st.sidebar.button("🔄 Limpar Cache", key="iac_clear_cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.sidebar.metric("📊 Registros", f"{len(df_corte_iac):,}")

    df_trabalho_iac = df_corte_iac.copy()

    # Estado isolado (prefixo iac_) para não conflitar com Arealva
    if 'iac_filtro_ops' not in st.session_state:
        st.session_state.iac_filtro_ops = []
    if 'iac_filtro_estacoes' not in st.session_state:
        st.session_state.iac_filtro_estacoes = []
    if 'iac_filtro_produtos' not in st.session_state:
        st.session_state.iac_filtro_produtos = []
    if 'iac_filtro_tamanhos' not in st.session_state:
        st.session_state.iac_filtro_tamanhos = []
    if 'iac_filtro_data_ini' not in st.session_state:
        st.session_state.iac_filtro_data_ini = (
            df_trabalho_iac['DATA'].min().date() if not df_trabalho_iac.empty else None
        )
    if 'iac_filtro_data_fim' not in st.session_state:
        st.session_state.iac_filtro_data_fim = (
            df_trabalho_iac['DATA'].max().date() if not df_trabalho_iac.empty else None
        )

    ops_disp_iac = sorted(df_trabalho_iac['OP'].dropna().unique())
    default_ops_iac = [op for op in st.session_state.iac_filtro_ops if op in ops_disp_iac]
    ops_sel_iac = st.sidebar.multiselect(
        "📋 Filtrar por OP", options=ops_disp_iac, default=default_ops_iac, key="iac_ms_ops"
    )
    st.session_state.iac_filtro_ops = ops_sel_iac

    est_disp_iac = sorted(df_trabalho_iac['ESTACAO'].dropna().unique())
    default_est_iac = [e for e in st.session_state.iac_filtro_estacoes if e in est_disp_iac]
    est_sel_iac = st.sidebar.multiselect(
        "🏭 Filtrar por Estação", options=est_disp_iac, default=default_est_iac, key="iac_ms_est"
    )
    st.session_state.iac_filtro_estacoes = est_sel_iac

    prod_disp_iac = sorted(df_trabalho_iac['PRODUTO'].dropna().unique())
    default_prod_iac = [p for p in st.session_state.iac_filtro_produtos if p in prod_disp_iac]
    prod_sel_iac = st.sidebar.multiselect(
        "📦 Filtrar por Produto", options=prod_disp_iac, default=default_prod_iac, key="iac_ms_prod"
    )
    st.session_state.iac_filtro_produtos = prod_sel_iac

    tam_disp_iac = sorted(df_trabalho_iac['TAMANHO'].dropna().unique())
    default_tam_iac = [t for t in st.session_state.iac_filtro_tamanhos if t in tam_disp_iac]
    tam_sel_iac = st.sidebar.multiselect(
        "📏 Filtrar por Tamanho", options=tam_disp_iac, default=default_tam_iac, key="iac_ms_tam"
    )
    st.session_state.iac_filtro_tamanhos = tam_sel_iac

    st.sidebar.markdown("### 📅 Filtro de Dias")
    if 'iac_filtro_tipo_data' not in st.session_state:
        st.session_state.iac_filtro_tipo_data = "Período"
    tipo_filtro_iac = st.sidebar.radio(
        "Tipo de filtro",
        options=["Um dia", "Período"],
        index=0 if st.session_state.iac_filtro_tipo_data == "Um dia" else 1,
        horizontal=True,
        key="iac_radio_tipo_data",
    )
    st.session_state.iac_filtro_tipo_data = tipo_filtro_iac

    if not df_trabalho_iac.empty:
        data_min_iac = df_trabalho_iac['DATA'].min().date()
        data_max_iac = df_trabalho_iac['DATA'].max().date()
        saved_ini_iac = st.session_state.iac_filtro_data_ini or data_min_iac
        saved_fim_iac = st.session_state.iac_filtro_data_fim or data_max_iac
        saved_ini_iac = max(saved_ini_iac, data_min_iac)
        saved_fim_iac = min(saved_fim_iac, data_max_iac)

        if tipo_filtro_iac == "Um dia":
            dia_iac = st.sidebar.date_input(
                "Data", value=saved_fim_iac,
                min_value=data_min_iac, max_value=data_max_iac,
                format="DD/MM/YYYY", key="iac_di_dia",
            )
            filtro_datas_iac = (dia_iac, dia_iac)
            st.session_state.iac_filtro_data_ini = dia_iac
            st.session_state.iac_filtro_data_fim = dia_iac
        else:
            d_ini_iac = st.sidebar.date_input(
                "Início", value=saved_ini_iac,
                min_value=data_min_iac, max_value=data_max_iac,
                format="DD/MM/YYYY", key="iac_di_ini",
            )
            d_fim_iac = st.sidebar.date_input(
                "Fim", value=saved_fim_iac,
                min_value=data_min_iac, max_value=data_max_iac,
                format="DD/MM/YYYY", key="iac_di_fim",
            )
            filtro_datas_iac = (d_ini_iac, d_fim_iac)
            st.session_state.iac_filtro_data_ini = d_ini_iac
            st.session_state.iac_filtro_data_fim = d_fim_iac
    else:
        filtro_datas_iac = (None, None)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.sidebar.caption(f"Registros carregados: {len(df_trabalho_iac):,}")

    # --- Apply filters ---
    df_filtrado_iac = df_trabalho_iac.copy()
    if ops_sel_iac:
        df_filtrado_iac = df_filtrado_iac[df_filtrado_iac['OP'].isin(ops_sel_iac)]
    if est_sel_iac:
        df_filtrado_iac = df_filtrado_iac[df_filtrado_iac['ESTACAO'].isin(est_sel_iac)]
    if prod_sel_iac:
        df_filtrado_iac = df_filtrado_iac[df_filtrado_iac['PRODUTO'].isin(prod_sel_iac)]
    if tam_sel_iac:
        df_filtrado_iac = df_filtrado_iac[df_filtrado_iac['TAMANHO'].isin(tam_sel_iac)]
    if isinstance(filtro_datas_iac, tuple) and filtro_datas_iac[0] is not None:
        df_filtrado_iac = df_filtrado_iac[
            (df_filtrado_iac['DATA'].dt.date >= filtro_datas_iac[0]) &
            (df_filtrado_iac['DATA'].dt.date <= filtro_datas_iac[1])
        ]

    # --- Meta total ponderada do recorte atual ---
    META_TOTAL_IAC = calcular_meta_total_ponderada_iacanga(df_filtrado_iac)

    # --- Dashboard Header ---
    st.markdown('<div class="dash-header">✂️ Iacanga — Mantas Giattex</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dash-sub">Acompanhamento de produção com meta variável por tamanho '
        '(Solteiro / Casal / Queen / King) e estação (Máquina / Mesa / Burdays)</div>',
        unsafe_allow_html=True,
    )

    # --- Tabs ---
    tab1_iac, tab2_iac, tab3_iac = st.tabs([
        "📊 Visão Geral",
        "📋 Acompanhamento por OP",
        "🏭 Produção por Estação",
    ])

    # =================================================================
    # TAB 1 — VISÃO GERAL
    # =================================================================
    with tab1_iac:
        st.markdown("### 📊 Indicadores Gerais")

        total_pecas_iac = df_filtrado_iac['QUANTIDADE'].sum()
        total_ops_iac = df_filtrado_iac['OP'].nunique()
        total_cores_iac = df_filtrado_iac['COR'].nunique()
        dias_trab_iac = df_filtrado_iac['DATA'].dt.date.nunique()
        media_dia_iac = total_pecas_iac / max(dias_trab_iac, 1)
        pecas_maq_iac = df_filtrado_iac[df_filtrado_iac['GRUPO_ESTACAO'] == 'MAQUINA']['QUANTIDADE'].sum()
        pecas_mesa_iac = df_filtrado_iac[df_filtrado_iac['GRUPO_ESTACAO'] == 'MESA']['QUANTIDADE'].sum()
        pecas_burday_iac = df_filtrado_iac[df_filtrado_iac['GRUPO_ESTACAO'] == 'BURDAY']['QUANTIDADE'].sum()
        delta_media_iac = ((media_dia_iac / META_TOTAL_IAC) - 1) * 100 if META_TOTAL_IAC > 0 else 0

        cols_kpi = st.columns(4)
        cols_kpi[0].metric("✂️ Total de Peças", f"{total_pecas_iac:,.0f}")
        cols_kpi[1].metric("📋 Total de OPs", f"{total_ops_iac}")
        cols_kpi[2].metric("🎨 Cores Diferentes", f"{total_cores_iac}")
        cols_kpi[3].metric("📆 Dias Trabalhados", f"{dias_trab_iac}")

        cols_kpi2 = st.columns(4)
        cols_kpi2[0].metric(
            "⚡ Média Peças/Dia",
            f"{media_dia_iac:,.0f}",
            delta=f"{delta_media_iac:+.1f}% vs Meta {META_TOTAL_IAC:,.0f}",
        )
        cols_kpi2[1].metric("🔧 Máquina", f"{pecas_maq_iac:,.0f}")
        cols_kpi2[2].metric("📐 Mesa", f"{pecas_mesa_iac:,.0f}")
        cols_kpi2[3].metric("🛠️ Burday's", f"{pecas_burday_iac:,.0f}")

        st.markdown("---")
        st.markdown("#### 📈 Produção Diária (Peças)")

        linhas_d = []
        for data_d, grupo_d in df_filtrado_iac.groupby('DATA'):
            linhas_d.append({
                'DATA': data_d,
                'QUANTIDADE': grupo_d['QUANTIDADE'].sum(),
                'META_DIA': calcular_meta_total_ponderada_iacanga(grupo_d),
            })
        prod_diaria_iac = (
            pd.DataFrame(linhas_d).sort_values('DATA') if linhas_d else pd.DataFrame()
        )

        if not prod_diaria_iac.empty:
            prod_diaria_iac['ACIMA_META'] = (
                prod_diaria_iac['QUANTIDADE'] >= prod_diaria_iac['META_DIA']
            )

            fig1_iac = go.Figure()
            df_acima_i = prod_diaria_iac[prod_diaria_iac['ACIMA_META']]
            df_abaixo_i = prod_diaria_iac[~prod_diaria_iac['ACIMA_META']]
            fig1_iac.add_trace(go.Bar(
                x=df_acima_i['DATA'], y=df_acima_i['QUANTIDADE'],
                name='Acima da Meta', marker_color='#2ca02c', opacity=0.85,
            ))
            fig1_iac.add_trace(go.Bar(
                x=df_abaixo_i['DATA'], y=df_abaixo_i['QUANTIDADE'],
                name='Abaixo da Meta', marker_color='#d62728', opacity=0.75,
            ))
            if len(prod_diaria_iac) >= 5:
                prod_diaria_iac['MM5'] = (
                    prod_diaria_iac['QUANTIDADE'].rolling(5, min_periods=1).mean()
                )
                fig1_iac.add_trace(go.Scatter(
                    x=prod_diaria_iac['DATA'], y=prod_diaria_iac['MM5'],
                    name='Tendência (5d)',
                    line=dict(color='#ff7f0e', width=3), mode='lines',
                ))
            # Meta variável diária (acompanha o mix do dia)
            fig1_iac.add_trace(go.Scatter(
                x=prod_diaria_iac['DATA'], y=prod_diaria_iac['META_DIA'],
                name='Meta (variável)',
                line=dict(color='#E0E0E0', width=2, dash='dash'),
                mode='lines',
            ))
            fig1_iac.update_layout(
                height=420, margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0.5, xanchor='center'),
                xaxis_title='', yaxis_title='Peças',
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#E0E0E0',
            )
            fig1_iac.update_xaxes(tickformat='%d/%m/%Y', gridcolor='rgba(255,255,255,0.05)')
            fig1_iac.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig1_iac, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 🏭 Distribuição por Estação")
            dist_est_iac = df_filtrado_iac.groupby('ESTACAO')['QUANTIDADE'].sum().reset_index()
            if not dist_est_iac.empty:
                fig2_iac = px.pie(
                    dist_est_iac, values='QUANTIDADE', names='ESTACAO',
                    color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4,
                )
                fig2_iac.update_traces(textposition='inside', textinfo='percent+label+value')
                fig2_iac.update_layout(
                    height=400, margin=dict(l=20, r=20, t=30, b=20),
                    paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                )
                st.plotly_chart(fig2_iac, use_container_width=True)

        with col_g2:
            st.markdown("#### 📏 Distribuição por Tamanho")
            dist_tam_iac = df_filtrado_iac.groupby('TAMANHO')['QUANTIDADE'].sum().reset_index()
            dist_tam_iac = dist_tam_iac.sort_values('QUANTIDADE', ascending=True)
            if not dist_tam_iac.empty:
                fig_tam = px.bar(
                    dist_tam_iac, y='TAMANHO', x='QUANTIDADE', orientation='h',
                    color='QUANTIDADE', color_continuous_scale='Tealgrn',
                    labels={'QUANTIDADE': 'Peças', 'TAMANHO': 'Tamanho'},
                )
                fig_tam.update_layout(
                    height=400, margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False, coloraxis_showscale=False,
                    paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                fig_tam.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig_tam, use_container_width=True)

        st.markdown("#### 📦 Produção por Produto")
        prod_prod_iac = df_filtrado_iac.groupby('PRODUTO')['QUANTIDADE'].sum().reset_index()
        prod_prod_iac = prod_prod_iac.sort_values('QUANTIDADE', ascending=True).tail(15)
        if not prod_prod_iac.empty:
            fig3_iac = px.bar(
                prod_prod_iac, y='PRODUTO', x='QUANTIDADE', orientation='h',
                color='QUANTIDADE', color_continuous_scale='Blues',
                labels={'QUANTIDADE': 'Peças', 'PRODUTO': 'Produto'},
            )
            fig3_iac.update_layout(
                height=450, margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False, coloraxis_showscale=False,
                paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                plot_bgcolor='rgba(0,0,0,0)',
            )
            fig3_iac.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig3_iac, use_container_width=True)

        st.markdown("#### 🎨 Top 15 Cores Mais Cortadas")
        col_cor_l, col_cor_r = st.columns(2)
        with col_cor_l:
            prod_cor_iac = df_filtrado_iac.groupby('COR')['QUANTIDADE'].sum().reset_index()
            prod_cor_iac = prod_cor_iac.sort_values('QUANTIDADE', ascending=True).tail(15)
            if not prod_cor_iac.empty:
                fig4_iac = px.bar(
                    prod_cor_iac, y='COR', x='QUANTIDADE', orientation='h',
                    color='QUANTIDADE', color_continuous_scale='Viridis',
                    labels={'QUANTIDADE': 'Peças', 'COR': 'Cor'},
                )
                fig4_iac.update_layout(
                    height=400, margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False, coloraxis_showscale=False,
                    paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                fig4_iac.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig4_iac, use_container_width=True)
        with col_cor_r:
            prod_cor_all_i = df_filtrado_iac.groupby('COR')['QUANTIDADE'].sum().reset_index()
            prod_cor_all_i = prod_cor_all_i.sort_values('QUANTIDADE', ascending=False).head(15)
            if not prod_cor_all_i.empty:
                prod_cor_all_i['%'] = (
                    prod_cor_all_i['QUANTIDADE'] / prod_cor_all_i['QUANTIDADE'].sum() * 100
                ).round(1)
                prod_cor_all_i.columns = ['Cor', 'Peças', '% do Total']
                st.dataframe(prod_cor_all_i, use_container_width=True, height=400, hide_index=True)

    # =================================================================
    # TAB 2 — ACOMPANHAMENTO POR OP
    # =================================================================
    with tab2_iac:
        st.markdown("### 📋 Acompanhamento Detalhado por OP")

        resumo_op_iac = df_filtrado_iac.groupby('OP').agg(
            Total_Pecas=('QUANTIDADE', 'sum'),
            Qtd_Cores=('COR', 'nunique'),
            Produto=('PRODUTO', 'first'),
            Tamanho=('TAMANHO', lambda x: ', '.join(sorted(x.dropna().unique()))),
            Data_Inicio=('DATA', 'min'),
            Ultimo_corte=('DATA', 'max'),
            Dias_Producao=('DATA', lambda x: x.dt.date.nunique()),
        ).reset_index().sort_values('Total_Pecas', ascending=False)

        st.markdown("#### Resumo das OPs")
        st.dataframe(
            resumo_op_iac.style.format({
                'Total_Pecas': '{:,.0f}',
                'Data_Inicio': lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '',
                'Ultimo_corte': lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '',
            }),
            use_container_width=True, height=400,
        )
        st.markdown("---")

        if not resumo_op_iac.empty:
            op_det_iac = st.selectbox(
                "🔎 Selecione uma OP para ver detalhes:",
                options=resumo_op_iac['OP'].tolist(),
                key="iac_sel_op",
            )
            if op_det_iac:
                df_op_iac = df_filtrado_iac[df_filtrado_iac['OP'] == op_det_iac]

                col_op1, col_op2, col_op3, col_op4 = st.columns(4)
                col_op1.metric("Peças Total", f"{df_op_iac['QUANTIDADE'].sum():,.0f}")
                col_op2.metric("Cores Cortadas", f"{df_op_iac['COR'].nunique()}")
                col_op3.metric(
                    "Produto",
                    df_op_iac['PRODUTO'].iloc[0] if not df_op_iac.empty else "N/A",
                )
                col_op4.metric(
                    "Tamanho",
                    ', '.join(sorted(df_op_iac['TAMANHO'].dropna().unique()))
                    if not df_op_iac.empty else "N/A",
                )

                st.markdown(f"#### Quantidade por Cor — OP {op_det_iac}")
                cor_op_iac = (
                    df_op_iac.groupby('COR')['QUANTIDADE'].sum()
                    .reset_index().sort_values('QUANTIDADE', ascending=False)
                )
                if not cor_op_iac.empty:
                    fig_op1_iac = px.bar(
                        cor_op_iac, x='COR', y='QUANTIDADE',
                        color='QUANTIDADE', color_continuous_scale='Blues',
                        labels={'COR': 'Cor', 'QUANTIDADE': 'Peças'}, text='QUANTIDADE',
                    )
                    fig_op1_iac.update_traces(textposition='outside')
                    fig_op1_iac.update_layout(
                        height=450, margin=dict(l=20, r=20, t=30, b=20),
                        coloraxis_showscale=False,
                        paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    fig_op1_iac.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
                    st.plotly_chart(fig_op1_iac, use_container_width=True)

                st.markdown(f"#### 📝 Registros Detalhados — OP {op_det_iac}")
                df_op_disp_iac = df_op_iac[
                    ['DATA', 'ESTACAO', 'COR', 'QUANTIDADE', 'PRODUTO', 'TAMANHO']
                ].copy()
                df_op_disp_iac['DATA'] = df_op_disp_iac['DATA'].dt.strftime('%d/%m/%Y')
                st.dataframe(df_op_disp_iac, use_container_width=True, height=300)

    # =================================================================
    # TAB 3 — PRODUÇÃO POR ESTAÇÃO
    # =================================================================
    with tab3_iac:
        st.markdown("### 🏭 Produção por Estação de Corte")

        estacoes_iac = sorted(df_filtrado_iac['ESTACAO'].dropna().unique().tolist())
        palette_iac = px.colors.qualitative.Set2 + px.colors.qualitative.Set3
        cores_est_iac = {est: palette_iac[i % len(palette_iac)] for i, est in enumerate(estacoes_iac)}

        st.markdown("#### 🎯 Progresso vs Meta Diária (Média Peças/Dia)")
        if estacoes_iac:
            n_cols = min(len(estacoes_iac), 3)
            cols_meta = st.columns(n_cols if n_cols > 0 else 1)
            for i, estacao in enumerate(estacoes_iac):
                df_est_b = df_filtrado_iac[df_filtrado_iac['ESTACAO'] == estacao]
                dias_b = df_est_b['DATA'].dt.date.nunique()
                media_b = df_est_b['QUANTIDADE'].sum() / max(dias_b, 1)
                meta_b = meta_diaria_por_estacao_iacanga(df_filtrado_iac, estacao)
                pct = min((media_b / meta_b * 100), 150) if meta_b > 0 else 0
                diff = media_b - meta_b

                if meta_b == 0:
                    cor_prog = '#888'
                    status = '⚠️ SEM META'
                elif pct >= 100:
                    cor_prog = '#2ca02c'
                    status = '✅ META ATINGIDA'
                elif pct >= 80:
                    cor_prog = '#ff7f0e'
                    status = '⚠️ PRÓXIMO DA META'
                else:
                    cor_prog = '#d62728'
                    status = '❌ ABAIXO DA META'

                pct_bar = min(pct, 100)
                with cols_meta[i % n_cols]:
                    card_html = (
                        '<div style="background:#1a1a2e; border-radius:14px; padding:20px; color:white; '
                        'text-align:center; box-shadow:0 3px 12px rgba(0,0,0,0.3); margin-bottom:10px;">'
                        f'<div style="font-size:0.8rem; letter-spacing:1px; color:#aaa; '
                        f'text-transform:uppercase; margin-bottom:4px;">{estacao}</div>'
                        f'<div style="font-size:2.2rem; font-weight:800; color:white; margin:4px 0;">'
                        f'{media_b:,.0f}</div>'
                        f'<div style="font-size:0.85rem; color:#bbb; margin-bottom:10px;">'
                        f'Meta: {meta_b:,.0f} pçs/dia</div>'
                        '<div style="background:#333; border-radius:8px; height:14px; '
                        'overflow:hidden; margin:8px 0;">'
                        f'<div style="width:{pct_bar:.0f}%; height:100%; background:{cor_prog}; '
                        f'border-radius:8px; transition:width 0.5s;"></div>'
                        '</div>'
                        '<div style="display:flex; justify-content:space-between; '
                        'font-size:0.78rem; color:#999; margin-bottom:8px;">'
                        f'<span>0</span><span>{meta_b:,.0f}</span>'
                        '</div>'
                        f'<div style="font-size:1.1rem; font-weight:700; color:{cor_prog};">'
                        f'{pct:.0f}%</div>'
                        f'<div style="font-size:0.78rem; color:{cor_prog}; margin-top:2px;">'
                        f'{status} ({diff:+,.0f})</div>'
                        '</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("---")

        # Métricas por estação
        if estacoes_iac:
            n_cols = min(len(estacoes_iac), 3)
            cols_est = st.columns(n_cols if n_cols > 0 else 1)
            for i, estacao in enumerate(estacoes_iac):
                df_est = df_filtrado_iac[df_filtrado_iac['ESTACAO'] == estacao]
                with cols_est[i % n_cols]:
                    st.markdown(f"#### {estacao}")
                    dias_est = df_est['DATA'].dt.date.nunique()
                    pecas_est = df_est['QUANTIDADE'].sum()
                    media_pe = pecas_est / max(dias_est, 1)
                    meta_e = meta_diaria_por_estacao_iacanga(df_filtrado_iac, estacao)
                    pct_meta = (media_pe / meta_e * 100) if meta_e > 0 else 0
                    delta_e = media_pe - meta_e
                    st.metric("Total Peças", f"{pecas_est:,.0f}")
                    st.metric("Dias Trabalhados", f"{dias_est}")
                    st.metric(
                        "Média Peças/Dia", f"{media_pe:,.0f}",
                        delta=f"{delta_e:+,.0f} vs Meta {meta_e:,.0f}",
                    )
                    st.metric("% da Meta", f"{pct_meta:.1f}%")

        st.markdown("---")
        # Produção diária por estação (com metas variáveis)
        st.markdown("#### 📈 Produção Diária por Estação (com Metas)")
        if not df_filtrado_iac.empty:
            prod_est_dia_iac = (
                df_filtrado_iac.groupby(['DATA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
            )
            fig_est1_iac = px.line(
                prod_est_dia_iac, x='DATA', y='QUANTIDADE', color='ESTACAO',
                labels={'DATA': 'Data', 'QUANTIDADE': 'Peças', 'ESTACAO': 'Estação'},
                color_discrete_map=cores_est_iac, markers=True,
            )
            for est in estacoes_iac:
                df_est_diario = df_filtrado_iac[df_filtrado_iac['ESTACAO'] == est]
                linhas_meta = []
                for data_, g in df_est_diario.groupby('DATA'):
                    linhas_meta.append({'DATA': data_, 'META': meta_ponderada_iacanga(g)})
                if linhas_meta:
                    df_metas_est = pd.DataFrame(linhas_meta).sort_values('DATA')
                    fig_est1_iac.add_trace(go.Scatter(
                        x=df_metas_est['DATA'], y=df_metas_est['META'],
                        name=f'Meta {est}',
                        line=dict(color=cores_est_iac[est], dash='dot', width=2),
                        mode='lines', showlegend=True,
                    ))
            fig_est1_iac.update_layout(
                height=500, margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                plot_bgcolor='rgba(0,0,0,0)',
            )
            fig_est1_iac.update_xaxes(tickformat='%d/%m/%Y', gridcolor='rgba(255,255,255,0.05)')
            fig_est1_iac.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig_est1_iac, use_container_width=True)

        # Análise Detalhada por Estação
        st.markdown("#### 📊 Análise Detalhada por Estação")
        for estacao in estacoes_iac:
            df_est = df_filtrado_iac[df_filtrado_iac['ESTACAO'] == estacao]
            if df_est.empty:
                continue
            meta_estacao_iac = meta_diaria_por_estacao_iacanga(df_filtrado_iac, estacao)

            with st.expander(f"📐 {estacao} — Análise Detalhada", expanded=False):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    linhas_d = []
                    for data_, g in df_est.groupby('DATA'):
                        linhas_d.append({
                            'DATA': data_,
                            'QUANTIDADE': g['QUANTIDADE'].sum(),
                            'META_DIA': meta_ponderada_iacanga(g),
                        })
                    prod_dia_est = (
                        pd.DataFrame(linhas_d).sort_values('DATA')
                        if linhas_d else pd.DataFrame()
                    )
                    fig_tend = go.Figure()
                    if not prod_dia_est.empty:
                        fig_tend.add_trace(go.Bar(
                            x=prod_dia_est['DATA'], y=prod_dia_est['QUANTIDADE'],
                            name='Peças/Dia', marker_color=cores_est_iac[estacao], opacity=0.75,
                        ))
                        if len(prod_dia_est) >= 5:
                            prod_dia_est['MM5'] = prod_dia_est['QUANTIDADE'].rolling(5).mean()
                            fig_tend.add_trace(go.Scatter(
                                x=prod_dia_est['DATA'], y=prod_dia_est['MM5'],
                                name='Média Móvel (5d)', line=dict(color='red', width=2),
                            ))
                        media_est = prod_dia_est['QUANTIDADE'].mean()
                        fig_tend.add_hline(
                            y=media_est, line_dash="dash", line_color="gray",
                            annotation_text=f"Média: {media_est:,.0f}",
                        )
                        fig_tend.add_trace(go.Scatter(
                            x=prod_dia_est['DATA'], y=prod_dia_est['META_DIA'],
                            name='Meta (variável)',
                            line=dict(color='#2ca02c', width=2, dash='dot'),
                            mode='lines+markers', marker=dict(symbol='diamond', size=7),
                        ))
                    fig_tend.update_layout(
                        title=f"Produção Diária — {estacao}", height=400,
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    fig_tend.update_xaxes(tickformat='%d/%m/%Y', gridcolor='rgba(255,255,255,0.05)')
                    fig_tend.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
                    st.plotly_chart(fig_tend, use_container_width=True)

                with col_e2:
                    prod_dia_est2 = df_est.groupby('DATA')['QUANTIDADE'].sum().reset_index()
                    fig_box_iac = px.box(
                        prod_dia_est2, y='QUANTIDADE',
                        color_discrete_sequence=[cores_est_iac[estacao]],
                        labels={'QUANTIDADE': 'Peças/Dia'},
                    )
                    if meta_estacao_iac > 0:
                        fig_box_iac.add_hline(
                            y=meta_estacao_iac, line_dash="dot", line_color="#2ca02c",
                            line_width=2, annotation_text=f"🎯 Meta: {meta_estacao_iac:,.0f}",
                            annotation_position="top left",
                        )
                    fig_box_iac.update_layout(
                        title=f"Consistência — {estacao}", height=400,
                        margin=dict(l=20, r=20, t=40, b=20),
                        paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig_box_iac, use_container_width=True)

                # Tabela de estatísticas
                prod_dia_stats = df_est.groupby('DATA')['QUANTIDADE'].sum()
                dias_acima = 0
                for data_, g in df_est.groupby('DATA'):
                    meta_dia = meta_ponderada_iacanga(g)
                    if g['QUANTIDADE'].sum() >= meta_dia and meta_dia > 0:
                        dias_acima += 1
                dias_total_est = len(prod_dia_stats)
                pct_meta_est = (
                    prod_dia_stats.mean() / meta_estacao_iac * 100
                ) if meta_estacao_iac > 0 else 0

                stats_df = pd.DataFrame({
                    'Estatística': [
                        '🎯 META DIÁRIA (ponderada)', '📊 Média/Dia', '% da Meta',
                        'Dias Acima da Meta', 'Mediana/Dia', 'Desvio Padrão',
                        'Mínimo/Dia', 'Máximo/Dia', 'Coef. Variação (%)', 'Total Peças',
                    ],
                    'Valor': [
                        f"{meta_estacao_iac:,.0f} peças",
                        f"{prod_dia_stats.mean():,.0f}",
                        f"{pct_meta_est:.1f}%",
                        f"{dias_acima} de {dias_total_est} ({(dias_acima/max(dias_total_est,1)*100):.0f}%)",
                        f"{prod_dia_stats.median():,.0f}",
                        f"{prod_dia_stats.std():,.0f}" if len(prod_dia_stats) > 1 else "N/A",
                        f"{prod_dia_stats.min():,.0f}",
                        f"{prod_dia_stats.max():,.0f}",
                        f"{(prod_dia_stats.std()/prod_dia_stats.mean()*100):,.1f}%"
                        if prod_dia_stats.mean() > 0 and len(prod_dia_stats) > 1 else "N/A",
                        f"{df_est['QUANTIDADE'].sum():,.0f}",
                    ],
                })
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

        # Comparativo semanal
        st.markdown("#### 📅 Produção Semanal Comparativa (com Meta Semanal)")
        if not df_filtrado_iac.empty:
            prod_semanal_iac = (
                df_filtrado_iac.groupby(['SEMANA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
            )
            metas_semanais = []
            for (semana, est), grupo in df_filtrado_iac.groupby(['SEMANA', 'ESTACAO']):
                meta_total_semana = 0
                for data_, g in grupo.groupby('DATA'):
                    meta_total_semana += meta_ponderada_iacanga(g)
                metas_semanais.append({
                    'SEMANA': semana, 'ESTACAO': est, 'META_SEMANAL': meta_total_semana,
                })
            if metas_semanais:
                df_metas_sem = pd.DataFrame(metas_semanais)
                prod_semanal_iac = prod_semanal_iac.merge(
                    df_metas_sem, on=['SEMANA', 'ESTACAO'], how='left'
                )

            fig_sem_iac = go.Figure()
            for est in estacoes_iac:
                df_s = prod_semanal_iac[prod_semanal_iac['ESTACAO'] == est]
                if df_s.empty:
                    continue
                fig_sem_iac.add_trace(go.Bar(
                    x=df_s['SEMANA'], y=df_s['QUANTIDADE'],
                    name=f'{est} (Real)', marker_color=cores_est_iac[est], opacity=0.8,
                ))
                if 'META_SEMANAL' in df_s.columns:
                    fig_sem_iac.add_trace(go.Scatter(
                        x=df_s['SEMANA'], y=df_s['META_SEMANAL'],
                        name=f'{est} (Meta)', mode='lines+markers',
                        line=dict(color=cores_est_iac[est], dash='dot', width=2),
                        marker=dict(symbol='diamond', size=8),
                    ))
            fig_sem_iac.update_layout(
                height=500, margin=dict(l=20, r=20, t=30, b=20),
                barmode='group', xaxis_title='Semana', yaxis_title='Peças',
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                plot_bgcolor='rgba(0,0,0,0)',
            )
            fig_sem_iac.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
            fig_sem_iac.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig_sem_iac, use_container_width=True)

    # --- Footer ---
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#606878; font-size:0.82rem;'>"
        "✂️ Iacanga · Mantas Giattex &nbsp;|&nbsp; "
        "Meta variável por tamanho + estação (ponderada pelo mix do dia) &nbsp;|&nbsp; "
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        "</div>",
        unsafe_allow_html=True,
    )


# =====================================================================
# SCREEN — AREALVA MANTA DASHBOARD
# =====================================================================
elif screen == 'arealva_manta':

    # --- Breadcrumb ---
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Arealva</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Manta</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Load data ---
    try:
        df_corte = carregar_dados()
    except KeyError as e:
        st.error(f"❌ Erro de coluna: {e}")
        st.error("📋 Verifique se a planilha tem: DATA, OP, COR, QUANTIDADE, ESTAÇÃO DE CORTE, PRODUTO")
        st.info("📡 A planilha deve estar compartilhada como 'Qualquer pessoa com o link'.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao carregar a planilha: {e}")
        st.info("📡 Verifique se a planilha Google Sheets está acessível.")
        st.stop()

    # --- Sidebar filters ---
    with st.sidebar:
        st.info(f"📅 {df_corte['DATA'].min().strftime('%d/%m/%Y')} → {df_corte['DATA'].max().strftime('%d/%m/%Y')}")
        if st.sidebar.button("🔄 Limpar Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.sidebar.metric("📊 Registros", f"{len(df_corte):,}")

    df_trabalho = df_corte.copy()

    if 'filtro_ops' not in st.session_state:
        st.session_state.filtro_ops = []
    if 'filtro_estacoes' not in st.session_state:
        st.session_state.filtro_estacoes = []
    if 'filtro_produtos' not in st.session_state:
        st.session_state.filtro_produtos = []
    if 'filtro_data_ini' not in st.session_state:
        st.session_state.filtro_data_ini = df_trabalho['DATA'].min().date() if not df_trabalho.empty else None
    if 'filtro_data_fim' not in st.session_state:
        st.session_state.filtro_data_fim = df_trabalho['DATA'].max().date() if not df_trabalho.empty else None

    ops_disponiveis = sorted(df_trabalho['OP'].dropna().unique())
    default_ops = [op for op in st.session_state.filtro_ops if op in ops_disponiveis]
    ops_selecionadas = st.sidebar.multiselect("📋 Filtrar por OP", options=ops_disponiveis, default=default_ops)
    st.session_state.filtro_ops = ops_selecionadas

    estacoes_disponiveis = sorted(df_trabalho['ESTACAO'].dropna().unique())
    default_est = [e for e in st.session_state.filtro_estacoes if e in estacoes_disponiveis]
    estacoes_selecionadas = st.sidebar.multiselect("🏭 Filtrar por Estação", options=estacoes_disponiveis, default=default_est)
    st.session_state.filtro_estacoes = estacoes_selecionadas

    produtos_disponiveis = sorted(df_trabalho['PRODUTO'].dropna().unique())
    default_prod = [p for p in st.session_state.filtro_produtos if p in produtos_disponiveis]
    produtos_selecionados = st.sidebar.multiselect("📦 Filtrar por Produto", options=produtos_disponiveis, default=default_prod)
    st.session_state.filtro_produtos = produtos_selecionados

    st.sidebar.markdown("### 📅 Filtro de Dias")
    if 'filtro_tipo_data' not in st.session_state:
        st.session_state.filtro_tipo_data = "Período"
    tipo_filtro = st.sidebar.radio(
        "Tipo de filtro",
        options=["Um dia", "Período"],
        index=0 if st.session_state.filtro_tipo_data == "Um dia" else 1,
        horizontal=True,
    )
    st.session_state.filtro_tipo_data = tipo_filtro

    if not df_trabalho.empty:
        data_min = df_trabalho['DATA'].min().date()
        data_max = df_trabalho['DATA'].max().date()
        saved_ini = st.session_state.filtro_data_ini or data_min
        saved_fim = st.session_state.filtro_data_fim or data_max
        saved_ini = max(saved_ini, data_min)
        saved_fim = min(saved_fim, data_max)

        if tipo_filtro == "Um dia":
            dia_selecionado = st.sidebar.date_input("Data", value=saved_fim,
                                                     min_value=data_min, max_value=data_max,
                                                     format="DD/MM/YYYY")
            filtro_datas = (dia_selecionado, dia_selecionado)
            st.session_state.filtro_data_ini = dia_selecionado
            st.session_state.filtro_data_fim = dia_selecionado
        else:
            data_inicio = st.sidebar.date_input("Início", value=saved_ini,
                                                 min_value=data_min, max_value=data_max,
                                                 format="DD/MM/YYYY")
            data_fim = st.sidebar.date_input("Fim", value=saved_fim,
                                              min_value=data_min, max_value=data_max,
                                              format="DD/MM/YYYY")
            filtro_datas = (data_inicio, data_fim)
            st.session_state.filtro_data_ini = data_inicio
            st.session_state.filtro_data_fim = data_fim
    else:
        filtro_datas = (None, None)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.sidebar.caption(f"Registros filtrados: {len(df_trabalho):,}")

    # --- Apply filters ---
    df_filtrado = df_trabalho.copy()
    if ops_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['OP'].isin(ops_selecionadas)]
    if estacoes_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['ESTACAO'].isin(estacoes_selecionadas)]
    if produtos_selecionados:
        df_filtrado = df_filtrado[df_filtrado['PRODUTO'].isin(produtos_selecionados)]
    if isinstance(filtro_datas, tuple) and filtro_datas[0] is not None:
        df_filtrado = df_filtrado[
            (df_filtrado['DATA'].dt.date >= filtro_datas[0]) &
            (df_filtrado['DATA'].dt.date <= filtro_datas[1])
        ]

    # --- Dashboard Header ---
    st.markdown('<div class="dash-header">✂️ Arealva — Manta</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-sub">Acompanhamento de produção e desempenho por estação</div>', unsafe_allow_html=True)

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "📋 Acompanhamento por OP", "🏭 Produção por Estação"])

    # TAB 1
    with tab1:
        st.markdown("### 📊 Indicadores Gerais")
        total_pecas = df_filtrado['QUANTIDADE'].sum()
        total_ops = df_filtrado['OP'].nunique()
        total_cores = df_filtrado['COR'].nunique()
        dias_trabalhados = df_filtrado['DATA'].dt.date.nunique()
        media_dia = total_pecas / max(dias_trabalhados, 1)
        pecas_maquina = df_filtrado[df_filtrado['ESTACAO'] == 'MAQUINA']['QUANTIDADE'].sum()
        pecas_mesa1 = df_filtrado[df_filtrado['ESTACAO'] == 'MESA 1']['QUANTIDADE'].sum()
        pecas_mesa2 = df_filtrado[df_filtrado['ESTACAO'] == 'MESA 2']['QUANTIDADE'].sum()
        delta_media = ((media_dia / META_TOTAL) - 1) * 100 if META_TOTAL > 0 else 0

        cols_kpi = st.columns(4)
        cols_kpi[0].metric("✂️ Total de Peças", f"{total_pecas:,.0f}")
        cols_kpi[1].metric("📋 Total de OPs", f"{total_ops}")
        cols_kpi[2].metric("🎨 Cores Diferentes", f"{total_cores}")
        cols_kpi[3].metric("📆 Dias Trabalhados", f"{dias_trabalhados}")

        cols_kpi2 = st.columns(4)
        cols_kpi2[0].metric("⚡ Média Peças/Dia", f"{media_dia:,.0f}", delta=f"{delta_media:+.1f}% vs Meta {META_TOTAL:,}")
        cols_kpi2[1].metric("🔧 Máquina", f"{pecas_maquina:,.0f}")
        cols_kpi2[2].metric("📐 Mesa 1", f"{pecas_mesa1:,.0f}")
        cols_kpi2[3].metric("📐 Mesa 2", f"{pecas_mesa2:,.0f}")

        st.markdown("---")
        st.markdown("#### 📈 Produção Diária (Peças)")
        prod_diaria = df_filtrado.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
        prod_diaria['ACIMA_META'] = prod_diaria['QUANTIDADE'] >= META_TOTAL

        fig1 = go.Figure()
        df_acima = prod_diaria[prod_diaria['ACIMA_META']]
        df_abaixo = prod_diaria[~prod_diaria['ACIMA_META']]
        fig1.add_trace(go.Bar(x=df_acima['DATA'], y=df_acima['QUANTIDADE'],
                              name='Acima da Meta', marker_color='#2ca02c', opacity=0.8))
        fig1.add_trace(go.Bar(x=df_abaixo['DATA'], y=df_abaixo['QUANTIDADE'],
                              name='Abaixo da Meta', marker_color='#d62728', opacity=0.7))
        if len(prod_diaria) >= 5:
            prod_diaria['MM5'] = prod_diaria['QUANTIDADE'].rolling(5, min_periods=1).mean()
            fig1.add_trace(go.Scatter(x=prod_diaria['DATA'], y=prod_diaria['MM5'],
                                      name='Tendência (5d)', line=dict(color='#ff7f0e', width=3), mode='lines'))
        fig1.add_hline(y=META_TOTAL, line_dash="dash", line_color="#aaa", line_width=2,
                       annotation_text=f"Meta: {META_TOTAL:,}", annotation_font_size=12,
                       annotation_font_color="#aaa")
        fig1.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20),
                           legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0.5, xanchor='center'),
                           xaxis_title='', yaxis_title='Peças',
                           plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                           font_color='#E0E0E0')
        fig1.update_xaxes(tickformat='%d/%m/%Y', gridcolor='rgba(255,255,255,0.05)')
        fig1.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig1, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 🏭 Distribuição por Estação")
            dist_estacao = df_filtrado.groupby('ESTACAO')['QUANTIDADE'].sum().reset_index()
            fig2 = px.pie(dist_estacao, values='QUANTIDADE', names='ESTACAO',
                          color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
            fig2.update_traces(textposition='inside', textinfo='percent+label+value')
            fig2.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20),
                               paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0')
            st.plotly_chart(fig2, use_container_width=True)

        with col_g2:
            st.markdown("#### 📦 Produção por Produto")
            prod_produto = df_filtrado.groupby('PRODUTO')['QUANTIDADE'].sum().reset_index()
            prod_produto = prod_produto.sort_values('QUANTIDADE', ascending=True).tail(15)
            fig3 = px.bar(prod_produto, y='PRODUTO', x='QUANTIDADE', orientation='h',
                          color='QUANTIDADE', color_continuous_scale='Blues',
                          labels={'QUANTIDADE': 'Peças', 'PRODUTO': 'Produto'})
            fig3.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                               showlegend=False, coloraxis_showscale=False,
                               paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                               plot_bgcolor='rgba(0,0,0,0)')
            fig3.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### 🎨 Top 15 Cores Mais Cortadas")
        col_cor_l, col_cor_r = st.columns(2)
        with col_cor_l:
            prod_cor = df_filtrado.groupby('COR')['QUANTIDADE'].sum().reset_index()
            prod_cor = prod_cor.sort_values('QUANTIDADE', ascending=True).tail(15)
            fig4 = px.bar(prod_cor, y='COR', x='QUANTIDADE', orientation='h',
                          color='QUANTIDADE', color_continuous_scale='Viridis',
                          labels={'QUANTIDADE': 'Peças', 'COR': 'Cor'})
            fig4.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20),
                               showlegend=False, coloraxis_showscale=False,
                               paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                               plot_bgcolor='rgba(0,0,0,0)')
            fig4.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig4, use_container_width=True)
        with col_cor_r:
            prod_cor_all = df_filtrado.groupby('COR')['QUANTIDADE'].sum().reset_index()
            prod_cor_all = prod_cor_all.sort_values('QUANTIDADE', ascending=False).head(15)
            prod_cor_all['%'] = (prod_cor_all['QUANTIDADE'] / prod_cor_all['QUANTIDADE'].sum() * 100).round(1)
            prod_cor_all.columns = ['Cor', 'Peças', '% do Total']
            st.dataframe(prod_cor_all, use_container_width=True, height=400, hide_index=True)

    # TAB 2
    with tab2:
        st.markdown("### 📋 Acompanhamento Detalhado por OP")
        resumo_op = df_filtrado.groupby('OP').agg(
            Total_Pecas=('QUANTIDADE', 'sum'),
            Qtd_Cores=('COR', 'nunique'),
            Produto=('PRODUTO', 'first'),
            Data_Inicio=('DATA', 'min'),
            Ultimo_corte=('DATA', 'max'),
            Dias_Producao=('DATA', lambda x: x.dt.date.nunique())
        ).reset_index().sort_values('Total_Pecas', ascending=False)

        st.markdown("#### Resumo das OPs")
        st.dataframe(
            resumo_op.style.format({
                'Total_Pecas': '{:,.0f}',
                'Data_Inicio': lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '',
                'Ultimo_corte': lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '',
            }),
            use_container_width=True, height=400,
        )
        st.markdown("---")
        op_detalhe = st.selectbox("🔎 Selecione uma OP para ver detalhes:", options=resumo_op['OP'].tolist())
        if op_detalhe:
            df_op = df_filtrado[df_filtrado['OP'] == op_detalhe]
            col_op1, col_op2, col_op3 = st.columns(3)
            col_op1.metric("Peças Total", f"{df_op['QUANTIDADE'].sum():,.0f}")
            col_op2.metric("Cores Cortadas", f"{df_op['COR'].nunique()}")
            col_op3.metric("Produto", df_op['PRODUTO'].iloc[0] if not df_op.empty else "N/A")

            st.markdown(f"#### Quantidade por Cor — OP {op_detalhe}")
            cor_op = df_op.groupby('COR')['QUANTIDADE'].sum().reset_index().sort_values('QUANTIDADE', ascending=False)
            fig_op1 = px.bar(cor_op, x='COR', y='QUANTIDADE', color='QUANTIDADE',
                             color_continuous_scale='Blues',
                             labels={'COR': 'Cor', 'QUANTIDADE': 'Peças'}, text='QUANTIDADE')
            fig_op1.update_traces(textposition='outside')
            fig_op1.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                                  coloraxis_showscale=False,
                                  paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                                  plot_bgcolor='rgba(0,0,0,0)')
            fig_op1.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig_op1, use_container_width=True)

            st.markdown(f"#### 📝 Registros Detalhados — OP {op_detalhe}")
            df_op_display = df_op[['DATA', 'ESTACAO', 'COR', 'QUANTIDADE', 'PRODUTO']].copy()
            df_op_display['DATA'] = df_op_display['DATA'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_op_display, use_container_width=True, height=300)

    # TAB 3
    with tab3:
        st.markdown("### 🏭 Produção por Estação de Corte")
        estacoes = ['MAQUINA', 'MESA 1', 'MESA 2']
        cores_estacao = {'MAQUINA': '#1f77b4', 'MESA 1': '#2ca02c', 'MESA 2': '#ff7f0e'}

        st.markdown("#### 🎯 Progresso vs Meta Diária (Média Peças/Dia)")
        cols_meta = st.columns(3)
        for i, estacao in enumerate(estacoes):
            df_est_b = df_filtrado[df_filtrado['ESTACAO'] == estacao]
            dias_b = df_est_b['DATA'].dt.date.nunique()
            media_b = df_est_b['QUANTIDADE'].sum() / max(dias_b, 1)
            meta_b = METAS[estacao]
            pct = min((media_b / meta_b * 100), 150) if meta_b > 0 else 0
            diff = media_b - meta_b
            cor_prog = '#2ca02c' if pct >= 100 else ('#ff7f0e' if pct >= 80 else '#d62728')
            status = '✅ META ATINGIDA' if pct >= 100 else ('⚠️ PRÓXIMO DA META' if pct >= 80 else '❌ ABAIXO DA META')
            pct_bar = min(pct, 100)
            with cols_meta[i]:
                card_html = (
                    '<div style="background:#1a1a2e; border-radius:14px; padding:20px; color:white; '
                    'text-align:center; box-shadow:0 3px 12px rgba(0,0,0,0.3);">'
                    f'<div style="font-size:0.8rem; letter-spacing:1px; color:#aaa; '
                    f'text-transform:uppercase; margin-bottom:4px;">{estacao}</div>'
                    f'<div style="font-size:2.2rem; font-weight:800; color:white; margin:4px 0;">'
                    f'{media_b:,.0f}</div>'
                    f'<div style="font-size:0.85rem; color:#bbb; margin-bottom:10px;">'
                    f'Meta: {meta_b:,} pçs/dia</div>'
                    '<div style="background:#333; border-radius:8px; height:14px; '
                    'overflow:hidden; margin:8px 0;">'
                    f'<div style="width:{pct_bar:.0f}%; height:100%; background:{cor_prog}; '
                    'border-radius:8px;"></div>'
                    '</div>'
                    '<div style="display:flex; justify-content:space-between; '
                    'font-size:0.78rem; color:#999; margin-bottom:8px;">'
                    f'<span>0</span><span>{meta_b:,}</span>'
                    '</div>'
                    f'<div style="font-size:1.1rem; font-weight:700; color:{cor_prog};">{pct:.0f}%</div>'
                    f'<div style="font-size:0.78rem; color:{cor_prog}; margin-top:2px;">'
                    f'{status} ({diff:+,.0f})</div>'
                    '</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("---")
        cols_est = st.columns(3)
        for i, estacao in enumerate(estacoes):
            df_est = df_filtrado[df_filtrado['ESTACAO'] == estacao]
            with cols_est[i]:
                st.markdown(f"#### {estacao}")
                dias_est = df_est['DATA'].dt.date.nunique()
                pecas_est = df_est['QUANTIDADE'].sum()
                media_pecas_est = pecas_est / max(dias_est, 1)
                meta_est = METAS[estacao]
                pct_meta = (media_pecas_est / meta_est * 100) if meta_est > 0 else 0
                delta_meta = media_pecas_est - meta_est
                st.metric("Total Peças", f"{pecas_est:,.0f}")
                st.metric("Dias Trabalhados", f"{dias_est}")
                st.metric("Média Peças/Dia", f"{media_pecas_est:,.0f}",
                          delta=f"{delta_meta:+,.0f} vs Meta {meta_est:,}")
                st.metric("% da Meta", f"{pct_meta:.1f}%")

        st.markdown("---")
        st.markdown("#### 📈 Produção Diária por Estação (com Metas)")
        prod_est_dia = df_filtrado.groupby(['DATA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
        fig_est1 = px.line(prod_est_dia, x='DATA', y='QUANTIDADE', color='ESTACAO',
                           labels={'DATA': 'Data', 'QUANTIDADE': 'Peças', 'ESTACAO': 'Estação'},
                           color_discrete_map=cores_estacao, markers=True)
        for est_nome, meta_val in METAS.items():
            fig_est1.add_hline(y=meta_val, line_dash="dot", line_width=1.5,
                               line_color=cores_estacao[est_nome],
                               annotation_text=f"Meta {est_nome}: {meta_val:,}",
                               annotation_position="top left",
                               annotation_font_size=10,
                               annotation_font_color=cores_estacao[est_nome],
                               opacity=0.5)
        fig_est1.update_layout(height=500, margin=dict(l=20, r=20, t=30, b=20),
                               paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                               plot_bgcolor='rgba(0,0,0,0)')
        fig_est1.update_xaxes(tickformat='%d/%m/%Y', gridcolor='rgba(255,255,255,0.05)')
        fig_est1.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig_est1, use_container_width=True)

        st.markdown("#### 📊 Análise Detalhada por Estação")
        for estacao in estacoes:
            df_est = df_filtrado[df_filtrado['ESTACAO'] == estacao]
            if df_est.empty:
                continue
            with st.expander(f"📐 {estacao} — Análise Detalhada", expanded=False):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    prod_dia_est = df_est.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
                    fig_tend = go.Figure()
                    fig_tend.add_trace(go.Bar(x=prod_dia_est['DATA'], y=prod_dia_est['QUANTIDADE'],
                                              name='Peças/Dia', marker_color=cores_estacao[estacao], opacity=0.7))
                    if len(prod_dia_est) >= 5:
                        prod_dia_est['MM5'] = prod_dia_est['QUANTIDADE'].rolling(5).mean()
                        fig_tend.add_trace(go.Scatter(x=prod_dia_est['DATA'], y=prod_dia_est['MM5'],
                                                      name='Média Móvel (5d)', line=dict(color='red', width=2)))
                    media_est_val = prod_dia_est['QUANTIDADE'].mean()
                    fig_tend.add_hline(y=media_est_val, line_dash="dash", line_color="gray",
                                       annotation_text=f"Média: {media_est_val:,.0f}")
                    meta_estacao = METAS.get(estacao, 0)
                    if meta_estacao > 0:
                        fig_tend.add_hline(y=meta_estacao, line_dash="dot", line_color="green",
                                           line_width=2, annotation_text=f"🎯 Meta: {meta_estacao:,}",
                                           annotation_position="top left")
                    fig_tend.update_layout(title=f"Produção Diária — {estacao}", height=400,
                                           margin=dict(l=20, r=20, t=40, b=20),
                                           paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                                           plot_bgcolor='rgba(0,0,0,0)')
                    fig_tend.update_xaxes(tickformat='%d/%m/%Y', gridcolor='rgba(255,255,255,0.05)')
                    fig_tend.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
                    st.plotly_chart(fig_tend, use_container_width=True)

                with col_e2:
                    prod_dia_est2 = df_est.groupby('DATA')['QUANTIDADE'].sum().reset_index()
                    fig_box = px.box(prod_dia_est2, y='QUANTIDADE',
                                     color_discrete_sequence=[cores_estacao[estacao]],
                                     labels={'QUANTIDADE': 'Peças/Dia'})
                    meta_box = METAS.get(estacao, 0)
                    if meta_box > 0:
                        fig_box.add_hline(y=meta_box, line_dash="dot", line_color="green",
                                          line_width=2, annotation_text=f"🎯 Meta: {meta_box:,}",
                                          annotation_position="top left")
                    fig_box.update_layout(title=f"Consistência — {estacao}", height=400,
                                          margin=dict(l=20, r=20, t=40, b=20),
                                          paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                                          plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_box, use_container_width=True)

                prod_dia_stats = df_est.groupby('DATA')['QUANTIDADE'].sum()
                meta_est_v = METAS.get(estacao, 0)
                pct_meta_est = (prod_dia_stats.mean() / meta_est_v * 100) if meta_est_v > 0 else 0
                dias_acima = (prod_dia_stats >= meta_est_v).sum() if meta_est_v > 0 else 0
                dias_total_est = len(prod_dia_stats)
                stats_df = pd.DataFrame({
                    'Estatística': ['🎯 META DIÁRIA', '📊 Média/Dia', '% da Meta',
                                    'Dias Acima da Meta', 'Mediana/Dia', 'Desvio Padrão',
                                    'Mínimo/Dia', 'Máximo/Dia', 'Coef. Variação (%)', 'Total Peças'],
                    'Valor': [
                        f"{meta_est_v:,} peças",
                        f"{prod_dia_stats.mean():,.0f}",
                        f"{pct_meta_est:.1f}%",
                        f"{dias_acima} de {dias_total_est} ({(dias_acima / max(dias_total_est, 1) * 100):.0f}%)",
                        f"{prod_dia_stats.median():,.0f}",
                        f"{prod_dia_stats.std():,.0f}" if len(prod_dia_stats) > 1 else "N/A",
                        f"{prod_dia_stats.min():,.0f}",
                        f"{prod_dia_stats.max():,.0f}",
                        f"{(prod_dia_stats.std() / prod_dia_stats.mean() * 100):,.1f}%"
                        if prod_dia_stats.mean() > 0 and len(prod_dia_stats) > 1 else "N/A",
                        f"{df_est['QUANTIDADE'].sum():,.0f}",
                    ]
                })
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

        st.markdown("#### 📅 Produção Semanal Comparativa (com Meta Semanal)")
        prod_semanal = df_filtrado.groupby(['SEMANA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
        dias_por_semana = (
            df_filtrado.groupby(['SEMANA', 'ESTACAO'])['DATA']
            .apply(lambda x: x.dt.date.nunique())
            .reset_index(name='DIAS')
        )
        prod_semanal = prod_semanal.merge(dias_por_semana, on=['SEMANA', 'ESTACAO'], how='left')
        prod_semanal['META_SEMANAL'] = prod_semanal.apply(
            lambda r: METAS.get(r['ESTACAO'], 0) * r['DIAS'], axis=1
        )
        fig_sem = go.Figure()
        for est in estacoes:
            df_s = prod_semanal[prod_semanal['ESTACAO'] == est]
            fig_sem.add_trace(go.Bar(x=df_s['SEMANA'], y=df_s['QUANTIDADE'],
                                     name=f'{est} (Real)', marker_color=cores_estacao[est], opacity=0.8))
            fig_sem.add_trace(go.Scatter(x=df_s['SEMANA'], y=df_s['META_SEMANAL'],
                                         name=f'{est} (Meta)', mode='lines+markers',
                                         line=dict(color=cores_estacao[est], dash='dot', width=2),
                                         marker=dict(symbol='diamond', size=8)))
        fig_sem.update_layout(height=500, margin=dict(l=20, r=20, t=30, b=20),
                              barmode='group', xaxis_title='Semana', yaxis_title='Peças',
                              legend=dict(orientation='h', yanchor='bottom', y=1.02),
                              paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                              plot_bgcolor='rgba(0,0,0,0)')
        fig_sem.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
        fig_sem.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig_sem, use_container_width=True)

    # --- Footer ---
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#606878; font-size:0.82rem;'>"
        "✂️ Arealva · Manta &nbsp;|&nbsp; Alimentado pela planilha CONTROLE GERAL MANTAS.xlsx &nbsp;|&nbsp; "
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        "</div>",
        unsafe_allow_html=True,
    )
