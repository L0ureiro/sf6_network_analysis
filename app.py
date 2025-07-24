import streamlit as st
import networkx as nx
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Análise de Rede de Torneio",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("Análise de Rede de Torneio de E-Sports")
st.write(
    "Esta aplicação interativa explora a estrutura de um torneio, revelando os jogadores mais importantes "
    "e as comunidades de competidores com base em dados de partidas reais."
)

# --- 2. CARREGAMENTO E PROCESSAMENTO DOS DADOS ---
# Usar @st.cache_data garante que esta função complexa só rode uma vez.
@st.cache_data
def carregar_e_processar_dados():
    """
    Carrega os grafos pré-processados e calcula o DataFrame de centralidade.
    """
    try:
        # Carrega o grafo completo para as análises numéricas
        g_completo = nx.read_graphml("rede_completa.graphml")
        
        # Carrega o subgrafo menor para a visualização interativa
        g_visualizacao = nx.read_graphml("rede_visualizacao.graphml")
        
    except FileNotFoundError:
        st.error(
            "Arquivos .graphml não encontrados! Certifique-se de que 'rede_completa.graphml' e "
            "'rede_visualizacao.graphml' estão na mesma pasta do seu app.py."
        )
        return None, None, None

    # Calcula as centralidades usando o grafo completo para garantir a precisão
    g_undir_simples = nx.Graph(g_completo)
    centrality_df = pd.DataFrame({
        'Jogador': list(g_undir_simples.nodes()),
        'Degree': list(nx.degree_centrality(g_undir_simples).values()),
        'Closeness': list(nx.closeness_centrality(g_undir_simples).values()),
        'Betweenness': list(nx.betweenness_centrality(g_undir_simples, weight='weight', normalized=True).values()),
        'Eigenvector': list(nx.eigenvector_centrality_numpy(g_undir_simples, weight='weight').values())
    })

    return g_completo, g_visualizacao, centrality_df

# Carrega os dados na primeira execução
G_completo, G_visualizacao, centrality_df = carregar_e_processar_dados()

# --- 3. SIDEBAR DE OPÇÕES ---
st.sidebar.title("Opções de Análise")
k_slider = st.sidebar.slider(
    "Selecione o número de jogadores (Top-K) para os rankings:", 
    min_value=5, max_value=20, value=10
)

# --- 4. CORPO PRINCIPAL COM ABAS ---
if G_completo and G_visualizacao and centrality_df is not None:
    tab_metricas, tab_centralidade, tab_rede = st.tabs([
        "📊 Métricas Gerais", 
        "🏆 Rankings de Centralidade", 
        "🕸️ Rede Interativa"
    ])

    with tab_metricas:
        st.header("Métricas Estruturais da Rede Completa")
        g_undir_simples = nx.Graph(G_completo)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Jogadores (Nós)", G_completo.number_of_nodes())
        col2.metric("Total de Partidas (Arestas)", G_completo.number_of_edges())
        col3.metric("Densidade da Rede", f"{nx.density(G_completo):.4f}")

        col4, col5, col6 = st.columns(3)
        col4.metric("Coef. de Clustering Global", f"{nx.average_clustering(g_undir_simples):.4f}")
        col5.metric("Assortatividade de Grau", f"{nx.degree_assortativity_coefficient(g_undir_simples):.4f}")
        col6.metric("Diâmetro da Rede", f"{nx.diameter(g_undir_simples)}")

        st.subheader("Análise de Conectividade")
        col7, col8 = st.columns(2)
        col7.metric("Componentes Fracamente Conectados", nx.number_weakly_connected_components(G_completo))
        col8.metric("Componentes Fortemente Conectados", nx.number_strongly_connected_components(G_completo))
        
        st.info(
            "**Como interpretar:** A rede possui uma baixa densidade (esparsa) e é altamente assortativa, "
            "indicando que jogadores com muitas partidas tendem a se enfrentar. "
            "A existência de muitos componentes fortemente conectados revela a complexa estrutura de vitórias e derrotas do torneio."
        )

    with tab_centralidade:
        st.header(f"Top-{k_slider} Jogadores por Métrica de Centralidade")
        st.markdown(
            "Aqui você pode ver quais jogadores foram mais 'importantes' na estrutura do torneio, "
            "de acordo com diferentes definições de centralidade. Todos os cálculos são baseados na rede completa."
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Por Grau (Mais Ativos)")
            st.dataframe(centrality_df[['Jogador', 'Degree']].nlargest(k_slider, "Degree").set_index("Jogador"))
            
            st.subheader("Por Betweenness (Melhores 'Pontes')")
            st.dataframe(centrality_df[['Jogador', 'Betweenness']].nlargest(k_slider, "Betweenness").set_index("Jogador"))

        with col_b:
            st.subheader("Por Eigenvector (Mais Influentes)")
            st.dataframe(centrality_df[['Jogador', 'Eigenvector']].nlargest(k_slider, "Eigenvector").set_index("Jogador"))
            
            st.subheader("Por Closeness (Mais 'Centrais')")
            st.dataframe(centrality_df[['Jogador', 'Closeness']].nlargest(k_slider, "Closeness").set_index("Jogador"))

    with tab_rede:
        st.header("Visualização Interativa do Núcleo da Rede")
        st.markdown(
            "Para garantir a performance, esta visualização mostra os **200 jogadores mais ativos**. "
            "Use o mouse para explorar a rede. O **tamanho** de cada jogador representa sua influência (Eigenvector) "
            "e a **cor** representa sua comunidade (calculada com base na rede completa)."
        )
        
        physics_enabled = st.sidebar.checkbox("Habilitar física interativa", value=True)

        # Gerar o grafo Pyvis a partir do subgrafo de visualização
        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
        net.toggle_physics(physics_enabled)
        
        # Dicionários de dados vêm do grafo COMPLETO para precisão
        eigenvector_scores = pd.Series(centrality_df.Eigenvector.values, index=centrality_df.Jogador).to_dict()
        max_eigenvector = max(eigenvector_scores.values()) if eigenvector_scores else 1.0
        palette = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6"]

        for node in G_visualizacao.nodes():
            # Os atributos (comunidade, scores) são buscados do grafo completo
            community_id = G_completo.nodes[node].get('community', 0)
            eigenvector = eigenvector_scores.get(node, 0)
            
            color = palette[community_id % len(palette)]
            size = 10 + (eigenvector / max_eigenvector) * 40
            
            info_hover = (f"<b>{node}</b><br>"
                          f"Comunidade: {community_id}<br>"
                          f"Influência (Eigenvector): {eigenvector:.4f}")
            
            net.add_node(node, label=node, title=info_hover, color=color, size=size)

        for source, target in G_visualizacao.edges():
            net.add_edge(source, target)

        # Gerar e exibir o HTML
        try:
            file_name = "rede_interativa_streamlit.html"
            net.save_graph(file_name)
            with open(file_name, 'r', encoding='utf-8') as f:
                source_code = f.read()
            components.html(source_code, height=800)
        except Exception as e:
            st.error(f"Ocorreu um erro ao gerar o grafo interativo: {e}")

else:
    st.warning("O grafo não pôde ser carregado. Verifique os arquivos .graphml.")
