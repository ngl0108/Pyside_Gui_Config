# cisco_config_manager/core/connection_manager.py
"""
Cisco 장비 연결 및 명령어 실행 관리 모듈
SSH/Telnet을 통한 실시간 연결 및 구성 배포
"""

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

# Netmiko를 사용할 수 없는 경우를 위한 폴백
try:
    from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False
    print("Warning: Netmiko not installed. Install with: pip install netmiko")

# Paramiko를 직접 사용하는 경우
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    print("Warning: Paramiko not installed. Install with: pip install paramiko")

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
            
    def batch_deploy(self, device_names: List[str], commands: List[str], parallel: bool = False) -> Dict[str, Tuple[bool, str]]:
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
        self.connection_manager = connection_manager
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
        if not self.connection_manager.is_connected(device_name):
            result['message'] = "Device not connected"
            return result
            
        connection = self.connection_manager.get_connection(device_name)
        
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
        connection = self.connection_manager.get_connection(device_name)
        
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
    
    # 연결 (실제 사용 시 비밀번호 입력 필요)
    # if manager.connect_device("SW1", "password123", "enable123"):
    #     connection = manager.get_connection("SW1")
    #     
    #     # 명령어 실행
    #     success, output = manager.execute_command("SW1", "show version")
    #     if success:
    #         print(output)
    #     
    #     # 구성 배포
    #     commands = [
    #         "interface GigabitEthernet0/1",
    #         "description Test Interface",
    #         "no shutdown"
    #     ]
    #     success, output = manager.deploy_config("SW1", commands)
    #     
    #     # 연결 종료
    #     manager.disconnect_device("SW1")
    
    print("Connection Manager module ready")