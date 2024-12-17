import os
import subprocess
import time
import curses
import psutil
import threading  # Pour le thread du spinner
from datetime import datetime  # Pour obtenir la date et l'heure du scan

# Chemin des fichiers audio
AUDIO_PATH = "/home/agent_red/.BatShell/AudioCommander/FRZ/NetNova/"

# Fichiers audio
AUDIO_LANCEMENT = "Module2-4Activer.mp3"
AUDIO_RKHUNTER = "rkhunter_scan.mp3"
AUDIO_CLAMAV = "clamav_scan.mp3"
AUDIO_SECURE = "secure_pc.mp3"
AUDIO_TERM = "moduleterm.mp3"

# Fichier temporaire pour les logs
LOG_FILE = os.path.expanduser("~/security_scan_results.txt")

# Fonction pour vérifier si un paquet est installé
def check_install(package):
    try:
        subprocess.check_call(['dpkg', '-s', package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

# Fonction pour installer un paquet
def install_package(package):
    try:
        subprocess.run(['apt-get', 'install', '-y', package], check=True)
    except subprocess.CalledProcessError:
        print(f"Erreur lors de l'installation de {package}. Veuillez vérifier vos permissions.")
        return False
    return True

# Fonction pour jouer un fichier audio avec redirection de stdout et stderr pour masquer les messages indésirables
def play_audio(audio_file):
    audio_path = os.path.join(AUDIO_PATH, audio_file)
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.Popen(['mpg123', '-q', audio_path], stdout=devnull, stderr=devnull).wait()
    except FileNotFoundError:
        print(f"Erreur : Le fichier audio {audio_path} est introuvable ou mpg123 n'est pas installé.")

# Fonction pour afficher la barre de progression uniquement
def display_progress_bar(stdscr, progress, total, message):
    stdscr.clear()
    stdscr.addstr(2, 0, message, curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

    bar_length = curses.COLS - 20  # Largeur de la barre de progression
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    stdscr.addstr(4, 0, f"[{bar}] {int((progress / total) * 100)}%", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

# Fonction pour afficher le texte clignotant au centre en bas du terminal
def display_spinner(stdscr, stop_event):
    spin = ['-', '\\', '|', '/']  # Effet de rotation
    idx = 0
    while not stop_event.is_set():
        center_x = curses.COLS // 2 - len("En cours") // 2
        center_y = curses.LINES - 2
        stdscr.addstr(center_y, center_x, f"En cours {spin[idx]}", curses.color_pair(1) | curses.A_BOLD)
        stdscr.refresh()
        time.sleep(0.2)
        idx = (idx + 1) % len(spin)
        # Effacement du texte après chaque rotation pour simuler un clignotement
        stdscr.addstr(center_y, center_x, " " * (len("En cours") + 2))
        stdscr.refresh()

# Fonction pour gérer la progression et lancer le spinner jusqu'à la fin réelle du scan
def update_progress_bar_during_scan(stdscr, duration, message, scan_function, *args):
    total_steps = 100
    mid_steps = total_steps // 2

    # Affichage de la barre de progression jusqu'à 50 %
    for i in range(mid_steps):
        display_progress_bar(stdscr, i + 1, total_steps, message)
        time.sleep(duration / total_steps)

    # Lancer un thread pour le texte "En cours" avec un flag pour l'arrêter
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=display_spinner, args=(stdscr, stop_event))
    spinner_thread.start()

    # Exécuter la fonction de scan
    scan_result = scan_function(*args)

    # Une fois le scan terminé, arrêter le thread du spinner
    stop_event.set()
    spinner_thread.join()

    # Compléter la barre à 100 % une fois le scan terminé (pour indication visuelle)
    for i in range(mid_steps, total_steps):
        display_progress_bar(stdscr, i + 1, total_steps, message)
        time.sleep(duration / total_steps)

    return scan_result

# Fonction pour exécuter la commande rkhunter et analyser les résultats
def run_rkhunter(stdscr):
    play_audio(AUDIO_RKHUNTER)
    message = "Exécution de rkhunter pour détecter les rootkits..."
    
    # Barre de progression et texte gérés pendant le scan
    def rkhunter_scan():
        try:
            output = subprocess.check_output(['rkhunter', '--check', '--skip-keypress'], stderr=subprocess.STDOUT).decode()
            return output
        except subprocess.CalledProcessError as e:
            return e.output.decode()

    output = update_progress_bar_during_scan(stdscr, 10, message, rkhunter_scan)

    # Enregistrer uniquement les alertes importantes dans les logs
    filtered_output = filter_logs(output)
    if filtered_output:
        save_logs(filtered_output)
    return output

# Fonction pour exécuter ClamAV
def run_clamav(stdscr, scan_type):
    play_audio(AUDIO_CLAMAV)
    
    if scan_type == 'complete':
        scan_cmd = ['clamscan', '-r', '--bell', '/']
        scan_duration = 15  # Simule une durée pour la barre de chargement
    else:
        scan_cmd = ['clamscan', '-r', '--bell', '/home']
        scan_duration = 10  # Simule une durée plus courte pour la barre de chargement
    
    message = "Exécution de ClamAV pour analyser les malwares..."

    # Barre de progression gérée pendant le scan
    def clamav_scan():
        try:
            output = subprocess.check_output(scan_cmd, stderr=subprocess.STDOUT).decode()
            return output
        except subprocess.CalledProcessError as e:
            return e.output.decode()

    output = update_progress_bar_during_scan(stdscr, scan_duration, message, clamav_scan)

    # Enregistrer uniquement les fichiers infectés ou suspects dans les logs
    filtered_clamav_output = filter_clamav_logs(output)

    # Ajouter les logs ClamAV à la fin du fichier log avec la date et l'heure du scan
    with open(LOG_FILE, 'a') as f:
        f.write("\n=== ClamAV Logs ===\n")
        f.write(filtered_clamav_output)  # Écrire uniquement les fichiers infectés ou suspects
        f.write(f"\nDate du scan : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")  # Ajouter la date et l'heure

    return output

# Fonction pour filtrer les logs ClamAV en gardant uniquement les fichiers infectés ou suspects
def filter_clamav_logs(log_data):
    filtered_logs = []
    for line in log_data.splitlines():
        if "FOUND" in line or "Warning" in line:  # Conserver uniquement les fichiers infectés ou suspects
            filtered_logs.append(line)
    return "\n".join(filtered_logs)

# Fonction pour filtrer les logs rkhunter en supprimant les lignes contenant "OK", "None Found", "Not Found"
# et en ne conservant que celles avec "Warning" ou "Found"
def filter_logs(log_data):
    filtered_logs = []
    for line in log_data.splitlines():
        if "Warning" in line or "Found" in line:  # Garder les lignes importantes
            filtered_logs.append(line)
    return "\n".join(filtered_logs)

# Fonction pour lister les ports ouverts
def list_open_ports(stdscr):
    stdscr.clear()
    stdscr.addstr(2, 0, "Liste des ports ouverts...", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

    connections = psutil.net_connections(kind='inet')
    open_ports = []

    for conn in connections:
        if conn.status == 'LISTEN':
            # Ne pas fermer les ports utiles à la navigation web (ex : 80, 443)
            if conn.laddr.port not in [80, 443]:
                open_ports.append(conn.laddr.port)  # On ne garde que le port

    if open_ports:
        stdscr.addstr(4, 0, f"Ports ouverts : {', '.join(map(str, open_ports))}", curses.color_pair(1) | curses.A_BOLD)
    else:
        stdscr.addstr(4, 0, "Aucun port ouvert trouvé.", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

    return open_ports

# Fonction pour fermer les ports et activer UFW
def secure_system(stdscr, open_ports):
    stdscr.clear()
    stdscr.addstr(2, 0, "Fermeture des ports et activation de UFW...", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

    if open_ports:
        for port in open_ports:
            try:
                subprocess.run(['ufw', 'deny', str(port)], check=True)  # On passe uniquement le port à UFW
                stdscr.addstr(4 + open_ports.index(port), 0, f"Règle ajoutée : Port {port} fermé.", curses.color_pair(1) | curses.A_BOLD)
                stdscr.refresh()
                time.sleep(0.1)
            except subprocess.CalledProcessError:
                stdscr.addstr(4, 0, f"Erreur lors de la fermeture du port {port}", curses.color_pair(1) | curses.A_BOLD)
                stdscr.refresh()
        # Affichage sur une nouvelle ligne pour chaque règle ajoutée
        stdscr.addstr(5 + len(open_ports), 0, "\n".join([f"Règle UFW : Port {port} fermé." for port in open_ports]), curses.color_pair(1))
    else:
        stdscr.addstr(4, 0, "Aucun port à fermer.", curses.color_pair(1) | curses.A_BOLD)
        stdscr.refresh()

    subprocess.run(['ufw', 'enable'], check=True)
    stdscr.addstr(6 + len(open_ports), 0, "UFW activé. Connexions entrantes bloquées.", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()
    time.sleep(2)

# Fonction pour installer et configurer fail2ban si un serveur SSH est en cours d'exécution
def setup_fail2ban(stdscr):
    ssh_servers = [conn for conn in psutil.net_connections() if conn.laddr.port == 22]
    
    if ssh_servers:
        stdscr.clear()
        stdscr.addstr(2, 0, "Voulez-vous installer et configurer Fail2Ban pour SSH ? (y/n)", curses.color_pair(1) | curses.A_BOLD)
        stdscr.refresh()

        choice = stdscr.getch()
        if choice == ord('y'):
            stdscr.clear()
            stdscr.addstr(2, 0, "Installation et configuration de Fail2Ban...", curses.color_pair(1) | curses.A_BOLD)
            stdscr.refresh()

            try:
                subprocess.run(['apt-get', 'install', '-y', 'fail2ban'], check=True)
                subprocess.run(['systemctl', 'enable', 'fail2ban'], check=True)
                subprocess.run(['systemctl', 'start', 'fail2ban'], check=True)
                stdscr.addstr(4, 0, "Fail2Ban installé et démarré.", curses.color_pair(1) | curses.A_BOLD)
            except subprocess.CalledProcessError:
                stdscr.addstr(4, 0, "Erreur lors de l'installation de Fail2Ban.", curses.color_pair(1) | curses.A_BOLD)
            stdscr.refresh()
            time.sleep(2)

# Fonction pour attendre l'entrée de l'utilisateur avant de continuer
def wait_for_enter(stdscr):
    stdscr.addstr(curses.LINES - 2, 0, "Appuyez sur Entrée pour continuer...", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()
    while True:
        if stdscr.getch() == 10:  # La touche 'Entrée'
            break

# Fonction principale
def main(stdscr):
    play_audio(AUDIO_LANCEMENT)  # Lecture du son au lancement du module
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.curs_set(0)

    stdscr.clear()
    stdscr.addstr(0, 0, "=== Analyse de Sécurité ===", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

    # Phase 1: rkhunter
    rkhunter_result = run_rkhunter(stdscr)
    wait_for_enter(stdscr)  # Pause pour permettre de lire les logs

    # Phase 2: ClamAV
    stdscr.clear()
    stdscr.addstr(2, 0, "Choisissez le type d'analyse ClamAV : ", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(4, 0, "1. Analyse complète", curses.color_pair(1))
    stdscr.addstr(5, 0, "2. Analyse rapide", curses.color_pair(1))
    stdscr.refresh()

    choice = stdscr.getch()

    if choice == ord('1'):
        clamav_result = run_clamav(stdscr, 'complete')
    else:
        clamav_result = run_clamav(stdscr, 'quick')

    wait_for_enter(stdscr)  # Pause pour permettre de lire les logs

    # Lecture de l'audio avant de demander la validation pour UFW
    play_audio(AUDIO_SECURE)

    # Phase 3: Gestion des ports
    open_ports = list_open_ports(stdscr)

    if open_ports:
        stdscr.clear()
        stdscr.addstr(2, 0, "Voulez-vous fermer les ports ouverts et activer UFW ? (y/n)", curses.color_pair(1) | curses.A_BOLD)
        stdscr.refresh()

        choice = stdscr.getch()
        if choice == ord('y'):
            secure_system(stdscr, open_ports)
    wait_for_enter(stdscr)  # Pause après gestion des ports

    # Phase 4: Installation de fail2ban si SSH détecté
    setup_fail2ban(stdscr)

    stdscr.clear()
    stdscr.addstr(4, 0, "Sécurisation du système terminée.", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()
    wait_for_enter(stdscr)  # Pause finale avant de terminer

    play_audio(AUDIO_TERM)  # Lecture du son à la fermeture du module

# Enregistrement des logs dans un fichier texte
def save_logs(log_data):
    with open(LOG_FILE, 'a') as f:
        f.write(log_data + "\n")
    print(f"Logs enregistrés dans {LOG_FILE}.")

# Fonction pour vérifier et installer les outils avant l'utilisation de curses
def check_and_install_tools():
    tools = ['rkhunter', 'clamav', 'ufw']
    for tool in tools:
        if not check_install(tool):
            user_input = input(f"{tool} n'est pas installé. Voulez-vous l'installer ? (y/n): ").lower()
            if user_input == 'y':
                if not install_package(tool):
                    print(f"Erreur : Impossible d'installer {tool}.")
                    return False
    return True

# Lancement du script
if __name__ == "__main__":
    # Vérification et installation des outils avant d'entrer dans curses
    if check_and_install_tools():
        curses.wrapper(main)
    else:
        print("Impossible de démarrer, des outils requis sont manquants.")
