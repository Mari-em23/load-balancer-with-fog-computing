# client.py — HTTP ONLY + DEBUG LOGS

import os
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

# ============================================================
# CONFIG
# ============================================================
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads_client"
RESULT_FOLDER = "results_client"
CHUNK_SIZE = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

LOAD_BALANCER_URL = "http://127.0.0.1:5005"


# ============================================================
# INDEX
# ============================================================
@app.route("/")
def index():
    return send_from_directory(".", "interface_web.html")


# ============================================================
# ENVOI DU FICHIER EN CHUNKS (CLIENT → LB)
# ============================================================
@app.route("/send_file", methods=["POST"])
def send_file_chunks():
    print("\n==================== NOUVEL UPLOAD ====================")

    if "file" not in request.files:
        print("[CLIENT][ERROR] Aucun fichier reçu depuis l’UI.")
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Sauvegarde du fichier complet côté client
    file.save(filepath)
    file_size = os.path.getsize(filepath)
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

    print(f"[CLIENT] Fichier reçu : {filename} ({file_size} octets)")
    print(f"[CLIENT] Nombre total de chunks : {total_chunks}")

    # =======================================================
    # AES KEY GENERATION
    # =======================================================
    key = AESGCM.generate_key(bit_length=128)
    nonce = os.urandom(12)
    key_hex = key.hex()
    nonce_hex = nonce.hex()

    print(f"[CLIENT] AES key : {key_hex}")
    print(f"[CLIENT] AES nonce : {nonce_hex}")

    # =======================================================
    # SEND CHUNKS
    # =======================================================
    with open(filepath, "rb") as f:
        for chunk_index in range(total_chunks):
            chunk = f.read(CHUNK_SIZE)

            if not chunk:
                break

            print(f"[CLIENT] → Envoi chunk {chunk_index}/{total_chunks-1}")

            files = {"chunk": (f"{filename}.part{chunk_index}", chunk)}

            headers = {
                "X-File-Name": filename,
                "X-Chunk-Index": str(chunk_index),
                "X-AES-Key": key_hex,
                "X-AES-Nonce": nonce_hex,
            }

            try:
                r = requests.post(
                    f"{LOAD_BALANCER_URL}/receive_chunk",
                    files=files,
                    headers=headers,
                    timeout=30,
                )
                r.raise_for_status()

                print(f"[CLIENT] ✓ Chunk {chunk_index} envoyé avec succès.")

            except Exception as e:
                print(f"[CLIENT][ERROR] Échec upload chunk {chunk_index} → {e}")
                return (
                    jsonify({"error": f"Erreur upload chunk {chunk_index}: {e}"}),
                    500,
                )

    print("[CLIENT] ✓ Upload complet envoyé au Load Balancer.")

    return jsonify(
        {"status": "Upload complet", "file": filename, "chunks": total_chunks}
    )


# ============================================================
# DOWNLOAD PROCESSED FILE FROM LB
# ============================================================
@app.route("/download_result/<filename>", methods=["GET"])
def download_result(filename):
    print(f"[CLIENT] → Téléchargement du fichier traité : {filename}")

    result_path = os.path.join(RESULT_FOLDER, filename)

    try:
        r = requests.get(
            f"{LOAD_BALANCER_URL}/download_result/{filename}",
            stream=True,
            timeout=60,
        )
        r.raise_for_status()

        print("[CLIENT] Réception du fichier depuis LB...")

        with open(result_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)

        print("[CLIENT] ✓ Fichier traité sauvegardé.")
        return send_file(result_path, as_attachment=True)

    except Exception as e:
        print(f"[CLIENT][ERROR] Erreur lors du download : {e}")
        return jsonify({"error": f"Erreur download result: {e}"}), 500


# ============================================================
# METRICS
# ============================================================
@app.route("/metrics", methods=["GET"])
def get_metrics():
    NODES = ["http://127.0.0.1:5001", "http://127.0.0.1:5002", "http://127.0.0.1:5003"]
    metrics = []

    for node in NODES:
        try:
            r = requests.get(f"{node}/health", timeout=1)
            metrics.append(r.json())
        except:
            metrics.append({"node": node, "error": "unreachable"})

    return jsonify(metrics)


# ============================================================
# RUN CLIENT
# ============================================================
if __name__ == "__main__":
    print("[CLIENT] Serveur client lancé sur port 4000")
    app.run(host="0.0.0.0", port=4000)
