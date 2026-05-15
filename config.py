"""
Arquivo de configuração do Dashboard - Análise de Corte
Customize aqui as opções da sua planilha Google Sheets
"""

# ================================================================
# CONFIGURAÇÃO DO GOOGLE SHEETS
# ================================================================

# ID da planilha Google Sheets (obrigatório)
# Você encontra na URL: https://docs.google.com/spreadsheets/d/[ID]/edit
GOOGLE_SHEETS_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"

# GID (Grid ID) - Deixe como None para detecção automática (RECOMENDADO)
# Se deixar None, o dashboard sempre carregará a PRIMEIRA ABA da planilha
# Apenas mude isto se souber exatamente qual GID usar
GOOGLE_SHEETS_GID = None  # Automático (primeira aba)

# Alternativas se precisar forçar um GID específico:
# GOOGLE_SHEETS_GID = "206085601"  # GID específico
# GOOGLE_SHEETS_GID = "0"  # Primeira aba


# ================================================================
# METAS DE PRODUÇÃO
# ================================================================

# Metas diárias de produção por estação (peças/dia)
METAS = {
    'MAQUINA': 7000,
    'MESA 1': 4000,
    'MESA 2': 3000
}

# Meta total diária (calculada automaticamente)
META_TOTAL = sum(METAS.values())  # 15.000


# ================================================================
# CACHE
# ================================================================

# Tempo de cache em segundos (quanto menor, mais atualizado mas mais lento)
CACHE_TTL = 60  # 60 segundos


# ================================================================
# FUNÇÃO AUXILIAR
# ================================================================

def get_google_sheets_urls():
    """
    Gera URLs de download do Google Sheets
    Tenta primeiro sem GID (mais confiável), depois com GID se necessário
    """
    urls = []
    
    # URLs sem GID especificado (carrega primeira aba - RECOMENDADO)
    urls.append(f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv")
    urls.append(f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq?tqx=out:csv")
    
    # URLs com GID se foi especificado
    if GOOGLE_SHEETS_GID:
        urls.append(f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv&gid={GOOGLE_SHEETS_GID}")
        urls.append(f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq?tqx=out:csv&gid={GOOGLE_SHEETS_GID}")
    
    return urls
