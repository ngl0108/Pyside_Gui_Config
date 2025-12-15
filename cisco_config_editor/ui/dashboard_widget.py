# cisco_config_manager/ui/dashboard_widget.py
"""
실시간 모니터링 대시보드 (최종 버전 - ConnectionManager 연동)
네트워크 상태, 성능 메트릭, 알림을 한눈에 표시
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter,
    QScrollArea, QGridLayout, QFrame, QDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QColor, QFont

import random
from datetime import datetime
from typing import Dict
from dataclasses import dataclass
from enum import Enum


# --- 데이터 모델 ---
class MetricType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    BANDWIDTH = "bandwidth"
    TEMPERATURE = "temperature"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DeviceMetric:
    device_id: str
    device_name: str
    timestamp: datetime
    metric_type: MetricType
    value: float
    unit: str


@dataclass
class Alert:
    id: str
    timestamp: datetime
    device: str
    severity: AlertSeverity
    message: str
    acknowledged: bool = False


# --- 백그라운드 수집기 (시뮬레이션) ---
class MetricCollector(QThread):
    """메트릭 수집 스레드 (데모용)"""
    metric_updated = Signal(DeviceMetric)
    alert_generated = Signal(Alert)

    def __init__(self):
        super().__init__()
        self.running = True
        self.devices = []
        self.collection_interval = 3  # 3초마다 갱신

    def add_device(self, device_id: str, device_name: str):
        """모니터링 장비 추가"""
        if not any(d['id'] == device_id for d in self.devices):
            self.devices.append({'id': device_id, 'name': device_name})

    def run(self):
        alert_counter = 0
        while self.running:
            for device in self.devices:
                # 1. CPU 사용률
                cpu_value = random.uniform(10, 95)
                self.metric_updated.emit(
                    DeviceMetric(device['id'], device['name'], datetime.now(), MetricType.CPU, cpu_value, "%"))

                # 2. 메모리 사용률
                mem_value = random.uniform(30, 85)
                self.metric_updated.emit(
                    DeviceMetric(device['id'], device['name'], datetime.now(), MetricType.MEMORY, mem_value, "%"))

                # 3. 대역폭 사용률
                bw_value = random.uniform(100, 950)
                self.metric_updated.emit(
                    DeviceMetric(device['id'], device['name'], datetime.now(), MetricType.BANDWIDTH, bw_value, "Mbps"))

                # 4. 알림 생성 (CPU 90% 이상 시 CRITICAL)
                if cpu_value > 90 and random.random() > 0.5:
                    alert_counter += 1
                    alert = Alert(
                        f"ALERT_{alert_counter}", datetime.now(), device['name'],
                        AlertSeverity.CRITICAL, f"CPU Critical: {cpu_value:.1f}%"
                    )
                    self.alert_generated.emit(alert)

            self.msleep(self.collection_interval * 1000)

    def stop(self):
        self.running = False


# --- UI 컴포넌트 ---
class MetricCard(QFrame):
    """개별 메트릭 표시 카드"""

    def __init__(self, title: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self.unit = unit
        self.value = 0
        self.threshold_warning = 70
        self.threshold_critical = 90

        # 스타일 (다크 모드 기준)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #2a2a2a;
            }
            QLabel { color: #ccc; }
        """)
        self._setup_ui(title)

    def _setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 제목
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # 값
        self.value_label = QLabel(f"0{self.unit}")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setFont(QFont("Arial", 20, QFont.Bold))
        layout.addWidget(self.value_label)

        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

    def update_value(self, value: float):
        """값 업데이트 및 상태 색상 적용"""
        self.value = value
        self.value_label.setText(f"{value:.1f}{self.unit}")

        # 프로그레스 바 값 설정 (Mbps는 1000Mbps 기준)
        if self.unit == "Mbps":
            progress_val = int(min(value / 1000 * 100, 100))
        else:
            progress_val = int(value)
        self.progress_bar.setValue(progress_val)

        # 상태 색상 로직
        color = "#2ecc71"  # Green (Normal)
        if value >= self.threshold_critical:
            color = "#e74c3c"  # Red (Critical)
        elif value >= self.threshold_warning:
            color = "#f1c40f"  # Yellow (Warning)

        self.value_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: #3e3e3e;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)


class DeviceStatusWidget(QGroupBox):
    """장비 하나에 대한 통합 상태 위젯"""

    def __init__(self, device_name: str, parent=None):
        super().__init__(device_name, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                color: #ecf0f1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)

        self.cpu_card = MetricCard("CPU", "%")
        self.memory_card = MetricCard("Memory", "%")
        self.bandwidth_card = MetricCard("Traffic", "Mbps")

        # 온도 카드는 임계값 조정
        self.temp_card = MetricCard("Temp", "°C")
        self.temp_card.threshold_warning = 60
        self.temp_card.threshold_critical = 75

        layout.addWidget(self.cpu_card, 0, 0)
        layout.addWidget(self.memory_card, 0, 1)
        layout.addWidget(self.bandwidth_card, 1, 0)
        layout.addWidget(self.temp_card, 1, 1)

    def update_metric(self, metric: DeviceMetric):
        """메트릭 타입에 따라 적절한 카드 업데이트"""
        if metric.metric_type == MetricType.CPU:
            self.cpu_card.update_value(metric.value)
        elif metric.metric_type == MetricType.MEMORY:
            self.memory_card.update_value(metric.value)
        elif metric.metric_type == MetricType.BANDWIDTH:
            self.bandwidth_card.update_value(metric.value)
        elif metric.metric_type == MetricType.TEMPERATURE:
            self.temp_card.update_value(metric.value)


class AlertListWidget(QWidget):
    """하단 알림 로그 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alerts = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 헤더
        header = QHBoxLayout()
        header.addWidget(QLabel("🔔 최근 알림"))

        self.btn_clear = QPushButton("모두 지우기")
        self.btn_clear.clicked.connect(self.clear_alerts)
        header.addWidget(self.btn_clear)
        header.addStretch()

        layout.addLayout(header)

        # 테이블
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Device", "Severity", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("background-color: #2b2b2b; color: white; gridline-color: #555;")
        layout.addWidget(self.table)

    def add_alert(self, alert: Alert):
        """알림 행 추가"""
        self.alerts.append(alert)
        row = self.table.rowCount()
        self.table.insertRow(row)

        time_item = QTableWidgetItem(alert.timestamp.strftime("%H:%M:%S"))
        dev_item = QTableWidgetItem(alert.device)

        sev_text = alert.severity.value.upper()
        sev_item = QTableWidgetItem(sev_text)

        # 심각도별 색상
        if alert.severity == AlertSeverity.CRITICAL:
            sev_item.setForeground(QColor("#e74c3c"))
        elif alert.severity == AlertSeverity.WARNING:
            sev_item.setForeground(QColor("#f1c40f"))
        else:
            sev_item.setForeground(QColor("#3498db"))

        msg_item = QTableWidgetItem(alert.message)

        self.table.setItem(row, 0, time_item)
        self.table.setItem(row, 1, dev_item)
        self.table.setItem(row, 2, sev_item)
        self.table.setItem(row, 3, msg_item)

        self.table.scrollToBottom()

    def clear_alerts(self):
        self.alerts.clear()
        self.table.setRowCount(0)


# --- 메인 다이얼로그 ---
class DashboardDialog(QDialog):
    """메인 대시보드 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("실시간 네트워크 대시보드")
        self.setMinimumSize(1400, 900)

        # 부모(MainWindow)의 connection_manager에 안전하게 접근
        self.device_manager = getattr(parent, 'connection_manager', None)
        self.device_widgets = {}

        self.collector = MetricCollector()
        self.collector.metric_updated.connect(self._on_metric_updated)
        self.collector.alert_generated.connect(self._on_alert_generated)

        self._setup_ui()
        self._init_devices()  # 장비 목록 초기화

        # 수집 시작
        self.collector.start()

    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)

        # 헤더 (제목, 마지막 업데이트, 버튼)
        header_layout = QHBoxLayout()
        title_label = QLabel("📊 실시간 네트워크 대시보드")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.last_update_label = QLabel("마지막 업데이트: -")
        header_layout.addWidget(self.last_update_label)

        refresh_button = QPushButton("🔄 강제 갱신")
        refresh_button.clicked.connect(self._refresh_dashboard)
        header_layout.addWidget(refresh_button)

        self.pause_button = QPushButton("⏸️ 일시정지")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self._toggle_collection)
        header_layout.addWidget(self.pause_button)

        layout.addLayout(header_layout)

        # 메인 스플리터
        main_splitter = QSplitter(Qt.Vertical)

        # 상단: 장비 메트릭 (스크롤 가능)
        device_scroll = QScrollArea()
        device_scroll.setWidgetResizable(True)
        device_container = QWidget()
        self.device_grid_layout = QGridLayout(device_container)
        device_scroll.setWidget(device_container)
        main_splitter.addWidget(device_scroll)

        # 하단: 알림 로그
        self.alert_widget = AlertListWidget()
        main_splitter.addWidget(self.alert_widget)

        main_splitter.setSizes([700, 300])  # 상:하 비율
        layout.addWidget(main_splitter)

    def _init_devices(self):
        """[핵심] 등록된 장비 목록을 가져와 대시보드에 추가"""
        devices_to_monitor = []

        if self.device_manager and self.device_manager.device_list:
            # 1. 실제 등록된 장비 사용
            for dev in self.device_manager.device_list:
                # ConnectionManager의 Device 클래스가 'host'와 'name' 속성을 가진다고 가정
                devices_to_monitor.append((dev.host, dev.name))

        # 2. 등록된 장비가 없으면 데모 장비 사용
        if not devices_to_monitor:
            devices_to_monitor = [
                ("10.1.1.1", "Demo-Router"),
                ("10.1.1.2", "Demo-Switch"),
                ("10.1.1.3", "Demo-Firewall")
            ]

        # UI 생성 및 수집기 등록
        row, col = 0, 0
        for dev_id, dev_name in devices_to_monitor:
            # 수집기에 등록 (실제 데이터를 가져올 ID와 표시할 Name)
            self.collector.add_device(dev_id, dev_name)

            # UI 위젯 생성
            widget = DeviceStatusWidget(dev_name)
            self.device_widgets[dev_id] = widget
            self.device_grid_layout.addWidget(widget, row, col)

            col += 1
            if col >= 3:  # 한 줄에 최대 3개 표시
                col = 0
                row += 1

    def _on_metric_updated(self, metric: DeviceMetric):
        """메트릭 업데이트 처리"""
        if metric.device_id in self.device_widgets:
            self.device_widgets[metric.device_id].update_metric(metric)

        self.last_update_label.setText(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")

    def _on_alert_generated(self, alert: Alert):
        """알림 생성 처리"""
        self.alert_widget.add_alert(alert)

    def _refresh_dashboard(self):
        """강제 새로고침 (데모에서는 타이머를 리셋하는 효과)"""
        self.last_update_label.setText(f"강제 갱신됨: {datetime.now().strftime('%H:%M:%S')}")
        # 실제로는 여기서 collector의 강제 run 호출 또는 데이터 요청 로직 필요

    def _toggle_collection(self, checked: bool):
        """수집 일시정지/재개"""
        if checked:
            self.collector.running = False
            self.pause_button.setText("▶️ 재개")
        else:
            self.collector.running = True
            self.collector.start()  # 중지된 경우 다시 시작
            self.pause_button.setText("⏸️ 일시정지")

    def closeEvent(self, event):
        """다이얼로그 종료 시 스레드 종료"""
        self.collector.stop()
        self.collector.wait()
        event.accept()