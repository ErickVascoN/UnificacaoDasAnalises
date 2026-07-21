"""
Carregador da planilha de produção externa (facções / prestadores).

Planilha única Google Sheets com múltiplas abas — uma por facção.
Estrutura de cada aba: DATA, PRODUTO, CLIENTE, QUANTIDADE
  (+ PRESTADOR na aba QUARTERIZADAS).
Colunas depois da primeira vazia são tabelas de referência lateral e ignoradas.

Camada padronizada: usa cache_manager.get_raw_sheet, date_parser e normalize.
"""

from __future__ import annotations

import io
import logging

import pandas as pd

from utils.cache_manager import get_raw
from utils.date_parser import parse_date_series
from utils.normalize import normalize_text

logger = logging.getLogger(__name__)

_BLANKS = frozenset({"", "NAN", "NONE", "N/A", "NA", "NAT", "-", "--", "DD/MM/AAAA"})


def _find_col(cols: list[str], *terms: str) -> str | None:
    """Retorna a 1ª coluna cujo nome normalizado contém algum dos termos."""
    for col in cols:
        cn = normalize_text(col)
        if any(normalize_text(t) in cn for t in terms if t):
            return col
    return None


def _parse_qty(series: pd.Series) -> pd.Series:
    """'1.234' → 1234; '1.234,5' → 1234; vazio → 0. Retorna inteiro."""
    s = (
        series.astype(str)
        .str.strip()
        .str.replace(r"[R$\s]", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)


def _load_tab(
    sheet_id: str, tab_name: str, cfg: dict, ttl: int
) -> pd.DataFrame | None:
    """Carrega uma aba individual (por GID) e retorna DataFrame normalizado."""
    # Permite planilha diferente por aba (ex: Litex usa outra spreadsheet)
    effective_sheet_id = cfg.get("sheet_id", sheet_id)
    content = get_raw(effective_sheet_id, cfg["gid"], ttl=ttl)
    if not content or not content.strip():
        logger.warning("Tab %r (gid=%s): sem dados / indisponível", tab_name, cfg["gid"])
        return None

    raw = pd.read_csv(io.StringIO(content), dtype=str, header=0)
    raw.columns = [str(c).strip() for c in raw.columns]

    # Trunca na primeira coluna sem nome (separa dados da tabela de referência lateral)
    cols = list(raw.columns)
    stop = next(
        (i for i, c in enumerate(cols) if c.startswith("Unnamed:")), len(cols)
    )
    raw = raw.iloc[:, :stop]
    cols = list(raw.columns)

    # col_map permite sobrescrever o termo de busca por campo (ex: EMPRESA no lugar de CLIENTE)
    col_map_cfg = cfg.get("col_map", {})

    def _col(field: str, *defaults: str) -> str | None:
        if field in col_map_cfg:
            return _find_col(cols, col_map_cfg[field])
        return _find_col(cols, *defaults)

    col_data  = _col("data",       "DATA")
    col_prod  = _col("produto",    "PRODUTO")
    col_cli   = _col("cliente",    "CLIENTE")
    col_qtd   = _col("quantidade", "QUANTIDADE")
    col_prest = _col("prestador",  "PRESTADOR")
    col_obs   = _col("observacao", "OBSERVACAO", "OBS")

    if not all([col_data, col_prod, col_cli, col_qtd]):
        logger.warning(
            "Tab %r: colunas essenciais não encontradas. Disponíveis: %s",
            tab_name, cols,
        )
        return None

    # fillna ANTES do astype(str): no pandas 3.x, astype(str) não converte
    # células ausentes (NaN real) em string "nan" — o valor permanece float,
    # escapando dos filtros de "vazios" abaixo e quebrando comparações/sorted().
    out = pd.DataFrame()
    out["DATA"]       = raw[col_data]
    out["PRODUTO"]    = raw[col_prod].fillna("").astype(str).str.strip().str.upper()
    out["CLIENTE"]    = raw[col_cli].fillna("").astype(str).str.strip().str.upper()
    out["QUANTIDADE"] = _parse_qty(raw[col_qtd])
    out["ABA"]        = tab_name.strip()
    out["PRESTADOR"]  = (
        raw[col_prest].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.upper()
        if col_prest
        else ""
    )
    # Texto livre — preserva a caixa digitada (diferente de PRODUTO/CLIENTE/
    # PRESTADOR, que são canonizados em upper para casar com aliases).
    out["OBSERVACAO"] = (
        raw[col_obs].fillna("").astype(str).str.strip()
        if col_obs
        else ""
    )

    # Facção: nome fixo da config OU o próprio prestador (abas quarterizadas, onde
    # cada prestador terceirizado é uma facção). Sem prestador → rótulo genérico.
    if cfg.get("por_prestador"):
        out["FACCAO"] = out["PRESTADOR"].where(
            out["PRESTADOR"].str.strip() != "", "QUARTERIZADA (S/ NOME)"
        )
    else:
        out["FACCAO"] = cfg["faccao"]

    # Datas: gviz exporta no formato M/D/YYYY (locale US do Google)
    out["DATA"] = parse_date_series(out["DATA"], default_order="MDY")

    # Corrige datas que caíram no futuro por causa de mistura de formatos na
    # mesma coluna — ex.: aba QUARTERIZADAS/MEGA PREVEN (BOCA), onde a maioria
    # das linhas vem do Google Sheets em M/D/YYYY, mas linhas digitadas à mão
    # usam DD/MM/YYYY. parse_date_series detecta UM formato pra coluna inteira
    # (correto pra evitar inversão dia/mês linha-a-linha), mas quando a coluna
    # é genuinamente mista, isso pode inverter dia/mês de linhas ambíguas do
    # formato minoritário — ex.: "6/12/2026" (12 de junho) virou 6 de dezembro,
    # aparecendo como a "última data" da facção no dashboard em vez de julho.
    # Produção real nunca é no futuro: se a data ficou depois de hoje E dia e
    # mês são ambos ≤12 (logo dava pra inverter), tenta a versão invertida e
    # usa se ela não for futura. Reportado pelo usuário 15/07/2026.
    _hoje = pd.Timestamp.now().normalize()
    def _corrigir_data_futura(ts):
        if pd.isna(ts) or ts <= _hoje:
            return ts
        d, m = ts.day, ts.month
        if d <= 12 and m <= 12:
            try:
                alt = pd.Timestamp(year=ts.year, month=d, day=m)
                if alt <= _hoje:
                    return alt
            except ValueError:
                pass
        return ts
    out["DATA"] = out["DATA"].apply(_corrigir_data_futura)

    # Remove linhas inválidas (placeholder, sem quantidade, etc.). Exceção:
    # QUANTIDADE=0 com Observação preenchida é um dia sem produção só pra
    # contextualização (ex.: "máquina quebrou") — mantém a linha pra aparecer
    # no dashboard/relatório, mas com QUANTIDADE=0 (não entra em nenhuma soma
    # nem conta como dia de produção nas médias — ver utils/faccoes_metas_calc.py
    # e as telas que calculam dias/média). Pedido do usuário 14/07/2026.
    raw_data_upper = raw[col_data].fillna("").astype(str).str.strip().str.upper()
    tem_obs = out["OBSERVACAO"].str.strip() != ""
    valid = (
        ~raw_data_upper.isin(_BLANKS)
        & out["DATA"].notna()
        & ((out["QUANTIDADE"] > 0) | tem_obs)
        & ~out["PRODUTO"].str.upper().isin(_BLANKS)
        & ~out["CLIENTE"].str.upper().isin(_BLANKS)
    )
    out = out[valid].reset_index(drop=True)

    _fac_log = "POR PRESTADOR" if cfg.get("por_prestador") else cfg["faccao"]
    logger.info("✓ %r → %s: %d linhas", tab_name.strip(), _fac_log, len(out))
    return out


def load_faccoes() -> pd.DataFrame:
    """
    Carrega e unifica todas as abas da planilha de facções externas.

    Returns
    -------
    DataFrame com colunas: DATA, FACCAO, ABA, PRESTADOR, PRODUTO, CLIENTE,
    QUANTIDADE, OBSERVACAO.
    Vazio em caso de erro ou planilha indisponível.
    """
    from config.settings import (
        FACCOES_SHEET_ID,
        FACCOES_CACHE_TTL,
        FACCOES_ABAS,
        FACCOES_PRODUTO_ALIAS,
        FACCOES_CLIENTE_ALIAS,
    )

    dfs = []
    for tab_name, cfg in FACCOES_ABAS.items():
        df = _load_tab(FACCOES_SHEET_ID, tab_name, cfg, FACCOES_CACHE_TTL)
        if df is not None and not df.empty:
            dfs.append(df)

    if not dfs:
        logger.error("load_faccoes: nenhuma aba retornou dados")
        return pd.DataFrame()

    result = pd.concat(dfs, ignore_index=True)

    # Remove linhas onde PRODUTO == FACCAO — artefato de linhas de cabeçalho/grupo
    # na aba QUARTERIZADAS onde o nome do prestador aparece como "produto".
    result = result[
        result["PRODUTO"].str.upper() != result["FACCAO"].str.upper()
    ].reset_index(drop=True)

    # Aplica alias de produtos (OUTLET PRENSADO → MANTA PRENSADA, FRONHA → FRONHAS, etc.)
    prod_alias = {normalize_text(k): v for k, v in FACCOES_PRODUTO_ALIAS.items()}
    result["PRODUTO"] = result["PRODUTO"].apply(
        lambda p: prod_alias.get(normalize_text(p), p)
    )

    # Aplica alias de clientes. Duas regras:
    #   1) alias exato (ex: NC INDUSTRIA → NIAZITTEX);
    #   2) qualquer cliente contendo "NIAZI" (NIAZI, NIAZITEX, NIAZITTEX…) → NIAZITTEX,
    #      mesma empresa que NC INDUSTRIA. Segue o padrão já usado em
    #      pages/2_Producao_Geral.py (_load_niazitex_suplementar filtra por "NIAZI").
    cli_alias = {normalize_text(k): v for k, v in FACCOES_CLIENTE_ALIAS.items()}

    def _canon_cliente(c: str) -> str:
        cn = normalize_text(c)
        if cn in cli_alias:
            return cli_alias[cn]
        if "NIAZI" in cn:
            return "NIAZITTEX"
        return c

    result["CLIENTE"] = result["CLIENTE"].apply(_canon_cliente)

    try:
        from utils.db_manager import upsert_df
        upsert_df(result, "faccoes", ["DATA", "FACCAO", "PRODUTO", "PRESTADOR", "CLIENTE"])
    except Exception:
        logger.warning("db_manager: falha ao salvar faccoes no banco local", exc_info=True)

    return result

