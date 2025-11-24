# cisco_config_editor/main.py
import sys
import os

# 프로젝트 루트 경로를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PySide6.QtWidgets import QApplication

# 직접 경로 지정해서 임포트
sys.path.append(os.path.join(current_dir, 'ui'))
sys.path.append(os.path.join(current_dir, 'core'))

from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Cisco Config Manager")
    app.setApplicationVersion("1.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())