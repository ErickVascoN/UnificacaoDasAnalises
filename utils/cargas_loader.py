"""Loader compartilhado de Previsão de Cargas (previsão x realizado).

Extraído de pages/8_Previsao_Cargas.py em 13/07/2026: antes pages/10_Relatorios.py
(a Central de Relatórios, que gera o PDF) tinha sua própria cópia dessa lógica de
parsing, presa numa lista fixa de meses (parava em Junho/2026) e sem as correções
de bugs feitas no dashboard (coluna do painel diário limitada, filtro de linha
TOTAL/GERAL, reconciliação por dias com carga cadastrada, override de Maio). Isso
fazia o PDF de Cargas divergir do dashboard. Agora as duas páginas importam deste
módulo único — uma correção feita aqui vale para as duas.
"""

from __future__ import annotations

import csv
import calendar
import io
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date

import pandas as pd
import streamlit as st

CARGAS_SHEET_ID = "1RvC2dkk9KCribduCoxXM6sKGB0lxuIXk"
CARGAS_CACHE_TTL = 300  # segundos

MESES_NOMES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO",
}

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def _meses_disponiveis(ano_inicio: int = 2026, mes_inicio: int = 1) -> list[tuple[str, int, int]]:
    """Gera (NOME, mes, ano) de ano_inicio/mes_inicio até o mês atual — antes
    era uma lista fixa que parava em junho/2026 e precisava ser editada todo
    mês manualmente (por isso julho não aparecia sozinho; feedback do
    usuário 13/07/2026)."""
    hoje = date.today()
    meses = []
    ano, mes = ano_inicio, mes_inicio
    while (ano, mes) <= (hoje.year, hoje.month):
        meses.append((MESES_NOMES_PT[mes], mes, ano))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return meses


MESES_DISPONIVEIS = _meses_disponiveis()

# Override manual do REALIZADO mensal para meses fechados onde o lançamento
# diário na planilha ficou incompleto e não é mais recuperável (confirmado com
# o usuário 10/07/2026) — o valor abaixo vem do relatório "Acompanhamento
# Mensal" (fechamento por empresa), que é a fonte confiável pra esses meses.
# Não mexe na extração normal: meses fora deste dict continuam vindo 100% da
# linha de resumo da planilha (_find_resumo_mensal). Junho removido em
# 13/07/2026: usuário preencheu os dias que faltavam na planilha, então
# volta a ler o total direto de lá.
REALIZADO_MENSAL_OVERRIDE: dict[tuple[int, int], float] = {
    (2026, 5): 4_065_134.69,  # Maio/2026
}


# ── Helpers de parsing ─────────────────────────────────────────────────────────
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


def _estimativa_mes_atual(df_raw: pd.DataFrame) -> dict | None:
    """Projeta o fechamento (Previsto e Realizado) do mês corrente.

    Cálculo (confirmado com o usuário em 13/07/2026):
    1. Previsto Projetado = Previsto lançado / dias cobertos pelos lançamentos
       x dias totais do mês (run-rate). "Dias cobertos" é o intervalo entre a
       primeira e a última carga já lançada no mês — não "dias corridos desde
       o dia 1" — porque a planilha é preenchida em blocos semanais (ex.:
       "SEMANA 06/07 A 11/07"), não dia a dia; contar por dias corridos do
       calendário dilui o valor pelos dias da semana seguinte que ainda nem
       foi lançada, subestimando a projeção pela metade (bug relatado pelo
       usuário em 13/07/2026).
    2. Aderência Média = média simples de (Realizado/Previsto) dos 2 últimos
       meses fechados (com Realizado oficial > 0) antes do mês corrente.
    3. Realizado Estimado = Previsto Projetado x Aderência Média.
    """
    hoje = date.today()
    ano_atual, mes_atual = hoje.year, hoje.month

    df_mes_atual = df_raw[(df_raw["ANO"] == ano_atual) & (df_raw["MES_NUM"] == mes_atual)]
    if df_mes_atual.empty:
        return None

    previsto_lancado = df_mes_atual["PREVISAO"].sum()
    dias_totais = calendar.monthrange(ano_atual, mes_atual)[1]

    df_cargas_mes = df_mes_atual[~df_mes_atual["STATUS"].isin(["CARGO_REAL", "NAO_ALOCADO"])]
    if df_cargas_mes.empty:
        return None
    dias_cobertos = (df_cargas_mes["DATA"].max() - df_cargas_mes["DATA"].min()).days + 1
    if dias_cobertos <= 0 or previsto_lancado <= 0:
        return None
    previsto_projetado = previsto_lancado / dias_cobertos * dias_totais

    df_real_mensal = (
        df_raw[df_raw["STATUS"] == "CARGO_REAL"]
        .groupby(["ANO", "MES_NUM"])
        .agg(PREVISAO=("PREVISAO", "sum"), REALIZADO=("REALIZADO", "sum"))
        .reset_index()
    )
    df_real_mensal = df_real_mensal[
        (df_real_mensal["REALIZADO"] > 0) & (df_real_mensal["PREVISAO"] > 0) &
        ((df_real_mensal["ANO"] < ano_atual) |
         ((df_real_mensal["ANO"] == ano_atual) & (df_real_mensal["MES_NUM"] < mes_atual)))
    ].sort_values(["ANO", "MES_NUM"])

    ultimos_2 = df_real_mensal.tail(2).copy()
    if ultimos_2.empty:
        return None
    ultimos_2["ADERENCIA"] = ultimos_2["REALIZADO"] / ultimos_2["PREVISAO"]
    aderencia_media = ultimos_2["ADERENCIA"].mean()
    realizado_estimado = previsto_projetado * aderencia_media

    return {
        "previsto_lancado": previsto_lancado,
        "previsto_projetado": previsto_projetado,
        "aderencia_media": aderencia_media,
        "realizado_estimado": realizado_estimado,
        "dias_corridos": dias_cobertos,
        "dias_totais": dias_totais,
        "n_meses_base": len(ultimos_2),
    }


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
    return list(csv.reader(io.StringIO(raw)))


def _first_frete(row: list[str], limit: int | None = None) -> float:
    """Primeiro R$ positivo em cols 5 até `limit` (exclusivo, default col 10).

    Para a maioria dos meses o frete está em col[6], mas JANEIRO usa col[7]
    (layout com coluna MOTORISTA extra). Varredura dinâmica evita hard-code.

    `limit` deve ser a coluna-base do painel diário (_find_painel_col) quando
    conhecida. Sem isso, em cargas com a própria célula de frete vazia (ex.:
    Armazenagem, frete subcontratado "FRETE GALICE") a varredura continuava
    até a col 9 e acabava lendo o Previsto do painel diário de OUTRO cliente
    no mesmo dia como se fosse o frete dessa carga — ex.: Julho/2026, painel
    começa na col 8, e a carga de Armazenagem de 06/07 (frete vazio) herdou
    os R$ 40.000 do Previsto de SULTAN no painel, inflando o Previsto da
    semana em R$ 70.000 (bug relatado pelo usuário em 13/07/2026).
    """
    hi = min(limit, len(row)) if limit is not None else min(10, len(row))
    for j in range(5, hi):
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
    2. Linha com 'GERAL' em cols 8-14 → col[GERAL+2] é o realizado (JANEIRO);
       col[GERAL+1] é o previsto quando presente (ex.: "Total geral (dd a
       dd/mm)" nos meses em andamento — antes ficava sempre 0.0, forçando o
       previsto a cair no fallback por carga individual, que não bate com o
       total oficial; bug relatado pelo usuário em 13/07/2026).
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
                prev_col = j + 1
                if len(row) > real_col:
                    v = _parse_money(row[real_col])
                    if v and abs(v) > 1_000_000:
                        prev_v = _parse_money(row[prev_col]) if len(row) > prev_col else None
                        return (abs(prev_v) if prev_v else 0.0, abs(v))

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


def _find_painel_col(rows: list[list[str]]) -> int | None:
    """Detecta a coluna do painel diário de realizado ("DD-mmm.") — a posição

    muda de mês para mês na planilha (ex.: col 8 em Junho, col 11 em Abril,
    col 9 em Maio), então não pode ser hard-coded. Usa a coluna mais frequente
    entre todas as células que casam com o padrão de cabeçalho de dia.
    """
    contagem: Counter = Counter()
    for row in rows:
        for j, cell in enumerate(row):
            if re.match(r'^\s*\d{1,2}\s*[-\.]\s*[a-z]{3}', str(cell).strip().lower()):
                contagem[j] += 1
    if not contagem:
        return None
    return contagem.most_common(1)[0][0]


def _find_painel_col_rotulo(rows: list[list[str]]) -> int | None:
    """Fallback para meses sem cabeçalho 'DD-mmm.' repetido (ex.: Janeiro), onde

    o painel não tem blocos por dia — cada linha de cliente já carrega sua data
    na própria linha de carga (col[1]). Localiza a coluna pelo rótulo de
    cabeçalho "REALIZADO" na primeira linha da planilha; o nome do cliente fica
    2 colunas antes.
    """
    if not rows:
        return None
    for j, cell in enumerate(rows[0]):
        if _norm(cell) == "REALIZADO" and j >= 2:
            return j - 2
    return None


def _extract_day_realized(rows: list[list[str]], mes_num: int, ano: int) -> dict:
    """
    Lê o painel direito do CSV e retorna {(data, cliente_norm): realizado}.

    Estrutura real do CSV por bloco de dia (coluna-base detectada por
    _find_painel_col, pois sua posição varia por mês):
      col[base]   = "DD-jun." (cabeçalho do dia) ou NOME do cliente
      linhas de cliente: col[base]=NOME, col[base+1]=previsto_val,
                         col[base+2]=realizado_val, col[base+3]=diferença_val
      linha de total/separador: col[base] vazio ou contém 'R$' — ignorada

    Alguns meses (ex.: Janeiro) não repetem o cabeçalho de dia — nesse caso cada
    linha de cliente usa a data da própria linha de carga (col[1]).
    """
    day_real: dict = {}
    col = _find_painel_col(rows)

    if col is not None:
        current_date = None
        for row in rows:
            if len(row) <= col:
                continue
            cell_base = str(row[col]).strip()

            # Cabeçalho de dia: "1-jun.", "19-abr.", etc.
            m = re.match(r'^(\d{1,2})\s*[-\.]\s*(\w{3})', cell_base.lower())
            if m:
                try:
                    current_date = date(ano, mes_num, int(m.group(1)))
                except ValueError:
                    current_date = None
                continue

            # Separador / total: col[base] vazio ou contém 'R$' — ignora
            if not cell_base or 'R$' in cell_base:
                continue

            if current_date is None or len(row) <= col + 2:
                continue

            # Linha de cliente: col[base]=nome, col[base+2]=realizado por cliente
            cliente_raw = cell_base.strip().upper()
            # Linha de "Total geral" do painel (ex.: "TOTAL GERAL (01 A 11/07)")
            # não é um cliente — se entrar aqui, soma o acumulado do mês inteiro
            # como se fosse mais um lançamento diário, dobrando o total do painel
            # (bug relatado pelo usuário em 13/07/2026 — semana 06/07-11/07 com
            # Realizado muito acima do previsto).
            if "TOTAL" in cliente_raw or "GERAL" in cliente_raw:
                continue
            v = _parse_num(str(row[col + 2]).strip())
            if v and v > 0 and cliente_raw:
                key = (current_date, _norm(cliente_raw))
                # Acumula caso haja mais de uma linha para o mesmo cliente no dia
                day_real[key] = day_real.get(key, 0.0) + v
        return day_real

    col = _find_painel_col_rotulo(rows)
    if col is None:
        return {}

    for row in rows:
        if len(row) <= col + 2:
            continue
        cliente_raw = str(row[col]).strip().upper()
        if not cliente_raw or 'R$' in cliente_raw:
            continue
        if "TOTAL" in cliente_raw or "GERAL" in cliente_raw:
            continue
        row_date = _parse_date_pt(row[1]) if len(row) > 1 else None
        if row_date is None:
            continue
        v = _parse_num(str(row[col + 2]).strip())
        if v and v > 0:
            key = (row_date, _norm(cliente_raw))
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
    if (ano, mes_num) in REALIZADO_MENSAL_OVERRIDE:
        realizado_mensal = REALIZADO_MENSAL_OVERRIDE[(ano, mes_num)]
    day_realized = _extract_day_realized(rows, mes_num, ano)
    _painel_col = _find_painel_col(rows)

    # Fallback para o mês corrente/em andamento: a linha de resumo ("Previsto
    # total | Realizado total") só é preenchida na planilha perto do fim do
    # mês, quando o total acumulado passa dos R$1,5M usados como filtro em
    # _find_resumo_mensal. Enquanto isso não acontece, usa a soma do painel
    # diário (mesma fonte da quebra semanal) para não deixar o Realizado do
    # mês travado em zero (bug relatado pelo usuário em 13/07/2026 — Julho
    # não atualizava automaticamente).
    if realizado_mensal == 0:
        realizado_mensal = sum(day_realized.values())

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

        # PREVISTO = primeiro R$ positivo em cols 5-9 (col[6] na maioria; col[7] em JANEIRO),
        # nunca além da coluna-base do painel diário (senão vaza pro previsto de outro cliente)
        valor_frete = _first_frete(row, limit=_painel_col)

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
            # Painel direito registra 1 realizado por (data, cliente) — não por carga
            # individual. Guarda a chave aqui; o valor é dividido logo abaixo entre
            # todas as cargas do mesmo cliente/dia para não contar em dobro no total.
            "_REAL_KEY": (
                (data_carga, _norm(destino)) if (data_carga, _norm(destino)) in day_realized
                else (data_carga, _norm(cliente)) if (data_carga, _norm(cliente)) in day_realized
                else None
            ),
            "REALIZADO_DIA":  0.0,
            "DIFERENCA":      0.0,
            "OBS":            obs_raw,
            "STATUS":         status,
        })

    # Painel direito só tem 1 realizado por (data, cliente); quando 2+ cargas do
    # mesmo cliente caem no mesmo dia, divide o valor entre elas — do contrário
    # cada carga herdaria o valor cheio do dia e o total semanal/mensal ficaria
    # contado em dobro (ou triplo).
    _contagem_chave = Counter(r["_REAL_KEY"] for r in records if r["_REAL_KEY"] is not None)
    for r in records:
        _chave = r.pop("_REAL_KEY", None)
        if _chave is not None:
            r["REALIZADO_DIA"] = day_realized[_chave] / _contagem_chave[_chave]

    # Nem todo lançamento do painel diário casa por nome com uma carga (ex.: entradas
    # que somam vários clientes numa única célula, ou grafia diferente da planilha de
    # cargas). Reconcilia proporcionalmente para que a soma das cargas casadas bata com
    # o total do painel diário DAS MESMAS DATAS que já têm carga cadastrada — nunca com
    # o Realizado mensal inteiro. Usar o mensal inteiro jogava o dinheiro de dias sem
    # nenhuma carga no mês (ex.: 01/07-04/07 em Julho/2026, cujo painel diário já tinha
    # lançamento mas a aba ainda não tinha as cargas daqueles dias) inteiro dentro da
    # única semana existente, inflando-a bem acima do que ela realmente produziu (bug
    # relatado pelo usuário em 13/07/2026 — semana 06/07-11/07 aparecendo com 133% de
    # aderência).
    _datas_com_carga = {r["DATA"] for r in records}
    _painel_datas_com_carga = sum(
        v for (_d, _c), v in day_realized.items() if _d in _datas_com_carga
    )
    _soma_batida = sum(r["REALIZADO_DIA"] for r in records)
    if _soma_batida > 0 and _painel_datas_com_carga > 0:
        _fator = _painel_datas_com_carga / _soma_batida
        for r in records:
            r["REALIZADO_DIA"] *= _fator

    # Lançamentos do painel diário em datas sem NENHUMA carga cadastrada no mês (ex.:
    # 02/07-04/07 em Julho/2026 — confirmado com o usuário em 13/07/2026 que não foram
    # previstos em lugar nenhum, nem no mês anterior). Não têm semana pra entrar, mas o
    # dinheiro é real — gera um registro "Não alocado" por lançamento em vez de
    # descartar silenciosamente, para aparecer à parte na quebra semanal (soma sempre
    # bate: mensal exato + semanas normais + não alocado).
    for (_data_orfa, _cliente_orfa), _v_orfa in day_realized.items():
        if _data_orfa in _datas_com_carga:
            continue
        records.append({
            "MES":            mes_nome,
            "MES_NUM":        mes_num,
            "ANO":            ano,
            "SEMANA":         "NAO_ALOCADO",
            "DATA":           _data_orfa,
            "DESTINO":        "SEM PREVISAO",
            "LOCAL":          "",
            "VEICULO":        "",
            "TIPO_VEICULO":   "",
            "VALOR_FRETE":    0.0,
            "CLIENTE":        _cliente_orfa,
            "PREVISAO":       0.0,
            "REALIZADO":      0.0,
            "REALIZADO_DIA":  _v_orfa,
            "DIFERENCA":      0.0,
            "OBS":            "Realizado do painel diário sem carga cadastrada no mês",
            "STATUS":         "NAO_ALOCADO",
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
