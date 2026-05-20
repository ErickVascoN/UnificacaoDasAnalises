# -*- coding: utf-8 -*-
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
from styles.home import get_home_css
from utils.auth import init_session_state
from components.sidebar import render_sidebar
from components.hero import render_hero
from components.kpi_row import render_kpi_row
from components.sector_tabs import render_sector_tabs

# ── Setup ──────────────────────────────────────────────────────────────────────
st.set_page_config(**PAGE_CONFIG)
st.markdown(get_home_css(), unsafe_allow_html=True)
init_session_state()

# ── Página ─────────────────────────────────────────────────────────────────────
render_sidebar()
render_hero()
render_kpi_row()
render_sector_tabs()

# ── Rodapé ─────────────────────────────────────────────────────────────────────
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
