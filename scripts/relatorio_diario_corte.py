"""Relatório diário de corte - busca dados do Google Sheets e envia por email."""

import io
import os
import smtplib
import logging
import tempfile
from calendar import monthrange
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "relatorio_corte.log"),
            encoding="utf-8"
        ),
    ]
)

# configuração
EMAIL_REMETENTE     = os.getenv("EMAIL_REMETENTE", "")
EMAIL_SENHA_APP     = os.getenv("EMAIL_SENHA_APP", "")
_dest_raw           = os.getenv("EMAIL_DESTINATARIOS", os.getenv("EMAIL_DESTINATARIO", "erickviniciusvas@gmail.com"))
EMAIL_DESTINATARIOS = [e.strip() for e in _dest_raw.split(",") if e.strip()]

SHEET_MANTA_AREALVA_ID  = "1KLbNpw-P28YgoijXfMXU-zRQULuDHMMB"
SHEET_MANTA_AREALVA_GID = "1544210185"

SHEET_MANTA_IACANGA_ID  = "1FBpCrq29_e1UBNwBlcgPTz66tbpUsgcgtzfXi4DcORU"
SHEET_MANTA_IACANGA_GID = "0"

SHEET_LENCOL_ID  = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
SHEET_LENCOL_GID = "1396046910"

HEADERS = {"User-Agent": "Mozilla/5.0"}

_raw: dict = {}  # cache pra não baixar os dados repetidas vezes

# helpers para processar dados
def _find_col(df: pd.DataFrame, *substrings: str) -> str | None:
    """Encontra coluna cujo nome ASCII contém todos os substrings (ignora acentos e encoding)."""
    for col in df.columns:
        col_ascii = col.encode("ascii", errors="ignore").decode().upper()
        if all(s.upper() in col_ascii for s in substrings):
            return col
    return None

def _find_col_exact(df: pd.DataFrame, name: str) -> str | None:
    """Encontra coluna cujo nome ASCII é exatamente `name` (ignora acentos e encoding)."""
    target = name.upper()
    for col in df.columns:
        if col.encode("ascii", errors="ignore").decode().upper().strip() == target:
            return col
    return None

def _baixar_csv(sheet_id: str, gid: str | None = None) -> pd.DataFrame | None:
    urls = [f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"]
    if gid:
        urls.insert(0, f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}")
    for url in urls:
        try:
            r = requests.get(url, timeout=30, headers=HEADERS)
            r.encoding = "utf-8"  # google sheets exporta UTF-8
            if r.status_code == 200 and len(r.text) > 100:
                return pd.read_csv(io.StringIO(r.text), header=0, dtype=str)
        except Exception as e:
            logging.warning(f"Falha {url[:60]}: {e}")
    return None

def _parse_datas(df: pd.DataFrame, col: str = "DATA", dayfirst: bool = True) -> pd.DataFrame:
    # Localiza coluna de data de forma case-insensitive (ex.: "Data" → "DATA")
    col_real = col
    for c in df.columns:
        if c.strip().upper() == col.upper():
            col_real = c
            break
    if col_real not in df.columns:
        logging.warning(f"Coluna '{col}' não encontrada. Colunas: {list(df.columns)}")
        return pd.DataFrame()

    raw = df[col_real].astype(str).str.split(" ").str[0].str.strip()
    try:
        # format="mixed" requer pandas >= 2.0
        parsed = pd.to_datetime(raw, format="mixed", dayfirst=dayfirst, errors="coerce")
    except TypeError:
        # pandas < 2.0: fallback sem format="mixed"
        parsed = pd.to_datetime(raw, dayfirst=dayfirst, errors="coerce")

    df = df.copy()
    df["DATA"] = parsed
    return df.dropna(subset=["DATA"])

def _dia_ref() -> date:
    return date.today() - timedelta(days=1)

# carregamento de dados
def _str_col(df: pd.DataFrame, col: str | None, fillna: str = "") -> pd.Series:
    if col and col in df.columns:
        return df[col].fillna(fillna).astype(str).str.strip()
    return pd.Series(fillna, index=df.index)

def _raw_manta_arealva() -> pd.DataFrame:
    if "are" in _raw:
        return _raw["are"]
    df = _baixar_csv(SHEET_MANTA_AREALVA_ID, SHEET_MANTA_AREALVA_GID)
    if df is None:
        logging.error("Não foi possível baixar Manta Arealva.")
        _raw["are"] = pd.DataFrame()
        return _raw["are"]
    df.columns = df.columns.str.strip().str.upper()
    # Planilha Manta Arealva usa formato americano M/D/AAAA (ex.: "1/7/2026" = 7 de janeiro)
    df = _parse_datas(df, dayfirst=False)
    if not df.empty:
        quant_col   = _find_col(df, "QUANTIDADE")
        estacao_col = _find_col(df, "ESTA", "CORTE")
        op_col      = _find_col(df, "OP")
        cor_col     = _find_col_exact(df, "COR")
        prod_col    = _find_col(df, "PRODUTO")
        tam_col     = _find_col(df, "TAMANHO")
        obs_col     = _find_col(df, "OBSERVA")
        df["QUANTIDADE"] = pd.to_numeric(_str_col(df, quant_col, "0"), errors="coerce").fillna(0).astype(int)
        df["ESTACAO"]    = _str_col(df, estacao_col, "SEM ESTACAO")
        df["OP"]         = _str_col(df, op_col, "SEM OP")
        df["COR"]        = _str_col(df, cor_col)
        df["PRODUTO"]    = _str_col(df, prod_col)
        df["TAMANHO"]    = _str_col(df, tam_col)
        df["OBS"]        = _str_col(df, obs_col)
        df = df[df["QUANTIDADE"] > 0].copy()
    _raw["are"] = df
    return _raw["are"]

def carregar_manta_arealva(dia: date) -> pd.DataFrame:
    df = _raw_manta_arealva()
    if df.empty:
        return df
    return df[df["DATA"].dt.date == dia].copy()

def carregar_manta_arealva_range(d_ini: date, d_fim: date) -> pd.DataFrame:
    df = _raw_manta_arealva()
    if df.empty:
        return df
    return df[(df["DATA"].dt.date >= d_ini) & (df["DATA"].dt.date <= d_fim)].copy()

def _raw_manta_iacanga() -> pd.DataFrame:
    if "iac" in _raw:
        return _raw["iac"]
    df = _baixar_csv(SHEET_MANTA_IACANGA_ID, SHEET_MANTA_IACANGA_GID)
    if df is None:
        logging.error("Não foi possível baixar Manta Iacanga.")
        _raw["iac"] = pd.DataFrame()
        return _raw["iac"]
    df.columns = df.columns.str.strip().str.upper()
    df = _parse_datas(df)
    if not df.empty:
        quant_col   = _find_col(df, "QUANTIDADE")
        estacao_col = _find_col(df, "ESTA", "CORTE")
        op_col      = _find_col(df, "OP")
        cor_col     = _find_col_exact(df, "COR")
        prod_col    = _find_col(df, "PRODUTO")
        tam_col     = _find_col(df, "TAMANHO")
        cliente_col = _find_col(df, "CLIENTE")
        obs_col     = _find_col(df, "OBSERVA")
        df["QUANTIDADE"] = pd.to_numeric(_str_col(df, quant_col, "0"), errors="coerce").fillna(0).astype(int)
        df["ESTACAO"]    = _str_col(df, estacao_col, "SEM ESTACAO")
        df["OP"]         = _str_col(df, op_col, "SEM OP")
        df["COR"]        = _str_col(df, cor_col)
        df["PRODUTO"]    = _str_col(df, prod_col)
        df["TAMANHO"]    = _str_col(df, tam_col)
        df["CLIENTE"]    = _str_col(df, cliente_col)
        df["OBS"]        = _str_col(df, obs_col)
        df = df[df["QUANTIDADE"] > 0].copy()
    _raw["iac"] = df
    return _raw["iac"]

def carregar_manta_iacanga(dia: date) -> pd.DataFrame:
    df = _raw_manta_iacanga()
    if df.empty:
        return df
    return df[df["DATA"].dt.date == dia].copy()

def carregar_manta_iacanga_range(d_ini: date, d_fim: date) -> pd.DataFrame:
    df = _raw_manta_iacanga()
    if df.empty:
        return df
    return df[(df["DATA"].dt.date >= d_ini) & (df["DATA"].dt.date <= d_fim)].copy()

def _raw_lencol_arealva() -> pd.DataFrame:
    if "len" in _raw:
        return _raw["len"]
    urls = [
        f"https://docs.google.com/spreadsheets/d/{SHEET_LENCOL_ID}/export?format=csv&gid={SHEET_LENCOL_GID}",
        f"https://docs.google.com/spreadsheets/d/{SHEET_LENCOL_ID}/export?format=csv",
    ]
    texto = None
    for url in urls:
        try:
            r = requests.get(url, timeout=30, headers=HEADERS)
            r.encoding = "utf-8"
            if r.status_code == 200 and len(r.text) > 100:
                texto = r.text
                break
        except Exception as e:
            logging.warning(f"Falha lençol {url[:60]}: {e}")
    if not texto:
        logging.error("Não foi possível baixar Lençol Arealva.")
        _raw["len"] = pd.DataFrame()
        return _raw["len"]

    linhas = texto.splitlines()
    header_row = 0
    for i, linha in enumerate(linhas[:6]):
        if "DATA" in linha.upper() and "PRESTADOR" in linha.upper():
            header_row = i
            break

    df_raw = pd.read_csv(io.StringIO(texto), skiprows=header_row, header=0, dtype=str)

    # Mapeia colunas pelo NOME do cabeçalho (não por posição fixa). A planilha já
    # mudou de estrutura no passado (ex.: coluna "RETALHO" removida), o que
    # desalinhava tudo quando o código assumia índices fixos.
    data_col     = _find_col(df_raw, "DATA")
    prest_col    = _find_col(df_raw, "PRESTADOR")
    op_col       = _find_col_exact(df_raw, "OP")
    cat_col      = _find_col(df_raw, "CATEGORIA")
    emp_col      = _find_col(df_raw, "EMPRESA") or _find_col(df_raw, "EMPESA")
    tecido_col   = _find_col(df_raw, "TECIDO")
    valor_pc_col = _find_col(df_raw, "R$", "PE")
    quant_col    = _find_col_exact(df_raw, "QUANT")
    valor_rc_col = _find_col(df_raw, "RECEBER")
    retalho_col  = _find_col(df_raw, "RETALHO")
    obs_col      = _find_col(df_raw, "OBSERVA")

    df = pd.DataFrame({
        "DATA":          _str_col(df_raw, data_col),
        "PRESTADOR":     _str_col(df_raw, prest_col),
        "OP":            _str_col(df_raw, op_col),
        "CATEGORIA":     _str_col(df_raw, cat_col),
        "EMPRESA":       _str_col(df_raw, emp_col),
        "TECIDO":        _str_col(df_raw, tecido_col),
        "VALOR_PECA":    _str_col(df_raw, valor_pc_col),
        "QUANT":         _str_col(df_raw, quant_col),
        "VALOR_RECEBER": _str_col(df_raw, valor_rc_col),
        "RETALHO_KG":    _str_col(df_raw, retalho_col),
        "OBS":           _str_col(df_raw, obs_col),
    })
    # Planilha Lençol Arealva usa formato americano M/D/AAAA (ex.: "1/7/2026" = 7 de janeiro)
    df = _parse_datas(df, dayfirst=False)

    def _parse_brl(s):
        s = str(s).strip()
        if not s or s.lower() in ("nan", "none"):
            return 0.0
        try:
            return float(s.replace("R$", "").replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    if not df.empty:
        df["QUANT"]         = pd.to_numeric(df["QUANT"].astype(str).str.replace(",", ""), errors="coerce").fillna(0).astype(int)
        df["VALOR_PECA"]    = df["VALOR_PECA"].apply(_parse_brl)
        df["VALOR_RECEBER"] = df["VALOR_RECEBER"].apply(_parse_brl)
        df["RETALHO_KG"]    = df["RETALHO_KG"].apply(_parse_brl)
        invalidos = {"", "NAN", "NONE", "N/A", "NAO", "NAO INFORMADO"}
        df = df[~df["PRESTADOR"].str.strip().str.upper().isin(invalidos)]
        df["OP"]        = df["OP"].replace("", "SEM OP").astype(str).str.strip()
        df["CATEGORIA"] = df["CATEGORIA"].astype(str).str.strip()
        df["EMPRESA"]   = df["EMPRESA"].astype(str).str.strip().str.upper()
        df["TECIDO"]    = df["TECIDO"].astype(str).str.strip()
        df["OBS"]       = df["OBS"].astype(str).str.strip()
        mask0 = df["VALOR_RECEBER"] == 0
        df.loc[mask0, "VALOR_RECEBER"] = df.loc[mask0, "QUANT"] * df.loc[mask0, "VALOR_PECA"]
        df = df[df["QUANT"] > 0].copy()
    _raw["len"] = df
    return _raw["len"]

def carregar_lencol_arealva(dia: date) -> pd.DataFrame:
    df = _raw_lencol_arealva()
    if df.empty:
        return df
    return df[df["DATA"].dt.date == dia].copy()

def carregar_lencol_arealva_range(d_ini: date, d_fim: date) -> pd.DataFrame:
    df = _raw_lencol_arealva()
    if df.empty:
        return df
    return df[(df["DATA"].dt.date >= d_ini) & (df["DATA"].dt.date <= d_fim)].copy()

# geração de HTML
# Paleta e escala tipográfica dos PDFs de corte (diário + consolidado) —
# centralizada aqui pra manter os blocos (_bloco_pdf_manta, _bloco_pdf_lencol,
# _tabela_meta_setor etc.) visualmente consistentes. Redesenho pedido pelo
# usuário 20/07/2026: números pequenos e blocos colados demais no PDF
# consolidado — números maiores, mais respiro entre elementos, cores de
# destaque por setor.
_PDF = {
    "navy":    "#1a237e",
    "blue":    "#1565c0",
    "teal":    "#00897b",
    "amber":   "#ef6c00",
    "slate":   "#37474f",
    "ink":     "#1e293b",
    "muted":   "#64748b",
    "border":  "#dde3ee",
    "head_bg": "#eef1f8",
    "row_alt": "#f8fafc",
    "green":   "#2e7d32",
    "yellow":  "#b8860b",
    "red":     "#c62828",
}


def _v(val: str) -> str:
    # retorna valor limpo ou traço se vazio
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "") else "—"

def _bloco_manta_arealva(df: pd.DataFrame) -> str:
    titulo, emoji = "MANTA AREALVA", "🏭"
    if df.empty:
        return (
            f'<div class="setor"><div class="setor-header">{emoji} {titulo}</div>'
            f'<div class="sem-producao">⚠️ Sem produção registrada</div></div>'
        )
    total_setor = 0
    blocos = ""
    for estacao, grupo in df.groupby("ESTACAO", sort=True):
        subtotal = int(grupo["QUANTIDADE"].sum())
        total_setor += subtotal
        linhas = ""
        for _, r in grupo.sort_values("OP").iterrows():
            obs = f'<td>{_v(r["OBS"])}</td>' if _v(r["OBS"]) != "—" else "<td>—</td>"
            linhas += (
                f'<tr>'
                f'<td>{_v(r["OP"])}</td>'
                f'<td>{_v(r["PRODUTO"])}</td>'
                f'<td>{_v(r["TAMANHO"])}</td>'
                f'<td>{_v(r["COR"])}</td>'
                f'<td class="qtd">{int(r["QUANTIDADE"]):,}</td>'
                f'{obs}'
                f'</tr>'
            )
        blocos += (
            f'<div class="colaborador-header">📍 {estacao}</div>'
            f'<table><thead><tr>'
            f'<th>OP</th><th>Produto</th><th>Tamanho</th><th>Estacao / Material</th><th>Qtd</th><th>Observação</th>'
            f'</tr></thead><tbody>{linhas}</tbody></table>'
            f'<div class="subtotal">Subtotal {estacao}: <strong>{subtotal:,} peças</strong></div>'
        )
    return (
        f'<div class="setor"><div class="setor-header">{emoji} {titulo}</div>'
        f'{blocos}'
        f'<div class="total-setor">TOTAL {titulo}: {total_setor:,} peças</div></div>'
    )

def _bloco_manta_iacanga(df: pd.DataFrame) -> str:
    titulo, emoji = "MANTA IACANGA", "✂️"
    if df.empty:
        return (
            f'<div class="setor"><div class="setor-header">{emoji} {titulo}</div>'
            f'<div class="sem-producao">⚠️ Sem produção registrada</div></div>'
        )
    total_setor = 0
    blocos = ""
    for estacao, grupo in df.groupby("ESTACAO", sort=True):
        subtotal = int(grupo["QUANTIDADE"].sum())
        total_setor += subtotal
        linhas = ""
        for _, r in grupo.sort_values("OP").iterrows():
            linhas += (
                f'<tr>'
                f'<td>{_v(r["OP"])}</td>'
                f'<td>{_v(r["CLIENTE"])}</td>'
                f'<td>{_v(r["PRODUTO"])}</td>'
                f'<td>{_v(r["TAMANHO"])}</td>'
                f'<td>{_v(r["COR"])}</td>'
                f'<td class="qtd">{int(r["QUANTIDADE"]):,}</td>'
                f'<td>{_v(r["OBS"])}</td>'
                f'</tr>'
            )
        blocos += (
            f'<div class="colaborador-header">📍 {estacao}</div>'
            f'<table><thead><tr>'
            f'<th>OP</th><th>Cliente</th><th>Produto</th><th>Tamanho</th><th>Cor</th><th>Qtd</th><th>Observação</th>'
            f'</tr></thead><tbody>{linhas}</tbody></table>'
            f'<div class="subtotal">Subtotal {estacao}: <strong>{subtotal:,} peças</strong></div>'
        )
    return (
        f'<div class="setor"><div class="setor-header">{emoji} {titulo}</div>'
        f'{blocos}'
        f'<div class="total-setor">TOTAL {titulo}: {total_setor:,} peças</div></div>'
    )

def _bloco_lencol(df: pd.DataFrame) -> str:
    titulo, emoji = "LENÇOL AREALVA", "✂️"
    if df.empty:
        return (
            f'<div class="setor"><div class="setor-header">{emoji} {titulo}</div>'
            f'<div class="sem-producao">⚠️ Sem produção registrada</div></div>'
        )
    total_setor = 0
    total_valor = 0.0
    blocos = ""
    for prestador, grupo in df.groupby("PRESTADOR", sort=True):
        subtotal     = int(grupo["QUANT"].sum())
        sub_valor    = grupo["VALOR_RECEBER"].sum()
        total_setor += subtotal
        total_valor += sub_valor
        linhas = ""
        for _, r in grupo.sort_values("OP").iterrows():
            vp  = f'R$ {r["VALOR_PECA"]:.2f}'.replace(".", ",") if r["VALOR_PECA"] else "—"
            vr  = f'R$ {r["VALOR_RECEBER"]:.2f}'.replace(".", ",") if r["VALOR_RECEBER"] else "—"
            ret = f'{r["RETALHO_KG"]:.2f} kg'.replace(".", ",") if r["RETALHO_KG"] else "—"
            linhas += (
                f'<tr>'
                f'<td>{_v(r["OP"])}</td>'
                f'<td>{_v(r["CATEGORIA"])}</td>'
                f'<td>{_v(r["EMPRESA"])}</td>'
                f'<td>{_v(r["TECIDO"])}</td>'
                f'<td class="qtd">{int(r["QUANT"]):,}</td>'
                f'<td class="qtd">{vp}</td>'
                f'<td class="qtd">{vr}</td>'
                f'<td class="qtd">{ret}</td>'
                f'<td>{_v(r["OBS"])}</td>'
                f'</tr>'
            )
        blocos += (
            f'<div class="colaborador-header">👤 {prestador}</div>'
            f'<table><thead><tr>'
            f'<th>OP</th><th>Categoria</th><th>Empresa</th><th>Tecido</th>'
            f'<th>Qtd</th><th>R$/peça</th><th>Total R$</th><th>Retalho</th><th>OBS</th>'
            f'</tr></thead><tbody>{linhas}</tbody></table>'
            f'<div class="subtotal">'
            f'Subtotal {prestador}: <strong>{subtotal:,} peças</strong> · '
            f'<strong>R$ {sub_valor:,.2f}</strong>'
            f'</div>'
        )
    tv_fmt = f'R$ {total_valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
    return (
        f'<div class="setor"><div class="setor-header">{emoji} {titulo}</div>'
        f'{blocos}'
        f'<div class="total-setor">TOTAL {titulo}: {total_setor:,} peças · {tv_fmt}</div></div>'
    )

def gerar_html(dia: date, df_manta_are: pd.DataFrame, df_manta_iac: pd.DataFrame, df_lencol: pd.DataFrame) -> str:
    total_manta_are = int(df_manta_are["QUANTIDADE"].sum()) if not df_manta_are.empty else 0
    total_manta_iac = int(df_manta_iac["QUANTIDADE"].sum()) if not df_manta_iac.empty else 0
    total_lencol    = int(df_lencol["QUANT"].sum())         if not df_lencol.empty    else 0
    total_geral     = total_manta_are + total_manta_iac + total_lencol

    ops = set()
    for df_, col in [(df_manta_are, "OP"), (df_manta_iac, "OP"), (df_lencol, "OP")]:
        if not df_.empty:
            ops.update(df_[col].unique())
    total_ops = len(ops)

    # Destaques
    setores = {
        "Manta Arealva": total_manta_are,
        "Manta Iacanga": total_manta_iac,
        "Lençol Arealva": total_lencol,
    }
    setor_destaque     = max(setores, key=setores.get)
    setor_destaque_qtd = setores[setor_destaque]

    colaboradores: dict[str, int] = {}
    if not df_manta_are.empty:
        for est, g in df_manta_are.groupby("ESTACAO"):
            colaboradores[f"{est} (Arealva)"] = int(g["QUANTIDADE"].sum())
    if not df_manta_iac.empty:
        for est, g in df_manta_iac.groupby("ESTACAO"):
            colaboradores[f"{est} (Iacanga)"] = int(g["QUANTIDADE"].sum())
    if not df_lencol.empty:
        for prest, g in df_lencol.groupby("PRESTADOR"):
            colaboradores[prest] = int(g["QUANT"].sum())

    col_destaque     = max(colaboradores, key=colaboradores.get) if colaboradores else "—"
    col_destaque_qtd = colaboradores.get(col_destaque, 0)

    data_fmt = dia.strftime("%d/%m/%Y")
    dias_pt  = ["Segunda-feira", "Terça-feira", "Quarta-feira",
                "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_semana = dias_pt[dia.weekday()]

    bloco_manta_are = _bloco_manta_arealva(df_manta_are)
    bloco_manta_iac = _bloco_manta_iacanga(df_manta_iac)
    bloco_lencol    = _bloco_lencol(df_lencol)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Corte — {data_fmt}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:Arial,sans-serif;font-size:11px;color:#1a1a1a;background:#fff;}}
  @media print{{
    body{{font-size:10px;}}
    .setor{{page-break-inside:avoid;}}
  }}
  .container{{max-width:190mm;margin:0 auto;padding:8mm 10mm;}}

  /* Header */
  .header{{border-bottom:3px solid #1a237e;padding-bottom:8px;margin-bottom:10px;}}
  .header-top{{display:flex;justify-content:space-between;align-items:flex-start;}}
  .empresa{{font-size:15px;font-weight:bold;color:#1a237e;}}
  .titulo{{font-size:12px;font-weight:bold;color:#333;margin-top:2px;letter-spacing:.3px;}}
  .data-box{{text-align:right;}}
  .data-principal{{font-size:14px;font-weight:bold;color:#1a237e;}}
  .data-sub{{font-size:9px;color:#666;margin-top:2px;}}

  /* KPIs */
  .resumo{{display:flex;gap:6px;margin-bottom:10px;}}
  .kpi{{flex:1;background:#f0f4ff;border:1px solid #c5cae9;border-radius:4px;padding:5px 6px;text-align:center;}}
  .kpi-valor{{font-size:16px;font-weight:bold;color:#1a237e;}}
  .kpi-label{{font-size:8px;color:#555;text-transform:uppercase;letter-spacing:.4px;margin-top:1px;}}

  /* Setores */
  .setor{{margin-bottom:10px;border:1px solid #ccc;border-radius:4px;overflow:hidden;}}
  .setor-header{{background:#1a237e;color:#fff;font-size:11px;font-weight:bold;padding:5px 10px;letter-spacing:.5px;}}
  .colaborador-header{{background:#e8eaf6;color:#1a237e;font-size:10px;font-weight:bold;padding:3px 10px;border-top:1px solid #c5cae9;}}
  .sem-producao{{padding:10px;color:#999;font-style:italic;text-align:center;}}

  /* Tabela */
  table{{width:100%;border-collapse:collapse;}}
  th{{background:#f5f5f5;text-align:left;padding:3px 8px;font-size:9px;text-transform:uppercase;color:#555;border-bottom:1px solid #ddd;}}
  td{{padding:3px 8px;border-bottom:1px solid #f0f0f0;font-size:10px;}}
  tr:last-child td{{border-bottom:none;}}
  tr:nth-child(even) td{{background:#fafafa;}}
  td.qtd{{text-align:right;font-weight:bold;color:#1a237e;}}

  /* Subtotais */
  .subtotal{{background:#e3f2fd;padding:3px 10px;font-size:10px;color:#1565c0;text-align:right;border-top:1px solid #bbdefb;}}
  .total-setor{{background:#1a237e;color:#fff;padding:4px 10px;font-size:11px;font-weight:bold;text-align:right;}}

  /* Destaques */
  .destaques{{background:#fff8e1;border:2px solid #ffc107;border-radius:4px;padding:8px 10px;margin-top:10px;}}
  .destaques-titulo{{font-size:11px;font-weight:bold;color:#e65100;margin-bottom:5px;}}
  .d-item{{display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px dashed #ffe082;font-size:10px;}}
  .d-item:last-child{{border-bottom:none;}}
  .d-label{{color:#555;}}
  .d-valor{{font-weight:bold;color:#e65100;}}

  /* Footer */
  .footer{{margin-top:10px;padding-top:6px;border-top:1px solid #ddd;font-size:8px;color:#aaa;display:flex;justify-content:space-between;}}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="header-top">
      <div>
        <div class="empresa">🏢 ZANATTEX</div>
        <div class="titulo">RELATÓRIO DIÁRIO DE PRODUÇÃO DE CORTE</div>
      </div>
      <div class="data-box">
        <div class="data-principal">{data_fmt}</div>
        <div class="data-sub">{dia_semana} · Referência: dia anterior</div>
      </div>
    </div>
  </div>

  <div class="resumo">
    <div class="kpi"><div class="kpi-valor">{total_geral:,}</div><div class="kpi-label">Total Geral</div></div>
    <div class="kpi"><div class="kpi-valor">{total_ops}</div><div class="kpi-label">Total OPs</div></div>
    <div class="kpi"><div class="kpi-valor">{total_manta_are:,}</div><div class="kpi-label">Manta Arealva</div></div>
    <div class="kpi"><div class="kpi-valor">{total_manta_iac:,}</div><div class="kpi-label">Manta Iacanga</div></div>
    <div class="kpi"><div class="kpi-valor">{total_lencol:,}</div><div class="kpi-label">Lençol Arealva</div></div>
  </div>

  {bloco_manta_are}
  {bloco_manta_iac}
  {bloco_lencol}

  <div class="destaques">
    <div class="destaques-titulo">⭐ DESTAQUES DO DIA</div>
    <div class="d-item">
      <span class="d-label">🏆 Total cortado no dia</span>
      <span class="d-valor">{total_geral:,} peças</span>
    </div>
    <div class="d-item">
      <span class="d-label">🥇 Setor destaque</span>
      <span class="d-valor">{setor_destaque} — {setor_destaque_qtd:,} peças</span>
    </div>
    <div class="d-item">
      <span class="d-label">👤 Colaborador / Estação destaque</span>
      <span class="d-valor">{col_destaque} — {col_destaque_qtd:,} peças</span>
    </div>
  </div>

  <div class="footer">
    <span>Gerado automaticamente · Sistema Zanattex</span>
  </div>

</div>
</body>
</html>"""

# geração de PDF
def _bloco_pdf_manta(titulo: str, df: pd.DataFrame, col_qtd: str = "QUANTIDADE") -> str:
    if df.empty:
        return (
            f'<table width="100%" style="margin-bottom:10px;border-collapse:collapse;">'
            f'<tr><td style="background:{_PDF["navy"]};color:#fff;font-weight:bold;padding:7px 12px;font-size:11px;">'
            f'{titulo}</td></tr>'
            f'<tr><td style="padding:12px;color:#888;font-style:italic;font-size:10px;border:1px solid {_PDF["border"]};border-top:none;">'
            f'Sem producao registrada</td></tr></table>'
        )
    total_setor = int(df[col_qtd].sum())
    blocos = (
        f'<table width="100%" style="margin-bottom:4px;border-collapse:collapse;">'
        f'<tr><td style="background:{_PDF["navy"]};color:#fff;font-weight:bold;padding:7px 12px;font-size:11px;">'
        f'{titulo}</td></tr></table>'
    )
    tem_cliente = "CLIENTE" in df.columns
    for estacao, grupo in df.groupby("ESTACAO", sort=True):
        subtotal = int(grupo[col_qtd].sum())
        blocos += (
            f'<table width="100%" style="margin:6px 0 0 0;border-collapse:collapse;">'
            f'<tr><td style="background:{_PDF["head_bg"]};color:{_PDF["navy"]};font-weight:bold;'
            f'padding:5px 10px;font-size:9.5px;letter-spacing:0.3px;">ESTACAO: {estacao}</td></tr></table>'
        )
        # cabeçalho da tabela
        th = f'background:{_PDF["head_bg"]};border:1px solid {_PDF["border"]};padding:5px 8px;font-size:8.5px;text-align:left;color:{_PDF["slate"]};text-transform:uppercase;letter-spacing:0.3px;'
        td_s = f'border:1px solid {_PDF["border"]};padding:4px 8px;font-size:9.5px;color:{_PDF["ink"]};'
        td_r = td_s + f'text-align:right;font-weight:bold;color:{_PDF["navy"]};'
        if tem_cliente:
            header = (f'<tr><th style="{th}">OP</th><th style="{th}">Cliente</th>'
                      f'<th style="{th}">Produto</th><th style="{th}">Tamanho</th>'
                      f'<th style="{th}">Cor</th><th style="{th}">Qtd</th>'
                      f'<th style="{th}">Observacao</th></tr>')
        else:
            header = (f'<tr><th style="{th}">OP</th><th style="{th}">Produto</th>'
                      f'<th style="{th}">Tamanho</th><th style="{th}">Cor</th>'
                      f'<th style="{th}">Qtd</th><th style="{th}">Observacao</th></tr>')
        linhas = ""
        for i, (_, r) in enumerate(grupo.sort_values("OP").iterrows()):
            bg = f'background:{_PDF["row_alt"]};' if i % 2 else ""
            if tem_cliente:
                linhas += (
                    f'<tr style="{bg}">'
                    f'<td style="{td_s}">{_v(r["OP"])}</td>'
                    f'<td style="{td_s}">{_v(r["CLIENTE"])}</td>'
                    f'<td style="{td_s}">{_v(r["PRODUTO"])}</td>'
                    f'<td style="{td_s}">{_v(r["TAMANHO"])}</td>'
                    f'<td style="{td_s}">{_v(r["COR"])}</td>'
                    f'<td style="{td_r}">{int(r[col_qtd]):,}</td>'
                    f'<td style="{td_s}">{_v(r["OBS"])}</td>'
                    f'</tr>'
                )
            else:
                linhas += (
                    f'<tr style="{bg}">'
                    f'<td style="{td_s}">{_v(r["OP"])}</td>'
                    f'<td style="{td_s}">{_v(r["PRODUTO"])}</td>'
                    f'<td style="{td_s}">{_v(r["TAMANHO"])}</td>'
                    f'<td style="{td_s}">{_v(r["COR"])}</td>'
                    f'<td style="{td_r}">{int(r[col_qtd]):,}</td>'
                    f'<td style="{td_s}">{_v(r["OBS"])}</td>'
                    f'</tr>'
                )
        blocos += (
            f'<table width="100%" style="border-collapse:collapse;margin-bottom:4px;">'
            f'<thead>{header}</thead><tbody>{linhas}</tbody></table>'
            f'<p style="text-align:right;font-size:9.5px;color:{_PDF["blue"]};'
            f'background:#e3f2fd;padding:4px 10px;margin:0 0 8px 0;">'
            f'Subtotal {estacao}: <b>{subtotal:,} pecas</b></p>'
        )
    blocos += (
        f'<p style="text-align:right;font-size:10px;font-weight:bold;color:#fff;'
        f'background:{_PDF["navy"]};padding:6px 10px;margin:0 0 14px 0;">'
        f'TOTAL {titulo}: {total_setor:,} pecas</p>'
    )
    return blocos

def _bloco_pdf_lencol(df: pd.DataFrame) -> str:
    titulo = "LENCOL AREALVA"
    if df.empty:
        return (
            f'<table width="100%" style="margin-bottom:10px;border-collapse:collapse;">'
            f'<tr><td style="background:{_PDF["navy"]};color:#fff;font-weight:bold;padding:7px 12px;font-size:11px;">'
            f'{titulo}</td></tr>'
            f'<tr><td style="padding:12px;color:#888;font-style:italic;font-size:10px;border:1px solid {_PDF["border"]};border-top:none;">'
            f'Sem producao registrada</td></tr></table>'
        )
    total_setor = int(df["QUANT"].sum())
    total_valor = df["VALOR_RECEBER"].sum()
    blocos = (
        f'<table width="100%" style="margin-bottom:4px;border-collapse:collapse;">'
        f'<tr><td style="background:{_PDF["navy"]};color:#fff;font-weight:bold;padding:7px 12px;font-size:11px;">'
        f'{titulo}</td></tr></table>'
    )
    th = f'background:{_PDF["head_bg"]};border:1px solid {_PDF["border"]};padding:5px 7px;font-size:8.5px;text-align:left;color:{_PDF["slate"]};text-transform:uppercase;letter-spacing:0.3px;'
    td_s = f'border:1px solid {_PDF["border"]};padding:4px 7px;font-size:9.5px;color:{_PDF["ink"]};'
    td_r = td_s + f'text-align:right;font-weight:bold;color:{_PDF["navy"]};'
    for prestador, grupo in df.groupby("PRESTADOR", sort=True):
        subtotal  = int(grupo["QUANT"].sum())
        sub_valor = grupo["VALOR_RECEBER"].sum()
        header = (
            f'<tr>'
            f'<th style="{th}">OP</th><th style="{th}">Categoria</th>'
            f'<th style="{th}">Empresa</th><th style="{th}">Tecido</th>'
            f'<th style="{th}">Qtd</th><th style="{th}">R$/peca</th>'
            f'<th style="{th}">Total R$</th><th style="{th}">Retalho</th>'
            f'<th style="{th}">OBS</th></tr>'
        )
        linhas = ""
        for i, (_, r) in enumerate(grupo.sort_values("OP").iterrows()):
            bg = f'background:{_PDF["row_alt"]};' if i % 2 else ""
            vp  = f'R$ {r["VALOR_PECA"]:.2f}'.replace(".", ",") if r["VALOR_PECA"] else "-"
            vr  = f'R$ {r["VALOR_RECEBER"]:.2f}'.replace(".", ",") if r["VALOR_RECEBER"] else "-"
            ret = f'{r["RETALHO_KG"]:.2f} kg'.replace(".", ",") if r["RETALHO_KG"] else "-"
            linhas += (
                f'<tr style="{bg}">'
                f'<td style="{td_s}">{_v(r["OP"])}</td>'
                f'<td style="{td_s}">{_v(r["CATEGORIA"])}</td>'
                f'<td style="{td_s}">{_v(r["EMPRESA"])}</td>'
                f'<td style="{td_s}">{_v(r["TECIDO"])}</td>'
                f'<td style="{td_r}">{int(r["QUANT"]):,}</td>'
                f'<td style="{td_r}">{vp}</td>'
                f'<td style="{td_r}">{vr}</td>'
                f'<td style="{td_r}">{ret}</td>'
                f'<td style="{td_s}">{_v(r["OBS"])}</td>'
                f'</tr>'
            )
        sv_fmt = f'R$ {sub_valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
        blocos += (
            f'<p style="background:{_PDF["head_bg"]};color:{_PDF["navy"]};font-weight:bold;'
            f'font-size:9.5px;padding:5px 10px;margin:6px 0 0 0;">Prestador: {prestador}</p>'
            f'<table width="100%" style="border-collapse:collapse;margin-bottom:4px;">'
            f'<thead>{header}</thead><tbody>{linhas}</tbody></table>'
            f'<p style="text-align:right;font-size:9.5px;color:{_PDF["blue"]};'
            f'background:#e3f2fd;padding:4px 10px;margin:0 0 8px 0;">'
            f'Subtotal {prestador}: <b>{subtotal:,} pecas</b> &nbsp;|&nbsp; <b>{sv_fmt}</b></p>'
        )
    tv_fmt = f'R$ {total_valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
    blocos += (
        f'<p style="text-align:right;font-size:10px;font-weight:bold;color:#fff;'
        f'background:{_PDF["navy"]};padding:6px 10px;margin:0 0 14px 0;">'
        f'TOTAL {titulo}: {total_setor:,} pecas &nbsp;|&nbsp; {tv_fmt}</p>'
    )
    return blocos

def gerar_pdf(dia: date, df_manta_are: pd.DataFrame, df_manta_iac: pd.DataFrame, df_lencol: pd.DataFrame) -> bytes:
    from xhtml2pdf import pisa

    total_manta_are = int(df_manta_are["QUANTIDADE"].sum()) if not df_manta_are.empty else 0
    total_manta_iac = int(df_manta_iac["QUANTIDADE"].sum()) if not df_manta_iac.empty else 0
    total_lencol    = int(df_lencol["QUANT"].sum())         if not df_lencol.empty    else 0
    total_geral     = total_manta_are + total_manta_iac + total_lencol

    ops: set[str] = set()
    for df_, col in [(df_manta_are, "OP"), (df_manta_iac, "OP"), (df_lencol, "OP")]:
        if not df_.empty:
            ops.update(df_[col].unique())

    setores = {"Manta Arealva": total_manta_are, "Manta Iacanga": total_manta_iac, "Lencol Arealva": total_lencol}
    setor_destaque = max(setores, key=setores.get)

    colaboradores: dict[str, int] = {}
    if not df_manta_are.empty:
        for est, g in df_manta_are.groupby("ESTACAO"):
            colaboradores[f"{est} (Arealva)"] = int(g["QUANTIDADE"].sum())
    if not df_manta_iac.empty:
        for est, g in df_manta_iac.groupby("ESTACAO"):
            colaboradores[f"{est} (Iacanga)"] = int(g["QUANTIDADE"].sum())
    if not df_lencol.empty:
        for prest, g in df_lencol.groupby("PRESTADOR"):
            colaboradores[prest] = int(g["QUANT"].sum())
    col_destaque     = max(colaboradores, key=colaboradores.get) if colaboradores else "-"
    col_destaque_qtd = colaboradores.get(col_destaque, 0)

    data_fmt   = dia.strftime("%d/%m/%Y")
    dias_pt    = ["Segunda-feira", "Terca-feira", "Quarta-feira",
                  "Quinta-feira", "Sexta-feira", "Sabado", "Domingo"]
    dia_semana = dias_pt[dia.weekday()]

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4 portrait; margin: 12mm 10mm; }}
  body {{ font-family: Arial, sans-serif; font-size: 10px; color: #1a1a1a; }}
  * {{ box-sizing: border-box; }}
</style>
</head>
<body>

<!-- HEADER -->
<table width="100%" style="border-bottom:2px solid #1a237e;margin-bottom:8px;padding-bottom:5px;">
  <tr>
    <td>
      <span style="font-size:15px;font-weight:bold;color:#1a237e;">ZANATTEX</span><br>
      <span style="font-size:11px;font-weight:bold;">RELATORIO DIARIO DE PRODUCAO DE CORTE</span>
    </td>
    <td align="right">
      <span style="font-size:14px;font-weight:bold;color:#1a237e;">{data_fmt}</span><br>
      <span style="font-size:9px;color:#666;">{dia_semana} &nbsp;|&nbsp; Referencia: dia anterior</span>
    </td>
  </tr>
</table>

<!-- KPIs -->
<table width="100%" style="border-collapse:collapse;margin-bottom:10px;">
  <tr>
    <td width="20%" align="center" style="background:#f0f4ff;border:1px solid #c5cae9;padding:5px;">
      <div style="font-size:16px;font-weight:bold;color:#1a237e;">{total_geral:,}</div>
      <div style="font-size:8px;color:#555;">TOTAL GERAL</div>
    </td>
    <td width="20%" align="center" style="background:#f0f4ff;border:1px solid #c5cae9;padding:5px;">
      <div style="font-size:16px;font-weight:bold;color:#1a237e;">{len(ops)}</div>
      <div style="font-size:8px;color:#555;">TOTAL OPs</div>
    </td>
    <td width="20%" align="center" style="background:#f0f4ff;border:1px solid #c5cae9;padding:5px;">
      <div style="font-size:16px;font-weight:bold;color:#1a237e;">{total_manta_are:,}</div>
      <div style="font-size:8px;color:#555;">MANTA AREALVA</div>
    </td>
    <td width="20%" align="center" style="background:#f0f4ff;border:1px solid #c5cae9;padding:5px;">
      <div style="font-size:16px;font-weight:bold;color:#1a237e;">{total_manta_iac:,}</div>
      <div style="font-size:8px;color:#555;">MANTA IACANGA</div>
    </td>
    <td width="20%" align="center" style="background:#f0f4ff;border:1px solid #c5cae9;padding:5px;">
      <div style="font-size:16px;font-weight:bold;color:#1a237e;">{total_lencol:,}</div>
      <div style="font-size:8px;color:#555;">LENCOL AREALVA</div>
    </td>
  </tr>
</table>

{_bloco_pdf_manta("MANTA AREALVA", df_manta_are)}
{_bloco_pdf_manta("MANTA IACANGA", df_manta_iac)}
{_bloco_pdf_lencol(df_lencol)}

<!-- DESTAQUES -->
<table width="100%" style="border-collapse:collapse;border:2px solid #ffc107;margin-top:6px;">
  <tr><td style="background:#fff8e1;padding:5px 8px;font-weight:bold;font-size:10px;color:#e65100;">
    DESTAQUES DO DIA
  </td></tr>
  <tr><td style="background:#fffde7;padding:3px 8px;font-size:9px;border-top:1px dashed #ffe082;">
    Total cortado no dia: <b>{total_geral:,} pecas</b>
  </td></tr>
  <tr><td style="background:#fffde7;padding:3px 8px;font-size:9px;border-top:1px dashed #ffe082;">
    Setor destaque: <b>{setor_destaque} &mdash; {setores[setor_destaque]:,} pecas</b>
  </td></tr>
  <tr><td style="background:#fffde7;padding:3px 8px;font-size:9px;border-top:1px dashed #ffe082;">
    Colaborador / Estacao destaque: <b>{col_destaque} &mdash; {col_destaque_qtd:,} pecas</b>
  </td></tr>
</table>

<!-- FOOTER -->
<p style="font-size:8px;color:#aaa;margin-top:8px;border-top:1px solid #ddd;padding-top:4px;">
  Gerado automaticamente &nbsp;|&nbsp; Sistema Zanattex
</p>

</body>
</html>"""

    buf = io.BytesIO()
    pisa.CreatePDF(html.encode("utf-8"), dest=buf, encoding="utf-8")
    return buf.getvalue()

# pdf consolidado com dia + mês + últimos 2 meses
_MESES_PT = ["Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

def _nome_mes(d: date) -> str:
    return f"{_MESES_PT[d.month - 1]}/{d.year}"

def _inicio_mes(d: date) -> date:
    return date(d.year, d.month, 1)

def _fim_mes(d: date) -> date:
    _, ultimo = monthrange(d.year, d.month)
    return date(d.year, d.month, ultimo)

def _mes_ant(d: date, n: int) -> date:
    m, y = d.month - n, d.year
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)

def _dias_uteis_simples(ini: date, fim: date) -> int:
    """Dias úteis (seg-sex) entre ini e fim, inclusive — sem feriados.

    Versão simplificada e autocontida: este script roda isolado (GitHub
    Actions, sem o pacote utils/ que depende do Streamlit), então não pode
    importar utils.feriados.contar_dias_uteis. Usada só pra estimar a Meta
    do Período (meta diária × dias úteis) no relatório consolidado — não
    precisa da precisão exata de feriados pra esse fim."""
    if fim < ini:
        return 0
    return sum(1 for i in range((fim - ini).days + 1) if (ini + timedelta(days=i)).weekday() < 5)

def _tabela_meta_setor(nome: str, meta_dia: float, dias: int, produzido: int) -> str:
    """Tabela 'Realizado x Meta' de um setor — 2 linhas (Producao do Periodo /
    Media Diaria) com Realizado, Meta e % Atingimento lado a lado, colorido.

    Mesma estrutura de analise da aba de Producao Diaria do dashboard ao vivo
    (pages/2_Producao_Geral.py::_tabela_resumo_meta), agora reaproveitada no
    PDF Consolidado de Corte pros 3 setores (Manta Arealva, Manta Iacanga,
    Lencol Arealva) — mesmos limiares de cor (verde >=100%, amarelo >=75%,
    vermelho <75%). Setor sem meta diaria cadastrada (meta_dia<=0 — caso do
    Lencol, que nao precisa de meta) mostra só o Realizado, sem comparacao
    inventada. Pedido do usuario 14/07/2026 (bloco original) e 16/07/2026
    (reaproveitar a mesma estrutura de analise da Producao Diaria)."""
    def _n(v: float) -> str:
        return f"{v:,.0f}".replace(",", ".")

    dias_ef      = max(dias, 1)
    media_dia    = produzido / dias_ef
    tem_meta     = meta_dia > 0
    meta_periodo = meta_dia * dias_ef

    def _cor(pct):
        if pct is None:
            return _PDF["muted"], _PDF["head_bg"]
        if pct >= 100:
            return _PDF["green"], "#e6f4ea"
        if pct >= 75:
            return _PDF["yellow"], "#fdf3dc"
        return _PDF["red"], "#fbe9e7"

    pct_periodo = (produzido / meta_periodo * 100) if (tem_meta and meta_periodo) else None
    pct_media   = (media_dia / meta_dia * 100) if tem_meta else None

    th = f'background:{_PDF["head_bg"]};border:1px solid {_PDF["border"]};padding:6px 9px;font-size:9px;text-align:left;color:{_PDF["slate"]};text-transform:uppercase;letter-spacing:0.3px;'
    td_s = f'border:1px solid {_PDF["border"]};padding:6px 9px;font-size:10.5px;color:{_PDF["ink"]};'
    td_r = td_s + "text-align:right;"

    def _linha(label, realizado, meta, pct):
        cor, bg  = _cor(pct)
        meta_txt = _n(meta) if tem_meta else "—"
        pct_txt  = f"{pct:.1f}%" if pct is not None else "—"
        return (
            f'<tr><td style="{td_s}">{label}</td>'
            f'<td style="{td_r}font-weight:bold;">{_n(realizado)}</td>'
            f'<td style="{td_r}color:{_PDF["muted"]};">{meta_txt}</td>'
            f'<td style="{td_r}">'
            f'<span style="background:{bg};color:{cor};font-weight:bold;padding:3px 9px;">{pct_txt}</span>'
            f'</td></tr>'
        )

    linhas = (
        _linha("Producao do Periodo", produzido, meta_periodo, pct_periodo)
        + _linha("Media Diaria", media_dia, meta_dia, pct_media)
    )
    obs = "" if tem_meta else (
        f'<p style="font-size:8px;color:{_PDF["muted"]};font-style:italic;padding:3px 9px;margin:0 0 10px 0;">'
        'Sem meta cadastrada para comparacao — mostrando apenas o realizado.</p>'
    )
    return (
        f'<p style="background:{_PDF["blue"]};color:#fff;font-weight:bold;padding:6px 10px;'
        f'font-size:10px;margin:10px 0 0 0;">{nome}</p>'
        f'<table width="100%" style="border-collapse:collapse;margin-bottom:{"10px" if tem_meta else "0"};">'
        f'<thead><tr><th style="{th}">Indicador</th><th style="{th}">Realizado</th>'
        f'<th style="{th}">Meta</th><th style="{th}">Atingimento</th></tr></thead>'
        f'<tbody>{linhas}</tbody></table>{obs}'
    )


def _bloco_meta_status(itens: list[tuple[str, float, int, int]]) -> str:
    """itens: lista de (nome_setor, meta_diaria, dias_uteis, produzido).

    Uma tabela 'Realizado x Meta' por setor (empilhadas), na mesma estrutura
    de analise da aba de Producao Diaria do dashboard ao vivo. Pedido do
    usuario 16/07/2026."""
    return "".join(
        _tabela_meta_setor(nome, meta_dia, dias, produzido)
        for nome, meta_dia, dias, produzido in itens
    )

def _bloco_resumo_manta(titulo: str, df: pd.DataFrame, col_qtd: str = "QUANTIDADE") -> str:
    th = f'background:{_PDF["head_bg"]};border:1px solid {_PDF["border"]};padding:5px 8px;font-size:8.5px;text-align:left;color:{_PDF["slate"]};text-transform:uppercase;letter-spacing:0.3px;'
    td_s = f'border:1px solid {_PDF["border"]};padding:4px 8px;font-size:9.5px;color:{_PDF["ink"]};'
    td_r = td_s + f'text-align:right;font-weight:bold;color:{_PDF["navy"]};'

    cabec = (
        f'<p style="background:{_PDF["blue"]};color:#fff;font-weight:bold;padding:6px 10px;'
        f'font-size:10px;margin:10px 0 0 0;">{titulo}</p>'
    )
    if df.empty:
        return cabec + f'<p style="color:#888;font-style:italic;font-size:9px;padding:6px 10px;margin:0 0 8px 0;">Sem producao no periodo</p>'

    total = int(df[col_qtd].sum())
    por_est = df.groupby("ESTACAO")[col_qtd].sum().sort_values(ascending=False)
    top_ops = df.groupby("OP").agg({col_qtd: "sum"}).sort_values(col_qtd, ascending=False).head(8)
    op_prod = df.groupby("OP")["PRODUTO"].first().to_dict() if "PRODUTO" in df.columns else {}

    linhas_est = ""
    for est, qtd in por_est.items():
        pct = int(qtd) * 100 // total if total else 0
        linhas_est += (
            f'<tr><td style="{td_s}">{est}</td>'
            f'<td style="{td_r}">{int(qtd):,}</td>'
            f'<td style="{td_r}">{pct}%</td></tr>'
        )

    linhas_op = ""
    for op, row in top_ops.iterrows():
        qtd = int(row[col_qtd])
        prod = _v(op_prod.get(op, ""))
        linhas_op += (
            f'<tr><td style="{td_s}">{op}</td>'
            f'<td style="{td_s}">{prod}</td>'
            f'<td style="{td_r}">{qtd:,}</td></tr>'
        )

    return (
        f'{cabec}'
        f'<p style="font-size:9.5px;font-weight:bold;color:{_PDF["navy"]};padding:4px 10px;margin:0;">Total: {total:,} pecas</p>'
        f'<table width="100%" style="border-collapse:collapse;margin-top:2px;">'
        f'<thead><tr><th style="{th}">Estacao</th><th style="{th}">Pecas</th><th style="{th}">%</th></tr></thead>'
        f'<tbody>{linhas_est}</tbody></table>'
        f'<p style="font-size:8px;color:{_PDF["muted"]};padding:4px 10px;background:{_PDF["head_bg"]};margin:4px 0 0 0;text-transform:uppercase;letter-spacing:0.3px;">Top OPs</p>'
        f'<table width="100%" style="border-collapse:collapse;margin-bottom:10px;">'
        f'<thead><tr><th style="{th}">OP</th><th style="{th}">Produto</th><th style="{th}">Qtd</th></tr></thead>'
        f'<tbody>{linhas_op}</tbody></table>'
    )

def _bloco_resumo_lencol(df: pd.DataFrame) -> str:
    th = f'background:{_PDF["head_bg"]};border:1px solid {_PDF["border"]};padding:5px 8px;font-size:8.5px;text-align:left;color:{_PDF["slate"]};text-transform:uppercase;letter-spacing:0.3px;'
    td_s = f'border:1px solid {_PDF["border"]};padding:4px 8px;font-size:9.5px;color:{_PDF["ink"]};'
    td_r = td_s + f'text-align:right;font-weight:bold;color:{_PDF["navy"]};'

    cabec = (
        f'<p style="background:{_PDF["blue"]};color:#fff;font-weight:bold;padding:6px 10px;'
        f'font-size:10px;margin:10px 0 0 0;">LENCOL AREALVA</p>'
    )
    if df.empty:
        return cabec + f'<p style="color:#888;font-style:italic;font-size:9px;padding:6px 10px;margin:0 0 8px 0;">Sem producao no periodo</p>'

    total = int(df["QUANT"].sum())
    total_val = df["VALOR_RECEBER"].sum()
    por_prest = df.groupby("PRESTADOR").agg({"QUANT": "sum", "VALOR_RECEBER": "sum"}).sort_values("QUANT", ascending=False)

    linhas_prest = ""
    for prest, row in por_prest.iterrows():
        qtd = int(row["QUANT"])
        pct = qtd * 100 // total if total else 0
        val_fmt = f'R$ {row["VALOR_RECEBER"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
        linhas_prest += (
            f'<tr><td style="{td_s}">{prest}</td>'
            f'<td style="{td_r}">{qtd:,}</td>'
            f'<td style="{td_r}">{pct}%</td>'
            f'<td style="{td_r}">{val_fmt}</td></tr>'
        )

    # Top OPs com material (TECIDO)
    top_ops = df.groupby("OP").agg({"QUANT": "sum", "VALOR_RECEBER": "sum"}).sort_values("QUANT", ascending=False).head(8)
    op_tecido = df.groupby("OP")["TECIDO"].first().to_dict() if "TECIDO" in df.columns else {}
    op_cat    = df.groupby("OP")["CATEGORIA"].first().to_dict() if "CATEGORIA" in df.columns else {}

    linhas_op = ""
    for op, row in top_ops.iterrows():
        qtd = int(row["QUANT"])
        val_fmt = f'R$ {row["VALOR_RECEBER"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
        tecido = _v(op_tecido.get(op, ""))
        cat    = _v(op_cat.get(op, ""))
        linhas_op += (
            f'<tr><td style="{td_s}">{op}</td>'
            f'<td style="{td_s}">{tecido}</td>'
            f'<td style="{td_s}">{cat}</td>'
            f'<td style="{td_r}">{qtd:,}</td>'
            f'<td style="{td_r}">{val_fmt}</td></tr>'
        )

    tv_fmt = f'R$ {total_val:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
    return (
        f'{cabec}'
        f'<p style="font-size:9.5px;font-weight:bold;color:{_PDF["navy"]};padding:4px 10px;margin:0;">Total: {total:,} pecas | {tv_fmt}</p>'
        f'<table width="100%" style="border-collapse:collapse;margin-top:2px;">'
        f'<thead><tr><th style="{th}">Prestador</th><th style="{th}">Pecas</th><th style="{th}">%</th><th style="{th}">Total R$</th></tr></thead>'
        f'<tbody>{linhas_prest}</tbody></table>'
        f'<p style="font-size:8px;color:{_PDF["muted"]};padding:4px 10px;background:{_PDF["head_bg"]};margin:4px 0 0 0;text-transform:uppercase;letter-spacing:0.3px;">Top OPs</p>'
        f'<table width="100%" style="border-collapse:collapse;margin-bottom:10px;">'
        f'<thead><tr><th style="{th}">OP</th><th style="{th}">Material</th><th style="{th}">Categoria</th><th style="{th}">Qtd</th><th style="{th}">Total R$</th></tr></thead>'
        f'<tbody>{linhas_op}</tbody></table>'
    )

def gerar_pdf_consolidado(
    dia: date,
    dia_ini: date | None = None,
    meta_diaria_arealva: float = 11000,
    meta_diaria_iacanga: float = 19000,
    meta_diaria_lencol: float = 0,
) -> bytes:
    """
    dia_ini : quando informado e diferente de `dia`, a seção 1 passa a somar
    o período [dia_ini, dia] (mesmo estilo resumido das seções de mês) em vez
    do detalhamento de um único dia — usado pela tela de Relatórios pra
    permitir um intervalo real. O e-mail diário automático não passa esse
    parâmetro, então continua idêntico (dia único, detalhado).

    meta_diaria_arealva / meta_diaria_iacanga / meta_diaria_lencol : meta
    diária (peças/dia) de cada setor de corte, usada pra calcular o corte
    médio/dia e a Meta do Período (meta diária × dias úteis) exibidos em
    cada seção. Valores default de Arealva/Iacanga = constantes hoje
    hardcoded em pages/10_Relatorios.py (_METAS_AREALVA_META_TOTAL / CASAL de
    _METAS_IACANGA); o caller da tela de Relatórios passa os valores reais
    explicitamente. Lençol não tem meta diária configurada no sistema (só
    meta por empresa/categoria na planilha METAS, sem recorte diário) —
    default 0, o que mostra o setor no bloco com os valores realizados mas
    sem comparação inventada; caller pode passar um valor real se/quando
    existir. Pedido do usuário 14/07/2026 (bloco original) e 16/07/2026
    (unificar Manta Arealva + Manta Iacanga + Lençol no mesmo bloco)."""
    from xhtml2pdf import pisa

    range_real = dia_ini is not None and dia_ini != dia

    mes_ini = _inicio_mes(dia)
    m1      = _mes_ant(dia, 1)
    m1_ini, m1_fim = _inicio_mes(m1), _fim_mes(m1)
    m2      = _mes_ant(dia, 2)
    m2_ini, m2_fim = _inicio_mes(m2), _fim_mes(m2)

    # Carregar (cacheado — mesmos objetos do relatório diário se já carregados)
    if range_real:
        are_dia = carregar_manta_arealva_range(dia_ini, dia)
        iac_dia = carregar_manta_iacanga_range(dia_ini, dia)
        len_dia = carregar_lencol_arealva_range(dia_ini, dia)
    else:
        are_dia = carregar_manta_arealva(dia)
        iac_dia = carregar_manta_iacanga(dia)
        len_dia = carregar_lencol_arealva(dia)

    are_mes = carregar_manta_arealva_range(mes_ini, dia)
    iac_mes = carregar_manta_iacanga_range(mes_ini, dia)
    len_mes = carregar_lencol_arealva_range(mes_ini, dia)

    are_m1  = carregar_manta_arealva_range(m1_ini, m1_fim)
    iac_m1  = carregar_manta_iacanga_range(m1_ini, m1_fim)
    len_m1  = carregar_lencol_arealva_range(m1_ini, m1_fim)

    are_m2  = carregar_manta_arealva_range(m2_ini, m2_fim)
    iac_m2  = carregar_manta_iacanga_range(m2_ini, m2_fim)
    len_m2  = carregar_lencol_arealva_range(m2_ini, m2_fim)

    def _tot(df, col):
        return int(df[col].sum()) if not df.empty else 0

    t_are_dia = _tot(are_dia, "QUANTIDADE"); t_iac_dia = _tot(iac_dia, "QUANTIDADE"); t_len_dia = _tot(len_dia, "QUANT")
    t_are_mes = _tot(are_mes, "QUANTIDADE"); t_iac_mes = _tot(iac_mes, "QUANTIDADE"); t_len_mes = _tot(len_mes, "QUANT")
    t_are_m1  = _tot(are_m1,  "QUANTIDADE"); t_iac_m1  = _tot(iac_m1,  "QUANTIDADE"); t_len_m1  = _tot(len_m1,  "QUANT")
    t_are_m2  = _tot(are_m2,  "QUANTIDADE"); t_iac_m2  = _tot(iac_m2,  "QUANTIDADE"); t_len_m2  = _tot(len_m2,  "QUANT")

    t_dia = t_are_dia + t_iac_dia + t_len_dia
    t_mes = t_are_mes + t_iac_mes + t_len_mes
    t_m1  = t_are_m1  + t_iac_m1  + t_len_m1
    t_m2  = t_are_m2  + t_iac_m2  + t_len_m2

    # Dias úteis de cada seção — base pra Meta do Período (meta diária × dias).
    dias_sec1 = _dias_uteis_simples(dia_ini if range_real else dia, dia)
    dias_sec2 = _dias_uteis_simples(mes_ini, dia)
    dias_m1   = _dias_uteis_simples(m1_ini, m1_fim)
    dias_m2   = _dias_uteis_simples(m2_ini, m2_fim)

    data_fmt = dia.strftime("%d/%m/%Y")
    dias_pt  = ["Segunda-feira", "Terca-feira", "Quarta-feira",
                "Quinta-feira", "Sexta-feira", "Sabado", "Domingo"]
    dia_semana = dias_pt[dia.weekday()]

    if range_real:
        sec1_titulo = f"1. PERIODO — {dia_ini.strftime('%d/%m/%Y')} a {data_fmt}"
        sec1_ref    = "Periodo selecionado"
    else:
        sec1_titulo = f"1. DIA — {data_fmt} (producao de ontem)"
        sec1_ref    = "Referencia: dia anterior"

    # Blocos de Meta x Realizado — um por seção (dias úteis próprios de cada
    # período), exibidos logo após os KPIs de total e antes das tabelas
    # detalhadas de Estação/Top OPs (pedido do usuário 14/07/2026).
    _meta_bloco_sec1 = _bloco_meta_status([
        ("Manta Arealva",  meta_diaria_arealva, dias_sec1, t_are_dia),
        ("Manta Iacanga",  meta_diaria_iacanga, dias_sec1, t_iac_dia),
        ("Lencol Arealva", meta_diaria_lencol,  dias_sec1, t_len_dia),
    ])
    _meta_bloco_sec2 = _bloco_meta_status([
        ("Manta Arealva",  meta_diaria_arealva, dias_sec2, t_are_mes),
        ("Manta Iacanga",  meta_diaria_iacanga, dias_sec2, t_iac_mes),
        ("Lencol Arealva", meta_diaria_lencol,  dias_sec2, t_len_mes),
    ])
    _meta_bloco_m1 = _bloco_meta_status([
        ("Manta Arealva",  meta_diaria_arealva, dias_m1, t_are_m1),
        ("Manta Iacanga",  meta_diaria_iacanga, dias_m1, t_iac_m1),
        ("Lencol Arealva", meta_diaria_lencol,  dias_m1, t_len_m1),
    ])
    _meta_bloco_m2 = _bloco_meta_status([
        ("Manta Arealva",  meta_diaria_arealva, dias_m2, t_are_m2),
        ("Manta Iacanga",  meta_diaria_iacanga, dias_m2, t_iac_m2),
        ("Lencol Arealva", meta_diaria_lencol,  dias_m2, t_len_m2),
    ])

    def kpi(v, lbl, cor=_PDF["navy"]):
        return (
            f'<td width="25%" style="background:#ffffff;border:1px solid {_PDF["border"]};'
            f'border-top:3px solid {cor};padding:12px 6px;text-align:center;">'
            f'<div style="font-size:21px;font-weight:bold;color:{cor};line-height:1.1;">{v}</div>'
            f'<div style="font-size:8px;color:{_PDF["muted"]};text-transform:uppercase;'
            f'letter-spacing:0.5px;margin-top:4px;">{lbl}</div>'
            f'</td>'
        )

    def kpi_row(*cells):
        return (
            f'<table width="100%" style="border-collapse:separate;border-spacing:5px 0;margin:0 -5px 12px -5px;">'
            f'<tr>{"".join(cells)}</tr></table>'
        )

    def sec_header(txt, cor="#0d47a1"):
        return (
            f'<table width="100%" style="margin:18px 0 10px 0;border-collapse:collapse;">'
            f'<tr><td style="background:{cor};color:#fff;font-weight:bold;font-size:12.5px;'
            f'padding:8px 12px;letter-spacing:0.4px;">{txt}</td></tr></table>'
        )

    def mes_bar(nome_mes, total):
        total_fmt = f"{total:,}".replace(",", ".")
        return (
            f'<table width="100%" style="margin-bottom:5px;border-collapse:collapse;">'
            f'<tr><td style="background:{_PDF["slate"]};color:#fff;font-weight:bold;font-size:11px;padding:7px 12px;">'
            f'{nome_mes} &nbsp;—&nbsp; Total: {total_fmt} pecas</td></tr></table>'
        )

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  @page {{ size: A4 portrait; margin: 14mm 11mm; }}
  body {{ font-family: Arial, sans-serif; font-size: 10.5px; color: {_PDF["ink"]}; }}
  * {{ box-sizing: border-box; }}
</style>
</head>
<body>

<table width="100%" style="border-bottom:3px solid {_PDF["navy"]};margin-bottom:14px;padding-bottom:7px;">
  <tr>
    <td>
      <span style="font-size:19px;font-weight:bold;color:{_PDF["navy"]};letter-spacing:0.4px;">ZANATTEX</span><br>
      <span style="font-size:12px;font-weight:bold;color:{_PDF["slate"]};">RELATORIO CONSOLIDADO DE CORTE</span>
    </td>
    <td align="right">
      <span style="font-size:15px;font-weight:bold;color:{_PDF["navy"]};">{data_fmt}</span><br>
      <span style="font-size:9px;color:{_PDF["muted"]};">{dia_semana} &nbsp;|&nbsp; {sec1_ref}</span>
    </td>
  </tr>
</table>

{sec_header(sec1_titulo)}
{kpi_row(
    kpi(f"{t_dia:,}".replace(",", "."), "Total Geral"),
    kpi(f"{t_are_dia:,}".replace(",", "."), "Manta Arealva", _PDF["blue"]),
    kpi(f"{t_iac_dia:,}".replace(",", "."), "Manta Iacanga", _PDF["teal"]),
    kpi(f"{t_len_dia:,}".replace(",", "."), "Lencol Arealva", _PDF["amber"]),
)}
{_meta_bloco_sec1}
{(_bloco_resumo_manta("MANTA AREALVA", are_dia) + _bloco_resumo_manta("MANTA IACANGA", iac_dia) + _bloco_resumo_lencol(len_dia)) if range_real else (_bloco_pdf_manta("MANTA AREALVA", are_dia) + _bloco_pdf_manta("MANTA IACANGA", iac_dia) + _bloco_pdf_lencol(len_dia))}

{sec_header(f"2. MES ATUAL — {_nome_mes(dia)}  (01/{dia.strftime('%m/%Y')} ate {data_fmt})", _PDF["blue"])}
{kpi_row(
    kpi(f"{t_mes:,}".replace(",", "."), "Total Geral"),
    kpi(f"{t_are_mes:,}".replace(",", "."), "Manta Arealva", _PDF["blue"]),
    kpi(f"{t_iac_mes:,}".replace(",", "."), "Manta Iacanga", _PDF["teal"]),
    kpi(f"{t_len_mes:,}".replace(",", "."), "Lencol Arealva", _PDF["amber"]),
)}
{_meta_bloco_sec2}
{_bloco_resumo_manta("MANTA AREALVA", are_mes)}
{_bloco_resumo_manta("MANTA IACANGA", iac_mes)}
{_bloco_resumo_lencol(len_mes)}

{sec_header("3. HISTORICO — ULTIMOS 2 MESES", _PDF["slate"])}

{mes_bar(_nome_mes(m1), t_m1)}
{kpi_row(
    kpi(f"{t_are_m1:,}".replace(",", "."), "Manta Arealva", _PDF["blue"]),
    kpi(f"{t_iac_m1:,}".replace(",", "."), "Manta Iacanga", _PDF["teal"]),
    kpi(f"{t_len_m1:,}".replace(",", "."), "Lencol Arealva", _PDF["amber"]),
)}
{_meta_bloco_m1}
{_bloco_resumo_manta("MANTA AREALVA", are_m1)}
{_bloco_resumo_manta("MANTA IACANGA", iac_m1)}
{_bloco_resumo_lencol(len_m1)}

{mes_bar(_nome_mes(m2), t_m2)}
{kpi_row(
    kpi(f"{t_are_m2:,}".replace(",", "."), "Manta Arealva", _PDF["blue"]),
    kpi(f"{t_iac_m2:,}".replace(",", "."), "Manta Iacanga", _PDF["teal"]),
    kpi(f"{t_len_m2:,}".replace(",", "."), "Lencol Arealva", _PDF["amber"]),
)}
{_meta_bloco_m2}
{_bloco_resumo_manta("MANTA AREALVA", are_m2)}
{_bloco_resumo_manta("MANTA IACANGA", iac_m2)}
{_bloco_resumo_lencol(len_m2)}

<p style="font-size:8.5px;color:#9aa4b2;margin-top:12px;border-top:1px solid {_PDF["border"]};padding-top:6px;">
  Gerado automaticamente &nbsp;|&nbsp; Sistema Zanattex
</p>
</body>
</html>"""

    buf = io.BytesIO()
    pisa.CreatePDF(html.encode("utf-8"), dest=buf, encoding="utf-8")
    return buf.getvalue()

# envio de email
def _corpo_resumo(dia: date, totais: dict[str, int], com_consolidado: bool = False) -> str:
    data_fmt = dia.strftime("%d/%m/%Y")
    total_geral = sum(totais.values())
    linhas_tabela = "".join(
        f'<tr>'
        f'<td style="padding:6px 10px;color:#555;">{s}</td>'
        f'<td style="padding:6px 10px;font-weight:bold;text-align:right;">{q:,} peças</td>'
        f'</tr>'
        for s, q in totais.items()
    )
    anexos_txt = "📎 <strong>Anexo 1:</strong> Relatório diário detalhado (PDF)."
    if com_consolidado:
        anexos_txt += "<br>📎 <strong>Anexo 2:</strong> Relatório consolidado — dia, mês atual e últimos 2 meses (PDF)."
    return f"""
<div style="font-family:Arial,sans-serif;font-size:13px;color:#1a1a1a;max-width:520px;">
  <h2 style="color:#1a237e;margin-bottom:4px;">✂️ Relatório de Corte — {data_fmt}</h2>
  <p style="color:#555;margin-top:0;">Produção do dia anterior · Sistema Zanattex</p>
  <hr style="border:1px solid #e0e0e0;margin:8px 0;">
  <table style="width:100%;border-collapse:collapse;font-size:13px;">
    <tr style="background:#f0f4ff;">
      <td style="padding:8px 10px;color:#555;font-weight:bold;">Total geral</td>
      <td style="padding:8px 10px;font-size:16px;font-weight:bold;color:#1a237e;text-align:right;">{total_geral:,} peças</td>
    </tr>
    {linhas_tabela}
  </table>
  <hr style="border:1px solid #e0e0e0;margin:8px 0;">
  <p style="color:#888;font-size:11px;margin:0;">{anexos_txt}</p>
</div>
""".strip()

def enviar_email(pdf_bytes: bytes, dia: date, totais: dict[str, int], pdf_consolidado: bytes | None = None) -> None:
    if not EMAIL_REMETENTE or not EMAIL_SENHA_APP:
        logging.error("Credenciais de e-mail não configuradas (EMAIL_REMETENTE / EMAIL_SENHA_APP).")
        return
    if not EMAIL_DESTINATARIOS:
        logging.error("Nenhum destinatário configurado (EMAIL_DESTINATARIOS).")
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"✂️ Relatório de Corte — {dia.strftime('%d/%m/%Y')}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = ", ".join(EMAIL_DESTINATARIOS)

    corpo = MIMEMultipart("alternative")
    corpo.attach(MIMEText(_corpo_resumo(dia, totais, com_consolidado=bool(pdf_consolidado)), "html", "utf-8"))
    msg.attach(corpo)

    nome_diario = f"relatorio_corte_{dia.strftime('%d-%m-%Y')}.pdf"
    anexo = MIMEBase("application", "pdf")
    anexo.set_payload(pdf_bytes)
    encoders.encode_base64(anexo)
    anexo.add_header("Content-Disposition", "attachment", filename=nome_diario)
    msg.attach(anexo)

    if pdf_consolidado:
        nome_cons = f"relatorio_consolidado_{dia.strftime('%d-%m-%Y')}.pdf"
        anexo2 = MIMEBase("application", "pdf")
        anexo2.set_payload(pdf_consolidado)
        encoders.encode_base64(anexo2)
        anexo2.add_header("Content-Disposition", "attachment", filename=nome_cons)
        msg.attach(anexo2)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        smtp.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIOS, msg.as_string())

    extras = f" + {nome_cons}" if pdf_consolidado else ""
    logging.info(f"E-mail enviado para {EMAIL_DESTINATARIOS} ({nome_diario}{extras})")

# main
if __name__ == "__main__":
    dia = _dia_ref()  # dia anterior por padrão
    
    hoje = date.today()
    weekday = hoje.weekday()  # 0=seg, 1=ter, 2=qua, 3=qui, 4=sex, 5=sab, 6=dom
    
    # Sábado e domingo: não envia
    if weekday in (5, 6):
        logging.info(f"Fim de semana ({['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][weekday]}). Nenhum relatório será enviado.")
        exit(0)
    
    # Segunda: envia sexta anterior (que não foi enviada no fim de semana)
    if weekday == 0:
        dia = hoje - timedelta(days=3)
        logging.info(f"Segunda. Será enviado relatório de sexta ({dia.strftime('%d/%m/%Y')}).")
    else:
        logging.info(f"Será enviado relatório de {dia.strftime('%d/%m/%Y')}.")
    
    logging.info(f"=== Relatório de Corte — {dia.strftime('%d/%m/%Y')} ===")

    df_manta_are = carregar_manta_arealva(dia)
    df_manta_iac = carregar_manta_iacanga(dia)
    df_lencol    = carregar_lencol_arealva(dia)

    logging.info(f"Manta Arealva : {len(df_manta_are)} registros | {int(df_manta_are['QUANTIDADE'].sum()) if not df_manta_are.empty else 0} peças")
    logging.info(f"Manta Iacanga : {len(df_manta_iac)} registros | {int(df_manta_iac['QUANTIDADE'].sum()) if not df_manta_iac.empty else 0} peças")
    logging.info(f"Lençol Arealva: {len(df_lencol)} registros | {int(df_lencol['QUANT'].sum()) if not df_lencol.empty else 0} peças")

    totais = {
        "Manta Arealva":  int(df_manta_are["QUANTIDADE"].sum()) if not df_manta_are.empty else 0,
        "Manta Iacanga":  int(df_manta_iac["QUANTIDADE"].sum()) if not df_manta_iac.empty else 0,
        "Lencol Arealva": int(df_lencol["QUANT"].sum())         if not df_lencol.empty    else 0,
    }
    logging.info("Gerando PDF diario...")
    pdf = gerar_pdf(dia, df_manta_are, df_manta_iac, df_lencol)

    logging.info("Gerando PDF consolidado (dia + mes + historico)...")
    try:
        pdf_cons = gerar_pdf_consolidado(dia)
    except Exception as e:
        logging.warning(f"PDF consolidado falhou, seguindo sem ele: {e}")
        pdf_cons = None

    enviar_email(pdf, dia, totais, pdf_cons)
    logging.info("Concluído.")
