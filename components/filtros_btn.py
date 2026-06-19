"""Botão flutuante 'Filtros' que abre a sidebar ao ser clicado."""

import streamlit.components.v1 as components

_HTML = """
<button onclick="
    var doc = window.parent.document;
    var selectors = [
        '[data-testid=stSidebarCollapsedControl] button',
        '[data-testid=stSidebarCollapsedControl]',
        'button[data-testid=stBaseButton-headerNoPadding]',
        '[data-testid=collapsedControl] button'
    ];
    var clicked = false;
    for (var i = 0; i < selectors.length; i++) {
        var el = doc.querySelector(selectors[i]);
        if (el) { el.click(); clicked = true; break; }
    }
    if (!clicked) {
        var btns = doc.querySelectorAll('button');
        for (var j = 0; j < btns.length; j++) {
            var b = btns[j];
            var r = b.getBoundingClientRect();
            if (r.left < 60 && r.top < 60 && r.width < 60 && b.querySelector('svg')) {
                b.click(); break;
            }
        }
    }
" style="
    width:100%;cursor:pointer;text-align:center;
    background:linear-gradient(135deg,#1A1F2E,#252B3B);
    border:1px solid #2D3748;border-radius:10px;
    color:#E2E8F0;padding:8px 16px;
    font-size:0.9rem;font-family:sans-serif;transition:all 0.3s ease;
" onmouseover="this.style.borderColor='#4ECDC4';this.style.color='#4ECDC4';"
   onmouseout="this.style.borderColor='#2D3748';this.style.color='#E2E8F0';">
    Filtros
</button>
"""


def render_filtros_btn(col_width: int = 1, total_cols: int = 6) -> None:
    """
    Renderiza o botão 'Filtros' em uma coluna estreita à esquerda.
    Ao clicar, abre a sidebar (mesmo que esteja recolhida).

    col_width / total_cols define a largura relativa do botão.
    """
    import streamlit as st
    col_btn, *_ = st.columns([col_width] + [total_cols - col_width])
    with col_btn:
        components.html(_HTML, height=45)
