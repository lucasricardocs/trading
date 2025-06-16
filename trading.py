# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import time
import re

# Suprimir warnings
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# --- Configurações Globais ---
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'
WORKSHEET_NAME = 'dados'

# Configuração da página
st.set_page_config(
    page_title="Trading Activity Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- Inicialização de Session State ---
def initialize_costs():
    """Inicializa os custos padrão no session state."""
    if 'custo_wdo' not in st.session_state:
        st.session_state.custo_wdo = 0.99
    if 'custo_win' not in st.session_state:
        st.session_state.custo_win = 0.39

# --- Funções de Conexão com Google Sheets ---
@st.cache_resource
def get_gspread_client():
    """Cria e retorna cliente gspread autenticado."""
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
    except Exception:
        return None

@st.cache_data(ttl=60)
def load_data_from_sheets():
    """Carrega dados da aba 'dados' da planilha Google Sheets."""
    try:
        gc = get_gspread_client()
        if gc is None:
            return None
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        
        if not data:
            return None
        
        df = pd.DataFrame(data)
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
        df = df.dropna(subset=['Data', 'Total'])
        
        return df
    except Exception:
        return None

def append_data_to_sheets(df):
    """Adiciona novos dados à aba 'dados'."""
    try:
        gc = get_gspread_client()
        if gc is None:
            return False
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        existing_data = worksheet.get_all_records()
        existing_dates = set()
        
        if existing_data:
            for row in existing_data:
                try:
                    date_obj = pd.to_datetime(row['Data'], format='%d/%m/%Y')
                    existing_dates.add(date_obj.date())
                except:
                    continue
        
        new_data = df.copy()
        new_data['Data'] = pd.to_datetime(new_data['Data'])
        
        if existing_dates:
            new_dates = set(new_data['Data'].dt.date)
            dates_to_add = new_dates - existing_dates
            
            if dates_to_add:
                new_data = new_data[new_data['Data'].dt.date.isin(dates_to_add)]
            else:
                return True
        
        if new_data.empty:
            return True
        
        rows_to_add = []
        for _, row in new_data.iterrows():
            rows_to_add.append([
                row['Data'].strftime('%d/%m/%Y'),
                float(row['Total'])
            ])
        
        worksheet.append_rows(rows_to_add)
        return True
    except Exception:
        return False

# --- Funções de Processamento ---
def detect_asset_cost(df):
    """Detecta o custo baseado nos dois primeiros caracteres da coluna ativo."""
    custo_por_contrato = st.session_state.custo_wdo
    asset_detected = "WDO (padrão)"
    
    for col in df.columns:
        if any(word in col.lower() for word in ['ativo', 'asset', 'symbol']):
            if not df[col].empty:
                first_asset = str(df[col].dropna().iloc[0]).upper().strip()
                
                if len(first_asset) >= 2:
                    first_two_chars = first_asset[:2]
                    
                    if first_two_chars == 'WD':
                        custo_por_contrato = st.session_state.custo_wdo
                        asset_detected = f"WD* ({first_asset})"
                    elif first_two_chars == 'WI':
                        custo_por_contrato = st.session_state.custo_win
                        asset_detected = f"WI* ({first_asset})"
                    else:
                        custo_por_contrato = st.session_state.custo_wdo
                        asset_detected = f"Outros ({first_asset})"
                break
    
    return custo_por_contrato, asset_detected

def process_trading_data(df, filename=None):
    """Processa os dados de trading do CSV."""
    try:
        df = df.copy()
        
        if df.empty:
            return pd.DataFrame()
        
        df.columns = df.columns.str.strip()
        
        # Detectar custo
        custo_por_contrato, asset_info = detect_asset_cost(df)
        
        # Procurar coluna Total
        total_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['total', 'resultado', 'valor', 'saldo']):
                total_col = col
                break
        
        if total_col is None:
            return pd.DataFrame()
        
        # Procurar colunas de quantidade
        qtd_compra_col = None
        qtd_venda_col = None
        
        for col in df.columns:
            if any(word in col.lower() for word in ['qtd compra', 'quantidade compra', 'qtd_compra']):
                qtd_compra_col = col
            elif any(word in col.lower() for word in ['qtd venda', 'quantidade venda', 'qtd_venda']):
                qtd_venda_col = col
        
        df = df[df[total_col].notna() & (df[total_col] != '') & (df[total_col] != 'nan')]
        
        if df.empty:
            return pd.DataFrame()
        
        def convert_total(value):
            try:
                if pd.isna(value) or value == '' or str(value).lower() == 'nan':
                    return 0
                
                value_str = str(value).strip()
                value_str = value_str.replace('R$', '').replace('$', '').strip()
                value_str = value_str.replace(',', '.')
                value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
                
                return float(value_str) if value_str else 0
            except:
                return 0
        
        def convert_quantity(value):
            try:
                if pd.isna(value) or value == '' or str(value).lower() == 'nan':
                    return 0
                return int(float(str(value).strip()))
            except:
                return 0
        
        df['Total'] = df[total_col].apply(convert_total)
        
        # Calcular custos
        if qtd_compra_col and qtd_venda_col:
            df['Qtd_Compra'] = df[qtd_compra_col].apply(convert_quantity)
            df['Qtd_Venda'] = df[qtd_venda_col].apply(convert_quantity)
            df['Total_Contratos'] = df['Qtd_Compra'] + df['Qtd_Venda']
        elif qtd_compra_col:
            df['Qtd_Compra'] = df[qtd_compra_col].apply(convert_quantity)
            df['Total_Contratos'] = df['Qtd_Compra'] * 2
        elif qtd_venda_col:
            df['Qtd_Venda'] = df[qtd_venda_col].apply(convert_quantity)
            df['Total_Contratos'] = df['Qtd_Venda'] * 2
        else:
            df['Total_Contratos'] = 2
        
        df['Custo_Operacao'] = df['Total_Contratos'] * custo_por_contrato
        df['Total_Bruto'] = df['Total']
        df['Total'] = df['Total_Bruto'] - df['Custo_Operacao']
        
        df = df[df['Total_Contratos'] > 0]
        
        if df.empty:
            return pd.DataFrame()
        
        # Criar data automaticamente
        data_arquivo = None
        if filename:
            try:
                patterns = [
                    r'(\d{1,2})(\w{3})(\d{2})',
                    r'(\d{1,2})-(\d{1,2})-(\d{2,4})',
                    r'(\d{1,2})(\d{2})(\d{2,4})',
                    r'(\d{4})-(\d{1,2})-(\d{1,2})',
                ]
                
                meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                }
                
                filename_lower = filename.lower()
                
                for pattern in patterns:
                    match = re.search(pattern, filename_lower)
                    if match:
                        if any(mes in filename_lower for mes in meses.keys()):
                            dia, mes_abr, ano = match.groups()
                            mes = meses.get(mes_abr, '06')
                            ano = f"20{ano}" if len(ano) == 2 else ano
                            data_arquivo = pd.to_datetime(f"{dia}/{mes}/{ano}", format='%d/%m/%Y')
                        else:
                            if len(match.groups()) == 3:
                                p1, p2, p3 = match.groups()
                                try:
                                    if len(p3) == 4:
                                        data_arquivo = pd.to_datetime(f"{p1}/{p2}/{p3}", format='%d/%m/%Y')
                                    else:
                                        ano_completo = f"20{p3}"
                                        data_arquivo = pd.to_datetime(f"{p1}/{p2}/{ano_completo}", format='%d/%m/%Y')
                                except:
                                    continue
                        break
            except Exception:
                pass
        
        if data_arquivo is None:
            data_arquivo = pd.Timestamp.now().normalize()
        
        df['Data'] = data_arquivo
        
        daily_data = df.groupby('Data').agg({
            'Total_Bruto': 'sum',
            'Custo_Operacao': 'sum',
            'Total': 'sum',
            'Total_Contratos': 'sum'
        }).reset_index()
        
        return daily_data[['Data', 'Total']], asset_info
        
    except Exception:
        return pd.DataFrame(), "Erro"

# --- Funções de Visualização ---
def create_statistics_container(df):
    """Cria container com estatísticas detalhadas."""
    if df.empty:
        return
    
    try:
        valor_acumulado = df['Total'].sum()
        total_ganho = df[df['Total'] > 0]['Total'].sum()
        total_perda = df[df['Total'] < 0]['Total'].sum()
        dias_positivos = len(df[df['Total'] > 0])
        dias_negativos = len(df[df['Total'] < 0])
        total_dias = len(df)
        
        perc_dias_positivos = (dias_positivos / total_dias * 100) if total_dias > 0 else 0
        perc_dias_negativos = (dias_negativos / total_dias * 100) if total_dias > 0 else 0
        
        maior_ganho = df['Total'].max() if not df.empty else 0
        maior_perda = df['Total'].min() if not df.empty else 0
        
        media_diaria = df[df['Total'] != 0]['Total'].mean() if len(df[df['Total'] != 0]) > 0 else 0
        
        st.markdown("""
        <div style="background: rgba(44, 62, 80, 0.3); 
                    backdrop-filter: blur(20px); padding: 2rem; border-radius: 15px; margin: 1rem 0; 
                    box-shadow: 0 8px 32px rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);">
            <h3 style="color: white; text-align: center; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.8);">📊 Estatísticas de Trading</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Valor Acumulado", f"R$ {valor_acumulado:,.2f}")
            st.metric("📈 Total Ganhos", f"R$ {total_ganho:,.2f}")
        
        with col2:
            st.metric("📉 Total Perdas", f"R$ {total_perda:,.2f}")
            st.metric("📊 Média Diária", f"R$ {media_diaria:,.2f}")
        
        with col3:
            st.metric("✅ Dias Positivos", f"{dias_positivos} ({perc_dias_positivos:.1f}%)")
            st.metric("🚀 Maior Ganho", f"R$ {maior_ganho:,.2f}")
        
        with col4:
            st.metric("❌ Dias Negativos", f"{dias_negativos} ({perc_dias_negativos:.1f}%)")
            st.metric("💥 Maior Perda", f"R$ {maior_perda:,.2f}")
            
    except Exception:
        pass

def create_area_chart(df):
    """Cria gráfico de área com evolução acumulada."""
    if df.empty:
        return None
    
    try:
        area_data = df.copy().sort_values('Data')
        area_data['Acumulado'] = area_data['Total'].cumsum()
        
        final_value = area_data['Acumulado'].iloc[-1]
        line_color = '#3498db' if final_value >= 0 else '#e74c3c'
        gradient_color = '#3498db' if final_value >= 0 else '#e74c3c'
        
        return alt.Chart(area_data).mark_area(
            line={'color': line_color, 'strokeWidth': 2},
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='rgba(255,255,255,0.1)', offset=0),
                    alt.GradientStop(color=gradient_color, offset=1)
                ],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('Data:T', title=None),
            y=alt.Y('Acumulado:Q', title=None),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado do Dia (R$)'),
                alt.Tooltip('Acumulado:Q', format=',.2f', title='Acumulado (R$)')
            ]
        ).properties(height=500, title='Evolução Acumulada dos Resultados')
    except Exception:
        return None

def create_daily_histogram(df):
    """Cria histograma diário."""
    if df.empty:
        return None
    
    try:
        hist_data = df.copy().sort_values('Data')
        
        return alt.Chart(hist_data).mark_bar(
            cornerRadius=2, stroke='white', strokeWidth=1
        ).encode(
            x=alt.X('Data:T', title=None),
            y=alt.Y('Total:Q', title=None),
            color=alt.condition(
                alt.datum.Total >= 0,
                alt.value('#3498db'),
                alt.value('#e74c3c')
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(height=500, title='Resultado Diário')
    except Exception:
        return None

def create_radial_chart(df):
    """Cria gráfico radial com dados mensais."""
    if df.empty:
        return None
    
    try:
        radial_data = df.copy()
        radial_data['Mes'] = radial_data['Data'].dt.strftime('%b')
        radial_data['MesNum'] = radial_data['Data'].dt.month
        
        monthly_data = radial_data.groupby(['Mes', 'MesNum']).agg({
            'Total': 'sum'
        }).reset_index()
        
        monthly_data = monthly_data.sort_values('MesNum')
        monthly_data['AbsTotal'] = monthly_data['Total'].abs()
        monthly_data = monthly_data[monthly_data['AbsTotal'] > 0]
        
        if monthly_data.empty:
            return None
        
        base = alt.Chart(monthly_data).encode(
            alt.Theta("AbsTotal:Q").stack(True),
            alt.Radius("AbsTotal:Q").scale(type="sqrt", zero=True, rangeMin=20),
            color=alt.condition(
                alt.datum.Total >= 0,
                alt.value('#3498db'),
                alt.value('#e74c3c')
            )
        )

        c1 = base.mark_arc(innerRadius=20, stroke="#fff", strokeWidth=2)
        c2 = base.mark_text(radiusOffset=15, fontSize=10, fontWeight='bold').encode(
            text=alt.Text('Mes:N'), color=alt.value('white')
        )

        return (c1 + c2).properties(height=500, title='Total por Mês')
    except Exception:
        return None

def create_trading_heatmap(df):
    """Cria heatmap estilo GitHub."""
    if df.empty:
        return None
    
    try:
        current_year = df['Data'].dt.year.max()
        df_year = df[df['Data'].dt.year == current_year].copy()

        if df_year.empty:
            return None

        start_date = pd.Timestamp(f'{current_year}-01-01')
        end_date = pd.Timestamp(f'{current_year}-12-31')
        
        start_weekday = start_date.weekday()
        if start_weekday > 0:
            start_date = start_date - pd.Timedelta(days=start_weekday)
        
        end_weekday = end_date.weekday()
        if end_weekday < 6:
            end_date = end_date + pd.Timedelta(days=6-end_weekday)
        
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        full_df = pd.DataFrame({'Data': all_dates})
        full_df = full_df.merge(df_year[['Data', 'Total']], on='Data', how='left')
        full_df['Total'] = full_df['Total'].fillna(0)
        
        full_df['week'] = ((full_df['Data'] - start_date).dt.days // 7)
        full_df['day_of_week'] = full_df['Data'].dt.weekday
        
        day_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        full_df['day_name'] = full_df['day_of_week'].map(lambda x: day_names[x])
        
        full_df['is_current_year'] = full_df['Data'].dt.year == current_year
        full_df['display_total'] = full_df['Total'].where(full_df['is_current_year'], None)
        
        return alt.Chart(full_df).mark_rect(
            stroke='white', strokeWidth=1, cornerRadius=2
        ).encode(
            x=alt.X('week:O', title=None, axis=None),
            y=alt.Y('day_name:N', sort=day_names, title=None,
                   axis=alt.Axis(labelAngle=0, labelFontSize=10, 
                               ticks=False, domain=False, grid=False)),
            color=alt.condition(
                alt.datum.display_total == None,
                alt.value('rgba(255,255,255,0.1)'),
                alt.Color('display_total:Q',
                    scale=alt.Scale(
                        range=['rgba(255,255,255,0.1)', '#74b9ff', '#0984e3', '#2d3436', '#636e72'],
                        type='linear'
                    ),
                    legend=None)
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('day_name:N', title='Dia'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(height=500, title=f'Atividade de Trading - {current_year}')
    except Exception:
        return None

# --- Função Principal ---
def main():
    initialize_costs()
    
    st.title("📈 Trading Activity Dashboard")
    
    # CSS para background com partículas
    st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at 30% 30%, #2c3e50, #000);
        background-attachment: fixed;
        position: relative;
        overflow-x: hidden;
        min-height: 100vh;
        color: white;
        font-family: Arial, sans-serif;
    }
    
    .particles {
        position: fixed;
        width: 100%;
        height: 100%;
        overflow: hidden;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: -1;
    }
    
    .particle {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.8);
        animation: float 20s infinite linear;
    }
    
    @keyframes float {
        0% {
            transform: translateY(100vh) scale(0.5);
            opacity: 0;
        }
        50% {
            opacity: 1;
        }
        100% {
            transform: translateY(-10vh) scale(1.2);
            opacity: 0;
        }
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    
    .stMarkdown, .stText, p, span {
        color: #e0e0e0 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #3498db, #74b9ff);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #74b9ff, #0984e3);
        box-shadow: 0 6px 20px rgba(52, 152, 219, 0.6);
        transform: translateY(-2px);
    }
    
    .stFileUploader > div {
        background-color: rgba(44, 62, 80, 0.3);
        border: 2px dashed rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
    }
    
    .stNumberInput > div > div > input {
        background-color: rgba(44, 62, 80, 0.5);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    </style>
    
    <div class="particles">
        <div class="particle" style="width: 10px; height: 10px; left: 20%; animation-delay: 0s;"></div>
        <div class="particle" style="width: 8px; height: 8px; left: 40%; animation-delay: 5s;"></div>
        <div class="particle" style="width: 12px; height: 12px; left: 60%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 80%; animation-delay: 15s;"></div>
        <div class="particle" style="width: 14px; height: 14px; left: 30%; animation-delay: 3s;"></div>
        <div class="particle" style="width: 9px; height: 9px; left: 70%; animation-delay: 8s;"></div>
        <div class="particle" style="width: 11px; height: 11px; left: 50%; animation-delay: 12s;"></div>
        <div class="particle" style="width: 7px; height: 7px; left: 90%; animation-delay: 18s;"></div>
        <div class="particle" style="width: 13px; height: 13px; left: 10%; animation-delay: 6s;"></div>
        <div class="particle" style="width: 5px; height: 5px; left: 25%; animation-delay: 14s;"></div>
        <div class="particle" style="width: 15px; height: 15px; left: 75%; animation-delay: 2s;"></div>
        <div class="particle" style="width: 8px; height: 8px; left: 45%; animation-delay: 16s;"></div>
        <div class="particle" style="width: 10px; height: 10px; left: 65%; animation-delay: 4s;"></div>
        <div class="particle" style="width: 12px; height: 12px; left: 85%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 15%; animation-delay: 7s;"></div>
        <div class="particle" style="width: 14px; height: 14px; left: 35%; animation-delay: 13s;"></div>
        <div class="particle" style="width: 9px; height: 9px; left: 55%; animation-delay: 9s;"></div>
        <div class="particle" style="width: 11px; height: 11px; left: 95%; animation-delay: 11s;"></div>
        <div class="particle" style="width: 7px; height: 7px; left: 5%; animation-delay: 17s;"></div>
        <div class="particle" style="width: 13px; height: 13px; left: 82%; animation-delay: 1s;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Configuração de custos
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.custo_wdo = st.number_input(
            "💰 Custo WDO (R$)",
            min_value=0.01,
            max_value=10.00,
            value=st.session_state.custo_wdo,
            step=0.01,
            format="%.2f"
        )
    
    with col2:
        st.session_state.custo_win = st.number_input(
            "💰 Custo WIN (R$)",
            min_value=0.01,
            max_value=10.00,
            value=st.session_state.custo_win,
            step=0.01,
            format="%.2f"
        )
    
    # Carregar dados
    sheets_data = load_data_from_sheets()
    
    # Upload
    uploaded_file = st.file_uploader(
        "📤 Upload CSV",
        type=['csv']
    )
    
    # Processar upload
    if uploaded_file is not None:
        try:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            df = None
            filename = uploaded_file.name
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(
                        uploaded_file, 
                        encoding=encoding, 
                        sep=';',
                        skiprows=4,
                        on_bad_lines='skip'
                    )
                    break
                except:
                    continue
            
            if df is not None:
                processed_result = process_trading_data(df, filename)
                
                if isinstance(processed_result, tuple):
                    processed_df, asset_info = processed_result
                else:
                    processed_df = processed_result
                    asset_info = "Processado"
                
                if not processed_df.empty:
                    if append_data_to_sheets(processed_df):
                        st.success(f"✅ Dados adicionados - {asset_info}")
                        time.sleep(1)
                        st.cache_data.clear()
                        sheets_data = load_data_from_sheets()
        except Exception:
            pass
    
    # Exibir dashboard
    if sheets_data is not None and not sheets_data.empty:
        # Estatísticas
        create_statistics_container(sheets_data)
        
        # Gráfico de área
        area_chart = create_area_chart(sheets_data)
        if area_chart is not None:
            st.altair_chart(area_chart, use_container_width=True)
        
        # Heatmap
        heatmap_chart = create_trading_heatmap(sheets_data)
        if heatmap_chart is not None:
            st.altair_chart(heatmap_chart, use_container_width=True)
        
        # Gráficos adicionais
        histogram_chart = create_daily_histogram(sheets_data)
        radial_chart = create_radial_chart(sheets_data)

        if histogram_chart is not None and radial_chart is not None:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.altair_chart(histogram_chart, use_container_width=True)
            
            with col2:
                st.altair_chart(radial_chart, use_container_width=True)

if __name__ == "__main__":
    main()
