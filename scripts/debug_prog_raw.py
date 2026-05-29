"""
Debug detalhado: verificar linha por linha como OP está sendo parseada
"""
import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url_gviz = (
    f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
    f"/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"
)

print("Baixando CSV...")
r = requests.get(url_gviz, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
conteudo = r.content.decode("utf-8")

# Pegar as 8 primeiras linhas
linhas = conteudo.splitlines()[:15]
print("Primeiras 15 linhas RAW:\n")
for i, linha in enumerate(linhas):
    print(f"{i:2d}: {linha[:150]}")

# Parse COM header
print("\n" + "="*80)
print("Parse automático com header=0:")
print("="*80)
df = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)

print(f"\nColuna 'OP' (primeiras 20 linhas, dtype={df['OP'].dtype}):")
for i in range(min(20, len(df))):
    op_val = df['OP'].iloc[i]
    op_repr = repr(op_val)
    print(f"  {i:2d}: {op_repr} (tipo: {type(op_val).__name__})")

# Procurar especificamente por "PROG"
print("\n" + "="*80)
print("Linhas que contêm 'PROG' em qualquer coluna:")
print("="*80)

for col in df.columns:
    prog_rows = df[df[col].astype(str).str.contains("PROG", case=False, na=False)]
    if not prog_rows.empty:
        print(f"\nColuna '{col}':")
        for idx, row in prog_rows.iterrows():
            print(f"  Linha {idx}: {row[col]}")
