# 📋 Integração dos Dashboards - Guia Completo

## 🎯 Status da Integração

✅ **Dashboard Corte** - Integrado com sucesso  
✅ **Dashboard Produção** - Integrado com sucesso  
✅ **Dashboard Faturamento** - Integrado com sucesso

---

## 📊 Estrutura de Setores

### 1️⃣ Corte (✂️)

- **Arquivo:** `sectors/corte.py`
- **Google Sheet ID:** `1iGj4-vknwzepbrHdRz1PwisZU2foU7aW`
- **Carregamento:** CSV export automático (primeira aba)
- **Funcionalidades:**
  - Filtros e ordenação de dados
  - Visualização de registros processados
  - Download de dados completos ou filtrados
  - Estatísticas básicas

### 2️⃣ Produção (🏭)

- **Arquivo:** `sectors/producao.py`
- **Google Sheet ID:** `15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y`
- **Carregamento:** CSV export automático (primeira aba)
- **Funcionalidades:**
  - 3 Abas de análise (Visão Geral, Detalhes, Dados)
  - Agrupamento de dados por coluna
  - Gráficos de distribuição
  - Filtros avançados

### 3️⃣ Faturamento (📈)

- **Arquivo:** `sectors/faturamento.py`
- **Google Sheet ID:** `1tpQmqkinlA4AscPI8kIkmm5DGD9Jw_wHb-5sy5itSGg`
- **Carregamento:** CSV export com GID específico (1255712550)
- **Funcionalidades:**
  - 4 Abas (Dashboard, Dados, Filtros, Exportar)
  - Gráficos interativos (barras, histogramas)
  - Estatísticas descritivas
  - Análises de KPIs
  - Design moderno com gradientes

---

## 🔄 Fluxo de Carregamento de Dados

```
┌─────────────────────────────────────────┐
│ app.py (Aplicação Principal)            │
│ - Gerencia estado da navegação          │
│ - Renderiza página inicial              │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ pages/home.py (Seleção de Setores)      │
│ - Exibe cards de setores                │
│ - Define sector em session_state        │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ sectors/[corte|producao|faturamento].py │
│ - Dashboard específico do setor         │
│ - Carrega dados do Google Sheets        │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Google Sheets (via CSV export)          │
│ - Dados em tempo real                   │
│ - Múltiplas estratégias de fallback     │
└─────────────────────────────────────────┘
```

---

## 🚀 Como Executar

### 1. Ativar Ambiente Virtual

```powershell
# Se não tiver criado ainda
python -m venv venv

# Ativar
.\venv\Scripts\Activate.ps1
```

### 2. Instalar Dependências

```powershell
pip install -r requirements.txt
```

### 3. Executar a Aplicação

```powershell
streamlit run app.py
```

A aplicação abrirá em `http://localhost:8501`

---

## 📥 Como os Dados são Carregados

### Método: CSV Export via URL

Cada dashboard carrega dados usando URLs de export do Google Sheets:

```python
# URL base sem GID (carrega primeira aba)
https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv

# URL com GID específico (opcional)
https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}
```

### Estratégia de Fallback

Se uma URL falhar, o código tenta automaticamente múltiplas alternativas:

1. **URL 1:** Export CSV padrão
2. **URL 2:** Google Visualization Query (gviz)
3. **URL 3:** Export com GID específico
4. **URL 4:** gviz com GID específico

Isso garante máxima compatibilidade e resiliência.

---

## 🔧 Customizações Possíveis

### Adicionar um Novo Setor

1. **Crie arquivo** `sectors/novo_setor.py`:

```python
from pages.dashboard_base import DashboardBase

class NovoSetorDashboard(DashboardBase):
    def render_dashboard(self):
        self.render_header()
        df = self.load_data()
        # Sua lógica aqui...

def render():
    dashboard = NovoSetorDashboard("novo_setor")
    dashboard.render_dashboard()
```

2. **Atualize** `config.py`:

```python
SHEETS_CONFIG = {
    # ... existentes
    "novo_setor": {
        "sheet_id": "SEU_SHEET_ID",
        "sheet_gid": None,
        "icon": "🎯",
        "descrição": "Descrição do setor"
    },
}
```

3. **Atualize** `sectors/__init__.py`:

```python
from .novo_setor import render as render_novo_setor
__all__ = [..., "render_novo_setor"]
```

4. **Atualize** `app.py` (roteamento):

```python
elif sector == "novo_setor":
    render_novo_setor()
```

### Customizar Cores

Edite `config.py`:

```python
"seu_setor": {
    "cor_primaria": "#FF6B6B"  # Adicione esta linha
}
```

Use em CSS conforme necessário nos dashboards.

---

## 🐛 Troubleshooting

### "Erro ao carregar dados"

**Causa:** Sheet ID incorreto ou planilha não compartilhada

**Solução:**

1. Verifique o Sheet ID na URL
2. Compartilhe a planilha publicamente ou com a conta de serviço
3. Verifique o nome da aba (se estiver usando sheet_name)

### "Dados vazios"

**Causa:** Planilha vazia ou formação incorreta

**Solução:**

1. Verifique se a planilha tem dados
2. Certifique-se que não tem linhas vazias no meio dos dados
3. Primeira linha deve conter cabeçalhos

### "Dashboard não renderiza"

**Causa:** Importação faltando ou erro no código

**Solução:**

1. Verifique imports em `app.py`
2. Verifique se o arquivo está em `sectors/`
3. Rode `streamlit run app.py` novamente

---

## 📊 Dados Esperados

Cada planilha deve seguir este formato:

| Coluna 1 | Coluna 2 | Coluna 3 |
| -------- | -------- | -------- |
| Valor A  | Valor B  | Valor C  |
| Valor A  | Valor B  | Valor C  |

**Regras:**

- ✅ Primeira linha = cabeçalhos
- ✅ Sem linhas/colunas vazias no meio
- ✅ Sem caracteres especiais problemáticos
- ✅ Números sem formatação extra

---

## 🎨 Temas Disponíveis

- **Corte:** Tema claro com azul primário
- **Produção:** Tema claro com turquesa
- **Faturamento:** Tema claro com verde-azul

Customize em `utils/styling.py` ou diretamente no arquivo do setor.

---

## 📈 Performance

- **Cache:** 5 minutos por padrão (ajustável em `config.py`)
- **Tamanho máximo:** Recomendado até 100k linhas
- **Timeout:** 10 segundos para carregamento

Para melhor performance:

1. Limite registros na visualização
2. Use filtros para reduzir dados
3. Agregue dados grandes em sumários

---

## 🔐 Segurança

- Sheet IDs são públicos (OK, é só ID)
- Não compartilhe chaves/tokens no código
- Use `.env` para configurações sensíveis
- Adicione ao `.gitignore`

---

## 📞 Suporte

Para problemas:

1. Verifique [SETUP.md](SETUP.md)
2. Verifique [DOCUMENTACAO.md](DOCUMENTACAO.md)
3. Consulte documentação Streamlit: https://docs.streamlit.io/

---

**Data de integração:** 14 de maio de 2026  
**Versão:** 1.0 Unificada  
**Status:** ✅ Pronto para Produção
