# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import time
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import traceback
import locale

# Configurar localização para português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except:
        pass

# Suprimir warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações ---
SPREADSHEET_ID = "16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM"
WORKSHEET_NAME = "dados"

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Disciplinas",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Customizado ---
st.markdown("""
<style>
    /* Importar fontes do Google */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e configurações globais */
    .main {
        padding-top: 2rem;
    }
    
    /* Customizar fonte principal */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header personalizado */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        text-align: center;
        margin: 0.5rem 0 0 0;
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c3e50;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0;
    }
    
    /* Seções */
    .section-header {
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 2rem 0 1rem 0;
        border-left: 4px solid #28a745;
    }
    
    .section-header h2 {
        color: #2c3e50;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    
    /* Filtros */
    .filter-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #e9ecef;
    }
    
    /* Tabela customizada */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    
    /* Status badges */
    .status-feito {
        background-color: #d4edda;
        color: #155724;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .status-pendente {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .status-andamento {
        background-color: #cce5ff;
        color: #004085;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .status-nao-iniciado {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Sidebar customizada */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Selectbox customizado */
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 2px solid #e9ecef;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Gráficos */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .metric-value {
            font-size: 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Funções de Autenticação e Carregamento de Dados ---
@st.cache_resource(ttl=timedelta(hours=1))
def get_gspread_client():
    try:
        # Carregar credenciais do Streamlit Secrets
        creds_info = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
            "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
        }
        creds = Credentials.from_service_account_info(creds_info)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"❌ Erro ao autenticar com o Google Sheets: {e}")
        st.info("💡 Verifique se as credenciais estão configuradas corretamente no secrets.toml")
        st.stop()

@st.cache_data(ttl=timedelta(minutes=5))
def load_data(spreadsheet_id, worksheet_name):
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_id(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except SpreadsheetNotFound:
        st.error(f"❌ Planilha com ID '{spreadsheet_id}' não encontrada.")
        st.info("💡 Verifique se o ID da planilha está correto e se a conta de serviço tem acesso.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados da planilha: {e}")
        st.stop()

# --- Header Principal ---
st.markdown("""
<div class="main-header">
    <h1>📚 Dashboard de Disciplinas</h1>
    <p>Acompanhe o progresso dos seus estudos em tempo real</p>
</div>
""", unsafe_allow_html=True)

# --- Carregar Dados ---
with st.spinner("🔄 Carregando dados da planilha..."):
    df = load_data(SPREADSHEET_ID, WORKSHEET_NAME)

if df is not None and not df.empty:
    st.success("✅ Dados carregados com sucesso!")
else:
    st.warning("⚠️ Não foi possível carregar os dados ou a planilha está vazia.")
    st.stop()

# --- Processamento de Dados ---
required_columns = ['Disciplinas', 'Feito', 'Pendente']

# Verificar se as colunas existem
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error(f"❌ Colunas não encontradas: {', '.join(missing_columns)}")
    st.info("📋 Colunas disponíveis na planilha:")
    st.write(df.columns.tolist())
    st.stop()

# Converter colunas para numérico
df['Feito'] = pd.to_numeric(df['Feito'], errors='coerce').fillna(0)
df['Pendente'] = pd.to_numeric(df['Pendente'], errors='coerce').fillna(0)
df['Total'] = df['Feito'] + df['Pendente']

# Adicionar status geral
def get_status(row):
    if row['Feito'] > 0 and row['Pendente'] == 0:
        return "Feito"
    elif row['Pendente'] > 0 and row['Feito'] == 0:
        return "Pendente"
    elif row['Feito'] > 0 and row['Pendente'] > 0:
        return "Em Andamento"
    else:
        return "Não Iniciado"

df['Status Geral'] = df.apply(get_status, axis=1)

# --- Métricas Principais ---
col1, col2, col3, col4 = st.columns(4)

total_disciplinas = len(df['Disciplinas'].unique())
total_feito = int(df['Feito'].sum())
total_pendente = int(df['Pendente'].sum())
total_conteudos = total_feito + total_pendente

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value">{total_disciplinas}</p>
        <p class="metric-label">Disciplinas</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value" style="color: #28a745;">{total_feito}</p>
        <p class="metric-label">Conteúdos Feitos</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value" style="color: #ffc107;">{total_pendente}</p>
        <p class="metric-label">Conteúdos Pendentes</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    progresso = (total_feito / total_conteudos * 100) if total_conteudos > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value" style="color: #667eea;">{progresso:.1f}%</p>
        <p class="metric-label">Progresso Geral</p>
    </div>
    """, unsafe_allow_html=True)

# --- Gráficos em Rosca ---
st.markdown("""
<div class="section-header">
    <h2>📊 Análise Visual dos Dados</h2>
</div>
""", unsafe_allow_html=True)

# Preparar dados para gráficos
df_grouped = df.groupby('Disciplinas')[['Feito', 'Pendente']].sum().reset_index()
df_melted = df_grouped.melt(id_vars=['Disciplinas'], var_name='Status', value_name='Quantidade')

# Gráfico 1: Status Geral (Feito vs Pendente)
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    
    # Dados para o gráfico de status geral
    status_data = pd.DataFrame({
        'Status': ['Feito', 'Pendente'],
        'Quantidade': [total_feito, total_pendente]
    })
    
    chart_status = alt.Chart(status_data).mark_arc(
        outerRadius=120,
        innerRadius=60,
        stroke='white',
        strokeWidth=2
    ).encode(
        theta=alt.Theta(field="Quantidade", type="quantitative"),
        color=alt.Color(
            field="Status", 
            type="nominal", 
            title="Status",
            scale=alt.Scale(range=["#28a745", "#ffc107"])
        ),
        tooltip=["Status", "Quantidade"]
    ).properties(
        title=alt.TitleParams(
            text="Status Geral (Feito vs Pendente)",
            fontSize=16,
            fontWeight='bold'
        ),
        width=300,
        height=300
    )
    
    text_status = chart_status.mark_text(
        radius=140,
        fontSize=14,
        fontWeight='bold'
    ).encode(
        text=alt.Text("Quantidade", format=".0f"),
        color=alt.value("black")
    )
    
    st.altair_chart(chart_status + text_status, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    
    # Gráfico 2: Distribuição por Disciplinas
    chart_disciplinas = alt.Chart(df_grouped).mark_arc(
        outerRadius=120,
        innerRadius=60,
        stroke='white',
        strokeWidth=2
    ).encode(
        theta=alt.Theta(field="Total", type="quantitative"),
        color=alt.Color(
            field="Disciplinas", 
            type="nominal", 
            title="Disciplina",
            scale=alt.Scale(scheme='category20')
        ),
        tooltip=["Disciplinas", "Total"]
    ).properties(
        title=alt.TitleParams(
            text="Distribuição por Disciplina",
            fontSize=16,
            fontWeight='bold'
        ),
        width=300,
        height=300
    )
    
    text_disciplinas = chart_disciplinas.mark_text(
        radius=140,
        fontSize=12,
        fontWeight='bold'
    ).encode(
        text=alt.Text("Total", format=".0f"),
        color=alt.value("black")
    )
    
    st.altair_chart(chart_disciplinas + text_disciplinas, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Gráfico de Barras por Disciplina ---
st.markdown('<div class="chart-container">', unsafe_allow_html=True)

chart_barras = alt.Chart(df_melted).mark_bar().encode(
    x=alt.X('Disciplinas:N', title='Disciplinas', sort='-y'),
    y=alt.Y('Quantidade:Q', title='Quantidade de Conteúdos'),
    color=alt.Color(
        'Status:N',
        scale=alt.Scale(range=["#28a745", "#ffc107"]),
        title="Status"
    ),
    tooltip=['Disciplinas', 'Status', 'Quantidade']
).properties(
    title=alt.TitleParams(
        text="Conteúdos por Disciplina e Status",
        fontSize=18,
        fontWeight='bold'
    ),
    width=800,
    height=400
)

st.altair_chart(chart_barras, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Filtros e Lista de Conteúdos ---
st.markdown("""
<div class="section-header">
    <h2>🔍 Lista Detalhada de Conteúdos</h2>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="filter-container">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    all_disciplinas = ["Todos"] + sorted(df["Disciplinas"].unique().tolist())
    selected_disciplina = st.selectbox("🎯 Filtrar por Disciplina:", all_disciplinas)

with col2:
    all_status_geral = ["Todos"] + sorted(df["Status Geral"].unique().tolist())
    selected_status_geral = st.selectbox("📊 Filtrar por Status:", all_status_geral)

with col3:
    # Botão para limpar filtros
    if st.button("🔄 Limpar Filtros"):
        st.experimental_rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Aplicar filtros
filtered_df = df.copy()

if selected_disciplina != "Todos":
    filtered_df = filtered_df[filtered_df["Disciplinas"] == selected_disciplina]

if selected_status_geral != "Todos":
    filtered_df = filtered_df[filtered_df["Status Geral"] == selected_status_geral]

# Função para aplicar cores aos status
def color_status(val):
    if val == "Feito":
        return 'background-color: #d4edda; color: #155724; font-weight: bold; border-radius: 10px; padding: 5px;'
    elif val == "Pendente":
        return 'background-color: #fff3cd; color: #856404; font-weight: bold; border-radius: 10px; padding: 5px;'
    elif val == "Em Andamento":
        return 'background-color: #cce5ff; color: #004085; font-weight: bold; border-radius: 10px; padding: 5px;'
    elif val == "Não Iniciado":
        return 'background-color: #f8d7da; color: #721c24; font-weight: bold; border-radius: 10px; padding: 5px;'
    return ''

# Exibir informações dos filtros aplicados
if selected_disciplina != "Todos" or selected_status_geral != "Todos":
    filtros_aplicados = []
    if selected_disciplina != "Todos":
        filtros_aplicados.append(f"Disciplina: {selected_disciplina}")
    if selected_status_geral != "Todos":
        filtros_aplicados.append(f"Status: {selected_status_geral}")
    
    st.info(f"🔍 Filtros aplicados: {' | '.join(filtros_aplicados)} | Resultados: {len(filtered_df)} registros")

# Preparar dados para exibição
display_df = filtered_df[["Disciplinas", "Feito", "Pendente", "Total", "Status Geral"]].copy()

# Verificar se existe coluna de conteúdo
content_columns = [col for col in df.columns if 'conteudo' in col.lower() or 'conteúdo' in col.lower()]
if content_columns:
    display_df = filtered_df[["Disciplinas"] + content_columns + ["Feito", "Pendente", "Total", "Status Geral"]].copy()

# Aplicar estilo à tabela
styled_df = display_df.style.applymap(color_status, subset=['Status Geral'])

# Exibir tabela
st.dataframe(
    styled_df,
    use_container_width=True,
    height=400
)

# --- Resumo dos Filtros ---
if len(filtered_df) > 0:
    st.markdown("### 📈 Resumo dos Dados Filtrados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        feito_filtrado = int(filtered_df['Feito'].sum())
        st.metric("✅ Total Feito", feito_filtrado)
    
    with col2:
        pendente_filtrado = int(filtered_df['Pendente'].sum())
        st.metric("⏳ Total Pendente", pendente_filtrado)
    
    with col3:
        total_filtrado = feito_filtrado + pendente_filtrado
        progresso_filtrado = (feito_filtrado / total_filtrado * 100) if total_filtrado > 0 else 0
        st.metric("📊 Progresso", f"{progresso_filtrado:.1f}%")

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 2rem;">
    <p>📚 Dashboard de Disciplinas | Desenvolvido com ❤️ usando Streamlit</p>
    <p>🔄 Dados atualizados automaticamente a cada 5 minutos</p>
</div>
""", unsafe_allow_html=True)

# --- Informações de Debug (apenas para desenvolvimento) ---
if st.sidebar.checkbox("🔧 Modo Debug"):
    st.sidebar.markdown("### 🔍 Informações de Debug")
    st.sidebar.write("**Colunas da planilha:**")
    st.sidebar.write(df.columns.tolist())
    st.sidebar.write("**Shape dos dados:**")
    st.sidebar.write(f"{df.shape[0]} linhas x {df.shape[1]} colunas")
    st.sidebar.write("**Tipos de dados:**")
    st.sidebar.write(df.dtypes)

