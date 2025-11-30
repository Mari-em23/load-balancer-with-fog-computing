# app_upload_client_correct.py
from flask import Flask, request, jsonify, send_from_directory, render_template_string
import requests, os, time, random
from threading import Thread, Lock

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CHUNK_SIZE = 5 * 1024 * 1024  
MAX_THREADS = 5

# Liste des fog nodes
FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

lock = Lock()
results = []

# Interface HTML simple
UPLOAD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Fog Load Balancer</title>
</head>
<body>
    <h2>Chiffrement distribué via Fog Nodes</h2>
    <input type="file" id="fileInput">
    <button onclick="uploadFile()">Chiffrer</button>

    <h3>Résultats</h3>
    <table border="1">
        <thead>
            <tr>
                <th>Chunk</th>
                <th>Nœud utilisé</th>
                <th>Temps de traitement (s)</th>
                <th>Temps total côté LB (s)</th>
            </tr>
        </thead>
        <tbody id="results"></tbody>
    </table>

<script>
function uploadFile() {
    const file = document.getElementById("fileInput").files[0];
    if (!file) { alert("Choisissez un fichier !"); return; }

    const formData = new FormData();
    formData.append("file", file);

    fetch("/process_file", { method: "POST", body: formData })
    .then(r => r.json())
    .then(data => {
        const tbody = document.getElementById("results");
        tbody.innerHTML = "";
        data.results.forEach(r => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${r.chunk}</td>
                <td>${r.node_used}</td>
                <td>${r.processing_time.toFixed(4)}</td>
                <td>${r.total_time.toFixed(4)}</td>
            `;
            tbody.appendChild(tr);
        });
    })
    .catch(err => alert("Erreur : " + err));
}
</script>
</body>
</html>
"""

# Fonction pour choisir aléatoirement un node
def select_node():
    return random.choice(FOG_NODES)

# Fonction pour envoyer un chunk à un node
def send_chunk(index, chunk):
    global results
    node = select_node()
    start_time = time.time()
    try:
        resp = requests.post(f"{node}/task", data=chunk, timeout=30)
        resp.raise_for_status()
        node_data = resp.json()
    except Exception as e:
        node_data = {"error": str(e), "node_used": node}

    total_time = time.time() - start_time

    with lock:
        results.append({
            "chunk": index,
            "node_used": node_data.get("node_used", node),
            "processing_time": node_data.get("processing_time", 0),
            "total_time": total_time,
            "error": node_data.get("error", None)
        })

# Route pour l'interface web
@app.route("/")
def index():
    return render_template_string(UPLOAD_PAGE)

# Route pour traiter le fichier uploadé
@app.route("/process_file", methods=["POST"])
def process_file():
    global results
    results = []

    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Découpage en chunks
    chunks = []
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)

    threads = []
    for idx, chunk in enumerate(chunks):
        while len([t for t in threads if t.is_alive()]) >= MAX_THREADS:
            time.sleep(0.05)
        t = Thread(target=send_chunk, args=(idx, chunk))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return jsonify({"message": f"{len(chunks)} chunks traités", "results": results})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
