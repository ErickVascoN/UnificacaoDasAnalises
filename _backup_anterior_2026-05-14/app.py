"""
Dashboard Unificado - Aplicação Principal
Agregador de dashboards por setor com interface de seleção
Integra: Corte, Produção e Faturamento
"""
import streamlit as st
from config import PAGE_CONFIG, AVAILABLE_SECTORS
from utils.styling import apply_custom_css
from views.home import render_home
from sectors.corte import render as render_corte
from sectors.producao import render as render_producao
from sectors.faturamento import render as render_faturamento


# ========================= CONFIGURAÇÃO DA PÁGINA =========================
st.set_page_config(**PAGE_CONFIG)
apply_custom_css()


# ========================= INICIALIZAÇÃO DE ESTADO =========================
# Força começar na página inicial
if "selected_sector" not in st.session_state:
    st.session_state.selected_sector = None


# ========================= NAVEGAÇÃO PRINCIPAL =========================
def main():
    """Função principal da aplicação"""
    
    # DEBUG: Mostrar estado atual
    # st.write(f"DEBUG: selected_sector = {st.session_state.selected_sector}")
    
    # Sidebar com informações
    with st.sidebar:
        st.title("🎯 Navegação")
        st.divider()
        
        # Botão para voltar à home
        if st.button("🏠 Página Inicial", use_container_width=True):
            st.session_state.selected_sector = None
            st.rerun()
        
        st.divider()
        
        # Links rápidos para setores
        st.subheader("📂 Setores Disponíveis")
        for sector in AVAILABLE_SECTORS:
            if st.button(
                f"📊 {sector.capitalize()}",
                use_container_width=True,
                key=f"sidebar_{sector}"
            ):
                st.session_state.selected_sector = sector
                st.rerun()
        
        st.divider()
        
        # Informações adicionais
        st.subheader("ℹ️ Informações")
        st.info(f"**Total de Setores:** {len(AVAILABLE_SECTORS)}")
        st.caption("🔄 Dados atualizados em tempo real")
        st.caption("📱 Interface responsiva e profissional")
        st.caption("✅ Integração Google Sheets")
    
    # ========================= CONTEÚDO PRINCIPAL =========================
    
    # Se nenhum setor foi selecionado, mostra a página inicial
    if st.session_state.selected_sector is None:
        render_home()
    
    # Caso contrário, renderiza o dashboard do setor selecionado
    else:
        sector = st.session_state.selected_sector
        
        # Roteamento para o dashboard correto
        if sector == "corte":
            render_corte()
        elif sector == "producao":
            render_producao()
        elif sector == "faturamento":
            render_faturamento()
        else:
            st.error(f"❌ Setor '{sector}' não encontrado!")
            st.session_state.selected_sector = None
            st.rerun()


# ========================= EXECUÇÃO =========================
if __name__ == "__main__":
    main()

