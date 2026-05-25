# 📊 Componente de Eficiência de Corte

Componente reutilizável para análise de eficiência de corte.

## 📍 Localização
`components/eficiencia_corte.py`

## 🚀 Como Usar

### Importar
```python
from components.eficiencia_corte import render_eficiencia_dashboard
```

### Renderizar como Aba
```python
# Dentro da página 3 (Controle de Corte)
with st.tabs([...tabs...]):
    with tab_eficiencia:
        render_eficiencia_dashboard(regiao="arealva", produto="manta")
        render_eficiencia_dashboard(regiao="arealva", produto="lencol")
```

## 📋 Funções Disponíveis

### `render_eficiencia_dashboard(regiao: str, produto: str = None)`
Renderiza o dashboard de eficiência completo.

**Parâmetros:**
- `regiao`: `"arealva"` ou `"iacanga"`
- `produto`: `"manta"` ou `"lencol"` (apenas para Arealva)

**Exemplo:**
```python
# Manta Arealva
render_eficiencia_dashboard(regiao="arealva", produto="manta")

# Lençol Arealva
render_eficiencia_dashboard(regiao="arealva", produto="lencol")

# Iacanga (em breve)
render_eficiencia_dashboard(regiao="iacanga")
```

### Funções Específicas
- `render_manta_arealva()` - Dashboard Manta Arealva
- `render_lencol_arealva()` - Dashboard Lençol Arealva

### Funções de Carregamento (com cache)
- `carregar_manta_arealva()` - Carrega dados Manta
- `carregar_lencol_arealva()` - Carrega dados Lençol

## 📊 Indicadores

### Manta Arealva
- ⚡ Eficiência (Peças) %
- ⚡ Eficiência (KG) %
- 📊 Aproveitamento (%)
- 👶 Total Babys (Peças)
- 🔄 Retalhos (Kg)
- 📈 Divergência (Kg)

### Lençol Arealva
- ⚡ Eficiência Média de Corte %
- 📦 Total Programado
- ✂️ Total Cortado
- 🔄 Retalho Médio (Kg)
- 📊 Perda (%)
- 📊 Aproveitamento (%)

## 🔗 Configuração

Sheet IDs e GIDs estão no componente:
```python
EFICIENCIA_MANTA_AREALVA_ID = "17ido41trF22ks7HgoJz9XHcJU0oA4SYK"
EFICIENCIA_MANTA_AREALVA_GID = "874592526"

EFICIENCIA_LENCOL_AREALVA_ID = "1PBb_XS9dsiRMBQt6cnILzUnANTaN9stQ"
EFICIENCIA_LENCOL_AREALVA_GID = "1424027835"
```

Se precisar centralizar, mova para `config/settings.py`.

## 💾 Cache
- TTL padrão: 300 segundos (5 min)
- Configurável via `EFICIENCIA_CACHE_TTL`

## 🎨 Visual
- Segue o padrão dark dos dashboards
- Gráficos Plotly interativos
- Métricas com indicadores de qualidade (✅ Excelente, 🔵 Bom, ⚠️ Atenção)

## ❌ Não Implementado
- Iacanga (em desenvolvimento)
- Filtros avançados (pode ser adicionado)
- Export de dados (pode ser adicionado)
