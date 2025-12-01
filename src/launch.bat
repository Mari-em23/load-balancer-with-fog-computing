@echo off

REM =============================
REM Lancer les nœuds fog
REM =============================
start cmd /k "python src/fog_node.py"
start cmd /k "python src/fog_node2.py"
start cmd /k "python src/fog_node3.py"

REM =============================
REM Choix de l'algorithme pour le load balancer
REM =============================
start cmd /k "python src/load_balancer_algo.py"
start cmd /k "python src/load_balancer_random.py"
start cmd /k "python src/load_balancer_rr.py"


REM =============================
REM Lancer le client (interface HTML)
REM =============================
start cmd /k "python src/client.py"

REM =============================
REM Ajouter une charge CPU locale pour rendre les nœuds plus sollicités
REM (sans toucher au code Python et sans ouvrir plusieurs clients)
REM =============================
echo Simulation de charge CPU pour charger les noeuds et voir l'effet de leurs collaboration pour le chiffrement

REM lancer 2 tâches de charge CPU en arrière-plan pour charger les noeuds et voir l'effet de leurs collaboration pour le chiffrement
start /B cmd /c "for /L %%x in (1,1,999999999) do @set /a %%x*%%x >nul"
start /B cmd /c "for /L %%x in (1,1,999999999) do @set /a %%x*%%x >nul"

echo Tout est lance. Utiliser l'interface HTML pour choisir et envoyer le fichier.
pause
