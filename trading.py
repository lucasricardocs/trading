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

# Função para carregar dados do Google Sheets
@st.cache_data(ttl=60)
def load_data_from_sheets():
    """Carrega dados da planilha Google Sheets usando st.connection."""
    try:
        # Criar conexão com Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Ler dados da planilha
        df = conn.read(worksheet="Sheet1", usecols=[0, 1])
        
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

# Função para enviar dados para Google Sheets
def append_data_to_sheets(df):
    """Envia dados processados para a planilha Google Sheets."""
    try:
        # Criar conexão com Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Preparar dados para envio
        df_to_send = df.copy()
        df_to_send['Data'] = df_to_send['Data'].dt.strftime('%d/%m/%Y')
        
        # Atualizar planilha (substitui dados existentes)
        conn.update(worksheet="Sheet1", data=df_to_send)
        
        return True
        
    except Exception as e:
        st.error(f'Erro ao enviar dados para Google Sheets: {str(e)}')
        return False

def process_trading_data(df):
    """Processa os dados de trading do CSV."""
    try:
        df = df.copy()
        df.columns = df.columns.str.strip()
        
        # Procurar pela coluna de Data
        date_col = None
        for col in df.columns:
            if any(word in col for word in ['Abertura', 'Fechamento', 'Data', 'data']):
                date_col = col
                break
        
        if date_col is None:
            st.error("❌ Coluna de data não encontrada")
            return pd.DataFrame()
        
        # Procurar pela coluna Total
        total_col = None
        for col in df.columns:
            if 'Total' in col or 'total' in col:
                total_col = col
                break
        
        if total_col is None:
            st.error("❌ Coluna de total não encontrada")
            return pd.DataFrame()
        
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
        
        # Container com estatísticas
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.15) 0%, rgba(247, 147, 30, 0.15) 100%); 
                    backdrop-filter: blur(20px); padding: 2rem; border-radius: 15px; margin: 1rem 0; 
                    box-shadow: 0 8px 32px rgba(255, 107, 53, 0.3); border: 1px solid rgba(255, 107, 53, 0.2);">
            <h3 style="color: white; text-align: center; margin-bottom: 1.5rem;">🔥 Estatísticas de Trading</h3>
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
        line_color = 'darkgreen' if final_value >= 0 else '#b71c1c'
        gradient_color = 'darkgreen' if final_value >= 0 else '#b71c1c'
        
        return alt.Chart(area_data).mark_area(
            line={'color': line_color, 'strokeWidth': 2},
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='white', offset=0),
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
                alt.value('#196127'),
                alt.value('#b71c1c')
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
                alt.value('#196127'),
                alt.value('#b71c1c')
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
        ).properties(height=500, title=f'Atividade de Trading - {current_year}')
        
    except Exception as e:
        st.error(f"❌ Erro ao criar heatmap: {str(e)}")
        return None

def main():
    st.title("📈 Trading Activity Dashboard")
    st.markdown("**Sistema integrado:** Upload CSV → Google Sheets → Visualizações")
    
    # CSS para tema escuro com efeito de fogo
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 25%, #2d1b1b 50%, #1a1a1a 75%, #0c0c0c 100%);
        background-attachment: fixed;
        position: relative;
        overflow-x: hidden;
    }
    
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
    
    .particle.large {
        width: 6px;
        height: 6px;
        background: radial-gradient(circle, #ff4500 0%, #ff6b35 40%, #ffaa00 70%, transparent 100%);
        box-shadow: 0 0 15px #ff4500, 0 0 25px #ff4500, 0 0 35px #ff4500;
        animation-duration: 10s;
    }
    
    .particle.small {
        width: 2px;
        height: 2px;
        background: radial-gradient(circle, #ffaa00 0%, #ffd700 50%, transparent 100%);
        box-shadow: 0 0 5px #ffaa00, 0 0 10px #ffaa00;
        animation-duration: 6s;
    }
    
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
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    
    .stMarkdown, .stText, p, span {
        color: #e0e0e0 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    
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
    
    .stFileUploader > div {
        background-color: rgba(40, 40, 40, 0.8);
        border: 2px dashed rgba(255, 107, 53, 0.5);
        backdrop-filter: blur(10px);
    }
    
    .stInfo, .stSuccess, .stWarning, .stError {
        background-color: rgba(40, 40, 40, 0.9);
        backdrop-filter: blur(10px);
        border-left: 4px solid #ff6b35;
    }
    </style>
    
    <div class="fire-particles" id="fireParticles"></div>
    <div class="ambient-glow"></div>
    
    <script>
    function createFireParticles() {
        const container = document.getElementById('fireParticles');
        if (!container) return;
        
        container.innerHTML = '';
        
        for (let i = 0; i < 50; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            const rand = Math.random();
            if (rand < 0.3) particle.classList.add('small');
            else if (rand > 0.7) particle.classList.add('large');
            
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 8 + 's';
            
            const duration = 6 + Math.random() * 4;
            particle.style.animationDuration = duration + 's';
            
            container.appendChild(particle);
        }
    }
    
    document.addEventListener('DOMContentLoaded', createFireParticles);
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
