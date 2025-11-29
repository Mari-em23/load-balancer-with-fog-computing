import requests, time

FILE_PATH = "C:\Users\Mariem\OneDrive\Documents\Role_and_Evolution_of_Non-Terrestrial_Networks_Toward_6G_Systems.pdf"
CHUNK_SIZE = 1024*1024
LB_URL = "http://127.0.0.1:4000/send_task"
OUTPUT_FILE = "results_random.txt"

with open(FILE_PATH, "rb") as f, open(OUTPUT_FILE, "w") as out_file:
    chunk_index = 0
    while True:
        chunk = f.read(CHUNK_SIZE)
        if not chunk:
            break
        start_time = time.time()
        resp = requests.post(LB_URL, data=chunk)
        elapsed = time.time() - start_time
        res_json = resp.json()

        out_file.write(f"Chunk {chunk_index}:\n")
        out_file.write(f"Node utilisé: {res_json['node_used']}\n")
        out_file.write(f"Temps traitement nœud: {res_json['processing_time']:.4f}s\n")
        out_file.write(f"Temps total client: {res_json['total_time']:.4f}s\n")
        out_file.write("="*50 + "\n")

        print(f"Chunk {chunk_index} envoyé à {res_json['node_used']}, temps total={elapsed:.4f}s")
        chunk_index += 1

print(f"Tous les chunks envoyés ! Résultats dans {OUTPUT_FILE}")
