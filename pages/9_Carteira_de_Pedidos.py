"""Dashboard de Carteira de Pedidos — análise de pedidos em aberto por cliente, produto e período."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from styles.global_ui import get_global_ui_css
from utils.pdf_report import gerar_pdf_carteira_pedidos
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button

# ── Configuração ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carteira de Pedidos | Zanattex",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

SHEET_ID  = "1U-iNIQRqKOIBrDZ86ZE5uJW6IQCzugJ7"
SHEET_GID = "611396912"
CACHE_TTL = 300

# ── Paleta ────────────────────────────────────────────────────────────────────
DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12),
    separators=",.",
    margin=dict(l=40, r=20, t=50, b=40),
)
_AXIS = dict(gridcolor="#2D3748", linecolor="#4A5568", zerolinecolor="#4A5568")

CORES_CAT = {
    "LENÇOL":             "#4ECDC4",
    "CORTINA":            "#FFA726",
    "COBERTOR":           "#45B7D1",
    "MANTA":              "#38BDF8",
    "COLCHA":             "#A78BFA",
    "FRONHA / ACESSÓRIOS":"#48BB78",
    "ALMOFADA":           "#F472B6",
    "TOALHA":             "#FC8181",
    "OUTROS":             "#718096",
}

MESES_PT_ABR = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#0F1117; }
[data-testid="stSidebar"]          { background:#1A1D2E; border-right:1px solid #2D3748; }

.pg-badge {
    display:inline-block; padding:5px 18px; border-radius:999px;
    font-size:.75rem; letter-spacing:.18em; text-transform:uppercase; font-weight:700;
    color:#4ECDC4; background:rgba(78,205,196,.10); border:1px solid rgba(78,205,196,.30);
    margin-bottom:14px;
}
.pg-title  { font-size:2.2rem; font-weight:900; color:#FFF; margin:0 0 4px 0; line-height:1.1; }
.pg-sub    { color:#718096; font-size:.95rem; margin-bottom:0; }
.accent    { color:#4ECDC4; }

.kpi-card  {
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
    border-radius:14px; padding:18px 20px; text-align:center;
}
.kpi-label { font-size:.75rem; color:#718096; text-transform:uppercase; letter-spacing:.12em; margin-bottom:6px; }
.kpi-value { font-size:1.65rem; font-weight:800; color:#FFF; line-height:1; margin-bottom:4px; }
.kpi-sub   { font-size:.82rem; color:#718096; }
.kpi-pos   { color:#48BB78; }
.kpi-neg   { color:#FC8181; }
.kpi-teal  { color:#4ECDC4; }

.sec-title {
    font-size:1rem; font-weight:700; color:#E2E8F0;
    margin:28px 0 12px 0; padding-bottom:6px;
    border-bottom:2px solid rgba(78,205,196,.3);
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return (unicodedata.normalize("NFD", str(s))
            .encode("ascii", "ignore").decode().upper().strip())


def _parse_float(s: str) -> float:
    try:
        # Remove qualquer símbolo não-numérico (R$, $, espaços, etc.)
        s = re.sub(r'[^\d,.\-]', '', str(s).strip())
        if not s:
            return 0.0
        if "," in s and "." in s:
            # Último separador define o tipo: vírgula depois → brasileiro 1.234,56
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                # US: 1,234.56 → remove vírgula de milhar
                s = s.replace(",", "")
        elif "," in s:
            # Só vírgula → decimal: 8,30 → 8.30
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0


def _parse_date(s: str) -> date | None:
    s = str(s).strip()
    try:
        parts = s.split("/")
        if len(parts) == 3:
            m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 100:
                y += 2000
            if 1900 < y < 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                return date(y, m, d)
    except Exception:
        pass
    return None


def _categorizar(desc: str) -> str:
    d = _norm(desc)
    # Lençol — nome completo, typos (LRNCOL), abreviações e jogos de cama
    if any(k in d for k in ["LENCOL", "LRNCOL", "JG CAMA", "JG LENCOL", "JOGO DE CAMA",
                             "JG KING", "JG QUEEN", "JG SOLT"]):
        return "LENÇOL"
    if re.match(r"^JC[A-Z0-9]*\s", d):   # JC, JCCD, JCD, JCKD, JCSS, JCCS, JCQD…
        return "LENÇOL"
    if re.match(r"^L[.\s]+\s*(CASAL|QUEEN|KING|SOLT|BERCE|BERCO|BABY)", d):
        return "LENÇOL"
    # Fronha / acessórios de cama
    if any(k in d for k in ["FRONHA", "PORTA TRAV", "SAIA BOX"]):
        return "FRONHA / ACESSÓRIOS"
    # Cortina — nome completo e abreviação CORT. em qualquer posição
    if "CORTINA" in d or re.search(r"CORT[.\s]", d):
        return "CORTINA"
    # Colcha
    if "COLCHA" in d:
        return "COLCHA"
    # Cobertor — nome completo, COBER (+ qualquer sufixo), COB. e COB<espaço>
    if "COBERTOR" in d or re.search(r"\bCOBER", d) or re.search(r"\bCOB[.\s]", d):
        return "COBERTOR"
    # Manta (mais leve — fleece, coral, shu velvet)
    if "MANTA" in d:
        return "MANTA"
    # Almofada / Toalha
    if "ALMOFADA" in d:
        return "ALMOFADA"
    if "TOALHA" in d:
        return "TOALHA"
    return "OUTROS"


def _tamanho(desc: str) -> str:
    d = _norm(desc)
    for t in ["KING", "QUEEN", "CASAL", "SOLTEIRO", "BABY", "BERCO"]:
        if t in d:
            return t
    return "N/I"


def _estado(municipio: str) -> str:
    m = re.search(r"-([A-Z]{2})$", str(municipio).strip())
    return m.group(1) if m else "N/I"


def _fmt_r(v: float) -> str:
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_n(v: float) -> str:
    return f"{int(v):,}".replace(",", ".")


def _layout(**kw) -> dict:
    out = {**DARK}
    xa = kw.pop("xaxis", {})
    ya = kw.pop("yaxis", {})
    out["xaxis"] = {**_AXIS, **xa}
    out["yaxis"] = {**_AXIS, **ya}
    out.update(kw)
    return out


# ── Loader ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_carteira() -> pd.DataFrame:
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&gid={SHEET_GID}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read().decode("utf-8", errors="replace")

    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return pd.DataFrame()

    records = []
    for row in rows[1:]:
        if len(row) < 11 or not row[0].strip():
            continue
        dt = _parse_date(row[0])
        if dt is None:
            continue
        qt  = _parse_float(row[8])
        vt  = _parse_float(row[10])
        vu  = _parse_float(row[9])
        if qt <= 0 and vt <= 0:
            continue
        desc = row[14].strip() if len(row) > 14 else ""
        dest = row[4].strip()
        mun  = row[5].strip() if len(row) > 5 else ""
        records.append({
            "DATA":        dt,
            "PEDIDO":      row[2].strip(),
            "NOTA":        row[1].strip(),
            "DESTINATARIO": dest,
            "MUNICIPIO":   mun,
            "ESTADO":      _estado(mun),
            "VENDEDOR":    row[7].strip() if len(row) > 7 else "",
            "QUANTIDADE":  qt,
            "VALOR_UNIT":  vu,
            "VALOR_TOTAL": vt,
            "COD_PROD":    row[12].strip() if len(row) > 12 else "",
            "DESCRICAO":   desc,
            "CATEGORIA":   _categorizar(desc),
            "TAMANHO":     _tamanho(desc),
        })

    df = pd.DataFrame(records)
    df["DATA"] = pd.to_datetime(df["DATA"])
    df["ANO"]  = df["DATA"].dt.year
    df["MES"]  = df["DATA"].dt.month
    df["ANO_MES"] = df["DATA"].dt.to_period("M").astype(str)
    df["MES_LABEL"] = df["DATA"].apply(
        lambda d: f"{MESES_PT_ABR[d.month]}/{str(d.year)[2:]}"
    )

    # Normalizar nomes de clientes (NC INDUSTRIA = NIAZITEX)
    _alias = {"NC INDUSTRIA E COMERCIO TEXTEIS LTDA": "NIAZITTEX",
               "NC INDUSTRIA E COMERCIO TEXTEIS": "NIAZITTEX"}
    df["CLIENTE"] = df["DESTINATARIO"].apply(
        lambda x: _alias.get(x.upper(), x)
    )
    # Nome curto do cliente
    def _nome_curto(n: str) -> str:
        n = n.upper()
        mapa = {
            "SULTAN": "SULTAN", "VESTIS": "VESTIS", "CAMESA": "CAMESA",
            "BURDAYS": "BURDAYS", "NC INDUSTRIA": "NIAZITTEX",
            "NIAZITTEX": "NIAZITTEX", "FATEX": "FATEX",
            "SEVEN": "SEVEN", "OLIVEIRA": "OLIVEIRA", "VIANELLI": "VIANELLI",
            "MARCELINO": "MARCELINO",
        }
        for k, v in mapa.items():
            if k in n:
                return v
        return n.split()[0][:12]

    df["CLIENTE_CURTO"] = df["CLIENTE"].apply(_nome_curto)
    return df


# ── Carregar ──────────────────────────────────────────────────────────────────
with st.spinner("⏳ Carregando carteira de pedidos…"):
    df_raw = load_carteira()

if df_raw.empty:
    st.error("❌ Nenhum dado disponível. Verifique o acesso à planilha.")
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
render_home_button()

with st.sidebar:
    st.markdown("## 📦 Filtros")
    st.caption(f"Atualizado a cada {CACHE_TTL}s · {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Atualizar Dados", key="refresh_cart", use_container_width=True):
        load_carteira.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**📅 Período**")
    anos_disp = sorted(df_raw["ANO"].unique())
    anos_sel  = st.multiselect("Ano", anos_disp, default=anos_disp, key="sel_ano_cart")
    if not anos_sel:
        anos_sel = anos_disp

    meses_disp = sorted(df_raw[df_raw["ANO"].isin(anos_sel)]["ANO_MES"].unique())
    meses_sel  = st.multiselect("Mês", meses_disp, placeholder="Todos", key="sel_mes_cart")

    st.markdown("**🏢 Cliente**")
    clientes_disp = sorted(df_raw["CLIENTE_CURTO"].unique())
    clientes_sel  = st.multiselect("Cliente", clientes_disp, placeholder="Todos", key="sel_cli_cart")

    st.markdown("**📦 Categoria**")
    cats_disp = sorted(df_raw["CATEGORIA"].unique())
    cats_sel  = st.multiselect("Categoria", cats_disp, placeholder="Todas", key="sel_cat_cart")

    st.markdown("**📐 Tamanho**")
    tam_disp = sorted(t for t in df_raw["TAMANHO"].unique() if t != "N/I")
    tam_sel  = st.multiselect("Tamanho", tam_disp, placeholder="Todos", key="sel_tam_cart")

    st.markdown("**🗺 Estado**")
    estados_disp = sorted(e for e in df_raw["ESTADO"].unique() if e != "N/I")
    estados_sel  = st.multiselect("Estado", estados_disp, placeholder="Todos", key="sel_est_cart")

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df = df_raw[df_raw["ANO"].isin(anos_sel)].copy()
if meses_sel:
    df = df[df["ANO_MES"].isin(meses_sel)]
if clientes_sel:
    df = df[df["CLIENTE_CURTO"].isin(clientes_sel)]
if cats_sel:
    df = df[df["CATEGORIA"].isin(cats_sel)]
if tam_sel:
    df = df[df["TAMANHO"].isin(tam_sel)]
if estados_sel:
    df = df[df["ESTADO"].isin(estados_sel)]

if df.empty:
    st.warning("⚠️ Nenhum registro com os filtros selecionados.")
    st.stop()

render_filtros_btn()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center'><span class='pg-badge'>📦 Comercial · Zanattex</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h1 class='pg-title' style='text-align:center'>Dashboard de <span class='accent'>Carteira de Pedidos</span></h1>"
    "<p class='pg-sub' style='text-align:center'>Análise de pedidos por cliente, produto, período e região</p>",
    unsafe_allow_html=True,
)

st.warning(
    "⚠️ **OBS — Sultan:** A carteira da Sultan está poluída com pedidos antigos/duplicados "
    "que ainda não foram baixados do sistema. Por isso, os volumes exibidos para esse cliente "
    "estão inflados e não refletem a carteira real em aberto.",
    icon=None,
)

st.divider()

# ── KPIs globais ──────────────────────────────────────────────────────────────
total_valor   = df["VALOR_TOTAL"].sum()
total_pecas   = int(df["QUANTIDADE"].sum())
n_pedidos     = df["PEDIDO"].nunique()
n_clientes    = df["CLIENTE_CURTO"].nunique()
n_produtos    = df["COD_PROD"].nunique()
ticket_medio  = total_valor / n_pedidos if n_pedidos > 0 else 0  # usado no PDF
valor_medio_p = total_valor / total_pecas if total_pecas > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
_kpis = [
    (c1, "💰 Valor Total",     _fmt_r(total_valor),       f"{n_pedidos} pedidos",    "teal"),
    (c2, "📦 Total de Peças",  _fmt_n(total_pecas),        "unidades",               "teal"),
    (c3, "🛒 Pedidos Únicos",  _fmt_n(n_pedidos),          "",                       "teal"),
    (c4, "🏢 Clientes Ativos", str(n_clientes),            "",                       "teal"),
    (c5, "🏷 Produtos Únicos", _fmt_n(n_produtos),         f"{len(df['CATEGORIA'].unique())} categorias", "teal"),
]
for col, label, value, sub, color in _kpis:
    with col:
        sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value kpi-{color}'>{value}</div>"
            f"{sub_html}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Linha 1: Evolução mensal + Distribuição por categoria ─────────────────────
st.markdown("<div class='sec-title'>📈 Evolução Mensal da Carteira</div>", unsafe_allow_html=True)

df_mes = (
    df.groupby("ANO_MES")
    .agg(VALOR=("VALOR_TOTAL", "sum"), PECAS=("QUANTIDADE", "sum"),
         PEDIDOS=("PEDIDO", "nunique"))
    .reset_index()
    .sort_values("ANO_MES")
)
df_mes["MES_LABEL"] = df_mes["ANO_MES"].apply(
    lambda s: f"{MESES_PT_ABR[int(s.split('-')[1])]}/{s.split('-')[0][2:]}"
)

col_g1, col_g2 = st.columns([2, 1])
with col_g1:
    df_mes["VALOR_ACUM"] = df_mes["VALOR"].cumsum()

    fig_ev = go.Figure()
    fig_ev.add_bar(
        x=df_mes["MES_LABEL"], y=df_mes["VALOR"],
        name="Valor Mensal", marker_color="#4ECDC4",
        text=[_fmt_r(v) for v in df_mes["VALOR"]],
        textposition="outside", textfont=dict(size=9),
    )
    fig_ev.add_scatter(
        x=df_mes["MES_LABEL"], y=df_mes["VALOR_ACUM"],
        name="Acumulado (R$)", mode="lines+markers",
        line=dict(color="#A78BFA", width=2.5, dash="dot"),
        marker=dict(size=7, color="#A78BFA"),
        customdata=[[_fmt_r(v)] for v in df_mes["VALOR_ACUM"]],
        hovertemplate="<b>Acumulado</b><br>%{customdata[0]}<extra></extra>",
    )
    fig_ev.add_scatter(
        x=df_mes["MES_LABEL"], y=df_mes["PECAS"],
        name="Peças", mode="lines+markers",
        yaxis="y2", line=dict(color="#FFA726", width=2.5),
        marker=dict(size=7, color="#FFA726"),
    )
    fig_ev.update_layout(
        **_layout(
            height=360, barmode="group",
            title="Valor e Volume de Pedidos por Mês",
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            yaxis=dict(tickprefix="R$ ", separatethousands=True),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title="Peças", tickformat=","),
        )
    )
    st.plotly_chart(fig_ev, use_container_width=True)

with col_g2:
    df_cat_pie = (
        df.groupby("CATEGORIA")["VALOR_TOTAL"].sum()
        .reset_index().sort_values("VALOR_TOTAL", ascending=False)
    )
    cores_pie = [CORES_CAT.get(c, "#718096") for c in df_cat_pie["CATEGORIA"]]

    # Para OUTROS: montar texto com os produtos que engloba
    _outros_detalhe = (
        df[df["CATEGORIA"] == "OUTROS"]
        .groupby("DESCRICAO")["VALOR_TOTAL"].sum()
        .sort_values(ascending=False)
        .head(8)
    )
    _outros_txt = "<br>".join(
        f"• {d[:40]}: {_fmt_r(v)}"
        for d, v in _outros_detalhe.items()
    ) if not _outros_detalhe.empty else ""

    # customdata: texto extra por fatia (vazio para as demais)
    _custom = []
    for cat in df_cat_pie["CATEGORIA"]:
        _custom.append(_outros_txt if cat == "OUTROS" else "")

    fig_cat = go.Figure(go.Pie(
        labels=df_cat_pie["CATEGORIA"],
        values=df_cat_pie["VALOR_TOTAL"],
        hole=0.52,
        textinfo="label+percent",
        marker=dict(colors=cores_pie),
        customdata=_custom,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Valor: R$ %{value:,.0f}<br>"
            "%{percent}<br>"
            "%{customdata}"
            "<extra></extra>"
        ),
    ))
    fig_cat.update_layout(
        **{**DARK, "margin": dict(l=10, r=10, t=50, b=10)},
        height=340,
        title="Carteira por Categoria",
        annotations=[dict(text="Categoria", x=.5, y=.5,
                          font=dict(size=10, color="#CBD5E0"), showarrow=False)],
        legend=dict(orientation="v", x=1.02, y=0.5),
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ── Linha 2: Top Clientes + Por Estado ───────────────────────────────────────
st.markdown("<div class='sec-title'>🏢 Análise por Cliente e Região</div>", unsafe_allow_html=True)
col_g3, col_g4 = st.columns(2)

with col_g3:
    df_cli = (
        df.groupby("CLIENTE_CURTO")
        .agg(VALOR=("VALOR_TOTAL", "sum"), PECAS=("QUANTIDADE", "sum"),
             PEDIDOS=("PEDIDO", "nunique"))
        .reset_index()
        .sort_values("VALOR", ascending=True)
    )
    fig_cli = go.Figure()
    fig_cli.add_bar(
        y=df_cli["CLIENTE_CURTO"], x=df_cli["VALOR"],
        orientation="h", marker_color="#4ECDC4",
        text=[_fmt_r(v) for v in df_cli["VALOR"]],
        textposition="outside", textfont=dict(size=9),
        name="Valor",
    )
    fig_cli.update_layout(
        **_layout(
            height=320, title="Valor Total por Cliente",
            xaxis=dict(tickprefix="R$ ", separatethousands=True),
        )
    )
    st.plotly_chart(fig_cli, use_container_width=True)

with col_g4:
    df_est = (
        df[df["ESTADO"] != "N/I"]
        .groupby("ESTADO")
        .agg(VALOR=("VALOR_TOTAL", "sum"), PECAS=("QUANTIDADE", "sum"))
        .reset_index()
        .sort_values("VALOR", ascending=False)
    )
    fig_est = go.Figure(go.Bar(
        x=df_est["ESTADO"], y=df_est["VALOR"],
        marker_color="#45B7D1",
        text=[_fmt_r(v) for v in df_est["VALOR"]],
        textposition="outside", textfont=dict(size=9),
    ))
    fig_est.update_layout(
        **_layout(
            height=320, title="Valor por Estado",
            yaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_est, use_container_width=True)

# ── Linha 3: Categorias por cliente (stacked) + Top produtos ─────────────────
st.markdown("<div class='sec-title'>📦 Mix de Produtos</div>", unsafe_allow_html=True)
col_g5, col_g6 = st.columns(2)

with col_g5:
    df_cc = (
        df.groupby(["CLIENTE_CURTO", "CATEGORIA"])["VALOR_TOTAL"]
        .sum().reset_index()
    )
    fig_cc = px.bar(
        df_cc, x="CLIENTE_CURTO", y="VALOR_TOTAL", color="CATEGORIA",
        color_discrete_map=CORES_CAT,
        title="Composição por Cliente × Categoria",
        labels={"VALOR_TOTAL": "Valor (R$)", "CLIENTE_CURTO": "Cliente",
                "CATEGORIA": "Categoria"},
        barmode="stack",
    )
    fig_cc.update_layout(
        **DARK, height=340,
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        yaxis=dict(**_AXIS, tickprefix="R$ "),
        xaxis=dict(**_AXIS),
    )
    fig_cc.update_traces(textfont_size=9)
    st.plotly_chart(fig_cc, use_container_width=True)

with col_g6:
    df_tam = (
        df[df["TAMANHO"] != "N/I"]
        .groupby("TAMANHO")
        .agg(VALOR=("VALOR_TOTAL", "sum"), PECAS=("QUANTIDADE", "sum"))
        .reset_index()
        .sort_values("PECAS", ascending=False)
    )
    _cores_tam = ["#4ECDC4", "#FFA726", "#45B7D1", "#A78BFA", "#48BB78", "#FC8181"]
    fig_tam = go.Figure()
    fig_tam.add_bar(
        x=df_tam["TAMANHO"], y=df_tam["PECAS"],
        marker_color=_cores_tam[:len(df_tam)],
        text=[_fmt_n(v) for v in df_tam["PECAS"]],
        textposition="outside", textfont=dict(size=10),
        name="Peças",
    )
    fig_tam.add_scatter(
        x=df_tam["TAMANHO"], y=df_tam["VALOR"],
        mode="markers", yaxis="y2", name="Valor (R$)",
        marker=dict(size=14, color="#FFA726", symbol="diamond"),
    )
    fig_tam.update_layout(
        **_layout(
            height=340,
            title="Volume e Valor por Tamanho",
            yaxis=dict(title="Peças"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title="Valor R$", tickprefix="R$ "),
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        )
    )
    st.plotly_chart(fig_tam, use_container_width=True)

# ── Linha 4: Evolução por categoria + Mapa de calor cliente × mês ─────────────
st.markdown("<div class='sec-title'>📊 Tendências e Concentração</div>", unsafe_allow_html=True)
col_g7, col_g8 = st.columns(2)

with col_g7:
    df_ev_cat = (
        df.groupby(["ANO_MES", "CATEGORIA"])["VALOR_TOTAL"]
        .sum().reset_index().sort_values("ANO_MES")
    )
    df_ev_cat["MES_LABEL"] = df_ev_cat["ANO_MES"].apply(
        lambda s: f"{MESES_PT_ABR[int(s.split('-')[1])]}/{s.split('-')[0][2:]}"
    )
    fig_ev_cat = px.area(
        df_ev_cat, x="MES_LABEL", y="VALOR_TOTAL", color="CATEGORIA",
        color_discrete_map=CORES_CAT,
        title="Evolução do Valor por Categoria",
        labels={"VALOR_TOTAL": "Valor (R$)", "MES_LABEL": "Mês", "CATEGORIA": ""},
    )
    fig_ev_cat.update_layout(
        **DARK, height=340,
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        yaxis=dict(**_AXIS, tickprefix="R$ "),
        xaxis=dict(**_AXIS),
    )
    st.plotly_chart(fig_ev_cat, use_container_width=True)

with col_g8:
    pivot_hm = df.pivot_table(
        index="CLIENTE_CURTO", columns="ANO_MES",
        values="VALOR_TOTAL", aggfunc="sum", fill_value=0,
    )
    pivot_hm = pivot_hm[sorted(pivot_hm.columns)]
    mes_labels_hm = [
        f"{MESES_PT_ABR[int(c.split('-')[1])]}/{c.split('-')[0][2:]}"
        for c in pivot_hm.columns
    ]
    fig_hm = go.Figure(go.Heatmap(
        z=pivot_hm.values,
        x=mes_labels_hm,
        y=pivot_hm.index.tolist(),
        colorscale=[[0, "rgba(30,40,60,.3)"], [0.4, "#1A3A5C"],
                    [0.7, "#2AA89A"], [1, "#4ECDC4"]],
        hovertemplate="%{y}<br>%{x}<br>R$ %{z:,.0f}<extra></extra>",
        colorbar=dict(title="R$", tickprefix="R$ "),
        text=[[f"R$ {v/1000:.0f}k" if v > 0 else "" for v in row]
              for row in pivot_hm.values],
        texttemplate="%{text}",
        textfont=dict(size=8),
    ))
    fig_hm.update_layout(**DARK, height=340,
                         title="Mapa de Calor: Cliente × Mês (R$)",
                         xaxis=dict(**_AXIS), yaxis=dict(**_AXIS))
    st.plotly_chart(fig_hm, use_container_width=True)

# ── Ranking de produtos ───────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>🏆 Top Produtos da Carteira</div>", unsafe_allow_html=True)

df_top_prod = (
    df.groupby("DESCRICAO")
    .agg(VALOR=("VALOR_TOTAL", "sum"), PECAS=("QUANTIDADE", "sum"),
         CLIENTES=("CLIENTE_CURTO", "nunique"))
    .reset_index()
    .sort_values("VALOR", ascending=True)
    .tail(15)
)
fig_top = go.Figure(go.Bar(
    y=df_top_prod["DESCRICAO"].str[:55],
    x=df_top_prod["VALOR"],
    orientation="h",
    marker=dict(
        color=df_top_prod["PECAS"],
        colorscale=[[0, "#1A3A5C"], [0.5, "#2AA89A"], [1, "#4ECDC4"]],
        showscale=True,
        colorbar=dict(title="Peças", x=1.02),
    ),
    text=[_fmt_r(v) for v in df_top_prod["VALOR"]],
    textposition="outside", textfont=dict(size=9),
    customdata=df_top_prod[["PECAS", "CLIENTES"]].values,
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Valor: R$ %{x:,.0f}<br>"
        "Peças: %{customdata[0]:,.0f}<br>"
        "Clientes: %{customdata[1]}<extra></extra>"
    ),
))
fig_top.update_layout(
    **_layout(
        height=480,
        title="Top 15 Produtos — Valor Total (cor = volume de peças)",
        xaxis=dict(tickprefix="R$ "),
    )
)
st.plotly_chart(fig_top, use_container_width=True)

# ── Tabela de Resumo por Cliente ─────────────────────────────────────────────
st.markdown("<div class='sec-title'>📋 Resumo por Cliente</div>", unsafe_allow_html=True)

st.warning(
    "⚠️ **OBS — Sultan:** A carteira da Sultan está poluída com pedidos antigos/duplicados "
    "que ainda não foram baixados do sistema. Por isso, os volumes exibidos para esse cliente "
    "estão inflados e não refletem a carteira real em aberto.",
    icon=None,
)

df_resumo_cli = (
    df.groupby(["CLIENTE_CURTO", "ESTADO"])
    .agg(
        Pedidos=("PEDIDO", "nunique"),
        Peças=("QUANTIDADE", "sum"),
        Valor=("VALOR_TOTAL", "sum"),
        Produtos=("COD_PROD", "nunique"),
        Categorias=("CATEGORIA", lambda x: ", ".join(sorted(x.unique()))),
    )
    .reset_index()
    .sort_values("Valor", ascending=False)
)
df_resumo_cli["% Carteira"] = (df_resumo_cli["Valor"] / total_valor * 100).round(1)

df_show_cli = df_resumo_cli.copy()
df_show_cli["Peças"]      = df_show_cli["Peças"].apply(_fmt_n)
df_show_cli["Valor"]      = df_show_cli["Valor"].apply(_fmt_r)
df_show_cli["% Carteira"] = df_show_cli["% Carteira"].apply(lambda v: f"{v:.1f}%")
df_show_cli.columns = ["Cliente", "Estado", "Pedidos", "Peças", "Valor Total",
                        "Produtos", "Categorias", "% Carteira"]
st.dataframe(df_show_cli, use_container_width=True, hide_index=True)

# ── Tabela de Detalhes ────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>🔍 Detalhe de Itens</div>", unsafe_allow_html=True)

col_tb1, col_tb2 = st.columns([3, 1])
with col_tb2:
    busca = st.text_input("🔍 Buscar produto / cliente", "", key="busca_cart",
                          placeholder="ex: CORTINA")

df_det = df.copy()
if busca.strip():
    mask = (
        df_det["DESCRICAO"].str.upper().str.contains(busca.upper(), na=False) |
        df_det["CLIENTE_CURTO"].str.upper().str.contains(busca.upper(), na=False)
    )
    df_det = df_det[mask]

df_table = df_det[[
    "DATA", "PEDIDO", "CLIENTE_CURTO", "MUNICIPIO", "CATEGORIA",
    "DESCRICAO", "TAMANHO", "QUANTIDADE", "VALOR_UNIT", "VALOR_TOTAL",
]].copy()
df_table["DATA"]        = df_table["DATA"].dt.strftime("%d/%m/%Y")
df_table["QUANTIDADE"]  = df_table["QUANTIDADE"].apply(_fmt_n)
df_table["VALOR_UNIT"]  = df_table["VALOR_UNIT"].apply(lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X","."))
df_table["VALOR_TOTAL"] = df_table["VALOR_TOTAL"].apply(_fmt_r)
df_table.columns = ["Data", "Pedido", "Cliente", "Município", "Categoria",
                    "Descrição", "Tamanho", "Qtd", "Vl. Unit.", "Vl. Total"]

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
    height=min(50 + len(df_table) * 35, 500),
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#4A5568;font-size:.82rem;'>"
    f"📦 Carteira de Pedidos · Zanattex &nbsp;|&nbsp; "
    f"{len(df_raw):,} itens carregados &nbsp;|&nbsp; "
    f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</div>",
    unsafe_allow_html=True,
)
