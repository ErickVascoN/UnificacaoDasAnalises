"""
Módulo de carregamento otimizado de planilhas Google Sheets.
Estratégia: cache em disco (cache_manager) → download com retry → fallback cache obsoleto
"""

import io
import logging
import time
import pandas as pd
import requests

logger = logging.getLogger(__name__)


def load_sheets_with_retry(
    spreadsheet_id: str,
    gid: str = "0",
    format_type: str = "csv",
    max_retries: int = 3,
    timeout: int = 30,
    ttl: int = 120,
) -> bytes | str | None:
    """
    Carrega planilha do Google Sheets via cache em disco (cache_manager).
    Para CSV: retorna string. Para XLSX: faz download direto e retorna bytes.

    O cache_manager já implementa retry + fallback para dado obsoleto, tornando
    esse dashboard resiliente a timeouts do Google.
    """
    if format_type == "csv":
        from utils.cache_manager import get_raw
        return get_raw(spreadsheet_id, gid, ttl=ttl)

    # XLSX: cache_manager não armazena xlsx — baixa direto com retry
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            return r.content
        except requests.exceptions.Timeout:
            logger.warning("⏱ XLSX timeout tentativa %d/%d", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(min(2 ** attempt, 10))
                timeout = min(timeout + 10, 60)
        except Exception as e:
            logger.error("✗ XLSX erro tentativa %d: %s", attempt + 1, str(e)[:80])
            if attempt < max_retries - 1:
                time.sleep(1)
    return None


def read_csv_from_sheets(
    spreadsheet_id: str,
    gid: str = "0",
    dtype: str | dict = str,
    max_retries: int = 3,
    ttl: int = 120,
) -> pd.DataFrame | None:
    """Carrega CSV do Sheets (via cache) e retorna DataFrame."""
    from utils.cache_manager import get_raw
    content = get_raw(spreadsheet_id, gid, ttl=ttl)
    if content is None:
        return None
    try:
        df = pd.read_csv(io.StringIO(content), dtype=dtype)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all")
        logger.info("✓ DataFrame: %d linhas × %d colunas", len(df), len(df.columns))
        return df
    except Exception as e:
        logger.error("Erro ao parsear CSV: %s", e)
        return None


def read_xlsx_from_sheets(
    spreadsheet_id: str,
    sheet_name: str | int = 0,
    max_retries: int = 3,
) -> pd.DataFrame | None:
    """Carrega XLSX do Sheets e retorna DataFrame."""
    content = load_sheets_with_retry(spreadsheet_id, "0", "xlsx", max_retries)
    if content is None:
        return None
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, engine="openpyxl")
        logger.info("✓ DataFrame: %d linhas × %d colunas", len(df), len(df.columns))
        return df
    except Exception as e:
        logger.error("Erro ao parsear XLSX: %s", e)
        return None


if __name__ == "__main__":
    # Teste rápido
    print("\n" + "=" * 80)
    print("TESTE: Carregamento Otimizado de Sheets")
    print("=" * 80)
    
    # Planilha de Produção Geral
    PROD_ID = "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y"
    
    print("\n[1] Testando CSV via gviz/tq (primeira aba)...")
    df = read_csv_from_sheets(PROD_ID, "0")
    if df is not None:
        print(f"✓ Carregado: {df.shape}")
    else:
        print("✗ Falhou")
    
    print("\n" + "=" * 80)
