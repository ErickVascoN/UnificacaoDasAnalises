"""
Cria a planilha Google Sheets "Producao Semanal - Externas" com 4 abas:
    MEGA BARIRI | PREVITTEX MATRIZ | PREVITTEX FILIAL | MEGA PREVEN

Cada aba contém cabeçalho formatado + linhas de exemplo para as fábricas preencherem
diariamente com: DATA | PRODUTO | CLIENTE | QUANTIDADE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRÉ-REQUISITO (configuração única — ~5 min)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Acesse: https://console.cloud.google.com
2. Crie ou selecione um projeto
3. Menu "APIs & Services" → "Enable APIs" → ative:
     • Google Sheets API
     • Google Drive API
4. Menu "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID"
     • Application type: Desktop app
     • Nome: qualquer (ex: "Unificação Dados")
     • Baixe o JSON gerado
5. Renomeie o arquivo baixado para  credentials.json
   e coloque nesta pasta:  scripts/credentials.json
6. Execute:
     venv\Scripts\python.exe scripts\criar_planilha_externas.py

   Um browser abrirá pedindo autorização com sua conta Google.
   Após autorizar, o script cria a planilha e imprime o ID para configurar no sistema.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import gspread
    from gspread.utils import rowcol_to_a1
except ImportError:
    print("ERRO: gspread não instalado. Execute: venv\\Scripts\\pip install gspread")
    sys.exit(1)

# ── Caminhos ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
CREDS_FILE   = SCRIPT_DIR / "credentials.json"
TOKEN_FILE   = SCRIPT_DIR / "authorized_user.json"

if not CREDS_FILE.exists():
    print(
        f"\nERRO: Arquivo de credenciais não encontrado em:\n  {CREDS_FILE}\n\n"
        "Siga as instruções no início deste script para criar o credentials.json.\n"
    )
    sys.exit(1)

# ── Dados das fábricas ───────────────────────────────────────────────────────────
# Formato: (PRODUTO, CLIENTE)
FABRICA_DADOS: dict[str, list[tuple[str, str]]] = {
    "MEGA BARIRI": [
        ("COBERTOR TOQUE DE SEDA", "NC INDUSTRIA"),
        ("MANTA",                  "NC INDUSTRIA"),
    ],
    "PREVITTEX MATRIZ": [
        ("MANTA BABY",      "ANDREZA"),
        ("JOGOS DE CAMA",   "ANDREZA"),
        ("FRONHAS",         "CAMESA"),
        ("VELOUR",          "CAMESA"),
        ("MANTA PRENSADA",  "CAMESA"),
        ("MANTA C/ CINTA",  "CAMESA"),
        ("COBERTOR 180G",   "CAMESA"),
        ("BABY",            "CAMESA"),
        ("CORTINA",         "CAMESA"),
        ("JOGO DE CAMA",    "CORTTEX"),
    ],
    "PREVITTEX FILIAL": [
        ("MANTA BABY",    "ANDREZA"),
        ("JOGOS DE CAMA", "ANDREZA"),
        ("CORTINA",       "DECOR"),
        ("JOGO DE CAMA",  "DECOR"),
    ],
    "MEGA PREVEN": [
        ("FRONHAS",                "MARCELINO"),
        ("JG DUPLO PONTO PALITO",  "MARCELINO"),
        ("FRONHA PONTO PALITO",    "MARCELINO"),
        ("TONHAS",                 "MARCELINO"),
    ],
}

# ── Cores por fábrica (header) ───────────────────────────────────────────────────
HEADER_COLORS: dict[str, dict] = {
    "MEGA BARIRI":     {"red": 0.07, "green": 0.30, "blue": 0.20},  # verde escuro
    "PREVITTEX MATRIZ":{"red": 0.10, "green": 0.20, "blue": 0.45},  # azul escuro
    "PREVITTEX FILIAL":{"red": 0.15, "green": 0.25, "blue": 0.50},  # azul médio
    "MEGA PREVEN":     {"red": 0.35, "green": 0.10, "blue": 0.35},  # roxo escuro
}

# ── Helpers ──────────────────────────────────────────────────────────────────────

def _col_width_request(sheet_id: int, col_idx: int, pixels: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": col_idx,
                "endIndex": col_idx + 1,
            },
            "properties": {"pixelSize": pixels},
            "fields": "pixelSize",
        }
    }

def _freeze_request(sheet_id: int, rows: int = 1) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": rows},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    }

def _header_format_request(sheet_id: int, num_cols: int, color: dict) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": color,
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "fontSize": 11,
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
        }
    }

def _example_row_format_request(sheet_id: int, num_rows: int, num_cols: int) -> dict:
    """Deixa as linhas de exemplo em itálico e cinza claro."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 1 + num_rows,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.94, "green": 0.94, "blue": 0.94},
                    "textFormat": {
                        "italic": True,
                        "foregroundColor": {"red": 0.4, "green": 0.4, "blue": 0.4},
                    },
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    }

def _border_request(sheet_id: int, num_rows: int, num_cols: int) -> dict:
    """Borda fina em todas as células com dados."""
    solid = {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}}
    return {
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": num_rows,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "top": solid, "bottom": solid, "left": solid, "right": solid,
            "innerHorizontal": solid, "innerVertical": solid,
        }
    }

# ── Main ─────────────────────────────────────────────────────────────────────────

def main():
    print("\n🔐 Autenticando com Google...")
    gc = gspread.oauth(
        credentials_filename=str(CREDS_FILE),
        authorized_user_filename=str(TOKEN_FILE),
    )
    print("✅ Autenticado.\n")

    print("📋 Criando planilha...")
    sh = gc.create("Producao Semanal - Externas")
    print(f"✅ Planilha criada: {sh.title}")
    print(f"   ID: {sh.id}\n")

    HEADERS = ["DATA", "PRODUTO", "CLIENTE", "QUANTIDADE"]

    for idx, (fabrica, exemplos) in enumerate(FABRICA_DADOS.items()):
        print(f"  🏭 Configurando aba: {fabrica}")

        # Cria ou usa a aba (a primeira já existe como "Sheet1")
        if idx == 0:
            ws = sh.sheet1
            ws.update_title(fabrica)
        else:
            ws = sh.add_worksheet(title=fabrica, rows=500, cols=6)

        sheet_id = ws.id

        # ── Escreve cabeçalho + linhas de exemplo ──────────────────────────────
        rows: list[list] = [HEADERS]
        for produto, cliente in exemplos:
            rows.append(["DD/MM/AAAA", produto, cliente, 0])

        ws.update(rows, "A1")

        # ── Formatações via batchUpdate ────────────────────────────────────────
        color = HEADER_COLORS[fabrica]
        col_widths = [120, 260, 180, 130]
        requests = [
            _freeze_request(sheet_id),
            _header_format_request(sheet_id, len(HEADERS), color),
            _example_row_format_request(sheet_id, len(exemplos), len(HEADERS)),
            _border_request(sheet_id, 1 + len(exemplos), len(HEADERS)),
        ]
        for col_idx, pixels in enumerate(col_widths):
            requests.append(_col_width_request(sheet_id, col_idx, pixels))

        sh.batch_update({"requests": requests})
        print(f"     GID: {sheet_id}")

    # ── Compartilhamento ────────────────────────────────────────────────────────
    print("\n🌐 Configurando acesso público (leitura)...")
    sh.share(None, perm_type="anyone", role="reader")
    print("✅ Qualquer pessoa com o link pode VER a planilha.")

    # ── Resultado final ─────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("✅  PLANILHA CRIADA COM SUCESSO")
    print("═" * 60)
    print(f"\n📎 URL:  https://docs.google.com/spreadsheets/d/{sh.id}")
    print(f"\n🔑 SPREADSHEET_ID = \"{sh.id}\"")
    print("\n📊 GIDs das abas:")
    for ws in sh.worksheets():
        print(f"   {ws.title:<22} GID = {ws.id}")

    print("\n" + "─" * 60)
    print("PRÓXIMOS PASSOS:")
    print("─" * 60)
    print("1. Acesse a planilha pelo link acima")
    print("2. Para cada fábrica, clique em 'Compartilhar' e adicione")
    print("   o e-mail deles com permissão 'Editor'")
    print("3. Instrua-os a preencher somente a aba com o nome deles")
    print("4. Anote o SPREADSHEET_ID acima — será adicionado ao settings.py")
    print("   pelo desenvolvedor para conectar ao dashboard.\n")


if __name__ == "__main__":
    main()
