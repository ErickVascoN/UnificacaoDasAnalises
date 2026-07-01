"""Histórico — Banco de dados local (SQLite). Acesso restrito ao Admin."""

import io
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.auth import init_session_state
from styles.global_ui import get_global_ui_css
from utils.db_manager import tabelas_status, query as db_query
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button

st.set_page_config(
    page_title="Histórico — Banco de Dados",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

st.markdown("""
<style>
    footer {visibility: hidden;}
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1C1C22 0%, #28282E 100%);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 16px 20px;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111115 0%, #191920 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    section[data-testid="stSidebar"] * { color: #E0E0E0 !important; }
</style>
""", unsafe_allow_html=True)

DARK_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0"),
    xaxis=dict(gridcolor="#2D3748"),
    yaxis=dict(gridcolor="#2D3748"),
    separators=",.",
)

TABELAS_INFO = {
    "faccoes":           {"label": "Produção — Facções Externas",      "col_qtd": "QUANTIDADE",  "col_grupo": "FACCAO"},
    "producao_interna":  {"label": "Produção — Interna (LITTEX/GGTTEX)", "col_qtd": "QUANTIDADE", "col_grupo": "UNIDADE"},
    "corte_arealva_manta": {"label": "Corte — Arealva Manta",          "col_qtd": "QUANTIDADE",  "col_grupo": "ESTACAO"},
    "corte_iacanga":     {"label": "Corte — Iacanga (Giattex)",         "col_qtd": "QUANTIDADE",  "col_grupo": "ESTACAO"},
    "corte_lencol":      {"label": "Corte — Lençol Arealva",            "col_qtd": "QUANT",       "col_grupo": "PRESTADOR"},
    "previsao_cargas":   {"label": "Previsão de Cargas",                "col_qtd": "PREVISAO",    "col_grupo": "DESTINO"},
    "programacao_corte": {"label": "Programação de Corte",              "col_qtd": "QNT. PROG",   "col_grupo": "CLIENTE"},
}

# ── Auth ───────────────────────────────────────────────────────────────────────
init_session_state()
if st.session_state.get("auth_nivel") != "admin":
    st.warning("🔒 Esta página é restrita ao Administrador.")
    st.stop()

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
st.markdown('<h1 style="color:#FFFFFF;font-size:2rem;font-weight:800;">🗄️ Histórico — Banco de Dados</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#A0A0A0;">Backup local SQLite de todos os dados da central. Atualizado automaticamente a cada carregamento.</p>', unsafe_allow_html=True)
render_filtros_btn()
st.markdown("---")

# ── Status geral do banco ──────────────────────────────────────────────────────
status_df = tabelas_status()
if status_df.empty:
    st.info("O banco ainda está vazio. Acesse as páginas de dados para iniciar a coleta automática.")
    st.stop()

st.subheader("Status do Banco")
total_reg = int(status_df["Registros"].sum())
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Tabelas", len(status_df))
with col2:
    st.metric("Total de Registros", f"{total_reg:,.0f}".replace(",", "."))
with col3:
    from pathlib import Path
    db_path = Path("data/zanattex.db")
    tamanho = f"{db_path.stat().st_size / 1024:.1f} KB" if db_path.exists() else "—"
    st.metric("Tamanho do Arquivo", tamanho)

status_show = status_df.copy()
status_show["Registros"] = status_show["Registros"].apply(lambda n: f"{n:,.0f}".replace(",", "."))
st.dataframe(status_show, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Consulta interativa ────────────────────────────────────────────────────────
st.subheader("Consultar Dados")

tabelas_disponiveis = [t for t in TABELAS_INFO if t in status_df["Tabela"].values]
if not tabelas_disponiveis:
    st.info("Nenhuma tabela com dados ainda.")
    st.stop()

render_home_button()

with st.sidebar:
    st.markdown("### 🗄️ Histórico")

    tabela_sel = st.selectbox(
        "Tabela",
        tabelas_disponiveis,
        format_func=lambda t: TABELAS_INFO.get(t, {}).get("label", t),
    )

    info = TABELAS_INFO.get(tabela_sel, {})

    col_data_min = status_df.loc[status_df["Tabela"] == tabela_sel, "Data Mínima"].iloc[0]
    col_data_max = status_df.loc[status_df["Tabela"] == tabela_sel, "Data Máxima"].iloc[0]

    try:
        d_min = pd.to_datetime(col_data_min).date()
        d_max = pd.to_datetime(col_data_max).date()
    except Exception:
        from datetime import date
        d_min = date(2024, 1, 1)
        d_max = date.today()

    from datetime import date
    periodo = st.date_input(
        "Período",
        value=(d_min, d_max),
        min_value=d_min,
        max_value=d_max,
        key="hist_periodo",
    )
    if len(periodo) == 2:
        data_ini, data_fim = periodo
    else:
        data_ini, data_fim = d_min, d_max

    max_rows = st.slider("Máx. linhas", 100, 5000, 1000, step=100)

# ── Carrega dados da tabela selecionada ───────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _load_hist(tabela: str, d_ini: str, d_fim: str, limit: int) -> pd.DataFrame:
    return db_query(
        f'SELECT * FROM "{tabela}" WHERE DATA >= ? AND DATA <= ? AND "_inserido_em" IS NOT NULL LIMIT ?',
        params=(d_ini, d_fim, limit),
    )

with st.spinner("Consultando banco..."):
    df_hist = _load_hist(tabela_sel, data_ini.isoformat(), data_fim.isoformat(), max_rows)

if df_hist.empty:
    st.info("Nenhum registro encontrado para o período selecionado.")
else:
    col_qtd  = info.get("col_qtd", "QUANTIDADE")
    col_grup = info.get("col_grupo", "")

    n_rows = len(df_hist)
    total_qtd = df_hist[col_qtd].sum() if col_qtd in df_hist.columns else 0

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Registros encontrados", f"{n_rows:,.0f}".replace(",", "."))
    with c2:
        if col_qtd in df_hist.columns:
            st.metric(f"Total ({col_qtd})", f"{total_qtd:,.0f}".replace(",", "."))

    # Gráfico de evolução
    if "DATA" in df_hist.columns and col_qtd in df_hist.columns:
        df_plot = df_hist.copy()
        df_plot["DATA"] = pd.to_datetime(df_plot["DATA"], errors="coerce")
        df_plot[col_qtd] = pd.to_numeric(df_plot[col_qtd], errors="coerce").fillna(0)

        if col_grup and col_grup in df_plot.columns:
            agg = df_plot.groupby(["DATA", col_grup])[col_qtd].sum().reset_index()
            fig = px.bar(
                agg, x="DATA", y=col_qtd, color=col_grup,
                title=f"Evolução — {TABELAS_INFO.get(tabela_sel, {}).get('label', tabela_sel)}",
                barmode="stack",
            )
        else:
            agg = df_plot.groupby("DATA")[col_qtd].sum().reset_index()
            fig = px.bar(agg, x="DATA", y=col_qtd, title="Evolução diária")

        fig.update_layout(**DARK_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    # Tabela
    st.markdown("---")
    cols_hide = ["_inserido_em"]
    df_show = df_hist.drop(columns=[c for c in cols_hide if c in df_hist.columns])
    st.dataframe(df_show, use_container_width=True, hide_index=True)

    # Exportar
    csv_bytes = df_hist.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Exportar CSV",
        data=csv_bytes,
        file_name=f"historico_{tabela_sel}_{data_ini}_{data_fim}.csv",
        mime="text/csv",
        use_container_width=False,
    )
