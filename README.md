# Central de Análise Zanattex

Aplicação **Streamlit** que centraliza os dados operacionais e comerciais da Zanattex
e do Grupo Giattex em uma única interface multipágina, com página inicial (Home) e
navegação por setor. Os dados vêm direto do **Google Sheets** (exportação CSV), sem
banco de dados intermediário.

> 📖 Documentação completa do projeto no **GUIA.md** (local — contém dados sensíveis,
> fora do versionamento) · padrões da camada de dados em **[PADROES.md](PADROES.md)**.

## Dashboards integrados

- **📦 Produtos Faturados** — Análise comercial e faturamento *(admin)*
- **🏭 Produção** — Por empresa + por colaborador (interno: Littex, Jogo, Fronha, Cortina)
- **✂️ Controle de Corte** — Manta Arealva, Iacanga e Lençol (com caseamento Jogo × Fundo e relatórios PDF)
- **🗂️ Programação de Corte** — Planejado × realizado por OP
- **🎯 Plano de Metas** — Metas × produção real e previsão de custos

## Estrutura

```
app.py                          # Página inicial (Home)
config/                         # Configurações: settings, sectors, changelog
pages/                          # Dashboards (1, 2, 3, 4, 7)
components/                     # Hero, KPIs, cards, sidebar, eficiência de corte
utils/                          # Loaders, cache, parser de datas, normalização, PDF
styles/                         # CSS da Home e temas
scripts/                        # Script de e-mail (relatório diário de corte)
data/                           # Fallback local (planilha_producao.xlsx)
GUIA.md  ·  PADROES.md          # Documentação
```

## Como executar

1. Crie e ative um ambiente virtual (recomendado):

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Rode a aplicação a partir da raiz do projeto:

   ```bash
   streamlit run app.py
   ```

4. O navegador abrirá em `http://localhost:8501`. Use o menu lateral esquerdo ou os
   cards da Home para navegar entre os setores.

> No Windows há também o atalho **`Abrir Dashboard.bat`**.

## Acesso

O acesso é controlado por senha digitada na Home, em dois níveis:

- **Usuário** — todos os dashboards, exceto Faturamento
- **Admin** — acesso total

As senhas ficam em `config/settings.py`. Veja o `GUIA.md` (documentação local) para
detalhes de autenticação, configuração de planilhas, metas e cache.

## Observações

- Cada dashboard usa `st.set_page_config` e seu próprio CSS — suportado em apps multipage.
- Os dashboards consumem dados diretamente do Google Sheets (as planilhas precisam estar
  com compartilhamento público para o download via CSV funcionar).
- `data/planilha_producao.xlsx` serve como fallback local para o dashboard de Produção.
- O botão **🔄 Limpar Cache** nas sidebars força a atualização imediata dos dados.
