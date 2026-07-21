"""Dashboard de Produção — Facções / Prestadores Externos."""

import os
import sys
from calendar import monthrange
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.auth import init_session_state
from utils.faccao_loader import load_faccoes
from utils.metas_manager import load_metas, save_metas, reset_metas
from utils.anotacoes_manager import add_anotacao, remove_anotacao, load_anotacoes, apply_to_fig
from utils.normalize import normalize_text
from utils.feriados import eh_dia_util, contar_dias_uteis
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button
from config.settings import FACCOES_FACCAO_ALIAS, CORES_FACCAO
from styles.global_ui import get_global_ui_css

st.set_page_config(
    page_title="Produção Facções",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

# ── CSS ────────────────────────────────────────────────────────────────────────
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
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important; font-weight: 700 !important; font-size: 1.8rem !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111115 0%, #191920 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    section[data-testid="stSidebar"] * { color: #E0E0E0 !important; }
    .main-title {
        text-align: center; color: #FFFFFF; font-size: 2.4rem;
        font-weight: 800; margin-bottom: 4px;
    }
    .sub-title {
        text-align: center; color: #A0A0A0; font-size: 1.05rem; margin-bottom: 20px;
    }
    hr { border: none; border-top: 1px solid rgba(255,255,255,0.12); margin: 16px 0; }
    .stProgress > div > div > div { background-color: #4ECDC4 !important; }
    .stButton > button {
        background: linear-gradient(135deg, #1C1C22, #28282E) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #FFFFFF !important; border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Constantes ─────────────────────────────────────────────────────────────────
DARK_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0"),
    xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748"),
    yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    separators=",.",
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _dias_uteis(year: int, month: int) -> int:
    _, n = monthrange(year, month)
    return sum(1 for d in range(1, n + 1) if eh_dia_util(date(year, month, d)))


def _fmt(n: float | int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _join_unique(s: pd.Series) -> str:
    """Junta valores de texto não-vazios e únicos com ' / ' — usado quando um
    groupby colapsa várias linhas (ex.: Observações de dias/produtos iguais
    mas facções diferentes) numa só, sem perder nenhuma. Mesmo padrão de
    utils/controle_op.py::agregar_por_op."""
    vals = sorted({str(v).strip() for v in s if str(v).strip() not in ("", "nan", "NAN", "None")})
    return " / ".join(vals)


def _color_pct(val, t_green: float = 100, t_yellow: float = 75) -> str:
    """Colore um valor de % por faixas. Usado em st.dataframe style."""
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


def _build_goals() -> pd.DataFrame:
    rows = []
    for g in load_metas():
        rows.append({
            "PRODUTO":     g["produto"].upper(),
            "CLIENTE":     g["cliente"].upper(),
            "FACCAO":      g["faccao"].upper(),
            "PRODUTO_N":   normalize_text(g["produto"]),
            "CLIENTE_N":   normalize_text(g["cliente"]),
            "FACCAO_N":    normalize_text(g["faccao"]),
            "META_DIA":    g.get("meta_dia", 0),   # >0 = meta diária (nova guia)
            "META_MES":    g.get("meta_mes", 0),   # >0 = meta mensal (legado)
            "META_SEMANA": g.get("meta_semana", 0),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["PRODUTO","CLIENTE","FACCAO","PRODUTO_N","CLIENTE_N","FACCAO_N",
                 "META_DIA","META_MES","META_SEMANA"]
    )


@st.cache_data(ttl=300, show_spinner="Carregando produção...")
def _carregar() -> pd.DataFrame:
    df = load_faccoes()
    if df.empty:
        return df
    df["PRODUTO_N"] = df["PRODUTO"].apply(normalize_text)
    df["CLIENTE_N"] = df["CLIENTE"].apply(normalize_text)
    df["FACCAO_N"]  = df["FACCAO"].apply(normalize_text)
    return df


# ── Auth ───────────────────────────────────────────────────────────────────────
init_session_state()
render_home_button()  # sempre visível, mesmo sem login
if not st.session_state.get("auth_nivel"):
    st.warning("Faça login na página principal para acessar este dashboard.")
    st.stop()

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
st.markdown('<h1 class="main-title">Produção — Facções Externas</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Análise diária, semanal e mensal por facção e produto</p>', unsafe_allow_html=True)
render_filtros_btn()

# ── Carregar dados ─────────────────────────────────────────────────────────────
df_all = _carregar()

if df_all.empty:
    st.error("Planilha de facções não disponível. Verifique a conexão ou tente novamente.")
    st.stop()

# Normaliza variações de grafia nos nomes de facção (typos na aba QUARTERIZADAS).
if FACCOES_FACCAO_ALIAS:
    df_all["FACCAO"] = df_all["FACCAO"].replace(FACCOES_FACCAO_ALIAS)
    # FACCAO_N (usada pra casar com a guia de metas) precisa ser recalculada
    # depois do replace acima — senão fica com o nome antigo (ex.: "zanatta"
    # em vez de "giattex"), o que faz a facção aparecer duplicada na tabela
    # (uma linha com produção e sem meta, outra com meta e sem produção).
    df_all["FACCAO_N"] = df_all["FACCAO"].apply(normalize_text)

goals_df = _build_goals()

# Para metas da nova guia (META_DIA > 0), META_MES = META_DIA × du_mes.
# Calculamos depois de saber du_mes (definido mais abaixo), então guardamos
# uma flag e atualizamos após o cálculo de du_mes.
_goals_tem_dia = not goals_df.empty and (goals_df["META_DIA"] > 0).any()

today = date.today()

with st.sidebar:
    st.markdown("### 🗓 Período")
    _primeiro_mes = today.replace(day=1)
    _periodo_raw = st.date_input(
        "Período",
        value=(_primeiro_mes, today),
        min_value=date(2024, 1, 1),
        max_value=date(2030, 12, 31),
        format="DD/MM/YYYY",
    )
    if isinstance(_periodo_raw, (list, tuple)) and len(_periodo_raw) == 2:
        data_ini, data_fim = _periodo_raw[0], _periodo_raw[1]
    elif isinstance(_periodo_raw, (list, tuple)) and len(_periodo_raw) == 1:
        data_ini = data_fim = _periodo_raw[0]
    else:
        data_ini = data_fim = today
    mes_sel = data_ini.month
    ano_sel = data_ini.year

    st.markdown("### 🔍 Filtros")
    faccoes_opts = sorted(df_all["FACCAO"].unique())
    faccoes_sel = st.multiselect("Facção", faccoes_opts,
                                 placeholder="Todas as facções")

    empresas_opts = sorted(v for v in df_all["CLIENTE"].unique() if isinstance(v, str))
    empresas_sel = st.multiselect("Empresa / Cliente", empresas_opts,
                                  placeholder="Todas as empresas")

    produtos_opts = sorted(v for v in df_all["PRODUTO"].unique() if isinstance(v, str))
    produtos_sel = st.multiselect("Produto", produtos_opts,
                                  placeholder="Todos os produtos")

    if st.button("🔄 Atualizar dados", use_container_width=True):
        from utils.cache_manager import invalidate_all
        invalidate_all()
        st.cache_data.clear()
        st.rerun()

    # ── Seções admin ──────────────────────────────────────────────────────────
    if st.session_state.get("auth_nivel") == "admin":
        st.markdown("---")

        # Configurar Metas
        with st.expander("⚙️ Configurar Metas"):
            metas_atual = load_metas()
            metas_df = pd.DataFrame(metas_atual)
            metas_edited = st.data_editor(
                metas_df,
                num_rows="dynamic",
                use_container_width=True,
                key="metas_editor",
                column_config={
                    "produto":     st.column_config.TextColumn("Produto"),
                    "cliente":     st.column_config.TextColumn("Cliente"),
                    "faccao":      st.column_config.TextColumn("Facção"),
                    "meta_mes":    st.column_config.NumberColumn("Meta Mês", step=500),
                    "meta_semana": st.column_config.NumberColumn("Meta Semana", step=100),
                },
            )
            c_save, c_reset = st.columns(2)
            with c_save:
                if st.button("💾 Salvar", use_container_width=True, key="btn_save_metas"):
                    save_metas(metas_edited.to_dict("records"))
                    st.success("Metas salvas!")
                    st.rerun()
            with c_reset:
                if st.button("↩ Resetar", use_container_width=True, key="btn_reset_metas"):
                    reset_metas()
                    st.info("Voltou ao padrão do settings.py")
                    st.rerun()

        # Anotações nos gráficos
        with st.expander("📝 Anotações nos Gráficos"):
            with st.form("form_anotacao", clear_on_submit=True):
                col_d, col_c = st.columns([3, 1])
                with col_d:
                    an_data = st.date_input("Data", value=today, key="an_data")
                with col_c:
                    an_cor = st.color_picker("Cor", value="#F59E0B", key="an_cor")
                an_texto = st.text_input("Texto da anotação", key="an_texto")
                if st.form_submit_button("➕ Adicionar", use_container_width=True):
                    if an_texto:
                        add_anotacao(an_data.isoformat(), an_texto, an_cor, ["faccoes"])
                        st.success("Anotação adicionada!")
                        st.rerun()
                    else:
                        st.warning("Digite um texto.")

            lista_an = load_anotacoes()
            faccoes_an = [a for a in lista_an if "all" in a.get("paginas", ["all"]) or "faccoes" in a.get("paginas", [])]
            if faccoes_an:
                st.markdown("**Anotações ativas:**")
                for a in sorted(faccoes_an, key=lambda x: x["data"]):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.markdown(
                            f"<span style='color:{a['cor']};font-size:.85rem;'>"
                            f"● {a['data']} — {a['texto']}</span>",
                            unsafe_allow_html=True,
                        )
                    with cols[1]:
                        if st.button("✕", key=f"del_an_{a['id']}"):
                            remove_anotacao(a["id"])
                            st.rerun()
            else:
                st.caption("Nenhuma anotação cadastrada.")

# ── Aplica filtros ──────────────────────────────────────────────────────────────
df = df_all.copy()
if faccoes_sel:
    df = df[df["FACCAO"].isin(faccoes_sel)]
if empresas_sel:
    df = df[df["CLIENTE"].isin(empresas_sel)]
if produtos_sel:
    df = df[df["PRODUTO"].isin(produtos_sel)]

# Filtra metas por empresa/produto apenas.
du_mes = _dias_uteis(ano_sel, mes_sel)

# Converte meta diária → mensal usando os dias com produção de cada facção no período.
# du_mes (dias úteis do mês) é usado apenas como fallback para facções sem produção.
_df_periodo_pre = df[
    (df["DATA"].dt.date >= data_ini) & (df["DATA"].dt.date <= data_fim)
]
# Dias distintos com produção por facção. Só conta QUANTIDADE > 0 — linhas
# de QUANTIDADE=0 com Observação (dia sem produção, mas contextualizado, ex.:
# "máquina quebrou") não contam como dia de produção, senão infla a meta e
# derruba a % sem queda real de produção (feedback do usuário 14/07/2026).
_dias_fac: dict[str, int] = {}
if not _df_periodo_pre.empty:
    _dias_fac = (
        _df_periodo_pre[_df_periodo_pre["QUANTIDADE"] > 0]
        .groupby("FACCAO_N")["DATA"]
        .apply(lambda s: s.dt.date.nunique())
        .to_dict()
    )

if _goals_tem_dia and not goals_df.empty:
    mask_dia = goals_df["META_DIA"] > 0
    goals_df.loc[mask_dia, "META_MES"] = goals_df.loc[mask_dia].apply(
        lambda r: int(r["META_DIA"] * _dias_fac.get(r["FACCAO_N"], du_mes)),
        axis=1,
    )
    goals_df.loc[mask_dia, "META_SEMANA"] = (goals_df.loc[mask_dia, "META_DIA"] * 5).astype(int)

# gf = goals filtrados por empresa/produto (para as tabs que usam match por produto/cliente)
gf = goals_df.copy()
if empresas_sel:
    gf = gf[gf["CLIENTE"].isin([e.upper() for e in empresas_sel])]
if produtos_sel:
    gf = gf[gf["PRODUTO"].isin([p.upper() for p in produtos_sel])]

# Meta da facção: agrupada por FACCAO_N.
# Para metas com CLIENTE específico (ex: CORTINA tem metas diferentes por cliente),
# usa média ponderada pela produção de cada cliente no período.
# Metas sem cliente (CLIENTE_N == "") somam diretamente.

# Produção por (facção, produto, cliente) e (facção, cliente) para ponderação
_qty_fac_cli: dict[tuple, int] = {}       # (fn, cn) → qty
_qty_fac_prod_cli: dict[tuple, int] = {}  # (fn, pn, cn) → qty
_qty_fac_total: dict[str, int] = {}       # fn → qty total
_qty_fac_prod: dict[tuple, int] = {}      # (fn, pn) → qty total do produto
if not _df_periodo_pre.empty:
    _tmp = _df_periodo_pre.assign(
        _cn=_df_periodo_pre["CLIENTE"].apply(normalize_text),
        _pn=_df_periodo_pre["PRODUTO"].apply(normalize_text),
    )
    for (fn, cn), qty in _tmp.groupby(["FACCAO_N", "_cn"])["QUANTIDADE"].sum().items():
        _qty_fac_cli[(fn, cn)] = int(qty)
        _qty_fac_total[fn] = _qty_fac_total.get(fn, 0) + int(qty)
    for (fn, pn, cn), qty in _tmp.groupby(["FACCAO_N", "_pn", "_cn"])["QUANTIDADE"].sum().items():
        _qty_fac_prod_cli[(fn, pn, cn)] = int(qty)
        _qty_fac_prod[(fn, pn)] = _qty_fac_prod.get((fn, pn), 0) + int(qty)


# Metas restritas às facções filtradas — sem isso, a Meta do Período soma
# a meta de TODAS as facções mesmo com filtro de Facção aplicado (reportado
# pelo usuário 16/07/2026).
_goals_calc = goals_df
if faccoes_sel:
    _faccoes_sel_n = {normalize_text(f) for f in faccoes_sel}
    _goals_calc = goals_df[goals_df["FACCAO_N"].isin(_faccoes_sel_n)]

_meta_fac_rows = []
for fn, grp in _goals_calc.groupby("FACCAO_N"):
    faccao_label = grp["FACCAO"].iloc[0]
    meta_dia_fac  = 0.0
    meta_sem_fac  = 0.0

    # Entradas sem cliente nem produto específico → soma direta
    sem_cli = grp[(grp["CLIENTE_N"] == "") & (grp["PRODUTO_N"] == "")]
    meta_dia_fac += float(sem_cli["META_DIA"].sum())
    meta_sem_fac += float(sem_cli["META_SEMANA"].sum())

    # Entradas com produto mas sem cliente (ex: ZANATTA só produto)
    com_prod_sem_cli = grp[(grp["PRODUTO_N"] != "") & (grp["CLIENTE_N"] == "")]
    meta_dia_fac += float(com_prod_sem_cli["META_DIA"].sum())
    meta_sem_fac += float(com_prod_sem_cli["META_SEMANA"].sum())

    # Entradas com cliente mas sem produto (ex: CORTINA por cliente)
    com_cli_sem_prod = grp[(grp["CLIENTE_N"] != "") & (grp["PRODUTO_N"] == "")]
    if not com_cli_sem_prod.empty:
        total_qty = _qty_fac_total.get(fn, 0)
        for _, grow in com_cli_sem_prod.iterrows():
            cn = grow["CLIENTE_N"]
            qty_cli = _qty_fac_cli.get((fn, cn), 0)
            if total_qty > 0 and qty_cli > 0:
                peso = qty_cli / total_qty
                meta_dia_fac += float(grow["META_DIA"]) * peso
                meta_sem_fac += float(grow["META_SEMANA"]) * peso

    # Entradas com produto E cliente (ex: ZANATTA por produto+cliente)
    com_prod_cli = grp[(grp["PRODUTO_N"] != "") & (grp["CLIENTE_N"] != "")]
    if not com_prod_cli.empty:
        # Agrupa por produto para ponderar dentro de cada produto
        for pn, pgrp in com_prod_cli.groupby("PRODUTO_N"):
            total_prod = _qty_fac_prod.get((fn, pn), 0)
            for _, grow in pgrp.iterrows():
                cn = grow["CLIENTE_N"]
                qty_pc = _qty_fac_prod_cli.get((fn, pn, cn), 0)
                if total_prod > 0 and qty_pc > 0:
                    peso = qty_pc / total_prod
                    meta_dia_fac += float(grow["META_DIA"]) * peso
                    meta_sem_fac += float(grow["META_SEMANA"]) * peso

    dias_fac = _dias_fac.get(fn, du_mes)
    meta_mes_fac = int(round(meta_dia_fac * dias_fac))
    _meta_fac_rows.append({
        "FACCAO_N":    fn,
        "FACCAO":      faccao_label,
        "META_DIA_FAC": int(round(meta_dia_fac)),
        "META_MES_FAC": meta_mes_fac,
        "META_SEM_FAC": int(round(meta_sem_fac)),
    })

meta_fac_df = pd.DataFrame(_meta_fac_rows) if _meta_fac_rows else pd.DataFrame(
    columns=["FACCAO_N", "FACCAO", "META_DIA_FAC", "META_MES_FAC", "META_SEM_FAC"]
)

meta_mes_total = int(meta_fac_df["META_MES_FAC"].sum())
meta_sem_total = int(meta_fac_df["META_SEM_FAC"].sum())
meta_dia_total = int(meta_fac_df["META_DIA_FAC"].sum())

_periodo_label = (
    f"{data_ini.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}"
    if data_ini != data_fim else data_ini.strftime('%d/%m/%Y')
)

# ── rank_df: Facção × Meta — produção total da facção vs meta mensal (dia × du_mes) ─
_df_periodo = df[
    (df["DATA"].dt.date >= data_ini) & (df["DATA"].dt.date <= data_fim)
]
_total_geral = int(_df_periodo["QUANTIDADE"].sum()) if not _df_periodo.empty else 1

# Produção total por facção — agrupa só por FACCAO_N para evitar duplicatas
# quando a planilha tem grafias ligeiramente diferentes do mesmo prestador.
if not _df_periodo.empty:
    _fac_qty = _df_periodo.groupby("FACCAO_N")["QUANTIDADE"].sum().reset_index()
    # Nome de exibição: primeira ocorrência do FACCAO canônico (após replace de alias)
    _fac_label_prod = (
        _df_periodo.groupby("FACCAO_N")["FACCAO"].first().reset_index()
    )
    _fac_grp = _fac_qty.merge(_fac_label_prod, on="FACCAO_N", how="left")
else:
    _fac_grp = pd.DataFrame(columns=["FACCAO_N", "FACCAO", "QUANTIDADE"])

# Meta por facção vem de meta_fac_df (META_DIA × dias_com_producao já calculado)
rank_df = _fac_grp.merge(
    meta_fac_df[["FACCAO_N", "FACCAO", "META_DIA_FAC", "META_MES_FAC", "META_SEM_FAC"]].rename(
        columns={"META_DIA_FAC": "META_DIA", "META_MES_FAC": "META_MES", "META_SEM_FAC": "META_SEMANA",
                 "FACCAO": "FACCAO_META"}
    ),
    on="FACCAO_N", how="outer",
)
rank_df["QUANTIDADE"] = rank_df["QUANTIDADE"].fillna(0).astype(int)
rank_df["META_DIA"]   = rank_df["META_DIA"].fillna(0).astype(int)
rank_df["META_MES"]   = rank_df["META_MES"].fillna(0).astype(int)
rank_df["META_SEMANA"]= rank_df["META_SEMANA"].fillna(0).astype(int)

# Nome de exibição: produção tem prioridade; quando só vem da meta, usa nome da meta
rank_df["FACCAO"] = rank_df["FACCAO"].where(
    rank_df["FACCAO"].notna() & (rank_df["FACCAO"] != ""),
    rank_df["FACCAO_META"],
)
rank_df.drop(columns=["FACCAO_META"], inplace=True, errors="ignore")

rank_df["PCT"] = rank_df.apply(
    lambda r: round(r["QUANTIDADE"] / r["META_MES"] * 100, 1) if r["META_MES"] > 0 else None, axis=1
)
rank_df["% do Total"] = (rank_df["QUANTIDADE"] / max(_total_geral, 1) * 100).round(1)
rank_df["RESTANTE"] = rank_df.apply(
    lambda r: max(0, int(r["META_MES"] - r["QUANTIDADE"])) if r["META_MES"] > 0 else None, axis=1
)

# ── Seletor de seção ───────────────────────────────────────────────────────────
# Antes usava st.tabs(), mas o Streamlit executa o corpo de TODAS as abas a cada
# rerun do script, mesmo as que não estão visualmente selecionadas — a aba "Por
# Facção" sozinha já monta ~9 gráficos Plotly + um loop por facção incondicional,
# então qualquer interação na página (inclusive mudar o período na sidebar)
# refazia o trabalho pesado das 5 abas de uma vez. Um seletor (só a seção
# escolhida executa) resolve isso — mesmo padrão já usado em pages/10_Relatorios.py
# (corrigido lá em 14/07/2026 pelo mesmo motivo: app caindo/lento no Streamlit
# Cloud com 2+ usuários). Reportado pelo usuário 15/07/2026.
_SECOES_FACCOES = ["📅 Mensal", "📆 Diário", "📊 Semanal", "📦 Por Produto", "🏭 Por Facção"]
_secao_faccoes = st.radio(
    "Seção", _SECOES_FACCOES, horizontal=True,
    key="secao_faccoes", label_visibility="collapsed",
)
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MENSAL
# ══════════════════════════════════════════════════════════════════════════════
if _secao_faccoes == "📅 Mensal":
    df_mes = df[
        (df["DATA"].dt.date >= data_ini) & (df["DATA"].dt.date <= data_fim)
    ]
    total_mes = int(df_mes["QUANTIDADE"].sum())

    # Dias úteis decorridos no período selecionado (até hoje ou até data_fim)
    _fim_ref = min(today, data_fim)
    du_passados = 0 if _fim_ref < data_ini else contar_dias_uteis(data_ini, _fim_ref)
    esperado = du_passados * meta_dia_total
    pct_mes  = total_mes / meta_mes_total * 100 if meta_mes_total > 0 else 0
    pct_ritmo = total_mes / esperado * 100 if esperado > 0 else 0

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Produção do Mês", _fmt(total_mes))
    with c2:
        st.metric("Meta Mensal", _fmt(meta_mes_total))
    with c3:
        cor_pct = "normal" if pct_mes >= 100 else "inverse"
        st.metric("% da Meta", f"{pct_mes:.1f}%")
    with c4:
        delta_ritmo = f"{pct_ritmo - 100:+.1f}pp vs esperado"
        st.metric("Ritmo", f"{pct_ritmo:.1f}%", delta=delta_ritmo)

    st.markdown("---")

    # Gráfico diário
    if not df_mes.empty:
        daily = (
            df_mes.groupby("DATA")["QUANTIDADE"].sum()
            .reset_index()
            .sort_values("DATA")
        )
        daily["DATA_STR"] = daily["DATA"].dt.strftime("%d/%m")

        fig = go.Figure()
        fig.add_bar(
            x=daily["DATA_STR"],
            y=daily["QUANTIDADE"],
            name="Produção",
            marker_color="#4ECDC4",
            hovertemplate="%{x}: <b>%{y:,.0f}</b><extra></extra>",
        )
        if meta_dia_total > 0:
            fig.add_scatter(
                x=daily["DATA_STR"],
                y=[meta_dia_total] * len(daily),
                mode="lines",
                name=f"Meta/dia ({_fmt(round(meta_dia_total))})",
                line=dict(color="#FF6B6B", dash="dash", width=2),
            )
        fig.update_layout(
            title=f"Produção Diária — {_periodo_label}",
            xaxis_title="Dia",
            yaxis_title="Peças",
            **DARK_LAYOUT,
        )
        _d_ini = data_ini
        _d_fim = daily["DATA"].max().date() if not daily.empty else _d_ini
        fig = apply_to_fig(fig, _d_ini, _d_fim, pagina="faccoes", x_fmt="%d/%m")
        st.plotly_chart(fig, use_container_width=True)

        # Acumulado vs meta (burn-up): produção acumulada × meta acumulada esperada
        daily_cum = daily.copy()
        daily_cum["ACUM"] = daily_cum["QUANTIDADE"].cumsum()
        # Pré-calcula dias úteis acumulados uma vez pro range inteiro do
        # período (1 passada, 1 chamada de eh_dia_util por dia do calendário)
        # em vez de recontar do zero pra cada dia que teve produção — antes
        # isso era O(dias com produção × tamanho do período); num período de
        # 1 ano isso chegava a ~130 mil chamadas só nesse trecho (reportado
        # pelo usuário 15/07/2026 — dashboard lento).
        _du_acum_map: dict = {}
        _acc = 0
        for _d in pd.date_range(data_ini, data_fim, freq="D").date:
            if eh_dia_util(_d):
                _acc += 1
            _du_acum_map[_d] = _acc
        daily_cum["DU_ACUM"] = daily_cum["DATA"].dt.date.map(_du_acum_map)
        daily_cum["META_ACUM"] = (daily_cum["DU_ACUM"] * meta_dia_total).round()

        fig_cum = go.Figure()
        fig_cum.add_scatter(
            x=daily_cum["DATA_STR"], y=daily_cum["ACUM"],
            mode="lines+markers", name="Produção acumulada",
            line=dict(color="#4ECDC4", width=3), fill="tozeroy",
            hovertemplate="%{x}: <b>%{y:,.0f}</b><extra></extra>",
        )
        if meta_dia_total > 0:
            fig_cum.add_scatter(
                x=daily_cum["DATA_STR"], y=daily_cum["META_ACUM"],
                mode="lines", name="Meta acumulada",
                line=dict(color="#FF6B6B", dash="dash", width=2),
            )
        fig_cum.update_layout(
            title="Acumulado vs Meta (Burn-up)",
            xaxis_title="Dia", yaxis_title="Peças acumuladas",
            **DARK_LAYOUT,
        )
        fig_cum = apply_to_fig(fig_cum, _d_ini, _d_fim, pagina="faccoes", x_fmt="%d/%m")
        st.plotly_chart(fig_cum, use_container_width=True)

        # Só conta dias com QUANTIDADE > 0 — dias zerados/contextualizados (Observação)
        # não entram na média (feedback do usuário 14/07/2026).
        dias_com_prod_mes = int(daily[daily["QUANTIDADE"] > 0]["DATA"].dt.date.nunique())
        media_dia_mes = total_mes / dias_com_prod_mes if dias_com_prod_mes else 0
        top_dia_mes = daily.loc[daily["QUANTIDADE"].idxmax()]
        saldo_meta_mes = total_mes - meta_mes_total
        top_fac_mes = (
            df_mes.groupby("FACCAO")["QUANTIDADE"]
            .sum().reset_index().sort_values("QUANTIDADE", ascending=False)
        )
        top3_share_mes = (
            top_fac_mes.head(3)["QUANTIDADE"].sum() / total_mes * 100
            if total_mes > 0 and not top_fac_mes.empty else 0
        )

        st.markdown("### 📌 Leitura Rápida do Mês")
        st.caption(
            f"Concentração das 3 maiores facções: {top3_share_mes:.1f}% do total do período. "
            f"Saldo atual versus meta: {_fmt(abs(saldo_meta_mes))} {'acima' if saldo_meta_mes >= 0 else 'abaixo'} da meta."
        )
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            st.metric("Dias com produção", dias_com_prod_mes)
        with c6:
            st.metric("Média diária", _fmt(round(media_dia_mes)))
        with c7:
            st.metric("Melhor dia", top_dia_mes["DATA"].strftime("%d/%m"), delta=_fmt(int(top_dia_mes["QUANTIDADE"])))
        with c8:
            st.metric("Saldo da meta", _fmt(abs(saldo_meta_mes)), delta="acima" if saldo_meta_mes >= 0 else "abaixo")

        if not top_fac_mes.empty:
            top_fac_mes = top_fac_mes.head(5).copy()
            fig_top_fac_mes = px.bar(
                top_fac_mes.sort_values("QUANTIDADE"),
                x="QUANTIDADE",
                y="FACCAO",
                orientation="h",
                color="FACCAO",
                color_discrete_map=CORES_FACCAO,
                text="QUANTIDADE",
                labels={"QUANTIDADE": "Peças", "FACCAO": "Facção"},
                title="Top Facções no Período",
            )
            fig_top_fac_mes.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_top_fac_mes.update_layout(showlegend=False, **DARK_LAYOUT)
            st.plotly_chart(fig_top_fac_mes, use_container_width=True)
    else:
        st.info(f"Sem produção registrada no período selecionado.")

    st.markdown("---")

    # Tabela de progresso: uma linha por facção — produção total vs meta diária × du_mes
    st.subheader("Progresso por Facção")
    st.caption(
        f"Meta mensal = meta diária × {du_mes} dias úteis do mês. "
        "Produção = total da facção (todos os produtos e clientes somados)."
    )

    # Produção total por facção no período mensal
    if not df_mes.empty:
        _prod_mes_fac = df_mes.groupby(["FACCAO_N", "FACCAO"])["QUANTIDADE"].sum().reset_index()
    else:
        _prod_mes_fac = pd.DataFrame(columns=["FACCAO_N", "FACCAO", "QUANTIDADE"])

    tabela_fac = meta_fac_df[["FACCAO_N", "FACCAO", "META_DIA_FAC", "META_MES_FAC", "META_SEM_FAC"]].merge(
        _prod_mes_fac[["FACCAO_N", "QUANTIDADE"]], on="FACCAO_N", how="left"
    )
    tabela_fac["QUANTIDADE"]   = tabela_fac["QUANTIDADE"].fillna(0).astype(int)
    tabela_fac["META_MES_FAC"] = tabela_fac["META_MES_FAC"].astype(int)
    tabela_fac["% Meta"] = tabela_fac.apply(
        lambda r: round(r["QUANTIDADE"] / r["META_MES_FAC"] * 100, 1) if r["META_MES_FAC"] > 0 else None, axis=1
    )
    tabela_fac["Restante"] = tabela_fac.apply(
        lambda r: max(0, r["META_MES_FAC"] - r["QUANTIDADE"]) if r["META_MES_FAC"] > 0 else None, axis=1
    )
    tabela = tabela_fac[["FACCAO", "META_DIA_FAC", "META_MES_FAC", "QUANTIDADE", "% Meta", "Restante"]].copy()
    tabela.columns = ["Facção", "Meta/Dia", "Meta Mês", "Produzido", "% Meta", "Restante"]
    tabela = tabela.sort_values("% Meta", ascending=False, na_position="last").reset_index(drop=True)

    def _fmt_opt(v, fmt):
        return fmt.format(v) if v is not None else "—"

    def _sfmt(v):
        try:
            return f"{int(v):,}".replace(",", ".") if v is not None and not pd.isna(v) else "—"
        except Exception:
            return "—"

    st.dataframe(
        tabela.style
        .map(_color_pct, subset=["% Meta"])
        .format({
            "Produzido": _sfmt,
            "Meta/Dia":  _sfmt,
            "Meta Mês":  _sfmt,
            "% Meta":    lambda v: f"{v:.1f}%" if v is not None and not pd.isna(v) else "—",
            "Restante":  _sfmt,
        }),
        column_config={
            "Facção":    st.column_config.TextColumn("Facção",    width="medium"),
            "Meta/Dia":  st.column_config.TextColumn("Meta/Dia",  width="small"),
            "Meta Mês":  st.column_config.TextColumn("Meta Mês",  width="small"),
            "Produzido": st.column_config.TextColumn("Produzido", width="small"),
            "% Meta":    st.column_config.TextColumn("% Meta",    width="small"),
            "Restante":  st.column_config.TextColumn("Restante",  width="small"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # ── Botão Relatório PDF ──────────────────────────────────────────────────
    def _gerar_pdf_faccoes_mensal() -> bytes:
        from utils.pdf_report import gerar_pdf_faccoes as _gpf
        filtros_str = []
        if faccoes_sel:
            filtros_str.append("Facções: " + ", ".join(sorted(faccoes_sel)))
        if empresas_sel:
            filtros_str.append("Empresas: " + ", ".join(sorted(empresas_sel)))
        if produtos_sel:
            filtros_str.append("Produtos: " + ", ".join(sorted(produtos_sel)))
        # Renomeia colunas do tabela para compatibilidade com o gerador
        tab_pdf = tabela.rename(columns={"Facção": "Faccao", "Meta Mês": "Meta Mes"})
        return _gpf(
            tabela=tab_pdf,
            df_mes=df_mes,
            total_mes=total_mes,
            meta_mes_total=meta_mes_total,
            pct_mes=pct_mes,
            pct_ritmo=pct_ritmo,
            meta_dia_total=meta_dia_total,
            data_ini=data_ini,
            data_fim=data_fim,
            filtros_texto=" | ".join(filtros_str),
            rank_df=rank_df,
            tem_filtro_faccao=bool(faccoes_sel),
        )

    def _html_faccoes_mensal() -> bytes:
        from datetime import datetime as _dt
        agora = _dt.now().strftime("%d/%m/%Y %H:%M")
        periodo_str = (
            f"{data_ini.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}"
            if data_ini != data_fim else data_ini.strftime('%d/%m/%Y')
        )

        def _n(v) -> str:
            return f"{int(v):,}".replace(",", ".")

        def _pct_bar_html(pct: float | None) -> str:
            if pct is None:
                return "—"
            filled = min(int(pct / 5), 20)
            bar = "█" * filled + "░" * (20 - filled)
            return f"{bar} {pct:.1f}%"

        def _tabela_rows() -> str:
            linhas = []
            for _, r in tabela.iterrows():
                pct_raw = r["% Meta"]
                pct = float(pct_raw) if pct_raw is not None and not pd.isna(pct_raw) else None
                if pct is not None:
                    cls = "sok" if pct >= 100 else ("samb" if pct >= 75 else "serr")
                    pct_str = f"<td class='num {cls}'>{pct:.1f}%</td>"
                else:
                    pct_str = "<td class='num'>—</td>"
                meta_dia_str = _n(r["Meta/Dia"]) if pd.notna(r["Meta/Dia"]) else "—"
                meta_mes_str = _n(r["Meta Mês"]) if pd.notna(r["Meta Mês"]) else "—"
                rest_str     = _n(r["Restante"]) if pd.notna(r["Restante"]) else "—"
                linhas.append(
                    f"<tr><td>{r['Facção']}</td>"
                    f"<td class='num'>{meta_dia_str}</td>"
                    f"<td class='num'>{meta_mes_str}</td>"
                    f"<td class='num'>{_n(r['Produzido'])}</td>"
                    f"{pct_str}"
                    f"<td class='num'>{rest_str}</td></tr>"
                )
            return "\n".join(linhas)

        def _faccao_x_meta_html() -> str:
            """Seção de comparação direta Facção × Meta com barra de progresso visual."""
            if not hasattr(rank_df, 'iterrows'):
                return ""
            rk = rank_df.sort_values("QUANTIDADE", ascending=False)
            linhas = []
            for _, r in rk.iterrows():
                _pct_raw = r["PCT"]
                pct = float(_pct_raw) if (_pct_raw is not None and not pd.isna(_pct_raw)) else None
                meta = r["META_MES"]
                prod = int(r["QUANTIDADE"])
                rest = r["RESTANTE"]
                if pct is not None:
                    cls = "sok" if pct >= 100 else ("samb" if pct >= 75 else "serr")
                    pct_cell = f"<td class='num {cls}'>{pct:.1f}%</td>"
                    bar_w = min(int(pct), 100)
                    bar_col = "#4ECDC4" if pct >= 100 else "#FFA726" if pct >= 75 else "#FF6B6B"
                    bar_html = (
                        f"<div style='background:#e5e7eb;border-radius:3px;height:8px;width:100%;'>"
                        f"<div style='background:{bar_col};width:{bar_w}%;height:8px;border-radius:3px;'></div></div>"
                    )
                    bar_cell = f"<td style='min-width:80px;padding:5px 6px;'>{bar_html}</td>"
                else:
                    pct_cell = "<td class='num' style='color:#999'>sem meta</td>"
                    bar_cell = "<td></td>"
                meta_str = _n(meta) if (meta and not pd.isna(meta) and meta > 0) else "—"
                rest_str = _n(rest) if (rest is not None and not pd.isna(rest)) else "—"
                pct_tot = r["% do Total"]
                linhas.append(
                    f"<tr>"
                    f"<td><strong>{r['FACCAO']}</strong></td>"
                    f"<td class='num'>{_n(prod)}</td>"
                    f"<td class='num'>{meta_str}</td>"
                    f"{pct_cell}"
                    f"{bar_cell}"
                    f"<td class='num'>{rest_str}</td>"
                    f"<td class='num' style='color:#888'>{pct_tot:.1f}%</td>"
                    f"</tr>"
                )
            return (
                "<table>\n"
                "  <thead><tr>"
                "<th>Fac&ccedil;&atilde;o</th>"
                "<th class='num'>Produzido</th>"
                "<th class='num'>Meta M&ecirc;s</th>"
                "<th class='num'>% da Meta</th>"
                "<th style='min-width:80px'>Progresso</th>"
                "<th class='num'>Restante</th>"
                "<th class='num'>% do Total</th>"
                "</tr></thead>\n"
                f"  <tbody>{''.join(linhas)}</tbody>\n"
                "</table>\n"
            )

        def _detalhe_faccoes_html() -> str:
            if df_mes.empty:
                return ""
            blocos = []
            for faccao in sorted(df_mes["FACCAO"].unique()):
                df_f = df_mes[df_mes["FACCAO"] == faccao].copy()
                det = (
                    df_f.groupby(["DATA", "PRODUTO", "CLIENTE"])["QUANTIDADE"]
                    .sum().reset_index()
                    .sort_values("DATA")
                )
                linhas = []
                for _, r in det.iterrows():
                    linhas.append(
                        f"<tr><td>{r['DATA'].strftime('%d/%m/%Y')}</td>"
                        f"<td>{r['PRODUTO']}</td><td>{r['CLIENTE']}</td>"
                        f"<td class='num'>{_n(r['QUANTIDADE'])}</td></tr>"
                    )
                total_fac = int(df_f["QUANTIDADE"].sum())
                # Meta individual da facção
                meta_fac_row = rank_df[rank_df["FACCAO"] == faccao]
                if not meta_fac_row.empty and meta_fac_row.iloc[0]["META_MES"] > 0:
                    pct_fac = meta_fac_row.iloc[0]["PCT"]
                    meta_fac = int(meta_fac_row.iloc[0]["META_MES"])
                    cls = "sok" if (pct_fac or 0) >= 100 else ("samb" if (pct_fac or 0) >= 75 else "serr")
                    meta_info = (
                        f" &nbsp;|&nbsp; Meta: {_n(meta_fac)}"
                        f" &nbsp;|&nbsp; <span class='{cls}'>{pct_fac:.1f}%</span>"
                    )
                else:
                    meta_info = ""
                blocos.append(
                    f"<div class='sec'>{faccao} &mdash; Total: {_n(total_fac)} pcs{meta_info}</div>\n"
                    "<table>\n"
                    "  <thead><tr><th>Data</th><th>Produto</th><th>Empresa</th>"
                    "<th class='num'>Qtd</th></tr></thead>\n"
                    f"  <tbody>{''.join(linhas)}</tbody>\n"
                    "</table>\n"
                )
            return "".join(blocos)

        tabela_html      = _tabela_rows()
        fac_meta_html    = _faccao_x_meta_html()
        detalhe_html     = _detalhe_faccoes_html()
        cls_pct = "sok" if pct_mes >= 100 else ("samb" if pct_mes >= 75 else "serr")

        # Conta facções acima/abaixo da meta
        n_acima  = int((rank_df["PCT"] >= 100).sum()) if not rank_df.empty else 0
        n_abaixo = int((rank_df["PCT"].notna() & (rank_df["PCT"] < 100)).sum()) if not rank_df.empty else 0
        n_sem    = int(rank_df["PCT"].isna().sum()) if not rank_df.empty else 0

        html = (
            "<!DOCTYPE html>\n<html lang='pt-BR'>\n<head>\n"
            "<meta charset='UTF-8'>\n"
            f"<title>Relatório Facções · {periodo_str}</title>\n"
            "<style>\n"
            "@page { margin: 15mm; size: A4 landscape; }\n"
            "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
            "body { font-family: Arial, sans-serif; font-size: 10px; color: #1a1a1a; background: #fff; }\n"
            ".hint { background:#FEF3C7; padding:8px 14px; margin-bottom:14px; border-radius:4px; font-size:12px; border:1px solid #FCD34D; }\n"
            ".header { border-bottom:3px solid #4ECDC4; padding-bottom:8px; margin-bottom:14px; }\n"
            ".header h1 { font-size:17px; color:#065F46; }\n"
            ".header .sub { color:#444; margin-top:3px; font-size:10px; }\n"
            ".kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:7px; margin-bottom:16px; }\n"
            ".kpi { border:1px solid #4ECDC4; border-radius:5px; padding:7px 9px; text-align:center; }\n"
            ".kpi-lbl { font-size:8px; color:#555; text-transform:uppercase; letter-spacing:.05em; }\n"
            ".kpi-val { font-size:15px; font-weight:700; color:#065F46; margin-top:2px; }\n"
            ".kpi-val.sok { color:#065F46; } .kpi-val.samb { color:#92400E; } .kpi-val.serr { color:#B91C1C; }\n"
            ".status-bar { display:flex; gap:12px; margin-bottom:14px; }\n"
            ".sb { border-radius:5px; padding:5px 12px; font-size:9px; font-weight:700; text-transform:uppercase; }\n"
            ".sb-ok  { background:#D1FAE5; color:#065F46; border:1px solid #6EE7B7; }\n"
            ".sb-amb { background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; }\n"
            ".sb-err { background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5; }\n"
            ".sb-na  { background:#F3F4F6; color:#6B7280; border:1px solid #D1D5DB; }\n"
            ".sec { font-size:11px; font-weight:700; color:#065F46; border-bottom:1px solid #4ECDC4; margin:14px 0 7px 0; padding-bottom:3px; }\n"
            "table { width:100%; border-collapse:collapse; margin-bottom:14px; font-size:9.5px; }\n"
            "th { background:#065F46; color:#fff; padding:4px 6px; text-align:left; font-size:8.5px; text-transform:uppercase; letter-spacing:.04em; }\n"
            "td { padding:3px 6px; border-bottom:1px solid #e5e7eb; vertical-align:middle; }\n"
            "tr:nth-child(even) td { background:#F0FDF4; }\n"
            ".num { text-align:right; font-variant-numeric:tabular-nums; }\n"
            ".sok { color:#065F46; font-weight:600; }\n"
            ".samb { color:#92400E; font-weight:600; }\n"
            ".serr { color:#B91C1C; font-weight:600; }\n"
            ".footer { margin-top:16px; padding-top:7px; border-top:1px solid #ccc; color:#777; font-size:8px; text-align:center; }\n"
            "@media print { .hint { display:none; } body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }\n"
            "</style>\n</head>\n<body>\n"
            "<div class='hint'><strong>Para gerar PDF:</strong> pressione <kbd>Ctrl+P</kbd> (Windows) "
            "ou <kbd>&#8984;+P</kbd> (Mac) &rarr; <em>Salvar como PDF</em>.</div>\n"
            "<div class='header'>\n"
            "  <h1>&#127981; Relatório de Produção &mdash; Facções</h1>\n"
            f"  <div class='sub'>Período: <strong>{periodo_str}</strong>"
            f"  &nbsp;|&nbsp; Gerado em: {agora}</div>\n"
            "</div>\n"
            "<div class='kpi-grid'>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Produção do Mês</div><div class='kpi-val'>{_n(total_mes)}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Meta Mensal</div><div class='kpi-val'>{_n(meta_mes_total)}</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>% da Meta</div><div class='kpi-val {cls_pct}'>{pct_mes:.1f}%</div></div>\n"
            f"  <div class='kpi'><div class='kpi-lbl'>Ritmo do Mês</div><div class='kpi-val'>{pct_ritmo:.1f}%</div></div>\n"
            "</div>\n"
            "<div class='status-bar'>\n"
            f"  <div class='sb sb-ok'>&#10003; {n_acima} fac&ccedil;&atilde;o(ões) acima da meta</div>\n"
            f"  <div class='sb sb-err'>&#9888; {n_abaixo} abaixo da meta</div>\n"
            f"  <div class='sb sb-na'>&#8212; {n_sem} sem meta cadastrada</div>\n"
            "</div>\n"
            "<div class='sec'>&#9654; Fac&ccedil;&atilde;o &times; Meta &mdash; Compara&ccedil;&atilde;o Direta</div>\n"
            f"{fac_meta_html}"
            "<div class='sec'>Progresso por Fac&ccedil;&atilde;o</div>\n"
            "<table>\n"
            "  <thead><tr><th>Fac&ccedil;&atilde;o</th>"
            "<th class='num'>Meta/Dia</th><th class='num'>Meta M&ecirc;s</th>"
            "<th class='num'>Produzido</th>"
            "<th class='num'>% Meta</th><th class='num'>Restante</th></tr></thead>\n"
            f"  <tbody>{tabela_html}</tbody>\n"
            "</table>\n"
            "<div class='sec'>Detalhe por Fac&ccedil;&atilde;o</div>\n"
            f"{detalhe_html}"
            "<div class='footer'>"
            f"Relatório Produção Facções &middot; {periodo_str} &middot; "
            f"Sistema Unificação dos Dados &middot; {agora}"
            "</div>\n</body>\n</html>"
        )
        return html.encode("utf-8")

    # ── Botão de download do relatório HTML ──────────────────────────────────
    st.markdown("---")
    _nome_arquivo = f"relatorio_faccoes_{data_ini.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.html"
    st.download_button(
        label="📄 Baixar Relatório HTML (abrir no navegador → Ctrl+P para PDF)",
        data=_html_faccoes_mensal(),
        file_name=_nome_arquivo,
        mime="text/html",
        use_container_width=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DIÁRIO
# ══════════════════════════════════════════════════════════════════════════════
elif _secao_faccoes == "📆 Diário":
    datas_disp = sorted(df["DATA"].dropna().dt.date.unique())

    if not datas_disp:
        st.info("Sem dados para os filtros selecionados.")
    else:
        data_sel = st.date_input(
            "Data",
            value=max(datas_disp),
            min_value=min(datas_disp),
            max_value=max(datas_disp),
            key="data_diario",
        )

        data_ts = pd.Timestamp(data_sel)
        df_dia = df[df["DATA"] == data_ts]

        total_dia  = int(df_dia["QUANTIDADE"].sum())
        meta_dia   = meta_mes_total / _dias_uteis(data_sel.year, data_sel.month)
        pct_dia    = total_dia / meta_dia * 100 if meta_dia > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Produção do Dia", _fmt(total_dia))
        with c2:
            st.metric("Meta Diária", _fmt(round(meta_dia)))
        with c3:
            st.metric("% da Meta", f"{pct_dia:.1f}%")

        st.markdown("---")

        saldo_dia = total_dia - meta_dia
        faccoes_ativas_dia = int(df_dia["FACCAO"].nunique())
        lider_dia = df_dia.groupby("FACCAO")["QUANTIDADE"].sum().sort_values(ascending=False).head(1)
        produto_lider_dia = df_dia.groupby("PRODUTO")["QUANTIDADE"].sum().sort_values(ascending=False).head(1)

        st.subheader("Resumo da Data")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            st.metric("Facções ativas", faccoes_ativas_dia)
        with c5:
            st.metric("Saldo vs meta", _fmt(abs(saldo_dia)), delta="acima" if saldo_dia >= 0 else "abaixo")
        with c6:
            st.metric(
                "Facção líder",
                lider_dia.index[0] if not lider_dia.empty else "—",
                delta=_fmt(int(lider_dia.iloc[0])) if not lider_dia.empty else None,
            )
        with c7:
            st.metric(
                "Produto líder",
                produto_lider_dia.index[0] if not produto_lider_dia.empty else "—",
                delta=_fmt(int(produto_lider_dia.iloc[0])) if not produto_lider_dia.empty else None,
            )

        if df_dia.empty:
            st.info(f"Sem produção em {data_sel.strftime('%d/%m/%Y')}.")
        else:
            col_g, col_t = st.columns([2, 1])

            with col_g:
                grp_dia = (
                    df_dia.groupby(["PRODUTO", "FACCAO"])["QUANTIDADE"]
                    .sum()
                    .reset_index()
                    .sort_values("QUANTIDADE", ascending=True)
                )
                fig = px.bar(
                    grp_dia,
                    x="QUANTIDADE",
                    y="PRODUTO",
                    color="FACCAO",
                    orientation="h",
                    color_discrete_map=CORES_FACCAO,
                    labels={
                        "QUANTIDADE": "Peças",
                        "PRODUTO":    "Produto",
                        "FACCAO":     "Facção",
                    },
                    title=f"Produção — {data_sel.strftime('%d/%m/%Y')}",
                )
                fig.update_layout(**DARK_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            with col_t:
                det = (
                    df_dia.groupby(["FACCAO", "PRODUTO", "CLIENTE"], as_index=False)
                    .agg(QUANTIDADE=("QUANTIDADE", "sum"), OBSERVACAO=("OBSERVACAO", _join_unique))
                    .sort_values("QUANTIDADE", ascending=False)
                )
                det.columns = ["Facção", "Produto", "Empresa", "Qtd", "Observações"]
                st.dataframe(det, use_container_width=True, hide_index=True)

            # Por prestador (somente QUARTERIZADAS / quando tem PRESTADOR)
            df_prest = df_dia[df_dia["PRESTADOR"].str.strip() != ""]
            if not df_prest.empty:
                st.markdown("**Detalhe por Prestador (Quarterizadas)**")
                prest_grp = (
                    df_prest.groupby(["PRESTADOR", "PRODUTO"])["QUANTIDADE"]
                    .sum()
                    .reset_index()
                    .sort_values("QUANTIDADE", ascending=False)
                )
                prest_grp.columns = ["Prestador", "Produto", "Qtd"]
                st.dataframe(prest_grp, use_container_width=True, hide_index=True)

            st.markdown("---")
            col_fac_dia, col_cli_dia = st.columns(2)

            with col_fac_dia:
                fac_dia = (
                    df_dia.groupby("FACCAO")["QUANTIDADE"]
                    .sum().reset_index().sort_values("QUANTIDADE", ascending=True)
                )
                fig_fac_dia = px.bar(
                    fac_dia,
                    x="QUANTIDADE",
                    y="FACCAO",
                    orientation="h",
                    color="FACCAO",
                    color_discrete_map=CORES_FACCAO,
                    text="QUANTIDADE",
                    labels={"QUANTIDADE": "Peças", "FACCAO": "Facção"},
                    title="Produção por Facção na Data",
                )
                fig_fac_dia.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                fig_fac_dia.update_layout(showlegend=False, **DARK_LAYOUT)
                st.plotly_chart(fig_fac_dia, use_container_width=True)

            with col_cli_dia:
                cli_dia = (
                    df_dia.groupby("CLIENTE")["QUANTIDADE"]
                    .sum().reset_index().sort_values("QUANTIDADE", ascending=True)
                )
                if cli_dia.empty:
                    st.info("Sem dados por empresa para a data selecionada.")
                else:
                    fig_cli_dia = px.bar(
                        cli_dia.tail(8),
                        x="QUANTIDADE",
                        y="CLIENTE",
                        orientation="h",
                        text="QUANTIDADE",
                        color="QUANTIDADE",
                        color_continuous_scale="Teal",
                        labels={"QUANTIDADE": "Peças", "CLIENTE": "Empresa"},
                        title="Top Empresas na Data",
                    )
                    fig_cli_dia.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                    fig_cli_dia.update_layout(coloraxis_showscale=False, **DARK_LAYOUT)
                    st.plotly_chart(fig_cli_dia, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SEMANAL
# ══════════════════════════════════════════════════════════════════════════════
elif _secao_faccoes == "📊 Semanal":
    datas_all = sorted(df["DATA"].dropna().dt.date.unique())

    if not datas_all:
        st.info("Sem dados para os filtros selecionados.")
    else:
        # Monta lista de semanas (segunda → sexta) disponíveis nos dados
        semanas_disponiveis = sorted({
            d - timedelta(days=d.weekday())
            for d in datas_all
        }, reverse=True)

        opcoes_semana = {
            f"{s.strftime('%d/%m')} a {(s + timedelta(days=4)).strftime('%d/%m/%Y')}": s
            for s in semanas_disponiveis
        }

        sem_escolhida_label = st.selectbox(
            "📅 Semana",
            options=list(opcoes_semana.keys()),
            index=0,
            key="sel_semana",
        )
        semana_ini = opcoes_semana[sem_escolhida_label]
        semana_fim = semana_ini + timedelta(days=4)

        st.markdown(
            f"**Semana:** {semana_ini.strftime('%d/%m')} a {semana_fim.strftime('%d/%m/%Y')}"
        )
        ref = min(semana_fim, max(datas_all))

        df_sem = df[
            (df["DATA"] >= pd.Timestamp(semana_ini))
            & (df["DATA"] <= pd.Timestamp(semana_fim))
        ]

        total_sem = int(df_sem["QUANTIDADE"].sum())
        pct_sem   = total_sem / meta_sem_total * 100 if meta_sem_total > 0 else 0
        dias_sem_passados = sum(
            1 for i in range(5)
            if (semana_ini + timedelta(days=i)) <= ref
        )
        meta_dia_sem  = meta_sem_total / 5 if meta_sem_total > 0 else 0
        esperado_sem  = dias_sem_passados * meta_dia_sem
        pct_ritmo_sem = total_sem / esperado_sem * 100 if esperado_sem > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Produção da Semana", _fmt(total_sem))
        with c2:
            st.metric("Meta Semanal", _fmt(meta_sem_total))
        with c3:
            st.metric("% da Meta", f"{pct_sem:.1f}%")
        with c4:
            st.metric("Ritmo", f"{pct_ritmo_sem:.1f}%",
                      delta=f"{pct_ritmo_sem - 100:+.1f}pp")

        st.markdown("---")

        if df_sem.empty:
            st.info("Sem produção registrada nesta semana.")
        else:
            DIAS_PT = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
                       "Thursday": "Qui", "Friday": "Sex"}

            prod_semana = (
                df_sem.groupby("PRODUTO")["QUANTIDADE"]
                .sum().reset_index().sort_values("QUANTIDADE", ascending=False)
            )
            if not prod_semana.empty:
                st.markdown("#### 📦 Produtos produzidos na semana")
                c_prod_graf, c_prod_tab = st.columns([2, 1])

                daily_sem = (
                    df_sem.groupby(["DATA", "PRODUTO"])["QUANTIDADE"]
                    .sum()
                    .reset_index()
                )
                daily_sem["DIA"] = daily_sem["DATA"].dt.day_name().map(
                    lambda d: DIAS_PT.get(d, d)
                ) + " " + daily_sem["DATA"].dt.strftime("%d/%m")
                ordem_dias = sorted(daily_sem["DATA"].unique())
                ordem_labels = [
                    (DIAS_PT.get(pd.Timestamp(d).day_name(), "") + " " + pd.Timestamp(d).strftime("%d/%m"))
                    for d in ordem_dias
                ]
                top_prod_sem = prod_semana.head(6)["PRODUTO"].tolist()
                daily_top = daily_sem[daily_sem["PRODUTO"].isin(top_prod_sem)].copy()

                with c_prod_graf:
                    fig_prod_sem = px.line(
                        daily_top,
                        x="DIA",
                        y="QUANTIDADE",
                        color="PRODUTO",
                        markers=True,
                        category_orders={"DIA": ordem_labels},
                        color_discrete_sequence=px.colors.qualitative.Set2,
                        labels={"QUANTIDADE": "Peças", "DIA": "Dia", "PRODUTO": "Produto"},
                        title="Evolução dos Principais Produtos na Semana",
                    )
                    fig_prod_sem.update_layout(**DARK_LAYOUT)
                    st.plotly_chart(fig_prod_sem, use_container_width=True)

                with c_prod_tab:
                    tab_prod_sem = prod_semana.head(10).copy()
                    tab_prod_sem.columns = ["Produto", "Produzido"]
                    st.dataframe(
                        tab_prod_sem,
                        use_container_width=True,
                        hide_index=True,
                    )

                pivot_sem = (
                    daily_sem.pivot_table(index="PRODUTO", columns="DIA", values="QUANTIDADE", aggfunc="sum", fill_value=0)
                )
                pivot_sem = pivot_sem.reindex(index=prod_semana.head(8)["PRODUTO"].tolist())
                if not pivot_sem.empty:
                    st.markdown("##### Matriz por Produto e Dia")
                    st.dataframe(
                        pivot_sem,
                        use_container_width=True,
                    )

            saldo_sem = total_sem - meta_sem_total
            # Só conta dias com QUANTIDADE > 0 (feedback do usuário 14/07/2026).
            dias_sem_prod = int(df_sem[df_sem["QUANTIDADE"] > 0]["DATA"].dt.date.nunique())
            media_dia_sem_prod = total_sem / dias_sem_prod if dias_sem_prod else 0
            fac_sem = (
                df_sem.groupby("FACCAO")["QUANTIDADE"]
                .sum().reset_index().sort_values("QUANTIDADE", ascending=False)
            )
            dia_sem_total = (
                df_sem.groupby("DATA")["QUANTIDADE"].sum().reset_index().sort_values("DATA")
            )

            st.markdown("---")
            st.subheader("Resumo da Semana")
            c5, c6, c7, c8 = st.columns(4)
            with c5:
                st.metric("Dias com produção", dias_sem_prod)
            with c6:
                st.metric("Média/dia", _fmt(round(media_dia_sem_prod)))
            with c7:
                st.metric("Saldo da meta", _fmt(abs(saldo_sem)), delta="acima" if saldo_sem >= 0 else "abaixo")
            with c8:
                st.metric(
                    "Facção líder",
                    fac_sem.iloc[0]["FACCAO"] if not fac_sem.empty else "—",
                    delta=_fmt(int(fac_sem.iloc[0]["QUANTIDADE"])) if not fac_sem.empty else None,
                )

            col_sem_dia, col_sem_fac = st.columns(2)

            with col_sem_dia:
                dia_sem_total["DIA"] = dia_sem_total["DATA"].dt.day_name().map(
                    lambda d: DIAS_PT.get(d, d)
                ) + " " + dia_sem_total["DATA"].dt.strftime("%d/%m")
                fig_semana_total = px.bar(
                    dia_sem_total,
                    x="DIA",
                    y="QUANTIDADE",
                    text="QUANTIDADE",
                    labels={"QUANTIDADE": "Peças", "DIA": "Dia"},
                    title="Produção Total por Dia da Semana",
                )
                if meta_dia_sem > 0:
                    fig_semana_total.add_hline(
                        y=meta_dia_sem,
                        line_dash="dash",
                        line_color="#FF6B6B",
                        annotation_text=f"Meta/dia ({_fmt(round(meta_dia_sem))})",
                        annotation_position="top right",
                    )
                fig_semana_total.update_traces(marker_color="#4ECDC4", texttemplate="%{text:,.0f}", textposition="outside")
                fig_semana_total.update_layout(**DARK_LAYOUT)
                st.plotly_chart(fig_semana_total, use_container_width=True)

            with col_sem_fac:
                if fac_sem.empty:
                    st.info("Sem facções para resumir na semana.")
                else:
                    fig_sem_faccao = px.bar(
                        fac_sem.sort_values("QUANTIDADE"),
                        x="QUANTIDADE",
                        y="FACCAO",
                        orientation="h",
                        color="FACCAO",
                        color_discrete_map=CORES_FACCAO,
                        text="QUANTIDADE",
                        labels={"QUANTIDADE": "Peças", "FACCAO": "Facção"},
                        title="Produção por Facção na Semana",
                    )
                    fig_sem_faccao.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                    fig_sem_faccao.update_layout(showlegend=False, **DARK_LAYOUT)
                    st.plotly_chart(fig_sem_faccao, use_container_width=True)

            prod_sem = (
                df_sem.groupby("PRODUTO")["QUANTIDADE"]
                .sum().reset_index().sort_values("QUANTIDADE", ascending=False)
            )
            if prod_sem.empty:
                st.info("Sem produção por produto no período selecionado.")
            else:
                prod_sem["% do Total"] = (prod_sem["QUANTIDADE"] / max(total_sem, 1) * 100).round(1)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — POR PRODUTO
# ══════════════════════════════════════════════════════════════════════════════
elif _secao_faccoes == "📦 Por Produto":
    df_mp = df[
        (df["DATA"].dt.date >= data_ini) & (df["DATA"].dt.date <= data_fim)
    ]

    if df_mp.empty:
        st.info("Sem dados no período selecionado para os filtros escolhidos.")
    else:
        prod_tot = (
            df_mp.groupby("PRODUTO")["QUANTIDADE"].sum()
            .reset_index().sort_values("QUANTIDADE", ascending=False)
        )
        total_prod = int(prod_tot["QUANTIDADE"].sum())
        lider = prod_tot.iloc[0]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Produtos diferentes", len(prod_tot))
        with c2:
            st.metric("Produto líder", lider["PRODUTO"].title())
        with c3:
            _share = lider["QUANTIDADE"] / total_prod * 100 if total_prod else 0
            st.metric("Peças do líder", _fmt(lider["QUANTIDADE"]),
                      delta=f"{_share:.0f}% do total")

        st.markdown("---")

        # Ranking de produção + mix (donut)
        col_rank, col_mix = st.columns([3, 2])
        with col_rank:
            fig_rank = px.bar(
                prod_tot.sort_values("QUANTIDADE"),
                x="QUANTIDADE", y="PRODUTO", orientation="h", text="QUANTIDADE",
                color="QUANTIDADE", color_continuous_scale="Teal",
                labels={"QUANTIDADE": "Peças", "PRODUTO": "Produto"},
                title="Ranking de Produção por Produto",
            )
            fig_rank.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_rank.update_layout(coloraxis_showscale=False, **DARK_LAYOUT)
            st.plotly_chart(fig_rank, use_container_width=True)
        with col_mix:
            fig_mix = px.pie(
                prod_tot, names="PRODUTO", values="QUANTIDADE", hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set3,
                title="Mix de Produtos",
            )
            fig_mix.update_traces(textposition="inside", textinfo="percent")
            fig_mix.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_mix, use_container_width=True)

        # Treemap: composição produto → empresa
        st.markdown("---")
        tree = (
            df_mp.groupby(["PRODUTO", "CLIENTE"])["QUANTIDADE"].sum().reset_index()
        )
        tree = tree[tree["QUANTIDADE"] > 0]
        fig_tree = px.treemap(
            tree, path=[px.Constant("Todos"), "PRODUTO", "CLIENTE"],
            values="QUANTIDADE",
            color="QUANTIDADE", color_continuous_scale="Teal",
            title="Composição: Produto → Empresa",
        )
        fig_tree.update_traces(
            texttemplate="%{label}<br>%{value:,.0f}",
            hovertemplate="%{label}<br><b>%{value:,.0f}</b> peças<extra></extra>",
        )
        fig_tree.update_layout(margin=dict(t=50, l=10, r=10, b=10), **DARK_LAYOUT)
        st.plotly_chart(fig_tree, use_container_width=True)

        # Heatmap pivot: produto × empresa — uma célula por combinação
        st.markdown("---")
        pivot = (
            tree.groupby(["PRODUTO", "CLIENTE"])["QUANTIDADE"]
            .sum()
            .unstack(fill_value=0)
        )
        # Ordena produtos: maior total no topo
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
        pivot = pivot.sort_index(axis=1)

        z_raw = pivot.values.astype(float)
        # Escala log para que valores pequenos também fiquem coloridos;
        # zeros ficam como NaN (célula transparente → sem cor)
        z_color = np.where(z_raw > 0, np.log1p(z_raw), np.nan)
        text_arr = [
            [f"{int(v):,}".replace(",", ".") if v > 0 else "" for v in row]
            for row in z_raw
        ]
        n_rows = len(pivot)
        fig_heat = go.Figure(go.Heatmap(
            z=z_color,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            text=text_arr,
            texttemplate="%{text}",
            textfont=dict(color="white", size=13),
            colorscale=[[0, "#1a4a8a"], [0.5, "#1976d2"], [1.0, "#64b5f6"]],
            showscale=False,
            hovertemplate="<b>%{y}</b><br>%{x}: %{text} peças<extra></extra>",
        ))
        fig_heat.update_layout(
            title="Produção por Produto e Empresa",
            xaxis_title="Empresa",
            yaxis_title="",
            height=max(420, n_rows * 40 + 120),
            margin=dict(t=60, l=180, r=20, b=60),
            **DARK_LAYOUT,
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Evolução diária dos principais produtos
        st.markdown("---")
        top_n = prod_tot.head(6)["PRODUTO"].tolist()
        evol = (
            df_mp[df_mp["PRODUTO"].isin(top_n)]
            .groupby(["DATA", "PRODUTO"])["QUANTIDADE"].sum().reset_index()
        )
        fig_evol = px.line(
            evol, x="DATA", y="QUANTIDADE", color="PRODUTO", markers=True,
            color_discrete_sequence=px.colors.qualitative.Bold,
            labels={"QUANTIDADE": "Peças", "DATA": "Data", "PRODUTO": "Produto"},
            title=f"Evolução Diária — Top {len(top_n)} Produtos",
        )
        fig_evol.update_layout(**DARK_LAYOUT)
        st.plotly_chart(fig_evol, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — POR FACÇÃO
# ══════════════════════════════════════════════════════════════════════════════
elif _secao_faccoes == "🏭 Por Facção":
    df_fac = df[
        (df["DATA"].dt.date >= data_ini) & (df["DATA"].dt.date <= data_fim)
    ]

    if df_fac.empty:
        st.info("Sem dados no período selecionado para os filtros escolhidos.")
    else:
        total_geral_fac = int(df_fac["QUANTIDADE"].sum())
        fac_grp = (
            df_fac.groupby("FACCAO")["QUANTIDADE"]
            .sum().reset_index()
            .sort_values("QUANTIDADE", ascending=False)
        )
        n_faccoes = len(fac_grp)
        lider_fac = fac_grp.iloc[0]

        # ── KPIs ─────────────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Facções Ativas", n_faccoes)
        k2.metric("Total Produzido", _fmt(total_geral_fac))
        k3.metric("Facção Líder", lider_fac["FACCAO"])
        k4.metric("Participação da Líder",
                  f"{lider_fac['QUANTIDADE'] / total_geral_fac * 100:.1f}%")

        st.divider()

        # ── Visão geral: pizza + diário stacked ──────────────────────────────────
        st.markdown("#### 📊 Visão Geral")
        col_pie, col_bar = st.columns(2)

        with col_pie:
            fig_pie = px.pie(
                fac_grp, names="FACCAO", values="QUANTIDADE",
                title=f"% por Facção — {_periodo_label}",
                color="FACCAO", color_discrete_map=CORES_FACCAO, hole=0.4,
            )
            fig_pie.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            daily_fac = (
                df_fac.groupby(["DATA", "FACCAO"])["QUANTIDADE"]
                .sum().reset_index()
            )
            daily_fac["DATA_STR"] = daily_fac["DATA"].dt.strftime("%d/%m")
            fig_stk = px.bar(
                daily_fac, x="DATA_STR", y="QUANTIDADE", color="FACCAO",
                color_discrete_map=CORES_FACCAO,
                labels={"QUANTIDADE": "Peças", "DATA_STR": "Dia", "FACCAO": "Facção"},
                title="Produção Diária por Facção",
            )
            fig_stk.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_stk, use_container_width=True)

        st.divider()

        # ── Ranking com meta ─────────────────────────────────────────────────────
        st.markdown("#### 🏆 Ranking e Atingimento de Meta")

        # rank_df já foi pré-computado antes das tabs com o mesmo período/filtro.
        # Aqui usamos diretamente — apenas recalculamos % do total com base em df_fac.
        rank_df_fac = rank_df.copy()
        if not df_fac.empty:
            rank_df_fac["% do Total"] = (rank_df_fac["QUANTIDADE"] / total_geral_fac * 100).round(1)

        # ── Comparação direta: Facção x Meta (destaque) ──────────────────────────
        st.markdown("##### 📊 Facção × Meta — Comparação Direta")
        rk_todos = rank_df_fac.sort_values("PCT", ascending=True, na_position="last")

        # Gráfico agrupado: produzido vs meta lado a lado
        fig_comp = go.Figure()
        fig_comp.add_bar(
            name="Meta Mês",
            y=rk_todos["FACCAO"],
            x=rk_todos["META_MES"],
            orientation="h",
            marker_color="rgba(255,107,107,0.35)",
            marker_line=dict(color="#FF6B6B", width=1),
            hovertemplate="<b>%{y}</b><br>Meta: %{x:,.0f}<extra></extra>",
        )
        fig_comp.add_bar(
            name="Produzido",
            y=rk_todos["FACCAO"],
            x=rk_todos["QUANTIDADE"],
            orientation="h",
            marker_color=[
                "#4ECDC4" if (pd.notna(p) and p >= 100) else "#FFA726" if (pd.notna(p) and p >= 75) else "#FF6B6B"
                for p in rk_todos["PCT"]
            ],
            text=[
                f"{p:.0f}%" if pd.notna(p) else "sem meta"
                for p in rk_todos["PCT"]
            ],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Produzido: %{x:,.0f}<extra></extra>",
        )
        fig_comp.update_layout(
            barmode="overlay",
            title="Produzido vs Meta por Facção",
            xaxis_title="Peças", yaxis_title="",
            height=max(400, len(rk_todos) * 38 + 120),
            **DARK_LAYOUT,
        )
        fig_comp.update_layout(legend=dict(orientation="h", y=1.08, x=0))
        st.plotly_chart(fig_comp, use_container_width=True)

        col_rank1, col_rank2 = st.columns(2)
        with col_rank1:
            rk = rank_df_fac.sort_values("QUANTIDADE", ascending=True)
            cores_rk = [CORES_FACCAO.get(f, "#4ECDC4") for f in rk["FACCAO"]]
            fig_rank = go.Figure(go.Bar(
                y=rk["FACCAO"], x=rk["QUANTIDADE"], orientation="h",
                marker_color=cores_rk,
                text=[_fmt(v) for v in rk["QUANTIDADE"]], textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} peças<extra></extra>",
            ))
            fig_rank.update_layout(
                title="Produção Total por Facção",
                xaxis_title="Peças", yaxis_title="", **DARK_LAYOUT,
            )
            st.plotly_chart(fig_rank, use_container_width=True)

        with col_rank2:
            rk_meta = rank_df_fac[rank_df_fac["PCT"].notna()].sort_values("PCT", ascending=True)
            if rk_meta.empty:
                st.info("Nenhuma facção com meta cadastrada no período.")
            else:
                cores_m = rk_meta["PCT"].apply(
                    lambda v: "#4ECDC4" if v >= 100 else "#FFA726" if v >= 75 else "#FF6B6B"
                )
                fig_meta = go.Figure(go.Bar(
                    y=rk_meta["FACCAO"], x=rk_meta["PCT"], orientation="h",
                    marker_color=cores_m,
                    text=[f"{p:.0f}%" for p in rk_meta["PCT"]], textposition="outside",
                    hovertemplate="<b>%{y}</b><br>%{x:.1f}% da meta<extra></extra>",
                ))
                fig_meta.add_vline(x=100, line_dash="dash", line_color="#FFFFFF",
                                   annotation_text="Meta", annotation_position="top")
                fig_meta.update_layout(
                    title="% da Meta Mensal por Facção",
                    xaxis_title="% da Meta", yaxis_title="", **DARK_LAYOUT,
                )
                st.plotly_chart(fig_meta, use_container_width=True)

        # Tabela completa Facção x Meta
        tab_rank = rank_df_fac[["FACCAO", "QUANTIDADE", "% do Total", "META_MES", "META_DIA", "PCT", "RESTANTE"]].copy()
        tab_rank.columns = ["Facção", "Produzido", "% do Total", "Meta Mês", "Meta/Dia", "% da Meta", "Restante"]
        tab_rank = tab_rank.sort_values("Produzido", ascending=False).reset_index(drop=True)
        tab_rank["Meta Mês"] = tab_rank["Meta Mês"].replace(0.0, None)
        tab_rank["Meta/Dia"] = tab_rank["Meta/Dia"].replace(0.0, None)
        def _safe_fmt(v):
            try:
                return _fmt(v) if v is not None and not pd.isna(v) else "—"
            except Exception:
                return "—"

        def _safe_pct(v):
            try:
                return f"{float(v):.1f}%" if v is not None and not pd.isna(v) else "—"
            except Exception:
                return "—"

        st.dataframe(
            tab_rank.style
            .map(_color_pct, subset=["% da Meta"])
            .format({
                "Produzido":  "{:,.0f}",
                "% do Total": "{:.1f}%",
                "Meta Mês":   _safe_fmt,
                "Meta/Dia":   _safe_fmt,
                "% da Meta":  _safe_pct,
                "Restante":   _safe_fmt,
            }),
            use_container_width=True, hide_index=True,
        )

        st.divider()

        # ── Análise de Consistência ──────────────────────────────────────────────
        st.markdown("#### 📈 Análise de Consistência por Facção")
        st.caption(
            "**Regularidade** mede a uniformidade da produção diária "
            "(100% = produção perfeitamente constante; coeficiente de variação = 0). "
            "**Assiduidade** mostra em quantos dias úteis do período houve produção."
        )

        du_per = contar_dias_uteis(data_ini, data_fim)

        # Vetorizado — antes era um loop Python por facção, cada uma refazendo
        # seu próprio groupby diário; agora é um único groupby geral (por
        # facção×dia) seguido de agregações vetorizadas. Mesmo resultado, sem
        # o custo de N sub-DataFrames recalculados a cada rerun (reportado
        # pelo usuário 15/07/2026 — dashboard lento).
        _diario_fac = (
            df_fac.assign(_DIA=df_fac["DATA"].dt.date)
            .groupby(["FACCAO", "_DIA"])["QUANTIDADE"].sum()
            .rename("QTD_DIA").reset_index()
        )
        _g = _diario_fac.groupby("FACCAO")["QTD_DIA"]
        df_cons = pd.DataFrame({
            "Dias Ativos": _g.size(),
            "_total":      _g.sum(),
            "Melhor Dia":  _g.max(),
            "_std":        _g.std(ddof=0),
        }).reset_index()
        df_cons["Média/Dia"] = (df_cons["_total"] / df_cons["Dias Ativos"]).fillna(0)
        _cv = np.where(
            (df_cons["Dias Ativos"] >= 2) & (df_cons["Média/Dia"] > 0),
            df_cons["_std"] / df_cons["Média/Dia"],
            np.nan,
        )
        df_cons["Regularidade (%)"] = np.where(
            ~np.isnan(_cv),
            np.clip(100.0 * (1.0 - _cv), 0.0, 100.0),
            np.where(df_cons["Dias Ativos"] >= 1, 100.0, 0.0),
        )
        df_cons["Assiduidade (%)"] = (
            (df_cons["Dias Ativos"] / du_per * 100).clip(upper=100) if du_per > 0 else 0.0
        )
        _pior = (
            _diario_fac[_diario_fac["QTD_DIA"] > 0]
            .groupby("FACCAO")["QTD_DIA"].min()
            .rename("Pior Dia (>0)")
        )
        df_cons = df_cons.merge(_pior, on="FACCAO", how="left")
        df_cons["Pior Dia (>0)"] = df_cons["Pior Dia (>0)"].fillna(0).astype(int)

        df_cons["Dias Ativos"]      = df_cons["Dias Ativos"].astype(int)
        df_cons["Média/Dia"]        = df_cons["Média/Dia"].round().astype(int)
        df_cons["Regularidade (%)"] = df_cons["Regularidade (%)"].round(1)
        df_cons["Assiduidade (%)"]  = df_cons["Assiduidade (%)"].round(1)
        df_cons["Melhor Dia"]       = df_cons["Melhor Dia"].astype(int)
        df_cons = df_cons[["FACCAO", "Dias Ativos", "Assiduidade (%)", "Média/Dia",
                            "Regularidade (%)", "Melhor Dia", "Pior Dia (>0)"]]

        col_cons1, col_cons2 = st.columns(2)
        with col_cons1:
            df_reg = df_cons.sort_values("Regularidade (%)", ascending=True)
            cores_reg = df_reg["Regularidade (%)"].apply(
                lambda v: "#4ECDC4" if v >= 80 else "#FFA726" if v >= 60 else "#FF6B6B"
            )
            fig_reg = go.Figure(go.Bar(
                y=df_reg["FACCAO"], x=df_reg["Regularidade (%)"], orientation="h",
                marker_color=cores_reg,
                text=[f"{v:.0f}%" for v in df_reg["Regularidade (%)"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Regularidade: %{x:.1f}%<extra></extra>",
            ))
            fig_reg.add_vline(x=80, line_dash="dash", line_color="#4ECDC4",
                              annotation_text="Boa (80%)", annotation_position="top")
            fig_reg.update_layout(title="Regularidade da Produção", yaxis_title="", **DARK_LAYOUT)
            fig_reg.update_xaxes(range=[0, 120], title_text="Regularidade (%)")
            st.plotly_chart(fig_reg, use_container_width=True)

        with col_cons2:
            df_ass = df_cons.sort_values("Assiduidade (%)", ascending=True)
            cores_ass = df_ass["Assiduidade (%)"].apply(
                lambda v: "#4ECDC4" if v >= 80 else "#FFA726" if v >= 50 else "#FF6B6B"
            )
            fig_ass = go.Figure(go.Bar(
                y=df_ass["FACCAO"], x=df_ass["Assiduidade (%)"], orientation="h",
                marker_color=cores_ass,
                text=[f"{v:.0f}%" for v in df_ass["Assiduidade (%)"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Assiduidade: %{x:.1f}%<extra></extra>",
            ))
            fig_ass.add_vline(x=80, line_dash="dash", line_color="#4ECDC4",
                              annotation_text="Boa (80%)", annotation_position="top")
            fig_ass.update_layout(
                title=f"Assiduidade — dias com produção / {du_per} dias úteis",
                yaxis_title="", **DARK_LAYOUT,
            )
            fig_ass.update_xaxes(range=[0, 120], title_text="Assiduidade (%)")
            st.plotly_chart(fig_ass, use_container_width=True)

        tab_cons = df_cons.sort_values("Regularidade (%)", ascending=False).reset_index(drop=True)
        st.dataframe(
            tab_cons.style
            .map(lambda v: _color_pct(v, t_green=80, t_yellow=60), subset=["Assiduidade (%)", "Regularidade (%)"])
            .format({
                "Média/Dia":         "{:,.0f}",
                "Melhor Dia":        "{:,.0f}",
                "Pior Dia (>0)":     "{:,.0f}",
                "Assiduidade (%)":   "{:.1f}%",
                "Regularidade (%)":  "{:.1f}%",
            }),
            use_container_width=True, hide_index=True,
            column_config={"FACCAO": st.column_config.TextColumn("Facção")},
        )

        st.divider()

        # ── Heatmap Facção × Dia ─────────────────────────────────────────────────
        st.markdown("#### 🗓 Mapa de Calor — Produção por Facção e Dia")
        st.caption("Cor mais intensa = maior volume. Células em branco = sem produção naquele dia. (Mostra toda a produção da facção no período, independente dos filtros de produto/cliente.)")

        # Usa df_all filtrado apenas por data para mostrar TODOS os dias de cada facção,
        # independente dos filtros de produto/cliente aplicados na sidebar.
        df_fac_hm = df_all[
            (df_all["DATA"].dt.date >= data_ini) & (df_all["DATA"].dt.date <= data_fim)
        ].copy()
        df_fac_hm["DATA_DAY"] = df_fac_hm["DATA"].dt.normalize()

        pivot_hm = df_fac_hm.pivot_table(
            index="FACCAO",
            columns="DATA_DAY",
            values="QUANTIDADE",
            aggfunc="sum",
            fill_value=0,
        )
        pivot_hm = pivot_hm[sorted(pivot_hm.columns)]
        col_labels_hm = [pd.Timestamp(c).strftime("%d/%m") for c in pivot_hm.columns]

        z_raw_hm = pivot_hm.values.astype(float)
        z_color_hm = np.where(z_raw_hm > 0, np.log1p(z_raw_hm), np.nan)
        text_hm = [
            [f"{int(v):,}".replace(",", ".") if v > 0 else "" for v in row]
            for row in z_raw_hm
        ]

        fig_hm = go.Figure(go.Heatmap(
            z=z_color_hm,
            x=col_labels_hm,
            y=pivot_hm.index.tolist(),
            text=text_hm,
            texttemplate="%{text}",
            textfont=dict(color="white", size=9),
            colorscale=[[0, "#1a3a5c"], [0.5, "#2aa89a"], [1, "#4ECDC4"]],
            showscale=False,
            hovertemplate="<b>%{y}</b><br>%{x}: %{text} peças<extra></extra>",
        ))
        fig_hm.update_layout(
            title="Mapa de Calor: Facção × Dia (escala log de cores)",
            xaxis_title="Dia", yaxis_title="",
            height=max(350, len(pivot_hm) * 38 + 120),
            margin=dict(t=60, l=170, r=20, b=50),
            **DARK_LAYOUT,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

        st.divider()

        # ── Evolução acumulada por facção ────────────────────────────────────────
        st.markdown("#### 📈 Evolução Acumulada por Facção")

        evol = (
            df_fac.groupby(["DATA", "FACCAO"])["QUANTIDADE"]
            .sum().reset_index().sort_values(["FACCAO", "DATA"])
        )
        evol["ACUM"] = evol.groupby("FACCAO")["QUANTIDADE"].cumsum()
        evol["DATA_STR"] = evol["DATA"].dt.strftime("%d/%m")

        fig_evol = px.line(
            evol, x="DATA_STR", y="ACUM", color="FACCAO",
            color_discrete_map=CORES_FACCAO, markers=True,
            labels={"ACUM": "Peças acumuladas", "DATA_STR": "Dia", "FACCAO": "Facção"},
            title="Produção Acumulada por Facção no Período",
        )
        fig_evol.update_layout(**DARK_LAYOUT)
        st.plotly_chart(fig_evol, use_container_width=True)

        # ── Produção diária por facção ────────────────────────────────────────────
        st.markdown("#### 📊 Produção Diária por Facção")

        diario = (
            df_fac.groupby(["DATA", "FACCAO"])["QUANTIDADE"]
            .sum().reset_index().sort_values(["FACCAO", "DATA"])
        )
        diario["DATA_STR"] = diario["DATA"].dt.strftime("%d/%m")

        fig_diario = px.line(
            diario, x="DATA_STR", y="QUANTIDADE", color="FACCAO",
            color_discrete_map=CORES_FACCAO, markers=True,
            labels={"QUANTIDADE": "Peças no dia", "DATA_STR": "Dia", "FACCAO": "Facção"},
            title="Produção Diária por Facção no Período",
        )
        fig_diario.update_layout(**DARK_LAYOUT)
        st.plotly_chart(fig_diario, use_container_width=True)

        st.divider()

        # ── Mix de produtos por facção ───────────────────────────────────────────
        st.markdown("#### 📦 Mix de Produtos por Facção")

        fac_prod = (
            df_fac.groupby(["FACCAO", "PRODUTO"])["QUANTIDADE"]
            .sum().reset_index()
        )
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
            st.plotly_chart(fig_mix, use_container_width=True)

        with col_mix2:
            # Heatmap produto × facção
            piv_pf = fac_prod.pivot_table(
                index="PRODUTO", columns="FACCAO",
                values="QUANTIDADE", aggfunc="sum", fill_value=0,
            )
            z_pf = piv_pf.values.astype(float)
            z_pf_color = np.where(z_pf > 0, np.log1p(z_pf), np.nan)
            text_pf = [
                [f"{int(v):,}".replace(",", ".") if v > 0 else "" for v in row]
                for row in z_pf
            ]
            fig_pf = go.Figure(go.Heatmap(
                z=z_pf_color,
                x=piv_pf.columns.tolist(),
                y=piv_pf.index.tolist(),
                text=text_pf,
                texttemplate="%{text}",
                textfont=dict(color="white", size=9),
                colorscale=[[0, "#3D2817"], [0.5, "#D97706"], [1, "#FBBF24"]],
                showscale=False,
                hovertemplate="<b>%{y}</b> → %{x}<br>%{text} peças<extra></extra>",
            ))
            fig_pf.update_layout(
                title="Produto × Facção (peças)",
                xaxis_title="Facção", yaxis_title="",
                height=max(350, len(piv_pf) * 32 + 120),
                margin=dict(t=50, l=160, r=20, b=80),
                **DARK_LAYOUT,
            )
            st.plotly_chart(fig_pf, use_container_width=True)

        st.divider()

        # ── Tabela de detalhe ────────────────────────────────────────────────────
        st.markdown("#### 📋 Detalhe por Facção / Produto / Empresa")

        det_fac = (
            df_fac.groupby(["PRODUTO_N", "CLIENTE_N", "FACCAO", "PRODUTO", "CLIENTE"])["QUANTIDADE"]
            .sum().reset_index()
            .sort_values(["FACCAO", "QUANTIDADE"], ascending=[True, False])
        )
        tot_prod_fac = det_fac.groupby(["PRODUTO_N", "CLIENTE_N"])["QUANTIDADE"].sum().rename("TOTAL_PROD")
        det_fac = det_fac.merge(tot_prod_fac, on=["PRODUTO_N", "CLIENTE_N"], how="left")
        gf_agg = (
            gf.groupby(["PRODUTO_N", "CLIENTE_N"])
            .agg(META_MES=("META_MES", "sum"))
            .reset_index()
        )
        det_fac = det_fac.merge(gf_agg, on=["PRODUTO_N", "CLIENTE_N"], how="left")
        det_fac["META_MES"] = det_fac["META_MES"].fillna(0).astype(int)
        det_fac["% Meta"] = det_fac.apply(
            lambda r: round(r["TOTAL_PROD"] / r["META_MES"] * 100, 1)
            if r["META_MES"] > 0 else None,
            axis=1,
        )
        det_fac = det_fac[["FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE", "META_MES", "% Meta"]]
        det_fac.columns = ["Facção", "Produto", "Empresa", "Produzido", "Meta Mês", "% Meta"]
        st.dataframe(
            det_fac.style
            .map(_color_pct, subset=["% Meta"])
            .format({
                "Produzido": "{:,.0f}",
                "Meta Mês":  lambda v: _fmt(v) if v > 0 else "—",
                "% Meta":    lambda v: f"{v:.1f}%" if v is not None else "—",
            }),
            use_container_width=True, hide_index=True,
        )
