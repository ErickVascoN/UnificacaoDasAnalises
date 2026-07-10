"""Calendário de feriados (nacionais + São Paulo) usado nos cálculos de dias
úteis do projeto inteiro — dashboards ao vivo e relatórios PDF.

Sem isso, todo cálculo de "dia útil" era só `weekday() < 5`, sem exceção
pra feriado. Um feriado como 09/07 (Revolução Constitucionalista, estadual
em SP) continuava contando como dia útil cheio na meta — como só uma
parte da equipe trabalha em feriado, a produção do dia fica bem abaixo da
meta esperada e puxa a média/% do período pra baixo de forma injusta.
Confirmado com o usuário: todas as facções são de SP, então nacional +
estadual SP cobre o caso (não precisa de calendário por município).
"""
from datetime import date, timedelta
from functools import lru_cache

import holidays as _holidays_lib
import pandas as pd


@lru_cache(maxsize=1)
def _calendario():
    return _holidays_lib.Brazil(subdiv="SP")


def _to_date(d) -> date:
    # type() exato (não isinstance) — datetime.datetime e pd.Timestamp também
    # são "isinstance(d, date)" (são subclasses), mas carregam hora e precisam
    # passar por pd.Timestamp(d).date() pra virar um date puro comparável.
    if type(d) is date:
        return d
    return pd.Timestamp(d).date()


def eh_feriado(d) -> bool:
    """True se a data é feriado nacional ou estadual de SP."""
    return _to_date(d) in _calendario()


def nome_feriado(d) -> str | None:
    """Nome do feriado na data, ou None se não for feriado."""
    return _calendario().get(_to_date(d))


def eh_dia_util(d) -> bool:
    """Dia útil = segunda a sexta e não é feriado nacional/SP."""
    dd = _to_date(d)
    return dd.weekday() < 5 and not eh_feriado(dd)


def contar_dias_uteis(ini: date, fim: date) -> int:
    """Conta dias úteis (seg-sex, exceto feriados) entre ini e fim, inclusive.

    Substitui o padrão repetido `sum(1 for i in range(...) if
    (ini + timedelta(days=i)).weekday() < 5)` usado em vários relatórios."""
    if fim < ini:
        return 0
    return sum(
        1 for i in range((fim - ini).days + 1)
        if eh_dia_util(ini + timedelta(days=i))
    )


def feriados_no_periodo(ini: date, fim: date) -> list[tuple[date, str]]:
    """Lista (data, nome) dos feriados nacionais/SP dentro do período,
    incluindo fins de semana — útil pra observações tipo 'Feriados no
    período: ...' nos relatórios."""
    if fim < ini:
        return []
    out = []
    for i in range((fim - ini).days + 1):
        d = ini + timedelta(days=i)
        nome = nome_feriado(d)
        if nome:
            out.append((d, nome))
    return out
