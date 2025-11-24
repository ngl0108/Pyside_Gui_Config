# cisco_config_manager/core/templates.py
import json
import os
from typing import Dict, List, Any
from datetime import datetime


class ConfigTemplate:
    """구성 템플릿 관리 클래스"""
    
    # 기본 템플릿 디렉토리
    TEMPLATE_DIR = os.path.expanduser("~/.cisco_config_manager/templates")
    
    def __init__(self):
        """템플릿 관리자 초기화"""
        self._ensure_template_dir()
        self.templates = self._load_templates()
        
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
                            template_name = filename[:-5]  # .json 제거
                            templates[template_name] = json.load(f)
                    except Exception as e:
                        print(f"템플릿 로드 실패 {filename}: {e}")
                        
        return templates
        
    def save_template(self, name: str, config: Dict, description: str = "") -> bool:
        """템플릿 저장"""
        try:
            template = {
                'name': name,
                'description': description,
                'created': datetime.now().isoformat(),
                'config': config
            }
            
            filepath = os.path.join(self.TEMPLATE_DIR, f"{name}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
                
            self.templates[name] = template
            return True
        except Exception as e:
            print(f"템플릿 저장 실패: {e}")
            return False
            
    def delete_template(self, name: str) -> bool:
        """템플릿 삭제"""
        try:
            filepath = os.path.join(self.TEMPLATE_DIR, f"{name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                
            if name in self.templates:
                del self.templates[name]
                
            return True
        except Exception as e:
            print(f"템플릿 삭제 실패: {e}")
            return False
            
    def get_template(self, name: str) -> Dict:
        """템플릿 가져오기"""
        return self.templates.get(name, {})
        
    def list_templates(self) -> List[Dict]:
        """템플릿 목록 반환"""
        template_list = []
        for name, template in self.templates.items():
            template_list.append({
                'name': name,
                'description': template.get('description', ''),
                'created': template.get('created', '')
            })
        return sorted(template_list, key=lambda x: x['name'])
        
    def apply_template(self, template_name: str, variables: Dict = None) -> Dict:
        """템플릿 적용 (변수 치환)"""
        template = self.get_template(template_name)
        if not template:
            return {}
            
        config = template.get('config', {})
        
        if variables:
            # 변수 치환 처리
            config_str = json.dumps(config)
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                config_str = config_str.replace(placeholder, str(var_value))
            config = json.loads(config_str)
            
        return config


class BuiltInTemplates:
    """내장 템플릿 모음"""
    
    @staticmethod
    def get_basic_l2_switch() -> Dict:
        """기본 L2 스위치 템플릿"""
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
        """기본 L3 스위치 템플릿"""
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
        """지사 라우터 템플릿"""
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
        """DMZ 방화벽 템플릿"""
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
        """VoIP 구성 템플릿"""
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
        """HSRP 구성 템플릿"""
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
        """OSPF 구성 템플릿"""
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
        """BGP 구성 템플릿"""
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
        """보안 강화 템플릿"""
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
        """스패닝 트리 구성 템플릿"""
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
    def list_builtin_templates() -> List[Dict]:
        """내장 템플릿 목록 반환"""
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