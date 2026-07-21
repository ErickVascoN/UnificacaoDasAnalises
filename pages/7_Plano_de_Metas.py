"""
Painel de Metas — Análise de Metas / Previsão de Custos

Fonte de dados: a planilha de Plano de Metas (METAS_SHEET_ID) traz o
PREVISTO (por combinação Cliente × Prestador × Produto × Centro de Custo ×
Mês) e, quando alguém lança manualmente, o REALIZADO. Só que o REALIZADO
lançado à mão praticamente parou depois de fevereiro/2026 — de março em
diante quase toda combinação ficava com Realizado = 0, mesmo tendo produção
real. Por isso (pedido do usuário 20/07/2026), o Realizado agora é
cruzado com a produção real de facções (utils/faccao_loader.load_faccoes),
usando os mesmos aliases de nome já usados em utils/producao_unificada.py e
config/settings.py:FACCOES_FACCAO_ALIAS — a mesma "ponte" de nomes que
pages/5_Producao_Faccoes.py já usa pra casar facção × meta. Quando existe
Realizado lançado na própria planilha, ele prevalece (é o dado confirmado
manualmente); senão, usa o cruzado com produção; se nenhum dos dois casar
(prestador sem correspondência conhecida), fica marcado como tal, nunca
escondido como zero silencioso.

Escopo do cruzamento: a planilha de facções (load_faccoes) tem cobertura
completa a partir de junho/2026 — antes disso é a "planilha antiga" que
não é lida aqui (evita acoplar esta página ao carregamento pesado de
pages/2_Producao_Geral.py). Meses de fev–mai/2026 continuam dependendo só
do Realizado lançado manualmente.
"""
from __future__ import annotations

import io
import os
import sys
import re
import calendar
import unicodedata
from datetime import date, datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.global_ui import get_global_ui_css

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.settings import (
    METAS_SHEET_ID, METAS_GID, METAS_CACHE_TTL,
    FACCOES_FACCAO_ALIAS, FACCOES_PRODUTO_ALIAS, FACCOES_CLIENTE_ALIAS,
)
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button
from utils.feriados import eh_dia_util
from utils.normalize import normalize_text

# ─
# CONFIG DA PÁGINA
# ─
st.set_page_config(
    page_title="Plano de Metas / Previsão de Custos",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)
render_home_button()  # sempre visível, mesmo sem login

if st.session_state.get("auth_nivel") not in ("usuario", "admin"):
    st.error("🔒 Acesso restrito. Faça login na página inicial.")
    st.stop()

IS_ADMIN = st.session_state.get("auth_nivel") == "admin"

# ─
# CSS
# ─
st.markdown("""
<style>
    footer {visibility: hidden;}
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1C1C22 0%, #28282E 100%);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px; padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label { color:#FFF !important; font-size:0.78rem !important; font-weight:600 !important; text-transform:uppercase !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color:#FFF !important; font-weight:700 !important; font-size:1.7rem !important; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg,#111115 0%,#191920 100%); border-right:1px solid rgba(255,255,255,0.1); }
    section[data-testid="stSidebar"] * { color:#E0E0E0 !important; }
    .block-container { padding-top: 1.5rem; }
    .sec-header { color:#FFF; font-size:1.1rem; font-weight:700; margin:18px 0 8px; border-bottom:1px solid rgba(255,255,255,0.12); padding-bottom:6px; }
</style>
""", unsafe_allow_html=True)

# ─
# HELPERS
# ─
_MESES_PT_ABR = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
_MESES_PT_LABEL = {v: k.capitalize() for k, v in _MESES_PT_ABR.items()}

def _norm(s: str) -> str:
    """Uppercase + remove acentos + strip."""
    if not isinstance(s, str):
        s = str(s) if not pd.isna(s) else ""
    s = s.strip().upper()
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

# Dicionários de alias já normalizados (chave via normalize_text) — mesma
# "ponte" de nomes usada em pages/5_Producao_Faccoes.py e
# utils/producao_unificada.py pra casar a guia de metas com a produção real.
_ALIAS_FACCAO_N  = {normalize_text(k): v for k, v in FACCOES_FACCAO_ALIAS.items()}
_ALIAS_PRODUTO_N = {normalize_text(k): v for k, v in FACCOES_PRODUTO_ALIAS.items()}
_ALIAS_CLIENTE_N = {normalize_text(k): v for k, v in FACCOES_CLIENTE_ALIAS.items()}

def _canon_faccao(nome: str) -> str:
    """Nome de prestador/facção/centro de custo → forma canônica da produção."""
    n = normalize_text(nome)
    return normalize_text(_ALIAS_FACCAO_N.get(n, nome))

def _canon_produto(nome: str) -> str:
    n = normalize_text(nome)
    return normalize_text(_ALIAS_PRODUTO_N.get(n, nome))

def _canon_cliente(nome: str) -> str:
    """Mesma regra de utils/faccao_loader.load_faccoes: alias exato, senão
    qualquer nome contendo "NIAZI" vira NIAZITTEX."""
    n = normalize_text(nome)
    if n in _ALIAS_CLIENTE_N:
        return normalize_text(_ALIAS_CLIENTE_N[n])
    if "NIAZI" in n:
        return "NIAZITTEX"
    return n

def _parse_data_base(val) -> date | None:
    """Converte '1-mar.', '1-abr', '1-mai' → date(ano, mes, 1)."""
    if pd.isna(val):
        return None
    raw = str(val).strip().lower().replace(".", "")
    m = re.search(r"(\d+)[\-/\s]([a-zá-ú]+)", raw)
    if m:
        mes_str = m.group(2)[:3]
        mes_num = _MESES_PT_ABR.get(mes_str)
        if mes_num:
            hoje = date.today()
            ano = hoje.year
            try:
                return date(ano, mes_num, 1)
            except ValueError:
                return None
    return None

def _parse_num(val) -> float:
    """Converte '3.000', 'R$ 0,44', '#ERROR!' → float ou NaN."""
    if pd.isna(val):
        return float("nan")
    s = str(val).strip()
    if s in ("#ERROR!", "#VALOR!", "#NAME?", "-", ""):
        return float("nan")
    s = re.sub(r"[R$\s]", "", s).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")

def _dias_uteis_mes(ano: int, mes: int) -> int:
    """Conta dias úteis (seg–sex, exceto feriados nacionais/SP) no mês inteiro."""
    _, n_dias = calendar.monthrange(ano, mes)
    count = 0
    for d in range(1, n_dias + 1):
        if eh_dia_util(date(ano, mes, d)):
            count += 1
    return count

def _fmt_br(v: float, dec: int = 0) -> str:
    if np.isnan(v):
        return "—"
    txt = f"{v:,.{dec}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_reais(v: float) -> str:
    if np.isnan(v):
        return "—"
    return "R$ " + _fmt_br(v, 2)

# ─
# CARREGAMENTO DE DADOS
# ─
@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_csv(sheet_id: str, gid: str) -> pd.DataFrame:
    from utils.cache_manager import get_raw
    content = get_raw(sheet_id, gid, ttl=METAS_CACHE_TTL)
    if not content:
        st.warning(f"⚠ Não foi possível carregar planilha {sheet_id}/{gid} (sem cache disponível).")
        return pd.DataFrame()
    try:
        df = pd.read_csv(io.StringIO(content), dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all")
        return df
    except Exception as e:
        st.warning(f"Erro ao parsear planilha {sheet_id}/{gid}: {e}")
        return pd.DataFrame()

# ─
# PLANO DE METAS
# ─
@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_metas() -> pd.DataFrame:
    raw = _load_csv(METAS_SHEET_ID, METAS_GID)
    if raw.empty:
        return pd.DataFrame()

    # Normaliza colunas (remove espaços, upper)
    raw.columns = [c.strip().upper() for c in raw.columns]

    # Detecta colunas principais (tolerante a pequenas variações)
    col_map = {}
    for col in raw.columns:
        n = _norm(col)
        if n == "CLIENTE": col_map["CLIENTE"] = col
        elif "RESPONSAVEL" in n: col_map["RESPONSAVEL"] = col
        elif n == "ATIVIDADE": col_map["ATIVIDADE"] = col
        elif n == "TIPO": col_map["TIPO"] = col
        elif "CENTRO" in n and "CUSTO" in n: col_map["CENTRO_CUSTO"] = col
        elif n == "PRODUTO": col_map["PRODUTO"] = col
        elif "META" in n and "MES" in n: col_map["META_MES"] = col
        # Coluna renomeada de "META DIÁRIA" para "PRODUÇÃO DIÁRIA" na planilha
        # de junho/2026 (mesmo cálculo: Meta Mês ÷ dias úteis, só mudou o
        # rótulo) — aceita as duas variantes pra não quebrar se o nome mudar
        # de novo (reportado pelo usuário 15/07/2026).
        elif "DIARI" in n and ("META" in n or "PRODUCAO" in n): col_map["META_DIARIA"] = col
        elif "VLR" in n or "UNITARIO" in n: col_map["VLR_UNIT"] = col
        elif n == "CUSTO" and "FINAL" not in n: col_map["CUSTO"] = col
        elif "DATA" in n and "BASE" in n: col_map["DATA_BASE"] = col
        elif n == "STATUS": col_map["STATUS"] = col

    required = ["CLIENTE", "RESPONSAVEL", "PRODUTO", "CENTRO_CUSTO",
                "META_MES", "DATA_BASE", "STATUS"]
    missing = [r for r in required if r not in col_map]
    if missing:
        st.warning(f"Planilha de metas sem colunas: {missing}")
        return pd.DataFrame()

    df = pd.DataFrame()
    df["CLIENTE"]      = raw[col_map["CLIENTE"]].apply(_norm)
    df["RESPONSAVEL"]  = raw[col_map["RESPONSAVEL"]].apply(_norm)
    df["ATIVIDADE"]    = raw[col_map.get("ATIVIDADE", col_map["CLIENTE"])].apply(_norm) if "ATIVIDADE" in col_map else ""
    df["TIPO"]         = raw[col_map.get("TIPO", col_map["CLIENTE"])].apply(_norm) if "TIPO" in col_map else ""
    df["CENTRO_CUSTO"] = raw[col_map["CENTRO_CUSTO"]].apply(_norm)
    df["PRODUTO"]      = raw[col_map["PRODUTO"]].apply(_norm)
    df["META_MES"]     = raw[col_map["META_MES"]].apply(_parse_num)
    df["META_DIARIA"]  = raw[col_map.get("META_DIARIA", col_map["META_MES"])].apply(_parse_num) if "META_DIARIA" in col_map else float("nan")
    df["VLR_UNIT"]     = raw[col_map["VLR_UNIT"]].apply(_parse_num) if "VLR_UNIT" in col_map else float("nan")
    df["CUSTO"]        = raw[col_map["CUSTO"]].apply(_parse_num) if "CUSTO" in col_map else float("nan")
    df["DATA_BASE"]    = raw[col_map["DATA_BASE"]].apply(_parse_data_base)
    df["STATUS"]       = raw[col_map["STATUS"]].apply(_norm)

    # Guarda raw_responsavel e raw_cliente para exibição e para o gerador do próximo mês
    df["_RAW_RESPONSAVEL"] = raw[col_map["RESPONSAVEL"]].astype(str).str.strip()
    df["_RAW_CLIENTE"]     = raw[col_map["CLIENTE"]].astype(str).str.strip()
    df["_RAW_CENTRO"]      = raw[col_map["CENTRO_CUSTO"]].astype(str).str.strip()
    df["_RAW_PRODUTO"]     = raw[col_map["PRODUTO"]].astype(str).str.strip()
    df["_RAW_ATIVIDADE"]   = raw[col_map["ATIVIDADE"]].astype(str).str.strip() if "ATIVIDADE" in col_map else ""
    df["_RAW_TIPO"]        = raw[col_map["TIPO"]].astype(str).str.strip() if "TIPO" in col_map else ""
    df["_RAW_META_DIARIA"] = raw[col_map["META_DIARIA"]].astype(str).str.strip() if "META_DIARIA" in col_map else ""
    df["_RAW_VLR_UNIT"]    = raw[col_map["VLR_UNIT"]].astype(str).str.strip() if "VLR_UNIT" in col_map else ""
    df["_RAW_CUSTO"]       = raw[col_map["CUSTO"]].astype(str).str.strip() if "CUSTO" in col_map else ""
    df["_RAW_STATUS"]      = raw[col_map["STATUS"]].astype(str).str.strip()

    # Formas canônicas (mesmo espaço de nomes da produção real) — usadas só
    # pra cruzar com utils.faccao_loader.load_faccoes, nunca pra exibição.
    df["_RESP_CANON"]    = df["_RAW_RESPONSAVEL"].apply(_canon_faccao)
    df["_CC_CANON"]      = df["_RAW_CENTRO"].apply(_canon_faccao)
    df["_PRODUTO_CANON"] = df["_RAW_PRODUTO"].apply(_canon_produto)
    df["_CLIENTE_CANON"] = df["_RAW_CLIENTE"].apply(_canon_cliente)

    df = df.dropna(subset=["DATA_BASE"])
    df = df[df["RESPONSAVEL"].str.len() > 0]
    df = df[df["STATUS"].isin(["PREVISTO", "REALIZADO"])]
    return df

# ─
# PRODUÇÃO REAL (cruzamento) — utils/faccao_loader.load_faccoes, mesma fonte
# usada por pages/5_Producao_Faccoes.py. Cobertura completa a partir de
# junho/2026 (ver docstring do módulo).
# ─
@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_faccoes_renomeada() -> pd.DataFrame:
    """Base compartilhada: load_faccoes() com a mesma renomeação/filtro de
    utils.producao_unificada.load_producao_unificada (nome canônico atual de
    cada facção, prestadores inativos fora). Usada tanto pro cruzamento do
    Realizado (_load_producao_faccoes_canon) quanto pra estimativa de
    capacidade máxima (_load_producao_diaria_prestador)."""
    from utils.faccao_loader import load_faccoes
    from utils.producao_unificada import FACCAO_RENOMEADA, FACCAO_TYPOS, PRESTADORES_INATIVOS

    df = load_faccoes()
    if df is None or df.empty:
        return pd.DataFrame(columns=["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"])

    df = df.copy()
    df["FACCAO"] = df["FACCAO"].map(
        lambda f: FACCAO_RENOMEADA.get(FACCAO_TYPOS.get(f, f), FACCAO_TYPOS.get(f, f))
    )
    df = df[~df["FACCAO"].isin(PRESTADORES_INATIVOS)]
    return df[["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"]]


@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_producao_faccoes_canon() -> pd.DataFrame:
    df = _load_faccoes_renomeada()
    if df.empty:
        return pd.DataFrame(columns=["_FACCAO_CANON", "_PRODUTO_CANON", "_CLIENTE_CANON",
                                      "_ANO", "_MES", "QUANTIDADE"])

    df = df.copy()
    df["_FACCAO_CANON"]  = df["FACCAO"].apply(normalize_text)
    df["_PRODUTO_CANON"] = df["PRODUTO"].apply(normalize_text)   # load_faccoes já aplica FACCOES_PRODUTO_ALIAS
    df["_CLIENTE_CANON"] = df["CLIENTE"].apply(normalize_text)   # load_faccoes já aplica FACCOES_CLIENTE_ALIAS
    df["_ANO"] = pd.to_datetime(df["DATA"]).dt.year
    df["_MES"] = pd.to_datetime(df["DATA"]).dt.month
    return df[["_FACCAO_CANON", "_PRODUTO_CANON", "_CLIENTE_CANON", "_ANO", "_MES", "QUANTIDADE"]]


@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_producao_diaria_prestador() -> pd.DataFrame:
    """Produção diária total (somando todos os produtos/clientes do dia) por
    prestador canônico — base pra estimar a capacidade máxima real de cada
    um, ver _capacidade_maxima_por_prestador. Métrica diferente da
    Capacidade Disponível (Meta Mês − Realizado do mês corrente): aqui é
    "o que o prestador já provou dar conta" olhando o histórico inteiro,
    não o que falta pra bater a meta contratada deste mês."""
    df = _load_faccoes_renomeada()
    if df.empty:
        return pd.DataFrame(columns=["_FACCAO_CANON", "DATA", "QUANTIDADE"])
    df = df.copy()
    df["_FACCAO_CANON"] = df["FACCAO"].apply(normalize_text)
    return df.groupby(["_FACCAO_CANON", "DATA"], as_index=False)["QUANTIDADE"].sum()


def _capacidade_maxima_por_prestador(
    df_diario: pd.DataFrame, top_pct: float = 0.10, min_dias_top: int = 3,
) -> pd.DataFrame:
    """
    Capacidade máxima diária estimada = média dos melhores dias de cada
    prestador (top 10% dos dias com produção registrada, mínimo 3 dias, ou
    todos se tiver menos histórico que isso).

    Por quê essa fórmula (escolha de analista, pedido do usuário
    20/07/2026): pico isolado (1 melhor dia) é ruidoso — um dia atípico
    (ajuda pontual, erro de lançamento) infla a estimativa. Média geral de
    todos os dias sub-representa o potencial — mistura dias fracos/parados
    com dias de ritmo pleno. A média dos melhores dias captura "o que o
    prestador entrega quando está no embalo", sem depender de um único dia.
    Exemplo motivador: Carol tem Meta Diária de 7.000, mas se ela produz
    8.500+ em vários dos seus melhores dias, ela comporta mais meta do que
    a contratada hoje.
    """
    cols = ["_FACCAO_CANON", "CAP_DIA_ESTIMADA", "N_DIAS_HISTORICO"]
    if df_diario.empty:
        return pd.DataFrame(columns=cols)
    linhas = []
    for facao, g in df_diario.groupby("_FACCAO_CANON"):
        valores = g["QUANTIDADE"].sort_values(ascending=False).tolist()
        n = len(valores)
        k = min(max(min_dias_top, int(np.ceil(n * top_pct))), n)
        linhas.append({
            "_FACCAO_CANON": facao,
            "CAP_DIA_ESTIMADA": float(np.mean(valores[:k])),
            "N_DIAS_HISTORICO": n,
        })
    return pd.DataFrame(linhas, columns=cols)

# ─
# CÁLCULO DE INDICADORES
# ─
def _calcular_indicadores(
    df_prev: pd.DataFrame, df_real_mes: pd.DataFrame,
    df_producao: pd.DataFrame, ano_mes: date,
) -> pd.DataFrame:
    """
    Para cada linha PREVISTO, o Realizado vem de duas fontes, nessa ordem
    de prioridade:
      1) REALIZADO lançado manualmente na própria planilha de metas (mesma
         combinação Cliente × Prestador × Produto × Centro de Custo, mesmo
         mês) — quando existe, é o dado confirmado, prevalece.
      2) Produção real cruzada via utils.faccao_loader.load_faccoes, casando
         nome de Prestador/Centro de Custo (via FACCOES_FACCAO_ALIAS) ×
         Produto × Cliente × mês/ano.
    Quando nenhuma das duas casa, o Realizado fica 0 e REALIZADO_FONTE
    marca "Sem correspondência" — nunca escondido como se fosse 100% de
    capacidade disponível real.
    """
    chaves = ["RESPONSAVEL", "CLIENTE", "PRODUTO", "CENTRO_CUSTO"]
    if df_real_mes.empty:
        real_map: dict = {}
    else:
        real_map = (
            df_real_mes.groupby(chaves)["META_MES"].sum().to_dict()
        )

    ano_ref, mes_ref = ano_mes.year, ano_mes.month
    if df_producao is None or df_producao.empty:
        prod_map: dict = {}
    else:
        df_prod_mes = df_producao[(df_producao["_ANO"] == ano_ref) & (df_producao["_MES"] == mes_ref)]
        prod_map = (
            df_prod_mes.groupby(["_FACCAO_CANON", "_PRODUTO_CANON", "_CLIENTE_CANON"])["QUANTIDADE"]
            .sum().to_dict()
        )

    rows = []
    for _, meta in df_prev.iterrows():
        resp, cli, prod, cc = meta["RESPONSAVEL"], meta["CLIENTE"], meta["PRODUTO"], meta["CENTRO_CUSTO"]
        meta_mes    = meta["META_MES"]
        meta_diaria = meta["META_DIARIA"]
        vlr_unit    = meta["VLR_UNIT"]
        custo_unit  = meta["CUSTO"]

        realizado_planilha = float(real_map.get((resp, cli, prod, cc), 0.0))

        # Cruzamento com produção real — tenta casar pelo Prestador (mais
        # específico) e, se não achar, pelo Centro de Custo.
        prod_n, cli_n = meta["_PRODUTO_CANON"], meta["_CLIENTE_CANON"]
        realizado_producao = float(prod_map.get((meta["_RESP_CANON"], prod_n, cli_n), 0.0))
        if realizado_producao == 0.0:
            realizado_producao = float(prod_map.get((meta["_CC_CANON"], prod_n, cli_n), 0.0))

        if realizado_planilha > 0:
            realizado = realizado_planilha
            fonte = "Lançado"
        elif realizado_producao > 0:
            realizado = realizado_producao
            fonte = "Produção"
        else:
            realizado = 0.0
            fonte = "Sem correspondência"

        pct_meta = (realizado / meta_mes * 100) if (not np.isnan(meta_mes) and meta_mes > 0) else float("nan")

        # Capacidade disponível — quanto da meta já comprometida (Meta Mês, que
        # é a própria capacidade contratada dessa combinação prestador×cliente×
        # produto) ainda não foi lançado como realizado. Nunca negativa.
        capacidade_disp = max(0.0, meta_mes - realizado) if not np.isnan(meta_mes) else float("nan")
        capacidade_disp_receita = capacidade_disp * vlr_unit if not np.isnan(vlr_unit) and not np.isnan(capacidade_disp) else float("nan")

        # Financeiro — Previsto (pela Meta) x Realizado (pelo que já foi
        # lançado como REALIZADO na própria planilha).
        receita_prev = meta_mes * vlr_unit  if (not np.isnan(meta_mes) and not np.isnan(vlr_unit)) else float("nan")
        custo_prev   = meta_mes * custo_unit if (not np.isnan(meta_mes) and not np.isnan(custo_unit)) else float("nan")
        receita_real = realizado * vlr_unit  if not np.isnan(vlr_unit) else float("nan")
        custo_real   = realizado * custo_unit if not np.isnan(custo_unit) else float("nan")
        margem_real  = receita_real - custo_real if (not np.isnan(receita_real) and not np.isnan(custo_real)) else float("nan")
        margem_prev  = receita_prev - custo_prev if (not np.isnan(receita_prev) and not np.isnan(custo_prev)) else float("nan")

        if np.isnan(pct_meta):
            status = "⚪"
        elif pct_meta >= 90:
            status = "🟢"
        elif pct_meta >= 60:
            status = "🟡"
        else:
            status = "🔴"

        rows.append({
            "CENTRO_CUSTO": cc,
            "RESPONSAVEL": meta["_RAW_RESPONSAVEL"],
            "CLIENTE": meta["_RAW_CLIENTE"],
            "PRODUTO": meta["_RAW_PRODUTO"],
            "META_MES": meta_mes,
            "META_DIARIA": meta_diaria,
            "REALIZADO": realizado,
            "REALIZADO_FONTE": fonte,
            "PCT_META": pct_meta,
            "CAPACIDADE_DISPONIVEL": capacidade_disp,
            "CAPACIDADE_DISPONIVEL_RECEITA": capacidade_disp_receita,
            "RECEITA_PREV": receita_prev,
            "CUSTO_PREV": custo_prev,
            "MARGEM_PREV": margem_prev,
            "RECEITA_REAL": receita_real,
            "CUSTO_REAL": custo_real,
            "MARGEM_REAL": margem_real,
            "VLR_UNIT": vlr_unit,
            "CUSTO_UNIT": custo_unit,
            "STATUS_ICON": status,
            "_RESP_NORM": resp,
            "_CLI_NORM": cli,
            "_PROD_NORM": prod,
            "_CC_NORM": cc,
            "_RESP_CANON": meta["_RESP_CANON"],
        })
    return pd.DataFrame(rows)

# ─
# GERADOR DE PLANO DO PRÓXIMO MÊS
# ─
def _gerar_proximo_mes_xlsx(
    df_prev: pd.DataFrame,
    df_indicadores: pd.DataFrame,
    ano_atual: int, mes_atual: int,
) -> bytes:
    """
    Gera Excel com estrutura idêntica ao plano de metas, com META MÊS e
    META DIÁRIA recalibradas pelo Realizado do mês atual (lançado na
    planilha ou cruzado com produção real, ver _calcular_indicadores);
    combinações sem nenhum Realizado mantêm a meta original.
    """
    prox_mes = mes_atual % 12 + 1
    prox_ano = ano_atual + (1 if mes_atual == 12 else 0)
    dias_uteis_prox = _dias_uteis_mes(prox_ano, prox_mes)

    abr_mes = _MESES_PT_LABEL.get(prox_mes, str(prox_mes))
    label_data_base = f"1-{abr_mes.lower()}."

    out_rows = []
    for _, meta in df_prev.iterrows():
        match = df_indicadores[
            (df_indicadores["_RESP_NORM"] == meta["RESPONSAVEL"]) &
            (df_indicadores["_CLI_NORM"] == meta["CLIENTE"]) &
            (df_indicadores["_PROD_NORM"] == meta["PRODUTO"]) &
            (df_indicadores["_CC_NORM"] == meta["CENTRO_CUSTO"])
        ]
        realizado = float(match.iloc[0]["REALIZADO"]) if not match.empty else 0.0

        if realizado > 0:
            nova_meta_mes    = round(realizado)
            nova_meta_diaria = round(realizado / max(dias_uteis_prox, 1))
        else:
            # Sem Realizado lançado ainda → mantém metas originais
            nova_meta_mes    = meta["META_MES"] if not np.isnan(meta["META_MES"]) else 0
            nova_meta_diaria = meta["META_DIARIA"] if not np.isnan(meta["META_DIARIA"]) else nova_meta_mes

        vlr_unit   = meta["VLR_UNIT"]
        custo_unit = meta["CUSTO"]
        preco_final = nova_meta_mes * vlr_unit   if not np.isnan(vlr_unit)   else float("nan")
        custo_final = nova_meta_mes * custo_unit if not np.isnan(custo_unit) else float("nan")

        out_rows.append({
            "CLIENTE":       meta["_RAW_CLIENTE"],
            "RESPONSÁVEL":   meta["_RAW_RESPONSAVEL"],
            "ATIVIDADE":     meta["_RAW_ATIVIDADE"],
            "TIPO":          meta["_RAW_TIPO"],
            "CENTRO DE CUSTO": meta["_RAW_CENTRO"],
            "PRODUTO":       meta["_RAW_PRODUTO"],
            "META MÊS":      nova_meta_mes,
            "META DIÁRIA":   nova_meta_diaria,
            "VLR UNITARIO":  vlr_unit if not np.isnan(vlr_unit) else "",
            "CUSTO":         custo_unit if not np.isnan(custo_unit) else "",
            "PREÇO FINAL":   preco_final if not np.isnan(preco_final) else "",
            "CUSTO FINAL":   custo_final if not np.isnan(custo_final) else "",
            "DATA BASE":     label_data_base,
            "STATUS":        "PREVISTO",
        })

    df_out = pd.DataFrame(out_rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Plano de Metas")
    buf.seek(0)
    return buf.getvalue()

# ─
# RENDERIZAÇÃO
# ─
def main():
    hoje = date.today()

    # cabeçalho
    st.markdown("<h1 style='color:#FFF;font-size:2rem;margin-bottom:4px;'>🎯 Painel de Metas</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#A0A0A0;margin-bottom:20px;'>Distribuição de demanda e análise de capacidade — "
        "Meta Restante · Capacidade Máxima Estimada · Metas por Cliente/Prestador/Centro de Custo/Produto · "
        "Previsto x Realizado (lançado ou cruzado com a produção real) · Previsão de Custos</p>",
        unsafe_allow_html=True,
    )
    render_filtros_btn()

    # carrega metas + produção real (pra cruzamento do Realizado e pra
    # estimativa de capacidade máxima por prestador)
    with st.spinner("Carregando plano de metas..."):
        df_metas = _load_metas()
        df_producao = _load_producao_faccoes_canon()
        df_diario_prestador = _load_producao_diaria_prestador()
        df_cap_maxima = _capacidade_maxima_por_prestador(df_diario_prestador)

    if df_metas.empty:
        st.error("Não foi possível carregar a planilha de metas. Verifique o acesso.")
        st.stop()

    # filtros
    meses_disponiveis = sorted(
        df_metas["DATA_BASE"].dropna().unique(),
        key=lambda d: (d.year, d.month),
    )
    # Padrão: o mês mais recente que já tem ALGUM dado real pra mostrar —
    # Realizado lançado na planilha OU produção cruzada no mês (ver
    # _load_producao_faccoes_canon). Evita abrir com tudo zerado só porque
    # o mês corrente não teve nada lançado à mão (reportado pelo usuário
    # 15/07/2026) — antes do cruzamento (20/07/2026) só considerava Lançado,
    # o que empurrava o padrão sempre pra fevereiro mesmo com meses mais
    # recentes já tendo produção real cruzável.
    meses_com_realizado = sorted(
        df_metas[df_metas["STATUS"] == "REALIZADO"]["DATA_BASE"].dropna().unique(),
        key=lambda d: (d.year, d.month),
    )
    meses_com_producao = set()
    if not df_producao.empty:
        meses_com_producao = {(int(a), int(m)) for a, m in df_producao[["_ANO", "_MES"]].drop_duplicates().itertuples(index=False)}
    meses_com_dado = sorted(
        {d for d in meses_disponiveis if d in meses_com_realizado or (d.year, d.month) in meses_com_producao},
        key=lambda d: (d.year, d.month),
    )
    mes_atual_disp = next(
        (d for d in meses_disponiveis if d.month == hoje.month and d.year == hoje.year), None
    )
    if mes_atual_disp is not None and mes_atual_disp in meses_com_dado:
        default_mes = mes_atual_disp
    elif meses_com_dado:
        default_mes = meses_com_dado[-1]
    else:
        default_mes = mes_atual_disp or (meses_disponiveis[-1] if meses_disponiveis else None)
    meses_labels = {d: f"{_MESES_PT_LABEL.get(d.month, d.month)}/{d.year}" for d in meses_disponiveis}

    with st.sidebar:
        st.markdown("### Filtros")
        mes_sel = st.selectbox(
            "Mês",
            options=meses_disponiveis,
            index=meses_disponiveis.index(default_mes) if default_mes in meses_disponiveis else 0,
            format_func=lambda d: meses_labels[d],
        )
        if mes_atual_disp is not None and mes_sel == mes_atual_disp and mes_atual_disp not in meses_com_dado and default_mes != mes_atual_disp:
            st.caption(
                f"ℹ️ {meses_labels[mes_atual_disp]} ainda não tem Realizado (lançado nem cruzado com "
                f"produção) — abrimos por padrão em {meses_labels[default_mes]}, o mês mais recente com dados."
            )
        df_mes = df_metas[df_metas["DATA_BASE"] == mes_sel]

        centros_disp = sorted(df_mes["CENTRO_CUSTO"].unique().tolist())
        centros_sel = st.multiselect("Centro de Custo", centros_disp, default=centros_disp)

        clientes_disp = sorted(df_mes["CLIENTE"].unique().tolist())
        clientes_sel = st.multiselect("Cliente", clientes_disp, default=clientes_disp)

        resp_disp = sorted(df_mes["RESPONSAVEL"].unique().tolist())
        resp_sel = st.multiselect("Prestador / Responsável", resp_disp, default=resp_disp)

    # Aplica filtros
    df_prev = df_mes[
        (df_mes["STATUS"] == "PREVISTO") &
        (df_mes["CENTRO_CUSTO"].isin(centros_sel)) &
        (df_mes["CLIENTE"].isin(clientes_sel)) &
        (df_mes["RESPONSAVEL"].isin(resp_sel))
    ].copy()

    df_real_mes = df_mes[df_mes["STATUS"] == "REALIZADO"].copy()

    if df_prev.empty:
        st.warning("Nenhuma meta PREVISTO encontrada para os filtros selecionados.")
        st.stop()

    df_ind = _calcular_indicadores(df_prev, df_real_mes, df_producao, mes_sel)

    # Diagnóstico (apenas Admin) — de onde vem o Realizado de cada combinação
    if IS_ADMIN:
        with st.sidebar.expander("🔍 Diagnóstico de Dados"):
            n_prev = len(df_ind)
            if n_prev:
                _fonte_counts = df_ind["REALIZADO_FONTE"].value_counts()
                st.caption(f"**PREVISTO no mês:** {n_prev} combinações")
                for _fonte, _n in _fonte_counts.items():
                    st.caption(f"**{_fonte}:** {_n} ({_n/n_prev*100:.0f}%)")
            else:
                st.caption("—")

    _n_sem_match = int((df_ind["REALIZADO_FONTE"] == "Sem correspondência").sum()) if not df_ind.empty else 0
    if not df_ind.empty and _n_sem_match == len(df_ind):
        st.info(
            "ℹ️ Nenhum Realizado encontrado para o mês selecionado — nem lançado na planilha, "
            "nem cruzado com a produção real — os indicadores abaixo mostram 100% de Capacidade "
            "Disponível até que haja algum dado."
        )
    elif _n_sem_match > 0:
        st.caption(
            f"⚠️ {_n_sem_match} de {len(df_ind)} combinações não têm Realizado (nem lançado, nem "
            f"produção cruzável — geralmente prestador sem correspondência conhecida ou mês fora da "
            f"cobertura da planilha de facções). Veja a aba Detalhado para identificar quais."
        )

    # ── KPIs — Produção ───────────────────────────────────────────────────────
    meta_total       = df_prev["META_MES"].sum(skipna=True)
    real_total       = df_ind["REALIZADO"].sum() if not df_ind.empty else 0.0
    capacidade_total = df_ind["CAPACIDADE_DISPONIVEL"].sum() if not df_ind.empty else 0.0
    pct_atingido     = (real_total / meta_total * 100) if meta_total > 0 else 0.0

    _n_lancado = int((df_ind["REALIZADO_FONTE"] == "Lançado").sum()) if not df_ind.empty else 0
    _n_producao = int((df_ind["REALIZADO_FONTE"] == "Produção").sum()) if not df_ind.empty else 0

    st.markdown("<div class='sec-header'>📦 Visão Geral do Mês — Produção</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Meta Total do Mês", _fmt_br(meta_total))
    c2.metric("Realizado", _fmt_br(real_total),
              delta=f"{pct_atingido:.1f}% da meta")
    c3.metric("Meta Restante do Mês", _fmt_br(capacidade_total),
              delta="ainda não realizado dentro da meta contratada")
    st.caption(
        f"Realizado = lançado manualmente na planilha quando existe ({_n_lancado} combinações), "
        f"senão cruzado com a produção real de facções ({_n_producao} combinações)."
    )

    # ── KPIs — Financeiro (Previsto x Realizado) ──────────────────────────────
    receita_prev_total = df_ind["RECEITA_PREV"].sum() if not df_ind.empty else 0.0
    custo_prev_total   = df_ind["CUSTO_PREV"].sum() if not df_ind.empty else 0.0
    receita_real_total = df_ind["RECEITA_REAL"].sum() if not df_ind.empty else 0.0
    custo_real_total   = df_ind["CUSTO_REAL"].sum() if not df_ind.empty else 0.0
    margem_prev_total  = receita_prev_total - custo_prev_total
    margem_real_total  = receita_real_total - custo_real_total

    st.markdown("<div class='sec-header'>💰 Visão Geral do Mês — Previsão de Custos</div>", unsafe_allow_html=True)
    st.caption(
        "Previsto = Meta Mês × Valor Unitário/Custo. Realizado = quantidade Realizada "
        "(lançada ou cruzada com produção, ver acima) × Valor Unitário/Custo."
    )
    df_fin_kpi = pd.DataFrame({
        "": ["Receita", "Custo", "Margem"],
        "Previsto (Meta)": [receita_prev_total, custo_prev_total, margem_prev_total],
        "Realizado": [receita_real_total, custo_real_total, margem_real_total],
    })
    for col in ["Previsto (Meta)", "Realizado"]:
        df_fin_kpi[col] = df_fin_kpi[col].apply(_fmt_reais)
    st.dataframe(df_fin_kpi, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Meta Restante do Mês — por Prestador ──────────────────────────────────
    # Antes chamada de "Capacidade Disponível" — renomeada (pedido do usuário
    # 20/07/2026) porque não mede capacidade física de produção, mede quanto
    # falta da META CONTRATADA. A capacidade real (o que o prestador consegue
    # produzir de fato) é a seção seguinte, calculada a partir do histórico.
    st.markdown("<div class='sec-header'>📉 Meta Restante do Mês — por Prestador</div>", unsafe_allow_html=True)
    st.caption(
        "Meta Restante = Meta Mês − Realizado (nunca negativa), somada por prestador em "
        "todos os clientes/produtos que ele atende. Mostra quanto da meta já CONTRATADA "
        "ainda não foi cumprido — não é a capacidade física do prestador (isso é a seção "
        "seguinte). Usar para saber quem ainda não bateu o que já foi combinado."
    )
    if not df_ind.empty:
        df_cap = df_ind.groupby("RESPONSAVEL", as_index=False).agg(
            META_MES=("META_MES", "sum"),
            REALIZADO=("REALIZADO", "sum"),
            CAPACIDADE_DISPONIVEL=("CAPACIDADE_DISPONIVEL", "sum"),
            CAPACIDADE_DISPONIVEL_RECEITA=("CAPACIDADE_DISPONIVEL_RECEITA", "sum"),
            _RESP_CANON=("_RESP_CANON", "first"),
        )
        df_cap_plot = df_cap.sort_values("CAPACIDADE_DISPONIVEL", ascending=True)

        fig_cap = go.Figure(go.Bar(
            y=df_cap_plot["RESPONSAVEL"], x=df_cap_plot["CAPACIDADE_DISPONIVEL"],
            orientation="h", marker_color="#FFA726",
            text=[_fmt_br(v) for v in df_cap_plot["CAPACIDADE_DISPONIVEL"]],
            textposition="outside",
        ))
        fig_cap.update_layout(
            height=max(320, 28 * len(df_cap_plot)),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"), xaxis=dict(gridcolor="#2D3748", title="Peças"),
            yaxis=dict(gridcolor="#2D3748"), margin=dict(l=10, r=10, t=10, b=10),
            separators=",.",
        )
        st.plotly_chart(fig_cap, use_container_width=True)

        tbl_cap = df_cap.sort_values("CAPACIDADE_DISPONIVEL", ascending=False).copy()
        _total_cap = {
            "RESPONSAVEL": "TOTAL",
            "META_MES": tbl_cap["META_MES"].sum(),
            "REALIZADO": tbl_cap["REALIZADO"].sum(),
            "CAPACIDADE_DISPONIVEL": tbl_cap["CAPACIDADE_DISPONIVEL"].sum(),
            "CAPACIDADE_DISPONIVEL_RECEITA": tbl_cap["CAPACIDADE_DISPONIVEL_RECEITA"].sum(),
        }
        tbl_cap_show = pd.concat([tbl_cap.drop(columns=["_RESP_CANON"]), pd.DataFrame([_total_cap])], ignore_index=True)
        tbl_cap_show["PCT_OCUPADO"] = tbl_cap_show.apply(
            lambda r: f"{(r['REALIZADO']/r['META_MES']*100):.1f}%" if r["META_MES"] > 0 else "—", axis=1
        )
        tbl_cap_show["CAPACIDADE_DISPONIVEL_RECEITA"] = tbl_cap_show["CAPACIDADE_DISPONIVEL_RECEITA"].apply(_fmt_reais)
        for col in ["META_MES", "REALIZADO", "CAPACIDADE_DISPONIVEL"]:
            tbl_cap_show[col] = tbl_cap_show[col].apply(_fmt_br)
        tbl_cap_show = tbl_cap_show[["RESPONSAVEL", "META_MES", "REALIZADO", "CAPACIDADE_DISPONIVEL",
                                     "CAPACIDADE_DISPONIVEL_RECEITA", "PCT_OCUPADO"]]
        tbl_cap_show.columns = ["Prestador", "Meta Mês", "Realizado", "Meta Restante",
                                 "Meta Restante (R$)", "% Já Ocupado"]
        st.dataframe(tbl_cap_show, use_container_width=True, hide_index=True)
    else:
        df_cap = pd.DataFrame()
        st.info("Sem dados de indicadores calculados.")

    st.markdown("---")

    # ── Capacidade Máxima Estimada — por Prestador ────────────────────────────
    st.markdown("<div class='sec-header'>🚀 Capacidade Máxima Estimada — por Prestador</div>", unsafe_allow_html=True)
    st.caption(
        "O quanto o prestador já PROVOU dar conta, olhando o histórico real de produção "
        "(utils.faccao_loader.load_faccoes, desde jun/2026) — não a meta contratada. "
        "Capacidade Máxima Diária = média dos melhores dias de produção dele (top 10% dos "
        "dias com produção registrada, mínimo 3 dias). Capacidade Máxima do Mês = isso × "
        "dias úteis do mês selecionado. Margem de Crescimento = Capacidade Máxima do Mês − "
        "Meta Mês atual: positivo indica que o prestador comporta mais meta do que a "
        "contratada hoje; negativo indica que a meta já está no teto (ou acima) do que ele "
        "já demonstrou produzir."
    )
    if not df_cap.empty and not df_cap_maxima.empty:
        dias_uteis_sel = _dias_uteis_mes(mes_sel.year, mes_sel.month)
        df_crescimento = df_cap.merge(
            df_cap_maxima, left_on="_RESP_CANON", right_on="_FACCAO_CANON", how="left",
        )
        df_crescimento["CAP_MES_ESTIMADA"] = df_crescimento["CAP_DIA_ESTIMADA"] * dias_uteis_sel
        df_crescimento["MARGEM_CRESCIMENTO"] = df_crescimento["CAP_MES_ESTIMADA"] - df_crescimento["META_MES"]
        # Histórico curto demais (< 5 dias) => estimativa pouco confiável, mas
        # ainda mostrada (marcada) em vez de escondida.
        df_crescimento["_BAIXA_CONFIANCA"] = df_crescimento["N_DIAS_HISTORICO"].fillna(0) < 5

        df_cresc_plot = df_crescimento.dropna(subset=["CAP_MES_ESTIMADA"]).sort_values("MARGEM_CRESCIMENTO", ascending=True)
        if not df_cresc_plot.empty:
            fig_cresc = go.Figure()
            fig_cresc.add_bar(name="Meta Mês (contratada)", y=df_cresc_plot["RESPONSAVEL"], x=df_cresc_plot["META_MES"],
                              orientation="h", marker_color="#5C677D")
            fig_cresc.add_bar(name="Capacidade Máxima Estimada", y=df_cresc_plot["RESPONSAVEL"], x=df_cresc_plot["CAP_MES_ESTIMADA"],
                              orientation="h", marker_color="#4ECDC4")
            fig_cresc.update_layout(
                barmode="group", height=max(320, 30 * len(df_cresc_plot)),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#CBD5E0"), xaxis=dict(gridcolor="#2D3748", title="Peças/mês"),
                yaxis=dict(gridcolor="#2D3748"),
                legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.12),
                margin=dict(l=10, r=10, t=10, b=10), separators=",.",
            )
            st.plotly_chart(fig_cresc, use_container_width=True)

        tbl_cresc = df_crescimento.sort_values("MARGEM_CRESCIMENTO", ascending=False).copy()
        tbl_cresc["_CONFIANCA"] = tbl_cresc["_BAIXA_CONFIANCA"].map(
            lambda b: "⚠️ pouco histórico" if b else "✔"
        )
        tbl_cresc.loc[tbl_cresc["CAP_MES_ESTIMADA"].isna(), "_CONFIANCA"] = "— sem histórico"
        tbl_cresc["N_DIAS_HISTORICO"] = tbl_cresc["N_DIAS_HISTORICO"].fillna(0).astype(int)
        for col in ["META_MES", "CAP_DIA_ESTIMADA", "CAP_MES_ESTIMADA", "MARGEM_CRESCIMENTO"]:
            tbl_cresc[col] = tbl_cresc[col].apply(lambda v: _fmt_br(v) if not np.isnan(v) else "—")
        tbl_cresc = tbl_cresc[["RESPONSAVEL", "META_MES", "CAP_DIA_ESTIMADA", "CAP_MES_ESTIMADA",
                               "MARGEM_CRESCIMENTO", "N_DIAS_HISTORICO", "_CONFIANCA"]]
        tbl_cresc.columns = ["Prestador", "Meta Mês", "Cap. Máxima Diária (estim.)", "Cap. Máxima do Mês (estim.)",
                             "Margem de Crescimento", "Dias no Histórico", "Confiança"]
        st.dataframe(tbl_cresc, use_container_width=True, hide_index=True)
    else:
        st.info("Sem histórico de produção suficiente pra estimar capacidade máxima.")

    st.markdown("---")

    # ── Metas — Cliente × Prestador × Centro de Custo × Produto ──────────────
    st.markdown("<div class='sec-header'>📋 Metas — por Cliente, Prestador, Centro de Custo e Produto</div>", unsafe_allow_html=True)

    def _render_quebra(dim_col: str) -> None:
        if df_ind.empty:
            st.info("Sem dados de indicadores calculados.")
            return
        df_g = df_ind.groupby(dim_col, as_index=False).agg(
            META_MES=("META_MES", "sum"),
            REALIZADO=("REALIZADO", "sum"),
            CAPACIDADE_DISPONIVEL=("CAPACIDADE_DISPONIVEL", "sum"),
        ).sort_values("META_MES", ascending=False)

        fig = go.Figure()
        fig.add_bar(name="Meta Mês", x=df_g[dim_col], y=df_g["META_MES"], marker_color="#5C677D")
        fig.add_bar(name="Realizado", x=df_g[dim_col], y=df_g["REALIZADO"], marker_color="#4ECDC4")
        fig.update_layout(
            barmode="group", height=340,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"), xaxis=dict(gridcolor="#2D3748"),
            yaxis=dict(gridcolor="#2D3748", title="Peças"),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2),
            margin=dict(l=10, r=10, t=10, b=10), separators=",.",
        )
        st.plotly_chart(fig, use_container_width=True)

        tbl = df_g.copy()
        _total = {
            dim_col: "TOTAL",
            "META_MES": tbl["META_MES"].sum(),
            "REALIZADO": tbl["REALIZADO"].sum(),
            "CAPACIDADE_DISPONIVEL": tbl["CAPACIDADE_DISPONIVEL"].sum(),
        }
        tbl = pd.concat([tbl, pd.DataFrame([_total])], ignore_index=True)
        tbl["PCT_META"] = tbl.apply(
            lambda r: r["REALIZADO"] / r["META_MES"] * 100 if r["META_MES"] > 0 else float("nan"), axis=1
        )
        tbl["PCT_META"] = tbl["PCT_META"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "—")
        for col in ["META_MES", "REALIZADO", "CAPACIDADE_DISPONIVEL"]:
            tbl[col] = tbl[col].apply(lambda v: _fmt_br(v) if not np.isnan(v) else "—")
        tbl.columns = [dim_col, "Meta Mês", "Realizado", "Meta Restante", "% Meta"]
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    tab_cli, tab_resp, tab_cc, tab_prod, tab_det = st.tabs(
        ["👤 Por Cliente", "🧵 Por Prestador", "🏭 Por Centro de Custo", "📦 Por Produto", "🔍 Detalhado"]
    )
    with tab_cli:
        _render_quebra("CLIENTE")
    with tab_resp:
        _render_quebra("RESPONSAVEL")
    with tab_cc:
        _render_quebra("CENTRO_CUSTO")
    with tab_prod:
        _render_quebra("PRODUTO")
    with tab_det:
        if not df_ind.empty:
            st.caption(
                "Coluna **Fonte**: Lançado = Realizado confirmado manualmente na planilha · "
                "Produção = cruzado com a produção real de facções · "
                "Sem correspondência = prestador/produto/cliente sem casamento automático "
                "(Realizado mostrado como 0, não é necessariamente zero real)."
            )
            tbl_det = df_ind[[
                "STATUS_ICON", "CENTRO_CUSTO", "RESPONSAVEL", "CLIENTE", "PRODUTO",
                "META_MES", "META_DIARIA", "REALIZADO", "REALIZADO_FONTE", "PCT_META", "CAPACIDADE_DISPONIVEL",
            ]].copy()
            tbl_det = tbl_det.sort_values(["CENTRO_CUSTO", "RESPONSAVEL"])
            _meta_total_det = tbl_det["META_MES"].sum()
            _real_total_det = tbl_det["REALIZADO"].sum()
            _total_det = {
                "STATUS_ICON": "", "CENTRO_CUSTO": "TOTAL", "RESPONSAVEL": "", "CLIENTE": "", "PRODUTO": "",
                "META_MES": _meta_total_det,
                "META_DIARIA": float("nan"),  # soma de taxas diárias de linhas diferentes não faz sentido
                "REALIZADO": _real_total_det,
                "REALIZADO_FONTE": "",
                "PCT_META": (_real_total_det / _meta_total_det * 100) if _meta_total_det > 0 else float("nan"),
                "CAPACIDADE_DISPONIVEL": tbl_det["CAPACIDADE_DISPONIVEL"].sum(),
            }
            tbl_det = pd.concat([tbl_det, pd.DataFrame([_total_det])], ignore_index=True)
            tbl_det["PCT_META"] = tbl_det["PCT_META"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "—")
            for col in ["META_MES", "META_DIARIA", "REALIZADO", "CAPACIDADE_DISPONIVEL"]:
                tbl_det[col] = tbl_det[col].apply(lambda v: _fmt_br(v) if not np.isnan(v) else "—")
            tbl_det.columns = [
                "⬤", "Centro Custo", "Prestador", "Cliente", "Produto",
                "Meta Mês", "Meta Diária", "Realizado", "Fonte", "% Meta", "Meta Restante",
            ]
            st.dataframe(tbl_det, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados de indicadores calculados.")

    st.markdown("---")

    # ── Previsão de Custos — Detalhamento por Cliente ─────────────────────────
    st.markdown("<div class='sec-header'>💰 Previsão de Custos — Detalhamento por Cliente</div>", unsafe_allow_html=True)
    st.caption(
        "Receita/Custo Realizado usam o Realizado (lançado ou cruzado com produção, "
        "ver aba Detalhado acima); Previsto usa a Meta."
    )
    if not df_ind.empty:
        df_fin = df_ind.groupby("CLIENTE", as_index=False).agg(
            RECEITA_PREV=("RECEITA_PREV", "sum"),
            CUSTO_PREV=("CUSTO_PREV", "sum"),
            RECEITA_REAL=("RECEITA_REAL", "sum"),
            CUSTO_REAL=("CUSTO_REAL", "sum"),
        )
        df_fin["MARGEM_PREV"] = df_fin["RECEITA_PREV"] - df_fin["CUSTO_PREV"]
        df_fin["MARGEM_REAL"] = df_fin["RECEITA_REAL"] - df_fin["CUSTO_REAL"]
        df_fin = df_fin.sort_values("RECEITA_PREV", ascending=False)

        fig_fin = go.Figure()
        fig_fin.add_bar(name="Receita Prevista", x=df_fin["CLIENTE"], y=df_fin["RECEITA_PREV"],
                        marker_color="#4ECDC4", opacity=0.4)
        fig_fin.add_bar(name="Receita Realizada", x=df_fin["CLIENTE"], y=df_fin["RECEITA_REAL"], marker_color="#4ECDC4")
        fig_fin.add_bar(name="Custo Realizado", x=df_fin["CLIENTE"], y=df_fin["CUSTO_REAL"], marker_color="#F87171")
        fig_fin.add_scatter(
            name="Margem Realizada", x=df_fin["CLIENTE"], y=df_fin["MARGEM_REAL"],
            mode="lines+markers", line=dict(color="#FFA726", width=2.5),
        )
        fig_fin.update_layout(
            barmode="group", height=360,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"), xaxis=dict(gridcolor="#2D3748"),
            yaxis=dict(gridcolor="#2D3748", title="R$", tickprefix="R$ "),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2),
            margin=dict(l=10, r=10, t=10, b=10), separators=",.",
        )
        st.plotly_chart(fig_fin, use_container_width=True)

        tbl_fin = df_fin[[
            "CLIENTE", "RECEITA_PREV", "CUSTO_PREV", "MARGEM_PREV",
            "RECEITA_REAL", "CUSTO_REAL", "MARGEM_REAL",
        ]].copy()
        _total_fin = {"CLIENTE": "TOTAL"}
        for _c in tbl_fin.columns[1:]:
            _total_fin[_c] = tbl_fin[_c].sum()
        tbl_fin = pd.concat([tbl_fin, pd.DataFrame([_total_fin])], ignore_index=True)
        for col in tbl_fin.columns[1:]:
            tbl_fin[col] = tbl_fin[col].apply(_fmt_reais)
        tbl_fin.columns = [
            "Cliente", "Receita Prevista", "Custo Previsto", "Margem Prevista",
            "Receita Realizada", "Custo Realizado", "Margem Realizada",
        ]
        st.dataframe(tbl_fin, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de indicadores calculados.")

    st.markdown("---")

    # seção — gerador do próximo mês
    if IS_ADMIN:
        prox_mes_num = mes_sel.month % 12 + 1
        prox_ano_num = mes_sel.year + (1 if mes_sel.month == 12 else 0)
        prox_label   = f"{_MESES_PT_LABEL.get(prox_mes_num, str(prox_mes_num))}/{prox_ano_num}"

        st.markdown(f"<div class='sec-header'>📥 Gerador de Plano — {prox_label}</div>", unsafe_allow_html=True)
        st.markdown(
            f"Gera uma planilha `.xlsx` com a estrutura idêntica ao plano de metas atual, "
            f"mas com **META MÊS** e **META DIÁRIA** recalibradas pelo Realizado (lançado ou "
            f"cruzado com produção) de {meses_labels[mes_sel]}. Combinações sem nenhum Realizado "
            f"mantêm as metas originais.",
            unsafe_allow_html=False,
        )
        if st.button(f"📥 Gerar Plano para {prox_label}", type="primary"):
            with st.spinner("Gerando planilha..."):
                xlsx_bytes = _gerar_proximo_mes_xlsx(
                    df_prev, df_ind,
                    mes_sel.year, mes_sel.month,
                )
            st.download_button(
                label=f"⬇️ Baixar Plano_{prox_label.replace('/', '-')}.xlsx",
                data=xlsx_bytes,
                file_name=f"Plano_Metas_{prox_label.replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

main()
