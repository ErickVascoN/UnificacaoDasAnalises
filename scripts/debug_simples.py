"""
Debug simples: verificar se OPs estão sendo carregadas corretamente do lençol
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from utils.lencol_loader_smart import load_lencol_smart_csv

print("Carregando lençol...")
df = load_lencol_smart_csv()

print(f"\n✓ Total: {len(df)} linhas")
print(f"✓ Colunas: {list(df.columns)}")

if not df.empty:
    print(f"\nPrimeiras 10 OPs do lençol:")
    print(df[["DATA", "OP", "QUANT"]].head(10).to_string(index=False))
    
    print(f"\nOPs únicas: {df['OP'].nunique()}")
    print(f"OPs com valor > 0: {(df['QUANT'] > 0).sum()}")
    
    print(f"\nTotais por OP (top 10):")
    totais = df.groupby("OP")["QUANT"].sum().sort_values(ascending=False)
    for op, qtd in totais.head(10).items():
        print(f"  {op}: {qtd:,.0f}".replace(",", "."))
