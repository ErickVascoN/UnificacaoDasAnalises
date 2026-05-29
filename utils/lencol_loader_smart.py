"""
Carregador robusto para Lençol via XLSX:
- Baixa Excel direto do Google Sheets (sem CSV que bagunça)
- Estrutura limpa, sem mistura de dados
- Mais rápido e confiável
"""

import io
import pandas as pd
import logging

logger = logging.getLogger(__name__)

LENCOL_SPREADSHEET_ID = "1ypSEpTvIsm_hbgHmEf-v0fuR-P9h0mOa"
LENCOL_SPREADSHEET_GID = "1396046910"


def load_lencol_smart_xlsx() -> pd.DataFrame:
    """
    Carrega Lençol via CSV (com cache em disco via cache_manager).

    Estrutura real da planilha:
      Linha 0: HEADER (primeira coluna: "CONTROLE DE CORTE DIÁRIO LENÇOL DATA")
      Linha 1+: DADOS
    """
    from utils.cache_manager import get_raw
    try:
        conteudo = get_raw(LENCOL_SPREADSHEET_ID, LENCOL_SPREADSHEET_GID, ttl=60)
        if not conteudo or not conteudo.strip():
            logger.error("CSV vazio ou indisponível")
            return pd.DataFrame()
        
        # ── Detecta a LINHA do cabeçalho pelo conteúdo ──────────────────────────────
        # O Google (gviz/tq) adivinha o cabeçalho de forma instável quando há título
        # mesclado na linha 1. Em vez de confiar nisso, lemos a grade crua (header=None)
        # e localizamos a linha que contém os rótulos reais (PRESTADOR + OP).
        raw = pd.read_csv(io.StringIO(conteudo), header=None, dtype=str)
        hdr_idx = 0
        for i in range(min(12, len(raw))):
            vals = [str(v).strip().upper() for v in raw.iloc[i].tolist()]
            if any("PRESTADOR" in v for v in vals) and any(v == "OP" for v in vals):
                hdr_idx = i
                break
        df = raw.iloc[hdr_idx + 1:].copy().reset_index(drop=True)
        df.columns = [
            str(c).strip() if (c is not None and str(c).strip() and str(c) != "nan")
            else f"COL_{i}"
            for i, c in enumerate(raw.iloc[hdr_idx].tolist())
        ]

        logger.debug(f"CSV carregado: {len(df)} linhas (cabeçalho na linha {hdr_idx})")
        logger.debug(f"Colunas: {list(df.columns)[:6]}")
        
        # ── Mapeia colunas por CONTEÚDO (não por nome confuso) ─────────────────────────
        col_map = {}
        
        # Estratégia: Iterar primeiras 12 colunas (dados) e analisar conteúdo
        for i, col in enumerate(df.columns[:12]):
            col_upper = col.upper().strip()
            
            # Pega amostra de valores não-vazios
            sample = df[col].dropna().head(10)
            sample_str = ' '.join(str(v).strip() for v in sample)
            
            # Detecção por conteúdo - ESPECÍFICA para datas (M/D/YYYY ou D/M/YYYY)
            is_date_col = False
            if not sample.empty:
                # Procura por padrão específico: X/XX/2026 ou XX/XX/2026
                sample_vals = sample.astype(str).tolist()
                date_count = sum(1 for v in sample_vals 
                               if '/' in v and len(v.split('/')) == 3 and 
                               any(part.isdigit() for part in v.split('/')) and
                               ('202' in v or '203' in v))  # Ano >= 2020
                is_date_col = date_count >= 3  # Pelo menos 3 valores em formato de data
            
            # Mapeamento prioritário por conteúdo
            if is_date_col and "DATA" not in col_map:
                col_map["DATA"] = col
                logger.debug(f"  Col[{i}] '{col}' → DATA (amostra: {sample.head(2).tolist()})")
            
            elif col_upper in ("PRESTADOR/NOME", "PRESTADOR/NOME "):
                col_map["PRESTADOR"] = col
                logger.debug(f"  Col[{i}] '{col}' → PRESTADOR")
            
            elif col_upper == "OP":
                col_map["OP"] = col
                logger.debug(f"  Col[{i}] '{col}' → OP")
            
            elif col_upper in ("CATEGORIA", "CATEGORIA "):
                col_map["CATEGORIA"] = col
                logger.debug(f"  Col[{i}] '{col}' → CATEGORIA")
            
            elif (col_upper in ("EMPRESA", "EMPESA")  # nome correto (ou typo comum)
                  or col_upper in ("DATA ", "DATA")) and "EMPRESA" not in col_map:
                # Coluna da empresa. Historicamente vinha rotulada como "DATA" (confuso);
                # hoje pode estar correta como "EMPRESA"/"EMPESA". Cobre os dois casos.
                col_map["EMPRESA"] = col
                logger.debug(f"  Col[{i}] '{col}' → EMPRESA")
            
            elif col_upper in ("TECIDO/PRODUTO", "TECIDO/PRODUTO "):
                col_map["TECIDO"] = col
                logger.debug(f"  Col[{i}] '{col}' → TECIDO")
            
            elif col_upper == "QUANT":
                col_map["QUANT"] = col
                logger.debug(f"  Col[{i}] '{col}' → QUANT")
            
            elif "R$ A RECEBER" in col_upper or "R$ A RECEBER" in col_upper:
                col_map["VALOR_RECEBER"] = col
                logger.debug(f"  Col[{i}] '{col}' → VALOR_RECEBER")
            
            elif ("R$ PEÇA" in col_upper or "R$ PEÇA" in col_upper) and "VALOR_PECA" not in col_map:
                col_map["VALOR_PECA"] = col
                logger.debug(f"  Col[{i}] '{col}' → VALOR_PECA")
            
            elif "RETALHO" in col_upper or "RETALHO (KG)" in col_upper:
                col_map["RETALHO_KG"] = col
                logger.debug(f"  Col[{i}] '{col}' → RETALHO_KG")
            
            elif "OBS" in col_upper or "OBSERVAÇÕES" in col_upper:
                col_map["OBS"] = col
                logger.debug(f"  Col[{i}] '{col}' → OBS")
        
        logger.debug(f"Mapeamento encontrado: {col_map}")
        
        # ── Extrai colunas ──────────────────────────────────────────────────────────
        df_clean = pd.DataFrame()
        for col_novo, col_orig in col_map.items():
            if col_orig in df.columns:
                df_clean[col_novo] = df[col_orig]
                logger.debug(f"  Mapeado {col_novo} ← {col_orig}")
        
        if df_clean.empty:
            logger.error(f"Nenhuma coluna mapeada. Disponíveis: {list(df.columns)[:10]}")
            return pd.DataFrame()
        
        df = df_clean
        logger.debug(f"Colunas extraídas: {list(df.columns)}")
        logger.debug(f"Amostra DATA (antes de converter): {df['DATA'].head(3).tolist()}")
        
        # ── Limpeza ──────────────────────────────────────────────────────────────────
        # Remove linhas com dados insuficientes
        df = df[(df.notna().sum(axis=1) > 1)].copy().reset_index(drop=True)
        logger.debug(f"Após remover linhas vazias: {len(df)} linhas")
        
        if df.empty:
            logger.error("Nenhuma linha válida após limpeza")
            return pd.DataFrame()
        
        # Converte datas — detecção de formato por coluna (D/M vs M/D)
        if "DATA" in df.columns:
            from utils.date_parser import parse_date_series, detectar_ordem
            logger.debug(f"Convertendo datas (ordem detectada: {detectar_ordem(df['DATA'])})")
            df["DATA"] = parse_date_series(df["DATA"])
            valid_dates = df["DATA"].notna().sum()
            logger.debug(f"Datas válidas: {valid_dates}/{len(df)}")

            before = len(df)
            df = df[df["DATA"].notna()].copy()
            logger.debug(f"Após remover datas inválidas: {len(df)} linhas (-{before-len(df)})")
        
        if df.empty:
            logger.error("Nenhuma data válida encontrada")
            return pd.DataFrame()
        
        # Converte números
        for col in ("QUANT", "VALOR_PECA", "VALOR_RECEBER", "RETALHO_KG"):
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str)
                    .str.replace("R$", "", regex=False)
                    .str.strip()
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False),
                    errors="coerce",
                ).fillna(0)
        
        if "QUANT" in df.columns:
            df["QUANT"] = df["QUANT"].astype(int)
        
        # Normaliza OP — NÃO descarta linhas sem OP (cortes reais podem não ter número).
        # OP vazia vira "SEM OP" para preservar a produção do dia.
        if "OP" in df.columns:
            invalidos_op = {"", "NAN", "NONE", "N/A", "NAT", "-"}
            df["OP"] = df["OP"].astype(str).str.strip()
            df.loc[df["OP"].str.upper().isin(invalidos_op), "OP"] = "SEM OP"

        # Remove apenas linhas SEM dado de produção real (lixo/totais do fim da planilha):
        # nenhuma quantidade E sem prestador E sem categoria.
        tem_quant = df["QUANT"] > 0 if "QUANT" in df.columns else False
        tem_prest = (
            df["PRESTADOR"].astype(str).str.strip().str.upper()
            .replace({"NAN": "", "NONE": "", "N/A": ""}).ne("")
            if "PRESTADOR" in df.columns else False
        )
        tem_cat = (
            df["CATEGORIA"].astype(str).str.strip().str.upper()
            .replace({"NAN": "", "NONE": "", "N/A": ""}).ne("")
            if "CATEGORIA" in df.columns else False
        )
        antes = len(df)
        df = df[tem_quant | tem_prest | tem_cat].copy().reset_index(drop=True)
        removidas = antes - len(df)
        if removidas > 0:
            logger.debug(f"Removidas {removidas} linhas sem dado de produção (lixo/totais)")

        logger.info(f"✓ Lençol carregado: {len(df)} linhas válidas")
        return df
        
    except Exception as e:
        logger.error(f"Erro: {str(e)[:150]}")
        return pd.DataFrame()


# Mantém função antiga para compatibilidade
def load_lencol_smart_csv() -> pd.DataFrame:
    """Função legada - agora chama load_lencol_smart_xlsx"""
    logger.warning("load_lencol_smart_csv foi descontinuado, usando XLSX")
    return load_lencol_smart_xlsx()


# ─────────────────────────────────────────────────────────────────────────
# TESTE
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    df = load_lencol_smart_csv()
    
    print("\n" + "="*80)
    print(f"✓ Carregado: {len(df)} linhas")
    print(f"  Data range: {df['DATA'].min()} → {df['DATA'].max()}")
    print(f"  Prestadores: {df['PRESTADOR'].nunique()}")
    print(f"  OPs: {df['OP'].nunique()}")
    print(f"  Quantidade total: {df['QUANT'].sum():,} peças")
    print("="*80)
    
    # Mostra linhas de 27/05
    df_27_05 = df[df["DATA"].dt.strftime("%d/%m") == "27/05"]
    print(f"\n📅 Registros em 27/05: {len(df_27_05)}")
    print(f"OPs em 27/05: {sorted(df_27_05['OP'].unique())}")
