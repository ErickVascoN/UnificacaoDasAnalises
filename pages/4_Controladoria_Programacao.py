"""
Controle de Programação de Corte
Cruza a programação semanal com os dados reais de corte (Arealva Manta + Iacanga).
"""

import os
import re
import sys
from datetime import datetime

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
from utils.controle_op import (
    load_programacao, load_cortes, enriquecer, agregar_por_op,
)

_COR_STATUS = {"Concluído": "#22c55e", "Parcial": "#f59e0b", "Pendente": "#ef4444"}
_COR_PROD   = {"Liberado": "#22c55e", "Não Iniciado": "#6b7280"}
_EMOJI_STATUS = {"Concluído": "✅", "Parcial": "🟡", "Pendente": "🔴"}
_EMOJI_PROD   = {"Liberado": "🟢", "Não Iniciado": "⚫"}

# page config
st.set_page_config(
    page_title="Controle de Programação",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

# css
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
render_home_button()  # sempre visível, mesmo sem login
if not st.session_state.get("auth_nivel"):
    st.warning("🔒 Acesso restrito. Faça login na página inicial.")
    st.stop()

with st.sidebar:
    st.markdown("### 📊 Controle de Programação")
    st.markdown("---")
    if st.button("🏢 Início", key="sb_home", use_container_width=True):
        safe_switch("app.py")
    st.markdown("---")
    st.header("🔍 Filtros")

# carregamento
_erro_prog   = None
_erro_cortes = None

with st.spinner("Carregando dados da programação..."):
    try:
        df_prog_raw = load_programacao()
    except Exception as e:
        _erro_prog = str(e)
        df_prog_raw = pd.DataFrame()

with st.spinner("Carregando dados de corte..."):
    try:
        df_cortes_raw = load_cortes()
    except Exception as e:
        _erro_cortes = str(e)
        df_cortes_raw = pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE"])

if _erro_prog:
    st.error(f"❌ Erro ao carregar programação: {_erro_prog}")
    st.info("Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link pode visualizar'.")
    st.stop()

if df_prog_raw.empty:
    st.error("❌ A planilha de programação foi carregada mas não retornou dados válidos.")
    st.info("Verifique se a planilha contém dados e se a coluna 'PED. CLIENTE' existe.")
    st.stop()

df_enriched = enriquecer(df_prog_raw, df_cortes_raw)

# sidebar — filtros
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
    if st.button("🔄 Atualizar Dados", key="prog_clear", use_container_width=True):
        from utils.cache_manager import invalidate_all
        invalidate_all()
        st.cache_data.clear()
        st.rerun()
    st.caption("🔖 cód. v20260611-6")
    st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"📋 Prog.: {len(df_prog_raw):,} linhas".replace(",", "."))
    total_cortes = len(df_cortes_raw)
    st.caption(f"✂️ Cortes total: {total_cortes:,} registros".replace(",", "."))
    if not df_cortes_raw.empty and "FONTE" in df_cortes_raw.columns:
        for fonte_nome, grupo in df_cortes_raw.groupby("FONTE"):
            st.caption(f"  · {fonte_nome}: {len(grupo):,}".replace(",", "."))
    if total_cortes == 0:
        st.warning("⚠️ Nenhum dado de corte carregado — verifique acesso às planilhas.")
    if _erro_cortes:
        st.warning(f"⚠️ Cortes: {_erro_cortes[:60]}")

    st.markdown("---")
    st.markdown("**🔍 Rastrear OP**")
    op_busca = st.text_input("OP / PED. CLIENTE", key="op_rastreio", placeholder="ex: 254333")
    if op_busca.strip():
        from utils.normalize import normalize_op as _nop
        _alvo = _nop(op_busca)
        resultado = df_cortes_raw[df_cortes_raw["OP"].map(_nop) == _alvo]
        if resultado.empty:
            st.info("Nenhum corte encontrado para essa OP.")
        else:
            st.success(f"**{resultado['QUANTIDADE'].apply(pd.to_numeric, errors='coerce').fillna(0).sum():,.0f}** peças cortadas".replace(",", "."))
            _cols_rastreio = [c for c in ["FONTE", "OP", "MATERIAL", "CLIENTE", "QUANTIDADE"] if c in resultado.columns]
            st.dataframe(resultado[_cols_rastreio], use_container_width=True, hide_index=True)

# aplicar filtros
df_filtered = df_enriched.copy()
if semanas_sel:
    df_filtered = df_filtered[df_filtered["SEMANA"].isin(semanas_sel)]
if clientes_sel:
    df_filtered = df_filtered[df_filtered["CLIENTE"].isin(clientes_sel)]
if locais_sel:
    df_filtered = df_filtered[df_filtered["LOCAL"].isin(locais_sel)]
if status_sel:
    df_filtered = df_filtered[df_filtered["STATUS_CORTE"].isin(status_sel)]

render_filtros_btn()

# header
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

# kpis
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

# diagnóstico de fontes
with st.expander("🔍 Diagnóstico — Verificação de Fontes de Corte", expanded=False):
    st.markdown("##### Status de carregamento por planilha")

    _FONTES_ESPERADAS = ["Zanattex", "Giattex", "Lençol"]
    diag_rows = []

    for fn in _FONTES_ESPERADAS:
        if not df_cortes_raw.empty and "FONTE" in df_cortes_raw.columns:
            g = df_cortes_raw[df_cortes_raw["FONTE"] == fn]
            n_reg = len(g)
        else:
            g = pd.DataFrame()
            n_reg = 0

        if n_reg > 0:
            n_ops   = int(g["OP"].nunique())
            qtd     = int(g["QUANTIDADE"].sum())
            status  = "✅ Carregado"
            top_ops = (
                g.groupby("OP")["QUANTIDADE"].sum()
                .nlargest(5)
                .index.tolist()
            )
            amostra = " · ".join(str(o) for o in top_ops)
            # Faixa de semanas carregadas
            if "SEMANA" in g.columns and g["SEMANA"].notna().any():
                sem_min = int(g["SEMANA"].dropna().min())
                sem_max = int(g["SEMANA"].dropna().max())
                semanas_str = f"sem. {sem_min}–{sem_max}"
            else:
                semanas_str = "sem data"
        else:
            n_ops, qtd, status, amostra, semanas_str = 0, 0, "❌ Sem dados", "—", "—"

        diag_rows.append({
            "Fonte": fn,
            "Status": status,
            "Registros": f"{n_reg:,}".replace(",", "."),
            "OPs únicas": f"{n_ops:,}".replace(",", "."),
            "Peças totais": f"{qtd:,}".replace(",", "."),
            "Semanas cobertas": semanas_str,
            "Top OPs (por qtd.)": amostra,
        })

    st.dataframe(pd.DataFrame(diag_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### Cruzamento: Programação × Cortes")

    from utils.normalize import normalize_op as _nop
    _ops_corte = (
        {o for o in df_cortes_raw["OP"].map(_nop).unique() if o}
        if not df_cortes_raw.empty else set()
    )
    # OP da programação = PED. CLIENTE (normalizada, prefixo-insensível)
    _peds_prog = {o for o in df_prog_raw["PED. CLIENTE"].map(_nop).unique() if o}

    _matched_ped = _peds_prog & _ops_corte
    _nao_matched = _peds_prog - _ops_corte

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("OPs na programação", len(_peds_prog))
    mc2.metric("Com corte encontrado", len(_matched_ped),
               help="OP (PED. CLIENTE) encontrada nos dados de corte, ignorando prefixo")
    mc3.metric("Sem corte encontrado", len(_nao_matched),
               help="Nenhum corte com essa OP nas planilhas de corte")

    if _nao_matched:
        st.markdown(
            f"**⚠️ {len(_nao_matched)} pedido(s) da programação sem corte registrado "
            f"em nenhuma das planilhas:**"
        )
        # Exibe em grid de 5 colunas
        _nm_sorted = sorted(_nao_matched)
        _cols_nm = st.columns(5)
        for i, nm in enumerate(_nm_sorted[:50]):   # limita a 50 para não poluir
            _cols_nm[i % 5].markdown(f"`{nm}`")
        if len(_nao_matched) > 50:
            st.caption(f"… e mais {len(_nao_matched) - 50} pedidos.")
    else:
        st.success("✅ Todos os pedidos da programação têm corte registrado em alguma fonte.")

    # Verificação inversa: OPs cortadas sem pedido na programação
    _corte_sem_prog = _ops_corte - _peds_prog
    if _corte_sem_prog:
        with st.container():
            st.markdown(
                f"**ℹ️ {len(_corte_sem_prog)} OP(s) cortada(s) sem pedido correspondente "
                f"na programação:**"
            )
            _cs_sorted = sorted(_corte_sem_prog)
            _cols_cs = st.columns(5)
            for i, op in enumerate(_cs_sorted[:30]):
                _cols_cs[i % 5].markdown(f"`{op}`")
            if len(_corte_sem_prog) > 30:
                st.caption(f"… e mais {len(_corte_sem_prog) - 30} OPs.")

    # ── Debug: diagnóstico do loader de lençol ─────────────────────────────────
    st.markdown("---")
    st.markdown("##### Debug: loader de lençol (raw)")
    try:
        from utils.cache_manager import get_raw as _get_raw
        _lenc_csv = _get_raw("1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa", "1396046910", ttl=1)
        if not _lenc_csv or not _lenc_csv.strip():
            st.error("get_raw() retornou vazio — sem acesso à planilha lençol")
        else:
            st.success(f"CSV lençol recebido: {len(_lenc_csv):,} bytes".replace(",", "."))
            _lines = _lenc_csv.splitlines()
            st.caption(f"Total de linhas CSV: {len(_lines)}")
            st.markdown("**Primeiras 6 linhas do CSV:**")
            st.code("\n".join(_lines[:6]))
    except Exception as _e:
        st.error(f"Erro ao buscar lençol raw: {_e}")

    st.markdown("##### Debug: load_lencol_smart_xlsx() resultado")
    try:
        import logging as _logging
        from utils.lencol_loader_smart import load_lencol_smart_xlsx as _load_len
        _df_len_dbg = _load_len()
        if _df_len_dbg.empty:
            st.error("load_lencol_smart_xlsx() retornou DataFrame vazio")
        else:
            st.success(f"{len(_df_len_dbg)} linhas carregadas. Colunas: {list(_df_len_dbg.columns)}")
            st.dataframe(_df_len_dbg.head(5), use_container_width=True, hide_index=True)
    except Exception as _e:
        st.error(f"Exceção em load_lencol_smart_xlsx: {_e}")

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# gráficos
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

# ── Previsto × Cortado por OP (das programadas) ───────────────────────────────
# Para OPs que ESTAVAM na programação e tiveram corte: compara o previsto
# (losango) com o que foi efetivamente cortado (barra). Respeita os filtros.
st.markdown('<div class="page-divider"></div>', unsafe_allow_html=True)
st.markdown("### 📊 Previsto × Cortado por OP (programadas)")
st.caption(
    "OPs da programação que tiveram corte. A barra mostra o que foi cortado; "
    "o losango marca o previsto — assim dá para ver se a OP atingiu, passou ou "
    "ficou abaixo do planejado."
)

_prog_cmp = df_agg[
    (df_agg["PED. CLIENTE"].astype(str).str.strip() != "")
    & (df_agg["QNT_CORTADA"] > 0)
].copy()

if _prog_cmp.empty:
    st.info("Nenhuma OP programada com corte no filtro atual.")
else:
    _pc = _prog_cmp.sort_values("QNT_CORTADA", ascending=False).head(15)
    _pc = _pc.sort_values("QNT_CORTADA", ascending=True)
    _ops_lbl = _pc["PED. CLIENTE"].astype(str).tolist()

    fig_pc = go.Figure()
    fig_pc.add_trace(go.Bar(
        x=_pc["QNT_CORTADA"].tolist(), y=_ops_lbl, orientation="h",
        name="Cortado", marker_color="#22c55e",
        text=[f"{int(v):,}".replace(",", ".") for v in _pc["QNT_CORTADA"]],
        textposition="outside",
    ))
    fig_pc.add_trace(go.Scatter(
        x=_pc["QNT_PROG_TOTAL"].tolist(), y=_ops_lbl, mode="markers",
        name="Previsto",
        marker=dict(symbol="diamond", size=13, color="#818CF8",
                    line=dict(color="#FFFFFF", width=1)),
    ))
    fig_pc.update_layout(
        height=max(300, len(_pc) * 36),
        margin=dict(l=0, r=80, t=10, b=0),
        barmode="overlay",
        xaxis_title="Peças", yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD5E0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor="#2D3748"),
        yaxis=dict(gridcolor="#2D3748", type="category",
                   categoryorder="array", categoryarray=_ops_lbl),
    )
    st.plotly_chart(fig_pc, use_container_width=True)

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# tabelas
tab_resumo, tab_detalhe = st.tabs(["📊 Resumo por Ordem (OP)", "📋 Detalhe Completo"])

# tab 1: resumo por op
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

# tab 2: detalhe completo
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
            "QNT. PROG", "DATA INICIO", "DATA FINALIZADO", "PREV. INDUSTRIALIZAÇÃO",
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

# ── Cortes fora da programação ────────────────────────────────────────────────
# OPs que foram cortadas mas NÃO constam na programação (produção fora do plano).
st.markdown('<div class="page-divider"></div>', unsafe_allow_html=True)
st.markdown("### ✂️ Cortes Fora da Programação")
_filtros_aplic = []
if semanas_sel:
    _filtros_aplic.append(", ".join(str(s) for s in sorted(semanas_sel)))
if clientes_sel:
    _filtros_aplic.append("empresa(s): " + ", ".join(sorted(clientes_sel)))
if locais_sel:
    _filtros_aplic.append("local: " + ", ".join(sorted(locais_sel)))
st.caption(
    "OPs que apareceram nas planilhas de corte mas não estão na programação — "
    "ou seja, foi cortado sem ter sido programado."
    + (f" Filtrando por {' · '.join(_filtros_aplic)}." if _filtros_aplic
       else " Considerando todas as semanas e empresas.")
)

from utils.normalize import normalize_op as _nop_fora, normalize_text as _ntxt_fora

if df_cortes_raw.empty:
    st.info("Sem dados de corte carregados.")
else:
    _cortes = df_cortes_raw.copy()
    _cortes["_OPN"] = _cortes["OP"].map(_nop_fora)
    # Respeita o filtro de semana da sidebar: vazio → todas as semanas; com semanas
    # selecionadas → apenas os cortes daquelas semanas.
    # OBS: a SEMANA da programação é texto ("SEMANA 22") e a dos cortes é Int64 (22).
    # Extraímos o número de dentro do texto e normalizamos para o filtro casar
    # ("SEMANA 22"→"22", "SEMANA 01"→"1", 22→"22").
    def _wk_canon(x):
        s = str(x).strip()
        m = re.search(r"\d+", s)
        return str(int(m.group())) if m else s
    if semanas_sel and "SEMANA" in _cortes.columns:
        _sem_alvo = {_wk_canon(s) for s in semanas_sel}
        _cortes = _cortes[_cortes["SEMANA"].map(_wk_canon).isin(_sem_alvo)]
    # Respeita o filtro de Cliente/Empresa: compara por nome normalizado
    # (maiúsculas/acentos) para casar "Burdays" (Giattex) com "BURDAYS" (Lençol).
    if clientes_sel and "CLIENTE" in _cortes.columns:
        _cli_alvo = {_ntxt_fora(c) for c in clientes_sel}
        _cortes = _cortes[_cortes["CLIENTE"].map(_ntxt_fora).isin(_cli_alvo)]
    # Respeita o filtro de Local: mapeia o LOCAL da programação (ex: "GIATTEX",
    # "CORTE LENÇOL", "ZANATTEX") para a FONTE do corte por palavra-chave.
    if locais_sel and "FONTE" in _cortes.columns:
        _LOCAL_FONTE_KW = {
            "Giattex":  ["GIATTEX", "GGTEX", "GIATTA", "IACANGA"],
            "Zanattex": ["ZANATTEX", "AREALVA", "ZANATTA"],
            "Lençol":   ["LENCOL"],
        }
        _locais_norm = [_ntxt_fora(l) for l in locais_sel]
        def _fonte_no_local(fonte):
            kws = _LOCAL_FONTE_KW.get(fonte, [])
            return any(any(kw in ln for kw in kws) for ln in _locais_norm)
        _cortes = _cortes[_cortes["FONTE"].map(_fonte_no_local)]
    _sem_op_pcs = int(_cortes.loc[_cortes["_OPN"] == "", "QUANTIDADE"].sum())
    _cortes = _cortes[_cortes["_OPN"] != ""]

    # Coleta OPs reconhecidas de TODAS as colunas de referência da programação:
    # PED. CLIENTE (ex: 700761-3722-27), PED. INT (ex: 83), OP INTERNA, OC.
    # Assim "PROG 83" → "83" bate com PED. INT=83 e não aparece como "fora".
    _cols_ref = ["PED. CLIENTE", "PED. INT", "OP INTERNA", "OC"]
    _peds_prog_fora: set[str] = set()
    for _c in _cols_ref:
        if _c in df_prog_raw.columns:
            _peds_prog_fora.update(
                o for o in df_prog_raw[_c].map(_nop_fora).unique() if o
            )
    _fora = _cortes[~_cortes["_OPN"].isin(_peds_prog_fora)]

    _total_cort_all = int(_cortes["QUANTIDADE"].sum())
    _total_fora_pcs = int(_fora["QUANTIDADE"].sum())
    _n_ops_fora = int(_fora["_OPN"].nunique())
    _pct_fora = (100 * _total_fora_pcs / _total_cort_all) if _total_cort_all else 0

    kf1, kf2, kf3 = st.columns(3)
    _kpi(kf1, "OPs fora da programação", f"{_n_ops_fora:,}".replace(",", "."),
         "cortadas sem programar", "#f59e0b" if _n_ops_fora else "#22c55e")
    _kpi(kf2, "Peças cortadas fora", f"{_total_fora_pcs:,}".replace(",", "."),
         "total realizado fora do plano", "#f59e0b" if _total_fora_pcs else "#22c55e")
    _kpi(kf3, "% do corte total", f"{_pct_fora:.1f}%".replace(".", ","),
         "do que foi cortado", "#f59e0b" if _pct_fora else "#22c55e")

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if _fora.empty:
        st.success("✅ Tudo o que foi cortado estava na programação.")
    else:
        def _join_unicos(serie):
            vals = sorted({
                str(v).strip() for v in serie
                if str(v).strip() not in ("", "nan", "NaN", "<NA>", "None", "NaT")
            })
            return " / ".join(vals)

        _agg_kwargs = {"QNT CORTADA": ("QUANTIDADE", "sum"), "Fonte": ("FONTE", _join_unicos)}
        if "DATA" in _fora.columns:
            _agg_kwargs["Data(s)"] = (
                "DATA",
                lambda s: " / ".join(
                    sorted({d.strftime("%d/%m/%Y") for d in s.dropna()})
                ),
            )
        if "MATERIAL" in _fora.columns:
            _agg_kwargs["Material"] = ("MATERIAL", _join_unicos)
        if "CLIENTE" in _fora.columns:
            _agg_kwargs["Cliente"] = ("CLIENTE", _join_unicos)
        _tab = (
            _fora.groupby("_OPN")
            .agg(**_agg_kwargs)
            .reset_index()
            .rename(columns={"_OPN": "OP"})
        )
        if "SEMANA" in _fora.columns:
            _sem = _fora.groupby("_OPN")["SEMANA"].apply(
                lambda s: _join_unicos(
                    s.dropna().astype("Int64").astype(str)
                )
            )
            _tab["Semana(s)"] = _tab["OP"].map(_sem)

        _tab = _tab.sort_values("QNT CORTADA", ascending=False).reset_index(drop=True)
        # Reordena: OP, QNT CORTADA, Data(s), restante
        _col_order = ["OP", "QNT CORTADA"]
        if "Data(s)" in _tab.columns:
            _col_order.append("Data(s)")
        _col_order += [c for c in _tab.columns if c not in _col_order]
        _tab = _tab[_col_order]

        _tab_fmt = _tab.copy()
        _tab_fmt["QNT CORTADA"] = _tab_fmt["QNT CORTADA"].map(lambda x: f"{int(x):,}".replace(",", "."))

        st.dataframe(_tab_fmt, use_container_width=True, hide_index=True)

        # Gráfico — top 15 OPs cortadas fora do plano
        _top = _tab.head(15).sort_values("QNT CORTADA", ascending=True)
        # OP é rótulo (categoria), não número — senão o eixo trata "1895301001"
        # como 1,8 bilhão e o gráfico fica achatado.
        _y_labels = _top["OP"].astype(str).tolist()
        fig_fora = go.Figure(go.Bar(
            x=_top["QNT CORTADA"].tolist(), y=_y_labels, orientation="h",
            marker_color="#f59e0b",
            text=[f"{int(v):,}".replace(",", ".") for v in _top["QNT CORTADA"]],
            textposition="outside",
        ))
        fig_fora.update_layout(
            height=max(280, len(_top) * 34),
            margin=dict(l=0, r=70, t=10, b=0),
            xaxis_title="Peças cortadas", yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"),
            xaxis=dict(gridcolor="#2D3748"),
            yaxis=dict(gridcolor="#2D3748", type="category",
                       categoryorder="array", categoryarray=_y_labels),
        )
        st.plotly_chart(fig_fora, use_container_width=True)

    if _sem_op_pcs > 0:
        st.caption(
            f"ℹ️ Além disso, {_sem_op_pcs:,}".replace(",", ".")
            + " peça(s) foram cortadas sem número de OP (não classificáveis)."
        )

# ── Botão Relatório PDF ───────────────────────────────────────────────────────
st.markdown("---")

def _html_ctrl_prog() -> bytes:
    from datetime import datetime as _dt
    agora = _dt.now().strftime("%d/%m/%Y %H:%M")

    def _n(v) -> str:
        return f"{int(v):,}".replace(",", ".")

    filtros_str = []
    if semanas_sel:
        filtros_str.append("Semanas: " + ", ".join(str(s) for s in sorted(semanas_sel)))
    if clientes_sel:
        filtros_str.append("Empresas: " + ", ".join(sorted(clientes_sel)))
    if locais_sel:
        filtros_str.append("Locais: " + ", ".join(sorted(locais_sel)))
    filtros_label = " &nbsp;|&nbsp; ".join(filtros_str) if filtros_str else "Todos os filtros"

    def _op_rows() -> str:
        if df_agg.empty:
            return "<tr><td colspan='9' style='text-align:center'>Sem dados</td></tr>"
        linhas = []
        for _, r in df_agg.iterrows():
            status_c = str(r.get("STATUS_CORTE", ""))
            cls = "sok" if status_c == "Concluído" else ("samb" if status_c == "Parcial" else "serr")
            ef = float(r.get("EFICIÊNCIA_PRC", 0))
            ef_cls = "sok" if ef >= 96 else ("samb" if ef >= 50 else "serr")
            dif = int(r.get("DIFERENÇA", 0))
            dif_s = f"{'+' if dif > 0 else ''}{_n(dif)}"
            op_val = str(r.get("PED. CLIENTE", "")).strip() or "—"
            linhas.append(
                f"<tr>"
                f"<td>{r.get('SEMANA','')}</td>"
                f"<td>{op_val}</td>"
                f"<td>{r.get('CLIENTE','')}</td>"
                f"<td>{r.get('LOCAL','')}</td>"
                f"<td>{r.get('PRODUTO','')}</td>"
                f"<td class='num'>{_n(r.get('QNT_PROG_TOTAL',0))}</td>"
                f"<td class='num'>{_n(r.get('QNT_CORTADA',0))}</td>"
                f"<td class='num {ef_cls}'>{ef:.1f}%</td>"
                f"<td class='{cls}'>{status_c}</td>"
                f"</tr>"
            )
        return "\n".join(linhas)

    op_html = _op_rows()
    ef_total = (total_cort_pcs / total_prog_pcs * 100) if total_prog_pcs > 0 else 0
    cls_ef = "sok" if ef_total >= 96 else ("samb" if ef_total >= 50 else "serr")

    html = (
        "<!DOCTYPE html>\n<html lang='pt-BR'>\n<head>\n"
        "<meta charset='UTF-8'>\n"
        "<title>Relatório Controle de Programação</title>\n"
        "<style>\n"
        "@page { margin: 15mm; size: A4 landscape; }\n"
        "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "body { font-family: Arial, sans-serif; font-size: 10px; color: #1a1a1a; background: #fff; }\n"
        ".hint { background:#FEF3C7; padding:8px 14px; margin-bottom:14px; border-radius:4px; font-size:12px; border:1px solid #FCD34D; }\n"
        ".header { border-bottom:3px solid #6366F1; padding-bottom:8px; margin-bottom:14px; }\n"
        ".header h1 { font-size:17px; color:#1E1B4B; }\n"
        ".header .sub { color:#444; margin-top:3px; font-size:10px; }\n"
        ".kpi-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:6px; margin-bottom:16px; }\n"
        ".kpi { border:1px solid #6366F1; border-radius:5px; padding:6px 8px; text-align:center; }\n"
        ".kpi-lbl { font-size:7.5px; color:#555; text-transform:uppercase; letter-spacing:.05em; }\n"
        ".kpi-val { font-size:13px; font-weight:700; color:#1E1B4B; margin-top:2px; }\n"
        ".sec { font-size:11px; font-weight:700; color:#1E1B4B; border-bottom:1px solid #6366F1; margin:14px 0 7px 0; padding-bottom:3px; }\n"
        "table { width:100%; border-collapse:collapse; margin-bottom:14px; font-size:9px; }\n"
        "th { background:#1E1B4B; color:#fff; padding:4px 6px; text-align:left; font-size:8px; text-transform:uppercase; letter-spacing:.04em; }\n"
        "td { padding:3px 5px; border-bottom:1px solid #e5e7eb; }\n"
        "tr:nth-child(even) td { background:#F5F3FF; }\n"
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
        "  <h1>&#128202; Relatório Controle de Programação de Corte</h1>\n"
        f"  <div class='sub'>{filtros_label} &nbsp;|&nbsp; Gerado em: {agora}</div>\n"
        "</div>\n"
        "<div class='kpi-grid'>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Total de OPs</div><div class='kpi-val'>{total_ops}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Concluídas</div><div class='kpi-val sok'>{concluidas}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Parciais</div><div class='kpi-val samb'>{parciais}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Pendentes</div><div class='kpi-val serr'>{pendentes}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Aderência</div><div class='kpi-val'>{aderencia_pct:.1f}%</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Peças Prog.</div><div class='kpi-val'>{_n(total_prog_pcs)}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Peças Cortadas</div><div class='kpi-val {cls_ef}'>{_n(total_cort_pcs)}</div></div>\n"
        "</div>\n"
        "<div class='sec'>Resumo por Ordem (OP)</div>\n"
        "<table>\n"
        "  <thead><tr><th>Sem.</th><th>OP</th><th>Cliente</th><th>Local</th><th>Produto</th>"
        "<th class='num'>Prog.</th><th class='num'>Cortado</th>"
        "<th class='num'>Efic. %</th><th>Status Corte</th></tr></thead>\n"
        f"  <tbody>{op_html}</tbody>\n"
        "</table>\n"
        "<div class='footer'>"
        f"Relatório Controle de Programação de Corte &middot; "
        f"Sistema Unificação dos Dados &middot; {agora}"
        "</div>\n</body>\n</html>"
    )
    return html.encode("utf-8")

