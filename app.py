import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import importlib.util
import re
import hmac
import hashlib

# Configuração do Streamlit
st.set_page_config(page_title="Relatório BRZ", layout="wide")

# --- CSS Customizado ---
st.markdown(
    """
    <style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .main-header {
        font-size: 3em;
        font-weight: bold;
        color: #2C3E50;
        text-align: center;
        margin-bottom: 20px;
        padding: 10px;
        border-bottom: 3px solid #18BC9C;
    }
    @media (max-width: 768px) {
        .main-header {
            font-size: 2.5em;
        }
    }
    div[data-testid="metric-container"] {
        background-color: #F0F8FF;
        border-radius: 10px;
        padding: 10px;
        margin: 5px;
    }
    .css-1d391kg { 
        background-color: #f7f7f7;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1 class='main-header'>Relatório - BRZ Checagem</h1>", unsafe_allow_html=True)

# Acessar secrets do Streamlit
SECRET_KEY = st.secrets["secret_key"]
AGENCY_VALUE = st.secrets["agency_value"]
SPREADSHEET_NAME = st.secrets["spreadsheet_name"]
SHEET_NAME = st.secrets["sheet_name"]
SPREADSHEET_CAMPAIGNS = st.secrets["spreadsheet_campaigns"]
SHEET_CAMPAIGNS = st.secrets["sheet_campaigns"]

# Carregar o módulo spreadsheet.py
spec = importlib.util.spec_from_file_location("spreadsheet", "sheetsbot/spreadsheet.py")
spreadsheet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spreadsheet)

# Funções de hash
def generate_hash(value, secret=SECRET_KEY):
    full_hash = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return full_hash[:12]

def validate_hash(hash_value, possible_values, secret=SECRET_KEY):
    for value in possible_values:
        expected_hash = generate_hash(value, secret)
        if expected_hash == hash_value:
            return value
    return None

# Capturar parâmetros da URL
query_params = st.query_params.to_dict()
site_hash = query_params.get("site", "")
veiculo_hash = query_params.get("veiculo", "")

# Carregar dados
spreadsheet_data = spreadsheet.get_page(1, SPREADSHEET_NAME, SHEET_NAME)
df = pd.DataFrame(spreadsheet_data)
campaigns_data = spreadsheet.get_page(1, SPREADSHEET_CAMPAIGNS, SHEET_CAMPAIGNS)
df_campaigns = pd.DataFrame(campaigns_data)

# Pré-processamento dos dados
df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
numeric_cols = ['Impressions', 'Clicks', 'Conversions']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df[df['Impressions'] > 0]

# Extrair valores possíveis
possible_sites = [site.strip() for site in df['Site'].unique().tolist()]
possible_veiculos = []
for zone in df['Zone'].unique():
    match = re.search(r'\[(.*?)\]', str(zone))
    if match:
        veiculo = match.group(1).strip()
        possible_veiculos.append(veiculo)

# Validar os hashes
selected_site = validate_hash(site_hash, possible_sites)
selected_veiculo = validate_hash(veiculo_hash, possible_veiculos)
agency_hash = generate_hash(AGENCY_VALUE)

# Extrair o ID da campanha
if selected_site:
    id_campaign = selected_site.split(' ')[0]
    campaign_row = df_campaigns[df_campaigns['ID'] == id_campaign]
    if not campaign_row.empty:
        campaign_info = campaign_row.iloc[0]
        st.subheader("Informações da Campanha")
        st.write(f"**Campanha:** {campaign_info['Campanha']}")
        st.write(f"**Cliente:** {campaign_info['Cliente']}")
        st.write(f"**Agência:** {campaign_info['Agência']}")
        st.write(f"**Início:** {campaign_info['Início']}")
        st.write(f"**Término:** {campaign_info['Término']}")
    else:
        st.warning("Campanha não encontrada para o ID extraído.")

# Lógica de filtragem
if site_hash == agency_hash:
    filtered_df = df.copy()
    st.subheader("Relatório Completo - Agência")
elif selected_site and selected_veiculo:
    filtered_df = df[df['Site'] == selected_site]
    filtered_df = filtered_df[filtered_df['Zone'].apply(lambda x: f"[{selected_veiculo}]" in str(x))]
    st.subheader(f"Relatório: {selected_site} - {selected_veiculo}")
else:
    st.warning("Acesso negado. Parâmetros inválidos.")
    st.stop()

# Filtro de datas
with st.expander("Filtros de Data"):
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    start_date = st.date_input("Data Inicial", min_date, min_value=min_date, max_value=max_date)
    end_date = st.date_input("Data Final", max_date, min_value=min_date, max_value=max_date)

filtered_df = filtered_df[
    (filtered_df['Date'].dt.date >= start_date) & 
    (filtered_df['Date'].dt.date <= end_date)
]

# Exibir relatório
if filtered_df.empty:
    st.warning("Nenhum dado disponível para os filtros selecionados.")
else:
    total_impressions = filtered_df['Impressions'].sum()
    total_conversions = filtered_df['Conversions'].sum()
    va_percent = (total_conversions / total_impressions * 100) if total_impressions > 0 else 0
    total_clicks = filtered_df['Clicks'].sum()
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Impressões", f"{total_impressions:,.0f}")
        st.metric("Conversões Totais", f"{total_conversions:,.0f}")
    with col2:
        st.metric("VA%", f"{va_percent:.2f}%")
        st.metric("CTR", f"{ctr:.2f}%")

    st.subheader("Impressões Diárias")
    daily_df = filtered_df.groupby('Date')['Impressions'].sum().reset_index()
    fig = px.line(daily_df, x='Date', y='Impressions', 
                  labels={'Date': 'Data', 'Impressions': 'Impressões'},
                  height=400)
    fig.update_layout(autosize=True, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Tabela Resumo 
    st.subheader("Tabela Resumo")
    filtered_df['Veículo'] = filtered_df['Zone'].apply(lambda x: re.search(r'\[(.*?)\]', str(x)).group(1) if re.search(r'\[(.*?)\]', str(x)) else '')
    summary_df = filtered_df.groupby(['Date', 'Veículo', 'Placement Size']).agg(
        Impressions=('Impressions', 'sum'),
        Clicks=('Clicks', 'sum'),
        Conversions=('Conversions', 'sum')
    ).reset_index()

    summary_df = summary_df.rename(columns={'Conversions': 'Viewable Impression'})
    summary_df['VA%'] = (summary_df['Viewable Impression'] / summary_df['Impressions'] * 100).round(2)
    summary_df['CTR'] = (summary_df['Clicks'] / summary_df['Impressions'] * 100).round(2)
    summary_df['Date'] = summary_df['Date'].dt.strftime('%d/%m/%Y')

    summary_df = summary_df[['Date', 'Veículo', 'Placement Size', 'Impressions', 'Clicks', 'Viewable Impression', 'VA%', 'CTR']]

    total_impressions = summary_df['Impressions'].sum()
    total_clicks = summary_df['Clicks'].sum()
    total_viewable_impression = summary_df['Viewable Impression'].sum()
    avg_va = summary_df['VA%'].mean().round(2)
    avg_ctr = summary_df['CTR'].mean().round(2)

    summary_row = pd.DataFrame({
        'Date': ['Total'],
        'Veículo': ['-'],
        'Placement Size': ['-'],
        'Impressions': [total_impressions],
        'Clicks': [total_clicks],
        'Viewable Impression': [total_viewable_impression],
        'VA%': [avg_va],
        'CTR': [avg_ctr]
    })

    summary_df = pd.concat([summary_df, summary_row], ignore_index=True)

    st.dataframe(summary_df.style.format({
        'Impressions': '{:,.0f}',
        'Clicks': '{:,.0f}',
        'Viewable Impression': '{:,.0f}',
        'VA%': '{:.2f}%',
        'CTR': '{:.2f}%'
    }), use_container_width=True)