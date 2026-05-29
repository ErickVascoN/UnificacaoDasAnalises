"""
Controle de Programação de Corte
Cruza a programação semanal com os dados reais de corte (Arealva Manta + Iacanga).
"""

import io
import logging
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
    # Rótulos padronizados: Arealva = Zanattex, Iacanga = Giattex.
    # col_mat = coluna com o material/produto; col_cli = coluna do cliente/empresa
    # (None → usa cli_fixo). Manta Arealva não tem cliente → sempre "Camesa".
    _SOURCES = [
        (MANTA_ID,   MANTA_GID,   "Zanattex", "QUANTIDADE", "PRODUTO", None,      "Camesa"),
        (IACANGA_ID, IACANGA_GID, "Giattex",  "QUANTIDADE", "PRODUTO", "CLIENTE", ""),
    ]

    for sid, gid, fonte, col_qtd, col_mat, col_cli, cli_fixo in _SOURCES:
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
            sub["MATERIAL"] = (
                df[col_mat].astype(str).str.strip() if col_mat in df.columns else ""
            )
            sub["CLIENTE"] = (
                df[col_cli].astype(str).str.strip()
                if (col_cli and col_cli in df.columns) else cli_fixo
            )

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
                "MATERIAL": (
                    df_len["TECIDO"].astype(str).str.strip()
                    if "TECIDO" in df_len.columns else ""
                ),
                "CLIENTE": (
                    df_len["EMPRESA"].astype(str).str.strip()
                    if "EMPRESA" in df_len.columns else ""
                ),
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
    if "MATERIAL" not in out.columns:
        out["MATERIAL"] = ""
    out["MATERIAL"] = out["MATERIAL"].astype(str).str.strip().replace(
        {"nan": "", "NaN": "", "None": "", "<NA>": "", "0": ""}
    )
    if "CLIENTE" not in out.columns:
        out["CLIENTE"] = ""
    out["CLIENTE"] = out["CLIENTE"].astype(str).str.strip().replace(
        {"nan": "", "NaN": "", "None": "", "<NA>": "", "0": ""}
    )
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

        pass  # não usado — ver mapeamento direto abaixo

    df = df.drop(columns=["_SEM"])

    # Mapeia cortado DIRETAMENTE por OP (_PEDN) → sem transform("sum") que
    # multiplicaria o valor pelo número de linhas da mesma OP na programação.
    # Cada linha recebe o total cortado da sua OP em todas as semanas.
    df["QNT_CORTADA"] = (
        df["_PEDN"].map(_op_map).fillna(0).astype(int)
    )
    df = df.drop(columns=["_PEDN"])

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

        # ── Lençol: QNT CORTADA por PRODUTO (não o total da OP) ───────────────────
        # A planilha de corte do Lençol traz o produto correto (TECIDO/MATERIAL).
        # Casa o produto da linha da programação com o do corte por similaridade;
        # sem correspondência ("caso não tenha"), mantém o total da OP. Só Lençol —
        # nas demais fontes o nome do produto não bate, então fica o total.
        if not df_cortes_raw.empty and "FONTE" in df_cortes_raw.columns \
                and "MATERIAL" in df_cortes_raw.columns:
            import difflib
            from utils.normalize import normalize_op as _nop_d, normalize_text as _nt_d
            _len = df_cortes_raw[df_cortes_raw["FONTE"] == "Lençol"].copy()
            _len["_OPN"] = _len["OP"].map(_nop_d)
            _len = _len[(_len["_OPN"] != "")
                        & (_len["MATERIAL"].astype(str).str.strip() != "")]
            # OPs cortadas em OUTRAS fontes (Giattex/Zanattex): nessas NÃO aplicamos a
            # quebra por produto (e não zeramos), para não atribuir 0 errado.
            _outras_opns = set(
                df_cortes_raw.loc[df_cortes_raw["FONTE"] != "Lençol", "OP"].map(_nop_d)
            ) - {""}
            if not _len.empty:
                _len_grp = _len.groupby(["_OPN", "MATERIAL"])["QUANTIDADE"].sum().reset_index()
                _mapa_len = {}
                for _, _r in _len_grp.iterrows():
                    _mapa_len.setdefault(_r["_OPN"], []).append(
                        (_nt_d(_r["MATERIAL"]), int(_r["QUANTIDADE"]))
                    )

                _LIMIAR_SIM = 0.70  # só casa produtos realmente parecidos

                def _cortado_por_produto(row):
                    opn = _nop_d(row.get("PED. CLIENTE", ""))
                    # Só quebra por produto OPs cortadas exclusivamente no Lençol.
                    if opn not in _mapa_len or opn in _outras_opns:
                        return None  # mantém o total da OP
                    desc = (str(row.get("DESCRIÇÃO DO PRODUTO", "")).strip()
                            or str(row.get("PRODUTO", "")).strip())
                    alvo = _nt_d(desc)
                    if not alvo:
                        return None
                    best_q, best_r = 0, 0.0
                    for _mn, _q in _mapa_len[opn]:
                        _ratio = difflib.SequenceMatcher(None, alvo, _mn).ratio()
                        if _ratio > best_r:
                            best_r, best_q = _ratio, _q
                    # Casou → qtd do produto; não casou → 0 (não foi cortado esse produto).
                    return best_q if best_r >= _LIMIAR_SIM else 0

                _novos = df_det.apply(_cortado_por_produto, axis=1)
                _mask_ovr = _novos.notna()
                if _mask_ovr.any():
                    df_det.loc[_mask_ovr, "QNT_CORTADA"] = _novos[_mask_ovr].astype(int)
                    _prog_row = pd.to_numeric(
                        df_det.loc[_mask_ovr, "QNT. PROG"], errors="coerce"
                    ).fillna(0)
                    df_det.loc[_mask_ovr, "DIFERENÇA"] = (
                        df_det.loc[_mask_ovr, "QNT_CORTADA"] - _prog_row
                    )
                    df_det.loc[_mask_ovr, "EFICIÊNCIA_%"] = (
                        df_det.loc[_mask_ovr, "QNT_CORTADA"]
                        / _prog_row.replace(0, pd.NA) * 100
                    ).fillna(0).round(1)

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

    _peds_prog_fora = {o for o in df_prog_raw["PED. CLIENTE"].map(_nop_fora).unique() if o}
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

        _agg_kwargs = {"Peças": ("QUANTIDADE", "sum"), "Fonte": ("FONTE", _join_unicos)}
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

        _tab = _tab.sort_values("Peças", ascending=False).reset_index(drop=True)
        _tab_fmt = _tab.copy()
        _tab_fmt["Peças"] = _tab_fmt["Peças"].map(lambda x: f"{int(x):,}".replace(",", "."))

        st.dataframe(_tab_fmt, use_container_width=True, hide_index=True)

        # Gráfico — top 15 OPs cortadas fora do plano
        _top = _tab.head(15).sort_values("Peças", ascending=True)
        # OP é rótulo (categoria), não número — senão o eixo trata "1895301001"
        # como 1,8 bilhão e o gráfico fica achatado.
        _y_labels = _top["OP"].astype(str).tolist()
        fig_fora = go.Figure(go.Bar(
            x=_top["Peças"].tolist(), y=_y_labels, orientation="h",
            marker_color="#f59e0b",
            text=[f"{int(v):,}".replace(",", ".") for v in _top["Peças"]],
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
