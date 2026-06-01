"""
Central de Atualizações — adicione novos itens no topo da lista.
Campos obrigatórios: date, tag, title, description
tag: "novo" | "melhoria" | "correção"
"""

CHANGELOG = [
    {
        "date": "01/06/2026",
        "tag": "melhoria",
        "title": "Lençol: tabela de OPs enriquecida com Jogo Duplo, Fundo, Diferença e status de caseamento",
        "description": (
            "A tabela 'Resumo por OP' na aba de OPs do dashboard Arealva Lençol agora inclui "
            "as colunas Jogo Duplo, Fundo, Diferença e Casea para cada OP. OPs sem corte de fundo "
            "exibem '—' nessas colunas, explicando por que não aparecem na seção de caseamento abaixo. "
            "OPs com fundo mostram a quantidade de jogos duplos, fundos, a diferença líquida "
            "(FUNDO − JOGO) e o ícone de status (✅ caseado / 🔴 faltam fundos / 🟠 sobram fundos). "
            "A coluna 'Peças' continua exibindo o total bruto (jogo + fundo + outros) com legenda "
            "explicativa abaixo da tabela. A seção de Caseamento abaixo da tabela é calculada uma "
            "única vez e reutilizada, eliminando computação duplicada."
        ),
    },
    {
        "date": "01/06/2026",
        "tag": "novo",
        "title": "Lençol: caseamento Jogo Duplo × Fundo (jogo vs fundo por OP e tamanho)",
        "description": (
            "Cada jogo duplo precisa de um fundo correspondente (corte à parte). Agora o "
            "dashboard de Lençol separa os fundos do total: o KPI principal passa a mostrar "
            "'Peças (s/ fundo)' e os fundos aparecem em destaque próprio. Nova seção "
            "'🔄 Caseamento Jogo Duplo × Fundo' na Visão Geral mostra jogos duplos, fundos, "
            "a diferença líquida (jogo − fundo) e quantas OPs divergem — com tabela das "
            "divergências por OP e tamanho (🔴 faltam fundos / 🟠 sobram fundos). Na aba de OPs, "
            "tabela de caseamento por OP+tamanho com filtro de divergências, e ao selecionar "
            "uma OP, o caseamento específico dela. O relatório PDF de fechamento ganhou a seção "
            "de caseamento com resumo e tabela colorida. O caseamento considera apenas OPs que "
            "tiveram corte de fundo (evita falsos alarmes nas OPs que não usam fundo) e casa "
            "JOGO DUPLO ↔ FUNDO por tamanho (CS/QE/ST/KING); jogo simples não entra. "
            "A identificação de fundo usa CATEGORIA + TECIDO com prioridade ao TECIDO: na "
            "prática a categoria frequentemente diz 'JOGO DUPLO CS' enquanto é o tecido que "
            "revela 'FUNDO CASAL 4PÇS' (e vice-versa, categoria 'FUNDO JOGO ST' com tecido "
            "'JOGO SOLTEIRO...'). O universo é restrito aos jogos de cama (categoria menciona "
            "JOGO), deixando porta-travesseiro, lençol avulso e fronha de fora do caseamento. "
            "A diferença é o saldo de fundos (FUNDO − JOGO): negativo = faltam fundos, "
            "positivo = sobram (ex.: jogo 6.391 vs fundo 6.290 → −101)."
        ),
    },
    {
        "date": "01/06/2026",
        "tag": "novo",
        "title": "Relatórios PDF de fechamento de mês em todos os dashboards de corte e produção",
        "description": (
            "Adicionado botão '📄 Gerar Relatório PDF de Fechamento' nos dashboards de "
            "Arealva Manta, Iacanga Manta, Arealva Lençol e Produção Geral. "
            "Cada relatório inclui: capa com fundo navy e período, resumo executivo com "
            "KPIs em destaque (total de peças, dias trabalhados, média/dia, % meta), "
            "tabela de desempenho por estação/empresa com status colorido (✔ META / ⚠ PERTO / ✘ ABAIXO), "
            "gráfico de produção diária com linha de meta e tendência, tabela detalhada diária, "
            "análise de distribuição por estação/cor/empresa, análise de tamanhos (Iacanga e Arealva), "
            "detalhe por OP e conclusão narrativa do período. "
            "Novo módulo utils/pdf_report.py usa ReportLab (layout) + Matplotlib (gráficos) — "
            "sem kaleido, 100% offline. Geração on-demand via session_state, com botão 🗑️ para limpar e "
            "regenerar com novos filtros."
        ),
    },
    {
        "date": "29/05/2026",
        "tag": "novo",
        "title": "Análise de Produção: hub Por Cliente / Por Colaborador (Interno com 4 guias)",
        "description": (
            "A Análise de Produção agora abre um seletor de cards (mesmo estilo do Corte) com "
            "duas visões: (1) Por Cliente — o dashboard multi-empresa existente; (2) Por Colaborador "
            "— dividido entre Interno e Externo. O painel Interno traz 4 guias (LITTEX, GGTTEX Jogos, "
            "GGTTEX Fronha e GGTTEX Cortina), cada uma com filtro de período e de colaborador, KPIs e "
            "gráfico de Top Colaboradores. Ao selecionar um ou mais colaboradores, o ranking dá lugar a "
            "'Quantidade por Dia' e a um gráfico de Consistência (Regularidade = estabilidade da produção "
            "diária; Assiduidade = % de dias com produção). Unidades com coluna de função (ex: Fronha) "
            "ganham análise 'Produção por Função'. Novo loader padronizado (utils/producao_interno_loader.py) "
            "detecta as colunas por conteúdo — necessário porque essas planilhas trazem o título mesclado "
            "embutido no cabeçalho — e usa date_parser/cache_manager (datas M/D corrigidas, sem inversão). "
            "O card de Produção saiu de 'Em manutenção'."
        ),
    },
    {
        "date": "28/05/2026",
        "tag": "correção",
        "title": "Lençol: erro 'Colunas faltando: EMPRESA' por cabeçalho instável do Google",
        "description": (
            "O Lençol falhava intermitentemente com 'Colunas faltando: [EMPRESA]'. Causa: a "
            "planilha tem título mesclado na linha 1 e os cabeçalhos reais na linha 3 — o "
            "endpoint gviz/tq do Google ADIVINHA qual é a linha de cabeçalho e essa adivinhação "
            "varia entre downloads (às vezes junta o título na coluna A, deslocando os nomes). "
            "Como o loader mapeava colunas pelo nome, quebrava quando o nome vinha diferente. "
            "Correção: o loader agora lê a grade crua e DETECTA a linha de cabeçalho pelo conteúdo "
            "(procura a linha com PRESTADOR + OP), ignorando o palpite do Google. Também passou a "
            "reconhecer a coluna da empresa por 'EMPRESA'/'EMPESA' além do antigo 'DATA'. "
            "Imune à variação do CSV a cada download."
        ),
    },
    {
        "date": "28/05/2026",
        "tag": "melhoria",
        "title": "Padronização: OP prefixo-insensível + módulos únicos de data/cache/normalização",
        "description": (
            "Para impedir que os bugs recentes voltem em qualquer parte do projeto, as soluções "
            "foram centralizadas em módulos compartilhados e aplicadas em todas as páginas: "
            "(1) utils/normalize.py — normalize_op() ignora prefixos de OP (PROG, PGR, OP) e "
            "espaços, então 'PROG 82', 'PGR 10' e '82'/'10' casam automaticamente no cruzamento "
            "programação×corte (não precisa mais tirar prefixo na mão). A OP do modelo é o "
            "PED. CLIENTE; OP INTERNA só substitui quando não há PED. CLIENTE. "
            "(2) utils/date_parser.py é agora a ÚNICA forma de converter datas — aplicado também "
            "no Plano de Metas (lançamentos) e na Eficiência de Corte. "
            "(3) Removidos os parsers de data locais e duplicados (parse_date_safe, _parse_data_corte, "
            "lencol_parse_date) que faziam do jeito antigo e podiam ser reusados por engano. "
            "(4) Criado PADROES.md documentando as regras (cache, datas, OP, filtro de linhas) "
            "para todo desenvolvimento futuro."
        ),
    },
    {
        "date": "28/05/2026",
        "tag": "correção",
        "title": "Controladoria de Programação: OPs faltando e cortes do Lençol não cruzando",
        "description": (
            "Dois bugs na comparação previsto × realizado: "
            "(1) OPs SUMINDO — load_programacao() descartava toda linha sem PED. CLIENTE, "
            "mas ~88 linhas (22 OPs, ex: FATTEX) usam OP INTERNA / PED. INT como identificador. "
            "A programação caía de ~910 para 888 OPs e a semana 22 perdia 1 OP. Agora PED. CLIENTE "
            "vazio recebe fallback de OP INTERNA → PED. INT, recuperando todas as OPs (910 totais, "
            "semana 22 com 22). "
            "(2) CORTES DO LENÇOL NÃO CRUZAVAM — load_cortes() fazia parsing próprio e lia a coluna "
            "chamada 'DATA' do Lençol, que na verdade contém o nome da EMPRESA (a data real está "
            "noutra coluna). Com isso TODOS os cortes do Lençol ficavam com semana ISO nula e não "
            "casavam no join por (OP, semana) — o realizado do Lençol aparecia como zero. Agora "
            "load_cortes() usa o loader dedicado (lencol_loader_smart) para o Lençol, trazendo 767 "
            "registros com semanas corretas (1–22). Resultado: cortes do Lençol passam a casar com a "
            "programação (ex: OPs 81 e 82 na semana 22)."
        ),
    },
    {
        "date": "28/05/2026",
        "tag": "correção",
        "title": "Datas invertidas (dia/mês) e linhas de produção sumindo dos dashboards",
        "description": (
            "Dois bugs graves que faziam dados corretos não aparecerem: "
            "(1) DATAS INVERTIDAS — o Google Sheets exporta datas conforme o locale de cada planilha "
            "(Iacanga em DD/MM/YY, Manta/Faturamento/Litex em MM/DD/YYYY). Os parsers antigos decidiam "
            "o formato valor-a-valor ou assumiam um formato fixo, invertendo dia/mês nas datas ambíguas. "
            "Efeito visível: Iacanga mostrava cortes até 'dezembro/2026' (12/05 lido como 5/dez) e o "
            "Litex/Niazitex na Produção Geral tinha 15 datas no mês errado. Criado utils/date_parser.py "
            "que detecta o formato olhando a COLUNA inteira (se algum valor tem 1º componente >12 a coluna "
            "é DD/MM; se algum tem 2º >12 é MM/DD) e aplica o mesmo formato a todos — determinístico e "
            "consistente. Aplicado em: Faturados, Produção Geral (Litex), Controle de Corte (Manta+Iacanga), "
            "Controladoria (semana ISO) e loader do Lençol. "
            "(2) LINHAS SUMINDO NO LENÇOL — o loader descartava toda linha sem número de OP, mas cortes "
            "reais às vezes não têm OP preenchida. Resultado: ~190 linhas de produção válidas eram perdidas "
            "(ex: corte de 28/05 do prestador JAPA/FABRICIO, 4005 peças CORTTEX, não aparecia). Agora OP "
            "vazia vira 'SEM OP' e só são removidas linhas sem nenhum dado real (sem quantidade, sem "
            "prestador e sem categoria — lixo/totais do fim da planilha). Lençol passou de 603 para 793 "
            "linhas válidas. Também corrigido _col() em eficiencia_corte.py para casar nomes de coluna por "
            "substring (a planilha de Lençol Arealva tem CLIENTE embutido num cabeçalho longo)."
        ),
    },
    {
        "date": "28/05/2026",
        "tag": "melhoria",
        "title": "Cache em disco — fim dos timeouts e dados inconsistentes entre dashboards",
        "description": (
            "Criado utils/cache_manager.py: ponto único de download para todas as planilhas Google Sheets. "
            "Fluxo: (1) verifica cache em disco cache/sheets/<id>_<gid>.csv; se fresco (< TTL), retorna sem tocar a rede; "
            "(2) se obsoleto, tenta download com retry e backoff; (3) se o Sheets der timeout ou erro, usa o cache anterior "
            "sem derrubar o dashboard. Todos os loaders (pages 1, 2, 3, 4, 7, eficiencia_corte, lencol_loader_smart, "
            "sheets_loader) foram atualizados para usar o cache_manager. Resultado: "
            "páginas que precisam das mesmas planilhas (ex: Manta/Iacanga/Lençol nas páginas 3 e 4) agora compartilham "
            "o mesmo arquivo em disco — sem downloads duplicados, sem versões diferentes dos dados. "
            "Botões 'Atualizar Dados' também limpam o cache em disco para forçar refresh completo. "
            "Leitura do cache: ~0.015s vs ~1.6s de download direto (100x mais rápido)."
        ),
    },
    {
        "date": "27/05/2026",
        "tag": "correção",
        "title": "Relatório diário de corte — peças zeradas no e-mail",
        "description": (
            "O script relatorio_diario_corte.py enviava relatório com 0 peças em todos os setores "
            "por dois motivos: (1) _parse_datas() usava format='mixed' do pandas 2.0+, mas "
            "requirements_relatorio.txt não tinha versão mínima — se o ambiente instalasse pandas "
            "1.x, todas as datas viravam NaT e dropna() esvaziava o DataFrame silenciosamente. "
            "(2) df.columns.str.strip() preservava o case original dos cabeçalhos (ex: 'Data'), "
            "mas o acesso posterior era df['DATA'] — KeyError em qualquer planilha com headers "
            "não totalmente maiúsculos. Correções: pandas>=2.0.0 pinado em requirements_relatorio.txt; "
            "_parse_datas() reescrito com busca case-insensitive da coluna e try/except para "
            "fallback compatível com pandas < 2.0; df.columns.str.upper() adicionado nos loaders "
            "de Manta Arealva e Manta Iacanga."
        ),
    },
    {
        "date": "27/05/2026",
        "tag": "correção",
        "title": "Correção sistêmica de parsing de datas (DD/MM vs MM/DD)",
        "description": (
            "Datas exportadas pelo Google Sheets em formato M/D/YYYY (locale US) eram "
            "interpretadas como DD/MM, causando registros em meses errados — erro direto "
            "em totais financeiros de pagamento. "
            "Correção em dois níveis: (1) load_corte_lencol() migrado de CSV para XLSX: "
            "Excel armazena datas como seriais numéricos, pandas retorna datetime64 sem "
            "nenhum parsing de texto, eliminando a ambiguidade definitivamente. "
            "(2) lencol_parse_date() e _parse_data_corte() reescritos com desambiguação "
            "por tamanho de componente — se a > 12 é DD/MM, se b > 12 é MM/DD, ambos ≤ 12 "
            "adota pt-BR (DD/MM). Cobre 3_Controle_de_Corte.py e 4_Controladoria_Programacao.py."
        ),
    },
    {
        "date": "27/05/2026",
        "tag": "melhoria",
        "title": "Plano de Metas — Dicionário de Equivalência de Nomes",
        "description": (
            "Prestadores cujos nomes diferem levemente entre o plano de metas e as planilhas de "
            "produção agora são resolvidos automaticamente por similaridade ≥ 90% (difflib). "
            "Um expander '🔤 Equivalências de Nomes' exibe matches automáticos, mapeamentos manuais "
            "ativos e prestadores ainda sem resolução. Mapeamentos manuais permanentes podem ser "
            "adicionados em config/settings.py → NOME_EQUIVALENCIAS."
        ),
    },
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
