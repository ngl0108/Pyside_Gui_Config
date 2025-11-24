# cisco_config_manager/ui/tabs/ha_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QCheckBox, QScrollArea, QComboBox, QLabel
)


class HaTab(QWidget):
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

        # StackWise Virtual (IOS-XE only)
        self.group_svl = QGroupBox("StackWise Virtual (IOS-XE only)")
        form_svl = QFormLayout()
        self.cb_svl_enabled = QCheckBox("Enable StackWise Virtual")
        self.le_svl_domain = QLineEdit()
        self.le_svl_domain.setPlaceholderText("예: 100")

        self.le_svl_priority = QLineEdit()
        self.le_svl_priority.setPlaceholderText("예: 10 (1-15)")

        self.le_svl_member_ports = QLineEdit()
        self.le_svl_member_ports.setPlaceholderText("예: TenGigabitEthernet1/0/1-2")

        form_svl.addRow(self.cb_svl_enabled)
        form_svl.addRow("Domain ID:", self.le_svl_domain)
        form_svl.addRow("Priority:", self.le_svl_priority)
        form_svl.addRow("Member Ports:", self.le_svl_member_ports)
        self.group_svl.setLayout(form_svl)
        layout.addWidget(self.group_svl)

        # vPC - Virtual Port-Channel (NX-OS only)
        self.group_vpc = QGroupBox("vPC - Virtual Port-Channel (NX-OS only)")
        form_vpc = QFormLayout()
        self.cb_vpc_enabled = QCheckBox("Enable vPC")
        self.le_vpc_domain = QLineEdit()
        self.le_vpc_domain.setPlaceholderText("예: 100")

        self.le_vpc_peer_keepalive = QLineEdit()
        self.le_vpc_peer_keepalive.setPlaceholderText("예: 192.168.1.1 source 192.168.1.2")

        self.le_vpc_peer_link = QLineEdit()
        self.le_vpc_peer_link.setPlaceholderText("예: port-channel100")

        self.le_vpc_peer_gateway = QCheckBox("vPC peer-gateway")

        form_vpc.addRow(self.cb_vpc_enabled)
        form_vpc.addRow("Domain ID:", self.le_vpc_domain)
        form_vpc.addRow("Peer-Keepalive:", self.le_vpc_peer_keepalive)
        form_vpc.addRow("Peer-Link:", self.le_vpc_peer_link)
        form_vpc.addRow(self.le_vpc_peer_gateway)
        self.group_vpc.setLayout(form_vpc)
        layout.addWidget(self.group_vpc)

        # HSRP/VRRP Settings
        group_fhrp = QGroupBox("HSRP/VRRP Settings")
        form_fhrp = QFormLayout()

        self.cb_fhrp_enabled = QCheckBox("Enable HSRP/VRRP")
        self.le_fhrp_group = QLineEdit()
        self.le_fhrp_group.setPlaceholderText("예: 10")

        self.le_fhrp_vip = QLineEdit()
        self.le_fhrp_vip.setPlaceholderText("예: 192.168.1.254")

        self.le_fhrp_priority = QLineEdit()
        self.le_fhrp_priority.setPlaceholderText("예: 110")

        self.cb_fhrp_preempt = QCheckBox("Preempt")
        self.le_fhrp_track = QLineEdit()
        self.le_fhrp_track.setPlaceholderText("예: 1 decrement 20")

        form_fhrp.addRow(self.cb_fhrp_enabled)
        form_fhrp.addRow("Group ID:", self.le_fhrp_group)
        form_fhrp.addRow("Virtual IP:", self.le_fhrp_vip)
        form_fhrp.addRow("Priority:", self.le_fhrp_priority)
        form_fhrp.addRow(self.cb_fhrp_preempt)
        form_fhrp.addRow("Track:", self.le_fhrp_track)
        group_fhrp.setLayout(form_fhrp)
        layout.addWidget(group_fhrp)

        # Gateway Load Balancing Protocol (GLBP)
        group_glbp = QGroupBox("Gateway Load Balancing Protocol (GLBP)")
        form_glbp = QFormLayout()

        self.cb_glbp_enabled = QCheckBox("Enable GLBP")
        self.le_glbp_group = QLineEdit()
        self.le_glbp_group.setPlaceholderText("예: 10")

        self.le_glbp_vip = QLineEdit()
        self.le_glbp_vip.setPlaceholderText("예: 192.168.1.254")

        self.le_glbp_priority = QLineEdit()
        self.le_glbp_priority.setPlaceholderText("예: 110")

        self.combo_glbp_load_balance = QComboBox()
        self.combo_glbp_load_balance.addItems(["round-robin", "weighted", "host-dependent"])

        form_glbp.addRow(self.cb_glbp_enabled)
        form_glbp.addRow("Group ID:", self.le_glbp_group)
        form_glbp.addRow("Virtual IP:", self.le_glbp_vip)
        form_glbp.addRow("Priority:", self.le_glbp_priority)
        form_glbp.addRow("Load Balancing:", self.combo_glbp_load_balance)
        group_glbp.setLayout(form_glbp)
        layout.addWidget(group_glbp)

        # Interface Tracking
        group_tracking = QGroupBox("Interface Tracking")
        tracking_layout = QVBoxLayout()

        tracking_info = QLabel("인터페이스 트래킹을 통해 HA 그룹의 우선순위를 동적으로 조정합니다.")
        tracking_info.setWordWrap(True)
        tracking_layout.addWidget(tracking_info)

        self.le_track_interface = QLineEdit()
        self.le_track_interface.setPlaceholderText("예: GigabitEthernet0/1 line-protocol")

        self.le_track_decrement = QLineEdit()
        self.le_track_decrement.setPlaceholderText("예: 20")

        tracking_form = QFormLayout()
        tracking_form.addRow("Track Interface:", self.le_track_interface)
        tracking_form.addRow("Decrement Value:", self.le_track_decrement)
        tracking_layout.addLayout(tracking_form)

        group_tracking.setLayout(tracking_layout)
        layout.addWidget(group_tracking)

        layout.addStretch()