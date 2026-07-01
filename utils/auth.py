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

def init_session_state() -> None:
    """Inicializa as chaves de autenticação no session_state."""
    if "auth_nivel" not in st.session_state:
        st.session_state.auth_nivel = ""


def set_auth_session(nivel: str) -> None:
    """Marca a sessão como autenticada no nível informado."""
    st.session_state.auth_nivel = nivel


def clear_auth_session() -> None:
    """Remove a autenticação da sessão atual."""
    st.session_state.auth_nivel = ""
