import streamlit as st
from pymongo import MongoClient
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase

# Configuración de conexión a MongoDB
MONGO_URI = "mongodb+srv://sebastian_us:4254787Jus@cluster0.ecyx6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "transcripciones"
COLLECTION_NAME = "transcripciones"

# Configuración de conexión a Neo4j
URI_NEO = "neo4j+s://08d5f7d0.databases.neo4j.io"
AUTH = ("neo4j", "IuWbeyZ2oHy3QCL7mPk4QU32dxzfy4O6yRCnfbydym8")


# Función para obtener conexión a MongoDB
def get_mongo_connection(uri, database_name, collection_name):
    client = MongoClient(uri)
    db = client[database_name]
    return db[collection_name]


# Función para obtener valores únicos
def get_unique_values(collection, field):
    return sorted(collection.distinct(field))


# Función para obtener datos desde MongoDB
def query_mongo(collection, query):
    return list(collection.find(query))


# Convertir resultados a DataFrame
def results_to_dataframe(results):
    if results:
        df = pd.DataFrame(results)
        df.drop(columns=["_id"], inplace=True, errors="ignore")
        return df
    return pd.DataFrame(columns=["No hay resultados"])


# Función para graficar grafo
from pyvis.network import Network
import streamlit as st

def obtener_providencias(driver):
    # Consulta para obtener todas las providencias
    query = "MATCH (p:Providencia) RETURN p.id AS id"
    with driver.session() as session:
        result = session.run(query)
        return [record["id"] for record in result]

def graficar_grafo_streamlit(driver, providencia, rango_min, rango_max):
    from pyvis.network import Network
    import streamlit.components.v1 as components

    # Consulta para obtener relaciones con la providencia seleccionada
    query = """
    MATCH (a:Providencia {id: $providencia})-[r:SIMILAR]->(b:Providencia)
    WHERE r.similitud >= $rango_min AND r.similitud <= $rango_max
    RETURN a.id AS origen, b.id AS destino, r.similitud AS similitud
    """
    
    # Crear el grafo en Pyvis
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    
    with driver.session() as session:
        result = session.run(query, providencia=providencia, rango_min=rango_min, rango_max=rango_max)
        relaciones = list(result)
        
        if relaciones:
            # Agregar nodos y relaciones al grafo si hay conexiones
            for record in relaciones:
                origen = record["origen"]
                destino = record["destino"]
                similitud = record["similitud"]
                
                net.add_node(origen, label=origen, title=f"Providencia: {origen}")
                net.add_node(destino, label=destino, title=f"Providencia: {destino}")
                net.add_edge(origen, destino, value=similitud, title=f"Similitud: {similitud}")
        else:
            # Si no hay conexiones, graficar solo la providencia seleccionada
            net.add_node(providencia, label=providencia, title=f"Providencia: {providencia}")
    
    # Configurar opciones del grafo
    net.set_options("""
    var options = {
      "physics": {
        "enabled": true,
        "stabilization": {
          "enabled": true
        }
      }
    }
    """)

    # Guardar y mostrar el grafo en Streamlit
    net.save_graph("grafo.html")
    components.html(open("grafo.html", "r").read(), height=600)



# Configuración de página en Streamlit
st.sidebar.title("Navegación")
page = st.sidebar.radio("Selecciona una página:", ["Resultados de los Filtros", "Filtrar por Similitudes"])

if page == "Resultados de los Filtros":
    # Conexión a MongoDB
    collection = get_mongo_connection(MONGO_URI, DATABASE_NAME, COLLECTION_NAME)

    # Título y descripción del sistema de consulta
    st.title("Sistema de Consulta de Providencias")
    st.markdown("""
    Bienvenido al sistema de consulta de providencias judiciales. 
    Aquí puedes filtrar y buscar por diferentes criterios, como:
    - **Nombre de la providencia**.
    - **Tipo de providencia**.
    - **Año de emisión**.
    - **Texto en el contenido de la providencia**.
    """)
    st.sidebar.subheader("Filtros")

    providencias = get_unique_values(collection, "providencia")
    selected_providencia = st.sidebar.selectbox("Providencia", [""] + providencias)

    tipos = get_unique_values(collection, "tipo")
    selected_tipo = st.sidebar.selectbox("Tipo", [""] + tipos)

    anios = get_unique_values(collection, "anio")
    selected_anio = st.sidebar.selectbox("Año", [""] + anios)

    texto_clave = st.sidebar.text_input("Texto")

    # Mostrar resultados
    if selected_providencia:
        results = query_mongo(collection, {"providencia": selected_providencia})
        st.dataframe(results_to_dataframe(results))
    elif selected_tipo:
        results = query_mongo(collection, {"tipo": selected_tipo})
        st.dataframe(results_to_dataframe(results))
    elif selected_anio:
        results = query_mongo(collection, {"anio": selected_anio})
        st.dataframe(results_to_dataframe(results))
    elif texto_clave:
        results = query_mongo(collection, {"$text": {"$search": texto_clave}})
        st.dataframe(results_to_dataframe(results))

elif page == "Filtrar por Similitudes":
    st.title("Visualización de Grafos de Providencias")
    st.markdown("""
    Aquí se podrá visualizar un grafo de las providencias que están relacionadas con
    otras. Para eso se debe indicar la providencia y un valor mínimo y máximo de 
    similitud de esa providencia con respecto a las otras y se podrá visualizar.
    """)

    # Obtener la lista de providencias desde Neo4j
    with GraphDatabase.driver(URI_NEO, auth=AUTH) as driver:
        # Obtener todas las providencias
        providencias = obtener_providencias(driver)

    # Seleccionar la providencia
    selected_providencia = st.sidebar.selectbox("Seleccione una providencia:", [""] + providencias)

    # Seleccionar el rango de similitudes
    st.sidebar.subheader("Filtro de similitudes")
    rango_min = st.sidebar.slider("Similitud mínima", 0.0, 100.0, 0.0, step=0.01)
    rango_max = st.sidebar.slider("Similitud máxima", 0.0, 100.0, 100.0, step=0.01)

    # Botón para generar el grafo
    if st.sidebar.button("Generar Grafo"):
        if selected_providencia:
            with GraphDatabase.driver(URI_NEO, auth=AUTH) as driver:
                graficar_grafo_streamlit(driver, selected_providencia, rango_min, rango_max)
        else:
            st.error("Seleccione una providencia.")
