"""Busca linhas com 'GERAL' ou totais mensais em cada aba."""
import io, re, csv, unicodedata, urllib.parse, urllib.request
from datetime import date

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
MESES = [
    ("JANEIRO", 1), ("FEVEREIRO", 2), ("MARÇO", 3),
    ("ABRIL", 4), ("MAIO", 5), ("JUNHO", 6),
]
MESES_PT = {
    "janeiro":1,"fevereiro":2,"marco":3,"março":3,
    "abril":4,"maio":5,"junho":6,
}

def _norm(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii","ignore").decode().upper().strip()

def _parse_date_pt(s):
    s = str(s).lower().strip()
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", s)
    if not m: return None
    month = MESES_PT.get(m.group(2))
    return bool(month)

def _fetch_csv(sheet_name):
    nome_enc = urllib.parse.quote(sheet_name)
    url = (f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&sheet={nome_enc}")
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(raw)))

def has_money(s): return "R$" in str(s)

for mes_nome, mes_num in MESES:
    try:
        rows = _fetch_csv(mes_nome)
    except Exception as e:
        print(f"\n{mes_nome}: ERRO - {e}")
        continue

    print(f"\n{'='*60}")
    print(f"  {mes_nome}  ({len(rows)} linhas no total)")
    print(f"{'='*60}")

    # Linhas com 'GERAL' ou grandes totais no final
    found = []
    for i, row in enumerate(rows):
        row_str = " ".join(row)
        if "GERAL" in _norm(row_str) or "TOTAL" in _norm(row_str):
            found.append((i, row))

    # Também mostrar as últimas 15 linhas não-vazias
    non_empty = [(i, row) for i, row in enumerate(rows)
                 if any(c.strip() for c in row)]
    last_rows = non_empty[-15:]

    print("  Linhas com 'GERAL' ou 'TOTAL':")
    for i, row in found[:10]:
        money_cols = [(j,row[j]) for j in range(len(row)) if has_money(row[j])]
        text_cols  = [(j,row[j]) for j in range(min(15,len(row))) if row[j].strip() and not has_money(row[j])]
        print(f"    row[{i:03d}]  texts={text_cols[:4]}  money={money_cols[:6]}")

    print("  Últimas 15 linhas não-vazias:")
    for i, row in last_rows:
        money_cols = [(j,row[j]) for j in range(len(row)) if has_money(row[j])]
        text_cols  = [(j,row[j]) for j in range(min(15,len(row))) if row[j].strip() and not has_money(row[j]) and not _parse_date_pt(row[j])]
        if money_cols or text_cols:
            print(f"    row[{i:03d}]  texts={text_cols[:3]}  money={money_cols[:5]}")
