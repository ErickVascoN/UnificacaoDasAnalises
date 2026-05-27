"""
📋 DATA INTEGRITY CHECKS - Validações de Integridade de Dados

Este módulo fornece funções para validação de integridade dos dados
carregados pelos dashboards. Usado para detectar problemas de parsing,
campos inválidos, ou inconsistências estruturais.

Uso:
    from data_integrity_checks import validate_corte_lencol
    
    df = load_corte_lencol()
    issues = validate_corte_lencol(df)
    if issues:
        print(f"⚠️ {len(issues)} problemas encontrados:")
        for issue in issues:
            print(f"  - {issue}")

Referência: AUDITORIA_QUALIDADE_DADOS.md
"""

import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ─
# VALIDAÇÕES ESPECÍFICAS POR DASHBOARD
# ─

def validate_corte_lencol(df: pd.DataFrame) -> list:
    """
    Valida integridade dos dados de Corte de Lençol.
    
    Retorna:
        list: Lista de mensagens de problema encontradas (vazia se OK)
    """
    issues = []
    
    # Verificar colunas obrigatórias
    required_cols = ["DATA", "PRESTADOR", "QUANT", "CATEGORIA"]
    for col in required_cols:
        if col not in df.columns:
            issues.append(f"❌ Coluna obrigatória faltando: {col}")
    
    if not issues:  # Só continua se tem as colunas
        # Verificar datas futuras (mais de 1 dia no futuro)
        tomorrow = pd.Timestamp.now() + timedelta(days=1)
        future_dates = (df["DATA"] > tomorrow).sum()
        if future_dates > 0:
            issues.append(f"⚠️ {future_dates} registros com datas muito futuras")
        
        # Verificar datas inválidas (NaT)
        invalid_dates = df["DATA"].isna().sum()
        if invalid_dates > 0:
            issues.append(f"⚠️ {invalid_dates} registros com DATA = NaT")
        
        # Verificar quantidades negativas
        if "QUANT" in df.columns:
            negative_qty = (df["QUANT"] < 0).sum()
            if negative_qty > 0:
                issues.append(f"⚠️ {negative_qty} registros com QUANTIDADE negativa")
        
        # Verificar PRESTADOR vazio
        if "PRESTADOR" in df.columns:
            empty_prestador = (df["PRESTADOR"].astype(str).str.strip() == "").sum()
            if empty_prestador > 0:
                issues.append(f"⚠️ {empty_prestador} registros com PRESTADOR vazio")
    
    return issues

def validate_producao_geral(df: pd.DataFrame) -> list:
    """
    Valida integridade dos dados de Produção Geral.
    
    Retorna:
        list: Lista de mensagens de problema encontradas (vazia se OK)
    """
    issues = []
    
    required_cols = ["Data", "Faccao", "Quantidade"]
    for col in required_cols:
        if col not in df.columns:
            issues.append(f"❌ Coluna obrigatória faltando: {col}")
    
    if not issues:
        # Verificar datas inválidas
        invalid_dates = df["Data"].isna().sum()
        if invalid_dates > 0:
            issues.append(f"⚠️ {invalid_dates} registros com Data = NaT")
        
        # Verificar quantidades negativas ou zero
        if "Quantidade" in df.columns:
            zero_qty = (df["Quantidade"] <= 0).sum()
            if zero_qty > 0:
                issues.append(f"⚠️ {zero_qty} registros com Quantidade <= 0")
    
    return issues

def validate_faturamento(df: pd.DataFrame) -> list:
    """
    Valida integridade dos dados de Faturamento.
    
    Retorna:
        list: Lista de mensagens de problema encontradas (vazia se OK)
    """
    issues = []
    
    required_cols = ["Data", "Quantidade"]
    for col in required_cols:
        if col not in df.columns:
            issues.append(f"❌ Coluna obrigatória faltando: {col}")
    
    if not issues:
        # Verificar datas inválidas
        invalid_dates = df["Data"].isna().sum()
        if invalid_dates > 0:
            issues.append(f"⚠️ {invalid_dates} registros com Data = NaT")
        
        # Verificar quantidades negativas
        if "Quantidade" in df.columns:
            negative_qty = (df["Quantidade"] < 0).sum()
            if negative_qty > 0:
                issues.append(f"⚠️ {negative_qty} registros com Quantidade negativa")
    
    return issues

# ─
# VALIDAÇÕES GENÉRICAS
# ─

def check_date_columns(df: pd.DataFrame, date_cols: list = None) -> dict:
    """
    Valida colunas de data em um DataFrame.
    
    Args:
        df: DataFrame a validar
        date_cols: Lista de nomes de colunas de data. Se None, auto-detecta
    
    Retorna:
        dict: Estatísticas de validação com estrutura:
            {
                'coluna': {
                    'total': int,
                    'valid': int,
                    'nat': int,
                    'future': int,
                    'samples': [examples of invalid]
                }
            }
    """
    if date_cols is None:
        date_cols = [col for col in df.columns if 'data' in col.lower() or 'date' in col.lower()]
    
    results = {}
    for col in date_cols:
        if col not in df.columns:
            results[col] = {'error': f'Coluna {col} não encontrada'}
            continue
        
        try:
            # Converter para datetime se necessário
            dates = pd.to_datetime(df[col], errors='coerce')
            
            total = len(dates)
            valid = dates.notna().sum()
            nat_count = dates.isna().sum()
            future = (dates > pd.Timestamp.now()).sum()
            
            # Amostras de valores inválidos
            invalid_samples = df[dates.isna()][col].drop_duplicates().head(3).tolist()
            
            results[col] = {
                'total': total,
                'valid': valid,
                'nat': nat_count,
                'future': future,
                'pct_valid': round(100 * valid / total, 1) if total > 0 else 0,
                'invalid_samples': invalid_samples
            }
        except Exception as e:
            results[col] = {'error': str(e)}
    
    return results

def check_numeric_columns(df: pd.DataFrame, numeric_cols: list = None) -> dict:
    """
    Valida colunas numéricas em um DataFrame.
    
    Args:
        df: DataFrame a validar
        numeric_cols: Lista de nomes de colunas numéricas. Se None, auto-detecta
    
    Retorna:
        dict: Estatísticas por coluna
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    results = {}
    for col in numeric_cols:
        if col not in df.columns:
            results[col] = {'error': f'Coluna {col} não encontrada'}
            continue
        
        try:
            values = pd.to_numeric(df[col], errors='coerce')
            valid = values.notna().sum()
            total = len(values)
            
            results[col] = {
                'total': total,
                'valid': valid,
                'invalid': total - valid,
                'pct_valid': round(100 * valid / total, 1) if total > 0 else 0,
                'min': float(values.min()) if valid > 0 else None,
                'max': float(values.max()) if valid > 0 else None,
                'mean': float(values.mean()) if valid > 0 else None,
                'negative_count': (values < 0).sum() if valid > 0 else 0,
            }
        except Exception as e:
            results[col] = {'error': str(e)}
    
    return results

def check_missing_values(df: pd.DataFrame) -> dict:
    """
    Retorna estatísticas de valores faltantes por coluna.
    
    Retorna:
        dict: {'coluna': {'total': int, 'missing': int, 'pct': float}}
    """
    results = {}
    for col in df.columns:
        total = len(df)
        missing = df[col].isna().sum()
        results[col] = {
            'total': total,
            'missing': missing,
            'pct': round(100 * missing / total, 1) if total > 0 else 0
        }
    return results

def generate_data_quality_report(df: pd.DataFrame, name: str = "Dataset") -> str:
    """
    Gera um relatório completo de qualidade de dados.
    
    Args:
        df: DataFrame a analisar
        name: Nome do dataset (para exibição)
    
    Retorna:
        str: Relatório formatado em texto
    """
    report = []
    report.append(f"\n{'='*60}")
    report.append(f"📊 RELATÓRIO DE QUALIDADE: {name}")
    report.append(f"{'='*60}")
    
    # Informações gerais
    report.append(f"\n📈 INFORMAÇÕES GERAIS:")
    report.append(f"  Linhas: {len(df):,}")
    report.append(f"  Colunas: {len(df.columns)}")
    report.append(f"  Memória: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    # Valores faltantes
    report.append(f"\n❓ VALORES FALTANTES:")
    missing = check_missing_values(df)
    for col, stats in missing.items():
        if stats['missing'] > 0:
            report.append(f"  {col}: {stats['missing']} ({stats['pct']}%)")
    
    # Colunas de data
    report.append(f"\n📅 COLUNAS DE DATA:")
    date_check = check_date_columns(df)
    for col, stats in date_check.items():
        if 'error' in stats:
            report.append(f"  {col}: ❌ {stats['error']}")
        else:
            report.append(f"  {col}: {stats['valid']}/{stats['total']} válidas ({stats['pct_valid']}%)")
            if stats['nat'] > 0:
                report.append(f"    ⚠️ {stats['nat']} NaT encontrados")
            if stats['future'] > 0:
                report.append(f"    ℹ️ {stats['future']} datas futuras")
    
    # Colunas numéricas
    report.append(f"\n🔢 COLUNAS NUMÉRICAS:")
    numeric_check = check_numeric_columns(df)
    for col, stats in numeric_check.items():
        if 'error' in stats:
            report.append(f"  {col}: ❌ {stats['error']}")
        else:
            report.append(f"  {col}: {stats['valid']}/{stats['total']} válidas ({stats['pct_valid']}%)")
            if stats['negative_count'] > 0:
                report.append(f"    ⚠️ {stats['negative_count']} valores negativos")
            report.append(f"    Range: [{stats['min']}, {stats['max']}]")
    
    report.append(f"\n{'='*60}\n")
    
    return "\n".join(report)

# ─
# MAIN - Para testes diretos
# ─

if __name__ == "__main__":
    """
    Teste rápido das funções de validação.
    
    Uso:
        python data_integrity_checks.py
    """
    print("🔍 Data Integrity Checks Module")
    print("Import este módulo em suas aplicações para usar as funções de validação.")
    print("\nExemplo:")
    print("  from data_integrity_checks import validate_corte_lencol")
    print("  df = load_corte_lencol()")
    print("  issues = validate_corte_lencol(df)")
