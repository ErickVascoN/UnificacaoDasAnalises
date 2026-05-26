# -*- coding: utf-8 -*-
"""
Central de Atualizações — adicione novos itens no topo da lista.
Campos obrigatórios: date, tag, title, description
tag: "novo" | "melhoria" | "correção"
"""

CHANGELOG = [
    {
        "date": "26/05/2026",
        "tag": "correção",
        "title": "Controladoria Programação — corte de lençol não aparecia (QNT CORTADA zerada)",
        "description": (
            "A planilha de lançamentos de corte de lençol (Arealva) não estava sendo carregada "
            "em 4_Controladoria_Programacao.py. Adicionada como terceira fonte em load_cortes(), "
            "com tratamento da coluna QUANT (vs QUANTIDADE nas demais) e header detection para "
            "linha de título. Aprimorado o matching: tenta PED. CLIENTE → OP e, se não encontrar, "
            "tenta OP INTERNA → OP. Sidebar agora exibe contagem de registros por fonte para diagnóstico."
        ),
    },
    {
        "date": "26/05/2026",
        "tag": "novo",
        "title": "Análise de Metas / Previsão de Custos — nova página automática",
        "description": (
            "Nova página 7_Plano_de_Metas.py acessível pelo card 'Análise de Metas / Previsão de Custos' "
            "na aba Análise de Dados. Cruza o plano de metas (planilha Google Sheets) com os lançamentos "
            "diários de 4 unidades (GGTTEX, ZANATTEX, LITEX-Fronha, LITEX-Geral) e o xlsx de Produção Geral. "
            "Exibe KPIs automáticos, tabela de progresso por prestador, gráfico de série temporal com projeção "
            "linear até fim do mês, análise de custos e receita por centro de custo, e gerador de plano do "
            "próximo mês em .xlsx calibrado pelo rendimento real (apenas Admin)."
        ),
    },
    {
        "date": "26/05/2026",
        "tag": "novo",
        "title": "GUIA.md — documentação completa do projeto",
        "description": (
            "Criado GUIA.md na raiz do projeto com explicação de toda a arquitetura, "
            "como rodar, autenticação, dashboards, configuração de planilhas e metas, "
            "como adicionar novos setores, como usar o changelog e dicas práticas de uso."
        ),
    },
    {
        "date": "26/05/2026",
        "tag": "melhoria",
        "title": "Manta Arealva — Mesa 2 removida e layout adaptativo",
        "description": (
            "Mesa 2 retirada do dashboard de Corte da Manta Arealva. "
            "Cards de progresso, KPIs por estação e colunas de análise agora se centralizam "
            "automaticamente — ao adicionar ou remover uma estação em CORTE_METAS, "
            "todos os componentes se adaptam sem precisar alterar o layout."
        ),
    },
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
