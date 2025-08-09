# -- coding: utf-8 --
import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.oauth2.service_account import Credentials
import numpy as np
from datetime import datetime, timedelta

# --- Configurações ---
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'
WORKSHEET_NAME = 'Página1'
CONCURSO_DATE = datetime(2024, 9, 28)  # Data do concurso

# --- Funções de Autenticação ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    
    credentials_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_worksheet():
    """Retorna a worksheet especificada."""
    gc = get_google_auth()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(WORKSHEET_NAME)

@st.cache_data(ttl=600)  # Cache de 10 minutos
def read_data():
    """Lê os dados da planilha."""
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

# --- Cálculo de dias restantes ---
def dias_restantes():
    hoje = datetime.now()
    return (CONCURSO_DATE - hoje).days

# --- Interface do Dashboard ---
st.set_page_config(
    page_title="TAE UFG - Dashboard de Estudos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

:root {
    --primary: #4361ee;
    --secondary: #3f37c9;
    --success: #4cc9f0;
    --warning: #f72585;
    --dark: #1d3557;
    --light: #f8f9fa;
}

* {
    font-family: 'Poppins', sans-serif;
}

.header {
    background: linear-gradient(135deg, #4361ee, #3a0ca3);
    color: white;
    padding: 1.5rem;
    border-radius: 15px;
    box-shadow: 0 6px 20px rgba(67, 97, 238, 0.3);
    margin-bottom: 2rem;
    text-align: center;
}

.metric-card {
    background: white;
    border-radius: 15px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    text-align: center;
    transition: all 0.3s ease;
    border: 1px solid rgba(0,0,0,0.05);
    height: 100%;
}

.metric-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.progress-container {
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
    height: 20px;
    margin: 15px 0;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #4361ee, #4895ef);
    border-radius: 10px;
    transition: width 1s ease-in-out;
}

.discipline-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 25px;
    margin-top: 2rem;
}

.donut-container {
    background: white;
    border-radius: 15px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
}

.donut-container:hover {
    transform: scale(1.03);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.countdown {
    font-size: 1.8rem;
    font-weight: 700;
    color: #f72585;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

h1, h2, h3, h4, h5, h6 {
    color: var(--dark);
}

</style>
""", unsafe_allow_html=True)

# Cabeçalho
st.markdown(f"""
<div class="header">
    <h1 style="margin:0;font-size:2.5rem;">🚀 DASHBOARD DE ESTUDOS - TAE UFG</h1>
    <h3 style="margin:0;font-weight:400;">Concurso em 28/09/2024 • <span class="countdown">{dias_restantes()} DIAS RESTANTES</span></h3>
</div>
""", unsafe_allow_html=True)

# Carregar dados
df = read_data()

if not df.empty and len(df.columns) >= 5:
    # Processar dados
    df = df.iloc[:, [0, 3, 4]]  # Colunas A, D, E
    df.columns = ['Disciplina', 'Feito', 'Pendente']
    
    # Converter para numérico
    df['Feito'] = pd.to_numeric(df['Feito'], errors='coerce').fillna(0)
    df['Pendente'] = pd.to_numeric(df['Pendente'], errors='coerce').fillna(0)
    
    # Calcular métricas
    total_feito = int(df['Feito'].sum())
    total_pendente = int(df['Pendente'].sum())
    total_questoes = total_feito + total_pendente
    percentual_geral = round((total_feito / total_questoes * 100) if total_questoes > 0 else 0, 1)
    
    # Calcular questões por dia
    dias_rest = dias_restantes()
    questoes_por_dia = round(total_pendente / dias_rest, 1) if dias_rest > 0 else total_pendente
    
    # Calcular progresso por disciplina
    df['Total'] = df['Feito'] + df['Pendente']
    df['Progresso (%)'] = round((df['Feito'] / df['Total']) * 100, 1)
    df = df.sort_values('Progresso (%)', ascending=False)
    
    # --- Seção de Métricas ---
    st.subheader("📈 Visão Geral do Progresso")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.markdown(f"""
    <div class="metric-card">
        <h3>✅ QUESTÕES FEITAS</h3>
        <h1 style="color:#4361ee;font-size:3rem;">{total_feito}</h1>
        <p>{percentual_geral}% do total</p>
    </div>
    """, unsafe_allow_html=True)
    
    col2.markdown(f"""
    <div class="metric-card">
        <h3>⏳ QUESTÕES PENDENTES</h3>
        <h1 style="color:#f72585;font-size:3rem;">{total_pendente}</h1>
        <p>{100 - percentual_geral}% do total</p>
    </div>
    """, unsafe_allow_html=True)
    
    col3.markdown(f"""
    <div class="metric-card">
        <h3>📚 QUESTÕES POR DIA</h3>
        <h1 style="color:#4895ef;font-size:3rem;">{questoes_por_dia}</h1>
        <p>Necessárias para concluir</p>
    </div>
    """, unsafe_allow_html=True)
    
    col4.markdown(f"""
    <div class="metric-card">
        <h3>⏱ DIAS RESTANTES</h3>
        <h1 style="color:#7209b7;font-size:3rem;">{dias_restantes()}</h1>
        <p>Até o concurso</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Gráfico de Progresso Geral ---
    st.markdown("---")
    st.subheader("📊 Progresso Geral")
    
    fig_geral = go.Figure()
    fig_geral.add_trace(go.Indicator(
        mode = "gauge+number",
        value = percentual_geral,
        number = {'suffix': "%"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Conclusão Geral"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#4361ee"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "gray"}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': percentual_geral}
    }))
    
    fig_geral.update_layout(
        height=300,
        margin=dict(l=50, r=50, t=80, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=16)
    )
    
    st.plotly_chart(fig_geral, use_container_width=True)
    
    # --- Gráficos de Rosca por Disciplina ---
    st.markdown("---")
    st.subheader("📚 Progresso por Disciplina")
    st.markdown('<div class="discipline-grid">', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        disciplina = row['Disciplina']
        feito = row['Feito']
        pendente = row['Pendente']
        progresso = row['Progresso (%)']
        
        # Criar gráfico de rosca interativo
        fig = go.Figure(data=[
            go.Pie(
                values=[feito, pendente],
                labels=['Feito', 'Pendente'],
                hole=0.6,
                marker_colors=['#4361ee', '#f72585'],
                hoverinfo='label+percent+value',
                textinfo='none',
                pull=[0.1, 0]  # Efeito de destaque
            )
        ])
        
        fig.update_layout(
            title=f'<b>{disciplina}</b><br><span style="font-size:1.2rem">{progresso}% Concluído</span>',
            showlegend=True,
            height=300,
            margin=dict(t=80, b=30, l=30, r=30),
            annotations=[
                dict(
                    text=f"{feito}/{feito+pendente}",
                    x=0.5, y=0.5,
                    font_size=20,
                    showarrow=False
                )
            ]
        )
        
        # Container para cada gráfico
        with st.container():
            st.markdown(f'<div class="donut-container">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- Análise de Priorização ---
    st.markdown("---")
    st.subheader("🎯 Priorização de Estudos")
    
    # Calcular prioridade (pendente/dias restantes)
    df['Prioridade'] = round(df['Pendente'] / dias_restantes(), 2)
    df = df.sort_values('Prioridade', ascending=False)
    
    fig_prioridade = px.bar(
        df,
        x='Disciplina',
        y='Prioridade',
        color='Prioridade',
        color_continuous_scale='OrRd',
        text='Prioridade',
        labels={'Prioridade': 'Questões/Dia Necessárias'},
        height=400
    )
    
    fig_prioridade.update_traces(
        texttemplate='%{text:.2f}',
        textposition='outside',
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5
    )
    
    fig_prioridade.update_layout(
        xaxis_title="Disciplina",
        yaxis_title="Questões por Dia Necessárias",
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x"
    )
    
    st.plotly_chart(fig_prioridade, use_container_width=True)
    
    # --- Tabela Detalhada ---
    st.markdown("---")
    st.subheader("🧾 Detalhamento Completo")
    
    # Adicionar coluna de status
    df['Status'] = df['Progresso (%)'].apply(
        lambda x: "✅ Dominado" if x >= 80 else 
                 "⏳ Em progresso" if x >= 50 else 
                 "❗ Prioridade")
    
    st.dataframe(
        df[['Disciplina', 'Feito', 'Pendente', 'Total', 'Progresso (%)', 'Prioridade', 'Status']],
        column_config={
            "Progresso (%)": st.column_config.ProgressColumn(
                format="%f%%",
                min_value=0,
                max_value=100,
            ),
            "Prioridade": st.column_config.NumberColumn(
                format="%.2f questões/dia"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    
else:
    st.warning("⚠️ Nenhum dado encontrado ou estrutura incorreta. Verifique a planilha.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido para acompanhamento de estudos • Concurso TAE UFG • Atualizado automaticamente")
