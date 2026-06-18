"""
Detalha o que está sendo somado no PREVISTO de cada mês:
  - Quantos cargos foram capturados vs. pulados
  - Fretes de Cancelada/Adiada separados
  - Previsto oficial da planilha (linha GERAL/TOTAL quando existir)
  - Fretes de linhas que TEM data mas foram IGNORADAS (destino vazio, etc.)
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
    return unicodedata.normalize("NFD",str(s)).encode("ascii","ignore").decode().upper().strip()

def _parse_money(s):
    s = str(s).strip()
    if not s or "R$" not in s: return None
    neg = s.startswith("-")
    clean = re.sub(r"[R$\s\-]","",s).replace(".","").replace(",",".")
    try:
        v = float(clean); return -v if neg else v
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
        if v and abs(v) > 0:
            return abs(v), j
    return 0.0, -1

def _fetch_csv(sheet_name):
    nome_enc = urllib.parse.quote(sheet_name)
    url = (f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}"
           f"/gviz/tq?tqx=out:csv&sheet={nome_enc}")
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(raw)))

def _planilha_previsto(rows):
    """Tenta extrair o PREVISTO total da planilha (linha GERAL ou resumo)."""
    # GERAL row: col[j]='GERAL', col[j+1]=previsto
    for row in rows:
        if _parse_date_pt(row[1] if len(row)>1 else ""): continue
        for j in range(8, min(15, len(row))):
            if "GERAL" in _norm(row[j]):
                prev_col = j + 1
                if len(row) > prev_col:
                    v = _parse_money(row[prev_col])
                    if v and abs(v) > 1_000_000:
                        return abs(v), f"GERAL col[{prev_col}]"
    # Maior valor REDONDO > 1M em linhas não-data (seria META ou PREVISTO)
    # Pega o segundo maior redondo (o maior costuma ser META)
    redondos = []
    for row in rows:
        if _parse_date_pt(row[1] if len(row)>1 else ""): continue
        for j in range(8, min(16, len(row))):
            v = _parse_money(row[j])
            if not v: continue
            av = abs(v)
            if av <= 1_000_000: continue
            if round(av) % 1_000 == 0:
                redondos.append((av, f"row col[{j}]={av:,.0f}"))
    redondos.sort(reverse=True)
    return (redondos[1] if len(redondos)>=2 else (0.0, "não encontrado"))

for mes_nome, mes_num, ano in MESES:
    try:
        rows = _fetch_csv(mes_nome)
    except Exception as e:
        print(f"\n{mes_nome}: ERRO - {e}"); continue

    print(f"\n{'='*65}")
    print(f"  {mes_nome}  ({len(rows)} linhas)")
    print(f"{'='*65}")

    prev_total  = 0.0
    prev_normal = 0.0
    prev_cancel = 0.0
    prev_adiada = 0.0
    n_ok = n_skip_dest = n_skip_frete0 = 0
    skipped_rows = []

    for i, row in enumerate(rows):
        if len(row) < 8: continue
        data_carga = _parse_date_pt(row[1]) if len(row)>1 else None
        if not data_carga: continue

        destino = row[2].strip().upper() if len(row)>2 else ""
        if not destino or destino in ("DESTINO",""):
            skipped_rows.append((i, "destino vazio", row[1][:30]))
            n_skip_dest += 1
            continue

        frete, fcol = _first_frete(row)

        # Status
        status = "Normal"
        for cell in row[6:15]:
            v = cell.strip().upper()
            if not v or "R$" in v: continue
            if "CANCEL" in v: status="Cancelada"; break
            if any(k in v for k in ["ADIAD","ADIADO","ADIADA"]): status="Adiada"; break
            if "ARMAZENAGEM" in v: status="Armazenagem"; break

        if frete == 0.0:
            skipped_rows.append((i, f"frete=0 (col buscado={fcol})", f"{destino[:20]} / {row[1][:20]}"))
            n_skip_frete0 += 1
        else:
            prev_total += frete
            if status in ("Normal","Armazenagem"): prev_normal += frete
            elif status == "Cancelada": prev_cancel += frete
            elif status == "Adiada":   prev_adiada += frete
            n_ok += 1

    # Previsto da planilha (linha de resumo)
    pl_prev, pl_desc = _planilha_previsto(rows)

    print(f"  Cargos capturados : {n_ok:3d}  ->  PREVISTO total  = R$ {prev_total:>12,.0f}")
    print(f"  +-- Normal/Armaz. :       ->  R$ {prev_normal:>12,.0f}")
    print(f"  +-- Canceladas    :       ->  R$ {prev_cancel:>12,.0f}")
    print(f"  +-- Adiadas       :       ->  R$ {prev_adiada:>12,.0f}")
    print(f"  Skipped destino=0 : {n_skip_dest}")
    print(f"  Skipped frete=0   : {n_skip_frete0}")
    if skipped_rows:
        for ri, reason, info in skipped_rows[:8]:
            print(f"      row[{ri:03d}] {reason}  |  {info}")
    print(f"  Planilha PREVISTO : R$ {pl_prev:>12,.0f}  [{pl_desc}]")
    dif = prev_total - pl_prev
    if pl_prev > 0:
        print(f"  Diferença (calc-planilha): R$ {dif:+,.0f}")
