# -*- coding: utf-8 -*-
"""Definição de todos os cards de setor exibidos na home."""

SECTORS_ANALISE = [
    {
        "key": "corte",
        "title": "Análise de Corte",
        "subtitle": "Mantas/ Lençol — estações e desempenho",
        "description": (
            "Painel operacional dos setores de corte com metas "
            "diárias por estação, produção, "
            "OPs, Cores, indicadores por operador "
            "e Ranking de desempenho."
        ),
        "icon": "✂️",
        "page_path": "pages/3_Controle_de_Corte.py",
        "color_a": "#1F3A93",
        "color_b": "#45B7D1",
        "accent":  "#4ECDC4",
        "tags": ["Operação", "Corte", "Metas diárias"],
        "requires_auth": True,
        "note": "Falta Carline",
    },
    {
        "key": "producao",
        "title": "Análise de Produção",
        "subtitle": "Multi-empresas em tempo real",
        "description": (
            "Acompanhamento da produção de todas as empresas do grupo "
            "(Burdays, Camesa, Niazitex, Cortex, Sultan, Decor, Marcelino) "
            "com metas e evolução diária."
        ),
        "icon": "🏭",
        "page_path": "pages/2_Producao_Geral.py",
        "color_a": "#0F4C5C",
        "color_b": "#4ECDC4",
        "accent":  "#FFA726",
        "tags": ["Produção", "Multi-empresa", "Metas"],
        "requires_auth": True,
        "note": "Em Construção",
    },
    {
        "key": "faturados",
        "title": "Análise de Faturamento",
        "subtitle": "Análise comercial e faturamento",
        "description": (
            "Visão completa de produtos faturados, ranking de clientes, "
            "evolução de receita, Acompanhamento comercial para tomada de decisões estratégicas."
        ),
        "icon": "📊",
        "page_path": "pages/1_Produtos_Faturados.py",
        "color_a": "#1D3557",
        "color_b": "#0C6E74",
        "accent":  "#E76F51",
        "tags": ["Comercial", "Receita", "Clientes"],
        "requires_auth": True,
        "note": "Em Construção",
    },
    {
        "key": "apontador_gut",
        "title": "Central de Controle GUT",
        "subtitle": "Apontador Zanattex — Controle de eficiência",
        "description": (
            "Painel de acompanhamento em tempo real do GUT (Giattex) com dados de "
            "eficiência, horas, operadores e performance."
        ),
        "icon": "⏱️",
        "external_url": (
            "https://www.appsheet.com/start/6ab5d5b4-6ceb-4641-be36-26a273f1f303"
            "#appName=ApontadorZanattex-819603934"
            "&group=%5B%7B%22Column%22%3A%22Data%22%2C%22Order%22%3A%22Descending%22%7D%5D"
            "&page=fastTable"
            "&sort=%5B%7B%22Column%22%3A%22Hora%22%2C%22Order%22%3A%22Descending%22%7D"
            "%2C%7B%22Column%22%3A%22Efici%C3%AAncia%22%2C%22Order%22%3A%22Descending%22%7D%5D"
            "&table=GIATTEX&view=GIATTEX"
        ),
        "color_a": "#1F4A5A",
        "color_b": "#2E8B9E",
        "accent":  "#26D0CE",
        "tags": ["GUT", "Eficiência", "Real-time"],
        "requires_auth": True,
        "note": "Falta Alguns Setores",
    },
    {
        "key": "analise_dados_gut",
        "title": "Análise de Dados GUT",
        "subtitle": "Dashboard analítico — Insights e tendências",
        "description": (
            "Análise completa dos dados do GUT em formato de dashboard interativo. "
            "Visualize tendências, indicadores de desempenho e insights estratégicos."
        ),
        "icon": "📈",
        "external_url": "https://datastudio.google.com/u/0/reporting/720db0c0-be65-40d9-ae9d-7627741385ce/page/p_si214uowdd",
        "color_a": "#3D2817",
        "color_b": "#D97706",
        "accent":  "#FBBF24",
        "tags": ["Análise", "GUT", "Insights"],
        "requires_auth": True,
    },
]

SECTORS_CONTROLADORIA = [
    {
        "key": "programacao_corte",
        "title": "Programação de Corte",
        "subtitle": "Planejamento — ordens e sequenciamento",
        "description": (
            "Gestão das ordens de programação de corte com sequenciamento por prioridade, "
            "volume planejado, datas e status de execução por setor."
        ),
        "icon": "📋",
        "page_path": "pages/4_Programacao_Corte.py",
        "color_a": "#2D1B69",
        "color_b": "#7C3AED",
        "accent":  "#A78BFA",
        "tags": ["Programação", "Corte", "Planejamento"],
        "requires_auth": True,
        "coming_soon": True,
    },
    {
        "key": "enderecamento_corte",
        "title": "Endereçamento de Corte",
        "subtitle": "Operação — distribuição por estação",
        "description": (
            "Controle do endereçamento das ordens de corte às estações de trabalho, "
            "com visibilidade de ocupação, balanceamento e rastreabilidade por OP."
        ),
        "icon": "📍",
        "page_path": "pages/5_Enderecamento_Corte.py",
        "color_a": "#3D1F00",
        "color_b": "#C2600A",
        "accent":  "#F59E0B",
        "tags": ["Endereçamento", "Corte", "Estações"],
        "requires_auth": True,
        "coming_soon": True,
    },
    {
        "key": "carteira_pedidos",
        "title": "Carteira de Pedidos",
        "subtitle": "Comercial — pedidos em aberto",
        "description": (
            "Visão consolidada da carteira de pedidos em aberto com prazos, "
            "clientes, volumes, situação de atendimento e evolução do backlog."
        ),
        "icon": "📂",
        "page_path": "pages/6_Carteira_Pedidos.py",
        "color_a": "#064E3B",
        "color_b": "#047857",
        "accent":  "#34D399",
        "tags": ["Pedidos", "Comercial", "Backlog"],
        "requires_auth": True,
        "coming_soon": True,
    },
]
