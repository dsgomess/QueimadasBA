import os

import pandas as pd
import plotly.express as px
import streamlit as st

from databricks import sql
from databricks.sdk.core import Config


# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Queimadas na Bahia",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Monitoramento de Queimadas na Bahia")

st.caption(
    "Análise de focos de calor | Fonte: INPE | Período: 2019–2025"
)


# =========================================================
# CONEXÃO COM O DATABRICKS
# =========================================================

cfg = Config()

warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")


@st.cache_data(ttl=600)
def consultar_gold(query):

    if not warehouse_id:
        raise ValueError(
            "A variável DATABRICKS_WAREHOUSE_ID não foi encontrada."
        )

    hostname = (
        cfg.host
        .replace("https://", "")
        .replace("http://", "")
    )

    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    with sql.connect(
        server_hostname=hostname,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate
    ) as conexao:

        with conexao.cursor() as cursor:

            cursor.execute(query)

            colunas = [
                coluna[0]
                for coluna in cursor.description
            ]

            registros = cursor.fetchall()

    return pd.DataFrame(registros, columns=colunas)


# =========================================================
# CONSULTA ÀS TABELAS GOLD
# =========================================================

try:

    dados_anual = consultar_gold("""
        SELECT
            Ano,
            total_focos,
            risco_fogo_medio,
            variacao_percentual
        FROM workspace.queimadas_bahia.gold_focos_anual
        ORDER BY Ano
    """)

    dados_bioma = consultar_gold("""
        SELECT
            Bioma,
            total_focos,
            risco_fogo_medio,
            precipitacao_media
        FROM workspace.queimadas_bahia.gold_focos_bioma
        ORDER BY total_focos DESC
    """)

    dados_municipio = consultar_gold("""
        SELECT
            Estado,
            Municipio,
            total_focos,
            risco_fogo_medio,
            dias_sem_chuva_medio
        FROM workspace.queimadas_bahia.gold_focos_municipio
        ORDER BY total_focos DESC
    """)

except Exception as erro:

    st.error("Não foi possível consultar as tabelas Gold.")

    st.exception(erro)

    st.stop()


# =========================================================
# INDICADORES GERAIS
# =========================================================

total_focos = int(dados_anual["total_focos"].sum())

ano_critico = int(
    dados_anual.loc[
        dados_anual["total_focos"].idxmax(),
        "Ano"
    ]
)

bioma_critico = dados_bioma.iloc[0]["Bioma"]

municipio_critico = dados_municipio.iloc[0]["Municipio"]


st.success("Dados carregados das tabelas Gold do Databricks.")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total de focos",
    f"{total_focos:,}".replace(",", ".")
)

col2.metric(
    "Ano com mais focos",
    str(ano_critico)
)

col3.metric(
    "Bioma com mais focos",
    bioma_critico
)

col4.metric(
    "Município com mais focos",
    municipio_critico.title()
)


st.divider()


# =========================================================
# ABAS DO DASHBOARD
# =========================================================

aba_anual, aba_bioma, aba_municipio, aba_dados = st.tabs([
    "📈 Evolução anual",
    "🌳 Análise por bioma",
    "📍 Análise por município",
    "📋 Dados detalhados"
])


# =========================================================
# ABA 1 - EVOLUÇÃO ANUAL
# =========================================================

with aba_anual:

    st.subheader("Evolução dos focos de calor")

    fig_anual = px.bar(
        dados_anual,
        x="Ano",
        y="total_focos",
        text="total_focos",
        title="Total de focos por ano",
        labels={
            "Ano": "Ano",
            "total_focos": "Total de focos"
        },
        hover_data=[
            "risco_fogo_medio",
            "variacao_percentual"
        ]
    )

    fig_anual.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    fig_anual.update_layout(
        xaxis=dict(
            tickmode="linear",
            dtick=1
        ),
        yaxis_title="Total de focos",
        xaxis_title="Ano",
        showlegend=False
    )

    st.plotly_chart(
        fig_anual,
        use_container_width=True
    )

    st.subheader("Variação anual")

    dados_variacao = dados_anual[
        ["Ano", "variacao_percentual"]
    ].copy()

    dados_variacao["variacao_percentual"] = (
        dados_variacao["variacao_percentual"].round(2)
    )

    st.dataframe(
        dados_variacao,
        hide_index=True,
        use_container_width=True
    )


# =========================================================
# ABA 2 - ANÁLISE POR BIOMA
# =========================================================

with aba_bioma:

    st.subheader("Distribuição dos focos por bioma")

    col1, col2 = st.columns(2)

    with col1:

        fig_bioma = px.bar(
            dados_bioma,
            x="Bioma",
            y="total_focos",
            text="total_focos",
            title="Total de focos por bioma",
            labels={
                "Bioma": "Bioma",
                "total_focos": "Total de focos"
            },
            hover_data=[
                "risco_fogo_medio",
                "precipitacao_media"
            ]
        )

        fig_bioma.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside"
        )

        fig_bioma.update_layout(
            xaxis_title="Bioma",
            yaxis_title="Total de focos",
            showlegend=False
        )

        st.plotly_chart(
            fig_bioma,
            use_container_width=True
        )

    with col2:

        fig_pizza = px.pie(
            dados_bioma,
            names="Bioma",
            values="total_focos",
            title="Participação de cada bioma",
            hole=0.4
        )

        fig_pizza.update_traces(
            textposition="inside",
            textinfo="percent+label"
        )

        st.plotly_chart(
            fig_pizza,
            use_container_width=True
        )

    st.subheader("Indicadores por bioma")

    dados_bioma_exibicao = dados_bioma.copy()

    dados_bioma_exibicao["risco_fogo_medio"] = (
        dados_bioma_exibicao["risco_fogo_medio"].round(3)
    )

    dados_bioma_exibicao["precipitacao_media"] = (
        dados_bioma_exibicao["precipitacao_media"].round(3)
    )

    st.dataframe(
        dados_bioma_exibicao,
        hide_index=True,
        use_container_width=True
    )


# =========================================================
# ABA 3 - ANÁLISE POR MUNICÍPIO
# =========================================================

with aba_municipio:

    st.subheader("Ranking de municípios")

    quantidade = st.slider(
        "Quantidade de municípios no ranking",
        min_value=5,
        max_value=min(30, len(dados_municipio)),
        value=min(10, len(dados_municipio)),
        step=5
    )

    dados_top = (
        dados_municipio
        .sort_values("total_focos", ascending=False)
        .head(quantidade)
        .copy()
    )

    fig_municipios = px.bar(
        dados_top.sort_values(
            "total_focos",
            ascending=True
        ),
        x="total_focos",
        y="Municipio",
        orientation="h",
        text="total_focos",
        title=f"Top {quantidade} municípios por focos de calor",
        labels={
            "Municipio": "Município",
            "total_focos": "Total de focos"
        },
        hover_data=[
            "Estado",
            "risco_fogo_medio",
            "dias_sem_chuva_medio"
        ]
    )

    fig_municipios.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    fig_municipios.update_layout(
        yaxis_title="Município",
        xaxis_title="Total de focos",
        showlegend=False,
        height=max(450, quantidade * 35)
    )

    st.plotly_chart(
        fig_municipios,
        use_container_width=True
    )

    st.subheader("Detalhamento dos municípios")

    dados_top["risco_fogo_medio"] = (
        dados_top["risco_fogo_medio"].round(3)
    )

    dados_top["dias_sem_chuva_medio"] = (
        dados_top["dias_sem_chuva_medio"].round(1)
    )

    st.dataframe(
        dados_top,
        hide_index=True,
        use_container_width=True
    )


# =========================================================
# ABA 4 - DADOS DETALHADOS
# =========================================================

with aba_dados:

    st.subheader("Explore as tabelas Gold")

    tipo_tabela = st.selectbox(
        "Selecione a tabela",
        [
            "Resumo anual",
            "Resumo por bioma",
            "Resumo por município"
        ]
    )

    if tipo_tabela == "Resumo anual":

        st.dataframe(
            dados_anual,
            hide_index=True,
            use_container_width=True
        )

    elif tipo_tabela == "Resumo por bioma":

        st.dataframe(
            dados_bioma,
            hide_index=True,
            use_container_width=True
        )

    else:

        st.dataframe(
            dados_municipio,
            hide_index=True,
            use_container_width=True
        )


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "Projeto de análise de dados | Fonte: INPE | "
    "Arquitetura Medallion: Bronze, Silver e Gold | "
    "Dashboard desenvolvido com Streamlit e Databricks."
)