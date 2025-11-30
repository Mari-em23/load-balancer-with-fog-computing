# parallel_client_verbose.py
import requests, time
from threading import Thread, Lock

FILE_PATH = "500Mo_file.txt"
CHUNK_SIZE = 1024*1024*50
LB_URL = "http://127.0.0.1:4000/send_task"
OUTPUT_FILE = "results_verbose.txt"
MAX_THREADS = 5

lock = Lock()
results = []

def send_chunk(index, chunk):
    start = time.time()
    try:
        resp = requests.post(LB_URL, data=chunk, timeout=90)
        data = resp.json()
    except Exception as e:
        data = {"error": str(e)}

    elapsed = time.time() - start

    with lock:
        results.append((index, data, elapsed))
        with open(OUTPUT_FILE, "a") as out_file:
            out_file.write(f"Chunk {index}\n")
            out_file.write(f"Temps total mesuré client: {elapsed:.4f}s\n")

            if "error" in data:
                out_file.write(f"Erreur: {data['error']}\n")
                print(f"[Chunk {index}] -> Erreur: {data['error']}")
            else:
                node_used = data.get("node_used", "inconnu")
                processing_time = data.get("processing_time", 0)
                total_time = data.get("total_time", elapsed)

                out_file.write(f"Noeud utilisé: {node_used}\n")
                out_file.write(f"Temps de traitement côté nœud: {processing_time:.4f}s\n")
                out_file.write(f"Temps total côté LB: {total_time:.4f}s\n")
                
                # Affichage détaillé pour comprendre la répartition
                print(f"[Chunk {index}] envoyé à {node_used}")
                print(f"  Temps nœud = {processing_time:.4f}s, Temps total LB = {total_time:.4f}s")
                print(f"  Temps mesuré client = {elapsed:.4f}s")

            out_file.write("="*50 + "\n")

def main():
    threads = []
    with open(FILE_PATH, "rb") as f:
        index = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            while len([t for t in threads if t.is_alive()]) >= MAX_THREADS:
                time.sleep(0.1)

            t = Thread(target=send_chunk, args=(index, chunk))
            t.start()
            threads.append(t)
            index += 1

    for t in threads:
        t.join()

    print("Terminé. Résultats détaillés dans results_verbose.txt")

if __name__ == "__main__":
    with open(OUTPUT_FILE, "w") as f:
        f.write("Résultats détaillés des chunks\n" + "="*50 + "\n")
    
    t_start = time.time()       # début du chronomètre
    main()                      # exécution du client
    t_end = time.time()         # fin du chronomètre
    
    print(f"\nTemps total d’exécution du client: {t_end - t_start:.4f}s")
