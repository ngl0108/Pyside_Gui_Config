# ansible_config_editor/core/ansible_engine.py
import yaml
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime



class AnsibleEngine:
    """
    Windows 환경에서의 개발 편의성을 위한 Mock Ansible 실행 엔진
    및 실제 정보 수집을 위한 Runner 실행 엔진

    - execute_configuration: Mock 모드로 플레이북 실행 결과 시뮬레이션
    - discover_facts: ansible-runner를 사용하여 실제 장비 정보 수집
    """

    def __init__(self):
        self.execution_history = []
        self.mock_mode = True  # 구성 적용은 Mock 모드로 유지

    def discover_facts(self, target_host: str, os_type: str, credentials: Dict[str, str]) -> Tuple[
        bool, Dict[str, Any]]:
        """
        특정 장비에 접속하여 facts 정보를 수집합니다.

        Args:
            target_host: 정보를 수집할 장비의 IP
            os_type: 장비 OS 유형 (플레이북의 when 조건에 사용)
            credentials: {'user': 'myuser', 'pass': 'mypass'} 형태의 인증 정보

        Returns:
            (성공 여부, 수집된 ansible_facts 사전 또는 에러 메시지)
        """
        import ansible_runner
        import tempfile
        import os
        # OS 유형에서 L2/L3 부분을 제거하여 순수 OS 이름만 사용 (예: L2_IOS-XE -> IOS-XE)
        clean_os_type = os_type.split('_')[-1]

        # 임시 인벤토리 파일 생성
        inventory_content = f"[{clean_os_type}]\n{target_host}\n"
        inv_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        inv_file.write(inventory_content)
        inv_file.close()

        playbook_path = 'discover_facts.yml'

        if not os.path.exists(playbook_path):
            return False, {"error": f"Playbook 파일({playbook_path})을 찾을 수 없습니다."}

        try:
            # ansible-runner 실행 (json_mode=True로 설정하여 결과 파싱 용이)
            r = ansible_runner.run(
                private_data_dir=tempfile.mkdtemp(),
                playbook=playbook_path,
                inventory=inv_file.name,
                extravars={
                    "ansible_user": credentials['user'],
                    "ansible_password": credentials['pass'],
                    "ansible_connection": "network_cli"
                },
                json_mode=True,
                quiet=True  # 불필요한 로그 최소화
            )

            if r.status == 'successful':
                for event in r.events:
                    if event['event'] == 'runner_on_ok' and 'ansible_facts' in event['event_data']['res']:
                        return True, event['event_data']['res']['ansible_facts']

            # 실패 시 마지막 이벤트의 stdout에서 원인 확인
            error_output = r.stdout.read().splitlines()[-10:]  # 마지막 10줄
            return False, {"error": f"Ansible 실행 실패: {r.status}", "details": "\n".join(error_output)}

        except Exception as e:
            return False, {"error": f"ansible-runner 실행 중 예외 발생: {str(e)}"}

        finally:
            os.unlink(inv_file.name)  # 임시 인벤토리 파일 삭제

        return False, {"error": "알 수 없는 오류로 정보 수집에 실패했습니다."}

    def execute_configuration(self, target_hosts: List[str], playbook_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        구성을 대상 장비에 적용합니다 (현재는 Mock 실행)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.mock_mode:
            return self._execute_mock(target_hosts, playbook_data, timestamp)
        else:
            return self._execute_real(target_hosts, playbook_data, timestamp)

    def _execute_mock(self, target_hosts: List[str], playbook_data: Dict[str, Any], timestamp: str) -> Tuple[str, str]:
        """Mock 실행 - 플레이북 내용을 분석하여 가상 실행 결과 생성"""
        execution_record = {
            'timestamp': timestamp,
            'hosts': target_hosts,
            'playbook': playbook_data,
            'status': 'mock_successful'
        }
        self.execution_history.append(execution_record)
        playbook_yaml = self._convert_to_yaml(playbook_data)
        task_count = len(playbook_data.get('tasks', []))
        host_count = len(target_hosts)
        mock_output = self._generate_mock_output(target_hosts, playbook_data, task_count)

        final_output = f"""
=== ANSIBLE MOCK EXECUTION REPORT ===
실행 시간: {timestamp}
대상 장비: {', '.join(target_hosts)} ({host_count}대)
총 태스크 수: {task_count}개

=== GENERATED PLAYBOOK (YAML) ===
{playbook_yaml}

=== MOCK EXECUTION RESULTS ===
{mock_output}

=== EXECUTION SUMMARY ===
✓ 모든 태스크가 성공적으로 실행되었습니다 (모의)
✓ {host_count}대 장비에 {task_count}개 태스크 적용 완료
✓ 구성 변경사항이 적용되었습니다 (모의)

주의: 이것은 Mock 실행 결과입니다. 실제 장비에는 적용되지 않았습니다.
"""
        return 'successful', final_output.strip()

    def _execute_real(self, target_hosts: List[str], playbook_data: Dict[str, Any], timestamp: str) -> Tuple[str, str]:
        """실제 ansible-runner를 사용한 실행 (향후 구현)"""
        return 'not_implemented', 'Real execution not implemented yet. Use mock mode.'

    def _convert_to_yaml(self, playbook_data: Dict[str, Any]) -> str:
        """플레이북 데이터를 YAML 문자열로 변환"""
        try:
            playbook_list = [playbook_data]
            return yaml.dump(playbook_list, default_flow_style=False, allow_unicode=True, indent=2)
        except Exception as e:
            return f"YAML 변환 오류: {str(e)}"

    def _generate_mock_output(self, target_hosts: List[str], playbook_data: Dict[str, Any], task_count: int) -> str:
        """가상 실행 결과 생성"""
        output_lines = []
        playbook_name = playbook_data.get('name', 'Unnamed Playbook')
        output_lines.append(f"PLAY [{playbook_name}] {'*' * 50}\n")

        for host in target_hosts:
            output_lines.append(f"TASK [Gathering Facts on {host}] {'*' * 30}")
            output_lines.append(f"ok: [{host}]\n")
            for i, task in enumerate(playbook_data.get('tasks', []), 1):
                task_name = task.get('name', f'Task {i}')
                output_lines.append(f"TASK [{task_name}] {'*' * 30}")
                if 'debug' in task:
                    output_lines.append(f'ok: [{host}] => {{"msg": "{task["debug"].get("msg", "Debug message")}"}}')
                elif any(module in task for module in ['cisco.ios.ios_config', 'cisco.nxos.nxos_config']):
                    config_module = 'cisco.ios.ios_config' if 'cisco.ios.ios_config' in task else 'cisco.nxos.nxos_config'
                    lines_count = len(task[config_module].get('lines', []))
                    output_lines.append(f"changed: [{host}] => (item={lines_count} configuration lines)")
                else:
                    output_lines.append(f"ok: [{host}]")
                output_lines.append("")

        output_lines.append("PLAY RECAP " + "*" * 50)
        for host in target_hosts:
            output_lines.append(
                f"{host:<20} : ok={task_count:<3} changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0")
        return "\n".join(output_lines)

    def get_execution_history(self) -> List[Dict[str, Any]]:
        return self.execution_history

    def clear_execution_history(self):
        self.execution_history = []

    def set_mock_mode(self, mock_enabled: bool):
        self.mock_mode = mock_enabled

    def validate_connectivity(self, target_hosts: List[str]) -> Dict[str, bool]:
        if self.mock_mode:
            return {host: True for host in target_hosts}
        else:
            return {host: False for host in target_hosts}

    def dry_run(self, target_hosts: List[str], playbook_data: Dict[str, Any]) -> Tuple[str, str]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        playbook_yaml = self._convert_to_yaml(playbook_data)
        task_count = len(playbook_data.get('tasks', []))
        dry_run_output = f"=== ANSIBLE DRY-RUN (CHECK MODE) ===\n실행 시간: {timestamp}\n대상 장비: {', '.join(target_hosts)}\n모드: Check Mode (실제 변경 없음)\n\n=== PLAYBOOK TO BE EXECUTED ===\n{playbook_yaml}\n\n=== EXPECTED CHANGES (DRY-RUN) ===\n다음 변경사항들이 적용될 예정입니다:\n\n"
        for i, task in enumerate(playbook_data.get('tasks', []), 1):
            task_name = task.get('name', f'Task {i}')
            dry_run_output += f"{i}. {task_name}\n"
            if 'cisco.ios.ios_config' in task or 'cisco.nxos.nxos_config' in task:
                config_key = 'cisco.ios.ios_config' if 'cisco.ios.ios_config' in task else 'cisco.nxos.nxos_config'
                lines = task[config_key].get('lines', [])
                dry_run_output += f"   - {len(lines)}개의 구성 라인이 추가/변경됩니다\n"
                for line in lines[:3]:
                    dry_run_output += f"     > {line}\n"
                if len(lines) > 3:
                    dry_run_output += f"     ... 및 {len(lines) - 3}개 추가 라인\n"
            else:
                dry_run_output += "   - 정보 수집 또는 검증 태스크\n"
            dry_run_output += "\n"
        dry_run_output += "=== DRY-RUN SUMMARY ===\n✓ 모든 태스크가 성공적으로 실행될 것으로 예상됩니다\n✓ 위 변경사항들이 실제 실행 시 적용됩니다\n⚠ 이것은 Dry-run 결과입니다. 실제 장비에는 아직 적용되지 않았습니다.\n\n실제 적용을 원하시면 '구성 적용' 버튼을 클릭하세요."
        return 'dry_run_successful', dry_run_output.strip()