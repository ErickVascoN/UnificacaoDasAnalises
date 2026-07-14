"""Dashboard de Previsão de Cargas — análise mensal previsão vs. realizado."""

from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from styles.global_ui import get_global_ui_css
from utils.pdf_report import gerar_pdf_previsao_cargas
from utils.cargas_loader import (
    CARGAS_CACHE_TTL,
    MESES_DISPONIVEIS,
    _norm,
    _estimativa_mes_atual,
    load_cargas,
)
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button

# ── Configuração ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Previsão de Cargas | Zanattex",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)
render_home_button()  # sempre visível, mesmo sem dados

DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12),
    separators=",.",
    margin=dict(l=40, r=20, t=50, b=40),
)
_AXIS_BASE = dict(gridcolor="#2D3748", linecolor="#4A5568", zerolinecolor="#4A5568")
DARK_AXES = dict(xaxis=_AXIS_BASE, yaxis=_AXIS_BASE)


def _layout(**kwargs) -> dict:
    """Merge DARK + DARK_AXES base with per-chart overrides (avoids duplicate key errors)."""
    out = {**DARK}
    x_override = kwargs.pop("xaxis", {})
    y_override = kwargs.pop("yaxis", {})
    out["xaxis"] = {**_AXIS_BASE, **x_override}
    out["yaxis"] = {**_AXIS_BASE, **y_override}
    out.update(kwargs)
    return out

CORES = {
    "previsao":  "#4ECDC4",
    "realizado": "#45B7D1",
    "diferenca_pos": "#48BB78",
    "diferenca_neg": "#FC8181",
    "accent":    "#FFA726",
    "neutro":    "#718096",
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0F1117; }
[data-testid="stSidebar"] { background: #1A1D2E; border-right: 1px solid #2D3748; }

.pg-badge {
    display:inline-block; padding:5px 18px; border-radius:999px;
    font-size:.75rem; letter-spacing:.18em; text-transform:uppercase; font-weight:700;
    color:#FFA726; background:rgba(255,167,38,.10); border:1px solid rgba(255,167,38,.30);
    margin-bottom:14px;
}
.pg-title {
    font-size:2.2rem; font-weight:900; color:#FFF; margin:0 0 4px 0; line-height:1.1;
}
.pg-sub { color:#718096; font-size:.95rem; margin-bottom:0; }
.accent { color:#FFA726; }

.kpi-card {
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
    border-radius:14px; padding:18px 20px; text-align:center;
}
.kpi-label { font-size:.75rem; color:#718096; text-transform:uppercase; letter-spacing:.12em; margin-bottom:6px; }
.kpi-value { font-size:1.65rem; font-weight:800; color:#FFF; line-height:1; margin-bottom:4px; }
.kpi-delta { font-size:.82rem; font-weight:600; }
.kpi-pos { color:#48BB78; }
.kpi-neg { color:#FC8181; }
.kpi-neu { color:#718096; }

.sec-title {
    font-size:1rem; font-weight:700; color:#E2E8F0;
    margin:24px 0 12px 0; padding-bottom:6px;
    border-bottom:2px solid rgba(255,167,38,.3);
}
.alert-box {
    padding:12px 16px; border-radius:10px; margin-bottom:12px;
    background:rgba(252,129,129,.08); border:1px solid rgba(252,129,129,.25);
    color:#FC8181; font-size:.88rem;
}
.ok-box {
    padding:12px 16px; border-radius:10px; margin-bottom:12px;
    background:rgba(72,187,120,.08); border:1px solid rgba(72,187,120,.25);
    color:#48BB78; font-size:.88rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers de formatação (parsing/loader agora em utils/cargas_loader.py) ────
def _fmt(v: float, dec: int = 0) -> str:
    if dec == 0:
        return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return f"{v:+.1f}%".replace(".", ",")


# ── Layout principal ──────────────────────────────────────────────────────────
with st.spinner("⏳ Carregando dados de cargas…"):
    df_raw = load_cargas()

if df_raw.empty:
    st.error("❌ Nenhum dado disponível. Verifique o acesso à planilha.")
    st.stop()

with st.sidebar:
    st.markdown("## 🚛 Filtros")

    st.caption(f"Atualizado a cada {CARGAS_CACHE_TTL}s · {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Atualizar Dados", key="refresh_cargas", use_container_width=True):
        load_cargas.clear()
        st.rerun()

    st.markdown("---")
    # "NAO_ALOCADO" é um registro sintético (Realizado do painel diário sem carga
    # cadastrada no mês) — não é uma carga real, não deve aparecer como opção de filtro.
    _df_filtro_opcoes = df_raw[df_raw["STATUS"] != "NAO_ALOCADO"]
    st.markdown("**📅 Meses**")
    meses_disp = df_raw["MES"].unique().tolist()
    sel_meses = st.multiselect(
        "Mês", meses_disp, default=meses_disp, placeholder="Todos", key="sel_mes_carga"
    )
    if not sel_meses:
        sel_meses = meses_disp

    st.markdown("**🏢 Destino / Cliente**")
    destinos_disp = sorted(_df_filtro_opcoes["DESTINO_NORM"].unique())
    sel_destinos = st.multiselect(
        "Destino", destinos_disp, placeholder="Todos", key="sel_dest_carga"
    )

    st.markdown("**📍 Local de Carregamento**")
    locais_disp = sorted(_df_filtro_opcoes["LOCAL"].unique())
    sel_locais = st.multiselect(
        "Origem", locais_disp, placeholder="Todas", key="sel_local_carga"
    )

    st.markdown("**🚦 Status da Carga**")
    # Exclui "SEMANA_TOTAL"/"NAO_ALOCADO" da lista visível — são internos ao parser, não um status de carga
    status_disp = sorted(s for s in _df_filtro_opcoes["STATUS"].unique() if s not in ("SEMANA_TOTAL", "CARGO_REAL"))
    sel_status = st.multiselect(
        "Status", status_disp, default=status_disp,
        placeholder="Todos", key="sel_status_carga"
    )
    if not sel_status:
        sel_status = status_disp

    st.markdown("---")
    mostrar_sem_real = st.toggle(
        "Incluir cargas sem realizado", value=False, key="toggle_sem_real"
    )



# ── Aplicar filtros ───────────────────────────────────────────────────────────
# Linhas CARGO_REAL (tabela lateral de realizado) e NAO_ALOCADO (Realizado do painel
# diário sem carga cadastrada no mês) são preservadas sem filtro de destino/local/
# status — são registros sintéticos, não cargas reais, e o Realizado/KPI do mês
# tem que continuar batendo mesmo que o usuário filtre por destino/local/status.
_df_mes = df_raw[df_raw["MES"].isin(sel_meses)]
df_real_fixo    = _df_mes[_df_mes["STATUS"] == "CARGO_REAL"].copy()
df_naoaloc_fixo = _df_mes[_df_mes["STATUS"] == "NAO_ALOCADO"].copy()
df_cargo_filt   = _df_mes[~_df_mes["STATUS"].isin(["CARGO_REAL", "NAO_ALOCADO"])].copy()

if sel_destinos:
    df_cargo_filt = df_cargo_filt[df_cargo_filt["DESTINO_NORM"].isin(sel_destinos)]
if sel_locais:
    df_cargo_filt = df_cargo_filt[df_cargo_filt["LOCAL"].isin(sel_locais)]
if sel_status:
    df_cargo_filt = df_cargo_filt[df_cargo_filt["STATUS"].isin(sel_status)]
if not mostrar_sem_real:
    # Mantém cargos de meses com previsto oficial mesmo que PREVISAO individual = 0
    _meses_com_prev_ofic = set(df_real_fixo[df_real_fixo["PREVISAO"] > 0]["MES_NUM"])
    df_cargo_filt = df_cargo_filt[
        (df_cargo_filt["PREVISAO"] > 0) |
        df_cargo_filt["MES_NUM"].isin(_meses_com_prev_ofic)
    ]

df = pd.concat([df_real_fixo, df_naoaloc_fixo, df_cargo_filt], ignore_index=True)

if df.empty:
    st.warning("⚠️ Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

render_filtros_btn()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center'><span class='pg-badge'>🚛 Logística · Zanattex</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h1 class='pg-title' style='text-align:center'>Dashboard de <span class='accent'>Previsão de Cargas</span></h1>"
    "<p class='pg-sub' style='text-align:center'>Análise de previsão vs. realizado por mês, destino e origem</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── KPIs globais ──────────────────────────────────────────────────────────────
# PREVISTO = soma de df["PREVISAO"] (cargo fretes + CARGO_REAL.PREVISAO oficial).
# Para meses sem previsto oficial: fretes somados dos cargos; CARGO_REAL.PREVISAO = 0.
# Para meses com previsto oficial: fretes dos cargos = 0; CARGO_REAL.PREVISAO = oficial.
# Assim df["PREVISAO"].sum() nunca dupla-conta.
df_cargos    = df[df["STATUS"].isin(["Normal", "Cancelada", "Adiada", "Armazenagem"])]
df_realizados = df[df["STATUS"] == "CARGO_REAL"]

total_prev   = df["PREVISAO"].sum()
total_real   = df_realizados["REALIZADO"].sum()
diferenca_g  = total_real - total_prev if total_prev > 0 else 0.0

# Aderência: apenas meses que já têm REALIZADO > 0 (exclui meses futuros/incompletos)
_meses_com_real = set(
    df_realizados.groupby("MES_NUM")["REALIZADO"]
    .sum().pipe(lambda s: s[s > 0].index)
)
_prev_adh = df[df["MES_NUM"].isin(_meses_com_real)]["PREVISAO"].sum()
_real_adh = df_realizados[df_realizados["MES_NUM"].isin(_meses_com_real)]["REALIZADO"].sum()
aderencia_g  = (_real_adh / _prev_adh * 100) if _prev_adh > 0 else 0.0
n_cargas     = df_cargos["DATA"].nunique()
n_canceladas = (df_cargos["STATUS"] == "Cancelada").sum()
n_adiadas    = (df_cargos["STATUS"] == "Adiada").sum()
n_clientes   = df_cargos["DESTINO_NORM"].nunique()

col1, col2, col3, col4, col5, col6 = st.columns(6)
kpis = [
    (col1, "💰 Previsão Total",   _fmt(total_prev), "", "neu"),
    (col2, "✅ Realizado Total",  _fmt(total_real), "", "neu"),
    (col3, "⚖️ Diferença",       _fmt(diferenca_g),
     f"{'+' if diferenca_g >= 0 else ''}{_fmt(diferenca_g)} vs previsão",
     "pos" if diferenca_g >= 0 else "neg"),
    (col4, "🎯 Aderência",       f"{aderencia_g:.1f}%".replace(".", ","),
     "Realizado / Previsto", "pos" if aderencia_g >= 95 else ("neg" if aderencia_g < 80 else "neu")),
    (col5, "🚚 Clientes Ativos",  str(n_clientes), "", "neu"),
    (col6, "🚩 Canceladas+Adiadas", str(n_canceladas + n_adiadas),
     f"{n_canceladas} cancel. · {n_adiadas} adiadas",
     "neg" if (n_canceladas + n_adiadas) > 5 else "neu"),
]
for col, label, value, delta, color in kpis:
    with col:
        delta_html = (
            f"<div class='kpi-delta kpi-{color}'>{delta}</div>" if delta else ""
        )
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div>"
            f"{delta_html}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Projeção de Fechamento do Mês Atual ───────────────────────────────────────
_estim = _estimativa_mes_atual(df_raw)
if _estim is not None:
    st.markdown("<div class='sec-title'>📈 Projeção de Fechamento do Mês Atual</div>", unsafe_allow_html=True)
    st.caption(
        f"Previsto Projetado = Previsto lançado ÷ {_estim['dias_corridos']} dias cobertos pelos "
        f"lançamentos × {_estim['dias_totais']} dias do mês. Realizado Estimado = Previsto Projetado × Aderência "
        f"Média dos {_estim['n_meses_base']} últimos meses fechados. Estimativa, não substitui o "
        f"Realizado oficial."
    )
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    estim_kpis = [
        (col_e1, "📋 Previsto Lançado", _fmt(_estim["previsto_lancado"]), "", "neu"),
        (col_e2, "📐 Previsto Projetado", _fmt(_estim["previsto_projetado"]), "run-rate do mês", "neu"),
        (col_e3, "🎯 Aderência Base", f"{_estim['aderencia_media']*100:.1f}%".replace(".", ","),
         "média últimos meses fechados", "neu"),
        (col_e4, "🔮 Realizado Estimado", _fmt(_estim["realizado_estimado"]), "projeção de fechamento", "neu"),
    ]
    for col, label, value, delta, color in estim_kpis:
        with col:
            delta_html = f"<div class='kpi-delta kpi-{color}'>{delta}</div>" if delta else ""
            st.markdown(
                f"<div class='kpi-card'>"
                f"<div class='kpi-label'>{label}</div>"
                f"<div class='kpi-value'>{value}</div>"
                f"{delta_html}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Previsão vs Realizado por Mês ─────────────────────────────────────────────
st.markdown("<div class='sec-title'>📊 Previsão vs. Realizado por Mês</div>", unsafe_allow_html=True)

_prev_mes = (
    df.groupby(["MES", "MES_NUM"])["PREVISAO"].sum().reset_index()
)
_real_mes = (
    df_realizados.groupby(["MES", "MES_NUM"])["REALIZADO"].sum().reset_index()
)
df_mes = (
    _prev_mes.merge(_real_mes, on=["MES", "MES_NUM"], how="outer")
    .fillna(0)
    .sort_values("MES_NUM")
)
df_mes["ADERENCIA"] = df_mes.apply(
    lambda r: r["REALIZADO"] / r["PREVISAO"] * 100 if r["PREVISAO"] > 0 else 0, axis=1
)
df_mes["DIFERENCA"] = df_mes["REALIZADO"] - df_mes["PREVISAO"]

fig_mes = go.Figure()
fig_mes.add_bar(
    x=df_mes["MES"], y=df_mes["PREVISAO"],
    name="Previsão", marker_color=CORES["previsao"],
    text=[_fmt(v) for v in df_mes["PREVISAO"]],
    textposition="outside", textfont=dict(size=10),
)
fig_mes.add_bar(
    x=df_mes["MES"], y=df_mes["REALIZADO"],
    name="Realizado", marker_color=CORES["realizado"],
    text=[_fmt(v) for v in df_mes["REALIZADO"]],
    textposition="outside", textfont=dict(size=10),
)
fig_mes.add_scatter(
    x=df_mes["MES"], y=df_mes["ADERENCIA"],
    name="Aderência %", mode="lines+markers+text",
    yaxis="y2", line=dict(color=CORES["accent"], width=2.5),
    marker=dict(size=8, color=CORES["accent"]),
    text=[f"{v:.0f}%".replace(".", ",") for v in df_mes["ADERENCIA"]],
    textposition="top center", textfont=dict(size=10, color=CORES["accent"]),
)
fig_mes.update_layout(
    **_layout(
        barmode="group", height=380,
        title="Previsão vs. Realizado — visão mensal",
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        yaxis=dict(tickprefix="R$ ", separatethousands=True),
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False,
            range=[0, 160], ticksuffix="%", title="Aderência %",
        ),
    )
)
st.plotly_chart(fig_mes, use_container_width=True)

# ── Linha 2: Por Destino + Por Local ─────────────────────────────────────────
st.markdown("<div class='sec-title'>🏢 Análise por Destino e Origem</div>", unsafe_allow_html=True)
col_g1, col_g2 = st.columns(2)

with col_g1:
    # Usa VALOR_FRETE (nunca zerado) em vez de PREVISAO: em meses com previsto
    # oficial no painel-resumo, PREVISAO de cada carga é zerada (o total já vem
    # do registro CARGO_REAL), o que deixaria esta quebra por cliente vazia.
    df_dest = (
        df[df["TEM_REALIZADO"] & (df["VALOR_FRETE"] > 0)]
        .groupby("DESTINO_NORM")
        .agg(PREVISAO=("VALOR_FRETE", "sum"), N_CARGAS=("DATA", "count"))
        .reset_index()
        .sort_values("PREVISAO", ascending=True)
        .tail(12)
    )
    fig_dest = go.Figure()
    fig_dest.add_bar(
        y=df_dest["DESTINO_NORM"], x=df_dest["PREVISAO"],
        name="Previsão (faturamento)", orientation="h", marker_color=CORES["previsao"],
        text=[_fmt(v) for v in df_dest["PREVISAO"]],
        textposition="outside", textfont=dict(size=9),
    )
    fig_dest.update_layout(
        **_layout(
            height=360,
            title="Previsão por Cliente - Meses Concluídos",
            xaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_dest, use_container_width=True)

with col_g2:
    # Mesmo motivo do df_dest acima: VALOR_FRETE nunca é zerado por mês.
    df_local = (
        df[df["VALOR_FRETE"] > 0]
        .groupby("LOCAL")
        .agg(PREVISAO=("VALOR_FRETE", "sum"), N=("DATA", "count"))
        .reset_index()
        .sort_values("PREVISAO", ascending=False)
    )
    fig_local = go.Figure(go.Pie(
        labels=df_local["LOCAL"],
        values=df_local["PREVISAO"],
        hole=0.52,
        textinfo="label+percent",
        hovertemplate="%{label}<br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        marker=dict(colors=["#4ECDC4", "#45B7D1", "#FFA726", "#FC8181", "#48BB78", "#A78BFA"]),
    ))
    fig_local.update_layout(
        **DARK, height=360,
        title="Distribuição por Local de Carregamento",
        annotations=[dict(text="Origem", x=.5, y=.5,
                          font=dict(size=11, color="#CBD5E0"), showarrow=False)],
    )
    st.plotly_chart(fig_local, use_container_width=True)

# ── Linha 3: Aderência por cliente + Evolução semanal ────────────────────────
st.markdown("<div class='sec-title'>🎯 Aderência da Previsão por Cliente</div>", unsafe_allow_html=True)
col_g3, col_g4 = st.columns(2)

with col_g3:
    # Aderência calculada pelo total mensal (REALIZADO mensal / PREVISTO mensal).
    # Não filtra por STATUS != CARGO_REAL: em meses com previsto oficial, o total
    # mora no registro CARGO_REAL (fretes individuais ficam zerados), então excluí-lo
    # zerava a previsão do mês inteiro assim que só meses "oficiais" ficavam selecionados.
    _prev_adh = (
        df[df["PREVISAO"] > 0]
        .groupby("MES")["PREVISAO"].sum()
    )
    _real_adh = (
        df[df["STATUS"] == "CARGO_REAL"]
        .groupby("MES")["REALIZADO"].sum()
    )
    df_adh = pd.DataFrame({"PREVISAO": _prev_adh, "REALIZADO": _real_adh}).dropna().reset_index()
    df_adh = df_adh[df_adh["PREVISAO"] > 0].copy()
    df_adh["ADERENCIA"] = df_adh["REALIZADO"] / df_adh["PREVISAO"] * 100
    df_adh = df_adh.sort_values("ADERENCIA", ascending=True)

    colors_bar = [
        CORES["diferenca_pos"] if v >= 95 else (CORES["diferenca_neg"] if v < 80 else CORES["accent"])
        for v in df_adh["ADERENCIA"]
    ]
    fig_adh = go.Figure(go.Bar(
        y=df_adh["MES"],
        x=df_adh["ADERENCIA"],
        orientation="h",
        marker_color=colors_bar,
        text=[f"{v:.1f}%".replace(".", ",") for v in df_adh["ADERENCIA"]],
        textposition="outside",
        hovertemplate="%{y}<br>Aderência: %{x:.1f}%<extra></extra>",
    ))
    fig_adh.add_vline(x=100, line_dash="dash", line_color="#718096", line_width=1.5,
                      annotation_text="Meta 100%", annotation_font_color="#718096")
    fig_adh.update_layout(
        **_layout(
            height=360,
            title="% Aderência (Realizado / Previsto) por Mês",
            xaxis=dict(ticksuffix="%", range=[0, 160]),
        )
    )
    st.plotly_chart(fig_adh, use_container_width=True)

with col_g4:
    # Usa VALOR_FRETE (nunca zerado) em vez de PREVISAO: para meses com previsto
    # oficial no painel-resumo (ex.: Janeiro, Maio, Junho), PREVISAO de cada carga
    # é zerada para não contar em dobro no total mensal — isso apagaria o mês
    # inteiro da quebra semanal, que não tem um "oficial" equivalente por semana.
    # Agrupa pela SEMANA da própria planilha (cabeçalho "SEMANA DD/MM A DD/MM"),
    # não por semana ISO — evita datas de corte que não batem com o que está na planilha.
    # Previsão/N só olham cargas com frete (VALOR_FRETE > 0) — cargas de Armazenagem
    # ou frete subcontratado (ex.: "FRETE GALICE") não entram na previsão de custo.
    # Realizado, porém, precisa somar TODAS as cargas da semana (inclusive as de
    # frete zero): o painel diário atribui o Realizado por (data, cliente), e um
    # cliente pode ter uma carga de Armazenagem e uma carga normal no mesmo dia —
    # se o Realizado só somasse as cargas com frete, a parte dividida para a carga
    # de frete zero desaparecia da semana (ex.: Julho 06/07-11/07 mostrava
    # R$ 803.070 quando a planilha soma R$ 848.057 para o mesmo período; bug
    # relatado pelo usuário em 13/07/2026).
    _semana_base = df[df["TEM_REALIZADO"]]
    df_week_prev = (
        _semana_base[_semana_base["VALOR_FRETE"] > 0]
        .groupby(["MES", "MES_NUM", "SEMANA"])
        .agg(PREVISAO=("VALOR_FRETE", "sum"), N=("DATA", "count"))
        .reset_index()
    )
    df_week_real = (
        _semana_base
        .groupby(["MES", "MES_NUM", "SEMANA"])
        .agg(REALIZADO=("REALIZADO_DIA", "sum"), INICIO=("DATA", "min"), FIM=("DATA", "max"))
        .reset_index()
    )
    df_week = df_week_prev.merge(
        df_week_real, on=["MES", "MES_NUM", "SEMANA"], how="outer"
    )
    df_week[["PREVISAO", "N"]] = df_week[["PREVISAO", "N"]].fillna(0)
    df_week = df_week.sort_values("INICIO")

    def _semana_label(row) -> str:
        if row["SEMANA"] == "NAO_ALOCADO":
            return f"{row['INICIO'].strftime('%d/%m')} a {row['FIM'].strftime('%d/%m')} (sem previsão)"
        m = re.search(r"(\d{2}/\d{2})\s*A\s*(\d{2}/\d{2})", _norm(row["SEMANA"]))
        if m:
            return f"{m.group(1)} a {m.group(2)}"
        # Sem cabeçalho de semana no início do mês (continuação da semana anterior)
        return f"{row['INICIO'].strftime('%d/%m')} a {row['FIM'].strftime('%d/%m')}"

    df_week["LABEL"] = df_week.apply(_semana_label, axis=1)

    # Gráfico de evolução semanal é uma linha de tendência semana-a-semana — a linha
    # "Não alocado" (dias sem nenhuma previsão) quebraria essa leitura com um ponto de
    # Previsão zerada fora de sequência. Ela continua aparecendo na tabela abaixo.
    df_week_chart = df_week[df_week["SEMANA"] != "NAO_ALOCADO"]

    fig_week = go.Figure()
    fig_week.add_scatter(
        x=df_week_chart["LABEL"], y=df_week_chart["PREVISAO"],
        name="Previsão", mode="lines+markers+text",
        line=dict(color=CORES["previsao"], width=2.5),
        marker=dict(size=7),
        text=[_fmt(v) for v in df_week["PREVISAO"]],
        textposition="top center", textfont=dict(size=9, color=CORES["previsao"]),
    )
    fig_week.add_scatter(
        x=df_week_chart["LABEL"], y=df_week_chart["REALIZADO"],
        name="Realizado", mode="lines+markers",
        line=dict(color=CORES["realizado"], width=2, dash="dot"),
        marker=dict(size=6),
    )
    fig_week.update_layout(
        **_layout(
            height=360,
            title="Evolução Semanal — Previsão vs. Realizado",
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
            yaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_week, use_container_width=True)

st.markdown("<div class='sec-title'>📆 Detalhamento por Semana</div>", unsafe_allow_html=True)
st.caption(
    "O Realizado por semana é estimado casando cliente + data com o painel diário da planilha "
    "e recalibrado para que a soma do mês bata exatamente com o Realizado oficial da planilha "
    "(nem todo lançamento diário casa por nome com uma carga específica). O total mensal é exato; "
    "a distribuição entre semanas é uma aproximação."
)

df_week_tab = df_week.copy()
df_week_tab["DIFERENCA"] = df_week_tab["REALIZADO"] - df_week_tab["PREVISAO"]
df_week_tab["ADERENCIA"] = df_week_tab.apply(
    lambda r: r["REALIZADO"] / r["PREVISAO"] * 100 if r["PREVISAO"] > 0 else None, axis=1
)

df_week_show = df_week_tab[
    ["MES", "LABEL", "N", "PREVISAO", "REALIZADO", "DIFERENCA", "ADERENCIA"]
].copy()
for _col in ["PREVISAO", "REALIZADO", "DIFERENCA"]:
    df_week_show[_col] = df_week_show[_col].apply(_fmt)
# Sem previsão (linha "Não alocado") não tem meta pra comparar — "0,0%" pareceria meta
# perdida quando na verdade não existe meta. Mostra "—" nesse caso.
df_week_show["ADERENCIA"] = df_week_show["ADERENCIA"].apply(
    lambda v: "—" if pd.isna(v) else f"{v:.1f}%".replace(".", ",")
)
df_week_show.columns = ["Mês", "Semana", "Cargas", "Previsão", "Realizado", "Diferença", "Aderência"]
st.dataframe(df_week_show, use_container_width=True, hide_index=True)

# ── Linha 4: Tipo de veículo + Timeline ──────────────────────────────────────
st.markdown("<div class='sec-title'>🚚 Frota e Timeline de Cargas</div>", unsafe_allow_html=True)
col_g5, col_g6 = st.columns(2)

with col_g5:
    df_veic = (
        df[~df["STATUS"].isin(["CARGO_REAL", "NAO_ALOCADO"]) & (df["TIPO_VEICULO"] != "Outro")]
        .groupby("TIPO_VEICULO")
        .agg(N=("DATA", "count"), PREVISAO=("VALOR_FRETE", "sum"))
        .reset_index()
        .sort_values("N", ascending=False)
    )
    fig_veic = go.Figure()
    fig_veic.add_bar(
        x=df_veic["TIPO_VEICULO"], y=df_veic["N"],
        name="Qtd. Cargas", marker_color=CORES["previsao"],
        text=df_veic["N"], textposition="outside",
        yaxis="y",
    )
    fig_veic.add_scatter(
        x=df_veic["TIPO_VEICULO"], y=df_veic["PREVISAO"],
        name="Previsão R$", mode="markers",
        marker=dict(size=14, color=CORES["accent"], symbol="diamond"),
        yaxis="y2",
    )
    fig_veic.update_layout(
        **_layout(
            height=320,
            title="Cargas por Tipo de Veículo",
            yaxis=dict(title="Qtd. Cargas"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title="Previsão R$", tickprefix="R$ "),
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        )
    )
    st.plotly_chart(fig_veic, use_container_width=True)

with col_g6:
    df_tl = (
        df[~df["STATUS"].isin(["CARGO_REAL", "NAO_ALOCADO"])]
        .groupby(["DATA", "STATUS"])
        .agg(PREVISAO=("VALOR_FRETE", "sum"), N=("DESTINO", "count"))
        .reset_index()
    )
    cores_status = {"Normal": CORES["previsao"], "Cancelada": CORES["diferenca_neg"],
                    "Adiada": CORES["accent"], "Armazenagem": CORES["neutro"]}
    fig_tl = go.Figure()
    for status_v, grp in df_tl.groupby("STATUS"):
        fig_tl.add_scatter(
            x=grp["DATA"], y=grp["PREVISAO"],
            mode="markers",
            name=status_v,
            marker=dict(
                size=grp["N"] * 5 + 8,
                color=cores_status.get(status_v, "#718096"),
                opacity=0.8,
                line=dict(color="rgba(255,255,255,.2)", width=1),
            ),
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                f"Status: {status_v}<br>"
                "Previsão: R$ %{y:,.0f}<br>"
                "Cargas: %{customdata}<extra></extra>"
            ),
            customdata=grp["N"],
        )
    fig_tl.update_layout(
        **_layout(
            height=320,
            title="Timeline de Cargas (tamanho = qtd. por dia)",
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            yaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_tl, use_container_width=True)

# ── Cancelamentos e Adiamentos ────────────────────────────────────────────────
st.markdown("<div class='sec-title'>🚨 Ocorrências — Canceladas e Adiadas</div>", unsafe_allow_html=True)

df_ocorr = df[df["STATUS"].isin(["Cancelada", "Adiada"])].copy()
if df_ocorr.empty:
    st.markdown("<div class='ok-box'>✅ Nenhuma cancelamento ou adiamento nos filtros selecionados.</div>",
                unsafe_allow_html=True)
else:
    valor_impacto = df_ocorr["VALOR_FRETE"].sum()
    n_cancel = (df_ocorr["STATUS"] == "Cancelada").sum()
    n_adiad  = (df_ocorr["STATUS"] == "Adiada").sum()

    st.markdown(
        f"<div class='alert-box'>⚠️ <strong>{len(df_ocorr)}</strong> ocorrências detectadas — "
        f"{n_cancel} canceladas · {n_adiad} adiadas · "
        f"Impacto na previsão: <strong>{_fmt(valor_impacto)}</strong></div>",
        unsafe_allow_html=True,
    )

    col_oc1, col_oc2 = st.columns(2)
    with col_oc1:
        df_oc_mes = df_ocorr.groupby(["MES", "STATUS"]).size().reset_index(name="N")
        fig_oc = px.bar(
            df_oc_mes, x="MES", y="N", color="STATUS",
            color_discrete_map={"Cancelada": CORES["diferenca_neg"], "Adiada": CORES["accent"]},
            title="Ocorrências por Mês",
            labels={"N": "Qtd.", "MES": "Mês"},
        )
        fig_oc.update_layout(**_layout(height=300, legend=dict(orientation="h", y=-0.18)))
        st.plotly_chart(fig_oc, use_container_width=True)

    with col_oc2:
        df_oc_dest = (
            df_ocorr.groupby("DESTINO_NORM")
            .agg(N=("DATA", "count"), PREVISAO=("VALOR_FRETE", "sum"))
            .reset_index()
            .sort_values("N", ascending=True)
        )
        fig_oc2 = go.Figure(go.Bar(
            y=df_oc_dest["DESTINO_NORM"], x=df_oc_dest["N"],
            orientation="h",
            text=df_oc_dest["N"], textposition="outside",
            marker_color=CORES["diferenca_neg"],
        ))
        fig_oc2.update_layout(
            **_layout(
                height=300,
                title="Ocorrências por Destino",
                xaxis=dict(title="Qtd."),
            )
        )
        st.plotly_chart(fig_oc2, use_container_width=True)

# ── Heatmap: cargas por dia da semana e mês ───────────────────────────────────
st.markdown("<div class='sec-title'>📅 Mapa de Calor — Cargas por Dia da Semana</div>", unsafe_allow_html=True)

dias_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dias_pt    = {"Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
              "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"}

df_heat = (
    df[df["TEM_REALIZADO"] & (df["VALOR_FRETE"] > 0)]
    .groupby(["MES", "DIA_SEMANA"])
    .agg(PREVISAO=("VALOR_FRETE", "sum"), N=("DATA", "count"))
    .reset_index()
)
df_heat["DIA_PT"] = df_heat["DIA_SEMANA"].map(dias_pt)

pivot_heat = df_heat.pivot_table(
    index="DIA_SEMANA", columns="MES", values="PREVISAO", aggfunc="sum", fill_value=0
)
# Ordenar dias
pivot_heat = pivot_heat.reindex([d for d in dias_order if d in pivot_heat.index])
pivot_heat.index = [dias_pt.get(d, d) for d in pivot_heat.index]

# Ordenar meses
mes_order = [m[0] for m in MESES_DISPONIVEIS if m[0] in pivot_heat.columns]
pivot_heat = pivot_heat[mes_order]

fig_heat = go.Figure(go.Heatmap(
    z=pivot_heat.values,
    x=pivot_heat.columns.tolist(),
    y=pivot_heat.index.tolist(),
    colorscale=[
        [0, "rgba(30,40,60,.4)"],
        [0.3, "#1A3A5C"],
        [0.7, "#2196F3"],
        [1, "#4ECDC4"],
    ],
    hovertemplate="%{y} · %{x}<br>R$ %{z:,.0f}<extra></extra>",
    colorbar=dict(title="R$", tickprefix="R$ "),
    text=[[_fmt(v).replace("R$ ", "") for v in row] for row in pivot_heat.values],
    texttemplate="%{text}",
    textfont=dict(size=9),
))
fig_heat.update_layout(**DARK, height=320, title="Previsão de Faturamento por Dia da Semana × Mês")
st.plotly_chart(fig_heat, use_container_width=True)

# ── Tabela detalhada ──────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>📋 Detalhe de Registros</div>", unsafe_allow_html=True)

col_tb1, col_tb2 = st.columns([3, 1])
with col_tb2:
    busca = st.text_input("🔍 Buscar destino/cliente", "", key="busca_carga", placeholder="ex: CAMESA")

df_show = df[df["STATUS"] != "CARGO_REAL"].copy()
if busca.strip():
    mask = df_show["DESTINO_NORM"].str.contains(busca.upper(), na=False) | \
           df_show["CLIENTE"].str.contains(busca.upper(), na=False)
    df_show = df_show[mask]

df_table = df_show[[
    "MES", "DATA", "DESTINO", "LOCAL", "TIPO_VEICULO",
    "CLIENTE", "VALOR_FRETE", "REALIZADO_DIA", "STATUS", "OBS"
]].copy()
df_table["DIFERENCA"] = df_table["REALIZADO_DIA"] - df_table["VALOR_FRETE"]

df_table["DATA"] = df_table["DATA"].dt.strftime("%d/%m/%Y")
for col in ["VALOR_FRETE", "REALIZADO_DIA", "DIFERENCA"]:
    df_table[col] = df_table[col].apply(lambda v: _fmt(v))

df_table = df_table[[
    "MES", "DATA", "DESTINO", "LOCAL", "TIPO_VEICULO",
    "CLIENTE", "VALOR_FRETE", "REALIZADO_DIA", "DIFERENCA", "STATUS", "OBS"
]]
df_table.columns = [
    "Mês", "Data Carga", "Destino", "Origem", "Veículo",
    "Cliente", "Previsão", "Realizado Dia", "Diferença", "Status", "Obs",
]

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
    height=min(50 + len(df_table) * 35, 500),
)

# ── Resumo mensal ─────────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>📊 Resumo por Mês</div>", unsafe_allow_html=True)

df_resumo = (
    df.groupby("MES")
    .agg(
        N_Registros=("DATA", "count"),
        Previsao=("PREVISAO", "sum"),
        Realizado=("REALIZADO", "sum"),
        Canceladas=("STATUS", lambda x: (x == "Cancelada").sum()),
        Adiadas=("STATUS", lambda x: (x == "Adiada").sum()),
        Destinos=("DESTINO_NORM", "nunique"),
    )
    .reset_index()
)
df_resumo["Aderência %"] = df_resumo.apply(
    lambda r: f"{r['Realizado']/r['Previsao']*100:.1f}%".replace(".", ",")
    if r["Previsao"] > 0 else "—", axis=1
)
df_resumo["Diferença"] = df_resumo["Realizado"] - df_resumo["Previsao"]
for col in ["Previsao", "Realizado", "Diferença"]:
    df_resumo[col] = df_resumo[col].apply(_fmt)

df_resumo.columns = [
    "Mês", "Registros", "Previsão Total", "Realizado Total",
    "Canceladas", "Adiadas", "Destinos Únicos", "Aderência %", "Diferença",
]
st.dataframe(df_resumo, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#4A5568;font-size:.82rem;'>"
    f"🚛 Previsão de Cargas · Zanattex &nbsp;|&nbsp; "
    f"Dados: {len(df_raw):,} registros carregados &nbsp;|&nbsp; "
    f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</div>",
    unsafe_allow_html=True,
)
