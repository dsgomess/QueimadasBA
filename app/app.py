import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Queimadas na Bahia",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Monitoramento de Queimadas na Bahia")
st.caption("Análise dos focos de calor registrados entre 2019 e 2025")

dados = pd.DataFrame({
    "Ano": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "Total de Focos": [
        157346, 161367, 340976, 239010,
        298220, 224936, 307664
    ]
})

total_focos = dados["Total de Focos"].sum()
ano_critico = dados.loc[dados["Total de Focos"].idxmax(), "Ano"]

col1, col2 = st.columns(2)

col1.metric("Total de Focos", f"{total_focos:,}".replace(",", "."))
col2.metric("Ano com Mais Focos", str(ano_critico))

fig = px.bar(
    dados,
    x="Ano",
    y="Total de Focos",
    title="Evolução Anual dos Focos de Calor",
    text_auto=True
)

st.plotly_chart(fig, use_container_width=True)