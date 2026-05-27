"""Utilitário para detectar automaticamente o GID de abas do Google Sheets."""

from __future__ import annotations
import re
import urllib.request
from urllib.error import HTTPError, URLError

def detectar_gid_google_sheets(spreadsheet_id: str) -> str:
    """
    Detecta automaticamente o GID (Grid ID) da primeira aba da planilha.

    Args:
        spreadsheet_id: ID da planilha Google Sheets.

    Returns:
        O GID detectado, ou "0" como fallback.
    """
    print(f"🔍 Detectando GID para a planilha: {spreadsheet_id}")
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")

        for pattern in (r'"gid":"?(\d+)"?', r'gid[=&](\d+)'):
            m = re.search(pattern, html)
            if m:
                gid = m.group(1)
                print(f"✅ GID detectado: {gid}")
                return gid

    except (HTTPError, URLError) as e:
        print(f"⚠️ Erro ao acessar a planilha: {e}")

    print("⚠️ Não foi possível detectar o GID, usando valor padrão: 0")
    return "0"

def listar_abas_google_sheets(spreadsheet_id: str) -> None:
    """
    Testa GIDs conhecidos e imprime quais retornam dados válidos.

    Args:
        spreadsheet_id: ID da planilha Google Sheets.
    """
    print(f"\n📋 Tentando listar abas da planilha: {spreadsheet_id}")
    headers = {"User-Agent": "Mozilla/5.0"}
    gids_para_testar = ["0", "206085601", "1", "2", "3"]

    for gid in gids_para_testar:
        url = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            f"/gviz/tq?tqx=out:csv&gid={gid}"
        )
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                conteudo = response.read().decode("utf-8")
            linhas = len(conteudo.split("\n"))
            status = f"OK ({linhas} linhas)" if conteudo.strip() and linhas > 1 else "Vazio"
            print(f"{'✅' if 'OK' in status else '❌'} GID {gid}: {status}")
        except Exception:
            print(f"❌ GID {gid}: Erro na requisição")

if __name__ == "__main__":
    SPREADSHEET_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
    gid = detectar_gid_google_sheets(SPREADSHEET_ID)
    listar_abas_google_sheets(SPREADSHEET_ID)
    print(f"\n💡 GID detectado: {gid}")
