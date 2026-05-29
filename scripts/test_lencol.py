"""
Script de diagnóstico: testa carregamento de dados do Lençol.
Verifica ambas as estratégias (XLSX e CSV via gviz/tq).
"""

import requests
import io
import pandas as pd

LENCOL_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_GID = "1396046910"

print("=" * 80)
print("TESTE DE LENÇOL — Diagnóstico de Carregamento")
print("=" * 80)

# ─ Teste 1: XLSX ─
print("\n[1] Tentando XLSX...")
url_xlsx = f"https://docs.google.com/spreadsheets/d/{LENCOL_ID}/export?format=xlsx"
try:
    r = requests.get(url_xlsx, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    print(f"✓ Status: {r.status_code}")
    print(f"✓ Tamanho: {len(r.content)} bytes")
    
    # Tenta ler o XLSX
    try:
        xls = pd.ExcelFile(io.BytesIO(r.content))
        print(f"✓ Abas encontradas: {xls.sheet_names}")
        
        # Lê primeira aba
        df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, dtype=str)
        print(f"✓ Primeira aba: {len(df)} linhas × {len(df.columns)} colunas")
        print(f"  Colunas: {df.columns.tolist()}")
        print(f"  Primeiras 3 linhas:")
        print(df.head(3).to_string())
    except Exception as e:
        print(f"✗ Erro ao ler XLSX: {e}")
except Exception as e:
    print(f"✗ Erro ao baixar XLSX: {e}")

# ─ Teste 2: CSV via gviz/tq ─
print("\n[2] Tentando CSV via gviz/tq...")
url_csv_gviz = f"https://docs.google.com/spreadsheets/d/{LENCOL_ID}/gviz/tq?tqx=out:csv&gid={LENCOL_GID}"
try:
    r = requests.get(url_csv_gviz, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    print(f"✓ Status: {r.status_code}")
    conteudo = r.content.decode("utf-8")
    print(f"✓ Tamanho: {len(conteudo)} caracteres")
    
    # Tenta ler o CSV
    try:
        df = pd.read_csv(io.StringIO(conteudo), dtype=str)
        print(f"✓ Dados: {len(df)} linhas × {len(df.columns)} colunas")
        print(f"  Colunas: {df.columns.tolist()}")
        print(f"  Primeiras 3 linhas:")
        print(df.head(3).to_string())
    except Exception as e:
        print(f"✗ Erro ao ler CSV: {e}")
except Exception as e:
    print(f"✗ Erro ao baixar CSV via gviz: {e}")

# ─ Teste 3: CSV via /export ─
print("\n[3] Tentando CSV via /export...")
url_csv_export = f"https://docs.google.com/spreadsheets/d/{LENCOL_ID}/export?format=csv&gid={LENCOL_GID}"
try:
    r = requests.get(url_csv_export, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    print(f"✓ Status: {r.status_code}")
    conteudo = r.content.decode("utf-8")
    print(f"✓ Tamanho: {len(conteudo)} caracteres")
    
    # Tenta ler o CSV
    try:
        df = pd.read_csv(io.StringIO(conteudo), dtype=str)
        print(f"✓ Dados: {len(df)} linhas × {len(df.columns)} colunas")
        print(f"  Colunas: {df.columns.tolist()}")
        print(f"  Primeiras 3 linhas:")
        print(df.head(3).to_string())
    except Exception as e:
        print(f"✗ Erro ao ler CSV: {e}")
except Exception as e:
    print(f"✗ Erro ao baixar CSV via export: {e}")

print("\n" + "=" * 80)
print("FIM DO DIAGNÓSTICO")
print("=" * 80)
