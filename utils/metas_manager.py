"""Gerenciador de metas de facções.

Hierarquia de fontes:
  1. Planilha Google Sheets (SHEET_ID_METAS / GID_METAS) — fonte principal, via cache_manager.
  2. data/metas_faccoes.json — override local (editor da UI).
  3. config/settings.py (METAS_FACCOES) — fallback hardcoded.
"""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path

import pandas as pd

from utils.normalize import normalize_text, is_blank

logger = logging.getLogger(__name__)

_PATH = Path("data/metas_faccoes.json")


# ── helpers ────────────────────────────────────────────────────────────────────

def _col(df: pd.DataFrame, *substrings: str) -> str | None:
    """Primeira coluna cujo nome normalizado contém todos os substrings."""
    for col in df.columns:
        col_n = normalize_text(col)
        if all(normalize_text(s) in col_n for s in substrings):
            return col
    return None


def _to_int(v) -> int:
    try:
        return int(float(str(v).replace(".", "").replace(",", ".").strip()))
    except Exception:
        return 0


# ── carregador da planilha ─────────────────────────────────────────────────────

def _parse_sheet_csv(csv_text: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(io.StringIO(csv_text), dtype=str)
    except Exception as e:
        logger.warning("metas_sheet: erro ao parsear CSV: %s", e)
        return None


def _rows_from_df(
    df: pd.DataFrame,
    c_cliente: str,
    c_faccao: str,
    c_produto: str,
    c_meta_mes: str,
    c_meta_dia: str | None,
    c_status: str | None,
    c_data: str | None,
    source: str,
) -> list[dict] | None:
    if c_status:
        mask = df[c_status].str.upper().str.strip().str.contains("REALIZADO", na=False)
        df = df[mask].copy()

    df["_meta_mes"] = df[c_meta_mes].apply(_to_int)
    df = df[df["_meta_mes"] > 0].copy()
    if df.empty:
        return None

    if c_meta_dia:
        df["_meta_semana"] = df[c_meta_dia].apply(lambda v: _to_int(v) * 5)
    else:
        df["_meta_semana"] = (df["_meta_mes"] / 4.4).astype(int)

    if c_data:
        from utils.date_parser import parse_date_series
        df["_data_base"] = parse_date_series(df[c_data])
        df = df.sort_values("_data_base", ascending=False, na_position="last")
        df = df.drop_duplicates(subset=[c_cliente, c_faccao, c_produto], keep="first")

    rows: list[dict] = []
    for _, row in df.iterrows():
        cliente = str(row[c_cliente]).strip().upper()
        faccao  = str(row[c_faccao]).strip().upper()
        produto = str(row[c_produto]).strip().upper()
        if is_blank(cliente) or is_blank(faccao) or is_blank(produto):
            continue
        rows.append({
            "produto":     produto,
            "cliente":     cliente,
            "faccao":      faccao,
            "meta_mes":    int(row["_meta_mes"]),
            "meta_semana": int(row["_meta_semana"]),
        })

    logger.info("%s: %d metas carregadas.", source, len(rows))
    return rows or None


def load_metas_from_faccoes_sheet(ttl: int = 3600) -> list[dict] | None:
    """
    Lê a guia de metas dentro da planilha de facções (FACCOES_SHEET_ID / FACCOES_GID_METAS).
    Colunas: FACÇÃO, PRODUTO, METAS  (CLIENTE é opcional — quando ausente, meta vale para todos).
    """
    from utils.cache_manager import get_raw
    from config.settings import FACCOES_SHEET_ID, FACCOES_GID_METAS

    csv_text = get_raw(FACCOES_SHEET_ID, FACCOES_GID_METAS, ttl=ttl)
    if not csv_text:
        return None

    df = _parse_sheet_csv(csv_text)
    if df is None:
        return None

    c_faccao   = _col(df, "FACCAO") or _col(df, "RESPONSAVEL") or _col(df, "PRESTADOR")
    c_produto  = _col(df, "PRODUTO")
    # Detecta coluna de meta: aceita "META MÊS", "META MES", "METAS", "META"
    c_meta_mes = _col(df, "META", "MES") or _col(df, "METAS") or _col(df, "META")
    c_cliente  = _col(df, "CLIENTE")  # opcional

    if not all([c_faccao, c_produto, c_meta_mes]):
        logger.warning(
            "faccoes_metas: colunas obrigatórias não encontradas. Disponíveis: %s",
            df.columns.tolist(),
        )
        return None

    # Quando não há CLIENTE, cria coluna vazia (sentinel "__ALL__")
    if not c_cliente:
        df["__CLIENTE__"] = "__ALL__"
        c_cliente = "__CLIENTE__"
        logger.info("faccoes_metas: sem coluna CLIENTE — metas valem para todos os clientes.")

    df["_meta_mes"] = df[c_meta_mes].apply(_to_int)
    df = df[df["_meta_mes"] > 0].copy()
    if df.empty:
        return None

    df["_meta_semana"] = (df["_meta_mes"] / 4.4).astype(int)

    # Aplica aliases de facção para casar com os nomes usados na produção
    try:
        from config.settings import FACCOES_FACCAO_ALIAS
        fac_alias = {normalize_text(k): v.upper() for k, v in FACCOES_FACCAO_ALIAS.items()}
    except Exception:
        fac_alias = {}

    rows: list[dict] = []
    for _, row in df.iterrows():
        faccao_raw = str(row[c_faccao]).strip().upper()
        produto_raw = str(row[c_produto]).strip().upper()
        cliente = str(row[c_cliente]).strip().upper()
        if is_blank(faccao_raw) or is_blank(produto_raw):
            continue

        # Aplica alias de facção
        faccao = fac_alias.get(normalize_text(faccao_raw), faccao_raw)

        meta_mes    = int(row["_meta_mes"])
        meta_semana = int(row["_meta_semana"])

        rows.append({
            "produto":     produto_raw,
            "cliente":     "" if cliente == "__ALL__" else cliente,
            "faccao":      faccao,
            "meta_dia":    meta_mes,   # campo "METAS" da planilha = diário
            "meta_mes":    0,          # calculado na página com du_mes real
            "meta_semana": meta_semana,
        })

    logger.info("faccoes_metas_sheet: %d metas carregadas.", len(rows))
    return rows or None


def load_metas_from_sheet(sheet_id: str, gid: str, ttl: int = 3600) -> list[dict] | None:
    """
    Baixa metas da planilha Google Sheets via cache_manager.
    Retorna None se indisponível ou sem colunas reconhecíveis.

    Colunas esperadas (detectadas por substring, insensível a acentos e caixa):
      CLIENTE, RESPONSAVEL (= facção), PRODUTO, META MES, META DIA, STATUS, DATA BASE
    """
    from utils.cache_manager import get_raw

    csv_text = get_raw(sheet_id, gid, ttl=ttl)
    if not csv_text:
        return None

    df = _parse_sheet_csv(csv_text)
    if df is None:
        return None

    c_cliente  = _col(df, "CLIENTE")
    c_faccao   = (_col(df, "RESPONSAVEL") or _col(df, "FACCAO") or _col(df, "PRESTADOR"))
    c_produto  = _col(df, "PRODUTO")
    c_meta_mes = _col(df, "META", "MES")
    c_meta_dia = _col(df, "META", "DIA")
    c_status   = _col(df, "STATUS")
    c_data     = _col(df, "DATA", "BASE")

    if not all([c_cliente, c_faccao, c_produto, c_meta_mes]):
        logger.warning(
            "metas_sheet: colunas obrigatórias não encontradas. Disponíveis: %s",
            df.columns.tolist(),
        )
        return None

    return _rows_from_df(
        df, c_cliente, c_faccao, c_produto, c_meta_mes,
        c_meta_dia=c_meta_dia, c_status=c_status, c_data=c_data,
        source="metas_sheet_legado",
    )


# ── API pública ────────────────────────────────────────────────────────────────

def load_metas() -> list[dict]:
    """
    Carrega metas na ordem de prioridade:
      1. Guia de metas dentro da planilha de facções (FACCOES_GID_METAS) — fonte primária
      2. Planilha de metas legada (SHEET_ID_METAS / GID_METAS)
      3. JSON local (data/metas_faccoes.json)
      4. config/settings.py (METAS_FACCOES)
    """
    from config.settings import SHEET_ID_METAS, GID_METAS, METAS_TTL, METAS_FACCOES

    faccoes_metas = load_metas_from_faccoes_sheet(ttl=METAS_TTL)
    if faccoes_metas:
        return faccoes_metas

    sheet_metas = load_metas_from_sheet(SHEET_ID_METAS, GID_METAS, ttl=METAS_TTL)
    if sheet_metas:
        return sheet_metas

    if _PATH.exists():
        try:
            return json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    return [dict(m) for m in METAS_FACCOES]


def save_metas(lista: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_metas() -> None:
    """Remove o JSON local, voltando a usar a planilha ou config/settings.py."""
    if _PATH.exists():
        _PATH.unlink()
