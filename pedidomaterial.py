# app.py

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta

# -------------------- CONFIGURAÇÕES INICIAIS --------------------
st.set_page_config(page_title="COGEX Almoxarifado", layout="wide")
st.title("\ud83d\udce6 COGEX ALMOXARIFADO")
st.markdown("**Sistema Integrado Google Sheets - Pedido de Material com Imagens e Filtros**")

# -------------------- CARREGAMENTO DE DADOS --------------------
@st.cache_data(show_spinner="Carregando dados do Google Sheets...")
def load_data():
    url_inventory = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSeWsxmLFzuWsa2oggpQb6p5SFapxXHcWaIl0Jjf2wAezvMgAV9XCc1r7fSSzRWTCgjk9eqREgWlrzp/pub?gid=1710164548&single=true&output=csv'
    url_items = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSeWsxmLFzuWsa2oggpQb6p5SFapxXHcWaIl0Jjf2wAezvMgAV9XCc1r7fSSzRWTCgjk9eqREgWlrzp/pub?gid=1011017078&single=true&output=csv'

    inventory = pd.read_csv(url_inventory)
    inventory['DateTime'] = pd.to_datetime(inventory['DateTime'], errors='coerce')
    items = pd.read_csv(url_items)
    return items, inventory

items_df, inventory_df = load_data()

# -------------------- PREPARAÇÃO DOS DADOS --------------------
merged_df = pd.merge(inventory_df, items_df, on='Item ID', how='left')
merged_df['Ano'] = merged_df['DateTime'].dt.year
merged_df['M\u00eas'] = merged_df['DateTime'].dt.month
merged_df['Semana'] = merged_df['DateTime'].dt.isocalendar().week

# -------------------- FILTROS LATERAIS --------------------
st.sidebar.title("Filtros")
produtos = st.sidebar.multiselect("Selecione os Produtos:", options=items_df['Name'].unique(), default=items_df['Name'].unique())
filtered_df = merged_df[merged_df['Name'].isin(produtos)]

# -------------------- CONSUMO M\u00c9DIO --------------------
st.header("\ud83d\udcca Consumo M\u00e9dio & Pedido de Material")

def consumo_medio(df, dias):
    data_limite = datetime.now() - timedelta(days=dias)
    consumo = df[(df['DateTime'] >= data_limite) & (df['Amount'] < 0)]
    consumo_agrupado = consumo.groupby('Name')['Amount'].sum().abs().reset_index()
    consumo_agrupado.rename(columns={'Amount': f'Consumo M\u00e9dio {dias} dias'}, inplace=True)
    return consumo_agrupado

consumo_7 = consumo_medio(filtered_df, 7)
consumo_15 = consumo_medio(filtered_df, 15)
consumo_30 = consumo_medio(filtered_df, 30)
consumo_45 = consumo_medio(filtered_df, 45)

consumo_total = consumo_7.merge(consumo_15, on='Name', how='outer').merge(consumo_30, on='Name', how='outer').merge(consumo_45, on='Name', how='outer').fillna(0)

estoque_atual = inventory_df.groupby('Item ID')['Amount'].sum().reset_index()
estoque_atual = pd.merge(estoque_atual, items_df[['Item ID', 'Name']], on='Item ID', how='left')

pedido_material = pd.merge(consumo_total, estoque_atual, on='Name', how='left')
pedido_material['Estoque Atual'] = pedido_material['Amount']
pedido_material.drop(columns=['Amount'], inplace=True)

pedido_material['Recomenda\u00e7\u00e3o Pedido'] = np.where(pedido_material['Estoque Atual'] < pedido_material['Consumo M\u00e9dio 15 dias'], 'Pedido Necess\u00e1rio', 'OK')

st.dataframe(pedido_material)

# -------------------- GR\u00c1FICOS --------------------
st.subheader("\ud83d\udcc8 Gr\u00e1fico - Consumo M\u00e9dio por Produto (15 dias)")
chart = alt.Chart(pedido_material).mark_bar().encode(
    x=alt.X('Name:N', sort='-y'),
    y='Consumo M\u00e9dio 15 dias:Q',
    color=alt.Color('Recomenda\u00e7\u00e3o Pedido:N', scale=alt.Scale(domain=['Pedido Necess\u00e1rio', 'OK'], range=['red', 'green'])),
    tooltip=['Name', 'Estoque Atual', 'Consumo M\u00e9dio 15 dias', 'Recomenda\u00e7\u00e3o Pedido']
).properties(width=900, height=400)

st.altair_chart(chart)

# -------------------- RANKING --------------------
st.subheader("\ud83c\udfc6 Ranking - Itens Mais Consumidos (\u00daltimos 30 dias)")
ranking_30 = consumo_medio(filtered_df, 30).sort_values(by='Consumo M\u00e9dio 30 dias', ascending=False)
st.table(ranking_30)

# -------------------- RELAT\u00d3RIO DE PEDIDO --------------------
st.download_button(
    label="\ud83d\udcc5 Baixar Relat\u00f3rio Pedido (CSV)",
    data=pedido_material.to_csv(index=False).encode('utf-8'),
    file_name='pedido_material_cogex.csv',
    mime='text/csv'
)
