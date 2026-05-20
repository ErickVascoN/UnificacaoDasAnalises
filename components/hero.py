# -*- coding: utf-8 -*-
"""Componente hero da página inicial."""

import streamlit as st


def render_hero() -> None:
    """Renderiza o bloco hero com título, subtítulo e pills de destaque."""
    st.markdown(
        """
        <div class="hero">
            <div class="hero-badge">Grupo Zanattex</div>
            <h1 class="hero-title">Central de Dados <span class="accent"> Zanattex</span></h1>
            <p class="hero-subtitle">
                Visão unificada da operação do Grupo em um único lugar. Explore painéis de análise de dados
                e ferramentas de controladoria para produção, faturamento e gestão integrada.
            </p>
            <div class="hero-meta">
                <span class="hero-pill"><b>5</b> &nbsp;Painéis integrados</span>
                <span class="hero-pill"><b>Real-time</b> &nbsp;Atualização contínua</span>
                <span class="hero-pill"><b>Multi-empresa</b> &nbsp;Grupo consolidado</span>
            </div>
        </div>
        <div class="divider"></div>
        """,
        unsafe_allow_html=True,
    )
