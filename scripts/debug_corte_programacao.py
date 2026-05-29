"""
Script para debugar por que OPs cortadas no lençol não aparecem na programação.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging
import importlib.util

# Import do arquivo com número no nome
spec = importlib.util.spec_from_file_location(
    "controladoria_prog",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pages", "4_Controladoria_Programacao.py")
)
controladoria = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controladoria)

load_cortes = controladoria.load_cortes
load_programacao = controladoria.load_programacao
enriquecer = controladoria.enriquecer

from utils.lencol_loader_smart import load_lencol_smart_csv

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("🔍 DIAGNÓSTICO: Cortes vs Programação")
print("="*80)

# 1. Carregar dados
print("\n📥 Carregando dados...")
try:
    df_lencol = load_lencol_smart_csv()
    print(f"✓ Lençol: {len(df_lencol)} linhas")
    print(f"  Colunas: {list(df_lencol.columns)}")
    if not df_lencol.empty:
        print(f"  Amostra DATA: {df_lencol['DATA'].iloc[:3].tolist()}")
        print(f"  Amostra OP: {df_lencol['OP'].iloc[:5].tolist()}")
except Exception as e:
    print(f"✗ Erro ao carregar Lençol: {e}")
    df_lencol = pd.DataFrame()

try:
    df_prog = load_programacao()
    print(f"✓ Programação: {len(df_prog)} linhas")
    print(f"  Amostra PED. CLIENTE: {df_prog['PED. CLIENTE'].iloc[:5].tolist()}")
except Exception as e:
    print(f"✗ Erro ao carregar Programação: {e}")
    df_prog = pd.DataFrame()

try:
    df_cortes = load_cortes()
    print(f"✓ Cortes (agregados): {len(df_cortes)} linhas")
    print(f"  Colunas: {list(df_cortes.columns)}")
    if "SEMANA" in df_cortes.columns:
        print(f"  Semanas com valor: {df_cortes['SEMANA'].notna().sum()}")
        print(f"  Semanas únicas: {sorted(df_cortes['SEMANA'].dropna().unique())}")
except Exception as e:
    print(f"✗ Erro ao carregar Cortes: {e}")
    df_cortes = pd.DataFrame()

# 2. Análise: OPs no lençol mas não na programação
print("\n" + "-"*80)
print("🔍 ANÁLISE 1: OPs no Lençol mas não encontradas na Programação")
print("-"*80)

if not df_lencol.empty and not df_prog.empty:
    ops_lencol = set(df_lencol["OP"].astype(str).str.strip().unique())
    ops_prog = set(df_prog["PED. CLIENTE"].astype(str).str.strip().unique())
    
    ops_sem_prog = ops_lencol - ops_prog
    
    if ops_sem_prog:
        print(f"⚠️  {len(ops_sem_prog)} OPs no lençol NÃO estão na programação:")
        for op in sorted(list(ops_sem_prog))[:10]:
            cortada = df_lencol[df_lencol["OP"] == op]["QUANT"].sum()
            print(f"   · OP {op}: {cortada:,.0f} peças cortadas".replace(",", "."))
        if len(ops_sem_prog) > 10:
            print(f"   ... e mais {len(ops_sem_prog)-10}")
    else:
        print("✓ Todas as OPs do lençol estão na programação")

# 3. Análise: Semanas
print("\n" + "-"*80)
print("🔍 ANÁLISE 2: Extração de Semanas")
print("-"*80)

if not df_cortes.empty:
    tem_semana = "SEMANA" in df_cortes.columns and df_cortes["SEMANA"].notna().any()
    print(f"Coluna SEMANA existe: {('SEMANA' in df_cortes.columns)}")
    if "SEMANA" in df_cortes.columns:
        print(f"Valores SEMANA (não-nulos): {df_cortes['SEMANA'].notna().sum()}/{len(df_cortes)}")
        print(f"Semanas encontradas: {sorted(df_cortes['SEMANA'].dropna().unique())}")
    
    # Verificar se lençol tem DATA
    if not df_lencol.empty and "DATA" in df_lencol.columns:
        print(f"\nLençol tem coluna DATA")
        print(f"  Datas com valor: {df_lencol['DATA'].notna().sum()}/{len(df_lencol)}")
        print(f"  Tipos de data (amostra): {df_lencol['DATA'].iloc[:3].tolist()}")

# 4. Análise: OPs no lençol
print("\n" + "-"*80)
print("🔍 ANÁLISE 3: Formato das OPs")
print("-"*80)

if not df_lencol.empty:
    print("Amostra de OPs do lençol (primeiras 10):")
    for i, op in enumerate(df_lencol["OP"].unique()[:10]):
        cortada = df_lencol[df_lencol["OP"] == op]["QUANT"].astype(str).str.replace(".", ",").values
        print(f"  {i+1}. '{op}' (len={len(str(op))}, tipo={type(op).__name__})")

# 5. Cruzamento
print("\n" + "-"*80)
print("🔍 ANÁLISE 4: Cruzamento no enriquecer()")
print("-"*80)

if not df_prog.empty and not df_cortes.empty:
    df_enriched = enriquecer(df_prog, df_cortes)
    
    sem_corte = df_enriched[df_enriched["QNT_CORTADA"] == 0]
    com_corte = df_enriched[df_enriched["QNT_CORTADA"] > 0]
    
    print(f"OPs com CORTE registrado: {len(com_corte)}")
    print(f"OPs SEM corte registrado: {len(sem_corte)}")
    
    # Mostrar algumas OPs que deveriam ter corte mas não têm
    print("\nExemplo de OPs SEM corte registrado:")
    for idx, row in sem_corte.head(5).iterrows():
        ped = row["PED. CLIENTE"]
        sem = row["SEMANA"]
        qnt_prog = row["QNT_PROG_TOTAL"]
        print(f"  · {ped} (semana {sem}): QNT_PROG={qnt_prog}, QNT_CORTADA=0")
        
        # Tentar encontrar essa OP no lençol
        if not df_lencol.empty:
            match = df_lencol[df_lencol["OP"].astype(str).str.strip() == str(ped).strip()]
            if not match.empty:
                total_cortada = match["QUANT"].sum()
                print(f"     ⚠️  MAS encontrada no lençol com {total_cortada:,.0f} peças!".replace(",", "."))
            else:
                print(f"     ✓ Não encontrada no lençol")

print("\n" + "="*80)
print("Fim do diagnóstico")
print("="*80)
