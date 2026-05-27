"""Componente de linha de KPIs da página inicial."""

import streamlit as st

def render_kpi_row() -> None:
    """Renderiza os 4 cards de KPI no topo da seção de setores."""
    st.markdown(
        """
        <div class="kpi-row">
            <div class="kpi">
                <div class="kpi-label">Painéis</div>
                <div class="kpi-value"><span class="kpi-accent">5</span> ativos</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Empresas Monitoradas</div>
                <div class="kpi-value">7+</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Fonte de Dados</div>
                <div class="kpi-value">Google Sheets</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Cache</div>
                <div class="kpi-value">Automático</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
