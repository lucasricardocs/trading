import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
import math

# Configuração da página
st.set_page_config(
    page_title="Análise de Operações Financeiras",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Título principal
st.title("📊 Análise de Operações Financeiras")
st.markdown("---")

# Upload do arquivo
uploaded_file = st.file_uploader(
    "Faça o upload do seu arquivo CSV",
    type=['csv'],
    help="Selecione um arquivo CSV com dados de operações financeiras"
)

if uploaded_file is not None:
    try:
        # Lê o arquivo CSV
        df_raw = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
        
        # Processa os dados a partir da linha 5 (índice 4)
        if len(df_raw) > 5:
            # Pega o cabeçalho da linha 5 (índice 4)
            headers = df_raw.iloc[4].values
            
            # Pega os dados da linha 6 em diante (índice 5+)
            df_data = df_raw.iloc[5:].copy()
            df_data.columns = headers
            
            # Remove linhas vazias
            df_data = df_data.dropna(how='all')
            
            # Processa as colunas necessárias
            required_columns = ['ATIVO', 'ABERTURA', 'QUANTIDADE', 'RESULTADO DA OPERAÇÃO']
            
            # Verifica se as colunas existem
            available_columns = [col for col in required_columns if col in df_data.columns]
            
            if len(available_columns) >= 3:  # Pelo menos 3 das 4 colunas necessárias
                # Limpa e processa os dados
                df_clean = df_data[available_columns].copy()
                
                # Processa a coluna de data (ABERTURA)
                if 'ABERTURA' in df_clean.columns:
                    # Extrai apenas a data da coluna ABERTURA
                    df_clean['DATA'] = pd.to_datetime(df_clean['ABERTURA'].str.split(' ').str[0], errors='coerce')
                
                # Processa a coluna de resultado
                if 'RESULTADO DA OPERAÇÃO' in df_clean.columns:
                    # Remove caracteres não numéricos e converte para float
                    df_clean['RESULTADO'] = df_clean['RESULTADO DA OPERAÇÃO'].astype(str).str.replace(r'[^\d.,-]', '', regex=True)
                    df_clean['RESULTADO'] = df_clean['RESULTADO'].str.replace(',', '.').astype(float, errors='ignore')
                
                # Processa quantidade
                if 'QUANTIDADE' in df_clean.columns:
                    df_clean['QTD'] = pd.to_numeric(df_clean['QUANTIDADE'], errors='coerce')
                
                # Remove linhas com dados inválidos
                df_clean = df_clean.dropna(subset=['DATA', 'RESULTADO'])
                
                if len(df_clean) > 0:
                    # Calcula estatísticas
                    valor_total = df_clean['RESULTADO'].sum()
                    media = df_clean['RESULTADO'].mean()
                    
                    # Agrupa por data para encontrar melhor e pior dia
                    df_por_dia = df_clean.groupby('DATA')['RESULTADO'].sum().reset_index()
                    melhor_dia = df_por_dia.loc[df_por_dia['RESULTADO'].idxmax()]
                    pior_dia = df_por_dia.loc[df_por_dia['RESULTADO'].idxmin()]
                    
                    # Estatísticas adicionais
                    total_operacoes = len(df_clean)
                    operacoes_positivas = len(df_clean[df_clean['RESULTADO'] > 0])
                    operacoes_negativas = len(df_clean[df_clean['RESULTADO'] < 0])
                    taxa_acerto = (operacoes_positivas / total_operacoes) * 100 if total_operacoes > 0 else 0
                    
                    # Exibe as métricas em caixas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            label="💰 Valor Total",
                            value=f"R$ {valor_total:,.2f}",
                            delta=f"{valor_total:+.2f}" if valor_total != 0 else None
                        )
                    
                    with col2:
                        st.metric(
                            label="📊 Média por Operação",
                            value=f"R$ {media:,.2f}",
                            delta=f"{media:+.2f}" if media != 0 else None
                        )
                    
                    with col3:
                        st.metric(
                            label="🎯 Taxa de Acerto",
                            value=f"{taxa_acerto:.1f}%",
                            delta=f"{operacoes_positivas}/{total_operacoes} ops"
                        )
                    
                    with col4:
                        st.metric(
                            label="📈 Total de Operações",
                            value=f"{total_operacoes}",
                            delta=f"Pos: {operacoes_positivas} | Neg: {operacoes_negativas}"
                        )
                    
                    # Segunda linha de métricas
                    col5, col6 = st.columns(2)
                    
                    with col5:
                        st.metric(
                            label="🟢 Melhor Dia",
                            value=f"R$ {melhor_dia['RESULTADO']:,.2f}",
                            delta=melhor_dia['DATA'].strftime('%d/%m/%Y')
                        )
                    
                    with col6:
                        st.metric(
                            label="🔴 Pior Dia",
                            value=f"R$ {pior_dia['RESULTADO']:,.2f}",
                            delta=pior_dia['DATA'].strftime('%d/%m/%Y')
                        )
                    
                    st.markdown("---")
                    
                    # Armazena os dados processados no session_state para uso nos gráficos
                    st.session_state['df_clean'] = df_clean
                    st.session_state['df_por_dia'] = df_por_dia
                    
                    st.success(f"✅ Dados processados com sucesso! {len(df_clean)} operações encontradas.")
                    
                else:
                    st.error("❌ Não foi possível processar os dados. Verifique o formato do arquivo.")
            else:
                st.error(f"❌ Colunas necessárias não encontradas. Disponíveis: {list(df_data.columns)}")
        else:
            st.error("❌ O arquivo deve ter pelo menos 6 linhas (dados a partir da linha 6).")
            
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
else:
    st.info("👆 Faça o upload de um arquivo CSV para começar a análise.")
    
    # Exemplo de formato esperado
    st.markdown("### 📋 Formato Esperado do Arquivo")
    st.markdown("""
    O arquivo CSV deve ter:
    - **Linha 5**: Cabeçalhos das colunas
    - **Linha 6 em diante**: Dados das operações
    - **Colunas necessárias**: ATIVO, ABERTURA, QUANTIDADE, RESULTADO DA OPERAÇÃO
    - **Separador**: ponto e vírgula (;)
    """)



# Seção de gráficos - só exibe se houver dados processados
if 'df_clean' in st.session_state and 'df_por_dia' in st.session_state:
    df_clean = st.session_state['df_clean']
    df_por_dia = st.session_state['df_por_dia']
    
    st.markdown("## 📈 Visualizações")
    
    # 1. HEATMAP (estilo GitHub)
    st.markdown("### 🔥 Heatmap de Resultados Diários")
    
    # Prepara dados para o heatmap
    df_heatmap = df_por_dia.copy()
    df_heatmap['year'] = df_heatmap['DATA'].dt.year
    df_heatmap['month'] = df_heatmap['DATA'].dt.month
    df_heatmap['day'] = df_heatmap['DATA'].dt.day
    df_heatmap['weekday'] = df_heatmap['DATA'].dt.dayofweek
    df_heatmap['week'] = df_heatmap['DATA'].dt.isocalendar().week
    
    # Determina a escala de cores baseada nos valores
    max_val = df_heatmap['RESULTADO'].max()
    min_val = df_heatmap['RESULTADO'].min()
    
    # Cria o heatmap
    heatmap = alt.Chart(df_heatmap).mark_rect().add_selection(
        alt.selection_single()
    ).encode(
        x=alt.X('week:O', title='Semana do Ano'),
        y=alt.Y('weekday:O', title='Dia da Semana', 
                scale=alt.Scale(domain=[0,1,2,3,4,5,6]),
                axis=alt.Axis(labelExpr="['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'][datum.value]")),
        color=alt.Color('RESULTADO:Q',
                       scale=alt.Scale(
                           domain=[min_val, 0, max_val],
                           range=['#d73027', '#f7f7f7', '#1a9850']
                       ),
                       title='Resultado (R$)'),
        tooltip=['DATA:T', 'RESULTADO:Q']
    ).properties(
        width='container',
        height=200,
        title='Heatmap de Resultados por Dia (Verde: Ganho, Vermelho: Perda, Cinza: Neutro)'
    )
    
    st.altair_chart(heatmap, use_container_width=True)
    
    # 2. AREA CHART com gradiente
    st.markdown("### 📊 Evolução dos Resultados Acumulados")
    
    # Calcula resultado acumulado
    df_acumulado = df_por_dia.copy().sort_values('DATA')
    df_acumulado['RESULTADO_ACUMULADO'] = df_acumulado['RESULTADO'].cumsum()
    
    # Cria o gráfico de área com gradiente
    area_chart = alt.Chart(df_acumulado).mark_area(
        line={'color': 'darkgreen'},
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color='white', offset=0),
                alt.GradientStop(color='darkgreen', offset=1)
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('DATA:T', title='Data'),
        y=alt.Y('RESULTADO_ACUMULADO:Q', title='Resultado Acumulado (R$)'),
        tooltip=['DATA:T', 'RESULTADO_ACUMULADO:Q', 'RESULTADO:Q']
    ).properties(
        width='container',
        height=500,
        title='Evolução do Resultado Acumulado ao Longo do Tempo'
    ).configure_view(
        fill='#1e1e1e'
    ).configure_axis(
        labelColor='white',
        titleColor='white'
    ).configure_title(
        color='white'
    )
    
    st.altair_chart(area_chart, use_container_width=True)
    
    # 3. HISTOGRAMA + GRÁFICO RADIAL (lado a lado)
    st.markdown("### 📊 Distribuição de Resultados")
    
    col_hist, col_radial = st.columns([2, 1])  # 2/3 para histograma, 1/3 para radial
    
    with col_hist:
        st.markdown("#### Histograma de Resultados")
        
        # Prepara dados para histograma
        df_hist = df_clean.copy()
        df_hist['cor'] = df_hist['RESULTADO'].apply(lambda x: 'Positivo' if x > 0 else 'Negativo' if x < 0 else 'Neutro')
        
        # Cria histograma
        histogram = alt.Chart(df_hist).mark_bar().encode(
            x=alt.X('RESULTADO:Q', bin=alt.Bin(maxbins=30), title='Resultado (R$)'),
            y=alt.Y('count()', title='Frequência'),
            color=alt.Color('cor:N', 
                           scale=alt.Scale(
                               domain=['Negativo', 'Neutro', 'Positivo'],
                               range=['#d73027', '#f7f7f7', '#1a9850']
                           ),
                           title='Tipo'),
            tooltip=['count()', 'RESULTADO:Q']
        ).properties(
            width='container',
            height=500,
            title='Distribuição dos Resultados das Operações'
        )
        
        st.altair_chart(histogram, use_container_width=True)
    
    with col_radial:
        st.markdown("#### Proporção de Trades")
        
        # Dados para gráfico radial
        operacoes_positivas = len(df_clean[df_clean['RESULTADO'] > 0])
        operacoes_negativas = len(df_clean[df_clean['RESULTADO'] < 0])
        total_ops = operacoes_positivas + operacoes_negativas
        
        # Dados para o gráfico de pizza
        pie_data = pd.DataFrame({
            'categoria': ['Ganhadoras', 'Perdedoras'],
            'quantidade': [operacoes_positivas, operacoes_negativas],
            'percentual': [operacoes_positivas/total_ops*100, operacoes_negativas/total_ops*100]
        })
        
        # Gráfico de pizza (simulando radial)
        pie_chart = alt.Chart(pie_data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta('quantidade:Q'),
            color=alt.Color('categoria:N',
                           scale=alt.Scale(
                               domain=['Ganhadoras', 'Perdedoras'],
                               range=['#1a9850', '#d73027']
                           ),
                           title='Tipo de Trade'),
            tooltip=['categoria:N', 'quantidade:Q', 'percentual:Q']
        ).properties(
            width=300,
            height=300,
            title='Proporção de Trades Ganhadoras vs Perdedoras'
        )
        
        st.altair_chart(pie_chart, use_container_width=True)
        
        # Exibe estatísticas do gráfico radial
        st.metric("🎯 Taxa de Acerto", f"{operacoes_positivas/total_ops*100:.1f}%")
        st.metric("🟢 Trades Ganhadoras", f"{operacoes_positivas}")
        st.metric("🔴 Trades Perdedoras", f"{operacoes_negativas}")
    
    # 4. GRÁFICO ADICIONAL: Resultado por Ativo
    st.markdown("### 🏢 Resultado por Ativo")
    
    if 'ATIVO' in df_clean.columns:
        df_por_ativo = df_clean.groupby('ATIVO')['RESULTADO'].agg(['sum', 'count', 'mean']).reset_index()
        df_por_ativo.columns = ['ATIVO', 'RESULTADO_TOTAL', 'NUM_OPERACOES', 'RESULTADO_MEDIO']
        df_por_ativo = df_por_ativo.sort_values('RESULTADO_TOTAL', ascending=False)
        
        # Gráfico de barras por ativo
        bar_chart = alt.Chart(df_por_ativo.head(20)).mark_bar().encode(
            x=alt.X('RESULTADO_TOTAL:Q', title='Resultado Total (R$)'),
            y=alt.Y('ATIVO:N', sort='-x', title='Ativo'),
            color=alt.Color('RESULTADO_TOTAL:Q',
                           scale=alt.Scale(
                               domain=[df_por_ativo['RESULTADO_TOTAL'].min(), 0, df_por_ativo['RESULTADO_TOTAL'].max()],
                               range=['#d73027', '#f7f7f7', '#1a9850']
                           ),
                           title='Resultado (R$)'),
            tooltip=['ATIVO:N', 'RESULTADO_TOTAL:Q', 'NUM_OPERACOES:Q', 'RESULTADO_MEDIO:Q']
        ).properties(
            width='container',
            height=500,
            title='Top 20 Ativos por Resultado Total'
        )
        
        st.altair_chart(bar_chart, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📋 Resumo dos Dados Processados")
    
    # Exibe uma amostra dos dados processados
    with st.expander("Ver amostra dos dados processados"):
        st.dataframe(df_clean.head(10), use_container_width=True)
        
    with st.expander("Ver dados agrupados por dia"):
        st.dataframe(df_por_dia.head(10), use_container_width=True)
