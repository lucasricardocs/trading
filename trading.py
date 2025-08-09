# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import time
from datetime import datetime, date
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
    page_title="Dashboard de Disciplinas",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# --- Funções ---
@st.cache_resource
def get_google_auth():
    """Autenticação com Google Sheets"""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais do Google não encontradas nos secrets do Streamlit")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
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

@st.cache_data(ttl=60)
def load_data():
    """Carregar dados da planilha"""
    worksheet = get_worksheet()
    if worksheet:
        try:
            # Obter todos os dados
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            
            # Limpar dados vazios
            df = df.dropna(subset=['Matéria'])
            df = df[df['Matéria'] != '']
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def create_donut_chart(data, title, color_scheme=None):
    """Criar gráfico de rosca com Altair"""
    if data.empty:
        return alt.Chart().mark_text(text="Sem dados", fontSize=16)
    
    # Preparar dados para o gráfico de rosca
    total = data['Peso'].sum()
    data_chart = data.copy()
    data_chart['percentage'] = (data_chart['Peso'] / total * 100).round(1)
    data_chart['angle'] = data_chart['Peso'] / total * 360
    
    # Gráfico de rosca (donut chart)
    base = alt.Chart(data_chart).add_selection(
        alt.selection_single()
    )
    
    # Arco externo
    outer_arc = base.mark_arc(
        innerRadius=50,
        outerRadius=100,
        stroke='white',
        strokeWidth=2
    ).encode(
        theta=alt.Theta('Peso:Q'),
        color=alt.Color(
            'Conteúdo:N',
            scale=alt.Scale(range=color_scheme if color_scheme else DISCIPLINA_COLORS),
            legend=alt.Legend(
                orient='right',
                titleFontSize=12,
                labelFontSize=10,
                symbolSize=100
            )
        ),
        tooltip=[
            alt.Tooltip('Conteúdo:N', title='Conteúdo'),
            alt.Tooltip('Peso:Q', title='Peso'),
            alt.Tooltip('percentage:Q', title='Percentual (%)', format='.1f')
        ]
    )
    
    # Texto central com o total
    text_center = alt.Chart(pd.DataFrame({'total': [total]})).mark_text(
        align='center',
        baseline='middle',
        fontSize=20,
        fontWeight='bold',
        color='#333'
    ).encode(
        text=alt.Text('total:Q', format='.0f')
    )
    
    # Título
    title_chart = alt.Chart(pd.DataFrame({'title': [title]})).mark_text(
        align='center',
        baseline='top',
        fontSize=16,
        fontWeight='bold',
        dy=-140,
        color='#333'
    ).encode(
        text='title:N'
    )
    
    return (outer_arc + text_center + title_chart).resolve_scale(
        color='independent'
    ).properties(
        width=250,
        height=250,
        title=alt.TitleParams(text=title, fontSize=16, anchor='start')
    )

def create_summary_chart(df):
    """Criar gráfico resumo de todas as disciplinas"""
    disciplinas_summary = df.groupby('Matéria')['Peso'].sum().reset_index()
    disciplinas_summary = disciplinas_summary.sort_values('Peso', ascending=False)
    
    total_geral = disciplinas_summary['Peso'].sum()
    disciplinas_summary['percentage'] = (disciplinas_summary['Peso'] / total_geral * 100).round(1)
    
    # Gráfico de rosca resumo
    base = alt.Chart(disciplinas_summary)
    
    outer_arc = base.mark_arc(
        innerRadius=60,
        outerRadius=120,
        stroke='white',
        strokeWidth=3
    ).encode(
        theta=alt.Theta('Peso:Q'),
        color=alt.Color(
            'Matéria:N',
            scale=alt.Scale(range=DISCIPLINA_COLORS),
            legend=alt.Legend(
                orient='right',
                titleFontSize=14,
                labelFontSize=12,
                symbolSize=150
            )
        ),
        tooltip=[
            alt.Tooltip('Matéria:N', title='Disciplina'),
            alt.Tooltip('Peso:Q', title='Peso Total'),
            alt.Tooltip('percentage:Q', title='Percentual (%)', format='.1f')
        ]
    )
    
    # Texto central
    text_center = alt.Chart(pd.DataFrame({'total': [total_geral]})).mark_text(
        align='center',
        baseline='middle',
        fontSize=24,
        fontWeight='bold',
        color='#333'
    ).encode(
        text=alt.Text('total:Q', format='.0f')
    )
    
    return (outer_arc + text_center).resolve_scale(
        color='independent'
    ).properties(
        width=300,
        height=300,
        title=alt.TitleParams(text="Resumo Geral das Disciplinas", fontSize=18, anchor='start')
    )

def main():
    """Função principal do dashboard"""
    st.title("📚 Dashboard de Evolução por Disciplinas")
    st.markdown("---")
    
    # Carregar dados
    with st.spinner("Carregando dados da planilha..."):
        df = load_data()
    
    if df.empty:
        st.error("Não foi possível carregar os dados da planilha.")
        st.info("Verifique se as credenciais do Google estão configuradas corretamente nos secrets do Streamlit.")
        return
    
    # Sidebar com informações
    st.sidebar.header("📊 Informações Gerais")
    total_disciplinas = df['Matéria'].nunique()
    total_conteudos = len(df)
    peso_total = df['Peso'].sum()
    
    st.sidebar.metric("Total de Disciplinas", total_disciplinas)
    st.sidebar.metric("Total de Conteúdos", total_conteudos)
    st.sidebar.metric("Peso Total", peso_total)
    
    # Filtros
    st.sidebar.header("🔍 Filtros")
    disciplinas_disponiveis = sorted(df['Matéria'].unique())
    disciplinas_selecionadas = st.sidebar.multiselect(
        "Selecione as disciplinas:",
        disciplinas_disponiveis,
        default=disciplinas_disponiveis
    )
    
    # Filtrar dados
    df_filtrado = df[df['Matéria'].isin(disciplinas_selecionadas)]
    
    if df_filtrado.empty:
        st.warning("Nenhuma disciplina selecionada ou dados disponíveis.")
        return
    
    # Layout principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📈 Gráficos de Rosca por Disciplina")
        
        # Criar gráficos para cada disciplina
        disciplinas = df_filtrado['Matéria'].unique()
        
        # Organizar em grid de 2 colunas
        for i in range(0, len(disciplinas), 2):
            cols = st.columns(2)
            
            for j, col in enumerate(cols):
                if i + j < len(disciplinas):
                    disciplina = disciplinas[i + j]
                    dados_disciplina = df_filtrado[df_filtrado['Matéria'] == disciplina]
                    
                    with col:
                        # Criar cores específicas para cada conteúdo da disciplina
                        num_conteudos = len(dados_disciplina)
                        colors = DISCIPLINA_COLORS[:num_conteudos] if num_conteudos <= len(DISCIPLINA_COLORS) else DISCIPLINA_COLORS * (num_conteudos // len(DISCIPLINA_COLORS) + 1)
                        
                        chart = create_donut_chart(dados_disciplina, disciplina, colors[:num_conteudos])
                        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.header("📊 Resumo Geral")
        
        # Gráfico resumo
        summary_chart = create_summary_chart(df_filtrado)
        st.altair_chart(summary_chart, use_container_width=True)
        
        # Tabela de dados
        st.subheader("📋 Dados Detalhados")
        
        # Preparar dados para exibição
        df_display = df_filtrado.copy()
        df_display = df_display.sort_values(['Matéria', 'Peso'], ascending=[True, False])
        
        # Mostrar tabela
        st.dataframe(
            df_display[['Matéria', 'Conteúdo', 'Peso']],
            use_container_width=True,
            hide_index=True
        )
        
        # Estatísticas por disciplina
        st.subheader("📈 Estatísticas por Disciplina")
        stats_disciplina = df_filtrado.groupby('Matéria').agg({
            'Peso': ['sum', 'mean', 'count']
        }).round(2)
        
        stats_disciplina.columns = ['Total', 'Média', 'Qtd Conteúdos']
        stats_disciplina = stats_disciplina.sort_values('Total', ascending=False)
        
        st.dataframe(stats_disciplina, use_container_width=True)
    
    # Rodapé
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 12px;'>
        Dashboard criado com Streamlit e Altair | Dados atualizados automaticamente
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
