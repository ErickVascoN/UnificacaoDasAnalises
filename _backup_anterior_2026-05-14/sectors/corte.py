"""
Dashboard - Setor de Corte
Dashboard integrado com dados do Google Sheets
Adaptado do projeto DashboardAnaliseCorte
"""
import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime
from views.dashboard_base import DashboardBase
from config import SHEETS_CONFIG


class CorteDashboard(DashboardBase):
    """Dashboard específico para o setor de Corte"""
    
    def load_data(self):
        """Carrega dados via CSV export do Google Sheets"""
        if self.data is None:
            sheet_id = self.config.get("sheet_id")
            sheet_gid = self.config.get("sheet_gid")
            
            # Tenta múltiplas URLs de fallback
            urls = [
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv",
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv",
            ]
            
            if sheet_gid:
                urls.extend([
                    f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={sheet_gid}",
                    f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={sheet_gid}",
                ])
            
            df = None
            for url in urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        df = pd.read_csv(io.StringIO(response.text))
                        df = df.dropna(how='all')
                        if not df.empty:
                            self.data = df
                            return df
                except Exception as e:
                    continue
            
            if df is None or df.empty:
                st.error("❌ Erro ao carregar dados do Google Sheets. Verifique o Sheet ID.")
                self.data = pd.DataFrame()
        
        return self.data
    
    def render_dashboard(self):
        """Renderiza o dashboard completo de Corte"""
        self.render_header()
        
        df = self.load_data()
        
        if df.empty:
            st.error("❌ Nenhum dado disponível para o setor de Corte.")
            return
        
        # ========== MÉTRICAS PRINCIPAIS ==========
        st.subheader("📊 Métricas Principais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total de Registros",
                f"{len(df):,}",
                border=True
            )
        
        with col2:
            st.metric(
                "Colunas de Dados",
                f"{len(df.columns)}",
                border=True
            )
        
        with col3:
            st.metric(
                "Última Atualização",
                datetime.now().strftime("%H:%M"),
                border=True
            )
        
        with col4:
            st.metric(
                "Status",
                "Ativo ✓",
                border=True
            )
        
        st.divider()
        
        # ========== FILTROS ==========
        st.subheader("🔍 Filtros e Análises")
        
        with st.expander("📋 Opções de Visualização", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if len(df.columns) > 0:
                    selected_columns = st.multiselect(
                        "Colunas para exibir:",
                        df.columns.tolist(),
                        default=df.columns.tolist()[:5] if len(df.columns) >= 5 else df.columns.tolist()
                    )
                else:
                    selected_columns = df.columns.tolist()
            
            with col2:
                limit = st.number_input("Limite de registros:", 1, len(df), min(100, len(df)))
            
            with col3:
                sort_column = st.selectbox("Ordenar por:", [None] + df.columns.tolist()) if len(df.columns) > 0 else None
        
        st.divider()
        
        # ========== DADOS DETALHADOS ==========
        st.subheader("📋 Dados Detalhados")
        
        # Aplicar filtros
        df_filtered = df.copy()
        
        if sort_column and sort_column is not None:
            try:
                df_filtered = df_filtered.sort_values(by=sort_column, ascending=False)
            except:
                pass
        
        df_filtered = df_filtered.head(limit)
        
        # Selecionar colunas
        if 'selected_columns' in locals() and len(selected_columns) > 0:
            display_columns = [col for col in selected_columns if col in df_filtered.columns]
            df_to_show = df_filtered[display_columns] if display_columns else df_filtered
        else:
            df_to_show = df_filtered
        
        st.dataframe(df_to_show, use_container_width=True)
        
        # Estatísticas básicas
        st.subheader("📊 Estatísticas Básicas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Linhas Exibidas", len(df_to_show))
        
        with col2:
            st.metric("Total de Linhas (Completo)", len(df))
        
        with col3:
            st.metric("Taxa de Exibição", f"{(len(df_to_show)/len(df)*100):.1f}%")
        
        st.divider()
        
        # ========== EXPORTAÇÃO ==========
        st.subheader("⬇️ Exportar Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Baixar Todos os Dados (CSV)",
                data=csv,
                file_name=f"corte_dados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            csv_filtered = df_filtered.to_csv(index=False)
            st.download_button(
                label="📥 Baixar Dados Filtrados (CSV)",
                data=csv_filtered,
                file_name=f"corte_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )


def render():
    """Renderiza o dashboard de Corte"""
    dashboard = CorteDashboard("corte")
    dashboard.render_dashboard()


if __name__ == "__main__":
    render()
