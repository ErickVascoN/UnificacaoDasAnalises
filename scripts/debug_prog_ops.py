"""
Debug: Verificar correspondência entre formato de OP no lençol vs programação
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from utils.lencol_loader_smart import load_lencol_smart_csv

df_lencol = load_lencol_smart_csv()

print("="*80)
print("OPs do Lençol - Verificar se há 'PROG' ou variações")
print("="*80)

# Buscar OPs que contêm "PROG"
ops_com_prog = df_lencol[df_lencol["OP"].str.contains("PROG", case=False, na=False)]

if not ops_com_prog.empty:
    print(f"\n✓ Encontradas {len(ops_com_prog)} linhas com 'PROG':")
    print(ops_com_prog[["DATA", "OP", "CATEGORIA", "QUANT"]].drop_duplicates(subset=["OP"]).to_string(index=False))
    
    print(f"\nOPs únicas com PROG:")
    ops_prog_uniq = ops_com_prog["OP"].unique()
    for op in sorted(ops_prog_uniq):
        total = df_lencol[df_lencol["OP"] == op]["QUANT"].sum()
        print(f"  · {op}: {total:,.0f} peças".replace(",", "."))
else:
    print("✗ Nenhuma OP com 'PROG' encontrada")

# Verificar formatos especiais
print("\n" + "="*80)
print("Amostra de todas as OPs únicas:")
print("="*80)
todas_ops = sorted(df_lencol["OP"].unique())
for op in todas_ops:
    total = df_lencol[df_lencol["OP"] == op]["QUANT"].sum()
    print(f"  '{op}': {total:>8.0f} peças".replace(",", "."))
