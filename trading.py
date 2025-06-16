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
HEADER_ROW_INDEX = 4  # Linha 5 do arquivo

# Cores
WIN_COLOR = '#2ECC71'
LOSS_COLOR = '#E74C3C'
PRIMARY_COLOR = '#3498DB'
GRAY_LIGHT = '#F5F5F5'
GRAY_DARK = '#E0E0E0'
HEATMAP_RANGE = ['#8B0000', '#CD5C5C', GRAY_DARK, '#90EE90', '#006400']

# --- Conexão Segura com Google Sheets ---
@st.cache_resource
def get_gspread_client():
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
        st.error(f"Erro na autenticação com a API do Google: {e}")
        return None

# --- Carregamento e Processamento de Dados (COM CORREÇÃO) ---
@st.cache_data
def load_and_process_data(uploaded_file, aggregate=True):
    """
    Lê um arquivo CSV, detecta o separador automaticamente, processa os dados e retorna um DataFrame.
    """
    encodings_to_try = ['latin-1', 'cp1252', 'iso-8859-1', 'utf-8']
    
    for encoding in encodings_to_try:
        try:
            uploaded_file.seek(0)
            
            # --- A CORREÇÃO PRINCIPAL ESTÁ AQUI ---
            # O `sep=None` instrui o Pandas a detectar o separador automaticamente.
            # `engine='python'` é necessário para que a detecção funcione.
            df = pd.read_csv(
                uploaded_file,
                sep=None,
                engine='python',
                header=HEADER_ROW_INDEX,
                skipinitialspace=True
            )
            
            # --- O restante do processamento continua o mesmo ---
            df.columns = df.columns.str.strip()
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)

            date_col = next((col for col in df.columns if 'Abertura' in col), None)
            total_col = next((col for col in df.columns if 'Total' in col), None)

            if not date_col or not total_col:
                # Se ainda assim não encontrar, tenta o próximo encoding antes de falhar
                continue

            df['Data_Ref'] = pd.to_datetime(df[date_col].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
            total_series = df[total_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df['Resultado'] = pd.to_numeric(total_series, errors='coerce').fillna(0)
            df = df.dropna(subset=['Data_Ref'])

            if not aggregate:
                return df

            daily_data = df.groupby('Data_Ref')['Resultado'].sum().reset_index()
            daily_data.columns = ['Data', 'Total']
            
            st.info(f"Arquivo lido com sucesso usando o encoding '{encoding}'.")
            return daily_data

        except Exception:
            continue
            
    st.error("Falha ao processar o arquivo. Verifique se o arquivo CSV não está corrompido e se o cabeçalho está na linha 5.")
    return None

# --- Integração com Google Sheets ---
def copy_df_to_sheets(df, filename):
    """Copia um DataFrame para uma nova aba no Google Sheets."""
    gc = get_gspread_client()
    if not gc: return False

    try:
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        sheet_name = filename.replace('.csv', '')[:31]

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=30)
        
        # Limpa o DataFrame de colunas totalmente vazias antes de enviar
        df_cleaned = df.dropna(how='all', axis=1)
        data_to_upload = [df_cleaned.columns.values.tolist()] + df_cleaned.astype(str).values.tolist()
        
        worksheet.update('A1', data_to_upload, value_input_option='USER_ENTERED')
        
        st.success(f"✅ Dados atualizados com sucesso na aba '{sheet_name}'!")
        return True
    
    except Exception as e:
        st.error(f"Erro ao enviar dados para o Google Sheets: {e}")
        return False

# --- Funções de Criação de Gráficos (sem alterações) ---

def create_line_chart(df):
    df_sorted = df.sort_values('Data').copy()
    df_sorted['Acumulado'] = df_sorted['Total'].cumsum()
    chart = alt.Chart(df_sorted).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Acumulado:Q', title='Resultado Acumulado (R$)'),
        color=alt.value(PRIMARY_COLOR),
        tooltip=[alt.Tooltip('Data:T', format='%d/%m/%Y'), alt.Tooltip('Total:Q', format=',.2f'), alt.Tooltip('Acumulado:Q', format=',.2f')]
    ).properties(height=400, title="Evolução dos Resultados")
    return chart

def create_accuracy_radial_chart(df):
    winning_days = (df['Total'] > 0).sum()
    total_days = len(df)
    accuracy_rate = (winning_days / total_days) * 100 if total_days > 0 else 0
    data = pd.DataFrame({'category': ['Dias Positivos', 'Dias Negativos'], 'value': [accuracy_rate, 100 - accuracy_rate], 'color': [WIN_COLOR, LOSS_COLOR]})
    chart = alt.Chart(data).mark_arc(innerRadius=60).encode(
        theta=alt.Theta('value:Q'), color=alt.Color('color:N', scale=None, legend=None),
        tooltip=['category:N', alt.Tooltip('value:Q', format='.1f', title='%')]
    ).properties(height=220, title=f'{accuracy_rate:.1f}% de Dias Positivos')
    return chart

def create_trading_heatmap(df):
    current_year = df['Data'].dt.year.max()
    df_year = df[df['Data'].dt.year == current_year].copy()
    all_dates = pd.date_range(start=f'{current_year}-01-01', end=f'{current_year}-12-31', freq='D')
    full_df = pd.DataFrame({'Data': all_dates}).merge(df_year, on='Data', how='left')
    full_df['Total'] = full_df['Total'].fillna(0)
    full_df['week'] = full_df['Data'].dt.isocalendar().week
    full_df['day_of_week'] = full_df['Data'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    max_abs_val = max(abs(df_year['Total'].min()), df_year['Total'].max()) if not df_year.empty else 1
    chart = alt.Chart(full_df).mark_rect(stroke='white', strokeWidth=2).encode(
        x=alt.X('week:O', title=None, axis=None), y=alt.Y('day_of_week:O', sort=day_order, title=None),
        color=alt.condition(
            alt.datum.Total == 0, alt.value(GRAY_LIGHT),
            alt.Color('Total:Q', scale=alt.Scale(domain=[-max_abs_val, 0, max_abs_val], range=HEATMAP_RANGE), legend=alt.Legend(title="Resultado", orient='bottom'))
        ),
        tooltip=[alt.Tooltip('Data:T', format='%d/%m/%Y'), alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')]
    ).properties(height=150, title=f'Atividade de Trading - {current_year}')
    return chart

# --- Interface Principal do Dashboard ---
def main():
    st.title("Dashboard de Análise de Performance")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo CSV", type=['csv'],
        help="O cabeçalho deve estar na linha 5 e os dados na linha 6."
    )
    
    if uploaded_file:
        daily_summary = load_and_process_data(uploaded_file, aggregate=True)
        
        if daily_summary is not None and not daily_summary.empty:
            st.header("Visão Geral dos Resultados Diários")

            col1, col2, col3, col4 = st.columns(4)
            total_result, avg_result, positive_days = daily_summary['Total'].sum(), daily_summary['Total'].mean(), (daily_summary['Total'] > 0).sum()
            col1.metric("Resultado Total", f"R$ {total_result:,.2f}")
            col2.metric("Dias Operados", len(daily_summary))
            col3.metric("Dias Positivos", f"{positive_days}")
            col4.metric("Média por Dia", f"R$ {avg_result:,.2f}")

            st.altair_chart(create_trading_heatmap(daily_summary), use_container_width=True)
            
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.altair_chart(create_line_chart(daily_summary), use_container_width=True)
            with col_right:
                st.altair_chart(create_accuracy_radial_chart(daily_summary), use_container_width=True)
            
            st.subheader("Sincronização com Google Sheets")
            if st.button("Copiar Dados para Planilha Google"):
                with st.spinner("Enviando dados brutos para a planilha..."):
                    raw_df = load_and_process_data(uploaded_file, aggregate=False) 
                    if raw_df is not None:
                        copy_df_to_sheets(raw_df, uploaded_file.name)

            with st.expander("Visualizar dados diários consolidados"):
                st.dataframe(daily_summary.sort_values(by='Data', ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()
