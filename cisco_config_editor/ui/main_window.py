# cisco_config_manager/ui/main_window.py
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu,
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QVBoxLayout, QWidget, QTextEdit, QSplitter,
    QDockWidget, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QPlainTextEdit, QInputDialog, QListWidget, QListWidgetItem, QTableWidgetItem,
    QDialog, QComboBox, QPushButton, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout, QDialogButtonBox, QStyle
)
from PySide6.QtGui import QUndoStack, QUndoCommand, QAction, QKeySequence, QIcon, QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt, QTimer, Signal, QSettings

# 탭 모듈들
from .tabs.interface_tab import InterfaceTab
from .tabs.vlan_tab import VlanTab
from .tabs.routing_tab import RoutingTab
from .tabs.switching_tab import SwitchingTab
from .tabs.security_tab import SecurityTab
from .tabs.acl_tab import AclTab
from .tabs.global_tab import GlobalTab
from .tabs.ha_tab import HaTab

# Core 모듈 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.device_manager import CiscoCommandGenerator
from core.network_utils import CLIAnalyzer
from core.config_manager import ConfigDiff
from core.device_manager import ConnectionManager
from core.network_utils import (
    NetworkValidator, VlanValidator, InterfaceValidator,
    SecurityValidator, RoutingValidator, PortValidator, HostnameValidator
)
from core.config_manager import ConfigTemplate, BuiltInTemplates
from core.config_manager import BackupScheduler
from core.utils import app_logger

# UI 모듈들
from .dialogs import (
    InterfaceDialog, VlanDialog, AclDialog, AceDialog,
    StaticRouteDialog, DnsServerDialog, NtpServerDialog
)
from .device_manager_dialog import DeviceManagerDialog


# --- 템플릿 저장 다이얼로그 (main_window.py에 포함) ---
class TemplateInputDialog(QDialog):
    """템플릿 이름, 설명, 카테고리를 입력받는 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("템플릿 정보 입력")
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("예: 표준_L3_코어")
        self.layout.addRow("템플릿 이름:", self.name_input)

        self.desc_input = QLineEdit()
        self.layout.addRow("설명:", self.desc_input)

        self.category_input = QLineEdit("User")
        self.layout.addRow("카테고리:", self.category_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_data(self):
        return (
            self.name_input.text(),
            self.desc_input.text(),
            self.category_input.text()
        )


# --- End TemplateInputDialog ---


class ConfigCommand(QUndoCommand):
    """구성 변경을 위한 Undo/Redo 명령"""

    def __init__(self, widget, old_value, new_value, description):
        super().__init__(description)
        self.widget = widget
        self.old_value = old_value
        self.new_value = new_value

    def undo(self):
        self.widget.setText(self.old_value)

    def redo(self):
        self.widget.setText(self.new_value)


class MainWindow(QMainWindow):
    # 시그널 정의
    config_changed = Signal()

    def __init__(self):
        super().__init__()
        self.current_file_path = None
        self.is_modified = False

        app_logger.log_info("애플리케이션 시작됨")

        # 핵심 매니저 초기화 - 변수명 명확히 구분
        self.command_generator = CiscoCommandGenerator()  # 명령어 생성기
        self.network_utils = CLIAnalyzer()  # CLI 분석기
        self.connection_manager = ConnectionManager()  # 장비 연결 관리기 (변수명 변경!)
        self.template_manager = ConfigTemplate()

        self.config_manager = BackupScheduler(self.connection_manager)  # connection_manager 사용
        self.config_manager.set_callback(self._on_scheduler_log)
        self.config_manager.start()

        self.original_config = {}

        # Undo/Redo 스택
        self.undo_stack = QUndoStack(self)

        # 설정 관리
        self.settings = QSettings("CiscoTools", "ConfigManager")

        # 최근 파일 목록
        self.recent_files = []
        self.max_recent_files = 5

        self._setup_ui()
        self._connect_signals()
        self._connect_tab_signals()
        self._load_settings()
        self._update_device_combo()
        self._update_status("준비됨 - 장비를 선택하거나 추가하세요.")

    def _setup_ui(self):
        """UI 초기화 및 설정"""
        self.setWindowTitle("Cisco Config Manager - 장비 중심 관리")
        self.setGeometry(100, 100, 1500, 900)

        # 1. 상단 장비 제어 패널
        self._setup_device_control_bar()

        # 2. 메인 화면 분할
        main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(main_splitter)

        # 좌측 패널 (구성 트리)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        left_layout.addWidget(QLabel("현재 구성 요약"))

        # 검색 필드
        search_layout = QHBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("설정 항목 검색...")
        search_button = QPushButton("검색")
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(search_button)
        left_layout.addLayout(search_layout)

        # 구성 트리
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabel("Configuration Tree")
        left_layout.addWidget(self.config_tree)

        main_splitter.addWidget(left_panel)

        # 중앙 패널 (탭)
        central_panel = QWidget()
        central_layout = QVBoxLayout(central_panel)
        central_layout.setContentsMargins(0, 0, 0, 0)

        # 메인 탭 위젯
        self.tab_widget = QTabWidget()
        central_layout.addWidget(self.tab_widget)

        # 탭 생성 (Undo Stack 전달)
        self.interface_tab = InterfaceTab(self.undo_stack)
        self.vlan_tab = VlanTab(self.undo_stack)
        self.global_tab = GlobalTab(self.undo_stack)
        self.routing_tab = RoutingTab(self.undo_stack)
        self.switching_tab = SwitchingTab(self.undo_stack)
        self.security_tab = SecurityTab(self.undo_stack)
        self.acl_tab = AclTab(self.undo_stack)
        self.ha_tab = HaTab(self.undo_stack)

        self.tab_widget.addTab(self.interface_tab, "🔌 인터페이스")
        self.tab_widget.addTab(self.vlan_tab, "🏷️ VLAN")
        self.tab_widget.addTab(self.global_tab, "🌐 기본 설정")
        self.tab_widget.addTab(self.routing_tab, "🛣️ 라우팅")
        self.tab_widget.addTab(self.switching_tab, "🔀 스위칭")
        self.tab_widget.addTab(self.security_tab, "🔒 보안")
        self.tab_widget.addTab(self.acl_tab, "🛡️ ACL")
        self.tab_widget.addTab(self.ha_tab, "⚡ HA")

        main_splitter.addWidget(central_panel)

        # 우측 패널 (미리보기) - 다크 테마 적용
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        right_layout.addWidget(QLabel("📝 생성될 명령어 (Preview)"))
        self.command_preview = QPlainTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setStyleSheet(
            "background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 10pt;")
        right_layout.addWidget(self.command_preview)

        right_layout.addWidget(QLabel("✅ 유효성 검사"))
        self.validation_output = QPlainTextEdit()
        self.validation_output.setReadOnly(True)
        self.validation_output.setMaximumHeight(150)
        self.validation_output.setStyleSheet(
            "background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 10pt;")
        right_layout.addWidget(self.validation_output)

        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([200, 800, 300])

        self._setup_menubar()
        self._setup_statusbar()

    def _setup_device_control_bar(self):
        toolbar = QToolBar("Device Control")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        toolbar.addWidget(QLabel("  대상 장비: "))
        self.combo_devices = QComboBox()
        self.combo_devices.setMinimumWidth(200)
        self.combo_devices.addItem("-- 장비 선택 --")
        toolbar.addWidget(self.combo_devices)

        btn_manage = QPushButton(" 장비 관리 ")
        btn_manage.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        btn_manage.clicked.connect(self._open_device_manager)
        toolbar.addWidget(btn_manage)

        toolbar.addSeparator()

        self.btn_pull_config = QPushButton(" 📥 현재 설정 가져오기 (Pull) ")
        self.btn_pull_config.setStyleSheet("font-weight: bold; color: blue;")
        self.btn_pull_config.clicked.connect(self._pull_config_from_device)
        toolbar.addWidget(self.btn_pull_config)

        toolbar.addSeparator()

        self.btn_push_config = QPushButton(" 🚀 설정 장비에 적용 (Push) ")
        self.btn_push_config.setStyleSheet("font-weight: bold; color: darkred;")
        self.btn_push_config.clicked.connect(self._deploy_current_config)
        toolbar.addWidget(self.btn_push_config)

    def _setup_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("파일")

        new_action = QAction("새 구성", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_config)
        file_menu.addAction(new_action)

        open_action = QAction("열기", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_config)
        file_menu.addAction(open_action)

        save_action = QAction("저장", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        save_as_action = QAction("다른 이름으로 저장", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._save_config_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        self.recent_files_menu = file_menu.addMenu("최근 파일")
        self._update_recent_files_menu()

        # 설정 메뉴
        file_menu.addSeparator()
        settings_menu = file_menu.addMenu("설정")
        backup_settings_action = QAction("자동 백업 설정", self)
        backup_settings_action.triggered.connect(self._open_backup_settings)
        settings_menu.addAction(backup_settings_action)

        file_menu.addSeparator()
        exit_action = QAction("종료", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 편집 메뉴
        edit_menu = menubar.addMenu("편집")
        undo_action = QAction("실행 취소", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo_stack.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("다시 실행", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.undo_stack.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()
        find_action = QAction("찾기", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self._show_find_dialog)
        edit_menu.addAction(find_action)

        edit_menu.addSeparator()
        compare_action = QAction("구성 비교", self)
        compare_action.setShortcut("Ctrl+D")
        compare_action.triggered.connect(self._compare_configs)
        edit_menu.addAction(compare_action)

        # 도구 메뉴
        tools_menu = menubar.addMenu("도구")
        generate_commands_action = QAction("명령어 생성", self)
        generate_commands_action.setShortcut("F5")
        generate_commands_action.triggered.connect(self._generate_commands)
        tools_menu.addAction(generate_commands_action)

        analyze_action = QAction("구성 분석", self)
        analyze_action.setShortcut("F6")
        analyze_action.triggered.connect(self._analyze_config)
        tools_menu.addAction(analyze_action)

        validate_action = QAction("구성 검증", self)
        validate_action.setShortcut("F7")
        validate_action.triggered.connect(self._validate_config)
        tools_menu.addAction(validate_action)

        tools_menu.addSeparator()
        device_manager_action = QAction("장비 연결 관리", self)
        device_manager_action.setShortcut("F8")
        device_manager_action.triggered.connect(self._open_device_manager)
        tools_menu.addAction(device_manager_action)

        deploy_action = QAction("현재 구성 배포", self)
        deploy_action.setShortcut("F9")
        deploy_action.triggered.connect(self._deploy_current_config)
        tools_menu.addAction(deploy_action)

        tools_menu.addSeparator()
        topology_action = QAction("네트워크 토폴로지", self)
        topology_action.setShortcut("F10")
        topology_action.triggered.connect(self._open_topology_viewer)
        tools_menu.addAction(topology_action)

        dashboard_action = QAction("실시간 대시보드", self)
        dashboard_action.setShortcut("F11")
        dashboard_action.triggered.connect(self._open_dashboard)
        tools_menu.addAction(dashboard_action)

        # 템플릿 메뉴 [⭐ 수정 및 추가]
        template_menu = menubar.addMenu("템플릿")

        template_manager_action = QAction("템플릿 관리자 열기", self)
        template_manager_action.triggered.connect(self._manage_templates)
        template_menu.addAction(template_manager_action)

        template_menu.addSeparator()

        save_as_template_action = QAction("현재 구성을 템플릿으로 저장...", self)
        save_as_template_action.triggered.connect(self._save_current_config_as_template)
        template_menu.addAction(save_as_template_action)

        # 보기 메뉴
        view_menu = menubar.addMenu("보기")
        tree_action = QAction("구성 트리", self)
        tree_action.setCheckable(True)
        tree_action.setChecked(True)
        tree_action.triggered.connect(self._toggle_config_tree)
        view_menu.addAction(tree_action)

        preview_action = QAction("명령어 미리보기", self)
        preview_action.setCheckable(True)
        preview_action.setChecked(True)
        preview_action.triggered.connect(self._toggle_preview)
        view_menu.addAction(preview_action)

        view_menu.addSeparator()
        refresh_action = QAction("새로고침", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_view)
        view_menu.addAction(refresh_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        help_action = QAction("도움말", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()
        about_action = QAction("정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_statusbar(self):
        self.status_bar = self.statusBar()
        self.status_label = QLabel("준비됨")
        self.status_bar.addWidget(self.status_label)

        self.modified_label = QLabel("")
        self.status_bar.addPermanentWidget(self.modified_label)

        self.file_label = QLabel("새 파일")
        self.status_bar.addPermanentWidget(self.file_label)

        self.time_label = QLabel("")
        self.status_bar.addPermanentWidget(self.time_label)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)

    def _connect_signals(self):
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.search_field.returnPressed.connect(self._search_config)
        self.config_changed.connect(self._on_config_changed)

    def _connect_tab_signals(self):
        # Interface Tab
        if hasattr(self.interface_tab, 'btn_add_interface'):
            self.interface_tab.btn_add_interface.clicked.connect(self._add_interface)
            self.interface_tab.btn_remove_interface.clicked.connect(self._remove_interface)
            self.interface_tab.interface_list.itemSelectionChanged.connect(self._on_interface_selected)

        # VLAN Tab
        if hasattr(self.vlan_tab, 'btn_add_vlan'):
            self.vlan_tab.btn_add_vlan.clicked.connect(self._add_vlan)
            self.vlan_tab.btn_remove_vlan.clicked.connect(self._remove_vlan)

        # ACL Tab
        if hasattr(self.acl_tab, 'btn_add_acl'):
            self.acl_tab.btn_add_acl.clicked.connect(self._add_acl)
            self.acl_tab.btn_remove_acl.clicked.connect(self._remove_acl)
            self.acl_tab.btn_add_rule.clicked.connect(self._add_ace)
            self.acl_tab.btn_remove_rule.clicked.connect(self._remove_ace)

        # Routing Tab
        if hasattr(self.routing_tab, 'btn_add_static_route'):
            self.routing_tab.btn_add_static_route.clicked.connect(self._add_static_route)
            self.routing_tab.btn_remove_static_route.clicked.connect(self._remove_static_route)

        # Global Tab
        if hasattr(self.global_tab, 'btn_add_dns'):
            self.global_tab.btn_add_dns.clicked.connect(self._add_dns_server)
            self.global_tab.btn_remove_dns.clicked.connect(self._remove_dns_server)
            self.global_tab.btn_add_ntp.clicked.connect(self._add_ntp_server)
            self.global_tab.btn_remove_ntp.clicked.connect(self._remove_ntp_server)

    def _update_device_combo(self):
        """장비 콤보박스 업데이트"""
        current_text = self.combo_devices.currentText()
        self.combo_devices.clear()
        self.combo_devices.addItem("-- 장비 선택 --")

        for device in self.connection_manager.device_list:  # connection_manager 사용
            self.combo_devices.addItem(f"{device.name} ({device.host})", device.name)

        index = self.combo_devices.findText(current_text)
        if index >= 0:
            self.combo_devices.setCurrentIndex(index)

    def _open_device_manager(self):
        dialog = DeviceManagerDialog(self)
        dialog.exec()
        self._update_device_combo()

    def _pull_config_from_device(self):
        if self.combo_devices.currentIndex() <= 0:
            QMessageBox.warning(self, "경고", "설정을 가져올 장비를 먼저 선택하세요.")
            return

        device_name = self.combo_devices.currentData()
        password, ok = QInputDialog.getText(self, "장비 연결", f"{device_name} 접속 비밀번호:", QLineEdit.Password)
        if not ok or not password:
            return

        self._update_status(f"{device_name}에 연결 중...")
        app_logger.log_info(f"장비 연결 시도: {device_name}")

        if self.connection_manager.connect_device(device_name, password):  # connection_manager 사용
            try:
                self._update_status("설정(show run) 가져오는 중...")
                connection = self.connection_manager.get_connection(device_name)  # connection_manager 사용

                cli_output = connection.get_running_config()
                vlan_output = connection.send_command("show vlan brief")

                self._update_status("설정 분석 중...")

                command_outputs = {
                    'show run': cli_output,
                    'show vlan': vlan_output
                }

                config_data = self.network_utils.analyze_multiple_commands(command_outputs)
                self._load_config_to_ui(config_data)

                self.original_config = config_data.copy()
                self.is_modified = False

                QMessageBox.information(self, "성공", f"{device_name}의 설정을 성공적으로 불러왔습니다.")
                self._update_status(f"{device_name} 설정 로드 완료")
                self._update_config_tree()
                app_logger.log_info(f"장비 설정 로드 성공: {device_name}")

            except Exception as e:
                app_logger.log_error(f"장비 설정 로드 실패: {str(e)}")
                QMessageBox.critical(self, "오류", f"설정 가져오기 실패: {str(e)}")
        else:
            app_logger.log_error(f"장비 연결 실패: {device_name}")
            QMessageBox.critical(self, "연결 실패", f"{device_name}에 연결할 수 없습니다.")
            self._update_status("연결 실패")

    def _load_config_to_ui(self, config: Dict):
        self._clear_all_tabs()

        # Global
        if 'global' in config:
            g = config['global']
            if hasattr(self, 'global_tab'):
                self.global_tab.le_hostname.setText(g.get('hostname', ''))
                self.global_tab.le_domain_name.setText(g.get('domain_name', ''))
                self.global_tab.cb_service_timestamps.setChecked(g.get('service_timestamps', True))
                for dns in g.get('dns_servers', []):
                    row = self.global_tab.dns_table.rowCount()
                    self.global_tab.dns_table.insertRow(row)
                    self.global_tab.dns_table.setItem(row, 0, QTableWidgetItem(dns.get('ip', '')))
                    self.global_tab.dns_table.setItem(row, 1, QTableWidgetItem(dns.get('vrf', '')))

        # Interfaces
        if 'interfaces' in config:
            for iface in config['interfaces']:
                self.interface_tab.interface_list.addItem(iface.get('name', ''))

        # VLAN
        if 'vlans' in config:
            vlans = config['vlans'] if isinstance(config['vlans'], list) else config['vlans'].get('list', [])
            for vlan in vlans:
                row = self.vlan_tab.vlan_table.rowCount()
                self.vlan_tab.vlan_table.insertRow(row)
                self.vlan_tab.vlan_table.setItem(row, 0, QTableWidgetItem(str(vlan.get('id', ''))))
                self.vlan_tab.vlan_table.setItem(row, 1, QTableWidgetItem(vlan.get('name', '')))
                self.vlan_tab.vlan_table.setItem(row, 2, QTableWidgetItem(vlan.get('description', '')))

        # Routing
        if 'static_routes' in config:
            for route in config['static_routes']:
                row = self.routing_tab.static_route_table.rowCount()
                self.routing_tab.static_route_table.insertRow(row)
                self.routing_tab.static_route_table.setItem(row, 0, QTableWidgetItem(
                    f"{route.get('network')}/{route.get('mask')}"))
                self.routing_tab.static_route_table.setItem(row, 1, QTableWidgetItem(route.get('next_hop', '')))
                self.routing_tab.static_route_table.setItem(row, 2, QTableWidgetItem(str(route.get('metric', 1))))
                self.routing_tab.static_route_table.setItem(row, 3, QTableWidgetItem(route.get('vrf', '')))

        # Security
        if 'security' in config:
            sec = config['security']
            for user in sec.get('users', []):
                row = self.security_tab.users_table.rowCount()
                self.security_tab.users_table.insertRow(row)
                self.security_tab.users_table.setItem(row, 0, QTableWidgetItem(user.get('username', '')))
                self.security_tab.users_table.setItem(row, 1, QTableWidgetItem(str(user.get('privilege', ''))))

        self._update_config_tree()

    def _deploy_current_config(self):
        commands = self._generate_commands(show_only=True)
        if not commands:
            QMessageBox.information(self, "알림", "변경할 사항이 없습니다.")
            return

        device_name = self.combo_devices.currentData()
        if not device_name:
            QMessageBox.warning(self, "경고", "장비를 선택하세요.")
            return

        app_logger.log_info(f"구성 배포 시도: {device_name}")
        dialog = DeviceManagerDialog(self)
        dialog.tab_widget.setCurrentIndex(2)
        dialog.deployment_commands.setPlainText('\n'.join(commands))
        dialog.exec()

    # --- CRUD Helper 메서드들 ---
    def _add_interface(self):
        dialog = InterfaceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.interface_tab.interface_list.addItem(data['name'])
            self._mark_modified()
            self._update_config_tree()

    def _remove_interface(self):
        current_item = self.interface_tab.interface_list.currentItem()
        if current_item:
            self.interface_tab.interface_list.takeItem(
                self.interface_tab.interface_list.row(current_item)
            )
            self._mark_modified()
            self._update_config_tree()

    def _on_interface_selected(self):
        selected = self.interface_tab.interface_list.selectedItems()
        if selected:
            self.interface_tab.config_area_widget.setVisible(True)
            self.interface_tab.if_label.setText(f"인터페이스: {selected[0].text()}")
        else:
            self.interface_tab.config_area_widget.setVisible(False)

    def _add_vlan(self):
        dialog = VlanDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.vlan_tab.vlan_table.rowCount()
            self.vlan_tab.vlan_table.insertRow(row)
            self.vlan_tab.vlan_table.setItem(row, 0, QTableWidgetItem(data['id']))
            self.vlan_tab.vlan_table.setItem(row, 1, QTableWidgetItem(data['name']))
            self.vlan_tab.vlan_table.setItem(row, 2, QTableWidgetItem(data['description']))
            self._mark_modified()
            self._update_config_tree()

    def _remove_vlan(self):
        current_row = self.vlan_tab.vlan_table.currentRow()
        if current_row >= 0:
            self.vlan_tab.vlan_table.removeRow(current_row)
            self._mark_modified()
            self._update_config_tree()

    def _add_acl(self):
        dialog = AclDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.acl_tab.acl_list_table.rowCount()
            self.acl_tab.acl_list_table.insertRow(row)
            self.acl_tab.acl_list_table.setItem(row, 0, QTableWidgetItem(data['name']))
            self.acl_tab.acl_list_table.setItem(row, 1, QTableWidgetItem(data['type']))
            self.acl_tab.acl_list_table.setItem(row, 2, QTableWidgetItem(data['description']))
            self.acl_tab.refresh_acl_combo()
            self._mark_modified()
            self._update_config_tree()

    def _remove_acl(self):
        current_row = self.acl_tab.acl_list_table.currentRow()
        if current_row >= 0:
            self.acl_tab.acl_list_table.removeRow(current_row)
            self.acl_tab.refresh_acl_combo()
            self._mark_modified()
            self._update_config_tree()

    def _add_ace(self):
        current_acl_row = self.acl_tab.acl_list_table.currentRow()
        if current_acl_row < 0:
            QMessageBox.warning(self, "경고", "먼저 ACL을 선택하세요.")
            return

        acl_type = self.acl_tab.acl_list_table.item(current_acl_row, 1).text()
        dialog = AceDialog(self, acl_type=acl_type)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.acl_tab.acl_rule_table.rowCount()
            self.acl_tab.acl_rule_table.insertRow(row)
            self._mark_modified()

    def _remove_ace(self):
        current_row = self.acl_tab.acl_rule_table.currentRow()
        if current_row >= 0:
            self.acl_tab.acl_rule_table.removeRow(current_row)
            self._mark_modified()

    def _add_static_route(self):
        dialog = StaticRouteDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.routing_tab.static_route_table.rowCount()
            self.routing_tab.static_route_table.insertRow(row)
            self.routing_tab.static_route_table.setItem(row, 0, QTableWidgetItem(f"{data['network']}/{data['mask']}"))
            self.routing_tab.static_route_table.setItem(row, 1, QTableWidgetItem(data['next_hop']))
            self.routing_tab.static_route_table.setItem(row, 2, QTableWidgetItem(data['metric']))
            self.routing_tab.static_route_table.setItem(row, 3, QTableWidgetItem(data['vrf']))
            self._mark_modified()

    def _remove_static_route(self):
        current_row = self.routing_tab.static_route_table.currentRow()
        if current_row >= 0:
            self.routing_tab.static_route_table.removeRow(current_row)
            self._mark_modified()

    def _add_dns_server(self):
        dialog = DnsServerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.global_tab.dns_table.rowCount()
            self.global_tab.dns_table.insertRow(row)
            self.global_tab.dns_table.setItem(row, 0, QTableWidgetItem(data['ip']))
            self.global_tab.dns_table.setItem(row, 1, QTableWidgetItem(data['vrf']))
            self._mark_modified()

    def _remove_dns_server(self):
        current_row = self.global_tab.dns_table.currentRow()
        if current_row >= 0:
            self.global_tab.dns_table.removeRow(current_row)
            self._mark_modified()

    def _add_ntp_server(self):
        dialog = NtpServerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.global_tab.ntp_table.rowCount()
            self.global_tab.ntp_table.insertRow(row)
            self.global_tab.ntp_table.setItem(row, 0, QTableWidgetItem(data['server']))
            self.global_tab.ntp_table.setItem(row, 1, QTableWidgetItem("✓" if data['prefer'] else ""))
            self.global_tab.ntp_table.setItem(row, 2, QTableWidgetItem(data['key_id']))
            self.global_tab.ntp_table.setItem(row, 3, QTableWidgetItem(data['vrf']))
            self._mark_modified()

    def _remove_ntp_server(self):
        current_row = self.global_tab.ntp_table.currentRow()
        if current_row >= 0:
            self.global_tab.ntp_table.removeRow(current_row)
            self._mark_modified()

    def _manage_templates(self):
        # 템플릿 관리자 열기 로직은 여기에 통합되어야 합니다.
        QMessageBox.information(self, "알림", "템플릿 관리자 UI는 통합 관리될 예정입니다.")

    def _save_current_config_as_template(self):
        """현재 편집 중인 구성을 템플릿 파일로 저장합니다."""

        # 템플릿 정보 입력 다이얼로그 띄우기
        dialog = TemplateInputDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        template_name, description, category = dialog.get_data()

        if not template_name:
            QMessageBox.warning(self, "경고", "템플릿 이름은 비워둘 수 없습니다.")
            return

        # 1. 현재 구성 데이터 가져오기
        config_data = self._get_current_config()  # 이미 구현된 데이터 수집 함수 사용

        # 2. 템플릿 관리자를 통해 저장
        try:
            success = self.template_manager.save_template(
                template_name,
                config_data,
                description,
                category
            )
            if success:
                QMessageBox.information(self, "완료", f"'{template_name}' 템플릿이 성공적으로 저장되었습니다.")
            else:
                QMessageBox.critical(self, "오류", "템플릿 저장에 실패했습니다.")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"템플릿 저장 중 예상치 못한 오류 발생: {str(e)}")

    def _open_backup_settings(self):
        """백업 스케줄러 설정 다이얼로그"""
        dialog = QDialog(self)
        dialog.setWindowTitle("자동 백업 설정")
        layout = QVBoxLayout(dialog)

        form = QFormLayout()
        spin_interval = QSpinBox()
        spin_interval.setRange(60, 86400)  # 1분 ~ 24시간
        spin_interval.setValue(self.config_manager.interval)
        spin_interval.setSuffix(" 초")

        form.addRow("백업 주기:", spin_interval)
        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec() == QDialog.Accepted:
            new_interval = spin_interval.value()
            self.config_manager.set_interval(new_interval)
            app_logger.log_info(f"백업 주기 변경됨: {new_interval}초")
            QMessageBox.information(self, "설정 완료", f"백업 주기가 {new_interval}초로 변경되었습니다.")

    def _on_scheduler_log(self, message):
        """스케줄러로부터 오는 메시지 처리"""
        self._update_status(message)

    def _new_config(self):
        if self.is_modified:
            reply = QMessageBox.question(self, "저장 확인", "현재 구성이 수정되었습니다. 저장하시겠습니까?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self._save_config()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self._clear_all_tabs()
        self.current_file_path = None
        self.is_modified = False
        self.original_config = {}
        self.setWindowTitle("Cisco Config Manager - 새 구성")
        self._update_status("새 구성 생성됨")
        self._update_config_tree()
        app_logger.log_info("새 구성 파일 생성됨")

    def _open_config(self, file_path=None):
        """구성 파일 열기 (file_path가 없으면 파일 선택창 띄움)"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "구성 파일 열기", "", "JSON Files (*.json);;All Files (*)")

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._load_config_to_ui(config)
                self.current_file_path = file_path
                self.original_config = config.copy()
                self.is_modified = False
                self.setWindowTitle(f"Cisco Config Manager - {os.path.basename(file_path)}")
                self._update_status(f"파일 열림: {file_path}")
                self._add_to_recent_files(file_path)
                self._update_config_tree()
                app_logger.log_info(f"파일 열기 성공: {file_path}")
            except Exception as e:
                app_logger.log_error(f"파일 열기 실패: {str(e)}")
                QMessageBox.critical(self, "오류", f"파일을 열 수 없습니다:\n{str(e)}")

    def _save_config(self):
        if not self.current_file_path:
            self._save_config_as()
        else:
            try:
                config = self._get_current_config()
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self.original_config = config.copy()
                self.is_modified = False
                self._update_status(f"저장됨: {self.current_file_path}")
                self._update_modified_status()
                app_logger.log_info(f"파일 저장 성공: {self.current_file_path}")
            except Exception as e:
                app_logger.log_error(f"파일 저장 실패: {str(e)}")
                QMessageBox.critical(self, "오류", f"파일을 저장할 수 없습니다:\n{str(e)}")

    def _save_config_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "구성 저장", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'
            self.current_file_path = file_path
            self._save_config()
            self.setWindowTitle(f"Cisco Config Manager - {os.path.basename(file_path)}")

    def _generate_commands(self, show_only=False):
        current_config = self._get_current_config()
        commands = self.command_generator.generate_commands(self.original_config, current_config)  # command_generator 사용
        self.command_preview.setPlainText('\n'.join(commands))
        if not show_only:
            QMessageBox.information(self, "명령어 생성", f"{len(commands)}개의 명령어가 생성되었습니다.")
        return commands

    def _analyze_config(self):
        config = self._get_current_config()
        dialog = QDialog(self)
        dialog.setWindowTitle("구성 분석 결과")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        analysis_text = self._generate_analysis_report(config)
        text_edit.setPlainText(analysis_text)
        layout.addWidget(text_edit)
        dialog.exec()

    def _validate_config(self):
        config = self._get_current_config()
        validation_results = []
        for interface in config.get('interfaces', []):
            if interface.get('routed', {}).get('ip'):
                ip = interface['routed']['ip'].split()[0]
                valid, msg = NetworkValidator.validate_ip_address(ip)
                if not valid:
                    validation_results.append(f"❌ 인터페이스 {interface['name']}: {msg}")
                else:
                    validation_results.append(f"✅ 인터페이스 {interface['name']}: 유효한 IP")
        for vlan in config.get('vlans', {}).get('list', []):
            valid, msg = VlanValidator.validate_vlan_id(vlan['id'])
            if not valid:
                validation_results.append(f"❌ VLAN {vlan['id']}: {msg}")
            else:
                validation_results.append(f"✅ VLAN {vlan['id']}: 유효함")
        self.validation_output.setPlainText('\n'.join(validation_results))
        if not validation_results:
            self.validation_output.setPlainText("모든 구성이 유효합니다.")

    def _compare_configs(self):
        if not self.original_config:
            QMessageBox.information(self, "정보", "비교할 원본 구성이 없습니다.")
            return
        current_config = self._get_current_config()
        changes = ConfigDiff.compare_configs(self.original_config, current_config)
        report = ConfigDiff.generate_change_report(changes)
        dialog = QDialog(self)
        dialog.setWindowTitle("구성 비교 결과")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(report)
        layout.addWidget(text_edit)
        dialog.exec()

    def _show_find_dialog(self):
        text, ok = QInputDialog.getText(self, "찾기", "검색어:")
        if ok and text:
            self.search_field.setText(text)
            self._search_config()

    def _search_config(self):
        search_term = self.search_field.text().lower()
        if not search_term:
            return

        found = False
        # 1. Config Tree에서 검색
        iterator = QTreeWidgetItemIterator(self.config_tree)
        while iterator.value():
            item = iterator.value()
            if search_term in item.text(0).lower():
                self.config_tree.setCurrentItem(item)
                item.setSelected(True)
                found = True
                break
            iterator += 1

        if not found:
            self._update_status(f"'{search_term}'을(를) 찾을 수 없습니다.")
        else:
            self._update_status(f"'{search_term}' 검색 완료")

    def _show_help(self):
        help_text = """Cisco Config Manager 도움말\n\n단축키:\n- F5: 명령어 생성\n- F8: 장비 관리\n- F9: 배포\n- F10: 토폴로지\n\n사용법:\n1. 상단 툴바에서 장비를 선택하고 '가져오기'를 누르세요.\n2. 설정을 변경하고 '명령어 생성'을 확인하세요.\n3. '적용' 버튼으로 장비에 배포하세요."""
        QMessageBox.information(self, "도움말", help_text)

    def _open_topology_viewer(self):
        from .topology_dialog import TopologyDialog
        topology_dialog = TopologyDialog(self)
        topology_dialog.exec()

    def _open_dashboard(self):
        from .dashboard_widget import DashboardDialog
        dashboard_dialog = DashboardDialog(self)
        dashboard_dialog.show()

    def _show_about(self):
        QMessageBox.about(self, "정보", "Cisco Config Manager v2.0\n\n장비 중심 구성 관리 도구")

    def _on_tab_changed(self, index):
        self._update_status(f"현재 탭: {self.tab_widget.tabText(index)}")

    def _on_config_changed(self):
        self._mark_modified()
        self._generate_commands(show_only=True)

    def _mark_modified(self):
        if not self.is_modified:
            self.is_modified = True
            self._update_modified_status()

    def _update_modified_status(self):
        if self.is_modified:
            self.modified_label.setText("[수정됨]")
            self.modified_label.setStyleSheet("color: red;")
        else:
            self.modified_label.setText("")

    def _update_status(self, message):
        self.status_label.setText(message)

    def _update_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)

    def _toggle_config_tree(self, checked):
        if checked:
            self.config_tree.parent().show()
        else:
            self.config_tree.parent().hide()

    def _toggle_preview(self, checked):
        if checked:
            self.command_preview.parent().show()
        else:
            self.command_preview.parent().hide()

    def _refresh_view(self):
        self._update_config_tree()
        self._validate_config()

    def _update_config_tree(self):
        self.config_tree.clear()
        config = self._get_current_config()
        global_item = QTreeWidgetItem(self.config_tree, ["전역 설정"])
        if config.get('global', {}).get('hostname'):
            QTreeWidgetItem(global_item, [f"호스트명: {config['global']['hostname']}"])
        interfaces_item = QTreeWidgetItem(self.config_tree, ["인터페이스"])
        for interface in config.get('interfaces', []):
            QTreeWidgetItem(interfaces_item, [interface.get('name', 'Unknown')])
        vlans_item = QTreeWidgetItem(self.config_tree, ["VLAN"])
        for vlan in config.get('vlans', {}).get('list', []):
            QTreeWidgetItem(vlans_item, [f"VLAN {vlan.get('id', '')}: {vlan.get('name', '')}"])
        self.config_tree.expandAll()

    def _get_current_config(self) -> Dict:
        """현재 UI의 모든 탭에서 데이터를 수집하여 딕셔너리로 반환"""
        config = {
            'global': {},
            'interfaces': [],
            'vlans': {'list': []},
            'routing': {
                'static_routes': [],
                'ospf': {},
                'bgp': {}
            },
            'switching': {},
            'security': {
                'aaa': {},
                'users': [],
                'snmp': {}
            },
            'acls': [],
            'ha': {}
        }

        # --- 1. Global Tab 데이터 수집 ---
        if hasattr(self, 'global_tab'):
            config['global']['hostname'] = self.global_tab.le_hostname.text()
            config['global']['domain_name'] = self.global_tab.le_domain_name.text()
            config['global']['service_timestamps'] = self.global_tab.cb_service_timestamps.isChecked()
            config['global']['password_encryption'] = self.global_tab.cb_service_password_encryption.isChecked()

            # DNS Servers
            dns_servers = []
            for row in range(self.global_tab.dns_table.rowCount()):
                ip = self.global_tab.dns_table.item(row, 0).text()
                vrf = self.global_tab.dns_table.item(row, 1).text()
                dns_servers.append({'ip': ip, 'vrf': vrf})
            config['global']['dns_servers'] = dns_servers

            # NTP Servers
            ntp_servers = []
            for row in range(self.global_tab.ntp_table.rowCount()):
                server = self.global_tab.ntp_table.item(row, 0).text()
                prefer = self.global_tab.ntp_table.item(row, 1).text() == "✓"
                ntp_servers.append({'server': server, 'prefer': prefer})
            config['global']['ntp_servers'] = ntp_servers

        # --- 2. VLAN Tab 데이터 수집 ---
        if hasattr(self, 'vlan_tab'):
            for row in range(self.vlan_tab.vlan_table.rowCount()):
                vlan_id = self.vlan_tab.vlan_table.item(row, 0).text()
                vlan_name = self.vlan_tab.vlan_table.item(row, 1).text()
                vlan_desc = self.vlan_tab.vlan_table.item(row, 2).text()

                vlan_data = {
                    'id': vlan_id,
                    'name': vlan_name,
                    'description': vlan_desc,
                    'svi': {'enabled': False}
                }
                config['vlans']['list'].append(vlan_data)

        # --- 3. Interface Tab 데이터 수집 ---
        if hasattr(self, 'interface_tab'):
            for i in range(self.interface_tab.interface_list.count()):
                item = self.interface_tab.interface_list.item(i)
                iface_name = item.text()
                config['interfaces'].append({
                    'name': iface_name,
                })

        # --- 4. Routing Tab 데이터 수집 ---
        if hasattr(self, 'routing_tab'):
            # Static Routes
            for row in range(self.routing_tab.static_route_table.rowCount()):
                network_mask = self.routing_tab.static_route_table.item(row, 0).text()
                if '/' in network_mask:
                    network, mask = network_mask.split('/')
                else:
                    network, mask = network_mask, "255.255.255.0"

                route = {
                    'network': network,
                    'mask': mask,
                    'next_hop': self.routing_tab.static_route_table.item(row, 1).text(),
                    'metric': self.routing_tab.static_route_table.item(row, 2).text(),
                    'vrf': self.routing_tab.static_route_table.item(row, 3).text()
                }
                config['routing']['static_routes'].append(route)

            # OSPF
            config['routing']['ospf']['enabled'] = self.routing_tab.cb_ospf_enabled.isChecked()
            config['routing']['ospf']['process_id'] = self.routing_tab.le_ospf_process_id.text()

            # BGP
            config['routing']['bgp']['enabled'] = self.routing_tab.cb_bgp_enabled.isChecked()
            config['routing']['bgp']['as_number'] = self.routing_tab.le_bgp_as_number.text()

        # --- 5. Security Tab 데이터 수집 ---
        if hasattr(self, 'security_tab'):
            # Local Users
            for row in range(self.security_tab.users_table.rowCount()):
                username = self.security_tab.users_table.item(row, 0).text()
                privilege = self.security_tab.users_table.item(row, 1).text()
                config['security']['users'].append({
                    'username': username,
                    'privilege': privilege
                })

        # --- 6. ACL Tab 데이터 수집 ---
        if hasattr(self, 'acl_tab'):
            for row in range(self.acl_tab.acl_list_table.rowCount()):
                acl_name = self.acl_tab.acl_list_table.item(row, 0).text()
                acl_type = self.acl_tab.acl_list_table.item(row, 1).text()
                config['acls'].append({
                    'name': acl_name,
                    'type': acl_type,
                    'rules': []
                })

        return config

    def _clear_all_tabs(self):
        """모든 탭의 입력 필드 초기화"""
        # 1. Global 탭 초기화
        if hasattr(self, 'global_tab'):
            self.global_tab.le_hostname.clear()
            self.global_tab.le_domain_name.clear()
            self.global_tab.dns_table.setRowCount(0)
            self.global_tab.ntp_table.setRowCount(0)
            self.global_tab.logging_table.setRowCount(0)
            self.global_tab.le_mgmt_ip.clear()
            self.global_tab.le_mgmt_subnet.clear()
            self.global_tab.le_mgmt_gateway.clear()

        # 2. Interface 탭 초기화
        if hasattr(self, 'interface_tab'):
            self.interface_tab.interface_list.clear()
            self.interface_tab.le_if_description.clear()
            self.interface_tab.cb_if_shutdown.setChecked(False)
            self.interface_tab.le_routed_ip.clear()
            self.interface_tab.le_access_vlan.clear()
            self.interface_tab.le_trunk_allowed.clear()
            self.interface_tab.config_area_widget.setVisible(False)

        # 3. VLAN 탭 초기화
        if hasattr(self, 'vlan_tab'):
            self.vlan_tab.vlan_table.setRowCount(0)
            self.vlan_tab.cb_svi_enabled.setChecked(False)
            self.vlan_tab.le_svi_ip.clear()
            self.vlan_tab.dhcp_helper_table.setRowCount(0)

        # 4. Routing 탭 초기화
        if hasattr(self, 'routing_tab'):
            self.routing_tab.static_route_table.setRowCount(0)
            self.routing_tab.cb_ospf_enabled.setChecked(False)
            self.routing_tab.ospf_network_table.setRowCount(0)
            self.routing_tab.cb_bgp_enabled.setChecked(False)
            self.routing_tab.bgp_neighbor_table.setRowCount(0)

        # 5. ACL 탭 초기화
        if hasattr(self, 'acl_tab'):
            self.acl_tab.acl_list_table.setRowCount(0)
            self.acl_tab.acl_rule_table.setRowCount(0)
            self.acl_tab.acl_summary_label.setText("총 0개의 ACL이 구성되었습니다.")

        # 6. Switching 탭 초기화
        if hasattr(self, 'switching_tab'):
            self.switching_tab.combo_stp_mode.setCurrentIndex(0)
            self.switching_tab.le_stp_priority.clear()
            self.switching_tab.mst_instance_table.setRowCount(0)

        # 7. Security 탭 초기화
        if hasattr(self, 'security_tab'):
            self.security_tab.aaa_server_table.setRowCount(0)
            self.security_tab.users_table.setRowCount(0)
            self.security_tab.snmp_community_table.setRowCount(0)

        # 8. HA 탭 초기화
        if hasattr(self, 'ha_tab'):
            self.ha_tab.cb_fhrp_enabled.setChecked(False) if hasattr(self.ha_tab, 'cb_fhrp_enabled') else None
            self.ha_tab.le_fhrp_vip.clear() if hasattr(self.ha_tab, 'le_fhrp_vip') else None

        self.is_modified = False
        self._update_modified_status()

    def _generate_analysis_report(self, config: Dict) -> str:
        """구성 분석 보고서 텍스트 생성"""
        report = []
        report.append(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"호스트명: {config.get('global', {}).get('hostname', 'N/A')}")

        ifaces = config.get('interfaces', [])
        report.append(f"총 인터페이스 수: {len(ifaces)}")

        vlans = config.get('vlans', {}).get('list', [])
        report.append(f"VLAN 개수: {len(vlans)}")

        acls = config.get('acls', [])
        report.append(f"ACL 개수: {len(acls)}")

        return "\n".join(report)

    def _add_to_recent_files(self, file_path):
        """최근 파일 목록에 추가"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent_files]
        self._update_recent_files_menu()
        self._save_settings()

    def _update_recent_files_menu(self):
        """메뉴바의 최근 파일 목록 갱신"""
        if not hasattr(self, 'recent_files_menu'):
            return

        self.recent_files_menu.clear()
        for file_path in self.recent_files:
            if os.path.exists(file_path):
                action = QAction(os.path.basename(file_path), self)
                action.triggered.connect(lambda checked, fp=file_path: self._open_config(fp))
                self.recent_files_menu.addAction(action)

    def _load_settings(self):
        """저장된 설정 로드 (창 크기, 최근 파일 등)"""
        self.recent_files = self.settings.value('recent_files', [])
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def _save_settings(self):
        """설정 저장"""
        self.settings.setValue('recent_files', self.recent_files)
        self.settings.setValue('geometry', self.saveGeometry())

    def closeEvent(self, event):
        # 스케줄러 중지
        if hasattr(self, 'scheduler'):
            self.config_manager.stop()
            app_logger.log_info("애플리케이션 종료")

        if self.is_modified:
            reply = QMessageBox.question(
                self, "저장 확인",
                "현재 구성이 수정되었습니다. 저장하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._save_config()
                self._save_settings()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                self._save_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self._save_settings()
            event.accept()