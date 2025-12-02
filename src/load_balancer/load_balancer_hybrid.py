# load_balancer_aes_optimized.py
from flask import Flask, request, jsonify
import requests, time
from threading import Lock

app = Flask(__name__)

FOG_NODES = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003",
]

node_kpi = {node: None for node in FOG_NODES}  # moyenne exp. du temps de traitement
node_counts = {node: 0 for node in FOG_NODES}
local_tasks = {node: 0 for node in FOG_NODES}  # tâches locales en cours
ALPHA = 0.3
LOCK = Lock()

# --- Sélection du nœud ---
def select_node(chunk_size):
    untested = [n for n in FOG_NODES if node_kpi[n] is None]
    if untested:
        return untested[0]

    node_scores = {}
    with LOCK:
        for node in FOG_NODES:
            # Récupérer état du nœud
            try:
                r = requests.get(f"{node}/health", timeout=2)
                resp = r.json()
                cpu = resp.get("cpu_percent", 0)
                ram = resp.get("ram_percent", 0)
            except:
                cpu = 100
                ram = 100

            # Score = KPI * (1 + tâches locales) * (1 + CPU/100) * (1 + RAM/100) * (chunk_size en Mo / 50)
            # Pondération chunk_size pour des chunks plus gros
            size_factor = chunk_size / (1024*1024*50)  # normalisé sur 50 Mo
            node_scores[node] = node_kpi[node] * (1 + local_tasks[node]) * (1 + cpu/100) * (1 + ram/100) * size_factor

    best_node = min(node_scores, key=lambda n: node_scores[n])
    return best_node

# --- Endpoint pour envoyer un chunk ---
@app.route("/send_task", methods=["POST"])
def send_task():
    chunk = request.data
    chunk_size = len(chunk)
    tried_nodes = []

    while len(tried_nodes) < len(FOG_NODES):
        node = select_node(chunk_size)
        if node in tried_nodes:
            remaining = [n for n in FOG_NODES if n not in tried_nodes]
            node = remaining[0]

        start_time = time.time()
        with LOCK:
            local_tasks[node] += 1

        try:
            resp = requests.post(f"{node}/task", data=chunk, timeout=30)
            node_resp = resp.json()
        except Exception as e:
            with LOCK:
                local_tasks[node] -= 1
            tried_nodes.append(node)
            continue

        elapsed = time.time() - start_time

        with LOCK:
            if node_kpi[node] is None:
                node_kpi[node] = elapsed
            else:
                node_kpi[node] = ALPHA * elapsed + (1 - ALPHA) * node_kpi[node]
            node_counts[node] += 1
            local_tasks[node] -= 1

        return jsonify({
            "node_used": node,
            "result": node_resp.get('result'),
            "processing_time": node_resp.get('processing_time', 0),
            "total_time": elapsed
        })

    return jsonify({"error": "All nodes failed"}), 500

# --- Endpoint pour vérifier l'état des nœuds ---
@app.route("/nodes_status", methods=["GET"])
def nodes_status():
    statuses = {}
    for node in FOG_NODES:
        try:
            r = requests.get(f"{node}/health", timeout=2)
            resp = r.json()
            statuses[node] = {
                "status": "online",
                "cpu_percent": resp.get('cpu_percent', None),
                "ram_percent": resp.get('ram_percent', None),
                "tasks_running": resp.get('tasks_running', None)
            }
        except:
            statuses[node] = {"status": "offline"}
    return jsonify(statuses)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
