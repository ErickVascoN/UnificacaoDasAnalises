# 📚 Documentação Avançada - Dashboard Unificado

## Índice

1. [Arquitetura do Projeto](#arquitetura)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Exemplos de Customização](#exemplos)
4. [Performance e Cache](#performance)
5. [Deployment](#deployment)

---

## 🏗️ Arquitetura do Projeto {#arquitetura}

### Fluxo de Dados

```
Google Sheets (Fonte de Dados)
         ↓
google_sheets.py (Carregamento)
         ↓
cache.py (Cache Local)
         ↓
dashboard_base.py (Template)
         ↓
sectors/*.py (Customização)
         ↓
Streamlit (Renderização)
         ↓
Browser (Usuário)
```

### Componentes Principais

| Arquivo                   | Propósito                     |
| ------------------------- | ----------------------------- |
| `app.py`                  | Entrada principal, roteamento |
| `config.py`               | Configurações centralizadas   |
| `pages/home.py`           | Página inicial                |
| `pages/dashboard_base.py` | Template base                 |
| `sectors/*.py`            | Dashboards específicos        |
| `utils/google_sheets.py`  | Integração com Sheets         |
| `utils/styling.py`        | Estilos e temas               |

---

## 📊 Estrutura de Dados {#estrutura-de-dados}

### Formato Esperado

Suas planilhas Google Sheets devem seguir este padrão:

| Data       | Produto | Quantidade | Valor | Status    |
| ---------- | ------- | ---------- | ----- | --------- |
| 2024-01-01 | Item A  | 100        | 1000  | Concluído |
| 2024-01-02 | Item B  | 150        | 1500  | Concluído |

**Regras:**

- Primeira linha contém cabeçalhos
- Sem linhas ou colunas vazias entre dados
- Datas em formato padrão (YYYY-MM-DD)
- Números sem formatação especial

---

## 🎨 Exemplos de Customização {#exemplos}

### Exemplo 1: Adicionar Gráfico de Vendas

Arquivo: `sectors/vendas.py`

```python
import streamlit as st
import pandas as pd
import plotly.express as px
from pages.dashboard_base import DashboardBase

class VendasDashboard(DashboardBase):
    def render_dashboard(self):
        self.render_header()

        df = self.load_data()
        if df.empty:
            st.error("Sem dados")
            return

        # Gráfico de Vendas por Produto
        fig_vendas = px.bar(
            df.groupby('Produto')['Valor'].sum().reset_index(),
            x='Produto',
            y='Valor',
            title='Vendas por Produto',
            color='Valor',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_vendas, use_container_width=True)

        # Evolução Temporal
        df['Data'] = pd.to_datetime(df['Data'])
        fig_evolucao = px.line(
            df.groupby('Data')['Valor'].sum().reset_index(),
            x='Data',
            y='Valor',
            title='Evolução de Vendas',
            markers=True
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

def render():
    dashboard = VendasDashboard("vendas")
    dashboard.render_dashboard()
```

### Exemplo 2: Adicionar Filtros Interativos

```python
def render_dashboard(self):
    self.render_header()
    df = self.load_data()

    # Filtros na sidebar
    with st.sidebar:
        produto_selecionado = st.multiselect(
            "Selecione Produtos:",
            df['Produto'].unique()
        )

        data_inicio = st.date_input("Data Início:")
        data_fim = st.date_input("Data Fim:")

    # Aplicar filtros
    df_filtrado = df[
        (df['Produto'].isin(produto_selecionado)) &
        (df['Data'] >= data_inicio) &
        (df['Data'] <= data_fim)
    ]

    st.dataframe(df_filtrado, use_container_width=True)
```

### Exemplo 3: Adicionar Métricas KPI

```python
def render_metrics(self, df: pd.DataFrame):
    col1, col2, col3, col4 = st.columns(4)

    total_vendas = df['Valor'].sum()
    media_vendas = df['Valor'].mean()
    max_vendas = df['Valor'].max()
    quantidade = len(df)

    with col1:
        st.metric("Total de Vendas", f"R$ {total_vendas:,.2f}")

    with col2:
        st.metric("Média por Item", f"R$ {media_vendas:,.2f}")

    with col3:
        st.metric("Máximo", f"R$ {max_vendas:,.2f}")

    with col4:
        st.metric("Quantidade", f"{quantidade:,}")
```

---

## ⚡ Performance e Cache {#performance}

### Usando Cache para Otimizar

```python
import streamlit as st
import pandas as pd
from config import CACHE_DURATION

# Cache padrão (5 minutos)
@st.cache_data(ttl=CACHE_DURATION)
def load_dados():
    # Carregamento pesado aqui
    return df

# Cache com refresh manual
@st.cache_data
def load_dados_manual():
    return df

# Para limpar cache
if st.button("Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()
```

### Otimizações de Performance

1. **Use `@st.cache_data`** para dados que não mudam frequentemente
2. **Limite o número de linhas** exibidas por padrão
3. **Lazy loading** para gráficos
4. **Paginate** grandes datasets

---

## 🚀 Deployment {#deployment}

### Opção 1: Streamlit Cloud (Grátis)

1. Suba o projeto para GitHub
2. Acesse https://share.streamlit.io/
3. Conecte seu repositório
4. Configure as variáveis de ambiente (SHEET_IDs, credenciais)

### Opção 2: Heroku

```bash
# Instale Heroku CLI
# Crie arquivo Procfile:
echo "web: streamlit run app.py" > Procfile

# Deploy
heroku login
heroku create seu-app-unificado
git push heroku main
```

### Opção 3: Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

```bash
docker build -t dashboard-unificado .
docker run -p 8501:8501 dashboard-unificado
```

---

## 🔐 Segurança

### Boas Práticas

1. **Nunca commit credenciais:**
   - Use `.env` e `.gitignore`
   - Configure no servidor via variáveis de ambiente

2. **Permissões no Google Cloud:**
   - Use contas de serviço com permissões mínimas
   - Revise regularmente

3. **Validação de Dados:**
   ```python
   def validar_dados(df):
       if df.empty:
           raise ValueError("DataFrame vazio")
       if not all(col in df.columns for col in ['Data', 'Valor']):
           raise ValueError("Colunas obrigatórias ausentes")
       return True
   ```

---

## 📝 Estrutura de Dados Adicional

### Campos Recomendados por Setor

**Corte:**

- Data, Produto, Quantidade, Metragem, Operador, Status

**Produção:**

- Data, Linha, Máquina, Unidades, Tempo, Eficiência

**Vendas:**

- Data, Cliente, Produto, Quantidade, Valor, Vendedor

---

## 🎯 Próximos Passos

1. Configure suas planilhas Google Sheets
2. Adicione novos setores conforme necessário
3. Customize gráficos e métricas
4. Faça deploy em produção
5. Recolha feedback dos usuários

---

Última atualização: 2024
