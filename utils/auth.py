# -*- coding: utf-8 -*-
"""Autenticação e controle de acesso."""

import streamlit as st
from config.settings import SENHA_USUARIO, SENHA_ADMIN


def verificar_acesso(senha: str) -> str:
    """Retorna 'admin', 'usuario' ou 'negado'."""
    if senha == SENHA_ADMIN:
        return "admin"
    if senha == SENHA_USUARIO:
        return "usuario"
    return "negado"


def pode_acessar(card_key: str, nivel_acesso: str) -> bool:
    """Verifica se o nível de acesso permite abrir um card específico."""
    if nivel_acesso == "admin":
        return True
    if nivel_acesso == "usuario":
        return card_key != "faturados"
    return False


def init_session_state() -> None:
    """Inicializa as chaves de autenticação no session_state."""
    if "auth_nivel" not in st.session_state:
        st.session_state.auth_nivel = ""
    if "auth_target" not in st.session_state:
        st.session_state.auth_target = None
