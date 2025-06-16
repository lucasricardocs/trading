# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
import io

# --- Configurações e Constantes ---
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'
HEADER_ROW_INDEX = 4  # Linha 5 do arquivo, que é o índice 4

# Cores para os gráficos
WIN_COLOR = '#2ECC71'
LOSS_COLOR = '#E74C3C'
PRIMARY_COLOR = '#3498db'
GRAY_LIGHT = '#F5F5F5'
GRAY_DARK = '#E0E0E0'
HEATMAP_RANGE = ['#8B0000', '#CD5C5C', GRAY_DARK, '#90EE90', '#006400']


# --- Conexão com Google Sheets ---
@st.cache_resource
def get_gspread_client():
    """Autoriza e retorna um cliente gspread para interagir com o Google Sheets."""
    try:
        credentials_info = dict(st.secrets["google_credentials"])
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Erro na autenticação com Google API: {e}")
        st.warning("Verifique se as credenciais 'google_credentials' estão configuradas nos segredos do Streamlit.")
        return None


# --- Carregamento e Processamento de Dados ---
@st.cache_data
def load_data(uploaded_file):
    """
    Lê um arquivo CSV, tenta diferentes encodings, processa e retorna um DataFrame.
    A função é cacheada para evitar reprocessamento do mesmo arquivo.
    """
    encodings_to_try = ['latin-1', 'cp1252', 'iso-8859-1', 'utf-8']
    
    for encoding in encodings_to_try:
        try:
            uploaded_file.seek(0)
            content = uploaded_file.read().decode(encoding)
            
            # Utiliza pandas para ler o CSV a partir do conteúdo decodificado
            df = pd.read_csv(
                io.StringIO(content),
                sep=';',
                header=HEADER_ROW_INDEX,
                skipinitialspace=True
            )
            
            # Limpeza e processamento do DataFrame
            df.columns = df.columns.str.strip()
            df = df.dropna(how='all') # Remove linhas completamente vazias

            # Identificar colunas essenciais
            date_col = next((col for col in df.columns if 'Abertura' in col or 'Data' in col), None)
            total_col = next((col for col in df.columns if 'Total' in col), None)

            if not date_col or not total_col:
                st.error("Não foi possível encontrar as colunas 'Abertura'/'Data' ou 'Total' no arquivo.")
                return None

            # Conversão e limpeza de dados
            df['Data'] = pd.to_datetime(df[date_col].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
            
            # Converte a coluna 'Total' para numérico
            total_series = df[total_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df['Total'] = pd.to_numeric(total_series, errors='coerce').fillna(0)

            df = df.dropna(subset=['Data'])
            
            # Agrupar por data para consolidar os resultados diários
            daily_data = df.groupby('Data')['Total'].sum().reset_index()
            
            return daily_data

        except Exception:
            continue
            
    st.error("Falha ao ler o arquivo. Nenhum encoding compatível encontrado ou formato de arquivo inválido.")
    return None

# --- Integração com Google Sheets ---
def copy_df_to_sheets(df, filename):
    """Copia um DataFrame para uma aba específica no Google Sheets."""
    gc = get_gspread_client()
    if not gc:
        return False

    try:
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        sheet_name = filename.replace('.csv', '')[:31]  # Nome da aba com limite de caracteres

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear() # Limpa a aba para inserir dados novos
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=30)
        
        # Prepara dados para atualização (cabeçalho + linhas)
        data_to_upload = [df.columns.values.tolist()] + df.astype(str).values.tolist()
        worksheet.update('A1', data_to_upload, value_input_option='USER_ENTERED')
        
        st.success(f"✅ Dados atualizados com sucesso na aba '{sheet_name}'!")
        return True
    
    except Exception as e:
        st.error(f"Ocorreu um erro ao enviar os dados para o Google Sheets: {e}")
        return False

# --- Funções de Criação de Gráficos ---

def create_line_chart(df):
    """Cria um gráfico de linha com a evolução do resultado acumulado."""
    if df is None or df.empty:
        return None
    
    df_sorted = df.sort_values('Data').copy()
    df_sorted['Acumulado'] = df_sorted['Total'].cumsum()
    
    chart = alt.Chart(df_sorted).mark_line(
        point=True, strokeWidth=2
    ).encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Acumulado:Q', title='Resultado Acumulado (R$)'),
        color=alt.value(PRIMARY_COLOR),
        tooltip=[
            alt.Tooltip('Data:T', format='%d/%m/%Y'),
            alt.Tooltip('Total:Q', format=',.2f', title='Resultado do Dia'),
            alt.Tooltip('Acumulado:Q', format=',.2f', title='Acumulado')
        ]
    ).properties(height=400, title="Evolução dos Resultados")
    
    return chart

def create_accuracy_radial_chart(df):
    """Cria um gráfico radial (pizza) com a taxa de acerto (dias positivos vs. negativos)."""
    if df is None or df.empty:
        return None
        
    winning_days = (df['Total'] > 0).sum()
    total_days = len(df)
    accuracy_rate = (winning_days / total_days) * 100 if total_days > 0 else 0
    
    data = pd.DataFrame({
        'category': ['Positivos', 'Negativos'],
        'value': [accuracy_rate, 100 - accuracy_rate],
        'color': [WIN_COLOR, LOSS_COLOR]
    })
    
    chart = alt.Chart(data).mark_arc(innerRadius=60, outerRadius=90).encode(
        theta=alt.Theta('value:Q'),
        color=alt.Color('color:N', scale=None),
        tooltip=[
            alt.Tooltip('category:N', title='Tipo'),
            alt.Tooltip('value:Q', format='.1f', title='Percentual (%)')
        ]
    ).properties(
        height=220,
        title=f'{accuracy_rate:.1f}% de Dias Positivos'
    )
    return chart

def create_trading_heatmap(df):
    """Cria um heatmap de atividade de trading similar ao do GitHub."""
    if df.empty:
        return None

    current_year = df['Data'].dt.year.max()
    df_year = df[df['Data'].dt.year == current_year].copy()

    # Cria um calendário completo para o ano
    all_dates = pd.date_range(start=f'{current_year}-01-01', end=f'{current_year}-12-31', freq='D')
    full_df = pd.DataFrame({'Data': all_dates})
    full_df = full_df.merge(df_year, on='Data', how='left')

    full_df['Total'] = full_df['Total'].fillna(0) # Dias sem dados ficam com 0
    full_df['week'] = full_df['Data'].dt.isocalendar().week
    full_df['day_of_week'] = full_df['Data'].dt.day_name()
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    max_abs_val = max(abs(df_year['Total'].min()), df_year['Total'].max()) if not df_year.empty else 1

    chart = alt.Chart(full_df).mark_rect(stroke='white', strokeWidth=2).encode(
        x=alt.X('week:O', title=None, axis=None),
        y=alt.Y('day_of_week:O', sort=day_order, title=None),
        color=alt.condition(
            alt.datum.Total == 0,
            alt.value(GRAY_LIGHT),
            alt.Color('Total:Q',
                      scale=alt.Scale(domain=[-max_abs_val, 0, max_abs_val], range=[LOSS_COLOR, GRAY_DARK, WIN_COLOR]),
                      legend=alt.Legend(title="Resultado", orient='bottom'))
        ),
        tooltip=[
            alt.Tooltip('Data:T', format='%d/%m/%Y'),
            alt.Tooltip('day_of_week:N', title='Dia'),
            alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
        ]
    ).properties(height=150, title=f'Atividade de Trading - {current_year}')
    
    return chart

# --- Interface Principal ---
def main():
    st.title("Dashboard de Análise de Trades")
    st.markdown("Faça o upload do seu relatório de performance em formato `.csv` para visualizar as análises.")

    uploaded_file = st.file_uploader(
        "Selecione o arquivo CSV",
        type=['csv'],
        help="O arquivo deve ter um cabeçalho na linha 5 e os dados começando na linha 6."
    )
    
    if uploaded_file:
        processed_data = load_data(uploaded_file)
        
        if processed_data is not None and not processed_data.empty:
            st.header("Visão Geral dos Resultados")

            # --- Métricas Principais ---
            col1, col2, col3, col4 = st.columns(4)
            total_result = processed_data['Total'].sum()
            avg_result = processed_data['Total'].mean()
            positive_days = (processed_data['Total'] > 0).sum()
            
            col1.metric("Resultado Total", f"R$ {total_result:,.2f}", delta_color="off")
            col2.metric("Dias Operados", len(processed_data))
            col3.metric("Dias Positivos", f"{positive_days}")
            col4.metric("Média Diária", f"R$ {avg_result:,.2f}")

            # --- Heatmap ---
            st.subheader("Heatmap de Atividade Anual")
            heatmap = create_trading_heatmap(processed_data)
            if heatmap:
                st.altair_chart(heatmap, use_container_width=True)

            # --- Gráficos Principais ---
            col_left, col_right = st.columns([2, 1])
            with col_left:
                line_chart = create_line_chart(processed_data)
                if line_chart:
                    st.altair_chart(line_chart, use_container_width=True)
            
            with col_right:
                st.subheader("Taxa de Acerto (Dias)")
                radial_chart = create_accuracy_radial_chart(processed_data)
                if radial_chart:
                    st.altair_chart(radial_chart, use_container_width=True)
            
            # --- Sincronização com Google Sheets ---
            st.subheader("Integração com Google Sheets")
            if st.button("Copiar Dados para Planilha Google"):
                with st.spinner("Conectando e enviando dados..."):
                    # Precisamos recarregar o CSV sem agregação para enviar os dados brutos
                    raw_df = load_data(uploaded_file, aggregate=False) 
                    if raw_df is not None:
                        copy_df_to_sheets(raw_df, uploaded_file.name)
                    else:
                        st.error("Não foi possível carregar os dados brutos para enviar.")

            # --- Detalhamento dos Dados ---
            with st.expander("Visualizar dados diários consolidados"):
                display_df = processed_data.copy()
                display_df['Data'] = display_df['Data'].dt.strftime('%d/%m/%Y')
                display_df['Total'] = display_df['Total'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(display_df, use_container_width=True)
        else:
            st.error("Não foi possível processar o arquivo. Verifique se o formato está correto.")
    else:
        st.info("Aguardando o upload de um arquivo CSV.")

if __name__ == "__main__":
    main()
