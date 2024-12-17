import sys
from PyQt5.QtWidgets import QOpenGLWidget, QApplication, QMainWindow, QVBoxLayout, QPushButton, QLineEdit, QWidget, QFileDialog
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import hashlib

class CrackerThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, wordlist_file, hash_input, parent=None):
        super(CrackerThread, self).__init__(parent)
        self.wordlist_file = wordlist_file
        self.hash_input = hash_input

    def run(self):
        try:
            with open(self.wordlist_file, 'r', errors='ignore') as file:
                for line in file:
                    word = line.strip()
                    hashed_word = hashlib.md5(word.encode()).hexdigest()
                    if hashed_word == self.hash_input:
                        self.update_signal.emit(f"Mot de passe trouvé : {word}")
                        return

                    # Ajout d'une petite pause pour laisser respirer le système
                    QThread.msleep(1)

            self.update_signal.emit("Mot de passe non trouvé.")

        except FileNotFoundError:
            self.update_signal.emit("Wordlist file not found.")
        except Exception as e:
            self.update_signal.emit(f"Erreur : {str(e)}")

class MyOpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(MyOpenGLWidget, self).__init__(parent)
        self.rot_y = 0
        self.rot_x_cube = 0
        self.text = "En Cours"

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_rotation)
        self.timer.start(16)

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink_text)
        self.blink_timer.start(500)

        self.is_text_visible = True

    def initializeGL(self):
        glutInit(sys.argv)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 1, 100)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        glPushMatrix()
        glRotatef(self.rot_y, 0, 1, 0)
        self.draw_rotating_cube()
        glPopMatrix()

        glPushMatrix()
        self.draw_rotating_cube_x()
        glPopMatrix()

        self.draw_fixed_text()

    def draw_rotating_cube(self):
        size = 1.5
        glutWireCube(size)

    def draw_rotating_cube_x(self):
        size = 1.5
        glPushMatrix()
        glRotatef(self.rot_x_cube, 1, 0, 0)
        glutWireCube(size)
        glPopMatrix()

    def draw_fixed_text(self):
        if self.is_text_visible:
            glPushMatrix()
            self.draw_text_on_cube()
            glPopMatrix()

    def draw_text_on_cube(self):
        # Affiche le texte au centre de la fenêtre sans rotation
        glColor3f(0.0, 1.0, 0.0)  # Couleur du texte en vert
        glRasterPos3f(-0.5, 0, -1.7)  # Position fixe du texte
        for char in self.text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    def update_rotation(self):
        self.rot_y += 0.9
        self.rot_x_cube += 0.9
        self.update()

    def blink_text(self):
        self.is_text_visible = not self.is_text_visible
        self.update()

class InterfaceSelection(QMainWindow):
    def __init__(self):
        super(InterfaceSelection, self).__init__()

        self.setWindowTitle('Interface de Sélection')
        self.setGeometry(100, 100, 400, 200)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.wordlist_file = ""
        self.hash_input = ""

        btn_wordlist = QPushButton("Sélectionner Wordlist", self)
        btn_wordlist.clicked.connect(self.select_wordlist)
        layout.addWidget(btn_wordlist)

        self.txt_hash = QLineEdit(self)
        self.txt_hash.setPlaceholderText("Entrer le hash")
        layout.addWidget(self.txt_hash)

        btn_start_crack = QPushButton("Démarrer le Crack", self)
        btn_start_crack.clicked.connect(self.start_crack)
        layout.addWidget(btn_start_crack)

        central_widget.setLayout(layout)

    def select_wordlist(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        wordlist_file, _ = QFileDialog.getOpenFileName(self, "Sélectionner Wordlist", "", "Text Files (*.txt);;All Files (*)", options=options)
        if wordlist_file:
            print(f"Wordlist sélectionnée : {wordlist_file}")
            self.wordlist_file = wordlist_file

    def start_crack(self):
        self.hash_input = self.txt_hash.text()
        if not self.wordlist_file or not self.hash_input:
            print("Veuillez sélectionner la wordlist et entrer le hash.")
            return

        print(f"Hash sélectionné : {self.hash_input}")
        print("Démarrer le crack avec la wordlist...")

        self.interface_cubes = InterfaceCubes(self.wordlist_file, self.hash_input)
        self.interface_cubes.show()
        self.close()

class InterfaceCubes(QMainWindow):
    def __init__(self, wordlist_file, hash_input):
        super(InterfaceCubes, self).__init__()

        self.setWindowTitle('Interface des Cubes')
        self.setGeometry(100, 100, 800, 600)

        central_widget = MyOpenGLWidget(self)
        self.setCentralWidget(central_widget)

        self.cracker_thread = CrackerThread(wordlist_file, hash_input)
        self.cracker_thread.update_signal.connect(self.handle_cracker_update)
        self.cracker_thread.start()

        # Baisser la priorité du thread de cracking pour ne pas ralentir l'interface
        self.cracker_thread.setPriority(QThread.LowPriority)

    def handle_cracker_update(self, status):
        print(status)
        if status.startswith("Mot de passe trouvé"):
            # Extraire le mot de passe trouvé du message et l'afficher
            password = status.split(": ")[1]
            self.centralWidget().text = f"Mot de passe : {password}"
            self.centralWidget().is_text_visible = True  # Afficher le texte
            self.centralWidget().blink_timer.stop()  # Arrêter le clignotement
        else:
            self.centralWidget().text = status
        self.centralWidget().update()


def main():
    app = QApplication(sys.argv)
    interface_selection = InterfaceSelection()
    interface_selection.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
