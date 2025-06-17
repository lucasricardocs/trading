# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
import time
import random
from datetime import datetime, timedelta, date
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
def load_data():
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            if 'ABERTURA' in df.columns:
                df['ABERTURA'] = pd.to_datetime(df['ABERTURA'], errors='coerce')
            
            if 'RESULTADO' in df.columns:
                df['RESULTADO'] = df['RESULTADO'].astype(str).str.replace(',', '.', regex=False)
                df['RESULTADO'] = pd.to_numeric(df['RESULTADO'], errors='coerce').fillna(0)
            
            if 'QUANTIDADE' in df.columns:
                df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0)

            if 'ATIVO' in df.columns and 'QUANTIDADE' in df.columns and 'RESULTADO' in df.columns:
                custos = {'WDOFUT': 1.09, 'WINFUT': 0.39}
                df['CUSTO'] = df.apply(lambda row: 
                    custos.get(row['ATIVO'], 0) * row['QUANTIDADE'] * 2, axis=1)
                df['RESULTADO_LIQUIDO'] = df['RESULTADO'] - df['CUSTO']
            else:
                df['CUSTO'] = 0
                df['RESULTADO_LIQUIDO'] = df.get('RESULTADO', 0)

            return df
        except Exception as e:
            st.error(f"Erro: {e}")
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
            st.error(f"Erro: {e}")
            return False
    return False

def calcular_largura_e_espacamento(num_elementos):
    if num_elementos <= 5:
        return {'size': 60, 'padding': 0.3}
    elif num_elementos <= 15:
        return {'size': 45, 'padding': 0.2}
    elif num_elementos <= 30:
        return {'size': 30, 'padding': 0.1}
    elif num_elementos <= 50:
        return {'size': 20, 'padding': 0.05}
    else:
        return {'size': 15, 'padding': 0.02}

def formatar_moeda(valor):
    """Formata valor monetário com símbolo R$ e separadores brasileiros"""
    try:
        # Formatação manual: R$ 1.234,56
        valor_str = f"{valor:,.2f}"
        
        # Separa parte inteira e decimal
        if '.' in valor_str:
            parte_inteira, parte_decimal = valor_str.split('.')
        else:
            parte_inteira = valor_str
            parte_decimal = "00"
        
        # Formata parte inteira com pontos
        parte_inteira_formatada = ""
        for i, char in enumerate(reversed(parte_inteira)):
            if i > 0 and i % 3 == 0:
                parte_inteira_formatada = '.' + parte_inteira_formatada
            parte_inteira_formatada = char + parte_inteira_formatada
        
        # Retorna string formatada
        return f"R$ {parte_inteira_formatada},{parte_decimal}"
    except:
        # Fallback para valores simples
        return f"R$ {valor:.2f}"

def create_heatmap_2d_github(df_heatmap_final):
    """Heatmap minimalista com dias fora do ano transparentes"""
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
    day_name_map = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    day_display_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    full_df['month'] = full_df['Data_dt'].dt.month
    full_df['month_name'] = full_df['Data_dt'].dt.strftime('%b')
    full_df['week_corrected'] = ((full_df['Data_dt'] - start_date).dt.days // 7)
    
    def get_stroke_width(row):
        if pd.isna(row['display_resultado']) or row['display_resultado'] is None:
            return 0
        else:
            return 2
    
    def get_color_category(row):
        if pd.isna(row['display_resultado']) or row['display_resultado'] is None:
            return 'fora_ano'
        elif row['display_resultado'] == 0:
            return 'vazio'
        elif row['display_resultado'] > 0:
            return 'positivo'
        else:
            return 'negativo'
    
    full_df['color_category'] = full_df.apply(get_color_category, axis=1)
    full_df['stroke_width'] = full_df.apply(get_stroke_width, axis=1)
    
    month_labels = full_df[full_df['is_current_year']].groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    months_chart = alt.Chart(month_labels).mark_text(
        align='center', baseline='bottom', fontSize=10, dy=-3, dx=-20,
        color='#999', fontWeight='normal'
    ).encode(
        x=alt.X('week_corrected:O', axis=None),
        text='month_name:N'
    )

    heatmap = alt.Chart(full_df).mark_rect(
        stroke='white',
        cornerRadius=2
    ).encode(
        x=alt.X('week_corrected:O', title=None, axis=None),
        y=alt.Y('day_display_name:N', sort=day_display_names, title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=9, ticks=False, 
                             domain=False, grid=False, labelColor='#999', labelPadding=8)),
        strokeWidth=alt.StrokeWidth('stroke_width:Q', legend=None),
        color=alt.Color('color_category:N',
                       scale=alt.Scale(
                           domain=['fora_ano', 'vazio', 'positivo', 'negativo'],
                           range=['transparent', '#cccccc', '#28a745', '#dc3545']
                       ),
                       legend=None),
        tooltip=[
            alt.Tooltip('Data:T', title='Data', format='%d/%m'),
            alt.Tooltip('RESULTADO_LIQUIDO:Q', title='R$', format=',.0f')
        ]
    ).properties(height=200)

    return alt.vconcat(months_chart, heatmap, spacing=5).configure_view(
        strokeWidth=0).configure(background='transparent')

def create_evolution_chart_with_gradient(df_area):
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
            alt.value('#28a745'),
            alt.value('#dc3545')
        ),
        tooltip=[
            'Data:T', 
            alt.Tooltip('Acumulado:Q', format=',.0f', title='Acumulado'), 
            alt.Tooltip('Resultado_Liquido_Dia:Q', format=',.0f', title='Dia')
        ]
    ).properties(width='container', height=300, background='transparent')
    
    return area_chart

def create_radial_chart(trades_ganhadores, trades_perdedores):
    """Cria gráfico radial no estilo especificado"""
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
                                     range=["#28a745", "#dc3545"]),
                       legend=None)
    )
    
    c1 = base.mark_arc(innerRadius=20, stroke="#fff", strokeWidth=2)
    
    c2 = base.mark_text(radiusOffset=15, color='white', fontSize=12, fontWeight='bold').encode(
        text="values:Q"
    )
    
    chart = (c1 + c2).properties(
        width=250,
        height=250,
        background='transparent'
    )
    
    return chart

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
            resultado_input = st.text_input("Resultado", value="0,00")
            
            try:
                resultado_valor = float(resultado_input.replace(',', '.'))
            except ValueError:
                st.error("Valor inválido. Use números com vírgula decimal.")
                resultado_valor = 0.0

            submitted = st.form_submit_button("✅ Adicionar")
            
            if submitted:
                if add_trade_to_sheet(ativo, data_abertura, quantidade, tipo_operacao, resultado_valor):
                    st.success("✅ Trade adicionado!")
                    st.cache_data.clear()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("❌ Erro ao adicionar")

    st.header("Filtros")
    
    df = load_data()
    
    if not df.empty and 'ABERTURA' in df.columns:
        data_min = df['ABERTURA'].min().date()
        data_max = df['ABERTURA'].max().date()
        data_inicial, data_final = st.date_input(
            "Intervalo de Datas", value=(data_min, data_max),
            min_value=data_min, max_value=data_max
        )
        df_filtrado = df[(df['ABERTURA'].dt.date >= data_inicial) & (df['ABERTURA'].dt.date <= data_final)]
    else:
        df_filtrado = df.copy()

    st.header("Resumo por Ativo")
    if not df_filtrado.empty:
        resumo_ativo = df_filtrado.groupby('ATIVO').agg({
            'RESULTADO_LIQUIDO': ['count', 'sum', 'mean']
        }).round(0)
        resumo_ativo.columns = ['Trades', 'Total', 'Média']
        resumo_ativo = resumo_ativo.reset_index()
        st.dataframe(resumo_ativo, use_container_width=True, hide_index=True)

# --- Corpo Principal ---
if df.empty:
    st.info("ℹ️ Adicione operações para começar")
else:
    with st.expander("📋 Ver Todas as Operações", expanded=False):
        st.dataframe(df, use_container_width=True)

    if 'RESULTADO_LIQUIDO' in df_filtrado.columns and 'ABERTURA' in df_filtrado.columns:
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
        
        # --- Métricas ---
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Total", 
                value=formatar_moeda(valor_total),
                delta=None
            )
        
        with col2:
            st.metric(
                label="📈 Média por Trade", 
                value=formatar_moeda(media_resultado),
                delta=None
            )
        
        with col3:
            st.metric(
                label="🎯 Total de Trades", 
                value=f"{total_trades}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="✅ Taxa de Acerto", 
                value=f"{taxa_acerto:.0f}%",
                delta=None
            )

        # --- Gráficos ---
        st.subheader("🔥 Atividade Anual")
        df_heatmap = df.copy()
        if not df_heatmap.empty and 'ABERTURA' in df_heatmap.columns:
            df_heatmap['Data'] = df_heatmap['ABERTURA'].dt.date
            df_heatmap_grouped = df_heatmap.groupby('Data')['RESULTADO_LIQUIDO'].sum().reset_index()
            
            ano_atual = datetime.now().year
            data_inicio = pd.Timestamp(f'{ano_atual}-01-01').date()
            data_fim = pd.Timestamp(f'{ano_atual}-12-31').date()
            
            date_range = pd.date_range(start=data_inicio, end=data_fim, freq='D')
            df_complete = pd.DataFrame({'Data': date_range.date})
            df_heatmap_final = df_complete.merge(df_heatmap_grouped, on='Data', how='left')
            df_heatmap_final['RESULTADO_LIQUIDO'] = df_heatmap_final['RESULTADO_LIQUIDO'].fillna(0)
            
            heatmap_2d_github = create_heatmap_2d_github(df_heatmap_final)
            if heatmap_2d_github:
                st.altair_chart(heatmap_2d_github, use_container_width=True)
        
        st.subheader("📊 Evolução Acumulada")
        if not df_por_dia.empty:
            df_area = df_por_dia.copy().sort_values('Data')
            df_area['Acumulado'] = df_area['Resultado_Liquido_Dia'].cumsum()
            evolution_chart = create_evolution_chart_with_gradient(df_area)
            st.altair_chart(evolution_chart, use_container_width=True)

        # --- Resultados por Trade ---
        st.subheader("🎯 Resultados por Trade")
        col_trades, col_radial = st.columns([2, 1])
        
        with col_trades:
            if not df_filtrado.empty:
                df_trades = df_filtrado.copy()
                df_trades = df_trades.sort_values('ABERTURA')
                df_trades['Index'] = range(1, len(df_trades) + 1)
                num_trades = len(df_trades)
                config = calcular_largura_e_espacamento(num_trades)
                
                bars = alt.Chart(df_trades).mark_bar(
                    size=config['size'], 
                    cornerRadius=1,
                    stroke='white',
                    strokeWidth=2
                ).encode(
                    x=alt.X('Index:O', title='', axis=alt.Axis(grid=False, domain=False, ticks=False),
                           scale=alt.Scale(paddingInner=config['padding'], paddingOuter=0.1)),
                    y=alt.Y('RESULTADO_LIQUIDO:Q', title='', axis=alt.Axis(grid=True, gridOpacity=0.1)),
                    color=alt.condition(alt.datum.RESULTADO_LIQUIDO > 0, alt.value('#28a745'), alt.value('#dc3545')),
                    tooltip=[
                        alt.Tooltip('Index:O', title='#'),
                        alt.Tooltip('ABERTURA:T', title='Data', format='%d/%m'),
                        alt.Tooltip('ATIVO:N', title='Ativo'),
                        alt.Tooltip('RESULTADO_LIQUIDO:Q', format=',.0f', title='R$')
                    ]
                )
                
                linha_zero = alt.Chart(pd.DataFrame({'zero': [0]})).mark_rule(
                    color='#666', strokeWidth=2, opacity=0.5
                ).encode(y=alt.Y('zero:Q'))
                
                chart_final = (bars + linha_zero).properties(
                    width='container', height=300, background='transparent'
                )
                st.altair_chart(chart_final, use_container_width=True)
        
        with col_radial:
            st.subheader("Distribuição")
            radial_chart = create_radial_chart(trades_ganhadores, trades_perdedores)
            if radial_chart:
                st.altair_chart(radial_chart, use_container_width=True)
            else:
                st.info("Sem dados suficientes para exibir o gráfico radial")

# Rodapé
st.caption("📊 Trading Analytics • 2025 • Desenvolvido com Streamlit")
