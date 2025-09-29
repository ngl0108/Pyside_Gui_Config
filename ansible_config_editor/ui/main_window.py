# ansible_config_editor/ui/main_window.py
import os
import json
from copy import deepcopy

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QFileDialog, QMessageBox, QTabWidget, QGroupBox, QAbstractItemView,
                               QApplication, QInputDialog, QLabel, QComboBox, QMenuBar, QTableWidgetItem)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ansible_config_editor.core.playbook_manager import ConfigManager
from ansible_config_editor.core.ansible_engine import AnsibleEngine
from .dialogs import CredentialsDialog, AddDevicesDialog, AddInterfacesDialog
from .tabs.global_tab import GlobalTab
from .tabs.interface_tab import InterfaceTab
from .tabs.vlan_tab import VlanTab
from .tabs.switching_tab import SwitchingTab
from .tabs.routing_tab import RoutingTab
from .tabs.ha_tab import HaTab
from .tabs.security_tab import SecurityTab
from .tabs.acl_tab import AclTab


class MainWindow(QMainWindow):
    # --- 초기화 및 UI 생성 메서드 ---
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Standard Network Config Manager")
        self.setGeometry(100, 100, 1800, 1000)

        self.config_manager = ConfigManager()
        self.ansible_engine = AnsibleEngine()
        self.current_config_path = None
        self.current_vlan_item = None

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._update_ui_for_os()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 왼쪽 패널
        device_management_group = QGroupBox("1. 장비 관리")
        device_layout = QVBoxLayout()
        self.combo_os_type = QComboBox()
        self.combo_os_type.addItems(["L2_IOS-XE", "L3_IOS-XE", "L2_NX-OS", "L3_NX-OS"])
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
        self.btn_fetch_info = QPushButton("선택 장비 정보 가져오기")
        self.btn_fetch_info.setToolTip("이 기능은 Linux 환경(예: WSL)에서만 사용 가능합니다.")
        device_layout.addWidget(self.btn_fetch_info)
        device_layout.addWidget(self.device_list)
        device_management_group.setLayout(device_layout)

        # 중앙 패널
        config_group = QGroupBox("2. 구성 편집")
        config_layout = QVBoxLayout()
        self.main_tabs = QTabWidget()

        self.global_tab = GlobalTab()
        self.interface_tab = InterfaceTab()
        self.vlan_tab = VlanTab()
        self.switching_tab = SwitchingTab()
        self.routing_tab = RoutingTab()
        self.ha_tab = HaTab()
        self.security_tab = SecurityTab()
        self.acl_tab = AclTab()

        self.main_tabs.addTab(self.global_tab, "Global")
        self.main_tabs.addTab(self.interface_tab, "Interface")
        self.main_tabs.addTab(self.vlan_tab, "VLAN")
        self.main_tabs.addTab(self.switching_tab, "Switching")
        self.main_tabs.addTab(self.routing_tab, "Routing")
        self.main_tabs.addTab(self.ha_tab, "HA (고가용성)")
        self.main_tabs.addTab(self.security_tab, "Security")
        self.main_tabs.addTab(self.acl_tab, "ACL")
        config_group.setLayout(config_layout)
        config_layout.addWidget(self.main_tabs)

        # 오른쪽 패널
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

    def _setup_menu(self):
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        file_menu = self.menu_bar.addMenu("파일(&F)")
        new_action = QAction("새 구성(&N)", self)
        new_action.triggered.connect(self._new_config_profile)
        open_action = QAction("구성 열기(&O)...", self)
        open_action.triggered.connect(self._load_config_profile)
        save_as_action = QAction("다른 이름으로 구성 저장(&A)...", self)
        save_as_action.triggered.connect(self._save_config_profile)
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_as_action)

    def _connect_signals(self):
        # 장비 관리
        self.btn_add_device.clicked.connect(self.ui_add_device)
        self.btn_remove_device.clicked.connect(self.ui_remove_device)
        self.btn_apply.clicked.connect(self.run_config_task)
        self.btn_fetch_info.clicked.connect(self._fetch_device_info)
        self.combo_os_type.currentTextChanged.connect(self._update_ui_for_os)

        # 인터페이스 탭
        it = self.interface_tab
        it.btn_add_interface.clicked.connect(self.ui_add_interface)
        it.btn_add_port_channel.clicked.connect(self.ui_add_port_channel)
        it.btn_remove_interface.clicked.connect(lambda: it.interface_list.takeItem(it.interface_list.currentRow()))
        it.interface_list.itemSelectionChanged.connect(self._on_interface_selected)
        for widget in [it.cb_if_shutdown, it.cb_stp_portfast, it.cb_stp_bpduguard, it.cb_ps_enabled,
                       it.cb_udld_enabled]:
            widget.toggled.connect(self._save_interface_data)
        for widget in [it.le_if_description, it.le_access_vlan, it.le_voice_vlan, it.le_trunk_native,
                       it.le_trunk_allowed, it.le_routed_ip, it.le_channel_group_id, it.le_ps_max_mac,
                       it.le_sc_broadcast, it.le_sc_multicast, it.le_sc_unicast]:
            widget.editingFinished.connect(self._save_interface_data)
        for widget in [it.combo_channel_group_mode, it.combo_ps_violation, it.combo_sc_action, it.combo_udld_mode]:
            widget.currentTextChanged.connect(self._save_interface_data)
        it.combo_if_type.currentTextChanged.connect(self._update_dynamic_interface_ui)
        it.combo_if_mode.currentTextChanged.connect(self._update_dynamic_interface_ui)

        # VLAN 탭
        vt = self.vlan_tab
        vt.btn_add_vlan.clicked.connect(lambda: self.ui_add_table_row(vt.vlan_table))
        vt.btn_remove_vlan.clicked.connect(lambda: self.ui_remove_table_row(vt.vlan_table))
        vt.vlan_table.itemSelectionChanged.connect(self._on_vlan_selected)
        vt.cb_svi_enabled.toggled.connect(self._save_svi_data)
        vt.le_svi_ip.editingFinished.connect(self._save_svi_data)
        vt.cb_fhrp_enabled.toggled.connect(self._save_svi_data)
        vt.le_fhrp_group.editingFinished.connect(self._save_svi_data)
        vt.le_fhrp_vip.editingFinished.connect(self._save_svi_data)
        vt.le_fhrp_priority.editingFinished.connect(self._save_svi_data)
        vt.cb_fhrp_preempt.toggled.connect(self._save_svi_data)
        vt.btn_add_helper.clicked.connect(lambda: self.ui_add_table_row(vt.dhcp_helper_table))
        vt.btn_remove_helper.clicked.connect(lambda: self.ui_remove_table_row(vt.dhcp_helper_table))
        vt.dhcp_helper_table.itemChanged.connect(self._save_svi_data)

        # Switching 탭
        st = self.switching_tab
        st.combo_stp_mode.currentTextChanged.connect(self._update_mst_ui_visibility)
        st.btn_add_mst_instance.clicked.connect(lambda: self.ui_add_table_row(st.mst_instance_table))
        st.btn_remove_mst_instance.clicked.connect(lambda: self.ui_remove_table_row(st.mst_instance_table))

        # Routing 탭
        rt = self.routing_tab
        rt.btn_add_static_route.clicked.connect(lambda: self.ui_add_table_row(rt.static_route_table))
        rt.btn_remove_static_route.clicked.connect(lambda: self.ui_remove_table_row(rt.static_route_table))
        rt.btn_add_ospf_net.clicked.connect(lambda: self.ui_add_table_row(rt.ospf_network_table))
        rt.btn_remove_ospf_net.clicked.connect(lambda: self.ui_remove_table_row(rt.ospf_network_table))
        rt.btn_add_eigrp_net.clicked.connect(lambda: self.ui_add_table_row(rt.eigrp_network_table))
        rt.btn_remove_eigrp_net.clicked.connect(lambda: self.ui_remove_table_row(rt.eigrp_network_table))
        rt.btn_add_bgp_neighbor.clicked.connect(lambda: self.ui_add_table_row(rt.bgp_neighbor_table))
        rt.btn_remove_bgp_neighbor.clicked.connect(lambda: self.ui_remove_table_row(rt.bgp_neighbor_table))

        # 글로벌 탭
        gt = self.global_tab
        gt.btn_add_dns.clicked.connect(lambda: self.ui_add_table_row(gt.dns_table))
        gt.btn_remove_dns.clicked.connect(lambda: self.ui_remove_table_row(gt.dns_table))
        gt.btn_add_log_host.clicked.connect(lambda: self.ui_add_table_row(gt.logging_table))
        gt.btn_remove_log_host.clicked.connect(lambda: self.ui_remove_table_row(gt.logging_table))
        gt.btn_add_ntp.clicked.connect(lambda: self.ui_add_table_row(gt.ntp_table))
        gt.btn_remove_ntp.clicked.connect(lambda: self.ui_remove_table_row(gt.ntp_table))
        gt.combo_timezone.currentTextChanged.connect(self._on_timezone_changed)
        gt.combo_mgmt_interface.currentTextChanged.connect(self._on_mgmt_interface_changed)
        gt.cb_enable_banner.toggled.connect(gt.te_banner_text.setEnabled)
        gt.cb_archive_config.toggled.connect(self._on_archive_config_toggled)
        gt.cb_archive_time_period.toggled.connect(gt.le_archive_time_period.setEnabled)

        # 보안 탭
        sect = self.security_tab
        sect.btn_add_aaa_group.clicked.connect(lambda: self.ui_add_table_row(sect.aaa_server_table))
        sect.btn_remove_aaa_group.clicked.connect(lambda: self.ui_remove_table_row(sect.aaa_server_table))
        sect.btn_add_user.clicked.connect(lambda: self.ui_add_table_row(sect.users_table))
        sect.btn_remove_user.clicked.connect(lambda: self.ui_remove_table_row(sect.users_table))
        sect.btn_add_snmp.clicked.connect(lambda: self.ui_add_table_row(sect.snmp_community_table))
        sect.btn_remove_snmp.clicked.connect(lambda: self.ui_remove_table_row(sect.snmp_community_table))
        sect.btn_add_snmp_v3.clicked.connect(lambda: self.ui_add_table_row(sect.snmp_v3_user_table))
        sect.btn_remove_snmp_v3.clicked.connect(lambda: self.ui_remove_table_row(sect.snmp_v3_user_table))

        # ACL 탭
        at = self.acl_tab
        at.btn_add_acl.clicked.connect(self.ui_add_acl)
        at.btn_remove_acl.clicked.connect(self.ui_remove_acl)
        at.acl_list_table.itemSelectionChanged.connect(self._on_acl_selected)
        at.acl_list_table.itemChanged.connect(self._save_acl_data)

        at.btn_add_rule.clicked.connect(lambda: self.ui_add_table_row(at.acl_rule_table))
        at.btn_remove_rule.clicked.connect(lambda: self.ui_remove_table_row(at.acl_rule_table))
        at.acl_rule_table.itemChanged.connect(self._save_acl_rule_data)


    # --- 핵심 로직 및 슬롯 메서드 ---
    def run_config_task(self):
        target_hosts = self._get_selected_devices()
        if not target_hosts: return
        user_input_data = self._gather_data_from_ui()
        os_type = self.combo_os_type.currentText()
        try:
            playbook_data = self.config_manager.generate_playbook(os_type, user_input_data)
            self.log_output.appendPlainText(f"===== {', '.join(target_hosts)}에 구성 적용 시작 ({os_type}) =====")
            status, result_stdout = self.ansible_engine.execute_configuration(target_hosts, playbook_data)
            self.log_output.appendPlainText("구성 적용 성공." if status == 'successful' else "구성 적용 실패.")
            self.log_output.appendPlainText("--- Ansible 실행 결과 (모의) ---");
            self.log_output.appendPlainText(result_stdout);
            self.log_output.appendPlainText("--------------------------\n")
        except Exception as e:
            self.log_output.appendPlainText(f"오류 발생: {str(e)}")

    def _fetch_device_info(self):
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "오류", "먼저 장비 목록에서 정보를 가져올 장비를 선택하세요.")
            return
        if len(selected_items) > 1:
            QMessageBox.warning(self, "오류", "정보 가져오기는 한 번에 하나의 장비만 선택할 수 있습니다.")
            return
        target_host = selected_items[0].text()
        os_type = self.combo_os_type.currentText()
        cred_dialog = CredentialsDialog(self)
        if cred_dialog.exec():
            credentials = cred_dialog.get_credentials()
            if not credentials['user'] or not credentials['pass']:
                QMessageBox.warning(self, "오류", "Username과 Password를 모두 입력해야 합니다.")
                return
            self.log_output.appendPlainText(f"[{target_host}] 정보 수집을 시작합니다...");
            QApplication.processEvents()
            success, result = self.ansible_engine.discover_facts(target_host, os_type, credentials)
            if success:
                self.log_output.appendPlainText(f"✓ [{target_host}] 정보 수집 성공!")
                self.interface_tab.interface_list.clear()
                if 'ansible_net_interfaces' in result:
                    for if_name in sorted(result['ansible_net_interfaces'].keys()):
                        self._add_interface_item(if_name)
                version = result.get('ansible_net_version', 'N/A')
                model = result.get('ansible_net_model', 'N/A')
                self.log_output.appendPlainText(f"  - 모델: {model}, OS 버전: {version}")
            else:
                self.log_output.appendPlainText(f"✗ [{target_host}] 정보 수집 실패!")
                error_details = result.get('details', str(result.get('error', '')))
                QMessageBox.critical(self, "정보 수집 실패", error_details)

    # --- 동적 UI 업데이트 메서드 ---
    def _update_ui_for_os(self):
        selected_os = self.combo_os_type.currentText()
        is_ios_xe = 'IOS-XE' in selected_os
        is_nx_os = 'NX-OS' in selected_os
        ios_xe_only_msg = "이 기능은 IOS-XE에서만 사용 가능합니다."
        nx_os_only_msg = "이 기능은 NX-OS에서만 사용 가능합니다."

        gt = self.global_tab
        gt.group_archive.setEnabled(is_ios_xe)
        gt.group_archive.setToolTip(ios_xe_only_msg if not is_ios_xe else "")
        gt.cb_summer_time.setEnabled(is_ios_xe)
        gt.cb_summer_time.setToolTip(ios_xe_only_msg if not is_ios_xe else "")
        gt.le_ntp_master_stratum.setEnabled(is_ios_xe)
        gt.le_ntp_master_stratum.setToolTip(ios_xe_only_msg if not is_ios_xe else "")

        ht = self.ha_tab
        ht.group_svl.setEnabled(is_ios_xe)
        ht.group_svl.setToolTip(ios_xe_only_msg if not is_ios_xe else "")
        ht.group_vpc.setEnabled(is_nx_os)
        ht.group_vpc.setToolTip(nx_os_only_msg if not is_nx_os else "")

        sect = self.security_tab
        sect.combo_vty_transport.setEnabled(is_ios_xe)
        sect.combo_vty_transport.setToolTip(ios_xe_only_msg if not is_ios_xe else "")

        self._on_archive_config_toggled(gt.cb_archive_config.isChecked())

    def _update_dynamic_interface_ui(self, *args):
        it = self.interface_tab
        selected_items = it.interface_list.selectedItems()
        if not selected_items: return

        current_mode = it.combo_if_mode.currentText()
        if current_mode == "--- Multiple Values ---":
            it.mode_stack.setCurrentIndex(-1)
        elif current_mode == "L2 Access":
            it.mode_stack.setCurrentIndex(0)
        elif current_mode == "L2 Trunk":
            it.mode_stack.setCurrentIndex(1)
        elif current_mode == "L3 Routed":
            it.mode_stack.setCurrentIndex(2)
        elif current_mode == "Port-Channel Member":
            it.mode_stack.setCurrentIndex(3)

        all_l2 = all("L2" in item.data(Qt.UserRole)['mode'] for item in selected_items)
        it.group_if_stp.setEnabled(all_l2)
        it.group_if_port_security.setEnabled(all_l2)

        all_fiber = all(item.data(Qt.UserRole)['type'] == "Fiber" for item in selected_items)
        it.group_if_udld.setEnabled(all_fiber)

        self._save_interface_data()

    def _update_mst_ui_visibility(self, mode):
        self.switching_tab.group_mst_config.setVisible(mode == "mst")

    # --- 탭별 데이터 관리 메서드 ---
    def _on_vlan_selected(self):
        vt = self.vlan_tab
        selected_items = vt.vlan_table.selectedItems()
        if not selected_items:
            vt.group_svi.setEnabled(False)
            vt.svi_label.setText("상단 테이블에서 설정을 원하는 VLAN을 선택하세요.")
            self.current_vlan_item = None
            return

        self.current_vlan_item = selected_items[0].row()
        vlan_id_item = vt.vlan_table.item(self.current_vlan_item, 0)
        vlan_id = vlan_id_item.text()
        vt.svi_label.setText(f"VLAN {vlan_id}의 SVI 설정")

        svi_data = vlan_id_item.data(Qt.UserRole) or {}
        vt.cb_svi_enabled.setChecked(svi_data.get('enabled', False))
        vt.le_svi_ip.setText(svi_data.get('ip', ''))

        fhrp_data = svi_data.get('fhrp', {})
        vt.cb_fhrp_enabled.setChecked(fhrp_data.get('enabled', False))
        vt.le_fhrp_group.setText(str(fhrp_data.get('group', '')))
        vt.le_fhrp_vip.setText(fhrp_data.get('vip', ''))
        vt.le_fhrp_priority.setText(str(fhrp_data.get('priority', '')))
        vt.cb_fhrp_preempt.setChecked(fhrp_data.get('preempt', False))

        vt.dhcp_helper_table.setRowCount(0)
        for helper in svi_data.get('dhcp_helpers', []):
            row_pos = vt.dhcp_helper_table.rowCount()
            vt.dhcp_helper_table.insertRow(row_pos)
            vt.dhcp_helper_table.setItem(row_pos, 0, QTableWidgetItem(helper))

        vt.group_svi.setEnabled(True)

    def _save_svi_data(self):
        vt = self.vlan_tab
        if self.current_vlan_item is None: return

        vlan_id_item = vt.vlan_table.item(self.current_vlan_item, 0)
        if not vlan_id_item: return

        helpers = [vt.dhcp_helper_table.item(row, 0).text() for row in range(vt.dhcp_helper_table.rowCount())
                   if vt.dhcp_helper_table.item(row, 0) and vt.dhcp_helper_table.item(row, 0).text()]

        svi_data = {
            'enabled': vt.cb_svi_enabled.isChecked(),
            'ip': vt.le_svi_ip.text(),
            'fhrp': {
                'enabled': vt.cb_fhrp_enabled.isChecked(),
                'group': vt.le_fhrp_group.text(),
                'vip': vt.le_fhrp_vip.text(),
                'priority': vt.le_fhrp_priority.text(),
                'preempt': vt.cb_fhrp_preempt.isChecked()
            },
            'dhcp_helpers': helpers
        }
        vlan_id_item.setData(Qt.UserRole, svi_data)

    def _on_interface_selected(self):
        it = self.interface_tab
        selected_items = it.interface_list.selectedItems()
        if not selected_items:
            it.config_area_widget.setVisible(False)
            return

        self._block_interface_signals(True)
        base_config = selected_items[0].data(Qt.UserRole)
        common_config = deepcopy(base_config)

        if len(selected_items) > 1:
            it.if_label.setText(f"'{len(selected_items)}개 인터페이스 동시 편집'")
            for item in selected_items[1:]:
                current_config = item.data(Qt.UserRole)
                for key, value in list(common_config.items()):
                    if key not in current_config or value != current_config[key]:
                        if isinstance(value, dict):
                            for sub_key, sub_value in list(value.items()):
                                if sub_key not in current_config.get(key, {}) or sub_value != current_config[key][
                                    sub_key]:
                                    del common_config[key][sub_key]
                        else:
                            del common_config[key]
        else:
            it.if_label.setText(f"'{base_config['name']}' 설정")

        it.cb_if_shutdown.setChecked(common_config.get('shutdown', False))
        it.le_if_description.setText(common_config.get('description', ''))
        it.combo_if_type.setCurrentText(common_config.get('type', '--- Multiple Values ---'))
        it.combo_if_mode.setCurrentText(common_config.get('mode', '--- Multiple Values ---'))

        it.le_access_vlan.setText(common_config.get('access', {}).get('vlan', ''))
        it.le_voice_vlan.setText(common_config.get('access', {}).get('voice_vlan', ''))
        it.le_trunk_native.setText(common_config.get('trunk', {}).get('native_vlan', ''))
        it.le_trunk_allowed.setText(common_config.get('trunk', {}).get('allowed_vlans', ''))
        it.le_routed_ip.setText(common_config.get('routed', {}).get('ip', ''))
        it.le_channel_group_id.setText(str(common_config.get('pc_member', {}).get('group_id', '')))
        it.combo_channel_group_mode.setCurrentText(common_config.get('pc_member', {}).get('mode', 'active'))

        it.cb_stp_portfast.setChecked(common_config.get('stp', {}).get('portfast', False))
        it.cb_stp_bpduguard.setChecked(common_config.get('stp', {}).get('bpduguard', False))

        ps_common = common_config.get('port_security', {})
        it.cb_ps_enabled.setChecked(ps_common.get('enabled', False))
        it.le_ps_max_mac.setText(str(ps_common.get('max_mac', '')))
        it.combo_ps_violation.setCurrentText(ps_common.get('violation', '--- Multiple Values ---'))

        # Placeholder for multiple values
        for w, v_key in {it.le_if_description: 'description', it.combo_if_type: 'type',
                         it.combo_if_mode: 'mode'}.items():
            w.setPlaceholderText("--- Multiple Values ---" if v_key not in common_config else "")

        self._update_dynamic_interface_ui()
        it.config_area_widget.setVisible(True)
        self._block_interface_signals(False)

    def _save_interface_data(self):
        it = self.interface_tab
        selected_items = it.interface_list.selectedItems()
        if not selected_items: return

        for item in selected_items:
            config = item.data(Qt.UserRole)
            if it.le_if_description.placeholderText() != "--- Multiple Values ---":
                config['description'] = it.le_if_description.text()
            if it.combo_if_type.currentText() != "--- Multiple Values ---":
                config['type'] = it.combo_if_type.currentText()
            if it.combo_if_mode.currentText() != "--- Multiple Values ---":
                config['mode'] = it.combo_if_mode.currentText()

            config['shutdown'] = it.cb_if_shutdown.isChecked()
            config['access']['vlan'] = it.le_access_vlan.text()
            config['access']['voice_vlan'] = it.le_voice_vlan.text()
            config['trunk']['native_vlan'] = it.le_trunk_native.text()
            config['trunk']['allowed_vlans'] = it.le_trunk_allowed.text()
            config['routed']['ip'] = it.le_routed_ip.text()
            config['pc_member']['group_id'] = it.le_channel_group_id.text()
            config['pc_member']['mode'] = it.combo_channel_group_mode.currentText()
            config['stp']['portfast'] = it.cb_stp_portfast.isChecked()
            config['stp']['bpduguard'] = it.cb_stp_bpduguard.isChecked()
            config['port_security']['enabled'] = it.cb_ps_enabled.isChecked()
            config['port_security']['max_mac'] = it.le_ps_max_mac.text()
            config['port_security']['violation'] = it.combo_ps_violation.currentText()
            config['udld']['enabled'] = it.cb_udld_enabled.isChecked()
            config['udld']['mode'] = it.combo_udld_mode.currentText()

            sc = config['storm_control']
            sc['broadcast'] = it.le_sc_broadcast.text()
            sc['multicast'] = it.le_sc_multicast.text()
            sc['unicast'] = it.le_sc_unicast.text()
            sc['action'] = it.combo_sc_action.currentText()

            item.setData(Qt.UserRole, config)

    # --- UI 헬퍼 메서드 ---
    def ui_add_device(self):
        dialog = AddDevicesDialog(self)
        if dialog.exec():
            self.device_list.addItems(dialog.get_devices())

    def ui_remove_device(self):
        for item in self.device_list.selectedItems():
            self.device_list.takeItem(self.device_list.row(item))

    def ui_add_interface(self):
        dialog = AddInterfacesDialog(self)
        if dialog.exec():
            for if_name in dialog.get_interfaces():
                if not self.interface_tab.interface_list.findItems(if_name, Qt.MatchExactly):
                    self._add_interface_item(if_name)

    def ui_add_port_channel(self):
        num, ok = QInputDialog.getInt(self, "Port-Channel 추가", "Port-Channel 번호 입력:", 1, 1, 4096)
        if ok:
            self._add_interface_item(f"Port-channel{num}")

    def ui_add_table_row(self, table_widget):
        table_widget.insertRow(table_widget.rowCount())

    def ui_remove_table_row(self, table_widget):
        current_row = table_widget.currentRow()
        if current_row > -1:
            table_widget.removeRow(current_row)

    # --- 내부 헬퍼 메서드 ---
    def _add_interface_item(self, interface_name):
        item = QListWidgetItem(interface_name)
        is_pc = 'port-channel' in interface_name.lower()
        default_config = {
            'name': interface_name, 'is_port_channel': is_pc, 'shutdown': False,
            'description': '', 'type': 'Copper', 'mode': 'L2 Access' if not is_pc else 'L2 Trunk',
            'access': {'vlan': '', 'voice_vlan': ''},
            'trunk': {'native_vlan': '', 'allowed_vlans': ''},
            'routed': {'ip': ''},
            'pc_member': {'group_id': '', 'mode': 'active'},
            'stp': {'portfast': False, 'bpduguard': False},
            'port_security': {'enabled': False, 'max_mac': '1', 'violation': 'shutdown'},
            'storm_control': {'broadcast': '', 'multicast': '', 'unicast': '', 'action': 'shutdown'},
            'udld': {'enabled': False, 'mode': 'normal'}
        }
        item.setData(Qt.UserRole, default_config)
        self.interface_tab.interface_list.addItem(item)

    def _block_interface_signals(self, block):
        it = self.interface_tab
        widgets = [it.cb_if_shutdown, it.le_if_description, it.combo_if_type, it.combo_if_mode,
                   it.le_access_vlan, it.le_voice_vlan, it.le_trunk_native, it.le_trunk_allowed,
                   it.le_routed_ip, it.le_channel_group_id, it.combo_channel_group_mode, it.cb_stp_portfast,
                   it.cb_stp_bpduguard, it.cb_ps_enabled, it.le_ps_max_mac, it.combo_ps_violation,
                   it.le_sc_broadcast, it.le_sc_multicast, it.le_sc_unicast, it.combo_sc_action,
                   it.cb_udld_enabled, it.combo_udld_mode]
        for widget in widgets:
            widget.blockSignals(block)

    def _get_selected_devices(self):
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "장비를 먼저 선택해주세요.")
            return None
        return [item.text() for item in selected_items]

    def _gather_data_from_ui(self):
        settings = {'global': {}, 'interfaces': [], 'vlans': {}, 'switching': {}, 'routing': {}, 'ha': {},
                    'security': {}}
        gt = self.global_tab;
        it = self.interface_tab;
        vt = self.vlan_tab
        st = self.switching_tab;
        rt = self.routing_tab;
        ht = self.ha_tab;
        sect = self.security_tab

        # Global
        g = settings['global']
        g['hostname'] = gt.le_hostname.text()
        g['service_timestamps'] = gt.cb_service_timestamps.isChecked()
        g['service_password_encryption'] = gt.cb_service_password_encryption.isChecked()
        g['service_call_home'] = gt.cb_service_call_home.isChecked()
        g['domain_name'] = gt.le_domain_name.text()
        g['dns_servers'] = [{'ip': gt.dns_table.item(r, 0).text(),
                             'vrf': (gt.dns_table.item(r, 1).text() if gt.dns_table.item(r, 1) else '')} for r in
                            range(gt.dns_table.rowCount()) if
                            gt.dns_table.item(r, 0) and gt.dns_table.item(r, 0).text()]
        g[
            'timezone'] = gt.le_custom_timezone.text() if gt.combo_timezone.currentText() == "Custom" else gt.combo_timezone.currentText()
        g['summer_time'] = {'enabled': gt.cb_summer_time.isChecked(), 'zone': gt.le_summer_time_zone.text()}
        g['logging_level'] = gt.combo_logging_level.currentText()
        g['logging_console'] = gt.cb_logging_console.isChecked()
        g['logging_buffered'] = gt.cb_logging_buffered.isChecked()
        g['logging_buffer_size'] = gt.le_logging_buffer_size.text()
        g['logging_hosts'] = [{'ip': gt.logging_table.item(r, 0).text(),
                               'vrf': (gt.logging_table.item(r, 1).text() if gt.logging_table.item(r, 1) else '')} for r
                              in range(gt.logging_table.rowCount()) if
                              gt.logging_table.item(r, 0) and gt.logging_table.item(r, 0).text()]
        g['ntp_authenticate'] = gt.cb_ntp_authenticate.isChecked()
        g['ntp_master_stratum'] = gt.le_ntp_master_stratum.text()
        g['ntp_servers'] = [{'ip': gt.ntp_table.item(r, 0).text(), 'prefer': (
            gt.ntp_table.item(r, 1).text().lower() == 'true' if gt.ntp_table.item(r, 1) else False),
                             'key_id': (gt.ntp_table.item(r, 2).text() if gt.ntp_table.item(r, 2) else ''),
                             'vrf': (gt.ntp_table.item(r, 3).text() if gt.ntp_table.item(r, 3) else '')} for r in
                            range(gt.ntp_table.rowCount()) if
                            gt.ntp_table.item(r, 0) and gt.ntp_table.item(r, 0).text()]
        mgmt_if = gt.combo_mgmt_interface.currentText()
        g['management'] = {'interface': gt.le_custom_mgmt_interface.text() if mgmt_if == "Custom" else (
            "" if mgmt_if == "None" else mgmt_if), 'ip': gt.le_mgmt_ip.text(), 'subnet': gt.le_mgmt_subnet.text(),
                           'gateway': gt.le_mgmt_gateway.text(), 'vrf': gt.le_mgmt_vrf.text()}
        g['banner'] = {'enabled': gt.cb_enable_banner.isChecked(), 'text': gt.te_banner_text.toPlainText()}
        g['archive'] = {'enabled': gt.cb_archive_config.isChecked(), 'path': gt.le_archive_path.text(),
                        'max_files': gt.le_archive_max_files.text(),
                        'time_period_enabled': gt.cb_archive_time_period.isChecked(),
                        'time_period': gt.le_archive_time_period.text()}

        # Interfaces
        settings['interfaces'] = [it.interface_list.item(i).data(Qt.UserRole) for i in range(it.interface_list.count())
                                  if it.interface_list.item(i).data(Qt.UserRole)]

        # VLANs
        settings['vlans']['enable_routing'] = vt.cb_ip_routing.isChecked()
        settings['vlans']['list'] = [{'id': vt.vlan_table.item(r, 0).text(),
                                      'name': (vt.vlan_table.item(r, 1).text() if vt.vlan_table.item(r, 1) else ''),
                                      'description': (
                                          vt.vlan_table.item(r, 2).text() if vt.vlan_table.item(r, 2) else ''),
                                      'svi': vt.vlan_table.item(r, 0).data(Qt.UserRole) or {}} for r in
                                     range(vt.vlan_table.rowCount()) if
                                     vt.vlan_table.item(r, 0) and vt.vlan_table.item(r, 0).text()]

        # Switching
        s = settings['switching']
        s['stp_mode'] = st.combo_stp_mode.currentText()
        s['stp_priority'] = st.le_stp_priority.text()
        s['stp_portfast_default'] = st.cb_stp_portfast_default.isChecked()
        s['stp_bpduguard_default'] = st.cb_stp_bpduguard_default.isChecked()
        s['stp_bpdufilter_default'] = st.cb_stp_bpdufilter_default.isChecked()
        s['stp_loopguard_default'] = st.cb_stp_loopguard_default.isChecked()
        s['mst'] = {'name': st.le_mst_name.text(), 'revision': st.le_mst_revision.text(), 'instances': [
            {'id': st.mst_instance_table.item(r, 0).text(), 'vlans': st.mst_instance_table.item(r, 1).text()} for r in
            range(st.mst_instance_table.rowCount()) if st.mst_instance_table.item(r, 0)]}
        s['vtp'] = {'enabled': st.cb_vtp_enabled.isChecked(), 'mode': st.combo_vtp_mode.currentText(),
                    'domain': st.le_vtp_domain.text(), 'password': st.le_vtp_password.text(),
                    'version': st.combo_vtp_version.currentText()}
        s['l2_security'] = {'dhcp_snooping_enabled': st.cb_dhcp_snooping_enabled.isChecked(),
                            'dhcp_snooping_vlans': st.le_dhcp_snooping_vlans.text(),
                            'dai_vlans': st.le_dai_vlans.text()}

        # Routing
        r = settings['routing']
        r['static_routes'] = [
            {'prefix': rt.static_route_table.item(i, 0).text(), 'nexthop': rt.static_route_table.item(i, 1).text(),
             'metric': rt.static_route_table.item(i, 2).text(), 'vrf': rt.static_route_table.item(i, 3).text()} for i in
            range(rt.static_route_table.rowCount()) if rt.static_route_table.item(i, 0)]
        r['ospf'] = {'enabled': rt.cb_ospf_enabled.isChecked(), 'process_id': rt.le_ospf_process_id.text(),
                     'router_id': rt.le_ospf_router_id.text(), 'networks': [
                {'prefix': rt.ospf_network_table.item(i, 0).text(), 'wildcard': rt.ospf_network_table.item(i, 1).text(),
                 'area': rt.ospf_network_table.item(i, 2).text()} for i in range(rt.ospf_network_table.rowCount()) if
                rt.ospf_network_table.item(i, 0)]}
        r['eigrp'] = {'enabled': rt.cb_eigrp_enabled.isChecked(), 'as_number': rt.le_eigrp_as_number.text(),
                      'router_id': rt.le_eigrp_router_id.text(), 'networks': [
                {'prefix': rt.eigrp_network_table.item(i, 0).text(),
                 'wildcard': rt.eigrp_network_table.item(i, 1).text()} for i in range(rt.eigrp_network_table.rowCount())
                if rt.eigrp_network_table.item(i, 0)]}
        r['bgp'] = {'enabled': rt.cb_bgp_enabled.isChecked(), 'as_number': rt.le_bgp_as_number.text(),
                    'router_id': rt.le_bgp_router_id.text(), 'neighbors': [
                {'ip': rt.bgp_neighbor_table.item(i, 0).text(), 'remote_as': rt.bgp_neighbor_table.item(i, 1).text(),
                 'description': rt.bgp_neighbor_table.item(i, 2).text(),
                 'update_source': rt.bgp_neighbor_table.item(i, 3).text(),
                 'rmap_in': rt.bgp_neighbor_table.item(i, 4).text(),
                 'rmap_out': rt.bgp_neighbor_table.item(i, 5).text()} for i in range(rt.bgp_neighbor_table.rowCount())
                if rt.bgp_neighbor_table.item(i, 0)],
                    'networks': [line.strip() for line in rt.te_bgp_networks.toPlainText().splitlines() if
                                 line.strip()]}

        # HA
        ha = settings['ha']
        ha['svl'] = {'enabled': ht.cb_svl_enabled.isChecked(), 'domain': ht.le_svl_domain.text()}
        ha['vpc'] = {'enabled': ht.cb_vpc_enabled.isChecked(), 'domain': ht.le_vpc_domain.text(),
                     'peer_keepalive': ht.le_vpc_peer_keepalive.text()}

        # Security
        sec = settings['security']
        sec['aaa_new_model'] = sect.cb_aaa_new_model.isChecked()
        sec['aaa_auth_login'] = sect.le_aaa_auth_login.text()
        sec['aaa_auth_exec'] = sect.le_aaa_auth_exec.text()
        sec['aaa_groups'] = [
            {'type': sect.aaa_server_table.item(r, 0).text(), 'group_name': sect.aaa_server_table.item(r, 1).text(),
             'servers': [s.strip() for s in sect.aaa_server_table.item(r, 2).text().split(',') if s.strip()]} for r in
            range(sect.aaa_server_table.rowCount()) if sect.aaa_server_table.item(r, 1)]
        sec['local_users'] = [{'username': sect.users_table.item(r, 0).text(), 'privilege': (
            sect.users_table.item(r, 1).text() if sect.users_table.item(r, 1) else '1'),
                               'password': (sect.users_table.item(r, 2).text() if sect.users_table.item(r, 2) else '')}
                              for r in range(sect.users_table.rowCount()) if
                              sect.users_table.item(r, 0) and sect.users_table.item(r, 0).text()]
        sec['line_config'] = {'con_timeout': sect.le_con_exec_timeout.text(),
                              'con_logging_sync': sect.cb_con_logging_sync.isChecked(),
                              'con_auth_aaa': sect.cb_con_auth_aaa.isChecked(),
                              'con_auth_method': sect.le_con_auth_method.text(), 'vty_range': sect.le_vty_range.text(),
                              'vty_timeout': sect.le_vty_exec_timeout.text(),
                              'vty_transport': sect.combo_vty_transport.currentText()}
        sec['snmp'] = {'location': sect.le_snmp_location.text(), 'contact': sect.le_snmp_contact.text(),
                       'communities': [{'community': sect.snmp_community_table.item(r, 0).text(), 'permission': (
                           sect.snmp_community_table.item(r, 1).text() if sect.snmp_community_table.item(r,
                                                                                                         1) else 'RO'),
                                        'acl': (sect.snmp_community_table.item(r,
                                                                               2).text() if sect.snmp_community_table.item(
                                            r, 2) else '')} for r in range(sect.snmp_community_table.rowCount()) if
                                       sect.snmp_community_table.item(r, 0)], 'v3_users': [
                {'username': sect.snmp_v3_user_table.item(r, 0).text(),
                 'group': sect.snmp_v3_user_table.item(r, 1).text(),
                 'auth_proto': sect.snmp_v3_user_table.item(r, 2).text(),
                 'auth_pass': sect.snmp_v3_user_table.item(r, 3).text(),
                 'priv_proto': sect.snmp_v3_user_table.item(r, 4).text(),
                 'priv_pass': sect.snmp_v3_user_table.item(r, 5).text()} for r in
                range(sect.snmp_v3_user_table.rowCount()) if
                sect.snmp_v3_user_table.item(r, 0) and sect.snmp_v3_user_table.item(r, 0).text()]}
        sec['hardening'] = {'no_ip_http': sect.cb_no_ip_http.isChecked(), 'no_cdp': sect.cb_no_cdp.isChecked(),
                            'lldp': sect.cb_lldp.isChecked()}



        return {
            "devices": [self.device_list.item(i).text() for i in range(self.device_list.count())],
            "settings": settings
        }

    def _apply_data_to_ui(self, data):
        self._block_interface_signals(True)
        gt = self.global_tab;
        it = self.interface_tab;
        vt = self.vlan_tab
        st = self.switching_tab;
        rt = self.routing_tab;
        ht = self.ha_tab;
        sect = self.security_tab

        # Device List
        self.device_list.clear()
        self.device_list.addItems(data.get('devices', []))
        settings = data.get('settings', {})

        # Global
        g = settings.get('global', {})
        gt.le_hostname.setText(g.get('hostname', ''))
        gt.cb_service_timestamps.setChecked(g.get('service_timestamps', False))
        gt.cb_service_password_encryption.setChecked(g.get('service_password_encryption', False))
        gt.cb_service_call_home.setChecked(g.get('service_call_home', False))
        gt.le_domain_name.setText(g.get('domain_name', ''))
        gt.dns_table.setRowCount(0)
        for server in g.get('dns_servers', []):
            row = gt.dns_table.rowCount();
            gt.dns_table.insertRow(row)
            gt.dns_table.setItem(row, 0, QTableWidgetItem(server.get('ip')));
            gt.dns_table.setItem(row, 1, QTableWidgetItem(server.get('vrf')))
        gt.combo_timezone.setCurrentText(g.get('timezone', 'KST 9'))
        gt.le_custom_timezone.setText(g.get('timezone', '') if gt.combo_timezone.currentText() == "Custom" else "")
        summer_time = g.get('summer_time', {});
        gt.cb_summer_time.setChecked(summer_time.get('enabled', False));
        gt.le_summer_time_zone.setText(summer_time.get('zone', ''))
        gt.combo_logging_level.setCurrentText(g.get('logging_level', 'informational (6)'))
        gt.cb_logging_console.setChecked(g.get('logging_console', True));
        gt.cb_logging_buffered.setChecked(g.get('logging_buffered', True))
        gt.le_logging_buffer_size.setText(g.get('logging_buffer_size', '32000'))
        gt.logging_table.setRowCount(0)
        for host in g.get('logging_hosts', []):
            row = gt.logging_table.rowCount();
            gt.logging_table.insertRow(row)
            gt.logging_table.setItem(row, 0, QTableWidgetItem(host.get('ip')));
            gt.logging_table.setItem(row, 1, QTableWidgetItem(host.get('vrf')))
        gt.cb_ntp_authenticate.setChecked(g.get('ntp_authenticate', False));
        gt.le_ntp_master_stratum.setText(g.get('ntp_master_stratum', ''))
        gt.ntp_table.setRowCount(0)
        for server in g.get('ntp_servers', []):
            row = gt.ntp_table.rowCount();
            gt.ntp_table.insertRow(row)
            gt.ntp_table.setItem(row, 0, QTableWidgetItem(server.get('ip')));
            gt.ntp_table.setItem(row, 1, QTableWidgetItem(str(server.get('prefer', False))));
            gt.ntp_table.setItem(row, 2, QTableWidgetItem(server.get('key_id')));
            gt.ntp_table.setItem(row, 3, QTableWidgetItem(server.get('vrf')))
        mgmt = g.get('management', {});
        gt.combo_mgmt_interface.setCurrentText(mgmt.get('interface', 'None'));
        gt.le_mgmt_ip.setText(mgmt.get('ip', ''));
        gt.le_mgmt_subnet.setText(mgmt.get('subnet', ''));
        gt.le_mgmt_gateway.setText(mgmt.get('gateway', ''));
        gt.le_mgmt_vrf.setText(mgmt.get('vrf', ''))
        banner = g.get('banner', {});
        gt.cb_enable_banner.setChecked(banner.get('enabled', False));
        gt.te_banner_text.setPlainText(banner.get('text', ''))
        archive = g.get('archive', {});
        gt.cb_archive_config.setChecked(archive.get('enabled', False));
        gt.le_archive_path.setText(archive.get('path', ''));
        gt.le_archive_max_files.setText(archive.get('max_files', ''));
        gt.cb_archive_time_period.setChecked(archive.get('time_period_enabled', False));
        gt.le_archive_time_period.setText(archive.get('time_period', ''))

        # Interfaces
        it.interface_list.clear()
        for if_config in settings.get('interfaces', []):
            self._add_interface_item(if_config.get('name', 'Unknown Interface'))
            last_item_index = it.interface_list.count() - 1
            if last_item_index >= 0:
                it.interface_list.item(last_item_index).setData(Qt.UserRole, if_config)

        # VLANs
        vlans_data = settings.get('vlans', {});
        vt.cb_ip_routing.setChecked(vlans_data.get('enable_routing', False))
        vt.vlan_table.setRowCount(0)
        for vlan_data in vlans_data.get('list', []):
            row = vt.vlan_table.rowCount();
            vt.vlan_table.insertRow(row)
            vlan_id_item = QTableWidgetItem(vlan_data.get('id'));
            vlan_id_item.setData(Qt.UserRole, vlan_data.get('svi', {}))
            vt.vlan_table.setItem(row, 0, vlan_id_item);
            vt.vlan_table.setItem(row, 1, QTableWidgetItem(vlan_data.get('name')));
            vt.vlan_table.setItem(row, 2, QTableWidgetItem(vlan_data.get('description')))

        # Switching
        s = settings.get('switching', {});
        st.combo_stp_mode.setCurrentText(s.get('stp_mode', 'rapid-pvst'));
        st.le_stp_priority.setText(s.get('stp_priority', ''));
        st.cb_stp_portfast_default.setChecked(s.get('stp_portfast_default', False));
        st.cb_stp_bpduguard_default.setChecked(s.get('stp_bpduguard_default', False));
        st.cb_stp_bpdufilter_default.setChecked(s.get('stp_bpdufilter_default', False));
        st.cb_stp_loopguard_default.setChecked(s.get('stp_loopguard_default', False))
        mst = s.get('mst', {});
        st.le_mst_name.setText(mst.get('name', ''));
        st.le_mst_revision.setText(mst.get('revision', '0'));
        st.mst_instance_table.setRowCount(0)
        for inst in mst.get('instances', []):
            row = st.mst_instance_table.rowCount();
            st.mst_instance_table.insertRow(row);
            st.mst_instance_table.setItem(row, 0, QTableWidgetItem(inst.get('id')));
            st.mst_instance_table.setItem(row, 1, QTableWidgetItem(inst.get('vlans')))
        vtp = s.get('vtp', {});
        st.cb_vtp_enabled.setChecked(vtp.get('enabled', False));
        st.combo_vtp_mode.setCurrentText(vtp.get('mode', 'transparent'));
        st.le_vtp_domain.setText(vtp.get('domain', ''));
        st.le_vtp_password.setText(vtp.get('password', ''));
        st.combo_vtp_version.setCurrentText(vtp.get('version', '2'))
        l2_sec = s.get('l2_security', {});
        st.cb_dhcp_snooping_enabled.setChecked(l2_sec.get('dhcp_snooping_enabled', False));
        st.le_dhcp_snooping_vlans.setText(l2_sec.get('dhcp_snooping_vlans', ''));
        st.le_dai_vlans.setText(l2_sec.get('dai_vlans', ''))

        # Routing
        r = settings.get('routing', {});
        rt.static_route_table.setRowCount(0)
        for route in r.get('static_routes', []):
            row = rt.static_route_table.rowCount();
            rt.static_route_table.insertRow(row);
            rt.static_route_table.setItem(row, 0, QTableWidgetItem(route.get('prefix')));
            rt.static_route_table.setItem(row, 1, QTableWidgetItem(route.get('nexthop')));
            rt.static_route_table.setItem(row, 2, QTableWidgetItem(route.get('metric')));
            rt.static_route_table.setItem(row, 3, QTableWidgetItem(route.get('vrf')))
        ospf = r.get('ospf', {});
        rt.cb_ospf_enabled.setChecked(ospf.get('enabled', False));
        rt.le_ospf_process_id.setText(ospf.get('process_id', '1'));
        rt.le_ospf_router_id.setText(ospf.get('router_id', ''));
        rt.ospf_network_table.setRowCount(0)
        for net in ospf.get('networks', []):
            row = rt.ospf_network_table.rowCount();
            rt.ospf_network_table.insertRow(row);
            rt.ospf_network_table.setItem(row, 0, QTableWidgetItem(net.get('prefix')));
            rt.ospf_network_table.setItem(row, 1, QTableWidgetItem(net.get('wildcard')));
            rt.ospf_network_table.setItem(row, 2, QTableWidgetItem(net.get('area')))
        eigrp = r.get('eigrp', {});
        rt.cb_eigrp_enabled.setChecked(eigrp.get('enabled', False));
        rt.le_eigrp_as_number.setText(eigrp.get('as_number', '100'));
        rt.le_eigrp_router_id.setText(eigrp.get('router_id', ''));
        rt.eigrp_network_table.setRowCount(0)
        for net in eigrp.get('networks', []):
            row = rt.eigrp_network_table.rowCount();
            rt.eigrp_network_table.insertRow(row);
            rt.eigrp_network_table.setItem(row, 0, QTableWidgetItem(net.get('prefix')));
            rt.eigrp_network_table.setItem(row, 1, QTableWidgetItem(net.get('wildcard')))
        bgp = r.get('bgp', {});
        rt.cb_bgp_enabled.setChecked(bgp.get('enabled', False));
        rt.le_bgp_as_number.setText(bgp.get('as_number', '65001'));
        rt.le_bgp_router_id.setText(bgp.get('router_id', ''));
        rt.bgp_neighbor_table.setRowCount(0)
        for n in bgp.get('neighbors', []):
            row = rt.bgp_neighbor_table.rowCount();
            rt.bgp_neighbor_table.insertRow(row);
            rt.bgp_neighbor_table.setItem(row, 0, QTableWidgetItem(n.get('ip')));
            rt.bgp_neighbor_table.setItem(row, 1, QTableWidgetItem(n.get('remote_as')));
            rt.bgp_neighbor_table.setItem(row, 2, QTableWidgetItem(n.get('description')));
            rt.bgp_neighbor_table.setItem(row, 3, QTableWidgetItem(n.get('update_source')));
            rt.bgp_neighbor_table.setItem(row, 4, QTableWidgetItem(n.get('rmap_in')));
            rt.bgp_neighbor_table.setItem(row, 5, QTableWidgetItem(n.get('rmap_out')))
        rt.te_bgp_networks.setPlainText("\n".join(bgp.get('networks', [])))

        # HA
        ha = settings.get('ha', {});
        svl = ha.get('svl', {});
        ht.cb_svl_enabled.setChecked(svl.get('enabled', False));
        ht.le_svl_domain.setText(svl.get('domain', ''))
        vpc = ha.get('vpc', {});
        ht.cb_vpc_enabled.setChecked(vpc.get('enabled', False));
        ht.le_vpc_domain.setText(vpc.get('domain', ''));
        ht.le_vpc_peer_keepalive.setText(vpc.get('peer_keepalive', ''))

        # Security
        sec = settings.get('security', {});
        sect.cb_aaa_new_model.setChecked(sec.get('aaa_new_model', False));
        sect.le_aaa_auth_login.setText(sec.get('aaa_auth_login', ''));
        sect.le_aaa_auth_exec.setText(sec.get('aaa_auth_exec', ''))
        sect.aaa_server_table.setRowCount(0)
        for group in sec.get('aaa_groups', []):
            row = sect.aaa_server_table.rowCount();
            sect.aaa_server_table.insertRow(row);
            sect.aaa_server_table.setItem(row, 0, QTableWidgetItem(group.get('type')));
            sect.aaa_server_table.setItem(row, 1, QTableWidgetItem(group.get('group_name')));
            sect.aaa_server_table.setItem(row, 2, QTableWidgetItem(",".join(group.get('servers', []))))
        sect.users_table.setRowCount(0)
        for user in sec.get('local_users', []):
            row = sect.users_table.rowCount();
            sect.users_table.insertRow(row);
            sect.users_table.setItem(row, 0, QTableWidgetItem(user.get('username')));
            sect.users_table.setItem(row, 1, QTableWidgetItem(user.get('privilege')));
            sect.users_table.setItem(row, 2, QTableWidgetItem(user.get('password')))
        line = sec.get('line_config', {});
        sect.le_con_exec_timeout.setText(line.get('con_timeout', '15 0'));
        sect.cb_con_logging_sync.setChecked(line.get('con_logging_sync', True));
        sect.cb_con_auth_aaa.setChecked(line.get('con_auth_aaa', False));
        sect.le_con_auth_method.setText(line.get('con_auth_method', 'default'));
        sect.le_vty_range.setText(line.get('vty_range', '0 4'));
        sect.le_vty_exec_timeout.setText(line.get('vty_timeout', '15 0'));
        sect.combo_vty_transport.setCurrentText(line.get('vty_transport', 'ssh'))
        snmp = sec.get('snmp', {});
        sect.le_snmp_location.setText(snmp.get('location', ''));
        sect.le_snmp_contact.setText(snmp.get('contact', ''));
        sect.snmp_community_table.setRowCount(0)
        for comm in snmp.get('communities', []):
            row = sect.snmp_community_table.rowCount();
            sect.snmp_community_table.insertRow(row);
            sect.snmp_community_table.setItem(row, 0, QTableWidgetItem(comm.get('community')));
            sect.snmp_community_table.setItem(row, 1, QTableWidgetItem(comm.get('permission')));
            sect.snmp_community_table.setItem(row, 2, QTableWidgetItem(comm.get('acl')))
        sect.snmp_v3_user_table.setRowCount(0)
        for user in snmp.get('v3_users', []):
            row = sect.snmp_v3_user_table.rowCount();
            sect.snmp_v3_user_table.insertRow(row);
            sect.snmp_v3_user_table.setItem(row, 0, QTableWidgetItem(user.get('username')));
            sect.snmp_v3_user_table.setItem(row, 1, QTableWidgetItem(user.get('group')));
            sect.snmp_v3_user_table.setItem(row, 2, QTableWidgetItem(user.get('auth_proto')));
            sect.snmp_v3_user_table.setItem(row, 3, QTableWidgetItem(user.get('auth_pass')));
            sect.snmp_v3_user_table.setItem(row, 4, QTableWidgetItem(user.get('priv_proto')));
            sect.snmp_v3_user_table.setItem(row, 5, QTableWidgetItem(user.get('priv_pass')))
        hardening = sec.get('hardening', {});

        # ACLs
        at.acl_list_table.setRowCount(0)
        for acl_data in settings.get('acls', []):
            row = at.acl_list_table.rowCount()
            at.acl_list_table.insertRow(row)
            name_item = QTableWidgetItem(acl_data.get("name"))
            name_item.setData(Qt.UserRole, acl_data.get("rules", []))
            at.acl_list_table.setItem(row, 0, name_item)
            at.acl_list_table.setItem(row, 1, QTableWidgetItem(acl_data.get("type")))
            at.acl_list_table.setItem(row, 2, QTableWidgetItem(acl_data.get("description")))
        self._update_acl_comboboxes()

        sect.cb_no_ip_http.setChecked(hardening.get('no_ip_http', True));
        sect.cb_no_cdp.setChecked(hardening.get('no_cdp', False));
        sect.cb_lldp.setChecked(hardening.get('lldp', True))

        it.config_area_widget.setVisible(False)
        self._block_interface_signals(False)
        self._update_ui_for_os()

    # --- 파일 메뉴 관련 메서드 ---
    def _new_config_profile(self):
        reply = QMessageBox.question(self, "새 구성", "현재 설정을 지우고 새로 시작하시겠습니까?", QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            blank_data = {"devices": [], "settings": {}}
            self._apply_data_to_ui(blank_data)
            self.current_config_path = None
            self.log_output.appendPlainText("UI가 초기화되었습니다.")

    def _load_config_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "구성 열기", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._apply_data_to_ui(config_data)
                self.current_config_path = path
                self.log_output.appendPlainText(f"'{os.path.basename(path)}' 구성을 불러왔습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"구성을 불러오는 중 오류 발생:\n{e}")

    def _save_config_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "다른 이름으로 구성 저장", "", "JSON Files (*.json)")
        if path:
            try:
                config_data = self._gather_data_from_ui()
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                self.current_config_path = path
                self.log_output.appendPlainText(f"'{os.path.basename(path)}' 파일으로 구성을 저장했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"구성을 저장하는 중 오류 발생:\n{e}")

    # --- 기타 동적 UI 헬퍼 ---
    def _on_timezone_changed(self, timezone):
        self.global_tab.le_custom_timezone.setEnabled(timezone == "Custom")
        if timezone != "Custom": self.global_tab.le_custom_timezone.clear()

    def _on_mgmt_interface_changed(self, interface):
        self.global_tab.le_custom_mgmt_interface.setEnabled(interface == "Custom")
        if interface != "Custom": self.global_tab.le_custom_mgmt_interface.clear()

    def _on_archive_config_toggled(self, checked):
        gt = self.global_tab
        gt.le_archive_path.setEnabled(checked)
        gt.le_archive_max_files.setEnabled(checked)
        gt.cb_archive_time_period.setEnabled(checked)
        gt.le_archive_time_period.setEnabled(checked and gt.cb_archive_time_period.isChecked())
        if not checked:
            gt.le_archive_path.clear()
            gt.le_archive_max_files.clear()
            gt.cb_archive_time_period.setChecked(False)
            gt.le_archive_time_period.clear()

        # --- ACL 관련 UI 헬퍼 및 슬롯 메서드 ---

    def ui_add_acl(self):
            """ACL 목록 테이블에 새로운 행을 추가하는 UI 슬롯"""
            at = self.acl_tab
            row = at.acl_list_table.rowCount()
            at.acl_list_table.insertRow(row)

            # 기본값으로 데이터 아이템 생성
            name_item = QTableWidgetItem("ACL_NAME_")
            type_item = QTableWidgetItem("standard")  # 또는 extended
            desc_item = QTableWidgetItem("")

            # 각 ACL 행은 자신의 규칙 목록(rules)을 데이터로 가짐
            name_item.setData(Qt.UserRole, [])

            at.acl_list_table.setItem(row, 0, name_item)
            at.acl_list_table.setItem(row, 1, type_item)
            at.acl_list_table.setItem(row, 2, desc_item)
            at.acl_list_table.selectRow(row)
            self._update_acl_comboboxes()

    def ui_remove_acl(self):
            """ACL 목록 테이블에서 선택된 행을 삭제하는 UI 슬롯"""
            at = self.acl_tab
            current_row = at.acl_list_table.currentRow()
            if current_row > -1:
                at.acl_list_table.removeRow(current_row)
                self._update_acl_comboboxes()

    def _on_acl_selected(self):
            """ACL 목록에서 특정 ACL을 선택했을 때 호출되는 슬롯"""
            at = self.acl_tab
            selected_items = at.acl_list_table.selectedItems()

            if not selected_items:
                at.acl_rule_group.setEnabled(False)
                at.acl_rule_label.setText("상단 목록에서 규칙을 수정할 ACL을 선택하세요.")
                at.acl_rule_table.setRowCount(0)
                return

            current_row = selected_items[0].row()
            name_item = at.acl_list_table.item(current_row, 0)
            acl_name = name_item.text()

            # 규칙 데이터 불러오기
            rules = name_item.data(Qt.UserRole) or []

            at.acl_rule_table.setRowCount(0)  # 기존 규칙 비우기
            for rule in rules:
                row_pos = at.acl_rule_table.rowCount()
                at.acl_rule_table.insertRow(row_pos)
                at.acl_rule_table.setItem(row_pos, 0, QTableWidgetItem(rule.get("seq", "")))
                at.acl_rule_table.setItem(row_pos, 1, QTableWidgetItem(rule.get("action", "permit")))
                at.acl_rule_table.setItem(row_pos, 2, QTableWidgetItem(rule.get("protocol", "ip")))
                at.acl_rule_table.setItem(row_pos, 3, QTableWidgetItem(rule.get("source", "")))
                at.acl_rule_table.setItem(row_pos, 4, QTableWidgetItem(rule.get("destination", "")))
                at.acl_rule_table.setItem(row_pos, 5, QTableWidgetItem(rule.get("src_port", "")))
                at.acl_rule_table.setItem(row_pos, 6, QTableWidgetItem(rule.get("dest_port", "")))
                at.acl_rule_table.setItem(row_pos, 7, QTableWidgetItem(rule.get("options", "")))

            at.acl_rule_label.setText(f"'{acl_name}'에 대한 규칙 편집")
            at.acl_rule_group.setEnabled(True)

    def _save_acl_data(self, item):
            """ACL 목록 테이블의 내용(이름, 타입, 설명)이 변경될 때 호출"""
            if item.column() == 0:  # 이름이 변경되면 콤보박스 업데이트
                self._update_acl_comboboxes()

    def _save_acl_rule_data(self):
            """ACL 규칙 테이블의 내용이 변경될 때, 데이터를 다시 저장하는 슬롯"""
            at = self.acl_tab
            current_acl_row = at.acl_list_table.currentRow()
            if current_acl_row < 0:
                return

            name_item = at.acl_list_table.item(current_acl_row, 0)
            rules = []
            for row in range(at.acl_rule_table.rowCount()):
                rule = {
                    "seq": at.acl_rule_table.item(row, 0).text() if at.acl_rule_table.item(row, 0) else "",
                    "action": at.acl_rule_table.item(row, 1).text() if at.acl_rule_table.item(row, 1) else "",
                    "protocol": at.acl_rule_table.item(row, 2).text() if at.acl_rule_table.item(row, 2) else "",
                    "source": at.acl_rule_table.item(row, 3).text() if at.acl_rule_table.item(row, 3) else "",
                    "destination": at.acl_rule_table.item(row, 4).text() if at.acl_rule_table.item(row, 4) else "",
                    "src_port": at.acl_rule_table.item(row, 5).text() if at.acl_rule_table.item(row, 5) else "",
                    "dest_port": at.acl_rule_table.item(row, 6).text() if at.acl_rule_table.item(row, 6) else "",
                    "options": at.acl_rule_table.item(row, 7).text() if at.acl_rule_table.item(row, 7) else "",
                }
                rules.append(rule)

            name_item.setData(Qt.UserRole, rules)

    def _update_acl_comboboxes(self):
            """ACL 목록이 변경될 때마다 다른 탭의 ACL 콤보박스를 업데이트"""
            at = self.acl_tab
            acl_names = [""]  # 첫 번째는 빈 값
            for row in range(at.acl_list_table.rowCount()):
                item = at.acl_list_table.item(row, 0)
                if item and item.text():
                    acl_names.append(item.text())

            # 대상 콤보박스들
            combo_boxes = [
                self.security_tab.combo_vty_access_class,
                self.interface_tab.combo_routed_acl_in,
                self.interface_tab.combo_routed_acl_out
            ]

            for combo in combo_boxes:
                current_text = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(acl_names)
                if current_text in acl_names:
                    combo.setCurrentText(current_text)
                combo.blockSignals(False)




    # --- 파일 메뉴 및 데이터 관리 메서드 ---

    def _new_config_profile(self):
        """UI를 기본값으로 초기화합니다."""
        reply = QMessageBox.question(self, "새 구성", "현재 설정을 지우고 새로 시작하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 모든 입력 필드를 지우기 위해 빈 데이터를 UI에 적용
            blank_data = {"devices": [], "settings": {}}
            self._apply_data_to_ui(blank_data)
            self.current_config_path = None
            self.log_output.appendPlainText("UI가 초기화되었습니다.")

    def _load_config_profile(self):
        """파일에서 구성 프로필을 불러와 UI에 적용합니다."""
        path, _ = QFileDialog.getOpenFileName(self, "구성 열기", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._apply_data_to_ui(config_data)
                self.current_config_path = path
                self.log_output.appendPlainText(f"'{os.path.basename(path)}' 구성을 불러왔습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"구성을 불러오는 중 오류 발생:\n{e}")

    def _save_config_profile(self):
        """현재 UI 상태를 구성 프로필 파일로 저장합니다."""
        path, _ = QFileDialog.getSaveFileName(self, "다른 이름으로 구성 저장", "", "JSON Files (*.json)")
        if path:
            try:
                config_data = self._gather_data_from_ui()
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                self.current_config_path = path
                self.log_output.appendPlainText(f"'{os.path.basename(path)}' 파일으로 구성을 저장했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"구성을 저장하는 중 오류 발생:\n{e}")

    def _gather_data_from_ui(self):
        """현재 UI의 모든 상태를 하나의 딕셔너리로 수집합니다."""
        settings = {'global': {}, 'interfaces': [], 'vlans': {}, 'switching': {}, 'routing': {}, 'ha': {},
                    'security': {}}
        gt = self.global_tab;
        it = self.interface_tab;
        vt = self.vlan_tab
        st = self.switching_tab;
        rt = self.routing_tab;
        ht = self.ha_tab;
        sect = self.security_tab
        at = self.acl_tab

        # Global
        g = settings['global']
        g['hostname'] = gt.le_hostname.text()
        g['service_timestamps'] = gt.cb_service_timestamps.isChecked()
        g['service_password_encryption'] = gt.cb_service_password_encryption.isChecked()
        g['service_call_home'] = gt.cb_service_call_home.isChecked()
        g['domain_name'] = gt.le_domain_name.text()
        g['dns_servers'] = [{'ip': gt.dns_table.item(r, 0).text(),
                             'vrf': (gt.dns_table.item(r, 1).text() if gt.dns_table.item(r, 1) else '')} for r in
                            range(gt.dns_table.rowCount()) if
                            gt.dns_table.item(r, 0) and gt.dns_table.item(r, 0).text()]
        g[
            'timezone'] = gt.le_custom_timezone.text() if gt.combo_timezone.currentText() == "Custom" else gt.combo_timezone.currentText()
        g['summer_time'] = {'enabled': gt.cb_summer_time.isChecked(), 'zone': gt.le_summer_time_zone.text()}
        g['logging_level'] = gt.combo_logging_level.currentText()
        g['logging_console'] = gt.cb_logging_console.isChecked()
        g['logging_buffered'] = gt.cb_logging_buffered.isChecked()
        g['logging_buffer_size'] = gt.le_logging_buffer_size.text()
        g['logging_hosts'] = [{'ip': gt.logging_table.item(r, 0).text(),
                               'vrf': (gt.logging_table.item(r, 1).text() if gt.logging_table.item(r, 1) else '')} for r
                              in range(gt.logging_table.rowCount()) if
                              gt.logging_table.item(r, 0) and gt.logging_table.item(r, 0).text()]
        g['ntp_authenticate'] = gt.cb_ntp_authenticate.isChecked()
        g['ntp_master_stratum'] = gt.le_ntp_master_stratum.text()
        g['ntp_servers'] = [{'ip': gt.ntp_table.item(r, 0).text(), 'prefer': (
            gt.ntp_table.item(r, 1).text().lower() == 'true' if gt.ntp_table.item(r, 1) else False),
                             'key_id': (gt.ntp_table.item(r, 2).text() if gt.ntp_table.item(r, 2) else ''),
                             'vrf': (gt.ntp_table.item(r, 3).text() if gt.ntp_table.item(r, 3) else '')} for r in
                            range(gt.ntp_table.rowCount()) if
                            gt.ntp_table.item(r, 0) and gt.ntp_table.item(r, 0).text()]
        mgmt_if = gt.combo_mgmt_interface.currentText()
        g['management'] = {'interface': gt.le_custom_mgmt_interface.text() if mgmt_if == "Custom" else (
            "" if mgmt_if == "None" else mgmt_if), 'ip': gt.le_mgmt_ip.text(), 'subnet': gt.le_mgmt_subnet.text(),
                           'gateway': gt.le_mgmt_gateway.text(), 'vrf': gt.le_mgmt_vrf.text()}
        g['banner'] = {'enabled': gt.cb_enable_banner.isChecked(), 'text': gt.te_banner_text.toPlainText()}
        g['archive'] = {'enabled': gt.cb_archive_config.isChecked(), 'path': gt.le_archive_path.text(),
                        'max_files': gt.le_archive_max_files.text(),
                        'time_period_enabled': gt.cb_archive_time_period.isChecked(),
                        'time_period': gt.le_archive_time_period.text()}

        # Interfaces
        settings['interfaces'] = [it.interface_list.item(i).data(Qt.UserRole) for i in range(it.interface_list.count())
                                  if it.interface_list.item(i).data(Qt.UserRole)]

        # VLANs
        settings['vlans']['enable_routing'] = vt.cb_ip_routing.isChecked()
        settings['vlans']['list'] = [{'id': vt.vlan_table.item(r, 0).text(),
                                      'name': (vt.vlan_table.item(r, 1).text() if vt.vlan_table.item(r, 1) else ''),
                                      'description': (
                                          vt.vlan_table.item(r, 2).text() if vt.vlan_table.item(r, 2) else ''),
                                      'svi': vt.vlan_table.item(r, 0).data(Qt.UserRole) or {}} for r in
                                     range(vt.vlan_table.rowCount()) if
                                     vt.vlan_table.item(r, 0) and vt.vlan_table.item(r, 0).text()]

        # Switching
        s = settings['switching']
        s['stp_mode'] = st.combo_stp_mode.currentText()
        s['stp_priority'] = st.le_stp_priority.text()
        s['stp_portfast_default'] = st.cb_stp_portfast_default.isChecked()
        s['stp_bpduguard_default'] = st.cb_stp_bpduguard_default.isChecked()
        s['stp_bpdufilter_default'] = st.cb_stp_bpdufilter_default.isChecked()
        s['stp_loopguard_default'] = st.cb_stp_loopguard_default.isChecked()
        s['mst'] = {'name': st.le_mst_name.text(), 'revision': st.le_mst_revision.text(), 'instances': [
            {'id': st.mst_instance_table.item(r, 0).text(), 'vlans': st.mst_instance_table.item(r, 1).text()} for r in
            range(st.mst_instance_table.rowCount()) if st.mst_instance_table.item(r, 0)]}
        s['vtp'] = {'enabled': st.cb_vtp_enabled.isChecked(), 'mode': st.combo_vtp_mode.currentText(),
                    'domain': st.le_vtp_domain.text(), 'password': st.le_vtp_password.text(),
                    'version': st.combo_vtp_version.currentText()}
        s['l2_security'] = {'dhcp_snooping_enabled': st.cb_dhcp_snooping_enabled.isChecked(),
                            'dhcp_snooping_vlans': st.le_dhcp_snooping_vlans.text(),
                            'dai_vlans': st.le_dai_vlans.text()}

        # Routing
        r = settings['routing']
        r['static_routes'] = [
            {'prefix': rt.static_route_table.item(i, 0).text(), 'nexthop': rt.static_route_table.item(i, 1).text(),
             'metric': rt.static_route_table.item(i, 2).text(), 'vrf': rt.static_route_table.item(i, 3).text()} for i in
            range(rt.static_route_table.rowCount()) if rt.static_route_table.item(i, 0)]
        r['ospf'] = {'enabled': rt.cb_ospf_enabled.isChecked(), 'process_id': rt.le_ospf_process_id.text(),
                     'router_id': rt.le_ospf_router_id.text(), 'networks': [
                {'prefix': rt.ospf_network_table.item(i, 0).text(), 'wildcard': rt.ospf_network_table.item(i, 1).text(),
                 'area': rt.ospf_network_table.item(i, 2).text()} for i in range(rt.ospf_network_table.rowCount()) if
                rt.ospf_network_table.item(i, 0)]}
        r['eigrp'] = {'enabled': rt.cb_eigrp_enabled.isChecked(), 'as_number': rt.le_eigrp_as_number.text(),
                      'router_id': rt.le_eigrp_router_id.text(), 'networks': [
                {'prefix': rt.eigrp_network_table.item(i, 0).text(),
                 'wildcard': rt.eigrp_network_table.item(i, 1).text()} for i in range(rt.eigrp_network_table.rowCount())
                if rt.eigrp_network_table.item(i, 0)]}
        r['bgp'] = {'enabled': rt.cb_bgp_enabled.isChecked(), 'as_number': rt.le_bgp_as_number.text(),
                    'router_id': rt.le_bgp_router_id.text(), 'neighbors': [
                {'ip': rt.bgp_neighbor_table.item(i, 0).text(), 'remote_as': rt.bgp_neighbor_table.item(i, 1).text(),
                 'description': rt.bgp_neighbor_table.item(i, 2).text(),
                 'update_source': rt.bgp_neighbor_table.item(i, 3).text(),
                 'rmap_in': rt.bgp_neighbor_table.item(i, 4).text(),
                 'rmap_out': rt.bgp_neighbor_table.item(i, 5).text()} for i in range(rt.bgp_neighbor_table.rowCount())
                if rt.bgp_neighbor_table.item(i, 0)],
                    'networks': [line.strip() for line in rt.te_bgp_networks.toPlainText().splitlines() if
                                 line.strip()]}

        # HA
        ha = settings['ha']
        ha['svl'] = {'enabled': ht.cb_svl_enabled.isChecked(), 'domain': ht.le_svl_domain.text()}
        ha['vpc'] = {'enabled': ht.cb_vpc_enabled.isChecked(), 'domain': ht.le_vpc_domain.text(),
                     'peer_keepalive': ht.le_vpc_peer_keepalive.text()}

        # Security
        sec = settings['security']
        sec['aaa_new_model'] = sect.cb_aaa_new_model.isChecked()
        sec['aaa_auth_login'] = sect.le_aaa_auth_login.text()
        sec['aaa_auth_exec'] = sect.le_aaa_auth_exec.text()
        sec['aaa_groups'] = [
            {'type': sect.aaa_server_table.item(r, 0).text(), 'group_name': sect.aaa_server_table.item(r, 1).text(),
             'servers': [s.strip() for s in sect.aaa_server_table.item(r, 2).text().split(',') if s.strip()]} for r in
            range(sect.aaa_server_table.rowCount()) if sect.aaa_server_table.item(r, 1)]
        sec['local_users'] = [{'username': sect.users_table.item(r, 0).text(), 'privilege': (
            sect.users_table.item(r, 1).text() if sect.users_table.item(r, 1) else '1'),
                               'password': (sect.users_table.item(r, 2).text() if sect.users_table.item(r, 2) else '')}
                              for r in range(sect.users_table.rowCount()) if
                              sect.users_table.item(r, 0) and sect.users_table.item(r, 0).text()]
        sec['line_config'] = {'con_timeout': sect.le_con_exec_timeout.text(),
                              'con_logging_sync': sect.cb_con_logging_sync.isChecked(),
                              'con_auth_aaa': sect.cb_con_auth_aaa.isChecked(),
                              'con_auth_method': sect.le_con_auth_method.text(), 'vty_range': sect.le_vty_range.text(),
                              'vty_timeout': sect.le_vty_exec_timeout.text(),
                              'vty_transport': sect.combo_vty_transport.currentText()}
        sec['snmp'] = {'location': sect.le_snmp_location.text(), 'contact': sect.le_snmp_contact.text(),
                       'communities': [{'community': sect.snmp_community_table.item(r, 0).text(), 'permission': (
                           sect.snmp_community_table.item(r, 1).text() if sect.snmp_community_table.item(r,
                                                                                                         1) else 'RO'),
                                        'acl': (sect.snmp_community_table.item(r,
                                                                               2).text() if sect.snmp_community_table.item(
                                            r, 2) else '')} for r in range(sect.snmp_community_table.rowCount()) if
                                       sect.snmp_community_table.item(r, 0)], 'v3_users': [
                {'username': sect.snmp_v3_user_table.item(r, 0).text(),
                 'group': sect.snmp_v3_user_table.item(r, 1).text(),
                 'auth_proto': sect.snmp_v3_user_table.item(r, 2).text(),
                 'auth_pass': sect.snmp_v3_user_table.item(r, 3).text(),
                 'priv_proto': sect.snmp_v3_user_table.item(r, 4).text(),
                 'priv_pass': sect.snmp_v3_user_table.item(r, 5).text()} for r in
                range(sect.snmp_v3_user_table.rowCount()) if
                sect.snmp_v3_user_table.item(r, 0) and sect.snmp_v3_user_table.item(r, 0).text()]}
        sec['hardening'] = {'no_ip_http': sect.cb_no_ip_http.isChecked(), 'no_cdp': sect.cb_no_cdp.isChecked(),
                            'lldp': sect.cb_lldp.isChecked()}
        # ACLs
        acls = []
        for r in range(at.acl_list_table.rowCount()):
            name_item = at.acl_list_table.item(r, 0)
            if name_item and name_item.text():
                acl_data = {
                    "name": name_item.text(),
                    "type": at.acl_list_table.item(r, 1).text() if at.acl_list_table.item(r, 1) else "",
                    "description": at.acl_list_table.item(r, 2).text() if at.acl_list_table.item(r, 2) else "",
                    "rules": name_item.data(Qt.UserRole) or []
                }
                acls.append(acl_data)
        settings['acls'] = acls

        return {
            "devices": [self.device_list.item(i).text() for i in range(self.device_list.count())],
            "settings": settings
        }

    def _apply_data_to_ui(self, data):
        """불러온 데이터 딕셔너리를 UI의 각 위젯에 적용합니다."""
        self._block_interface_signals(True)
        gt = self.global_tab;
        it = self.interface_tab;
        vt = self.vlan_tab
        st = self.switching_tab;
        rt = self.routing_tab;
        ht = self.ha_tab;
        sect = self.security_tab

        # Device List
        self.device_list.clear()
        self.device_list.addItems(data.get('devices', []))
        settings = data.get('settings', {})

        # Global
        g = settings.get('global', {})
        gt.le_hostname.setText(g.get('hostname', ''))
        gt.cb_service_timestamps.setChecked(g.get('service_timestamps', False))
        gt.cb_service_password_encryption.setChecked(g.get('service_password_encryption', False))
        gt.cb_service_call_home.setChecked(g.get('service_call_home', False))
        gt.le_domain_name.setText(g.get('domain_name', ''))
        gt.dns_table.setRowCount(0)
        for server in g.get('dns_servers', []):
            row = gt.dns_table.rowCount();
            gt.dns_table.insertRow(row)
            gt.dns_table.setItem(row, 0, QTableWidgetItem(server.get('ip')));
            gt.dns_table.setItem(row, 1, QTableWidgetItem(server.get('vrf')))
        gt.combo_timezone.setCurrentText(g.get('timezone', 'KST 9'))
        self._on_timezone_changed(gt.combo_timezone.currentText())
        if gt.combo_timezone.currentText() == "Custom": gt.le_custom_timezone.setText(g.get('timezone', ''))
        summer_time = g.get('summer_time', {});
        gt.cb_summer_time.setChecked(summer_time.get('enabled', False));
        gt.le_summer_time_zone.setText(summer_time.get('zone', ''))
        gt.combo_logging_level.setCurrentText(g.get('logging_level', 'informational (6)'))
        gt.cb_logging_console.setChecked(g.get('logging_console', True));
        gt.cb_logging_buffered.setChecked(g.get('logging_buffered', True))
        gt.le_logging_buffer_size.setText(g.get('logging_buffer_size', '32000'))
        gt.logging_table.setRowCount(0)
        for host in g.get('logging_hosts', []):
            row = gt.logging_table.rowCount();
            gt.logging_table.insertRow(row)
            gt.logging_table.setItem(row, 0, QTableWidgetItem(host.get('ip')));
            gt.logging_table.setItem(row, 1, QTableWidgetItem(host.get('vrf')))
        gt.cb_ntp_authenticate.setChecked(g.get('ntp_authenticate', False));
        gt.le_ntp_master_stratum.setText(g.get('ntp_master_stratum', ''))
        gt.ntp_table.setRowCount(0)
        for server in g.get('ntp_servers', []):
            row = gt.ntp_table.rowCount();
            gt.ntp_table.insertRow(row)
            gt.ntp_table.setItem(row, 0, QTableWidgetItem(server.get('ip')));
            gt.ntp_table.setItem(row, 1, QTableWidgetItem(str(server.get('prefer', False))));
            gt.ntp_table.setItem(row, 2, QTableWidgetItem(server.get('key_id')));
            gt.ntp_table.setItem(row, 3, QTableWidgetItem(server.get('vrf')))
        mgmt = g.get('management', {});
        gt.combo_mgmt_interface.setCurrentText(mgmt.get('interface', 'None'))
        self._on_mgmt_interface_changed(gt.combo_mgmt_interface.currentText())
        gt.le_mgmt_ip.setText(mgmt.get('ip', ''));
        gt.le_mgmt_subnet.setText(mgmt.get('subnet', ''));
        gt.le_mgmt_gateway.setText(mgmt.get('gateway', ''));
        gt.le_mgmt_vrf.setText(mgmt.get('vrf', ''))
        banner = g.get('banner', {});
        gt.cb_enable_banner.setChecked(banner.get('enabled', False));
        gt.te_banner_text.setPlainText(banner.get('text', ''))
        archive = g.get('archive', {});
        gt.cb_archive_config.setChecked(archive.get('enabled', False));
        gt.le_archive_path.setText(archive.get('path', ''));
        gt.le_archive_max_files.setText(archive.get('max_files', ''));
        gt.cb_archive_time_period.setChecked(archive.get('time_period_enabled', False));
        gt.le_archive_time_period.setText(archive.get('time_period', ''))

        # Interfaces
        it.interface_list.clear()
        for if_config in settings.get('interfaces', []):
            self._add_interface_item(if_config.get('name', 'Unknown Interface'))
            last_item_index = it.interface_list.count() - 1
            if last_item_index >= 0:
                it.interface_list.item(last_item_index).setData(Qt.UserRole, if_config)

        # VLANs
        vlans_data = settings.get('vlans', {});
        vt.cb_ip_routing.setChecked(vlans_data.get('enable_routing', False))
        vt.vlan_table.setRowCount(0)
        for vlan_data in vlans_data.get('list', []):
            row = vt.vlan_table.rowCount();
            vt.vlan_table.insertRow(row)
            vlan_id_item = QTableWidgetItem(vlan_data.get('id'));
            vlan_id_item.setData(Qt.UserRole, vlan_data.get('svi', {}))
            vt.vlan_table.setItem(row, 0, vlan_id_item);
            vt.vlan_table.setItem(row, 1, QTableWidgetItem(vlan_data.get('name')));
            vt.vlan_table.setItem(row, 2, QTableWidgetItem(vlan_data.get('description')))

        # Switching
        s = settings.get('switching', {});
        st.combo_stp_mode.setCurrentText(s.get('stp_mode', 'rapid-pvst'));
        st.le_stp_priority.setText(s.get('stp_priority', ''));
        st.cb_stp_portfast_default.setChecked(s.get('stp_portfast_default', False));
        st.cb_stp_bpduguard_default.setChecked(s.get('stp_bpduguard_default', False));
        st.cb_stp_bpdufilter_default.setChecked(s.get('stp_bpdufilter_default', False));
        st.cb_stp_loopguard_default.setChecked(s.get('stp_loopguard_default', False))
        self._update_mst_ui_visibility(st.combo_stp_mode.currentText())
        mst = s.get('mst', {});
        st.le_mst_name.setText(mst.get('name', ''));
        st.le_mst_revision.setText(mst.get('revision', '0'));
        st.mst_instance_table.setRowCount(0)
        for inst in mst.get('instances', []):
            row = st.mst_instance_table.rowCount();
            st.mst_instance_table.insertRow(row);
            st.mst_instance_table.setItem(row, 0, QTableWidgetItem(inst.get('id')));
            st.mst_instance_table.setItem(row, 1, QTableWidgetItem(inst.get('vlans')))
        vtp = s.get('vtp', {});
        st.cb_vtp_enabled.setChecked(vtp.get('enabled', False));
        st.combo_vtp_mode.setCurrentText(vtp.get('mode', 'transparent'));
        st.le_vtp_domain.setText(vtp.get('domain', ''));
        st.le_vtp_password.setText(vtp.get('password', ''));
        st.combo_vtp_version.setCurrentText(vtp.get('version', '2'))
        l2_sec = s.get('l2_security', {});
        st.cb_dhcp_snooping_enabled.setChecked(l2_sec.get('dhcp_snooping_enabled', False));
        st.le_dhcp_snooping_vlans.setText(l2_sec.get('dhcp_snooping_vlans', ''));
        st.le_dai_vlans.setText(l2_sec.get('dai_vlans', ''))

        # Routing
        r = settings.get('routing', {});
        rt.static_route_table.setRowCount(0)
        for route in r.get('static_routes', []):
            row = rt.static_route_table.rowCount();
            rt.static_route_table.insertRow(row);
            rt.static_route_table.setItem(row, 0, QTableWidgetItem(route.get('prefix')));
            rt.static_route_table.setItem(row, 1, QTableWidgetItem(route.get('nexthop')));
            rt.static_route_table.setItem(row, 2, QTableWidgetItem(route.get('metric')));
            rt.static_route_table.setItem(row, 3, QTableWidgetItem(route.get('vrf')))
        ospf = r.get('ospf', {});
        rt.cb_ospf_enabled.setChecked(ospf.get('enabled', False));
        rt.le_ospf_process_id.setText(ospf.get('process_id', '1'));
        rt.le_ospf_router_id.setText(ospf.get('router_id', ''));
        rt.ospf_network_table.setRowCount(0)
        for net in ospf.get('networks', []):
            row = rt.ospf_network_table.rowCount();
            rt.ospf_network_table.insertRow(row);
            rt.ospf_network_table.setItem(row, 0, QTableWidgetItem(net.get('prefix')));
            rt.ospf_network_table.setItem(row, 1, QTableWidgetItem(net.get('wildcard')));
            rt.ospf_network_table.setItem(row, 2, QTableWidgetItem(net.get('area')))
        eigrp = r.get('eigrp', {});
        rt.cb_eigrp_enabled.setChecked(eigrp.get('enabled', False));
        rt.le_eigrp_as_number.setText(eigrp.get('as_number', '100'));
        rt.le_eigrp_router_id.setText(eigrp.get('router_id', ''));
        rt.eigrp_network_table.setRowCount(0)
        for net in eigrp.get('networks', []):
            row = rt.eigrp_network_table.rowCount();
            rt.eigrp_network_table.insertRow(row);
            rt.eigrp_network_table.setItem(row, 0, QTableWidgetItem(net.get('prefix')));
            rt.eigrp_network_table.setItem(row, 1, QTableWidgetItem(net.get('wildcard')))
        bgp = r.get('bgp', {});
        rt.cb_bgp_enabled.setChecked(bgp.get('enabled', False));
        rt.le_bgp_as_number.setText(bgp.get('as_number', '65001'));
        rt.le_bgp_router_id.setText(bgp.get('router_id', ''));
        rt.bgp_neighbor_table.setRowCount(0)
        for n in bgp.get('neighbors', []):
            row = rt.bgp_neighbor_table.rowCount();
            rt.bgp_neighbor_table.insertRow(row);
            rt.bgp_neighbor_table.setItem(row, 0, QTableWidgetItem(n.get('ip')));
            rt.bgp_neighbor_table.setItem(row, 1, QTableWidgetItem(n.get('remote_as')));
            rt.bgp_neighbor_table.setItem(row, 2, QTableWidgetItem(n.get('description')));
            rt.bgp_neighbor_table.setItem(row, 3, QTableWidgetItem(n.get('update_source')));
            rt.bgp_neighbor_table.setItem(row, 4, QTableWidgetItem(n.get('rmap_in')));
            rt.bgp_neighbor_table.setItem(row, 5, QTableWidgetItem(n.get('rmap_out')))
        rt.te_bgp_networks.setPlainText("\n".join(bgp.get('networks', [])))

        # HA
        ha = settings.get('ha', {});
        svl = ha.get('svl', {});
        ht.cb_svl_enabled.setChecked(svl.get('enabled', False));
        ht.le_svl_domain.setText(svl.get('domain', ''))
        vpc = ha.get('vpc', {});
        ht.cb_vpc_enabled.setChecked(vpc.get('enabled', False));
        ht.le_vpc_domain.setText(vpc.get('domain', ''));
        ht.le_vpc_peer_keepalive.setText(vpc.get('peer_keepalive', ''))

        # Security
        sec = settings.get('security', {});
        sect.cb_aaa_new_model.setChecked(sec.get('aaa_new_model', False));
        sect.le_aaa_auth_login.setText(sec.get('aaa_auth_login', ''));
        sect.le_aaa_auth_exec.setText(sec.get('aaa_auth_exec', ''))
        sect.aaa_server_table.setRowCount(0)
        for group in sec.get('aaa_groups', []):
            row = sect.aaa_server_table.rowCount();
            sect.aaa_server_table.insertRow(row);
            sect.aaa_server_table.setItem(row, 0, QTableWidgetItem(group.get('type')));
            sect.aaa_server_table.setItem(row, 1, QTableWidgetItem(group.get('group_name')));
            sect.aaa_server_table.setItem(row, 2, QTableWidgetItem(",".join(group.get('servers', []))))
        sect.users_table.setRowCount(0)
        for user in sec.get('local_users', []):
            row = sect.users_table.rowCount();
            sect.users_table.insertRow(row);
            sect.users_table.setItem(row, 0, QTableWidgetItem(user.get('username')));
            sect.users_table.setItem(row, 1, QTableWidgetItem(user.get('privilege')));
            sect.users_table.setItem(row, 2, QTableWidgetItem(user.get('password')))
        line = sec.get('line_config', {});
        sect.le_con_exec_timeout.setText(line.get('con_timeout', '15 0'));
        sect.cb_con_logging_sync.setChecked(line.get('con_logging_sync', True));
        sect.cb_con_auth_aaa.setChecked(line.get('con_auth_aaa', False));
        sect.le_con_auth_method.setText(line.get('con_auth_method', 'default'));
        sect.le_vty_range.setText(line.get('vty_range', '0 4'));
        sect.le_vty_exec_timeout.setText(line.get('vty_timeout', '15 0'));
        sect.combo_vty_transport.setCurrentText(line.get('vty_transport', 'ssh'))
        snmp = sec.get('snmp', {});
        sect.le_snmp_location.setText(snmp.get('location', ''));
        sect.le_snmp_contact.setText(snmp.get('contact', ''));
        sect.snmp_community_table.setRowCount(0)
        for comm in snmp.get('communities', []):
            row = sect.snmp_community_table.rowCount();
            sect.snmp_community_table.insertRow(row);
            sect.snmp_community_table.setItem(row, 0, QTableWidgetItem(comm.get('community')));
            sect.snmp_community_table.setItem(row, 1, QTableWidgetItem(comm.get('permission')));
            sect.snmp_community_table.setItem(row, 2, QTableWidgetItem(comm.get('acl')))
        sect.snmp_v3_user_table.setRowCount(0)
        for user in snmp.get('v3_users', []):
            row = sect.snmp_v3_user_table.rowCount();
            sect.snmp_v3_user_table.insertRow(row);
            sect.snmp_v3_user_table.setItem(row, 0, QTableWidgetItem(user.get('username')));
            sect.snmp_v3_user_table.setItem(row, 1, QTableWidgetItem(user.get('group')));
            sect.snmp_v3_user_table.setItem(row, 2, QTableWidgetItem(user.get('auth_proto')));
            sect.snmp_v3_user_table.setItem(row, 3, QTableWidgetItem(user.get('auth_pass')));
            sect.snmp_v3_user_table.setItem(row, 4, QTableWidgetItem(user.get('priv_proto')));
            sect.snmp_v3_user_table.setItem(row, 5, QTableWidgetItem(user.get('priv_pass')))
        hardening = sec.get('hardening', {});

        sect.cb_no_ip_http.setChecked(hardening.get('no_ip_http', True));
        sect.cb_no_cdp.setChecked(hardening.get('no_cdp', False));
        sect.cb_lldp.setChecked(hardening.get('lldp', True))

        it.config_area_widget.setVisible(False)
        self._block_interface_signals(False)
        self._update_ui_for_os()