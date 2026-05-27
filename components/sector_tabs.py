"""Componente de abas de setores (Análise de Dados / Controladoria)."""

import streamlit as st
from config.sectors import SECTORS_ANALISE, SECTORS_CONTROLADORIA
from components.sector_card import render_sector_cards

def render_sector_tabs() -> None:
    """Renderiza o cabeçalho 'Setores Disponíveis' e as duas abas de cards."""
    st.markdown(
        """
        <div style="text-align: center; margin-top: 32px; margin-bottom: 8px;">
            <h2 style="font-family: 'Sora', sans-serif; font-size: 1.45rem; font-weight: 700;
                       color: var(--text-strong); margin: 0 0 8px 0;">
                Setores Disponíveis
            </h2>
            <p style="color: var(--text-muted); margin: 0 0 24px 0; font-size: 0.98rem;">
                Clique em um cartão para abrir o dashboard do setor
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_analise, tab_controladoria = st.tabs(["📊 Análise de Dados", "💼 Controladoria"])

    with tab_analise:
        render_sector_cards(SECTORS_ANALISE, "analise")

    with tab_controladoria:
        if SECTORS_CONTROLADORIA:
            render_sector_cards(SECTORS_CONTROLADORIA, "controladoria")
        else:
            st.markdown(
                """
                <div style="text-align:center; padding: 48px 0 40px 0;">
                    <div style="font-size: 3rem; margin-bottom: 16px;">💼</div>
                    <p style="font-family:'Sora',sans-serif; font-size:1.2rem; font-weight:700;
                               color:var(--text-strong); margin-bottom: 8px;">
                        Controladoria
                    </p>
                    <p style="color:var(--text-muted); font-size:0.92rem; max-width:420px; margin: 0 auto;">
                        Os painéis de Controladoria estão sendo preparados.<br>
                        Em breve estarão disponíveis aqui.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
