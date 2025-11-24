# cisco_config_manager/ui/tabs/switching_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QTableWidget, QPushButton, QHeaderView, QCheckBox,
    QComboBox, QScrollArea, QHBoxLayout, QLabel
)


class SwitchingTab(QWidget):
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

        # Spanning Tree Protocol (STP)
        group_stp = QGroupBox("Spanning Tree Protocol (STP)")
        form_stp = QFormLayout()

        self.combo_stp_mode = QComboBox()
        self.combo_stp_mode.addItems(["rapid-pvst", "pvst", "mst"])

        self.le_stp_priority = QLineEdit()
        self.le_stp_priority.setPlaceholderText("예: 4096 (VLAN 1 기준)")

        self.cb_stp_portfast_default = QCheckBox("spanning-tree portfast default")
        self.cb_stp_bpduguard_default = QCheckBox("spanning-tree portfast bpduguard default")
        self.cb_stp_bpdufilter_default = QCheckBox("spanning-tree portfast bpdufilter default")
        self.cb_stp_loopguard_default = QCheckBox("spanning-tree loopguard default")

        form_stp.addRow("STP Mode:", self.combo_stp_mode)
        form_stp.addRow("Root Bridge Priority (VLAN 1):", self.le_stp_priority)
        form_stp.addRow(self.cb_stp_portfast_default)
        form_stp.addRow(self.cb_stp_bpduguard_default)
        form_stp.addRow(self.cb_stp_bpdufilter_default)
        form_stp.addRow(self.cb_stp_loopguard_default)
        group_stp.setLayout(form_stp)
        layout.addWidget(group_stp)

        # MST Configuration
        self.group_mst_config = QGroupBox("MST Configuration")
        mst_layout = QVBoxLayout()

        mst_form = QFormLayout()
        self.le_mst_name = QLineEdit()
        self.le_mst_name.setPlaceholderText("예: Region1")

        self.le_mst_revision = QLineEdit("0")

        mst_form.addRow("Configuration Name:", self.le_mst_name)
        mst_form.addRow("Revision Number:", self.le_mst_revision)
        mst_layout.addLayout(mst_form)

        self.mst_instance_table = QTableWidget(0, 2)
        self.mst_instance_table.setHorizontalHeaderLabels(["Instance ID", "VLANs (예: 10,20,30-40)"])
        self.mst_instance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        mst_btn_layout = QHBoxLayout()
        self.btn_add_mst_instance = QPushButton("Instance 추가")
        self.btn_remove_mst_instance = QPushButton("Instance 삭제")
        mst_btn_layout.addWidget(self.btn_add_mst_instance)
        mst_btn_layout.addWidget(self.btn_remove_mst_instance)

        mst_layout.addLayout(mst_btn_layout)
        mst_layout.addWidget(self.mst_instance_table)
        self.group_mst_config.setLayout(mst_layout)
        self.group_mst_config.setVisible(False)
        layout.addWidget(self.group_mst_config)

        # VLAN Trunking Protocol (VTP)
        group_vtp = QGroupBox("VLAN Trunking Protocol (VTP)")
        form_vtp = QFormLayout()

        self.cb_vtp_enabled = QCheckBox("Enable VTP")
        self.combo_vtp_mode = QComboBox()
        self.combo_vtp_mode.addItems(["transparent", "server", "client", "off"])

        self.le_vtp_domain = QLineEdit()
        self.le_vtp_domain.setPlaceholderText("예: COMPANY")

        self.le_vtp_password = QLineEdit()
        self.le_vtp_password.setEchoMode(QLineEdit.Password)
        self.le_vtp_password.setPlaceholderText("VTP 도메인 비밀번호")

        self.combo_vtp_version = QComboBox()
        self.combo_vtp_version.addItems(["2", "1", "3"])

        form_vtp.addRow(self.cb_vtp_enabled)
        form_vtp.addRow("Mode:", self.combo_vtp_mode)
        form_vtp.addRow("Domain:", self.le_vtp_domain)
        form_vtp.addRow("Password:", self.le_vtp_password)
        form_vtp.addRow("Version:", self.combo_vtp_version)
        group_vtp.setLayout(form_vtp)
        layout.addWidget(group_vtp)

        # L2 Security
        group_l2_security = QGroupBox("L2 Security")
        form_l2_sec = QFormLayout()

        self.cb_dhcp_snooping_enabled = QCheckBox("Enable DHCP Snooping (Global)")
        self.le_dhcp_snooping_vlans = QLineEdit()
        self.le_dhcp_snooping_vlans.setPlaceholderText("예: 10,20,30-40")

        self.le_dai_vlans = QLineEdit()
        self.le_dai_vlans.setPlaceholderText("예: 10,20,30-40")

        self.cb_ip_source_guard = QCheckBox("IP Source Guard 활성화")
        self.le_ipsg_vlans = QLineEdit()
        self.le_ipsg_vlans.setPlaceholderText("예: 10,20,30-40")

        form_l2_sec.addRow(self.cb_dhcp_snooping_enabled)
        form_l2_sec.addRow("DHCP Snooping VLANs:", self.le_dhcp_snooping_vlans)
        form_l2_sec.addRow("Dynamic ARP Inspection (DAI) VLANs:", self.le_dai_vlans)
        form_l2_sec.addRow(self.cb_ip_source_guard)
        form_l2_sec.addRow("IP Source Guard VLANs:", self.le_ipsg_vlans)
        group_l2_security.setLayout(form_l2_sec)
        layout.addWidget(group_l2_security)

        # MAC Address Table
        group_mac = QGroupBox("MAC Address Table")
        form_mac = QFormLayout()

        self.le_mac_aging_time = QLineEdit("300")
        self.cb_mac_notification = QCheckBox("MAC Notification 활성화")
        self.le_mac_limit = QLineEdit()
        self.le_mac_limit.setPlaceholderText("예: 1000")

        form_mac.addRow("MAC Aging Time (초):", self.le_mac_aging_time)
        form_mac.addRow(self.cb_mac_notification)
        form_mac.addRow("MAC Address Limit:", self.le_mac_limit)
        group_mac.setLayout(form_mac)
        layout.addWidget(group_mac)

        layout.addStretch()

        # 시그널 연결
        self._connect_signals()

    def _connect_signals(self):
        """시그널 연결"""
        self.combo_stp_mode.currentTextChanged.connect(self._on_stp_mode_changed)

    def _on_stp_mode_changed(self, mode):
        """STP 모드 변경 핸들러"""
        self.group_mst_config.setVisible(mode == "mst")