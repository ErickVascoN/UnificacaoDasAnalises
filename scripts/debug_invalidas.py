"""
Debug: Ver quais valores NÃO estão sendo parseados como data
"""
import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url_csv = (
    f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
    f"/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"
)

print("Baixando CSV...")
r = requests.get(url_csv, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
conteudo = r.content.decode("utf-8")

df = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
df.columns = [c.strip() if isinstance(c, str) else f"COL_{i}" 
              for i, c in enumerate(df.columns)]

col_data = 'CONTROLE DE CORTE DIÁRIO LENÇOL DATA'
parsed = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

print(f"Total: {len(df)}")
print(f"Datas válidas: {parsed.notna().sum()}")
print(f"Datas inválidas: {parsed.isna().sum()}")

print(f"\nExemplos de valores NÃO parseados (inválidos):")
invalidos = df[parsed.isna()][col_data].unique()
for i, val in enumerate(invalidos[:15]):
    print(f"  {i+1}. '{val}'")
