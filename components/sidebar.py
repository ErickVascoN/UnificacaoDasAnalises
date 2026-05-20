# -*- coding: utf-8 -*-
"""Componente de sidebar da página inicial."""

from datetime import datetime
import streamlit as st
from utils.navigation import safe_switch


def render_sidebar() -> None:
    """Renderiza a barra lateral com autenticação e navegação rápida."""
    with st.sidebar:
        st.markdown("### 🏢 Central de Análise Zanattex")
        st.caption("setores — Grupo")

        if st.session_state.auth_nivel:
            nivel_label = (
                "👑 Admin" if st.session_state.auth_nivel == "admin" else "👤 Usuário"
            )
            st.success(f"{nivel_label} · Autenticado")
            if st.button("🚪 Fazer Logout", use_container_width=True):
                st.session_state.auth_nivel = ""
                st.rerun()
        else:
            st.info("🔓 Não autenticado")

        st.markdown("---")
        st.markdown("**Navegação rápida**")
        st.link_button(
            "⏱️ Central de Controle GUT",
            (
                "https://www.appsheet.com/start/6ab5d5b4-6ceb-4641-be36-26a273f1f303"
                "#appName=ApontadorZanattex-819603934"
                "&group=%5B%7B%22Column%22%3A%22Data%22%2C%22Order%22%3A%22Descending%22%7D%5D"
                "&page=fastTable"
                "&sort=%5B%7B%22Column%22%3A%22Hora%22%2C%22Order%22%3A%22Descending%22%7D"
                "%2C%7B%22Column%22%3A%22Efici%C3%AAncia%22%2C%22Order%22%3A%22Descending%22%7D%5D"
                "&table=GIATTEX&view=GIATTEX"
            ),
            use_container_width=True,
        )
        st.link_button(
            "📈 Análise de Dados GUT",
            "https://datastudio.google.com/u/0/reporting/720db0c0-be65-40d9-ae9d-7627741385ce/page/p_si214uowdd",
            use_container_width=True,
        )
        st.markdown("---")

        nivel = st.session_state.auth_nivel
        if nivel:
            if nivel == "admin":
                if st.button("📦 Faturamento", key="nav_faturados", use_container_width=True):
                    safe_switch("pages/1_Produtos_Faturados.py")
            else:
                st.button(
                    "📦 Faturamento 🔒",
                    key="nav_faturados",
                    use_container_width=True,
                    disabled=True,
                )
            if st.button("🏭 Produção", key="nav_producao", use_container_width=True):
                safe_switch("pages/2_Producao_Geral.py")
            if st.button("✂️ Corte", key="nav_corte", use_container_width=True):
                safe_switch("pages/3_Controle_de_Corte.py")
        else:
            st.caption("🔒 Faça login para acessar os dashboards.")

        st.markdown("---")
        st.caption(
            f"⏱️ Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            "Use o menu lateral ou os cards abaixo para navegar."
        )
