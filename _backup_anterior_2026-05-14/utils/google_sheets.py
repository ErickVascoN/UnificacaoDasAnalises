"""
Integração com Google Sheets
"""
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
import streamlit as st
from config import CACHE_DURATION


@st.cache_data(ttl=CACHE_DURATION)
def load_sheet_data(sheet_id: str, sheet_name: str) -> pd.DataFrame:
    """
    Carrega dados de uma planilha Google Sheets.
    
    Args:
        sheet_id: ID da planilha (parte da URL)
        sheet_name: Nome da aba dentro da planilha
        
    Returns:
        DataFrame com os dados
    """
    try:
        # Autenticação com Google Sheets
        gc = gspread.oauth()
        sheet = gc.open_by_key(sheet_id)
        worksheet = sheet.worksheet(sheet_name)
        
        # Converter para DataFrame
        df = get_as_dataframe(worksheet, evaluate_formulas=True)
        df = df.dropna(how='all')  # Remove linhas completamente vazias
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados de '{sheet_name}': {str(e)}")
        return pd.DataFrame()


def load_multiple_sheets(sheet_configs: dict) -> dict:
    """
    Carrega dados de múltiplas abas da mesma planilha.
    
    Args:
        sheet_configs: Dicionário com configurações de abas
                      {"aba_nome": "Nome da Aba", ...}
        
    Returns:
        Dicionário com DataFrames carregados
    """
    data = {}
    for key, config in sheet_configs.items():
        data[key] = load_sheet_data(config["sheet_id"], config["sheet_name"])
    return data
