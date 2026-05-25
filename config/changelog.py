# -*- coding: utf-8 -*-
"""
Central de Atualizações — adicione novos itens no topo da lista.
Campos obrigatórios: date, tag, title, description
tag: "novo" | "melhoria" | "correção"
"""

CHANGELOG = [
    {
        "date": "25/05/2026",
        "tag": "melhoria",
        "title": "Limpeza de código morto e arquivos obsoletos",
        "description": (
            "Removidos arquivos sem uso: utils/google_sheets.py, utils/column_standards.py, "
            "components/EFICIENCIA_README.md, pasta docs/ e _backup_anterior_2026-05-14/. "
            "Função morta get_google_sheets_urls() removida de config/__init__.py."
        ),
    },
    {
        "date": "25/05/2026",
        "tag": "novo",
        "title": "Análise de Eficiência — Lençol Arealva",
        "description": (
            "Dashboard completo de eficiência do Lençol com KPIs de metros cortados, "
            "metros esperados, aproveitamento %, diferença (MTs) e retalho por OP. "
            "Inclui 4 gráficos e tabela detalhada com filtros por Cliente, Tecido e Status."
        ),
    },
    {
        "date": "25/05/2026",
        "tag": "melhoria",
        "title": "Formatação numérica brasileira em todo o projeto",
        "description": (
            "Todos os números acima de 1.000 agora usam ponto como separador de milhar "
            "(ex: 57.632 em vez de 57,632) em todos os dashboards, KPIs e tabelas."
        ),
    },
    {
        "date": "25/05/2026",
        "tag": "melhoria",
        "title": "Análise de Eficiência — Manta Arealva reformulada",
        "description": (
            "Novo detalhamento por OP com breakdown em kg: Peças Boas, Babys e Retalhos. "
            "KPIs de Aproveitamento %, Kgs Cortados e Divergência. Gráficos limitados a 10 OPs "
            "para melhor leitura. Fórmulas alinhadas com a planilha de origem."
        ),
    },
    {
        "date": "20/05/2026",
        "tag": "novo",
        "title": "Rastreador de OP na Programação de Corte",
        "description": (
            "Ferramenta na sidebar da Programação de Corte para localizar qualquer OP "
            "e ver exatamente de qual planilha os cortes estão vindo, com total de peças."
        ),
    },
    {
        "date": "20/05/2026",
        "tag": "melhoria",
        "title": "Status 'Concluído' por eficiência na Programação de Corte",
        "description": (
            "OPs com eficiência ≥ 98% agora aparecem automaticamente como Concluídas, "
            "mesmo que não tenham 100% das peças registradas."
        ),
    },
    {
        "date": "15/05/2026",
        "tag": "correção",
        "title": "Datas incorretas na Manta Arealva",
        "description": (
            "Corrigido problema onde datas no formato MM/DD/AAAA (exportadas pelo Google Sheets) "
            "eram interpretadas como DD/MM — causando registros em meses errados."
        ),
    },
    {
        "date": "10/05/2026",
        "tag": "novo",
        "title": "Análise de Faturamento (Produtos Faturados)",
        "description": (
            "Dashboard comercial com ranking de clientes, evolução de receita e "
            "visão consolidada dos produtos faturados por período."
        ),
    },
]
