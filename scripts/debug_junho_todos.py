"""Mostra TODOS os rows de JUNHO (com e sem data) para achar o gap de R$60K."""
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

url = f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=JUNHO"
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=20) as r:
    raw = r.read().decode("utf-8", errors="replace")
rows = list(csv.reader(io.StringIO(raw)))

print(f"JUNHO - {len(rows)} linhas\n")
print(f"{'ROW':>5}  {'TEM DATA':8}  {'DESTINO':15}  {'C5 (data saida?)':22}  {'C6 (frete?)':14}  {'C7 (obs?)'}")
print("-"*110)

for i, row in enumerate(rows):
    if len(row) < 3: continue
    data_carga = _parse_date_pt(row[1]) if len(row)>1 else None
    c0 = row[0].strip()[:20] if len(row)>0 else ""
    c1 = row[1].strip()[:30] if len(row)>1 else ""
    c2 = row[2].strip()[:14] if len(row)>2 else ""
    c5 = row[5].strip()[:20] if len(row)>5 else ""
    c6 = row[6].strip()[:13] if len(row)>6 else ""
    c7 = row[7].strip()[:20] if len(row)>7 else ""

    # Só mostra rows que têm algum R$ OU que têm data OU que estão entre rows com data
    tem_money = any(_parse_money(row[j]) for j in range(min(10, len(row))))
    if not data_carga and not tem_money:
        continue  # pula completamente vazias

    marcador = "DATA    " if data_carga else "        "
    print(f"  [{i:03d}]  {marcador}  {c2:15}  {c5:22}  {c6:13}  {c7}")
    if not data_carga and tem_money:
        # Mostrar todos os R$ desta linha
        money = [(j, row[j].strip()) for j in range(min(12, len(row))) if _parse_money(row[j])]
        print(f"          *** NAO-CARGO com R$: {money}")
