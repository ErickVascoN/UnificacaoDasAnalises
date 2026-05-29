"""
CSS dos cards de seletor (estilo "escolha o tipo de análise"), compartilhado.

Mesmo visual usado em pages/3_Controle_de_Corte.py (telas de seleção com
.region-card / .rc-* / .page-header / .breadcrumb). Centralizado aqui para
reuso no hub de Produção (pages/2_Producao_Geral.py).
"""

from __future__ import annotations


def get_selector_cards_css() -> str:
    """Retorna o bloco <style> com as classes dos cards de seletor e breadcrumb."""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ---- PAGE HEADER ---- */
.page-header { text-align: center; padding: 30px 12px 8px 12px; }
.page-badge {
    display: inline-block; padding: 6px 18px; border-radius: 999px;
    font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase;
    color: #4ECDC4; background: rgba(78,205,196,0.10);
    border: 1px solid rgba(78,205,196,0.30); font-weight: 600; margin-bottom: 20px;
}
.page-title {
    font-family: 'Sora', sans-serif; font-size: 2.7rem; font-weight: 800;
    line-height: 1.05; margin: 0 0 14px 0; color: #FFFFFF; letter-spacing: -0.5px;
}
.page-title .accent {
    background: linear-gradient(90deg, #4ECDC4, #7CDDD6 45%, #45B7D1 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.page-subtitle {
    font-size: 1.05rem; color: #A0A0A0; max-width: 580px;
    margin: 0 auto 10px auto; line-height: 1.55;
}
.page-divider {
    height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.10), transparent);
    margin: 28px 0 36px 0;
}

/* ---- REGION / PRODUCT CARDS ---- */
.region-card {
    position: relative; border-radius: 20px; padding: 32px 26px 26px 26px;
    background: linear-gradient(160deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.10); overflow: hidden; text-align: center;
    min-height: 320px; transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    margin-bottom: 4px;
}
.region-card::before {
    content: ""; position: absolute; inset: 0;
    background: linear-gradient(160deg, var(--rc-a) 0%, var(--rc-b) 100%);
    opacity: 0.16; transition: opacity 0.25s ease; pointer-events: none;
}
.region-card:hover {
    transform: translateY(-5px); border-color: var(--rc-accent, rgba(78,205,196,0.55));
    box-shadow: 0 18px 44px rgba(0,0,0,0.55), 0 0 0 1px var(--rc-accent, rgba(78,205,196,0.4));
}
.region-card:hover::before { opacity: 0.28; }
.region-card.disabled { opacity: 0.55; }
.region-card.disabled:hover {
    transform: none !important; border-color: rgba(255,255,255,0.10) !important; box-shadow: none !important;
}
.rc-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 72px; height: 72px; border-radius: 18px;
    background: linear-gradient(135deg, var(--rc-a), var(--rc-b));
    font-size: 2.2rem; box-shadow: 0 8px 24px rgba(0,0,0,0.40); margin: 0 auto 20px auto;
}
.rc-label {
    font-size: 0.76rem; color: var(--rc-accent, #4ECDC4); font-weight: 600;
    letter-spacing: 0.10em; text-transform: uppercase; margin-bottom: 8px;
}
.rc-title { font-family: 'Sora', sans-serif; font-size: 1.65rem; font-weight: 800; color: #FFFFFF; margin: 0 0 12px 0; }
.rc-desc { color: #C0C0C0; font-size: 0.93rem; line-height: 1.57; margin-bottom: 18px; }
.rc-tags { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.rc-tag {
    font-size: 0.72rem; padding: 4px 11px; border-radius: 999px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.13); color: #A0A0A0;
}
.rc-tag-soon {
    font-size: 0.72rem; padding: 4px 11px; border-radius: 999px;
    background: rgba(255,167,38,0.10); border: 1px solid rgba(255,167,38,0.32); color: #FFA726;
}

/* ---- BREADCRUMB ---- */
.breadcrumb { font-size: 0.85rem; color: #606878; margin-bottom: 6px; padding: 0 2px; }
.breadcrumb .bc-sep { margin: 0 6px; color: rgba(255,255,255,0.18); }
.breadcrumb .bc-active { color: #4ECDC4; font-weight: 600; }
.breadcrumb .bc-link { color: #7A8899; }
</style>
"""
