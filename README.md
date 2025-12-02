First commit : - Load balancer working randomly with local fog nodes.
               - Prometheus integration to visualize with grafana. Run      prometheus --config.file=prometheus.yml     after adding prometheus to path. For more information : https://grafana.com/docs/grafana/latest/datasources/prometheus/configure/   
               - Web interface to simulate client (HTML, CSS, JS)
               ✅ 1. Activate the virtual environment (.venv)



.\.venv\Scripts\Activate



✅ 2. Install everything from requirements.txt

Make sure you're inside your project folder, then run:

pip install -r requirements.txt
            
# Installer les dépendances dans un environnement virtuel
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows
pip install flask
          
.\launch.bat
