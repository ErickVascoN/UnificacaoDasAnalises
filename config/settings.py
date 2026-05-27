"""Configurações centralizadas de todos os dashboards."""
from __future__ import annotations

# página principal
PAGE_CONFIG = dict(
    page_title="Central de Análise Zanattex | Setores",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# autenticação
SENHA_USUARIO = "0102"
SENHA_ADMIN = "adm0102"

# corte (setor 1 — arealva / mantas)
CORTE_SHEETS_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
CORTE_SHEETS_GID = "1544210185"
CORTE_CACHE_TTL = 60             # segundos
CORTE_METAS = {"MAQUINA": 7000, "MESA 1": 4000}
CORTE_META_TOTAL = sum(CORTE_METAS.values())

# corte iacanga (setor 2 — mantas giattex)
IACANGA_SHEETS_ID = "14OFOAxrV_DkyrwG6KG8NZT-PeXUV4jezPrPO90rh1DU"
IACANGA_SHEETS_GID = "1362699684"

# faturamento
FATURAMENTO_SHEETS_ID = "1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg"
FATURAMENTO_SHEETS_GID = "1255712550"
FATURAMENTO_CACHE_TTL = 300      # segundos

# produção
PRODUCAO_SHEETS_ID = "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y"
PRODUCAO_CACHE_TTL = 120         # segundos

# plano de metas
METAS_SHEET_ID = "1gOhDE__QZ_AbgXZZZWuLTUfR-P1CYPvh"
METAS_GID      = "1593003426"

# Mapeamento CENTRO DE CUSTO (normalizado) → planilha de lançamentos diários.
# Apenas os IDs são fixos; produtos, metas e preços vêm da leitura dinâmica.
LANCAMENTOS_SHEETS = {
    "GGTTEX": {
        "id": "1SGOeT2nZZyxvKNeMftHc7tkv_KQuPt15",
        "gid": "296216772",
        "col_qtd": "TOTAL PRODUZIDO",
        "col_worker": "PRESTADOR",
        "col_empresa": "EMPRESA",
        "col_data": "DATA PRODUÇÃO",
    },
    "ZANATTEX": {
        "id": "1XzfLwE86G59zNvrT_kfi3R9i7DEz4RA8",
        "gid": "410924690",
        "col_qtd": "TOTAL PRODUZIDO",
        "col_worker": "NOME",
        "col_empresa": "EMPRESA",
        "col_data": "DATA PRODUÇÃO",
    },

    "ZANATTA": {
        "id": "1XzfLwE86G59zNvrT_kfi3R9i7DEz4RA8",
        "gid": "410924690",
        "col_qtd": "TOTAL PRODUZIDO",
        "col_worker": "NOME",
        "col_empresa": "EMPRESA",
        "col_data": "DATA PRODUÇÃO",
    },
    "LITEX_FRONHA": {
        "id": "1AbVSR614bCyJYWf2wq8WOM-XeK4oN4sT",
        "gid": "410924690",
        "col_qtd": "TOTAL PRODUZIDO",
        "col_worker": "PRESTADOR(A)",
        "col_empresa": "EMPRESA",
        "col_data": "DATA PRODUÇÃO",
    },
    "LITEX_GERAL": {
        "id": "1SF2ZumsloWdUVAMt1SRYd1o5gNIY9RXD",
        "gid": "1697720285",
        "col_qtd": "TOTAL CONFERIDO",
        "col_worker": "PRESTADOR",
        "col_empresa": "CLIENTE",
        "col_data": "DATA",
    },
    # GIATEX, MEGA PREVEN, ESPECIAL, PREVITTEX, ZANATTA → cobertos pelo xlsx de Produção Geral
}

# Grupos de CENTRO DE CUSTO (normalizado) → chave(s) em LANCAMENTOS_SHEETS
CENTRO_CUSTO_PARA_LANCAMENTO = {
    "GGTTEX": ["GGTTEX"],
    "GGTEX":  ["GGTTEX"],
    "ZANATTEX": ["ZANATTEX"],
    "ZANATTA":  ["ZANATTA"],
    "LITEX":    ["LITEX_FRONHA", "LITEX_GERAL"],
    # Demais → apenas Produção Geral (xlsx)
}

METAS_CACHE_TTL = 300  # segundos

# equivalência de nomes de prestadores
# Mapeia variante (uppercase, sem acento) → nome canônico nas planilhas de produção.
# Entradas manuais têm PRIORIDADE sobre a detecção automática por similaridade ≥90%.
# Chave e valor devem estar normalizados: uppercase, sem acento, sem espaços extras.
# Exemplo de uso:
#   "MARIA A SILVA":   "MARIA APARECIDA SILVA",
#   "JOSE C SANTOS":   "JOSE CARVALHO SANTOS",
NOME_EQUIVALENCIAS: dict[str, str] = {
    # Adicione aqui aliases permanentes conforme forem identificados:
}

# eficiência de corte
# Manta Arealva
EFICIENCIA_MANTA_AREALVA_ID = "17ido41trF22ks7HgoJz9XHcJU0oA4SYK"
EFICIENCIA_MANTA_AREALVA_GID = "874592526"

# Lençol Arealva
EFICIENCIA_LENCOL_AREALVA_ID = "1PBb_XS9dsiRMBQt6cnILzUnANTaN9stQ"
EFICIENCIA_LENCOL_AREALVA_GID = "1424027835"

# Cache
EFICIENCIA_CACHE_TTL = 300       # segundos
