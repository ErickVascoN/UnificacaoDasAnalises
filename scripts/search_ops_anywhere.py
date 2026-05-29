"""
Procura por OPs 81 e 82 em TODO o CSV (qualquer data)
"""

import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url = f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"

print("=" * 80)
print("Procurando OPs 81 e 82 em TODO o CSV (qualquer data)")
print("=" * 80)

r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

texto_bruto = r.content.decode("utf-8")

# Busca textual direta
print("\n🔍 Busca textual no CSV bruto:")
if ",81," in texto_bruto or ",81\n" in texto_bruto or " 81," in texto_bruto or " 81\n" in texto_bruto:
    print("✓ OP 81 encontrada no texto bruto")
else:
    print("✗ OP 81 NÃO encontrada no texto bruto")

if ",82," in texto_bruto or ",82\n" in texto_bruto or " 82," in texto_bruto or " 82\n" in texto_bruto:
    print("✓ OP 82 encontrada no texto bruto")
else:
    print("✗ OP 82 NÃO encontrada no texto bruto")

# Carrega como DF
df = pd.read_csv(io.StringIO(texto_bruto), header=0, dtype=str)
print(f"\n📊 Dimensões do CSV: {len(df)} linhas × {len(df.columns)} colunas")

# Procura em todas as colunas
print("\n🔍 Procurando em todas as colunas do DataFrame:")
found = False
for col in df.columns:
    matches = df[df[col].astype(str).str.contains("^81$|^82$", regex=True, na=False)]
    if not matches.empty:
        print(f"✓ Coluna '{col}': encontrou {len(matches)} ocorrência(s)")
        found = True
        for idx, row in matches.iterrows():
            print(f"  Linha {idx}: {row.to_dict()}")

if not found:
    print("✗ OPs 81 e 82 não encontradas em nenhuma coluna")

# Mostra todas as linhas que contêm "27/05" em qualquer coluna
print(f"\n📅 Mostrando todas as linhas com '27/05' em qualquer coluna:")
mask = df.astype(str).apply(lambda x: x.str.contains("27/05", na=False)).any(axis=1)
matching_rows = df[mask]
print(f"Encontradas {len(matching_rows)} linhas")

for idx, row in matching_rows.iterrows():
    print(f"\nLinha {idx}: {dict(row)}")

print("\n" + "=" * 80)
