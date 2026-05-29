"""
Debug: Verificar parsing de datas do CSV
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

linhas = conteudo.splitlines()
print(f"Total de linhas: {len(linhas)}")
print(f"Linha 0: {linhas[0][:100]}")
print(f"Linha 1: {linhas[1][:100]}")

# Pula título
skiprows = 0
if "CONTROLE" in linhas[0].upper():
    skiprows = 1

print(f"\nPulando {skiprows} linhas")

df = pd.read_csv(io.StringIO(conteudo), skiprows=skiprows, header=0, dtype=str)

print(f"\nColunas: {list(df.columns)}")
print(f"Total de linhas: {len(df)}")

# Normaliza
df.columns = [c.strip().upper() if isinstance(c, str) else f"COL_{i}" 
              for i, c in enumerate(df.columns)]

print(f"\nColunas normalizadas: {list(df.columns)}")

# Procura DATA
for col in df.columns:
    if "DATA" in str(col).upper():
        print(f"\nColuna DATA: '{col}'")
        print(f"Primeiros valores: {df[col].head(5).tolist()}")
        
        # Tenta parsear
        datas = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        print(f"Após parse: {datas.head(5).tolist()}")
        print(f"Válidas: {datas.notna().sum()}/{len(datas)}")
        break
