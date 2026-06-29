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
    },
    {
        "key": "producao",
        "title": "Análise de Produção",
        "subtitle": "Por Cliente e Por Colaborador",
        "description": (
            "Acompanhamento da produção em duas visões: Por Cliente (multi-empresa, "
            "metas e evolução) e Por Colaborador (internos por unidade — LITTEX e GGTTEX — "
            "com ranking, consistência e externos)."
        ),
        "icon": "🏭",
        "page_path": "pages/2_Producao_Geral.py",
        "color_a": "#0F4C5C",
        "color_b": "#4ECDC4",
        "accent":  "#FFA726",
        "tags": ["Produção", "Por Cliente", "Por Colaborador"],
        "requires_auth": True,
    },
    {
        "key": "previsao_cargas",
        "title": "Previsão de Cargas",
        "subtitle": "Logística · Previsão vs. Realizado",
        "description": (
            "Comparativo mensal previsão vs. realizado, aderência por destino, "
            "análise por origem e timeline de cargas."
        ),
        "icon": "🚛",
        "page_path": "pages/8_Previsao_Cargas.py",
        "color_a": "#1A2744",
        "color_b": "#2563EB",
        "accent":  "#FFA726",
        "tags": ["Logística", "Cargas", "Previsão vs. Realizado"],
        "requires_auth": True,
    },
    {
        "key": "metas_previsao",
        "title": "Análise de Metas / Previsão de Custos",
        "subtitle": "Progresso automático vs. metas e projeção",
        "description": (
            "Acompanhamento automático do plano de metas por prestador e unidade, "
            "com previsão de atingimento até o fim do mês e projeção de custos "
            "e receita baseada no rendimento diário real."
        ),
        "icon": "🎯",
        "page_path": "pages/7_Plano_de_Metas.py",
        "color_a": "#1A3A2A",
        "color_b": "#2A9D5C",
        "accent":  "#F4A261",
        "tags": ["Metas", "Previsão", "Custos"],
        "requires_auth": True,
        "admin_only": True,
        "maintenance": True,
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
        "admin_only": True,
        "maintenance": True,
    },
]

SECTORS_CONTROLADORIA = [
    {
        "key": "programacao_corte",
        "title": "Programação de Corte",
        "subtitle": "Análise — Planejado vs Realizado",
        "description": (
            "Dashboard que cruza a programação semanal de corte com o que foi "
            "realmente cortado. Monitora andamento por OP com status "
            "Pendente, Parcial e Concluído em tempo real."
        ),
        "icon": "📋",
        "page_path": "pages/4_Controladoria_Programacao.py",
        "color_a": "#2D1B69",
        "color_b": "#7C3AED",
        "accent":  "#A78BFA",
        "tags": ["Programação", "Corte", "Planejado vs Realizado"],
        "requires_auth": True,
    },
    
    {
        "key": "carteira_pedidos",
        "title": "Carteira de Pedidos",
        "subtitle": "Comercial — pedidos em aberto",
        "description": (
            "Visão consolidada da carteira de pedidos com análise por cliente, "
            "categoria, tamanho e região. KPIs, gráficos interativos e evolução mensal."
        ),
        "icon": "📦",
        "page_path": "pages/9_Carteira_de_Pedidos.py",
        "color_a": "#064E3B",
        "color_b": "#047857",
        "accent":  "#34D399",
        "tags": ["Pedidos", "Comercial", "Análise"],
        "requires_auth": True,
    },
    {
        "key": "relatorios",
        "title": "Relatórios",
        "subtitle": "Central de geração de PDFs",
        "description": (
            "Gere relatórios PDF completos de todos os módulos em um único lugar: "
            "Corte (Arealva, Lençol, Iacanga), Produção Geral, Facções, "
            "Previsão de Cargas, Carteira de Pedidos e Programação de Corte."
        ),
        "icon": "📄",
        "page_path": "pages/10_Relatorios.py",
        "color_a": "#1A2744",
        "color_b": "#2563EB",
        "accent":  "#60A5FA",
        "tags": ["PDF", "Relatórios", "Exportar"],
        "requires_auth": True,
    },
    {
        "key": "historico_db",
        "title": "Histórico de Dados",
        "subtitle": "Backup SQLite — todas as fontes",
        "description": (
            "Banco de dados local com backup permanente de toda produção, corte e cargas. "
            "Protege contra perda ou alteração das planilhas Google Sheets. "
            "Consulta por período, exportação CSV e status do banco."
        ),
        "icon": "🗄️",
        "page_path": "pages/6_Historico.py",
        "color_a": "#1E3A5F",
        "color_b": "#2D6A9F",
        "accent":  "#4DA6FF",
        "tags": ["Backup", "SQLite", "Histórico"],
        "requires_auth": True,
        "admin_only": True,
    },
]
