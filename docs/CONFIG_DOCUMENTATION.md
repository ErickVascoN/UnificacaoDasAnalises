"""
⚙️ CONFIG_DOCUMENTATION - Referência de Configurações

Este arquivo documenta todas as configurações do projeto e como usá-las.
Para modificar valores, edite config/settings.py.

Seções:

1. Cache TTL - Tempos de vida do cache
2. Google Sheets IDs - Identificadores de planilhas
3. Autenticação - Senhas e validações
4. Validação - Checklist de valores esperados
5. Troubleshooting - Soluções para problemas comuns
   """

# ──────────────────────────────────────────────────────────────

# 1. CACHE TTL (Time To Live)

# ──────────────────────────────────────────────────────────────

"""
Configuração: @st.cache_data(ttl=CACHE_TTL)

Os tempos de cache são críticos para performance:

CORTE_CACHE_TTL = 60 segundos

- Dashboard: 3_Controle_de_Corte.py
- Dados: Arealva Manta (corte)
- Frequência de atualização: Cada minuto
- Razão: Dados críticos, atualizações frequentes

IACANGA_CACHE_TTL = (não definido no settings.py, usa padrão)

- Dashboard: Iacanga (corte)
- Dados: Mantas Iacanga
- Frequência de atualização: Similar ao Arealva

FATURAMENTO_CACHE_TTL = 300 segundos (5 minutos)

- Dashboard: 1_Produtos_Faturados.py
- Dados: Produtos faturados
- Frequência de atualização: Menos frequente

PRODUCAO_CACHE_TTL = 120 segundos (2 minutos)

- Dashboard: 2_Producao_Geral.py
- Dados: Produção geral
- Frequência de atualização: Média

LENCOL_CACHE_TTL = 3600 segundos (1 hora)

- Dashboard: 3_Controle_de_Corte.py - Seção Arealva Lençol
- Dados: Corte de lençol
- Frequência de atualização: Uma vez por hora
- Razão: Planilha de consulta menos crítica

NOTA: Se dados não aparecerem atualizados:

1. Aumente o TTL (cache dura mais tempo)
2. Ou reduzca o TTL (cache expira mais rápido)
3. Ou force refresh com st.cache_data.clear_cache()
   """

# ──────────────────────────────────────────────────────────────

# 2. GOOGLE SHEETS IDS

# ──────────────────────────────────────────────────────────────

"""
Estrutura: "ID_DA_PLANILHA" + "\_GID" = Sheet ID + GID de abas

Cada entrada tem:

- SHEETS_ID: Identificador global da planilha
- SHEETS_GID: Identificador da aba específica (gid)

CORTE (Arealva Manta):
ID: 1iGj4-vknwzepbrHdRz1PwisZU2foU7aW
GID: 1544210185

URL: https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}

IACANGA (Mantas):
ID: 14OFOAxrV_DkyrwG6KG8NZT-PeXUV4jezPrPO90rh1DU
GID: 1362699684

FATURAMENTO (Produtos):
ID: 1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg
GID: 1255712550

PRODUCAO (Geral):
ID: 15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y
(sem GID = usa aba padrão)

LENCOL (Arealva Lençol) - em 3_Controle_de_Corte.py:
ID: 1lT_HKBDfDLFNUvwh1oOKfSZy2_kNaP0eoSqLmCaKZbQ
GID: 0 (aba padrão)

PARA ADICIONAR NOVA FONTE:

1. Abra a planilha no Google Sheets
2. URL format: https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}
3. Copie o ID e GID
4. Adicione em config/settings.py
5. Use em data loading function
   """

# ──────────────────────────────────────────────────────────────

# 3. AUTENTICAÇÃO

# ──────────────────────────────────────────────────────────────

"""
Dois níveis de acesso definidos em config/settings.py:

SENHA_USUARIO = "0102"

- Acesso: Visualização de dashboards
- Restrições: Sem edição, sem dados sensíveis

SENHA_ADMIN = "adm0102"

- Acesso: Tudo
- Restrições: Nenhuma (apenas use em produção segura)

IMPLEMENTAÇÃO:

- Verificado em app.py antes de carregar dashboards
- Use st.secrets para produção (não em código)
- Suporta múltiplos usuários (adicione em futuro)

TODO: Integrar com autenticação segura

- OAuth2 / SSO
- Banco de dados de usuários
- Logs de acesso
  """

# ──────────────────────────────────────────────────────────────

# 4. METAS E LIMITES

# ──────────────────────────────────────────────────────────────

"""
CORTE_METAS (Por máquina/mesa):
{
"MAQUINA": 7000, # peças/dia
"MESA 1": 4000, # peças/dia
"MESA 2": 3000, # peças/dia
}

CORTE_META_TOTAL = sum(CORTE_METAS.values()) = 14000 peças/dia

COMO USAR:
from config.settings import CORTE_METAS

for estacao, meta in CORTE_METAS.items():
print(f"{estacao}: {meta} peças")

TODO: Metas por facção/período

- Adicionar metas por mês
- Adicionar ajustes sazonais
- Adicionar histórico de metas
  """

# ──────────────────────────────────────────────────────────────

# 5. CHECKLIST DE VALIDAÇÃO

# ──────────────────────────────────────────────────────────────

"""
Antes de mudar configurações, valide:

✓ Google Sheets IDs estão corretos
→ Teste: Abra URL no navegador, confirma CSV
→ Se erro 404: ID ou GID está errado

✓ Caches não estão muito altos
→ Se dados atrasados: Reduzir TTL
→ Se muitos loads: Aumentar TTL

✓ Autenticação funcionando
→ Teste: Tente senhas erradas (deve falhar)
→ Teste: Tente senha correta (deve passar)

✓ Sem senhas em código
→ Em produção: Use st.secrets ou variáveis ambiente
→ Não faça git commit de senhas

✓ Dados parseando corretamente
→ Use: data*integrity_checks.validate*\*()
→ Verifique: Datas, quantidades, valores
"""

# ──────────────────────────────────────────────────────────────

# 6. TROUBLESHOOTING

# ──────────────────────────────────────────────────────────────

"""
PROBLEMA: "❌ Falha ao baixar CSV do Google Sheets"
CAUSAS:

1. ID ou GID incorretos em settings.py
2. Planilha não é compartilhada (permissions)
3. Internet offline
4. Google Sheets fora do ar
   SOLUÇÕES:
   → Validar URLs com curl/Postman
   → Compartilhar planilha com "Anyone with link can view"
   → Adicionar retry logic com timeout maior
   → Ver logs em pages/\*.py com st.debug()

PROBLEMA: "Dados não aparecerem atualizados"
CAUSAS:

1. Cache TTL muito alto
2. st.cache_data não foi limpo
3. Dados não mudaram na fonte
   SOLUÇÕES:
   → Reduzir CACHE_TTL em settings.py
   → st.cache_data.clear_cache()
   → Verificar: write to Google Sheets funcionando

PROBLEMA: "Parsing de data quebrado (ambíguas)"
CAUSAS:

1. Formato misturado (DD/MM vs MM/DD)
2. format='mixed' recursion (MÉDIO #14 resolvido)
   SOLUÇÕES:
   → Usar dayfirst=True (padrão)
   → Normalizar formato na origem
   → Ver: lencol_parse_date() em 3_Controle_de_Corte.py

PROBLEMA: "Quantidades negativas"
CAUSAS:

1. Dados digitados errado
2. Devolução/ajuste de quantidade
   SOLUÇÕES:
   → Validar com data_integrity_checks
   → Investigar registro específico
   → Adicionar campo de motivo na planilha
   """

# ──────────────────────────────────────────────────────────────

# 7. REFERÊNCIAS

# ──────────────────────────────────────────────────────────────

"""
📚 DOCUMENTAÇÃO RELACIONADA:

- AUDITORIA_QUALIDADE_DADOS.md
  → 28 problemas identificados e soluções

- COLUMN_STANDARDS.py
  → Normalização de nomes de coluna
  → Padrões de coluna entre dashboards

- data_integrity_checks.py
  → Validação de integridade de dados
  → Relatórios de qualidade

- RESUMO_TRABALHO_CONCLUIDO.md
  → Histórico de correções e commits
  → Próximas ações prioritárias

🔧 COMO ADICIONAR NOVA CONFIGURAÇÃO:

1. Edite config/settings.py
2. Adicione comentário explicativo
3. Teste em um dashboard (import e use)
4. Commit com mensagem descritiva
5. Documente em CONFIG_DOCUMENTATION.md

⚡ PERFORMANCE TIPS:

- Cache agressivo para dados estáticos (TTL alto)
- Cache moderado para dados que mudam pouco
- Sem cache para dados críticos em tempo real
- Use @st.cache_data, não @st.cache (deprecated)
- Clear cache manualmente com st.cache_data.clear_cache()
  """

# ──────────────────────────────────────────────────────────────

# EXEMPLO DE USO

# ──────────────────────────────────────────────────────────────

"""

# Em qualquer dashboard:

from config.settings import (
PAGE_CONFIG,
CORTE_METAS,
FATURAMENTO_CACHE_TTL,
FATURAMENTO_SHEETS_ID,
)
import streamlit as st

# Configurar página

st.set_page_config(\*\*PAGE_CONFIG)

# Usar em cache decorator

@st.cache_data(ttl=FATURAMENTO_CACHE_TTL)
def load_data(): # carregar usando FATURAMENTO_SHEETS_ID
pass

# Usar em lógica

for estacao, meta in CORTE_METAS.items():
st.metric(estacao, meta)
"""
