"""Caseamento Jogo Duplo × Fundo — corte de Lençol.

Um JOGO DUPLO precisa de um FUNDO correspondente (corte separado). As
quantidades devem casear por OP + tamanho. Quando não caseiam, apontamos a
diferença. JOGO SIMPLES não tem fundo.

Extraído de pages/3_Controle_de_Corte.py para ser reutilizado também na
geração de PDF (pages/10_Relatorios.py) sem duplicar a lógica.
"""

from __future__ import annotations

import re

import pandas as pd


def lencol_classifica_jogo_fundo(cat: str, tecido: str = "") -> tuple[str, str]:
    """Classifica um registro em (tipo, tamanho) a partir da CATEGORIA + TECIDO.

    tipo    ∈ {FUNDO, JOGO_DUPLO, JOGO_SIMPLES, OUTRO}
    tamanho ∈ {SOLTEIRO, CASAL, QUEEN, KING, ''}

    Regras descobertas nos dados reais:
      • O universo de caseamento são os JOGOS DE CAMA → a CATEGORIA menciona "JOGO"
        (ex.: "JOGO DUPLO CS", "FUNDO JOGO ST"). Porta-travesseiro, lençol avulso,
        fronha etc. ficam de fora (tipo OUTRO), mesmo tendo "fundo".
      • Dentro do universo, o TECIDO é a fonte autoritativa de jogo vs fundo:
        a categoria pode dizer "JOGO DUPLO CS" enquanto o tecido diz
        "FUNDO CASAL 4PÇS"  → é FUNDO; e pode dizer "FUNDO JOGO ST" enquanto o
        tecido diz "JOGO SOLTEIRO..."  → é JOGO. O tecido manda; a categoria é só
        fallback quando o tecido não esclarece.
    """
    c = re.sub(r"\s+", " ", str(cat).upper().strip())
    t = re.sub(r"\s+", " ", str(tecido).upper().strip())
    # Fora do universo jogo-cama (categoria não menciona JOGO) → não caseia
    if "JOGO" not in c:
        return ("OUTRO", "")
    txt = c + " " + t
    tamanho = ""
    if "KING" in txt:
        tamanho = "KING"
    elif "QUEEN" in txt or re.search(r"\bQE\b", txt):
        tamanho = "QUEEN"
    elif "CASAL" in txt or re.search(r"\bCS\b", txt):
        tamanho = "CASAL"
    elif "SOLT" in txt or re.search(r"\bST\b", txt):
        tamanho = "SOLTEIRO"
    tipo_jogo = "JOGO_SIMPLES" if ("SIMPLES" in c or "SIMPLES" in t) else "JOGO_DUPLO"
    # TECIDO manda
    if "FUNDO" in t:
        return ("FUNDO", tamanho)
    if "JOGO" in t:
        return (tipo_jogo, tamanho)
    # Tecido não esclarece → usa a categoria (ex.: "FUNDO JOGO QE")
    if "FUNDO" in c:
        return ("FUNDO", tamanho)
    return (tipo_jogo, tamanho)


def lencol_fronha_mult(tamanho: str) -> int:
    """Multiplicador de fronhas por jogo cortado.

    No caseamento, todo tamanho leva 2 fronhas por jogo, exceto o solteiro
    (que leva só 1). A fronha é cortada junto do jogo (mesma peça de corte).
    """
    return 1 if str(tamanho).strip().upper() == "SOLTEIRO" else 2


def lencol_tipos_tams(df: pd.DataFrame) -> tuple[list, list]:
    """Classifica todas as linhas do df em (tipos, tamanhos) de forma determinística.

    Usa zip sobre as colunas em vez de df.apply(axis=1) — este último expande tuplas
    em DataFrame de forma inconsistente e quebra a indexação.
    """
    n = len(df)
    cats = df["CATEGORIA"].astype(str).tolist() if "CATEGORIA" in df.columns else [""] * n
    tecs = df["TECIDO"].astype(str).tolist() if "TECIDO" in df.columns else [""] * n
    tipos, tams = [], []
    for c, t in zip(cats, tecs):
        tp, tm = lencol_classifica_jogo_fundo(c, t)
        tipos.append(tp)
        tams.append(tm)
    return tipos, tams


def lencol_caseamento(df: pd.DataFrame, apenas_com_fundo: bool = True) -> pd.DataFrame:
    """Reconcilia JOGO DUPLO × FUNDO por (OP, TAMANHO).

    Retorna DataFrame com colunas: OP, TAMANHO, JOGO, FUNDO, DIFERENCA, STATUS.
    DIFERENCA = FUNDO − JOGO (saldo de fundos): negativo = faltam fundos;
    positivo = sobram fundos; zero = caseado.

    apenas_com_fundo=True restringe às OPs que tiveram ao menos 1 corte de fundo —
    evita marcar como divergentes as centenas de OPs que simplesmente não usam fundo.
    """
    cols = ["OP", "TAMANHO", "JOGO", "FUNDO", "FRONHA", "DIFERENCA", "STATUS"]
    if df is None or df.empty or "CATEGORIA" not in df.columns:
        return pd.DataFrame(columns=cols)
    d = df.copy()
    _tipos, _tams = lencol_tipos_tams(d)
    d["_TIPO"] = _tipos
    d["_TAM"] = _tams
    d_rel = d[d["_TIPO"].isin(["JOGO_DUPLO", "FUNDO"])]
    if d_rel.empty:
        return pd.DataFrame(columns=cols)
    if apenas_com_fundo:
        ops_com_fundo = set(d_rel.loc[d_rel["_TIPO"] == "FUNDO", "OP"].unique())
        d_rel = d_rel[d_rel["OP"].isin(ops_com_fundo)]
        if d_rel.empty:
            return pd.DataFrame(columns=cols)
    jogo = (d_rel[d_rel["_TIPO"] == "JOGO_DUPLO"]
            .groupby(["OP", "_TAM"])["QUANT"].sum().rename("JOGO"))
    fundo = (d_rel[d_rel["_TIPO"] == "FUNDO"]
             .groupby(["OP", "_TAM"])["QUANT"].sum().rename("FUNDO"))
    rec = pd.concat([jogo, fundo], axis=1).fillna(0).reset_index()
    rec = rec.rename(columns={"_TAM": "TAMANHO"})
    rec["TAMANHO"] = rec["TAMANHO"].replace("", "—")
    rec["JOGO"] = pd.to_numeric(rec["JOGO"], errors="coerce").fillna(0).astype(int)
    rec["FUNDO"] = pd.to_numeric(rec["FUNDO"], errors="coerce").fillna(0).astype(int)
    rec["FRONHA"] = [
        jogo * lencol_fronha_mult(tam)
        for jogo, tam in zip(rec["JOGO"].tolist(), rec["TAMANHO"].tolist())
    ]
    rec["DIFERENCA"] = rec["FUNDO"] - rec["JOGO"]
    rec["STATUS"] = rec["DIFERENCA"].apply(
        lambda x: "✅ Caseado" if x == 0
        else ("🔴 Faltam fundos" if x < 0 else "🟠 Sobram fundos")
    )
    rec = rec.reindex(
        rec["DIFERENCA"].abs().sort_values(ascending=False).index
    ).reset_index(drop=True)
    return rec[cols]
