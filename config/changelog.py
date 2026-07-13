"""
Central de Atualizações — adicione novos itens no topo da lista.
Campos obrigatórios: date, tag, title, description
tag: "novo" | "melhoria" | "correção"
"""

CHANGELOG = [
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Resumo por OP sumia com cortes parciais em Controle de Programação",
        "description": (
            "utils/controle_op.py::_valido(): no pandas 3.x, Series.astype(str) não converte "
            "mais NaN em texto 'nan' (mantém NaN real) — sem fillna('') antes, células "
            "genuinamente vazias eram tratadas como 'válidas', deixando linhas quase em branco "
            "(só CLIENTE preenchido, sem OP/produto/qtd. programada) entrarem com _CHAVE = NaN. "
            "Essas linhas casavam com cortes reais e apareciam na aba Detalhe Completo como "
            "'Parcial' com peças cortadas, mas o groupby() do Resumo por OP descarta chaves NaN "
            "silenciosamente — por isso sumiam de lá (ex.: Semana 27, 3 linhas/~13.700 peças). "
            "Corrigido com fillna('') antes do astype(str). Afeta pages/4_Controladoria_"
            "Programacao.py, pages/10_Relatorios.py e pages/11_Controle_de_OP.py (todos usam "
            "essa mesma função). Reportado pelo usuário em 13/07/2026."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "novo",
        "title": "Linha \"Não alocado\" para Realizado sem previsão em Previsão de Cargas",
        "description": (
            "pages/8_Previsao_Cargas.py: confirmado com o usuário que os dias 02/07 a 05/07 de "
            "Julho/2026 não têm carga cadastrada em nenhum mês (só 01/07 estava previsto, dentro "
            "da última semana de Junho) — o painel diário já tinha Realizado lançado pra esses "
            "dias, mas sem nenhuma semana pra entrar. Antes esse valor era só descartado da quebra "
            "semanal (contava apenas no Realizado mensal do topo). Agora _parse_month gera um "
            "registro 'NAO_ALOCADO' por lançamento órfão, e a tabela 'Detalhamento por Semana' "
            "mostra uma linha à parte (ex.: '01/07 a 04/07 (sem previsão)') com esse Realizado — "
            "soma sempre bate com o mensal oficial (semanas normais + não alocado). Esse registro "
            "sintético foi excluído do gráfico de evolução semanal (quebraria a linha de tendência), "
            "dos filtros da sidebar, dos gráficos de frota/timeline/ocorrências e do cálculo de "
            "'dias cobertos' da projeção de fechamento do mês — aparece só na tabela de "
            "detalhamento e na listagem de registros."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Realizado semanal descartava cargas de frete zero em Previsão de Cargas",
        "description": (
            "pages/8_Previsao_Cargas.py: a tabela 'Detalhamento por Semana' filtrava Previsão E "
            "Realizado pelas mesmas cargas com VALOR_FRETE > 0. Isso descartava o Realizado de "
            "cargas de Armazenagem/frete subcontratado (frete = 0): o painel diário atribui o "
            "Realizado por (data, cliente) dividido entre todas as cargas daquele cliente no dia — "
            "quando uma delas tinha frete zero, a parte dela desaparecia da semana ao invés de ser "
            "só excluída do Previsto. Na semana 06/07-11/07 de Julho isso descontava R$ 44.986,70 "
            "(mostrava R$ 803.070 quando a planilha soma R$ 848.057 para o mesmo período — "
            "confirmado pelo usuário em 13/07/2026). Corrigido separando os dois agrupamentos: "
            "Previsão continua só com cargas de frete > 0, Realizado agora soma todas as cargas da "
            "semana."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Previsto da última semana inflado (frete vazando do painel diário)",
        "description": (
            "pages/8_Previsao_Cargas.py::_first_frete: a varredura de frete (cols 5-9) não parava "
            "antes da coluna-base do painel diário — em cargas com a própria célula de frete vazia "
            "(Armazenagem, ou 'FRETE GALICE'/frete subcontratado), continuava buscando e acabava "
            "lendo o Previsto de OUTRO cliente no painel diário do mesmo dia como se fosse o frete "
            "daquela carga. Na semana 06/07-11/07 de Julho isso inflou o Previsto de R$ 845.000 "
            "(valor real, que bate com o subtotal 'R$ 845.000,00' já calculado na própria planilha) "
            "para R$ 915.000 (R$ 70 mil vazados: R$ 40 mil do Previsto de SULTAN 06/07 + R$ 30 mil "
            "do Previsto de MARCELINO 10/07). Corrigido para a varredura nunca passar da "
            "coluna-base do painel diário (_find_painel_col). Reportado pelo usuário em 13/07/2026."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Realizado da última semana inflado em Previsão de Cargas",
        "description": (
            "pages/8_Previsao_Cargas.py: a semana 06/07-11/07 de Julho aparecia com 133% de "
            "aderência. Duas causas: (1) _extract_day_realized lia a linha 'TOTAL GERAL (01 A "
            "11/07)' do painel diário como se fosse mais um cliente, dobrando o total lido do "
            "painel — corrigido ignorando linhas com 'TOTAL'/'GERAL' no nome do cliente; (2) o "
            "fator de reconciliação semanal (linha ~755) escalava o Realizado casado até bater "
            "com o Realizado oficial do MÊS INTEIRO — como os dias 01/07 a 04/07 têm lançamento "
            "no painel diário mas nenhuma carga cadastrada na aba ainda, todo esse valor "
            "(~R$ 489 mil) caía inteiro na única semana existente. Corrigido para reconciliar "
            "apenas contra o painel diário DAS DATAS que já têm carga cadastrada — o Realizado "
            "mensal usado nos KPIs continua exato, só a quebra semanal deixou de ser inflada. "
            "Reportado pelo usuário em 13/07/2026."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Datas em mm/dd em dois gráficos de Produção Geral",
        "description": (
            "pages/2_Producao_Geral.py: os gráficos 'Evolução Diária — Top Produtos' (linha "
            "~1409, aba de facções) e '📈 Quantidade por Dia' (linha ~2060, dashboard de "
            "colaboradores) usavam a coluna DATA (datetime) direto no eixo x sem "
            "xaxis=dict(tickformat=\"%d/%m/%Y\") — diferente de todos os outros gráficos da "
            "página, que já tinham esse override. Sem ele, o Plotly aplica o formato automático "
            "de data (padrão mm/dd, estilo EUA). Corrigido adicionando o tickformat nos dois. "
            "Reportado pelo usuário em 13/07/2026."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Previsto mensal de Previsão de Cargas ignorava o valor oficial da linha 'GERAL'",
        "description": (
            "pages/8_Previsao_Cargas.py::_find_resumo_mensal (estratégia 2, linha com 'GERAL'): "
            "só lia o Realizado (col[GERAL+2]) e sempre zerava o Previsto, mesmo quando o valor "
            "oficial estava ao lado (col[GERAL+1]) — ex.: linha 'Total geral (01 a 11/07)' de "
            "Julho tinha Previsto R$ 905.000 na planilha, mas o dashboard mostrava R$ 915.000 "
            "porque caía no fallback de somar o frete individual de cada carga (aproximado, sem "
            "bater com o oficial). Corrigido para ler também col[GERAL+1] quando presente. Mesmo "
            "ajuste corrige Janeiro (linha 'GERAL janeiro'), que tinha o mesmo problema. "
            "Reportado pelo usuário em 13/07/2026."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "novo",
        "title": "Projeção de fechamento do mês atual em Previsão de Cargas",
        "description": (
            "pages/8_Previsao_Cargas.py: nova seção 'Projeção de Fechamento do Mês Atual' com "
            "4 KPIs (Previsto Lançado, Previsto Projetado, Aderência Base, Realizado Estimado). "
            "Cálculo: Previsto Projetado = Previsto lançado ÷ dias cobertos pelos lançamentos "
            "× dias totais do mês (run-rate); Realizado Estimado = Previsto Projetado × aderência "
            "média (Realizado/Previsto) dos 2 últimos meses fechados. 'Dias cobertos' usa o "
            "intervalo real entre a primeira e a última carga lançada no mês — não os dias "
            "corridos do calendário — porque a planilha é preenchida em blocos semanais; dividir "
            "por dias corridos diluía a projeção pela metade (ajustado após feedback do usuário "
            "13/07/2026). Também corrigido bug onde o Realizado do mês corrente ficava travado "
            "em zero quando a linha de resumo da planilha ainda não existia (fallback agora usa "
            "a soma do painel diário)."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Override manual do Realizado de Junho removido em Previsão de Cargas",
        "description": (
            "pages/8_Previsao_Cargas.py (REALIZADO_MENSAL_OVERRIDE): usuário preencheu os dias "
            "que faltavam na planilha de Junho/2026, então o valor hardcoded (4.124.995,84, "
            "adicionado em 10/07/2026 porque o lançamento diário estava incompleto) foi "
            "removido — Junho volta a ler o Realizado direto da linha de resumo da planilha "
            "(_find_resumo_mensal), igual todo mês fora desse dict. Maio continua com override "
            "(não foi mencionado como corrigido)."
        ),
    },
    {
        "date": "13/07/2026",
        "tag": "correção",
        "title": "Previsão de Cargas não reconhecia o mês atual sozinho",
        "description": (
            "Usuário perguntou por que julho não aparecia automaticamente em Previsão de "
            "Cargas. Causa: pages/8_Previsao_Cargas.py::MESES_DISPONIVEIS era uma lista fixa "
            "de tuplas (JANEIRO a JUNHO/2026) que precisava ser editada manualmente todo mês "
            "— o loop que baixa/parseia os dados (linha ~699) só processa os meses que estão "
            "nessa lista, então julho nunca era buscado, mesmo com dado disponível na "
            "planilha. Trocado por _meses_disponiveis(), que gera a lista de Janeiro/2026 até "
            "o mês corrente automaticamente (date.today()) — não precisa mais editar esse "
            "arquivo todo início de mês."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "novo",
        "title": "Central de Relatórios ganhou aba para Colaboradores Internos",
        "description": (
            "Faltava gerar PDF individual de produção para colaboradores internos "
            "(LITTEX/GGTTEX) na Central de Relatórios — só existia esse relatório "
            "no código (utils/pdf_report.py::gerar_pdf_colaborador), sem nenhuma tela "
            "que chamasse ele. Adicionada aba '👥 Colaboradores Internos' em "
            "pages/10_Relatorios.py: escolhe unidade (LITTEX/GGTTEX Jogos/Fronha/Cortina), "
            "colaborador e período, e gera o mesmo PDF (produção por setor, por empresa e "
            "detalhamento diário) que já existia no dashboard 'Por Colaborador → Interno'. "
            "Testado ao vivo gerando o PDF de um colaborador da LITTEX."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "correção",
        "title": "Tela de Produção Interna quebrava com TypeError ao listar colaboradores",
        "description": (
            "Erro 'not supported between instances of float and str' ao abrir a aba "
            "GGTTEX Cortina em Produção Geral → Colaboradores Internos. Causa: no pandas 3.x, "
            "'.astype(str)' deixou de converter células vazias (NaN) em string 'nan' — o valor "
            "ficava como float mesmo depois da limpeza, escapando do filtro de linhas vazias e "
            "quebrando o sorted() da lista de colaboradores. Corrigido em "
            "utils/producao_interno_loader.py (coluna COLABORADOR e _limpar_texto) e no mesmo "
            "padrão em utils/faccao_loader.py (PRODUTO, CLIENTE, PRESTADOR, DATA), adicionando "
            "fillna('') antes do astype(str). Validado recarregando as 4 unidades internas e as "
            "abas de Facções: todas as colunas de texto agora só têm string, sem mistura de tipos."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "correção",
        "title": "Nome do produto às vezes vinha como código na tabela de OPs",
        "description": (
            "Usuário notou, na tabela 'Todas as OPs' do Controle de OP, produtos aparecendo "
            "como o código (ex.: '700075-2021-25', '1.12636.02.9999') ou como o próprio número "
            "da OP, em vez do nome. Causa: em várias linhas da planilha de Programação a coluna "
            "PRODUTO guarda só o código — quem tem o nome legível é DESCRIÇÃO DO PRODUTO, e "
            "utils/controle_op.py::enriquecer() usava sempre a coluna PRODUTO crua na saída. "
            "Corrigido pra preferir DESCRIÇÃO DO PRODUTO sempre que ela existir (só cai pra "
            "PRODUTO quando a descrição está vazia) — não muda o matching multi-produto interno "
            "(já usava essa mesma preferência) nem os números de status/quantidade, só o nome "
            "exibido. Testado com dados reais: 120 OPs com código no lugar do nome, agora 0."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "melhoria",
        "title": "Controle de OP com visual mais rico (rosca de status, gauge, top clientes, badges)",
        "description": (
            "Usuário achou o Controle de OP simples demais — só números crus nos KPIs e "
            "tabelas sem cor. pages/11_Controle_de_OP.py: adicionado gráfico de rosca "
            "'Distribuição por Status' (Concluído/Parcial/Pendente/Fora da Programação, com o "
            "total de OPs no centro), gauge de 'Aderência Geral' e gráfico de barras 'Top 10 "
            "Clientes por Peças Cortadas', todos logo abaixo dos KPIs. As duas tabelas "
            "(Detalhamento e Todas as OPs) agora coloriram a coluna Status com a cor de cada "
            "status (fundo + texto, via pandas Styler) e emoji (✅🟡🔴🟣) na frente do texto. "
            "KPIs ganharam os mesmos emojis. Testado: Styler renderiza sem erro com dados "
            "reais (1397 linhas) e o app sobe normal."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "correção",
        "title": "Controle de OP agora inclui cortes fora da programação",
        "description": (
            "Usuário perguntou se o Controle de OP considerava cortes que não foram "
            "programados. Não considerava: historico_op() partia sempre da planilha de "
            "Programação e só juntava o corte por cima — qualquer OP cortada sem nunca ter "
            "sido lançada na Programação ficava 100% invisível. Testado com dados reais: 313 "
            "OPs (~1,58 milhão de peças) estavam nessa situação. "
            "utils/controle_op.py: nova _ops_fora_programacao() identifica, a partir do "
            "próprio histórico de corte, toda OP que não bateu com nenhuma linha da "
            "Programação, e entram no resultado de historico_op() com status novo 'Fora da "
            "Programação' (FORA_PROGRAMACAO=True). Produto: preenchido pelo MATERIAL do "
            "próprio registro de corte (sempre disponível — 313/313 preenchidos no teste); só "
            "cai pra busca na Carteira de Pedidos (_load_carteira_lookup, novo) quando o corte "
            "não tem material nenhum — mesma ressalva de match baixo (~2%) já registrada no "
            "item anterior, mas ainda vale tentar preencher o que der. Quantidade de "
            "referência (pra calcular % e status Concluído/Parcial em vez de só 'Fora da "
            "Programação') também vem da Carteira quando encontrada. Efeito colateral bom: "
            "'0' (placeholder de linhas em branco/retrabalho sem OP, 13 registros) passou a "
            "ser filtrado como OP inválida em load_cortes — antes viraria uma falsa 'OP fora "
            "da programação' misturando produtos sem relação. pages/11_Controle_de_OP.py: "
            "novo KPI 'Fora da Programação', novo status no filtro, tabela geral trata "
            "% Conclusão/Data Conclusão vazios sem quebrar. gerar_pdf_fechamento_op "
            "(utils/pdf_report.py) idem, mais nova cor (teal) pro status na tabela do PDF. "
            "Testado: PDF gera sem erro com a mistura de status."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "novo",
        "title": "Novo Controle de OP — histórico de conclusão, status, % e relatório de fechamento",
        "description": (
            "Pedido do usuário: um controle de OP com histórico de conclusão, status, % de "
            "conclusão e relatório de fechamento, o mais automático possível com os dados já "
            "existentes. Investigação: só o estágio de corte tem OP rastreável hoje "
            "(Programação × Corte, já calculado em pages/4_Controladoria_Programacao.py); "
            "produção nas facções não tem OP nenhuma e a Carteira de Pedidos (campo PEDIDO) "
            "tem só 2,1% de match com as OPs da Programação (23 de 1082, testado com dados "
            "reais) — não é um vínculo confiável, então não foi usado. Escopo definido com o "
            "usuário: só Programação → Corte, 100% automático, sem digitação nova.\n"
            "Extraída pra utils/controle_op.py (antes só existia dentro de "
            "pages/4_Controladoria_Programacao.py) toda a lógica de cruzamento: "
            "load_programacao, load_cortes, enriquecer, agregar_por_op — pages/4 e "
            "pages/10_Relatorios.py (_calcular_df_agg, aba Programação) passaram a importar "
            "dali em vez de reimplementar (as duas versões tinham divergido: 100% vs 96% de "
            "limiar pro status 'Concluído' — unificado em 96%, LIMIAR_CONCLUSAO). Nova função "
            "calcular_data_conclusao: acumula os registros de corte de cada OP por data até "
            "atingir 96% do programado — mesmo limiar do status, pra nunca dar 'Concluído' sem "
            "data ou vice-versa (testado: 378/378 OPs concluídas com data calculada). Nova "
            "página pages/11_Controle_de_OP.py: KPIs (Total/Concluídas/Parciais/Pendentes/"
            "Aderência), gráfico de OPs concluídas por semana, tabela de histórico de "
            "conclusão e tabela geral, aviso de escopo (só corte, facção ainda não rastreada) "
            "e botão de gerar relatório PDF (gerar_pdf_fechamento_op, utils/pdf_report.py). "
            "Card novo na Home (config/sectors.py, SECTORS_CONTROLADORIA). Testado com dados "
            "reais: números batem exatamente com pages/4 (1084 OPs, 378 concluídas, 114 "
            "parciais, 592 pendentes) e o PDF gera sem erro."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "melhoria",
        "title": "KPI 'Meta Mensal' renomeado pra 'Meta do Período' no relatório PDF",
        "description": (
            "utils/pdf_report.py (gerar_pdf_faccoes, 'Resumo Executivo'): o KPI dizia 'Meta "
            "Mensal', mas o relatório (aba Produção Geral / Facções de pages/10_Relatorios.py) "
            "aceita qualquer intervalo de Data Inicial/Final, não só um mês fechado — nome "
            "desatualizado desde que o filtro de período virou livre. Renomeado pra 'Meta do "
            "Período', igual ao label que o dashboard ao vivo (pages/2_Producao_Geral.py, KPI "
            "k2) já usa."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "novo",
        "title": "Calendário de feriados (nacional + SP) reconhecido em toda a meta e nos relatórios",
        "description": (
            "Usuário notou que 09/07/2026 (feriado estadual de SP, Revolução "
            "Constitucionalista) apareceu como dia normal no dashboard/relatório, mesmo com só "
            "parte da equipe trabalhando — todo cálculo de 'dia útil' do projeto usava só "
            "weekday() < 5 (seg-sex), sem noção de feriado. Novo módulo utils/feriados.py, "
            "usando a lib 'holidays' (adicionada em requirements.txt) com calendário Brasil + "
            "SP (confirmado com o usuário: todas as facções são de SP). Expõe eh_feriado, "
            "nome_feriado, eh_dia_util e contar_dias_uteis — substituído o padrão "
            "'weekday() < 5' repetido em ~15 lugares: utils/faccoes_metas_calc.py (cálculo "
            "central de meta, maior alcance — alimenta dashboard e relatórios), "
            "pages/2_Producao_Geral.py, pages/3_Controle_de_Corte.py, "
            "pages/5_Producao_Faccoes.py, pages/7_Plano_de_Metas.py, utils/faccoes_viz.py e "
            "utils/pdf_report.py. Em pages/2_Producao_Geral.py "
            "(calcular_dias_com_sabados_trabalhados), feriado com produção passou a contar "
            "como 'dia extra trabalhado' — mesma regra já usada pra sábado — em vez de dia "
            "útil cheio. Visual: o gráfico 'Produção Diária x Meta' (dashboard, aba Por "
            "Cliente) e _chart_producao_diaria (relatórios PDF de corte) agora pintam a barra "
            "do feriado de âmbar (não vermelho/verde) com o nome do feriado no hover/legenda, "
            "e o relatório Arealva Manta ganhou uma linha 'Feriados no período' junto das "
            "observações que já existiam de sábado trabalhado / dia útil sem registro."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "correção",
        "title": "Estações do Corte Iacanga duplicadas por acento/maiúscula",
        "description": (
            "A planilha de corte Iacanga tem a mesma estação física digitada de formas "
            "diferentes ao longo do tempo ('Maquina 1' sem acento, 'Máquina 1' com acento, "
            "'mesa 2' minúsculo) — sem normalizar, cada grafia virava uma linha própria no "
            "relatório 'Desempenho por Estação' e nos filtros/gráficos do dashboard "
            "(confirmado com dados reais: 'Máquina 1' tinha 120 peças numa grafia + 52 na "
            "outra, deveriam somar 172 juntos). Pior: o relatório PDF (utils/pdf_report.py) "
            "classificava a variante SEM acento como grupo MAQUINA mas a variante COM "
            "acento como MESA (comparação de string sem tratar acento), puxando a meta de "
            "referência errada pra metade dos registros de Máquina. Adicionada "
            "canoniza_estacao_iacanga() em pages/3_Controle_de_Corte.py (usada por "
            "carregar_dados_iacanga) e _canoniza_estacao_iacanga() equivalente em "
            "pages/10_Relatorios.py (usada por _dados_iacanga, que alimenta o PDF) — "
            "reconhece MAQUINA/MESA/BURDAY/REFILAMENTO/DERIVADOS + número e uniformiza pra "
            "grafia única (ex.: sempre 'Máquina 1'); nomes fora desse padrão passam "
            "inalterados. gerar_pdf_iacanga_manta também parou de reclassificar o grupo por "
            "conta própria sem tratar acento — agora reusa GRUPO_ESTACAO já calculado "
            "corretamente quando o df traz essa coluna. Testado com dados reais da "
            "planilha: 17 grafias distintas viraram 11 estações reais, sem perder peça."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "correção",
        "title": "Realizado de Maio/Junho corrigido na Previsão de Cargas",
        "description": (
            "pages/8_Previsao_Cargas.py: o REALIZADO mensal de Maio e Junho/2026, extraído "
            "automaticamente da linha-resumo da planilha de cargas, não batia com o valor "
            "real de fechamento (relatório 'Acompanhamento Mensal' por empresa) — o "
            "lançamento diário desses meses ficou incompleto na origem e o usuário "
            "confirmou que não há mais como recuperar esse detalhe dia a dia. Adicionado "
            "REALIZADO_MENSAL_OVERRIDE (dict (ano, mes) → valor) aplicado logo após "
            "_find_resumo_mensal(), só para Maio (R$ 4.065.134,69) e Junho (R$ "
            "4.124.995,84) — os valores corretos vêm do Acompanhamento Mensal. Não altera a "
            "extração normal: Julho em diante continua vindo 100% da planilha, e a "
            "reconciliação do painel diário (_fator) usa o valor já corrigido, então o "
            "gráfico de evolução diária desses dois meses também soma certo."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "novo",
        "title": "Filtro de Facção/Empresa no Relatório de Produção Geral",
        "description": (
            "pages/10_Relatorios.py (aba 🏭 Produção Geral): antes o relatório sempre saía com "
            "todas as facções fixas + quarterizadas do período, sem como isolar 1 ou algumas "
            "empresas específicas. Novo multiselect 'Facção / Empresa' (placeholder 'Todas', "
            "vazio = sem filtro, mesmo padrão de pages/9_Carteira_de_Pedidos.py) dentro do card "
            "de período, populado com a lista completa de FACCAO do dataset unificado "
            "(utils/producao_unificada.load_producao_unificada) — carregado uma vez fora do "
            "clique do botão pra já aparecer no filtro antes de gerar. O filtro selecionado "
            "aparece na capa do PDF ('Filtros ativos: Facção(ões): ...') e, quando são 1 a 3 "
            "facções, entra no nome do arquivo baixado. Nenhuma mudança em "
            "utils/pdf_report.py — gerar_pdf_faccoes já funciona sobre qualquer subconjunto do "
            "dataset."
        ),
    },
    {
        "date": "10/07/2026",
        "tag": "novo",
        "title": "Comparação Produzido x Meta na aba 'Por Cliente' do drilldown de facção",
        "description": (
            "pages/2_Producao_Geral.py (render_faccao_drilldown, aba 'Por Cliente'): "
            "primeira tentativa rateava a Meta do Período por (cliente, produto) e "
            "mostrava Meta/Saldo/% dentro da tabela 'Resumo por Cliente/Produto' — usuário "
            "apontou que isso está errado, porque a meta é um valor único pra quarterizada "
            "inteira, não definida por produto, então fragmentá-la por linha é enganoso "
            "(removida a função _calcular_meta_cliente_produto_faccao_periodo criada pra "
            "isso, ficou sem uso). Substituído por um gráfico de barras separado "
            "'🎯 Produzido x Meta — Total do Período', acima da tabela, comparando só os "
            "dois totais (Produzido vs Meta) já calculados no topo da página — não quebra "
            "nada por produto/cliente, e deixa claro que é uma meta só. Também troquei "
            "'Evolução Diária por Cliente' (uma linha por cliente) por 'Evolução Diária por "
            "Produto' (uma linha por produto, pedido do usuário) e corrigi o eixo Y desse "
            "gráfico pra sempre começar em zero — antes ele autoescalava a partir do menor "
            "valor da série (ex.: começava em 3.600 em vez de 0), fazendo variações "
            "pequenas parecerem quedas ou saltos dramáticos."
        ),
    },
    {
        "date": "09/07/2026",
        "tag": "correção",
        "title": "Realizado do Plano de Metas não batia com prestadores terceirizados",
        "description": (
            "pages/7_Plano_de_Metas.py: o Realizado é calculado cruzando o nome do RESPONSAVEL "
            "(planilha de metas) com o nome do FACÇÃO/PRESTADOR na Produção Geral (xlsx). "
            "Diagnóstico mostrou 5 de 11 prestadores de maio/2026 sem match (Realizado caiu pra "
            "2,2% da meta): 'GIATTEX (LETICIA)', 'ZARO TEXTIL (LUIS)' e 'MARCELA SOARES DE "
            "MATTOS' tinham sufixos que quebravam o match com 'GIATTEX', 'ZARO (LUIS)' e "
            "'MARCELA SOARES'; 'MEGA PREVEN' era ambíguo entre 'MEGA PREVEN BARIRI' e 'MEGA "
            "PREVEN MATRIZ' (confirmado com o usuário → MATRIZ). Os 4 aliases foram cadastrados "
            "em config/settings.py → NOME_EQUIVALENCIAS. Faltava ainda 'ANAILA TELLES', que não "
            "aparece na Produção Geral — usuário indicou que ela está na aba QUARTERIZADAS da "
            "planilha de facções externas (utils/faccao_loader.py), fonte que essa página nunca "
            "consultava. Adicionada _load_faccoes_quarterizadas() e plugada em "
            "_build_producao_real(), mas SÓ incluindo prestadores que a Produção Geral não cobre "
            "— 13 dos 14 nomes da aba QUARTERIZADAS já existem na Produção Geral (mesma produção "
            "registrada nas duas fontes) e entrariam em dobro se fossem somados sem esse filtro. "
            "Resultado: Realizado subiu de 11.285 (2,2%) para 136.084 (26,1%) da meta de maio, "
            "sem inflar os prestadores que já batiam."
        ),
    },
    {
        "date": "09/07/2026",
        "tag": "melhoria",
        "title": "Plano de Metas simplificado para apresentação",
        "description": (
            "pages/7_Plano_de_Metas.py: removida a seção financeira (Receita Prevista/Projetada, "
            "Custo Projetado, Margem Projetada) dos KPIs, da tabela de progresso por prestador e "
            "da seção por centro de custo — mantendo só produção (Meta Mês, Realizado, Projeção). "
            "Removido também o expander de diagnóstico 'Equivalências de Nomes' (debug técnico de "
            "auto-match, sem valor para quem só consulta o painel). Seção 4 renomeada para "
            "'Produção por Centro de Custo'. Confirmado que o link da planilha de metas "
            "(config/settings.py → SHEET_ID_METAS/GID_METAS) já apontava para a planilha nova "
            "informada pelo usuário — nenhuma mudança necessária ali."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Análise de Faturamento removida (card + página)",
        "description": (
            "config/sectors.py (SECTORS_ANALISE): removido o card 'faturados' (Análise de "
            "Faturamento) — estava marcado como 'maintenance' há um tempo e o usuário decidiu "
            "não seguir com essa análise. Confirmado que nenhum outro arquivo importava ou "
            "referenciava pages/1_Produtos_Faturados.py (nem utils/, nem outras páginas), então "
            "o arquivo foi apagado do projeto junto com o card."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "novo",
        "title": "Nova análise de Peças por Categoria na Carteira de Pedidos",
        "description": (
            "pages/9_Carteira_de_Pedidos.py: até agora a única visão por categoria era em R$ "
            "(pizza 'Carteira por Categoria', evolução mensal, cliente × categoria) — não dava "
            "pra saber quantas peças de cada categoria ainda faltam produzir. Nova seção "
            "'Peças por Categoria — O que Falta Produzir', logo após os KPIs: gráfico de barras "
            "horizontal com o total de peças em carteira por categoria (mesmas cores de "
            "CORES_CAT usadas no resto do dashboard) + tabela com % do total e nº de pedidos "
            "por categoria. Respeita os mesmos filtros da sidebar (Ano, Mês, Cliente, Categoria, "
            "Produto etc.). Barra 'OUTROS' mostra ao passar o mouse os até 8 produtos "
            "(DESCRICAO) que mais pesam nela, com a quantidade de peças de cada um — mesmo "
            "padrão já usado na pizza 'Carteira por Categoria' (em R$), agora também em peças."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Spinner de carregamento replicado em todos os dashboards",
        "description": (
            "Varredura em todas as páginas (pages/1 a pages/9) atrás de carregamentos pesados "
            "sem indicador visual, mesmo problema já corrigido na Produção Geral (ver item "
            "anterior). A maioria já tinha spinner (Carteira de Pedidos, Programação, Facções, "
            "Histórico, Plano de Metas, Previsão de Cargas) — cobertos por st.spinner() manual "
            "ou pelo show_spinner do @st.cache_data. Adicionado onde faltava: "
            "pages/1_Produtos_Faturados.py (load_data, carregamento principal da planilha) e "
            "pages/3_Controle_de_Corte.py (carregar_dados/carregar_dados_iacanga — Manta "
            "Arealva e Iacanga — antes usavam o spinner genérico padrão do Streamlit "
            "'Running carregar_dados()...'; agora show_spinner=False no cache + st.spinner com "
            "mensagem própria, no mesmo padrão do resto do arquivo). app.py (Home) e "
            "pages/10_Relatorios.py não precisam — não fazem carregamento pesado ao abrir a "
            "página, só quando o usuário clica em 'Gerar', o que já tinha spinner."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Removida a data/horário de geração de todos os relatórios PDF",
        "description": (
            "utils/pdf_report.py: removido 'Gerado em: {data/hora}' da capa e do rodapé de "
            "todo relatório (função compartilhada por todos os PDFs — _make_cover, "
            "_cover_page_template, _header_footer_normal — e a linha de assinatura no fim de "
            "cada relatório, ~11 ocorrências). Mantido só 'Sistema de Gestão Industrial' como "
            "identificação, sem timestamp. scripts/relatorio_diario_corte.py: mesmo tratamento "
            "no relatório diário de corte e no consolidado (PDF anexado ao e-mail automático) — "
            "removida a linha 'Enviado em: {data} às 10:00' dos três rodapés. Pedido do usuário: "
            "tirar data e horário de geração dos relatórios."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Spinner de carregamento na Produção Geral pra não parecer travado",
        "description": (
            "pages/2_Producao_Geral.py: usuário relatou que o dashboard parece travado — tela "
            "em branco (só o breadcrumb) enquanto os dados carregam, sem nenhum indicador "
            "visual. render_por_faccao() (carrega o dataset unificado — planilha antiga + "
            "facções, o load mais pesado da página) e _render_interno_tab() (carrega cada "
            "unidade interna: LITTEX, GGTTEX etc.) agora envolvem o carregamento em "
            "st.spinner() com mensagem descritiva. O título/cabeçalho de cada tela já renderiza "
            "antes do load (confirmado lendo main() e render_por_faccao()); o que faltava era só "
            "o indicador de 'carregando' no meio do caminho. Não é uma tela de splash de "
            "verdade — o Streamlit não desenha nada antes do script rodar, então não tem como "
            "mostrar algo antes disso — mas resolve a sensação de travado."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "correção",
        "title": "Mesmo bug de filtro 'preso' corrigido em Carteira de Pedidos e Relatórios",
        "description": (
            "Varredura no projeto inteiro atrás do mesmo bug corrigido na Produção Geral (ver "
            "item anterior). Novo helper utils/ui_helpers.py:multiselect_reset_on_grow "
            "(reaproveitado pela correção da Produção Geral) aplicado em mais 3 pontos onde o "
            "filtro de Mês depende do filtro de Ano — mesmo padrão de risco: "
            "pages/9_Carteira_de_Pedidos.py (Mês e Produto, que depende de Categoria) e "
            "pages/10_Relatorios.py (Mês da Carteira, aba Carteira de Pedidos). Conferidos e "
            "descartados como já seguros: pages/1_Produtos_Faturados.py (o filtro de Ano já tem "
            "on_change que limpa o de Mês, resolvendo o problema por outro caminho), "
            "pages/7_Plano_de_Metas.py e pages/1_Produtos_Faturados.py (widgets sem key= "
            "explícita resetam sozinhos ao mudar as opções, não travam), "
            "pages/8_Previsao_Cargas.py, pages/4_Controladoria_Programacao.py, "
            "pages/3_Controle_de_Corte.py e pages/5_Producao_Faccoes.py (nenhum filtro nesses "
            "arquivos depende de outro — sem cascata, sem risco)."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "correção",
        "title": "Filtros de Cliente/Produto podiam ficar 'presos' escondendo dados reais (Previttex Matriz e qualquer facção)",
        "description": (
            "pages/2_Producao_Geral.py (render_faccao_drilldown e _faccao_sidebar_filtros): "
            "usuário reportou que a Previttex Matriz, na aba Por Cliente, só mostrava 'Cobertor "
            "Velour' pro cliente Camesa, mesmo produzindo mais produtos pra esse cliente. "
            "Investigação confirmou que os dados brutos (utils/faccao_loader.py, "
            "utils/producao_unificada.py) sempre estiveram completos — o bug era nos widgets "
            "st.multiselect em cascata (Ano → Mês → Cliente → Produto): o Streamlit só REDUZ a "
            "seleção guardada quando as opções mudam, nunca a expande de volta ao novo default. "
            "Assim, se o usuário estreitava o período (ex.: modo 'Um dia' num dia em que só um "
            "produto rodou) e depois alargava de novo, o filtro de Produto continuava preso "
            "naquele produto único, escondendo os outros em todas as abas (Visão Geral, Por "
            "Cliente, Ranking, Dados) — bug genérico, afetava qualquer facção, não só a "
            "Previttex. Corrigido com o novo helper _multiselect_reset_on_grow, que resincroniza "
            "a seleção pra lista cheia sempre que as opções mudam."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Consolidado de Corte ganha período real; visual em card replicado em todas as abas de Relatórios",
        "description": (
            "scripts/relatorio_diario_corte.py (gerar_pdf_consolidado): novo parâmetro opcional "
            "dia_ini — quando informado e diferente de 'dia', a seção 1 do PDF passa a somar o "
            "período [dia_ini, dia] no formato resumido (igual às seções de mês) em vez do "
            "detalhamento de um único dia. Sem esse parâmetro o comportamento é idêntico ao de "
            "antes, então o e-mail diário automático (que não passa dia_ini) continua igual. "
            "pages/10_Relatorios.py: a aba ✂️ Corte agora tem Data Inicial/Final também pro "
            "Consolidado (antes só tinha 'Dia de referência'). O padrão visual em card com borda "
            "('📅 Período' + campos + botão) foi replicado nas abas Produção Geral, Cargas, "
            "Carteira de Pedidos e Programação, no lugar do antigo truque de 3 colunas pra "
            "centralizar o botão."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Aba Corte reorganizada com seletor de relatório; aba Facções removida",
        "description": (
            "pages/10_Relatorios.py: a aba ✂️ Corte tinha 5 relatórios (Consolidado, Arealva "
            "Manta, Iacanga Manta, Lençol, Itaju) espalhados em duas colunas, cada um com sua "
            "própria data e botão — confuso de entender à primeira vista. Agora tem um seletor "
            "'Tipo de relatório' e só mostra os campos e o botão do relatório escolhido por vez. "
            "A aba 👕 Facções foi removida (não é mais usada — o relatório de Produção Geral já "
            "cobre o mesmo caso via dataset unificado, ver changelog de 07/07/2026); as funções "
            "_dias_uteis e _dados_faccoes, que só serviam essa aba, e os imports load_faccoes / "
            "FACCOES_FACCAO_ALIAS, que ficaram sem uso, foram removidos junto."
        ),
    },
    {
        "date": "08/07/2026",
        "tag": "melhoria",
        "title": "Total do produto agora é coluna mesclada, não linha extra, na tabela de Facções/Produção Geral",
        "description": (
            "utils/pdf_report.py (gerar_pdf_faccoes, tabela 'Visão Geral por Empresa / "
            "Produto'): antes cada grupo de produto era fechado com uma linha extra 'TOTAL' "
            "no meio da tabela — testado e achado bagunçado pelo usuário. Agora a tabela tem "
            "duas colunas novas, 'Total do Produto' e 'Média/Dia (Produto)', mescladas "
            "verticalmente (SPAN) e centralizadas ao lado das linhas de facção de cada "
            "produto, sem linha extra. Vale tanto pro relatório de Facções quanto pro de "
            "Produção Geral, que reaproveita a mesma função."
        ),
    },
    {
        "date": "07/07/2026",
        "tag": "novo",
        "title": "Relatório 'Corte Consolidado' agora é idêntico ao PDF do e-mail diário",
        "description": (
            "pages/10_Relatorios.py (aba ✂️ Corte, botão 'Gerar Corte Consolidado'): antes gerava "
            "um PDF próprio (utils.pdf_report.gerar_pdf_corte_consolidado, com Itaju e sem "
            "detalhamento por dia/mês). Agora chama diretamente "
            "scripts.relatorio_diario_corte.gerar_pdf_consolidado — a mesma função que gera o "
            "anexo do e-mail automático diário — com um novo campo 'Dia de referência' (padrão: "
            "ontem, igual ao e-mail). Produz o mesmo PDF de 3 seções (Dia / Mês Atual / Últimos 2 "
            "Meses) com Manta Arealva + Manta Iacanga + Lençol Arealva. Os outros 4 relatórios da "
            "aba (Arealva Manta, Iacanga Manta, Lençol, Itaju) continuam com seus layouts "
            "próprios, com comparação de meta. Testado ao vivo: PDF gerado com sucesso."
        ),
    },
    {
        "date": "07/07/2026",
        "tag": "novo",
        "title": "Relatório de Produção (aba Produção Geral) usa dataset unificado",
        "description": (
            "pages/10_Relatorios.py (aba 🏭 Produção Geral): o relatório agora gera exatamente o "
            "mesmo formato da aba Facções (Resumo Executivo + Facção x Meta + gráficos + "
            "detalhamento por produto/facção + detalhe diário), só que a partir do dataset "
            "unificado (utils.producao_unificada.load_producao_unificada) — histórico completo "
            "(planilha antiga + facções) com todas as correções já aplicadas ao dashboard ao vivo "
            "(GIATTEX, Felipe→Litex, quarterizadas inativas removidas). O relatório antigo por "
            "empresa/cliente (gerar_pdf_producao_geral) deixou de ser usado nessa aba. Corrigido "
            "de quebra um bug em utils/producao_unificada.py: quando um dos dois lados (legado ou "
            "facções) vinha vazio, pd.concat trocava a coluna DATA pra dtype 'object', quebrando "
            "qualquer .dt.date usado depois — forçado pd.to_datetime no resultado final. "
            "Testado ao vivo: PDF gerado com sucesso e a tabela Facção x Meta bate com a tela."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "melhoria",
        "title": "Prestadores quarterizados inativos removidos do dashboard",
        "description": (
            "utils/producao_unificada.py (PRESTADORES_INATIVOS): Angela Bandeirantes, Anjos "
            "Texteis, Daiane, Mara, Marcia Gonçalves, Maria Gessi e Maria Helena não produzem "
            "mais e só poluíam a lista de QUARTERIZADAS. Removidos do dataset unificado inteiro "
            "(pedido do usuário). Testado ao vivo: nenhuma das sete aparece mais na lista, e o "
            "total de QUARTERIZADAS caiu de 3.584.069 para 3.145.360 un. — exatamente a soma da "
            "produção histórica delas (438.709 un.)."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "correção",
        "title": "Prestador Felipe unificado com a facção fixa LITEX",
        "description": (
            "utils/producao_unificada.py: o prestador FELIPE (quarterizada na planilha de "
            "facções) é a mesma pessoa/produção da facção fixa LITEX — 'LITTEX', na planilha "
            "antiga, já era o nome usado pra essa mesma produção. Adicionado 'FELIPE' → 'LITEX' "
            "em FACCAO_RENOMEADA (mantido 'LITTEX' → 'LITEX' em FACCAO_ALIAS_LEGADO). FELIPE "
            "deixou de aparecer separado em QUARTERIZADAS. Testado ao vivo: LITEX passou de "
            "56.952 para 490.184 un. (56.952 + 433.232 do Felipe) e QUARTERIZADAS caiu na mesma "
            "proporção, de 4.017.301 para 3.584.069 un."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "correção",
        "title": "Botão 'Início' duplicado na sidebar de Produção por Facção",
        "description": (
            "pages/2_Producao_Geral.py (_faccao_sidebar_filtros): a sidebar das telas de "
            "facção (home, quarterizadas e drill-down) chamava render_home_button() por cima "
            "do botão 'Início' que _sidebar_nav_producao já desenha, duplicando o botão. "
            "Removida a chamada redundante. Também removido o botão 'Ver comparação completa "
            "entre facções', que levava para a página antiga de comparação (5_Producao_Faccoes.py), "
            "já substituída pela aba 'Comparação — Facção e Produto' dentro da própria tela."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "melhoria",
        "title": "QUARTERIZADAS sempre primeiro na lista de seleção",
        "description": (
            "pages/2_Producao_Geral.py (_faccao_grade_selecao): o item 'QUARTERIZADAS' na home de "
            "facções ficava perdido no meio/fim da lista (ordem alfabética colocava ele por "
            "último). Agora ele sempre aparece primeiro, com o resto das facções em ordem "
            "alfabética logo depois."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "novo",
        "title": "Aba 'Comparação — Facção e Produto' dentro da Produção Diária",
        "description": (
            "pages/2_Producao_Geral.py: a home de facções ('Dashboard de Produção — Todas as "
            "Facções') ganhou uma segunda aba, ao lado de 'Visão Geral', com a comparação "
            "completa entre facções e entre produtos — portada de pages/5_Producao_Faccoes.py "
            "(abas '🏭 Por Facção' e '📦 Por Produto'), sem trazer as visões Mensal/Semanal/Diária "
            "daquela página (já cobertas pela 'Evolução Mensal' existente). Sub-aba 'Por Facção': "
            "KPIs, % por facção, produção diária empilhada, ranking Produzido vs Meta (usa "
            "utils/faccoes_metas_calc.calcular_meta_faccoes — a versão sem o bug de duplicação "
            "corrigido acima), regularidade/assiduidade (reaproveita utils/faccoes_viz.py, criado "
            "antes mas ainda sem uso), mapa de calor Facção × Dia, evolução acumulada/diária, mix "
            "de produtos por facção e tabela de detalhe. Sub-aba 'Por Produto': ranking, mix "
            "(donut), treemap Produto→Empresa, heatmap Produto×Empresa, evolução dos top 6 "
            "produtos. Diferença de escopo: aqui a comparação é sempre por FACCAO individual (sem "
            "agrupar quarterizadas), igual ao comportamento original da página portada."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "correção",
        "title": "Facção duplicada e sem meta na comparação entre facções (GIATTEX / MEGA PREVEN MATRIZ)",
        "description": (
            "pages/5_Producao_Faccoes.py: a tabela 'Ranking detalhado Facção × Meta' mostrava "
            "GIATTEX duas vezes (uma com produção e sem meta, outra com meta e produção zerada) e "
            "MEGA PREVEN MATRIZ sempre sem meta. Causa: o alias FACCOES_FACCAO_ALIAS (ZANATTA→"
            "GIATTEX, PREVITTEX FILIAL→MEGA PREVEN MATRIZ) renomeava a coluna de exibição FACCAO, "
            "mas a coluna FACCAO_N (usada pra casar produção com a guia de metas) tinha sido "
            "calculada ANTES do rename e ficava com o nome antigo — produção com chave 'zanatta', "
            "meta com chave 'giattex', nunca combinavam. Corrigido recalculando FACCAO_N depois de "
            "aplicar o alias. Confirmado com dados reais: antes, produção usava a chave 'ZANATTA'/"
            "'PREVITTEX FILIAL' e meta usava 'GIATTEX'/'MEGA PREVEN MATRIZ' (chaves diferentes); "
            "depois da correção, as duas batem exatamente. Bug pré-existente, independente da "
            "unificação com a planilha antiga — afetava só esta página (utils/producao_unificada."
            "py, usado pelo novo drill-down, já fazia esse recálculo corretamente)."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "melhoria",
        "title": "Nota de 'última data com dado' em cada facção/prestador",
        "description": (
            "pages/2_Producao_Geral.py (_faccao_grade_selecao): cada botão de seleção (facção "
            "fixa ou prestador individual dentro de Quarterizadas) ganhou uma notinha discreta "
            "('· até DD/MM') com a última data com produção lançada no período filtrado, embutida "
            "na mesma linha do botão (não como elemento separado, pra não ficar solta do card). "
            "O card agregado 'QUARTERIZADAS' na home NÃO mostra essa data — misturar a última "
            "data de todos os prestadores não diz muito; quem quiser saber a data de cada um "
            "entra no card e vê lá dentro. Serve pra identificar rapidamente quem está com "
            "lançamento em dia e quem está atrasado — algumas quarterizadas já apareceram bem "
            "discrepantes entre si (uma até "
            "03/07, outra só até 06/02). Investigação à parte: verificamos se o parser de data "
            "estava invertendo dia/mês (suspeita do usuário) cruzando duas datas específicas "
            "direto contra as células brutas do Excel (Angela Bandeirantes → 06/02, Felipe → "
            "07/04) — ambas batem exatamente com o dado real (células datetime nativas do Excel, "
            "sem ambiguidade). Também vasculhamos todas as abas por cabeçalhos de data gravados "
            "como texto (esses sim arriscam inversão) — só existem em 'Niazittex' (não usada "
            "nessa via, vem da LITEX_GERAL) e 'Decor', e ambas seguem DD/MM/AAAA corretamente. "
            "Nenhum caso de inversão dia/mês encontrado nos pontos verificados."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "melhoria",
        "title": "KPIs removidos das telas de seleção de facção/quarterizadas",
        "description": (
            "pages/2_Producao_Geral.py: removida a linha de KPIs (Grupos/Prestadores Ativos, "
            "Produção Total, Média por Item, Dias com Registros) do topo das telas de seleção "
            "(home de facções e tela de Quarterizadas) — a pedido do usuário. As duas telas "
            "compartilham a mesma função (_faccao_grade_selecao), então a mudança vale pras duas "
            "de uma vez. O drill-down individual de cada facção/prestador continua com seus "
            "próprios KPIs (Total Produzido, Meta, Saldo, Atingimento etc.), sem alteração."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "novo",
        "title": "Produção por Cliente descontinuada — só a Produção Diária (facções) fica",
        "description": (
            "pages/2_Producao_Geral.py: removido o dashboard antigo 'Produção por Cliente' "
            "(render_home/render_company e a tela intermediária 'Produção por Cliente ou "
            "Facções') — o time passa a usar só a nova visão unificada de facções (KPIs + Visão "
            "Geral / Por Cliente / Ranking & Alertas / Dados), que já cobre a análise por cliente "
            "dentro de cada facção. Clicar em 'Por Cliente' na tela 'Tipo de Análise' agora vai "
            "direto pra tela de facções, sem a etapa intermediária de escolher entre os dois "
            "dashboards (que não fazia mais sentido com só uma opção restando). Removidas ~1.000 "
            "linhas de código morto: render_home(), render_company(), render_por_cliente(), "
            "_screen_por_cliente_type(), _calc_meta(), _calc_meta_por_produto(), "
            "_all_data_from_unificado(), _on_home_ano_change/_on_home_mes_change() e "
            "CORES_EMPRESAS — nenhuma dessas funções tinha mais chamador depois da migração. "
            "load_all_data() e as funções de suporte da planilha antiga (_load_niazitex_"
            "suplementar, _load_metas_lookup_pg etc.) continuam — são a fonte da fatia legada "
            "(pré-01/06/2026) da linha do tempo unificada em utils/producao_unificada.py, ainda "
            "em uso pela nova tela."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "correção",
        "title": "Produto 'JOGOS'/'JOGO' da planilha antiga desambiguado por contexto",
        "description": (
            "utils/producao_unificada.py: a planilha antiga registra 'JOGOS' ou 'JOGO' como "
            "abreviação genérica, mas o produto real varia por quem produziu — aparecia solto na "
            "tabela 'Resumo por Cliente / Produto' ao lado do nome já correto (ex.: cliente "
            "Marcelino com 'JOGO DE CAMA PP' de um lado e 'JOGOS' de outro, sem unificar). Nova "
            "função _normalizar_produto_legado(): quando a facção é a Carline (MEGA (CARLINE)), "
            "'JOGOS'/'JOGO' viram 'JOGO DE CAMA'; quando o cliente é Marcelino (via outra facção), "
            "viram 'JOGO DE CAMA PP'. Fora desses dois contextos o produto não é alterado. "
            "Confirmado com o usuário e validado direto no CSV exportado da tela ao vivo — 100% das "
            "linhas de Marcelino/Carline já saem como 'JOGO DE CAMA', nenhuma 'JOGOS' solta."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "melhoria",
        "title": "Quarterizadas agrupadas na tela de facções + remoção de heatmap poluído",
        "description": (
            "pages/2_Producao_Geral.py: a tela 'Análise de Facções' listava cada prestador "
            "quarterizado (SUZANA, CAROL MENDES, FELIPE, ZARO (LUIS)...) solto ao lado das facções "
            "fixas, ficando confusa. Agora os prestadores individuais entram sob um único item "
            "'QUARTERIZADAS' na tela inicial; clicar nele abre uma nova tela (render_faccao_"
            "quarterizadas) só com os prestadores, no mesmo padrão visual (KPIs, gráfico, lista de "
            "seleção, evolução mensal, resumo). Critério de agrupamento (utils/producao_unificada."
            "py: faccoes_fixas()/is_quarterizada()/grupo_de()): é quarterizada tudo que NÃO é uma "
            "das facções fixas configuradas em FACCOES_ABAS — inclui ZARO (LUIS), que apesar do "
            "nome com parênteses é prestador individual; exclui MEGA (BOCA)/MEGA (CARLINE), que são "
            "facções fixas apesar do nome parecido. O botão 'Voltar' do drill-down individual agora "
            "sabe voltar pra tela de Quarterizadas (não pra Visão Geral) quando a facção clicada era "
            "uma quarterizada. Removido também o mapa de calor Cliente × Dia da aba 'Por Cliente' do "
            "drill-down — ficava ilegível pra prestadores com muitos dias de produção (cada dia "
            "virava uma faixa fina na única linha do heatmap)."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "correção",
        "title": "Reconciliação de nomes de facção na linha do tempo unificada",
        "description": (
            "utils/producao_unificada.py: correção dos alias de facção da planilha antiga, que "
            "estavam na direção errada e deixavam nomes desatualizados/duplicados na tela de "
            "facções. Agora o sistema sempre exibe o nome ATUAL: 'GIATTEX' (não mais 'Zanatta') e "
            "'MEGA PREVEN MATRIZ' (não mais 'Previttex Filial') — são abas só renomeadas no Sheets, "
            "mesmo GID. Duplicatas por digitação unificadas: 'NATHIELLY'→'NATCHIELLY', "
            "'PREVITEX MATRIZ'→'PREVITTEX MATRIZ', 'ELIZANGELA'→'ELISANGELA', e 'GGTTEX' solto → "
            "'GGTTEX CORTINA' (todos confirmados com o usuário). A tela de facções (home e resumo) "
            "passou a esconder facções com 0 peças no período — antes poluíam a lista com nomes "
            "sem produção. Corrigido também um bug de estado no drill-down: as chaves dos filtros "
            "de Ano/Mês/Cliente/Produto agora incluem o nome da facção, então trocar de facção na "
            "mesma sessão não faz o filtro de uma 'vazar' pra outra. Obs.: quando um nome aparece "
            "sem correspondente atual, é facção que parou ou começou a produzir — não é erro."
        ),
    },
    {
        "date": "06/07/2026",
        "tag": "novo",
        "title": "Drill-down por Facção + linha do tempo unificada em Produção por Cliente",
        "description": (
            "pages/2_Producao_Geral.py: 'Análise de Facções' (dentro de Análise de Produção → "
            "Por Cliente) deixou de abrir direto pages/5_Producao_Faccoes.py e passou a ter uma "
            "tela própria no mesmo padrão visual de 'Produção por Cliente' (KPIs + abas Visão "
            "Geral / Por Cliente / Ranking & Alertas / Dados) — selecionando uma facção específica "
            "dá pra ver o total dela somando todos os clientes que atende, algo que antes só dava "
            "pra ver fatiado dentro da tela de cada cliente. Um link 'Ver comparação completa "
            "entre facções →' preserva o acesso à página antiga de comparação lado a lado. "
            "utils/producao_unificada.py (novo): costura a planilha antiga de Produção Geral "
            "(histórico desde out/2025) com a planilha de Facções (mais atualizada, mas só com "
            "dados consistentes a partir de ~jun/2026) numa única linha do tempo — cutover em "
            "01/06/2026, antes disso vem da planilha antiga, depois da planilha de facções. Os "
            "nomes de facção da planilha antiga foram reconciliados manualmente com o usuário "
            "contra os nomes atuais (ex.: 'ZANATTEX' → 'GGTTEX RUTE', 'GIATTEX' → 'ZANATTA' e "
            "'MEGA PREVEN MATRIZ' → 'PREVITTEX FILIAL', que são a mesma aba só renomeada no "
            "Sheets — confirmado que o código busca por GID, não por nome, então isso não quebra). "
            "'Produção por Cliente' (render_home/render_company) passou a usar essa mesma linha "
            "do tempo unificada — os gráficos de Evolução Mensal e Produção Mensal por Ano agora "
            "têm o histórico completo (antes ficariam vazios pra qualquer período usando só a "
            "planilha de facções). A Meta do Período de cada cliente passou a somar a fatia "
            "legada (cálculo antigo, por linha) com a fatia nova (sistema ponderado por "
            "cliente/produto da planilha de facções), sem duplicar. utils/faccoes_viz.py (novo): "
            "heatmap e cálculo de regularidade/assiduidade extraídos de "
            "pages/5_Producao_Faccoes.py como funções genéricas, reaproveitadas no novo "
            "drill-down. CORES_FACCAO movido de pages/5_Producao_Faccoes.py para "
            "config/settings.py. Corrigido de brinde um bug pré-existente e não relacionado: "
            "dois print() de debug com seta unicode que quebravam load_all_data() inteiro em "
            "consoles Windows (cp1252) sempre que o cache estava frio."
        ),
    },
    {
        "date": "05/07/2026",
        "tag": "correção",
        "title": "Análises da Previsão de Cargas ficavam zeradas ao filtrar poucos meses",
        "description": (
            "pages/8_Previsao_Cargas.py: os gráficos por cliente, por local de carregamento, por tipo de "
            "veículo, timeline, ocorrências (cancel./adiadas) e o mapa de calor por dia da semana somavam "
            "a coluna PREVISAO — que é zerada linha a linha nos meses em que a planilha já tem um total "
            "previsto oficial (pra não contar em dobro no total mensal). Com todos os meses selecionados, "
            "algum mês em andamento sem total oficial ainda tinha PREVISAO preenchida e mascarava o "
            "problema; ao filtrar só meses já concluídos (todos com total oficial), as quebras ficavam "
            "totalmente vazias. Trocado para VALOR_FRETE (frete individual, nunca zerado) nessas quebras — "
            "mesmo padrão que a Evolução Semanal já usava. O gráfico de % Aderência por Mês tinha um bug "
            "à parte: excluía o registro CARGO_REAL (onde mora o previsto oficial) do cálculo, zerando a "
            "previsão de qualquer mês oficial — corrigido para usar o mesmo total já validado no gráfico "
            "mensal acima."
        ),
    },
    {
        "date": "05/07/2026",
        "tag": "melhoria",
        "title": "Filtro de Produto na Carteira de Pedidos agora agrupa por subcategoria",
        "description": (
            "pages/9_Carteira_de_Pedidos.py: o filtro de Produto (adicionado antes nesta mesma sessão) "
            "listava as 862 descrições exatas da planilha, uma por tamanho/cor (ex.: 'COB. DAY BY DAY "
            "ROLINHO SORT. CASAL 1,80MX2,20M' e '...QUEEN 2,20MX2,40M' apareciam como 2 produtos "
            "diferentes). Adicionada _subcategoria() em pages/9_Carteira_de_Pedidos.py, que remove "
            "tamanho/dimensão/cor/qualificadores (SORTIDO, LISO etc.) do texto pra agrupar variações do "
            "mesmo produto-base — a lista caiu de 862 para 495 opções (~43%). O filtro agora seleciona "
            "pela subcategoria; as tabelas e gráficos de detalhe continuam quebrando por produto "
            "específico (DESCRICAO) dentro do que foi selecionado. É uma heurística de texto — typos e "
            "cores não catalogadas podem deixar algum resíduo (ex.: 'CORTEX' vs 'CORTTEX')."
        ),
    },
    {
        "date": "04/07/2026",
        "tag": "correção",
        "title": "Meta digitada na coluna principal (METAS) era ignorada quando a linha já usava colunas extras",
        "description": (
            "utils/metas_manager.py (load_metas_from_faccoes_sheet): quando uma facção tem metas por "
            "cliente em colunas extras (ex.: GGTTEX CORTINA com 'BURDAYS 500' na METAS 2, 'SULTAN 150' na "
            "METAS 3), o parser só varria essas colunas extras em busca do padrão 'NOME NÚMERO' — nunca a "
            "coluna METAS principal. Ao adicionar 'DECOR 700' direto na coluna METAS (em vez de abrir mais "
            "uma coluna extra), o valor era descartado silenciosamente. Corrigido: a coluna METAS principal "
            "agora também entra na varredura desse padrão. Também correção da ponderação de meta por "
            "cliente (utils/faccoes_metas_calc.py) — um cliente sem meta cadastrada dividia a meta "
            "ponderada da facção pela metade sem contribuir nada de volta; agora só pondera pelos clientes "
            "que têm meta. O relatório também passou a apontar o cliente exato quando falta meta "
            "('Meta possivelmente incompleta: X — falta meta de CLIENTE'), em vez de um aviso genérico."
        ),
    },
    {
        "date": "04/07/2026",
        "tag": "melhoria",
        "title": "Gráficos do relatório de Facções nunca cortam mais facções de fora",
        "description": (
            "utils/pdf_report.py: os gráficos 'Produzido vs Meta Mês por Facção' e 'Mix de Produtos por "
            "Facção' limitavam a top 20 e top 10 facções por volume, respectivamente — as menores ficavam "
            "de fora sem aviso. A diretoria pediu para nunca cortar facções das análises; os dois gráficos "
            "agora incluem todas (o parâmetro top_n virou opcional, None = todas)."
        ),
    },
    {
        "date": "04/07/2026",
        "tag": "correção",
        "title": "Produção da MEGA (CARLINE) estava sendo contada como 'MEGA PREVEN FILIAL' (aba renomeada)",
        "description": (
            "config/settings.py (FACCOES_ABAS): a aba de gid 524251509 foi renomeada na planilha de "
            "'MEGA PREVEN FILIAL' para 'MEGA (CARLINE)' — mas o mapeamento gid→facção continuava com o "
            "rótulo antigo, que não corresponde a nenhuma facção real nem meta configurada. A produção "
            "real da Carline (15.100 peças em junho) aparecia como 'MEGA PREVEN FILIAL / sem meta'. "
            "Corrigido o rótulo para 'MEGA (CARLINE)', que já tem meta configurada na planilha (700 pç/dia "
            "= 15.400/mês) — agora bate 98,1%. Conferido também o mapeamento de todas as outras abas da "
            "planilha de facções contra os nomes atuais (via metadata htmlview da planilha); as únicas "
            "outras divergências (ZANATTA→GIATTEX, PREVITTEX FILIAL→MEGA PREVEN MATRIZ) já haviam sido "
            "corrigidas via alias nesta mesma sessão. A aba 'LITEX' dentro dessa planilha (gid 354291436) "
            "está vazia — não é usada, e não representa um gap de dados."
        ),
    },
    {
        "date": "04/07/2026",
        "tag": "correção",
        "title": "ZANATTA/PREVITTEX FILIAL apareciam 'sem meta' — facções foram renomeadas e faltava o alias",
        "description": (
            "config/settings.py (FACCOES_FACCAO_ALIAS): confirmado com o usuário que ZANATTA virou "
            "GIATTEX e PREVITTEX FILIAL virou MEGA PREVEN MATRIZ — a planilha de metas já usa os nomes "
            "novos, mas a planilha de produção ainda lança pelos nomes antigos. Sem o alias, a produção "
            "real (ZANATTA: 342.861 peças em junho, maior produtor do mês) ficava 'sem meta configurada' "
            "e o nome novo (GIATTEX) aparecia com 0 produzido — as duas linhas do relatório estavam "
            "descrevendo a mesma facção sem se conectar. Adicionados 'ZANATTA'→'GIATTEX' e "
            "'PREVITTEX FILIAL'→'MEGA PREVEN MATRIZ'; agora batem 134,2% e 101,4% da meta, respectivamente."
        ),
    },
    {
        "date": "04/07/2026",
        "tag": "correção",
        "title": "Aliases de facção desatualizados faziam a tabela Facção x Meta mostrar nomes errados",
        "description": (
            "config/settings.py (FACCOES_FACCAO_ALIAS): removidos 2 aliases obsoletos — "
            "'RUTE TALITA E TAMARA' → 'RUTE E TALITA' reescrevia o nome atual e correto da guia de "
            "metas para um nome antigo que não existe em nenhum mês de produção (fazia uma facção "
            "'fantasma' aparecer, e a real ficar sem meta vinculada); 'LUIZ CARLOS (ZARO)' → "
            "'LUIS CARLOS' estava morto dos dois lados. utils/metas_manager.py: a tabela secundária "
            "(estilo ZANATTA/GIATTEX) tinha uma linha duplicada na planilha (GIATTEX/KIT COLCHA/BURDAYS "
            "repetida duas vezes com o mesmo valor), contando a meta em dobro — adicionada deduplicação "
            "por (facção, produto, cliente, meta). utils/cache_manager.py: adicionados headers "
            "Cache-Control/Pragma no download para reduzir o CDN do Google servir uma resposta em cache "
            "logo após uma edição recente na planilha."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "melhoria",
        "title": "Relatório de Facções mostra até quando cada facção tem dado lançado",
        "description": (
            "utils/faccoes_metas_calc.py (calcular_meta_faccoes) e utils/pdf_report.py "
            "(gerar_pdf_faccoes): a tabela Facção x Meta ganhou a coluna 'Dados até' (último dia com "
            "produção lançada por facção) e um aviso listando quem está atrasado em relação às demais "
            "(ex.: SUZANA/FRANCIANE/RONILDA sem lançamento desde 17/06, 13 dias). A referência de atraso "
            "é a facção mais atualizada do grupo, não o fim do período — evita acusar atraso por causa de "
            "fim de semana/feriado em que ninguém produz. Sem isso, uma facção que simplesmente não mandou "
            "a planilha ainda aparecia como se tivesse produzido pouco, confundindo dado ausente com "
            "desempenho fraco."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "melhoria",
        "title": "Relatório PDF de Facções ganhou seção 'Facção x Meta' logo no início, com destaques",
        "description": (
            "utils/pdf_report.py (gerar_pdf_faccoes): o PDF não tinha uma tabela resumo Facção x Meta — "
            "só uma tabela granular por Produto/Empresa/Facção e um gráfico sem contexto de meta. "
            "Adicionada, logo após o Resumo Executivo, a tabela 'Facção x Meta' (Produzido, % do Total, "
            "Meta Mês, % Meta, Restante) com cores por status, gráfico comparativo Produzido vs Meta por "
            "facção, bloco de Destaques (melhor/pior desempenho) e um novo gráfico de Mix de Produtos por "
            "Facção. A lógica de cálculo de meta ponderada por facção (produto+cliente, dias reais de "
            "produção) foi extraída de pages/5_Producao_Faccoes.py para utils/faccoes_metas_calc.py, "
            "reutilizada também no relatório de pages/10_Relatorios.py — antes o relatório usava uma conta "
            "mais simples (e com o bug de meta_mes=0 corrigido nesta mesma sessão), então divergia do "
            "dashboard ao vivo. Corrigidos 3 aliases de facção faltantes em FACCOES_FACCAO_ALIAS "
            "(GGTTEX (RUTE)/GGTTEX (CORTINA)/MEGA (BOCA) não batiam com a grafia da produção, fazendo a "
            "meta aparecer 'zerada' numa linha fantasma enquanto a produção real ficava sem meta "
            "vinculada). Destaques agora ignora facções com % da meta > 200% (sinal de meta mal "
            "calibrada) e as lista à parte como 'meta possivelmente desatualizada'."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "correção",
        "title": "Meta mensal de facções vinha sempre zerada (afetava todo o dashboard e relatórios)",
        "description": (
            "utils/metas_manager.py (_make_entry, usada por load_metas_from_faccoes_sheet — fonte "
            "primária de metas): a coluna 'METAS' da planilha de metas é uma meta diária, mas o código "
            "zerava meta_mes incondicionalmente (meta_mes: 0) em vez de calculá-la a partir da meta "
            "diária. Como essa é a fonte de maior prioridade em load_metas(), isso zerava a meta mensal "
            "de TODAS as 35 facções cadastradas, não só uma. Corrigido para meta_mes = meta_dia × 22 "
            "dias úteis (consistente com os valores hardcoded de config/settings.py, onde meta_mes/22 = "
            "meta_semana/5 para as facções antigas)."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "correção",
        "title": "PDF de Corte de Lençol ignorava o período selecionado e zerava Jogos/Fundos",
        "description": (
            "10_Relatorios.py: o botão 'Gerar Lençol' passava _dados_lencol() inteiro (histórico "
            "completo desde 29/12/2025) para o PDF sem filtrar pela data inicial/final escolhida — o "
            "cabeçalho mostrava o período certo, mas os números (peças, dias trabalhados, prestadores) "
            "eram do acumulado geral, não do mês selecionado. Além disso, caseamento_df e totais_jf eram "
            "passados vazios/None de forma fixa, então os KPIs 'Jogos Duplos' e 'Fundos de Jogo' do PDF "
            "sempre apareciam zerados. Corrigido o filtro de data e adicionado o cálculo real de "
            "caseamento. A lógica de classificação jogo×fundo foi extraída para utils/lencol_caseamento.py "
            "e agora é compartilhada com 3_Controle_de_Corte.py, para as duas telas não divergirem."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "correção",
        "title": "Realizado por semana da Previsão de Cargas agora bate exatamente com o total oficial do mês",
        "description": (
            "8_Previsao_Cargas.py e 10_Relatorios.py: quando 2+ cargas do mesmo cliente caíam no mesmo "
            "dia, cada uma herdava o valor cheio do Realizado daquele dia/cliente (a planilha só registra "
            "1 valor por dia/cliente, não por carga) — isso contava o mesmo Realizado em dobro/triplo e "
            "inflava a Aderência para mais de 150% em várias semanas. Agora o valor do dia é dividido "
            "entre as cargas que compartilham a mesma chave. Além disso, nem todo lançamento do painel "
            "diário casa por nome com uma carga (grafias diferentes, células com vários clientes somados), "
            "então a soma ficava até 19% abaixo do Realizado oficial da planilha — foi adicionada uma "
            "recalibração proporcional para que a soma de cada mês bata exatamente (diferença R$ 0,00 "
            "testada nos 6 meses) com o Realizado oficial já usado no gráfico mensal e nos KPIs da página. "
            "Adicionado aviso na tela deixando claro que a distribuição semanal é uma estimativa, mas o "
            "total mensal é exato."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "correção",
        "title": "Corrigido Realizado zerado em Jan/Fev/Mar/Abr/Maio na Previsão de Cargas",
        "description": (
            "8_Previsao_Cargas.py e 10_Relatorios.py: _extract_day_realized assumia que o painel "
            "diário de realizado sempre começava na coluna 8, mas essa posição muda por mês na planilha "
            "(col 8 em Junho, col 11 em Abril, col 9 em Maio) — nos outros meses o cabeçalho 'DD-mmm.' "
            "nunca era encontrado nessa coluna fixa e o Realizado ficava sempre zerado. Janeiro nem usa "
            "blocos de cabeçalho de dia — cada linha de cliente já carrega sua própria data na linha de "
            "carga. Adicionada detecção dinâmica da coluna (_find_painel_col) e um fallback para o "
            "formato de Janeiro (_find_painel_col_rotulo). Agora os 6 meses retornam Realizado real."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "correção",
        "title": "Corrigido Realizado fantasma por dia/cliente na Previsão de Cargas",
        "description": (
            "8_Previsao_Cargas.py: _extract_day_realized lia a coluna 'diferença' (row[11]) do "
            "painel-resumo diário em vez da coluna 'realizado' (row[10]) — e o parser de número remove "
            "o sinal de '-', então uma diferença negativa (dia sem realizado ainda, ex.: 29/06 e 30/06) "
            "virava um 'realizado' fictício igual ao previsto. Isso inflava REALIZADO_DIA em dias/clientes "
            "sem lançamento e distorcia a coluna Diferença da tabela 'Detalhe de Itens' e o novo gráfico/"
            "tabela semanal. Corrigido para ler row[10] (realizado de verdade). Havia uma cópia idêntica "
            "dessa função em 10_Relatorios.py (_extract_day_realized_cg, usada pelo PDF de Previsão de "
            "Cargas) com o mesmo bug — corrigida também."
        ),
    },
    {
        "date": "03/07/2026",
        "tag": "correção",
        "title": "Corrigido buraco em Janeiro/Maio/Junho na quebra semanal da Previsão de Cargas",
        "description": (
            "8_Previsao_Cargas.py: o gráfico e a nova tabela 'Detalhamento por Semana' agrupavam por "
            "PREVISAO, que é zerada por carga individual nos meses em que a planilha já tem um previsto "
            "oficial no painel-resumo (Janeiro, Maio, Junho) — para evitar dobrar o total mensal. Isso "
            "apagava esses meses inteiros da visão semanal, sobrando só Fevereiro-Abril. A agregação semanal "
            "agora usa VALOR_FRETE (valor do frete por carga, nunca zerado), cobrindo todos os meses. O "
            "rótulo de cada semana também deixou de usar número de semana ISO (que corta no meio do mês, "
            "gerando uma '5ª semana' artificial) e passou a usar o intervalo de datas do cabeçalho 'SEMANA "
            "DD/MM A DD/MM' da própria planilha."
        ),
    },
    {
        "date": "02/07/2026",
        "tag": "correção",
        "title": "Corrigido travamento do Controle de Corte (Lençol) e desalinhamento de colunas no relatório de email",
        "description": (
            "A planilha Lençol Arealva removeu a coluna RETALHO, o que travava a página "
            "3_Controle_de_Corte.py (exigia essa coluna) e desalinhava scripts/relatorio_diario_corte.py, "
            "que lia colunas por posição fixa — OBSERVAÇÕES virava 'Retalho' e a coluna OBS real ficava "
            "sempre vazia. RETALHO_KG/OBS agora são opcionais na página; o script de relatório passou a "
            "mapear colunas pelo nome do cabeçalho, resistindo a mudanças de estrutura na planilha."
        ),
    },
    {
        "date": "02/07/2026",
        "tag": "correção",
        "title": "Corrigido bug de data no relatório diário de corte (Manta Arealva e Lençol Arealva)",
        "description": (
            "scripts/relatorio_diario_corte.py: as planilhas Manta Arealva e Lençol Arealva usam formato "
            "americano M/D/AAAA, mas eram parseadas com dayfirst=True (formato brasileiro), invertendo dia/mês "
            "em datas ambíguas (ex.: '1/7/2026' = 7 de janeiro era lido como 1º de julho). Isso fazia o relatório "
            "puxar cortes de um dia errado (ex.: EDILSON/ERICK aparecendo em 01/07/2026 quando na verdade cortou "
            "em 07/01/2026). _parse_datas agora recebe dayfirst=False para essas duas planilhas; Manta Iacanga "
            "permanece dayfirst=True (formato brasileiro DD/MM/AA confirmado)."
        ),
    },
    {
        "date": "01/07/2026",
        "tag": "melhoria",
        "title": "Meta ponderada por produto+cliente para ZANATTA e suporte a colunas METAS 2/3 nomeadas",
        "description": (
            "metas_manager.py: detecção de colunas extras expandida para aceitar 'METAS 2'/'METAS 3' além de 'Unnamed:'; "
            "nova lógica de tabela secundária detecta FACÇÃO.1/PRODUTO.1/METAS.1/CLIENTE.1 para suportar a estrutura ZANATTA. "
            "5_Producao_Faccoes.py: ponderação de metas estendida para 4 casos — sem cliente/produto (soma direta), "
            "só produto, só cliente (CORTINA), produto+cliente (ZANATTA) — usando _qty_fac_prod_cli para peso correto."
        ),
    },
    {
        "date": "30/06/2026",
        "tag": "melhoria",
        "title": "Limpeza geral: remoção de código morto em todo o projeto",
        "description": (
            "Auditoria completa do projeto: removidos imports não utilizados (render_kpi_row em app.py, "
            "plotly.express/urllib em eficiencia_corte.py, import io inline em 3_Controle_de_Corte.py), "
            "funções mortas (pode_acessar em auth.py, _pct_bar e MESES_PT em 5_Producao_Faccoes.py), "
            "bloco __main__ de debug em faccao_loader.py. "
            "Funções _color_pct e _cor_cons unificadas em uma única função parametrizada. "
            "Imports de metas_manager.py reorganizados para o topo do arquivo."
        ),
    },
    {
        "date": "29/06/2026",
        "tag": "melhoria",
        "title": "Facções: metas da nova guia + dashboard Facção × Meta",
        "description": (
            "Metas de facções agora carregadas da guia dedicada na planilha de facções "
            "(GID 1797767576) como fonte primária, com fallback para a planilha legada. "
            "Dashboard aprimorado: gráfico de comparação direta Facção × Meta (overlay), "
            "tabela com Meta Mês, Meta Semana, % da Meta e Restante por facção. "
            "Relatório HTML reformulado com seção 'Facção × Meta' em destaque (barras de progresso visuais), "
            "contadores de facções acima/abaixo da meta e meta individual exibida no cabeçalho de cada facção. "
            "Botão de download do relatório agora visível na aba Mensal."
        ),
    },
    {
        "date": "25/06/2026",
        "tag": "novo",
        "title": "Central de Relatórios PDF (página 10)",
        "description": (
            "Criada a página Relatórios (pages/10_Relatorios.py) com geração centralizada de todos "
            "os relatórios PDF do sistema. Organizada em abas: Corte (Consolidado, Arealva Manta, "
            "Iacanga, Lençol), Produção Geral, Facções, Cargas, Carteira de Pedidos e Programação. "
            "Botões de PDF removidos das páginas individuais (2, 3, 4, 5, 8 e 9). "
            "Card 'Relatórios' adicionado à seção Controladoria da Home."
        ),
    },
    {
        "date": "25/06/2026",
        "tag": "novo",
        "title": "PDFs reais para Produção por Facção e Programação de Corte",
        "description": (
            "Substituídos os exports HTML das páginas 4 e 5 por relatórios PDF reais via ReportLab. "
            "gerar_pdf_faccoes: capa, KPIs, gráfico diário, tabela de progresso por facção/produto/empresa, "
            "gráfico top facções, detalhe diário por facção. "
            "gerar_pdf_programacao: capa, KPIs, gráfico programado vs cortado por semana, tabela de OPs "
            "com status colorido e eficiência. Ambos com header/footer automáticos e capa navy."
        ),
    },
    {
        "date": "25/06/2026",
        "tag": "melhoria",
        "title": "Metas de facção carregadas dinamicamente da planilha Google Sheets",
        "description": (
            "O dashboard Produção por Facção agora lê as metas diretamente da planilha de "
            "planejamento (SHEET_ID_METAS). Para cada (produto, cliente, facção), pega o "
            "registro PREVISTO mais recente por DATA BASE. Fallback automático para JSON local "
            "e depois para config/settings.py se a planilha estiver indisponível. "
            "Também adicionado gráfico de Produção Diária por Facção ao lado do acumulado."
        ),
    },
    {
        "date": "24/06/2026",
        "tag": "correção",
        "title": "Mapa de calor por facção: dados completos e NATHIELLY unificada",
        "description": (
            "Heatmap 'Mapa de Calor: Facção × Dia' agora usa todos os dados do período "
            "sem os filtros de produto/cliente, mostrando todos os dias de produção de cada facção. "
            "Também unificou a grafia NATHIELLY → NATCHIELLY (typo recorrente na aba QUARTERIZADAS), "
            "eliminando a linha duplicada no heatmap e em todas as análises."
        ),
    },
    {
        "date": "24/06/2026",
        "tag": "melhoria",
        "title": "Análise detalhada por facção em Produção Facções Externas",
        "description": (
            "Aba 'Por Facção' expandida com: KPIs globais, ranking com % da meta (barras coloridas), "
            "análise de consistência (regularidade e assiduidade por facção com gráficos e tabela), "
            "mapa de calor Facção × Dia, evolução acumulada por facção, mix de produtos "
            "(barras empilhadas + heatmap Produto × Facção) e tabela de detalhe com meta por linha."
        ),
    },
    {
        "date": "24/06/2026",
        "tag": "melhoria",
        "title": "Cards GUT movidos da Home para a tela de Por Colaborador",
        "description": (
            "Os cards 'Central de Controle GUT' e 'Análise de Dados GUT' foram removidos da "
            "página inicial e adicionados à tela 'Por Colaborador' em Análise de Produção, "
            "substituindo o card 'Externo' (em breve). A tela agora exibe 3 cards lado a lado: "
            "Interno, Central de Controle GUT e Análise de Dados GUT."
        ),
    },
    {
        "date": "23/06/2026",
        "tag": "melhoria",
        "title": "Aviso de carteira Sultan poluída na página Carteira de Pedidos",
        "description": (
            "Adicionado OBS de alerta logo acima da tabela 'Resumo por Cliente' informando que "
            "a carteira da Sultan contém pedidos antigos/duplicados não baixados do sistema, "
            "fazendo os volumes exibidos estarem inflados."
        ),
    },
    {
        "date": "23/06/2026",
        "tag": "correção",
        "title": "Loader de lençol não encontrava coluna OP com variações de nome",
        "description": (
            "A detecção de cabeçalho e coluna OP em lencol_loader_smart.py exigia a string exata 'OP'. "
            "Se a célula estivesse como 'N° OP', 'Nº OP' ou similar, o loader retornava vazio e "
            "toda a fonte Lençol ficava ausente — OPs registradas como 'PROG 83' mostravam QNT CORTADA = 0 "
            "mesmo com corte existente. Regex agora aceita variações (N°/Nº + espaços + ponto final). "
            "Limite de varredura ampliado de 12 para 20 colunas."
        ),
    },
    {
        "date": "23/06/2026",
        "tag": "correção",
        "title": "Corte lençol FUNDO-only não zerava mais no cruzamento",
        "description": (
            "OPs do CORTE LENÇOL cujo produto é exclusivamente FUNDO (ex: CORTTEX OP 83) "
            "apareciam com QNT CORTADA = 0 mesmo com corte registrado. O filtro _is_lencol_fundo "
            "excluía todos os registros para evitar dupla-contagem CIMA+FUNDO nos jogos, mas "
            "eliminava também pedidos legítimos de só-FUNDO. Agora o filtro só exclui registros "
            "FUNDO quando a mesma OP também possui registros não-FUNDO (CIMA)."
        ),
    },
    {
        "date": "23/06/2026",
        "tag": "melhoria",
        "title": "Metas de produção por facção ampliadas",
        "description": (
            "Adicionadas 36 novas entradas em METAS_FACCOES cobrindo ZANATTA (BURDAYS, FORTEX, SULTAN, CORTTEX), "
            "PREVITTEX e ZARO TEXTIL (CORTTEX, SULTAN), MARCIA GONÇALVES / VANIA CONFECÇÕES / FRANCIELE LOPES (CAMESA), "
            "RUTE ZANATTEX (BURDAYS, CAMESA, CORTTEX), KELLY/SHERPA (BURDAYS), ZANATTEX(RUTE)/ZARO/MEGA PREVEN (MARCELINO). "
            "Nova seção FORTEX adicionada. Meta de CAROL MENDES/MANTA PRENSADA/CAMESA atualizada para 4 000/dia. "
            "Alias 'JOGO CAMA' → 'JOGOS DUPLOS' incluído."
        ),
    },
    {
        "date": "22/06/2026",
        "tag": "correção",
        "title": "Realizado por cliente corrigido em Previsão de Cargas",
        "description": (
            "_extract_day_realized() agora indexa por (data, cliente_norm) ao invés de só (data). "
            "Antes, o total do dia era repetido em cada cargo individual — agora cada cargo "
            "recebe o valor correto do painel direito da planilha."
        ),
    },
    {
        "date": "22/06/2026",
        "tag": "melhoria",
        "title": "Filtro de período por intervalo de datas em Facções",
        "description": (
            "Substituídos seletores de Mês/Ano por date_input de intervalo em pages/5. "
            "Todos os filtros (df_mes, df_mp, df_mes_fac) e cálculos de dias úteis "
            "passam a usar data_ini/data_fim. Default: 1º do mês atual → hoje."
        ),
    },
    {
        "date": "22/06/2026",
        "tag": "correção",
        "title": "Corrigido erro de layout duplicado no gráfico de barras empilhadas",
        "description": (
            "Corrigido TypeError no update_layout do gráfico de barras por produto/facção: "
            "DARK_LAYOUT já continha a chave 'legend', causando conflito ao passá-la novamente. "
            "Separado em dois update_layout consecutivos."
        ),
    },
    {
        "date": "22/06/2026",
        "tag": "melhoria",
        "title": "Metas de facção atualizadas por prestador e setor",
        "description": (
            "METAS_FACCOES substituído: 32 entradas por prestador/setor com metas mensais e semanais reais. "
            "FACCOES_PRODUTO_ALIAS atualizado com nomes canônicos novos: FRONHA AVULSA, COBERTOR BABY, "
            "COBERTOR VELOUR, JOGOS DUPLOS, JOGOS SIMPLES, JG PONTO PALITO, FRONHA PONTO PALITO."
        ),
    },
    {
        "date": "20/06/2026",
        "tag": "correção",
        "title": "Previsão de Cargas: realizado por dia corrigido no PDF",
        "description": (
            "Corrigido parser do painel direito do CSV (_extract_day_realized): "
            "col[11] contém o valor de realizado diretamente (sem prefixo 'R$' separado), "
            "e linhas de separador/total (col[8] vazio ou com 'R$') são ignoradas. "
            "A coluna 'Realizado Dia (R$)' no PDF agora exibe os valores corretos."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "melhoria",
        "title": "PDF Previsão de Cargas: coluna Realizado por dia",
        "description": (
            "Adicionada coluna 'Realizado Dia (R$)' no Detalhe de Registros do PDF. "
            "O valor é extraído do painel direito da planilha (soma dos realizados de "
            "todos os clientes no mesmo dia). A coluna 'Frete' foi renomeada para 'Previsto'. "
            "Dias sem lançamento exibem '—'."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "correção",
        "title": "Previsão de Cargas: PREVISÃO TOTAL corrigido para R$ 2.450.000",
        "description": (
            "Corrigido PREVISÃO TOTAL (antes mostrava soma dos fretes individuais = R$3.390.000). "
            "A detecção da linha de resumo agora procura a linha sem data que tenha dois valores "
            "> R$1,5M — padrão exclusivo da linha 'Previsto total | Realizado total' da planilha. "
            "A abordagem anterior (busca por texto 'Previsto') disparava falso positivo nos cabeçalhos "
            "de dias ('previsto'), retornando valor errado antes de alcançar o resumo."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "novo",
        "title": "Relatório Mensal Consolidado — todos os cortes",
        "description": (
            "Botão 'Gerar Relatório Mensal — Todos os Cortes' adicionado à tela de seleção "
            "de região (página 3). Gera automaticamente um PDF com seções para Arealva Manta, "
            "Arealva Lençol, Iacanga e Itaju cobrindo o mês atual: KPIs, gráfico diário e "
            "tabela por estação/prestador para cada região."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "melhoria",
        "title": "PDF: Meta do Período e % Atingido na tabela de Facções",
        "description": (
            "Na tabela 'Produção por Facção / Produto' do relatório PDF de Produção Geral, "
            "adicionadas duas colunas: 'Meta Período' (meta diária × dias úteis do intervalo) "
            "e '% Ating.' (produção real ÷ meta), com cor verde/âmbar/vermelho por desempenho."
        ),
    },
    {
        "date": "19/06/2026",
        "tag": "melhoria",
        "title": "Botão 'Filtros' em todos os dashboards",
        "description": (
            "Adicionado botão 'Filtros' no topo do conteúdo principal de todos os dashboards "
            "(Corte, Produção Geral, Facções, Previsão de Cargas, Programação, Carteira de Pedidos, "
            "Plano de Metas e Histórico). Ao clicar, abre a sidebar automaticamente — facilita o uso "
            "para usuários menos familiarizados com a interface."
        ),
    },
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
