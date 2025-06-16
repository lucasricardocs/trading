# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- Configurações ---
SPREADSHEET_ID = '16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM'

# Configuração da página
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- Conexão Google Sheets ---
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
        st.error(f"Erro na autenticação: {e}")
        return None

# --- Função corrigida para ler CSV com diferentes encodings ---
def read_csv_with_encoding(uploaded_file):
    """Tenta ler o CSV com diferentes encodings até encontrar o correto."""
    encodings = [
        'latin-1',      # Mais comum para arquivos brasileiros
        'cp1252',       # Windows
        'iso-8859-1',   # Latin-1
        'utf-8',        # UTF-8
        'windows-1252', # Windows específico
        'cp850',        # DOS
        'utf-16'        # UTF-16
    ]
    
    for encoding in encodings:
        try:
            uploaded_file.seek(0)  # Reset file pointer
            
            # Ler o conteúdo como texto primeiro
            content = uploaded_file.read().decode(encoding)
            
            # Dividir em linhas
            lines = content.split('\n')
            
            st.success(f"✅ Arquivo lido com encoding: {encoding}")
            return lines, encoding
            
        except UnicodeDecodeError:
            st.warning(f"⚠️ Encoding {encoding} falhou, tentando próximo...")
            continue
        except Exception as e:
            st.warning(f"⚠️ Erro com {encoding}: {e}")
            continue
    
    st.error("❌ Não foi possível ler o arquivo com nenhum encoding testado")
    return None, None

# --- Colar dados do CSV no Google Sheets ---
def copy_csv_to_sheets(uploaded_file, filename):
    try:
        gc = get_gspread_client()
        if gc is None:
            return False
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # Nome da aba
        sheet_name = filename.replace('.csv', '')[:30]
        
        # Criar ou acessar aba
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        
        # Ler arquivo CSV com encoding correto
        lines, encoding_used = read_csv_with_encoding(uploaded_file)
        
        if lines is None:
            return False
        
        st.info(f"📄 Total de linhas no arquivo: {len(lines)}")
        
        # Verificar se tem pelo menos 6 linhas
        if len(lines) < 6:
            st.error("❌ Arquivo não tem dados suficientes (mínimo 6 linhas)")
            return False
        
        # Linha 5 = cabeçalho (índice 4)
        header_line = lines[4].strip()
        if not header_line:
            st.error("❌ Linha 5 (cabeçalho) está vazia")
            return False
        
        header = header_line.split(';')
        st.success(f"✅ Cabeçalho encontrado: {len(header)} colunas")
        
        # Dados a partir da linha 6
        data_rows = []
        for i, line in enumerate(lines[5:], 6):
            if line.strip():
                cells = line.strip().split(';')
                if any(cell.strip() for cell in cells):
                    # Ajustar para mesmo número de colunas
                    while len(cells) < len(header):
                        cells.append('')
                    data_rows.append(cells[:len(header)])
        
        # Verificar dados existentes
        existing_data = worksheet.get_all_values()
        
        # Se vazio, inserir cabeçalho
        if not existing_data:
            worksheet.update('A1', [header])
            start_row = 2
        else:
            # Encontrar primeira linha vazia
            start_row = len(existing_data) + 1
        
        # Inserir dados
        if data_rows:
            end_row = start_row + len(data_rows) - 1
            range_name = f'A{start_row}:Z{end_row}'
            worksheet.update(range_name, data_rows)
        
        st.success(f"✅ {len(data_rows)} linhas copiadas para {sheet_name}")
        return True
        
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

# --- Processar dados para gráficos ---
def process_data_for_charts(uploaded_file):
    try:
        # Ler CSV com encoding correto
        lines, encoding_used = read_csv_with_encoding(uploaded_file)
        
        if lines is None:
            return None
        
        # Converter para DataFrame
        # Pular as primeiras 4 linhas e usar linha 5 como cabeçalho
        header = lines[4].strip().split(';')
        data_lines = []
        
        for line in lines[5:]:
            if line.strip():
                cells = line.strip().split(';')
                if any(cell.strip() for cell in cells):
                    while len(cells) < len(header):
                        cells.append('')
                    data_lines.append(cells[:len(header)])
        
        # Criar DataFrame
        df = pd.DataFrame(data_lines, columns=header)
        
        # Processar dados
        df.columns = df.columns.str.strip()
        
        # Encontrar coluna de data
        date_col = None
        for col in df.columns:
            if any(word in col for word in ['Abertura', 'Fechamento', 'Data']):
                date_col = col
                break
        
        # Encontrar coluna total
        total_col = None
        for col in df.columns:
            if 'Total' in col:
                total_col = col
                break
        
        if not date_col or not total_col:
            st.error("❌ Colunas necessárias não encontradas")
            return None
        
        # Limpar dados
        df = df[df[date_col].notna() & df[total_col].notna()]
        df = df[df[date_col] != '']
        df = df[df[total_col] != '']
        
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
        
        # Agrupar por data
        daily_data = df.groupby('Data')['Total'].sum().reset_index()
        
        return daily_data
        
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return None

# --- Criar heatmap com escala de cores correta ---
def create_trading_heatmap(df):
    """Cria heatmap com cinza para dias vazios, vermelho para perdas, verde para ganhos."""
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
        
        # Determinar valores máximos para escala
        max_gain = df_year['Total'].max() if not df_year.empty else 100
        max_loss = abs(df_year['Total'].min()) if not df_year.empty else 100
        
        # Criar escala de cores: vermelho para perdas, cinza para zero, verde para ganhos
        color_scale = alt.Scale(
            domain=[-max_loss, -max_loss*0.5, 0, max_gain*0.5, max_gain],
            range=['#8B0000', '#CD5C5C', '#E0E0E0', '#90EE90', '#006400'],
            type='linear'
        )
        
        # Criar heatmap
        chart = alt.Chart(full_df).mark_rect(
            stroke='white', strokeWidth=1, cornerRadius=2
        ).encode(
            x=alt.X('week:O', title=None, axis=None),
            y=alt.Y('day_name:N', sort=day_names, title=None,
                   axis=alt.Axis(labelAngle=0, labelFontSize=10, 
                               ticks=False, domain=False, grid=False)),
            color=alt.condition(
                alt.datum.display_total == None,
                alt.value('#E0E0E0'),  # Cinza claro para dias fora do ano
                alt.condition(
                    alt.datum.display_total == 0,
                    alt.value('#F5F5F5'),  # Cinza muito claro para dias sem trading
                    alt.Color('display_total:Q',
                        scale=color_scale,
                        legend=alt.Legend(
                            title="Resultado (R$)", 
                            orient='bottom',
                            gradientLength=200
                        )
                    )
                )
            ),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('day_name:N', title='Dia'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado (R$)')
            ]
        ).properties(
            height=180,
            title=f'Atividade de Trading - {current_year}'
        )
        
        return chart
        
    except Exception as e:
        st.error(f"Erro no heatmap: {e}")
        return None

# --- Criar gráfico de linha ---
def create_line_chart(df):
    if df is None or df.empty:
        return None
    
    try:
        df_sorted = df.sort_values('Data')
        df_sorted['Acumulado'] = df_sorted['Total'].cumsum()
        
        chart = alt.Chart(df_sorted).mark_line(
            point=True, strokeWidth=2
        ).encode(
            x=alt.X('Data:T', title='Data'),
            y=alt.Y('Acumulado:Q', title='Resultado Acumulado (R$)'),
            color=alt.value('#3498db'),
            tooltip=[
                alt.Tooltip('Data:T', format='%d/%m/%Y'),
                alt.Tooltip('Total:Q', format=',.2f', title='Resultado do Dia'),
                alt.Tooltip('Acumulado:Q', format=',.2f', title='Acumulado')
            ]
        ).properties(
            height=400,
            title='Evolução dos Resultados'
        )
        
        return chart
        
    except Exception:
        return None

# --- Interface Principal ---
def main():
    st.title("📈 Trading Dashboard")
    
    # Upload
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
    
    if uploaded_file:
        filename = uploaded_file.name
        
        # PASSO 1: Copiar para Google Sheets
        st.subheader("📋 Copiando dados para Google Sheets")
        if copy_csv_to_sheets(uploaded_file, filename):
            
            # PASSO 2: Processar dados
            st.subheader("📊 Processando dados para gráficos")
            processed_data = process_data_for_charts(uploaded_file)
            
            if processed_data is not None and not processed_data.empty:
                # Estatísticas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total = processed_data['Total'].sum()
                    st.metric("Total", f"R$ {total:,.2f}")
                
                with col2:
                    dias = len(processed_data)
                    st.metric("Dias", dias)
                
                with col3:
                    positivos = len(processed_data[processed_data['Total'] > 0])
                    st.metric("Dias +", positivos)
                
                with col4:
                    media = processed_data['Total'].mean()
                    st.metric("Média", f"R$ {media:,.2f}")
                
                # Gráficos
                st.subheader("🔥 Heatmap de Atividade")
                heatmap = create_trading_heatmap(processed_data)
                if heatmap:
                    st.altair_chart(heatmap, use_container_width=True)
                
                st.subheader("📈 Evolução dos Resultados")
                line_chart = create_line_chart(processed_data)
                if line_chart:
                    st.altair_chart(line_chart, use_container_width=True)
                
                # Legenda explicativa
                st.info("""
                **Como interpretar o heatmap:**
                - 🟩 **Verde escuro**: Maiores ganhos
                - 🟢 **Verde claro**: Ganhos menores
                - ⬜ **Cinza claro**: Dias sem trading
                - 🟥 **Vermelho claro**: Perdas menores
                - 🟥 **Vermelho escuro**: Maiores perdas
                - Passe o mouse sobre os quadrados para ver detalhes
                """)
                
                # Dados processados
                with st.expander("📊 Dados por dia"):
                    display_df = processed_data.copy()
                    display_df['Data'] = display_df['Data'].dt.strftime('%d/%m/%Y')
                    display_df['Total'] = display_df['Total'].apply(lambda x: f"R$ {x:,.2f}")
                    st.dataframe(display_df, use_container_width=True)
            
            else:
                st.error("Não foi possível processar os dados")
    
    else:
        st.info("👆 Faça upload do arquivo CSV")
        
        # Exemplo com formato exato
        st.subheader("Formato esperado do arquivo")
        st.markdown("**O arquivo deve ter exatamente este cabeçalho na linha 5:**")
        
        example_header = {
            'Subconta': ['70568938', '70568938', '70568938'],
            'Ativo': ['WDON25', 'WDON25', 'WDON25'],
            'Abertura': ['16/06/2025 09:00', '16/06/2025 09:18', '16/06/2025 09:49'],
            'Fechamento': ['16/06/2025 09:17', '16/06/2025 09:49', '16/06/2025 10:11'],
            'Tempo Operação': ['17min', '30min44s', '22min12s'],
            'Qtd Compra': ['2', '4', '3'],
            'Qtd Venda': ['2', '4', '3'],
            'Lado': ['V', 'C', 'V'],
            'Preço Compra': ['5.537,00', '5.536,88', '5.540,67'],
            'Preço Venda': ['5.541,00', '5.533,50', '5.529,00'],
            'Preço de Mercado': ['5.549,50', '5.549,50', '5.549,50'],
            'Res. Intervalo': ['80', '-135', '-350'],
            'Res. Intervalo (%)': ['4', '-3,38', '-11,67'],
            'Número Operação': ['1', '2', '3'],
            'Res. Operação': ['80', '-135', '-350'],
            'Res. Operação (%)': ['4', '-3,38', '-11,67'],
            'TET': ['30min39s', '17min39s', '30min49s'],
            'Total': ['80', '-135', '-405']
        }
        
        st.dataframe(pd.DataFrame(example_header))
        st.caption("**Importante:** O cabeçalho deve estar exatamente na linha 5 do arquivo CSV, e os dados devem começar na linha 6.")

if __name__ == "__main__":
    main()
