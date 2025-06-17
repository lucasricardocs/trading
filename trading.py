# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.gridspec as gridspec
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

# --- Configuração da Página e CSS Customizado (UI/UX Aprimorado) ---
st.set_page_config(
    page_title="Trading Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Aprimorado para UI/UX Superior[2]
st.markdown("""
<style>
    /* Reset e Base */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: #e8eaed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header Principal */
    h1 {
        background: linear-gradient(90deg, #4fc3f7 0%, #29b6f6 50%, #03a9f4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    /* Subtítulos Minimalistas */
    h2, h3 {
        color: #b3b3b3;
        font-weight: 500;
        border-bottom: 1px solid #2a2a3e;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    
    /* Sidebar Elegante */
    .css-1d391kg {
        background: rgba(26, 26, 46, 0.95);
        backdrop-filter: blur(10px);
        border-right: 1px solid #2a2a3e;
    }
    
    /* Métricas com Glassmorphism */
    [data-testid="stMetric"] {
        background: rgba(42, 42, 62, 0.3);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        border-color: rgba(79, 195, 247, 0.3);
    }
    
    [data-testid="stMetricLabel"] > div {
        color: #9e9e9e;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    [data-testid="stMetricValue"] {
        color: #e8eaed;
        font-weight: 600;
        font-size: 1.4rem;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem;
        opacity: 0.8;
    }
    
    /* Inputs Modernos */
    .stSelectbox > div > div {
        background: rgba(42, 42, 62, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #e8eaed;
    }
    
    .stTextInput > div > div > input {
        background: rgba(42, 42, 62, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #e8eaed;
    }
    
    .stNumberInput > div > div > input {
        background: rgba(42, 42, 62, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #e8eaed;
    }
    
    /* Botões Elegantes */
    .stButton > button {
        background: linear-gradient(45deg, #29b6f6, #03a9f4);
        border: none;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(41, 182, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(41, 182, 246, 0.4);
        background: linear-gradient(45deg, #03a9f4, #0288d1);
    }
    
    /* Containers com Blur */
    .element-container {
        background: rgba(42, 42, 62, 0.2);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Alertas Estilizados */
    [data-testid="stAlert"] {
        background: rgba(42, 42, 62, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Expander Limpo */
    .streamlit-expanderHeader {
        background: rgba(42, 42, 62, 0.3);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Dataframe Moderno */
    .dataframe {
        background: rgba(42, 42, 62, 0.3);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Scrollbar Customizada */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(42, 42, 62, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(79, 195, 247, 0.5);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(79, 195, 247, 0.7);
    }
    
    /* Animações Suaves */
    * {
        transition: all 0.2s ease;
    }
    
    /* Rodapé Elegante */
    .footer {
        background: rgba(26, 26, 46, 0.8);
        backdrop-filter: blur(10px);
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1rem;
        margin-top: 2rem;
        border-radius: 12px 12px 0 0;
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
            st.error("🔐 Credenciais não encontradas")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict:
            st.error("🔐 Credenciais vazias")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"❌ Erro de autenticação: {e}")
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
            st.error(f"📄 Planilha não encontrada")
            return None
        except Exception as e:
            st.error(f"❌ Erro ao acessar planilha: {e}")
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
            st.error(f"❌ Erro ao ler dados: {e}")
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
            st.error(f"❌ Erro ao adicionar: {e}")
            return False
    return False

def calcular_largura_e_espacamento(num_elementos):
    """Calcula largura e espaçamento para centralizar histogramas."""
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

def create_3d_heatmap(df_heatmap_final):
    """Cria um heatmap 3D minimalista para perspectiva."""[5][6]
    
    plt.style.use('dark_background')
    
    fig = plt.figure(figsize=(8, 2.5))
    fig.patch.set_alpha(0.0)
    
    gs = gridspec.GridSpec(1, 1, figure=fig, 
                          left=0.05, right=0.95, 
                          top=0.90, bottom=0.10)
    
    ax = fig.add_subplot(gs[0], projection='3d')
    
    try:
        ax.set_box_aspect([4, 1, 0.3])
    except:
        pass
    
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
    
    dx = dy = 0.7
    dz = []
    
    max_abs_resultado = max(abs(min(resultados)), abs(max(resultados))) if resultados else 1
    
    for resultado in resultados:
        if resultado == 0:
            dz.append(0.01)
        else:
            altura_barra = (abs(resultado) / max_abs_resultado) * 0.8 + 0.05
            dz.append(altura_barra)
    
    dz = np.array(dz)
    
    cores = []
    for resultado in resultados:
        if resultado > 0:
            intensity = min(abs(resultado) / max_abs_resultado, 1.0) if max_abs_resultado > 0 else 0
            if intensity < 0.3:
                cores.append('#2d5a47')
            elif intensity < 0.6:
                cores.append('#3d7c5a')
            else:
                cores.append('#4d9e6d')
        elif resultado < 0:
            intensity = min(abs(resultado) / max_abs_resultado, 1.0) if max_abs_resultado > 0 else 0
            if intensity < 0.3:
                cores.append('#5a2d2d')
            elif intensity < 0.6:
                cores.append('#7c3d3d')
            else:
                cores.append('#9e4d4d')
        else:
            cores.append('#2a2a2a')
    
    bars = ax.bar3d(x, y, z, dx, dy, dz, color=cores, shade=True, alpha=0.8, 
                    edgecolor='none', linewidth=0)
    
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('none')
    ax.yaxis.pane.set_edgecolor('none')
    ax.zaxis.pane.set_edgecolor('none')
    ax.grid(False)
    
    ax.set_xlim(0, 53)
    ax.set_ylim(-0.5, 6.5)
    ax.set_zlim(0, max(dz) * 1.2 if len(dz) > 0 else 1)
    
    ax.view_init(elev=60, azim=-30)
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, 
                bbox_inches='tight', facecolor='none', 
                edgecolor='none', transparent=True,
                pad_inches=0)
    buffer.seek(0)
    plt.close()
    
    return buffer

def create_heatmap_2d_github(df_heatmap_final):
    """Cria um heatmap 2D minimalista estilo GitHub."""[3]
    
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
    day_name_map = {0: 'S', 1: 'T', 2: 'Q', 3: 'Q', 4: 'S', 5: 'S', 6: 'D'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    
    day_display_names = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D']
    
    full_df['month'] = full_df['Data_dt'].dt.month
    full_df['month_name'] = full_df['Data_dt'].dt.strftime('%b')

    full_df['week_corrected'] = ((full_df['Data_dt'] - start_date).dt.days // 7)
    
    month_labels = full_df[full_df['is_current_year']].groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    months_chart = alt.Chart(month_labels).mark_text(
        align='center',
        baseline='bottom',
        fontSize=10,
        dy=-3,
        dx=-20,
        color='#6b7280',
        fontWeight='normal'
    ).encode(
        x=alt.X('week_corrected:O', axis=None),
        text='month_name:N'
    )

    tooltip_fields = [
        alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
        alt.Tooltip('RESULTADO_LIQUIDO:Q', title='R$', format=',.2f')
    ]

    valores = full_df[full_df['is_current_year']]['RESULTADO_LIQUIDO']
    max_positivo = valores[valores > 0].max() if len(valores[valores > 0]) > 0 else 100
    max_negativo = valores[valores < 0].min() if len(valores[valores < 0]) > 0 else -100
    
    threshold_1 = max_positivo * 0.25
    threshold_2 = max_positivo * 0.5
    threshold_3 = max_positivo * 0.75

    heatmap = alt.Chart(full_df).mark_rect(
        stroke='#1f2937',
        strokeWidth=1,
        cornerRadius=1
    ).encode(
        x=alt.X('week_corrected:O', title=None, axis=None),
        y=alt.Y('day_display_name:N', 
                sort=day_display_names,
                title=None,
                axis=alt.Axis(
                    labelAngle=0, 
                    labelFontSize=9, 
                    ticks=False, 
                    domain=False, 
                    grid=False, 
                    labelColor='#6b7280',
                    labelPadding=6
                )),
        color=alt.condition(
            alt.datum.display_resultado == None,
            alt.value('#1f2937'),
            alt.condition(
                alt.datum.display_resultado == 0,
                alt.value('#f9fafb'),
                alt.condition(
                    alt.datum.display_resultado > 0,
                    alt.Color('display_resultado:Q',
                        scale=alt.Scale(
                            range=['#dcfce7', '#86efac', '#22c55e', '#16a34a'],
                            type='threshold',
                            domain=[0.01, threshold_1, threshold_2, threshold_3]
                        ),
                        legend=None),
                    alt.Color('display_resultado:Q',
                        scale=alt.Scale(
                            range=['#fef2f2', '#fca5a5', '#ef4444', '#dc2626'],
                            type='threshold',
                            domain=[max_negativo, max_negativo * 0.75, max_negativo * 0.5, max_negativo * 0.25]
                        ),
                        legend=None)
                )
            )
        ),
        tooltip=tooltip_fields
    ).properties(
        height=200
    )

    final_chart = alt.vconcat(
        months_chart,
        heatmap,
        spacing=5
    ).configure_view(
        strokeWidth=0
    ).configure(
        background='transparent'
    )

    return final_chart

# --- Interface Principal ---
st.title("Trading Analytics")

# --- Sidebar Minimalista ---
with st.sidebar:
    st.markdown("### ➕ Nova Operação")
    
    with st.form("nova_operacao"):
        ativo = st.selectbox("Ativo", ["WDOFUT", "WINFUT"])
        data_abertura = st.date_input("Data", value=date.today())
        quantidade = st.number_input("Contratos", min_value=1, value=1)
        tipo_operacao = st.selectbox("Tipo", ["Compra", "Venda"])
        
        resultado_input = st.text_input("Resultado (R$)", value="0,00")
        
        try:
            resultado = float(resultado_input.replace(',', '.'))
        except ValueError:
            st.error("Valor inválido")
            resultado = 0.0

        submitted = st.form_submit_button("✅ Adicionar")
        
        if submitted:
            if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
                st.success("✅ Adicionado!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("❌ Erro")

# --- Carregar Dados ---
df = load_data()

# --- Sidebar: Filtros ---
with st.sidebar:
    st.markdown("### 🔎 Período")
    if not df.empty and 'ABERTURA' in df.columns:
        data_min = df['ABERTURA'].min().date()
        data_max = df['ABERTURA'].max().date()
        data_inicial, data_final = st.date_input(
            "Intervalo",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max
        )
        df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
    else:
        df_filtrado = df.copy()

    st.markdown("### 📊 Por Ativo")
    if not df_filtrado.empty:
        resumo_ativo = df_filtrado.groupby('ATIVO').agg({
            'RESULTADO': ['count', 'sum'],
            'CUSTO': 'sum',
            'RESULTADO_LIQUIDO': ['sum', 'mean']
        }).round(2)
        
        resumo_ativo.columns = ['Trades', 'Bruto', 'Custo', 'Líquido', 'Média']
        resumo_ativo = resumo_ativo.reset_index()
        
        st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)

# --- Corpo Principal ---
if df.empty:
    st.info("📊 Adicione sua primeira operação")
else:
    # Mensagem auto-dismiss
    success_container = st.empty()
    success_container.success(f"✅ {len(df)} operações carregadas")
    
    def clear_message():
        time.sleep(2)
        success_container.empty()
    
    threading.Thread(target=clear_message).start()
    
    with st.expander("📋 Dados"):
        st.dataframe(df, use_container_width=True)

    # --- Métricas ---[7]
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
        
        # Métricas Principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💰 Líquido Total",
                f"R$ {valor_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                f"R$ {valor_total_bruto:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
            )
        
        with col2:
            st.metric(
                "💸 Custos",
                f"R$ {custo_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                f"{(custo_total/valor_total_bruto*100):.1f}%" if valor_total_bruto != 0 else "0%"
            )
        
        with col3:
            st.metric(
                "📈 Média/Trade",
                f"R$ {media_resultado:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                f"{media_resultado:+.2f}".replace('.', 'X').replace(',', '.').replace('X', ',') if media_resultado != 0 else None
            )
        
        with col4:
            st.metric(
                "🎯 Taxa Acerto",
                f"{taxa_acerto:.1f}%",
                f"{trades_ganhadores}/{total_trades}"
            )

        # --- Heatmaps Minimalistas ---[3]
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
            
            # 3D Perspectiva
            heatmap_3d_buffer = create_3d_heatmap(df_heatmap_final)
            if heatmap_3d_buffer:
                col1, col2, col3 = st.columns([1, 8, 1])
                with col2:
                    st.image(heatmap_3d_buffer, use_container_width=True)
            
            # 2D Principal
            heatmap_2d_github = create_heatmap_2d_github(df_heatmap_final)
            if heatmap_2d_github:
                st.altair_chart(heatmap_2d_github, use_container_width=True)
        
        # --- Evolução Acumulada ---
        st.markdown("### 📊 Evolução")
        
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
                x=alt.X('Data:T', title=''),
                y=alt.Y('Resultado_Liquido_Acumulado:Q', title='Acumulado (R$)'),
                color=alt.Color(
                    'Cor_Area:N',
                    scale=alt.Scale(
                        domain=['Negativo', 'Positivo'],
                        range=['#ef4444', '#22c55e']
                    ),
                    legend=None
                ),
                tooltip=[
                    'Data:T', 
                    alt.Tooltip('Resultado_Liquido_Acumulado:Q', format='.2f', title='Acumulado'), 
                    alt.Tooltip('Resultado_Liquido_Dia:Q', format='.2f', title='Dia')
                ]
            ).properties(
                width='container',
                height=400,
                background='transparent'
            )
            
            st.altair_chart(area_chart, use_container_width=True)

        # --- Trades Individuais ---[7]
        st.markdown("### 📅 Por Trade")
        if not df_filtrado.empty:
            df_trades = df_filtrado.copy()
            df_trades = df_trades.sort_values('ABERTURA')
            df_trades['Trade_Index'] = range(1, len(df_trades) + 1)
            
            num_trades = len(df_trades)
            config = calcular_largura_e_espacamento(num_trades)
            
            bars = alt.Chart(df_trades).mark_bar(
                size=config['size'],
                cornerRadius=2,
                stroke='white',
                strokeWidth=0.5
            ).encode(
                x=alt.X('Trade_Index:O', 
                       title='',
                       axis=alt.Axis(grid=False, domain=False, ticks=False),
                       scale=alt.Scale(
                           paddingInner=config['padding'],
                           paddingOuter=0.1
                       )),
                y=alt.Y('RESULTADO_LIQUIDO:Q', 
                       title='R$',
                       axis=alt.Axis(grid=True, gridOpacity=0.1)),
                color=alt.condition(
                    alt.datum.RESULTADO_LIQUIDO > 0,
                    alt.value('#22c55e'),
                    alt.value('#ef4444')
                ),
                tooltip=[
                    alt.Tooltip('Trade_Index:O', title='#'),
                    alt.Tooltip('ABERTURA:T', title='Data', format='%d/%m'),
                    alt.Tooltip('ATIVO:N', title='Ativo'),
                    alt.Tooltip('RESULTADO_LIQUIDO:Q', format='.2f', title='R$')
                ]
            )
            
            linha_zero = alt.Chart(pd.DataFrame({'zero': [0]})).mark_rule(
                color='#ffffff',
                strokeWidth=2,
                opacity=0.5
            ).encode(y=alt.Y('zero:Q'))
            
            chart_final = (bars + linha_zero).properties(
                width='container',
                height=400,
                background='transparent'
            )
            
            st.altair_chart(chart_final, use_container_width=True)

# --- Rodapé Elegante ---
st.markdown("""
<div class="footer">
    <div style="text-align:center;color:#6b7280;font-size:0.9rem;">
        <strong>Trading Analytics</strong> • Desenvolvido com Python & Streamlit<br>
        <span style="font-size:0.8rem;">© 2025 • Análise profissional de trading</span>
    </div>
</div>
""", unsafe_allow_html=True)
