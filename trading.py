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
    locale.setlocale(locale.LC_TIME, 'pt_BR')

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
    /* Estilo geral */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle at top right, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
        z-index: 1;
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        z-index: 1;
    }
    
    .metric-card::after {
        content: "";
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(102,126,234,0.05) 0%, rgba(255,255,255,0) 70%);
        z-index: -1;
        transition: all 0.5s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(102,126,234,0.15);
    }
    
    .metric-card:hover::after {
        transform: scale(1.5);
    }
    
    /* Container dos gráficos */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 6px 25px rgba(0,0,0,0.08);
        border: 1px solid #f0f4f8;
        margin: 1rem 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .chart-container::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 5px;
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    .chart-container:hover {
        box-shadow: 0 10px 35px rgba(102,126,234,0.15);
    }
    
    /* Títulos dos gráficos */
    .chart-title {
        text-align: center;
        font-size: 1.3rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 1.5rem;
        padding: 0.8rem;
        background: linear-gradient(to right, #f8f9fa, #eef2f7);
        border-radius: 10px;
        position: relative;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.8rem 0;
        text-align: center;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(102,126,234,0.2);
        position: relative;
        overflow: hidden;
    }
    
    .info-box::before {
        content: "";
        position: absolute;
        top: -20%;
        left: -20%;
        width: 150%;
        height: 150%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
    }
    
    /* Progress info */
    .progress-info {
        background: #f8fafc;
        padding: 1.2rem;
        border-radius: 12px;
        text-align: center;
        margin-top: 1.5rem;
        border: 2px solid #eef2f7;
        font-size: 1rem;
        position: relative;
        box-shadow: 0 3px 10px rgba(0,0,0,0.03);
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 1.2rem 2.5rem;
        border-radius: 12px;
        text-align: center;
        margin: 2.5rem 0 1.5rem 0;
        font-size: 1.6rem;
        font-weight: 700;
        box-shadow: 0 5px 20px rgba(102,126,234,0.3);
        position: relative;
        overflow: hidden;
    }
    
    .section-header::after {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%23ffffff' fill-opacity='0.1' fill-rule='evenodd'/%3E%3C/svg%3E");
        opacity: 0.3;
    }
    
    /* Sidebar styling */
    .sidebar-content {
        background: linear-gradient(180deg, #4a6fc9, #5b3f8e);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .sidebar-content::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0));
    }
    
    /* Debug panel */
    .debug-panel {
        background: #f8fafc;
        border: 2px dashed #c5d5f8;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    }
    
    /* Botões */
    .stButton>button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.8rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(102,126,234,0.3) !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 15px rgba(102,126,234,0.4) !important;
    }
    
    /* Progress bars */
    .progress-bar {
        height: 20px;
        background: #e9ecef;
        border-radius: 10px;
        overflow: hidden;
        margin: 1rem 0;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .progress-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Footer */
    .dashboard-footer {
        background: linear-gradient(135deg, #4a6fc9, #5b3f8e);
        color: white;
        padding: 2.5rem;
        border-radius: 15px;
        margin-top: 3rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(102,126,234,0.3);
    }
    
    .dashboard-footer::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%23ffffff' fill-opacity='0.1' fill-rule='evenodd'/%3E%3C/svg%3E");
        opacity: 0.2;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .section-header {
            font-size: 1.3rem;
            padding: 1rem;
        }
        
        .chart-title {
            font-size: 1.1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Cores Padrão ---
COLOR_POSITIVE = "#28a745"  # Verde
COLOR_NEGATIVE = "#dc3545"  # Vermelho
COLOR_NEUTRAL = "#4fc3f7"   # Azul
COLOR_BASE = "#f0f0f0"      # Cinza claro

# Paleta de cores para as disciplinas
DISCIPLINA_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"
]

# --- Funções de Autenticação ---
@st.cache_resource
def get_google_auth():
    """Autenticação com Google Sheets"""
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    try:
        # Corrigido para usar a chave correta do Streamlit
        if "gcp_service_account" not in st.secrets:
            st.error("Credenciais do Google não encontradas nos secrets do Streamlit")
            return None
        
        credentials_dict = st.secrets["gcp_service_account"]
        if not credentials_dict:
            st.error("Credenciais vazias")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Obter planilha do Google Sheets"""
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
            st.error(f"Erro ao acessar planilha: {e}")
            return None
    return None

# --- Funções de Dados ---
@st.cache_data(ttl=300, show_spinner="Atualizando dados...")
def load_data():
    """Carregar dados da planilha"""
    worksheet = get_worksheet()
    if worksheet:
        try:
            all_values = worksheet.get_all_values()
            
            if not all_values or len(all_values) < 2:
                st.warning("Planilha vazia ou com poucos dados")
                return pd.DataFrame()
            
            headers = all_values[0]
            
            # Limpar cabeçalhos vazios e duplicados
            clean_headers = []
            for i, header in enumerate(headers):
                if header.strip():
                    clean_headers.append(header.strip())
                else:
                    clean_headers.append(f"Coluna_{i}")
            
            data_rows = all_values[1:]
            
            # Criar DataFrame
            df = pd.DataFrame(data_rows, columns=clean_headers)
            
            # Verificar e renomear colunas necessárias
            column_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if 'matéria' in col_lower or 'materia' in col_lower or 'disciplina' in col_lower:
                    column_mapping[col] = 'Matéria'
                elif 'status' in col_lower or 'situação' in col_lower or 'situacao' in col_lower:
                    column_mapping[col] = 'STATUS'
            
            df = df.rename(columns=column_mapping)
            
            # Verificar colunas obrigatórias
            required_columns = ['Matéria', 'STATUS']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Colunas obrigatórias não encontradas: {missing_columns}")
                st.info(f"Colunas disponíveis: {list(df.columns)}")
                return pd.DataFrame()
            
            # Limpar dados
            df = df.dropna(subset=['Matéria'])
            df = df[df['Matéria'] != '']
            
            # Normalizar valores de STATUS
            df['STATUS'] = df['STATUS'].str.strip().str.upper()
            
            # Filtrar apenas status válidos
            valid_status = ['FEITO', 'PENDENTE', 'EM ANDAMENTO', 'REVISÃO']
            df = df[df['STATUS'].isin(valid_status)]
            
            if df.empty:
                st.warning("Nenhum dado válido encontrado após limpeza")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            with st.expander("🔍 Informações de Debug"):
                st.error(f"Erro detalhado: {type(e).__name__} - {str(e)}")
                st.code(traceback.format_exc(), language='python')
            return pd.DataFrame()
    return pd.DataFrame()

def process_data_for_charts(df):
    """Processar dados para os gráficos usando groupby"""
    if df.empty:
        return {}
    
    # Agrupar por matéria e status
    grouped = df.groupby(['Matéria', 'STATUS']).size().unstack(fill_value=0)
    
    disciplinas_stats = {}
    
    for disciplina, row in grouped.iterrows():
        feito = row.get('FEITO', 0)
        pendente = row.get('PENDENTE', 0)
        em_andamento = row.get('EM ANDAMENTO', 0)
        revisao = row.get('REVISÃO', 0)
        
        total = feito + pendente + em_andamento + revisao
        
        if total > 0:
            percentual_feito = (feito / total) * 100
            
            disciplinas_stats[disciplina] = {
                'feito': feito,
                'pendente': pendente,
                'em_andamento': em_andamento,
                'revisao': revisao,
                'total': total,
                'percentual_feito': percentual_feito
            }
    
    return disciplinas_stats

# --- Funções de Visualização ---
def create_donut_chart(feito, pendente, em_andamento, revisao, disciplina, color_scheme=None):
    """Criar gráfico de rosca com Altair"""
    # Dados para o gráfico
    data = pd.DataFrame([
        {'categoria': 'Feito', 'valor': feito, 'disciplina': disciplina},
        {'categoria': 'Pendente', 'valor': pendente, 'disciplina': disciplina},
        {'categoria': 'Em Andamento', 'valor': em_andamento, 'disciplina': disciplina},
        {'categoria': 'Revisão', 'valor': revisao, 'disciplina': disciplina}
    ])
    
    # Cores padrão se não especificadas
    if color_scheme is None:
        color_scheme = [COLOR_POSITIVE, COLOR_NEGATIVE, "#ffc107", "#9c27b0"]
    
    # Gráfico de rosca
    chart = alt.Chart(data).mark_arc(
        innerRadius=60,
        outerRadius=90,
        stroke='white',
        strokeWidth=3,
        strokeOpacity=1
    ).encode(
        theta=alt.Theta('valor:Q'),
        color=alt.Color(
            'categoria:N',
            scale=alt.Scale(
                domain=['Feito', 'Pendente', 'Em Andamento', 'Revisão'],
                range=color_scheme
            ),
            legend=alt.Legend(
                orient='bottom',
                title=None,
                labelFontSize=11,
                symbolSize=150,
                symbolType='circle'
            )
        ),
        tooltip=[
            alt.Tooltip('categoria:N', title='Status'),
            alt.Tooltip('valor:Q', title='Quantidade'),
            alt.Tooltip('disciplina:N', title='Disciplina')
        ]
    ).properties(
        width=220,
        height=220
    )
    
    return chart

def create_summary_metrics(disciplinas_stats):
    """Criar métricas resumo"""
    if not disciplinas_stats:
        return 0, 0, 0, 0.0
    
    total_feito = sum(stats['feito'] for stats in disciplinas_stats.values())
    total_pendente = sum(stats['pendente'] for stats in disciplinas_stats.values())
    total_geral = sum(stats['total'] for stats in disciplinas_stats.values())
    percentual_geral = (total_feito / total_geral * 100) if total_geral > 0 else 0
    
    return total_feito, total_pendente, total_geral, percentual_geral

def create_progress_bar_chart(disciplinas_stats):
    """Criar gráfico de barras horizontais com progresso"""
    if not disciplinas_stats:
        return alt.Chart().mark_text(text='Nenhum dado disponível')
    
    # Preparar dados para o gráfico
    data = []
    for disciplina, stats in disciplinas_stats.items():
        data.append({
            'disciplina': disciplina,
            'percentual': stats['percentual_feito'],
            'feito': stats['feito'],
            'total': stats['total']
        })
    
    df_progress = pd.DataFrame(data)
    df_progress = df_progress.sort_values('percentual', ascending=True)
    
    # Gráfico de barras horizontais
    chart = alt.Chart(df_progress).mark_bar(
        height=25,
        cornerRadius=8,
        stroke='white',
        strokeWidth=2
    ).encode(
        x=alt.X('percentual:Q', 
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(title='Percentual Concluído (%)', 
                            titleFontSize=14, 
                            titleFontWeight='bold',
                            labelFontSize=12)),
        y=alt.Y('disciplina:O', 
                axis=alt.Axis(title=None, 
                            labelLimit=250, 
                            labelFontSize=12,
                            labelFontWeight='bold'),
                sort=alt.EncodingSortField(field='percentual', order='ascending')),
        color=alt.Color(
            'percentual:Q',
            scale=alt.Scale(
                range=['#ff6b6b', '#ffa502', '#2ed573'],
                domain=[0, 50, 100]
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip('disciplina:N', title='Disciplina'),
            alt.Tooltip('feito:Q', title='Concluídos'),
            alt.Tooltip('total:Q', title='Total'),
            alt.Tooltip('percentual:Q', title='Percentual (%)', format='.1f')
        ]
    ).properties(
        width=700,
        height=400
    )
    
    return chart

def display_metric_card(title, value, delta=None, help_text="", icon="📊"):
    """Exibir card de métrica personalizado"""
    delta_html = ""
    if delta:
        delta_color = "#28a745" if "%" in str(delta) and float(delta.replace("%", "")) > 0 else "#dc3545"
        delta_html = f'<div style="color: {delta_color}; font-size: 0.9rem; font-weight: 600;">📈 {delta}</div>'
    
    st.markdown(f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-size: 1.8rem; margin-right: 0.8rem; opacity: 0.8;">{icon}</span>
            <span style="color: #6c757d; font-size: 1rem; font-weight: 600;">{title}</span>
        </div>
        <div style="font-size: 2.2rem; font-weight: bold; color: #2c3e50; margin-bottom: 0.5rem; letter-spacing: -0.5px;">{value}</div>
        {delta_html}
        <div style="color: #6c757d; font-size: 0.9rem; margin-top: 0.5rem;">{help_text}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Função Principal ---
def main():
    """Função principal do dashboard"""
    
    # Calcular dias para a prova
    data_prova = date(2025, 9, 28)
    data_hoje = date.today()
    dias_para_prova = max(0, (data_prova - data_hoje).days)
    
    # Formatar data atual
    data_formatada = datetime.now().strftime("%A, %d de %B de %Y").title()
    
    # Definir cor e ícone baseado nos dias restantes
    if dias_para_prova > 60:
        cor_prazo = "#28a745"  # Verde
        icone_prazo = "🟢"
        status_prazo = "Bastante tempo"
    elif dias_para_prova > 30:
        cor_prazo = "#ffc107"  # Amarelo
        icone_prazo = "🟡"
        status_prazo = "Tempo moderado"
    elif dias_para_prova > 0:
        cor_prazo = "#fd7e14"  # Laranja
        icone_prazo = "🟠"
        status_prazo = "Reta final!"
    else:
        cor_prazo = "#dc3545"  # Vermelho
        icone_prazo = "🔴"
        status_prazo = "Prazo vencido"
    
    # Cabeçalho principal com informações da prova
    st.markdown(f"""
    <div class="main-header">
        <h1 style="font-size: 2.5rem; margin-bottom: 1rem;">📚 Dashboard de Estudos</h1>
        <p style="font-size: 1.2rem; opacity: 0.9; margin-bottom: 1.5rem;">Acompanhe seu progresso para o concurso público</p>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-top: 1.5rem;">
            <div style="background: rgba(255,255,255,0.15); padding: 1.5rem; border-radius: 15px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.8rem; display: flex; align-items: center;">
                    <span style="margin-right: 0.5rem;">📅</span> Data Atual
                </div>
                <div style="font-size: 1.5rem; font-weight: bold;">
                    {data_formatada}
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.15); padding: 1.5rem; border-radius: 15px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.8rem; display: flex; align-items: center;">
                    <span style="margin-right: 0.5rem;">🎯</span> Data da Prova
                </div>
                <div style="font-size: 1.5rem; font-weight: bold;">
                    Domingo, 28 de Setembro de 2025
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.15); padding: 1.5rem; border-radius: 15px; backdrop-filter: blur(10px); border: 2px solid {cor_prazo}; box-shadow: 0 0 15px {cor_prazo}40;">
                <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.8rem; display: flex; align-items: center;">
                    <span style="margin-right: 0.5rem;">{icone_prazo}</span> Dias Restantes
                </div>
                <div style="font-size: 2.5rem; font-weight: bold; color: {cor_prazo}; text-shadow: 0 0 10px {cor_prazo}80;">
                    {dias_para_prova} dias
                </div>
                <div style="font-size: 1rem; opacity: 0.9; margin-top: 0.5rem;">
                    {status_prazo}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Controles do Dashboard")
        
        # Botão para atualizar dados
        if st.button("🔄 Atualizar Dados", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        # Botão para debug
        debug_mode = st.checkbox("🔍 Modo Debug", help="Mostrar informações detalhadas para diagnóstico")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Informações técnicas
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 📊 Informações Técnicas")
        st.info("📡 Dados sincronizados automaticamente a cada 5 minutos")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Informações da prova
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 🎯 Informações da Prova")
        
        # Calcular estatísticas de tempo
        semanas_restantes = dias_para_prova // 7
        dias_extras = dias_para_prova % 7
        
        if dias_para_prova > 0:
            st.success(f"⏰ **{dias_para_prova} dias restantes**")
            if semanas_restantes > 0:
                st.info(f"📅 Equivale a {semanas_restantes} semana(s) e {dias_extras} dia(s)")
        else:
            st.error("🚨 **Prazo vencido!**")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Legenda de cores
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 🎨 Legenda de Status")
        st.markdown("""
        <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem; align-items: center;">
            <div style="background: #28a745; width: 20px; height: 20px; border-radius: 50%;"></div>
            <div>Concluído</div>
            <div style="background: #dc3545; width: 20px; height: 20px; border-radius: 50%;"></div>
            <div>Pendente</div>
            <div style="background: #ffc107; width: 20px; height: 20px; border-radius: 50%;"></div>
            <div>Em Andamento</div>
            <div style="background: #9c27b0; width: 20px; height: 20px; border-radius: 50%;"></div>
            <div>Revisão</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Dicas de estudo
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 💡 Dicas de Estudo")
        st.markdown("""
        - Priorize as matérias com menor progresso
        - Estabeleça metas diárias realistas
        - Faça revisões periódicas
        - Descanse adequadamente entre sessões
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Carregar dados
    with st.spinner("🔄 Carregando dados da planilha..."):
        df = load_data()
    
    # Modo debug
    if debug_mode and not df.empty:
        with st.expander("🔍 Painel de Debug - Dados Carregados"):
            st.markdown('<div class="debug-panel">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**📊 Estrutura do DataFrame:**")
                st.write(f"📏 Dimensões: {df.shape[0]} linhas x {df.shape[1]} colunas")
                st.write(f"📋 Colunas: {list(df.columns)}")
                st.write("**📈 Distribuição dos Dados:**")
                st.write("**Status:**")
                st.write(df['STATUS'].value_counts())
            with col2:
                st.write("**📋 Amostra dos Dados:**")
                st.dataframe(df.head(10), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")
        
        # Painel de soluções
        with st.expander("💡 Guia de Solução de Problemas", expanded=True):
            st.markdown("""
            <div class="debug-panel">
            
            ### 🔧 Possíveis soluções:
            
            **1. Verificar a planilha:**
            - ✅ Certifique-se de que existe uma aba chamada "dados"
            - ✅ Verifique se há cabeçalhos nas colunas
            - ✅ Remova colunas vazias do cabeçalho
            
            **2. Colunas obrigatórias:**
            - 📝 `Matéria` ou `Disciplina`: Nome da matéria/disciplina
            - 🏷️ `STATUS`: Deve conter "FEITO", "PENDENTE", "EM ANDAMENTO" ou "REVISÃO"
            
            **3. Formato esperado:**
            ```
            | Matéria              | Conteúdo                    | STATUS        |
            |----------------------|----------------------------|---------------|
            | LÍNGUA PORTUGUESA    | Interpretação de textos    | FEITO         |
            | RACIOCÍNIO LÓGICO    | Lógica e raciocínio        | EM ANDAMENTO  |
            ```
            
            **4. Verificar permissões:**
            - 🔐 A conta de serviço tem acesso à planilha?
            - 🆔 O ID da planilha está correto?
            - 🌐 A planilha está compartilhada com o e-mail do serviço?
            
            </div>
            """, unsafe_allow_html=True)
        return
    
    # Processar dados
    disciplinas_stats = process_data_for_charts(df)
    
    if not disciplinas_stats:
        st.warning("⚠️ Nenhum dado válido encontrado após processamento.")
        return
    
    # Métricas gerais
    total_feito, total_pendente, total_geral, percentual_geral = create_summary_metrics(disciplinas_stats)
    
    # Seção de Resumo Geral
    st.markdown('<div class="section-header">📈 Resumo Geral do Progresso</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_metric_card(
            title="Total de Itens",
            value=f"{total_geral}",
            help_text="Número total de tópicos de estudo",
            icon="📋"
        )
    
    with col2:
        display_metric_card(
            title="Itens Concluídos", 
            value=f"{total_feito}",
            delta=f"{percentual_geral:.1f}%",
            help_text="Tópicos já estudados",
            icon="✅"
        )
    
    with col3:
        display_metric_card(
            title="Itens Pendentes",
            value=f"{total_pendente}",
            delta=f"{100-percentual_geral:.1f}%",
            help_text="Tópicos ainda não estudados",
            icon="⏳"
        )
    
    with col4:
        display_metric_card(
            title="Progresso Geral",
            value=f"{percentual_geral:.1f}%",
            help_text="Percentual geral de conclusão",
            icon="🎯"
        )
    
    # Seção de Progresso por Disciplina
    st.markdown('<div class="section-header">📊 Análise por Disciplina</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">📈 Ranking de Progresso por Disciplina</div>', unsafe_allow_html=True)
        progress_chart = create_progress_bar_chart(disciplinas_stats)
        st.altair_chart(progress_chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">📋 Detalhamento por Disciplina</div>', unsafe_allow_html=True)
        for i, (disciplina, stats) in enumerate(disciplinas_stats.items()):
            progress_color = "#28a745" if stats['percentual_feito'] > 75 else "#ffc107" if stats['percentual_feito'] > 40 else "#dc3545"
            
            with st.expander(f"📚 **{disciplina}** ({stats['percentual_feito']:.1f}%)", expanded=i<2):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("✅ Concluídos", stats['feito'])
                    st.metric("⏳ Pendentes", stats['pendente'])
                with col_b:
                    st.metric("🚧 Em Andamento", stats.get('em_andamento', 0))
                    st.metric("📝 Revisão", stats.get('revisao', 0))
                
                # Barra de progresso
                progress_width = int(stats['percentual_feito'])
                st.markdown(f"""
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress_width}%; background: {progress_color};"></div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção de Gráficos de Rosca
    st.markdown('<div class="section-header">🍩 Visualização Detalhada por Disciplina</div>', unsafe_allow_html=True)
    
    # Organizar em colunas (máximo 3 por linha)
    disciplinas = list(disciplinas_stats.keys())
    
    for i in range(0, len(disciplinas), 3):
        cols = st.columns(3)
        
        for j, col in enumerate(cols):
            if i + j < len(disciplinas):
                disciplina = disciplinas[i + j]
                stats = disciplinas_stats[disciplina]
                
                with col:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.markdown(f'<div class="chart-title">📚 {disciplina}</div>', unsafe_allow_html=True)
                    
                    donut_chart = create_donut_chart(
                        stats['feito'], 
                        stats['pendente'],
                        stats.get('em_andamento', 0),
                        stats.get('revisao', 0),
                        disciplina
                    )
                    
                    st.altair_chart(donut_chart, use_container_width=True)
                    
                    progress_color = "#28a745" if stats['percentual_feito'] > 75 else "#ffc107" if stats['percentual_feito'] > 40 else "#dc3545"
                    
                    st.markdown(f"""
                    <div class="progress-info">
                        <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem;">
                            ✅ <strong>{stats['feito']}</strong> de <strong>{stats['total']}</strong> itens concluídos
                        </div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: {progress_color};">
                            🎯 {stats['percentual_feito']:.1f}% de progresso
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # Rodapé com informações
    current_time = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    semanas_restantes = dias_para_prova // 7
    dias_extras = dias_para_prova % 7
    tempo_restante = f"{semanas_restantes} semanas e {dias_extras} dias" if semanas_restantes > 0 else f"{dias_para_prova} dias"
    
    st.markdown(f"""
    <div class="dashboard-footer">
        <h3 style="text-align: center; margin-bottom: 1.5rem;">💡 Estratégias para Sucesso nos Estudos</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin: 1.5rem 0;">
            <div style="background: rgba(255,255,255,0.1); padding: 1.2rem; border-radius: 12px; backdrop-filter: blur(5px);">
                <div style="font-size: 1.3rem; margin-bottom: 0.8rem; display: flex; align-items: center;">📊</div>
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">Acompanhe regularmente</div>
                <div>Use este dashboard diariamente para monitorar seu progresso</div>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 1.2rem; border-radius: 12px; backdrop-filter: blur(5px);">
                <div style="font-size: 1.3rem; margin-bottom: 0.8rem; display: flex; align-items: center;">🎯</div>
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">Foque no vermelho</div>
                <div>Priorize as disciplinas com menor percentual de conclusão</div>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 1.2rem; border-radius: 12px; backdrop-filter: blur(5px);">
                <div style="font-size: 1.3rem; margin-bottom: 0.8rem; display: flex; align-items: center;">✅</div>
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">Celebre o verde</div>
                <div>Reconheça seu progresso nas disciplinas já avançadas</div>
            </div>
        </div>
        <hr style="border: 1px solid rgba(255,255,255,0.3); margin: 1.5rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; font-size: 0.95rem;">
            <div>
                🔄 Última atualização: {current_time}
            </div>
            <div>
                📈 {len(disciplinas_stats)} disciplinas | {icone_prazo} {tempo_restante} para a prova
            </div>
            <div>
                📚 Dashboard de Estudos v2.5
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
