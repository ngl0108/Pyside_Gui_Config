# ansible_config_editor/ui/dialogs.py
from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
                               QVBoxLayout, QLabel, QPlainTextEdit, QMessageBox, QComboBox)


class CredentialsDialog(QDialog):
    """SSH 인증 정보를 입력받기 위한 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SSH 인증 정보")
        layout = QFormLayout(self)
        self.username_edit = QLineEdit(self)
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("Username:", self.username_edit)
        layout.addRow("Password:", self.password_edit)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_credentials(self):
        return {'user': self.username_edit.text(), 'pass': self.password_edit.text()}


class AddDevicesDialog(QDialog):
    """여러 장비를 추가하기 위한 커스텀 대화상자"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("여러 장비 추가")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("추가할 장비의 IP 또는 호스트명을 한 줄에 하나씩 입력하세요."))
        self.text_edit = QPlainTextEdit(self)
        layout.addWidget(self.text_edit)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_devices(self):
        content = self.text_edit.toPlainText()
        return [line.strip() for line in content.splitlines() if line.strip()]


class AddInterfacesDialog(QDialog):
    """인터페이스 종류, 슬롯, 포트 범위를 입력받는 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("인터페이스 범위 추가")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.combo_type = QComboBox()
        self.combo_type.addItems(
            ["GigabitEthernet", "TenGigabitEthernet", "TwentyFiveGigE", "FortyGigabitEthernet", "FastEthernet"])
        self.le_slot = QLineEdit()
        self.le_slot.setPlaceholderText("예: 1/0")
        self.le_start_port = QLineEdit()
        self.le_start_port.setPlaceholderText("예: 1")
        self.le_end_port = QLineEdit()
        self.le_end_port.setPlaceholderText("예: 24 (단일 포트는 비워두세요)")
        form_layout.addRow("인터페이스 종류:", self.combo_type)
        form_layout.addRow("모듈/슬롯 번호:", self.le_slot)
        form_layout.addRow("시작 포트 번호:", self.le_start_port)
        form_layout.addRow("끝 포트 번호 (선택):", self.le_end_port)
        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_interfaces(self):
        if_type = self.combo_type.currentText()
        slot = self.le_slot.text()
        start_port_str = self.le_start_port.text()
        end_port_str = self.le_end_port.text()
        if not (if_type and slot and start_port_str):
            QMessageBox.warning(self, "입력 오류", "인터페이스 종류, 슬롯, 시작 포트는 필수입니다.")
            return []
        try:
            start_port = int(start_port_str)
            end_port = int(end_port_str) if end_port_str else start_port
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "포트 번호는 숫자여야 합니다.")
            return []
        if start_port > end_port:
            QMessageBox.warning(self, "입력 오류", "끝 포트 번호는 시작 포트보다 크거나 같아야 합니다.")
            return []
        return [f"{if_type}{slot}/{i}" for i in range(start_port, end_port + 1)]