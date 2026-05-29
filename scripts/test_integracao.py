import sys
import os

# Adiciona diretório ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pages'))

# Importa o arquivo (importlib para contornar o nome com número)
import importlib.util
spec = importlib.util.spec_from_file_location("prog", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                 'pages', '4_Controladoria_Programacao.py'))
prog_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prog_module)

# Agora posso usar as funções
load_cortes = prog_module.load_cortes
load_programacao = prog_module.load_programacao
enriquecer = prog_module.enriquecer

print("\n" + "="*80)
print("TESTANDO INTEGRAÇÃO: Programação + Cortes (Lençol Carregado)")
print("="*80)

print("\n[1] Carregando cortes...")
df_cortes = load_cortes()
print(f"  ✓ {len(df_cortes)} registros de cortes")
print(f"  OPs únicos em cortes: {df_cortes['OP'].nunique()}")

print("\n[2] Carregando programação...")
df_prog = load_programacao()
print(f"  ✓ {len(df_prog)} registros de programação")

print("\n[3] Enriquecendo dados (join)...")
df_resultado = enriquecer(df_prog, df_cortes)
print(f"  ✓ {len(df_resultado)} registros após enriquecimento")

print("\nPrimeiros OPs com cortes:")
print(df_resultado[['OP', 'PED.CLIENTE', 'SEMANA', 'QNT.PROG', 'QUANTIDADE', 'EFICIENCIA']].head(10).to_string())

print(f"\nOPs com cortes: {df_resultado[df_resultado['QUANTIDADE'] > 0]['OP'].nunique()}")
print(f"Quantidades cortadas: {df_resultado['QUANTIDADE'].sum()}")
print(f"\nOPs cortados: {sorted(df_resultado[df_resultado['QUANTIDADE'] > 0]['OP'].unique()[:15])}")
