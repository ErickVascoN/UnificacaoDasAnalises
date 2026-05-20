# -*- coding: utf-8 -*-
"""
Mapeamento global de colunas padronizadas.

Centraliza a padronização de nomes de colunas entre todos os módulos,
facilitando a consolidação de dados de múltiplas fontes.
"""

from __future__ import annotations
import pandas as pd

# ── Mapeamento alias → nome padronizado ───────────────────────────────────────

COLUMN_ALIASES: dict[str, dict] = {
    "ESTACAO_PADRAO": {
        "aliases": ["Faccao", "ESTACAO", "ESTACAO DE CORTE", "MAQUINA", "MESA", "ESTACAO_CORTE"],
        "description": "Estação/Máquina/Fação de trabalho",
    },
    "DATA_PADRAO": {
        "aliases": ["DATA", "Date", "data", "DT", "Data", "DATA_PRODUCAO"],
        "description": "Data da produção/corte",
    },
    "QUANTIDADE_PADRAO": {
        "aliases": ["QUANTIDADE", "QUANT", "Quantidade", "QTD", "QUANTIDAD"],
        "description": "Quantidade produzida/cortada",
    },
    "PRODUTO_PADRAO": {
        "aliases": ["PRODUTO", "Produto", "CATEGORIA", "ITEM", "TIPO_PRODUTO"],
        "description": "Nome ou tipo do produto",
    },
    "PRESTADOR_PADRAO": {
        "aliases": ["PRESTADOR", "Prestador", "FORNECEDOR", "PESSOA", "OPERADOR"],
        "description": "Nome da pessoa/prestador",
    },
    "EMPRESA_PADRAO": {
        "aliases": ["EMPRESA", "Empresa", "FABRICANTE", "CLIENTE"],
        "description": "Nome da empresa/cliente",
    },
}

# ── Funções ───────────────────────────────────────────────────────────────────

def normalize_columns(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """
    Renomeia colunas do DataFrame para os nomes padronizados.

    Args:
        df: DataFrame com colunas para normalizar.
        verbose: Se True, imprime o mapeamento aplicado.

    Returns:
        DataFrame com colunas renomeadas (cópia).
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    rename_map: dict[str, str] = {}
    df_cols_upper = {col: col.upper() for col in df.columns}

    for standard_name, cfg in COLUMN_ALIASES.items():
        for alias in cfg["aliases"]:
            for orig_col, upper_col in df_cols_upper.items():
                if upper_col == alias.upper():
                    rename_map[orig_col] = standard_name
                    if verbose:
                        print(f"  ✓ {orig_col:20s} → {standard_name}")
                    break

    if rename_map:
        df = df.rename(columns=rename_map)
        if verbose:
            print(f"\nTotal de colunas normalizadas: {len(rename_map)}")

    return df


def check_required_columns(
    df: pd.DataFrame,
    required_names: list[str] | None = None,
    verbose: bool = False,
) -> bool:
    """
    Verifica se o DataFrame possui as colunas padronizadas requeridas.

    Args:
        df: DataFrame a verificar.
        required_names: Lista de nomes padronizados requeridos.
            Padrão: ['ESTACAO_PADRAO', 'DATA_PADRAO', 'QUANTIDADE_PADRAO'].
        verbose: Se True, imprime detalhes sobre colunas faltando.

    Returns:
        True se todas as colunas requeridas estão presentes.
    """
    if required_names is None:
        required_names = ["ESTACAO_PADRAO", "DATA_PADRAO", "QUANTIDADE_PADRAO"]

    missing = [col for col in required_names if col not in df.columns]

    if missing:
        if verbose:
            available = [c for c in df.columns if "_PADRAO" in c]
            print(f"❌ Colunas faltando: {missing}")
            print(f"   Disponíveis: {available}")
        return False

    if verbose:
        print("✓ Todas as colunas requeridas presentes")
    return True
