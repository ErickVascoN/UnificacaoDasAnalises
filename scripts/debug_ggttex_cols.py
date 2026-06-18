"""
Debug: inspeciona colunas brutas e totais carregados pelo loader
para LITTEX, GGTTEX_FRONHA e GGTTEX_JOGOS.

Uso:
    python scripts/debug_ggttex_cols.py
"""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import get_raw, invalidate
from utils.normalize import normalize_text
from utils.date_parser import parse_date_series, detectar_ordem
from utils.producao_interno_loader import load_interno_unidade
from config.settings import PRODUCAO_INTERNO_SHEETS
import pandas as pd
from datetime import date, timedelta

SEP = "=" * 70

# Semana atual e anterior
hoje = date.today()
segunda_atual = hoje - timedelta(days=hoje.weekday())
semanas = [
    (segunda_atual - timedelta(weeks=1), segunda_atual - timedelta(weeks=1) + timedelta(days=6), "semana -1"),
    (segunda_atual,                       segunda_atual + timedelta(days=6),                     "semana atual"),
]


def _achar_coluna(colunas, *termos):
    termos_norm = [normalize_text(t) for t in termos]
    for col in colunas:
        cn = normalize_text(col)
        if any(t and t in cn for t in termos_norm):
            return col
    return None


def inspecionar_planilha(chave: str):
    print(f"\n{SEP}")
    print(f"PLANILHA: {chave}")
    print(SEP)

    cfg = PRODUCAO_INTERNO_SHEETS[chave]
    # Força busca fresca (ignora cache)
    invalidate(cfg["id"], cfg["gid"])
    conteudo = get_raw(cfg["id"], cfg["gid"], ttl=0)
    if not conteudo or not conteudo.strip():
        print("  !! CSV vazio ou indisponível")
        return

    raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
    raw.columns = [str(c).strip() for c in raw.columns]
    cols = list(raw.columns)

    # 1) Colunas brutas
    print(f"\n  Total de colunas: {len(cols)}")
    print("  Colunas brutas:")
    for i, c in enumerate(cols):
        print(f"    [{i:02d}] '{c}'")

    # 2) O que o loader detectaria
    col_data  = _achar_coluna(cols, "DATA")
    col_colab = _achar_coluna(cols, "PRESTADOR", "COLABORADOR")
    col_qtd   = _achar_coluna(cols, "TOTAL PRODUZIDO", "TOTAL CONFERIDO", "TOTAL")
    col_setor = _achar_coluna(cols, "SETOR")
    col_func  = _achar_coluna(cols, "FUNCAO")
    if chave == "LITTEX":
        col_prod = _achar_coluna(cols, "PRODUTO") or _achar_coluna(cols, "DESCRICAO")
    else:
        col_prod = _achar_coluna(cols, "DESCRICAO") or _achar_coluna(cols, "PRODUTO")
    col_cli   = _achar_coluna(cols, "CLIENTE") or _achar_coluna(cols, "EMPRESA")

    print(f"\n  Colunas detectadas pelo loader:")
    print(f"    DATA      → '{col_data}'")
    print(f"    COLAB     → '{col_colab}'")
    print(f"    QUANTIDADE→ '{col_qtd}'")
    print(f"    SETOR     → '{col_setor}'")
    print(f"    FUNCAO    → '{col_func}'")
    print(f"    PRODUTO   → '{col_prod}'")
    print(f"    CLIENTE   → '{col_cli}'")

    if not col_data or not col_colab or not col_qtd:
        print("  !! Colunas essenciais não encontradas — loader retornaria DataFrame vazio")
        return

    # 3) Formato de data detectado
    ordem = detectar_ordem(raw[col_data])
    print(f"\n  Formato de data detectado: {ordem}")
    print(f"  Exemplos de data bruta: {raw[col_data].dropna().head(5).tolist()}")

    # 4) Totais por semana (via loader vs. raw)
    datas_loader = parse_date_series(raw[col_data])
    qtd_raw = pd.to_numeric(
        raw[col_qtd].astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0)

    print(f"\n  Total bruto (sem filtro): {int(qtd_raw.sum())}")

    print(f"\n  Totais por semana (RAW vs LOADER):")
    df_loader = load_interno_unidade(chave)
    for seg, dom, label in semanas:
        mask_raw = (datas_loader.dt.date >= seg) & (datas_loader.dt.date <= dom)
        soma_raw = int(qtd_raw[mask_raw].sum())
        n_raw = int(mask_raw.sum())

        if df_loader.empty:
            soma_loader = 0
            n_loader = 0
        else:
            mask_ldr = (df_loader["DATA"].dt.date >= seg) & (df_loader["DATA"].dt.date <= dom)
            soma_loader = int(df_loader.loc[mask_ldr, "QUANTIDADE"].sum())
            n_loader = int(mask_ldr.sum())

        dif = soma_loader - soma_raw
        flag = " <<< DIFERENÇA" if abs(dif) > 0 else ""
        print(f"    {label} ({seg} a {dom}): RAW={soma_raw} ({n_raw} linhas) | LOADER={soma_loader} ({n_loader} linhas) | dif={dif:+}{flag}")

    # 5) Mostra primeiras linhas da coluna de quantidade para inspeção visual
    print(f"\n  Amostra da coluna QUANTIDADE ('{col_qtd}') — primeiras 10 linhas:")
    amostra = raw[[col_data, col_colab, col_qtd]].head(10)
    print(amostra.to_string(index=False))


for chave in ["LITTEX", "GGTTEX_FRONHA", "GGTTEX_JOGOS"]:
    try:
        inspecionar_planilha(chave)
    except Exception as e:
        print(f"\n  ERRO ao inspecionar {chave}: {e}")

print(f"\n{SEP}")
print("Concluído.")
