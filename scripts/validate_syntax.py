"""
Teste de sintaxe para validar imports nas páginas modificadas.
"""

import sys
import ast

files_to_check = [
    "pages/2_Producao_Geral.py",
    "pages/7_Plano_de_Metas.py",
    "pages/3_Controle_de_Corte.py",
]

print("=" * 80)
print("VALIDAÇÃO DE SINTAXE E IMPORTS")
print("=" * 80)

all_ok = True

for filepath in files_to_check:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Valida sintaxe Python
        ast.parse(code)
        print(f"✓ {filepath:50} — Sintaxe OK")
        
        # Verifica imports essenciais
        if "import time" in code or "from time" in code:
            print(f"  ✓ tem 'import time'")
        else:
            if "time.sleep" in code:
                print(f"  ⚠ usa time.sleep() mas não importa time!")
                all_ok = False
        
        if "import logging" in code or "from logging" in code:
            print(f"  ✓ tem 'import logging'")
        else:
            if "logging." in code:
                print(f"  ⚠ usa logging mas não importa!")
                all_ok = False
        
        if "import os" in code:
            print(f"  ✓ tem 'import os'")
        elif "os.path" in code:
            print(f"  ⚠ usa os.path mas não importa os!")
            all_ok = False
        
    except SyntaxError as e:
        print(f"✗ {filepath:50} — ERRO: {e}")
        all_ok = False
    except FileNotFoundError:
        print(f"✗ {filepath:50} — Arquivo não encontrado")
        all_ok = False
    except Exception as e:
        print(f"✗ {filepath:50} — Erro: {e}")
        all_ok = False

print("\n" + "=" * 80)
if all_ok:
    print("✓ TUDO OK! Pronto para reiniciar Streamlit.")
else:
    print("⚠ Há problemas a resolver.")
print("=" * 80)

sys.exit(0 if all_ok else 1)
