"""
Dashboard - Setor de Faturamento
Dashboard integrado com dados do Google Sheets
Adaptado do projeto "Produtos Faturados"
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
from datetime import datetime
from views.dashboard_base import DashboardBase
from config import SHEETS_CONFIG


class FaturamentoDashboard(DashboardBase):
    """Dashboard específico para o setor de Faturamento"""
    
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
        """Renderiza o dashboard completo de Faturamento"""
        self.render_header()
        
        df = self.load_data()
        
        if df.empty:
            st.error("❌ Nenhum dado disponível para o setor de Faturamento.")
            return
        
        # ========== APLICAR CSS CUSTOMIZADO ==========
        st.markdown("""
        <style>
            .faturamento-hero {
                background: linear-gradient(120deg, #0C6E74, #1D3557);
                border-radius: 15px;
                padding: 20px;
                color: white;
                margin-bottom: 20px;
            }
            .kpi-card {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
                padding: 15px;
                border-left: 4px solid #0C6E74;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # ========== SEÇÃO HERÓI ==========
        st.markdown("""
        <div class="faturamento-hero">
            <h2 style="margin: 0;">💰 Produtos Faturados</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Análise em Tempo Real de Faturamento</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== MÉTRICAS PRINCIPAIS ==========
        st.subheader("📊 KPIs - Indicadores Principais")
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_registros = len(df)
            st.metric(
                "📦 Total de Produtos",
                f"{total_registros:,}",
                border=True
            )
        
        with col2:
            if numeric_cols:
                total_valor = df[numeric_cols[0]].sum() if len(numeric_cols) > 0 else 0
                st.metric(
                    "💵 Valor Total",
                    f"R$ {total_valor:,.2f}",
                    border=True
                )
            else:
                st.metric("💵 Valor Total", "N/A", border=True)
        
        with col3:
            st.metric(
                "📈 Colunas de Dados",
                f"{len(df.columns)}",
                border=True
            )
        
        with col4:
            st.metric(
                "🕐 Atualizado em",
                datetime.now().strftime("%H:%M"),
                border=True
            )
        
        st.divider()
        
        # ========== ABAS DE ANÁLISE ==========
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Dados", "🔍 Filtros", "📥 Exportar"])
        
        with tab1:
            st.subheader("Análises Visuais")
            
            # Gráficos se houver dados numéricos
            if numeric_cols:
                col1, col2 = st.columns(2)
                
                with col1:
                    try:
                        # Gráfico de valores principais
                        fig_top = px.bar(
                            df.head(10),
                            x=df.columns[0] if len(df.columns) > 0 else None,
                            y=numeric_cols[0],
                            title=f"Top 10 - {numeric_cols[0]}",
                            color=numeric_cols[0],
                            color_continuous_scale="Blues"
                        )
                        st.plotly_chart(fig_top, use_container_width=True)
                    except Exception as e:
                        st.info("Não foi possível gerar o gráfico de barras")
                
                with col2:
                    try:
                        # Gráfico de distribuição
                        fig_dist = px.histogram(
                            df,
                            x=numeric_cols[0],
                            nbins=20,
                            title=f"Distribuição - {numeric_cols[0]}",
                            color_discrete_sequence=["#0C6E74"]
                        )
                        st.plotly_chart(fig_dist, use_container_width=True)
                    except Exception as e:
                        st.info("Não foi possível gerar o histograma")
            else:
                st.info("📌 Nenhuma coluna numérica encontrada para gráficos")
            
            # Estatísticas descritivas
            st.subheader("📊 Estatísticas Descritivas")
            if numeric_cols:
                stats_df = df[numeric_cols].describe()
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("Nenhuma coluna numérica para estatísticas")
        
        with tab2:
            st.subheader("Dados Completos")
            
            col1, col2 = st.columns([0.8, 0.2])
            
            with col1:
                st.write(f"**Total:** {len(df)} registros carregados")
            
            with col2:
                show_all = st.checkbox("Ver todos", value=False)
            
            if show_all:
                st.dataframe(df, use_container_width=True)
            else:
                st.dataframe(df.head(20), use_container_width=True)
        
        with tab3:
            st.subheader("Opções de Filtro")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if len(df.columns) > 0:
                    filter_col = st.selectbox("Coluna para filtrar:", df.columns.tolist())
                    
                    if filter_col:
                        unique_vals = df[filter_col].unique()[:50]
                        selected_val = st.multiselect(
                            f"Selecione valores de '{filter_col}':",
                            unique_vals,
                            default=unique_vals[:1] if len(unique_vals) > 0 else []
                        )
                        
                        if selected_val:
                            df_filtered = df[df[filter_col].isin(selected_val)]
                            st.write(f"**Registros encontrados:** {len(df_filtered)}")
                            st.dataframe(df_filtered, use_container_width=True)
            
            with col2:
                st.info("""
                **💡 Como usar filtros:**
                1. Selecione uma coluna
                2. Escolha um ou mais valores
                3. Veja os resultados filtrados
                4. Exporte se necessário
                """)
        
        with tab4:
            st.subheader("Exportar Dados")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Baixar CSV (Completo)",
                    data=csv,
                    file_name=f"faturamento_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Exportar primeiros 100 registros
                csv_limited = df.head(100).to_csv(index=False)
                st.download_button(
                    label="📥 Baixar CSV (Top 100)",
                    data=csv_limited,
                    file_name=f"faturamento_top100_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            st.divider()
            
            st.info("""
            ℹ️ **Informações sobre exportação:**
            - Todos os formatos são em CSV
            - Para Excel, você pode abrir o CSV em qualquer programa
            - Os dados mantêm toda a formatação original
            """)
        
        st.divider()
        
        # ========== RESUMO ==========
        st.subheader("📌 Resumo dos Dados")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Registros", len(df))
        
        with col2:
            st.metric("Colunas", len(df.columns))
        
        with col3:
            st.metric("Tipos de Dados", len(df.dtypes.unique()))
        
        with col4:
            st.metric("Memória (MB)", f"{df.memory_usage(deep=True).sum() / 1024**2:.2f}")


def render():
    """Renderiza o dashboard de Faturamento"""
    dashboard = FaturamentoDashboard("faturamento")
    dashboard.render_dashboard()


if __name__ == "__main__":
    render()
