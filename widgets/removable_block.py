# widgets/removable_block.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class RemovableBlock(QWidget):
    """
    封裝含有刪除按鈕與文字標籤的區塊元件，
    若來源為 DraggableLabel 則支援雙擊編輯功能。
    """
    def __init__(self, text, row, col, source_type, editor):
        super().__init__()
        self.setProperty("block_text", text)
        self.setProperty("block_type", source_type)
        self.text = text
        self.row = row
        self.col = col
        self.source_type = source_type
        self.editor = editor
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.delete_button = QPushButton("×", self)
        self.delete_button.setFixedSize(15, 15)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: red;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                color: darkred;
            }
        """)
        self.delete_button.clicked.connect(lambda: self.editor.remove_block(self, self.row, self.col))
        layout.addWidget(self.delete_button)
        self.label = QLabel(self.text, self)
        self.label.setToolTip(self.text)
        self.label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #F0F8FF;
                color: #333333;
                border: 1px solid #CCE7FF;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.label)
        if self.source_type == b"DraggableLabel":
            self.label.mouseDoubleClickEvent = lambda e: self.editor.edit_label_text(self.label, self.row, self.col)
        self.delete_button.hide()

    def enterEvent(self, event):
        self.delete_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.delete_button.hide()
        super().leaveEvent(event)
