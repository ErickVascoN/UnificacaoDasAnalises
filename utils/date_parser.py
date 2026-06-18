"""
Parser de datas robusto com detecção de formato por COLUNA.

Problema que resolve:
  O Google Sheets exporta datas conforme o locale/formatação de cada planilha.
  - Algumas planilhas exportam M/D/YYYY  (ex: Arealva Manta → "1/20/2026")
  - Outras exportam D/M/YY              (ex: Iacanga       → "02/05/26")

  Um parser que decide o formato valor-a-valor erra as datas ambíguas
  (quando dia E mês são ≤ 12). Ex: "12/05/26" pode ser 12/mai OU 5/dez.

Estratégia (detecção por coluna):
  1. Varre TODOS os valores da coluna e separa em (a, b, ano).
  2. Se ALGUM valor tem a > 12  → a coluna inteira é DD/MM (dia primeiro).
  3. Senão, se ALGUM tem b > 12 → a coluna inteira é MM/DD (mês primeiro).
  4. Se todos forem ambíguos    → assume DD/MM (padrão brasileiro).
  Depois aplica o MESMO formato detectado a todos os valores — consistência total.
"""

from __future__ import annotations

import re
import pandas as pd

_DATE_RE = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\s*$")
_ISO_RE = re.compile(r"^\s*(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})")


def _only_date_part(value) -> str:
    """Remove parte de hora ('5/28/2026 00:00:00' → '5/28/2026')."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "nat", ""):
        return ""
    return s.split(" ")[0].strip()


def detectar_ordem(series: pd.Series, default: str = "DMY") -> str:
    """
    Analisa a coluna e retorna 'DMY', 'MDY' ou 'ISO'.

    DMY  → dia primeiro  (DD/MM/YYYY)
    MDY  → mês primeiro  (MM/DD/YYYY)
    ISO  → ano primeiro  (YYYY-MM-DD)

    Args:
        default: ordem assumida quando todas as datas são ambíguas
                 (ambos componentes ≤ 12). Use "MDY" para planilhas com
                 locale US (ex: LITTEX, GGTTEX). Padrão "DMY" (brasileiro).
    """
    tem_iso = False
    primeiro_maior_12 = False  # força DMY
    segundo_maior_12 = False   # força MDY

    for raw in series.dropna():
        s = _only_date_part(raw)
        if not s:
            continue

        if _ISO_RE.match(s):
            tem_iso = True
            continue

        m = _DATE_RE.match(s)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            primeiro_maior_12 = True
        if b > 12:
            segundo_maior_12 = True

    # ISO só vence se não houver nenhum formato com barras
    if tem_iso and not primeiro_maior_12 and not segundo_maior_12:
        return "ISO"
    if primeiro_maior_12:
        return "DMY"
    if segundo_maior_12:
        return "MDY"
    # Todos ambíguos → usa o default fornecido pelo chamador
    return default


def _parse_um(s: str, ordem: str) -> pd.Timestamp:
    """Converte um único valor já sabendo a ordem da coluna."""
    if not s:
        return pd.NaT

    # ISO sempre sem ambiguidade
    mi = _ISO_RE.match(s)
    if mi:
        try:
            return pd.to_datetime(s.split(" ")[0], format="%Y-%m-%d")
        except Exception:
            return pd.to_datetime(s, errors="coerce")

    m = _DATE_RE.match(s)
    if not m:
        return pd.to_datetime(s, errors="coerce")

    a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
    if len(y) == 2:
        y = "20" + y
    year = int(y)

    if ordem == "MDY":
        mes, dia = a, b
    else:  # DMY
        dia, mes = a, b

    # Correção defensiva: se a ordem detectada produzir mês inválido mas o
    # componente oposto for válido, inverte (lida com linhas atípicas).
    if mes > 12 and dia <= 12:
        dia, mes = mes, dia

    try:
        return pd.Timestamp(year=year, month=mes, day=dia)
    except (ValueError, TypeError):
        return pd.NaT


def parse_date_series(series: pd.Series, default_order: str = "DMY") -> pd.Series:
    """
    Converte uma Series de datas (strings) em datetime, detectando o formato
    da coluna inteira primeiro. Use SEMPRE que carregar uma coluna de datas
    de planilha — garante consistência e evita inversão dia/mês.

    Args:
        default_order: ordem usada quando todas as datas são ambíguas.
                       Passe "MDY" para planilhas com locale US (ex: LITTEX, GGTTEX).
    """
    if series is None or len(series) == 0:
        return pd.to_datetime(series, errors="coerce")
    ordem = detectar_ordem(series, default=default_order)
    limpa = series.map(_only_date_part)
    return limpa.map(lambda s: _parse_um(s, ordem))


def parse_date_single(value, ordem: str = "DMY") -> pd.Timestamp:
    """Parse de um único valor (quando não há coluna para detectar a ordem)."""
    return _parse_um(_only_date_part(value), ordem)
