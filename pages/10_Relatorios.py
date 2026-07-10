"""Central de Relatórios — geração de todos os PDFs em um único lugar."""

from __future__ import annotations

import csv
import io
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from calendar import monthrange
from collections import Counter
from datetime import date, datetime, timedelta

import pandas as pd
import requests
import streamlit as st
from components.sidebar import render_home_button

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.auth import init_session_state
from styles.global_ui import get_global_ui_css
from utils.cache_manager import get_raw
from utils.date_parser import parse_date_series
from utils.metas_manager import load_metas
from utils.normalize import normalize_text
from utils.ui_helpers import multiselect_reset_on_grow
from utils.feriados import contar_dias_uteis, feriados_no_periodo
from config.settings import (
    CORTE_SHEETS_ID, CORTE_SHEETS_GID, CORTE_CACHE_TTL,
    IACANGA_SHEETS_ID, IACANGA_SHEETS_GID,
    PRODUCAO_SHEETS_ID,
)

from utils.lencol_caseamento import lencol_tipos_tams as _lencol_tipos_tams, lencol_caseamento
from utils.pdf_report import (
    gerar_pdf_arealva_manta,
    gerar_pdf_iacanga_manta,
    gerar_pdf_lencol,
    gerar_pdf_itaju,
    gerar_pdf_faccoes,
    gerar_pdf_previsao_cargas,
    gerar_pdf_carteira_pedidos,
    gerar_pdf_programacao,
    nome_arquivo_pdf,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Relatórios | Zanattex",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

# ── Constantes ─────────────────────────────────────────────────────────────────
_TTL = 300

# Corte Itaju
_ITAJU_ID  = "19dJKG956drBCv3fEnL75dTLf157xLKvE"
_ITAJU_GID = "1039503764"

# Metas Arealva / Iacanga (mesmos valores de 3_Controle_de_Corte.py)
# Para gerar_pdf_arealva_manta (metas flat) e gerar_pdf_corte_consolidado (metas nested)
_METAS_AREALVA_FLAT: dict[str, float] = {"MAQUINA": 7000, "MESA 1": 4000}
_METAS_AREALVA_META_TOTAL: float = sum(_METAS_AREALVA_FLAT.values())

_METAS_AREALVA: dict[str, dict] = {
    "MAQUINA": {"_DEFAULT": 7000},
    "MESA 1":  {"SOLTEIRO": 4700, "CASAL": 4000, "QUEEN": 2500, "KING": 2200, "_DEFAULT": 4000},
}
_METAS_IACANGA: dict[str, dict] = {
    "MAQUINA": {"SOLTEIRO": 8000, "CASAL": 7000, "QUEEN": 5500, "KING": 4500},
    "MESA":    {"SOLTEIRO": 3500, "CASAL": 3000, "QUEEN": 2600, "KING": 2300},
    "BURDAY":  {"SOLTEIRO": 9000, "CASAL": 9000, "QUEEN": 9000, "KING": 9000, "_DEFAULT": 9000},
}

# Cargas
_CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
_MESES_CARGAS = [
    ("JANEIRO",   1, 2026),
    ("FEVEREIRO", 2, 2026),
    ("MARÇO",     3, 2026),
    ("ABRIL",     4, 2026),
    ("MAIO",      5, 2026),
    ("JUNHO",     6, 2026),
]
_MESES_PT_CARGAS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Carteira
_CARTEIRA_SHEET_ID = "1U-iNIQRqKOIBrDZ86ZE5uJW6IQCzugJ7"
_CARTEIRA_GID      = "611396912"

# Programação
_PROG_ID     = "1FeTwrPEBOcC6RmD_5zh8NQLwOrYO87XA"
_PROG_GID    = "708887209"
_LENCOL_PROG_ID  = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
_LENCOL_PROG_GID = "1396046910"

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
footer{visibility:hidden;}
.stApp{background-color:#0F1117;}
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#111115 0%,#191920 100%);
    border-right:1px solid rgba(255,255,255,.10);
}
section[data-testid="stSidebar"] *{color:#E0E0E0!important;}
.pg-badge{
    display:inline-block;padding:5px 18px;border-radius:999px;
    font-size:.75rem;letter-spacing:.18em;text-transform:uppercase;font-weight:700;
    color:#4ECDC4;background:rgba(78,205,196,.10);border:1px solid rgba(78,205,196,.30);
    margin-bottom:14px;
}
.pg-title{font-size:2.2rem;font-weight:900;color:#FFF;margin:0 0 4px 0;line-height:1.1;}
.pg-sub{color:#718096;font-size:.95rem;margin-bottom:0;}
.accent{color:#4ECDC4;}
.report-card{
    background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
    border-radius:12px;padding:20px;margin-bottom:12px;
}
.report-card h4{color:#E2E8F0;font-size:.95rem;margin:0 0 4px 0;}
.report-card p{color:#718096;font-size:.82rem;margin:0;}
.stButton>button{
    background:linear-gradient(135deg,#1C1C22,#28282E)!important;
    border:1px solid rgba(255,255,255,.12)!important;
    color:#FFF!important;border-radius:10px!important;
}
.stButton>button:hover{border-color:#4ECDC4!important;color:#4ECDC4!important;}
</style>
""", unsafe_allow_html=True)

# ── Auth ───────────────────────────────────────────────────────────────────────
init_session_state()
render_home_button()  # sempre visível, mesmo sem login
if not st.session_state.get("auth_nivel"):
    st.warning("🔒 Acesso restrito. Faça login na página inicial para continuar.")
    st.stop()

with st.sidebar:
    st.markdown("### 📄 Central de Relatórios")
    st.markdown("---")
    if st.button("🔄 Atualizar Dados", key="sb_refresh", use_container_width=True):
        from utils.cache_manager import invalidate_all
        invalidate_all()
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Atualizado em: {datetime.now().strftime('%H:%M:%S')}")

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center'><span class='pg-badge'>📄 Zanattex · Central de Relatórios</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h1 class='pg-title' style='text-align:center'>Central de <span class='accent'>Relatórios PDF</span></h1>"
    "<p class='pg-sub' style='text-align:center'>Gere todos os relatórios em um único lugar — selecione o período e baixe o PDF</p>",
    unsafe_allow_html=True,
)
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _norm_text(s: str) -> str:
    return (unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().upper().strip())


def _normaliza_tamanho(tam: str) -> str:
    s = _norm_text(tam)
    if "SOLT" in s: return "SOLTEIRO"
    if "CASAL" in s or "DUPLO" in s: return "CASAL"
    if "QUEEN" in s or s == "Q": return "QUEEN"
    if "KING" in s or s == "K": return "KING"
    return s


def _canoniza_estacao_iacanga(estacao: str) -> str:
    """Uniformiza a grafia da estação de corte (Iacanga).

    A planilha tem "Maquina 1" e "Máquina 1" (com/sem acento) digitados ao
    longo do tempo pra mesma estação física — sem normalizar, cada grafia vira
    uma linha própria no relatório (estação duplicada) e a variante sem match
    exato de acento escapa da classificação de Grupo Meta (MAQUINA/MESA),
    puxando a meta de referência errada. Reconhece MAQUINA/MESA/BURDAY/
    REFILAMENTO/DERIVADOS + número opcional; nomes fora desse padrão passam
    inalterados (só strip), pra não mascarar uma estação nova ainda não mapeada.
    """
    s = re.sub(r"\s+", " ", _norm_text(estacao)).strip()
    m = re.match(r"^(MAQUINA|MESA|BURDAY|REFILAMENTO|DERIVADOS)\s*(\d*)$", s)
    if not m:
        return str(estacao).strip()
    label = {
        "MAQUINA": "Máquina", "MESA": "Mesa", "BURDAY": "Burday",
        "REFILAMENTO": "Refilamento", "DERIVADOS": "Derivados",
    }[m.group(1)]
    numero = m.group(2)
    return f"{label} {numero}".strip() if numero else label


# ══════════════════════════════════════════════════════════════════════════════
# LOADERS LOCAIS (cacheados)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_arealva() -> pd.DataFrame:
    content = get_raw(CORTE_SHEETS_ID, CORTE_SHEETS_GID, ttl=CORTE_CACHE_TTL)
    if not content:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(content), dtype=str)
    df.columns = df.columns.str.strip()
    df = df.drop(columns=[c for c in df.columns if "Unnamed" in c or "Coluna" in c], errors="ignore")
    if "DATA" not in df.columns or "QUANTIDADE" not in df.columns:
        return pd.DataFrame()
    df["DATA"] = parse_date_series(df["DATA"])
    df = df.dropna(subset=["DATA"])
    df["QUANTIDADE"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    df["ESTACAO"] = df.get("ESTAÇÃO DE CORTE", df.get("ESTACAO", pd.Series(dtype=str))).astype(str).str.strip()
    df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip() if "PRODUTO" in df.columns else ""
    df["OP"] = df.get("OP", pd.Series("SEM OP", index=df.index)).fillna("SEM OP").astype(str).str.strip()
    df["COR"] = df.get("COR", pd.Series("", index=df.index)).astype(str).str.strip().str.upper()
    if "TAMANHO" in df.columns:
        df["TAMANHO"] = df["TAMANHO"].astype(str).str.strip().apply(_normaliza_tamanho)
    else:
        df["TAMANHO"] = ""
    df["SEMANA"] = df["DATA"].dt.isocalendar().week.astype(int)
    df["MES"] = df["DATA"].dt.month
    return df


@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_iacanga() -> pd.DataFrame:
    content = get_raw(IACANGA_SHEETS_ID, IACANGA_SHEETS_GID, ttl=_TTL)
    if not content:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(content), dtype=str)
    df.columns = df.columns.str.strip()
    if "DATA" not in df.columns or "QUANTIDADE" not in df.columns:
        return pd.DataFrame()
    df["DATA"] = parse_date_series(df["DATA"])
    df = df.dropna(subset=["DATA"])
    df["QUANTIDADE"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    df["ESTACAO"] = (
        df.get("ESTAÇÃO DE CORTE", df.get("ESTACAO", pd.Series(dtype=str)))
        .astype(str).str.strip().apply(_canoniza_estacao_iacanga)
    )
    df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip() if "PRODUTO" in df.columns else ""
    df["OP"] = df.get("OP", pd.Series("SEM OP", index=df.index)).fillna("SEM OP").astype(str).str.strip()
    df["COR"] = df.get("COR", pd.Series("", index=df.index)).astype(str).str.strip().str.upper()
    df["TAMANHO"] = df.get("TAMANHO", pd.Series("", index=df.index)).astype(str).str.strip().apply(_normaliza_tamanho)
    df["GRUPO_ESTACAO"] = df["ESTACAO"].apply(lambda e: (
        "BURDAY"  if "BURDAY" in _norm_text(e) else
        "MAQUINA" if "MAQUINA" in _norm_text(e) or _norm_text(e).startswith("MAQ") else
        "MESA"    if "MESA"   in _norm_text(e) else
        "OUTRO"
    ))
    df["SEMANA"] = df["DATA"].dt.isocalendar().week.astype(int)
    df["MES"] = df["DATA"].dt.month
    return df


@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_lencol() -> pd.DataFrame:
    try:
        from utils.lencol_loader_smart import load_lencol_smart_csv
        df = load_lencol_smart_csv()
        if df.empty:
            return df
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
        df = df[df["DATA"].notna()]
        df["QUANT"] = pd.to_numeric(df["QUANT"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_itaju() -> pd.DataFrame:
    content = get_raw(_ITAJU_ID, _ITAJU_GID, ttl=_TTL)
    if not content:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(content), dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {}
    for c in df.columns:
        cn = _norm_text(c)
        if "DATA" in cn:      col_map[c] = "DATA"
        elif "OP" == cn:      col_map[c] = "OP"
        elif "ESTAC" in cn:   col_map[c] = "ESTACAO"
        elif "COR" == cn:     col_map[c] = "COR"
        elif "QUANT" in cn:   col_map[c] = "QUANTIDADE"
        elif "TAMANHA" in cn or "TAMANHO" in cn: col_map[c] = "TAMANHO"
        elif "PRODUTO" in cn: col_map[c] = "PRODUTO"
    df = df.rename(columns=col_map)
    needed = ["DATA", "OP", "QUANTIDADE", "TAMANHO", "PRODUTO"]
    if any(c not in df.columns for c in needed):
        return pd.DataFrame()
    keep = [c for c in ["DATA", "OP", "ESTACAO", "COR", "QUANTIDADE", "TAMANHO", "PRODUTO"] if c in df.columns]
    df = df[keep].copy()
    df["DATA"] = parse_date_series(df["DATA"], default_order="MDY")
    df["QUANTIDADE"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    df["OP"] = df["OP"].astype(str).str.strip()
    df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip().str.upper()
    df["TAMANHO"] = df["TAMANHO"].astype(str).str.strip().str.upper()
    if "COR" in df.columns:     df["COR"] = df["COR"].astype(str).str.strip().str.upper()
    if "ESTACAO" in df.columns: df["ESTACAO"] = df["ESTACAO"].astype(str).str.strip().str.upper()
    blanks = {"", "NAN", "NONE", "N/A", "NAT"}
    df = df[df["DATA"].notna() & (df["QUANTIDADE"] > 0) & ~df["PRODUTO"].str.upper().isin(blanks)].reset_index(drop=True)
    df["SEMANA"] = df["DATA"].dt.isocalendar().week.astype(int)
    return df


# ── Produção Geral ─────────────────────────────────────────────────────────────

_HEADER_LABELS_PG = frozenset(["FACCAO", "PRODUTO", "META DIARIA", "META MENSAL", "QTDE PRODUZIDA", "FALTA", "CLIENTE"])

def _remove_accents(s: str) -> str:
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode()

def _is_header_row_pg(row_series) -> bool:
    vals = row_series.astype(str).str.upper().tolist()
    for v in vals:
        v_clean = _remove_accents(v.strip())
        if "FACCAO" in v_clean or v.strip() == "PRODUTO":
            return True
    return False

def _parse_sheet_pg(raw: pd.DataFrame, sheet_name: str) -> pd.DataFrame | None:
    header_idx = None
    for i, row in raw.iterrows():
        if _is_header_row_pg(row):
            header_idx = i
            break
    if header_idx is None:
        return None
    df = raw.iloc[header_idx + 1:].copy()
    df.columns = raw.iloc[header_idx].astype(str).str.strip().tolist()
    df = df.reset_index(drop=True)
    df = df.dropna(how="all")

    def _find_col(*keywords):
        for kw in keywords:
            for c in df.columns:
                if _remove_accents(str(c).upper().strip()).replace(" ", "") == _remove_accents(kw).replace(" ", ""):
                    return c
                if _remove_accents(kw) in _remove_accents(str(c).upper()):
                    return c
        return None

    col_data  = _find_col("DATA", "DATA PRODUCAO", "DATA DE PRODUCAO")
    col_fac   = _find_col("FACCAO", "PRESTADOR", "COLABORADOR", "NOME")
    col_prod  = _find_col("PRODUTO")
    col_qtd   = _find_col("QTDE PRODUZIDA", "QUANTIDADE", "QTDE", "TOTAL PRODUZIDO")
    col_meta  = _find_col("META DIARIA", "META DIA", "META")
    col_cli   = _find_col("CLIENTE", "EMPRESA")

    if not col_qtd:
        return None

    records = []
    for _, row in df.iterrows():
        try:
            qtd_raw = str(row[col_qtd]) if col_qtd else ""
            qtd_raw = re.sub(r"[^\d.]", "", qtd_raw.replace(",", "."))
            qtd = int(float(qtd_raw)) if qtd_raw else 0
        except Exception:
            qtd = 0
        if qtd <= 0:
            continue

        data_val = None
        if col_data:
            try:
                data_val = pd.to_datetime(row[col_data], dayfirst=True, errors="coerce")
            except Exception:
                pass

        meta_val = None
        if col_meta:
            try:
                mv = str(row[col_meta]).replace(",", ".").strip()
                meta_val = float(re.sub(r"[^\d.]", "", mv)) if mv else None
            except Exception:
                pass

        records.append({
            "Data":        data_val,
            "Faccao":      str(row[col_fac]).strip() if col_fac else sheet_name,
            "Produto":     str(row[col_prod]).strip() if col_prod else "",
            "Quantidade":  qtd,
            "Meta Diaria": meta_val,
            "Cliente":     str(row[col_cli]).strip() if col_cli else "",
            "Empresa":     sheet_name,
        })

    if not records:
        return None
    result = pd.DataFrame(records)
    result = result[result["Data"].notna()].copy()
    if result.empty:
        return None
    result["Ano"] = result["Data"].dt.year
    result["Mes"] = result["Data"].dt.month
    result["DiaSemana"] = result["Data"].dt.day_name()
    result["Meta Diaria"] = pd.to_numeric(result["Meta Diaria"], errors="coerce")
    return result


@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_producao() -> dict[str, pd.DataFrame]:
    try:
        url = f"https://docs.google.com/spreadsheets/d/{PRODUCAO_SHEETS_ID}/export?format=xlsx"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        xlsx_data = io.BytesIO(r.content)
    except Exception:
        return {}
    try:
        xls = pd.ExcelFile(xlsx_data, engine="openpyxl")
    except Exception:
        return {}

    _NIAZI = {"niazitex", "niazittex", "niazi"}
    all_data: dict[str, pd.DataFrame] = {}
    for sheet in xls.sheet_names:
        if sheet.lower() in {"diversos"} | _NIAZI:
            continue
        try:
            raw = pd.read_excel(xlsx_data, sheet_name=sheet, header=None, engine="openpyxl")
            parsed = _parse_sheet_pg(raw, sheet)
            if parsed is not None and len(parsed) > 0:
                all_data[sheet] = parsed
        except Exception:
            pass
    return all_data


# ── Facções ────────────────────────────────────────────────────────────────────

def _metas_faccoes() -> pd.DataFrame:
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


# ── Cargas ─────────────────────────────────────────────────────────────────────

def _parse_money_cg(s: str) -> float | None:
    s = str(s).strip()
    if not s or "R$" not in s:
        return None
    neg = s.startswith("-")
    clean = re.sub(r"[R$\s\-]", "", s).replace(".", "").replace(",", ".")
    try:
        v = float(clean)
        return -v if neg else v
    except ValueError:
        return None

def _parse_num_cg(s: str) -> float | None:
    s = str(s).strip()
    if not s or s in ("-", "R$", "R$  -", "R$-"):
        return None
    clean = re.sub(r"[R$\s\-]", "", s).replace(".", "").replace(",", ".")
    try:
        v = float(clean)
        return v if v > 0 else None
    except ValueError:
        return None

def _parse_date_cg(s: str) -> date | None:
    raw = str(s).strip()
    sl = raw.lower()
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", sl)
    if m:
        month = _MESES_PT_CARGAS.get(m.group(2))
        if month:
            try:
                return date(int(m.group(4)), month, int(m.group(3)))
            except ValueError:
                pass
    m2 = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$", raw.strip())
    if m2:
        a, b, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            if a > 12: return date(y, b, a)
            elif b > 12: return date(y, a, b)
            else: return date(y, b, a)
        except ValueError:
            pass
    m3 = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", raw.strip())
    if m3:
        try:
            return date(int(m3.group(1)), int(m3.group(2)), int(m3.group(3)))
        except ValueError:
            pass
    return None

def _is_date_str_cg(s: str) -> bool:
    return bool(re.search(r"\d{4}", s)) and any(mes in s.lower() for mes in _MESES_PT_CARGAS)

def _first_frete_cg(row: list[str]) -> float:
    for j in range(5, min(10, len(row))):
        v = _parse_money_cg(row[j])
        if v and abs(v) > 0:
            return abs(v)
    return 0.0

def _fetch_csv_cargas(sheet_name: str) -> list[list[str]]:
    nome_enc = urllib.parse.quote(sheet_name)
    url = (
        f"https://docs.google.com/spreadsheets/d/{_CARGAS_SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={nome_enc}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(raw)))

def _find_resumo_cg(rows: list[list[str]]) -> tuple[float, float]:
    for row in rows:
        if _parse_date_cg(row[1] if len(row) > 1 else ""):
            continue
        big = []
        for cell in row:
            v = _parse_num_cg(str(cell))
            if v and v > 1_500_000:
                big.append(v)
        if len(big) >= 2:
            return (big[0], big[1])
    best = 0.0
    for row in rows:
        if _parse_date_cg(row[1] if len(row) > 1 else ""):
            continue
        for j in range(8, min(16, len(row))):
            v = _parse_money_cg(row[j])
            if not v: continue
            av = abs(v)
            if av <= 1_000_000 or round(av) % 1_000 == 0: continue
            if av > best: best = av
    return (0.0, best)

def _find_painel_col_cg(rows: list[list[str]]) -> int | None:
    """Coluna do painel diário de realizado ("DD-mmm.") — varia por mês na planilha."""
    contagem: Counter = Counter()
    for row in rows:
        for j, cell in enumerate(row):
            if re.match(r'^\s*\d{1,2}\s*[-\.]\s*[a-z]{3}', str(cell).strip().lower()):
                contagem[j] += 1
    if not contagem:
        return None
    return contagem.most_common(1)[0][0]


def _find_painel_col_rotulo_cg(rows: list[list[str]]) -> int | None:
    """Fallback para meses sem cabeçalho 'DD-mmm.' repetido (ex.: Janeiro) — usa o
    rótulo "REALIZADO" na primeira linha; o nome do cliente fica 2 colunas antes."""
    if not rows:
        return None
    for j, cell in enumerate(rows[0]):
        if _norm_text(cell) == "REALIZADO" and j >= 2:
            return j - 2
    return None


def _extract_day_realized_cg(rows: list[list[str]], mes_num: int, ano: int) -> dict:
    day_real: dict = {}
    col = _find_painel_col_cg(rows)

    if col is not None:
        current_date = None
        for row in rows:
            if len(row) <= col: continue
            cell_base = str(row[col]).strip()
            m = re.match(r'^(\d{1,2})\s*[-\.]\s*(\w{3})', cell_base.lower())
            if m:
                try: current_date = date(ano, mes_num, int(m.group(1)))
                except ValueError: current_date = None
                continue
            if not cell_base or 'R$' in cell_base: continue
            if current_date is None or len(row) <= col + 2: continue
            cliente_raw = cell_base.strip().upper()
            v = _parse_num_cg(str(row[col + 2]).strip())
            if v and v > 0 and cliente_raw:
                key = (current_date, _norm_text(cliente_raw))
                day_real[key] = day_real.get(key, 0.0) + v
        return day_real

    col = _find_painel_col_rotulo_cg(rows)
    if col is None:
        return {}
    for row in rows:
        if len(row) <= col + 2: continue
        cliente_raw = str(row[col]).strip().upper()
        if not cliente_raw or 'R$' in cliente_raw: continue
        row_date = _parse_date_cg(row[1]) if len(row) > 1 else None
        if row_date is None: continue
        v = _parse_num_cg(str(row[col + 2]).strip())
        if v and v > 0:
            key = (row_date, _norm_text(cliente_raw))
            day_real[key] = day_real.get(key, 0.0) + v
    return day_real

def _parse_month_cargas(rows: list[list[str]], mes_nome: str, mes_num: int, ano: int) -> list[dict]:
    previsto_mensal, realizado_mensal = _find_resumo_cg(rows)
    day_realized = _extract_day_realized_cg(rows, mes_num, ano)

    def _only_frete_col(r):
        if len(r) <= 6: return False
        return (not any(r[j].strip() for j in range(6)) and bool(r[6].strip())
                and not any(r[j].strip() for j in range(7, len(r))))

    _merged_idx: set[int] = set()
    for _i, _r in enumerate(rows):
        if _parse_date_cg(_r[1] if len(_r) > 1 else ""): continue
        if not (_only_frete_col(_r) and _first_frete_cg(_r)): continue
        _next = rows[_i + 1] if _i + 1 < len(rows) else []
        if _parse_date_cg(_next[1] if len(_next) > 1 else ""):
            _merged_idx.add(_i)

    records = []
    semana_atual = ""
    _last_cargo_date = None
    _last_destino_raw = ""

    for idx, row in enumerate(rows):
        if len(row) < 8: continue
        cell0 = row[0].strip()
        if re.search(r"SEMANA\s+\d{2}/\d{2}", _norm_text(cell0), re.I):
            semana_atual = cell0
            if not _parse_date_cg(row[1] if len(row) > 1 else ""):
                continue
        if "DATA CARREGAMENTO" in _norm_text(row[1] if len(row) > 1 else ""):
            continue
        data_carga = _parse_date_cg(row[1]) if len(row) > 1 else None
        if not data_carga:
            if idx in _merged_idx and _last_cargo_date:
                data_carga = _last_cargo_date
            else:
                continue
        _last_cargo_date = data_carga
        destino = row[2].strip().upper() if len(row) > 2 else ""
        if not destino or destino == "DESTINO":
            if _last_destino_raw:
                destino = _last_destino_raw
            else:
                continue
        else:
            _last_destino_raw = destino
        valor_frete = _first_frete_cg(row)
        cliente = ""
        for i in range(4, min(8, len(row))):
            v = row[i].strip()
            if v and "R$" not in v and not _is_date_str_cg(v) and not re.match(r"^\d+[-/]", v):
                cliente = v.upper(); break
        if not cliente:
            cliente = destino
        local = ""
        for i in range(3, min(7, len(row))):
            v = row[i].strip().upper()
            if v and "R$" not in v and not _is_date_str_cg(v):
                local = v; break
        local_n = _norm_text(local)
        if "IACANGA" in local_n: local_tag = "Iacanga"
        elif "AREALVA" in local_n: local_tag = "Arealva"
        elif "ITAJU" in local_n: local_tag = "Itaju"
        else: local_tag = local_n[:15] if local_n else "N/I"
        status = "Normal"
        obs_raw = ""
        for cell in row[6:15]:
            v = cell.strip().upper()
            if not v or "R$" in v: continue
            if "CANCEL" in v: obs_raw = v; status = "Cancelada"; break
            if any(k in v for k in ["ADIAD", "ADIADO", "ADIADA"]): obs_raw = v; status = "Adiada"; break
            if "ARMAZENAGEM" in v: obs_raw = v; status = "Armazenagem"; break
        records.append({
            "MES":          mes_nome,
            "MES_NUM":      mes_num,
            "ANO":          ano,
            "SEMANA":       semana_atual,
            "DATA":         data_carga,
            "DESTINO":      destino,
            "LOCAL":        local_tag,
            "VALOR_FRETE":  valor_frete,
            "CLIENTE":      cliente,
            "PREVISAO":     0.0 if previsto_mensal > 0 else valor_frete,
            "REALIZADO":    0.0,
            # Painel direito registra 1 realizado por (data, cliente) — não por carga
            # individual; guarda a chave e divide o valor logo abaixo entre todas as
            # cargas do mesmo cliente/dia para não contar em dobro no total.
            "_REAL_KEY": (
                (data_carga, _norm_text(destino)) if (data_carga, _norm_text(destino)) in day_realized
                else (data_carga, _norm_text(cliente)) if (data_carga, _norm_text(cliente)) in day_realized
                else None
            ),
            "REALIZADO_DIA": 0.0,
            "DIFERENCA":    0.0,
            "OBS":          obs_raw,
            "STATUS":       status,
        })

    _contagem_chave = Counter(r["_REAL_KEY"] for r in records if r["_REAL_KEY"] is not None)
    for r in records:
        _chave = r.pop("_REAL_KEY", None)
        if _chave is not None:
            r["REALIZADO_DIA"] = day_realized[_chave] / _contagem_chave[_chave]

    # Reconcilia proporcionalmente com o Realizado oficial da linha-resumo (nem todo
    # lançamento do painel diário casa por nome com uma carga) — mesma lógica de
    # 8_Previsao_Cargas.py, para o relatório não divergir do dashboard.
    _soma_batida = sum(r["REALIZADO_DIA"] for r in records)
    if _soma_batida > 0 and realizado_mensal > 0:
        _fator = realizado_mensal / _soma_batida
        for r in records:
            r["REALIZADO_DIA"] *= _fator

    if realizado_mensal > 0 or previsto_mensal > 0:
        proxy = _last_cargo_date or date(ano, mes_num, 28)
        records.append({
            "MES": mes_nome, "MES_NUM": mes_num, "ANO": ano, "SEMANA": "",
            "DATA": proxy, "DESTINO": mes_nome, "LOCAL": "", "VALOR_FRETE": 0.0,
            "CLIENTE": mes_nome, "PREVISAO": previsto_mensal, "REALIZADO": realizado_mensal,
            "REALIZADO_DIA": 0.0, "DIFERENCA": 0.0, "OBS": "", "STATUS": "CARGO_REAL",
        })
    return records


@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_cargas() -> pd.DataFrame:
    all_records: list[dict] = []
    for mes_nome, mes_num, ano in _MESES_CARGAS:
        try:
            rows = _fetch_csv_cargas(mes_nome)
            records = _parse_month_cargas(rows, mes_nome, mes_num, ano)
            all_records.extend(records)
        except Exception:
            pass
    if not all_records:
        return pd.DataFrame()
    df = pd.DataFrame(all_records)
    df["DATA"] = pd.to_datetime(df["DATA"])
    alias = {"NIAZITEX": "NIAZITEX", "NIAZITTEX": "NIAZITEX", "NC INDUSTRIA": "NIAZITEX"}
    df["DESTINO_NORM"] = df["DESTINO"].apply(lambda x: alias.get(_norm_text(x), _norm_text(x)))
    df["CLIENTE_NORM"] = df["CLIENTE"].apply(lambda x: alias.get(_norm_text(x), _norm_text(x)))
    meses_com_real = set(df.loc[df["STATUS"] == "CARGO_REAL", "MES"].tolist())
    df["TEM_REALIZADO"] = df["MES"].isin(meses_com_real) & (df["STATUS"] != "CARGO_REAL")
    return df


# ── Carteira de Pedidos ────────────────────────────────────────────────────────

def _parse_float_cart(s: str) -> float:
    try:
        s = re.sub(r'[^\d,.\-]', '', str(s).strip())
        if not s: return 0.0
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."): s = s.replace(".", "").replace(",", ".")
            else: s = s.replace(",", "")
        elif "," in s: s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0

def _parse_date_cart(s: str) -> date | None:
    s = str(s).strip()
    try:
        parts = s.split("/")
        if len(parts) == 3:
            m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 100: y += 2000
            if 1900 < y < 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                return date(y, m, d)
    except Exception:
        pass
    return None

def _categorizar_cart(desc: str) -> str:
    d = _norm_text(desc)
    if any(k in d for k in ["LENCOL", "LRNCOL", "JG CAMA", "JG LENCOL", "JOGO DE CAMA"]): return "LENÇOL"
    if re.match(r"^JC[A-Z0-9]*\s", d): return "LENÇOL"
    if any(k in d for k in ["FRONHA", "PORTA TRAV", "SAIA BOX"]): return "FRONHA / ACESSÓRIOS"
    if "CORTINA" in d or re.search(r"CORT[.\s]", d): return "CORTINA"
    if "COLCHA" in d: return "COLCHA"
    if "COBERTOR" in d or re.search(r"\bCOBER", d): return "COBERTOR"
    if "MANTA" in d: return "MANTA"
    if "ALMOFADA" in d: return "ALMOFADA"
    if "TOALHA" in d: return "TOALHA"
    return "OUTROS"

@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_carteira() -> pd.DataFrame:
    url = (f"https://docs.google.com/spreadsheets/d/{_CARTEIRA_SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&gid={_CARTEIRA_GID}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except Exception:
        return pd.DataFrame()
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows: return pd.DataFrame()
    records = []
    for row in rows[1:]:
        if len(row) < 11 or not row[0].strip(): continue
        dt = _parse_date_cart(row[0])
        if dt is None: continue
        qt = _parse_float_cart(row[8])
        vt = _parse_float_cart(row[10])
        if qt <= 0 and vt <= 0: continue
        desc = row[14].strip() if len(row) > 14 else ""
        dest = row[4].strip()
        mun  = row[5].strip() if len(row) > 5 else ""
        me   = re.search(r"-([A-Z]{2})$", mun)
        records.append({
            "DATA": dt, "PEDIDO": row[2].strip(), "NOTA": row[1].strip(),
            "DESTINATARIO": dest, "MUNICIPIO": mun, "ESTADO": me.group(1) if me else "N/I",
            "VENDEDOR": row[7].strip() if len(row) > 7 else "",
            "QUANTIDADE": qt, "VALOR_UNIT": _parse_float_cart(row[9]),
            "VALOR_TOTAL": vt, "COD_PROD": row[12].strip() if len(row) > 12 else "",
            "DESCRICAO": desc, "CATEGORIA": _categorizar_cart(desc),
        })
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records)
    df["DATA"] = pd.to_datetime(df["DATA"])
    df["ANO"] = df["DATA"].dt.year
    df["MES"] = df["DATA"].dt.month
    df["ANO_MES"] = df["DATA"].dt.to_period("M").astype(str)
    _alias_cli = {"NC INDUSTRIA E COMERCIO TEXTEIS LTDA": "NIAZITTEX",
                  "NC INDUSTRIA E COMERCIO TEXTEIS": "NIAZITTEX"}
    df["CLIENTE"] = df["DESTINATARIO"].apply(lambda x: _alias_cli.get(x.upper(), x))
    def _nome_curto(n):
        n = n.upper()
        mapa = {"SULTAN":"SULTAN","VESTIS":"VESTIS","CAMESA":"CAMESA","BURDAYS":"BURDAYS",
                "NC INDUSTRIA":"NIAZITTEX","NIAZITTEX":"NIAZITTEX","FATEX":"FATEX",
                "SEVEN":"SEVEN","OLIVEIRA":"OLIVEIRA","VIANELLI":"VIANELLI","MARCELINO":"MARCELINO"}
        for k, v in mapa.items():
            if k in n: return v
        return n.split()[0][:12]
    df["CLIENTE_CURTO"] = df["CLIENTE"].apply(_nome_curto)
    return df


# ── Programação ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=_TTL, show_spinner=False)
def _dados_programacao() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (df_programacao, df_cortes_agregados)."""
    # Programação
    texto_prog = get_raw(_PROG_ID, _PROG_GID, ttl=_TTL)
    df_prog = pd.DataFrame()
    if texto_prog:
        linhas = texto_prog.splitlines()
        header_row = 0
        for i, linha in enumerate(linhas[:10]):
            if "SEMANA" in linha.upper() and "CLIENTE" in linha.upper():
                header_row = i; break
        df_prog = pd.read_csv(io.StringIO(texto_prog), skiprows=header_row, header=0, dtype=str)
        df_prog.columns = df_prog.columns.str.strip()
        col_map = {c.upper().strip(): c for c in df_prog.columns}
        for col in ["PED. CLIENTE", "SEMANA", "CLIENTE", "LOCAL", "PRODUTO", "QNT. PROG", "OP INTERNA"]:
            real = col_map.get(col.upper(), col)
            if real not in df_prog.columns: df_prog[col] = ""
            elif real != col: df_prog[col] = df_prog[real]
        df_prog["PED. CLIENTE"] = df_prog["PED. CLIENTE"].astype(str).str.strip()
        df_prog["QNT. PROG"] = pd.to_numeric(df_prog["QNT. PROG"], errors="coerce").fillna(0).astype(int)
        invalidos = {"", "NAN", "NONE", "N/A"}
        def _valido(serie):
            s = serie.astype(str).str.strip()
            return s.ne("") & ~s.str.upper().isin(invalidos)
        ped_valido = _valido(df_prog["PED. CLIENTE"])
        if "OP INTERNA" in df_prog.columns:
            usar_opint = ~ped_valido & _valido(df_prog["OP INTERNA"])
            df_prog.loc[usar_opint, "PED. CLIENTE"] = df_prog.loc[usar_opint, "OP INTERNA"].astype(str).str.strip()
        ped_valido = _valido(df_prog["PED. CLIENTE"])
        df_prog = df_prog[ped_valido | (df_prog["QNT. PROG"] > 0)].reset_index(drop=True)
        df_prog["_CHAVE"] = df_prog["PED. CLIENTE"]

    # Cortes (manta + iacanga + lençol)
    frames = []
    for sid, gid, fonte, col_qtd in [
        (CORTE_SHEETS_ID, CORTE_SHEETS_GID, "Zanattex", "QUANTIDADE"),
        (IACANGA_SHEETS_ID, IACANGA_SHEETS_GID, "Giattex", "QUANTIDADE"),
    ]:
        texto = get_raw(sid, gid, ttl=_TTL)
        if not texto: continue
        try:
            sub = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
            sub.columns = sub.columns.str.strip()
            if "OP" not in sub.columns or col_qtd not in sub.columns: continue
            df_s = sub[["OP", col_qtd]].copy().rename(columns={col_qtd: "QUANTIDADE"})
            df_s["FONTE"] = fonte
            if "DATA" in sub.columns:
                datas = parse_date_series(sub["DATA"])
                df_s["SEMANA"] = datas.dt.isocalendar().week.astype("Int64")
                df_s["DATA"] = datas
            else:
                df_s["SEMANA"] = pd.array([pd.NA] * len(df_s), dtype="Int64")
                df_s["DATA"] = pd.NaT
            frames.append(df_s)
        except Exception:
            pass
    # Lençol prog
    texto_ln = get_raw(_LENCOL_PROG_ID, _LENCOL_PROG_GID, ttl=_TTL)
    if texto_ln:
        try:
            sub_ln = pd.read_csv(io.StringIO(texto_ln), header=0, dtype=str)
            sub_ln.columns = sub_ln.columns.str.strip()
            col_op_ln = next((c for c in sub_ln.columns if "OP" in c.upper()), None)
            col_qt_ln = next((c for c in sub_ln.columns if "QUANT" in c.upper() or c.upper() == "QUANT"), None)
            col_dt_ln = next((c for c in sub_ln.columns if "DATA" in c.upper()), None)
            if col_op_ln and col_qt_ln:
                df_ln = sub_ln[[col_op_ln, col_qt_ln]].copy().rename(columns={col_op_ln: "OP", col_qt_ln: "QUANTIDADE"})
                df_ln["FONTE"] = "Lencol"
                if col_dt_ln:
                    datas = parse_date_series(sub_ln[col_dt_ln])
                    df_ln["SEMANA"] = datas.dt.isocalendar().week.astype("Int64")
                    df_ln["DATA"] = datas
                else:
                    df_ln["SEMANA"] = pd.array([pd.NA] * len(df_ln), dtype="Int64")
                    df_ln["DATA"] = pd.NaT
                frames.append(df_ln)
        except Exception:
            pass

    if not frames:
        return df_prog, pd.DataFrame()
    df_cortes = pd.concat(frames, ignore_index=True)
    df_cortes["OP"] = df_cortes["OP"].fillna("").astype(str).str.strip()
    df_cortes["QUANTIDADE"] = pd.to_numeric(df_cortes["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    df_cortes = df_cortes[df_cortes["OP"].ne("") & (df_cortes["QUANTIDADE"] > 0)]

    return df_prog, df_cortes


def _calcular_df_agg(df_prog: pd.DataFrame, df_cortes: pd.DataFrame):
    """Agrega programação vs corte e retorna (df_agg, KPIs).

    Reaproveita utils.controle_op.enriquecer/agregar_por_op — mesma lógica
    usada ao vivo em pages/4_Controladoria_Programacao.py, em vez de uma
    reimplementação própria (que tinha divergido: limiar de 100% aqui contra
    96% lá para status 'Concluído')."""
    if df_prog.empty:
        return pd.DataFrame(), 0, 0, 0, 0, 0.0, 0, 0

    from utils.controle_op import enriquecer, agregar_por_op
    df_agg = agregar_por_op(enriquecer(df_prog, df_cortes))

    total_ops  = len(df_agg)
    concluidas = (df_agg["STATUS_CORTE"] == "Concluído").sum()
    parciais   = (df_agg["STATUS_CORTE"] == "Parcial").sum()
    pendentes  = (df_agg["STATUS_CORTE"] == "Pendente").sum()
    aderencia  = round(concluidas / total_ops * 100, 1) if total_ops > 0 else 0.0
    total_prog = int(df_agg["QNT_PROG_TOTAL"].sum())
    total_cort = int(df_agg["QNT_CORTADA"].sum())

    return df_agg, total_ops, int(concluidas), int(parciais), int(pendentes), aderencia, total_prog, total_cort


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT — TABS
# ══════════════════════════════════════════════════════════════════════════════

_today = date.today()
_mes_ini = _today.replace(day=1)
_mes_fim = _today.replace(day=monthrange(_today.year, _today.month)[1])

tab_corte, tab_prod, tab_interno, tab_cargas, tab_pedidos, tab_prog = st.tabs([
    "✂️ Corte", "🏭 Produção Geral", "👥 Colaboradores Internos", "🚛 Cargas",
    "📦 Carteira de Pedidos", "📋 Programação",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB — CORTE
# ══════════════════════════════════════════════════════════════════════════════
with tab_corte:
    st.markdown("### ✂️ Relatórios de Corte")
    st.markdown("Escolha o relatório abaixo — o período aparece sempre no card seguinte.")

    _OPCOES_CORTE = {
        "📋 Consolidado": (
            "Idêntico ao PDF enviado automaticamente por e-mail: Manta Arealva + Manta Iacanga + "
            "Lençol Arealva, em 3 seções (Dia / Mês Atual / Últimos 2 Meses)."
        ),
        "🧵 Arealva Manta": "Relatório detalhado do corte Arealva Manta.",
        "🧶 Iacanga Manta": "Relatório detalhado do corte Iacanga.",
        "🛏️ Lençol Arealva": "Relatório detalhado do corte de lençol.",
        "🪡 Itaju (Ponto Palito)": "Relatório detalhado do corte Itaju.",
    }
    _tipo_corte = st.segmented_control(
        "Tipo de relatório", list(_OPCOES_CORTE.keys()),
        default="📋 Consolidado", key="tipo_corte",
    )
    _tipo_corte = _tipo_corte or "📋 Consolidado"
    st.caption(_OPCOES_CORTE[_tipo_corte])

    with st.container(border=True):
        if _tipo_corte == "📋 Consolidado":
            st.markdown("📅 **Período**")
            st.caption(
                "As seções 'Mês Atual' e 'Últimos 2 Meses' sempre usam a Data Final como "
                "referência — só a seção 1 muda: dia único vira detalhado, período vira resumo."
            )
            _ci_cc, _cf_cc = st.columns(2)
            with _ci_cc:
                _ini_cc = st.date_input(
                    "Data Inicial", value=date.today() - timedelta(days=1),
                    format="DD/MM/YYYY", key="ini_cc",
                )
            with _cf_cc:
                _dia_cc = st.date_input(
                    "Data Final", value=date.today() - timedelta(days=1),
                    format="DD/MM/YYYY", key="dia_cc",
                )
            if st.button("📄 Gerar Corte Consolidado", key="btn_cc", type="primary"):
                with st.spinner("Carregando dados e gerando PDF…"):
                    try:
                        from scripts.relatorio_diario_corte import gerar_pdf_consolidado as _gerar_pdf_consolidado_email
                        _bytes_cc = _gerar_pdf_consolidado_email(_dia_cc, dia_ini=_ini_cc)
                        st.session_state["pdf_cc_bytes"] = _bytes_cc
                        st.session_state["pdf_cc_nome"] = f"relatorio_consolidado_{_dia_cc.strftime('%d-%m-%Y')}.pdf"
                        st.success("PDF gerado! Clique em Baixar.")
                    except Exception as _e:
                        st.error(f"Erro ao gerar PDF: {_e}")
            if st.session_state.get("pdf_cc_bytes"):
                st.download_button("⬇️ Baixar PDF Consolidado", data=st.session_state["pdf_cc_bytes"],
                    file_name=st.session_state.get("pdf_cc_nome", "corte_consolidado.pdf"),
                    mime="application/pdf", key="dl_cc")

        else:
            st.markdown("📅 **Período**")
            _ci, _cf = st.columns(2)
            with _ci:
                _ini_corte = st.date_input("Data Inicial", value=_mes_ini, format="DD/MM/YYYY", key="ini_corte")
            with _cf:
                _fim_corte = st.date_input("Data Final", value=_mes_fim, format="DD/MM/YYYY", key="fim_corte")

            if _tipo_corte == "🧵 Arealva Manta":
                if st.button("📄 Gerar Arealva Manta", key="btn_am", type="primary"):
                    with st.spinner("Gerando PDF…"):
                        try:
                            _df_am = _dados_arealva()
                            _df_am_f = _df_am[(_df_am["DATA"].dt.date >= _ini_corte) & (_df_am["DATA"].dt.date <= _fim_corte)]
                            _bytes_am = gerar_pdf_arealva_manta(
                                df=_df_am_f,
                                ini=_ini_corte,
                                fim=_fim_corte,
                                meta_total=_METAS_AREALVA_META_TOTAL,
                                metas=_METAS_AREALVA_FLAT,
                                filtros_texto="",
                            )
                            st.session_state["pdf_am_bytes"] = _bytes_am
                            st.session_state["pdf_am_nome"] = nome_arquivo_pdf("arealva_manta", _ini_corte, _fim_corte)
                            st.success("PDF gerado!")
                        except Exception as _e:
                            st.error(f"Erro: {_e}")
                if st.session_state.get("pdf_am_bytes"):
                    st.download_button("⬇️ Baixar Arealva Manta PDF", data=st.session_state["pdf_am_bytes"],
                        file_name=st.session_state.get("pdf_am_nome", "arealva_manta.pdf"),
                        mime="application/pdf", key="dl_am")

            elif _tipo_corte == "🧶 Iacanga Manta":
                if st.button("📄 Gerar Iacanga Manta", key="btn_iac", type="primary"):
                    with st.spinner("Gerando PDF…"):
                        try:
                            _df_iac_full = _dados_iacanga()
                            _df_iac = _df_iac_full[(_df_iac_full["DATA"].dt.date >= _ini_corte) & (_df_iac_full["DATA"].dt.date <= _fim_corte)]
                            _meta_iac_total = sum(v.get("CASAL", 0) for v in _METAS_IACANGA.values())
                            _bytes_iac = gerar_pdf_iacanga_manta(
                                df=_df_iac,
                                ini=_ini_corte,
                                fim=_fim_corte,
                                meta_total=_meta_iac_total,
                                metas_por_grupo=_METAS_IACANGA,
                                filtros_texto="",
                            )
                            st.session_state["pdf_iac_bytes"] = _bytes_iac
                            st.session_state["pdf_iac_nome"] = nome_arquivo_pdf("iacanga_manta", _ini_corte, _fim_corte)
                            st.success("PDF gerado!")
                        except Exception as _e:
                            st.error(f"Erro: {_e}")
                if st.session_state.get("pdf_iac_bytes"):
                    st.download_button("⬇️ Baixar Iacanga Manta PDF", data=st.session_state["pdf_iac_bytes"],
                        file_name=st.session_state.get("pdf_iac_nome", "iacanga_manta.pdf"),
                        mime="application/pdf", key="dl_iac")

            elif _tipo_corte == "🛏️ Lençol Arealva":
                if st.button("📄 Gerar Lençol", key="btn_ln", type="primary"):
                    with st.spinner("Gerando PDF…"):
                        try:
                            _df_ln_full = _dados_lencol()
                            _df_ln = _df_ln_full[
                                (_df_ln_full["DATA"].dt.date >= _ini_corte) &
                                (_df_ln_full["DATA"].dt.date <= _fim_corte)
                            ].copy()
                            # Caseamento Jogo Duplo × Fundo (mesma lógica do dashboard, via
                            # utils/lencol_caseamento) — sem isso os KPIs de Jogos/Fundos
                            # do PDF ficam sempre zerados.
                            _tipos_jf_ln, _ = _lencol_tipos_tams(_df_ln)
                            _df_ln_jf = _df_ln.assign(_TIPO_JF=_tipos_jf_ln)
                            _total_pecas_ln = int(_df_ln["QUANT"].sum())
                            _total_fundos_ln = int(_df_ln_jf.loc[_df_ln_jf["_TIPO_JF"] == "FUNDO", "QUANT"].sum())
                            _total_jogos_duplo_ln = int(_df_ln_jf.loc[_df_ln_jf["_TIPO_JF"] == "JOGO_DUPLO", "QUANT"].sum())
                            _casea_ln = lencol_caseamento(_df_ln)
                            _bytes_ln = gerar_pdf_lencol(
                                df=_df_ln,
                                ini=_ini_corte,
                                fim=_fim_corte,
                                filtros_texto="",
                                caseamento_df=_casea_ln,
                                totais_jf={
                                    "total_fundos": _total_fundos_ln,
                                    "total_sem_fundo": _total_pecas_ln - _total_fundos_ln,
                                    "total_jogos_duplo": _total_jogos_duplo_ln,
                                },
                            )
                            st.session_state["pdf_ln_bytes"] = _bytes_ln
                            st.session_state["pdf_ln_nome"] = nome_arquivo_pdf("lencol", _ini_corte, _fim_corte)
                            st.success("PDF gerado!")
                        except Exception as _e:
                            st.error(f"Erro: {_e}")
                if st.session_state.get("pdf_ln_bytes"):
                    st.download_button("⬇️ Baixar Lençol PDF", data=st.session_state["pdf_ln_bytes"],
                        file_name=st.session_state.get("pdf_ln_nome", "lencol.pdf"),
                        mime="application/pdf", key="dl_ln")

            elif _tipo_corte == "🪡 Itaju (Ponto Palito)":
                _obs_it = st.text_area(
                    "OBS (opcional, aparece em destaque no topo do PDF)",
                    value="",
                    placeholder="Ex.: Estão sem OS liberada para corte — no momento a equipe está apenas "
                                 "fazendo aproveitamento de sobras, aguardando a liberação dos próximos lotes.",
                    key="obs_itaju",
                )
                if st.button("📄 Gerar Itaju", key="btn_it", type="primary"):
                    with st.spinner("Gerando PDF…"):
                        try:
                            _df_it_full = _dados_itaju()
                            _df_it = _df_it_full[
                                (_df_it_full["DATA"].dt.date >= _ini_corte) & (_df_it_full["DATA"].dt.date <= _fim_corte)
                            ] if not _df_it_full.empty else _df_it_full
                            _bytes_it = gerar_pdf_itaju(
                                df=_df_it,
                                ini=_ini_corte,
                                fim=_fim_corte,
                                filtros_texto="",
                                obs_texto=_obs_it.strip(),
                            )
                            st.session_state["pdf_it_bytes"] = _bytes_it
                            st.session_state["pdf_it_nome"] = nome_arquivo_pdf("itaju", _ini_corte, _fim_corte)
                            st.success("PDF gerado!")
                        except Exception as _e:
                            st.error(f"Erro: {_e}")
                if st.session_state.get("pdf_it_bytes"):
                    st.download_button("⬇️ Baixar Itaju PDF", data=st.session_state["pdf_it_bytes"],
                        file_name=st.session_state.get("pdf_it_nome", "itaju.pdf"),
                        mime="application/pdf", key="dl_it")


# ══════════════════════════════════════════════════════════════════════════════
# TAB — PRODUÇÃO GERAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_prod:
    st.markdown("### 🏭 Relatório de Produção")
    st.markdown(
        "Relatório de produção x meta x período — indicador principal é Facção x Meta, "
        "com histórico unificado (planilha antiga + facções, mesmas correções do dashboard ao vivo)."
    )

    from utils.producao_unificada import load_producao_unificada
    _all_data_legado_pg = _dados_producao()
    with st.spinner("Carregando lista de facções…"):
        _df_unif_pg_full = load_producao_unificada(_all_data_legado_pg)
    _faccoes_disp_pg = (
        sorted(_df_unif_pg_full["FACCAO"].unique()) if not _df_unif_pg_full.empty else []
    )

    with st.container(border=True):
        st.markdown("📅 **Período**")
        _ci_pg, _cf_pg = st.columns(2)
        with _ci_pg:
            _ini_pg = st.date_input("Data Inicial", value=_mes_ini, format="DD/MM/YYYY", key="ini_pg")
        with _cf_pg:
            _fim_pg = st.date_input("Data Final", value=_mes_fim, format="DD/MM/YYYY", key="fim_pg")

        _sel_faccoes_pg = st.multiselect(
            "Facção / Empresa", _faccoes_disp_pg, placeholder="Todas", key="faccoes_pg",
        )

        if st.button("📄 Gerar Relatório de Produção", key="btn_pg", type="primary"):
            with st.spinner("Carregando dados de produção… pode levar alguns segundos."):
                try:
                    from utils.faccoes_metas_calc import calcular_meta_faccoes

                    if _df_unif_pg_full.empty:
                        st.error("Nenhum dado de produção disponível. Verifique a conexão com a planilha.")
                    else:
                        _df_mes_pg = _df_unif_pg_full[
                            (_df_unif_pg_full["DATA"].dt.date >= _ini_pg) & (_df_unif_pg_full["DATA"].dt.date <= _fim_pg)
                        ].copy()
                        if _sel_faccoes_pg:
                            _df_mes_pg = _df_mes_pg[_df_mes_pg["FACCAO"].isin(_sel_faccoes_pg)]
                        if _df_mes_pg.empty:
                            st.warning("Nenhuma produção no período/facções selecionados.")
                        else:
                            _mes_sel_pg = _ini_pg.month
                            _ano_sel_pg = _ini_pg.year

                            # Meta por facção (ponderada por produto/cliente + dias reais de
                            # produção) — mesma conta do dashboard unificado (pages/2_Producao_Geral.py),
                            # via utils/faccoes_metas_calc, para o relatório nunca divergir da tela.
                            _calc_pg = calcular_meta_faccoes(
                                _df_mes_pg[["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"]],
                                _ano_sel_pg, _mes_sel_pg,
                            )
                            _rank_df_pg = _calc_pg["rank_df"]
                            _meta_mes_total_pg = _calc_pg["meta_mes_total"]
                            _meta_dia_total_pg = _calc_pg["meta_dia_total"]
                            _total_mes_pg = int(_df_mes_pg["QUANTIDADE"].sum())

                            _fim_ref_pg = min(_today, _fim_pg)
                            _du_passados_pg = (
                                contar_dias_uteis(_ini_pg, _fim_ref_pg) if _fim_ref_pg >= _ini_pg else 0
                            )
                            _esperado_pg = _du_passados_pg * _meta_dia_total_pg
                            _pct_mes_pg   = _total_mes_pg / _meta_mes_total_pg * 100 if _meta_mes_total_pg > 0 else 0
                            _pct_ritmo_pg = _total_mes_pg / _esperado_pg * 100 if _esperado_pg > 0 else 0

                            # Monta tabela por (produto, empresa, facção)
                            _df_mes_pg["PRODUTO_N"] = _df_mes_pg["PRODUTO"].apply(normalize_text)
                            _df_mes_pg["CLIENTE_N"] = _df_mes_pg["CLIENTE"].apply(normalize_text)
                            _df_mes_pg["FACCAO_N"]  = _df_mes_pg["FACCAO"].apply(normalize_text)
                            _prod_pg = (
                                _df_mes_pg.groupby(["PRODUTO_N","CLIENTE_N","FACCAO_N","PRODUTO","CLIENTE","FACCAO"])
                                .agg(QUANTIDADE=("QUANTIDADE","sum")).reset_index()
                            )

                            _goals_pg = _metas_faccoes()
                            if not _goals_pg.empty:
                                _metas_pg_df = _goals_pg[["PRODUTO_N","CLIENTE_N","FACCAO_N","META_MES"]].copy()
                                _merged_pg = _prod_pg.merge(_metas_pg_df, on=["PRODUTO_N","CLIENTE_N","FACCAO_N"], how="left")
                                _merged_pg["META_MES"] = _merged_pg["META_MES"].fillna(0).astype(int)
                            else:
                                _merged_pg = _prod_pg.copy()
                                _merged_pg["META_MES"] = 0

                            _merged_pg["Pct_Meta"] = _merged_pg.apply(
                                lambda r: round(r["QUANTIDADE"]/r["META_MES"]*100, 1) if r["META_MES"] > 0 else None, axis=1
                            )
                            _merged_pg["Restante"] = _merged_pg.apply(
                                lambda r: max(0, r["META_MES"] - r["QUANTIDADE"]) if r["META_MES"] > 0 else None, axis=1
                            )
                            _tabela_pg = _merged_pg[["PRODUTO","CLIENTE","FACCAO","QUANTIDADE","META_MES","Pct_Meta","Restante"]].copy()
                            _tabela_pg.columns = ["Produto","Empresa","Faccao","Produzido","Meta Mes","% Meta","Restante"]
                            _tabela_pg["Meta Mes"] = _tabela_pg["Meta Mes"].replace(0, None)

                            _filtros_txt_pg = (
                                f"Facção(ões): {', '.join(_sel_faccoes_pg)}" if _sel_faccoes_pg else ""
                            )
                            _bytes_pg = gerar_pdf_faccoes(
                                tabela=_tabela_pg,
                                df_mes=_df_mes_pg,
                                total_mes=_total_mes_pg,
                                meta_mes_total=_meta_mes_total_pg,
                                pct_mes=_pct_mes_pg,
                                pct_ritmo=_pct_ritmo_pg,
                                meta_dia_total=_meta_dia_total_pg,
                                data_ini=_ini_pg,
                                data_fim=_fim_pg,
                                filtros_texto=_filtros_txt_pg,
                                rank_df=_rank_df_pg,
                            )
                            st.session_state["pdf_pg_bytes"] = _bytes_pg
                            if 1 <= len(_sel_faccoes_pg) <= 3:
                                _slug_pg = "_".join(
                                    normalize_text(f).replace(" ", "_") for f in _sel_faccoes_pg
                                )
                                _dashboard_slug_pg = f"producao_{_slug_pg}"
                            else:
                                _dashboard_slug_pg = "producao"
                            st.session_state["pdf_pg_nome"] = nome_arquivo_pdf(_dashboard_slug_pg, _ini_pg, _fim_pg)
                            st.success("PDF gerado!")
                except Exception as _e:
                    st.error(f"Erro ao gerar PDF: {_e}")

        if st.session_state.get("pdf_pg_bytes"):
            st.download_button("⬇️ Baixar Produção PDF", data=st.session_state["pdf_pg_bytes"],
                file_name=st.session_state.get("pdf_pg_nome", "producao.pdf"),
                mime="application/pdf", key="dl_pg", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB — FACÇÕES
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB — COLABORADORES INTERNOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_interno:
    st.markdown("### 👥 Relatório de Colaborador Interno")
    st.markdown(
        "Produção individual de um colaborador interno (LITTEX / GGTTEX), por período — "
        "mesmo relatório usado no dashboard 'Por Colaborador → Interno'."
    )

    from utils.producao_interno_loader import load_interno_unidade
    from utils.pdf_report import gerar_pdf_colaborador
    from config.settings import PRODUCAO_INTERNO_SHEETS

    _unidades_int = list(PRODUCAO_INTERNO_SHEETS.keys())
    _rotulos_int = [PRODUCAO_INTERNO_SHEETS[k]["label"] for k in _unidades_int]

    with st.container(border=True):
        _unidade_lbl_int = st.selectbox("Unidade", _rotulos_int, key="unidade_int")
        _chave_int = _unidades_int[_rotulos_int.index(_unidade_lbl_int)]

        with st.spinner("Carregando colaboradores…"):
            _df_int_full = load_interno_unidade(_chave_int)

        if _df_int_full.empty:
            st.warning("⚠️ Sem dados disponíveis para essa unidade.")
        else:
            _dmin_int = _df_int_full["DATA"].min().date()
            _dmax_int = _df_int_full["DATA"].max().date()

            _colab_disp_int = sorted(_df_int_full["COLABORADOR"].unique())
            _colab_sel_int = st.selectbox("Colaborador", _colab_disp_int, key="colab_int")

            _ci_int, _cf_int = st.columns(2)
            with _ci_int:
                _ini_int = st.date_input("Data Inicial", value=_dmin_int, min_value=_dmin_int,
                                          max_value=_dmax_int, format="DD/MM/YYYY", key="ini_int")
            with _cf_int:
                _fim_int = st.date_input("Data Final", value=_dmax_int, min_value=_dmin_int,
                                          max_value=_dmax_int, format="DD/MM/YYYY", key="fim_int")

            if st.button("📄 Gerar Relatório do Colaborador", key="btn_int", type="primary"):
                if _ini_int > _fim_int:
                    st.error("A data inicial não pode ser maior que a final.")
                else:
                    with st.spinner("Gerando PDF…"):
                        try:
                            _mask_int = (
                                (_df_int_full["COLABORADOR"] == _colab_sel_int)
                                & (_df_int_full["DATA"].dt.date >= _ini_int)
                                & (_df_int_full["DATA"].dt.date <= _fim_int)
                            )
                            _df_colab_int = _df_int_full[_mask_int].copy()
                            if _df_colab_int.empty:
                                st.warning("Nenhum registro desse colaborador no período selecionado.")
                            else:
                                _bytes_int = gerar_pdf_colaborador(
                                    df_colab=_df_colab_int,
                                    colaborador=_colab_sel_int,
                                    unidade_label=PRODUCAO_INTERNO_SHEETS[_chave_int]["label"],
                                    data_ini=_ini_int,
                                    data_fim=_fim_int,
                                )
                                st.session_state["pdf_int_bytes"] = _bytes_int
                                _slug_int = normalize_text(_colab_sel_int).replace(" ", "_")
                                st.session_state["pdf_int_nome"] = nome_arquivo_pdf(
                                    f"colaborador_{_chave_int.lower()}_{_slug_int}", _ini_int, _fim_int
                                )
                                st.success("PDF gerado!")
                        except Exception as _e:
                            st.error(f"Erro ao gerar PDF: {_e}")

        if st.session_state.get("pdf_int_bytes"):
            st.download_button("⬇️ Baixar Relatório do Colaborador", data=st.session_state["pdf_int_bytes"],
                file_name=st.session_state.get("pdf_int_nome", "relatorio_colaborador.pdf"),
                mime="application/pdf", key="dl_int", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB — CARGAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_cargas:
    st.markdown("### 🚛 Relatório de Previsão de Cargas")
    st.markdown("Comparativo previsão vs. realizado por mês e destino.")

    with st.container(border=True):
        st.markdown("📅 **Período**")
        _meses_disp_cg = [m[0] for m in _MESES_CARGAS]
        _sel_meses_cg = st.multiselect("Meses", _meses_disp_cg, default=_meses_disp_cg, key="sel_mes_cg")
        if not _sel_meses_cg:
            _sel_meses_cg = _meses_disp_cg

        if st.button("📄 Gerar Relatório de Cargas", key="btn_cg", type="primary"):
            with st.spinner("Carregando dados de cargas… pode levar alguns segundos."):
                try:
                    _df_raw_cg = _dados_cargas()
                    if _df_raw_cg.empty:
                        st.error("Dados de cargas não disponíveis.")
                    else:
                        _df_cg_f = _df_raw_cg[_df_raw_cg["MES"].isin(_sel_meses_cg)]
                        _df_cargos_cg = _df_cg_f[_df_cg_f["STATUS"] != "CARGO_REAL"]
                        _df_realizados_cg = _df_cg_f[_df_cg_f["STATUS"] == "CARGO_REAL"]

                        _total_prev_cg = float(_df_cargos_cg["PREVISAO"].sum()) + float(_df_realizados_cg["PREVISAO"].sum())
                        _total_real_cg = float(_df_realizados_cg["REALIZADO"].sum())
                        _dif_cg = _total_real_cg - _total_prev_cg
                        _meses_c_real = _df_realizados_cg["MES"].nunique()
                        _adh_cg = (_total_real_cg / _total_prev_cg * 100) if (_total_prev_cg > 0 and _meses_c_real > 0) else 0.0
                        _n_canc_cg = int((_df_cargos_cg["STATUS"] == "Cancelada").sum())
                        _n_adi_cg  = int((_df_cargos_cg["STATUS"] == "Adiada").sum())
                        _n_cli_cg  = int(_df_cargos_cg["DESTINO_NORM"].nunique()) if "DESTINO_NORM" in _df_cargos_cg.columns else 0

                        _mes_nums = {m[0]: m[1] for m in _MESES_CARGAS}
                        _df_mes_cg_rows = []
                        for _mes in _sel_meses_cg:
                            _mn = _mes_nums.get(_mes, 0)
                            _df_m = _df_cg_f[_df_cg_f["MES"] == _mes]
                            _prev_m = float(_df_m[_df_m["STATUS"] != "CARGO_REAL"]["PREVISAO"].sum())
                            _real_row = _df_m[_df_m["STATUS"] == "CARGO_REAL"]
                            _real_m = float(_real_row["REALIZADO"].sum()) if not _real_row.empty else 0.0
                            if _real_row.empty and not _df_m[_df_m["STATUS"] != "CARGO_REAL"].empty:
                                _prev_official = float(_df_m[_df_m["STATUS"] == "CARGO_REAL"]["PREVISAO"].sum())
                                if _prev_official > 0:
                                    _prev_m = _prev_official
                            _adh_m = (_real_m / _prev_m * 100) if _prev_m > 0 else 0.0
                            _df_mes_cg_rows.append({"MES": _mes, "MES_NUM": _mn,
                                "PREVISAO": _prev_m, "REALIZADO": _real_m,
                                "ADERENCIA": _adh_m, "DIFERENCA": _real_m - _prev_m})
                        _df_mes_cg = pd.DataFrame(_df_mes_cg_rows)

                        _bytes_cg = gerar_pdf_previsao_cargas(
                            df_cargos=_df_cargos_cg,
                            df_realizados=_df_realizados_cg,
                            df_mes=_df_mes_cg,
                            total_prev=_total_prev_cg,
                            total_real=_total_real_cg,
                            diferenca_g=_dif_cg,
                            aderencia_g=_adh_cg,
                            n_canceladas=_n_canc_cg,
                            n_adiadas=_n_adi_cg,
                            n_clientes=_n_cli_cg,
                            sel_meses=_sel_meses_cg,
                        )
                        st.session_state["pdf_cg_bytes"] = _bytes_cg
                        st.session_state["pdf_cg_nome"] = f"relatorio_cargas_{datetime.now().strftime('%Y%m%d')}.pdf"
                        st.success("PDF gerado!")
                except Exception as _e:
                    st.error(f"Erro ao gerar PDF: {_e}")

        if st.session_state.get("pdf_cg_bytes"):
            st.download_button("⬇️ Baixar Cargas PDF", data=st.session_state["pdf_cg_bytes"],
                file_name=st.session_state.get("pdf_cg_nome", "relatorio_cargas.pdf"),
                mime="application/pdf", key="dl_cg", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB — CARTEIRA DE PEDIDOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_pedidos:
    st.markdown("### 📦 Relatório de Carteira de Pedidos")
    st.markdown("Análise consolidada de pedidos em aberto por cliente e categoria.")

    with st.spinner("Carregando carteira…") if "cart_raw" not in st.session_state else st.empty():
        _df_cart_raw = _dados_carteira()

    if _df_cart_raw.empty:
        st.warning("Dados de carteira não disponíveis.")
    else:
        with st.container(border=True):
            st.markdown("📅 **Período**")
            _col_ano, _col_mes = st.columns(2)
            with _col_ano:
                _anos_cart = sorted(_df_cart_raw["ANO"].unique())
                _sel_anos_cart = st.multiselect("Ano", _anos_cart, default=_anos_cart, key="sel_ano_cart_rel")
                if not _sel_anos_cart: _sel_anos_cart = _anos_cart
            with _col_mes:
                _meses_cart = sorted(_df_cart_raw[_df_cart_raw["ANO"].isin(_sel_anos_cart)]["ANO_MES"].unique())
                _sel_meses_cart = multiselect_reset_on_grow(
                    "Mês", _meses_cart, "sel_mes_cart_rel", reset_to="empty", placeholder="Todos",
                )

            _df_cart = _df_cart_raw[_df_cart_raw["ANO"].isin(_sel_anos_cart)].copy()
            if _sel_meses_cart:
                _df_cart = _df_cart[_df_cart["ANO_MES"].isin(_sel_meses_cart)]

            _total_valor_cart  = _df_cart["VALOR_TOTAL"].sum()
            _total_pecas_cart  = int(_df_cart["QUANTIDADE"].sum())
            _n_pedidos_cart    = _df_cart["PEDIDO"].nunique()
            _n_clientes_cart   = _df_cart["CLIENTE_CURTO"].nunique()
            _n_produtos_cart   = _df_cart["COD_PROD"].nunique()
            _ticket_medio_cart = _total_valor_cart / _n_pedidos_cart if _n_pedidos_cart > 0 else 0

            _anos_str = ', '.join(str(a) for a in _sel_anos_cart)
            _meses_str = ', '.join(_sel_meses_cart) if _sel_meses_cart else 'Todos'
            _periodo_cart = f"{_anos_str} — {_meses_str}"

            if st.button("📄 Gerar Relatório Carteira", key="btn_cart", type="primary"):
                if _df_cart.empty:
                    st.warning("Nenhum registro no período selecionado.")
                else:
                    with st.spinner("Gerando PDF…"):
                        try:
                            _bytes_cart = gerar_pdf_carteira_pedidos(
                                df=_df_cart,
                                total_valor=_total_valor_cart,
                                total_pecas=_total_pecas_cart,
                                n_pedidos=_n_pedidos_cart,
                                n_clientes=_n_clientes_cart,
                                n_produtos=_n_produtos_cart,
                                ticket_medio=_ticket_medio_cart,
                                periodo=_periodo_cart,
                                filtros_texto="",
                            )
                            st.session_state["pdf_cart_bytes"] = _bytes_cart
                            st.session_state["pdf_cart_nome"] = f"carteira_pedidos_{datetime.now().strftime('%Y%m%d')}.pdf"
                            st.success("PDF gerado!")
                        except Exception as _e:
                            st.error(f"Erro ao gerar PDF: {_e}")

            if st.session_state.get("pdf_cart_bytes"):
                st.download_button("⬇️ Baixar Carteira PDF", data=st.session_state["pdf_cart_bytes"],
                    file_name=st.session_state.get("pdf_cart_nome", "carteira_pedidos.pdf"),
                    mime="application/pdf", key="dl_cart", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB — PROGRAMAÇÃO DE CORTE
# ══════════════════════════════════════════════════════════════════════════════
with tab_prog:
    st.markdown("### 📋 Relatório de Programação de Corte")
    st.markdown("Status de OPs programadas vs. cortadas (todas as semanas disponíveis).")

    with st.container(border=True):
        if st.button("📄 Gerar Relatório de Programação", key="btn_prog", type="primary"):
            with st.spinner("Carregando dados e gerando PDF… pode levar alguns segundos."):
                try:
                    _df_prog, _df_cortes_prog = _dados_programacao()
                    if _df_prog.empty:
                        st.error("Dados de programação não disponíveis.")
                    else:
                        _df_agg, _total_ops, _concluidas, _parciais, _pendentes, _aderencia, _total_prog, _total_cort = \
                            _calcular_df_agg(_df_prog, _df_cortes_prog)
                        if _df_agg.empty:
                            st.warning("Nenhuma OP encontrada após cruzamento.")
                        else:
                            _bytes_prog = gerar_pdf_programacao(
                                df_agg=_df_agg,
                                total_ops=_total_ops,
                                concluidas=_concluidas,
                                parciais=_parciais,
                                pendentes=_pendentes,
                                aderencia_pct=_aderencia,
                                total_prog_pcs=_total_prog,
                                total_cort_pcs=_total_cort,
                                filtros_texto="",
                            )
                            st.session_state["pdf_prog_bytes"] = _bytes_prog
                            st.session_state["pdf_prog_nome"] = f"relatorio_programacao_{datetime.now().strftime('%Y%m%d')}.pdf"
                            st.success("PDF gerado!")
                except Exception as _e:
                    st.error(f"Erro ao gerar PDF: {_e}")

        if st.session_state.get("pdf_prog_bytes"):
            st.download_button("⬇️ Baixar Programação PDF", data=st.session_state["pdf_prog_bytes"],
                file_name=st.session_state.get("pdf_prog_nome", "relatorio_programacao.pdf"),
                mime="application/pdf", key="dl_prog", use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#4A5568;font-size:.82rem;'>"
    f"📄 Central de Relatórios · Zanattex &nbsp;|&nbsp; "
    f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    "</div>",
    unsafe_allow_html=True,
)
