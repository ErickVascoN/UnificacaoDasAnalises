from __future__ import annotations

import io
import os
import re
import time
import unicodedata
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg/edit?gid=1255712550#gid=1255712550"
CACHE_TTL_SECONDS = 300

COLORS = {
    "primary": "#0C6E74",
    "secondary": "#1D3557",
    "accent": "#E76F51",
    "gold": "#F4A261",
    "mint": "#2A9D8F",
    "ink": "#0B132B",
    "muted": "#5C677D",
    "bg_light": "#F3F6F9",
}


st.set_page_config(
    page_title="Dashboard de Produtos Faturados",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Sora:wght@500;600;700&display=swap');

            :root {
                --primary: #0C6E74;
                --secondary: #1D3557;
                --accent: #E76F51;
                --gold: #F4A261;
                --ink: #0B132B;
                --muted: #5C677D;
                --card: rgba(255, 255, 255, 0.82);
            }

            .stApp {
                background:
                    radial-gradient(circle at 8% 12%, rgba(231, 111, 81, 0.16) 0%, rgba(231, 111, 81, 0) 40%),
                    radial-gradient(circle at 86% 6%, rgba(12, 110, 116, 0.16) 0%, rgba(12, 110, 116, 0) 38%),
                    linear-gradient(180deg, #f9fcff 0%, #edf3f8 100%);
                color: var(--ink);
                font-family: 'Space Grotesk', sans-serif;
            }

            .stApp p,
            .stApp li,
            .stApp span,
            .stApp label,
            .stApp div {
                color: #1e2b47;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #f5f8fc 0%, #eef2f9 100%);
                border-right: 1px solid rgba(29, 53, 87, 0.12);
            }

            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
            [data-testid="stSidebar"] .stCaption {
                color: #1d3557 !important;
                font-family: 'Space Grotesk', sans-serif;
            }

            [data-testid="stSidebar"] [data-baseweb="input"] > div,
            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] [data-baseweb="textarea"] > div {
                background: rgba(255, 255, 255, 0.98) !important;
                border: 1.5px solid rgba(29, 53, 87, 0.2) !important;
            }

            [data-testid="stSidebar"] input,
            [data-testid="stSidebar"] textarea,
            [data-testid="stSidebar"] [data-baseweb="select"] input {
                color: #1d3557 !important;
                -webkit-text-fill-color: #1d3557 !important;
                font-weight: 500;
            }

            [data-testid="stSidebar"] input::placeholder,
            [data-testid="stSidebar"] textarea::placeholder {
                color: #7a8ca8 !important;
                opacity: 1;
            }

            [data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {
                background-color: #e76f51 !important;
            }

            [data-testid="stSidebar"] [data-baseweb="slider"] > div > div {
                background: rgba(29, 53, 87, 0.15) !important;
            }

            [data-baseweb="tab-list"] {
                gap: 0.45rem;
                margin-bottom: 0.7rem;
            }

            [data-baseweb="tab-list"] button {
                color: #1d3557 !important;
                font-weight: 700;
                background: rgba(255, 255, 255, 0.8);
                border-radius: 10px 10px 0 0;
                padding: 0.4rem 0.7rem;
            }

            [data-baseweb="tab-list"] button[aria-selected="true"] {
                color: #ffffff !important;
                background: #0c6e74;
                border-bottom: 2px solid #0c6e74;
            }

            /* Multiselect badges/tags */
            [data-baseweb="tag"] {
                background-color: #0c6e74 !important;
            }

            [data-baseweb="tag"] > span {
                color: #ffffff !important;
            }

            [data-baseweb="tag"] [data-testid="stTagCloseButton"] {
                color: rgba(255, 255, 255, 0.7) !important;
            }

            [data-baseweb="tab-panel"] {
                background: rgba(255, 255, 255, 0.52);
                border: 1px solid rgba(17, 32, 63, 0.08);
                border-radius: 0 12px 12px 12px;
                padding: 0.6rem 0.8rem 0.9rem 0.8rem;
            }

            h1, h2, h3 {
                font-family: 'Fraunces', serif !important;
                color: #11203f;
                letter-spacing: 0.2px;
            }

            [data-testid="stWidgetLabel"] p,
            [data-testid="stMetricLabel"] p,
            .stCaption,
            small {
                color: #3c4d70 !important;
            }

            [data-testid="stMetricValue"] {
                font-family: 'Sora', 'Space Grotesk', sans-serif !important;
                font-weight: 600 !important;
                color: #132445 !important;
                font-variant-numeric: tabular-nums;
            }

            [data-testid="stMarkdownContainer"] p strong {
                color: #12213e;
            }

            .hero {
                background: linear-gradient(120deg, rgba(12,110,116,0.95), rgba(29,53,87,0.95));
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 22px;
                padding: 1.3rem 1.5rem;
                margin-bottom: 1.2rem;
                box-shadow: 0 12px 30px rgba(16, 24, 40, 0.18);
            }

            .hero h2 {
                margin: 0;
                color: #ffffff;
                font-size: 1.9rem;
            }

            .hero p {
                margin: 0.35rem 0 0 0;
                color: rgba(255, 255, 255, 0.9);
                font-size: 1rem;
            }

            .kpi-card {
                border-radius: 18px;
                padding: 1rem 1.05rem;
                background: var(--card);
                border: 1px solid rgba(17, 32, 63, 0.08);
                box-shadow: 0 6px 18px rgba(17, 32, 63, 0.08);
                backdrop-filter: blur(2px);
                min-height: 130px;
            }

            .kpi-label {
                font-size: 0.82rem;
                font-weight: 700;
                color: var(--muted);
                text-transform: uppercase;
                letter-spacing: 0.7px;
                margin-bottom: 0.45rem;
            }

            .kpi-value {
                font-family: 'Sora', 'Space Grotesk', sans-serif;
                font-weight: 600;
                color: var(--ink);
                font-size: 1.72rem;
                line-height: 1.08;
                font-variant-numeric: tabular-nums;
                letter-spacing: 0.08px;
            }

            .kpi-sub {
                color: #42506b;
                font-size: 0.83rem;
                margin-top: 0.35rem;
            }

            .kpi-delta-up {
                margin-top: 0.45rem;
                color: #1c8c63;
                font-size: 0.8rem;
                font-weight: 600;
            }

            .kpi-delta-down {
                margin-top: 0.45rem;
                color: #c44536;
                font-size: 0.8rem;
                font-weight: 600;
            }

            .insight-box {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(17, 32, 63, 0.08);
                border-left: 6px solid #E76F51;
                border-radius: 16px;
                padding: 1rem 1.1rem;
                margin-top: 0.6rem;
                box-shadow: 0 4px 14px rgba(17, 32, 63, 0.06);
            }

            .insight-box p {
                margin: 0.2rem 0;
                color: #1f2d4a;
                font-size: 0.93rem;
            }

            .story-row {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(17, 32, 63, 0.08);
                border-radius: 16px;
                padding: 0.9rem 1rem;
                box-shadow: 0 4px 14px rgba(17, 32, 63, 0.06);
                margin-top: 0.6rem;
                margin-bottom: 0.8rem;
            }

            .story-row p {
                margin: 0.22rem 0;
                color: #1f2d4a;
                font-size: 0.92rem;
            }

            .chart-help {
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(17, 32, 63, 0.08);
                border-left: 5px solid #0C6E74;
                border-radius: 12px;
                padding: 0.62rem 0.8rem;
                margin-top: 0.35rem;
                margin-bottom: 0.95rem;
            }

            .chart-help p {
                margin: 0.08rem 0;
                color: #223456;
                font-size: 0.84rem;
            }

            .alert-card {
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                margin-bottom: 0.55rem;
                border: 1px solid rgba(17, 32, 63, 0.1);
                background: rgba(255,255,255,0.85);
            }

            .alert-title {
                font-weight: 700;
                font-size: 0.88rem;
                margin-bottom: 0.2rem;
            }

            .alert-text {
                font-size: 0.84rem;
                color: #2b395a;
                margin: 0.08rem 0;
            }

            .risk-high {
                border-left: 6px solid #d62828;
            }

            .risk-mid {
                border-left: 6px solid #f4a261;
            }

            .risk-low {
                border-left: 6px solid #2a9d8f;
            }

            .foot-note {
                margin-top: 1rem;
                font-size: 0.8rem;
                color: #556078;
            }

            @media (max-width: 900px) {
                .hero h2 {
                    font-size: 1.45rem;
                }
                .kpi-value {
                    font-size: 1.42rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_text(value: str) -> str:
    # Converter para string e remover NaN/None
    value = str(value).strip() if pd.notna(value) else ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "_", ascii_text)
    ascii_text = re.sub(r"_+", "_", ascii_text).strip("_")
    return ascii_text


def to_brl(value: float) -> str:
    """Formata valor em R$ com separadores de milhar (formato brasileiro)."""
    if pd.isna(value):
        return "R$ 0,00"
    # Format: 1234567.89 -> 1.234.567,89
    formatted = f"{value:,.2f}"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def to_int(value: float) -> str:
    """Formata inteiro com separadores de milhar (formato brasileiro: 1.234.567)."""
    if pd.isna(value):
        return "0"
    # Format: 1234567 -> 1.234.567
    return f"{int(round(value)):,}".replace(",", ".")


def format_number_br(value: float, decimals: int = 0) -> str:
    """Formata número genérico com separadores de milhar (formato brasileiro)."""
    if pd.isna(value):
        return "0"
    if decimals == 0:
        return f"{int(round(value)):,}".replace(",", ".")
    else:
        formatted = f"{value:,.{decimals}f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def safe_to_float(value) -> float | None:
    """Converte valor para float com segurança, retorna None para valores inválidos."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip().upper()
        if value in ["NI", "N/A", "", "-", "NULL"]:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    return None


def to_pct(value: float) -> str:
    """Formata percentual (formato brasileiro)."""
    if pd.isna(value):
        return "0,0%"
    return f"{value * 100:.1f}%".replace(".", ",")


def to_date_br_short(value: pd.Timestamp | str) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%d/%m/%y")


def build_export_url(sheet_url: str) -> str:
    parsed = urlparse(sheet_url)
    if "export?format=csv" in sheet_url:
        return sheet_url

    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError("Link inválido: não foi possível identificar o ID da planilha.")

    sheet_id = match.group(1)
    query_params = parse_qs(parsed.query)
    gid_from_query = query_params.get("gid", [None])[0]

    gid = gid_from_query
    if gid is None and parsed.fragment:
        fragment_match = re.search(r"gid=([0-9]+)", parsed.fragment)
        gid = fragment_match.group(1) if fragment_match else None

    if gid is None:
        gid = "0"

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def parse_br_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_best_date(series: pd.Series) -> pd.Series:
    first = pd.to_datetime(series, errors="coerce", dayfirst=False)
    second = pd.to_datetime(series, errors="coerce", dayfirst=True)
    if first.notna().sum() >= second.notna().sum():
        return first
    return second


def is_dimension(word: str) -> bool:
    """Verifica se uma palavra é uma dimensão (ex: 1.40X2.00, 0.47X0.65)."""
    word = str(word).strip().upper()
    # Dimensões têm X e contêm números
    return "X" in word and any(c.isdigit() for c in word)


def is_valid_color_word(word: str) -> bool:
    """Verifica se uma palavra é válida como cor (não é código/número)."""
    if not word or len(word) <= 2:
        return False
    
    word_upper = word.upper()
    
    # Pula abreviações comuns que não são cores
    skip_words = {"SORT", "EST", "SHU", "LS", "MCF", "EL", "CL", "CS", "DIV", "ES", "GSM", "REAP", "PET", "DEC"}
    if word_upper in skip_words:
        return False
    
    # Pula palavras que são principalmente números/hífens (como "18-0", "17-0610")
    digit_count = sum(1 for c in word if c.isdigit() or c == "-")
    if digit_count > len(word) * 0.5:  # Se mais de 50% é número/hífen
        return False
    
    # Deve ter pelo menos 3 caracteres e ser principalmente letras
    letter_count = sum(1 for c in word if c.isalpha())
    if letter_count < len(word) * 0.6:  # Menos de 60% de letras é suspeito
        return False
    
    return True


def categorize_size(product_name: str) -> str:
    """Extrai tamanho/dimensão do nome do produto."""
    if not product_name:
        return "Indefinido"
    
    name = str(product_name).strip()
    
    # Procura por dimensões explícitas (1.40X2.00, 0.47X0.65, etc)
    palavras = name.split()
    for palavra in palavras:
        palavra_limpa = palavra.rstrip(".,;-")
        if is_dimension(palavra_limpa):
            return palavra_limpa
    
    # Se não encontrar dimensão, procura por palavras-chave de tamanho
    name_upper = normalize_text(name).upper()
    
    if "queen" in name_upper:
        return "Queen"
    elif "casal" in name_upper:
        return "Casal"
    elif "solteiro" in name_upper or "solt" in name_upper:
        return "Solteiro"
    else:
        return "Indefinido"


def categorize_color(product_name: str) -> str:
    """Extrai a cor, pulando dimensões e códigos no final do nome."""
    if not product_name:
        return "Indefinido"
    
    # Remove espaços extras e pega palavras em ordem reversa (do final para o início)
    palavras = str(product_name).strip().split()
    
    # Procura de trás para frente, pulando dimensões e palavras inválidas
    for i in range(len(palavras) - 1, -1, -1):
        palavra = palavras[i].strip().rstrip(".,;-")
        
        # Pula palavras vazias ou dimensões
        if not palavra or is_dimension(palavra):
            continue
        
        # Verifica se é uma palavra válida como cor
        if is_valid_color_word(palavra):
            return palavra
    
    return "Indefinido"


def categorize_product(product_name: str) -> str:
    """Agrupa produtos baseado em palavras-chave no nome."""
    if not product_name:
        return "Outros"
    
    name = normalize_text(str(product_name).strip()).upper()
    
    # Mapeamento de palavras-chave → categoria
    mapping = {
        "Cobertores": ["COBERTOR"],
        "Colchas": ["COLCHA"],
        "Cortinas": ["CORTINA"],
        "Fronhas": ["FRONHA"],
        "Jogos de Cama": ["JOGO", "JG "],
        "Kits": ["KIT"],
        "Mantas": ["MANTA"],
        "Edredons": ["EDREDON"],
        "Almofadas": ["ALMOFADA"],
        "Lençóis": ["LENCO"],  # Adicionar lençóis também
    }
    
    for categoria, keywords in mapping.items():
        for keyword in keywords:
            if keyword in name:
                return categoria
    
    return "Outros"


def canonical_column_names(columns: list[str]) -> dict[str, str]:
    renamed: dict[str, str] = {}
    for original in columns:
        # Converter para string (caso seja NaN/float)
        original_str = str(original).strip() if pd.notna(original) else ""
        key = normalize_text(original_str)

        if "data" in key and "emiss" in key:
            renamed[original] = "data_emissao"
        elif "nota" == key or key.startswith("nota"):
            renamed[original] = "nota"
        elif "pedido" in key:
            renamed[original] = "pedido"
        elif "cfop" in key:
            renamed[original] = "cfop"
        elif "destinat" in key:
            renamed[original] = "destinatario"
        elif "municip" in key:
            renamed[original] = "municipio"
        elif "frete" in key:
            renamed[original] = "frete"
        elif "quant" in key:
            renamed[original] = "quantidade"
        elif "valor" in key and "unit" in key:
            renamed[original] = "valor_unit"
        elif "valor" in key and "total" in key:
            renamed[original] = "valor_total"
        elif key == "st":
            renamed[original] = "st"
        elif "cod" in key and "prod" in key:
            renamed[original] = "cod_prod"
        elif "venc" in key and "fatura" in key:
            renamed[original] = "venc_fatura"
        elif "descricao" in key and "produto" in key:
            renamed[original] = "descricao_produto"
        elif "situ" in key:
            renamed[original] = "situacao"
        else:
            renamed[original] = key
    return renamed


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_data(sheet_url: str) -> pd.DataFrame:
    """Carrega dados com retry exponencial e fallback local (TIER 3 Melhoria)."""
    export_url = build_export_url(sheet_url)
    
    # Retry com backoff exponencial (TIER 3 FIX)
    max_retries = 3
    base_delay = 2  # segundos
    for attempt in range(max_retries):
        try:
            response = requests.get(export_url, timeout=45)
            response.raise_for_status()
            csv_text = response.content.decode("utf-8-sig", errors="ignore")
            break  # Sucesso, sai do loop
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 2, 4, 8 segundos
                st.warning(f"Tentativa {attempt + 1} falhou. Retentando em {delay}s... ({str(e)[:50]})")
                import time
                time.sleep(delay)
            else:
                # Fallback: tenta carregar arquivo local se existir
                fallback_file = "cache_data.csv"
                if os.path.exists(fallback_file):
                    st.warning(f"Falha permanente. Carregando dados em cache (mais recente).")
                    with open(fallback_file, "r", encoding="utf-8-sig") as f:
                        csv_text = f.read()
                else:
                    raise ValueError("Não foi possível carregar do Google Sheets e sem cache local disponível.")
    
    df = pd.read_csv(io.StringIO(csv_text), dtype=str)
    df = df.rename(columns=canonical_column_names(list(df.columns)))
    
    # Criar colunas dinamicamente baseado no nome do produto
    df["grupo_produto"] = df["descricao_produto"].apply(categorize_product)
    df["tamanho"] = df["descricao_produto"].apply(categorize_size)
    df["cor"] = df["descricao_produto"].apply(categorize_color)

    required_cols = [
        "data_emissao",
        "pedido",
        "destinatario",
        "municipio",
        "frete",
        "quantidade",
        "valor_unit",
        "valor_total",
        "cod_prod",
        "descricao_produto",
        "situacao",
        "nota",
        "cfop",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("\u00a0", " ", regex=False)
                .str.strip()
                .replace({"": np.nan, "nan": np.nan, "None": np.nan})
            )

    df["data_emissao"] = parse_best_date(df["data_emissao"])
    df["quantidade"] = parse_br_number(df["quantidade"]).fillna(0)
    df["valor_unit"] = parse_br_number(df["valor_unit"]).fillna(0)
    df["valor_total"] = parse_br_number(df["valor_total"]).fillna(0)
    df = df.drop(columns=["vendedor"], errors="ignore")

    df = df[df["data_emissao"].notna()].copy()
    df["pedido"] = df["pedido"].astype(str)

    df["ano"] = df["data_emissao"].dt.year
    df["mes"] = df["data_emissao"].dt.month
    df["ano_mes"] = df["data_emissao"].dt.to_period("M").dt.to_timestamp()
    df["dia_semana"] = df["data_emissao"].dt.day_name()

    cidade_estado = df["municipio"].fillna("-").str.rsplit("-", n=1, expand=True)
    if cidade_estado.shape[1] == 2:
        df["cidade"] = cidade_estado[0].str.strip()
        df["estado"] = cidade_estado[1].str.strip().str.upper()
    else:
        df["cidade"] = df["municipio"].fillna("-")
        df["estado"] = "NA"

    df["ticket_item"] = np.where(df["quantidade"] > 0, df["valor_total"] / df["quantidade"], 0)

    return df


def kpi_card(title: str, value: str, subtext: str, delta: float | None = None) -> str:
    delta_html = ""
    if delta is not None and np.isfinite(delta):
        delta_class = "kpi-delta-up" if delta >= 0 else "kpi-delta-down"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="{delta_class}">{arrow} {to_pct(abs(delta))} vs período anterior</div>'

    return f"""
        <div class="kpi-card">
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{subtext}</div>
            {delta_html}
        </div>
    """


def compare_previous_period(df_all: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp, metric_col: str) -> float | None:
    """Compara período atual com período anterior de mesma duração."""
    if metric_col not in df_all.columns:
        return None

    days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=max(days - 1, 1))

    current_mask = (df_all["data_emissao"] >= start_date) & (df_all["data_emissao"] <= end_date)
    prev_mask = (df_all["data_emissao"] >= prev_start) & (df_all["data_emissao"] <= prev_end)

    current_value = df_all.loc[current_mask, metric_col].sum()
    prev_value = df_all.loc[prev_mask, metric_col].sum()

    if prev_value <= 0:
        return None

    return (current_value - prev_value) / prev_value


def compare_with_baseline(df_all: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp, metric_col: str, baseline_type: str) -> float | None:
    """Compara período atual com múltiplas baselines: anterior, ano passado, ou média 3M (TIER 1 FIX)."""
    if metric_col not in df_all.columns or df_all.empty:
        return None

    current_mask = (df_all["data_emissao"] >= start_date) & (df_all["data_emissao"] <= end_date)
    current_value = df_all.loc[current_mask, metric_col].sum()

    if baseline_type == "período_anterior":
        return compare_previous_period(df_all, start_date, end_date, metric_col)
    
    elif baseline_type == "ano_passado":
        prev_year_start = start_date - pd.DateOffset(years=1)
        prev_year_end = end_date - pd.DateOffset(years=1)
        prev_mask = (df_all["data_emissao"] >= prev_year_start) & (df_all["data_emissao"] <= prev_year_end)
        prev_value = df_all.loc[prev_mask, metric_col].sum()
        if prev_value <= 0:
            return None
        return (current_value - prev_value) / prev_value
    
    elif baseline_type == "media_3m":
        months_back = 3
        three_months_ago = start_date - pd.DateOffset(months=months_back)
        prev_mask = (df_all["data_emissao"] >= three_months_ago) & (df_all["data_emissao"] < start_date)
        prev_value = df_all.loc[prev_mask, metric_col].sum() / months_back if not df_all.loc[prev_mask].empty else 0
        if prev_value <= 0:
            return None
        return (current_value - prev_value) / prev_value
    
    return None


def monthly_view(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("ano_mes", as_index=False)
        .agg(
            faturamento=("valor_total", "sum"),
            quantidade=("quantidade", "sum"),
            pedidos=("pedido", "nunique"),
        )
        .sort_values("ano_mes")
    )


def build_alerts(
    df: pd.DataFrame,
    cliente_limit: float,
) -> list[dict[str, str]]:
    if df.empty:
        return []

    alerts: list[dict[str, str]] = []
    receita_total = df["valor_total"].sum()

    if receita_total <= 0:
        return []

    cliente_agg = (
        df.groupby("destinatario", as_index=False)["valor_total"]
        .sum()
        .sort_values("valor_total", ascending=False)
    )
    if not cliente_agg.empty:
        share_cliente = cliente_agg.iloc[0]["valor_total"] / receita_total
        if share_cliente >= cliente_limit:
            alerts.append(
                {
                    "severity": "high",
                    "title": "Risco de concentração em cliente",
                    "detail": f"{cliente_agg.iloc[0]['destinatario']} representa {to_pct(share_cliente)} da receita.",
                    "action": "Ação sugerida: acelerar expansão em 2 a 3 contas de médio porte para reduzir dependência.",
                }
            )

    mensal = monthly_view(df)
    if len(mensal) >= 4:
        ult = mensal.iloc[-1]["faturamento"]
        media_3 = mensal.iloc[-4:-1]["faturamento"].mean()
        if media_3 > 0:
            delta = (ult - media_3) / media_3
            if delta <= -0.2:
                alerts.append(
                    {
                        "severity": "high",
                        "title": "Queda relevante no mês mais recente",
                        "detail": f"O último mês ficou {to_pct(abs(delta))} abaixo da média dos 3 meses anteriores.",
                        "action": "Ação sugerida: revisar rupturas, preço e mix de produtos de maior giro.",
                    }
                )

    ticket_item = np.where(df["quantidade"] > 0, df["valor_total"] / df["quantidade"], np.nan)
    # Proteção contra divisão por zero e valores inválidos (TIER 1 FIX)
    mean_val = np.nanmean(ticket_item)
    std_val = np.nanstd(ticket_item)
    if pd.notna(mean_val) and mean_val > 0 and pd.notna(std_val) and std_val > 0:
        coef_var = std_val / mean_val
        if coef_var > 1.2:
            alerts.append(
                {
                    "severity": "mid",
                    "title": "Alta dispersão de preço médio por item",
                    "detail": f"Existe grande variação de preço unitário entre vendas (CV: {coef_var:.2f}x).",
                    "action": "Ação sugerida: revisar política de preço e descontos por canal/cliente.",
                }
            )

    if not alerts:
        alerts.append(
            {
                "severity": "low",
                "title": "Operação estável no recorte",
                "detail": "Sem alertas críticos detectados com as regras atuais.",
                "action": "Ação sugerida: manter monitoramento semanal dos principais drivers.",
            }
        )

    return alerts[:4]


def build_forecast(mensal: pd.DataFrame, periods: int = 4) -> pd.DataFrame:
    """Constrói previsão com detecção de sazonalidade (TIER 2 Melhoria)."""
    if len(mensal) < 4:
        return pd.DataFrame()

    x = np.arange(len(mensal), dtype=float)
    y = mensal["faturamento"].to_numpy(dtype=float)

    # Detecção básica de sazonalidade: se houver pelo menos 12 meses, busca padrão
    has_seasonality = False
    seasonal_factor = 1.0
    if len(mensal) >= 12:
        # Compara pares de meses: mês N vs mês N-12
        last_year = mensal.tail(12)["faturamento"].mean()
        two_years_ago = mensal.iloc[-24:-12]["faturamento"].mean() if len(mensal) >= 24 else last_year
        if two_years_ago > 0:
            seasonal_factor = last_year / two_years_ago
            # Se a relação entre anos está entre 0.8 e 1.2, considera estável (sem sazonalidade forte)
            has_seasonality = seasonal_factor < 0.85 or seasonal_factor > 1.15

    # Regressão linear como baseline
    slope, intercept = np.polyfit(x, y, 1)
    trend = slope * x + intercept
    residuals = y - trend
    sigma = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0

    # Previsão com aplicação de fator sazonal se detectado
    future_x = np.arange(len(mensal), len(mensal) + periods, dtype=float)
    future_y = slope * future_x + intercept
    if has_seasonality:
        # Aplica fator sazonal progressivamente (suavizado)
        for i, fy in enumerate(future_y):
            seasonal_adjustment = seasonal_factor ** (i / periods)  # Suavização gradual
            future_y[i] = fy * seasonal_adjustment

    future_dates = [mensal["ano_mes"].max() + pd.offsets.MonthBegin(i + 1) for i in range(periods)]

    z_score = 1.28  # ~80% de confiança
    lower = np.maximum(0, future_y - z_score * sigma)
    upper = np.maximum(0, future_y + z_score * sigma)

    forecast = pd.DataFrame(
        {
            "ano_mes": future_dates,
            "faturamento_previsto": np.maximum(0, future_y),
            "faixa_inferior": lower,
            "faixa_superior": upper,
        }
    )
    return forecast


def render_alerts(alerts: list[dict[str, str]]) -> None:
    level_map = {"high": "risk-high", "mid": "risk-mid", "low": "risk-low"}
    for item in alerts:
        level_class = level_map.get(item["severity"], "risk-low")
        st.markdown(
            (
                f'<div class="alert-card {level_class}">'
                f'<div class="alert-title">{item["title"]}</div>'
                f'<div class="alert-text">{item["detail"]}</div>'
                f'<div class="alert-text">{item["action"]}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render_chart_help(purpose: str, insight: str) -> None:
    st.markdown(
        (
            '<div class="chart-help">'
            f"<p><strong>Para que serve:</strong> {purpose}</p>"
            f"<p><strong>Insight:</strong> {insight}</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_kpi_section(df_f: pd.DataFrame, receita_total: float, quantidade_total: float, pedidos_unicos: int, 
                       ticket_medio_pedido: float, preco_medio_ponderado: float, clientes_ativos: int, 
                       produtos_ativos: int, delta_receita: float | None, delta_volume: float | None) -> None:
    """Renderiza seção de KPIs principais (TIER 2 Refactor)."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(kpi_card("Peças Faturadas", to_brl(receita_total), "Receita no período", delta_receita), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Volume", to_int(quantidade_total), "Unidades faturadas", delta_volume), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Pedidos", to_int(pedidos_unicos), "Pedidos únicos"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Ticket por Pedido", to_brl(ticket_medio_pedido), "Média por pedido"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("Preço Médio", to_brl(preco_medio_ponderado), "Valor por unidade"), unsafe_allow_html=True)
    with c6:
        st.markdown(kpi_card("Clientes Ativos", to_int(clientes_ativos), f"{to_int(produtos_ativos)} produtos ativos"), unsafe_allow_html=True)


def render_narrative_section(mensal_last: float, media_3m: float, top_cliente_name: str, top_cliente_share: float,
                             top_prod_name: str, gap_meta: float, meta_mensal: float) -> None:
    """Renderiza narrativa executiva de 60 segundos (TIER 2 Refactor)."""
    insights = generate_insights_from_metrics(mensal_last, media_3m, top_cliente_share, gap_meta, meta_mensal)
    st.markdown('<div class="insight-box">' + "".join([f"<p>• {i}</p>" for i in insights]) + "</div>", unsafe_allow_html=True)

    st.subheader("Resumo Executivo")
    st.markdown(
        (
            '<div class="story-row">'
            f"<p><strong>Onde estamos:</strong> peças faturadas recentes de {to_brl(mensal_last)} versus média móvel trimestral de {to_brl(media_3m)}.</p>"
            f"<p><strong>O que move o resultado:</strong> principal cliente é {top_cliente_name} com {to_pct(top_cliente_share)} da receita; produto líder: {top_prod_name}.</p>"
            f"<p><strong>O que fazer agora:</strong> {'acelerar receita para fechar meta mensal' if gap_meta < 0 else 'sustentar ritmo e proteger margem'} ({to_brl(abs(gap_meta))} {'abaixo' if gap_meta < 0 else 'acima'} da meta).</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def generate_insights_from_metrics(mensal_last: float, media_3m: float, top_cliente_share: float, 
                                   gap_meta: float, meta_mensal: float) -> list[str]:
    """Gera insights automaticamente baseado em métricas principais (TIER 2 Refactor)."""
    insights = []
    
    if mensal_last > media_3m * 1.1:
        insights.append(f"Crescimento forte: faturamento {to_pct((mensal_last / media_3m - 1))} acima da média trimestral.")
    elif mensal_last < media_3m * 0.9:
        insights.append(f"Queda preocupante: {to_pct((1 - mensal_last / media_3m))} abaixo da média dos últimos 3 meses.")
    
    if top_cliente_share > 0.4:
        insights.append(f"Concentração elevada: maior cliente representa {to_pct(top_cliente_share)} (risco maior que 30%).")
    
    if gap_meta < 0:
        insights.append(f"Meta em risco: faltam {to_brl(abs(gap_meta))} para atingir o objetivo mensal.")
    elif gap_meta > meta_mensal * 0.2:
        insights.append(f"Desempenho acima da expectativa: {to_pct(gap_meta / meta_mensal)} acima da meta.")
    
    if not insights:
        insights.append("Operação dentro do normal. Acompanhe métricas semanalmente.")
    
    return insights[:4]  # Limita a 4 insights


def generate_insights(df: pd.DataFrame) -> list[str]:
    insights: list[str] = []

    if df.empty:
        return ["Sem dados após os filtros aplicados."]

    receita_total = df["valor_total"].sum()

    cliente_agg = df.groupby("destinatario", as_index=False)["valor_total"].sum().sort_values("valor_total", ascending=False)
    if not cliente_agg.empty and receita_total > 0:
        top_cliente = cliente_agg.iloc[0]
        share_cliente = top_cliente["valor_total"] / receita_total
        insights.append(
            f"Cliente líder: {top_cliente['destinatario']} concentra {to_pct(share_cliente)} das peças faturadas no recorte."
        )

    produto_agg = df.groupby("descricao_produto", as_index=False)["valor_total"].sum().sort_values("valor_total", ascending=False)
    if not produto_agg.empty and receita_total > 0:
        top_prod = produto_agg.iloc[0]
        share_prod = top_prod["valor_total"] / receita_total
        insights.append(
            f"Produto de maior impacto: {top_prod['descricao_produto']} representa {to_pct(share_prod)} da receita atual."
        )

    mensal = df.groupby("ano_mes", as_index=False)["valor_total"].sum().sort_values("ano_mes")
    if len(mensal) >= 2 and mensal.iloc[-2]["valor_total"] > 0:
        last = mensal.iloc[-1]["valor_total"]
        previous = mensal.iloc[-2]["valor_total"]
        change = (last - previous) / previous
        direction = "crescimento" if change >= 0 else "queda"
        insights.append(f"Tendência recente: {direction} de {to_pct(abs(change))} no último mês fechado.")

    ticket_medio = np.where(df["quantidade"].sum() > 0, df["valor_total"].sum() / df["quantidade"].sum(), 0)
    insights.append(f"Preço médio ponderado no recorte: {to_brl(float(ticket_medio))} por unidade faturada.")

    return insights[:5]


def chart_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(template="plotly_white")
    fig.update_layout(
        plot_bgcolor="#f8fbff",
        paper_bgcolor="#f8fbff",
        margin=dict(l=10, r=10, t=40, b=20),
        legend_title_text="",
        font=dict(family="Space Grotesk, sans-serif", color="#1b2a47"),
        legend=dict(font=dict(color="#213352")),
    )
    fig.update_xaxes(
        showgrid=False,
        showline=True,
        linecolor="rgba(27,42,71,0.6)",
        tickfont=dict(color="#233453"),
        title_font=dict(color="#1b2a47"),
        tickformat="%d/%m/%y",
        hoverformat="%d/%m/%y",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(35,52,83,0.18)",
        zeroline=True,
        zerolinecolor="rgba(35,52,83,0.3)",
        tickfont=dict(color="#233453"),
        title_font=dict(color="#1b2a47"),
    )
    return fig


def get_dynamic_chart_height(data_points: int, base_height: int = 400) -> int:
    """Calcula altura dinâmica do gráfico baseado na quantidade de dados (TIER 2 Melhoria)."""
    if data_points <= 5:
        return base_height
    elif data_points <= 15:
        return int(base_height * 1.2)
    elif data_points <= 25:
        return int(base_height * 1.5)
    else:
        return int(base_height * (1 + min((data_points - 25) * 0.05, 2.0)))  # Cap em 3x


def render_presentation_mode(
    df_f: pd.DataFrame,
    mensal: pd.DataFrame,
    alerts: list[dict[str, str]],
    forecast_df: pd.DataFrame,
    meta_mensal: float,
    receita_total: float,
    quantidade_total: float,
    pedidos_unicos: int,
    ticket_medio_pedido: float,
    top_cliente_name: str,
    top_cliente_share: float,
    top_prod_name: str,
    mensal_last: float,
    media_3m: float,
    gap_meta: float,
) -> None:
    st.markdown("### Modo Apresentação")
    st.caption("Fluxo guiado para reunião executiva: avance pelas etapas e apresente com foco em decisão.")

    etapa = st.radio(
        "Etapa da apresentação",
        ["Panorama", "Riscos", "Oportunidades", "Plano"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if etapa == "Panorama":
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Peças Faturadas", to_brl(receita_total))
        k2.metric("Volume", to_int(quantidade_total))
        k3.metric("Pedidos", to_int(pedidos_unicos))
        k4.metric("Ticket", to_brl(ticket_medio_pedido))

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=mensal["ano_mes"],
                y=mensal["faturamento"],
                mode="lines+markers",
                name="Peças Faturadas",
                line=dict(color=COLORS["primary"], width=4),
            )
        )
        fig.add_trace(
            go.Bar(
                x=mensal["ano_mes"],
                y=mensal["quantidade"],
                name="Volume",
                marker_color="rgba(244,162,97,0.38)",
            )
        )
        fig.update_layout(title="Panorama Mensal de Receita e Volume")
        st.plotly_chart(chart_layout(fig), use_container_width=True)
        if len(mensal) >= 2 and mensal.iloc[-2]["faturamento"] > 0:
            delta_mes = (mensal.iloc[-1]["faturamento"] - mensal.iloc[-2]["faturamento"]) / mensal.iloc[-2]["faturamento"]
            insight_panorama = f"No mês mais recente, as peças faturadas {'subiram' if delta_mes >= 0 else 'caíram'} {to_pct(abs(delta_mes))} vs mês anterior."
        else:
            insight_panorama = f"No recorte atual, o total mais recente de peças faturadas é {to_brl(mensal_last)}."
        render_chart_help(
            "Comparar evolução mensal de receita e volume para identificar aceleração ou desaceleração do negócio.",
            insight_panorama,
        )

        st.markdown(
            (
                f"**Mensagem-chave:** no recorte atual, o último mês fechou em {to_brl(mensal_last)} "
                f"(média de 3 meses: {to_brl(media_3m)})."
            )
        )

    elif etapa == "Riscos":
        render_alerts(alerts)

        top_clientes = (
            df_f.groupby("destinatario", as_index=False)["valor_total"]
            .sum()
            .sort_values("valor_total", ascending=False)
            .head(8)
        )
        fig_risk = px.bar(
            top_clientes.sort_values("valor_total"),
            x="valor_total",
            y="destinatario",
            orientation="h",
            title="Concentração de Receita - Top 8 Clientes",
            color="valor_total",
            color_continuous_scale=["#FCE4D8", "#F4A261", "#E76F51"],
            labels={"valor_total": "Receita (R$)", "destinatario": "Cliente"},
        )
        st.plotly_chart(chart_layout(fig_risk), use_container_width=True)
        if not top_clientes.empty and top_clientes["valor_total"].sum() > 0:
            share_top3 = top_clientes["valor_total"].head(3).sum() / top_clientes["valor_total"].sum()
            insight_risco = f"Os 3 maiores clientes concentram {to_pct(share_top3)} do top 8 exibido."
        else:
            insight_risco = "Sem dados suficientes para inferir concentração no recorte."
        render_chart_help(
            "Mostrar risco de dependência comercial por carteira de clientes.",
            insight_risco,
        )

    elif etapa == "Oportunidades":
        c1, c2 = st.columns(2)

        produto_perf = (
            df_f.groupby("descricao_produto", as_index=False)["valor_total"]
            .sum()
            .sort_values("valor_total", ascending=False)
            .head(12)
        )
        estado_perf = (
            df_f.groupby("estado", as_index=False)["valor_total"]
            .sum()
            .sort_values("valor_total", ascending=False)
        )

        with c1:
            fig_prod = px.bar(
                produto_perf.sort_values("valor_total"),
                x="valor_total",
                y="descricao_produto",
                orientation="h",
                title="Top Produtos para Escalar Receita",
                color="valor_total",
                color_continuous_scale=["#D7EFEA", "#2A9D8F", "#1D3557"],
                labels={"valor_total": "Receita (R$)", "descricao_produto": "Produto"},
            )
            st.plotly_chart(chart_layout(fig_prod), use_container_width=True)
            if not produto_perf.empty and produto_perf["valor_total"].sum() > 0:
                share_top_prod = produto_perf.iloc[0]["valor_total"] / produto_perf["valor_total"].sum()
                insight_prod = f"O produto líder representa {to_pct(share_top_prod)} da receita dos 12 principais itens."
            else:
                insight_prod = "Sem dados suficientes para inferir concentração de produto."
            render_chart_help(
                "Destacar quais produtos puxam resultado e merecem prioridade comercial.",
                insight_prod,
            )

        with c2:
            fig_geo = px.bar(
                estado_perf,
                x="estado",
                y="valor_total",
                title="Estados com Maior Potencial de Crescimento",
                color="valor_total",
                color_continuous_scale=["#D6EAF8", "#0C6E74", "#1D3557"],
                labels={"valor_total": "Receita (R$)", "estado": "Estado"},
            )
            st.plotly_chart(chart_layout(fig_geo), use_container_width=True)
            if not estado_perf.empty and estado_perf["valor_total"].sum() > 0:
                share_estado = estado_perf.iloc[0]["valor_total"] / estado_perf["valor_total"].sum()
                insight_geo = f"O estado líder concentra {to_pct(share_estado)} da receita geográfica no período."
            else:
                insight_geo = "Sem dados suficientes para inferir concentração geográfica."
            render_chart_help(
                "Comparar tração comercial por estado para orientar expansão territorial.",
                insight_geo,
            )

        st.markdown(
            f"**Mensagem-chave:** maior alavanca atual está em {top_prod_name}, e o cliente líder é {top_cliente_name} ({to_pct(top_cliente_share)} da receita)."
        )

    else:
        left, right = st.columns([1, 2])

        with left:
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=float(mensal_last),
                    number={"prefix": "R$ "},
                    title={"text": "Meta Mensal"},
                    gauge={
                        "axis": {"range": [0, max(meta_mensal * 1.5, mensal_last * 1.2 + 1)]},
                        "bar": {"color": COLORS["primary"]},
                        "steps": [
                            {"range": [0, meta_mensal * 0.85], "color": "#ffd6cc"},
                            {"range": [meta_mensal * 0.85, meta_mensal], "color": "#ffe9bf"},
                            {"range": [meta_mensal, max(meta_mensal * 1.5, mensal_last * 1.2 + 1)], "color": "#d8f3dc"},
                        ],
                        "threshold": {
                            "line": {"color": COLORS["accent"], "width": 4},
                            "thickness": 0.75,
                            "value": meta_mensal,
                        },
                    },
                )
            )
            fig_gauge.update_layout(height=320)
            st.plotly_chart(chart_layout(fig_gauge), use_container_width=True)
            atingimento_meta = (mensal_last / meta_mensal) if meta_mensal > 0 else 0
            render_chart_help(
                "Mostrar o quanto o mês atual está distante da meta de peças faturadas.",
                f"Atingimento atual: {to_pct(atingimento_meta)} da meta mensal configurada.",
            )

        with right:
            if forecast_df.empty:
                st.info("Sem meses suficientes para previsão no recorte atual.")
            else:
                fig_forecast = go.Figure()
                fig_forecast.add_trace(
                    go.Scatter(
                        x=mensal["ano_mes"],
                        y=mensal["faturamento"],
                        mode="lines+markers",
                        name="Histórico",
                        line=dict(color=COLORS["secondary"], width=3),
                    )
                )
                fig_forecast.add_trace(
                    go.Scatter(
                        x=forecast_df["ano_mes"],
                        y=forecast_df["faturamento_previsto"],
                        mode="lines+markers",
                        name="Previsão",
                        line=dict(color=COLORS["primary"], width=3, dash="dot"),
                    )
                )
                fig_forecast.update_layout(title="Previsão de Receita - 4 Meses")
                st.plotly_chart(chart_layout(fig_forecast), use_container_width=True)
                meses_acima_meta = int((forecast_df["faturamento_previsto"] >= meta_mensal).sum())
                render_chart_help(
                    "Antecipar tendência de peças faturadas para planejar decisões comerciais com antecedência.",
                    f"Na previsão base, {meses_acima_meta} de {len(forecast_df)} meses ficam acima da meta atual.",
                )

        st.markdown("**Plano de ação recomendado:**")
        st.markdown("1. Defender as contas estratégicas e reduzir concentração com novas contas de médio porte.")
        st.markdown("2. Priorizar os produtos líderes com maior margem e maior giro.")
        st.markdown(
            f"3. {'Ativar plano comercial para recuperar' if gap_meta < 0 else 'Sustentar ritmo e elevar rentabilidade com mix premium'} {to_brl(abs(gap_meta))} {'abaixo' if gap_meta < 0 else 'acima'} da meta."
        )


def main() -> None:
    inject_styles()

    st.markdown(
        """
        <div class="hero">
            <h2>Análise de Produtos Faturados</h2>
            <p>Visão comercial e operacional em tempo real.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Configuração")
        
        # Help inicial (TIER 3 Onboarding)
        with st.expander("ℹ️ Como usar este dashboard", expanded=False):
            st.markdown("""
            **Visão Executiva**: Métricas principais e tendências.  
            **Comercial**: Análise por vendedor e clientes.  
            **Produtos**: Ranking e mix de receita.  
            **Geografia**: Estados e cidades com maior potencial.  
            **Previsão**: Cenários para os próximos 4 meses.
            
            💡 **Dicas**:
            - Altere a "Comparação" para ver deltas vs. ano passado ou média 3M
            - Use os alertas inteligentes para monitorar riscos
            - Em "Modo Apresentação", siga o guia de 4 etapas para reuniões
            """)
        
        sheet_url = st.text_input("Link da planilha Google Sheets", value=DEFAULT_SHEET_URL)
        refresh_click = st.button("Atualizar dados agora", use_container_width=True)
        modo_apresentacao = st.toggle("Modo Apresentação", value=False)
        st.caption("Atualização automática em cache a cada 5 minutos.")

    if refresh_click:
        st.cache_data.clear()

    try:
        df = load_data(sheet_url)
    except Exception as exc:
        st.error(f"Não foi possível carregar a planilha. Erro: {exc}")
        st.stop()

    if df.empty:
        st.warning("A planilha não retornou dados válidos no recorte atual.")
        st.stop()

    data_min = df["data_emissao"].min().date()
    data_max = df["data_emissao"].max().date()
    data_max_ano = date(data_max.year, 12, 31)

    # Calcular anos e meses disponíveis
    df["ano_filtro"] = df["data_emissao"].dt.year
    df["mes_filtro"] = df["data_emissao"].dt.month
    
    anos_disponiveis = sorted(df["ano_filtro"].unique().tolist())
    
    # Callbacks para cascata de filtros
    def _on_ano_change():
        """Reset dependências quando Ano muda"""
        for k in ("filtro_mes", "filtro_data_ini", "filtro_data_fim"):
            st.session_state.pop(k, None)
    
    def _on_mes_change():
        """Reset dependências quando Mês muda"""
        for k in ("filtro_data_ini", "filtro_data_fim"):
            st.session_state.pop(k, None)

    with st.sidebar:
        st.markdown("---")
        
        # Debug: Mostrar informações do dataset (agora após df ser carregado)
        with st.expander("🔧 Debug - Informações do Dataset"):
            debug_info = f"""
            **Tamanho do Dataset:**
            - Total de linhas: {len(df):,}
            - Colunas: {len(df.columns)}
            
            **Range de Datas:**
            - De: {df['data_emissao'].min()}
            - Até: {df['data_emissao'].max()}
            
            **Valores Únicos Principais:**
            - Anos: {df['ano_filtro'].nunique()}
            - Clientes: {df['destinatario'].nunique()}
            - Produtos: {df['descricao_produto'].nunique()}
            - Estados: {df['estado'].nunique()}
            """
            st.markdown(debug_info)
        
        st.markdown("---")
        st.subheader("Filtros de Data")
        
        # Filtro simplificado: anos + meses com range automático de datas
        anos_sel = st.multiselect(
            "Anos",
            options=anos_disponiveis,
            default=anos_disponiveis,
            key="filtro_ano",
            on_change=_on_ano_change,
        )
        if not anos_sel:
            anos_sel = anos_disponiveis
        
        # Filtro 2: Seleção de Meses (em cascata com Anos)
        meses_disponiveis = sorted(
            df[df["ano_filtro"].isin(anos_sel)]["mes_filtro"].unique().tolist()
        )
        
        MESES_NOMES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                       7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
        
        meses_sel = st.multiselect(
            "Meses",
            options=meses_disponiveis,
            default=meses_disponiveis,
            format_func=lambda m: MESES_NOMES.get(m, f"Mês {m}"),
            key="filtro_mes",
            on_change=_on_mes_change,
        )
        if not meses_sel:
            meses_sel = meses_disponiveis
        
        # Calcular range de datas baseado em Anos/Meses selecionados
        df_filt_temp = df[df["ano_filtro"].isin(anos_sel) & df["mes_filtro"].isin(meses_sel)]
        
        if not df_filt_temp.empty:
            d_min_filt = df_filt_temp["data_emissao"].min().date()
            d_max_filt = df_filt_temp["data_emissao"].max().date()
        else:
            d_min_filt = data_min
            d_max_filt = data_max
        
        # Seleção de Data Simplificada (Período)
        col_ini, col_fim = st.columns(2)
        with col_ini:
            data_inicial = st.date_input(
                "Início",
                value=st.session_state.get("filtro_data_ini", d_min_filt),
                min_value=d_min_filt,
                max_value=d_max_filt,
                format="DD/MM/YYYY",
                key="filtro_data_ini",
            )
        with col_fim:
            data_final = st.date_input(
                "Fim",
                value=st.session_state.get("filtro_data_fim", d_max_filt),
                min_value=d_min_filt,
                max_value=d_max_filt,
                format="DD/MM/YYYY",
                key="filtro_data_fim",
            )
        
        # Garantir que data_inicial <= data_final
        if data_inicial > data_final:
            data_inicial, data_final = data_final, data_inicial
        
        st.caption(f"📅 Range dinâmico: {d_min_filt.strftime('%d/%m/%Y')} até {d_max_filt.strftime('%d/%m/%Y')}")

        st.markdown("---")
        st.subheader("Comparação")
        tipo_comparacao = st.radio(
            "Comparar com:",
            ["Período Anterior", "Mesmo Período Ano Passado", "Média Móvel 3M"],
            horizontal=False,
            key="tipo_comparacao",
        )
        # Mapear para chaves do comparador
        map_comparacao = {
            "Período Anterior": "período_anterior",
            "Mesmo Período Ano Passado": "ano_passado",
            "Média Móvel 3M": "media_3m",
        }
        baseline_sel = map_comparacao.get(tipo_comparacao, "período_anterior")

        st.markdown("---")

        clientes = sorted(df["destinatario"].dropna().unique().tolist())
        estados = sorted(df["estado"].dropna().unique().tolist())
        produtos = sorted(df["descricao_produto"].dropna().unique().tolist())
        fretes = sorted(df["frete"].dropna().unique().tolist())
        grupos = sorted(df["grupo_produto"].dropna().unique().tolist())
        tamanhos = sorted(df["tamanho"].dropna().unique().tolist())
        cores = sorted(df["cor"].dropna().unique().tolist())

        cliente_sel = st.multiselect("Cliente", options=clientes)
        estado_sel = st.multiselect("Estado", options=estados)
        
        # Cascatear cidade de estado (Bug fix)
        if estado_sel:
            cidades = sorted(df[df["estado"].isin(estado_sel)]["cidade"].dropna().unique().tolist())
        else:
            cidades = sorted(df["cidade"].dropna().unique().tolist())
        
        cidade_sel = st.multiselect("Cidade", options=cidades)
        
        # Seleção de grupo (ANTES de produtos)
        grupo_sel = st.multiselect("Grupo de Produto", options=grupos)
        
        # Se grupos forem selecionados, filtrar produtos para mostrar apenas do grupo
        if grupo_sel:
            produtos_filtrados = sorted(
                df[df["grupo_produto"].isin(grupo_sel)]["descricao_produto"].dropna().unique().tolist()
            )
        else:
            produtos_filtrados = produtos
        
        # Filtro de produtos (agora dinâmico baseado na seleção de grupo)
        produto_sel = st.multiselect("Produto", options=produtos_filtrados)
        
        # Filtros de tamanho e cor dinâmicos baseados em produtos selecionados
        if produto_sel:
            # Se produtos foram selecionados, mostrar apenas tamanhos/cores daqueles produtos
            tamanhos_filtrados = sorted(
                df[df["descricao_produto"].isin(produto_sel)]["tamanho"].dropna().unique().tolist()
            )
            cores_filtradas = sorted(
                df[df["descricao_produto"].isin(produto_sel)]["cor"].dropna().unique().tolist()
            )
        elif grupo_sel:
            # Se só grupo foi selecionado (sem produtos), mostrar tamanhos/cores do grupo
            tamanhos_filtrados = sorted(
                df[df["grupo_produto"].isin(grupo_sel)]["tamanho"].dropna().unique().tolist()
            )
            cores_filtradas = sorted(
                df[df["grupo_produto"].isin(grupo_sel)]["cor"].dropna().unique().tolist()
            )
        else:
            # Se nada foi selecionado, mostrar tudo
            tamanhos_filtrados = tamanhos
            cores_filtradas = cores
        
        tamanho_sel = st.multiselect("Tamanho", options=tamanhos_filtrados)
        cor_sel = st.multiselect("Cor", options=cores_filtradas)
        frete_sel = st.multiselect("Frete", options=fretes)

        st.markdown("---")
        st.subheader("Metas e Alertas")
        
        meta_mensal = st.number_input(
            "Meta de peças faturadas mensal (R$)",
            min_value=0.0,
            value=300000.0,
            step=10000.0,
        )
        st.metric("Meta Mensal", to_brl(meta_mensal))
        
        limite_cliente = st.slider("Alerta concentração por cliente", min_value=20, max_value=90, value=45, step=1) / 100
        
        # Botão limpar filtros + indicador de filtros ativos
        st.markdown("---")
        col_clear, col_indicator = st.columns([1, 2])
        
        with col_clear:
            if st.button("🗑️ Limpar Filtros", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key.startswith("filtro_"):
                        st.session_state.pop(key, None)
                st.rerun()
        
        # Indicador de filtros ativos
        filtros_ativos = sum([
            len(cliente_sel) > 0,
            len(estado_sel) > 0,
            len(cidade_sel) > 0,
            len(grupo_sel) > 0,
            len(produto_sel) > 0,
            len(tamanho_sel) > 0,
            len(cor_sel) > 0,
            len(frete_sel) > 0,
            (data_inicial != d_min_filt or data_final != d_max_filt),
        ])
        
        with col_indicator:
            if filtros_ativos > 0:
                st.info(f"✓ {filtros_ativos} filtro(s) ativo(s)")

    start_date = pd.Timestamp(data_inicial)
    end_date = pd.Timestamp(data_final)

    if start_date > end_date:
        st.error("A data inicial não pode ser maior que a data final.")
        st.stop()

    # Filtro com todos os campos corretos (Bug fix: incluir ano/mês e cascatear corretamente)
    mask = (df["data_emissao"] >= start_date) & (df["data_emissao"] <= end_date)
    mask &= df["ano_filtro"].isin(anos_sel)
    mask &= df["mes_filtro"].isin(meses_sel)
    
    if cliente_sel:
        mask &= df["destinatario"].isin(cliente_sel)
    if estado_sel:
        mask &= df["estado"].isin(estado_sel)
    if cidade_sel:
        mask &= df["cidade"].isin(cidade_sel)
    if produto_sel:
        mask &= df["descricao_produto"].isin(produto_sel)
    if grupo_sel:
        mask &= df["grupo_produto"].isin(grupo_sel)
    if tamanho_sel:
        mask &= df["tamanho"].isin(tamanho_sel)
    if cor_sel:
        mask &= df["cor"].isin(cor_sel)
    if frete_sel:
        mask &= df["frete"].isin(frete_sel)

    df_f = df.loc[mask].copy()

    if df_f.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        st.stop()

    receita_total = df_f["valor_total"].sum()
    quantidade_total = df_f["quantidade"].sum()
    pedidos_unicos = df_f["pedido"].nunique()
    clientes_ativos = df_f["destinatario"].nunique()
    produtos_ativos = df_f["descricao_produto"].nunique()
    ticket_medio_pedido = receita_total / pedidos_unicos if pedidos_unicos > 0 else 0
    preco_medio_ponderado = receita_total / quantidade_total if quantidade_total > 0 else 0

    delta_receita = compare_with_baseline(df, start_date, end_date, "valor_total", baseline_sel)
    delta_volume = compare_with_baseline(df, start_date, end_date, "quantidade", baseline_sel)
    mensal = monthly_view(df_f)

    forecast_df = build_forecast(mensal, periods=4)
    alerts = build_alerts(df_f, cliente_limit=limite_cliente)

    top_cliente_row = (
        df_f.groupby("destinatario", as_index=False)["valor_total"]
        .sum()
        .sort_values("valor_total", ascending=False)
        .head(1)
    )
    top_prod_row = (
        df_f.groupby("descricao_produto", as_index=False)["valor_total"]
        .sum()
        .sort_values("valor_total", ascending=False)
        .head(1)
    )
    top_cliente_name = top_cliente_row.iloc[0]["destinatario"] if not top_cliente_row.empty else "-"
    top_cliente_share = (top_cliente_row.iloc[0]["valor_total"] / receita_total) if (not top_cliente_row.empty and receita_total > 0) else 0
    top_prod_name = top_prod_row.iloc[0]["descricao_produto"] if not top_prod_row.empty else "-"

    mensal_last = mensal.iloc[-1]["faturamento"] if not mensal.empty else 0
    media_3m = mensal.tail(3)["faturamento"].mean() if not mensal.empty else 0
    gap_meta = mensal_last - meta_mensal

    if modo_apresentacao:
        render_presentation_mode(
            df_f=df_f,
            mensal=mensal,
            alerts=alerts,
            forecast_df=forecast_df,
            meta_mensal=meta_mensal,
            receita_total=receita_total,
            quantidade_total=quantidade_total,
            pedidos_unicos=pedidos_unicos,
            ticket_medio_pedido=ticket_medio_pedido,
            top_cliente_name=top_cliente_name,
            top_cliente_share=top_cliente_share,
            top_prod_name=top_prod_name,
            mensal_last=mensal_last,
            media_3m=media_3m,
            gap_meta=gap_meta,
        )

        missing_nota = df["nota"].isna().mean() * 100
        missing_cfop = df["cfop"].isna().mean() * 100
        st.markdown(
            f'<div class="foot-note">Qualidade de dados: Nota com {missing_nota:.1f}% de ausência e CFOP com {missing_cfop:.1f}% de ausência.</div>',
            unsafe_allow_html=True,
        )
        return

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(kpi_card("Peças Faturadas", to_brl(receita_total), "Receita no período", delta_receita), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Volume", to_int(quantidade_total), "Unidades faturadas", delta_volume), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Pedidos", to_int(pedidos_unicos), "Pedidos únicos"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Ticket por Pedido", to_brl(ticket_medio_pedido), "Média por pedido"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("Preço Médio", to_brl(preco_medio_ponderado), "Valor por unidade"), unsafe_allow_html=True)
    with c6:
        st.markdown(kpi_card("Clientes Ativos", to_int(clientes_ativos), f"{to_int(produtos_ativos)} produtos ativos"), unsafe_allow_html=True)

    insights = generate_insights(df_f)
    st.markdown('<div class="insight-box">' + "".join([f"<p>• {i}</p>" for i in insights]) + "</div>", unsafe_allow_html=True)

    st.subheader("Resumo Executivo")
    st.markdown(
        (
            '<div class="story-row">'
            f"<p><strong>Onde estamos:</strong> peças faturadas recentes de {to_brl(mensal_last)} versus média móvel trimestral de {to_brl(media_3m)}.</p>"
            f"<p><strong>O que move o resultado:</strong> principal cliente é {top_cliente_name} com {to_pct(top_cliente_share)} da receita; produto líder: {top_prod_name}.</p>"
            f"<p><strong>O que fazer agora:</strong> {'acelerar receita para fechar meta mensal' if gap_meta < 0 else 'sustentar ritmo e proteger margem'} ({to_brl(abs(gap_meta))} {'abaixo' if gap_meta < 0 else 'acima'} da meta).</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.subheader("Alertas Inteligentes")
    render_alerts(alerts)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Visão Executiva", "Comercial", "Produtos", "Geografia e Detalhes", "Previsão e Metas"]
    )

    with tab1:
        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        fig_trend.add_trace(
            go.Bar(
                x=mensal["ano_mes"],
                y=mensal["quantidade"],
                name="Volume",
                marker_color="rgba(244,162,97,0.45)",
            ),
            secondary_y=False,
        )
        fig_trend.add_trace(
            go.Scatter(
                x=mensal["ano_mes"],
                y=mensal["faturamento"],
                name="Peças Faturadas",
                mode="lines+markers",
                line=dict(color=COLORS["primary"], width=3),
                marker=dict(size=7, color=COLORS["secondary"]),
            ),
            secondary_y=True,
        )
        fig_trend.update_yaxes(title_text="Volume", secondary_y=False)
        fig_trend.update_yaxes(title_text="Peças Faturadas (R$)", secondary_y=True)
        fig_trend.update_layout(title="Evolução Mensal de Receita e Volume")
        st.plotly_chart(chart_layout(fig_trend), use_container_width=True)
        if len(mensal) >= 2 and mensal.iloc[-2]["faturamento"] > 0:
            delta_trend = (mensal.iloc[-1]["faturamento"] - mensal.iloc[-2]["faturamento"]) / mensal.iloc[-2]["faturamento"]
            insight_trend = f"No mês mais recente, as peças faturadas {'subiram' if delta_trend >= 0 else 'caíram'} {to_pct(abs(delta_trend))} em relação ao mês anterior."
        else:
            insight_trend = f"Peças faturadas recentes no recorte: {to_brl(mensal_last)}."
        render_chart_help(
            "Mostrar a evolução do negócio ao longo dos meses, cruzando receita e volume vendido.",
            insight_trend,
        )

        top_clientes = (
            df_f.groupby("destinatario", as_index=False)["valor_total"]
            .sum()
            .sort_values("valor_total", ascending=False)
            .head(12)
        )
        top_clientes["acumulado"] = top_clientes["valor_total"].cumsum() / top_clientes["valor_total"].sum()

        fig_pareto_clientes = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto_clientes.add_trace(
            go.Bar(
                x=top_clientes["destinatario"],
                y=top_clientes["valor_total"],
                name="Peças Faturadas",
                marker_color=COLORS["secondary"],
            ),
            secondary_y=False,
        )
        fig_pareto_clientes.add_trace(
            go.Scatter(
                x=top_clientes["destinatario"],
                y=top_clientes["acumulado"] * 100,
                name="Acumulado %",
                mode="lines+markers",
                line=dict(color=COLORS["accent"], width=3),
            ),
            secondary_y=True,
        )
        fig_pareto_clientes.update_yaxes(title_text="Peças Faturadas (R$)", secondary_y=False)
        fig_pareto_clientes.update_yaxes(title_text="Acumulado (%)", secondary_y=True, range=[0, 105])
        fig_pareto_clientes.update_layout(title="Pareto de Clientes (Top 12)")
        st.plotly_chart(chart_layout(fig_pareto_clientes), use_container_width=True)
        if not top_clientes.empty and top_clientes["valor_total"].sum() > 0:
            share_top3_clientes = top_clientes["valor_total"].head(3).sum() / top_clientes["valor_total"].sum()
            insight_pareto_cliente = f"Os 3 maiores clientes somam {to_pct(share_top3_clientes)} da receita do top 12."
        else:
            insight_pareto_cliente = "Sem dados suficientes para inferir concentração de clientes."
        render_chart_help(
            "Evidenciar concentração de receita por clientes e apoiar decisões de diversificação da carteira.",
            insight_pareto_cliente,
        )

    with tab2:
        col_a, col_b = st.columns(2)

        with col_a:
            cliente_share = (
                df_f.groupby("destinatario", as_index=False)["valor_total"]
                .sum()
                .sort_values("valor_total", ascending=False)
                .head(10)
            )
            fig_clientes_share = px.pie(
                cliente_share,
                names="destinatario",
                values="valor_total",
                hole=0.45,
                color_discrete_sequence=[COLORS["primary"], COLORS["accent"], COLORS["gold"], COLORS["mint"]],
                title="Participação de Peças Faturadas por Cliente (Top 10)",
            )
            st.plotly_chart(chart_layout(fig_clientes_share), use_container_width=True)
            if not cliente_share.empty and cliente_share["valor_total"].sum() > 0:
                share_top_cliente = cliente_share.iloc[0]["valor_total"] / cliente_share["valor_total"].sum()
                insight_cliente_share = f"O principal cliente representa {to_pct(share_top_cliente)} da receita dentro do top 10 exibido."
            else:
                insight_cliente_share = "Sem dados suficientes para inferir distribuição por cliente."
            render_chart_help(
                "Mostrar a distribuição de receita por cliente para medir concentração da carteira.",
                insight_cliente_share,
            )

        with col_b:
            cliente_scatter = (
                df_f.groupby("destinatario", as_index=False)
                .agg(
                    faturamento=("valor_total", "sum"),
                    volume=("quantidade", "sum"),
                    ticket_medio=("ticket_item", "mean"),
                    pedidos=("pedido", "nunique"),
                )
                .sort_values("faturamento", ascending=False)
                .head(20)
            )
            fig_scatter = px.scatter(
                cliente_scatter,
                x="volume",
                y="faturamento",
                size="ticket_medio",
                color="pedidos",
                color_continuous_scale="Tealgrn",
                hover_name="destinatario",
                title="Clientes: Volume x Receita x Ticket",
                labels={"volume": "Volume", "faturamento": "Receita (R$)", "pedidos": "Pedidos"},
            )
            fig_scatter.update_traces(marker=dict(line=dict(width=1, color="white"), opacity=0.82))
            st.plotly_chart(chart_layout(fig_scatter), use_container_width=True)
            if not cliente_scatter.empty:
                cliente_top = cliente_scatter.iloc[0]["destinatario"]
                insight_scatter = f"{cliente_top} aparece como principal conta em receita entre os 20 maiores clientes."
            else:
                insight_scatter = "Sem dados suficientes para identificar posicionamento de clientes."
            render_chart_help(
                "Cruzar volume, receita e ticket para identificar clientes estratégicos e oportunidades de crescimento.",
                insight_scatter,
            )

        ticket_cliente = (
            df_f.groupby("destinatario", as_index=False)
            .agg(faturamento=("valor_total", "sum"), pedidos=("pedido", "nunique"))
            .query("pedidos > 0")
        )
        ticket_cliente["ticket"] = ticket_cliente["faturamento"] / ticket_cliente["pedidos"]
        ticket_cliente = ticket_cliente.sort_values("ticket", ascending=False).head(15)

        fig_ticket = px.bar(
            ticket_cliente,
            x="ticket",
            y="destinatario",
            orientation="h",
            title="Top 15 Clientes por Ticket Médio de Pedido",
            color="ticket",
            color_continuous_scale=["#CDECE7", "#2A9D8F", "#1D3557"],
            labels={"ticket": "Ticket Médio (R$)", "destinatario": "Cliente"},
        )
        fig_ticket.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(chart_layout(fig_ticket), use_container_width=True)
        if not ticket_cliente.empty:
            insight_ticket = f"Maior ticket médio no recorte: {ticket_cliente.iloc[0]['destinatario']} com {to_brl(ticket_cliente.iloc[0]['ticket'])}."
        else:
            insight_ticket = "Sem dados suficientes para comparar ticket por cliente."
        render_chart_help(
            "Mostrar quais clientes pagam maior valor por pedido, apoiando estratégia de rentabilidade.",
            insight_ticket,
        )

    with tab3:
        col_p1, col_p2 = st.columns(2)

        produto_perf = (
            df_f.groupby(["descricao_produto", "cod_prod"], as_index=False)
            .agg(faturamento=("valor_total", "sum"), volume=("quantidade", "sum"))
            .sort_values("faturamento", ascending=False)
        )

        top_prod = produto_perf.head(15).copy()
        top_prod["produto"] = top_prod["descricao_produto"].str.slice(0, 48)

        with col_p1:
            fig_prod = px.bar(
                top_prod.sort_values("faturamento"),
                x="faturamento",
                y="produto",
                orientation="h",
                title="Top 15 Produtos por Receita",
                color="faturamento",
                color_continuous_scale=["#FCE4D8", "#F4A261", "#E76F51"],
                labels={"faturamento": "Receita (R$)", "produto": "Produto"},
            )
            st.plotly_chart(chart_layout(fig_prod), use_container_width=True)
            if not produto_perf.empty and produto_perf["faturamento"].sum() > 0:
                share_produto_lider = produto_perf.iloc[0]["faturamento"] / produto_perf["faturamento"].sum()
                insight_prod_bar = f"O produto líder responde por {to_pct(share_produto_lider)} da receita total de produtos no recorte."
            else:
                insight_prod_bar = "Sem dados suficientes para inferir concentração por produto."
            render_chart_help(
                "Destacar os produtos que mais contribuem para peças faturadas, orientando foco de mix e estoque.",
                insight_prod_bar,
            )

        with col_p2:
            fig_tree = px.treemap(
                top_prod,
                path=["produto"],
                values="faturamento",
                color="volume",
                color_continuous_scale=["#D7EFEA", "#2A9D8F", "#1D3557"],
                title="Mix de Receita dos Principais Produtos",
            )
            st.plotly_chart(chart_layout(fig_tree), use_container_width=True)
            if not top_prod.empty and top_prod["faturamento"].sum() > 0:
                share_top5_mix = top_prod["faturamento"].head(5).sum() / top_prod["faturamento"].sum()
                insight_tree = f"Os 5 maiores itens concentram {to_pct(share_top5_mix)} da receita dentro do top 15 exibido."
            else:
                insight_tree = "Sem dados suficientes para leitura de mix."
            render_chart_help(
                "Visualizar rapidamente o mix de receita entre os produtos mais relevantes.",
                insight_tree,
            )

        pareto = produto_perf.copy()
        pareto["acumulado"] = pareto["faturamento"].cumsum() / pareto["faturamento"].sum()
        pareto_display = pareto.head(25)

        fig_pareto_prod = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto_prod.add_trace(
            go.Bar(
                x=pareto_display["descricao_produto"].str.slice(0, 28),
                y=pareto_display["faturamento"],
                name="Receita",
                marker_color=COLORS["mint"],
            ),
            secondary_y=False,
        )
        fig_pareto_prod.add_trace(
            go.Scatter(
                x=pareto_display["descricao_produto"].str.slice(0, 28),
                y=pareto_display["acumulado"] * 100,
                name="Acumulado %",
                mode="lines+markers",
                line=dict(color=COLORS["accent"], width=3),
            ),
            secondary_y=True,
        )
        fig_pareto_prod.update_yaxes(title_text="Receita (R$)", secondary_y=False)
        fig_pareto_prod.update_yaxes(title_text="Acumulado (%)", secondary_y=True, range=[0, 105])
        fig_pareto_prod.update_layout(title="Curva ABC de Produtos (Top 25)")
        st.plotly_chart(chart_layout(fig_pareto_prod), use_container_width=True)
        if not pareto.empty:
            n_prod_80 = int((pareto["acumulado"] <= 0.8).sum() + 1)
            n_prod_80 = min(n_prod_80, len(pareto))
            insight_pareto_prod = f"Aproximadamente {n_prod_80} produtos explicam 80% da receita acumulada no período."
        else:
            insight_pareto_prod = "Sem dados suficientes para curva ABC."
        render_chart_help(
            "Classificar produtos por impacto financeiro e definir foco de gestão na curva ABC.",
            insight_pareto_prod,
        )

    with tab4:
        col_g1, col_g2 = st.columns(2)

        estado_perf = (
            df_f.groupby("estado", as_index=False)
            .agg(faturamento=("valor_total", "sum"), volume=("quantidade", "sum"), clientes=("destinatario", "nunique"))
            .sort_values("faturamento", ascending=False)
        )

        with col_g1:
            fig_estado = px.bar(
                estado_perf,
                x="estado",
                y="faturamento",
                color="clientes",
                title="Receita por Estado",
                color_continuous_scale=["#D6EAF8", "#0C6E74", "#1D3557"],
                labels={"faturamento": "Receita (R$)", "estado": "Estado", "clientes": "Clientes"},
            )
            st.plotly_chart(chart_layout(fig_estado), use_container_width=True)
            if not estado_perf.empty and estado_perf["faturamento"].sum() > 0:
                share_estado_lider = estado_perf.iloc[0]["faturamento"] / estado_perf["faturamento"].sum()
                insight_estado = f"O estado líder concentra {to_pct(share_estado_lider)} da receita geográfica no recorte."
            else:
                insight_estado = "Sem dados suficientes para distribuição por estado."
            render_chart_help(
                "Comparar desempenho por estado para orientar expansão comercial e cobertura regional.",
                insight_estado,
            )

        with col_g2:
            cidade_perf = (
                df_f.groupby("cidade", as_index=False)["valor_total"]
                .sum()
                .sort_values("valor_total", ascending=False)
                .head(15)
            )
            fig_cidade = px.bar(
                cidade_perf.sort_values("valor_total"),
                x="valor_total",
                y="cidade",
                orientation="h",
                title="Top 15 Cidades por Receita",
                color="valor_total",
                color_continuous_scale=["#EEF7FA", "#2A9D8F", "#1D3557"],
                labels={"valor_total": "Receita (R$)", "cidade": "Cidade"},
            )
            st.plotly_chart(chart_layout(fig_cidade), use_container_width=True)
            if not cidade_perf.empty and cidade_perf["valor_total"].sum() > 0:
                share_cidade = cidade_perf.iloc[0]["valor_total"] / cidade_perf["valor_total"].sum()
                insight_cidade = f"A cidade líder representa {to_pct(share_cidade)} da receita entre as 15 cidades exibidas."
            else:
                insight_cidade = "Sem dados suficientes para distribuição por cidade."
            render_chart_help(
                "Identificar polos urbanos com maior geração de receita para priorização comercial.",
                insight_cidade,
            )

        st.subheader("Detalhamento do Recorte")
        detalhamento = df_f[
            [
                "data_emissao",
                "pedido",
                "destinatario",
                "cidade",
                "estado",
                "descricao_produto",
                "quantidade",
                "valor_unit",
                "valor_total",
                "frete",
                "situacao",
            ]
        ].sort_values("data_emissao", ascending=False)

        detalhamento_display = detalhamento.copy()
        detalhamento_display["data_emissao"] = detalhamento_display["data_emissao"].apply(to_date_br_short)
        # Formatar colunas monetárias com separadores de milhar
        detalhamento_display["valor_unit"] = detalhamento_display["valor_unit"].apply(
            lambda x: to_brl(safe_to_float(x)) if safe_to_float(x) is not None else "R$ 0,00"
        )
        detalhamento_display["valor_total"] = detalhamento_display["valor_total"].apply(
            lambda x: to_brl(safe_to_float(x)) if safe_to_float(x) is not None else "R$ 0,00"
        )
        detalhamento_display["frete"] = detalhamento_display["frete"].apply(
            lambda x: to_brl(safe_to_float(x)) if safe_to_float(x) is not None else "R$ 0,00"
        )
        # Formatar coluna quantidade com separadores de milhar
        detalhamento_display["quantidade"] = detalhamento_display["quantidade"].apply(
            lambda x: to_int(safe_to_float(x)) if safe_to_float(x) is not None else "0"
        )

        st.dataframe(
            detalhamento_display,
            use_container_width=True,
            hide_index=True,
            height=390,
        )

        st.download_button(
            label="Baixar recorte filtrado (CSV)",
            data=detalhamento_display.to_csv(index=False).encode("utf-8-sig"),
            file_name="recorte_dashboard_produtos_faturados.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab5:
        c_meta1, c_meta2 = st.columns([1, 2])

        with c_meta1:
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=float(mensal_last),
                    number={"prefix": "R$ "},
                    title={"text": "Peças Faturadas do mês recente"},
                    gauge={
                        "axis": {"range": [0, max(meta_mensal * 1.5, mensal_last * 1.2 + 1)]},
                        "bar": {"color": COLORS["primary"]},
                        "steps": [
                            {"range": [0, meta_mensal * 0.85], "color": "#ffd6cc"},
                            {"range": [meta_mensal * 0.85, meta_mensal], "color": "#ffe9bf"},
                            {"range": [meta_mensal, max(meta_mensal * 1.5, mensal_last * 1.2 + 1)], "color": "#d8f3dc"},
                        ],
                        "threshold": {
                            "line": {"color": COLORS["accent"], "width": 4},
                            "thickness": 0.75,
                            "value": meta_mensal,
                        },
                    },
                )
            )
            fig_gauge.update_layout(height=320)
            st.plotly_chart(chart_layout(fig_gauge), use_container_width=True)
            render_chart_help(
                "Acompanhar rapidamente se o mês recente está acima ou abaixo da meta definida.",
                f"Atingimento atual da meta: {to_pct((mensal_last / meta_mensal) if meta_mensal > 0 else 0)}.",
            )

            atingimento = (mensal_last / meta_mensal) if meta_mensal > 0 else 0
            st.metric("Atingimento da meta", to_pct(atingimento))

        with c_meta2:
            if forecast_df.empty:
                st.info("Previsão disponível quando houver pelo menos 4 meses no recorte filtrado.")
            else:
                historico = mensal[["ano_mes", "faturamento"]].copy()
                historico["tipo"] = "Histórico"

                previsto = forecast_df[["ano_mes", "faturamento_previsto"]].rename(columns={"faturamento_previsto": "faturamento"})
                previsto["tipo"] = "Previsto"

                fig_forecast = go.Figure()
                fig_forecast.add_trace(
                    go.Scatter(
                        x=historico["ano_mes"],
                        y=historico["faturamento"],
                        mode="lines+markers",
                        name="Histórico",
                        line=dict(color=COLORS["secondary"], width=3),
                    )
                )
                fig_forecast.add_trace(
                    go.Scatter(
                        x=forecast_df["ano_mes"],
                        y=forecast_df["faturamento_previsto"],
                        mode="lines+markers",
                        name="Previsão base",
                        line=dict(color=COLORS["primary"], width=3, dash="dot"),
                    )
                )
                fig_forecast.add_trace(
                    go.Scatter(
                        x=forecast_df["ano_mes"],
                        y=forecast_df["faixa_superior"],
                        mode="lines",
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
                fig_forecast.add_trace(
                    go.Scatter(
                        x=forecast_df["ano_mes"],
                        y=forecast_df["faixa_inferior"],
                        mode="lines",
                        line=dict(width=0),
                        fill="tonexty",
                        fillcolor="rgba(12,110,116,0.16)",
                        name="Faixa provável (80%)",
                    )
                )
                fig_forecast.update_layout(title="Projeção de Peças Faturadas para Próximos 4 Meses")
                st.plotly_chart(chart_layout(fig_forecast), use_container_width=True)
                meses_acima_meta = int((forecast_df["faturamento_previsto"] >= meta_mensal).sum())
                render_chart_help(
                    "Projetar receita futura para antecipar decisões comerciais e metas.",
                    f"No cenário base, {meses_acima_meta} de {len(forecast_df)} meses projetados superam a meta mensal atual.",
                )

                cenario = forecast_df[["ano_mes", "faturamento_previsto"]].copy()
                cenario["Conservador (-10%)"] = cenario["faturamento_previsto"] * 0.9
                cenario["Base"] = cenario["faturamento_previsto"]
                cenario["Otimista (+10%)"] = cenario["faturamento_previsto"] * 1.1
                cenario["ano_mes"] = cenario["ano_mes"].dt.strftime("%d/%m/%y")

                # Formatar colunas monetárias
                cenario_display = cenario.rename(columns={"ano_mes": "Mês"})[["Mês", "Conservador (-10%)", "Base", "Otimista (+10%)"]].copy()
                cenario_display["Conservador (-10%)"] = cenario_display["Conservador (-10%)"].apply(lambda x: to_brl(x))
                cenario_display["Base"] = cenario_display["Base"].apply(lambda x: to_brl(x))
                cenario_display["Otimista (+10%)"] = cenario_display["Otimista (+10%)"].apply(lambda x: to_brl(x))

                st.dataframe(
                    cenario_display,
                    use_container_width=True,
                    hide_index=True,
                )

    missing_nota = df["nota"].isna().mean() * 100
    missing_cfop = df["cfop"].isna().mean() * 100
    st.markdown(
        f'<div class="foot-note">Qualidade de dados: Nota com {missing_nota:.1f}% de ausência e CFOP com {missing_cfop:.1f}% de ausência. Essas colunas foram mantidas fora das análises críticas.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
