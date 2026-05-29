"""
Lista TODAS as OPs que aparecem em 27/05
"""

import requests
import io
import pandas as pd

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

url = f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}"

print("=" * 80)
print("Baixando CSV da planilha de Lençol...")
print("=" * 80)

r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

texto = r.content.decode("utf-8")
df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)

# Normaliza
df.columns = [c.strip() for c in df.columns]
cols_useful = [c for c in df.columns if c and c.strip()][:11]
df = df[cols_useful].copy().iloc[:, :11]

expected_cols = [
    "DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA",
    "TECIDO", "VALOR_PECA", "QUANT", "VALOR_RECEBER", "RETALHO_KG", "OBS",
]
df.columns = expected_cols[:len(df.columns)]

# Remove vazias
df = df[(df.notna().sum(axis=1) > 1)].copy().reset_index(drop=True)

# Converte datas
raw_dates = df["DATA"].astype(str).str.split(" ").str[0].str.strip()
try:
    df["DATA"] = pd.to_datetime(raw_dates, format="mixed", dayfirst=False, errors="coerce")
except TypeError:
    df["DATA"] = pd.to_datetime(raw_dates, dayfirst=False, errors="coerce")

# Remove inválidas
df = df[df["DATA"].notna()]

# Filtra por 27/05 (qualquer ano)
df_27_05 = df[df["DATA"].dt.strftime("%d/%m") == "27/05"]

print(f"\n📊 Total de registros em 27/05: {len(df_27_05)}")
print(f"\nOPs encontradas em 27/05:")
print("-" * 80)

if df_27_05.empty:
    print("❌ Nenhum registro em 27/05")
else:
    # Agrupa por OP
    ops_27_05 = df_27_05["OP"].astype(str).str.strip().unique()
    print(f"\n{len(ops_27_05)} OPs diferentes:\n")
    
    for op in sorted(ops_27_05):
        matches = df_27_05[df_27_05["OP"].astype(str).str.strip() == op]
        print(f"OP: {op}")
        for idx, row in matches.iterrows():
            print(f"  • {row['DATA'].strftime('%d/%m/%Y')} | {row['PRESTADOR']} | {row['QUANT']} pç | {row['CATEGORIA']} | {row['EMPRESA']}")
        print()

print("=" * 80)
