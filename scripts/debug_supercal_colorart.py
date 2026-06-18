"""
Verifica OPs na programação que têm tanto produtos SUPERCAL quanto COLOR ART
(ou outras marcas que podem colidir no matching).

Execute: python scripts/debug_supercal_colorart.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import pandas as pd
from utils.cache_manager import get_raw
from utils.normalize import normalize_text

PROG_ID  = "1FeTwrPEBOcC6RmD_5zh8NQLwOrYO87XA"
PROG_GID = "708887209"

texto = get_raw(PROG_ID, PROG_GID, ttl=60)
df = pd.read_csv(io.StringIO(texto), dtype=str)
df.columns = df.columns.str.strip()
df["QNT. PROG"] = pd.to_numeric(df.get("QNT. PROG", 0), errors="coerce").fillna(0).astype(int)

# Coluna de OP
op_col  = "PED. CLIENTE"
desc_col = "DESCRIÇÃO DO PRODUTO" if "DESCRIÇÃO DO PRODUTO" in df.columns else "PRODUTO"

df["_DESC_NORM"] = df[desc_col].fillna("").apply(normalize_text)
df["_OP"]        = df[op_col].fillna("").astype(str).str.strip()

# Filtra OPs válidas com descrição
df = df[(df["_OP"] != "") & (df["_OP"].str.upper() != "NAN") & (df["_DESC_NORM"] != "")]

MARCAS = {"SUPERCAL": "SUPERCAL", "COLOR": "COLOR ART"}

def marcas_da_linha(desc_norm: str) -> set:
    words = set(desc_norm.split())
    return {label for token, label in MARCAS.items() if token in words}

df["_MARCAS"] = df["_DESC_NORM"].apply(marcas_da_linha)

# Agrupa por OP e coleta todas as marcas presentes
op_marcas = df.groupby("_OP")["_MARCAS"].apply(lambda s: set().union(*s))
conflito  = op_marcas[op_marcas.apply(len) > 1]

print("=" * 70)
print(f"OPs com mistura de SUPERCAL + COLOR ART na programação: {len(conflito)}")
print("=" * 70)

if conflito.empty:
    print("Nenhuma OP com conflito de marca encontrada.")
else:
    for op, marcas in conflito.items():
        produtos = df[df["_OP"] == op][[desc_col, "QNT. PROG"]].drop_duplicates()
        print(f"\nOP {op}  →  marcas: {marcas}")
        for _, row in produtos.iterrows():
            desc = str(row[desc_col])[:80]
            print(f"    {row['QNT. PROG']:>6}  {desc}")
