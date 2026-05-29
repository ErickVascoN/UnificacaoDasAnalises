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
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.auth import init_session_state
from utils.navigation import safe_switch

# constantes
PROG_ID     = "1FeTwrPEBOcC6RmD_5zh8NQLwOrYO87XA"
PROG_GID    = "708887209"
MANTA_ID    = "1KLbNpw-P28YgoijXfMXU-zRQULuDHMMB"
MANTA_GID   = "1544210185"
IACANGA_ID  = "1FBpCrq29_e1UBNwBlcgPTz66tbpUsgcgtzfXi4DcORU"
IACANGA_GID = "0"
LENCOL_ID   = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_GID  = "1396046910"
CACHE_TTL   = 300

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
if not st.session_state.get("auth_nivel"):
    st.warning("🔒 Acesso restrito. Faça login na página inicial.")
    if st.button("← Voltar ao Início"):
        safe_switch("app.py")
    st.stop()

# sidebar nav
with st.sidebar:
    st.markdown("### 📊 Controle de Programação")
    st.markdown("---")
    if st.button("🏢 Início", key="sb_home", use_container_width=True):
        safe_switch("app.py")
    st.markdown("---")
    st.header("🔍 Filtros")

# data loading
def _fetch(sheet_id: str, gid: str) -> str | None:
    from utils.cache_manager import get_raw
    return get_raw(sheet_id, gid, ttl=CACHE_TTL)

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_programacao() -> pd.DataFrame:
    texto = _fetch(PROG_ID, PROG_GID)
    if not texto:
        raise ConnectionError("Não foi possível baixar a planilha de programação.")

    # Detecta linha real do cabeçalho (pode haver título antes)
    linhas = texto.splitlines()
    header_row = 0
    for i, linha in enumerate(linhas[:10]):
        linha_up = linha.upper()
        if "SEMANA" in linha_up and "CLIENTE" in linha_up:
            header_row = i
            break

    df = pd.read_csv(io.StringIO(texto), skiprows=header_row, header=0, dtype=str)
    df.columns = df.columns.str.strip()

    # Normaliza nomes de colunas para encontrar variações de encoding
    col_map = {c.upper().strip(): c for c in df.columns}

    def _col(nome: str) -> str:
        """Retorna o nome real da coluna, case-insensitive."""
        return col_map.get(nome.upper().strip(), nome)

    # Garante colunas essenciais
    essenciais = [
        "PED. CLIENTE", "SEMANA", "CLIENTE", "LOCAL", "PRODUTO",
        "PED. INT", "OP INTERNA", "OC", "DESCRIÇÃO DO PRODUTO",
        "QNT. PROG", "REPRO./INCLUIDO(S/N)", "MOTIVO REPRO./INCLUSÃO",
        "DATA INICIO", "DATA FINALIZADO", "PREV. INDUSTRIALIZAÇÃO",
    ]
    for col in essenciais:
        real = _col(col)
        if real not in df.columns:
            df[col] = ""
        elif real != col:
            df[col] = df[real]

    df["PED. CLIENTE"] = df["PED. CLIENTE"].astype(str).str.strip()
    df["QNT. PROG"]    = pd.to_numeric(df["QNT. PROG"], errors="coerce").fillna(0).astype(int)
    df["SEMANA"]       = df["SEMANA"].astype(str).str.strip()
    df["CLIENTE"]      = df["CLIENTE"].astype(str).str.strip()
    df["LOCAL"]        = df["LOCAL"].astype(str).str.strip()

    invalidos = {"", "NAN", "NONE", "N/A"}

    def _valido(serie: pd.Series) -> pd.Series:
        s = serie.astype(str).str.strip()
        return s.ne("") & ~s.str.upper().isin(invalidos)

    # Fallback de OP: quando NÃO existe a OP (PED. CLIENTE), a OP INTERNA ocupa o lugar
    # dela e passa a ser a OP daquela linha. Se a OP existe, OP INTERNA é ignorada
    # (não entra no cruzamento, para não gerar match falso).
    ped_valido = _valido(df["PED. CLIENTE"])
    if "OP INTERNA" in df.columns:
        usar_opint = ~ped_valido & _valido(df["OP INTERNA"])
        df.loc[usar_opint, "PED. CLIENTE"] = (
            df.loc[usar_opint, "OP INTERNA"].astype(str).str.strip()
        )

    # Mantém linhas com OP (própria ou via OP INTERNA) e também as sem OP nenhuma
    # mas com produção real (ex: MANTA CELTA sem OP, só quantidade programada).
    ped_valido = _valido(df["PED. CLIENTE"])
    tem_producao = df["QNT. PROG"] > 0
    df = df[ped_valido | tem_producao].reset_index(drop=True)

    # _CHAVE = a OP (PED. CLIENTE). Linhas que continuam sem OP nenhuma agrupam por
    # CLIENTE+PRODUTO+SEMANA (sub-linhas do mesmo item viram uma OP só); OP exibida vazia.
    df["_CHAVE"] = df["PED. CLIENTE"]
    sem_op = ~_valido(df["PED. CLIENTE"])
    df.loc[sem_op, "_CHAVE"] = (
        "SEMOP|"
        + df.loc[sem_op, "CLIENTE"].astype(str).str.strip() + "|"
        + df.loc[sem_op, "PRODUTO"].astype(str).str.strip() + "|"
        + df.loc[sem_op, "SEMANA"].astype(str).str.strip()
    )
    df.loc[sem_op, "PED. CLIENTE"] = ""  # exibido como vazio/"—"
    return df

# (parser de data local removido — usar utils.date_parser.parse_date_series,
#  que detecta o formato D/M vs M/D por coluna.)

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_cortes() -> pd.DataFrame:
    """
    Carrega dados de corte de três fontes:
      - Arealva/Manta  (QUANTIDADE, header simples)
      - Iacanga        (QUANTIDADE, header simples)
      - Lençol Arealva (QUANT, pode ter linha de título → header detection)

    Retorna colunas [OP, QUANTIDADE, FONTE, SEMANA].
    SEMANA é o nº ISO da semana derivado da coluna DATA — essencial para que
    o join não some cortes de semanas anteriores para OPs reutilizadas (ex: PROG 81).
    """
    from utils.date_parser import parse_date_series
    frames = []

    # Manta e Iacanga: header simples, coluna DATA correta → parsing direto.
    _SOURCES = [
        (MANTA_ID,   MANTA_GID,   "Arealva",  "QUANTIDADE"),
        (IACANGA_ID, IACANGA_GID, "Iacanga",  "QUANTIDADE"),
    ]

    for sid, gid, fonte, col_qtd in _SOURCES:
        texto = _fetch(sid, gid)
        if not texto:
            logging.debug(f"load_cortes: sem texto para {fonte}")
            continue
        try:
            df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
            df.columns = df.columns.str.strip()

            if "OP" not in df.columns or col_qtd not in df.columns:
                logging.debug(
                    f"load_cortes: {fonte} sem colunas esperadas. "
                    f"Disponíveis: {list(df.columns)}"
                )
                continue

            sub = df[["OP", col_qtd]].copy()
            sub = sub.rename(columns={col_qtd: "QUANTIDADE"})
            sub["FONTE"] = fonte

            # Derivar SEMANA ISO a partir de DATA (para join por semana)
            if "DATA" in df.columns:
                datas = parse_date_series(df["DATA"])
                sub["SEMANA"] = datas.dt.isocalendar().week.astype("Int64")
            else:
                sub["SEMANA"] = pd.array([pd.NA] * len(sub), dtype="Int64")

            frames.append(sub)
            logging.debug(f"load_cortes: {fonte} → {len(sub)} registros")

        except Exception as e:
            logging.debug(f"load_cortes: parse {fonte}: {e}")

    # Lençol: estrutura complexa (coluna "DATA" contém empresa, data real noutra coluna).
    # Usa o loader dedicado, que mapeia as colunas por conteúdo corretamente.
    try:
        from utils.lencol_loader_smart import load_lencol_smart_xlsx
        df_len = load_lencol_smart_xlsx()
        if not df_len.empty and "OP" in df_len.columns and "QUANT" in df_len.columns:
            sub = pd.DataFrame({
                "OP": df_len["OP"],
                "QUANTIDADE": df_len["QUANT"],
                "FONTE": "Lençol",
            })
            if "DATA" in df_len.columns:
                datas = pd.to_datetime(df_len["DATA"], errors="coerce")
                sub["SEMANA"] = datas.dt.isocalendar().week.astype("Int64")
            else:
                sub["SEMANA"] = pd.array([pd.NA] * len(sub), dtype="Int64")
            frames.append(sub)
            logging.debug(f"load_cortes: Lençol → {len(sub)} registros")
        else:
            logging.debug("load_cortes: Lençol vazio ou sem colunas OP/QUANT")
    except Exception as e:
        logging.debug(f"load_cortes: parse Lençol: {e}")

    if not frames:
        return pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE", "SEMANA"])

    out = pd.concat(frames, ignore_index=True)
    out["OP"]         = out["OP"].astype(str).str.strip()
    out["QUANTIDADE"] = pd.to_numeric(out["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    invalidos = {"", "NAN", "NONE", "N/A", "SEM OP"}
    out = out[~out["OP"].str.upper().isin(invalidos)]
    return out

# lógica de cruzamento
def _status_corte(cortada: int, prog_total: int) -> str:
    if cortada <= 0:
        return "Pendente"
    eficiencia = cortada / prog_total if prog_total > 0 else 0
    if eficiencia >= 0.96:
        return "Concluído"
    return "Parcial"

def enriquecer(df_prog: pd.DataFrame, df_cortes: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza programação com cortes.

    Join principal: (OP, SEMANA)
      Garante que OPs reutilizadas semana a semana (ex: "PROG 81") não acumulem
      cortes de semanas anteriores — cada linha da programação enxerga apenas
      os cortes da sua própria semana.

    Prioridade de chave de busca:
      1. (PED. CLIENTE, SEMANA)  → caso mais comum
      2. (OP INTERNA,  SEMANA)  → quando a planilha de corte usa OP interna
    """
    import re as _re

    df = df_prog.copy()
    # _CHAVE = identificador de agrupamento (OP, ou chave única p/ linhas sem OP).
    # Fallback defensivo caso a coluna não exista (compatibilidade).
    if "_CHAVE" not in df.columns:
        df["_CHAVE"] = df["PED. CLIENTE"]

    # Soma QNT. PROG por (_CHAVE, SEMANA) — evita acumular semanas anteriores
    # para OPs reutilizadas semana a semana (ex: "PROG 81" tem 9.000/sem, não 88.992 total)
    total_prog_op = df.groupby(["_CHAVE", "SEMANA"])["QNT. PROG"].transform("sum")
    df["QNT_PROG_TOTAL"] = total_prog_op.fillna(0).astype(int)

    # sem dados de corte
    if df_cortes.empty:
        df["QNT_CORTADA"]  = 0
        df["STATUS_PROD"]  = "Não Iniciado"
        df["STATUS_CORTE"] = "Pendente"
        df["DIFERENÇA"]    = -df["QNT_PROG_TOTAL"]
        df["EFICIÊNCIA_%"] = 0.0
        return df

    # índice (op, semana) → quantidade cortada
    _tem_semana = (
        "SEMANA" in df_cortes.columns
        and df_cortes["SEMANA"].notna().any()
    )
    # OP normalizada (sem prefixo PROG/PGR/OP) — cruzamento prefixo-insensível.
    from utils.normalize import normalize_op, is_blank
    _cortes = df_cortes.copy()
    _cortes["_OPN"] = _cortes["OP"].map(normalize_op)
    _cortes = _cortes[_cortes["_OPN"].ne("")]

    if _tem_semana:
        _sem_idx = (
            _cortes.dropna(subset=["SEMANA"])
            .assign(_S=lambda d: d["SEMANA"].astype(int))
            .groupby(["_OPN", "_S"])["QUANTIDADE"].sum()
        )
        # dict: (op_normalizada, semana_int) → quantidade
        _sem_map: dict = {(str(op), int(s)): int(q) for (op, s), q in _sem_idx.items()}
    else:
        _sem_map = {}

    # Índice OP normalizada → quantidade (fallback sem semana)
    _op_map: dict = _cortes.groupby("_OPN")["QUANTIDADE"].sum().to_dict()

    # extrair semana iso do campo semana da programação ("semana 22" → 22)
    def _parse_sem(s) -> int | None:
        m = _re.search(r"\d+", str(s))
        return int(m.group()) if m else None

    df["_SEM"] = df["SEMANA"].apply(_parse_sem)

    # OP da programação normalizada da mesma forma (a OP é o PED. CLIENTE;
    # OP INTERNA não entra no cruzamento para não gerar match falso).
    df["_PEDN"] = df["PED. CLIENTE"].map(normalize_op)

    def _get_cortado(row) -> float:
        ped = row["_PEDN"]
        sem = row["_SEM"]

        if not ped:
            return 0.0  # linha sem OP → não há como cruzar com corte

        if _tem_semana and sem is not None:
            # (OP=PED. CLIENTE, SEMANA), ambas normalizadas
            return float(_sem_map.get((ped, sem), 0))
        else:
            # Sem informação de semana: usa acumulado por OP
            return float(_op_map.get(ped, 0))

    df["_CORTADO_ROW"] = df.apply(_get_cortado, axis=1)
    df = df.drop(columns=["_SEM", "_PEDN"])

    # Soma por _CHAVE → valor único distribuído a todas as linhas da OP
    df["QNT_CORTADA"] = (
        df.groupby("_CHAVE")["_CORTADO_ROW"]
        .transform("sum")
        .fillna(0)
        .astype(int)
    )
    df = df.drop(columns=["_CORTADO_ROW"])

    df["STATUS_PROD"]  = df["QNT_CORTADA"].apply(
        lambda x: "Liberado" if x > 0 else "Não Iniciado"
    )
    df["STATUS_CORTE"] = df.apply(
        lambda r: _status_corte(r["QNT_CORTADA"], r["QNT_PROG_TOTAL"]), axis=1
    )
    df["DIFERENÇA"]    = df["QNT_CORTADA"] - df["QNT_PROG_TOTAL"]
    df["EFICIÊNCIA_%"] = (
        df["QNT_CORTADA"] / df["QNT_PROG_TOTAL"].replace(0, pd.NA) * 100
    ).fillna(0).round(1)
    return df

def agregar_por_op(df: pd.DataFrame) -> pd.DataFrame:
    def join_unique(s):
        vals = sorted({str(v) for v in s if str(v) not in ("", "nan", "NAN", "None")})
        return " / ".join(vals)

    chave = "_CHAVE" if "_CHAVE" in df.columns else "PED. CLIENTE"
    return df.groupby(chave, as_index=False).agg(
        **{"PED. CLIENTE": ("PED. CLIENTE", "first")},
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
            st.dataframe(resultado[["FONTE", "OP", "QUANTIDADE"]], use_container_width=True, hide_index=True)

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

    _FONTES_ESPERADAS = ["Arealva", "Iacanga", "Lençol"]
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
