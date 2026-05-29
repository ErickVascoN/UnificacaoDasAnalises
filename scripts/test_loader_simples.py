import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.lencol_loader_smart import load_lencol_smart_csv

# Teste direto do loader
df_lencol = load_lencol_smart_csv()

print("\n" + "="*80)
print("*** LENCOL LOADER FUNCIONANDO ***")
print("="*80)
print(f"Linhas: {len(df_lencol)}")
print(f"OPs unicos: {df_lencol['OP'].nunique()}")
print(f"Quantidades: {df_lencol['QUANT'].sum()}")

print("\nSample OPs:")
print(df_lencol[['OP', 'QUANT', 'EMPRESA']].drop_duplicates('OP').head(15).to_string())

print("\n*** LOADER PRONTO PARA DASHBOARD ***")
