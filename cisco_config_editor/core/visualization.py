# cisco_config_manager/core/visualization.py
"""
네트워크 토폴로지 시각화 모듈
실시간 네트워크 구조를 그래픽으로 표현
"""

import json
import math
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Warning: NetworkX not installed. Install with: pip install networkx")

try:
    import matplotlib

    matplotlib.use('Qt5Agg')  # PySide6와 호환
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.patches as patches

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib not installed. Install with: pip install matplotlib")


class DeviceType(Enum):
    """네트워크 장비 타입"""
    ROUTER = "router"
    L3_SWITCH = "l3_switch"
    L2_SWITCH = "l2_switch"
    FIREWALL = "firewall"
    ACCESS_POINT = "ap"
    SERVER = "server"
    PC = "pc"
    CLOUD = "cloud"
    UNKNOWN = "unknown"


class LinkType(Enum):
    """링크 타입"""
    ETHERNET = "ethernet"
    FIBER = "fiber"
    WIRELESS = "wireless"
    SERIAL = "serial"
    VIRTUAL = "virtual"


class LinkStatus(Enum):
    """링크 상태"""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class NetworkDevice:
    """네트워크 장비 데이터 클래스"""
    id: str
    name: str
    type: DeviceType
    ip_address: str
    location: Optional[Tuple[float, float]] = None
    status: str = "unknown"
    interfaces: List[Dict] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.interfaces is None:
            self.interfaces = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class NetworkLink:
    """네트워크 링크 데이터 클래스"""
    id: str
    source_device: str
    source_interface: str
    target_device: str
    target_interface: str
    type: LinkType
    bandwidth: Optional[str] = None
    status: LinkStatus = LinkStatus.UNKNOWN
    utilization: float = 0.0
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class NetworkTopology:
    """네트워크 토폴로지 관리 클래스"""

    def __init__(self):
        self.devices: Dict[str, NetworkDevice] = {}
        self.links: Dict[str, NetworkLink] = {}
        self.graph = None

        if NETWORKX_AVAILABLE:
            self.graph = nx.Graph()

    def add_device(self, device: NetworkDevice) -> bool:
        """장비 추가"""
        if device.id in self.devices:
            return False

        self.devices[device.id] = device

        if self.graph is not None:
            self.graph.add_node(
                device.id,
                name=device.name,
                type=device.type.value,
                ip=device.ip_address,
                status=device.status
            )

        return True

    def remove_device(self, device_id: str) -> bool:
        """장비 제거"""
        if device_id not in self.devices:
            return False

        # 관련 링크 제거
        links_to_remove = []
        for link_id, link in self.links.items():
            if link.source_device == device_id or link.target_device == device_id:
                links_to_remove.append(link_id)

        for link_id in links_to_remove:
            self.remove_link(link_id)

        # 장비 제거
        del self.devices[device_id]

        if self.graph is not None:
            self.graph.remove_node(device_id)

        return True

    def add_link(self, link: NetworkLink) -> bool:
        """링크 추가"""
        if link.id in self.links:
            return False

        if link.source_device not in self.devices or link.target_device not in self.devices:
            return False

        self.links[link.id] = link

        if self.graph is not None:
            self.graph.add_edge(
                link.source_device,
                link.target_device,
                id=link.id,
                type=link.type.value,
                bandwidth=link.bandwidth,
                status=link.status.value,
                utilization=link.utilization
            )

        return True

    def remove_link(self, link_id: str) -> bool:
        """링크 제거"""
        if link_id not in self.links:
            return False

        link = self.links[link_id]
        del self.links[link_id]

        if self.graph is not None:
            self.graph.remove_edge(link.source_device, link.target_device)

        return True

    def get_device_neighbors(self, device_id: str) -> List[str]:
        """장비의 이웃 장비 목록 반환"""
        neighbors = []

        for link in self.links.values():
            if link.source_device == device_id:
                neighbors.append(link.target_device)
            elif link.target_device == device_id:
                neighbors.append(link.source_device)

        return list(set(neighbors))

    def calculate_layout(self, layout_type: str = "spring") -> Dict[str, Tuple[float, float]]:
        """토폴로지 레이아웃 계산"""
        if not NETWORKX_AVAILABLE or self.graph is None:
            # 수동 레이아웃
            return self._calculate_manual_layout()

        positions = {}

        if layout_type == "spring":
            positions = nx.spring_layout(self.graph, k=2, iterations=50)
        elif layout_type == "circular":
            positions = nx.circular_layout(self.graph)
        elif layout_type == "hierarchical":
            positions = self._calculate_hierarchical_layout()
        elif layout_type == "kamada":
            positions = nx.kamada_kawai_layout(self.graph)
        else:
            positions = nx.spring_layout(self.graph)

        # 위치 정규화 (0-1 범위로)
        for device_id in positions:
            x, y = positions[device_id]
            positions[device_id] = (x, y)

        return positions

    def _calculate_manual_layout(self) -> Dict[str, Tuple[float, float]]:
        """수동 레이아웃 계산 (NetworkX 없을 때)"""
        positions = {}
        device_count = len(self.devices)

        if device_count == 0:
            return positions

        # 원형 레이아웃
        angle_step = 2 * math.pi / device_count
        radius = 0.4

        for i, device_id in enumerate(self.devices.keys()):
            angle = i * angle_step
            x = 0.5 + radius * math.cos(angle)
            y = 0.5 + radius * math.sin(angle)
            positions[device_id] = (x, y)

        return positions

    def _calculate_hierarchical_layout(self) -> Dict[str, Tuple[float, float]]:
        """계층적 레이아웃 계산"""
        if not self.graph:
            return self._calculate_manual_layout()

        # 장비 타입별로 계층 결정
        layers = {
            DeviceType.ROUTER: 0,
            DeviceType.FIREWALL: 0,
            DeviceType.L3_SWITCH: 1,
            DeviceType.L2_SWITCH: 2,
            DeviceType.ACCESS_POINT: 2,
            DeviceType.SERVER: 3,
            DeviceType.PC: 3,
            DeviceType.CLOUD: -1
        }

        # 계층별로 장비 그룹화
        device_layers = {}
        for device_id, device in self.devices.items():
            layer = layers.get(device.type, 2)
            if layer not in device_layers:
                device_layers[layer] = []
            device_layers[layer].append(device_id)

        # 위치 계산
        positions = {}
        layer_count = len(device_layers)

        for layer_idx, (layer, devices) in enumerate(sorted(device_layers.items())):
            y = 1.0 - (layer_idx / max(layer_count - 1, 1))
            device_count = len(devices)

            for device_idx, device_id in enumerate(devices):
                if device_count == 1:
                    x = 0.5
                else:
                    x = device_idx / (device_count - 1)
                positions[device_id] = (x, y)

        return positions

    def discover_from_cdp(self, cdp_output: str) -> None:
        """CDP 출력에서 토폴로지 자동 탐색"""
        # CDP neighbor 정보 파싱
        lines = cdp_output.split('\n')

        for line in lines:
            if 'Device ID' in line or '---' in line or not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 3:
                neighbor_name = parts[0]
                local_interface = parts[1] + parts[2] if len(parts) > 2 else parts[1]

                # 원격 인터페이스 찾기
                remote_interface = ""
                for i in range(3, len(parts)):
                    if 'Eth' in parts[i] or 'Gig' in parts[i] or 'Fas' in parts[i]:
                        remote_interface = parts[i]
                        break

                # 장비와 링크 추가
                # (실제 구현에서는 더 상세한 파싱 필요)

    def to_json(self) -> str:
        """토폴로지를 JSON으로 변환"""
        topology_data = {
            'devices': [],
            'links': [],
            'metadata': {
                'created': datetime.now().isoformat(),
                'device_count': len(self.devices),
                'link_count': len(self.links)
            }
        }

        for device in self.devices.values():
            topology_data['devices'].append({
                'id': device.id,
                'name': device.name,
                'type': device.type.value,
                'ip_address': device.ip_address,
                'status': device.status,
                'interfaces': device.interfaces,
                'metadata': device.metadata
            })

        for link in self.links.values():
            topology_data['links'].append({
                'id': link.id,
                'source_device': link.source_device,
                'source_interface': link.source_interface,
                'target_device': link.target_device,
                'target_interface': link.target_interface,
                'type': link.type.value,
                'bandwidth': link.bandwidth,
                'status': link.status.value,
                'utilization': link.utilization,
                'metadata': link.metadata
            })

        return json.dumps(topology_data, indent=2)

    def from_json(self, json_str: str) -> None:
        """JSON에서 토폴로지 로드"""
        topology_data = json.loads(json_str)

        # 기존 데이터 초기화
        self.devices.clear()
        self.links.clear()
        if self.graph is not None:
            self.graph.clear()

        # 장비 로드
        for device_data in topology_data.get('devices', []):
            device = NetworkDevice(
                id=device_data['id'],
                name=device_data['name'],
                type=DeviceType(device_data['type']),
                ip_address=device_data['ip_address'],
                status=device_data.get('status', 'unknown'),
                interfaces=device_data.get('interfaces', []),
                metadata=device_data.get('metadata', {})
            )
            self.add_device(device)

        # 링크 로드
        for link_data in topology_data.get('links', []):
            link = NetworkLink(
                id=link_data['id'],
                source_device=link_data['source_device'],
                source_interface=link_data['source_interface'],
                target_device=link_data['target_device'],
                target_interface=link_data['target_interface'],
                type=LinkType(link_data['type']),
                bandwidth=link_data.get('bandwidth'),
                status=LinkStatus(link_data.get('status', 'unknown')),
                utilization=link_data.get('utilization', 0.0),
                metadata=link_data.get('metadata', {})
            )
            self.add_link(link)


class TopologyVisualizer:
    """토폴로지 시각화 클래스"""

    def __init__(self, topology: NetworkTopology):
        self.topology = topology
        self.figure = None
        self.canvas = None
        self.ax = None

        # 장비 타입별 아이콘/색상
        self.device_colors = {
            DeviceType.ROUTER: '#FF6B6B',
            DeviceType.L3_SWITCH: '#4ECDC4',
            DeviceType.L2_SWITCH: '#45B7D1',
            DeviceType.FIREWALL: '#F7B731',
            DeviceType.ACCESS_POINT: '#5F27CD',
            DeviceType.SERVER: '#00D2D3',
            DeviceType.PC: '#A8E6CF',
            DeviceType.CLOUD: '#C7ECEE',
            DeviceType.UNKNOWN: '#95A5A6'
        }

        # 장비 타입별 모양
        self.device_shapes = {
            DeviceType.ROUTER: 's',  # 정사각형
            DeviceType.L3_SWITCH: 'D',  # 다이아몬드
            DeviceType.L2_SWITCH: 'o',  # 원
            DeviceType.FIREWALL: '^',  # 삼각형
            DeviceType.ACCESS_POINT: '*',  # 별
            DeviceType.SERVER: 'H',  # 육각형
            DeviceType.PC: 'p',  # 오각형
            DeviceType.CLOUD: 'h',  # 육각형
            DeviceType.UNKNOWN: 'o'  # 원
        }

        # 링크 상태별 색상
        self.link_colors = {
            LinkStatus.UP: '#2ECC71',
            LinkStatus.DOWN: '#E74C3C',
            LinkStatus.DEGRADED: '#F39C12',
            LinkStatus.UNKNOWN: '#95A5A6'
        }

    def create_figure(self, figsize: Tuple[int, int] = (12, 8)) -> Figure:
        """Figure 생성"""
        if not MATPLOTLIB_AVAILABLE:
            return None

        self.figure = Figure(figsize=figsize, dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        return self.figure

    def draw_topology(self, layout_type: str = "spring", show_labels: bool = True,
                      show_interfaces: bool = False, show_utilization: bool = False):
        """토폴로지 그리기"""
        if not MATPLOTLIB_AVAILABLE or self.ax is None:
            return

        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # 레이아웃 계산
        positions = self.topology.calculate_layout(layout_type)

        # 링크 그리기
        for link in self.topology.links.values():
            self._draw_link(link, positions, show_utilization)

        # 장비 그리기
        for device_id, device in self.topology.devices.items():
            if device_id in positions:
                self._draw_device(device, positions[device_id], show_labels, show_interfaces)

        # 범례 추가
        self._add_legend()

        # 제목 추가
        self.ax.set_title("Network Topology Visualization", fontsize=16, fontweight='bold')

        # 그리드 추가
        self.ax.grid(True, alpha=0.1)

        # 여백 조정
        self.ax.set_xlim(-0.1, 1.1)
        self.ax.set_ylim(-0.1, 1.1)

        if self.canvas:
            self.canvas.draw()

    def _draw_device(self, device: NetworkDevice, position: Tuple[float, float],
                     show_labels: bool, show_interfaces: bool):
        """장비 그리기"""
        x, y = position
        color = self.device_colors.get(device.type, '#95A5A6')
        shape = self.device_shapes.get(device.type, 'o')

        # 상태에 따른 테두리 색상
        edge_color = '#2ECC71' if device.status == 'up' else '#E74C3C'

        # 장비 아이콘 그리기
        self.ax.scatter(x, y, s=500, c=color, marker=shape,
                        edgecolors=edge_color, linewidth=2, zorder=3)

        # 레이블 표시
        if show_labels:
            # 장비 이름
            self.ax.text(x, y - 0.06, device.name, fontsize=9, fontweight='bold',
                         ha='center', va='top')

            # IP 주소
            if device.ip_address:
                self.ax.text(x, y - 0.08, device.ip_address, fontsize=7,
                             ha='center', va='top', color='gray')

        # 인터페이스 표시
        if show_interfaces and device.interfaces:
            interface_text = '\n'.join([f"{iface.get('name', '')}"
                                        for iface in device.interfaces[:3]])
            self.ax.text(x + 0.05, y, interface_text, fontsize=6,
                         ha='left', va='center', color='blue', alpha=0.7)

    def _draw_link(self, link: NetworkLink, positions: Dict[str, Tuple[float, float]],
                   show_utilization: bool):
        """링크 그리기"""
        if link.source_device not in positions or link.target_device not in positions:
            return

        x1, y1 = positions[link.source_device]
        x2, y2 = positions[link.target_device]

        # 링크 색상
        color = self.link_colors.get(link.status, '#95A5A6')

        # 링크 두께 (대역폭에 따라)
        linewidth = 1
        if link.bandwidth:
            if 'G' in link.bandwidth:
                linewidth = 3
            elif 'M' in link.bandwidth:
                linewidth = 2

        # 링크 스타일 (타입에 따라)
        linestyle = '-'
        if link.type == LinkType.WIRELESS:
            linestyle = ':'
        elif link.type == LinkType.VIRTUAL:
            linestyle = '--'

        # 링크 그리기
        self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth,
                     linestyle=linestyle, alpha=0.6, zorder=1)

        # 사용률 표시
        if show_utilization and link.utilization > 0:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            util_text = f"{link.utilization:.0f}%"

            # 높은 사용률 강조
            text_color = '#E74C3C' if link.utilization > 80 else '#F39C12' if link.utilization > 60 else '#2ECC71'

            self.ax.text(mid_x, mid_y, util_text, fontsize=7,
                         ha='center', va='center', color=text_color,
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

        # 대역폭 레이블
        if link.bandwidth:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            offset_x = 0.02
            offset_y = -0.02 if not show_utilization else 0.02
            self.ax.text(mid_x + offset_x, mid_y + offset_y, link.bandwidth,
                         fontsize=6, ha='center', va='center', color='gray', alpha=0.7)

    def _add_legend(self):
        """범례 추가"""
        # 장비 타입 범례
        device_legend = []
        for device_type, color in self.device_colors.items():
            if any(d.type == device_type for d in self.topology.devices.values()):
                device_legend.append(plt.Line2D([0], [0], marker=self.device_shapes[device_type],
                                                color='w', markerfacecolor=color, markersize=10,
                                                label=device_type.value.replace('_', ' ').title()))

        # 링크 상태 범례
        link_legend = []
        for status, color in self.link_colors.items():
            if any(l.status == status for l in self.topology.links.values()):
                link_legend.append(plt.Line2D([0], [0], color=color, linewidth=2,
                                              label=f"Link {status.value}"))

        if device_legend:
            first_legend = self.ax.legend(handles=device_legend, loc='upper left',
                                          title="Device Types", fontsize=8)
            self.ax.add_artist(first_legend)

        if link_legend:
            self.ax.legend(handles=link_legend, loc='upper right',
                           title="Link Status", fontsize=8)

    def save_topology(self, filename: str, dpi: int = 300):
        """토폴로지 이미지 저장"""
        if self.figure:
            self.figure.savefig(filename, dpi=dpi, bbox_inches='tight')

    def get_canvas(self):
        """Qt 캔버스 반환"""
        if not MATPLOTLIB_AVAILABLE:
            return None

        if self.canvas is None and self.figure is not None:
            self.canvas = FigureCanvas(self.figure)

        return self.canvas


class TopologyAnalyzer:
    """토폴로지 분석 클래스"""

    def __init__(self, topology: NetworkTopology):
        self.topology = topology

    def find_single_points_of_failure(self) -> List[str]:
        """단일 장애점 찾기"""
        spof = []

        if not NETWORKX_AVAILABLE or not self.topology.graph:
            return spof

        # 브리지 찾기 (제거 시 네트워크가 분리되는 엣지)
        bridges = list(nx.bridges(self.topology.graph))
        for source, target in bridges:
            spof.append(f"Link between {source} and {target}")

        # 아티큘레이션 포인트 찾기 (제거 시 네트워크가 분리되는 노드)
        articulation_points = list(nx.articulation_points(self.topology.graph))
        for node in articulation_points:
            spof.append(f"Device {node}")

        return spof

    def calculate_redundancy_score(self) -> float:
        """이중화 점수 계산 (0-100)"""
        if not self.topology.devices:
            return 0

        score = 100

        # 단일 장애점당 감점
        spof = self.find_single_points_of_failure()
        score -= len(spof) * 10

        # 단일 업링크 장비당 감점
        for device_id in self.topology.devices:
            neighbors = self.topology.get_device_neighbors(device_id)
            if len(neighbors) == 1:
                score -= 5

        return max(0, min(100, score))

    def find_shortest_path(self, source: str, target: str) -> List[str]:
        """최단 경로 찾기"""
        if not NETWORKX_AVAILABLE or not self.topology.graph:
            return []

        try:
            return nx.shortest_path(self.topology.graph, source, target)
        except nx.NetworkXNoPath:
            return []

    def get_topology_statistics(self) -> Dict[str, Any]:
        """토폴로지 통계"""
        stats = {
            'device_count': len(self.topology.devices),
            'link_count': len(self.topology.links),
            'device_types': {},
            'link_types': {},
            'average_connectivity': 0,
            'redundancy_score': 0,
            'single_points_of_failure': []
        }

        # 장비 타입별 개수
        for device in self.topology.devices.values():
            device_type = device.type.value
            stats['device_types'][device_type] = stats['device_types'].get(device_type, 0) + 1

        # 링크 타입별 개수
        for link in self.topology.links.values():
            link_type = link.type.value
            stats['link_types'][link_type] = stats['link_types'].get(link_type, 0) + 1

        # 평균 연결성
        if stats['device_count'] > 0:
            total_connections = sum(len(self.topology.get_device_neighbors(d))
                                    for d in self.topology.devices)
            stats['average_connectivity'] = total_connections / stats['device_count']

        # 이중화 점수
        stats['redundancy_score'] = self.calculate_redundancy_score()

        # 단일 장애점
        stats['single_points_of_failure'] = self.find_single_points_of_failure()

        return stats


# 테스트 및 예제
if __name__ == "__main__":
    # 토폴로지 생성
    topology = NetworkTopology()

    # 장비 추가
    devices = [
        NetworkDevice("R1", "Core-Router", DeviceType.ROUTER, "10.0.0.1"),
        NetworkDevice("FW1", "Firewall-1", DeviceType.FIREWALL, "10.0.0.2"),
        NetworkDevice("SW1", "Core-Switch-1", DeviceType.L3_SWITCH, "10.0.1.1"),
        NetworkDevice("SW2", "Core-Switch-2", DeviceType.L3_SWITCH, "10.0.1.2"),
        NetworkDevice("SW3", "Access-Switch-1", DeviceType.L2_SWITCH, "10.0.2.1"),
        NetworkDevice("SW4", "Access-Switch-2", DeviceType.L2_SWITCH, "10.0.2.2"),
        NetworkDevice("SRV1", "Server-1", DeviceType.SERVER, "10.0.10.1"),
        NetworkDevice("PC1", "PC-1", DeviceType.PC, "10.0.10.100")
    ]

    for device in devices:
        topology.add_device(device)

    # 링크 추가
    links = [
        NetworkLink("L1", "R1", "Gi0/0", "FW1", "Gi0/0", LinkType.FIBER, "10G", LinkStatus.UP, 45),
        NetworkLink("L2", "FW1", "Gi0/1", "SW1", "Gi0/0", LinkType.FIBER, "10G", LinkStatus.UP, 60),
        NetworkLink("L3", "FW1", "Gi0/2", "SW2", "Gi0/0", LinkType.FIBER, "10G", LinkStatus.UP, 55),
        NetworkLink("L4", "SW1", "Gi0/1", "SW2", "Gi0/1", LinkType.FIBER, "10G", LinkStatus.UP, 30),
        NetworkLink("L5", "SW1", "Gi0/2", "SW3", "Gi0/0", LinkType.ETHERNET, "1G", LinkStatus.UP, 70),
        NetworkLink("L6", "SW2", "Gi0/2", "SW4", "Gi0/0", LinkType.ETHERNET, "1G", LinkStatus.UP, 65),
        NetworkLink("L7", "SW3", "Gi0/1", "SRV1", "eth0", LinkType.ETHERNET, "1G", LinkStatus.UP, 40),
        NetworkLink("L8", "SW4", "Gi0/1", "PC1", "eth0", LinkType.ETHERNET, "1G", LinkStatus.UP, 10)
    ]

    for link in links:
        topology.add_link(link)

    # 분석
    analyzer = TopologyAnalyzer(topology)
    stats = analyzer.get_topology_statistics()

    print("토폴로지 통계:")
    print(f"- 장비 수: {stats['device_count']}")
    print(f"- 링크 수: {stats['link_count']}")
    print(f"- 평균 연결성: {stats['average_connectivity']:.2f}")
    print(f"- 이중화 점수: {stats['redundancy_score']}/100")
    print(f"- 단일 장애점: {len(stats['single_points_of_failure'])}개")

    # 시각화 (Matplotlib 설치 시)
    if MATPLOTLIB_AVAILABLE:
        visualizer = TopologyVisualizer(topology)
        fig = visualizer.create_figure()
        visualizer.draw_topology(layout_type="hierarchical", show_utilization=True)
        # visualizer.save_topology("topology.png")
        print("\n시각화 준비 완료")