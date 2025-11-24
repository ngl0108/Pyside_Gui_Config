# cisco_config_manager/ui/tabs/interface_tab.py
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QPushButton,
    QScrollArea, QGroupBox, QFormLayout, QLabel, QCheckBox,
    QLineEdit, QComboBox, QStackedWidget, QAbstractItemView
)
from PySide6.QtCore import Qt


class InterfaceTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)

        # Left Panel (Interface List)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(QLabel("설정할 인터페이스 목록 (Ctrl, Shift로 다중 선택 가능)"))
        self.interface_list = QListWidget()
        self.interface_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        left_layout.addWidget(self.interface_list)

        warning_label = QLabel("주의: 물리적 구성이 동일한\n장비 그룹별로 작업하십시오.")
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        left_layout.addWidget(warning_label)

        btn_layout = QHBoxLayout()
        self.btn_add_interface = QPushButton("인터페이스 추가")
        self.btn_add_port_channel = QPushButton("Port-Channel 추가")
        self.btn_remove_interface = QPushButton("목록에서 삭제")
        btn_layout.addWidget(self.btn_add_interface)
        btn_layout.addWidget(self.btn_add_port_channel)
        left_layout.addLayout(btn_layout)
        left_layout.addWidget(self.btn_remove_interface)

        main_layout.addWidget(left_widget, 2)

        # Right Panel (Configuration Area)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        right_widget = QWidget()
        config_layout = QVBoxLayout(right_widget)
        scroll_area.setWidget(right_widget)
        main_layout.addWidget(scroll_area, 5)

        self.config_area_widget = QWidget()
        config_layout.addWidget(self.config_area_widget)
        form_layout = QVBoxLayout(self.config_area_widget)

        # Basic Settings
        group_basic = QGroupBox("기본 설정")
        form_basic = QFormLayout()
        self.if_label = QLabel("왼쪽 목록에서 인터페이스를 선택하세요.")
        self.cb_if_shutdown = QCheckBox("Shutdown")
        self.le_if_description = QLineEdit()
        self.le_if_description.setPlaceholderText("인터페이스 설명")

        self.combo_if_type = QComboBox()
        self.combo_if_type.addItems(["Copper", "Fiber", "SFP", "QSFP"])

        self.combo_if_mode = QComboBox()
        self.combo_if_mode.addItems(["L2 Access", "L2 Trunk", "L3 Routed", "Port-Channel Member"])

        form_basic.addRow(self.if_label)
        form_basic.addRow("상태:", self.cb_if_shutdown)
        form_basic.addRow("설명:", self.le_if_description)
        form_basic.addRow("포트 유형:", self.combo_if_type)
        form_basic.addRow("인터페이스 모드:", self.combo_if_mode)
        group_basic.setLayout(form_basic)
        form_layout.addWidget(group_basic)

        # Mode Specific Settings (Stacked Widget)
        self.mode_stack = QStackedWidget()
        form_layout.addWidget(self.mode_stack)

        # Stack 0: L2 Access
        stack_access = QWidget()
        form_access = QFormLayout(stack_access)
        self.le_access_vlan = QLineEdit()
        self.le_access_vlan.setPlaceholderText("예: 10")
        self.le_voice_vlan = QLineEdit()
        self.le_voice_vlan.setPlaceholderText("예: 20 (선택사항)")
        form_access.addRow("Access VLAN:", self.le_access_vlan)
        form_access.addRow("Voice VLAN:", self.le_voice_vlan)
        self.mode_stack.addWidget(stack_access)

        # Stack 1: L2 Trunk
        stack_trunk = QWidget()
        form_trunk = QFormLayout(stack_trunk)
        self.le_trunk_native = QLineEdit()
        self.le_trunk_native.setPlaceholderText("예: 1")
        self.le_trunk_allowed = QLineEdit()
        self.le_trunk_allowed.setPlaceholderText("예: 10,20,30-40 또는 all")
        form_trunk.addRow("Native VLAN:", self.le_trunk_native)
        form_trunk.addRow("Allowed VLANs:", self.le_trunk_allowed)
        self.mode_stack.addWidget(stack_trunk)

        # Stack 2: L3 Routed
        stack_routed = QWidget()
        form_routed = QFormLayout(stack_routed)
        self.le_routed_ip = QLineEdit()
        self.le_routed_ip.setPlaceholderText("예: 192.168.1.1 255.255.255.0")

        self.combo_routed_acl_in = QComboBox()
        self.combo_routed_acl_in.addItems(["", "ACL-1", "ACL-2", "ACL-3"])
        self.combo_routed_acl_out = QComboBox()
        self.combo_routed_acl_out.addItems(["", "ACL-1", "ACL-2", "ACL-3"])

        form_routed.addRow("IP 주소/Prefix:", self.le_routed_ip)
        form_routed.addRow("IP Access-Group IN:", self.combo_routed_acl_in)
        form_routed.addRow("IP Access-Group OUT:", self.combo_routed_acl_out)
        self.mode_stack.addWidget(stack_routed)

        # Stack 3: Port-Channel Member
        stack_pc_member = QWidget()
        form_pc_member = QFormLayout(stack_pc_member)
        self.le_channel_group_id = QLineEdit()
        self.le_channel_group_id.setPlaceholderText("예: 10")
        self.combo_channel_group_mode = QComboBox()
        self.combo_channel_group_mode.addItems(["active", "passive", "on"])
        form_pc_member.addRow("Channel-Group ID:", self.le_channel_group_id)
        form_pc_member.addRow("LACP 모드:", self.combo_channel_group_mode)
        self.mode_stack.addWidget(stack_pc_member)

        # Other Feature Groups
        self.group_if_stp = QGroupBox("Spanning Tree")
        form_stp = QFormLayout(self.group_if_stp)
        self.cb_stp_portfast = QCheckBox("Portfast 활성화 (Edge port)")
        self.cb_stp_bpduguard = QCheckBox("BPDU Guard 활성화")
        self.cb_stp_bpdufilter = QCheckBox("BPDU Filter 활성화")
        form_stp.addRow(self.cb_stp_portfast)
        form_stp.addRow(self.cb_stp_bpduguard)
        form_stp.addRow(self.cb_stp_bpdufilter)
        form_layout.addWidget(self.group_if_stp)

        self.group_if_port_security = QGroupBox("Port Security")
        form_ps = QFormLayout(self.group_if_port_security)
        self.cb_ps_enabled = QCheckBox("Port Security 활성화")
        self.le_ps_max_mac = QLineEdit("1")
        self.combo_ps_violation = QComboBox()
        self.combo_ps_violation.addItems(["shutdown", "restrict", "protect"])
        self.le_ps_aging_time = QLineEdit()
        self.le_ps_aging_time.setPlaceholderText("예: 5 (분)")
        form_ps.addRow(self.cb_ps_enabled)
        form_ps.addRow("최대 MAC 주소 수:", self.le_ps_max_mac)
        form_ps.addRow("Violation 모드:", self.combo_ps_violation)
        form_ps.addRow("Aging Time (분):", self.le_ps_aging_time)
        form_layout.addWidget(self.group_if_port_security)

        self.group_if_storm_control = QGroupBox("Storm Control")
        form_sc = QFormLayout(self.group_if_storm_control)
        self.le_sc_broadcast = QLineEdit()
        self.le_sc_broadcast.setPlaceholderText("예: 10.00")
        self.le_sc_multicast = QLineEdit()
        self.le_sc_multicast.setPlaceholderText("예: 5.00")
        self.le_sc_unicast = QLineEdit()
        self.le_sc_unicast.setPlaceholderText("예: 5.00")
        self.combo_sc_action = QComboBox()
        self.combo_sc_action.addItems(["shutdown", "trap", "block"])
        form_sc.addRow("Broadcast Level (%):", self.le_sc_broadcast)
        form_sc.addRow("Multicast Level (%):", self.le_sc_multicast)
        form_sc.addRow("Unicast Level (%):", self.le_sc_unicast)
        form_sc.addRow("Action:", self.combo_sc_action)
        form_layout.addWidget(self.group_if_storm_control)

        self.group_if_udld = QGroupBox("UDLD")
        form_udld = QFormLayout(self.group_if_udld)
        self.cb_udld_enabled = QCheckBox("UDLD 활성화")
        self.combo_udld_mode = QComboBox()
        self.combo_udld_mode.addItems(["normal", "aggressive"])
        self.combo_udld_mode.setEnabled(False)
        form_udld.addRow(self.cb_udld_enabled)
        form_udld.addRow("모드:", self.combo_udld_mode)
        form_layout.addWidget(self.group_if_udld)

        # Speed and Duplex Settings
        self.group_if_speed = QGroupBox("Speed & Duplex")
        form_speed = QFormLayout(self.group_if_speed)
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["auto", "10", "100", "1000", "10000"])
        self.combo_duplex = QComboBox()
        self.combo_duplex.addItems(["auto", "half", "full"])
        self.le_mtu = QLineEdit()
        self.le_mtu.setPlaceholderText("예: 1500")
        form_speed.addRow("Speed (Mbps):", self.combo_speed)
        form_speed.addRow("Duplex:", self.combo_duplex)
        form_speed.addRow("MTU:", self.le_mtu)
        form_layout.addWidget(self.group_if_speed)

        config_layout.addStretch()
        self.config_area_widget.setVisible(False)

        # 시그널 연결
        self._connect_signals()

    def _connect_signals(self):
        """시그널 연결"""
        self.cb_udld_enabled.toggled.connect(self.combo_udld_mode.setEnabled)
        self.combo_if_mode.currentTextChanged.connect(self._on_mode_changed)

    def _on_mode_changed(self, mode):
        """인터페이스 모드 변경 핸들러"""
        mode_mapping = {
            "L2 Access": 0,
            "L2 Trunk": 1,
            "L3 Routed": 2,
            "Port-Channel Member": 3
        }
        self.mode_stack.setCurrentIndex(mode_mapping.get(mode, 0))

        # L2 전용 기능 활성화/비활성화
        is_l2 = mode in ["L2 Access", "L2 Trunk"]
        self.group_if_stp.setEnabled(is_l2)
        self.group_if_port_security.setEnabled(is_l2)
        self.group_if_storm_control.setEnabled(is_l2)