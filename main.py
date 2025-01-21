import os
import re
import sys
import json
import ctypes
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, QLineEdit, QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QLabel, QFileDialog, QCheckBox)

version = 3


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal(int)

    def __init__(self, action, server_url, custom_path=None):
        super().__init__()
        self.action = action
        self.server_url = server_url
        self.custom_path = custom_path

    def find_steam_libraries(self):
        if self.custom_path is not None:
            return [os.path.join(self.custom_path, "steamapps")]

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
        self.setGeometry(100, 100, 450, 500)
        self.server_url = "rujackbox.vercel.app"
        self.custom_path = None
        self.elem_height = 28
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        grid_layout = QGridLayout()

        self.server_label = QLabel("Сервер:")
        self.server_label.setMinimumHeight(self.elem_height)

        self.server_input = QLineEdit()
        self.server_input.setText(self.server_url)
        self.server_input.setMinimumHeight(self.elem_height)

        self.auto_path_checkbox = QCheckBox("Автоматически определить путь до папки Steam (может быть дольше)")
        self.auto_path_checkbox.setChecked(False)
        self.auto_path_checkbox.stateChanged.connect(self.toggle_path_input)

        self.path_label = QLabel("Папка:")
        self.path_label.setMinimumHeight(self.elem_height)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Выберите папку Steam...")
        self.path_input.setMinimumHeight(self.elem_height)

        self.browse_button = QPushButton("...")
        self.browse_button.clicked.connect(self.browse_path)
        self.browse_button.setMinimumHeight(self.elem_height)
        self.browse_button.setMaximumWidth(40)

        grid_layout.addWidget(QLabel("Сервер:"), 0, 0)
        grid_layout.addWidget(self.server_input, 0, 1, 1, 2)

        grid_layout.addWidget(self.path_label, 1, 0)
        grid_layout.addWidget(self.path_input, 1, 1)
        grid_layout.addWidget(self.browse_button, 1, 2)

        self.patch_button = QPushButton("Прошить")
        self.patch_button.clicked.connect(self.start_patch)
        self.patch_button.setMinimumHeight(self.elem_height)

        self.unpatch_button = QPushButton("Сбросить")
        self.unpatch_button.clicked.connect(self.start_unpatch)
        self.unpatch_button.setMinimumHeight(self.elem_height)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.patch_button)
        button_layout.addWidget(self.unpatch_button)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.copyright = QLabel(f"© Emjoes 2025 v{version}")
        self.copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(grid_layout)
        layout.addWidget(self.auto_path_checkbox)
        layout.addLayout(button_layout)
        layout.addWidget(self.log)
        layout.addWidget(self.copyright)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def toggle_path_input(self):
        height = 0 if self.auto_path_checkbox.isChecked() else self.elem_height
        self.path_label.setMinimumHeight(height)
        self.path_label.setMaximumHeight(height)
        self.path_input.setMinimumHeight(height)
        self.path_input.setMaximumHeight(height)
        self.browse_button.setMinimumHeight(height)
        self.browse_button.setMaximumHeight(height)

    def browse_path(self):
        selected_path = QFileDialog.getExistingDirectory(self, "Выберите папку Steam")
        if selected_path:
            self.path_input.setText(selected_path)

    def log_message(self, message):
        self.log.append(message)

    def start_patch(self):
        self.server_url = self.server_input.text()
        self.custom_path = None if self.auto_path_checkbox.isChecked() else self.path_input.text()
        self.start_worker("patch")

    def start_unpatch(self):
        self.custom_path = None if self.auto_path_checkbox.isChecked() else self.path_input.text()
        self.start_worker("unpatch")

    def start_worker(self, action):
        self.patch_button.setEnabled(False)
        self.unpatch_button.setEnabled(False)
        self.log.clear()

        self.worker = WorkerThread(action, self.server_url, custom_path=self.custom_path)
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
