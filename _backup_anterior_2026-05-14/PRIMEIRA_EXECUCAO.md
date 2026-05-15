# 🚀 PRIMEIRA EXECUÇÃO - Passo a Passo

## ⚡ Quick Start (5 minutos)

### 1️⃣ Abrir PowerShell

```powershell
# Navegue até a pasta do projeto
cd "c:\Users\erick\OneDrive\Área de Trabalho\Trabalho\Projeto Unificação dos Dados"
```

### 2️⃣ Ativar Ambiente Virtual

```powershell
# Se ainda não criou:
python -m venv venv

# Ativar:
.\venv\Scripts\Activate.ps1

# Se tiver erro de política, execute como ADMIN e rode:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3️⃣ Instalar Dependências

```powershell
pip install -r requirements.txt
```

⏱️ Pode levar 2-3 minutos na primeira execução

### 4️⃣ Executar a Aplicação

```powershell
streamlit run app.py
```

✨ A aplicação abrirá automaticamente em `http://localhost:8501`

---

## 📋 O que Você Verá

### Página Inicial

- Título: "Dashboard Unificado - Análise por Setor"
- 3 Cards interativos: ✂️ Corte | 🏭 Produção | 📈 Faturamento
- Informações sobre o projeto

### Sidebar (Esquerda)

- 🏠 Botão "Página Inicial"
- 📂 Setores (links para cada dashboard)
- ℹ️ Informações do projeto

---

## 🧪 Testar Cada Setor

### Teste 1: Corte

1. Clique em "✂️ CORTE"
2. Você deve ver:
   - Métricas (Total de Registros, Colunas de Dados, etc)
   - Opções de Filtro
   - Tabela de dados
   - Botão de download CSV

### Teste 2: Produção

1. Clique em "🏠 Página Inicial"
2. Clique em "🏭 PRODUÇÃO"
3. Você deve ver:
   - Métricas KPI
   - 3 Abas: Visão Geral, Detalhes, Dados
   - Gráficos de distribuição
   - Filtros avançados

### Teste 3: Faturamento

1. Clique em "🏠 Página Inicial"
2. Clique em "📈 FATURAMENTO"
3. Você deve ver:
   - Seção Herói (colorida)
   - 4 Métricas principais
   - 4 Abas: Dashboard, Dados, Filtros, Exportar
   - Gráficos interativos (barras, histogramas)
   - Estatísticas descritivas

---

## ✅ Checklist de Validação

- [ ] Aplicação inicia sem erros
- [ ] Página inicial carrega com 3 setores
- [ ] Corte: carrega dados e exibe tabela
- [ ] Produção: 3 abas funcionam
- [ ] Faturamento: gráficos aparecem
- [ ] Sidebar: navegação funciona
- [ ] Download: botões CSV funcionam

---

## 🐛 Erros Comuns

### ❌ "Module not found: streamlit"

```powershell
# Solução:
pip install -r requirements.txt
```

### ❌ "Permission denied" no PowerShell

```powershell
# Como administrador:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### ❌ "Failed to load Google Sheets data"

1. Verifique se as planilhas estão públicas
2. Ou compartilhe com a conta de serviço
3. Veja [SETUP.md](SETUP.md) para mais detalhes

### ❌ "Port 8501 already in use"

```powershell
# Use outra porta:
streamlit run app.py --server.port 8502
```

---

## 📊 Se os Dados Não Aparecerem

1. **Verifique o Sheet ID** em `config.py`
2. **Compartilhe a planilha** publicamente
3. **Verifique a primeira aba** (é a que carrega por padrão)
4. **Feche e reabra** a aplicação

---

## 🎨 Personalizações Rápidas

### Mudar Título

Edite `config.py`:

```python
PAGE_CONFIG = {
    "page_title": "Meu Dashboard Unificado",
    ...
}
```

### Mudar Cores

Edite `sectors/seu_setor.py` e procure por cores em hex (#XXXXXX)

### Adicionar Novo Setor

Veja [INTEGRACAO.md](INTEGRACAO.md) > "Adicionar um Novo Setor"

---

## 📞 Problemas?

1. **Leia:** [SETUP.md](SETUP.md)
2. **Leia:** [INTEGRACAO.md](INTEGRACAO.md)
3. **Leia:** [DOCUMENTACAO.md](DOCUMENTACAO.md)
4. **Consulte:** Documentação Streamlit (https://docs.streamlit.io/)

---

## 💡 Dicas

- Deixe a aba aberta enquanto trabalha
- Use CTRL+R para recarregar
- Use a sidebar para navegar rapidamente
- Exporte dados em CSV conforme necessário
- Customize conforme seus dados

---

## 🎯 Próximas Ações

1. ✅ Primeira execução bem-sucedida?
   → Celebre! 🎉

2. Dados não aparecem?
   → Verifique [SETUP.md](SETUP.md)

3. Quer customizar?
   → Veja [DOCUMENTACAO.md](DOCUMENTACAO.md)

4. Quer adicionar setor?
   → Veja [INTEGRACAO.md](INTEGRACAO.md)

---

**Sucesso! Seu dashboard unificado está rodando! 🚀**

Para parar a aplicação: `CTRL + C` no PowerShell
