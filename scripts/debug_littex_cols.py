import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import get_raw
from config.settings import PRODUCAO_INTERNO_SHEETS
import pandas as pd

cfg = PRODUCAO_INTERNO_SHEETS["LITTEX"]
conteudo = get_raw(cfg["id"], cfg["gid"], ttl=300)
raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
raw.columns = [str(c).strip() for c in raw.columns]

print("Colunas brutas:")
for i, c in enumerate(raw.columns):
    print(f"  [{i}] '{c}'")

print("\nPrimeiras 3 linhas das colunas DESCR*/PROD*/CLIENTE/EMPRESA:")
cols_interest = [c for c in raw.columns if any(k in c.upper() for k in ["DESCR","PROD","CLIEN","EMPRE","FABRIC"])]
if cols_interest:
    print(raw[cols_interest].head(3).to_string())
