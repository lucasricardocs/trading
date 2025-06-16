import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import numpy as np
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configuração da página
st.set_page_config(
    page_title="Trading Activity Dashboard",
    page_icon="📈",
    layout="wide"
)

# Função para conectar com Google Sheets (leitura)
@st.cache_data(ttl=60)  # Cache por 1 minuto para dados mais atualizados
def load_data_from_sheets():
    """Carrega dados da planilha Google Sheets."""
    try:
        # Carrega as credenciais
        credentials = Credentials.from_service_account_info(
            st.secrets["google_credentials"],
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        # Constrói o serviço
        service = build('sheets', 'v4', credentials=credentials)
        
        # ID da planilha
        spreadsheet_id = st.secrets["SPREADSHEET_ID"]
        
        # Range de dados
        range_name = 'Sheet1!A:B'  # Apenas colunas Data e Total
        
        # Faz a requisição
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            return None
        
        # Converte para DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Converter tipos de dados
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
        
        # Remover linhas com dados inválidos
        df = df.dropna(subset=['Data', 'Total'])
        
        return df
        
    except Exception as e:
        st.error(f'Erro ao carregar dados do Google Sheets: {str(e)}')
        return None

# Função para enviar dados para Google Sheets
def append_data_to_sheets(df):
    """Envia dados processados para a planilha Google Sheets."""
    try:
        # Carrega as credenciais com permissão de escrita
        credentials = Credentials.from_service_account_info(
            st.secrets["google_credentials"],
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Constrói o serviço
        service = build('sheets', 'v4', credentials=credentials)
        
        # ID da planilha
        spreadsheet_id = st.secrets["SPREADSHEET_ID"]
        
        # Preparar dados para envio
        data_to_append = []
        
        for _, row in df.iterrows():
            data_to_append.append([
                row['Data'].strftime('%d/%m/%Y'),
                float(row['Total'])
            ])
        
        # Verificar se a planilha tem cabeçalhos
        range_name = 'Sheet1!A1:B1'
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # Se não houver cabeçalhos, adicionar
        if not values or values[0] != ['Data', 'Total']:
            header_body = {
                'values': [['Data', 'Total']]
            }
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Sheet1!A1:B1',
                valueInputOption='RAW',
                body=header_body
            ).execute()
        
        # Limpar dados existentes (exceto cabeçalho)
        clear_range = 'Sheet1!A2:B10000'
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=clear_range
        ).execute()
        
        # Adicionar novos dados
        if data_to_append:
            body = {
                'values': data_to_append
            }
            
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='Sheet1!A2:B2',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True
        
    except Exception as e:
        st.error(f'Erro ao enviar dados para Google Sheets: {str(e)}')
        return False

def process_trading_data(df):
    """Processa os dados de trading do CSV."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    
    # Procurar pela coluna de Data
    date_col = None
    for col in df.columns:
        if any(word in col for word in ['Abertura', 'Fechamento', 'Data', 'data']):
            date_col = col
            break
    
    if date_col is None:
        raise ValueError("Coluna de data não encontrada")
    
    # Procurar pela coluna Total
    total_col = None
    for col in df.columns:
        if 'Total' in col or 'total' in col:
            total_col = col
            break
    
    if total_col is None:
        raise ValueError("Coluna de total não encontrada")
    
    # Filtrar apenas linhas que têm data válida
    df = df[df[date_col].notna() & (df[date_col] != '')]
    
    # Converter Data para datetime
    def extract_date(date_str):
        try:
            if isinstance(date_str, str):
                date_part = date_str.split(' ')[0]
                return pd.to_datetime(date_part, format='%d/%m/%Y', errors='coerce')
            else:
                return pd.to_datetime(date_str, errors='coerce')
        except:
            return pd.NaT
    
    df['Data'] = df[date_col].apply(extract_date)
    
    # Converter Total para numérico
    if df[total_col].dtype == 'object':
        df['Total'] = df[total_col].astype(str).str.strip()
        df['Total'] = df['Total'].str.replace(',', '.')
        df['Total'] = df['Total'].str.replace(r'[^\d\-\.]', '', regex=True)
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    else:
        df['Total'] = pd.to_numeric(df[total_col], errors='coerce')
    
    # Remover linhas com datas ou totais inválidos
    df = df.dropna(subset=['Data', 'Total'])
    
    # Agrupar por data para somar os resultados do dia
    daily_data = df.groupby('Data').agg({
        'Total': 'sum'
    }).reset_index()
    
    return daily_data

def create_statistics_container(df):
    """Cria container com estatísticas detalhadas - versão tema escuro."""
    if df.empty:
        return
    
    # Calcular estatísticas
    valor_acumulado = df['Total'].sum()
    total_ganho = df[df['Total'] > 0]['Total'].sum()
    total_perda = df[df['Total'] < 0]['Total'].sum()
    dias_positivos = len(df[df['Total'] > 0])
    dias_negativos = len(df[df['Total'] < 0])
    dias_neutros = len(df[df['Total'] == 0])
    total_dias = len(df)
    
    # Calcular percentuais
    perc_dias_positivos = (dias_positivos / total_dias * 100) if total_dias > 0 else 0
    perc_dias_negativos = (dias_negativos / total_dias * 100) if total_dias > 0 else 0
    
    # Maior ganho e maior perda
    maior_ganho = df['Total'].max() if not df.empty else 0
    maior_perda = df['Total'].min() if not df.empty else 0
    
    # Média diária
    media_diaria = df[df['Total'] != 0]['Total'].mean() if len(df[df['Total'] != 0]) > 0 else 0
    
    # Container principal com estilo atualizado para tema escuro
    st.markdown("""
    <style>
    .stats-container-dark {
        background: linear-gradient(135deg, rgba(255, 107, 53, 0.15) 0%, rgba(247, 147, 30, 0.15) 100%);
        backdrop-filter: blur(20px);
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(255, 107, 53, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 107, 53, 0.2);
    }
    .stats-title-dark {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    .metric-card-dark {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(15px);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(255, 107, 53, 0.3);
        box-shadow: 0 4px 15px rgba(255, 107, 53, 0.2);
    }
    .metric-value-dark {
        font-size: 1.5rem;
        font-weight: bold;
        color: white;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
    }
    .metric-label-dark {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.5rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    .positive { color: #4ade80; text-shadow: 0 0 10px #4ade80; }
    .negative { color: #f87171; text-shadow: 0 0 10px #f87171; }
    .neutral { color: #fbbf24; text-shadow: 0 0 10px #fbbf24; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="stats-container-dark">', unsafe_allow_html=True)
    st.markdown('<div class="stats-title-dark">🔥 Estatísticas de Trading</div>', unsafe_allow_html=True)
    
    # Primeira linha - Valores principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        color_class = "positive" if valor_acumulado >= 0 else "negative"
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">💰 Valor Acumulado Total</div>
            <div class="metric-value-dark {color_class}">R$ {valor_acumulado:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">📈 Total de Ganhos</div>
            <div class="metric-value-dark positive">R$ {total_ganho:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">📉 Total de Perdas</div>
            <div class="metric-value-dark negative">R$ {total_perda:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        color_class = "positive" if media_diaria >= 0 else "negative"
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">📊 Média Diária</div>
            <div class="metric-value-dark {color_class}">R$ {media_diaria:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Segunda linha - Estatísticas de dias
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">✅ Dias Positivos</div>
            <div class="metric-value-dark positive">{dias_positivos} ({perc_dias_positivos:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">❌ Dias Negativos</div>
            <div class="metric-value-dark negative">{dias_negativos} ({perc_dias_negativos:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">🚀 Maior Ganho</div>
            <div class="metric-value-dark positive">R$ {maior_ganho:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card-dark">
            <div class="metric-label-dark">💥 Maior Perda</div>
            <div class="metric-value-dark negative">R$ {maior_perda:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def create_trading_heatmap(df):
    """Cria um gráfico de heatmap estilo GitHub para a atividade de trading."""
    try:
        if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
            st.warning("Dados insuficientes para gerar o heatmap.")
            return None

        current_year = df['Data'].dt.year.max()
        df_year = df[df['Data'].dt.year == current_year].copy()

        if df_year.empty:
            st.warning(f"Sem dados para o ano {current_year}.")
            return None

        start_date = pd.Timestamp(f'{current_year}-01-01')
        end_date = pd.Timestamp(f'{current_year}-12-31')
        
        start_weekday = start_date.weekday()
        if start_weekday > 0:
            start_date = start_date - pd.Timedelta(days=start_weekday)
        
        end_weekday = end_date.weekday()
        if end_weekday < 6:
            end_date = end_date + pd.Timedelta(days=6-end_weekday)
        
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        full_df = pd.DataFrame({'Data': all_dates})
        full_df = full_df.merge(df_year[['Data', 'Total']], on='Data', how='left')
        full_df['Total'] = full_df['Total'].fillna(0)
        
        full_df['week'] = ((full_df['Data'] - start_date).dt.days // 7)
        full_df['day_of_week'] = full_df['Data'].dt.weekday
        
        day_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        full_df['day_name'] = full_df['day_of_week'].map(lambda x: day_names[x])
        
        full_df['is_current_year'] = full_df['Data'].dt.year == current_year
        full_df['display_total'] = full_df['Total'].where(full_df['is_current_year'], None)
        
        heatmap = alt.Chart(full_df).mark_rect(
            stroke='white',
            strokeWidth=1,
            cornerRadius=2
        ).encode(
            x=alt.X('week:O', title=None, axis=None),
            y=alt.Y('day_name:N', 
                   sort=day_names,
                   title=None,
                   axis=alt.Axis(labelAngle=0, labelFontSize=10, 
                               ticks=False, domain=False, grid=False)),
            color=alt.condition(
                alt.datum.display_total == None,
                alt.value('#ebedf0'),
                alt.Color('display_total:Q',
                    scale=alt.Scale(
                        range=['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
                        type='linear'
                    ),
                    legend=None)
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('day_name:N', title='Dia'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(
            height=500,
            title=f'Atividade de Trading - {current_year}'
        ).configure_view(
            stroke=None
        ).resolve_scale(
            color='independent'
        )
        
        return heatmap
        
    except Exception as e:
        st.error(f"Erro ao criar heatmap: {e}")
        return None

def create_area_chart(df):
    """Cria um gráfico de área com gradiente mostrando evolução acumulada."""
    try:
        if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
            st.warning("Dados insuficientes para gerar o gráfico de área.")
            return None

        # Preparar dados para o gráfico de área
        area_data = df.copy()
        area_data = area_data.sort_values('Data')
        
        # Calcular valor acumulado
        area_data['Acumulado'] = area_data['Total'].cumsum()
        
        # Determinar cor baseada no resultado final
        final_value = area_data['Acumulado'].iloc[-1]
        line_color = 'darkgreen' if final_value >= 0 else '#b71c1c'
        gradient_color = 'darkgreen' if final_value >= 0 else '#b71c1c'
        
        # Criar gráfico de área com gradiente
        area_chart = alt.Chart(area_data).mark_area(
            line={'color': line_color, 'strokeWidth': 2},
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='white', offset=0),
                    alt.GradientStop(color=gradient_color, offset=1)
                ],
                x1=1,
                x2=1,
                y1=1,
                y2=0
            )
        ).encode(
            x=alt.X('Data:T', 
                   title=None,
                   axis=alt.Axis(labelAngle=-45, labelFontSize=10, 
                               ticks=False, domain=False, grid=False)),
            y=alt.Y('Acumulado:Q', 
                   title=None,
                   axis=alt.Axis(labelFontSize=10, ticks=False, 
                               domain=False, grid=False)),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado do Dia (R$)'),
                alt.Tooltip('Acumulado:Q', format=',.2f', title='Acumulado (R$)')
            ]
        ).properties(
            height=500,
            title='Evolução Acumulada dos Resultados'
        ).configure_view(
            stroke=None
        ).configure_title(
            fontSize=14,
            anchor='start'
        )
        
        return area_chart
        
    except Exception as e:
        st.error(f"Erro ao criar gráfico de área: {e}")
        return None

def create_daily_histogram(df):
    """Cria um histograma diário com cores condicionais."""
    try:
        if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
            st.warning("Dados insuficientes para gerar o histograma.")
            return None

        hist_data = df.copy()
        hist_data = hist_data.sort_values('Data')
        
        histogram = alt.Chart(hist_data).mark_bar(
            cornerRadius=2,
            stroke='white',
            strokeWidth=1
        ).encode(
            x=alt.X('Data:T', 
                   title=None,
                   axis=alt.Axis(labelAngle=-45, labelFontSize=10, 
                               ticks=False, domain=False, grid=False)),
            y=alt.Y('Total:Q', 
                   title=None,
                   axis=alt.Axis(labelFontSize=10, ticks=False, 
                               domain=False, grid=False)),
            color=alt.condition(
                alt.datum.Total >= 0,
                alt.value('#196127'),
                alt.value('#b71c1c')
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(
            height=500,
            title='Resultado Diário'
        ).configure_view(
            stroke=None
        ).configure_title(
            fontSize=14,
            anchor='start'
        )
        
        return histogram
        
    except Exception as e:
        st.error(f"Erro ao criar histograma: {e}")
        return None

def create_radial_chart(df):
    """Cria um gráfico radial com dados mensais."""
    try:
        if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
            st.warning("Dados insuficientes para gerar o gráfico radial.")
            return None

        radial_data = df.copy()
        radial_data['Mes'] = radial_data['Data'].dt.strftime('%b')
        radial_data['MesNum'] = radial_data['Data'].dt.month
        
        monthly_data = radial_data.groupby(['Mes', 'MesNum']).agg({
            'Total': 'sum'
        }).reset_index()
        
        monthly_data = monthly_data.sort_values('MesNum')
        monthly_data['AbsTotal'] = monthly_data['Total'].abs()
        monthly_data = monthly_data[monthly_data['AbsTotal'] > 0]
        
        if monthly_data.empty:
            st.warning("Sem dados válidos para o gráfico radial.")
            return None
        
        base = alt.Chart(monthly_data).encode(
            alt.Theta("AbsTotal:Q").stack(True),
            alt.Radius("AbsTotal:Q").scale(type="sqrt", zero=True, rangeMin=20),
            color=alt.condition(
                alt.datum.Total >= 0,
                alt.value('#196127'),
                alt.value('#b71c1c')
            )
        )

        c1 = base.mark_arc(
            innerRadius=20, 
            stroke="#fff",
            strokeWidth=2
        )

        c2 = base.mark_text(
            radiusOffset=15,
            fontSize=10,
            fontWeight='bold'
        ).encode(
            text=alt.Text('Mes:N'),
            color=alt.value('white')
        )

        radial_chart = (c1 + c2).properties(
            height=500,
            title='Total por Mês'
        ).configure_view(
            stroke=None
        ).configure_title(
            fontSize=12,
            anchor='start'
        )
        
        return radial_chart
        
    except Exception as e:
        st.error(f"Erro ao criar gráfico radial: {e}")
        return None

def main():
    st.title("📈 Trading Activity Dashboard")
    st.markdown("**Sistema integrado:** Upload CSV → Google Sheets → Visualizações")
    
    # CSS para background escuro com efeito de partículas de fogo
    st.markdown("""
    <style>
    /* Background escuro principal */
    .stApp {
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 25%, #2d1b1b 50%, #1a1a1a 75%, #0c0c0c 100%);
        background-attachment: fixed;
        position: relative;
        overflow-x: hidden;
    }
    
    /* Container de partículas de fogo */
    .fire-particles {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
        overflow: hidden;
    }
    
    /* Partículas individuais */
    .particle {
        position: absolute;
        width: 4px;
        height: 4px;
        background: radial-gradient(circle, #ff6b35 0%, #f7931e 30%, #ffaa00 60%, transparent 100%);
        border-radius: 50%;
        opacity: 0;
        animation: rise 8s infinite linear;
        box-shadow: 0 0 10px #ff6b35, 0 0 20px #ff6b35, 0 0 30px #ff6b35;
    }
    
    /* Partículas maiores para variação */
    .particle.large {
        width: 6px;
        height: 6px;
        background: radial-gradient(circle, #ff4500 0%, #ff6b35 40%, #ffaa00 70%, transparent 100%);
        box-shadow: 0 0 15px #ff4500, 0 0 25px #ff4500, 0 0 35px #ff4500;
        animation-duration: 10s;
    }
    
    /* Partículas pequenas para detalhes */
    .particle.small {
        width: 2px;
        height: 2px;
        background: radial-gradient(circle, #ffaa00 0%, #ffd700 50%, transparent 100%);
        box-shadow: 0 0 5px #ffaa00, 0 0 10px #ffaa00;
        animation-duration: 6s;
    }
    
    /* Animação de subida das partículas */
    @keyframes rise {
        0% {
            bottom: -10px;
            opacity: 0;
            transform: translateX(0px) scale(0.5);
        }
        10% {
            opacity: 1;
            transform: translateX(10px) scale(1);
        }
        50% {
            opacity: 0.8;
            transform: translateX(-20px) scale(1.2);
        }
        80% {
            opacity: 0.4;
            transform: translateX(15px) scale(0.8);
        }
        100% {
            bottom: 100vh;
            opacity: 0;
            transform: translateX(-10px) scale(0.3);
        }
    }
    
    /* Efeito de brilho ambiente */
    .ambient-glow {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(ellipse at center bottom, rgba(255, 107, 53, 0.1) 0%, rgba(247, 147, 30, 0.05) 30%, transparent 70%);
        pointer-events: none;
        z-index: -1;
        animation: pulse 4s ease-in-out infinite alternate;
    }
    
    @keyframes pulse {
        0% { opacity: 0.3; }
        100% { opacity: 0.7; }
    }
    
    /* Ajustes para elementos do Streamlit */
    .stApp > header {
        background-color: transparent;
    }
    
    /* Títulos e textos com melhor contraste */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    
    /* Container de estatísticas com transparência */
    .stats-container {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(255, 107, 53, 0.2);
    }
    
    /* Cards de métricas com efeito de fogo */
    .metric-card {
        background: rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 107, 53, 0.3);
        box-shadow: 0 4px 15px rgba(255, 107, 53, 0.2);
    }
    
    /* Sidebar escura */
    .css-1d391kg {
        background-color: rgba(20, 20, 20, 0.95);
        backdrop-filter: blur(10px);
    }
    
    /* Botões com efeito de fogo */
    .stButton > button {
        background: linear-gradient(45deg, #ff4500, #ff6b35);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #ff6b35, #ff8c00);
        box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6);
        transform: translateY(-2px);
    }
    
    /* Upload area com tema escuro */
    .stFileUploader > div {
        background-color: rgba(40, 40, 40, 0.8);
        border: 2px dashed rgba(255, 107, 53, 0.5);
        backdrop-filter: blur(10px);
    }
    
    /* Expander com tema escuro */
    .streamlit-expanderHeader {
        background-color: rgba(40, 40, 40, 0.8);
        color: white;
        border: 1px solid rgba(255, 107, 53, 0.3);
    }
    
    /* Dataframe com tema escuro */
    .stDataFrame {
        background-color: rgba(20, 20, 20, 0.9);
        backdrop-filter: blur(10px);
    }
    
    /* Texto geral */
    .stMarkdown, .stText, p, span {
        color: #e0e0e0 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    
    /* Info boxes */
    .stInfo, .stSuccess, .stWarning, .stError {
        background-color: rgba(40, 40, 40, 0.9);
        backdrop-filter: blur(10px);
        border-left: 4px solid #ff6b35;
    }
    </style>
    
    <!-- HTML para partículas de fogo -->
    <div class="fire-particles" id="fireParticles"></div>
    <div class="ambient-glow"></div>
    
    <script>
    // JavaScript para gerar partículas dinamicamente
    function createFireParticles() {
        const container = document.getElementById('fireParticles');
        if (!container) return;
        
        // Limpar partículas existentes
        container.innerHTML = '';
        
        // Criar 50 partículas
        for (let i = 0; i < 50; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            // Adicionar variações de tamanho
            const rand = Math.random();
            if (rand < 0.3) particle.classList.add('small');
            else if (rand > 0.7) particle.classList.add('large');
            
            // Posição horizontal aleatória
            particle.style.left = Math.random() * 100 + '%';
            
            // Delay aleatório para animação
            particle.style.animationDelay = Math.random() * 8 + 's';
            
            // Velocidade ligeiramente variada
            const duration = 6 + Math.random() * 4;
            particle.style.animationDuration = duration + 's';
            
            container.appendChild(particle);
        }
    }
    
    // Criar partículas quando a página carregar
    document.addEventListener('DOMContentLoaded', createFireParticles);
    
    // Recriar partículas periodicamente para manter o efeito
    setInterval(createFireParticles, 30000);
    </script>
    """, unsafe_allow_html=True)
    
    # Carregar dados do Google Sheets automaticamente
    with st.spinner("Carregando dados do Google Sheets..."):
        sheets_data = load_data_from_sheets()
    
    # Seção de upload para alimentar o Google Sheets
    st.subheader("📤 Alimentar Banco de Dados")
    uploaded_file = st.file_uploader(
        "Faça upload do CSV para atualizar o Google Sheets",
        type=['csv'],
        help="Este arquivo será processado e enviado para o Google Sheets."
    )
    
    # Processar upload se houver
    if uploaded_file is not None:
        try:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            df = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding=encoding, sep=';', 
                                   skiprows=4, on_bad_lines='skip')
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None:
                st.error("Não foi possível ler o arquivo.")
                return
            
            processed_df = process_trading_data(df)
            
            if not processed_df.empty:
                with st.spinner("Enviando dados para Google Sheets..."):
                    if append_data_to_sheets(processed_df):
                        st.success("✅ Dados enviados com sucesso! Recarregando visualizações...")
                        # Limpar cache e recarregar dados
                        st.cache_data.clear()
                        sheets_data = load_data_from_sheets()
                    else:
                        st.error("❌ Erro ao enviar dados para Google Sheets.")
                        
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")
    
    # Exibir visualizações baseadas nos dados do Google Sheets
    if sheets_data is not None and not sheets_data.empty:
        st.markdown("---")
        st.subheader("📊 Dashboard - Dados do Google Sheets")
        
        # Container de estatísticas
        create_statistics_container(sheets_data)
        
        # Gráfico de área (novo)
        st.subheader("📈 Evolução Acumulada")
        area_chart = create_area_chart(sheets_data)
        if area_chart is not None:
            st.altair_chart(area_chart, use_container_width=True)
        
        # Heatmap
        st.subheader("🔥 Heatmap de Atividade")
        chart = create_trading_heatmap(sheets_data)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        
        # Gráficos adicionais
        st.subheader("📊 Análise Detalhada")
        histogram_chart = create_daily_histogram(sheets_data)
        radial_chart = create_radial_chart(sheets_data)

        if histogram_chart is not None and radial_chart is not None:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.altair_chart(histogram_chart, use_container_width=True)
            
            with col2:
                st.altair_chart(radial_chart, use_container_width=True)
        
        # Dados da planilha
        with st.expander("📋 Dados do Google Sheets", expanded=False):
            display_df = sheets_data.copy()
            display_df['Data'] = display_df['Data'].dt.strftime('%d/%m/%Y')
            display_df['Total'] = display_df['Total'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(display_df, use_container_width=True)
    
    else:
        st.info("📋 Nenhum dado encontrado no Google Sheets. Faça upload de um arquivo CSV para começar.")
        
        # Mostrar exemplo do formato esperado
        st.subheader("📋 Formato Esperado do CSV")
        example_data = {
            'Data': ['16/06/2025', '17/06/2025', '18/06/2025'],
            'Ativo': ['WDON25', 'WDON25', 'WDON25'],
            'Lado': ['V', 'C', 'V'],
            'Total': ['80,00', '-55,00', '125,00']
        }
        st.dataframe(pd.DataFrame(example_data))

if __name__ == "__main__":
    main()
