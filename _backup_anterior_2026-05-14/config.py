"""
Configurações centralizadas do Dashboard Unificado
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ========================= CONFIGURAÇÕES GOOGLE SHEETS =========================
# Configurações dos dashboards por setor
SHEETS_CONFIG = {
    "corte": {
        "sheet_id": "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW",
        "sheet_gid": None,  # Automático (primeira aba)
        "icon": "✂️",
        "descrição": "Análise de dados do setor de Corte",
        "cor_primaria": "#FF6B6B"
    },
    "producao": {
        "sheet_id": "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y",
        "sheet_gid": None,
        "icon": "🏭",
        "descrição": "Análise de dados do setor de Produção",
        "cor_primaria": "#4ECDC4"
    },
    "faturamento": {
        "sheet_id": "1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg",
        "sheet_gid": 1255712550,
        "icon": "📈",
        "descrição": "Análise de Produtos Faturados",
        "cor_primaria": "#0C6E74"
    },
}

# ========================= CONFIGURAÇÕES STREAMLIT =========================
PAGE_CONFIG = {
    "page_title": "Dashboard Unificado - Análise por Setor",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ========================= CONFIGURAÇÕES DE TEMA =========================
THEME_CONFIG = {
    "primaryColor": "#0066cc",
    "backgroundColor": "#ffffff",
    "secondaryBackgroundColor": "#f0f2f6",
    "textColor": "#262730",
    "font": "sans serif"
}

# ========================= CACHE =========================
CACHE_DURATION = 300  # 5 minutos em segundos

# ========================= CREDENCIAIS GOOGLE SHEETS =========================
# Para funcionamento adequado, configure uma conta de serviço no Google Cloud
# E defina a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS apontando para o JSON
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# ========================= SETORES DISPONÍVEIS =========================
AVAILABLE_SECTORS = list(SHEETS_CONFIG.keys())
