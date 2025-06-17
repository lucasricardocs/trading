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

# Injetar CSS e JavaScript para o background animado
def inject_custom_css():
    """Injeta CSS customizado para o background animado."""
    css_content = """
    <style>
    /* CSS para Background Animado com Fagulhas Douradas */
    
    /* Importar fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e estilo base */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0f0f0f 100%) !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Container principal */
    .main .block-container {
        background: rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(255, 215, 0, 0.2) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        padding: 2rem !important;
        margin-top: 1rem !important;
    }
    
    /* Container para as partículas */
    .particles-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
        overflow: hidden;
    }
    
    /* Estilo das partículas/fagulhas */
    .particle {
        position: absolute;
        width: 3px;
        height: 3px;
        background: radial-gradient(circle, #ffd700 0%, #ffb347 50%, transparent 100%);
        border-radius: 50%;
        opacity: 0;
        animation: sparkle-rise linear infinite;
        box-shadow: 0 0 6px #ffd700, 0 0 12px #ffa500;
    }
    
    /* Partículas maiores ocasionais */
    .particle.large {
        width: 5px;
        height: 5px;
        box-shadow: 0 0 10px #ffd700, 0 0 20px #ffa500, 0 0 30px #ff8c00;
    }
    
    /* Partículas pequenas */
    .particle.small {
        width: 2px;
        height: 2px;
        box-shadow: 0 0 4px #ffd700, 0 0 8px #ffa500;
    }
    
    /* Animação principal das fagulhas subindo */
    @keyframes sparkle-rise {
        0% {
            transform: translateY(100vh) translateX(0) scale(0);
            opacity: 0;
        }
        10% {
            opacity: 1;
            transform: translateY(90vh) translateX(10px) scale(1);
        }
        50% {
            opacity: 0.8;
            transform: translateY(50vh) translateX(-20px) scale(1.2);
        }
        80% {
            opacity: 0.4;
            transform: translateY(20vh) translateX(15px) scale(0.8);
        }
        100% {
            transform: translateY(-10vh) translateX(-10px) scale(0);
            opacity: 0;
        }
    }
    
    /* Variações de animação para movimento mais natural */
    .particle:nth-child(odd) {
        animation-name: sparkle-rise-left;
    }
    
    .particle:nth-child(even) {
        animation-name: sparkle-rise-right;
    }
    
    @keyframes sparkle-rise-left {
        0% {
            transform: translateY(100vh) translateX(0) rotate(0deg) scale(0);
            opacity: 0;
        }
        10% {
            opacity: 1;
            transform: translateY(90vh) translateX(-15px) rotate(45deg) scale(1);
        }
        50% {
            opacity: 0.8;
            transform: translateY(50vh) translateX(-30px) rotate(180deg) scale(1.2);
        }
        80% {
            opacity: 0.4;
            transform: translateY(20vh) translateX(-10px) rotate(270deg) scale(0.8);
        }
        100% {
            transform: translateY(-10vh) translateX(5px) rotate(360deg) scale(0);
            opacity: 0;
        }
    }
    
    @keyframes sparkle-rise-right {
        0% {
            transform: translateY(100vh) translateX(0) rotate(0deg) scale(0);
            opacity: 0;
        }
        10% {
            opacity: 1;
            transform: translateY(90vh) translateX(15px) rotate(-45deg) scale(1);
        }
        50% {
            opacity: 0.8;
            transform: translateY(50vh) translateX(30px) rotate(-180deg) scale(1.2);
        }
        80% {
            opacity: 0.4;
            transform: translateY(20vh) translateX(10px) rotate(-270deg) scale(0.8);
        }
        100% {
            transform: translateY(-10vh) translateX(-5px) rotate(-360deg) scale(0);
            opacity: 0;
        }
    }
    
    /* Efeito de brilho adicional no fundo */
    .particles-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(ellipse at bottom, rgba(255, 215, 0, 0.1) 0%, transparent 50%);
        animation: glow-pulse 4s ease-in-out infinite alternate;
    }
    
    @keyframes glow-pulse {
        0% {
            opacity: 0.3;
        }
        100% {
            opacity: 0.7;
        }
    }
    
    /* Estilos para elementos do Streamlit */
    .stSelectbox > div > div {
        background-color: rgba(26, 26, 26, 0.8) !important;
        border: 1px solid rgba(255, 215, 0, 0.3) !important;
        color: #ffffff !important;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #ffd700, #ffb347) !important;
        color: #000 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #ffb347, #ffd700) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4) !important;
    }
    
    /* Estilo para métricas */
    .metric-container {
        background: rgba(26, 26, 26, 0.6) !important;
        border: 1px solid rgba(255, 215, 0, 0.3) !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    /* Estilo para gráficos */
    .stPlotlyChart {
        background: rgba(26, 26, 26, 0.4) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 215, 0, 0.2) !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(10, 10, 10, 0.9) !important;
        border-right: 1px solid rgba(255, 215, 0, 0.3) !important;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #ffd700 !important;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.3) !important;
    }
    
    /* Texto geral */
    .stMarkdown, .stText {
        color: #ffffff !important;
    }
    
    /* Upload de arquivo */
    .stFileUploader > div {
        background: rgba(26, 26, 26, 0.8) !important;
        border: 2px dashed rgba(255, 215, 0, 0.5) !important;
        border-radius: 10px !important;
    }
    </style>
    """
    
    js_content = """
    <script>
    // JavaScript para gerar partículas dinamicamente
    function createParticles() {
        const container = document.querySelector('.particles-container');
        if (!container) {
            // Criar container se não existir
            const newContainer = document.createElement('div');
            newContainer.className = 'particles-container';
            document.body.appendChild(newContainer);
            return createParticles();
        }
        
        // Limpar partículas existentes
        container.innerHTML = '';
        
        // Número de partículas baseado no tamanho da tela
        const particleCount = Math.floor(window.innerWidth / 20);
        
        for (let i = 0; i < particleCount; i++) {
            createParticle(container);
        }
    }
    
    function createParticle(container) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // Adicionar classes aleatórias para variação
        const rand = Math.random();
        if (rand < 0.1) {
            particle.classList.add('large');
        } else if (rand < 0.3) {
            particle.classList.add('small');
        }
        
        // Posição horizontal aleatória
        const leftPosition = Math.random() * 100;
        particle.style.left = leftPosition + '%';
        
        // Duração da animação aleatória (entre 3 e 8 segundos)
        const duration = 3 + Math.random() * 5;
        particle.style.animationDuration = duration + 's';
        
        // Delay aleatório para início da animação
        const delay = Math.random() * 2;
        particle.style.animationDelay = delay + 's';
        
        container.appendChild(particle);
        
        // Remover partícula após a animação e criar uma nova
        setTimeout(() => {
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
                createParticle(container);
            }
        }, (duration + delay) * 1000);
    }
    
    // Inicializar partículas
    function initializeParticles() {
        createParticles();
        
        // Recriar partículas quando a janela for redimensionada
        window.addEventListener('resize', createParticles);
    }
    
    // Aguardar o DOM carregar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeParticles);
    } else {
        initializeParticles();
    }
    
    // Para Streamlit, aguardar o carregamento completo
    setTimeout(initializeParticles, 1000);
    </script>
    """
    
    st.markdown(css_content, unsafe_allow_html=True)
    st.markdown(js_content, unsafe_allow_html=True)

# Chamar a função de injeção de CSS
inject_custom_css()

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
        # Para desenvolvimento local, usar arquivo de credenciais
        # Para produção, usar st.secrets
        if 'google_credentials' in st.secrets:
            credentials_info = dict(st.secrets["google_credentials"])
            credentials = Credentials.from_service_account_info(
                credentials_info,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
        else:
            st.warning("⚠️ Credenciais do Google Sheets não configuradas")
            return None
        
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
    """Processa os dados de trading do CSV baseado na estrutura da tabela fornecida."""
    # Limpar e processar as colunas
    df = df.copy()
    
    # Limpar nomes das colunas (remover espaços extras)
    df.columns = df.columns.str.strip()
    
    # Procurar pela coluna de Data (Abertura ou Fechamento)
    date_col = None
    for col in df.columns:
        if any(word in col for word in ['Abertura', 'Fechamento', 'Data']):
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
    def convert_total(value):
        try:
            if pd.isna(value) or value == '':
                return 0
            
            # Converter para string e limpar
            value_str = str(value).strip()
            
            # Remover caracteres não numéricos exceto - e .
            value_str = value_str.replace(',', '.')
            value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
            
            return float(value_str) if value_str else 0
        except:
            return 0
    
    df['Total'] = df[total_col].apply(convert_total)
    
    # Remover linhas com datas ou totais inválidos
    df = df.dropna(subset=['Data'])
    
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
        
        # Processar dados para dashboard
        processed_data = process_trading_data(df_original)
        
        # Salvar dados processados na aba 'dados'
        gc = get_gspread_client()
        if gc:
            try:
                spreadsheet = gc.open_by_key(SPREADSHEET_ID)
                
                # Verificar se aba 'dados' existe, se não, criar
                try:
                    dados_worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
                except:
                    dados_worksheet = spreadsheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=10)
                
                # Limpar aba dados
                dados_worksheet.clear()
                
                # Inserir cabeçalho
                dados_worksheet.update('A1', [['Data', 'Total']])
                
                # Preparar dados para inserção
                data_for_sheets = []
                for _, row in processed_data.iterrows():
                    data_for_sheets.append([
                        row['Data'].strftime('%d/%m/%Y'),
                        row['Total']
                    ])
                
                # Inserir dados
                if data_for_sheets:
                    range_name = f'A2:B{len(data_for_sheets) + 1}'
                    dados_worksheet.update(range_name, data_for_sheets)
                
                st.success(f"✅ Dados processados salvos na aba '{WORKSHEET_NAME}'")
                
            except Exception as e:
                st.error(f"Erro ao salvar dados processados: {e}")
        
        return processed_data, "Dados processados com sucesso"
        
    except Exception as e:
        return pd.DataFrame(), f"Erro no processamento: {str(e)}"

# --- FUNÇÕES DE VISUALIZAÇÃO ---
def create_heatmap(df):
    """Cria heatmap estilo GitHub."""
    if df.empty:
        return alt.Chart().mark_text(text="Sem dados").resolve_scale(color='independent')
    
    # Preparar dados para heatmap
    df_heatmap = df.copy()
    df_heatmap['Data'] = pd.to_datetime(df_heatmap['Data'])
    df_heatmap['Ano'] = df_heatmap['Data'].dt.year
    df_heatmap['Semana'] = df_heatmap['Data'].dt.isocalendar().week
    df_heatmap['DiaSemana'] = df_heatmap['Data'].dt.dayofweek
    
    # Criar escala de cores baseada nos valores
    max_val = df_heatmap['Total'].max()
    min_val = df_heatmap['Total'].min()
    
    heatmap = alt.Chart(df_heatmap).mark_rect().add_selection(
        alt.selection_single()
    ).encode(
        x=alt.X('Semana:O', title='Semana do Ano'),
        y=alt.Y('DiaSemana:O', title='Dia da Semana', 
                scale=alt.Scale(domain=[0,1,2,3,4,5,6])),
        color=alt.Color('Total:Q', 
                       scale=alt.Scale(scheme='goldgreen', domain=[min_val, max_val]),
                       title='Total'),
        tooltip=['Data:T', 'Total:Q']
    ).properties(
        width=800,
        height=200,
        title="Heatmap de Atividade (Estilo GitHub)"
    )
    
    return heatmap

def create_area_chart(df):
    """Cria gráfico de área com evolução acumulada."""
    if df.empty:
        return alt.Chart().mark_text(text="Sem dados").resolve_scale(color='independent')
    
    df_area = df.copy()
    df_area['Data'] = pd.to_datetime(df_area['Data'])
    df_area = df_area.sort_values('Data')
    df_area['Total_Acumulado'] = df_area['Total'].cumsum()
    
    area_chart = alt.Chart(df_area).mark_area(
        color='gold',
        opacity=0.7
    ).encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Total_Acumulado:Q', title='Total Acumulado'),
        tooltip=['Data:T', 'Total:Q', 'Total_Acumulado:Q']
    ).properties(
        width=800,
        height=300,
        title="Evolução Acumulada"
    )
    
    return area_chart

def create_histogram(df):
    """Cria histograma diário."""
    if df.empty:
        return alt.Chart().mark_text(text="Sem dados").resolve_scale(color='independent')
    
    histogram = alt.Chart(df).mark_bar(
        color='gold'
    ).encode(
        x=alt.X('Data:T', title='Data'),
        y=alt.Y('Total:Q', title='Total'),
        tooltip=['Data:T', 'Total:Q']
    ).properties(
        width=800,
        height=300,
        title="Histograma Diário"
    )
    
    return histogram

def create_radial_chart(df):
    """Cria gráfico radial."""
    if df.empty:
        return alt.Chart().mark_text(text="Sem dados").resolve_scale(color='independent')
    
    # Preparar dados para gráfico radial (por dia da semana)
    df_radial = df.copy()
    df_radial['Data'] = pd.to_datetime(df_radial['Data'])
    df_radial['DiaSemana'] = df_radial['Data'].dt.day_name()
    
    radial_data = df_radial.groupby('DiaSemana')['Total'].sum().reset_index()
    
    radial_chart = alt.Chart(radial_data).mark_arc(
        innerRadius=50,
        outerRadius=120
    ).encode(
        theta=alt.Theta('Total:Q'),
        color=alt.Color('DiaSemana:N', scale=alt.Scale(scheme='gold')),
        tooltip=['DiaSemana:N', 'Total:Q']
    ).properties(
        width=300,
        height=300,
        title="Distribuição por Dia da Semana"
    )
    
    return radial_chart

def calculate_statistics(df):
    """Calcula estatísticas detalhadas."""
    if df.empty:
        return {}
    
    stats = {
        'total_geral': df['Total'].sum(),
        'media_diaria': df['Total'].mean(),
        'mediana': df['Total'].median(),
        'desvio_padrao': df['Total'].std(),
        'maximo': df['Total'].max(),
        'minimo': df['Total'].min(),
        'dias_ativos': len(df),
        'periodo': f"{df['Data'].min().strftime('%d/%m/%Y')} - {df['Data'].max().strftime('%d/%m/%Y')}"
    }
    
    return stats

# --- INTERFACE PRINCIPAL ---
def main():
    """Função principal do aplicativo."""
    
    # Inicializar session state
    initialize_session_state()
    
    # Título principal
    st.title("📈 Trading Activity Dashboard")
    st.markdown("---")
    
    # Sidebar para controles
    with st.sidebar:
        st.header("🎛️ Controles")
        
        # Upload de CSV
        st.subheader("📁 Upload CSV")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo CSV",
            type=['csv'],
            help="Faça upload do arquivo CSV com dados de trading"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ Arquivo carregado: {uploaded_file.name}")
            
            # Botões de processamento
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📋 Colar no Sheets", help="Copia dados do CSV para Google Sheets"):
                    with st.spinner("Copiando dados..."):
                        success, message = copy_csv_to_sheets(uploaded_file, uploaded_file.name)
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
            
            with col2:
                if st.button("🔄 Processar Dados", help="Processa dados para dashboard"):
                    with st.spinner("Processando dados..."):
                        processed_data, message = process_data_for_dashboard(uploaded_file, uploaded_file.name)
                        if not processed_data.empty:
                            st.session_state.filtered_data = processed_data
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
        
        st.markdown("---")
        
        # Carregar dados do Google Sheets
        st.subheader("📊 Dados do Sheets")
        if st.button("🔄 Carregar do Google Sheets"):
            with st.spinner("Carregando dados..."):
                data = load_data_from_sheets()
                if data is not None:
                    st.session_state.filtered_data = data
                    st.success("✅ Dados carregados com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao carregar dados")
        
        # Filtros
        if st.session_state.filtered_data is not None and not st.session_state.filtered_data.empty:
            st.markdown("---")
            st.subheader("🔍 Filtros")
            
            df = st.session_state.filtered_data
            df['Data'] = pd.to_datetime(df['Data'])
            
            # Filtro de ano
            anos_disponiveis = sorted(df['Data'].dt.year.unique())
            ano_selecionado = st.selectbox("Ano", ['Todos'] + anos_disponiveis)
            
            # Filtro de mês
            meses_disponiveis = sorted(df['Data'].dt.month.unique())
            mes_selecionado = st.selectbox("Mês", ['Todos'] + meses_disponiveis)
            
            # Aplicar filtros
            df_filtrado = df.copy()
            if ano_selecionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Data'].dt.year == ano_selecionado]
            if mes_selecionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Data'].dt.month == mes_selecionado]
            
            st.session_state.filtered_data = df_filtrado
    
    # Área principal
    if st.session_state.filtered_data is not None and not st.session_state.filtered_data.empty:
        df = st.session_state.filtered_data
        
        # Estatísticas principais
        st.subheader("📊 Estatísticas Principais")
        stats = calculate_statistics(df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Total Geral", f"R$ {stats['total_geral']:,.2f}")
        with col2:
            st.metric("📈 Média Diária", f"R$ {stats['media_diaria']:,.2f}")
        with col3:
            st.metric("📅 Dias Ativos", stats['dias_ativos'])
        with col4:
            st.metric("📊 Máximo", f"R$ {stats['maximo']:,.2f}")
        
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("📉 Mínimo", f"R$ {stats['minimo']:,.2f}")
        with col6:
            st.metric("🎯 Mediana", f"R$ {stats['mediana']:,.2f}")
        with col7:
            st.metric("📏 Desvio Padrão", f"R$ {stats['desvio_padrao']:,.2f}")
        with col8:
            st.metric("📆 Período", stats['periodo'])
        
        st.markdown("---")
        
        # Visualizações
        st.subheader("📈 Visualizações")
        
        # Heatmap
        st.markdown("### 🔥 Heatmap de Atividade")
        heatmap = create_heatmap(df)
        st.altair_chart(heatmap, use_container_width=True)
        
        # Gráficos em colunas
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Evolução Acumulada")
            area_chart = create_area_chart(df)
            st.altair_chart(area_chart, use_container_width=True)
            
            st.markdown("### 📊 Histograma Diário")
            histogram = create_histogram(df)
            st.altair_chart(histogram, use_container_width=True)
        
        with col2:
            st.markdown("### 🎯 Distribuição por Dia da Semana")
            radial_chart = create_radial_chart(df)
            st.altair_chart(radial_chart, use_container_width=True)
            
            # Tabela de dados
            st.markdown("### 📋 Dados Recentes")
            st.dataframe(df.tail(10), use_container_width=True)
    
    else:
        # Tela inicial
        st.info("👋 Bem-vindo ao Trading Activity Dashboard!")
        st.markdown("""
        ### 🚀 Como usar:
        
        1. **📁 Upload CSV**: Faça upload do seu arquivo CSV na sidebar
        2. **📋 Colar no Sheets**: Copie os dados para o Google Sheets
        3. **🔄 Processar Dados**: Processe os dados para o dashboard
        4. **📊 Visualizar**: Explore os gráficos e estatísticas
        
        ### ✨ Funcionalidades:
        - 🔗 Integração completa com Google Sheets
        - 📊 Dashboard com heatmap estilo GitHub
        - 📈 Gráficos interativos e estatísticas detalhadas
        - 🎛️ Filtros avançados por ano e mês
        - 🔄 Processamento automático de dados CSV
        """)

if __name__ == "__main__":
    main()

