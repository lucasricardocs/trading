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
    page_title="Trading Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Cores Padrão ---
COLOR_POSITIVE = "#28a745"  # Verde
COLOR_NEGATIVE = "#dc3545"  # Vermelho
COLOR_NEUTRAL = "#4fc3f7"   # Azul
COLOR_BASE = "#f0f0f0"      # Cinza claro

# --- Funções ---
@st.cache_resource
def get_google_auth():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    try:
        if "google_credentials" not in st.secrets:
            st.error("Credenciais não encontradas")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict:
            st.error("Credenciais vazias")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro: {e}")
        return None

@st.cache_resource
def get_worksheet():
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
            st.error(f"Erro: {e}")
            return None
    return None

@st.cache_data(ttl=60)



def get_worksheet_data():
    worksheet = get_worksheet()
    if worksheet:
        try:
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            # Converter 'Peso' e 'num_questoes' para numérico, tratando erros
            df['Peso'] = pd.to_numeric(df['Peso'], errors='coerce').fillna(0)
            df['num_questoes'] = pd.to_numeric(df['num_questoes'], errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- Main App ---

def main():
    st.title("📊 Dashboard de Evolução por Disciplina")

    # Contador de dias para a prova
    exam_date = date(2025, 9, 21)
    today = date.today()
    days_left = (exam_date - today).days
    st.info(f"Faltam {days_left} dias para a prova (21/09/2025)!")

    df = get_worksheet_data()

    if df.empty:
        st.warning("Não foi possível carregar os dados da planilha.")
        return

    st.subheader("Evolução por Disciplina")

    # Agrupar por disciplina e calcular a soma do 'Peso'
    discipline_summary = df.groupby('Matéria')['Peso'].sum().reset_index()

    # Criar gráficos de rosca para cada disciplina
    for index, row in discipline_summary.iterrows():
        discipline = row['Matéria']
        total_peso = row['Peso']

        st.write(f"### {discipline}")

        # Para o gráfico de rosca, precisamos de uma proporção.
        # Como não temos dados de 'evolução' explícitos, vamos simular
        # uma proporção baseada no 'Peso' total da disciplina em relação ao total geral.
        # Ou, para um gráfico de rosca mais simples, podemos mostrar a distribuição
        # dos 'Pesos' dentro da própria disciplina, se houver subcategorias.
        # Por enquanto, vou criar um gráfico de rosca simples mostrando o 'Peso' total
        # da disciplina em relação a um 'total possível' hipotético para fins de visualização.
        # Idealmente, precisaríamos de mais dados para uma 'evolução' real.

        # Exemplo: Gráfico de rosca mostrando o 'Peso' da disciplina vs. um 'total máximo' (arbitrário para demonstração)
        # Se 'Peso' representa a pontuação em uma disciplina, e o máximo é 100
        max_peso_hipotetico = 100 # Isso precisaria ser definido com base nos dados reais ou requisitos
        data_for_donut = pd.DataFrame({
            'category': ['Concluído', 'A Concluir'],
            'value': [total_peso, max_peso_hipotetico - total_peso]
        })

        chart = alt.Chart(data_for_donut).mark_arc(outerRadius=120).encode(
            theta=alt.Theta(field="value", type="quantitative"),
            color=alt.Color(field="category", scale=alt.Scale(range=[COLOR_POSITIVE, COLOR_BASE])),
            order=alt.Order("value", sort="descending"),
            tooltip=["category", "value"]
        ).properties(
            title=f"Progresso em {discipline}"
        )

        text = chart.mark_text(radius=140).encode(
            text=alt.Text("value", format=".1f"),
            order=alt.Order("value", sort="descending"),
            color=alt.value("black")
        )

        st.altair_chart(chart + text, use_container_width=True)

if __name__ == "__main__":
    main()
