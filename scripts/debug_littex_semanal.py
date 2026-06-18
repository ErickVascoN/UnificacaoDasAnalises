import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.producao_interno_loader import load_interno_unidade
from datetime import date, timedelta

df = load_interno_unidade("LITTEX")
print(f"Total linhas carregadas: {len(df)}")

if df.empty:
    print("DataFrame vazio — checar planilha ou conexao.")
    sys.exit()

print(f"Periodo: {df['DATA'].min().date()} ate {df['DATA'].max().date()}")
print(f"Colunas: {list(df.columns)}")
print(f"Produtos unicos: {sorted(df['PRODUTO'].dropna().unique())[:15]}")
print(f"Clientes unicos: {sorted(df['CLIENTE'].dropna().unique())[:10]}")

hoje = date.today()
print(f"\nHoje: {hoje}")

for w in range(5):
    segunda = hoje - timedelta(days=hoje.weekday()) - timedelta(weeks=w)
    domingo = segunda + timedelta(days=6)
    n = int(((df["DATA"].dt.date >= segunda) & (df["DATA"].dt.date <= domingo)).sum())
    qtd = int(df.loc[(df["DATA"].dt.date >= segunda) & (df["DATA"].dt.date <= domingo), "QUANTIDADE"].sum())
    label = "<<< SEMANA ATUAL" if w == 0 else ""
    print(f"  Semana -{w} ({segunda} a {domingo}): {n} linhas | {qtd} pecas {label}")
