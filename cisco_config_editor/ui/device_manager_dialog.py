# cisco_config_manager/ui/device_manager_dialog.py
"""
장비 연결 관리 GUI
실시간 연결, 명령어 실행, 구성 배포를 위한 UI
"""

# [수정됨] QWidget 추가
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QTextEdit, QComboBox, QCheckBox, QLabel, QMessageBox,
    QHeaderView, QTabWidget, QListWidget, QSplitter,
    QProgressBar, QInputDialog, QFileDialog, QTreeWidget,
    QTreeWidgetItem, QPlainTextEdit, QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QColor, QFont, QTextCharFormat

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.device_manager import (
    ConnectionManager, DeviceInfo, DeviceType,
    ConnectionStatus, DeploymentManager
)

from datetime import datetime
from typing import List, Dict, Optional


class ConnectionWorker(QThread):
    """백그라운드 연결 작업을 위한 워커 스레드"""

    # 시그널 정의
    connection_result = Signal(str, bool, str)  # device_name, success, message
    command_result = Signal(str, bool, str)  # device_name, success, output
    status_update = Signal(str, str)  # device_name, status
    progress_update = Signal(int)  # progress percentage

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self.device_manager = connection_manager
        self.task_queue = []
        self.running = True

    def add_connection_task(self, device_name: str, password: str, enable_password: Optional[str] = None):
        """연결 작업 추가"""
        self.task_queue.append({
            'type': 'connect',
            'device_name': device_name,
            'password': password,
            'enable_password': enable_password
        })

    def add_command_task(self, device_name: str, command: str):
        """명령어 실행 작업 추가"""
        self.task_queue.append({
            'type': 'command',
            'device_name': device_name,
            'command': command
        })

    def add_deployment_task(self, device_name: str, commands: List[str]):
        """배포 작업 추가"""
        self.task_queue.append({
            'type': 'deploy',
            'device_name': device_name,
            'commands': commands
        })

    def run(self):
        """워커 스레드 실행"""
        while self.running:
            if self.task_queue:
                task = self.task_queue.pop(0)

                if task['type'] == 'connect':
                    self._handle_connection(task)
                elif task['type'] == 'command':
                    self._handle_command(task)
                elif task['type'] == 'deploy':
                    self._handle_deployment(task)

            self.msleep(100)  # 100ms 대기

    def _handle_connection(self, task):
        """연결 처리"""
        device_name = task['device_name']
        self.status_update.emit(device_name, "연결 중...")

        success = self.device_manager.connect_device(
            device_name,
            task['password'],
            task.get('enable_password')
        )

        if success:
            self.connection_result.emit(device_name, True, "연결 성공")
            self.status_update.emit(device_name, "연결됨")
        else:
            self.connection_result.emit(device_name, False, "연결 실패")
            self.status_update.emit(device_name, "연결 실패")

    def _handle_command(self, task):
        """명령어 처리"""
        device_name = task['device_name']
        success, output = self.device_manager.execute_command(
            device_name,
            task['command']
        )
        self.command_result.emit(device_name, success, output)

    def _handle_deployment(self, task):
        """배포 처리"""
        device_name = task['device_name']
        success, output = self.device_manager.deploy_config(
            device_name,
            task['commands']
        )
        self.command_result.emit(device_name, success, output)

    def stop(self):
        """워커 중지"""
        self.running = False


class DeviceManagerDialog(QDialog):
    """장비 관리 다이얼로그"""

    # 시그널 정의
    config_deployed = Signal(str, list)  # device_name, commands

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("장비 연결 관리")
        self.setMinimumSize(1000, 700)

        # 매니저 초기화
        self.device_manager = ConnectionManager()
        self.deployment_manager = DeploymentManager(self.device_manager)

        # 워커 스레드
        self.worker = ConnectionWorker(self.device_manager)
        self.worker.connection_result.connect(self._on_connection_result)
        self.worker.command_result.connect(self._on_command_result)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.start()

        self._setup_ui()
        self._load_devices()

        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_device_status)
        self.status_timer.start(5000)  # 5초마다 업데이트

    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)

        # 메인 탭
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 1. 장비 목록 탭
        self.device_tab = QWidget()
        self._setup_device_tab()
        self.tab_widget.addTab(self.device_tab, "장비 목록")

        # 2. 터미널 탭
        self.terminal_tab = QWidget()
        self._setup_terminal_tab()
        self.tab_widget.addTab(self.terminal_tab, "터미널")

        # 3. 배포 탭
        self.deployment_tab = QWidget()
        self._setup_deployment_tab()
        self.tab_widget.addTab(self.deployment_tab, "구성 배포")

        # 4. 백업/복원 탭
        self.backup_tab = QWidget()
        self._setup_backup_tab()
        self.tab_widget.addTab(self.backup_tab, "백업/복원")

        # 5. 로그 탭
        self.log_tab = QWidget()
        self._setup_log_tab()
        self.tab_widget.addTab(self.log_tab, "로그")

    def _setup_device_tab(self):
        """장비 목록 탭 설정"""
        layout = QVBoxLayout(self.device_tab)

        # 장비 추가 버튼
        button_layout = QHBoxLayout()
        self.btn_add_device = QPushButton("➕ 장비 추가")
        self.btn_remove_device = QPushButton("➖ 장비 제거")
        self.btn_edit_device = QPushButton("✏️ 편집")
        self.btn_connect = QPushButton("🔌 연결")
        self.btn_disconnect = QPushButton("❌ 연결 해제")
        self.btn_connect_all = QPushButton("🔌 모두 연결")
        self.btn_disconnect_all = QPushButton("❌ 모두 해제")

        button_layout.addWidget(self.btn_add_device)
        button_layout.addWidget(self.btn_remove_device)
        button_layout.addWidget(self.btn_edit_device)
        button_layout.addWidget(self.btn_connect)
        button_layout.addWidget(self.btn_disconnect)
        button_layout.addWidget(self.btn_connect_all)
        button_layout.addWidget(self.btn_disconnect_all)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 장비 테이블
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(7)
        self.device_table.setHorizontalHeaderLabels([
            "선택", "장비명", "IP 주소", "타입", "상태", "연결 시간", "마지막 오류"
        ])

        # QHeaderView.Stretch -> QHeaderView.ResizeMode.Stretch
        self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.device_table)

        # 버튼 연결
        self.btn_add_device.clicked.connect(self._add_device)
        self.btn_remove_device.clicked.connect(self._remove_device)
        self.btn_edit_device.clicked.connect(self._edit_device)
        self.btn_connect.clicked.connect(self._connect_device)
        self.btn_disconnect.clicked.connect(self._disconnect_device)
        self.btn_connect_all.clicked.connect(self._connect_all_devices)
        self.btn_disconnect_all.clicked.connect(self._disconnect_all_devices)

    def _setup_terminal_tab(self):
        """터미널 탭 설정"""
        layout = QVBoxLayout(self.terminal_tab)

        # 장비 선택
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("장비 선택:"))
        self.combo_terminal_device = QComboBox()
        select_layout.addWidget(self.combo_terminal_device)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        # 명령어 입력
        command_layout = QHBoxLayout()
        self.le_command = QLineEdit()
        self.le_command.setPlaceholderText("명령어 입력 (예: show running-config)")
        self.le_command.returnPressed.connect(self._execute_command)
        self.btn_execute = QPushButton("실행")
        self.btn_execute.clicked.connect(self._execute_command)

        command_layout.addWidget(self.le_command)
        command_layout.addWidget(self.btn_execute)
        layout.addLayout(command_layout)

        # 터미널 출력
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Courier", 10))
        self.terminal_output.setStyleSheet("background-color: #1e1e1e; color: #00ff00;")
        layout.addWidget(self.terminal_output)

        # 빠른 명령어 버튼
        quick_cmd_layout = QHBoxLayout()
        quick_cmd_layout.addWidget(QLabel("빠른 명령어:"))

        quick_commands = [
            "show version",
            "show running-config",
            "show interfaces status",
            "show vlan brief",
            "show ip interface brief",
            "show cdp neighbors",
            "show mac address-table"
        ]

        for cmd in quick_commands:
            btn = QPushButton(cmd)
            btn.clicked.connect(lambda checked, c=cmd: self._execute_quick_command(c))
            quick_cmd_layout.addWidget(btn)

        layout.addLayout(quick_cmd_layout)

    def _setup_deployment_tab(self):
        """배포 탭 설정"""
        layout = QVBoxLayout(self.deployment_tab)

        # 배포 대상 선택
        target_group = QGroupBox("배포 대상")
        target_layout = QVBoxLayout(target_group)

        self.deployment_device_list = QListWidget()
        self.deployment_device_list.setSelectionMode(QListWidget.MultiSelection)
        target_layout.addWidget(self.deployment_device_list)

        layout.addWidget(target_group)

        # 명령어 입력
        command_group = QGroupBox("구성 명령어")
        command_layout = QVBoxLayout(command_group)

        self.deployment_commands = QTextEdit()
        self.deployment_commands.setPlaceholderText(
            "배포할 명령어를 입력하세요.\n"
            "예:\n"
            "interface GigabitEthernet0/1\n"
            "  description Uplink to Core\n"
            "  no shutdown"
        )
        command_layout.addWidget(self.deployment_commands)

        layout.addWidget(command_group)

        # 옵션
        option_layout = QHBoxLayout()
        self.cb_backup_before_deploy = QCheckBox("배포 전 백업")
        self.cb_backup_before_deploy.setChecked(True)
        self.cb_validate_commands = QCheckBox("명령어 검증")
        self.cb_validate_commands.setChecked(True)
        self.cb_parallel_deploy = QCheckBox("병렬 배포")

        option_layout.addWidget(self.cb_backup_before_deploy)
        option_layout.addWidget(self.cb_validate_commands)
        option_layout.addWidget(self.cb_parallel_deploy)
        option_layout.addStretch()

        layout.addLayout(option_layout)

        # 배포 버튼
        deploy_button_layout = QHBoxLayout()
        self.btn_validate_only = QPushButton("검증만 수행")
        self.btn_deploy = QPushButton("🚀 배포 시작")
        self.btn_rollback = QPushButton("⏪ 롤백")

        deploy_button_layout.addWidget(self.btn_validate_only)
        deploy_button_layout.addWidget(self.btn_deploy)
        deploy_button_layout.addWidget(self.btn_rollback)
        deploy_button_layout.addStretch()

        layout.addLayout(deploy_button_layout)

        # 배포 결과
        result_group = QGroupBox("배포 결과")
        result_layout = QVBoxLayout(result_group)

        self.deployment_result = QTextEdit()
        self.deployment_result.setReadOnly(True)
        result_layout.addWidget(self.deployment_result)

        layout.addWidget(result_group)

        # 버튼 연결
        self.btn_validate_only.clicked.connect(self._validate_commands)
        self.btn_deploy.clicked.connect(self._deploy_config)
        self.btn_rollback.clicked.connect(self._rollback_config)

    def _setup_backup_tab(self):
        """백업/복원 탭 설정"""
        layout = QVBoxLayout(self.backup_tab)

        # 백업 섹션
        backup_group = QGroupBox("백업")
        backup_layout = QVBoxLayout(backup_group)

        backup_button_layout = QHBoxLayout()
        self.btn_backup_selected = QPushButton("선택 장비 백업")
        self.btn_backup_all = QPushButton("모든 장비 백업")
        self.btn_schedule_backup = QPushButton("백업 스케줄 설정")

        backup_button_layout.addWidget(self.btn_backup_selected)
        backup_button_layout.addWidget(self.btn_backup_all)
        backup_button_layout.addWidget(self.btn_schedule_backup)
        backup_button_layout.addStretch()

        backup_layout.addLayout(backup_button_layout)

        # 백업 목록
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels([
            "장비명", "백업 시간", "타입", "파일 경로", "크기"
        ])

        # QHeaderView.Stretch -> QHeaderView.ResizeMode.Stretch
        self.backup_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        backup_layout.addWidget(self.backup_table)
        layout.addWidget(backup_group)

        # 복원 섹션
        restore_group = QGroupBox("복원")
        restore_layout = QVBoxLayout(restore_group)

        restore_button_layout = QHBoxLayout()
        self.btn_restore = QPushButton("선택 백업 복원")
        self.btn_compare_backup = QPushButton("백업 비교")
        self.btn_delete_backup = QPushButton("백업 삭제")

        restore_button_layout.addWidget(self.btn_restore)
        restore_button_layout.addWidget(self.btn_compare_backup)
        restore_button_layout.addWidget(self.btn_delete_backup)
        restore_button_layout.addStretch()

        restore_layout.addLayout(restore_button_layout)
        layout.addWidget(restore_group)

        # 버튼 연결
        self.btn_backup_selected.clicked.connect(self._backup_selected)
        self.btn_backup_all.clicked.connect(self._backup_all)
        self.btn_restore.clicked.connect(self._restore_backup)

    def _setup_log_tab(self):
        """로그 탭 설정"""
        layout = QVBoxLayout(self.log_tab)

        # 로그 필터
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("필터:"))
        self.combo_log_level = QComboBox()
        self.combo_log_level.addItems(["모두", "정보", "경고", "오류"])
        filter_layout.addWidget(self.combo_log_level)

        self.le_log_search = QLineEdit()
        self.le_log_search.setPlaceholderText("검색...")
        filter_layout.addWidget(self.le_log_search)

        self.btn_clear_log = QPushButton("로그 지우기")
        filter_layout.addWidget(self.btn_clear_log)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # 로그 출력
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # 버튼 연결
        self.btn_clear_log.clicked.connect(self.log_output.clear)
        self.combo_log_level.currentTextChanged.connect(self._filter_log)
        self.le_log_search.textChanged.connect(self._filter_log)

    def _load_devices(self):
        """장비 목록 로드"""
        self.device_table.setRowCount(0)

        for device in self.device_manager.device_list:
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)

            # 체크박스
            checkbox = QCheckBox()
            self.device_table.setCellWidget(row, 0, checkbox)

            # 장비 정보
            self.device_table.setItem(row, 1, QTableWidgetItem(device.name))
            self.device_table.setItem(row, 2, QTableWidgetItem(device.host))
            self.device_table.setItem(row, 3, QTableWidgetItem(device.device_type))

            # 상태
            status_item = QTableWidgetItem("미연결")
            status_item.setForeground(QColor("gray"))
            self.device_table.setItem(row, 4, status_item)

            # 연결 시간
            self.device_table.setItem(row, 5, QTableWidgetItem(""))

            # 마지막 오류
            self.device_table.setItem(row, 6, QTableWidgetItem(""))

        self._update_combo_boxes()

    def _update_combo_boxes(self):
        """콤보박스 업데이트"""
        # 터미널 장비 선택
        self.combo_terminal_device.clear()

        # 배포 대상 목록
        self.deployment_device_list.clear()

        for device in self.device_manager.device_list:
            if self.device_manager.is_connected(device.name):
                self.combo_terminal_device.addItem(device.name)
            self.deployment_device_list.addItem(device.name)

    def _add_device(self):
        """장비 추가"""
        dialog = QDialog(self)
        dialog.setWindowTitle("장비 추가")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        le_name = QLineEdit()
        le_host = QLineEdit()
        le_username = QLineEdit()
        combo_type = QComboBox()
        combo_type.addItems([t.value for t in DeviceType])
        spin_port = QSpinBox()
        spin_port.setRange(1, 65535)
        spin_port.setValue(22)
        spin_timeout = QSpinBox()
        spin_timeout.setRange(5, 300)
        spin_timeout.setValue(30)

        layout.addRow("장비명:", le_name)
        layout.addRow("IP 주소:", le_host)
        layout.addRow("사용자명:", le_username)
        layout.addRow("장비 타입:", combo_type)
        layout.addRow("포트:", spin_port)
        layout.addRow("타임아웃(초):", spin_timeout)

        # 버튼
        button_layout = QHBoxLayout()
        btn_ok = QPushButton("추가")
        btn_cancel = QPushButton("취소")
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addRow(button_layout)

        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)

        # QDialog.Accepted -> QDialog.DialogCode.Accepted
        if dialog.exec() == QDialog.DialogCode.Accepted:
            device = DeviceInfo(
                name=le_name.text(),
                host=le_host.text(),
                username=le_username.text(),
                password="",  # 연결 시 입력
                device_type=combo_type.currentText(),
                port=spin_port.value(),
                timeout=spin_timeout.value()
            )

            if self.device_manager.add_device(device):
                self._load_devices()
                self._log(f"장비 추가됨: {device.name}")
            else:
                QMessageBox.warning(self, "경고", "장비 추가 실패")

    def _remove_device(self):
        """장비 제거"""
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.warning(self, "경고", "제거할 장비를 선택하세요.")
            return

        # QMessageBox.Yes/No -> QMessageBox.StandardButton.Yes/No
        reply = QMessageBox.question(
            self, "확인",
            f"{len(selected_devices)}개 장비를 제거하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for device_name in selected_devices:
                self.device_manager.remove_device(device_name)
                self._log(f"장비 제거됨: {device_name}")
            self._load_devices()

    def _edit_device(self):
        """장비 편집"""
        # 구현 필요
        pass

    def _connect_device(self):
        """선택 장비 연결"""
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.warning(self, "경고", "연결할 장비를 선택하세요.")
            return

        for device_name in selected_devices:
            # 비밀번호 입력
            password, ok = QInputDialog.getText(
                self, f"{device_name} 연결",
                f"{device_name} 비밀번호:",
                QLineEdit.Password
            )

            if ok and password:
                # Enable 비밀번호 (선택사항)
                enable_password, ok = QInputDialog.getText(
                    self, f"{device_name} 연결",
                    f"{device_name} Enable 비밀번호 (선택사항):",
                    QLineEdit.Password
                )

                if not ok:
                    enable_password = None

                # 백그라운드에서 연결
                self.worker.add_connection_task(device_name, password, enable_password)
                self._log(f"연결 시도 중: {device_name}")

    def _disconnect_device(self):
        """선택 장비 연결 해제"""
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.warning(self, "경고", "해제할 장비를 선택하세요.")
            return

        for device_name in selected_devices:
            self.device_manager.disconnect_device(device_name)
            self._log(f"연결 해제됨: {device_name}")

        self._update_device_status()

    def _connect_all_devices(self):
        """모든 장비 연결"""
        # 구현 필요
        pass

    def _disconnect_all_devices(self):
        """모든 장비 연결 해제"""
        self.device_manager.disconnect_all()
        self._log("모든 장비 연결 해제됨")
        self._update_device_status()

    def _execute_command(self):
        """명령어 실행"""
        device_name = self.combo_terminal_device.currentText()
        command = self.le_command.text()

        if not device_name or not command:
            return

        self.terminal_output.appendPlainText(f"\n> {command}\n")
        self.worker.add_command_task(device_name, command)
        self.le_command.clear()

    def _execute_quick_command(self, command):
        """빠른 명령어 실행"""
        self.le_command.setText(command)
        self._execute_command()

    def _validate_commands(self):
        """명령어 검증"""
        commands = self.deployment_commands.toPlainText().strip().split('\n')
        valid, errors = self.deployment_manager.validate_commands(commands)

        if valid:
            self.deployment_result.append("✅ 명령어 검증 성공\n")
        else:
            self.deployment_result.append("❌ 명령어 검증 실패:\n")
            for error in errors:
                self.deployment_result.append(f"  - {error}\n")

    def _deploy_config(self):
        """구성 배포"""
        selected_items = self.deployment_device_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "배포할 장비를 선택하세요.")
            return

        commands = self.deployment_commands.toPlainText().strip().split('\n')
        if not commands or not commands[0]:
            QMessageBox.warning(self, "경고", "배포할 명령어를 입력하세요.")
            return

        # 검증
        if self.cb_validate_commands.isChecked():
            valid, errors = self.deployment_manager.validate_commands(commands)
            if not valid:
                # QMessageBox.Yes/No -> QMessageBox.StandardButton.Yes/No
                reply = QMessageBox.warning(
                    self, "경고",
                    "명령어 검증 실패. 계속하시겠습니까?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        # 배포 시작
        self.deployment_result.clear()
        self.deployment_result.append(f"배포 시작: {datetime.now()}\n")
        self.deployment_result.append(f"대상 장비: {len(selected_items)}대\n")
        self.deployment_result.append("=" * 50 + "\n")

        for item in selected_items:
            device_name = item.text()

            if not self.device_manager.is_connected(device_name):
                self.deployment_result.append(f"❌ {device_name}: 미연결\n")
                continue

            # 백그라운드 배포
            self.worker.add_deployment_task(device_name, commands)
            self.deployment_result.append(f"⏳ {device_name}: 배포 중...\n")

        # 시그널 발생
        for item in selected_items:
            self.config_deployed.emit(item.text(), commands)

    def _rollback_config(self):
        """구성 롤백"""
        selected_items = self.deployment_device_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "롤백할 장비를 선택하세요.")
            return

        # QMessageBox.Yes/No -> QMessageBox.StandardButton.Yes/No
        reply = QMessageBox.question(
            self, "확인",
            "선택한 장비의 마지막 변경을 롤백하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                device_name = item.text()
                result = self.deployment_manager.rollback(device_name)

                if result['success']:
                    self._log(f"✅ {device_name}: 롤백 성공")
                else:
                    self._log(f"❌ {device_name}: 롤백 실패 - {result['message']}")

    def _backup_selected(self):
        """선택 장비 백업"""
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.warning(self, "경고", "백업할 장비를 선택하세요.")
            return

        for device_name in selected_devices:
            if self.device_manager.is_connected(device_name):
                connection = self.device_manager.get_connection(device_name)
                backup = connection.backup_config()

                if backup:
                    self._log(f"✅ {device_name}: 백업 완료")
                    self._add_backup_to_table(backup)
                else:
                    self._log(f"❌ {device_name}: 백업 실패")
            else:
                self._log(f"⚠️ {device_name}: 미연결 상태")

    def _backup_all(self):
        """모든 장비 백업"""
        results = self.device_manager.backup_all_devices()

        for device_name, backup in results.items():
            if backup:
                self._log(f"✅ {device_name}: 백업 완료")
                self._add_backup_to_table(backup)
            else:
                self._log(f"❌ {device_name}: 백업 실패")

    def _restore_backup(self):
        """백업 복원"""
        # 구현 필요
        pass

    def _add_backup_to_table(self, backup):
        """백업 테이블에 추가"""
        row = self.backup_table.rowCount()
        self.backup_table.insertRow(row)

        self.backup_table.setItem(row, 0, QTableWidgetItem(backup.device_name))
        self.backup_table.setItem(row, 1, QTableWidgetItem(backup.timestamp))
        self.backup_table.setItem(row, 2, QTableWidgetItem("Running"))
        self.backup_table.setItem(row, 3, QTableWidgetItem(backup.file_path))

        # 파일 크기
        try:
            size = os.path.getsize(backup.file_path)
            size_str = f"{size:,} bytes"
            self.backup_table.setItem(row, 4, QTableWidgetItem(size_str))
        except:
            self.backup_table.setItem(row, 4, QTableWidgetItem("N/A"))

    def _get_selected_devices(self) -> List[str]:
        """선택된 장비 목록 반환"""
        selected = []
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                device_name = self.device_table.item(row, 1).text()
                selected.append(device_name)
        return selected

    def _update_device_status(self):
        """장비 상태 업데이트"""
        for row in range(self.device_table.rowCount()):
            device_name = self.device_table.item(row, 1).text()
            status = self.device_manager.get_device_status(device_name)

            # 상태 업데이트
            status_item = self.device_table.item(row, 4)
            if status['connected']:
                status_item.setText("연결됨")
                status_item.setForeground(QColor("green"))
            else:
                status_item.setText("미연결")
                status_item.setForeground(QColor("gray"))

            # 마지막 오류
            if status.get('last_error'):
                self.device_table.item(row, 6).setText(status['last_error'])

        self._update_combo_boxes()

    def _on_connection_result(self, device_name: str, success: bool, message: str):
        """연결 결과 처리"""
        self._log(f"{device_name}: {message}")
        self._update_device_status()

    def _on_command_result(self, device_name: str, success: bool, output: str):
        """명령어 결과 처리"""
        if success:
            self.terminal_output.appendPlainText(output)
        else:
            self.terminal_output.appendPlainText(f"오류: {output}")

        # 배포 결과 업데이트
        if "배포" in output or "deploy" in output.lower():
            status = "✅" if success else "❌"
            self.deployment_result.append(f"{status} {device_name}: 완료\n")

    def _on_status_update(self, device_name: str, status: str):
        """상태 업데이트 처리"""
        self._log(f"{device_name}: {status}")

    def _filter_log(self):
        """로그 필터링"""
        # 구현 필요
        pass

    def _log(self, message: str):
        """로그 추가"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_output.append(log_entry)

    def closeEvent(self, event):
        """다이얼로그 종료 시"""
        self.worker.stop()
        self.worker.wait()
        self.device_manager.disconnect_all()
        event.accept()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = DeviceManagerDialog()
    dialog.show()
    sys.exit(app.exec())