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


def main():
    """메인 함수"""
    # 에러 핸들러 먼저 임포트 (중요!)
    from error_handler import error_handler

    # QApplication 생성
    app = QApplication(sys.argv)
    app.setApplicationName("Cisco Config Manager")
    app.setApplicationVersion("1.0 - 오류 알림 버전")

    # 메인 윈도우 생성
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())