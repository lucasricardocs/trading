
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
    st.warning("⚠️ Biblioteca gspread não encontrada. Usando dados de exemplo.")

# --- Configurações ---
# ATENÇÃO: SUBSTITUA COM SEUS DADOS REAIS
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM' # ID da sua planilha
WORKSHEET_NAME_DADOS = 'Planilha1' # Nome da aba da análise de conteúdo
CONCURSO_DATE = datetime(2025, 9, 28) # Data do concurso

# Dados do edital (para calcular o progresso ponderado)
ED_DATA = {
    'Matéria': [
        'LÍNGUA PORTUGUESA', 
        'RLM', 
        'INFORMÁTICA', 
        'LEGISLAÇÃO', 
        'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO'
    ],
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
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials_dict = st.secrets.get("google_credentials")
        if not credentials_dict:
            st.warning("Credenciais do Google não encontradas. Usando dados de exemplo.")
            return None
        
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return None

@st.cache_data(ttl=600)
def read_dados_from_sheets():
    """Lê dados da aba 'Planilha1' do Google Sheets ou usa dados de exemplo."""
    
    # Se não há conexão com Google Sheets, usar dados de exemplo
    if not GSPREAD_AVAILABLE or not st.secrets.get("google_credentials"):
        st.info("⚠️ Usando dados de exemplo. Configure as credenciais do Google Sheets para usar seus dados reais.")
        
        # Dados de exemplo mais realistas
        conteudos_do_edital = {
            'LÍNGUA PORTUGUESA': [
                'Compreensão e interpretação de textos',
                'Tipologia textual',
                'Ortografia oficial',
                'Acentuação gráfica',
                'Emprego das classes de palavras',
                'Emprego do sinal indicativo de crase',
                'Sintaxe da oração e do período',
                'Pontuação',
                'Concordância nominal e verbal',
                'Regência nominal e verbal',
                'Significação das palavras',
                'Redação (confronto e reconhecimento de frases corretas e incorretas)'
            ],
            'RLM': [
                'Estruturas lógicas',
                'Lógica de argumentação',
                'Diagramas lógicos',
                'Resolução de situações-problema',
                'Raciocínio lógico envolvendo problemas aritméticos',
                'Raciocínio sequencial',
                'Orientações espacial e temporal',
                'Formação de conceitos',
                'Discriminação de elementos'
            ],
            'INFORMÁTICA': [
                'MS-Windows 7 ou versões mais recentes',
                'MS-Office 2010 ou versões mais recentes',
                'Conceitos básicos sobre Linux',
                'Conceitos organizacionais de arquivos e métodos de acesso',
                'Conceitos de proteção e segurança',
                'Vírus e antivírus',
                'Internet e correio eletrônico'
            ],
            'LEGISLAÇÃO': [
                'Lei nº 8.112/90 e suas alterações',
                'Lei nº 11.091/2005',
                'Decreto nº 5.825/2006',
                'Lei nº 9.394/96',
                'Constituição Federal/88 (arts. 205 a 214)',
                'Lei nº 8.429/92',
                'Lei nº 12.527/11'
            ],
            'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO': [
                'Noções de Administração',
                'Características básicas das organizações',
                'Tipos de estrutura organizacional',
                'Natureza e finalidades das organizações',
                'Gestão de processos',
                'Gestão de contratos',
                'Noções de gestão de pessoas',
                'Gestão de material e patrimônio',
                'Noções de arquivologia',
                'Noções de gestão financeira',
                'Licitações e contratos administrativos',
                'Controle interno e externo'
            ]
        }
        
        # Simular dados com status mais realístico
        sample_data = []
        np.random.seed(42)  # Para reproduzibilidade
        
        for materia, conteudos in conteudos_do_edital.items():
            for conteudo in conteudos:
                # Probabilidade diferente para cada matéria
                prob_feito = {
                    'LÍNGUA PORTUGUESA': 0.7,
                    'RLM': 0.5,
                    'INFORMÁTICA': 0.8,
                    'LEGISLAÇÃO': 0.4,
                    'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO': 0.3
                }.get(materia, 0.5)
                
                status = 'Feito' if np.random.rand() < prob_feito else 'Pendente'
                sample_data.append({
                    'Matéria': materia, 
                    'Conteúdo': conteudo, 
                    'Status': status
                })
        
        return pd.DataFrame(sample_data)

    # Tentar ler do Google Sheets
    try:
        gc = get_google_auth()
        if not gc:
            return pd.DataFrame()
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME_DADOS)
        
        # CORREÇÃO: Usar get_all_values() para evitar o erro de cabeçalho duplicado
        data = worksheet.get_all_values()
        if not data:
            st.warning("Planilha está vazia. Verifique se há dados na aba especificada.")
            return pd.DataFrame()
        
        headers = data[0]
        records = data[1:]
        
        df = pd.DataFrame(records, columns=headers)
        
        # Validação básica dos dados
        required_columns = ['Matéria', 'Conteúdo', 'Status']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Colunas obrigatórias não encontradas: {missing_columns}. Verifique o nome das colunas na planilha.")
            return pd.DataFrame()
        
        # Limpeza dos dados
        df['Status'] = df['Status'].astype(str).str.strip()
        df = df[df['Status'].isin(['Feito', 'Pendente'])]
        
        return df
        
    except gspread.WorksheetNotFound:
        st.error(f"Aba '{WORKSHEET_NAME_DADOS}' não encontrada na planilha.")
        return pd.DataFrame()
    except gspread.SpreadsheetNotFound:
        st.error("Planilha não encontrada. Verifique o ID da planilha.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        st.exception(e) # Exibe o traceback completo para depuração
        return pd.DataFrame()

# --- Funções de Processamento de Dados ---
def calculate_weighted_metrics(df_dados):
    """Calcula métricas de progresso ponderado com base no edital."""
    df_edital = pd.DataFrame(ED_DATA)
    
    # Verifica se as colunas essenciais existem
    if df_dados.empty or 'Matéria' not in df_dados.columns or 'Status' not in df_dados.columns:
        st.error("Dados insuficientes para calcular métricas.")
        return pd.DataFrame(), 0.0

    # Preparação dos dados
    df_dados = df_dados.copy()
    df_dados['Status'] = df_dados['Status'].astype(str).str.strip()
    df_dados['Feito'] = (df_dados['Status'].str.lower() == 'feito').astype(int)
    df_dados['Pendente'] = (df_dados['Status'].str.lower() == 'pendente').astype(int)
    
    # Agregação por matéria
    df_progresso_summary = df_dados.groupby('Matéria').agg(
        Conteudos_Feitos=('Feito', 'sum'),
        Conteudos_Pendentes=('Pendente', 'sum')
    ).reset_index()
    
    # Merge com dados do edital
    df_final = pd.merge(df_edital, df_progresso_summary, on='Matéria', how='left').fillna(0)
    
    # Cálculos de pontuação ponderada
    df_final['Total_Conteudos_Real'] = df_final['Conteudos_Feitos'] + df_final['Conteudos_Pendentes']
    df_final['Pontos_por_Conteudo'] = np.where(
        df_final['Total_Conteudos'] > 0, 
        df_final['Peso'] / df_final['Total_Conteudos'], 
        0
    )
    df_final['Pontos_Concluidos'] = df_final['Conteudos_Feitos'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_Totais'] = df_final['Total_Conteudos'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_Pendentes'] = df_final['Pontos_Totais'] - df_final['Pontos_Concluidos']
    
    df_final['Progresso_Ponderado'] = np.where(
        df_final['Peso'] > 0, 
        np.round(df_final['Pontos_Concluidos'] / df_final['Peso'] * 100, 1), 
        0
    )
    
    # Progresso geral
    total_pontos = df_final['Peso'].sum()
    total_pontos_concluidos = df_final['Pontos_Concluidos'].sum()
    progresso_ponderado_geral = round(
        (total_pontos_concluidos / total_pontos) * 100, 1
    ) if total_pontos > 0 else 0
    
    return df_final, progresso_ponderado_geral

# --- Funções de Design e Gráficos ---
def apply_light_theme_css():
    """Aplica CSS para tema limpo e profissional."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        
        .metric-container {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .countdown {
            font-size: 1.1rem;
            font-weight: 500;
            color: #667eea;
            background: rgba(102, 126, 234, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            display: inline-block;
        }
        
        .stMetric > div > div:first-child {
            font-size: 0.9rem;
            font-weight: 500;
            color: #666;
        }
        
        .stMetric > div > div:nth-child(2) {
            font-size: 2rem;
            font-weight: 700;
            color: #667eea;
        }
        
        .section-header {
            font-size: 1.3rem;
            font-weight: 600;
            color: #2c3e50;
            margin: 2rem 0 1rem 0;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 0.5rem;
        }
        
        div[data-testid="stExpander"] {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
        }
        
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #666;
            border-top: 1px solid #eee;
            margin-top: 3rem;
        }
        </style>
    """, unsafe_allow_html=True)

def create_altair_donut_chart(data_row):
    """Cria um gráfico de rosca melhorado."""
    df_chart = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'], 
        'Pontos': [data_row['Pontos_Concluidos'], data_row['Pontos_Pendentes']]
    })
    
    base = alt.Chart(df_chart).encode(
        theta=alt.Theta("Pontos:Q", stack=True)
    )
    
    pie = base.mark_arc(
        outerRadius=85, 
        innerRadius=55, 
        stroke="white", 
        strokeWidth=3
    ).encode(
        color=alt.Color(
            "Status:N", 
            scale=alt.Scale(
                domain=['Concluído', 'Pendente'], 
                range=['#667eea', '#e74c3c']
            ),
            legend=None
        ),
        tooltip=["Status:N", alt.Tooltip("Pontos:Q", format=".2f")]
    )
    
    # Texto central
    text_progresso = alt.Chart(
        pd.DataFrame({'text': [f"{data_row['Progresso_Ponderado']:.1f}%"]})
    ).mark_text(
        align='center', 
        baseline='middle', 
        fontSize=20, 
        fontWeight='bold', 
        color='#2c3e50'
    ).encode(text=alt.Text('text:N'))
    
    return (pie + text_progresso).properties(
        title=alt.TitleParams(
            text=data_row['Matéria'], 
            fontSize=14, 
            fontWeight='bold',
            anchor='start'
        ),
        width=200,
        height=200
    ).resolve_scale(color='independent')

def create_altair_bar_chart(df_summary):
    """Cria gráfico de barras horizontal melhorado."""
    df_melted = df_summary.melt(
        id_vars=['Matéria'], 
        value_vars=['Conteudos_Feitos', 'Conteudos_Pendentes'],
        var_name='Status', 
        value_name='Conteudos'
    )
    
    # Mapear nomes para exibição
    df_melted['Status_Display'] = df_melted['Status'].map({
        'Conteudos_Feitos': 'Concluído',
        'Conteudos_Pendentes': 'Pendente'
    })
    
    chart = alt.Chart(df_melted).mark_bar(
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X('Conteudos:Q', title='Número de Conteúdos'),
        y=alt.Y('Matéria:N', sort='-x', title=''),
        color=alt.Color(
            'Status_Display:N',
            scale=alt.Scale(
                domain=['Concluído', 'Pendente'],
                range=['#667eea', '#e74c3c']
            ),
            legend=alt.Legend(title="Status", orient="top")
        ),
        tooltip=['Matéria:N', 'Status_Display:N', 'Conteudos:Q']
    ).properties(
        title="Progresso por Disciplina",
        height=300
    )
    
    return chart

def create_priority_chart(df_summary):
    """Cria gráfico de prioridade baseado em peso vs progresso."""
    # Calcular pontuação de prioridade (quanto menor o progresso e maior o peso, maior a prioridade)
    df_priority = df_summary.copy()
    df_priority['Prioridade'] = (100 - df_priority['Progresso_Ponderado']) * df_priority['Peso'] / 100
    
    chart = alt.Chart(df_priority).mark_circle(
        size=200,
        stroke='white',
        strokeWidth=2
    ).encode(
        x=alt.X('Progresso_Ponderado:Q', title='Progresso Atual (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('Peso:Q', title='Peso da Disciplina'),
        size=alt.Size('Prioridade:Q', title='Prioridade', scale=alt.Scale(range=[100, 400])),
        color=alt.Color('Prioridade:Q', scale=alt.Scale(scheme='reds'), legend=None),
        tooltip=['Matéria:N', 'Progresso_Ponderado:Q', 'Peso:Q', 'Prioridade:Q']
    ).properties(
        title="Matriz de Prioridade de Estudo",
        width=400,
        height=300
    )
    
    return chart

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard TAE UFG", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_light_theme_css()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🎯 Dashboard TAE UFG")
    st.markdown("---")
    
    # Informações do concurso
    dias_restantes = (CONCURSO_DATE - datetime.now()).days
    
    if dias_restantes > 0:
        st.success(f"🗓️ **{dias_restantes} dias** para o concurso")
        
        # Cálculo de dias úteis aproximado (5/7 dos dias)
        dias_uteis = int(dias_restantes * 5/7)
        st.info(f"📅 Aproximadamente **{dias_uteis} dias úteis**")
    else:
        st.warning("🎯 Concurso já realizado")
    
    st.markdown("---")
    
    # Controles
    if st.button("🔄 Atualizar Dados", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Informações adicionais
    with st.expander("ℹ️ Informações"):
        st.markdown("""
        **Pesos das Disciplinas:**
        - Língua Portuguesa: 2
        - RLM: 1  
        - Informática: 1
        - Legislação: 1
        - Conhecimentos Específicos: 3
        
        **Como usar:**
        1. Mantenha sua planilha atualizada
        2. Use 'Feito' ou 'Pendente' na coluna Status
        3. Clique em 'Atualizar Dados' para sincronizar
        """)

# --- Header Principal ---
st.markdown("""
<div class="main-header">
    <h1>📊 Dashboard TAE UFG</h1>
    <p>Acompanhamento do Progresso de Estudos</p>
</div>
""", unsafe_allow_html=True)

# --- Conteúdo Principal ---
df_dados = read_dados_from_sheets()

if not df_dados.empty:
    df_final, progresso_ponderado_geral = calculate_weighted_metrics(df_dados)
    
    # Métricas principais
    st.markdown('<div class="section-header">📈 Resumo Geral</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_conteudos_feito = df_dados[df_dados['Status'].str.lower() == 'feito'].shape[0]
    total_conteudos_pendente = df_dados[df_dados['Status'].str.lower() == 'pendente'].shape[0]
    total_conteudos = total_conteudos_feito + total_conteudos_pendente
    
    with col1:
        st.metric(
            label="🎯 Progresso Geral", 
            value=f"{progresso_ponderado_geral:.1f}%"
        )
    
    with col2:
        st.metric(
            label="✅ Conteúdos Feitos", 
            value=f"{total_conteudos_feito}"
        )
    
    with col3:
        st.metric(
            label="⏳ Conteúdos Pendentes", 
            value=f"{total_conteudos_pendente}"
        )
    
    with col4:
        taxa_conclusao = (total_conteudos_feito / total_conteudos * 100) if total_conteudos > 0 else 0
        st.metric(
            label="📊 Taxa de Conclusão", 
            value=f"{taxa_conclusao:.1f}%"
        )
    
    st.markdown("---")
    
    # Filtro de disciplinas
    st.markdown('<div class="section-header">🎨 Personalizar Visualização</div>', unsafe_allow_html=True)
    
    disciplinas_disponiveis = list(df_final['Matéria'].unique())
    disciplinas_selecionadas = st.multiselect(
        "Selecione as disciplinas para visualização:",
        disciplinas_disponiveis,
        default=disciplinas_disponiveis,
        help="Escolha quais disciplinas exibir nos gráficos"
    )
    
    if disciplinas_selecionadas:
        df_final_filtered = df_final[df_final['Matéria'].isin(disciplinas_selecionadas)]
        
        # Gráficos de rosca por disciplina
        st.markdown('<div class="section-header">🎯 Progresso por Disciplina</div>', unsafe_allow_html=True)
        
        # Organizar em linhas de até 3 colunas
        num_cols = min(3, len(df_final_filtered))
        rows = []
        for i in range(0, len(df_final_filtered), num_cols):
            rows.append(df_final_filtered.iloc[i:i+num_cols])
        
        for row_data in rows:
            cols = st.columns(num_cols)
            for idx, (_, row) in enumerate(row_data.iterrows()):
                with cols[idx]:
                    chart = create_altair_donut_chart(row)
                    st.altair_chart(chart, use_container_width=True)
        
        st.markdown("---")
        
        # Gráficos de análise
        st.markdown('<div class="section-header">📊 Análise Detalhada</div>', unsafe_allow_html=True)
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            chart_bar = create_altair_bar_chart(df_final_filtered)
            st.altair_chart(chart_bar, use_container_width=True)
        
        with col_right:
            chart_priority = create_priority_chart(df_final_filtered)
            st.altair_chart(chart_priority, use_container_width=True)
        
        # Tabela detalhada
        with st.expander("📋 Dados Detalhados", expanded=False):
            st.markdown("**Resumo por Disciplina:**")
            
            # Preparar tabela de resumo
            display_columns = [
                'Matéria', 'Conteudos_Feitos', 'Conteudos_Pendentes', 
                'Progresso_Ponderado', 'Peso'
            ]
            df_display = df_final_filtered[display_columns].copy()
            df_display.columns = [
                'Disciplina', 'Feitos', 'Pendentes', 
                'Progresso (%)', 'Peso'
            ]
            
            st.dataframe(
                df_display, 
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("**Todos os Conteúdos:**")
            st.dataframe(
                df_dados[df_dados['Matéria'].isin(disciplinas_selecionadas)], 
                use_container_width=True,
                hide_index=True
            )
    
    else:
        st.info("Selecione pelo menos uma disciplina para visualizar os dados.")

else:
    st.error("❌ Não foi possível carregar os dados. Verifique sua conexão e configurações.")
    st.markdown("""
    **Possíveis soluções:**
    1. Verifique se o ID da planilha está correto
    2. Confirme se a aba 'Planilha1' existe
    3. Verifique as permissões de acesso à planilha
    4. Confirme se as credenciais do Google estão configuradas corretamente
    """)

# --- Rodapé ---
st.markdown("""
<div class="footer">
    <p>
        🚀 Dashboard desenvolvido com Streamlit | 
        📊 Concurso TAE UFG 2025 |
        💡 Acompanhe seu progresso de forma inteligente
    </p>
</div>
""", unsafe_allow_html=True)
```
