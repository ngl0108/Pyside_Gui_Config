# ansible_config_editor/ui/tabs/vlan_tab.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
                               QTableWidget, QPushButton, QHeaderView, QCheckBox,
                               QLabel, QScrollArea, QHBoxLayout, QAbstractItemView)


class VlanTab(QWidget):
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

        self.cb_ip_routing = QCheckBox("Enable Inter-VLAN Routing (ip routing)")
        layout.addWidget(self.cb_ip_routing)

        # VLAN Management
        group_vlan = QGroupBox("1. VLAN 생성 및 관리")
        vlan_layout = QVBoxLayout()
        self.vlan_table = QTableWidget(0, 3)
        self.vlan_table.setHorizontalHeaderLabels(["VLAN ID", "VLAN Name", "Description"])
        self.vlan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.vlan_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vlan_table.setSelectionMode(QAbstractItemView.SingleSelection)
        vlan_button_layout = QHBoxLayout()
        self.btn_add_vlan = QPushButton("VLAN 추가")
        self.btn_remove_vlan = QPushButton("VLAN 삭제")
        vlan_button_layout.addWidget(self.btn_add_vlan)
        vlan_button_layout.addWidget(self.btn_remove_vlan)
        vlan_layout.addLayout(vlan_button_layout)
        vlan_layout.addWidget(self.vlan_table)
        group_vlan.setLayout(vlan_layout)
        layout.addWidget(group_vlan)

        # SVI (Vlan Interface) Settings
        self.group_svi = QGroupBox("2. SVI (Vlan Interface) 설정")
        svi_layout = QVBoxLayout()
        self.svi_label = QLabel("상단 테이블에서 설정을 원하는 VLAN을 선택하세요.")
        svi_layout.addWidget(self.svi_label)

        svi_form_layout = QFormLayout()
        self.cb_svi_enabled = QCheckBox("SVI 인터페이스 생성")
        self.le_svi_ip = QLineEdit()
        svi_form_layout.addRow(self.cb_svi_enabled)
        svi_form_layout.addRow("IP 주소/Prefix:", self.le_svi_ip)
        svi_layout.addLayout(svi_form_layout)

        # FHRP (VRRP / HSRP) Settings
        self.group_fhrp = QGroupBox("VRRP / HSRP 설정")
        fhrp_form = QFormLayout()
        self.cb_fhrp_enabled = QCheckBox("VRRP/HSRP 활성화")
        self.le_fhrp_group = QLineEdit()
        self.le_fhrp_vip = QLineEdit()
        self.le_fhrp_priority = QLineEdit()
        self.cb_fhrp_preempt = QCheckBox("Preempt 활성화")
        fhrp_form.addRow(self.cb_fhrp_enabled)
        fhrp_form.addRow("Group ID:", self.le_fhrp_group)
        fhrp_form.addRow("Virtual IP:", self.le_fhrp_vip)
        fhrp_form.addRow("Priority:", self.le_fhrp_priority)
        fhrp_form.addRow(self.cb_fhrp_preempt)
        self.group_fhrp.setLayout(fhrp_form)
        svi_layout.addWidget(self.group_fhrp)

        # DHCP Helper Settings
        self.group_dhcp_helper = QGroupBox("DHCP Helper")
        dhcp_helper_layout = QVBoxLayout()
        self.dhcp_helper_table = QTableWidget(0, 1)
        self.dhcp_helper_table.setHorizontalHeaderLabels(["Helper-Address IP"])
        self.dhcp_helper_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        dhcp_helper_buttons = QHBoxLayout()
        self.btn_add_helper = QPushButton("Helper 추가")
        self.btn_remove_helper = QPushButton("Helper 삭제")
        dhcp_helper_buttons.addWidget(self.btn_add_helper)
        dhcp_helper_buttons.addWidget(self.btn_remove_helper)
        dhcp_helper_layout.addLayout(dhcp_helper_buttons)
        dhcp_helper_layout.addWidget(self.dhcp_helper_table)
        self.group_dhcp_helper.setLayout(dhcp_helper_layout)
        svi_layout.addWidget(self.group_dhcp_helper)

        self.group_svi.setLayout(svi_layout)
        self.group_svi.setEnabled(False)
        layout.addWidget(self.group_svi)

        layout.addStretch()