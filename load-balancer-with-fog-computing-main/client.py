# client.py
from flask import Flask, request, jsonify, render_template_string
import requests, os, time, random
from threading import Thread, Lock

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CHUNK_SIZE = 5 * 1024 * 1024  # 5 Mo par chunk
MAX_THREADS = 5

FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

lock = Lock()
results = []
metrics = []

# HTML Interface
UPLOAD_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Fog Load Balancer</title>
<style>
body { font-family: Arial; background: #f0f2f5; margin:0; padding:20px; }
h2 { text-align:center; }
.upload-section { display:flex; justify-content:center; gap:10px; margin-bottom:20px; }
input[type=file] { padding:5px; border-radius:5px; border:1px solid #ccc; }
button { background:#4CAF50; color:white; padding:8px 16px; border:none; border-radius:5px; cursor:pointer; }
button:hover { background:#45a049; }
table { width:80%; margin:auto; border-collapse:collapse; background:white; box-shadow:0 2px 5px rgba(0,0,0,0.1); }
th,td { padding:10px; text-align:center; border-bottom:1px solid #ddd; }
th { background:#4CAF50; color:white; }
tr:hover { background:#f1f1f1; }
#results-message { text-align:center; margin-bottom:10px; color:#555; }
</style>
</head>
<body>
<h2>Chiffrement distribué via Fog Nodes</h2>
<div class="upload-section">
<input type="file" id="fileInput">
<button onclick="uploadFile()">Chiffrer</button>
<button onclick="getMetrics()">Voir CPU/RAM</button>
</div>

<div id="results-message"></div>

<h3>Chunks</h3>
<table>
<thead>
<tr><th>Chunk</th><th>Nœud utilisé</th><th>Temps de traitement (s)</th><th>Temps total côté LB (s)</th></tr>
</thead>
<tbody id="results"></tbody>
</table>

<h3>Metrics des nœuds</h3>
<table>
<thead>
<tr><th>Nœud</th><th>CPU %</th><th>RAM %</th><th>Tasks en cours</th></tr>
</thead>
<tbody id="metrics"></tbody>
</table>

<script>
async function uploadFile() {
    const file = document.getElementById("fileInput").files[0];
    if(!file) { alert("Choisissez un fichier !"); return; }
    const formData = new FormData();
    formData.append("file", file);
    document.getElementById("results-message").innerText = "Chargement et chiffrement en cours...";
    try {
        const res = await fetch("/process_file", { method:"POST", body:formData });
        const data = await res.json();
        const tbody = document.getElementById("results");
        tbody.innerHTML = "";
        if(data.error){ document.getElementById("results-message").innerText="Erreur : "+data.error; return; }
        document.getElementById("results-message").innerText=`${data.results.length} chunks traités`;
        data.results.forEach(r=>{
            const tr=document.createElement("tr");
            tr.innerHTML=`
                <td>${r.chunk}</td>
                <td>${r.node_used}</td>
                <td>${r.processing_time.toFixed(4)}</td>
                <td>${r.total_time.toFixed(4)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(err){ document.getElementById("results-message").innerText="Erreur : "+err; }
}

async function getMetrics() {
    try {
        const res = await fetch("/metrics");
        const data = await res.json();
        const tbody = document.getElementById("metrics");
        tbody.innerHTML = "";
        data.forEach(node=>{
            const tr=document.createElement("tr");
            if(node.error){
                tr.innerHTML=`<td>${node.node}</td><td colspan="3">Node unreachable</td>`;
            } else {
                tr.innerHTML=`<td>${node.port}</td><td>${node.cpu_percent}</td><td>${node.ram_percent}</td><td>${node.tasks_running}</td>`;
            }
            tbody.appendChild(tr);
        });
    } catch(err){ alert("Erreur: "+err); }
}
</script>
</body>
</html>
"""

# Choix aléatoire d'un node
def select_node():
    return random.choice(FOG_NODES)

# Envoyer un chunk
def send_chunk(index, chunk):
    global results
    node = select_node()
    start = time.time()
    try:
        resp = requests.post(f"{node}/task", data=chunk, timeout=30)
        resp.raise_for_status()
        node_data = resp.json()
    except:
        node_data = {"node_used": node, "processing_time":0}
    total = time.time()-start
    with lock:
        results.append({
            "chunk": index,
            "node_used": node_data.get("node_used", node),
            "processing_time": node_data.get("processing_time",0),
            "total_time": total
        })

@app.route("/")
def index():
    return render_template_string(UPLOAD_PAGE)

@app.route("/process_file", methods=["POST"])
def process_file():
    global results
    results=[]
    if "file" not in request.files:
        return jsonify({"error":"Aucun fichier reçu"}),400
    file=request.files["file"]
    filepath=os.path.join(UPLOAD_FOLDER,file.filename)
    file.save(filepath)
    chunks=[]
    with open(filepath,"rb") as f:
        while True:
            c=f.read(CHUNK_SIZE)
            if not c: break
            chunks.append(c)
    threads=[]
    for idx,c in enumerate(chunks):
        while len([t for t in threads if t.is_alive()])>=MAX_THREADS: time.sleep(0.05)
        t=Thread(target=send_chunk,args=(idx,c))
        t.start()
        threads.append(t)
    for t in threads: t.join()
    return jsonify({"results":results})

# Endpoint pour récupérer CPU/RAM des nodes
@app.route("/metrics", methods=["GET"])
def get_metrics():
    nodes_metrics=[]
    for node in FOG_NODES:
        try:
            r=requests.get(node+"/health",timeout=2)
            r.raise_for_status()
            nodes_metrics.append(r.json())
        except:
            nodes_metrics.append({"node":node,"error":"unreachable"})
    return jsonify(nodes_metrics)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5005,debug=True)
