# ansible_config_editor/ui/tabs/ha_tab.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
                               QCheckBox, QScrollArea)


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
        form_svl.addRow(self.cb_svl_enabled)
        form_svl.addRow("Domain ID:", self.le_svl_domain)
        self.group_svl.setLayout(form_svl)
        layout.addWidget(self.group_svl)

        # vPC - Virtual Port-Channel (NX-OS only)
        self.group_vpc = QGroupBox("vPC - Virtual Port-Channel (NX-OS only)")
        form_vpc = QFormLayout()
        self.cb_vpc_enabled = QCheckBox("Enable vPC")
        self.le_vpc_domain = QLineEdit()
        self.le_vpc_peer_keepalive = QLineEdit()
        form_vpc.addRow(self.cb_vpc_enabled)
        form_vpc.addRow("Domain ID:", self.le_vpc_domain)
        form_vpc.addRow("Peer-Keepalive:", self.le_vpc_peer_keepalive)
        self.group_vpc.setLayout(form_vpc)
        layout.addWidget(self.group_vpc)

        layout.addStretch()