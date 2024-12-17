import os
import time
import subprocess
import threading
import re

# Variables globales
ALERT_COOLDOWN = 60  # Temps d'attente minimum entre deux alertes audio (en secondes)
PING_THRESHOLD = 10
PORT_SCAN_THRESHOLD = 10
AUTH_ATTEMPT_THRESHOLD = 4  # Nombre de tentatives échouées avant déclenchement de l'alerte
SCAN_INTERVAL = 10  # Intervalle de détection en secondes
ping_count = 0
port_scan_count = 0
auth_attempts = 0  # Compteur de tentatives d'authentification échouées
last_alert_time = 0
blocked_ips = set()  # Set pour stocker les IP déjà bloquées
log_entries = []  # Liste pour stocker les événements des logs
terminal_opened = False  # Variable pour savoir si le terminal a déjà été ouvert

# Mutex pour éviter des problèmes de synchronisation
ping_lock = threading.Lock()
port_lock = threading.Lock()
auth_lock = threading.Lock()

# Event pour gérer l'arrêt des threads
stop_event = threading.Event()

# Fonction pour générer un nom de fichier unique pour les logs
def generate_log_filename():
    counter = 1
    while os.path.exists(f"/home/agent_red/.BatShell/Executable/Nova-Modules/ModuleStarter/Module/Log_Nova_Security/Nova_Security_log_{counter}.txt"):
        counter += 1
    return f"/home/agent_red/.BatShell/Executable/Nova-Modules/ModuleStarter/Module/Log_Nova_Security/Nova_Security_log_{counter}.txt"

# Fonction pour exporter les logs dans un fichier texte
def export_logs():
    try:
        log_filename = generate_log_filename()
        with open(log_filename, 'w') as log_file:
            for entry in log_entries:
                log_file.write(entry + '\n')
        print(f"Logs exportés dans le fichier : {log_filename}")
    except Exception as e:
        add_log_entry(f"Erreur lors de l'exportation des logs : {str(e)}")

# Fonction pour ajouter une entrée dans les logs
def add_log_entry(entry):
    log_entries.append(entry)
    print(entry)  # Affiche également les logs dans le terminal

# Fonction pour jouer un fichier audio
def play_audio(file):
    try:
        subprocess.Popen(['mpg123', file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
    except FileNotFoundError:
        add_log_entry(f"Erreur : Le fichier audio {file} est introuvable ou mpg123 n'est pas installé.")

# Fonction pour ramener la session tmux en avant-plan, ou ouvrir un nouveau terminal si nécessaire
def bring_terminal_to_foreground():
    global terminal_opened
    if terminal_opened:
        return

    try:
        subprocess.Popen(['lxterminal', '-e', '/root/Nova-Modules/controlleur/SecurityAttachTmux.sh'])
        terminal_opened = True  # Marquer le terminal comme ouvert
        add_log_entry("Terminal ouvert avec succès.")
    except Exception as e:
        add_log_entry(f"Erreur lors de l'ouverture du terminal : {str(e)}")

# Fonction pour couper le Wi-Fi avec nmcli
def disable_wifi():
    try:
        add_log_entry("⚠️  Désactivation du Wi-Fi via nmcli...")
        subprocess.run(['sudo', 'nmcli', 'radio', 'wifi', 'off'], check=True)
        add_log_entry("Wi-Fi désactivé avec succès.")
    except subprocess.CalledProcessError:
        add_log_entry("Erreur lors de la désactivation du Wi-Fi.")

# Fonction pour bloquer l'IP de l'attaquant
def block_ip(ip):
    add_log_entry(f"⚠️  Blocage de l'IP : {ip}")
    try:
        if subprocess.run(['which', 'ufw'], capture_output=True).returncode == 0:
            subprocess.run(['sudo', 'ufw', 'deny', 'from', ip], check=True)
        else:
            subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'], check=True)
        add_log_entry(f"IP {ip} bloquée avec succès.")
        blocked_ips.add(ip)
        export_logs()
    except subprocess.CalledProcessError:
        add_log_entry(f"Erreur lors du blocage de l'IP : {ip}")

# Fonction pour vérifier si une IP est déjà bloquée par ufw ou iptables
def is_ip_blocked(ip):
    if ip in blocked_ips:
        return True

    try:
        ufw_status = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
        if ip in ufw_status.stdout:
            blocked_ips.add(ip)
            return True

        iptables_status = subprocess.run(['sudo', 'iptables', '-L', '-n'], capture_output=True, text=True)
        if ip in iptables_status.stdout:
            blocked_ips.add(ip)
            return True
        return False
    except Exception:
        return False

# Fonction pour vérifier et activer UFW
def check_and_enable_ufw():
    try:
        ufw_status = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
        if "Status: active" not in ufw_status.stdout:
            add_log_entry("⚠️  UFW n'est pas activé. Activation en cours...")
            subprocess.run(['sudo', 'ufw', 'enable'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            add_log_entry("✅ UFW activé avec succès.")
        else:
            add_log_entry("✅ UFW est déjà activé.")
    except subprocess.CalledProcessError:
        add_log_entry("Erreur lors de l'activation de UFW.")

# Fonction pour surveiller les tentatives de scan via tcpdump
def detect_scan_activity():
    global ping_count, port_scan_count, last_alert_time
    last_display_time = 0
    alert_display_interval = 10

    add_log_entry("Surveillance des pings multiples et des scans de ports (ICMP, TCP)...")

    # Vérification et activation de UFW avant de commencer la surveillance
    check_and_enable_ufw()

    process = subprocess.Popen(
        ['tcpdump', '-nn', 'icmp or tcp[13] == 2', '-l'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        while not stop_event.is_set():
            line = process.stdout.readline().decode('utf-8').strip()
            if line:
                with ping_lock, port_lock:
                    ip_match = re.search(r'IP (\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        ip = ip_match.group(1)
                        if is_ip_blocked(ip):
                            continue
                        if "ICMP echo request" in line:
                            ping_count += 1
                        elif "Flags [S]" in line:
                            port_scan_count += 1

                        if ping_count >= PING_THRESHOLD or port_scan_count >= PORT_SCAN_THRESHOLD:
                            if time.time() - last_alert_time > ALERT_COOLDOWN:
                                add_log_entry(f"⚠️  Détection d'un ping flood ou scan de ports de l'IP {ip}.")
                                play_audio("/home/agent_red/.BatShell/AudioCommander/FRZ/NetNova/alerte.mp3")
                                bring_terminal_to_foreground()
                                block_ip(ip)
                                last_alert_time = time.time()
                            ping_count = 0
                            port_scan_count = 0
            time.sleep(0.1)
    finally:
        process.terminate()

# Fonction pour surveiller les logs système via journalctl
def tail_system_logs():
    add_log_entry("Surveillance des logs système (authentification et UFW) via journalctl...")
    process = subprocess.Popen(['journalctl', '-f', '-g', 'UFW\|authentication\|Failed password'], stdout=subprocess.PIPE)
    try:
        while not stop_event.is_set():
            line = process.stdout.readline().decode('utf-8').strip()
            if line:
                add_log_entry(f"[Journal] {line}")
            time.sleep(0.1)
    finally:
        process.terminate()

# Fonction pour surveiller les activités réseau et journaux en parallèle
def monitor_multiple_logs():
    threads = [
        threading.Thread(target=detect_scan_activity),
        threading.Thread(target=tail_system_logs),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

# Fonction principale
def main():
    add_log_entry("=== NetNova Machine Security Viewer ===")
    play_audio("/home/agent_red/.BatShell/AudioCommander/FRZ/NetNova/SuperviseurNetNova.mp3")
    monitor_multiple_logs()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        add_log_entry("Programme interrompu.")
        stop_event.set()
        export_logs()
