# cisco_config_editor/command_generator.py
from typing import List, Dict, Any


class CiscoCommandGenerator:
    """Cisco 명령어 생성기 - 향상된 버전"""

    def __init__(self):
        self.os_type = "IOS"

    def set_os_type(self, os_type: str):
        """OS 타입 설정"""
        self.os_type = os_type

    def generate_commands(self, original_config: Dict, modified_config: Dict) -> List[str]:
        """변경사항을 Cisco 명령어로 변환 - 신규 구성 지원 개선"""
        commands = []

        # 구성 모드 진입
        commands.append("configure terminal")

        # 원본 구성이 거의 비어있는 경우 (신규 구성)
        if not original_config or self._is_blank_config(original_config):
            # 전체 구성을 생성
            commands.extend(self._generate_complete_config_commands(modified_config))
        else:
            # 변경사항만 생성
            commands.extend(self._generate_diff_commands(original_config, modified_config))

        commands.append("end")
        commands.append("write memory")
        return commands

    def _is_blank_config(self, config: Dict) -> bool:
        """구성이 비어있는지 확인"""
        if not config:
            return True

        # 인터페이스, VLAN 등 주요 설정이 없는지 확인
        interfaces = config.get('interfaces', [])
        vlans = config.get('vlans', {}).get('list', [])
        global_settings = config.get('global', {})

        return (len(interfaces) == 0 and
                len(vlans) == 0 and
                not global_settings.get('hostname'))

    def _generate_complete_config_commands(self, config: Dict) -> List[str]:
        """전체 구성 명령어 생성 (신규 장비용)"""
        commands = []

        # 글로벌 설정
        commands.extend(self._generate_global_commands(config.get('global', {})))

        # VLAN 설정
        commands.extend(self._generate_vlan_commands([], config.get('vlans', {}).get('list', [])))

        # 인터페이스 설정
        commands.extend(self._generate_interface_commands([], config.get('interfaces', [])))

        # 라우팅 설정
        commands.extend(self._generate_routing_commands({}, config))

        return commands

    def _generate_diff_commands(self, original: Dict, modified: Dict) -> List[str]:
        """변경사항만 명령어 생성 (기존 장비용)"""
        commands = []

        # 호스트명 변경
        commands.extend(self._generate_hostname_commands(original, modified))

        # 인터페이스 명령어
        commands.extend(self._generate_interface_commands(
            original.get('interfaces', []),
            modified.get('interfaces', [])
        ))

        # VLAN 명령어
        commands.extend(self._generate_vlan_commands(
            original.get('vlans', {}).get('list', []),
            modified.get('vlans', {}).get('list', [])
        ))

        # 라우팅 명령어
        commands.extend(self._generate_routing_commands(original, modified))

        return commands

    def _generate_global_commands(self, global_config: Dict) -> List[str]:
        """글로벌 설정 명령어 생성"""
        commands = []

        # 호스트명
        if global_config.get('hostname'):
            commands.append(f"hostname {global_config['hostname']}")

        # 도메인명
        if global_config.get('domain_name'):
            commands.append(f"ip domain-name {global_config['domain_name']}")

        # 서비스 설정
        if global_config.get('service_password_encryption'):
            commands.append("service password-encryption")

        if global_config.get('service_timestamps'):
            commands.append("service timestamps debug datetime msec")
            commands.append("service timestamps log datetime msec")

        return commands

    def _generate_hostname_commands(self, original: Dict, modified: Dict) -> List[str]:
        """호스트명 관련 명령어 생성"""
        commands = []

        orig_global = original.get('global', {})
        mod_global = modified.get('global', {})

        orig_hostname = orig_global.get('hostname', '')
        mod_hostname = mod_global.get('hostname', '')

        if orig_hostname != mod_hostname and mod_hostname:
            commands.append(f"hostname {mod_hostname}")

        return commands

    def _generate_interface_commands(self, orig_interfaces: List, mod_interfaces: List) -> List[str]:
        """인터페이스 관련 명령어 생성"""
        commands = []

        orig_iface_map = {iface['name']: iface for iface in orig_interfaces}
        mod_iface_map = {iface['name']: iface for iface in mod_interfaces}

        # 모든 인터페이스 처리
        all_interfaces = set(orig_iface_map.keys()) | set(mod_iface_map.keys())

        for iface_name in all_interfaces:
            orig_iface = orig_iface_map.get(iface_name, {})
            mod_iface = mod_iface_map.get(iface_name, {})

            # 인터페이스 진입
            commands.append(f"interface {iface_name}")

            # 설명 변경
            if orig_iface.get('description') != mod_iface.get('description'):
                if mod_iface.get('description'):
                    commands.append(f" description {mod_iface['description']}")
                else:
                    commands.append(" no description")

            # shutdown 상태 변경
            if orig_iface.get('shutdown') != mod_iface.get('shutdown'):
                if mod_iface.get('shutdown'):
                    commands.append(" shutdown")
                else:
                    commands.append(" no shutdown")

            # 인터페이스 모드 변경
            if orig_iface.get('mode') != mod_iface.get('mode'):
                commands.extend(self._generate_interface_mode_commands(orig_iface, mod_iface))

            # VLAN 설정 변경
            if orig_iface.get('access', {}).get('vlan') != mod_iface.get('access', {}).get('vlan'):
                vlan = mod_iface.get('access', {}).get('vlan')
                if vlan:
                    commands.append(f" switchport access vlan {vlan}")

            # IP 주소 변경
            if orig_iface.get('routed', {}).get('ip') != mod_iface.get('routed', {}).get('ip'):
                ip = mod_iface.get('routed', {}).get('ip')
                if ip:
                    commands.append(f" ip address {ip}")
                else:
                    commands.append(" no ip address")

            # STP 설정 변경
            if orig_iface.get('stp', {}).get('portfast') != mod_iface.get('stp', {}).get('portfast'):
                if mod_iface.get('stp', {}).get('portfast'):
                    commands.append(" spanning-tree portfast")
                else:
                    commands.append(" no spanning-tree portfast")

            # Port Security 설정 변경
            if orig_iface.get('port_security', {}).get('enabled') != mod_iface.get('port_security', {}).get('enabled'):
                if mod_iface.get('port_security', {}).get('enabled'):
                    max_mac = mod_iface.get('port_security', {}).get('max_mac', '1')
                    violation = mod_iface.get('port_security', {}).get('violation', 'shutdown')
                    commands.append(" switchport port-security")
                    commands.append(f" switchport port-security maximum {max_mac}")
                    commands.append(f" switchport port-security violation {violation}")
                else:
                    commands.append(" no switchport port-security")

            commands.append("exit")

        return commands

    def _generate_interface_mode_commands(self, orig_iface: Dict, mod_iface: Dict) -> List[str]:
        """인터페이스 모드 변경 명령어 생성"""
        commands = []
        orig_mode = orig_iface.get('mode', '')
        mod_mode = mod_iface.get('mode', '')

        if orig_mode != mod_mode:
            if mod_mode == 'L2 Access':
                commands.append(" switchport mode access")
                commands.append(" no switchport trunk native vlan")
                commands.append(" no switchport trunk allowed vlan")
            elif mod_mode == 'L2 Trunk':
                commands.append(" switchport mode trunk")
                native_vlan = mod_iface.get('trunk', {}).get('native_vlan', '1')
                commands.append(f" switchport trunk native vlan {native_vlan}")
            elif mod_mode == 'L3 Routed':
                commands.append(" no switchport")

        return commands

    def _generate_vlan_commands(self, orig_vlans: List, mod_vlans: List) -> List[str]:
        """VLAN 관련 명령어 생성"""
        commands = []

        orig_vlan_map = {vlan['id']: vlan for vlan in orig_vlans}
        mod_vlan_map = {vlan['id']: vlan for vlan in mod_vlans}

        # 추가된 VLAN
        for vlan_id in set(mod_vlan_map.keys()) - set(orig_vlan_map.keys()):
            vlan = mod_vlan_map[vlan_id]
            commands.append(f"vlan {vlan_id}")
            if vlan.get('name') and vlan['name'] != f'VLAN{vlan_id}':
                commands.append(f" name {vlan['name']}")
            commands.append("exit")

        # 수정된 VLAN
        for vlan_id in set(orig_vlan_map.keys()) & set(mod_vlan_map.keys()):
            orig_vlan = orig_vlan_map[vlan_id]
            mod_vlan = mod_vlan_map[vlan_id]

            if orig_vlan.get('name') != mod_vlan.get('name'):
                commands.append(f"vlan {vlan_id}")
                commands.append(f" name {mod_vlan['name']}")
                commands.append("exit")

        # 삭제된 VLAN
        for vlan_id in set(orig_vlan_map.keys()) - set(mod_vlan_map.keys()):
            commands.append(f"no vlan {vlan_id}")

        return commands

    def _generate_routing_commands(self, original: Dict, modified: Dict) -> List[str]:
        """라우팅 관련 명령어 생성"""
        commands = []

        # 정적 경로
        orig_routes = original.get('routing', {}).get('static_routes', [])
        mod_routes = modified.get('routing', {}).get('static_routes', [])

        # 삭제된 정적 경로
        for route in orig_routes:
            if route not in mod_routes:
                commands.append(f"no ip route {route.get('prefix')} {route.get('nexthop')}")

        # 추가된 정적 경로
        for route in mod_routes:
            if route not in orig_routes:
                commands.append(f"ip route {route.get('prefix')} {route.get('nexthop')}")

        return commands

    def generate_interface_config(self, interface_config: Dict) -> List[str]:
        """단일 인터페이스 구성 명령어 생성"""
        commands = [f"interface {interface_config['name']}"]

        if interface_config.get('description'):
            commands.append(f" description {interface_config['description']}")

        if interface_config.get('shutdown'):
            commands.append(" shutdown")
        else:
            commands.append(" no shutdown")

        # 모드별 설정
        mode = interface_config.get('mode', 'L2 Access')
        if mode == 'L2 Access':
            commands.append(" switchport mode access")
            vlan = interface_config.get('access', {}).get('vlan')
            if vlan:
                commands.append(f" switchport access vlan {vlan}")
        elif mode == 'L2 Trunk':
            commands.append(" switchport mode trunk")
            native_vlan = interface_config.get('trunk', {}).get('native_vlan', '1')
            commands.append(f" switchport trunk native vlan {native_vlan}")
        elif mode == 'L3 Routed':
            commands.append(" no switchport")
            ip = interface_config.get('routed', {}).get('ip')
            if ip:
                commands.append(f" ip address {ip}")

        commands.append("exit")
        return commands

    def generate_vlan_config(self, vlan_config: Dict) -> List[str]:
        """단일 VLAN 구성 명령어 생성"""
        commands = [f"vlan {vlan_config['id']}"]

        if vlan_config.get('name'):
            commands.append(f" name {vlan_config['name']}")

        commands.append("exit")
        return commands