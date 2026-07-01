"""Dashboard de Previsão de Cargas — análise mensal previsão vs. realizado."""

from __future__ import annotations

import io
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from styles.global_ui import get_global_ui_css
from utils.pdf_report import gerar_pdf_previsao_cargas
from components.filtros_btn import render_filtros_btn
from components.sidebar import render_home_button

# ── Configuração ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Previsão de Cargas | Zanattex",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_global_ui_css(), unsafe_allow_html=True)

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
CARGAS_CACHE_TTL = 300  # segundos

MESES_DISPONIVEIS = [
    ("JANEIRO",   1, 2026),
    ("FEVEREIRO", 2, 2026),
    ("MARÇO",     3, 2026),
    ("ABRIL",     4, 2026),
    ("MAIO",      5, 2026),
    ("JUNHO",     6, 2026),
]

DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12),
    separators=",.",
    margin=dict(l=40, r=20, t=50, b=40),
)
_AXIS_BASE = dict(gridcolor="#2D3748", linecolor="#4A5568", zerolinecolor="#4A5568")
DARK_AXES = dict(xaxis=_AXIS_BASE, yaxis=_AXIS_BASE)


def _layout(**kwargs) -> dict:
    """Merge DARK + DARK_AXES base with per-chart overrides (avoids duplicate key errors)."""
    out = {**DARK}
    x_override = kwargs.pop("xaxis", {})
    y_override = kwargs.pop("yaxis", {})
    out["xaxis"] = {**_AXIS_BASE, **x_override}
    out["yaxis"] = {**_AXIS_BASE, **y_override}
    out.update(kwargs)
    return out

CORES = {
    "previsao":  "#4ECDC4",
    "realizado": "#45B7D1",
    "diferenca_pos": "#48BB78",
    "diferenca_neg": "#FC8181",
    "accent":    "#FFA726",
    "neutro":    "#718096",
}

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0F1117; }
[data-testid="stSidebar"] { background: #1A1D2E; border-right: 1px solid #2D3748; }

.pg-badge {
    display:inline-block; padding:5px 18px; border-radius:999px;
    font-size:.75rem; letter-spacing:.18em; text-transform:uppercase; font-weight:700;
    color:#FFA726; background:rgba(255,167,38,.10); border:1px solid rgba(255,167,38,.30);
    margin-bottom:14px;
}
.pg-title {
    font-size:2.2rem; font-weight:900; color:#FFF; margin:0 0 4px 0; line-height:1.1;
}
.pg-sub { color:#718096; font-size:.95rem; margin-bottom:0; }
.accent { color:#FFA726; }

.kpi-card {
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
    border-radius:14px; padding:18px 20px; text-align:center;
}
.kpi-label { font-size:.75rem; color:#718096; text-transform:uppercase; letter-spacing:.12em; margin-bottom:6px; }
.kpi-value { font-size:1.65rem; font-weight:800; color:#FFF; line-height:1; margin-bottom:4px; }
.kpi-delta { font-size:.82rem; font-weight:600; }
.kpi-pos { color:#48BB78; }
.kpi-neg { color:#FC8181; }
.kpi-neu { color:#718096; }

.sec-title {
    font-size:1rem; font-weight:700; color:#E2E8F0;
    margin:24px 0 12px 0; padding-bottom:6px;
    border-bottom:2px solid rgba(255,167,38,.3);
}
.alert-box {
    padding:12px 16px; border-radius:10px; margin-bottom:12px;
    background:rgba(252,129,129,.08); border:1px solid rgba(252,129,129,.25);
    color:#FC8181; font-size:.88rem;
}
.ok-box {
    padding:12px 16px; border-radius:10px; margin-bottom:12px;
    background:rgba(72,187,120,.08); border:1px solid rgba(72,187,120,.25);
    color:#48BB78; font-size:.88rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return (
        unicodedata.normalize("NFD", str(s))
        .encode("ascii", "ignore").decode()
        .upper().strip()
    )


def _parse_money(s: str) -> float | None:
    s = str(s).strip()
    if not s or "R$" not in s:
        return None
    neg = s.startswith("-")
    clean = re.sub(r"[R$\s\-]", "", s).replace(".", "").replace(",", ".")
    try:
        v = float(clean)
        return -v if neg else v
    except ValueError:
        return None


def _is_zero_money(s: str) -> bool:
    s = str(s).strip()
    return bool(re.match(r"^\s*R\$\s*[-\s]*$", s) or s in ("R$  -   ", "R$ -", "R$ 0,00"))


def _parse_date_pt(s: str) -> date | None:
    raw = str(s).strip()
    sl = raw.lower()

    # Formato primário: "quinta-feira, junho 1, 2026" (gviz PT locale)
    m = re.search(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", sl)
    if m:
        month = MESES_PT.get(m.group(2))
        if month:
            try:
                return date(int(m.group(4)), month, int(m.group(3)))
            except ValueError:
                pass

    # Fallback: "dd/mm/yyyy" ou "d/m/yyyy" (BR) ou "m/d/yyyy" (US)
    m2 = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$", raw.strip())
    if m2:
        a, b, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        # a > 12 → certamente é dia (DD/MM/YYYY)
        # b > 12 → certamente é mês (MM/DD/YYYY)
        # ambos ≤ 12 → assume DD/MM/YYYY (padrão BR)
        try:
            if a > 12:
                return date(y, b, a)
            elif b > 12:
                return date(y, a, b)
            else:
                return date(y, b, a)   # DD/MM/YYYY
        except ValueError:
            pass

    # Fallback: "yyyy-mm-dd" (ISO)
    m3 = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", raw.strip())
    if m3:
        try:
            return date(int(m3.group(1)), int(m3.group(2)), int(m3.group(3)))
        except ValueError:
            pass

    return None


def _is_date_str(s: str) -> bool:
    return bool(re.search(r"\d{4}", s)) and any(
        mes in s.lower() for mes in MESES_PT
    )


def _fmt(v: float, dec: int = 0) -> str:
    if dec == 0:
        return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return f"{v:+.1f}%".replace(".", ",")


# ── Loader ────────────────────────────────────────────────────────────────────
def _fetch_csv(sheet_name: str) -> list[list[str]]:
    nome_enc = urllib.parse.quote(sheet_name)
    url = (
        f"https://docs.google.com/spreadsheets/d/{CARGAS_SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={nome_enc}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    import csv
    return list(csv.reader(io.StringIO(raw)))


def _first_frete(row: list[str]) -> float:
    """Primeiro R$ positivo em cols 5-9.

    Para a maioria dos meses o frete está em col[6], mas JANEIRO usa col[7]
    (layout com coluna MOTORISTA extra). Varredura dinâmica evita hard-code.
    """
    for j in range(5, min(10, len(row))):
        v = _parse_money(row[j])
        if v and abs(v) > 0:
            return abs(v)
    return 0.0


def _parse_num(s: str) -> float | None:
    """Parse numérico permissivo — aceita valor com ou sem prefixo R$ ('2.450.000,00')."""
    s = str(s).strip()
    if not s or s in ("-", "R$", "R$  -", "R$-"):
        return None
    clean = re.sub(r"[R$\s\-]", "", s).replace(".", "").replace(",", ".")
    try:
        v = float(clean)
        return v if v > 0 else None
    except ValueError:
        return None


def _find_resumo_mensal(rows: list[list[str]]) -> tuple[float, float]:
    """Retorna (previsto_mensal, realizado_mensal) a partir da linha de resumo da planilha.

    Estratégia:
    1. Cabeçalho "Previsto total" no painel direito → lê os dois primeiros valores
       numéricos > R$10K da linha seguinte (previsto, realizado). Aplicada PRIMEIRO
       pois é a mais confiável e funciona mesmo quando o realizado > R$1M (que
       interferiria com a estratégia 2).
    2. Linha com 'GERAL' em cols 8-14 → col[GERAL+2] é o realizado (JANEIRO).
    3. Maior valor não-redondo (not % 1.000) > R$1 M em cols 8-15 de linhas
       não-data → realizado oficial do mês (FEVEREIRO-ABRIL concluídos).
    """

    # 1. Linha de resumo com DOIS valores > R$1.5M na mesma linha (sem data).
    # Só a linha "Previsto total | Realizado total" tem esse padrão — valores
    # de dias individuais ficam abaixo de R$1M. Não depende de texto nem de
    # posição de coluna; aceita número puro sem prefixo R$ ("2.450.000,00").
    for row in rows:
        if _parse_date_pt(row[1] if len(row) > 1 else ""):
            continue
        big: list[float] = []
        for cell in row:
            v = _parse_num(str(cell))
            if v and v > 1_500_000:
                big.append(v)
        if len(big) >= 2:
            return (big[0], big[1])

    # 2. Linha GERAL (JANEIRO)
    for row in rows:
        if _parse_date_pt(row[1] if len(row) > 1 else ""):
            continue
        for j in range(8, min(15, len(row))):
            if "GERAL" in _norm(row[j]):
                real_col = j + 2
                if len(row) > real_col:
                    v = _parse_money(row[real_col])
                    if v and abs(v) > 1_000_000:
                        return (0.0, abs(v))

    # 3. Maior valor não-redondo > R$1M em cols 8-15
    best = 0.0
    for row in rows:
        if _parse_date_pt(row[1] if len(row) > 1 else ""):
            continue
        for j in range(8, min(16, len(row))):
            v = _parse_money(row[j])
            if not v:
                continue
            av = abs(v)
            if av <= 1_000_000:
                continue
            if round(av) % 1_000 == 0:
                continue
            if av > best:
                best = av
    if best > 0:
        return (0.0, best)

    return (0.0, 0.0)


def _find_realizado_mensal(rows: list[list[str]]) -> float:
    """Compat wrapper — retorna apenas o realizado."""
    _, real = _find_resumo_mensal(rows)
    return real


def _extract_day_realized(rows: list[list[str]], mes_num: int, ano: int) -> dict:
    """
    Lê o painel direito do CSV (cols 8-13) e retorna {(data, cliente_norm): realizado}.

    Estrutura real do CSV por bloco de dia:
      col[8] = "DD-jun." (cabeçalho do dia, com col[9]="previsto" col[11]="diferença")
      linhas de cliente: col[8]=NOME, col[9]='R$', col[10]=previsto_val,
                         col[11]=realizado_val (número direto, sem prefixo separado)
      linha de total/separador: col[8]='' ou contém 'R$' — ignorada
    """
    day_real: dict = {}
    current_date = None

    for row in rows:
        if len(row) <= 8:
            continue
        cell8 = str(row[8]).strip()

        # Cabeçalho de dia: "1-jun.", "19-jun.", etc.
        m = re.match(r'^(\d{1,2})\s*[-\.]\s*(\w{3})', cell8.lower())
        if m:
            try:
                current_date = date(ano, mes_num, int(m.group(1)))
            except ValueError:
                current_date = None
            continue

        # Separador / total: col[8] vazio ou contém 'R$' — ignora
        if not cell8 or 'R$' in cell8:
            continue

        if current_date is None or len(row) <= 11:
            continue

        # Linha de cliente: col[8]=nome, col[11]=realizado por cliente
        cliente_raw = cell8.strip().upper()
        v = _parse_num(str(row[11]).strip())
        if v and v > 0 and cliente_raw:
            key = (current_date, _norm(cliente_raw))
            # Acumula caso haja mais de uma linha para o mesmo cliente no dia
            day_real[key] = day_real.get(key, 0.0) + v

    return day_real


def _parse_month(rows: list[list[str]], mes_nome: str, mes_num: int, ano: int) -> list[dict]:
    """Parse rows de uma aba mensal em registros de carga.

    Gera dois tipos de registro:
      1. Linhas de CARGO (com data em col[1]):
         PREVISAO = primeiro R$ positivo em cols 5-9 (frete individual).
         STATUS = Normal / Cancelada / Adiada / Armazenagem.
      2. UM registro CARGO_REAL por mês com o REALIZADO total detectado pela
         função _find_realizado_mensal (linha GERAL ou maior não-redondo > 1M).

    PREVISTO mensal = soma dos fretes individuais dos cargos OU previsto do painel
    direito quando disponível (meses em andamento com linha de resumo).
    REALIZADO mensal = valor oficial da planilha (linha de resumo).
    """
    previsto_mensal, realizado_mensal = _find_resumo_mensal(rows)
    day_realized = _extract_day_realized(rows, mes_num, ano)

    # Pré-computa índices de "linha mesclada": linha sem data onde SOMENTE col[6]
    # tem valor (todos os outros cols estão vazios) E a próxima linha tem data.
    # Esse padrão exato ocorre quando o Sheets exporta uma célula de frete cujos
    # campos de data/destino/veículo/local estão em células mescladas com a linha anterior.
    # Linhas "entre semanas" (totais de semana) também não têm data mas geralmente
    # têm conteúdo em cols além do 6 (cliente, previsto, etc.) → não passam na checagem.
    def _only_frete_col(r: list[str]) -> bool:
        """True se somente col[6] tem conteúdo e todos os outros estão vazios."""
        if len(r) <= 6:
            return False
        return (
            not any(r[j].strip() for j in range(6))
            and bool(r[6].strip())
            and not any(r[j].strip() for j in range(7, len(r)))
        )

    _merged_idx: set[int] = set()
    for _i, _r in enumerate(rows):
        if _parse_date_pt(_r[1] if len(_r) > 1 else ""):
            continue
        if not (_only_frete_col(_r) and _first_frete(_r)):
            continue
        _next = rows[_i + 1] if _i + 1 < len(rows) else []
        if _parse_date_pt(_next[1] if len(_next) > 1 else ""):
            _merged_idx.add(_i)

    records = []
    semana_atual = ""
    semana_end_date: date | None = None
    _last_cargo_date: date | None = None
    _last_destino_raw: str = ""

    for idx, row in enumerate(rows):
        if len(row) < 8:
            continue

        # Cabeçalho de semana (ex: "SEMANA 02/02  A 07/02")
        cell0 = row[0].strip()
        if re.search(r"SEMANA\s+\d{2}/\d{2}", _norm(cell0), re.I):
            semana_atual = cell0
            m_sem = re.search(r"A\s+(\d{2})/(\d{2})", cell0)
            if m_sem:
                try:
                    semana_end_date = date(ano, int(m_sem.group(2)), int(m_sem.group(1)))
                except ValueError:
                    semana_end_date = None
            if not _parse_date_pt(row[1] if len(row) > 1 else ""):
                continue

        if "DATA CARREGAMENTO" in _norm(row[1] if len(row) > 1 else ""):
            continue

        data_carga = _parse_date_pt(row[1]) if len(row) > 1 else None

        if not data_carga:
            # Célula mesclada: todos os campos (data, destino, veículo) estão mesclados
            # com a linha anterior no Sheets → CSV exporta cols 1-5 como vazio.
            # Identificado pelo lookahead: próxima linha com data confirma que este row
            # está no meio de uma sequência de cargos (não é total de semana).
            if idx in _merged_idx and _last_cargo_date:
                data_carga = _last_cargo_date
            else:
                continue

        # ── Linha de CARGO (com data em col[1] ou herdada de célula mesclada) ───
        _last_cargo_date = data_carga

        destino = row[2].strip().upper() if len(row) > 2 else ""
        if not destino or destino in ("DESTINO", ""):
            # Herda destino da linha anterior quando célula está mesclada
            if _last_destino_raw:
                destino = _last_destino_raw
            else:
                continue
        else:
            _last_destino_raw = destino

        # PREVISTO = primeiro R$ positivo em cols 5-9 (col[6] na maioria; col[7] em JANEIRO)
        valor_frete = _first_frete(row)

        # Cliente: busca textual de col[4] a col[7]
        cliente = ""
        for i in range(4, min(8, len(row))):
            v = row[i].strip()
            if v and "R$" not in v and not _is_date_str(v) and not re.match(r"^\d+[-/]", v):
                cliente = v.upper()
                break
        if not cliente:
            cliente = destino

        # Local carregamento: busca textual entre col[3] e col[6]
        local = ""
        for i in range(3, min(7, len(row))):
            v = row[i].strip().upper()
            if v and "R$" not in v and not _is_date_str(v):
                local = v
                break
        local_norm = _norm(local)
        if "IACANGA" in local_norm:
            local_tag = "Iacanga"
        elif "AREALVA" in local_norm:
            local_tag = "Arealva"
        elif "ITAJU" in local_norm:
            local_tag = "Itaju"
        elif "BARIRI" in local_norm:
            local_tag = "Bariri"
        elif "IBITINGA" in local_norm:
            local_tag = "Ibitinga"
        elif local_norm:
            local_tag = "Múltiplas"
        else:
            local_tag = "N/I"

        # OBS / status
        obs_raw = ""
        status = "Normal"
        for cell in row[6:15]:
            v = cell.strip().upper()
            if not v or "R$" in v:
                continue
            if "CANCEL" in v:
                obs_raw = v; status = "Cancelada"; break
            if any(k in v for k in ["ADIAD", "ADIADO", "ADIADA"]):
                obs_raw = v; status = "Adiada"; break
            if "ARMAZENAGEM" in v:
                obs_raw = v; status = "Armazenagem"; break

        # Veículo
        veiculo = ""
        for i in range(3, min(6, len(row))):
            v = row[i].strip()
            if v and not _is_date_str(v) and "R$" not in v:
                vn = _norm(v)
                if any(k in vn for k in ["CARRETA", "TRUCK", "TRANSP", "ACCELO"]):
                    veiculo = v.upper()
                    break
        tipo_veiculo = (
            "Carreta"    if "CARRETA" in _norm(veiculo) else
            "Truck"      if "TRUCK"   in _norm(veiculo) else
            "Acello"     if "ACCELO"  in _norm(veiculo) else
            "Transporte" if "TRANSP"  in _norm(veiculo) else
            "Outro"
        )

        records.append({
            "MES":          mes_nome,
            "MES_NUM":      mes_num,
            "ANO":          ano,
            "SEMANA":       semana_atual,
            "DATA":         data_carga,
            "DESTINO":      destino,
            "LOCAL":        local_tag,
            "VEICULO":      veiculo,
            "TIPO_VEICULO": tipo_veiculo,
            "VALOR_FRETE":  valor_frete,
            "CLIENTE":      cliente,
            # Quando o painel direito tem previsto oficial, zera o frete individual
            # para evitar dupla contagem (previsto total vai no CARGO_REAL).
            "PREVISAO":       0.0 if previsto_mensal > 0 else valor_frete,
            "REALIZADO":      0.0,
            # Painel direito usa nome da empresa (= DESTINO). Tenta também CLIENTE
            # como fallback para meses onde ambos coincidem.
            "REALIZADO_DIA":  (
                day_realized.get((data_carga, _norm(destino)), 0.0)
                or day_realized.get((data_carga, _norm(cliente)), 0.0)
            ),
            "DIFERENCA":      0.0,
            "OBS":            obs_raw,
            "STATUS":         status,
        })

    # Registro único de REALIZADO e PREVISTO mensal (da linha de resumo da planilha)
    if realizado_mensal > 0 or previsto_mensal > 0:
        proxy_date = _last_cargo_date or date(ano, mes_num, 28)
        records.append({
            "MES":          mes_nome,
            "MES_NUM":      mes_num,
            "ANO":          ano,
            "SEMANA":       "",
            "DATA":         proxy_date,
            "DESTINO":      mes_nome,
            "LOCAL":        "",
            "VEICULO":      "",
            "TIPO_VEICULO": "",
            "VALOR_FRETE":  0.0,
            "CLIENTE":      mes_nome,
            "PREVISAO":      previsto_mensal,
            "REALIZADO":     realizado_mensal,
            "REALIZADO_DIA": 0.0,
            "DIFERENCA":     0.0,
            "OBS":           "",
            "STATUS":        "CARGO_REAL",
        })

    return records


@st.cache_data(ttl=CARGAS_CACHE_TTL, show_spinner=False)
def load_cargas() -> pd.DataFrame:
    all_records: list[dict] = []
    for mes_nome, mes_num, ano in MESES_DISPONIVEIS:
        try:
            rows = _fetch_csv(mes_nome)
            records = _parse_month(rows, mes_nome, mes_num, ano)
            all_records.extend(records)
        except Exception as e:
            st.warning(f"⚠️ Não foi possível carregar {mes_nome}: {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    df["DATA"] = pd.to_datetime(df["DATA"])
    df["SEMANA_ISO"] = df["DATA"].dt.isocalendar().week.astype(int)
    df["DIA_SEMANA"] = df["DATA"].dt.day_name()

    # Normalizar clientes
    alias = {
        "NIAZITEX": "NIAZITEX",
        "NIAZITTEX": "NIAZITEX",
        "NC INDUSTRIA": "NIAZITEX",
    }
    df["CLIENTE_NORM"] = df["CLIENTE"].apply(
        lambda x: alias.get(_norm(x), _norm(x))
    )
    df["DESTINO_NORM"] = df["DESTINO"].apply(
        lambda x: alias.get(_norm(x), _norm(x))
    )

    # Meses que têm realizado lançado na planilha
    meses_com_real = set(df.loc[df["STATUS"] == "CARGO_REAL", "MES"].tolist())
    # Cargo records de meses concluídos (exclui o próprio registro CARGO_REAL)
    df["TEM_REALIZADO"] = df["MES"].isin(meses_com_real) & (df["STATUS"] != "CARGO_REAL")

    try:
        from utils.db_manager import upsert_df
        _cols_db = ["DATA", "DESTINO", "CLIENTE", "STATUS", "LOCAL", "VEICULO", "TIPO_VEICULO", "PREVISAO", "REALIZADO", "VALOR_FRETE", "OBS"]
        _cols_exist = [c for c in _cols_db if c in df.columns]
        upsert_df(df[_cols_exist], "previsao_cargas", ["DATA", "DESTINO", "CLIENTE", "STATUS"])
    except Exception:
        import logging
        logging.warning("db_manager: falha ao salvar previsao_cargas", exc_info=True)

    return df


# ── Layout principal ──────────────────────────────────────────────────────────
with st.spinner("⏳ Carregando dados de cargas…"):
    df_raw = load_cargas()

if df_raw.empty:
    st.error("❌ Nenhum dado disponível. Verifique o acesso à planilha.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_home_button()

with st.sidebar:
    st.markdown("## 🚛 Filtros")

    st.caption(f"Atualizado a cada {CARGAS_CACHE_TTL}s · {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Atualizar Dados", key="refresh_cargas", use_container_width=True):
        load_cargas.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**📅 Meses**")
    meses_disp = df_raw["MES"].unique().tolist()
    sel_meses = st.multiselect(
        "Mês", meses_disp, default=meses_disp, placeholder="Todos", key="sel_mes_carga"
    )
    if not sel_meses:
        sel_meses = meses_disp

    st.markdown("**🏢 Destino / Cliente**")
    destinos_disp = sorted(df_raw["DESTINO_NORM"].unique())
    sel_destinos = st.multiselect(
        "Destino", destinos_disp, placeholder="Todos", key="sel_dest_carga"
    )

    st.markdown("**📍 Local de Carregamento**")
    locais_disp = sorted(df_raw["LOCAL"].unique())
    sel_locais = st.multiselect(
        "Origem", locais_disp, placeholder="Todas", key="sel_local_carga"
    )

    st.markdown("**🚦 Status da Carga**")
    # Exclui "SEMANA_TOTAL" da lista visível — é interno ao parser, não um status de carga
    status_disp = sorted(s for s in df_raw["STATUS"].unique() if s not in ("SEMANA_TOTAL", "CARGO_REAL"))
    sel_status = st.multiselect(
        "Status", status_disp, default=status_disp,
        placeholder="Todos", key="sel_status_carga"
    )
    if not sel_status:
        sel_status = status_disp

    st.markdown("---")
    mostrar_sem_real = st.toggle(
        "Incluir cargas sem realizado", value=False, key="toggle_sem_real"
    )



# ── Aplicar filtros ───────────────────────────────────────────────────────────
# Linhas CARGO_REAL (tabela lateral de realizado) são preservadas sem filtro de
# destino/local/status para que o KPI de realizado seja sempre o total real do mês.
_df_mes = df_raw[df_raw["MES"].isin(sel_meses)]
df_real_fixo  = _df_mes[_df_mes["STATUS"] == "CARGO_REAL"].copy()
df_cargo_filt = _df_mes[_df_mes["STATUS"] != "CARGO_REAL"].copy()

if sel_destinos:
    df_cargo_filt = df_cargo_filt[df_cargo_filt["DESTINO_NORM"].isin(sel_destinos)]
if sel_locais:
    df_cargo_filt = df_cargo_filt[df_cargo_filt["LOCAL"].isin(sel_locais)]
if sel_status:
    df_cargo_filt = df_cargo_filt[df_cargo_filt["STATUS"].isin(sel_status)]
if not mostrar_sem_real:
    # Mantém cargos de meses com previsto oficial mesmo que PREVISAO individual = 0
    _meses_com_prev_ofic = set(df_real_fixo[df_real_fixo["PREVISAO"] > 0]["MES_NUM"])
    df_cargo_filt = df_cargo_filt[
        (df_cargo_filt["PREVISAO"] > 0) |
        df_cargo_filt["MES_NUM"].isin(_meses_com_prev_ofic)
    ]

df = pd.concat([df_real_fixo, df_cargo_filt], ignore_index=True)

if df.empty:
    st.warning("⚠️ Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

render_filtros_btn()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center'><span class='pg-badge'>🚛 Logística · Zanattex</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h1 class='pg-title' style='text-align:center'>Dashboard de <span class='accent'>Previsão de Cargas</span></h1>"
    "<p class='pg-sub' style='text-align:center'>Análise de previsão vs. realizado por mês, destino e origem</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── KPIs globais ──────────────────────────────────────────────────────────────
# PREVISTO = soma de df["PREVISAO"] (cargo fretes + CARGO_REAL.PREVISAO oficial).
# Para meses sem previsto oficial: fretes somados dos cargos; CARGO_REAL.PREVISAO = 0.
# Para meses com previsto oficial: fretes dos cargos = 0; CARGO_REAL.PREVISAO = oficial.
# Assim df["PREVISAO"].sum() nunca dupla-conta.
df_cargos    = df[df["STATUS"].isin(["Normal", "Cancelada", "Adiada", "Armazenagem"])]
df_realizados = df[df["STATUS"] == "CARGO_REAL"]

total_prev   = df["PREVISAO"].sum()
total_real   = df_realizados["REALIZADO"].sum()
diferenca_g  = total_real - total_prev if total_prev > 0 else 0.0

# Aderência: apenas meses que já têm REALIZADO > 0 (exclui meses futuros/incompletos)
_meses_com_real = set(
    df_realizados.groupby("MES_NUM")["REALIZADO"]
    .sum().pipe(lambda s: s[s > 0].index)
)
_prev_adh = df[df["MES_NUM"].isin(_meses_com_real)]["PREVISAO"].sum()
_real_adh = df_realizados[df_realizados["MES_NUM"].isin(_meses_com_real)]["REALIZADO"].sum()
aderencia_g  = (_real_adh / _prev_adh * 100) if _prev_adh > 0 else 0.0
n_cargas     = df_cargos["DATA"].nunique()
n_canceladas = (df_cargos["STATUS"] == "Cancelada").sum()
n_adiadas    = (df_cargos["STATUS"] == "Adiada").sum()
n_clientes   = df_cargos["DESTINO_NORM"].nunique()

col1, col2, col3, col4, col5, col6 = st.columns(6)
kpis = [
    (col1, "💰 Previsão Total",   _fmt(total_prev), "", "neu"),
    (col2, "✅ Realizado Total",  _fmt(total_real), "", "neu"),
    (col3, "⚖️ Diferença",       _fmt(diferenca_g),
     f"{'+' if diferenca_g >= 0 else ''}{_fmt(diferenca_g)} vs previsão",
     "pos" if diferenca_g >= 0 else "neg"),
    (col4, "🎯 Aderência",       f"{aderencia_g:.1f}%".replace(".", ","),
     "Realizado / Previsto", "pos" if aderencia_g >= 95 else ("neg" if aderencia_g < 80 else "neu")),
    (col5, "🚚 Clientes Ativos",  str(n_clientes), "", "neu"),
    (col6, "🚩 Canceladas+Adiadas", str(n_canceladas + n_adiadas),
     f"{n_canceladas} cancel. · {n_adiadas} adiadas",
     "neg" if (n_canceladas + n_adiadas) > 5 else "neu"),
]
for col, label, value, delta, color in kpis:
    with col:
        delta_html = (
            f"<div class='kpi-delta kpi-{color}'>{delta}</div>" if delta else ""
        )
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div>"
            f"{delta_html}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Previsão vs Realizado por Mês ─────────────────────────────────────────────
st.markdown("<div class='sec-title'>📊 Previsão vs. Realizado por Mês</div>", unsafe_allow_html=True)

_prev_mes = (
    df.groupby(["MES", "MES_NUM"])["PREVISAO"].sum().reset_index()
)
_real_mes = (
    df_realizados.groupby(["MES", "MES_NUM"])["REALIZADO"].sum().reset_index()
)
df_mes = (
    _prev_mes.merge(_real_mes, on=["MES", "MES_NUM"], how="outer")
    .fillna(0)
    .sort_values("MES_NUM")
)
df_mes["ADERENCIA"] = df_mes.apply(
    lambda r: r["REALIZADO"] / r["PREVISAO"] * 100 if r["PREVISAO"] > 0 else 0, axis=1
)
df_mes["DIFERENCA"] = df_mes["REALIZADO"] - df_mes["PREVISAO"]

fig_mes = go.Figure()
fig_mes.add_bar(
    x=df_mes["MES"], y=df_mes["PREVISAO"],
    name="Previsão", marker_color=CORES["previsao"],
    text=[_fmt(v) for v in df_mes["PREVISAO"]],
    textposition="outside", textfont=dict(size=10),
)
fig_mes.add_bar(
    x=df_mes["MES"], y=df_mes["REALIZADO"],
    name="Realizado", marker_color=CORES["realizado"],
    text=[_fmt(v) for v in df_mes["REALIZADO"]],
    textposition="outside", textfont=dict(size=10),
)
fig_mes.add_scatter(
    x=df_mes["MES"], y=df_mes["ADERENCIA"],
    name="Aderência %", mode="lines+markers+text",
    yaxis="y2", line=dict(color=CORES["accent"], width=2.5),
    marker=dict(size=8, color=CORES["accent"]),
    text=[f"{v:.0f}%".replace(".", ",") for v in df_mes["ADERENCIA"]],
    textposition="top center", textfont=dict(size=10, color=CORES["accent"]),
)
fig_mes.update_layout(
    **_layout(
        barmode="group", height=380,
        title="Previsão vs. Realizado — visão mensal",
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        yaxis=dict(tickprefix="R$ ", separatethousands=True),
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False,
            range=[0, 160], ticksuffix="%", title="Aderência %",
        ),
    )
)
st.plotly_chart(fig_mes, use_container_width=True)

# ── Linha 2: Por Destino + Por Local ─────────────────────────────────────────
st.markdown("<div class='sec-title'>🏢 Análise por Destino e Origem</div>", unsafe_allow_html=True)
col_g1, col_g2 = st.columns(2)

with col_g1:
    df_dest = (
        df[df["TEM_REALIZADO"] & (df["PREVISAO"] > 0)]
        .groupby("DESTINO_NORM")
        .agg(PREVISAO=("PREVISAO", "sum"), N_CARGAS=("DATA", "count"))
        .reset_index()
        .sort_values("PREVISAO", ascending=True)
        .tail(12)
    )
    fig_dest = go.Figure()
    fig_dest.add_bar(
        y=df_dest["DESTINO_NORM"], x=df_dest["PREVISAO"],
        name="Previsão (faturamento)", orientation="h", marker_color=CORES["previsao"],
        text=[_fmt(v) for v in df_dest["PREVISAO"]],
        textposition="outside", textfont=dict(size=9),
    )
    fig_dest.update_layout(
        **_layout(
            height=360,
            title="Previsão por Cliente - Meses Concluídos",
            xaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_dest, use_container_width=True)

with col_g2:
    df_local = (
        df[df["PREVISAO"] > 0]
        .groupby("LOCAL")
        .agg(PREVISAO=("PREVISAO", "sum"), N=("DATA", "count"))
        .reset_index()
        .sort_values("PREVISAO", ascending=False)
    )
    fig_local = go.Figure(go.Pie(
        labels=df_local["LOCAL"],
        values=df_local["PREVISAO"],
        hole=0.52,
        textinfo="label+percent",
        hovertemplate="%{label}<br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        marker=dict(colors=["#4ECDC4", "#45B7D1", "#FFA726", "#FC8181", "#48BB78", "#A78BFA"]),
    ))
    fig_local.update_layout(
        **DARK, height=360,
        title="Distribuição por Local de Carregamento",
        annotations=[dict(text="Origem", x=.5, y=.5,
                          font=dict(size=11, color="#CBD5E0"), showarrow=False)],
    )
    st.plotly_chart(fig_local, use_container_width=True)

# ── Linha 3: Aderência por cliente + Evolução semanal ────────────────────────
st.markdown("<div class='sec-title'>🎯 Aderência da Previsão por Cliente</div>", unsafe_allow_html=True)
col_g3, col_g4 = st.columns(2)

with col_g3:
    # Aderência calculada pelo total mensal (REALIZADO mensal / PREVISTO mensal por fretes)
    _prev_adh = (
        df[df["STATUS"].isin(["Normal", "Cancelada", "Adiada", "Armazenagem"]) & (df["PREVISAO"] > 0)]
        .groupby("MES")["PREVISAO"].sum()
    )
    _real_adh = (
        df[df["STATUS"] == "CARGO_REAL"]
        .groupby("MES")["REALIZADO"].sum()
    )
    df_adh = pd.DataFrame({"PREVISAO": _prev_adh, "REALIZADO": _real_adh}).dropna().reset_index()
    df_adh = df_adh[df_adh["PREVISAO"] > 0].copy()
    df_adh["ADERENCIA"] = df_adh["REALIZADO"] / df_adh["PREVISAO"] * 100
    df_adh = df_adh.sort_values("ADERENCIA", ascending=True)

    colors_bar = [
        CORES["diferenca_pos"] if v >= 95 else (CORES["diferenca_neg"] if v < 80 else CORES["accent"])
        for v in df_adh["ADERENCIA"]
    ]
    fig_adh = go.Figure(go.Bar(
        y=df_adh["MES"],
        x=df_adh["ADERENCIA"],
        orientation="h",
        marker_color=colors_bar,
        text=[f"{v:.1f}%".replace(".", ",") for v in df_adh["ADERENCIA"]],
        textposition="outside",
        hovertemplate="%{y}<br>Aderência: %{x:.1f}%<extra></extra>",
    ))
    fig_adh.add_vline(x=100, line_dash="dash", line_color="#718096", line_width=1.5,
                      annotation_text="Meta 100%", annotation_font_color="#718096")
    fig_adh.update_layout(
        **_layout(
            height=360,
            title="% Aderência (Realizado / Previsto) por Mês",
            xaxis=dict(ticksuffix="%", range=[0, 160]),
        )
    )
    st.plotly_chart(fig_adh, use_container_width=True)

with col_g4:
    df_week = (
        df[df["TEM_REALIZADO"] & (df["PREVISAO"] > 0)]
        .groupby(["MES", "MES_NUM", "SEMANA_ISO"])
        .agg(PREVISAO=("PREVISAO", "sum"), N=("DATA", "count"))
        .reset_index()
        .sort_values(["MES_NUM", "SEMANA_ISO"])
    )
    df_week["LABEL"] = df_week["MES"].str[:3] + " S" + df_week["SEMANA_ISO"].astype(str)

    fig_week = go.Figure()
    fig_week.add_scatter(
        x=df_week["LABEL"], y=df_week["PREVISAO"],
        name="Previsão (faturamento/semana)", mode="lines+markers",
        line=dict(color=CORES["previsao"], width=2.5),
        marker=dict(size=7),
    )
    fig_week.update_layout(
        **_layout(
            height=360,
            title="Evolução Semanal — Previsão de Faturamento",
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
            yaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_week, use_container_width=True)

# ── Linha 4: Tipo de veículo + Timeline ──────────────────────────────────────
st.markdown("<div class='sec-title'>🚚 Frota e Timeline de Cargas</div>", unsafe_allow_html=True)
col_g5, col_g6 = st.columns(2)

with col_g5:
    df_veic = (
        df[df["TIPO_VEICULO"] != "Outro"]
        .groupby("TIPO_VEICULO")
        .agg(N=("DATA", "count"), PREVISAO=("PREVISAO", "sum"))
        .reset_index()
        .sort_values("N", ascending=False)
    )
    fig_veic = go.Figure()
    fig_veic.add_bar(
        x=df_veic["TIPO_VEICULO"], y=df_veic["N"],
        name="Qtd. Cargas", marker_color=CORES["previsao"],
        text=df_veic["N"], textposition="outside",
        yaxis="y",
    )
    fig_veic.add_scatter(
        x=df_veic["TIPO_VEICULO"], y=df_veic["PREVISAO"],
        name="Previsão R$", mode="markers",
        marker=dict(size=14, color=CORES["accent"], symbol="diamond"),
        yaxis="y2",
    )
    fig_veic.update_layout(
        **_layout(
            height=320,
            title="Cargas por Tipo de Veículo",
            yaxis=dict(title="Qtd. Cargas"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title="Previsão R$", tickprefix="R$ "),
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        )
    )
    st.plotly_chart(fig_veic, use_container_width=True)

with col_g6:
    df_tl = (
        df.groupby(["DATA", "STATUS"])
        .agg(PREVISAO=("PREVISAO", "sum"), N=("DESTINO", "count"))
        .reset_index()
    )
    cores_status = {"Normal": CORES["previsao"], "Cancelada": CORES["diferenca_neg"],
                    "Adiada": CORES["accent"], "Armazenagem": CORES["neutro"]}
    fig_tl = go.Figure()
    for status_v, grp in df_tl.groupby("STATUS"):
        fig_tl.add_scatter(
            x=grp["DATA"], y=grp["PREVISAO"],
            mode="markers",
            name=status_v,
            marker=dict(
                size=grp["N"] * 5 + 8,
                color=cores_status.get(status_v, "#718096"),
                opacity=0.8,
                line=dict(color="rgba(255,255,255,.2)", width=1),
            ),
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>"
                f"Status: {status_v}<br>"
                "Previsão: R$ %{y:,.0f}<br>"
                "Cargas: %{customdata}<extra></extra>"
            ),
            customdata=grp["N"],
        )
    fig_tl.update_layout(
        **_layout(
            height=320,
            title="Timeline de Cargas (tamanho = qtd. por dia)",
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            yaxis=dict(tickprefix="R$ "),
        )
    )
    st.plotly_chart(fig_tl, use_container_width=True)

# ── Cancelamentos e Adiamentos ────────────────────────────────────────────────
st.markdown("<div class='sec-title'>🚨 Ocorrências — Canceladas e Adiadas</div>", unsafe_allow_html=True)

df_ocorr = df[df["STATUS"].isin(["Cancelada", "Adiada"])].copy()
if df_ocorr.empty:
    st.markdown("<div class='ok-box'>✅ Nenhuma cancelamento ou adiamento nos filtros selecionados.</div>",
                unsafe_allow_html=True)
else:
    valor_impacto = df_ocorr["PREVISAO"].sum()
    n_cancel = (df_ocorr["STATUS"] == "Cancelada").sum()
    n_adiad  = (df_ocorr["STATUS"] == "Adiada").sum()

    st.markdown(
        f"<div class='alert-box'>⚠️ <strong>{len(df_ocorr)}</strong> ocorrências detectadas — "
        f"{n_cancel} canceladas · {n_adiad} adiadas · "
        f"Impacto na previsão: <strong>{_fmt(valor_impacto)}</strong></div>",
        unsafe_allow_html=True,
    )

    col_oc1, col_oc2 = st.columns(2)
    with col_oc1:
        df_oc_mes = df_ocorr.groupby(["MES", "STATUS"]).size().reset_index(name="N")
        fig_oc = px.bar(
            df_oc_mes, x="MES", y="N", color="STATUS",
            color_discrete_map={"Cancelada": CORES["diferenca_neg"], "Adiada": CORES["accent"]},
            title="Ocorrências por Mês",
            labels={"N": "Qtd.", "MES": "Mês"},
        )
        fig_oc.update_layout(**_layout(height=300, legend=dict(orientation="h", y=-0.18)))
        st.plotly_chart(fig_oc, use_container_width=True)

    with col_oc2:
        df_oc_dest = (
            df_ocorr.groupby("DESTINO_NORM")
            .agg(N=("DATA", "count"), PREVISAO=("PREVISAO", "sum"))
            .reset_index()
            .sort_values("N", ascending=True)
        )
        fig_oc2 = go.Figure(go.Bar(
            y=df_oc_dest["DESTINO_NORM"], x=df_oc_dest["N"],
            orientation="h",
            text=df_oc_dest["N"], textposition="outside",
            marker_color=CORES["diferenca_neg"],
        ))
        fig_oc2.update_layout(
            **_layout(
                height=300,
                title="Ocorrências por Destino",
                xaxis=dict(title="Qtd."),
            )
        )
        st.plotly_chart(fig_oc2, use_container_width=True)

# ── Heatmap: cargas por dia da semana e mês ───────────────────────────────────
st.markdown("<div class='sec-title'>📅 Mapa de Calor — Cargas por Dia da Semana</div>", unsafe_allow_html=True)

dias_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dias_pt    = {"Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
              "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"}

df_heat = (
    df[df["TEM_REALIZADO"] & (df["PREVISAO"] > 0)]
    .groupby(["MES", "DIA_SEMANA"])
    .agg(PREVISAO=("PREVISAO", "sum"), N=("DATA", "count"))
    .reset_index()
)
df_heat["DIA_PT"] = df_heat["DIA_SEMANA"].map(dias_pt)

pivot_heat = df_heat.pivot_table(
    index="DIA_SEMANA", columns="MES", values="PREVISAO", aggfunc="sum", fill_value=0
)
# Ordenar dias
pivot_heat = pivot_heat.reindex([d for d in dias_order if d in pivot_heat.index])
pivot_heat.index = [dias_pt.get(d, d) for d in pivot_heat.index]

# Ordenar meses
mes_order = [m[0] for m in MESES_DISPONIVEIS if m[0] in pivot_heat.columns]
pivot_heat = pivot_heat[mes_order]

fig_heat = go.Figure(go.Heatmap(
    z=pivot_heat.values,
    x=pivot_heat.columns.tolist(),
    y=pivot_heat.index.tolist(),
    colorscale=[
        [0, "rgba(30,40,60,.4)"],
        [0.3, "#1A3A5C"],
        [0.7, "#2196F3"],
        [1, "#4ECDC4"],
    ],
    hovertemplate="%{y} · %{x}<br>R$ %{z:,.0f}<extra></extra>",
    colorbar=dict(title="R$", tickprefix="R$ "),
    text=[[_fmt(v).replace("R$ ", "") for v in row] for row in pivot_heat.values],
    texttemplate="%{text}",
    textfont=dict(size=9),
))
fig_heat.update_layout(**DARK, height=320, title="Previsão de Faturamento por Dia da Semana × Mês")
st.plotly_chart(fig_heat, use_container_width=True)

# ── Tabela detalhada ──────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>📋 Detalhe de Registros</div>", unsafe_allow_html=True)

col_tb1, col_tb2 = st.columns([3, 1])
with col_tb2:
    busca = st.text_input("🔍 Buscar destino/cliente", "", key="busca_carga", placeholder="ex: CAMESA")

df_show = df[df["STATUS"] != "CARGO_REAL"].copy()
if busca.strip():
    mask = df_show["DESTINO_NORM"].str.contains(busca.upper(), na=False) | \
           df_show["CLIENTE"].str.contains(busca.upper(), na=False)
    df_show = df_show[mask]

df_table = df_show[[
    "MES", "DATA", "DESTINO", "LOCAL", "TIPO_VEICULO",
    "CLIENTE", "VALOR_FRETE", "REALIZADO_DIA", "STATUS", "OBS"
]].copy()
df_table["DIFERENCA"] = df_table["REALIZADO_DIA"] - df_table["VALOR_FRETE"]

df_table["DATA"] = df_table["DATA"].dt.strftime("%d/%m/%Y")
for col in ["VALOR_FRETE", "REALIZADO_DIA", "DIFERENCA"]:
    df_table[col] = df_table[col].apply(lambda v: _fmt(v))

df_table = df_table[[
    "MES", "DATA", "DESTINO", "LOCAL", "TIPO_VEICULO",
    "CLIENTE", "VALOR_FRETE", "REALIZADO_DIA", "DIFERENCA", "STATUS", "OBS"
]]
df_table.columns = [
    "Mês", "Data Carga", "Destino", "Origem", "Veículo",
    "Cliente", "Previsão", "Realizado Dia", "Diferença", "Status", "Obs",
]

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
    height=min(50 + len(df_table) * 35, 500),
)

# ── Resumo mensal ─────────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>📊 Resumo por Mês</div>", unsafe_allow_html=True)

df_resumo = (
    df.groupby("MES")
    .agg(
        N_Registros=("DATA", "count"),
        Previsao=("PREVISAO", "sum"),
        Realizado=("REALIZADO", "sum"),
        Canceladas=("STATUS", lambda x: (x == "Cancelada").sum()),
        Adiadas=("STATUS", lambda x: (x == "Adiada").sum()),
        Destinos=("DESTINO_NORM", "nunique"),
    )
    .reset_index()
)
df_resumo["Aderência %"] = df_resumo.apply(
    lambda r: f"{r['Realizado']/r['Previsao']*100:.1f}%".replace(".", ",")
    if r["Previsao"] > 0 else "—", axis=1
)
df_resumo["Diferença"] = df_resumo["Realizado"] - df_resumo["Previsao"]
for col in ["Previsao", "Realizado", "Diferença"]:
    df_resumo[col] = df_resumo[col].apply(_fmt)

df_resumo.columns = [
    "Mês", "Registros", "Previsão Total", "Realizado Total",
    "Canceladas", "Adiadas", "Destinos Únicos", "Aderência %", "Diferença",
]
st.dataframe(df_resumo, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#4A5568;font-size:.82rem;'>"
    f"🚛 Previsão de Cargas · Zanattex &nbsp;|&nbsp; "
    f"Dados: {len(df_raw):,} registros carregados &nbsp;|&nbsp; "
    f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</div>",
    unsafe_allow_html=True,
)
