import re
from pathlib import Path # Added
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QGraphicsDropShadowEffect

from file_search_module.utils.common import format_modified_date
# Assuming path_utils.py is at project root and accessible in PYTHONPATH
from path_utils import get_bundled_resource_path 

# Local resource_path function removed

class ResultCard(QFrame):
    cardDoubleClicked = pyqtSignal(str, str) # file_path, keyword
    
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
        
        file_path_obj = Path(self.file_path)
        filename = file_path_obj.name # Replaces os.path.basename
        
        try:
            # Get modification time using pathlib
            modified_time = file_path_obj.stat().st_mtime 
            date_str = format_modified_date(modified_time)
        except Exception: # Catch potential errors like FileNotFoundError if path is invalid
            date_str = ""
        
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        # Get extension using pathlib
        ext = file_path_obj.suffix.lower().lstrip('.') if file_path_obj.suffix else ""
        
        # Base path for icons relative to project root
        icon_base_path_str = "file_search_module/ui/icons/"
        
        ext_icon_map = {
            'pdf': get_bundled_resource_path(f"{icon_base_path_str}pdf_icon.png"),
            'txt': get_bundled_resource_path(f"{icon_base_path_str}txt_icon.png"),
            'docx': get_bundled_resource_path(f"{icon_base_path_str}docx_icon.png"),
            'xlsx': get_bundled_resource_path(f"{icon_base_path_str}xlsx_icon.png"),
            'html': get_bundled_resource_path(f"{icon_base_path_str}html_icon.png")
        }
        # Default icon path also needs to be relative to project root
        default_icon_path = get_bundled_resource_path(f"{icon_base_path_str}file_icon.png")
        icon_path_obj = ext_icon_map.get(ext, default_icon_path)
        
        icon_label = QLabel()
        # QIcon can handle Path objects, but str() is safer if issues arise
        icon_label.setPixmap(QIcon(str(icon_path_obj)).pixmap(30, 30)) 
        
        title_label = QLabel(filename) # filename is already a string from Path.name
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
