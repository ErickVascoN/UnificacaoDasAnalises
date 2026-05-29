# Padrões do Projeto — Camada de Dados

Estas regras existem para evitar que os bugs já corrigidos voltem a acontecer.
**Sempre que mexer em carregamento/tratamento de planilha, siga isto.**

## 1. Carregar planilha → SEMPRE via `cache_manager`

Nunca chame `requests.get` / `urllib` direto numa página.

```python
from utils.cache_manager import get_raw
texto = get_raw(sheet_id, gid, ttl=120)   # CSV bruto, com cache em disco + fallback
```

Por quê: o `cache_manager` guarda a planilha em `cache/sheets/`, reaproveita entre
páginas, e se o Google der timeout usa o último dado bom (o dashboard não cai).
Para XLSX use `utils.sheets_loader.load_sheets_with_retry(..., format_type="xlsx")`.

## 2. Converter datas → SEMPRE `date_parser.parse_date_series`

Nunca use `pd.to_datetime(..., dayfirst=True/False)` nem `strptime` numa coluna de
data de planilha. Nunca crie um parser de data local.

```python
from utils.date_parser import parse_date_series
df["DATA"] = parse_date_series(df["DATA"])
```

Por quê: cada planilha do Google exporta num formato (uma em `DD/MM/YY`, outra em
`MM/DD/YYYY`). O `parse_date_series` detecta o formato olhando a **coluna inteira**
e aplica igual a todos — sem inverter dia/mês (foi o que fazia o Iacanga mostrar
"dezembro").

## 3. Comparar OP entre planilhas → SEMPRE `normalize.normalize_op`

Ao cruzar OP da programação com OP do corte (ou qualquer match de OP entre fontes):

```python
from utils.normalize import normalize_op
chave_corte = normalize_op(op_corte)     # "PROG 82" → "82"
chave_prog  = normalize_op(ped_cliente)  # "PGR 10"  → "10"
```

Por quê: a mesma OP aparece como `PROG 82`, `PGR 10`, `82`... Normalizar (tira
prefixo PROG/PGR/OP, espaços, caixa) faz casar sozinho, sem corrigir na mão.
A OP do nosso modelo é o **PED. CLIENTE**. `OP INTERNA` só substitui a OP quando
não existe PED. CLIENTE (aí ela está no lugar da OP).

## 4. Filtrar linhas → NUNCA descartar por um campo-chave vazio

Não jogue fora a linha só porque OP/PED/etc. está vazio — pode ser produção real
sem aquele campo (foi o que sumia cortes no Lençol).

```python
from utils.normalize import is_blank
# Mantenha linhas com dado real; só remova lixo (sem quantidade E sem prestador...).
# Campo-chave vazio: preencha com placeholder ("SEM OP") em vez de dropar.
```

## 5. Achar coluna por conteúdo, não confiar no nome

Há planilhas onde a coluna chamada `DATA` contém o nome da empresa (Lençol). Quando
o layout for "torto", use o loader dedicado (ex: `utils.lencol_loader_smart`) que
mapeia por conteúdo — não leia a coluna pelo nome cru.

---

## Módulos compartilhados (use, não reinvente)

| Módulo | Função | Para quê |
|---|---|---|
| `utils/cache_manager.py` | `get_raw`, `invalidate_all` | baixar planilha com cache |
| `utils/date_parser.py` | `parse_date_series` | converter datas sem inverter dia/mês |
| `utils/normalize.py` | `normalize_op`, `is_blank`, `normalize_text` | comparar OP/textos entre fontes |
| `utils/sheets_loader.py` | `read_csv_from_sheets`, `load_sheets_with_retry` | atalhos CSV/XLSX sobre o cache |
