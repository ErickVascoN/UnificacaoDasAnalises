"""
Debug: Mostrar exatamente qual coluna é mapeada para DATA e qual é seu conteúdo
"""
import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url_csv = (
    f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
    f"/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"
)

print("Baixando CSV...")
r = requests.get(url_csv, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
conteudo = r.content.decode("utf-8")

# Lê com header=0
df = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)

print(f"Colunas originais ({len(df.columns)} total):")
for i, col in enumerate(df.columns[:15]):
    print(f"  [{i}] '{col}'")

# Normaliza
df.columns = [c.strip() if isinstance(c, str) else f"COL_{i}" 
              for i, c in enumerate(df.columns)]

print(f"\nColunas após strip:")
for i, col in enumerate(df.columns[:15]):
    print(f"  [{i}] '{col}'")

# Procura DATA
print("\nProcurando coluna DATA...")
for col in df.columns:
    col_upper = col.upper().strip()
    if "CONTROLE" in col_upper and "LENÇOL" in col_upper and "DATA" in col_upper:
        print(f"\n✓ Encontrada: '{col}'")
        print(f"  Tipo: {df[col].dtype}")
        print(f"  Primeiros 10 valores:")
        for val in df[col].head(10):
            print(f"    '{val}'")
        
        # Tenta parsear
        print(f"\n  Parseando com dayfirst=True...")
        parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        print(f"  Válidas: {parsed.notna().sum()}/{len(parsed)}")
        print(f"  Primeiras 10 após parse:")
        for val in parsed.head(10):
            print(f"    {val}")
        break
