# app.py
# Este é o arquivo único para o dashboard, usando apenas a aba 'Dados'

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import numpy as np

# Tentar importar gspread, mas funcionar sem ele para teste local
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    
# --- Configurações ---
# ATENÇÃO: SUBSTITUA COM SEUS DADOS REAIS
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM' # ID da sua planilha
WORKSHEET_NAME_DADOS = 'Dados' # Nome da aba da análise de conteúdo
CONCURSO_DATE = datetime(2025, 9, 28) # Data do concurso

# Dados do edital (mantidos para calcular o progresso ponderado)
ED_DATA = {
    'Matéria': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO'],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3]
}

# --- Funções de Autenticação e Leitura de Dados ---
@st.cache_resource
def get_google_auth():
    """Autenticação com Google Sheets."""
    if not GSPREAD_AVAILABLE:
        return None
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro na autenticação. Verifique seu `secrets.toml`: {e}")
        return None

@st.cache_data(ttl=600)
def read_dados_from_sheets():
    """Lê dados da aba 'Dados' do Google Sheets ou usa dados de exemplo."""
    if not GSPREAD_AVAILABLE or not st.secrets.get("google_credentials"):
        st.info("⚠️ Dados de exemplo estão sendo usados. Para usar seus dados, configure as credenciais do Google Sheets.")
        
        # Dados de exemplo simulando a aba 'Dados'
        conteudos_do_edital = {
            'LÍNGUA PORTUGUESA': ['Gramática', 'Interpretação', 'Concordância Verbal', 'Crase'],
            'RLM': ['Lógica de proposições', 'Argumentação', 'Diagramas Lógicos'],
            'INFORMÁTICA': ['Windows', 'Excel', 'Word'],
            'LEGISLAÇÃO': ['Lei 8.112', 'Lei 8.429'],
            'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO': ['Administração Geral', 'Gestão de Pessoas', 'Gestão Financeira']
        }
        sample_data = []
        for materia, conteudos in conteudos_do_edital.items():
            for conteudo in conteudos:
                status = 'Feito' if np.random.rand() > 0.5 else 'Pendente'
                sample_data.append({'Matéria': materia, 'Conteúdo': conteudo, 'Status': status})
        
        return pd.DataFrame(sample_data)

    try:
        gc = get_google_auth()
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME_DADOS)
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        return df
    except Exception as e:
        st.error(f"Erro ao ler dados da aba '{WORKSHEET_NAME_DADOS}'. Verifique o ID e o nome da aba.")
        st.exception(e)
        return pd.DataFrame()

# --- Funções de Processamento de Dados ---
def calculate_weighted_metrics(df_dados):
    """Calcula métricas de progresso ponderado com base no edital."""
    df_edital = pd.DataFrame(ED_DATA)
    
    # Verifica se as colunas essenciais existem
    if 'Matéria' not in df_dados.columns or 'Status' not in df_dados.columns:
        st.error("Erro: As colunas 'Matéria' e 'Status' não foram encontradas na planilha. Verifique o cabeçalho.")
        return pd.DataFrame(), 0.0

    df_dados['Feito'] = df_dados['Status'].apply(lambda x: 1 if isinstance(x, str) and x.strip().lower() == 'feito' else 0)
    df_dados['Pendente'] = df_dados['Status'].apply(lambda x: 1 if isinstance(x, str) and x.strip().lower() == 'pendente' else 0)
    
    df_progresso_summary = df_dados.groupby('Matéria').agg(
        Conteudos_Feitos=('Feito', 'sum'),
        Conteudos_Pendentes=('Pendente', 'sum')
    ).reset_index()
    
    df_final = pd.merge(df_edital, df_progresso_summary, on='Matéria', how='left').fillna(0)
    
    # Calcula a pontuação ponderada
    df_final['Pontos_por_Conteudo'] = np.where(df_final['Total_Conteudos'] > 0, df_final['Peso'] / df_final['Total_Conteudos'], 0)
    df_final['Pontos_Concluidos'] = df_final['Conteudos_Feitos'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_Pendentes'] = df_final['Total_Conteudos'] * df_final['Pontos_por_Conteudo'] - df_final['Pontos_Concluidos']
    df_final['Progresso_Ponderado'] = np.where(df_final['Peso'] > 0, round(df_final['Pontos_Concluidos'] / df_final['Peso'] * 100, 1), 0)
    
    total_pontos = df_final['Peso'].sum()
    total_pontos_concluidos = df_final['Pontos_Concluidos'].sum()
    progresso_ponderado_geral = round((total_pontos_concluidos / total_pontos) * 100, 1) if total_pontos > 0 else 0
    
    return df_final, progresso_ponderado_geral

# --- Funções de Design e Gráficos ---
def apply_light_theme_css():
    """Aplica CSS para tema diurno e clean."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        html, body, .stApp { font-family: 'Poppins', sans-serif; background-color: #f0f2f6; color: #1c1c1c; }
        h1, h2, h3 { color: #1c1c1c; }
        .stMetric > div > div:first-child { font-weight: 600; color: #666; }
        .stMetric > div > div:nth-child(2) { font-size: 2.5rem; font-weight: 700; color: #007bff; }
        .countdown { font-size: 1.2rem; font-weight: 600; color: #007bff; }
        .st-emotion-cache-1r6ilae { border-bottom: 1px solid #e0e0e0; margin-bottom: 1.5rem; }
        .stExpander { border-radius: 10px; border: 1px solid #e0e0e0; background-color: #ffffff; padding: 10px; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

def create_altair_donut_chart(data_row):
    """Cria um gráfico de rosca com contorno branco e tema claro."""
    df_chart = pd.DataFrame({'Status': ['Concluído', 'Pendente'], 'Pontos': [data_row['Pontos_Concluidos'], data_row['Pontos_Pendentes']]})
    base = alt.Chart(df_chart).encode(theta=alt.Theta("Pontos:Q", stack=True))
    pie = base.mark_arc(outerRadius=80, innerRadius=50, stroke="#ffffff", strokeWidth=2.5).encode(
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Concluido', 'Pendente'], range=['#007bff', '#ff4b4b'])),
        order=alt.Order("Pontos", sort="descending"),
        tooltip=["Status", "Pontos:Q"]
    )
    text_progresso = alt.Chart(pd.DataFrame({'text': [f"{data_row['Progresso_Ponderado']}%"]})).mark_text(
        align='center', baseline='middle', fontSize=25, fontWeight='bold', color='#1c1c1c'
    ).encode(text=alt.Text('text:N'))
    return (pie + text_progresso).properties(
        title=data_row['Matéria']
    ).resolve_scale(color='independent')

def create_altair_bubble_chart(df_summary):
    """Cria um gráfico de bolhas para priorização de estudo."""
    chart = alt.Chart(df_summary).mark_circle().encode(
        x=alt.X('Total_Conteudos:Q', title='Total de Conteúdos', axis=alt.Axis(grid=True)),
        y=alt.Y('Peso:Q', title='Peso da Disciplina'),
        size=alt.Size('Porcentagem_Pontos:Q', title='Pontuação Total (%)', scale=alt.Scale(range=[100, 1000])),
        color=alt.Color('Matéria:N', legend=None),
        tooltip=['Matéria', 'Total_Conteudos', 'Peso', 'Porcentagem_Pontos:Q']
    ).properties(title='Prioridade de Estudo (Conteúdos x Peso)').interactive()
    return chart

def create_altair_bar_chart_conteudo(df_summary):
    """Cria um gráfico de barras para o progresso de conteúdos."""
    df_melted = df_summary.melt('Matéria', var_name='Status', value_name='Conteudos', value_vars=['Conteudos_Feitos', 'Conteudos_Pendentes'])
    chart = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X('Conteudos:Q', title='Conteúdos'),
        y=alt.Y('Matéria:N', sort='-x', title='Disciplina'),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Conteudos_Feitos', 'Conteudos_Pendentes'], range=['#007bff', '#ff4b4b']), legend=alt.Legend(title="Status")),
        tooltip=['Matéria', 'Status', 'Conteudos']
    ).properties(title="Conteúdos Concluídos por Disciplina")
    return chart

def create_altair_bar_chart_conteudo_detalhado(df_summary):
    """Cria um gráfico de barras detalhado para a segunda aba."""
    df_melted = df_summary.melt(
        'Matéria', 
        var_name='Status', 
        value_name='Count'
    )
    
    bar_chart = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X('Count:Q', title='Número de Conteúdos'),
        y=alt.Y('Matéria:N', sort='-x', title='Disciplina'),
        color=alt.Color('Status:N', 
                        scale=alt.Scale(domain=['Feito', 'Pendente'], range=['#007bff', '#ff4b4b']),
                        legend=alt.Legend(title="Status")),
        tooltip=['Matéria', 'Status', 'Count']
    ).properties(
        title="Distribuição de Conteúdos por Matéria"
    )
    st.altair_chart(bar_chart, use_container_width=True)


# --- Main App ---
st.set_page_config(page_title="Dashboard TAE UFG", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
apply_light_theme_css()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🎯 Configurações")
    st.markdown("---")
    st.markdown("### 🔄 Atualização")
    if st.button("Atualizar Dados", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- HEADER ---
dias_restantes = (CONCURSO_DATE - datetime.now()).days
status_concurso = f"{dias_restantes} dias restantes" if dias_restantes >= 0 else "Concurso realizado"
st.markdown(f"""
    <h1 style='text-align: center;'>📊 DASHBOARD TAE UFG</h1>
    <p style='text-align: center; font-size: 1.2rem;'>Progresso do Edital • <span class='countdown'>{status_concurso}</span></p>
    <hr style='border-top: 1px solid #e0e0e0;'>
""", unsafe_allow_html=True)


# --- Conteúdo Principal ---
st.subheader("Dashboard de Progresso Geral")
df_dados = read_dados_from_sheets()

if not df_dados.empty:
    df_final, progresso_ponderado_geral = calculate_weighted_metrics(df_dados)
    
    st.markdown("#### Métricas de Progresso")
    
    col1, col2, col3 = st.columns(3)
    total_conteudos_feito = df_dados[df_dados['Status'].str.lower().str.strip() == 'feito'].shape[0]
    total_conteudos_pendente = df_dados[df_dados['Status'].str.lower().str.strip() == 'pendente'].shape[0]
    
    with col1: st.metric(label="✅ Progresso Ponderado Geral", value=f"{progresso_ponderado_geral}%")
    with col2: st.metric(label="📚 Conteúdos Concluídos", value=f"{int(total_conteudos_feito)}")
    with col3: st.metric(label="⏳ Conteúdos Pendentes", value=f"{int(total_conteudos_pendente)}")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Filtro de disciplinas
    disciplinas_disponiveis = [m for m in ED_DATA['Matéria']]
    disciplinas_selecionadas = st.multiselect("Selecione as disciplinas para os gráficos:", disciplinas_disponiveis, default=disciplinas_disponiveis)
    df_final_filtered = df_final[df_final['Matéria'].isin(disciplinas_selecionadas)]

    with st.container():
        st.markdown("#### Progresso por Disciplina (Ponderado)")
        if not df_final_filtered.empty:
            cols_charts = st.columns(len(df_final_filtered))
            for idx, (_, row) in enumerate(df_final_filtered.iterrows()):
                with cols_charts[idx % len(cols_charts)]:
                    chart = create_altair_donut_chart(row)
                    st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Nenhuma disciplina selecionada para visualização.")


    st.markdown("---")

    with st.container():
        st.markdown("#### Análise de Prioridade e Conteúdo")
        col_bar, col_bubble = st.columns(2)
        
        with col_bar:
            chart_bar_conteudo = create_altair_bar_chart_conteudo(df_final_filtered)
            st.altair_chart(chart_bar_conteudo, use_container_width=True)

        with col_bubble:
            df_strategy = pd.DataFrame(ED_DATA)
            total_peso_geral = df_strategy['Peso'].sum()
            df_strategy['Porcentagem_Pontos'] = round((df_strategy['Peso'] / total_peso_geral) * 100, 1)
            chart_bubble = create_altair_bubble_chart(df_strategy)
            st.altair_chart(chart_bubble, use_container_width=True)

    with st.expander("🔍 Ver Tabela de Conteúdos Detalhada"):
        st.markdown("Esta tabela lista todos os conteúdos do edital e o seu status.")
        st.dataframe(df_dados, use_container_width=True, hide_index=True)
    
else:
    st.error(f"❌ Não foi possível carregar os dados da aba '{WORKSHEET_NAME_DADOS}'. Verifique sua conexão e configurações.")


# --- Rodapé ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px;">
    <p style="margin: 0; color: #666;">
        🚀 Dashboard desenvolvido com Streamlit e Altair<br>
        📊 Concurso TAE UFG
    </p>
</div>
""", unsafe_allow_html=True)
