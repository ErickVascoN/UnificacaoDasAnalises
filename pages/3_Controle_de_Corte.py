import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import locale
import io
import os
import sys
import urllib.request
from urllib.error import HTTPError, URLError

# Garante que config.py e gid_detector.py (na raiz do projeto) sejam
# importaveis quando este script roda como pagina em /pages/.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Importar configurações (com fallback se não existir)
try:
    from config import GOOGLE_SHEETS_ID, GOOGLE_SHEETS_GID, METAS, META_TOTAL, CACHE_TTL
except ImportError:
    # Valores padrão se config.py não existir
    GOOGLE_SHEETS_ID = "1iGj4-vknwzepbrHdRz1PwisZU2foU7aW"
    GOOGLE_SHEETS_GID = None
    METAS = {'MAQUINA': 7000, 'MESA 1': 4000, 'MESA 2': 3000}
    META_TOTAL = sum(METAS.values())
    CACHE_TTL = 60

# CONFIGURAR LOCALE BRASILEIRO
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass  # fallback, usa padrão do sistema

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Dashboard Controle de Corte",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; font-weight: 600; }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 10px;
        padding: 12px 16px;
    }
</style>
""", unsafe_allow_html=True)


# FUNÇÕES
# Função removida: classificar_estacao - agora a estação vem direto da planilha


def baixar_csv_google_sheets():
    """
    Baixa o CSV do Google Sheets de forma automática.
    - Tenta primeiro sem especificar GID (usa a primeira aba)
    - Se falhar, tenta as URLs com GID padrão
    - Implementa retry automático
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Estratégia 1: Sem especificar GID (carrega a primeira aba - mais confiável)
    urls_padrao = [
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq?tqx=out:csv",
    ]
    
    # Estratégia 2: Com GIDs conhecidos (fallback)
    gids_fallback = ["206085601", "0"]  # GID padrão (0 é a primeira aba)
    urls_fallback = []
    for gid in gids_fallback:
        urls_fallback.extend([
            f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv&gid={gid}",
            f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq?tqx=out:csv&gid={gid}",
        ])
    
    # Combinar URLs (prioridade: sem GID → com GID)
    todas_urls = urls_padrao + urls_fallback
    ultimo_erro = None

    for url in todas_urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                conteudo = response.read().decode('utf-8')
                # Validar se recebeu dados
                if conteudo.strip():
                    return io.StringIO(conteudo)
        except (HTTPError, URLError, TimeoutError) as erro:
            ultimo_erro = erro
            continue

    raise RuntimeError(f"Falha ao baixar CSV do Google Sheets. Último erro: {ultimo_erro}")


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados():
    # Sempre lê do Google Sheets (fonte única de dados)
    csv_data = baixar_csv_google_sheets()
    df_corte = pd.read_csv(csv_data, header=0)
    
    # Limpar problemas de espaços em branco nos nomes das colunas
    df_corte.columns = df_corte.columns.str.strip()
    
    # Remover colunas vazias ou desnecessárias
    df_corte = df_corte.drop(columns=[col for col in df_corte.columns if 'Unnamed' in col or 'Coluna' in col], errors='ignore')

    # Verificar colunas obrigatórias
    colunas_obrigatorias = ['DATA', 'OP', 'COR', 'QUANTIDADE', 'ESTAÇÃO DE CORTE', 'PRODUTO']
    colunas_faltantes = [col for col in colunas_obrigatorias if col not in df_corte.columns]
    
    if colunas_faltantes:
        raise KeyError(
            f"Colunas obrigatórias faltando na planilha: {', '.join(colunas_faltantes)}. "
            f"Colunas disponíveis: {', '.join(df_corte.columns.tolist())}"
        )

    # Remove componente de hora se existir (ex: "5/12/2026 0:00:00" → "5/12/2026")
    data_raw = df_corte['DATA'].astype(str).str.split(' ').str[0].str.strip()
    # Planilha em formato EUA (M/D/YYYY): dayfirst=False interpreta mês primeiro
    df_corte['DATA'] = pd.to_datetime(data_raw, format='mixed', dayfirst=False, errors='coerce')
    # Remove datas futuras (erros de digitação na planilha)
    df_corte = df_corte[df_corte['DATA'] <= pd.Timestamp.now()]
    df_corte = df_corte.dropna(subset=['DATA', 'OP'], how='any')
    df_corte = df_corte[df_corte['OP'].astype(str).str.strip() != '']
    df_corte['OP'] = df_corte['OP'].astype(str).str.strip()
    df_corte['COR'] = df_corte['COR'].astype(str).str.strip().str.upper()
    df_corte['QUANTIDADE'] = pd.to_numeric(df_corte['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
    df_corte['ESTACAO'] = df_corte['ESTAÇÃO DE CORTE'].astype(str).str.strip()
    df_corte['PRODUTO'] = df_corte['PRODUTO'].astype(str).str.strip()
    df_corte['SEMANA'] = df_corte['DATA'].dt.isocalendar().week.astype(int)
    df_corte['MES'] = df_corte['DATA'].dt.month
    df_corte['DIA_SEMANA'] = df_corte['DATA'].dt.day_name()

    return df_corte


# =====================================================================
# CARREGAMENTO
# =====================================================================
try:
    df_corte = carregar_dados()
except KeyError as e:
    st.error(f"❌ Erro de coluna: {e}")
    st.error("📋 Verifique se a planilha Google Sheets tem as seguintes colunas (em qualquer ordem):")
    st.error("DATA, OP, COR, QUANTIDADE, ESTAÇÃO DE CORTE, PRODUTO")
    st.info("📡 Também verifique se a planilha está compartilhada como 'Qualquer pessoa com o link'.")
    st.stop()
except Exception as e:
    st.error(f"❌ Erro ao carregar a planilha: {e}")
    st.info("📡 Verifique se a planilha Google Sheets está compartilhada como 'Qualquer pessoa com o link'.")
    st.stop()

# =====================================================================
# HEADER
# =====================================================================
st.markdown('<div class="main-header">✂️ Dashboard Controle de Corte - Mantas</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Acompanhamento de produção e desempenho por estação</div>', unsafe_allow_html=True)

# =====================================================================
# SIDEBAR - FILTROS (com persistência via session_state)
# =====================================================================
st.sidebar.header("🔍 Filtros")

# Mostrar range de datas disponíveis no sidebar
st.sidebar.info(f"📅 Dados de {df_corte['DATA'].min().strftime('%d/%m/%Y')} até {df_corte['DATA'].max().strftime('%d/%m/%Y')}")

if st.sidebar.button("🔄 Limpar Cache e Recarregar", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.metric("📊 Total de Registros", f"{len(df_corte):,}")

df_trabalho = df_corte.copy()

# Inicializar session_state dos filtros
if 'filtro_ops' not in st.session_state:
    st.session_state.filtro_ops = []
if 'filtro_estacoes' not in st.session_state:
    st.session_state.filtro_estacoes = []
if 'filtro_produtos' not in st.session_state:
    st.session_state.filtro_produtos = []
if 'filtro_data_ini' not in st.session_state:
    st.session_state.filtro_data_ini = df_trabalho['DATA'].min().date() if not df_trabalho.empty else None
if 'filtro_data_fim' not in st.session_state:
    st.session_state.filtro_data_fim = df_trabalho['DATA'].max().date() if not df_trabalho.empty else None

# Filtro de OP
ops_disponiveis = sorted(df_trabalho['OP'].dropna().unique())
# Validar valores salvos (podem ter sido removidos dos dados)
default_ops = [op for op in st.session_state.filtro_ops if op in ops_disponiveis]
ops_selecionadas = st.sidebar.multiselect("📋 Filtrar por OP", options=ops_disponiveis, default=default_ops)
st.session_state.filtro_ops = ops_selecionadas

# Filtro de Estação
estacoes_disponiveis = sorted(df_trabalho['ESTACAO'].dropna().unique())
default_est = [e for e in st.session_state.filtro_estacoes if e in estacoes_disponiveis]
estacoes_selecionadas = st.sidebar.multiselect("🏭 Filtrar por Estação", options=estacoes_disponiveis, default=default_est)
st.session_state.filtro_estacoes = estacoes_selecionadas

# Filtro de Produto
produtos_disponiveis = sorted(df_trabalho['PRODUTO'].dropna().unique())
default_prod = [p for p in st.session_state.filtro_produtos if p in produtos_disponiveis]
produtos_selecionados = st.sidebar.multiselect("📦 Filtrar por Produto", options=produtos_disponiveis, default=default_prod)
st.session_state.filtro_produtos = produtos_selecionados

# Filtro de Dias
st.sidebar.markdown("### 📅 Filtro de Dias")

if 'filtro_tipo_data' not in st.session_state:
    st.session_state.filtro_tipo_data = "Período"

tipo_filtro = st.sidebar.radio(
    "Tipo de filtro",
    options=["Um dia", "Período"],
    index=0 if st.session_state.filtro_tipo_data == "Um dia" else 1,
    horizontal=True
)
st.session_state.filtro_tipo_data = tipo_filtro

if not df_trabalho.empty:
    data_min = df_trabalho['DATA'].min().date()
    data_max = df_trabalho['DATA'].max().date()
    saved_ini = st.session_state.filtro_data_ini if st.session_state.filtro_data_ini else data_min
    saved_fim = st.session_state.filtro_data_fim if st.session_state.filtro_data_fim else data_max
    saved_ini = max(saved_ini, data_min)
    saved_fim = min(saved_fim, data_max)

    if tipo_filtro == "Um dia":
        dia_selecionado = st.sidebar.date_input(
            "Data",
            value=saved_fim,
            min_value=data_min,
            max_value=data_max,
            format="DD/MM/YYYY"
        )
        filtro_datas = (dia_selecionado, dia_selecionado)
        st.session_state.filtro_data_ini = dia_selecionado
        st.session_state.filtro_data_fim = dia_selecionado
    else:
        data_inicio = st.sidebar.date_input(
            "Início",
            value=saved_ini,
            min_value=data_min,
            max_value=data_max,
            format="DD/MM/YYYY"
        )
        Ultimo_corte = st.sidebar.date_input(
            "Fim",
            value=saved_fim,
            min_value=data_min,
            max_value=data_max,
            format="DD/MM/YYYY"
        )
        filtro_datas = (data_inicio, Ultimo_corte)
        st.session_state.filtro_data_ini = data_inicio
        st.session_state.filtro_data_fim = Ultimo_corte

# Aplicar filtros
df_filtrado = df_trabalho.copy()
if ops_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['OP'].isin(ops_selecionadas)]
if estacoes_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['ESTACAO'].isin(estacoes_selecionadas)]
if produtos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['PRODUTO'].isin(produtos_selecionados)]
if isinstance(filtro_datas, tuple) and len(filtro_datas) == 2:
    df_filtrado = df_filtrado[
        (df_filtrado['DATA'].dt.date >= filtro_datas[0]) &
        (df_filtrado['DATA'].dt.date <= filtro_datas[1])
    ]

st.sidebar.markdown("---")
st.sidebar.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.sidebar.caption(f"Registros carregados: {len(df_filtrado):,}")

# ABAS 
tab1, tab2, tab3 = st.tabs([
    "📊 Visão Geral",
    "📋 Acompanhamento por OP",
    "🏭 Produção por Estação"
])


# TAB 1 - VISÃO GERAL

with tab1:
    st.markdown("### 📊 Indicadores Gerais")

    total_pecas = df_filtrado['QUANTIDADE'].sum()
    total_ops = df_filtrado['OP'].nunique()
    total_cores = df_filtrado['COR'].nunique()
    dias_trabalhados = df_filtrado['DATA'].dt.date.nunique()
    media_dia = total_pecas / max(dias_trabalhados, 1)
    pecas_maquina = df_filtrado[df_filtrado['ESTACAO'] == 'MAQUINA']['QUANTIDADE'].sum()
    pecas_mesa1 = df_filtrado[df_filtrado['ESTACAO'] == 'MESA 1']['QUANTIDADE'].sum()
    pecas_mesa2 = df_filtrado[df_filtrado['ESTACAO'] == 'MESA 2']['QUANTIDADE'].sum()
    delta_media = ((media_dia / META_TOTAL) - 1) * 100 if META_TOTAL > 0 else 0

    # KPIs - Linha 1
    cols_kpi = st.columns(4)
    cols_kpi[0].metric("✂️ Total de Peças", f"{total_pecas:,.0f}")
    cols_kpi[1].metric("📋 Total de OPs", f"{total_ops}")
    cols_kpi[2].metric("🎨 Cores Diferentes", f"{total_cores}")
    cols_kpi[3].metric("📆 Dias Trabalhados", f"{dias_trabalhados}")

    # KPIs - Linha 2
    cols_kpi2 = st.columns(4)
    cols_kpi2[0].metric("⚡ Média Peças/Dia", f"{media_dia:,.0f}", delta=f"{delta_media:+.1f}% vs Meta {META_TOTAL:,}")
    cols_kpi2[1].metric("🔧 Máquina", f"{pecas_maquina:,.0f}")
    cols_kpi2[2].metric("📐 Mesa 1", f"{pecas_mesa1:,.0f}")
    cols_kpi2[3].metric("📐 Mesa 2", f"{pecas_mesa2:,.0f}")

    st.markdown("---")

    # Gráfico de produção diária - barras com cor condicional (verde/vermelho vs meta)
    st.markdown("#### 📈 Produção Diária (Peças)")
    prod_diaria = df_filtrado.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
    prod_diaria['ACIMA_META'] = prod_diaria['QUANTIDADE'] >= META_TOTAL
    prod_diaria['COR'] = prod_diaria['ACIMA_META'].map({True: '✅ Acima da Meta', False: '❌ Abaixo da Meta'})

    fig1 = go.Figure()
    # Barras coloridas por meta
    df_acima = prod_diaria[prod_diaria['ACIMA_META']]
    df_abaixo = prod_diaria[~prod_diaria['ACIMA_META']]
    fig1.add_trace(go.Bar(x=df_acima['DATA'], y=df_acima['QUANTIDADE'],
                          name='Acima da Meta', marker_color='#2ca02c', opacity=0.8))
    fig1.add_trace(go.Bar(x=df_abaixo['DATA'], y=df_abaixo['QUANTIDADE'],
                          name='Abaixo da Meta', marker_color='#d62728', opacity=0.7))
    # Média móvel 5 dias
    if len(prod_diaria) >= 5:
        prod_diaria['MM5'] = prod_diaria['QUANTIDADE'].rolling(5, min_periods=1).mean()
        fig1.add_trace(go.Scatter(x=prod_diaria['DATA'], y=prod_diaria['MM5'],
                                  name='Tendência (5d)', line=dict(color='#ff7f0e', width=3),
                                  mode='lines'))
    # Linha de meta
    fig1.add_hline(y=META_TOTAL, line_dash="dash", line_color="#333", line_width=2,
                   annotation_text=f"Meta: {META_TOTAL:,}",
                   annotation_font_size=12, annotation_font_color="#333")
    fig1.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20),
                       legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0.5, xanchor='center'),
                       xaxis_title='', yaxis_title='Peças',
                       plot_bgcolor='rgba(0,0,0,0)')
    fig1.update_xaxes(tickformat='%d/%m/%Y')
    fig1.update_yaxes(gridcolor='rgba(0,0,0,0.06)')
    st.plotly_chart(fig1, width='stretch')

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### 🏭 Distribuição por Estação")
        dist_estacao = df_filtrado.groupby('ESTACAO')['QUANTIDADE'].sum().reset_index()
        fig2 = px.pie(dist_estacao, values='QUANTIDADE', names='ESTACAO',
                      color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
        fig2.update_traces(textposition='inside', textinfo='percent+label+value')
        fig2.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig2, width='stretch')

    with col_g2:
        st.markdown("#### 📦 Produção por Produto")
        prod_produto = df_filtrado.groupby('PRODUTO')['QUANTIDADE'].sum().reset_index()
        prod_produto = prod_produto.sort_values('QUANTIDADE', ascending=True).tail(15)
        fig3 = px.bar(prod_produto, y='PRODUTO', x='QUANTIDADE', orientation='h',
                      color='QUANTIDADE', color_continuous_scale='Blues',
                      labels={'QUANTIDADE': 'Peças', 'PRODUTO': 'Produto'})
        fig3.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                           showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig3, width='stretch')

    st.markdown("#### 🎨 Top 15 Cores Mais Cortadas")
    col_cor_l, col_cor_r = st.columns(2)
    with col_cor_l:
        prod_cor = df_filtrado.groupby('COR')['QUANTIDADE'].sum().reset_index()
        prod_cor = prod_cor.sort_values('QUANTIDADE', ascending=True).tail(15)
        fig4 = px.bar(prod_cor, y='COR', x='QUANTIDADE', orientation='h',
                      color='QUANTIDADE', color_continuous_scale='Viridis',
                      labels={'QUANTIDADE': 'Peças', 'COR': 'Cor'})
        fig4.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20),
                           showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig4, width='stretch')

    with col_cor_r:
        # Tabela resumo de cores
        prod_cor_all = df_filtrado.groupby('COR')['QUANTIDADE'].sum().reset_index()
        prod_cor_all = prod_cor_all.sort_values('QUANTIDADE', ascending=False).head(15)
        prod_cor_all['%'] = (prod_cor_all['QUANTIDADE'] / prod_cor_all['QUANTIDADE'].sum() * 100).round(1)
        prod_cor_all.columns = ['Cor', 'Peças', '% do Total']
        st.dataframe(prod_cor_all, width='stretch', height=400, hide_index=True)

# TAB 2 - ACOMPANHAMENTO POR OP
with tab2:
    st.markdown("### 📋 Acompanhamento Detalhado por OP")

    resumo_op = df_filtrado.groupby('OP').agg(
        Total_Pecas=('QUANTIDADE', 'sum'),
        Qtd_Cores=('COR', 'nunique'),
        Produto=('PRODUTO', 'first'),
        Data_Inicio=('DATA', 'min'),
        Ultimo_corte=('DATA', 'max'),
        Dias_Producao=('DATA', lambda x: x.dt.date.nunique())
    ).reset_index()
    resumo_op = resumo_op.sort_values('Total_Pecas', ascending=False)

    st.markdown("#### Resumo das OPs")
    st.dataframe(
        resumo_op.style.format({
            'Total_Pecas': '{:,.0f}',
            'Data_Inicio': lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '',
            'Data_Fim': lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
        }),
        width='stretch', height=400
    )

    st.markdown("---")

    op_detalhe = st.selectbox("🔎 Selecione uma OP para ver detalhes:", options=resumo_op['OP'].tolist())

    if op_detalhe:
        df_op = df_filtrado[df_filtrado['OP'] == op_detalhe]

        col_op1, col_op2, col_op3 = st.columns(3)
        col_op1.metric("Peças Total", f"{df_op['QUANTIDADE'].sum():,.0f}")
        col_op2.metric("Cores Cortadas", f"{df_op['COR'].nunique()}")
        col_op3.metric("Produto", df_op['PRODUTO'].iloc[0] if not df_op.empty else "N/A")

        st.markdown(f"#### Quantidade por Cor - OP {op_detalhe}")
        cor_op = df_op.groupby('COR')['QUANTIDADE'].sum().reset_index().sort_values('QUANTIDADE', ascending=False)

        fig_op1 = px.bar(cor_op, x='COR', y='QUANTIDADE',
                         color='QUANTIDADE', color_continuous_scale='Blues',
                         labels={'COR': 'Cor', 'QUANTIDADE': 'Peças'},
                         text='QUANTIDADE')
        fig_op1.update_traces(textposition='outside')
        fig_op1.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                              coloraxis_showscale=False)
        st.plotly_chart(fig_op1, width='stretch')

        st.markdown(f"#### 📝 Registros Detalhados - OP {op_detalhe}")
        df_op_display = df_op[['DATA', 'ESTACAO', 'COR', 'QUANTIDADE', 'PRODUTO']].copy()
        df_op_display['DATA'] = df_op_display['DATA'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_op_display, width='stretch', height=300)


# =====================================================================
# TAB 3 - PRODUÇÃO POR ESTAÇÃO
# =====================================================================
with tab3:
    st.markdown("### 🏭 Produção por Estação de Corte")

    estacoes = ['MAQUINA', 'MESA 1', 'MESA 2']
    cores_estacao = {'MAQUINA': '#1f77b4', 'MESA 1': '#2ca02c', 'MESA 2': '#ff7f0e'}

    # Progresso vs Meta - Cards com barra de progresso HTML
    st.markdown("#### 🎯 Progresso vs Meta Diária (Média Peças/Dia)")
    cols_meta = st.columns(3)
    for i, estacao in enumerate(estacoes):
        df_est_b = df_filtrado[df_filtrado['ESTACAO'] == estacao]
        dias_b = df_est_b['DATA'].dt.date.nunique()
        media_b = df_est_b['QUANTIDADE'].sum() / max(dias_b, 1)
        meta_b = METAS[estacao]
        pct = min((media_b / meta_b * 100), 150) if meta_b > 0 else 0
        diff = media_b - meta_b

        if pct >= 100:
            cor_prog = '#2ca02c'
            status = '✅ META ATINGIDA'
        elif pct >= 80:
            cor_prog = '#ff7f0e'
            status = '⚠️ PRÓXIMO DA META'
        else:
            cor_prog = '#d62728'
            status = '❌ ABAIXO DA META'

        pct_bar = min(pct, 100)
        with cols_meta[i]:
            st.markdown(f'''
            <div style="background:#1a1a2e; border-radius:14px; padding:20px; color:white; text-align:center; box-shadow:0 3px 12px rgba(0,0,0,0.2);">
                <div style="font-size:0.8rem; letter-spacing:1px; color:#aaa; text-transform:uppercase; margin-bottom:4px;">{estacao}</div>
                <div style="font-size:2.2rem; font-weight:800; color:white; margin:4px 0;">{media_b:,.0f}</div>
                <div style="font-size:0.85rem; color:#bbb; margin-bottom:10px;">Meta: {meta_b:,} pçs/dia</div>
                <div style="background:#333; border-radius:8px; height:14px; overflow:hidden; margin:8px 0;">
                    <div style="width:{pct_bar:.0f}%; height:100%; background:{cor_prog}; border-radius:8px; transition:width 0.5s;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#999; margin-bottom:8px;">
                    <span>0</span><span>{meta_b:,}</span>
                </div>
                <div style="font-size:1.1rem; font-weight:700; color:{cor_prog};">{pct:.0f}%</div>
                <div style="font-size:0.78rem; color:{cor_prog}; margin-top:2px;">{status} ({diff:+,.0f})</div>
            </div>''', unsafe_allow_html=True)

    st.markdown("---")

    # Métricas por estação
    cols_est = st.columns(3)
    for i, estacao in enumerate(estacoes):
        df_est = df_filtrado[df_filtrado['ESTACAO'] == estacao]
        with cols_est[i]:
            st.markdown(f"#### {estacao}")
            dias_est = df_est['DATA'].dt.date.nunique()
            pecas_est = df_est['QUANTIDADE'].sum()
            media_pecas_est = pecas_est / max(dias_est, 1)
            meta_est = METAS[estacao]
            pct_meta = (media_pecas_est / meta_est * 100) if meta_est > 0 else 0
            delta_meta = media_pecas_est - meta_est

            st.metric("Total Peças", f"{pecas_est:,.0f}")
            st.metric("Dias Trabalhados", f"{dias_est}")
            st.metric("Média Peças/Dia", f"{media_pecas_est:,.0f}", delta=f"{delta_meta:+,.0f} vs Meta {meta_est:,}")
            st.metric("% da Meta", f"{pct_meta:.1f}%")

    st.markdown("---")

    # Produção diária por estação
    st.markdown("#### 📈 Produção Diária por Estação (com Metas)")
    prod_est_dia = df_filtrado.groupby(['DATA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
    fig_est1 = px.line(prod_est_dia, x='DATA', y='QUANTIDADE', color='ESTACAO',
                       labels={'DATA': 'Data', 'QUANTIDADE': 'Peças', 'ESTACAO': 'Estação'},
                       color_discrete_map=cores_estacao, markers=True)
    for est_nome, meta_val in METAS.items():
        fig_est1.add_hline(y=meta_val, line_dash="dot", line_width=1.5,
                           line_color=cores_estacao[est_nome],
                           annotation_text=f"Meta {est_nome}: {meta_val:,}",
                           annotation_position="top left",
                           annotation_font_size=10,
                           annotation_font_color=cores_estacao[est_nome],
                           opacity=0.5)
    fig_est1.update_layout(height=500, margin=dict(l=20, r=20, t=30, b=20))
    fig_est1.update_xaxes(tickformat='%d/%m/%Y')
    st.plotly_chart(fig_est1, width='stretch')

    # Análise detalhada por estação
    st.markdown("#### 📊 Análise Detalhada por Estação")

    for estacao in estacoes:
        df_est = df_filtrado[df_filtrado['ESTACAO'] == estacao]
        if df_est.empty:
            continue

        with st.expander(f"📐 {estacao} - Análise Detalhada", expanded=False):
            col_e1, col_e2 = st.columns(2)

            with col_e1:
                prod_dia_est = df_est.groupby('DATA')['QUANTIDADE'].sum().reset_index().sort_values('DATA')
                fig_tend = go.Figure()
                fig_tend.add_trace(go.Bar(
                    x=prod_dia_est['DATA'], y=prod_dia_est['QUANTIDADE'],
                    name='Peças/Dia', marker_color=cores_estacao[estacao], opacity=0.7
                ))
                if len(prod_dia_est) >= 5:
                    prod_dia_est['MM5'] = prod_dia_est['QUANTIDADE'].rolling(5).mean()
                    fig_tend.add_trace(go.Scatter(
                        x=prod_dia_est['DATA'], y=prod_dia_est['MM5'],
                        name='Média Móvel (5d)', line=dict(color='red', width=2)
                    ))
                media_est = prod_dia_est['QUANTIDADE'].mean()
                fig_tend.add_hline(y=media_est, line_dash="dash", line_color="gray",
                                   annotation_text=f"Média: {media_est:,.0f}")
                meta_estacao = METAS.get(estacao, 0)
                if meta_estacao > 0:
                    fig_tend.add_hline(y=meta_estacao, line_dash="dot", line_color="green", line_width=2,
                                       annotation_text=f"🎯 Meta: {meta_estacao:,}",
                                       annotation_position="top left")
                fig_tend.update_layout(title=f"Produção Diária - {estacao}",
                                       height=400, margin=dict(l=20, r=20, t=40, b=20))
                fig_tend.update_xaxes(tickformat='%d/%m/%Y')
                st.plotly_chart(fig_tend, width='stretch')

            with col_e2:
                prod_dia_est2 = df_est.groupby('DATA')['QUANTIDADE'].sum().reset_index()
                fig_box = px.box(prod_dia_est2, y='QUANTIDADE',
                                 color_discrete_sequence=[cores_estacao[estacao]],
                                 labels={'QUANTIDADE': 'Peças/Dia'})
                meta_box = METAS.get(estacao, 0)
                if meta_box > 0:
                    fig_box.add_hline(y=meta_box, line_dash="dot", line_color="green", line_width=2,
                                      annotation_text=f"🎯 Meta: {meta_box:,}",
                                      annotation_position="top left")
                fig_box.update_layout(title=f"Consistência - {estacao}",
                                      height=400, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_box, width='stretch')

            # Tabela de estatísticas
            prod_dia_stats = df_est.groupby('DATA')['QUANTIDADE'].sum()
            meta_est_val = METAS.get(estacao, 0)
            pct_meta_est = (prod_dia_stats.mean() / meta_est_val * 100) if meta_est_val > 0 else 0
            dias_acima = (prod_dia_stats >= meta_est_val).sum() if meta_est_val > 0 else 0
            dias_total_est = len(prod_dia_stats)
            stats_df = pd.DataFrame({
                'Estatística': ['🎯 META DIÁRIA', '📊 Média/Dia', '% da Meta', 'Dias Acima da Meta',
                                'Mediana/Dia', 'Desvio Padrão', 'Mínimo/Dia', 'Máximo/Dia',
                                'Coef. Variação (%)', 'Total Peças'],
                'Valor': [
                    f"{meta_est_val:,} peças",
                    f"{prod_dia_stats.mean():,.0f}",
                    f"{pct_meta_est:.1f}%",
                    f"{dias_acima} de {dias_total_est} ({(dias_acima/max(dias_total_est,1)*100):.0f}%)",
                    f"{prod_dia_stats.median():,.0f}",
                    f"{prod_dia_stats.std():,.0f}" if len(prod_dia_stats) > 1 else "N/A",
                    f"{prod_dia_stats.min():,.0f}",
                    f"{prod_dia_stats.max():,.0f}",
                    f"{(prod_dia_stats.std()/prod_dia_stats.mean()*100):,.1f}%" if prod_dia_stats.mean() > 0 and len(prod_dia_stats) > 1 else "N/A",
                    f"{df_est['QUANTIDADE'].sum():,.0f}"
                ]
            })
            st.dataframe(stats_df, width='stretch', hide_index=True)

    # Comparativo semanal
    st.markdown("#### 📅 Produção Semanal Comparativa (com Meta Semanal)")
    prod_semanal = df_filtrado.groupby(['SEMANA', 'ESTACAO'])['QUANTIDADE'].sum().reset_index()
    dias_por_semana = df_filtrado.groupby(['SEMANA', 'ESTACAO'])['DATA'].apply(lambda x: x.dt.date.nunique()).reset_index(name='DIAS')
    prod_semanal = prod_semanal.merge(dias_por_semana, on=['SEMANA', 'ESTACAO'], how='left')
    prod_semanal['META_SEMANAL'] = prod_semanal.apply(lambda r: METAS.get(r['ESTACAO'], 0) * r['DIAS'], axis=1)
    fig_sem = go.Figure()
    for est in estacoes:
        df_s = prod_semanal[prod_semanal['ESTACAO'] == est]
        fig_sem.add_trace(go.Bar(
            x=df_s['SEMANA'], y=df_s['QUANTIDADE'],
            name=f'{est} (Real)', marker_color=cores_estacao[est], opacity=0.8
        ))
        fig_sem.add_trace(go.Scatter(
            x=df_s['SEMANA'], y=df_s['META_SEMANAL'],
            name=f'{est} (Meta)', mode='lines+markers',
            line=dict(color=cores_estacao[est], dash='dot', width=2),
            marker=dict(symbol='diamond', size=8)
        ))
    fig_sem.update_layout(
        height=500, margin=dict(l=20, r=20, t=30, b=20),
        barmode='group', xaxis_title='Semana', yaxis_title='Peças',
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig_sem, width='stretch')


# =====================================================================
# RODAPÉ
# =====================================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.85rem;'>"
    "✂️ Dashboard Controle de Corte - Mantas | Alimentado pela planilha CONTROLE GERAL MANTAS.xlsx | "
    f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    "</div>",
    unsafe_allow_html=True
)
