import streamlit as st
import pandas as pd
import logging
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import io
import os
import sys
import re
import requests
import numpy as np
from plotly.subplots import make_subplots

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from components.filtros_btn import render_filtros_btn

try:
    from config import GOOGLE_SHEETS_ID, GOOGLE_SHEETS_GID, METAS, META_TOTAL, CACHE_TTL
except ImportError:
    GOOGLE_SHEETS_ID = "1KLbNpw-P28YgoijXfMXU-zRQULuDHMMB"
    GOOGLE_SHEETS_GID = "1544210185"
    METAS = {'MAQUINA': 7000, 'MESA 1': 4000}
    META_TOTAL = sum(METAS.values())
    CACHE_TTL = 60

# Metas variáveis por (estação, tamanho) — Arealva Manta
# MAQUINA não varia por tamanho: usa _DEFAULT=7000 para qualquer tamanho
# MESA 1 varia conforme o tamanho da manta cortada
METAS_AREALVA_POR_TAMANHO: dict[str, dict] = {
    "MAQUINA": {"_DEFAULT": 7000},
    "MESA 1":  {"SOLTEIRO": 4700, "CASAL": 4000, "QUEEN": 2500, "KING": 2200, "_DEFAULT": 4000},
}

# config iacanga (Setor 2 - Mantas Giattex)
GOOGLE_SHEETS_ID_IACANGA = "1FBpCrq29_e1UBNwBlcgPTz66tbpUsgcgtzfXi4DcORU"
GOOGLE_SHEETS_GID_IACANGA = "0"

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

# helpers iacanga - normaliza e meta variável

def _norm_iacanga(texto: str) -> str:
    """normaliza: trim + upper + remove acentos."""
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
    """identifica o grupo de meta (MAQUINA/MESA/BURDAY) pela estacao."""
    s = _norm_iacanga(estacao)
    if "BURDAY" in s:
        return "BURDAY"
    if "MAQUINA" in s or s.startswith("MAQ"):
        return "MAQUINA"
    if "MESA" in s:
        return "MESA"
    return "OUTRO"

def normaliza_tamanho_iacanga(tam: str) -> str:
    """normaliza tamanho pra SOLTEIRO/CASAL/QUEEN/KING."""
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
    """meta diária pra um par (estação, tamanho)."""
    grupo = identifica_grupo_estacao_iacanga(estacao)
    tam = normaliza_tamanho_iacanga(tamanho)
    if grupo not in METAS_POR_TAMANHO:
        return 0
    metas_g = METAS_POR_TAMANHO[grupo]
    return metas_g.get(tam, metas_g.get("_DEFAULT", 0))

def meta_ponderada_iacanga(df_subset: pd.DataFrame) -> float:
    """meta ponderada pelo mix real de tamanhos cortados."""
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

# ── Helpers de meta por tamanho — Arealva Manta ──────────────────────────────

def meta_por_registro_arealva(estacao: str, tamanho: str) -> float:
    """Meta diária para um par (estação Arealva, tamanho).

    Fallback:
      1. METAS_AREALVA_POR_TAMANHO[estacao][tamanho]
      2. METAS_AREALVA_POR_TAMANHO[estacao]['_DEFAULT']
      3. METAS[estacao]  ← backward-compat para estações não mapeadas
      4. 0
    """
    est = str(estacao).strip().upper()
    # Reutiliza a normalização do Iacanga (SOLTEIRO/CASAL/QUEEN/KING)
    tam = normaliza_tamanho_iacanga(tamanho)
    if est not in METAS_AREALVA_POR_TAMANHO:
        return METAS.get(estacao, 0)
    metas_g = METAS_AREALVA_POR_TAMANHO[est]
    return metas_g.get(tam, metas_g.get("_DEFAULT", METAS.get(estacao, 0)))


def meta_ponderada_arealva(df_subset: pd.DataFrame) -> float:
    """Meta ponderada pelo mix real de tamanhos no subset (Arealva Manta).

    Se a coluna TAMANHO não existir ou estiver toda vazia, cai no fallback
    da meta fixa por estação — garante compatibilidade com registros históricos.
    """
    if df_subset.empty:
        return 0.0

    def _meta_fixa_ponderada(df: pd.DataFrame) -> float:
        """Fallback: meta fixa de METAS ponderada pela qtd de cada estação."""
        total = df['QUANTIDADE'].sum()
        if total <= 0:
            return 0.0
        soma = 0.0
        for est, g in df.groupby('ESTACAO'):
            soma += METAS.get(est, 0) * (g['QUANTIDADE'].sum() / total)
        return soma

    # Sem coluna TAMANHO → fallback histórico
    if 'TAMANHO' not in df_subset.columns:
        return _meta_fixa_ponderada(df_subset)

    tem_tamanho = (
        df_subset['TAMANHO'].notna()
        & (df_subset['TAMANHO'].astype(str).str.strip() != '')
        & (df_subset['TAMANHO'].astype(str).str.lower() != 'nan')
    )
    if not tem_tamanho.any():
        return _meta_fixa_ponderada(df_subset)

    # Mix com tamanhos: ponderação real
    total = df_subset['QUANTIDADE'].sum()
    if total <= 0:
        return 0.0
    soma = 0.0
    for (est, tam), grupo in df_subset.groupby(['ESTACAO', 'TAMANHO']):
        soma += meta_por_registro_arealva(est, tam) * (grupo['QUANTIDADE'].sum() / total)
    return soma


def meta_diaria_por_estacao_arealva(df_subset: pd.DataFrame, estacao: str) -> float:
    """Meta ponderada restrita a uma estação específica (Arealva Manta)."""
    return meta_ponderada_arealva(df_subset[df_subset['ESTACAO'] == estacao])


def calcular_meta_total_ponderada_arealva(df_subset: pd.DataFrame) -> float:
    """Soma das metas ponderadas de cada estação presente no subset (Arealva Manta)."""
    if df_subset.empty:
        return 0.0
    total = 0.0
    for est in df_subset['ESTACAO'].unique():
        total += meta_diaria_por_estacao_arealva(df_subset, est)
    return total

# ── Utilitário de análise de dias trabalhados ─────────────────────────────────

def _analisa_dias(datas_trabalhadas, data_ini, data_fim):
    """
    Analisa os dias trabalhados em um período.

    Retorna dict:
      sabados         : int  — sábados presentes em datas_trabalhadas
      uteis_esperados : int  — dias Seg-Sex no intervalo [data_ini, data_fim]
      ausentes        : list[date] — dias úteis sem registro
                        (lista vazia se >15 ausentes, para não poluir)
    """
    from datetime import timedelta as _td
    trabalhadas = set(datas_trabalhadas)
    sabados = sum(1 for d in trabalhadas if d.weekday() == 5)
    uteis = []
    cur = data_ini
    while cur <= data_fim:
        if cur.weekday() < 5:   # Seg(0)…Sex(4)
            uteis.append(cur)
        cur += _td(days=1)
    ausentes = [d for d in uteis if d not in trabalhadas]
    if len(ausentes) > 15:
        ausentes = []
    return {'sabados': sabados, 'uteis_esperados': len(uteis), 'ausentes': ausentes}

# ─────────────────────────────────────────────────────────────────────────────

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

# CSS

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

# DATA LOADING
# Datas são convertidas com utils.date_parser.parse_date_series (detecção de
# formato por coluna — D/M vs M/D). Não criar parsers de data locais aqui.

def baixar_csv_google_sheets():
    from utils.cache_manager import get_raw
    conteudo = get_raw(GOOGLE_SHEETS_ID, GOOGLE_SHEETS_GID, ttl=CACHE_TTL)
    if conteudo:
        return io.StringIO(conteudo)
    st.error("❌ Não foi possível carregar a planilha de Corte (Arealva Manta). Verifique sua conexão.")
    raise RuntimeError("Falha ao carregar planilha de corte Arealva Manta.")

@st.cache_data(ttl=CACHE_TTL)
def carregar_dados():
    csv_data = baixar_csv_google_sheets()
    # dtype=str evita que OP numérica vire float ("10" → "10.0").
    df_corte = pd.read_csv(csv_data, header=0, dtype=str)
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
    from utils.date_parser import parse_date_series
    df_corte['DATA'] = parse_date_series(df_corte['DATA'])
    df_corte = df_corte.dropna(subset=['DATA'])
    df_corte['OP'] = df_corte['OP'].fillna('SEM OP').astype(str).str.strip()
    df_corte.loc[df_corte['OP'] == '', 'OP'] = 'SEM OP'
    df_corte['COR'] = df_corte['COR'].astype(str).str.strip().str.upper()
    
    # Log quantity conversion errors
    before_quant = len(df_corte)
    df_corte['QUANTIDADE'] = pd.to_numeric(df_corte['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
    errors_quant = (df_corte['QUANTIDADE'] == 0).sum()
    if errors_quant > 0:
        logging.debug(f"Convertidas {errors_quant} quantidades inválidas para 0 em carregar_dados()")
    df_corte['ESTACAO'] = df_corte['ESTAÇÃO DE CORTE'].astype(str).str.strip()
    df_corte['PRODUTO'] = df_corte['PRODUTO'].astype(str).str.strip()
    df_corte['SEMANA'] = df_corte['DATA'].dt.isocalendar().week.astype(int)
    df_corte['MES'] = df_corte['DATA'].dt.month
    df_corte['DIA_SEMANA'] = df_corte['DATA'].dt.day_name()
    # TAMANHO — coluna opcional (adicionada à planilha após o histórico inicial)
    # normaliza_tamanho_iacanga reutilizada: mesmos valores SOLTEIRO/CASAL/QUEEN/KING
    if 'TAMANHO' in df_corte.columns:
        df_corte['TAMANHO'] = (
            df_corte['TAMANHO'].astype(str).str.strip()
            .apply(normaliza_tamanho_iacanga)
        )
    else:
        # Schema uniforme; funções de meta detectam '' e usam fallback fixo
        df_corte['TAMANHO'] = ''

    try:
        from utils.db_manager import upsert_df
        upsert_df(
            df_corte[["DATA", "OP", "COR", "QUANTIDADE", "PRODUTO", "ESTACAO", "TAMANHO"]],
            "corte_arealva_manta",
            ["DATA", "OP", "COR", "ESTACAO"],
        )
    except Exception:
        logging.warning("db_manager: falha ao salvar corte_arealva_manta", exc_info=True)

    return df_corte

# DATA LOADING — IACANGA (planilha própria)

def baixar_csv_google_sheets_iacanga():
    from utils.cache_manager import get_raw
    conteudo = get_raw(GOOGLE_SHEETS_ID_IACANGA, GOOGLE_SHEETS_GID_IACANGA, ttl=CACHE_TTL)
    if conteudo:
        return io.StringIO(conteudo)
    raise RuntimeError("Falha ao carregar planilha de corte Iacanga.")

@st.cache_data(ttl=CACHE_TTL)
def carregar_dados_iacanga():
    csv_data = baixar_csv_google_sheets_iacanga()
    # dtype=str evita que OP numérica vire float ("10" → "10.0").
    df_full = pd.read_csv(csv_data, header=0, dtype=str)
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

    from utils.date_parser import parse_date_series
    df['DATA'] = parse_date_series(df['DATA'])
    df = df.dropna(subset=['DATA'])
    df['OP'] = df['OP'].fillna('SEM OP').astype(str).str.strip()
    df.loc[df['OP'] == '', 'OP'] = 'SEM OP'
    df['COR'] = df['COR'].astype(str).str.strip().str.upper()
    df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
    df['ESTACAO'] = df['ESTAÇÃO DE CORTE'].astype(str).str.strip()
    df['PRODUTO'] = df['PRODUTO'].astype(str).str.strip()
    df['TAMANHO'] = df['TAMANHO'].astype(str).str.strip().apply(normaliza_tamanho_iacanga)
    df['GRUPO_ESTACAO'] = df['ESTACAO'].apply(identifica_grupo_estacao_iacanga)
    df['SEMANA'] = df['DATA'].dt.isocalendar().week.astype(int)
    df['MES'] = df['DATA'].dt.month
    df['DIA_SEMANA'] = df['DATA'].dt.day_name()

    try:
        from utils.db_manager import upsert_df
        upsert_df(
            df[["DATA", "OP", "COR", "QUANTIDADE", "PRODUTO", "ESTACAO", "TAMANHO", "GRUPO_ESTACAO"]],
            "corte_iacanga",
            ["DATA", "OP", "COR", "ESTACAO"],
        )
    except Exception:
        logging.warning("db_manager: falha ao salvar corte_iacanga", exc_info=True)

    return df

# LENÇOL — CONSTANTES E HELPERS

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"
LENCOL_CACHE_TTL = 60

LENCOL_CORES_EMPRESA = {
    "BURDAYS":   "#FF6B6B",
    "CAMESA":    "#4ECDC4",
    "NIAZITEX":  "#45B7D1",
    "CORTTEX":   "#FFA726",
    "CORTEX":    "#FFA726",
    "SULTAN":    "#AB47BC",
    "DECOR":     "#26C6DA",
    "MARCELINO": "#FFD54F",
    "SEVEN":     "#66BB6A",
    "HOTEL":     "#EC407A",
}

LENCOL_PALETA = [
    "#4ECDC4", "#FF6B6B", "#45B7D1", "#FFA726",
    "#AB47BC", "#66BB6A", "#FFD54F", "#EC407A",
    "#7E57C2", "#26C6DA",
]

LENCOL_DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12),
    separators=",.",
    margin=dict(l=40, r=20, t=50, b=40),
)

LENCOL_DARK_AXES = dict(
    xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0"),
    yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0"),
)

LENCOL_MESES_PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                   7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

LENCOL_DIAS_PT = {
    "Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua",
    "Thursday":"Qui","Friday":"Sex","Saturday":"Sáb","Sunday":"Dom",
}
LENCOL_ORDEM_DIAS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def lencol_layout_dark(**kwargs):
    layout = {**LENCOL_DARK, **LENCOL_DARK_AXES}
    if 'yaxis' in kwargs:
        layout['yaxis'] = {**LENCOL_DARK_AXES['yaxis'], **kwargs.pop('yaxis')}
    if 'xaxis' in kwargs:
        layout['xaxis'] = {**LENCOL_DARK_AXES['xaxis'], **kwargs.pop('xaxis')}
    layout.update(kwargs)
    return layout

def lencol_fmt_num(v, dec=0):
    txt = f"{float(v):,.{dec}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")

def lencol_fmt_brl(v):
    return f"R$ {lencol_fmt_num(v, 2)}"

def lencol_parse_brl(s):
    if pd.isna(s):
        return 0.0
    s_str = str(s).strip()
    if s_str in ("", "nan", "NaN", "none", "None", "N/A"):
        return 0.0
    try:
        s_str = re.sub(r"R\$\s*", "", s_str).strip()
        s_str = s_str.replace(".", "").replace(",", ".")
        return float(s_str)
    except Exception:
        return 0.0

def lencol_cat_base(cat):
    if pd.isna(cat) or str(cat).strip().lower() in ("", "nan", "none", "n/a"):
        return ""
    c = re.sub(r"\s+", " ", str(cat).strip().upper())
    c = c.replace("DUPLOM", "DUPLO")
    for suf in (" KING", " QUEEN", " QE", " CS", " ST", " SOLT", " SIMPLES SOLT"):
        if c.endswith(suf):
            c = c[: -len(suf)].strip()
            break
    return c

def lencol_cor_empresa(emp):
    return LENCOL_CORES_EMPRESA.get(emp.upper().strip(), "#718096")

# ── Caseamento Jogo Duplo × Fundo ─────────────────────────────────────────────
# Um JOGO DUPLO precisa de um FUNDO correspondente (corte separado). As
# quantidades devem casear por OP + tamanho. Quando não caseiam, apontamos a
# diferença. JOGO SIMPLES não tem fundo.

def lencol_classifica_jogo_fundo(cat: str, tecido: str = "") -> tuple[str, str]:
    """Classifica um registro em (tipo, tamanho) a partir da CATEGORIA + TECIDO.

    tipo    ∈ {FUNDO, JOGO_DUPLO, JOGO_SIMPLES, OUTRO}
    tamanho ∈ {SOLTEIRO, CASAL, QUEEN, KING, ''}

    Regras descobertas nos dados reais:
      • O universo de caseamento são os JOGOS DE CAMA → a CATEGORIA menciona "JOGO"
        (ex.: "JOGO DUPLO CS", "FUNDO JOGO ST"). Porta-travesseiro, lençol avulso,
        fronha etc. ficam de fora (tipo OUTRO), mesmo tendo "fundo".
      • Dentro do universo, o TECIDO é a fonte autoritativa de jogo vs fundo:
        a categoria pode dizer "JOGO DUPLO CS" enquanto o tecido diz
        "FUNDO CASAL 4PÇS"  → é FUNDO; e pode dizer "FUNDO JOGO ST" enquanto o
        tecido diz "JOGO SOLTEIRO..."  → é JOGO. O tecido manda; a categoria é só
        fallback quando o tecido não esclarece.
    """
    c = re.sub(r"\s+", " ", str(cat).upper().strip())
    t = re.sub(r"\s+", " ", str(tecido).upper().strip())
    # Fora do universo jogo-cama (categoria não menciona JOGO) → não caseia
    if "JOGO" not in c:
        return ("OUTRO", "")
    txt = c + " " + t
    tamanho = ""
    if "KING" in txt:
        tamanho = "KING"
    elif "QUEEN" in txt or re.search(r"\bQE\b", txt):
        tamanho = "QUEEN"
    elif "CASAL" in txt or re.search(r"\bCS\b", txt):
        tamanho = "CASAL"
    elif "SOLT" in txt or re.search(r"\bST\b", txt):
        tamanho = "SOLTEIRO"
    tipo_jogo = "JOGO_SIMPLES" if ("SIMPLES" in c or "SIMPLES" in t) else "JOGO_DUPLO"
    # TECIDO manda
    if "FUNDO" in t:
        return ("FUNDO", tamanho)
    if "JOGO" in t:
        return (tipo_jogo, tamanho)
    # Tecido não esclarece → usa a categoria (ex.: "FUNDO JOGO QE")
    if "FUNDO" in c:
        return ("FUNDO", tamanho)
    return (tipo_jogo, tamanho)


def _lencol_tipos_tams(df: pd.DataFrame) -> tuple[list, list]:
    """Classifica todas as linhas do df em (tipos, tamanhos) de forma determinística.

    Usa zip sobre as colunas em vez de df.apply(axis=1) — este último expande tuplas
    em DataFrame de forma inconsistente e quebra a indexação.
    """
    n = len(df)
    cats = df["CATEGORIA"].astype(str).tolist() if "CATEGORIA" in df.columns else [""] * n
    tecs = df["TECIDO"].astype(str).tolist() if "TECIDO" in df.columns else [""] * n
    tipos, tams = [], []
    for c, t in zip(cats, tecs):
        tp, tm = lencol_classifica_jogo_fundo(c, t)
        tipos.append(tp)
        tams.append(tm)
    return tipos, tams


def lencol_caseamento(df: pd.DataFrame, apenas_com_fundo: bool = True) -> pd.DataFrame:
    """Reconcilia JOGO DUPLO × FUNDO por (OP, TAMANHO).

    Retorna DataFrame com colunas: OP, TAMANHO, JOGO, FUNDO, DIFERENCA, STATUS.
    DIFERENCA = FUNDO − JOGO (saldo de fundos): negativo = faltam fundos;
    positivo = sobram fundos; zero = caseado.

    apenas_com_fundo=True restringe às OPs que tiveram ao menos 1 corte de fundo —
    evita marcar como divergentes as centenas de OPs que simplesmente não usam fundo.
    """
    cols = ["OP", "TAMANHO", "JOGO", "FUNDO", "DIFERENCA", "STATUS"]
    if df is None or df.empty or "CATEGORIA" not in df.columns:
        return pd.DataFrame(columns=cols)
    d = df.copy()
    _tipos, _tams = _lencol_tipos_tams(d)
    d["_TIPO"] = _tipos
    d["_TAM"] = _tams
    d_rel = d[d["_TIPO"].isin(["JOGO_DUPLO", "FUNDO"])]
    if d_rel.empty:
        return pd.DataFrame(columns=cols)
    if apenas_com_fundo:
        ops_com_fundo = set(d_rel.loc[d_rel["_TIPO"] == "FUNDO", "OP"].unique())
        d_rel = d_rel[d_rel["OP"].isin(ops_com_fundo)]
        if d_rel.empty:
            return pd.DataFrame(columns=cols)
    jogo = (d_rel[d_rel["_TIPO"] == "JOGO_DUPLO"]
            .groupby(["OP", "_TAM"])["QUANT"].sum().rename("JOGO"))
    fundo = (d_rel[d_rel["_TIPO"] == "FUNDO"]
             .groupby(["OP", "_TAM"])["QUANT"].sum().rename("FUNDO"))
    rec = pd.concat([jogo, fundo], axis=1).fillna(0).reset_index()
    rec = rec.rename(columns={"_TAM": "TAMANHO"})
    rec["TAMANHO"] = rec["TAMANHO"].replace("", "—")
    rec["JOGO"] = rec["JOGO"].astype(int)
    rec["FUNDO"] = rec["FUNDO"].astype(int)
    rec["DIFERENCA"] = rec["FUNDO"] - rec["JOGO"]
    rec["STATUS"] = rec["DIFERENCA"].apply(
        lambda x: "✅ Caseado" if x == 0
        else ("🔴 Faltam fundos" if x < 0 else "🟠 Sobram fundos")
    )
    rec = rec.reindex(
        rec["DIFERENCA"].abs().sort_values(ascending=False).index
    ).reset_index(drop=True)
    return rec[cols]

# Datas do Lençol são tratadas no loader (utils.lencol_loader_smart) via
# utils.date_parser.parse_date_series. Não há parser de data local aqui.

def lencol_delta_icon(v):
    if v > 0:
        return f"▲ {lencol_fmt_num(v, 1)}%"
    if v < 0:
        return f"▼ {lencol_fmt_num(abs(v), 1)}%"
    return "— 0,0%"

@st.cache_data(ttl=LENCOL_CACHE_TTL, show_spinner=False)
def load_corte_lencol() -> pd.DataFrame:
    """
    Carrega lançamentos de lençol via CSV (NOT XLSX).

    Razão: XLSX export tima timeout (60+ segundos). CSV via gviz/tq é rápido e confiável.
    O parser robusto em utils.lencol_loader_smart já detecta datas corretamente
    por conteúdo (padrão M/D/YYYY com ano >= 2020) e converte com dayfirst=False.
    """
    try:
        from utils.lencol_loader_smart import load_lencol_smart_csv
        df = load_lencol_smart_csv()
        
        if df.empty:
            st.error("❌ Não foi possível baixar dados da planilha de lençol: DataFrame vazio")
            raise ConnectionError("Lençol loader retornou DataFrame vazio")
        
        # Garante colunas esperadas
        expected_cols = [
            "DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA",
            "TECIDO", "VALOR_PECA", "QUANT", "VALOR_RECEBER", "RETALHO_KG", "OBS",
        ]
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
            st.error(f"❌ Colunas faltando: {missing}")
            raise ValueError(f"Colunas esperadas faltando: {missing}")
        
        # DATA já vem como datetime do loader, mas normaliza para ter certeza
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
        before_count = len(df)
        df = df[df["DATA"].notna()]
        removed_nat = before_count - len(df)
        if removed_nat > 0:
            logging.debug(f"Removidos {removed_nat} registros com DATA inválida no Lençol")

        # Colunas numéricas: CSV já retorna string — pd.to_numeric() garante conversão
        df["QUANT"] = pd.to_numeric(df["QUANT"], errors="coerce").fillna(0).astype(int)
        df["VALOR_PECA"] = pd.to_numeric(df["VALOR_PECA"], errors="coerce").fillna(0.0)
        df["VALOR_RECEBER"] = pd.to_numeric(df["VALOR_RECEBER"], errors="coerce").fillna(0.0)
        df["RETALHO_KG"] = pd.to_numeric(df["RETALHO_KG"], errors="coerce").fillna(0.0)

        df["PRESTADOR"] = df["PRESTADOR"].astype(str).str.strip()
        df["EMPRESA"] = df["EMPRESA"].astype(str).str.strip().str.upper()
        df["CATEGORIA"] = df["CATEGORIA"].astype(str).str.strip().str.upper()
        df["CATEGORIA"] = df["CATEGORIA"].apply(
            lambda x: re.sub(r"\s+", " ", str(x))
            if pd.notna(x) and str(x).strip() not in ("", "nan", "none") else ""
        )
        df["TECIDO"] = df["TECIDO"].astype(str).str.strip()
        df["OP"] = df["OP"].astype(str).str.strip()

        invalidos = {"", "NAN", "NONE", "N/A", "NAO", "NAO INFORMADO"}
        
        # Log antes das remoções
        registros_antes = len(df)
        
        # Remover prestadores inválidos
        df = df[~df["PRESTADOR"].str.upper().isin(invalidos)]
        removidos_prestador = registros_antes - len(df)
        if removidos_prestador > 0:
            logging.debug(f"Removidos {removidos_prestador} registros com PRESTADOR inválido em load_corte_lencol()")
        
        # Remover empresas inválidas
        registros_antes_empresa = len(df)
        df = df[~df["EMPRESA"].str.upper().isin(invalidos)]
        removidos_empresa = registros_antes_empresa - len(df)
        if removidos_empresa > 0:
            logging.debug(f"Removidos {removidos_empresa} registros com EMPRESA inválida em load_corte_lencol()")
        
        # Remover quantidade zero
        registros_antes_quant = len(df)
        df = df[df["QUANT"] > 0]
        removidos_quant = registros_antes_quant - len(df)
        if removidos_quant > 0:
            logging.debug(f"Removidos {removidos_quant} registros com QUANT <= 0 em load_corte_lencol()")
        
        df = df.reset_index(drop=True)

        mask0 = df["VALOR_RECEBER"] == 0
        df.loc[mask0, "VALOR_RECEBER"] = df.loc[mask0, "QUANT"] * df.loc[mask0, "VALOR_PECA"]

        df["CAT_BASE"] = df["CATEGORIA"].apply(lencol_cat_base)
        df["ANO"] = df["DATA"].dt.year
        df["MES"] = df["DATA"].dt.month
        df["MES_NOME"] = df["MES"].map(LENCOL_MESES_PT)
        df["ANO_MES"] = df["DATA"].dt.to_period("M").astype(str)
        df["SEMANA"] = df["DATA"].dt.isocalendar().week.astype(int)
        df["DIA_SEMANA"] = df["DATA"].dt.day_name()
        df["DIA_SEMANA_PT"] = df["DIA_SEMANA"].map(LENCOL_DIAS_PT)

        try:
            from utils.db_manager import upsert_df
            upsert_df(
                df[["DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA", "TECIDO", "QUANT", "VALOR_PECA", "VALOR_RECEBER", "RETALHO_KG"]],
                "corte_lencol",
                ["DATA", "PRESTADOR", "OP", "CATEGORIA"],
            )
        except Exception:
            logging.warning("db_manager: falha ao salvar corte_lencol", exc_info=True)

        return df

    except Exception as e:
        st.error(f"❌ Não foi possível baixar dados da planilha de lençol: {e}")
        logging.debug(f"Erro completo: {e}")
        return pd.DataFrame(columns=[
            "DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA",
            "TECIDO", "VALOR_PECA", "QUANT", "VALOR_RECEBER", "RETALHO_KG", "OBS",
        ])

@st.cache_data(ttl=LENCOL_CACHE_TTL, show_spinner=False)
def load_metas_lencol() -> pd.DataFrame:
    url = (
        f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet=METAS"
    )
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), header=0, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        if "PRESTADOR" not in df.columns and df.shape[1] >= 4:
            df.columns = ["PRESTADOR", "EMPRESA", "CATEGORIA", "META"]
        df["PRESTADOR"] = df["PRESTADOR"].replace("", np.nan).ffill()
        df["EMPRESA"] = df["EMPRESA"].replace("", np.nan).ffill()
        df["PRESTADOR"] = df["PRESTADOR"].astype(str).str.strip().str.upper()
        df["EMPRESA"] = df["EMPRESA"].astype(str).str.strip().str.upper()
        df["CATEGORIA"] = df["CATEGORIA"].astype(str).str.strip().str.upper()
        df["META"] = pd.to_numeric(df["META"], errors="coerce")
        df = df[df["META"].notna() & (df["META"] > 0)].reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar metas de lençol: {str(e)[:100]}")
        logging.debug(f"URL: {url}")
        return pd.DataFrame(columns=["PRESTADOR", "EMPRESA", "CATEGORIA", "META"])

# ── ITAJU — PONTO PALITO MARCELINO ────────────────────────────────────────────

ITAJU_SHEET_ID  = "19dJKG956drBCv3fEnL75dTLf157xLKvE"
ITAJU_GID       = "1039503764"
ITAJU_CACHE_TTL = 60

ITAJU_CORES_PRODUTO = {
    "CIMA":   "#4ECDC4",
    "FUNDO":  "#FF6B6B",
    "FRONHA": "#FFA726",
    "JOGO":   "#45B7D1",
}

ITAJU_DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12), separators=",.",
    margin=dict(l=40, r=20, t=50, b=40),
)
ITAJU_DARK_AXES = dict(
    xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0"),
    yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0"),
)

def _itaju_layout(**kw):
    lay = {**ITAJU_DARK, **ITAJU_DARK_AXES}
    lay.update(kw)
    return lay

def _itaju_fmt(v, dec=0):
    return f"{float(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(ttl=ITAJU_CACHE_TTL, show_spinner=False)
def load_itaju() -> pd.DataFrame:
    from utils.cache_manager import get_raw as _gr
    from utils.date_parser import parse_date_series
    content = _gr(ITAJU_SHEET_ID, ITAJU_GID, ttl=ITAJU_CACHE_TTL)
    if not content:
        return pd.DataFrame()
    import io as _io
    raw = pd.read_csv(_io.StringIO(content), dtype=str, header=0)
    raw.columns = [str(c).strip() for c in raw.columns]
    # normaliza nomes de colunas com possível encoding quebrado
    col_map = {}
    for c in raw.columns:
        cn = normalize_text_basic(c)
        if "DATA"     in cn: col_map[c] = "DATA"
        elif "OP"     in cn: col_map[c] = "OP"
        elif "ESTAC"  in cn or "ESTA" in cn: col_map[c] = "ESTACAO"
        elif "COR"    in cn: col_map[c] = "COR"
        elif "QUANT"  in cn: col_map[c] = "QUANTIDADE"
        elif "TAMANHA" in cn or "TAMANHO" in cn: col_map[c] = "TAMANHO"
        elif "PRODUTO" in cn: col_map[c] = "PRODUTO"
        elif "OBS"    in cn: col_map[c] = "OBS"
    raw = raw.rename(columns=col_map)
    needed = ["DATA", "OP", "QUANTIDADE", "TAMANHO", "PRODUTO"]
    missing = [c for c in needed if c not in raw.columns]
    if missing:
        return pd.DataFrame()
    df = raw[["DATA", "OP",
              raw.columns[raw.columns.tolist().index("ESTACAO")] if "ESTACAO" in raw.columns else "OP",
              "COR" if "COR" in raw.columns else "OP",
              "QUANTIDADE", "TAMANHO", "PRODUTO",
              "OBS" if "OBS" in raw.columns else "OP"]].copy()
    # reseleciona as colunas certas após rename
    keep = [c for c in ["DATA", "OP", "ESTACAO", "COR", "QUANTIDADE", "TAMANHO", "PRODUTO", "OBS"] if c in raw.columns]
    df = raw[keep].copy()
    df["DATA"]      = parse_date_series(df["DATA"], default_order="MDY")
    df["QUANTIDADE"]= pd.to_numeric(df["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    df["OP"]        = df["OP"].astype(str).str.strip()
    df["PRODUTO"]   = df["PRODUTO"].astype(str).str.strip().str.upper()
    df["TAMANHO"]   = df["TAMANHO"].astype(str).str.strip().str.upper()
    if "COR"     in df.columns: df["COR"]     = df["COR"].astype(str).str.strip().str.upper()
    if "ESTACAO" in df.columns: df["ESTACAO"] = df["ESTACAO"].astype(str).str.strip().str.upper()
    blanks = {"", "NAN", "NONE", "N/A", "NAT"}
    df = df[
        df["DATA"].notna()
        & (df["QUANTIDADE"] > 0)
        & ~df["PRODUTO"].str.upper().isin(blanks)
    ].reset_index(drop=True)
    df["DIA_SEMANA"] = df["DATA"].dt.day_name()
    df["SEMANA"]     = df["DATA"].dt.isocalendar().week.astype(int)
    return df


def normalize_text_basic(s: str) -> str:
    import unicodedata, re as _re
    s = str(s).strip().upper()
    nfd = unicodedata.normalize("NFD", s)
    s = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return _re.sub(r"\s+", " ", s).strip()


def itaju_caseamento(df: pd.DataFrame) -> pd.DataFrame:
    """Reconcilia CIMA × FUNDO (× FRONHA) por OP + TAMANHO + COR."""
    cols_out = ["OP", "TAMANHO", "COR", "CIMA", "FUNDO", "FRONHA", "DIFER_CF", "STATUS"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols_out)
    grp_cols = ["OP", "TAMANHO"] + (["COR"] if "COR" in df.columns else [])
    piv = (
        df[df["PRODUTO"].isin(["CIMA", "FUNDO", "FRONHA"])]
        .groupby(grp_cols + ["PRODUTO"])["QUANTIDADE"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ["CIMA", "FUNDO", "FRONHA"]:
        if col not in piv.columns:
            piv[col] = 0
    piv["DIFER_CF"] = piv["FUNDO"] - piv["CIMA"]
    piv["STATUS"] = piv["DIFER_CF"].apply(
        lambda x: "✅ Caseado" if x == 0
        else ("🔴 Falta fundo" if x < 0 else "🟠 Sobra fundo")
    )
    if "COR" not in piv.columns:
        piv["COR"] = "—"
    piv = piv.rename(columns={"PRODUTO": "PRODUTO"})
    return piv[cols_out].sort_values("DIFER_CF", key=abs, ascending=False).reset_index(drop=True)


# NAVIGATION HELPERS

if st.session_state.get('_active_page') != 'corte':
    st.session_state.corte_screen = 'analysis_type'
st.session_state._active_page = 'corte'

def _go(screen: str):
    st.session_state.corte_screen = screen
    st.rerun()

# SIDEBAR

with st.sidebar:
    st.markdown("### ✂️ Controle de Corte")
    st.markdown("---")
    if st.button("🏢  Início", key="sb_home", use_container_width=True):
        st.session_state.corte_screen = 'analysis_type'
        st.switch_page("app.py")

    screen = st.session_state.corte_screen
    if screen == 'regions':
        if st.button("← Tipo de Análise", key="sb_back_regions", use_container_width=True):
            _go('analysis_type')
    elif screen == 'arealva_products':
        if st.button("← Regiões", key="sb_back1", use_container_width=True):
            _go('regions')
        if st.button("← Tipo de Análise", key="sb_back_type1", use_container_width=True):
            _go('analysis_type')
    elif screen == 'arealva_manta':
        if st.button("← Produtos", key="sb_back2", use_container_width=True):
            _go('arealva_products')
        if st.button("← Regiões", key="sb_back3", use_container_width=True):
            _go('regions')
    elif screen == 'arealva_lencol':
        if st.button("← Produtos", key="sb_back5", use_container_width=True):
            _go('arealva_products')
        if st.button("← Regiões", key="sb_back6", use_container_width=True):
            _go('regions')
    elif screen == 'eficiencia_dashboard':
        if st.button("← Tipo de Análise", key="sb_back_efic", use_container_width=True):
            _go('analysis_type')
    elif screen in ('iacanga_rendimento', 'iacanga_eficiencia'):
        if st.button("← Regiões", key="sb_back8", use_container_width=True):
            _go('regions')
    elif screen == 'itaju':
        if st.button("← Regiões", key="sb_back_itaju", use_container_width=True):
            _go('regions')

    # Filters injected below only for the dashboard screens
    if screen in ('arealva_manta', 'iacanga_rendimento', 'arealva_lencol', 'iacanga_eficiencia'):
        st.markdown("---")
        st.header("🔍 Filtros")

# SCREEN — ANALYSIS TYPE SELECTION (Rendimento vs Eficiência Geral)

screen = st.session_state.corte_screen

if screen == 'analysis_type':
    st.markdown("""
    <div class="page-header">
        <div class="page-badge">✂️ Controle de Corte</div>
        <h1 class="page-title">Selecione o Tipo de <span class="accent">Análise</span></h1>
        <p class="page-subtitle">Escolha o tipo de análise de corte para acessar o painel</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    _, col_rendimento_main, col_eficiencia_main, _ = st.columns([0.5, 3, 3, 0.5])

    with col_rendimento_main:
        st.markdown("""
        <div class="region-card" style="--rc-a:#2F5F6F; --rc-b:#4ECDC4; --rc-accent:#4ECDC4;">
            <div class="rc-icon">📊</div>
            <div class="rc-label">Produção · Por Região e Estação</div>
            <div class="rc-title">Análise de Corte</div>
            <div class="rc-desc">
                Acompanhamento da produção diária por região (Arealva, Iacanga, Itaju), estação e operador — com metas, OPs e evolução semanal.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Arealva</span>
                <span class="rc-tag">Iacanga</span>
                <span class="rc-tag">Itaju</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_rendimento_main", use_container_width=True):
            _go('regions')

    with col_eficiencia_main:
        st.markdown("""
        <div class="region-card" style="--rc-a:#6F4F7F; --rc-b:#AB47BC; --rc-accent:#AB47BC;">
            <div class="rc-icon">⚡</div>
            <div class="rc-label">KPIs · Eficiência Operacional</div>
            <div class="rc-title">Análise de Eficiência OPs</div>
            <div class="rc-desc">
                Métricas de eficiência, produtividade e desempenho de corte por linha de produto — Manta, Lençol e Giattex.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Eficiência</span>
                <span class="rc-tag">KPIs</span>
                <span class="rc-tag">Manta · Lençol · Giattex</span>
            </div>
            <div style="margin-top:14px;background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.35);
                        border-radius:8px;padding:10px 14px;font-size:.82rem;color:#FCD34D;line-height:1.4;">
                🔧 <strong>Em desenvolvimento</strong> — funcionalidades ainda em construção.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.button("Abrir Dashboard  →", key="btn_eficiencia_main", use_container_width=True, disabled=True)

    st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
    col_back_inicio, *_ = st.columns([2, 5])
    with col_back_inicio:
        if st.button("🏢 Voltar ao Início", key="back_to_home", use_container_width=True):
            st.session_state.corte_screen = 'analysis_type'
            st.switch_page("app.py")

# SCREEN — EFICIÊNCIA DASHBOARD (UNIFIED WITH 3 TABS)

elif screen == 'eficiencia_dashboard':
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Eficiência de Corte</span>
    </div>
    """, unsafe_allow_html=True)
    
    from components.eficiencia_corte import render_dashboard_eficiencia
    render_dashboard_eficiencia()
    
    st.markdown("---")
    col_back_efic, *_ = st.columns([2, 5])
    with col_back_efic:
        if st.button("← Voltar ao Tipo de Análise", key="back_efic_analysis", use_container_width=True):
            _go('analysis_type')

# SCREEN — REGION SELECTOR

elif screen == 'regions':
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Rendimento de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Regiões</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-top:20px;">
        <div class="page-badge">🏭 Regiões</div>
        <h1 class="page-title">Selecione a <span class="accent">Região</span></h1>
        <p class="page-subtitle">Escolha a unidade de corte para acessar o painel de produção</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    col_arealva, col_iacanga, col_itaju = st.columns(3)

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
            _go('iacanga_rendimento')

    with col_itaju:
        st.markdown("""
        <div class="region-card" style="--rc-a:#064E3B; --rc-b:#059669; --rc-accent:#34D399;">
            <div class="rc-icon">🧵</div>
            <div class="rc-label">Unidade · Itaju</div>
            <div class="rc-title">Itaju</div>
            <div class="rc-desc">
                Corte Ponto Palito Marcelino. Acompanhamento da produção
                por OP e metas diárias da unidade de Itaju.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Ponto Palito</span>
                <span class="rc-tag">Marcelino</span>
                <span class="rc-tag">Estações</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Itaju  →", key="btn_itaju", use_container_width=True):
            _go('itaju')

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    col_back2, *_ = st.columns([2, 5])
    with col_back2:
        if st.button("← Voltar ao Tipo de Análise", key="back_to_analysis_type", use_container_width=True):
            _go('analysis_type')

# SCREEN — AREALVA PRODUCT SELECTOR

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
                <span class="rc-tag">OPs</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_manta", use_container_width=True):
            _go('arealva_manta')

    with col_lencol:
        st.markdown("""
        <div class="region-card" style="--rc-a:#1A3A1A; --rc-b:#4ECDC4; --rc-accent:#4ECDC4;">
            <div class="rc-icon">✂️</div>
            <div class="rc-label">Produto · Arealva</div>
            <div class="rc-title">Lençol</div>
            <div class="rc-desc">
                Painel completo de corte de lençol com metas, prestadores,
                empresas, categorias, análise temporal e financeira.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Prestadores</span>
                <span class="rc-tag">Empresas</span>
                <span class="rc-tag">Financeiro</span>
                <span class="rc-tag">Metas</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_lencol", use_container_width=True):
            _go('arealva_lencol')

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("← Voltar às Regiões", key="back_to_regions", use_container_width=True):
            _go('regions')

# SCREEN — IACANGA RENDIMENTO — DASHBOARD MANTAS GIATTEX

elif screen == 'iacanga_rendimento':

    # breadcrumb
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Iacanga · Mantas Giattex</span>
    </div>
    """, unsafe_allow_html=True)

    # load data
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

    # sidebar filters
    with st.sidebar:
        if not df_corte_iac.empty:
            st.info(
                f"📅 {df_corte_iac['DATA'].min().strftime('%d/%m/%Y')} → "
                f"{df_corte_iac['DATA'].max().strftime('%d/%m/%Y')}"
            )
        if st.sidebar.button("🔄 Atualizar Dados", key="iac_clear_cache", use_container_width=True):
            from utils.cache_manager import invalidate_all
            invalidate_all()
            st.cache_data.clear()
            st.rerun()
        st.sidebar.metric("📊 Registros", f"{len(df_corte_iac):,}".replace(",", "."))

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
    st.sidebar.caption(f"Registros carregados: {len(df_trabalho_iac):,}".replace(",", "."))

    # apply filters
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

    # meta total ponderada do recorte atual
    META_TOTAL_IAC = calcular_meta_total_ponderada_iacanga(df_filtrado_iac)

    render_filtros_btn()
    # dashboard header
    st.markdown('<div class="dash-header">✂️ Iacanga — Mantas Giattex</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dash-sub">Acompanhamento de produção com meta variável por tamanho '
        '(Solteiro / Casal / Queen / King) e estação (Máquina / Mesa / Burdays)</div>',
        unsafe_allow_html=True,
    )

    # Período efetivo para análise de dias úteis / sábados (Iacanga)
    _ini_iac = filtro_datas_iac[0] if (isinstance(filtro_datas_iac, tuple) and filtro_datas_iac[0]) else data_min_iac
    _fim_iac = filtro_datas_iac[1] if (isinstance(filtro_datas_iac, tuple) and filtro_datas_iac[1]) else data_max_iac

    # tabs
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
        cols_kpi[0].metric("✂️ Total de Peças", f"{total_pecas_iac:,.0f}".replace(",", "."))
        cols_kpi[1].metric("📋 Total de OPs", f"{total_ops_iac}")
        cols_kpi[2].metric("🎨 Cores Diferentes", f"{total_cores_iac}")
        _info_iac = _analisa_dias(df_filtrado_iac['DATA'].dt.date.unique(), _ini_iac, _fim_iac)
        _delta_iac = f"+{_info_iac['sabados']} sáb." if _info_iac['sabados'] > 0 else None
        _help_iac = ("⚠️ Sem registro: " + ", ".join(d.strftime('%d/%m') for d in _info_iac['ausentes'])) if _info_iac['ausentes'] else None
        cols_kpi[3].metric("📆 Dias Trabalhados", f"{dias_trab_iac}", delta=_delta_iac, delta_color="off", help=_help_iac)

        cols_kpi2 = st.columns(4)
        cols_kpi2[0].metric(
            "⚡ Média Peças/Dia",
            f"{media_dia_iac:,.0f}".replace(",", "."),
            delta=f"{delta_media_iac:+.1f}% vs Meta {META_TOTAL_IAC:,.0f}".replace(",", "."),
        )
        cols_kpi2[1].metric("🔧 Máquina", f"{pecas_maq_iac:,.0f}".replace(",", "."))
        cols_kpi2[2].metric("📐 Mesa", f"{pecas_mesa_iac:,.0f}".replace(",", "."))
        cols_kpi2[3].metric("🛠️ Burday's", f"{pecas_burday_iac:,.0f}".replace(",", "."))

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
                'Total_Pecas': lambda v: f"{int(v):,}".replace(",", "."),
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
                col_op1.metric("Peças Total", f"{df_op_iac['QUANTIDADE'].sum():,.0f}".replace(",", "."))
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
                _fn = lambda v: f"{int(v):,}".replace(",", ".")
                with cols_meta[i % n_cols]:
                    card_html = (
                        '<div style="background:#1a1a2e; border-radius:14px; padding:20px; color:white; '
                        'text-align:center; box-shadow:0 3px 12px rgba(0,0,0,0.3); margin-bottom:10px;">'
                        f'<div style="font-size:0.8rem; letter-spacing:1px; color:#aaa; '
                        f'text-transform:uppercase; margin-bottom:4px;">{estacao}</div>'
                        f'<div style="font-size:2.2rem; font-weight:800; color:white; margin:4px 0;">'
                        f'{_fn(media_b)}</div>'
                        f'<div style="font-size:0.85rem; color:#bbb; margin-bottom:10px;">'
                        f'Meta: {_fn(meta_b)} pçs/dia</div>'
                        '<div style="background:#333; border-radius:8px; height:14px; '
                        'overflow:hidden; margin:8px 0;">'
                        f'<div style="width:{pct_bar:.0f}%; height:100%; background:{cor_prog}; '
                        f'border-radius:8px; transition:width 0.5s;"></div>'
                        '</div>'
                        '<div style="display:flex; justify-content:space-between; '
                        'font-size:0.78rem; color:#999; margin-bottom:8px;">'
                        f'<span>0</span><span>{_fn(meta_b)}</span>'
                        '</div>'
                        f'<div style="font-size:1.1rem; font-weight:700; color:{cor_prog};">'
                        f'{pct:.0f}%</div>'
                        f'<div style="font-size:0.78rem; color:{cor_prog}; margin-top:2px;">'
                        f'{status} ({("+" if diff >= 0 else "")}{_fn(diff)})</div>'
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
                    _info_est_iac = _analisa_dias(df_est['DATA'].dt.date.unique(), _ini_iac, _fim_iac)
                    _delta_est_iac = f"+{_info_est_iac['sabados']} sáb." if _info_est_iac['sabados'] > 0 else None
                    _help_est_iac = ("⚠️ Sem registro: " + ", ".join(d.strftime('%d/%m') for d in _info_est_iac['ausentes'])) if _info_est_iac['ausentes'] else None
                    st.metric("Total Peças", f"{pecas_est:,.0f}".replace(",", "."))
                    st.metric("Dias Trabalhados", f"{dias_est}", delta=_delta_est_iac, delta_color="off", help=_help_est_iac)
                    st.metric(
                        "Média Peças/Dia", f"{media_pe:,.0f}".replace(",", "."),
                        delta=f"{delta_e:+,.0f} vs Meta {meta_e:,.0f}".replace(",", "."),
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
                            annotation_text=f"Média: {media_est:,.0f}".replace(",", "."),
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
                            line_width=2, annotation_text=f"🎯 Meta: {meta_estacao_iac:,.0f}".replace(",", "."),
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
                        f"{meta_estacao_iac:,.0f} peças".replace(",", "."),
                        f"{prod_dia_stats.mean():,.0f}".replace(",", "."),
                        f"{pct_meta_est:.1f}%",
                        f"{dias_acima} de {dias_total_est} ({(dias_acima/max(dias_total_est,1)*100):.0f}%)",
                        f"{prod_dia_stats.median():,.0f}".replace(",", "."),
                        f"{prod_dia_stats.std():,.0f}".replace(",", ".") if len(prod_dia_stats) > 1 else "N/A",
                        f"{prod_dia_stats.min():,.0f}".replace(",", "."),
                        f"{prod_dia_stats.max():,.0f}".replace(",", "."),
                        f"{(prod_dia_stats.std()/prod_dia_stats.mean()*100):,.1f}%".replace(",", ".")
                        if prod_dia_stats.mean() > 0 and len(prod_dia_stats) > 1 else "N/A",
                        f"{df_est['QUANTIDADE'].sum():,.0f}".replace(",", "."),
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

    # footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#606878; font-size:0.82rem;'>"
        "✂️ Iacanga · Mantas Giattex &nbsp;|&nbsp; "
        "Meta variável por tamanho + estação (ponderada pelo mix do dia) &nbsp;|&nbsp; "
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        "</div>",
        unsafe_allow_html=True,
    )

# SCREEN — AREALVA MANTA DASHBOARD

elif screen == 'arealva_manta':

    # breadcrumb
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Arealva</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Manta</span>
    </div>
    """, unsafe_allow_html=True)

    # load data
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

    # sidebar filters
    with st.sidebar:
        st.info(f"📅 {df_corte['DATA'].min().strftime('%d/%m/%Y')} → {df_corte['DATA'].max().strftime('%d/%m/%Y')}")
        if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
            from utils.cache_manager import invalidate_all
            invalidate_all()
            st.cache_data.clear()
            st.rerun()
        st.sidebar.metric("📊 Registros", f"{len(df_corte):,}".replace(",", "."))

    df_trabalho = df_corte.copy()

    if 'filtro_ops' not in st.session_state:
        st.session_state.filtro_ops = []
    if 'filtro_estacoes' not in st.session_state:
        st.session_state.filtro_estacoes = []
    if 'filtro_produtos' not in st.session_state:
        st.session_state.filtro_produtos = []
    if 'filtro_tamanhos' not in st.session_state:
        st.session_state.filtro_tamanhos = []
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

    # Filtro de Tamanho — exibido apenas quando a planilha tem valores preenchidos
    tamanhos_disponiveis = sorted(
        v for v in df_trabalho['TAMANHO'].dropna().unique()
        if str(v).strip() not in ('', 'nan', 'NAN')
    )
    if tamanhos_disponiveis:
        default_tam = [t for t in st.session_state.filtro_tamanhos if t in tamanhos_disponiveis]
        tamanhos_selecionados = st.sidebar.multiselect(
            "📏 Filtrar por Tamanho", options=tamanhos_disponiveis, default=default_tam,
        )
        st.session_state.filtro_tamanhos = tamanhos_selecionados
    else:
        tamanhos_selecionados = []
        st.session_state.filtro_tamanhos = []

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
    st.sidebar.caption(f"Registros filtrados: {len(df_trabalho):,}".replace(",", "."))

    # apply filters
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
    if tamanhos_selecionados:
        df_filtrado = df_filtrado[df_filtrado['TAMANHO'].isin(tamanhos_selecionados)]

    # Meta total ponderada para o recorte atual (substitui META_TOTAL fixo)
    META_TOTAL_AREALVA = calcular_meta_total_ponderada_arealva(df_filtrado)

    # Período efetivo para análise de dias úteis / sábados
    _ini_periodo = filtro_datas[0] if (isinstance(filtro_datas, tuple) and filtro_datas[0]) else data_min
    _fim_periodo = filtro_datas[1] if (isinstance(filtro_datas, tuple) and filtro_datas[1]) else data_max

    render_filtros_btn()
    # dashboard header
    st.markdown('<div class="dash-header">✂️ Arealva — Manta</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-sub">Acompanhamento de produção e desempenho por estação</div>', unsafe_allow_html=True)

    # tabs
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "📋 Acompanhamento por OP", "🏭 Produção por Estação"])

    # TAB 1
    with tab1:
        st.markdown("### 📊 Indicadores Gerais")
        total_pecas = df_filtrado['QUANTIDADE'].sum()
        total_ops = df_filtrado['OP'].nunique()
        total_cores = df_filtrado['COR'].nunique()
        dias_trabalhados = df_filtrado['DATA'].dt.date.nunique()
        media_dia = total_pecas / max(dias_trabalhados, 1)
        delta_media = ((media_dia / META_TOTAL_AREALVA) - 1) * 100 if META_TOTAL_AREALVA > 0 else 0

        cols_kpi = st.columns(4)
        cols_kpi[0].metric("✂️ Total de Peças", f"{total_pecas:,.0f}".replace(",", "."))
        cols_kpi[1].metric("📋 Total de OPs", f"{total_ops}")
        cols_kpi[2].metric("🎨 Cores Diferentes", f"{total_cores}")
        _info_dias = _analisa_dias(df_filtrado['DATA'].dt.date.unique(), _ini_periodo, _fim_periodo)
        _delta_dias = f"+{_info_dias['sabados']} sáb." if _info_dias['sabados'] > 0 else None
        _help_dias = ("⚠️ Sem registro: " + ", ".join(d.strftime('%d/%m') for d in _info_dias['ausentes'])) if _info_dias['ausentes'] else None
        cols_kpi[3].metric("📆 Dias Trabalhados", f"{dias_trabalhados}", delta=_delta_dias, delta_color="off", help=_help_dias)

        _ICONS_EST = {"MAQUINA": "🔧", "MESA 1": "📐", "MESA 2": "📐"}
        cols_kpi2 = st.columns(1 + len(METAS))
        cols_kpi2[0].metric("⚡ Média Peças/Dia", f"{media_dia:,.0f}".replace(",", "."), delta=f"{delta_media:+.1f}% vs Meta {META_TOTAL_AREALVA:,.0f}".replace(",", "."))
        for _j, (_est, _) in enumerate(METAS.items()):
            _icon = _ICONS_EST.get(_est, "🏭")
            _pecas = df_filtrado[df_filtrado['ESTACAO'] == _est]['QUANTIDADE'].sum()
            cols_kpi2[_j + 1].metric(f"{_icon} {_est}", f"{_pecas:,.0f}".replace(",", "."))

        st.markdown("---")
        st.markdown("#### 📈 Produção Diária (Peças)")
        prod_diaria = df_filtrado.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
        prod_diaria['ACIMA_META'] = prod_diaria['QUANTIDADE'] >= META_TOTAL_AREALVA

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
        fig1.add_hline(y=META_TOTAL_AREALVA, line_dash="dash", line_color="#aaa", line_width=2,
                       annotation_text=f"Meta: {META_TOTAL_AREALVA:,.0f}".replace(",", "."), annotation_font_size=12,
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
                'Total_Pecas': lambda v: f"{int(v):,}".replace(",", "."),
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
            col_op1.metric("Peças Total", f"{df_op['QUANTIDADE'].sum():,.0f}".replace(",", "."))
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
        estacoes = list(METAS.keys())
        _PALETA = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2']
        cores_estacao = {est: _PALETA[i % len(_PALETA)] for i, est in enumerate(estacoes)}

        st.markdown("#### 🎯 Progresso vs Meta Diária (Média Peças/Dia)")
        cols_meta = st.columns(len(estacoes))
        for i, estacao in enumerate(estacoes):
            df_est_b = df_filtrado[df_filtrado['ESTACAO'] == estacao]
            dias_b = df_est_b['DATA'].dt.date.nunique()
            media_b = df_est_b['QUANTIDADE'].sum() / max(dias_b, 1)
            meta_b = meta_diaria_por_estacao_arealva(df_filtrado, estacao)
            if meta_b == 0:
                meta_b = METAS.get(estacao, 0)
            pct = min((media_b / meta_b * 100), 150) if meta_b > 0 else 0
            diff = media_b - meta_b
            cor_prog = '#2ca02c' if pct >= 100 else ('#ff7f0e' if pct >= 80 else '#d62728')
            status = '✅ META ATINGIDA' if pct >= 100 else ('⚠️ PRÓXIMO DA META' if pct >= 80 else '❌ ABAIXO DA META')
            pct_bar = min(pct, 100)
            _fn = lambda v: f"{int(v):,}".replace(",", ".")
            # Nota "(ponderada)" quando há tamanhos preenchidos na estação
            _tem_tam_b = (
                'TAMANHO' in df_est_b.columns
                and df_est_b['TAMANHO'].str.strip().replace('', pd.NA).notna().any()
            )
            _nota_meta = ' <span style="font-size:0.7rem;color:#888;">(ponderada)</span>' if _tem_tam_b else ''
            with cols_meta[i]:
                card_html = (
                    '<div style="background:#1a1a2e; border-radius:14px; padding:20px; color:white; '
                    'text-align:center; box-shadow:0 3px 12px rgba(0,0,0,0.3);">'
                    f'<div style="font-size:0.8rem; letter-spacing:1px; color:#aaa; '
                    f'text-transform:uppercase; margin-bottom:4px;">{estacao}</div>'
                    f'<div style="font-size:2.2rem; font-weight:800; color:white; margin:4px 0;">'
                    f'{_fn(media_b)}</div>'
                    f'<div style="font-size:0.85rem; color:#bbb; margin-bottom:10px;">'
                    f'Meta: {_fn(meta_b)} pçs/dia{_nota_meta}</div>'
                    '<div style="background:#333; border-radius:8px; height:14px; '
                    'overflow:hidden; margin:8px 0;">'
                    f'<div style="width:{pct_bar:.0f}%; height:100%; background:{cor_prog}; '
                    'border-radius:8px;"></div>'
                    '</div>'
                    '<div style="display:flex; justify-content:space-between; '
                    'font-size:0.78rem; color:#999; margin-bottom:8px;">'
                    f'<span>0</span><span>{_fn(meta_b)}</span>'
                    '</div>'
                    f'<div style="font-size:1.1rem; font-weight:700; color:{cor_prog};">{pct:.0f}%</div>'
                    f'<div style="font-size:0.78rem; color:{cor_prog}; margin-top:2px;">'
                    f'{status} ({("+" if diff >= 0 else "")}{_fn(diff)})</div>'
                    '</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("---")
        cols_est = st.columns(len(estacoes))
        for i, estacao in enumerate(estacoes):
            df_est = df_filtrado[df_filtrado['ESTACAO'] == estacao]
            with cols_est[i]:
                st.markdown(f"#### {estacao}")
                dias_est = df_est['DATA'].dt.date.nunique()
                pecas_est = df_est['QUANTIDADE'].sum()
                media_pecas_est = pecas_est / max(dias_est, 1)
                meta_est = meta_diaria_por_estacao_arealva(df_filtrado, estacao)
                if meta_est == 0:
                    meta_est = METAS.get(estacao, 0)
                pct_meta = (media_pecas_est / meta_est * 100) if meta_est > 0 else 0
                delta_meta = media_pecas_est - meta_est
                st.metric("Total Peças", f"{pecas_est:,.0f}".replace(",", "."))
                _info_est = _analisa_dias(df_est['DATA'].dt.date.unique(), _ini_periodo, _fim_periodo)
                _delta_est = f"+{_info_est['sabados']} sáb." if _info_est['sabados'] > 0 else None
                _help_est = ("⚠️ Sem registro: " + ", ".join(d.strftime('%d/%m') for d in _info_est['ausentes'])) if _info_est['ausentes'] else None
                st.metric("Dias Trabalhados", f"{dias_est}", delta=_delta_est, delta_color="off", help=_help_est)
                st.metric("Média Peças/Dia", f"{media_pecas_est:,.0f}".replace(",", "."),
                          delta=f"{delta_meta:+,.0f} vs Meta {meta_est:,.0f}".replace(",", "."))
                st.metric("% da Meta", f"{pct_meta:.1f}%")

        st.markdown("---")
        st.markdown("#### 📈 Produção Diária por Estação (com Metas)")
        prod_est_dia = df_filtrado.groupby(['DATA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
        fig_est1 = px.line(prod_est_dia, x='DATA', y='QUANTIDADE', color='ESTACAO',
                           labels={'DATA': 'Data', 'QUANTIDADE': 'Peças', 'ESTACAO': 'Estação'},
                           color_discrete_map=cores_estacao, markers=True)
        # Meta ponderada diária por estação (flutua conforme mix de tamanhos)
        for est_nm in estacoes:
            _df_est_d = df_filtrado[df_filtrado['ESTACAO'] == est_nm]
            _linhas_meta = []
            for _data, _g in _df_est_d.groupby('DATA'):
                _linhas_meta.append({'DATA': _data, 'META': meta_ponderada_arealva(_g)})
            if _linhas_meta:
                _df_meta_est = pd.DataFrame(_linhas_meta).sort_values('DATA')
                fig_est1.add_trace(go.Scatter(
                    x=_df_meta_est['DATA'], y=_df_meta_est['META'],
                    name=f'Meta {est_nm}',
                    line=dict(color=cores_estacao.get(est_nm, '#aaa'), dash='dot', width=2),
                    mode='lines', showlegend=True,
                ))
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
                    # Calcula META_DIA ponderada por data (padrão Iacanga)
                    _linhas_d_exp = []
                    for _data_d, _g_d in df_est.groupby('DATA'):
                        _linhas_d_exp.append({
                            'DATA': _data_d,
                            'QUANTIDADE': _g_d['QUANTIDADE'].sum(),
                            'META_DIA': meta_ponderada_arealva(_g_d),
                        })
                    prod_dia_est = pd.DataFrame(_linhas_d_exp).sort_values('DATA') if _linhas_d_exp else pd.DataFrame(columns=['DATA', 'QUANTIDADE', 'META_DIA'])
                    fig_tend = go.Figure()
                    fig_tend.add_trace(go.Bar(x=prod_dia_est['DATA'], y=prod_dia_est['QUANTIDADE'],
                                              name='Peças/Dia', marker_color=cores_estacao[estacao], opacity=0.7))
                    if len(prod_dia_est) >= 5:
                        prod_dia_est['MM5'] = prod_dia_est['QUANTIDADE'].rolling(5).mean()
                        fig_tend.add_trace(go.Scatter(x=prod_dia_est['DATA'], y=prod_dia_est['MM5'],
                                                      name='Média Móvel (5d)', line=dict(color='red', width=2)))
                    media_est_val = prod_dia_est['QUANTIDADE'].mean() if not prod_dia_est.empty else 0
                    fig_tend.add_hline(y=media_est_val, line_dash="dash", line_color="gray",
                                       annotation_text=f"Média: {media_est_val:,.0f}".replace(",", "."))
                    if not prod_dia_est.empty and 'META_DIA' in prod_dia_est.columns:
                        fig_tend.add_trace(go.Scatter(
                            x=prod_dia_est['DATA'], y=prod_dia_est['META_DIA'],
                            name='Meta (ponderada)',
                            line=dict(color='#2ca02c', width=2, dash='dot'),
                            mode='lines+markers', marker=dict(symbol='diamond', size=7),
                        ))
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
                    meta_box = meta_diaria_por_estacao_arealva(df_filtrado, estacao)
                    if meta_box == 0:
                        meta_box = METAS.get(estacao, 0)
                    if meta_box > 0:
                        fig_box.add_hline(y=meta_box, line_dash="dot", line_color="green",
                                          line_width=2, annotation_text=f"🎯 Meta: {meta_box:,.0f}".replace(",", "."),
                                          annotation_position="top left")
                    fig_box.update_layout(title=f"Consistência — {estacao}", height=400,
                                          margin=dict(l=20, r=20, t=40, b=20),
                                          paper_bgcolor='rgba(0,0,0,0)', font_color='#E0E0E0',
                                          plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_box, use_container_width=True)

                prod_dia_stats = df_est.groupby('DATA')['QUANTIDADE'].sum()
                meta_est_v = meta_diaria_por_estacao_arealva(df_filtrado, estacao)
                if meta_est_v == 0:
                    meta_est_v = METAS.get(estacao, 0)
                pct_meta_est = (prod_dia_stats.mean() / meta_est_v * 100) if meta_est_v > 0 else 0
                # Dias acima da meta: compara com meta ponderada de cada dia (padrão Iacanga)
                dias_acima = 0
                for _data_a, _g_a in df_est.groupby('DATA'):
                    _meta_dia_a = meta_ponderada_arealva(_g_a)
                    if _g_a['QUANTIDADE'].sum() >= _meta_dia_a and _meta_dia_a > 0:
                        dias_acima += 1
                dias_total_est = len(prod_dia_stats)
                stats_df = pd.DataFrame({
                    'Estatística': ['🎯 META DIÁRIA (ponderada)', '📊 Média/Dia', '% da Meta',
                                    'Dias Acima da Meta', 'Mediana/Dia', 'Desvio Padrão',
                                    'Mínimo/Dia', 'Máximo/Dia', 'Coef. Variação (%)', 'Total Peças'],
                    'Valor': [
                        f"{meta_est_v:,.0f} peças".replace(",", "."),
                        f"{prod_dia_stats.mean():,.0f}".replace(",", "."),
                        f"{pct_meta_est:.1f}%",
                        f"{dias_acima} de {dias_total_est} ({(dias_acima / max(dias_total_est, 1) * 100):.0f}%)",
                        f"{prod_dia_stats.median():,.0f}".replace(",", "."),
                        f"{prod_dia_stats.std():,.0f}".replace(",", ".") if len(prod_dia_stats) > 1 else "N/A",
                        f"{prod_dia_stats.min():,.0f}".replace(",", "."),
                        f"{prod_dia_stats.max():,.0f}".replace(",", "."),
                        f"{(prod_dia_stats.std() / prod_dia_stats.mean() * 100):,.1f}%".replace(",", ".")
                        if prod_dia_stats.mean() > 0 and len(prod_dia_stats) > 1 else "N/A",
                        f"{df_est['QUANTIDADE'].sum():,.0f}".replace(",", "."),
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
        # Meta semanal ponderada: soma da meta ponderada de cada dia dentro da semana
        _metas_sem = []
        for (_sem, _est_s), _g_s in df_filtrado.groupby(['SEMANA', 'ESTACAO']):
            _meta_sem_total = 0.0
            for _data_s, _g_dia_s in _g_s.groupby('DATA'):
                _meta_sem_total += meta_ponderada_arealva(_g_dia_s)
            _metas_sem.append({'SEMANA': _sem, 'ESTACAO': _est_s, 'META_SEMANAL': _meta_sem_total})
        if _metas_sem:
            prod_semanal = prod_semanal.merge(
                pd.DataFrame(_metas_sem), on=['SEMANA', 'ESTACAO'], how='left',
            )
            prod_semanal['META_SEMANAL'] = prod_semanal['META_SEMANAL'].fillna(0)
        else:
            prod_semanal['META_SEMANAL'] = 0
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

    # footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#606878; font-size:0.82rem;'>"
        "✂️ Arealva · Manta &nbsp;|&nbsp; Alimentado pela planilha CONTROLE GERAL MANTAS.xlsx &nbsp;|&nbsp; "
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        "</div>",
        unsafe_allow_html=True,
    )

# SCREEN — IACANGA EFICIÊNCIA — PLACEHOLDER (EM BREVE)

elif screen == 'iacanga_eficiencia':
    
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Iacanga</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Eficiência de Corte</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-top:20px;">
        <div class="page-badge">⚡ Iacanga</div>
        <h1 class="page-title">Eficiência de <span class="accent">Corte</span></h1>
        <p class="page-subtitle">Análise de rendimento e eficiência operacional</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    # Placeholder - Em breve
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="
            background: linear-gradient(160deg, rgba(171,71,188,0.1) 0%, rgba(123,47,190,0.1) 100%);
            border: 2px solid rgba(171,71,188,0.3);
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            margin-top: 40px;
        ">
            <div style="font-size: 3.5rem; margin-bottom: 20px;">🔜</div>
            <h2 style="color: #FFFFFF; font-size: 1.8rem; margin-bottom: 10px;">Dashboard em Desenvolvimento</h2>
            <p style="color: #B0B0B0; font-size: 1.1rem; line-height: 1.6; margin-bottom: 30px;">
                Este painel de Eficiência de Corte está sendo construído e trará análises detalhadas sobre:
            </p>
            <div style="
                background: rgba(171,71,188,0.1);
                border-left: 4px solid #AB47BC;
                border-radius: 8px;
                padding: 20px;
                text-align: left;
                margin: 20px 0;
                color: #E0E0E0;
                font-size: 0.95rem;
                line-height: 1.8;
            ">
                <strong>📊 Métricas Planejadas:</strong><br>
                • Rendimento por OP em quilogramas (kgs)<br>
                • Taxa de eficiência operacional<br>
                • Produtividade média por cortador<br>
                • Comparativos e tendências<br>
                • Análise de rejeição e qualidade
            </div>
            <p style="color: #888; font-size: 0.9rem; margin-top: 30px;">
                ⏰ Voltaremos em breve com uma experiência completa e robusta!
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
    col_back_ef, *_ = st.columns([2, 5])
    with col_back_ef:
        if st.button("← Voltar à Seleção de Análise", key="back_to_type_selection", use_container_width=True):
            _go('iacanga_type_selection')

# SCREEN — AREALVA LENÇOL DASHBOARD

elif screen == 'arealva_lencol':

    # CSS específico do lençol
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* ── Métricas – estilo do dashboard original ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg,#1C1C22 0%,#28282E 100%) !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,.3) !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    div[data-testid="stMetric"] label {
        color: #A0AEC0 !important;
        font-size: .72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: .8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.65rem !important;
        font-family: 'Sora', sans-serif !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] * {
        font-family: 'Sora', sans-serif !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        font-size: .8rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    /* ── Seções e utilitários ── */
    .ln-sec {
        font-size:1rem;font-weight:700;color:#E2E8F0;
        margin:20px 0 10px 0;padding-bottom:6px;
        border-bottom:2px solid rgba(78,205,196,.3);
    }
    .ln-insight {
        background:linear-gradient(135deg,rgba(78,205,196,.07),rgba(69,183,209,.04));
        border:1px solid rgba(78,205,196,.22);border-radius:12px;
        padding:14px 18px;margin:8px 0;
    }
    .ln-insight h4 {color:#4ECDC4;margin:0 0 6px;font-size:.8rem;
        text-transform:uppercase;letter-spacing:.5px}
    .ln-insight p {color:#CBD5E0;margin:0;font-size:.88rem;line-height:1.55}
    .ln-rank-gold   {color:#FFD700;font-weight:800;font-size:1.1rem}
    .ln-rank-silver {color:#C0C0C0;font-weight:700}
    .ln-rank-bronze {color:#CD7F32;font-weight:700}
    </style>
    """, unsafe_allow_html=True)

    # Breadcrumb
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Arealva</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Lençol</span>
    </div>
    """, unsafe_allow_html=True)

    # Carregar dados
    with st.spinner("⏳ Carregando dados da planilha de lençol…"):
        try:
            df_raw_ln = load_corte_lencol()
            df_metas_ln = load_metas_lencol()
        except Exception as _e_ln:
            st.error(f"❌ Erro ao carregar dados: {_e_ln}")
            st.info("Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link'.")
            st.stop()

    if df_raw_ln.empty:
        st.error("❌ Nenhum dado encontrado na planilha de lençol.")
        st.stop()

    data_min_ln = df_raw_ln["DATA"].min().date()
    data_max_ln = df_raw_ln["DATA"].max().date()
    hoje_ln = datetime.now().date()

    # sidebar filters
    with st.sidebar:
        st.caption(f"Atualizado a cada {LENCOL_CACHE_TTL}s · {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Limpar Cache", key="ln_clear", use_container_width=True):
            load_corte_lencol.clear()
            load_metas_lencol.clear()
            st.rerun()

        st.markdown("**📅 Período**")
        periodo_opt_ln = st.radio(
            "Preset lençol",
            ["Personalizado", "7 dias", "30 dias", "Mês atual", "Todo o período"],
            index=4, label_visibility="collapsed", key="ln_periodo_opt",
        )

        if periodo_opt_ln == "7 dias":
            p_ini_ln, p_fim_ln = hoje_ln - timedelta(days=6), hoje_ln
        elif periodo_opt_ln == "30 dias":
            p_ini_ln, p_fim_ln = hoje_ln - timedelta(days=29), hoje_ln
        elif periodo_opt_ln == "Mês atual":
            p_ini_ln = hoje_ln.replace(day=1)
            p_fim_ln = hoje_ln
            # Início de mês: ainda não há dados do mês corrente → recua para o mês anterior
            if p_ini_ln > data_max_ln:
                p_fim_ln = p_ini_ln - timedelta(days=1)   # último dia do mês anterior
                p_ini_ln = p_fim_ln.replace(day=1)
        elif periodo_opt_ln == "Todo o período":
            p_ini_ln, p_fim_ln = data_min_ln, data_max_ln
        else:
            if "ln_periodo_ini" not in st.session_state:
                st.session_state["ln_periodo_ini"] = data_min_ln
            if "ln_periodo_fim" not in st.session_state:
                st.session_state["ln_periodo_fim"] = data_max_ln
            st.session_state["ln_periodo_ini"] = max(min(st.session_state["ln_periodo_ini"], data_max_ln), data_min_ln)
            st.session_state["ln_periodo_fim"] = max(min(st.session_state["ln_periodo_fim"], data_max_ln), data_min_ln)
            col_d1_ln, col_d2_ln = st.columns(2)
            with col_d1_ln:
                p_ini_ln = st.date_input("De", value=st.session_state["ln_periodo_ini"],
                                         format="DD/MM/YYYY", key="ln_periodo_ini")
            with col_d2_ln:
                p_fim_ln = st.date_input("Até", value=st.session_state["ln_periodo_fim"],
                                         format="DD/MM/YYYY", key="ln_periodo_fim")
            if p_ini_ln > p_fim_ln:
                st.error("❌ Data 'De' não pode ser maior que 'Até'")

        # Clamp apenas ao mínimo disponível; não corta o fim (evita range invertido)
        p_ini_ln = max(p_ini_ln, data_min_ln)
        # p_fim_ln não é clampeado para data_max_ln: o filtro retorna só o que existe

        st.markdown("**🔍 Filtros**")
        todos_prest_ln = sorted([x for x in df_raw_ln["PRESTADOR"].unique() if pd.notna(x) and str(x).strip()])
        sel_prest_ln = st.multiselect("Prestador", todos_prest_ln, placeholder="Todos", key="ln_prest")

        todas_emp_ln = sorted([x for x in df_raw_ln["EMPRESA"].unique() if pd.notna(x) and str(x).strip()])
        sel_emp_ln = st.multiselect("Empresa", todas_emp_ln, placeholder="Todas", key="ln_emp")

        todas_cats_ln = sorted([x for x in df_raw_ln["CAT_BASE"].unique() if pd.notna(x) and str(x).strip()])
        sel_cat_ln = st.multiselect("Categoria", todas_cats_ln, placeholder="Todas", key="ln_cat")

        st.caption(f"📊 {len(df_raw_ln):,} registros totais".replace(",", "."))

    # aplicar filtros
    df_ln = df_raw_ln[
        (df_raw_ln["DATA"].dt.date >= p_ini_ln) &
        (df_raw_ln["DATA"].dt.date <= p_fim_ln)
    ].copy()
    if sel_prest_ln:
        df_ln = df_ln[df_ln["PRESTADOR"].isin(sel_prest_ln)]
    if sel_emp_ln:
        df_ln = df_ln[df_ln["EMPRESA"].isin(sel_emp_ln)]
    if sel_cat_ln:
        df_ln = df_ln[df_ln["CAT_BASE"].isin(sel_cat_ln)]

    if df_ln.empty:
        st.warning("⚠️ Nenhum dado para os filtros selecionados.")
        st.stop()

    # métricas globais
    total_pecas_ln = int(df_ln["QUANT"].sum())
    total_valor_ln = df_ln["VALOR_RECEBER"].sum()

    # Caseamento jogo × fundo — separa os fundos do total de peças
    # (usa CATEGORIA + TECIDO: o fundo muitas vezes só aparece no TECIDO)
    _tipos_jf_ln, _tams_jf_ln = _lencol_tipos_tams(df_ln)
    df_ln = df_ln.assign(_TIPO_JF=_tipos_jf_ln, _TAM_JF=_tams_jf_ln)
    total_fundos_ln = int(df_ln.loc[df_ln["_TIPO_JF"] == "FUNDO", "QUANT"].sum())
    total_jogos_duplo_ln = int(df_ln.loc[df_ln["_TIPO_JF"] == "JOGO_DUPLO", "QUANT"].sum())
    total_sem_fundo_ln = total_pecas_ln - total_fundos_ln

    dias_trab_ln = (p_fim_ln - p_ini_ln).days + 1
    dias_com_dados_ln = df_ln["DATA"].dt.date.nunique()
    # Média diária baseada nas peças SEM fundo (consistente com o KPI principal)
    media_diaria_ln = total_sem_fundo_ln / dias_com_dados_ln if dias_com_dados_ln else 0
    n_prestadores_ln = df_ln["PRESTADOR"].nunique()
    n_empresas_ln = df_ln["EMPRESA"].nunique()
    ticket_medio_ln = total_valor_ln / total_pecas_ln if total_pecas_ln else 0
    top_prestador_ln = df_ln.groupby("PRESTADOR")["QUANT"].sum().idxmax() if not df_ln.empty else "—"
    top_empresa_ln = df_ln.groupby("EMPRESA")["QUANT"].sum().idxmax() if not df_ln.empty else "—"

    dias_periodo_ln = (p_fim_ln - p_ini_ln).days + 1
    p_ini_ant_ln = p_ini_ln - timedelta(days=dias_periodo_ln)
    p_fim_ant_ln = p_ini_ln - timedelta(days=1)
    df_ant_ln = df_raw_ln[
        (df_raw_ln["DATA"].dt.date >= p_ini_ant_ln) &
        (df_raw_ln["DATA"].dt.date <= p_fim_ant_ln)
    ]
    if sel_prest_ln: df_ant_ln = df_ant_ln[df_ant_ln["PRESTADOR"].isin(sel_prest_ln)]
    if sel_emp_ln:   df_ant_ln = df_ant_ln[df_ant_ln["EMPRESA"].isin(sel_emp_ln)]
    if sel_cat_ln:   df_ant_ln = df_ant_ln[df_ant_ln["CAT_BASE"].isin(sel_cat_ln)]
    pecas_ant_ln = int(df_ant_ln["QUANT"].sum()) if not df_ant_ln.empty else 0
    valor_ant_ln = df_ant_ln["VALOR_RECEBER"].sum() if not df_ant_ln.empty else 0
    # Peças do período anterior também sem fundo (delta do KPI principal)
    if not df_ant_ln.empty:
        _tipos_ant_ln, _ = _lencol_tipos_tams(df_ant_ln)
        _mask_fundo_ant = np.array([tp == "FUNDO" for tp in _tipos_ant_ln])
        _fundos_ant_ln = int(df_ant_ln.loc[_mask_fundo_ant, "QUANT"].sum())
    else:
        _fundos_ant_ln = 0
    pecas_ant_sf_ln = pecas_ant_ln - _fundos_ant_ln
    delta_pecas_ln = ((total_sem_fundo_ln - pecas_ant_sf_ln) / pecas_ant_sf_ln * 100) if (pecas_ant_sf_ln and periodo_opt_ln != "Todo o período") else None
    delta_valor_ln = ((total_valor_ln - valor_ant_ln) / valor_ant_ln * 100) if (valor_ant_ln and periodo_opt_ln != "Todo o período") else None

    status_pg_ln = "Pago" if p_fim_ln < data_max_ln else "A Pagar"

    render_filtros_btn()
    # header
    st.markdown(
        f"<h1 style='text-align:center;color:#FFFFFF;font-size:2rem;"
        f"font-weight:800;margin-bottom:2px'>✂️ Dashboard Corte · Lençol</h1>"
        f"<p style='text-align:center;color:#718096;font-size:.9rem;margin-bottom:0'>"
        f"{p_ini_ln.strftime('%d/%m/%Y')} — {p_fim_ln.strftime('%d/%m/%Y')} · "
        f"{total_pecas_ln:,} peças · {dias_trab_ln} dias no período</p>".replace(",", "."),
        unsafe_allow_html=True,
    )
    st.divider()

    # abas
    tabs_ln = st.tabs([
        "📊 Visão Geral", "👥 Prestadores", "📋 OPs",
        "🏭 Empresas", "📦 Categorias", "📅 Temporal",
        "💰 Financeiro", "🎯 Metas", "🏆 Ranking",
    ])

    # tab 1 — visão geral
    with tabs_ln[0]:
        c1, c2, c3, c4 = st.columns(4)
        kd_p = lencol_delta_icon(delta_pecas_ln) if delta_pecas_ln is not None else None
        kd_v = lencol_delta_icon(delta_valor_ln) if delta_valor_ln is not None else None
        _help_pecas_ln = (
            f"Total bruto: {lencol_fmt_num(total_pecas_ln)} peças. "
            f"Exclui {lencol_fmt_num(total_fundos_ln)} fundos de jogo de cama "
            f"(cortados à parte, identificados pelo tecido). Veja o caseamento abaixo."
        ) if total_fundos_ln > 0 else None
        c1.metric("🧵 Peças (s/ fundo)", lencol_fmt_num(total_sem_fundo_ln), kd_p, help=_help_pecas_ln)
        c2.metric(f"💰 Total {status_pg_ln}", lencol_fmt_brl(total_valor_ln), kd_v)
        _info_ln = _analisa_dias(df_ln["DATA"].dt.date.unique(), p_ini_ln, p_fim_ln)
        _delta_ln = f"+{_info_ln['sabados']} sáb." if _info_ln['sabados'] > 0 else None
        _help_ln = ("⚠️ Sem registro: " + ", ".join(d.strftime('%d/%m') for d in _info_ln['ausentes'])) if _info_ln['ausentes'] else None
        c3.metric("📆 Dias Trabalhados", str(dias_com_dados_ln), delta=_delta_ln, delta_color="off", help=_help_ln)
        c4.metric("📈 Média Diária", lencol_fmt_num(media_diaria_ln, 0) + " pç/dia")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("👷 Prestadores", str(n_prestadores_ln))
        c6.metric("🏭 Empresas", str(n_empresas_ln))
        c7.metric("🥇 Top Prestador", top_prestador_ln)
        c8.metric("🏆 Top Empresa", top_empresa_ln)

        # ── Caseamento Jogo Duplo × Fundo ────────────────────────────────────
        _casea_ln = lencol_caseamento(df_ln)
        if total_fundos_ln > 0 or not _casea_ln.empty:
            st.markdown("<div class='ln-sec'>🔄 Caseamento Jogo Duplo × Fundo</div>", unsafe_allow_html=True)
            st.caption(
                "Cada jogo duplo precisa de um fundo correspondente (corte à parte). "
                "As quantidades devem casear por OP e tamanho. "
                "⚠️ Este caseamento olha **só os jogos duplos das OPs que tiveram fundo** — "
                "por isso é menor que o KPI 'Peças (s/ fundo)', que inclui também jogos "
                "simples e outros produtos (fronha, lençol avulso, etc.)."
            )
            _jogo_em_op_fundo = int(_casea_ln["JOGO"].sum()) if not _casea_ln.empty else 0
            _fundo_em_op_fundo = int(_casea_ln["FUNDO"].sum()) if not _casea_ln.empty else 0
            # Saldo de fundos = FUNDO − JOGO (negativo = faltam fundos)
            _dif_liq_ln = _fundo_em_op_fundo - _jogo_em_op_fundo
            _ops_diverg_ln = int((_casea_ln["DIFERENCA"] != 0).sum()) if not _casea_ln.empty else 0
            _ops_total_casea = _casea_ln["OP"].nunique() if not _casea_ln.empty else 0

            # Jogos duplos de OPs que NÃO tiveram fundo no período = ficam fora do caseamento
            _jogos_sem_par = total_sem_fundo_ln - _jogo_em_op_fundo

            cj1, cj2, cj3, cj4 = st.columns(4)
            cj1.metric("🧩 Jogos Duplos", lencol_fmt_num(_jogo_em_op_fundo),
                       help="Jogos duplos das OPs que tiveram fundo (universo do caseamento).")
            cj2.metric("🔄 Fundos", lencol_fmt_num(_fundo_em_op_fundo),
                       help="Fundos de jogo cortados nas OPs que tiveram fundo.")
            cj3.metric("⚖️ Saldo de fundos (OPs c/ fundo)",
                       f"{'+' if _dif_liq_ln > 0 else ''}{lencol_fmt_num(_dif_liq_ln)}",
                       delta=("Caseado" if _dif_liq_ln == 0
                              else (f"Faltam {lencol_fmt_num(abs(_dif_liq_ln))} fundos" if _dif_liq_ln < 0
                                    else f"Sobram {lencol_fmt_num(_dif_liq_ln)} fundos")),
                       delta_color=("off" if _dif_liq_ln == 0 else "inverse"),
                       help="Fundo − Jogo somando as OPs que tiveram fundo. "
                            "Negativo = faltam fundos; positivo = sobram.")
            cj4.metric("🚩 OPs divergentes", f"{_ops_diverg_ln}/{_ops_total_casea}",
                       help="OPs (com fundo) onde jogo e fundo não caseiam por tamanho.")

            if _jogos_sem_par > 0:
                st.info(
                    f"ℹ️ **{lencol_fmt_num(_jogos_sem_par)} peças** são jogos duplos de OPs que **não tiveram "
                    f"corte de fundo no período filtrado** — por isso ficam fora do caseamento acima. "
                    f"O fundo dessas OPs pode ter sido cortado em outro período ou ainda não foi cortado.",
                    icon=None,
                )

            if not _casea_ln.empty:
                _div_ln = _casea_ln[_casea_ln["DIFERENCA"] != 0]
                if not _div_ln.empty:
                    with st.expander(f"🔎 Ver {len(_div_ln)} divergência(s) de caseamento", expanded=False):
                        _casea_show = _div_ln.copy()
                        _casea_show["JOGO"] = _casea_show["JOGO"].apply(lencol_fmt_num)
                        _casea_show["FUNDO"] = _casea_show["FUNDO"].apply(lencol_fmt_num)
                        _casea_show["DIFERENCA"] = _casea_show["DIFERENCA"].apply(
                            lambda v: f"{'+' if v > 0 else ''}{lencol_fmt_num(v)}"
                        )
                        st.dataframe(
                            _casea_show.rename(columns={
                                "OP": "OP", "TAMANHO": "Tamanho", "JOGO": "Jogo",
                                "FUNDO": "Fundo", "DIFERENCA": "Diferença", "STATUS": "Status",
                            }),
                            use_container_width=True, hide_index=True,
                        )
                        st.caption(
                            "🔴 Faltam fundos = cortou jogo mas não cortou fundo suficiente.  "
                            "🟠 Sobram fundos = cortou fundo a mais que o jogo."
                        )
                else:
                    st.success("✅ Todas as OPs com fundo estão caseadas (jogo = fundo por tamanho).")

        st.divider()
        col_a_ln, col_b_ln = st.columns([2, 1])

        with col_a_ln:
            st.markdown("<div class='ln-sec'>Produção Mensal</div>", unsafe_allow_html=True)
            df_mes_ln = (
                df_ln.groupby(["ANO_MES", "MES_NOME"])["QUANT"].sum()
                .reset_index().sort_values("ANO_MES")
            )
            fig_ln1 = go.Figure(go.Bar(
                x=df_mes_ln["ANO_MES"], y=df_mes_ln["QUANT"],
                text=[lencol_fmt_num(v) for v in df_mes_ln["QUANT"]],
                textposition="outside",
                textfont=dict(color="#CBD5E0", size=11),
                marker=dict(color=df_mes_ln["QUANT"],
                            colorscale=[[0, "#1C3A4A"], [1, "#4ECDC4"]], showscale=False),
            ))
            fig_ln1.update_layout(**lencol_layout_dark(title="Peças cortadas por mês", height=320))
            st.plotly_chart(fig_ln1, use_container_width=True)

        with col_b_ln:
            st.markdown("<div class='ln-sec'>Market Share Empresas</div>", unsafe_allow_html=True)
            df_emp_ln0 = df_ln.groupby("EMPRESA")["QUANT"].sum().reset_index().sort_values("QUANT", ascending=False)
            fig_ln2 = go.Figure(go.Pie(
                labels=df_emp_ln0["EMPRESA"], values=df_emp_ln0["QUANT"],
                hole=0.5,
                marker=dict(colors=[lencol_cor_empresa(e) for e in df_emp_ln0["EMPRESA"]]),
                textinfo="percent",
                hovertemplate="%{label}<br>%{value:,.0f} peças<br>%{percent}<extra></extra>",
            ))
            fig_ln2.update_layout(**lencol_layout_dark(
                height=320,
                legend=dict(orientation="v", font=dict(size=10)),
                annotations=[dict(text="Empresas", x=.5, y=.5,
                                  font=dict(size=12, color="#CBD5E0"), showarrow=False)],
            ))
            st.plotly_chart(fig_ln2, use_container_width=True)

        col_c_ln, col_d_ln = st.columns(2)
        with col_c_ln:
            st.markdown("<div class='ln-sec'>Evolução Diária + Média Móvel 7d</div>", unsafe_allow_html=True)
            df_dia_ln = df_ln.groupby("DATA")["QUANT"].sum().reset_index().sort_values("DATA")
            df_dia_ln["MA7"] = df_dia_ln["QUANT"].rolling(7, min_periods=1).mean().round(0)
            fig_ln3 = go.Figure()
            fig_ln3.add_trace(go.Bar(x=df_dia_ln["DATA"], y=df_dia_ln["QUANT"],
                                     name="Peças/dia", marker_color="rgba(78,205,196,0.35)"))
            fig_ln3.add_trace(go.Scatter(x=df_dia_ln["DATA"], y=df_dia_ln["MA7"],
                                         name="Média 7d", line=dict(color="#FF6B6B", width=2)))
            fig_ln3.update_layout(**lencol_layout_dark(height=280, title="Produção diária"))
            st.plotly_chart(fig_ln3, use_container_width=True)

        with col_d_ln:
            st.markdown("<div class='ln-sec'>Top 8 Categorias</div>", unsafe_allow_html=True)
            df_cat_ln0 = (df_ln.groupby("CAT_BASE")["QUANT"].sum()
                          .reset_index().sort_values("QUANT", ascending=True).tail(8))
            fig_ln4 = go.Figure(go.Bar(
                x=df_cat_ln0["QUANT"], y=df_cat_ln0["CAT_BASE"],
                orientation="h",
                text=[lencol_fmt_num(v) for v in df_cat_ln0["QUANT"]],
                textposition="outside",
                textfont=dict(color="#CBD5E0"),
                marker_color="#4ECDC4",
            ))
            fig_ln4.update_layout(**lencol_layout_dark(height=280, title="Peças por categoria"))
            st.plotly_chart(fig_ln4, use_container_width=True)

        st.markdown("<div class='ln-sec'>💡 Insights Automáticos</div>", unsafe_allow_html=True)
        ic1_ln, ic2_ln, ic3_ln = st.columns(3)
        df_dsem_ln = df_ln.groupby("DIA_SEMANA")["QUANT"].mean()
        if not df_dsem_ln.empty:
            melhor_dia_ln = LENCOL_DIAS_PT.get(df_dsem_ln.idxmax(), df_dsem_ln.idxmax())
            with ic1_ln:
                st.markdown(
                    f"<div class='ln-insight'><h4>📅 Melhor dia</h4>"
                    f"<p><b>{melhor_dia_ln}</b> é o dia mais produtivo em média, "
                    f"com <b>{lencol_fmt_num(df_dsem_ln.max(), 0)}</b> peças/dia.</p></div>",
                    unsafe_allow_html=True,
                )
        df_emp_ln_i = df_ln.groupby("EMPRESA")["QUANT"].sum()
        if not df_emp_ln_i.empty:
            emp_top_ln = df_emp_ln_i.idxmax()
            pct_top_ln = df_emp_ln_i.max() / df_emp_ln_i.sum() * 100
            with ic2_ln:
                st.markdown(
                    f"<div class='ln-insight'><h4>🏭 Empresa líder</h4>"
                    f"<p><b>{emp_top_ln}</b> responde por <b>{lencol_fmt_num(pct_top_ln, 1)}%</b> "
                    f"de toda a produção no período.</p></div>",
                    unsafe_allow_html=True,
                )
        with ic3_ln:
            st.markdown(
                f"<div class='ln-insight'><h4>💲 Ticket médio</h4>"
                f"<p>Cada peça cortada vale em média <b>R$ {lencol_fmt_num(ticket_medio_ln, 4)}</b>. "
                f"Total acumulado: <b>{lencol_fmt_brl(total_valor_ln)}</b>.</p></div>",
                unsafe_allow_html=True,
            )

    # tab 2 — prestadores
    with tabs_ln[1]:
        st.markdown("<div class='ln-sec'>Desempenho por Prestador</div>", unsafe_allow_html=True)
        df_prest_ln = (
            df_ln.groupby("PRESTADOR")
            .agg(Peças=("QUANT","sum"), Valor=("VALOR_RECEBER","sum"),
                 Dias=("DATA","nunique"), Empresas=("EMPRESA","nunique"),
                 Categorias=("CAT_BASE","nunique"))
            .reset_index().sort_values("Peças", ascending=False)
        )
        df_prest_ln["Média/Dia"] = (df_prest_ln["Peças"] / df_prest_ln["Dias"]).round(0).astype(int)
        df_prest_ln["R$/Peça"] = (df_prest_ln["Valor"] / df_prest_ln["Peças"]).round(4)
        df_prest_show_ln = df_prest_ln.copy()
        df_prest_show_ln["Peças"] = df_prest_show_ln["Peças"].apply(lencol_fmt_num)
        df_prest_show_ln["Valor"] = df_prest_show_ln["Valor"].apply(lencol_fmt_brl)
        df_prest_show_ln["Média/Dia"] = df_prest_show_ln["Média/Dia"].apply(lencol_fmt_num)
        df_prest_show_ln["R$/Peça"] = df_prest_show_ln["R$/Peça"].apply(lambda v: f"R$ {lencol_fmt_num(v,4)}")
        st.dataframe(df_prest_show_ln.rename(columns={"PRESTADOR":"Prestador"}),
                     use_container_width=True, hide_index=True)

        col_p1_ln, col_p2_ln = st.columns(2)
        with col_p1_ln:
            st.markdown("<div class='ln-sec'>Produção por Prestador</div>", unsafe_allow_html=True)
            fig_p1_ln = go.Figure(go.Bar(
                y=df_prest_ln["PRESTADOR"], x=df_prest_ln["Peças"], orientation="h",
                text=[lencol_fmt_num(v) for v in df_prest_ln["Peças"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker=dict(
                    color=list(range(len(df_prest_ln))),
                    colorscale=[[i/max(len(df_prest_ln)-1,1), c]
                                for i,c in enumerate(LENCOL_PALETA[:len(df_prest_ln)])],
                    showscale=False,
                ),
            ))
            fig_p1_ln.update_layout(**lencol_layout_dark(height=360, title="Total de peças cortadas"))
            st.plotly_chart(fig_p1_ln, use_container_width=True)

        with col_p2_ln:
            st.markdown("<div class='ln-sec'>Valor Ganho por Prestador</div>", unsafe_allow_html=True)
            fig_p2_ln = go.Figure(go.Bar(
                y=df_prest_ln["PRESTADOR"], x=df_prest_ln["Valor"], orientation="h",
                text=[lencol_fmt_brl(v) for v in df_prest_ln["Valor"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker_color="#FFD54F",
            ))
            fig_p2_ln.update_layout(**lencol_layout_dark(height=360, title=f"R$ {status_pg_ln} por prestador"))
            st.plotly_chart(fig_p2_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Evolução Mensal por Prestador</div>", unsafe_allow_html=True)
        df_pmes_ln = (df_ln.groupby(["ANO_MES","PRESTADOR"])["QUANT"].sum()
                      .reset_index().sort_values("ANO_MES"))
        fig_pev_ln = px.line(df_pmes_ln, x="ANO_MES", y="QUANT", color="PRESTADOR",
                             markers=True, color_discrete_sequence=LENCOL_PALETA,
                             labels={"QUANT":"Peças","ANO_MES":"Mês","PRESTADOR":"Prestador"})
        fig_pev_ln.update_layout(**lencol_layout_dark(height=320, title="Peças cortadas por mês"))
        fig_pev_ln.update_traces(line_width=2, marker_size=6)
        st.plotly_chart(fig_pev_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Prestador × Empresa (peças)</div>", unsafe_allow_html=True)
        df_hm_ln = df_ln.pivot_table(index="PRESTADOR", columns="EMPRESA",
                                     values="QUANT", aggfunc="sum", fill_value=0)
        fig_hm_ln = go.Figure(go.Heatmap(
            z=df_hm_ln.values, x=list(df_hm_ln.columns), y=list(df_hm_ln.index),
            colorscale="Teal",
            text=[[lencol_fmt_num(v) for v in row] for row in df_hm_ln.values],
            texttemplate="%{text}", textfont=dict(size=10),
        ))
        fig_hm_ln.update_layout(**lencol_layout_dark(height=300, title="Distribuição prestador × empresa"))
        st.plotly_chart(fig_hm_ln, use_container_width=True)

    # tab 4 — empresas
    with tabs_ln[3]:
        df_emp_tab_ln = (
            df_ln.groupby("EMPRESA")
            .agg(Peças=("QUANT","sum"), Valor=("VALOR_RECEBER","sum"),
                 Dias=("DATA","nunique"), Prestadores=("PRESTADOR","nunique"),
                 Categorias=("CAT_BASE","nunique"), OPs=("OP","nunique"))
            .reset_index().sort_values("Peças", ascending=False)
        )
        df_emp_tab_ln["Share%"] = (df_emp_tab_ln["Peças"] / df_emp_tab_ln["Peças"].sum() * 100).round(1)
        df_emp_tab_ln["R$/Peça"] = (df_emp_tab_ln["Valor"] / df_emp_tab_ln["Peças"]).round(4)

        st.markdown("<div class='ln-sec'>Resumo por Empresa</div>", unsafe_allow_html=True)
        cols_emp_ln = st.columns(min(len(df_emp_tab_ln), 5))
        for idx_e, (_, row_e) in enumerate(df_emp_tab_ln.iterrows()):
            if idx_e >= len(cols_emp_ln):
                break
            with cols_emp_ln[idx_e]:
                cor_e = lencol_cor_empresa(row_e["EMPRESA"])
                st.markdown(
                    f"<div style='background:linear-gradient(135deg,#1C1C22,#28282E);"
                    f"border:1px solid {cor_e}44;border-top:3px solid {cor_e};"
                    f"border-radius:10px;padding:12px 14px;text-align:center'>"
                    f"<div style='color:{cor_e};font-weight:700;font-size:.8rem'>{row_e['EMPRESA']}</div>"
                    f"<div style='color:#FFF;font-size:1.3rem;font-weight:800'>{lencol_fmt_num(row_e['Peças'])}</div>"
                    f"<div style='color:#A0AEC0;font-size:.75rem'>peças · {row_e['Share%']}%</div>"
                    f"<div style='color:#CBD5E0;font-size:.8rem;margin-top:4px'>{lencol_fmt_brl(row_e['Valor'])}</div>"
                    f"</div>", unsafe_allow_html=True,
                )

        st.divider()
        col_e1_ln, col_e2_ln = st.columns(2)
        with col_e1_ln:
            st.markdown("<div class='ln-sec'>Volume por Empresa</div>", unsafe_allow_html=True)
            fig_e1_ln = go.Figure(go.Bar(
                x=df_emp_tab_ln["EMPRESA"], y=df_emp_tab_ln["Peças"],
                text=[lencol_fmt_num(v) for v in df_emp_tab_ln["Peças"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker=dict(color=[lencol_cor_empresa(e) for e in df_emp_tab_ln["EMPRESA"]]),
            ))
            fig_e1_ln.update_layout(**lencol_layout_dark(height=300, title="Peças por empresa"))
            st.plotly_chart(fig_e1_ln, use_container_width=True)

        with col_e2_ln:
            st.markdown("<div class='ln-sec'>Valor por Empresa</div>", unsafe_allow_html=True)
            fig_e2_ln = go.Figure(go.Bar(
                x=df_emp_tab_ln["EMPRESA"], y=df_emp_tab_ln["Valor"],
                text=[lencol_fmt_brl(v) for v in df_emp_tab_ln["Valor"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker=dict(color=[lencol_cor_empresa(e) for e in df_emp_tab_ln["EMPRESA"]]),
            ))
            fig_e2_ln.update_layout(**lencol_layout_dark(height=300, title=f"R$ {status_pg_ln} por empresa"))
            st.plotly_chart(fig_e2_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Evolução Mensal por Empresa</div>", unsafe_allow_html=True)
        df_emes_ln = (df_ln.groupby(["ANO_MES","EMPRESA"])["QUANT"].sum()
                      .reset_index().sort_values("ANO_MES"))
        fig_emes_ln = px.bar(df_emes_ln, x="ANO_MES", y="QUANT", color="EMPRESA",
                             barmode="stack", color_discrete_map=LENCOL_CORES_EMPRESA,
                             labels={"QUANT":"Peças","ANO_MES":"Mês","EMPRESA":"Empresa"})
        fig_emes_ln.update_layout(**lencol_layout_dark(height=320, title="Volume mensal empilhado por empresa"))
        st.plotly_chart(fig_emes_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Tabela Comparativa</div>", unsafe_allow_html=True)
        df_emp_show_ln = df_emp_tab_ln.copy()
        df_emp_show_ln["Peças"] = df_emp_show_ln["Peças"].apply(lencol_fmt_num)
        df_emp_show_ln["Valor"] = df_emp_show_ln["Valor"].apply(lencol_fmt_brl)
        df_emp_show_ln["R$/Peça"] = df_emp_show_ln["R$/Peça"].apply(lambda v: f"R$ {lencol_fmt_num(v,4)}")
        df_emp_show_ln["Share%"] = df_emp_show_ln["Share%"].apply(lambda v: f"{lencol_fmt_num(v,1)}%")
        st.dataframe(df_emp_show_ln.rename(columns={"EMPRESA":"Empresa"}),
                     use_container_width=True, hide_index=True)

    # tab 5 — categorias
    with tabs_ln[4]:
        df_cat_tab_ln = (
            df_ln.groupby("CAT_BASE")
            .agg(Peças=("QUANT","sum"), Valor=("VALOR_RECEBER","sum"),
                 Empresas=("EMPRESA","nunique"), Registros=("QUANT","count"))
            .reset_index().sort_values("Peças", ascending=False)
        )
        df_cat_tab_ln["Share%"] = (df_cat_tab_ln["Peças"] / df_cat_tab_ln["Peças"].sum() * 100).round(1)
        df_cat_tab_ln["R$/Peça"] = (df_cat_tab_ln["Valor"] / df_cat_tab_ln["Peças"]).round(4)

        col_c1_ln, col_c2_ln = st.columns(2)
        with col_c1_ln:
            st.markdown("<div class='ln-sec'>Top Categorias – Volume</div>", unsafe_allow_html=True)
            df_top_ln = df_cat_tab_ln.sort_values("Peças", ascending=True).tail(10)
            fig_c1_ln = go.Figure(go.Bar(
                x=df_top_ln["Peças"], y=df_top_ln["CAT_BASE"], orientation="h",
                text=[lencol_fmt_num(v) for v in df_top_ln["Peças"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker=dict(color=df_top_ln["Peças"],
                            colorscale=[[0,"#1C3A4A"],[1,"#4ECDC4"]], showscale=False),
            ))
            fig_c1_ln.update_layout(**lencol_layout_dark(height=350, title="Peças por categoria (Top 10)"))
            st.plotly_chart(fig_c1_ln, use_container_width=True)

        with col_c2_ln:
            st.markdown("<div class='ln-sec'>Top Categorias – Valor</div>", unsafe_allow_html=True)
            df_top_v_ln = df_cat_tab_ln.sort_values("Valor", ascending=True).tail(10)
            fig_c2_ln = go.Figure(go.Bar(
                x=df_top_v_ln["Valor"], y=df_top_v_ln["CAT_BASE"], orientation="h",
                text=[lencol_fmt_brl(v) for v in df_top_v_ln["Valor"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker_color="#FFD54F",
            ))
            fig_c2_ln.update_layout(**lencol_layout_dark(height=350, title="Valor R$ por categoria (Top 10)"))
            st.plotly_chart(fig_c2_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Distribuição: Empresa → Categoria</div>", unsafe_allow_html=True)
        df_tree_ln = df_ln.groupby(["EMPRESA","CAT_BASE"])["QUANT"].sum().reset_index()
        df_tree_ln = df_tree_ln[df_tree_ln["QUANT"] > 0]
        fig_tree_ln = px.treemap(df_tree_ln, path=["EMPRESA","CAT_BASE"], values="QUANT",
                                 color="EMPRESA", color_discrete_map=LENCOL_CORES_EMPRESA)
        fig_tree_ln.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                  font=dict(color="#CBD5E0"),
                                  margin=dict(l=10,r=10,t=40,b=10), height=380)
        fig_tree_ln.update_traces(textfont=dict(color="#FFFFFF"),
                                  hovertemplate="<b>%{label}</b><br>%{value:,} peças<extra></extra>")
        st.plotly_chart(fig_tree_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Empresa × Categoria (peças)</div>", unsafe_allow_html=True)
        df_hmec_ln = df_ln.pivot_table(index="EMPRESA", columns="CAT_BASE",
                                       values="QUANT", aggfunc="sum", fill_value=0)
        fig_hmec_ln = go.Figure(go.Heatmap(
            z=df_hmec_ln.values, x=list(df_hmec_ln.columns), y=list(df_hmec_ln.index),
            colorscale="Blues",
            text=[[lencol_fmt_num(v) if v > 0 else "" for v in row] for row in df_hmec_ln.values],
            texttemplate="%{text}", textfont=dict(size=9),
        ))
        fig_hmec_ln.update_layout(**lencol_layout_dark(height=300, title="Peças: empresa vs categoria"))
        st.plotly_chart(fig_hmec_ln, use_container_width=True)

    # tab 6 — temporal
    with tabs_ln[5]:
        col_t1_ln, col_t2_ln = st.columns(2)
        with col_t1_ln:
            st.markdown("<div class='ln-sec'>Produção Diária</div>", unsafe_allow_html=True)
            df_d_ln = df_ln.groupby("DATA")["QUANT"].sum().reset_index().sort_values("DATA")
            df_d_ln["MA7"] = df_d_ln["QUANT"].rolling(7, min_periods=1).mean().round(0)
            df_d_ln["ACUM"] = df_d_ln["QUANT"].cumsum()
            fig_t1_ln = make_subplots(specs=[[{"secondary_y": True}]])
            fig_t1_ln.add_trace(go.Bar(x=df_d_ln["DATA"], y=df_d_ln["QUANT"],
                                       name="Peças/dia", marker_color="rgba(78,205,196,0.4)"),
                                secondary_y=False)
            fig_t1_ln.add_trace(go.Scatter(x=df_d_ln["DATA"], y=df_d_ln["MA7"],
                                           name="Média 7d", line=dict(color="#FF6B6B", width=2)),
                                secondary_y=False)
            fig_t1_ln.add_trace(go.Scatter(x=df_d_ln["DATA"], y=df_d_ln["ACUM"],
                                           name="Acumulado", line=dict(color="#FFD54F", width=1.5, dash="dot")),
                                secondary_y=True)
            fig_t1_ln.update_layout(**lencol_layout_dark(height=320, title="Diário + Acumulado",
                                                         legend=dict(orientation="h", y=-0.2)))
            fig_t1_ln.update_yaxes(title_text="Peças/dia", secondary_y=False, gridcolor="#2D3748")
            fig_t1_ln.update_yaxes(title_text="Acumulado", secondary_y=True, gridcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_t1_ln, use_container_width=True)

        with col_t2_ln:
            st.markdown("<div class='ln-sec'>Produção Semanal</div>", unsafe_allow_html=True)
            df_sem_ln = df_ln.groupby(["ANO","SEMANA"])["QUANT"].sum().reset_index()
            df_sem_ln["LABEL"] = df_sem_ln["ANO"].astype(str) + "-S" + df_sem_ln["SEMANA"].astype(str).str.zfill(2)
            fig_t2_ln = go.Figure(go.Bar(
                x=df_sem_ln["LABEL"], y=df_sem_ln["QUANT"],
                marker=dict(color=df_sem_ln["QUANT"],
                            colorscale=[[0,"#1C3A4A"],[1,"#4ECDC4"]], showscale=False),
            ))
            fig_t2_ln.update_layout(**lencol_layout_dark(height=320, title="Produção por semana"))
            st.plotly_chart(fig_t2_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Calendário de Produção (Dia × Semana)</div>", unsafe_allow_html=True)
        df_cal_ln = df_ln.groupby(["SEMANA","DIA_SEMANA"])["QUANT"].sum().reset_index()
        df_cal_piv_ln = df_cal_ln.pivot_table(index="DIA_SEMANA", columns="SEMANA",
                                              values="QUANT", fill_value=0)
        ordem_ln = [d for d in LENCOL_ORDEM_DIAS if d in df_cal_piv_ln.index]
        df_cal_piv_ln = df_cal_piv_ln.reindex(ordem_ln)
        df_cal_piv_ln.index = [LENCOL_DIAS_PT.get(d, d) for d in df_cal_piv_ln.index]
        fig_cal_ln = go.Figure(go.Heatmap(
            z=df_cal_piv_ln.values,
            x=[f"S{c}" for c in df_cal_piv_ln.columns],
            y=list(df_cal_piv_ln.index),
            colorscale="Teal",
            hovertemplate="%{y} – Semana %{x}<br>%{z:,} peças<extra></extra>",
        ))
        fig_cal_ln.update_layout(**lencol_layout_dark(height=260, title="Intensidade de produção por semana e dia"))
        st.plotly_chart(fig_cal_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Média por Dia da Semana</div>", unsafe_allow_html=True)
        df_dsem2_ln = (
            df_ln.groupby(["DATA","DIA_SEMANA"])["QUANT"].sum().reset_index()
            .groupby("DIA_SEMANA")["QUANT"].mean().reset_index()
        )
        df_dsem2_ln = df_dsem2_ln[df_dsem2_ln["DIA_SEMANA"].isin(LENCOL_ORDEM_DIAS)]
        df_dsem2_ln["ORDEM"] = df_dsem2_ln["DIA_SEMANA"].map({d:i for i,d in enumerate(LENCOL_ORDEM_DIAS)})
        df_dsem2_ln = df_dsem2_ln.sort_values("ORDEM")
        df_dsem2_ln["DIA_PT"] = df_dsem2_ln["DIA_SEMANA"].map(LENCOL_DIAS_PT)
        fig_ds_ln = go.Figure(go.Bar(
            x=df_dsem2_ln["DIA_PT"], y=df_dsem2_ln["QUANT"].round(0),
            text=[lencol_fmt_num(v, 0) for v in df_dsem2_ln["QUANT"]],
            textposition="outside",
            marker=dict(color=df_dsem2_ln["QUANT"],
                        colorscale=[[0,"#2C3E50"],[1,"#4ECDC4"]], showscale=False),
        ))
        fig_ds_ln.update_layout(**lencol_layout_dark(height=260, title="Média de peças por dia da semana"))
        st.plotly_chart(fig_ds_ln, use_container_width=True)

    # tab 7 — financeiro
    with tabs_ln[6]:
        total_r_ln = df_ln["VALOR_RECEBER"].sum()
        media_dia_r_ln = total_r_ln / dias_trab_ln if dias_trab_ln else 0
        media_peca_r_ln = total_r_ln / df_ln["QUANT"].sum() if df_ln["QUANT"].sum() else 0

        col_f0_ln, col_f1_ln, col_f2_ln, col_f3_ln = st.columns(4)
        col_f0_ln.metric("💰 Total R$", lencol_fmt_brl(total_r_ln))
        col_f1_ln.metric("📅 Média Diária R$", lencol_fmt_brl(media_dia_r_ln))
        col_f2_ln.metric("🧵 R$/Peça Médio", f"R$ {lencol_fmt_num(media_peca_r_ln, 4)}")
        _info_ln2 = _analisa_dias(df_ln["DATA"].dt.date.unique(), p_ini_ln, p_fim_ln)
        _delta_ln2 = f"+{_info_ln2['sabados']} sáb." if _info_ln2['sabados'] > 0 else None
        _help_ln2 = ("⚠️ Sem registro: " + ", ".join(d.strftime('%d/%m') for d in _info_ln2['ausentes'])) if _info_ln2['ausentes'] else None
        col_f3_ln.metric("🗓️ Dias Trabalhados", str(dias_com_dados_ln), delta=_delta_ln2, delta_color="off", help=_help_ln2)

        st.divider()
        col_fa_ln, col_fb_ln = st.columns(2)
        with col_fa_ln:
            st.markdown("<div class='ln-sec'>Ranking Financeiro – Prestadores</div>", unsafe_allow_html=True)
            df_fpr_ln = (df_ln.groupby("PRESTADOR")["VALOR_RECEBER"].sum()
                         .reset_index().sort_values("VALOR_RECEBER", ascending=True))
            fig_fa_ln = go.Figure(go.Bar(
                x=df_fpr_ln["VALOR_RECEBER"], y=df_fpr_ln["PRESTADOR"], orientation="h",
                text=[lencol_fmt_brl(v) for v in df_fpr_ln["VALOR_RECEBER"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker_color="#FFD54F",
            ))
            fig_fa_ln.update_layout(**lencol_layout_dark(height=300, title=f"Total R$ {status_pg_ln} por prestador"))
            st.plotly_chart(fig_fa_ln, use_container_width=True)

        with col_fb_ln:
            st.markdown("<div class='ln-sec'>Ticket Médio por Empresa</div>", unsafe_allow_html=True)
            df_tick_ln = (
                df_ln.groupby("EMPRESA")
                .apply(lambda x: (x["VALOR_RECEBER"].sum() / x["QUANT"].sum()) if x["QUANT"].sum() > 0 else 0)
                .reset_index(name="Ticket").sort_values("Ticket", ascending=True)
            )
            fig_fb_ln = go.Figure(go.Bar(
                x=df_tick_ln["Ticket"], y=df_tick_ln["EMPRESA"], orientation="h",
                text=[f"R$ {lencol_fmt_num(v, 4)}" for v in df_tick_ln["Ticket"]],
                textposition="outside", textfont=dict(color="#CBD5E0"),
                marker=dict(color=[lencol_cor_empresa(e) for e in df_tick_ln["EMPRESA"]]),
            ))
            fig_fb_ln.update_layout(**lencol_layout_dark(height=300, title="R$ por peça (ticket médio)"))
            st.plotly_chart(fig_fb_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Evolução Financeira Mensal</div>", unsafe_allow_html=True)
        df_fmes_ln = (df_ln.groupby(["ANO_MES","EMPRESA"])["VALOR_RECEBER"].sum()
                      .reset_index().sort_values("ANO_MES"))
        fig_fmes_ln = px.bar(df_fmes_ln, x="ANO_MES", y="VALOR_RECEBER", color="EMPRESA",
                             barmode="stack", color_discrete_map=LENCOL_CORES_EMPRESA,
                             labels={"VALOR_RECEBER":"R$","ANO_MES":"Mês","EMPRESA":"Empresa"})
        fig_fmes_ln.update_layout(**lencol_layout_dark(height=300, title=f"Valor R$ mensal {status_pg_ln} por empresa"))
        st.plotly_chart(fig_fmes_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Relação Quantidade × Valor por Registro</div>", unsafe_allow_html=True)
        fig_sc_ln = px.scatter(
            df_ln, x="QUANT", y="VALOR_RECEBER", color="EMPRESA",
            size="QUANT", size_max=18, opacity=0.7,
            hover_data=["PRESTADOR","CATEGORIA","DATA"],
            color_discrete_map=LENCOL_CORES_EMPRESA,
            labels={"QUANT":"Quantidade (peças)","VALOR_RECEBER":"Valor (R$)","EMPRESA":"Empresa"},
        )
        fig_sc_ln.update_layout(**lencol_layout_dark(height=320))
        st.plotly_chart(fig_sc_ln, use_container_width=True)

    # tab 8 — metas
    with tabs_ln[7]:
        if df_metas_ln.empty:
            st.info("Nenhuma meta encontrada na planilha METAS.")
        else:
            df_real_ln = (
                df_ln.groupby(["EMPRESA","CAT_BASE"])["QUANT"].sum().reset_index()
                .rename(columns={"CAT_BASE":"CATEGORIA","QUANT":"REAL"})
            )
            df_metas_clean_ln = df_metas_ln.copy()
            df_metas_clean_ln["EMPRESA"] = df_metas_clean_ln["EMPRESA"].str.strip().str.upper()
            df_metas_clean_ln["CATEGORIA"] = df_metas_clean_ln["CATEGORIA"].apply(lencol_cat_base)

            df_comp_ln = df_metas_clean_ln.merge(df_real_ln, on=["EMPRESA","CATEGORIA"], how="left")
            df_comp_ln["REAL"] = df_comp_ln["REAL"].fillna(0).astype(int)
            df_comp_ln["ATINGIMENTO%"] = (df_comp_ln["REAL"] / df_comp_ln["META"] * 100).round(1)
            df_comp_ln["DESVIO"] = (df_comp_ln["REAL"] - df_comp_ln["META"]).astype(int)
            df_comp_ln = df_comp_ln.sort_values("ATINGIMENTO%", ascending=False)

            meta_total_ln = df_comp_ln["META"].sum()
            real_total_ln = df_comp_ln["REAL"].sum()
            ating_geral_ln = real_total_ln / meta_total_ln * 100 if meta_total_ln else 0
            n_atingidas_ln = int((df_comp_ln["ATINGIMENTO%"] >= 100).sum())

            c_m1_ln, c_m2_ln, c_m3_ln, c_m4_ln = st.columns(4)
            c_m1_ln.metric("🎯 Meta Total", lencol_fmt_num(meta_total_ln))
            c_m2_ln.metric("✅ Produção Real", lencol_fmt_num(real_total_ln))
            c_m3_ln.metric("📊 Atingimento", f"{lencol_fmt_num(ating_geral_ln, 1)}%")
            c_m4_ln.metric("🏆 Metas Atingidas", f"{n_atingidas_ln}/{len(df_comp_ln)}")

            st.divider()
            st.markdown("<div class='ln-sec'>Meta vs Realizado por Empresa × Categoria</div>", unsafe_allow_html=True)
            df_comp_sorted_ln = df_comp_ln.sort_values("META", ascending=True)
            df_comp_sorted_ln = df_comp_sorted_ln.copy()
            df_comp_sorted_ln["LABEL"] = df_comp_sorted_ln["EMPRESA"] + " · " + df_comp_sorted_ln["CATEGORIA"]
            fig_meta_ln = go.Figure()
            fig_meta_ln.add_trace(go.Bar(
                y=df_comp_sorted_ln["LABEL"], x=df_comp_sorted_ln["META"],
                name="Meta", orientation="h", marker_color="rgba(160,174,192,0.4)",
            ))
            fig_meta_ln.add_trace(go.Bar(
                y=df_comp_sorted_ln["LABEL"], x=df_comp_sorted_ln["REAL"],
                name="Realizado", orientation="h",
                marker_color=[
                    "#4ECDC4" if v >= 100 else ("#FFD54F" if v >= 75 else "#FF6B6B")
                    for v in df_comp_sorted_ln["ATINGIMENTO%"]
                ],
            ))
            fig_meta_ln.update_layout(
                **LENCOL_DARK, height=max(280, len(df_comp_sorted_ln) * 32),
                barmode="overlay", title="Verde ≥ 100% · Amarelo ≥ 75% · Vermelho < 75%",
            )
            st.plotly_chart(fig_meta_ln, use_container_width=True)

            st.markdown("<div class='ln-sec'>Progresso por Empresa × Categoria</div>", unsafe_allow_html=True)
            for _, row_m in df_comp_ln.iterrows():
                pct_m = min(float(row_m["ATINGIMENTO%"]), 100.0) / 100
                lbl_m = f"{row_m['EMPRESA']} · {row_m['CATEGORIA']}"
                col_lbl_m, col_prog_m, col_pct_m = st.columns([3, 5, 1])
                with col_lbl_m: st.caption(lbl_m)
                with col_prog_m: st.progress(pct_m)
                with col_pct_m: st.caption(f"{lencol_fmt_num(row_m['ATINGIMENTO%'], 1)}%")

            st.markdown("<div class='ln-sec'>Tabela Detalhada de Metas</div>", unsafe_allow_html=True)
            df_meta_show_ln = df_comp_ln[["EMPRESA","CATEGORIA","META","REAL","DESVIO","ATINGIMENTO%"]].copy()
            df_meta_show_ln["META"] = df_meta_show_ln["META"].apply(lencol_fmt_num)
            df_meta_show_ln["REAL"] = df_meta_show_ln["REAL"].apply(lencol_fmt_num)
            df_meta_show_ln["DESVIO"] = df_meta_show_ln["DESVIO"].apply(
                lambda v: f"+{lencol_fmt_num(v)}" if v >= 0 else lencol_fmt_num(v)
            )
            df_meta_show_ln["ATINGIMENTO%"] = df_meta_show_ln["ATINGIMENTO%"].apply(
                lambda v: f"{lencol_fmt_num(v, 1)}%"
            )
            st.dataframe(df_meta_show_ln, use_container_width=True, hide_index=True)

    # tab 9 — ranking
    with tabs_ln[8]:
        st.markdown("<div class='ln-sec'>🏆 Ranking Geral de Prestadores</div>", unsafe_allow_html=True)
        df_rank_ln = (
            df_ln.groupby("PRESTADOR")
            .agg(Peças=("QUANT","sum"), Valor=("VALOR_RECEBER","sum"), Dias=("DATA","nunique"))
            .reset_index().sort_values("Peças", ascending=False)
        ).reset_index(drop=True)
        df_rank_ln["Pos"] = df_rank_ln.index + 1
        df_rank_ln["Média/Dia"] = (df_rank_ln["Peças"] / df_rank_ln["Dias"]).round(0)

        for i, row_r in df_rank_ln.iterrows():
            if i == 0:
                badge = "<span class='ln-rank-gold'>🥇 1º</span>"
            elif i == 1:
                badge = "<span class='ln-rank-silver'>🥈 2º</span>"
            elif i == 2:
                badge = "<span class='ln-rank-bronze'>🥉 3º</span>"
            else:
                badge = f"<span style='color:#A0AEC0'>{i+1}º</span>"
            pct_r = row_r["Peças"] / df_rank_ln["Peças"].sum() * 100 if df_rank_ln["Peças"].sum() > 0 else 0
            col_rank_a, col_rank_b, col_rank_c = st.columns([1, 4, 3])
            with col_rank_a:
                st.markdown(badge, unsafe_allow_html=True)
            with col_rank_b:
                st.markdown(f"**{row_r['PRESTADOR']}** — {lencol_fmt_num(row_r['Peças'])} peças ({lencol_fmt_num(pct_r,1)}%)")
            with col_rank_c:
                st.markdown(f"{lencol_fmt_brl(row_r['Valor'])} · {lencol_fmt_num(row_r['Média/Dia'],0)} pç/dia")

        st.divider()
        st.markdown("<div class='ln-sec'>Comparativo de Desempenho</div>", unsafe_allow_html=True)
        fig_rank_ln = go.Figure(go.Bar(
            x=df_rank_ln["PRESTADOR"],
            y=df_rank_ln["Peças"],
            text=[lencol_fmt_num(v) for v in df_rank_ln["Peças"]],
            textposition="outside", textfont=dict(color="#CBD5E0"),
            marker=dict(
                color=list(range(len(df_rank_ln))),
                colorscale=[[i/max(len(df_rank_ln)-1,1), c]
                            for i,c in enumerate(LENCOL_PALETA[:len(df_rank_ln)])],
                showscale=False,
            ),
        ))
        fig_rank_ln.update_layout(**lencol_layout_dark(height=300, title="Ranking por total de peças"))
        st.plotly_chart(fig_rank_ln, use_container_width=True)

        st.markdown("<div class='ln-sec'>Radar de Performance (normalizado)</div>", unsafe_allow_html=True)
        if len(df_rank_ln) >= 2:
            df_radar_ln = df_rank_ln.copy()
            for col_r in ["Peças", "Valor", "Média/Dia"]:
                mx = df_radar_ln[col_r].max()
                df_radar_ln[col_r + "_norm"] = (df_radar_ln[col_r] / mx * 100).round(1) if mx > 0 else 0
            categorias_r = ["Peças", "Valor", "Média/Dia"]
            fig_radar_ln = go.Figure()
            for _, row_rd in df_radar_ln.iterrows():
                vals = [row_rd[c + "_norm"] for c in categorias_r] + [row_rd[categorias_r[0] + "_norm"]]
                fig_radar_ln.add_trace(go.Scatterpolar(
                    r=vals, theta=categorias_r + [categorias_r[0]],
                    fill="toself", name=row_rd["PRESTADOR"], opacity=0.7,
                ))
            fig_radar_ln.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="#2D3748"),
                           angularaxis=dict(gridcolor="#2D3748")),
                **LENCOL_DARK, height=380,
            )
            st.plotly_chart(fig_radar_ln, use_container_width=True)
        else:
            st.info("Radar disponível com 2 ou mais prestadores.")

    # tab 3 — ops
    with tabs_ln[2]:
        st.markdown("<div class='ln-sec'>📋 Resumo por OP</div>", unsafe_allow_html=True)

        resumo_op_ln = (
            df_ln.groupby("OP")
            .agg(
                Peças=("QUANT", "sum"),
                Valor=("VALOR_RECEBER", "sum"),
                Prestadores=("PRESTADOR", "nunique"),
                Empresas=("EMPRESA", "nunique"),
                Tecido=("TECIDO", "first"),
                Categoria=("CATEGORIA", "first"),
                Data_Inicio=("DATA", "min"),
                Ultimo_Corte=("DATA", "max"),
                Registros=("QUANT", "count"),
            )
            .reset_index()
            .sort_values("Peças", ascending=False)
        )

        # ── Enriquecer resumo com Jogo Duplo / Fundo / Caseamento ────────────
        # Calcula uma única vez — reutilizado na seção de caseamento abaixo
        _casea_op_ln = lencol_caseamento(df_ln)
        if not _casea_op_ln.empty:
            _casea_por_op_ln = (
                _casea_op_ln.groupby("OP", as_index=False)
                .agg(Jogo_Duplo=("JOGO", "sum"), Fundo=("FUNDO", "sum"), Diferenca=("DIFERENCA", "sum"))
            )
            _casea_por_op_ln["Casea"] = _casea_por_op_ln["Diferenca"].apply(
                lambda x: "✅" if x == 0 else ("🔴" if x < 0 else "🟠")
            )
            resumo_op_ln = resumo_op_ln.merge(
                _casea_por_op_ln[["OP", "Jogo_Duplo", "Fundo", "Diferenca", "Casea"]],
                on="OP", how="left"
            )
        else:
            resumo_op_ln["Jogo_Duplo"] = 0
            resumo_op_ln["Fundo"] = 0
            resumo_op_ln["Diferenca"] = 0
            resumo_op_ln["Casea"] = "—"
        for _c in ["Jogo_Duplo", "Fundo", "Diferenca"]:
            resumo_op_ln[_c] = resumo_op_ln[_c].fillna(0).astype(int)
        resumo_op_ln["Casea"] = resumo_op_ln["Casea"].fillna("—")

        resumo_op_show_ln = resumo_op_ln.copy()
        resumo_op_show_ln["Peças"] = resumo_op_show_ln["Peças"].apply(lencol_fmt_num)
        resumo_op_show_ln["Valor"] = resumo_op_show_ln["Valor"].apply(lencol_fmt_brl)
        resumo_op_show_ln["Data_Inicio"] = resumo_op_show_ln["Data_Inicio"].dt.strftime("%d/%m/%Y")
        resumo_op_show_ln["Ultimo_Corte"] = resumo_op_show_ln["Ultimo_Corte"].dt.strftime("%d/%m/%Y")
        resumo_op_show_ln["Jogo_Duplo"] = resumo_op_show_ln["Jogo_Duplo"].apply(
            lambda v: lencol_fmt_num(v) if v > 0 else "—"
        )
        resumo_op_show_ln["Fundo"] = resumo_op_show_ln["Fundo"].apply(
            lambda v: lencol_fmt_num(v) if v > 0 else "—"
        )
        resumo_op_show_ln["Diferenca"] = resumo_op_show_ln.apply(
            lambda r: (f"+{lencol_fmt_num(r['Diferenca'])}" if r["Diferenca"] > 0
                       else lencol_fmt_num(r["Diferenca"])) if r["Casea"] != "—" else "—",
            axis=1
        )
        st.dataframe(
            resumo_op_show_ln.rename(columns={
                "OP": "OP", "Peças": "Peças", "Jogo_Duplo": "Jogo Duplo",
                "Fundo": "Fundo", "Diferenca": "Diferença", "Casea": "Casea",
                "Valor": "Valor R$", "Prestadores": "Prestadores", "Empresas": "Empresas",
                "Tecido": "Tecido", "Categoria": "Categoria",
                "Data_Inicio": "Início", "Ultimo_Corte": "Último Corte",
                "Registros": "Registros",
            })[[
                "OP", "Peças", "Jogo Duplo", "Fundo", "Diferença", "Casea",
                "Valor R$", "Prestadores", "Empresas", "Tecido", "Categoria",
                "Início", "Último Corte", "Registros",
            ]],
            use_container_width=True, height=380, hide_index=True,
        )
        st.caption(
            "**Peças** = total bruto (jogo + fundo + outros).  "
            "**Jogo Duplo** / **Fundo** = cortes classificados por tipo.  "
            "**Casea**: ✅ caseado · 🔴 faltam fundos · 🟠 sobram fundos · — sem fundo."
        )

        # ── Caseamento Jogo × Fundo por OP ───────────────────────────────────
        # _casea_op_ln já foi calculado acima
        if not _casea_op_ln.empty:
            st.divider()
            st.markdown("<div class='ln-sec'>🔄 Caseamento Jogo Duplo × Fundo (por OP)</div>", unsafe_allow_html=True)
            _div_op_ln = _casea_op_ln[_casea_op_ln["DIFERENCA"] != 0]
            _n_ok = int((_casea_op_ln["DIFERENCA"] == 0).sum())
            _n_div = len(_div_op_ln)
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("✅ Pares caseados", str(_n_ok))
            cc2.metric("🚩 Pares divergentes", str(_n_div))
            _saldo_op_ln = int(_casea_op_ln["DIFERENCA"].sum())
            cc3.metric("⚖️ Saldo de fundos",
                       f"{'+' if _saldo_op_ln > 0 else ''}{lencol_fmt_num(_saldo_op_ln)}",
                       help="FUNDO − JOGO no total. Negativo = faltam fundos; positivo = sobram.")
            _mostrar_so_div = st.checkbox(
                "Mostrar apenas divergências", value=True, key="ln_casea_so_div"
            )
            _tab_casea = _div_op_ln if _mostrar_so_div else _casea_op_ln
            if _tab_casea.empty:
                st.success("✅ Todas as OPs com fundo estão caseadas (jogo = fundo por tamanho).")
            else:
                _casea_op_show = _tab_casea.copy()
                _casea_op_show["JOGO"] = _casea_op_show["JOGO"].apply(lencol_fmt_num)
                _casea_op_show["FUNDO"] = _casea_op_show["FUNDO"].apply(lencol_fmt_num)
                _casea_op_show["DIFERENCA"] = _casea_op_show["DIFERENCA"].apply(
                    lambda v: f"{'+' if v > 0 else ''}{lencol_fmt_num(v)}"
                )
                st.dataframe(
                    _casea_op_show.rename(columns={
                        "OP": "OP", "TAMANHO": "Tamanho", "JOGO": "Jogo",
                        "FUNDO": "Fundo", "DIFERENCA": "Diferença", "STATUS": "Status",
                    }),
                    use_container_width=True, height=320, hide_index=True,
                )
                st.caption(
                    "🔴 Faltam fundos = jogo cortado sem fundo suficiente.  "
                    "🟠 Sobram fundos = fundo cortado a mais que o jogo."
                )

        st.divider()

        if not resumo_op_ln.empty:
            op_sel_ln = st.selectbox(
                "🔎 Selecione uma OP para detalhar:",
                options=resumo_op_ln["OP"].tolist(),
                key="ln_sel_op",
            )
            if op_sel_ln:
                df_op_ln = df_ln[df_ln["OP"] == op_sel_ln]

                col_o1, col_o2, col_o3, col_o4 = st.columns(4)
                col_o1.metric("🧵 Total de Peças", lencol_fmt_num(df_op_ln["QUANT"].sum()))
                col_o2.metric("💰 Total R$", lencol_fmt_brl(df_op_ln["VALOR_RECEBER"].sum()))
                col_o3.metric("👷 Prestadores", str(df_op_ln["PRESTADOR"].nunique()))
                col_o4.metric("📅 Dias em Produção", str(df_op_ln["DATA"].dt.date.nunique()))

                # Caseamento desta OP específica
                _casea_sel_ln = lencol_caseamento(df_op_ln, apenas_com_fundo=False)
                _casea_sel_ln = _casea_sel_ln[
                    (_casea_sel_ln["JOGO"] > 0) | (_casea_sel_ln["FUNDO"] > 0)
                ]
                if not _casea_sel_ln.empty and (_casea_sel_ln["FUNDO"].sum() > 0):
                    _dif_sel = int(_casea_sel_ln["DIFERENCA"].sum())
                    if _dif_sel == 0:
                        st.success(f"✅ OP {op_sel_ln}: jogo e fundo caseados por tamanho.")
                    else:
                        _txt_sel = (f"faltam {lencol_fmt_num(abs(_dif_sel))} fundos" if _dif_sel < 0
                                    else f"sobram {lencol_fmt_num(_dif_sel)} fundos")
                        st.warning(f"⚠️ OP {op_sel_ln}: caseamento divergente — {_txt_sel} no total.")
                    _casea_sel_show = _casea_sel_ln.copy()
                    _casea_sel_show["JOGO"] = _casea_sel_show["JOGO"].apply(lencol_fmt_num)
                    _casea_sel_show["FUNDO"] = _casea_sel_show["FUNDO"].apply(lencol_fmt_num)
                    _casea_sel_show["DIFERENCA"] = _casea_sel_show["DIFERENCA"].apply(
                        lambda v: f"{'+' if v > 0 else ''}{lencol_fmt_num(v)}"
                    )
                    st.dataframe(
                        _casea_sel_show.rename(columns={
                            "TAMANHO": "Tamanho", "JOGO": "Jogo", "FUNDO": "Fundo",
                            "DIFERENCA": "Diferença", "STATUS": "Status",
                        }).drop(columns=["OP"]),
                        use_container_width=True, hide_index=True,
                    )

                col_oa, col_ob = st.columns(2)
                with col_oa:
                    st.markdown("<div class='ln-sec'>Peças por Prestador</div>", unsafe_allow_html=True)
                    df_op_prest_ln = (
                        df_op_ln.groupby("PRESTADOR")["QUANT"].sum()
                        .reset_index().sort_values("QUANT", ascending=True)
                    )
                    fig_op_p_ln = go.Figure(go.Bar(
                        x=df_op_prest_ln["QUANT"], y=df_op_prest_ln["PRESTADOR"],
                        orientation="h",
                        text=[lencol_fmt_num(v) for v in df_op_prest_ln["QUANT"]],
                        textposition="outside", textfont=dict(color="#CBD5E0"),
                        marker_color="#4ECDC4",
                    ))
                    fig_op_p_ln.update_layout(**lencol_layout_dark(
                        height=max(240, len(df_op_prest_ln) * 42),
                        title=f"Peças por prestador — OP {op_sel_ln}",
                    ))
                    st.plotly_chart(fig_op_p_ln, use_container_width=True)

                with col_ob:
                    st.markdown("<div class='ln-sec'>Peças por Empresa</div>", unsafe_allow_html=True)
                    df_op_emp_ln = (
                        df_op_ln.groupby("EMPRESA")["QUANT"].sum()
                        .reset_index().sort_values("QUANT", ascending=True)
                    )
                    fig_op_e_ln = go.Figure(go.Bar(
                        x=df_op_emp_ln["QUANT"], y=df_op_emp_ln["EMPRESA"],
                        orientation="h",
                        text=[lencol_fmt_num(v) for v in df_op_emp_ln["QUANT"]],
                        textposition="outside", textfont=dict(color="#CBD5E0"),
                        marker=dict(color=[lencol_cor_empresa(e) for e in df_op_emp_ln["EMPRESA"]]),
                    ))
                    fig_op_e_ln.update_layout(**lencol_layout_dark(
                        height=max(240, len(df_op_emp_ln) * 42),
                        title=f"Peças por empresa — OP {op_sel_ln}",
                    ))
                    st.plotly_chart(fig_op_e_ln, use_container_width=True)

                col_oc, col_od = st.columns(2)
                with col_oc:
                    st.markdown("<div class='ln-sec'>Peças por Categoria</div>", unsafe_allow_html=True)
                    df_op_cat_ln = (
                        df_op_ln.groupby("CAT_BASE")["QUANT"].sum()
                        .reset_index().sort_values("QUANT", ascending=True)
                    )
                    if df_op_cat_ln.empty or df_op_cat_ln["CAT_BASE"].str.strip().eq("").all():
                        df_op_cat_ln = (
                            df_op_ln.groupby("CATEGORIA")["QUANT"].sum()
                            .reset_index().sort_values("QUANT", ascending=True)
                        )
                        df_op_cat_ln.columns = ["CAT_BASE", "QUANT"]
                    fig_op_c_ln = go.Figure(go.Bar(
                        x=df_op_cat_ln["QUANT"], y=df_op_cat_ln["CAT_BASE"],
                        orientation="h",
                        text=[lencol_fmt_num(v) for v in df_op_cat_ln["QUANT"]],
                        textposition="outside", textfont=dict(color="#CBD5E0"),
                        marker_color="#FF6B6B",
                    ))
                    fig_op_c_ln.update_layout(**lencol_layout_dark(
                        height=max(240, len(df_op_cat_ln) * 42),
                        title=f"Peças por categoria — OP {op_sel_ln}",
                    ))
                    st.plotly_chart(fig_op_c_ln, use_container_width=True)

                with col_od:
                    st.markdown("<div class='ln-sec'>Produção Diária desta OP</div>", unsafe_allow_html=True)
                    df_op_dia_ln = (
                        df_op_ln.groupby("DATA")["QUANT"].sum()
                        .reset_index().sort_values("DATA")
                    )
                    fig_op_dia_ln = go.Figure(go.Bar(
                        x=df_op_dia_ln["DATA"], y=df_op_dia_ln["QUANT"],
                        text=[lencol_fmt_num(v) for v in df_op_dia_ln["QUANT"]],
                        textposition="outside", textfont=dict(color="#CBD5E0"),
                        marker_color="rgba(78,205,196,0.5)",
                    ))
                    fig_op_dia_ln.update_layout(**lencol_layout_dark(
                        height=max(240, len(df_op_dia_ln) * 30),
                        title=f"Evolução diária — OP {op_sel_ln}",
                    ))
                    fig_op_dia_ln.update_xaxes(tickformat="%d/%m/%Y")
                    st.plotly_chart(fig_op_dia_ln, use_container_width=True)

                st.markdown("<div class='ln-sec'>Registros Detalhados</div>", unsafe_allow_html=True)
                df_op_det_ln = df_op_ln[[
                    "DATA", "PRESTADOR", "EMPRESA", "CATEGORIA",
                    "TECIDO", "QUANT", "VALOR_PECA", "VALOR_RECEBER", "OBS",
                ]].copy().sort_values("DATA")
                df_op_det_ln["DATA"] = df_op_det_ln["DATA"].dt.strftime("%d/%m/%Y")
                df_op_det_ln["VALOR_PECA"] = df_op_det_ln["VALOR_PECA"].apply(lencol_fmt_brl)
                df_op_det_ln["VALOR_RECEBER"] = df_op_det_ln["VALOR_RECEBER"].apply(lencol_fmt_brl)
                df_op_det_ln["QUANT"] = df_op_det_ln["QUANT"].apply(lencol_fmt_num)
                st.dataframe(
                    df_op_det_ln.rename(columns={
                        "DATA": "Data", "PRESTADOR": "Prestador", "EMPRESA": "Empresa",
                        "CATEGORIA": "Categoria", "TECIDO": "Tecido", "QUANT": "Peças",
                        "VALOR_PECA": "R$/Peça", "VALOR_RECEBER": "Total R$", "OBS": "OBS",
                    }),
                    use_container_width=True, height=320, hide_index=True,
                )

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#606878; font-size:0.82rem;'>"
        "✂️ Arealva · Lençol &nbsp;|&nbsp; Alimentado pela planilha CONTROLE DE CORTE DIÁRIO LENÇOL &nbsp;|&nbsp; "
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        "</div>",
        unsafe_allow_html=True,
    )

# ── SCREEN — ITAJU ────────────────────────────────────────────────────────────
elif screen == 'itaju':

    st.markdown("""
    <style>
    .it-sec {
        font-size:1rem;font-weight:700;color:#E2E8F0;
        margin:20px 0 10px 0;padding-bottom:6px;
        border-bottom:2px solid rgba(52,211,153,.35);
    }
    .it-badge {
        display:inline-block;padding:4px 14px;border-radius:999px;
        font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;
        color:#34D399;background:rgba(52,211,153,.10);
        border:1px solid rgba(52,211,153,.30);font-weight:600;margin-bottom:16px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Controle de Corte</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Regiões</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Itaju · Ponto Palito</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Carregar dados ──────────────────────────────────────────────────────
    with st.spinner("⏳ Carregando dados de Itaju…"):
        df_it_raw = load_itaju()

    if df_it_raw.empty:
        st.error("❌ Não foi possível carregar a planilha de Itaju.")
        st.info("Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link pode visualizar'.")
        col_bk, *_ = st.columns([2, 5])
        with col_bk:
            if st.button("← Voltar às Regiões", key="itaju_back_err"):
                _go('regions')
        st.stop()

    data_min_it = df_it_raw["DATA"].min().date()
    data_max_it = df_it_raw["DATA"].max().date()
    hoje_it = datetime.now().date()

    # ── Sidebar ─────────────────────────────────────────────────────────────
    with st.sidebar:
        st.caption(f"Atualizado a cada {ITAJU_CACHE_TTL}s · {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Limpar Cache", key="it_clear", use_container_width=True):
            load_itaju.clear()
            st.rerun()

        st.markdown("**📅 Período**")
        periodo_it = st.radio(
            "Preset Itaju", ["7 dias", "30 dias", "Mês atual", "Todo o período", "Personalizado"],
            index=3, label_visibility="collapsed", key="it_periodo_opt",
        )
        if periodo_it == "7 dias":
            p_ini_it, p_fim_it = hoje_it - timedelta(days=6), hoje_it
        elif periodo_it == "30 dias":
            p_ini_it, p_fim_it = hoje_it - timedelta(days=29), hoje_it
        elif periodo_it == "Mês atual":
            p_ini_it = hoje_it.replace(day=1)
            p_fim_it = hoje_it
            if p_ini_it > data_max_it:
                p_fim_it = p_ini_it - timedelta(days=1)
                p_ini_it = p_fim_it.replace(day=1)
        elif periodo_it == "Todo o período":
            p_ini_it, p_fim_it = data_min_it, data_max_it
        else:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                p_ini_it = st.date_input("De", value=data_min_it, format="DD/MM/YYYY", key="it_ini")
            with col_d2:
                p_fim_it = st.date_input("Até", value=data_max_it, format="DD/MM/YYYY", key="it_fim")
        p_ini_it = max(p_ini_it, data_min_it)

        st.markdown("**🔍 Filtros**")
        ops_disp = sorted(df_it_raw["OP"].unique())
        sel_ops_it = st.multiselect("OP", ops_disp, placeholder="Todas", key="it_op")

        if "ESTACAO" in df_it_raw.columns:
            est_disp = sorted(df_it_raw["ESTACAO"].unique())
            sel_est_it = st.multiselect("Estação de Corte", est_disp, placeholder="Todas", key="it_est")
        else:
            sel_est_it = []

        if "COR" in df_it_raw.columns:
            cor_disp = sorted(df_it_raw["COR"].unique())
            sel_cor_it = st.multiselect("Cor", cor_disp, placeholder="Todas", key="it_cor")
        else:
            sel_cor_it = []

        tam_disp = sorted(df_it_raw["TAMANHO"].unique())
        sel_tam_it = st.multiselect("Tamanho", tam_disp, placeholder="Todos", key="it_tam")

        st.caption(f"📊 {len(df_it_raw):,} registros totais".replace(",", "."))

    # ── Aplicar filtros ─────────────────────────────────────────────────────
    df_it = df_it_raw[
        (df_it_raw["DATA"].dt.date >= p_ini_it) &
        (df_it_raw["DATA"].dt.date <= p_fim_it)
    ].copy()
    if sel_ops_it:  df_it = df_it[df_it["OP"].isin(sel_ops_it)]
    if sel_est_it:  df_it = df_it[df_it["ESTACAO"].isin(sel_est_it)]
    if sel_cor_it:  df_it = df_it[df_it["COR"].isin(sel_cor_it)]
    if sel_tam_it:  df_it = df_it[df_it["TAMANHO"].isin(sel_tam_it)]

    if df_it.empty:
        st.warning("⚠️ Nenhum dado para os filtros selecionados.")
        st.stop()

    # ── Cabeçalho ───────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center'><span class='it-badge'>🧵 Itaju · Ponto Palito Marcelino</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h1 style='text-align:center;color:#FFF;font-size:2rem;font-weight:800;margin-bottom:2px'>"
        f"✂️ Dashboard Corte · Ponto Palito</h1>"
        f"<p style='text-align:center;color:#718096;font-size:.9rem;margin-bottom:0'>"
        f"{p_ini_it.strftime('%d/%m/%Y')} — {p_fim_it.strftime('%d/%m/%Y')} · "
        f"{int(df_it['QUANTIDADE'].sum()):,} peças</p>".replace(",", "."),
        unsafe_allow_html=True,
    )
    st.divider()

    # ── KPIs globais ────────────────────────────────────────────────────────
    total_it      = int(df_it["QUANTIDADE"].sum())
    tot_cima      = int(df_it[df_it["PRODUTO"] == "CIMA"]["QUANTIDADE"].sum())
    tot_fundo     = int(df_it[df_it["PRODUTO"] == "FUNDO"]["QUANTIDADE"].sum())
    tot_fronha    = int(df_it[df_it["PRODUTO"] == "FRONHA"]["QUANTIDADE"].sum())
    dias_com_it   = df_it["DATA"].dt.date.nunique()
    media_dia_it  = total_it / dias_com_it if dias_com_it else 0
    n_ops_it      = df_it["OP"].nunique()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🧵 Total Peças",    _itaju_fmt(total_it))
    c2.metric("⬆️ Cima",          _itaju_fmt(tot_cima))
    c3.metric("⬇️ Fundo",         _itaju_fmt(tot_fundo))
    c4.metric("🪡 Fronha",        _itaju_fmt(tot_fronha))
    c5.metric("📆 Dias Trabalhados", str(dias_com_it))
    c6.metric("📋 OPs",            str(n_ops_it))

    st.divider()

    # ── Caseamento CIMA × FUNDO ─────────────────────────────────────────────
    st.markdown("<div class='it-sec'>🔄 Caseamento — Cima × Fundo × Fronha por OP</div>", unsafe_allow_html=True)
    st.caption(
        "Para cada OP + Tamanho + Cor, a quantidade de **Cima** e **Fundo** deve ser igual. "
        "A **Fronha** é registrada separadamente. Divergência indica que o corte de um dos lados está incompleto."
    )

    df_casea_it = itaju_caseamento(df_it)

    if df_casea_it.empty:
        st.info("Sem dados suficientes para caseamento no período selecionado.")
    else:
        n_total_ops_c = len(df_casea_it)
        n_ok   = (df_casea_it["STATUS"] == "✅ Caseado").sum()
        n_div  = n_total_ops_c - n_ok
        saldo  = int(df_casea_it["DIFER_CF"].sum())

        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("🧩 OPs no período", str(n_total_ops_c))
        cc2.metric("✅ Caseadas (Cima=Fundo)", str(n_ok))
        cc3.metric("🚩 Divergentes", str(n_div),
                   delta=("Tudo caseado" if n_div == 0 else f"{n_div} pendente(s)"),
                   delta_color=("off" if n_div == 0 else "inverse"))
        cc4.metric("⚖️ Saldo Geral (Fundo−Cima)",
                   f"{'+' if saldo > 0 else ''}{_itaju_fmt(saldo)}",
                   delta=("Caseado" if saldo == 0 else ("Faltam fundos" if saldo < 0 else "Sobram fundos")),
                   delta_color=("off" if saldo == 0 else "inverse"))

        # Tabela de divergências
        div_it = df_casea_it[df_casea_it["STATUS"] != "✅ Caseado"]
        if not div_it.empty:
            with st.expander(f"🔎 Ver {len(div_it)} divergência(s)", expanded=True):
                show_div = div_it.copy()
                for col in ["CIMA", "FUNDO", "FRONHA"]:
                    show_div[col] = show_div[col].apply(_itaju_fmt)
                show_div["DIFER_CF"] = show_div["DIFER_CF"].apply(
                    lambda v: f"{'+' if v > 0 else ''}{_itaju_fmt(v)}"
                )
                st.dataframe(
                    show_div.rename(columns={
                        "OP": "OP", "TAMANHO": "Tamanho", "COR": "Cor",
                        "CIMA": "Cima", "FUNDO": "Fundo", "FRONHA": "Fronha",
                        "DIFER_CF": "Dif. (F−C)", "STATUS": "Status",
                    }),
                    use_container_width=True, hide_index=True,
                )
        else:
            st.success("✅ Todas as OPs do período estão caseadas (Cima = Fundo).")

        with st.expander("📋 Caseamento completo (todas as OPs)", expanded=False):
            show_all = df_casea_it.copy()
            for col in ["CIMA", "FUNDO", "FRONHA"]:
                show_all[col] = show_all[col].apply(_itaju_fmt)
            show_all["DIFER_CF"] = show_all["DIFER_CF"].apply(
                lambda v: f"{'+' if v > 0 else ''}{_itaju_fmt(v)}"
            )
            st.dataframe(
                show_all.rename(columns={
                    "OP": "OP", "TAMANHO": "Tamanho", "COR": "Cor",
                    "CIMA": "Cima", "FUNDO": "Fundo", "FRONHA": "Fronha",
                    "DIFER_CF": "Dif. (F−C)", "STATUS": "Status",
                }),
                use_container_width=True, hide_index=True,
            )

    st.divider()

    # ── Gráficos ────────────────────────────────────────────────────────────
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("<div class='it-sec'>Produção Diária por Produto</div>", unsafe_allow_html=True)
        df_dia_it = (
            df_it.groupby(["DATA", "PRODUTO"])["QUANTIDADE"]
            .sum().reset_index()
        )
        df_dia_it["DATA_STR"] = df_dia_it["DATA"].dt.strftime("%d/%m")
        fig_it1 = go.Figure()
        for prod in ["CIMA", "FUNDO", "FRONHA"]:
            sub = df_dia_it[df_dia_it["PRODUTO"] == prod]
            if not sub.empty:
                fig_it1.add_bar(
                    x=sub["DATA_STR"], y=sub["QUANTIDADE"],
                    name=prod, marker_color=ITAJU_CORES_PRODUTO.get(prod, "#718096"),
                )
        fig_it1.update_layout(**_itaju_layout(barmode="group", height=300, title="Peças por dia"))
        st.plotly_chart(fig_it1, use_container_width=True)

    with col_g2:
        st.markdown("<div class='it-sec'>Mix por Produto</div>", unsafe_allow_html=True)
        df_mix_it = df_it.groupby("PRODUTO")["QUANTIDADE"].sum().reset_index()
        fig_it2 = go.Figure(go.Pie(
            labels=df_mix_it["PRODUTO"], values=df_mix_it["QUANTIDADE"],
            hole=0.5,
            marker=dict(colors=[ITAJU_CORES_PRODUTO.get(p, "#718096") for p in df_mix_it["PRODUTO"]]),
            textinfo="percent+label",
            hovertemplate="%{label}<br>%{value:,.0f} peças<br>%{percent}<extra></extra>",
        ))
        fig_it2.update_layout(**_itaju_layout(height=300,
            annotations=[dict(text="Produtos", x=.5, y=.5,
                              font=dict(size=11, color="#CBD5E0"), showarrow=False)]))
        st.plotly_chart(fig_it2, use_container_width=True)

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("<div class='it-sec'>Produção por Tamanho</div>", unsafe_allow_html=True)
        df_tam_it = (
            df_it.groupby(["TAMANHO", "PRODUTO"])["QUANTIDADE"]
            .sum().reset_index().sort_values("QUANTIDADE", ascending=False)
        )
        fig_it3 = go.Figure()
        for prod in ["CIMA", "FUNDO", "FRONHA"]:
            sub = df_tam_it[df_tam_it["PRODUTO"] == prod]
            if not sub.empty:
                fig_it3.add_bar(
                    x=sub["TAMANHO"], y=sub["QUANTIDADE"],
                    name=prod, marker_color=ITAJU_CORES_PRODUTO.get(prod, "#718096"),
                )
        fig_it3.update_layout(**_itaju_layout(barmode="group", height=300, title="Peças por tamanho"))
        st.plotly_chart(fig_it3, use_container_width=True)

    with col_g4:
        if "COR" in df_it.columns:
            st.markdown("<div class='it-sec'>Produção por Cor</div>", unsafe_allow_html=True)
            df_cor_it = (
                df_it.groupby("COR")["QUANTIDADE"].sum()
                .reset_index().sort_values("QUANTIDADE", ascending=True)
            )
            fig_it4 = go.Figure(go.Bar(
                x=df_cor_it["QUANTIDADE"], y=df_cor_it["COR"],
                orientation="h",
                text=[_itaju_fmt(v) for v in df_cor_it["QUANTIDADE"]],
                textposition="outside",
                marker=dict(color=df_cor_it["QUANTIDADE"],
                            colorscale=[[0, "#1C3A4A"], [1, "#34D399"]], showscale=False),
            ))
            fig_it4.update_layout(**_itaju_layout(height=300, title="Peças por cor"))
            st.plotly_chart(fig_it4, use_container_width=True)
        elif "ESTACAO" in df_it.columns:
            st.markdown("<div class='it-sec'>Produção por Estação</div>", unsafe_allow_html=True)
            df_est_it = df_it.groupby("ESTACAO")["QUANTIDADE"].sum().reset_index()
            fig_it4 = go.Figure(go.Bar(
                x=df_est_it["ESTACAO"], y=df_est_it["QUANTIDADE"],
                marker_color="#34D399",
                text=[_itaju_fmt(v) for v in df_est_it["QUANTIDADE"]],
                textposition="outside",
            ))
            fig_it4.update_layout(**_itaju_layout(height=300, title="Peças por estação"))
            st.plotly_chart(fig_it4, use_container_width=True)

    # ── Tabela por OP ───────────────────────────────────────────────────────
    st.markdown("<div class='it-sec'>📋 Detalhe por OP</div>", unsafe_allow_html=True)
    grp_cols_op = ["OP", "TAMANHO"] + (["COR"] if "COR" in df_it.columns else [])
    df_op_it = (
        df_it.groupby(grp_cols_op + ["PRODUTO"])["QUANTIDADE"]
        .sum().unstack(fill_value=0).reset_index()
    )
    df_op_it.columns = [str(c).strip() for c in df_op_it.columns]
    for col in ["CIMA", "FUNDO", "FRONHA"]:
        if col not in df_op_it.columns:
            df_op_it[col] = 0
    df_op_it["TOTAL"] = df_op_it[["CIMA", "FUNDO", "FRONHA"]].sum(axis=1)
    df_op_it["DIFER"] = df_op_it["FUNDO"] - df_op_it["CIMA"]
    df_op_it["STATUS"] = df_op_it["DIFER"].apply(
        lambda x: "✅" if x == 0 else ("🔴" if x < 0 else "🟠")
    )
    st.dataframe(
        df_op_it.rename(columns={
            "OP": "OP", "TAMANHO": "Tamanho", "COR": "Cor",
            "CIMA": "Cima", "FUNDO": "Fundo", "FRONHA": "Fronha",
            "TOTAL": "Total", "DIFER": "Dif. F−C", "STATUS": "Status",
        }),
        use_container_width=True, hide_index=True,
        height=min(50 + len(df_op_it) * 35, 500),
    )

    # ── Botão Relatório PDF ─────────────────────────────────────────────────
    def _html_itaju_relatorio() -> bytes:
        """Gera relatório HTML formatado para impressão/PDF do Corte Itaju."""
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        periodo_str = f"{p_ini_it.strftime('%d/%m/%Y')} — {p_fim_it.strftime('%d/%m/%Y')}"

        def _n(v) -> str:
            return f"{int(v):,}".replace(",", ".")

        def _casea_rows() -> str:
            if df_casea_it.empty:
                return "<tr><td colspan='8' style='text-align:center'>Sem dados</td></tr>"
            linhas = []
            for _, r in df_casea_it.iterrows():
                ok = "✅" in str(r["STATUS"])
                cls = "ok" if ok else "err"
                dif = int(r["DIFER_CF"])
                dif_s = f"{'+' if dif > 0 else ''}{_n(dif)}"
                cor_v = r.get("COR", "") if "COR" in df_casea_it.columns else ""
                linhas.append(
                    f"<tr><td>{r['OP']}</td><td>{r.get('TAMANHO','')}</td><td>{cor_v}</td>"
                    f"<td class='num'>{_n(r['CIMA'])}</td><td class='num'>{_n(r['FUNDO'])}</td>"
                    f"<td class='num'>{_n(r['FRONHA'])}</td>"
                    f"<td class='num s{cls}'>{dif_s}</td><td class='s{cls}'>{r['STATUS']}</td></tr>"
                )
            return "\n".join(linhas)

        def _op_rows() -> str:
            if df_op_it.empty:
                return "<tr><td colspan='9' style='text-align:center'>Sem dados</td></tr>"
            tem_cor = "COR" in df_op_it.columns
            linhas = []
            for _, r in df_op_it.iterrows():
                dif = int(r["DIFER"])
                dif_s = f"{'+' if dif > 0 else ''}{_n(dif)}"
                cls = "ok" if r["STATUS"] == "✅" else "err"
                dif_color = "#B91C1C" if dif != 0 else "#065F46"
                cor_td = f"<td>{r.get('COR','')}</td>" if tem_cor else ""
                linhas.append(
                    f"<tr><td>{r['OP']}</td><td>{r.get('TAMANHO','')}</td>{cor_td}"
                    f"<td class='num'>{_n(r['CIMA'])}</td><td class='num'>{_n(r['FUNDO'])}</td>"
                    f"<td class='num'>{_n(r['FRONHA'])}</td><td class='num'>{_n(r['TOTAL'])}</td>"
                    f"<td class='num' style='color:{dif_color};font-weight:600'>{dif_s}</td>"
                    f"<td class='s{cls}'>{r['STATUS']}</td></tr>"
                )
            return "\n".join(linhas)

        cor_th = "<th>Cor</th>" if "COR" in df_op_it.columns else ""
        casea_html = _casea_rows()
        op_html    = _op_rows()

        html = (
            "<!DOCTYPE html>\n"
            "<html lang='pt-BR'>\n"
            "<head>\n"
            "<meta charset='UTF-8'>\n"
            f"<title>Relatório Corte Itaju · {periodo_str}</title>\n"
            "<style>\n"
            "@page { margin: 15mm; size: A4 landscape; }\n"
            "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
            "body { font-family: Arial, sans-serif; font-size: 10px; color: #1a1a1a; background: #fff; }\n"
            ".hint { background:#FEF3C7; padding:8px 14px; margin-bottom:14px; border-radius:4px;"
            "        font-size:12px; border:1px solid #FCD34D; }\n"
            ".header { border-bottom:3px solid #065F46; padding-bottom:8px; margin-bottom:14px; }\n"
            ".header h1 { font-size:17px; color:#065F46; }\n"
            ".header .sub { color:#444; margin-top:3px; font-size:10px; }\n"
            ".kpi-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:7px; margin-bottom:16px; }\n"
            ".kpi { border:1px solid #34D399; border-radius:5px; padding:7px 9px; text-align:center; }\n"
            ".kpi-lbl { font-size:8px; color:#555; text-transform:uppercase; letter-spacing:.05em; }\n"
            ".kpi-val { font-size:15px; font-weight:700; color:#065F46; margin-top:2px; }\n"
            ".sec { font-size:11px; font-weight:700; color:#065F46;"
            "       border-bottom:1px solid #34D399; margin:14px 0 7px 0; padding-bottom:3px; }\n"
            "table { width:100%; border-collapse:collapse; margin-bottom:14px; font-size:9.5px; }\n"
            "th { background:#065F46; color:#fff; padding:4px 6px; text-align:left;"
            "     font-size:8.5px; text-transform:uppercase; letter-spacing:.04em; }\n"
            "td { padding:3px 6px; border-bottom:1px solid #e5e7eb; }\n"
            "tr:nth-child(even) td { background:#F0FDF4; }\n"
            ".num { text-align:right; font-variant-numeric:tabular-nums; }\n"
            ".sok { color:#065F46; font-weight:600; }\n"
            ".serr { color:#B91C1C; font-weight:600; }\n"
            ".footer { margin-top:16px; padding-top:7px; border-top:1px solid #ccc;"
            "          color:#777; font-size:8px; text-align:center; }\n"
            "@media print { .hint { display:none; }"
            "  body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }\n"
            "</style>\n"
            "</head>\n"
            "<body>\n"
            "<div class='hint'>"
            "  <strong>Para gerar PDF:</strong> pressione <kbd>Ctrl+P</kbd> (Windows) ou"
            "  <kbd>⌘+P</kbd> (Mac) &rarr; escolha <em>Salvar como PDF</em>."
            "</div>\n"
            "<div class='header'>\n"
            "  <h1>&#9986; Relatório Corte Itaju &middot; Ponto Palito Marcelino</h1>\n"
            f"  <div class='sub'>Período: <strong>{periodo_str}</strong>"
            f"  &nbsp;|&nbsp; Gerado em: {agora}</div>\n"
            "</div>\n"
            "<div class='kpi-grid'>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Total Peças</div><div class='kpi-val'>{_n(total_it)}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Cima</div><div class='kpi-val'>{_n(tot_cima)}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Fundo</div><div class='kpi-val'>{_n(tot_fundo)}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Fronha</div><div class='kpi-val'>{_n(tot_fronha)}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Dias Trabalhados</div><div class='kpi-val'>{dias_com_it}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>OPs</div><div class='kpi-val'>{n_ops_it}</div></div>\n"
            "</div>\n"
            "<div class='sec'>Caseamento &mdash; Cima &times; Fundo &times; Fronha por OP</div>\n"
            "<table>\n"
            "  <thead><tr><th>OP</th><th>Tamanho</th><th>Cor</th>"
            "<th class='num'>Cima</th><th class='num'>Fundo</th><th class='num'>Fronha</th>"
            "<th class='num'>Dif. (F&minus;C)</th><th>Status</th></tr></thead>\n"
            f"  <tbody>{casea_html}</tbody>\n"
            "</table>\n"
            "<div class='sec'>Detalhe por OP</div>\n"
            "<table>\n"
            f"  <thead><tr><th>OP</th><th>Tamanho</th>{cor_th}"
            "<th class='num'>Cima</th><th class='num'>Fundo</th><th class='num'>Fronha</th>"
            "<th class='num'>Total</th><th class='num'>Dif. F&minus;C</th><th>Status</th></tr></thead>\n"
            f"  <tbody>{op_html}</tbody>\n"
            "</table>\n"
            "<div class='footer'>"
            f"Relatório Corte Itaju &middot; Ponto Palito Marcelino &middot; "
            f"Sistema Unificação dos Dados &middot; {agora}"
            "</div>\n"
            "</body>\n"
            "</html>"
        )
        return html.encode("utf-8")

    st.divider()
    _col_l, _col_c, _col_r = st.columns([3, 2, 3])
    with _col_c:
        st.download_button(
            label="📄 Gerar Relatório PDF",
            data=_html_itaju_relatorio(),
            file_name=(
                f"relatorio_itaju_{p_ini_it.strftime('%Y%m%d')}"
                f"_{p_fim_it.strftime('%Y%m%d')}.html"
            ),
            mime="text/html",
            use_container_width=True,
        )
    st.markdown(
        "<p style='text-align:center;color:#718096;font-size:.8rem;margin-top:4px'>"
        "Abre no navegador &rarr; <kbd>Ctrl+P</kbd> &rarr; Salvar como PDF</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#606878;font-size:.82rem;'>"
        f"🧵 Itaju · Ponto Palito Marcelino &nbsp;|&nbsp; "
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        f"</div>",
        unsafe_allow_html=True,
    )
