"""Costura a planilha legada de Produção Geral com a planilha de Facções
numa única linha do tempo contínua (out/2025 → hoje).

Cutover em 01/06/2026: dados anteriores vêm da planilha antiga (mais precisa
antes dessa data — a planilha de facções só tem lançamentos consistentes a
partir de maio/junho de 2026); dados a partir dessa data vêm da planilha de
facções (mais atual e com meta ponderada por cliente/produto).

Os alias abaixo foram validados manualmente com o usuário (não inferidos por
parecença de nome) — ver config/changelog.py para o histórico da decisão.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

CUTOVER_DATE = date(2026, 6, 1)

# CLIENTE como aparece em load_faccoes() (maiúsculo) → nome canônico usado em
# CORES_EMPRESAS / pela planilha antiga. Valores sem entrada aqui viram
# Title Case (BURDAYS -> Burdays) — já bate com CORES_EMPRESAS.
# NIAZITTEX e SEVEN são clientes diferentes e separados — não devem ser
# fundidos num único rótulo (bug relatado pelo usuário 13/07/2026: relatório
# mostrava "Niazittex / Seven" para produção da Seven).
CLIENTE_ALIAS: dict[str, str] = {
    "CORTTEX":   "Cortex",
    "NIAZITTEX": "Niazittex",
    "SEVEN":     "Seven",
    "FORTEX":    "Fortex",
}

# Nome de FACCAO específico da FORMATAÇÃO da planilha antiga (maiúsculo) → nome
# canônico. Só faz sentido aplicar na fatia legada — esses formatos (parênteses,
# "solto" etc.) não ocorrem na planilha de facções. Validado manualmente linha a
# linha com o usuário. Nomes sem entrada aqui (majoritariamente quarterizadas
# individuais que já batem com PRESTADOR da aba QUARTERIZADAS, ou facções que
# pararam/começaram a produzir) passam sem alteração.
FACCAO_ALIAS_LEGADO: dict[str, str] = {
    "ZANATTEX":           "GGTTEX RUTE",
    "MEGA PREVEN BARIRI": "MEGA BARIRI",
    "MEGA (BOCA)":        "MEGA PREVEN (BOCA)",
    "GGTTEX (RUTE)":      "GGTTEX RUTE",
    "GGTTEX (CORTINA)":   "GGTTEX CORTINA",
    "GGTTEX":             "GGTTEX CORTINA",   # "GGTTEX" solto na planilha antiga = a Cortina (confirmado 06/07/2026)
    "LITTEX":             "LITEX",
    "ZARO TEXTIL":        "ZARO (LUIS)",
}

# Typos de nome de prestador que podem ocorrer nas DUAS planilhas (lançamento
# manual) — aplicado no dataset já combinado (legado + facções), não só na
# fatia legada. Ex.: "NATHIELLY" reapareceu na planilha de facções ao vivo
# depois de já ter sido corrigido só na legada (06/07/2026).
FACCAO_TYPOS: dict[str, str] = {
    "NATHIELLY":       "NATCHIELLY",
    "PREVITEX MATRIZ": "PREVITTEX MATRIZ",
    "ELIZANGELA":      "ELISANGELA",       # mesma pessoa, typo S/Z
}

# Facções renomeadas pelo negócio, mas cujo GID na planilha de facções ainda
# está configurado (FACCOES_ABAS) com o label INTERNO antigo (o código busca
# por GID, que é estável — só o nome de exibição da aba no Sheets mudou).
# Aplicado no final, na coluna FACCAO já combinada (legado + facções), pra
# exibir sempre o nome atual, nunca o antigo — confirmado com o usuário
# 06/07/2026 (ele já via isso documentado em config/settings.py:
# FACCOES_FACCAO_ALIAS, usado lá pra casar meta, na mesma direção).
FACCAO_RENOMEADA: dict[str, str] = {
    "ZANATTA":           "GIATTEX",           # Zanatta virou Giattex
    "PREVITTEX FILIAL":  "MEGA PREVEN MATRIZ",  # Previttex Filial virou Mega Preven Matriz
    # FELIPE é o prestador que produz para a facção fixa LITEX — na planilha de
    # facções ele aparece como prestador individual na aba QUARTERIZADAS, mas
    # sua produção é a mesma coisa que a facção LITEX (mesma que recebia o nome
    # "LITTEX" na planilha antiga). Unificado sob o nome fixo, confirmado com o
    # usuário 06/07/2026 — ele deixa de aparecer separado em QUARTERIZADAS.
    "FELIPE":            "LITEX",
}

# Prestadores quarterizados que pararam de produzir — pedido do usuário
# 06/07/2026 pra tirar do dashboard (só poluíam a lista, sem produção recente).
# A linha do tempo histórica deles é removida do dataset unificado inteiro.
PRESTADORES_INATIVOS: set[str] = {
    "ANGELA BANDEIRANTES",
    "ANJOS TEXTEIS",
    "DAIANE",
    "MARA",
    "MARCIA GONÇALVES",
    "MARIA GESSI",
    "MARIA HELENA",
}

_COLUNAS_UNIFICADAS = [
    "DATA", "CLIENTE", "FACCAO", "PRODUTO", "QUANTIDADE", "META_DIARIA", "FONTE", "OBSERVACAO",
]

# Rótulo do grupo que junta todos os prestadores individuais (quarterizadas).
GRUPO_QUARTERIZADAS = "QUARTERIZADAS"


def faccoes_fixas() -> set[str]:
    """Conjunto das facções 'fixas' (não-quarterizadas), no nome canônico atual.

    Derivado de config.settings.FACCOES_ABAS: cada aba com nome fixo (faccao !=
    None) é uma facção fixa; a aba QUARTERIZADAS (faccao=None, por_prestador)
    agrupa os prestadores individuais. Aplica FACCAO_RENOMEADA pra usar o nome
    atual (ex.: label interno ZANATTA vira GIATTEX). Tudo que NÃO estiver aqui é
    tratado como quarterizada — o que já inclui ZARO (LUIS) e os nomes de pessoa
    física, e exclui MEGA (BOCA)/MEGA (CARLINE) etc., que são fixas.
    """
    from config.settings import FACCOES_ABAS
    fixas = set()
    for cfg in FACCOES_ABAS.values():
        nome = cfg.get("faccao")
        if nome:
            fixas.add(FACCAO_RENOMEADA.get(nome, nome))
    return fixas


def is_quarterizada(faccao: str) -> bool:
    """True se a facção é um prestador individual (não uma das facções fixas)."""
    return faccao not in faccoes_fixas()


def grupo_de(faccao: str) -> str:
    """Grupo de exibição da facção: ela mesma se fixa, senão GRUPO_QUARTERIZADAS."""
    return faccao if faccao in faccoes_fixas() else GRUPO_QUARTERIZADAS


def _normalizar_produto_legado(faccao: str, cliente: str, produto: str) -> str:
    """'JOGOS'/'JOGO' na planilha antiga é uma abreviação que representa
    produtos diferentes dependendo de quem produziu — vira 'JOGO DE CAMA'
    quando a facção é a Carline, ou 'JOGO DE CAMA PP' quando o cliente é
    Marcelino produzido por outra facção. Confirmado com o usuário 06/07/2026.
    """
    p = str(produto).strip().upper()
    if p not in ("JOGOS", "JOGO"):
        return produto
    if faccao == "MEGA (CARLINE)":
        return "JOGO DE CAMA"
    if str(cliente).strip().upper() == "MARCELINO":
        return "JOGO DE CAMA PP"
    return produto


def _achatar_legado(all_data_legado: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """all_data_legado: dict[empresa] -> DataFrame[Faccao, Produto, Data,
    Quantidade, Meta Diaria, ...] (saída de load_all_data() em
    pages/2_Producao_Geral.py). Achata em um único DataFrame no schema
    unificado, restrito a DATA < CUTOVER_DATE."""
    frames = []
    for empresa, df in all_data_legado.items():
        if df is None or df.empty:
            continue
        faccao_col = df["Faccao"].astype(str).str.strip().str.upper().map(
            lambda v: FACCAO_ALIAS_LEGADO.get(v, v)
        )
        # CLIENTE: usa a coluna "Cliente" da própria linha quando existe (caso
        # de "Niazittex / Seven" — uma única aba/empresa carregando dois
        # clientes DIFERENTES, ver pages/2_Producao_Geral.py::
        # _load_niazitex_suplementar) — sem isso, todas as linhas dessa
        # empresa (Niazittex e Seven juntos) eram rotuladas com o nome da
        # aba/empresa "Niazittex / Seven", misturando dois clientes que devem
        # ficar separados nos relatórios (feedback do usuário 13/07/2026).
        # Demais empresas (Burdays, Camesa etc.) não têm coluna "Cliente"
        # própria — o cliente delas É o nome da empresa/aba, sem mudança.
        cliente_col = (
            df["Cliente"] if "Cliente" in df.columns else empresa
        )
        sub = pd.DataFrame({
            "DATA":        pd.to_datetime(df["Data"]),
            "CLIENTE":     cliente_col,
            "FACCAO":      faccao_col,
            "PRODUTO":     [
                _normalizar_produto_legado(f, empresa, p)
                for f, p in zip(faccao_col, df["Produto"])
            ],
            "QUANTIDADE":  df["Quantidade"],
            "META_DIARIA": pd.to_numeric(df.get("Meta Diaria"), errors="coerce").fillna(0.0),
            "OBSERVACAO":  "",  # planilha antiga não tem essa coluna
        })
        frames.append(sub)

    if not frames:
        return pd.DataFrame(columns=_COLUNAS_UNIFICADAS)

    out = pd.concat(frames, ignore_index=True)
    out["FONTE"] = "legado"
    out = out[out["DATA"] < pd.Timestamp(CUTOVER_DATE)]
    return out[_COLUNAS_UNIFICADAS]


def _preparar_faccoes(df_fac: pd.DataFrame) -> pd.DataFrame:
    """df_fac: saída de utils.faccao_loader.load_faccoes() — colunas DATA,
    FACCAO, ABA, PRESTADOR, PRODUTO, CLIENTE, QUANTIDADE, OBSERVACAO. Restringe a
    DATA >= CUTOVER_DATE e normaliza nome de cliente pro padrão canônico.
    META_DIARIA fica 0 aqui — meta dessa fatia é calculada à parte
    (_calcular_meta_cliente_periodo / _calcular_meta_faccao_periodo), pois a
    ponderação de calcular_meta_faccoes() usa o total do período, não faz
    sentido embutir por linha."""
    if df_fac is None or df_fac.empty:
        return pd.DataFrame(columns=_COLUNAS_UNIFICADAS)

    out = df_fac[["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"]].copy()
    out["CLIENTE"] = out["CLIENTE"].apply(
        lambda c: CLIENTE_ALIAS.get(str(c).strip().upper(), str(c).strip().title())
    )
    out["META_DIARIA"] = 0.0
    out["FONTE"] = "faccoes"
    # Defensivo: coluna nova (adicionada 14/07/2026) — se load_faccoes() vier
    # de uma versão antiga em cache sem essa coluna, não deve quebrar.
    out["OBSERVACAO"] = df_fac["OBSERVACAO"] if "OBSERVACAO" in df_fac.columns else ""
    out = out[out["DATA"] >= pd.Timestamp(CUTOVER_DATE)]
    return out[_COLUNAS_UNIFICADAS]


def load_producao_unificada(all_data_legado: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Dataset único DATA/CLIENTE/FACCAO/PRODUTO/QUANTIDADE/META_DIARIA/FONTE,
    costurando a planilha antiga (< CUTOVER_DATE) com a planilha de facções
    (>= CUTOVER_DATE). Usado tanto pela dimensão Cliente (agrupar por CLIENTE)
    quanto pela dimensão Facção (agrupar por FACCAO).

    all_data_legado: já deve vir carregado pelo chamador (ex.: load_all_data()
    de pages/2_Producao_Geral.py) — este módulo não importa páginas Streamlit.
    """
    from utils.faccao_loader import load_faccoes

    df_legado = _achatar_legado(all_data_legado)
    df_novo = _preparar_faccoes(load_faccoes())
    df = pd.concat([df_legado, df_novo], ignore_index=True)
    # Se um dos dois lados vier vazio (ex.: falha de rede na planilha antiga),
    # pd.concat faz a coluna DATA virar dtype "object" em vez de datetime64,
    # quebrando qualquer .dt.date usado depois pelos chamadores — força de volta.
    df["DATA"] = pd.to_datetime(df["DATA"])
    if not df.empty:
        df["FACCAO"] = df["FACCAO"].map(
            lambda f: FACCAO_RENOMEADA.get(FACCAO_TYPOS.get(f, f), FACCAO_TYPOS.get(f, f))
        )
        df = df[~df["FACCAO"].isin(PRESTADORES_INATIVOS)]
    return df


def _calcular_meta_cliente_periodo(
    df_periodo_completo: pd.DataFrame,
    cliente: str,
    ano_sel: int,
    mes_sel: int,
) -> dict:
    """Produzido + meta do período para um CLIENTE, somando as duas fontes.

    - Fatia legada: soma de META_DIARIA já embutida por linha (vem do Plano de
      Metas, por mês/ano — mesma lógica que _calc_meta já usa hoje).
    - Fatia nova (facções): calcular_meta_faccoes() só expõe meta agregada por
      FACCAO, não por cliente. Aproximação: para cada facção que atende esse
      cliente no período, aloca a META_MES daquela facção proporcionalmente à
      fatia de peças que o cliente representa na produção da facção no mesmo
      período. Não é idêntico ao peso "contratual" que calcular_meta_faccoes
      usa internamente para metas definidas por cliente, mas é uma
      aproximação razoável e documentada — ver PADROES do plano de unificação.

    df_periodo_completo: já filtrado pelo período (Ano/Mês/dias), SEM filtro
    de cliente — precisa dos outros clientes da mesma facção pra calcular a
    proporção.
    """
    from utils.faccoes_metas_calc import calcular_meta_faccoes

    legado = df_periodo_completo[df_periodo_completo["FONTE"] == "legado"]
    novo = df_periodo_completo[df_periodo_completo["FONTE"] == "faccoes"]

    legado_cliente = legado[legado["CLIENTE"] == cliente]
    produzido_legado = float(legado_cliente["QUANTIDADE"].sum())
    meta_legado = float(legado_cliente["META_DIARIA"].sum())

    novo_cliente = novo[novo["CLIENTE"] == cliente]
    produzido_novo = float(novo_cliente["QUANTIDADE"].sum())
    meta_novo = 0.0
    if not novo.empty:
        resultado = calcular_meta_faccoes(
            novo[["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"]], ano_sel, mes_sel
        )
        rank_df = resultado["rank_df"]
        qty_fac_cliente = novo_cliente.groupby("FACCAO")["QUANTIDADE"].sum()
        qty_fac_total = novo.groupby("FACCAO")["QUANTIDADE"].sum()
        for faccao, qty_cli in qty_fac_cliente.items():
            qty_tot = qty_fac_total.get(faccao, 0)
            if qty_tot <= 0:
                continue
            linha = rank_df[rank_df["FACCAO"] == faccao]
            if linha.empty:
                continue
            meta_mes_fac = float(linha.iloc[0]["META_MES"])
            meta_novo += meta_mes_fac * (qty_cli / qty_tot)

    return {
        "produzido": produzido_legado + produzido_novo,
        "meta_periodo": meta_legado + meta_novo,
        # Breakdown por fonte — usado por render_company (Produção Geral) pra somar
        # só a contribuição da fatia nova a um meta_periodo já calculado por _calc_meta
        # pra fatia legada, sem contar a fatia legada duas vezes.
        "produzido_legado": produzido_legado,
        "meta_legado": meta_legado,
        "produzido_novo": produzido_novo,
        "meta_novo": meta_novo,
    }


def _calcular_meta_faccao_periodo(
    df_periodo_completo: pd.DataFrame,
    faccao: str,
    ano_sel: int,
    mes_sel: int,
) -> dict:
    """Produzido + meta do período para uma FACCAO, somando as duas fontes.

    - Fatia legada: soma de META_DIARIA das linhas dessa facção (já embutida
      por linha, vem do Plano de Metas).
    - Fatia nova: calcular_meta_faccoes() já agrega por facção — usa META_MES
      direto do rank_df, sem precisar de rateio (diferente da versão por
      cliente acima).
    """
    from utils.faccoes_metas_calc import calcular_meta_faccoes

    legado = df_periodo_completo[
        (df_periodo_completo["FONTE"] == "legado") & (df_periodo_completo["FACCAO"] == faccao)
    ]
    produzido_legado = float(legado["QUANTIDADE"].sum())
    meta_legado = float(legado["META_DIARIA"].sum())

    novo = df_periodo_completo[df_periodo_completo["FONTE"] == "faccoes"]
    produzido_novo = float(novo[novo["FACCAO"] == faccao]["QUANTIDADE"].sum())
    meta_novo = 0.0
    if not novo.empty:
        resultado = calcular_meta_faccoes(
            novo[["DATA", "FACCAO", "PRODUTO", "CLIENTE", "QUANTIDADE"]], ano_sel, mes_sel
        )
        linha = resultado["rank_df"][resultado["rank_df"]["FACCAO"] == faccao]
        if not linha.empty:
            meta_novo = float(linha.iloc[0]["META_MES"])

    return {
        "produzido": produzido_legado + produzido_novo,
        "meta_periodo": meta_legado + meta_novo,
    }
