"""
Debug 2: Verificar se o cruzamento está funcionando após a correção
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from utils.lencol_loader_smart import load_lencol_smart_csv

# Simular o que load_cortes faz
df_lencol = load_lencol_smart_csv()

print(f"Total de linhas no lençol: {len(df_lencol)}")
print(f"Total de OPs únicas: {df_lencol['OP'].nunique()}")

# Soma por OP (como o load_cortes faz)
totais_por_op = df_lencol.groupby("OP")["QUANT"].sum().sort_values(ascending=False)

print(f"\nTop 20 OPs por quantidade cortada:")
for op, qtd in totais_por_op.head(20).items():
    print(f"  OP {op}: {qtd:>8.0f} peças".replace(",", "."))

# Exemplos de OPs que estava bugadas antes
print(f"\nVerificação de OPs específicas:")
ops_para_verificar = ['255910', '91532', '91534', '81', '82']
for op in ops_para_verificar:
    cortada = df_lencol[df_lencol['OP'] == op]['QUANT'].sum()
    if cortada > 0:
        print(f"  ✓ OP {op}: {cortada:,.0f} peças".replace(",", "."))
    else:
        print(f"  ✗ OP {op}: NÃO encontrada")
