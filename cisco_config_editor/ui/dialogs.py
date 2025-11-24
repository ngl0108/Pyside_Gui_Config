# cisco_config_manager/ui/dialogs.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QCheckBox,
    QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression


class InterfaceDialog(QDialog):
    """인터페이스 추가/편집 다이얼로그"""
    
    def __init__(self, parent=None, interface_data=None):
        super().__init__(parent)
        self.interface_data = interface_data or {}
        self.setWindowTitle("인터페이스 설정" if interface_data else "인터페이스 추가")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 인터페이스 기본 정보
        form = QFormLayout()
        
        self.le_name = QLineEdit()
        self.le_name.setPlaceholderText("예: GigabitEthernet0/1")
        
        self.le_description = QLineEdit()
        self.le_description.setPlaceholderText("인터페이스 설명")
        
        self.cb_shutdown = QCheckBox("Shutdown 상태")
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["L2 Access", "L2 Trunk", "L3 Routed", "Port-Channel Member"])
        
        form.addRow("인터페이스 이름:", self.le_name)
        form.addRow("설명:", self.le_description)
        form.addRow("상태:", self.cb_shutdown)
        form.addRow("모드:", self.combo_mode)
        
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _load_data(self):
        """기존 데이터 로드"""
        if self.interface_data:
            self.le_name.setText(self.interface_data.get('name', ''))
            self.le_description.setText(self.interface_data.get('description', ''))
            self.cb_shutdown.setChecked(self.interface_data.get('shutdown', False))
            
            mode_index = self.combo_mode.findText(self.interface_data.get('mode', 'L2 Access'))
            if mode_index >= 0:
                self.combo_mode.setCurrentIndex(mode_index)
                
    def get_data(self):
        """입력된 데이터 반환"""
        return {
            'name': self.le_name.text().strip(),
            'description': self.le_description.text().strip(),
            'shutdown': self.cb_shutdown.isChecked(),
            'mode': self.combo_mode.currentText()
        }


class VlanDialog(QDialog):
    """VLAN 추가/편집 다이얼로그"""
    
    def __init__(self, parent=None, vlan_data=None):
        super().__init__(parent)
        self.vlan_data = vlan_data or {}
        self.setWindowTitle("VLAN 편집" if vlan_data else "VLAN 추가")
        self.setModal(True)
        self.setMinimumWidth(350)
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # VLAN ID
        self.le_vlan_id = QLineEdit()
        self.le_vlan_id.setPlaceholderText("2-4094")
        validator = QRegularExpressionValidator(QRegularExpression("^[2-9]|[1-9][0-9]{1,2}|[1-3][0-9]{3}|40[0-8][0-9]|409[0-4]$"))
        self.le_vlan_id.setValidator(validator)
        
        # VLAN 이름
        self.le_vlan_name = QLineEdit()
        self.le_vlan_name.setPlaceholderText("예: Management_VLAN")
        self.le_vlan_name.setMaxLength(32)  # Cisco VLAN 이름 제한
        
        # VLAN 설명
        self.le_vlan_desc = QLineEdit()
        self.le_vlan_desc.setPlaceholderText("VLAN 설명 (선택사항)")
        
        form.addRow("VLAN ID:", self.le_vlan_id)
        form.addRow("VLAN 이름:", self.le_vlan_name)
        form.addRow("설명:", self.le_vlan_desc)
        
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _load_data(self):
        """기존 데이터 로드"""
        if self.vlan_data:
            self.le_vlan_id.setText(str(self.vlan_data.get('id', '')))
            self.le_vlan_name.setText(self.vlan_data.get('name', ''))
            self.le_vlan_desc.setText(self.vlan_data.get('description', ''))
            # 편집 모드에서는 VLAN ID 변경 불가
            if self.vlan_data.get('id'):
                self.le_vlan_id.setReadOnly(True)
                
    def _validate_and_accept(self):
        """유효성 검사 후 승인"""
        vlan_id = self.le_vlan_id.text().strip()
        
        if not vlan_id:
            QMessageBox.warning(self, "경고", "VLAN ID를 입력하세요.")
            return
            
        try:
            vlan_id_int = int(vlan_id)
            if vlan_id_int < 2 or vlan_id_int > 4094:
                QMessageBox.warning(self, "경고", "VLAN ID는 2-4094 범위여야 합니다.")
                return
        except ValueError:
            QMessageBox.warning(self, "경고", "올바른 VLAN ID를 입력하세요.")
            return
            
        if not self.le_vlan_name.text().strip():
            self.le_vlan_name.setText(f"VLAN{vlan_id}")
            
        self.accept()
        
    def get_data(self):
        """입력된 데이터 반환"""
        return {
            'id': self.le_vlan_id.text().strip(),
            'name': self.le_vlan_name.text().strip() or f"VLAN{self.le_vlan_id.text().strip()}",
            'description': self.le_vlan_desc.text().strip()
        }


class AclDialog(QDialog):
    """ACL 추가/편집 다이얼로그"""
    
    def __init__(self, parent=None, acl_data=None):
        super().__init__(parent)
        self.acl_data = acl_data or {}
        self.setWindowTitle("ACL 편집" if acl_data else "ACL 추가")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # ACL 이름/번호
        self.le_acl_name = QLineEdit()
        self.le_acl_name.setPlaceholderText("ACL 이름 또는 번호 (1-199, 1300-2699)")
        
        # ACL 타입
        self.combo_acl_type = QComboBox()
        self.combo_acl_type.addItems(["Standard", "Extended", "Named Standard", "Named Extended"])
        
        # ACL 설명
        self.le_acl_desc = QLineEdit()
        self.le_acl_desc.setPlaceholderText("ACL 설명 (선택사항)")
        
        form.addRow("ACL 이름/번호:", self.le_acl_name)
        form.addRow("ACL 타입:", self.combo_acl_type)
        form.addRow("설명:", self.le_acl_desc)
        
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _load_data(self):
        """기존 데이터 로드"""
        if self.acl_data:
            self.le_acl_name.setText(self.acl_data.get('name', ''))
            
            type_index = self.combo_acl_type.findText(self.acl_data.get('type', 'Extended'))
            if type_index >= 0:
                self.combo_acl_type.setCurrentIndex(type_index)
                
            self.le_acl_desc.setText(self.acl_data.get('description', ''))
            
    def _validate_and_accept(self):
        """유효성 검사 후 승인"""
        acl_name = self.le_acl_name.text().strip()
        
        if not acl_name:
            QMessageBox.warning(self, "경고", "ACL 이름 또는 번호를 입력하세요.")
            return
            
        # 숫자인 경우 범위 확인
        if acl_name.isdigit():
            acl_num = int(acl_name)
            acl_type = self.combo_acl_type.currentText()
            
            if "Standard" in acl_type:
                if not (1 <= acl_num <= 99 or 1300 <= acl_num <= 1999):
                    QMessageBox.warning(self, "경고", 
                        "Standard ACL 번호는 1-99 또는 1300-1999 범위여야 합니다.")
                    return
            elif "Extended" in acl_type:
                if not (100 <= acl_num <= 199 or 2000 <= acl_num <= 2699):
                    QMessageBox.warning(self, "경고", 
                        "Extended ACL 번호는 100-199 또는 2000-2699 범위여야 합니다.")
                    return
                    
        self.accept()
        
    def get_data(self):
        """입력된 데이터 반환"""
        return {
            'name': self.le_acl_name.text().strip(),
            'type': self.combo_acl_type.currentText(),
            'description': self.le_acl_desc.text().strip()
        }


class AceDialog(QDialog):
    """ACL Entry (ACE) 추가/편집 다이얼로그"""
    
    def __init__(self, parent=None, ace_data=None, acl_type="Extended"):
        super().__init__(parent)
        self.ace_data = ace_data or {}
        self.acl_type = acl_type
        self.setWindowTitle("ACE 편집" if ace_data else "ACE 추가")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Sequence Number
        self.spin_seq = QSpinBox()
        self.spin_seq.setRange(1, 2147483647)
        self.spin_seq.setValue(10)
        
        # Action
        self.combo_action = QComboBox()
        self.combo_action.addItems(["permit", "deny"])
        
        # Protocol (Extended ACL만)
        self.combo_protocol = QComboBox()
        self.combo_protocol.addItems(["ip", "tcp", "udp", "icmp", "eigrp", "ospf", "ahp", "esp", "gre"])
        
        # Source IP
        self.le_src_ip = QLineEdit()
        self.le_src_ip.setPlaceholderText("예: 192.168.1.0/24 또는 any 또는 host 192.168.1.1")
        
        # Destination IP (Extended ACL만)
        self.le_dst_ip = QLineEdit()
        self.le_dst_ip.setPlaceholderText("예: 10.0.0.0/8 또는 any 또는 host 10.1.1.1")
        
        # Source Port (TCP/UDP만)
        self.le_src_port = QLineEdit()
        self.le_src_port.setPlaceholderText("예: eq 80 또는 range 1024 65535")
        
        # Destination Port (TCP/UDP만)
        self.le_dst_port = QLineEdit()
        self.le_dst_port.setPlaceholderText("예: eq 443 또는 gt 1023")
        
        # Options
        self.le_options = QLineEdit()
        self.le_options.setPlaceholderText("추가 옵션 (예: established, log)")
        
        form.addRow("Sequence:", self.spin_seq)
        form.addRow("Action:", self.combo_action)
        
        if "Extended" in self.acl_type:
            form.addRow("Protocol:", self.combo_protocol)
            form.addRow("Source IP:", self.le_src_ip)
            form.addRow("Destination IP:", self.le_dst_ip)
            form.addRow("Source Port:", self.le_src_port)
            form.addRow("Dest Port:", self.le_dst_port)
            form.addRow("Options:", self.le_options)
            
            # 프로토콜 변경 시 포트 필드 활성화/비활성화
            self.combo_protocol.currentTextChanged.connect(self._on_protocol_changed)
        else:
            form.addRow("Source IP:", self.le_src_ip)
            
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # 초기 상태 설정
        if "Extended" in self.acl_type:
            self._on_protocol_changed(self.combo_protocol.currentText())
            
    def _on_protocol_changed(self, protocol):
        """프로토콜 변경 시 포트 필드 활성화/비활성화"""
        port_protocols = ["tcp", "udp"]
        enable_ports = protocol.lower() in port_protocols
        self.le_src_port.setEnabled(enable_ports)
        self.le_dst_port.setEnabled(enable_ports)
        
    def _load_data(self):
        """기존 데이터 로드"""
        if self.ace_data:
            self.spin_seq.setValue(int(self.ace_data.get('seq', 10)))
            
            action_index = self.combo_action.findText(self.ace_data.get('action', 'permit'))
            if action_index >= 0:
                self.combo_action.setCurrentIndex(action_index)
                
            if "Extended" in self.acl_type:
                protocol_index = self.combo_protocol.findText(self.ace_data.get('protocol', 'ip'))
                if protocol_index >= 0:
                    self.combo_protocol.setCurrentIndex(protocol_index)
                    
                self.le_dst_ip.setText(self.ace_data.get('dst_ip', ''))
                self.le_src_port.setText(self.ace_data.get('src_port', ''))
                self.le_dst_port.setText(self.ace_data.get('dst_port', ''))
                self.le_options.setText(self.ace_data.get('options', ''))
                
            self.le_src_ip.setText(self.ace_data.get('src_ip', ''))
            
    def get_data(self):
        """입력된 데이터 반환"""
        data = {
            'seq': self.spin_seq.value(),
            'action': self.combo_action.currentText(),
            'src_ip': self.le_src_ip.text().strip()
        }
        
        if "Extended" in self.acl_type:
            data.update({
                'protocol': self.combo_protocol.currentText(),
                'dst_ip': self.le_dst_ip.text().strip(),
                'src_port': self.le_src_port.text().strip(),
                'dst_port': self.le_dst_port.text().strip(),
                'options': self.le_options.text().strip()
            })
            
        return data


class StaticRouteDialog(QDialog):
    """정적 경로 추가/편집 다이얼로그"""
    
    def __init__(self, parent=None, route_data=None):
        super().__init__(parent)
        self.route_data = route_data or {}
        self.setWindowTitle("경로 편집" if route_data else "정적 경로 추가")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Destination Network
        self.le_network = QLineEdit()
        self.le_network.setPlaceholderText("예: 192.168.1.0")
        
        # Subnet Mask
        self.le_mask = QLineEdit()
        self.le_mask.setPlaceholderText("예: 255.255.255.0")
        
        # Next Hop / Interface
        self.le_next_hop = QLineEdit()
        self.le_next_hop.setPlaceholderText("예: 10.0.0.1 또는 GigabitEthernet0/1")
        
        # Metric
        self.spin_metric = QSpinBox()
        self.spin_metric.setRange(1, 255)
        self.spin_metric.setValue(1)
        
        # VRF
        self.le_vrf = QLineEdit()
        self.le_vrf.setPlaceholderText("VRF 이름 (선택사항)")
        
        form.addRow("목적지 네트워크:", self.le_network)
        form.addRow("서브넷 마스크:", self.le_mask)
        form.addRow("Next-Hop/Interface:", self.le_next_hop)
        form.addRow("Metric:", self.spin_metric)
        form.addRow("VRF:", self.le_vrf)
        
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _load_data(self):
        """기존 데이터 로드"""
        if self.route_data:
            self.le_network.setText(self.route_data.get('network', ''))
            self.le_mask.setText(self.route_data.get('mask', ''))
            self.le_next_hop.setText(self.route_data.get('next_hop', ''))
            self.spin_metric.setValue(int(self.route_data.get('metric', 1)))
            self.le_vrf.setText(self.route_data.get('vrf', ''))
            
    def _validate_and_accept(self):
        """유효성 검사 후 승인"""
        if not self.le_network.text().strip():
            QMessageBox.warning(self, "경고", "목적지 네트워크를 입력하세요.")
            return
            
        if not self.le_mask.text().strip():
            QMessageBox.warning(self, "경고", "서브넷 마스크를 입력하세요.")
            return
            
        if not self.le_next_hop.text().strip():
            QMessageBox.warning(self, "경고", "Next-Hop 또는 Interface를 입력하세요.")
            return
            
        self.accept()
        
    def get_data(self):
        """입력된 데이터 반환"""
        return {
            'network': self.le_network.text().strip(),
            'mask': self.le_mask.text().strip(),
            'next_hop': self.le_next_hop.text().strip(),
            'metric': str(self.spin_metric.value()),
            'vrf': self.le_vrf.text().strip()
        }


class DnsServerDialog(QDialog):
    """DNS 서버 추가 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DNS 서버 추가")
        self.setModal(True)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.le_dns_ip = QLineEdit()
        self.le_dns_ip.setPlaceholderText("예: 8.8.8.8")
        
        self.le_vrf = QLineEdit()
        self.le_vrf.setPlaceholderText("VRF 이름 (선택사항)")
        
        form.addRow("DNS 서버 IP:", self.le_dns_ip)
        form.addRow("VRF:", self.le_vrf)
        
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _validate_and_accept(self):
        """IP 주소 유효성 검사"""
        ip = self.le_dns_ip.text().strip()
        if not ip:
            QMessageBox.warning(self, "경고", "DNS 서버 IP를 입력하세요.")
            return
            
        # 간단한 IP 주소 유효성 검사
        parts = ip.split('.')
        if len(parts) != 4:
            QMessageBox.warning(self, "경고", "올바른 IP 주소를 입력하세요.")
            return
            
        try:
            for part in parts:
                if not 0 <= int(part) <= 255:
                    QMessageBox.warning(self, "경고", "올바른 IP 주소를 입력하세요.")
                    return
        except ValueError:
            QMessageBox.warning(self, "경고", "올바른 IP 주소를 입력하세요.")
            return
            
        self.accept()
        
    def get_data(self):
        """입력된 데이터 반환"""
        return {
            'ip': self.le_dns_ip.text().strip(),
            'vrf': self.le_vrf.text().strip()
        }


class NtpServerDialog(QDialog):
    """NTP 서버 추가 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NTP 서버 추가")
        self.setModal(True)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.le_ntp_ip = QLineEdit()
        self.le_ntp_ip.setPlaceholderText("예: 192.168.1.100 또는 time.google.com")
        
        self.cb_prefer = QCheckBox("Prefer")
        
        self.le_key_id = QLineEdit()
        self.le_key_id.setPlaceholderText("인증 키 ID (선택사항)")
        
        self.le_vrf = QLineEdit()
        self.le_vrf.setPlaceholderText("VRF 이름 (선택사항)")
        
        form.addRow("NTP 서버:", self.le_ntp_ip)
        form.addRow("우선 서버:", self.cb_prefer)
        form.addRow("Key ID:", self.le_key_id)
        form.addRow("VRF:", self.le_vrf)
        
        layout.addLayout(form)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _validate_and_accept(self):
        """입력 유효성 검사"""
        if not self.le_ntp_ip.text().strip():
            QMessageBox.warning(self, "경고", "NTP 서버 주소를 입력하세요.")
            return
        self.accept()
        
    def get_data(self):
        """입력된 데이터 반환"""
        return {
            'server': self.le_ntp_ip.text().strip(),
            'prefer': self.cb_prefer.isChecked(),
            'key_id': self.le_key_id.text().strip(),
            'vrf': self.le_vrf.text().strip()
        }