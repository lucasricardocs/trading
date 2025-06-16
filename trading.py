import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import numpy as np

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

def create_trading_heatmap(df):
    """Cria um gráfico de heatmap estilo GitHub para a atividade de trading."""
    if df.empty or 'Data' not in df.columns or 'Total' not in df.columns:
        st.warning("Dados insuficientes para gerar o heatmap.")
        return None

    # Determinar o ano atual ou mais recente dos dados
    current_year = df['Data'].dt.year.max()
    df_year = df[df['Data'].dt.year == current_year].copy()

    if df_year.empty:
        st.warning(f"Sem dados para o ano {current_year}.")
        return None

    # Obter o dia da semana do primeiro dia do ano (0=segunda, 6=domingo)
    first_day_of_year = pd.Timestamp(f'{current_year}-01-01')
    first_day_weekday = first_day_of_year.weekday()
    
    # Calcular quantos dias antes do 01/01 precisamos adicionar para começar na segunda
    days_before = first_day_weekday
    
    # Criar range de datas começando na segunda-feira da semana do 01/01
    start_date = first_day_of_year - pd.Timedelta(days=days_before)
    end_date = datetime(current_year, 12, 31)
    
    # Garantir que terminamos no domingo da última semana
    days_after = 6 - end_date.weekday()
    if days_after < 6:
        end_date = end_date + pd.Timedelta(days=days_after)
    
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # DataFrame com todas as datas
    full_df = pd.DataFrame({'Data': all_dates})
    
    # Marcar quais datas são do ano atual
    full_df['is_current_year'] = full_df['Data'].dt.year == current_year
    
    # Fazer merge com os dados reais
    full_df = full_df.merge(df_year[['Data', 'Total']], on='Data', how='left')
    
    # Preencher NaNs
    full_df['Total'] = full_df['Total'].fillna(0)
    
    # Para dias que não são do ano atual, definir como None para visualização
    full_df['display_total'] = full_df['Total'].copy()
    mask_not_current_year = ~full_df['is_current_year']
    full_df.loc[mask_not_current_year, 'display_total'] = None

    # Mapear os nomes dos dias
    full_df['day_of_week'] = full_df['Data'].dt.weekday
    day_name_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    full_df['day_display_name'] = full_df['day_of_week'].map(day_name_map)
    
    # Ordem fixa dos dias
    day_display_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    
    full_df['month'] = full_df['Data'].dt.month
    full_df['month_name'] = full_df['Data'].dt.strftime('%b')

    # Calcular semana baseado na primeira data
    full_df['week_corrected'] = ((full_df['Data'] - start_date).dt.days // 7)
    
    # Encontrar a primeira semana de cada mês para os rótulos
    month_labels = full_df[full_df['is_current_year']].groupby('month').agg(
        week_corrected=('week_corrected', 'min'),
        month_name=('month_name', 'first')
    ).reset_index()

    # Determinar escala de cores baseada nos valores
    max_value = full_df['Total'].max()
    if max_value > 0:
        thresholds = [0.01, max_value * 0.25, max_value * 0.5, max_value * 0.75]
    else:
        thresholds = [0.01, 100, 250, 500]

    # Labels dos meses
    months_chart = alt.Chart(month_labels).mark_text(
        align='center',
        baseline='bottom',
        fontSize=12,
        dy=-5,
        color='#666666'
    ).encode(
        x=alt.X('week_corrected:O', axis=None),
        text='month_name:N'
    )

    # Tooltip
    tooltip_fields = [
        alt.Tooltip('Data:T', title='Data', format='%d/%m/%Y'),
        alt.Tooltip('day_display_name:N', title='Dia'),
        alt.Tooltip('Total:Q', title='Resultado (R$)', format=',.2f')
    ]

    # Gráfico principal (heatmap)
    heatmap = alt.Chart(full_df).mark_rect(
        stroke='#ffffff',
        strokeWidth=2,
        cornerRadius=2
    ).encode(
        x=alt.X('week_corrected:O',
                title=None, 
                axis=None),
        y=alt.Y('day_display_name:N', 
                sort=day_display_names,
                title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=12, ticks=False, 
                            domain=False, grid=False, labelColor='#666666')),
        color=alt.condition(
            alt.datum.display_total == None,
            alt.value('#f0f0f0'),
            alt.Color('display_total:Q',
                scale=alt.Scale(
                    range=['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
                    type='threshold',
                    domain=thresholds
                ),
                legend=alt.Legend(
                    title="Resultado Diário (R$)",
                    titleFontSize=12,
                    labelFontSize=10,
                    orient='bottom',
                    direction='horizontal'
                ))
        ),
        tooltip=tooltip_fields
    ).properties(
        height=180,
        width=800
    )

    # Combinar gráfico final
    final_chart = alt.vconcat(
        months_chart,
        heatmap,
        spacing=5
    ).properties(
        title=alt.TitleParams(
            text=f'Atividade de Trading - {current_year}',
            fontSize=20,
            anchor='start',
            color='#333333',
            dy=-10
        )
    ).resolve_scale(
        color='independent'
    )

    return final_chart

def main():
    st.set_page_config(
        page_title="Trading Activity Heatmap",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 Trading Activity Heatmap")
    st.markdown("Faça upload do seu arquivo CSV de trading para visualizar sua atividade em um heatmap estilo GitHub.")
    
    # Upload do arquivo
    uploaded_file = st.file_uploader(
        "Escolha seu arquivo CSV",
        type=['csv'],
        help="Faça upload do arquivo CSV com os dados de trading."
    )
    
    if uploaded_file is not None:
        try:
            # Tentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            df = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    # Pular as primeiras 4 linhas e usar a linha 5 como cabeçalho
                    df = pd.read_csv(uploaded_file, encoding=encoding, sep=';', 
                                   skiprows=4, on_bad_lines='skip')
                    st.success(f"Arquivo carregado com encoding: {encoding}")
                    break
                        
                except (UnicodeDecodeError, pd.errors.ParserError) as e:
                    continue
            
            if df is None:
                st.error("Não foi possível ler o arquivo com nenhum encoding testado.")
                return
            
            # Mostrar preview dos dados
            with st.expander("👀 Preview dos dados", expanded=False):
                st.dataframe(df.head())
                st.write(f"**Total de registros:** {len(df)}")
                st.write(f"**Colunas:** {list(df.columns)}")
            
            # Processar os dados
            processed_df = process_trading_data(df)
            
            if not processed_df.empty:
                # Mostrar estatísticas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_result = processed_df['Total'].sum()
                    st.metric("Resultado Total", f"R$ {total_result:,.2f}")
                
                with col2:
                    trading_days = len(processed_df[processed_df['Total'] != 0])
                    st.metric("Dias de Trading", trading_days)
                
                with col3:
                    avg_daily = processed_df[processed_df['Total'] != 0]['Total'].mean()
                    if not pd.isna(avg_daily):
                        st.metric("Média Diária", f"R$ {avg_daily:,.2f}")
                    else:
                        st.metric("Média Diária", "R$ 0,00")
                
                with col4:
                    profitable_days = len(processed_df[processed_df['Total'] > 0])
                    st.metric("Dias Lucrativos", profitable_days)
                
                # Criar e exibir o heatmap
                st.subheader("Heatmap de Atividade")
                chart = create_trading_heatmap(processed_df)
                
                if chart is not None:
                    st.altair_chart(chart, use_container_width=True)
                    
                    # Mostrar legenda explicativa
                    st.info("""
                    **Como interpretar o heatmap:**
                    - Cada quadrado representa um dia
                    - Cores mais escuras = resultados maiores (positivos ou negativos)
                    - Cores mais claras = resultados menores
                    - Cinza claro = sem atividade de trading
                    - Passe o mouse sobre os quadrados para ver detalhes
                    """)
                    
                    # Mostrar dados processados
                    with st.expander("📊 Dados processados por dia", expanded=False):
                        display_df = processed_df.copy()
                        display_df['Data'] = display_df['Data'].dt.strftime('%d/%m/%Y')
                        display_df['Total'] = display_df['Total'].apply(lambda x: f"R$ {x:,.2f}")
                        st.dataframe(display_df, use_container_width=True)
                
            else:
                st.error("Não foi possível processar os dados. Verifique se o arquivo está no formato correto.")
                
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            st.info("Certifique-se de que o arquivo CSV está no formato correto com as colunas 'Data' e 'Total'.")
    
    else:
        st.info("👆 Faça upload do seu arquivo CSV para começar")
        
        # Mostrar exemplo do formato esperado
        st.subheader("Formato esperado do arquivo")
        example_data = {
            'Data': ['16/06/2025', '16/06/2025', '16/06/2025'],
            'Ativo': ['WDON25', 'WDON25', 'WDON25'],
            'Lado': ['V', 'C', 'V'],
            'Total': ['80,00', '-55,00', '-405,00']
        }
        st.dataframe(pd.DataFrame(example_data))
        st.caption("O arquivo deve conter pelo menos as colunas 'Data' e 'Total'. Outras colunas são opcionais.")

if __name__ == "__main__":
    main()
