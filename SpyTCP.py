import os
import time
import curses
import subprocess
import psutil
from scapy.all import sniff

# Chemin des fichiers audio
AUDIO_PATH = "/home/agent_red/.BatShell/AudioCommander/FRZ/NetNova/"

# Fichiers audio
AUDIO_SNIFF = "SpyTCP.mp3"
AUDIO_TERM = "moduleterm.mp3"

# Interface réseau à utiliser pour le sniffing
INTERFACE = "enp1s0"  # Modifier avec l'interface réseau active

# Fichier temporaire pour les logs
LOG_FILE = os.path.expanduser("~/sniff_results.txt")

# Fonction pour jouer un fichier audio avec redirection des messages

def play_audio(audio_file):
    audio_path = os.path.join(AUDIO_PATH, audio_file)
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.Popen(['mpg123', '-q', audio_path], stdout=devnull, stderr=devnull).wait()
    except FileNotFoundError:
        print(f"Erreur : Le fichier audio {audio_path} est introuvable ou mpg123 n'est pas installé.")

# Fonction pour afficher le titre du module
def display_title(stdscr):
    title = "=== SPY TCP Version 0.3 ==="
    stdscr.addstr(0, curses.COLS // 2 - len(title) // 2, title, curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

# Fonction pour nettoyer l'écran
def clear_screen(stdscr):
    stdscr.clear()
    display_title(stdscr)

# Fonction pour lister les connexions réseau actives (remplace le scan Nmap)
def list_active_connections(stdscr):
    clear_screen(stdscr)
    stdscr.addstr(2, 0, "=== Ports actuellement ouverts ===\n", curses.color_pair(1) | curses.A_BOLD)

    connections = psutil.net_connections(kind='inet')
    open_ports = set()

    for conn in connections:
        if conn.status == 'LISTEN':
            open_ports.add(conn.laddr.port)

    if open_ports:
        stdscr.addstr(4, 0, f"Ports ouverts : {', '.join(map(str, sorted(open_ports)))}", curses.color_pair(1) | curses.A_BOLD)
    else:
        stdscr.addstr(4, 0, "Aucun port ouvert détecté", curses.color_pair(1) | curses.A_BOLD)

    stdscr.refresh()
    time.sleep(3)
    return sorted(open_ports)

# Fonction pour sniffer le réseau sur un port choisi
def sniff_on_port(stdscr, port):
    clear_screen(stdscr)
    play_audio(AUDIO_SNIFF)
    middle_y = curses.LINES // 2 - 5

    sniffed_packets = []

    def packet_callback(packet):
        packet_summary = packet.summary()
        sniffed_packets.append(packet_summary)
        stdscr.addstr(middle_y, 0, f"Packet: {packet_summary}\n", curses.color_pair(1) | curses.A_BOLD)
        stdscr.refresh()

    filter_str = f"tcp port {port}" if port else "tcp"

    stdscr.addstr(middle_y - 2, 0, f"[INFO] Sniffing sur le port {port}..." if port else "[INFO] Sniffing sur tous les ports...", curses.color_pair(1) | curses.A_BOLD)
    stdscr.refresh()

    try:
        sniff(filter=filter_str, iface=INTERFACE, prn=packet_callback, store=0)
    except KeyboardInterrupt:
        pass  # Gérer proprement l'interruption

    handle_sniffing_stop(sniffed_packets)

# Fonction pour gérer l'interruption et sauvegarder les logs
def handle_sniffing_stop(sniffed_packets):
    with open(LOG_FILE, 'w') as f:
        f.write("\n".join(sniffed_packets))
    print(f"Logs sauvegardés dans {LOG_FILE}")

# Fonction principale pour afficher les ports ouverts et sniffer
def scan_ports(stdscr):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)

    curses.curs_set(0)
    display_title(stdscr)

    open_ports = list_active_connections(stdscr)

    while True:
        clear_screen(stdscr)
        stdscr.addstr(2, 0, "Entrez un port à sniffer ou '0' pour tout sniffer :", curses.color_pair(1))
        stdscr.refresh()
        curses.echo()
        input_str = stdscr.getstr(3, 0).decode("utf-8").strip()
        curses.noecho()

        try:
            port = int(input_str)
            sniff_on_port(stdscr, port if port > 0 else None)
            break
        except ValueError:
            stdscr.addstr(5, 0, "Entrée invalide. Veuillez entrer un nombre valide.", curses.color_pair(1))
            stdscr.refresh()
            time.sleep(2)

    play_audio(AUDIO_TERM)

def main(stdscr):
    try:
        scan_ports(stdscr)
    except KeyboardInterrupt:
        curses.endwin()
        print("Programme interrompu par l'utilisateur.")
    finally:
        curses.curs_set(1)

if __name__ == "__main__":
    curses.wrapper(main)
