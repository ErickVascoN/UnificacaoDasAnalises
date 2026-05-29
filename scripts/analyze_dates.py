"""
Verifica formatos de data no CSV
"""

import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url = f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"

print("=" * 80)
print("Analisando formatos de data no CSV via gviz/tq")
print("=" * 80)

r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

df = pd.read_csv(io.StringIO(r.content.decode("utf-8")), header=0, dtype=str)

print(f"\n📊 Dimensões: {len(df)} linhas × {len(df.columns)} colunas")
print(f"\n📋 Primeiras 3 colunas:\n{df.iloc[:5, :3]}")

# Procura coluna que parece ter datas
print("\n🔍 Procurando coluna com datas:")
for col in df.columns[:5]:  # Verifica primeiras 5 colunas
    samples = df[col].dropna().unique()[:10]
    print(f"\nColuna '{col}':")
    print(f"  Amostras: {samples}")
    
    # Conta ocorrências de patterns de data
    data_pattern_count = sum(1 for s in samples if any(c.isdigit() for c in str(s)))
    if data_pattern_count > 0:
        print(f"  ➜ {data_pattern_count}/{len(samples)} valores parecem ser datas/números")

# Mostra linhas inteiras de exemplo
print("\n" + "=" * 80)
print("Linhas de exemplo (completas):")
print("=" * 80)
for i in range(min(3, len(df))):
    print(f"\nLinha {i}:")
    for col, val in df.iloc[i].items():
        if pd.notna(val) and str(val).strip():
            print(f"  {col}: {val}")

# Procura especificamente por padrões de data
print("\n" + "=" * 80)
print("Procurando padrões de data (Maio/May 2026):")
print("=" * 80)

for col in df.columns:
    matches = df[df[col].astype(str).str.contains("May|5/2026|5/27|27|2026-05", regex=True, case=False, na=False)]
    if not matches.empty:
        print(f"\n✓ Coluna '{col}': {len(matches)} ocorrência(s)")
        for idx, val in matches[col].items():
            print(f"  → {val}")

print("\n" + "=" * 80)
