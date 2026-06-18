"""
Abordagem final:
  PREVISTO  = soma dos fretes individuais de cargo (primeiro R$ em cols 5-9)
  REALIZADO = maior valor não-redondo > R$1M entre linhas não-data pós-último-cargo
              (ou col[GERAL+2] quando existe linha 'GERAL')
"""
import io, re, csv, unicodedata, urllib.parse, urllib.request
from datetime import date

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
MESES = [
    ("JANEIRO",   1, 2026),
    ("FEVEREIRO", 2, 2026),
    ("MARÇO",     3, 2026),
    ("ABRIL",     4, 2026),
    ("MAIO",      5, 2026),
    ("JUNHO",     6, 2026),
]
MESES_PT = {
    "janeiro":1,"fevereiro":2,"marco":3,"março":3,
    "abril":4,"maio":5,"junho":6,"julho":7,
    "agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12,
}

def _norm(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii","ignore").decode().upper().strip()

def _parse_money(s):
    s = str(s).strip()
    if not s or "R$" not in s: return None
    neg = s.startswith("-")
    clean = re.sub(r"[R$\s\-]","",s).replace(".","").replace(",",".")
    try:
        v = float(clean)
        return -v if neg else v
    except: return None

def _parse_date_pt(s):
    s = str(s).lower().strip()
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", s)
    if not m: return None
    month = MESES_PT.get(m.group(2))
    if not month: return None
    try: return date(int(m.group(4)), month, int(m.group(3)))
    except: return None

def _fetch_csv(sheet_name):
    nome_enc = urllib.parse.quote(sheet_name)
    url = (f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&sheet={nome_enc}")
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(raw)))

def _first_frete(row):
    """Primeiro R$ positivo em cols 5-9 (col[6] para FEV/MAR/ABR/JUN, col[7] para JAN)."""
    for j in range(5, min(10, len(row))):
        v = _parse_money(row[j])
        if v and abs(v) > 0:
            return abs(v)
    return 0.0

def _find_realizado(rows):
    """
    Encontra o total realizado mensal:
    1. Se existe linha com 'GERAL': retorna col[GERAL+2].
    2. Senão: maior valor não-redondo > R$1M em cols 8-14 de linhas não-data
       que aparecem APÓS o último cargo.
    Fallback: 0.0
    """
    # Detectar linha GERAL (ex: JANEIRO)
    for row in rows:
        if _parse_date_pt(row[1] if len(row)>1 else ""): continue
        for j in range(8, min(15, len(row))):
            if "GERAL" in _norm(row[j]):
                real_col = j + 2  # client=j, previsto=j+1, realizado=j+2
                if len(row) > real_col:
                    v = _parse_money(row[real_col])
                    if v and abs(v) > 1_000_000:
                        return abs(v), f"GERAL col[{real_col}]"
                break

    # Sem GERAL: maior não-redondo > 1M em linhas pós-último-cargo (cols 8-14)
    last_cargo_idx = -1
    for i, row in enumerate(rows):
        if len(row)>1 and _parse_date_pt(row[1]):
            last_cargo_idx = i

    best = 0.0
    best_desc = ""
    for i in range(last_cargo_idx + 1, len(rows)):
        row = rows[i]
        for j in range(8, min(16, len(row))):
            v = _parse_money(row[j])
            if not v: continue
            av = abs(v)
            if av <= 1_000_000: continue
            cents_part = round(av) % 1_000
            if cents_part == 0: continue  # valor redondo = meta/previsto planejado
            if av > best:
                best = av
                best_desc = f"row[{i}] col[{j}]={av:,.0f}"

    return best, best_desc or "não encontrado"

def _parse_month(rows, mes_nome, mes_num, ano):
    # PREVISTO: soma fretes de linhas com data
    cargo_prev = 0.0
    n_cargo = 0
    for row in rows:
        if len(row) < 3: continue
        data_carga = _parse_date_pt(row[1]) if len(row)>1 else None
        if not data_carga: continue
        destino = row[2].strip().upper() if len(row)>2 else ""
        if not destino or "DESTINO" == destino: continue
        frete = _first_frete(row)
        if frete > 0:
            cargo_prev += frete
            n_cargo += 1

    # REALIZADO: linha de resumo mensal
    realizado, real_desc = _find_realizado(rows)

    return cargo_prev, realizado, n_cargo, real_desc

print("PREVISTO = soma fretes cargo | REALIZADO = total mensal (linha-resumo)\n")
grand_prev = grand_real = 0.0

for mes_nome, mes_num, ano in MESES:
    try:
        rows = _fetch_csv(mes_nome)
        prev, real, n_c, real_desc = _parse_month(rows, mes_nome, mes_num, ano)
    except Exception as e:
        print(f"  {mes_nome}: ERRO - {e}")
        continue

    print(f"  {mes_nome}  ({len(rows)} linhas)")
    print(f"    {n_c} cargos  ->  PREVISTO  = R$ {prev:,.0f}")
    print(f"    REALIZADO = R$ {real:,.0f}  [{real_desc}]")
    grand_prev += prev
    grand_real += real
    print()

print("=" * 55)
print(f"TOTAL PREVISTO:  R$ {grand_prev:,.0f}")
print(f"TOTAL REALIZADO: R$ {grand_real:,.0f}")
print()
print("Esperados FEVEREIRO: PREV ~3.653.000  REAL ~3.365.242")
print("Esperados JANEIRO:   PREV ~3.855.000  REAL ~3.377.274")
