import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import get_raw, invalidate
import pandas as pd
from datetime import date, timedelta

SEGUNDA = date(2026, 5, 25)
DOMINGO = date(2026, 5, 31)

FONTES = {
    "PRODUCAO_INTERNO (atual)": ("1wpCdsgLVv_R14yDkak6OMwXKJjUbvL9p", "1697720285"),
    "LITEX_GERAL             ": ("1SF2ZumsloWdUVAMt1SRYd1o5gNIY9RXD", "1697720285"),
}

for nome, (sheet_id, gid) in FONTES.items():
    invalidate(sheet_id, gid)
    conteudo = get_raw(sheet_id, gid, ttl=0)
    if not conteudo:
        print(f"{nome} -> FALHOU (sem conteudo)")
        continue
    raw = pd.read_csv(io.StringIO(conteudo), header=0, dtype=str)
    raw.columns = [str(c).strip() for c in raw.columns]
    print(f"\n{nome}")
    print(f"  Linhas totais : {len(raw)}")
    print(f"  Colunas       : {list(raw.columns)[:10]}")

    # tenta detectar coluna de data e quantidade
    col_data = next((c for c in raw.columns if c.upper() in ("DATA", "DATA PRODUCAO", "DATA PRODUÇÃO")), None)
    col_qtd  = next((c for c in raw.columns if "CONFERIDO" in c.upper() or "PRODUZIDO" in c.upper()), None)

    if col_data and col_qtd:
        from utils.date_parser import parse_date_series
        datas = parse_date_series(raw[col_data])
        mask  = (datas.dt.date >= SEGUNDA) & (datas.dt.date <= DOMINGO)
        qtd_semana = pd.to_numeric(
            raw.loc[mask, col_qtd].astype(str)
               .str.replace(".", "", regex=False)
               .str.replace(",", ".", regex=False),
            errors="coerce"
        ).sum()
        print(f"  Linhas semana : {mask.sum()}")
        print(f"  Soma semana   : {qtd_semana:.0f}")
    else:
        print(f"  col_data={col_data} | col_qtd={col_qtd}")
