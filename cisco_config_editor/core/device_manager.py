# cisco_config_manager/core/device_manager.py
import os
import json
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

# 현재 코드의 import 부분을 다음과 같이 수정
try:
    from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException
    NETMIKO_AVAILABLE = True
    print("Netmiko successfully imported")
except ImportError as e:
    NETMIKO_AVAILABLE = False
    print(f"Error importing netmiko: {e}")
    print("Please install with: pip install netmiko")

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
    print("Paramiko successfully imported")
except ImportError as e:
    PARAMIKO_AVAILABLE = False
    print(f"Error importing paramiko: {e}")
    print("Please install with: pip install paramiko")
# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """연결 상태 열거형"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    BUSY = "busy"


class DeviceType(Enum):
    """장비 타입 열거형"""
    CISCO_IOS = "cisco_ios"
    CISCO_IOSXE = "cisco_iosxe"
    CISCO_NXOS = "cisco_nxos"
    CISCO_ASA = "cisco_asa"
    CISCO_IOS_TELNET = "cisco_ios_telnet"


@dataclass
class DeviceInfo:
    """장비 정보 데이터 클래스"""
    name: str
    host: str
    username: str
    password: str
    device_type: str = "cisco_ios"
    port: int = 22
    enable_password: Optional[str] = None
    timeout: int = 30
    session_log: Optional[str] = None

    def to_dict(self) -> Dict:
        """딕셔너리로 변환 (비밀번호 제외)"""
        return {
            'name': self.name,
            'host': self.host,
            'username': self.username,
            'device_type': self.device_type,
            'port': self.port,
            'timeout': self.timeout
        }


@dataclass
class BackupInfo:
    """백업 정보 데이터 클래스"""
    device_name: str
    timestamp: str
    config: str
    file_path: str

    def save(self):
        """백업 파일 저장"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w') as f:
            f.write(self.config)
        logger.info(f"Backup saved: {self.file_path}")


class DeviceConnection:
    """단일 장비 연결 관리 클래스"""

    def __init__(self, device_info: DeviceInfo):
        self.device_info = device_info
        self.connection = None
        self.status = ConnectionStatus.DISCONNECTED
        self.last_error = None
        self.backup_dir = os.path.expanduser("~/.cisco_config_manager/backups")

    def connect(self) -> bool:
        """장비에 연결"""
        if not NETMIKO_AVAILABLE:
            self.last_error = "Netmiko library not installed"
            self.status = ConnectionStatus.ERROR
            return False

        self.status = ConnectionStatus.CONNECTING

        try:
            device_dict = {
                'device_type': self.device_info.device_type,
                'host': self.device_info.host,
                'username': self.device_info.username,
                'password': self.device_info.password,
                'port': self.device_info.port,
                'timeout': self.device_info.timeout,
                'session_log': self.device_info.session_log
            }

            if self.device_info.enable_password:
                device_dict['secret'] = self.device_info.enable_password

            self.connection = ConnectHandler(**device_dict)

            # Enable 모드 진입
            if self.device_info.enable_password:
                self.connection.enable()

            self.status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to {self.device_info.name} ({self.device_info.host})")
            return True

        except NetmikoAuthenticationException as e:
            self.last_error = f"Authentication failed: {str(e)}"
            self.status = ConnectionStatus.ERROR
            logger.error(self.last_error)
            return False

        except NetmikoTimeoutException as e:
            self.last_error = f"Connection timeout: {str(e)}"
            self.status = ConnectionStatus.ERROR
            logger.error(self.last_error)
            return False

        except Exception as e:
            self.last_error = f"Connection error: {str(e)}"
            self.status = ConnectionStatus.ERROR
            logger.error(self.last_error)
            return False

    def disconnect(self):
        """연결 종료"""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info(f"Disconnected from {self.device_info.name}")
            except:
                pass
            finally:
                self.connection = None
                self.status = ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.status == ConnectionStatus.CONNECTED and self.connection is not None

    def send_command(self, command: str, use_textfsm: bool = False) -> str:
        """단일 명령어 실행"""
        if not self.is_connected():
            raise ConnectionError("Not connected to device")

        try:
            self.status = ConnectionStatus.BUSY
            output = self.connection.send_command(command, use_textfsm=use_textfsm)
            self.status = ConnectionStatus.CONNECTED
            return output
        except Exception as e:
            self.last_error = f"Command execution failed: {str(e)}"
            logger.error(self.last_error)
            raise

    def send_config_commands(self, commands: List[str]) -> str:
        """구성 명령어 실행"""
        if not self.is_connected():
            raise ConnectionError("Not connected to device")

        try:
            self.status = ConnectionStatus.BUSY
            output = self.connection.send_config_set(commands)
            self.status = ConnectionStatus.CONNECTED
            return output
        except Exception as e:
            self.last_error = f"Config commands failed: {str(e)}"
            logger.error(self.last_error)
            raise

    def get_running_config(self) -> str:
        """현재 실행 구성 가져오기"""
        return self.send_command("show running-config")

    def get_startup_config(self) -> str:
        """시작 구성 가져오기"""
        return self.send_command("show startup-config")

    def save_config(self) -> bool:
        """구성 저장 (write memory)"""
        try:
            output = self.send_command("write memory")
            return "OK" in output or "bytes copied" in output
        except Exception as e:
            logger.error(f"Failed to save config: {str(e)}")
            return False

    def backup_config(self, backup_type: str = "running") -> Optional[BackupInfo]:
        """구성 백업"""
        try:
            if backup_type == "running":
                config = self.get_running_config()
            else:
                config = self.get_startup_config()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{self.device_info.name}_{backup_type}_{timestamp}.cfg"
            file_path = os.path.join(self.backup_dir, self.device_info.name, file_name)

            backup = BackupInfo(
                device_name=self.device_info.name,
                timestamp=timestamp,
                config=config,
                file_path=file_path
            )
            backup.save()

            return backup

        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None

    def restore_config(self, backup: BackupInfo) -> bool:
        """구성 복원"""
        try:
            # 현재 구성 백업
            current_backup = self.backup_config("running_before_restore")
            if not current_backup:
                logger.warning("Could not backup current config before restore")

            # 백업 구성을 명령어로 변환
            commands = backup.config.split('\n')
            # 주석과 빈 줄 제거
            commands = [cmd for cmd in commands if cmd and not cmd.startswith('!')]

            # 구성 모드 진입 및 적용
            output = self.send_config_commands(commands)

            # 구성 저장
            if self.save_config():
                logger.info(f"Configuration restored from {backup.file_path}")
                return True
            else:
                logger.error("Failed to save restored configuration")
                return False

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False


class ConnectionManager:
    """다중 장비 연결 관리 클래스"""

    def __init__(self):
        self.connections: Dict[str, DeviceConnection] = {}
        self.device_list: List[DeviceInfo] = []
        self.config_dir = os.path.expanduser("~/.cisco_config_manager")
        self.devices_file = os.path.join(self.config_dir, "devices.json")
        self._load_devices()

    def _load_devices(self):
        """저장된 장비 목록 로드"""
        if os.path.exists(self.devices_file):
            try:
                with open(self.devices_file, 'r') as f:
                    devices_data = json.load(f)
                    for device_dict in devices_data:
                        # 비밀번호는 저장하지 않으므로 빈 문자열로 초기화
                        device_dict.setdefault('password', '')
                        device_dict.setdefault('enable_password', None)
                        self.device_list.append(DeviceInfo(**device_dict))
                logger.info(f"Loaded {len(self.device_list)} devices")
            except Exception as e:
                logger.error(f"Failed to load devices: {str(e)}")

    def save_devices(self):
        """장비 목록 저장 (비밀번호 제외)"""
        os.makedirs(self.config_dir, exist_ok=True)
        devices_data = [device.to_dict() for device in self.device_list]

        with open(self.devices_file, 'w') as f:
            json.dump(devices_data, f, indent=2)
        logger.info(f"Saved {len(self.device_list)} devices")

    def add_device(self, device_info: DeviceInfo) -> bool:
        """장비 추가"""
        # 중복 확인
        for existing in self.device_list:
            if existing.name == device_info.name:
                logger.warning(f"Device {device_info.name} already exists")
                return False

        self.device_list.append(device_info)
        self.save_devices()
        return True

    def remove_device(self, device_name: str) -> bool:
        """장비 제거"""
        # 연결 종료
        if device_name in self.connections:
            self.connections[device_name].disconnect()
            del self.connections[device_name]

        # 목록에서 제거
        self.device_list = [d for d in self.device_list if d.name != device_name]
        self.save_devices()
        return True

    def connect_device(self, device_name: str, password: str, enable_password: Optional[str] = None) -> bool:
        """특정 장비에 연결"""
        device_info = self.get_device_info(device_name)
        if not device_info:
            logger.error(f"Device {device_name} not found")
            return False

        # 비밀번호 설정
        device_info.password = password
        device_info.enable_password = enable_password

        # 연결 객체 생성 및 연결
        connection = DeviceConnection(device_info)
        if connection.connect():
            self.connections[device_name] = connection
            return True
        return False

    def disconnect_device(self, device_name: str):
        """특정 장비 연결 종료"""
        if device_name in self.connections:
            self.connections[device_name].disconnect()
            del self.connections[device_name]

    def disconnect_all(self):
        """모든 연결 종료"""
        for connection in self.connections.values():
            connection.disconnect()
        self.connections.clear()

    def get_device_info(self, device_name: str) -> Optional[DeviceInfo]:
        """장비 정보 가져오기"""
        for device in self.device_list:
            if device.name == device_name:
                return device
        return None

    def get_connection(self, device_name: str) -> Optional[DeviceConnection]:
        """연결 객체 가져오기"""
        return self.connections.get(device_name)

    def is_connected(self, device_name: str) -> bool:
        """연결 상태 확인"""
        connection = self.get_connection(device_name)
        return connection.is_connected() if connection else False

    def execute_command(self, device_name: str, command: str) -> Tuple[bool, str]:
        """명령어 실행"""
        connection = self.get_connection(device_name)
        if not connection:
            return False, f"Device {device_name} not connected"

        try:
            output = connection.send_command(command)
            return True, output
        except Exception as e:
            return False, str(e)

    def deploy_config(self, device_name: str, commands: List[str], backup_first: bool = True) -> Tuple[bool, str]:
        """구성 배포"""
        connection = self.get_connection(device_name)
        if not connection:
            return False, f"Device {device_name} not connected"

        try:
            # 백업 수행
            if backup_first:
                backup = connection.backup_config("running_before_deploy")
                if not backup:
                    return False, "Backup failed"

            # 구성 적용
            output = connection.send_config_commands(commands)

            # 구성 저장
            if connection.save_config():
                return True, output
            else:
                return False, "Failed to save configuration"

        except Exception as e:
            return False, str(e)

    def batch_deploy(self, device_names: List[str], commands: List[str], parallel: bool = False) -> Dict[
        str, Tuple[bool, str]]:
        """다중 장비 일괄 배포"""
        results = {}

        if parallel:
            # 병렬 처리
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self.deploy_config, name, commands): name
                    for name in device_names
                }
                for future in concurrent.futures.as_completed(futures):
                    device_name = futures[future]
                    try:
                        results[device_name] = future.result()
                    except Exception as e:
                        results[device_name] = (False, str(e))
        else:
            # 순차 처리
            for device_name in device_names:
                results[device_name] = self.deploy_config(device_name, commands)

        return results

    def backup_all_devices(self) -> Dict[str, Optional[BackupInfo]]:
        """모든 연결된 장비 백업"""
        results = {}
        for device_name, connection in self.connections.items():
            if connection.is_connected():
                results[device_name] = connection.backup_config()
        return results

    def get_device_status(self, device_name: str) -> Dict[str, Any]:
        """장비 상태 정보"""
        connection = self.get_connection(device_name)
        if not connection:
            return {
                'name': device_name,
                'status': ConnectionStatus.DISCONNECTED.value,
                'connected': False
            }

        return {
            'name': device_name,
            'status': connection.status.value,
            'connected': connection.is_connected(),
            'host': connection.device_info.host,
            'last_error': connection.last_error
        }

    def get_all_status(self) -> List[Dict[str, Any]]:
        """모든 장비 상태"""
        status_list = []
        for device in self.device_list:
            status_list.append(self.get_device_status(device.name))
        return status_list


class DeploymentManager:
    """구성 배포 관리 클래스"""

    def __init__(self, connection_manager: ConnectionManager):
        self.device_manager = connection_manager
        self.deployment_history = []
        self.rollback_configs = {}

    def validate_commands(self, commands: List[str]) -> Tuple[bool, List[str]]:
        """명령어 유효성 검사"""
        errors = []

        # 위험한 명령어 검사
        dangerous_commands = [
            'reload',
            'format',
            'delete',
            'erase',
            'clear config'
        ]

        for cmd in commands:
            cmd_lower = cmd.lower().strip()
            for dangerous in dangerous_commands:
                if dangerous in cmd_lower:
                    errors.append(f"위험한 명령어 감지: {cmd}")

        # 구문 검사 (기본)
        for cmd in commands:
            if cmd.strip() and not cmd.startswith('!'):
                # 기본적인 구문 검사
                if '  ' in cmd:  # 연속된 공백
                    errors.append(f"구문 오류 가능성: {cmd}")

        return len(errors) == 0, errors

    def create_rollback_plan(self, device_name: str, commands: List[str]) -> List[str]:
        """롤백 명령어 생성"""
        rollback_commands = []

        for cmd in commands:
            cmd = cmd.strip()
            if cmd.startswith('no '):
                # 'no' 명령어는 원래 명령어로 롤백
                rollback_commands.append(cmd[3:])
            elif not cmd.startswith('!') and cmd:
                # 일반 명령어는 'no'를 붙여서 롤백
                rollback_commands.append(f"no {cmd}")

        return rollback_commands

    def deploy_with_validation(self, device_name: str, commands: List[str]) -> Dict[str, Any]:
        """검증 후 배포"""
        result = {
            'device': device_name,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'message': '',
            'backup': None,
            'output': ''
        }

        # 명령어 검증
        valid, errors = self.validate_commands(commands)
        if not valid:
            result['message'] = f"Validation failed: {'; '.join(errors)}"
            return result

        # 연결 확인
        if not self.device_manager.is_connected(device_name):
            result['message'] = "Device not connected"
            return result

        connection = self.device_manager.get_connection(device_name)

        try:
            # 백업
            backup = connection.backup_config()
            result['backup'] = backup.file_path if backup else None

            # 배포
            output = connection.send_config_commands(commands)
            result['output'] = output

            # 저장
            if connection.save_config():
                result['success'] = True
                result['message'] = "Deployment successful"

                # 이력 저장
                self.deployment_history.append(result)

                # 롤백 정보 저장
                self.rollback_configs[device_name] = {
                    'backup': backup,
                    'commands': self.create_rollback_plan(device_name, commands),
                    'timestamp': datetime.now()
                }
            else:
                result['message'] = "Failed to save configuration"

        except Exception as e:
            result['message'] = f"Deployment failed: {str(e)}"

        return result

    def rollback(self, device_name: str) -> Dict[str, Any]:
        """마지막 변경 롤백"""
        result = {
            'device': device_name,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'message': ''
        }

        if device_name not in self.rollback_configs:
            result['message'] = "No rollback configuration available"
            return result

        rollback_info = self.rollback_configs[device_name]
        connection = self.device_manager.get_connection(device_name)

        if not connection or not connection.is_connected():
            result['message'] = "Device not connected"
            return result

        try:
            # 백업에서 복원
            if rollback_info['backup']:
                if connection.restore_config(rollback_info['backup']):
                    result['success'] = True
                    result['message'] = "Rollback successful"
                    del self.rollback_configs[device_name]
                else:
                    result['message'] = "Rollback failed"
            else:
                # 롤백 명령어 실행
                output = connection.send_config_commands(rollback_info['commands'])
                if connection.save_config():
                    result['success'] = True
                    result['message'] = "Rollback successful"
                    del self.rollback_configs[device_name]
                else:
                    result['message'] = "Failed to save rollback configuration"

        except Exception as e:
            result['message'] = f"Rollback failed: {str(e)}"

        return result

    def get_deployment_history(self, device_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """배포 이력 조회"""
        if device_name:
            return [h for h in self.deployment_history if h['device'] == device_name]
        return self.deployment_history


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


# 테스트 및 예제 사용
if __name__ == "__main__":
    # 연결 관리자 생성
    manager = ConnectionManager()

    # 장비 추가
    device = DeviceInfo(
        name="SW1",
        host="192.168.1.10",
        username="admin",
        password="",  # 실제 사용 시 입력
        device_type="cisco_ios"
    )
    manager.add_device(device)

    print("Device Manager module ready")