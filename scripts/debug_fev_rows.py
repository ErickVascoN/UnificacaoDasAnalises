"""Mostra col[1] (data?) de cada linha de FEV rows[100-127] para confirmar quais têm data."""
import io, re, csv, unicodedata, urllib.parse, urllib.request
from datetime import date

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
MESES_PT = {
    "janeiro":1,"fevereiro":2,"marco":3,"abril":4,
    "maio":5,"junho":6,"julho":7,"agosto":8,
}

def _parse_date_pt(s):
    s = str(s).lower().strip()
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", s)
    if not m: return None
    month = MESES_PT.get(m.group(2))
    if not month: return None
    try: return date(int(m.group(4)), month, int(m.group(3)))
    except ValueError: return None

def _parse_money(s):
    s = str(s).strip()
    if not s or "R$" not in s: return None
    clean = re.sub(r"[R$\s\-]","",s).replace(".","").replace(",",".")
    try: return abs(float(clean))
    except: return None

url = (f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}"
       f"/gviz/tq?tqx=out:csv&sheet=FEVEREIRO")
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=20) as r:
    raw = r.read().decode("utf-8", errors="replace")
rows = list(csv.reader(io.StringIO(raw)))

print(f"FEVEREIRO - {len(rows)} linhas totais")
print(f"{'ROW':>5}  {'TEM DATA':8}  COL[1][:40]         COL[6]             COL[9]             COL[10]")
print("-"*120)

for i in range(100, min(128, len(rows))):
    row = rows[i]
    col1 = row[1].strip() if len(row)>1 else ""
    col4 = row[4].strip() if len(row)>4 else ""
    col6 = row[6].strip() if len(row)>6 else ""
    col9 = row[9].strip() if len(row)>9 else ""
    col10 = row[10].strip() if len(row)>10 else ""
    has_date = bool(_parse_date_pt(col1))
    m6 = _parse_money(col6) or 0
    m9 = _parse_money(col9) or 0
    m10 = _parse_money(col10) or 0
    label = f"col4={col4}" if col4 else ""
    print(f"  [{i:03d}]  {'DATA':8}" if has_date else f"  [{i:03d}]  {'':8}", end="")
    print(f"  {col1[:35]:35s}  {m6:>12,.0f}  {m9:>12,.0f}  {m10:>12,.0f}  {label}")
