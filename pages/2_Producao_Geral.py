import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import logging
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import re
import io
import os
import sys
import unicodedata
import numpy as np

# Garante que a raiz do projeto esteja no path (para imports utils/styles/config
# mesmo quando a página é aberta diretamente).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.auth import init_session_state
from styles.global_ui import get_global_ui_css
from styles.selector_cards import get_selector_cards_css
from config.settings import PRODUCAO_INTERNO_SHEETS, CORES_FACCAO
from utils.producao_interno_loader import load_interno_unidade
from utils.producao_unificada import (
    load_producao_unificada,
    _calcular_meta_faccao_periodo,
    _calcular_meta_cliente_periodo,
    grupo_de,
    is_quarterizada,
    GRUPO_QUARTERIZADAS,
)
from utils.faccoes_metas_calc import calcular_meta_faccoes
from utils.faccoes_viz import heatmap_por_dimensao, consistencia_por_dimensao
from utils.feriados import eh_dia_util, eh_feriado, nome_feriado, feriados_no_periodo
from utils.ui_helpers import multiselect_reset_on_grow as _multiselect_reset_on_grow

# ─
# CONFIGURACAO DA PAGINA
# ─
st.set_page_config(
    page_title="Dashboard Produção - Empresas",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(get_global_ui_css(), unsafe_allow_html=True)

# ─
# CSS CUSTOMIZADO
# ─
st.markdown("""
<style>
    footer {visibility: hidden;}
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1C1C22 0%, #28282E 100%);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label {
        color: #FFFFFF !important; font-size: 0.8rem !important;
        font-weight: 600 !important; text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important; font-weight: 700 !important; font-size: 1.8rem !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #1C1C22, #28282E) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #FFFFFF !important; border-radius: 10px !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        border-color: #4ECDC4 !important;
        box-shadow: 0 0 15px rgba(78,205,196,0.3) !important;
        color: #4ECDC4 !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111115 0%, #191920 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    section[data-testid="stSidebar"] * { color: #E0E0E0 !important; }
    .main-title {
        text-align: center; color: #FFFFFF; font-size: 2.6rem;
        font-weight: 800; margin-bottom: 0; letter-spacing: 0.5px;
    }
    .sub-title {
        text-align: center; color: #A0A0A0; font-size: 1.15rem;
        margin-top: 4px; margin-bottom: 20px;
    }
    .section-title {
        text-align: center; color: #FFFFFF; font-size: 1.4rem;
        font-weight: 700; margin: 24px 0 12px 0;
    }
    hr { border: none; border-top: 1px solid rgba(255,255,255,0.12); margin: 20px 0; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    .stProgress > div > div > div { background-color: #4ECDC4 !important; }
    span[data-baseweb="tag"] {
        background-color: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: #FFFFFF !important;
        font-size: 0.9rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ─
# CONSTANTES
# ─
SPREADSHEET_ID = "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y"

DARK_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0"),
    xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748"),
    yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748"),
    separators=",.",
)

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

MESES_NOME = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

NOMES_DIAS = {
    "Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
    "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom",
}

ORDEM_DIAS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# ─
# LITEX_GERAL — suplemento diário da Niazitex
# (a aba Niazitex no xlsx não é preenchida; os dados reais ficam nesta planilha)
# ─
_LITEX_GERAL_ID  = "1SF2ZumsloWdUVAMt1SRYd1o5gNIY9RXD"
_LITEX_GERAL_GID = "1697720285"

# ─
# PLANO DE METAS — fonte de Meta Diária autoritativa
# (substitui os valores de Meta Diaria do xlsx de Produção Geral)
# ─
_METAS_SHEET_ID_PG = "1gOhDE__QZ_AbgXZZZWuLTUfR-P1CYPvh"
_METAS_GID_PG      = "1593003426"
_MESES_PT_ABR_PG   = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

# metas diárias hardcoded — niazittex / seven
# Fonte: Plano de Metas (aprovado pelo usuário).
# Chaves = resultado de _norm_produto_niazi() aplicado ao nome do produto.
_NIAZI_SEVEN_METAS: dict[str, float] = {
    "FRONHA":             3_000.0,
    "LENCOL COM ELASTIC": 3_000.0,
    "LENCOL PLANO":       5_000.0,
    "JOGO SIMPLES":       2_000.0,
    # MANTA e TOALHA DE MESA: sem meta definida por enquanto
}
# Nome canônico da empresa no dashboard
_NIAZI_SEVEN_KEY = "Niazittex / Seven"

_PROD_SUFIXOS_PG = frozenset({
    "ST", "CS", "QN", "KG", "SL", "EX", "CAL",
    "SOLTEIRO", "CASAL", "QUEEN", "KING", "AVULSA",
    "HOTEL", "EXTRA", "SUPER", "PLUS", "P", "M", "G", "GG",
})

def _norm_pg(s: str) -> str:
    """Uppercase + remove acentos."""
    s = str(s).strip().upper()
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

def _base_prod_pg(nome: str) -> str:
    """'LENCOL ST' → 'LENCOL', 'FRONHA AVULSA P' → 'FRONHA'."""
    words = _norm_pg(nome).split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0]
    result = [words[0]]
    for w in words[1:]:
        if w in _PROD_SUFIXOS_PG or (len(w) <= 2 and w.isalpha()):
            break
        result.append(w)
    return " ".join(result)

def _parse_num_pg(val) -> float | None:
    """Converte número no formato brasileiro ('1.234,56' ou '150') → float. Retorna None se inválido."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "nan", "None", "#ERROR!", "#VALOR!", "#NAME?", "-"):
        return None
    s = re.sub(r"[R$\s]", "", s)
    # Formato brasileiro: ponto como milhar, vírgula como decimal
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.search(r"\.\d{3}$", s):
        # "3.000" → ponto é separador de milhar, não decimal
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None

def _load_metas_lookup_pg() -> dict:
    """
    Baixa a planilha de Plano de Metas e retorna lookup:
      {(faccao_norm, produto_base, mes, ano): meta_diaria}

    Faccao é normalizado por _norm_pg(); produto pela base (_base_prod_pg()).
    Chaves são geradas tanto para RESPONSÁVEL (primário) quanto para CLIENTE
    (fallback), permitindo correspondência mesmo quando o Faccao é o nome da empresa.

    NÃO usa @st.cache_data — chamado de dentro de load_all_data() que já é cacheada.
    """
    from utils.cache_manager import get_raw as _get_raw
    content = _get_raw(_METAS_SHEET_ID_PG, _METAS_GID_PG, ttl=300)
    try:
        if not content:
            raise ValueError("Planilha de metas indisponível")
        df_raw = pd.read_csv(io.StringIO(content), dtype=str)
        df_raw.columns = [c.strip().upper() for c in df_raw.columns]
    except Exception as e:
        print(f"[METAS_LOOKUP] Erro ao carregar planilha de metas: {e}")
        return {}

    # Detecta colunas pelo nome (tolerante a variações)
    col_resp   = next((c for c in df_raw.columns if "RESPONSAVEL" in _norm_pg(c)), None)
    col_cli    = next((c for c in df_raw.columns if _norm_pg(c) == "CLIENTE"),     None)
    col_prod   = next((c for c in df_raw.columns if _norm_pg(c) == "PRODUTO"),     None)
    col_meta_d = next((c for c in df_raw.columns if "META" in _norm_pg(c) and "DIARI" in _norm_pg(c)), None)
    col_meta_m = next((c for c in df_raw.columns if "META" in _norm_pg(c) and "MES" in _norm_pg(c)),   None)
    col_data_b = next((c for c in df_raw.columns if "DATA" in _norm_pg(c) and "BASE" in _norm_pg(c)),  None)
    col_status = next((c for c in df_raw.columns if _norm_pg(c) == "STATUS"),      None)

    if not all([col_resp, col_prod, col_data_b, col_status]):
        print(f"[METAS_LOOKUP] Colunas essenciais ausentes. Disponíveis: {list(df_raw.columns)}")
        return {}

    lookup: dict = {}
    for _, row in df_raw.iterrows():
        status = _norm_pg(str(row.get(col_status, "")))
        if status != "PREVISTO":
            continue

        # mês e ano da meta (ex: "1-mai." → mes=5, ano=2026)
        data_raw = str(row.get(col_data_b, "")).strip().lower().replace(".", "")
        m_match = re.search(r"(\d+)[\-/\s]([a-z]+)", data_raw)
        if not m_match:
            continue
        mes_str = m_match.group(2)[:3]
        mes_num = _MESES_PT_ABR_PG.get(mes_str)
        if not mes_num:
            continue
        ano_num = date.today().year  # mesma convenção de 7_Plano_de_Metas.py

        # produto: normaliza preservando nome completo (ex: "lencol com elastic" ≠ "lencol plano")
        prod_base = _norm_produto_niazi(str(row.get(col_prod, "")))
        if not prod_base:
            continue

        # meta diária: prefere meta diária, fallback meta mês
        meta_val: float | None = None
        for col_try in filter(None, [col_meta_d, col_meta_m]):
            meta_val = _parse_num_pg(row.get(col_try))
            if meta_val is not None and meta_val > 0:
                break
        if meta_val is None or meta_val <= 0:
            continue

        # armazena por responsável (primário)
        resp = _norm_pg(str(row.get(col_resp, "")))
        if resp:
            lookup.setdefault((resp, prod_base, mes_num, ano_num), meta_val)

        # armazena por cliente (fallback, sem sobrescrever chave do responsável)
        if col_cli:
            cli = _norm_pg(str(row.get(col_cli, "")))
            if cli and cli != resp:
                lookup.setdefault((cli, prod_base, mes_num, ano_num), meta_val)

    print(f"[METAS_LOOKUP] {len(lookup)} entradas carregadas do plano de metas")
    return lookup

def _norm_produto_niazi(nome: str) -> str:
    """
    Normaliza nome de produto para Niazittex.
    - Usa _base_prod_pg para remover sufixos de tamanho ("FRONHA AVULSA" → "FRONHA")
    - Preserva palavras que distinguem variantes ("LENCOL COM ELASTIC" ≠ "LENCOL PLANO")
    - Normaliza "ELASTICO" → "ELASTIC" para casar com a planilha de metas
    """
    s = _base_prod_pg(_norm_pg(nome))   # uppercase + remove acentos + remove sufixos
    s = s.replace("ELASTICO", "ELASTIC")  # "ELÁSTICO" = "ELASTIC" (planilha de metas usa sem O)
    return s

def _load_niazitex_suplementar() -> pd.DataFrame:
    """
    Carrega a planilha LITEX_GERAL e devolve apenas os dados do cliente NIAZITTEX.

    Regras:
    - Filtra coluna CLIENTE contendo "NIAZI" (cobre NIAZITEX, NIAZITTEX, NIAZI…)
    - Agrupa por (Data, Produto) somando TOTAL CONFERIDO de todos os prestadores
    - Produto é normalizado com _norm_produto_niazi (sem corte de sufixos)
    - Meta Diaria é preenchida posteriormente por _load_metas_lookup_pg()
    """
    from utils.cache_manager import get_raw as _get_raw
    content = _get_raw(_LITEX_GERAL_ID, _LITEX_GERAL_GID, ttl=120)
    try:
        if not content:
            raise ValueError("LITEX_GERAL indisponível")
        raw_full = pd.read_csv(io.StringIO(content), header=None, dtype=str)
    except Exception as e:
        logging.warning(f"LITEX_GERAL não carregado: {e}")
        return pd.DataFrame()

    # Encontra linha de cabeçalho real
    _HDR_KEYWORDS = {"DATA", "PRESTADOR", "CONFERIDO", "PRODUZIDO", "DESCRICAO", "DESCRI", "PRODUTO", "SETOR"}
    hdr_idx = None
    for i, row in raw_full.iterrows():
        vals = [_norm_pg(str(v)) for v in row.tolist()]
        if any(any(kw in v for kw in _HDR_KEYWORDS) for v in vals):
            hdr_idx = i
            break

    if hdr_idx is None:
        print(f"[LITEX_GERAL] Cabeçalho não encontrado. Primeiras linhas: {raw_full.head(3).values.tolist()}")
        return pd.DataFrame()

    raw = raw_full.iloc[hdr_idx + 1:].copy()
    raw.columns = [str(v).strip() for v in raw_full.iloc[hdr_idx].tolist()]
    raw = raw.reset_index(drop=True)

    # Localiza colunas pelo nome normalizado
    col_data = next((c for c in raw.columns if _norm_pg(c) == "DATA"), None)
    col_qtd  = next((c for c in raw.columns if "CONFERIDO" in _norm_pg(c) or "PRODUZIDO" in _norm_pg(c)), None)
    col_prod = next((c for c in raw.columns if _norm_pg(c) == "PRODUTO"), None)
    col_cli  = next((c for c in raw.columns if _norm_pg(c) == "CLIENTE"), None)

    if not col_data or not col_qtd or not col_prod:
        print(f"[LITEX_GERAL] Colunas não encontradas. Disponíveis: {list(raw.columns)} | "
              f"DATA={col_data} QTD={col_qtd} PROD={col_prod} CLI={col_cli}")
        return pd.DataFrame()

    from utils.date_parser import parse_date_series
    raw["_DATA"] = parse_date_series(raw[col_data])
    raw["_QTD"]  = pd.to_numeric(
        raw[col_qtd].str.replace(",", ".", regex=False), errors="coerce"
    ).fillna(0)
    raw["_PROD"] = raw[col_prod].apply(
        lambda x: _norm_produto_niazi(str(x))
        if pd.notna(x) and str(x).strip() not in ("", "nan", "None")
        else ""
    )

    # filtra pelos clientes niazittex e seven (combinados no dashboard)
    _CLI_KWS = ("NIAZI", "SEVEN")
    if col_cli:
        antes = len(raw)
        clientes_unicos = raw[col_cli].dropna().apply(_norm_pg).unique().tolist()
        print(f"[LITEX_GERAL] Clientes disponíveis na planilha: {clientes_unicos}")
        raw = raw[raw[col_cli].apply(
            lambda x: any(kw in _norm_pg(str(x)) for kw in _CLI_KWS) if pd.notna(x) else False
        )]
        print(f"[LITEX_GERAL] Filtro NIAZI/SEVEN: {antes} -> {len(raw)} linhas")
    else:
        print("[LITEX_GERAL] Coluna CLIENTE não encontrada — usando todas as linhas")

    # Normaliza CLIENTE → "NIAZI" / "SEVEN" / valor original
    def _norm_cli_label(x):
        if not pd.notna(x) or str(x).strip() in ("", "nan", "None"):
            return ""
        n = _norm_pg(str(x))
        if "NIAZI" in n:
            return "NIAZI"
        if "SEVEN" in n:
            return "SEVEN"
        return n

    raw["_CLI"] = raw[col_cli].apply(_norm_cli_label) if col_cli else ""

    raw = raw.dropna(subset=["_DATA"])
    raw = raw[(raw["_QTD"] > 0) & (raw["_PROD"] != "")]

    if raw.empty:
        print("[LITEX_GERAL] Nenhum registro após filtro NIAZI/SEVEN + QTD > 0")
        return pd.DataFrame()

    # Agrega por (Data, Produto, Cliente) — mantém os dois clientes separados
    df = (
        raw.groupby(["_DATA", "_PROD", "_CLI"], as_index=False)
        .agg(_QTD=("_QTD", "sum"))
    )

    print(f"[LITEX_GERAL] Produtos: {sorted(df['_PROD'].unique().tolist())}")
    print(f"[LITEX_GERAL] Clientes: {sorted(df['_CLI'].unique().tolist())}")

    df["Faccao"]      = "LITEX"
    df["Produto"]     = df["_PROD"]
    df["Cliente"]     = df["_CLI"]
    df["Data"]        = df["_DATA"]
    df["Quantidade"]  = df["_QTD"]
    df["Meta Diaria"] = pd.NA
    df["Ano"]         = df["Data"].dt.year
    df["Mes"]         = df["Data"].dt.month
    df["Mes Nome"]    = df["Mes"].map(MESES_PT)
    df["Dia"]         = df["Data"].dt.day
    df["Semana"]      = df["Data"].dt.isocalendar().week.astype(int)
    df["DiaSemana"]   = df["Data"].dt.day_name()

    df["Meta Diaria"] = pd.to_numeric(df["Meta Diaria"], errors="coerce")

    return df[[
        "Faccao", "Cliente", "Produto", "Data", "Quantidade", "Meta Diaria",
        "Ano", "Mes", "Mes Nome", "Dia", "Semana", "DiaSemana",
    ]]

# ─
# UTILITÁRIOS
# ─
def fmt_br(v, decimals=0):
    txt = f"{v:,.{decimals}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")

def dias_uteis(datas):
    """
    CONSOLIDADO MÉDIO #16: Calcula dias úteis de seg-sex no período.
    
    Uso:
    - Contar dias trabalháveis (segunda a sexta) em um período
    - Base para cálculos de meta (não inclui sábados)
    
    Args:
        datas: Lista/Series de datas
        
    Returns:
        int: Quantidade de dias de segunda a sexta (sem duplicatas)
    
    Exemplo:
        >>> dias_uteis(['2026-05-04', '2026-05-05', '2026-05-09'])  # seg, ter, sab
        2  # Retorna apenas segunda e terça (2 dias úteis)
    """
    # MÉDIO #17: drop_duplicates after normalize to count unique calendar dates
    # This ensures timestamps with different times (e.g., 14:30 vs 14:45) count as 1 day
    d = pd.to_datetime(datas).dropna().dt.normalize().drop_duplicates()
    return int(d.dt.date.map(eh_dia_util).sum())

def calcular_dias_com_sabados_trabalhados(datas_grupo):
    """
    CONSOLIDADO MÉDIO #16: Calcula dias úteis MAIS sábados onde houve produção.
    
    Uso:
    - Contar dias efetivos trabalhados (seg-sex + sábados com produção)
    - Para cálculo de meta considerando sábados trabalhados
    
    Args:
        datas_grupo: Series de datas onde houve produção
        
    Returns:
        int: Dias úteis (seg-sex) + sábados com produção
    
    Lógica:
    - Extrai TODOS os dias seg-sex do período
    - Conta APENAS os sábados (weekday=5) presentes nos dados
    - Retorna a soma: seg-sex + sábados_com_trabalho
    
    Exemplo:
        >>> # dados de 4º a 8º maio (seg-sex) + 11º e 15º (sab)
        >>> calcular_dias_com_sabados_trabalhados([...datas...])
        7  # 5 dias úteis (4-8) + 2 sábados (11, 15)
    """
    # MÉDIO #17: drop_duplicates after normalize - counts unique calendar dates
    # Handles multiple timestamps per day (e.g., morning/afternoon batches)
    d = pd.to_datetime(datas_grupo).dropna().dt.normalize().drop_duplicates()

    # Dias de segunda a sexta no período, exceto feriados (nacionais/SP) —
    # feriado só entra na conta como sábado (linha abaixo): se teve produção
    # nele, é "dia extra trabalhado", não um dia útil normal cheio.
    _dia_feriado = d.dt.date.map(eh_feriado)
    dias_seg_sex = ((d.dt.weekday <= 4) & ~_dia_feriado).sum()

    # Sábados onde houve produção (weekday 5) + feriados onde houve produção
    sabados_com_prod = (d.dt.weekday == 5).sum()
    feriados_com_prod = ((d.dt.weekday <= 4) & _dia_feriado).sum()

    return int(dias_seg_sex + sabados_com_prod + feriados_com_prod)

# REMOVIDO: dias_uteis_com_sabados_trabalhados() - ver replacement abaixo
# REMOVIDO: dias_uteis_com_trabalho() - consolidada em calcular_dias_com_sabados_trabalhados()

# ─
# PARSING DE DATAS
# ─
_SKIP_KEYWORDS = frozenset([
    "faccao", "produto", "meta", "qtde", "falta",
    "column", "cliente", "responsavel", "%", " tr",
])

_PT_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4,
    "mai": 5, "jun": 6, "jul": 7, "ago": 8,
    "set": 9, "out": 10, "nov": 11, "dez": 12,
}

def _remove_accents(text):
    replacements = {
        "\u00e7": "c", "\u00c7": "C", "\u00e3": "a", "\u00c3": "A",
        "\u00e1": "a", "\u00c1": "A", "\u00e9": "e", "\u00c9": "E",
        "\u00ed": "i", "\u00cd": "I", "\u00f3": "o", "\u00d3": "O",
        "\u00fa": "u", "\u00da": "U", "\u00e2": "a", "\u00ea": "e", "\u00f4": "o",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text

def _infer_year(month: int, base_year: int) -> int:
    current_year = datetime.now().year
    if base_year is None:
        base_year = current_year
    return base_year if month >= 10 else base_year + 1

def parse_date_header(h, base_year=None):
    if base_year is None:
        base_year = datetime.now().year

    if h is None:
        return None
    if isinstance(h, datetime):
        return h.date()
    if isinstance(h, date):
        return h

    h_str = str(h).strip()
    if not h_str or h_str.lower() == "nan":
        return None

    skip_check = _remove_accents(h_str.lower())
    if any(kw in skip_check for kw in _SKIP_KEYWORDS):
        return None

    h_norm = h_str.replace("-", "/")

    try:
        return datetime.strptime(h_norm, "%d/%m/%Y").date()
    except ValueError:
        pass

    try:
        return datetime.strptime(h_norm, "%d/%m/%y").date()
    except ValueError:
        pass

    parts = h_norm.split("/")
    if len(parts) in (2, 3):
        try:
            day = int(parts[0])
            month = int(parts[1])
            if len(parts) == 3:
                year = int(parts[2])
                year = year + 2000 if year < 100 else year
            else:
                year = _infer_year(month, base_year)
            return date(year, month, day)
        except (ValueError, TypeError):
            pass

    for abbr, month_num in _PT_MONTHS.items():
        if abbr in h_str.lower():
            match = re.search(r"(\d+)", h_str)
            if match:
                day = int(match.group(1))
                year = _infer_year(month_num, base_year)
                try:
                    return date(year, month_num, day)
                except ValueError:
                    pass

    return None

# ─
# CARREGAMENTO DOS DADOS
# ─
@st.cache_data(ttl=300)
def load_all_data():
    import requests as req

    xlsx_data = None
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx"
        r = req.get(url, timeout=30)
        r.raise_for_status()
        xlsx_data = io.BytesIO(r.content)
    except Exception as e:
        st.warning(f"Não foi possível carregar do Google Sheets: {e}. Tentando arquivo local...")
        xlsx_data = "data/planilha_producao.xlsx"

    all_data: dict[str, pd.DataFrame] = {}
    xls = pd.ExcelFile(xlsx_data, engine="openpyxl")

    _NIAZI_NOMES = {"niazitex", "niazittex", "niazi"}

    for sheet in xls.sheet_names:
        if sheet.lower() in {"diversos"} | _NIAZI_NOMES:
            # Niazitex é alimentada exclusivamente pelo LITEX_GERAL (abaixo)
            continue
        try:
            raw = pd.read_excel(xlsx_data, sheet_name=sheet, header=None, engine="openpyxl")
            parsed = _parse_sheet(raw, sheet)
            if parsed is not None and len(parsed) > 0:
                all_data[sheet] = parsed
        except Exception as e:
            st.warning(f"Erro ao processar aba '{sheet}': {e}")

    # niazitex — exclusivamente pelo litex_geral (atualizado diariamente)
    df_litex = _load_niazitex_suplementar()
    print(f"[load_all_data] Abas xlsx carregadas: {list(all_data.keys())}")
    print(f"[load_all_data] LITEX_GERAL registros: {len(df_litex)}")
    if not df_litex.empty:
        all_data[_NIAZI_SEVEN_KEY] = df_litex.sort_values("Data").reset_index(drop=True)
        print(f"[load_all_data] {_NIAZI_SEVEN_KEY} atualizada com LITEX_GERAL. "
              f"Datas: {df_litex['Data'].min()} -> {df_litex['Data'].max()}")

    # injeta meta diária da planilha de plano de metas
    # Substitui os valores de "Meta Diaria" do xlsx (que podem estar desatualizados)
    # pelos valores autoritativos do Plano de Metas.
    metas_lkp = _load_metas_lookup_pg()
    if metas_lkp:
        def _inject_meta_diaria(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            def _get_meta(row):
                fac      = _norm_pg(str(row["Faccao"]))
                # Usa mesma normalização do lookup: preserva nome completo
                prod     = _norm_produto_niazi(str(row["Produto"]))
                mes      = int(row["Mes"])
                ano      = int(row["Ano"])
                meta_plano = metas_lkp.get((fac, prod, mes, ano))
                # Usa meta do plano quando disponível; caso contrário mantém a do xlsx
                return meta_plano if meta_plano is not None else row["Meta Diaria"]
            df["Meta Diaria"] = df.apply(_get_meta, axis=1)
            # Força float64: apply() com mix de Python float + None gera dtype object,
            # o que faz pandas usar operator.truediv (Python) que lança ZeroDivisionError.
            df["Meta Diaria"] = pd.to_numeric(df["Meta Diaria"], errors="coerce")
            return df

        all_data = {k: _inject_meta_diaria(v) for k, v in all_data.items()}
        # Diagnóstico: conta quantas linhas receberam meta do plano
        total_rows  = sum(len(v) for v in all_data.values())
        com_meta    = sum((v["Meta Diaria"].notna() & (v["Meta Diaria"] > 0)).sum() for v in all_data.values())
        print(f"[load_all_data] Meta Diária injetada: {com_meta}/{total_rows} linhas com meta do plano")
    else:
        # Garante float64 mesmo sem injeção (previne object dtype residual do xlsx)
        for k in all_data:
            all_data[k]["Meta Diaria"] = pd.to_numeric(all_data[k]["Meta Diaria"], errors="coerce")

    # metas hardcoded para niazittex / seven (sobrescreve qualquer valor anterior)
    if _NIAZI_SEVEN_KEY in all_data:
        df_ns = all_data[_NIAZI_SEVEN_KEY].copy()
        df_ns["Meta Diaria"] = df_ns["Produto"].apply(
            lambda p: _NIAZI_SEVEN_METAS.get(_norm_produto_niazi(str(p)))
        )
        df_ns["Meta Diaria"] = pd.to_numeric(df_ns["Meta Diaria"], errors="coerce")
        all_data[_NIAZI_SEVEN_KEY] = df_ns
        com_meta_ns = int(df_ns["Meta Diaria"].notna().sum())
        print(f"[load_all_data] Metas hardcoded {_NIAZI_SEVEN_KEY}: "
              f"{com_meta_ns}/{len(df_ns)} linhas com meta. "
              f"Produtos com meta: {sorted(_NIAZI_SEVEN_METAS.keys())}")

    return all_data

# ─
# PARSING DE ABAS
# ─
_HEADER_LABELS = frozenset([
    "FACCAO", "PRODUTO", "META DIARIA", "META MENSAL",
    "QTDE PRODUZIDA", "FALTA", "CLIENTE",
])

def _is_header_row(row_series) -> bool:
    vals = row_series.astype(str).str.upper().tolist()
    for v in vals:
        v = str(v).strip()
        v_clean = _remove_accents(v)
        if "FACCAO" in v_clean or v == "PRODUTO":
            return True
    return False

def _find_all_header_rows(raw) -> list[int]:
    header_rows = []
    for i in range(len(raw)):
        if _is_header_row(raw.iloc[i]):
            header_rows.append(i)
    return header_rows

def _parse_block(raw_block: pd.DataFrame, headers: list, sheet_name: str) -> list[dict]:
    col_idx: dict[str, int] = {}
    for idx, h in enumerate(headers):
        if h is None or str(h) == "nan":
            continue
        hu = str(h).upper().strip()
        hu_clean = _remove_accents(hu)

        if "FACCAO" in hu_clean and "faccao" not in col_idx:
            col_idx["faccao"] = idx
        elif hu == "PRODUTO" and "produto" not in col_idx:
            col_idx["produto"] = idx
        elif hu == "CLIENTE" and "faccao" not in col_idx:
            col_idx["faccao"] = idx
        elif ("META" in hu and ("DIARI" in hu_clean or "DIARIA" in hu_clean)
              and "meta_diaria" not in col_idx):
            col_idx["meta_diaria"] = idx

    date_cols: dict[int, date] = {}
    for idx, h in enumerate(headers):
        d = parse_date_header(h)
        if d is not None:
            date_cols[idx] = d

    if not date_cols or "produto" not in col_idx:
        return []

    records = []
    last_faccao = None   # herda facção quando coluna usa células mescladas
    last_produto = None  # herda produto quando coluna usa células mescladas
    for _, row in raw_block.iterrows():
        if "faccao" in col_idx:
            fv = row.iloc[col_idx["faccao"]]
            if pd.isna(fv) or str(fv).strip() in ("", "nan", "None"):
                # célula vazia = célula mesclada — herda a facção anterior
                if last_faccao is None:
                    continue
                faccao = last_faccao
            else:
                faccao = str(fv).strip().upper()
                if _remove_accents(faccao) in _HEADER_LABELS or faccao in _HEADER_LABELS:
                    last_faccao = None
                    last_produto = None
                    continue
                last_faccao = faccao
        else:
            faccao = sheet_name.upper()

        pv = row.iloc[col_idx["produto"]]
        if pd.isna(pv) or str(pv).strip() in ("", "nan", "None"):
            # célula vazia = célula mesclada — herda o produto anterior
            if last_produto is None:
                continue
            produto = last_produto
        else:
            produto = str(pv).strip().upper()
            if _remove_accents(produto) in _HEADER_LABELS or produto in _HEADER_LABELS:
                last_produto = None
                continue
            last_produto = produto

        meta_d = None
        if "meta_diaria" in col_idx:
            mv = row.iloc[col_idx["meta_diaria"]]
            try:
                meta_d = float(mv) if pd.notna(mv) else None
            except (ValueError, TypeError):
                meta_d = None

        for ci, dt in date_cols.items():
            try:
                v = row.iloc[ci]
                qty = float(v) if (pd.notna(v) and str(v).strip() not in ("-", "")) else 0.0
            except (ValueError, TypeError, IndexError):
                qty = 0.0

            records.append({
                "Faccao": faccao,
                "Produto": produto,
                "Data": dt,
                "Quantidade": qty,
                "Meta Diaria": meta_d,
            })

    return records

def _parse_sheet(raw: pd.DataFrame, sheet_name: str) -> pd.DataFrame | None:
    header_rows = _find_all_header_rows(raw)

    if not header_rows:
        return None

    all_records: list[dict] = []

    for block_num, header_idx in enumerate(header_rows):
        next_header = header_rows[block_num + 1] if block_num + 1 < len(header_rows) else len(raw)
        headers = raw.iloc[header_idx].tolist()
        block_data = raw.iloc[header_idx + 1 : next_header].reset_index(drop=True)
        block_data = block_data.dropna(how="all").reset_index(drop=True)

        if block_data.empty:
            continue

        records = _parse_block(block_data, headers, sheet_name)
        all_records.extend(records)

    if not all_records:
        return None

    df = pd.DataFrame(all_records)
    df["Data"] = pd.to_datetime(df["Data"])

    df = (
        df.groupby(["Faccao", "Produto", "Data"], as_index=False)
        .agg({"Quantidade": "sum", "Meta Diaria": "first"})
    )

    df["Ano"]       = df["Data"].dt.year
    df["Mes"]       = df["Data"].dt.month
    df["Mes Nome"]  = df["Mes"].map(MESES_PT)
    df["Dia"]       = df["Data"].dt.day
    df["Semana"]    = df["Data"].dt.isocalendar().week.astype(int)
    df["DiaSemana"] = df["Data"].dt.day_name()

    return df

# ─
# BOTÃO FILTROS (HTML)
# ─
_FILTROS_BTN_HTML = """
<button onclick="
    var doc = window.parent.document;
    var selectors = [
        '[data-testid=stSidebarCollapsedControl] button',
        '[data-testid=stSidebarCollapsedControl]',
        'button[data-testid=stBaseButton-headerNoPadding]',
        '[data-testid=collapsedControl] button'
    ];
    var clicked = false;
    for (var i = 0; i < selectors.length; i++) {
        var el = doc.querySelector(selectors[i]);
        if (el) { el.click(); clicked = true; break; }
    }
    if (!clicked) {
        var btns = doc.querySelectorAll('button');
        for (var j = 0; j < btns.length; j++) {
            var b = btns[j];
            var r = b.getBoundingClientRect();
            if (r.left < 60 && r.top < 60 && r.width < 60 && b.querySelector('svg')) {
                b.click(); break;
            }
        }
    }
" style="
    width:100%;cursor:pointer;text-align:center;
    background:linear-gradient(135deg,#1A1F2E,#252B3B);
    border:1px solid #2D3748;border-radius:10px;
    color:#E2E8F0;padding:8px 16px;
    font-size:0.9rem;font-family:sans-serif;transition:all 0.3s ease;
" onmouseover="this.style.borderColor='#4ECDC4';this.style.color='#4ECDC4';"
   onmouseout="this.style.borderColor='#2D3748';this.style.color='#E2E8F0';">Filtros</button>
"""

# ─
# POR FACÇÃO — única visão de produção do dashboard (Produção por Cliente foi
# descontinuada em 06/07/2026, ver changelog). Alimentada pela linha do tempo
# unificada: planilha antiga até 31/05/2026 + planilha de facções a partir de
# 01/06/2026. Ver utils/producao_unificada.py.
# ─
@st.cache_data(ttl=300, show_spinner=False)
def _load_producao_unificada_cached() -> pd.DataFrame:
    all_data = load_all_data()
    df = load_producao_unificada(all_data)
    if df.empty:
        return df
    df["Ano"] = df["DATA"].dt.year
    df["Mes"] = df["DATA"].dt.month
    df["DiaSemana"] = df["DATA"].dt.day_name()
    df["Semana"] = df["DATA"].dt.isocalendar().week.astype(int)
    return df


def _faccao_sidebar_filtros(df_unif: pd.DataFrame) -> pd.DataFrame:
    """Desenha a sidebar de filtros (Ano/Mês/Dias) das telas de seleção de
    facção e devolve o df já filtrado pelo período. Keys compartilhadas entre a
    home e a tela de quarterizadas (nunca coexistem na mesma renderização), pra
    o filtro persistir ao navegar entre elas."""
    with st.sidebar:
        st.markdown("### Filtros")

        all_anos = sorted(df_unif["Ano"].unique())
        sel_anos = _multiselect_reset_on_grow("Ano", all_anos, "faccao_sel_ano")
        if not sel_anos:
            sel_anos = all_anos

        all_meses = sorted(df_unif[df_unif["Ano"].isin(sel_anos)]["Mes"].unique())
        sel_meses = _multiselect_reset_on_grow(
            "Mês", all_meses, "faccao_sel_mes", format_func=lambda m: MESES_NOME[m]
        )
        if not sel_meses:
            sel_meses = all_meses

        df_periodo = df_unif[df_unif["Ano"].isin(sel_anos) & df_unif["Mes"].isin(sel_meses)]

        st.markdown("### Filtro de Dias")
        modo = st.radio("Tipo de filtro", ["Período", "Um dia"], horizontal=True, key="faccao_sel_modo")

        if not df_periodo.empty:
            d_min = df_periodo["DATA"].min().date()
            d_max = df_periodo["DATA"].max().date()
            if modo == "Um dia":
                dia_sel = st.date_input("Dia", value=d_max, min_value=d_min, max_value=d_max,
                                        format="DD/MM/YYYY", key="faccao_sel_dia")
                df_periodo = df_periodo[df_periodo["DATA"].dt.date == dia_sel]
            else:
                d_ini = st.date_input("Início", value=d_min, min_value=d_min, max_value=d_max,
                                      format="DD/MM/YYYY", key="faccao_sel_ini")
                d_fim = st.date_input("Fim", value=d_max, min_value=d_min, max_value=d_max,
                                      format="DD/MM/YYYY", key="faccao_sel_fim")
                ini, fim = min(d_ini, d_fim), max(d_ini, d_fim)
                df_periodo = df_periodo[df_periodo["DATA"].dt.date.between(ini, fim)]

        if st.button("🔄 Atualizar Dados", use_container_width=True, key="faccao_sel_refresh"):
            from utils.cache_manager import invalidate_all
            invalidate_all()
            st.cache_data.clear()
            st.rerun()

        st.sidebar.divider()
        st.sidebar.caption("Dados atualizados a cada 5 min.")

    return df_periodo


def _faccao_grade_selecao(df_periodo: pd.DataFrame, dim_col: str, on_select, key_ns: str):
    """Gráfico de barras + botões de seleção + evolução mensal + resumo,
    agrupando pela coluna dim_col (GRUPO na home; FACCAO na tela de
    quarterizadas). on_select(nome) é chamado ao clicar num item — normalmente
    seta um query_param e dá rerun. Itens sem produção no período são omitidos."""
    totals = (
        df_periodo.groupby(dim_col, as_index=False)["QUANTIDADE"].sum()
        .query("QUANTIDADE > 0")
        .sort_values("QUANTIDADE", ascending=True)
    )

    col_chart, col_select = st.columns([3, 2])
    with col_chart:
        st.markdown('<p class="section-title">Produção Total</p>', unsafe_allow_html=True)
        fig = px.bar(totals, x="QUANTIDADE", y=dim_col, orientation="h",
                     color=dim_col, color_discrete_map=CORES_FACCAO, text="QUANTIDADE")
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont=dict(color="#CBD5E0"))
        fig.update_layout(showlegend=False, height=max(300, len(totals) * 45),
                          margin=dict(l=0, r=80, t=10, b=0),
                          xaxis_title="Quantidade Produzida", yaxis_title="", **DARK_LAYOUT)
        st.plotly_chart(fig, width="stretch")

    ultima_data = (
        df_periodo[df_periodo["QUANTIDADE"] > 0]
        .groupby(dim_col)["DATA"].max()
    )

    # QUARTERIZADAS sempre primeiro na lista de seleção; o resto em ordem alfabética.
    nomes_ordenados = sorted(
        totals[dim_col], key=lambda n: (n != GRUPO_QUARTERIZADAS, n)
    )

    with col_select:
        st.markdown('<p class="section-title">Selecione</p>', unsafe_allow_html=True)
        for nome in nomes_ordenados:
            total_item = totals.loc[totals[dim_col] == nome, "QUANTIDADE"].values[0]
            sufixo = " ▸" if nome == GRUPO_QUARTERIZADAS else ""
            # No card agregado de QUARTERIZADAS a "última data" não diz muito (mistura todo
            # mundo) — quem quiser saber a data de cada prestador entra e vê lá dentro.
            nota_data = (
                f"  ·  até {ultima_data[nome].strftime('%d/%m')}"
                if nome in ultima_data.index and nome != GRUPO_QUARTERIZADAS
                else ""
            )
            label = f"  {nome}  -  {total_item:,.0f} un.{nota_data}{sufixo}".replace(",", ".")
            if st.button(label, key=f"btn_{key_ns}_{nome}", use_container_width=True):
                on_select(nome)

    st.markdown("---")
    st.markdown('<p class="section-title">Evolução Mensal</p>', unsafe_allow_html=True)
    mensal = df_periodo.groupby(["Ano", "Mes", dim_col], as_index=False)["QUANTIDADE"].sum()
    mensal["Periodo"] = mensal.apply(lambda r: f"{int(r['Ano'])}-{int(r['Mes']):02d}", axis=1)
    fig2 = px.line(mensal, x="Periodo", y="QUANTIDADE", color=dim_col,
                   color_discrete_map=CORES_FACCAO, markers=True)
    fig2.update_layout(height=420, xaxis_title="Período", yaxis_title="Quantidade Produzida",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                       **DARK_LAYOUT)
    st.plotly_chart(fig2, width="stretch")

    st.markdown("---")
    st.markdown('<p class="section-title">Resumo</p>', unsafe_allow_html=True)
    resumo_rows = []
    for nome, grp in df_periodo.groupby(dim_col):
        total = grp["QUANTIDADE"].sum()
        if total <= 0:
            continue
        dias = grp[grp["QUANTIDADE"] > 0]["DATA"].nunique()
        media = total / dias if dias > 0 else 0
        resumo_rows.append({
            dim_col.title(): nome, "Total Produzido": int(total),
            "Dias Trabalhados": dias, "Média Diária": int(media),
            "Clientes": grp["CLIENTE"].nunique(), "Produtos": grp["PRODUTO"].nunique(),
        })
    df_resumo = pd.DataFrame(resumo_rows).sort_values("Total Produzido", ascending=False)
    _fmt_int = lambda v: f"{v:,.0f}".replace(",", ".")
    st.dataframe(df_resumo.style.format({"Total Produzido": _fmt_int, "Média Diária": _fmt_int}),
                 width="stretch", hide_index=True)


def _color_pct_comparacao(val, t_green: float = 100, t_yellow: float = 75) -> str:
    """Colore um valor de % por faixas (usado nas tabelas da aba Comparação)."""
    try:
        v = float(val)
        if pd.isna(v):
            return ""
    except Exception:
        return ""
    if v >= t_green:
        return "color: #4ECDC4; font-weight: bold"
    if v >= t_yellow:
        return "color: #FFA726"
    return "color: #FF6B6B"


def _faccao_tab_comparacao(df_periodo: pd.DataFrame):
    """Comparação completa entre facções e produtos — portado de
    pages/5_Producao_Faccoes.py (abas 'Por Facção' e 'Por Produto'), sem as
    visões mensal/semanal/diária (já cobertas por 'Evolução Mensal' na aba
    Visão Geral). Usa FACCAO (não agrupado em Quarterizadas) — comparação
    granular, cada prestador aparece separado, igual à página original."""
    if df_periodo.empty:
        st.info("Sem dados no período selecionado.")
        return

    sub_fac, sub_prod = st.tabs(["🏭 Por Facção", "📦 Por Produto"])

    # ── Por Facção ───────────────────────────────────────────────────────────
    with sub_fac:
        fac_grp = (
            df_periodo.groupby("FACCAO")["QUANTIDADE"].sum().reset_index()
            .sort_values("QUANTIDADE", ascending=False)
        )
        fac_grp = fac_grp[fac_grp["QUANTIDADE"] > 0]
        if fac_grp.empty:
            st.info("Sem produção no período selecionado.")
        else:
            total_geral_fac = int(fac_grp["QUANTIDADE"].sum())
            n_faccoes = len(fac_grp)
            lider_fac = fac_grp.iloc[0]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Facções Ativas", n_faccoes)
            k2.metric("Total Produzido", fmt_br(total_geral_fac))
            k3.metric("Facção Líder", lider_fac["FACCAO"])
            k4.metric("Participação da Líder", f"{lider_fac['QUANTIDADE'] / total_geral_fac * 100:.1f}%")

            st.divider()
            st.markdown("#### 📊 Visão Geral")
            col_pie, col_bar = st.columns(2)
            with col_pie:
                fig_pie = px.pie(
                    fac_grp, names="FACCAO", values="QUANTIDADE", title="% por Facção",
                    color="FACCAO", color_discrete_map=CORES_FACCAO, hole=0.4,
                )
                fig_pie.update_layout(**DARK_LAYOUT)
                st.plotly_chart(fig_pie, width="stretch")
            with col_bar:
                daily_fac = df_periodo.groupby(["DATA", "FACCAO"])["QUANTIDADE"].sum().reset_index()
                daily_fac["DATA_STR"] = daily_fac["DATA"].dt.strftime("%d/%m")
                fig_stk = px.bar(
                    daily_fac, x="DATA_STR", y="QUANTIDADE", color="FACCAO",
                    color_discrete_map=CORES_FACCAO, title="Produção Diária por Facção",
                    labels={"QUANTIDADE": "Peças", "DATA_STR": "Dia", "FACCAO": "Facção"},
                )
                fig_stk.update_layout(**DARK_LAYOUT)
                st.plotly_chart(fig_stk, width="stretch")

            st.divider()
            st.markdown("#### 🏆 Ranking e Atingimento de Meta")
            data_ini_p = df_periodo["DATA"].min().date()
            data_fim_p = df_periodo["DATA"].max().date()
            try:
                meta_calc = calcular_meta_faccoes(
                    df_periodo[["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"]],
                    data_ini_p.year, data_ini_p.month,
                )
                rank_df = meta_calc["rank_df"]
            except Exception:
                rank_df = pd.DataFrame(columns=["FACCAO", "QUANTIDADE", "META_MES", "META_DIA", "PCT", "RESTANTE"])

            if rank_df.empty:
                st.info("Meta indisponível para o período selecionado.")
            else:
                rank_df = rank_df.copy()
                rank_df["% do Total"] = (rank_df["QUANTIDADE"] / total_geral_fac * 100).round(1)
                rk_todos = rank_df.sort_values("PCT", ascending=True, na_position="last")

                fig_comp = go.Figure()
                fig_comp.add_bar(
                    name="Meta Mês", y=rk_todos["FACCAO"], x=rk_todos["META_MES"], orientation="h",
                    marker_color="rgba(255,107,107,0.35)", marker_line=dict(color="#FF6B6B", width=1),
                    hovertemplate="<b>%{y}</b><br>Meta: %{x:,.0f}<extra></extra>",
                )
                fig_comp.add_bar(
                    name="Produzido", y=rk_todos["FACCAO"], x=rk_todos["QUANTIDADE"], orientation="h",
                    marker_color=[
                        "#4ECDC4" if (pd.notna(p) and p >= 100) else "#FFA726" if (pd.notna(p) and p >= 75) else "#FF6B6B"
                        for p in rk_todos["PCT"]
                    ],
                    text=[f"{p:.0f}%" if pd.notna(p) else "sem meta" for p in rk_todos["PCT"]],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Produzido: %{x:,.0f}<extra></extra>",
                )
                fig_comp.update_layout(
                    barmode="overlay", title="Produzido vs Meta por Facção",
                    xaxis_title="Peças", yaxis_title="",
                    height=max(400, len(rk_todos) * 38 + 120),
                    legend=dict(orientation="h", y=1.08, x=0),
                    **DARK_LAYOUT,
                )
                st.plotly_chart(fig_comp, width="stretch")

                col_rank1, col_rank2 = st.columns(2)
                with col_rank1:
                    rk = rank_df.sort_values("QUANTIDADE", ascending=True)
                    cores_rk = [CORES_FACCAO.get(f, "#4ECDC4") for f in rk["FACCAO"]]
                    fig_rank = go.Figure(go.Bar(
                        y=rk["FACCAO"], x=rk["QUANTIDADE"], orientation="h", marker_color=cores_rk,
                        text=[fmt_br(v) for v in rk["QUANTIDADE"]], textposition="outside",
                        hovertemplate="<b>%{y}</b><br>%{x:,.0f} peças<extra></extra>",
                    ))
                    fig_rank.update_layout(title="Produção Total por Facção", xaxis_title="Peças",
                                           yaxis_title="", **DARK_LAYOUT)
                    st.plotly_chart(fig_rank, width="stretch")

                with col_rank2:
                    rk_meta = rank_df[rank_df["PCT"].notna()].sort_values("PCT", ascending=True)
                    if rk_meta.empty:
                        st.info("Nenhuma facção com meta cadastrada no período.")
                    else:
                        cores_m = rk_meta["PCT"].apply(
                            lambda v: "#4ECDC4" if v >= 100 else "#FFA726" if v >= 75 else "#FF6B6B"
                        )
                        fig_meta = go.Figure(go.Bar(
                            y=rk_meta["FACCAO"], x=rk_meta["PCT"], orientation="h", marker_color=cores_m,
                            text=[f"{p:.0f}%" for p in rk_meta["PCT"]], textposition="outside",
                            hovertemplate="<b>%{y}</b><br>%{x:.1f}% da meta<extra></extra>",
                        ))
                        fig_meta.add_vline(x=100, line_dash="dash", line_color="#FFFFFF",
                                           annotation_text="Meta", annotation_position="top")
                        fig_meta.update_layout(title="% da Meta Mensal por Facção", xaxis_title="% da Meta",
                                               yaxis_title="", **DARK_LAYOUT)
                        st.plotly_chart(fig_meta, width="stretch")

                tab_rank = rank_df[["FACCAO", "QUANTIDADE", "% do Total", "META_MES", "META_DIA", "PCT", "RESTANTE"]].copy()
                tab_rank.columns = ["Facção", "Produzido", "% do Total", "Meta Mês", "Meta/Dia", "% da Meta", "Restante"]
                tab_rank = tab_rank.sort_values("Produzido", ascending=False).reset_index(drop=True)
                tab_rank["Meta Mês"] = tab_rank["Meta Mês"].replace(0.0, None)
                tab_rank["Meta/Dia"] = tab_rank["Meta/Dia"].replace(0.0, None)

                def _safe_fmt(v):
                    try:
                        return fmt_br(v) if v is not None and not pd.isna(v) else "—"
                    except Exception:
                        return "—"

                def _safe_pct(v):
                    try:
                        return f"{float(v):.1f}%" if v is not None and not pd.isna(v) else "—"
                    except Exception:
                        return "—"

                st.dataframe(
                    tab_rank.style
                    .map(_color_pct_comparacao, subset=["% da Meta"])
                    .format({
                        "Produzido":  "{:,.0f}", "% do Total": "{:.1f}%",
                        "Meta Mês":   _safe_fmt, "Meta/Dia":   _safe_fmt,
                        "% da Meta":  _safe_pct, "Restante":   _safe_fmt,
                    }),
                    width="stretch", hide_index=True,
                )

            st.divider()
            st.markdown("#### 📈 Análise de Consistência por Facção")
            st.caption(
                "**Regularidade** mede a uniformidade da produção diária "
                "(100% = produção perfeitamente constante). **Assiduidade** mostra em "
                "quantos dias úteis do período houve produção."
            )
            df_cons = consistencia_por_dimensao(df_periodo, data_ini_p, data_fim_p, dim_col="FACCAO")

            col_cons1, col_cons2 = st.columns(2)
            with col_cons1:
                df_reg = df_cons.sort_values("Regularidade (%)", ascending=True)
                cores_reg = df_reg["Regularidade (%)"].apply(
                    lambda v: "#4ECDC4" if v >= 80 else "#FFA726" if v >= 60 else "#FF6B6B"
                )
                fig_reg = go.Figure(go.Bar(
                    y=df_reg["FACCAO"], x=df_reg["Regularidade (%)"], orientation="h", marker_color=cores_reg,
                    text=[f"{v:.0f}%" for v in df_reg["Regularidade (%)"]], textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Regularidade: %{x:.1f}%<extra></extra>",
                ))
                fig_reg.add_vline(x=80, line_dash="dash", line_color="#4ECDC4",
                                  annotation_text="Boa (80%)", annotation_position="top")
                fig_reg.update_layout(title="Regularidade da Produção", yaxis_title="", **DARK_LAYOUT)
                fig_reg.update_xaxes(range=[0, 120], title_text="Regularidade (%)")
                st.plotly_chart(fig_reg, width="stretch")

            with col_cons2:
                df_ass = df_cons.sort_values("Assiduidade (%)", ascending=True)
                cores_ass = df_ass["Assiduidade (%)"].apply(
                    lambda v: "#4ECDC4" if v >= 80 else "#FFA726" if v >= 50 else "#FF6B6B"
                )
                fig_ass = go.Figure(go.Bar(
                    y=df_ass["FACCAO"], x=df_ass["Assiduidade (%)"], orientation="h", marker_color=cores_ass,
                    text=[f"{v:.0f}%" for v in df_ass["Assiduidade (%)"]], textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Assiduidade: %{x:.1f}%<extra></extra>",
                ))
                fig_ass.add_vline(x=80, line_dash="dash", line_color="#4ECDC4",
                                  annotation_text="Boa (80%)", annotation_position="top")
                fig_ass.update_layout(title="Assiduidade — dias com produção / dias úteis",
                                      yaxis_title="", **DARK_LAYOUT)
                fig_ass.update_xaxes(range=[0, 120], title_text="Assiduidade (%)")
                st.plotly_chart(fig_ass, width="stretch")

            st.dataframe(
                df_cons.sort_values("Regularidade (%)", ascending=False).reset_index(drop=True)
                .style.map(lambda v: _color_pct_comparacao(v, t_green=80, t_yellow=60),
                           subset=["Assiduidade (%)", "Regularidade (%)"])
                .format({
                    "Média/Dia": "{:,.0f}", "Melhor Dia": "{:,.0f}", "Pior Dia (>0)": "{:,.0f}",
                    "Assiduidade (%)": "{:.1f}%", "Regularidade (%)": "{:.1f}%",
                }),
                width="stretch", hide_index=True,
            )

            st.divider()
            st.markdown("#### 🗓 Mapa de Calor — Produção por Facção e Dia")
            st.caption("Cor mais intensa = maior volume. Células em branco = sem produção naquele dia.")
            st.plotly_chart(heatmap_por_dimensao(df_periodo, dim_col="FACCAO", dark_layout=DARK_LAYOUT), width="stretch")

            st.divider()
            st.markdown("#### 📈 Evolução Acumulada e Diária por Facção")
            evol = (
                df_periodo.groupby(["DATA", "FACCAO"])["QUANTIDADE"].sum().reset_index()
                .sort_values(["FACCAO", "DATA"])
            )
            evol["ACUM"] = evol.groupby("FACCAO")["QUANTIDADE"].cumsum()
            evol["DATA_STR"] = evol["DATA"].dt.strftime("%d/%m")
            fig_evol = px.line(
                evol, x="DATA_STR", y="ACUM", color="FACCAO", color_discrete_map=CORES_FACCAO, markers=True,
                labels={"ACUM": "Peças acumuladas", "DATA_STR": "Dia", "FACCAO": "Facção"},
                title="Produção Acumulada por Facção no Período",
            )
            fig_evol.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_evol, width="stretch")

            fig_diario = px.line(
                evol, x="DATA_STR", y="QUANTIDADE", color="FACCAO", color_discrete_map=CORES_FACCAO, markers=True,
                labels={"QUANTIDADE": "Peças no dia", "DATA_STR": "Dia", "FACCAO": "Facção"},
                title="Produção Diária por Facção no Período",
            )
            fig_diario.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_diario, width="stretch")

            st.divider()
            st.markdown("#### 📦 Mix de Produtos por Facção")
            fac_prod = df_periodo.groupby(["FACCAO", "PRODUTO"])["QUANTIDADE"].sum().reset_index()
            fac_prod = fac_prod[fac_prod["QUANTIDADE"] > 0]

            col_mix1, col_mix2 = st.columns(2)
            with col_mix1:
                fig_mix = px.bar(
                    fac_prod, x="FACCAO", y="QUANTIDADE", color="PRODUTO",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    labels={"QUANTIDADE": "Peças", "FACCAO": "Facção", "PRODUTO": "Produto"},
                    title="Composição de Produtos por Facção",
                )
                fig_mix.update_layout(**DARK_LAYOUT)
                fig_mix.update_layout(legend=dict(orientation="h", y=-0.35, x=0.5, xanchor="center"))
                st.plotly_chart(fig_mix, width="stretch")

            with col_mix2:
                piv_pf = fac_prod.pivot_table(index="PRODUTO", columns="FACCAO", values="QUANTIDADE",
                                              aggfunc="sum", fill_value=0)
                z_pf = piv_pf.values.astype(float)
                z_pf_color = np.where(z_pf > 0, np.log1p(z_pf), np.nan)
                text_pf = [[f"{int(v):,}".replace(",", ".") if v > 0 else "" for v in row] for row in z_pf]
                fig_pf = go.Figure(go.Heatmap(
                    z=z_pf_color, x=piv_pf.columns.tolist(), y=piv_pf.index.tolist(),
                    text=text_pf, texttemplate="%{text}", textfont=dict(color="white", size=9),
                    colorscale=[[0, "#3D2817"], [0.5, "#D97706"], [1, "#FBBF24"]], showscale=False,
                    hovertemplate="<b>%{y}</b> → %{x}<br>%{text} peças<extra></extra>",
                ))
                fig_pf.update_layout(
                    title="Produto × Facção (peças)", xaxis_title="Facção", yaxis_title="",
                    height=max(350, len(piv_pf) * 32 + 120), margin=dict(t=50, l=160, r=20, b=80),
                    **DARK_LAYOUT,
                )
                st.plotly_chart(fig_pf, width="stretch")

            st.divider()
            st.markdown("#### 📋 Detalhe por Facção / Produto / Empresa")
            det_fac = (
                df_periodo.groupby(["FACCAO", "PRODUTO", "CLIENTE"])["QUANTIDADE"].sum().reset_index()
                .sort_values(["FACCAO", "QUANTIDADE"], ascending=[True, False])
            )
            det_fac.columns = ["Facção", "Produto", "Empresa", "Produzido"]
            st.dataframe(
                det_fac.style.format({"Produzido": "{:,.0f}"}),
                width="stretch", hide_index=True,
            )

    # ── Por Produto ──────────────────────────────────────────────────────────
    with sub_prod:
        prod_tot = (
            df_periodo.groupby("PRODUTO")["QUANTIDADE"].sum().reset_index()
            .sort_values("QUANTIDADE", ascending=False)
        )
        prod_tot = prod_tot[prod_tot["QUANTIDADE"] > 0]
        if prod_tot.empty:
            st.info("Sem produção no período selecionado.")
        else:
            total_prod = int(prod_tot["QUANTIDADE"].sum())
            lider = prod_tot.iloc[0]

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Produtos diferentes", len(prod_tot))
            with c2:
                st.metric("Produto líder", lider["PRODUTO"].title())
            with c3:
                _share = lider["QUANTIDADE"] / total_prod * 100 if total_prod else 0
                st.metric("Peças do líder", fmt_br(lider["QUANTIDADE"]), delta=f"{_share:.0f}% do total")

            st.divider()
            col_rank, col_mix = st.columns([3, 2])
            with col_rank:
                fig_rank = px.bar(
                    prod_tot.sort_values("QUANTIDADE"), x="QUANTIDADE", y="PRODUTO", orientation="h",
                    text="QUANTIDADE", color="QUANTIDADE", color_continuous_scale="Teal",
                    labels={"QUANTIDADE": "Peças", "PRODUTO": "Produto"}, title="Ranking de Produção por Produto",
                )
                fig_rank.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                fig_rank.update_layout(coloraxis_showscale=False, **DARK_LAYOUT)
                st.plotly_chart(fig_rank, width="stretch")
            with col_mix:
                fig_mix = px.pie(
                    prod_tot, names="PRODUTO", values="QUANTIDADE", hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Set3, title="Mix de Produtos",
                )
                fig_mix.update_traces(textposition="inside", textinfo="percent")
                fig_mix.update_layout(**DARK_LAYOUT)
                st.plotly_chart(fig_mix, width="stretch")

            st.divider()
            tree = df_periodo.groupby(["PRODUTO", "CLIENTE"])["QUANTIDADE"].sum().reset_index()
            tree = tree[tree["QUANTIDADE"] > 0]
            fig_tree = px.treemap(
                tree, path=[px.Constant("Todos"), "PRODUTO", "CLIENTE"], values="QUANTIDADE",
                color="QUANTIDADE", color_continuous_scale="Teal", title="Composição: Produto → Empresa",
            )
            fig_tree.update_traces(
                texttemplate="%{label}<br>%{value:,.0f}",
                hovertemplate="%{label}<br><b>%{value:,.0f}</b> peças<extra></extra>",
            )
            fig_tree.update_layout(margin=dict(t=50, l=10, r=10, b=10), **DARK_LAYOUT)
            st.plotly_chart(fig_tree, width="stretch")

            st.divider()
            pivot = tree.groupby(["PRODUTO", "CLIENTE"])["QUANTIDADE"].sum().unstack(fill_value=0)
            pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
            pivot = pivot.sort_index(axis=1)
            z_raw = pivot.values.astype(float)
            z_color = np.where(z_raw > 0, np.log1p(z_raw), np.nan)
            text_arr = [[f"{int(v):,}".replace(",", ".") if v > 0 else "" for v in row] for row in z_raw]
            n_rows = len(pivot)
            fig_heat = go.Figure(go.Heatmap(
                z=z_color, x=pivot.columns.tolist(), y=pivot.index.tolist(),
                text=text_arr, texttemplate="%{text}", textfont=dict(color="white", size=13),
                colorscale=[[0, "#1a4a8a"], [0.5, "#1976d2"], [1.0, "#64b5f6"]], showscale=False,
                hovertemplate="<b>%{y}</b><br>%{x}: %{text} peças<extra></extra>",
            ))
            fig_heat.update_layout(
                title="Produção por Produto e Empresa", xaxis_title="Empresa", yaxis_title="",
                height=max(420, n_rows * 40 + 120), margin=dict(t=60, l=180, r=20, b=60), **DARK_LAYOUT,
            )
            st.plotly_chart(fig_heat, width="stretch")

            st.divider()
            top_n = prod_tot.head(6)["PRODUTO"].tolist()
            evol_p = (
                df_periodo[df_periodo["PRODUTO"].isin(top_n)]
                .groupby(["DATA", "PRODUTO"])["QUANTIDADE"].sum().reset_index()
            )
            fig_evol_p = px.line(
                evol_p, x="DATA", y="QUANTIDADE", color="PRODUTO", markers=True,
                color_discrete_sequence=px.colors.qualitative.Bold,
                labels={"QUANTIDADE": "Peças", "DATA": "Data", "PRODUTO": "Produto"},
                title=f"Evolução Diária — Top {len(top_n)} Produtos",
            )
            fig_evol_p.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_evol_p, width="stretch")


def render_faccao_home(df_unif: pd.DataFrame):
    df_periodo = _faccao_sidebar_filtros(df_unif)

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        components.html(_FILTROS_BTN_HTML, height=45)
    st.markdown('<p class="main-title">🏭 Dashboard de Produção — Todas as Facções</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Facções fixas e Quarterizadas (agrupadas)</p>', unsafe_allow_html=True)
    st.markdown("---")

    if df_periodo.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    tab_geral, tab_comparacao = st.tabs(["Visão Geral", "📊 Comparação — Facção e Produto"])

    with tab_geral:
        # Agrupa: cada facção fixa é seu próprio item; todos os prestadores
        # individuais entram sob o item único QUARTERIZADAS (clicável → lista deles).
        df_grupo = df_periodo.copy()
        df_grupo["GRUPO"] = df_grupo["FACCAO"].map(grupo_de)

        def _select(nome: str):
            if nome == GRUPO_QUARTERIZADAS:
                st.query_params["grupo"] = GRUPO_QUARTERIZADAS
            else:
                st.query_params["faccao"] = nome
            st.rerun()

        _faccao_grade_selecao(df_grupo, "GRUPO", _select, key_ns="grupo")

    with tab_comparacao:
        _faccao_tab_comparacao(df_periodo)


def render_faccao_quarterizadas(df_unif: pd.DataFrame):
    df_periodo = _faccao_sidebar_filtros(df_unif)
    df_periodo = df_periodo[df_periodo["FACCAO"].map(is_quarterizada)]

    col_btn, col_back = st.columns([1, 2])
    with col_btn:
        components.html(_FILTROS_BTN_HTML, height=45)
    with col_back:
        if st.button("< Voltar para Todas as Facções", key="quart_voltar"):
            st.query_params.pop("grupo", None)
            st.rerun()
    st.markdown('<p class="main-title">🏭 Quarterizadas — Prestadores</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Selecione um prestador para ver o detalhe</p>', unsafe_allow_html=True)
    st.markdown("---")

    if df_periodo.empty:
        st.warning("Nenhuma quarterizada com produção no período selecionado.")
        return

    def _select(nome: str):
        st.query_params["faccao"] = nome
        st.rerun()

    _faccao_grade_selecao(df_periodo, "FACCAO", _select, key_ns="prest")


def render_faccao_drilldown(faccao: str, df_unif: pd.DataFrame):
    cor = CORES_FACCAO.get(faccao, "#1E3A5F")
    df = df_unif[df_unif["FACCAO"] == faccao]

    # Chaves de widget incluem a facção — sem isso, trocar de facção na mesma
    # sessão faz o filtro de Ano/Mês/Cliente/Produto de uma facção "vazar" pra
    # outra (Streamlit mantém o valor do widget pela key, ignorando o novo
    # default assim que a key já foi vista antes).
    _kp = lambda sufixo: f"faccao_dd_{sufixo}__{faccao}"

    _rotulo_voltar = "< Voltar para Quarterizadas" if is_quarterizada(faccao) else "< Voltar para Visão Geral"
    with st.sidebar:
        if st.button(_rotulo_voltar, use_container_width=True, key="faccao_dd_voltar"):
            st.query_params.pop("faccao", None)
            if is_quarterizada(faccao):
                st.query_params["grupo"] = GRUPO_QUARTERIZADAS
            st.rerun()

        st.markdown("---")
        st.markdown(f"### {faccao}")
        st.sidebar.markdown("### Filtros")

        anos = sorted(df["Ano"].unique())
        sel_anos = _multiselect_reset_on_grow("Ano", anos, _kp("ano"))
        if not sel_anos:
            sel_anos = anos

        meses_disp = sorted(df[df["Ano"].isin(sel_anos)]["Mes"].unique())
        sel_meses = _multiselect_reset_on_grow("Mês", meses_disp, _kp("mes"),
                                               format_func=lambda m: MESES_NOME[m])
        if not sel_meses:
            sel_meses = meses_disp

        df_f = df[(df["Ano"].isin(sel_anos)) & (df["Mes"].isin(sel_meses))]

        st.markdown("### Filtro de Dias")
        modo = st.radio("Tipo de filtro", ["Período", "Um dia"], horizontal=True, key=_kp("modo"))

        if not df_f.empty:
            d_min = df_f["DATA"].min().date()
            d_max = df_f["DATA"].max().date()
            if modo == "Um dia":
                dia_sel = st.date_input("Dia", value=d_max, min_value=d_min, max_value=d_max,
                                        format="DD/MM/YYYY", key=_kp("dia"))
                df_f = df_f[df_f["DATA"].dt.date == dia_sel]
            else:
                d_ini = st.date_input("Início", value=d_min, min_value=d_min, max_value=d_max,
                                      format="DD/MM/YYYY", key=_kp("ini"))
                d_fim = st.date_input("Fim", value=d_max, min_value=d_min, max_value=d_max,
                                      format="DD/MM/YYYY", key=_kp("fim"))
                ini, fim = min(d_ini, d_fim), max(d_ini, d_fim)
                df_f = df_f[df_f["DATA"].dt.date.between(ini, fim)]

        clientes = sorted(df_f["CLIENTE"].unique()) if not df_f.empty else []
        sel_clientes = _multiselect_reset_on_grow("Cliente", clientes, _kp("cliente"))
        if not sel_clientes:
            sel_clientes = clientes

        produtos = (
            sorted(df_f[df_f["CLIENTE"].isin(sel_clientes)]["PRODUTO"].unique())
            if not df_f.empty else []
        )
        sel_produtos = _multiselect_reset_on_grow("Produto", produtos, _kp("produto"))
        if not sel_produtos:
            sel_produtos = produtos

        if st.button("🔄 Atualizar Dados", use_container_width=True, key="faccao_dd_refresh"):
            from utils.cache_manager import invalidate_all
            invalidate_all()
            st.cache_data.clear()
            st.rerun()

        st.sidebar.divider()
        st.sidebar.caption("Dados atualizados a cada 5 min.")

    df_f = df_f[df_f["CLIENTE"].isin(sel_clientes) & df_f["PRODUTO"].isin(sel_produtos)]

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        components.html(_FILTROS_BTN_HTML, height=45)
    st.markdown(f'<p class="main-title">🏭 Dashboard de Produção Diária — {faccao.upper()}</p>', unsafe_allow_html=True)
    st.markdown("---")

    if df_f.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    prod_total = df_f["QUANTIDADE"].sum()
    d_uteis = calcular_dias_com_sabados_trabalhados(df_f["DATA"])
    media_dia = prod_total / d_uteis if d_uteis else 0

    ano_meta = int(sel_anos[0]) if sel_anos else date.today().year
    mes_meta = int(sel_meses[0]) if sel_meses else date.today().month
    meta_calc = _calcular_meta_faccao_periodo(df_f, faccao, ano_meta, mes_meta)
    meta_periodo = meta_calc["meta_periodo"]
    tem_meta = meta_periodo > 0
    saldo = prod_total - meta_periodo if tem_meta else 0
    ating = (prod_total / meta_periodo) if (tem_meta and meta_periodo > 0) else 0

    meses_selecionados = len({(a, m) for a in sel_anos for m in sel_meses})
    if meses_selecionados > 1:
        st.caption(
            "ℹ️ A meta da fatia mais recente (planilha de facções) é um valor constante "
            "por período — a precisão cai quanto mais meses o filtro selecionado cobrir."
        )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Produzido", fmt_br(prod_total))
    k2.metric("Meta do Período", fmt_br(meta_periodo) if tem_meta else "Sem meta")
    k3.metric("Saldo", fmt_br(saldo) if tem_meta else "-",
              delta=fmt_br(saldo) if tem_meta else None,
              delta_color="normal" if tem_meta else "off")
    k4.metric("Atingimento", f"{ating*100:.1f}%" if tem_meta else "-",
              delta=f"{(ating-1)*100:+.1f} pp" if tem_meta else None)
    k5.metric("Média / Dia", fmt_br(media_dia))
    k6.metric("Dias Úteis", str(d_uteis))

    if not tem_meta:
        st.info("Esta facção ainda não possui meta cadastrada para o período selecionado.")

    st.markdown("")

    tab_vis, tab_cli, tab_rank, tab_dados = st.tabs(
        ["Visão Geral", "Por Cliente", "Ranking & Alertas", "Dados"]
    )

    with tab_vis:
        serie = df_f.groupby("DATA", as_index=False)["QUANTIDADE"].sum().sort_values("DATA")
        meta_dia_medio = (meta_periodo / d_uteis) if (tem_meta and d_uteis) else 0
        serie["Acum. Produzido"] = serie["QUANTIDADE"].cumsum()
        serie["_feriado"] = serie["DATA"].dt.date.map(eh_feriado)
        serie["_dia_util"] = serie["DATA"].dt.date.map(eh_dia_util)
        serie["Acum. Meta"] = serie["_dia_util"].cumsum() * meta_dia_medio

        # Barra de feriado ganha cor própria (âmbar) em vez de vermelho/verde —
        # produção baixa num feriado (só parte da equipe trabalha) não é falha
        # de meta, e sem essa marcação isso ficava invisível no gráfico
        # (feedback do usuário 10/07/2026, feriado de 09/07 em SP).
        cores_barras = (
            [
                "#f59e0b" if feriado else ("#22c55e" if q >= meta_dia_medio else "#ef4444")
                for q, feriado in zip(serie["QUANTIDADE"], serie["_feriado"])
            ]
            if tem_meta else
            ["#f59e0b" if feriado else cor for feriado in serie["_feriado"]]
        )
        hover_texto = [
            f"{d.strftime('%d/%m/%Y')}<br>{q:,.0f} peças<br>🎉 Feriado: {nome_feriado(d.date())}".replace(",", ".")
            if feriado else f"{d.strftime('%d/%m/%Y')}<br>{q:,.0f} peças".replace(",", ".")
            for d, q, feriado in zip(serie["DATA"], serie["QUANTIDADE"], serie["_feriado"])
        ]

        fig1 = go.Figure()
        fig1.add_bar(x=serie["DATA"], y=serie["QUANTIDADE"], name="Produzido", marker_color=cores_barras,
                     text=hover_texto, hovertemplate="%{text}<extra></extra>")
        if tem_meta:
            fig1.add_scatter(x=serie["DATA"], y=[meta_dia_medio] * len(serie), mode="lines",
                             name="Meta Diária (média)", line=dict(color="#facc15", width=2, dash="dash"))
        fig1.update_layout(title="Produção Diária x Meta", xaxis_title="Data", yaxis_title="Peças",
                           template="plotly_dark", separators=",.",
                           xaxis=dict(tickformat="%d/%m/%Y"),
                           legend=dict(orientation="h", y=-0.15), margin=dict(t=50, b=60))
        st.plotly_chart(fig1, width="stretch")

        _feriados_periodo = feriados_no_periodo(
            df_f["DATA"].min().date(), df_f["DATA"].max().date()
        ) if not df_f.empty else []
        if _feriados_periodo:
            st.caption(
                "🎉 Feriados no período: " + ", ".join(
                    f"{d.strftime('%d/%m')} ({nome})" for d, nome in _feriados_periodo
                )
            )

        col_a, col_b = st.columns(2)
        with col_a:
            fig_acum = go.Figure()
            fig_acum.add_scatter(x=serie["DATA"], y=serie["Acum. Produzido"],
                                 mode="lines+markers", name="Produzido Acumulado",
                                 line=dict(color="#3b82f6", width=3))
            if tem_meta:
                fig_acum.add_scatter(x=serie["DATA"], y=serie["Acum. Meta"],
                                     mode="lines", name="Meta Acumulada",
                                     line=dict(color="#facc15", width=2, dash="dot"))
            fig_acum.update_layout(title="Acumulado: Produção x Meta", template="plotly_dark",
                                   separators=",.", xaxis=dict(tickformat="%d/%m/%Y"),
                                   legend=dict(orientation="h", y=-0.18), margin=dict(t=50, b=60))
            st.plotly_chart(fig_acum, width="stretch")

        with col_b:
            dia_df = df_f.groupby(["DATA", "DiaSemana"], as_index=False)["QUANTIDADE"].sum()
            dia_df["DiaSemana"] = pd.Categorical(dia_df["DiaSemana"], categories=ORDEM_DIAS, ordered=True)
            dia_df = dia_df.dropna(subset=["DiaSemana"]).sort_values("DiaSemana")
            dia_df["Dia"] = dia_df["DiaSemana"].map(NOMES_DIAS)
            fig_box = px.box(dia_df, x="Dia", y="QUANTIDADE", color="Dia",
                             title="Distribuição por Dia da Semana", template="plotly_dark")
            fig_box.update_layout(showlegend=False, separators=",.", margin=dict(t=50, b=40))
            st.plotly_chart(fig_box, width="stretch")

        mensal = df_f.groupby(["Ano", "Mes"], as_index=False)["QUANTIDADE"].sum()
        mensal["MesNome"] = mensal["Mes"].map(MESES_NOME)
        mensal["Ano"] = mensal["Ano"].astype(str)
        fig_mes = px.bar(mensal, x="MesNome", y="QUANTIDADE", color="Ano", barmode="group",
                         text_auto=True, title="Produção Mensal", template="plotly_dark")
        fig_mes.update_layout(xaxis_title="Mês", yaxis_title="Peças",
                              separators=",.", margin=dict(t=50, b=40))
        st.plotly_chart(fig_mes, width="stretch")

    with tab_cli:
        if tem_meta:
            st.markdown("### 🎯 Produzido x Meta — Total do Período")
            fig_meta_total = go.Figure()
            fig_meta_total.add_bar(
                y=["Total"], x=[prod_total], name="Produzido", orientation="h",
                marker_color=cor, text=[fmt_br(prod_total)], textposition="auto",
            )
            fig_meta_total.add_bar(
                y=["Total"], x=[meta_periodo], name="Meta", orientation="h",
                marker_color="#facc15", text=[fmt_br(meta_periodo)], textposition="auto",
            )
            fig_meta_total.update_layout(
                barmode="group", template="plotly_dark", height=160,
                xaxis_title="Peças", separators=",.",
                margin=dict(t=10, b=40), legend=dict(orientation="h", y=-0.3),
            )
            st.plotly_chart(fig_meta_total, width="stretch")
            st.markdown("---")

        tbl = df_f.groupby(["CLIENTE", "PRODUTO"], as_index=False).agg(Produzido=("QUANTIDADE", "sum"))
        tbl = tbl[tbl["Produzido"] > 0].sort_values(["CLIENTE", "PRODUTO"])

        st.markdown("### Resumo por Cliente / Produto")
        _fmt_int = lambda v: f"{v:,.0f}".replace(",", ".")
        st.dataframe(
            tbl.rename(columns={"CLIENTE": "Cliente", "PRODUTO": "Produto"}).style.format({"Produzido": _fmt_int}),
            width="stretch", hide_index=True,
        )

        st.markdown("### Evolução Diária por Produto")
        prod_prod = df_f.groupby(["DATA", "PRODUTO"], as_index=False)["QUANTIDADE"].sum().sort_values("DATA")
        fig_linhas = px.line(prod_prod, x="DATA", y="QUANTIDADE", color="PRODUTO", markers=True,
                             template="plotly_dark")
        fig_linhas.update_layout(title="Evolução Diária por Produto", xaxis_title="Data", yaxis_title="Peças",
                                 xaxis=dict(tickformat="%d/%m/%Y"),
                                 yaxis=dict(rangemode="tozero"),
                                 legend=dict(orientation="h", y=-0.2), margin=dict(t=50, b=60),
                                 separators=",.")
        st.plotly_chart(fig_linhas, width="stretch")

    with tab_rank:
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("### Top 5 Dias Mais Produtivos")
            top5 = df_f.groupby("DATA", as_index=False)["QUANTIDADE"].sum().nlargest(5, "QUANTIDADE")
            top5["DataFmt"] = top5["DATA"].dt.strftime("%d/%m/%Y")
            for i, row in enumerate(top5.itertuples(), 1):
                medal = ["1.", "2.", "3."][i - 1] if i <= 3 else f"  {i}."
                st.markdown(f"**{medal} {row.DataFmt}** - {fmt_br(row.QUANTIDADE)} peças")

        with col_r2:
            st.markdown("### Top 5 Dias Menos Produtivos")
            bot5 = df_f.groupby("DATA", as_index=False)["QUANTIDADE"].sum().nsmallest(5, "QUANTIDADE")
            bot5["DataFmt"] = bot5["DATA"].dt.strftime("%d/%m/%Y")
            for i, row in enumerate(bot5.itertuples(), 1):
                st.markdown(f"**{i}. {row.DataFmt}** - {fmt_br(row.QUANTIDADE)} peças")

        st.markdown("---")
        st.markdown("### Heatmap - Produção Semanal por Cliente")
        heat = df_f.pivot_table(index="CLIENTE", columns="Semana", values="QUANTIDADE", aggfunc="sum").fillna(0)
        fig_heat = px.imshow(heat, aspect="auto", color_continuous_scale="YlGn",
                             labels=dict(x="Semana", y="Cliente", color="Peças"), template="plotly_dark")
        fig_heat.update_layout(separators=",.", margin=dict(t=20, b=40))
        st.plotly_chart(fig_heat, width="stretch")

    with tab_dados:
        st.markdown("### Base Filtrada")
        df_view = df_f[["DATA", "CLIENTE", "PRODUTO", "QUANTIDADE"]].copy()
        df_view = df_view.sort_values(["DATA", "CLIENTE"], ascending=[False, True])
        df_view["DATA"] = df_view["DATA"].dt.strftime("%d/%m/%Y")
        df_view = df_view.rename(
            columns={"DATA": "Data", "CLIENTE": "Cliente", "PRODUTO": "Produto", "QUANTIDADE": "Quantidade"}
        )
        _fmt_int = lambda v: f"{v:,.0f}".replace(",", ".") if pd.notna(v) else "-"
        st.dataframe(
            df_view.reset_index(drop=True).style.format({"Quantidade": _fmt_int}),
            width="stretch", height=500,
        )
        csv = df_f.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar CSV filtrado", csv,
            file_name=f"producao_faccao_{faccao.lower().replace(' ', '_')}_filtrada.csv",
            mime="text/csv",
            key="faccao_dd_download",
        )


def render_por_faccao():
    with st.spinner("Carregando dados de produção…"):
        df_unif = _load_producao_unificada_cached()

    if df_unif.empty:
        st.error("Não foi possível carregar os dados de produção (planilha antiga + planilha de facções).")
        return

    faccao = st.query_params.get("faccao", None)
    grupo = st.query_params.get("grupo", None)
    if faccao and faccao in df_unif["FACCAO"].unique():
        render_faccao_drilldown(faccao, df_unif)
    elif grupo == GRUPO_QUARTERIZADAS:
        render_faccao_quarterizadas(df_unif)
    else:
        render_faccao_home(df_unif)


# ─
# HUB — navegação por telas (mesmo estilo do Controle de Corte)
# ─
def _go_prod(screen: str):
    st.session_state.producao_screen = screen
    st.rerun()

def _sidebar_nav_producao(screen: str):
    with st.sidebar:
        st.markdown("### 🏭 Análise de Produção")
        st.markdown("---")
        if st.button("🏢  Início", key="prod_sb_home", use_container_width=True):
            st.session_state.producao_screen = 'analysis_type'
            st.switch_page("app.py")
        if screen == 'por_faccao':
            if st.button("← Tipo de Análise", key="prod_sb_back_facc2", use_container_width=True):
                _go_prod('analysis_type')
        elif screen == 'relatorio_semanal':
            if st.button("← Tipo de Análise", key="prod_sb_back_rel2", use_container_width=True):
                _go_prod('analysis_type')
        elif screen == 'colaborador_type':
            if st.button("← Tipo de Análise", key="prod_sb_back_colab", use_container_width=True):
                _go_prod('analysis_type')
        elif screen == 'interno':
            if st.button("← Por Colaborador", key="prod_sb_back_intext", use_container_width=True):
                _go_prod('colaborador_type')
            if st.button("← Tipo de Análise", key="prod_sb_back2", use_container_width=True):
                _go_prod('analysis_type')

def _screen_analysis_type():
    st.markdown("""
    <div class="page-header">
        <div class="page-badge">🏭 Análise de Produção</div>
        <h1 class="page-title">Selecione o Tipo de <span class="accent">Análise</span></h1>
        <p class="page-subtitle">Escolha como deseja analisar a produção</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    _, c1, c2, _ = st.columns([0.5, 3, 3, 0.5])
    with c1:
        st.markdown("""
        <div class="region-card" style="--rc-a:#0F4C5C; --rc-b:#4ECDC4; --rc-accent:#4ECDC4;">
            <div class="rc-icon">🏢</div>
            <div class="rc-label">Análise · Geral</div>
            <div class="rc-title">Por Cliente</div>
            <div class="rc-desc">
                Produção diária por facção e por cliente, com metas ponderadas,
                evolução e ranking — visão multi-empresa e multi-facção.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Multi-empresa</span>
                <span class="rc-tag">Metas</span>
                <span class="rc-tag">Evolução</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_por_cliente", use_container_width=True):
            _go_prod('por_faccao')

    with c2:
        st.markdown("""
        <div class="region-card" style="--rc-a:#1A3A5C; --rc-b:#45B7D1; --rc-accent:#45B7D1;">
            <div class="rc-icon">👥</div>
            <div class="rc-label">Análise · Geral</div>
            <div class="rc-title">Por Colaborador</div>
            <div class="rc-desc">
                Produção por colaborador, com análise de ranking, consistência
                e desempenho — dividido entre internos e externos.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Interno</span>
                <span class="rc-tag">Externo</span>
                <span class="rc-tag">Consistência</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_por_colaborador", use_container_width=True):
            _go_prod('colaborador_type')

    st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("🏢 Voltar ao Início", key="prod_back_home", use_container_width=True):
            st.session_state.producao_screen = 'analysis_type'
            st.switch_page("app.py")

_GUT_APONTADOR_URL = "https://www.appsheet.com/start/bcbb42c8-42a6-4424-8cb2-c11a69052d89"
_GUT_ANALISE_URL = (
    "https://datastudio.google.com/u/0/reporting/"
    "720db0c0-be65-40d9-ae9d-7627741385ce/page/p_si214uowdd"
)

def _screen_colaborador_type():
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Análise de Produção</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Por Colaborador</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-top:18px;">
        <div class="page-badge">👥 Por Colaborador</div>
        <h1 class="page-title">Colaboradores e <span class="accent">GUT</span></h1>
        <p class="page-subtitle">Escolha o painel de colaboradores ou acesse o sistema GUT</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    _, c1, c2, c3, _ = st.columns([0.25, 3, 3, 3, 0.25])
    with c1:
        st.markdown("""
        <div class="region-card" style="--rc-a:#1A3A2A; --rc-b:#2A9D5C; --rc-accent:#2A9D5C;">
            <div class="rc-icon">🏠</div>
            <div class="rc-label">Colaboradores · Internos</div>
            <div class="rc-title">Interno</div>
            <div class="rc-desc">
                Produção dos colaboradores internos por unidade, em guias:
                LITTEX, GGTTEX Jogos, GGTTEX Fronha e GGTTEX Cortina.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">LITTEX</span>
                <span class="rc-tag">GGTTEX</span>
                <span class="rc-tag">4 unidades</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Interno  →", key="btn_interno", use_container_width=True):
            _go_prod('interno')

    with c2:
        st.markdown("""
        <div class="region-card" style="--rc-a:#1F4A5A; --rc-b:#2E8B9E; --rc-accent:#26D0CE;">
            <div class="rc-icon">⏱️</div>
            <div class="rc-label">Apontador Zanattex · GUT</div>
            <div class="rc-title">Central de Controle GUT</div>
            <div class="rc-desc">
                Painel de acompanhamento em tempo real do GUT (Giattex) com dados de
                eficiência, horas, operadores e performance.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">GUT</span>
                <span class="rc-tag">Eficiência</span>
                <span class="rc-tag">Real-time</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Abrir Central GUT  →", url=_GUT_APONTADOR_URL, use_container_width=True)

    with c3:
        st.markdown("""
        <div class="region-card" style="--rc-a:#3D2817; --rc-b:#D97706; --rc-accent:#FBBF24;">
            <div class="rc-icon">📈</div>
            <div class="rc-label">Dashboard Analítico · GUT</div>
            <div class="rc-title">Análise de Dados GUT</div>
            <div class="rc-desc">
                Análise completa dos dados do GUT em formato de dashboard interativo.
                Visualize tendências, indicadores de desempenho e insights estratégicos.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Análise</span>
                <span class="rc-tag">GUT</span>
                <span class="rc-tag">Insights</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Abrir Análise GUT  →", url=_GUT_ANALISE_URL, use_container_width=True)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("← Voltar ao Tipo de Análise", key="prod_back_type_colab", use_container_width=True):
            _go_prod('analysis_type')

# ─
# INTERNO — dashboard com 4 guias (uma por unidade)
# ─
def _consistencia_colaboradores(base: pd.DataFrame, selecionados: list, dias_unidade: int) -> pd.DataFrame:
    """
    Por colaborador selecionado, calcula:
      - Regularidade = 100*(1 - CV) da produção diária (CV = desvio/média), clamp 0–100.
      - Assiduidade  = 100 * dias_com_produção / dias_úteis_observados na unidade.
    Retorna DataFrame longo [COLABORADOR, METRICA, VALOR].
    """
    linhas = []
    for nome in selecionados:
        sub = base[base["COLABORADOR"] == nome]
        diario = sub.groupby(sub["DATA"].dt.date)["QUANTIDADE"].sum()
        dias_ativos = int(diario.shape[0])
        assiduidade = (100.0 * dias_ativos / dias_unidade) if dias_unidade else 0.0
        if dias_ativos >= 2 and diario.mean() > 0:
            cv = diario.std(ddof=0) / diario.mean()
            regularidade = max(0.0, min(100.0, 100.0 * (1.0 - cv)))
        else:
            regularidade = 100.0 if dias_ativos >= 1 else 0.0
        linhas.append({"COLABORADOR": nome, "METRICA": "Regularidade", "VALOR": round(regularidade, 1)})
        linhas.append({"COLABORADOR": nome, "METRICA": "Assiduidade",  "VALOR": round(min(assiduidade, 100.0), 1)})
    return pd.DataFrame(linhas)

def _render_interno_tab(chave: str, cfg: dict):
    with st.spinner(f"Carregando dados de {cfg['label']}…"):
        df = load_interno_unidade(chave)
    if df.empty:
        st.warning(f"⚠️ Sem dados disponíveis para {cfg['label']}.")
        return

    dmin, dmax = df["DATA"].min().date(), df["DATA"].max().date()

    # ── Filtros ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        ini = st.date_input("De", value=dmin, min_value=dmin, max_value=dmax,
                            format="DD/MM/YYYY", key=f"ini_{chave}")
    with c2:
        fim = st.date_input("Até", value=dmax, min_value=dmin, max_value=dmax,
                            format="DD/MM/YYYY", key=f"fim_{chave}")
    colabs_all = sorted(df["COLABORADOR"].unique())
    with c3:
        sel = st.multiselect("Colaborador(es)", colabs_all, key=f"colab_{chave}",
                             placeholder="Todos (ranking)")

    if ini > fim:
        st.error("A data inicial não pode ser maior que a final.")
        return

    mask = (df["DATA"].dt.date >= ini) & (df["DATA"].dt.date <= fim)
    dff = df[mask].copy()
    if dff.empty:
        st.info("Nenhum registro no período selecionado.")
        return

    # ── KPIs ────────────────────────────────────────────────────────────────────
    total = int(dff["QUANTIDADE"].sum())
    n_colab = dff["COLABORADOR"].nunique()
    dias_unidade = dff["DATA"].dt.date.nunique()
    media_dia = total / dias_unidade if dias_unidade else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Produzido", f"{total:,.0f}".replace(",", "."))
    k2.metric("Colaboradores", f"{n_colab}")
    k3.metric("Dias com Produção", f"{dias_unidade}")
    k4.metric("Média / Dia", f"{media_dia:,.0f}".replace(",", "."))

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Gráfico principal dinâmico ───────────────────────────────────────────────
    if not sel:
        st.markdown('<p class="section-title">🏆 Top Colaboradores</p>', unsafe_allow_html=True)
        top = (dff.groupby("COLABORADOR")["QUANTIDADE"].sum()
               .sort_values(ascending=True).tail(15).reset_index())
        fig = px.bar(top, x="QUANTIDADE", y="COLABORADOR", orientation="h",
                     text="QUANTIDADE", color="QUANTIDADE", color_continuous_scale="Teal")
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                          textfont=dict(color="#CBD5E0"))
        fig.update_layout(height=max(320, len(top) * 36), showlegend=False,
                          coloraxis_showscale=False, margin=dict(l=0, r=70, t=10, b=0),
                          xaxis_title="Quantidade", yaxis_title="", **DARK_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    else:
        base = dff[dff["COLABORADOR"].isin(sel)].copy()
        # 1) Quantidade por dia
        st.markdown('<p class="section-title">📈 Quantidade por Dia</p>', unsafe_allow_html=True)
        diario = (base.groupby([base["DATA"].dt.date, "COLABORADOR"])["QUANTIDADE"]
                  .sum().reset_index())
        diario.columns = ["DATA", "COLABORADOR", "QUANTIDADE"]
        fig_dia = px.line(diario, x="DATA", y="QUANTIDADE", color="COLABORADOR", markers=True)
        fig_dia.update_layout(height=380, xaxis_title="Dia", yaxis_title="Quantidade",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                          xanchor="right", x=1), **DARK_LAYOUT)
        st.plotly_chart(fig_dia, use_container_width=True)

        # 2) Consistência (Regularidade + Assiduidade)
        st.markdown('<p class="section-title">🎯 Consistência por Colaborador</p>',
                    unsafe_allow_html=True)
        st.caption("Regularidade = estabilidade da produção diária · "
                   "Assiduidade = % de dias com produção no período.")
        cons = _consistencia_colaboradores(base, sel, dias_unidade)
        fig_cons = px.bar(cons, x="COLABORADOR", y="VALOR", color="METRICA",
                          barmode="group", text="VALOR", range_y=[0, 105],
                          color_discrete_map={"Regularidade": "#4ECDC4", "Assiduidade": "#FFA726"})
        fig_cons.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
        fig_cons.update_layout(height=360, xaxis_title="", yaxis_title="%",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                           xanchor="right", x=1), **DARK_LAYOUT)
        st.plotly_chart(fig_cons, use_container_width=True)

    escopo = dff[dff["COLABORADOR"].isin(sel)] if sel else dff

    # ── Análise por Setor (apenas se a unidade tiver setor preenchido) ───────────
    if "SETOR" in dff.columns and escopo["SETOR"].astype(str).str.strip().ne("").any():
        setor = escopo[escopo["SETOR"].astype(str).str.strip() != ""]
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">🏭 Produção por Setor</p>', unsafe_allow_html=True)
        aggs = (setor.groupby("SETOR")["QUANTIDADE"].sum()
                .sort_values(ascending=True).reset_index())
        fig_s = px.bar(aggs, x="QUANTIDADE", y="SETOR", orientation="h",
                       text="QUANTIDADE", color="QUANTIDADE", color_continuous_scale="Teal")
        fig_s.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                            textfont=dict(color="#CBD5E0"))
        fig_s.update_layout(height=max(260, len(aggs) * 36), showlegend=False,
                            coloraxis_showscale=False, margin=dict(l=0, r=70, t=10, b=0),
                            xaxis_title="Quantidade", yaxis_title="", **DARK_LAYOUT)
        st.plotly_chart(fig_s, use_container_width=True)

        # ── Setor como Função: Mix Setor × Colaborador ───────────────────────────
        # Só quando a unidade NÃO tem coluna de função dedicada (ex.: Littex) e há
        # mais de um setor — aqui o SETOR faz o papel de "função" do colaborador.
        if "FUNCAO" not in dff.columns and setor["SETOR"].nunique() >= 2:
            st.markdown('<p class="section-title">🧩 Mix Setor × Colaborador</p>',
                        unsafe_allow_html=True)
            st.caption("Cada colaborador e os setores em que atuou no período "
                       "(o setor funciona como a função da pessoa).")
            colabs_foco_s = (
                [c for c in sel if c in setor["COLABORADOR"].unique()]
                if sel else
                setor.groupby("COLABORADOR")["QUANTIDADE"].sum()
                .sort_values(ascending=False).head(15).index.tolist()
            )
            mix_s = setor[setor["COLABORADOR"].isin(colabs_foco_s)]
            if not mix_s.empty:
                mix_s_agg = (mix_s.groupby(["COLABORADOR", "SETOR"])["QUANTIDADE"]
                             .sum().reset_index())
                ordem_s = (mix_s_agg.groupby("COLABORADOR")["QUANTIDADE"].sum()
                           .sort_values(ascending=True).index.tolist())
                fig_ms = px.bar(mix_s_agg, x="QUANTIDADE", y="COLABORADOR", color="SETOR",
                                orientation="h", barmode="stack",
                                category_orders={"COLABORADOR": ordem_s})
                fig_ms.update_layout(height=max(280, len(ordem_s) * 38),
                                     margin=dict(l=0, r=30, t=10, b=0),
                                     xaxis_title="Quantidade", yaxis_title="",
                                     legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                                 xanchor="right", x=1, title="Setor"),
                                     **DARK_LAYOUT)
                st.plotly_chart(fig_ms, use_container_width=True)

                # Versatilidade: nº de setores + setor principal por colaborador
                st.markdown('<p class="section-title">⭐ Setor Principal por Colaborador</p>',
                            unsafe_allow_html=True)
                idx_princ_s = mix_s_agg.groupby("COLABORADOR")["QUANTIDADE"].idxmax()
                principal_s = (mix_s_agg.loc[idx_princ_s, ["COLABORADOR", "SETOR"]]
                               .set_index("COLABORADOR")["SETOR"])
                vers_s = (mix_s.groupby("COLABORADOR")
                          .agg(**{"Nº de Setores": ("SETOR", "nunique"),
                                  "Total": ("QUANTIDADE", "sum")})
                          .reset_index())
                vers_s["Setor Principal"] = vers_s["COLABORADOR"].map(principal_s)
                vers_s = vers_s.sort_values("Total", ascending=False)
                vers_s = vers_s.rename(columns={"COLABORADOR": "Colaborador"})
                vers_s["Total"] = vers_s["Total"].map(lambda x: f"{x:,.0f}".replace(",", "."))
                st.dataframe(
                    vers_s[["Colaborador", "Setor Principal", "Nº de Setores", "Total"]],
                    use_container_width=True, hide_index=True,
                )

    # ── Análise por Função (apenas se a unidade tiver coluna de função) ──────────
    if "FUNCAO" in dff.columns:
        func = escopo[escopo["FUNCAO"].astype(str).str.strip() != ""]
        if not func.empty:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<p class="section-title">🔧 Produção por Função</p>',
                        unsafe_allow_html=True)
            agg = (func.groupby("FUNCAO")["QUANTIDADE"].sum()
                   .sort_values(ascending=True).reset_index())
            fig_f = px.bar(agg, x="QUANTIDADE", y="FUNCAO", orientation="h",
                           text="QUANTIDADE", color="QUANTIDADE", color_continuous_scale="Tealgrn")
            fig_f.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                                textfont=dict(color="#CBD5E0"))
            fig_f.update_layout(height=max(260, len(agg) * 36), showlegend=False,
                                coloraxis_showscale=False, margin=dict(l=0, r=70, t=10, b=0),
                                xaxis_title="Quantidade", yaxis_title="", **DARK_LAYOUT)
            st.plotly_chart(fig_f, use_container_width=True)

            # ── Individual: Mix de funções por colaborador ───────────────────────
            # Escopo: colaboradores filtrados; se nenhum, top 12 por produção total.
            if sel:
                colabs_foco = sel
            else:
                colabs_foco = (func.groupby("COLABORADOR")["QUANTIDADE"].sum()
                               .sort_values(ascending=False).head(12).index.tolist())
            mix = func[func["COLABORADOR"].isin(colabs_foco)]
            if not mix.empty:
                st.markdown('<p class="section-title">🧩 Mix de Funções por Colaborador</p>',
                            unsafe_allow_html=True)
                mix_agg = (mix.groupby(["COLABORADOR", "FUNCAO"])["QUANTIDADE"]
                           .sum().reset_index())
                # ordena colaboradores por total (maior em cima na barra horizontal)
                ordem = (mix_agg.groupby("COLABORADOR")["QUANTIDADE"].sum()
                         .sort_values(ascending=True).index.tolist())
                fig_mix = px.bar(mix_agg, x="QUANTIDADE", y="COLABORADOR", color="FUNCAO",
                                 orientation="h", barmode="stack",
                                 category_orders={"COLABORADOR": ordem})
                fig_mix.update_layout(height=max(280, len(ordem) * 42),
                                      margin=dict(l=0, r=30, t=10, b=0),
                                      xaxis_title="Quantidade", yaxis_title="",
                                      legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                                  xanchor="right", x=1, title=""),
                                      **DARK_LAYOUT)
                st.plotly_chart(fig_mix, use_container_width=True)

                # ── Versatilidade: nº de funções + função principal ──────────────
                st.markdown('<p class="section-title">⭐ Versatilidade dos Colaboradores</p>',
                            unsafe_allow_html=True)
                st.caption("Quantas funções diferentes cada colaborador executa e qual a principal "
                           "(maior volume) no período/seleção.")
                idx_princ = mix_agg.groupby("COLABORADOR")["QUANTIDADE"].idxmax()
                principal = (mix_agg.loc[idx_princ, ["COLABORADOR", "FUNCAO"]]
                             .set_index("COLABORADOR")["FUNCAO"])
                vers = (mix.groupby("COLABORADOR")
                        .agg(**{"Nº de Funções": ("FUNCAO", "nunique"),
                                "Total": ("QUANTIDADE", "sum")})
                        .reset_index())
                vers["Função Principal"] = vers["COLABORADOR"].map(principal)
                vers = vers.sort_values("Nº de Funções", ascending=False)
                vers = vers.rename(columns={"COLABORADOR": "Colaborador"})
                vers["Total"] = vers["Total"].map(lambda x: f"{x:,.0f}".replace(",", "."))
                st.dataframe(
                    vers[["Colaborador", "Nº de Funções", "Função Principal", "Total"]],
                    use_container_width=True, hide_index=True,
                )

    # ── Análise por Tamanho (apenas se a unidade tiver TAMANHO preenchido) ──────
    if "TAMANHO" in dff.columns and escopo["TAMANHO"].astype(str).str.strip().ne("").any():
        tam = escopo[escopo["TAMANHO"].astype(str).str.strip() != ""].copy()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">📐 Produção por Tamanho (Costura)</p>',
                    unsafe_allow_html=True)
        st.caption("Registros das costureiras — tamanho informado na coluna DESCRIÇÃO da planilha.")

        agg_t = (tam.groupby("TAMANHO")["QUANTIDADE"].sum()
                 .sort_values(ascending=True).reset_index())
        _TAM_CORES = {"CASAL": "#4ECDC4", "SOLTEIRO": "#45B7D1",
                      "QUEEN": "#96CEB4", "KING": "#FFEAA7"}
        fig_t = px.bar(agg_t, x="QUANTIDADE", y="TAMANHO", orientation="h",
                       text="QUANTIDADE",
                       color="TAMANHO", color_discrete_map=_TAM_CORES)
        fig_t.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                            textfont=dict(color="#CBD5E0"))
        fig_t.update_layout(height=max(220, len(agg_t) * 50), showlegend=False,
                            margin=dict(l=0, r=80, t=10, b=0),
                            xaxis_title="Quantidade", yaxis_title="", **DARK_LAYOUT)
        st.plotly_chart(fig_t, use_container_width=True)

        # Mix Tamanho × Costureira
        costureiras_foco = (
            [c for c in sel if c in tam["COLABORADOR"].unique()]
            if sel else
            tam.groupby("COLABORADOR")["QUANTIDADE"].sum()
            .sort_values(ascending=False).head(12).index.tolist()
        )
        mix_t = tam[tam["COLABORADOR"].isin(costureiras_foco)]
        if not mix_t.empty:
            st.markdown('<p class="section-title">🧵 Mix Tamanho × Costureira</p>',
                        unsafe_allow_html=True)
            mix_t_agg = (mix_t.groupby(["COLABORADOR", "TAMANHO"])["QUANTIDADE"]
                         .sum().reset_index())
            ordem_t = (mix_t_agg.groupby("COLABORADOR")["QUANTIDADE"].sum()
                       .sort_values(ascending=True).index.tolist())
            fig_mt = px.bar(mix_t_agg, x="QUANTIDADE", y="COLABORADOR", color="TAMANHO",
                            orientation="h", barmode="stack",
                            category_orders={"COLABORADOR": ordem_t},
                            color_discrete_map=_TAM_CORES)
            fig_mt.update_layout(height=max(280, len(ordem_t) * 44),
                                 margin=dict(l=0, r=30, t=10, b=0),
                                 xaxis_title="Quantidade", yaxis_title="",
                                 legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                             xanchor="right", x=1, title="Tamanho"),
                                 **DARK_LAYOUT)
            st.plotly_chart(fig_mt, use_container_width=True)

            # Tabela pivot: Costureira × Tamanho
            st.markdown('<p class="section-title">📋 Resumo Costureira × Tamanho</p>',
                        unsafe_allow_html=True)
            pivot_t = (mix_t_agg
                       .pivot(index="COLABORADOR", columns="TAMANHO", values="QUANTIDADE")
                       .fillna(0).astype(int))
            pivot_t["Total"] = pivot_t.sum(axis=1)
            pivot_t = pivot_t.sort_values("Total", ascending=False).reset_index()
            pivot_t.columns.name = None
            for _col in pivot_t.columns[1:]:
                pivot_t[_col] = pivot_t[_col].map(lambda x: f"{x:,.0f}".replace(",", "."))
            st.dataframe(pivot_t.rename(columns={"COLABORADOR": "Costureira"}),
                         use_container_width=True, hide_index=True)

    # ── Produção por Cliente (quando houver) ─────────────────────────────────────
    if "CLIENTE" in dff.columns and escopo["CLIENTE"].astype(str).str.strip().ne("").any():
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">🏢 Produção por Cliente</p>', unsafe_allow_html=True)
        cli = escopo[escopo["CLIENTE"].astype(str).str.strip() != ""]
        aggc = (cli.groupby("CLIENTE")["QUANTIDADE"].sum()
                .sort_values(ascending=True).tail(15).reset_index())
        fig_c = px.bar(aggc, x="QUANTIDADE", y="CLIENTE", orientation="h",
                       text="QUANTIDADE", color="QUANTIDADE", color_continuous_scale="Blugrn")
        fig_c.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                            textfont=dict(color="#CBD5E0"))
        fig_c.update_layout(height=max(260, len(aggc) * 36), showlegend=False,
                            coloraxis_showscale=False, margin=dict(l=0, r=70, t=10, b=0),
                            xaxis_title="Quantidade", yaxis_title="", **DARK_LAYOUT)
        st.plotly_chart(fig_c, use_container_width=True)

    # ── Tabela detalhada ──────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    with st.expander("📋 Dados detalhados", expanded=False):
        tabela = escopo.copy()
        tabela["DATA"] = tabela["DATA"].dt.strftime("%d/%m/%Y")
        st.dataframe(tabela.sort_values("DATA"), use_container_width=True, hide_index=True)

def _screen_interno():
    with st.sidebar:
        st.markdown("### Atualizar")
        if st.button("🔄 Atualizar Dados", use_container_width=True, key="btn_atualizar_interno"):
            from utils.cache_manager import invalidate_all
            invalidate_all()
            st.cache_data.clear()
            st.rerun()
        st.sidebar.caption("Dados atualizados a cada 5 min.")

    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Análise de Produção</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Por Colaborador</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Interno</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="main-title">👥 Produção — Colaboradores Internos</p>',
                unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Selecione a unidade nas guias abaixo</p>',
                unsafe_allow_html=True)

    chaves = list(PRODUCAO_INTERNO_SHEETS.keys())
    rotulos = [f"{PRODUCAO_INTERNO_SHEETS[k]['icon']} {PRODUCAO_INTERNO_SHEETS[k]['label']}"
               for k in chaves]
    tabs = st.tabs(rotulos)
    for tab, chave in zip(tabs, chaves):
        with tab:
            _render_interno_tab(chave, PRODUCAO_INTERNO_SHEETS[chave])

# ── Fontes do Relatório Semanal (apenas loaders internos já existentes) ─────────
_FONTES_REL_SEMANAL = [
    ("LITTEX",  "LITTEX"),
    ("GGTTEX",  "GGTTEX_JOGOS"),
    ("GGTTEX",  "GGTTEX_FRONHA"),
    ("CORTINA", "GGTTEX_CORTINA"),
]

_MESES_ABREV_REL = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

# ── Metas da foto (CLIENTE · PRODUTO · FÁBRICA · META_MES · META_SEM) ────────────
# ZANATTEX = GGTTEX (mesma fábrica, nome antigo na tabela)
_METAS_FOTO = [
    # NC INDUSTRIA
    ("NC INDUSTRIA", "COBERTOR TOQUE DE SEDA", "MEGA BARIRI",     250000, 62500),
    ("NC INDUSTRIA", "MANTA",                  "MEGA BARIRI",      13000,  3250),
    ("NC INDUSTRIA", "FRONHAS",                "LITEX",            30000,  7500),
    # BURDAYS
    ("BURDAYS",      "LENCOL AVULSO",          "ZANATTEX",        110000, 27500),
    ("BURDAYS",      "LENCOL AVULSO",          "ZANATTEX",         15000,  3750),
    ("BURDAYS",      "CORTINA",                "ZANATTEX",             0,     0),
    # ANDREZA
    ("ANDREZA",      "MANTA BABY",             "PREVITTEX MATRIZ",  20000,  5000),
    ("ANDREZA",      "JOGOS DE CAMA",          "PREVITTEX MATRIZ",  50000, 12500),
    # CAMESA
    ("CAMESA",       "FRONHAS",                "ZANATTEX",         100000, 25000),
    ("CAMESA",       "FRONHAS",                "PREVITTEX MATRIZ",  33000,  8250),
    ("CAMESA",       "VELOUR",                 "ZANATTEX",         200000, 50000),
    ("CAMESA",       "MANTA PRENSADA",         "ZANATTEX",          15000,  3750),
    ("CAMESA",       "MANTA C/ CINTA",         "ZANATTEX",          63000, 15750),
    ("CAMESA",       "COBERTOR 180G",          "ZANATTEX",          60000, 15000),
    ("CAMESA",       "BABY",                   "ZANATTEX",          70000, 17500),
    # DECOR
    ("DECOR",        "JOGO DE CAMA",           "PREVITTEX FILIAL",  14000,  3500),
    ("DECOR",        "CORTINA",                "GGTTEX",            10000,  2500),
    # SULTAN
    ("SULTAN",       "CORTINA",                "ZANATTEX",           5000,  1250),
    ("SULTAN",       "JOGO DE CAMA",           "ZANATTEX",          60000, 15000),
    ("SULTAN",       "FRONHAS",                "ZANATTEX",          10000,  2500),
    # MARCELINO
    ("MARCELINO",    "JG DUPLO PONTO PALITO",  "MEGA PREVEN",       10000,  2500),
    ("MARCELINO",    "FRONHA PONTO PALITO",    "MEGA PREVEN",        4000,  1000),
    ("MARCELINO",    "TONHAS",                 "MEGA PREVEN",       20000,  5000),
    ("MARCELINO",    "TONHAS",                 "ZANATTEX",          80000, 20000),
    # SEVEN
    ("SEVEN",        "LENCOL AVULSO",          "ZANATTEX",         180000, 45000),
    ("SEVEN",        "FRONHA PLUSH",           "ZANATTEX",              0,     0),
]

# Fábricas que já têm dados no sistema
_FABRICAS_COM_DADOS = {"LITEX", "LITTEX", "ZANATTEX", "GGTTEX", "CORTINA"}


def _norm_match(s: str) -> str:
    """Uppercase + sem acento para matching de nomes."""
    s = str(s).strip().upper()
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _get_realizado_meta(df_prod: pd.DataFrame, cliente: str, produto: str, fabrica: str) -> int:
    """
    Retorna o realizado da semana para uma linha de meta.
    Regras de matching (por limitação da estrutura dos loaders):
      - LITEX/LITTEX  → LITTEX, match por CLIENTE + PRODUTO (normalizado)
      - ZANATTEX/GGTTEX + JOGO DE CAMA/JOGOS DE CAMA → GGTTEX_JOGOS (todas as linhas do cliente)
      - ZANATTEX/GGTTEX + CORTINA → GGTTEX_CORTINA (todas as linhas do cliente)
      - ZANATTEX/GGTTEX + outros → GGTTEX data do cliente, tenta match de produto
      - PREVITTEX / MEGA BARIRI / MEGA PREVEN → sem dados, retorna 0
    """
    if df_prod.empty:
        return 0

    fab_u   = fabrica.upper()
    prod_n  = _norm_match(produto)
    cli_n   = _norm_match(cliente)

    if fab_u in ("LITEX", "LITTEX"):
        fab_labels = ["LITTEX"]
    elif fab_u in ("ZANATTEX", "GGTTEX"):
        fab_labels = ["GGTTEX", "CORTINA"]
    else:
        return 0  # sem dados ainda

    df_f = df_prod[df_prod["FABRICA"].isin(fab_labels)].copy()
    df_c = df_f[df_f["CLIENTE"].apply(_norm_match) == cli_n]
    if df_c.empty:
        return 0

    # Matching por produto
    if prod_n in ("JOGO DE CAMA", "JOGOS DE CAMA"):
        # GGTTEX_JOGOS: produtos são tamanhos (CASAL/SOLTEIRO/QUEEN) → pega tudo do cliente
        df_p = df_c[df_c["FABRICA"] == "GGTTEX"]
    elif prod_n == "CORTINA":
        df_p = df_c[df_c["FABRICA"] == "CORTINA"]
    else:
        # Tenta match exato normalizado
        df_p = df_c[df_c["PRODUTO"].apply(_norm_match) == prod_n]
        if df_p.empty:
            # Fallback: produto do loader começa com os primeiros 5 chars da meta
            pref = prod_n[:5]
            df_p = df_c[df_c["PRODUTO"].apply(_norm_match).str.startswith(pref)]

    return int(df_p["QUANTIDADE"].sum())


@st.cache_data(ttl=300, show_spinner=False)
def _load_rel_semanal_cached(segunda: date, domingo: date) -> pd.DataFrame:
    """
    Carrega e consolida produção da semana a partir dos loaders internos:
    LITTEX, GGTTEX (Jogos + Fronha), GGTTEX Cortina.
    Retorna DataFrame: FABRICA | PRODUTO | CLIENTE | QUANTIDADE
    """
    frames = []
    for label, chave in _FONTES_REL_SEMANAL:
        df = load_interno_unidade(chave)
        if df.empty:
            continue
        mask = (df["DATA"].dt.date >= segunda) & (df["DATA"].dt.date <= domingo)
        df_f = df[mask].copy()
        if df_f.empty:
            continue
        df_f["FABRICA"] = label
        frames.append(df_f[["FABRICA", "PRODUTO", "CLIENTE", "QUANTIDADE"]])

    if not frames:
        return pd.DataFrame(columns=["FABRICA", "PRODUTO", "CLIENTE", "QUANTIDADE"])

    combined = pd.concat(frames, ignore_index=True)
    combined["PRODUTO"] = combined["PRODUTO"].fillna("").str.strip().str.upper()
    combined["CLIENTE"] = combined["CLIENTE"].fillna("").str.strip().str.upper()

    return (
        combined
        .groupby(["FABRICA", "PRODUTO", "CLIENTE"], as_index=False)["QUANTIDADE"]
        .sum()
        .sort_values(["FABRICA", "PRODUTO", "CLIENTE"])
        .reset_index(drop=True)
    )


def _semana_range(offset: int = 0) -> tuple[date, date]:
    """(segunda, domingo) da semana atual + offset em semanas."""
    hoje = date.today()
    segunda = hoje - timedelta(days=hoje.weekday()) + timedelta(weeks=offset)
    return segunda, segunda + timedelta(days=6)


def _screen_relatorio_semanal():
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Análise de Produção</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Por Cliente</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Relatório Semanal</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header" style="padding-top:18px;">
        <div class="page-badge">📋 Relatório Semanal</div>
        <h1 class="page-title">Relatório <span class="accent">Semanal</span></h1>
        <p class="page-subtitle">Produção da semana — LITTEX · GGTTEX · Cortina</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    # ── Navegação de semana ──────────────────────────────────────────────────────
    # Padrão: última semana completa (offset -1), pois a semana atual pode
    # ainda não ter dados lançados.
    offset = st.session_state.get("rel_sem_offset", -1)
    segunda, domingo = _semana_range(offset)

    col_prev, col_label, col_next, col_refresh = st.columns([1, 3, 1, 1])
    with col_prev:
        if st.button("← Semana anterior", key="rel_sem_prev", use_container_width=True):
            st.session_state.rel_sem_offset = offset - 1
            st.rerun()
    with col_label:
        s_str = f"{segunda.day:02d} {_MESES_ABREV_REL[segunda.month-1]}"
        d_str = f"{domingo.day:02d} {_MESES_ABREV_REL[domingo.month-1]} {domingo.year}"
        st.markdown(
            f"<div style='text-align:center;font-size:1.1rem;font-weight:700;"
            f"color:#FFFFFF;padding:8px 0;'>📅 {s_str} — {d_str}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Semana seguinte →", key="rel_sem_next",
                     use_container_width=True, disabled=(offset >= 0)):
            st.session_state.rel_sem_offset = offset + 1
            st.rerun()
    with col_refresh:
        if st.button("🔄 Atualizar", key="rel_sem_refresh", use_container_width=True):
            from utils.cache_manager import invalidate
            for _, chave in _FONTES_REL_SEMANAL:
                cfg = PRODUCAO_INTERNO_SHEETS.get(chave, {})
                if cfg:
                    invalidate(cfg["id"], cfg["gid"])
            _load_rel_semanal_cached.clear()
            st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Carregamento ─────────────────────────────────────────────────────────────
    with st.spinner("Carregando dados da semana..."):
        df = _load_rel_semanal_cached(segunda, domingo)

    if df.empty:
        st.warning("Nenhum dado de produção encontrado para essa semana.")
        col_back, *_ = st.columns([2, 5])
        with col_back:
            if st.button("← Voltar", key="rel_sem_back_vazio", use_container_width=True):
                _go_prod('analysis_type')
        return

    # ── Abas ─────────────────────────────────────────────────────────────────────
    tab_fab, tab_cli = st.tabs(["🏭 Por Fábrica", "🏢 Por Cliente"])

    # ════════════════════════════════════════════════════════════════════════════
    # ABA 1 — Por Fábrica (conteúdo original)
    # ════════════════════════════════════════════════════════════════════════════
    with tab_fab:
        totais_fab  = df.groupby("FABRICA")["QUANTIDADE"].sum()
        total_geral = int(df["QUANTIDADE"].sum())
        fab_ordem   = [f for f in ["LITTEX", "GGTTEX", "CORTINA"] if f in totais_fab.index]

        met_cols = st.columns(1 + len(fab_ordem))
        with met_cols[0]:
            st.metric("Total Geral", f"{total_geral:,}".replace(",", ".") + " pçs")
        for i, fab in enumerate(fab_ordem, start=1):
            with met_cols[i]:
                st.metric(fab, f"{int(totais_fab[fab]):,}".replace(",", ".") + " pçs")

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        COR_FAB = {"LITTEX": "#4ECDC4", "GGTTEX": "#45B7D1", "CORTINA": "#AB47BC"}

        for fab in ["LITTEX", "GGTTEX", "CORTINA"]:
            df_fab = df[df["FABRICA"] == fab]
            if df_fab.empty:
                continue

            cor       = COR_FAB.get(fab, "#FFFFFF")
            total_fab = int(df_fab["QUANTIDADE"].sum())

            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04);border-left:4px solid {cor};"
                f"border-radius:0 10px 10px 0;padding:10px 18px;margin-bottom:8px;"
                f"display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:{cor};font-weight:800;font-size:1.05rem;"
                f"letter-spacing:0.08em;'>🏭 {fab}</span>"
                f"<span style='color:#A0A0A0;font-size:0.9rem;'>Total semana: "
                f"<strong style='color:#FFFFFF;'>{total_fab:,}".replace(",", ".") +
                f"</strong> pçs</span></div>",
                unsafe_allow_html=True,
            )

            df_show = (
                df_fab[["PRODUTO", "CLIENTE", "QUANTIDADE"]]
                .sort_values(["CLIENTE", "PRODUTO"])
                .reset_index(drop=True)
                .rename(columns={"PRODUTO": "Produto", "CLIENTE": "Cliente",
                                  "QUANTIDADE": "Qtd. Semana"})
            )
            st.dataframe(
                df_show,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Produto":     st.column_config.TextColumn("Produto",     width="large"),
                    "Cliente":     st.column_config.TextColumn("Cliente",     width="medium"),
                    "Qtd. Semana": st.column_config.NumberColumn("Qtd. Semana",
                                       format="%d", width="small"),
                },
            )
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # Export CSV dentro da aba
        nome_csv = f"relatorio_semanal_{segunda.strftime('%d%m%Y')}.csv"
        st.download_button(
            "⬇ Exportar CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=nome_csv,
            mime="text/csv",
            use_container_width=False,
            key="rel_sem_export",
        )

    # ════════════════════════════════════════════════════════════════════════════
    # ABA 2 — Por Cliente (análise de metas)
    # ════════════════════════════════════════════════════════════════════════════
    with tab_cli:
        st.markdown(
            "<p style='color:#A0A0A0;font-size:0.9rem;margin-bottom:20px;'>"
            "Comparativo <strong style='color:#FFFFFF;'>Meta Semana × Realizado</strong> "
            "com base nas metas definidas. Fábricas sem dados aparecem como "
            "<em>Aguardando</em>.</p>",
            unsafe_allow_html=True,
        )

        # Agrupa linhas de metas por cliente (preserva ordem de inserção)
        clientes_ord: list[str] = []
        metas_por_cli: dict[str, list] = {}
        for cli, prod, fab, meta_mes, meta_sem in _METAS_FOTO:
            if cli not in metas_por_cli:
                clientes_ord.append(cli)
                metas_por_cli[cli] = []
            metas_por_cli[cli].append((prod, fab, meta_mes, meta_sem))

        COR_CLI = {
            "NC INDUSTRIA": "#4ECDC4",
            "BURDAYS":      "#45B7D1",
            "ANDREZA":      "#FFD93D",
            "CAMESA":       "#FF6B6B",
            "DECOR":        "#C3A6FF",
            "SULTAN":       "#FF9F43",
            "MARCELINO":    "#26de81",
            "SEVEN":        "#fd9644",
        }

        for cli in clientes_ord:
            linhas   = metas_por_cli[cli]
            cor_cli  = COR_CLI.get(cli, "#AAAAAA")

            rows = []
            total_meta_sem = 0
            total_real     = 0

            for prod, fab, meta_mes, meta_sem in linhas:
                tem_dados = fab.strip().upper() in _FABRICAS_COM_DADOS
                real      = _get_realizado_meta(df, cli, prod, fab) if tem_dados else None

                if meta_sem > 0 and real is not None:
                    pct = real / meta_sem * 100
                    if pct >= 90:
                        ind = "🟢"
                    elif pct >= 50:
                        ind = "🟡"
                    else:
                        ind = "🔴"
                    pct_str = f"{pct:.1f}%"
                elif real is None:
                    ind     = "⚫"
                    pct_str = "Aguardando"
                else:
                    # meta_sem == 0 → sem meta definida
                    ind     = "—"
                    pct_str = "—"

                real_str = f"{real:,}".replace(",", ".") if real is not None else "—"
                meta_str = f"{meta_sem:,}".replace(",", ".") if meta_sem > 0 else "—"

                rows.append({
                    "": ind,
                    "Produto":   prod,
                    "Fábrica":   fab,
                    "Meta Sem.": meta_str,
                    "Realizado": real_str,
                    "%":         pct_str,
                })

                if meta_sem > 0:
                    total_meta_sem += meta_sem
                if real is not None:
                    total_real += real

            # Cabeçalho do cliente
            pct_total = (total_real / total_meta_sem * 100) if total_meta_sem > 0 else 0
            ind_total = "🟢" if pct_total >= 90 else ("🟡" if pct_total >= 50 else "🔴")
            if total_meta_sem == 0:
                ind_total = "⚫"

            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04);"
                f"border-left:4px solid {cor_cli};"
                f"border-radius:0 10px 10px 0;padding:10px 18px;margin:16px 0 6px 0;"
                f"display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:{cor_cli};font-weight:800;font-size:1.05rem;"
                f"letter-spacing:0.06em;'>🏢 {cli}</span>"
                f"<span style='color:#A0A0A0;font-size:0.9rem;'>"
                f"Meta sem.: <strong style='color:#FFFFFF;'>"
                f"{total_meta_sem:,}".replace(",", ".") +
                f"</strong> &nbsp;|&nbsp; "
                f"Realizado: <strong style='color:#FFFFFF;'>"
                f"{total_real:,}".replace(",", ".") +
                f"</strong> pçs &nbsp; {ind_total} "
                f"<strong style='color:#FFFFFF;'>{pct_total:.1f}%</strong>"
                f"</span></div>",
                unsafe_allow_html=True,
            )

            df_cli = pd.DataFrame(rows)
            st.dataframe(
                df_cli,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "":          st.column_config.TextColumn("",          width=28),
                    "Produto":   st.column_config.TextColumn("Produto",   width="large"),
                    "Fábrica":   st.column_config.TextColumn("Fábrica",   width="medium"),
                    "Meta Sem.": st.column_config.TextColumn("Meta Sem.", width="small"),
                    "Realizado": st.column_config.TextColumn("Realizado", width="small"),
                    "%":         st.column_config.TextColumn("%",         width="small"),
                },
            )

    # ── Rodapé ───────────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("← Voltar", key="rel_sem_back", use_container_width=True):
            _go_prod('analysis_type')


# ─
# MAIN — dispatcher de telas
# ─
def main():
    init_session_state()
    st.markdown(get_selector_cards_css(), unsafe_allow_html=True)

    if st.session_state.get('_active_page') != 'producao':
        st.session_state.producao_screen = 'analysis_type'
    st.session_state._active_page = 'producao'

    screen = st.session_state.get('producao_screen', 'analysis_type')
    _sidebar_nav_producao(screen)

    if screen == 'analysis_type':
        _screen_analysis_type()
    elif screen == 'relatorio_semanal':
        _screen_relatorio_semanal()
    elif screen == 'colaborador_type':
        _screen_colaborador_type()
    elif screen == 'interno':
        _screen_interno()
    else:  # 'por_faccao' — Produção por Cliente foi descontinuada, ver changelog
        st.markdown("""
        <div class="breadcrumb">
            <span class="bc-link">Análise de Produção</span>
            <span class="bc-sep">›</span>
            <span class="bc-active">Por Cliente</span>
        </div>
        """, unsafe_allow_html=True)
        render_por_faccao()

if __name__ == "__main__":
    main()