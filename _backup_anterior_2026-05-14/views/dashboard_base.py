"""
Template Base para Dashboards de Setor
Use este arquivo como referência para criar novos dashboards
"""
import streamlit as st
import pandas as pd
from utils.google_sheets import load_sheet_data
from config import SHEETS_CONFIG


class DashboardBase:
    """Classe base para construir dashboards de setores"""
    
    def __init__(self, sector_key: str):
        """
        Inicializa o dashboard de um setor.
        
        Args:
            sector_key: Chave do setor em SHEETS_CONFIG
        """
        self.sector_key = sector_key
        self.config = SHEETS_CONFIG.get(sector_key, {})
        self.data = None
    
    def load_data(self) -> pd.DataFrame:
        """Carrega dados do Google Sheets"""
        if self.data is None:
            self.data = load_sheet_data(
                self.config.get("sheet_id"),
                self.config.get("sheet_name", "Dados")
            )
        return self.data
    
    def render_header(self):
        """Renderiza o cabeçalho do dashboard"""
        icon = self.config.get("icon", "📊")
        title = self.sector_key.capitalize()
        
        st.title(f"{icon} Dashboard - {title}")
        
        # Botão para voltar
        col1, col2 = st.columns([0.9, 0.1])
        with col2:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.selected_sector = None
                st.rerun()
    
    def render_metrics(self, df: pd.DataFrame):
        """
        Renderiza métricas básicas.
        Override este método para customizar.
        """
        st.subheader("📈 Métricas Principais")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Registros", len(df))
        
        with col2:
            st.metric("Colunas", len(df.columns))
        
        with col3:
            st.metric("Dados", "Carregado ✓")
    
    def render_data_preview(self, df: pd.DataFrame):
        """Renderiza preview dos dados"""
        st.subheader("📋 Prévia dos Dados")
        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True
        )
    
    def render_dashboard(self):
        """Método principal - override para customizar o layout"""
        self.render_header()
        
        # Carrega dados
        df = self.load_data()
        
        if df.empty:
            st.error("❌ Nenhum dado disponível para este setor.")
            return
        
        # Renderiza componentes
        self.render_metrics(df)
        st.divider()
        self.render_data_preview(df)


def render_sector_dashboard(sector_key: str):
    """
    Função helper para renderizar um dashboard de setor.
    
    Args:
        sector_key: Chave do setor
    """
    dashboard = DashboardBase(sector_key)
    dashboard.render_dashboard()
