"""Mostra cols 0-15 de linhas de cargo que tiveram frete=0 (nao encontrado em cols 5-9)."""
import io, re, csv, unicodedata, urllib.parse, urllib.request
from datetime import date

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
MESES = [("JANEIRO",1,2026),("FEVEREIRO",2,2026),("MARÇO",3,2026),("ABRIL",4,2026),("MAIO",5,2026),("JUNHO",6,2026)]
MESES_PT = {"janeiro":1,"fevereiro":2,"marco":3,"marco":3,"março":3,"abril":4,"maio":5,"junho":6,"julho":7}

def _parse_money(s):
    s = str(s).strip()
    if not s or "R$" not in s: return None
    clean = re.sub(r"[R$\s\-]","",s).replace(".","").replace(",",".")
    try: return abs(float(clean))
    except: return None

def _parse_date_pt(s):
    s = str(s).lower().strip()
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", s)
    if not m: return None
    month = MESES_PT.get(m.group(2))
    if not month: return None
    try: return date(int(m.group(4)), month, int(m.group(3)))
    except: return None

def _first_frete(row):
    for j in range(5, min(10, len(row))):
        v = _parse_money(row[j])
        if v and abs(v) > 0: return abs(v), j
    return 0.0, -1

def _fetch_csv(sheet_name):
    nome_enc = urllib.parse.quote(sheet_name)
    url = (f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nome_enc}")
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(raw)))

for mes_nome, mes_num, ano in MESES:
    try: rows = _fetch_csv(mes_nome)
    except Exception as e: print(f"{mes_nome}: ERRO {e}"); continue

    frete0_rows = []
    for i, row in enumerate(rows):
        if len(row) < 8: continue
        data_carga = _parse_date_pt(row[1]) if len(row)>1 else None
        if not data_carga: continue
        destino = row[2].strip().upper() if len(row)>2 else ""
        if not destino or destino in ("DESTINO",""): continue
        frete, _ = _first_frete(row)
        if frete == 0.0:
            frete0_rows.append((i, row))

    if not frete0_rows: continue
    print(f"\n{'='*70}")
    print(f"  {mes_nome} - {len(frete0_rows)} cargos sem frete em cols 5-9")
    print(f"{'='*70}")
    for i, row in frete0_rows:
        destino = row[2].strip()[:15] if len(row)>2 else ""
        data_str = row[1].strip()[:25] if len(row)>1 else ""
        # Mostrar todas as colunas com R$
        money_cols = [(j, row[j]) for j in range(len(row)) if _parse_money(row[j])]
        text_cols = [(j, row[j][:20]) for j in range(min(16,len(row))) if row[j].strip() and not _parse_money(row[j]) and j not in (1,2)]
        print(f"  row[{i:03d}] {destino:15s} | {data_str}")
        if money_cols:
            print(f"           R$ em cols: {[(j,row[j][:15]) for j,_ in money_cols]}")
        else:
            print(f"           NENHUM R$ encontrado na linha")
        if text_cols:
            print(f"           texto:  {text_cols[:5]}")
        print()
