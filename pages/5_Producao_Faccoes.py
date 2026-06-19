"""Dashboard de Produção — Facções / Prestadores Externos."""

import os
import sys
from calendar import monthrange
from datetime import date, timedelta

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
from components.filtros_btn import render_filtros_btn

st.set_page_config(
    page_title="Produção Facções",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# Cores fixas para as facções "fixas". Os prestadores quarterizados (facções
# dinâmicas) recebem cores automáticas do Plotly — color_discrete_map só mapeia
# as categorias que casam e auto-atribui o restante.
CORES_FACCAO = {
    "ZANATTA":          "#4ECDC4",
    "GGTTEX RUTE":      "#45B7D1",
    "GGTTEX CORTINA":   "#5DA9E9",
    "PREVITTEX MATRIZ": "#FFA726",
    "MEGA BARIRI":      "#FF6B6B",
    "MEGA PREVEN":      "#AB47BC",
    "LITEX":            "#34D399",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _dias_uteis(year: int, month: int) -> int:
    _, n = monthrange(year, month)
    return sum(1 for d in range(1, n + 1) if date(year, month, d).weekday() < 5)


def _fmt(n: float | int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _pct_bar(pct: float) -> str:
    filled = min(int(pct / 5), 20)
    return "█" * filled + "░" * (20 - filled) + f"  {pct:.1f}%"


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
            "META_MES":    g["meta_mes"],
            "META_SEMANA": g["meta_semana"],
        })
    return pd.DataFrame(rows)


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

goals_df = _build_goals()
today = date.today()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗓 Período")
    mes_sel = st.selectbox("Mês", range(1, 13), index=today.month - 1,
                           format_func=lambda m: MESES_PT[m])
    ano_sel = st.number_input("Ano", min_value=2024, max_value=2030,
                              value=today.year, step=1)

    st.markdown("### 🔍 Filtros")
    faccoes_opts = sorted(df_all["FACCAO"].unique())
    faccoes_sel = st.multiselect("Facção", faccoes_opts,
                                 placeholder="Todas as facções")

    empresas_opts = sorted(df_all["CLIENTE"].unique())
    empresas_sel = st.multiselect("Empresa / Cliente", empresas_opts,
                                  placeholder="Todas as empresas")

    produtos_opts = sorted(df_all["PRODUTO"].unique())
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
# A facção NÃO entra no filtro de metas: ela é só o centro de custo (onde é
# faturado). O que conta para a meta é ONDE o produto é PRODUZIDO, e o mesmo
# produto+cliente pode ser produzido em várias facções ao mesmo tempo — todas
# somam para a mesma meta. Por isso o match é sempre por (PRODUTO, CLIENTE).
gf = goals_df.copy()
if empresas_sel:
    gf = gf[gf["CLIENTE"].isin([e.upper() for e in empresas_sel])]
if produtos_sel:
    gf = gf[gf["PRODUTO"].isin([p.upper() for p in produtos_sel])]

du_mes = _dias_uteis(ano_sel, mes_sel)
meta_mes_total  = int(gf["META_MES"].sum())
meta_sem_total  = int(gf["META_SEMANA"].sum())
meta_dia_total  = meta_mes_total / du_mes if du_mes > 0 else 0

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_mes, tab_dia, tab_sem, tab_prod, tab_fac = st.tabs([
    "📅 Mensal", "📆 Diário", "📊 Semanal", "📦 Por Produto", "🏭 Por Facção"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MENSAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_mes:
    df_mes = df[
        (df["DATA"].dt.year == ano_sel) & (df["DATA"].dt.month == mes_sel)
    ]
    total_mes = int(df_mes["QUANTIDADE"].sum())

    # Dias úteis passados no mês (até hoje ou até fim do mês)
    if ano_sel == today.year and mes_sel == today.month:
        dia_ref = today.day
    else:
        dia_ref = monthrange(ano_sel, mes_sel)[1]

    du_passados = sum(
        1 for d in range(1, dia_ref + 1)
        if date(ano_sel, mes_sel, d).weekday() < 5
    )
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
            title=f"Produção Diária — {MESES_PT[mes_sel]} {ano_sel}",
            xaxis_title="Dia",
            yaxis_title="Peças",
            **DARK_LAYOUT,
        )
        _d_ini = date(ano_sel, mes_sel, 1)
        _d_fim = daily["DATA"].max().date() if not daily.empty else _d_ini
        fig = apply_to_fig(fig, _d_ini, _d_fim, pagina="faccoes", x_fmt="%d/%m")
        st.plotly_chart(fig, use_container_width=True)

        # Acumulado vs meta (burn-up): produção acumulada × meta acumulada esperada
        daily_cum = daily.copy()
        daily_cum["ACUM"] = daily_cum["QUANTIDADE"].cumsum()
        daily_cum["DU_ACUM"] = [
            sum(1 for d in range(1, ts.day + 1)
                if date(ts.year, ts.month, d).weekday() < 5)
            for ts in daily_cum["DATA"]
        ]
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
    else:
        st.info(f"Sem produção registrada em {MESES_PT[mes_sel]}/{ano_sel}.")

    st.markdown("---")

    # Tabela de progresso por produto/empresa
    st.subheader("Progresso por Produto / Empresa")
    st.caption(
        "A meta é considerada onde o produto é **produzido**. Quando um produto é "
        "fabricado em mais de uma facção, todas somam para a mesma meta. "
        "A coluna *Produzido em* mostra as facções que contribuíram."
    )

    if not df_mes.empty:
        prod_grp = (
            df_mes.groupby(["PRODUTO_N", "CLIENTE_N"])
            .agg(
                QUANTIDADE=("QUANTIDADE", "sum"),
                FACCOES=("FACCAO", lambda s: ", ".join(sorted(s.unique()))),
            )
            .reset_index()
        )
    else:
        prod_grp = pd.DataFrame(
            columns=["PRODUTO_N", "CLIENTE_N", "QUANTIDADE", "FACCOES"]
        )

    # Match por (PRODUTO, CLIENTE) — soma a produção de TODAS as facções que
    # fabricaram o item (a facção é só centro de custo, não entra na chave).
    merged = gf.merge(
        prod_grp[["PRODUTO_N", "CLIENTE_N", "QUANTIDADE", "FACCOES"]],
        on=["PRODUTO_N", "CLIENTE_N"],
        how="left",
    )
    merged["QUANTIDADE"] = merged["QUANTIDADE"].fillna(0).astype(int)
    merged["FACCOES"] = merged["FACCOES"].fillna("—")
    merged["% Meta"] = (
        merged["QUANTIDADE"] / merged["META_MES"] * 100
    ).round(1).fillna(0)
    merged["Restante"] = (
        merged["META_MES"] - merged["QUANTIDADE"]
    ).clip(lower=0).astype(int)

    tabela = merged[
        ["PRODUTO", "CLIENTE", "FACCOES", "QUANTIDADE", "META_MES", "% Meta", "Restante"]
    ].copy()
    tabela.columns = ["Produto", "Empresa", "Produzido em", "Produzido", "Meta Mês", "% Meta", "Restante"]
    tabela = tabela.sort_values("% Meta", ascending=False).reset_index(drop=True)

    def _color_pct(val):
        try:
            v = float(val)
        except Exception:
            return ""
        if v >= 100:
            return "color: #4ECDC4; font-weight: bold"
        if v >= 75:
            return "color: #FFA726"
        return "color: #FF6B6B"

    st.dataframe(
        tabela.style
        .map(_color_pct, subset=["% Meta"])
        .format({
            "Produzido": "{:,.0f}",
            "Meta Mês":  "{:,.0f}",
            "% Meta":    "{:.1f}%",
            "Restante":  "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ── Botão Relatório PDF ──────────────────────────────────────────────────
    def _html_faccoes_mensal() -> bytes:
        from datetime import datetime as _dt
        agora = _dt.now().strftime("%d/%m/%Y %H:%M")
        mes_nome = MESES_PT.get(mes_sel, str(mes_sel))
        periodo_str = f"{mes_nome} / {ano_sel}"

        def _n(v) -> str:
            return f"{int(v):,}".replace(",", ".")

        def _tabela_rows() -> str:
            linhas = []
            for _, r in tabela.iterrows():
                pct = float(r["% Meta"])
                cls = "sok" if pct >= 100 else ("samb" if pct >= 75 else "serr")
                linhas.append(
                    f"<tr><td>{r['Produto']}</td><td>{r['Empresa']}</td>"
                    f"<td>{r['Produzido em']}</td>"
                    f"<td class='num'>{_n(r['Produzido'])}</td>"
                    f"<td class='num'>{_n(r['Meta Mês'])}</td>"
                    f"<td class='num {cls}'>{pct:.1f}%</td>"
                    f"<td class='num'>{_n(r['Restante'])}</td></tr>"
                )
            return "\n".join(linhas)

        tabela_html = _tabela_rows()
        cls_pct = "sok" if pct_mes >= 100 else ("samb" if pct_mes >= 75 else "serr")

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
            ".sec { font-size:11px; font-weight:700; color:#065F46; border-bottom:1px solid #4ECDC4; margin:14px 0 7px 0; padding-bottom:3px; }\n"
            "table { width:100%; border-collapse:collapse; margin-bottom:14px; font-size:9.5px; }\n"
            "th { background:#065F46; color:#fff; padding:4px 6px; text-align:left; font-size:8.5px; text-transform:uppercase; letter-spacing:.04em; }\n"
            "td { padding:3px 6px; border-bottom:1px solid #e5e7eb; }\n"
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
            "<div class='sec'>Progresso por Produto / Empresa</div>\n"
            "<table>\n"
            "  <thead><tr><th>Produto</th><th>Empresa</th><th>Produzido em</th>"
            "<th class='num'>Produzido</th><th class='num'>Meta M&ecirc;s</th>"
            "<th class='num'>% Meta</th><th class='num'>Restante</th></tr></thead>\n"
            f"  <tbody>{tabela_html}</tbody>\n"
            "</table>\n"
            "<div class='footer'>"
            f"Relatório Produção Facções &middot; {periodo_str} &middot; "
            f"Sistema Unificação dos Dados &middot; {agora}"
            "</div>\n</body>\n</html>"
        )
        return html.encode("utf-8")

    st.divider()
    _col_l_fac, _col_c_fac, _col_r_fac = st.columns([3, 2, 3])
    with _col_c_fac:
        st.download_button(
            label="📄 Gerar Relatório PDF",
            data=_html_faccoes_mensal(),
            file_name=f"relatorio_faccoes_{ano_sel}_{mes_sel:02d}.html",
            mime="text/html",
            use_container_width=True,
        )
    st.markdown(
        "<p style='text-align:center;color:#718096;font-size:.8rem;margin-top:4px'>"
        "Abre no navegador &rarr; <kbd>Ctrl+P</kbd> &rarr; Salvar como PDF</p>",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DIÁRIO
# ══════════════════════════════════════════════════════════════════════════════
with tab_dia:
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
                    df_dia.groupby(["FACCAO", "PRODUTO", "CLIENTE"])["QUANTIDADE"]
                    .sum()
                    .reset_index()
                    .sort_values("QUANTIDADE", ascending=False)
                )
                det.columns = ["Facção", "Produto", "Empresa", "Qtd"]
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SEMANAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_sem:
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

            daily_sem = (
                df_sem.groupby(["DATA", "PRODUTO"])["QUANTIDADE"]
                .sum()
                .reset_index()
            )
            daily_sem["DIA"] = daily_sem["DATA"].dt.day_name().map(
                lambda d: DIAS_PT.get(d, d)
            ) + " " + daily_sem["DATA"].dt.strftime("%d/%m")
            # Ordena dias cronologicamente
            ordem_dias = sorted(daily_sem["DATA"].unique())
            ordem_labels = [
                (DIAS_PT.get(pd.Timestamp(d).day_name(), "") + " " + pd.Timestamp(d).strftime("%d/%m"))
                for d in ordem_dias
            ]

            fig = px.bar(
                daily_sem,
                x="DIA",
                y="QUANTIDADE",
                color="PRODUTO",
                color_discrete_sequence=px.colors.qualitative.Set2,
                category_orders={"DIA": ordem_labels},
                labels={"QUANTIDADE": "Peças", "DIA": "Dia", "PRODUTO": "Produto"},
                title="Produção por Dia e Produto",
            )
            if meta_dia_sem > 0:
                fig.add_hline(
                    y=meta_dia_sem,
                    line_dash="dash",
                    line_color="#FF6B6B",
                    annotation_text=f"Meta/dia ({_fmt(round(meta_dia_sem))})",
                    annotation_position="top right",
                )
            fig.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

            # Resumo por produto + empresa + meta semanal.
            # Match por (PRODUTO, CLIENTE), somando todas as facções.
            prod_sem = (
                df_sem.groupby(["PRODUTO_N", "CLIENTE_N"])["QUANTIDADE"]
                .sum()
                .reset_index()
            )
            wk = gf.merge(prod_sem, on=["PRODUTO_N", "CLIENTE_N"], how="left")
            wk["QUANTIDADE"] = wk["QUANTIDADE"].fillna(0).astype(int)
            wk["% Meta"] = (
                wk["QUANTIDADE"] / wk["META_SEMANA"] * 100
            ).round(1).fillna(0)
            wk = wk.sort_values("% Meta", ascending=False)
            tab_wk = wk[["PRODUTO", "CLIENTE", "QUANTIDADE", "META_SEMANA", "% Meta"]].copy()
            tab_wk.columns = ["Produto", "Empresa", "Produzido", "Meta Semana", "% Meta"]

            st.dataframe(
                tab_wk.style
                .map(_color_pct, subset=["% Meta"])
                .format({
                    "Produzido":   "{:,.0f}",
                    "Meta Semana": "{:,.0f}",
                    "% Meta":      "{:.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — POR PRODUTO
# ══════════════════════════════════════════════════════════════════════════════
with tab_prod:
    df_mp = df[
        (df["DATA"].dt.year == ano_sel) & (df["DATA"].dt.month == mes_sel)
    ]

    if df_mp.empty:
        st.info(f"Sem dados em {MESES_PT[mes_sel]}/{ano_sel} para os filtros selecionados.")
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

        # Progresso vs meta por produto / empresa (barras coloridas por faixa)
        st.markdown("---")
        st.subheader("Atingimento da Meta por Produto")
        prod_grp_p = (
            df_mp.groupby(["PRODUTO_N", "CLIENTE_N"])["QUANTIDADE"].sum().reset_index()
        )
        mp = gf.merge(prod_grp_p, on=["PRODUTO_N", "CLIENTE_N"], how="left")
        mp["QUANTIDADE"] = mp["QUANTIDADE"].fillna(0).astype(int)
        mp = mp[mp["QUANTIDADE"] > 0].copy()
        if mp.empty:
            st.info("Nenhum produto com meta cadastrada produzido neste mês.")
        else:
            mp["PCT"] = (mp["QUANTIDADE"] / mp["META_MES"] * 100).round(1)
            mp["LABEL"] = mp["PRODUTO"] + " — " + mp["CLIENTE"]
            mp = mp.sort_values("PCT")
            cores = mp["PCT"].apply(
                lambda v: "#4ECDC4" if v >= 100 else "#FFA726" if v >= 75 else "#FF6B6B"
            )
            fig_prog = go.Figure()
            fig_prog.add_bar(
                x=mp["PCT"], y=mp["LABEL"], orientation="h",
                marker_color=cores,
                text=[f"{p:.0f}%" for p in mp["PCT"]], textposition="outside",
                hovertemplate="%{y}<br>%{x:.1f}% da meta mensal<extra></extra>",
            )
            fig_prog.add_vline(
                x=100, line_dash="dash", line_color="#FFFFFF",
                annotation_text="Meta", annotation_position="top",
            )
            fig_prog.update_layout(
                title="% da Meta Mensal por Produto / Empresa",
                xaxis_title="% da Meta", yaxis_title="",
                **DARK_LAYOUT,
            )
            st.plotly_chart(fig_prog, use_container_width=True)

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
with tab_fac:
    df_mes_fac = df[
        (df["DATA"].dt.year == ano_sel) & (df["DATA"].dt.month == mes_sel)
    ]

    if df_mes_fac.empty:
        st.info(f"Sem dados em {MESES_PT[mes_sel]}/{ano_sel} para os filtros selecionados.")
    else:
        # Produção por facção no mês
        fac_grp = (
            df_mes_fac.groupby("FACCAO")["QUANTIDADE"]
            .sum()
            .reset_index()
            .sort_values("QUANTIDADE", ascending=False)
        )

        col_pie, col_bar = st.columns(2)

        with col_pie:
            fig_pie = px.pie(
                fac_grp,
                names="FACCAO",
                values="QUANTIDADE",
                title=f"% por Facção — {MESES_PT[mes_sel]}",
                color="FACCAO",
                color_discrete_map=CORES_FACCAO,
                hole=0.4,
            )
            fig_pie.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            # Produção diária por facção (stacked)
            daily_fac = (
                df_mes_fac.groupby(["DATA", "FACCAO"])["QUANTIDADE"]
                .sum()
                .reset_index()
            )
            daily_fac["DATA_STR"] = daily_fac["DATA"].dt.strftime("%d/%m")
            fig_stk = px.bar(
                daily_fac,
                x="DATA_STR",
                y="QUANTIDADE",
                color="FACCAO",
                color_discrete_map=CORES_FACCAO,
                labels={"QUANTIDADE": "Peças", "DATA_STR": "Dia", "FACCAO": "Facção"},
                title="Produção Diária por Facção",
            )
            fig_stk.update_layout(**DARK_LAYOUT)
            st.plotly_chart(fig_stk, use_container_width=True)

        st.markdown("---")
        st.caption(
            "Aqui a facção representa **onde a peça é produzida**. As metas não são "
            "atribuídas a uma facção (um mesmo produto pode ser feito em várias ao "
            "mesmo tempo) — o acompanhamento de meta fica nas abas Mensal e Semanal."
        )

        # Produção total por facção (onde foi produzido)
        fac_tot = (
            df_mes_fac.groupby("FACCAO")["QUANTIDADE"].sum().reset_index()
            .sort_values("QUANTIDADE", ascending=False)
        )
        total_geral = int(fac_tot["QUANTIDADE"].sum())
        fac_tot["% do Total"] = (
            (fac_tot["QUANTIDADE"] / total_geral * 100).round(1)
            if total_geral > 0 else 0
        )
        fac_tot.columns = ["Facção", "Produzido", "% do Total"]

        st.dataframe(
            fac_tot.style.format({
                "Produzido":  "{:,.0f}",
                "% do Total": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Detalhe facção × produto × empresa
        st.markdown("**Detalhe por Facção / Produto / Empresa**")
        det_fac = (
            df_mes_fac.groupby(["FACCAO", "PRODUTO", "CLIENTE"])["QUANTIDADE"]
            .sum()
            .reset_index()
            .sort_values(["FACCAO", "QUANTIDADE"], ascending=[True, False])
        )
        det_fac.columns = ["Facção", "Produto", "Empresa", "Produzido"]
        st.dataframe(
            det_fac.style.format({"Produzido": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )
