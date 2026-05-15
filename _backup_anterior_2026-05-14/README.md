# Dashboard Unificado - Análise de Setores

Plataforma centralizada de análise de dados por setor (Corte, Produção, Faturamento e mais) com integração em tempo real com Google Sheets.

## 🎯 Setores Disponíveis

- ✂️ **Corte** - Análise de dados do setor de corte
- 🏭 **Produção** - Análise de dados de produção geral
- 📈 **Faturamento** - Análise de produtos faturados

## ⚙️ Arquitetura

```
projeto/
├── app.py                          # Aplicação principal Streamlit
├── config.py                       # Configurações centralizadas
├── requirements.txt                # Dependências do projeto
├── pages/
│   ├── home.py                    # Página inicial (seleção de setor)
│   └── dashboard_base.py          # Template base para dashboards
├── sectors/
│   ├── corte.py                   # Dashboard Corte
│   ├── producao.py                # Dashboard Produção
│   └── faturamento.py             # Dashboard Faturamento
└── utils/
    ├── google_sheets.py           # Integração com Google Sheets
    └── styling.py                 # Temas e estilos
```

## 🚀 Quick Start

### 1. Instalar Dependências

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Executar

```bash
streamlit run app.py
```

## 📚 Documentação

- [SETUP.md](SETUP.md) - Guia de configuração inicial
- [INTEGRACAO.md](INTEGRACAO.md) - Detalhes sobre integração dos dashboards
- [DOCUMENTACAO.md](DOCUMENTACAO.md) - Documentação técnica avançada

## ✨ Características

✅ **Página Inicial Interativa** com seleção visual de setores  
✅ **Múltiplos Dashboards** Corte, Produção e Faturamento  
✅ **Integração Google Sheets** em tempo real  
✅ **Design Profissional** responsivo e moderno  
✅ **Filtros e Análises** customizáveis por setor  
✅ **Exportação de Dados** em CSV  
✅ **Cache Inteligente** para otimizar performance

## 🔄 Fluxo de Dados

Google Sheets → CSV Export → Dashboard → Visualizações

Cada dashboard carrega dados automaticamente via URLs de export, com múltiplas estratégias de fallback para garantir resiliência.

## 🛠️ Adicionar Novo Setor

1. Crie arquivo em `sectors/novo_setor.py`
2. Atualize `config.py` com dados do setor
3. Atualize `sectors/__init__.py` com import
4. Atualize roteamento em `app.py`

Veja [INTEGRACAO.md](INTEGRACAO.md) para detalhes.

## 📊 Dados Esperados

Suas planilhas Google Sheets devem ter:

- Primeira linha com cabeçalhos
- Sem linhas ou colunas vazias no meio
- Dados estruturados e limpos

## 🔐 Segurança

- Configurações sensíveis em `.env` (não versionado)
- Sheet IDs públicos (apenas ID, sem dados sensíveis)
- Use `.gitignore` para arquivos confidenciais

## 📞 Suporte

Consulte:

- [SETUP.md](SETUP.md) para problemas de instalação
- [INTEGRACAO.md](INTEGRACAO.md) para problemas de dados
- Documentação Streamlit: https://docs.streamlit.io/

---

**Versão:** 1.0 Unificada  
**Status:** ✅ Pronto para Produção  
**Data:** 14 de maio de 2026
