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
import calendar
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

# --- Funções de Autenticação e Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google ('google_credentials') não encontradas em st.secrets.")
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

            # Calcular custo e resultado líquido
            if 'ATIVO' in df.columns and 'QUANTIDADE' in df.columns and 'RESULTADO' in df.columns:
                custos = {'WDOFUT': 1.09, 'WINFUT': 0.39}
                df['CUSTO'] = df.apply(lambda row: 
                    custos.get(row['ATIVO'], 0) * row['QUANTIDADE'] * 2, axis=1)
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

def calcular_largura_adaptativa(num_elementos):
    """Calcula a largura das barras baseada no número de elementos."""
    if num_elementos <= 5:
        return 0.9
    elif num_elementos <= 15:
        return 0.7
    elif num_elementos <= 30:
        return 0.5
    elif num_elementos <= 50:
        return 0.3
    else:
        return 0.2

def create_3d_heatmap(df_heatmap_final):
    """Cria um heatmap 3D estilo GitHub com fundo transparente."""
    
    plt.style.use('dark_background')
    
    fig = plt.figure(figsize=(18, 8))
    fig.patch.set_alpha(0.0)
    ax = fig.add_subplot(111, projection='3d')
    
    ano_atual = datetime.now().year
    data_inicio = pd.Timestamp(f'{ano_atual}-01-01')
    data_fim = pd.Timestamp(f'{ano_atual}-12-31')
    
    todas_datas = pd.date_range(start=data_inicio, end=data_fim, freq='D')
    
    semanas = []
    dias_semana = []
    resultados = []
    
    primeiro_domingo = data_inicio - pd.Timedelta(days=data_inicio.weekday() + 1)
    if data_inicio.weekday() == 6:
        primeiro_domingo = data_inicio
    
    for data in todas_datas:
        dias_desde_inicio = (data - primeiro_domingo).days
        semana = dias_desde_inicio // 7
        dia_semana = data.weekday()
        
        resultado_dia = df_heatmap_final[df_heatmap_final['Data'] == data.date()]
        if not resultado_dia.empty:
            resultado = resultado_dia['RESULTADO_LIQUIDO'].iloc[0]
        else:
            resultado = 0
        
        semanas.append(semana)
        dias_semana.append(dia_semana)
        resultados.append(resultado)
    
    x = np.array(semanas)
    y = np.array(dias_semana)
    z = np.zeros_like(x)
    
    dx = dy = 0.9
    dz = []
    
    for resultado in resultados:
        if resultado == 0:
            dz.append(0.1)
        else:
            altura = max(abs(resultado) / 100, 0.5)
            dz.append(altura)
    
    dz = np.array(dz)
    
    cores = []
    for resultado in resultados:
        if resultado > 0:
            if resultado <= 50:
                cores.append('#0e4429')
            elif resultado <= 100:
                cores.append('#006d32')
            elif resultado <= 200:
                cores.append('#26a641')
            else:
                cores.append('#39d353')
        elif resultado < 0:
            if resultado >= -50:
                cores.append('#450a0a')
            elif resultado >= -100:
                cores.append('#7f1d1d')
            elif resultado >= -200:
                cores.append('#dc2626')
            else:
                cores.append('#f87171')
        else:
            cores.append('#161b22')
    
    ax.bar3d(x, y, z, dx, dy, dz, color=cores, shade=False, alpha=0.9)
    
    ax.set_xlabel('Semanas', fontsize=12, color='#8b949e')
    ax.set_ylabel('Dia da Semana', fontsize=12, color='#8b949e')
    ax.set_zlabel('Resultado (R$)', fontsize=12, color='#8b949e')
    
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_yticklabels(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'])
    
    ax.tick_params(axis='x', colors='#8b949e')
    ax.tick_params(axis='y', colors='#8b949e')
    ax.tick_params(axis='z', colors='#8b949e')
    
    plt.title(f'Contribuições de Trading - {ano_atual}', 
              fontsize=14, color='#f0f6fc', pad=20)
    
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('none')
    ax.yaxis.pane.set_edgecolor('none')
    ax.zaxis.pane.set_edgecolor('none')
    ax.grid(False)
    
    ax.view_init(elev=30, azim=-60)
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                facecolor='none', edgecolor='none', transparent=True)
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

    st.header("📊 Resumo por Ativo")
    if not df_filtrado.empty:
        resumo_ativo = df_filtrado.groupby('ATIVO').agg({
            'RESULTADO': ['count', 'sum'],
            'CUSTO': 'sum',
            'RESULTADO_LIQUIDO': ['sum', 'mean']
        }).round(2)
        
        resumo_ativo.columns = ['Nº Trades', 'Total Bruto (R$)', 'Custo Total (R$)', 'Total Líquido (R$)', 'Média Líquida (R$)']
        resumo_ativo = resumo_ativo.reset_index()
        
        st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)

# --- Corpo Principal ---
if df.empty:
    st.info("📊 Nenhuma operação encontrada. Adicione sua primeira operação usando o formulário na barra lateral.")
else:
    # Mensagem auto-dismiss em 2 segundos
    success_container = st.empty()
    success_container.success(f"✅ {len(df)} operações carregadas com sucesso!")
    
    def clear_message():
        time.sleep(2)
        success_container.empty()
    
    threading.Thread(target=clear_message).start()
    
    with st.expander("📋 Ver todas as operações"):
        st.dataframe(df, use_container_width=True)

    # --- Métricas e Análises ---
    if 'RESULTADO_LIQUIDO' in df_filtrado.columns and 'ABERTURA' in df_filtrado.columns:
        valor_total = df_filtrado['RESULTADO_LIQUIDO'].sum()
        valor_total_bruto = df_filtrado['RESULTADO'].sum()
        custo_total = df_filtrado['CUSTO'].sum()
        media_resultado = df_filtrado['RESULTADO_LIQUIDO'].mean()
        
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
        
        total_trades = len(df_filtrado)
        trades_ganhadores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] > 0])
        trades_perdedores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] < 0])
        taxa_acerto = (trades_ganhadores / total_trades * 100) if total_trades > 0 else 0
        
        # Exibir métricas
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
        
        # Heatmaps Anuais
        st.subheader("🔥 Heatmaps Anuais")
        
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
            
            # Heatmap 3D
            heatmap_3d_buffer = create_3d_heatmap(df_heatmap_final)
            if heatmap_3d_buffer:
                st.image(heatmap_3d_buffer, use_column_width=True)
            
            # Heatmap 2D
            df_heatmap_2d = df_complete.merge(df_heatmap_grouped, on='Data', how='left')
            df_heatmap_2d['RESULTADO_LIQUIDO'] = df_heatmap_2d['RESULTADO_LIQUIDO'].fillna(0)
            
            df_heatmap_2d['Data_dt'] = pd.to_datetime(df_heatmap_2d['Data'])
            df_heatmap_2d['Mes'] = df_heatmap_2d['Data_dt'].dt.month
            df_heatmap_2d['DiaSemana'] = df_heatmap_2d['Data_dt'].dt.dayofweek
            
            valor_max = abs(df_heatmap_2d['RESULTADO_LIQUIDO']).max()
            
            heatmap_2d = alt.Chart(df_heatmap_2d).mark_rect(
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X('Mes:O', 
                        title='Meses do Ano',
                        axis=alt.Axis(
                            labelExpr="datum.value == 1 ? 'Jan' : datum.value == 2 ? 'Fev' : datum.value == 3 ? 'Mar' : datum.value == 4 ? 'Abr' : datum.value == 5 ? 'Mai' : datum.value == 6 ? 'Jun' : datum.value == 7 ? 'Jul' : datum.value == 8 ? 'Ago' : datum.value == 9 ? 'Set' : datum.value == 10 ? 'Out' : datum.value == 11 ? 'Nov' : 'Dez'"
                        )),
                y=alt.Y('DiaSemana:O', 
                        title='Dias da Semana',
                        axis=alt.Axis(
                            labelExpr="datum.value == 0 ? 'Seg' : datum.value == 1 ? 'Ter' : datum.value == 2 ? 'Qua' : datum.value == 3 ? 'Qui' : datum.value == 4 ? 'Sex' : datum.value == 5 ? 'Sáb' : 'Dom'"
                        )),
                color=alt.Color(
                    'RESULTADO_LIQUIDO:Q',
                    scale=alt.Scale(
                        domain=[-valor_max if valor_max > 0 else -1, 0, valor_max if valor_max > 0 else 1],
                        range=['#d73027', '#f1f1f1', '#1a9850']
                    ),
                    title='Resultado Líquido (R$)'
                ),
                tooltip=[
                    alt.Tooltip('Data:T', title='Data'),
                    alt.Tooltip('RESULTADO_LIQUIDO:Q', format='.2f', title='Resultado (R$)')
                ]
            ).properties(
                width='container',
                height=200,
                background='transparent'
            )
            
            st.altair_chart(heatmap_2d, use_container_width=True)
        
        # Evolução Acumulada
        st.subheader("📊 Evolução Acumulada")
        
        if not df_por_dia.empty:
            df_area = df_por_dia.copy().sort_values('Data')
            df_area['Resultado_Liquido_Acumulado'] = df_area['Resultado_Liquido_Dia'].cumsum()
            
            df_area['Cor_Area'] = df_area['Resultado_Liquido_Acumulado'].apply(
                lambda x: 'Positivo' if x >= 0 else 'Negativo'
            )
            
            area_chart = alt.Chart(df_area).mark_area(
                line={'color': '#ffffff', 'strokeWidth': 2},
                opacity=0.7
            ).encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Resultado_Liquido_Acumulado:Q', title='Resultado Acumulado (R$)'),
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
                    alt.Tooltip('Resultado_Liquido_Acumulado:Q', format='.2f', title='Acumulado (R$)'), 
                    alt.Tooltip('Resultado_Liquido_Dia:Q', format='.2f', title='Dia (R$)')
                ]
            ).properties(
                width='container',
                height=500,
                background='transparent'
            )
            
            st.altair_chart(area_chart, use_container_width=True)

        # Resultados por Trade
        st.subheader("📅 Resultados por Trade")
        if not df_filtrado.empty:
            df_trades = df_filtrado.copy()
            df_trades = df_trades.sort_values('ABERTURA')
            df_trades['Trade_Index'] = range(1, len(df_trades) + 1)
            
            num_trades = len(df_trades)
            largura_adaptativa = calcular_largura_adaptativa(num_trades)
            
            bar_trades = alt.Chart(df_trades).mark_bar(
                size=largura_adaptativa * 60,
                cornerRadius=3,
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X('Trade_Index:O', title='Trade'),
                y=alt.Y('RESULTADO_LIQUIDO:Q', title='Resultado (R$)'),
                color=alt.condition(
                    alt.datum.RESULTADO_LIQUIDO > 0,
                    alt.value('#1a9850'),
                    alt.value('#d73027')
                ),
                tooltip=[
                    alt.Tooltip('Trade_Index:O', title='Nº'),
                    alt.Tooltip('ABERTURA:T', title='Data', format='%d/%m'),
                    alt.Tooltip('ATIVO:N', title='Ativo'),
                    alt.Tooltip('RESULTADO_LIQUIDO:Q', format='.2f', title='Líquido (R$)')
                ]
            ).properties(
                width='container',
                height=500,
                background='transparent'
            )
            
            st.altair_chart(bar_trades, use_container_width=True)
        
        # Resultado Diário
        st.subheader("📅 Resultado Diário")
        
        col_hist, col_radial = st.columns([2, 1])
        
        with col_hist:
            if not df_por_dia.empty:
                num_dias = len(df_por_dia)
                largura_adaptativa = calcular_largura_adaptativa(num_dias)
                
                bar_daily = alt.Chart(df_por_dia).mark_bar(
                    size=largura_adaptativa * 80,
                    cornerRadius=4,
                    stroke='white',
                    strokeWidth=1.5
                ).encode(
                    x=alt.X('Data:T', title='Data', axis=alt.Axis(format='%d/%m')),
                    y=alt.Y('Resultado_Liquido_Dia:Q', title='Resultado (R$)'),
                    color=alt.condition(
                        alt.datum.Resultado_Liquido_Dia > 0,
                        alt.value('#1a9850'),
                        alt.value('#d73027')
                    ),
                    tooltip=[
                        alt.Tooltip('Data:T', title='Data', format='%d/%m'),
                        alt.Tooltip('Resultado_Liquido_Dia:Q', format='.2f', title='Líquido (R$)')
                    ]
                ).properties(
                    width='container',
                    height=500,
                    background='transparent'
                )
                
                st.altair_chart(bar_daily, use_container_width=True)
        
        with col_radial:
            pizza_data = pd.DataFrame({
                'Tipo': ['Ganhadores', 'Perdedores'],
                'Quantidade': [trades_ganhadores, trades_perdedores]
            })
            
            if trades_perdedores == 0:
                pizza_data = pizza_data[pizza_data['Quantidade'] > 0]
            
            pie_chart = alt.Chart(pizza_data).mark_arc(
                innerRadius=60,
                outerRadius=140,
                stroke='white',
                strokeWidth=2
            ).encode(
                theta=alt.Theta("Quantidade:Q", stack=True),
                color=alt.Color("Tipo:N", 
                               scale=alt.Scale(domain=["Ganhadores", "Perdedores"], 
                                             range=["#1a9850", "#d73027"])),
                tooltip=["Tipo:N", "Quantidade:Q"]
            ).properties(
                width='container',
                height=500,
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
