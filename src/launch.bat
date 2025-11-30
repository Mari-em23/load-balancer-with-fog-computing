@echo off
REM Lancer les nœuds fog
start cmd /k "python src/fog_node.py"
start cmd /k "python src/fog_node2.py"
start cmd /k "python src/fog_node3.py"

REM Choix de l'algorithme pour le load balancer
echo Choisir l'algorithme pour le load balancer :
echo 1) Algo 
echo 2) Random
set /p choice=Votre choix (1 ou 2) : 

if "%choice%"=="1" (
    start cmd /k "python load_balancer_algo.py"
) else (
    start cmd /k "python load_balancer_random.py"
)

REM Lancer le client
start cmd /k "python src/client.py"
