import os
import subprocess
import sys
import signal
import time
import curses

mp3_module_disponible = "/home/agent_red/.BatShell/AudioCommander/FRZ/NetNova/ModuleDisponible.mp3"

def play_audio(file):
    time.sleep(2)
    subprocess.Popen(['mpg123', '-q', file]).wait()

def list_modules(module_dir):
    files = os.listdir(module_dir)
    modules = [file for file in files if file.endswith(".py")]
    return modules

def launch_module_in_terminal(script):
    subprocess.Popen(['lxterminal', '-e', 'bash', '-c', f'sudo -E python3 {script}; echo "Appuyez sur une touche pour fermer le terminal"; read'])

def launch_module_in_tmux(script_name, script_path):
    subprocess.Popen(['sudo', 'tmux', 'new-session', '-d', '-s', script_name, f'sudo python3 {script_path}'])

def show_tmux_sessions(stdscr):
    stdscr.clear()
    stdscr.addstr("=== Sessions tmux en cours ===\n", curses.color_pair(2))
    try:
        result = subprocess.run(['sudo','tmux', 'ls'], capture_output=True, text=True, check=True)
        stdscr.addstr(result.stdout, curses.color_pair(1))
    except subprocess.CalledProcessError:
        stdscr.addstr("Aucune session tmux en cours ou tmux n'est pas installé.\n", curses.color_pair(1))
    stdscr.addstr("\nAppuyez sur une touche pour continuer...", curses.color_pair(2))
    stdscr.getch()

def execute_script(module_dir, files, stdscr):
    stdscr.addstr("\nChoisissez un module à exécuter et appuyez sur ENTER :\n", curses.color_pair(2))
    curses.echo()

    for i, file in enumerate(files, start=1):
        stdscr.addstr(f"{i}. {os.path.splitext(file)[0]}\n", curses.color_pair(1))

    stdscr.addstr(f"{len(files) + 1}. Afficher les sessions tmux en cours\n", curses.color_pair(1))
    stdscr.addstr(f"{len(files) + 2}. Quitter le sélecteur de modules\n", curses.color_pair(1))

    try:
        # Lire la saisie utilisateur et convertir en entier
        choice = int(stdscr.getstr().decode('utf-8'))

        if 1 <= choice <= len(files):
            script = os.path.join(module_dir, files[choice - 1])
            script_name = os.path.splitext(files[choice - 1])[0]

            stdscr.addstr("\nType de lancement :\n", curses.color_pair(2))
            stdscr.addstr("1. Lancer dans un nouveau terminal\n", curses.color_pair(1))
            stdscr.addstr("2. Lancer en background avec tmux\n", curses.color_pair(1))

            launch_choice = int(stdscr.getstr().decode('utf-8'))

            if launch_choice == 1:
                launch_module_in_terminal(script)
            elif launch_choice == 2:
                launch_module_in_tmux(script_name, script)
            else:
                stdscr.addstr("Choix invalide.", curses.color_pair(1))

            stdscr.addstr("Appuyez sur une touche pour continuer...", curses.color_pair(2))
            stdscr.getch()

        elif choice == len(files) + 1:
            # Afficher les sessions tmux en cours
            show_tmux_sessions(stdscr)

        elif choice == len(files) + 2:
            # Quitter le sélecteur de modules
            return False

        else:
            stdscr.addstr("Choix invalide. Appuyez sur une touche pour continuer...", curses.color_pair(1))
            stdscr.getch()

    except ValueError:
        stdscr.addstr("Entrée invalide. Veuillez entrer un numéro valide.\n", curses.color_pair(1))
        stdscr.getch()

    return True

def handle_sigint(signum, frame):
    sys.exit(0)

def curses_main(stdscr):
    # Configuration des couleurs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)  # Texte rouge
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Texte blanc pour les titres

    # Chemin vers le dossier des modules
    module_dir = "/home/agent_red/.BatShell/Executable/Nova-Modules/ModuleStarter/Module/"

    # Lecture du fichier audio annonçant l'ouverture de la page des modules
    play_audio(mp3_module_disponible)

    while True:
        stdscr.clear()
        stdscr.addstr("=== NetNova Machine Security Viewer ===\n", curses.color_pair(2))
        stdscr.addstr("Affichage des modules disponibles :\n", curses.color_pair(2))

        # Affichage de la liste des modules Python
        files = list_modules(module_dir)

        if not files:
            stdscr.addstr("Aucun module disponible.\n", curses.color_pair(1))
            stdscr.getch()
            break

        # Exécution du script sélectionné ou afficher les sessions tmux
        if not execute_script(module_dir, files, stdscr):
            break

        stdscr.refresh()

def main():
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGHUP, handle_sigint)

    # Lancer l'interface curses
    curses.wrapper(curses_main)

if __name__ == "__main__":
    main()

