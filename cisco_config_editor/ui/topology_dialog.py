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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network_visualizer import (
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
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_visualization)

        self._setup_ui()
        self._create_sample_topology()

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

        # 메인 스플리터
        main_splitter = QSplitter(Qt.Horizontal)

        # 좌측 패널 (장비/링크 목록)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 장비 목록
        device_group = QGroupBox("장비 목록")
        device_layout = QVBoxLayout(device_group)

        self.device_list = QListWidget()
        self.device_list.itemClicked.connect(self._on_device_selected)
        device_layout.addWidget(self.device_list)

        device_button_layout = QHBoxLayout()
        self.btn_edit_device = QPushButton("편집")
        self.btn_remove_device = QPushButton("제거")
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
        self.link_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        link_layout.addWidget(self.link_table)

        link_button_layout = QHBoxLayout()
        self.btn_edit_link = QPushButton("편집")
        self.btn_remove_link = QPushButton("제거")
        link_button_layout.addWidget(self.btn_edit_link)
        link_button_layout.addWidget(self.btn_remove_link)
        link_layout.addLayout(link_button_layout)

        left_layout.addWidget(link_group)

        main_splitter.addWidget(left_panel)

        # 중앙 패널 (토폴로지 시각화)
        center_panel = QWidget()
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
        fig = self.visualizer.create_figure((10, 8))
        canvas = self.visualizer.get_canvas()
        if canvas:
            center_layout.addWidget(canvas)

            # 네비게이션 툴바 (확대/축소, 이동 등)
            if TOOLBAR_AVAILABLE:
                nav_toolbar = NavigationToolbar(canvas, self)
                center_layout.addWidget(nav_toolbar)
        else:
            # 캔버스를 사용할 수 없는 경우 안내 메시지
            no_canvas_label = QLabel("토폴로지 시각화를 위해 matplotlib를 설치하세요.\npip install matplotlib")
            no_canvas_label.setAlignment(Qt.AlignCenter)
            center_layout.addWidget(no_canvas_label)

        main_splitter.addWidget(center_panel)

        # 우측 패널 (정보/분석)
        right_panel = QWidget()
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

        main_splitter.addWidget(right_panel)

        # 분할 비율 설정
        main_splitter.setSizes([250, 700, 250])