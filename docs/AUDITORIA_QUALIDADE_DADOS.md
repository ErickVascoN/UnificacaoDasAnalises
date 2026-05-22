# 📊 AUDITORIA DE QUALIDADE DE DADOS - PROJETO UNIFICAÇÃO

**Data da Análise**: 20 de maio de 2026  
**Status**: ✅ Documento de Referência para Correções Futuras  
**Total de Problemas Identificados**: 28 (4 Críticos | 6 Altos | 10 Médios | 8 Baixos)

---

## 📑 ÍNDICE

1. [Problemas Críticos](#-problemas-críticos)
2. [Problemas Altos](#-problemas-altos)
3. [Problemas Médios](#-problemas-médios)
4. [Problemas Baixos](#-problemas-baixos)
5. [Plano de Ação](#-plano-de-ação)
6. [Checklist de Implementação](#-checklist-de-implementação)

---

## 🔴 PROBLEMAS CRÍTICOS (4)

### ⚠️ CRÍTICO #1: Filtro de Datas Remove Dados Válidos de "Hoje"

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 453  
**Função**: `carregar_dados()`  
**Severidade**: 🔴 CRÍTICO

**Código Problemático**:

```python
df_corte = df_corte[df_corte['DATA'] <= pd.Timestamp.now()]
```

**Problema**:
Remove registros com datas/horas no futuro (mesmo que hoje). Se dados têm timestamp 14:30 e são executados em 09:00, a data de hoje é rejeitada. Isso causa **perda de dados de produção do dia atual após certo horário**.

**Impacto**: 🔥 PERDA DE DADOS DE PRODUÇÃO

**Solução Recomendada**:

```python
# ANTES
before_count = len(df_corte)
df_corte = df_corte[df_corte['DATA'] <= pd.Timestamp.now()]
removed = before_count - len(df_corte)

# DEPOIS
before_count = len(df_corte)
df_corte = df_corte[df_corte['DATA'].dt.date <= pd.Timestamp.now().date()]
removed = before_count - len(df_corte)
if removed > 0:
    st.info(f"⚠️ {removed} registros removidos (datas no futuro)")
```

---

### ⚠️ CRÍTICO #2: Filtro de Datas Remove Dados Válidos (Lençol)

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 680  
**Função**: `load_corte_lencol()`  
**Severidade**: 🔴 CRÍTICO

**Código Problemático**:

```python
now = pd.Timestamp.now().normalize()
df = df[df["DATA"] <= now]
```

**Problema**: Mesmo problema do #1, mas em função diferente. Remove dados de corte de lençol.

**Impacto**: 🔥 PERDA DE DADOS DE CORTE

**Solução**:

```python
# ANTES
now = pd.Timestamp.now().normalize()
df = df[df["DATA"] <= now]

# DEPOIS
before_count = len(df)
df = df[df["DATA"].dt.date <= pd.Timestamp.now().date()]
removed = before_count - len(df)
if removed > 0:
    st.warning(f"⚠️ {removed} registros de lençol removidos (futuro)")
```

---

### ⚠️ CRÍTICO #3: Ordem Ambígua de Formatos de Data

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 627  
**Função**: `lencol_parse_date()`  
**Severidade**: 🔴 CRÍTICO

**Código Problemático**:

```python
formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"]
```

**Problema**: Tenta `%m/%d/%Y` (formato US) como segunda opção. Datas ambíguas como "01/02/2026" são interpretadas incorretamente (2 de janeiro vs 1º de fevereiro). **Este é o problema que foi recentemente corrigido no commit 305b123**.

**Impacto**: 🔥 PARSING INCORRETO DE DATAS

**Status**: ✅ JÁ FOI CORRIGIDO (commit 305b123)  
**Ordem Atual Correta**: `["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"]`

---

### ⚠️ CRÍTICO #4: Parse de Data Ambíguo com Dois Formatos

**Arquivo**: `pages/1_Produtos_Faturados.py`  
**Linha**: 462-463  
**Função**: `parse_best_date()`  
**Severidade**: 🔴 CRÍTICO

**Código Problemático**:

```python
first = pd.to_datetime(series, errors="coerce", dayfirst=False)
second = pd.to_datetime(series, errors="coerce", dayfirst=True)
if first.notna().sum() >= second.notna().sum():
    return first
```

**Problema**: Tenta dois formatos e escolhe o que tiver MAIS matches. Isso é perigoso - se 51% dos dados são ambíguos e entram em ambos formatos, o critério é aleatório. **Resultado: ~50% das datas podem estar invertidas (dia ↔ mês)**.

**Impacto**: 🔥 ~50% DAS DATAS INVERTIDAS

**Solução Recomendada**:

```python
# ANTES - ERRADO
first = pd.to_datetime(series, errors="coerce", dayfirst=False)
second = pd.to_datetime(series, errors="coerce", dayfirst=True)
if first.notna().sum() >= second.notna().sum():
    return first

# DEPOIS - CORRETO
return pd.to_datetime(series, errors="coerce", dayfirst=True)
```

---

## 🟠 PROBLEMAS ALTOS (6)

### 🔧 ALTO #5: Tratamento de Erro Silencioso em Download

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 429-431  
**Função**: `baixar_csv_google_sheets()`

**Código Problemático**:

```python
except (HTTPError, URLError, TimeoutError) as erro:
    ultimo_erro = erro
    continue
```

**Problema**: Loop tenta múltiplas URLs mas apenas registra erro localmente. Se todas falharem, erro final pode ser perdido. **Impossibilidade de debugar falhas de rede**.

**Solução**:

```python
except (HTTPError, URLError, TimeoutError) as erro:
    st.warning(f"⚠️ URL falhou: {url[:50]}... Erro: {str(erro)[:100]}")
    ultimo_erro = erro
    continue
```

---

### 🔧 ALTO #6: Tratamento de Erro Silencioso - Load Lençol

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 603  
**Função**: `load_corte_lencol()`

**Código Problemático**:

```python
except Exception:
    continue
```

**Problema**: Sem mensagem, sem logging. Usuário não sabe qual URL falhou.

**Solução**:

```python
except Exception as e:
    st.warning(f"❌ URL {url[:50]}... falhou: {str(e)[:80]}")
    continue
```

---

### 🔧 ALTO #7: Locale Error Silencioso

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 141-142  
**Função**: Configuração global

**Código Problemático**:

```python
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass
```

**Problema**: Falha silenciosamente se nenhuma locale PT-BR funcionar. Formatação de datas será em English.

**Solução**:

```python
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        st.warning("⚠️ Locale PT-BR não disponível. Datas podem aparecer em English.")
```

---

### 🔧 ALTO #8: Dropna Sem Verificação de Impacto

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 454  
**Função**: `carregar_dados()`

**Código Problemático**:

```python
df_corte = df_corte.dropna(subset=['DATA', 'OP'])
```

**Problema**: Remove registros sem logging de quantos foram removidos.

**Solução**:

```python
before_count = len(df_corte)
df_corte = df_corte.dropna(subset=['DATA', 'OP'])
removed = before_count - len(df_corte)
if removed > 0:
    st.info(f"📊 {removed} registros removidos (DATA ou OP vazios)")
```

---

### 🔧 ALTO #9: Try/Except Amplo Sem Logging

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 631-635  
**Função**: `lencol_parse_date()`

**Problema**: Loop silencia todos os erros de parsing.

**Solução**:

```python
invalid_count = 0
for fmt in formatos:
    try:
        return pd.to_datetime(data_str, format=fmt)
    except Exception:
        invalid_count += 1
        continue
if invalid_count > 0:
    st.debug(f"Data '{data_str}' não parseada em nenhum formato")
```

---

### 🔧 ALTO #10: Exception Genérica em Main Loop

**Arquivo**: `pages/3_Controle_de_Corte.py`  
**Linha**: 660  
**Função**: `load_metas_lencol()`

**Código Problemático**:

```python
except Exception as e:
    return pd.DataFrame(columns=["PRESTADOR", "EMPRESA", "CATEGORIA", "META"])
```

**Problema**: Retorna DataFrame vazio se falhar. Usuário vê "sem metas" em vez de erro real.

**Solução**:

```python
except Exception as e:
    st.error(f"❌ Erro ao carregar metas: {str(e)}")
    return pd.DataFrame(columns=["PRESTADOR", "EMPRESA", "CATEGORIA", "META"])
```

---

## 🟡 PROBLEMAS MÉDIOS (10)

### 📋 MÉDIO #11: Remoção de Quantidade Zero Sem Aviso

**Arquivo**: `pages/3_Controle_de_Corte.py`, Linha 715  
**Função**: `load_corte_lencol()`

```python
df = df[df["QUANT"] > 0]  # ❌ Sem contar removidos
```

**Solução**:

```python
before = len(df)
df = df[df["QUANT"] > 0]
removed = before - len(df)
if removed > 0:
    st.debug(f"Removidas {removed} linhas com QUANT=0")
```

---

### 📋 MÉDIO #12: Conversão de Tipo Sem Validação

**Arquivo**: `pages/3_Controle_de_Corte.py`, Linha 458  
**Função**: `carregar_dados()`

```python
df_corte['QUANTIDADE'] = pd.to_numeric(
    df_corte['QUANTIDADE'], errors='coerce'
).fillna(0).astype(int)
```

**Problema**: Converte erro para 0. Se coluna tiver texto, todos viram 0 sem aviso.

**Solução**:

```python
before = df_corte['QUANTIDADE'].notna().sum()
df_corte['QUANTIDADE'] = pd.to_numeric(
    df_corte['QUANTIDADE'], errors='coerce'
).fillna(0).astype(int)
after = (df_corte['QUANTIDADE'] > 0).sum()
if after < before:
    st.warning(f"⚠️ {before - after} quantidades convertidas para 0 (erros)")
```

---

### 📋 MÉDIO #13: ⚡ INCONSISTÊNCIA DE COLUNAS ENTRE PLANILHAS

**Arquivo**: `pages/2_Producao_Geral.py` (linha 251) vs `pages/3_Controle_de_Corte.py`  
**Problema**:

- Em `2_Producao_Geral.py`: coluna se chama `"Faccao"`
- Em `3_Controle_de_Corte.py`: coluna se chama `"ESTACAO DE CORTE"`

**Impacto**: 🔥 **IMPOSSÍVEL CONSOLIDAR DADOS ENTRE MÓDULOS**

**Status**: ⚠️ PRECISA DE STANDARDIZAÇÃO GLOBAL

**Recomendação**:
Criar um arquivo `COLUMN_MAPPING.py` com mapeamento de nomes padrão:

```python
COLUMN_STANDARDS = {
    'station': ['Faccao', 'ESTACAO', 'ESTACAO DE CORTE', 'MAQUINA', 'MESA'],
    'date': ['DATA', 'Date', 'data', 'DT'],
    'quantity': ['QUANTIDADE', 'QUANT', 'Quantidade'],
    'product': ['PRODUTO', 'Produto', 'CATEGORIA'],
}
```

---

### 📋 MÉDIO #14: Parse de Data com Format Mixed

**Arquivo**: `pages/3_Controle_de_Corte.py`, Linha 452  
**Função**: `carregar_dados()`

```python
df_corte['DATA'] = pd.to_datetime(
    data_raw, format='mixed', dayfirst=True, errors='coerce'
)
```

**Problema**: `format='mixed'` é impreciso com `dayfirst=True`. Pandas tenta adivinhar.

**Solução**:

```python
# Ser explícito sobre o formato
df_corte['DATA'] = pd.to_datetime(
    data_raw, format='%d/%m/%Y', errors='coerce'
)
```

---

### 📋 MÉDIO #15: Fillna com 0 em Meta Diária

**Arquivo**: `pages/2_Producao_Geral.py`, Linha 196  
**Função**: `_calc_meta()`

```python
meta_mensal["Meta Diaria"] = meta_mensal["Meta Diaria"].fillna(0)
```

**Problema**: Se meta está faltando, assume 0. Pode indicar erro de carregamento.

**Solução**:

```python
before = meta_mensal["Meta Diaria"].isna().sum()
meta_mensal["Meta Diaria"] = meta_mensal["Meta Diaria"].fillna(0)
if before > 0:
    st.warning(f"⚠️ {before} metas preenchidas com 0 (faltavam dados)")
```

---

### 📋 MÉDIO #16: ⚡ DUAS FUNÇÕES DE DIAS ÚTEIS COM LÓGICA DIFERENTE

**Arquivo**: `pages/2_Producao_Geral.py`, Linhas 135-177  
**Funções**: `dias_uteis_com_sabados_trabalhados()` vs `dias_uteis_com_trabalho()`

**Problema**: Duas funções fazem cálculos parecidos mas com lógica ligeiramente diferente.

- Qual está correta?
- Qual deveria ser usada onde?

**Impacto**: Metas podem estar descalibradas

**Recomendação**:

- Consolidar em uma única função com testes unitários
- Documentar qual lógica deve ser usada
- Remover a função não usada

---

### 📋 MÉDIO #17: Agrupamento Sem Verificação

**Arquivo**: `pages/2_Producao_Geral.py`, Linhas 182-186  
**Função**: `_calc_meta()`

```python
.drop_duplicates(subset=["Faccao", "Produto", "Ano", "Mes"])
.groupby(["Faccao", "Ano", "Mes"], as_index=False)
```

**Problema**: Drop_duplicates em colunas diferentes que depois no groupby. Pode perder dados.

**Solução**: Verificar se colunas do drop_duplicates contêm as do groupby.

---

### 📋 MÉDIO #18: Remoção de Empresa Sem Logging

**Arquivo**: `pages/3_Controle_de_Corte.py`, Linha 710  
**Função**: `load_corte_lencol()`

```python
invalidos = {"", "NAN", "NONE", "N/A", "NAO", "NAO INFORMADO"}
df = df[~df["PRESTADOR"].str.upper().isin(invalidos)]
df = df[~df["EMPRESA"].str.upper().isin(invalidos)]
```

**Solução**:

```python
before = len(df)
df = df[~df["PRESTADOR"].str.upper().isin(invalidos)]
df = df[~df["EMPRESA"].str.upper().isin(invalidos)]
removed = before - len(df)
if removed > 0:
    st.info(f"📊 {removed} registros removidos (empresa/prestador inválido)")
```

---

### 📋 MÉDIO #19: Filtro Entre Datas Pode Estar Errado

**Arquivo**: `pages/2_Producao_Geral.py`, Linhas 666-676

```python
date_filter = lambda df: df[
    df["Ano"].isin(sel_anos) & df["Mes"].isin(sel_meses) &
    (df["Data"].dt.date.between(ini, fim))
]
```

**Problema**: Filtra por ano/mês AND também entre datas. Pode haver sobreposição.

**Solução**: Usar OR ou remover redundância.

---

### 📋 MÉDIO #20: Comparação de Período Ignora prev=0

**Arquivo**: `pages/1_Produtos_Faturados.py`, Linhas 765-770  
**Função**: `compare_previous_period()`

```python
if prev_value <= 0:
    return None
```

**Problema**: Se período anterior era 0, retorna None. Mas delta deveria ser infinito ou erro.

**Solução**:

```python
if prev_value <= 0:
    return float('inf') if current_value > 0 else 0
```

---

## 🟢 PROBLEMAS BAIXOS (8)

### 🧹 BAIXO #21-22: Import Não Usado - make_subplots

**Arquivo**: `pages/1_Produtos_Faturados.py`, Linha 15 e `pages/3_Controle_de_Corte.py`, Linha 16

```python
from plotly.subplots import make_subplots  # ❌ Nunca usado
```

**Solução**: Remover import

---

### 🧹 BAIXO #23: Import Não Usado - time

**Arquivo**: `pages/1_Produtos_Faturados.py`, Linha 6

```python
import time  # ❌ Nunca usado
```

**Solução**: Remover import

---

### 🧹 BAIXO #24: Função Morta - is_valid_color_word()

**Arquivo**: `pages/1_Produtos_Faturados.py`, Linha 470

**Problema**: Função definida mas nunca chamada

**Solução**: Remover função

---

### 🧹 BAIXO #25: Função Morta - is_dimension()

**Arquivo**: `pages/1_Produtos_Faturados.py`, Linha 461

**Problema**: Função definida mas nunca chamada

**Solução**: Remover função

---

### 🧹 BAIXO #26: Função Morta - normalize_text()

**Arquivo**: `pages/1_Produtos_Faturados.py`, Linha 372

**Problema**: Função definida mas nunca chamada

**Solução**: Remover função ou implementar

---

### 🧹 BAIXO #27: Import Raramente Usado

**Arquivo**: `pages/2_Producao_Geral.py`, Linha 2

```python
import streamlit.components.v1 as components  # Usado apenas 1 vez
```

**Solução**: Simplificar ou mover HTML para arquivo separado

---

### 🧹 BAIXO #28: CSS Duplicado Não Reutilizável

**Arquivo**: `pages/2_Producao_Geral.py`, Linhas 73-100

**Problema**: CSS duplicado entre páginas, não reutilizável

**Solução**: Mover para arquivo `styles.css` separado

---

## 📊 RESUMO POR CATEGORIA

| Categoria           | Crítica | Alta  | Média  | Baixa | Total  |
| ------------------- | ------- | ----- | ------ | ----- | ------ |
| Parseamento de Data | 3       | 1     | 2      | 0     | **6**  |
| Tratamento de Erro  | 0       | 5     | 1      | 0     | **6**  |
| Código Morto        | 0       | 0     | 0      | 5     | **5**  |
| Filtro de Dados     | 1       | 0     | 6      | 0     | **7**  |
| Inconsistências     | 0       | 0     | 1      | 3     | **4**  |
| **TOTAL**           | **4**   | **6** | **10** | **8** | **28** |

---

## 🎯 PLANO DE AÇÃO

### 📍 FASE 1 - HOJE (2 horas) - CRÍTICO 🔴

```
⏱️ Tempo estimado: 2 horas

[ ] CRÍTICO #1: Remover filtro `<= pd.Timestamp.now()` em carregar_dados() (linha 453)
[ ] CRÍTICO #2: Remover filtro em load_corte_lencol() (linha 680)
[ ] CRÍTICO #3: Parse_date já foi corrigido ✅ (commit 305b123)
[ ] CRÍTICO #4: Corrigir parse_best_date() em 1_Produtos_Faturados.py
[ ] ALTO #8: Adicionar logging em dropna()
[ ] ALTO #9: Adicionar logging em parse loops
```

**Commit Message**: `fix: Remove future timestamp filters and fix date parsing ambiguity`

---

### 📍 FASE 2 - HOJE (4 horas) - ALTOS 🟠

```
⏱️ Tempo estimado: 4 horas

[ ] ALTO #5: Adicionar st.warning() em download errors
[ ] ALTO #6: Adicionar st.warning() em load_corte_lencol()
[ ] ALTO #7: Adicionar st.warning() em locale errors
[ ] ALTO #10: Adicionar st.error() em load_metas_lencol()
[ ] MÉDIO #8: Dropna logging
[ ] MÉDIO #11: Remove quant=0 logging
[ ] MÉDIO #12: Conversão tipo logging
```

**Commit Message**: `feat: Add error logging and warnings for data loading failures`

---

### 📍 FASE 3 - ESTA SEMANA (6 horas) - MÉDIOS 🟡

```
⏱️ Tempo estimado: 6 horas

[ ] MÉDIO #13: ⚡ Standardizar nomes de colunas (CRÍTICO)
[ ] MÉDIO #14: Remover format='mixed' ambíguo
[ ] MÉDIO #15: Fillna logging
[ ] MÉDIO #16: ⚡ Consolidar funções de dias úteis
[ ] MÉDIO #17: Verificar drop_duplicates logic
[ ] MÉDIO #18: Remover empresa logging
[ ] MÉDIO #19: Revisar filtro de datas
[ ] MÉDIO #20: Comparação de período
```

**Commit Message**: `refactor: Standardize column names and consolidate date calculations`

---

### 📍 FASE 4 - PRÓXIMA SEMANA (2 horas) - BAIXOS 🟢

```
⏱️ Tempo estimado: 2 horas

[ ] BAIXO #21-22: Remover imports make_subplots
[ ] BAIXO #23: Remover import time
[ ] BAIXO #24-26: Remover funções mortas
[ ] BAIXO #27: Simplificar components import
[ ] BAIXO #28: Mover CSS para arquivo separado
```

**Commit Message**: `chore: Remove unused imports and dead code`

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Preparação

- [ ] Clonar/fazer backup da branch atual
- [ ] Criar branch `fix/data-quality` para trabalhar
- [ ] Ler este documento completamente

### Fase 1 - Crítico (HOJE)

- [ ] CRÍTICO #1: Remover filtro timestamp em carregar_dados()
  - [ ] Arquivo: `pages/3_Controle_de_Corte.py`, Linha 453
  - [ ] Testar com dados do dia atual
  - [ ] Verificar se dados aparecem após 12:00

- [ ] CRÍTICO #2: Remover filtro timestamp em load_corte_lencol()
  - [ ] Arquivo: `pages/3_Controle_de_Corte.py`, Linha 680
  - [ ] Testar dashboard Arealva Lençol
  - [ ] Verificar se gráfico mostra hoje

- [ ] CRÍTICO #3: ✅ JÁ FOI CORRIGIDO
  - [ ] Status: Commit 305b123 aplicado
  - [ ] Verificar se lencol_parse_date() usa %d/%m/%Y primeiro

- [ ] CRÍTICO #4: Corrigir parse_best_date()
  - [ ] Arquivo: `pages/1_Produtos_Faturados.py`, Linha 462-463
  - [ ] Remover primeiro parse com dayfirst=False
  - [ ] Testar com datas ambíguas (01/02, 02/03, etc)

- [ ] Commit e push ao final da Fase 1

### Fase 2 - Altos (HOJE)

- [ ] ALTO #5: Adicionar warnings em baixar_csv_google_sheets()
  - [ ] Arquivo: `pages/3_Controle_de_Corte.py`, Linha 429
  - [ ] Testar com rede desconectada

- [ ] ALTO #6, #7, #10: Adicionar st.error/warning em handlers
  - [ ] Testar falhas simuladas

- [ ] ALTO #8, #9: Adicionar logging de removidos
  - [ ] Verificar se mensagens aparecem na tela

- [ ] Commit e push ao final da Fase 2

### Fase 3 - Médios (ESTA SEMANA)

- [ ] MÉDIO #13: ⚡ Standardizar colunas
  - [ ] Mapeamento: Faccao → ESTACAO_PADRAO
  - [ ] Teste de consolidação entre módulos
  - [ ] Criar COLUMN_MAPPING.py

- [ ] MÉDIO #16: Consolidar dias úteis
  - [ ] Entender diferença entre duas funções
  - [ ] Escolher correta ou criar híbrida
  - [ ] Remover função não usada

- [ ] Outros médios conforme checklist

- [ ] Commit e push ao final da Fase 3

### Fase 4 - Baixos (PRÓXIMA SEMANA)

- [ ] Remover imports não usados
- [ ] Remover funções mortas
- [ ] Consolidar CSS
- [ ] Commit e push

### Testes Finais

- [ ] Executar `streamlit run app.py`
- [ ] Testar cada dashboard
- [ ] Verificar se dados são carregados corretamente
- [ ] Revisar logs para avisos de remover dados
- [ ] Criar PR e revisar mudanças

---

## 📝 NOTAS IMPORTANTES

### ⚠️ ANTES DE COMEÇAR

1. **Sempre fazer backup** da branch atual
2. **Testar localmente** antes de fazer push
3. **Verificar se dados aparecem** após mudanças
4. **Documentar** qualquer mudança no comportamento

### 🔍 COMO TESTAR

- Dados com datas de hoje: `pd.Timestamp.now()`
- Dados com datas futuras: Modificar planilha
- Dados ambíguos: 01/02, 02/03, etc
- Dados com erro: Remover colunas, adicionar lixo

### 📊 MÉTRICAS A MONITORAR

- Número de registros carregados
- Número de registros removidos (e por quê)
- Tempo de carregamento da planilha
- Quantidade de avisos mostrados

### 🚨 SINAIS DE ALERTA

- ❌ Dados "sumiram" após mudança
- ❌ Gráficos vazios ou com dias faltando
- ❌ Avisos frequentes de "formato inválido"
- ❌ Metas de 0 aparecendo
- ❌ Datas invertidas (janeiro aparecendo como mês 2)

---

## 📞 REFERÊNCIAS

**Arquivo Original de Análise**:  
`c:\Users\erick\AppData\Roaming\Code\User\workspaceStorage\b2270cf33c88b7751b2fe0865ee2f689\GitHub.copilot-chat\chat-session-resources\13d09da3-b34c-451a-b943-db88d3f19956\toolu_bdrk_0113omxcCvHDWwbHnnrj8byN__vscode-1779272831830\content.txt`

**Commits Relacionados**:

- `305b123` - fix: Correct date parsing order in Arealva Lençol dashboard
- `1e0bd55` - Revert "fix: Use correct spreadsheet for Arealva Manta dashboard..."
- `169f2d7` - fix: Use correct spreadsheet for Arealva Manta dashboard...

**Data de Criação**: 20 de maio de 2026  
**Versão**: 1.0  
**Status**: ✅ Pronto para Implementação

---

## 🔄 HISTÓRICO DE ATUALIZAÇÕES

| Data       | Versão | Mudanças                                        |
| ---------- | ------ | ----------------------------------------------- |
| 20/05/2026 | 1.0    | Documento criado com 28 problemas identificados |

---

**📌 PRÓXIMOS PASSOS**: Escolha a fase (1, 2, 3 ou 4) e comece pelas correções CRÍTICAS primeiro!
