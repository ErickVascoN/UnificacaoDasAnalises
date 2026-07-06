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

# plano de metas (aliases de SHEET_ID_METAS/GID_METAS — definidos abaixo)
# METAS_SHEET_ID e METAS_GID são declarados como alias após a definição canônica.

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
    "PREVITTEX MATRIZ":  {"gid": "1938192189", "faccao": "PREVITTEX MATRIZ"},
    "PREVITTEX FILIAL":  {"gid": "1921426222", "faccao": "PREVITTEX FILIAL"},
    "MEGA BARIRI":         {"gid": "1219460477", "faccao": "MEGA BARIRI"},
    "MEGA PREVEN (BOCA)":  {"gid": "431490653",  "faccao": "MEGA PREVEN (BOCA)"},
    # gid 524251509: aba renomeada na planilha de "MEGA PREVEN FILIAL" para
    # "MEGA (CARLINE)" (confirmado com o usuário em 04/07/2026, via htmlview da
    # planilha) — o rótulo antigo fazia a produção real da Carline ser contada
    # como "MEGA PREVEN FILIAL" (que já nem existe mais como aba/facção).
    "MEGA (CARLINE)":      {"gid": "524251509",  "faccao": "MEGA (CARLINE)"},
    # Litex — planilha separada; colunas com nomes diferentes (EMPRESA, TOTAL DE PEÇAS)
    "LITEX (ENFARDAMENTO)": {
        "sheet_id": "1wpCdsgLVv_R14yDkak6OMwXKJjUbvL9p",
        "gid":      "1384006621",
        "faccao":   "LITEX",
        "col_map":  {"cliente": "EMPRESA", "quantidade": "TOTAL"},
    },
}
# Obs: PREVITTEX FILIAL reativada em 30/06/2026 com gid=1921426222. A meta
# JOGO DE CAMA/CORTTEX (antes atribuída a FILIAL) continua cruzando por
# (produto, cliente) com a produção lançada em PREVITTEX MATRIZ.

# Alias de nomes de produtos: como aparecem na planilha → nome canônico das metas.
FACCOES_PRODUTO_ALIAS: dict[str, str] = {
    "OUTLET PRENSADO":       "MANTA PRENSADA",
    "OUTLET C/CINTA":        "MANTA C/CINTA",
    # Fronhas: variantes → canônico
    "FRONHA":                "FRONHA AVULSA",
    "FRONHAS":               "FRONHA AVULSA",
    "FRONHAS PONTO PALITO":  "FRONHA PONTO PALITO",
    # Cobertores: nome curto → canônico
    "BABY":                  "COBERTOR BABY",
    "VELOUR":                "COBERTOR VELOUR",
    "MICRO 180G":            "COBERTOR 180G",
    "MANTA MAGICA":          "MICRO 180G (MAGICA)",
    # Jogos: variantes → canônico
    "JOGO":                  "JOGOS DUPLOS",
    "JOGO DUPLO":            "JOGOS DUPLOS",
    "JOGO DE CAMA":          "JOGOS DUPLOS",
    "JOGOS DE CAMA":         "JOGOS DUPLOS",
    "JOGO CAMA":             "JOGOS DUPLOS",
    "JOGO SIMPLES":          "JOGOS SIMPLES",
    # Ponto palito
    "JG DUPLO PONTO PALITO": "JG PONTO PALITO",
    # Lençol: variantes Litex → canônico
    "LENCOL QE":             "LENCOL AVULSO",
    "LENCOL ST":             "LENCOL AVULSO",
    "LENCOL CS":             "LENCOL AVULSO",
    "LENCOL KING":           "LENCOL AVULSO",
    "LECOL QE":              "LENCOL AVULSO",
}

# Alias de nomes de clientes/empresas: variante na planilha → nome canônico.
# Aplicado tanto na produção quanto nas metas (mesmo nome dos dois lados do match).
# Além destes aliases exatos, o loader também trata qualquer cliente contendo
# "NIAZI" (NIAZI, NIAZITEX, NIAZITTEX…) como NIAZITTEX — mesma empresa que NC INDUSTRIA.
FACCOES_CLIENTE_ALIAS: dict[str, str] = {
    "NC INDUSTRIA": "NIAZITTEX",   # NC Indústria = Niazittex = Niazi (mesma empresa)
}

# Alias de nomes de facções/prestadores: variante encontrada na planilha → nome canônico.
# Usado para unificar grafias diferentes do mesmo prestador (typos na QUARTERIZADAS)
# e para casar os nomes da guia de metas com os nomes da produção.
FACCOES_FACCAO_ALIAS: dict[str, str] = {
    # Typos recorrentes na QUARTERIZADAS
    "NATHIELLY":              "NATCHIELLY",
    # Guia de metas usa nomes diferentes da produção
    "LITTEX":                 "LITEX",
    "CORTINA (GGTTEX)":       "GGTTEX CORTINA",
    "RUTE (ZANATTEX)":        "GGTTEX RUTE",      # Rute Zanattex = GGTTEX (Rute)
    "RUTE ZANATTEX":          "GGTTEX RUTE",      # variante do mesmo nome
    "MEGA FILIAL":            "MEGA PREVEN FILIAL",   # nome na guia de metas → faccao da produção
    "BOCA":                   "MEGA PREVEN (BOCA)",   # variante curta
    "MEGA (BOCA)":            "MEGA PREVEN (BOCA)",   # variante com prefixo MEGA na guia de metas
    "PREVITTEX":              "PREVITTEX MATRIZ",
    "GGTTEX (RUTE)":          "GGTTEX RUTE",          # guia de metas usa parênteses; produção não
    "GGTTEX (CORTINA)":       "GGTTEX CORTINA",       # idem
    # Quarterizadas — nome na guia de metas → nome na aba QUARTERIZADAS
    # "LUIZ CARLOS (ZARO)": "LUIS CARLOS" removido em 04/07/2026 — nem origem nem
    # destino aparecem em nenhum mês de produção; alias morto (ZARO (LUIS) é o
    # nome real usado tanto na produção quanto na guia de metas atual).
    # "RUTE TALITA E TAMARA": "RUTE E TALITA" removido em 04/07/2026 — reescrevia
    # o nome atual e correto da guia de metas ("RUTE TALITA E TAMARA") para um
    # nome antigo que não existe em nenhum mês de produção, fazendo a facção
    # aparecer com o nome errado no relatório e a meta não bater com ninguém.
    "LETICIA (GIATTEX)":      "LETICIA",
    # Facções renomeadas — a planilha de produção ainda lança pelo nome antigo,
    # mas a guia de metas já foi atualizada para o nome novo (confirmado com o
    # usuário em 04/07/2026). Sem isso, a produção real ficava "sem meta" e o
    # nome novo aparecia com 0 produzido.
    "ZANATTA":                "GIATTEX",          # Zanatta virou Giattex
    "PREVITTEX FILIAL":       "MEGA PREVEN MATRIZ",  # Previttex Filial virou Mega Preven Matriz
}

# Metas de facções — guia dentro da planilha de facções (fonte primária)
# Colunas: FACÇÃO, PRODUTO, CLIENTE, META MÊS
FACCOES_GID_METAS = "1797767576"

# Planilha de metas de facções (fonte secundária — planilha separada legada)
SHEET_ID_METAS = "1gOhDE__QZ_AbgXZZZWuLTUfR-P1CYPvh"
GID_METAS      = "1593003426"
METAS_TTL      = 3600  # 1 hora
# Aliases para compatibilidade com 7_Plano_de_Metas.py
METAS_SHEET_ID = SHEET_ID_METAS
METAS_GID      = GID_METAS

# Metas mensais por (produto, cliente, faccao).
# Nomes comparados após normalize_text() — acentos e caixa são ignorados.
# Meta diária = meta_mes / dias_uteis_do_mes.
# ATENÇÃO: este fallback é usado apenas se a planilha acima estiver indisponível.
# Facções que produzem mas não têm entrada aqui aparecem na tabela sem meta.
METAS_FACCOES: list[dict] = [
    # ── CAMESA ─────────────────────────────────────────────────────────────────
    {"produto": "COBERTOR VELOUR",     "cliente": "CAMESA",    "faccao": "PREVITTEX MATRIZ",          "meta_mes": 20_000,  "meta_semana": 5_000},
    {"produto": "MANTA PRENSADA",      "cliente": "CAMESA",    "faccao": "MEGA BARIRI",               "meta_mes": 42_000,  "meta_semana": 7_000},
    {"produto": "MANTA PRENSADA",      "cliente": "CAMESA",    "faccao": "CAROL MENDES",              "meta_mes": 88_000,  "meta_semana": 20_000},
    {"produto": "COBERTOR 180G",       "cliente": "CAMESA",    "faccao": "VANIA CAPOTTI",             "meta_mes": 21_000,  "meta_semana": 5_250},
    {"produto": "COBERTOR 180G",       "cliente": "CAMESA",    "faccao": "JOSIANE STEFANI",           "meta_mes": 7_000,   "meta_semana": 1_750},
    {"produto": "COBERTOR BABY",       "cliente": "CAMESA",    "faccao": "GUSTAVO ITAJU",             "meta_mes": 8_400,   "meta_semana": 2_100},
    {"produto": "COBERTOR BABY",       "cliente": "CAMESA",    "faccao": "KELLY ITAJU",               "meta_mes": 8_400,   "meta_semana": 2_100},
    {"produto": "COBERTOR BABY",       "cliente": "CAMESA",    "faccao": "LITEX",                     "meta_mes": 2_000,   "meta_semana": 500},
    {"produto": "JOGOS DUPLOS",        "cliente": "CAMESA",    "faccao": "GGTTEX RUTE",               "meta_mes": 21_000,  "meta_semana": 5_250},
    {"produto": "FRONHA AVULSA",       "cliente": "CAMESA",    "faccao": "FERNANDA SOUZA",            "meta_mes": 18_000,  "meta_semana": 4_500},
    {"produto": "FRONHA AVULSA",       "cliente": "CAMESA",    "faccao": "FRANCIANE",                 "meta_mes": 18_000,  "meta_semana": 4_500},
    {"produto": "MANTA",               "cliente": "CAMESA",    "faccao": "MARCIA GONÇALVES",          "meta_mes": 33_000,  "meta_semana": 7_500},
    {"produto": "DIVERSOS",            "cliente": "CAMESA",    "faccao": "CAROL MENDES (NATCHIELLY)", "meta_mes": 44_000,  "meta_semana": 10_000},
    {"produto": "MANTA",               "cliente": "CAMESA",    "faccao": "VANIA CONFECÇÕES",          "meta_mes": 55_000,  "meta_semana": 12_500},
    {"produto": "MANTA",               "cliente": "CAMESA",    "faccao": "JOSIANE STEFANI",           "meta_mes": 44_000,  "meta_semana": 10_000},
    {"produto": "MANTA",               "cliente": "CAMESA",    "faccao": "PREVITTEX MATRIZ",          "meta_mes": 55_000,  "meta_semana": 12_500},
    {"produto": "JOGOS DUPLOS",        "cliente": "CAMESA",    "faccao": "RUTE ZANATTEX",             "meta_mes": 66_000,  "meta_semana": 15_000},
    {"produto": "FRONHA AVULSA",       "cliente": "CAMESA",    "faccao": "FRANCIELE LOPES",           "meta_mes": 44_000,  "meta_semana": 10_000},
    # ── BURDAYS ────────────────────────────────────────────────────────────────
    {"produto": "LENCOL AVULSO",       "cliente": "BURDAYS",   "faccao": "RUTE E TALITA",             "meta_mes": 18_000,  "meta_semana": 4_500},
    {"produto": "LENCOL AVULSO",       "cliente": "BURDAYS",   "faccao": "MEGA PREVEN",               "meta_mes": 15_000,  "meta_semana": 3_750},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "FERNANDA SOUZA",            "meta_mes": 18_000,  "meta_semana": 4_500},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "SUZANA",                    "meta_mes": 18_000,  "meta_semana": 4_500},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "ANAILA",                    "meta_mes": 6_000,   "meta_semana": 1_500},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "FRAN ALMERIN",              "meta_mes": 6_000,   "meta_semana": 1_500},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "LITEX",                     "meta_mes": 12_000,  "meta_semana": 3_000},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "RONILDA",                   "meta_mes": 6_000,   "meta_semana": 1_500},
    {"produto": "CORTINA",             "cliente": "BURDAYS",   "faccao": "GGTTEX CORTINA",            "meta_mes": 3_000,   "meta_semana": 750},
    {"produto": "CORTINA",             "cliente": "BURDAYS",   "faccao": "MEGA PREVEN",               "meta_mes": 10_010,  "meta_semana": 2_275},
    {"produto": "LENCOL AVULSO",       "cliente": "BURDAYS",   "faccao": "RUTE ZANATTEX",             "meta_mes": 14_960,  "meta_semana": 3_400},
    {"produto": "LENCOL AVULSO",       "cliente": "BURDAYS",   "faccao": "ZARO TEXTIL",               "meta_mes": 11_000,  "meta_semana": 2_500},
    {"produto": "CORTINA",             "cliente": "BURDAYS",   "faccao": "MARCELA",                   "meta_mes": 10_010,  "meta_semana": 2_275},
    {"produto": "PORTA",               "cliente": "BURDAYS",   "faccao": "SUZANA",                    "meta_mes": 44_000,  "meta_semana": 10_000},
    {"produto": "MANTA",               "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 199_980, "meta_semana": 45_450},
    {"produto": "KIT COLCHA",          "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 39_996,  "meta_semana": 9_090},
    {"produto": "PROTETOR",            "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 17_996,  "meta_semana": 4_090},
    {"produto": "JOGOS DUPLOS",        "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 29_986,  "meta_semana": 6_815},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 110_000, "meta_semana": 25_000},
    {"produto": "LENCOL AVULSO",       "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 79_992,  "meta_semana": 18_180},
    {"produto": "PORTA",               "cliente": "BURDAYS",   "faccao": "ZANATTA",                   "meta_mes": 66_000,  "meta_semana": 15_000},
    {"produto": "SHERPA",              "cliente": "BURDAYS",   "faccao": "KELLY",                     "meta_mes": 49_940,  "meta_semana": 11_350},
    {"produto": "FRONHA AVULSA",       "cliente": "BURDAYS",   "faccao": "FRANCIANE",                 "meta_mes": 22_000,  "meta_semana": 5_000},
    # ── SEVEN ──────────────────────────────────────────────────────────────────
    {"produto": "FRONHA PLUSH",        "cliente": "SEVEN",     "faccao": "LITEX",                     "meta_mes": 4_500,   "meta_semana": 1_125},
    {"produto": "LENCOL AVULSO",       "cliente": "SEVEN",     "faccao": "LITEX",                     "meta_mes": 5_000,   "meta_semana": 1_250},
    {"produto": "FRONHA AVULSA",       "cliente": "SEVEN",     "faccao": "FRANCIANE",                 "meta_mes": 9_900,   "meta_semana": 2_475},
    {"produto": "FRONHA AVULSA",       "cliente": "SEVEN",     "faccao": "SUZANA",                    "meta_mes": 15_500,  "meta_semana": 3_875},
    {"produto": "FRONHA AVULSA",       "cliente": "SEVEN",     "faccao": "LITEX",                     "meta_mes": 6_000,   "meta_semana": 1_500},
    # ── CORTTEX ────────────────────────────────────────────────────────────────
    {"produto": "JOGOS DUPLOS",        "cliente": "CORTTEX",   "faccao": "MEGA PREVEN",               "meta_mes": 24_500,  "meta_semana": 6_125},
    {"produto": "JOGOS SIMPLES",       "cliente": "CORTTEX",   "faccao": "MEGA PREVEN",               "meta_mes": 10_000,  "meta_semana": 2_500},
    {"produto": "JOGOS DUPLOS",        "cliente": "CORTTEX",   "faccao": "PREVITTEX MATRIZ",          "meta_mes": 77_000,  "meta_semana": 17_500},
    {"produto": "JOGOS DUPLOS",        "cliente": "CORTTEX",   "faccao": "RUTE ZANATTEX",             "meta_mes": 11_220,  "meta_semana": 2_550},
    {"produto": "MANTA",               "cliente": "CORTTEX",   "faccao": "ZANATTA",                   "meta_mes": 132_000, "meta_semana": 30_000},
    {"produto": "JOGOS DUPLOS",        "cliente": "CORTTEX",   "faccao": "ZARO TEXTIL",               "meta_mes": 26_400,  "meta_semana": 6_000},
    # ── DECOR ──────────────────────────────────────────────────────────────────
    {"produto": "CORTINA",             "cliente": "DECOR",     "faccao": "GGTTEX CORTINA",            "meta_mes": 5_390,   "meta_semana": 1_348},
    # ── FORTEX ─────────────────────────────────────────────────────────────────
    {"produto": "MANTA",               "cliente": "FORTEX",    "faccao": "ZANATTA",                   "meta_mes": 99_000,  "meta_semana": 22_500},
    # ── MARCELINO ──────────────────────────────────────────────────────────────
    {"produto": "JG PONTO PALITO",     "cliente": "MARCELINO", "faccao": "MEGA PREVEN",               "meta_mes": 3_500,   "meta_semana": 875},
    {"produto": "FRONHA PONTO PALITO", "cliente": "MARCELINO", "faccao": "MEGA PREVEN",               "meta_mes": 3_500,   "meta_semana": 875},
    {"produto": "JOGOS DUPLOS",        "cliente": "MARCELINO", "faccao": "ZANATTEX (RUTE)",           "meta_mes": 44_000,  "meta_semana": 10_000},
    {"produto": "JOGOS DUPLOS",        "cliente": "MARCELINO", "faccao": "ZARO TEXTIL",               "meta_mes": 22_000,  "meta_semana": 5_000},
    {"produto": "JOGOS DUPLOS",        "cliente": "MARCELINO", "faccao": "MEGA PREVEN",               "meta_mes": 22_000,  "meta_semana": 5_000},
    # ── SULTAN ─────────────────────────────────────────────────────────────────
    {"produto": "LENCOL AVULSO",       "cliente": "SULTAN",    "faccao": "LUIS CARLOS",               "meta_mes": 2_500,   "meta_semana": 625},
    {"produto": "CORTINA",             "cliente": "SULTAN",    "faccao": "GGTTEX CORTINA",            "meta_mes": 600,     "meta_semana": 150},
    {"produto": "FRONHA AVULSA",       "cliente": "SULTAN",    "faccao": "FERNANDA SOUZA",            "meta_mes": 66_000,  "meta_semana": 15_000},
    {"produto": "AVULSOS",             "cliente": "SULTAN",    "faccao": "PREVITTEX MATRIZ",          "meta_mes": 66_000,  "meta_semana": 15_000},
    {"produto": "FRONHA AVULSA",       "cliente": "SULTAN",    "faccao": "FRANCIELE LOPES",           "meta_mes": 44_000,  "meta_semana": 10_000},
    {"produto": "MANTA",               "cliente": "SULTAN",    "faccao": "ZANATTA",                   "meta_mes": 132_000, "meta_semana": 30_000},
    {"produto": "JOGOS DUPLOS",        "cliente": "SULTAN",    "faccao": "ZANATTA",                   "meta_mes": 44_000,  "meta_semana": 10_000},
    {"produto": "AVULSOS",             "cliente": "SULTAN",    "faccao": "ZARO TEXTIL",               "meta_mes": 11_000,  "meta_semana": 2_500},
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
