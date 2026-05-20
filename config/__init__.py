# -*- coding: utf-8 -*-
"""
Backward-compat: pages/3_Controle_de_Corte.py usa `from config import ...`
Este __init__ re-exporta os nomes que a página espera.
"""
from .settings import (
    CORTE_SHEETS_ID as GOOGLE_SHEETS_ID,
    CORTE_SHEETS_GID as GOOGLE_SHEETS_GID,
    CORTE_METAS as METAS,
    CORTE_META_TOTAL as META_TOTAL,
    CORTE_CACHE_TTL as CACHE_TTL,
)


def get_google_sheets_urls() -> list[str]:
    from utils.google_sheets import build_export_urls
    return build_export_urls(GOOGLE_SHEETS_ID, GOOGLE_SHEETS_GID)
