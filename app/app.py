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


def definir_todos(prefixo, itens, valor):
    """Callback dos botões: escreve direto nas keys dos checkboxes."""
    for item in itens:
        st.session_state[f"{prefixo}_{item}"] = valor


# 1. ANO
anos_disponiveis = sorted(dados["Ano"].dropna().unique().tolist())

ano_min, ano_max = st.sidebar.select_slider(
    "📅 Período (ano)",
    options=anos_disponiveis,
    value=(min(anos_disponiveis), max(anos_disponiveis))
)

anos_selecionados = [a for a in anos_disponiveis if ano_min <= a <= ano_max]
dados_ano = dados[dados["Ano"].isin(anos_selecionados)].copy()


# 2. BIOMAS (checkbox)
st.sidebar.subheader("🌳 Biomas")

biomas_disponiveis = (
    dados_ano.groupby("Bioma")["total_focos"]
    .sum().sort_values(ascending=False).index.tolist()
)

st.sidebar.button(
    "Selecionar todos os biomas",
    on_click=definir_todos, args=("bioma", biomas_disponiveis, True)
)
st.sidebar.button(
    "Limpar seleção de biomas",
    on_click=definir_todos, args=("bioma", biomas_disponiveis, False)
)

biomas_selecionados = []
for bioma in biomas_disponiveis:
    st.session_state.setdefault(f"bioma_{bioma}", True)
    if st.sidebar.checkbox(bioma, key=f"bioma_{bioma}"):
        biomas_selecionados.append(bioma)

dados_bioma = dados_ano[dados_ano["Bioma"].isin(biomas_selecionados)].copy()


# 3. MESES (checkbox)
st.sidebar.subheader("📆 Meses")

nomes_meses = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

meses_disponiveis = sorted(dados_bioma["Mes"].dropna().unique().astype(int).tolist())

st.sidebar.button(
    "Selecionar todos os meses",
    on_click=definir_todos, args=("mes", meses_disponiveis, True)
)
st.sidebar.button(
    "Limpar seleção de meses",
    on_click=definir_todos, args=("mes", meses_disponiveis, False)
)

meses_selecionados = []
for mes in meses_disponiveis:
    st.session_state.setdefault(f"mes_{mes}", True)
    if st.sidebar.checkbox(nomes_meses[mes], key=f"mes_{mes}"):
        meses_selecionados.append(mes)

dados_base = dados_bioma[dados_bioma["Mes"].isin(meses_selecionados)].copy()


# 4. MUNICÍPIOS (multiselect; vazio = todos)
st.sidebar.subheader("📍 Municípios")

municipios_disponiveis = (
    dados_base.groupby("Municipio")["total_focos"]
    .sum().sort_values(ascending=False).index.tolist()
)

municipios_escolhidos = st.sidebar.multiselect(
    "Buscar município",
    options=municipios_disponiveis,
    placeholder="Todos"
)
municipios_selecionados = municipios_escolhidos or municipios_disponiveis


# 5. APLICAÇÃO DOS FILTROS
dados_filtrados = dados_base[
    dados_base["Municipio"].isin(municipios_selecionados)
].copy()

st.sidebar.divider()
st.sidebar.caption(f"Biomas selecionados: {len(biomas_selecionados)}")
st.sidebar.caption(f"Meses selecionados: {len(meses_selecionados)}")
st.sidebar.caption(f"Municípios considerados: {len(municipios_selecionados)}")

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
# VARIAÇÃO YEAR-OVER-YEAR (YoY)
# =========================================================

def calcular_yoy(
    dados,
    ano_atual,
    biomas,
    meses,
    municipios
):
    """
    Compara o último ano selecionado com o ano anterior,
    mantendo os filtros de bioma, mês e município.
    """

    if ano_atual - 1 not in dados["Ano"].unique():
        return None

    def total_do_ano(ano):
        df = dados[
            (dados["Ano"] == ano)
            & dados["Bioma"].isin(biomas)
            & dados["Mes"].isin(meses)
            & dados["Municipio"].isin(municipios)
        ]

        return int(df["total_focos"].sum())

    atual = total_do_ano(ano_atual)
    anterior = total_do_ano(ano_atual - 1)

    if anterior == 0:
        return None

    return ((atual - anterior) / anterior) * 100


def formatar_yoy(valor):
    if valor is None or pd.isna(valor):
        return "N/D"

    return f"{valor:+.1f}%".replace(".", ",")

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
# CABEÇALHO
# =========================================================

st.subheader("Monitoramento de Queimadas na Bahia")

st.caption(
    f"Período selecionado: {min(anos_selecionados)} "
    f"a {max(anos_selecionados)}"
)

ano_referencia = max(anos_selecionados)

yoy_geral = calcular_yoy(
    dados,
    ano_referencia,
    biomas_selecionados,
    meses_selecionados,
    municipios_selecionados
)

st.caption(
    f"Comparação YoY: {ano_referencia} "
    f"em relação a {ano_referencia - 1}"
    if yoy_geral is not None
    else "Comparação YoY indisponível para o período."
)


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

    # KPIs DA VISÃO GERAL
    focos_ano_ref = int(
        focos_por_ano.loc[focos_por_ano["Ano"] == ano_referencia, "total_focos"].sum()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total de focos",
        formatar_inteiro(total_focos)
    )

    col2.metric(
        "Variação YoY",
        formatar_yoy(yoy_geral),
        delta=(
            f"{formatar_yoy(yoy_geral)} vs. ano anterior"
            if yoy_geral is not None
            else None
        )
    )

    col3.metric(
        "Município com mais focos",
        municipio_critico
    )

    col4.metric(
        "Risco médio de fogo",
        formatar_decimal(risco_medio, 3)
    )

    st.divider()

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

    # KPIs DA PÁGINA BIOMAS

    bioma_top = focos_por_bioma.iloc[0]
    bioma_mais_focos = bioma_top["Bioma"]
    participacao_biomas = bioma_top["total_focos"] / total_focos * 100

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Bioma com mais focos", bioma_mais_focos)
    col2.metric("Total de focos", formatar_inteiro(total_focos))
    col3.metric("Participação do bioma líder", f"{participacao_biomas:.1f}%".replace(".", ","))
    col4.metric("Variação YoY", formatar_yoy(yoy_geral))

    st.divider()

    st.subheader("Distribuição por bioma")

    resumo_bioma = (
        dados_filtrados
        .groupby("Bioma", as_index=False)
        .agg(
            total_focos=("total_focos", "sum")
        )
        .sort_values("total_focos", ascending=False)
    )

    fig_bioma = px.bar(
        resumo_bioma,
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
        resumo_bioma,
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

        # KPIs DA PÁGINA MUNICÍPIOS

    total_focos_municipios = int(
        focos_por_municipio["total_focos"].sum()
    )

    municipio_mais_focos = (
        focos_por_municipio.iloc[0]["Municipio"]
    )

    risco_medio_municipios = media_ponderada(
        dados_filtrados,
        "risco_fogo_medio",
        "qtd_risco_valido"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Município com mais focos",
        municipio_mais_focos
    )

    col2.metric(
        "Total de focos",
        formatar_inteiro(total_focos_municipios)
    )

    col3.metric(
        "Variação YoY",
        formatar_yoy(yoy_geral)
    )

    col4.metric(
        "Risco médio de fogo",
        formatar_decimal(risco_medio_municipios, 3)
    )

    st.divider()

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

   # Média mensal de focos no período filtrado
    media_mensal = focos_por_mes["total_focos"].mean()

    # Indicadores de sazonalidade
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Mês com mais focos",
        mes_critico["Nome_mes"]
    )

    col2.metric(
        "Focos no mês mais crítico",
        formatar_inteiro(mes_critico["total_focos"])
    )

    col3.metric(
        "Média mensal de focos",
        formatar_inteiro(media_mensal)
    )

    col4.metric(
        "Variação anual (YoY)",
        formatar_yoy(yoy_geral)
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