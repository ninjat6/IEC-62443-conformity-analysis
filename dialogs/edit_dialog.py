# dialogs/edit_dialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

class EditDialog(QDialog):
    """
    當使用者雙擊區塊時彈出編輯內容的對話框
    """
    def __init__(self, original_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("編輯內容")
        self.setModal(True)
        self.original_text = original_text
        self.new_text = original_text
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setText(self.original_text)
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.on_ok)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def on_ok(self):
        self.new_text = self.text_edit.toPlainText()
        self.accept()
