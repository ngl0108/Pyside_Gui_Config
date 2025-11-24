# cisco_config_manager/ui/tabs/global_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QTableWidget, QPushButton, QHeaderView, QCheckBox,
    QComboBox, QPlainTextEdit, QScrollArea, QHBoxLayout, QLabel
)


class GlobalTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Hostname & General Service
        group_hostname = QGroupBox("Hostname & General Service")
        form_hostname = QFormLayout()
        self.le_hostname = QLineEdit()
        self.cb_service_timestamps = QCheckBox("service timestamps debug/log")
        self.cb_service_password_encryption = QCheckBox("service password-encryption")
        self.cb_service_call_home = QCheckBox("no service call-home")
        form_hostname.addRow("Hostname:", self.le_hostname)
        form_hostname.addRow(self.cb_service_timestamps)
        form_hostname.addRow(self.cb_service_password_encryption)
        form_hostname.addRow(self.cb_service_call_home)
        group_hostname.setLayout(form_hostname)
        layout.addWidget(group_hostname)

        # DNS & Domain
        group_dns = QGroupBox("DNS & Domain")
        form_dns = QFormLayout()
        self.le_domain_name = QLineEdit()
        self.dns_table = QTableWidget(0, 2)
        self.dns_table.setHorizontalHeaderLabels(["DNS 서버 IP", "VRF (선택사항)"])
        self.dns_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        dns_button_layout = QHBoxLayout()
        self.btn_add_dns = QPushButton("DNS 서버 추가")
        self.btn_remove_dns = QPushButton("DNS 서버 삭제")
        dns_button_layout.addWidget(self.btn_add_dns)
        dns_button_layout.addWidget(self.btn_remove_dns)

        form_dns.addRow("Domain Name:", self.le_domain_name)
        form_dns.addRow(dns_button_layout)
        form_dns.addRow(self.dns_table)
        group_dns.setLayout(form_dns)
        layout.addWidget(group_dns)

        # Clock & Timezone
        group_clock = QGroupBox("Clock & Timezone")
        form_clock = QFormLayout()
        self.combo_timezone = QComboBox()
        self.combo_timezone.addItems([
            "UTC 0", "KST 9", "JST 9", "CST 8", "EST -5", "PST -8",
            "GMT 0", "CET 1", "Custom"
        ])
        self.le_custom_timezone = QLineEdit()
        self.le_custom_timezone.setEnabled(False)
        self.le_custom_timezone.setPlaceholderText("예: KST 9")

        self.cb_summer_time = QCheckBox("Summer-time (Daylight Saving) 적용")
        self.le_summer_time_zone = QLineEdit()
        self.le_summer_time_zone.setPlaceholderText("예: KST")
        self.le_summer_time_zone.setEnabled(False)

        form_clock.addRow("Timezone:", self.combo_timezone)
        form_clock.addRow("Custom Timezone:", self.le_custom_timezone)
        form_clock.addRow(self.cb_summer_time)
        form_clock.addRow("Summer Time Zone:", self.le_summer_time_zone)
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

        self.cb_logging_console = QCheckBox("Console Logging")
        self.cb_logging_console.setChecked(True)
        self.cb_logging_buffered = QCheckBox("Buffered Logging")
        self.cb_logging_buffered.setChecked(True)
        self.le_logging_buffer_size = QLineEdit("32000")

        self.logging_table = QTableWidget(0, 2)
        self.logging_table.setHorizontalHeaderLabels(["로깅 서버 IP", "VRF (선택사항)"])
        self.logging_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        logging_button_layout = QHBoxLayout()
        self.btn_add_log_host = QPushButton("로깅 서버 추가")
        self.btn_remove_log_host = QPushButton("로깅 서버 삭제")
        logging_button_layout.addWidget(self.btn_add_log_host)
        logging_button_layout.addWidget(self.btn_remove_log_host)

        form_logging.addRow("Logging Level:", self.combo_logging_level)
        form_logging.addRow(self.cb_logging_console)
        form_logging.addRow(self.cb_logging_buffered)
        form_logging.addRow("Buffer Size:", self.le_logging_buffer_size)
        form_logging.addRow(logging_button_layout)
        form_logging.addRow(self.logging_table)
        group_logging.setLayout(form_logging)
        layout.addWidget(group_logging)

        # NTP
        group_ntp = QGroupBox("NTP")
        form_ntp = QFormLayout()
        self.cb_ntp_authenticate = QCheckBox("NTP Authentication")
        self.le_ntp_master_stratum = QLineEdit()
        self.le_ntp_master_stratum.setPlaceholderText("예: 5")

        self.ntp_table = QTableWidget(0, 4)
        self.ntp_table.setHorizontalHeaderLabels(["NTP 서버 IP", "Prefer", "Key ID", "VRF"])
        self.ntp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        ntp_button_layout = QHBoxLayout()
        self.btn_add_ntp = QPushButton("NTP 서버 추가")
        self.btn_remove_ntp = QPushButton("NTP 서버 삭제")
        ntp_button_layout.addWidget(self.btn_add_ntp)
        ntp_button_layout.addWidget(self.btn_remove_ntp)

        form_ntp.addRow(self.cb_ntp_authenticate)
        form_ntp.addRow("Master Stratum:", self.le_ntp_master_stratum)
        form_ntp.addRow(ntp_button_layout)
        form_ntp.addRow(self.ntp_table)
        group_ntp.setLayout(form_ntp)
        layout.addWidget(group_ntp)

        # Management Interface
        group_mgmt = QGroupBox("Management Interface")
        form_mgmt = QFormLayout()
        self.combo_mgmt_interface = QComboBox()
        self.combo_mgmt_interface.addItems([
            "None", "GigabitEthernet0/0", "Management1", "Management0",
            "Vlan1", "FastEthernet0", "Custom"
        ])

        self.le_custom_mgmt_interface = QLineEdit()
        self.le_custom_mgmt_interface.setEnabled(False)
        self.le_custom_mgmt_interface.setPlaceholderText("예: GigabitEthernet0/1")

        self.le_mgmt_ip = QLineEdit()
        self.le_mgmt_ip.setPlaceholderText("예: 192.168.1.10")
        self.le_mgmt_subnet = QLineEdit()
        self.le_mgmt_subnet.setPlaceholderText("예: 255.255.255.0")
        self.le_mgmt_gateway = QLineEdit()
        self.le_mgmt_gateway.setPlaceholderText("예: 192.168.1.1")
        self.le_mgmt_vrf = QLineEdit()
        self.le_mgmt_vrf.setPlaceholderText("예: management")

        form_mgmt.addRow("Management Interface:", self.combo_mgmt_interface)
        form_mgmt.addRow("Custom Interface:", self.le_custom_mgmt_interface)
        form_mgmt.addRow("IP Address:", self.le_mgmt_ip)
        form_mgmt.addRow("Subnet Mask:", self.le_mgmt_subnet)
        form_mgmt.addRow("Gateway:", self.le_mgmt_gateway)
        form_mgmt.addRow("VRF:", self.le_mgmt_vrf)
        group_mgmt.setLayout(form_mgmt)
        layout.addWidget(group_mgmt)

        # Login Banner
        group_banner = QGroupBox("Login Banner")
        form_banner = QFormLayout()
        self.cb_enable_banner = QCheckBox("Enable Login Banner")
        self.te_banner_text = QPlainTextEdit()
        self.te_banner_text.setMaximumHeight(100)
        self.te_banner_text.setEnabled(False)
        self.te_banner_text.setPlaceholderText("MOTD 배너 텍스트를 입력하세요...")

        form_banner.addRow(self.cb_enable_banner)
        form_banner.addRow("Banner Text:", self.te_banner_text)
        group_banner.setLayout(form_banner)
        layout.addWidget(group_banner)

        # Configuration Archive
        self.group_archive = QGroupBox("Configuration Archive")
        form_archive = QFormLayout()
        self.cb_archive_config = QCheckBox("Enable Configuration Archive")

        self.le_archive_path = QLineEdit()
        self.le_archive_path.setEnabled(False)
        self.le_archive_path.setPlaceholderText("예: flash:archive")

        self.le_archive_max_files = QLineEdit()
        self.le_archive_max_files.setEnabled(False)
        self.le_archive_max_files.setPlaceholderText("예: 10")

        self.cb_archive_time_period = QCheckBox("Time-based Archive")
        self.le_archive_time_period = QLineEdit()
        self.le_archive_time_period.setEnabled(False)
        self.le_archive_time_period.setPlaceholderText("예: 60 (분)")

        form_archive.addRow(self.cb_archive_config)
        form_archive.addRow("Archive Path:", self.le_archive_path)
        form_archive.addRow("Max Files:", self.le_archive_max_files)
        form_archive.addRow(self.cb_archive_time_period, self.le_archive_time_period)
        self.group_archive.setLayout(form_archive)
        layout.addWidget(self.group_archive)

        # 시그널 연결
        self._connect_signals()

        layout.addStretch()

    def _connect_signals(self):
        """시그널 연결"""
        self.combo_timezone.currentTextChanged.connect(self._on_timezone_changed)
        self.cb_summer_time.toggled.connect(self.le_summer_time_zone.setEnabled)
        self.combo_mgmt_interface.currentTextChanged.connect(self._on_mgmt_interface_changed)
        self.cb_enable_banner.toggled.connect(self.te_banner_text.setEnabled)
        self.cb_archive_config.toggled.connect(self._on_archive_config_toggled)
        self.cb_archive_time_period.toggled.connect(self.le_archive_time_period.setEnabled)

    def _on_timezone_changed(self, timezone):
        """타임존 변경 핸들러"""
        self.le_custom_timezone.setEnabled(timezone == "Custom")

    def _on_mgmt_interface_changed(self, interface):
        """관리 인터페이스 변경 핸들러"""
        self.le_custom_mgmt_interface.setEnabled(interface == "Custom")

    def _on_archive_config_toggled(self, checked):
        """아카이브 설정 토글 핸들러"""
        self.le_archive_path.setEnabled(checked)
        self.le_archive_max_files.setEnabled(checked)
        self.cb_archive_time_period.setEnabled(checked)
        self.le_archive_time_period.setEnabled(
            checked and self.cb_archive_time_period.isChecked()
        )