"""
Controle de OP — Histórico de Conclusão, Status e % de Conclusão
Cobre o ciclo Programação → Corte (utils/controle_op.py). Produção nas
facções (costura/acabamento) ainda não tem OP vinculada nos dados de
origem — ver aviso na tela.
"""

import os
import sys
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.auth import init_session_state
from styles.global_ui import get_global_ui_css
from utils.navigation import safe_switch
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button
from utils.controle_op import load_programacao, load_cortes, historico_op
from utils.pdf_report import gerar_pdf_fechamento_op, nome_arquivo_pdf

_COR_STATUS = {
    "Concluído": "#22c55e", "Parcial": "#f59e0b", "Pendente": "#ef4444",
    "Fora da Programação": "#a78bfa",
}
_EMOJI_STATUS = {
    "Concluído": "✅", "Parcial": "🟡", "Pendente": "🔴", "Fora da Programação": "🟣",
}


def _cor_status_cell(val: str) -> str:
    cor = _COR_STATUS.get(val, "#9CA3AF")
    return f"background-color:{cor}26;color:{cor};font-weight:700;border-radius:6px;"


def _fmt_status(val: str) -> str:
    return f"{_EMOJI_STATUS.get(val, '')} {val}".strip()

# page config
st.set_page_config(
    page_title="Controle de OP",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

# css — mesmo visual de pages/4_Controladoria_Programacao.py, pra manter
# a identidade das telas de Controladoria consistente.
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
.page-subtitle{font-size:1rem;color:#A0A0A0;max-width:580px;margin:0 auto 10px auto;text-align:center;}
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

# auth
init_session_state()
render_home_button()
if not st.session_state.get("auth_nivel"):
    st.warning("🔒 Acesso restrito. Faça login na página inicial.")
    st.stop()

with st.sidebar:
    st.markdown("### 🗂️ Controle de OP")
    st.markdown("---")
    if st.button("🏢 Início", key="sb_home_op", use_container_width=True):
        safe_switch("app.py")
    st.markdown("---")
    st.header("🔍 Filtros")

# carregamento
_erro = None
with st.spinner("Carregando dados de programação e corte..."):
    try:
        df_prog_raw = load_programacao()
        df_cortes_raw = load_cortes()
    except Exception as e:
        _erro = str(e)
        df_prog_raw = pd.DataFrame()
        df_cortes_raw = pd.DataFrame()

if _erro:
    st.error(f"❌ Erro ao carregar dados: {_erro}")
    st.stop()

if df_prog_raw.empty:
    st.error("❌ A planilha de programação foi carregada mas não retornou dados válidos.")
    st.stop()

df_hist = historico_op(df_prog_raw, df_cortes_raw)

# sidebar — filtros de Cliente e Status filtram o conjunto de OPs inteiro
# (todas, independente de já terem sido concluídas ou não). O filtro de
# Período (abaixo) só recorta a tabela/gráfico de histórico de conclusão —
# OPs pendentes/parciais não têm DATA_CONCLUSAO e continuam contando nos
# KPIs de qualquer forma.
with st.sidebar:
    clientes_disp = sorted(df_hist["CLIENTE"].dropna().unique())
    clientes_sel  = st.multiselect("👤 Cliente", options=clientes_disp, default=[], key="op_cliente")

    status_disp = ["Pendente", "Parcial", "Concluído", "Fora da Programação"]
    status_sel  = st.multiselect("🔄 Status", options=status_disp, default=[], key="op_status")

    datas_concl = df_hist["DATA_CONCLUSAO"].dropna()
    if not datas_concl.empty:
        _dmin, _dmax = min(datas_concl), max(datas_concl)
    else:
        _dmin = _dmax = date.today()
    st.markdown("**📅 Período de conclusão**")
    st.caption("Filtra só a tabela/gráfico de histórico — não os KPIs de status.")
    periodo_ini = st.date_input("De", value=_dmin, key="op_periodo_ini", format="DD/MM/YYYY")
    periodo_fim = st.date_input("Até", value=_dmax, key="op_periodo_fim", format="DD/MM/YYYY")

    st.markdown("---")
    if st.button("🔄 Atualizar Dados", key="op_clear", use_container_width=True):
        from utils.cache_manager import invalidate_all
        invalidate_all()
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# aplica filtros de Cliente/Status (sobre o conjunto inteiro de OPs)
df_filtrado = df_hist.copy()
if clientes_sel:
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"].isin(clientes_sel)]
if status_sel:
    df_filtrado = df_filtrado[df_filtrado["STATUS_CORTE"].isin(status_sel)]

render_filtros_btn()

# header
st.markdown("""
<div class="breadcrumb">
  <span class="bc-link">Controladoria</span>
  <span class="bc-sep">›</span>
  <span class="bc-active">Controle de OP</span>
</div>
<div style="text-align:center;padding:24px 12px 8px 12px;">
  <div class="page-badge">🗂️ Controladoria · Histórico e Fechamento de OP</div>
  <h1 class="page-title">Controle de <span class="accent">OP</span></h1>
  <p class="page-subtitle">Status, % de conclusão e histórico de fechamento — Programação × Corte</p>
</div>
<div class="page-divider"></div>
""", unsafe_allow_html=True)

# kpis
total_ops     = len(df_filtrado)
concluidas    = int((df_filtrado["STATUS_CORTE"] == "Concluído").sum())
parciais      = int((df_filtrado["STATUS_CORTE"] == "Parcial").sum())
pendentes     = int((df_filtrado["STATUS_CORTE"] == "Pendente").sum())
fora_prog     = int((df_filtrado["STATUS_CORTE"] == "Fora da Programação").sum())
aderencia_pct = round(concluidas / total_ops * 100, 1) if total_ops else 0.0

k1, k2, k3, k4, k5 = st.columns(5)

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

_kpi(k1, "Total de OPs", total_ops, "no filtro atual")
_kpi(k2, "✅ Concluídas", concluidas, f"{aderencia_pct}% aderência", "#22c55e")
_kpi(k3, "🟡 Parciais", parciais, "em andamento", "#f59e0b")
_kpi(k4, "🔴 Pendentes", pendentes, "não iniciadas", "#ef4444")
_kpi(k5, "🟣 Fora da Programação", fora_prog, "cortadas sem programação", "#a78bfa")

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── Visão geral: distribuição por status + aderência ─────────────────────────
# Pedido do usuário 10/07/2026: dashboard "simples demais" — status e
# análises viram gráficos em vez de só números crus.
col_donut, col_gauge = st.columns([3, 2])

with col_donut:
    _status_labels = ["Concluído", "Parcial", "Pendente", "Fora da Programação"]
    _status_valores = [concluidas, parciais, pendentes, fora_prog]
    fig_status = go.Figure(go.Pie(
        labels=_status_labels, values=_status_valores, hole=0.58,
        marker=dict(colors=[_COR_STATUS[s] for s in _status_labels]),
        textinfo="label+value", textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>%{value} OPs (%{percent})<extra></extra>",
    ))
    fig_status.update_layout(
        title="Distribuição por Status", template="plotly_dark",
        separators=",.", height=340, showlegend=False,
        margin=dict(t=50, b=20, l=10, r=10),
        annotations=[dict(text=f"{total_ops}<br>OPs", x=.5, y=.5, font=dict(size=18, color="#FFF"),
                          showarrow=False)],
    )
    st.plotly_chart(fig_status, use_container_width=True)

with col_gauge:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=aderencia_pct,
        number={"suffix": "%", "font": {"size": 40}},
        title={"text": "Aderência Geral", "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#9CA3AF"},
            "bar": {"color": "#6366F1"},
            "bgcolor": "rgba(255,255,255,.04)",
            "steps": [
                {"range": [0, 50], "color": "rgba(239,68,68,.25)"},
                {"range": [50, 80], "color": "rgba(245,158,11,.25)"},
                {"range": [80, 100], "color": "rgba(34,197,94,.25)"},
            ],
        },
    ))
    fig_gauge.update_layout(template="plotly_dark", height=340, margin=dict(t=60, b=20, l=30, r=30))
    st.plotly_chart(fig_gauge, use_container_width=True)

# ── Top clientes por volume cortado ───────────────────────────────────────────
_top_clientes = (
    df_filtrado[df_filtrado["CLIENTE"].astype(str).str.strip().ne("")]
    .groupby("CLIENTE", as_index=False)
    .agg(PECAS=("QNT_CORTADA", "sum"), OPS=("PED. CLIENTE", "count"))
    .sort_values("PECAS", ascending=False)
    .head(10)
)
if not _top_clientes.empty:
    fig_top = go.Figure(go.Bar(
        x=_top_clientes["PECAS"], y=_top_clientes["CLIENTE"], orientation="h",
        marker_color="#6366F1",
        text=[f"{p:,.0f} pçs · {o} OPs".replace(",", ".") for p, o in zip(_top_clientes["PECAS"], _top_clientes["OPS"])],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} peças<extra></extra>",
    ))
    fig_top.update_layout(
        title="Top 10 Clientes por Peças Cortadas", template="plotly_dark",
        separators=",.", height=380, margin=dict(t=50, b=20, l=10, r=80),
        yaxis=dict(autorange="reversed"), xaxis_title="Peças Cortadas",
    )
    st.plotly_chart(fig_top, use_container_width=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# histórico de conclusão — só OPs Concluído com DATA_CONCLUSAO no período
df_concluidas_periodo = df_filtrado[
    (df_filtrado["STATUS_CORTE"] == "Concluído") &
    df_filtrado["DATA_CONCLUSAO"].notna() &
    (df_filtrado["DATA_CONCLUSAO"] >= periodo_ini) &
    (df_filtrado["DATA_CONCLUSAO"] <= periodo_fim)
].sort_values("DATA_CONCLUSAO")

st.markdown("### 📈 Histórico de Conclusão de OPs")

if df_concluidas_periodo.empty:
    st.warning("Nenhuma OP concluída com data calculada no período selecionado.")
else:
    _por_semana = (
        df_concluidas_periodo
        .assign(SEMANA_CONCLUSAO=lambda d: pd.to_datetime(d["DATA_CONCLUSAO"]).dt.to_period("W").astype(str))
        .groupby("SEMANA_CONCLUSAO", as_index=False)
        .size()
        .rename(columns={"size": "OPS_CONCLUIDAS"})
        .sort_values("SEMANA_CONCLUSAO")
    )
    fig_hist = go.Figure(go.Bar(
        x=_por_semana["SEMANA_CONCLUSAO"], y=_por_semana["OPS_CONCLUIDAS"],
        marker_color="#22c55e",
        text=_por_semana["OPS_CONCLUIDAS"], textposition="outside",
    ))
    fig_hist.update_layout(
        title="OPs Concluídas por Semana", template="plotly_dark",
        separators=",.", margin=dict(t=50, b=40), height=340,
        xaxis_title="Semana", yaxis_title="OPs concluídas",
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("#### Detalhamento")
    _tab = df_concluidas_periodo[[
        "PED. CLIENTE", "CLIENTE", "PRODUTO", "QNT_PROG_TOTAL", "QNT_CORTADA",
        "EFICIÊNCIA_PRC", "STATUS_CORTE", "DATA_CONCLUSAO",
    ]].rename(columns={
        "PED. CLIENTE": "OP", "QNT_PROG_TOTAL": "Programado", "QNT_CORTADA": "Cortado",
        "EFICIÊNCIA_PRC": "% Conclusão", "STATUS_CORTE": "Status", "DATA_CONCLUSAO": "Data Conclusão",
    })
    st.dataframe(
        _tab.style.map(_cor_status_cell, subset=["Status"]).format({
            "Programado": "{:,.0f}", "Cortado": "{:,.0f}", "% Conclusão": "{:.1f}%",
            "Data Conclusão": lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "—",
            "Status": _fmt_status,
        }),
        use_container_width=True, hide_index=True, height=420,
    )

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# tabela geral (todas as OPs do filtro de Cliente/Status, qualquer status —
# inclui "Fora da Programação", que pode não ter % Conclusão/Programado
# quando não achou referência na Carteira de Pedidos).
st.markdown("### 📋 Todas as OPs no Filtro")
_tab_geral = df_filtrado[[
    "PED. CLIENTE", "CLIENTE", "PRODUTO", "QNT_PROG_TOTAL", "QNT_CORTADA",
    "EFICIÊNCIA_PRC", "STATUS_CORTE", "DATA_CONCLUSAO",
]].rename(columns={
    "PED. CLIENTE": "OP", "QNT_PROG_TOTAL": "Programado", "QNT_CORTADA": "Cortado",
    "EFICIÊNCIA_PRC": "% Conclusão", "STATUS_CORTE": "Status", "DATA_CONCLUSAO": "Data Conclusão",
})
_tab_geral["% Conclusão"] = pd.to_numeric(_tab_geral["% Conclusão"], errors="coerce")
_tab_geral = _tab_geral.sort_values("% Conclusão", ascending=False, na_position="last")
st.dataframe(
    _tab_geral.style.map(_cor_status_cell, subset=["Status"]).format({
        "Programado": "{:,.0f}", "Cortado": "{:,.0f}",
        "% Conclusão": lambda v: f"{v:.1f}%" if pd.notna(v) else "—",
        "Data Conclusão": lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "—",
        "Status": _fmt_status,
    }),
    use_container_width=True, hide_index=True, height=420,
)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Relatório de Fechamento (PDF) ────────────────────────────────────────────
st.markdown("### 📄 Relatório de Fechamento")
with st.container(border=True):
    if st.button("📄 Gerar Relatório de Fechamento", key="btn_fechamento_op", type="primary"):
        with st.spinner("Gerando PDF…"):
            try:
                _bytes_op = gerar_pdf_fechamento_op(
                    df_agg=df_concluidas_periodo if not df_concluidas_periodo.empty else df_filtrado,
                    periodo_ini=periodo_ini,
                    periodo_fim=periodo_fim,
                    total_ops=total_ops,
                    concluidas=concluidas,
                    parciais=parciais,
                    pendentes=pendentes,
                    aderencia_pct=aderencia_pct,
                    fora_programacao=fora_prog,
                    filtros_texto="",
                )
                st.session_state["pdf_op_bytes"] = _bytes_op
                st.session_state["pdf_op_nome"] = nome_arquivo_pdf("fechamento_op", periodo_ini, periodo_fim)
                st.success("PDF gerado!")
            except Exception as _e:
                st.error(f"Erro ao gerar PDF: {_e}")

    if st.session_state.get("pdf_op_bytes"):
        st.download_button(
            "⬇️ Baixar Relatório de Fechamento", data=st.session_state["pdf_op_bytes"],
            file_name=st.session_state.get("pdf_op_nome", "fechamento_op.pdf"),
            mime="application/pdf", key="dl_op",
        )
