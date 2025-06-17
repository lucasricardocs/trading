# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import time
import threading
import random
from datetime import datetime, timedelta, date
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings

# Suprimir warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações ---
SPREADSHEET_ID = "16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM"
WORKSHEET_NAME = "dados"

# --- Configuração da Página ---
st.set_page_config(
    page_title="Trading Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 Cores para fagulhas
cores = ['#ff4500', '#ff8c00', '#ffd700', '#ffffff']

# 🎧 Som de braseiro
audio_html = """
<audio autoplay loop volume="0.3">
  <source src="https://cdn.pixabay.com/download/audio/2022/03/15/audio_ef3fcd5aab.mp3?filename=fireplace-crackling-11268.mp3" type="audio/mp3">
</audio>
"""

# 🔥 Função para gerar CSS das fagulhas
def gerar_fagulhas(qtd=100):
    fagulhas = ""
    for i in range(qtd):
        left = random.randint(0, 100)
        size = random.uniform(3, 6)
        duration = random.uniform(5, 9)
        delay = random.uniform(0, 8)
        shift = random.randint(-100, 100)
        rotation = random.randint(-180, 180)
        scale = random.uniform(0.6, 1.5)
        blur = max(0.5, (2.0 - scale))
        cor = random.choice(cores)

        fagulhas += f"""
        .spark:nth-child({i+1}) {{
            left: {left}%;
            width: {size}px;
            height: {size}px;
            background: {cor};
            --horizontal-shift: {shift}px;
            --rotation: {rotation}deg;
            --scale: {scale};
            --blur: {blur}px;
            animation-duration: {duration}s, {random.uniform(1,3)}s;
            animation-delay: {delay}s, {random.uniform(0,2)}s;
        }}
        """
    return fagulhas

# CSS Aprimorado com Containers Escuros Sólidos
css = f"""
<style>
/* Background e fagulhas */
body {{
    background-color: #000000;
    overflow-x: hidden;
}}

.spark {{
    position: fixed;
    bottom: 0;
    border-radius: 50%;
    opacity: 0;
    mix-blend-mode: screen;
    animation: rise linear infinite, flicker ease-in-out infinite;
    z-index: -1;
    pointer-events: none;
}}

.spark.long {{
    width: 2px !important;
    height: 10px !important;
    background: linear-gradient(to top, rgba(255,255,255,0.7), rgba(255,255,255,0));
    border-radius: 50%;
}}

@keyframes rise {{
    0% {{
        transform: translateY(0) translateX(0) scale(var(--scale)) rotate(0deg);
        opacity: 1;
        filter: blur(var(--blur));
    }}
    30% {{
        opacity: 1;
    }}
    100% {{
        transform: translateY(-120vh) translateX(var(--horizontal-shift)) scale(calc(var(--scale) * 0.5)) rotate(var(--rotation));
        opacity: 0;
        filter: blur(calc(var(--blur) + 1px));
    }}
}}

@keyframes flicker {{
    0%, 100% {{
        opacity: 0.9;
    }}
    50% {{
        opacity: 0.4;
    }}
}}

/* UI Trading sobre as fagulhas */
.stApp {{
    background: transparent;
    color: #e8eaed;
    font-family: 'Inter', sans-serif;
}}

h1 {{
    color: #4fc3f7;
    font-weight: 600;
    font-size: 2rem;
    margin-bottom: 1rem;
    text-align: center;
    text-shadow: 0 0 10px rgba(79, 195, 247, 0.5);
}}

h2, h3 {{
    color: #9e9e9e;
    font-weight: 400;
    font-size: 1.2rem;
    margin: 1rem 0 0.5rem 0;
}}

/* Sidebar */
.css-1d391kg {{
    background: rgba(17, 17, 17, 0.95) !important;
    border-right: 1px solid #333;
    backdrop-filter: blur(15px);
}}

/* Métricas */
[data-testid="stMetric"] {{
    background: rgba(26, 26, 26, 0.95) !important;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 1rem;
    backdrop-filter: blur(15px);
}}

[data-testid="stMetricLabel"] > div {{
    color: #888;
    font-size: 0.8rem;
}}

[data-testid="stMetricValue"] {{
    color: #e8eaed;
    font-weight: 500;
}}

/* Inputs */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {{
    background: rgba(26, 26, 26, 0.95) !important;
    border: 1px solid #333;
    border-radius: 6px;
    color: #e8eaed;
}}

/* Botões */
.stButton > button {{
    background: rgba(41, 182, 246, 0.95) !important;
    border: none;
    border-radius: 6px;
    color: white;
    font-weight: 500;
    padding: 0.5rem 1rem;
}}

.stButton > button:hover {{
    background: rgba(3, 169, 244, 0.95) !important;
}}

/* Alertas */
[data-testid="stAlert"] {{
    background: rgba(26, 26, 26, 0.95) !important;
    border: 1px solid #333;
    border-radius: 6px;
}}

/* Expander */
.streamlit-expanderHeader {{
    background: rgba(26, 26, 26, 0.95) !important;
    border: 1px solid #333;
    border-radius: 6px;
}}

/* CONTAINERS ESCUROS SÓLIDOS */
.chart-container {{
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
}}

.chart-container h3 {{
    color: #e8eaed;
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.3rem;
    font-weight: 500;
}}

/* Container específico para heatmap */
.heatmap-container {{
    background: #1a1a1a;
    border: 1px solid #28a745;
    border-radius: 12px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 20px rgba(40, 167, 69, 0.2);
}}

.heatmap-container h3 {{
    color: #28a745;
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.3rem;
    font-weight: 500;
}}

/* Container específico para evolução */
.evolution-container {{
    background: #1a1a1a;
    border: 1px solid #8a2be2;
    border-radius: 12px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 20px rgba(138, 43, 226, 0.2);
}}

.evolution-container h3 {{
    color: #8a2be2;
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.3rem;
    font-weight: 500;
}}

/* Container específico para trades */
.trades-container {{
    background: #1a1a1a;
    border: 1px solid #dc3545;
    border-radius: 12px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 20px rgba(220, 53, 69, 0.2);
}}

.trades-container h3 {{
    color: #dc3545;
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.3rem;
    font-weight: 500;
}}

{gerar_fagulhas(100)}
</style>
"""

# 🔥 Inserindo CSS, som e fagulhas
st.markdown(css, unsafe_allow_html=True)
st.markdown(audio_html, unsafe_allow_html=True)
spark_divs = "".join([f"<div class='spark {'long' if random.random() < 0.2 else ''}'></div>" for _ in range(100)])
st.markdown(spark_divs, unsafe_allow_html=True)

# --- Funções ---
@st.cache_resource
def get_google_auth():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais não encontradas")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict:
            st.error("Credenciais vazias")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro: {e}")
        return None

@st.cache_resource
def get_worksheet():
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error("Planilha não encontrada")
            return None
        except Exception as e:
            st.error(f"Erro: {e}")
            return None
    return None

@st.cache_data(ttl=60)
def load_data():
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            if 'ABERTURA' in df.columns:
                df['ABERTURA'] = pd.to_datetime(df['ABERTURA'], errors='coerce')
            
            if 'RESULTADO' in df.columns:
                df['RESULTADO'] = df['RESULTADO'].astype(str).str.replace(',', '.', regex=False)
                df['RESULTADO'] = pd.to_numeric(df['RESULTADO'], errors='coerce').fillna(0)
            
            if 'QUANTIDADE' in df.columns:
                df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0)

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
            st.error(f"Erro: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
    worksheet = get_worksheet()
    if worksheet:
        try:
            resultado_str = str(resultado).replace(',', '.')
            worksheet.append_row([ativo, data_abertura.strftime('%Y-%m-%d'), quantidade, tipo_operacao, resultado_str])
            return True
        except Exception as e:
            st.error(f"Erro: {e}")
            return False
    return False

def calcular_largura_e_espacamento(num_elementos):
    if num_elementos <= 5:
        return {'size': 60, 'padding': 0.3}
    elif num_elementos <= 15:
        return {'size': 45, 'padding': 0.2}
    elif num_elementos <= 30:
        return {'size': 30, 'padding': 0.1}
    elif num_elementos <= 50:
        return {'size': 20, 'padding': 0.05}
    else:
        return {'size': 15, 'padding': 0.02}

def create_heatmap_2d_github(df_heatmap_final):
    """Heatmap com dias da semana completos e cores corretas"""
    if df_heatmap_final.empty:
        return None
    
    current_year = datetime.now().year
    first_day_of_year = pd.Timestamp(f'{current_year}-01-01')
    first_day_weekday = first_day_of_year.weekday()
    days_before = first_day_weekday
    start_date = first_day_of_year - pd.Timedelta(days=days_before)
    end_date = datetime(current_year, 12, 31)
    days_after = 6 - end_date.weekday()
    if days_after < 6:
        end_date = end_date + pd.Timedelta(days=days_after)
    
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    full_df = pd.DataFrame({'Data': all_dates.date})
    full_df['is_current_year'] = pd.to_datetime(full_df['Data']).dt.year == current_year
    full_df = full_df.merge(df_heatmap_final, on='Data', how='left')
    full_df['RESULTADO_LIQUIDO'] = full_df['RESULTADO_LIQUIDO'].fillna(0)
    full_df['display_resultado'] = full_df['RESULTADO_LIQUIDO'].copy()
    mask_not_current_year = ~full_df['is_current_year']
    full_df.loc[mask_not_current_year, 'display_resultado'] = None
    full_df['Data_dt'] = pd.to_datetime(full_df['Data'])
    full_df['day_of_week'] = full_df['Data_dt'].dt.weekday
    
    # DIAS DA SEMANA COMPLETOS
    day_name_map = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    day_display_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    full_df['month'] = full_df['Data_dt'].dt.month
    full_df['month_name'] = full_df['Data_dt'].dt.strftime('%b')
    full_df['week_corrected'] = ((full_df['Data_dt'] - start_date).dt.days // 7)
    
    month_labels = full_df[full_df['is_current_year']].groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    months_chart = alt.Chart(month_labels).mark_text(
        align='center', baseline='bottom', fontSize=10, dy=-3, dx=-20,
        color='#999', fontWeight='normal'
    ).encode(
        x=alt.X('week_corrected:O', axis=None),
        text='month_name:N'
    )

    valores = full_df[full_df['is_current_year']]['RESULTADO_LIQUIDO']
    max_positivo = valores[valores > 0].max() if len(valores[valores > 0]) > 0 else 100
    max_negativo = valores[valores < 0].min() if len(valores[valores < 0]) > 0 else -100
    threshold_2 = max_positivo * 0.5
    threshold_3 = max_positivo * 0.75

    heatmap = alt.Chart(full_df).mark_rect(
        stroke='white',  # STROKE BRANCO
        strokeWidth=2,   # ESPAÇAMENTO ENTRE BLOCOS
        cornerRadius=2
    ).encode(
        x=alt.X('week_corrected:O', title=None, axis=None),
        y=alt.Y('day_display_name:N', sort=day_display_names, title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=9, ticks=False, 
                             domain=False, grid=False, labelColor='#999', labelPadding=8)),
        color=alt.condition(
            alt.datum.display_resultado == None, alt.value('#222'),
            alt.condition(
                alt.datum.display_resultado == 0, alt.value('#cccccc'),  # CINZA CLARO para dias vazios
                alt.condition(
                    alt.datum.display_resultado > 0,
                    alt.value('#28a745'),  # VERDE para positivos
                    alt.value('#dc3545')   # VERMELHO para negativos
                )
            )
        ),
        tooltip=[
            alt.Tooltip('Data:T', title='Data', format='%d/%m'),
            alt.Tooltip('RESULTADO_LIQUIDO:Q', title='R$', format=',.0f')
        ]
    ).properties(height=200)

    return alt.vconcat(months_chart, heatmap, spacing=5).configure_view(
        strokeWidth=0).configure(background='transparent')

def create_evolution_chart_with_gradient(df_area):
    """Gráfico de evolução com gradiente e stroke"""
    area_chart = alt.Chart(df_area).mark_area(
        line={'strokeWidth': 4, 'stroke': '#ffffff'},  # STROKE BRANCO
        opacity=0.8,
        interpolate='monotone'
    ).encode(
        x=alt.X('Data:T', title=''),
        y=alt.Y('Acumulado:Q', title=''),
        color=alt.condition(
            alt.datum.Acumulado >= 0,
            alt.value('#28a745'),  # VERDE se positivo
            alt.value('#dc3545')   # VERMELHO se negativo
        ),
        tooltip=[
            'Data:T', 
            alt.Tooltip('Acumulado:Q', format=',.0f', title='Acumulado'), 
            alt.Tooltip('Resultado_Liquido_Dia:Q', format=',.0f', title='Dia')
        ]
    ).properties(width='container', height=300, background='transparent')
    
    return area_chart

def create_radial_chart(trades_ganhadores, trades_perdedores):
    """Cria gráfico radial (pizza) para trades"""
    if trades_ganhadores == 0 and trades_perdedores == 0:
        return None
        
    pizza_data = pd.DataFrame({
        'Tipo': ['Ganhadores', 'Perdedores'],
        'Quantidade': [trades_ganhadores, trades_perdedores]
    })
    
    # Filtrar apenas valores > 0
    pizza_data = pizza_data[pizza_data['Quantidade'] > 0]
    
    pie_chart = alt.Chart(pizza_data).mark_arc(
        innerRadius=50,
        outerRadius=120,
        stroke='white',
        strokeWidth=3
    ).encode(
        theta=alt.Theta("Quantidade:Q", stack=True),
        color=alt.Color("Tipo:N", 
                       scale=alt.Scale(domain=["Ganhadores", "Perdedores"], 
                                     range=["#28a745", "#dc3545"]),
                       legend=alt.Legend(
                           orient="bottom",
                           titleColor="#e8eaed",
                           labelColor="#e8eaed"
                       )),
        tooltip=["Tipo:N", "Quantidade:Q"]
    ).properties(
        width=250,
        height=250,
        background='transparent'
    )
    
    return pie_chart

# --- Interface ---
st.title("🔥 Trading Analytics")

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ➕ Adicionar")
    
    with st.form("nova_operacao"):
        ativo = st.selectbox("Ativo", ["WDOFUT", "WINFUT"])
        data_abertura = st.date_input("Data", value=date.today())
        quantidade = st.number_input("Contratos", min_value=1, value=1)
        tipo_operacao = st.selectbox("Tipo", ["Compra", "Venda"])
        resultado_input = st.text_input("Resultado", value="0,00")
        
        try:
            resultado = float(resultado_input.replace(',', '.'))
        except ValueError:
            st.error("Valor inválido")
            resultado = 0.0

        submitted = st.form_submit_button("✅ Adicionar")
        
        if submitted:
            if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
                temp_success = st.empty()
                temp_success.success("✅ Trade adicionado!")
                st.cache_data.clear()
                time.sleep(1.5)
                temp_success.empty()
                st.rerun()
            else:
                st.error("❌ Erro ao adicionar")

# --- Dados ---
df = load_data()

# --- Filtros ---
with st.sidebar:
    st.markdown("### 🔎 Período")
    if not df.empty and 'ABERTURA' in df.columns:
        data_min = df['ABERTURA'].min().date()
        data_max = df['ABERTURA'].max().date()
        data_inicial, data_final = st.date_input(
            "Intervalo", value=(data_min, data_max),
            min_value=data_min, max_value=data_max
        )
        df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
    else:
        df_filtrado = df.copy()

    st.markdown("### 📊 Resumo")
    if not df_filtrado.empty:
        resumo_ativo = df_filtrado.groupby('ATIVO').agg({
            'RESULTADO_LIQUIDO': ['count', 'sum', 'mean']
        }).round(0)
        resumo_ativo.columns = ['Trades', 'Total', 'Média']
        resumo_ativo = resumo_ativo.reset_index()
        st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)

# --- Corpo Principal ---
if df.empty:
    st.info("🔥 Adicione operações para começar")
else:
    with st.expander("📋 Dados"):
        st.dataframe(df, use_container_width=True)

    if 'RESULTADO_LIQUIDO' in df_filtrado.columns and 'ABERTURA' in df_filtrado.columns:
        valor_total = df_filtrado['RESULTADO_LIQUIDO'].sum()
        media_resultado = df_filtrado['RESULTADO_LIQUIDO'].mean()
        
        df_por_dia = df_filtrado.groupby(df_filtrado['ABERTURA'].dt.date).agg({
            'RESULTADO_LIQUIDO': 'sum'
        }).reset_index()
        df_por_dia.columns = ['Data', 'Resultado_Liquido_Dia']
        
        total_trades = len(df_filtrado)
        trades_ganhadores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] > 0])
        trades_perdedores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] < 0])
        taxa_acerto = (trades_ganhadores / total_trades * 100) if total_trades > 0 else 0
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Total", f"R$ {valor_total:,.0f}".replace('.', 'X').replace(',', '.').replace('X', ','))
        with col2:
            st.metric("📈 Média", f"R$ {media_resultado:,.0f}".replace('.', 'X').replace(',', '.').replace('X', ','))
        with col3:
            st.metric("🎯 Trades", f"{total_trades}")
        with col4:
            st.metric("✅ Acerto", f"{taxa_acerto:.0f}%")

        # Heatmap Anual
        st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
        st.markdown("### 🔥 Atividade Anual")
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
            
            heatmap_2d_github = create_heatmap_2d_github(df_heatmap_final)
            if heatmap_2d_github:
                st.altair_chart(heatmap_2d_github, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Evolução Acumulada
        st.markdown('<div class="evolution-container">', unsafe_allow_html=True)
        st.markdown("### 📊 Evolução Acumulada")
        if not df_por_dia.empty:
            df_area = df_por_dia.copy().sort_values('Data')
            df_area['Acumulado'] = df_area['Resultado_Liquido_Dia'].cumsum()
            evolution_chart = create_evolution_chart_with_gradient(df_area)
            st.altair_chart(evolution_chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Resultados por Trade + Gráfico Radial
        st.markdown('<div class="trades-container">', unsafe_allow_html=True)
        st.markdown("### 🎯 Resultados por Trade")
        
        # Layout: 2/3 para trades, 1/3 para radial
        col_trades, col_radial = st.columns([2, 1])
        
        with col_trades:
            if not df_filtrado.empty:
                df_trades = df_filtrado.copy()
                df_trades = df_trades.sort_values('ABERTURA')
                df_trades['Index'] = range(1, len(df_trades) + 1)
                num_trades = len(df_trades)
                config = calcular_largura_e_espacamento(num_trades)
                
                bars = alt.Chart(df_trades).mark_bar(size=config['size'], cornerRadius=1).encode(
                    x=alt.X('Index:O', title='', axis=alt.Axis(grid=False, domain=False, ticks=False),
                           scale=alt.Scale(paddingInner=config['padding'], paddingOuter=0.1)),
                    y=alt.Y('RESULTADO_LIQUIDO:Q', title='', axis=alt.Axis(grid=True, gridOpacity=0.1)),
                    color=alt.condition(alt.datum.RESULTADO_LIQUIDO > 0, alt.value('#28a745'), alt.value('#dc3545')),
                    tooltip=[
                        alt.Tooltip('Index:O', title='#'),
                        alt.Tooltip('ABERTURA:T', title='Data', format='%d/%m'),
                        alt.Tooltip('ATIVO:N', title='Ativo'),
                        alt.Tooltip('RESULTADO_LIQUIDO:Q', format=',.0f', title='R$')
                    ]
                )
                
                linha_zero = alt.Chart(pd.DataFrame({'zero': [0]})).mark_rule(
                    color='#666', strokeWidth=1, opacity=0.5
                ).encode(y=alt.Y('zero:Q'))
                
                chart_final = (bars + linha_zero).properties(
                    width='container', height=300, background='transparent'
                )
                st.altair_chart(chart_final, use_container_width=True)
        
        with col_radial:
            st.markdown("#### Distribuição")
            radial_chart = create_radial_chart(trades_ganhadores, trades_perdedores)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Rodapé
st.markdown("""
<div style="text-align:center;color:#666;font-size:0.8rem;margin-top:2rem;padding:1rem;border-top:1px solid #333;background:rgba(0,0,0,0.8);">
    🔥 Trading Analytics • 2025 • Fagulhas 3D + Som ambiente
</div>
""", unsafe_allow_html=True)
