# gui/result_filter_panel.py
"""
結果過濾面板：提供搜尋、篩選、排序功能
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QComboBox, QLabel, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class ResultFilterPanel(QWidget):
    """
    結果過濾面板

    功能：
    - 關鍵字搜尋
    - 章節過濾 (SP.01 ~ SP.12)
    - 相似度過濾
    - 排序方式選擇
    """

    filter_changed = pyqtSignal()  # 過濾條件變更信號

    # 章節定義
    CHAPTERS = [
        ("SP.01", "人員配備"),
        ("SP.02", "保障措施"),
        ("SP.03", "架構設計"),
        ("SP.04", "無線安全"),
        ("SP.05", "安全儀表系統"),
        ("SP.06", "配置管控"),
        ("SP.07", "遠程訪問"),
        ("SP.08", "事件管理"),
        ("SP.09", "帳戶管理"),
        ("SP.10", "惡意軟件防護"),
        ("SP.11", "補丁管理"),
        ("SP.12", "備份與還原"),
    ]

    # 相似度過濾選項
    SIMILARITY_OPTIONS = [
        ("所有", 0.0),
        ("≥80% (高)", 0.80),
        ("≥65% (中)", 0.65),
        ("≥50% (低)", 0.50),
    ]

    # 排序選項
    SORT_OPTIONS = [
        ("依條款", "requirement"),
        ("相似度 ↓", "similarity_desc"),
        ("相似度 ↑", "similarity_asc"),
        ("依檔名", "filename"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """建立 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(10)

        # 搜尋框
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(2)

        search_label = QLabel("搜尋")
        search_label.setFont(QFont("System UI", 9))
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 輸入關鍵字...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_filter_changed)
        self.search_input.setMinimumWidth(150)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_container)

        # 章節過濾
        chapter_container = QWidget()
        chapter_layout = QVBoxLayout(chapter_container)
        chapter_layout.setContentsMargins(0, 0, 0, 0)
        chapter_layout.setSpacing(2)

        chapter_label = QLabel("章節")
        chapter_label.setFont(QFont("System UI", 9))
        chapter_layout.addWidget(chapter_label)

        self.chapter_filter = QComboBox()
        self.chapter_filter.addItem("所有章節", None)
        for code, name in self.CHAPTERS:
            self.chapter_filter.addItem(f"{code} {name}", code)
        self.chapter_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.chapter_filter.setMinimumWidth(140)
        chapter_layout.addWidget(self.chapter_filter)

        layout.addWidget(chapter_container)

        # 相似度過濾
        similarity_container = QWidget()
        similarity_layout = QVBoxLayout(similarity_container)
        similarity_layout.setContentsMargins(0, 0, 0, 0)
        similarity_layout.setSpacing(2)

        similarity_label = QLabel("相似度")
        similarity_label.setFont(QFont("System UI", 9))
        similarity_layout.addWidget(similarity_label)

        self.similarity_filter = QComboBox()
        for label, value in self.SIMILARITY_OPTIONS:
            self.similarity_filter.addItem(label, value)
        self.similarity_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.similarity_filter.setMinimumWidth(100)
        similarity_layout.addWidget(self.similarity_filter)

        layout.addWidget(similarity_container)

        # 排序
        sort_container = QWidget()
        sort_layout = QVBoxLayout(sort_container)
        sort_layout.setContentsMargins(0, 0, 0, 0)
        sort_layout.setSpacing(2)

        sort_label = QLabel("排序")
        sort_label.setFont(QFont("System UI", 9))
        sort_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        for label, value in self.SORT_OPTIONS:
            self.sort_combo.addItem(label, value)
        self.sort_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.sort_combo.setMinimumWidth(100)
        sort_layout.addWidget(self.sort_combo)

        layout.addWidget(sort_container)

        # 重置按鈕
        reset_container = QWidget()
        reset_layout = QVBoxLayout(reset_container)
        reset_layout.setContentsMargins(0, 0, 0, 0)
        reset_layout.setSpacing(2)

        reset_label = QLabel(" ")  # 佔位
        reset_label.setFont(QFont("System UI", 9))
        reset_layout.addWidget(reset_label)

        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_filters)
        reset_layout.addWidget(self.reset_btn)

        layout.addWidget(reset_container)

        # 彈性空間
        layout.addStretch()

    def _on_filter_changed(self):
        """過濾條件變更時發送信號"""
        self.filter_changed.emit()

    def get_filters(self) -> dict:
        """取得當前過濾條件"""
        return {
            'search': self.search_input.text().strip().lower(),
            'chapter': self.chapter_filter.currentData(),
            'min_similarity': self.similarity_filter.currentData(),
            'sort_by': self.sort_combo.currentData(),
        }

    def reset_filters(self):
        """重置所有過濾條件"""
        self.search_input.clear()
        self.chapter_filter.setCurrentIndex(0)
        self.similarity_filter.setCurrentIndex(0)
        self.sort_combo.setCurrentIndex(0)

    def apply_filters(self, results: list) -> list:
        """
        套用過濾條件並排序結果

        Args:
            results: 原始結果列表

        Returns:
            過濾並排序後的結果列表
        """
        filters = self.get_filters()
        filtered = results.copy()

        # 關鍵字搜尋
        search_text = filters['search']
        if search_text:
            filtered = [
                r for r in filtered
                if (search_text in r.get('requirement', '').lower() or
                    search_text in r.get('requirement_text', '').lower() or
                    search_text in r.get('snippet', '').lower() or
                    search_text in r.get('source_file', '').lower())
            ]

        # 章節過濾
        chapter = filters['chapter']
        if chapter:
            filtered = [
                r for r in filtered
                if r.get('requirement', '').startswith(chapter)
            ]

        # 相似度過濾
        min_sim = filters['min_similarity']
        if min_sim > 0:
            filtered = [
                r for r in filtered
                if r.get('similarity', 0) >= min_sim
            ]

        # 排序
        sort_by = filters['sort_by']
        if sort_by == 'requirement':
            filtered.sort(key=lambda x: x.get('requirement', ''))
        elif sort_by == 'similarity_desc':
            filtered.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        elif sort_by == 'similarity_asc':
            filtered.sort(key=lambda x: x.get('similarity', 0))
        elif sort_by == 'filename':
            filtered.sort(key=lambda x: x.get('source_file', '').split('\\')[-1].split('/')[-1])

        return filtered

    def get_filter_summary(self, original_count: int, filtered_count: int) -> str:
        """取得過濾摘要文字"""
        filters = self.get_filters()
        active_filters = []

        if filters['search']:
            active_filters.append(f"關鍵字: {filters['search']}")
        if filters['chapter']:
            active_filters.append(f"章節: {filters['chapter']}")
        if filters['min_similarity'] > 0:
            active_filters.append(f"相似度 ≥ {int(filters['min_similarity'] * 100)}%")

        if active_filters:
            filter_text = " | ".join(active_filters)
            return f"顯示 {filtered_count}/{original_count} 筆結果 ({filter_text})"
        else:
            return f"共 {original_count} 筆結果"
