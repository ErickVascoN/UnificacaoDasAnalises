import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests
import io

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url_csv = (
    f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
    f"/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"
)

r = requests.get(url_csv, timeout=40)
df = pd.read_csv(io.StringIO(r.content.decode("utf-8")), header=0, dtype=str)
df.columns = [c.strip() if isinstance(c, str) else f"COL_{i}" for i, c in enumerate(df.columns)]

print("Análise de cada coluna:")
print("=" * 80)

for i, col in enumerate(df.columns[:12]):
    sample = df[col].dropna().head(5).tolist()
    print(f"\nColuna [{i}]: '{col}'")
    print(f"  Amostra: {sample}")
    
    # Testa cada padrão
    has_slash_date = any('/' in str(v) and len(str(v)) >= 8 for v in sample)
    has_dash_date = any('-' in str(v) and len(str(v)) >= 8 for v in sample)
    has_digits = any(str(v).isdigit() for v in sample)
    
    print(f"  Padrões: slash_date={has_slash_date}, dash_date={has_dash_date}, digits={has_digits}")
    
    if has_slash_date:
        print(f"  ✓ PARECE SER DATA")
