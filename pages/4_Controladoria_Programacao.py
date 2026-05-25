# -*- coding: utf-8 -*-
"""
Controle de Programação de Corte
Cruza a programação semanal com os dados reais de corte (Arealva Manta + Iacanga).
"""

import io
import logging
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.auth import init_session_state
from utils.navigation import safe_switch

# ── Constantes ─────────────────────────────────────────────────────────────────
PROG_ID     = "1FeTwrPEBOcC6RmD_5zh8NQLwOrYO87XA"
PROG_GID    = "708887209"
MANTA_ID    = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
MANTA_GID   = "1544210185"
IACANGA_ID  = "14OFOAxrV_DkyrwG6KG8NZT-PeXUV4jezPrPO90rh1DU"
IACANGA_GID = "1362699684"
CACHE_TTL   = 300

_COR_STATUS = {"Concluído": "#22c55e", "Parcial": "#f59e0b", "Pendente": "#ef4444"}
_COR_PROD   = {"Liberado": "#22c55e", "Não Iniciado": "#6b7280"}
_EMOJI_STATUS = {"Concluído": "✅", "Parcial": "🟡", "Pendente": "🔴"}
_EMOJI_PROD   = {"Liberado": "🟢", "Não Iniciado": "⚫"}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Controle de Programação",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
footer{visibility:hidden;}#MainMenu{visibility:hidden;}
.stApp{
    background:
        radial-gradient(circle at 15% 15%,rgba(99,102,241,.07) 0%,transparent 42%),
        radial-gradient(circle at 85% 20%,rgba(79,70,229,.06) 0%,transparent 42%),
        linear-gradient(180deg,#0B0E14 0%,#0E1117 55%,#11151F 100%);
    color:#E0E0E0;font-family:'Space Grotesk',sans-serif;
}
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0C0F16 0%,#141925 100%)!important;
    border-right:1px solid rgba(255,255,255,.10);
}
section[data-testid="stSidebar"] *{color:#E0E0E0!important;font-family:'Space Grotesk',sans-serif;}
.page-badge{
    display:inline-block;padding:6px 18px;border-radius:999px;
    font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;
    color:#818CF8;background:rgba(129,140,248,.10);
    border:1px solid rgba(129,140,248,.30);font-weight:600;margin-bottom:20px;
}
.page-title{
    font-family:'Sora',sans-serif;font-size:2.4rem;font-weight:800;
    line-height:1.05;margin:0 0 14px 0;color:#FFF;letter-spacing:-.5px;
}
.page-title .accent{
    background:linear-gradient(90deg,#818CF8,#A5B4FC 45%,#6366F1 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.page-subtitle{font-size:1rem;color:#A0A0A0;max-width:580px;margin:0 auto 10px auto;}
.page-divider{
    height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.10),transparent);
    margin:28px 0 36px 0;
}
.breadcrumb{font-size:.85rem;color:#606878;margin-bottom:12px;padding:0 2px;}
.breadcrumb .bc-sep{margin:0 6px;color:rgba(255,255,255,.18);}
.breadcrumb .bc-active{color:#818CF8;font-weight:600;}
.breadcrumb .bc-link{color:#7A8899;}
.kpi-wrap{
    background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
    border-radius:14px;padding:18px 14px;text-align:center;
}
.kpi-label{font-size:.70rem;color:#9CA3AF;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;}
.kpi-value{font-family:'Sora',sans-serif;font-size:2rem;font-weight:800;color:#FFF;line-height:1;}
.kpi-sub{font-size:.75rem;color:#6B7280;margin-top:4px;}
.stButton>button{
    background:linear-gradient(135deg,#6366F1,#4F46E5)!important;
    color:#FFF!important;font-weight:700!important;border-radius:12px!important;
    padding:10px 14px!important;border:1px solid rgba(99,102,241,.55)!important;
    box-shadow:0 6px 18px rgba(99,102,241,.22)!important;
    transition:transform .2s ease!important;width:100%!important;
}
.stButton>button:hover{transform:translateY(-2px);}
section[data-testid="stSidebar"] .stButton>button{
    background:linear-gradient(135deg,rgba(99,102,241,.16),rgba(99,102,241,.07))!important;
    color:#818CF8!important;border:1px solid rgba(99,102,241,.35)!important;box-shadow:none!important;
}
section[data-testid="stSidebar"] .stButton>button p,
section[data-testid="stSidebar"] .stButton>button span{color:inherit!important;font-weight:600!important;}
div[data-testid="stMetric"]{
    background-color:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.15);
    border-radius:10px;padding:12px 16px;
}
</style>
""", unsafe_allow_html=True)

# ── Auth ───────────────────────────────────────────────────────────────────────
init_session_state()
if not st.session_state.get("auth_nivel"):
    st.warning("🔒 Acesso restrito. Faça login na página inicial.")
    if st.button("← Voltar ao Início"):
        safe_switch("app.py")
    st.stop()

# ── Sidebar nav ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Controle de Programação")
    st.markdown("---")
    if st.button("🏢 Início", key="sb_home", use_container_width=True):
        safe_switch("app.py")
    st.markdown("---")
    st.header("🔍 Filtros")


# ── Data loading ───────────────────────────────────────────────────────────────
def _fetch(sheet_id: str, gid: str) -> str | None:
    for url in [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}",
    ]:
        try:
            r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            r.encoding = "utf-8"
            if r.status_code == 200 and len(r.text) > 100:
                return r.text
        except Exception as e:
            logging.debug(f"fetch {url[:60]}: {e}")
    return None


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_programacao() -> pd.DataFrame:
    texto = _fetch(PROG_ID, PROG_GID)
    if not texto:
        raise ConnectionError("Não foi possível carregar a planilha de programação.")

    df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
    df.columns = df.columns.str.strip()

    # Garantir colunas essenciais
    for col in ["PED. CLIENTE", "SEMANA", "CLIENTE", "LOCAL", "PRODUTO",
                "PED. INT", "OP INTERNA", "OC", "DESCRIÇÃO DO PRODUTO",
                "REPRO./INCLUIDO(S/N)", "MOTIVO REPRO./INCLUSÃO",
                "DATA INICIO", "DATA FINALIZADO", "PREV. INDUSTRIALIZAÇÃO"]:
        if col not in df.columns:
            df[col] = ""

    df["PED. CLIENTE"] = df["PED. CLIENTE"].astype(str).str.strip()
    df["QNT. PROG"]    = pd.to_numeric(df.get("QNT. PROG", pd.Series(dtype=str)), errors="coerce").fillna(0).astype(int)
    df["SEMANA"]       = df["SEMANA"].astype(str).str.strip()
    df["CLIENTE"]      = df["CLIENTE"].astype(str).str.strip()
    df["LOCAL"]        = df["LOCAL"].astype(str).str.strip()

    invalidos = {"", "NAN", "NONE", "N/A"}
    df = df[~df["PED. CLIENTE"].str.upper().isin(invalidos)].reset_index(drop=True)
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_cortes() -> pd.DataFrame:
    frames = []
    for sid, gid, fonte in [
        (MANTA_ID, MANTA_GID, "Arealva"),
        (IACANGA_ID, IACANGA_GID, "Iacanga"),
    ]:
        texto = _fetch(sid, gid)
        if not texto:
            continue
        try:
            df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
            df.columns = df.columns.str.strip()
            if "OP" in df.columns and "QUANTIDADE" in df.columns:
                sub = df[["OP", "QUANTIDADE"]].copy()
                sub["FONTE"] = fonte
                frames.append(sub)
        except Exception as e:
            logging.debug(f"parse {fonte}: {e}")

    if not frames:
        return pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE"])

    out = pd.concat(frames, ignore_index=True)
    out["OP"]         = out["OP"].astype(str).str.strip()
    out["QUANTIDADE"] = pd.to_numeric(out["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    return out


# ── Lógica de cruzamento ───────────────────────────────────────────────────────
def _status_corte(cortada: int, prog_total: int) -> str:
    if cortada <= 0:
        return "Pendente"
    if cortada >= prog_total:
        return "Concluído"
    return "Parcial"


def enriquecer(df_prog: pd.DataFrame, df_cortes: pd.DataFrame) -> pd.DataFrame:
    cortes_por_op = df_cortes.groupby("OP")["QUANTIDADE"].sum().to_dict()
    total_prog_op = df_prog.groupby("PED. CLIENTE")["QNT. PROG"].transform("sum")

    df = df_prog.copy()
    df["QNT_PROG_TOTAL"] = total_prog_op.astype(int)
    df["QNT_CORTADA"]    = df["PED. CLIENTE"].map(cortes_por_op).fillna(0).astype(int)
    df["STATUS_PROD"]    = df["QNT_CORTADA"].apply(
        lambda x: "Liberado" if x > 0 else "Não Iniciado"
    )
    df["STATUS_CORTE"]   = df.apply(
        lambda r: _status_corte(r["QNT_CORTADA"], r["QNT_PROG_TOTAL"]), axis=1
    )
    df["DIFERENÇA"]      = df["QNT_CORTADA"] - df["QNT_PROG_TOTAL"]
    df["EFICIÊNCIA_%"]   = (
        df["QNT_CORTADA"] / df["QNT_PROG_TOTAL"].replace(0, pd.NA) * 100
    ).fillna(0).round(1)
    return df


def agregar_por_op(df: pd.DataFrame) -> pd.DataFrame:
    def join_unique(s):
        vals = sorted({str(v) for v in s if str(v) not in ("", "nan", "NAN", "None")})
        return " / ".join(vals)

    return df.groupby("PED. CLIENTE", as_index=False).agg(
        SEMANA        =("SEMANA",          "first"),
        CLIENTE       =("CLIENTE",         "first"),
        LOCAL         =("LOCAL",           "first"),
        PRODUTO       =("PRODUTO",         join_unique),
        QNT_PROG_TOTAL=("QNT_PROG_TOTAL",  "first"),
        QNT_CORTADA   =("QNT_CORTADA",     "first"),
        STATUS_PROD   =("STATUS_PROD",     "first"),
        STATUS_CORTE  =("STATUS_CORTE",    "first"),
        DIFERENÇA     =("DIFERENÇA",       "first"),
        EFICIÊNCIA_PRC=("EFICIÊNCIA_%",    "first"),
    )


# ── Carregamento com spinner ───────────────────────────────────────────────────
with st.spinner("Carregando dados..."):
    try:
        df_prog_raw = load_programacao()
    except Exception as e:
        st.error(f"❌ Erro ao carregar programação: {e}")
        st.stop()

    try:
        df_cortes_raw = load_cortes()
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar dados de corte: {e}")
        df_cortes_raw = pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE"])

df_enriched = enriquecer(df_prog_raw, df_cortes_raw)


# ── Sidebar — filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    semanas_disp = sorted(df_enriched["SEMANA"].dropna().unique())
    semanas_sel  = st.multiselect("📅 Semana", options=semanas_disp, default=[], key="prog_semana")

    clientes_disp = sorted(df_enriched["CLIENTE"].dropna().unique())
    clientes_sel  = st.multiselect("👤 Cliente", options=clientes_disp, default=[], key="prog_cliente")

    locais_disp = sorted(df_enriched["LOCAL"].dropna().unique())
    locais_sel  = st.multiselect("🏭 Local", options=locais_disp, default=[], key="prog_local")

    status_disp = ["Pendente", "Parcial", "Concluído"]
    status_sel  = st.multiselect("🔄 Status de Corte", options=status_disp, default=[], key="prog_status")

    st.markdown("---")
    if st.button("🔄 Limpar Cache", key="prog_clear", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"Registros: {len(df_enriched):,}")


# ── Aplicar filtros ────────────────────────────────────────────────────────────
df_filtered = df_enriched.copy()
if semanas_sel:
    df_filtered = df_filtered[df_filtered["SEMANA"].isin(semanas_sel)]
if clientes_sel:
    df_filtered = df_filtered[df_filtered["CLIENTE"].isin(clientes_sel)]
if locais_sel:
    df_filtered = df_filtered[df_filtered["LOCAL"].isin(locais_sel)]
if status_sel:
    df_filtered = df_filtered[df_filtered["STATUS_CORTE"].isin(status_sel)]


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="breadcrumb">
  <span class="bc-link">Controladoria</span>
  <span class="bc-sep">›</span>
  <span class="bc-active">Controle de Programação</span>
</div>
<div style="text-align:center;padding:24px 12px 8px 12px;">
  <div class="page-badge">📊 Controladoria · Planejado vs Realizado</div>
  <h1 class="page-title">Programação de <span class="accent">Corte</span></h1>
  <p class="page-subtitle">Acompanhamento semanal cruzando o programado com o realizado nos dashboards de corte</p>
</div>
<div class="page-divider"></div>
""", unsafe_allow_html=True)


# ── KPIs ───────────────────────────────────────────────────────────────────────
df_agg = agregar_por_op(df_filtered)

total_ops      = len(df_agg)
concluidas     = (df_agg["STATUS_CORTE"] == "Concluído").sum()
parciais       = (df_agg["STATUS_CORTE"] == "Parcial").sum()
pendentes      = (df_agg["STATUS_CORTE"] == "Pendente").sum()
aderencia_pct  = round(concluidas / total_ops * 100, 1) if total_ops else 0
total_prog_pcs = int(df_agg["QNT_PROG_TOTAL"].sum())
total_cort_pcs = int(df_agg["QNT_CORTADA"].sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)

def _kpi(col, label, value, sub="", color="#FFFFFF"):
    with col:
        st.markdown(
            f'<div class="kpi-wrap">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

_kpi(k1, "Total de OPs",     total_ops,      "ordens na programação")
_kpi(k2, "Concluídas",       concluidas,     f"{aderencia_pct}% aderência",  "#22c55e")
_kpi(k3, "Parciais",         parciais,       "em andamento",                 "#f59e0b")
_kpi(k4, "Pendentes",        pendentes,      "não iniciadas",                "#ef4444")
_kpi(k5, "Peças Prog.",      f"{total_prog_pcs:,}".replace(",", "."), "total programado")
_kpi(k6, "Peças Cortadas",   f"{total_cort_pcs:,}".replace(",", "."), "total realizado",
     "#22c55e" if total_cort_pcs >= total_prog_pcs else "#f59e0b")

st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)


# ── Gráficos ───────────────────────────────────────────────────────────────────
_DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
)

col_donut, col_bar = st.columns([1, 2], gap="large")

with col_donut:
    st.markdown("#### Status das Ordens")
    labels = ["Concluído", "Parcial", "Pendente"]
    values = [concluidas, parciais, pendentes]
    colors = ["#22c55e", "#f59e0b", "#ef4444"]
    fig_donut = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.60,
        marker=dict(colors=colors, line=dict(color="#0B0E14", width=2)),
        textinfo="percent+value",
        textfont=dict(size=13),
        showlegend=True,
    ))
    fig_donut.update_layout(
        **_DARK,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        annotations=[dict(
            text=f"<b>{total_ops}</b><br>OPs",
            x=0.5, y=0.5, font_size=16, showarrow=False, font_color="#FFFFFF",
        )],
        height=300,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_bar:
    st.markdown("#### Programado vs Cortado por Semana")
    if not df_agg.empty:
        df_sem = df_agg.groupby("SEMANA", as_index=False).agg(
            QNT_PROG_TOTAL=("QNT_PROG_TOTAL", "sum"),
            QNT_CORTADA   =("QNT_CORTADA",    "sum"),
        ).sort_values("SEMANA")

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Programado", x=df_sem["SEMANA"], y=df_sem["QNT_PROG_TOTAL"],
            marker_color="rgba(129,140,248,0.55)", marker_line_color="#818CF8", marker_line_width=1,
        ))
        fig_bar.add_trace(go.Bar(
            name="Cortado", x=df_sem["SEMANA"], y=df_sem["QNT_CORTADA"],
            marker_color="rgba(34,197,94,0.65)", marker_line_color="#22c55e", marker_line_width=1,
        ))
        fig_bar.update_layout(
            **_DARK,
            barmode="group",
            xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0"),
            yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0",
                       title="Peças"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=300,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para o período selecionado.")

st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)


# ── Tabelas ────────────────────────────────────────────────────────────────────
tab_resumo, tab_detalhe = st.tabs(["📊 Resumo por Ordem (OP)", "📋 Detalhe Completo"])

# ── Tab 1: Resumo por OP ──────────────────────────────────────────────────────
with tab_resumo:
    if df_agg.empty:
        st.info("Nenhuma ordem encontrada com os filtros aplicados.")
    else:
        df_show = df_agg.copy()
        df_show["STATUS PRODUÇÃO"] = df_show["STATUS_PROD"].apply(
            lambda s: f"{_EMOJI_PROD.get(s, '')} {s}"
        )
        df_show["STATUS CORTE"] = df_show["STATUS_CORTE"].apply(
            lambda s: f"{_EMOJI_STATUS.get(s, '')} {s}"
        )
        df_show["EFICIÊNCIA"] = df_show["EFICIÊNCIA_PRC"].apply(lambda x: f"{x:.1f}%")
        df_show["DIFERENÇA"]  = df_show["DIFERENÇA"].apply(
            lambda x: f"+{int(x):,}".replace(",", ".") if x >= 0 else f"{int(x):,}".replace(",", ".")
        )
        df_show["QNT PROG"]    = df_show["QNT_PROG_TOTAL"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_show["QNT CORTADA"] = df_show["QNT_CORTADA"].apply(lambda x: f"{int(x):,}".replace(",", "."))

        colunas_exibir = [
            "SEMANA", "PED. CLIENTE", "CLIENTE", "LOCAL", "PRODUTO",
            "QNT PROG", "QNT CORTADA", "DIFERENÇA", "EFICIÊNCIA",
            "STATUS PRODUÇÃO", "STATUS CORTE",
        ]
        st.dataframe(
            df_show[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            height=min(50 + len(df_show) * 35, 600),
        )
        st.caption(f"Total: {len(df_show)} ordens | {total_prog_pcs:,} peças programadas | {total_cort_pcs:,} cortadas".replace(",", "."))


# ── Tab 2: Detalhe Completo ───────────────────────────────────────────────────
with tab_detalhe:
    if df_filtered.empty:
        st.info("Nenhum registro encontrado com os filtros aplicados.")
    else:
        df_det = df_filtered.copy()

        # Colunas originais da planilha + calculadas (substituindo as manuais)
        df_det["STATUS PRODUÇÃO"] = df_det["STATUS_PROD"].apply(
            lambda s: f"{_EMOJI_PROD.get(s, '')} {s}"
        )
        df_det["STATUS CORTE"] = df_det["STATUS_CORTE"].apply(
            lambda s: f"{_EMOJI_STATUS.get(s, '')} {s}"
        )
        df_det["QNT CORTADA"]  = df_det["QNT_CORTADA"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_det["EFICIÊNCIA %"] = df_det["EFICIÊNCIA_%"].apply(lambda x: f"{x:.1f}%")
        df_det["DIFERENÇA"]    = df_det["DIFERENÇA"].apply(
            lambda x: f"+{int(x):,}".replace(",", ".") if x >= 0 else f"{int(x):,}".replace(",", ".")
        )

        colunas_det = [
            "SEMANA", "CLIENTE", "LOCAL", "PRODUTO", "PED. CLIENTE",
            "PED. INT", "OP INTERNA", "OC", "DESCRIÇÃO DO PRODUTO",
            "QNT. PROG", "REPRO./INCLUIDO(S/N)", "MOTIVO REPRO./INCLUSÃO",
            "DATA INICIO", "DATA FINALIZADO", "PREV. INDUSTRIALIZAÇÃO",
            "QNT CORTADA", "STATUS PRODUÇÃO", "STATUS CORTE", "EFICIÊNCIA %", "DIFERENÇA",
        ]
        colunas_det = [c for c in colunas_det if c in df_det.columns]

        st.dataframe(
            df_det[colunas_det],
            use_container_width=True,
            hide_index=True,
            height=min(50 + len(df_det) * 35, 700),
        )
        st.caption(f"Total: {len(df_det)} linhas")
