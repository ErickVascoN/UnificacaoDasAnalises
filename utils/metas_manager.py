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
import re
from pathlib import Path

import pandas as pd

from utils.date_parser import parse_date_series
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

    cols_list  = list(df.columns)

    c_faccao   = _col(df, "FACCAO") or _col(df, "RESPONSAVEL") or _col(df, "PRESTADOR")
    c_produto  = _col(df, "PRODUTO")
    # Detecta coluna de meta: aceita "META MÊS", "META MES", "METAS", "META"
    c_meta_mes = _col(df, "META", "MES") or _col(df, "METAS") or _col(df, "META")

    if not all([c_faccao, c_produto, c_meta_mes]):
        logger.warning(
            "faccoes_metas: colunas obrigatórias não encontradas. Disponíveis: %s",
            df.columns.tolist(),
        )
        return None

    # ── Tabela secundária (ex: ZANATTA) ────────────────────────────────────────
    # Detecta a segunda ocorrência de FACÇÃO (ex: "FACÇÃO "), que marca o início
    # da tabela lateral. Colunas a partir daí pertencem à tabela secundária e NÃO
    # devem ser usadas para a tabela principal (evita ler CLIENTE do ZANATTA como
    # cliente de CAROL MENDES ou outra facção da tabela principal).
    c_fac2  = next((c for c in cols_list if normalize_text(c).startswith("FACCAO") and c != c_faccao), None)
    _sec_start = cols_list.index(c_fac2) if c_fac2 else len(cols_list)
    _primary_cols = set(cols_list[:_sec_start])

    # CLIENTE da tabela principal: só aceita se a coluna vier ANTES da tabela secundária
    c_cliente = next(
        (c for c in cols_list[:_sec_start] if normalize_text(c).startswith("CLIENTE")),
        None,
    )

    # Alias de facção
    try:
        from config.settings import FACCOES_FACCAO_ALIAS
        fac_alias = {normalize_text(k): v.upper() for k, v in FACCOES_FACCAO_ALIAS.items()}
    except Exception:
        fac_alias = {}

    def _apply_alias(name: str) -> str:
        return fac_alias.get(normalize_text(name), name)

    def _make_entry(faccao: str, produto: str, cliente: str, meta_dia: int) -> dict:
        return {
            "produto":     produto,
            "cliente":     cliente,
            "faccao":      _apply_alias(faccao.strip().upper()),
            "meta_dia":    meta_dia,
            "meta_mes":    0,
            "meta_semana": int(meta_dia * 5),
        }

    # ── Colunas extras da tabela principal ────────────────────────────────────
    # Suporta tanto "Unnamed: N" (cabeçalho vazio) quanto "METAS 2", "METAS 3"
    # (cabeçalhos nomeados). Restringe às colunas primárias para não confundir
    # com colunas da tabela secundária.
    _extra_cols = [
        c for c in cols_list[:_sec_start]
        if (c.startswith("Unnamed:") or re.match(r"METAS?\s*[2-9]", normalize_text(c)))
        and c != c_meta_mes
    ]

    df["_meta_mes"] = df[c_meta_mes].apply(_to_int)
    df = df.copy()
    df["_tem_extras"] = False
    if _extra_cols:
        def _tem_extras_fn(row):
            if row["_meta_mes"] > 0:
                return False
            for c in _extra_cols:
                v = str(row[c]).strip() if pd.notna(row[c]) else ""
                if re.search(r"\d", v):
                    return True
            return False
        df["_tem_extras"] = df.apply(_tem_extras_fn, axis=1)

    # Colunas da tabela secundária
    c_prod2 = next((c for c in cols_list[_sec_start:] if normalize_text(c).startswith("PRODUTO")), None)
    c_meta2 = next((c for c in cols_list[_sec_start:] if normalize_text(c).startswith("META")), None)
    c_cli2  = next((c for c in cols_list[_sec_start:] if normalize_text(c).startswith("CLIENTE")), None)

    rows: list[dict] = []

    # ── Parseia tabela principal ───────────────────────────────────────────────
    df_main = df[(df["_meta_mes"] > 0) | df["_tem_extras"]].copy()
    for _, row in df_main.iterrows():
        faccao_raw  = str(row[c_faccao]).strip().upper()
        produto_raw = str(row[c_produto]).strip().upper()
        # c_cliente pode ser None quando a tabela principal não tem coluna CLIENTE
        cliente_raw = str(row[c_cliente]).strip().upper() if c_cliente else "__ALL__"
        if is_blank(faccao_raw) or is_blank(produto_raw):
            continue

        if row["_tem_extras"]:
            # Linha com metas por cliente em colunas extras (ex: CORTINA)
            for ec in _extra_cols:
                v = str(row[ec]).strip() if pd.notna(row[ec]) else ""
                m = re.match(r"^(.+?)\s+(\d[\d.,]*)$", v.strip())
                if not m:
                    continue
                cli_extra = m.group(1).strip().upper()
                meta_dia  = _to_int(m.group(2))
                if meta_dia > 0 and not is_blank(cli_extra):
                    rows.append(_make_entry(faccao_raw, produto_raw, cli_extra, meta_dia))
        else:
            meta_dia = int(row["_meta_mes"])
            cliente  = "" if (cliente_raw == "__ALL__" or is_blank(cliente_raw)) else cliente_raw
            rows.append(_make_entry(faccao_raw, produto_raw, cliente, meta_dia))

    # ── Parseia tabela secundária (ZANATTA-style: facção+produto+meta+cliente) ─
    if c_fac2 and c_prod2 and c_meta2:
        df_sec = df[df[c_fac2].notna() & (df[c_fac2].str.strip() != "")].copy()
        df_sec["_meta2"] = df_sec[c_meta2].apply(_to_int)
        df_sec = df_sec[df_sec["_meta2"] > 0]
        for _, row in df_sec.iterrows():
            fac2  = str(row[c_fac2]).strip().upper()
            prod2 = str(row[c_prod2]).strip().upper() if pd.notna(row[c_prod2]) else ""
            cli2  = str(row[c_cli2]).strip().upper() if pd.notna(row[c_cli2]) else ""
            meta2 = int(row["_meta2"])
            if is_blank(fac2) or is_blank(prod2):
                continue
            rows.append(_make_entry(fac2, prod2, cli2, meta2))
        logger.info("faccoes_metas_sheet (tabela secundária): %d entradas.", len(df_sec))

    if not rows:
        return None

    logger.info("faccoes_metas_sheet: %d metas carregadas no total.", len(rows))
    return rows


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
