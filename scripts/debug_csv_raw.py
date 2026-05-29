"""
Debug detalhado: verificar como as colunas estão sendo detectadas
"""
import requests
import io
import pandas as pd
import re as _re

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url_gviz = (
    f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
    f"/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"
)

url_export = (
    f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
    f"/export?format=csv&gid={LENCOL_SPREADSHEET_GID}"
)

print("Baixando CSV raw...")
r = requests.get(url_gviz, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
conteudo = r.content.decode("utf-8")

print(f"Total de caracteres: {len(conteudo)}")

# Primeiras linhas
linhas = conteudo.splitlines()
print(f"\nPrimeiras 5 linhas RAW:")
for i, linha in enumerate(linhas[:5]):
    print(f"  {i}: {linha[:120]}")

# Parse com header=0
df = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)

print(f"\nColunas detectadas (total {len(df.columns)}):")
for i, col in enumerate(df.columns):
    print(f"  {i}: '{col}'")

print(f"\nPrimeiras 5 linhas (parse automático):")
print(df.head(5).to_string())

# Detecta coluna de DATA (como o código faz)
print("\n" + "="*80)
print("Detectando coluna DATA...")
data_col_idx = None
for i, col in enumerate(df.columns):
    samples = df[col].dropna().unique()[:50]
    # Procura por padrão de data
    date_count = sum(1 for s in samples if any(
        ('/' in str(s) and '2026' in str(s))
        for _ in [1]
    ))
    if date_count >= len(samples) * 0.5:
        data_col_idx = i
        print(f"✓ Coluna DATA encontrada: índice {i}, nome '{col}'")
        print(f"  Amostra: {samples[:3]}")
        break

if data_col_idx is not None:
    print(f"\nExtraindo 11 colunas a partir de {data_col_idx}...")
    df_slice = df.iloc[:, data_col_idx:data_col_idx+11]
    print(f"Colunas extraídas: {list(df_slice.columns)}")
    print(f"\nPrimeiras 5 linhas extraídas:")
    print(df_slice.head(5).to_string())
else:
    print("✗ Coluna DATA NÃO DETECTADA")
