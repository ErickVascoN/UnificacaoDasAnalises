"""
Painel de Metas — Análise de Metas / Previsão de Custos

Fonte de dados: única — a própria planilha de Plano de Metas (METAS_SHEET_ID),
que já traz tanto o PREVISTO quanto o REALIZADO lançado manualmente (por
combinação Cliente × Prestador × Produto × Centro de Custo × Mês). Não cruza
com nenhuma fonte externa de produção diária (xlsx Produção Geral, facções,
lançamentos por unidade) — só usa o que está na própria planilha, a pedido do
usuário (15/07/2026): cruzar com produção diária externa exigia resolver
nomes de dezenas de prestadores sem correspondência, e a planilha já tem o
Realizado quando ele é lançado.
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

from config.settings import METAS_SHEET_ID, METAS_GID, METAS_CACHE_TTL
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button
from utils.feriados import eh_dia_util

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
        elif "PRECO" in n and "FINAL" in n: col_map["PRECO_FINAL"] = col
        elif "CUSTO" in n and "FINAL" in n: col_map["CUSTO_FINAL"] = col
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
    df["PRECO_FINAL"]  = raw[col_map["PRECO_FINAL"]].apply(_parse_num) if "PRECO_FINAL" in col_map else float("nan")
    df["CUSTO_FINAL"]  = raw[col_map["CUSTO_FINAL"]].apply(_parse_num) if "CUSTO_FINAL" in col_map else float("nan")
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

    df = df.dropna(subset=["DATA_BASE"])
    df = df[df["RESPONSAVEL"].str.len() > 0]
    df = df[df["STATUS"].isin(["PREVISTO", "REALIZADO"])]
    return df

# ─
# CÁLCULO DE INDICADORES
# ─
def _calcular_indicadores(df_prev: pd.DataFrame, df_real_mes: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada linha PREVISTO, busca o Realizado já lançado na própria
    planilha de metas — linhas STATUS=REALIZADO do mesmo mês, com a mesma
    combinação Cliente × Prestador × Produto × Centro de Custo. Não cruza
    com nenhuma fonte externa de produção diária: se a planilha ainda não
    tem um REALIZADO lançado pra essa combinação, o Realizado fica 0 (não
    "sem dado" — reflete exatamente o que está na planilha).
    """
    chaves = ["RESPONSAVEL", "CLIENTE", "PRODUTO", "CENTRO_CUSTO"]
    if df_real_mes.empty:
        real_map: dict = {}
    else:
        real_map = (
            df_real_mes.groupby(chaves)["META_MES"].sum().to_dict()
        )

    rows = []
    for _, meta in df_prev.iterrows():
        resp, cli, prod, cc = meta["RESPONSAVEL"], meta["CLIENTE"], meta["PRODUTO"], meta["CENTRO_CUSTO"]
        meta_mes    = meta["META_MES"]
        meta_diaria = meta["META_DIARIA"]
        vlr_unit    = meta["VLR_UNIT"]
        custo_unit  = meta["CUSTO"]

        realizado = float(real_map.get((resp, cli, prod, cc), 0.0))

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
    META DIÁRIA recalibradas pelo Realizado já lançado na própria planilha
    para o mês atual (quando houver); combinações sem Realizado lançado
    mantêm a meta original.
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
        "<p style='color:#A0A0A0;margin-bottom:20px;'>Distribuição de demanda e análise da capacidade disponível — "
        "Capacidade Disponível · Metas por Cliente/Prestador/Centro de Custo/Produto · "
        "Previsto x Realizado (lançado na planilha) · Previsão de Custos</p>",
        unsafe_allow_html=True,
    )
    render_filtros_btn()

    # carrega metas
    with st.spinner("Carregando plano de metas..."):
        df_metas = _load_metas()

    if df_metas.empty:
        st.error("Não foi possível carregar a planilha de metas. Verifique o acesso.")
        st.stop()

    # filtros
    meses_disponiveis = sorted(
        df_metas["DATA_BASE"].dropna().unique(),
        key=lambda d: (d.year, d.month),
    )
    # Padrão: o mês atual só se ele já tiver algum Realizado lançado na
    # planilha; senão, cai pro mês mais recente que já tem Realizado (evita
    # abrir a página com tudo zerado só porque o mês corrente ainda não foi
    # fechado — reportado pelo usuário 15/07/2026). Sem nenhum Realizado em
    # lugar nenhum, cai pro mês atual (ou o último disponível).
    meses_com_realizado = sorted(
        df_metas[df_metas["STATUS"] == "REALIZADO"]["DATA_BASE"].dropna().unique(),
        key=lambda d: (d.year, d.month),
    )
    mes_atual_disp = next(
        (d for d in meses_disponiveis if d.month == hoje.month and d.year == hoje.year), None
    )
    if mes_atual_disp is not None and mes_atual_disp in meses_com_realizado:
        default_mes = mes_atual_disp
    elif meses_com_realizado:
        default_mes = meses_com_realizado[-1]
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
        if mes_atual_disp is not None and mes_sel == mes_atual_disp and mes_atual_disp not in meses_com_realizado and default_mes != mes_atual_disp:
            st.caption(
                f"ℹ️ {meses_labels[mes_atual_disp]} ainda não tem Realizado lançado na planilha "
                f"— abrimos por padrão em {meses_labels[default_mes]}, o mês mais recente com dados."
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

    df_ind = _calcular_indicadores(df_prev, df_real_mes)

    # Diagnóstico (apenas Admin) — quantas metas já têm Realizado lançado
    if IS_ADMIN:
        with st.sidebar.expander("🔍 Diagnóstico de Dados"):
            n_prev = len(df_ind)
            n_com_real = int((df_ind["REALIZADO"] > 0).sum())
            st.caption(f"**PREVISTO no mês:** {n_prev} combinações")
            st.caption(f"**Com Realizado lançado:** {n_com_real} ({n_com_real/n_prev*100:.0f}%)" if n_prev else "—")
            st.caption(f"**Sem Realizado lançado ainda:** {n_prev - n_com_real}")

    if df_real_mes.empty:
        st.info(
            "ℹ️ Nenhum REALIZADO lançado ainda na planilha para o mês selecionado — "
            "os indicadores abaixo mostram 100% de Capacidade Disponível até que "
            "alguém lance o Realizado."
        )

    # ── KPIs — Produção ───────────────────────────────────────────────────────
    meta_total       = df_prev["META_MES"].sum(skipna=True)
    real_total       = df_ind["REALIZADO"].sum() if not df_ind.empty else 0.0
    capacidade_total = df_ind["CAPACIDADE_DISPONIVEL"].sum() if not df_ind.empty else 0.0
    pct_atingido     = (real_total / meta_total * 100) if meta_total > 0 else 0.0

    st.markdown("<div class='sec-header'>📦 Visão Geral do Mês — Produção</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Meta Total do Mês", _fmt_br(meta_total))
    c2.metric("Realizado (lançado na planilha)", _fmt_br(real_total),
              delta=f"{pct_atingido:.1f}% da meta")
    c3.metric("Capacidade Disponível", _fmt_br(capacidade_total),
              delta="ainda não lançado como realizado dentro da meta contratada")

    # ── KPIs — Financeiro (Previsto x Realizado) ──────────────────────────────
    receita_prev_total = df_ind["RECEITA_PREV"].sum() if not df_ind.empty else 0.0
    custo_prev_total   = df_ind["CUSTO_PREV"].sum() if not df_ind.empty else 0.0
    receita_real_total = df_ind["RECEITA_REAL"].sum() if not df_ind.empty else 0.0
    custo_real_total   = df_ind["CUSTO_REAL"].sum() if not df_ind.empty else 0.0
    margem_prev_total  = receita_prev_total - custo_prev_total
    margem_real_total  = receita_real_total - custo_real_total

    st.markdown("<div class='sec-header'>💰 Visão Geral do Mês — Previsão de Custos</div>", unsafe_allow_html=True)
    st.caption(
        "Previsto = Meta Mês × Valor Unitário/Custo. Realizado = quantidade já lançada "
        "como REALIZADO na planilha × Valor Unitário/Custo."
    )
    df_fin_kpi = pd.DataFrame({
        "": ["Receita", "Custo", "Margem"],
        "Previsto (Meta)": [receita_prev_total, custo_prev_total, margem_prev_total],
        "Realizado (lançado)": [receita_real_total, custo_real_total, margem_real_total],
    })
    for col in ["Previsto (Meta)", "Realizado (lançado)"]:
        df_fin_kpi[col] = df_fin_kpi[col].apply(_fmt_reais)
    st.dataframe(df_fin_kpi, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Capacidade Disponível — por Prestador ─────────────────────────────────
    st.markdown("<div class='sec-header'>🎯 Capacidade Disponível — por Prestador</div>", unsafe_allow_html=True)
    st.caption(
        "Capacidade Disponível = Meta Mês − Realizado (nunca negativa), somada por "
        "prestador em todos os clientes/produtos que ele atende. Mostra quanto da meta "
        "já contratada ainda não foi lançado como realizado — usar para decidir quem "
        "ainda comporta mais demanda neste mês."
    )
    if not df_ind.empty:
        df_cap = df_ind.groupby("RESPONSAVEL", as_index=False).agg(
            META_MES=("META_MES", "sum"),
            REALIZADO=("REALIZADO", "sum"),
            CAPACIDADE_DISPONIVEL=("CAPACIDADE_DISPONIVEL", "sum"),
            CAPACIDADE_DISPONIVEL_RECEITA=("CAPACIDADE_DISPONIVEL_RECEITA", "sum"),
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
        tbl_cap = pd.concat([tbl_cap, pd.DataFrame([_total_cap])], ignore_index=True)
        tbl_cap["PCT_OCUPADO"] = tbl_cap.apply(
            lambda r: f"{(r['REALIZADO']/r['META_MES']*100):.1f}%" if r["META_MES"] > 0 else "—", axis=1
        )
        tbl_cap["CAPACIDADE_DISPONIVEL_RECEITA"] = tbl_cap["CAPACIDADE_DISPONIVEL_RECEITA"].apply(_fmt_reais)
        for col in ["META_MES", "REALIZADO", "CAPACIDADE_DISPONIVEL"]:
            tbl_cap[col] = tbl_cap[col].apply(_fmt_br)
        tbl_cap = tbl_cap[["RESPONSAVEL", "META_MES", "REALIZADO", "CAPACIDADE_DISPONIVEL",
                           "CAPACIDADE_DISPONIVEL_RECEITA", "PCT_OCUPADO"]]
        tbl_cap.columns = ["Prestador", "Meta Mês", "Realizado", "Capacidade Disponível",
                            "Capacidade Disponível (R$)", "% Já Ocupado"]
        st.dataframe(tbl_cap, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de indicadores calculados.")

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
        tbl.columns = [dim_col, "Meta Mês", "Realizado", "Capacidade Disponível", "% Meta"]
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
            tbl_det = df_ind[[
                "STATUS_ICON", "CENTRO_CUSTO", "RESPONSAVEL", "CLIENTE", "PRODUTO",
                "META_MES", "META_DIARIA", "REALIZADO", "PCT_META", "CAPACIDADE_DISPONIVEL",
            ]].copy()
            tbl_det = tbl_det.sort_values(["CENTRO_CUSTO", "RESPONSAVEL"])
            _meta_total_det = tbl_det["META_MES"].sum()
            _real_total_det = tbl_det["REALIZADO"].sum()
            _total_det = {
                "STATUS_ICON": "", "CENTRO_CUSTO": "TOTAL", "RESPONSAVEL": "", "CLIENTE": "", "PRODUTO": "",
                "META_MES": _meta_total_det,
                "META_DIARIA": float("nan"),  # soma de taxas diárias de linhas diferentes não faz sentido
                "REALIZADO": _real_total_det,
                "PCT_META": (_real_total_det / _meta_total_det * 100) if _meta_total_det > 0 else float("nan"),
                "CAPACIDADE_DISPONIVEL": tbl_det["CAPACIDADE_DISPONIVEL"].sum(),
            }
            tbl_det = pd.concat([tbl_det, pd.DataFrame([_total_det])], ignore_index=True)
            tbl_det["PCT_META"] = tbl_det["PCT_META"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "—")
            for col in ["META_MES", "META_DIARIA", "REALIZADO", "CAPACIDADE_DISPONIVEL"]:
                tbl_det[col] = tbl_det[col].apply(lambda v: _fmt_br(v) if not np.isnan(v) else "—")
            tbl_det.columns = [
                "⬤", "Centro Custo", "Prestador", "Cliente", "Produto",
                "Meta Mês", "Meta Diária", "Realizado", "% Meta", "Capacidade Disponível",
            ]
            st.dataframe(tbl_det, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados de indicadores calculados.")

    st.markdown("---")

    # ── Previsão de Custos — Detalhamento por Cliente ─────────────────────────
    st.markdown("<div class='sec-header'>💰 Previsão de Custos — Detalhamento por Cliente</div>", unsafe_allow_html=True)
    st.caption(
        "Receita/Custo Realizado usam a quantidade já lançada como REALIZADO na "
        "planilha; Previsto usa a Meta."
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
            f"mas com **META MÊS** e **META DIÁRIA** recalibradas pelo Realizado já lançado "
            f"em {meses_labels[mes_sel]}. Combinações sem Realizado lançado mantêm as metas originais.",
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
