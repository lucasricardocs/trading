# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta, date
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import time

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "16ttz6MqheB925H18CVH9UqlVMnzk9BYIIzl-4jb84aM" # ID da sua planilha
WORKSHEET_NAME = "dados"

# --- Configuração da Página e CSS Customizado (Tema Escuro) ---
st.set_page_config(
    page_title="Análise de Trading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Geral para o tema escuro */
    body {
        background-color: #1a1a1a;
        color: #f0f0f0;
    }
    .stApp {
        background-color: #1a1a1a;
    }
    /* Containers e cards */
    .st-emotion-cache-1wmy9hp {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #3a3a3a;
    }
    .st-emotion-cache-1r6y40v {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #3a3a3a;
    }
    .st-emotion-cache-1cyp85g {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #3a3a3a;
    }
    /* Sidebar */
    .st-emotion-cache-1d391kg {
        background-color: #2a2a2a;
        border-right: 1px solid #3a3a3a;
    }
    /* Títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #f0f0f0;
    }
    /* Métricas */
    [data-testid="stMetric"] {
        background-color: #2a2a2a;
        border-radius: 0.5rem;
        border: 1px solid #3a3a3a;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] > div {
        color: #cccccc;
    }
    [data-testid="stMetricValue"] {
        color: #f0f0f0;
    }
    [data-testid="stMetricDelta"] {
        color: #f0f0f0;
    }
    /* Inputs */
    .st-emotion-cache-vj1c9o {
        background-color: #3a3a3a;
        color: #f0f0f0;
    }
    .st-emotion-cache-13ln4gm {
        background-color: #3a3a3a;
        color: #f0f0f0;
    }
    /* Botões */
    .st-emotion-cache-l9rwg9 {
        background-color: #007bff;
        color: white;
    }
    .st-emotion-cache-l9rwg9:hover {
        background-color: #0056b3;
    }
    /* Mensagens de sucesso/erro/info */
    [data-testid="stSuccessAlert"] {
        background-color: #28a745;
        color: white;
    }
    [data-testid="stErrorAlert"] {
        background-color: #dc3545;
        color: white;
    }
    [data-testid="stInfoAlert"] {
        background-color: #17a2b8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Função para autenticar e carregar dados da planilha
@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro na autenticação com Google Sheets. Verifique suas credenciais em .streamlit/secrets.toml: {e}")
        return None

@st.cache_data(ttl=60)  # Cache por 1 minuto
def load_data():
    try:
        gc = get_gspread_client()
        if gc is None:
            return pd.DataFrame()
        
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            if 'ABERTURA' in df.columns:
                df['ABERTURA'] = pd.to_datetime(df['ABERTURA'], errors='coerce')
            if 'RESULTADO' in df.columns:
                # Converter para string para lidar com vírgulas, depois para float
                df['RESULTADO'] = df['RESULTADO'].astype(str).str.replace(',', '.', regex=False)
                df['RESULTADO'] = pd.to_numeric(df['RESULTADO'], errors='coerce')
            if 'QUANTIDADE' in df.columns:
                df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce')
        
        return df
    except SpreadsheetNotFound:
        st.error(f"Planilha com ID {SPREADSHEET_ID} ou worksheet '{WORKSHEET_NAME}' não encontrada. Verifique o ID, o nome da worksheet ou as permissões.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame()

def add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
    try:
        gc = get_gspread_client()
        if gc is None:
            return False
        
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        # Converter resultado para string com ponto antes de enviar para o Google Sheets
        resultado_str = str(resultado).replace(',', '.')
        
        worksheet.append_row([ativo, data_abertura.strftime('%Y-%m-%d'), quantidade, tipo_operacao, resultado_str])
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar dados na planilha: {e}")
        return False

# Título da aplicação
st.title("📈 Análise de Operações de Trading")

# Sidebar para entrada de dados
with st.sidebar:
    st.header("➕ Nova Operação")
    
    with st.form("nova_operacao"):
        ativo = st.selectbox("Ativo", ["WDOFUT", "WINFUT"])
        data_abertura = st.date_input("Data da Operação", value=date.today())
        quantidade = st.number_input("Quantidade de Contratos", min_value=1, value=1)
        tipo_operacao = st.selectbox("Tipo", ["Compra", "Venda"])
        
        # Campo de resultado com formato de vírgula e dica para esvaziar
        resultado_input = st.text_input("Resultado em R$", value="0,00", help="Use vírgula como separador decimal. Apague para inserir novo valor.")
        
        # Tentar converter para float, lidando com vírgula
        try:
            resultado = float(resultado_input.replace(',', '.'))
        except ValueError:
            st.error("Por favor, insira um valor numérico válido para o Resultado (use vírgula para decimais).")
            resultado = 0.0 # Valor padrão em caso de erro

        submitted = st.form_submit_button("Adicionar Operação")
        
        if submitted:
            if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
                st.success("Operação adicionada com sucesso!")
                st.cache_data.clear()  # Limpar cache para recarregar dados
                st.rerun()
            else:
                st.error("Erro ao adicionar operação")

# Carregar e exibir dados
df = load_data()

# Filtro por período (datas) na sidebar acima das métricas
with st.sidebar:
    st.header("🔎 Filtro de Período")
    if not df.empty and 'ABERTURA' in df.columns:
        data_min = df['ABERTURA'].min().date()
        data_max = df['ABERTURA'].max().date()
        data_inicial, data_final = st.date_input(
            "Selecione o período para análise",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max
        )
        df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
    else:
        df_filtrado = df.copy()

    # Resumo por ativo em tabela lateral
    st.header("📊 Resumo por Ativo")
    if not df_filtrado.empty:
        resumo_ativo = df_filtrado.groupby('ATIVO')['RESULTADO'].agg(['count', 'sum', 'mean']).reset_index()
        resumo_ativo.columns = ['Ativo', 'Nº Trades', 'Total (R$)', 'Média (R$)']
        st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)

if df.empty:
    st.info("📊 Nenhuma operação encontrada. Adicione sua primeira operação usando o formulário na barra lateral.")
else:
    st.success(f"✅ {len(df)} operações carregadas com sucesso!")
    
    # Exibir dados em uma tabela expansível
    with st.expander("📋 Ver todas as operações"):
        st.dataframe(df, use_container_width=True)

    # Métricas e análises (usando dados filtrados)
    if 'RESULTADO' in df_filtrado.columns and 'ABERTURA' in df_filtrado.columns:
        # Calcular métricas
        valor_total = df_filtrado['RESULTADO'].sum()
        media_resultado = df_filtrado['RESULTADO'].mean()
        
        # Agrupar por data para encontrar melhor e pior dia
        df_por_dia = df_filtrado.groupby(df_filtrado['ABERTURA'].dt.date)['RESULTADO'].sum().reset_index()
        df_por_dia.columns = ['Data', 'Resultado_Dia']
        
        if not df_por_dia.empty:
            melhor_dia = df_por_dia.loc[df_por_dia['Resultado_Dia'].idxmax()]
            pior_dia = df_por_dia.loc[df_por_dia['Resultado_Dia'].idxmin()]
        else:
            melhor_dia = pior_dia = {'Data': None, 'Resultado_Dia': 0}
        
        # Calcular outras métricas
        total_trades = len(df_filtrado)
        trades_ganhadores = len(df_filtrado[df_filtrado['RESULTADO'] > 0])
        trades_perdedores = len(df_filtrado[df_filtrado['RESULTADO'] < 0])
        taxa_acerto = (trades_ganhadores / total_trades * 100) if total_trades > 0 else 0
        
        # Exibir métricas em colunas
        st.header("📊 Resumo das Operações")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Valor Total",
                value=f"R$ {valor_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=f"{valor_total:+.2f}".replace('.', 'X').replace(',', '.').replace('X', ',') if valor_total != 0 else None
            )
        
        with col2:
            st.metric(
                label="📈 Média por Trade",
                value=f"R$ {media_resultado:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=f"{media_resultado:+.2f}".replace('.', 'X').replace(',', '.').replace('X', ',') if media_resultado != 0 else None
            )
        
        with col3:
            st.metric(
                label="🎯 Taxa de Acerto",
                value=f"{taxa_acerto:.1f}%",
                delta=f"{trades_ganhadores}/{total_trades}"
            )
        
        with col4:
            st.metric(
                label="🔢 Total de Trades",
                value=total_trades,
                delta=f"G:{trades_ganhadores} P:{trades_perdedores}"
            )
        
        # Segunda linha de métricas
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                label="🟢 Melhor Dia",
                value=f"R$ {melhor_dia['Resultado_Dia']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=melhor_dia['Data'].strftime('%d/%m/%Y') if melhor_dia['Data'] else ""
            )
        
        with col6:
            st.metric(
                label="🔴 Pior Dia",
                value=f"R$ {pior_dia['Resultado_Dia']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta=pior_dia['Data'].strftime('%d/%m/%Y') if pior_dia['Data'] else ""
            )
        
        with col7:
            maior_ganho = df_filtrado['RESULTADO'].max()
            st.metric(
                label="💎 Maior Ganho",
                value=f"R$ {maior_ganho:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta="Individual"
            )
        
        with col8:
            maior_perda = df_filtrado['RESULTADO'].min()
            st.metric(
                label="💸 Maior Perda",
                value=f"R$ {maior_perda:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                delta="Individual"
            )

        st.header("📈 Visualizações")
        
        # 1. Heatmap estilo GitHub (anualizado, NÃO sofre filtro)
        st.subheader("🔥 Heatmap de Resultados Diários (Ano Completo)")
        
        # Preparar dados para o heatmap (usando df completo, não filtrado)
        df_heatmap = df.copy()
        df_heatmap['Data'] = df_heatmap['ABERTURA'].dt.date
        df_heatmap_grouped = df_heatmap.groupby('Data')['RESULTADO'].sum().reset_index()
        
        # Criar range de datas completo
        if not df_heatmap_grouped.empty:
            date_range = pd.date_range(
                start=df_heatmap_grouped['Data'].min(),
                end=df_heatmap_grouped['Data'].max(),
                freq='D'
            )
            
            # Criar DataFrame completo com todas as datas
            df_complete = pd.DataFrame({'Data': date_range.date})
            df_heatmap_final = df_complete.merge(df_heatmap_grouped, on='Data', how='left')
            df_heatmap_final['RESULTADO'] = df_heatmap_final['RESULTADO'].fillna(0)
            
            # Adicionar informações para o heatmap
            df_heatmap_final['Ano'] = pd.to_datetime(df_heatmap_final['Data']).dt.year
            df_heatmap_final['Semana'] = pd.to_datetime(df_heatmap_final['Data']).dt.isocalendar().week
            df_heatmap_final['DiaSemana'] = pd.to_datetime(df_heatmap_final['Data']).dt.dayofweek
            
            # Criar heatmap
            heatmap = alt.Chart(df_heatmap_final).mark_rect().encode(
                x=alt.X('week(Data):O', title='Semana do Ano'),
                y=alt.Y('day(Data):O', title='Dia da Semana'),
                color=alt.Color(
                    'RESULTADO:Q',
                    scale=alt.Scale(
                        domain=[-abs(df_heatmap_final['RESULTADO']).max(), 0, abs(df_heatmap_final['RESULTADO']).max()],
                        range=['#d73027', '#f7f7f7', '#1a9850']
                    ),
                    title='Resultado (R$)'
                ),
                tooltip=['Data:T', alt.Tooltip('RESULTADO:Q', format='.2f')]
            ).properties(
                width='container',
                height=500,
                title='Heatmap de Resultados Diários'
            ).interactive()
            
            st.altair_chart(heatmap, use_container_width=True)
        
        # 2. Gráfico de área com gradiente (filtro de datas)
        st.subheader("📊 Evolução Acumulada dos Resultados")
        
        if not df_por_dia.empty:
            # Calcular resultado acumulado
            df_area = df_por_dia.copy()
            df_area = df_area.sort_values('Data')
            df_area['Resultado_Acumulado'] = df_area['Resultado_Dia'].cumsum()
            
            area_chart = alt.Chart(df_area).mark_area(
                line={'color': '#1a9850'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[
                        alt.GradientStop(color='#2a2a2a', offset=0), # Cor de fundo escura
                        alt.GradientStop(color='#1a9850', offset=1)
                    ],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Resultado_Acumulado:Q', title='Resultado Acumulado (R$)'),
                tooltip=['Data:T', alt.Tooltip('Resultado_Acumulado:Q', format='.2f'), alt.Tooltip('Resultado_Dia:Q', format='.2f')]
            ).properties(
                width='container',
                height=500,
                title='Evolução do Resultado Acumulado'
            ).interactive()
            
            st.altair_chart(area_chart, use_container_width=True)

        # 3. Gráfico de barras da evolução diária (filtro de datas)
        st.subheader("📅 Evolução Diária dos Resultados")
        if not df_por_dia.empty:
            bar_chart = alt.Chart(df_por_dia).mark_bar().encode(
                x=alt.X('Data:T', title='Data'),
                y=alt.Y('Resultado_Dia:Q', title='Resultado do Dia (R$)'),
                color=alt.condition(
                    alt.datum.Resultado_Dia > 0,
                    alt.value('#1a9850'),
                    alt.value('#d73027')
                ),
                tooltip=['Data:T', alt.Tooltip('Resultado_Dia:Q', format='.2f')]
            ).properties(
                width='container',
                height=500,
                title='Evolução Diária do Resultado'
            ).interactive()
            st.altair_chart(bar_chart, use_container_width=True)
        
        # 4. Histograma e gráfico radial lado a lado (filtro de datas)
        st.subheader("📈 Distribuição de Resultados e Performance")
        
        col_hist, col_radial = st.columns([2, 1])
        
        with col_hist:
            # Histograma de resultados
            hist_data = df_filtrado.copy()
            hist_data['Cor'] = hist_data['RESULTADO'].apply(lambda x: 'Ganho' if x > 0 else 'Perda' if x < 0 else 'Neutro')
            
            histogram = alt.Chart(hist_data).mark_bar().encode(
                x=alt.X('RESULTADO:Q', bin=alt.Bin(maxbins=20), title='Resultado (R$)'),
                y=alt.Y('count():Q', title='Frequência'),
                color=alt.Color(
                    'Cor:N',
                    scale=alt.Scale(
                        domain=['Perda', 'Neutro', 'Ganho'],
                        range=['#d73027', '#cccccc', '#1a9850'] # Cinza para neutro
                    ),
                    title='Tipo'
                ),
                tooltip=[alt.Tooltip('RESULTADO:Q', format='.2f'), 'count():Q']
            ).properties(
                width='container',
                height=500,
                title='Distribuição dos Resultados'
            ).interactive()
            
            st.altair_chart(histogram, use_container_width=True)
        
        with col_radial:
            # Gráfico de pizza para trades ganhadores vs perdedores
            pizza_data = pd.DataFrame({
                'Tipo': ['Ganhadores', 'Perdedores'],
                'Quantidade': [trades_ganhadores, trades_perdedores],
                'Cor': ['#1a9850', '#d73027']
            })
            
            if trades_perdedores == 0:
                pizza_data = pizza_data[pizza_data['Quantidade'] > 0]
            
            pie_chart = alt.Chart(pizza_data).mark_arc(
                innerRadius=50,
                outerRadius=120
            ).encode(
                theta=alt.Theta("Quantidade:Q", stack=True),
                color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Ganhadores", "Perdedores"], range=["#1a9850", "#d73027"])),
                tooltip=["Tipo:N", "Quantidade:Q"]
            ).properties(
                width='container',
                height=500,
                title="Proporção de Trades Ganhadores/Perdedores"
            ).interactive()
            
            st.altair_chart(pie_chart, use_container_width=True)

# --- Rodapé ---
st.markdown(
    """
    <hr style="border:1px solid #444;margin-top:2em;margin-bottom:1em">
    <div style="text-align:center;color:#888;font-size:0.95em;">
        Desenvolvido com <b>Python</b> • Powered by <b>Streamlit</b> + <b>Altair</b> • Dados salvos em <b>Google Sheets</b><br>
        <span style="font-size:0.85em;">© {ano} - Este painel é apenas para fins informativos e educacionais.</span>
    </div>
    """.format(ano=datetime.now().year),
    unsafe_allow_html=True
)
