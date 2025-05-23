# widgets/draggable_value.py

from PyQt6.QtWidgets import QLabel, QFrame
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor
from PyQt6.QtCore import QMimeData, QPointF, Qt

class DraggableValue(QLabel):
    def __init__(self, text, full_text):
        super().__init__(text)
        self.full_text = full_text
        self.short_text = text
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #F8FBFF;
                color: #333333;
                border: 1px solid #CCE7FF;
                border-radius: 5px;
                font-size: 14px;
                text-align: left;
                margin-bottom: 10px;
            }
            QLabel:hover {
                background-color: #E0F7FF;
            }
        """)
        self.setToolTip(self.full_text)

    def set_size(self, width, height):
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.update_text(width)

    def update_text(self, width):
        padding = 20
        char_width = 8
        max_chars = max((width - padding) // char_width, 3)
        self.short_text = (self.full_text if len(self.full_text) <= max_chars
                           else self.full_text[:max_chars - 3] + "...")
        self.setText(self.short_text)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.full_text)
            mime_data.setData("source_type", b"DraggableValue")
            drag.setMimeData(mime_data)

            drag_width, drag_height = 100, 30
            pixmap = QPixmap(drag_width, drag_height)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#e6f7ff"))
            painter.setPen(QColor("#80d4ff"))
            painter.drawRoundedRect(0, 0, drag_width, drag_height, 5, 5)

            font = self.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#333333"))
            painter.drawText(pixmap.rect().adjusted(10, 0, -10, 0),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             self.short_text)
            painter.end()

            drag.setPixmap(pixmap)
            drag.setHotSpot(QPointF(drag_width / 2, drag_height / 2).toPoint())
            drag.exec(Qt.DropAction.MoveAction)
