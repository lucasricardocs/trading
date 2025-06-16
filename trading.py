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
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
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
            st.info("ℹ️ Aba 'dados' está vazia")
            return None
        
        df = pd.DataFrame(data)
        
        # Se a aba 'dados' tem a estrutura completa, processar como CSV
        if 'Abertura' in df.columns or 'Fechamento' in df.columns:
            # Procurar coluna de data
            date_col = None
            for col in df.columns:
                if any(word in col for word in ['Abertura', 'Fechamento', 'Data']):
                    date_col = col
                    break
            
            # Procurar coluna total
            total_col = None
            for col in df.columns:
                if any(word in col for word in ['Total', 'total']):
                    total_col = col
                    break
            
            if date_col is None or total_col is None:
                st.error("❌ Colunas necessárias não encontradas")
                return None
            
            # Filtrar dados válidos
            df = df[df[date_col].notna() & (df[date_col] != '')]
            df = df[df[total_col].notna() & (df[total_col] != '')]
            
            # Converter data
            def extract_date(date_str):
                try:
                    if isinstance(date_str, str):
                        date_part = date_str.split(' ')[0]
                        return pd.to_datetime(date_part, format='%d/%m/%Y', errors='coerce')
                    else:
                        return pd.to_datetime(date_str, errors='coerce')
                except:
                    return pd.NaT
            
            df['Data'] = df[date_col].apply(extract_date)
            
            # Converter total
            def convert_total(value):
                try:
                    if pd.isna(value) or value == '':
                        return 0
                    value_str = str(value).strip().replace(',', '.')
                    value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
                    return float(value_str) if value_str else 0
                except:
                    return 0
            
            df['Total'] = df[total_col].apply(convert_total)
            
            # Remover dados inválidos
            df = df.dropna(subset=['Data'])
            df = df[df['Total'] != 0]
            
            # Agrupar por data
            daily_data = df.groupby('Data').agg({
                'Total': 'sum'
            }).reset_index()
            
            return daily_data
            
        else:
            # Estrutura simples (Data, Total)
            if 'Data' in df.columns and 'Total' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
                df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
                df = df.dropna(subset=['Data', 'Total'])
                return df
            else:
                st.error("❌ Estrutura de dados não reconhecida")
                return None
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None

# --- FUNÇÃO PARA COLAR DADOS DO CSV ---
def copy_csv_to_sheets(uploaded_file, filename=None):
    """Cola dados do CSV garantindo correspondência exata de colunas com Google Sheets."""
    try:
        st.info("🔄 Iniciando processo de cópia com correspondência de colunas...")
        
        gc = get_gspread_client()
        if gc is None:
            st.error("❌ Falha na conexão com Google Sheets")
            return False, "Erro de conexão"
        
        st.success("✅ Conectado ao Google Sheets")
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        st.success("✅ Planilha encontrada")
        
        # Nome da aba baseado no arquivo
        if filename:
            sheet_name = filename.replace('.csv', '').replace('.CSV', '')[:30]
        else:
            sheet_name = f"CSV_{datetime.now().strftime('%d%m%Y_%H%M')}"
        
        st.info(f"📋 Criando/acessando aba: {sheet_name}")
        
        # Verificar se a aba já existe, se não, criar
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            st.info("📋 Aba existente encontrada")
        except:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=30)
            st.success(f"✅ Nova aba criada: {sheet_name}")
        
        # LER O ARQUIVO CSV
        uploaded_file.seek(0)
        
        # Tentar diferentes encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
        csv_content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                csv_content = uploaded_file.read().decode(encoding)
                used_encoding = encoding
                break
            except Exception as e:
                continue
        
        if csv_content is None:
            st.error("❌ Não foi possível ler o arquivo CSV")
            return False, "Erro ao ler arquivo"
        
        st.success(f"✅ Arquivo lido com encoding: {used_encoding}")
        
        # Dividir em linhas
        csv_lines = csv_content.split('\n')
        st.info(f"📄 Total de linhas no arquivo: {len(csv_lines)}")
        
        # Verificar se tem pelo menos 6 linhas (linha 5 + dados)
        if len(csv_lines) < 6:
            st.error("❌ Arquivo não tem dados suficientes (mínimo 6 linhas)")
            return False, "Arquivo muito pequeno"
        
        # LINHA 5 DO CSV = CABEÇALHO (índice 4)
        header_line = csv_lines[4].strip()
        if not header_line:
            st.error("❌ Linha 5 (cabeçalho) está vazia")
            return False, "Cabeçalho vazio"
        
        # Processar cabeçalho do CSV
        csv_header = []
        for cell in header_line.split(';'):
            clean_cell = cell.strip().strip('"').strip()
            csv_header.append(clean_cell)
        
        st.success(f"✅ Cabeçalho CSV (linha 5): {csv_header}")
        
        # Verificar cabeçalho existente no Google Sheets
        try:
            existing_data = worksheet.get_all_values()
            if existing_data:
                sheets_header = existing_data[0]
                st.info(f"📊 Cabeçalho Google Sheets (linha 1): {sheets_header}")
                
                # Verificar se os cabeçalhos são iguais
                if csv_header != sheets_header:
                    st.warning("⚠️ Cabeçalhos diferentes! Atualizando Google Sheets...")
                    # Atualizar cabeçalho do Google Sheets com o do CSV
                    worksheet.update('A1', [csv_header])
                    st.success("✅ Cabeçalho do Google Sheets atualizado")
                else:
                    st.success("✅ Cabeçalhos são idênticos")
            else:
                # Planilha vazia - inserir cabeçalho do CSV
                st.info("📝 Planilha vazia - inserindo cabeçalho do CSV")
                worksheet.update('A1', [csv_header])
                st.success("✅ Cabeçalho inserido na linha 1")
        except Exception as e:
            st.error(f"Erro ao verificar cabeçalho: {e}")
            # Inserir cabeçalho mesmo assim
            worksheet.update('A1', [csv_header])
        
        # Processar dados (linhas 6 em diante do CSV)
        data_lines = csv_lines[5:]  # Linhas 6 em diante (índice 5+)
        linhas_preenchidas = []
        
        for i, line in enumerate(data_lines, 6):
            line = line.strip()
            if line:  # Se a linha não está vazia
                cells = []
                for cell in line.split(';'):
                    clean_cell = cell.strip().strip('"').strip()
                    cells.append(clean_cell)
                
                # Verificar se a linha tem pelo menos uma célula com conteúdo
                if any(cell for cell in cells):
                    # Ajustar para ter exatamente o mesmo número de colunas que o cabeçalho
                    while len(cells) < len(csv_header):
                        cells.append('')
                    if len(cells) > len(csv_header):
                        cells = cells[:len(csv_header)]
                    
                    linhas_preenchidas.append(cells)
        
        st.success(f"✅ Linhas preenchidas processadas: {len(linhas_preenchidas)}")
        
        if len(linhas_preenchidas) == 0:
            st.warning("⚠️ Nenhuma linha preenchida encontrada abaixo da linha 5")
            return False, "Sem dados para inserir"
        
        # Encontrar primeira linha vazia (abaixo do cabeçalho)
        existing_data = worksheet.get_all_values()
        primeira_linha_vazia = 2  # Começar da linha 2 (abaixo do cabeçalho)
        
        if len(existing_data) > 1:  # Se há mais que só o cabeçalho
            for i in range(1, len(existing_data)):  # Começar da linha 2 (índice 1)
                row = existing_data[i]
                # Verificar se a linha está completamente vazia
                if not any(cell.strip() for cell in row if cell):
                    primeira_linha_vazia = i + 1  # +1 porque gspread usa indexação 1-based
                    break
                else:
                    primeira_linha_vazia = i + 2  # Próxima linha após a última preenchida
        
        st.info(f"📍 Inserindo dados a partir da linha: {primeira_linha_vazia}")
        
        # Inserir as linhas preenchidas
        if linhas_preenchidas:
            # Calcular range para inserção
            num_rows = len(linhas_preenchidas)
            num_cols = len(csv_header)
            
            # Converter número para letra da coluna
            def num_to_col_letter(num):
                result = ""
                while num > 0:
                    num -= 1
                    result = chr(65 + (num % 26)) + result
                    num //= 26
                return result
            
            end_col = num_to_col_letter(num_cols)
            end_row = primeira_linha_vazia + num_rows - 1
            range_name = f'A{primeira_linha_vazia}:{end_col}{end_row}'
            
            st.info(f"📊 Inserindo no range: {range_name}")
            st.info(f"📋 Inserindo {num_rows} linhas com {num_cols} colunas cada")
            
            # Inserir dados na planilha
            worksheet.update(range_name, linhas_preenchidas, value_input_option='RAW')
            
            st.success(f"✅ {num_rows} linhas inseridas com correspondência exata de colunas!")
        
        return True, f"{sheet_name} - {len(linhas_preenchidas)} linhas inseridas com colunas correspondentes"
        
    except Exception as e:
        st.error(f"❌ Erro durante a cópia: {str(e)}")
        return False, f"Erro: {str(e)}"

# --- PROCESSAR DADOS PARA DASHBOARD ---
def process_trading_data(df):
    """Processa os dados de trading do CSV."""
    # Limpar e processar as colunas
    df = df.copy()
    
    # Limpar nomes das colunas (remover espaços extras)
    df.columns = df.columns.str.strip()
    
    # Procurar pela coluna de Data (pode ser Abertura ou Fechamento)
    date_col = None
    for col in df.columns:
        if any(word in col for word in ['Abertura', 'Fechamento', 'Data', 'data']):
            date_col = col
            break
    
    if date_col is None:
        raise ValueError("Coluna de data não encontrada")
    
    # Procurar pela coluna Total
    total_col = None
    for col in df.columns:
        if 'Total' in col or 'total' in col:
            total_col = col
            break
    
    if total_col is None:
        raise ValueError("Coluna de total não encontrada")
    
    # Filtrar apenas linhas que têm data válida (não vazias)
    df = df[df[date_col].notna() & (df[date_col] != '')]
    
    # Converter Data para datetime - extrair apenas a parte da data
    def extract_date(date_str):
        try:
            # Se for string, pegar apenas os primeiros 10 caracteres (DD/MM/YYYY)
            if isinstance(date_str, str):
                date_part = date_str.split(' ')[0]  # Pegar só a parte da data
                return pd.to_datetime(date_part, format='%d/%m/%Y', errors='coerce')
            else:
                return pd.to_datetime(date_str, errors='coerce')
        except:
            return pd.NaT
    
    df['Data'] = df[date_col].apply(extract_date)
    
    # Converter Total para numérico
    if df[total_col].dtype == 'object':
        # Remover espaços, substituir vírgulas por pontos
        df['Total'] = df[total_col].astype(str).str.strip()
        df['Total'] = df['Total'].str.replace(',', '.')
        # Remover caracteres não numéricos exceto - e .
        df['Total'] = df['Total'].str.replace(r'[^\d\-\.]', '', regex=True)
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    else:
        df['Total'] = pd.to_numeric(df[total_col], errors='coerce')
    
    # Remover linhas com datas ou totais inválidos
    df = df.dropna(subset=['Data', 'Total'])
    
    # Agrupar por data para somar os resultados do dia
    daily_data = df.groupby('Data').agg({
        'Total': 'sum'
    }).reset_index()
    
    return daily_data

def process_data_for_dashboard(uploaded_file, filename=None):
    """Processa dados do CSV para o dashboard usando pandas."""
    try:
        # Ler CSV com pandas
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
        
        # Processar dados usando a função existente
        processed_df = process_trading_data(df_original)
        
        return processed_df, f"Processados {len(processed_df)} dias de trading"
        
    except Exception as e:
        return pd.DataFrame(), f"Erro: {str(e)}"

# --- ADICIONAR DADOS PROCESSADOS À ABA 'dados' ---
def add_to_dados_sheet(df):
    """Adiciona dados processados à aba 'dados'."""
    try:
        gc = get_gspread_client()
        if gc is None:
            return False
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        except:
            # Criar aba 'dados' se não existir
            worksheet = spreadsheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=10)
            worksheet.update('A1', [['Data', 'Total']])
        
        # Verificar se já existem dados
        existing_data = worksheet.get_all_records()
        existing_dates = set()
        
        if existing_data:
            for row in existing_data:
                try:
                    if 'Data' in row:
                        date_obj = pd.to_datetime(row['Data'], format='%d/%m/%Y')
                        existing_dates.add(date_obj.date())
                except:
                    continue
        
        # Filtrar dados novos
        new_data = df.copy()
        new_data['Data'] = pd.to_datetime(new_data['Data'])
        
        if existing_dates:
            new_dates = set(new_data['Data'].dt.date)
            dates_to_add = new_dates - existing_dates
            
            if dates_to_add:
                new_data = new_data[new_data['Data'].dt.date.isin(dates_to_add)]
            else:
                st.info("ℹ️ Dados já existem na aba 'dados'")
                return True
        
        if new_data.empty:
            return True
        
        # Preparar dados para inserção
        rows_to_add = []
        for _, row in new_data.iterrows():
            rows_to_add.append([
                row['Data'].strftime('%d/%m/%Y'),
                float(row['Total'])
            ])
        
        worksheet.append_rows(rows_to_add)
        st.success(f"✅ {len(rows_to_add)} dias adicionados à aba 'dados'")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao adicionar à aba dados: {e}")
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

def create_simple_heatmap(df):
    """Cria um heatmap simplificado caso o principal falhe."""
    try:
        df_year = df.copy()
        current_year = df_year['Data'].dt.year.max()
        
        # Criar grid simples
        df_year['day_of_week'] = df_year['Data'].dt.dayofweek
        df_year['week'] = df_year['Data'].dt.isocalendar().week
        
        # Mapear dias da semana
        day_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        df_year['day_name'] = df_year['day_of_week'].map(lambda x: day_names[x])
        
        chart = alt.Chart(df_year).mark_rect(
            stroke='white',
            strokeWidth=1
        ).encode(
            x=alt.X('week:O', title='Semana'),
            y=alt.Y('day_name:N', sort=day_names, title='Dia'),
            color=alt.Color('Total:Q',
                scale=alt.Scale(scheme='greens'),
                title='Resultado (R$)'),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f')
            ]
        ).properties(
            width=600,
            height=200,
            title=f'Heatmap de Trading - {current_year}'
        )
        
        return chart
    except Exception as e:
        st.error(f"Erro no heatmap simplificado: {e}")
        return None

def create_trading_heatmap(df):
    """Cria um gráfico de heatmap estilo GitHub para a atividade de trading."""
    try:
        if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
            st.warning("Dados insuficientes para gerar o heatmap.")
            return None

        # Determinar o ano atual ou mais recente dos dados
        current_year = df['Data'].dt.year.max()
        df_year = df[df['Data'].dt.year == current_year].copy()

        if df_year.empty:
            st.warning(f"Sem dados para o ano {current_year}.")
            return None

        # Criar range completo de datas para o ano
        start_date = pd.Timestamp(f'{current_year}-01-01')
        end_date = pd.Timestamp(f'{current_year}-12-31')
        
        # Ajustar para começar na segunda-feira
        start_weekday = start_date.weekday()
        if start_weekday > 0:
            start_date = start_date - pd.Timedelta(days=start_weekday)
        
        # Ajustar para terminar no domingo
        end_weekday = end_date.weekday()
        if end_weekday < 6:
            end_date = end_date + pd.Timedelta(days=6-end_weekday)
        
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # DataFrame com todas as datas
        full_df = pd.DataFrame({'Data': all_dates})
        full_df = full_df.merge(df_year[['Data', 'Total']], on='Data', how='left')
        full_df['Total'] = full_df['Total'].fillna(0)
        
        # Adicionar informações de semana e dia
        full_df['week'] = ((full_df['Data'] - start_date).dt.days // 7)
        full_df['day_of_week'] = full_df['Data'].dt.weekday
        
        # Mapear nomes dos dias
        day_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        full_df['day_name'] = full_df['day_of_week'].map(lambda x: day_names[x])
        
        # Marcar dias do ano atual
        full_df['is_current_year'] = full_df['Data'].dt.year == current_year
        full_df['display_total'] = full_df['Total'].where(full_df['is_current_year'], None)
        
        # Criar heatmap estilo GitHub
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
            height=180, 
            title=f'Atividade de Trading - {current_year}'
        ).configure_title(
            fontSize=16,
            color='#333'
        )
        
        return chart
    except Exception as e:
        st.error(f"Erro ao criar heatmap: {e}")
        return None

# --- Função Principal ---
def main():
    initialize_session_state()
    
    # CSS com partículas douradas
    st.markdown("""
    <style>
    .stApp {
        position: relative !important;
        overflow-x: hidden !important;
        min-height: 100vh !important;
    }
    
    /* Container de partículas */
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
    
    /* Partículas individuais */
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
            for (let i = 0; i < 25; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                
                const size = Math.random() * 8 + 4;
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
    
    document.addEventListener('DOMContentLoaded', createAdditionalParticles);
    setTimeout(createAdditionalParticles, 1000);
    </script>
    """, unsafe_allow_html=True)
    
    st.title("📈 Trading Activity Dashboard")
    
    # SIDEBAR COM FILTROS
    with st.sidebar:
        st.title("🎛️ Controles")
        
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
    
    # PROCESSAMENTO DO UPLOAD
    if uploaded_file is not None:
        filename = uploaded_file.name
        st.subheader("🔄 Processamento do Arquivo")
        
        # PASSO 1: Colar dados originais
        st.markdown("### 📋 PASSO 1: Copiando dados originais")
        success_copy, result_copy = copy_csv_to_sheets(uploaded_file, filename)
        
        if success_copy:
            st.success(f"✅ {result_copy}")
            
            # PASSO 2: Processar para dashboard
            st.markdown("### ⚙️ PASSO 2: Processando para dashboard")
            processed_df, asset_info = process_data_for_dashboard(uploaded_file, filename)
            
            if not processed_df.empty:
                st.success(f"✅ {asset_info}")
                
                # PASSO 3: Adicionar à aba dados
                st.markdown("### 📊 PASSO 3: Adicionando à aba 'dados'")
                if add_to_dados_sheet(processed_df):
                    st.success("✅ Dados adicionados à aba 'dados'")
                    
                    # Atualizar cache
                    st.cache_data.clear()
                    time.sleep(1)
                    
                    # Recarregar dados
                    sheets_data = load_data_from_sheets()
                    if sheets_data is not None:
                        st.session_state.filtered_data = sheets_data
                        st.success("🔄 Dashboard atualizado!")
                else:
                    st.error("❌ Erro ao adicionar à aba 'dados'")
            else:
                st.error(f"❌ Erro no processamento: {asset_info}")
        else:
            st.error(f"❌ Erro na cópia: {result_copy}")
    
    # DASHBOARD
    st.markdown("---")
    st.subheader("📊 Dashboard")
    
    # Exibir dados filtrados
    display_data = st.session_state.filtered_data
    
    if display_data is not None and not display_data.empty:
        # Estatísticas
        create_statistics_container(display_data)
        
        # Gráfico de área
        st.subheader("📈 Evolução Acumulada")
        area_chart = create_area_chart(display_data)
        if area_chart is not None:
            st.altair_chart(area_chart, use_container_width=True)
        
        # Heatmap estilo GitHub
        st.subheader("🔥 Heatmap de Atividade")
        heatmap_chart = create_trading_heatmap(display_data)
        if heatmap_chart is not None:
            st.altair_chart(heatmap_chart, use_container_width=True)
        else:
            # Fallback para heatmap simplificado
            simple_heatmap = create_simple_heatmap(display_data)
            if simple_heatmap is not None:
                st.altair_chart(simple_heatmap, use_container_width=True)
        
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
                
        # Mostrar dados processados
        with st.expander("📊 Dados processados por dia", expanded=False):
            display_df = display_data.copy()
            display_df['Data'] = display_df['Data'].dt.strftime('%d/%m/%Y')
            display_df['Total'] = display_df['Total'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(display_df, use_container_width=True)
            
    else:
        st.info("📋 Nenhum dado encontrado. Faça upload de um arquivo CSV para começar.")
        
        # Mostrar exemplo do formato esperado
        st.subheader("Formato esperado do arquivo")
        example_data = {
            'Subconta': ['12345', '12345', '12345'],
            'Ativo': ['WDON25', 'WDON25', 'WDON25'],
            'Abertura': ['16/06/2025 10:30', '16/06/2025 14:15', '16/06/2025 15:45'],
            'Total': ['80,00', '-55,00', '-405,00']
        }
        st.dataframe(pd.DataFrame(example_data))
        st.caption("O arquivo deve conter pelo menos as colunas de data (Abertura/Fechamento) e 'Total'. Outras colunas são opcionais.")

if __name__ == "__main__":
    main()
