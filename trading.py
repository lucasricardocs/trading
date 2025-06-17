# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import time
import random
from datetime import datetime, timedelta, date
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import locale

# Tentativa de configurar locale - fallback seguro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

# Suprimir warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações ---
SPREADSHEET_ID = "16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM"
WORKSHEET_NAME = "dados"

# --- Configuração da Página ---
st.set_page_config(
    page_title="Trading Analytics Pro",
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

# CSS Completo com Fagulhas
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
    font-size: 2.5rem;
    margin-bottom: 1rem;
    text-align: center;
    text-shadow: 0 0 12px rgba(79, 195, 247, 0.6);
    padding-bottom: 10px;
    border-bottom: 1px solid #333;
}}

h2, h3 {{
    color: #9e9e9e;
    font-weight: 400;
    font-size: 1.4rem;
    margin: 1.5rem 0 0.8rem 0;
    border-left: 3px solid #4fc3f7;
    padding-left: 10px;
}}

/* Sidebar */
.css-1d391kg {{
    background: rgba(17, 17, 17, 0.95) !important;
    border-right: 1px solid #333;
    backdrop-filter: blur(15px);
}}

/* Containers */
.stMetric, .stDataFrame, .stAlert, .streamlit-expanderContent {{
    background: rgba(17, 17, 17, 0.85) !important;
    border: 1px solid #333 !important;
    border-radius: 10px !important;
    padding: 15px !important;
    margin: 10px 0 !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
}}

/* Métricas */
[data-testid="stMetricLabel"] {{
    font-size: 0.95rem !important;
    color: #9e9e9e !important;
}}

[data-testid="stMetricValue"] {{
    font-size: 1.8rem !important;
    color: #e8eaed !important;
    font-weight: 500 !important;
}}

.stMetric .positive {{
    color: #28a745 !important;
    text-shadow: 0 0 8px rgba(40, 167, 69, 0.4);
}}

.stMetric .negative {{
    color: #dc3545 !important;
    text-shadow: 0 0 8px rgba(220, 53, 69, 0.4);
}}

/* Inputs */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {{
    background: rgba(26, 26, 26, 0.95) !important;
    border: 1px solid #333;
    border-radius: 8px;
    color: #e8eaed;
    padding: 8px 12px;
}}

/* Botões */
.stButton > button {{
    background: linear-gradient(45deg, #29b6f6, #0288d1) !important;
    border: none;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    padding: 0.6rem 1.2rem;
    transition: all 0.3s ease;
}}

.stButton > button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(41, 182, 246, 0.4);
}}

/* Tabs */
[role="tablist"] button {{
    background: rgba(26, 26, 26, 0.85) !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    margin: 0 5px !important;
    padding: 8px 20px !important;
    transition: all 0.3s ease;
}}

[role="tablist"] button:hover {{
    background: rgba(41, 182, 246, 0.2) !important;
}}

[aria-selected="true"] {{
    background: linear-gradient(45deg, #29b6f6, #0288d1) !important;
    border-color: #4fc3f7 !important;
    box-shadow: 0 2px 8px rgba(79, 195, 247, 0.3);
}}

/* Gráficos */
svg {{
    background: transparent !important;
}}

/* Tooltips */
[data-testid="stTooltip"] {{
    background: rgba(17, 17, 17, 0.95) !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4) !important;
}}

{gerar_fagulhas(150)}
</style>
"""

# 🔥 Inserindo CSS, som e fagulhas
st.markdown(css, unsafe_allow_html=True)
st.markdown(audio_html, unsafe_allow_html=True)
spark_divs = "".join([f"<div class='spark {'long' if random.random() < 0.2 else ''}'></div>" for _ in range(150)])
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

def formatar_moeda(valor):
    """Formata valor monetário com símbolo R$ e separadores brasileiros"""
    try:
        # Formatação manual: R$ 1.234,56
        valor_str = f"{valor:,.2f}"
        
        # Separa parte inteira e decimal
        if '.' in valor_str:
            parte_inteira, parte_decimal = valor_str.split('.')
        else:
            parte_inteira = valor_str
            parte_decimal = "00"
        
        # Formata parte inteira com pontos
        parte_inteira_formatada = ""
        for i, char in enumerate(reversed(parte_inteira)):
            if i > 0 and i % 3 == 0:
                parte_inteira_formatada = '.' + parte_inteira_formatada
            parte_inteira_formatada = char + parte_inteira_formatada
        
        # Retorna string formatada
        return f"R$ {parte_inteira_formatada},{parte_decimal}"
    except:
        # Fallback para valores simples
        return f"R$ {valor:.2f}"

def create_heatmap_2d_github(df_heatmap_final):
    """Heatmap minimalista com dias fora do ano transparentes"""
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
    
    # Dias da semana completos
    day_name_map = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    day_display_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    full_df['month'] = full_df['Data_dt'].dt.month
    full_df['month_name'] = full_df['Data_dt'].dt.strftime('%b')
    full_df['week_corrected'] = ((full_df['Data_dt'] - start_date).dt.days // 7)
    
    def get_stroke_width(row):
        if pd.isna(row['display_resultado']) or row['display_resultado'] is None:
            return 0
        else:
            return 2
    
    def get_color_category(row):
        if pd.isna(row['display_resultado']) or row['display_resultado'] is None:
            return 'fora_ano'
        elif row['display_resultado'] == 0:
            return 'vazio'
        elif row['display_resultado'] > 0:
            return 'positivo'
        else:
            return 'negativo'
    
    full_df['color_category'] = full_df.apply(get_color_category, axis=1)
    full_df['stroke_width'] = full_df.apply(get_stroke_width, axis=1)
    
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

    heatmap = alt.Chart(full_df).mark_rect(
        stroke='white',
        cornerRadius=2
    ).encode(
        x=alt.X('week_corrected:O', title=None, axis=None),
        y=alt.Y('day_display_name:N', sort=day_display_names, title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=9, ticks=False, 
                             domain=False, grid=False, labelColor='#999', labelPadding=8)),
        strokeWidth=alt.StrokeWidth('stroke_width:Q', legend=None),
        color=alt.Color('color_category:N',
                       scale=alt.Scale(
                           domain=['fora_ano', 'vazio', 'positivo', 'negativo'],
                           range=['transparent', '#cccccc', '#28a745', '#dc3545']
                       ),
                       legend=None),
        tooltip=[
            alt.Tooltip('Data:T', title='Data', format='%d/%m'),
            alt.Tooltip('RESULTADO_LIQUIDO:Q', title='R$', format=',.0f')
        ]
    ).properties(height=200)

    return alt.vconcat(months_chart, heatmap, spacing=5).configure_view(
        strokeWidth=0).configure(background='transparent')

def create_evolution_chart_with_gradient(df_area):
    """Gráfico de evolução com stroke 2"""
    area_chart = alt.Chart(df_area).mark_area(
        line={'strokeWidth': 2, 'stroke': '#ffffff'},
        opacity=0.8,
        interpolate='monotone'
    ).encode(
        x=alt.X('Data:T', title=''),
        y=alt.Y('Acumulado:Q', title=''),
        color=alt.condition(
            alt.datum.Acumulado >= 0,
            alt.value('#28a745'),
            alt.value('#dc3545')
        ),
        tooltip=[
            'Data:T', 
            alt.Tooltip('Acumulado:Q', format=',.0f', title='Acumulado'), 
            alt.Tooltip('Resultado_Liquido_Dia:Q', format=',.0f', title='Dia')
        ]
    ).properties(width='container', height=300, background='transparent')
    
    return area_chart

def create_radial_chart(trades_ganhadores, trades_perdedores):
    """Cria gráfico radial no estilo especificado"""
    if trades_ganhadores == 0 and trades_perdedores == 0:
        return None
    
    source = pd.DataFrame({
        "values": [trades_ganhadores, trades_perdedores],
        "labels": ["Ganhadores", "Perdedores"]
    })
    
    source = source[source['values'] > 0]
    
    if source.empty:
        return None
    
    base = alt.Chart(source).encode(
        alt.Theta("values:Q").stack(True),
        alt.Radius("values").scale(type="sqrt", zero=True, rangeMin=20),
        color=alt.Color("labels:N", 
                       scale=alt.Scale(domain=["Ganhadores", "Perdedores"], 
                                     range=["#28a745", "#dc3545"]),
                       legend=None)
    )
    
    c1 = base.mark_arc(innerRadius=20, stroke="#fff", strokeWidth=2)
    
    c2 = base.mark_text(radiusOffset=15, color='white', fontSize=12, fontWeight='bold').encode(
        text="values:Q"
    )
    
    chart = (c1 + c2).properties(
        width=250,
        height=250,
        background='transparent'
    )
    
    return chart

# --- Interface ---
st.title("🔥 Trading Analytics Pro")

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ➕ Adicionar Operação")
    
    with st.form("nova_operacao"):
        ativo = st.selectbox("Ativo", ["WDOFUT", "WINFUT"])
        data_abertura = st.date_input("Data", value=date.today())
        quantidade = st.number_input("Contratos", min_value=1, value=1)
        tipo_operacao = st.selectbox("Tipo", ["Compra", "Venda"])
        resultado_input = st.text_input("Resultado (R$)", value="0,00")
        
        try:
            resultado_valor = float(resultado_input.replace(',', '.'))
        except ValueError:
            st.error("Valor inválido. Use números com vírgula decimal.")
            resultado_valor = 0.0

        submitted = st.form_submit_button("✅ Adicionar")
        
        if submitted:
            if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado_valor):
                st.success("✅ Trade adicionado!")
                st.cache_data.clear()
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ Erro ao adicionar")

    st.markdown("### 🔎 Filtros")
    
    df = load_data()
    
    if not df.empty and 'ABERTURA' in df.columns:
        data_min = df['ABERTURA'].min().date()
        data_max = df['ABERTURA'].max().date()
        data_inicial, data_final = st.date_input(
            "Período", value=(data_min, data_max),
            min_value=data_min, max_value=data_max
        )
        df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
    else:
        df_filtrado = df.copy()

    st.markdown("### 📊 Resumo por Ativo")
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
    # Dados filtrados
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
    
    # Criando abas para diferentes análises
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral", 
        "📈 Desempenho", 
        "🔍 Análise Detalhada",
        "🏆 Performance"
    ])

    with tab1:
        # --- Métricas Básicas ---
        st.subheader("📊 Métricas Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Total", formatar_moeda(valor_total))
        
        with col2:
            st.metric("📈 Média/Trade", formatar_moeda(media_resultado))
        
        with col3:
            st.metric("🎯 Total Trades", f"{total_trades}")
        
        with col4:
            st.metric("✅ Taxa de Acerto", f"{taxa_acerto:.0f}%")
        
        # --- Gráficos Principais ---
        st.subheader("🔥 Atividade Anual")
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
        
        st.subheader("📈 Evolução Acumulada")
        if not df_por_dia.empty:
            df_area = df_por_dia.copy().sort_values('Data')
            df_area['Acumulado'] = df_area['Resultado_Liquido_Dia'].cumsum()
            evolution_chart = create_evolution_chart_with_gradient(df_area)
            st.altair_chart(evolution_chart, use_container_width=True)

    with tab2:
        # --- Métricas de Risco ---
        st.subheader("📉 Métricas de Risco")
        col5, col6, col7 = st.columns(3)
        
        with col5:
            if not df_por_dia.empty:
                max_drawdown = (df_area['Acumulado'].cummax() - df_area['Acumulado']).max()
                st.metric("📉 Máximo Drawdown", formatar_moeda(max_drawdown))
        
        with col6:
            if len(df_filtrado) > 1:
                sharpe_ratio = (media_resultado / df_filtrado['RESULTADO_LIQUIDO'].std()) * np.sqrt(252)
                st.metric("⚖️ Índice Sharpe", f"{sharpe_ratio:.2f}")
        
        with col7:
            if trades_perdedores > 0:
                win_loss_ratio = trades_ganhadores / trades_perdedores
                st.metric("📊 Ratio Win/Loss", f"{win_loss_ratio:.2f}:1")
            elif trades_ganhadores > 0:
                st.metric("📊 Ratio Win/Loss", f"{trades_ganhadores}:0")
        
        # --- Distribuição de Resultados ---
        st.subheader("📊 Distribuição de Resultados")
        if not df_filtrado.empty:
            hist_values = df_filtrado['RESULTADO_LIQUIDO']
            hist_chart = alt.Chart(df_filtrado).mark_bar().encode(
                alt.X("RESULTADO_LIQUIDO:Q", bin=True, title="Resultado (R$)"),
                alt.Y('count()', title="Quantidade de Trades"),
                color=alt.value('#4fc3f7')
            ).properties(height=300)
            st.altair_chart(hist_chart, use_container_width=True)
        
        # --- Performance por Horário ---
        st.subheader("🕒 Performance por Horário")
        if 'ABERTURA' in df_filtrado.columns:
            df_filtrado['HORA'] = df_filtrado['ABERTURA'].dt.hour
            performance_horario = df_filtrado.groupby('HORA')['RESULTADO_LIQUIDO'].mean().reset_index()
            bar_chart = alt.Chart(performance_horario).mark_bar().encode(
                x='HORA:O',
                y='RESULTADO_LIQUIDO:Q',
                color=alt.condition(
                    alt.datum.RESULTADO_LIQUIDO >= 0,
                    alt.value('#28a745'),
                    alt.value('#dc3545')
                )
            ).properties(height=300)
            st.altair_chart(bar_chart, use_container_width=True)

    with tab3:
        # --- Correlação entre Ativos ---
        st.subheader("🔗 Correlação entre Ativos")
        if 'ATIVO' in df_filtrado.columns:
            pivot_df = df_filtrado.pivot_table(
                index='ABERTURA', 
                columns='ATIVO', 
                values='RESULTADO_LIQUIDO', 
                aggfunc='sum'
            ).fillna(0)
            
            if len(pivot_df.columns) > 1:
                corr_matrix = pivot_df.corr()
                # Formatar a matriz de correlação para visualização
                corr_chart = alt.Chart(corr_matrix.reset_index().melt('index')).mark_rect().encode(
                    x='index:O',
                    y='variable:O',
                    color=alt.Color('value:Q', scale=alt.Scale(scheme='redblue', reverse=True)),
                    tooltip=['index', 'variable', 'value']
                ).properties(width=600, height=500)
                st.altair_chart(corr_chart, use_container_width=True)
            else:
                st.info("Necessário mais de um ativo para calcular correlação")
        
        # --- Dispersão: Resultado vs Volume ---
        st.subheader("💹 Resultado vs Volume de Contratos")
        if 'QUANTIDADE' in df_filtrado.columns:
            scatter_data = df_filtrado[['QUANTIDADE', 'RESULTADO_LIQUIDO']]
            scatter_chart = alt.Chart(scatter_data).mark_circle(size=60).encode(
                x='QUANTIDADE:Q',
                y='RESULTADO_LIQUIDO:Q',
                color=alt.condition(
                    alt.datum.RESULTADO_LIQUIDO >= 0,
                    alt.value('#28a745'),
                    alt.value('#dc3545')
                ),
                tooltip=['QUANTIDADE', 'RESULTADO_LIQUIDO']
            ).properties(height=400)
            st.altair_chart(scatter_chart, use_container_width=True)
        
        # --- Sazonalidade ---
        st.subheader("🔄 Análise de Sazonalidade")
        if not df_filtrado.empty:
            df_semanal = df_filtrado.set_index('ABERTURA').resample('W')['RESULTADO_LIQUIDO'].sum().reset_index()
            sazonal_chart = alt.Chart(df_semanal).mark_bar().encode(
                x='ABERTURA:T',
                y='RESULTADO_LIQUIDO:Q',
                color=alt.condition(
                    alt.datum.RESULTADO_LIQUIDO >= 0,
                    alt.value('#28a745'),
                    alt.value('#dc3545')
                )
            ).properties(height=400)
            st.altair_chart(sazonal_chart, use_container_width=True)

    with tab4:
        # --- Top Operações ---
        st.subheader("🏆 Top Operações")
        col_top1, col_top2 = st.columns(2)
        
        with col_top1:
            st.markdown("##### ✅ Melhores Operações")
            if not df_filtrado.empty:
                top_ganhos = df_filtrado.nlargest(5, 'RESULTADO_LIQUIDO')[['ATIVO', 'ABERTURA', 'QUANTIDADE', 'RESULTADO_LIQUIDO']]
                st.dataframe(top_ganhos.style.format({
                    'RESULTADO_LIQUIDO': lambda x: formatar_moeda(x),
                    'ABERTURA': lambda x: x.strftime('%d/%m/%Y')
                }), height=300)
        
        with col_top2:
            st.markdown("##### ❌ Piores Operações")
            if not df_filtrado.empty:
                top_perdas = df_filtrado.nsmallest(5, 'RESULTADO_LIQUIDO')[['ATIVO', 'ABERTURA', 'QUANTIDADE', 'RESULTADO_LIQUIDO']]
                st.dataframe(top_perdas.style.format({
                    'RESULTADO_LIQUIDO': lambda x: formatar_moeda(x),
                    'ABERTURA': lambda x: x.strftime('%d/%m/%Y')
                }), height=300)
        
        # --- Evolução de Capital ---
        st.subheader("📈 Evolução de Capital por Trade")
        if not df_filtrado.empty:
            df_capital = df_filtrado.sort_values('ABERTURA')
            df_capital['Capital Acumulado'] = df_capital['RESULTADO_LIQUIDO'].cumsum()
            capital_chart = alt.Chart(df_capital).mark_line(
                stroke='#4fc3f7',
                strokeWidth=3
            ).encode(
                x='ABERTURA:T',
                y='Capital Acumulado:Q',
                tooltip=['ABERTURA:T', 'Capital Acumulado:Q']
            ).properties(height=400)
            st.altair_chart(capital_chart, use_container_width=True)
        
        # --- Indicadores de Consistência ---
        st.subheader("📏 Indicadores de Consistência")
        col_con1, col_con2, col_con3 = st.columns(3)
        
        with col_con1:
            if not df_por_dia.empty:
                dias_lucrativos = (df_por_dia['Resultado_Liquido_Dia'] > 0).sum()
                st.metric("📈 Dias Lucrativos", f"{dias_lucrativos} ({dias_lucrativos/len(df_por_dia)*100:.0f}%)")
        
        with col_con2:
            if not df_por_dia.empty:
                sequencia_ganhos = (df_por_dia['Resultado_Liquido_Dia'] > 0).astype(int)
                sequencia_ganhos = sequencia_ganhos.groupby((sequencia_ganhos != sequencia_ganhos.shift()).cumsum()).cumcount() + 1
                max_sequencia_ganhos = sequencia_ganhos.max()
                st.metric("🔥 Maior Sequência de Ganhos", f"{max_sequencia_ganhos} dias")
        
        with col_con3:
            if not df_por_dia.empty:
                sequencia_perdas = (df_por_dia['Resultado_Liquido_Dia'] < 0).astype(int)
                sequencia_perdas = sequencia_perdas.groupby((sequencia_perdas != sequencia_perdas.shift()).cumsum()).cumcount() + 1
                max_sequencia_perdas = sequencia_perdas.max()
                st.metric("💧 Maior Sequência de Perdas", f"{max_sequencia_perdas} dias")

# Rodapé
st.markdown("""
<div style="text-align:center;color:#666;font-size:0.8rem;margin-top:2rem;padding:1rem;border-top:1px solid #333;background:rgba(0,0,0,0.8);">
    🔥 Trading Analytics Pro • 2025 • Fagulhas 3D + Som ambiente
</div>
""", unsafe_allow_html=True)
