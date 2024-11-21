from flask import Flask, request, jsonify
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os

app = Flask(__name__, static_folder="static")

# Ruta para guardar temporalmente los gráficos generados
STATIC_DIR = os.path.join(app.static_folder, "graphs")
os.makedirs(STATIC_DIR, exist_ok=True)

# Función para procesar archivos y crear el grafo
def procesar_archivo(file):
    try:
        # Detectar el formato del archivo
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, delimiter='\t')  # Usamos '\t' para separar por tabulador
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            raise ValueError("Formato de archivo no compatible. Use CSV o Excel.")
        
        # Normalizar los nombres de las columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Verificar si las columnas necesarias están presentes
        columnas_requeridas = ['nodo 1', 'nodo 2', 'distancia (km)', 'grosor (cm)', 'costo (usd)']
        if all(col in df.columns for col in columnas_requeridas):
            G = crear_grafo(df)
        else:
            raise ValueError("El archivo no contiene las columnas requeridas.")
        
        # Algoritmo de Kruskal
        mst, peso_total = kruskal(G)
        
        # Generar gráficos
        pos = nx.spring_layout(G)
        grafo_path = generar_grafico(G, "grafo_completo.png", pos, titulo="Grafo Completo")
        mst_path = generar_grafico(G, "grafo_mst.png", pos, mst_edges=mst, titulo="Árbol de Expansión Mínima (MST)")
        
        grafo_url = f"/static/graphs/{os.path.basename(grafo_path)}"
        mst_url = f"/static/graphs/{os.path.basename(mst_path)}"
        return {"grafo": grafo_url, "mst": mst_url, "peso_total": peso_total}
    except Exception as e:
        return {"error": str(e)}

# Crear grafo
def crear_grafo(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        nodo1 = row['nodo 1']
        nodo2 = row['nodo 2']
        costo = row['costo (usd)']
        if nodo1 != nodo2:
            G.add_edge(nodo1, nodo2, weight=costo)
    return G

# Algoritmo de Kruskal
def kruskal(G):
    node_to_index = {node: idx for idx, node in enumerate(G.nodes())}
    edges = [(data['weight'], node_to_index[u], node_to_index[v], u, v) for u, v, data in G.edges(data=True)]
    edges.sort()
    uf = UnionFind(len(G.nodes()))
    mst = []
    peso_total = 0
    for weight, u_idx, v_idx, u, v in edges:
        if uf.union(u_idx, v_idx):
            mst.append((u, v))
            peso_total += weight
    return mst, peso_total

# Union-Find
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rootX = self.find(x)
        rootY = self.find(y)
        if rootX != rootY:
            if self.rank[rootX] < self.rank[rootY]:
                self.parent[rootX] = rootY
            elif self.rank[rootX] > self.rank[rootY]:
                self.parent[rootY] = rootX
            else:
                self.parent[rootY] = rootX
                self.rank[rootX] += 1
            return True
        return False

# Generar gráfico
def generar_grafico(G, filename, pos, mst_edges=None, titulo=""):
    plt.figure(figsize=(8, 8))
    if titulo == "Grafo Completo":
        nx.draw(G, pos, with_labels=True, node_size=500, edge_color="gold", node_color="blue", font_color="white")
    else:
        nx.draw_networkx(G, pos, with_labels=True, node_size=500, edge_color=(1, 1, 1, 0), node_color="red", font_color="white")
        nx.draw_networkx_edges(G, pos, edgelist=mst_edges, edge_color="gold", width=2)
    
    plt.axis("off")
    path = os.path.join(STATIC_DIR, filename)
    plt.savefig(path, bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close()
    return path

# Rutas Flask
@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se proporcionó un archivo"}), 400
    resultado = procesar_archivo(file)
    return jsonify(resultado)

if __name__ == "__main__":
    app.run(debug=True)
