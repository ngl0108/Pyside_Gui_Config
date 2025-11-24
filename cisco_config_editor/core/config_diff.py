# cisco_config_manager/core/config_diff.py
from typing import Dict, List, Any, Tuple
import json


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