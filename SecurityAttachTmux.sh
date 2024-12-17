#!/bin/bash

# Nom de la session tmux
TMUX_SESSION="NovaSecurity"

# Vérifier si tmux est installé
if ! command -v tmux &> /dev/null; then
    echo "Erreur : tmux n'est pas installé. Installez-le avec : sudo apt-get install tmux"
    exit 1
fi

# Fonction pour créer ou réattacher à une session tmux
create_or_attach_tmux() {
    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        echo "Rattachement à la session tmux existante : $TMUX_SESSION"
        tmux attach-session -t "$TMUX_SESSION"
    else
        echo "Création d'une nouvelle session tmux : $TMUX_SESSION"
        tmux new-session -s "$TMUX_SESSION" -d
        tmux send-keys -t "$TMUX_SESSION" "tail -f /home/agent_red/.BatShell/Executable/Nova-Modules/ModuleStarter/Module/Log_Nova_Security/Nova_Security_log_*.txt" C-m
        tmux attach-session -t "$TMUX_SESSION"
    fi
}

# Ouvrir un nouveau terminal avec lxterminal et exécuter tmux
if command -v lxterminal &> /dev/null; then
    lxterminal -e bash -c "$(declare -f create_or_attach_tmux); create_or_attach_tmux"
else
    echo "Erreur : lxterminal n'est pas installé ou disponible. Veuillez l'installer avec : sudo apt-get install lxterminal"
    exit 1
fi
