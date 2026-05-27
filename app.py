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
from styles.home import get_home_css
from utils.auth import init_session_state
from components.sidebar import render_sidebar
from components.hero import render_hero
from components.kpi_row import render_kpi_row
from components.sector_tabs import render_sector_tabs

# setup
st.set_page_config(**PAGE_CONFIG)
st.markdown(get_home_css(), unsafe_allow_html=True)
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

# página
render_sidebar()
render_hero()

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

_, col_btn, _ = st.columns([3, 1, 3])
with col_btn:
    if st.button("📋 Ver Novidades", use_container_width=True, type="secondary"):
        _modal_changelog()

render_kpi_row()
render_sector_tabs()

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
