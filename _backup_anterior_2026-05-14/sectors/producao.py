"""
Dashboard - Setor de Produção
Dashboard integrado com dados do Google Sheets
Adaptado do projeto DashboardAnaliseProducaoGeral
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime
from views.dashboard_base import DashboardBase
from config import SHEETS_CONFIG


class ProducaoDashboard(DashboardBase):
    """Dashboard específico para o setor de Produção"""
    
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
                st.error("❌ Erro ao carregar dados do Google Sheets.")
                self.data = pd.DataFrame()
        
        return self.data
    
    def render_dashboard(self):
        """Renderiza o dashboard completo de Produção"""
        self.render_header()
        
        df = self.load_data()
        
        if df.empty:
            st.error("❌ Nenhum dado disponível para o setor de Produção.")
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
                "Eficiência Geral",
                "95.2%",
                delta="+1.5%",
                border=True
            )
        
        with col3:
            st.metric(
                "Rendimento",
                "98.2%",
                delta="-0.3%",
                border=True
            )
        
        with col4:
            st.metric(
                "Disponibilidade",
                "99.1%",
                border=True
            )
        
        st.divider()
        
        # ========== ABAS DE ANÁLISE ==========
        tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "📊 Detalhes", "📋 Dados"])
        
        with tab1:
            st.write("""
            **Visão Geral de Produção**
            
            Esta aba mostra as métricas agregadas e comparações gerais de desempenho.
            """)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.success(f"✅ Registros Carregados: {len(df)}")
            
            with col2:
                st.info(f"📌 Colunas de Dados: {len(df.columns)}")
            
            with col3:
                st.info(f"🕐 Hora da Consulta: {datetime.now().strftime('%H:%M:%S')}")
            
            # Gráfico de distribuição (se houver dados numéricos)
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                st.subheader("📊 Distribuição de Valores")
                try:
                    fig = px.box(df, y=numeric_cols[:1], title="Distribuição do Primeiro Campo Numérico")
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    pass
        
        with tab2:
            st.write("""
            **Detalhes por Linha de Produção**
            
            Analise o desempenho detalhado de cada linha individualmente.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if len(df.columns) > 0:
                    groupby_col = st.selectbox("Agrupar por:", df.columns.tolist())
                    if groupby_col:
                        try:
                            grouped = df.groupby(groupby_col).size().reset_index(name='Quantidade')
                            st.dataframe(grouped, use_container_width=True)
                        except:
                            st.info("Não foi possível agrupar os dados.")
            
            with col2:
                st.info("""
                **💡 Dicas:**
                - Selecione uma coluna para agrupar
                - Veja a quantidade de registros por grupo
                - Use os dados para identificar gargalos
                """)
        
        with tab3:
            st.write("""
            **Dataset Completo**
            
            Visualize todos os dados carregados da planilha.
            """)
            
            col1, col2 = st.columns([0.8, 0.2])
            
            with col1:
                st.write(f"Total de **{len(df)}** registros carregados")
            
            with col2:
                show_all = st.checkbox("Expandir", value=False)
            
            if show_all:
                st.dataframe(df, use_container_width=True)
            else:
                st.dataframe(df.head(15), use_container_width=True)
        
        st.divider()
        
        # ========== FILTROS AVANÇADOS ==========
        st.subheader("🔍 Filtros Avançados")
        
        with st.expander("Opções de Filtro", expanded=False):
            if len(df.columns) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    filter_column = st.selectbox("Coluna para filtrar:", df.columns.tolist())
                
                with col2:
                    if filter_column:
                        unique_values = df[filter_column].unique()[:20]
                        selected_value = st.selectbox("Valor:", unique_values)
                        
                        if selected_value:
                            df_filtered = df[df[filter_column] == selected_value]
                            st.write(f"**Registros encontrados:** {len(df_filtered)}")
                            st.dataframe(df_filtered, use_container_width=True)
        
        st.divider()
        
        # ========== EXPORTAÇÃO ==========
        st.subheader("⬇️ Exportar Dados")
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Dados Completos (CSV)",
            data=csv,
            file_name=f"producao_dados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )


def render():
    """Renderiza o dashboard de Produção"""
    dashboard = ProducaoDashboard("producao")
    dashboard.render_dashboard()


if __name__ == "__main__":
    render()
