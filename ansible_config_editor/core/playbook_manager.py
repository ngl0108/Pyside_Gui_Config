# ansible_config_editor/core/playbook_manager.py
import yaml
from typing import Dict, List, Any


class ConfigManager:
    """
    GUI에서 수집된 구조화된 데이터로부터 OS 유형에 맞는
    Ansible 플레이북을 동적으로 생성하는 핵심 클래스
    """

    def __init__(self):
        self.supported_os_types = [
            "L2_IOS-XE", "L3_IOS-XE",
            "L2_NX-OS", "L3_NX-OS",
            "WLC_AireOS"
        ]

    def generate_playbook(self, os_type: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        주어진 OS 유형과 구성 데이터로부터 완전한 Ansible 플레이북을 생성합니다.

        Args:
            os_type: 대상 장비 OS 유형 (예: "L3_IOS-XE")
            config_data: UI에서 수집된 구조화된 구성 데이터

        Returns:
            Ansible이 실행할 수 있는 완전한 플레이북 구조 (딕셔너리)
        """
        if os_type not in self.supported_os_types:
            raise ValueError(f"지원하지 않는 OS 유형입니다: {os_type}")

        # 기본 플레이북 구조 생성
        playbook = {
            'name': f'Standard Configuration for {os_type}',
            'hosts': 'all',
            'gather_facts': 'no',
            'connection': 'network_cli',
            'tasks': []
        }

        # OS별 기본 설정
        if 'IOS-XE' in os_type:
            playbook['vars'] = {
                'ansible_network_os': 'ios',
                'ansible_user': '{{ ansible_user }}',
                'ansible_password': '{{ ansible_password }}'
            }
        elif 'NX-OS' in os_type:
            playbook['vars'] = {
                'ansible_network_os': 'nxos',
                'ansible_user': '{{ ansible_user }}',
                'ansible_password': '{{ ansible_password }}'
            }

        # 모듈별 태스크 생성
        global_tasks = self._generate_global_tasks(os_type, config_data.get('global', {}))
        interface_tasks = self._generate_interface_tasks(os_type, config_data.get('interfaces', {}))
        vlan_tasks = self._generate_vlan_tasks(os_type, config_data.get('vlans', {}))
        # ! --- 추가된 부분 시작 ---
        switching_tasks = self._generate_switching_tasks(os_type, config_data.get('switching', {}))
        # ! --- 추가된 부분 끝 ---
        routing_tasks = self._generate_routing_tasks(os_type, config_data.get('routing', {}))
        ha_tasks = self._generate_ha_tasks(os_type, config_data.get('ha', {}))
        security_tasks = self._generate_security_tasks(os_type, config_data.get('security', {}))

        # 모든 태스크를 플레이북에 추가
        playbook['tasks'].extend(global_tasks)
        playbook['tasks'].extend(interface_tasks)
        playbook['tasks'].extend(vlan_tasks)
        # ! --- 추가된 부분 시작 ---
        playbook['tasks'].extend(switching_tasks)
        # ! --- 추가된 부분 끝 ---
        playbook['tasks'].extend(routing_tasks)
        playbook['tasks'].extend(ha_tasks)
        playbook['tasks'].extend(security_tasks)

        return playbook

    def _generate_global_tasks(self, os_type: str, global_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """글로벌 설정 태스크 생성 (확장된 버전)"""
        tasks = []
        commands = []

        # Hostname 설정
        hostname = global_config.get('hostname', '')
        if hostname:
            commands.append(f"hostname {hostname}")

        # Service 설정
        if global_config.get('service_timestamps', False):
            if 'IOS-XE' in os_type:
                commands.extend([
                    "service timestamps debug datetime msec localtime show-timezone",
                    "service timestamps log datetime msec localtime show-timezone"
                ])
            elif 'NX-OS' in os_type:
                commands.extend([
                    "service timestamps debug",
                    "service timestamps log"
                ])

        if global_config.get('service_password_encryption', False):
            commands.append("service password-encryption")

        if global_config.get('service_call_home', False):
            commands.append("no service call-home")

        # DNS & Domain 설정
        domain_name = global_config.get('domain_name', '')
        if domain_name:
            if 'IOS-XE' in os_type:
                commands.append(f"ip domain name {domain_name}")
            elif 'NX-OS' in os_type:
                commands.append(f"ip domain-name {domain_name}")

        # DNS 서버 설정
        for dns_server in global_config.get('dns_servers', []):
            if dns_server.get('ip'):
                if dns_server.get('vrf'):
                    if 'IOS-XE' in os_type:
                        commands.append(f"ip name-server vrf {dns_server['vrf']} {dns_server['ip']}")
                    elif 'NX-OS' in os_type:
                        commands.append(f"ip name-server {dns_server['ip']} use-vrf {dns_server['vrf']}")
                else:
                    commands.append(f"ip name-server {dns_server['ip']}")

        # Clock & Timezone 설정
        timezone = global_config.get('timezone', '')
        if timezone:
            if timezone.startswith('KST'):
                if 'IOS-XE' in os_type:
                    commands.append("clock timezone KST 9")
                elif 'NX-OS' in os_type:
                    commands.append("clock timezone KST 9 0")
            elif timezone.startswith('JST'):
                if 'IOS-XE' in os_type:
                    commands.append("clock timezone JST 9")
                elif 'NX-OS' in os_type:
                    commands.append("clock timezone JST 9 0")
            elif timezone.startswith('UTC'):
                if 'IOS-XE' in os_type:
                    commands.append("clock timezone UTC 0")
                elif 'NX-OS' in os_type:
                    commands.append("clock timezone UTC 0 0")
            elif timezone.startswith('Custom') or '/' in timezone:
                # Custom timezone 처리는 추후 구현
                pass
            else:
                # 기타 타임존 파싱
                parts = timezone.split()
                if len(parts) >= 2:
                    tz_name = parts[0]
                    try:
                        offset = int(parts[1])
                        if 'IOS-XE' in os_type:
                            commands.append(f"clock timezone {tz_name} {offset}")
                        elif 'NX-OS' in os_type:
                            commands.append(f"clock timezone {tz_name} {offset} 0")
                    except ValueError:
                        pass

        # Logging 설정
        logging_level = global_config.get('logging_level', '')
        if logging_level:
            # "informational (6)" 형태에서 숫자만 추출
            level_num = logging_level.split('(')[1].split(')')[0] if '(' in logging_level else '6'
            if 'IOS-XE' in os_type:
                commands.append(f"logging trap {level_num}")
            elif 'NX-OS' in os_type:
                commands.append(f"logging level {level_num}")

        if global_config.get('logging_console', True):
            commands.append("logging console")

        if global_config.get('logging_buffered', True):
            buffer_size = global_config.get('logging_buffer_size', '32000')
            if buffer_size:
                commands.append(f"logging buffered {buffer_size}")
            else:
                commands.append("logging buffered")

        # Remote Logging 설정
        for log_host in global_config.get('logging_hosts', []):
            if log_host.get('ip'):
                if log_host.get('vrf'):
                    if 'IOS-XE' in os_type:
                        commands.append(f"logging host {log_host['ip']} vrf {log_host['vrf']}")
                    elif 'NX-OS' in os_type:
                        commands.append(f"logging server {log_host['ip']} use-vrf {log_host['vrf']}")
                else:
                    if 'IOS-XE' in os_type:
                        commands.append(f"logging host {log_host['ip']}")
                    elif 'NX-OS' in os_type:
                        commands.append(f"logging server {log_host['ip']}")

        # NTP 설정
        if global_config.get('ntp_authenticate', False):
            commands.append("ntp authenticate")

        ntp_master_stratum = global_config.get('ntp_master_stratum', '')
        if ntp_master_stratum:
            commands.append(f"ntp master {ntp_master_stratum}")

        for ntp_server in global_config.get('ntp_servers', []):
            if ntp_server.get('ip'):
                ntp_cmd = f"ntp server {ntp_server['ip']}"

                if ntp_server.get('key_id'):
                    ntp_cmd += f" key {ntp_server['key_id']}"

                if ntp_server.get('prefer'):
                    ntp_cmd += " prefer"

                if ntp_server.get('vrf'):
                    if 'IOS-XE' in os_type:
                        ntp_cmd += f" vrf {ntp_server['vrf']}"
                    elif 'NX-OS' in os_type:
                        ntp_cmd += f" use-vrf {ntp_server['vrf']}"

                commands.append(ntp_cmd)

        # Management Interface 설정
        mgmt_config = global_config.get('management', {})
        if mgmt_config.get('interface') and mgmt_config.get('ip'):
            interface = mgmt_config['interface']
            ip = mgmt_config['ip']
            subnet = mgmt_config.get('subnet', '255.255.255.0')
            gateway = mgmt_config.get('gateway', '')
            vrf = mgmt_config.get('vrf', '')

            # 서브넷 마스크 처리 (/24 -> 255.255.255.0 변환)
            if subnet.startswith('/'):
                try:
                    prefix_len = int(subnet[1:])
                    # 간단한 CIDR to netmask 변환 (주요 값들만)
                    cidr_to_mask = {
                        24: '255.255.255.0', 25: '255.255.255.128', 26: '255.255.255.192',
                        27: '255.255.255.224', 28: '255.255.255.240', 29: '255.255.255.248',
                        30: '255.255.255.252', 16: '255.255.0.0', 8: '255.0.0.0'
                    }
                    subnet = cidr_to_mask.get(prefix_len, '255.255.255.0')
                except ValueError:
                    subnet = '255.255.255.0'

            # 인터페이스 설정 명령어 생성
            if 'IOS-XE' in os_type:
                commands.extend([
                    f"interface {interface}",
                    f" ip address {ip} {subnet}",
                    " no shutdown"
                ])
                if vrf:
                    commands.insert(-1, f" vrf forwarding {vrf}")
            elif 'NX-OS' in os_type:
                commands.extend([
                    f"interface {interface}",
                    f" ip address {ip}/{self._netmask_to_prefix(subnet)}",
                    " no shutdown"
                ])
                if vrf:
                    commands.insert(-1, f" vrf member {vrf}")

            # 기본 게이트웨이 설정
            if gateway:
                if vrf:
                    if 'IOS-XE' in os_type:
                        commands.append(f"ip route vrf {vrf} 0.0.0.0 0.0.0.0 {gateway}")
                    elif 'NX-OS' in os_type:
                        commands.append(f"vrf context {vrf}")
                        commands.append(f" ip route 0.0.0.0/0 {gateway}")
                else:
                    commands.append(f"ip route 0.0.0.0 0.0.0.0 {gateway}")

        # Banner 설정
        banner_config = global_config.get('banner', {})
        if banner_config.get('enabled') and banner_config.get('text'):
            banner_text = banner_config['text']
            # 배너 텍스트에서 줄바꿈을 ^C로 구분된 형태로 변환
            formatted_banner = banner_text.replace('\n', '^C')
            commands.append(f"banner login ^C{formatted_banner}^C")

        # Archive 설정
        archive_config = global_config.get('archive', {})
        if archive_config.get('enabled'):
            archive_commands = ["archive"]

            if archive_config.get('path'):
                archive_commands.append(f" path {archive_config['path']}")

            if archive_config.get('max_files'):
                archive_commands.append(f" maximum {archive_config['max_files']}")

            if archive_config.get('time_period_enabled') and archive_config.get('time_period'):
                archive_commands.append(f" time-period {archive_config['time_period']}")

            commands.extend(archive_commands)

        # 명령어가 있으면 태스크 생성
        if commands:
            if 'IOS-XE' in os_type:
                tasks.append({
                    'name': 'Configure Global Settings (IOS-XE)',
                    'cisco.ios.ios_config': {
                        'lines': commands
                    }
                })
            elif 'NX-OS' in os_type:
                # NX-OS는 일부 기능을 활성화해야 함
                feature_commands = []
                if global_config.get('ntp_servers'):
                    feature_commands.append("feature ntp")
                if global_config.get('management', {}).get('vrf'):
                    feature_commands.append("feature interface-vlan")

                if feature_commands:
                    tasks.append({
                        'name': 'Enable required features (NX-OS)',
                        'cisco.nxos.nxos_config': {
                            'lines': feature_commands
                        }
                    })

                tasks.append({
                    'name': 'Configure Global Settings (NX-OS)',
                    'cisco.nxos.nxos_config': {
                        'lines': commands
                    }
                })

        return tasks

    def _netmask_to_prefix(self, netmask: str) -> str:
        """네트마스크를 CIDR 프리픽스로 변환"""
        mask_to_prefix = {
            '255.255.255.0': '24', '255.255.255.128': '25', '255.255.255.192': '26',
            '255.255.255.224': '27', '255.255.255.240': '28', '255.255.255.248': '29',
            '255.255.255.252': '30', '255.255.0.0': '16', '255.0.0.0': '8'
        }
        return mask_to_prefix.get(netmask, '24')

    def _generate_interface_tasks(self, os_type: str, interface_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """인터페이스 설정 태스크 생성 (기본 구현)"""
        tasks = []

        # 현재는 기본 구조만 제공
        if interface_config.get('description'):
            tasks.append({
                'name': 'Configure Interface Description (Placeholder)',
                'debug': {
                    'msg': f"Interface type: {interface_config.get('type', 'Access')}, "
                           f"Description: {interface_config.get('description')}"
                }
            })

        return tasks

    def _generate_vlan_tasks(self, os_type: str, vlan_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """VLAN 설정 태스크 생성"""
        tasks = []
        commands = []

        # VLAN 생성
        for vlan in vlan_config.get('list', []):
            if vlan.get('id'):
                vlan_id = vlan['id']
                vlan_name = vlan.get('name', f"VLAN{vlan_id}")

                if 'IOS-XE' in os_type:
                    commands.extend([
                        f"vlan {vlan_id}",
                        f" name {vlan_name}"
                    ])
                elif 'NX-OS' in os_type:
                    commands.extend([
                        f"vlan {vlan_id}",
                        f"  name {vlan_name}"
                    ])

        if commands:
            if 'IOS-XE' in os_type:
                tasks.append({
                    'name': 'Configure VLANs (IOS-XE)',
                    'cisco.ios.ios_config': {
                        'lines': commands
                    }
                })
            elif 'NX-OS' in os_type:
                tasks.append({
                    'name': 'Configure VLANs (NX-OS)',
                    'cisco.nxos.nxos_config': {
                        'lines': commands
                    }
                })

        return tasks

    # ! --- 추가된 부분 시작 ---
    def _generate_switching_tasks(self, os_type: str, switching_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """스위칭 관련 설정 태스크 생성"""
        tasks = []
        commands = []

        # Spanning Tree
        if 'IOS-XE' in os_type or 'NX-OS' in os_type:
            if switching_config.get('stp_mode'):
                commands.append(f"spanning-tree mode {switching_config['stp_mode']}")
            if switching_config.get('stp_portfast_default'):
                commands.append("spanning-tree portfast default")
            if switching_config.get('stp_bpduguard_default'):
                commands.append("spanning-tree portfast bpduguard default")

        if commands:
            module = 'cisco.ios.ios_config' if 'IOS-XE' in os_type else 'cisco.nxos.nxos_config'
            tasks.append({
                'name': 'Configure Switching Settings',
                module: {
                    'lines': commands
                }
            })
        return tasks

    # ! --- 추가된 부분 끝 ---

    def _generate_routing_tasks(self, os_type: str, routing_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """라우팅 설정 태스크 생성 (향후 구현)"""
        tasks = []

        # 현재는 플레이스홀더만 제공
        tasks.append({
            'name': 'Configure Routing (Placeholder)',
            'debug': {
                'msg': 'Routing configuration will be implemented here'
            }
        })

        return tasks

    def _generate_ha_tasks(self, os_type: str, ha_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """고가용성 설정 태스크 생성 (향후 구현)"""
        tasks = []

        if 'IOS-XE' in os_type:
            tasks.append({
                'name': 'Configure StackWise Virtual (Placeholder)',
                'debug': {
                    'msg': 'StackWise Virtual configuration for IOS-XE'
                }
            })
        elif 'NX-OS' in os_type:
            tasks.append({
                'name': 'Configure vPC (Placeholder)',
                'debug': {
                    'msg': 'vPC configuration for NX-OS'
                }
            })

        return tasks

    def _generate_security_tasks(self, os_type: str, security_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        # ! --- 수정된 부분 시작 ---
        """보안 설정 태스크 생성 (대폭 확장)"""
        tasks = []
        commands = []

        # Local Users
        for user in security_config.get('local_users', []):
            if user.get('username') and user.get('password'):
                commands.append(
                    f"username {user['username']} privilege {user.get('privilege', '1')} secret {user['password']}")

        # AAA 설정
        if security_config.get('aaa_new_model', False):
            commands.append("aaa new-model")

        if security_config.get('aaa_auth_login'):
            commands.append(f"aaa authentication login {security_config['aaa_auth_login']}")

        if security_config.get('aaa_auth_exec'):
            commands.append(f"aaa authorization exec {security_config['aaa_auth_exec']}")

        # AAA 서버 그룹
        for aaa_group in security_config.get('aaa_groups', []):
            group_type = aaa_group.get('type', '').lower()
            group_name = aaa_group.get('group_name', '')
            servers = aaa_group.get('servers', [])

            if group_type and group_name and servers:
                if 'IOS-XE' in os_type:
                    if group_type == 'tacacs+':
                        commands.append(f"aaa group server tacacs+ {group_name}")
                        for server in servers:
                            commands.append(
                                f" server-private {server}")  # IOS-XE는 server-private을 사용하기도 함, 혹은 server ip
                    elif group_type == 'radius':
                        commands.append(f"aaa group server radius {group_name}")
                        for server in servers:
                            commands.append(f" server {server}")
                elif 'NX-OS' in os_type:
                    if group_type == 'tacacs+':
                        commands.append(f"aaa group server tacacs+ {group_name}")
                        for server in servers:
                            commands.append(f"  server {server}")

        # Line Configuration
        line_conf = security_config.get('line_config', {})
        if line_conf:
            commands.append("line con 0")
            if line_conf.get('con_timeout'):
                commands.append(f" exec-timeout {line_conf['con_timeout']}")
            if line_conf.get('con_logging_sync'):
                commands.append(" logging synchronous")

            commands.append("line vty 0 4")
            if line_conf.get('vty_timeout'):
                commands.append(f" exec-timeout {line_conf['vty_timeout']}")
            if line_conf.get('vty_transport'):
                commands.append(f" transport input {line_conf['vty_transport']}")

        # SNMP
        snmp_conf = security_config.get('snmp', {})
        if snmp_conf:
            if snmp_conf.get('location'):
                commands.append(f"snmp-server location {snmp_conf['location']}")
            if snmp_conf.get('contact'):
                commands.append(f"snmp-server contact {snmp_conf['contact']}")
            for comm in snmp_conf.get('communities', []):
                if comm.get('community'):
                    cmd = f"snmp-server community {comm['community']} {comm.get('permission', 'RO')}"
                    if comm.get('acl'):
                        cmd += f" {comm['acl']}"
                    commands.append(cmd)

        # Security Hardening
        hardening_conf = security_config.get('hardening', {})
        if hardening_conf:
            if hardening_conf.get('no_ip_http'):
                commands.append("no ip http server")
                commands.append("no ip http secure-server")
            if hardening_conf.get('no_cdp'):
                if 'IOS-XE' in os_type:
                    commands.append("no cdp run")
                elif 'NX-OS' in os_type:
                    commands.append("no feature cdp")
            if hardening_conf.get('lldp'):
                if 'IOS-XE' in os_type:
                    commands.append("lldp run")
                elif 'NX-OS' in os_type:
                    commands.append("feature lldp")

        if commands:
            module = 'cisco.ios.ios_config' if 'IOS-XE' in os_type else 'cisco.nxos.nxos_config'
            tasks.append({
                'name': 'Configure Security Settings',
                module: {
                    'lines': commands
                }
            })

        return tasks

    # ! --- 수정된 부분 끝 ---

    def export_playbook_to_yaml(self, playbook_data: Dict[str, Any]) -> str:
        """
        생성된 플레이북을 YAML 문자열로 변환합니다.
        파일로 저장하거나 미리보기에 사용할 수 있습니다.
        """
        # 플레이북을 리스트로 감싸야 함 (Ansible 플레이북 형식)
        playbook_list = [playbook_data]
        return yaml.dump(playbook_list, default_flow_style=False, allow_unicode=True, indent=2)