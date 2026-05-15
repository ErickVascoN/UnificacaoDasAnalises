"""
Estilos e temas do Dashboard
"""
import streamlit as st


def apply_custom_css():
    """Aplica CSS customizado para melhorar a aparência"""
    st.markdown("""
    <style>
    /* Botões da sidebar e geral */
    .stButton > button {
        background-color: #0066cc;
        color: white !important;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #0052a3;
    }
    </style>
    """, unsafe_allow_html=True)


def create_sector_card(icon: str, title: str, description: str, selected: bool = False) -> str:
    """
    Cria um card visual para um setor.
    
    Args:
        icon: Emoji ou ícone
        title: Título do setor
        description: Descrição breve
        selected: Se está selecionado
        
    Returns:
        HTML do card
    """
    border_color = "#0066cc" if selected else "#e5e7eb"
    bg_color = "#f0f7ff" if selected else "#ffffff"
    
    return f"""
    <div style="
        background-color: {bg_color};
        border: 2px solid {border_color};
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: {'0 4px 12px rgba(0,102,204,0.2)' if selected else '0 1px 3px rgba(0,0,0,0.06)'};
    ">
        <div style="font-size: 48px; margin-bottom: 10px;">{icon}</div>
        <h3 style="color: #0066cc; margin: 10px 0; font-size: 18px;">{title}</h3>
        <p style="color: #666; font-size: 14px; margin: 0;">{description}</p>
    </div>
    """


def display_metric(label: str, value, suffix: str = "", delta=None):
    """
    Exibe uma métrica formatada profissionalmente.
    
    Args:
        label: Rótulo da métrica
        value: Valor a exibir
        suffix: Sufixo (%, R$, etc)
        delta: Valor de variação (opcional)
    """
    col = st.columns([1, 1])[0]
    with col:
        st.metric(
            label=label,
            value=f"{value}{suffix}",
            delta=delta,
            border=True
        )


def create_loading_spinner(text: str = "Carregando dados..."):
    """Exibe um spinner de carregamento estilizado"""
    with st.spinner(f"⏳ {text}"):
        return True
