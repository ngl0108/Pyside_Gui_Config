# cisco_config_manager/core/validators.py
import re
import ipaddress
from typing import Tuple, Optional


class NetworkValidator:
    """네트워크 관련 입력값 검증 클래스"""
    
    @staticmethod
    def validate_ip_address(ip_str: str) -> Tuple[bool, str]:
        """IP 주소 유효성 검사"""
        try:
            ipaddress.ip_address(ip_str)
            return True, "유효한 IP 주소입니다."
        except ValueError:
            return False, f"'{ip_str}'는 올바른 IP 주소가 아닙니다."
            
    @staticmethod
    def validate_subnet_mask(mask_str: str) -> Tuple[bool, str]:
        """서브넷 마스크 유효성 검사"""
        try:
            # 점 표기법 마스크 검사
            if '.' in mask_str:
                parts = mask_str.split('.')
                if len(parts) != 4:
                    return False, "서브넷 마스크는 4개의 옥텟으로 구성되어야 합니다."
                    
                # 각 옥텟 검사
                valid_octets = [255, 254, 252, 248, 240, 224, 192, 128, 0]
                found_zero = False
                
                for part in parts:
                    try:
                        octet = int(part)
                        if octet not in valid_octets:
                            return False, f"'{octet}'는 유효한 마스크 옥텟이 아닙니다."
                        if found_zero and octet != 0:
                            return False, "서브넷 마스크는 연속된 1 비트 후 0 비트로 구성되어야 합니다."
                        if octet == 0:
                            found_zero = True
                    except ValueError:
                        return False, f"'{part}'는 올바른 숫자가 아닙니다."
                        
                return True, "유효한 서브넷 마스크입니다."
            else:
                return False, "올바른 서브넷 마스크 형식이 아닙니다."
        except Exception as e:
            return False, f"서브넷 마스크 검증 오류: {str(e)}"
            
    @staticmethod
    def validate_network_prefix(prefix_str: str) -> Tuple[bool, str]:
        """네트워크 프리픽스 유효성 검사 (예: 192.168.1.0/24)"""
        try:
            network = ipaddress.ip_network(prefix_str, strict=False)
            return True, f"유효한 네트워크: {network}"
        except ValueError:
            return False, f"'{prefix_str}'는 올바른 네트워크 프리픽스가 아닙니다."
            
    @staticmethod
    def validate_wildcard_mask(mask_str: str) -> Tuple[bool, str]:
        """와일드카드 마스크 유효성 검사"""
        try:
            parts = mask_str.split('.')
            if len(parts) != 4:
                return False, "와일드카드 마스크는 4개의 옥텟으로 구성되어야 합니다."
                
            for part in parts:
                try:
                    octet = int(part)
                    if not 0 <= octet <= 255:
                        return False, f"'{octet}'는 0-255 범위를 벗어났습니다."
                except ValueError:
                    return False, f"'{part}'는 올바른 숫자가 아닙니다."
                    
            return True, "유효한 와일드카드 마스크입니다."
        except Exception as e:
            return False, f"와일드카드 마스크 검증 오류: {str(e)}"
            
    @staticmethod
    def validate_mac_address(mac_str: str) -> Tuple[bool, str]:
        """MAC 주소 유효성 검사"""
        # Cisco 형식: xxxx.xxxx.xxxx
        cisco_pattern = r'^[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}$'
        # 표준 형식: xx:xx:xx:xx:xx:xx 또는 xx-xx-xx-xx-xx-xx
        standard_pattern = r'^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$'
        
        if re.match(cisco_pattern, mac_str) or re.match(standard_pattern, mac_str):
            return True, "유효한 MAC 주소입니다."
        else:
            return False, "올바른 MAC 주소 형식이 아닙니다. (예: 0011.2233.4455 또는 00:11:22:33:44:55)"


class VlanValidator:
    """VLAN 관련 검증 클래스"""
    
    @staticmethod
    def validate_vlan_id(vlan_id: str) -> Tuple[bool, str]:
        """VLAN ID 유효성 검사"""
        try:
            vlan_num = int(vlan_id)
            if vlan_num == 1:
                return False, "VLAN 1은 기본 VLAN으로 수정할 수 없습니다."
            elif 2 <= vlan_num <= 1001:
                return True, f"표준 VLAN {vlan_num}입니다."
            elif 1002 <= vlan_num <= 1005:
                return False, f"VLAN {vlan_num}는 예약된 VLAN입니다."
            elif 1006 <= vlan_num <= 4094:
                return True, f"확장 VLAN {vlan_num}입니다."
            else:
                return False, f"VLAN ID는 2-4094 범위여야 합니다."
        except ValueError:
            return False, f"'{vlan_id}'는 올바른 숫자가 아닙니다."
            
    @staticmethod
    def validate_vlan_range(vlan_range: str) -> Tuple[bool, str]:
        """VLAN 범위 유효성 검사 (예: 10,20,30-40)"""
        try:
            vlans = []
            parts = vlan_range.replace(' ', '').split(',')
            
            for part in parts:
                if '-' in part:
                    # 범위 처리
                    start, end = part.split('-')
                    start_num = int(start)
                    end_num = int(end)
                    
                    if start_num >= end_num:
                        return False, f"잘못된 범위: {part}"
                        
                    for vlan in range(start_num, end_num + 1):
                        valid, _ = VlanValidator.validate_vlan_id(str(vlan))
                        if not valid:
                            return False, f"범위에 잘못된 VLAN ID가 포함됨: {vlan}"
                        vlans.append(vlan)
                else:
                    # 단일 VLAN
                    valid, msg = VlanValidator.validate_vlan_id(part)
                    if not valid:
                        return False, msg
                    vlans.append(int(part))
                    
            return True, f"유효한 VLAN 범위: {sorted(set(vlans))}"
        except Exception as e:
            return False, f"VLAN 범위 파싱 오류: {str(e)}"
            
    @staticmethod
    def validate_vlan_name(name: str) -> Tuple[bool, str]:
        """VLAN 이름 유효성 검사"""
        if not name:
            return False, "VLAN 이름이 비어있습니다."
            
        if len(name) > 32:
            return False, "VLAN 이름은 32자를 초과할 수 없습니다."
            
        # 특수문자 검사
        if re.match(r'^[a-zA-Z0-9_\-]+$', name):
            return True, "유효한 VLAN 이름입니다."
        else:
            return False, "VLAN 이름에는 영문자, 숫자, _, - 만 사용할 수 있습니다."


class InterfaceValidator:
    """인터페이스 관련 검증 클래스"""
    
    # 인터페이스 이름 패턴
    INTERFACE_PATTERNS = {
        'ethernet': r'^(Fast|Gigabit|TenGigabit|TwentyFiveGigE|FortyGigabit|HundredGigE)?Ethernet\d+(/\d+)*$',
        'port_channel': r'^Port-channel\d+$',
        'vlan': r'^Vlan\d+$',
        'loopback': r'^Loopback\d+$',
        'tunnel': r'^Tunnel\d+$',
        'serial': r'^Serial\d+(/\d+)*$',
        'management': r'^Management\d+(/\d+)*$'
    }
    
    @staticmethod
    def validate_interface_name(name: str) -> Tuple[bool, str]:
        """인터페이스 이름 유효성 검사"""
        if not name:
            return False, "인터페이스 이름이 비어있습니다."
            
        # 각 패턴 확인
        for iface_type, pattern in InterfaceValidator.INTERFACE_PATTERNS.items():
            if re.match(pattern, name, re.IGNORECASE):
                return True, f"유효한 {iface_type} 인터페이스입니다."
                
        return False, "올바른 인터페이스 이름 형식이 아닙니다."
        
    @staticmethod
    def validate_interface_range(range_str: str) -> Tuple[bool, str]:
        """인터페이스 범위 유효성 검사 (예: GigabitEthernet0/1-5)"""
        try:
            # 기본 형식 검사
            match = re.match(r'^(\S+?)(\d+)/(\d+)-(\d+)$', range_str)
            if not match:
                return False, "올바른 인터페이스 범위 형식이 아닙니다."
                
            prefix = match.group(1)
            module = int(match.group(2))
            start_port = int(match.group(3))
            end_port = int(match.group(4))
            
            if start_port >= end_port:
                return False, "시작 포트가 종료 포트보다 작아야 합니다."
                
            return True, f"{prefix}{module}/{start_port}-{end_port} 범위가 유효합니다."
        except Exception as e:
            return False, f"인터페이스 범위 파싱 오류: {str(e)}"


class SecurityValidator:
    """보안 관련 검증 클래스"""
    
    @staticmethod
    def validate_password_strength(password: str, min_length: int = 8) -> Tuple[bool, str]:
        """비밀번호 강도 검증"""
        if len(password) < min_length:
            return False, f"비밀번호는 최소 {min_length}자 이상이어야 합니다."
            
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        strength_count = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength_count < 3:
            return False, "비밀번호는 대문자, 소문자, 숫자, 특수문자 중 최소 3가지를 포함해야 합니다."
            
        return True, "강력한 비밀번호입니다."
        
    @staticmethod
    def validate_acl_number(acl_num: str, acl_type: str = "standard") -> Tuple[bool, str]:
        """ACL 번호 유효성 검사"""
        try:
            num = int(acl_num)
            
            if acl_type.lower() == "standard":
                if 1 <= num <= 99 or 1300 <= num <= 1999:
                    return True, f"유효한 표준 ACL 번호입니다: {num}"
                else:
                    return False, "표준 ACL은 1-99 또는 1300-1999 범위여야 합니다."
                    
            elif acl_type.lower() == "extended":
                if 100 <= num <= 199 or 2000 <= num <= 2699:
                    return True, f"유효한 확장 ACL 번호입니다: {num}"
                else:
                    return False, "확장 ACL은 100-199 또는 2000-2699 범위여야 합니다."
                    
            else:
                return False, f"알 수 없는 ACL 타입: {acl_type}"
                
        except ValueError:
            return False, f"'{acl_num}'는 올바른 숫자가 아닙니다."
            
    @staticmethod
    def validate_community_string(community: str) -> Tuple[bool, str]:
        """SNMP 커뮤니티 스트링 검증"""
        if not community:
            return False, "커뮤니티 스트링이 비어있습니다."
            
        if len(community) < 8:
            return False, "보안을 위해 커뮤니티 스트링은 8자 이상이어야 합니다."
            
        # 기본값 확인
        default_strings = ['public', 'private', 'default']
        if community.lower() in default_strings:
            return False, f"'{community}'는 보안상 사용하지 말아야 할 기본값입니다."
            
        return True, "유효한 커뮤니티 스트링입니다."


class RoutingValidator:
    """라우팅 관련 검증 클래스"""
    
    @staticmethod
    def validate_as_number(as_num: str, bgp_type: str = "2byte") -> Tuple[bool, str]:
        """AS 번호 유효성 검사"""
        try:
            num = int(as_num)
            
            if bgp_type == "2byte":
                if 1 <= num <= 65535:
                    if 64512 <= num <= 65535:
                        return True, f"프라이빗 AS 번호입니다: {num}"
                    else:
                        return True, f"퍼블릭 AS 번호입니다: {num}"
                else:
                    return False, "2바이트 AS 번호는 1-65535 범위여야 합니다."
                    
            elif bgp_type == "4byte":
                if 1 <= num <= 4294967295:
                    return True, f"유효한 4바이트 AS 번호입니다: {num}"
                else:
                    return False, "4바이트 AS 번호는 1-4294967295 범위여야 합니다."
                    
            else:
                return False, f"알 수 없는 BGP 타입: {bgp_type}"
                
        except ValueError:
            return False, f"'{as_num}'는 올바른 숫자가 아닙니다."
            
    @staticmethod
    def validate_ospf_area(area: str) -> Tuple[bool, str]:
        """OSPF 영역 ID 유효성 검사"""
        try:
            # 정수 형식
            if area.isdigit():
                num = int(area)
                if 0 <= num <= 4294967295:
                    return True, f"유효한 OSPF 영역 ID입니다: {num}"
                else:
                    return False, "OSPF 영역 ID는 0-4294967295 범위여야 합니다."
                    
            # IP 주소 형식
            elif '.' in area:
                valid, msg = NetworkValidator.validate_ip_address(area)
                if valid:
                    return True, f"유효한 OSPF 영역 ID입니다: {area}"
                else:
                    return False, f"잘못된 IP 형식의 영역 ID: {msg}"
                    
            else:
                return False, "OSPF 영역 ID는 정수 또는 IP 주소 형식이어야 합니다."
                
        except Exception as e:
            return False, f"OSPF 영역 ID 검증 오류: {str(e)}"
            
    @staticmethod
    def validate_eigrp_as(as_num: str) -> Tuple[bool, str]:
        """EIGRP AS 번호 유효성 검사"""
        try:
            num = int(as_num)
            if 1 <= num <= 65535:
                return True, f"유효한 EIGRP AS 번호입니다: {num}"
            else:
                return False, "EIGRP AS 번호는 1-65535 범위여야 합니다."
        except ValueError:
            return False, f"'{as_num}'는 올바른 숫자가 아닙니다."


class PortValidator:
    """포트 관련 검증 클래스"""
    
    WELL_KNOWN_PORTS = {
        20: 'FTP-DATA', 21: 'FTP', 22: 'SSH', 23: 'TELNET',
        25: 'SMTP', 53: 'DNS', 67: 'DHCP-SERVER', 68: 'DHCP-CLIENT',
        69: 'TFTP', 80: 'HTTP', 110: 'POP3', 123: 'NTP',
        143: 'IMAP', 161: 'SNMP', 162: 'SNMP-TRAP', 179: 'BGP',
        443: 'HTTPS', 445: 'SMB', 514: 'SYSLOG', 520: 'RIP',
        546: 'DHCPv6-CLIENT', 547: 'DHCPv6-SERVER', 1645: 'OLD-RADIUS',
        1646: 'OLD-RADIUS-ACCT', 1812: 'RADIUS', 1813: 'RADIUS-ACCT',
        3389: 'RDP', 5060: 'SIP', 5061: 'SIP-TLS'
    }
    
    @staticmethod
    def validate_port_number(port: str) -> Tuple[bool, str]:
        """포트 번호 유효성 검사"""
        try:
            port_num = int(port)
            if not 1 <= port_num <= 65535:
                return False, "포트 번호는 1-65535 범위여야 합니다."
                
            if port_num in PortValidator.WELL_KNOWN_PORTS:
                service = PortValidator.WELL_KNOWN_PORTS[port_num]
                return True, f"유효한 포트입니다: {port_num} ({service})"
            elif port_num < 1024:
                return True, f"Well-known 포트입니다: {port_num}"
            elif port_num < 49152:
                return True, f"Registered 포트입니다: {port_num}"
            else:
                return True, f"Dynamic/Private 포트입니다: {port_num}"
                
        except ValueError:
            return False, f"'{port}'는 올바른 포트 번호가 아닙니다."
            
    @staticmethod
    def validate_port_range(port_range: str) -> Tuple[bool, str]:
        """포트 범위 유효성 검사 (예: 1024-2048)"""
        try:
            if '-' in port_range:
                start, end = port_range.split('-')
                start_num = int(start.strip())
                end_num = int(end.strip())
                
                if start_num >= end_num:
                    return False, "시작 포트가 종료 포트보다 작아야 합니다."
                    
                if not (1 <= start_num <= 65535 and 1 <= end_num <= 65535):
                    return False, "포트 번호는 1-65535 범위여야 합니다."
                    
                return True, f"유효한 포트 범위: {start_num}-{end_num}"
            else:
                return PortValidator.validate_port_number(port_range)
                
        except Exception as e:
            return False, f"포트 범위 파싱 오류: {str(e)}"


class HostnameValidator:
    """호스트명 관련 검증 클래스"""
    
    @staticmethod
    def validate_hostname(hostname: str) -> Tuple[bool, str]:
        """호스트명 유효성 검사"""
        if not hostname:
            return False, "호스트명이 비어있습니다."
            
        if len(hostname) > 63:
            return False, "호스트명은 63자를 초과할 수 없습니다."
            
        # 첫 글자는 문자여야 함
        if not hostname[0].isalpha():
            return False, "호스트명은 문자로 시작해야 합니다."
            
        # 마지막 글자는 문자 또는 숫자여야 함
        if not hostname[-1].isalnum():
            return False, "호스트명은 문자 또는 숫자로 끝나야 합니다."
            
        # 유효한 문자만 포함
        if re.match(r'^[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9]$', hostname):
            return True, "유효한 호스트명입니다."
        else:
            return False, "호스트명에는 영문자, 숫자, 하이픈(-)만 사용할 수 있습니다."
            
    @staticmethod
    def validate_domain_name(domain: str) -> Tuple[bool, str]:
        """도메인 이름 유효성 검사"""
        if not domain:
            return False, "도메인 이름이 비어있습니다."
            
        # 각 레이블 검사
        labels = domain.split('.')
        if len(labels) < 2:
            return False, "도메인 이름은 최소 하나의 점(.)을 포함해야 합니다."
            
        for label in labels:
            if not label:
                return False, "빈 레이블이 있습니다."
            if len(label) > 63:
                return False, f"레이블 '{label}'이 63자를 초과합니다."
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', label):
                return False, f"레이블 '{label}'에 잘못된 문자가 포함되어 있습니다."
                
        return True, "유효한 도메인 이름입니다."


# 유틸리티 함수
def validate_input(value: str, validator_func: callable) -> Tuple[bool, str]:
    """범용 입력 검증 함수"""
    return validator_func(value)


def get_validator_for_field(field_type: str) -> Optional[callable]:
    """필드 타입에 맞는 검증 함수 반환"""
    validators = {
        'ip_address': NetworkValidator.validate_ip_address,
        'subnet_mask': NetworkValidator.validate_subnet_mask,
        'network_prefix': NetworkValidator.validate_network_prefix,
        'wildcard_mask': NetworkValidator.validate_wildcard_mask,
        'mac_address': NetworkValidator.validate_mac_address,
        'vlan_id': VlanValidator.validate_vlan_id,
        'vlan_range': VlanValidator.validate_vlan_range,
        'vlan_name': VlanValidator.validate_vlan_name,
        'interface_name': InterfaceValidator.validate_interface_name,
        'interface_range': InterfaceValidator.validate_interface_range,
        'password': SecurityValidator.validate_password_strength,
        'acl_number': SecurityValidator.validate_acl_number,
        'community_string': SecurityValidator.validate_community_string,
        'as_number': RoutingValidator.validate_as_number,
        'ospf_area': RoutingValidator.validate_ospf_area,
        'eigrp_as': RoutingValidator.validate_eigrp_as,
        'port_number': PortValidator.validate_port_number,
        'port_range': PortValidator.validate_port_range,
        'hostname': HostnameValidator.validate_hostname,
        'domain_name': HostnameValidator.validate_domain_name,
    }
    
    return validators.get(field_type)