import os
import pandas as pd
import streamlit as st

from databricks import sql
from databricks.sdk.core import Config


st.set_page_config(
    page_title="Queimadas na Bahia",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Monitoramento de Queimadas na Bahia")
st.caption("Dados do INPE | 2019–2025")

# Configuração de autenticação do Databricks App
cfg = Config()

# Warehouse configurado em Settings > Resources
warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")


@st.cache_data(ttl=600)
def consultar_gold():

    if not warehouse_id:
        raise ValueError(
            "A variável DATABRICKS_WAREHOUSE_ID não foi encontrada."
        )

    hostname = cfg.host.replace("https://", "").replace("http://", "")

    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    with sql.connect(
        server_hostname=hostname,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate
    ) as conexao:

        with conexao.cursor() as cursor:

            cursor.execute("""
                SELECT
                    Ano,
                    total_focos,
                    risco_fogo_medio,
                    variacao_percentual
                FROM workspace.queimadas_bahia.gold_focos_anual
                ORDER BY Ano
            """)

            colunas = [coluna[0] for coluna in cursor.description]
            registros = cursor.fetchall()

    return pd.DataFrame(registros, columns=colunas)


try:
    dados = consultar_gold()

    st.success("Conexão com a tabela Gold realizada com sucesso!")

    total_focos = int(dados["total_focos"].sum())

    ano_critico = int(
        dados.loc[dados["total_focos"].idxmax(), "Ano"]
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Total de focos",
        f"{total_focos:,}".replace(",", ".")
    )

    col2.metric(
        "Ano com mais focos",
        str(ano_critico)
    )

    st.subheader("Focos de calor por ano")

    st.bar_chart(
        dados,
        x="Ano",
        y="total_focos"
    )

    st.subheader("Dados da tabela Gold")

    st.dataframe(dados, use_container_width=True)

except Exception as erro:
    st.error("Não foi possível consultar a tabela Gold.")
    st.exception(erro)