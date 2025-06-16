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
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Inicialização de Session State ---
def initialize_session_state():
    """Inicializa todos os valores do session state."""
    if 'custo_wdo' not in st.session_state:
        st.session_state.custo_wdo = 0.99
    if 'custo_win' not in st.session_state:
        st.session_state.custo_win = 0.39
    if 'filtered_data' not in st.session_state:
        st.session_state.filtered_data = None

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

# --- PASSO 1: COLAR DADOS BRUTOS NO GOOGLE SHEETS ---
def copy_csv_to_sheets_first(uploaded_file, filename=None):
    """PASSO 1: Cola dados do CSV EXATAMENTE como estão no arquivo original."""
    try:
        gc = get_gspread_client()
        if gc is None:
            return False, "Erro de conexão"
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # Nome da aba baseado no arquivo
        if filename:
            sheet_name = filename.replace('.csv', '').replace('.CSV', '')[:30]
        else:
            sheet_name = f"CSV_{datetime.now().strftime('%d%m%Y_%H%M')}"
        
        # Verificar se a aba já existe, se não, criar
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        
        # LER O ARQUIVO CSV ORIGINAL DIRETAMENTE
        uploaded_file.seek(0)
        
        # Tentar diferentes encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
        csv_lines = None
        
        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode(encoding)
                csv_lines = content.split('\n')
                break
            except:
                continue
        
        if csv_lines is None:
            return False, "Erro ao ler arquivo"
        
        # Pegar dados a partir da linha 5 (índice 4)
        if len(csv_lines) < 5:
            return False, "Arquivo não tem dados suficientes"
        
        # Linha 5 é o cabeçalho (índice 4)
        header_line = csv_lines[4].strip()
        data_lines = csv_lines[5:]  # Dados a partir da linha 6
        
        # Processar cabeçalho
        header_cells = [cell.strip().strip('"') for cell in header_line.split(';')]
        
        # Processar linhas de dados - APENAS as que têm conteúdo
        data_rows = []
        for line in data_lines:
            line = line.strip()
            if line:  # Se a linha não está vazia
                cells = [cell.strip().strip('"') for cell in line.split(';')]
                # Verificar se a linha tem pelo menos uma célula com conteúdo
                if any(cell for cell in cells):
                    # Garantir que a linha tenha o mesmo número de colunas que o cabeçalho
                    while len(cells) < len(header_cells):
                        cells.append('')
                    # Se tem mais colunas que o cabeçalho, cortar
                    if len(cells) > len(header_cells):
                        cells = cells[:len(header_cells)]
                    data_rows.append(cells)
        
        # Obter dados existentes na planilha
        existing_data = worksheet.get_all_values()
        
        # Se a planilha está vazia, adicionar cabeçalho primeiro
        if not existing_data:
            worksheet.update('A1', [header_cells])
            first_empty_row = 2
        else:
            # Encontrar primeira linha vazia
            first_empty_row = 2  # Começar da linha 2
            for i in range(1, len(existing_data)):
                row = existing_data[i]
                if not any(cell.strip() for cell in row if cell):
                    first_empty_row = i + 1
                    break
                else:
                    first_empty_row = i + 2
        
        # Inserir dados na planilha
        if data_rows:
            # Calcular range
            num_rows = len(data_rows)
            num_cols = len(header_cells)
            
            def num_to_col_letter(num):
                result = ""
                while num > 0:
                    num -= 1
                    result = chr(65 + (num % 26)) + result
                    num //= 26
                return result
            
            end_col = num_to_col_letter(num_cols)
            end_row = first_empty_row + num_rows - 1
            range_name = f'A{first_empty_row}:{end_col}{end_row}'
            
            # Inserir dados
            worksheet.update(range_name, data_rows, value_input_option='RAW')
        
        return True, f"{sheet_name} (coladas {len(data_rows)} linhas do CSV original)"
        
    except Exception as e:
        return False, str(e)

# --- PASSO 2: PROCESSAR DADOS E APLICAR CUSTOS ---
def process_data_and_apply_costs(uploaded_file, filename=None):
    """PASSO 2: Processa dados do CSV e aplica custos."""
    try:
        # Ler CSV com pandas para processamento
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
        df_original = None
        
        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                df_original = pd.read_csv(
                    uploaded_file, 
                    encoding=encoding, 
                    sep=';',
                    skiprows=4,
                    on_bad_lines='skip'
                )
                break
            except:
                continue
        
        if df_original is None:
            return pd.DataFrame(), "Erro ao ler CSV"
        
        df = df_original.copy()
        
        if df.empty:
            return pd.DataFrame(), "CSV vazio"
        
        df.columns = df.columns.str.strip()
        
        # Detectar tipo de ativo e custo
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
        
        # Procurar coluna Total
        total_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['total', 'resultado', 'valor', 'saldo']):
                total_col = col
                break
        
        if total_col is None:
            return pd.DataFrame(), "Coluna Total não encontrada"
        
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
            return pd.DataFrame(), "Nenhuma linha válida"
        
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
            return pd.DataFrame(), "Nenhuma operação válida"
        
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
        
        return daily_data[['Data', 'Total']], asset_detected
        
    except Exception as e:
        return pd.DataFrame(), f"Erro: {str(e)}"

# --- PASSO 3: ADICIONAR DADOS PROCESSADOS À ABA 'dados' ---
def add_processed_data_to_sheets(df):
    """PASSO 3: Adiciona dados processados à aba 'dados'."""
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

# --- Funções de Filtro ---
def filter_data_by_date(df, year_filter, month_filter):
    """Filtra dados por ano e mês."""
    if df is None or df.empty:
        return df
    
    filtered_df = df.copy()
    
    if year_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Data'].dt.year == year_filter]
    
    if month_filter != "Todos":
        month_num = {
            'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
            'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
            'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
        }
        if month_filter in month_num:
            filtered_df = filtered_df[filtered_df['Data'].dt.month == month_num[month_filter]]
    
    return filtered_df

# --- Funções de Visualização ---
def create_statistics_container(df):
    """Cria container com estatísticas detalhadas."""
    if df is None or df.empty:
        st.warning("⚠️ Sem dados para exibir estatísticas")
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
        <div style="background: rgba(255, 255, 255, 0.1); 
                    backdrop-filter: blur(20px); padding: 2rem; border-radius: 15px; margin: 1rem 0; 
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);">
            <h3 style="color: #333; text-align: center; margin-bottom: 1.5rem;">📊 Estatísticas de Trading</h3>
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
    if df is None or df.empty:
        return None
    
    try:
        area_data = df.copy().sort_values('Data')
        area_data['Acumulado'] = area_data['Total'].cumsum()
        
        final_value = area_data['Acumulado'].iloc[-1]
        line_color = '#3498db' if final_value >= 0 else '#e74c3c'
        gradient_color = '#3498db' if final_value >= 0 else '#e74c3c'
        
        chart = alt.Chart(area_data).mark_area(
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
        ).properties(
            height=500, 
            title='Evolução Acumulada dos Resultados'
        ).configure_title(
            fontSize=16,
            color='#333'
        ).configure_axis(
            labelColor='#333',
            titleColor='#333'
        )
        
        return chart
    except Exception:
        return None

def create_daily_histogram(df):
    """Cria histograma diário."""
    if df is None or df.empty:
        return None
    
    try:
        hist_data = df.copy().sort_values('Data')
        
        chart = alt.Chart(hist_data).mark_bar(
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
        ).properties(
            height=500, 
            title='Resultado Diário'
        ).configure_title(
            fontSize=16,
            color='#333'
        ).configure_axis(
            labelColor='#333',
            titleColor='#333'
        )
        
        return chart
    except Exception:
        return None

def create_radial_chart(df):
    """Cria gráfico radial com dados mensais."""
    if df is None or df.empty:
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
            text=alt.Text('Mes:N'), color=alt.value('#333')
        )

        chart = (c1 + c2).properties(
            height=500, 
            title='Total por Mês'
        ).configure_title(
            fontSize=16,
            color='#333'
        )
        
        return chart
    except Exception:
        return None

def create_trading_heatmap(df):
    """Cria heatmap estilo GitHub."""
    if df is None or df.empty:
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
        
        chart = alt.Chart(full_df).mark_rect(
            stroke='white', strokeWidth=1, cornerRadius=2
        ).encode(
            x=alt.X('week:O', title=None, axis=None),
            y=alt.Y('day_name:N', sort=day_names, title=None,
                   axis=alt.Axis(labelAngle=0, labelFontSize=10, labelColor='#333',
                               ticks=False, domain=False, grid=False)),
            color=alt.condition(
                alt.datum.display_total == None,
                alt.value('#ebedf0'),
                alt.Color('display_total:Q',
                    scale=alt.Scale(
                        range=['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
                        type='linear'
                    ),
                    legend=None)
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('day_name:N', title='Dia'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(
            height=500, 
            title=f'Atividade de Trading - {current_year}'
        ).configure_title(
            fontSize=16,
            color='#333'
        )
        
        return chart
    except Exception:
        return None

# --- Função Principal ---
def main():
    initialize_session_state()
    
    # CSS simples sem partículas por enquanto
    st.markdown("""
    <style>
    .stApp {
        position: relative !important;
        overflow-x: hidden !important;
        min-height: 100vh !important;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #3498db, #74b9ff) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #74b9ff, #0984e3) !important;
        box-shadow: 0 6px 20px rgba(52, 152, 219, 0.6) !important;
        transform: translateY(-2px) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # SIDEBAR COM FILTROS
    with st.sidebar:
        st.title("🎛️ Controles")
        
        st.markdown("---")
        st.subheader("💰 Configuração de Custos")
        
        st.session_state.custo_wdo = st.number_input(
            "Custo WDO (R$)",
            min_value=0.01,
            max_value=10.00,
            value=st.session_state.custo_wdo,
            step=0.01,
            format="%.2f"
        )
        
        st.session_state.custo_win = st.number_input(
            "Custo WIN (R$)",
            min_value=0.01,
            max_value=10.00,
            value=st.session_state.custo_win,
            step=0.01,
            format="%.2f"
        )
        
        st.markdown("---")
        st.subheader("📅 Filtros de Data")
        
        # Carregar dados para filtros
        sheets_data = load_data_from_sheets()
        
        if sheets_data is not None and not sheets_data.empty:
            # Filtro de Ano
            years_available = sorted(sheets_data['Data'].dt.year.unique(), reverse=True)
            year_options = ["Todos"] + [int(year) for year in years_available]
            
            year_filter = st.selectbox(
                "Ano",
                options=year_options,
                index=0
            )
            
            # Filtro de Mês
            month_options = ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                           "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            
            month_filter = st.selectbox(
                "Mês",
                options=month_options,
                index=0
            )
            
            # Aplicar filtros
            filtered_data = filter_data_by_date(sheets_data, year_filter, month_filter)
            st.session_state.filtered_data = filtered_data
            
            # Mostrar informações dos filtros
            if filtered_data is not None and not filtered_data.empty:
                st.markdown("---")
                st.subheader("📊 Resumo Filtrado")
                st.metric("Registros", len(filtered_data))
                st.metric("Período", f"{filtered_data['Data'].min().strftime('%d/%m/%Y')} a {filtered_data['Data'].max().strftime('%d/%m/%Y')}")
                st.metric("Total", f"R$ {filtered_data['Total'].sum():,.2f}")
        else:
            st.warning("Sem dados disponíveis")
            st.session_state.filtered_data = None
        
        st.markdown("---")
        st.subheader("📤 Upload")
        
        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=['csv']
        )
    
    # CONTEÚDO PRINCIPAL
    st.title("📈 Trading Activity Dashboard")
    
    # PROCESSAR UPLOAD NA ORDEM CORRETA
    if uploaded_file is not None:
        filename = uploaded_file.name
        
        # PASSO 1: COLAR DADOS BRUTOS
        st.subheader("🔄 Processamento em Etapas")
        
        with st.expander("📋 PASSO 1: Colando dados brutos no Google Sheets", expanded=True):
            with st.spinner("Colando dados originais do CSV..."):
                success_copy, result_copy = copy_csv_to_sheets_first(uploaded_file, filename)
                
                if success_copy:
                    st.success(f"✅ PASSO 1 CONCLUÍDO: {result_copy}")
                else:
                    st.error(f"❌ PASSO 1 FALHOU: {result_copy}")
        
        # PASSO 2: PROCESSAR E APLICAR CUSTOS
        if success_copy:
            with st.expander("⚙️ PASSO 2: Processando dados e aplicando custos", expanded=True):
                with st.spinner("Aplicando custos e processando dados..."):
                    processed_df, asset_info = process_data_and_apply_costs(uploaded_file, filename)
                    
                    if not processed_df.empty:
                        st.success(f"✅ PASSO 2 CONCLUÍDO: Dados processados - {asset_info}")
                        
                        # Mostrar resumo do processamento
                        total_bruto = processed_df['Total'].sum()
                        st.info(f"💰 Total processado: R$ {total_bruto:,.2f}")
                        
                        # PASSO 3: ADICIONAR À ABA 'dados'
                        with st.expander("📊 PASSO 3: Adicionando à aba 'dados' para dashboard", expanded=True):
                            with st.spinner("Adicionando dados processados à aba 'dados'..."):
                                success_add = add_processed_data_to_sheets(processed_df)
                                
                                if success_add:
                                    st.success("✅ PASSO 3 CONCLUÍDO: Dados adicionados à aba 'dados'")
                                    
                                    # Recarregar dados para dashboard
                                    time.sleep(1)
                                    st.cache_data.clear()
                                    sheets_data = load_data_from_sheets()
                                    if sheets_data is not None:
                                        st.session_state.filtered_data = sheets_data
                                        st.success("🔄 Dashboard atualizado com novos dados!")
                                else:
                                    st.error("❌ PASSO 3 FALHOU: Erro ao adicionar dados à aba 'dados'")
                    else:
                        st.error(f"❌ PASSO 2 FALHOU: {asset_info}")
    
    # PASSO 4: EXIBIR DASHBOARD
    display_data = st.session_state.filtered_data
    
    if display_data is not None and not display_data.empty:
        st.markdown("---")
        st.subheader("📊 PASSO 4: Dashboard com Dados Processados")
        
        # Estatísticas
        create_statistics_container(display_data)
        
        # Gráfico de área
        st.subheader("📈 Evolução Acumulada")
        area_chart = create_area_chart(display_data)
        if area_chart is not None:
            st.altair_chart(area_chart, use_container_width=True)
        
        # Heatmap
        st.subheader("🔥 Heatmap de Atividade")
        heatmap_chart = create_trading_heatmap(display_data)
        if heatmap_chart is not None:
            st.altair_chart(heatmap_chart, use_container_width=True)
        
        # Gráficos adicionais
        st.subheader("📊 Análise Detalhada")
        histogram_chart = create_daily_histogram(display_data)
        radial_chart = create_radial_chart(display_data)

        if histogram_chart is not None and radial_chart is not None:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.altair_chart(histogram_chart, use_container_width=True)
            
            with col2:
                st.altair_chart(radial_chart, use_container_width=True)
    else:
        st.info("📋 Nenhum dado encontrado. Faça upload de um arquivo CSV para começar.")

if __name__ == "__main__":
    main()
