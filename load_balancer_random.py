# load_balancer.py
from flask import Flask, request, jsonify
import requests, time, random
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # <- allow all origins (for testing)


app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 100 MB limit



FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

def select_node():
    return random.choice(FOG_NODES)  # aléatoire simple

@app.route("/send_task", methods=["POST"])
def send_task():
    chunk = request.data
    node = select_node()
    start_time = time.time()
    try:
        resp = requests.post(f"{node}/task", data=chunk, timeout=15)
        node_resp = resp.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    elapsed = time.time() - start_time

    return jsonify({
        "node_used": node_resp.get("node_used", "unknown"),
        "result": node_resp.get("result"),
        "processing_time": node_resp.get("processing_time"),
        "total_time": elapsed
    })

@app.route("/nodes_status", methods=["GET"])
def nodes_status():
    statuses = {}
    for node in FOG_NODES:
        try:
            r = requests.get(f"{node}/health", timeout=2)
            statuses[node] = r.json()
        except:
            statuses[node] = "offline"
    return jsonify(statuses)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)