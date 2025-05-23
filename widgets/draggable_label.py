# widgets/draggable_label.py

from PyQt6.QtWidgets import QLabel, QFrame
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor
from PyQt6.QtCore import QMimeData, QPointF, Qt

class DraggableLabel(QLabel):
    def __init__(self, text, full_text):
        super().__init__(text)
        self.full_text = full_text
        self.short_text = text
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 10px;
                font-size: 12px;
                color: #333333;
                text-align: center;
            }
            QLabel:hover {
                background-color: #e6f7ff;
                border: 1px solid #80d4ff;
            }
        """)
        self.setToolTip(self.full_text)

    def set_size(self, width, height):
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.update_text(width)

    def update_text(self, width):
        max_chars = max((width - 20) // 7, 3)
        self.short_text = (self.full_text if len(self.full_text) <= max_chars
                           else self.full_text[:max_chars - 3] + "...")
        self.setText(self.short_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.full_text)
            mime_data.setData("source_type", b"DraggableLabel")
            drag.setMimeData(mime_data)

            drag_width, drag_height = 100, 30
            pixmap = QPixmap(drag_width, drag_height)
            pixmap.fill(QColor(255, 255, 255, 0))

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#e6f7ff"))
            painter.setPen(QColor("#80d4ff"))
            painter.drawRoundedRect(0, 0, drag_width, drag_height, 8, 8)

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
