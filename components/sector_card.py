# -*- coding: utf-8 -*-
"""Componente de renderização dos cards de setor."""

import streamlit as st
from utils.auth import verificar_acesso
from utils.navigation import safe_switch

_COLS_PER_ROW = 3


def render_sector_cards(sectors: list[dict], tab_prefix: str) -> None:
    """
    Renderiza uma grade de cards de setor dentro de uma aba.

    Args:
        sectors: Lista de dicts de setor (ver config/sectors.py).
        tab_prefix: Prefixo único para as chaves dos widgets Streamlit,
                    evitando colisões entre abas.
    """
    nivel_acesso: str = st.session_state.auth_nivel
    rows = [
        sectors[i : i + _COLS_PER_ROW]
        for i in range(0, len(sectors), _COLS_PER_ROW)
    ]

    for row_sectors in rows:
        padding = _COLS_PER_ROW - len(row_sectors)
        cols = st.columns(_COLS_PER_ROW, gap="medium")

        for col, sector in zip(cols, row_sectors):
            with col:
                _render_single_card(sector, tab_prefix, nivel_acesso)

        for i in range(padding):
            with cols[len(row_sectors) + i]:
                st.empty()


def _render_single_card(sector: dict, tab_prefix: str, nivel_acesso: str) -> None:
    locked = sector["key"] == "faturados" and nivel_acesso not in ("", "admin")
    coming_soon = sector.get("coming_soon", False)

    tags_html = "".join(
        f'<span class="sector-tag">{tag}</span>' for tag in sector["tags"]
    )

    if locked:
        badge_html = (
            '<div style="position:absolute;top:10px;right:12px;'
            'background:rgba(231,111,81,0.18);border:1px solid rgba(231,111,81,0.45);'
            'border-radius:6px;padding:2px 8px;font-size:.63rem;'
            'color:#E76F51;font-weight:700;letter-spacing:.04em">🔒 ADMIN</div>'
        )
    elif coming_soon:
        badge_html = (
            '<div style="position:absolute;top:10px;right:12px;'
            'background:rgba(161,139,250,0.15);border:1px solid rgba(161,139,250,0.40);'
            'border-radius:6px;padding:2px 8px;font-size:.63rem;'
            'color:#A78BFA;font-weight:700;letter-spacing:.04em">🚧 EM BREVE</div>'
        )
    else:
        badge_html = ""

    dim = "opacity:.50;pointer-events:none;" if (locked or coming_soon) else ""
    card_style = (
        f"--card-a:{sector['color_a']};--card-b:{sector['color_b']};"
        f"--card-accent:{sector['accent']};" + dim
    )

    st.markdown(
        f'<div class="sector-card" style="{card_style}">'
        f"{badge_html}"
        f'<div class="sector-card-inner">'
        f'<div class="sector-icon-wrap">{sector["icon"]}</div>'
        f'<div class="sector-card-body">'
        f'<div class="sector-subtitle">{sector["subtitle"]}</div>'
        f'<h3 class="sector-title">{sector["title"]}</h3>'
        f'<p class="sector-desc">{sector["description"]}</p>'
        f'<div class="sector-tags">{tags_html}</div>'
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    key = f"{tab_prefix}_{sector['key']}"
    _render_card_button(sector, key, nivel_acesso, locked, coming_soon)


def _render_card_button(
    sector: dict,
    key: str,
    nivel_acesso: str,
    locked: bool,
    coming_soon: bool,
) -> None:
    if coming_soon:
        st.button("🚧 Em breve", key=f"open_{key}", use_container_width=True, disabled=True)

    elif locked:
        st.button(
            "🔒 Acesso restrito — Admin",
            key=f"open_{key}",
            use_container_width=True,
            disabled=True,
        )

    elif nivel_acesso:
        if "external_url" in sector:
            st.link_button(
                f"Abrir {sector['title']}  →",
                sector["external_url"],
                use_container_width=True,
            )
        else:
            if st.button(
                f"Abrir {sector['title']}  →",
                key=f"open_{key}",
                use_container_width=True,
            ):
                safe_switch(sector["page_path"])

    elif st.session_state.auth_target == key:
        _render_inline_auth(sector, key)

    else:
        if st.button(
            f"🔒 Abrir {sector['title']}  →",
            key=f"open_{key}",
            use_container_width=True,
        ):
            st.session_state.auth_target = key
            st.rerun()


def _render_inline_auth(sector: dict, key: str) -> None:
    senha_input = st.text_input(
        "Senha",
        type="password",
        key=f"senha_{key}",
        placeholder="Digite a senha...",
        label_visibility="collapsed",
    )
    col_ok, col_x = st.columns([4, 1])
    with col_ok:
        if st.button("Entrar  →", key=f"ok_{key}", use_container_width=True):
            if not senha_input:
                st.warning("⚠️ Digite a senha.")
            else:
                nivel = verificar_acesso(senha_input)
                if nivel == "negado":
                    st.error("❌ Senha incorreta.")
                elif sector["key"] == "faturados" and nivel != "admin":
                    st.error("🔒 Faturamento requer senha Admin.")
                else:
                    st.session_state.auth_nivel = nivel
                    st.session_state.auth_target = None
                    if "page_path" in sector:
                        safe_switch(sector["page_path"])
                    else:
                        st.rerun()
    with col_x:
        if st.button("✕", key=f"cancel_{key}", use_container_width=True):
            st.session_state.auth_target = None
            st.rerun()
