@echo off
REM Lancer les nœuds fog en parallèle
start /b python src/fog_nodes/fog_node1.py
start /b python src/fog_nodes/fog_node2.py
start /b python src/fog_nodes/fog_node3.py

REM Choix de l'algorithme pour le load balancer
echo Choisir l'algorithme pour le load balancer :
echo 1) Random 
echo 2) Round Robin
echo 3) Hybrid
set /p choice=Votre choix : 

if "%choice%"=="1" (
    start /b python src/load_balancer/load_balancer_random.py
) else if "%choice%"=="2" (
    start /b python src/load_balancer/load_balancer_robin.py
) else (
    start /b python src/load_balancer/load_balancer_hybrid.py
)

REM Lancer le client
start /b python src/client.py
