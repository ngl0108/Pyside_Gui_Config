# cisco_config_manager/core/cli_analyzer.py
import re
from typing import Dict, List, Any


class CLIAnalyzer:
    """Show run CLI 출력 분석기 - 향상된 버전"""

    @staticmethod
    def analyze_show_run(cli_output: str) -> Dict[str, Any]:
        """show run 출력을 분석하여 구조화된 데이터 반환"""
        analysis = {
            'interfaces': [],
            'vlans': [],
            'version': '',
            'model': '',
            'hostname': '',
            'os_type': 'IOS',
            'management_ip': '',
            'static_routes': [],
            'ospf_config': {},
            'bgp_config': {}
        }

        lines = cli_output.split('\n')

        # OS 타입 감지
        analysis['os_type'] = CLIAnalyzer._detect_os_type(lines)

        # 호스트명 추출
        analysis['hostname'] = CLIAnalyzer._extract_hostname(lines)

        # 인터페이스 분석
        interface_blocks = CLIAnalyzer._extract_interface_blocks(lines)
        analysis['interfaces'] = CLIAnalyzer._parse_interfaces(interface_blocks)

        # VLAN 분석
        analysis['vlans'] = CLIAnalyzer._parse_vlans(lines)

        # 라우팅 정보 분석
        analysis['static_routes'] = CLIAnalyzer._parse_static_routes(lines)
        analysis['ospf_config'] = CLIAnalyzer._parse_ospf_config(lines)
        analysis['bgp_config'] = CLIAnalyzer._parse_bgp_config(lines)

        # 버전 정보 추출
        analysis.update(CLIAnalyzer._parse_version_info(lines))

        return analysis

    @staticmethod
    def _detect_os_type(lines: List[str]) -> str:
        """OS 타입 감지"""
        for line in lines:
            if 'IOS-XE' in line:
                return 'IOS-XE'
            elif 'NX-OS' in line:
                return 'NX-OS'
            elif 'Adaptive Security Appliance' in line:
                return 'ASA'
            elif 'IOS' in line:
                return 'IOS'
        return 'IOS'

    @staticmethod
    def _extract_hostname(lines: List[str]) -> str:
        """호스트명 추출"""
        for line in lines:
            if line.startswith('hostname '):
                return line.replace('hostname ', '').strip()
        return 'Unknown'

    @staticmethod
    def _extract_interface_blocks(lines: List[str]) -> List[List[str]]:
        """인터페이스 블록 추출"""
        blocks = []
        current_block = []
        in_interface = False

        for line in lines:
            stripped_line = line.strip()

            # 인터페이스 시작
            if re.match(r'^interface\s+\S+', stripped_line):
                if current_block:
                    blocks.append(current_block)
                current_block = [stripped_line]
                in_interface = True
            # 인터페이스 블록 내부
            elif in_interface and stripped_line and not stripped_line.startswith('!'):
                current_block.append(stripped_line)
            # 인터페이스 블록 종료
            elif in_interface and (stripped_line.startswith('!') or not stripped_line):
                in_interface = False
                if current_block:
                    blocks.append(current_block)
                    current_block = []

        if current_block:
            blocks.append(current_block)

        return blocks

    @staticmethod
    def _parse_interfaces(blocks: List[List[str]]) -> List[Dict]:
        """인터페이스 블록 파싱 - 향상된 버전"""
        interfaces = []

        for block in blocks:
            if not block:
                continue

            interface = {
                'name': block[0].replace('interface ', '').strip(),
                'description': '',
                'shutdown': True,  # 기본적으로 shutdown으로 가정
                'vlan': '',
                'mode': 'access',
                'ip_address': '',
                'subnet_mask': '',
                'type': 'physical',
                'channel_group': '',
                'speed': '',
                'duplex': '',
                'mtu': ''
            }

            for line in block:
                line_lower = line.lower()

                # 설명
                if 'description' in line:
                    interface['description'] = line.replace('description', '').strip()

                # shutdown 상태
                if 'shutdown' in line_lower and 'no shutdown' not in line_lower:
                    interface['shutdown'] = True
                elif 'no shutdown' in line_lower:
                    interface['shutdown'] = False

                # VLAN 설정
                if 'switchport access vlan' in line_lower:
                    interface['vlan'] = line.split()[-1]
                    interface['mode'] = 'access'
                elif 'switchport mode trunk' in line_lower:
                    interface['mode'] = 'trunk'
                elif 'switchport trunk native vlan' in line_lower:
                    interface['vlan'] = line.split()[-1]  # native vlan

                # IP 주소
                if 'ip address' in line_lower and 'dhcp' not in line_lower:
                    ip_match = re.search(r'ip address (\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        interface['ip_address'] = ip_match.group(1)
                        interface['subnet_mask'] = ip_match.group(2)
                        interface['mode'] = 'routed'

                # Port-Channel
                if 'channel-group' in line_lower:
                    match = re.search(r'channel-group\s+(\d+)', line)
                    if match:
                        interface['channel_group'] = match.group(1)
                        interface['type'] = 'port-channel-member'

                # 속도/듀플렉스
                if 'speed' in line_lower:
                    interface['speed'] = line.split()[-1]
                if 'duplex' in line_lower:
                    interface['duplex'] = line.split()[-1]

                # MTU
                if 'mtu' in line_lower:
                    mtu_match = re.search(r'mtu\s+(\d+)', line)
                    if mtu_match:
                        interface['mtu'] = mtu_match.group(1)

            # Port-Channel 인터페이스 감지
            if 'port-channel' in interface['name'].lower():
                interface['type'] = 'port-channel'

            interfaces.append(interface)

        return interfaces

    @staticmethod
    def _parse_vlans(lines: List[str]) -> List[Dict]:
        """VLAN 정보 파싱 - 향상된 버전"""
        vlans = []
        in_vlan_section = False

        for line in lines:
            stripped_line = line.strip()

            # VLAN 섹션 시작
            if 'vlan ' in stripped_line and 'name' not in stripped_line and 'access' not in stripped_line:
                parts = stripped_line.split()
                if len(parts) >= 2 and parts[0] == 'vlan':
                    vlan_id = parts[1]
                    # 이미 존재하는 VLAN인지 확인
                    existing_vlan = next((v for v in vlans if v['id'] == vlan_id), None)
                    if not existing_vlan:
                        vlans.append({'id': vlan_id, 'name': f'VLAN{vlan_id}'})
                    in_vlan_section = True

            # VLAN 이름
            elif 'vlan name' in stripped_line.lower():
                parts = stripped_line.split()
                if len(parts) >= 4:  # vlan <id> name <name>
                    vlan_id = parts[1]
                    vlan_name = ' '.join(parts[3:])
                    # 기존 VLAN 업데이트 또는 새로 추가
                    existing_vlan = next((v for v in vlans if v['id'] == vlan_id), None)
                    if existing_vlan:
                        existing_vlan['name'] = vlan_name
                    else:
                        vlans.append({'id': vlan_id, 'name': vlan_name})

            # VLAN 설명
            elif in_vlan_section and 'name' in stripped_line.lower():
                parts = stripped_line.split()
                if len(parts) >= 2:
                    # 마지막 VLAN에 이름 추가
                    if vlans:
                        vlans[-1]['name'] = parts[1]

        return vlans

    @staticmethod
    def _parse_static_routes(lines: List[str]) -> List[Dict]:
        """정적 경로 파싱"""
        routes = []

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('ip route '):
                parts = stripped_line.split()
                if len(parts) >= 4:
                    route = {
                        'network': parts[2],
                        'mask': parts[3],
                        'next_hop': parts[4] if len(parts) > 4 else '',
                        'interface': parts[5] if len(parts) > 5 else ''
                    }
                    routes.append(route)

        return routes

    @staticmethod
    def _parse_ospf_config(lines: List[str]) -> Dict:
        """OSPF 구성 파싱"""
        ospf_config = {'enabled': False, 'process_id': '', 'networks': []}
        in_ospf = False
        current_process = ''

        for line in lines:
            stripped_line = line.strip()

            if 'router ospf' in stripped_line:
                ospf_config['enabled'] = True
                parts = stripped_line.split()
                if len(parts) >= 2:
                    current_process = parts[1]
                    ospf_config['process_id'] = current_process
                in_ospf = True
            elif in_ospf and stripped_line.startswith('network '):
                parts = stripped_line.split()
                if len(parts) >= 4:
                    network = {
                        'network': parts[1],
                        'wildcard': parts[2],
                        'area': parts[3]
                    }
                    ospf_config['networks'].append(network)
            elif in_ospf and stripped_line.startswith('!'):
                in_ospf = False

        return ospf_config

    @staticmethod
    def _parse_bgp_config(lines: List[str]) -> Dict:
        """BGP 구성 파싱"""
        bgp_config = {'enabled': False, 'as_number': '', 'neighbors': []}
        in_bgp = False

        for line in lines:
            stripped_line = line.strip()

            if 'router bgp' in stripped_line:
                bgp_config['enabled'] = True
                parts = stripped_line.split()
                if len(parts) >= 2:
                    bgp_config['as_number'] = parts[2]
                in_bgp = True
            elif in_bgp and 'neighbor' in stripped_line and 'remote-as' in stripped_line:
                parts = stripped_line.split()
                neighbor_ip = parts[1]
                remote_as = parts[3] if len(parts) > 3 else ''
                bgp_config['neighbors'].append({
                    'ip': neighbor_ip,
                    'remote_as': remote_as
                })
            elif in_bgp and stripped_line.startswith('!'):
                in_bgp = False

        return bgp_config

    @staticmethod
    def _parse_version_info(lines: List[str]) -> Dict:
        """버전 및 모델 정보 파싱"""
        version_info = {'version': '', 'model': '', 'serial': ''}

        for line in lines:
            if 'Version' in line:
                version_info['version'] = line.strip()
            elif 'Model number' in line or 'pid:' in line.lower():
                version_info['model'] = line.strip()
            elif 'System serial number' in line or 'SN:' in line:
                version_info['serial'] = line.strip()

        return version_info

    @staticmethod
    def analyze_multiple_commands(command_outputs: Dict[str, str]) -> Dict[str, Any]:
        """여러 show 명령어 출력 분석"""
        analysis = {}

        if 'show run' in command_outputs:
            analysis.update(CLIAnalyzer.analyze_show_run(command_outputs['show run']))

        if 'show version' in command_outputs:
            # 버전 정보 보강
            version_info = CLIAnalyzer._parse_detailed_version(command_outputs['show version'])
            analysis.update(version_info)

        if 'show vlan' in command_outputs:
            # VLAN 정보 보강
            vlan_info = CLIAnalyzer._parse_show_vlan(command_outputs['show vlan'])
            analysis['vlans'] = vlan_info

        return analysis

    @staticmethod
    def _parse_detailed_version(version_output: str) -> Dict:
        """상세 버전 정보 파싱"""
        info = {'version': '', 'model': '', 'serial': '', 'uptime': '', 'memory': ''}
        lines = version_output.split('\n')

        for line in lines:
            if 'Version' in line:
                info['version'] = line.strip()
            elif 'Model number' in line or 'pid:' in line.lower():
                info['model'] = line.strip()
            elif 'System serial number' in line:
                info['serial'] = line.strip()
            elif 'uptime' in line.lower():
                info['uptime'] = line.strip()
            elif 'Memory' in line:
                info['memory'] = line.strip()

        return info

    @staticmethod
    def _parse_show_vlan(vlan_output: str) -> List[Dict]:
        """show vlan 출력 파싱"""
        vlans = []
        lines = vlan_output.split('\n')
        in_vlan_table = False

        for line in lines:
            stripped_line = line.strip()

            # VLAN 테이블 시작
            if 'VLAN Name' in stripped_line and 'Status' in stripped_line:
                in_vlan_table = True
                continue

            if in_vlan_table and stripped_line and not stripped_line.startswith('---'):
                parts = stripped_line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    vlan_id = parts[0]
                    vlan_name = parts[1] if len(parts) > 1 else f'VLAN{vlan_id}'
                    vlans.append({'id': vlan_id, 'name': vlan_name})

        return vlans