"""Cálculo de meta por facção — Produção de Facções Externas.

Extraído de pages/5_Producao_Faccoes.py para ser reutilizado também na geração
de PDF (pages/10_Relatorios.py) sem duplicar a lógica — a mesma conta que o
dashboard mostra ao vivo é a que vai para o relatório da CEO.

Regras de negócio (mantidas do dashboard):
  - A meta de cada facção pode vir de 3 formatos na planilha de metas:
    sem cliente/produto (soma direta), com produto mas sem cliente, com cliente
    mas sem produto (pondera pela produção de cada cliente), ou com produto E
    cliente (pondera dentro de cada produto). Ver load_metas()/config/settings.py.
  - Meta mensal de cada facção = meta diária × dias em que a facção realmente
    produziu no período (fallback: dias úteis do mês, para facções sem produção
    no período — assim elas ainda aparecem com uma meta de referência).
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date

import pandas as pd

from utils.metas_manager import load_metas
from utils.normalize import normalize_text
from utils.feriados import eh_dia_util


def dias_uteis(year: int, month: int) -> int:
    _, n = monthrange(year, month)
    return sum(1 for d in range(1, n + 1) if eh_dia_util(date(year, month, d)))


def _build_goals() -> pd.DataFrame:
    rows = []
    for g in load_metas():
        rows.append({
            "PRODUTO":     g["produto"].upper(),
            "CLIENTE":     g["cliente"].upper(),
            "FACCAO":      g["faccao"].upper(),
            "PRODUTO_N":   normalize_text(g["produto"]),
            "CLIENTE_N":   normalize_text(g["cliente"]),
            "FACCAO_N":    normalize_text(g["faccao"]),
            "META_DIA":    g.get("meta_dia", 0),
            "META_MES":    g.get("meta_mes", 0),
            "META_SEMANA": g.get("meta_semana", 0),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["PRODUTO", "CLIENTE", "FACCAO", "PRODUTO_N", "CLIENTE_N", "FACCAO_N",
                 "META_DIA", "META_MES", "META_SEMANA"]
    )


def calcular_meta_faccoes(
    df_periodo: pd.DataFrame,
    ano_sel: int,
    mes_sel: int,
) -> dict:
    """Calcula meta por facção e o ranking Facção × Meta para o período dado.

    Parameters
    ----------
    df_periodo : DataFrame já filtrado pelo período (e por facção/produto/cliente,
                 se aplicável) — colunas DATA, FACCAO, PRODUTO, CLIENTE, QUANTIDADE.
    ano_sel, mes_sel : usados apenas como fallback de dias úteis para facções
                 sem nenhuma produção no período.

    Returns
    -------
    dict com:
      rank_df        : DataFrame (FACCAO, QUANTIDADE, META_DIA, META_MES,
                        META_SEMANA, PCT, PCT_TOTAL, RESTANTE, ULTIMA_DATA,
                        DIAS_ATRASO) — 1 linha/facção. ULTIMA_DATA = último dia com
                        produção lançada; DIAS_ATRASO = quantos dias atrás da facção
                        mais atualizada do grupo (0 = está em dia com as demais).
                        Serve para o leitor distinguir "produção baixa" de "dado
                        ainda não enviado".
      meta_mes_total, meta_sem_total, meta_dia_total : int, somas globais.
      total_geral    : int, total produzido no período (todas as facções).
    """
    goals_df = _build_goals()
    du_mes = dias_uteis(ano_sel, mes_sel)

    df_periodo = df_periodo.copy()
    if "FACCAO_N" not in df_periodo.columns:
        df_periodo["FACCAO_N"] = df_periodo["FACCAO"].apply(normalize_text)

    total_geral = int(df_periodo["QUANTIDADE"].sum()) if not df_periodo.empty else 0

    # Dias distintos com produção por facção (fallback: du_mes). Só conta dias
    # com QUANTIDADE > 0 — linhas de QUANTIDADE=0 com Observação (ex.: "máquina
    # quebrou", contextualização de um dia sem produção) não devem inflar o
    # número de dias considerados na meta/média, senão a meta cresce e a % cai
    # sem produção real ter caído (feedback do usuário 14/07/2026).
    _dias_fac: dict[str, int] = {}
    _ultima_data_fac: dict[str, date] = {}
    if not df_periodo.empty:
        _df_com_producao = df_periodo[df_periodo["QUANTIDADE"] > 0]
        _dias_fac = (
            _df_com_producao.groupby("FACCAO_N")["DATA"]
            .apply(lambda s: s.dt.date.nunique())
            .to_dict()
        )
        _ultima_data_fac = (
            df_periodo.groupby("FACCAO_N")["DATA"]
            .apply(lambda s: s.dt.date.max())
            .to_dict()
        )

    _goals_tem_dia = not goals_df.empty and (goals_df["META_DIA"] > 0).any()
    if _goals_tem_dia:
        mask_dia = goals_df["META_DIA"] > 0
        goals_df.loc[mask_dia, "META_MES"] = goals_df.loc[mask_dia].apply(
            lambda r: int(r["META_DIA"] * _dias_fac.get(r["FACCAO_N"], du_mes)),
            axis=1,
        )
        goals_df.loc[mask_dia, "META_SEMANA"] = (goals_df.loc[mask_dia, "META_DIA"] * 5).astype(int)

    # Produção por (facção, produto, cliente) e (facção, cliente) — usada para
    # ponderar metas que são definidas por cliente ou por produto+cliente.
    _qty_fac_cli: dict[tuple, int] = {}
    _qty_fac_prod_cli: dict[tuple, int] = {}
    _qty_fac_total: dict[str, int] = {}
    _qty_fac_prod: dict[tuple, int] = {}
    if not df_periodo.empty:
        _tmp = df_periodo.assign(
            _cn=df_periodo["CLIENTE"].apply(normalize_text),
            _pn=df_periodo["PRODUTO"].apply(normalize_text),
        )
        for (fn, cn), qty in _tmp.groupby(["FACCAO_N", "_cn"])["QUANTIDADE"].sum().items():
            _qty_fac_cli[(fn, cn)] = int(qty)
            _qty_fac_total[fn] = _qty_fac_total.get(fn, 0) + int(qty)
        for (fn, pn, cn), qty in _tmp.groupby(["FACCAO_N", "_pn", "_cn"])["QUANTIDADE"].sum().items():
            _qty_fac_prod_cli[(fn, pn, cn)] = int(qty)
            _qty_fac_prod[(fn, pn)] = _qty_fac_prod.get((fn, pn), 0) + int(qty)

    _meta_fac_rows = []
    _gaps_fac: dict[str, list[tuple[str, str, int]]] = {}
    for fn, grp in goals_df.groupby("FACCAO_N"):
        faccao_label = grp["FACCAO"].iloc[0]
        meta_dia_fac = 0.0
        meta_sem_fac = 0.0

        sem_cli = grp[(grp["CLIENTE_N"] == "") & (grp["PRODUTO_N"] == "")]
        meta_dia_fac += float(sem_cli["META_DIA"].sum())
        meta_sem_fac += float(sem_cli["META_SEMANA"].sum())

        com_prod_sem_cli = grp[(grp["PRODUTO_N"] != "") & (grp["CLIENTE_N"] == "")]
        meta_dia_fac += float(com_prod_sem_cli["META_DIA"].sum())
        meta_sem_fac += float(com_prod_sem_cli["META_SEMANA"].sum())

        # Pondera pela % de peças que cada cliente representa na produção da
        # facção (não por dias): os clientes costumam ser atendidos no mesmo dia
        # (um dia com produção pra 3 clientes ao mesmo tempo), então contar dias
        # por cliente e somar duplicaria dias sobrepostos. Só entra o cliente que
        # TEM meta cadastrada — do contrário um cliente sem meta (ex.: DECOR)
        # diluiria a meta ponderada sem contribuir nada de volta.
        com_cli_sem_prod = grp[(grp["CLIENTE_N"] != "") & (grp["PRODUTO_N"] == "")]
        if not com_cli_sem_prod.empty:
            total_qty_com_meta = sum(
                _qty_fac_cli.get((fn, cn), 0) for cn in com_cli_sem_prod["CLIENTE_N"]
            )
            for _, grow in com_cli_sem_prod.iterrows():
                cn = grow["CLIENTE_N"]
                qty_cli = _qty_fac_cli.get((fn, cn), 0)
                if total_qty_com_meta > 0 and qty_cli > 0:
                    peso = qty_cli / total_qty_com_meta
                    meta_dia_fac += float(grow["META_DIA"]) * peso
                    meta_sem_fac += float(grow["META_SEMANA"]) * peso

        com_prod_cli = grp[(grp["PRODUTO_N"] != "") & (grp["CLIENTE_N"] != "")]
        if not com_prod_cli.empty:
            for pn, pgrp in com_prod_cli.groupby("PRODUTO_N"):
                clientes_com_meta = set(pgrp["CLIENTE_N"])
                total_prod_com_meta = sum(
                    _qty_fac_prod_cli.get((fn, pn, cn), 0) for cn in clientes_com_meta
                )
                for _, grow in pgrp.iterrows():
                    cn = grow["CLIENTE_N"]
                    qty_pc = _qty_fac_prod_cli.get((fn, pn, cn), 0)
                    if total_prod_com_meta > 0 and qty_pc > 0:
                        peso = qty_pc / total_prod_com_meta
                        meta_dia_fac += float(grow["META_DIA"]) * peso
                        meta_sem_fac += float(grow["META_SEMANA"]) * peso

                # Clientes que produzem esse produto mas não têm meta cadastrada —
                # a produção deles não é medida contra nada, sinaliza pra revisão.
                _clientes_produto = {
                    k[2] for k in _qty_fac_prod_cli if k[0] == fn and k[1] == pn
                }
                for cn_falta in _clientes_produto - clientes_com_meta:
                    qty_falta = _qty_fac_prod_cli.get((fn, pn, cn_falta), 0)
                    if qty_falta > 0:
                        _gaps_fac.setdefault(fn, []).append((pn, cn_falta, qty_falta))

        dias_fac = _dias_fac.get(fn, du_mes)
        meta_mes_fac = int(round(meta_dia_fac * dias_fac))
        _meta_fac_rows.append({
            "FACCAO_N":     fn,
            "FACCAO":       faccao_label,
            "META_DIA_FAC": int(round(meta_dia_fac)),
            "META_MES_FAC": meta_mes_fac,
            "META_SEM_FAC": int(round(meta_sem_fac)),
        })

    meta_fac_df = pd.DataFrame(_meta_fac_rows) if _meta_fac_rows else pd.DataFrame(
        columns=["FACCAO_N", "FACCAO", "META_DIA_FAC", "META_MES_FAC", "META_SEM_FAC"]
    )

    meta_mes_total = int(meta_fac_df["META_MES_FAC"].sum())
    meta_sem_total = int(meta_fac_df["META_SEM_FAC"].sum())
    meta_dia_total = int(meta_fac_df["META_DIA_FAC"].sum())

    # ── rank_df: produção total por facção × meta ────────────────────────────
    if not df_periodo.empty:
        _fac_qty = df_periodo.groupby("FACCAO_N")["QUANTIDADE"].sum().reset_index()
        _fac_label_prod = df_periodo.groupby("FACCAO_N")["FACCAO"].first().reset_index()
        _fac_grp = _fac_qty.merge(_fac_label_prod, on="FACCAO_N", how="left")
    else:
        _fac_grp = pd.DataFrame(columns=["FACCAO_N", "FACCAO", "QUANTIDADE"])

    rank_df = _fac_grp.merge(
        meta_fac_df[["FACCAO_N", "FACCAO", "META_DIA_FAC", "META_MES_FAC", "META_SEM_FAC"]].rename(
            columns={"META_DIA_FAC": "META_DIA", "META_MES_FAC": "META_MES", "META_SEM_FAC": "META_SEMANA",
                     "FACCAO": "FACCAO_META"}
        ),
        on="FACCAO_N", how="outer",
    )
    rank_df["QUANTIDADE"] = rank_df["QUANTIDADE"].fillna(0).astype(int)
    rank_df["META_DIA"] = rank_df["META_DIA"].fillna(0).astype(int)
    rank_df["META_MES"] = rank_df["META_MES"].fillna(0).astype(int)
    rank_df["META_SEMANA"] = rank_df["META_SEMANA"].fillna(0).astype(int)
    rank_df["FACCAO"] = rank_df["FACCAO"].where(
        rank_df["FACCAO"].notna() & (rank_df["FACCAO"] != ""),
        rank_df["FACCAO_META"],
    )
    rank_df.drop(columns=["FACCAO_META"], inplace=True, errors="ignore")

    rank_df["PCT"] = rank_df.apply(
        lambda r: round(r["QUANTIDADE"] / r["META_MES"] * 100, 1) if r["META_MES"] > 0 else None, axis=1
    )
    rank_df["PCT_TOTAL"] = (rank_df["QUANTIDADE"] / max(total_geral, 1) * 100).round(1)
    rank_df["RESTANTE"] = rank_df.apply(
        lambda r: max(0, int(r["META_MES"] - r["QUANTIDADE"])) if r["META_MES"] > 0 else None, axis=1
    )

    # Clientes que produzem um produto já coberto por meta de outros clientes,
    # mas eles mesmos não têm meta cadastrada — a % da meta dessa facção conta a
    # produção deles sem ter contra o que comparar (ver comentário acima em
    # com_prod_cli). Texto pronto para exibir como aviso no relatório.
    def _gaps_texto(fn: str) -> str | None:
        gaps = _gaps_fac.get(fn)
        if not gaps:
            return None
        partes = ", ".join(f"{cn} ({_fmt_qty(qty)} em {pn})" for pn, cn, qty in gaps)
        return partes

    def _fmt_qty(v: int) -> str:
        return f"{v:,}".replace(",", ".")

    rank_df["META_GAPS"] = rank_df["FACCAO_N"].apply(_gaps_texto)

    # Até quando cada facção tem dado — para a diretoria enxergar quem ainda não
    # mandou a produção dos últimos dias, em vez de ler "produção baixa" onde na
    # verdade é "dado incompleto". Referência = facção mais atualizada do grupo
    # (não o fim do período), para não acusar atraso por causa de fim de semana
    # ou feriado em que ninguém produz.
    _ref_data = max(_ultima_data_fac.values()) if _ultima_data_fac else None
    rank_df["ULTIMA_DATA"] = rank_df["FACCAO_N"].map(_ultima_data_fac)
    if _ref_data is not None:
        rank_df["DIAS_ATRASO"] = rank_df["ULTIMA_DATA"].apply(
            lambda d: (_ref_data - d).days if pd.notna(d) else None
        )
    else:
        rank_df["DIAS_ATRASO"] = None

    rank_df = rank_df.sort_values("QUANTIDADE", ascending=False).reset_index(drop=True)

    return {
        "rank_df": rank_df,
        "meta_fac_df": meta_fac_df,
        "meta_mes_total": meta_mes_total,
        "meta_sem_total": meta_sem_total,
        "meta_dia_total": meta_dia_total,
        "total_geral": total_geral,
    }
