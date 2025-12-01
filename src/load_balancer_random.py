from flask import Flask, request, jsonify
import os, time, random, requests
from threading import Thread, Lock

app = Flask(__name__)

UPLOAD_FOLDER = "uploads_lb"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CHUNK_SIZE = 5 * 1024 * 1024
MAX_THREADS = 5

FOG_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]

lock = Lock()
results = []

def select_node():
    return random.choice(FOG_NODES)

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

    total = time.time() - start
    with lock:
        results.append({
            "chunk": index,
            "node_used": node_data.get("node_used", node),
            "processing_time": node_data.get("processing_time", 0),
            "total_time": total
        })

@app.route("/process_file", methods=["POST"])
def process_file():
    global results
    results = []

    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    lb_type = request.form.get("lb_type", "random")

    file = request.files["file"]
    num_chunks = int(request.form.get("num_chunks", 0))
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    chunks = []
    with open(filepath, "rb") as f:
        while True:
            c = f.read(CHUNK_SIZE)
            if not c: break
            chunks.append(c)

    threads = []
    for idx, c in enumerate(chunks):
        while len([t for t in threads if t.is_alive()]) >= MAX_THREADS:
            time.sleep(0.05)
        t = Thread(target=send_chunk, args=(idx, c))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)