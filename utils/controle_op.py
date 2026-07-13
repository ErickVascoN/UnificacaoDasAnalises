"""Controle de OP — cruzamento Programação x Corte, compartilhado entre
pages/4_Controladoria_Programacao.py, pages/10_Relatorios.py (aba
Programação) e pages/11_Controle_de_OP.py.

Extraído de pages/4_Controladoria_Programacao.py (onde a lógica nasceu) pra
eliminar a duplicação que já existia entre pages/4 e o
_calcular_df_agg() de pages/10_Relatorios.py — os dois reimplementavam o
mesmo cruzamento de forma levemente diferente.
"""

import io
import logging

import pandas as pd
import streamlit as st

# constantes das planilhas de origem
PROG_ID     = "1FeTwrPEBOcC6RmD_5zh8NQLwOrYO87XA"
PROG_GID    = "708887209"
MANTA_ID    = "1KLbNpw-P28YgoijXfMXU-zRQULuDHMMB"
MANTA_GID   = "1544210185"
IACANGA_ID  = "1FBpCrq29_e1UBNwBlcgPTz66tbpUsgcgtzfXi4DcORU"
IACANGA_GID = "0"
LENCOL_ID   = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_GID  = "1396046910"
CARTEIRA_ID  = "1U-iNIQRqKOIBrDZ86ZE5uJW6IQCzugJ7"
CARTEIRA_GID = "611396912"
CACHE_TTL   = 300


def _fetch(sheet_id: str, gid: str) -> str | None:
    from utils.cache_manager import get_raw
    return get_raw(sheet_id, gid, ttl=CACHE_TTL)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_programacao() -> pd.DataFrame:
    texto = _fetch(PROG_ID, PROG_GID)
    if not texto:
        raise ConnectionError("Não foi possível baixar a planilha de programação.")

    # Detecta linha real do cabeçalho (pode haver título antes)
    linhas = texto.splitlines()
    header_row = 0
    for i, linha in enumerate(linhas[:10]):
        linha_up = linha.upper()
        if "SEMANA" in linha_up and "CLIENTE" in linha_up:
            header_row = i
            break

    df = pd.read_csv(io.StringIO(texto), skiprows=header_row, header=0, dtype=str)
    df.columns = df.columns.str.strip()

    # Normaliza nomes de colunas para encontrar variações de encoding
    col_map = {c.upper().strip(): c for c in df.columns}

    def _col(nome: str) -> str:
        """Retorna o nome real da coluna, case-insensitive."""
        return col_map.get(nome.upper().strip(), nome)

    # Garante colunas essenciais
    essenciais = [
        "PED. CLIENTE", "SEMANA", "CLIENTE", "LOCAL", "PRODUTO",
        "PED. INT", "OP INTERNA", "OC", "DESCRIÇÃO DO PRODUTO",
        "QNT. PROG", "DATA INICIO", "DATA FINALIZADO", "PREV. INDUSTRIALIZAÇÃO",
    ]
    for col in essenciais:
        real = _col(col)
        if real not in df.columns:
            df[col] = ""
        elif real != col:
            df[col] = df[real]

    df["PED. CLIENTE"] = df["PED. CLIENTE"].astype(str).str.strip()
    df["QNT. PROG"]    = pd.to_numeric(df["QNT. PROG"], errors="coerce").fillna(0).astype(int)
    df["SEMANA"]       = df["SEMANA"].astype(str).str.strip()
    df["CLIENTE"]      = df["CLIENTE"].astype(str).str.strip()
    df["LOCAL"]        = df["LOCAL"].astype(str).str.strip()

    invalidos = {"", "NAN", "NONE", "N/A"}

    def _valido(serie: pd.Series) -> pd.Series:
        # fillna ANTES do astype(str): no pandas 3.x, Series.astype(str) não
        # converte NaN/None em texto "nan" — mantém NaN real. Sem o fillna,
        # células genuinamente vazias (NaN) passavam nesse check como
        # "válidas" (NaN != "" e NaN not in invalidos), deixando linhas
        # praticamente em branco (só CLIENTE preenchido) entrarem com
        # _CHAVE = NaN — que o groupby() do Resumo descarta silenciosamente,
        # enquanto a aba Detalhe (sem groupby) continuava mostrando essas
        # linhas com cortes reais casados. Bug relatado pelo usuário
        # 13/07/2026 (Semana 27: cortes parciais sumindo do Resumo).
        s = serie.fillna("").astype(str).str.strip()
        return s.ne("") & ~s.str.upper().isin(invalidos)

    # Fallback de OP: quando NÃO existe a OP (PED. CLIENTE), a OP INTERNA ocupa o lugar
    # dela e passa a ser a OP daquela linha. Se a OP existe, OP INTERNA é ignorada
    # (não entra no cruzamento, para não gerar match falso).
    ped_valido = _valido(df["PED. CLIENTE"])
    if "OP INTERNA" in df.columns:
        usar_opint = ~ped_valido & _valido(df["OP INTERNA"])
        df.loc[usar_opint, "PED. CLIENTE"] = (
            df.loc[usar_opint, "OP INTERNA"].astype(str).str.strip()
        )

    # Mantém linhas com OP (própria ou via OP INTERNA) e também as sem OP nenhuma
    # mas com produção real (ex: MANTA CELTA sem OP, só quantidade programada).
    ped_valido = _valido(df["PED. CLIENTE"])
    tem_producao = df["QNT. PROG"] > 0
    df = df[ped_valido | tem_producao].reset_index(drop=True)

    # _CHAVE = a OP (PED. CLIENTE). Linhas que continuam sem OP nenhuma agrupam por
    # CLIENTE+PRODUTO+SEMANA (sub-linhas do mesmo item viram uma OP só); OP exibida vazia.
    df["_CHAVE"] = df["PED. CLIENTE"]
    sem_op = ~_valido(df["PED. CLIENTE"])
    df.loc[sem_op, "_CHAVE"] = (
        "SEMOP|"
        + df.loc[sem_op, "CLIENTE"].astype(str).str.strip() + "|"
        + df.loc[sem_op, "PRODUTO"].astype(str).str.strip() + "|"
        + df.loc[sem_op, "SEMANA"].astype(str).str.strip()
    )
    df.loc[sem_op, "PED. CLIENTE"] = ""  # exibido como vazio/"—"

    try:
        from utils.db_manager import upsert_df
        _cols_db = ["_CHAVE", "SEMANA", "CLIENTE", "LOCAL", "PRODUTO", "QNT. PROG", "DATA INICIO", "DATA FINALIZADO"]
        _cols_exist = [c for c in _cols_db if c in df.columns]
        upsert_df(df[_cols_exist], "programacao_corte", ["_CHAVE", "PRODUTO"])
    except Exception:
        logging.warning("db_manager: falha ao salvar programacao_corte", exc_info=True)

    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_cortes() -> pd.DataFrame:
    """
    Carrega dados de corte de três fontes:
      - Arealva/Manta  (QUANTIDADE, header simples)
      - Iacanga        (QUANTIDADE, header simples)
      - Lençol Arealva (QUANT, pode ter linha de título → header detection)

    Retorna colunas [OP, QUANTIDADE, FONTE, SEMANA, DATA].
    SEMANA é o nº ISO da semana derivado da coluna DATA — essencial para que
    o join não some cortes de semanas anteriores para OPs reutilizadas (ex: PROG 81).
    DATA (por registro) é usada pra calcular a data de conclusão de cada OP
    (ver calcular_data_conclusao).
    """
    from utils.date_parser import parse_date_series
    frames = []

    # Manta e Iacanga: header simples, coluna DATA correta → parsing direto.
    # Rótulos padronizados: Arealva = Zanattex, Iacanga = Giattex.
    # col_mat = coluna com o material/produto; col_cli = coluna do cliente/empresa
    # (None → usa cli_fixo). Manta Arealva não tem cliente → sempre "Camesa".
    _SOURCES = [
        (MANTA_ID,   MANTA_GID,   "Zanattex", "QUANTIDADE", "PRODUTO", None,      "Camesa"),
        (IACANGA_ID, IACANGA_GID, "Giattex",  "QUANTIDADE", "PRODUTO", "CLIENTE", ""),
    ]

    for sid, gid, fonte, col_qtd, col_mat, col_cli, cli_fixo in _SOURCES:
        texto = _fetch(sid, gid)
        if not texto:
            logging.debug(f"load_cortes: sem texto para {fonte}")
            continue
        try:
            df = pd.read_csv(io.StringIO(texto), header=0, dtype=str)
            df.columns = df.columns.str.strip()

            if "OP" not in df.columns or col_qtd not in df.columns:
                logging.debug(
                    f"load_cortes: {fonte} sem colunas esperadas. "
                    f"Disponíveis: {list(df.columns)}"
                )
                continue

            sub = df[["OP", col_qtd]].copy()
            sub = sub.rename(columns={col_qtd: "QUANTIDADE"})
            sub["FONTE"] = fonte
            sub["MATERIAL"] = (
                df[col_mat].astype(str).str.strip() if col_mat in df.columns else ""
            )
            sub["CLIENTE"] = (
                df[col_cli].astype(str).str.strip()
                if (col_cli and col_cli in df.columns) else cli_fixo
            )

            # Derivar SEMANA ISO a partir de DATA (para join por semana)
            if "DATA" in df.columns:
                datas = parse_date_series(df["DATA"])
                sub["SEMANA"] = datas.dt.isocalendar().week.astype("Int64")
                sub["DATA"] = datas
            else:
                sub["SEMANA"] = pd.array([pd.NA] * len(sub), dtype="Int64")
                sub["DATA"] = pd.NaT

            frames.append(sub)
            logging.debug(f"load_cortes: {fonte} → {len(sub)} registros")

        except Exception as e:
            logging.debug(f"load_cortes: parse {fonte}: {e}")

    # Lençol: estrutura complexa (coluna "DATA" contém empresa, data real noutra coluna).
    # Usa o loader dedicado, que mapeia as colunas por conteúdo corretamente.
    try:
        from utils.lencol_loader_smart import load_lencol_smart_xlsx
        df_len = load_lencol_smart_xlsx()
        if not df_len.empty and "OP" in df_len.columns and "QUANT" in df_len.columns:
            sub = pd.DataFrame({
                "OP": df_len["OP"],
                "QUANTIDADE": df_len["QUANT"],
                "FONTE": "Lençol",
                "MATERIAL": (
                    # Concatena CATEGORIA + TECIDO para que o matching distingua
                    # ex: "JOGO SIMPLES CS" + "JOGO LENÇOL + FRONHAS" vs JOGO DUPLO.
                    (
                        df_len["CATEGORIA"].fillna("").astype(str).str.strip()
                        + " "
                        + df_len["TECIDO"].fillna("").astype(str).str.strip()
                    ).str.strip()
                    if ("TECIDO" in df_len.columns and "CATEGORIA" in df_len.columns)
                    else (df_len["TECIDO"].astype(str).str.strip() if "TECIDO" in df_len.columns else "")
                ),
                "CLIENTE": (
                    df_len["EMPRESA"].astype(str).str.strip()
                    if "EMPRESA" in df_len.columns else ""
                ),
            })
            if "DATA" in df_len.columns:
                datas = pd.to_datetime(df_len["DATA"], errors="coerce")
                sub["SEMANA"] = datas.dt.isocalendar().week.astype("Int64")
                sub["DATA"] = datas
            else:
                sub["SEMANA"] = pd.array([pd.NA] * len(sub), dtype="Int64")
                sub["DATA"] = pd.NaT
            frames.append(sub)
            logging.debug(f"load_cortes: Lençol → {len(sub)} registros")
        else:
            logging.debug("load_cortes: Lençol vazio ou sem colunas OP/QUANT")
    except Exception as e:
        logging.debug(f"load_cortes: parse Lençol: {e}")

    if not frames:
        return pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE", "SEMANA", "DATA"])

    out = pd.concat(frames, ignore_index=True)
    out["OP"]         = out["OP"].astype(str).str.strip()
    out["QUANTIDADE"] = pd.to_numeric(out["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
    if "MATERIAL" not in out.columns:
        out["MATERIAL"] = ""
    out["MATERIAL"] = out["MATERIAL"].astype(str).str.strip().replace(
        {"nan": "", "NaN": "", "None": "", "<NA>": "", "0": ""}
    )
    if "CLIENTE" not in out.columns:
        out["CLIENTE"] = ""
    out["CLIENTE"] = out["CLIENTE"].astype(str).str.strip().replace(
        {"nan": "", "NaN": "", "None": "", "<NA>": "", "0": ""}
    )
    # "0" é usado como placeholder/lixo em algumas linhas (ex.: retrabalho
    # sem OP definida) — não é uma OP de verdade, exclui pra não virar uma
    # falsa "OP fora da programação" agregando lançamentos sem relação.
    invalidos = {"", "NAN", "NONE", "N/A", "SEM OP", "0"}
    out = out[~out["OP"].str.upper().isin(invalidos)]
    return out


def _parse_float_br(s: str) -> float:
    """Converte string numérica BR ('1.234,56') ou US ('1,234.56') pra float."""
    import re as _re
    s = _re.sub(r'[^\d,.\-]', '', str(s).strip())
    if not s:
        return 0.0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _load_carteira_lookup() -> pd.DataFrame:
    """PEDIDO/DESCRIÇÃO/QUANTIDADE da Carteira de Pedidos, só pra tentar
    preencher produto/quantidade de referência de OPs cortadas fora da
    programação, quando o corte não traz o nome do produto. Mesma planilha
    e mesmos índices de coluna de
    pages/9_Carteira_de_Pedidos.py::load_carteira() (cabeçalho não é
    confiável — acesso posicional, replicado aqui de propósito).

    Cruzamento best-effort: testado com dados reais (10/07/2026) que só
    ~2% das OPs de Programação têm PEDIDO correspondente na Carteira — os
    espaços de numeração são majoritariamente independentes. Ainda assim
    vale tentar pra esse caso específico (preencher o que puder), só não
    dá pra usar como join confiável de verdade."""
    import csv
    from utils.normalize import normalize_op

    texto = _fetch(CARTEIRA_ID, CARTEIRA_GID)
    if not texto:
        return pd.DataFrame(columns=["OP_NORM", "PRODUTO", "QUANTIDADE"])

    rows = list(csv.reader(io.StringIO(texto)))
    registros = []
    for row in rows[1:]:
        if len(row) < 11 or not row[0].strip():
            continue
        pedido = row[2].strip()
        opn = normalize_op(pedido)
        if not opn:
            continue
        qt = _parse_float_br(row[8]) if len(row) > 8 else 0.0
        desc = row[14].strip() if len(row) > 14 else ""
        registros.append({"OP_NORM": opn, "PRODUTO": desc, "QUANTIDADE": qt})

    if not registros:
        return pd.DataFrame(columns=["OP_NORM", "PRODUTO", "QUANTIDADE"])

    df = pd.DataFrame(registros)
    return df.groupby("OP_NORM", as_index=False).agg(
        PRODUTO=("PRODUTO", lambda s: " / ".join(sorted({v for v in s if v}))),
        QUANTIDADE=("QUANTIDADE", "sum"),
    )


# lógica de cruzamento
LIMIAR_CONCLUSAO = 0.96  # >=96% cortado já conta como "Concluído" (perda/refile)


def _status_corte(cortada: int, prog_total: int) -> str:
    if cortada <= 0:
        return "Pendente"
    eficiencia = cortada / prog_total if prog_total > 0 else 0
    if eficiencia >= LIMIAR_CONCLUSAO:
        return "Concluído"
    return "Parcial"


def enriquecer(df_prog: pd.DataFrame, df_cortes: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza programação com cortes.

    OPs com 1 produto  → total cortado da OP (comportamento anterior).
    OPs com N produtos → matching por similaridade entre DESCRIÇÃO DO PRODUTO
                         (programação) e MATERIAL (corte), linha a linha.
                         Cada produto recebe sua própria quantidade cortada e
                         seu próprio QNT_PROG_TOTAL, gerando status independentes.
    """
    import re as _re
    import difflib

    df = df_prog.copy()
    if "_CHAVE" not in df.columns:
        df["_CHAVE"] = df["PED. CLIENTE"]

    # Em várias linhas a coluna PRODUTO da planilha guarda só o código
    # (ex.: "700075-2021-25", "1.12636.02.9999") em vez do nome — quando
    # DESCRIÇÃO DO PRODUTO existe, ela é o nome legível de verdade. Prefere
    # a descrição sempre que disponível; sem isso, a tabela de OPs mostrava
    # código em vez de nome de produto (feedback do usuário 10/07/2026). Não
    # muda o matching multi-produto abaixo — ele já usa essa mesma
    # preferência (DESCRIÇÃO DO PRODUTO ou PRODUTO) pra montar `desc`.
    if "DESCRIÇÃO DO PRODUTO" in df.columns:
        _desc = df["DESCRIÇÃO DO PRODUTO"].astype(str).str.strip()
        _desc_valida = _desc.ne("") & ~_desc.str.upper().isin({"NAN", "NONE", "N/A"})
        df["PRODUTO"] = _desc.where(_desc_valida, df["PRODUTO"])

    # QNT_PROG_TOTAL inicial = soma da OP inteira (usado para OPs de 1 produto)
    total_prog_op = df.groupby(["_CHAVE", "SEMANA"])["QNT. PROG"].transform("sum")
    df["QNT_PROG_TOTAL"] = total_prog_op.fillna(0).astype(int)

    if df_cortes.empty:
        df["QNT_CORTADA"]  = 0
        df["STATUS_PROD"]  = "Não Iniciado"
        df["STATUS_CORTE"] = "Pendente"
        df["DIFERENÇA"]    = -df["QNT_PROG_TOTAL"]
        df["EFICIÊNCIA_%"] = 0.0
        return df

    from utils.normalize import normalize_op, normalize_text
    _cortes = df_cortes.copy()
    _cortes["_OPN"] = _cortes["OP"].map(normalize_op)
    _cortes = _cortes[_cortes["_OPN"].ne("")]

    # Total cortado por OP (fallback para OPs de 1 produto).
    # No lençol cada JOGO gera duas linhas de corte: CIMA e FUNDO.
    # Só a CIMA (ou qualquer uma, desde que uma) representa "1 jogo cortado";
    # somar as duas dobra a contagem e infla a eficiência para ~200%.
    # IMPORTANTE: "Fundo Porta" no Giattex/Zanattex é produto legítimo — o filtro
    # é restrito à fonte Lençol para não excluir esses cortes.
    if "MATERIAL" in _cortes.columns and "FONTE" in _cortes.columns:
        _fonte_up = _cortes["FONTE"].astype(str).str.upper()
        _mat_str  = _cortes["MATERIAL"].astype(str)
        _is_lencol_fundo = (
            _fonte_up.str.contains("LEN", na=False) &
            _mat_str.str.contains(r"\bFUNDO\b", case=False, na=False, regex=True)
        )
        # Só exclui FUNDO quando a mesma OP também tem registros não-FUNDO (CIMA).
        # OPs que só possuem registros FUNDO (pedidos exclusivos de lençol fundo)
        # ficam preservadas — sem isso, QNT_CORTADA sempre daria 0 para elas.
        _ops_com_nao_fundo = set(_cortes.loc[~_is_lencol_fundo, "_OPN"].unique())
        _excluir = _is_lencol_fundo & _cortes["_OPN"].isin(_ops_com_nao_fundo)
        _op_map: dict = _cortes[~_excluir].groupby("_OPN")["QUANTIDADE"].sum().to_dict()
    else:
        _op_map: dict = _cortes.groupby("_OPN")["QUANTIDADE"].sum().to_dict()

    # Mapa de materiais: op_norm → [(material_norm, qtd)]
    # Usado para matching individual quando a OP tem múltiplos produtos.
    _prod_map: dict[str, list] = {}
    if "MATERIAL" in _cortes.columns:
        _com_mat = _cortes[_cortes["MATERIAL"].astype(str).str.strip().ne("")]
        if not _com_mat.empty:
            _cm = _com_mat.copy()
            _cm["_MAT"] = _cm["MATERIAL"].apply(normalize_text)
            _cm = _cm[_cm["_MAT"].ne("")]
            for opn, grp in _cm.groupby("_OPN"):
                _prod_map[opn] = list(grp.groupby("_MAT")["QUANTIDADE"].sum().items())

    # "_PEDN" é a chave de join com o corte. Usa PED. CLIENTE primeiro; se não
    # existir nos cortes, tenta PED. INT / OP INTERNA / OC. Isso permite que
    # "PROG 83" (corte) → "83" bata com a linha de programação que tem PED. INT=83,
    # mesmo quando o PED. CLIENTE é "700761-3722-27" (inexistente no corte).
    _known_opns: set[str] = set(_cortes["_OPN"].unique())
    _alt_cols_pedn = [c for c in ["PED. INT", "OP INTERNA", "OC"] if c in df.columns]

    def _best_pedn(row) -> str:
        k = normalize_op(str(row.get("PED. CLIENTE", "")))
        if k in _known_opns:
            return k
        for _ac in _alt_cols_pedn:
            k2 = normalize_op(str(row.get(_ac, "")))
            if k2 and k2 in _known_opns:
                return k2
        return k  # fallback: PED. CLIENTE mesmo sem match

    df["_PEDN"] = df.apply(_best_pedn, axis=1)

    # Quantidade de linhas por OP **na mesma semana** — evita contar a mesma OP
    # em semanas diferentes como se fossem "múltiplos produtos".
    n_linhas_op = (
        df.groupby(["_CHAVE", "SEMANA"])["_CHAVE"]
        .transform("count")
        .fillna(1)
        .astype(int)
        .tolist()
    )

    # Tokens que diferenciam produtos do mesmo OP (tamanho + n° de peças).
    # O SequenceMatcher falha aqui porque CASAL/QUEEN/SOLTEIRO são apenas 1
    # palavra em strings longas quase idênticas — a diferença de ratio é < 5%.
    # Estratégia: se ambos os textos têm token de tamanho → compara tokens
    # (deve coincidir). Se não → fallback para ratio de string inteira.
    # IMPORTANTE: normalize_text retorna UPPERCASE — os tokens devem ser UPPER.
    _TAMANHOS = {"CASAL", "QUEEN", "SOLTEIRO", "KING"}
    _RE_PECAS  = _re.compile(r'\b(\d+)\s*P(?:C[SC]S?|[SC]S?|E[CC]A|E[CC]AS?)?\b', _re.IGNORECASE)
    # Abreviações usadas na coluna CATEGORIA do lençol (ex: "JOGO SIPLES CS")
    _TAM_ALIAS = {"CS": "CASAL", "QE": "QUEEN", "ST": "SOLTEIRO", "KG": "KING"}

    def _tokens_prod(txt_norm: str) -> tuple[str, str]:
        """(tamanho, n_pecas) a partir do texto já normalizado (UPPERCASE, sem acentos)."""
        words = txt_norm.split()
        tam   = next((w for w in words if w in _TAMANHOS), "")
        if not tam:
            tam = next((_TAM_ALIAS[w] for w in words if w in _TAM_ALIAS), "")
        m     = _RE_PECAS.search(txt_norm)
        pecas = m.group(1) if m else ""
        return tam, pecas

    # ── Pré-calcula atribuições para OPs multi-produto ────────────────────────
    # Chave: (opn, semana) — OPs repetidas em semanas diferentes são tratadas
    # separadamente. Winner-takes-all dentro de cada (OP, semana).
    _op_to_positions: dict[tuple, list[int]] = {}
    for pos in range(len(df)):
        opn = df.iloc[pos]["_PEDN"]
        sem = df.iloc[pos]["SEMANA"]
        if opn:
            _op_to_positions.setdefault((opn, sem), []).append(pos)

    # _assignment: (opn, semana) → {pos: qtd_cortada}
    _assignment: dict[tuple, dict[int, int]] = {}
    for (opn, sem), positions in _op_to_positions.items():
        if len(positions) <= 1 or opn not in _prod_map:
            continue  # OP de 1 produto na semana → tratado depois (usa total)

        asgn = {pos: 0 for pos in positions}

        for mat_n, qtd in _prod_map[opn]:
            mat_tam, mat_pecas = _tokens_prod(mat_n)

            best_pos, best_score = None, -1.0
            for pos in positions:
                row = df.iloc[pos]
                desc = (
                    str(row.get("DESCRIÇÃO DO PRODUTO", "")).strip()
                    or str(row.get("PRODUTO", "")).strip()
                )
                alvo = normalize_text(desc)
                if not alvo:
                    continue

                prog_tam, prog_pecas = _tokens_prod(alvo)

                # Palavras-chave que bloqueiam o match quando presentes no corte
                # mas ausentes na programação. Exemplos:
                #   FUNDO  — sub-produto cortado junto com o jogo, não programado
                #   SIMPLES/SIPLES — jogo simples (lençol+fronhas) ≠ jogo de cama duplo
                #   LENCOL — "JOGO LENÇOL + FRONHAS" nunca aparece na programação como JOGO DE CAMA
                _SUB_PROD = {"FUNDO", "SIMPLES", "SIPLES", "LENCOL"}
                _mat_words = set(mat_n.split())
                _alvo_words = set(alvo.split())
                if (_mat_words & _SUB_PROD) and not (_alvo_words & _SUB_PROD):
                    score = 0.0
                elif mat_tam and prog_tam:
                    # Ambos têm token de tamanho → tamanho deve coincidir
                    if mat_tam != prog_tam:
                        score = 0.0  # tamanho errado → descartado
                    else:
                        # Tamanho bate: desempate por tokens de marca de linha.
                        # Ex: "COLOR ART" e "SUPERCAL" são coleções distintas —
                        # se corte tem COLOR e programação tem SUPERCAL → produto errado.
                        _MARCA = {"SUPERCAL", "COLOR"}
                        _mat_marca  = _mat_words  & _MARCA
                        _prog_marca = _alvo_words & _MARCA
                        if _mat_marca and _prog_marca:
                            if _mat_marca & _prog_marca:
                                score = 3.5   # marca coincide → ótimo
                            else:
                                score = 0.5   # marca diferente → quase descartado
                        else:
                            # Sem token de marca em um dos lados → similaridade geral
                            score = 2.0 + difflib.SequenceMatcher(None, alvo, mat_n).ratio()
                        if mat_pecas and prog_pecas and mat_pecas == prog_pecas:
                            score += 1.0  # n° de peças também bate
                else:
                    # Sem token de tamanho → similaridade geral como fallback
                    score = difflib.SequenceMatcher(None, alvo, mat_n).ratio()

                if score > best_score:
                    best_score, best_pos = score, pos

            # Atribui ao vencedor se score > 0 (tamanho bateu ou sim. > 0)
            if best_pos is not None and best_score > 0:
                asgn[best_pos] = asgn.get(best_pos, 0) + int(qtd)

        # Só usa atribuição por produto se ao menos 1 material foi casado.
        # Se todos deram score 0 (ex: TECIDO sem token de tamanho reconhecível,
        # ou PRODUTO vazio na programação), cai no fallback de total da OP.
        if any(v > 0 for v in asgn.values()):
            _assignment[(opn, sem)] = asgn

    # ── Preenche QNT_CORTADA e QNT_PROG_TOTAL por linha ──────────────────────
    qtd_cortada_list = []
    prog_indiv_list  = []   # None = manter QNT_PROG_TOTAL já calculado

    for pos in range(len(df)):
        row = df.iloc[pos]
        opn = row["_PEDN"]
        sem = row["SEMANA"]
        n_prod = int(n_linhas_op[pos])
        asgn_key = (opn, sem)

        if n_prod <= 1 or asgn_key not in _assignment:
            # OP de 1 produto na semana ou sem material no corte → total da OP
            qtd_cortada_list.append(int(_op_map.get(opn, 0)))
            prog_indiv_list.append(None)
        else:
            # OP multi-produto na semana: usa a atribuição calculada acima
            qtd_cortada_list.append(_assignment[asgn_key].get(pos, 0))
            prog_indiv_list.append(
                int(pd.to_numeric(row.get("QNT. PROG", 0), errors="coerce") or 0)
            )

    df["QNT_CORTADA"] = qtd_cortada_list

    # Salva total programado por OP antes de sobrescrever com valores individuais
    # (usado na aba Resumo para mostrar total da OP, não de 1 produto)
    df["QNT_PROG_OP"] = df["QNT_PROG_TOTAL"]

    # Aplica QNT_PROG_TOTAL individual para linhas multi-produto
    for pos, pval in enumerate(prog_indiv_list):
        if pval is not None:
            df.iloc[pos, df.columns.get_loc("QNT_PROG_TOTAL")] = pval

    # QNT_CORTADA_OP: total cortado por OP **por semana** para o Resumo.
    # OPs com per-product matching (_assignment) têm valores individuais por linha
    # (ex: CASAL=368, QUEEN=0, SOLTEIRO=110). A aba Resumo precisa da SOMA (478),
    # agrupando por semana para não somar cortes de semanas diferentes.
    df["QNT_CORTADA_OP"] = df["QNT_CORTADA"].copy()
    _assigned_ops = {opn for (opn, _sem) in _assignment.keys()}
    if _assigned_ops:
        _mask_asgn = df["_PEDN"].isin(_assigned_ops)
        if _mask_asgn.any():
            _grp_sum = (
                df.loc[_mask_asgn]
                .groupby(["_CHAVE", "SEMANA"])["QNT_CORTADA"]
                .transform("sum")
            )
            df.loc[_mask_asgn, "QNT_CORTADA_OP"] = _grp_sum

    # Mantém a chave de match resolvida (_PEDN → _OP_MATCH_KEY) em vez de
    # descartar — historico_op() precisa dela pra achar os registros de corte
    # certos de cada OP mesmo quando o match veio de PED. INT/OP INTERNA/OC
    # em vez do PED. CLIENTE (sem isso, boa parte das OPs "Concluído" ficava
    # sem DATA_CONCLUSAO calculável).
    df = df.rename(columns={"_PEDN": "_OP_MATCH_KEY"})

    df["STATUS_PROD"]  = df["QNT_CORTADA"].apply(
        lambda x: "Liberado" if x > 0 else "Não Iniciado"
    )
    df["STATUS_CORTE"] = df.apply(
        lambda r: _status_corte(r["QNT_CORTADA"], r["QNT_PROG_TOTAL"]), axis=1
    )
    df["STATUS_CORTE_OP"] = df.apply(
        lambda r: _status_corte(int(r["QNT_CORTADA_OP"]), int(r["QNT_PROG_OP"])), axis=1
    )
    df["DIFERENÇA"]    = df["QNT_CORTADA"] - df["QNT_PROG_TOTAL"]
    df["EFICIÊNCIA_%"] = (
        df["QNT_CORTADA"] / df["QNT_PROG_TOTAL"].replace(0, pd.NA) * 100
    ).fillna(0).round(1)
    return df


def agregar_por_op(df: pd.DataFrame) -> pd.DataFrame:
    def join_unique(s):
        vals = sorted({str(v) for v in s if str(v) not in ("", "nan", "NAN", "None")})
        return " / ".join(vals)

    chave = "_CHAVE" if "_CHAVE" in df.columns else "PED. CLIENTE"
    # QNT_CORTADA_OP e QNT_PROG_OP garantem o total correto por OP no Resumo,
    # mesmo quando o matching distribuiu cortes individualmente por produto.
    qtd_cort_col  = "QNT_CORTADA_OP"  if "QNT_CORTADA_OP"  in df.columns else "QNT_CORTADA"
    qtd_prog_col  = "QNT_PROG_OP"     if "QNT_PROG_OP"     in df.columns else "QNT_PROG_TOTAL"
    status_col    = "STATUS_CORTE_OP" if "STATUS_CORTE_OP" in df.columns else "STATUS_CORTE"
    _extra = {}
    if "_OP_MATCH_KEY" in df.columns:
        # Chave de match resolvida (PED. CLIENTE ou fallback PED. INT/OP
        # INTERNA/OC) — historico_op() usa pra achar os cortes certos da OP.
        _extra["_OP_MATCH_KEY"] = ("_OP_MATCH_KEY", "first")
    return df.groupby(chave, as_index=False).agg(
        **{"PED. CLIENTE": ("PED. CLIENTE", "first")},
        SEMANA        =("SEMANA",          "first"),
        CLIENTE       =("CLIENTE",         "first"),
        LOCAL         =("LOCAL",           "first"),
        PRODUTO       =("PRODUTO",         join_unique),
        QNT_PROG_TOTAL=(qtd_prog_col,      "first"),
        QNT_CORTADA   =(qtd_cort_col,      "first"),
        STATUS_PROD   =("STATUS_PROD",     "first"),
        STATUS_CORTE  =(status_col,        "first"),
        DIFERENÇA     =("DIFERENÇA",       "first"),
        EFICIÊNCIA_PRC=("EFICIÊNCIA_%",    "first"),
        **_extra,
    )


def calcular_data_conclusao(df_cortes_op: pd.DataFrame, qnt_prog_total: int):
    """Ordena os registros de corte de UMA OP por DATA, faz cumsum de
    QUANTIDADE e devolve a primeira data em que o acumulado atinge
    LIMIAR_CONCLUSAO (96%) do programado — mesmo limiar usado por
    _status_corte pra marcar "Concluído" (perda/refile normalmente impede
    bater 100% exato). None se a OP nunca atingiu o limiar (ou não tem
    nenhum registro com DATA válida)."""
    if qnt_prog_total <= 0 or df_cortes_op.empty:
        return None
    d = df_cortes_op.dropna(subset=["DATA"]).sort_values("DATA")
    if d.empty:
        return None
    acumulado = d["QUANTIDADE"].cumsum()
    atingiu = d.loc[acumulado >= qnt_prog_total * LIMIAR_CONCLUSAO, "DATA"]
    if atingiu.empty:
        return None
    return atingiu.iloc[0].date()


def _ops_fora_programacao(df_cortes: pd.DataFrame, chaves_programadas: set) -> pd.DataFrame:
    """OPs que aparecem no corte mas não em nenhuma linha da Programação
    (cortadas "fora da programação" — pedido do usuário 10/07/2026: 'ele
    considera os cortes que não foram programados?' — antes não considerava
    nenhum, ficavam invisíveis no Controle de OP).

    Quando o corte não traz o nome do produto (MATERIAL vazio), tenta
    completar via Carteira de Pedidos (_load_carteira_lookup) — nome e/ou
    quantidade de referência —, casando normalize_op(OP) == normalize_op(PEDIDO).
    Cruzamento best-effort (~2% de match, ver docstring de
    _load_carteira_lookup); quando não acha, fica sem quantidade de
    referência e o status vira "Fora da Programação" em vez de
    Concluído/Parcial/Pendente (não dá pra julgar % sem uma meta)."""
    from utils.normalize import normalize_op

    _cortes = df_cortes.copy()
    _cortes["_OPN"] = _cortes["OP"].map(normalize_op)
    _cortes = _cortes[_cortes["_OPN"].ne("") & ~_cortes["_OPN"].isin(chaves_programadas)]
    if _cortes.empty:
        return pd.DataFrame()

    carteira = _load_carteira_lookup()
    carteira_map = carteira.set_index("OP_NORM").to_dict("index") if not carteira.empty else {}

    linhas = []
    for opn, grp in _cortes.groupby("_OPN"):
        qtd_cortada = int(grp["QUANTIDADE"].sum())
        materiais = sorted({
            str(m).strip() for m in grp.get("MATERIAL", pd.Series(dtype=str))
            if str(m).strip()
        })
        produto = " / ".join(materiais)
        cliente = next((str(c).strip() for c in grp.get("CLIENTE", pd.Series(dtype=str)) if str(c).strip()), "")

        ref = carteira_map.get(opn)
        qnt_referencia = 0
        if ref:
            if not produto and ref.get("PRODUTO"):
                produto = ref["PRODUTO"]
            qnt_referencia = int(ref.get("QUANTIDADE") or 0)

        if qnt_referencia > 0:
            status = _status_corte(qtd_cortada, qnt_referencia)
            eficiencia = round(qtd_cortada / qnt_referencia * 100, 1)
            data_concl = calcular_data_conclusao(grp, qnt_referencia)
        else:
            status = "Fora da Programação"
            eficiencia = None
            data_concl = None

        linhas.append({
            "PED. CLIENTE": grp["OP"].iloc[0],
            "SEMANA": grp["SEMANA"].iloc[0] if "SEMANA" in grp.columns else "",
            "CLIENTE": cliente,
            "LOCAL": "",
            "PRODUTO": produto or "Sem Dados",
            "QNT_PROG_TOTAL": qnt_referencia,
            "QNT_CORTADA": qtd_cortada,
            "STATUS_PROD": "Liberado" if qtd_cortada > 0 else "Não Iniciado",
            "STATUS_CORTE": status,
            "DIFERENÇA": qtd_cortada - qnt_referencia,
            "EFICIÊNCIA_PRC": eficiencia,
            "_OP_MATCH_KEY": opn,
            "DATA_CONCLUSAO": data_concl,
            "FORA_PROGRAMACAO": True,
        })
    return pd.DataFrame(linhas)


def historico_op(df_prog: pd.DataFrame, df_cortes: pd.DataFrame) -> pd.DataFrame:
    """agregar_por_op(enriquecer(...)) + coluna DATA_CONCLUSAO — a data em
    que o acumulado cortado de cada OP atingiu o total programado, calculada
    a partir do histórico diário de corte (load_cortes traz DATA por
    registro). None quando a OP ainda não atingiu o programado.

    Também inclui as OPs cortadas fora da programação (ver
    _ops_fora_programacao) — marcadas com FORA_PROGRAMACAO=True, pra que
    "todas as OPs que estão sendo cortadas e que já foram cortadas" (pedido
    do usuário) apareçam, não só as que têm linha na planilha de
    Programação."""
    from utils.normalize import normalize_op

    df_agg = agregar_por_op(enriquecer(df_prog, df_cortes))
    df_agg["FORA_PROGRAMACAO"] = False

    if df_cortes.empty or "DATA" not in df_cortes.columns:
        df_agg["DATA_CONCLUSAO"] = None
        return df_agg

    _cortes = df_cortes.copy()
    _cortes["_OPN"] = _cortes["OP"].map(normalize_op)
    _cortes_por_op = {opn: grp for opn, grp in _cortes.groupby("_OPN")}

    datas_conclusao = []
    chaves_programadas = set()
    for _, row in df_agg.iterrows():
        # _OP_MATCH_KEY (quando disponível) é a chave já resolvida por
        # enriquecer() — inclui o fallback PED. INT/OP INTERNA/OC. Sem ela
        # (df_prog sem esse enriquecimento), cai no PED. CLIENTE direto.
        opn = str(row.get("_OP_MATCH_KEY") or normalize_op(str(row.get("PED. CLIENTE", ""))))
        chaves_programadas.add(opn)
        grp = _cortes_por_op.get(opn)
        if grp is None:
            datas_conclusao.append(None)
            continue
        datas_conclusao.append(
            calcular_data_conclusao(grp, int(row["QNT_PROG_TOTAL"]))
        )
    df_agg["DATA_CONCLUSAO"] = datas_conclusao

    df_fora = _ops_fora_programacao(df_cortes, chaves_programadas)
    if df_fora.empty:
        return df_agg
    return pd.concat([df_agg, df_fora], ignore_index=True)
