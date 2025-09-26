# ansible_config_editor/ui/main_window.py
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QListWidget, QPlainTextEdit,
                               QFileDialog, QMessageBox, QTabWidget, QFormLayout,
                               QLineEdit, QGroupBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QApplication, QInputDialog,
                               QScrollArea, QCheckBox, QLabel, QComboBox, QMenuBar)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ansible_config_editor.core.playbook_manager import ConfigManager
from ansible_config_editor.core.ansible_engine import AnsibleEngine


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Standard Network Config Manager")
        self.setGeometry(100, 100, 1800, 1000)

        self.config_manager = ConfigManager()
        self.ansible_engine = AnsibleEngine()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 왼쪽 패널: 장비 관리 및 OS 선택 ---
        device_management_group = QGroupBox("1. 장비 관리")
        device_layout = QVBoxLayout()

        self.combo_os_type = QComboBox()
        os_types = [
            "L2_IOS-XE",
            "L3_IOS-XE",
            "L2_NX-OS",
            "L3_NX-OS",
            "WLC_AireOS"
        ]
        self.combo_os_type.addItems(os_types)
        device_layout.addWidget(QLabel("대상 장비 OS 유형:"))
        device_layout.addWidget(self.combo_os_type)

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        device_button_layout = QHBoxLayout()
        self.btn_add_device = QPushButton("장비 추가")
        self.btn_remove_device = QPushButton("장비 삭제")
        device_button_layout.addWidget(self.btn_add_device)
        device_button_layout.addWidget(self.btn_remove_device)
        device_layout.addLayout(device_button_layout)
        device_layout.addWidget(self.device_list)
        device_management_group.setLayout(device_layout)

        # --- 중앙 패널: 계층적 구성 탭 ---
        config_group = QGroupBox("2. 구성 편집")
        config_layout = QVBoxLayout()
        self.main_tabs = QTabWidget()

        # 각 모듈에 대한 탭 생성
        self.main_tabs.addTab(self._create_global_tab(), "Global")
        self.main_tabs.addTab(self._create_interface_tab(), "Interface")
        self.main_tabs.addTab(self._create_vlan_tab(), "VLAN")
        # ! --- 추가된 부분 시작 ---
        self.main_tabs.addTab(self._create_switching_tab(), "Switching")
        # ! --- 추가된 부분 끝 ---
        self.main_tabs.addTab(self._create_routing_tab(), "Routing")
        self.main_tabs.addTab(self._create_ha_tab(), "HA (고가용성)")
        self.main_tabs.addTab(self._create_security_tab(), "Security")  # ! --- 수정된 부분 ---

        config_layout.addWidget(self.main_tabs)
        config_group.setLayout(config_layout)

        # --- 오른쪽 패널: 실행 및 로그 ---
        execution_group = QGroupBox("3. 실행 및 로그")
        execution_layout = QVBoxLayout()
        self.btn_apply = QPushButton("구성 적용")
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        execution_layout.addWidget(self.btn_apply)
        execution_layout.addWidget(self.log_output)
        execution_group.setLayout(execution_layout)

        main_layout.addWidget(device_management_group, 1)
        main_layout.addWidget(config_group, 3)
        main_layout.addWidget(execution_group, 2)

    def _create_scrollable_tab(self):
        """탭 내부에 스크롤을 추가하기 위한 헬퍼 함수"""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)
        return tab_widget, scroll_layout

    def _create_global_tab(self):
        tab, layout = self._create_scrollable_tab()

        # Hostname & General Service
        group_hostname = QGroupBox("Hostname & General Service")
        form_hostname = QFormLayout()
        self.le_hostname = QLineEdit()
        self.le_hostname.setPlaceholderText("예: SW-CORE-01")
        self.cb_service_timestamps = QCheckBox()
        self.cb_service_password_encryption = QCheckBox()
        self.cb_service_call_home = QCheckBox()
        form_hostname.addRow("Hostname:", self.le_hostname)
        form_hostname.addRow("service timestamps debug/log", self.cb_service_timestamps)
        form_hostname.addRow("service password-encryption", self.cb_service_password_encryption)
        form_hostname.addRow("no service call-home", self.cb_service_call_home)
        group_hostname.setLayout(form_hostname)
        layout.addWidget(group_hostname)

        # DNS & Domain
        group_dns = QGroupBox("DNS & Domain")
        form_dns = QFormLayout()
        self.le_domain_name = QLineEdit()
        self.le_domain_name.setPlaceholderText("예: company.com")
        self.dns_table = QTableWidget(0, 2)
        self.dns_table.setHorizontalHeaderLabels(["DNS 서버 IP", "VRF (선택사항)"])
        self.dns_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.btn_add_dns = QPushButton("DNS 서버 추가")
        self.btn_remove_dns = QPushButton("DNS 서버 삭제")
        form_dns.addRow("Domain Name:", self.le_domain_name)
        form_dns.addRow(self.btn_add_dns, self.btn_remove_dns)
        form_dns.addRow("DNS Servers:", self.dns_table)
        group_dns.setLayout(form_dns)
        layout.addWidget(group_dns)

        # Clock & Timezone
        group_clock = QGroupBox("Clock & Timezone")
        form_clock = QFormLayout()
        self.combo_timezone = QComboBox()
        timezones = [
            "UTC 0", "KST 9", "JST 9", "CST 8", "EST -5",
            "PST -8", "GMT 0", "CET 1", "Custom"
        ]
        self.combo_timezone.addItems(timezones)
        self.combo_timezone.setCurrentText("KST 9")  # 기본값 한국 시간
        self.le_custom_timezone = QLineEdit()
        self.le_custom_timezone.setPlaceholderText("예: Asia/Seoul")
        self.le_custom_timezone.setEnabled(False)
        form_clock.addRow("Timezone:", self.combo_timezone)
        form_clock.addRow("Custom Timezone:", self.le_custom_timezone)
        group_clock.setLayout(form_clock)
        layout.addWidget(group_clock)

        # Logging
        group_logging = QGroupBox("Logging")
        form_logging = QFormLayout()
        self.combo_logging_level = QComboBox()
        self.combo_logging_level.addItems([
            "informational (6)", "warnings (4)", "errors (3)",
            "critical (2)", "debugging (7)"
        ])
        self.combo_logging_level.setCurrentText("informational (6)")
        self.cb_logging_console = QCheckBox()
        self.cb_logging_console.setChecked(True)
        self.cb_logging_buffered = QCheckBox()
        self.cb_logging_buffered.setChecked(True)
        self.le_logging_buffer_size = QLineEdit()
        self.le_logging_buffer_size.setPlaceholderText("예: 32000")
        self.le_logging_buffer_size.setText("32000")

        self.logging_table = QTableWidget(0, 2)
        self.logging_table.setHorizontalHeaderLabels(["로깅 서버 IP", "VRF (선택사항)"])
        self.logging_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.btn_add_log_host = QPushButton("로깅 서버 추가")
        self.btn_remove_log_host = QPushButton("로깅 서버 삭제")

        form_logging.addRow("Logging Level:", self.combo_logging_level)
        form_logging.addRow("Console Logging:", self.cb_logging_console)
        form_logging.addRow("Buffered Logging:", self.cb_logging_buffered)
        form_logging.addRow("Buffer Size:", self.le_logging_buffer_size)
        form_logging.addRow(self.btn_add_log_host, self.btn_remove_log_host)
        form_logging.addRow("Remote Logging Hosts:", self.logging_table)
        group_logging.setLayout(form_logging)
        layout.addWidget(group_logging)

        # NTP
        group_ntp = QGroupBox("NTP")
        form_ntp = QFormLayout()
        self.cb_ntp_authenticate = QCheckBox()
        self.le_ntp_master_stratum = QLineEdit()
        self.le_ntp_master_stratum.setPlaceholderText("예: 8 (없으면 비워두세요)")
        self.ntp_table = QTableWidget(0, 4)
        self.ntp_table.setHorizontalHeaderLabels(["NTP 서버 IP", "Prefer", "Key ID", "VRF"])
        self.ntp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.btn_add_ntp = QPushButton("NTP 서버 추가")
        self.btn_remove_ntp = QPushButton("NTP 서버 삭제")

        form_ntp.addRow("NTP Authentication:", self.cb_ntp_authenticate)
        form_ntp.addRow("Master Stratum:", self.le_ntp_master_stratum)
        form_ntp.addRow(self.btn_add_ntp, self.btn_remove_ntp)
        form_ntp.addRow("NTP Servers:", self.ntp_table)
        group_ntp.setLayout(form_ntp)
        layout.addWidget(group_ntp)

        # Management Interface
        group_mgmt = QGroupBox("Management Interface")
        form_mgmt = QFormLayout()
        self.combo_mgmt_interface = QComboBox()
        mgmt_interfaces = [
            "None", "GigabitEthernet0/0", "Management1", "Management0",
            "Vlan1", "FastEthernet0", "Custom"
        ]
        self.combo_mgmt_interface.addItems(mgmt_interfaces)
        self.le_custom_mgmt_interface = QLineEdit()
        self.le_custom_mgmt_interface.setPlaceholderText("예: GigabitEthernet1/0/1")
        self.le_custom_mgmt_interface.setEnabled(False)
        self.le_mgmt_ip = QLineEdit()
        self.le_mgmt_ip.setPlaceholderText("예: 192.168.1.100")
        self.le_mgmt_subnet = QLineEdit()
        self.le_mgmt_subnet.setPlaceholderText("예: 255.255.255.0 또는 /24")
        self.le_mgmt_gateway = QLineEdit()
        self.le_mgmt_gateway.setPlaceholderText("예: 192.168.1.1")
        self.le_mgmt_vrf = QLineEdit()
        self.le_mgmt_vrf.setPlaceholderText("예: Mgmt-intf (선택사항)")

        form_mgmt.addRow("Management Interface:", self.combo_mgmt_interface)
        form_mgmt.addRow("Custom Interface:", self.le_custom_mgmt_interface)
        form_mgmt.addRow("IP Address:", self.le_mgmt_ip)
        form_mgmt.addRow("Subnet Mask:", self.le_mgmt_subnet)
        form_mgmt.addRow("Gateway:", self.le_mgmt_gateway)
        form_mgmt.addRow("VRF:", self.le_mgmt_vrf)
        group_mgmt.setLayout(form_mgmt)
        layout.addWidget(group_mgmt)

        # Banner
        group_banner = QGroupBox("Login Banner")
        banner_layout = QVBoxLayout()
        self.cb_enable_banner = QCheckBox("Enable Login Banner")
        self.te_banner_text = QPlainTextEdit()
        self.te_banner_text.setMaximumHeight(100)
        self.te_banner_text.setPlaceholderText(
            "예:\n"
            "********************************\n"
            "* Authorized Access Only      *\n"
            "* All activities monitored    *\n"
            "********************************"
        )
        self.te_banner_text.setEnabled(False)
        banner_layout.addWidget(self.cb_enable_banner)
        banner_layout.addWidget(QLabel("Banner Text:"))
        banner_layout.addWidget(self.te_banner_text)
        group_banner.setLayout(banner_layout)
        layout.addWidget(group_banner)

        # Archive & Configuration Management
        group_archive = QGroupBox("Configuration Archive")
        form_archive = QFormLayout()
        self.cb_archive_config = QCheckBox("Enable Configuration Archive")
        self.le_archive_path = QLineEdit()
        self.le_archive_path.setPlaceholderText("예: bootflash:archive")
        self.le_archive_path.setEnabled(False)
        self.le_archive_max_files = QLineEdit()
        self.le_archive_max_files.setPlaceholderText("예: 10")
        self.le_archive_max_files.setEnabled(False)
        self.cb_archive_time_period = QCheckBox("Time-based Archive")
        self.le_archive_time_period = QLineEdit()
        self.le_archive_time_period.setPlaceholderText("예: 1440 (minutes)")
        self.le_archive_time_period.setEnabled(False)

        form_archive.addRow(self.cb_archive_config)
        form_archive.addRow("Archive Path:", self.le_archive_path)
        form_archive.addRow("Max Files:", self.le_archive_max_files)
        form_archive.addRow(self.cb_archive_time_period, self.le_archive_time_period)
        group_archive.setLayout(form_archive)
        layout.addWidget(group_archive)

        layout.addStretch()
        return tab

    def _create_interface_tab(self):
        tab, layout = self._create_scrollable_tab()

        # 기본적인 인터페이스 설정 UI 추가
        group_interface = QGroupBox("Physical Interface Configuration")
        form_interface = QFormLayout()

        # 인터페이스 타입 선택
        self.combo_interface_type = QComboBox()
        self.combo_interface_type.addItems(["Access", "Trunk", "Routed"])
        form_interface.addRow("Interface Mode:", self.combo_interface_type)

        # 기본 설정
        self.le_interface_description = QLineEdit()
        self.le_interface_description.setPlaceholderText("예: To Server Farm")
        form_interface.addRow("Description:", self.le_interface_description)

        group_interface.setLayout(form_interface)
        layout.addWidget(group_interface)

        # 추후 상세 구현 예정 메시지
        layout.addWidget(QLabel("인터페이스 설정 (Trunk, Access, Port-Channel) 기능이 여기에 구현됩니다."))
        layout.addStretch()
        return tab

    def _create_vlan_tab(self):
        tab, layout = self._create_scrollable_tab()

        # VLAN 관리 테이블
        group_vlan = QGroupBox("VLAN Management")
        vlan_layout = QVBoxLayout()

        self.vlan_table = QTableWidget(0, 3)
        self.vlan_table.setHorizontalHeaderLabels(["VLAN ID", "VLAN Name", "Description"])
        self.vlan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        vlan_button_layout = QHBoxLayout()
        self.btn_add_vlan = QPushButton("VLAN 추가")
        self.btn_remove_vlan = QPushButton("VLAN 삭제")
        vlan_button_layout.addWidget(self.btn_add_vlan)
        vlan_button_layout.addWidget(self.btn_remove_vlan)

        vlan_layout.addLayout(vlan_button_layout)
        vlan_layout.addWidget(self.vlan_table)
        group_vlan.setLayout(vlan_layout)
        layout.addWidget(group_vlan)

        layout.addWidget(QLabel("VLAN 정의 및 SVI 설정 기능이 여기에 구현됩니다."))
        layout.addStretch()
        return tab

    # ! --- 추가된 부분 시작 ---
    def _create_switching_tab(self):
        tab, layout = self._create_scrollable_tab()

        # Spanning Tree
        group_stp = QGroupBox("Spanning Tree Protocol")
        form_stp = QFormLayout()
        self.combo_stp_mode = QComboBox()
        self.combo_stp_mode.addItems(["pvst", "rapid-pvst", "mst"])
        self.cb_stp_portfast_default = QCheckBox("spanning-tree portfast default")
        self.cb_stp_bpduguard_default = QCheckBox("spanning-tree portfast bpduguard default")
        form_stp.addRow("STP Mode:", self.combo_stp_mode)
        form_stp.addRow(self.cb_stp_portfast_default)
        form_stp.addRow(self.cb_stp_bpduguard_default)
        group_stp.setLayout(form_stp)
        layout.addWidget(group_stp)

        layout.addStretch()
        return tab

    # ! --- 추가된 부분 끝 ---

    def _create_routing_tab(self):
        tab, layout = self._create_scrollable_tab()
        layout.addWidget(QLabel("Static, OSPF, BGP, VRRP 등 라우팅 설정 기능이 여기에 구현됩니다."))
        layout.addStretch()
        return tab

    def _create_ha_tab(self):
        tab, layout = self._create_scrollable_tab()
        layout.addWidget(QLabel("StackWise Virtual (IOS-XE), vPC (NX-OS) 등 고가용성 설정 기능이 여기에 구현됩니다."))
        layout.addStretch()
        return tab

    def _create_security_tab(self):
        tab, layout = self._create_scrollable_tab()

        # AAA
        group_aaa = QGroupBox("AAA")
        form_aaa = QFormLayout()
        self.cb_aaa_new_model = QCheckBox("aaa new-model 활성화")
        self.le_aaa_auth_login = QLineEdit()
        self.le_aaa_auth_login.setPlaceholderText("예: default group tacacs+ local")
        self.le_aaa_auth_exec = QLineEdit()
        self.le_aaa_auth_exec.setPlaceholderText("예: default group tacacs+ local")

        self.aaa_server_table = QTableWidget(0, 3)
        self.aaa_server_table.setHorizontalHeaderLabels(["서버 종류 (tacacs+/radius)", "그룹 이름", "서버 IP 리스트 (쉼표로 구분)"])
        self.aaa_server_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.btn_add_aaa_group = QPushButton("AAA 서버 그룹 추가")
        self.btn_remove_aaa_group = QPushButton("AAA 서버 그룹 삭제")

        form_aaa.addRow(self.cb_aaa_new_model)
        form_aaa.addRow("Authentication Login:", self.le_aaa_auth_login)
        form_aaa.addRow("Authorization Exec:", self.le_aaa_auth_exec)
        form_aaa.addRow(self.btn_add_aaa_group, self.btn_remove_aaa_group)
        form_aaa.addRow("AAA Server Groups:", self.aaa_server_table)
        group_aaa.setLayout(form_aaa)
        layout.addWidget(group_aaa)

        # ! --- 추가된 부분 시작 ---
        # Local Users
        group_users = QGroupBox("Local User Accounts")
        users_layout = QVBoxLayout()
        self.users_table = QTableWidget(0, 3)
        self.users_table.setHorizontalHeaderLabels(["Username", "Privilege (1-15)", "Password"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        users_button_layout = QHBoxLayout()
        self.btn_add_user = QPushButton("사용자 추가")
        self.btn_remove_user = QPushButton("사용자 삭제")
        users_button_layout.addWidget(self.btn_add_user)
        users_button_layout.addWidget(self.btn_remove_user)
        users_layout.addLayout(users_button_layout)
        users_layout.addWidget(self.users_table)
        group_users.setLayout(users_layout)
        layout.addWidget(group_users)

        # Line Configuration
        group_line = QGroupBox("Line Configuration (Console/VTY)")
        form_line = QFormLayout()
        self.le_con_exec_timeout = QLineEdit("15 0")
        self.cb_con_logging_sync = QCheckBox()
        self.cb_con_logging_sync.setChecked(True)
        self.le_vty_exec_timeout = QLineEdit("15 0")
        self.combo_vty_transport = QComboBox()
        self.combo_vty_transport.addItems(["ssh", "telnet", "none", "all"])
        self.combo_vty_transport.setCurrentText("ssh")
        form_line.addRow("Console Timeout (min sec):", self.le_con_exec_timeout)
        form_line.addRow("Console Logging Synchronous:", self.cb_con_logging_sync)
        form_line.addRow("VTY Timeout (min sec):", self.le_vty_exec_timeout)
        form_line.addRow("VTY Transport Input:", self.combo_vty_transport)
        group_line.setLayout(form_line)
        layout.addWidget(group_line)

        # SNMP
        group_snmp = QGroupBox("SNMP")
        snmp_layout = QVBoxLayout()
        self.snmp_community_table = QTableWidget(0, 3)
        self.snmp_community_table.setHorizontalHeaderLabels(
            ["Community String", "Permission (RO/RW)", "ACL (Optional)"])
        self.snmp_community_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        snmp_button_layout = QHBoxLayout()
        self.btn_add_snmp = QPushButton("Community 추가")
        self.btn_remove_snmp = QPushButton("Community 삭제")
        snmp_button_layout.addWidget(self.btn_add_snmp)
        snmp_button_layout.addWidget(self.btn_remove_snmp)
        snmp_form = QFormLayout()
        self.le_snmp_location = QLineEdit()
        self.le_snmp_contact = QLineEdit()
        snmp_form.addRow("Location:", self.le_snmp_location)
        snmp_form.addRow("Contact:", self.le_snmp_contact)
        snmp_layout.addLayout(snmp_form)
        snmp_layout.addLayout(snmp_button_layout)
        snmp_layout.addWidget(self.snmp_community_table)
        group_snmp.setLayout(snmp_layout)
        layout.addWidget(group_snmp)

        # Security Hardening
        group_hardening = QGroupBox("Security Hardening")
        form_hardening = QFormLayout()
        self.cb_no_ip_http = QCheckBox("no ip http server")
        self.cb_no_ip_http.setChecked(True)
        self.cb_no_cdp = QCheckBox("no cdp run")
        self.cb_lldp = QCheckBox("lldp run")
        self.cb_lldp.setChecked(True)
        form_hardening.addRow(self.cb_no_ip_http)
        form_hardening.addRow(self.cb_no_cdp)
        form_hardening.addRow(self.cb_lldp)
        group_hardening.setLayout(form_hardening)
        layout.addWidget(group_hardening)
        # ! --- 추가된 부분 끝 ---

        layout.addStretch()
        return tab

    def _connect_signals(self):
        self.btn_add_device.clicked.connect(self.ui_add_device)
        self.btn_remove_device.clicked.connect(self.ui_remove_device)
        self.btn_apply.clicked.connect(self.run_config_task)

        # Global Tab 시그널 연결
        self.btn_add_log_host.clicked.connect(lambda: self.ui_add_table_row(self.logging_table))
        self.btn_remove_log_host.clicked.connect(lambda: self.ui_remove_table_row(self.logging_table))
        self.btn_add_ntp.clicked.connect(lambda: self.ui_add_table_row(self.ntp_table))
        self.btn_remove_ntp.clicked.connect(lambda: self.ui_remove_table_row(self.ntp_table))
        self.btn_add_dns.clicked.connect(lambda: self.ui_add_table_row(self.dns_table))
        self.btn_remove_dns.clicked.connect(lambda: self.ui_remove_table_row(self.dns_table))

        # 동적 UI 제어
        self.combo_timezone.currentTextChanged.connect(self._on_timezone_changed)
        self.combo_mgmt_interface.currentTextChanged.connect(self._on_mgmt_interface_changed)
        self.cb_enable_banner.toggled.connect(self.te_banner_text.setEnabled)
        self.cb_archive_config.toggled.connect(self._on_archive_config_toggled)
        self.cb_archive_time_period.toggled.connect(self.le_archive_time_period.setEnabled)

        # Security Tab 시그널 연결
        self.btn_add_aaa_group.clicked.connect(lambda: self.ui_add_table_row(self.aaa_server_table))
        self.btn_remove_aaa_group.clicked.connect(lambda: self.ui_remove_table_row(self.aaa_server_table))
        # ! --- 추가된 부분 시작 ---
        self.btn_add_user.clicked.connect(lambda: self.ui_add_table_row(self.users_table))
        self.btn_remove_user.clicked.connect(lambda: self.ui_remove_table_row(self.users_table))
        self.btn_add_snmp.clicked.connect(lambda: self.ui_add_table_row(self.snmp_community_table))
        self.btn_remove_snmp.clicked.connect(lambda: self.ui_remove_table_row(self.snmp_community_table))
        # ! --- 추가된 부분 끝 ---

        # VLAN 관리 버튼 연결
        if hasattr(self, 'btn_add_vlan'):
            self.btn_add_vlan.clicked.connect(lambda: self.ui_add_table_row(self.vlan_table))
            self.btn_remove_vlan.clicked.connect(lambda: self.ui_remove_table_row(self.vlan_table))

    def _on_timezone_changed(self, timezone):
        """타임존 선택 변경 시 커스텀 입력 필드 활성화/비활성화"""
        self.le_custom_timezone.setEnabled(timezone == "Custom")
        if timezone != "Custom":
            self.le_custom_timezone.clear()

    def _on_mgmt_interface_changed(self, interface):
        """관리 인터페이스 선택 변경 시 커스텀 입력 필드 활성화/비활성화"""
        self.le_custom_mgmt_interface.setEnabled(interface == "Custom")
        if interface != "Custom":
            self.le_custom_mgmt_interface.clear()

    def _on_archive_config_toggled(self, checked):
        """Configuration Archive 체크박스 변경 시 관련 필드들 활성화/비활성화"""
        self.le_archive_path.setEnabled(checked)
        self.le_archive_max_files.setEnabled(checked)
        self.cb_archive_time_period.setEnabled(checked)
        if checked and self.cb_archive_time_period.isChecked():
            self.le_archive_time_period.setEnabled(True)
        else:
            self.le_archive_time_period.setEnabled(False)

        if not checked:
            self.le_archive_path.clear()
            self.le_archive_max_files.clear()
            self.cb_archive_time_period.setChecked(False)
            self.le_archive_time_period.clear()

    def _gather_data_from_ui(self):
        """하드코딩된 UI에서 모든 사용자 입력값을 수집합니다."""
        # ! --- 수정된 부분 시작 ---
        data = {'global': {}, 'interfaces': {}, 'vlans': {}, 'switching': {}, 'routing': {}, 'ha': {}, 'security': {}}

        # Global Tab
        data['global']['hostname'] = self.le_hostname.text()
        # ... (기존 Global 설정 수집 코드는 동일)
        # ! --- (이하 Global, Interface, VLAN 데이터 수집 코드는 기존과 동일하여 생략) ---

        # Global Tab - 기본 설정
        data['global']['hostname'] = self.le_hostname.text()
        data['global']['service_timestamps'] = self.cb_service_timestamps.isChecked()
        data['global']['service_password_encryption'] = self.cb_service_password_encryption.isChecked()
        data['global']['service_call_home'] = self.cb_service_call_home.isChecked()

        # DNS & Domain 설정
        data['global']['domain_name'] = self.le_domain_name.text()
        dns_servers = []
        for row in range(self.dns_table.rowCount()):
            ip_item = self.dns_table.item(row, 0)
            vrf_item = self.dns_table.item(row, 1)
            if ip_item and ip_item.text():
                dns_servers.append({'ip': ip_item.text(), 'vrf': vrf_item.text() if vrf_item else ''})
        data['global']['dns_servers'] = dns_servers

        # Clock & Timezone 설정
        timezone = self.combo_timezone.currentText()
        if timezone == "Custom":
            data['global']['timezone'] = self.le_custom_timezone.text()
        else:
            data['global']['timezone'] = timezone

        # Logging 설정
        data['global']['logging_level'] = self.combo_logging_level.currentText()
        data['global']['logging_console'] = self.cb_logging_console.isChecked()
        data['global']['logging_buffered'] = self.cb_logging_buffered.isChecked()
        data['global']['logging_buffer_size'] = self.le_logging_buffer_size.text()

        log_hosts = []
        for row in range(self.logging_table.rowCount()):
            ip_item = self.logging_table.item(row, 0)
            vrf_item = self.logging_table.item(row, 1)
            if ip_item and ip_item.text():
                log_hosts.append({'ip': ip_item.text(), 'vrf': vrf_item.text() if vrf_item else ''})
        data['global']['logging_hosts'] = log_hosts

        # NTP 설정
        data['global']['ntp_authenticate'] = self.cb_ntp_authenticate.isChecked()
        data['global']['ntp_master_stratum'] = self.le_ntp_master_stratum.text()

        ntp_servers = []
        for row in range(self.ntp_table.rowCount()):
            ip_item = self.ntp_table.item(row, 0)
            prefer_item = self.ntp_table.item(row, 1)
            key_item = self.ntp_table.item(row, 2)
            vrf_item = self.ntp_table.item(row, 3)
            if ip_item and ip_item.text():
                ntp_servers.append({
                    'ip': ip_item.text(),
                    'prefer': prefer_item.text().lower() == 'true' if prefer_item and prefer_item.text() else False,
                    'key_id': key_item.text() if key_item else '',
                    'vrf': vrf_item.text() if vrf_item else ''
                })
        data['global']['ntp_servers'] = ntp_servers

        # Management Interface 설정
        mgmt_interface = self.combo_mgmt_interface.currentText()
        if mgmt_interface == "Custom":
            mgmt_interface = self.le_custom_mgmt_interface.text()
        elif mgmt_interface == "None":
            mgmt_interface = ""

        data['global']['management'] = {
            'interface': mgmt_interface,
            'ip': self.le_mgmt_ip.text(),
            'subnet': self.le_mgmt_subnet.text(),
            'gateway': self.le_mgmt_gateway.text(),
            'vrf': self.le_mgmt_vrf.text()
        }

        # Banner 설정
        data['global']['banner'] = {
            'enabled': self.cb_enable_banner.isChecked(),
            'text': self.te_banner_text.toPlainText() if self.cb_enable_banner.isChecked() else ''
        }

        # Archive 설정
        data['global']['archive'] = {
            'enabled': self.cb_archive_config.isChecked(),
            'path': self.le_archive_path.text() if self.cb_archive_config.isChecked() else '',
            'max_files': self.le_archive_max_files.text() if self.cb_archive_config.isChecked() else '',
            'time_period_enabled': self.cb_archive_time_period.isChecked(),
            'time_period': self.le_archive_time_period.text() if self.cb_archive_time_period.isChecked() else ''
        }

        # Interface Tab
        data['interfaces']['type'] = self.combo_interface_type.currentText()
        data['interfaces']['description'] = self.le_interface_description.text()

        # VLAN Tab
        vlans = []
        for row in range(self.vlan_table.rowCount()):
            vlan_id_item = self.vlan_table.item(row, 0)
            vlan_name_item = self.vlan_table.item(row, 1)
            vlan_desc_item = self.vlan_table.item(row, 2)
            if vlan_id_item and vlan_id_item.text():
                vlans.append({
                    'id': vlan_id_item.text(),
                    'name': vlan_name_item.text() if vlan_name_item else '',
                    'description': vlan_desc_item.text() if vlan_desc_item else ''
                })
        data['vlans']['list'] = vlans

        # ! --- 추가된 부분 시작 ---
        # Switching Tab
        data['switching']['stp_mode'] = self.combo_stp_mode.currentText()
        data['switching']['stp_portfast_default'] = self.cb_stp_portfast_default.isChecked()
        data['switching']['stp_bpduguard_default'] = self.cb_stp_bpduguard_default.isChecked()

        # Security Tab
        sec = data['security']
        sec['aaa_new_model'] = self.cb_aaa_new_model.isChecked()
        sec['aaa_auth_login'] = self.le_aaa_auth_login.text()
        sec['aaa_auth_exec'] = self.le_aaa_auth_exec.text()

        # AAA 서버 그룹
        sec['aaa_groups'] = []
        for row in range(self.aaa_server_table.rowCount()):
            type_item = self.aaa_server_table.item(row, 0)
            group_item = self.aaa_server_table.item(row, 1)
            servers_item = self.aaa_server_table.item(row, 2)
            if type_item and group_item and servers_item:
                sec['aaa_groups'].append({
                    'type': type_item.text(),
                    'group_name': group_item.text(),
                    'servers': [s.strip() for s in servers_item.text().split(',') if s.strip()]
                })

        # Local Users
        sec['local_users'] = []
        for row in range(self.users_table.rowCount()):
            user_item = self.users_table.item(row, 0)
            priv_item = self.users_table.item(row, 1)
            pass_item = self.users_table.item(row, 2)
            if user_item and user_item.text():
                sec['local_users'].append({
                    'username': user_item.text(),
                    'privilege': priv_item.text() if priv_item else '1',
                    'password': pass_item.text() if pass_item else ''
                })

        # Line Config
        sec['line_config'] = {
            'con_timeout': self.le_con_exec_timeout.text(),
            'con_logging_sync': self.cb_con_logging_sync.isChecked(),
            'vty_timeout': self.le_vty_exec_timeout.text(),
            'vty_transport': self.combo_vty_transport.currentText()
        }

        # SNMP
        sec['snmp'] = {
            'location': self.le_snmp_location.text(),
            'contact': self.le_snmp_contact.text(),
            'communities': []
        }
        for row in range(self.snmp_community_table.rowCount()):
            comm_item = self.snmp_community_table.item(row, 0)
            perm_item = self.snmp_community_table.item(row, 1)
            acl_item = self.snmp_community_table.item(row, 2)
            if comm_item and comm_item.text():
                sec['snmp']['communities'].append({
                    'community': comm_item.text(),
                    'permission': perm_item.text() if perm_item else 'RO',
                    'acl': acl_item.text() if acl_item else ''
                })

        # Security Hardening
        sec['hardening'] = {
            'no_ip_http': self.cb_no_ip_http.isChecked(),
            'no_cdp': self.cb_no_cdp.isChecked(),
            'lldp': self.cb_lldp.isChecked()
        }
        # ! --- 추가된 부분 끝 ---

        return data

    def run_config_task(self):
        target_hosts = self._get_selected_devices()
        if not target_hosts: return

        user_input_data = self._gather_data_from_ui()
        os_type = self.combo_os_type.currentText()

        try:
            playbook_data = self.config_manager.generate_playbook(os_type, user_input_data)

            self.log_output.appendPlainText(f"===== {', '.join(target_hosts)}에 구성 적용 시작 ({os_type}) =====")
            status, result_stdout = self.ansible_engine.execute_configuration(target_hosts, playbook_data)

            if status == 'successful':
                self.log_output.appendPlainText("구성 적용 성공.")
            else:
                self.log_output.appendPlainText("구성 적용 실패.")

            self.log_output.appendPlainText("--- Ansible 실행 결과 (모의) ---")
            self.log_output.appendPlainText(result_stdout)
            self.log_output.appendPlainText("--------------------------\n")
        except Exception as e:
            self.log_output.appendPlainText(f"오류 발생: {str(e)}")

    # --- UI 헬퍼 함수들 ---
    def ui_add_device(self):
        text, ok = QInputDialog.getText(self, '장비 추가', '장비 IP 또는 호스트명 입력:')
        if ok and text:
            self.device_list.addItem(text)

    def ui_remove_device(self):
        for item in self.device_list.selectedItems():
            self.device_list.takeItem(self.device_list.row(item))

    def ui_add_table_row(self, table_widget):
        table_widget.insertRow(table_widget.rowCount())

    def ui_remove_table_row(self, table_widget):
        current_row = table_widget.currentRow()
        if current_row > -1:
            table_widget.removeRow(current_row)

    def _get_selected_devices(self):
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "장비를 먼저 선택해주세요.")
            return None
        return [item.text() for item in selected_items]