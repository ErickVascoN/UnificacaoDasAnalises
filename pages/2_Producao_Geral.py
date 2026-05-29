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
from styles.selector_cards import get_selector_cards_css
from config.settings import PRODUCAO_INTERNO_SHEETS
from utils.producao_interno_loader import load_interno_unidade

# ─
# CONFIGURACAO DA PAGINA
# ─
st.set_page_config(
    page_title="Dashboard Produção - Empresas",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

CORES_EMPRESAS = {
    "Burdays": "#FF6B6B",
    "Camesa": "#4ECDC4",
    "Niazittex / Seven": "#45B7D1",
    "Cortex": "#FFA726",
    "Sultan": "#AB47BC",
    "Decor": "#26C6DA",
    "Marcelino": "#FFD54F",
}

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
        print(f"[LITEX_GERAL] Filtro NIAZI/SEVEN: {antes} → {len(raw)} linhas")
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
    return int((d.dt.weekday <= 4).sum())

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
    
    # Dias de segunda a sexta no período
    dias_seg_sex = (d.dt.weekday <= 4).sum()
    
    # Sábados onde houve produção (weekday 5)
    sabados_com_prod = (d.dt.weekday == 5).sum()
    
    return int(dias_seg_sex + sabados_com_prod)

# REMOVIDO: dias_uteis_com_sabados_trabalhados() - ver replacement abaixo
# REMOVIDO: dias_uteis_com_trabalho() - consolidada em calcular_dias_com_sabados_trabalhados()

def _calc_meta(df_f: pd.DataFrame, sel_facs: list) -> tuple:
    """
    Calcula a meta do período considerando que cada mês pode ter
    uma meta diária diferente por facção/produto.
    """
    df_sel = df_f[df_f["Faccao"].isin(sel_facs)].copy()

    meta_mensal = (
        df_sel
        # MÉDIO #17: Remove duplicate (Faccao, Produto, Year, Month) entries
        # Keep first occurrence of each (Fac, Prod, Year, Month) to avoid duplicate metas
        .drop_duplicates(subset=["Faccao", "Produto", "Ano", "Mes"])
        .groupby(["Faccao", "Ano", "Mes"], as_index=False)
        .agg({
            "Meta Diaria": "first"  # Pega apenas uma meta por (Faccao, Mes) - não duplica
        })
    )
    # Log fillna para Meta Diaria
    meta_diaria_antes_fillna = meta_mensal["Meta Diaria"].isna().sum()
    meta_mensal["Meta Diaria"] = meta_mensal["Meta Diaria"].fillna(0)
    if meta_diaria_antes_fillna > 0:
        logging.debug(f"Preenchidas {meta_diaria_antes_fillna} metas diárias com 0 em _calc_meta()")

    if meta_mensal["Meta Diaria"].sum() == 0:
        empty = pd.DataFrame(columns=["Faccao", "Meta Periodo", "Meta Dia Min", "Meta Dia Max"])
        return 0.0, pd.Series(dtype=float), empty

    dias_mes = (
        df_sel.groupby(["Ano", "Mes"])["Data"]
        .apply(calcular_dias_com_sabados_trabalhados)
        .reset_index()
        .rename(columns={"Data": "DiasUteis"})
    )

    meta_mensal = meta_mensal.merge(dias_mes, on=["Ano", "Mes"], how="left")
    meta_mensal["DiasUteis"] = meta_mensal["DiasUteis"].fillna(0)
    meta_mensal["Meta Periodo Mes"] = meta_mensal["Meta Diaria"] * meta_mensal["DiasUteis"]

    meta_periodo = float(meta_mensal["Meta Periodo Mes"].sum())

    meta_por_anomes = (
        meta_mensal.groupby(["Ano", "Mes"], as_index=False)["Meta Diaria"].sum()
    )
    datas_unicas = df_sel[["Data", "Ano", "Mes"]].drop_duplicates()
    # MÉDIO #17: Select unique (Data, Ano, Mes) combinations
    # This creates a mapping of each date to its year/month for meta lookups
    meta_por_data = (
        datas_unicas
        .merge(meta_por_anomes, on=["Ano", "Mes"], how="left")
        .sort_values("Data")
        .set_index("Data")["Meta Diaria"]
    )
    # Log fillna para Meta por Data
    meta_por_data_antes_fillna = meta_por_data.isna().sum()
    meta_por_data = meta_por_data.fillna(0)
    if meta_por_data_antes_fillna > 0:
        logging.debug(f"Preenchidas {meta_por_data_antes_fillna} metas diárias faltando por data em _calc_meta()")
    meta_por_data = meta_por_data[~meta_por_data.index.duplicated(keep="first")]

    meta_por_faccao = (
        meta_mensal
        .groupby("Faccao")
        .agg(
            Meta_Periodo=("Meta Periodo Mes", "sum"),
            Meta_Dia_Min=("Meta Diaria", "min"),
            Meta_Dia_Max=("Meta Diaria", "max"),
        )
        .reset_index()
        .rename(columns={
            "Meta_Periodo": "Meta Periodo",
            "Meta_Dia_Min": "Meta Dia Min",
            "Meta_Dia_Max": "Meta Dia Max",
        })
    )

    return meta_periodo, meta_por_data, meta_por_faccao

def _calc_meta_por_produto(df_f: pd.DataFrame, sel_facs: list) -> pd.DataFrame:
    """
    Calcula meta por (Faccao, Produto) para a tabela expandida.
    """
    df_sel = df_f[df_f["Faccao"].isin(sel_facs)].copy()

    meta_mensal = (
        df_sel
        # MÉDIO #17: Remove duplicate (Faccao, Produto, Year, Month) entries
        # Keep first occurrence to avoid duplicate meta calculations
        .drop_duplicates(subset=["Faccao", "Produto", "Ano", "Mes"])
        [["Faccao", "Produto", "Ano", "Mes", "Meta Diaria"]]
        .copy()
    )
    # Log fillna para Meta Diaria (por produto)
    meta_diaria_antes_fillna = meta_mensal["Meta Diaria"].isna().sum()
    meta_mensal["Meta Diaria"] = meta_mensal["Meta Diaria"].fillna(0)
    if meta_diaria_antes_fillna > 0:
        logging.debug(f"Preenchidas {meta_diaria_antes_fillna} metas diárias com 0 em _calc_meta_por_produto()")

    dias_mes = (
        df_sel.groupby(["Ano", "Mes"])["Data"]
        .apply(calcular_dias_com_sabados_trabalhados)
        .reset_index()
        .rename(columns={"Data": "DiasUteis"})
    )

    meta_mensal = meta_mensal.merge(dias_mes, on=["Ano", "Mes"], how="left")
    # Log fillna para DiasUteis (por produto)
    dias_uteis_antes_fillna = meta_mensal["DiasUteis"].isna().sum()
    meta_mensal["DiasUteis"] = meta_mensal["DiasUteis"].fillna(0)
    if dias_uteis_antes_fillna > 0:
        logging.debug(f"Preenchidos {dias_uteis_antes_fillna} dias úteis com 0 em _calc_meta_por_produto()")
    meta_mensal["Meta Periodo Mes"] = meta_mensal["Meta Diaria"] * meta_mensal["DiasUteis"]

    result = (
        meta_mensal
        .groupby(["Faccao", "Produto"])
        .agg(
            Meta_Periodo=("Meta Periodo Mes", "sum"),
            Meta_Dia_Min=("Meta Diaria", "min"),
            Meta_Dia_Max=("Meta Diaria", "max"),
        )
        .reset_index()
        .rename(columns={
            "Meta_Periodo": "Meta Periodo",
            "Meta_Dia_Min": "Meta Dia Min",
            "Meta_Dia_Max": "Meta Dia Max",
        })
    )
    return result

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
              f"Datas: {df_litex['Data'].min()} → {df_litex['Data'].max()}")

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
    for _, row in raw_block.iterrows():
        if "faccao" in col_idx:
            fv = row.iloc[col_idx["faccao"]]
            if pd.isna(fv) or str(fv).strip() in ("", "nan", "None"):
                continue
            faccao = str(fv).strip().upper()
            if _remove_accents(faccao) in _HEADER_LABELS or faccao in _HEADER_LABELS:
                continue
        else:
            faccao = sheet_name.upper()

        pv = row.iloc[col_idx["produto"]]
        if pd.isna(pv) or str(pv).strip() in ("", "nan", "None"):
            continue
        produto = str(pv).strip().upper()
        if _remove_accents(produto) in _HEADER_LABELS or produto in _HEADER_LABELS:
            continue

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
# Callbacks de filtro
# ─
def _on_home_ano_change():
    for k in ("home_mes", "home_dia", "home_ini", "home_fim"):
        st.session_state.pop(k, None)

def _on_home_mes_change():
    for k in ("home_dia", "home_ini", "home_fim"):
        st.session_state.pop(k, None)

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
# TELA INICIAL (HOME)
# ─
def render_home(all_data):
    with st.sidebar:
        st.markdown("### Filtros")

        all_anos = sorted(set(a for df in all_data.values() for a in df["Ano"].unique()))
        if "home_ano" not in st.session_state:
            st.session_state["home_ano"] = list(all_anos)
        sel_anos = st.multiselect("Ano", all_anos, key="home_ano", on_change=_on_home_ano_change)
        if not sel_anos:
            sel_anos = all_anos

        all_meses = sorted(set(
            m for df in all_data.values()
            for m in df[df["Ano"].isin(sel_anos)]["Mes"].unique()
        ))
        if "home_mes" not in st.session_state:
            st.session_state["home_mes"] = list(all_meses)
        else:
            valid_set = set(all_meses)
            st.session_state["home_mes"] = [m for m in st.session_state["home_mes"] if m in valid_set]
        sel_meses = st.multiselect(
            "Mês", all_meses, format_func=lambda m: MESES_NOME[m],
            key="home_mes", on_change=_on_home_mes_change,
        )
        if not sel_meses:
            sel_meses = all_meses

        st.markdown("### Filtro de Dias")
        modo = st.radio("Tipo de filtro", ["Período", "Um dia"], horizontal=True, key="home_modo")

        all_datas = pd.concat([df["Data"] for df in all_data.values()])
        filtered_datas = all_datas[
            all_datas.dt.year.isin(sel_anos) & all_datas.dt.month.isin(sel_meses)
        ]
        if not filtered_datas.empty:
            d_min = filtered_datas.min().date()
            d_max = filtered_datas.max().date()
        else:
            d_min = all_datas.min().date()
            d_max = all_datas.max().date()

        for _k, _def in [("home_dia", d_max), ("home_ini", d_min), ("home_fim", d_max)]:
            if _k not in st.session_state:
                st.session_state[_k] = _def
            else:
                _v = st.session_state[_k]
                if _v < d_min:
                    st.session_state[_k] = d_min
                elif _v > d_max:
                    st.session_state[_k] = d_max

        if modo == "Um dia":
            dia_sel = st.date_input("Dia", min_value=d_min, max_value=d_max,
                                    format="DD/MM/YYYY", key="home_dia")
            date_filter = lambda df: df[
                df["Ano"].isin(sel_anos) & df["Mes"].isin(sel_meses) &
                (df["Data"].dt.date == dia_sel)
            ]
        else:
            d_ini = st.date_input("Início", min_value=d_min, max_value=d_max,
                                  format="DD/MM/YYYY", key="home_ini")
            d_fim = st.date_input("Fim", min_value=d_min, max_value=d_max,
                                  format="DD/MM/YYYY", key="home_fim")
            ini, fim = min(d_ini, d_fim), max(d_ini, d_fim)
            date_filter = lambda df: df[
                df["Ano"].isin(sel_anos) & df["Mes"].isin(sel_meses) &
                (df["Data"].dt.date.between(ini, fim))
            ]

        if st.button("🔄 Atualizar Dados", use_container_width=True):
            from utils.cache_manager import invalidate_all
            invalidate_all()
            st.cache_data.clear()
            st.rerun()

        st.sidebar.divider()
        st.sidebar.caption("Dados atualizados a cada 10 min.")

    filtered_data = {emp: date_filter(df) for emp, df in all_data.items()}
    filtered_data = {emp: df for emp, df in filtered_data.items() if not df.empty}
    excluidas = sorted(set(all_data.keys()) - set(filtered_data.keys()))

    if not filtered_data:
        st.markdown('<p class="main-title">🏭 Dashboard de Produção — Todas as Empresas</p>', unsafe_allow_html=True)
        st.markdown("---")
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        components.html(_FILTROS_BTN_HTML, height=45)

    st.markdown('<p class="main-title">🏭 Dashboard de Produção — Todas as Empresas</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Visão Geral de Todas as Empresas</p>', unsafe_allow_html=True)
    st.markdown("---")

    total_geral = sum(df["Quantidade"].sum() for df in filtered_data.values())
    n_empresas = len(filtered_data)
    dias_total = max((df[df["Quantidade"] > 0]["Data"].nunique() for df in filtered_data.values()), default=0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Empresas Ativas", n_empresas)
    m2.metric("Produção Total", f"{total_geral:,.0f}".replace(",", "."))
    m3.metric("Média por Empresa", f"{total_geral / n_empresas:,.0f}".replace(",", ".") if n_empresas else "0")
    m4.metric("Dias com Registros", dias_total)

    if excluidas:
        st.info(f"Empresas sem dados no período filtrado: **{', '.join(excluidas)}**")

    st.markdown("---")

    col_chart, col_select = st.columns([3, 2])
    company_totals = [{"Empresa": emp, "Total": df["Quantidade"].sum()} for emp, df in filtered_data.items()]
    df_totals = pd.DataFrame(company_totals).sort_values("Total", ascending=True)

    with col_chart:
        st.markdown('<p class="section-title">Produção Total por Empresa</p>', unsafe_allow_html=True)
        fig = px.bar(df_totals, x="Total", y="Empresa", orientation="h",
                     color="Empresa", color_discrete_map=CORES_EMPRESAS, text="Total")
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont=dict(color="#CBD5E0"))
        fig.update_layout(showlegend=False, height=max(300, n_empresas * 55),
                          margin=dict(l=0, r=80, t=10, b=0),
                          xaxis_title="Quantidade Produzida", yaxis_title="", **DARK_LAYOUT)
        st.plotly_chart(fig, width="stretch")

    with col_select:
        st.markdown('<p class="section-title">Selecione uma Empresa</p>', unsafe_allow_html=True)
        for emp in sorted(filtered_data.keys()):
            total_emp = df_totals.loc[df_totals["Empresa"] == emp, "Total"].values[0]
            if st.button(f"  {emp}  -  {total_emp:,.0f} un.".replace(",", "."),
                         key=f"btn_{emp}", use_container_width=True):
                st.query_params["empresa"] = emp
                st.rerun()

    st.markdown("---")

    st.markdown('<p class="section-title">Evolução Mensal da Produção</p>', unsafe_allow_html=True)
    monthly_frames = []
    for emp, df in filtered_data.items():
        grp = df.groupby(["Ano", "Mes"])["Quantidade"].sum().reset_index()
        grp["Empresa"] = emp
        grp["Periodo"] = grp.apply(lambda r: f"{int(r['Ano'])}-{int(r['Mes']):02d}", axis=1)
        monthly_frames.append(grp)

    if monthly_frames:
        df_monthly = pd.concat(monthly_frames, ignore_index=True)
        fig2 = px.line(df_monthly, x="Periodo", y="Quantidade", color="Empresa",
                       color_discrete_map=CORES_EMPRESAS, markers=True)
        fig2.update_layout(height=420, xaxis_title="Período", yaxis_title="Quantidade Produzida",
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                           **DARK_LAYOUT)
        st.plotly_chart(fig2, width="stretch")

    st.markdown("---")
    st.markdown('<p class="section-title">Produção Total por Produto</p>', unsafe_allow_html=True)

    prod_frames = []
    for emp, df in filtered_data.items():
        grp = df.groupby("Produto")["Quantidade"].sum().reset_index()
        grp["Empresa"] = emp
        prod_frames.append(grp)

    if prod_frames:
        df_prod_full = pd.concat(prod_frames, ignore_index=True)
        df_prod_full = df_prod_full[df_prod_full["Quantidade"] > 0]

        empresas_disp = sorted(df_prod_full["Empresa"].unique())
        produtos_disp_all = sorted(df_prod_full["Produto"].unique())

        st.markdown("""
        <style>
        .filtro-treemap-card {
            background: linear-gradient(135deg, #16161C 0%, #1E1E26 100%);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 14px;
            padding: 14px 20px 6px 20px;
            margin-bottom: 16px;
        }
        .filtro-treemap-header {
            display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
            color: #FFFFFF; font-size: 0.78rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 1px;
        }
        .filtro-treemap-header span {
            display: inline-block; width: 18px; height: 2px;
            background: #FFFFFF; border-radius: 2px;
        }
        .filtro-treemap-card label {
            color: #8899AA !important; font-size: 0.72rem !important;
            font-weight: 600 !important; text-transform: uppercase !important;
            letter-spacing: 0.6px !important;
        }
        span[data-baseweb="tag"] {
            background-color: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            color: #FFFFFF !important; border-radius: 6px !important;
            font-size: 0.9rem !important;
        }
        span[data-baseweb="tag"] span { color: #FFFFFF !important; font-size: 0.9rem !important; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="filtro-treemap-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="filtro-treemap-header"><span></span> Filtros do Gráfico <span></span></div>',
            unsafe_allow_html=True,
        )

        if st.session_state.pop("_tree_reset", False):
            st.session_state["tree_empresas"] = []
            st.session_state["tree_produtos"] = []

        col_fe, col_fp, col_clear = st.columns([3, 5, 1])

        with col_fe:
            sel_emp_tree = st.multiselect(
                "🏭  Empresas", empresas_disp, default=[], key="tree_empresas",
                placeholder="Selecione empresas...",
            )

        with col_fp:
            base_emp = sel_emp_tree if sel_emp_tree else empresas_disp
            produtos_disp = sorted(
                df_prod_full[df_prod_full["Empresa"].isin(base_emp)]["Produto"].unique()
            )
            sel_prod_tree = st.multiselect(
                "📦  Produtos", produtos_disp, default=[], key="tree_produtos",
                placeholder="Selecione produtos...",
            )

        with col_clear:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            if st.button("✕ Limpar", key="tree_clear", help="Resetar filtros do gráfico", use_container_width=True):
                st.session_state["_tree_reset"] = True
                st.rerun()

        emp_ativas  = sel_emp_tree  if sel_emp_tree  else empresas_disp
        prod_ativos = sel_prod_tree if sel_prod_tree else produtos_disp

        n_emp = len(emp_ativas); n_prod = len(prod_ativos)
        total_emp = len(empresas_disp); total_prod = len(produtos_disp_all)
        filtro_msg = (
            "Sem filtro ativo — exibindo tudo"
            if not sel_emp_tree and not sel_prod_tree
            else f'Exibindo <b style="color:#FFFFFF">{n_emp}</b>/{total_emp} empresas '
                 f'· <b style="color:#FFFFFF">{n_prod}</b>/{total_prod} produtos'
        )
        st.markdown(
            f'<p style="color:#555E6E;font-size:0.72rem;margin:4px 0 0 2px;">{filtro_msg}</p>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        df_prod = df_prod_full[
            df_prod_full["Empresa"].isin(emp_ativas) &
            df_prod_full["Produto"].isin(prod_ativos)
        ].copy()

        df_prod["Qtd_fmt"] = df_prod["Quantidade"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
        fig3 = px.treemap(df_prod, path=["Produto", "Empresa"], values="Quantidade",
                          color="Empresa", color_discrete_map=CORES_EMPRESAS, custom_data=["Qtd_fmt"])
        fig3.update_traces(
            textinfo="label+value",
            texttemplate="<b>%{label}</b><br>%{customdata[0]} un.",
            textfont=dict(size=13, color="#FFFFFF"),
            hovertemplate="<b>%{label}</b><br>Quantidade: %{customdata[0]}<extra></extra>",
        )
        fig3.update_layout(height=550, margin=dict(l=0, r=0, t=30, b=0), **DARK_LAYOUT)
        st.plotly_chart(fig3, width="stretch")

    st.markdown('<p class="section-title">Resumo por Empresa</p>', unsafe_allow_html=True)
    resumo_rows = []
    for emp, df in filtered_data.items():
        total = df["Quantidade"].sum()
        dias = df[df["Quantidade"] > 0]["Data"].nunique()
        media = total / dias if dias > 0 else 0
        resumo_rows.append({
            "Empresa": emp, "Total Produzido": int(total),
            "Dias Trabalhados": dias, "Média Diária": int(media),
            "Facções": df["Faccao"].nunique(), "Produtos": df["Produto"].nunique(),
        })
    df_resumo = pd.DataFrame(resumo_rows).sort_values("Total Produzido", ascending=False)
    _fmt_int = lambda v: f"{v:,.0f}".replace(",", ".")
    st.dataframe(df_resumo.style.format({"Total Produzido": _fmt_int, "Média Diária": _fmt_int}),
                 width="stretch", hide_index=True)

# ─
# PAGINA DA EMPRESA (ANALISE DETALHADA)
# ─
def render_company(empresa, df, all_data):
    cor = CORES_EMPRESAS.get(empresa, "#1E3A5F")

    with st.sidebar:
        if st.button("< Voltar para Visão Geral", use_container_width=True):
            st.query_params.clear()
            st.rerun()

        st.markdown("---")
        st.markdown(f"### {empresa}")
        st.sidebar.markdown("### Filtros")

        anos = sorted(df["Ano"].unique())
        sel_anos = st.multiselect("Ano", anos, default=anos)
        if not sel_anos:
            sel_anos = anos

        meses_disp = sorted(df[df["Ano"].isin(sel_anos)]["Mes"].unique())
        sel_meses = st.multiselect("Mês", meses_disp, default=meses_disp,
                                   format_func=lambda m: MESES_NOME[m])
        if not sel_meses:
            sel_meses = meses_disp

        df_f = df[(df["Ano"].isin(sel_anos)) & (df["Mes"].isin(sel_meses))]

        st.markdown("### Filtro de Dias")
        modo = st.radio("Tipo de filtro", ["Período", "Um dia"], horizontal=True)

        if not df_f.empty:
            d_min = df_f["Data"].min().date()
            d_max = df_f["Data"].max().date()

            if modo == "Um dia":
                dia_sel = st.date_input("Dia", value=d_max, min_value=d_min,
                                        max_value=d_max, format="DD/MM/YYYY")
                df_f = df_f[df_f["Data"].dt.date == dia_sel]
            else:
                d_ini = st.date_input("Início", value=d_min, min_value=d_min,
                                      max_value=d_max, format="DD/MM/YYYY")
                d_fim = st.date_input("Fim", value=d_max, min_value=d_min,
                                      max_value=d_max, format="DD/MM/YYYY")
                ini, fim = min(d_ini, d_fim), max(d_ini, d_fim)
                df_f = df_f[df_f["Data"].dt.date.between(ini, fim)]

        # filtro de cliente (apenas para niazittex / seven)
        if empresa == _NIAZI_SEVEN_KEY and "Cliente" in df_f.columns and not df_f.empty:
            clientes_disp = sorted(df_f["Cliente"].dropna().unique().tolist())
            clientes_disp = [c for c in clientes_disp if c]   # remove strings vazias
            if clientes_disp:
                sel_cli = st.multiselect(
                    "Cliente", clientes_disp, default=clientes_disp,
                    key="cli_niazi_filter",
                )
                if sel_cli:
                    df_f = df_f[df_f["Cliente"].isin(sel_cli)]

        facs = sorted(df_f["Faccao"].unique()) if not df_f.empty else []
        sel_facs = st.multiselect("Facção", facs, default=facs)
        if not sel_facs:
            sel_facs = facs

        prods = sorted(df_f[df_f["Faccao"].isin(sel_facs)]["Produto"].unique()) if not df_f.empty else []
        sel_prods = st.multiselect("Produto", prods, default=prods)
        if not sel_prods:
            sel_prods = prods

        if st.button("🔄 Atualizar Dados", use_container_width=True, key="btn_atualizar_empresa"):
            st.cache_data.clear()
            st.rerun()

        st.sidebar.divider()
        st.sidebar.caption("Dados atualizados a cada 10 min.")

    df_f = df_f[(df_f["Faccao"].isin(sel_facs)) & (df_f["Produto"].isin(sel_prods))]

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        components.html(_FILTROS_BTN_HTML, height=45)
    st.markdown(f'<p class="main-title">🏭 Dashboard de Produção Diária — {empresa.upper()}</p>', unsafe_allow_html=True)
    st.markdown("---")

    if df_f.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    prod_total = df_f["Quantidade"].sum()
    d_uteis = calcular_dias_com_sabados_trabalhados(df_f["Data"])
    media_dia = prod_total / d_uteis if d_uteis else 0

    meta_periodo, meta_por_data, meta_por_faccao = _calc_meta(df_f, sel_facs)
    tem_meta = meta_periodo > 0
    saldo = prod_total - meta_periodo if tem_meta else 0
    ating = (prod_total / meta_periodo) if (tem_meta and meta_periodo > 0) else 0

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
        st.info("Esta empresa ainda não possui meta cadastrada. "
                "Ao preencher a coluna 'Meta Diária', os gráficos de meta serão exibidos automaticamente.")

    st.markdown("")

    tab_vis, tab_facc, tab_rank, tab_dados = st.tabs(
        ["Visão Geral", "Por Facção", "Ranking & Alertas", "Dados"]
    )

    # ─ tab 1
    with tab_vis:
        serie = df_f.groupby("Data", as_index=False)["Quantidade"].sum().sort_values("Data")
        serie["Meta Dia"] = serie["Data"].map(meta_por_data).fillna(0)
        serie["Acum. Produzido"] = serie["Quantidade"].cumsum()
        serie["Acum. Meta"] = serie["Meta Dia"].cumsum()

        fig1 = go.Figure()
        cores_barras = (
            ["#22c55e" if p >= m else "#ef4444" for p, m in zip(serie["Quantidade"], serie["Meta Dia"])]
            if tem_meta else [cor] * len(serie)
        )
        fig1.add_bar(x=serie["Data"], y=serie["Quantidade"], name="Produzido", marker_color=cores_barras)
        if tem_meta:
            fig1.add_scatter(x=serie["Data"], y=serie["Meta Dia"], mode="lines",
                             name="Meta Diária", line=dict(color="#facc15", width=2, dash="dash"))
        fig1.update_layout(title="Produção Diária x Meta", xaxis_title="Data", yaxis_title="Peças",
                           template="plotly_dark", separators=",.",
                           xaxis=dict(tickformat="%d/%m/%Y"),
                           legend=dict(orientation="h", y=-0.15), margin=dict(t=50, b=60))
        st.plotly_chart(fig1, width="stretch")

        col_a, col_b = st.columns(2)
        with col_a:
            fig_acum = go.Figure()
            fig_acum.add_scatter(x=serie["Data"], y=serie["Acum. Produzido"],
                                 mode="lines+markers", name="Produzido Acumulado",
                                 line=dict(color="#3b82f6", width=3))
            if tem_meta:
                fig_acum.add_scatter(x=serie["Data"], y=serie["Acum. Meta"],
                                     mode="lines", name="Meta Acumulada",
                                     line=dict(color="#facc15", width=2, dash="dot"))
            fig_acum.update_layout(title="Acumulado: Produção x Meta", template="plotly_dark",
                                   separators=",.", xaxis=dict(tickformat="%d/%m/%Y"),
                                   legend=dict(orientation="h", y=-0.18), margin=dict(t=50, b=60))
            st.plotly_chart(fig_acum, width="stretch")

        with col_b:
            dia_df = df_f.groupby(["Data", "DiaSemana"], as_index=False)["Quantidade"].sum()
            dia_df["DiaSemana"] = pd.Categorical(dia_df["DiaSemana"], categories=ORDEM_DIAS, ordered=True)
            dia_df = dia_df.dropna(subset=["DiaSemana"]).sort_values("DiaSemana")
            dia_df["Dia"] = dia_df["DiaSemana"].map(NOMES_DIAS)
            fig_box = px.box(dia_df, x="Dia", y="Quantidade", color="Dia",
                             title="Distribuição por Dia da Semana", template="plotly_dark")
            fig_box.update_layout(showlegend=False, separators=",.", margin=dict(t=50, b=40))
            st.plotly_chart(fig_box, width="stretch")

        mensal = df_f.groupby(["Ano", "Mes"], as_index=False)["Quantidade"].sum()
        mensal["MesNome"] = mensal["Mes"].map(MESES_NOME)
        mensal["Ano"] = mensal["Ano"].astype(str)
        fig_mes = px.bar(mensal, x="MesNome", y="Quantidade", color="Ano", barmode="group",
                         text_auto=True, title="Produção Mensal", template="plotly_dark")
        fig_mes.update_layout(xaxis_title="Mês", yaxis_title="Peças",
                              separators=",.", margin=dict(t=50, b=40))
        st.plotly_chart(fig_mes, width="stretch")

    # ─ tab 2
    with tab_facc:
        # agrupamento por facção + produto (uma linha por combinação)
        tbl = df_f.groupby(["Faccao", "Produto"], as_index=False).agg(
            Produzido=("Quantidade", "sum"),
        )
        
        # contar dias: todos úteis + sábados trabalhados
        dias_list = []
        for (fac, prod), group in df_f.groupby(["Faccao", "Produto"]):
            # Consolidado MÉDIO #16: Usar função única para dias com sábados
            datas_fac_prod = df_f[(df_f["Faccao"] == fac) & 
                                   (df_f["Produto"] == prod)]["Data"]
            dias_calc = calcular_dias_com_sabados_trabalhados(datas_fac_prod)
            dias_list.append({"Faccao": fac, "Produto": prod, "Dias": dias_calc})
        dias_por_faccao_produto = pd.DataFrame(dias_list)
        
        tbl = tbl.merge(dias_por_faccao_produto, on=["Faccao", "Produto"], how="left")

        # meta por (faccao, produto)
        meta_prod_df = _calc_meta_por_produto(df_f, list(tbl["Faccao"].unique()))
        tbl = tbl.merge(meta_prod_df, on=["Faccao", "Produto"], how="left")
        tbl["Meta Periodo"] = tbl["Meta Periodo"].fillna(0)
        tbl["Meta Dia Min"]  = tbl["Meta Dia Min"].fillna(0)
        tbl["Meta Dia Max"]  = tbl["Meta Dia Max"].fillna(0)

        meses_selecionados = df_f["Mes"].nunique()

        def _fmt_meta_dia(row):
            if row["Meta Dia Min"] == row["Meta Dia Max"]:
                return f"{row['Meta Dia Max']:,.0f}".replace(",", ".")
            return (
                f"{row['Meta Dia Min']:,.0f} — {row['Meta Dia Max']:,.0f}".replace(",", ".")
                .replace(",", ".")
            )
        tbl["Meta Dia"] = tbl.apply(_fmt_meta_dia, axis=1)

        # Garante float64 antes das divisões (previne ZeroDivisionError com object dtype)
        tbl["Meta Periodo"] = pd.to_numeric(tbl["Meta Periodo"], errors="coerce").fillna(0)
        tbl["Produzido"]    = pd.to_numeric(tbl["Produzido"],    errors="coerce").fillna(0)
        tbl["Dias"]         = pd.to_numeric(tbl["Dias"],         errors="coerce").fillna(0)
        tbl["Ating. %"] = np.where(
            tbl["Meta Periodo"] > 0, tbl["Produzido"] / tbl["Meta Periodo"] * 100, 0
        )
        tbl["Saldo"]     = tbl["Produzido"] - tbl["Meta Periodo"]
        tbl["Media/Dia"] = np.where(tbl["Dias"] > 0, tbl["Produzido"] / tbl["Dias"], 0)
        tbl = tbl.sort_values(["Faccao", "Produto"])

        # tabela agregada por facção (usada nos gráficos e alertas)
        _, _, meta_fac_df = _calc_meta(df_f, sel_facs)
        
        # contar dias: todos úteis + sábados trabalhados (por facção)
        dias_fac_list = []
        for fac, group in df_f.groupby("Faccao"):
            # Consolidado MÉDIO #16: Usar função única para dias com sábados
            datas_fac = df_f[df_f["Faccao"] == fac]["Data"]
            dias_calc = calcular_dias_com_sabados_trabalhados(datas_fac)
            dias_fac_list.append({"Faccao": fac, "Dias": dias_calc})
        dias_por_faccao = pd.DataFrame(dias_fac_list)
        
        tbl_fac = df_f.groupby("Faccao", as_index=False).agg(
            Produzido=("Quantidade", "sum"),
        ).merge(dias_por_faccao, on="Faccao", how="left").merge(meta_fac_df, on="Faccao", how="left")
        tbl_fac["Meta Periodo"] = pd.to_numeric(tbl_fac["Meta Periodo"], errors="coerce").fillna(0)
        tbl_fac["Produzido"]    = pd.to_numeric(tbl_fac["Produzido"],    errors="coerce").fillna(0)
        tbl_fac["Ating. %"] = np.where(
            tbl_fac["Meta Periodo"] > 0,
            tbl_fac["Produzido"] / tbl_fac["Meta Periodo"] * 100, 0
        )
        tbl_fac["Saldo"] = tbl_fac["Produzido"] - tbl_fac["Meta Periodo"]
        tbl_fac = tbl_fac.sort_values("Ating. %", ascending=False)

        st.markdown("### Resumo por Facção / Produto")
        if meses_selecionados > 1:
            st.caption("ℹ️ **Meta Dia**: valor fixo quando igual em todos os meses selecionados; faixa *mín — máx* quando varia.")

        _fmt_int = lambda v: f"{v:,.0f}".replace(",", ".")
        tbl_display = tbl[[
            "Faccao", "Produto", "Produzido", "Dias",
            "Meta Dia", "Meta Periodo", "Ating. %", "Saldo", "Media/Dia"
        ]].rename(columns={
            "Faccao": "Facção",
            "Meta Periodo": "Meta Período",
            "Media/Dia": "Média/Dia",
        })
        st.dataframe(
            tbl_display.style.format({
                "Produzido": _fmt_int, "Meta Período": _fmt_int,
                "Saldo": _fmt_int, "Ating. %": "{:.1f}%", "Média/Dia": _fmt_int,
            }).background_gradient(subset=["Ating. %"], cmap="RdYlGn", vmin=50, vmax=120),
            width="stretch", hide_index=True,
        )

        st.markdown("")
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            if tem_meta:
                fig_ating = go.Figure()
                cores_at = [
                    "#22c55e" if a >= 100 else "#f97316" if a >= 80 else "#ef4444"
                    for a in tbl_fac["Ating. %"]
                ]
                fig_ating.add_bar(
                    y=tbl_fac["Faccao"], x=tbl_fac["Ating. %"], orientation="h",
                    marker_color=cores_at,
                    text=[f"{a:.1f}%" for a in tbl_fac["Ating. %"]], textposition="outside",
                )
                fig_ating.add_vline(x=100, line_dash="dash", line_color="#facc15")
                fig_ating.update_layout(
                    title="Atingimento por Facção (%)", xaxis_title="% Meta", yaxis_title="",
                    template="plotly_dark", separators=",.", margin=dict(t=50, l=100, r=40, b=40),
                )
                st.plotly_chart(fig_ating, width="stretch")
            else:
                fig_vol = px.bar(
                    tbl_fac.sort_values("Produzido", ascending=True),
                    y="Faccao", x="Produzido", orientation="h", text="Produzido",
                    color_discrete_sequence=[cor], title="Volume Produzido por Facção",
                    template="plotly_dark",
                )
                fig_vol.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                fig_vol.update_layout(separators=",.", margin=dict(t=50, l=100, r=40, b=40))
                st.plotly_chart(fig_vol, width="stretch")

        with col_f2:
            if tem_meta:
                fig_tree = px.treemap(
                    tbl_fac, path=["Faccao"], values="Produzido", color="Ating. %",
                    color_continuous_scale="RdYlGn", range_color=[50, 120],
                    title="Participação no Volume (cor = ating. %)", template="plotly_dark",
                )
            else:
                fig_tree = px.treemap(
                    tbl_fac, path=["Faccao"], values="Produzido", color="Produzido",
                    color_continuous_scale=[[0, "#1A3A4A"], [1, cor]],
                    title="Participação no Volume Total", template="plotly_dark",
                )
            fig_tree.update_layout(separators=",.", margin=dict(t=50, b=10))
            st.plotly_chart(fig_tree, width="stretch")

        prod_facc = (
            df_f.groupby(["Data", "Faccao"], as_index=False)["Quantidade"]
            .sum().sort_values("Data")
        )
        _CORES_FAC = [
            "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
            "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
        ]
        faccoes_no_dado = set(prod_facc["Faccao"].unique())
        faccoes = [f for f in sel_facs if f in faccoes_no_dado]
        cor_map = {f: _CORES_FAC[i % len(_CORES_FAC)] for i, f in enumerate(faccoes)}

        fig_linhas = go.Figure()
        for fac in faccoes:
            df_fac = prod_facc[prod_facc["Faccao"] == fac].sort_values("Data")
            fig_linhas.add_scatter(
                x=df_fac["Data"], y=df_fac["Quantidade"], mode="lines+markers",
                name=fac, legendgroup="Facção", legendgrouptitle_text="Facção",
                line=dict(color=cor_map[fac], width=2), marker=dict(size=5),
            )

        # Usar meta diária somada por facção (não média)
        # MÉDIO #17: Keep one (Faccao, Produto) pair to calculate meta sum per facção
        # This ensures each product's meta is counted only once in the sum
        meta_por_f = (
            df_f.drop_duplicates(subset=["Faccao", "Produto"])
            .groupby("Faccao")["Meta Diaria"].sum()
        )
        datas_range = [prod_facc["Data"].min(), prod_facc["Data"].max()]
        for fac in faccoes:
            meta_val = meta_por_f.get(fac, 0)
            if meta_val > 0:
                fig_linhas.add_scatter(
                    x=datas_range, y=[meta_val, meta_val], mode="lines",
                    name=f"Meta {fac}: {meta_val:,.0f}".replace(",", "."),
                    legendgroup="Meta", legendgrouptitle_text="Meta",
                    line=dict(dash="dash", width=2, color=cor_map.get(fac, "#FFFFFF")),
                    showlegend=True,
                )

        fig_linhas.update_layout(
            title="Evolução Diária por Facção", xaxis_title="Data", yaxis_title="Peças",
            xaxis=dict(tickformat="%d/%m/%Y"),
            legend=dict(orientation="v", x=1.02, y=1, groupclick="toggleitem"),
            margin=dict(t=50, b=60, r=200), template="plotly_dark", separators=",.",
        )
        st.plotly_chart(fig_linhas, width="stretch")

    # ─ tab 3
    with tab_rank:
        col_r1, col_r2 = st.columns(2)

        with col_r1:
            st.markdown("### Top 5 Dias Mais Produtivos")
            top5 = df_f.groupby("Data", as_index=False)["Quantidade"].sum().nlargest(5, "Quantidade")
            top5["DataFmt"] = top5["Data"].dt.strftime("%d/%m/%Y")
            for i, row in enumerate(top5.itertuples(), 1):
                medal = ["1.", "2.", "3."][i - 1] if i <= 3 else f"  {i}."
                st.markdown(f"**{medal} {row.DataFmt}** - {fmt_br(row.Quantidade)} peças")

        with col_r2:
            st.markdown("### Top 5 Dias Menos Produtivos")
            bot5 = df_f.groupby("Data", as_index=False)["Quantidade"].sum().nsmallest(5, "Quantidade")
            bot5["DataFmt"] = bot5["Data"].dt.strftime("%d/%m/%Y")
            for i, row in enumerate(bot5.itertuples(), 1):
                st.markdown(f"**{i}. {row.DataFmt}** - {fmt_br(row.Quantidade)} peças")

        st.markdown("---")
        st.markdown("### Facções com Produção Abaixo de 70% da Meta")
        if tem_meta:
            alerta = tbl_fac[tbl_fac["Ating. %"] < 70][
                ["Faccao", "Produzido", "Meta Periodo", "Ating. %", "Saldo"]
            ]
            if alerta.empty:
                st.success("Nenhuma facção abaixo de 70% no período selecionado!")
            else:
                alerta = alerta.rename(columns={"Faccao": "Facção", "Meta Periodo": "Meta Período"})
                st.dataframe(
                    alerta.style.format({
                        "Produzido": _fmt_int, "Meta Período": _fmt_int,
                        "Ating. %": "{:.1f}%", "Saldo": _fmt_int,
                    }).map(lambda _: "color: #ef4444", subset=["Ating. %"]),
                    width="stretch", hide_index=True,
                )
        else:
            st.info("Alertas de meta serão exibidos quando a meta for cadastrada na planilha.")

        st.markdown("---")
        st.markdown("### Heatmap - Produção Semanal por Facção")
        heat = df_f.pivot_table(
            index="Faccao", columns="Semana", values="Quantidade", aggfunc="sum"
        ).fillna(0)
        fig_heat = px.imshow(
            heat, aspect="auto", color_continuous_scale="YlGn",
            labels=dict(x="Semana", y="Facção", color="Peças"), template="plotly_dark",
        )
        fig_heat.update_layout(separators=",.", margin=dict(t=20, b=40))
        st.plotly_chart(fig_heat, width="stretch")

    # ─ tab 4
    with tab_dados:
        st.markdown("### Base Filtrada")
        df_view = df_f[["Data", "Faccao", "Produto", "Quantidade", "Meta Diaria"]].copy()
        df_view = df_view.sort_values(["Data", "Faccao"], ascending=[False, True])
        df_view["Data"] = df_view["Data"].dt.strftime("%d/%m/%Y")
        df_view = df_view.rename(columns={"Faccao": "Facção", "Meta Diaria": "Meta Diária"})
        _fmt_int = lambda v: f"{v:,.0f}".replace(",", ".") if pd.notna(v) and v is not None else "-"
        st.dataframe(
            df_view.reset_index(drop=True).style.format({
                "Quantidade": _fmt_int, "Meta Diária": _fmt_int,
            }),
            width="stretch", height=500,
        )
        csv = df_f.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar CSV filtrado", csv,
            file_name=f"producao_{empresa.lower()}_filtrada.csv",
            mime="text/csv",
        )

# ─
# POR CLIENTE — dashboard de Produção Geral existente (sem alteração de lógica)
# ─
def render_por_cliente():
    all_data = load_all_data()

    if not all_data:
        st.error("Não foi possível carregar os dados da planilha.")
        st.info("Verifique se o arquivo 'planilha_producao.xlsx' está disponível "
                "ou se a planilha do Google Sheets está acessível.")
        return

    empresa = st.query_params.get("empresa", None)

    if empresa and empresa in all_data:
        render_company(empresa, all_data[empresa], all_data)
    else:
        render_home(all_data)

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
        if screen == 'por_cliente':
            if st.button("← Tipo de Análise", key="prod_sb_back_cli", use_container_width=True):
                _go_prod('analysis_type')
        elif screen == 'colaborador_type':
            if st.button("← Tipo de Análise", key="prod_sb_back_colab", use_container_width=True):
                _go_prod('analysis_type')
        elif screen in ('interno', 'externo'):
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
                Acompanhamento da produção por empresa/cliente, com metas diárias,
                evolução e ranking — visão multi-empresa.
            </div>
            <div class="rc-tags">
                <span class="rc-tag">Multi-empresa</span>
                <span class="rc-tag">Metas</span>
                <span class="rc-tag">Evolução</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Dashboard  →", key="btn_por_cliente", use_container_width=True):
            _go_prod('por_cliente')

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
        <h1 class="page-title">Interno ou <span class="accent">Externo</span></h1>
        <p class="page-subtitle">Escolha o grupo de colaboradores para visualizar o painel</p>
    </div>
    <div class="page-divider"></div>
    """, unsafe_allow_html=True)

    _, c1, c2, _ = st.columns([0.5, 3, 3, 0.5])
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
        <div class="region-card disabled" style="--rc-a:#3D2817; --rc-b:#D97706; --rc-accent:#FFA726;">
            <div class="rc-icon">🚚</div>
            <div class="rc-label">Colaboradores · Externos</div>
            <div class="rc-title">Externo</div>
            <div class="rc-desc">
                Produção dos prestadores/facções externos.
                Em construção — planilhas serão integradas em breve.
            </div>
            <div class="rc-tags">
                <span class="rc-tag-soon">🚧 Em breve</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Externo  →", key="btn_externo", use_container_width=True):
            _go_prod('externo')

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("← Voltar ao Tipo de Análise", key="prod_back_type_colab", use_container_width=True):
            _go_prod('analysis_type')

def _screen_externo():
    st.markdown("""
    <div class="breadcrumb">
        <span class="bc-link">Análise de Produção</span>
        <span class="bc-sep">›</span>
        <span class="bc-link">Por Colaborador</span>
        <span class="bc-sep">›</span>
        <span class="bc-active">Externo</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:3.5rem; margin-bottom:16px;">🚧</div>
        <h2 style="color:#FFFFFF; font-family:'Sora',sans-serif; font-weight:800;">Em breve</h2>
        <p style="color:#A0A0A0; max-width:520px; margin:10px auto; line-height:1.6;">
            O painel de produção dos colaboradores <b>externos</b> (prestadores/facções)
            está sendo construído. As planilhas serão integradas em breve.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_back, *_ = st.columns([2, 5])
    with col_back:
        if st.button("← Voltar a Por Colaborador", key="prod_back_colab_ext", use_container_width=True):
            _go_prod('colaborador_type')

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
    df = load_interno_unidade(chave)
    if df.empty:
        st.warning(f"⚠️ Sem dados disponíveis para {cfg['label']}.")
        return

    dmin, dmax = df["DATA"].min().date(), df["DATA"].max().date()

    # ── Filtros ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        ini = st.date_input("De", value=dmin, min_value=dmin, max_value=dmax, key=f"ini_{chave}")
    with c2:
        fim = st.date_input("Até", value=dmax, min_value=dmin, max_value=dmax, key=f"fim_{chave}")
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
    elif screen == 'colaborador_type':
        _screen_colaborador_type()
    elif screen == 'interno':
        _screen_interno()
    elif screen == 'externo':
        _screen_externo()
    else:  # 'por_cliente' — dashboard de Produção Geral existente
        st.markdown("""
        <div class="breadcrumb">
            <span class="bc-link">Análise de Produção</span>
            <span class="bc-sep">›</span>
            <span class="bc-active">Por Cliente</span>
        </div>
        """, unsafe_allow_html=True)
        render_por_cliente()

if __name__ == "__main__":
    main()