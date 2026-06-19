"""
Central de Atualizações — adicione novos itens no topo da lista.
Campos obrigatórios: date, tag, title, description
tag: "novo" | "melhoria" | "correção"
"""

CHANGELOG = [
    {
        "date": "19/06/2026",
        "tag": "novo",
        "title": "Histórico de Dados — Banco SQLite local",
        "description": (
            "Banco de dados SQLite (data/zanattex.db) criado para backup permanente de "
            "toda produção, corte, cargas e programação. Atualizado automaticamente a cada "
            "carregamento de qualquer dashboard. Página 'Histórico de Dados' (admin only) "
            "permite consultar por período, visualizar gráficos e exportar CSV."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "novo",
        "title": "Metas configuráveis via interface",
        "description": (
            "Admin pode editar as metas de facções diretamente pelo sidebar da página "
            "'Produção Facções', sem precisar alterar o código. As metas são salvas em "
            "data/metas_faccoes.json. Botão 'Resetar' volta ao padrão do settings.py."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "novo",
        "title": "Anotações nos gráficos",
        "description": (
            "Admin pode marcar datas especiais (feriados, greves, paradas) diretamente "
            "nos gráficos de produção diária e burn-up da página Facções. Linhas verticais "
            "coloridas com texto aparecem automaticamente nos gráficos do período selecionado."
        ),
    },
    {
        "date": "18/06/2026",
        "tag": "melhoria",
        "title": "Home — Análise de Metas e Faturamento bloqueados para Admin",
        "description": (
            "Os cards 'Análise de Metas / Previsão de Custos' e 'Análise de Faturamento' "
            "agora exigem senha de Administrador para acesso. Usuários com senha comum veem "
            "o badge '🔒 ADMIN' com aviso de manutenção e botão desabilitado. "
            "Admin pode acessar normalmente; os cards ficam com badge 🔒 ADMIN + aviso "
            "de que ainda há ajustes em andamento."
        ),
    },
    {
        "date": "18/06/2026",
        "tag": "correção",
        "title": "Produção Geral — Meta Período calculada por dias com produção por (Facção, Produto)",
        "description": (
            "Corrigido cálculo de 'Meta Período' na tabela Por Facção: antes usava todos os dias "
            "úteis do mês agrupados apenas por (Ano, Mês), fazendo todas as facções receberem "
            "os mesmos N dias independente de quanto produziram. Agora agrupa por "
            "(Facção, Produto, Ano, Mês) e filtra Quantidade > 0, alinhando a Meta Período "
            "exatamente com os Dias exibidos na tabela (ex: 11 dias × 1.000 = 11.000, não 15.000)."
        ),
    },
    {
        "date": "18/06/2026",
        "tag": "melhoria",
        "title": "Facções Externas — MANTA MAGICA → MICRO 180G (MAGICA)",
        "description": (
            "Produto 'MANTA MAGICA' agora exibe como 'MICRO 180G (MAGICA)' na página "
            "Produção Facções Externas, diferenciando-o do produto 'COBERTOR 180G' normal. "
            "Meta separada adicionada em METAS_FACCOES para o novo nome — ajuste o valor "
            "em config/settings.py se a meta da Manta Mágica for diferente da COBERTOR 180G."
        ),
    },
    {
        "date": "18/06/2026",
        "tag": "melhoria",
        "title": "Produção Geral — meta calculada pelos dias com produção",
        "description": (
            "Alterada a lógica de cálculo de 'Dias' e 'Meta Período' no tab Por Facção: "
            "antes contava todos os dias úteis do intervalo; agora conta apenas os dias onde "
            "houve produção > 0. Isso beneficia produtos com ciclo irregular (ex: JOGOS, "
            "JOGO DUPLO) que não produzem diariamente, evitando que o atingimento seja "
            "penalizado por dias de pausa que fazem parte do processo natural de produção."
        ),
    },
    {
        "date": "18/06/2026",
        "tag": "correção",
        "title": "Produção Geral — células mescladas na coluna FACÇÃO",
        "description": (
            "Corrigido bug em _parse_block: quando a coluna FACÇÃO usava células mescladas "
            "no Google Sheets, o pandas lia NaN em todas as linhas exceto a primeira do grupo. "
            "O parser pulava essas linhas, deixando de contar toda a produção das linhas "
            "subsequentes da mesma facção (ex: VANIA CONFEÇÕES tinha 6 linhas de MANTA mas "
            "o dashboard registrava apenas 1). Agora o valor da célula anterior é herdado "
            "quando a célula FACCAO está vazia, replicando o comportamento visual do Sheets."
        ),
    },
    {
        "date": "18/06/2026",
        "tag": "melhoria",
        "title": "Produção Geral — expander de conferência diária por facção",
        "description": (
            "Adicionado painel 'Conferência diária por Facção' (expansível) no tab 'Por Facção'. "
            "Permite selecionar uma facção e ver a produção dia a dia por produto em forma de pivot, "
            "facilitando a comparação direta com os valores da planilha e a identificação de "
            "divergências causadas por múltiplas linhas do mesmo produto na planilha."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "novo",
        "title": "Relatório PDF — Carteira de Pedidos",
        "description": (
            "Botão 'Gerar Relatório PDF' adicionado ao dashboard de Carteira de Pedidos. "
            "O relatório segue o mesmo padrão ReportLab dos outros dashboards: capa navy, "
            "cabeçalho/rodapé com paginação. Conteúdo: KPIs executivos (valor total, peças, "
            "pedidos, clientes, ticket médio, SKUs), tabela por categoria, gráfico de evolução "
            "mensal com linha acumulada (barras verdes + linha roxa), pizza de categorias, "
            "ranking de clientes e top 15 produtos (barras horizontais), tabela resumo por "
            "cliente e conclusão automática do período."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "melhoria",
        "title": "Carteira de Pedidos — linha acumulada no gráfico mensal",
        "description": (
            "Adicionada linha de valor acumulado (roxa pontilhada) ao gráfico de evolução "
            "mensal da Carteira de Pedidos. A linha cresce até o total do KPI, deixando "
            "claro que a carteira completa é a soma de todos os meses, não apenas o mês corrente."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "novo",
        "title": "Dashboard Carteira de Pedidos (página 9)",
        "description": (
            "Novo dashboard 'Carteira de Pedidos' alimentado pela planilha do Google Sheets. "
            "KPIs: Valor Total, Total Peças, Pedidos Únicos, Clientes Ativos, Ticket Médio, Produtos Únicos. "
            "Gráficos: evolução mensal (barras + linha de peças), pizza por categoria, "
            "valor por cliente, valor por estado, composição cliente×categoria (stacked), "
            "volume+valor por tamanho (CASAL/QUEEN/KING…), evolução por categoria (area), "
            "mapa de calor cliente×mês, top 15 produtos. "
            "Filtros: ano, mês, cliente, categoria, tamanho, estado. "
            "Tabelas: resumo por cliente e detalhe de itens com busca livre."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "melhoria",
        "title": "PDFs de Corte — gráficos maiores e sem espremido lado a lado",
        "description": (
            "Nos relatórios PDF de Lençol, Arealva e Iacanga, os gráficos de distribuição "
            "(pizza de empresas e barras de prestadores/cores/tamanhos) estavam espremidos "
            "lado a lado ocupando meia página cada. Agora cada gráfico ocupa largura total "
            "(17 cm), com a pizza centralizada e os demais em linha única. "
            "Gráficos de produção diária também aumentados (largura 17 cm, altura 6,5)."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "novo",
        "title": "Previsão de Cargas — botão Gerar Relatório PDF",
        "description": (
            "Adicionado botão '📄 Gerar Relatório PDF' no dashboard de Previsão de Cargas. "
            "Gera PDF real via ReportLab (mesmo padrão dos relatórios de corte): capa navy, "
            "KPIs (Previsão, Realizado, Diferença, Aderência, Destinos, Ocorrências), "
            "tabela de resumo por mês com aderência % colorida, gráficos matplotlib "
            "(Previsão vs Realizado por mês + top destinos), tabela detalhada de registros, "
            "página de ocorrências (se houver canceladas/adiadas) e conclusão com status global."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "correção",
        "title": "PDF Produção Geral — Meta/Dia considera apenas facções com produção real",
        "description": (
            "A Meta/Dia no relatório PDF estava inflada porque incluía pares (Facção, Produto) "
            "com meta definida mas sem produção alguma no período. "
            "Agora filtra apenas os pares com Quantidade > 0 antes de somar as metas — "
            "assim a meta reflete só as facções que efetivamente estavam ativas. "
            "Aplicado nas duas seções do PDF: tabela 'Desempenho por Empresa' e KPIs individuais."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "correção",
        "title": "PDF Produção Geral — Meta/Dia corrigida para soma de todas as facções",
        "description": (
            "No relatório PDF da Produção Geral, a coluna 'Meta/Dia' exibia a média de uma "
            "linha só em vez da soma das metas de todas as facções da empresa. "
            "Agora calcula: para cada par (Facção, Produto) único, toma a meta diária média "
            "e soma tudo — refletindo o target real total da empresa por dia. "
            "Corrigido nas duas seções do PDF: tabela 'Desempenho por Empresa' e KPIs individuais."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "novo",
        "title": "Produção Facções e Controladoria — botão Gerar Relatório PDF",
        "description": (
            "Adicionado botão '📄 Gerar Relatório PDF' em dois dashboards: "
            "(1) Produção Facções — aba Mensal: KPIs do mês (produção, meta, %, ritmo) "
            "e tabela de progresso por produto/empresa com % da meta colorida. "
            "(2) Controladoria Programação de Corte: KPIs (OPs, concluídas, parciais, "
            "pendentes, aderência, peças) e tabela resumo por OP com eficiência e status. "
            "Ambos baixam HTML formatado para impressão (Ctrl+P → Salvar como PDF)."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "correção",
        "title": "Previsão de Cargas — Aderência calculada só sobre meses concluídos",
        "description": (
            "O KPI de Aderência Global agora considera apenas os meses que possuem "
            "REALIZADO > 0. Antes, meses futuros ou sem dados consolidados (ex.: MAIO e JUNHO) "
            "entravam no denominador, puxando o percentual para baixo artificialmente. "
            "Previsão Total e Realizado Total continuam mostrando todos os meses."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "novo",
        "title": "Corte Itaju — botão Gerar Relatório PDF",
        "description": (
            "Adicionado botão '📄 Gerar Relatório PDF' na tela do Corte Itaju. "
            "Ao clicar, baixa um arquivo HTML com KPIs, tabela de caseamento (Cima × Fundo × Fronha) "
            "e detalhe por OP — formatado com CSS para impressão. "
            "Basta abrir no navegador e usar Ctrl+P → Salvar como PDF."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "correção",
        "title": "Previsão de Cargas — PREVISTO incluindo Canceladas e célula mesclada JUNHO",
        "description": (
            "Filtro de status no sidebar agora inclui todas as categorias por padrão (Normal, Adiada, Cancelada). "
            "Antes, Canceladas eram excluídas da seleção padrão, causando PREVISTO menor que o da planilha. "
            "Corrigida também a detecção de cargos em células mescladas no JUNHO: "
            "linhas sem data/destino mas com valor na col[6] e seguidas por uma linha com data "
            "agora herdam a data/destino do cargo anterior. JUNHO PREVISTO: R$2.510.000 ✓."
        ),
    },
    {
        "date": "17/06/2026",
        "tag": "melhoria",
        "title": "Previsão de Cargas — renomeação de títulos (frete → faturamento)",
        "description": (
            "Títulos e rótulos do dashboard de Previsão de Cargas atualizados: "
            "'frete' substituído por 'faturamento' em todos os títulos de gráficos. "
            "Gráfico de destinos renomeado para 'Previsão por Cliente - Meses Concluídos'. "
            "Nomes internos de funções (ex.: _first_frete) não foram alterados."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "correção",
        "title": "Previsão de Cargas — PREVISTO e REALIZADO corrigidos",
        "description": (
            "Corrigida a lógica de cálculo do PREVISTO e REALIZADO mensais. "
            "PREVISTO agora é calculado somando os fretes individuais de cada cargo (valores diários), "
            "com detecção dinâmica da coluna do frete (col[6] para a maioria dos meses, col[7] para JANEIRO). "
            "REALIZADO passa a usar o valor de resumo oficial da planilha: linha 'GERAL' para JANEIRO "
            "(col[11]=3.377.274) e maior valor não-redondo >R$1M em cols 8-14 para os demais meses "
            "(FEVEREIRO=3.365.242, MARÇO=3.972.017, ABRIL=3.283.794). MAIO e JUNHO mostram 0 pois "
            "os dados ainda não foram consolidados na planilha."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "novo",
        "title": "Dashboard de Previsão de Cargas",
        "description": (
            "Novo dashboard analítico de logística com dados de JANEIRO a JUNHO/2026. "
            "Inclui KPIs globais (previsão, realizado, aderência %), previsão vs. realizado "
            "por mês e por destino, aderência por cliente, evolução semanal, análise de frota, "
            "timeline de cargas, análise de cancelamentos/adiamentos, heatmap por dia da semana "
            "e tabela detalhada com busca. Dados lidos diretamente do Google Sheets em tempo real."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "novo",
        "title": "Dashboard Itaju — Corte Ponto Palito Marcelino",
        "description": (
            "Novo dashboard completo para a unidade de Itaju (Corte Ponto Palito Marcelino). "
            "Inclui filtros de período e OP/Estação/Cor/Tamanho na sidebar, KPIs globais "
            "(Cima, Fundo, Fronha, dias, OPs), caseamento CIMA × FUNDO × FRONHA com tabela "
            "de divergências, gráficos de produção diária/por tamanho/por cor e tabela de "
            "detalhe por OP com saldo e status de caseamento."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "novo",
        "title": "Facções: integração Litex (Enfardamento)",
        "description": (
            "Dados de produção da Litex adicionados à Análise de Facções. A planilha de "
            "enfardamento usa colunas diferentes (EMPRESA, TOTAL DE PEÇAS) — integrado via "
            "col_map na configuração sem impactar as demais abas. Alias de produtos de "
            "lençol (LENCOL QE/ST/CS/KING → LENCOL AVULSO) também adicionados."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "melhoria",
        "title": "Facções: seletor de semana na aba Semanal",
        "description": (
            "A aba Semanal agora permite escolher qualquer semana disponível no histórico, "
            "em vez de exibir sempre a semana atual. O seletor usa os dados reais "
            "(segunda a sexta) e o 'ritmo' da semana corrente considera apenas os dias já passados."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "melhoria",
        "title": "Controle de Corte: card Itaju na seleção de regiões",
        "description": (
            "Adicionado card de Itaju (Ponto Palito Marcelino) na tela de seleção de regiões "
            "do Controle de Corte, ao lado de Arealva e Iacanga."
        ),
    },
    {
        "date": "16/06/2026",
        "tag": "melhoria",
        "title": "Produção Geral: card de Análise de Facções na seleção 'Por Cliente'",
        "description": (
            "Substituído o card de Relatório Semanal pelo card de Análise de Facções na "
            "tela de seleção 'Por Cliente'. O card de Dashboard de Produção foi mantido. "
            "A Análise de Facções foi removida da tela inicial pois já é acessível via "
            "Análise de Produção."
        ),
    },
    {
        "date": "15/06/2026",
        "tag": "novo",
        "title": "Facções: nova aba 'Por Produto' e gráfico de burn-up",
        "description": (
            "Adicionada a aba 'Por Produto' com ranking de produção, mix (donut), "
            "treemap produto→empresa, atingimento da meta por produto e evolução "
            "diária dos principais produtos. A aba Mensal ganhou um gráfico de "
            "acumulado vs meta (burn-up) para ver se o ritmo cobre a meta do mês."
        ),
    },
    {
        "date": "15/06/2026",
        "tag": "melhoria",
        "title": "Facções: equivalências de nomes de produto e cliente",
        "description": (
            "Produtos e clientes que aparecem com nomes diferentes mas são a mesma "
            "coisa agora são unificados no cruzamento com metas: MANTA MÁGICA = "
            "COBERTOR 180G (é 180g); NC INDÚSTRIA / NIAZI = NIAZITTEX; OUTLET "
            "PRENSADO = MANTA PRENSADA; OUTLET C/CINTA = MANTA C/CINTA."
        ),
    },
    {
        "date": "15/06/2026",
        "tag": "correção",
        "title": "Facções: download por GID e quarterizados como facção",
        "description": (
            "As abas eram baixadas por nome via gviz (?sheet=), que devolvia a aba "
            "errada quando a pedida estava vazia/oculta — produção dos quarterizados "
            "aparecia trocada em PREVITTEX FILIAL. Agora cada aba é baixada pelo GID "
            "(estável). Além disso, cada prestador da aba QUARTERIZADAS virou uma "
            "facção própria, e GGTTEX foi separada em Rute e Cortina."
        ),
    },
    {
        "date": "15/06/2026",
        "tag": "correção",
        "title": "Facções: compatibilidade com pandas 3.0 (Styler.map)",
        "description": (
            "A página de Facções usava Styler.applymap, removido no pandas 3.0, "
            "causando AttributeError ao abrir a aba Mensal. Trocado por Styler.map. "
            "Também registrado o card 'Análise de Facções' na home (config/sectors.py) — "
            "antes a página existia mas não aparecia no menu de cards."
        ),
    },
    {
        "date": "15/06/2026",
        "tag": "novo",
        "title": "Dashboard de Produção Facções Externas (página 5)",
        "description": (
            "Nova página 5_Producao_Faccoes.py com análise diária, semanal e mensal "
            "da nova planilha de facções externas (Google Sheets com uma aba por facção). "
            "Abas suportadas: QUARTERIZADAS, GGTTEX (RUTE), GGTTEX (CORTINA), ZANATTA, "
            "PREVITTEX MATRIZ, PREVITTEX FILIAL, MEGA BARIRI, MEGA PREVEN. "
            "Metas por (produto, cliente, facção) com meta diária calculada dinamicamente "
            "(meta_mes / dias_úteis_do_mês). Tabela de progresso com coloração por % atingida. "
            "Inclui: utils/faccao_loader.py e cache_manager.get_raw_sheet()."
        ),
    },
    {
        "date": "11/06/2026",
        "tag": "correção",
        "title": "Programação de Corte: abreviações de tamanho reconhecidas no lençol (CS, ST, QE)",
        "description": (
            "A coluna CATEGORIA do lençol usa abreviações (CS=Casal, ST=Solteiro, QE=Queen) "
            "em vez do nome completo. O matching ignorava essas abreviações e caía no "
            "SequenceMatcher, que não distinguia bem CASAL de SOLTEIRO em JOGO SIMPLES. "
            "Adicionado _TAM_ALIAS no _tokens_prod: CS→CASAL, ST→SOLTEIRO, QE→QUEEN, KG→KING."
        ),
    },
    {
        "date": "11/06/2026",
        "tag": "correção",
        "title": "Programação de Corte: JOGO SIMPLES não somado com JOGO DE CAMA (DUPLO)",
        "description": (
            "Cortes de 'JOGO SIMPLES' (lençol + fronhas) do lençol estavam sendo atribuídos "
            "às linhas de 'JOGO DE CAMA' (duplo) porque ambos têm token de tamanho. "
            "Corrigido em três frentes: (1) MATERIAL do lençol concatena CATEGORIA + TECIDO/PRODUTO; "
            "(2) palavras-bloqueio expandidas: FUNDO, SIMPLES, SIPLES (typo comum na planilha) "
            "e LENCOL ('JOGO LENÇOL + FRONHAS' nunca aparece como 'JOGO DE CAMA' na programação). "
            "Se qualquer uma dessas palavras está no corte mas não na programação → score 0."
        ),
    },
    {
        "date": "11/06/2026",
        "tag": "correção",
        "title": "Programação de Corte: FUNDO não contabilizado no total de JOGO cortado",
        "description": (
            "O Giattex registra cortes de JOGO e FUNDO separadamente com a mesma OP. "
            "Como ambos têm token de tamanho (SOLTEIRO/CASAL/QUEEN), o matching atribuía "
            "os cortes de FUNDO às linhas de JOGO da programação, inflando o QNT_CORTADA. "
            "Corrigido: no scoring do matching, se o material de corte contém 'FUNDO' mas "
            "a linha da programação não contém, score = 0 — evitando a atribuição indevida."
        ),
    },
    {
        "date": "11/06/2026",
        "tag": "correção",
        "title": "Programação de Corte: corte zerado para OPs que aparecem em múltiplas semanas",
        "description": (
            "OPs que existiam em SEMANA 22 e SEMANA 23 da programação eram contadas como "
            "'múltiplos produtos' pelo groupby que usava apenas _CHAVE (sem SEMANA). "
            "Isso acionava o algoritmo winner-takes-all, que atribuía todos os cortes à "
            "linha da primeira semana — deixando a linha da semana atual com QNT_CORTADA=0. "
            "Corrigido: n_linhas_op, _op_to_positions e _assignment agora usam a chave "
            "(OP, SEMANA), tratando cada semana de forma independente. O groupby de "
            "QNT_CORTADA_OP também foi ajustado para somar por (CHAVE, SEMANA)."
        ),
    },
    {
        "date": "11/06/2026",
        "tag": "correção",
        "title": "Programação de Corte: matching multi-produto por token de tamanho e peças",
        "description": (
            "O matching anterior (SequenceMatcher sobre a string inteira) não diferenciava "
            "corretamente CASAL, QUEEN e SOLTEIRO porque as descrições são quase idênticas — "
            "a diferença de ratio entre o produto certo e os errados era < 5%, causando "
            "todos ficarem 'Concluído'. Agora o algoritmo extrai tokens discriminantes de "
            "cada texto: tamanho (CASAL/QUEEN/SOLTEIRO/KING) e número de peças (4P/3P). "
            "Quando ambos os lados têm token de tamanho, o tamanho deve coincidir exatamente; "
            "n° de peças dá um bônus extra. Cortes sem coincidência de tamanho recebem score 0 "
            "e ficam 'Pendente'. Textos sem token de tamanho continuam usando similaridade geral. "
            "Correção adicional: se o matching por token não encontrar nenhuma correspondência "
            "(ex: TECIDO do lençol sem token de tamanho reconhecível), o OP não entra no "
            "mapa de atribuição e cai no fallback de total da OP — evitando zeros indevidos."
        ),
    },
    {
        "date": "10/06/2026",
        "tag": "correção",
        "title": "Programação de Corte: status por produto quando a OP tem múltiplos itens",
        "description": (
            "Quando uma mesma OP tinha vários produtos programados (ex: CASAL, QUEEN e "
            "SOLTEIRO na OP 60790), o dashboard somava as quantidades e comparava com o "
            "total cortado — fazendo todos ficarem 'Parcial' mesmo que apenas um produto "
            "tivesse sido cortado. Agora, OPs com múltiplos produtos usam matching por "
            "similaridade de texto (DESCRIÇÃO DO PRODUTO × MATERIAL do corte) para "
            "atribuir a quantidade cortada a cada linha individualmente. "
            "OPs com apenas 1 produto mantêm o comportamento anterior."
        ),
    },
    {
        "date": "10/06/2026",
        "tag": "correção",
        "title": "Datas das planilhas internas: parsing MDY e exibição DD/MM/YYYY corrigidos",
        "description": (
            "Duas correções na aba Colaboradores Internos (LITTEX, GGTTEX Jogos, Fronha, Cortina): "
            "1) As planilhas usam locale US (MM/DD/AA). Quando todos os dias do mês são ≤ 12, "
            "o detector de formato não conseguia distinguir MDY de DMY e caía no padrão "
            "brasileiro — invertendo dia e mês. Corrigido adicionando date_order='MDY' por "
            "planilha em PRODUCAO_INTERNO_SHEETS e passando esse hint para parse_date_series. "
            "2) Os filtros de data exibiam no formato YYYY/MM/DD (padrão Streamlit). "
            "Corrigido adicionando format='DD/MM/YYYY' nos date_input de De/Até."
        ),
    },
    {
        "date": "05/06/2026",
        "tag": "novo",
        "title": "Relatório Semanal: aba 'Por Cliente' com análise de metas",
        "description": (
            "Adicionada aba '🏢 Por Cliente' no Relatório Semanal com comparativo "
            "Meta Semana × Realizado para cada empresa (NC Industria, Burdays, Andreza, "
            "Camesa, Decor, Sultan, Marcelino, Seven). Indicadores visuais 🟢🟡🔴 mostram "
            "atingimento da meta. Fábricas sem dados ainda (Mega Bariri, Previttex, Mega Preven) "
            "aparecem como 'Aguardando'. As metas foram extraídas da tabela de referência "
            "semanal/mensal por produto e fábrica."
        ),
    },
    {
        "date": "02/06/2026",
        "tag": "correção",
        "title": "Colaboradores Internos: nomes duplicados por acento/espaço unificados",
        "description": (
            "Nomes de colaboradores que apareciam duplicados por diferença de caixa no acento "
            "(ex.: 'LUÊNIA' com Ê maiúsculo vs 'LUêNIA' com ê minúsculo) ou por espaços duplos "
            "agora são canonicalizados no carregamento (colapsa espaços + UPPER). Isso unifica "
            "a produção da pessoa num único registro em todos os gráficos e rankings das 4 "
            "unidades internas (Littex, Jogo, Fronha, Cortina)."
        ),
    },
    {
        "date": "02/06/2026",
        "tag": "novo",
        "title": "Littex (Colaboradores Internos): análise Setor × Colaborador (setor como função)",
        "description": (
            "Nas unidades sem coluna de função dedicada (Littex e Cortina), o SETOR passa a "
            "funcionar como a 'função' do colaborador. A seção '🏭 Produção por Setor' ganhou "
            "duas análises novas: '🧩 Mix Setor × Colaborador' (barras empilhadas mostrando os "
            "setores em que cada colaborador atuou) e '⭐ Setor Principal por Colaborador' "
            "(tabela com setor principal, nº de setores e total por colaborador). Aparece apenas "
            "quando a unidade tem 2+ setores e não possui coluna de função própria — assim "
            "Jogo e Fronha, que já têm o mix por função, não duplicam a análise."
        ),
    },
    {
        "date": "02/06/2026",
        "tag": "novo",
        "title": "Jogo (Colaboradores Internos): análise por Função e Tamanho separados",
        "description": (
            "A coluna DESCRIÇÃO da planilha GGTTEX Jogos continha a função misturada ao "
            "tamanho costurado. A extração agora separa os dois: para costureiras (SETOR = "
            "COSTURA RETA / GALONEIRA / CANTO), FUNCAO = tipo de costura e TAMANHO = tamanho "
            "da peça (CASAL, SOLTEIRO, QUEEN, KING); para a MESA, FUNCAO = atividade "
            "(DOBRA E EMPAPELA, DOBRA FUNDO, CASEADO, EMBALAGEM, etc.) e TAMANHO fica vazio. "
            "O dashboard 'Por Colaborador → GGTTEX Jogos' ganhou três novas seções: "
            "'📐 Produção por Tamanho (Costura)' com gráfico de barras por tamanho, "
            "'🧵 Mix Tamanho × Costureira' com barras empilhadas e "
            "'📋 Resumo Costureira × Tamanho' com tabela pivot. "
            "A análise por Função já existente agora exibe os tipos reais (COSTURA RETA, "
            "COSTURA GALONEIRA, COSTURA CANTO, DOBRA E EMPAPELA, etc.) em vez dos tamanhos. "
            "Corrigido também bug de detecção de coluna: 'RETORNO PRODUTO MANUFATURADO...' "
            "era identificada erroneamente como coluna de produto; agora DESCRIÇÃO tem "
            "prioridade na busca."
        ),
    },
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
