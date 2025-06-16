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

def copy_full_csv_to_sheets(df_original, filename=None):
    """Cola TODAS as linhas preenchidas do CSV literalmente na planilha Google Sheets."""
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
            # Se não existe, criar nova aba
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            
            # Criar cabeçalho padrão na linha 1
            header_padrao = [
                'Subconta', 'Ativo', 'Abertura', 'Fechamento', 'Tempo Operação',
                'Qtd Compra', 'Qtd Venda', 'Lado', 'Preço Compra', 'Preço Venda',
                'Preço de Mercado', 'Res. Intervalo', 'Res. Intervalo (%)',
                'Número Operação', 'Res. Operação', 'Res. Operação (%)', 'TET', 'Total'
            ]
            worksheet.update('A1', [header_padrao])
        
        # Obter dados existentes na planilha
        existing_data = worksheet.get_all_values()
        
        # Encontrar a primeira linha vazia abaixo do cabeçalho (linha 1)
        first_empty_row = 2  # Começar da linha 2 (abaixo do cabeçalho)
        
        if len(existing_data) > 1:  # Se há mais que só o cabeçalho
            for i in range(1, len(existing_data)):  # Começar da linha 2 (índice 1)
                row = existing_data[i]
                # Se a linha está completamente vazia
                if not any(cell.strip() for cell in row if cell):
                    first_empty_row = i + 1  # +1 porque gspread usa indexação 1-based
                    break
                else:
                    first_empty_row = i + 2  # Próxima linha após a última preenchida
        
        # Filtrar TODAS as linhas que têm pelo menos uma célula preenchida
        linhas_preenchidas = []
        
        for _, row in df_original.iterrows():
            # Verificar se a linha tem pelo menos uma célula com conteúdo
            linha_tem_conteudo = False
            linha_dados = []
            
            for value in row:
                if pd.isna(value):
                    linha_dados.append('')
                else:
                    valor_str = str(value).strip()
                    linha_dados.append(valor_str)
                    if valor_str:  # Se não está vazio
                        linha_tem_conteudo = True
            
            # Se a linha tem conteúdo, adicionar à lista
            if linha_tem_conteudo:
                linhas_preenchidas.append(linha_dados)
        
        # Inserir TODAS as linhas preenchidas na planilha
        if linhas_preenchidas:
            # Calcular o range para inserção
            num_rows = len(linhas_preenchidas)
            num_cols = len(linhas_preenchidas[0])
            
            # Converter número para letra da coluna
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
            
            # Inserir os dados LITERALMENTE
            worksheet.update(range_name, linhas_preenchidas, value_input_option='RAW')
        
        return True, f"{sheet_name} (coladas {len(linhas_preenchidas)} linhas preenchidas)"
        
    except Exception as e:
        return False, str(e)

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
            return pd.DataFrame(), "Erro"
        
        df.columns = df.columns.str.strip()
        
        custo_por_contrato, asset_info = detect_asset_cost(df)
        
        total_col = None
        for col in df.columns:
            if any(word in col.lower() for word in ['total', 'resultado', 'valor', 'saldo']):
                total_col = col
                break
        
        if total_col is None:
            return pd.DataFrame(), "Erro"
        
        qtd_compra_col = None
        qtd_venda_col = None
        
        for col in df.columns:
            if any(word in col.lower() for word in ['qtd compra', 'quantidade compra', 'qtd_compra']):
                qtd_compra_col = col
            elif any(word in col.lower() for word in ['qtd venda', 'quantidade venda', 'qtd_venda']):
                qtd_venda_col = col
        
        df = df[df[total_col].notna() & (df[total_col] != '') & (df[total_col] != 'nan')]
        
        if df.empty:
            return pd.DataFrame(), "Erro"
        
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
            return pd.DataFrame(), "Erro"
        
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
    
    # CSS APENAS COM PARTÍCULAS (sem background escuro)
    st.markdown("""
    <style>
    /* Remover background escuro - usar padrão do Streamlit */
    .stApp {
        position: relative !important;
        overflow-x: hidden !important;
        min-height: 100vh !important;
    }
    
    /* Container de partículas - APENAS as fagulhas */
    .particles {
        position: fixed !important;
        width: 100vw !important;
        height: 100vh !important;
        overflow: hidden !important;
        top: 0 !important;
        left: 0 !important;
        pointer-events: none !important;
        z-index: -1 !important;
    }
    
    /* Partículas individuais - fagulhas douradas */
    .particle {
        position: absolute !important;
        border-radius: 50% !important;
        background: radial-gradient(circle, #ffd700 0%, #ffaa00 50%, transparent 100%) !important;
        animation: float 20s infinite linear !important;
        display: block !important;
        visibility: visible !important;
        box-shadow: 0 0 6px #ffd700, 0 0 12px #ffd700 !important;
    }
    
    /* Animação das partículas subindo */
    @keyframes float {
        0% {
            transform: translateY(100vh) scale(0.5) !important;
            opacity: 0 !important;
        }
        10% {
            opacity: 0.8 !important;
        }
        50% {
            opacity: 1 !important;
        }
        90% {
            opacity: 0.6 !important;
        }
        100% {
            transform: translateY(-10vh) scale(1.2) !important;
            opacity: 0 !important;
        }
    }
    
    /* Garantir que todo conteúdo fique acima das partículas */
    .main .block-container,
    .stApp > div,
    .stMarkdown,
    .metric-container,
    .vega-embed,
    .stDataFrame,
    .stSelectbox,
    .stNumberInput,
    .stFileUploader,
    .stButton,
    .stMetric,
    .stColumns {
        position: relative !important;
        z-index: 1 !important;
        background: transparent !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: rgba(248, 249, 251, 0.95) !important;
        backdrop-filter: blur(10px) !important;
        position: relative !important;
        z-index: 10 !important;
    }
    
    /* Gráficos acima das partículas */
    .vega-embed,
    .vega-embed canvas,
    .vega-embed svg {
        background: transparent !important;
        position: relative !important;
        z-index: 5 !important;
    }
    
    /* Botões */
    .stButton > button {
        background: linear-gradient(45deg, #3498db, #74b9ff) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4) !important;
        transition: all 0.3s ease !important;
        position: relative !important;
        z-index: 4 !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #74b9ff, #0984e3) !important;
        box-shadow: 0 6px 20px rgba(52, 152, 219, 0.6) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Upload area */
    .stFileUploader > div {
        background-color: rgba(248, 249, 251, 0.8) !important;
        border: 2px dashed rgba(52, 152, 219, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        position: relative !important;
        z-index: 3 !important;
    }
    
    /* Inputs */
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        position: relative !important;
        z-index: 3 !important;
    }
    </style>
    
    <!-- HTML para partículas douradas -->
    <div class="particles" id="particles-container">
        <div class="particle" style="width: 8px; height: 8px; left: 15%; animation-delay: 0s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 35%; animation-delay: 3s;"></div>
        <div class="particle" style="width: 10px; height: 10px; left: 55%; animation-delay: 6s;"></div>
        <div class="particle" style="width: 4px; height: 4px; left: 75%; animation-delay: 9s;"></div>
        <div class="particle" style="width: 12px; height: 12px; left: 25%; animation-delay: 12s;"></div>
        <div class="particle" style="width: 7px; height: 7px; left: 65%; animation-delay: 15s;"></div>
        <div class="particle" style="width: 9px; height: 9px; left: 45%; animation-delay: 18s;"></div>
        <div class="particle" style="width: 5px; height: 5px; left: 85%; animation-delay: 2s;"></div>
        <div class="particle" style="width: 11px; height: 11px; left: 5%; animation-delay: 5s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 95%; animation-delay: 8s;"></div>
        <div class="particle" style="width: 8px; height: 8px; left: 20%; animation-delay: 11s;"></div>
        <div class="particle" style="width: 10px; height: 10px; left: 80%; animation-delay: 14s;"></div>
        <div class="particle" style="width: 4px; height: 4px; left: 40%; animation-delay: 17s;"></div>
        <div class="particle" style="width: 9px; height: 9px; left: 60%; animation-delay: 1s;"></div>
        <div class="particle" style="width: 7px; height: 7px; left: 30%; animation-delay: 4s;"></div>
        <div class="particle" style="width: 12px; height: 12px; left: 70%; animation-delay: 7s;"></div>
        <div class="particle" style="width: 5px; height: 5px; left: 10%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 8px; height: 8px; left: 90%; animation-delay: 13s;"></div>
        <div class="particle" style="width: 6px; height: 6px; left: 50%; animation-delay: 16s;"></div>
        <div class="particle" style="width: 11px; height: 11px; left: 12%; animation-delay: 19s;"></div>
    </div>
    
    <script>
    // JavaScript para criar partículas adicionais
    function createAdditionalParticles() {
        const container = document.getElementById('particles-container');
        if (container) {
            // Criar 25 partículas adicionais
            for (let i = 0; i < 25; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                
                const size = Math.random() * 8 + 4; // 4px a 12px
                particle.style.width = size + 'px';
                particle.style.height = size + 'px';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDelay = Math.random() * 20 + 's';
                particle.style.display = 'block';
                particle.style.visibility = 'visible';
                
                container.appendChild(particle);
            }
        }
    }
    
    // Executar quando a página carregar
    document.addEventListener('DOMContentLoaded', createAdditionalParticles);
    setTimeout(createAdditionalParticles, 1000);
    </script>
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
    
    # Processar upload
    if uploaded_file is not None:
        try:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            df_original = None
            filename = uploaded_file.name
            
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
            
            if df_original is not None:
                # Colar TODAS as linhas preenchidas literalmente
                success_full, sheet_name = copy_full_csv_to_sheets(df_original, filename)
                
                if success_full:
                    st.success(f"✅ Todas as linhas preenchidas coladas: {sheet_name}")
                
                # Processar dados para dashboard (COM custos)
                processed_result = process_trading_data(df_original, filename)
                
                if isinstance(processed_result, tuple):
                    processed_df, asset_info = processed_result
                else:
                    processed_df = processed_result
                    asset_info = "Processado"
                
                if not processed_df.empty:
                    if append_data_to_sheets(processed_df):
                        st.success(f"✅ Dados processados adicionados - {asset_info}")
                        time.sleep(1)
                        st.cache_data.clear()
                        # Recarregar dados
                        sheets_data = load_data_from_sheets()
                        if sheets_data is not None:
                            st.session_state.filtered_data = sheets_data
        except Exception:
            pass
    
    # Exibir dashboard com dados filtrados
    display_data = st.session_state.filtered_data
    
    if display_data is not None and not display_data.empty:
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
            if histogram_chart is not None:
                st.altair_chart(histogram_chart, use_container_width=True)
            if radial_chart is not None:
                st.altair_chart(radial_chart, use_container_width=True)
    else:
        st.info("📋 Nenhum dado encontrado. Faça upload de um arquivo CSV para começar.")

if __name__ == "__main__":
    main()
