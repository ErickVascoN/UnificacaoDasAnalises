"""
Extrai dados CORRETOS de 5/27/2026 (27 de maio)
considerando o desalinhamento das colunas
"""

import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url = f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"

print("=" * 80)
print("Extraindo dados com colunas CORRETAS de 5/27/2026")
print("=" * 80)

r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

df = pd.read_csv(io.StringIO(r.content.decode("utf-8")), header=0, dtype=str)

print(f"\n📊 CSV tem {len(df.columns)} colunas")
print(f"\nNomes das colunas (primeiras 10):")
for i, col in enumerate(df.columns[:10]):
    print(f"  [{i}] '{col}'")

# Coluna 0 tem as datas
data_col = df.columns[0]  # 'CONTROLE DE CORTE DIÁRIO LENÇOL DATA '

print(f"\n🔍 Filtrando por data = 5/27/2026 na coluna '{data_col}'...")
df_27_05 = df[df[data_col] == "5/27/2026"].copy()

print(f"✓ Encontradas {len(df_27_05)} linhas com 5/27/2026")

if len(df_27_05) > 0:
    print("\n📋 Todas as linhas de 5/27/2026:")
    print("-" * 80)
    for idx, row in df_27_05.iterrows():
        print(f"\nLinha {idx}:")
        for col, val in row.items():
            if pd.notna(val) and str(val).strip():
                print(f"  {col}: {val}")
    
    # Procura por OPs 81 e 82
    print("\n" + "=" * 80)
    print("🔍 Procurando OPs 81 e 82:")
    for op_num in ["81", "82"]:
        encontrado = False
        for idx, row in df_27_05.iterrows():
            for col, val in row.items():
                if str(val).strip() == op_num:
                    print(f"✓ OP {op_num} encontrada em coluna '{col}' (Linha {idx})")
                    print(f"  Linha completa: {dict(row)}")
                    encontrado = True
                    break
        if not encontrado:
            print(f"✗ OP {op_num} não encontrada")

print("\n" + "=" * 80)
