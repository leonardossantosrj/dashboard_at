import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from mplsoccer import Pitch, VerticalPitch
from statsbombpy import sb

st.set_page_config(page_title="Análise de Partidas", layout="wide")

# ---------------------------------------------------------------------
# Carregamento dos dados
# ---------------------------------------------------------------------

@st.cache_data
def carregar_competicoes():
    return sb.competitions()
 
 
@st.cache_data
def carregar_partidas(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)
 
 
@st.cache_data
def carregar_eventos(match_id):
    return sb.events(match_id=match_id)

# ---------------------------------------------------------------------

def mapa_de_passes(passes, titulo):
    """Desenha as setas dos passes no campo."""
    # Na StatsBomb a posição vem como uma lista [x, y] dentro de uma coluna só
    # então tive que separaar em duas colunas para plot do grafico
    passes["x"] = passes["location"].apply(lambda p: p[0])
    passes["y"] = passes["location"].apply(lambda p: p[1])
    passes["x_fim"] = passes["pass_end_location"].apply(lambda p: p[0])
    passes["y_fim"] = passes["pass_end_location"].apply(lambda p: p[1])
 
    campo = Pitch(pitch_type="statsbomb", pitch_color="#f4f4f4", line_color="#333333")
    fig, ax = campo.draw(figsize=(10, 7))
 
    campo.arrows(passes["x"], passes["y"], passes["x_fim"], passes["y_fim"],
                 width=2, headwidth=4, color="#1f77b4", ax=ax, label="Passe certo")
 
    ax.legend(loc="upper left")
    ax.set_title(titulo)
    return fig

# ---------------------------------------------------------------------

def mapa_de_chutes(chutes, titulo):
    """Desenha os chutes no ataque"""
    chutes["x"] = chutes["location"].apply(lambda p: p[0])
    chutes["y"] = chutes["location"].apply(lambda p: p[1])
 
    # Usando na documentação, half=True mostra só o campo de ataque
    #  que é o que interesse onde os chutes rolam
    campo = VerticalPitch(pitch_type="statsbomb", half=True,
                          pitch_color="#f4f4f4", line_color="#333333")
    fig, ax = campo.draw(figsize=(9, 7))
 
    gols = chutes[chutes["shot_outcome"] == "Goal"]
    outros = chutes[chutes["shot_outcome"] != "Goal"]
 
    campo.scatter(outros["x"], outros["y"], s=outros["shot_statsbomb_xg"] * 700 + 60,
                  color="#999999", edgecolors="black", alpha=0.7, ax=ax, label="Chute")
    campo.scatter(gols["x"], gols["y"], s=gols["shot_statsbomb_xg"] * 700 + 60,
                  color="#d62728", edgecolors="black", ax=ax, label="Gol")
 
    ax.legend(loc="lower left")
    ax.set_title(titulo)
    return fig

# ---------------------------------------------------------------------

def mapa_de_calor(acoes, titulo):
    """Onde o jogador mais apareceu no jogo"""
    acoes = acoes.dropna(subset=["location"])
    acoes["x"] = acoes["location"].apply(lambda p: p[0])
    acoes["y"] = acoes["location"].apply(lambda p: p[1])
 
    campo = Pitch(pitch_type="statsbomb", pitch_color="#f4f4f4", line_color="#333333")
    fig, ax = campo.draw(figsize=(10, 7))
 
    campo.kdeplot(acoes["x"], acoes["y"], ax=ax, fill=True, levels=50,
                  cmap="Reds", alpha=0.7)
 
    ax.set_title(titulo)
    return fig

# ---------------------------------------------------------------------
 
def grafico_passadores(passes, quantidade):
    """Barras com os jogadores que mais acertaram passes"""
    ranking = passes["player"].value_counts().head(quantidade)
 
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(x=ranking.values, y=ranking.index, color="#1f77b4", ax=ax)
    ax.set_xlabel("Passes certos")
    ax.set_ylabel("")
    ax.set_title("Jogadores que mais acertaram passes")
    return fig
 
# --------------------------------------------------------------------- 
def grafico_passes_x_chutes(passes, chutes):
    """Quantidade de passes vs quantidade de chutes de cada jogador"""
    resumo = pd.DataFrame({
        "passes": passes["player"].value_counts(),
        "chutes": chutes["player"].value_counts(),
    }).fillna(0)
    resumo = resumo[resumo["chutes"] > 0]
 
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=resumo, x="passes", y="chutes", s=120, color="#d62728", ax=ax)
    ax.set_xlabel("Passes certos")
    ax.set_ylabel("Chutes")
    ax.set_title("Quem passa muito finaliza?")
    return fig

# ---------------------------------------------------------------------
# BARRA LATERAL 3.b
# ---------------------------------------------------------------------

st.sidebar.header("Filtros")
 
competicoes = carregar_competicoes()
campeonato = st.sidebar.selectbox("Campeonato",
                                  sorted(competicoes["competition_name"].unique()))
 
temporadas = competicoes[competicoes["competition_name"] == campeonato]
temporada = st.sidebar.selectbox("Temporada", sorted(temporadas["season_name"].unique()))
 
linha = temporadas[temporadas["season_name"] == temporada].iloc[0]
partidas = carregar_partidas(int(linha["competition_id"]), int(linha["season_id"]))
 
# Textinho pro usuário ler
partidas["rotulo"] = (partidas["home_team"] + " " + partidas["home_score"].astype(str)
                      + " x " + partidas["away_score"].astype(str) + " "
                      + partidas["away_team"])
 
rotulo = st.sidebar.selectbox("Partida", sorted(partidas["rotulo"]))
partida = partidas[partidas["rotulo"] == rotulo].iloc[0]
 
barra = st.sidebar.progress(0, text="Carregando eventos...")
eventos = carregar_eventos(int(partida["match_id"]))
barra.progress(100, text="Pronto!")
 
# Usei o key aqui para guardar a escolha, achei melhor usar isso para melhor utilização da página 
# isso faz com que o jogador selecionado permanece selecionado quando o usuário troca de aba.
jogadores = ["Todos"] + sorted(eventos["player"].dropna().unique())
jogador = st.sidebar.selectbox("Jogador", jogadores, key="jogador_escolhido")
 

# Aqui reparei numa pegadinha da StatsBomb, só há preenchimento quando o pass_outcome quando o passe DÁ ERRADO,
# então passe certo é aquele em que essa coluna está vazia.
# Assim, fiz a separação dos passes, passes_certos e chutes.
passes = eventos[eventos["type"] == "Pass"]
passes_certos = passes[passes["pass_outcome"].isna()]
chutes = eventos[eventos["type"] == "Shot"]

# ---------------------------------------------------------------------
# PÁGINA
# ---------------------------------------------------------------------

st.title("Como um time cria e finaliza suas chances?")
st.caption(f"{campeonato} - {temporada}  |  {rotulo}")
 
aba1, aba2, aba3 = st.tabs(["Visão geral", "Mapas de campo", "Jogadores"])
 
 
# --- ABA 1 ---
with aba1:
    st.subheader("Números da partida")
 
    gols = len(chutes[chutes["shot_outcome"] == "Goal"])
    taxa = gols / len(chutes) * 100
 
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gols", gols)
    col2.metric("Chutes", len(chutes))
    col3.metric("Passes certos", len(passes_certos))
    col4.metric("Conversão em gol", f"{taxa:.1f}%")
 
    st.subheader("Eventos da partida")
 
    # Formulário: os filtros só valem quando o usuário clica no botão.
    with st.form("filtros"):
        tipos = st.multiselect("Tipos de evento", sorted(eventos["type"].unique()),
                               default=["Pass", "Shot"])
        quantidade = st.number_input("Quantas linhas mostrar", 5, 500, 50, step=5)
        intervalo = st.slider("Minutos da partida", 0, 125, (0, 125))
        st.form_submit_button("Aplicar filtros")
 
    filtrados = eventos[eventos["type"].isin(tipos)]
    filtrados = filtrados[filtrados["minute"].between(intervalo[0], intervalo[1])]
 
    if jogador != "Todos":
        filtrados = filtrados[filtrados["player"] == jogador]
 
    tabela = filtrados[["minute", "type", "team", "player", "position"]]
    st.dataframe(tabela.head(quantidade), use_container_width=True)
 
    st.download_button("Baixar eventos em CSV",
                       data=tabela.to_csv(index=False).encode("utf-8"),
                       file_name="eventos.csv",
                       mime="text/csv")
 
 
# --- ABA 2 ---
with aba2:
    time = st.radio("Time", [partida["home_team"], partida["away_team"]],
                    horizontal=True)
 
    passes_time = passes_certos[passes_certos["team"] == time]
    chutes_time = chutes[chutes["team"] == time]
 
    if jogador != "Todos":
        passes_time = passes_time[passes_time["player"] == jogador]
        chutes_time = chutes_time[chutes_time["player"] == jogador]
 
    col_esq, col_dir = st.columns(2)
 
    with col_esq:
        st.subheader("Mapa de passes")
        with st.spinner("Desenhando o campo..."):
            st.pyplot(mapa_de_passes(passes_time, f"Passes certos - {time}"))
 
    with col_dir:
        st.subheader("Mapa de chutes")
        # Sem esse if a página quebra quando o jogador escolhido não chutou.
        if len(chutes_time) == 0:
            st.info("Esse jogador não finalizou na partida.")
        else:
            with st.spinner("Desenhando o campo..."):
                st.pyplot(mapa_de_chutes(chutes_time, f"Chutes - {time}"))
 
    st.subheader("Mapa de calor")
    if jogador == "Todos":
        st.info("Escolha um jogador na barra lateral para ver o mapa de calor.")
    else:
        acoes = eventos[eventos["player"] == jogador]
        st.pyplot(mapa_de_calor(acoes, f"Ações de {jogador}"))
 
 
# --- ABA 3 ---
with aba3:
    quantos = st.slider("Quantos jogadores no ranking", 5, 20, 10)
    st.pyplot(grafico_passadores(passes_certos, quantos))
 
    st.subheader("Passes x chutes")
    st.pyplot(grafico_passes_x_chutes(passes_certos, chutes))
 
    st.subheader("Comparar dois jogadores")
 
    nomes = sorted(eventos["player"].dropna().unique())
    col1, col2 = st.columns(2)
    jogador_a = col1.selectbox("Jogador A", nomes, index=0)
    jogador_b = col2.selectbox("Jogador B", nomes, index=1)
 
    comparacao = pd.DataFrame({
        jogador_a: {
            "Passes certos": len(passes_certos[passes_certos["player"] == jogador_a]),
            "Chutes": len(chutes[chutes["player"] == jogador_a]),
        },
        jogador_b: {
            "Passes certos": len(passes_certos[passes_certos["player"] == jogador_b]),
            "Chutes": len(chutes[chutes["player"] == jogador_b]),
        },
    })
 
    st.dataframe(comparacao, use_container_width=True)
    st.bar_chart(comparacao)