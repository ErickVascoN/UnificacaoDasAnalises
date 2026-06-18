"""Inspeciona linhas sem data (candidatas a totais) em cada aba de cargas."""
import io, re, csv, unicodedata, urllib.parse, urllib.request
from datetime import date

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
MESES_DISPONIVEIS = [
    ("JANEIRO",   1, 2026),
    ("FEVEREIRO", 2, 2026),
    ("MARCO",     3, 2026),
    ("ABRIL",     4, 2026),
    ("MAIO",      5, 2026),
    ("JUNHO",     6, 2026),
]
MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

def _norm(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().upper().strip()

def _parse_date_pt(s):
    s = str(s).lower().strip()
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", s)
    if not m:
        return None
    month = MESES_PT.get(m.group(2))
    if not month:
        return None
    try:
        return date(int(m.group(4)), month, int(m.group(3)))
    except ValueError:
        return None

def _fetch_csv(sheet_name):
    nome_enc = urllib.parse.quote(sheet_name)
    url = (
        f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={nome_enc}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(raw)))

def has_money(s):
    return "R$" in str(s)

for mes_nome, mes_num, ano in MESES_DISPONIVEIS:
    try:
        rows = _fetch_csv(mes_nome)
    except Exception as e:
        print(f"\n{mes_nome}: ERRO ao buscar - {e}")
        continue

    print(f"\n{'='*60}")
    print(f"  {mes_nome} - linhas sem data em col[1] (com algum valor)")
    print(f"{'='*60}")
    count = 0
    for i, row in enumerate(rows):
        if len(row) < 4:
            continue
        col1 = row[1] if len(row) > 1 else ""
        if _parse_date_pt(col1):
            continue  # linha de cargo normal
        if "DATA CARREGAMENTO" in _norm(col1):
            continue
        # Mostrar apenas linhas que parecem ter algum valor relevante
        cols_with_content = [j for j, c in enumerate(row) if c.strip() and c.strip() not in ("", '""')]
        if not cols_with_content:
            continue
        # Filtrar linhas muito vazias (menos de 3 colunas preenchidas)
        if len(cols_with_content) < 2:
            continue
        print(f"  row[{i:03d}]:", end="")
        for j in range(min(15, len(row))):
            val = row[j].strip()
            if val:
                print(f"  [{j}]={val!r}", end="")
        print()
        count += 1
        if count >= 30:
            print("  ... (truncado em 30 linhas)")
            break
