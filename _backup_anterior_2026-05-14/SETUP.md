# 🚀 Guia de Configuração - Dashboard Unificado

## Pré-requisitos

- Python 3.8 ou superior
- Conta Google com Google Sheets habilitado
- Conhecimento básico de terminal/PowerShell

## 1️⃣ Instalação Inicial

### Passo 1: Instalar Python

Se você ainda não tem Python instalado:

1. Baixe em https://www.python.org/
2. Durante a instalação, **marque "Add Python to PATH"**
3. Abra PowerShell e verifique: `python --version`

### Passo 2: Clonar/Baixar o Projeto

```powershell
# Navegue até a pasta do projeto
cd "c:\Users\erick\OneDrive\Área de Trabalho\Trabalho\Projeto Unificação dos Dados"
```

### Passo 3: Criar Ambiente Virtual

```powershell
# Criar o ambiente
python -m venv venv

# Ativar (Windows)
.\venv\Scripts\Activate.ps1

# Se tiver erro de política, execute como administrador e rode:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Passo 4: Instalar Dependências

```powershell
pip install -r requirements.txt
```

## 2️⃣ Configurar Google Sheets

### Passo 1: Criar Projeto no Google Cloud

1. Acesse https://console.cloud.google.com/
2. Crie um novo projeto chamado "Dashboard Unificado"
3. Habilite as APIs:
   - Google Sheets API
   - Google Drive API

### Passo 2: Criar Conta de Serviço

1. Vá para "Credenciais" no lado esquerdo
2. Clique em "Criar Credenciais" → "Conta de Serviço"
3. Preencha os detalhes e clique em "Criar e Continuar"
4. Na próxima página, clique em "Criar Chave" → JSON
5. Um arquivo JSON será baixado - salve como `credenciais.json` na pasta do projeto

### Passo 3: Compartilhar Planilhas com a Conta de Serviço

1. Abra o arquivo `credenciais.json` com um editor de texto
2. Copie o email em `client_email` (algo como: `...@....iam.gserviceaccount.com`)
3. Em cada planilha do Google Sheets, clique em "Compartilhar" e:
   - Cole o email da conta de serviço
   - Dê permissão de leitura
   - Clique em "Compartilhar"

## 3️⃣ Configurar o Dashboard

### Passo 1: Copiar Variáveis de Ambiente

```powershell
# Copie o arquivo .env.example
Copy-Item .env.example .env
```

### Passo 2: Editar arquivo `.env`

Abra o arquivo `.env` e preencha:

```
SHEET_ID_CORTE=cole_aqui_o_id_da_planilha_corte
SHEET_ID_PRODUCAO=cole_aqui_o_id_da_planilha_producao
GOOGLE_APPLICATION_CREDENTIALS=./credenciais.json
```

**Como encontrar o ID da planilha:**

- Abra a planilha no Google Sheets
- Copie o ID da URL: `https://docs.google.com/spreadsheets/d/{ID_AQUI}/edit`

## 4️⃣ Executar a Aplicação

```powershell
# Certifique-se que o ambiente virtual está ativado
# Se não estiver, rode: .\venv\Scripts\Activate.ps1

# Execute a aplicação
streamlit run app.py
```

A aplicação abrirá automaticamente em `http://localhost:8501`

## 5️⃣ Customizações

### Adicionar Novo Setor

1. Crie um novo arquivo em `sectors/seu_setor.py`:

```python
from pages.dashboard_base import DashboardBase

class SeuSetorDashboard(DashboardBase):
    def render_dashboard(self):
        # Sua customização aqui
        self.render_header()
        # ... adicione componentes

def render():
    dashboard = SeuSetorDashboard("seu_setor")
    dashboard.render_dashboard()
```

2. Atualize `config.py`:

```python
SHEETS_CONFIG = {
    # ... outros setores
    "seu_setor": {
        "sheet_id": "cole_o_id_aqui",
        "sheet_name": "Dados",
        "icon": "🎯",  # Escolha um emoji
        "descrição": "Descrição do seu setor"
    },
}
```

3. Atualize `sectors/__init__.py`:

```python
from .seu_setor import render as render_seu_setor

__all__ = [
    # ... outros
    "render_seu_setor",
]
```

4. Atualize `app.py` adicionando no roteamento:

```python
elif sector == "seu_setor":
    render_seu_setor()
```

### Customizar Gráficos

Em cada arquivo de setor (ex: `sectors/corte.py`), adicione gráficos Plotly:

```python
import plotly.express as px

# Adicionar um gráfico
fig = px.bar(df, x='coluna1', y='coluna2', title='Meu Gráfico')
st.plotly_chart(fig, use_container_width=True)
```

### Temas e Estilos

Todos os estilos estão em `utils/styling.py`. Customize cores, fontes e elementos visuais lá.

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'streamlit'"

```powershell
pip install streamlit
```

### "Permission denied" ao rodar script PowerShell

```powershell
# Como administrador:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Dados não carregam

1. Verifique se `credenciais.json` existe
2. Verifique se o arquivo foi compartilhado com a conta de serviço
3. Verifique se o SHEET_ID está correto (sem espaços)
4. Verifique o nome da aba (sheet_name) em `config.py`

### Erro de autenticação Google

1. Certifique-se que as APIs estão habilitadas no Google Cloud
2. Verifique se `credenciais.json` está válido
3. Tente deletar e recriar a chave

## 📞 Suporte

Para mais informações sobre Streamlit: https://docs.streamlit.io/
Para mais informações sobre Google Sheets API: https://developers.google.com/sheets/api

---

**Sucesso! Seu dashboard unificado está pronto! 🎉**
