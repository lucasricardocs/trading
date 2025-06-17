# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import io
import time
import threading
from datetime import datetime, timedelta, date
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM"
WORKSHEET_NAME = "dados"

# --- Configuração da Página e CSS Customizado (Tema Escuro) ---
st.set_page_config(
    page_title="Análise de Trading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Geral para o tema escuro */
    body {
        background-color: #1a1a1a;
        color: #f0f0f0;
    }
    .stApp {
        background-color: #1a1a1a;
    }
    /* Containers e cards */
    .st-emotion-cache-1wmy9hp {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #3a3a3a;
    }
    .st-emotion-cache-1r6y40v {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #3a3a3a;
    }
    .st-emotion-cache-1cyp85g {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #3a3a3a;
    }
    /* Sidebar */
    .st-emotion-cache-1d391kg {
        background-color: #2a2a2a;
        border-right: 1px solid #3a3a3a;
    }
    /* Títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #f0f0f0;
    }
    /* Métricas */
    [data-testid="stMetric"] {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        border: 1px solid #3a3a3a;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] > div {
        color: #cccccc;
    }
    [data-testid="stMetricValue"] {
        color: #f0f0f0;
    }
    [data-testid="stMetricDelta"] {
        color: #f0f0f0;
    }
    /* Inputs */
    .st-emotion-cache-vj1c9o {
        background-color: #3a3a3a;
        color: #f0f0f0;
    }
    .st-emotion-cache-13ln4gm {
        background-color: #3a3a3a;
        color: #f0f0f0;
    }
    /* Botões */
    .st-emotion-cache-l9rwg9 {
        background-color: #007bff;
        color: white;
    }
    .st-emotion-cache-l9rwg9:hover {
        background-color: #0056b3;
    }
    /* Mensagens de sucesso/erro/info */
    [data-testid="stSuccessAlert"] {
        background-color: #28a745;
        color: white;
    }
    [data-testid="stErrorAlert"] {
        background-color: #dc3545;
        color: white;
    }
    [data-testid="stInfoAlert"] {
        background-color: #17a2b8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Funções de Autenticação e Acesso ao Google Sheets (Estrutura Melhorada) ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets. Configure o arquivo .streamlit/secrets.toml")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict:
            st.error("As credenciais do Google em st.secrets estão vazias.")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro de autenticação com Google: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"Planilha com ID '{SPREADSHEET_ID}' não encontrada.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha '{WORKSHEET_NAME}': {e}")
            return None
    return None

@st.cache_data(ttl=60)
def load_data():
    """Lê todos os registros da planilha de trading e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.info("A planilha de trading está vazia.")
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            # Processamento das colunas existentes
            if 'ABERTURA' in df.columns:
                df['ABERTURA'] = pd.to_datetime(df['ABERTURA'], errors='coerce')
            
            if 'RESULTADO' in df.columns:
                df['RESULTADO'] = df['RESULTADO'].astype(str).str.replace(',', '.', regex=False)
                df['RESULTADO'] = pd.to_numeric(df['RESULTADO'], errors='coerce').fillna(0)
            
            if 'QUANTIDADE' in df.columns:
                df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0)

            # NOVA FUNCIONALIDADE: Calcular custo e resultado líquido
            if 'ATIVO' in df.columns and 'QUANTIDADE' in df.columns and 'RESULTADO' in df.columns:
                # Definir custos por ativo
                custos = {'WDOFUT': 1.09, 'WINFUT': 0.39}
                
                # Calcular custo total por operação
                df['CUSTO'] = df.apply(lambda row: 
                    custos.get(row['ATIVO'], 0) * row['QUANTIDADE'] * 2, axis=1)
                
                # Calcular resultado líquido (sempre subtrai o custo)
                df['RESULTADO_LIQUIDO'] = df['RESULTADO'] - df['CUSTO']
            else:
                df['CUSTO'] = 0
                df['RESULTADO_LIQUIDO'] = df.get('RESULTADO', 0)

            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
    """Adiciona uma nova operação à planilha."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            resultado_str = str(resultado).replace(',', '.')
            worksheet.append_row([ativo, data_abertura.strftime('%Y-%m-%d'), quantidade, tipo_operacao, resultado_str])
            return True
        except Exception as e:
            st.error(f"Erro ao adicionar dados na planilha: {e}")
            return False
    return False

def create_3d_heatmap(df_heatmap_final):
    """Cria um heatmap 3D dos resultados de trading com design consistente."""
    
    # Preparar dados para o gráfico 3D
    df_3d = df_heatmap_final.copy()
    df_3d = df_3d[df_3d['RESULTADO_LIQUIDO'] != 0]  # Remover dias sem trades
    
    if df_3d.empty:
        return None
    
    # Configurar matplotlib para tema escuro
    plt.style.use('dark_background')
    
    # Criar figura 3D
    fig = plt.figure(figsize=(16, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Preparar dados
    x = df_3d['Semana_Ajustada']
    y = df_3d['DiaSemana']
    z = np.zeros_like(x)
    dx = dy = 0.8
    dz = np.abs(df_3d['RESULTADO_LIQUIDO'])  # Altura baseada no valor absoluto
    
    # Definir cores baseadas no resultado (MESMO ESQUEMA DO 2D)
    valor_max = abs(df_heatmap_final['RESULTADO_LIQUIDO']).max()
    colors = []
    for resultado in df_3d['RESULTADO_LIQUIDO']:
        if resultado > 0:
            # Verde escuro (#1a9850) - mesmo do heatmap 2D
            intensity = min(resultado / valor_max, 1.0) if valor_max > 0 else 0.5
            colors.append((0.1, 0.6 * intensity + 0.4, 0.31, 0.8))  # Verde escuro
        else:
            # Vermelho escuro (#d73027) - mesmo do heatmap 2D
            intensity = min(abs(resultado) / valor_max, 1.0) if valor_max > 0 else 0.5
            colors.append((0.84 * intensity + 0.16, 0.19, 0.15, 0.8))  # Vermelho escuro
    
    # Criar gráfico de barras 3D
    ax.bar3d(x, y, z, dx, dy, dz, color=colors, shade=True, alpha=0.8)
    
    # Configurar eixos (MESMO ESTILO DO 2D)
    ax.set_xlabel('Semanas do Ano', fontsize=12, color='white')
    ax.set_ylabel('Dia da Semana', fontsize=12, color='white')
    ax.set_zlabel('Resultado Líquido (R$)', fontsize=12, color='white')
    
    # Configurar labels dos dias da semana (MESMO DO 2D)
    ax.set_yticks(range(7))
    ax.set_yticklabels(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'])
    
    # Título (MESMO PADRÃO DO 2D)
    ano_atual = datetime.now().year
    ax.set_title(f'Heatmap 3D - Resultados Líquidos Diários - {ano_atual}', 
                fontsize=16, color='white', pad=20)
    
    # Configurar cores dos eixos para tema escuro
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.zaxis.label.set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.tick_params(axis='z', colors='white')
    
    # Configurar fundo (TRANSPARENTE COMO O 2D)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.grid(True, alpha=0.3)
    
    # Salvar em buffer para exibir no Streamlit
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                facecolor='#1a1a1a', edgecolor='none')
    buffer.seek(0)
    plt.close()
    
    return buffer

# --- Interface Principal ---
st.title("📈 Análise de Operações de Trading")

# --- Sidebar: Entrada de Dados ---
with st.sidebar:
    st.header("➕ Nova Operação")
    
    with st.form("nova_operacao"):
        ativo = st.selectbox("Ativo", ["WDOFUT", "WINFUT"])
        data_abertura = st.date_input("Data da Operação", value=date.today())
        quantidade = st.number_input("Quantidade de Contratos", min_value=1, value=1)
        tipo_operacao = st.selectbox("Tipo", ["Compra", "Venda"])
        
        resultado_input = st.text_input("Resultado em R$", value="0,00", 
                                      help="Use vírgula como separador decimal.")
        
        try:
            resultado = float(resultado_input.replace(',', '.'))
        except ValueError:
            st.error("Por favor, insira um valor numérico válido para o Resultado.")
            resultado = 0.0

        submitted = st.form_submit_button("Adicionar Operação")
        
        if submitted:
            if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
                st.success("Operação adicionada com sucesso!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Erro ao adicionar operação")

# --- Carregar Dados ---
df = load_data()

# --- Sidebar: Filtros e Resumos ---
with st.sidebar:
    st.header("🔎 Filtro de Período")
    if not df.empty and 'ABERTURA' in df.columns:
        data_min = df['ABERTURA'].min().date()
        data_max = df['ABERTURA'].max().date()
        data_inicial, data_final = st.date_input(
            "Selecione o período para análise",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max
        )
        df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
    else:
        df_filtrado = df.copy()

    # Resumo por ativo com custo e resultado líquido
    st.header("📊 Resumo por Ativo")
    if not df_filtrado.empty:
        resumo_ativo = df_filtrado.groupby('ATIVO').agg({
            'RESULTADO': ['count', 'sum'],
            'CUSTO': 'sum',
            'RESULTADO_LIQUIDO': ['sum', 'mean']
        }).round(2)
        
        # Achatar as colunas
        resumo_ativo.columns = ['Nº Trades', 'Total Bruto (R$)', 'Custo Total (R$)', 'Total Líquido (R$)', 'Média Líquida (R$)']
        resumo_ativo = resumo_ativo.reset_index()
        
        st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)

# --- Corpo Principal ---
if df.empty:
    st.info("📊 Nenhuma operação encontrada. Adicione sua primeira operação usando o formulário na barra lateral.")
else:
    # Implementação com auto-dismiss em 2 segundos
    success_container = st.empty()
    success_container.success(f"✅ {len(df)} operações carregadas com sucesso!")
    
    # Usar threading para não travar a aplicação
    def clear_message():
        time.sleep(2)
        success_container.empty()
    
    threading.Thread(target=clear_message).start()
    
    with st.expander("📋 Ver todas as operações"):
        st.dataframe(df, use_container_width=True)

    # --- Métricas e Análises (USANDO RESULTADO LÍQUIDO) ---
    if 'RESULTADO_LIQUIDO' in df_filtrado.columns and 'ABERTURA' in df_filtrado.columns:
        # Calcular métricas com resultado líquido
        valor_total = df_filtrado['RESULTADO_LIQUIDO'].sum()
        valor_total_bruto = df_filtrado['RESULTADO'].sum()
        custo_total = df_filtrado['CUSTO'].sum()
        media_resultado = df_filtrado['RESULTADO_LIQUIDO'].mean()
        
        # Agrupar por data usando resultado líquido
        df_por_dia = df_filtrado.groupby(df_filtrado['ABERTURA'].dt.date).agg({
            'RESULTADO_LIQUIDO': 'sum',
            'RESULTADO': 'sum',
            'CUSTO': 'sum'
        }).reset_index()
        df_por_dia.columns = ['Data', 'Resultado_Liquido_Dia', 'Resultado_Bruto_Dia', 'Custo_Dia']
        
        if not df_por_dia.empty:
            melhor_dia = df_por_dia.loc[df_por_dia['Resultado_Liquido_Dia'].idxmax()]
            pior_dia = df_por_dia.loc[df_por_dia['Resultado_Liquido_Dia'].idxmin()]
        else:
            melhor_dia = pior_dia = {'Data': None, 'Resultado_Liquido_Dia': 0}
        
        # Outras métricas usando resultado líquido
        total_trades = len(df_filtrado)
        trades_ganhadores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] > 0])
        trades_perdedores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] < 0])
        taxa_acerto = (trades_ganhadores / total_trades * 100) if total_trades > 0 else 0
        
        # Exibir métricas atualizadas
        st.header("📊 Resumo das Operações")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Resultado Líquido Total",
                value=f"R$ {valor_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=f"Bruto: R$ {valor_total_bruto:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
            )
        
        with col2:
            st.metric(
                label="💸 Custo Total",
                value=f"R$ {custo_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=f"Impacto: {(custo_total/valor_total_bruto*100):.1f}%" if valor_total_bruto != 0 else "0%"
            )
        
        with col3:
            st.metric(
                label="📈 Média Líquida por Trade",
                value=f"R$ {media_resultado:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=f"{media_resultado:+.2f}".replace('.', 'X').replace(',', '.').replace('X', ',') if media_resultado != 0 else None
            )
        
        with col4:
            st.metric(
                label="🎯 Taxa de Acerto (Líquida)",
                value=f"{taxa_acerto:.1f}%",
                delta=f"{trades_ganhadores}/{total_trades}"
            )
        
        # Segunda linha de métricas
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                label="🟢 Melhor Dia (Líquido)",
                value=f"R$ {melhor_dia['Resultado_Liquido_Dia']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=melhor_dia['Data'].strftime('%d/%m/%Y') if melhor_dia['Data'] else ""
            )
        
        with col6:
            st.metric(
                label="🔴 Pior Dia (Líquido)",
                value=f"R$ {pior_dia['Resultado_Liquido_Dia']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=pior_dia['Data'].strftime('%d/%m/%Y') if pior_dia['Data'] else ""
            )
        
        with col7:
            maior_ganho = df_filtrado['RESULTADO_LIQUIDO'].max()
            st.metric(
                label="💎 Maior Ganho Líquido",
                value=f"R$ {maior_ganho:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta="Individual"
            )
        
        with col8:
            maior_perda = df_filtrado['RESULTADO_LIQUIDO'].min()
            st.metric(
                label="💸 Maior Perda Líquida",
                value=f"R$ {maior_perda:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta="Individual"
            )

        # --- Visualizações ---
        st.header("📈 Visualizações")
        
        # 1. Heatmaps de Resultados Líquidos Diários (3D ACIMA DO 2D)
        st.subheader("🔥 Heatmaps de Resultados Líquidos Diários (Ano Completo)")
        
        # Preparar dados para ambos os heatmaps
        df_heatmap = df.copy()
        if not df_heatmap.empty and 'ABERTURA' in df_heatmap.columns:
            df_heatmap['Data'] = df_heatmap['ABERTURA'].dt.date
            df_heatmap_grouped = df_heatmap.groupby('Data')['RESULTADO_LIQUIDO'].sum().reset_index()
            
            ano_atual = datetime.now().year
            data_inicio = pd.Timestamp(f'{ano_atual}-01-01').date()
            data_fim = pd.Timestamp(f'{ano_atual}-12-31').date()
            
            date_range = pd.date_range(start=data_inicio, end=data_fim, freq='D')
            df_complete = pd.DataFrame({'Data': date_range.date})
            df_heatmap_final = df_complete.merge(df_heatmap_grouped, on='Data', how='left')
            df_heatmap_final['RESULTADO_LIQUIDO'] = df_heatmap_final['RESULTADO_LIQUIDO'].fillna(0)
            
            df_heatmap_final['Data_dt'] = pd.to_datetime(df_heatmap_final['Data'])
            df_heatmap_final['Semana'] = df_heatmap_final['Data_dt'].dt.isocalendar().week
            df_heatmap_final['DiaSemana'] = df_heatmap_final['Data_dt'].dt.dayofweek
            
            primeira_semana = df_heatmap_final['Semana'].min()
            df_heatmap_final['Semana_Ajustada'] = df_heatmap_final['Semana'] - primeira_semana + 1
            
            nomes_dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
            df_heatmap_final['Nome_Dia'] = df_heatmap_final['DiaSemana'].map(lambda x: nomes_dias[x])
            
            # HEATMAP 3D (PRIMEIRO - ACIMA)
            st.markdown("### 🎯 Heatmap 3D")
            st.info("**Heatmap 3D**: Altura das barras representa o valor absoluto do resultado. Verde = Lucro, Vermelho = Prejuízo")
            
            heatmap_3d_buffer = create_3d_heatmap(df_heatmap_final)
            
            if heatmap_3d_buffer:
                st.image(heatmap_3d_buffer, use_column_width=True)
            else:
                st.warning("Não há dados suficientes para gerar o heatmap 3D. Adicione mais operações.")
            
            # HEATMAP 2D (SEGUNDO - ABAIXO)
            st.markdown("### 📊 Heatmap 2D")
            
            valor_max = abs(df_heatmap_final['RESULTADO_LIQUIDO']).max()
            
            heatmap_2d = alt.Chart(df_heatmap_final).mark_rect(
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X('Semana_Ajustada:O', 
                        title='Semanas do Ano',
                        axis=alt.Axis(labelAngle=0, tickCount=12)),
                y=alt.Y('DiaSemana:O', 
                        title='',
                        axis=alt.Axis(labels=False, ticks=False),
                        scale=alt.Scale(domain=[0, 1, 2, 3, 4, 5, 6])),
                color=alt.Color(
                    'RESULTADO_LIQUIDO:Q',
                    scale=alt.Scale(
                        domain=[-valor_max if valor_max > 0 else -1, 0, valor_max if valor_max > 0 else 1],
                        range=['#d73027', '#f1f1f1', '#1a9850'],
                        type='linear'
                    ),
                    title='Resultado Líquido (R$)',
                    legend=alt.Legend(orient='right')
                ),
                tooltip=[
                    alt.Tooltip('Data:T', title='Data'),
                    alt.Tooltip('RESULTADO_LIQUIDO:Q', format='.2f', title='Resultado Líquido (R$)'),
                    alt.Tooltip('Nome_Dia:N', title='Dia da Semana')
                ]
            ).properties(
                width='container',
                height=150,
                title=alt.TitleParams(
                    text=f'Heatmap 2D - Resultados Líquidos Diários - {ano_atual}',
                    fontSize=16,
                    anchor='start'
                ),
                background='transparent'
            ).resolve_scale(
                color='independent'
            )
            
            st.altair_chart(heatmap_2d, use_container_width=True)
        
        # 2. Gráfico de área acumulada com cores condicionais - usando resultado líquido
        st.subheader("📊 Evolução Acumulada dos Resultados Líquidos")
        
        if not df_por_dia.empty:
            df_area = df_por_dia.copy().sort_values('Data')
            df_area['Resultado_Liquido_Acumulado'] = df_area['Resultado_Liquido_Dia'].cumsum()
            
            # Adicionar coluna de cor baseada no valor acumulado
            df_area['Cor_Area'] = df_area['Resultado_Liquido_Acumulado'].apply(
                lambda x: 'Positivo' if x >= 0 else 'Negativo'
            )
            
            area_chart = alt.Chart(df_area).mark_area(
                line={'color': '#ffffff', 'strokeWidth': 2},
                opacity=0.7
            ).encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Resultado_Liquido_Acumulado:Q', title='Resultado Líquido Acumulado (R$)'),
                color=alt.Color(
                    'Cor_Area:N',
                    scale=alt.Scale(
                        domain=['Negativo', 'Positivo'],
                        range=['#d73027', '#1a9850']
                    ),
                    legend=None
                ),
                tooltip=[
                    'Data:T', 
                    alt.Tooltip('Resultado_Liquido_Acumulado:Q', format='.2f', title='Líquido Acumulado (R$)'), 
                    alt.Tooltip('Resultado_Liquido_Dia:Q', format='.2f', title='Líquido Dia (R$)'),
                    alt.Tooltip('Custo_Dia:Q', format='.2f', title='Custo Dia (R$)')
                ]
            ).properties(
                width='container',
                height=500,
                title='Evolução do Resultado Líquido Acumulado',
                background='transparent'
            )
            
            st.altair_chart(area_chart, use_container_width=True)

        # 3. Gráfico de barras diário - usando resultado líquido
        st.subheader("📅 Evolução Diária dos Resultados Líquidos")
        if not df_por_dia.empty:
            bar_chart = alt.Chart(df_por_dia).mark_bar().encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Resultado_Liquido_Dia:Q', title='Resultado Líquido do Dia (R$)'),
                color=alt.condition(
                    alt.datum.Resultado_Liquido_Dia > 0,
                    alt.value('#1a9850'),
                    alt.value('#d73027')
                ),
                tooltip=[
                    'Data:T', 
                    alt.Tooltip('Resultado_Liquido_Dia:Q', format='.2f', title='Líquido (R$)'),
                    alt.Tooltip('Resultado_Bruto_Dia:Q', format='.2f', title='Bruto (R$)'),
                    alt.Tooltip('Custo_Dia:Q', format='.2f', title='Custo (R$)')
                ]
            ).properties(
                width='container',
                height=500,
                title='Evolução Diária do Resultado Líquido',
                background='transparent'
            )
            st.altair_chart(bar_chart, use_container_width=True)
        
        # 4. Histograma e gráfico radial - usando resultado líquido
        st.subheader("📈 Distribuição de Resultados Líquidos e Performance")
        
        col_hist, col_radial = st.columns([2, 1])
        
        with col_hist:
            hist_data = df_filtrado.copy()
            hist_data['Cor'] = hist_data['RESULTADO_LIQUIDO'].apply(lambda x: 'Ganho' if x > 0 else 'Perda' if x < 0 else 'Neutro')
            
            histogram = alt.Chart(hist_data).mark_bar().encode(
                x=alt.X('RESULTADO_LIQUIDO:Q', bin=alt.Bin(maxbins=20), title='Resultado Líquido (R$)'),
                y=alt.Y('count():Q', title='Frequência'),
                color=alt.Color(
                    'Cor:N',
                    scale=alt.Scale(
                        domain=['Perda', 'Neutro', 'Ganho'],
                        range=['#d73027', '#cccccc', '#1a9850']
                    ),
                    title='Tipo'
                ),
                tooltip=[alt.Tooltip('RESULTADO_LIQUIDO:Q', format='.2f'), 'count():Q']
            ).properties(
                width='container',
                height=500,
                title='Distribuição dos Resultados Líquidos',
                background='transparent'
            )
            
            st.altair_chart(histogram, use_container_width=True)
        
        with col_radial:
            pizza_data = pd.DataFrame({
                'Tipo': ['Ganhadores', 'Perdedores'],
                'Quantidade': [trades_ganhadores, trades_perdedores],
                'Cor': ['#1a9850', '#d73027']
            })
            
            if trades_perdedores == 0:
                pizza_data = pizza_data[pizza_data['Quantidade'] > 0]
            
            pie_chart = alt.Chart(pizza_data).mark_arc(
                innerRadius=50,
                outerRadius=120
            ).encode(
                theta=alt.Theta("Quantidade:Q", stack=True),
                color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Ganhadores", "Perdedores"], range=["#1a9850", "#d73027"])),
                tooltip=["Tipo:N", "Quantidade:Q"]
            ).properties(
                width='container',
                height=500,
                title="Proporção de Trades Ganhadores/Perdedores (Líquido)",
                background='transparent'
            )
            
            st.altair_chart(pie_chart, use_container_width=True)

# --- Rodapé ---
st.markdown(
    """
    <hr style="border:1px solid #444;margin-top:2em;margin-bottom:1em">
    <div style="text-align:center;color:#888;font-size:0.95em;">
        Desenvolvido com <b>Python</b> • Powered by <b>Streamlit</b> + <b>Altair</b> • Dados salvos em <b>Google Sheets</b><br>
        <span style="font-size:0.85em;">© {ano} - Este painel é apenas para fins informativos e educacionais.</span>
    </div>
    """.format(ano=datetime.now().year),
    unsafe_allow_html=True
)
