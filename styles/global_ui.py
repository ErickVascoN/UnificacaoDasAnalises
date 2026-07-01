"""Estilos globais compartilhados entre todas as páginas do app."""


def get_global_ui_css() -> str:
    """Retorna CSS para esconder a navegação nativa do Streamlit e o rodapé padrão."""
    return """
    <style>
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid="stSidebarNav"] { display: none !important; }
    </style>
    """
