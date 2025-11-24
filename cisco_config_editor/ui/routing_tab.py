# cisco_config_manager/ui/tabs/routing_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QTableWidget, QPushButton, QHeaderView, QCheckBox,
    QTabWidget, QHBoxLayout, QLabel, QPlainTextEdit, QComboBox
)


class RoutingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        routing_tabs = QTabWidget()
        layout.addWidget(routing_tabs)

        # --- Static Routing Tab ---
        static_tab = QWidget()
        static_layout = QVBoxLayout(static_tab)

        self.static_route_table = QTableWidget(0, 4)
        self.static_route_table.setHorizontalHeaderLabels(
            ["Destination Prefix (예: 1.1.1.0/24)", "Next-Hop IP / Interface", "Metric", "VRF"]
        )
        self.static_route_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        static_btn_layout = QHBoxLayout()
        self.btn_add_static_route = QPushButton("정적 경로 추가")
        self.btn_remove_static_route = QPushButton("정적 경로 삭제")
        static_btn_layout.addWidget(self.btn_add_static_route)
        static_btn_layout.addWidget(self.btn_remove_static_route)

        static_layout.addLayout(static_btn_layout)
        static_layout.addWidget(self.static_route_table)
        routing_tabs.addTab(static_tab, "Static")

        # --- OSPF Tab ---
        ospf_tab = QWidget()
        ospf_layout = QVBoxLayout(ospf_tab)

        group_ospf_global = QGroupBox("OSPF Global Settings")
        form_ospf_global = QFormLayout()
        self.cb_ospf_enabled = QCheckBox("Enable OSPF")
        self.le_ospf_process_id = QLineEdit("1")
        self.le_ospf_router_id = QLineEdit()
        self.le_ospf_router_id.setPlaceholderText("예: 1.1.1.1")

        form_ospf_global.addRow(self.cb_ospf_enabled)
        form_ospf_global.addRow("Process ID:", self.le_ospf_process_id)
        form_ospf_global.addRow("Router ID:", self.le_ospf_router_id)
        group_ospf_global.setLayout(form_ospf_global)
        ospf_layout.addWidget(group_ospf_global)

        group_ospf_networks = QGroupBox("Networks to Advertise")
        layout_ospf_networks = QVBoxLayout(group_ospf_networks)

        self.ospf_network_table = QTableWidget(0, 3)
        self.ospf_network_table.setHorizontalHeaderLabels(["Network Address", "Wildcard Mask", "Area"])
        self.ospf_network_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        ospf_net_btn_layout = QHBoxLayout()
        self.btn_add_ospf_net = QPushButton("네트워크 추가")
        self.btn_remove_ospf_net = QPushButton("네트워크 삭제")
        ospf_net_btn_layout.addWidget(self.btn_add_ospf_net)
        ospf_net_btn_layout.addWidget(self.btn_remove_ospf_net)

        layout_ospf_networks.addLayout(ospf_net_btn_layout)
        layout_ospf_networks.addWidget(self.ospf_network_table)
        ospf_layout.addWidget(group_ospf_networks)

        routing_tabs.addTab(ospf_tab, "OSPF")

        # --- EIGRP Tab ---
        eigrp_tab = QWidget()
        eigrp_layout = QVBoxLayout(eigrp_tab)

        group_eigrp_global = QGroupBox("EIGRP Global Settings")
        form_eigrp_global = QFormLayout()
        self.cb_eigrp_enabled = QCheckBox("Enable EIGRP")
        self.le_eigrp_as_number = QLineEdit("100")
        self.le_eigrp_router_id = QLineEdit()
        self.le_eigrp_router_id.setPlaceholderText("예: 1.1.1.1")

        form_eigrp_global.addRow(self.cb_eigrp_enabled)
        form_eigrp_global.addRow("AS Number:", self.le_eigrp_as_number)
        form_eigrp_global.addRow("Router ID:", self.le_eigrp_router_id)
        group_eigrp_global.setLayout(form_eigrp_global)
        eigrp_layout.addWidget(group_eigrp_global)

        group_eigrp_networks = QGroupBox("Networks to Advertise")
        layout_eigrp_networks = QVBoxLayout(group_eigrp_networks)

        self.eigrp_network_table = QTableWidget(0, 2)
        self.eigrp_network_table.setHorizontalHeaderLabels(["Network Address", "Wildcard Mask (Optional)"])
        self.eigrp_network_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        eigrp_net_btn_layout = QHBoxLayout()
        self.btn_add_eigrp_net = QPushButton("네트워크 추가")
        self.btn_remove_eigrp_net = QPushButton("네트워크 삭제")
        eigrp_net_btn_layout.addWidget(self.btn_add_eigrp_net)
        eigrp_net_btn_layout.addWidget(self.btn_remove_eigrp_net)

        layout_eigrp_networks.addLayout(eigrp_net_btn_layout)
        layout_eigrp_networks.addWidget(self.eigrp_network_table)
        eigrp_layout.addWidget(group_eigrp_networks)

        routing_tabs.addTab(eigrp_tab, "EIGRP")

        # --- BGP Tab ---
        bgp_tab = QWidget()
        bgp_layout = QVBoxLayout(bgp_tab)

        group_bgp_global = QGroupBox("BGP Global Settings")
        form_bgp_global = QFormLayout()
        self.cb_bgp_enabled = QCheckBox("Enable BGP")
        self.le_bgp_as_number = QLineEdit("65001")
        self.le_bgp_router_id = QLineEdit()
        self.le_bgp_router_id.setPlaceholderText("예: 1.1.1.1")

        form_bgp_global.addRow(self.cb_bgp_enabled)
        form_bgp_global.addRow("Local AS Number:", self.le_bgp_as_number)
        form_bgp_global.addRow("Router ID:", self.le_bgp_router_id)
        group_bgp_global.setLayout(form_bgp_global)
        bgp_layout.addWidget(group_bgp_global)

        group_bgp_neighbors = QGroupBox("BGP Neighbors")
        layout_bgp_neighbors = QVBoxLayout(group_bgp_neighbors)

        self.bgp_neighbor_table = QTableWidget(0, 6)
        self.bgp_neighbor_table.setHorizontalHeaderLabels(
            ["Neighbor IP", "Remote AS", "Description", "Update Source", "Route-Map IN", "Route-Map OUT"]
        )
        self.bgp_neighbor_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        bgp_neighbor_btn_layout = QHBoxLayout()
        self.btn_add_bgp_neighbor = QPushButton("Neighbor 추가")
        self.btn_remove_bgp_neighbor = QPushButton("Neighbor 삭제")
        bgp_neighbor_btn_layout.addWidget(self.btn_add_bgp_neighbor)
        bgp_neighbor_btn_layout.addWidget(self.btn_remove_bgp_neighbor)

        layout_bgp_neighbors.addLayout(bgp_neighbor_btn_layout)
        layout_bgp_neighbors.addWidget(self.bgp_neighbor_table)
        bgp_layout.addWidget(group_bgp_neighbors)

        group_bgp_networks = QGroupBox("Networks to Advertise")
        layout_bgp_networks = QVBoxLayout(group_bgp_networks)
        layout_bgp_networks.addWidget(QLabel("광고할 네트워크 Prefix 목록 (한 줄에 하나씩)"))
        self.te_bgp_networks = QPlainTextEdit()
        self.te_bgp_networks.setPlaceholderText("예:\n192.168.1.0/24\n192.168.2.0/24\n10.0.0.0/8")
        layout_bgp_networks.addWidget(self.te_bgp_networks)
        bgp_layout.addWidget(group_bgp_networks)

        routing_tabs.addTab(bgp_tab, "BGP")

        # --- RIP Tab ---
        rip_tab = QWidget()
        rip_layout = QVBoxLayout(rip_tab)

        group_rip_global = QGroupBox("RIP Global Settings")
        form_rip_global = QFormLayout()
        self.cb_rip_enabled = QCheckBox("Enable RIP")
        self.le_rip_version = QLineEdit("2")

        form_rip_global.addRow(self.cb_rip_enabled)
        form_rip_global.addRow("RIP Version:", self.le_rip_version)
        group_rip_global.setLayout(form_rip_global)
        rip_layout.addWidget(group_rip_global)

        group_rip_networks = QGroupBox("Networks to Advertise")
        layout_rip_networks = QVBoxLayout(group_rip_networks)

        self.rip_network_table = QTableWidget(0, 1)
        self.rip_network_table.setHorizontalHeaderLabels(["Network Address"])
        self.rip_network_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        rip_net_btn_layout = QHBoxLayout()
        self.btn_add_rip_net = QPushButton("네트워크 추가")
        self.btn_remove_rip_net = QPushButton("네트워크 삭제")
        rip_net_btn_layout.addWidget(self.btn_add_rip_net)
        rip_net_btn_layout.addWidget(self.btn_remove_rip_net)

        layout_rip_networks.addLayout(rip_net_btn_layout)
        layout_rip_networks.addWidget(self.rip_network_table)
        rip_layout.addWidget(group_rip_networks)

        routing_tabs.addTab(rip_tab, "RIP")

        # --- Route Redistribution Tab ---
        redistribution_tab = QWidget()
        redistribution_layout = QVBoxLayout(redistribution_tab)

        group_redistribution = QGroupBox("Route Redistribution")
        form_redistribution = QFormLayout()

        self.cb_redistribute_connected = QCheckBox("Redistribute Connected")
        self.cb_redistribute_static = QCheckBox("Redistribute Static")
        self.cb_redistribute_ospf = QCheckBox("Redistribute OSPF")
        self.cb_redistribute_eigrp = QCheckBox("Redistribute EIGRP")
        self.cb_redistribute_bgp = QCheckBox("Redistribute BGP")
        self.cb_redistribute_rip = QCheckBox("Redistribute RIP")

        form_redistribution.addRow(self.cb_redistribute_connected)
        form_redistribution.addRow(self.cb_redistribute_static)
        form_redistribution.addRow(self.cb_redistribute_ospf)
        form_redistribution.addRow(self.cb_redistribute_eigrp)
        form_redistribution.addRow(self.cb_redistribute_bgp)
        form_redistribution.addRow(self.cb_redistribute_rip)

        group_redistribution.setLayout(form_redistribution)
        redistribution_layout.addWidget(group_redistribution)

        routing_tabs.addTab(redistribution_tab, "Route Redistribution")