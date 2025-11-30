from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import threading, os, time

FOG_NODES = [5001, 5002, 5003]

def start_node(PORT):
    app = Flask(f'node_{PORT}')
    tasks_running = 0
    lock = threading.Lock()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "port": PORT,
            "tasks_running": tasks_running
        })

    @app.route("/task", methods=["POST"])
    def task():
        nonlocal tasks_running
        chunk = request.data
        with lock:
            tasks_running += 1

        start_time = time.time()
        try:
            key = AESGCM.generate_key(bit_length=128)
            aes = AESGCM(key)
            nonce = os.urandom(12)
            ciphertext = aes.encrypt(nonce, chunk, None)
            processing_time = time.time() - start_time
            return jsonify({
                "result": ciphertext.hex(),
                "nonce": nonce.hex(),
                "key": key.hex(),
                "processing_time": processing_time,
                "node_used": PORT
            })
        finally:
            with lock:
                tasks_running -= 1

    app.run(host="0.0.0.0", port=PORT)

# Lancer un thread pour chaque nœud
for port in FOG_NODES:
    threading.Thread(target=start_node, args=(port,), daemon=True).start()

# Empêcher le script de se terminer
while True:
    time.sleep(10)
