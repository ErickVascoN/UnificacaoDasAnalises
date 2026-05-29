"""
Normalização canônica de identificadores e textos — usada em TODO o projeto.

Objetivo: garantir que o mesmo dado escrito de formas diferentes em planilhas
diferentes seja tratado como igual. Evita a classe de bugs onde um corte não
cruza com a programação só porque a OP foi digitada como "PROG 10", "PGR 10"
ou "10".

Funções principais:
  - is_blank(v)      → True para vazio/nan/none/n/a (valores não-informados).
  - normalize_op(v)  → chave canônica de OP: sem prefixo (PROG/PGR/OP), upper, sem
                       espaços/zeros à esquerda redundantes. Use SEMPRE ao comparar
                       OPs entre planilhas (programação × cortes).
  - normalize_text(v)→ upper + sem acentos + espaços colapsados (nomes/produtos).
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Valores que significam "vazio / não informado" em qualquer planilha.
BLANK_VALUES = frozenset({
    "", "NAN", "NONE", "N/A", "NA", "NAT", "-", "--", "SEM OP", "SEM",
})

# Prefixos que são apenas ruído de digitação na frente do número da OP.
# Ex: "PROG 82" → "82", "PGR 10" → "10", "OP 123" → "123", "O.P. 5" → "5".
# - alternativas mais longas primeiro (PROGRAMACAO antes de PROG);
# - lookahead (?=\d) garante que só removemos quando um número segue o prefixo,
#   evitando comer palavras como "PROGRESSO".
_OP_PREFIX_RE = re.compile(
    r"^\s*(?:PROGRAMA(?:CAO|ÇÃO)?|PROG|PGR|O\.?P\.?)\s*[:\-#]?\s*(?=\d)",
    re.IGNORECASE,
)
_SPACES_RE = re.compile(r"\s+")


def is_blank(value) -> bool:
    """True se o valor representa vazio/não-informado."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip().upper() in BLANK_VALUES


def normalize_op(value) -> str:
    """
    Chave canônica de OP para cruzamento entre planilhas.

    Remove prefixo (PROG/PGR/OP), espaços e normaliza caixa. Retorna "" para
    valores vazios. NÃO é para exibição — é a chave usada nos joins/lookups.

    Exemplos:
        "PROG 82" → "82"   "PGR 10" → "10"   "OP 123" → "123"
        " 10 "    → "10"   "82A"    → "82A"  ""/"nan" → ""
    """
    if is_blank(value):
        return ""
    s = str(value).strip()
    # remove sufixo decimal de floats vindos do CSV ("82.0" → "82")
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    s = _OP_PREFIX_RE.sub("", s)          # tira prefixo PROG/PGR/OP
    s = _SPACES_RE.sub(" ", s).strip()    # colapsa espaços internos
    s = s.upper()
    if s in BLANK_VALUES:
        return ""
    return s


def normalize_op_series(series: pd.Series) -> pd.Series:
    """Aplica normalize_op a uma Series inteira (vetorizado por map)."""
    return series.map(normalize_op)


def normalize_text(value) -> str:
    """Upper + remove acentos + colapsa espaços. Para nomes/produtos/empresas."""
    if is_blank(value):
        return ""
    s = str(value).strip()
    nfd = unicodedata.normalize("NFD", s)
    s = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    s = _SPACES_RE.sub(" ", s).strip().upper()
    return s
