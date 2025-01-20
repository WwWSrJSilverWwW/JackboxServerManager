import os
import re
import sys
import json
import ctypes
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QLineEdit, QHBoxLayout, QVBoxLayout, QWidget, QLabel

version = 2


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal(int)

    def __init__(self, action, server_url):
        super().__init__()
        self.action = action
        self.server_url = server_url

    @staticmethod
    def find_steam_libraries():
        drives = [f"{chr(d)}:/" for d in range(65, 91) if os.path.exists(f"{chr(d)}:/")]
        steam_libraries = []
        for drive in drives:
            for root, dirs, _ in os.walk(drive):
                if "steamapps" in dirs:
                    steam_libraries.append(os.path.join(root, "steamapps"))
        return steam_libraries

    @staticmethod
    def find_game_folders(library_paths):
        game_folders = []
        game_regex = re.compile(r".*Jackbox.*", re.IGNORECASE)
        for library in library_paths:
            common_path = os.path.join(library, "common")
            if os.path.exists(common_path):
                for folder in os.listdir(common_path):
                    if game_regex.match(folder):
                        game_folders.append(os.path.join(common_path, folder))
        return game_folders

    def process_config_files(self, game_folders, add_server_url):
        count = 0
        for game_folder in game_folders:
            games_path = os.path.join(game_folder, "games")
            if not os.path.exists(games_path):
                continue

            for subfolder in os.listdir(games_path):
                config_path = os.path.join(games_path, subfolder, "jbg.config.jet")
                if os.path.isfile(config_path):
                    with open(config_path, "r", encoding="utf-8") as file:
                        try:
                            config_data = json.load(file)
                        except json.JSONDecodeError:
                            self.log_signal.emit(f"Ошибка чтения файла: {config_path}")
                            continue

                    action_message = "не изменен"
                    if add_server_url:
                        if "serverUrl" not in config_data:
                            config_data["serverUrl"] = self.server_url
                            count += 1
                            action_message = "прошит"
                    else:
                        if "serverUrl" in config_data:
                            del config_data["serverUrl"]
                            count += 1
                            action_message = "сброшен"

                    with open(config_path, "w", encoding="utf-8") as file:
                        json.dump(config_data, file, indent=4, ensure_ascii=False)

                    self.log_signal.emit(f"Обработан файл: {config_path.split('\\games\\')[-1]} ({action_message})")

        return count

    def run(self):
        self.log_signal.emit("Начало обработки...")
        steam_libraries = self.find_steam_libraries()
        game_folders = self.find_game_folders(steam_libraries)
        count = self.process_config_files(game_folders, add_server_url=(self.action == "patch"))
        self.done_signal.emit(count)


class JackboxConfigApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jackbox Server Manager")
        self.setWindowIcon(QIcon(resource_path("jbg-icon.ico")))
        self.setGeometry(100, 100, 400, 450)
        self.server_url = "rujackbox.vercel.app"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        button_layout = QHBoxLayout()

        self.server_input = QLineEdit()
        self.server_input.setText(self.server_url)

        self.patch_button = QPushButton("Прошить")
        self.patch_button.clicked.connect(self.start_patch)

        self.unpatch_button = QPushButton("Сбросить")
        self.unpatch_button.clicked.connect(self.start_unpatch)

        top_layout.addWidget(QLabel("Сервер:"))
        top_layout.addWidget(self.server_input)
        button_layout.addWidget(self.patch_button)
        button_layout.addWidget(self.unpatch_button)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.copyright = QLabel(f"© Emjoes 2025 v{version}")
        self.copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(top_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.log)
        layout.addWidget(self.copyright)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def log_message(self, message):
        self.log.append(message)

    def start_patch(self):
        self.server_url = self.server_input.text()
        self.start_worker("patch")

    def start_unpatch(self):
        self.start_worker("unpatch")

    def start_worker(self, action):
        self.patch_button.setEnabled(False)
        self.unpatch_button.setEnabled(False)
        self.log.clear()

        self.worker = WorkerThread(action, self.server_url)
        self.worker.log_signal.connect(self.log_message)
        self.worker.done_signal.connect(self.on_worker_done)
        self.worker.start()

    def on_worker_done(self, count):
        action = "Прошивка завершена" if self.worker.action == "patch" else "Сброс завершен"
        self.log_message(f"{action}. Изменено файлов: {count}")
        self.patch_button.setEnabled(True)
        self.unpatch_button.setEnabled(True)


if __name__ == "__main__":
    myappid = "mycompany.myproduct.subproduct.version"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    window = JackboxConfigApp()
    window.show()
    sys.exit(app.exec())
