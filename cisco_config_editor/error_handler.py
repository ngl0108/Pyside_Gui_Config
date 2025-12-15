# cisco_config_editor/error_handler.py
import sys
import traceback
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject, Signal, QTimer, QCoreApplication


class ErrorHandler(QObject):
    """실제로 창을 띄우는 에러 핸들러"""

    # 시그널 정의 - 메인 스레드에서 실행되도록
    show_error_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.show_error_signal.connect(self._show_error_dialog)
        self.setup_global_handler()

    def setup_global_handler(self):
        """전역 예외 처리 설정"""
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """모든 예외 처리 - 실제로 창을 띄움"""
        # KeyboardInterrupt는 예외
        if exc_type == KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = str(exc_value)
        error_type = exc_type.__name__
        error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        # 콘솔에 출력 (디버깅용)
        print("\n" + "=" * 60)
        print(f"🚨 치명적 오류 발생: {error_type}")
        print(f"메시지: {error_msg}")
        print("=" * 60)

        # 로그 파일 저장
        self.save_error_log(error_type, error_msg, error_details)

        # 1. Qt 애플리케이션이 실행중인지 확인
        app = QCoreApplication.instance()

        if app:
            # Qt 애플리케이션이 실행중이면 시그널로 창 띄우기
            self.show_error_signal.emit(
                f"애플리케이션 오류 ({error_type})",
                f"다음 오류가 발생했습니다:\n\n"
                f"📛 {error_msg}\n\n"
                f"자세한 내용은 로그 파일을 확인하거나 개발자에게 문의하세요."
            )
        else:
            # Qt가 없으면 간단한 콘솔 메시지
            print("\n⚠️  Qt 애플리케이션이 없어 에러 다이얼로그를 표시할 수 없습니다.")
            print(f"오류: {error_type} - {error_msg}")

    def save_error_log(self, error_type, error_msg, error_details):
        """에러 로그 저장"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open('error_log.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"[{timestamp}] {error_type}\n")
                f.write(f"메시지: {error_msg}\n")
                f.write(f"{'=' * 60}\n")
                f.write(error_details)
                f.write("\n")

            print(f"📝 에러 로그 저장됨: error_log.txt")
        except Exception as e:
            print(f"❌ 로그 저장 실패: {e}")

    def _show_error_dialog(self, title, message):
        """실제로 에러 다이얼로그 표시 (메인 스레드에서 실행)"""
        try:
            # 활성화된 창 찾기
            app = QApplication.instance()
            if not app:
                print("❌ QApplication 인스턴스 없음")
                return

            # 가장 위에 있는 창 찾기
            top_level_windows = [w for w in app.topLevelWindows() if w.isVisible()]
            parent = top_level_windows[0] if top_level_windows else None

            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.Ok)

            # 상세 정보 버튼 추가
            detail_btn = msg_box.addButton("📋 상세 정보", QMessageBox.ActionRole)
            detail_btn.clicked.connect(lambda: self._show_details_dialog(parent))

            # 닫기 버튼
            close_btn = msg_box.addButton("✖️ 닫기", QMessageBox.ActionRole)
            close_btn.clicked.connect(msg_box.close)

            msg_box.exec()

        except Exception as e:
            print(f"❌ 에러 다이얼로그 생성 실패: {e}")

    def _show_details_dialog(self, parent):
        """상세 에러 정보 다이얼로그"""
        try:
            with open('error_log.txt', 'r', encoding='utf-8') as f:
                logs = f.read()

            # 마지막 에러 찾기
            error_blocks = logs.split('=' * 60)
            last_error = error_blocks[-2] if len(error_blocks) > 1 else "에러 로그 없음"

            dialog = QMessageBox(parent)
            dialog.setWindowTitle("오류 상세 정보")
            dialog.setIcon(QMessageBox.Information)
            dialog.setText("최근 발생한 오류의 상세 정보:")
            dialog.setDetailedText(last_error.strip())
            dialog.setStandardButtons(QMessageBox.Close)
            dialog.exec()
        except:
            QMessageBox.information(parent, "로그 없음", "에러 로그 파일을 찾을 수 없습니다.")


# 전역 인스턴스 생성
error_handler = ErrorHandler()