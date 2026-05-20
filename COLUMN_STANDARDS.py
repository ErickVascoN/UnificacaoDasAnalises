"""
MAPEAMENTO GLOBAL DE COLUNAS PADRONIZADAS

Este arquivo centraliza a padronização de nomes de colunas entre todos os módulos.
Facilita consolidação de dados e evita inconsistências.

IMPORTANTE: Sempre usar os nomes PADRONIZADOS internamente nas funções.
Usar este mapeamento para renomear colunas na leitura dos dados.

Autor: QA Audit - Fase 3
Data: 2026-01-XX
"""

# ======================================================================
# MAPEAMENTO DE NOMES DE COLUNAS
# ======================================================================

COLUMN_ALIASES = {
    """Possíveis variações de nomes de colunas encontradas nos dados"""
    
    'ESTACAO_PADRAO': {
        'aliases': ['Faccao', 'ESTACAO', 'ESTACAO DE CORTE', 'MAQUINA', 'MESA', 'ESTACAO_CORTE'],
        'description': 'Estação/Máquina/Fação de trabalho',
        'priority': 1,  # Deve ser padronizado primeiro
    },
    
    'DATA_PADRAO': {
        'aliases': ['DATA', 'Date', 'data', 'DT', 'Data', 'DATA_PRODUCAO'],
        'description': 'Data da produção/corte',
        'priority': 1,
    },
    
    'QUANTIDADE_PADRAO': {
        'aliases': ['QUANTIDADE', 'QUANT', 'Quantidade', 'QTD', 'QUANTIDAD'],
        'description': 'Quantidade produzida/cortada',
        'priority': 1,
    },
    
    'PRODUTO_PADRAO': {
        'aliases': ['PRODUTO', 'Produto', 'CATEGORIA', 'ITEM', 'TIPO_PRODUTO'],
        'description': 'Nome ou tipo do produto',
        'priority': 2,
    },
    
    'PRESTADOR_PADRAO': {
        'aliases': ['PRESTADOR', 'Prestador', 'FORNECEDOR', 'PESSOA', 'OPERADOR'],
        'description': 'Nome da pessoa/prestador',
        'priority': 2,
    },
    
    'EMPRESA_PADRAO': {
        'aliases': ['EMPRESA', 'Empresa', 'FABRICANTE', 'CLIENTE'],
        'description': 'Nome da empresa/cliente',
        'priority': 2,
    },
}

# ======================================================================
# FUNÇÃO DE NORMALIZAÇÃO
# ======================================================================

def normalize_columns(df, verbose=False):
    """
    Normaliza os nomes das colunas do DataFrame para valores padronizados.
    
    Args:
        df (pd.DataFrame): DataFrame com colunas para normalizar
        verbose (bool): Se True, imprime o mapeamento aplicado
        
    Returns:
        pd.DataFrame: DataFrame com colunas renomeadas
        
    Example:
        >>> df = load_data()
        >>> df = normalize_columns(df, verbose=True)
        # Colunas serão renomeadas automaticamente
    """
    import pandas as pd
    
    if df is None or df.empty:
        return df
    
    df = df.copy()
    rename_map = {}
    
    # Construir mapa de nomes encontrados -> padronizados
    df_cols_upper = {col: col.upper() for col in df.columns}
    
    for standard_name, config in COLUMN_ALIASES.items():
        for alias in config['aliases']:
            # Procura tanto por match exato quanto em maiúsculas
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


# ======================================================================
# FUNÇÃO DE VERIFICAÇÃO
# ======================================================================

def check_required_columns(df, required_names=None, verbose=False):
    """
    Verifica se DataFrame tem as colunas necessárias após normalização.
    
    Args:
        df (pd.DataFrame): DataFrame a verificar
        required_names (list): Lista de nomes padronizados requeridos
        verbose (bool): Se True, imprime detalhes
        
    Returns:
        bool: True se todas as colunas requeridas estão presentes
        
    Example:
        >>> required = ['ESTACAO_PADRAO', 'DATA_PADRAO', 'QUANTIDADE_PADRAO']
        >>> if not check_required_columns(df, required):
        ...     raise ValueError("Colunas obrigatórias faltando!")
    """
    if required_names is None:
        required_names = [
            'ESTACAO_PADRAO',
            'DATA_PADRAO', 
            'QUANTIDADE_PADRAO'
        ]
    
    missing = [col for col in required_names if col not in df.columns]
    
    if missing:
        available = [c for c in df.columns if '_PADRAO' in c]
        if verbose:
            print(f"❌ Colunas faltando: {missing}")
            print(f"   Disponíveis: {available}")
        return False
    
    if verbose:
        print(f"✓ Todas as colunas requeridas presentes")
    
    return True


# ======================================================================
# EXEMPLOS DE USO
# ======================================================================

"""
EXEMPLO 1: Normalizar coluna ao carregar dados
────────────────────────────────────────────

def load_data_producao():
    df = pd.read_csv("producao.csv")
    
    # ANTES: df tem coluna 'Faccao'
    # DEPOIS: df tem coluna 'ESTACAO_PADRAO'
    df = normalize_columns(df)
    
    return df


EXEMPLO 2: Garantir colunas requeridas
───────────────────────────────────────

def processar_dados(df):
    df = normalize_columns(df, verbose=True)
    
    required = ['ESTACAO_PADRAO', 'DATA_PADRAO', 'QUANTIDADE_PADRAO']
    if not check_required_columns(df, required):
        raise ValueError("Dados inválidos após normalização")
    
    # Agora posso usar com segurança:
    df['ESTACAO_PADRAO'].value_counts()
    df['DATA_PADRAO'].min()
    df['QUANTIDADE_PADRAO'].sum()


EXEMPLO 3: Consolidar dados de múltiplas fontes
───────────────────────────────────────────────

df1 = pd.read_csv("producao.csv")  # tem 'Faccao'
df2 = pd.read_csv("corte.csv")     # tem 'ESTACAO DE CORTE'

df1 = normalize_columns(df1)
df2 = normalize_columns(df2)

# Agora ambas têm 'ESTACAO_PADRAO' e podem ser concatenadas!
df_consolidado = pd.concat([df1, df2])
"""
