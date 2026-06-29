"""
Controle de Programação de Corte
Cruza a programação semanal com os dados reais de corte (Arealva Manta + Iacanga).
"""

import io
import logging
import os
import re
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.auth import init_session_state
from utils.navigation import safe_switch
from components.filtros_btn import render_filtros_btn

# constantes
PROG_ID     = "1FeTwrPEBOcC6RmD_5zh8NQLwOrYO87XA"
PROG_GID    = "708887209"
MANTA_ID    = "1KLbNpw-P28YgoijXfMXU-zRQULuDHMMB"
MANTA_GID   = "1544210185"
IACANGA_ID  = "1FBpCrq29_e1UBNwBlcgPTz66tbpUsgcgtzfXi4DcORU"
IACANGA_GID = "0"
LENCOL_ID   = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_GID  = "1396046910"
CACHE_TTL   = 300

_COR_STATUS = {"Concluído": "#22c55e", "Parcial": "#f59e0b", "Pendente": "#ef4444"}
_COR_PROD   = {"Liberado": "#22c55e", "Não Iniciado": "#6b7280"}
_EMOJI_STATUS = {"Concluído": "✅", "Parcial": "🟡", "Pendente": "🔴"}
_EMOJI_PROD   = {"Liberado": "🟢", "Não Iniciado": "⚫"}

# page config
st.set_page_config(
    page_title="Controle de Programação",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# css
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
footer{visibility:hidden;}#MainMenu{visibility:hidden;}
.stApp{
    background:
        radial-gradient(circle at 15% 15%,rgba(99,102,241,.07) 0%,transparent 42%),
        radial-gradient(circle at 85% 20%,rgba(79,70,229,.06) 0%,transparent 42%),
        linear-gradient(180deg,#0B0E14 0%,#0E1117 55%,#11151F 100%);
    color:#E0E0E0;font-family:'Space Grotesk',sans-serif;
}
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0C0F16 0%,#141925 100%)!important;
    border-right:1px solid rgba(255,255,255,.10);
}
section[data-testid="stSidebar"] *{color:#E0E0E0!important;font-family:'Space Grotesk',sans-serif;}
.page-badge{
    display:inline-block;padding:6px 18px;border-radius:999px;
    font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;
    color:#818CF8;background:rgba(129,140,248,.10);
    border:1px solid rgba(129,140,248,.30);font-weight:600;margin-bottom:20px;
}
.page-title{
    font-family:'Sora',sans-serif;font-size:2.4rem;font-weight:800;
    line-height:1.05;margin:0 0 14px 0;color:#FFF;letter-spacing:-.5px;
}
.page-title .accent{
    background:linear-gradient(90deg,#818CF8,#A5B4FC 45%,#6366F1 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.page-subtitle{font-size:1rem;color:#A0A0A0;max-width:580px;margin:0 auto 10px auto;text-align:center;}
.page-divider{
    height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.10),transparent);
    margin:28px 0 36px 0;
}
.breadcrumb{font-size:.85rem;color:#606878;margin-bottom:12px;padding:0 2px;}
.breadcrumb .bc-sep{margin:0 6px;color:rgba(255,255,255,.18);}
.breadcrumb .bc-active{color:#818CF8;font-weight:600;}
.breadcrumb .bc-link{color:#7A8899;}
.kpi-wrap{
    background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
    border-radius:14px;padding:18px 14px;text-align:center;
}
.kpi-label{font-size:.70rem;color:#9CA3AF;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;}
.kpi-value{font-family:'Sora',sans-serif;font-size:2rem;font-weight:800;color:#FFF;line-height:1;}
.kpi-sub{font-size:.75rem;color:#6B7280;margin-top:4px;}
.stButton>button{
    background:linear-gradient(135deg,#6366F1,#4F46E5)!important;
    color:#FFF!important;font-weight:700!important;border-radius:12px!important;
    padding:10px 14px!important;border:1px solid rgba(99,102,241,.55)!important;
    box-shadow:0 6px 18px rgba(99,102,241,.22)!important;
    transition:transform .2s ease!important;width:100%!important;
}
.stButton>button:hover{transform:translateY(-2px);}
section[data-testid="stSidebar"] .stButton>button{
    background:linear-gradient(135deg,rgba(99,102,241,.16),rgba(99,102,241,.07))!important;
    color:#818CF8!important;border:1px solid rgba(99,102,241,.35)!important;box-shadow:none!important;
}
section[data-testid="stSidebar"] .stButton>button p,
section[data-testid="stSidebar"] .stButton>button span{color:inherit!important;font-weight:600!important;}
div[data-testid="stMetric"]{
    background-color:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.15);
    border-radius:10px;padding:12px 16px;
}
</style>
""", unsafe_allow_html=True)

# auth
init_session_state()
if not st.session_state.get("auth_nivel"):
    st.warning("🔒 Acesso restrito. Faça login na página inicial.")
    if st.button("← Voltar ao Início"):
        safe_switch("app.py")
    st.stop()

# sidebar nav
with st.sidebar:
    st.markdown("### 📊 Controle de Programação")
    st.markdown("---")
    if st.button("🏢 Início", key="sb_home", use_container_width=True):
        safe_switch("app.py")
    st.markdown("---")
    st.header("🔍 Filtros")

# data loading
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
        s = serie.astype(str).str.strip()
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
        import logging
        logging.warning("db_manager: falha ao salvar programacao_corte", exc_info=True)

    return df

# (parser de data local removido — usar utils.date_parser.parse_date_series,
#  que detecta o formato D/M vs M/D por coluna.)

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_cortes() -> pd.DataFrame:
    """
    Carrega dados de corte de três fontes:
      - Arealva/Manta  (QUANTIDADE, header simples)
      - Iacanga        (QUANTIDADE, header simples)
      - Lençol Arealva (QUANT, pode ter linha de título → header detection)

    Retorna colunas [OP, QUANTIDADE, FONTE, SEMANA].
    SEMANA é o nº ISO da semana derivado da coluna DATA — essencial para que
    o join não some cortes de semanas anteriores para OPs reutilizadas (ex: PROG 81).
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
        return pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE", "SEMANA"])

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
    invalidos = {"", "NAN", "NONE", "N/A", "SEM OP"}
    out = out[~out["OP"].str.upper().isin(invalidos)]
    return out

# lógica de cruzamento
def _status_corte(cortada: int, prog_total: int) -> str:
    if cortada <= 0:
        return "Pendente"
    eficiencia = cortada / prog_total if prog_total > 0 else 0
    if eficiencia >= 0.96:
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

    df = df.drop(columns=["_PEDN"])

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
    )

# carregamento
_erro_prog   = None
_erro_cortes = None

with st.spinner("Carregando dados da programação..."):
    try:
        df_prog_raw = load_programacao()
    except Exception as e:
        _erro_prog = str(e)
        df_prog_raw = pd.DataFrame()

with st.spinner("Carregando dados de corte..."):
    try:
        df_cortes_raw = load_cortes()
    except Exception as e:
        _erro_cortes = str(e)
        df_cortes_raw = pd.DataFrame(columns=["OP", "QUANTIDADE", "FONTE"])

if _erro_prog:
    st.error(f"❌ Erro ao carregar programação: {_erro_prog}")
    st.info("Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link pode visualizar'.")
    st.stop()

if df_prog_raw.empty:
    st.error("❌ A planilha de programação foi carregada mas não retornou dados válidos.")
    st.info("Verifique se a planilha contém dados e se a coluna 'PED. CLIENTE' existe.")
    st.stop()

df_enriched = enriquecer(df_prog_raw, df_cortes_raw)

# sidebar — filtros
with st.sidebar:
    semanas_disp = sorted(df_enriched["SEMANA"].dropna().unique())
    semanas_sel  = st.multiselect("📅 Semana", options=semanas_disp, default=[], key="prog_semana")

    clientes_disp = sorted(df_enriched["CLIENTE"].dropna().unique())
    clientes_sel  = st.multiselect("👤 Cliente", options=clientes_disp, default=[], key="prog_cliente")

    locais_disp = sorted(df_enriched["LOCAL"].dropna().unique())
    locais_sel  = st.multiselect("🏭 Local", options=locais_disp, default=[], key="prog_local")

    status_disp = ["Pendente", "Parcial", "Concluído"]
    status_sel  = st.multiselect("🔄 Status de Corte", options=status_disp, default=[], key="prog_status")

    st.markdown("---")
    if st.button("🔄 Atualizar Dados", key="prog_clear", use_container_width=True):
        from utils.cache_manager import invalidate_all
        invalidate_all()
        st.cache_data.clear()
        st.rerun()
    st.caption("🔖 cód. v20260611-6")
    st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.caption(f"📋 Prog.: {len(df_prog_raw):,} linhas".replace(",", "."))
    total_cortes = len(df_cortes_raw)
    st.caption(f"✂️ Cortes total: {total_cortes:,} registros".replace(",", "."))
    if not df_cortes_raw.empty and "FONTE" in df_cortes_raw.columns:
        for fonte_nome, grupo in df_cortes_raw.groupby("FONTE"):
            st.caption(f"  · {fonte_nome}: {len(grupo):,}".replace(",", "."))
    if total_cortes == 0:
        st.warning("⚠️ Nenhum dado de corte carregado — verifique acesso às planilhas.")
    if _erro_cortes:
        st.warning(f"⚠️ Cortes: {_erro_cortes[:60]}")

    st.markdown("---")
    st.markdown("**🔍 Rastrear OP**")
    op_busca = st.text_input("OP / PED. CLIENTE", key="op_rastreio", placeholder="ex: 254333")
    if op_busca.strip():
        from utils.normalize import normalize_op as _nop
        _alvo = _nop(op_busca)
        resultado = df_cortes_raw[df_cortes_raw["OP"].map(_nop) == _alvo]
        if resultado.empty:
            st.info("Nenhum corte encontrado para essa OP.")
        else:
            st.success(f"**{resultado['QUANTIDADE'].apply(pd.to_numeric, errors='coerce').fillna(0).sum():,.0f}** peças cortadas".replace(",", "."))
            _cols_rastreio = [c for c in ["FONTE", "OP", "MATERIAL", "CLIENTE", "QUANTIDADE"] if c in resultado.columns]
            st.dataframe(resultado[_cols_rastreio], use_container_width=True, hide_index=True)

# aplicar filtros
df_filtered = df_enriched.copy()
if semanas_sel:
    df_filtered = df_filtered[df_filtered["SEMANA"].isin(semanas_sel)]
if clientes_sel:
    df_filtered = df_filtered[df_filtered["CLIENTE"].isin(clientes_sel)]
if locais_sel:
    df_filtered = df_filtered[df_filtered["LOCAL"].isin(locais_sel)]
if status_sel:
    df_filtered = df_filtered[df_filtered["STATUS_CORTE"].isin(status_sel)]

render_filtros_btn()

# header
st.markdown("""
<div class="breadcrumb">
  <span class="bc-link">Controladoria</span>
  <span class="bc-sep">›</span>
  <span class="bc-active">Controle de Programação</span>
</div>
<div style="text-align:center;padding:24px 12px 8px 12px;">
  <div class="page-badge">📊 Controladoria · Planejado vs Realizado</div>
  <h1 class="page-title">Programação de <span class="accent">Corte</span></h1>
  <p class="page-subtitle">Acompanhamento semanal cruzando o programado com o realizado nos dashboards de corte</p>
</div>
<div class="page-divider"></div>
""", unsafe_allow_html=True)

# kpis
df_agg = agregar_por_op(df_filtered)

total_ops      = len(df_agg)
concluidas     = (df_agg["STATUS_CORTE"] == "Concluído").sum()
parciais       = (df_agg["STATUS_CORTE"] == "Parcial").sum()
pendentes      = (df_agg["STATUS_CORTE"] == "Pendente").sum()
aderencia_pct  = round(concluidas / total_ops * 100, 1) if total_ops else 0
total_prog_pcs = int(df_agg["QNT_PROG_TOTAL"].sum())
total_cort_pcs = int(df_agg["QNT_CORTADA"].sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)

def _kpi(col, label, value, sub="", color="#FFFFFF"):
    with col:
        st.markdown(
            f'<div class="kpi-wrap">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

_kpi(k1, "Total de OPs",     total_ops,      "ordens na programação")
_kpi(k2, "Concluídas",       concluidas,     f"{aderencia_pct}% aderência",  "#22c55e")
_kpi(k3, "Parciais",         parciais,       "em andamento",                 "#f59e0b")
_kpi(k4, "Pendentes",        pendentes,      "não iniciadas",                "#ef4444")
_kpi(k5, "Peças Prog.",      f"{total_prog_pcs:,}".replace(",", "."), "total programado")
_kpi(k6, "Peças Cortadas",   f"{total_cort_pcs:,}".replace(",", "."), "total realizado",
     "#22c55e" if total_cort_pcs >= total_prog_pcs else "#f59e0b")

st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

# diagnóstico de fontes
with st.expander("🔍 Diagnóstico — Verificação de Fontes de Corte", expanded=False):
    st.markdown("##### Status de carregamento por planilha")

    _FONTES_ESPERADAS = ["Zanattex", "Giattex", "Lençol"]
    diag_rows = []

    for fn in _FONTES_ESPERADAS:
        if not df_cortes_raw.empty and "FONTE" in df_cortes_raw.columns:
            g = df_cortes_raw[df_cortes_raw["FONTE"] == fn]
            n_reg = len(g)
        else:
            g = pd.DataFrame()
            n_reg = 0

        if n_reg > 0:
            n_ops   = int(g["OP"].nunique())
            qtd     = int(g["QUANTIDADE"].sum())
            status  = "✅ Carregado"
            top_ops = (
                g.groupby("OP")["QUANTIDADE"].sum()
                .nlargest(5)
                .index.tolist()
            )
            amostra = " · ".join(str(o) for o in top_ops)
            # Faixa de semanas carregadas
            if "SEMANA" in g.columns and g["SEMANA"].notna().any():
                sem_min = int(g["SEMANA"].dropna().min())
                sem_max = int(g["SEMANA"].dropna().max())
                semanas_str = f"sem. {sem_min}–{sem_max}"
            else:
                semanas_str = "sem data"
        else:
            n_ops, qtd, status, amostra, semanas_str = 0, 0, "❌ Sem dados", "—", "—"

        diag_rows.append({
            "Fonte": fn,
            "Status": status,
            "Registros": f"{n_reg:,}".replace(",", "."),
            "OPs únicas": f"{n_ops:,}".replace(",", "."),
            "Peças totais": f"{qtd:,}".replace(",", "."),
            "Semanas cobertas": semanas_str,
            "Top OPs (por qtd.)": amostra,
        })

    st.dataframe(pd.DataFrame(diag_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### Cruzamento: Programação × Cortes")

    from utils.normalize import normalize_op as _nop
    _ops_corte = (
        {o for o in df_cortes_raw["OP"].map(_nop).unique() if o}
        if not df_cortes_raw.empty else set()
    )
    # OP da programação = PED. CLIENTE (normalizada, prefixo-insensível)
    _peds_prog = {o for o in df_prog_raw["PED. CLIENTE"].map(_nop).unique() if o}

    _matched_ped = _peds_prog & _ops_corte
    _nao_matched = _peds_prog - _ops_corte

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("OPs na programação", len(_peds_prog))
    mc2.metric("Com corte encontrado", len(_matched_ped),
               help="OP (PED. CLIENTE) encontrada nos dados de corte, ignorando prefixo")
    mc3.metric("Sem corte encontrado", len(_nao_matched),
               help="Nenhum corte com essa OP nas planilhas de corte")

    if _nao_matched:
        st.markdown(
            f"**⚠️ {len(_nao_matched)} pedido(s) da programação sem corte registrado "
            f"em nenhuma das planilhas:**"
        )
        # Exibe em grid de 5 colunas
        _nm_sorted = sorted(_nao_matched)
        _cols_nm = st.columns(5)
        for i, nm in enumerate(_nm_sorted[:50]):   # limita a 50 para não poluir
            _cols_nm[i % 5].markdown(f"`{nm}`")
        if len(_nao_matched) > 50:
            st.caption(f"… e mais {len(_nao_matched) - 50} pedidos.")
    else:
        st.success("✅ Todos os pedidos da programação têm corte registrado em alguma fonte.")

    # Verificação inversa: OPs cortadas sem pedido na programação
    _corte_sem_prog = _ops_corte - _peds_prog
    if _corte_sem_prog:
        with st.container():
            st.markdown(
                f"**ℹ️ {len(_corte_sem_prog)} OP(s) cortada(s) sem pedido correspondente "
                f"na programação:**"
            )
            _cs_sorted = sorted(_corte_sem_prog)
            _cols_cs = st.columns(5)
            for i, op in enumerate(_cs_sorted[:30]):
                _cols_cs[i % 5].markdown(f"`{op}`")
            if len(_corte_sem_prog) > 30:
                st.caption(f"… e mais {len(_corte_sem_prog) - 30} OPs.")

    # ── Debug: diagnóstico do loader de lençol ─────────────────────────────────
    st.markdown("---")
    st.markdown("##### Debug: loader de lençol (raw)")
    try:
        from utils.cache_manager import get_raw as _get_raw
        _lenc_csv = _get_raw("1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa", "1396046910", ttl=1)
        if not _lenc_csv or not _lenc_csv.strip():
            st.error("get_raw() retornou vazio — sem acesso à planilha lençol")
        else:
            st.success(f"CSV lençol recebido: {len(_lenc_csv):,} bytes".replace(",", "."))
            _lines = _lenc_csv.splitlines()
            st.caption(f"Total de linhas CSV: {len(_lines)}")
            st.markdown("**Primeiras 6 linhas do CSV:**")
            st.code("\n".join(_lines[:6]))
    except Exception as _e:
        st.error(f"Erro ao buscar lençol raw: {_e}")

    st.markdown("##### Debug: load_lencol_smart_xlsx() resultado")
    try:
        import logging as _logging
        from utils.lencol_loader_smart import load_lencol_smart_xlsx as _load_len
        _df_len_dbg = _load_len()
        if _df_len_dbg.empty:
            st.error("load_lencol_smart_xlsx() retornou DataFrame vazio")
        else:
            st.success(f"{len(_df_len_dbg)} linhas carregadas. Colunas: {list(_df_len_dbg.columns)}")
            st.dataframe(_df_len_dbg.head(5), use_container_width=True, hide_index=True)
    except Exception as _e:
        st.error(f"Exceção em load_lencol_smart_xlsx: {_e}")

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# gráficos
_DARK = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
)

col_donut, col_bar = st.columns([1, 2], gap="large")

with col_donut:
    st.markdown("#### Status das Ordens")
    labels = ["Concluído", "Parcial", "Pendente"]
    values = [concluidas, parciais, pendentes]
    colors = ["#22c55e", "#f59e0b", "#ef4444"]
    fig_donut = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.60,
        marker=dict(colors=colors, line=dict(color="#0B0E14", width=2)),
        textinfo="percent+value",
        textfont=dict(size=13),
        showlegend=True,
    ))
    fig_donut.update_layout(
        **_DARK,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        annotations=[dict(
            text=f"<b>{total_ops}</b><br>OPs",
            x=0.5, y=0.5, font_size=16, showarrow=False, font_color="#FFFFFF",
        )],
        height=300,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_bar:
    st.markdown("#### Programado vs Cortado por Semana")
    if not df_agg.empty:
        df_sem = df_agg.groupby("SEMANA", as_index=False).agg(
            QNT_PROG_TOTAL=("QNT_PROG_TOTAL", "sum"),
            QNT_CORTADA   =("QNT_CORTADA",    "sum"),
        ).sort_values("SEMANA")

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Programado", x=df_sem["SEMANA"], y=df_sem["QNT_PROG_TOTAL"],
            marker_color="rgba(129,140,248,0.55)", marker_line_color="#818CF8", marker_line_width=1,
        ))
        fig_bar.add_trace(go.Bar(
            name="Cortado", x=df_sem["SEMANA"], y=df_sem["QNT_CORTADA"],
            marker_color="rgba(34,197,94,0.65)", marker_line_color="#22c55e", marker_line_width=1,
        ))
        fig_bar.update_layout(
            **_DARK,
            barmode="group",
            xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0"),
            yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748", color="#A0AEC0",
                       title="Peças"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=300,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para o período selecionado.")

st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

# ── Previsto × Cortado por OP (das programadas) ───────────────────────────────
# Para OPs que ESTAVAM na programação e tiveram corte: compara o previsto
# (losango) com o que foi efetivamente cortado (barra). Respeita os filtros.
st.markdown('<div class="page-divider"></div>', unsafe_allow_html=True)
st.markdown("### 📊 Previsto × Cortado por OP (programadas)")
st.caption(
    "OPs da programação que tiveram corte. A barra mostra o que foi cortado; "
    "o losango marca o previsto — assim dá para ver se a OP atingiu, passou ou "
    "ficou abaixo do planejado."
)

_prog_cmp = df_agg[
    (df_agg["PED. CLIENTE"].astype(str).str.strip() != "")
    & (df_agg["QNT_CORTADA"] > 0)
].copy()

if _prog_cmp.empty:
    st.info("Nenhuma OP programada com corte no filtro atual.")
else:
    _pc = _prog_cmp.sort_values("QNT_CORTADA", ascending=False).head(15)
    _pc = _pc.sort_values("QNT_CORTADA", ascending=True)
    _ops_lbl = _pc["PED. CLIENTE"].astype(str).tolist()

    fig_pc = go.Figure()
    fig_pc.add_trace(go.Bar(
        x=_pc["QNT_CORTADA"].tolist(), y=_ops_lbl, orientation="h",
        name="Cortado", marker_color="#22c55e",
        text=[f"{int(v):,}".replace(",", ".") for v in _pc["QNT_CORTADA"]],
        textposition="outside",
    ))
    fig_pc.add_trace(go.Scatter(
        x=_pc["QNT_PROG_TOTAL"].tolist(), y=_ops_lbl, mode="markers",
        name="Previsto",
        marker=dict(symbol="diamond", size=13, color="#818CF8",
                    line=dict(color="#FFFFFF", width=1)),
    ))
    fig_pc.update_layout(
        height=max(300, len(_pc) * 36),
        margin=dict(l=0, r=80, t=10, b=0),
        barmode="overlay",
        xaxis_title="Peças", yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD5E0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor="#2D3748"),
        yaxis=dict(gridcolor="#2D3748", type="category",
                   categoryorder="array", categoryarray=_ops_lbl),
    )
    st.plotly_chart(fig_pc, use_container_width=True)

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# tabelas
tab_resumo, tab_detalhe = st.tabs(["📊 Resumo por Ordem (OP)", "📋 Detalhe Completo"])

# tab 1: resumo por op
with tab_resumo:
    if df_agg.empty:
        st.info("Nenhuma ordem encontrada com os filtros aplicados.")
    else:
        df_show = df_agg.copy()
        df_show["STATUS PRODUÇÃO"] = df_show["STATUS_PROD"].apply(
            lambda s: f"{_EMOJI_PROD.get(s, '')} {s}"
        )
        df_show["STATUS CORTE"] = df_show["STATUS_CORTE"].apply(
            lambda s: f"{_EMOJI_STATUS.get(s, '')} {s}"
        )
        df_show["EFICIÊNCIA"] = df_show["EFICIÊNCIA_PRC"].apply(lambda x: f"{x:.1f}%")
        df_show["DIFERENÇA"]  = df_show["DIFERENÇA"].apply(
            lambda x: f"+{int(x):,}".replace(",", ".") if x >= 0 else f"{int(x):,}".replace(",", ".")
        )
        df_show["QNT PROG"]    = df_show["QNT_PROG_TOTAL"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_show["QNT CORTADA"] = df_show["QNT_CORTADA"].apply(lambda x: f"{int(x):,}".replace(",", "."))

        colunas_exibir = [
            "SEMANA", "PED. CLIENTE", "CLIENTE", "LOCAL", "PRODUTO",
            "QNT PROG", "QNT CORTADA", "DIFERENÇA", "EFICIÊNCIA",
            "STATUS PRODUÇÃO", "STATUS CORTE",
        ]
        st.dataframe(
            df_show[colunas_exibir],
            use_container_width=True,
            hide_index=True,
            height=min(50 + len(df_show) * 35, 600),
        )
        st.caption(f"Total: {len(df_show)} ordens | {total_prog_pcs:,} peças programadas | {total_cort_pcs:,} cortadas".replace(",", "."))

# tab 2: detalhe completo
with tab_detalhe:
    if df_filtered.empty:
        st.info("Nenhum registro encontrado com os filtros aplicados.")
    else:
        df_det = df_filtered.copy()

        # Colunas originais da planilha + calculadas (substituindo as manuais)
        df_det["STATUS PRODUÇÃO"] = df_det["STATUS_PROD"].apply(
            lambda s: f"{_EMOJI_PROD.get(s, '')} {s}"
        )
        df_det["STATUS CORTE"] = df_det["STATUS_CORTE"].apply(
            lambda s: f"{_EMOJI_STATUS.get(s, '')} {s}"
        )
        df_det["QNT CORTADA"]  = df_det["QNT_CORTADA"].apply(lambda x: f"{int(x):,}".replace(",", "."))
        df_det["EFICIÊNCIA %"] = df_det["EFICIÊNCIA_%"].apply(lambda x: f"{x:.1f}%")
        df_det["DIFERENÇA"]    = df_det["DIFERENÇA"].apply(
            lambda x: f"+{int(x):,}".replace(",", ".") if x >= 0 else f"{int(x):,}".replace(",", ".")
        )

        colunas_det = [
            "SEMANA", "CLIENTE", "LOCAL", "PRODUTO", "PED. CLIENTE",
            "PED. INT", "OP INTERNA", "OC", "DESCRIÇÃO DO PRODUTO",
            "QNT. PROG", "DATA INICIO", "DATA FINALIZADO", "PREV. INDUSTRIALIZAÇÃO",
            "QNT CORTADA", "STATUS PRODUÇÃO", "STATUS CORTE", "EFICIÊNCIA %", "DIFERENÇA",
        ]
        colunas_det = [c for c in colunas_det if c in df_det.columns]

        st.dataframe(
            df_det[colunas_det],
            use_container_width=True,
            hide_index=True,
            height=min(50 + len(df_det) * 35, 700),
        )
        st.caption(f"Total: {len(df_det)} linhas")

# ── Cortes fora da programação ────────────────────────────────────────────────
# OPs que foram cortadas mas NÃO constam na programação (produção fora do plano).
st.markdown('<div class="page-divider"></div>', unsafe_allow_html=True)
st.markdown("### ✂️ Cortes Fora da Programação")
_filtros_aplic = []
if semanas_sel:
    _filtros_aplic.append(", ".join(str(s) for s in sorted(semanas_sel)))
if clientes_sel:
    _filtros_aplic.append("empresa(s): " + ", ".join(sorted(clientes_sel)))
if locais_sel:
    _filtros_aplic.append("local: " + ", ".join(sorted(locais_sel)))
st.caption(
    "OPs que apareceram nas planilhas de corte mas não estão na programação — "
    "ou seja, foi cortado sem ter sido programado."
    + (f" Filtrando por {' · '.join(_filtros_aplic)}." if _filtros_aplic
       else " Considerando todas as semanas e empresas.")
)

from utils.normalize import normalize_op as _nop_fora, normalize_text as _ntxt_fora

if df_cortes_raw.empty:
    st.info("Sem dados de corte carregados.")
else:
    _cortes = df_cortes_raw.copy()
    _cortes["_OPN"] = _cortes["OP"].map(_nop_fora)
    # Respeita o filtro de semana da sidebar: vazio → todas as semanas; com semanas
    # selecionadas → apenas os cortes daquelas semanas.
    # OBS: a SEMANA da programação é texto ("SEMANA 22") e a dos cortes é Int64 (22).
    # Extraímos o número de dentro do texto e normalizamos para o filtro casar
    # ("SEMANA 22"→"22", "SEMANA 01"→"1", 22→"22").
    def _wk_canon(x):
        s = str(x).strip()
        m = re.search(r"\d+", s)
        return str(int(m.group())) if m else s
    if semanas_sel and "SEMANA" in _cortes.columns:
        _sem_alvo = {_wk_canon(s) for s in semanas_sel}
        _cortes = _cortes[_cortes["SEMANA"].map(_wk_canon).isin(_sem_alvo)]
    # Respeita o filtro de Cliente/Empresa: compara por nome normalizado
    # (maiúsculas/acentos) para casar "Burdays" (Giattex) com "BURDAYS" (Lençol).
    if clientes_sel and "CLIENTE" in _cortes.columns:
        _cli_alvo = {_ntxt_fora(c) for c in clientes_sel}
        _cortes = _cortes[_cortes["CLIENTE"].map(_ntxt_fora).isin(_cli_alvo)]
    # Respeita o filtro de Local: mapeia o LOCAL da programação (ex: "GIATTEX",
    # "CORTE LENÇOL", "ZANATTEX") para a FONTE do corte por palavra-chave.
    if locais_sel and "FONTE" in _cortes.columns:
        _LOCAL_FONTE_KW = {
            "Giattex":  ["GIATTEX", "GGTEX", "GIATTA", "IACANGA"],
            "Zanattex": ["ZANATTEX", "AREALVA", "ZANATTA"],
            "Lençol":   ["LENCOL"],
        }
        _locais_norm = [_ntxt_fora(l) for l in locais_sel]
        def _fonte_no_local(fonte):
            kws = _LOCAL_FONTE_KW.get(fonte, [])
            return any(any(kw in ln for kw in kws) for ln in _locais_norm)
        _cortes = _cortes[_cortes["FONTE"].map(_fonte_no_local)]
    _sem_op_pcs = int(_cortes.loc[_cortes["_OPN"] == "", "QUANTIDADE"].sum())
    _cortes = _cortes[_cortes["_OPN"] != ""]

    # Coleta OPs reconhecidas de TODAS as colunas de referência da programação:
    # PED. CLIENTE (ex: 700761-3722-27), PED. INT (ex: 83), OP INTERNA, OC.
    # Assim "PROG 83" → "83" bate com PED. INT=83 e não aparece como "fora".
    _cols_ref = ["PED. CLIENTE", "PED. INT", "OP INTERNA", "OC"]
    _peds_prog_fora: set[str] = set()
    for _c in _cols_ref:
        if _c in df_prog_raw.columns:
            _peds_prog_fora.update(
                o for o in df_prog_raw[_c].map(_nop_fora).unique() if o
            )
    _fora = _cortes[~_cortes["_OPN"].isin(_peds_prog_fora)]

    _total_cort_all = int(_cortes["QUANTIDADE"].sum())
    _total_fora_pcs = int(_fora["QUANTIDADE"].sum())
    _n_ops_fora = int(_fora["_OPN"].nunique())
    _pct_fora = (100 * _total_fora_pcs / _total_cort_all) if _total_cort_all else 0

    kf1, kf2, kf3 = st.columns(3)
    _kpi(kf1, "OPs fora da programação", f"{_n_ops_fora:,}".replace(",", "."),
         "cortadas sem programar", "#f59e0b" if _n_ops_fora else "#22c55e")
    _kpi(kf2, "Peças cortadas fora", f"{_total_fora_pcs:,}".replace(",", "."),
         "total realizado fora do plano", "#f59e0b" if _total_fora_pcs else "#22c55e")
    _kpi(kf3, "% do corte total", f"{_pct_fora:.1f}%".replace(".", ","),
         "do que foi cortado", "#f59e0b" if _pct_fora else "#22c55e")

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if _fora.empty:
        st.success("✅ Tudo o que foi cortado estava na programação.")
    else:
        def _join_unicos(serie):
            vals = sorted({
                str(v).strip() for v in serie
                if str(v).strip() not in ("", "nan", "NaN", "<NA>", "None", "NaT")
            })
            return " / ".join(vals)

        _agg_kwargs = {"QNT CORTADA": ("QUANTIDADE", "sum"), "Fonte": ("FONTE", _join_unicos)}
        if "DATA" in _fora.columns:
            _agg_kwargs["Data(s)"] = (
                "DATA",
                lambda s: " / ".join(
                    sorted({d.strftime("%d/%m/%Y") for d in s.dropna()})
                ),
            )
        if "MATERIAL" in _fora.columns:
            _agg_kwargs["Material"] = ("MATERIAL", _join_unicos)
        if "CLIENTE" in _fora.columns:
            _agg_kwargs["Cliente"] = ("CLIENTE", _join_unicos)
        _tab = (
            _fora.groupby("_OPN")
            .agg(**_agg_kwargs)
            .reset_index()
            .rename(columns={"_OPN": "OP"})
        )
        if "SEMANA" in _fora.columns:
            _sem = _fora.groupby("_OPN")["SEMANA"].apply(
                lambda s: _join_unicos(
                    s.dropna().astype("Int64").astype(str)
                )
            )
            _tab["Semana(s)"] = _tab["OP"].map(_sem)

        _tab = _tab.sort_values("QNT CORTADA", ascending=False).reset_index(drop=True)
        # Reordena: OP, QNT CORTADA, Data(s), restante
        _col_order = ["OP", "QNT CORTADA"]
        if "Data(s)" in _tab.columns:
            _col_order.append("Data(s)")
        _col_order += [c for c in _tab.columns if c not in _col_order]
        _tab = _tab[_col_order]

        _tab_fmt = _tab.copy()
        _tab_fmt["QNT CORTADA"] = _tab_fmt["QNT CORTADA"].map(lambda x: f"{int(x):,}".replace(",", "."))

        st.dataframe(_tab_fmt, use_container_width=True, hide_index=True)

        # Gráfico — top 15 OPs cortadas fora do plano
        _top = _tab.head(15).sort_values("QNT CORTADA", ascending=True)
        # OP é rótulo (categoria), não número — senão o eixo trata "1895301001"
        # como 1,8 bilhão e o gráfico fica achatado.
        _y_labels = _top["OP"].astype(str).tolist()
        fig_fora = go.Figure(go.Bar(
            x=_top["QNT CORTADA"].tolist(), y=_y_labels, orientation="h",
            marker_color="#f59e0b",
            text=[f"{int(v):,}".replace(",", ".") for v in _top["QNT CORTADA"]],
            textposition="outside",
        ))
        fig_fora.update_layout(
            height=max(280, len(_top) * 34),
            margin=dict(l=0, r=70, t=10, b=0),
            xaxis_title="Peças cortadas", yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E0"),
            xaxis=dict(gridcolor="#2D3748"),
            yaxis=dict(gridcolor="#2D3748", type="category",
                       categoryorder="array", categoryarray=_y_labels),
        )
        st.plotly_chart(fig_fora, use_container_width=True)

    if _sem_op_pcs > 0:
        st.caption(
            f"ℹ️ Além disso, {_sem_op_pcs:,}".replace(",", ".")
            + " peça(s) foram cortadas sem número de OP (não classificáveis)."
        )

# ── Botão Relatório PDF ───────────────────────────────────────────────────────
st.markdown("---")

def _html_ctrl_prog() -> bytes:
    from datetime import datetime as _dt
    agora = _dt.now().strftime("%d/%m/%Y %H:%M")

    def _n(v) -> str:
        return f"{int(v):,}".replace(",", ".")

    filtros_str = []
    if semanas_sel:
        filtros_str.append("Semanas: " + ", ".join(str(s) for s in sorted(semanas_sel)))
    if clientes_sel:
        filtros_str.append("Empresas: " + ", ".join(sorted(clientes_sel)))
    if locais_sel:
        filtros_str.append("Locais: " + ", ".join(sorted(locais_sel)))
    filtros_label = " &nbsp;|&nbsp; ".join(filtros_str) if filtros_str else "Todos os filtros"

    def _op_rows() -> str:
        if df_agg.empty:
            return "<tr><td colspan='9' style='text-align:center'>Sem dados</td></tr>"
        linhas = []
        for _, r in df_agg.iterrows():
            status_c = str(r.get("STATUS_CORTE", ""))
            cls = "sok" if status_c == "Concluído" else ("samb" if status_c == "Parcial" else "serr")
            ef = float(r.get("EFICIÊNCIA_PRC", 0))
            ef_cls = "sok" if ef >= 96 else ("samb" if ef >= 50 else "serr")
            dif = int(r.get("DIFERENÇA", 0))
            dif_s = f"{'+' if dif > 0 else ''}{_n(dif)}"
            op_val = str(r.get("PED. CLIENTE", "")).strip() or "—"
            linhas.append(
                f"<tr>"
                f"<td>{r.get('SEMANA','')}</td>"
                f"<td>{op_val}</td>"
                f"<td>{r.get('CLIENTE','')}</td>"
                f"<td>{r.get('LOCAL','')}</td>"
                f"<td>{r.get('PRODUTO','')}</td>"
                f"<td class='num'>{_n(r.get('QNT_PROG_TOTAL',0))}</td>"
                f"<td class='num'>{_n(r.get('QNT_CORTADA',0))}</td>"
                f"<td class='num {ef_cls}'>{ef:.1f}%</td>"
                f"<td class='{cls}'>{status_c}</td>"
                f"</tr>"
            )
        return "\n".join(linhas)

    op_html = _op_rows()
    ef_total = (total_cort_pcs / total_prog_pcs * 100) if total_prog_pcs > 0 else 0
    cls_ef = "sok" if ef_total >= 96 else ("samb" if ef_total >= 50 else "serr")

    html = (
        "<!DOCTYPE html>\n<html lang='pt-BR'>\n<head>\n"
        "<meta charset='UTF-8'>\n"
        "<title>Relatório Controle de Programação</title>\n"
        "<style>\n"
        "@page { margin: 15mm; size: A4 landscape; }\n"
        "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "body { font-family: Arial, sans-serif; font-size: 10px; color: #1a1a1a; background: #fff; }\n"
        ".hint { background:#FEF3C7; padding:8px 14px; margin-bottom:14px; border-radius:4px; font-size:12px; border:1px solid #FCD34D; }\n"
        ".header { border-bottom:3px solid #6366F1; padding-bottom:8px; margin-bottom:14px; }\n"
        ".header h1 { font-size:17px; color:#1E1B4B; }\n"
        ".header .sub { color:#444; margin-top:3px; font-size:10px; }\n"
        ".kpi-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:6px; margin-bottom:16px; }\n"
        ".kpi { border:1px solid #6366F1; border-radius:5px; padding:6px 8px; text-align:center; }\n"
        ".kpi-lbl { font-size:7.5px; color:#555; text-transform:uppercase; letter-spacing:.05em; }\n"
        ".kpi-val { font-size:13px; font-weight:700; color:#1E1B4B; margin-top:2px; }\n"
        ".sec { font-size:11px; font-weight:700; color:#1E1B4B; border-bottom:1px solid #6366F1; margin:14px 0 7px 0; padding-bottom:3px; }\n"
        "table { width:100%; border-collapse:collapse; margin-bottom:14px; font-size:9px; }\n"
        "th { background:#1E1B4B; color:#fff; padding:4px 6px; text-align:left; font-size:8px; text-transform:uppercase; letter-spacing:.04em; }\n"
        "td { padding:3px 5px; border-bottom:1px solid #e5e7eb; }\n"
        "tr:nth-child(even) td { background:#F5F3FF; }\n"
        ".num { text-align:right; font-variant-numeric:tabular-nums; }\n"
        ".sok { color:#065F46; font-weight:600; }\n"
        ".samb { color:#92400E; font-weight:600; }\n"
        ".serr { color:#B91C1C; font-weight:600; }\n"
        ".footer { margin-top:16px; padding-top:7px; border-top:1px solid #ccc; color:#777; font-size:8px; text-align:center; }\n"
        "@media print { .hint { display:none; } body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }\n"
        "</style>\n</head>\n<body>\n"
        "<div class='hint'><strong>Para gerar PDF:</strong> pressione <kbd>Ctrl+P</kbd> (Windows) "
        "ou <kbd>&#8984;+P</kbd> (Mac) &rarr; <em>Salvar como PDF</em>.</div>\n"
        "<div class='header'>\n"
        "  <h1>&#128202; Relatório Controle de Programação de Corte</h1>\n"
        f"  <div class='sub'>{filtros_label} &nbsp;|&nbsp; Gerado em: {agora}</div>\n"
        "</div>\n"
        "<div class='kpi-grid'>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Total de OPs</div><div class='kpi-val'>{total_ops}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Concluídas</div><div class='kpi-val sok'>{concluidas}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Parciais</div><div class='kpi-val samb'>{parciais}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Pendentes</div><div class='kpi-val serr'>{pendentes}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Aderência</div><div class='kpi-val'>{aderencia_pct:.1f}%</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Peças Prog.</div><div class='kpi-val'>{_n(total_prog_pcs)}</div></div>\n"
        f"  <div class='kpi'><div class='kpi-lbl'>Peças Cortadas</div><div class='kpi-val {cls_ef}'>{_n(total_cort_pcs)}</div></div>\n"
        "</div>\n"
        "<div class='sec'>Resumo por Ordem (OP)</div>\n"
        "<table>\n"
        "  <thead><tr><th>Sem.</th><th>OP</th><th>Cliente</th><th>Local</th><th>Produto</th>"
        "<th class='num'>Prog.</th><th class='num'>Cortado</th>"
        "<th class='num'>Efic. %</th><th>Status Corte</th></tr></thead>\n"
        f"  <tbody>{op_html}</tbody>\n"
        "</table>\n"
        "<div class='footer'>"
        f"Relatório Controle de Programação de Corte &middot; "
        f"Sistema Unificação dos Dados &middot; {agora}"
        "</div>\n</body>\n</html>"
    )
    return html.encode("utf-8")

