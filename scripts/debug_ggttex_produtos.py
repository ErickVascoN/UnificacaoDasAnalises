import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.producao_interno_loader import load_interno_unidade

for chave in ["GGTTEX_JOGOS", "GGTTEX_FRONHA", "GGTTEX_CORTINA"]:
    df = load_interno_unidade(chave)
    if df.empty:
        print(f"{chave}: vazio"); continue
    print(f"\n{'='*50}")
    print(f"{chave}: {len(df)} linhas | {df['DATA'].min().date()} a {df['DATA'].max().date()}")
    print(f"  Produtos : {sorted(df['PRODUTO'].dropna().unique())}")
    print(f"  Clientes : {sorted(df['CLIENTE'].dropna().unique())}")
