import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import numpy as np
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(
    page_title="Trading Activity Dashboard",
    page_icon="📈",
    layout="wide"
)

# Função para carregar dados da aba "dados" do Google Sheets
@st.cache_data(ttl=60)
def load_data_from_sheets():
    """Carrega dados da aba 'dados' da planilha Google Sheets."""
    try:
        # Criar conexão com Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Ler dados da aba "dados"
        df = conn.read(worksheet="dados", usecols=[0, 1], ttl=60)
        
        if df.empty:
            return None
        
        # Converter tipos de dados
        df.columns = ['Data', 'Total']
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
        
        # Remover linhas com dados inválidos
        df = df.dropna(subset=['Data', 'Total'])
        
        return df
        
    except Exception as e:
        st.error(f'Erro ao carregar dados do Google Sheets: {str(e)}')
        return None

# Função para adicionar dados à aba "dados" (alimentação diária)
def append_data_to_sheets_robust(df):
    """Versão robusta que adiciona dados diretamente na primeira linha vazia."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        # Carrega as credenciais
        credentials = Credentials.from_service_account_info(
            st.secrets["connections"]["gsheets"],
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Constrói o serviço
        service = build('sheets', 'v4', credentials=credentials)
        
        # ID da planilha
        spreadsheet_id = "16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM"
        
        # Preparar dados para envio
        df_to_append = df.copy()
        df_to_append['Data'] = df_to_append['Data'].dt.strftime('%d/%m/%Y')
        
        # Converter para lista de listas
        values_to_append = []
        for _, row in df_to_append.iterrows():
            values_to_append.append([row['Data'], float(row['Total'])])
        
        # Verificar dados existentes para evitar duplicatas
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='dados!A:B'
            ).execute()
            
            existing_values = result.get('values', [])
            if len(existing_values) > 1:  # Se há mais que só o cabeçalho
                existing_dates = set()
                for row in existing_values[1:]:  # Pular cabeçalho
                    if len(row) >= 1:
                        try:
                            date_obj = pd.to_datetime(row[0], format='%d/%m/%Y')
                            existing_dates.add(date_obj.date())
                        except:
                            continue
                
                # Filtrar apenas datas que não existem
                filtered_values = []
                for value_row in values_to_append:
                    try:
                        date_obj = pd.to_datetime(value_row[0], format='%d/%m/%Y')
                        if date_obj.date() not in existing_dates:
                            filtered_values.append(value_row)
                    except:
                        continue
                
                values_to_append = filtered_values
                
                if not values_to_append:
                    st.warning("⚠️ Todos os dados já existem na planilha")
                    return True
                    
        except Exception as e:
            st.warning(f"⚠️ Não foi possível verificar dados existentes: {e}")
        
        if not values_to_append:
            st.warning("⚠️ Nenhum dado novo para adicionar")
            return True
        
        # Adicionar dados na primeira linha vazia
        body = {
            'values': values_to_append
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='dados!A:B',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        st.success(f"✅ {len(values_to_append)} novos registros adicionados à aba 'dados'")
        return True
        
    except Exception as e:
        st.error(f'❌ Erro ao adicionar dados ao Google Sheets: {str(e)}')
        return False

def process_trading_data(df):
    """Processa os dados de trading do CSV - cabeçalho na linha 5, dados a partir da linha 6."""
    try:
        df = df.copy()
        
        # Verificar se o DataFrame não está vazio
        if df.empty:
            st.error("❌ Arquivo CSV vazio")
            return pd.DataFrame()
        
        # Limpar nomes das colunas (remover espaços extras)
        df.columns = df.columns.str.strip()
        
        # Debug: mostrar as colunas encontradas
        st.write("🔍 Colunas encontradas no CSV:", list(df.columns))
        
        # Procurar pela coluna de Data
        date_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['abertura', 'fechamento', 'data', 'date']):
                date_col = col
                break
        
        if date_col is None:
            st.error(f"❌ Coluna de data não encontrada. Colunas disponíveis: {list(df.columns)}")
            return pd.DataFrame()
        
        # Procurar pela coluna Total
        total_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['total', 'resultado', 'valor']):
                total_col = col
                break
        
        if total_col is None:
            st.error(f"❌ Coluna de total não encontrada. Colunas disponíveis: {list(df.columns)}")
            return pd.DataFrame()
        
        st.success(f"✅ Usando coluna de data: '{date_col}' e coluna de total: '{total_col}'")
        
        # Filtrar apenas linhas que têm data válida (não vazias e não NaN)
        df = df[df[date_col].notna() & (df[date_col] != '') & (df[date_col] != 'nan')]
        
        if df.empty:
            st.error("❌ Nenhuma linha com data válida encontrada")
            return pd.DataFrame()
        
        # Converter Data para datetime
        def extract_date(date_str):
            try:
                if pd.isna(date_str) or date_str == '' or str(date_str).lower() == 'nan':
                    return pd.NaT
                
                if isinstance(date_str, str):
                    # Pegar apenas a parte da data (antes do espaço se houver)
                    date_part = date_str.split(' ')[0]
                    # Tentar diferentes formatos de data
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                        try:
                            return pd.to_datetime(date_part, format=fmt)
                        except:
                            continue
                    return pd.to_datetime(date_part, errors='coerce')
                else:
                    return pd.to_datetime(date_str, errors='coerce')
            except:
                return pd.NaT
        
        df['Data'] = df[date_col].apply(extract_date)
        
        # Converter Total para numérico
        def convert_total(value):
            try:
                if pd.isna(value) or value == '' or str(value).lower() == 'nan':
                    return 0
                
                # Converter para string e limpar
                value_str = str(value).strip()
                
                # Remover símbolos de moeda e espaços
                value_str = value_str.replace('R$', '').replace('$', '').strip()
                
                # Substituir vírgula por ponto (formato brasileiro)
                value_str = value_str.replace(',', '.')
                
                # Remover caracteres não numéricos exceto - e .
                value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
                
                # Converter para float
                return float(value_str) if value_str else 0
                
            except:
                return 0
        
        df['Total'] = df[total_col].apply(convert_total)
        
        # Remover linhas com datas inválidas
        df = df.dropna(subset=['Data'])
        
        if df.empty:
            st.error("❌ Nenhuma linha com data válida após conversão")
            return pd.DataFrame()
        
        # Mostrar preview dos dados processados
        st.write("📊 Preview dos dados processados:")
        preview_df = df[['Data', 'Total']].head()
        preview_df['Data'] = preview_df['Data'].dt.strftime('%d/%m/%Y')
        st.dataframe(preview_df)
        
        # Agrupar por data para somar os resultados do dia
        daily_data = df.groupby('Data').agg({
            'Total': 'sum'
        }).reset_index()
        
        st.success(f"✅ Dados processados: {len(daily_data)} dias únicos encontrados")
        
        return daily_data
        
    except Exception as e:
        st.error(f"❌ Erro ao processar dados: {str(e)}")
        return pd.DataFrame()

def create_statistics_container(df):
    """Cria container com estatísticas detalhadas."""
    if df.empty:
        st.warning("⚠️ Sem dados para exibir estatísticas")
        return
    
    try:
        # Calcular estatísticas
        valor_acumulado = df['Total'].sum()
        total_ganho = df[df['Total'] > 0]['Total'].sum()
        total_perda = df[df['Total'] < 0]['Total'].sum()
        dias_positivos = len(df[df['Total'] > 0])
        dias_negativos = len(df[df['Total'] < 0])
        total_dias = len(df)
        
        # Calcular percentuais
        perc_dias_positivos = (dias_positivos / total_dias * 100) if total_dias > 0 else 0
        perc_dias_negativos = (dias_negativos / total_dias * 100) if total_dias > 0 else 0
        
        # Maior ganho e maior perda
        maior_ganho = df['Total'].max() if not df.empty else 0
        maior_perda = df['Total'].min() if not df.empty else 0
        
        # Média diária
        media_diaria = df[df['Total'] != 0]['Total'].mean() if len(df[df['Total'] != 0]) > 0 else 0
        
        # Container com estatísticas estilizado
        st.markdown("""
        <div style="background: rgba(44, 62, 80, 0.3); 
                    backdrop-filter: blur(20px); padding: 2rem; border-radius: 15px; margin: 1rem 0; 
                    box-shadow: 0 8px 32px rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);">
            <h3 style="color: white; text-align: center; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.8);">📊 Estatísticas de Trading</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Valor Acumulado", f"R$ {valor_acumulado:,.2f}")
            st.metric("📈 Total Ganhos", f"R$ {total_ganho:,.2f}")
        
        with col2:
            st.metric("📉 Total Perdas", f"R$ {total_perda:,.2f}")
            st.metric("📊 Média Diária", f"R$ {media_diaria:,.2f}")
        
        with col3:
            st.metric("✅ Dias Positivos", f"{dias_positivos} ({perc_dias_positivos:.1f}%)")
            st.metric("🚀 Maior Ganho", f"R$ {maior_ganho:,.2f}")
        
        with col4:
            st.metric("❌ Dias Negativos", f"{dias_negativos} ({perc_dias_negativos:.1f}%)")
            st.metric("💥 Maior Perda", f"R$ {maior_perda:,.2f}")
            
    except Exception as e:
        st.error(f"❌ Erro ao criar estatísticas: {str(e)}")

def create_area_chart(df):
    """Cria gráfico de área com evolução acumulada."""
    if df.empty:
        return None
    
    try:
        area_data = df.copy().sort_values('Data')
        area_data['Acumulado'] = area_data['Total'].cumsum()
        
        final_value = area_data['Acumulado'].iloc[-1]
        line_color = '#3498db' if final_value >= 0 else '#e74c3c'
        gradient_color = '#3498db' if final_value >= 0 else '#e74c3c'
        
        return alt.Chart(area_data).mark_area(
            line={'color': line_color, 'strokeWidth': 2},
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='rgba(255,255,255,0.1)', offset=0),
                    alt.GradientStop(color=gradient_color, offset=1)
                ],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('Data:T', title=None),
            y=alt.Y('Acumulado:Q', title=None),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado do Dia (R$)'),
                alt.Tooltip('Acumulado:Q', format=',.2f', title='Acumulado (R$)')
            ]
        ).properties(height=500, title='Evolução Acumulada dos Resultados')
        
    except Exception as e:
        st.error(f"❌ Erro ao criar gráfico de área: {str(e)}")
        return None

def create_daily_histogram(df):
    """Cria histograma diário."""
    if df.empty:
        return None
    
    try:
        hist_data = df.copy().sort_values('Data')
        
        return alt.Chart(hist_data).mark_bar(
            cornerRadius=2, stroke='white', strokeWidth=1
        ).encode(
            x=alt.X('Data:T', title=None),
            y=alt.Y('Total:Q', title=None),
            color=alt.condition(
                alt.datum.Total >= 0,
                alt.value('#3498db'),
                alt.value('#e74c3c')
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(height=500, title='Resultado Diário')
        
    except Exception as e:
        st.error(f"❌ Erro ao criar histograma: {str(e)}")
        return None

def create_radial_chart(df):
    """Cria gráfico radial com dados mensais."""
    if df.empty:
        return None
    
    try:
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
            return None
        
        base = alt.Chart(monthly_data).encode(
            alt.Theta("AbsTotal:Q").stack(True),
            alt.Radius("AbsTotal:Q").scale(type="sqrt", zero=True, rangeMin=20),
            color=alt.condition(
                alt.datum.Total >= 0,
                alt.value('#3498db'),
                alt.value('#e74c3c')
            )
        )

        c1 = base.mark_arc(innerRadius=20, stroke="#fff", strokeWidth=2)
        c2 = base.mark_text(radiusOffset=15, fontSize=10, fontWeight='bold').encode(
            text=alt.Text('Mes:N'), color=alt.value('white')
        )

        return (c1 + c2).properties(height=500, title='Total por Mês')
        
    except Exception as e:
        st.error(f"❌ Erro ao criar gráfico radial: {str(e)}")
        return None

def create_trading_heatmap(df):
    """Cria heatmap estilo GitHub."""
    if df.empty:
        return None
    
    try:
        current_year = df['Data'].dt.year.max()
        df_year = df[df['Data'].dt.year == current_year].copy()

        if df_year.empty:
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
        
        return alt.Chart(full_df).mark_rect(
            stroke='white', strokeWidth=1, cornerRadius=2
        ).encode(
            x=alt.X('week:O', title=None, axis=None),
            y=alt.Y('day_name:N', sort=day_names, title=None,
                   axis=alt.Axis(labelAngle=0, labelFontSize=10, 
                               ticks=False, domain=False, grid=False)),
            color=alt.condition(
                alt.datum.display_total == None,
                alt.value('rgba(255,255,255,0.1)'),
                alt.Color('display_total:Q',
                    scale=alt.Scale(
                        range=['rgba(255,255,255,0.1)', '#74b9ff', '#0984e3', '#2d3436', '#636e72'],
                        type='linear'
                    ),
                    legend=None)
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('day_name:N', title='Dia'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(height=500, title=f'Atividade de Trading - {current_year}')
        
    except Exception as e:
        st.error(f"❌ Erro ao criar heatmap: {str(e)}")
        return None

def main():
    st.title("📈 Trading Activity Dashboard")
    st.markdown("**Sistema integrado:** Upload CSV → Google Sheets (aba dados) → Visualizações")
    
    # CSS para background com partículas animadas (baseado no HTML fornecido)
    st.markdown("""
    <style>
    /* Background principal com gradiente radial exato do HTML fornecido */
    .stApp {
        background: radial-gradient(circle at 30% 30%, #2c3e50, #000);
        background-attachment: fixed;
        position: relative;
        overflow-x: hidden;
        min-height: 100vh;
        color: white;
        font-family: Arial, sans-serif;
    }
    
    /* Container de partículas exato do HTML fornecido */
    .particles {
        position: absolute;
        width: 100%;
        height: 100%;
        overflow: hidden;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: -1;
    }
    
    /* Partículas individuais exatas do HTML fornecido */
    .particle {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.8);
        animation: float 20s infinite linear;
    }
    
    /* Animação de flutuação exata do HTML fornecido */
    @keyframes float {
        0% {
            transform: translateY(100vh) scale(0.5);
            opacity: 0;
        }
        50% {
            opacity: 1;
        }
        100% {
            transform: translateY(-10vh) scale(1.2);
            opacity: 0;
        }
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
    
    /* Texto geral */
    .stMarkdown, .stText, p, span {
        color: #e0e0e0 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    
    /* Botões com tema azul */
    .stButton > button {
        background: linear-gradient(45deg, #3498db, #74b9ff);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #74b9ff, #0984e3);
        box-shadow: 0 6px 20px rgba(52, 152, 219, 0.6);
        transform: translateY(-2px);
    }
    
    /* Upload area com tema escuro */
    .stFileUploader > div {
        background-color: rgba(44, 62, 80, 0.3);
        border: 2px dashed rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
    }
    
    /* Expander com tema escuro */
    .streamlit-expanderHeader {
        background-color: rgba(44, 62, 80, 0.3);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    /* Dataframe com tema escuro */
    .stDataFrame {
        background-color: rgba(44, 62, 80, 0.2);
        backdrop-filter: blur(10px);
    }
    
    /* Info boxes */
    .stInfo, .stSuccess, .stWarning, .stError {
        background-color: rgba(44, 62, 80, 0.3);
        backdrop-filter: blur(10px);
        border-left: 4px solid #3498db;
    }
    
    /* Métricas com fundo transparente */
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    </style>
    
    <!-- HTML para partículas animadas exato do HTML fornecido -->
    <div class="particles">
        <div class="particle" style="width: 10px; height: 10px; left: 20%; animation-delay: 0s;"></div>
        <div class="particle" style="width: 8px; height: 8px; left: 40%; animation-delay: 5s;"></div>
        <div class="particle" style="width: 12px; height: 12px; left: 60%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 80%; animation-delay: 15s;"></div>
        <div class="particle" style="width: 14px; height: 14px; left: 30%; animation-delay: 3s;"></div>
        <div class="particle" style="width: 9px; height: 9px; left: 70%; animation-delay: 8s;"></div>
        <div class="particle" style="width: 11px; height: 11px; left: 50%; animation-delay: 12s;"></div>
        <div class="particle" style="width: 7px; height: 7px; left: 90%; animation-delay: 18s;"></div>
        <div class="particle" style="width: 13px; height: 13px; left: 10%; animation-delay: 6s;"></div>
        <div class="particle" style="width: 5px; height: 5px; left: 25%; animation-delay: 14s;"></div>
        <div class="particle" style="width: 15px; height: 15px; left: 75%; animation-delay: 2s;"></div>
        <div class="particle" style="width: 8px; height: 8px; left: 45%; animation-delay: 16s;"></div>
        <div class="particle" style="width: 10px; height: 10px; left: 65%; animation-delay: 4s;"></div>
        <div class="particle" style="width: 12px; height: 12px; left: 85%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 15%; animation-delay: 7s;"></div>
        <div class="particle" style="width: 14px; height: 14px; left: 35%; animation-delay: 13s;"></div>
        <div class="particle" style="width: 9px; height: 9px; left: 55%; animation-delay: 9s;"></div>
        <div class="particle" style="width: 11px; height: 11px; left: 95%; animation-delay: 11s;"></div>
        <div class="particle" style="width: 7px; height: 7px; left: 5%; animation-delay: 17s;"></div>
        <div class="particle" style="width: 13px; height: 13px; left: 82%; animation-delay: 1s;"></div>
    </div>
    
    <script>
    // JavaScript para criar mais partículas dinamicamente
    function createMoreParticles() {
        const container = document.querySelector('.particles');
        if (!container) return;
        
        // Criar 30 partículas adicionais
        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            // Tamanho aleatório entre 4px e 16px
            const size = Math.random() * 12 + 4;
            particle.style.width = size + 'px';
            particle.style.height = size + 'px';
            
            // Posição horizontal aleatória
            particle.style.left = Math.random() * 100 + '%';
            
            // Delay aleatório para animação
            particle.style.animationDelay = Math.random() * 20 + 's';
            
            // Duração ligeiramente variada
            const duration = 18 + Math.random() * 6;
            particle.style.animationDuration = duration + 's';
            
            container.appendChild(particle);
        }
    }
    
    // Criar partículas quando a página carregar
    document.addEventListener('DOMContentLoaded', createMoreParticles);
    </script>
    """, unsafe_allow_html=True)
    
    # Carregar dados da aba "dados" do Google Sheets automaticamente
    with st.spinner("Carregando dados da aba 'dados' do Google Sheets..."):
        sheets_data = load_data_from_sheets()
    
    # Seção de upload para alimentar a aba "dados"
    st.subheader("📤 Alimentar Base de Dados")
    st.info("💡 O arquivo CSV será processado e enviado para a aba 'dados' da planilha Google Sheets")
    
    uploaded_file = st.file_uploader(
        "Faça upload do CSV para atualizar a aba 'dados' do Google Sheets",
        type=['csv'],
        help="Este arquivo será processado e enviado para a aba 'dados' da planilha."
    )
    
    # Processar upload se houver
    if uploaded_file is not None:
        try:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            df = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)
                    # Ler CSV pulando as primeiras 4 linhas, usando a linha 5 como cabeçalho
                    df = pd.read_csv(
                        uploaded_file, 
                        encoding=encoding, 
                        sep=';',  # Separador ponto e vírgula
                        skiprows=4,  # Pular as primeiras 4 linhas
                        on_bad_lines='skip'  # Ignorar linhas problemáticas
                    )
                    st.success(f"✅ Arquivo carregado com encoding: {encoding}")
                    break
                except (UnicodeDecodeError, pd.errors.ParserError) as e:
                    st.warning(f"⚠️ Tentativa com encoding {encoding} falhou: {str(e)}")
                    continue
            
            if df is None:
                st.error("❌ Não foi possível ler o arquivo com nenhum encoding testado.")
                return
            
            # Mostrar informações sobre o arquivo carregado
            st.write(f"📁 Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")
            
            # Mostrar preview do arquivo bruto
            with st.expander("👀 Preview do arquivo CSV bruto", expanded=False):
                st.dataframe(df.head(10))
            
            processed_df = process_trading_data(df)
            
            if not processed_df.empty:
                with st.spinner("Adicionando novos dados à aba 'dados' do Google Sheets..."):
                    success = append_data_to_sheets_robust(processed_df)
                    
                    if success:
                        st.success("✅ Dados adicionados com sucesso! Recarregando visualizações...")
                        st.cache_data.clear()
                        sheets_data = load_data_from_sheets()
                    else:
                        st.error("❌ Erro ao adicionar dados ao Google Sheets.")
            else:
                st.error("❌ Nenhum dado válido foi processado do arquivo CSV.")
                        
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")
    
    # Exibir visualizações baseadas nos dados da aba "dados"
    if sheets_data is not None and not sheets_data.empty:
        st.markdown("---")
        st.subheader("📊 Dashboard - Dados da Aba 'dados'")
        st.info(f"📋 Exibindo dados da planilha Google Sheets (aba 'dados') - {len(sheets_data)} registros encontrados")
        
        # Container de estatísticas
        create_statistics_container(sheets_data)
        
        # Gráfico de área
        st.subheader("📈 Evolução Acumulada")
        area_chart = create_area_chart(sheets_data)
        if area_chart is not None:
            st.altair_chart(area_chart, use_container_width=True)
        
        # Heatmap
        st.subheader("🔥 Heatmap de Atividade")
        heatmap_chart = create_trading_heatmap(sheets_data)
        if heatmap_chart is not None:
            st.altair_chart(heatmap_chart, use_container_width=True)
        
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
        
        # Dados da aba "dados"
        with st.expander("📋 Dados da Aba 'dados' - Google Sheets", expanded=False):
            display_df = sheets_data.copy()
            display_df['Data'] = display_df['Data'].dt.strftime('%d/%m/%Y')
            display_df['Total'] = display_df['Total'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(display_df, use_container_width=True)
            st.caption(f"Fonte: Google Sheets - Aba 'dados' | Total de registros: {len(display_df)}")
    
    else:
        st.info("📋 Nenhum dado encontrado na aba 'dados' do Google Sheets. Faça upload de um arquivo CSV para começar.")
        
        # Mostrar exemplo do formato esperado
        st.subheader("📋 Formato Esperado do CSV")
        example_data = {
            'Data': ['16/06/2025', '17/06/2025', '18/06/2025'],
            'Ativo': ['WDON25', 'WDON25', 'WDON25'],
            'Lado': ['V', 'C', 'V'],
            'Total': ['80,00', '-55,00', '125,00']
        }
        st.dataframe(pd.DataFrame(example_data))
        st.caption("💡 Os dados processados serão enviados para a aba 'dados' da planilha Google Sheets")

if __name__ == "__main__":
    main()
