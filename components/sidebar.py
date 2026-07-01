"""Componente de sidebar da página inicial."""

from datetime import datetime
import streamlit as st
from utils.auth import clear_auth_session


def render_home_button() -> None:
    """Botão de voltar ao início — adicione no topo de cada sidebar de página."""
    if st.sidebar.button("🏠 Início", use_container_width=True, key="btn_home"):
        st.switch_page("app.py")
    st.sidebar.markdown("---")


def render_sidebar() -> None:
    """Renderiza a barra lateral com autenticação e logout."""
    with st.sidebar:
        st.markdown("### 🏢 Central de Análise Zanattex")
        st.caption("setores — Grupo")

        if st.session_state.auth_nivel:
            nivel_label = (
                "👑 Admin" if st.session_state.auth_nivel == "admin" else "👤 Usuário"
            )
            st.success(f"{nivel_label} · Autenticado")
        else:
            st.info("🔒 Não autenticado")

        st.markdown("---")
        st.caption(
            f"⏱️ Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            "Use os cards abaixo para navegar."
        )
