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

def process_data_for_charts(df):
    """Processar dados para os gráficos de rosca"""
    if df.empty:
        return {}
    
    # Agrupar por matéria e contar status
    disciplinas_stats = {}
    
    for disciplina in df['Matéria'].unique():
        disciplina_data = df[df['Matéria'] == disciplina]
        
        feito = len(disciplina_data[disciplina_data['STATUS'] == 'FEITO'])
        pendente = len(disciplina_data[disciplina_data['STATUS'] == 'PENDENTE'])
        total = feito + pendente
        
        if total > 0:
            percentual_feito = (feito / total) * 100
            
            disciplinas_stats[disciplina] = {
                'feito': feito,
                'pendente': pendente,
                'total': total,
                'percentual_feito': percentual_feito
            }
    
    return disciplinas_stats

def create_donut_chart(feito, pendente, disciplina, color_scheme=None):
    """Criar gráfico de rosca com Altair"""
    # Dados para o gráfico
    data = pd.DataFrame([
        {'categoria': 'Feito', 'valor': feito, 'disciplina': disciplina},
        {'categoria': 'Pendente', 'valor': pendente, 'disciplina': disciplina}
    ])
    
    # Cores padrão se não especificadas
    if color_scheme is None:
        color_scheme = [COLOR_POSITIVE, COLOR_NEGATIVE]
    
    # Gráfico de rosca
    chart = alt.Chart(data).add_selection(
        alt.selection_single()
    ).mark_arc(
        innerRadius=50,
        outerRadius=80,
        stroke='white',
        strokeWidth=2
    ).encode(
        theta=alt.Theta('valor:Q'),
        color=alt.Color(
            'categoria:N',
            scale=alt.Scale(
                domain=['Feito', 'Pendente'],
                range=color_scheme
            ),
            legend=alt.Legend(
                orient='bottom',
                titleFontSize=12,
                labelFontSize=10
            )
        ),
        tooltip=[
            alt.Tooltip('categoria:N', title='Status'),
            alt.Tooltip('valor:Q', title='Quantidade'),
            alt.Tooltip('disciplina:N', title='Disciplina')
        ]
    ).resolve_scale(
        color='independent'
    ).properties(
        width=200,
        height=200,
        title=alt.TitleParams(
            text=disciplina,
            fontSize=14,
            fontWeight='bold',
            anchor='start'
        )
    )
    
    return chart

def create_summary_metrics(disciplinas_stats):
    """Criar métricas resumo"""
    if not disciplinas_stats:
        return 0, 0, 0, 0.0
    
    total_feito = sum(stats['feito'] for stats in disciplinas_stats.values())
    total_pendente = sum(stats['pendente'] for stats in disciplinas_stats.values())
    total_geral = total_feito + total_pendente
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
        height=20,
        cornerRadius=5
    ).encode(
        x=alt.X('percentual:Q', 
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(title='Percentual Concluído (%)', format='.0f')),
        y=alt.Y('disciplina:O', 
                axis=alt.Axis(title=None, labelLimit=200)),
        color=alt.Color(
            'percentual:Q',
            scale=alt.Scale(
                range=['#ff4757', '#ffa502', '#2ed573'],
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
        width=500,
        height=300,
        title=alt.TitleParams(
            text='Progresso por Disciplina',
            fontSize=16,
            fontWeight='bold'
        )
    )
    
    return chart

def main():
    """Função principal do dashboard"""
    
    # Título principal
    st.title("📚 Dashboard de Estudos - Concurso Público")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controles")
        
        # Botão para atualizar dados
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Informações
        st.markdown("### 📊 Informações")
        st.info("Dados atualizados automaticamente a cada 60 segundos")
        
        # Legenda de cores
        st.markdown("### 🎨 Legenda")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"🟢 **Feito**")
        with col2:
            st.markdown(f"🔴 **Pendente**")
    
    # Carregar dados
    with st.spinner("Carregando dados..."):
        df = load_data()
    
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")
        return
    
    # Processar dados
    disciplinas_stats = process_data_for_charts(df)
    
    if not disciplinas_stats:
        st.warning("⚠️ Nenhum dado válido encontrado.")
        return
    
    # Métricas gerais
    total_feito, total_pendente, total_geral, percentual_geral = create_summary_metrics(disciplinas_stats)
    
    # Container para métricas
    st.header("📈 Resumo Geral")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📋 Total de Itens",
            value=f"{total_geral:,}",
            help="Número total de tópicos de estudo"
        )
    
    with col2:
        st.metric(
            label="✅ Concluídos",
            value=f"{total_feito:,}",
            delta=f"{percentual_geral:.1f}%",
            help="Tópicos já estudados"
        )
    
    with col3:
        st.metric(
            label="⏳ Pendentes",
            value=f"{total_pendente:,}",
            delta=f"{100-percentual_geral:.1f}%",
            delta_color="inverse",
            help="Tópicos ainda não estudados"
        )
    
    with col4:
        st.metric(
            label="🎯 Progresso",
            value=f"{percentual_geral:.1f}%",
            help="Percentual geral de conclusão"
        )
    
    st.markdown("---")
    
    # Gráfico de progresso geral
    st.header("📊 Progresso por Disciplina")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        progress_chart = create_progress_bar_chart(disciplinas_stats)
        st.altair_chart(progress_chart, use_container_width=True)
    
    with col2:
        st.markdown("### 📋 Detalhes")
        for disciplina, stats in disciplinas_stats.items():
            with st.expander(f"**{disciplina}**"):
                st.write(f"**Concluídos:** {stats['feito']}")
                st.write(f"**Pendentes:** {stats['pendente']}")
                st.write(f"**Total:** {stats['total']}")
                st.write(f"**Progresso:** {stats['percentual_feito']:.1f}%")
    
    st.markdown("---")
    
    # Gráficos de rosca por disciplina
    st.header("🍩 Gráficos de Rosca por Disciplina")
    
    # Organizar em colunas (máximo 3 por linha)
    disciplinas = list(disciplinas_stats.keys())
    
    for i in range(0, len(disciplinas), 3):
        cols = st.columns(3)
        
        for j, col in enumerate(cols):
            if i + j < len(disciplinas):
                disciplina = disciplinas[i + j]
                stats = disciplinas_stats[disciplina]
                
                with col:
                    # Criar gráfico de rosca
                    donut_chart = create_donut_chart(
                        stats['feito'], 
                        stats['pendente'], 
                        disciplina,
                        [COLOR_POSITIVE, COLOR_NEGATIVE]
                    )
                    
                    st.altair_chart(donut_chart, use_container_width=True)
                    
                    # Informações adicionais
                    st.markdown(f"""
                    <div style='text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 5px; margin-top: 10px;'>
                        <strong>{stats['feito']}</strong> de <strong>{stats['total']}</strong> itens concluídos
                        <br>
                        <span style='color: #28a745; font-weight: bold;'>{stats['percentual_feito']:.1f}%</span> de progresso
                    </div>
                    """, unsafe_allow_html=True)
    
    # Rodapé
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #6c757d; font-size: 0.9em;'>
            💡 <strong>Dica:</strong> Use o botão "Atualizar Dados" na barra lateral para sincronizar com a planilha<br>
            📊 Dashboard atualizado em: """ + datetime.now().strftime("%d/%m/%Y às %H:%M:%S") + """
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
