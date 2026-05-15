"""
Página Inicial - Seleção de Setor
"""
import streamlit as st
from config import SHEETS_CONFIG
from utils.styling import create_sector_card


def render_home():
    """Renderiza a página inicial com seleção de setores"""
    
    # Título e descrição
    st.title("📊 Dashboard Unificado - Análise por Setor")
    st.markdown("""
    Bem-vindo ao Dashboard Unificado! Selecione um setor abaixo para visualizar 
    análises detalhadas de dados em tempo real.
    """)
    
    st.divider()
    
    # Seção de seleção de setores
    st.subheader("🎯 Escolha um Setor para Análise")
    
    # Criar grid de setores
    cols = st.columns(len(SHEETS_CONFIG))
    
    for idx, (sector_key, sector_config) in enumerate(SHEETS_CONFIG.items()):
        with cols[idx]:
            # Renderizar card do setor
            card_html = create_sector_card(
                icon=sector_config.get("icon", "📊"),
                title=sector_key.capitalize(),
                description=sector_config.get("descrição", ""),
                selected=False
            )
            
            # Botão para selecionar o setor
            if st.button(
                f"{sector_config.get('icon', '📊')} {sector_key.upper()}",
                key=f"btn_{sector_key}",
                use_container_width=True,
                help=sector_config.get("descrição", "")
            ):
                st.session_state.selected_sector = sector_key
                st.rerun()
    
    st.divider()
    
    # Seção de informações
    st.subheader("ℹ️ Informações")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"📌 Total de Setores: **{len(SHEETS_CONFIG)}")
    
    with col2:
        st.info("🔄 Dados atualizados em tempo real")
    
    with col3:
        st.info("⚡ Integrado com Google Sheets")
    
    # Seção com estatísticas
    st.divider()
    st.subheader("📈 Setores Disponíveis")
    
    sector_list = []
    for sector_key, config in SHEETS_CONFIG.items():
        sector_list.append({
            "Setor": f"{config.get('icon', '📊')} {sector_key.capitalize()}",
            "Descrição": config.get("descrição", ""),
        })
    
    import pandas as pd
    df_setores = pd.DataFrame(sector_list)
    st.dataframe(df_setores, use_container_width=True, hide_index=True)
    
    st.markdown("""
    ---
    ### 📖 Como usar:
    1. Clique em um setor acima para ver o dashboard específico
    2. Explore os gráficos e métricas interativas
    3. Use os filtros para refinar os dados
    4. Exporte dados em CSV quando necessário
    5. Volte à página inicial para trocar de setor (clique em "Página Inicial" na sidebar)
    """)


if __name__ == "__main__":
    render_home()

