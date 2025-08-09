# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import time
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import warnings
import traceback
import locale
# Removido plotly - usando apenas Altair

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
CACHE_TTL_HOURS = 1
DATA_REFRESH_MINUTES = 5

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
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
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
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0.5rem 0 0 0;
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
    
    /* Alert boxes */
    .alert-info {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .metric-value {
            font-size: 2rem;
        }
        
        .metric-card {
            height: auto;
            min-height: 100px;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Funções de Utilidade ---
def show_error(message, details=None):
    """Exibe mensagem de erro com detalhes opcionais"""
    st.error(f"❌ {message}")
    if details and st.sidebar.checkbox("🔍 Ver detalhes do erro"):
        st.sidebar.code(details)

def show_loading(message="Carregando..."):
    """Exibe spinner de carregamento"""
    return st.spinner(f"🔄 {message}")

# --- Funções de Autenticação e Carregamento de Dados ---
@st.cache_resource(ttl=timedelta(hours=CACHE_TTL_HOURS))
def get_gspread_client():
    """Inicializa e retorna cliente do Google Sheets"""
    try:
        # Verificar se as credenciais existem
        if "google_credentials" not in st.secrets:
            raise ValueError("Credenciais do Google Cloud não encontradas no secrets.toml")
        
        creds_info = {
            "type": st.secrets["google_credentials"]["type"],
            "project_id": st.secrets["google_credentials"]["project_id"],
            "private_key_id": st.secrets["google_credentials"]["private_key_id"],
            "private_key": st.secrets["google_credentials"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["google_credentials"]["client_email"],
            "client_id": st.secrets["google_credentials"]["client_id"],
            "auth_uri": st.secrets["google_credentials"]["auth_uri"],
            "token_uri": st.secrets["google_credentials"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_credentials"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["google_credentials"]["client_x509_cert_url"],
            "universe_domain": st.secrets["google_credentials"]["universe_domain"]
        }
        
        creds = Credentials.from_service_account_info(creds_info)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        show_error("Erro ao autenticar com o Google Sheets", str(e))
        st.info("💡 Verifique se as credenciais estão configuradas corretamente no secrets.toml")
        st.stop()

@st.cache_data(ttl=timedelta(minutes=DATA_REFRESH_MINUTES))
def load_data(spreadsheet_id, worksheet_name):
    """Carrega dados da planilha Google Sheets"""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_id(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        
        if not data:
            raise ValueError("Planilha está vazia ou não contém dados válidos")
        
        df = pd.DataFrame(data)
        return df
    except SpreadsheetNotFound:
        show_error(f"Planilha com ID '{spreadsheet_id}' não encontrada")
        st.info("💡 Verifique se o ID da planilha está correto e se a conta de serviço tem acesso.")
        st.stop()
    except APIError as e:
        show_error("Erro de API do Google Sheets", str(e))
        st.info("💡 Verifique se você não excedeu o limite de requisições da API.")
        st.stop()
    except Exception as e:
        show_error("Erro ao carregar dados da planilha", str(e))
        st.stop()

def process_data(df):
    """Processa e valida os dados carregados"""
    required_columns = ['Disciplinas', 'Feito', 'Pendente']
    
    # Verificar se as colunas existem
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        show_error(f"Colunas não encontradas: {', '.join(missing_columns)}")
        st.info("📋 Colunas disponíveis na planilha:")
        st.write(df.columns.tolist())
        st.stop()

    # Converter colunas para numérico
    df['Feito'] = pd.to_numeric(df['Feito'], errors='coerce').fillna(0)
    df['Pendente'] = pd.to_numeric(df['Pendente'], errors='coerce').fillna(0)
    df['Total'] = df['Feito'] + df['Pendente']

    # Adicionar percentual de progresso por disciplina
    df['Progresso_Pct'] = df.apply(lambda row: 
        (row['Feito'] / row['Total'] * 100) if row['Total'] > 0 else 0, axis=1)

    # Adicionar status geral
    def get_status(row):
        if row['Total'] == 0:
            return "Não Iniciado"
        elif row['Feito'] == row['Total']:
            return "Concluído"
        elif row['Feito'] > 0 and row['Pendente'] > 0:
            return "Em Andamento"
        elif row['Pendente'] > 0 and row['Feito'] == 0:
            return "Não Iniciado"
        else:
            return "Em Andamento"

    df['Status_Geral'] = df.apply(get_status, axis=1)
    
    return df

def create_metrics_html(value, label, color="#2c3e50", border_color="#667eea"):
    """Cria HTML para cards de métricas"""
    return f"""
    <div class="metric-card" style="border-left-color: {border_color};">
        <p class="metric-value" style="color: {color};">{value}</p>
        <p class="metric-label">{label}</p>
    </div>
    """

def format_status_cell(status):
    """Formata células de status com cores"""
    status_colors = {
        "Concluído": "#28a745",
        "Em Andamento": "#007bff", 
        "Não Iniciado": "#dc3545",
        "Pendente": "#ffc107"
    }
    color = status_colors.get(status, "#6c757d")
    return f'<span style="color: {color}; font-weight: bold;">●</span> {status}'

# --- Início da Aplicação ---
def main():
    # Header Principal
    st.markdown("""
    <div class="main-header">
        <h1>📚 Dashboard de Disciplinas</h1>
        <p>Acompanhe o progresso dos seus estudos em tempo real</p>
    </div>
    """, unsafe_allow_html=True)

    # Carregar Dados
    with show_loading("Carregando dados da planilha..."):
        df = load_data(SPREADSHEET_ID, WORKSHEET_NAME)

    if df is not None and not df.empty:
        st.success("✅ Dados carregados com sucesso!")
        
        # Mostrar timestamp da última atualização
        current_time = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
        st.info(f"🕒 Última atualização: {current_time}")
    else:
        st.warning("⚠️ Não foi possível carregar os dados ou a planilha está vazia.")
        st.stop()

    # Processar dados
    try:
        df = process_data(df)
    except Exception as e:
        show_error("Erro ao processar os dados", str(e))
        st.stop()

    # --- Métricas Principais ---
    st.markdown("### 📊 Visão Geral")
    
    total_disciplinas = len(df['Disciplinas'].unique())
    total_feito = int(df['Feito'].sum())
    total_pendente = int(df['Pendente'].sum())
    total_conteudos = total_feito + total_pendente
    progresso_geral = (total_feito / total_conteudos * 100) if total_conteudos > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(create_metrics_html(
            total_disciplinas, "Disciplinas", "#667eea", "#667eea"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(create_metrics_html(
            total_feito, "Conteúdos Concluídos", "#28a745", "#28a745"
        ), unsafe_allow_html=True)

    with col3:
        st.markdown(create_metrics_html(
            total_pendente, "Conteúdos Pendentes", "#ffc107", "#ffc107"
        ), unsafe_allow_html=True)

    with col4:
        st.markdown(create_metrics_html(
            f"{progresso_geral:.1f}%", "Progresso Geral", "#667eea", "#667eea"
        ), unsafe_allow_html=True)

    # --- Gráficos de Análise ---
    st.markdown("""
    <div class="section-header">
        <h2>📈 Análise Visual dos Dados</h2>
    </div>
    """, unsafe_allow_html=True)

    # Gráficos lado a lado
    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de Pizza - Status Geral
        st.subheader("🔄 Distribuição Geral")
        
        if total_conteudos > 0:
            # Dados para o gráfico de status geral
            status_data = pd.DataFrame({
                'Status': ['Concluído', 'Pendente'],
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
                    scale=alt.Scale(
                        domain=['Concluído', 'Pendente'],
                        range=["#28a745", "#ffc107"]
                    )
                ),
                tooltip=[
                    alt.Tooltip("Status", title="Status"),
                    alt.Tooltip("Quantidade", title="Quantidade", format=".0f")
                ]
            ).properties(
                title=alt.TitleParams(
                    text="Status dos Conteúdos",
                    fontSize=16,
                    fontWeight='bold',
                    anchor='start',
                    color='#2c3e50'
                ),
                width=300,
                height=300
            )
            
            text_status = chart_status.mark_text(
                radius=140,
                fontSize=14,
                fontWeight='bold',
                color='black'
            ).encode(
                text=alt.Text("Quantidade", format=".0f")
            )
            
            st.altair_chart(chart_status + text_status, use_container_width=True)

    with col2:
        # Gráfico de Barras - Por Disciplina
        st.subheader("📚 Por Disciplina")
        
        df_chart = df.groupby('Disciplinas')[['Feito', 'Pendente']].sum().reset_index()
        df_melted = df_chart.melt(
            id_vars=['Disciplinas'], 
            value_vars=['Feito', 'Pendente'],
            var_name='Status', 
            value_name='Quantidade'
        )
        
        # Renomear para melhor exibição
        df_melted['Status'] = df_melted['Status'].replace({'Feito': 'Concluído', 'Pendente': 'Pendente'})
        
        chart_barras = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('Disciplinas:N', title='Disciplinas', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Quantidade:Q', title='Quantidade de Conteúdos'),
            color=alt.Color(
                'Status:N',
                scale=alt.Scale(
                    domain=['Concluído', 'Pendente'],
                    range=["#28a745", "#ffc107"]
                ),
                title="Status"
            ),
            tooltip=[
                alt.Tooltip('Disciplinas:N', title='Disciplina'), 
                alt.Tooltip('Status:N', title='Status'), 
                alt.Tooltip('Quantidade:Q', title='Quantidade')
            ]
        ).properties(
            title=alt.TitleParams(
                text="Conteúdos por Disciplina",
                fontSize=16,
                fontWeight='bold',
                anchor='start',
                color='#2c3e50'
            ),
            width=400,
            height=300
        )
        
        st.altair_chart(chart_barras, use_container_width=True)

    # Gráfico de Barras Horizontais - Progresso Geral
    st.subheader("📊 Ranking de Progresso por Disciplina")
    
    # Calcular progresso por disciplina para o gráfico de barras
    df_progress_bar = df.groupby('Disciplinas').agg({
        'Feito': 'sum',
        'Pendente': 'sum',
        'Total': 'sum'
    }).reset_index()
    
    df_progress_bar['Progresso_Pct'] = (df_progress_bar['Feito'] / df_progress_bar['Total'] * 100).round(1)
    df_progress_bar = df_progress_bar.sort_values('Progresso_Pct', ascending=True)
    
    # Criar escala de cores baseada no progresso
    def get_color_for_progress(progress):
        if progress >= 75:
            return "#198754"  # Verde escuro
        elif progress >= 50:
            return "#28a745"  # Verde
        elif progress >= 25:
            return "#ffc107"  # Amarelo
        else:
            return "#dc3545"  # Vermelho
    
    df_progress_bar['Cor'] = df_progress_bar['Progresso_Pct'].apply(get_color_for_progress)
    
    chart_progress = alt.Chart(df_progress_bar).mark_bar().encode(
        x=alt.X('Progresso_Pct:Q', title='Progresso (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('Disciplinas:N', title='Disciplinas', sort='-x'),
        color=alt.Color(
            'Progresso_Pct:Q',
            scale=alt.Scale(
                domain=[0, 25, 50, 75, 100],
                range=["#dc3545", "#ffc107", "#28a745", "#198754", "#155724"]
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip('Disciplinas:N', title='Disciplina'),
            alt.Tooltip('Progresso_Pct:Q', title='Progresso (%)', format='.1f'),
            alt.Tooltip('Feito:Q', title='Concluído'),
            alt.Tooltip('Pendente:Q', title='Pendente'),
            alt.Tooltip('Total:Q', title='Total')
        ]
    ).properties(
        title=alt.TitleParams(
            text="Percentual de Progresso por Disciplina",
            fontSize=16,
            fontWeight='bold',
            anchor='start',
            color='#2c3e50'
        ),
        width=700,
        height=max(300, len(df_progress_bar) * 40)
    )
    
    # Adicionar texto com os valores nas barras
    text_progress = alt.Chart(df_progress_bar).mark_text(
        align='left',
        dx=5,
        fontSize=11,
        fontWeight='bold',
        color='white'
    ).encode(
        x=alt.X('Progresso_Pct:Q'),
        y=alt.Y('Disciplinas:N', sort='-x'),
        text=alt.Text('Progresso_Pct:Q', format='.1f')
    )
    
    st.altair_chart(chart_progress + text_progress, use_container_width=True)
    st.markdown("""
    <div class="section-header">
        <h2>🍩 Progresso Individual por Disciplina</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Calcular progresso por disciplina
    df_progress = df.groupby('Disciplinas').agg({
        'Feito': 'sum',
        'Pendente': 'sum',
        'Total': 'sum'
    }).reset_index()
    
    df_progress['Progresso_Pct'] = (df_progress['Feito'] / df_progress['Total'] * 100).round(1)
    df_progress = df_progress.sort_values('Progresso_Pct', ascending=False)
    
    # Definir quantos gráficos por linha baseado no número de disciplinas
    num_disciplinas = len(df_progress)
    cols_per_row = 3 if num_disciplinas > 6 else 2 if num_disciplinas > 2 else 1
    
    # Criar gráficos de rosca para cada disciplina
    for i in range(0, len(df_progress), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j in range(cols_per_row):
            if i + j < len(df_progress):
                row = df_progress.iloc[i + j]
                disciplina = row['Disciplinas']
                feito = int(row['Feito'])
                pendente = int(row['Pendente'])
                total = int(row['Total'])
                progresso_pct = row['Progresso_Pct']
                
                with cols[j]:
                    # Preparar dados para o gráfico de rosca
                    if total > 0:
                        chart_data = pd.DataFrame({
                            'Status': ['Feito', 'Pendente'],
                            'Quantidade': [feito, pendente],
                            'Percentual': [progresso_pct, 100 - progresso_pct]
                        })
                        
                        # Definir cor baseada no progresso
                        if progresso_pct == 100:
                            color_scheme = ['#28a745', '#e9ecef']  # Verde e cinza claro
                        elif progresso_pct >= 75:
                            color_scheme = ['#198754', '#ffc107']  # Verde escuro e amarelo
                        elif progresso_pct >= 50:
                            color_scheme = ['#28a745', '#ffc107']  # Verde e amarelo
                        elif progresso_pct >= 25:
                            color_scheme = ['#ffc107', '#dc3545']  # Amarelo e vermelho
                        else:
                            color_scheme = ['#6c757d', '#dc3545']  # Cinza e vermelho
                        
                        # Criar gráfico de rosca
                        chart = alt.Chart(chart_data).mark_arc(
                            outerRadius=80,
                            innerRadius=45,
                            stroke='white',
                            strokeWidth=2
                        ).encode(
                            theta=alt.Theta('Quantidade:Q'),
                            color=alt.Color(
                                'Status:N',
                                scale=alt.Scale(
                                    domain=['Feito', 'Pendente'],
                                    range=color_scheme
                                ),
                                legend=None
                            ),
                            tooltip=[
                                alt.Tooltip('Status:N', title='Status'),
                                alt.Tooltip('Quantidade:Q', title='Quantidade'),
                                alt.Tooltip('Percentual:Q', title='Percentual (%)', format='.1f')
                            ]
                        ).properties(
                            width=180,
                            height=180,
                            title=alt.TitleParams(
                                text=[disciplina, f"{progresso_pct:.1f}% concluído"],
                                fontSize=12,
                                fontWeight='bold',
                                anchor='start',
                                color='#2c3e50'
                            )
                        ).resolve_scale(
                            color='independent'
                        )
                        
                        # Adicionar texto no centro com o percentual
                        text_chart = alt.Chart(pd.DataFrame({'x': [0], 'y': [0], 'text': [f"{progresso_pct:.0f}%"]})).mark_text(
                            fontSize=18,
                            fontWeight='bold',
                            color='#2c3e50'
                        ).encode(
                            x=alt.X('x:Q', scale=alt.Scale(domain=[-1, 1])),
                            y=alt.Y('y:Q', scale=alt.Scale(domain=[-1, 1])),
                            text='text:N'
                        ).properties(
                            width=180,
                            height=180
                        )
                        
                        # Combinar os gráficos
                        combined_chart = (chart + text_chart).resolve_scale(
                            x='shared',
                            y='shared'
                        )
                        
                        st.altair_chart(combined_chart, use_container_width=False)
                        
                        # Adicionar informações detalhadas abaixo do gráfico
                        st.markdown(f"""
                        <div style="text-align: center; margin-top: -10px; padding: 10px; 
                                    background-color: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
                            <small style="color: #6c757d;">
                                <strong>Total:</strong> {total} • 
                                <span style="color: #28a745;"><strong>Feito:</strong> {feito}</span> • 
                                <span style="color: #ffc107;"><strong>Pendente:</strong> {pendente}</span>
                            </small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Caso não tenha dados
                        st.markdown(f"""
                        <div style="text-align: center; padding: 40px; 
                                    background-color: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #6c757d; margin-bottom: 10px;">{disciplina}</h4>
                            <p style="color: #6c757d; font-style: italic;">Nenhum conteúdo cadastrado</p>
                        </div>
                        """, unsafe_allow_html=True)
    
    # Resumo estatístico dos gráficos
    st.markdown("### 📈 Resumo Estatístico")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        disciplinas_completas = len(df_progress[df_progress['Progresso_Pct'] == 100])
        st.metric("🏆 Disciplinas Completas", disciplinas_completas)
    
    with col2:
        disciplinas_andamento = len(df_progress[(df_progress['Progresso_Pct'] > 0) & (df_progress['Progresso_Pct'] < 100)])
        st.metric("🔄 Em Andamento", disciplinas_andamento)
    
    with col3:
        disciplinas_nao_iniciadas = len(df_progress[df_progress['Progresso_Pct'] == 0])
        st.metric("⭕ Não Iniciadas", disciplinas_nao_iniciadas)
    
    with col4:
        progresso_medio = df_progress['Progresso_Pct'].mean()
        st.metric("📊 Progresso Médio", f"{progresso_medio:.1f}%")

    # --- Filtros e Tabela ---
    st.markdown("""
    <div class="section-header">
        <h2>🔍 Dados Detalhados</h2>
    </div>
    """, unsafe_allow_html=True)

    # Filtros
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        disciplinas_options = ["Todas"] + sorted(df["Disciplinas"].unique().tolist())
        selected_disciplina = st.selectbox("🎯 Disciplina:", disciplinas_options)

    with col2:
        status_options = ["Todos"] + sorted(df["Status_Geral"].unique().tolist())
        selected_status = st.selectbox("📊 Status:", status_options)

    with col3:
        min_progresso = st.slider("📈 Progresso mínimo (%):", 0, 100, 0)

    with col4:
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Aplicar filtros
    filtered_df = df.copy()
    
    if selected_disciplina != "Todas":
        filtered_df = filtered_df[filtered_df["Disciplinas"] == selected_disciplina]
    
    if selected_status != "Todos":
        filtered_df = filtered_df[filtered_df["Status_Geral"] == selected_status]
    
    filtered_df = filtered_df[filtered_df["Progresso_Pct"] >= min_progresso]

    # Mostrar informações dos filtros
    if selected_disciplina != "Todas" or selected_status != "Todos" or min_progresso > 0:
        filtros_ativos = []
        if selected_disciplina != "Todas":
            filtros_ativos.append(f"Disciplina: {selected_disciplina}")
        if selected_status != "Todos":
            filtros_ativos.append(f"Status: {selected_status}")
        if min_progresso > 0:
            filtros_ativos.append(f"Progresso ≥ {min_progresso}%")
        
        st.info(f"🔍 Filtros ativos: {' | '.join(filtros_ativos)} | Registros: {len(filtered_df)}")

    # Preparar dados para exibição
    if len(filtered_df) > 0:
        display_columns = ["Disciplinas", "Feito", "Pendente", "Total", "Progresso_Pct", "Status_Geral"]
        
        # Buscar colunas de conteúdo
        content_columns = [col for col in df.columns 
                          if any(keyword in col.lower() for keyword in ['conteudo', 'conteúdo', 'topico', 'tópico', 'assunto'])]
        
        if content_columns:
            display_columns = ["Disciplinas"] + content_columns[:3] + ["Feito", "Pendente", "Total", "Progresso_Pct", "Status_Geral"]
        
        display_df = filtered_df[display_columns].copy()
        display_df['Progresso_Pct'] = display_df['Progresso_Pct'].round(1).astype(str) + '%'
        
        # Renomear colunas para exibição
        column_names = {
            'Progresso_Pct': 'Progresso (%)',
            'Status_Geral': 'Status'
        }
        display_df = display_df.rename(columns=column_names)
        
        # Exibir tabela
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400,
            column_config={
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Status atual da disciplina"
                ),
                "Progresso (%)": st.column_config.TextColumn(
                    "Progresso (%)",
                    help="Percentual de conclusão"
                )
            }
        )

        # Resumo dos dados filtrados
        if len(filtered_df) > 0:
            st.markdown("### 📈 Resumo dos Dados Filtrados")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                feito_filtrado = int(filtered_df['Feito'].sum())
                st.metric("✅ Total Concluído", feito_filtrado)
            
            with col2:
                pendente_filtrado = int(filtered_df['Pendente'].sum())
                st.metric("⏳ Total Pendente", pendente_filtrado)
            
            with col3:
                total_filtrado = feito_filtrado + pendente_filtrado
                st.metric("📚 Total de Conteúdos", total_filtrado)
            
            with col4:
                progresso_filtrado = (feito_filtrado / total_filtrado * 100) if total_filtrado > 0 else 0
                st.metric("📊 Progresso Médio", f"{progresso_filtrado:.1f}%")
    else:
        st.warning("⚠️ Nenhum registro encontrado com os filtros aplicados.")

    # --- Sidebar com Informações ---
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        
        # Informações do sistema
        st.markdown("#### 📊 Informações dos Dados")
        st.write(f"**Total de registros:** {len(df)}")
        st.write(f"**Disciplinas únicas:** {len(df['Disciplinas'].unique())}")
        st.write(f"**Última atualização:** {current_time}")
        
        st.markdown("---")
        
        # Opções de visualização
        st.markdown("#### 🎨 Opções de Visualização")
        show_empty_disciplines = st.checkbox("Mostrar disciplinas vazias", value=False)
        
        if show_empty_disciplines:
            st.info("Incluindo disciplinas sem conteúdo nos gráficos")
        
        # Estatísticas rápidas
        st.markdown("#### 📈 Estatísticas Rápidas")
        disciplina_mais_avancada = df.loc[df['Progresso_Pct'].idxmax(), 'Disciplinas'] if len(df) > 0 else "N/A"
        disciplina_menos_avancada = df.loc[df['Progresso_Pct'].idxmin(), 'Disciplinas'] if len(df) > 0 else "N/A"
        
        st.write(f"**🏆 Mais avançada:** {disciplina_mais_avancada}")
        st.write(f"**🔄 Menos avançada:** {disciplina_menos_avancada}")
        
        # Modo debug
        if st.checkbox("🔧 Modo Debug"):
            st.markdown("#### 🔍 Debug Info")
            st.write("**Colunas disponíveis:**")
            st.code(", ".join(df.columns.tolist()))
            st.write("**Tipos de dados:**")
            st.code(str(df.dtypes))

    # --- Footer ---
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; padding: 2rem;">
        <p>📚 Dashboard de Disciplinas | Desenvolvido com ❤️ usando Streamlit e Altair</p>
        <p>🔄 Dados sincronizados automaticamente com Google Sheets</p>
    </div>
    """, unsafe_allow_html=True)

# --- Executar Aplicação ---
if __name__ == "__main__":
    main()
