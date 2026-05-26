# -*- coding: utf-8 -*-
"""Configurações centralizadas de todos os dashboards."""

# ── Página principal ───────────────────────────────────────────────────────────
PAGE_CONFIG = dict(
    page_title="Central de Análise Zanattex | Setores",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Autenticação ───────────────────────────────────────────────────────────────
SENHA_USUARIO = "0102"
SENHA_ADMIN = "adm0102"

# ── Corte (Setor 1 — Giattex / Mantas) ────────────────────────────────────────
CORTE_SHEETS_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
CORTE_SHEETS_GID = "1544210185"
CORTE_CACHE_TTL = 60             # segundos
CORTE_METAS = {"MAQUINA": 7000, "MESA 1": 4000}
CORTE_META_TOTAL = sum(CORTE_METAS.values())

# ── Corte Iacanga (Setor 2 — Mantas Giattex) ──────────────────────────────────
IACANGA_SHEETS_ID = "14OFOAxrV_DkyrwG6KG8NZT-PeXUV4jezPrPO90rh1DU"
IACANGA_SHEETS_GID = "1362699684"

# ── Faturamento ────────────────────────────────────────────────────────────────
FATURAMENTO_SHEETS_ID = "1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg"
FATURAMENTO_SHEETS_GID = "1255712550"
FATURAMENTO_CACHE_TTL = 300      # segundos

# ── Produção ───────────────────────────────────────────────────────────────────
PRODUCAO_SHEETS_ID = "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y"
PRODUCAO_CACHE_TTL = 120         # segundos

# ── Eficiência de Corte ────────────────────────────────────────────────────────
# Manta Arealva
EFICIENCIA_MANTA_AREALVA_ID = "17ido41trF22ks7HgoJz9XHcJU0oA4SYK"
EFICIENCIA_MANTA_AREALVA_GID = "874592526"

# Lençol Arealva
EFICIENCIA_LENCOL_AREALVA_ID = "1PBb_XS9dsiRMBQt6cnILzUnANTaN9stQ"
EFICIENCIA_LENCOL_AREALVA_GID = "1424027835"

# Cache
EFICIENCIA_CACHE_TTL = 300       # segundos
