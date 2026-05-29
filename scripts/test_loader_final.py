import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.lencol_loader_smart import load_lencol_smart_csv

df = load_lencol_smart_csv()

print("\n" + "="*80)
print(f"✓ LOADER FUNCIONANDO: {len(df)} linhas carregadas")
print("="*80)

if len(df) > 0:
    print("\nColunas extraídas:")
    for col in df.columns:
        print(f"  • {col}")
    
    print("\nPrimeiras 5 linhas:")
    print(df.head()[['DATA', 'OP', 'QUANT', 'EMPRESA']].to_string())
    
    print(f"\nOPs únicos: {df['OP'].nunique()}")
    print(f"OPs: {sorted(df['OP'].unique().astype(str))[:10]}")
    
    print(f"\nQuantidades totais: {df['QUANT'].sum()}")
    print(f"Datas: {df['DATA'].min()} → {df['DATA'].max()}")
else:
    print("\n✗ FALHA: DataFrame vazio!")
