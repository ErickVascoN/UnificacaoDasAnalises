import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import get_raw
from config.settings import PRODUCAO_INTERNO_SHEETS
import pandas as pd
from datetime import date, timedelta

cfg = PRODUCAO_INTERNO_SHEETS["LITTEX"]
conteudo = get_raw(cfg["id"], cfg["gid"], ttl=300)
raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
raw.columns = [str(c).strip() for c in raw.columns]

# Semana 25-31 Mai
SEGUNDA = date(2026, 5, 25)
DOMINGO = date(2026, 5, 31)

# Identifica colunas relevantes
col_data  = next((c for c in raw.columns if "DATA" in c.upper()), None)
col_qtd   = next((c for c in raw.columns if "TOTAL CONFERIDO" in c.upper() or "TOTAL PRODUZIDO" in c.upper()), None)
col_prod  = next((c for c in raw.columns if c.upper() == "PRODUTO"), None)
col_cli   = next((c for c in raw.columns if "CLIENTE" in c.upper()), None)
col_descr = next((c for c in raw.columns if "DESCRI" in c.upper()), None)
col_colab = next((c for c in raw.columns if "PRESTADOR" in c.upper() or "COLABORADOR" in c.upper()), None)

print(f"col_data={col_data} | col_qtd={col_qtd} | col_prod={col_prod} | col_cli={col_cli}")
print(f"col_descr={col_descr} | col_colab={col_colab}")
print(f"\nTotal linhas brutas: {len(raw)}")

# Filtra pela semana
from utils.date_parser import parse_date_series
datas = parse_date_series(raw[col_data])
mask = (datas.dt.date >= SEGUNDA) & (datas.dt.date <= DOMINGO)
raw_semana = raw[mask].copy()
print(f"Linhas na semana 25-31 Mai: {len(raw_semana)}")

# Mostra todas as linhas da semana com colunas relevantes
cols_show = [c for c in [col_data, col_colab, col_prod, col_descr, col_cli, col_qtd] if c]
print("\nDados brutos da semana:")
print(raw_semana[cols_show].to_string(index=True))

print(f"\nTotal CONFERIDO bruto na semana: {pd.to_numeric(raw_semana[col_qtd].str.replace('.','').str.replace(',','.'), errors='coerce').sum()}")
