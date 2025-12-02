# load_balancer.py — Compatible avec client.py

from flask import Flask, request, jsonify, Response, send_file
import requests
import os
from threading import Lock

app = Flask(__name__)
from flask_cors import CORS

CORS(app)

# Dossier des fichiers reconstruits
OUTPUT_FOLDER = "processed_files/"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

CHUNK_SIZE = 5 * 1024 * 1024

rr_lock = Lock()
rr_index = 0


def select_node():
    global rr_index
    with rr_lock:
        node = FOG_NODES[rr_index]
        rr_index = (rr_index + 1) % len(FOG_NODES)
    return node


# ==========================================================
# CLIENT → LB → FOG → LB (enregistrement chunk)
# ==========================================================
@app.route("/receive_chunk", methods=["POST"])
def receive_chunk():

    try:
        if "chunk" not in request.files:
            return jsonify({"error": "chunk manquant"}), 400

        chunk = request.files["chunk"].read()
        filename = request.headers.get("X-File-Name")
        chunk_index = request.headers.get("X-Chunk-Index")
        aes_key = request.headers.get("X-AES-Key")
        aes_nonce = request.headers.get("X-AES-Nonce")

        if not filename or not aes_key or not aes_nonce:
            return jsonify({"error": "Headers manquants"}), 400

        # Choix Fog Node
        node = select_node()
        print(f"[LB] → Envoi chunk {chunk_index} à {node}")

        fog_resp = requests.post(
            f"{node}/task_chunk",
            files={"chunk": ("chunk", chunk)},
            headers={
                "X-AES-Key": aes_key,
                "X-AES-Nonce": aes_nonce,
                "X-File-Name": filename,
                "X-Chunk-Index": chunk_index,
            },
            timeout=30,
        )
        fog_resp.raise_for_status()

        encrypted_chunk = fog_resp.content
        print(f"[LB] ← Chunk {chunk_index} reçu depuis {node}")

        # Assemble le fichier final
        output_path = os.path.join(OUTPUT_FOLDER, filename + ".encrypted")
        with open(output_path, "ab") as f:
            f.write(encrypted_chunk)

        print(f"[LB] ✓ Chunk {chunk_index} ajouté au fichier {filename}.encrypted")

        return jsonify(
            {
                "results": [
                    {"chunk": chunk_index, "node_used": node, "status": "received"}
                ]
            }
        )

    except Exception as e:
        print("[LB ERROR]", e)
        return jsonify({"error": str(e)}), 500


# ==========================================================
# CLIENT → LB : Récupération du fichier final
# ==========================================================
@app.route("/download_result/<filename>", methods=["GET"])
def download_result(filename):

    filepath = os.path.join(OUTPUT_FOLDER, filename + ".encrypted")

    if not os.path.exists(filepath):
        return jsonify({"error": "Fichier indisponible"}), 404

    print(f"[LB] → Envoi fichier final au client : {filename}.encrypted")

    return send_file(filepath, as_attachment=True)


# ==========================================================
# ROUTE /send_file — utilisée par l'interface web
# ==========================================================
@app.route("/send_file", methods=["POST"])
def send_file_web():

    file = request.files.get("file")
    lb_type = request.form.get("lb_type", "random")

    if not file:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    filename = file.filename
    filepath = os.path.join("tmp_uploads", filename)
    os.makedirs("tmp_uploads", exist_ok=True)
    file.save(filepath)

    file_size = os.path.getsize(filepath)
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

    results = []
    import time

    start_total = time.time()

    # Envoi chunk par chunk au même endpoint que le client CLI
    with open(filepath, "rb") as f:
        for chunk_index in range(total_chunks):
            chunk = f.read(CHUNK_SIZE)

            node = select_node()
            t0 = time.time()

            resp = requests.post(
                f"{node}/task_chunk",
                files={"chunk": (f"{filename}.part{chunk_index}", chunk)},
                headers={
                    "X-File-Name": filename,
                    "X-Chunk-Index": str(chunk_index),
                    "X-AES-Key": "none",
                    "X-AES-Nonce": "none",
                },
                timeout=20,
            )

            processing_time = time.time() - t0

            results.append(
                {
                    "chunk": chunk_index,
                    "node_used": node,
                    "processing_time": processing_time,
                    "total_time": processing_time,  # LB ne mesure pas autre chose
                }
            )

    total_time = time.time() - start_total

    throughput = total_chunks / total_time if total_time > 0 else 0
    error_rate = 0

    return jsonify(
        {"results": results, "throughput": throughput, "error_rate": error_rate}
    )


@app.route("/")
def home():
    return "Load Balancer opérationnel."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
