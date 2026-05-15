"""
Script para listar a estrutura do projeto
Execute com: python listar_estrutura.py
"""

import os
from pathlib import Path


def listar_estrutura(caminho=".", prefixo="", ignorar=None):
    """Exibe a estrutura de diretórios de forma visual"""
    
    if ignorar is None:
        ignorar = {
            '.git', '__pycache__', '.pytest_cache', 'venv', 'env',
            '.venv', '.env', '.DS_Store', '*.pyc', '*.egg-info',
            '.streamlit', '__pycache__'
        }
    
    items = []
    try:
        for item in sorted(os.listdir(caminho)):
            # Pular itens ignorados
            if item in ignorar or item.startswith('.'):
                continue
            
            caminho_item = os.path.join(caminho, item)
            is_dir = os.path.isdir(caminho_item)
            
            # Símbolo
            simbolo = "📁" if is_dir else "📄"
            items.append((item, is_dir, caminho_item))
    
    except PermissionError:
        return
    
    for i, (item, is_dir, caminho_item) in enumerate(items):
        eh_ultimo = (i == len(items) - 1)
        
        # Caracteres visuais
        simbolo_arvore = "└── " if eh_ultimo else "├── "
        novo_prefixo = prefixo + ("    " if eh_ultimo else "│   ")
        
        # Ícone apropriado
        if is_dir:
            if item == "utils":
                print(f"{prefixo}{simbolo_arvore}🔧 {item}/")
            elif item == "pages":
                print(f"{prefixo}{simbolo_arvore}📄 {item}/")
            elif item == "sectors":
                print(f"{prefixo}{simbolo_arvore}📊 {item}/")
            else:
                print(f"{prefixo}{simbolo_arvore}📁 {item}/")
            
            # Recursão
            listar_estrutura(caminho_item, novo_prefixo, ignorar)
        else:
            # Ícone por tipo de arquivo
            if item.endswith('.py'):
                print(f"{prefixo}{simbolo_arvore}🐍 {item}")
            elif item.endswith('.md'):
                print(f"{prefixo}{simbolo_arvore}📝 {item}")
            elif item.endswith('.txt'):
                print(f"{prefixo}{simbolo_arvore}📋 {item}")
            elif item.endswith('.json'):
                print(f"{prefixo}{simbolo_arvore}⚙️  {item}")
            else:
                print(f"{prefixo}{simbolo_arvore}📄 {item}")


if __name__ == "__main__":
    print("🎯 Estrutura do Dashboard Unificado")
    print("=" * 50)
    print()
    listar_estrutura(".")
    print()
    print("=" * 50)
    print("✅ Estrutura listada com sucesso!")
