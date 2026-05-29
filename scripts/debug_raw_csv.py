"""
Debug: Ver a estrutura exata do CSV (sem parse)
"""
import requests

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
print(f"Total de linhas: {len(linhas)}\n")

print("="*120)
print("Primeiras 5 linhas RAW (completas):")
print("="*120)
for i in range(min(5, len(linhas))):
    print(f"\nLinha {i}:")
    print(linhas[i])
    print(f"  Comprimento: {len(linhas[i])}")
    
    # Split por vírgula
    partes = linhas[i].split('","')
    print(f"  Campos: {len(partes)}")
    for j, parte in enumerate(partes[:8]):
        print(f"    [{j}] {parte[:80]}")
