"""
Diagnóstico: OPs 81 e 82 no dia 27/05 não aparecem no dashboard Lençol.
Vai baixar o CSV e mostrar se os dados estão sendo carregados corretamente.
"""

import requests
import io
import pandas as pd
from datetime import datetime

# URLs de download (mesmas do dashboard)
LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"

_URLS = [
    (
        f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
        f"/gviz/tq?tqx=out:csv&gid={LENCOL_SPREADSHEET_GID}",
        False,   # dayfirst=False → M/D/YYYY
    ),
    (
        f"https://docs.google.com/spreadsheets/d/{LENCOL_SPREADSHEET_ID}"
        f"/export?format=csv&gid={LENCOL_SPREADSHEET_GID}",
        True,    # dayfirst=True → DD/MM/YYYY (locale PT-BR)
    ),
]

print("=" * 80)
print("DIAGNÓSTICO: OPs 81 e 82 em 27/05")
print("=" * 80)

texto = None
dayfirst = False
url_usado = None

for url, df_flag in _URLS:
    try:
        print(f"\n🔄 Tentando: {url[:80]}...")
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        conteudo = r.content.decode("utf-8")
        if conteudo.strip():
            texto = conteudo
            dayfirst = df_flag
            url_usado = url
            print(f"✓ Sucesso! ({len(conteudo)} bytes)")
            break
    except Exception as e:
        print(f"✗ Falhou: {str(e)[:60]}")

if not texto:
    print("❌ Não conseguiu baixar CSV de nenhuma URL!")
    exit(1)

# Lê CSV
df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
print(f"\n📊 Dados brutos: {len(df)} linhas, {len(df.columns)} colunas")
print(f"URL usado (dayfirst={dayfirst}): {'gviz' if not dayfirst else 'export'}")

# Normaliza colunas
df.columns = [c.strip() for c in df.columns]
cols_useful = [c for c in df.columns if c and c.strip()][:11]
df = df[cols_useful].copy().iloc[:, :11]

expected_cols = [
    "DATA", "PRESTADOR", "OP", "CATEGORIA", "EMPRESA",
    "TECIDO", "VALOR_PECA", "QUANT", "VALOR_RECEBER", "RETALHO_KG", "OBS",
]
df.columns = expected_cols[:len(df.columns)]

print(f"📋 Após normalização: {len(df)} linhas")

# Remove vazias
df_antes = len(df)
df = df[(df.notna().sum(axis=1) > 1)].copy().reset_index(drop=True)
print(f"🗑️  Após remover vazias: {len(df)} linhas (-{df_antes - len(df)})")

# Procura OPs 81 e 82 ANTES de converter datas
print("\n🔍 PROCURANDO OPs 81 e 82 (antes conversão de datas):")
for op_num in ["81", "82"]:
    matches = df[df["OP"].astype(str).str.strip() == op_num]
    if not matches.empty:
        print(f"\n✓ OP {op_num} encontrada ({len(matches)} linha(s)):")
        for idx, row in matches.iterrows():
            print(f"  → DATA: '{row['DATA']}' | PRESTADOR: '{row['PRESTADOR']}' | QUANT: '{row['QUANT']}'")
    else:
        print(f"\n✗ OP {op_num} NÃO encontrada no CSV")

# Converte datas
print(f"\n📅 Convertendo datas (dayfirst={dayfirst})...")
raw_dates = df["DATA"].astype(str).str.split(" ").str[0].str.strip()
try:
    df["DATA"] = pd.to_datetime(raw_dates, format="mixed", dayfirst=dayfirst, errors="coerce")
except TypeError:
    df["DATA"] = pd.to_datetime(raw_dates, dayfirst=dayfirst, errors="coerce")

# Procura OPs 81 e 82 no dia 27/05
print("\n🔍 PROCURANDO OPs 81 e 82 no dia 27/05 (após conversão):")
df_27_05 = df[df["DATA"].dt.strftime("%d/%m") == "27/05"]
print(f"📊 Linhas com data 27/05: {len(df_27_05)}")

for op_num in ["81", "82"]:
    matches = df_27_05[df_27_05["OP"].astype(str).str.strip() == op_num]
    if not matches.empty:
        print(f"\n✓ OP {op_num} em 27/05 encontrada ({len(matches)} linha(s)):")
        for idx, row in matches.iterrows():
            print(f"  → DATA: {row['DATA']} | PRESTADOR: {row['PRESTADOR']} | QUANT: {row['QUANT']} | CATEGORIA: {row['CATEGORIA']}")
    else:
        print(f"\n✗ OP {op_num} NÃO encontrada em 27/05")

# Remove inválidas (como faz o dashboard)
print(f"\n🗑️  Aplicando filtros do dashboard...")
df_antes = len(df)
df = df[df["DATA"].notna()]
print(f"  Após remover DATA inválida: {len(df)} linhas")

invalidos = {"", "NAN", "NONE", "N/A", "NAO", "NAO INFORMADO"}
df_antes = len(df)
df = df[~df["PRESTADOR"].str.upper().isin(invalidos)]
print(f"  Após remover PRESTADOR inválido: {len(df)} linhas")

# Procura OPs FINAIS
print("\n✅ RESULTADO FINAL (após todos os filtros do dashboard):")
for op_num in ["81", "82"]:
    matches = df[df["OP"].astype(str).str.strip() == op_num]
    final_matches_27_05 = matches[matches["DATA"].dt.strftime("%d/%m") == "27/05"]
    if not final_matches_27_05.empty:
        print(f"\n✓ OP {op_num} em 27/05: APARECE ({len(final_matches_27_05)} linha(s))")
        for idx, row in final_matches_27_05.iterrows():
            print(f"  → {row['DATA'].strftime('%d/%m/%Y')} | {row['PRESTADOR']} | {row['QUANT']} pç | {row['CATEGORIA']}")
    else:
        print(f"\n✗ OP {op_num} em 27/05: NÃO APARECE (removida durante limpeza)")

print("\n" + "=" * 80)
