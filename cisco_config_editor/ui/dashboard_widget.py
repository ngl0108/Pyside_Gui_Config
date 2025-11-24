# cisco_config_manager/ui/dashboard_widget.py
"""
실시간 모니터링 대시보드
네트워크 상태, 성능 메트릭, 알림을 한눈에 표시
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QGridLayout,
    QFrame, QScrollArea, QTabWidget, QDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QDateTime, QPropertyAnimation
from PySide6.QtGui import QPalette, QColor, QFont, QPainter, QBrush, QPen

import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MetricType(Enum):
    """메트릭 타입"""
    CPU = "cpu"
    MEMORY = "memory"
    BANDWIDTH = "bandwidth"
    PACKET_LOSS = "packet_loss"
    LATENCY = "latency"
    TEMPERATURE = "temperature"


class AlertSeverity(Enum):
    """알림 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DeviceMetric:
    """장비 메트릭 데이터"""
    device_id: str
    device_name: str
    timestamp: datetime
    metric_type: MetricType
    value: float
    unit: str
    threshold_warning: float = 0
    threshold_critical: float = 0


@dataclass
class Alert:
    """알림 데이터"""
    id: str
    timestamp: datetime
    device: str
    severity: AlertSeverity
    message: str
    acknowledged: bool = False


class MetricCollector(QThread):
    """메트릭 수집 스레드"""

    # 시그널 정의
    metric_updated = Signal(DeviceMetric)
    alert_generated = Signal(Alert)

    def __init__(self):
        super().__init__()
        self.running = True
        self.devices = []
        self.collection_interval = 5  # 초

    def add_device(self, device_id: str, device_name: str):
        """모니터링 장비 추가"""
        self.devices.append({'id': device_id, 'name': device_name})

    def run(self):
        """메트릭 수집 실행"""
        alert_counter = 0

        while self.running:
            for device in self.devices:
                # 시뮬레이션된 메트릭 생성
                # 실제로는 SNMP, API 등을 통해 수집

                # CPU 사용률
                cpu_value = random.uniform(20, 90)
                cpu_metric = DeviceMetric(
                    device['id'], device['name'],
                    datetime.now(), MetricType.CPU,
                    cpu_value, "%", 70, 90
                )
                self.metric_updated.emit(cpu_metric)

                # 메모리 사용률
                mem_value = random.uniform(30, 85)
                mem_metric = DeviceMetric(
                    device['id'], device['name'],
                    datetime.now(), MetricType.MEMORY,
                    mem_value, "%", 75, 90
                )
                self.metric_updated.emit(mem_metric)

                # 대역폭 사용률
                bw_value = random.uniform(100, 950)
                bw_metric = DeviceMetric(
                    device['id'], device['name'],
                    datetime.now(), MetricType.BANDWIDTH,
                    bw_value, "Mbps", 800, 950
                )
                self.metric_updated.emit(bw_metric)

                # 알림 생성 (임계값 초과 시)
                if cpu_value > 80:
                    alert_counter += 1
                    alert = Alert(
                        f"ALERT_{alert_counter}",
                        datetime.now(),
                        device['name'],
                        AlertSeverity.WARNING if cpu_value < 90 else AlertSeverity.CRITICAL,
                        f"High CPU usage: {cpu_value:.1f}%"
                    )
                    self.alert_generated.emit(alert)

            self.msleep(self.collection_interval * 1000)

    def stop(self):
        """수집 중지"""
        self.running = False


class MetricCard(QFrame):
    """메트릭 카드 위젯"""

    def __init__(self, title: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.value = 0
        self.threshold_warning = 70
        self.threshold_critical = 90

        self.setFrameStyle(QFrame.Box)
        self.setMinimumHeight(120)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 제목
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)

        # 값
        self.value_label = QLabel("0" + self.unit)
        self.value_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.value_label.setFont(font)
        layout.addWidget(self.value_label)

        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # 상태 레이블
        self.status_label = QLabel("Normal")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def update_value(self, value: float):
        """값 업데이트"""
        self.value = value
        self.value_label.setText(f"{value:.1f}{self.unit}")

        if self.unit == "%":
            self.progress_bar.setValue(int(value))
        else:
            # 다른 단위는 최대값 대비 비율로 표시
            if self.unit == "Mbps":
                max_value = 1000
                self.progress_bar.setValue(int(value / max_value * 100))

        # 상태 색상 업데이트
        if value >= self.threshold_critical:
            self.value_label.setStyleSheet("color: #E74C3C;")  # 빨강
            self.status_label.setText("Critical")
            self.status_label.setStyleSheet("color: #E74C3C;")
        elif value >= self.threshold_warning:
            self.value_label.setStyleSheet("color: #F39C12;")  # 주황
            self.status_label.setText("Warning")
            self.status_label.setStyleSheet("color: #F39C12;")
        else:
            self.value_label.setStyleSheet("color: #27AE60;")  # 초록
            self.status_label.setText("Normal")
            self.status_label.setStyleSheet("color: #27AE60;")


class DeviceStatusWidget(QWidget):
    """장비 상태 위젯"""

    def __init__(self, device_name: str, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.metrics = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 장비명
        name_label = QLabel(self.device_name)
        name_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        name_label.setFont(font)
        layout.addWidget(name_label)

        # 메트릭 카드 그리드
        grid_layout = QGridLayout()

        # CPU 카드
        self.cpu_card = MetricCard("CPU", "%")
        grid_layout.addWidget(self.cpu_card, 0, 0)

        # 메모리 카드
        self.memory_card = MetricCard("Memory", "%")
        grid_layout.addWidget(self.memory_card, 0, 1)

        # 대역폭 카드
        self.bandwidth_card = MetricCard("Bandwidth", "Mbps")
        grid_layout.addWidget(self.bandwidth_card, 1, 0)

        # 온도 카드
        self.temp_card = MetricCard("Temperature", "°C")
        self.temp_card.threshold_warning = 60
        self.temp_card.threshold_critical = 75
        grid_layout.addWidget(self.temp_card, 1, 1)

        layout.addLayout(grid_layout)

    def update_metric(self, metric: DeviceMetric):
        """메트릭 업데이트"""
        if metric.metric_type == MetricType.CPU:
            self.cpu_card.update_value(metric.value)
        elif metric.metric_type == MetricType.MEMORY:
            self.memory_card.update_value(metric.value)
        elif metric.metric_type == MetricType.BANDWIDTH:
            self.bandwidth_card.update_value(metric.value)
        elif metric.metric_type == MetricType.TEMPERATURE:
            self.temp_card.update_value(metric.value)


class AlertListWidget(QWidget):
    """알림 목록 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alerts = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 헤더
        header_layout = QHBoxLayout()
        title_label = QLabel("🔔 Alerts")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)

        self.alert_count_label = QLabel("0 Active")
        header_layout.addWidget(self.alert_count_label)
        header_layout.addStretch()

        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.clear_all_alerts)
        header_layout.addWidget(clear_button)

        layout.addLayout(header_layout)

        # 알림 테이블
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(5)
        self.alert_table.setHorizontalHeaderLabels(["Time", "Device", "Severity", "Message", "Action"])
        self.alert_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.alert_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.alert_table)

    def add_alert(self, alert: Alert):
        """알림 추가"""
        self.alerts.append(alert)

        row = self.alert_table.rowCount()
        self.alert_table.insertRow(row)

        # 시간
        time_item = QTableWidgetItem(alert.timestamp.strftime("%H:%M:%S"))
        self.alert_table.setItem(row, 0, time_item)

        # 장비
        device_item = QTableWidgetItem(alert.device)
        self.alert_table.setItem(row, 1, device_item)

        # 심각도
        severity_item = QTableWidgetItem(alert.severity.value.upper())
        if alert.severity == AlertSeverity.CRITICAL:
            severity_item.setForeground(QColor("#E74C3C"))
        elif alert.severity == AlertSeverity.ERROR:
            severity_item.setForeground(QColor("#E67E22"))
        elif alert.severity == AlertSeverity.WARNING:
            severity_item.setForeground(QColor("#F39C12"))
        else:
            severity_item.setForeground(QColor("#3498DB"))
        self.alert_table.setItem(row, 2, severity_item)

        # 메시지
        message_item = QTableWidgetItem(alert.message)
        self.alert_table.setItem(row, 3, message_item)

        # 액션 버튼
        ack_button = QPushButton("Acknowledge")
        ack_button.clicked.connect(lambda: self.acknowledge_alert(row))
        self.alert_table.setCellWidget(row, 4, ack_button)

        # 카운트 업데이트
        active_count = len([a for a in self.alerts if not a.acknowledged])
        self.alert_count_label.setText(f"{active_count} Active")

        # 스크롤을 최신 항목으로
        self.alert_table.scrollToBottom()

    def acknowledge_alert(self, row: int):
        """알림 확인"""
        if row < len(self.alerts):
            self.alerts[row].acknowledged = True
            self.alert_table.removeRow(row)

            # 카운트 업데이트
            active_count = len([a for a in self.alerts if not a.acknowledged])
            self.alert_count_label.setText(f"{active_count} Active")

    def clear_all_alerts(self):
        """모든 알림 지우기"""
        self.alerts.clear()
        self.alert_table.setRowCount(0)
        self.alert_count_label.setText("0 Active")


class DashboardDialog(QDialog):
    """대시보드 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("실시간 네트워크 대시보드")
        self.setMinimumSize(1400, 900)

        # 메트릭 수집기
        self.collector = MetricCollector()
        self.collector.metric_updated.connect(self._on_metric_updated)
        self.collector.alert_generated.connect(self._on_alert_generated)

        # 장비 상태 위젯 딕셔너리
        self.device_widgets = {}

        self._setup_ui()
        self._add_sample_devices()

        # 수집 시작
        self.collector.start()

    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)

        # 헤더
        header_layout = QHBoxLayout()

        title_label = QLabel("📊 실시간 네트워크 대시보드")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 업데이트 시간
        self.last_update_label = QLabel("마지막 업데이트: -")
        header_layout.addWidget(self.last_update_label)

        # 새로고침 버튼
        refresh_button = QPushButton("🔄 새로고침")
        refresh_button.clicked.connect(self._refresh_dashboard)
        header_layout.addWidget(refresh_button)

        layout.addLayout(header_layout)

        # 메인 스플리터
        main_splitter = QSplitter(Qt.Vertical)

        # 상단: 장비 메트릭
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        # 요약 통계
        summary_group = QGroupBox("네트워크 요약")
        summary_layout = QHBoxLayout(summary_group)

        self.total_devices_card = self._create_summary_card("총 장비", "0")
        self.active_devices_card = self._create_summary_card("활성 장비", "0")
        self.total_alerts_card = self._create_summary_card("알림", "0")
        self.avg_cpu_card = self._create_summary_card("평균 CPU", "0%")
        self.avg_bandwidth_card = self._create_summary_card("평균 대역폭", "0 Mbps")

        summary_layout.addWidget(self.total_devices_card)
        summary_layout.addWidget(self.active_devices_card)
        summary_layout.addWidget(self.total_alerts_card)
        summary_layout.addWidget(self.avg_cpu_card)
        summary_layout.addWidget(self.avg_bandwidth_card)

        top_layout.addWidget(summary_group)

        # 장비 메트릭 스크롤 영역
        device_scroll = QScrollArea()
        device_scroll.setWidgetResizable(True)

        device_container = QWidget()
        self.device_grid_layout = QGridLayout(device_container)
        device_scroll.setWidget(device_container)

        top_layout.addWidget(QLabel("장비별 메트릭:"))
        top_layout.addWidget(device_scroll)

        main_splitter.addWidget(top_widget)

        # 하단: 알림
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)

        self.alert_widget = AlertListWidget()
        bottom_layout.addWidget(self.alert_widget)

        main_splitter.addWidget(bottom_widget)

        # 분할 비율
        main_splitter.setSizes([600, 300])

        layout.addWidget(main_splitter)

        # 하단 버튼
        button_layout = QHBoxLayout()

        self.pause_button = QPushButton("⏸️ 일시정지")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self._toggle_collection)
        button_layout.addWidget(self.pause_button)

        button_layout.addStretch()

        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_summary_card(self, title: str, value: str) -> QFrame:
        """요약 카드 생성"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setMinimumSize(150, 80)

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; color: #7F8C8D;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        value_label.setObjectName("value")  # 나중에 찾기 위한 이름
        layout.addWidget(value_label)

        return card

    def _add_sample_devices(self):
        """샘플 장비 추가"""
        sample_devices = [
            ("CORE-R1", "Core Router 1"),
            ("CORE-SW1", "Core Switch 1"),
            ("DIST-SW1", "Distribution Switch 1"),
            ("ACC-SW1", "Access Switch 1"),
            ("FW1", "Firewall 1"),
            ("SRV1", "Server 1")
        ]

        row, col = 0, 0
        for device_id, device_name in sample_devices:
            # 수집기에 장비 추가
            self.collector.add_device(device_id, device_name)

            # UI에 위젯 추가
            device_widget = DeviceStatusWidget(device_name)
            self.device_widgets[device_id] = device_widget
            self.device_grid_layout.addWidget(device_widget, row, col)

            col += 1
            if col >= 3:  # 3열로 표시
                col = 0
                row += 1

        # 요약 업데이트
        self._update_summary()

    def _on_metric_updated(self, metric: DeviceMetric):
        """메트릭 업데이트 처리"""
        if metric.device_id in self.device_widgets:
            self.device_widgets[metric.device_id].update_metric(metric)

        # 마지막 업데이트 시간
        self.last_update_label.setText(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")

        # 요약 업데이트
        self._update_summary()

    def _on_alert_generated(self, alert: Alert):
        """알림 생성 처리"""
        self.alert_widget.add_alert(alert)

        # 알림 카운트 업데이트
        alert_count = len(self.alert_widget.alerts)
        self.total_alerts_card.findChild(QLabel, "value").setText(str(alert_count))

    def _update_summary(self):
        """요약 통계 업데이트"""
        # 총 장비 수
        total_devices = len(self.device_widgets)
        self.total_devices_card.findChild(QLabel, "value").setText(str(total_devices))

        # 활성 장비 수 (실제로는 연결 상태 확인 필요)
        active_devices = total_devices  # 현재는 모두 활성으로 가정
        self.active_devices_card.findChild(QLabel, "value").setText(str(active_devices))

        # 평균 CPU (샘플 데이터)
        avg_cpu = random.uniform(40, 60)
        self.avg_cpu_card.findChild(QLabel, "value").setText(f"{avg_cpu:.1f}%")

        # 평균 대역폭 (샘플 데이터)
        avg_bandwidth = random.uniform(300, 700)
        self.avg_bandwidth_card.findChild(QLabel, "value").setText(f"{avg_bandwidth:.0f} Mbps")

    def _refresh_dashboard(self):
        """대시보드 새로고침"""
        # 강제 메트릭 수집
        self._update_summary()
        self.last_update_label.setText(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")

    def _toggle_collection(self, checked: bool):
        """수집 일시정지/재개"""
        if checked:
            self.collector.running = False
            self.pause_button.setText("▶️ 재개")
        else:
            self.collector.running = True
            self.pause_button.setText("⏸️ 일시정지")

    def closeEvent(self, event):
        """다이얼로그 종료 시"""
        self.collector.stop()
        self.collector.wait()
        event.accept()