import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import get_raw, invalidate
import pandas as pd
from datetime import date

SEGUNDA = date(2026, 5, 25)
DOMINGO = date(2026, 5, 31)

# Testa varios GIDs para o mesmo spreadsheet
SHEET_ID = "1wpCdsgLVv_R14yDkak6OMwXKJjUbvL9p"
GIDS_TESTE = ["0", "1697720285", "1", "2", "3"]

for gid in GIDS_TESTE:
    invalidate(SHEET_ID, gid)
    conteudo = get_raw(SHEET_ID, gid, ttl=0)
    if not conteudo or not conteudo.strip():
        print(f"GID {gid:>15} -> sem dados")
        continue

    try:
        raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
        raw.columns = [str(c).strip() for c in raw.columns]
        col_qtd  = next((c for c in raw.columns if "CONFERIDO" in c.upper() or "PRODUZIDO" in c.upper()), None)
        col_data = next((c for c in raw.columns if c.upper() == "DATA"), None)

        soma_semana = 0
        linhas_semana = 0
        if col_data and col_qtd:
            from utils.date_parser import parse_date_series
            datas = parse_date_series(raw[col_data])
            mask  = (datas.dt.date >= SEGUNDA) & (datas.dt.date <= DOMINGO)
            linhas_semana = int(mask.sum())
            soma_semana = int(pd.to_numeric(
                raw.loc[mask, col_qtd].astype(str)
                   .str.replace(".", "", regex=False)
                   .str.replace(",", ".", regex=False),
                errors="coerce"
            ).sum())

        print(f"GID {gid:>15} -> {len(raw):>5} linhas | semana: {linhas_semana} linhas / {soma_semana} pcs | cols: {list(raw.columns)[:5]}")
    except Exception as e:
        print(f"GID {gid:>15} -> ERRO: {e}")
