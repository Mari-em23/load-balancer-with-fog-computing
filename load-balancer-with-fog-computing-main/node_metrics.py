from prometheus_client import start_http_server, Gauge
import psutil, time, threading

# Ports de chaque nœud
FOG_NODES = [5001, 5002, 5003]

def start_metrics(PORT):
    METRICS_PORT = 8000 + (PORT % 1000)
    cpu_gauge = Gauge(f'fog_cpu_percent_{PORT}', 'CPU usage percent')
    ram_gauge = Gauge(f'fog_ram_percent_{PORT}', 'RAM usage percent')
    tasks_gauge = Gauge(f'fog_tasks_running_{PORT}', 'Tasks running')
    tasks_running = 0  # on peut lier plus tard avec serveur Flask

    start_http_server(METRICS_PORT, addr="0.0.0.0")
    while True:
        cpu_gauge.set(psutil.cpu_percent(interval=0.5))
        ram_gauge.set(psutil.virtual_memory().percent)
        tasks_gauge.set(tasks_running)
        time.sleep(1)

# Lancer un thread pour chaque nœud
for port in FOG_NODES:
    threading.Thread(target=start_metrics, args=(port,), daemon=True).start()

# Empêcher le script de se terminer
while True:
    time.sleep(10)
