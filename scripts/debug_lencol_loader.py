"""
Script de diagnóstico do loader de lençol.
Execute com: python scripts/debug_lencol_loader.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

print("=" * 70)
print("1. Testando get_raw() para lençol")
print("=" * 70)

from utils.cache_manager import get_raw, invalidate

# Força download fresco
invalidate("1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa", "1396046910")

csv = get_raw("1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa", "1396046910", ttl=1)
if not csv:
    print("ERRO: get_raw() retornou None — planilha inacessível")
    sys.exit(1)

lines = csv.splitlines()
print(f"\nCSV recebido: {len(csv):,} bytes, {len(lines)} linhas")
print("\n--- Primeiras 8 linhas ---")
for i, l in enumerate(lines[:8]):
    print(f"  [{i}] {l[:120]}")

print("\n" + "=" * 70)
print("2. Testando load_lencol_smart_xlsx()")
print("=" * 70)

from utils.lencol_loader_smart import load_lencol_smart_xlsx

df = load_lencol_smart_xlsx()

if df.empty:
    print("\nERRO: DataFrame vazio!\n")
    print("Verifique os logs acima para identificar em qual etapa falhou.")
else:
    print(f"\nSUCESSO: {len(df)} linhas carregadas")
    print(f"Colunas: {list(df.columns)}")
    print(f"\nPrimeiras 5 linhas:")
    print(df.head(5).to_string())
    print(f"\nOPs únicas: {df['OP'].nunique() if 'OP' in df.columns else 'coluna OP ausente'}")
    if "OP" in df.columns:
        print(f"Amostra de OPs: {sorted(df['OP'].unique())[:10]}")
    if "QUANT" in df.columns:
        print(f"QUANT total: {df['QUANT'].sum():,}")
