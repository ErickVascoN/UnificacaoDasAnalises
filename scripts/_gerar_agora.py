import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.relatorio_diario_corte import (
    carregar_manta_arealva, carregar_manta_iacanga,
    carregar_lencol_arealva, gerar_pdf, gerar_pdf_consolidado
)
from datetime import date, timedelta

dia = date.today() - timedelta(days=1)
desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Área de Trabalho")
if not os.path.isdir(desktop):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")

print(f"Carregando dados de {dia.strftime('%d/%m/%Y')}...")
a = carregar_manta_arealva(dia)
b = carregar_manta_iacanga(dia)
c = carregar_lencol_arealva(dia)

print("Gerando PDF diario...")
pdf_diario = gerar_pdf(dia, a, b, c)
nome_diario = os.path.join(desktop, f"relatorio_corte_{dia.strftime('%d-%m-%Y')}.pdf")
with open(nome_diario, "wb") as f:
    f.write(pdf_diario)
print(f"PDF diario salvo em: {nome_diario}")
os.startfile(nome_diario)

print("Gerando PDF consolidado (dia + mes + historico)...")
pdf_cons = gerar_pdf_consolidado(dia)
nome_cons = os.path.join(desktop, f"relatorio_consolidado_{dia.strftime('%d-%m-%Y')}.pdf")
with open(nome_cons, "wb") as f:
    f.write(pdf_cons)
print(f"PDF consolidado salvo em: {nome_cons}")
os.startfile(nome_cons)
