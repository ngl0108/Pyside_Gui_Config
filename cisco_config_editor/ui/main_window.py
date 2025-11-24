# cisco_config_manager/ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu,
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QVBoxLayout, QWidget, QTextEdit, QSplitter,
    QDockWidget, QTreeWidget, QTreeWidgetItem, QPlainTextEdit,
    QInputDialog, QListWidget, QListWidgetItem, QTableWidgetItem,
    QDialog, QComboBox, QPushButton, QHBoxLayout, QLabel,
    QUndoStack, QUndoCommand, QLineEdit, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QSettings
from PySide6.QtGui import QAction, QKeySequence, QIcon, QTextCharFormat, QColor, QFont

# 탭 모듈들
from .tabs.interface_tab import InterfaceTab
from .tabs.vlan_tab import VlanTab
from .tabs.routing_tab import RoutingTab
from .tabs.switching_tab import SwitchingTab
from .tabs.security_tab import SecurityTab
from .tabs.acl_tab import AclTab
from .tabs.global_tab import GlobalTab
from .tabs.ha_tab import HaTab

# Core 모듈들 - 상대 경로로 수정
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.command_generator import CiscoCommandGenerator
from core.cli_analyzer import CLIAnalyzer
from core.config_diff import ConfigDiff
from core.validators import (
    NetworkValidator, VlanValidator, InterfaceValidator,
    SecurityValidator, RoutingValidator, PortValidator, HostnameValidator
)
from core.templates import ConfigTemplate, BuiltInTemplates

# UI 모듈들
from dialogs import (
    InterfaceDialog, VlanDialog, AclDialog, AceDialog,
    StaticRouteDialog, DnsServerDialog, NtpServerDialog
)

import json
from datetime import datetime
from typing import Dict, List, Any, Optional


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
        self.command_generator = CiscoCommandGenerator()
        self.cli_analyzer = CLIAnalyzer()
        self.original_config = {}
        self.template_manager = ConfigTemplate()

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
        self._update_status("준비됨")

    def _setup_ui(self):
        """UI 초기화 및 설정"""
        self.setWindowTitle("Cisco Config Manager")
        self.setGeometry(100, 100, 1400, 900)

        # 중앙 위젯을 Splitter로 설정
        main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(main_splitter)

        # 좌측 패널 (구성 트리)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 검색 필드
        search_layout = QHBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("검색...")
        search_button = QPushButton("검색")
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(search_button)
        left_layout.addLayout(search_layout)

        # 구성 트리
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabel("구성 요소")
        left_layout.addWidget(self.config_tree)

        # 템플릿 목록
        self.template_list = QListWidget()
        self._load_template_list()
        left_layout.addWidget(QLabel("템플릿:"))
        left_layout.addWidget(self.template_list)

        main_splitter.addWidget(left_panel)

        # 중앙 패널 (탭)
        central_panel = QWidget()
        central_layout = QVBoxLayout(central_panel)

        # 메인 탭 위젯
        self.tab_widget = QTabWidget()
        central_layout.addWidget(self.tab_widget)

        # 탭 추가
        self.global_tab = GlobalTab()
        self.interface_tab = InterfaceTab()
        self.vlan_tab = VlanTab()
        self.routing_tab = RoutingTab()
        self.switching_tab = SwitchingTab()
        self.security_tab = SecurityTab()
        self.acl_tab = AclTab()
        self.ha_tab = HaTab()

        self.tab_widget.addTab(self.global_tab, "🌐 전역 설정")
        self.tab_widget.addTab(self.interface_tab, "🔌 인터페이스")
        self.tab_widget.addTab(self.vlan_tab, "🏷️ VLAN")
        self.tab_widget.addTab(self.routing_tab, "🛣️ 라우팅")
        self.tab_widget.addTab(self.switching_tab, "🔀 스위칭")
        self.tab_widget.addTab(self.security_tab, "🔒 보안")
        self.tab_widget.addTab(self.acl_tab, "🛡️ ACL")
        self.tab_widget.addTab(self.ha_tab, "⚡ HA")

        main_splitter.addWidget(central_panel)

        # 우측 패널 (명령어 미리보기)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_layout.addWidget(QLabel("명령어 미리보기:"))
        self.command_preview = QPlainTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setPlaceholderText("생성된 명령어가 여기에 표시됩니다...")
        right_layout.addWidget(self.command_preview)

        # 검증 결과
        right_layout.addWidget(QLabel("검증 결과:"))
        self.validation_output = QPlainTextEdit()
        self.validation_output.setReadOnly(True)
        self.validation_output.setMaximumHeight(150)
        right_layout.addWidget(self.validation_output)

        main_splitter.addWidget(right_panel)

        # 분할 비율 설정
        main_splitter.setSizes([250, 900, 250])

        # 메뉴바 설정
        self._setup_menubar()

        # 툴바 설정
        self._setup_toolbar()

        # 상태바 설정
        self._setup_statusbar()

    def _setup_menubar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()

        # 파일 메뉴
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

        # 최근 파일 메뉴
        self.recent_files_menu = file_menu.addMenu("최근 파일")
        self._update_recent_files_menu()

        file_menu.addSeparator()

        import_action = QAction("CLI 구성 가져오기", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._import_cli_config)
        file_menu.addAction(import_action)

        export_action = QAction("CLI 명령어 내보내기", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_commands)
        file_menu.addAction(export_action)

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

        # 장비 연결 관리 추가
        device_manager_action = QAction("장비 연결 관리", self)
        device_manager_action.setShortcut("F8")
        device_manager_action.triggered.connect(self._open_device_manager)
        tools_menu.addAction(device_manager_action)

        deploy_action = QAction("현재 구성 배포", self)
        deploy_action.setShortcut("F9")
        deploy_action.triggered.connect(self._deploy_current_config)
        tools_menu.addAction(deploy_action)

        tools_menu.addSeparator()

        # 시각화 및 모니터링 추가
        topology_action = QAction("네트워크 토폴로지", self)
        topology_action.setShortcut("F10")
        topology_action.triggered.connect(self._open_topology_viewer)
        tools_menu.addAction(topology_action)

        dashboard_action = QAction("실시간 대시보드", self)
        dashboard_action.setShortcut("F11")
        dashboard_action.triggered.connect(self._open_dashboard)
        tools_menu.addAction(dashboard_action)

        tools_menu.addSeparator()

        template_action = QAction("템플릿 관리", self)
        template_action.triggered.connect(self._manage_templates)
        tools_menu.addAction(template_action)

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

    def _setup_toolbar(self):
        """툴바 설정"""
        toolbar = self.addToolBar("주요 도구")
        toolbar.setMovable(False)

        # 툴바 액션들
        new_action = toolbar.addAction("📄 새 구성")
        new_action.triggered.connect(self._new_config)

        open_action = toolbar.addAction("📁 열기")
        open_action.triggered.connect(self._open_config)

        save_action = toolbar.addAction("💾 저장")
        save_action.triggered.connect(self._save_config)

        toolbar.addSeparator()

        undo_action = toolbar.addAction("↶ 실행취소")
        undo_action.triggered.connect(self.undo_stack.undo)

        redo_action = toolbar.addAction("↷ 다시실행")
        redo_action.triggered.connect(self.undo_stack.redo)

        toolbar.addSeparator()

        generate_action = toolbar.addAction("⚙️ 명령어 생성")
        generate_action.triggered.connect(self._generate_commands)

        analyze_action = toolbar.addAction("🔍 구성 분석")
        analyze_action.triggered.connect(self._analyze_config)

        validate_action = toolbar.addAction("✓ 검증")
        validate_action.triggered.connect(self._validate_config)

        toolbar.addSeparator()

        template_action = toolbar.addAction("📋 템플릿")
        template_action.triggered.connect(self._manage_templates)

    def _setup_statusbar(self):
        """상태바 설정"""
        self.status_bar = self.statusBar()

        # 상태 메시지
        self.status_label = QLabel("준비됨")
        self.status_bar.addWidget(self.status_label)

        # 수정 상태
        self.modified_label = QLabel("")
        self.status_bar.addPermanentWidget(self.modified_label)

        # 파일 경로
        self.file_label = QLabel("새 파일")
        self.status_bar.addPermanentWidget(self.file_label)

        # 현재 시간
        self.time_label = QLabel("")
        self.status_bar.addPermanentWidget(self.time_label)

        # 시간 업데이트 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)

    def _connect_signals(self):
        """시그널 연결"""
        # 탭 변경 시
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # 템플릿 선택 시
        self.template_list.itemDoubleClicked.connect(self._apply_template)

        # 검색
        self.search_field.returnPressed.connect(self._search_config)

        # 구성 변경 시
        self.config_changed.connect(self._on_config_changed)

    def _connect_tab_signals(self):
        """각 탭의 시그널 연결"""
        # Interface 탭 시그널 연결
        if hasattr(self.interface_tab, 'btn_add_interface'):
            self.interface_tab.btn_add_interface.clicked.connect(self._add_interface)
            self.interface_tab.btn_remove_interface.clicked.connect(self._remove_interface)
            self.interface_tab.interface_list.itemSelectionChanged.connect(self._on_interface_selected)

        # VLAN 탭 시그널 연결
        if hasattr(self.vlan_tab, 'btn_add_vlan'):
            self.vlan_tab.btn_add_vlan.clicked.connect(self._add_vlan)
            self.vlan_tab.btn_remove_vlan.clicked.connect(self._remove_vlan)

        # ACL 탭 시그널 연결
        if hasattr(self.acl_tab, 'btn_add_acl'):
            self.acl_tab.btn_add_acl.clicked.connect(self._add_acl)
            self.acl_tab.btn_remove_acl.clicked.connect(self._remove_acl)
            self.acl_tab.btn_add_rule.clicked.connect(self._add_ace)
            self.acl_tab.btn_remove_rule.clicked.connect(self._remove_ace)

        # 라우팅 탭 시그널 연결
        if hasattr(self.routing_tab, 'btn_add_static_route'):
            self.routing_tab.btn_add_static_route.clicked.connect(self._add_static_route)
            self.routing_tab.btn_remove_static_route.clicked.connect(self._remove_static_route)

        # Global 탭 시그널 연결
        if hasattr(self.global_tab, 'btn_add_dns'):
            self.global_tab.btn_add_dns.clicked.connect(self._add_dns_server)
            self.global_tab.btn_remove_dns.clicked.connect(self._remove_dns_server)
            self.global_tab.btn_add_ntp.clicked.connect(self._add_ntp_server)
            self.global_tab.btn_remove_ntp.clicked.connect(self._remove_ntp_server)

    def _add_interface(self):
        """인터페이스 추가"""
        dialog = InterfaceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.interface_tab.interface_list.addItem(data['name'])
            self._mark_modified()
            self._update_config_tree()

    def _remove_interface(self):
        """인터페이스 제거"""
        current_item = self.interface_tab.interface_list.currentItem()
        if current_item:
            self.interface_tab.interface_list.takeItem(
                self.interface_tab.interface_list.row(current_item)
            )
            self._mark_modified()
            self._update_config_tree()

    def _on_interface_selected(self):
        """인터페이스 선택 시"""
        selected = self.interface_tab.interface_list.selectedItems()
        if selected:
            self.interface_tab.config_area_widget.setVisible(True)
            self.interface_tab.if_label.setText(f"인터페이스: {selected[0].text()}")
        else:
            self.interface_tab.config_area_widget.setVisible(False)

    def _add_vlan(self):
        """VLAN 추가"""
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
        """VLAN 제거"""
        current_row = self.vlan_tab.vlan_table.currentRow()
        if current_row >= 0:
            self.vlan_tab.vlan_table.removeRow(current_row)
            self._mark_modified()
            self._update_config_tree()

    def _add_acl(self):
        """ACL 추가"""
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
        """ACL 제거"""
        current_row = self.acl_tab.acl_list_table.currentRow()
        if current_row >= 0:
            self.acl_tab.acl_list_table.removeRow(current_row)
            self.acl_tab.refresh_acl_combo()
            self._mark_modified()
            self._update_config_tree()

    def _add_ace(self):
        """ACL Entry 추가"""
        # 현재 선택된 ACL 가져오기
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
            # ACE 데이터 추가
            self._mark_modified()

    def _remove_ace(self):
        """ACL Entry 제거"""
        current_row = self.acl_tab.acl_rule_table.currentRow()
        if current_row >= 0:
            self.acl_tab.acl_rule_table.removeRow(current_row)
            self._mark_modified()

    def _add_static_route(self):
        """정적 경로 추가"""
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
        """정적 경로 제거"""
        current_row = self.routing_tab.static_route_table.currentRow()
        if current_row >= 0:
            self.routing_tab.static_route_table.removeRow(current_row)
            self._mark_modified()

    def _add_dns_server(self):
        """DNS 서버 추가"""
        dialog = DnsServerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.global_tab.dns_table.rowCount()
            self.global_tab.dns_table.insertRow(row)
            self.global_tab.dns_table.setItem(row, 0, QTableWidgetItem(data['ip']))
            self.global_tab.dns_table.setItem(row, 1, QTableWidgetItem(data['vrf']))
            self._mark_modified()

    def _remove_dns_server(self):
        """DNS 서버 제거"""
        current_row = self.global_tab.dns_table.currentRow()
        if current_row >= 0:
            self.global_tab.dns_table.removeRow(current_row)
            self._mark_modified()

    def _add_ntp_server(self):
        """NTP 서버 추가"""
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
        """NTP 서버 제거"""
        current_row = self.global_tab.ntp_table.currentRow()
        if current_row >= 0:
            self.global_tab.ntp_table.removeRow(current_row)
            self._mark_modified()

    def _new_config(self):
        """새 구성 생성"""
        if self.is_modified:
            reply = QMessageBox.question(
                self, "저장 확인",
                "현재 구성이 수정되었습니다. 저장하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self._save_config()
            elif reply == QMessageBox.Cancel:
                return

        self._clear_all_tabs()
        self.current_file_path = None
        self.is_modified = False
        self.original_config = {}
        self.setWindowTitle("Cisco Config Manager - 새 구성")
        self._update_status("새 구성 생성됨")
        self._update_config_tree()

    def _open_config(self):
        """구성 파일 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "구성 파일 열기", "",
            "JSON Files (*.json);;All Files (*)"
        )

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

            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일을 열 수 없습니다:\n{str(e)}")

    def _save_config(self):
        """구성 저장"""
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

            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일을 저장할 수 없습니다:\n{str(e)}")

    def _save_config_as(self):
        """다른 이름으로 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "구성 저장", "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'

            self.current_file_path = file_path
            self._save_config()
            self.setWindowTitle(f"Cisco Config Manager - {os.path.basename(file_path)}")

    def _import_cli_config(self):
        """CLI 구성 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CLI 구성 가져오기", "",
            "Text Files (*.txt);;Config Files (*.cfg);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cli_content = f.read()

                # CLI 분석
                config = self.cli_analyzer.analyze_show_run(cli_content)
                self._load_config_to_ui(config)
                self.is_modified = True
                self._update_status(f"CLI 구성 가져옴: {file_path}")
                self._update_config_tree()

            except Exception as e:
                QMessageBox.critical(self, "오류", f"CLI 구성을 가져올 수 없습니다:\n{str(e)}")

    def _export_commands(self):
        """명령어 내보내기"""
        commands = self._generate_commands(show_only=True)
        if not commands:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "명령어 내보내기", "",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(commands))

                self._update_status(f"명령어 내보냄: {file_path}")
                QMessageBox.information(self, "성공", "명령어가 성공적으로 내보내졌습니다.")

            except Exception as e:
                QMessageBox.critical(self, "오류", f"명령어를 내보낼 수 없습니다:\n{str(e)}")

    def _generate_commands(self, show_only=False):
        """명령어 생성"""
        current_config = self._get_current_config()
        commands = self.command_generator.generate_commands(self.original_config, current_config)

        # 명령어 미리보기 업데이트
        self.command_preview.setPlainText('\n'.join(commands))

        if not show_only:
            QMessageBox.information(self, "명령어 생성", f"{len(commands)}개의 명령어가 생성되었습니다.")

        return commands

    def _analyze_config(self):
        """구성 분석"""
        config = self._get_current_config()

        # 분석 결과 다이얼로그 표시
        dialog = QDialog(self)
        dialog.setWindowTitle("구성 분석 결과")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        # 분석 내용 생성
        analysis_text = self._generate_analysis_report(config)
        text_edit.setPlainText(analysis_text)

        layout.addWidget(text_edit)
        dialog.exec()

    def _validate_config(self):
        """구성 검증"""
        config = self._get_current_config()
        validation_results = []

        # 각 설정 검증
        # IP 주소 검증
        for interface in config.get('interfaces', []):
            if interface.get('routed', {}).get('ip'):
                ip = interface['routed']['ip'].split()[0] if ' ' in interface['routed']['ip'] else interface['routed'][
                    'ip']
                valid, msg = NetworkValidator.validate_ip_address(ip)
                if not valid:
                    validation_results.append(f"❌ 인터페이스 {interface['name']}: {msg}")
                else:
                    validation_results.append(f"✅ 인터페이스 {interface['name']}: 유효한 IP")

        # VLAN ID 검증
        for vlan in config.get('vlans', {}).get('list', []):
            valid, msg = VlanValidator.validate_vlan_id(vlan['id'])
            if not valid:
                validation_results.append(f"❌ VLAN {vlan['id']}: {msg}")
            else:
                validation_results.append(f"✅ VLAN {vlan['id']}: 유효함")

        # 검증 결과 표시
        self.validation_output.setPlainText('\n'.join(validation_results))

        if not validation_results:
            self.validation_output.setPlainText("모든 구성이 유효합니다.")

    def _compare_configs(self):
        """구성 비교"""
        if not self.original_config:
            QMessageBox.information(self, "정보", "비교할 원본 구성이 없습니다.")
            return

        current_config = self._get_current_config()
        changes = ConfigDiff.compare_configs(self.original_config, current_config)
        report = ConfigDiff.generate_change_report(changes)

        # 비교 결과 다이얼로그
        dialog = QDialog(self)
        dialog.setWindowTitle("구성 비교 결과")
        dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(report)

        layout.addWidget(text_edit)
        dialog.exec()

    def _manage_templates(self):
        """템플릿 관리 다이얼로그"""
        dialog = QDialog(self)
        dialog.setWindowTitle("템플릿 관리")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        # 템플릿 선택
        template_combo = QComboBox()
        builtin_templates = BuiltInTemplates.list_builtin_templates()
        for template in builtin_templates:
            template_combo.addItem(f"[내장] {template['description']}", template['name'])

        for name in self.template_manager.templates:
            template_combo.addItem(f"[사용자] {name}", name)

        layout.addWidget(QLabel("템플릿 선택:"))
        layout.addWidget(template_combo)

        # 변수 입력 영역
        variables_text = QTextEdit()
        variables_text.setPlaceholderText(
            "변수를 JSON 형식으로 입력하세요.\n예:\n{\n  \"hostname\": \"SW1\",\n  \"domain\": \"example.com\"\n}")
        layout.addWidget(QLabel("템플릿 변수:"))
        layout.addWidget(variables_text)

        # 버튼
        button_layout = QHBoxLayout()
        apply_button = QPushButton("적용")
        save_button = QPushButton("현재 구성을 템플릿으로 저장")
        close_button = QPushButton("닫기")

        button_layout.addWidget(apply_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        # 시그널 연결
        def apply_template():
            template_name = template_combo.currentData()
            try:
                variables = json.loads(variables_text.toPlainText()) if variables_text.toPlainText() else {}

                # 내장 템플릿인지 확인
                if template_combo.currentText().startswith("[내장]"):
                    config = BuiltInTemplates.get_builtin_template(template_name)
                else:
                    config = self.template_manager.apply_template(template_name, variables)

                if config:
                    self._load_config_to_ui(config)
                    self._mark_modified()
                    dialog.accept()
            except json.JSONDecodeError:
                QMessageBox.warning(dialog, "오류", "올바른 JSON 형식이 아닙니다.")

        def save_as_template():
            name, ok = QInputDialog.getText(dialog, "템플릿 저장", "템플릿 이름:")
            if ok and name:
                desc, ok = QInputDialog.getText(dialog, "템플릿 저장", "템플릿 설명:")
                if ok:
                    config = self._get_current_config()
                    if self.template_manager.save_template(name, config, desc):
                        QMessageBox.information(dialog, "성공", "템플릿이 저장되었습니다.")
                        self._load_template_list()

        apply_button.clicked.connect(apply_template)
        save_button.clicked.connect(save_as_template)
        close_button.clicked.connect(dialog.reject)

        dialog.exec()

    def _apply_template(self, item):
        """템플릿 적용"""
        template_name = item.text()
        if template_name.startswith("[내장]"):
            # 내장 템플릿 처리
            pass
        else:
            # 사용자 템플릿 처리
            pass

    def _show_find_dialog(self):
        """찾기 다이얼로그"""
        text, ok = QInputDialog.getText(self, "찾기", "검색어:")
        if ok and text:
            self.search_field.setText(text)
            self._search_config()

    def _search_config(self):
        """구성 검색"""
        search_term = self.search_field.text().lower()
        if not search_term:
            return

        # 현재 탭에서 검색
        # 구현 필요

    def _show_help(self):
        """도움말 표시"""
        help_text = """
        Cisco Config Manager 도움말

        단축키:
        - Ctrl+N: 새 구성
        - Ctrl+O: 열기
        - Ctrl+S: 저장
        - Ctrl+Z: 실행 취소
        - Ctrl+Y: 다시 실행
        - F5: 명령어 생성
        - F6: 구성 분석
        - F7: 구성 검증
        - F8: 장비 연결 관리
        - F9: 구성 배포
        - F10: 네트워크 토폴로지
        - F11: 실시간 대시보드

        사용 방법:
        1. 각 탭에서 네트워크 구성 요소를 설정합니다.
        2. '명령어 생성'을 클릭하여 Cisco 명령어를 생성합니다.
        3. '장비 연결 관리'에서 실제 장비에 연결합니다.
        4. '구성 배포'로 생성된 명령어를 장비에 적용합니다.
        5. '네트워크 토폴로지'로 네트워크 구조를 시각화합니다.
        6. '실시간 대시보드'로 네트워크 상태를 모니터링합니다.
        """

        QMessageBox.information(self, "도움말", help_text)

    def _open_topology_viewer(self):
        """네트워크 토폴로지 뷰어 열기"""
        from topology_dialog import TopologyDialog

        topology_dialog = TopologyDialog(self)
        topology_dialog.exec()

    def _open_dashboard(self):
        """실시간 대시보드 열기"""
        from dashboard_widget import DashboardDialog

        dashboard_dialog = DashboardDialog(self)
        dashboard_dialog.show()  # 모달리스로 표시

    def _open_device_manager(self):
        """장비 관리 다이얼로그 열기"""
        from device_manager_dialog import DeviceManagerDialog

        self.device_manager = DeviceManagerDialog(self)
        self.device_manager.config_deployed.connect(self._on_config_deployed)
        self.device_manager.exec()

    def _deploy_current_config(self):
        """현재 구성을 장비에 배포"""
        # 현재 구성에서 명령어 생성
        commands = self._generate_commands(show_only=True)
        if not commands:
            QMessageBox.warning(self, "경고", "생성된 명령어가 없습니다.")
            return

        # 장비 관리자 열기
        from device_manager_dialog import DeviceManagerDialog

        self.device_manager = DeviceManagerDialog(self)

        # 배포 탭으로 이동하고 명령어 설정
        self.device_manager.tab_widget.setCurrentIndex(2)  # 배포 탭
        self.device_manager.deployment_commands.setPlainText('\n'.join(commands))

        self.device_manager.exec()

    def _on_config_deployed(self, device_name: str, commands: List[str]):
        """구성 배포 완료 처리"""
        self._update_status(f"구성이 {device_name}에 배포되었습니다.")

        # 배포 로그 저장 (옵션)
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'device': device_name,
            'commands': commands
        }
        # 로그 파일에 저장하거나 데이터베이스에 기록

    def _show_about(self):
        """프로그램 정보 표시"""
        about_text = """
        Cisco Config Manager v1.0

        Cisco 네트워크 장비 구성 관리 도구

        © 2024 Network Tools
        """

        QMessageBox.about(self, "정보", about_text)

    def _on_tab_changed(self, index):
        """탭 변경 시 처리"""
        self._update_status(f"현재 탭: {self.tab_widget.tabText(index)}")

    def _on_config_changed(self):
        """구성 변경 시 처리"""
        self._mark_modified()
        # 실시간 명령어 생성 (옵션)
        if hasattr(self, 'auto_generate') and self.auto_generate:
            self._generate_commands(show_only=True)

    def _mark_modified(self):
        """수정됨 표시"""
        if not self.is_modified:
            self.is_modified = True
            self._update_modified_status()

    def _update_modified_status(self):
        """수정 상태 업데이트"""
        if self.is_modified:
            self.modified_label.setText("[수정됨]")
            self.modified_label.setStyleSheet("color: red;")
        else:
            self.modified_label.setText("")

    def _update_status(self, message):
        """상태바 업데이트"""
        self.status_label.setText(message)

    def _update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)

    def _toggle_config_tree(self, checked):
        """구성 트리 표시/숨김"""
        # 구현 필요
        pass

    def _toggle_preview(self, checked):
        """명령어 미리보기 표시/숨김"""
        # 구현 필요
        pass

    def _refresh_view(self):
        """화면 새로고침"""
        self._update_config_tree()
        self._validate_config()

    def _update_config_tree(self):
        """구성 트리 업데이트"""
        self.config_tree.clear()

        config = self._get_current_config()

        # 전역 설정
        global_item = QTreeWidgetItem(self.config_tree, ["전역 설정"])
        if config.get('global', {}).get('hostname'):
            QTreeWidgetItem(global_item, [f"호스트명: {config['global']['hostname']}"])

        # 인터페이스
        interfaces_item = QTreeWidgetItem(self.config_tree, ["인터페이스"])
        for interface in config.get('interfaces', []):
            QTreeWidgetItem(interfaces_item, [interface.get('name', 'Unknown')])

        # VLAN
        vlans_item = QTreeWidgetItem(self.config_tree, ["VLAN"])
        for vlan in config.get('vlans', {}).get('list', []):
            QTreeWidgetItem(vlans_item, [f"VLAN {vlan.get('id', '')}: {vlan.get('name', '')}"])

        # ACL
        acls_item = QTreeWidgetItem(self.config_tree, ["ACL"])
        for acl in config.get('acls', []):
            QTreeWidgetItem(acls_item, [acl.get('name', 'Unknown')])

        self.config_tree.expandAll()

    def _load_template_list(self):
        """템플릿 목록 로드"""
        self.template_list.clear()

        # 내장 템플릿
        builtin = BuiltInTemplates.list_builtin_templates()
        for template in builtin:
            item = QListWidgetItem(f"[내장] {template['description']}")
            item.setData(Qt.UserRole, template['name'])
            self.template_list.addItem(item)

        # 사용자 템플릿
        user_templates = self.template_manager.list_templates()
        for template in user_templates:
            item = QListWidgetItem(f"{template['name']}")
            item.setData(Qt.UserRole, template['name'])
            self.template_list.addItem(item)

    def _add_to_recent_files(self, file_path):
        """최근 파일 목록에 추가"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]
        self._update_recent_files_menu()
        self._save_settings()

    def _update_recent_files_menu(self):
        """최근 파일 메뉴 업데이트"""
        self.recent_files_menu.clear()
        for file_path in self.recent_files:
            action = QAction(os.path.basename(file_path), self)
            action.setData(file_path)
            action.triggered.connect(lambda checked, fp=file_path: self._open_recent_file(fp))
            self.recent_files_menu.addAction(action)

    def _open_recent_file(self, file_path):
        """최근 파일 열기"""
        if os.path.exists(file_path):
            # 현재 파일 저장 확인
            if self.is_modified:
                reply = QMessageBox.question(
                    self, "저장 확인",
                    "현재 구성이 수정되었습니다. 저장하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                if reply == QMessageBox.Yes:
                    self._save_config()
                elif reply == QMessageBox.Cancel:
                    return

            # 파일 열기
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._load_config_to_ui(config)
                self.current_file_path = file_path
                self.original_config = config.copy()
                self.is_modified = False
                self.setWindowTitle(f"Cisco Config Manager - {os.path.basename(file_path)}")
                self._update_status(f"파일 열림: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일을 열 수 없습니다:\n{str(e)}")
                self.recent_files.remove(file_path)
                self._update_recent_files_menu()
        else:
            QMessageBox.warning(self, "경고", f"파일을 찾을 수 없습니다:\n{file_path}")
            self.recent_files.remove(file_path)
            self._update_recent_files_menu()

    def _load_settings(self):
        """설정 로드"""
        self.recent_files = self.settings.value('recent_files', [])
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.value('state')
        if state:
            self.restoreState(state)

    def _save_settings(self):
        """설정 저장"""
        self.settings.setValue('recent_files', self.recent_files)
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('state', self.saveState())

    def _clear_all_tabs(self):
        """모든 탭 초기화"""
        # 구현 필요 - 각 탭의 모든 필드를 초기 상태로
        pass

    def _get_current_config(self) -> Dict:
        """현재 UI의 구성을 딕셔너리로 반환"""
        config = {
            'global': {},
            'interfaces': [],
            'vlans': {'list': []},
            'routing': {},
            'switching': {},
            'security': {},
            'acls': [],
            'ha': {}
        }

        # Global 탭에서 데이터 수집
        if hasattr(self.global_tab, 'le_hostname'):
            config['global']['hostname'] = self.global_tab.le_hostname.text()

        # VLAN 탭에서 데이터 수집
        for row in range(self.vlan_tab.vlan_table.rowCount()):
            vlan = {
                'id': self.vlan_tab.vlan_table.item(row, 0).text() if self.vlan_tab.vlan_table.item(row, 0) else '',
                'name': self.vlan_tab.vlan_table.item(row, 1).text() if self.vlan_tab.vlan_table.item(row, 1) else '',
                'description': self.vlan_tab.vlan_table.item(row, 2).text() if self.vlan_tab.vlan_table.item(row,
                                                                                                             2) else ''
            }
            config['vlans']['list'].append(vlan)

        # 다른 탭들도 유사하게 처리

        return config

    def _load_config_to_ui(self, config: Dict):
        """구성을 UI에 로드"""
        # Global 탭 로드
        if 'global' in config:
            if hasattr(self.global_tab, 'le_hostname'):
                self.global_tab.le_hostname.setText(config['global'].get('hostname', ''))

        # VLAN 탭 로드
        if 'vlans' in config:
            self.vlan_tab.vlan_table.setRowCount(0)
            for vlan in config['vlans'].get('list', []):
                row = self.vlan_tab.vlan_table.rowCount()
                self.vlan_tab.vlan_table.insertRow(row)
                self.vlan_tab.vlan_table.setItem(row, 0, QTableWidgetItem(str(vlan.get('id', ''))))
                self.vlan_tab.vlan_table.setItem(row, 1, QTableWidgetItem(vlan.get('name', '')))
                self.vlan_tab.vlan_table.setItem(row, 2, QTableWidgetItem(vlan.get('description', '')))

        # 다른 탭들도 유사하게 처리

    def _generate_analysis_report(self, config: Dict) -> str:
        """분석 보고서 생성"""
        report = []
        report.append("=== Cisco 구성 분석 보고서 ===\n")
        report.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 기본 정보
        report.append("[기본 정보]")
        report.append(f"호스트명: {config.get('global', {}).get('hostname', 'Not set')}")
        report.append(f"도메인명: {config.get('global', {}).get('domain_name', 'Not set')}")
        report.append("")

        # 인터페이스 분석
        interfaces = config.get('interfaces', [])
        report.append(f"[인터페이스 분석]")
        report.append(f"총 인터페이스 수: {len(interfaces)}")
        if interfaces:
            shutdown_count = sum(1 for i in interfaces if i.get('shutdown'))
            report.append(f"- 활성화: {len(interfaces) - shutdown_count}")
            report.append(f"- 비활성화: {shutdown_count}")
        report.append("")

        # VLAN 분석
        vlans = config.get('vlans', {}).get('list', [])
        report.append(f"[VLAN 분석]")
        report.append(f"총 VLAN 수: {len(vlans)}")
        if vlans:
            for vlan in vlans:
                report.append(f"- VLAN {vlan.get('id', '')}: {vlan.get('name', '')}")
        report.append("")

        # 보안 분석
        report.append("[보안 분석]")
        security_config = config.get('security', {})
        if security_config.get('aaa', {}).get('new_model'):
            report.append("✓ AAA new-model 활성화")
        else:
            report.append("⚠ AAA new-model 비활성화")

        if config.get('global', {}).get('service_password_encryption'):
            report.append("✓ 비밀번호 암호화 활성화")
        else:
            report.append("⚠ 비밀번호 암호화 비활성화")

        return '\n'.join(report)

    def closeEvent(self, event):
        """프로그램 종료 시"""
        if self.is_modified:
            reply = QMessageBox.question(
                self, "저장 확인",
                "현재 구성이 수정되었습니다. 저장하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self._save_config()
                self._save_settings()
                event.accept()
            elif reply == QMessageBox.No:
                self._save_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self._save_settings()
            event.accept()