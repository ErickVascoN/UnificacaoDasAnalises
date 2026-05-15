# Dashboard Unificado

Aplicação Streamlit que centraliza os três dashboards da operação em uma única
interface multipágina, com página inicial (Home) e navegação por setor.

## Setores integrados

- **📦 Produtos Faturados** — Análise comercial e faturamento
- **🏭 Produção Geral** — Acompanhamento multi-empresas
- **✂️ Controle de Corte** — Mantas, estações e desempenho

> Cada dashboard foi preservado **exatamente** como o original. A unificação
> apenas adiciona a Home e organiza os dashboards como páginas do Streamlit.

## Estrutura

```
DashboardUnificado/
├── app.py                          # Página inicial (Home)
├── config.py                       # Configurações do dashboard de Corte
├── gid_detector.py                 # Utilitário do dashboard de Corte
├── planilha_producao.xlsx          # Fallback local (Produção Geral)
├── requirements.txt
├── README.md
├── Abrir Dashboard.bat             # Atalho Windows
├── .streamlit/
│   └── config.toml                 # Tema unificado
└── pages/
    ├── 1_📦_Produtos_Faturados.py
    ├── 2_🏭_Producao_Geral.py
    └── 3_✂️_Controle_de_Corte.py
```

## Como executar

1. Crie e ative um ambiente virtual (recomendado):

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Rode a aplicação a partir da raiz do projeto:

   ```bash
   streamlit run app.py
   ```

4. O navegador abrirá em `http://localhost:8501`. Use o menu lateral
   esquerdo ou os cards da Home para navegar entre os setores.

## Paleta de cores

A Home utiliza um tema escuro elegante que harmoniza com os três dashboards:

- Fundo profundo `#0E1117` (base Produção Geral)
- Destaque turquesa `#4ECDC4` (Produção Geral)
- Azul marinho `#1D3557` (Faturados)
- Coral `#E76F51` e dourado `#F4A261` (Faturados)
- Azul claro `#45B7D1` (Corte)

Cada dashboard mantém **sua própria paleta interna** (light/dark) — apenas a
Home foi estilizada para servir como hub.

## Observações

- As páginas usam `st.set_page_config` e seu próprio CSS — Streamlit suporta
  isso em apps multipage.
- Os dashboards continuam consumindo dados diretamente do Google Sheets.
- `planilha_producao.xlsx` serve como fallback local para o dashboard de
  Produção Geral.
