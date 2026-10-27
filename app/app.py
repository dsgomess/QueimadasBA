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
# CARREGAMENTO DA GOLD ANALÍTICA
# =========================================================

@st.cache_data(ttl=600)
def carregar_dados():

    query = """
        SELECT
            Ano,
            Mes,
            Bioma,
            Municipio,
            total_focos,
            risco_fogo_medio,
            precipitacao_media,
            dias_sem_chuva_medio,
            qtd_risco_valido,
            qtd_precipitacao_valida,
            qtd_dias_sem_chuva_validos
        FROM workspace.queimadas_bahia.gold_focos_analitico
    """

    dados = consultar_gold(query)

    dados["Ano"] = dados["Ano"].astype(int)
    dados["Mes"] = dados["Mes"].astype(int)
    dados["total_focos"] = dados["total_focos"].astype(int)

    return dados


try:

    dados = carregar_dados()

except Exception as erro:

    st.error("Não foi possível carregar a tabela Gold analítica.")
    st.exception(erro)
    st.stop()



# =========================================================
# FILTROS LATERAIS
# =========================================================

st.sidebar.title("🔎 Filtros")
st.sidebar.caption("Selecione os períodos e as categorias que deseja analisar.")

# 1. ANO — intervalo de anos
anos_disponiveis = sorted(
    dados["Ano"].dropna().unique().tolist()
)

ano_min, ano_max = st.sidebar.select_slider(
    "📅 Período (ano)",
    options=anos_disponiveis,
    value=(min(anos_disponiveis), max(anos_disponiveis))
)

anos_selecionados = [
    ano for ano in anos_disponiveis
    if ano_min <= ano <= ano_max
]

dados_ano = dados[
    dados["Ano"].isin(anos_selecionados)
].copy()


# 2. BIOMAS — checkboxes
st.sidebar.subheader("🌳 Biomas")

biomas_disponiveis = (
    dados_ano.groupby("Bioma")["total_focos"]
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

if st.sidebar.button("Selecionar todos os biomas"):
    st.session_state["biomas_selecionados"] = biomas_disponiveis.copy()

if st.sidebar.button("Limpar seleção de biomas"):
    st.session_state["biomas_selecionados"] = []

if "biomas_selecionados" not in st.session_state:
    st.session_state["biomas_selecionados"] = biomas_disponiveis.copy()

# Remove da seleção biomas que não estão mais disponíveis
st.session_state["biomas_selecionados"] = [
    b for b in st.session_state["biomas_selecionados"]
    if b in biomas_disponiveis
]

biomas_selecionados = []

for bioma in biomas_disponiveis:
    marcado = st.sidebar.checkbox(
        bioma,
        value=bioma in st.session_state["biomas_selecionados"],
        key=f"bioma_{bioma}"
    )

    if marcado:
        biomas_selecionados.append(bioma)

st.session_state["biomas_selecionados"] = biomas_selecionados

dados_bioma = dados_ano[
    dados_ano["Bioma"].isin(biomas_selecionados)
].copy()


# 3. MESES — checkboxes
st.sidebar.subheader("📆 Meses")

nomes_meses = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

meses_disponiveis = sorted(
    dados_bioma["Mes"].dropna().unique().astype(int).tolist()
)

if st.sidebar.button("Selecionar todos os meses"):
    st.session_state["meses_selecionados"] = meses_disponiveis.copy()

if st.sidebar.button("Limpar seleção de meses"):
    st.session_state["meses_selecionados"] = []

if "meses_selecionados" not in st.session_state:
    st.session_state["meses_selecionados"] = meses_disponiveis.copy()

st.session_state["meses_selecionados"] = [
    m for m in st.session_state["meses_selecionados"]
    if m in meses_disponiveis
]

meses_selecionados = []

for mes in meses_disponiveis:
    marcado = st.sidebar.checkbox(
        nomes_meses[mes],
        value=mes in st.session_state["meses_selecionados"],
        key=f"mes_{mes}"
    )

    if marcado:
        meses_selecionados.append(mes)

st.session_state["meses_selecionados"] = meses_selecionados

dados_base = dados_bioma[
    dados_bioma["Mes"].isin(meses_selecionados)
].copy()


# 4. MUNICÍPIOS — checkboxes
st.sidebar.subheader("📍 Municípios")

municipios_disponiveis = (
    dados_base.groupby("Municipio")["total_focos"]
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

if st.sidebar.button("Selecionar todos os municípios"):
    st.session_state["municipios_selecionados"] = municipios_disponiveis.copy()

if st.sidebar.button("Limpar seleção de municípios"):
    st.session_state["municipios_selecionados"] = []

if "municipios_selecionados" not in st.session_state:
    st.session_state["municipios_selecionados"] = municipios_disponiveis.copy()

st.session_state["municipios_selecionados"] = [
    m for m in st.session_state["municipios_selecionados"]
    if m in municipios_disponiveis
]

municipios_selecionados = []

# Limita a quantidade exibida para a barra lateral não ficar excessivamente longa
limite_municipios_exibidos = 100
municipios_exibidos = municipios_disponiveis[:limite_municipios_exibidos]

for municipio in municipios_exibidos:
    marcado = st.sidebar.checkbox(
        municipio,
        value=municipio in st.session_state["municipios_selecionados"],
        key=f"municipio_{municipio}"
    )

    if marcado:
        municipios_selecionados.append(municipio)

st.session_state["municipios_selecionados"] = municipios_selecionados

if len(municipios_disponiveis) > limite_municipios_exibidos:
    st.sidebar.caption(
        f"Exibindo os {limite_municipios_exibidos} municípios "
        "com mais focos no período selecionado."
    )

# 5. APLICAÇÃO DOS FILTROS
dados_filtrados = dados_base[
    dados_base["Municipio"].isin(municipios_selecionados)
].copy()

st.sidebar.divider()
st.sidebar.caption(f"Biomas selecionados: {len(biomas_selecionados)}")
st.sidebar.caption(f"Meses selecionados: {len(meses_selecionados)}")
st.sidebar.caption(f"Municípios selecionados: {len(municipios_selecionados)}")

if st.sidebar.button("Limpar cache dos dados"):
    st.cache_data.clear()
    st.rerun()



# =========================================================
# FUNÇÕES AUXILIARES PARA OS KPIs
# =========================================================

def media_ponderada(
    df,
    coluna_media,
    coluna_quantidade
):

    validos = df[
        df[coluna_media].notna()
        & (df[coluna_quantidade] > 0)
    ]

    if validos.empty:
        return None

    denominador = validos[coluna_quantidade].sum()

    if denominador == 0:
        return None

    return (
        validos[coluna_media]
        * validos[coluna_quantidade]
    ).sum() / denominador


def formatar_inteiro(valor):

    return f"{int(valor):,}".replace(",", ".")


def formatar_decimal(valor, casas=2):

    if valor is None or pd.isna(valor):
        return "N/D"

    return f"{valor:.{casas}f}".replace(".", ",")


# =========================================================
# VALIDAÇÃO DOS FILTROS
# =========================================================

if dados_filtrados.empty:

    st.warning(
        "Nenhum registro encontrado para os filtros selecionados. "
        "Altere os critérios na barra lateral."
    )

    st.stop()


# =========================================================
# INDICADORES DINÂMICOS
# =========================================================

total_focos = int(
    dados_filtrados["total_focos"].sum()
)

risco_medio = media_ponderada(
    dados_filtrados,
    "risco_fogo_medio",
    "qtd_risco_valido"
)

# Ano com maior número de focos dentro da seleção.

focos_por_ano = (
    dados_filtrados
    .groupby("Ano", as_index=False)["total_focos"]
    .sum()
)

ano_critico = int(
    focos_por_ano.loc[
        focos_por_ano["total_focos"].idxmax(),
        "Ano"
    ]
)

# Bioma e município com mais focos dentro da seleção.

focos_por_bioma = (
    dados_filtrados
    .groupby("Bioma", as_index=False)["total_focos"]
    .sum()
    .sort_values("total_focos", ascending=False)
)

focos_por_municipio = (
    dados_filtrados
    .groupby("Municipio", as_index=False)["total_focos"]
    .sum()
    .sort_values("total_focos", ascending=False)
)

bioma_critico = focos_por_bioma.iloc[0]["Bioma"]

municipio_critico = focos_por_municipio.iloc[0]["Municipio"]


# =========================================================
# CABEÇALHO E KPIs
# =========================================================

st.subheader("Visão geral")

st.caption(
    f"Período selecionado: "
    f"{min(anos_selecionados) if anos_selecionados else '—'} "
    f"a {max(anos_selecionados) if anos_selecionados else '—'}"
    if anos_selecionados
    else "Nenhum ano selecionado"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total de focos",
    formatar_inteiro(total_focos)
)

col2.metric(
    "Ano mais crítico",
    str(ano_critico)
)

col3.metric(
    "Bioma mais afetado",
    bioma_critico
)

col4.metric(
    "Risco médio de fogo",
    formatar_decimal(risco_medio, 3)
)

st.divider()


# =========================================================
# ABAS DO DASHBOARD
# =========================================================

aba_geral, aba_bioma, aba_municipio, aba_sazonalidade = st.tabs([
    "📊 Visão geral",
    "🌳 Biomas",
    "📍 Municípios",
    "📅 Sazonalidade"
])


# =========================================================
# ABA 1 - VISÃO GERAL
# =========================================================

with aba_geral:

    st.subheader("Evolução anual dos focos")

    fig_anual = px.bar(
        focos_por_ano,
        x="Ano",
        y="total_focos",
        text="total_focos",
        labels={
            "Ano": "Ano",
            "total_focos": "Total de focos"
        },
        title="Focos de calor por ano"
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
        showlegend=False
    )

    st.plotly_chart(
        fig_anual,
        use_container_width=True
    )

    st.subheader("Resumo dos registros filtrados")

    st.dataframe(
        dados_filtrados[
            [
                "Ano",
                "Mes",
                "Bioma",
                "Municipio",
                "total_focos"
            ]
        ].sort_values(
            ["Ano", "total_focos"],
            ascending=[True, False]
        ),
        hide_index=True,
        use_container_width=True
    )


# =========================================================
# ABA 2 - BIOMAS
# =========================================================

with aba_bioma:

    st.subheader("Distribuição por bioma")

    dados_bioma = (
        dados_filtrados
        .groupby("Bioma", as_index=False)
        .agg(
            total_focos=("total_focos", "sum")
        )
        .sort_values("total_focos", ascending=False)
    )

    fig_bioma = px.bar(
        dados_bioma,
        x="Bioma",
        y="total_focos",
        text="total_focos",
        title="Total de focos por bioma",
        labels={
            "Bioma": "Bioma",
            "total_focos": "Total de focos"
        }
    )

    fig_bioma.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    st.plotly_chart(
        fig_bioma,
        use_container_width=True
    )

    fig_pizza = px.pie(
        dados_bioma,
        names="Bioma",
        values="total_focos",
        title="Participação dos biomas",
        hole=0.4
    )

    fig_pizza.update_traces(
        textinfo="percent+label"
    )

    st.plotly_chart(
        fig_pizza,
        use_container_width=True
    )


# =========================================================
# ABA 3 - MUNICÍPIOS
# =========================================================

with aba_municipio:

    st.subheader("Ranking de municípios")

    quantidade_maxima = min(
        30,
        len(focos_por_municipio)
    )

    quantidade = st.slider(
        "Municípios no ranking",
        min_value=1,
        max_value=quantidade_maxima,
        value=min(10, quantidade_maxima)
    )

    dados_top = (
        focos_por_municipio
        .head(quantidade)
        .sort_values("total_focos", ascending=True)
    )

    fig_municipios = px.bar(
        dados_top,
        x="total_focos",
        y="Municipio",
        orientation="h",
        text="total_focos",
        title=f"Top {quantidade} municípios",
        labels={
            "Municipio": "Município",
            "total_focos": "Total de focos"
        }
    )

    fig_municipios.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    fig_municipios.update_layout(
        height=max(450, quantidade * 35)
    )

    st.plotly_chart(
        fig_municipios,
        use_container_width=True
    )

    st.subheader("Indicadores municipais")

    dados_municipio = dados_filtrados.copy()

    dados_municipio["risco_ponderado"] = (
        dados_municipio["risco_fogo_medio"]
        * dados_municipio["qtd_risco_valido"]
    )

    dados_municipio["dias_sem_chuva_ponderado"] = (
        dados_municipio["dias_sem_chuva_medio"]
        * dados_municipio["qtd_dias_sem_chuva_validos"]
    )

    resumo_municipios = (
        dados_municipio
        .groupby("Municipio", as_index=False)
        .agg(
            total_focos=("total_focos", "sum"),
            soma_risco=("risco_ponderado", "sum"),
            qtd_risco=("qtd_risco_valido", "sum"),
            soma_dias=("dias_sem_chuva_ponderado", "sum"),
            qtd_dias=("qtd_dias_sem_chuva_validos", "sum")
        )
    )

    resumo_municipios["risco_fogo_medio"] = (
        resumo_municipios["soma_risco"]
        / resumo_municipios["qtd_risco"].replace(0, float("nan"))
    )

    resumo_municipios["dias_sem_chuva_medio"] = (
        resumo_municipios["soma_dias"]
        / resumo_municipios["qtd_dias"].replace(0, float("nan"))
    )

    st.dataframe(
        resumo_municipios[
            [
                "Municipio",
                "total_focos",
                "risco_fogo_medio",
                "dias_sem_chuva_medio"
            ]
        ].sort_values(
            "total_focos",
            ascending=False
        ),
        hide_index=True,
        use_container_width=True
    )


# =========================================================
# ABA 4 - SAZONALIDADE
# =========================================================

with aba_sazonalidade:

    st.subheader("Distribuição mensal dos focos")

    focos_por_mes = (
        dados_filtrados
        .groupby("Mes", as_index=False)["total_focos"]
        .sum()
        .sort_values("Mes")
    )

    focos_por_mes["Nome_mes"] = (
        focos_por_mes["Mes"].map(nomes_meses)
    )

    mes_critico = focos_por_mes.loc[
        focos_por_mes["total_focos"].idxmax()
    ]

    col1, col2 = st.columns(2)

    col1.metric(
        "Mês com mais focos",
        mes_critico["Nome_mes"]
    )

    col2.metric(
        "Focos no mês mais crítico",
        formatar_inteiro(mes_critico["total_focos"])
    )

    fig_mensal = px.bar(
        focos_por_mes,
        x="Nome_mes",
        y="total_focos",
        text="total_focos",
        title="Focos por mês",
        labels={
            "Nome_mes": "Mês",
            "total_focos": "Total de focos"
        },
        category_orders={
            "Nome_mes": list(nomes_meses.values())
        }
    )

    fig_mensal.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    st.plotly_chart(
        fig_mensal,
        use_container_width=True
    )

    st.subheader("Comparação mensal entre anos")

    comparacao = (
        dados_filtrados
        .groupby(
            ["Ano", "Mes"],
            as_index=False
        )["total_focos"]
        .sum()
    )

    comparacao["Nome_mes"] = (
        comparacao["Mes"].map(nomes_meses)
    )

    fig_comparacao = px.line(
        comparacao,
        x="Nome_mes",
        y="total_focos",
        color="Ano",
        markers=True,
        title="Sazonalidade por ano",
        labels={
            "Nome_mes": "Mês",
            "total_focos": "Total de focos",
            "Ano": "Ano"
        },
        category_orders={
            "Nome_mes": list(nomes_meses.values())
        }
    )

    st.plotly_chart(
        fig_comparacao,
        use_container_width=True
    )


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "Fonte: INPE | Arquitetura Medallion: Bronze, Silver e Gold | "
    "Aplicação desenvolvida com Streamlit e Databricks."
)