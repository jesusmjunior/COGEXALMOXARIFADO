import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO

# -------------------- CONFIGURAÇÕES INICIAIS --------------------
st.set_page_config(page_title="COGEX Almoxarifado", layout="wide")

st.title("📦 COGEX ALMOXARIFADO")
st.markdown("**Sistema de Gestão de Pedido de Material Automatizado**")

# -------------------- CARREGAMENTO DE DADOS --------------------
@st.cache_data
def load_data():
    items = pd.read_csv('data/items.csv')
    inventory = pd.read_csv('data/inventory.csv')
    inventory['DateTime'] = pd.to_datetime(inventory['DateTime'])
    return items, inventory

items_df, inventory_df = load_data()

# -------------------- FUNÇÕES UTILITÁRIAS --------------------
def calcular_consumo_medio(inventory):
    consumo = inventory[inventory['Amount'] < 0].groupby('Item ID')['Amount'].sum().abs()
    dias = (inventory['DateTime'].max() - inventory['DateTime'].min()).days
    consumo_medio = consumo / dias
    return consumo_medio

def calcular_saldo_atual(inventory):
    saldo = inventory.groupby('Item ID')['Amount'].sum()
    return saldo

def gerar_pedido(cobertura_dias):
    consumo = calcular_consumo_medio(inventory_df)
    saldo = calcular_saldo_atual(inventory_df)

    pedido_df = pd.DataFrame()
    pedido_df['Consumo Médio Diário'] = consumo
    pedido_df['Estoque Atual'] = saldo
    pedido_df['Necessidade'] = (pedido_df['Consumo Médio Diário'] * cobertura_dias).round()
    pedido_df['A Pedir'] = pedido_df['Necessidade'] - pedido_df['Estoque Atual']
    pedido_df['Status'] = pedido_df['A Pedir'].apply(lambda x: 'Dentro do padrão' if x <= 0 else 'Reposição necessária')
    pedido_df = pedido_df.reset_index()
    pedido_df = pd.merge(pedido_df, items_df[['Item ID', 'Name', 'Description', 'Image']], on='Item ID', how='left')
    return pedido_df

def export_pdf(df, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.set_font("Arial", size=10)
    for i, row in df.iterrows():
        pdf.multi_cell(0, 10, txt=str(row.to_dict()))
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer

# -------------------- INTERFACE STREAMLIT --------------------
menu = st.sidebar.selectbox("Navegar", ["Pedido de Material", "Estoque Atual", "Estatísticas"])

# -------------------- ABA 1: PEDIDO DE MATERIAL --------------------
if menu == "Pedido de Material":
    st.header("📄 Pedido de Material Automático")
    dias = st.radio("Selecione a Cobertura (Dias):", [7, 15, 30, 45], horizontal=True)

    pedido = gerar_pedido(dias)
    st.subheader(f"Pedido de Material para {dias} dias de cobertura:")
    st.dataframe(pedido, use_container_width=True)

    csv = pedido.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Pedido em CSV", data=csv, file_name=f'pedido_{dias}dias.csv', mime='text/csv')

    pdf_buffer = export_pdf(pedido, f"Pedido de Material - Cobertura {dias} dias")
    st.download_button("📄 Baixar Pedido em PDF", data=pdf_buffer.getvalue(), file_name=f'pedido_{dias}dias.pdf', mime='application/pdf')

# -------------------- ABA 2: ESTOQUE ATUAL --------------------
elif menu == "Estoque Atual":
    st.header("📊 Estoque Atual")
    saldo = calcular_saldo_atual(inventory_df).reset_index()
    saldo.columns = ['Item ID', 'Saldo Atual']
    saldo['Status'] = saldo['Saldo Atual'].apply(lambda x: 'Saldo Negativo' if x < 0 else 'Ok')
    saldo = pd.merge(saldo, items_df[['Item ID', 'Name', 'Description', 'Image']], on='Item ID', how='left')
    st.dataframe(saldo, use_container_width=True)

    csv_saldo = saldo.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Estoque Atual CSV", data=csv_saldo, file_name='estoque_atual.csv', mime='text/csv')

    pdf_buffer = export_pdf(saldo, "Estoque Atual")
    st.download_button("📄 Baixar Estoque Atual PDF", data=pdf_buffer.getvalue(), file_name='estoque_atual.pdf', mime='application/pdf')

# -------------------- ABA 3: ESTATÍSTICAS --------------------
elif menu == "Estatísticas":
    st.header("📈 Análises e Estatísticas")

    # Saldo Atual por Item ID
    saldo = calcular_saldo_atual(inventory_df)
    st.subheader("Saldo Atual por Item ID")
    fig, ax = plt.subplots()
    saldo.plot(kind='bar', ax=ax)
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Movimentação histórica
    st.subheader("Movimentação Histórica por Mês")
    inventory_df['Mes/Ano'] = inventory_df['DateTime'].dt.to_period('M')
    movimento = inventory_df.groupby('Mes/Ano')['Amount'].sum()
    fig2, ax2 = plt.subplots()
    movimento.plot(kind='line', ax=ax2, marker='o')
    plt.xticks(rotation=45)
    st.pyplot(fig2)

    # Total de Movimentações
    st.subheader("Total de Movimentações Registradas")
    st.write(f"Total de registros no inventário: **{len(inventory_df)}**")

# -------------------- RODAPÉ --------------------
st.markdown("---")
st.markdown("**COGEX ALMOXARIFADO - SISTEMA DE PEDIDO DE MATERIAL AUTOMATIZADO | Powered by Streamlit**")
