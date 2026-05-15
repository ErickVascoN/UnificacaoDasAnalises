"""
Utilitário para detectar automaticamente o GID correto do Google Sheets.
Execute este script quando a planilha tiver mudanças estruturais.
"""

import urllib.request
import urllib.parse
import re
from urllib.error import HTTPError, URLError

def detectar_gid_google_sheets(spreadsheet_id):
    """
    Detecta automaticamente o GID (Grid ID) da primeira aba do Google Sheets.
    
    Args:
        spreadsheet_id (str): ID da planilha Google Sheets
    
    Returns:
        str: O GID detectado
    """
    print(f"🔍 Detectando GID para a planilha: {spreadsheet_id}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # URL para acessar o HTML da planilha
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Procurar pelo gid no HTML (geralmente vem em um atributo data)
            # Padrão: "gid":"206085601" ou similar
            match = re.search(r'"gid":"?(\d+)"?', html)
            if match:
                gid = match.group(1)
                print(f"✅ GID detectado: {gid}")
                return gid
            
            # Fallback: procurar de outra forma
            match = re.search(r'gid[=&](\d+)', html)
            if match:
                gid = match.group(1)
                print(f"✅ GID detectado (método alternativo): {gid}")
                return gid
                
    except (HTTPError, URLError) as e:
        print(f"⚠️ Erro ao acessar a planilha: {e}")
    
    # Se não conseguir detectar, retorna 0 (primeira aba padrão)
    print("⚠️ Não foi possível detectar o GID, usando valor padrão: 0")
    return "0"


def listar_abas_google_sheets(spreadsheet_id):
    """
    Lista todas as abas disponíveis na planilha (requer acesso via gviz).
    
    Args:
        spreadsheet_id (str): ID da planilha Google Sheets
    """
    print(f"\n📋 Tentando listar abas da planilha: {spreadsheet_id}")
    print("⚠️ Nota: Este método pode não funcionar se a planilha não está configurada corretamente.")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    gids_para_testar = ["0", "206085601", "1", "2", "3"]
    
    print("\n🔄 Testando GIDs conhecidos:\n")
    
    for gid in gids_para_testar:
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                conteudo = response.read().decode('utf-8')
                linhas = len(conteudo.split('\n'))
                if conteudo.strip() and linhas > 1:
                    print(f"✅ GID {gid}: OK ({linhas} linhas)")
                else:
                    print(f"❌ GID {gid}: Vazio ou inválido")
        except:
            print(f"❌ GID {gid}: Erro na requisição")


if __name__ == "__main__":
    SPREADSHEET_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
    
    print("=" * 60)
    print("🔧 Ferramenta de Detecção de GID - Google Sheets")
    print("=" * 60)
    
    # Detectar GID
    gid = detectar_gid_google_sheets(SPREADSHEET_ID)
    
    # Listar abas
    listar_abas_google_sheets(SPREADSHEET_ID)
    
    print("\n" + "=" * 60)
    print("💡 Dica: O GID detectado é:", gid)
    print("   Se precisar usar um GID específico, atualize")
    print("   a variável GOOGLE_SHEETS_GID no dashboard.py")
    print("=" * 60)
