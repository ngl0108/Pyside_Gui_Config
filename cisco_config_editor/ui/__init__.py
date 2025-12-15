# cisco_config_manager/ui/tabs/__init__.py
"""
구성 탭 모듈 패키지
"""

from .tabs.interface_tab import InterfaceTab
from .tabs.vlan_tab import VlanTab
from .tabs.routing_tab import RoutingTab
from .tabs.switching_tab import SwitchingTab
from .tabs.security_tab import SecurityTab
from .tabs.acl_tab import AclTab
from .tabs.ha_tab import HaTab
from .tabs.global_tab import GlobalTab

__all__ = [
    'InterfaceTab',
    'VlanTab',
    'RoutingTab',
    'SwitchingTab',
    'SecurityTab',
    'AclTab',
    'HaTab',
    'GlobalTab'
]