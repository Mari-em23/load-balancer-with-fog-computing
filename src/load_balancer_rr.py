from flask import Flask, request, jsonify, send_from_directory
import requests, time, random, os
from flask_cors import CORS
from threading import Lock

app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = "uploads/"
CHUNK_SIZE = 5 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

# --------- ROUND ROBIN STATE ---------
rr_index = 0
rr_lock = Lock()


def select_node():
    """
    Sélectionne le nœud Fog suivant selon l'algorithme Round Robin.
    Thread-safe pour éviter les conflits entre threads simultanés.
    """
    global rr_index
    with rr_lock:
        node = FOG_NODES[rr_index]
        rr_index = (rr_index + 1) % len(FOG_NODES)
    return node


@app.route("/")
def index():
    return send_from_directory(".", "interface_web.html")


@app.route("/process_file", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files["file"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    results = []
    index = 0

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            node = select_node()  # <<< ROUND ROBIN HERE

            start = time.time()

            try:
                resp = requests.post(
                    f"{node}/task",
                    data=chunk,
                    headers={"X-File-Name": file.filename},
                    timeout=15,
                )

                resp.raise_for_status()
                node_data = resp.json()

            except requests.exceptions.RequestException as e:
                return jsonify({"error": f"Request failed: {str(e)}"}), 500

            except ValueError:
                return jsonify({"error": "Réponse invalide du nœud Fog"}), 500

            total_time = time.time() - start

            results.append(
                {
                    "chunk": index,
                    "node": node,
                    "processing_time": node_data.get("processing_time"),
                    "total_time": total_time,
                    "node_used": node_data.get("node_used"),
                }
            )

            index += 1

    return jsonify({"results": results})


@app.route("/task", methods=["POST"])
def forward_chunk():
    """
    Le client envoie ici un chunk.
    Le LB applique Round Robin et redirige vers un Fog Node.
    """
    chunk = request.data
    filename = request.headers.get("X-File-Name", "unknown")

    node = select_node()  # Round Robin

    try:
        resp = requests.post(
            f"{node}/task", data=chunk, headers={"X-File-Name": filename}, timeout=15
        )
        resp.raise_for_status()

        data = resp.json()
        data["node_used"] = node  # pour que le client sache quel fog node a traité
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "_main_":
    app.run(host="0.0.0.0", port=5007)
