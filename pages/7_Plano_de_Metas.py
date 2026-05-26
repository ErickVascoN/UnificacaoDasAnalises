# -*- coding: utf-8 -*-
"""
Plano de Metas — Análise de Metas / Previsão de Custos

Fontes de dados (todas lidas dinamicamente, sem valores hardcoded):
  A) Planilha de metas (METAS_SHEET_ID) — alvos por prestador × produto × mês
  B) 4 planilhas de lançamentos diários (LANCAMENTOS_SHEETS) — produção real granular
  C) xlsx Produção Geral (PRODUCAO_SHEETS_ID) — complementa unidades sem lançamentos
"""
from __future__ import annotations

import io
import os
import sys
import re
import calendar
import unicodedata
import urllib.request
from datetime import date, datetime
from urllib.error import HTTPError, URLError

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.settings import (
    METAS_SHEET_ID, METAS_GID,
    LANCAMENTOS_SHEETS, CENTRO_CUSTO_PARA_LANCAMENTO,
    PRODUCAO_SHEETS_ID, METAS_CACHE_TTL,
)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG DA PÁGINA
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Plano de Metas / Previsão de Custos",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

if st.session_state.get("auth_nivel") not in ("usuario", "admin"):
    st.error("🔒 Acesso restrito. Faça login na página inicial.")
    if st.button("← Voltar"):
        st.switch_page("app.py")
    st.stop()

IS_ADMIN = st.session_state.get("auth_nivel") == "admin"

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    footer {visibility: hidden;}
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1C1C22 0%, #28282E 100%);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px; padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label { color:#FFF !important; font-size:0.78rem !important; font-weight:600 !important; text-transform:uppercase !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color:#FFF !important; font-weight:700 !important; font-size:1.7rem !important; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg,#111115 0%,#191920 100%); border-right:1px solid rgba(255,255,255,0.1); }
    section[data-testid="stSidebar"] * { color:#E0E0E0 !important; }
    .block-container { padding-top: 1.5rem; }
    .status-verde { color: #4ADE80; font-weight: 700; }
    .status-amarelo { color: #FCD34D; font-weight: 700; }
    .status-vermelho { color: #F87171; font-weight: 700; }
    .sec-header { color:#FFF; font-size:1.1rem; font-weight:700; margin:18px 0 8px; border-bottom:1px solid rgba(255,255,255,0.12); padding-bottom:6px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
_MESES_PT_ABR = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
_MESES_PT_LABEL = {v: k.capitalize() for k, v in _MESES_PT_ABR.items()}

_SKIP_HEADER_KW = frozenset([
    "faccao", "produto", "meta", "qtde", "falta",
    "column", "cliente", "responsavel", "%", " tr",
])


def _parse_date_col(h) -> date | None:
    """Converte cabeçalho de coluna em date. Trata Timestamp, date e strings."""
    if h is None:
        return None
    if isinstance(h, datetime):
        return h.date()
    if isinstance(h, date):
        return h
    if hasattr(h, "date") and callable(h.date):
        try:
            return h.date()
        except Exception:
            return None
    h_str = str(h).strip()
    if not h_str or h_str.lower() in ("nan", "none", ""):
        return None
    # Descarta palavras-chave não-data
    h_low = unicodedata.normalize("NFD", h_str.lower())
    h_low = "".join(c for c in h_low if unicodedata.category(c) != "Mn")
    if any(kw in h_low for kw in _SKIP_HEADER_KW):
        return None
    # Tenta Timestamp string do pandas "2026-04-27 00:00:00"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", h_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    h_norm = h_str.replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(h_norm, fmt).date()
        except ValueError:
            pass
    parts = h_norm.split("/")
    if len(parts) in (2, 3):
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else datetime.now().year
            year = year + 2000 if year < 100 else year
            return date(year, month, day)
        except (ValueError, TypeError):
            pass
    for abbr, month_num in _MESES_PT_ABR.items():
        if abbr in h_str.lower():
            dm = re.search(r"(\d+)", h_str)
            if dm:
                try:
                    return date(datetime.now().year, month_num, int(dm.group(1)))
                except ValueError:
                    pass
    return None


def _norm(s: str) -> str:
    """Uppercase + remove acentos + strip."""
    if not isinstance(s, str):
        s = str(s) if not pd.isna(s) else ""
    s = s.strip().upper()
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


_PRODUTO_SUFIXOS = frozenset({
    "ST", "CS", "QN", "KG", "SL", "EX", "CAL",
    "SOLTEIRO", "CASAL", "QUEEN", "KING", "AVULSA",
    "HOTEL", "EXTRA", "SUPER", "PLUS", "P", "M", "G", "GG",
})


def _base_produto(nome: str) -> str:
    """'LENCOL ST' → 'LENCOL', 'FRONHA AVULSA P' → 'FRONHA'. Espera string já _norm'd."""
    words = nome.strip().split()
    if len(words) <= 1:
        return nome.strip()
    result = [words[0]]
    for w in words[1:]:
        if w in _PRODUTO_SUFIXOS or (len(w) <= 2 and w.isalpha()):
            break
        result.append(w)
    return " ".join(result)


def _empresa_match(e1: str, e2: str) -> bool:
    """'NIAZI' ↔ 'NIAZITEX' → True (substring, mínimo 5 chars)."""
    if not e1 or not e2:
        return False
    if e1 == e2:
        return True
    short, long_ = (e1, e2) if len(e1) <= len(e2) else (e2, e1)
    return len(short) >= 5 and short in long_


def _parse_data_base(val) -> date | None:
    """Converte '1-mar.', '1-abr', '1-mai' → date(ano, mes, 1)."""
    if pd.isna(val):
        return None
    raw = str(val).strip().lower().replace(".", "")
    m = re.search(r"(\d+)[\-/\s]([a-zá-ú]+)", raw)
    if m:
        mes_str = m.group(2)[:3]
        mes_num = _MESES_PT_ABR.get(mes_str)
        if mes_num:
            hoje = date.today()
            ano = hoje.year
            try:
                return date(ano, mes_num, 1)
            except ValueError:
                return None
    return None


def _parse_num(val) -> float:
    """Converte '3.000', 'R$ 0,44', '#ERROR!' → float ou NaN."""
    if pd.isna(val):
        return float("nan")
    s = str(val).strip()
    if s in ("#ERROR!", "#VALOR!", "#NAME?", "-", ""):
        return float("nan")
    s = re.sub(r"[R$\s]", "", s).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _dias_uteis_mes(ano: int, mes: int) -> int:
    """Conta dias úteis (seg–sex) no mês inteiro."""
    _, n_dias = calendar.monthrange(ano, mes)
    count = 0
    for d in range(1, n_dias + 1):
        if date(ano, mes, d).weekday() < 5:
            count += 1
    return count


def _fmt_br(v: float, dec: int = 0) -> str:
    if np.isnan(v):
        return "—"
    txt = f"{v:,.{dec}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_reais(v: float) -> str:
    if np.isnan(v):
        return "—"
    return "R$ " + _fmt_br(v, 2)


def _csv_url(sheet_id: str, gid: str) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DE DADOS
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_csv(sheet_id: str, gid: str) -> pd.DataFrame:
    url = _csv_url(sheet_id, gid)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
        df = pd.read_csv(io.BytesIO(raw), dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception:
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text), dtype=str)
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            st.warning(f"Falha ao carregar planilha {sheet_id}/{gid}: {e}")
            return pd.DataFrame()


@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_producao_geral() -> pd.DataFrame:
    """
    Carrega o xlsx de Produção Geral (mesma fonte de 2_Producao_Geral.py).
    Cada aba = empresa; FACCAO column = contractor/facção (= RESPONSAVEL no plano de metas).
    Datas são cabeçalhos de coluna — trata Timestamp, date e string.
    """
    url = f"https://docs.google.com/spreadsheets/d/{PRODUCAO_SHEETS_ID}/export?format=xlsx"
    xlsx_data = None
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        xlsx_data = io.BytesIO(r.content)
    except Exception:
        local = os.path.join(_ROOT, "data", "planilha_producao.xlsx")
        if os.path.exists(local):
            xlsx_data = local
        else:
            return pd.DataFrame()

    rows = []
    try:
        xls = pd.ExcelFile(xlsx_data, engine="openpyxl")
        for sheet in xls.sheet_names:
            if sheet.lower() == "diversos":
                continue
            empresa = _norm(sheet)
            try:
                raw = pd.read_excel(xlsx_data, sheet_name=sheet, header=None, engine="openpyxl")
            except Exception:
                continue

            # Busca todas as linhas de cabeçalho que contêm "FACCAO" ou "PRODUTO"
            for hdr_idx in range(len(raw)):
                header_row = raw.iloc[hdr_idx].tolist()
                vals_norm = [_norm(str(v)) for v in header_row]
                if not any("FACCAO" in v or v == "PRODUTO" for v in vals_norm):
                    continue

                # Mapeia índices de colunas pelos VALORES ORIGINAIS do cabeçalho
                col_fac_idx = None
                col_prod_idx = None
                date_col_map: dict[int, date] = {}  # col_index → date

                for idx, (h_orig, h_norm_val) in enumerate(zip(header_row, vals_norm)):
                    if "FACCAO" in h_norm_val and col_fac_idx is None:
                        col_fac_idx = idx
                    elif h_norm_val == "PRODUTO" and col_prod_idx is None:
                        col_prod_idx = idx
                    else:
                        # Tenta interpretar como data usando o VALOR ORIGINAL (não normalizado)
                        d = _parse_date_col(h_orig)
                        if d is not None:
                            date_col_map[idx] = d

                if col_prod_idx is None or not date_col_map:
                    continue

                # Itera linhas de dados abaixo do cabeçalho
                data_block = raw.iloc[hdr_idx + 1:]
                for _, row in data_block.iterrows():
                    # Para se encontrar outro cabeçalho
                    row_norm = [_norm(str(v)) for v in row.tolist()]
                    if any("FACCAO" in v or v == "PRODUTO" for v in row_norm):
                        break

                    fac_raw = row.iloc[col_fac_idx] if col_fac_idx is not None else None
                    fac = _norm(str(fac_raw)) if fac_raw is not None and not pd.isna(fac_raw) else empresa
                    if not fac or fac in ("NAN", "NONE", ""):
                        fac = empresa

                    prod_raw = row.iloc[col_prod_idx]
                    produto = _norm(str(prod_raw)) if not pd.isna(prod_raw) else ""

                    for col_idx, d_obj in date_col_map.items():
                        qtd = _parse_num(row.iloc[col_idx])
                        if not np.isnan(qtd) and qtd > 0:
                            rows.append({
                                "PRESTADOR": fac,
                                "EMPRESA": empresa,
                                "PRODUTO": produto,
                                "DATA": d_obj,
                                "QUANTIDADE": qtd,
                            })
    except Exception:
        pass

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _load_lancamentos(centro_custo_norm: str) -> pd.DataFrame:
    """Carrega e normaliza lançamentos para um CENTRO DE CUSTO."""
    chaves = CENTRO_CUSTO_PARA_LANCAMENTO.get(centro_custo_norm, [])
    frames = []
    for chave in chaves:
        cfg = LANCAMENTOS_SHEETS.get(chave)
        if not cfg:
            continue
        raw = _load_csv(cfg["id"], cfg["gid"])
        if raw.empty:
            continue
        # Normaliza nomes de colunas
        raw.columns = [c.strip() for c in raw.columns]
        col_w = cfg["col_worker"]
        col_e = cfg["col_empresa"]
        col_d = cfg["col_data"]
        col_q = cfg["col_qtd"]
        # Verifica se colunas existem (pode haver variações de nome)
        col_w = next((c for c in raw.columns if _norm(c) == _norm(col_w)), None)
        col_e = next((c for c in raw.columns if _norm(c) == _norm(col_e)), None)
        col_d = next((c for c in raw.columns if _norm(c) == _norm(col_d)), None)
        col_q = next((c for c in raw.columns if _norm(c) == _norm(col_q)), None)
        if not col_d or not col_q:
            continue
        sub = raw.copy()
        sub["_PRESTADOR"] = sub[col_w].apply(_norm) if col_w else ""
        sub["_EMPRESA"] = sub[col_e].apply(_norm) if col_e else ""
        sub["_DATA"] = pd.to_datetime(sub[col_d], dayfirst=True, errors="coerce").dt.date
        sub["_QUANTIDADE"] = sub[col_q].apply(_parse_num)
        sub = sub.dropna(subset=["_DATA"])
        sub = sub[sub["_QUANTIDADE"] > 0]
        # Auto-detecta coluna de produto / descrição
        col_p_raw = None
        for _cand in ("DESCRICAO", "PRODUTO"):
            col_p_raw = next(
                (c for c in raw.columns if _norm(c).startswith(_cand[:6])),
                None,
            )
            if col_p_raw:
                break
        if col_p_raw and col_p_raw in sub.columns:
            sub = sub.copy()
            sub["_PRODUTO"] = sub[col_p_raw].apply(
                lambda x: _base_produto(_norm(str(x)))
                if pd.notna(x) and str(x).strip() not in ("", "NAN", "NONE")
                else ""
            )
        else:
            sub = sub.copy()
            sub["_PRODUTO"] = ""
        frames.append(sub[["_PRESTADOR", "_EMPRESA", "_DATA", "_QUANTIDADE", "_PRODUTO"]].rename(columns={
            "_PRESTADOR": "PRESTADOR", "_EMPRESA": "EMPRESA",
            "_DATA": "DATA", "_QUANTIDADE": "QUANTIDADE", "_PRODUTO": "PRODUTO",
        }))
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────────
# PLANO DE METAS
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=METAS_CACHE_TTL)
def _load_metas() -> pd.DataFrame:
    raw = _load_csv(METAS_SHEET_ID, METAS_GID)
    if raw.empty:
        return pd.DataFrame()

    # Normaliza colunas (remove espaços, upper)
    raw.columns = [c.strip().upper() for c in raw.columns]

    # Detecta colunas principais (tolerante a pequenas variações)
    col_map = {}
    for col in raw.columns:
        n = _norm(col)
        if n == "CLIENTE": col_map["CLIENTE"] = col
        elif "RESPONSAVEL" in n: col_map["RESPONSAVEL"] = col
        elif n == "ATIVIDADE": col_map["ATIVIDADE"] = col
        elif n == "TIPO": col_map["TIPO"] = col
        elif "CENTRO" in n and "CUSTO" in n: col_map["CENTRO_CUSTO"] = col
        elif n == "PRODUTO": col_map["PRODUTO"] = col
        elif "META" in n and "MES" in n: col_map["META_MES"] = col
        elif "META" in n and "DIARI" in n: col_map["META_DIARIA"] = col
        elif "VLR" in n or "UNITARIO" in n: col_map["VLR_UNIT"] = col
        elif n == "CUSTO" and "FINAL" not in n: col_map["CUSTO"] = col
        elif "PRECO" in n and "FINAL" in n: col_map["PRECO_FINAL"] = col
        elif "CUSTO" in n and "FINAL" in n: col_map["CUSTO_FINAL"] = col
        elif "DATA" in n and "BASE" in n: col_map["DATA_BASE"] = col
        elif n == "STATUS": col_map["STATUS"] = col

    required = ["CLIENTE", "RESPONSAVEL", "PRODUTO", "CENTRO_CUSTO",
                "META_MES", "DATA_BASE", "STATUS"]
    missing = [r for r in required if r not in col_map]
    if missing:
        st.warning(f"Planilha de metas sem colunas: {missing}")
        return pd.DataFrame()

    df = pd.DataFrame()
    df["CLIENTE"]      = raw[col_map["CLIENTE"]].apply(_norm)
    df["RESPONSAVEL"]  = raw[col_map["RESPONSAVEL"]].apply(_norm)
    df["ATIVIDADE"]    = raw[col_map.get("ATIVIDADE", col_map["CLIENTE"])].apply(_norm) if "ATIVIDADE" in col_map else ""
    df["TIPO"]         = raw[col_map.get("TIPO", col_map["CLIENTE"])].apply(_norm) if "TIPO" in col_map else ""
    df["CENTRO_CUSTO"] = raw[col_map["CENTRO_CUSTO"]].apply(_norm)
    df["PRODUTO"]      = raw[col_map["PRODUTO"]].apply(_norm)
    df["META_MES"]     = raw[col_map["META_MES"]].apply(_parse_num)
    df["META_DIARIA"]  = raw[col_map.get("META_DIARIA", col_map["META_MES"])].apply(_parse_num) if "META_DIARIA" in col_map else float("nan")
    df["VLR_UNIT"]     = raw[col_map["VLR_UNIT"]].apply(_parse_num) if "VLR_UNIT" in col_map else float("nan")
    df["CUSTO"]        = raw[col_map["CUSTO"]].apply(_parse_num) if "CUSTO" in col_map else float("nan")
    df["PRECO_FINAL"]  = raw[col_map["PRECO_FINAL"]].apply(_parse_num) if "PRECO_FINAL" in col_map else float("nan")
    df["CUSTO_FINAL"]  = raw[col_map["CUSTO_FINAL"]].apply(_parse_num) if "CUSTO_FINAL" in col_map else float("nan")
    df["DATA_BASE"]    = raw[col_map["DATA_BASE"]].apply(_parse_data_base)
    df["STATUS"]       = raw[col_map["STATUS"]].apply(_norm)

    # Guarda raw_responsavel e raw_cliente para o gerador do próximo mês
    df["_RAW_RESPONSAVEL"] = raw[col_map["RESPONSAVEL"]].astype(str).str.strip()
    df["_RAW_CLIENTE"]     = raw[col_map["CLIENTE"]].astype(str).str.strip()
    df["_RAW_CENTRO"]      = raw[col_map["CENTRO_CUSTO"]].astype(str).str.strip()
    df["_RAW_PRODUTO"]     = raw[col_map["PRODUTO"]].astype(str).str.strip()
    df["_RAW_ATIVIDADE"]   = raw[col_map["ATIVIDADE"]].astype(str).str.strip() if "ATIVIDADE" in col_map else ""
    df["_RAW_TIPO"]        = raw[col_map["TIPO"]].astype(str).str.strip() if "TIPO" in col_map else ""
    df["_RAW_META_DIARIA"] = raw[col_map["META_DIARIA"]].astype(str).str.strip() if "META_DIARIA" in col_map else ""
    df["_RAW_VLR_UNIT"]    = raw[col_map["VLR_UNIT"]].astype(str).str.strip() if "VLR_UNIT" in col_map else ""
    df["_RAW_CUSTO"]       = raw[col_map["CUSTO"]].astype(str).str.strip() if "CUSTO" in col_map else ""
    df["_RAW_STATUS"]      = raw[col_map["STATUS"]].astype(str).str.strip()

    df = df.dropna(subset=["DATA_BASE"])
    df = df[df["RESPONSAVEL"].str.len() > 0]
    df = df[df["STATUS"].isin(["PREVISTO", "REALIZADO"])]
    return df


# ──────────────────────────────────────────────────────────────────────────────
# PRODUÇÃO REAL (lançamentos + prod geral)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=METAS_CACHE_TTL)
def _build_producao_real(centros: list[str]) -> pd.DataFrame:
    """
    Agrega produção real de todas as fontes.

    Sempre inclui Produção Geral (xlsx) porque é lá que FACCAO = RESPONSAVEL do plano de metas.
    Os lançamentos detalhados (por unidade) são adicionados como suplemento para maior granularidade.
    """
    frames = []

    # 1. Produção Geral (FACCAO = contractor = RESPONSAVEL) — sempre carregada
    df_pg = _load_producao_geral()
    if not df_pg.empty:
        df_pg = df_pg.copy()
        df_pg["CENTRO_CUSTO"] = "PRODUCAO_GERAL"
        frames.append(df_pg)

    # 2. Lançamentos detalhados por unidade — complemento para unidades mapeadas
    for cc in centros:
        cc_norm = _norm(cc)
        if cc_norm in CENTRO_CUSTO_PARA_LANCAMENTO:
            df_lanc = _load_lancamentos(cc_norm)
            if not df_lanc.empty:
                df_lanc = df_lanc.copy()
                df_lanc["CENTRO_CUSTO"] = cc_norm
                frames.append(df_lanc)

    if not frames:
        return pd.DataFrame(columns=["PRESTADOR", "EMPRESA", "PRODUTO", "DATA", "QUANTIDADE", "CENTRO_CUSTO"])
    result = pd.concat(frames, ignore_index=True)
    if "PRODUTO" not in result.columns:
        result["PRODUTO"] = ""
    result["PRODUTO"] = result["PRODUTO"].fillna("")
    result["DATA"] = pd.to_datetime(result["DATA"], errors="coerce").dt.date
    return result.dropna(subset=["DATA"])


# ──────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE INDICADORES
# ──────────────────────────────────────────────────────────────────────────────
def _calcular_indicadores(
    df_prev: pd.DataFrame,
    df_real: pd.DataFrame,
    hoje: date,
) -> pd.DataFrame:
    """
    Para cada linha PREVISTO, une com produção real e calcula:
    realizado, % atingido, média diária, projeção, custos projetados.
    """
    rows = []
    for _, meta in df_prev.iterrows():
        resp  = meta["RESPONSAVEL"]
        emp   = meta["CLIENTE"]
        cc    = meta["CENTRO_CUSTO"]
        mes   = meta["DATA_BASE"].month
        ano   = meta["DATA_BASE"].year
        meta_mes   = meta["META_MES"]
        meta_diaria = meta["META_DIARIA"]
        vlr_unit   = meta["VLR_UNIT"]
        custo_unit = meta["CUSTO"]

        prod_norm  = meta["PRODUTO"]   # já _norm'd
        base_prod  = _base_produto(prod_norm)
        mes_mask   = df_real["DATA"].apply(lambda d: d.month == mes and d.year == ano)
        has_prod   = "PRODUTO" in df_real.columns

        def _prod_filter(df_in: pd.DataFrame) -> pd.DataFrame:
            if df_in.empty or not base_prod or not has_prod:
                return df_in
            sub_p = df_in[df_in["PRODUTO"].apply(
                lambda p: bool(p) and _base_produto(p) == base_prod
            )]
            return sub_p if not sub_p.empty else df_in

        # Estratégia 1 — worker individual + empresa (match parcial)
        df_g = _prod_filter(df_real[
            mes_mask &
            (df_real["PRESTADOR"] == resp) &
            df_real["EMPRESA"].apply(lambda e: _empresa_match(e, emp))
        ])
        # Estratégia 2 — worker individual, qualquer empresa
        if df_g.empty:
            df_g = _prod_filter(df_real[mes_mask & (df_real["PRESTADOR"] == resp)])
        # Estratégia 3 — nível unidade (RESPONSAVEL == nome do centro de custo)
        if df_g.empty and resp in CENTRO_CUSTO_PARA_LANCAMENTO:
            df_unit = df_real[
                mes_mask &
                df_real["EMPRESA"].apply(lambda e: _empresa_match(e, emp))
            ]
            df_g = _prod_filter(df_unit)

        realizado = float(df_g["QUANTIDADE"].sum()) if not df_g.empty else 0.0
        datas_unicas = df_g["DATA"].nunique() if not df_g.empty else 0

        media_diaria_real = realizado / max(datas_unicas, 1)
        dias_uteis_mes = _dias_uteis_mes(ano, mes)

        # Dias restantes (a partir de amanhã se hoje ainda no mês)
        if hoje.month == mes and hoje.year == ano:
            _, n_dias = calendar.monthrange(ano, mes)
            dias_restantes = sum(
                1 for d in range(hoje.day + 1, n_dias + 1)
                if date(ano, mes, d).weekday() < 5
            )
        else:
            dias_restantes = 0

        projecao = realizado + (media_diaria_real * dias_restantes)

        # Ritmo esperado até hoje
        if hoje.month == mes and hoje.year == ano:
            dias_passados = sum(
                1 for d in range(1, hoje.day + 1)
                if date(ano, mes, d).weekday() < 5
            )
        else:
            dias_passados = dias_uteis_mes

        ritmo_esperado = (meta_mes * (dias_passados / max(dias_uteis_mes, 1))) if not np.isnan(meta_mes) else 0
        pct_ritmo = (realizado / ritmo_esperado * 100) if ritmo_esperado > 0 else (100 if realizado > 0 else 0)

        pct_meta = (realizado / meta_mes * 100) if (not np.isnan(meta_mes) and meta_mes > 0) else float("nan")

        # Financeiro
        receita_prev  = meta_mes * vlr_unit  if (not np.isnan(meta_mes) and not np.isnan(vlr_unit)) else float("nan")
        custo_prev    = meta_mes * custo_unit if (not np.isnan(meta_mes) and not np.isnan(custo_unit)) else float("nan")
        receita_proj  = projecao * vlr_unit   if not np.isnan(vlr_unit) else float("nan")
        custo_proj    = projecao * custo_unit  if not np.isnan(custo_unit) else float("nan")
        margem_proj   = receita_proj - custo_proj if (not np.isnan(receita_proj) and not np.isnan(custo_proj)) else float("nan")

        if pct_ritmo >= 90:
            status = "🟢"
        elif pct_ritmo >= 70:
            status = "🟡"
        else:
            status = "🔴"

        rows.append({
            "CENTRO_CUSTO": cc,
            "RESPONSAVEL": meta["_RAW_RESPONSAVEL"],
            "CLIENTE": meta["_RAW_CLIENTE"],
            "PRODUTO": meta["_RAW_PRODUTO"],
            "META_MES": meta_mes,
            "REALIZADO": realizado,
            "PCT_META": pct_meta,
            "META_DIARIA": meta_diaria,
            "MEDIA_DIARIA_REAL": media_diaria_real,
            "PROJECAO": projecao,
            "DIAS_TRABALHADOS": datas_unicas,
            "DIAS_RESTANTES": dias_restantes,
            "PCT_RITMO": pct_ritmo,
            "RECEITA_PREV": receita_prev,
            "CUSTO_PREV": custo_prev,
            "RECEITA_PROJ": receita_proj,
            "CUSTO_PROJ": custo_proj,
            "MARGEM_PROJ": margem_proj,
            "VLR_UNIT": vlr_unit,
            "CUSTO_UNIT": custo_unit,
            "STATUS_ICON": status,
            "_RESP_NORM": resp,
            "_EMP_NORM": emp,
            "_ANO": ano,
            "_MES": mes,
        })
    return pd.DataFrame(rows)


def _serie_diaria(
    df_real: pd.DataFrame,
    resp: str, emp: str,
    ano: int, mes: int,
    meta_diaria: float,
    hoje: date,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna série real acumulada e projeção até fim do mês."""
    mes_mask_s = df_real["DATA"].apply(lambda d: d.month == mes and d.year == ano)
    df_g = df_real[mes_mask_s & (df_real["PRESTADOR"] == resp) & df_real["EMPRESA"].apply(lambda e: _empresa_match(e, emp))]
    if df_g.empty:
        df_g = df_real[mes_mask_s & (df_real["PRESTADOR"] == resp)]
    if df_g.empty and resp in CENTRO_CUSTO_PARA_LANCAMENTO:
        df_g = df_real[mes_mask_s & df_real["EMPRESA"].apply(lambda e: _empresa_match(e, emp))]

    # Produção diária
    if df_g.empty:
        return pd.DataFrame(), pd.DataFrame()

    daily = (
        df_g.groupby("DATA")["QUANTIDADE"].sum()
        .reset_index().sort_values("DATA")
    )
    daily.columns = ["DATA", "QTD_DIA"]
    daily["ACUMULADO"] = daily["QTD_DIA"].cumsum()

    # Projeção linear: regressão nos valores diários reais
    _, n_dias = calendar.monthrange(ano, mes)
    dias_uteis = [
        date(ano, mes, d) for d in range(1, n_dias + 1)
        if date(ano, mes, d).weekday() < 5
    ]
    datas_real = sorted(daily["DATA"].tolist())
    if len(datas_real) >= 2:
        x = np.arange(len(datas_real), dtype=float)
        y = daily["ACUMULADO"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        n_tot = len(dias_uteis)
        x_fut = np.arange(len(datas_real), n_tot, dtype=float)
        y_fut = np.maximum(0, slope * x_fut + intercept)
        last_acc = float(daily["ACUMULADO"].iloc[-1])
        # Garante monotonia
        y_fut = np.maximum(last_acc, last_acc + slope * np.arange(1, len(x_fut) + 1))
    else:
        media = float(daily["QTD_DIA"].mean()) if not daily.empty else 0
        n_restantes = len([d for d in dias_uteis if d > hoje])
        y_fut = np.cumsum(np.full(n_restantes, media)) + (float(daily["ACUMULADO"].iloc[-1]) if not daily.empty else 0)

    datas_futuras = [d for d in dias_uteis if d > (datas_real[-1] if datas_real else hoje)]
    proj = pd.DataFrame({"DATA": datas_futuras, "ACUMULADO_PROJ": y_fut[:len(datas_futuras)]})

    # Rampa meta
    meta_diaria_val = meta_diaria if (not np.isnan(meta_diaria)) else 0
    meta_ramp = pd.DataFrame({
        "DATA": dias_uteis,
        "META_ACC": [meta_diaria_val * (i + 1) for i in range(len(dias_uteis))],
    })

    # Merge tudo
    real_full = pd.merge(
        pd.DataFrame({"DATA": dias_uteis}),
        daily[["DATA", "ACUMULADO"]],
        on="DATA", how="left"
    )
    real_full = pd.merge(real_full, meta_ramp, on="DATA", how="left")
    real_full = pd.merge(real_full, proj, on="DATA", how="left")
    return daily, real_full


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DE PLANO DO PRÓXIMO MÊS
# ──────────────────────────────────────────────────────────────────────────────
def _gerar_proximo_mes_xlsx(
    df_prev: pd.DataFrame,
    df_indicadores: pd.DataFrame,
    ano_atual: int, mes_atual: int,
) -> bytes:
    """
    Gera Excel com estrutura idêntica ao plano de metas,
    com META MÊS e META DIÁRIA recalibradas pelo rendimento do mês atual.
    """
    prox_mes = mes_atual % 12 + 1
    prox_ano = ano_atual + (1 if mes_atual == 12 else 0)
    dias_uteis_prox = _dias_uteis_mes(prox_ano, prox_mes)

    # Meses para label (ex: "1-jun.")
    abr_mes = _MESES_PT_LABEL.get(prox_mes, str(prox_mes))
    label_data_base = f"1-{abr_mes.lower()}."

    out_rows = []
    for _, meta in df_prev.iterrows():
        resp_norm = meta["RESPONSAVEL"]
        emp_norm  = meta["CLIENTE"]
        cc_norm   = meta["CENTRO_CUSTO"]
        prod_norm = meta["PRODUTO"]

        # Busca indicadores calculados para essa combinação
        match = df_indicadores[
            (df_indicadores["_RESP_NORM"] == resp_norm) &
            (df_indicadores["_EMP_NORM"] == emp_norm)
        ]

        if not match.empty:
            media_diaria_real = float(match.iloc[0]["MEDIA_DIARIA_REAL"])
            dias_trab = int(match.iloc[0]["DIAS_TRABALHADOS"])
        else:
            media_diaria_real = float("nan")
            dias_trab = 0

        if dias_trab > 0 and not np.isnan(media_diaria_real) and media_diaria_real > 0:
            nova_meta_diaria = round(media_diaria_real)
            nova_meta_mes    = round(media_diaria_real * dias_uteis_prox)
        else:
            # Sem produção real → mantém metas originais
            nova_meta_diaria = meta["META_DIARIA"] if not np.isnan(meta["META_DIARIA"]) else meta["META_MES"]
            nova_meta_mes    = meta["META_MES"] if not np.isnan(meta["META_MES"]) else 0

        vlr_unit   = meta["VLR_UNIT"]
        custo_unit = meta["CUSTO"]
        preco_final = nova_meta_mes * vlr_unit   if not np.isnan(vlr_unit)   else float("nan")
        custo_final = nova_meta_mes * custo_unit if not np.isnan(custo_unit) else float("nan")

        out_rows.append({
            "CLIENTE":       meta["_RAW_CLIENTE"],
            "RESPONSÁVEL":   meta["_RAW_RESPONSAVEL"],
            "ATIVIDADE":     meta["_RAW_ATIVIDADE"],
            "TIPO":          meta["_RAW_TIPO"],
            "CENTRO DE CUSTO": meta["_RAW_CENTRO"],
            "PRODUTO":       meta["_RAW_PRODUTO"],
            "META MÊS":      nova_meta_mes,
            "META DIÁRIA":   nova_meta_diaria,
            "VLR UNITARIO":  vlr_unit if not np.isnan(vlr_unit) else "",
            "CUSTO":         custo_unit if not np.isnan(custo_unit) else "",
            "PREÇO FINAL":   preco_final if not np.isnan(preco_final) else "",
            "CUSTO FINAL":   custo_final if not np.isnan(custo_final) else "",
            "DATA BASE":     label_data_base,
            "STATUS":        "PREVISTO",
        })

    df_out = pd.DataFrame(out_rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Plano de Metas")
    buf.seek(0)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# RENDERIZAÇÃO
# ──────────────────────────────────────────────────────────────────────────────
def main():
    hoje = date.today()

    # ── Cabeçalho ──────────────────────────────────────────────────────────────
    st.markdown("<h1 style='color:#FFF;font-size:2rem;margin-bottom:4px;'>🎯 Plano de Metas / Previsão de Custos</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#A0A0A0;margin-bottom:20px;'>Acompanhamento automático vs. metas — produção real, projeções e análise de custos</p>", unsafe_allow_html=True)

    # ── Carrega metas ──────────────────────────────────────────────────────────
    with st.spinner("Carregando plano de metas..."):
        df_metas = _load_metas()

    if df_metas.empty:
        st.error("Não foi possível carregar a planilha de metas. Verifique o acesso.")
        st.stop()

    # ── Filtros ────────────────────────────────────────────────────────────────
    meses_disponiveis = sorted(
        df_metas["DATA_BASE"].dropna().unique(),
        key=lambda d: (d.year, d.month),
    )
    # Padrão: mês atual (ou mais próximo disponível)
    default_mes = next(
        (d for d in meses_disponiveis if d.month == hoje.month and d.year == hoje.year),
        meses_disponiveis[-1] if meses_disponiveis else None,
    )
    meses_labels = {d: f"{_MESES_PT_LABEL.get(d.month, d.month)}/{d.year}" for d in meses_disponiveis}

    with st.sidebar:
        st.markdown("### Filtros")
        mes_sel = st.selectbox(
            "Mês",
            options=meses_disponiveis,
            index=meses_disponiveis.index(default_mes) if default_mes in meses_disponiveis else 0,
            format_func=lambda d: meses_labels[d],
        )
        df_mes = df_metas[df_metas["DATA_BASE"] == mes_sel]

        centros_disp = sorted(df_mes["CENTRO_CUSTO"].unique().tolist())
        centros_sel = st.multiselect("Centro de Custo", centros_disp, default=centros_disp)

        clientes_disp = sorted(df_mes["CLIENTE"].unique().tolist())
        clientes_sel = st.multiselect("Cliente", clientes_disp, default=clientes_disp)

        resp_disp = sorted(df_mes["RESPONSAVEL"].unique().tolist())
        resp_sel = st.multiselect("Prestador / Responsável", resp_disp, default=resp_disp)

    # Diagnóstico (apenas Admin)
    if IS_ADMIN:
        with st.sidebar.expander("🔍 Diagnóstico de Dados"):
            df_pg_dbg = _load_producao_geral()
            n_pg = len(df_pg_dbg)
            st.caption(f"**Produção Geral:** {n_pg} registros")
            if n_pg == 0:
                st.error("⚠️ Produção Geral vazio — verifique acesso ao xlsx.")
            else:
                empresas_pg = sorted(df_pg_dbg["EMPRESA"].unique().tolist())
                st.caption(f"Empresas xlsx: {empresas_pg}")
                facs_pg    = set(df_pg_dbg["PRESTADOR"].unique())
                resps_prev = set(df_mes[df_mes["STATUS"] == "PREVISTO"]["RESPONSAVEL"].unique())
                com_dado   = sorted(resps_prev & facs_pg)
                sem_dado   = sorted(resps_prev - facs_pg)
                st.caption(f"✅ FACCAO com match ({len(com_dado)}): {com_dado[:10]}")
                st.caption(f"❌ Sem match direto ({len(sem_dado)}): {sem_dado[:10]}")
                if sem_dado:
                    st.caption(f"_FACCAOs no xlsx:_ {sorted(list(facs_pg))[:15]}")

            # Lançamentos detalhados
            st.markdown("---")
            centros_diag = sorted(set(_norm(c) for c in df_mes["CENTRO_CUSTO"].unique()))
            for cc_d in centros_diag:
                if cc_d in CENTRO_CUSTO_PARA_LANCAMENTO:
                    df_lanc_d = _load_lancamentos(cc_d)
                    n_lanc = len(df_lanc_d)
                    st.caption(f"**{cc_d}** lançamentos: {n_lanc} linhas")
                    if n_lanc > 0:
                        prods_lanc = sorted(df_lanc_d["PRODUTO"].dropna().unique().tolist()) if "PRODUTO" in df_lanc_d.columns else []
                        emps_lanc  = sorted(df_lanc_d["EMPRESA"].unique().tolist())
                        if prods_lanc:
                            st.caption(f"  Produtos: {prods_lanc[:10]}")
                        st.caption(f"  Empresas: {emps_lanc[:8]}")

    # Aplica filtros
    df_prev = df_mes[
        (df_mes["STATUS"] == "PREVISTO") &
        (df_mes["CENTRO_CUSTO"].isin(centros_sel)) &
        (df_mes["CLIENTE"].isin(clientes_sel)) &
        (df_mes["RESPONSAVEL"].isin(resp_sel))
    ].copy()

    df_real_mes = df_mes[
        (df_mes["STATUS"] == "REALIZADO") &
        (df_mes["CENTRO_CUSTO"].isin(centros_sel))
    ].copy()

    if df_prev.empty:
        st.warning("Nenhuma meta PREVISTO encontrada para os filtros selecionados.")
        st.stop()

    # ── Produção real ──────────────────────────────────────────────────────────
    with st.spinner("Carregando dados de produção..."):
        df_prod = _build_producao_real(centros_sel)

    df_ind = _calcular_indicadores(df_prev, df_prod, hoje)

    # ── KPI Row ────────────────────────────────────────────────────────────────
    meta_total     = df_prev["META_MES"].sum(skipna=True)
    real_total     = df_ind["REALIZADO"].sum() if not df_ind.empty else 0.0
    proj_total     = df_ind["PROJECAO"].sum() if not df_ind.empty else 0.0
    pct_atingido   = (real_total / meta_total * 100) if meta_total > 0 else 0.0
    receita_prev_t = df_ind["RECEITA_PREV"].sum(skipna=True) if not df_ind.empty else 0.0
    receita_proj_t = df_ind["RECEITA_PROJ"].sum(skipna=True) if not df_ind.empty else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Meta Total do Mês", _fmt_br(meta_total))
    c2.metric("Realizado Acumulado", _fmt_br(real_total),
              delta=f"{pct_atingido:.1f}% da meta")
    c3.metric("Projeção Fim do Mês", _fmt_br(proj_total),
              delta=f"{(proj_total/meta_total*100 if meta_total > 0 else 0):.1f}% da meta")
    c4.metric("Receita Prevista", _fmt_reais(receita_prev_t))
    c5.metric("Receita Projetada", _fmt_reais(receita_proj_t))

    st.markdown("---")

    # ── Seção 2 — Tabela de Progresso ─────────────────────────────────────────
    st.markdown("<div class='sec-header'>📋 Progresso por Prestador × Produto</div>", unsafe_allow_html=True)

    if not df_ind.empty:
        tbl = df_ind[[
            "STATUS_ICON", "CENTRO_CUSTO", "RESPONSAVEL", "CLIENTE", "PRODUTO",
            "META_MES", "REALIZADO", "PCT_META", "META_DIARIA", "MEDIA_DIARIA_REAL",
            "PROJECAO", "RECEITA_PREV", "RECEITA_PROJ", "CUSTO_PROJ", "MARGEM_PROJ",
        ]].copy()
        tbl = tbl.sort_values(["CENTRO_CUSTO", "RESPONSAVEL"])
        tbl["PCT_META"] = tbl["PCT_META"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "—")
        for col in ["META_MES", "REALIZADO", "META_DIARIA", "MEDIA_DIARIA_REAL", "PROJECAO"]:
            tbl[col] = tbl[col].apply(lambda v: _fmt_br(v) if not np.isnan(v) else "—")
        for col in ["RECEITA_PREV", "RECEITA_PROJ", "CUSTO_PROJ", "MARGEM_PROJ"]:
            tbl[col] = tbl[col].apply(_fmt_reais)
        tbl.columns = [
            "⬤", "Centro Custo", "Prestador", "Cliente", "Produto",
            "Meta Mês", "Realizado", "% Meta", "Meta Diária", "Média Diária",
            "Projeção", "Receita Prev.", "Receita Proj.", "Custo Proj.", "Margem Proj.",
        ]
        st.dataframe(tbl, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de indicadores calculados.")

    st.markdown("---")

    # ── Seção 3 — Série Temporal por Prestador ─────────────────────────────────
    st.markdown("<div class='sec-header'>📈 Evolução Diária — Meta vs Realizado vs Projeção</div>", unsafe_allow_html=True)

    if not df_ind.empty:
        prestadores_unicos = df_ind["RESPONSAVEL"].unique().tolist()
        col_sel1, col_sel2 = st.columns([2, 1])
        with col_sel1:
            resp_graf = st.selectbox("Prestador", prestadores_unicos)
        with col_sel2:
            ano_graf = mes_sel.year
            mes_graf = mes_sel.month
            resp_norm_graf = _norm(resp_graf)
            emp_norm_graf  = df_ind[df_ind["RESPONSAVEL"] == resp_graf]["_EMP_NORM"].iloc[0] if len(df_ind[df_ind["RESPONSAVEL"] == resp_graf]) > 0 else ""
            meta_d_graf = df_ind[df_ind["RESPONSAVEL"] == resp_graf]["META_DIARIA"].iloc[0] if len(df_ind[df_ind["RESPONSAVEL"] == resp_graf]) > 0 else float("nan")

        _, serie = _serie_diaria(df_prod, resp_norm_graf, emp_norm_graf, ano_graf, mes_graf, meta_d_graf, hoje)

        if not serie.empty:
            fig = go.Figure()
            # Realizado acumulado
            mask_real = serie["ACUMULADO"].notna()
            fig.add_trace(go.Scatter(
                x=serie.loc[mask_real, "DATA"].astype(str),
                y=serie.loc[mask_real, "ACUMULADO"],
                name="Realizado",
                line=dict(color="#4ECDC4", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
            ))
            # Rampa meta
            fig.add_trace(go.Scatter(
                x=serie["DATA"].astype(str),
                y=serie["META_ACC"],
                name="Rampa Meta",
                line=dict(color="#A0A0A0", width=1.5, dash="dash"),
                mode="lines",
            ))
            # Projeção
            mask_proj = serie["ACUMULADO_PROJ"].notna()
            fig.add_trace(go.Scatter(
                x=serie.loc[mask_proj, "DATA"].astype(str),
                y=serie.loc[mask_proj, "ACUMULADO_PROJ"],
                name="Projeção",
                line=dict(color="#FFA726", width=2, dash="dot"),
                mode="lines",
            ))
            # Meta Mês (linha horizontal)
            row_meta = df_ind[df_ind["RESPONSAVEL"] == resp_graf]
            if not row_meta.empty:
                meta_mes_val = row_meta.iloc[0]["META_MES"]
                if not np.isnan(meta_mes_val):
                    fig.add_hline(
                        y=meta_mes_val, line_dash="dash", line_color="#F87171",
                        annotation_text=f"Meta Mês: {_fmt_br(meta_mes_val)}",
                        annotation_position="right",
                    )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#CBD5E0"),
                xaxis=dict(gridcolor="#2D3748", title="Data"),
                yaxis=dict(gridcolor="#2D3748", title="Peças (acumulado)"),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                height=380, margin=dict(l=20, r=20, t=20, b=20),
                separators=",.",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados diários disponíveis para este prestador no mês selecionado.")

    st.markdown("---")

    # ── Seção 4 — Análise de Custos por Centro de Custo ───────────────────────
    st.markdown("<div class='sec-header'>💰 Análise de Custos e Receita por Centro de Custo</div>", unsafe_allow_html=True)

    if not df_ind.empty:
        df_cc = df_ind.groupby("CENTRO_CUSTO", as_index=False).agg(
            META_MES=("META_MES", "sum"),
            REALIZADO=("REALIZADO", "sum"),
            PROJECAO=("PROJECAO", "sum"),
            RECEITA_PREV=("RECEITA_PREV", "sum"),
            RECEITA_PROJ=("RECEITA_PROJ", "sum"),
            CUSTO_PREV=("CUSTO_PREV", "sum"),
            CUSTO_PROJ=("CUSTO_PROJ", "sum"),
            MARGEM_PROJ=("MARGEM_PROJ", "sum"),
        )

        # Gráfico barras: produção
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Bar(name="Meta Mês", x=df_cc["CENTRO_CUSTO"], y=df_cc["META_MES"], marker_color="#5C677D"))
        fig_prod.add_trace(go.Bar(name="Realizado", x=df_cc["CENTRO_CUSTO"], y=df_cc["REALIZADO"], marker_color="#4ECDC4"))
        fig_prod.add_trace(go.Bar(name="Projeção", x=df_cc["CENTRO_CUSTO"], y=df_cc["PROJECAO"], marker_color="#FFA726", opacity=0.7))
        fig_prod.update_layout(
            barmode="group", height=320,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"), xaxis=dict(gridcolor="#2D3748"),
            yaxis=dict(gridcolor="#2D3748", title="Peças"),
            legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10,r=10,t=10,b=10),
            separators=",.",
        )
        st.plotly_chart(fig_prod, use_container_width=True)

        # Gráfico financeiro
        fig_fin = go.Figure()
        fig_fin.add_trace(go.Bar(name="Receita Prevista", x=df_cc["CENTRO_CUSTO"], y=df_cc["RECEITA_PREV"], marker_color="#2A9D5C"))
        fig_fin.add_trace(go.Bar(name="Receita Projetada", x=df_cc["CENTRO_CUSTO"], y=df_cc["RECEITA_PROJ"], marker_color="#4ADE80"))
        fig_fin.add_trace(go.Bar(name="Custo Projetado", x=df_cc["CENTRO_CUSTO"], y=df_cc["CUSTO_PROJ"], marker_color="#F87171"))
        fig_fin.add_trace(go.Bar(name="Margem Projetada", x=df_cc["CENTRO_CUSTO"], y=df_cc["MARGEM_PROJ"], marker_color="#FCD34D"))
        fig_fin.update_layout(
            barmode="group", height=320,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"), xaxis=dict(gridcolor="#2D3748"),
            yaxis=dict(gridcolor="#2D3748", title="R$"),
            legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10,r=10,t=10,b=10),
            separators=",.",
        )
        st.plotly_chart(fig_fin, use_container_width=True)

        # Tabela de margem
        tbl_cc = df_cc.copy()
        for col in ["META_MES", "REALIZADO", "PROJECAO"]:
            tbl_cc[col] = tbl_cc[col].apply(lambda v: _fmt_br(v))
        for col in ["RECEITA_PREV", "RECEITA_PROJ", "CUSTO_PREV", "CUSTO_PROJ", "MARGEM_PROJ"]:
            tbl_cc[col] = tbl_cc[col].apply(_fmt_reais)
        tbl_cc.columns = [
            "Centro Custo", "Meta Mês", "Realizado", "Projeção",
            "Receita Prev.", "Receita Proj.", "Custo Prev.", "Custo Proj.", "Margem Proj.",
        ]
        st.dataframe(tbl_cc, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Seção 5 — Gerador do Próximo Mês ──────────────────────────────────────
    if IS_ADMIN:
        prox_mes_num = mes_sel.month % 12 + 1
        prox_ano_num = mes_sel.year + (1 if mes_sel.month == 12 else 0)
        prox_label   = f"{_MESES_PT_LABEL.get(prox_mes_num, str(prox_mes_num))}/{prox_ano_num}"

        st.markdown(f"<div class='sec-header'>📥 Gerador de Plano — {prox_label}</div>", unsafe_allow_html=True)
        st.markdown(
            f"Gera uma planilha `.xlsx` com a estrutura idêntica ao plano de metas atual, "
            f"mas com **META MÊS** e **META DIÁRIA** recalibradas pelo rendimento real de "
            f"{meses_labels[mes_sel]}. Prestadores sem produção registrada mantêm as metas originais.",
            unsafe_allow_html=False,
        )
        if st.button(f"📥 Gerar Plano para {prox_label}", type="primary"):
            with st.spinner("Gerando planilha..."):
                xlsx_bytes = _gerar_proximo_mes_xlsx(
                    df_prev, df_ind,
                    mes_sel.year, mes_sel.month,
                )
            st.download_button(
                label=f"⬇️ Baixar Plano_{prox_label.replace('/', '-')}.xlsx",
                data=xlsx_bytes,
                file_name=f"Plano_Metas_{prox_label.replace('/', '-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


main()
