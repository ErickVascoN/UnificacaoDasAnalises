"""Mostra cada linha de JUNHO com data: destino, frete capturado e col usada."""
import io, re, csv, unicodedata, urllib.parse, urllib.request
from datetime import date

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
MESES_PT = {"janeiro":1,"fevereiro":2,"marco":3,"março":3,"abril":4,"maio":5,"junho":6,"julho":7}

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

url = (f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=JUNHO")
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=20) as r:
    raw = r.read().decode("utf-8", errors="replace")
rows = list(csv.reader(io.StringIO(raw)))

print(f"JUNHO - {len(rows)} linhas totais\n")
print(f"{'ROW':>5}  {'DESTINO':15}  {'COL':>4}  {'FRETE':>14}  {'C5':20}  {'C6':15}  {'C7'}")
print("-" * 110)

total = 0.0
n_ok = 0
skipped = []

for i, row in enumerate(rows):
    if len(row) < 6: continue
    data_carga = _parse_date_pt(row[1]) if len(row)>1 else None
    if not data_carga: continue

    destino = row[2].strip().upper() if len(row)>2 else ""
    if not destino or destino in ("DESTINO",""):
        skipped.append((i, "destino vazio"))
        continue

    frete, fcol = _first_frete(row)
    c5 = row[5].strip()[:18] if len(row)>5 else ""
    c6 = row[6].strip()[:14] if len(row)>6 else ""
    c7 = row[7].strip()[:20] if len(row)>7 else ""

    if frete > 0:
        total += frete
        n_ok += 1
        print(f"  [{i:03d}]  {destino:15}  col[{fcol}]  R$ {frete:>12,.0f}  {c5:20}  {c6:14}  {c7}")
    else:
        print(f"  [{i:03d}]  {destino:15}  ---     R$ {0:>12,.0f}  {c5:20}  {c6:14}  {c7}  << FRETE ZERO")

print("-" * 110)
print(f"\n  {n_ok} cargos com frete > 0")
print(f"  TOTAL NOSSO: R$ {total:,.0f}")
print(f"  ESPERADO:    R$ 2.510.000")
print(f"  DIFERENCA:   R$ {2510000 - total:,.0f}")
if skipped:
    print(f"\n  Skipped (destino vazio): {skipped}")
