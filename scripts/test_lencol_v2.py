"""
Script de diagnóstico 2: testa parsing corrigido de Lençol.
"""

import requests
import io
import pandas as pd
from datetime import datetime

LENCOL_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_GID = "1396046910"

print("=" * 80)
print("TESTE DE LENÇOL — Parsing Corrigido")
print("=" * 80)

# Pega CSV via gviz/tq
url_csv_gviz = f"https://docs.google.com/spreadsheets/d/{LENCOL_ID}/gviz/tq?tqx=out:csv&gid={LENCOL_GID}"

print("\n[1] Baixando CSV via gviz/tq...")
try:
    r = requests.get(url_csv_gviz, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    print(f"✓ Status: {r.status_code}")
    texto = r.content.decode("utf-8")
    print(f"✓ Tamanho: {len(texto)} caracteres")
except Exception as e:
    print(f"✗ Erro: {e}")
    exit(1)

# Lê sem atribuir nomes de cabeçalho
print("\n[2] Parsing com atribuição por POSIÇÃO...")
df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
print(f"Colunas originais ({len(df.columns)}): {df.columns.tolist()[:15]}")

# Normaliza nomes
df.columns = [c.strip() for c in df.columns]

# Pega primeiras 11
expected_cols = [
    "DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA",
    "TECIDO", "VALOR_PECA", "QUANT", "VALOR_RECEBER", "RETALHO_KG", "OBS",
]
n_cols = min(11, len(df.columns))
df = df.iloc[:, :n_cols].copy()
df.columns = expected_cols[:n_cols]

print(f"Colunas após mapeamento: {df.columns.tolist()}")
print(f"Formato: {len(df)} linhas × {len(df.columns)} colunas")

# Remove vazias
df = df[(df.notna().sum(axis=1) > 1)].copy().reset_index(drop=True)
print(f"Após remover vazias: {len(df)} linhas")

# Trata datas (gviz usa M/D/YYYY)
print("\n[3] Processando datas (dayfirst=False para gviz M/D/YYYY)...")
raw_dates = df["DATA"].astype(str).str.split(" ").str[0].str.strip()
try:
    df["DATA"] = pd.to_datetime(raw_dates, format="mixed", dayfirst=False, errors="coerce")
except TypeError:
    df["DATA"] = pd.to_datetime(raw_dates, dayfirst=False, errors="coerce")

df = df[df["DATA"].notna()].copy()
print(f"Após parse de datas: {len(df)} linhas")
print(f"Intervalo de datas: {df['DATA'].min()} até {df['DATA'].max()}")

# Trata números
print("\n[4] Processando números...")
for col in ("QUANT", "VALOR_PECA", "VALOR_RECEBER", "RETALHO_KG"):
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str)
                   .str.replace("R$", "", regex=False)
                   .str.strip()
                   .str.replace(".", "", regex=False)
                   .str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)
        df[col] = df[col].astype(float)

print("✓ Conversão concluída")

print("\n[5] Amostra de dados:")
print(df[["DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA", "QUANT"]].head(10).to_string())

print("\n[6] Estatísticas:")
print(f"Total de linhas: {len(df)}")
print(f"Total de OPs: {df['OP'].nunique()}")
print(f"Total de peças (QUANT): {df['QUANT'].sum():,.0f}")
print(f"Prestadores: {df['PRESTADOR'].nunique()}")
print(f"Empresas: {df['EMPRESA'].nunique()}")

print("\n" + "=" * 80)
print("✓ PARSING CORRIGIDO FUNCIONANDO!")
print("=" * 80)
