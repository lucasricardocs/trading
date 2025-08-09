# -- coding: utf-8 --
import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64

# --- Configurações ---
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'
WORKSHEET_NAME = 'Data'
CONCURSO_DATE = datetime(2024, 9, 28)  # Data do concurso

# --- Funções de Autenticação ---
@st.cache_resource
def get_google_auth():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    credentials_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_worksheet():
    gc = get_google_auth()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(WORKSHEET_NAME)

@st.cache_data(ttl=600)
def read_data():
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

# --- Funções de Design ---
def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{encoded_string.decode()});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        .custom-card {{
            background-color: rgba(255, 255, 255, 0.92) !important;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            margin-bottom: 25px;
        }}
        .header {{
            background: linear-gradient(135deg, rgba(67, 97, 238, 0.9), rgba(58, 12, 163, 0.9));
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: center;
        }}
        .countdown {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffd700;
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.7);
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
        .discipline-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 25px;
            margin-top: 2rem;
        }}
        .donut-container {{
            background-color: rgba(255, 255, 255, 0.85);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        .donut-container:hover {{
            transform: scale(1.02);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Configuração da Página ---
st.set_page_config(
    page_title="Progresso TAE UFG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Adicionar fundo (coloque uma imagem 'background.jpg' na mesma pasta)
# add_bg_from_local('background.jpg')  # Descomente e substitua pelo caminho da sua imagem

# --- Cabeçalho ---
dias_restantes = (CONCURSO_DATE - datetime.now()).days
st.markdown(f"""
<div class="header">
    <h1 style="margin:0;">📊 PROGRESSO DE ESTUDOS - TAE UFG</h1>
    <h3 style="margin:0; font-weight:400;">Concurso em 28/09/2024 • <span class="countdown">{dias_restantes} DIAS RESTANTES</span></h3>
</div>
""", unsafe_allow_html=True)

# --- Carregar Dados ---
df = read_data()

if not df.empty:
    # Verificar e renomear colunas
    if len(df.columns) >= 5:
        df = df.iloc[:, [0, 3, 4]]  # Colunas A, D, E
        df.columns = ['Disciplina', 'Feito', 'Pendente']
        
        # Converter para numérico
        df['Feito'] = pd.to_numeric(df['Feito'], errors='coerce').fillna(0)
        df['Pendente'] = pd.to_numeric(df['Pendente'], errors='coerce').fillna(0)
        
        # Calcular total e progresso
        df['Total'] = df['Feito'] + df['Pendente']
        df['Progresso (%)'] = round(df['Feito'] / df['Total'] * 100, 1)
        
        # --- Gráficos de Rosca por Disciplina ---
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
            st.markdown(f'<div class="donut-container">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- Gráfico de Progresso Geral ---
        st.markdown("---")
        with st.container():
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("📈 Progresso Geral por Disciplina")
            
            # Ordenar por progresso
            df_sorted = df.sort_values('Progresso (%)', ascending=True)
            
            # Criar gráfico de barras horizontais
            fig = go.Figure()
            
            # Barra de feito
            fig.add_trace(go.Bar(
                y=df_sorted['Disciplina'],
                x=df_sorted['Feito'],
                name='Feito',
                orientation='h',
                marker=dict(color='#4361ee'),
                hovertemplate='<b>%{y}</b><br>Feito: %{x} questões<br>Progresso: %{customdata}%',
                customdata=df_sorted['Progresso (%)']
            ))
            
            # Barra de pendente
            fig.add_trace(go.Bar(
                y=df_sorted['Disciplina'],
                x=df_sorted['Pendente'],
                name='Pendente',
                orientation='h',
                marker=dict(color='#f72585'),
                hovertemplate='<b>%{y}</b><br>Pendente: %{x} questões'
            ))
            
            fig.update_layout(
                barmode='stack',
                height=600,
                xaxis_title="Quantidade de Questões",
                yaxis_title="Disciplina",
                legend_title="Status",
                hovermode="y unified",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # --- Resumo Estatístico ---
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.subheader("🏆 Top 3 Disciplinas")
                
                top3 = df.nlargest(3, 'Progresso (%)')
                
                for i, (_, row) in enumerate(top3.iterrows()):
                    st.metric(
                        label=f"{i+1}. {row['Disciplina']}",
                        value=f"{row['Progresso (%)']}%",
                        help=f"Feito: {row['Feito']} | Pendente: {row['Pendente']}"
                    )
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.subheader("🚨 Disciplinas Prioritárias")
                
                bottom3 = df.nsmallest(3, 'Progresso (%)')
                
                for i, (_, row) in enumerate(bottom3.iterrows()):
                    st.metric(
                        label=f"{i+1}. {row['Disciplina']}",
                        value=f"{row['Progresso (%)']}%",
                        delta=f"Pendente: {row['Pendente']} questões",
                        delta_color="inverse"
                    )
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.error("A planilha não possui colunas suficientes. Verifique a estrutura dos dados.")
else:
    st.warning("Nenhum dado encontrado na planilha. Verifique a conexão e os dados.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido para acompanhamento de estudos • Concurso TAE UFG • Atualizado automaticamente")
