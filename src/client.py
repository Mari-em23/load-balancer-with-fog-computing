from flask import Flask, request, jsonify, render_template_string, send_from_directory
import requests, os, shutil

app = Flask(__name__)

UPLOAD_FOLDER = "uploads_client"
ENCRYPTED_FOLDER = "encrypted"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Map lbType to Load Balancer URLs
LB_URLS = {
    "random": "http://127.0.0.1:5005",
    "algo": "http://127.0.0.1:5006",
    "round_robin": "http://127.0.0.1:5007"
}

CHUNK_SIZE = 5 * 1024 * 1024

UPLOAD_PAGE = """ 
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Fog Load Balancer</title>
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin:0; padding:20px; color:#333;}
h2 { text-align:center; color:#4335af; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);}
.upload-section { display:flex; justify-content:center; gap:10px; margin-bottom:20px; }
input[type=file], select { padding:8px; border-radius:8px; border:1px solid #ccc; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);}
button { 
    background: linear-gradient(135deg,#4335af,#6c5dd3); 
    color:white; padding:10px 20px; border:none; border-radius:10px; cursor:pointer; 
    font-weight:bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
}
button:hover { 
    background: linear-gradient(135deg,#6c5dd3,#4335af); transform: translateY(-2px); 
    box-shadow: 0 6px 8px rgba(0,0,0,0.15);
}
table { width:80%; margin:auto; border-collapse:collapse; background:white; 
        box-shadow:0 4px 10px rgba(0,0,0,0.1); border-radius:10px; overflow:hidden;}
th,td { padding:12px; text-align:center; border-bottom:1px solid #ddd; }
th { background: linear-gradient(135deg,#4335af,#6c5dd3); color:white; }
tr:hover { background:#f1f1f1; }
#results-message { text-align:center; margin-bottom:10px; color:#555; font-weight:bold;}
.bar { height:20px; border-radius:10px; text-align:right; padding-right:5px; color:white; font-weight:bold;
       background: linear-gradient(90deg,#4335af,#6c5dd3);}
</style>
</head>
<body>
<h2>Chiffrement distribué via Fog Nodes</h2>
<div class="upload-section">
<input type="file" id="fileInput">
<select id="lbType">
    <option value="random">Random</option>
    <option value="round_robin">Round Robin</option>
    <option value="algo">Algo</option>
</select>
<button onclick="uploadFile()">Chiffrer</button>
<button onclick="getMetrics()">Voir Metrics</button>
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

<div style="text-align:center; margin-top:20px;">
    <a id="downloadLink" href="#" download style="display:none;">
        <button style="background: linear-gradient(135deg,#43afc0,#6cd3d0); color:white; padding:10px 20px; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">
            Télécharger le fichier chiffré
        </button>
    </a>
</div>

<script>
async function uploadFile() {
    const file = document.getElementById("fileInput").files[0];
    if(!file){ alert("Choisissez un fichier !"); return; }

    const lbType = document.getElementById("lbType").value;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("lb_type", lbType);

    document.getElementById("results-message").innerText = "Chargement et chiffrement en cours...";

    try {
        const res = await fetch("/send_file", { method:"POST", body:formData });
        const data = await res.json();

        if(data.error){
            document.getElementById("results-message").innerText="Erreur : "+data.error;
            return;
        }

        const tbody = document.getElementById("results");
        tbody.innerHTML = "";

        const results = data.results || [];
        document.getElementById("results-message").innerText=`${results.length} chunks traités`;

        results.forEach(r=>{
            const tr = document.createElement("tr");

            const processingTime = (r.processing_time != null) ? r.processing_time.toFixed(4) : "N/A";
            const totalTime = (r.total_time != null) ? r.total_time.toFixed(4) : "N/A";
            const nodeUsed = r.node_used || "Unknown";
            const chunkIndex = r.chunk != null ? r.chunk : "N/A";

            tr.innerHTML=`
                <td>${chunkIndex}</td>
                <td>${nodeUsed}</td>
                <td>${processingTime}</td>
                <td>${totalTime}</td>
            `;
            tbody.appendChild(tr);
        });

        // Show download button
        if (data.encrypted_file_url) {
            const downloadLink = document.getElementById("downloadLink");
            downloadLink.href = data.encrypted_file_url;
            downloadLink.style.display = "inline-block";
        }

    } catch(err){
        document.getElementById("results-message").innerText="Erreur : "+err;
    }
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
                const cpu_color = node.cpu_percent>80?'#ff4d4f':'#4335af';
                const ram_color = node.ram_percent>80?'#ff4d4f':'#4335af';
                const cpu_bar = `<div class="bar" style="width:${node.cpu_percent}%;background: linear-gradient(50deg,${cpu_color},#6c5dd3)">${node.cpu_percent}%</div>`;
                const ram_bar = `<div class="bar" style="width:${node.ram_percent}%;background: linear-gradient(50deg,${ram_color},#6c5dd3)">${node.ram_percent}%</div>`;
                
                tr.innerHTML=`
                    <td>${node.port}</td>
                    <td>${cpu_bar}</td>
                    <td>${ram_bar}</td>
                    <td>${node.tasks_running}</td>
                `;
            }
            tbody.appendChild(tr);
        });
    } catch(err){
        alert("Erreur: "+err);
    }
}

setInterval(getMetrics, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(UPLOAD_PAGE)

@app.route("/send_file", methods=["POST"])
def send_file():
    if "file" not in request.files:
        return jsonify({"error":"Aucun fichier reçu"}),400
    
    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    file_size = os.path.getsize(filepath)
    num_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

    lb_type = request.form.get("lb_type", "random")
    lb_url = LB_URLS.get(lb_type, LB_URLS["random"])

    resp_data = {}
    try:
        with open(filepath, "rb") as f:
            files = {"file": (file.filename, f)}
            data = {"num_chunks": num_chunks, "lb_type": lb_type}
            resp = requests.post(f"{lb_url}/process_file", files=files, data=data)
            resp.raise_for_status()
            resp_data = resp.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

    # Save encrypted file (for demo, just copy original)
    encrypted_file_path = os.path.join(ENCRYPTED_FOLDER, file.filename + ".enc")
    shutil.copy(filepath, encrypted_file_path)
    resp_data["encrypted_file_url"] = f"/download/{file.filename}.enc"

    return jsonify(resp_data)


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(ENCRYPTED_FOLDER, filename, as_attachment=True)


@app.route("/metrics", methods=["GET"])
def get_metrics():
    nodes = ["http://127.0.0.1:5001", "http://127.0.0.1:5002", "http://127.0.0.1:5003"]
    metrics = []
    for node in nodes:
        try:
            r = requests.get(node + "/health", timeout=1)
            r.raise_for_status()
            metrics.append(r.json())
        except:
            metrics.append({"node": node, "error": "unreachable"})
    return jsonify(metrics)


if __name__=="__main__":
    app.run(host="0.0.0.0", port=4000, debug=True)
