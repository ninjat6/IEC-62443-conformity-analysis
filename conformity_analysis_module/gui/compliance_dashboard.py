# gui/compliance_dashboard.py
"""
符合性統計儀表板：提供視覺化統計摘要
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush

# 顏色定義
ACCENT_COLOR = "#007AFF"
SUCCESS_COLOR = "#198754"
WARNING_COLOR = "#FFC107"
ERROR_COLOR = "#DC3545"
TEXT_COLOR = "#212529"
SECONDARY_TEXT_COLOR = "#6C757D"
BORDER_COLOR = "#DDE1E6"
CONTENT_BG = "#FFFFFF"


class StatCard(QFrame):
    """統計數字卡片"""

    def __init__(self, title: str, value: str, icon: str, color: str = ACCENT_COLOR, parent=None):
        super().__init__(parent)
        self.color = color
        self._setup_ui(title, value, icon)

    def _setup_ui(self, title: str, value: str, icon: str):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CONTENT_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # 圖標和標題
        header = QHBoxLayout()
        header.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("System UI", 20))
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setFont(QFont("System UI", 10))
        title_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR};")
        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)

        # 數值
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("System UI", 28, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {self.color};")
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        """更新數值"""
        self.value_label.setText(value)


class ChapterProgressBar(QWidget):
    """章節符合度進度條"""

    def __init__(self, chapter: str, name: str, matched: int, total: int, parent=None):
        super().__init__(parent)
        self.chapter = chapter
        self.name = name
        self.matched = matched
        self.total = total
        self.progress = (matched / total * 100) if total > 0 else 0
        self.setMinimumHeight(35)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        bar_height = 20
        bar_y = (height - bar_height) // 2

        # 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E9ECEF"))
        painter.drawRoundedRect(80, bar_y, width - 130, bar_height, 5, 5)

        # 進度
        if self.progress > 0:
            # 根據進度選擇顏色
            if self.progress >= 70:
                color = SUCCESS_COLOR
            elif self.progress >= 40:
                color = WARNING_COLOR
            else:
                color = ERROR_COLOR

            painter.setBrush(QColor(color))
            progress_width = int((width - 130) * self.progress / 100)
            painter.drawRoundedRect(80, bar_y, progress_width, bar_height, 5, 5)

        # 章節標籤
        painter.setPen(QColor(TEXT_COLOR))
        painter.setFont(QFont("System UI", 9, QFont.Weight.Bold))
        painter.drawText(5, bar_y, 70, bar_height, Qt.AlignmentFlag.AlignVCenter, self.chapter)

        # 百分比
        painter.setFont(QFont("System UI", 9))
        painter.drawText(width - 45, bar_y, 45, bar_height,
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                        f"{self.progress:.0f}%")


class ComplianceDashboard(QWidget):
    """
    符合性統計儀表板

    顯示：
    - 分析條款數 / 已匹配數 / 待補充數
    - 平均相似度
    - 各章節符合度進度條
    """

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 統計卡片區
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.total_card = StatCard("分析條款", "0", "📋", ACCENT_COLOR)
        self.matched_card = StatCard("已匹配", "0", "✅", SUCCESS_COLOR)
        self.missing_card = StatCard("待補充", "0", "❌", ERROR_COLOR)
        self.avg_sim_card = StatCard("平均相似度", "0%", "📈", WARNING_COLOR)

        cards_layout.addWidget(self.total_card)
        cards_layout.addWidget(self.matched_card)
        cards_layout.addWidget(self.missing_card)
        cards_layout.addWidget(self.avg_sim_card)

        layout.addLayout(cards_layout)

        # 章節符合度標題
        chapter_title = QLabel("📊 各章節符合度")
        chapter_title.setFont(QFont("System UI", 11, QFont.Weight.Bold))
        chapter_title.setStyleSheet(f"color: {TEXT_COLOR}; margin-top: 10px;")
        layout.addWidget(chapter_title)

        # 章節進度條區域
        self.chapter_container = QWidget()
        self.chapter_layout = QVBoxLayout(self.chapter_container)
        self.chapter_layout.setContentsMargins(0, 0, 0, 0)
        self.chapter_layout.setSpacing(5)

        # 初始化空進度條
        self.chapter_bars = {}
        for code, name in self.CHAPTERS:
            bar = ChapterProgressBar(code, name, 0, 1)
            self.chapter_bars[code] = bar
            self.chapter_layout.addWidget(bar)

        layout.addWidget(self.chapter_container)

    def update_stats(self, results: list, total_requirements: int, selected_requirements: dict):
        """
        更新統計數據

        Args:
            results: 分析結果列表
            total_requirements: 總條款數
            selected_requirements: 選中的條款字典
        """
        # 計算已匹配的唯一條款數
        matched_reqs = set(r.get('requirement', '') for r in results)
        matched_count = len(matched_reqs)
        missing_count = total_requirements - matched_count

        # 計算平均相似度
        if results:
            avg_sim = sum(r.get('similarity', 0) for r in results) / len(results)
        else:
            avg_sim = 0

        # 更新卡片
        self.total_card.set_value(str(total_requirements))
        self.matched_card.set_value(str(matched_count))
        self.missing_card.set_value(str(missing_count))
        self.avg_sim_card.set_value(f"{avg_sim:.0%}")

        # 計算各章節符合度
        chapter_stats = {}
        for code, name in self.CHAPTERS:
            chapter_stats[code] = {'matched': set(), 'total': 0}

        # 統計選中的條款
        for req_key in selected_requirements.keys():
            for code, _ in self.CHAPTERS:
                if req_key.startswith(code):
                    chapter_stats[code]['total'] += 1
                    break

        # 統計已匹配的條款
        for req in matched_reqs:
            for code, _ in self.CHAPTERS:
                if req.startswith(code):
                    chapter_stats[code]['matched'].add(req)
                    break

        # 更新章節進度條
        self._update_chapter_bars(chapter_stats)

    def _update_chapter_bars(self, chapter_stats: dict):
        """更新章節進度條"""
        # 清除舊的進度條
        for i in reversed(range(self.chapter_layout.count())):
            widget = self.chapter_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.chapter_bars = {}

        # 創建新的進度條
        for code, name in self.CHAPTERS:
            stats = chapter_stats.get(code, {'matched': set(), 'total': 0})
            matched = len(stats['matched'])
            total = stats['total']

            if total > 0:  # 只顯示有選中條款的章節
                bar = ChapterProgressBar(code, name, matched, total)
                self.chapter_bars[code] = bar
                self.chapter_layout.addWidget(bar)

        # 如果沒有任何章節有數據
        if not self.chapter_bars:
            empty_label = QLabel("請選擇條款並執行分析")
            empty_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR}; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chapter_layout.addWidget(empty_label)

    def clear(self):
        """清除所有統計數據"""
        self.total_card.set_value("0")
        self.matched_card.set_value("0")
        self.missing_card.set_value("0")
        self.avg_sim_card.set_value("0%")

        # 清除章節進度條
        for i in reversed(range(self.chapter_layout.count())):
            widget = self.chapter_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.chapter_bars = {}
