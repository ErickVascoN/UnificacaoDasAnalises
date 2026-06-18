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
CORTE_SHEETS_ID = "1KLbNpw-P28YgoijXfMXU-zRQULuDHMMB"
CORTE_SHEETS_GID = "1544210185"
CORTE_CACHE_TTL = 60             # segundos
CORTE_METAS = {"MAQUINA": 7000, "MESA 1": 4000}
CORTE_META_TOTAL = sum(CORTE_METAS.values())

# corte iacanga (setor 2 — mantas giattex)
IACANGA_SHEETS_ID = "1FBpCrq29_e1UBNwBlcgPTz66tbpUsgcgtzfXi4DcORU"
IACANGA_SHEETS_GID = "0"

# faturamento
FATURAMENTO_SHEETS_ID = "1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg"
FATURAMENTO_SHEETS_GID = "1255712550"
FATURAMENTO_CACHE_TTL = 300      # segundos

# produção
PRODUCAO_SHEETS_ID = "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y"
PRODUCAO_CACHE_TTL = 120         # segundos

# produção — colaboradores internos (4 unidades, cada uma uma guia/tab)
# Planilhas com título mesclado embutido no cabeçalho, datas M/D/YYYY e
# quantidade com ponto de milhar → o loader detecta colunas por substring,
# usa parse_date_series e limpa os números (ver utils/producao_interno_loader.py).
PRODUCAO_INTERNO_SHEETS = {
    "LITTEX":         {"id": "1wpCdsgLVv_R14yDkak6OMwXKJjUbvL9p", "gid": "1697720285", "label": "LITTEX",         "icon": "🧵", "date_order": "MDY"},
    "GGTTEX_JOGOS":   {"id": "1b8gCNUqZagkINAN1egnA7Va6g6Bv4esv", "gid": "410924690",  "label": "GGTTEX Jogos",   "icon": "🛏️", "date_order": "MDY"},
    "GGTTEX_FRONHA":  {"id": "1b8gCNUqZagkINAN1egnA7Va6g6Bv4esv", "gid": "671875370",  "label": "GGTTEX Fronha",  "icon": "🛌", "date_order": "MDY"},
    "GGTTEX_CORTINA": {"id": "1PG5t_aWif2iJiCyEtgKE6sLFvMu7w5sL", "gid": "296216772",  "label": "GGTTEX Cortina", "icon": "🪟", "date_order": "MDY"},
}
PRODUCAO_INTERNO_CACHE_TTL = 300  # segundos

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

# ── Produção externa (facções / prestadores) ──────────────────────────────────
# Planilha Google Sheets com uma aba por facção: DATA, PRODUTO, CLIENTE, QUANTIDADE.
FACCOES_SHEET_ID  = "1V05lVI-HlZXpGTc1p3R2V7ddnMTTjSOQ"
FACCOES_CACHE_TTL = 300  # segundos

# Mapeamento de cada aba → facção. A aba é baixada por GID (confiável); o nome
# do gviz `?sheet=` não é confiável (quando a aba está vazia/oculta ele devolve a
# primeira aba no lugar — causava produção trocada de facção).
#
# Cada entrada:
#   "gid":          id numérico da aba no Google Sheets (estável).
#   "faccao":       nome fixo da facção (None quando vem do prestador).
#   "por_prestador" (opcional): True → a FACÇÃO de cada linha é o PRESTADOR.
#       Usado na aba QUARTERIZADAS, onde cada prestador terceirizado é uma facção.
FACCOES_ABAS: dict[str, dict] = {
    "QUARTERIZADAS":    {"gid": "994268246",  "faccao": None, "por_prestador": True},
    "GGTTEX (RUTE)":    {"gid": "1265193869", "faccao": "GGTTEX RUTE"},
    "GGTTEX (CORTINA)": {"gid": "1766002384", "faccao": "GGTTEX CORTINA"},
    "ZANATTA":          {"gid": "670406828",  "faccao": "ZANATTA"},
    "PREVITTEX MATRIZ": {"gid": "1938192189", "faccao": "PREVITTEX MATRIZ"},
    "MEGA BARIRI":      {"gid": "1219460477", "faccao": "MEGA BARIRI"},
    "MEGA PREVEN":      {"gid": "431490653",  "faccao": "MEGA PREVEN"},
    # Litex — planilha separada; colunas com nomes diferentes (EMPRESA, TOTAL DE PEÇAS)
    "LITEX (ENFARDAMENTO)": {
        "sheet_id": "1wpCdsgLVv_R14yDkak6OMwXKJjUbvL9p",
        "gid":      "1384006621",
        "faccao":   "LITEX",
        "col_map":  {"cliente": "EMPRESA", "quantidade": "TOTAL"},
    },
}
# Obs: PREVITTEX FILIAL não está mais entre as abas visíveis da planilha. A meta
# JOGO DE CAMA/CORTTEX (antes atribuída a FILIAL) continua cruzando por
# (produto, cliente) com a produção lançada em PREVITTEX MATRIZ.

# Alias de nomes de produtos: como aparecem na planilha → nome canônico das metas.
FACCOES_PRODUTO_ALIAS: dict[str, str] = {
    "OUTLET PRENSADO": "MANTA PRENSADA",
    "OUTLET C/CINTA":  "MANTA C/CINTA",
    "FRONHA":          "FRONHAS",
    "JOGO":            "JOGO DE CAMA",
    "JOGOS DE CAMA":   "JOGO DE CAMA",
    "MANTA MAGICA":    "COBERTOR 180G",   # Manta Mágica é 180g = Cobertor 180G
    # Litex: variantes de lençol → nome canônico
    "LENCOL QE":       "LENCOL AVULSO",
    "LENCOL ST":       "LENCOL AVULSO",
    "LENCOL CS":       "LENCOL AVULSO",
    "LENCOL KING":     "LENCOL AVULSO",
    "LECOL QE":        "LENCOL AVULSO",   # typo frequente na planilha
}

# Alias de nomes de clientes/empresas: variante na planilha → nome canônico.
# Aplicado tanto na produção quanto nas metas (mesmo nome dos dois lados do match).
# Além destes aliases exatos, o loader também trata qualquer cliente contendo
# "NIAZI" (NIAZI, NIAZITEX, NIAZITTEX…) como NIAZITTEX — mesma empresa que NC INDUSTRIA.
FACCOES_CLIENTE_ALIAS: dict[str, str] = {
    "NC INDUSTRIA": "NIAZITTEX",   # NC Indústria = Niazittex = Niazi (mesma empresa)
}

# Metas mensais por (produto, cliente, faccao).
# Nomes comparados após normalize_text() — acentos e caixa são ignorados.
# Meta diária é calculada dinamicamente: meta_mes / dias_uteis_do_mes.
METAS_FACCOES: list[dict] = [
    {"produto": "COBERTOR TOQUE DE SEDA", "cliente": "NIAZITTEX",     "faccao": "MEGA BARIRI",      "meta_mes": 30_000,  "meta_semana": 7_500},
    {"produto": "MANTA",                  "cliente": "NIAZITTEX",     "faccao": "MEGA BARIRI",      "meta_mes": 13_000,  "meta_semana": 3_250},
    {"produto": "FRONHAS",                "cliente": "BURDAYS",       "faccao": "LITEX",            "meta_mes": 250_000, "meta_semana": 62_500},
    {"produto": "LENCOL AVULSO",          "cliente": "BURDAYS",       "faccao": "ZANATTEX",         "meta_mes": 110_000, "meta_semana": 27_500},
    {"produto": "CORTINA",                "cliente": "ANDREZA",       "faccao": "GGTTEX",           "meta_mes": 15_000,  "meta_semana": 3_750},
    {"produto": "MANTA BABY",             "cliente": "ANDREZA",       "faccao": "PREVITTEX MATRIZ", "meta_mes": 20_000,  "meta_semana": 5_000},
    {"produto": "JOGO DE CAMA",           "cliente": "CAMESA",        "faccao": "PREVITTEX MATRIZ", "meta_mes": 50_000,  "meta_semana": 12_500},
    {"produto": "FRONHAS",                "cliente": "CAMESA",        "faccao": "ZANATTEX",         "meta_mes": 100_000, "meta_semana": 25_000},
    {"produto": "VELOUR",                 "cliente": "CAMESA",        "faccao": "PREVITTEX MATRIZ", "meta_mes": 33_000,  "meta_semana": 8_250},
    {"produto": "MANTA PRENSADA",         "cliente": "CAMESA",        "faccao": "ZANATTEX",         "meta_mes": 200_000, "meta_semana": 50_000},
    {"produto": "MANTA C/CINTA",          "cliente": "CAMESA",        "faccao": "ZANATTEX",         "meta_mes": 15_000,  "meta_semana": 3_750},
    {"produto": "COBERTOR 180G",          "cliente": "CAMESA",        "faccao": "ZANATTEX",         "meta_mes": 63_000,  "meta_semana": 15_750},
    {"produto": "BABY",                   "cliente": "CAMESA",        "faccao": "ZANATTEX",         "meta_mes": 70_000,  "meta_semana": 17_500},
    {"produto": "JOGO DE CAMA",           "cliente": "CORTTEX",       "faccao": "PREVITTEX FILIAL", "meta_mes": 14_000,  "meta_semana": 3_500},
    {"produto": "CORTINA",                "cliente": "DECOR",         "faccao": "GGTTEX",           "meta_mes": 10_000,  "meta_semana": 2_500},
    {"produto": "JOGO DE CAMA",           "cliente": "DECOR",         "faccao": "GGTTEX",           "meta_mes": 5_000,   "meta_semana": 1_250},
    {"produto": "CORTINA",                "cliente": "SULTAN",        "faccao": "ZANATTEX",         "meta_mes": 60_000,  "meta_semana": 15_000},
    {"produto": "FRONHAS",                "cliente": "SULTAN",        "faccao": "ZANATTEX",         "meta_mes": 10_000,  "meta_semana": 2_500},
    {"produto": "JG DUPLO PONTO PALITO",  "cliente": "MARCELINO",     "faccao": "MEGA PREVEN",      "meta_mes": 4_000,   "meta_semana": 1_000},
    {"produto": "FRONHAS PONTO PALITO",   "cliente": "MARCELINO",     "faccao": "MEGA PREVEN",      "meta_mes": 20_000,  "meta_semana": 5_000},
    {"produto": "FRONHAS",                "cliente": "SEVEN",         "faccao": "ZANATTEX",         "meta_mes": 80_000,  "meta_semana": 20_000},
    {"produto": "LENCOL AVULSO",          "cliente": "SEVEN",         "faccao": "ZANATTEX",         "meta_mes": 20_000,  "meta_semana": 5_000},
    {"produto": "FRONHA PLUSH",           "cliente": "SEVEN",         "faccao": "ZANATTEX",         "meta_mes": 18_000,  "meta_semana": 4_500},
]

# eficiência de corte
# Manta Arealva
EFICIENCIA_MANTA_AREALVA_ID = "1MDk2B2m8IA4IJn2yKvjFwyTyAnYbvACo"
EFICIENCIA_MANTA_AREALVA_GID = "874592526"

# Lençol Arealva
EFICIENCIA_LENCOL_AREALVA_ID = "18i48EIx-c7V5kyFt2Zxl6NmXwgvq9NSR"
EFICIENCIA_LENCOL_AREALVA_GID = "1424027835"

# Cache
EFICIENCIA_CACHE_TTL = 300       # segundos
