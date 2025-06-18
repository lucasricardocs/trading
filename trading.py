# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
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
            st.error("Credenciais não encontradas no `st.secrets`. Por favor, configure-as.")
            return None
        
        credentials_dict = st.secrets["google_credentials"]
        if not credentials_dict:
            st.error("Credenciais vazias. Verifique a configuração de `st.secrets`.")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro ao autenticar com o Google Sheets: {e}")
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
            st.error(f"Planilha com ID '{SPREADSHEET_ID}' não encontrada. Verifique o ID e as permissões.")
            return None
        except Exception as e:
            st.error(f"Erro ao acessar a planilha: {e}")
            return None
    return None

@st.cache_data(ttl=60)
def load_data():
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                st.info("Nenhum dado encontrado na planilha. Adicione algumas operações.")
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            # Conversão de tipos de dados
            if 'ABERTURA' in df.columns:
                df['ABERTURA'] = pd.to_datetime(df['ABERTURA'], errors='coerce')
            
            if 'RESULTADO' in df.columns:
                df['RESULTADO'] = df['RESULTADO'].astype(str).str.replace(',', '.', regex=False)
                df['RESULTADO'] = pd.to_numeric(df['RESULTADO'], errors='coerce').fillna(0)
            
            if 'QUANTIDADE' in df.columns:
                df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0)

            # Cálculo de CUSTO e RESULTADO_LIQUIDO (vetorizado)
            if 'ATIVO' in df.columns and 'QUANTIDADE' in df.columns and 'RESULTADO' in df.columns:
                custos = {'WDOFUT': 1.09, 'WINFUT': 0.39}
                df['CUSTO'] = df['ATIVO'].map(custos).fillna(0) * df['QUANTIDADE'] * 2
                df['RESULTADO_LIQUIDO'] = df['RESULTADO'] - df['CUSTO']
            else:
                df['CUSTO'] = 0
                df['RESULTADO_LIQUIDO'] = df.get('RESULTADO', 0)

            return df
        except Exception as e:
            st.error(f"Erro ao carregar ou processar os dados da planilha: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado):
    worksheet = get_worksheet()
    if worksheet:
        try:
            resultado_str = str(resultado).replace(',', '.')
            worksheet.append_row([ativo, data_abertura.strftime('%Y-%m-%d'), quantidade, tipo_operacao, resultado_str])
            return True
        except Exception as e:
            st.error(f"Erro ao adicionar trade à planilha: {e}")
            return False
    return False

def formatar_moeda(valor):
    """Formata valor monetário com símbolo R$ e separadores brasileiros."""
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

def create_heatmap_trading_style(df_heatmap_final):
    """Heatmap aprimorado no estilo trading"""
    if df_heatmap_final.empty:
        return None
    
    current_year = datetime.now().year
    first_day_of_year = pd.Timestamp(f'{current_year}-01-01')
    first_day_weekday = first_day_of_year.weekday()
    days_before = first_day_weekday
    start_date = first_day_of_year - pd.Timedelta(days=days_before)
    end_date = datetime(current_year, 12, 31)
    days_after = 6 - end_date.weekday()
    if days_after < 6:
        end_date = end_date + pd.Timedelta(days=days_after)
    
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    full_df = pd.DataFrame({'Data': all_dates.date})
    full_df['is_current_year'] = pd.to_datetime(full_df['Data']).dt.year == current_year
    full_df = full_df.merge(df_heatmap_final, on='Data', how='left')
    full_df['RESULTADO_LIQUIDO'] = full_df['RESULTADO_LIQUIDO'].fillna(0)
    full_df['display_resultado'] = full_df['RESULTADO_LIQUIDO'].copy()
    mask_not_current_year = ~full_df['is_current_year']
    full_df.loc[mask_not_current_year, 'display_resultado'] = None
    full_df['Data_dt'] = pd.to_datetime(full_df['Data'])
    full_df['day_of_week'] = full_df['Data_dt'].dt.weekday
    
    # Dias da semana completos
    day_name_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    day_display_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    
    full_df['month'] = full_df['Data_dt'].dt.month
    full_df['month_name'] = full_df['Data_dt'].dt.strftime('%b')
    full_df['week_corrected'] = ((full_df['Data_dt'] - start_date).dt.days // 7)
    
    # Definir categorias de cores baseado no valor
    def get_color_category(row):
        if pd.isna(row['display_resultado']) or row['display_resultado'] is None:
            return 'fora_ano'
        elif row['display_resultado'] == 0:
            return 'neutro'
        elif row['display_resultado'] > 0:
            # 3 níveis de verde
            if row['display_resultado'] > 3000:
                return 'positivo_forte'
            elif row['display_resultado'] > 1000:
                return 'positivo_medio'
            else:
                return 'positivo_fraco'
        else:
            # 3 níveis de vermelho
            if row['display_resultado'] < -3000:
                return 'negativo_forte'
            elif row['display_resultado'] < -1000:
                return 'negativo_medio'
            else:
                return 'negativo_fraco'
    
    full_df['color_category'] = full_df.apply(get_color_category, axis=1)
    
    # Mapeamento de cores aprimorado
    color_scale = alt.Scale(
        domain=['fora_ano', 'neutro', 
                'positivo_fraco', 'positivo_medio', 'positivo_forte',
                'negativo_fraco', 'negativo_medio', 'negativo_forte'],
        range=['transparent', COLOR_BASE,
               '#e6f4ea', '#a7d7b8', COLOR_POSITIVE,  # Tons de verde
               '#fce8e6', '#f4a9a9', COLOR_NEGATIVE]   # Tons de vermelho
    )
    
    # Legendas dos meses
    month_labels = full_df[full_df['is_current_year']].groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    months_chart = alt.Chart(month_labels).mark_text(
        align='center', baseline='bottom', fontSize=12, dy=-5,
        color='#555', fontWeight='bold'
    ).encode(
        x=alt.X('week_corrected:O', axis=None),
        text='month_name:N'
    )

    # Heatmap principal
    heatmap = alt.Chart(full_df).mark_rect(
        stroke='white',
        strokeWidth=1,
        cornerRadius=2
    ).encode(
        x=alt.X('week_corrected:O', title=None, axis=None),
        y=alt.Y('day_display_name:N', sort=day_display_names, title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=11, ticks=False, 
                             domain=False, grid=False, labelColor='#555')),
        color=alt.Color('color_category:N', scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
            alt.Tooltip('day_display_name:N', title='Dia da Semana'),
            alt.Tooltip('RESULTADO_LIQUIDO:Q', title='Resultado (R$)', format='.2f', formatType='currency') # Melhoria aqui
        ]
    ).properties(
        height=220
    )

    # Legenda de cores
    legend_data = pd.DataFrame({
        'Categoria': ['Forte Positivo', 'Médio Positivo', 'Fraco Positivo', 
                      'Neutro', 'Fraco Negativo', 'Médio Negativo', 'Forte Negativo'],
        'Cor': [COLOR_POSITIVE, '#a7d7b8', '#e6f4ea', COLOR_BASE, 
                '#fce8e6', '#f4a9a9', COLOR_NEGATIVE],
        'Valor Min': [3000, 1000, 0.01, 0, -0.01, -1000, -3000],
        'Valor Max': [None, 3000, 1000, 0.01, -0.01, -1000, None]
    })
    
    legend = alt.Chart(legend_data).mark_rect().encode(
        y=alt.Y('Categoria:N', axis=alt.Axis(title=None, orient='right')),
        color=alt.Color('Cor:N', scale=alt.Scale(domain=legend_data['Cor'].tolist(), 
                                               range=legend_data['Cor'].tolist()),
                       legend=None)
    ).properties(
        title='Legenda de Resultados',
        width=20,
        height=200
    )

    # Combinar gráficos
    chart = alt.vconcat(months_chart, heatmap, spacing=1).configure_view(
        strokeWidth=0
    ).configure(
        background='transparent'
    )
    
    return chart

def create_evolution_chart(df_area):
    """Gráfico de evolução com stroke 2"""
    area_chart = alt.Chart(df_area).mark_area(
        line={'strokeWidth': 2, 'stroke': '#ffffff'},
        opacity=0.8,
        interpolate='monotone'
    ).encode(
        x=alt.X('Data:T', title=''),
        y=alt.Y('Acumulado:Q', title=''),
        color=alt.condition(
            alt.datum.Acumulado >= 0,
            alt.value(COLOR_POSITIVE),
            alt.value(COLOR_NEGATIVE)
        ),
        tooltip=[
            alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'), 
            alt.Tooltip('Acumulado:Q', format='.2f', title='Acumulado', formatType='currency'), # Melhoria aqui
            alt.Tooltip('Resultado_Liquido_Dia:Q', format='.2f', title='Dia', formatType='currency') # Melhoria aqui
        ]
    ).properties(height=300)
    
    return area_chart.configure(background='transparent')

def create_radial_chart(trades_ganhadores, trades_perdedores):
    """Cria gráfico radial minimalista"""
    if trades_ganhadores == 0 and trades_perdedores == 0:
        return None
    
    source = pd.DataFrame({
        "values": [trades_ganhadores, trades_perdedores],
        "labels": ["Ganhadores", "Perdedores"]
    })
    
    source = source[source['values'] > 0]
    
    if source.empty:
        return None
    
    base = alt.Chart(source).encode(
        alt.Theta("values:Q").stack(True),
        alt.Radius("values").scale(type="sqrt", zero=True, rangeMin=20),
        color=alt.Color("labels:N", 
                       scale=alt.Scale(domain=["Ganhadores", "Perdedores"], 
                                     range=[COLOR_POSITIVE, COLOR_NEGATIVE]),
                       legend=None)
    )
    
    c1 = base.mark_arc(innerRadius=20, stroke="#fff", strokeWidth=2)
    
    c2 = base.mark_text(radiusOffset=15, color='white', fontSize=12, fontWeight='bold').encode(
        text="values:Q"
    )
    
    chart = (c1 + c2).properties(
        height=250
    )
    
    return chart.configure(background='transparent')

def create_histogram_chart(df_filtrado):
    """Cria histograma de resultados"""
    return alt.Chart(df_filtrado).mark_bar(
        stroke='white',
        strokeWidth=2
    ).encode(
        alt.X("RESULTADO_LIQUIDO:Q", bin=True, title="Resultado (R$)", axis=alt.Axis(format='.2f', formatType='currency')),
        alt.Y('count()', title="Quantidade de Trades"),
        color=alt.value(COLOR_NEUTRAL),
        tooltip=[
            alt.Tooltip('RESULTADO_LIQUIDO:Q', title='Resultado (R$)', bin=True, format='.2f', formatType='currency'),
            alt.Tooltip('count()', title='Trades')
        ]
    ).properties(height=300).configure(background='transparent')

def create_hourly_chart(df_filtrado):
    """Gráfico de performance por horário"""
    df_filtrado['HORA'] = df_filtrado['ABERTURA'].dt.hour
    performance_horario = df_filtrado.groupby('HORA')['RESULTADO_LIQUIDO'].mean().reset_index()
    
    return alt.Chart(performance_horario).mark_bar(
        stroke='white',
        strokeWidth=2
    ).encode(
        x=alt.X('HORA:O', title='Hora do Dia'),
        y=alt.Y('RESULTADO_LIQUIDO:Q', title='Resultado Médio (R$)', axis=alt.Axis(format='.2f', formatType='currency')),
        color=alt.condition(
            alt.datum.RESULTADO_LIQUIDO >= 0,
            alt.value(COLOR_POSITIVE),
            alt.value(COLOR_NEGATIVE)
        ),
        tooltip=[
            alt.Tooltip('HORA:O', title='Hora'),
            alt.Tooltip('RESULTADO_LIQUIDO:Q', title='Resultado Médio (R$)', format='.2f', formatType='currency')
        ]
    ).properties(height=300).configure(background='transparent')

def format_top_trades(df_trades):
    """Formata DataFrame de top trades para exibição."""
    df_formatted = df_trades.copy()
    if 'ABERTURA' in df_formatted.columns:
        df_formatted['ABERTURA'] = df_formatted['ABERTURA'].dt.strftime('%d/%m/%Y')
    if 'RESULTADO_LIQUIDO' in df_formatted.columns:
        df_formatted['RESULTADO_LIQUIDO'] = df_formatted['RESULTADO_LIQUIDO'].apply(formatar_moeda)
    return df_formatted

# --- Interface ---
st.title("📊 Trading Analytics")

# --- Sidebar ---
with st.sidebar:
    st.header("Operações")
    
    with st.expander("➕ Adicionar Nova Operação", expanded=True):
        with st.form("nova_operacao"):
            ativo = st.selectbox("Ativo", ["WDOFUT", "WINFUT"])
            data_abertura = st.date_input("Data", value=date.today())
            quantidade = st.number_input("Contratos", min_value=1, value=1)
            tipo_operacao = st.selectbox("Tipo", ["Compra", "Venda"])
            resultado_input = st.text_input("Resultado (R$)", value="0,00")
            
            try:
                resultado_valor = float(resultado_input.replace(',', '.'))
            except ValueError:
                st.error("Valor inválido. Use números com vírgula decimal (ex: 123,45).")
                resultado_valor = 0.0

            submitted = st.form_submit_button("✅ Adicionar")
            
            if submitted:
                if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado_valor):
                    st.success("✅ Trade adicionado com sucesso!")
                    st.cache_data.clear() # Limpa o cache para recarregar os dados
                    st.rerun() # Força o rerun para atualizar a interface
                else:
                    st.error("❌ Erro ao adicionar trade. Verifique os logs.")

    st.header("Filtros")
    
    df = load_data()
    
    with st.expander("🔎 Período", expanded=True):
        if not df.empty and 'ABERTURA' in df.columns and not df['ABERTURA'].isnull().all():
            data_min = df['ABERTURA'].min().date()
            data_max = df['ABERTURA'].max().date()
            data_inicial, data_final = st.date_input(
                "Intervalo de Datas", value=(data_min, data_max),
                min_value=data_min, max_value=data_max
            )
            df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
        else:
            st.info("Não há dados de data disponíveis para filtrar.")
            df_filtrado = df.copy()

    st.header("Resumo")
    with st.expander("📊 Por Ativo", expanded=True):
        if not df_filtrado.empty and 'ATIVO' in df_filtrado.columns and 'RESULTADO_LIQUIDO' in df_filtrado.columns:
            resumo_ativo = df_filtrado.groupby('ATIVO').agg({
                'RESULTADO_LIQUIDO': ['count', 'sum', 'mean']
            }).round(2) # Arredondar para 2 casas decimais para valores monetários
            resumo_ativo.columns = ['Trades', 'Total', 'Média']
            resumo_ativo = resumo_ativo.reset_index()
            
            # Formatar colunas monetárias
            resumo_ativo['Total'] = resumo_ativo['Total'].apply(formatar_moeda)
            resumo_ativo['Média'] = resumo_ativo['Média'].apply(formatar_moeda)
            
            st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)
        else:
            st.info("Dados insuficientes para gerar o resumo por ativo.")

# --- Corpo Principal ---
if df.empty:
    st.info("ℹ️ Adicione operações para começar a visualizar os dados.")
else:
    # Dados filtrados
    valor_total = df_filtrado['RESULTADO_LIQUIDO'].sum()
    media_resultado = df_filtrado['RESULTADO_LIQUIDO'].mean()
    
    df_por_dia = df_filtrado.groupby(df_filtrado['ABERTURA'].dt.date).agg({
        'RESULTADO_LIQUIDO': 'sum'
    }).reset_index()
    df_por_dia.columns = ['Data', 'Resultado_Liquido_Dia']
    
    total_trades = len(df_filtrado)
    trades_ganhadores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] > 0])
    trades_perdedores = len(df_filtrado[df_filtrado['RESULTADO_LIQUIDO'] < 0])
    taxa_acerto = (trades_ganhadores / total_trades * 100) if total_trades > 0 else 0
    
    # Criar abas
    tab1, tab2, tab3 = st.tabs(["Visão Geral", "Análise de Risco", "Performance"])
    
    with tab1:
        # --- Métricas Principais ---
        st.subheader("Métricas Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Total", formatar_moeda(valor_total))
        
        with col2:
            st.metric("📈 Média/Trade", formatar_moeda(media_resultado))
        
        with col3:
            st.metric("🎯 Total Trades", f"{total_trades}")
        
        with col4:
            st.metric("✅ Taxa de Acerto", f"{taxa_acerto:.0f}%")
        
        # --- Atividade Anual ---
        st.subheader("Atividade Anual")
        if not df.empty and 'ABERTURA' in df.columns and not df['ABERTURA'].isnull().all():
            df_heatmap = df.copy()
            df_heatmap['Data'] = df_heatmap['ABERTURA'].dt.date
            df_heatmap_grouped = df_heatmap.groupby('Data')['RESULTADO_LIQUIDO'].sum().reset_index()
            
            ano_atual = datetime.now().year
            data_inicio = pd.Timestamp(f'{ano_atual}-01-01').date()
            data_fim = pd.Timestamp(f'{ano_atual}-12-31').date()
            
            date_range = pd.date_range(start=data_inicio, end=data_fim, freq='D')
            df_complete = pd.DataFrame({'Data': date_range.date})
            df_heatmap_final = df_complete.merge(df_heatmap_grouped, on='Data', how='left')
            df_heatmap_final['RESULTADO_LIQUIDO'] = df_heatmap_final['RESULTADO_LIQUIDO'].fillna(0)
            
            heatmap = create_heatmap_trading_style(df_heatmap_final)
            if heatmap:
                st.altair_chart(heatmap, use_container_width=True)
            else:
                st.info("Dados insuficientes para gerar o Heatmap Anual.")
        else:
            st.info("Dados de abertura insuficientes para gerar o Heatmap Anual.")
        
        # --- Evolução Acumulada ---
        st.subheader("Evolução Acumulada")
        if not df_por_dia.empty:
            df_area = df_por_dia.copy().sort_values('Data')
            df_area['Acumulado'] = df_area['Resultado_Liquido_Dia'].cumsum()
            evolution_chart = create_evolution_chart(df_area)
            st.altair_chart(evolution_chart, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o Gráfico de Evolução Acumulada.")
    
    with tab2:
        # --- Métricas de Risco ---
        st.subheader("Métricas de Risco")
        col5, col6, col7 = st.columns(3)
        
        with col5:
            if not df_por_dia.empty and 'Acumulado' in df_area.columns:
                max_drawdown = (df_area['Acumulado'].cummax() - df_area['Acumulado']).max()
                st.metric("📉 Máximo Drawdown", formatar_moeda(max_drawdown))
            else:
                st.info("N/A")
        
        with col6:
            if len(df_filtrado) > 1 and df_filtrado['RESULTADO_LIQUIDO'].std() > 0:
                sharpe_ratio = (media_resultado / df_filtrado['RESULTADO_LIQUIDO'].std()) * np.sqrt(252)
                st.metric("⚖️ Índice Sharpe", f"{sharpe_ratio:.2f}")
            else:
                st.info("N/A")
        
        with col7:
            if trades_perdedores > 0:
                win_loss_ratio = trades_ganhadores / trades_perdedores
                st.metric("📊 Ratio Win/Loss", f"{win_loss_ratio:.2f}:1")
            elif trades_ganhadores > 0:
                st.metric("📊 Ratio Win/Loss", f"{trades_ganhadores}:0")
            else:
                st.info("N/A")
        
        # --- Histograma e Radial lado a lado ---
        col_hist, col_radial = st.columns([2, 1])
        
        with col_hist:
            st.subheader("Distribuição de Resultados")
            if not df_filtrado.empty and 'RESULTADO_LIQUIDO' in df_filtrado.columns:
                hist_chart = create_histogram_chart(df_filtrado)
                st.altair_chart(hist_chart, use_container_width=True)
            else:
                st.info("Dados insuficientes para gerar o Histograma.")
        
        with col_radial:
            st.subheader("Distribuição de Trades")
            radial_chart = create_radial_chart(trades_ganhadores, trades_perdedores)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
            else:
                st.info("Sem dados suficientes para gerar o Gráfico Radial.")
    
    with tab3:
        # --- Performance por Horário ---
        st.subheader("Performance por Horário")
        if 'ABERTURA' in df_filtrado.columns and not df_filtrado['ABERTURA'].isnull().all():
            hourly_chart = create_hourly_chart(df_filtrado)
            st.altair_chart(hourly_chart, use_container_width=True)
        else:
            st.info("Dados de abertura insuficientes para gerar o Gráfico de Performance por Horário.")
        
        # --- Top Operações ---
        col_top1, col_top2 = st.columns(2)
        
        with col_top1:
            st.subheader("Melhores Operações")
            if not df_filtrado.empty and 'RESULTADO_LIQUIDO' in df_filtrado.columns:
                top_ganhos = df_filtrado.nlargest(5, 'RESULTADO_LIQUIDO')[['ATIVO', 'ABERTURA', 'QUANTIDADE', 'RESULTADO_LIQUIDO']]
                st.dataframe(format_top_trades(top_ganhos), hide_index=True)
            else:
                st.info("Nenhum dado para melhores operações.")
        
        with col_top2:
            st.subheader("Piores Operações")
            if not df_filtrado.empty and 'RESULTADO_LIQUIDO' in df_filtrado.columns:
                top_perdas = df_filtrado.nsmallest(5, 'RESULTADO_LIQUIDO')[['ATIVO', 'ABERTURA', 'QUANTIDADE', 'RESULTADO_LIQUIDO']]
                st.dataframe(format_top_trades(top_perdas), hide_index=True)
            else:
                st.info("Nenhum dado para piores operações.")
        
        # --- Resultado vs Volume ---
        st.subheader("Resultado vs Volume de Contratos")
        if 'QUANTIDADE' in df_filtrado.columns and 'RESULTADO_LIQUIDO' in df_filtrado.columns:
            scatter_data = df_filtrado[['QUANTIDADE', 'RESULTADO_LIQUIDO']]
            scatter_chart = alt.Chart(scatter_data).mark_circle(
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X('QUANTIDADE:Q', title='Quantidade de Contratos'),
                y=alt.Y('RESULTADO_LIQUIDO:Q', title='Resultado Líquido (R$)', axis=alt.Axis(format='.2f', formatType='currency')),
                color=alt.condition(
                    alt.datum.RESULTADO_LIQUIDO >= 0,
                    alt.value(COLOR_POSITIVE),
                    alt.value(COLOR_NEGATIVE)
                ),
                tooltip=[
                    alt.Tooltip('QUANTIDADE:Q', title='Quantidade'),
                    alt.Tooltip('RESULTADO_LIQUIDO:Q', title='Resultado (R$)', format='.2f', formatType='currency')
                ]
            ).properties(height=300)
            st.altair_chart(scatter_chart.configure(background='transparent'), use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o Gráfico de Resultado vs Volume.")

# Rodapé
st.caption("📊 Trading Analytics • 2025 • Desenvolvido com Streamlit")
