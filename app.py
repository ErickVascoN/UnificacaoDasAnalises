"""
Dashboard Unificado — Página Inicial
Centraliza o acesso aos dashboards setoriais em uma única interface.
"""

import os
import sys

import streamlit as st

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config.settings import PAGE_CONFIG
from config.changelog import CHANGELOG
from styles.global_ui import get_global_ui_css
from styles.home import get_home_css
from utils.auth import init_session_state, verificar_acesso, set_auth_session, clear_auth_session
from components.sidebar import render_sidebar
from components.hero import render_hero
from components.sector_tabs import render_sector_tabs

# setup
st.set_page_config(**PAGE_CONFIG)
st.markdown(get_home_css(), unsafe_allow_html=True)
st.markdown(get_global_ui_css(), unsafe_allow_html=True)
init_session_state()
st.session_state._active_page = 'home'

_TAG_STYLE = {
    "novo":     ("🟢", "#22C55E", "rgba(34,197,94,.12)"),
    "melhoria": ("🔵", "#6366F1", "rgba(99,102,241,.12)"),
    "correção": ("🟡", "#F59E0B", "rgba(245,158,11,.12)"),
}

@st.dialog("📋 Novidades & Atualizações", width="large")
def _modal_changelog():
    st.markdown(
        "<p style='color:#94A3B8;font-size:.9rem;margin-bottom:16px;'>"
        "Últimas adições e melhorias na plataforma.</p>",
        unsafe_allow_html=True,
    )
    for entry in CHANGELOG:
        _, color, bg = _TAG_STYLE.get(entry["tag"], ("⚪", "#94A3B8", "rgba(148,163,184,.1)"))
        st.markdown(
            f"""
            <div style="background:{bg};border-left:3px solid {color};
                        border-radius:8px;padding:12px 16px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                    <span style="background:{color};color:#000;font-size:.65rem;font-weight:700;
                                 padding:2px 8px;border-radius:20px;text-transform:uppercase;">
                        {entry['tag']}
                    </span>
                    <span style="color:#64748B;font-size:.8rem;">{entry['date']}</span>
                </div>
                <div style="font-weight:700;color:#E2E8F0;margin-bottom:4px;">{entry['title']}</div>
                <div style="color:#94A3B8;font-size:.85rem;line-height:1.5;">{entry['description']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

def _apply_login_overlay_style() -> None:
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] { visibility: hidden; }
            section.main > div.block-container {
                filter: blur(6px) brightness(0.72);
                pointer-events: none;
                user-select: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("🔐 Acesso Unificado", width="large")
def _render_login_dialog() -> None:
    st.markdown(
        """
        <div style="margin-bottom:10px;">
            <div style="color:#4ECDC4;font-size:.72rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;margin-bottom:10px;">
                Acesso Unificado
            </div>
            <div style="font-family:'Sora',sans-serif;font-size:1.8rem;line-height:1.05;font-weight:800;color:#E2E8F0;margin-bottom:10px;">
                Faça o Login para Acessar a Central
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=True):
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        nivel = verificar_acesso(senha)
        if nivel == "negado":
            st.error("Senha incorreta.")
        else:
            set_auth_session(nivel)
            st.rerun()

    st.markdown(
        """
        <div style="margin-top:6px;color:#94A3B8;font-size:.84rem;line-height:1.45;">
            • Usuário: libera todos os cards comuns.<br>
            • Admin: libera tudo, inclusive os módulos administrativos.<br>
            • Ao atualizar a página, o login volta a ser solicitado.
        </div>
        """,
        unsafe_allow_html=True,
    )


# página
if not st.session_state.auth_nivel:
    _apply_login_overlay_style()

if st.session_state.auth_nivel:
    with st.sidebar:
        if st.button("🚪 Fazer Logout", use_container_width=True):
            clear_auth_session()
            st.rerun()

render_sidebar()
render_hero()

if st.session_state.auth_nivel:
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    c_left, c_center, c_right = st.columns([2.2, 1, 2.2])
    with c_center:
        if st.button("📋 Ver Novidades", use_container_width=True, type="secondary"):
            _modal_changelog()

st.markdown(
    """
    <div style="
        background: rgba(245,158,11,0.08);
        border: 1px solid rgba(245,158,11,0.30);
        border-left: 4px solid #F59E0B;
        border-radius: 10px;
        padding: 12px 18px;
        margin: 0 0 16px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    ">
        <span style="font-size:1.2rem;">🚧</span>
        <span style="color:#FCD34D; font-size:0.88rem; line-height:1.5;">
            <b>Plataforma em fase de melhorias contínuas.</b>
            Os dashboards estão sendo aprimorados constantemente — novos dados,
            correções e funcionalidades são adicionados com frequência.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

render_sector_tabs()

if not st.session_state.auth_nivel:
    _render_login_dialog()

# rodapé
st.markdown("---")
st.markdown(
    """
    <div class="footer-note">
        <b>Análise de Dados & Programação</b> ·
        Zanattex - Industria e Comercio de Confeccoes Ltda
    </div>
    """,
    unsafe_allow_html=True,
)
