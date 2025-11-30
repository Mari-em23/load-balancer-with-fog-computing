from prometheus_client import start_http_server, Gauge
import psutil
import time

cpu_gauge = Gauge('fog_cpu_percent', 'CPU usage percent')

start_http_server(8001, addr="0.0.0.0")

while True:
    cpu_gauge.set(psutil.cpu_percent(interval=0.5))
    time.sleep(1)
