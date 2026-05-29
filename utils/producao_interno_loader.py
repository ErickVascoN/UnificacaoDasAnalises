"""
Carregador padronizado das planilhas de produção dos COLABORADORES INTERNOS.

São 4 unidades (cada uma vira uma guia no dashboard "Por Colaborador → Interno"):
    LITTEX, GGTTEX Jogos, GGTTEX Fronha, GGTTEX Cortina.

Particularidades dessas planilhas (motivo de existir um loader dedicado):
  - O título mesclado da planilha fica EMBUTIDO no nome de algumas colunas do
    cabeçalho (ex: "LITEX  PRESTADOR", "PRODUÇÃO - FRONHA DATA PRODUÇÃO",
    "PRODUÇÃO JOGO DE LENÇOL RUTE COLABORADOR(A)"). Por isso a coluna é detectada
    por SUBSTRING (case/acento-insensível), não por nome exato.
  - Datas vêm em M/D/YYYY (locale US do Google) → usa date_parser.parse_date_series,
    que detecta o formato pela coluna inteira (evita inverter dia/mês).
  - Quantidade vem com ponto de milhar ("1.186") → limpeza numérica.

Camada padronizada (ver PADROES.md): usa cache_manager, date_parser e normalize.
"""

from __future__ import annotations

import io
import logging

import pandas as pd

from utils.cache_manager import get_raw
from utils.date_parser import parse_date_series
from utils.normalize import normalize_text

logger = logging.getLogger(__name__)


def _achar_coluna(colunas, *termos) -> str | None:
    """
    Retorna o nome ORIGINAL da 1ª coluna cujo nome normalizado contém algum dos
    termos (também normalizados). Comparação por substring, acento/caixa-insensível.
    """
    termos_norm = [normalize_text(t) for t in termos]
    for col in colunas:
        cn = normalize_text(col)
        if any(t and t in cn for t in termos_norm):
            return col
    return None


_TEXTO_VAZIO = {"", "NAN", "NONE", "N/A", "NA", "NAT", "-", "--"}


def _limpar_texto(serie: pd.Series) -> pd.Series:
    """Strip + transforma valores 'vazios' (nan/none/-/...) em string vazia ''."""
    s = serie.astype(str).str.strip()
    return s.where(~s.str.upper().isin(_TEXTO_VAZIO), "")


def _limpar_qtd(serie: pd.Series) -> pd.Series:
    """'1.186' → 1186 ; '1.234,5' → 1234 ; vazio → 0. Inteiro."""
    s = (
        serie.astype(str)
        .str.replace("R$", "", regex=False)
        .str.strip()
        .str.replace(".", "", regex=False)   # ponto de milhar
        .str.replace(",", ".", regex=False)  # vírgula decimal → ponto
    )
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)


def load_interno_unidade(chave: str) -> pd.DataFrame:
    """
    Carrega e normaliza uma das unidades internas.

    Args:
        chave: chave em config.settings.PRODUCAO_INTERNO_SHEETS
               (LITTEX, GGTTEX_JOGOS, GGTTEX_FRONHA, GGTTEX_CORTINA).

    Returns:
        DataFrame com colunas: DATA, COLABORADOR, SETOR, FUNCAO (opcional),
        PRODUTO, CLIENTE, QUANTIDADE. FUNCAO só existe quando a planilha tem
        uma coluna de função. DataFrame vazio em caso de erro.
    """
    from config.settings import PRODUCAO_INTERNO_SHEETS, PRODUCAO_INTERNO_CACHE_TTL

    cfg = PRODUCAO_INTERNO_SHEETS.get(chave)
    if not cfg:
        logger.error(f"Unidade interna desconhecida: {chave}")
        return pd.DataFrame()

    try:
        conteudo = get_raw(cfg["id"], cfg["gid"], ttl=PRODUCAO_INTERNO_CACHE_TTL)
        if not conteudo or not conteudo.strip():
            logger.error(f"{chave}: CSV vazio/indisponível")
            return pd.DataFrame()

        raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
        raw.columns = [str(c).strip() for c in raw.columns]
        cols = list(raw.columns)

        # ── Detecta colunas por conteúdo do nome (substring) ──────────────────
        col_data  = _achar_coluna(cols, "DATA")
        col_colab = _achar_coluna(cols, "PRESTADOR", "COLABORADOR")
        col_qtd   = _achar_coluna(cols, "TOTAL PRODUZIDO", "TOTAL CONFERIDO", "TOTAL")
        col_setor = _achar_coluna(cols, "SETOR")
        col_func  = _achar_coluna(cols, "FUNCAO")          # "FUNÇÃO" → normaliza p/ FUNCAO
        col_prod  = _achar_coluna(cols, "PRODUTO", "DESCRICAO")
        col_cli   = _achar_coluna(cols, "CLIENTE") or _achar_coluna(cols, "EMPRESA")

        if not col_colab or not col_qtd or not col_data:
            logger.error(
                f"{chave}: colunas essenciais não encontradas "
                f"(colab={col_colab}, qtd={col_qtd}, data={col_data}). "
                f"Disponíveis: {cols}"
            )
            return pd.DataFrame()

        out = pd.DataFrame()
        out["DATA"]        = raw[col_data]
        out["COLABORADOR"] = raw[col_colab].astype(str).str.strip()
        out["QUANTIDADE"]  = _limpar_qtd(raw[col_qtd])
        out["SETOR"]       = _limpar_texto(raw[col_setor]) if col_setor else ""
        if col_func:
            out["FUNCAO"]  = _limpar_texto(raw[col_func])
        out["PRODUTO"]     = _limpar_texto(raw[col_prod]) if col_prod else ""
        out["CLIENTE"]     = _limpar_texto(raw[col_cli]) if col_cli else ""

        # ── Datas (detecção de formato por coluna; resolve M/D vs D/M) ─────────
        out["DATA"] = parse_date_series(out["DATA"])

        # ── Limpeza de linhas ──────────────────────────────────────────────────
        # Remove sujeira: sem colaborador real OU sem data OU sem quantidade.
        vazios = {"", "NAN", "NONE", "N/A", "-"}
        tem_colab = ~out["COLABORADOR"].str.upper().isin(vazios)
        out = out[tem_colab & out["DATA"].notna() & (out["QUANTIDADE"] > 0)]
        out = out.reset_index(drop=True)

        # ── Descarta datas de ANO atípico ───────────────────────────────────────
        # Erros de digitação (ex: "5/19/2016" ou "1/8/2025" numa planilha de 2026)
        # geram datas em anos errados que distorcem o filtro de período. Mantém só
        # o ano dominante da coluna (orientado pelos dados, sem depender do relógio).
        if not out.empty and out["DATA"].notna().any():
            _anos = out["DATA"].dt.year
            _ano_dom = int(_anos.mode().iloc[0])
            _bad = _anos != _ano_dom
            if _bad.any():
                _descartadas = sorted({str(d.date()) for d in out.loc[_bad, "DATA"]})
                logger.warning(
                    f"{chave}: {int(_bad.sum())} linha(s) com ano atípico "
                    f"(≠ {_ano_dom}) descartada(s): {_descartadas[:8]}"
                )
                out = out[~_bad].reset_index(drop=True)

        logger.info(f"✓ {chave}: {len(out)} linhas válidas")
        return out

    except Exception as e:
        logger.error(f"{chave}: erro {str(e)[:150]}")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────
# TESTE
# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=logging.INFO)

    from config.settings import PRODUCAO_INTERNO_SHEETS

    for chave in PRODUCAO_INTERNO_SHEETS:
        df = load_interno_unidade(chave)
        print("=" * 70)
        print(f"{chave}: {len(df)} linhas | colunas: {list(df.columns)}")
        if not df.empty:
            print(f"  Periodo: {df['DATA'].min().date()} ate {df['DATA'].max().date()}")
            print(f"  Colaboradores: {df['COLABORADOR'].nunique()}")
            print(f"  Total peças: {df['QUANTIDADE'].sum():,}")
            if "FUNCAO" in df.columns:
                print(f"  Funções: {sorted(df['FUNCAO'].unique())[:8]}")
