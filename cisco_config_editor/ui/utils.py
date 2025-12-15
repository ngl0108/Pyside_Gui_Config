# cisco_config_manager/ui/utils.py
from PySide6.QtGui import QUndoCommand, QColor
from PySide6.QtWidgets import QLineEdit, QComboBox, QCheckBox, QPlainTextEdit


class ConfigUndoCommand(QUndoCommand):
    """설정 변경에 대한 Undo/Redo를 처리하는 클래스"""

    def __init__(self, widget, old_value, new_value, description="Config Change"):
        super().__init__(description)
        self.widget = widget
        self.old_value = old_value
        self.new_value = new_value
        self.first_run = True

    def undo(self):
        """이전 값으로 되돌리기"""
        self._apply_value(self.old_value)

    def redo(self):
        """다시 실행하기"""
        # 명령이 처음 생성될 때는 이미 UI 값이 변경된 상태이므로 실행하지 않음
        if self.first_run:
            self.first_run = False
            return
        self._apply_value(self.new_value)

    def _apply_value(self, value):
        """위젯 타입에 따라 값을 UI에 적용"""
        if isinstance(self.widget, QLineEdit):
            self.widget.setText(value)
        elif isinstance(self.widget, QPlainTextEdit):
            self.widget.setPlainText(value)
        elif isinstance(self.widget, QComboBox):
            self.widget.setCurrentText(value)
        elif isinstance(self.widget, QCheckBox):
            self.widget.setChecked(value)


class WidgetManager:
    """위젯에 유효성 검사 및 Undo/Redo 기능을 쉽게 연결해주는 매니저"""

    def __init__(self, undo_stack):
        self.undo_stack = undo_stack

    def setup_validator(self, widget, validator_func):
        """실시간 유효성 검사 연결 (이 메서드가 없어서 에러가 났었습니다)"""
        if isinstance(widget, QLineEdit):
            # 텍스트가 변경될 때마다 _validate 메서드 호출
            widget.textChanged.connect(lambda text: self._validate(widget, text, validator_func))

    def _validate(self, widget, text, validator_func):
        """유효성 검사 수행 및 시각적 피드백 (빨간 테두리)"""
        valid, msg = validator_func(text)
        if not valid and text:  # 비어있지 않은데 유효하지 않으면 빨간 테두리
            widget.setStyleSheet("border: 2px solid red;")
            widget.setToolTip(f"오류: {msg}")
        else:
            widget.setStyleSheet("")  # 정상 복구
            widget.setToolTip("")