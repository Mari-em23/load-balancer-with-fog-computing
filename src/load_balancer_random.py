from flask import Flask, request, jsonify, send_from_directory
import requests, time, random, os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = "uploads/"
CHUNK_SIZE = 5 * 1024 * 1024  # 20 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

def select_node():
    return random.choice(FOG_NODES)

@app.route("/")
def index():
    return send_from_directory(".", "interface_web.html")

@app.route("/process_file", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files["file"]
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    results = []
    index = 0

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            node = select_node()
            start = time.time()

            try:
                resp = requests.post(f"{node}/task",data=chunk,headers={"X-File-Name": file.filename}, timeout=15)

                resp.raise_for_status() 
                node_data = resp.json()
            except requests.exceptions.RequestException as e:
                return jsonify({"error": f"Request failed: {str(e)}"}), 500
            except ValueError:
                 return jsonify({"error": "Le nœud a renvoyé une réponse invalide ou vide"}), 500

            total_time = time.time() - start

            results.append({
                "chunk": index,
                "node": node,
                "processing_time": node_data.get("processing_time", None),
                "total_time": total_time,
                "node_used": node_data.get("node_used", None)
            })

            index += 1

    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)