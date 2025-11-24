# cisco_config_manager/ui/tabs/acl_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
    QTableWidget, QPushButton, QHeaderView, QCheckBox,
    QComboBox, QScrollArea, QHBoxLayout, QLabel, QAbstractItemView,
    QTableWidgetItem
)
from PySide6.QtCore import Qt


class AclTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. ACL 목록 관리
        acl_list_group = QGroupBox("1. ACL 목록")
        acl_list_layout = QVBoxLayout(acl_list_group)

        self.acl_list_table = QTableWidget(0, 3)
        self.acl_list_table.setHorizontalHeaderLabels(["Name/Number", "Type", "Description"])
        self.acl_list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.acl_list_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.acl_list_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.acl_list_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.acl_list_table.setSelectionMode(QAbstractItemView.SingleSelection)

        acl_list_btn_layout = QHBoxLayout()
        self.btn_add_acl = QPushButton("ACL 추가")
        self.btn_remove_acl = QPushButton("ACL 삭제")
        acl_list_btn_layout.addWidget(self.btn_add_acl)
        acl_list_btn_layout.addWidget(self.btn_remove_acl)

        acl_list_layout.addLayout(acl_list_btn_layout)
        acl_list_layout.addWidget(self.acl_list_table)
        main_layout.addWidget(acl_list_group)

        # 2. ACL 규칙 (ACE) 관리
        self.acl_rule_group = QGroupBox("2. ACL 규칙 (ACE)")
        acl_rule_layout = QVBoxLayout(self.acl_rule_group)

        self.acl_rule_label = QLabel("상단 목록에서 규칙을 수정할 ACL을 선택하세요.")
        self.acl_rule_label.setAlignment(Qt.AlignCenter)

        self.acl_rule_table = QTableWidget(0, 8)
        self.acl_rule_table.setHorizontalHeaderLabels([
            "Seq", "Action", "Protocol", "Source IP/Mask",
            "Dest IP/Mask", "Src Port", "Dest Port", "Options"
        ])
        # 컬럼 너비 조절
        self.acl_rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.acl_rule_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.acl_rule_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        acl_rule_btn_layout = QHBoxLayout()
        self.btn_add_rule = QPushButton("규칙 추가")
        self.btn_remove_rule = QPushButton("규칙 삭제")
        acl_rule_btn_layout.addWidget(self.btn_add_rule)
        acl_rule_btn_layout.addWidget(self.btn_remove_rule)

        acl_rule_layout.addWidget(self.acl_rule_label)
        acl_rule_layout.addLayout(acl_rule_btn_layout)
        acl_rule_layout.addWidget(self.acl_rule_table)

        self.acl_rule_group.setEnabled(False)
        main_layout.addWidget(self.acl_rule_group)

        # 3. ACL 적용 정보
        acl_apply_group = QGroupBox("3. ACL 적용 정보")
        acl_apply_layout = QVBoxLayout(acl_apply_group)

        apply_info = QLabel("아래에서 ACL을 적용할 인터페이스와 방향을 선택하세요.")
        acl_apply_layout.addWidget(apply_info)

        apply_form = QFormLayout()
        self.combo_acl_interface = QComboBox()
        self.combo_acl_interface.addItems(["-- 인터페이스 선택 --", "GigabitEthernet0/0", "GigabitEthernet0/1", "Vlan1"])

        self.combo_acl_direction = QComboBox()
        self.combo_acl_direction.addItems(["IN", "OUT"])

        self.combo_acl_name = QComboBox()
        self.combo_acl_name.addItems(["-- ACL 선택 --"])

        self.btn_apply_acl = QPushButton("인터페이스에 ACL 적용")

        apply_form.addRow("인터페이스:", self.combo_acl_interface)
        apply_form.addRow("방향:", self.combo_acl_direction)
        apply_form.addRow("ACL 이름:", self.combo_acl_name)
        apply_form.addRow(self.btn_apply_acl)

        acl_apply_layout.addLayout(apply_form)
        main_layout.addWidget(acl_apply_group)

        # 4. ACL 요약
        acl_summary_group = QGroupBox("4. ACL 요약")
        summary_layout = QVBoxLayout(acl_summary_group)

        self.acl_summary_label = QLabel("총 0개의 ACL이 구성되었습니다.")
        summary_layout.addWidget(self.acl_summary_label)

        main_layout.addWidget(acl_summary_group)

        main_layout.addStretch()

    def update_acl_summary(self):
        """ACL 요약 업데이트"""
        acl_count = self.acl_list_table.rowCount()
        total_rules = 0

        for row in range(acl_count):
            name_item = self.acl_list_table.item(row, 0)
            if name_item:
                rules = name_item.data(Qt.UserRole) or []
                total_rules += len(rules)

        self.acl_summary_label.setText(
            f"총 {acl_count}개의 ACL, {total_rules}개의 규칙이 구성되었습니다."
        )

    def refresh_acl_combo(self):
        """ACL 콤보박스 새로고침"""
        self.combo_acl_name.clear()
        self.combo_acl_name.addItem("-- ACL 선택 --")

        for row in range(self.acl_list_table.rowCount()):
            name_item = self.acl_list_table.item(row, 0)
            if name_item and name_item.text():
                self.combo_acl_name.addItem(name_item.text())