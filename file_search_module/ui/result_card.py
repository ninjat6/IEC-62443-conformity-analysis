import os
import sys
import re
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QGraphicsDropShadowEffect

from file_search_module.utils.common import format_modified_date

def resource_path(relative_path):
    """取得資源的絕對路徑，支援開發與打包環境"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class ResultCard(QFrame):
    cardDoubleClicked = pyqtSignal(str, str)
    
    def __init__(self, file_path, raw_line, keyword, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.raw_line = raw_line
        self.keyword = keyword
        self._snippet_label = None
        self.modified_label = None
        
        self.init_card_ui()
    
    def init_card_ui(self):
        self.setObjectName("ResultCard")
        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # 陰影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(6)
        
        filename = os.path.basename(self.file_path)
        try:
            modified_time = os.path.getmtime(self.file_path)
            date_str = format_modified_date(modified_time)
        except Exception:
            date_str = ""
        
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        ext_icon_map = {
            'pdf': resource_path('icons/pdf_icon.png'),
            'txt': resource_path('icons/txt_icon.png'),
            'docx': resource_path('icons/docx_icon.png'),
            'xlsx': resource_path('icons/xlsx_icon.png'),
            'html': resource_path('icons/html_icon.png')
        }
        icon_path = ext_icon_map.get(ext, resource_path('ui/icons/file_icon.png'))
        
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(icon_path).pixmap(30, 30))
        
        title_label = QLabel(filename)
        font_title = QFont()
        font_title.setBold(True)
        font_title.setPointSize(14)
        title_label.setFont(font_title)
        
        top_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        top_layout.addWidget(title_label, 1, Qt.AlignmentFlag.AlignVCenter)
        
        self.modified_label = QLabel(date_str, self)
        date_font = QFont()
        date_font.setPointSize(12)
        self.modified_label.setFont(date_font)
        self.modified_label.setStyleSheet("color: #555555;")
        self.modified_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.modified_label, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.modified_label.hide()
        
        main_layout.addLayout(top_layout)
        
        self._snippet_label = QLabel()
        self._snippet_label.setTextFormat(Qt.TextFormat.RichText)
        self._snippet_label.setWordWrap(True)
        self._snippet_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        main_layout.addWidget(self._snippet_label, 1)
        
        self.update_snippet_text()
    
    def update_snippet_text(self):
        if not self.keyword:
            self._snippet_label.setText(self.raw_line)
            return
        dynamic_radius = max(10, self.width() // 10)
        snippet = self.extract_surrounding_context(self.raw_line, self.keyword, dynamic_radius)
        snippet_html = self.highlight_keyword(snippet, self.keyword)
        self._snippet_label.setText(snippet_html)
    
    def extract_surrounding_context(self, full_text, keyword, radius=30):
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        match = pattern.search(full_text)
        if not match:
            return full_text
        start_idx = match.start()
        end_idx = match.end()
        left_start = max(0, start_idx - radius)
        right_end = min(len(full_text), end_idx + radius)
        snippet = ""
        if left_start > 0:
            snippet += "..."
        snippet += full_text[left_start:right_end]
        if right_end < len(full_text):
            snippet += "..."
        return snippet
    
    def highlight_keyword(self, text, keyword):
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        def replace_func(m):
            return f"<span style='background-color: #FFEB3B; border-radius: 3px; font-weight: bold;'>{m.group(0)}</span>"
        return pattern.sub(replace_func, text)
    
    def enterEvent(self, event):
        self.setProperty("hover", True)
        self.style().polish(self)
        if self.modified_label:
            self.modified_label.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().polish(self)
        if self.modified_label:
            self.modified_label.hide()
        super().leaveEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parentWidget():
            container_width = self.parentWidget().width()
            self.setMaximumWidth(container_width)
            self.setMinimumWidth(min(300, container_width))
            self._snippet_label.setMaximumWidth(container_width - 40)
        self.update_snippet_text()
    
    def mouseDoubleClickEvent(self, event):
        self.cardDoubleClicked.emit(self.file_path, self.keyword)
        super().mouseDoubleClickEvent(event)
