# -*- coding: utf-8 -*-
"""CSS completo da página inicial (home/app.py)."""

from .theme import PALETTE


def get_home_css() -> str:
    """Retorna o bloco <style> completo para injeção via st.markdown."""
    p = PALETTE
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        :root {{
            --bg-deep: {p['bg_deep']};
            --bg-card: {p['bg_card']};
            --bg-card-2: {p['bg_card_2']};
            --teal: {p['teal']};
            --navy: {p['navy']};
            --coral: {p['coral']};
            --gold: {p['gold']};
            --text-strong: {p['text_strong']};
            --text-default: {p['text_default']};
            --text-muted: {p['text_muted']};
            --border: {p['border']};
            --border-hover: {p['border_hover']};
        }}

        footer {{ visibility: hidden; }}
        #MainMenu {{ visibility: hidden; }}
        [data-testid="stSidebarNav"] {{ display: none !important; }}

        .stApp {{
            background:
                radial-gradient(circle at 12% 10%, rgba(78,205,196,0.10) 0%, rgba(78,205,196,0) 38%),
                radial-gradient(circle at 88% 14%, rgba(231,111,81,0.10) 0%, rgba(231,111,81,0) 40%),
                radial-gradient(circle at 50% 110%, rgba(69,183,209,0.08) 0%, rgba(69,183,209,0) 45%),
                linear-gradient(180deg, #0B0E14 0%, #0E1117 55%, #11151F 100%);
            color: var(--text-default);
            font-family: 'Space Grotesk', sans-serif;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0C0F16 0%, #141925 100%) !important;
            border-right: 1px solid var(--border);
        }}
        section[data-testid="stSidebar"] * {{
            color: var(--text-default) !important;
            font-family: 'Space Grotesk', sans-serif;
        }}

        /* ── Hero ── */
        .hero {{
            text-align: center;
            padding: 28px 12px 8px 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
        }}
        .hero-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 999px;
            font-size: 0.72rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--teal);
            background: rgba(78,205,196,0.10);
            border: 1px solid rgba(78,205,196,0.30);
            font-weight: 600;
            margin-bottom: 18px;
        }}
        .hero-title {{
            font-family: 'Sora', sans-serif;
            font-size: 3.0rem;
            font-weight: 800;
            line-height: 1.05;
            margin: 0;
            color: var(--text-strong);
            letter-spacing: -0.5px;
        }}
        .hero-title .accent {{
            background: linear-gradient(90deg, var(--teal), #7CDDD6 45%, var(--coral) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .hero-subtitle {{
            font-size: 1.10rem;
            color: var(--text-muted);
            max-width: 760px;
            margin: 14px auto 6px auto;
            line-height: 1.5;
            text-align: center;
            width: 100%;
        }}
        .hero-meta {{
            display: inline-flex;
            gap: 14px;
            justify-content: center;
            margin: 18px 0 8px 0;
            flex-wrap: wrap;
        }}
        .hero-pill {{
            font-size: 0.78rem;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: rgba(255,255,255,0.03);
            color: var(--text-muted);
        }}
        .hero-pill b {{ color: var(--text-strong); font-weight: 600; }}

        .divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border), transparent);
            margin: 22px 0 8px 0;
        }}

        .section-label {{
            font-family: 'Sora', sans-serif;
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--text-strong);
            margin: 14px 0 4px 0;
            text-align: center;
        }}
        .section-helper {{
            color: var(--text-muted);
            margin-bottom: 18px;
            text-align: center;
        }}

        /* ── Layout de colunas ── */
        [data-testid="stHorizontalBlock"] {{ align-items: stretch !important; }}
        [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {{
            height: 100%;
            display: flex;
            flex-direction: column;
        }}
        [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stMarkdownContainer"] {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stMarkdownContainer"] > div {{
            height: 100%;
        }}

        /* ── Cards de setor ── */
        .sector-card {{
            position: relative;
            border-radius: 14px;
            padding: 14px 16px 12px 16px;
            background: linear-gradient(160deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%);
            border: 1px solid var(--border);
            overflow: hidden;
            height: 280px;
            box-sizing: border-box;
            transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
        }}
        .sector-card::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(160deg, var(--card-a) 0%, var(--card-b) 100%);
            opacity: 0.16;
            transition: opacity 0.22s ease;
            pointer-events: none;
        }}
        .sector-card:hover {{
            transform: translateY(-3px);
            border-color: var(--card-accent, var(--border-hover));
            box-shadow: 0 10px 24px rgba(0,0,0,0.40),
                        0 0 0 1px var(--card-accent, var(--border-hover));
        }}
        .sector-card:hover::before {{ opacity: 0.28; }}

        .sector-card-inner {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            height: 100%;
        }}
        .sector-icon-wrap {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            width: 42px;
            height: 42px;
            border-radius: 11px;
            background: linear-gradient(135deg, var(--card-a), var(--card-b));
            font-size: 1.25rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.30);
            margin-top: 2px;
        }}
        .sector-card-body {{ flex: 1; min-width: 0; }}
        .sector-title {{
            font-family: 'Sora', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-strong);
            margin: 0 0 1px 0;
            line-height: 1.2;
        }}
        .sector-subtitle {{
            font-size: 0.70rem;
            color: var(--card-accent);
            margin: 0 0 6px 0;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .sector-desc {{
            color: var(--text-muted);
            font-size: 0.80rem;
            line-height: 1.45;
            margin-bottom: 8px;
        }}
        .sector-tags {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 0; }}
        .sector-note {{
            margin-top: 8px;
            padding: 4px 10px;
            border-radius: 6px;
            background: rgba(251,191,36,0.10);
            border: 1px solid rgba(251,191,36,0.35);
            color: #FBBF24;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }}
        .sector-tag {{
            font-size: 0.65rem;
            padding: 2px 8px;
            border-radius: 999px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: var(--text-muted);
            letter-spacing: 0.02em;
        }}

        /* ── Botões de navegação (cards e conteúdo principal) ── */
        .stButton > button {{
            background: linear-gradient(135deg, var(--teal), #2BB3AB) !important;
            color: #0B0E14 !important;
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            border-radius: 10px !important;
            padding: 7px 12px !important;
            border: 1px solid rgba(78,205,196,0.55) !important;
            box-shadow: 0 4px 14px rgba(78,205,196,0.22) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease !important;
            width: 100% !important;
            margin-top: 6px !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(78,205,196,0.40) !important;
            filter: brightness(1.05);
        }}
        .stButton > button:active,
        .stButton > button:focus {{
            background: linear-gradient(135deg, var(--teal), #2BB3AB) !important;
            color: #0B0E14 !important;
            outline: none !important;
        }}
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {{ color: #0B0E14 !important; font-weight: 700 !important; }}

        /* ── Botões da sidebar (estilo mais sutil) ── */
        section[data-testid="stSidebar"] .stButton > button {{
            background: linear-gradient(135deg, rgba(78,205,196,0.18), rgba(78,205,196,0.08)) !important;
            color: var(--teal) !important;
            border: 1px solid rgba(78,205,196,0.35) !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: linear-gradient(135deg, rgba(78,205,196,0.30), rgba(78,205,196,0.14)) !important;
            border-color: var(--teal) !important;
            color: #FFFFFF !important;
            transform: translateY(-1px);
        }}
        section[data-testid="stSidebar"] .stButton > button p,
        section[data-testid="stSidebar"] .stButton > button span {{
            color: inherit !important;
            font-weight: 600 !important;
        }}

        /* ── Botão "Em breve" (disabled) ── */
        .stButton > button:disabled {{
            background: rgba(161,139,250,0.10) !important;
            color: #A78BFA !important;
            border: 1px solid rgba(161,139,250,0.30) !important;
            box-shadow: none !important;
            opacity: 1 !important;
            cursor: default !important;
        }}
        .stButton > button:disabled p,
        .stButton > button:disabled span,
        .stButton > button:disabled div {{ color: #A78BFA !important; font-weight: 600 !important; }}

        /* ── KPIs ── */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0,1fr));
            gap: 14px;
            margin: 8px 0 6px 0;
        }}
        @media (max-width: 900px) {{
            .kpi-row {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
        }}
        .kpi {{
            padding: 14px 16px;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: linear-gradient(140deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
        }}
        .kpi-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-muted);
            font-weight: 600;
        }}
        .kpi-value {{
            font-family: 'Sora', sans-serif;
            font-size: 1.55rem;
            font-weight: 700;
            color: var(--text-strong);
            margin-top: 6px;
        }}
        .kpi-accent {{ color: var(--teal); }}

        /* ── Abas (Análise de Dados / Controladoria) ── */
        [data-testid="stTabs"] {{ margin-top: 8px; }}
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            padding: 5px 6px !important;
            gap: 6px !important;
            display: flex !important;
            width: fit-content !important;
            margin: 0 auto 24px auto !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            font-family: 'Sora', sans-serif !important;
            font-size: 0.93rem !important;
            font-weight: 600 !important;
            padding: 9px 28px !important;
            border-radius: 10px !important;
            border: 1px solid transparent !important;
            color: var(--text-muted) !important;
            background: transparent !important;
            transition: all 0.22s ease !important;
            letter-spacing: 0.02em !important;
            white-space: nowrap !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
            color: var(--text-strong) !important;
            background: rgba(255,255,255,0.06) !important;
            border-color: var(--border) !important;
        }}
        [data-testid="stTabs"] [aria-selected="true"] {{
            background: linear-gradient(135deg, var(--teal), #2BB3AB) !important;
            color: #0B0E14 !important;
            border-color: rgba(78,205,196,0.55) !important;
            box-shadow: 0 4px 18px rgba(78,205,196,0.35), 0 0 0 1px rgba(78,205,196,0.30) !important;
            font-weight: 700 !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab-highlight"],
        [data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none !important; }}

        /* ── Rodapé ── */
        .footer-note {{
            margin-top: 22px;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.82rem;
        }}
        .footer-note b {{ color: var(--text-default); font-weight: 600; }}
    </style>
    """
