# cisco_config_manager/core/config_manager.py
import json
import os
import re
import time
import threading
from typing import Dict, List, Any, Tuple, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

# 로깅 설정
logger = logging.getLogger(__name__)


class ConfigDiff:
    """구성 변경사항 비교 클래스"""

    @staticmethod
    def compare_configs(original: Dict, modified: Dict) -> Dict[str, Any]:
        """두 구성을 비교하여 변경사항 반환"""
        changes = {
            'added': {},
            'modified': {},
            'deleted': {},
            'summary': {
                'total_changes': 0,
                'interfaces_changed': 0,
                'vlans_changed': 0,
                'global_changed': 0
            }
        }

        # 글로벌 설정 비교
        ConfigDiff._compare_global_config(original, modified, changes)

        # 인터페이스 비교
        ConfigDiff._compare_interfaces(original, modified, changes)

        # VLAN 비교
        ConfigDiff._compare_vlans(original, modified, changes)

        # 라우팅 비교
        ConfigDiff._compare_routing(original, modified, changes)

        # 요약 계산
        changes['summary']['total_changes'] = (
                len(changes['added']) +
                len(changes['modified']) +
                len(changes['deleted'])
        )

        return changes

    @staticmethod
    def _compare_global_config(original: Dict, modified: Dict, changes: Dict):
        """글로벌 설정 비교"""
        orig_global = original.get('global', {})
        mod_global = modified.get('global', {})

        global_changes = {}

        # 호스트명 변경
        if orig_global.get('hostname') != mod_global.get('hostname'):
            global_changes['hostname'] = {
                'original': orig_global.get('hostname'),
                'modified': mod_global.get('hostname')
            }

        # 도메인명 변경
        if orig_global.get('domain_name') != mod_global.get('domain_name'):
            global_changes['domain_name'] = {
                'original': orig_global.get('domain_name'),
                'modified': mod_global.get('domain_name')
            }

        if global_changes:
            changes['modified']['global'] = global_changes
            changes['summary']['global_changed'] = len(global_changes)

    @staticmethod
    def _compare_interfaces(original: Dict, modified: Dict, changes: Dict):
        """인터페이스 구성 비교"""
        orig_interfaces = {iface['name']: iface for iface in original.get('interfaces', [])}
        mod_interfaces = {iface['name']: iface for iface in modified.get('interfaces', [])}

        all_interface_names = set(orig_interfaces.keys()) | set(mod_interfaces.keys())
        interface_changes = 0

        for iface_name in all_interface_names:
            orig_iface = orig_interfaces.get(iface_name, {})
            mod_iface = mod_interfaces.get(iface_name, {})

            # 새 인터페이스 추가
            if iface_name not in orig_interfaces:
                changes['added'][f"interface_{iface_name}"] = mod_iface
                interface_changes += 1
                continue

            # 인터페이스 삭제
            if iface_name not in mod_interfaces:
                changes['deleted'][f"interface_{iface_name}"] = orig_iface
                interface_changes += 1
                continue

            # 인터페이스 변경사항
            iface_changes = ConfigDiff._compare_single_interface(orig_iface, mod_iface)
            if iface_changes:
                changes['modified'][f"interface_{iface_name}"] = iface_changes
                interface_changes += 1

        changes['summary']['interfaces_changed'] = interface_changes

    @staticmethod
    def _compare_single_interface(orig_iface: Dict, mod_iface: Dict) -> Dict:
        """단일 인터페이스 변경사항 비교"""
        changes = {}

        # 기본 속성 비교
        basic_attributes = ['description', 'shutdown', 'mode', 'type']
        for attr in basic_attributes:
            if orig_iface.get(attr) != mod_iface.get(attr):
                changes[attr] = {
                    'original': orig_iface.get(attr),
                    'modified': mod_iface.get(attr)
                }

        # Access 설정 비교
        if orig_iface.get('access') != mod_iface.get('access'):
            changes['access'] = {
                'original': orig_iface.get('access'),
                'modified': mod_iface.get('access')
            }

        # Trunk 설정 비교
        if orig_iface.get('trunk') != mod_iface.get('trunk'):
            changes['trunk'] = {
                'original': orig_iface.get('trunk'),
                'modified': mod_iface.get('trunk')
            }

        # Routed 설정 비교
        if orig_iface.get('routed') != mod_iface.get('routed'):
            changes['routed'] = {
                'original': orig_iface.get('routed'),
                'modified': mod_iface.get('routed')
            }

        # STP 설정 비교
        if orig_iface.get('stp') != mod_iface.get('stp'):
            changes['stp'] = {
                'original': orig_iface.get('stp'),
                'modified': mod_iface.get('stp')
            }

        # Port Security 설정 비교
        if orig_iface.get('port_security') != mod_iface.get('port_security'):
            changes['port_security'] = {
                'original': orig_iface.get('port_security'),
                'modified': mod_iface.get('port_security')
            }

        return changes

    @staticmethod
    def _compare_vlans(original: Dict, modified: Dict, changes: Dict):
        """VLAN 구성 비교"""
        orig_vlans = {vlan['id']: vlan for vlan in original.get('vlans', {}).get('list', [])}
        mod_vlans = {vlan['id']: vlan for vlan in modified.get('vlans', {}).get('list', [])}

        all_vlan_ids = set(orig_vlans.keys()) | set(mod_vlans.keys())
        vlan_changes = 0

        for vlan_id in all_vlan_ids:
            orig_vlan = orig_vlans.get(vlan_id, {})
            mod_vlan = mod_vlans.get(vlan_id, {})

            # 새 VLAN 추가
            if vlan_id not in orig_vlans:
                changes['added'][f"vlan_{vlan_id}"] = mod_vlan
                vlan_changes += 1
                continue

            # VLAN 삭제
            if vlan_id not in mod_vlans:
                changes['deleted'][f"vlan_{vlan_id}"] = orig_vlan
                vlan_changes += 1
                continue

            # VLAN 변경사항
            vlan_changes_detail = ConfigDiff._compare_single_vlan(orig_vlan, mod_vlan)
            if vlan_changes_detail:
                changes['modified'][f"vlan_{vlan_id}"] = vlan_changes_detail
                vlan_changes += 1

        changes['summary']['vlans_changed'] = vlan_changes

    @staticmethod
    def _compare_single_vlan(orig_vlan: Dict, mod_vlan: Dict) -> Dict:
        """단일 VLAN 변경사항 비교"""
        changes = {}

        # VLAN 이름 변경
        if orig_vlan.get('name') != mod_vlan.get('name'):
            changes['name'] = {
                'original': orig_vlan.get('name'),
                'modified': mod_vlan.get('name')
            }

        # VLAN 설명 변경
        if orig_vlan.get('description') != mod_vlan.get('description'):
            changes['description'] = {
                'original': orig_vlan.get('description'),
                'modified': mod_vlan.get('description')
            }

        # SVI 설정 변경
        if orig_vlan.get('svi') != mod_vlan.get('svi'):
            changes['svi'] = {
                'original': orig_vlan.get('svi'),
                'modified': mod_vlan.get('svi')
            }

        return changes

    @staticmethod
    def _compare_routing(original: Dict, modified: Dict, changes: Dict):
        """라우팅 구성 비교"""
        # 정적 경로 비교
        orig_routes = original.get('routing', {}).get('static_routes', [])
        mod_routes = modified.get('routing', {}).get('static_routes', [])

        # 추가된 정적 경로
        for route in mod_routes:
            if route not in orig_routes:
                changes['added'][f"static_route_{route.get('prefix')}"] = route

        # 삭제된 정적 경로
        for route in orig_routes:
            if route not in mod_routes:
                changes['deleted'][f"static_route_{route.get('prefix')}"] = route

    @staticmethod
    def get_change_summary(changes: Dict) -> str:
        """변경사항 요약 문자열 반환"""
        summary = changes.get('summary', {})
        return (
            f"총 변경사항: {summary.get('total_changes', 0)}개\n"
            f"- 인터페이스: {summary.get('interfaces_changed', 0)}개\n"
            f"- VLAN: {summary.get('vlans_changed', 0)}개\n"
            f"- 글로벌 설정: {summary.get('global_changed', 0)}개"
        )

    @staticmethod
    def generate_change_report(changes: Dict) -> str:
        """상세 변경 보고서 생성"""
        report = ["=== 구성 변경 보고서 ==="]

        # 추가된 항목
        if changes['added']:
            report.append("\n[추가된 항목]")
            for key, value in changes['added'].items():
                report.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")

        # 삭제된 항목
        if changes['deleted']:
            report.append("\n[삭제된 항목]")
            for key, value in changes['deleted'].items():
                report.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")

        # 수정된 항목
        if changes['modified']:
            report.append("\n[수정된 항목]")
            for key, value in changes['modified'].items():
                report.append(f"- {key}:")
                for attr, change in value.items():
                    report.append(f"  {attr}: {change['original']} → {change['modified']}")

        # 요약
        report.append(f"\n[요약]")
        report.append(ConfigDiff.get_change_summary(changes))

        return "\n".join(report)


class ConfigTemplate:
    """구성 템플릿 관리 클래스"""

    # 기본 템플릿 디렉토리
    TEMPLATE_DIR = os.path.expanduser("~/.cisco_config_manager/templates")

    def __init__(self):
        """템플릿 관리자 초기화"""
        self._ensure_template_dir()
        self.config_manager = self._load_templates()

    def _ensure_template_dir(self):
        """템플릿 디렉토리 생성"""
        if not os.path.exists(self.TEMPLATE_DIR):
            os.makedirs(self.TEMPLATE_DIR)

    def _load_templates(self) -> Dict[str, Dict]:
        """저장된 템플릿 로드"""
        templates = {}

        if os.path.exists(self.TEMPLATE_DIR):
            for filename in os.listdir(self.TEMPLATE_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.TEMPLATE_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # 키는 파일명에서 가져오고, 템플릿 이름은 내부 데이터에서 가져옴
                            template_name = data.get('name', filename[:-5])
                            templates[template_name] = data
                    except Exception as e:
                        logger.error(f"템플릿 로드 실패 {filename}: {e}")

        return templates

    def save_template(self, template_name: str, config_data: Dict, description: str = "",
                      category: str = "User") -> bool:
        """
        현재 구성 데이터를 새로운 구성 템플릿으로 저장합니다.
        :param template_name: 템플릿 이름 (UI에서 입력받음)
        :param config_data: 저장할 구성 데이터
        :param description: 템플릿 설명
        :param category: 템플릿 카테고리
        :return: 성공 여부
        """
        if not template_name:
            raise ValueError("템플릿 이름은 필수입니다.")

        # 파일명은 템플릿 이름을 기반으로 안전하게 만듦
        safe_filename = re.sub(r'[^\w\-_\.]', '', template_name.replace(' ', '_')).lower()
        filepath = os.path.join(self.TEMPLATE_DIR, f"{safe_filename}.json")

        template_data = {
            "name": template_name,
            "description": description,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "config": config_data
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=4, ensure_ascii=False)

            self.config_manager[template_name] = template_data
            logger.info(f"새 템플릿 저장 완료: {template_name}")
            return True
        except Exception as e:
            logger.error(f"템플릿 저장 실패: {str(e)}")
            raise IOError(f"템플릿 저장 실패: {str(e)}")

    def delete_template(self, name: str) -> bool:
        """템플릿 삭제"""
        try:
            # 안전한 파일명 찾기
            safe_filename = re.sub(r'[^\w\-_\.]', '', name.replace(' ', '_')).lower()
            filepath = os.path.join(self.TEMPLATE_DIR, f"{safe_filename}.json")

            if os.path.exists(filepath):
                os.remove(filepath)

            if name in self.config_manager:
                del self.config_manager[name]

            logger.info(f"템플릿 삭제 완료: {name}")
            return True
        except Exception as e:
            logger.error(f"템플릿 삭제 실패: {e}")
            return False

    def get_template(self, name: str) -> Dict:
        """템플릿 가져오기"""
        return self.config_manager.get(name, {})

    def list_templates(self) -> List[Dict]:
        """템플릿 목록 반환"""
        template_list = []
        for name, template in self.config_manager.items():
            template_list.append({
                'name': name,
                'description': template.get('description', ''),
                'created': template.get('created_at', ''),
                'category': template.get('category', 'User')
            })
        return sorted(template_list, key=lambda x: x['name'])

    def get_all_templates_metadata(self) -> List[Dict]:
        """모든 템플릿의 메타데이터 (내장 + 사용자) 목록을 반환합니다."""
        # 내장 템플릿 메타데이터
        builtin_metadata = BuiltInTemplates.get_all_templates_metadata()

        # 사용자 정의 템플릿 메타데이터
        user_metadata = self.list_templates()

        return builtin_metadata + user_metadata

    def apply_template(self, template_name: str, variables: Dict = None) -> Dict:
        """템플릿 적용 (변수 치환 기능 강화)"""
        template = self.get_template(template_name)
        if not template:
            return {}

        config = template.get('config', {})

        if variables:
            # 1. 딕셔너리를 JSON 문자열로 변환
            config_str = json.dumps(config)

            # 2. 변수 치환 ({{var}} 형식)
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"  # {{key}}
                config_str = config_str.replace(placeholder, str(var_value))

            # 3. 미치환 변수 체크 (선택사항)
            remaining_vars = re.findall(r'\{\{([^}]+)\}\}', config_str)
            if remaining_vars:
                logger.warning(f"템플릿 '{template_name}'에 미치환 변수 잔존: {remaining_vars}")

            # 4. JSON으로 다시 변환
            try:
                config = json.loads(config_str)
            except json.JSONDecodeError as e:
                logger.error(f"템플릿 '{template_name}' 치환 중 JSON 오류: {e}")
                return {}

        return config


class BuiltInTemplates:
    """내장 템플릿 모음"""

    @staticmethod
    def get_basic_l2_switch() -> Dict:
        return {
            'global': {
                'hostname': '{{hostname}}',
                'domain_name': '{{domain}}',
                'service_password_encryption': True,
                'service_timestamps': True,
                'no_ip_http': True,
                'no_cdp': False,
                'lldp': True
            },
            'vlans': {
                'list': [
                    {'id': '10', 'name': 'Management'},
                    {'id': '20', 'name': 'Data'},
                    {'id': '30', 'name': 'Voice'},
                    {'id': '99', 'name': 'Native'}
                ]
            },
            'interfaces': [
                {
                    'name': 'GigabitEthernet0/1',
                    'description': 'Uplink to Core',
                    'mode': 'L2 Trunk',
                    'trunk': {
                        'native_vlan': '99',
                        'allowed_vlans': '10,20,30'
                    }
                }
            ],
            'switching': {
                'stp_mode': 'rapid-pvst',
                'portfast_default': True,
                'bpduguard_default': True
            }
        }

    @staticmethod
    def get_basic_l3_switch() -> Dict:
        return {
            'global': {
                'hostname': '{{hostname}}',
                'domain_name': '{{domain}}',
                'ip_routing': True,
                'service_password_encryption': True,
                'service_timestamps': True
            },
            'vlans': {
                'ip_routing': True,
                'list': [
                    {
                        'id': '10',
                        'name': 'Management',
                        'svi': {
                            'enabled': True,
                            'ip': '{{mgmt_ip}} {{mgmt_mask}}',
                            'description': 'Management VLAN'
                        }
                    },
                    {
                        'id': '20',
                        'name': 'Data',
                        'svi': {
                            'enabled': True,
                            'ip': '{{data_ip}} {{data_mask}}',
                            'description': 'Data VLAN'
                        }
                    }
                ]
            },
            'interfaces': [
                {
                    'name': 'GigabitEthernet0/1',
                    'description': 'Link to Router',
                    'mode': 'L3 Routed',
                    'routed': {
                        'ip': '{{uplink_ip}} {{uplink_mask}}'
                    }
                }
            ],
            'routing': {
                'static_routes': [
                    {
                        'prefix': '0.0.0.0 0.0.0.0',
                        'nexthop': '{{default_gateway}}'
                    }
                ]
            }
        }

    @staticmethod
    def get_branch_router() -> Dict:
        return {
            'global': {
                'hostname': 'Branch-{{branch_id}}',
                'domain_name': '{{domain}}',
                'service_password_encryption': True,
                'service_timestamps': True,
                'no_ip_http': True
            },
            'interfaces': [
                {
                    'name': 'GigabitEthernet0/0',
                    'description': 'WAN Interface',
                    'mode': 'L3 Routed',
                    'routed': {
                        'ip': '{{wan_ip}} {{wan_mask}}'
                    }
                },
                {
                    'name': 'GigabitEthernet0/1',
                    'description': 'LAN Interface',
                    'mode': 'L3 Routed',
                    'routed': {
                        'ip': '{{lan_ip}} {{lan_mask}}'
                    }
                }
            ],
            'routing': {
                'static_routes': [
                    {
                        'prefix': '0.0.0.0 0.0.0.0',
                        'nexthop': '{{isp_gateway}}'
                    }
                ],
                'nat': {
                    'enabled': True,
                    'inside': 'GigabitEthernet0/1',
                    'outside': 'GigabitEthernet0/0',
                    'overload': True
                }
            },
            'security': {
                'acls': [
                    {
                        'name': 'NAT_ACL',
                        'type': 'Standard',
                        'entries': [
                            {
                                'action': 'permit',
                                'source': '{{lan_network}} {{lan_wildcard}}'
                            }
                        ]
                    }
                ]
            }
        }

    @staticmethod
    def get_dmz_firewall() -> Dict:
        return {
            'global': {
                'hostname': 'FW-DMZ-{{site}}',
                'domain_name': '{{domain}}',
                'service_password_encryption': True,
                'no_ip_http': True,
                'no_cdp': True
            },
            'interfaces': [
                {
                    'name': 'GigabitEthernet0/0',
                    'description': 'Outside Interface',
                    'mode': 'L3 Routed',
                    'routed': {
                        'ip': '{{outside_ip}} {{outside_mask}}'
                    },
                    'security_level': 0
                },
                {
                    'name': 'GigabitEthernet0/1',
                    'description': 'Inside Interface',
                    'mode': 'L3 Routed',
                    'routed': {
                        'ip': '{{inside_ip}} {{inside_mask}}'
                    },
                    'security_level': 100
                },
                {
                    'name': 'GigabitEthernet0/2',
                    'description': 'DMZ Interface',
                    'mode': 'L3 Routed',
                    'routed': {
                        'ip': '{{dmz_ip}} {{dmz_mask}}'
                    },
                    'security_level': 50
                }
            ],
            'security': {
                'acls': [
                    {
                        'name': 'OUTSIDE_IN',
                        'type': 'Extended',
                        'entries': [
                            {
                                'action': 'permit',
                                'protocol': 'tcp',
                                'source': 'any',
                                'destination': '{{dmz_web_server}}',
                                'dst_port': 'eq 80'
                            },
                            {
                                'action': 'permit',
                                'protocol': 'tcp',
                                'source': 'any',
                                'destination': '{{dmz_web_server}}',
                                'dst_port': 'eq 443'
                            }
                        ]
                    }
                ]
            }
        }

    @staticmethod
    def get_voip_config() -> Dict:
        return {
            'global': {
                'hostname': '{{hostname}}',
                'domain_name': '{{domain}}',
                'service_timestamps': True
            },
            'vlans': {
                'list': [
                    {
                        'id': '{{voice_vlan}}',
                        'name': 'Voice',
                        'priority': 5
                    }
                ]
            },
            'interfaces': [],  # 인터페이스별로 적용
            'qos': {
                'class_maps': [
                    {
                        'name': 'VOICE-RTP',
                        'match': 'dscp ef'
                    },
                    {
                        'name': 'VOICE-SIGNALING',
                        'match': 'dscp cs3'
                    }
                ],
                'policy_maps': [
                    {
                        'name': 'VOICE-POLICY',
                        'classes': [
                            {
                                'name': 'VOICE-RTP',
                                'priority': 'percent 30'
                            },
                            {
                                'name': 'VOICE-SIGNALING',
                                'bandwidth': 'percent 5'
                            }
                        ]
                    }
                ],
                'auto_qos': True
            },
            'switching': {
                'voice_vlan': '{{voice_vlan}}',
                'trust_device': 'cisco-phone',
                'mls_qos': True
            }
        }

    @staticmethod
    def get_hsrp_config() -> Dict:
        return {
            'ha': {
                'hsrp': {
                    'enabled': True,
                    'groups': [
                        {
                            'id': '{{group_id}}',
                            'vip': '{{virtual_ip}}',
                            'priority': '{{priority}}',
                            'preempt': True,
                            'track': '{{track_interface}}',
                            'decrement': 20,
                            'authentication': '{{auth_string}}'
                        }
                    ]
                }
            }
        }

    @staticmethod
    def get_ospf_config() -> Dict:
        return {
            'routing': {
                'ospf': {
                    'enabled': True,
                    'process_id': '{{process_id}}',
                    'router_id': '{{router_id}}',
                    'networks': [
                        {
                            'network': '{{network1}}',
                            'wildcard': '{{wildcard1}}',
                            'area': '0'
                        },
                        {
                            'network': '{{network2}}',
                            'wildcard': '{{wildcard2}}',
                            'area': '{{area2}}'
                        }
                    ],
                    'passive_interfaces': ['default'],
                    'no_passive_interfaces': ['{{uplink_interface}}']
                }
            }
        }

    @staticmethod
    def get_bgp_config() -> Dict:
        return {
            'routing': {
                'bgp': {
                    'enabled': True,
                    'as_number': '{{local_as}}',
                    'router_id': '{{router_id}}',
                    'neighbors': [
                        {
                            'ip': '{{neighbor_ip}}',
                            'remote_as': '{{remote_as}}',
                            'description': '{{neighbor_desc}}',
                            'update_source': '{{update_source}}',
                            'soft_reconfiguration': True
                        }
                    ],
                    'networks': [
                        '{{advertised_network1}}',
                        '{{advertised_network2}}'
                    ],
                    'redistribute': {
                        'connected': True,
                        'static': False
                    }
                }
            }
        }

    @staticmethod
    def get_security_hardening() -> Dict:
        return {
            'global': {
                'service_password_encryption': True,
                'no_ip_http': True,
                'no_ip_http_secure': True,
                'no_cdp': True,
                'no_service_tcp_small_servers': True,
                'no_service_udp_small_servers': True,
                'no_service_finger': True,
                'no_ip_source_route': True,
                'no_ip_bootp_server': True,
                'tcp_synwait_time': 10,
                'tcp_intercept': True
            },
            'security': {
                'aaa': {
                    'new_model': True,
                    'authentication_login': 'default local',
                    'authorization_exec': 'default local',
                    'accounting': 'default start-stop local'
                },
                'ssh': {
                    'version': 2,
                    'timeout': 60,
                    'authentication_retries': 3,
                    'key_size': 2048
                },
                'passwords': {
                    'min_length': 8,
                    'encryption_type': 7
                },
                'login': {
                    'block_for': 300,
                    'attempts': 3,
                    'within': 60,
                    'quiet_mode_access_class': 'MGMT_ACL'
                }
            },
            'line_console': {
                'exec_timeout': '5 0',
                'logging_synchronous': True,
                'transport_output': 'none'
            },
            'line_vty': {
                'exec_timeout': '5 0',
                'transport_input': 'ssh',
                'access_class': 'SSH_ACL'
            }
        }

    @staticmethod
    def get_spanning_tree_config() -> Dict:
        return {
            'switching': {
                'stp_mode': 'rapid-pvst',
                'portfast_default': True,
                'bpduguard_default': True,
                'bpdufilter_default': False,
                'loopguard_default': True,
                'root_guard_interfaces': ['{{uplink1}}', '{{uplink2}}'],
                'priorities': {
                    'vlan_1': 4096,
                    'vlan_10': 8192,
                    'vlan_20': 8192,
                    'vlan_30': 8192
                }
            }
        }

    @staticmethod
    def get_builtin_template(name: str) -> Dict:
        """내장 템플릿 반환"""
        templates = {
            'basic_l2_switch': BuiltInTemplates.get_basic_l2_switch,
            'basic_l3_switch': BuiltInTemplates.get_basic_l3_switch,
            'branch_router': BuiltInTemplates.get_branch_router,
            'dmz_firewall': BuiltInTemplates.get_dmz_firewall,
            'voip_config': BuiltInTemplates.get_voip_config,
            'hsrp_config': BuiltInTemplates.get_hsrp_config,
            'ospf_config': BuiltInTemplates.get_ospf_config,
            'bgp_config': BuiltInTemplates.get_bgp_config,
            'security_hardening': BuiltInTemplates.get_security_hardening,
            'spanning_tree_config': BuiltInTemplates.get_spanning_tree_config
        }

        if name in templates:
            return templates[name]()
        return {}

    @staticmethod
    def get_all_templates_metadata() -> List[Dict]:
        """내장 템플릿 메타데이터 목록 반환"""
        return [
            {
                'name': 'basic_l2_switch',
                'description': '기본 L2 스위치 구성',
                'category': 'Switch'
            },
            {
                'name': 'basic_l3_switch',
                'description': '기본 L3 스위치 구성',
                'category': 'Switch'
            },
            {
                'name': 'branch_router',
                'description': '지사 라우터 구성',
                'category': 'Router'
            },
            {
                'name': 'dmz_firewall',
                'description': 'DMZ 방화벽 구성',
                'category': 'Security'
            },
            {
                'name': 'voip_config',
                'description': 'VoIP 구성',
                'category': 'Voice'
            },
            {
                'name': 'hsrp_config',
                'description': 'HSRP 고가용성 구성',
                'category': 'HA'
            },
            {
                'name': 'ospf_config',
                'description': 'OSPF 라우팅 구성',
                'category': 'Routing'
            },
            {
                'name': 'bgp_config',
                'description': 'BGP 라우팅 구성',
                'category': 'Routing'
            },
            {
                'name': 'security_hardening',
                'description': '보안 강화 구성',
                'category': 'Security'
            },
            {
                'name': 'spanning_tree_config',
                'description': '스패닝 트리 구성',
                'category': 'Switch'
            }
        ]


class BackupScheduler:
    """설정 백업 자동화 스케줄러"""

    def __init__(self, connection_manager):
        self.device_manager = connection_manager
        self.interval = 3600  # 기본 1시간
        self.running = False
        self.thread = None
        self.callback = None  # UI 업데이트용 콜백

    def set_interval(self, seconds: int):
        """주기 설정 (초 단위)"""
        self.interval = seconds

    def set_callback(self, callback: Callable):
        """백업 완료 시 호출할 UI 콜백"""
        self.callback = callback

    def start(self):
        """스케줄러 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"백업 스케줄러 시작됨 (주기: {self.interval}초)")

    def stop(self):
        """스케줄러 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("백업 스케줄러 중지됨")

    def _run_loop(self):
        """백그라운드 실행 루프"""
        while self.running:
            try:
                self._perform_backup()
            except Exception as e:
                logger.error(f"스케줄러 오류: {str(e)}")

            # interval 만큼 대기 (1초씩 체크하며 중지 신호 확인)
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

    def _perform_backup(self):
        """모든 연결된 장비 백업 수행"""
        logger.info("자동 백업 시작")
        results = self.device_manager.backup_all_devices()

        success_count = 0
        for device, backup in results.items():
            if backup:
                success_count += 1
                if self.callback:
                    self.callback(f"자동 백업 완료: {device}")
            else:
                logger.warning(f"자동 백업 실패: {device}")

        logger.info(f"자동 백업 완료 (성공: {success_count}/{len(results)})")