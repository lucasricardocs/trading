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

# --- CSS Customizado ---
st.markdown("""
<style>
    /* Estilo geral */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-left: 5px solid #667eea;
        margin: 0.5rem 0;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    /* Container dos gráficos */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 6px 25px rgba(0,0,0,0.1);
        border: 3px solid #f8f9fa;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .chart-container:hover {
        border-color: #667eea;
        box-shadow: 0 8px 35px rgba(102,126,234,0.15);
    }
    
    /* Títulos dos gráficos */
    .chart-title {
        text-align: center;
        font-size: 1.3rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background: linear-gradient(90deg, #f8f9fa, #e9ecef);
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: 600;
    }
    
    /* Progress info */
    .progress-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-top: 1rem;
        border: 2px solid #e9ecef;
        font-size: 0.95rem;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        padding: 1rem 2rem;
        border-radius: 50px;
        text-align: center;
        margin: 2rem 0 1rem 0;
        font-size: 1.5rem;
        font-weight: 700;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    
    /* Sidebar styling */
    .sidebar-content {
        background: linear-gradient(180deg, #667eea, #764ba2);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    /* Debug panel */
    .debug-panel {
        background: #f1f3f4;
        border: 2px dashed #6c757d;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
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

# --- Funções de Dados ---
@st.cache_data(ttl=60)
def load_data():
    """Carregar dados da planilha"""
    worksheet = get_worksheet()
    if worksheet:
        try:
            # Método alternativo para lidar com cabeçalhos duplicados
            all_values = worksheet.get_all_values()
            
            if not all_values:
                st.warning("Planilha vazia")
                return pd.DataFrame()
            
            # Pegar a primeira linha como cabeçalho e limpar
            headers = all_values[0]
            
            # Limpar cabeçalhos vazios e duplicados
            clean_headers = []
            for i, header in enumerate(headers):
                if header.strip():  # Se não estiver vazio
                    clean_headers.append(header.strip())
                else:
                    clean_headers.append(f"Coluna_{i}")  # Nome padrão para colunas vazias
            
            # Pegar os dados (excluindo cabeçalho)
            data_rows = all_values[1:]
            
            # Criar DataFrame
            df = pd.DataFrame(data_rows, columns=clean_headers)
            
            # Verificar se as colunas necessárias existem
            required_columns = ['Matéria', 'STATUS']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                # Tentar mapear colunas similares
                column_mapping = {}
                for col in df.columns:
                    col_lower = col.lower()
                    if 'matéria' in col_lower or 'materia' in col_lower or 'disciplina' in col_lower:
                        column_mapping[col] = 'Matéria'
                    elif 'status' in col_lower or 'situação' in col_lower or 'situacao' in col_lower:
                        column_mapping[col] = 'STATUS'
                
                # Renomear colunas
                df = df.rename(columns=column_mapping)
                
                # Verificar novamente
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    st.error(f"Colunas obrigatórias não encontradas: {missing_columns}")
                    st.info(f"Colunas disponíveis: {list(df.columns)}")
                    return pd.DataFrame()
            
            # Limpar dados vazios
            df = df.dropna(subset=['Matéria'])
            df = df[df['Matéria'] != '']
            
            # Limpar valores de STATUS
            df['STATUS'] = df['STATUS'].str.strip().str.upper()
            
            # Filtrar apenas status válidos
            valid_status = ['FEITO', 'PENDENTE']
            df = df[df['STATUS'].isin(valid_status)]
            
            if df.empty:
                st.warning("Nenhum dado válido encontrado após limpeza")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            # Adicionar informações de debug
            with st.expander("🔍 Informações de Debug"):
                st.write(f"Erro detalhado: {str(e)}")
                try:
                    all_values = worksheet.get_all_values()
                    if all_values:
                        st.write("Primeira linha (cabeçalhos):")
                        st.write(all_values[0])
                        st.write(f"Total de linhas: {len(all_values)}")
                except:
                    st.write("Não foi possível acessar os dados da planilha")
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

# --- Funções de Visualização ---
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
                domain=['Feito', 'Pendente'],
                range=color_scheme
            ),
            legend=alt.Legend(
                orient='bottom',
                titleFontSize=12,
                labelFontSize=11,
                symbolSize=100,
                symbolType='circle'
            )
        ),
        tooltip=[
            alt.Tooltip('categoria:N', title='Status'),
            alt.Tooltip('valor:Q', title='Quantidade'),
            alt.Tooltip('disciplina:N', title='Disciplina')
        ],
        opacity=alt.condition(
            alt.selection_single(),
            alt.value(1.0),
            alt.value(0.8)
        )
    ).resolve_scale(
        color='independent'
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
                            labelFontWeight='bold')),
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
        width=600,
        height=350
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
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">{icon}</span>
            <span style="color: #6c757d; font-size: 0.9rem; font-weight: 600;">{title}</span>
        </div>
        <div style="font-size: 2rem; font-weight: bold; color: #2c3e50; margin-bottom: 0.5rem;">{value:,}</div>
        {delta_html}
        <div style="color: #6c757d; font-size: 0.8rem; margin-top: 0.5rem;">{help_text}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Função Principal ---
def main():
    """Função principal do dashboard"""
    
    # Calcular dias para a prova
    data_prova = date(2025, 9, 28)
    data_hoje = date.today()
    dias_para_prova = (data_prova - data_hoje).days
    
    # Formatação da data atual
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    dias_semana = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", 
        "sexta-feira", "sábado", "domingo"
    ]
    
    data_formatada = f"{dias_semana[data_hoje.weekday()]}, {data_hoje.day} de {meses[data_hoje.month-1]} de {data_hoje.year}"
    
    # Definir cor e ícone baseado nos dias restantes
    if dias_para_prova > 60:
        cor_prazo = "#28a745"  # Verde - muito tempo
        icone_prazo = "🟢"
        status_prazo = "Bastante tempo"
    elif dias_para_prova > 30:
        cor_prazo = "#ffc107"  # Amarelo - tempo moderado
        icone_prazo = "🟡"
        status_prazo = "Tempo moderado"
    elif dias_para_prova > 0:
        cor_prazo = "#fd7e14"  # Laranja - pouco tempo
        icone_prazo = "🟠"
        status_prazo = "Reta final!"
    else:
        cor_prazo = "#dc3545"  # Vermelho - prazo passou
        icone_prazo = "🔴"
        status_prazo = "Prazo vencido"
        dias_para_prova = abs(dias_para_prova)
    
    # Cabeçalho principal com informações da prova
    st.markdown(f"""
    <div class="main-header">
        <h1>📚 Dashboard de Estudos - Concurso Público</h1>
        <p style="font-size: 1.1rem; opacity: 0.9; margin-bottom: 1.5rem;">Acompanhe seu progresso de forma visual e organizada</p>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 1.5rem;">
            <div style="background: rgba(255,255,255,0.15); padding: 1.2rem; border-radius: 15px; backdrop-filter: blur(10px);">
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
                    📅 Data Atual
                </div>
                <div style="font-size: 1.3rem; font-weight: bold;">
                    {data_formatada.title()}
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.15); padding: 1.2rem; border-radius: 15px; backdrop-filter: blur(10px);">
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
                    🎯 Data da Prova
                </div>
                <div style="font-size: 1.3rem; font-weight: bold;">
                    Domingo, 28 de setembro de 2025
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.15); padding: 1.2rem; border-radius: 15px; backdrop-filter: blur(10px); border: 2px solid {cor_prazo};">
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
                    {icone_prazo} Dias Restantes
                </div>
                <div style="font-size: 2.2rem; font-weight: bold; color: {cor_prazo};">
                    {dias_para_prova} dias
                </div>
                <div style="font-size: 0.9rem; opacity: 0.8; margin-top: 0.3rem;">
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
        # Informações técnicas
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 📊 Informações Técnicas")
        st.info("📡 Dados sincronizados automaticamente a cada 60 segundos")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão para atualizar dados
        if st.button("🔄 Atualizar Dados", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        # Botão para debug
        debug_mode = st.checkbox("🔍 Modo Debug", help="Mostrar informações detalhadas para diagnóstico")
        
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
        
        # Metas diárias sugeridas
        if dias_para_prova > 0 and total_pendente > 0:
            itens_por_dia = max(1, total_pendente / dias_para_prova)
            st.markdown(f"""
            **📈 Meta sugerida:**  
            ~{itens_por_dia:.1f} itens/dia
            """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Legenda de cores
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 🎨 Legenda de Cores")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🟢 **Concluído**")
        with col2:
            st.markdown("🔴 **Pendente**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Instruções
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("### 💡 Como usar")
        st.markdown("""
        - Visualize o progresso geral no topo
        - Analise cada disciplina nos gráficos
        - Passe o mouse sobre os gráficos para detalhes
        - Use o modo debug se houver problemas
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
            with col2:
                st.write("**📈 Distribuição dos Dados:**")
                st.write("**Status:**")
                st.write(df['STATUS'].value_counts())
                st.write("**Disciplinas:**")
                st.write(df['Matéria'].value_counts())
            
            st.write("**🔍 Amostra dos Dados (5 primeiras linhas):**")
            st.dataframe(df.head(), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")
        
        # Painel de soluções
        with st.expander("💡 Guia de Solução de Problemas", expanded=True):
            st.markdown("""
            <div style='background: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 5px solid #dc3545;'>
            
            ### 🔧 Possíveis soluções:
            
            **1. Verificar a planilha:**
            - ✅ Certifique-se de que existe uma aba chamada "dados"
            - ✅ Verifique se há cabeçalhos nas colunas
            - ✅ Remova colunas vazias do cabeçalho
            
            **2. Colunas obrigatórias:**
            - 📝 `Matéria` ou `Disciplina`: Nome da matéria/disciplina
            - 🏷️ `STATUS`: Deve conter exatamente "FEITO" ou "PENDENTE"
            
            **3. Formato esperado:**
            ```
            | Matéria              | Conteúdo                    | STATUS   |
            |----------------------|----------------------------|----------|
            | LÍNGUA PORTUGUESA    | Interpretação de textos    | FEITO    |
            | RACIOCÍNIO LÓGICO    | Lógica e raciocínio       | PENDENTE |
            ```
            
            **4. Verificar permissões:**
            - 🔐 A conta de serviço tem acesso à planilha?
            - 🆔 O ID da planilha está correto?
            - 🌐 A planilha está compartilhada adequadamente?
            
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
            value=total_geral,
            help_text="Número total de tópicos de estudo",
            icon="📋"
        )
    
    with col2:
        display_metric_card(
            title="Itens Concluídos", 
            value=total_feito,
            delta=f"{percentual_geral:.1f}%",
            help_text="Tópicos já estudados",
            icon="✅"
        )
    
    with col3:
        display_metric_card(
            title="Itens Pendentes",
            value=total_pendente,
            delta=f"{100-percentual_geral:.1f}%",
            help_text="Tópicos ainda não estudados",
            icon="⏳"
        )
    
    with col4:
        display_metric_card(
            title="Progresso Geral",
            value=f"{percentual_geral:.1f}",
            delta="%",
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
            progress_color = "#28a745" if stats['percentual_feito'] > 50 else "#ffc107" if stats['percentual_feito'] > 20 else "#dc3545"
            
            with st.expander(f"📚 **{disciplina}** ({stats['percentual_feito']:.1f}%)", expanded=i==0):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("✅ Concluídos", stats['feito'])
                    st.metric("📊 Total", stats['total'])
                with col_b:
                    st.metric("⏳ Pendentes", stats['pendente'])
                    st.metric("🎯 Progresso", f"{stats['percentual_feito']:.1f}%")
                
                # Barra de progresso
                progress_width = int(stats['percentual_feito'])
                st.markdown(f"""
                <div style="background: #e9ecef; border-radius: 10px; height: 20px; margin: 10px 0;">
                    <div style="background: {progress_color}; width: {progress_width}%; height: 100%; border-radius: 10px; transition: width 0.3s ease;"></div>
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
                    # Container com borda branca
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    
                    # Título do gráfico
                    st.markdown(f'<div class="chart-title">📚 {disciplina}</div>', unsafe_allow_html=True)
                    
                    # Criar gráfico de rosca
                    donut_chart = create_donut_chart(
                        stats['feito'], 
                        stats['pendente'], 
                        disciplina,
                        [COLOR_POSITIVE, COLOR_NEGATIVE]
                    )
                    
                    st.altair_chart(donut_chart, use_container_width=True)
                    
                    # Informações adicionais
                    progress_color = "#28a745" if stats['percentual_feito'] > 50 else "#ffc107" if stats['percentual_feito'] > 20 else "#dc3545"
                    
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
    st.markdown("---")
    current_time = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    st.markdown(f"""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(90deg, #667eea, #764ba2); color: white; border-radius: 15px; margin-top: 2rem;'>
        <h3>💡 Dicas para o Sucesso nos Estudos</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">📊 Acompanhe regularmente</div>
                <div style="font-size: 0.9rem;">Use este dashboard diariamente para monitorar seu progresso</div>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">🎯 Foque no vermelho</div>
                <div style="font-size: 0.9rem;">Priorize as disciplinas com menor percentual de conclusão</div>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">✅ Celebre o verde</div>
                <div style="font-size: 0.9rem;">Reconheça seu progresso nas disciplinas já avançadas</div>
            </div>
        </div>
        <hr style="border: 1px solid rgba(255,255,255,0.3); margin: 1.5rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div style="font-size: 0.9rem; opacity: 0.8;">
                🔄 Última atualização: {current_time}
            </div>
            <div style="font-size: 0.9rem; opacity: 0.8;">
                📈 {len(disciplinas_stats)} disciplinas | {icone_prazo} {dias_para_prova} dias para a prova
            </div>
            <div style="font-size: 0.9rem; opacity: 0.8;">
                📚 Dashboard de Estudos v2.1
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
