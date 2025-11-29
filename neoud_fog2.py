# fog_node.py
from flask import Flask, request, jsonify
from prometheus_client import start_http_server, Gauge
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, threading, time, psutil

app = Flask(__name__)

# Metrics
cpu_gauge = Gauge('fog_cpu_percent', 'CPU usage percent')
tasks_gauge = Gauge('fog_tasks_running', 'Number of tasks running')
ram_gauge = Gauge('fog_ram_percent', 'RAM usage percent')

tasks_running = 0
lock = threading.Lock()

PORT = int(os.environ.get("PORT", "5002"))
METRICS_PORT = 8000 + (PORT % 1000)

def update_metrics():
    global tasks_running
    while True:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        cpu_gauge.set(cpu)
        tasks_gauge.set(tasks_running)
        ram_gauge.set(ram)
        time.sleep(1)

threading.Thread(target=update_metrics, daemon=True).start()
start_http_server(METRICS_PORT)

@app.route("/health", methods=["GET"])
def health():
    cpu = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory().percent
    return jsonify({
        "status": "ok",
        "port": PORT,
        "cpu_percent": cpu,
        "ram_percent": ram,
        "tasks_running": tasks_running
    })

@app.route("/task", methods=["POST"])
def task():
    global tasks_running
    chunk = request.data
    with lock:
        tasks_running += 1
    start_time = time.time()
    try:
        key = AESGCM.generate_key(bit_length=128)
        aes = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aes.encrypt(nonce, chunk, None)
        proc_time = time.time() - start_time
        return jsonify({
            "result": ciphertext.hex(),
            "nonce": nonce.hex(),
            "key": key.hex(),
            "processing_time": proc_time,
            "node_used": f"{PORT}"   # <-- Important pour le load balancer / client
        })
    finally:
        with lock:
            tasks_running -= 1

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
