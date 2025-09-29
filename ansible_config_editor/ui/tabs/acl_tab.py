# ansible_config_editor/ui/tabs/acl_tab.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox,
                               QTableWidget, QPushButton, QHeaderView, QCheckBox,
                               QComboBox, QScrollArea, QHBoxLayout, QLabel, QAbstractItemView,
                               QTableWidgetItem)
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
        self.acl_rule_table.setHorizontalHeaderLabels(
            ["Seq", "Action", "Protocol", "Source IP/Mask",
             "Dest IP/Mask", "Src Port", "Dest Port", "Options"]
        )
        # 컬럼 너비 조절 (필요에 따라 수정)
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

        self.acl_rule_group.setEnabled(False)  # 처음에는 비활성화
        main_layout.addWidget(self.acl_rule_group)