# -*- coding: utf-8 -*-
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
    st.warning("⚠️ Bibliotecas do Google Sheets não disponíveis. Usando dados de exemplo.")

# --- Configurações ---
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'
WORKSHEET_NAME = 'Data'  # Nome da aba correta
CONCURSO_DATE = datetime(2025, 9, 28)  # Data do concurso

# Dados de questões e pesos para o edital
# A porcentagem de cada matéria é calculada com base no peso total
ED_DATA = {
    'Matéria': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO'],
    'Total_Conteudos': [20, 15, 10, 15, 30], # Quantidade de conteúdos por matéria (estimada da imagem)
    'Peso': [2, 1, 1, 1, 3] # Peso de cada matéria
}

# --- Dados de exemplo para teste local ---
def get_sample_data():
    """Gera dados de exemplo com base na nova estrutura do edital."""
    
    # Detalhamento dos conteúdos
    conteudos_do_edital = {
        'LÍNGUA PORTUGUESA': ['Características e funcionalidades de gêneros textuais variados', 'Interpretação de textos', 'Variação linguística: estilística, sociocultural, geográfica, histórica', 'Mecanismos de produção de sentidos nos textos: polissemia, ironia, comparação, ambiguidade, citação, inferência, pressuposto', 'Coesão e coerência textuais', 'Sequências textuais: descritiva, narrativa, argumentativa, injuntiva', 'Tipos de argumento', 'Acentuação e ortografia', 'Processo de formação de palavras', 'Classes morfológicas', 'Fenômenos gramaticais e construção de significados na língua portuguesa', 'Relações de coordenação e subordinação entre orações e entre termos da oração', 'Concordância verbal e nominal', 'Regência verbal e nominal', 'Colocação pronominal', 'Pontuação', 'Estilística', 'Figuras de linguagem'],
        'RLM': ['Lógica e raciocínio lógico', 'Análise de argumentação', 'Proposição lógica', 'Proposições simples e compostas', 'Lógica sentencial', 'Tabela verdade', 'Tautologia, contradição e contingência', 'Argumentos das negações', 'Conjuntos, subconjuntos e operações básicas de conjunto', 'Estatística básica: moda, média, mediana e desvio padrão', 'Grandezas proporcionais, razão e proporção', 'Regra de três', 'Porcentagem'],
        'INFORMÁTICA': ['Juros simples e compostos', 'Família de sistemas operacionais Microsoft Windows para microcomputadores pessoais: interface gráfica, ajuda/suporte e atalhos de teclado', 'Gerenciamento de arquivos e pastas: tipos de arquivos, extensões, pesquisa e localização de conteúdo', 'Configurações e Painel de Controle, incluindo solução de problemas', 'Procedimentos de backup, gerenciamento de impressão', 'Instalação, desinstalação e alteração de programas; ativação/desativação de recursos; configuração de aplicativos', 'Configurações do acesso à internet', 'Aplicativos de escritório (software de edição de texto)', 'Aplicativos de escritório (software cliente de email)', 'Conceitos de organização de dados e bancos de dados', 'Plataforma eletrônica: tipos de dados, criação de planilhas e gráficos, fórmulas aritméticas e funções, configuração da página e impressão, formatação, validação de dados, filtros e dados externos'],
        'LEGISLAÇÃO': ['Ética no serviço público', 'Lei nº 8.429/1992 e alterações', 'Lei nº 9.784/1999 e alterações', 'Lei nº 12.527/2011', 'Decreto nº 1.171/1994', 'Decreto nº 7.210/2010', 'Princípios Fundamentais da CF/88'],
        'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO': ['Atos administrativos: elementos e atributos', 'Agentes públicos, agentes políticos e servidores públicos', 'Noções de gestão de projetos: conceitos básicos e ferramentas', 'Conceitos básicos de administração', 'Noções das funções administrativas: planejamento, organização, direção e controle', 'Conhecimentos básicos de organização, sistemas e métodos (OSM)', 'Gestão por processos e melhoria contínua', 'Ferramentas de gestão da qualidade na administração pública', 'Princípios da Administração Pública', 'Administração direta, indireta e fundacional', 'Orçamento público: elaboração, ciclo orçamentário e finanças públicas (PPA, LDO e LOA)', 'Lei de Responsabilidade Fiscal (LRF)', 'Lei nº 4.320/1964 e suas atualizações', 'Controle na auditoria no setor público: noções de áreas e funções', 'Lei nº 8.112/1990', 'Lei de Improbidade Administrativa (Lei nº 8.429/1992)', 'Código de Ética Profissional do Servidor Público Federal', 'Administração de Materiais e Gestão de Estoques: estrutura, tipos de materiais e classificação', 'Gestão de estoques: recebimento, armazenagem, distribuição e inventários', 'Ferramentas da gestão da qualidade e suas aplicações na Administração Pública'],
    }
    
    data = []
    for materia, conteudos in conteudos_do_edital.items():
        for conteudo in conteudos:
            # Simular status com Feito (1) ou Pendente (0)
            status = 'Feito' if np.random.rand() > 0.5 else 'Pendente'
            data.append({'Matéria': materia, 'Conteúdo': conteudo, 'Status': status})

    return pd.DataFrame(data)

# --- Funções de Autenticação Google Sheets (mantidas) ---
@st.cache_resource
def get_google_auth():
    """Autenticação com Google Sheets"""
    if not GSPREAD_AVAILABLE:
        return None
    
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                  'https://www.googleapis.com/auth/drive']
        credentials_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Obter planilha do Google Sheets"""
    gc = get_google_auth()
    if gc is None:
        return None
    
    try:
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(WORKSHEET_NAME)
    except Exception as e:
        st.error(f"Erro ao acessar planilha: {e}")
        return None

@st.cache_data(ttl=600)
def read_data_from_sheets():
    """Lê dados do Google Sheets ou usa dados de exemplo."""
    worksheet = get_worksheet()
    if worksheet is None:
        return get_sample_data()
    
    try:
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        # Verificar se as colunas essenciais existem
        if df.empty or 'Matéria' not in df.columns or 'Conteúdo' not in df.columns or 'Status' not in df.columns:
            st.warning("A planilha não contém as colunas 'Matéria', 'Conteúdo' e 'Status'. Usando dados de exemplo.")
            return get_sample_data()
            
        return df
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return get_sample_data()

# --- Funções de Processamento de Dados ---
def calculate_weighted_metrics(df_progresso):
    """Calcula métricas de progresso ponderado com base no edital."""
    
    df_edital = pd.DataFrame(ED_DATA)
    
    # Preparar dados de progresso
    df_progresso['Feito'] = df_progresso['Status'].apply(lambda x: 1 if x.strip().lower() == 'feito' else 0)
    df_progresso['Pendente'] = df_progresso['Status'].apply(lambda x: 1 if x.strip().lower() == 'pendente' else 0)
    
    # Agrupar o progresso por matéria
    df_progresso_summary = df_progresso.groupby('Matéria').agg(
        Conteudos_Feitos=('Feito', 'sum'),
        Conteudos_Pendentes=('Pendente', 'sum')
    ).reset_index()
    
    # Unir dados do edital com dados de progresso
    df_final = pd.merge(df_edital, df_progresso_summary, on='Matéria', how='left').fillna(0)
    
    # Calcular métricas ponderadas
    df_final['Pontos_por_Conteudo'] = np.where(df_final['Total_Conteudos'] > 0, df_final['Peso'] / df_final['Total_Conteudos'], 0)
    df_final['Pontos_Concluidos'] = df_final['Conteudos_Feitos'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_Pendentes'] = df_final['Total_Conteudos'] * df_final['Pontos_por_Conteudo'] - df_final['Pontos_Concluidos']
    
    # Calcular progresso ponderado por matéria
    df_final['Progresso_Ponderado'] = np.where(df_final['Peso'] > 0, round(df_final['Pontos_Concluidos'] / df_final['Peso'] * 100, 1), 0)
    
    # Calcular métricas globais
    total_pontos = df_final['Peso'].sum()
    total_pontos_concluidos = df_final['Pontos_Concluidos'].sum()
    progresso_ponderado_geral = round((total_pontos_concluidos / total_pontos) * 100, 1) if total_pontos > 0 else 0
    
    return df_final, progresso_ponderado_geral

# --- Funções de Design (mantidas) ---
def apply_dark_theme_css():
    """Aplicar CSS para tema escuro e clean"""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        html, body, .stApp {
            font-family: 'Poppins', sans-serif;
            background-color: #0d1117; /* GitHub Dark */
            color: #c9d1d9;
        }
        
        .stHeader, .stMetric, .stMarkdown, .stButton, .stProgress, h1, h2, h3 {
            color: #c9d1d9;
        }

        .st-emotion-cache-18ni7ap { /* sidebar header */
            background-color: #0d1117;
        }

        .st-emotion-cache-13sdqmw { /* sidebar */
            background-color: #161b22; /* Darker tone for sidebar */
            border-right: 1px solid #30363d;
        }

        .stButton button {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            font-weight: 600;
        }
        .stButton button:hover {
            background-color: #30363d;
        }

        .metric-label {
            font-weight: 600;
            color: #8b949e;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #58a6ff; /* Azul vibrante */
        }

        .countdown {
            font-size: 1.5rem;
            font-weight: 600;
            color: #58a6ff;
            text-shadow: none;
        }

        .st-emotion-cache-1r6ilae {
             border-bottom: 1px solid #30363d;
             margin-bottom: 1.5rem;
        }

        /* Títulos */
        h1 { font-size: 2.5rem; font-weight: 700; }
        h2 { font-size: 2rem; font-weight: 600; }
        h3 { font-size: 1.5rem; font-weight: 600; color: #8b949e; }
        
        </style>
    """, unsafe_allow_html=True)

# --- Funções de Gráficos Altair ---
def create_altair_donut_chart(data_row):
    """Cria um gráfico de rosca com Altair para uma disciplina."""
    df_chart = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Pontos': [data_row['Pontos_Concluidos'], data_row['Pontos_Pendentes']]
    })
    
    base = alt.Chart(df_chart).encode(
        theta=alt.Theta("Pontos:Q", stack=True)
    )
    
    pie = base.mark_arc(outerRadius=120, innerRadius=80).encode(
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#58a6ff', '#f85149'])),
        order=alt.Order("Pontos", sort="descending"),
        tooltip=["Status", "Pontos:Q"]
    )
    
    text_progresso = alt.Chart(pd.DataFrame({'text': [f"{data_row['Progresso_Ponderado']}%"]})).mark_text(
        align='center',
        baseline='middle',
        fontSize=40,
        fontWeight='bold',
        color='#c9d1d9'
    ).encode(
        text=alt.Text('text:N')
    )

    return (pie + text_progresso).properties(
        title=data_row['Matéria']
    ).resolve_scale(
        color='independent'
    )

def create_altair_bubble_chart(df_summary):
    """Cria um gráfico de bolhas para priorização de estudo."""
    chart = alt.Chart(df_summary).mark_circle().encode(
        x=alt.X('Total_Conteudos:Q', title='Total de Conteúdos', axis=alt.Axis(grid=True)),
        y=alt.Y('Peso:Q', title='Peso da Disciplina'),
        size=alt.Size('Porcentagem_Pontos:Q', title='Pontuação Total (%)', scale=alt.Scale(range=[100, 1000])),
        color=alt.Color('Matéria:N', legend=None),
        tooltip=['Matéria', 'Total_Conteudos', 'Peso', 'Porcentagem_Pontos:Q']
    ).properties(
        title='Prioridade de Estudo (Conteúdos x Peso)'
    ).interactive()
    return chart

def create_altair_bar_chart_conteudo(df_summary):
    """Cria um gráfico de barras empilhadas para o progresso de conteúdos."""
    df_melted = df_summary.melt(
        'Matéria', 
        var_name='Status', 
        value_name='Conteudos', 
        value_vars=['Conteudos_Feitos', 'Conteudos_Pendentes']
    )
    
    chart = alt.Chart(df_melted).mark_bar().encode(
        x=alt.X('Conteudos:Q', title='Conteúdos'),
        y=alt.Y('Matéria:N', sort='-x', title='Disciplina'),
        color=alt.Color('Status:N', 
                        scale=alt.Scale(domain=['Conteudos_Feitos', 'Conteudos_Pendentes'], range=['#58a6ff', '#f85149']),
                        legend=alt.Legend(title="Status")),
        tooltip=['Matéria', 'Status', 'Conteudos']
    ).properties(
        title="Progresso por Conteúdo Concluído"
    )
    
    return chart

# --- Configuração da Página e CSS ---
st.set_page_config(
    page_title="Dashboard TAE UFG - Progresso de Estudos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_dark_theme_css()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🎯 Filtros e Configurações")
    
    disciplinas_disponiveis = [m for m in ED_DATA['Matéria']]
    disciplinas_selecionadas = st.multiselect(
        "Selecione as disciplinas:",
        disciplinas_disponiveis,
        default=disciplinas_disponiveis
    )
    
    st.markdown("---")
    
    st.markdown("### 🔄 Atualização")
    if st.button("Atualizar Dados", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- Cabeçalho ---
dias_restantes = (CONCURSO_DATE - datetime.now()).days
status_concurso = f"{dias_restantes} DIAS RESTANTES" if dias_restantes >= 0 else "CONCURSO REALIZADO"

st.markdown(f"""
<h1 style='text-align: center;'>📊 DASHBOARD TAE UFG</h1>
<p style='text-align: center; font-size: 1.2rem;'>Progresso do Edital • <span class='countdown'>{status_concurso}</span></p>
<hr style='border-top: 1px solid #30363d;'>
""", unsafe_allow_html=True)

# --- Carregar e Processar Dados ---
df_progresso = read_data_from_sheets()

if not df_progresso.empty:
    df_final, progresso_ponderado_geral = calculate_weighted_metrics(df_progresso)
    
    # Filtrar dados para exibição
    df_final_filtered = df_final[df_final['Matéria'].isin(disciplinas_selecionadas)]
    
    # --- Métricas Principais ---
    col1, col2, col3 = st.columns(3)
    
    total_conteudos_feito = df_progresso['Feito'].sum()
    total_conteudos_pendente = df_progresso['Pendente'].sum()
    
    with col1:
        st.metric(label="📚 Conteúdos Concluídos", value=f"{int(total_conteudos_feito)}")
    with col2:
        st.metric(label="⏳ Conteúdos Pendentes", value=f"{int(total_conteudos_pendente)}")
    with col3:
        st.metric(label="✅ Progresso Ponderado", value=f"{progresso_ponderado_geral}%")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Visualizações de Progresso (Altair) ---
    st.markdown("### Progresso por Disciplina (Ponderado)")
    cols_charts = st.columns(df_final_filtered.shape[0])
    
    for idx, (_, row) in enumerate(df_final_filtered.iterrows()):
        with cols_charts[idx % len(cols_charts)]:
            chart = create_altair_donut_chart(row)
            st.altair_chart(chart, use_container_width=True)

    # --- Análise Estratégica ---
    st.markdown("### Análise de Prioridade de Estudo")
    
    df_strategy = pd.DataFrame(ED_DATA)
    total_peso_geral = df_strategy['Peso'].sum()
    df_strategy['Porcentagem_Pontos'] = round((df_strategy['Peso'] / total_peso_geral) * 100, 1)

    chart_bubble = create_altair_bubble_chart(df_strategy)
    st.altair_chart(chart_bubble, use_container_width=True)

    # --- Gráfico de Barras por Conteúdo ---
    st.markdown("### Conteúdos Concluídos por Disciplina")
    
    chart_bar_conteudo = create_altair_bar_chart_conteudo(df_final_filtered)
    st.altair_chart(chart_bar_conteudo, use_container_width=True)

    st.markdown("<hr style='border-top: 1px solid #30363d;'>", unsafe_allow_html=True)
    
    # --- Tabela Detalhada ---
    st.markdown("### Tabela de Progresso por Conteúdo")
    
    st.dataframe(
        df_progresso[['Matéria', 'Conteúdo', 'Status']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")

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
