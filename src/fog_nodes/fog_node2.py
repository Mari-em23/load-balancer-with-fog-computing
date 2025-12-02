# fog_node.py — Version totalement compatible LB

from flask import Flask, request, jsonify, Response
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, psutil, time, threading
from prometheus_client import start_http_server, Gauge, Counter

app = Flask(__name__)

# -----------------------------
# PROMETHEUS METRICS
# -----------------------------
cpu_gauge = Gauge('fog_cpu_percent', 'CPU usage percent')
tasks_gauge = Gauge('fog_tasks_running', 'Number of tasks running')
ram_gauge = Gauge('fog_ram_percent', 'RAM usage percent')
chunks_counter = Counter('chunks_processed_total', 'Total chunks processed', ['node', 'file'])
errors_counter = Counter('errors_total', 'Total errors', ['node'])

tasks_running = 0
lock = threading.Lock()

PORT = int(os.environ.get("PORT", "5002"))
METRICS_PORT = 8000 + (PORT % 1000)


# -----------------------------
# METRICS BACKGROUND THREAD
# -----------------------------
def update_metrics():
    while True:
        cpu_gauge.set(psutil.cpu_percent(interval=0.1))
        ram_gauge.set(psutil.virtual_memory().percent)
        tasks_gauge.set(tasks_running)
        time.sleep(1)

threading.Thread(target=update_metrics, daemon=True).start()
start_http_server(METRICS_PORT)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "port": PORT,
        "cpu_percent": psutil.cpu_percent(interval=0.05),
        "ram_percent": psutil.virtual_memory().percent,
        "tasks_running": tasks_running
    })


# -----------------------------
# RÉCEPTION DU CHUNK
# -----------------------------
@app.route("/task_chunk", methods=["POST"])
def task_chunk():
    global tasks_running

    with lock:
        tasks_running += 1

    try:
        # Vérifier la présence du chunk envoyé par le LB
        if "chunk" not in request.files:
            raise Exception("Fichier chunk manquant (POST files['chunk'])")

        chunk_data = request.files["chunk"].read()
        if not chunk_data:
            raise Exception("Chunk vide reçu")

        # Headers envoyés par le LB (obligatoires)
        key_hex = request.headers.get("X-AES-Key")
        nonce_hex = request.headers.get("X-AES-Nonce")
        filename = request.headers.get("X-File-Name", "unknown")
        chunk_index = request.headers.get("X-Chunk-Index")

        if not key_hex or not nonce_hex or chunk_index is None:
            raise Exception("Headers AES-Key / AES-Nonce / Chunk-Index manquants")

        print(f"[FOG {PORT}] → Réception chunk {chunk_index} pour fichier {filename}")

        # Convertir clés
        key = bytes.fromhex(key_hex)
        nonce = bytes.fromhex(nonce_hex)

        aes = AESGCM(key)

        # Traitement = chiffrement
        encrypted_chunk = aes.encrypt(nonce, chunk_data, None)

        chunks_counter.labels(node=str(PORT), file=filename).inc()

        print(f"[FOG {PORT}] ✓ Chunk {chunk_index} chiffré et renvoyé")

        # Retourner chunk chiffré → Load Balancer
        return Response(encrypted_chunk, mimetype="application/octet-stream")

    except Exception as e:
        print(f"[FOG {PORT}] ERREUR: {e}")
        errors_counter.labels(node=str(PORT)).inc()
        return jsonify({"error": str(e)}), 500

    finally:
        with lock:
            tasks_running -= 1


# -----------------------------
# RUN SERVEUR
# -----------------------------
if __name__ == "__main__":
    print(f"[FOG] Démarrage Fog Node sur port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
