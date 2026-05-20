# -*- coding: utf-8 -*-
"""Utilitários de navegação entre páginas Streamlit."""

import streamlit as st


def safe_switch(page_path: str) -> None:
    """Navega para uma página exibindo mensagem amigável em caso de falha."""
    try:
        st.switch_page(page_path)
    except Exception as e:  # noqa: BLE001
        st.error(
            f"Não foi possível abrir `{page_path}`.\n\n"
            "**Solução:** pare o Streamlit no terminal (Ctrl+C) e rode "
            "`streamlit run app.py` de novo. O Streamlit cacheia a lista "
            "de páginas no startup; renomear arquivos exige reinício."
        )
        with st.expander("Detalhes técnicos"):
            st.code(str(e))
