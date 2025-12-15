# cisco_config_manager/ui/topology_dialog.py
"""
네트워크 토폴로지 시각화 다이얼로그
대화형 네트워크 다이어그램 표시 및 관리
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QCheckBox, QLabel,
    QSplitter, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QToolBar, QMessageBox, QFileDialog, QInputDialog,
    QTextEdit, QSpinBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QAction

import sys
import os
import json
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.visualization import (
    NetworkTopology, NetworkDevice, NetworkLink,
    DeviceType, LinkType, LinkStatus,
    TopologyVisualizer, TopologyAnalyzer
)

try:
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

    TOOLBAR_AVAILABLE = True
except ImportError:
    TOOLBAR_AVAILABLE = False


class TopologyDialog(QDialog):
    """토폴로지 시각화 다이얼로그"""

    # 시그널 정의
    topology_changed = Signal()
    device_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("네트워크 토폴로지 시각화")
        self.setMinimumSize(1200, 800)

        # 토폴로지 및 시각화 객체
        self.topology = NetworkTopology()
        self.visualizer = TopologyVisualizer(self.topology)
        self.analyzer = TopologyAnalyzer(self.topology)

        # 자동 갱신 타이머
        self.refresh_timer = QTimer(self)  # 부모 지정
        self.refresh_timer.timeout.connect(self._refresh_visualization)

        self._setup_ui()

        # 안전한 초기화: UI가 완전히 로드된 후 데이터 생성
        QTimer.singleShot(0, self._create_sample_topology)

    def _setup_ui(self):
        """UI 설정"""
        main_layout = QVBoxLayout(self)

        # 툴바
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # 툴바 액션
        add_device_action = toolbar.addAction("➕ 장비 추가")
        add_device_action.triggered.connect(self._add_device)

        add_link_action = toolbar.addAction("🔗 링크 추가")
        add_link_action.triggered.connect(self._add_link)

        toolbar.addSeparator()

        save_action = toolbar.addAction("💾 저장")
        save_action.triggered.connect(self._save_topology)

        load_action = toolbar.addAction("📂 불러오기")
        load_action.triggered.connect(self._load_topology)

        export_action = toolbar.addAction("📷 이미지 저장")
        export_action.triggered.connect(self._export_image)

        toolbar.addSeparator()

        analyze_action = toolbar.addAction("🔍 분석")
        analyze_action.triggered.connect(self._analyze_topology)

        main_layout.addWidget(toolbar)

        # [중요 수정] QSplitter에 self(부모)를 지정하여 메모리 해제 방지
        main_splitter = QSplitter(Qt.Horizontal, self)

        # 좌측 패널 (장비/링크 목록)
        left_panel = QWidget(self)  # 부모 지정
        left_layout = QVBoxLayout(left_panel)

        # 장비 목록
        device_group = QGroupBox("장비 목록")
        device_layout = QVBoxLayout(device_group)

        self.device_list = QListWidget()
        self.device_list.itemClicked.connect(self._on_device_selected)
        device_layout.addWidget(self.device_list)

        device_button_layout = QHBoxLayout()
        self.btn_edit_device = QPushButton("편집")
        self.btn_edit_device.clicked.connect(self._edit_device)
        self.btn_remove_device = QPushButton("제거")
        self.btn_remove_device.clicked.connect(self._remove_device)
        device_button_layout.addWidget(self.btn_edit_device)
        device_button_layout.addWidget(self.btn_remove_device)
        device_layout.addLayout(device_button_layout)

        left_layout.addWidget(device_group)

        # 링크 목록
        link_group = QGroupBox("링크 목록")
        link_layout = QVBoxLayout(link_group)

        self.link_table = QTableWidget()
        self.link_table.setColumnCount(4)
        self.link_table.setHorizontalHeaderLabels(["Source", "Target", "Type", "Status"])
        # QHeaderView.ResizeMode 사용 (PySide6 호환)
        self.link_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        link_layout.addWidget(self.link_table)

        link_button_layout = QHBoxLayout()
        self.btn_edit_link = QPushButton("편집")
        self.btn_edit_link.clicked.connect(self._edit_link)
        self.btn_remove_link = QPushButton("제거")
        self.btn_remove_link.clicked.connect(self._remove_link)
        link_button_layout.addWidget(self.btn_edit_link)
        link_button_layout.addWidget(self.btn_remove_link)
        link_layout.addLayout(link_button_layout)

        left_layout.addWidget(link_group)

        main_splitter.addWidget(left_panel)

        # 중앙 패널 (토폴로지 시각화)
        center_panel = QWidget(self)  # 부모 지정
        center_layout = QVBoxLayout(center_panel)

        # 시각화 옵션
        options_layout = QHBoxLayout()

        options_layout.addWidget(QLabel("레이아웃:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["spring", "hierarchical", "circular", "kamada"])
        self.layout_combo.currentTextChanged.connect(self._on_layout_changed)
        options_layout.addWidget(self.layout_combo)

        self.cb_show_labels = QCheckBox("레이블 표시")
        self.cb_show_labels.setChecked(True)
        self.cb_show_labels.toggled.connect(self._refresh_visualization)
        options_layout.addWidget(self.cb_show_labels)

        self.cb_show_interfaces = QCheckBox("인터페이스 표시")
        self.cb_show_interfaces.toggled.connect(self._refresh_visualization)
        options_layout.addWidget(self.cb_show_interfaces)

        self.cb_show_utilization = QCheckBox("사용률 표시")
        self.cb_show_utilization.setChecked(True)
        self.cb_show_utilization.toggled.connect(self._refresh_visualization)
        options_layout.addWidget(self.cb_show_utilization)

        options_layout.addWidget(QLabel("자동 갱신:"))
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(0, 60)
        self.refresh_spin.setValue(0)
        self.refresh_spin.setSuffix(" 초")
        self.refresh_spin.valueChanged.connect(self._on_refresh_changed)
        options_layout.addWidget(self.refresh_spin)

        options_layout.addStretch()

        center_layout.addLayout(options_layout)

        # 캔버스
        try:
            fig = self.visualizer.create_figure((10, 8))
            canvas = self.visualizer.get_canvas()
            if canvas:
                center_layout.addWidget(canvas)

                # 네비게이션 툴바 (확대/축소, 이동 등)
                if TOOLBAR_AVAILABLE:
                    nav_toolbar = NavigationToolbar(canvas, self)
                    center_layout.addWidget(nav_toolbar)
            else:
                raise ImportError("Canvas creation failed")
        except Exception:
            # 캔버스를 사용할 수 없는 경우 안내 메시지
            no_canvas_label = QLabel("토폴로지 시각화를 위해 matplotlib와 networkx를 설치하세요.\npip install matplotlib networkx")
            no_canvas_label.setAlignment(Qt.AlignCenter)
            no_canvas_label.setStyleSheet("color: red; font-weight: bold;")
            center_layout.addWidget(no_canvas_label)

        main_splitter.addWidget(center_panel)

        # 우측 패널 (정보/분석)
        right_panel = QWidget(self)  # 부모 지정
        right_layout = QVBoxLayout(right_panel)

        # 토폴로지 통계
        stats_group = QGroupBox("토폴로지 통계")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(200)
        stats_layout.addWidget(self.stats_text)

        right_layout.addWidget(stats_group)

        # 선택된 장비 정보
        device_info_group = QGroupBox("장비 정보")
        device_info_layout = QVBoxLayout(device_info_group)

        self.device_info_text = QTextEdit()
        self.device_info_text.setReadOnly(True)
        device_info_layout.addWidget(self.device_info_text)

        right_layout.addWidget(device_info_group)

        # 분석 결과
        analysis_group = QGroupBox("토폴로지 분석")
        analysis_layout = QVBoxLayout(analysis_group)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_text)

        right_layout.addWidget(analysis_group)

        # 분할 비율 설정
        main_splitter.setSizes([250, 700, 250])
        main_layout.addWidget(main_splitter)

    # --- 샘플 데이터 생성 ---
    def _create_sample_topology(self):
        """샘플 토폴로지 데이터 생성"""
        # 장비 추가
        devices = [
            NetworkDevice("R1", "Core-Router", DeviceType.ROUTER, "10.0.0.1"),
            NetworkDevice("FW1", "Firewall", DeviceType.FIREWALL, "10.0.0.2"),
            NetworkDevice("SW1", "Dist-Switch-1", DeviceType.L3_SWITCH, "10.0.1.1"),
            NetworkDevice("SW2", "Dist-Switch-2", DeviceType.L3_SWITCH, "10.0.1.2"),
            NetworkDevice("ACC1", "Access-1", DeviceType.L2_SWITCH, "10.0.2.1"),
            NetworkDevice("ACC2", "Access-2", DeviceType.L2_SWITCH, "10.0.2.2"),
            NetworkDevice("SRV1", "Web-Server", DeviceType.SERVER, "10.0.10.1"),
            NetworkDevice("PC1", "Admin-PC", DeviceType.PC, "10.0.20.100")
        ]

        for dev in devices:
            dev.status = "up"
            self.topology.add_device(dev)

        # 링크 추가
        links = [
            NetworkLink("L1", "R1", "Gi0/0", "FW1", "Gi0/0", LinkType.FIBER, "10G", LinkStatus.UP),
            NetworkLink("L2", "FW1", "Gi0/1", "SW1", "Gi0/0", LinkType.FIBER, "10G", LinkStatus.UP),
            NetworkLink("L3", "FW1", "Gi0/2", "SW2", "Gi0/0", LinkType.FIBER, "10G", LinkStatus.UP),
            NetworkLink("L4", "SW1", "Gi0/1", "SW2", "Gi0/1", LinkType.FIBER, "10G", LinkStatus.UP),
            NetworkLink("L5", "SW1", "Gi0/2", "ACC1", "Gi0/1", LinkType.ETHERNET, "1G", LinkStatus.UP),
            NetworkLink("L6", "SW2", "Gi0/2", "ACC2", "Gi0/1", LinkType.ETHERNET, "1G", LinkStatus.UP),
            NetworkLink("L7", "ACC1", "Fa0/1", "SRV1", "Eth0", LinkType.ETHERNET, "1G", LinkStatus.UP),
            NetworkLink("L8", "ACC2", "Fa0/1", "PC1", "Eth0", LinkType.ETHERNET, "1G", LinkStatus.UP),
        ]

        for link in links:
            self.topology.add_link(link)

        self._update_lists()
        self._refresh_visualization()

    # --- 핵심 기능: 시각화 갱신 ---
    def _refresh_visualization(self):
        """토폴로지 시각화 갱신"""
        # [수정] 캔버스 유무 확인
        if not hasattr(self, 'layout_combo') or not hasattr(self.visualizer, 'figure'):
            return

        layout_type = self.layout_combo.currentText()
        show_labels = self.cb_show_labels.isChecked()
        show_interfaces = self.cb_show_interfaces.isChecked()
        show_utilization = self.cb_show_utilization.isChecked()

        self.visualizer.draw_topology(
            layout_type=layout_type,
            show_labels=show_labels,
            show_interfaces=show_interfaces,
            show_utilization=show_utilization
        )

        self._update_stats()

    def _on_layout_changed(self, layout_name):
        """레이아웃 변경 시 호출"""
        self._refresh_visualization()

    def _on_refresh_changed(self, value):
        """자동 갱신 설정 변경"""
        if value > 0:
            self.refresh_timer.start(value * 1000)
        else:
            self.refresh_timer.stop()

    # --- 데이터 관리 및 업데이트 ---
    def _update_lists(self):
        """장비 및 링크 목록 UI 업데이트"""
        if not hasattr(self, 'device_list'): return

        # 장비 목록 갱신
        self.device_list.clear()
        for device_id, device in self.topology.devices.items():
            item = QListWidgetItem(f"{device.name} ({device.type.value})")
            item.setData(Qt.UserRole, device_id)
            self.device_list.addItem(item)

        # 링크 목록 갱신
        self.link_table.setRowCount(0)
        for link_id, link in self.topology.links.items():
            row = self.link_table.rowCount()
            self.link_table.insertRow(row)

            self.link_table.setItem(row, 0, QTableWidgetItem(link.source_device))
            self.link_table.setItem(row, 1, QTableWidgetItem(link.target_device))
            self.link_table.setItem(row, 2, QTableWidgetItem(link.type.value))
            self.link_table.setItem(row, 3, QTableWidgetItem(link.status.value))

    def _update_stats(self):
        """통계 정보 업데이트"""
        try:
            # [중요 수정] UI 객체 생존 여부 확인
            if not hasattr(self, 'stats_text') or not self.stats_text:
                return

            # C++ 객체 삭제 여부 확인 시도 (RuntimeError 방지용 try-except 사용)
            stats = self.analyzer.get_topology_statistics()
            text = f"총 장비 수: {stats.get('device_count', 0)}\n"
            text += f"총 링크 수: {stats.get('link_count', 0)}\n"
            text += f"평균 연결성: {stats.get('average_connectivity', 0):.2f}\n"
            text += f"이중화 점수: {stats.get('redundancy_score', 0)}\n"

            self.stats_text.setText(text)
        except RuntimeError:
            # 위젯이 이미 삭제된 경우 무시
            pass
        except Exception as e:
            print(f"Stats update warning: {e}")

    def _on_device_selected(self, item):
        """장비 선택 시 정보 표시"""
        device_id = item.data(Qt.UserRole)
        device = self.topology.devices.get(device_id)

        if device:
            info = f"ID: {device.id}\n"
            info += f"이름: {device.name}\n"
            info += f"타입: {device.type.value}\n"
            info += f"IP: {device.ip_address}\n"
            info += f"상태: {device.status}\n"

            self.device_info_text.setText(info)
            self.device_selected.emit(device_id)

    def _analyze_topology(self):
        """토폴로지 분석 실행"""
        try:
            spof = self.analyzer.find_single_points_of_failure()

            result = "=== 단일 장애점 (SPOF) ===\n"
            if spof:
                for point in spof:
                    result += f"- {point}\n"
            else:
                result += "발견된 단일 장애점이 없습니다.\n"

            self.analysis_text.setText(result)
        except Exception as e:
            self.analysis_text.setText(f"분석 중 오류 발생: {str(e)}")

    # --- CRUD 동작 (구현 예시) ---
    def _add_device(self):
        QMessageBox.information(self, "알림", "장비 추가 기능은 구현 예정입니다.")

    def _add_link(self):
        QMessageBox.information(self, "알림", "링크 추가 기능은 구현 예정입니다.")

    def _edit_device(self):
        pass

    def _remove_device(self):
        pass

    def _edit_link(self):
        pass

    def _remove_link(self):
        pass

    def _save_topology(self):
        """토폴로지 저장"""
        filename, _ = QFileDialog.getSaveFileName(self, "토폴로지 저장", "", "JSON Files (*.json)")
        if filename:
            try:
                json_data = self.topology.to_json()
                with open(filename, 'w') as f:
                    f.write(json_data)
                QMessageBox.information(self, "성공", "저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"저장 실패: {str(e)}")

    def _load_topology(self):
        """토폴로지 불러오기"""
        filename, _ = QFileDialog.getOpenFileName(self, "토폴로지 열기", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    json_data = f.read()
                self.topology.from_json(json_data)
                self._update_lists()
                self._refresh_visualization()
            except Exception as e:
                QMessageBox.critical(self, "오류", f"불러오기 실패: {str(e)}")

    def _export_image(self):
        """이미지로 내보내기"""
        if not self.visualizer.figure:
            return

        filename, _ = QFileDialog.getSaveFileName(self, "이미지 저장", "", "PNG Files (*.png);;JPEG Files (*.jpg)")
        if filename:
            try:
                self.visualizer.save_topology(filename)
                QMessageBox.information(self, "성공", "이미지가 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"이미지 저장 실패: {str(e)}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = TopologyDialog()
    dialog.show()
    sys.exit(app.exec())