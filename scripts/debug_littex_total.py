import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import get_raw, invalidate
import pandas as pd
from datetime import date

SHEET_ID = "1wpCdsgLVv_R14yDkak6OMwXKJjUbvL9p"
GID      = "1697720285"

invalidate(SHEET_ID, GID)
conteudo = get_raw(SHEET_ID, GID, ttl=0)
raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
raw.columns = [str(c).strip() for c in raw.columns]

col_qtd  = "TOTAL CONFERIDO"
col_data = "DATA"

qtd_num = pd.to_numeric(
    raw[col_qtd].astype(str)
       .str.replace(".", "", regex=False)
       .str.replace(",", ".", regex=False),
    errors="coerce"
)

print(f"Total linhas no CSV  : {len(raw)}")
print(f"Linhas com quantidade: {qtd_num.notna().sum()}")
print(f"Soma TOTAL geral     : {qtd_num.sum():.0f}")

# Soma por semana
from utils.date_parser import parse_date_series
datas = parse_date_series(raw[col_data])

print("\nSoma por semana (todas):")
raw2 = raw.copy()
raw2["_DATA"] = datas
raw2["_QTD"]  = qtd_num
raw2 = raw2.dropna(subset=["_DATA"])
raw2["_SEG"] = raw2["_DATA"].dt.to_period("W-SUN").dt.start_time.dt.date

for seg, grp in sorted(raw2.groupby("_SEG")):
    from datetime import timedelta
    dom  = seg + timedelta(days=6)
    soma = grp["_QTD"].sum()
    n    = len(grp)
    print(f"  {str(seg)} a {str(dom)} : {n:>3} linhas | {soma:>7.0f} pcs")
