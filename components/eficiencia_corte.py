"""
Componente de Eficiência de Corte — Dashboard Unificado
Abas: Manta Arealva (Zanattex), Lençol, GIattex
"""

import streamlit as st
import pandas as pd
import logging
import plotly.express as px
import plotly.graph_objects as go
import io
import urllib.request
from urllib.error import HTTPError, URLError
import numpy as np

# CONFIG

EFICIENCIA_MANTA_AREALVA_ID  = "17ido41trF22ks7HgoJz9XHcJU0oA4SYK"
EFICIENCIA_MANTA_AREALVA_GID = "874592526"

EFICIENCIA_LENCOL_AREALVA_ID  = "1Wd0C-Sb23mQWAUX01UfpcqVMhIVRVe6H"
EFICIENCIA_LENCOL_AREALVA_GID = "2055485890"

EFICIENCIA_GIATTEX_ID  = "1XaBhH1vCqI-xKXO3-B5kI-_mCNYk_Sp5"
EFICIENCIA_GIATTEX_GID = "0"

EFICIENCIA_CACHE_TTL = 300

# tema
_ACCENT   = "#6366F1"
_GREEN    = "#22C55E"
_YELLOW   = "#F59E0B"
_RED      = "#EF4444"
_PLOT_BG  = "rgba(0,0,0,0)"
_FONT     = dict(color="#E2E8F0", size=11)

# HELPERS

def _fetch(sheet_id: str, gid: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode("utf-8")
                if txt.strip():
                    return txt
        except (HTTPError, URLError, TimeoutError) as e:
            logging.debug(f"fetch {sheet_id[:20]}: {e}")
    raise RuntimeError(f"Não foi possível baixar a planilha {sheet_id}")

def _detect_header(texto: str, marcadores: list[str]) -> int:
    """Retorna índice da linha que contém os cabeçalhos reais."""
    for i, linha in enumerate(texto.splitlines()[:15]):
        lu = linha.upper()
        if any(m.upper() in lu for m in marcadores):
            return i
    return 0

def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.strip()
              .str.replace(".", "", regex=False)
              .str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0)

def _col(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    """Retorna o primeiro nome de coluna encontrado (case-insensitive)."""
    mapa = {c.upper().strip(): c for c in df.columns}
    for c in candidatos:
        found = mapa.get(c.upper().strip())
        if found:
            return found
    return None

def _kpi(col, label: str, valor: str, delta: str = "", color: str = "#E2E8F0"):
    col.markdown(f"""
    <div style="background:rgba(99,102,241,.09);border:1px solid rgba(99,102,241,.25);
                border-radius:10px;padding:14px 16px;text-align:center;">
        <div style="font-size:.7rem;color:#94A3B8;font-weight:600;
                    text-transform:uppercase;letter-spacing:.05em;">{label}</div>
        <div style="font-size:1.5rem;font-weight:700;color:{color};margin:4px 0;">{valor}</div>
        {"<div style='font-size:.75rem;color:#64748B;'>"+delta+"</div>" if delta else ""}
    </div>""", unsafe_allow_html=True)

def _plot_cfg():
    return dict(
        plot_bgcolor=_PLOT_BG, paper_bgcolor=_PLOT_BG,
        font=_FONT, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )

# CARREGAMENTO — Manta Arealva

@st.cache_data(ttl=EFICIENCIA_CACHE_TTL, show_spinner=False)
def carregar_manta_arealva() -> pd.DataFrame:
    texto = _fetch(EFICIENCIA_MANTA_AREALVA_ID, EFICIENCIA_MANTA_AREALVA_GID)
    skip  = _detect_header(texto, ["NUM OP", "PRODUTO", "TOTAL CORTE", "KGS CORTADOS"])
    df    = pd.read_csv(io.StringIO(texto), skiprows=skip, header=0, dtype=str)
    df.columns = df.columns.str.strip()
    df = df.drop(columns=[c for c in df.columns if "Unnamed" in c or not c.strip()], errors="ignore")

    for col in ["PRODUTO", "TAMANHO", "PRODUTOR", "NUM OP"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    # Numéricos — usa nomes exatos da planilha
    num_cols = [
        "QTDE PREV (Peças)", "QTDE PREV (Kgs)", "MEDIA GRAMATURA",
        "TOTAL CORTE", "KGS CORTADOS", "RETALHOS (Kg)", "BABYS (Peças)",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = _num(df[col])
        else:
            df[col] = 0.0

    # KGS FINAL — usa da planilha se existir, senão recalcula
    kgs_final_col = _col(df, ["KGS FINAL"])
    if kgs_final_col:
        df["KGS FINAL"] = _num(df[kgs_final_col])
    else:
        df["KGS FINAL"] = (
            df["TOTAL CORTE"] * df["MEDIA GRAMATURA"]
            + df["RETALHOS (Kg)"]
            + df["BABYS (Peças)"] * 0.1955
        ).round(3)

    # DIVERGÊNCIA — usa da planilha se existir, senão recalcula
    div_col = _col(df, ["!DIVERGENCIA! (KG)", "DIVERGENCIA", "DIVERGÊNCIA"])
    if div_col:
        df["DIVERGENCIA (Kg)"] = _num(df[div_col])
    else:
        df["DIVERGENCIA (Kg)"] = (df["KGS CORTADOS"] - df["KGS FINAL"]).round(3)

    # APROVEITAMENTO — usa da planilha se existir (KGS FINAL / KGS CORTADOS)
    aprov_col = _col(df, ["APROVEITAMENTO (%)", "APROVEITAMENTO"])
    if aprov_col:
        raw = df[aprov_col].astype(str).str.replace("%", "").str.strip()
        df["APROVEITAMENTO_%"] = pd.to_numeric(
            raw.str.replace(",", "."), errors="coerce"
        ).round(1)
    else:
        df["APROVEITAMENTO_%"] = (
            df["KGS FINAL"] / df["KGS CORTADOS"].replace(0, np.nan) * 100
        ).round(1)

    # Invalida aproveitamento onde KGS CORTADOS = 0 (OP não iniciada)
    df.loc[df["KGS CORTADOS"] == 0, "APROVEITAMENTO_%"] = np.nan

    # Conclusão da OP em peças (apenas para referência)
    df["CONCLUSAO_%"] = (
        df["TOTAL CORTE"] / df["QTDE PREV (Peças)"].replace(0, np.nan) * 100
    ).fillna(0).round(1)

    # Breakdown em KG
    df["PECAS_BOAS_KG"] = (df["TOTAL CORTE"] * df["MEDIA GRAMATURA"]).round(3)
    df["BABYS_KG"]      = (df["BABYS (Peças)"] * 0.1955).round(3)

    if "DATA INICIO" in df.columns:
        df["DATA INICIO"] = pd.to_datetime(df["DATA INICIO"], errors="coerce")

    invalidos = {"", "NAN", "NONE", "N/A"}
    df = df[~df["NUM OP"].astype(str).str.upper().str.strip().isin(invalidos)].reset_index(drop=True)
    return df

# CARREGAMENTO — Lençol Arealva

@st.cache_data(ttl=EFICIENCIA_CACHE_TTL, show_spinner=False)
def carregar_lencol_arealva() -> pd.DataFrame:
    texto = _fetch(EFICIENCIA_LENCOL_AREALVA_ID, EFICIENCIA_LENCOL_AREALVA_GID)
    skip  = _detect_header(texto, ["O.P.", "CLIENTE", "PRODUTO", "QUANTIDADE"])
    df    = pd.read_csv(io.StringIO(texto), skiprows=skip, header=0, dtype=str)
    df.columns = df.columns.str.strip()
    df = df.drop(columns=[c for c in df.columns if "Unnamed" in c or not c.strip()], errors="ignore")

    # Resolve colunas pelos nomes exatos da planilha (case-insensitive)
    op_col       = _col(df, ["O.P.", "OP", "NUM OP"])
    cli_col      = _col(df, ["CLIENTE"])
    prod_col     = _col(df, ["PRODUTO"])
    tec_col      = _col(df, ["TECIDO"])
    tipo_col     = _col(df, ["TIPO"])
    tam_col      = _col(df, ["TAMANHO"])
    stat_col     = _col(df, ["STATUS"])
    prog_col     = _col(df, ["QUANTIDADE PROGRAMADA(PÇS)", "QUANTIDADE PROGRAMADA (PÇS)",
                              "QNT PROG", "PROGRAMADO", "QTDE PREV"])
    cort_col     = _col(df, ["QUANTIDADE CORTADA(PÇS)", "QUANTIDADE CORTADA (PÇS)",
                              "QNT CORTADA", "CORTADO"])
    mts_esp_col  = _col(df, ["METROS ESPERADOS(MTS)", "METROS ESPERADOS (MTS)", "MTS ESPERADOS"])
    mts_cort_col = _col(df, ["METROS CORTADOS(MTS)", "METROS CORTADOS (MTS)", "MTS CORTADOS"])
    dif_col      = _col(df, ["DIFERENÇA (MTS)", "DIFERENCA (MTS)", "DIFERENÇA", "DIFERENCA"])
    perda_col    = _col(df, ["PERDA (%)", "PERDA"])
    ret_col      = _col(df, ["RETALHO (KG)", "RETALHO (KG)", "RETALHO"])
    aprov_col    = _col(df, ["APROVEITAMENTO", "APROV"])

    col_map = {
        op_col: "OP", cli_col: "CLIENTE", prod_col: "PRODUTO",
        tec_col: "TECIDO", tipo_col: "TIPO", tam_col: "TAMANHO", stat_col: "STATUS",
        prog_col: "QTD_PROG", cort_col: "QTD_CORT",
        mts_esp_col: "MTS_ESP", mts_cort_col: "MTS_CORT",
        dif_col: "DIFERENCA_MTS", perda_col: "PERDA_%",
        ret_col: "RETALHO_KG", aprov_col: "APROV_RAW",
    }
    renames = {orig: dest for orig, dest in col_map.items()
               if orig and orig in df.columns and orig != dest}
    if renames:
        df = df.rename(columns=renames)

    for col in ["OP", "CLIENTE", "PRODUTO", "TECIDO", "TIPO", "TAMANHO", "STATUS"]:
        df[col] = df[col].astype(str).str.strip() if col in df.columns else ""

    for col in ["QTD_PROG", "QTD_CORT", "MTS_ESP", "MTS_CORT", "RETALHO_KG"]:
        df[col] = _num(df[col]) if col in df.columns else 0.0

    # Aproveitamento % — usa da planilha se disponível
    if "APROV_RAW" in df.columns:
        df["APROVEITAMENTO_%"] = _num(
            df["APROV_RAW"].astype(str).str.strip().str.replace("%", "", regex=False)
        ).round(1)
    else:
        df["APROVEITAMENTO_%"] = (
            df["MTS_CORT"] / df["MTS_ESP"].replace(0, np.nan) * 100
        ).round(1)
    df.loc[df["MTS_CORT"] == 0, "APROVEITAMENTO_%"] = np.nan

    # Perda %
    if "PERDA_%" in df.columns:
        df["PERDA_%"] = _num(
            df["PERDA_%"].astype(str).str.strip().str.replace("%", "", regex=False)
        ).round(1)
    else:
        df["PERDA_%"] = 0.0

    # Diferença (MTs): da planilha ou recalculada (cortado - esperado)
    if "DIFERENCA_MTS" in df.columns:
        df["DIFERENCA_MTS"] = _num(df["DIFERENCA_MTS"]).round(1)
    else:
        df["DIFERENCA_MTS"] = (df["MTS_CORT"] - df["MTS_ESP"]).round(1)

    # Conclusão OP em peças
    df["CONCLUSAO_%"] = (
        df["QTD_CORT"] / df["QTD_PROG"].replace(0, np.nan) * 100
    ).fillna(0).round(1)

    invalidos = {"", "NAN", "NONE", "N/A"}
    df = df[~df["OP"].astype(str).str.upper().str.strip().isin(invalidos)]

    # Remove linhas sem nenhum dado relevante (linhas vazias do fim da planilha)
    tem_dado = (
        (df["QTD_PROG"] > 0) |
        (df["QTD_CORT"] > 0) |
        (df["MTS_ESP"]  > 0) |
        (df["MTS_CORT"] > 0)
    )
    df = df[tem_dado].reset_index(drop=True)
    return df

# CARREGAMENTO — GIattex

@st.cache_data(ttl=EFICIENCIA_CACHE_TTL, show_spinner=False)
def carregar_giattex() -> pd.DataFrame:
    try:
        texto = _fetch(EFICIENCIA_GIATTEX_ID, EFICIENCIA_GIATTEX_GID)
        df    = pd.read_csv(io.StringIO(texto), dtype=str)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        logging.warning(f"GIattex: {e}")
        return pd.DataFrame()

# RENDER PRINCIPAL

def render_dashboard_eficiencia():
    st.markdown("""
    <div style="text-align:center;padding:20px 0 8px 0;">
      <div style="display:inline-block;background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.4);
                  border-radius:20px;padding:4px 16px;font-size:.75rem;color:#818CF8;font-weight:600;
                  letter-spacing:.06em;margin-bottom:10px;">⚡ EFICIÊNCIA DE CORTE</div>
      <h1 style="font-size:2rem;font-weight:800;margin:0;">
        Análise de <span style="color:#6366F1;">Eficiência</span> de Corte
      </h1>
      <p style="color:#94A3B8;font-size:.95rem;margin:6px auto 0 auto;max-width:520px;text-align:center;">
        Análise detalhada por OP — eficiência, babys, retalhos e perdas por setor
      </p>
    </div>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,.08);margin:16px 0 20px 0;">
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "🔪 Manta Arealva (Zanattex)",
        "📋 Lençol Arealva",
        "🧵 GIattex",
    ])
    with tab1: _aba_manta()
    with tab2: _aba_lencol()
    with tab3: _aba_giattex()

# ABA 1 — MANTA AREALVA

def _aba_manta():
    try:
        with st.spinner("Carregando Manta Arealva..."):
            df_raw = carregar_manta_arealva()
    except Exception as e:
        st.error(f"❌ Erro ao carregar Manta Arealva: {e}")
        st.caption("Verifique se a planilha está acessível e com as colunas esperadas.")
        return

    if df_raw.empty:
        st.warning("Nenhum dado disponível para Manta Arealva.")
        return

    if df_raw["RETALHOS (Kg)"].sum() == 0 and df_raw["BABYS (Peças)"].sum() == 0:
        with st.expander("⚠️ Babys/Retalhos zerados — colunas disponíveis na planilha", expanded=False):
            st.caption("Colunas encontradas na planilha:")
            st.code(", ".join(df_raw.columns.tolist()))

    # filtros
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        ops_disp   = sorted(df_raw["NUM OP"].dropna().unique())
        prod_disp  = sorted(df_raw["PRODUTO"].dropna().unique()) if "PRODUTO" in df_raw.columns else []
        tam_disp   = sorted(df_raw["TAMANHO"].dropna().unique()) if "TAMANHO" in df_raw.columns else []
        prod_by_d  = sorted(df_raw["PRODUTOR"].dropna().unique()) if "PRODUTOR" in df_raw.columns else []

        ops_sel    = c1.multiselect("OP",        ops_disp,  default=[], key="ef_manta_op")
        prod_sel   = c2.multiselect("Produto",   prod_disp, default=[], key="ef_manta_prod")
        tam_sel    = c3.multiselect("Tamanho",   tam_disp,  default=[], key="ef_manta_tam")
        prod_by_sel= c4.multiselect("Produtor",  prod_by_d, default=[], key="ef_manta_prodby")

    df = df_raw.copy()
    if ops_sel:    df = df[df["NUM OP"].isin(ops_sel)]
    if prod_sel:   df = df[df["PRODUTO"].isin(prod_sel)]
    if tam_sel:    df = df[df["TAMANHO"].isin(tam_sel)]
    if prod_by_sel:df = df[df["PRODUTOR"].isin(prod_by_sel)]

    if df.empty:
        st.info("Nenhum dado para os filtros selecionados.")
        return

    # kpis
    total_ops    = df["NUM OP"].nunique()
    aprov_media  = df["APROVEITAMENTO_%"].mean(skipna=True)
    total_kgs_in = df["KGS CORTADOS"].sum()
    total_pecas  = df["PECAS_BOAS_KG"].sum()
    total_baby   = df["BABYS_KG"].sum()
    total_ret    = df["RETALHOS (Kg)"].sum()
    total_div    = df["DIVERGENCIA (Kg)"].sum()

    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
    _kpi(k1, "Total OPs",        f"{total_ops}")
    _kpi(k2, "Aproveitamento",   f"{aprov_media:.1f}%".replace(".", ",") if not np.isnan(aprov_media) else "—",
         color=_GREEN if not np.isnan(aprov_media) and aprov_media>=95 else _YELLOW if not np.isnan(aprov_media) and aprov_media>=85 else _RED)
    _kpi(k3, "Kgs Cortados",     f"{total_kgs_in:,.0f}".replace(",", "."))
    _kpi(k4, "Peças Boas (kg)",  f"{total_pecas:,.0f}".replace(",", "."), color=_GREEN)
    _kpi(k5, "Babys (kg)",       f"{total_baby:,.0f}".replace(",", "."), color=_YELLOW)
    _kpi(k6, "Retalhos (kg)",    f"{total_ret:,.0f}".replace(",", "."), color=_YELLOW)
    _kpi(k7, "Divergência (kg)", f"{total_div:+,.0f}".replace(",", "."),
         color=_GREEN if abs(total_div)<50 else _YELLOW if abs(total_div)<200 else _RED)

    st.markdown("<br>", unsafe_allow_html=True)

    # gráficos
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("##### Composição dos Kgs por OP")
        df_comp = df.groupby("NUM OP", as_index=False).agg(
            PECAS=("PECAS_BOAS_KG","sum"),
            BABYS=("BABYS_KG","sum"),
            RETALHOS=("RETALHOS (Kg)","sum"),
        ).sort_values("PECAS", ascending=True).tail(10)
        df_comp["NUM OP"] = df_comp["NUM OP"].astype(str)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Peças Boas (kg)", y=df_comp["NUM OP"], x=df_comp["PECAS"],
                             orientation="h", marker_color="rgba(34,197,94,.8)"))
        fig.add_trace(go.Bar(name="Babys (kg)",      y=df_comp["NUM OP"], x=df_comp["BABYS"],
                             orientation="h", marker_color="rgba(245,158,11,.8)"))
        fig.add_trace(go.Bar(name="Retalhos (kg)",   y=df_comp["NUM OP"], x=df_comp["RETALHOS"],
                             orientation="h", marker_color="rgba(239,68,68,.8)"))
        fig.update_layout(**_plot_cfg())
        fig.update_layout(height=max(300, len(df_comp)*30),
                          barmode="stack", xaxis_title="kg",
                          yaxis=dict(type="category"),
                          legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        st.markdown("##### Aproveitamento % por OP (KGS FINAL / KGS CORTADOS)")
        df_ap = df[df["APROVEITAMENTO_%"].notna()].groupby("NUM OP", as_index=False)["APROVEITAMENTO_%"].mean().sort_values("APROVEITAMENTO_%", ascending=True).tail(10)
        df_ap["NUM OP"] = df_ap["NUM OP"].astype(str)
        fig2 = go.Figure(go.Bar(
            x=df_ap["APROVEITAMENTO_%"], y=df_ap["NUM OP"], orientation="h",
            marker_color=[_GREEN if v>=95 else _YELLOW if v>=85 else _RED for v in df_ap["APROVEITAMENTO_%"]],
            text=df_ap["APROVEITAMENTO_%"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
            textposition="outside"
        ))
        fig2.add_vline(x=100, line_dash="dot", line_color="rgba(99,102,241,.5)", annotation_text="100%")
        fig2.update_layout(**_plot_cfg(), height=max(280, len(df_ap)*28),
                           xaxis_title="Aproveitamento (%)", yaxis=dict(type="category"))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # babys & retalhos
    st.markdown("##### Babys & Retalhos por OP")
    c_l2, c_r2 = st.columns(2)
    df_br = df.groupby("NUM OP", as_index=False).agg(
        BABYS=("BABYS (Peças)","sum"),
        RETALHOS=("RETALHOS (Kg)","sum"),
    ).sort_values("RETALHOS", ascending=False).head(10)
    df_br["NUM OP"] = df_br["NUM OP"].astype(str)

    with c_l2:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(name="Babys (peças)", x=df_br["NUM OP"], y=df_br["BABYS"],
                               marker_color="rgba(245,158,11,.8)"))
        fig3.add_trace(go.Bar(name="Retalhos (kg)", x=df_br["NUM OP"], y=df_br["RETALHOS"],
                               marker_color="rgba(239,68,68,.8)"))
        fig3.update_layout(**_plot_cfg(), height=300, barmode="group",
                           xaxis=dict(type="category", tickangle=-45), yaxis_title="Qtd / Kg")
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    with c_r2:
        st.markdown("##### Divergência (kg) por OP")
        df_div = df.groupby("NUM OP", as_index=False)["DIVERGENCIA (Kg)"].sum().sort_values("DIVERGENCIA (Kg)").head(10)
        df_div["NUM OP"] = df_div["NUM OP"].astype(str)
        fig4 = go.Figure(go.Bar(
            x=df_div["DIVERGENCIA (Kg)"], y=df_div["NUM OP"], orientation="h",
            marker_color=[_GREEN if abs(v)<50 else _YELLOW if abs(v)<200 else _RED for v in df_div["DIVERGENCIA (Kg)"]],
            text=df_div["DIVERGENCIA (Kg)"].apply(lambda v: f"{v:+.1f} kg".replace(".", ",")),
            textposition="outside"
        ))
        fig4.add_vline(x=0, line_dash="solid", line_color="rgba(255,255,255,.2)")
        fig4.update_layout(**_plot_cfg(), height=max(280, len(df_div)*28),
                           xaxis_title="Divergência (kg)", yaxis=dict(type="category"))
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # tabela detalhada
    st.markdown("##### Detalhamento por OP")
    cols_show = [c for c in [
        "NUM OP","PRODUTO","TAMANHO","PRODUTOR",
        "TOTAL CORTE","KGS CORTADOS",
        "PECAS_BOAS_KG","BABYS_KG","RETALHOS (Kg)","KGS FINAL",
        "APROVEITAMENTO_%","DIVERGENCIA (Kg)","CONCLUSAO_%"
    ] if c in df.columns]
    df_show = df[cols_show].copy().rename(columns={
        "NUM OP":"OP","PRODUTO":"Produto","TAMANHO":"Tamanho","PRODUTOR":"Produtor",
        "TOTAL CORTE":"Cortado (Pçs)","KGS CORTADOS":"Kgs Cortados",
        "PECAS_BOAS_KG":"Peças Boas (kg)","BABYS_KG":"Babys (kg)",
        "RETALHOS (Kg)":"Retalhos (kg)","KGS FINAL":"Kgs Final",
        "APROVEITAMENTO_%":"Aproveitamento %","DIVERGENCIA (Kg)":"Divergência (kg)",
        "CONCLUSAO_%":"Conclusão OP %",
    })

    def _pct_fmt(v):
        try:
            return f"{float(v):.1f}%".replace(".", ",") if not np.isnan(float(v)) else "—"
        except: return "—"

    def _color_aprov(val):
        try:
            v = float(str(val).replace(",", ".").replace("%", ""))
            return "color:#22C55E" if v>=95 else "color:#F59E0B" if v>=85 else "color:#EF4444"
        except: return ""

    def _color_efic(val):
        try:
            v = float(str(val).replace(",", ".").replace("%", ""))
            return "color:#22C55E" if v>=95 else "color:#F59E0B" if v>=85 else "color:#EF4444"
        except: return ""

    def _num_fmt(v):
        try: return f"{float(v):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except: return v

    num_fmt_cols = [c for c in ["Cortado (Pçs)","Kgs Cortados","Peças Boas (kg)",
                                 "Babys (kg)","Retalhos (kg)","Kgs Final","Divergência (kg)"] if c in df_show.columns]
    pct_fmt = {c: _pct_fmt for c in ["Aproveitamento %","Conclusão OP %"] if c in df_show.columns}
    pct_fmt.update({c: _num_fmt for c in num_fmt_cols})
    styled = df_show.style.format(pct_fmt, na_rep="—")
    if "Aproveitamento %" in df_show.columns:
        styled = styled.map(_color_aprov, subset=["Aproveitamento %"])
    if "Conclusão OP %" in df_show.columns:
        styled = styled.map(_color_efic, subset=["Conclusão OP %"])

    st.dataframe(styled, use_container_width=True, hide_index=True, height=380)

# ABA 2 — LENÇOL AREALVA

def _aba_lencol():
    try:
        with st.spinner("Carregando Lençol Arealva..."):
            df_raw = carregar_lencol_arealva()
    except Exception as e:
        st.error(f"❌ Erro ao carregar Lençol: {e}")
        st.caption("Verifique se a planilha está acessível e com as colunas esperadas.")
        return

    if df_raw.empty:
        st.warning("Nenhum dado disponível para Lençol.")
        return

    # filtros
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        ops_disp  = sorted(df_raw["OP"].dropna().unique())
        cli_disp  = sorted([x for x in df_raw["CLIENTE"].dropna().unique() if x not in ("", "nan")])
        tec_disp  = sorted([x for x in df_raw["TECIDO"].dropna().unique()  if x not in ("", "nan")])
        stat_disp = sorted([x for x in df_raw["STATUS"].dropna().unique()  if x not in ("", "nan")])

        ops_sel  = c1.multiselect("OP",      ops_disp,  default=[], key="ef_len_op")
        cli_sel  = c2.multiselect("Cliente", cli_disp,  default=[], key="ef_len_cli")
        tec_sel  = c3.multiselect("Tecido",  tec_disp,  default=[], key="ef_len_tec")
        stat_sel = c4.multiselect("Status",  stat_disp, default=[], key="ef_len_stat")

    df = df_raw.copy()
    if ops_sel:  df = df[df["OP"].isin(ops_sel)]
    if cli_sel:  df = df[df["CLIENTE"].isin(cli_sel)]
    if tec_sel:  df = df[df["TECIDO"].isin(tec_sel)]
    if stat_sel: df = df[df["STATUS"].isin(stat_sel)]

    if df.empty:
        st.info("Nenhum dado para os filtros selecionados.")
        return

    # kpis
    total_ops    = df["OP"].nunique()
    aprov_media  = df["APROVEITAMENTO_%"].mean(skipna=True)
    total_mts_in = df["MTS_CORT"].sum()
    total_mts_esp= df["MTS_ESP"].sum()
    total_dif    = df["DIFERENCA_MTS"].sum()
    total_ret    = df["RETALHO_KG"].sum()
    total_prog_p = df["QTD_PROG"].sum()
    total_cort_p = df["QTD_CORT"].sum()
    conclusao_med= df["CONCLUSAO_%"].mean()

    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
    _kpi(k1, "Total OPs",         f"{total_ops}")
    _kpi(k2, "Aproveitamento",
         f"{aprov_media:.1f}%".replace(".", ",") if not np.isnan(aprov_media) else "—",
         color=_GREEN if not np.isnan(aprov_media) and aprov_media>=95
               else _YELLOW if not np.isnan(aprov_media) and aprov_media>=85 else _RED)
    _kpi(k3, "Metros Cortados",   f"{total_mts_in:,.0f}".replace(",", "."))
    _kpi(k4, "Metros Esperados",  f"{total_mts_esp:,.0f}".replace(",", "."))
    _kpi(k5, "Diferença (MTs)",   f"{total_dif:+,.0f}".replace(",", "."),
         color=_GREEN if abs(total_dif)<50 else _YELLOW if abs(total_dif)<500 else _RED)
    _kpi(k6, "Retalho (kg)",      f"{total_ret:,.0f}".replace(",", "."), color=_YELLOW)
    _kpi(k7, "Conclusão OP",
         f"{conclusao_med:.1f}%".replace(".", ","),
         color=_GREEN if conclusao_med>=98 else _YELLOW if conclusao_med>=80 else _RED)

    st.markdown("<br>", unsafe_allow_html=True)

    # gráficos linha 1
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("##### Metros Esperados vs Cortados por OP")
        df_mts = df.groupby("OP", as_index=False).agg(
            ESP=("MTS_ESP", "sum"),
            CORT=("MTS_CORT", "sum"),
        ).sort_values("ESP", ascending=True).tail(10)
        df_mts["OP"] = df_mts["OP"].astype(str)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Metros Esperados", y=df_mts["OP"], x=df_mts["ESP"],
                             orientation="h", marker_color="rgba(99,102,241,.7)"))
        fig.add_trace(go.Bar(name="Metros Cortados",  y=df_mts["OP"], x=df_mts["CORT"],
                             orientation="h", marker_color="rgba(34,197,94,.7)"))
        fig.update_layout(**_plot_cfg())
        fig.update_layout(height=max(300, len(df_mts)*30), barmode="group",
                          xaxis_title="Metros (MTs)", yaxis=dict(type="category"),
                          legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        st.markdown("##### Aproveitamento % por OP (Metros Cortados / Esperados)")
        df_ap = df[df["APROVEITAMENTO_%"].notna()].groupby("OP", as_index=False)["APROVEITAMENTO_%"].mean()\
                  .sort_values("APROVEITAMENTO_%", ascending=True).tail(10)
        df_ap["OP"] = df_ap["OP"].astype(str)
        fig2 = go.Figure(go.Bar(
            x=df_ap["APROVEITAMENTO_%"], y=df_ap["OP"], orientation="h",
            marker_color=[_GREEN if v>=95 else _YELLOW if v>=85 else _RED for v in df_ap["APROVEITAMENTO_%"]],
            text=df_ap["APROVEITAMENTO_%"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
            textposition="outside"
        ))
        fig2.add_vline(x=100, line_dash="dot", line_color="rgba(99,102,241,.5)", annotation_text="100%")
        fig2.update_layout(**_plot_cfg(), height=max(280, len(df_ap)*28),
                           xaxis_title="Aproveitamento (%)", yaxis=dict(type="category"))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # gráficos linha 2
    c_l2, c_r2 = st.columns(2)

    with c_l2:
        st.markdown("##### Diferença (MTs) por OP")
        df_dif = df.groupby("OP", as_index=False)["DIFERENCA_MTS"].sum()\
                   .sort_values("DIFERENCA_MTS", ascending=True).head(10)
        df_dif["OP"] = df_dif["OP"].astype(str)
        fig3 = go.Figure(go.Bar(
            x=df_dif["DIFERENCA_MTS"], y=df_dif["OP"], orientation="h",
            marker_color=[_GREEN if abs(v)<50 else _YELLOW if abs(v)<300 else _RED
                          for v in df_dif["DIFERENCA_MTS"]],
            text=df_dif["DIFERENCA_MTS"].apply(lambda v: f"{v:+.1f} m".replace(".", ",")),
            textposition="outside"
        ))
        fig3.add_vline(x=0, line_dash="solid", line_color="rgba(255,255,255,.2)")
        fig3.update_layout(**_plot_cfg(), height=max(280, len(df_dif)*28),
                           xaxis_title="Diferença (MTs)", yaxis=dict(type="category"))
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    with c_r2:
        st.markdown("##### Conclusão OP % (Peças Cortadas / Programadas)")
        df_conc = df.groupby("OP", as_index=False).agg(
            PROG=("QTD_PROG","sum"), CORT=("QTD_CORT","sum")
        )
        df_conc["CONCLUSAO_%"] = (
            df_conc["CORT"] / df_conc["PROG"].replace(0, np.nan) * 100
        ).fillna(0).round(1)
        df_conc = df_conc.sort_values("CONCLUSAO_%", ascending=True).tail(10)
        df_conc["OP"] = df_conc["OP"].astype(str)
        fig4 = go.Figure(go.Bar(
            x=df_conc["CONCLUSAO_%"], y=df_conc["OP"], orientation="h",
            marker_color=[_GREEN if v>=98 else _YELLOW if v>=80 else _RED for v in df_conc["CONCLUSAO_%"]],
            text=df_conc["CONCLUSAO_%"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
            textposition="outside"
        ))
        fig4.add_vline(x=100, line_dash="dot", line_color="rgba(99,102,241,.5)", annotation_text="100%")
        fig4.update_layout(**_plot_cfg(), height=max(280, len(df_conc)*28),
                           xaxis_title="Conclusão OP (%)", yaxis=dict(type="category"))
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # tabela detalhada
    st.markdown("##### Detalhamento por OP")
    cols_show = [c for c in [
        "OP","CLIENTE","PRODUTO","TIPO","TAMANHO","TECIDO","STATUS",
        "QTD_PROG","QTD_CORT","MTS_ESP","MTS_CORT",
        "DIFERENCA_MTS","PERDA_%","RETALHO_KG","APROVEITAMENTO_%","CONCLUSAO_%"
    ] if c in df.columns]
    df_show = df[cols_show].copy().rename(columns={
        "OP":"OP","CLIENTE":"Cliente","PRODUTO":"Produto","TIPO":"Tipo",
        "TAMANHO":"Tamanho","TECIDO":"Tecido","STATUS":"Status",
        "QTD_PROG":"Prog (Pçs)","QTD_CORT":"Cort (Pçs)",
        "MTS_ESP":"Mts Esperados","MTS_CORT":"Mts Cortados",
        "DIFERENCA_MTS":"Diferença (MTs)","PERDA_%":"Perda %",
        "RETALHO_KG":"Retalho (kg)",
        "APROVEITAMENTO_%":"Aproveitamento %","CONCLUSAO_%":"Conclusão OP %",
    })

    def _pct_fmt(v):
        try:
            return f"{float(v):.1f}%".replace(".", ",") if not np.isnan(float(v)) else "—"
        except: return "—"

    def _num_fmt(v):
        try: return f"{float(v):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except: return v

    def _color_aprov(val):
        try:
            v = float(str(val).replace(",", ".").replace("%", ""))
            return "color:#22C55E" if v>=95 else "color:#F59E0B" if v>=85 else "color:#EF4444"
        except: return ""

    def _color_conc(val):
        try:
            v = float(str(val).replace(",", ".").replace("%", ""))
            return "color:#22C55E" if v>=98 else "color:#F59E0B" if v>=80 else "color:#EF4444"
        except: return ""

    num_cols = [c for c in ["Prog (Pçs)","Cort (Pçs)","Mts Esperados","Mts Cortados",
                             "Diferença (MTs)","Retalho (kg)"] if c in df_show.columns]
    pct_cols = {c: _pct_fmt for c in ["Aproveitamento %","Conclusão OP %","Perda %"]
                if c in df_show.columns}
    pct_cols.update({c: _num_fmt for c in num_cols})
    styled = df_show.style.format(pct_cols, na_rep="—")
    if "Aproveitamento %" in df_show.columns:
        styled = styled.map(_color_aprov, subset=["Aproveitamento %"])
    if "Conclusão OP %" in df_show.columns:
        styled = styled.map(_color_conc, subset=["Conclusão OP %"])

    st.dataframe(styled, use_container_width=True, hide_index=True, height=380)

# ABA 3 — GIATTEX

def _aba_giattex():
    try:
        with st.spinner("Carregando GIattex..."):
            df = carregar_giattex()
    except Exception as e:
        st.error(f"❌ Erro ao carregar GIattex: {e}")
        return

    if df.empty:
        st.info("📌 Dados de GIattex ainda não configurados.")
        st.markdown("""
        **Para configurar:**
        1. Abra `components/eficiencia_corte.py`
        2. Atualize `EFICIENCIA_GIATTEX_ID` e `EFICIENCIA_GIATTEX_GID` com os IDs corretos da planilha
        """)
        return

    st.markdown("#### 🧵 GIattex — Eficiência de Corte")
    st.dataframe(df, use_container_width=True, hide_index=True)
