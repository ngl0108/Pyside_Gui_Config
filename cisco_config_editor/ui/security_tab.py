# cisco_config_manager/ui/tabs/security_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QTableWidget, QPushButton, QHeaderView, QCheckBox,
    QComboBox, QScrollArea, QHBoxLayout, QLabel
)


class SecurityTab(QWidget):
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

        # AAA
        group_aaa = QGroupBox("AAA (Authentication, Authorization, Accounting)")
        form_aaa = QFormLayout()
        self.cb_aaa_new_model = QCheckBox("aaa new-model 활성화")

        self.le_aaa_auth_login = QLineEdit("default group tacacs+ local")
        self.le_aaa_auth_exec = QLineEdit("default group tacacs+ local")
        self.le_aaa_accounting = QLineEdit()
        self.le_aaa_accounting.setPlaceholderText("예: default start-stop group tacacs+")

        self.aaa_server_table = QTableWidget(0, 3)
        self.aaa_server_table.setHorizontalHeaderLabels(["서버 종류 (tacacs+/radius)", "그룹 이름", "서버 IP 리스트 (쉼표로 구분)"])
        self.aaa_server_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        aaa_button_layout = QHBoxLayout()
        self.btn_add_aaa_group = QPushButton("AAA 서버 그룹 추가")
        self.btn_remove_aaa_group = QPushButton("AAA 서버 그룹 삭제")
        aaa_button_layout.addWidget(self.btn_add_aaa_group)
        aaa_button_layout.addWidget(self.btn_remove_aaa_group)

        form_aaa.addRow(self.cb_aaa_new_model)
        form_aaa.addRow("Authentication Login:", self.le_aaa_auth_login)
        form_aaa.addRow("Authorization Exec:", self.le_aaa_auth_exec)
        form_aaa.addRow("Accounting:", self.le_aaa_accounting)
        form_aaa.addRow(aaa_button_layout)
        form_aaa.addRow(self.aaa_server_table)
        group_aaa.setLayout(form_aaa)
        layout.addWidget(group_aaa)

        # Local User Accounts
        group_users = QGroupBox("Local User Accounts")
        users_layout = QVBoxLayout()

        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels(["Username", "Privilege (1-15)", "Password", "Secret"])
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

        # Line Configuration (Console/VTY)
        group_line = QGroupBox("Line Configuration (Console/VTY)")
        form_line = QFormLayout()

        self.le_con_exec_timeout = QLineEdit("15 0")
        self.cb_con_logging_sync = QCheckBox()
        self.cb_con_logging_sync.setChecked(True)

        self.cb_con_auth_aaa = QCheckBox("Console Login Authentication (AAA)")
        self.le_con_auth_method = QLineEdit("default")
        self.le_con_auth_method.setEnabled(False)

        self.le_vty_range = QLineEdit("0 4")
        self.le_vty_exec_timeout = QLineEdit("15 0")

        self.combo_vty_transport = QComboBox()
        self.combo_vty_transport.addItems(["ssh", "telnet", "none", "all"])
        self.combo_vty_transport.setCurrentText("ssh")

        self.combo_vty_access_class = QComboBox()
        self.combo_vty_access_class.addItems(["", "ACL-1", "ACL-2", "ACL-3"])

        form_line.addRow("Console Timeout (min sec):", self.le_con_exec_timeout)
        form_line.addRow("Console Logging Synchronous:", self.cb_con_logging_sync)
        form_line.addRow(self.cb_con_auth_aaa, self.le_con_auth_method)
        form_line.addRow("VTY Line Range:", self.le_vty_range)
        form_line.addRow("VTY Timeout (min sec):", self.le_vty_exec_timeout)
        form_line.addRow("VTY Transport Input:", self.combo_vty_transport)
        form_line.addRow("VTY Access-Class IN:", self.combo_vty_access_class)
        group_line.setLayout(form_line)
        layout.addWidget(group_line)

        # SNMP
        group_snmp = QGroupBox("SNMP Configuration")
        snmp_layout = QVBoxLayout()

        snmp_form = QFormLayout()
        self.le_snmp_location = QLineEdit()
        self.le_snmp_location.setPlaceholderText("예: Seoul Datacenter")

        self.le_snmp_contact = QLineEdit()
        self.le_snmp_contact.setPlaceholderText("예: admin@company.com")

        snmp_form.addRow("Location:", self.le_snmp_location)
        snmp_form.addRow("Contact:", self.le_snmp_contact)
        snmp_layout.addLayout(snmp_form)

        # SNMPv2c Communities
        group_snmp_v2 = QGroupBox("SNMPv2c Communities")
        snmp_v2_layout = QVBoxLayout()

        self.snmp_community_table = QTableWidget(0, 3)
        self.snmp_community_table.setHorizontalHeaderLabels(
            ["Community String", "Permission (RO/RW)", "ACL (Optional)"])
        self.snmp_community_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        snmp_v2_button_layout = QHBoxLayout()
        self.btn_add_snmp = QPushButton("v2c Community 추가")
        self.btn_remove_snmp = QPushButton("v2c Community 삭제")
        snmp_v2_button_layout.addWidget(self.btn_add_snmp)
        snmp_v2_button_layout.addWidget(self.btn_remove_snmp)

        snmp_v2_layout.addLayout(snmp_v2_button_layout)
        snmp_v2_layout.addWidget(self.snmp_community_table)
        group_snmp_v2.setLayout(snmp_v2_layout)
        snmp_layout.addWidget(group_snmp_v2)

        # SNMPv3 Users
        group_snmp_v3 = QGroupBox("SNMPv3 Users")
        snmp_v3_layout = QVBoxLayout()

        self.snmp_v3_user_table = QTableWidget(0, 6)
        self.snmp_v3_user_table.setHorizontalHeaderLabels([
            "Username", "Group", "Auth (md5/sha)", "Auth Pass", "Priv (des/aes)", "Priv Pass"
        ])
        self.snmp_v3_user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        snmp_v3_button_layout = QHBoxLayout()
        self.btn_add_snmp_v3 = QPushButton("v3 User 추가")
        self.btn_remove_snmp_v3 = QPushButton("v3 User 삭제")
        snmp_v3_button_layout.addWidget(self.btn_add_snmp_v3)
        snmp_v3_button_layout.addWidget(self.btn_remove_snmp_v3)

        snmp_v3_layout.addLayout(snmp_v3_button_layout)
        snmp_v3_layout.addWidget(self.snmp_v3_user_table)
        group_snmp_v3.setLayout(snmp_v3_layout)
        snmp_layout.addWidget(group_snmp_v3)

        group_snmp.setLayout(snmp_layout)
        layout.addWidget(group_snmp)

        # Security Hardening
        group_hardening = QGroupBox("Security Hardening")
        form_hardening = QFormLayout()

        self.cb_no_ip_http = QCheckBox("no ip http server & secure-server")
        self.cb_no_ip_http.setChecked(True)

        self.cb_no_cdp = QCheckBox("no cdp run / no feature cdp")

        self.cb_lldp = QCheckBox("lldp run / feature lldp")
        self.cb_lldp.setChecked(True)

        self.cb_ip_domain_lookup = QCheckBox("no ip domain-lookup")
        self.cb_ip_domain_lookup.setChecked(True)

        self.cb_service_password_encryption = QCheckBox("service password-encryption")
        self.cb_service_password_encryption.setChecked(True)

        self.cb_boot_network = QCheckBox("no boot network")
        self.cb_boot_network.setChecked(True)

        form_hardening.addRow(self.cb_no_ip_http)
        form_hardening.addRow(self.cb_no_cdp)
        form_hardening.addRow(self.cb_lldp)
        form_hardening.addRow(self.cb_ip_domain_lookup)
        form_hardening.addRow(self.cb_service_password_encryption)
        form_hardening.addRow(self.cb_boot_network)
        group_hardening.setLayout(form_hardening)
        layout.addWidget(group_hardening)

        # TCP Adjustments
        group_tcp = QGroupBox("TCP Adjustments")
        form_tcp = QFormLayout()

        self.cb_tcp_small_servers = QCheckBox("no service tcp-small-servers")
        self.cb_tcp_small_servers.setChecked(True)

        self.cb_udp_small_servers = QCheckBox("no service udp-small-servers")
        self.cb_udp_small_servers.setChecked(True)

        self.cb_finger_service = QCheckBox("no service finger")
        self.cb_finger_service.setChecked(True)

        form_tcp.addRow(self.cb_tcp_small_servers)
        form_tcp.addRow(self.cb_udp_small_servers)
        form_tcp.addRow(self.cb_finger_service)
        group_tcp.setLayout(form_tcp)
        layout.addWidget(group_tcp)

        layout.addStretch()

        # 시그널 연결
        self._connect_signals()

    def _connect_signals(self):
        """시그널 연결"""
        self.cb_con_auth_aaa.toggled.connect(self.le_con_auth_method.setEnabled)