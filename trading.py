# -- coding: utf-8 --
import streamlit as st
import gspread
import pandas as pd
import altair as alt
from google.oauth2.service_account import Credentials

# --- Configurações Atualizadas ---
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'
WORKSHEET_NAME = 'Página1'  # Nome padrão da planilha

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

# --- Interface do Dashboard ---
st.set_page_config(
    page_title="Progresso TAE UFG",
    page_icon="📚",
    layout="wide"
)

# Cabeçalho personalizado
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600&display=swap');
.header {
    font-family: 'Montserrat', sans-serif;
    color: #1e3a8a;
    text-align: center;
    padding: 1rem;
    border-radius: 10px;
    background: linear-gradient(90deg, #f0f9ff, #e0f2fe);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    text-align: center;
    transition: transform 0.3s;
}
.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header"><h1>🚀 PROGRESSO DE ESTUDOS - CONCURSO TAE UFG</h1></div>', unsafe_allow_html=True)

# Carregar dados
df = read_data()

if not df.empty:
    # Verificar e renomear colunas
    if len(df.columns) >= 5:
        df = df.iloc[:, [0, 3, 4]]  # Colunas A, D, E
        df.columns = ['Disciplina', 'Feito', 'Pendente']
        
        # Converter para numérico
        df['Feito'] = pd.to_numeric(df['Feito'], errors='coerce').fillna(0)
        df['Pendente'] = pd.to_numeric(df['Pendente'], errors='coerce').fillna(0)
        
        # Calcular métricas totais
        total_feito = int(df['Feito'].sum())
        total_pendente = int(df['Pendente'].sum())
        total_questoes = total_feito + total_pendente
        percentual = round((total_feito / total_questoes * 100) if total_questoes > 0 else 0, 1)
        
        # Mostrar métricas
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="metric-card"><h3>✅ Feito</h3><h2 style="color:#2563eb">{total_feito}</h2></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric-card"><h3>⏳ Pendente</h3><h2 style="color:#f59e0b">{total_pendente}</h2></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric-card"><h3>📊 Progresso</h3><h2 style="color:#10b981">{percentual}%</h2></div>', unsafe_allow_html=True)
        
        # Gráficos em rosca animados
        st.markdown("---")
        st.subheader("Distribuição por Disciplina")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de Feito com animação
            feito_chart = alt.Chart(df).mark_arc(innerRadius=70).encode(
                theta=alt.Theta('Feito:Q', title="Questões Feitas"),
                color=alt.Color('Disciplina:N', 
                               legend=alt.Legend(title="Disciplinas"),
                               scale=alt.Scale(scheme='blues')),
                tooltip=['Disciplina', 'Feito'],
                order=alt.Order('Feito:Q', sort='descending')
            ).properties(
                title='Questões Concluídas',
                height=400
            ).interactive()
            
            st.altair_chart(feito_chart, use_container_width=True)
        
        with col2:
            # Gráfico de Pendente com animação
            pendente_chart = alt.Chart(df).mark_arc(innerRadius=70).encode(
                theta=alt.Theta('Pendente:Q', title="Questões Pendentes"),
                color=alt.Color('Disciplina:N', 
                               legend=alt.Legend(title="Disciplinas"),
                               scale=alt.Scale(scheme='oranges')),
                tooltip=['Disciplina', 'Pendente'],
                order=alt.Order('Pendente:Q', sort='descending')
            ).properties(
                title='Questões Pendentes',
                height=400
            ).interactive()
            
            st.altair_chart(pendente_chart, use_container_width=True)
        
        # Tabela detalhada
        st.markdown("---")
        st.subheader("Detalhamento por Disciplina")
        df['Progresso (%)'] = round((df['Feito'] / (df['Feito'] + df['Pendente'])) * 100, 1)
        df = df.sort_values('Progresso (%)', ascending=False)
        st.dataframe(df.style.background_gradient(subset=['Progresso (%)'], cmap='YlGn'),
                    use_container_width=True,
                    hide_index=True)
        
        # Progresso geral
        st.markdown("---")
        st.subheader("Progresso Geral")
        progress_bar = st.progress(0)
        for i in range(int(percentual) + 1):
            progress_bar.progress(i)
            time.sleep(0.02)  # Efeito de animação
        
        st.metric(label="Conclusão Total", value=f"{percentual}%")
        
    else:
        st.error("A planilha não possui colunas suficientes. Verifique a estrutura dos dados.")
else:
    st.warning("Nenhum dado encontrado na planilha. Verifique a conexão e os dados.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido para acompanhamento de estudos - Concurso TAE UFG | Atualizado automaticamente")
