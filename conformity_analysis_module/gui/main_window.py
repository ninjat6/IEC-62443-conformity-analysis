# gui/main_window.py
import re
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QListWidget, QLabel, QTextEdit, QWidget, QListWidgetItem, QComboBox,
    QGroupBox, QSplitter, QProgressBar, QAbstractItemView, QSizePolicy,
    QFrame, QScrollArea, QCheckBox, QMessageBox, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QSlider, QRadioButton, QButtonGroup, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QPainter, QBrush, QScreen
from PyQt6.QtWidgets import QStyle
from pathlib import Path

from conformity_analysis_module.core.analyzer import Analyzer
from conformity_analysis_module.core.worksheet_updater import WorksheetUpdater
from conformity_analysis_module.core.requirements_loader import RequirementsLoader
from conformity_analysis_module.utils.logger import logger

# 顏色主題定義
BG_COLOR = "#F8F9FA"
CONTENT_BG_COLOR = "#FFFFFF"
BORDER_COLOR = "#DDE1E6"
TEXT_COLOR = "#212529"
SECONDARY_TEXT_COLOR = "#6C757D"
ACCENT_COLOR = "#007AFF"
ACCENT_HOVER_COLOR = "#005ECB"
ACCENT_PRESSED_COLOR = "#004BA0"
DISABLED_BG_COLOR = "#E9ECEF"
DISABLED_TEXT_COLOR = "#ADB5BD"
ERROR_COLOR = "#DC3545"
SUCCESS_COLOR = "#198754"
WARNING_COLOR = "#FFC107"
INFO_COLOR = "#17A2B8"


class AnalysisThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, analyzer, folder_path, requirements, threshold=0.65):
        super().__init__()
        self.analyzer = analyzer
        self.folder_path = folder_path
        self.requirements = requirements
        self.threshold = threshold

    def run(self):
        try:
            results = self.analyzer.analyze(self.folder_path, self.requirements, self.threshold)
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Analysis thread error: {e}", exc_info=True)
            self.error.emit(str(e))


class StyledButton(QPushButton):
    def __init__(self, text, primary=False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("System UI", 10, QFont.Weight.Medium))
        self.update_style()

    def update_style(self):
        if self.primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT_COLOR}; color: white;
                    border: none; border-radius: 6px; padding: 8px 18px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {ACCENT_HOVER_COLOR}; }}
                QPushButton:pressed {{ background-color: {ACCENT_PRESSED_COLOR}; }}
                QPushButton:disabled {{
                    background-color: {DISABLED_BG_COLOR}; color: {DISABLED_TEXT_COLOR};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CONTENT_BG_COLOR}; color: {TEXT_COLOR};
                    border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px 18px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #F1F3F5; border-color: #C8CDD2;
                }}
                QPushButton:pressed {{ background-color: #E9ECEF; }}
                QPushButton:disabled {{
                    background-color: {BG_COLOR}; color: {DISABLED_TEXT_COLOR};
                    border-color: {BORDER_COLOR};
                }}
            """)


class ResponsiveWidget(QWidget):
    """響應式容器組件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_width_for_horizontal = 1200  # 最小寬度閾值
        self.is_horizontal_layout = True
        
    def set_layout_threshold(self, threshold):
        self.min_width_for_horizontal = threshold
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        current_width = self.width()
        should_be_horizontal = current_width >= self.min_width_for_horizontal
        
        if should_be_horizontal != self.is_horizontal_layout:
            self.is_horizontal_layout = should_be_horizontal
            self.update_layout_orientation()
    
    def update_layout_orientation(self):
        # 子類實現具體的佈局調整邏輯
        pass


class ConformityAnalysisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IEC 62443-2-4 符合性分析工具")
        
        # 響應式設計參數
        self.current_screen_size = "large"  # large, medium, small
        self.layout_breakpoints = {
            'small': 800,
            'medium': 1200,
            'large': 1600
        }
        
        # 初始化所有組件引用為 None，避免未定義錯誤
        self.main_splitter = None
        self.left_scroll_area = None
        self.right_panel = None
        self.tip_labels = []  # 提前初始化
        
        # 初始化數據
        try:
            self.requirements = RequirementsLoader.load()
        except Exception as e:
            logger.error(f"Failed to load requirements: {e}", exc_info=True)
            self.requirements = {}
            
        self.chapter_names = {
            "SP.01": "人員配備", "SP.02": "保障措施", "SP.03": "架構設計",
            "SP.04": "無線安全", "SP.05": "安全儀表系統", "SP.06": "配置管控",
            "SP.07": "遠程訪問", "SP.08": "事件管理", "SP.09": "帳戶管理",
            "SP.10": "惡意軟件防護", "SP.11": "補丁管理", "SP.12": "備份與還原"
        }
        self.folder_path = None
        self.analyzer = None
        self.analysis_thread = None
        self.analysis_results = []
        self.threshold_value = 0.65  # 預設閾值
        
        self._is_updating_checks = False
        self.total_requirements_count = 0
        
        try:
            self.setup_window()
            self.setup_styles()
            self.init_ui()
            self.populate_requirements_tree()
            self.update_selection_count()
        except Exception as e:
            logger.error(f"Error during window initialization: {e}", exc_info=True)
            # 顯示錯誤對話框
            QMessageBox.critical(None, "初始化錯誤", f"應用程式初始化時發生錯誤:\n\n{str(e)}\n\n請檢查相關文件是否完整。")

    def setup_window(self):
        """設置視窗屬性"""
        # 獲取螢幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # 設置最小尺寸
        self.setMinimumSize(900, 700)
        
        # 最大化視窗
        self.showMaximized()
        
        # 設置視窗圖標（如果有的話）
        # self.setWindowIcon(QIcon("path/to/icon.png"))

    def get_screen_size_category(self):
        """根據當前視窗寺大小決定螢幕尺寸分類"""
        width = self.width()
        if width < self.layout_breakpoints['small']:
            return 'small'
        elif width < self.layout_breakpoints['medium']:
            return 'medium'
        else:
            return 'large'

    def setup_styles(self):
        """設置全局樣式"""
        self.setFont(QFont("System UI", 9))
        self.setStyleSheet(f"""
            QMainWindow {{ 
                background-color: {BG_COLOR}; 
            }}
            QLabel {{ 
                color: {TEXT_COLOR}; 
                font-size: 10pt; 
            }}
            QGroupBox {{
                font-size: 11pt; 
                font-weight: 500; 
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR}; 
                border-radius: 8px;
                margin-top: 10px; 
                padding-top: 12px;
                background-color: {CONTENT_BG_COLOR};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; 
                subcontrol-position: top left;
                left: 15px; 
                padding: 0 8px;
                background-color: {CONTENT_BG_COLOR}; 
                color: {SECONDARY_TEXT_COLOR};
                font-weight: 600;
            }}
            QTreeWidget {{
                background-color: {CONTENT_BG_COLOR};
                border: 1px solid {BORDER_COLOR}; 
                border-radius: 6px;
                padding: 5px; 
                outline: none; 
                font-size: 10pt;
                selection-background-color: {ACCENT_COLOR};
            }}
            QTreeWidget::item {{
                padding: 8px 5px; 
                color: {TEXT_COLOR}; 
                border-radius: 4px;
                min-height: 20px;
            }}
            QTreeWidget::item:selected {{
                background-color: {ACCENT_COLOR}; 
                color: white;
            }}
            QTreeWidget::item:hover:!selected {{ 
                background-color: #F0F3F5; 
            }}
            QTreeWidget::indicator {{
                width: 18px;
                height: 18px;
            }}
            QTextEdit {{
                background-color: {CONTENT_BG_COLOR};
                border: 1px solid {BORDER_COLOR}; 
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'SF Mono', 'Monaco', monospace;
                font-size: 10pt; 
                color: {TEXT_COLOR}; 
                line-height: 1.6;
            }}
            QComboBox {{
                background-color: {CONTENT_BG_COLOR};
                border: 1px solid {BORDER_COLOR}; 
                border-radius: 6px;
                padding: 8px 12px; 
                min-height: 20px;
                font-size: 10pt; 
                color: {TEXT_COLOR};
            }}
            QComboBox:hover {{ 
                border-color: #AEB5BC; 
            }}
            QComboBox:focus {{ 
                border-color: {ACCENT_COLOR}; 
            }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 24px; 
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QProgressBar {{
                background-color: #E9ECEF; 
                border: none; 
                border-radius: 4px;
                text-align: center; 
                font-size: 9pt; 
                color: {SECONDARY_TEXT_COLOR};
                height: 24px;
            }}
            QProgressBar::chunk {{ 
                background-color: {ACCENT_COLOR}; 
                border-radius: 4px; 
            }}
            QCheckBox::indicator:indeterminate, 
            QTreeWidget::indicator:indeterminate {{
                background-color: {ACCENT_COLOR}BF;
                border-color: {ACCENT_COLOR};
            }}
            QCheckBox {{ 
                spacing: 8px; 
                font-size: 10pt; 
                color: {TEXT_COLOR}; 
            }}
            QCheckBox::indicator {{
                width: 18px; 
                height: 18px;
                border: 2px solid #ADB5BD; 
                border-radius: 4px;
                background-color: {CONTENT_BG_COLOR};
            }}
            QCheckBox::indicator:hover {{ 
                border-color: {ACCENT_COLOR}; 
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_COLOR}; 
                border-color: {ACCENT_COLOR};
            }}
            QSplitter::handle {{ 
                background: {BG_COLOR}; 
            }}
            QSplitter::handle:horizontal {{ 
                height: 8px; 
                margin: 2px 0; 
            }}
            QSplitter::handle:vertical {{ 
                width: 8px; 
                margin: 0 2px; 
            }}
            QSplitter::handle:hover {{ 
                background: #CFD2D5; 
            }}
            QSplitter::handle:pressed {{ 
                background: {ACCENT_COLOR}; 
            }}
            QLineEdit {{
                padding: 10px 12px; 
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px; 
                background-color: {CONTENT_BG_COLOR};
                color: {TEXT_COLOR}; 
                font-size: 10pt;
                min-height: 16px;
            }}
            QLineEdit:read-only {{
                background-color: #F1F3F5; 
                color: {SECONDARY_TEXT_COLOR};
            }}
            QLineEdit:focus {{
                border-color: {ACCENT_COLOR};
            }}
            QRadioButton {{
                spacing: 10px; 
                font-size: 10pt; 
                color: {TEXT_COLOR};
                padding: 4px;
            }}
            QRadioButton::indicator {{
                width: 18px; 
                height: 18px;
                border: 2px solid #ADB5BD; 
                border-radius: 9px;
                background-color: {CONTENT_BG_COLOR};
            }}
            QRadioButton::indicator:hover {{
                border-color: {ACCENT_COLOR};
            }}
            QRadioButton::indicator:checked {{
                background-color: {ACCENT_COLOR}; 
                border-color: {ACCENT_COLOR};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: #F1F3F5;
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #C1C7CD;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #A8B2BA;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)

    def init_ui(self):
        """初始化用戶界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主佈局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 創建標題
        self.create_header(main_layout)
        
        # 創建主要分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)
        
        try:
            # 創建左側面板
            left_panel = self.create_left_panel()
            self.main_splitter.addWidget(left_panel)
            
            # 創建右側面板
            right_panel = self.create_right_panel()
            self.main_splitter.addWidget(right_panel)
            
            # 設置初始比例
            self.main_splitter.setSizes([650, 750])
            
            main_layout.addWidget(self.main_splitter, 1)
            
            # 創建狀態欄
            self.create_status_bar()
            
            # 初始化響應式佈局（延遲執行）
            QTimer.singleShot(100, self.update_responsive_layout)
            
        except Exception as e:
            logger.error(f"Error during UI initialization: {e}", exc_info=True)
            # 設置一個基本的錯誤顯示
            error_label = QLabel(f"UI 初始化錯誤: {str(e)}")
            main_layout.addWidget(error_label)

    def create_header(self, parent_layout):
        """創建標題區域"""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 15)
        header_layout.setSpacing(8)
        
        # 主標題
        title_label = QLabel("IEC 62443-2-4 符合性分析工具")
        title_label.setFont(QFont("System UI", 20, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; margin-bottom: 5px;")
        header_layout.addWidget(title_label)
        
        # 副標題
        subtitle_label = QLabel("自動化分析文件與 IEC 62443-2-4 標準的符合性 • 支援響應式佈局")
        subtitle_label.setFont(QFont("System UI", 11))
        subtitle_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR};")
        header_layout.addWidget(subtitle_label)
        
        parent_layout.addWidget(header_widget)

    def create_left_panel(self):
        """創建左側控制面板"""
        # 創建滾動區域以支持小螢幕
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 內容容器
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(25)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 步驟 1：選擇資料夾
        folder_group = self.create_folder_selection_group()
        layout.addWidget(folder_group)
        
        # 步驟 2：選擇模型
        model_group = self.create_model_selection_group()  
        layout.addWidget(model_group)
        
        # 步驟 3：選擇條款
        requirements_group = self.create_requirements_selection_group()
        layout.addWidget(requirements_group)
        
        # 步驟 4：相似度設定
        threshold_group = self.create_threshold_settings_group()
        layout.addWidget(threshold_group)
        
        # 行動按鈕
        action_buttons = self.create_action_buttons()
        layout.addWidget(action_buttons)
        
        # 添加彈性空間
        layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        self.left_scroll_area = scroll_area
        return scroll_area

    def create_folder_selection_group(self):
        """創建資料夾選擇組"""
        group = QGroupBox("步驟 1：選擇分析資料夾")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # 路徑顯示
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("尚未選擇資料夾...")
        self.folder_path_edit.setReadOnly(True)
        layout.addWidget(self.folder_path_edit)
        
        # 瀏覽按鈕
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.select_folder_btn = StyledButton("📁 瀏覽資料夾")
        self.select_folder_btn.clicked.connect(self.select_folder)
        button_layout.addWidget(self.select_folder_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_container)
        group.setLayout(layout)
        return group

    def create_model_selection_group(self):
        """創建模型選擇組"""
        group = QGroupBox("步驟 2：選擇分析模型")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 模型選擇下拉框
        self.model_combo = QComboBox()
        self.model_combo.addItem("🔤 all-MiniLM-L12-v2 (預設英文模型)", "models/all-MiniLM-L12-v2")
        self.model_combo.addItem("🌐 paraphrase-multilingual-MiniLM-L12-v2 (增強中文支援)", "models/paraphrase-multilingual-MiniLM-L12-v2")
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)
        
        # 模型說明
        self.model_info = QLabel("適用於英文文件的快速分析")
        self.model_info.setFont(QFont("System UI", 9))
        self.model_info.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR}; padding: 8px; background-color: #F8F9FA; border-radius: 4px;")
        self.model_info.setWordWrap(True)
        layout.addWidget(self.model_info)
        
        group.setLayout(layout)
        return group

    def create_requirements_selection_group(self):
        """創建條款選擇組"""
        group = QGroupBox("步驟 3：選擇分析條款")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # 快速選擇按鈕
        quick_select_widget = QWidget()
        quick_select_layout = QHBoxLayout(quick_select_widget)
        quick_select_layout.setContentsMargins(0, 0, 0, 0)
        quick_select_layout.setSpacing(15)
        
        self.select_all_btn = QPushButton("✅ 全選")
        self.select_none_btn = QPushButton("❌ 全不選")
        
        for btn in [self.select_all_btn, self.select_none_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    color: {ACCENT_COLOR};
                    border: none; 
                    padding: 8px 12px; 
                    font-size: 10pt;
                    font-weight: 500;
                    border-radius: 4px;
                }}
                QPushButton:hover {{ 
                    background-color: {ACCENT_COLOR}15;
                    text-decoration: underline; 
                }}
                QPushButton:pressed {{
                    background-color: {ACCENT_COLOR}25;
                }}
            """)
        
        self.select_all_btn.clicked.connect(self.select_all_requirements)
        self.select_none_btn.clicked.connect(self.select_none_requirements)
        
        quick_select_layout.addWidget(self.select_all_btn)
        quick_select_layout.addWidget(self.select_none_btn)
        quick_select_layout.addStretch()
        
        layout.addWidget(quick_select_widget)
        
        # 條款樹狀視圖
        self.requirements_tree = QTreeWidget()
        self.requirements_tree.setHeaderHidden(True)
        self.requirements_tree.itemChanged.connect(self.on_requirement_item_changed)
        self.requirements_tree.setMinimumHeight(300)
        layout.addWidget(self.requirements_tree)
        
        # 選擇計數
        self.selection_count_label = QLabel("已選擇 0 個條款")
        self.selection_count_label.setFont(QFont("System UI", 9))
        self.selection_count_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR}; padding: 8px; background-color: #F8F9FA; border-radius: 4px;")
        layout.addWidget(self.selection_count_label)
        
        group.setLayout(layout)
        return group

    def create_threshold_settings_group(self):
        """創建相似度設定組"""
        group = QGroupBox("步驟 4：相似度設定")
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # 預設選項區域
        preset_container = QWidget()
        preset_layout = QGridLayout(preset_container)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(15)

        self.threshold_button_group = QButtonGroup()
        self.radio_buttons = []

        # 預設選項
        presets = [
            ("嚴格", "80%", 0.80, "🎯"),
            ("標準", "65%", 0.65, "⚖️"), 
            ("寬鬆", "50%", 0.50, "🔍"),
            ("自訂", "", None, "⚙️")
        ]

        for i, (name, percentage, value, icon) in enumerate(presets):
            # 創建選項容器
            option_widget = QWidget()
            option_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {CONTENT_BG_COLOR};
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 8px;
                    padding: 8px;
                }}
                QWidget:hover {{
                    border-color: {ACCENT_COLOR};
                    background-color: #F8F9FA;
                }}
            """)
            
            option_layout = QHBoxLayout(option_widget)
            option_layout.setContentsMargins(8, 8, 8, 8)
            option_layout.setSpacing(10)
            
            # 單選按鈕
            radio = QRadioButton()
            self.radio_buttons.append(radio)
            
            # 圖標和標籤
            label_text = f"{icon} {name}"
            if percentage:
                label_text += f" ({percentage})"
                
            label = QLabel(label_text)
            label.setFont(QFont("System UI", 10, QFont.Weight.Medium))
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # 點擊標籤選中單選按鈕
            label.mousePressEvent = lambda e, r=radio: r.setChecked(True)
            
            option_layout.addWidget(radio)
            option_layout.addWidget(label, 1)
            
            # 佈局到網格
            row = i // 2
            col = i % 2
            preset_layout.addWidget(option_widget, row, col)
            
            # 設置按鈕行為
            if value is not None:
                radio.clicked.connect(lambda checked, v=value: self.set_threshold_preset(v))
            else:
                radio.clicked.connect(self.enable_custom_threshold)
                
            self.threshold_button_group.addButton(radio, i)
            
            # 保存引用
            if name == "標準":
                self.standard_radio = radio
                radio.setChecked(True)  # 預設選擇
            elif name == "自訂":
                self.custom_radio = radio

        layout.addWidget(preset_container)

        # 滑桿控制區域
        slider_container = self.create_slider_container()
        layout.addWidget(slider_container)

        # 提示信息卡片
        info_card = self.create_threshold_info_card()
        layout.addWidget(info_card)

        group.setLayout(layout)
        return group

    def create_slider_container(self):
        """創建滑桿控制容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 滑桿標題和當前值
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        slider_title = QLabel("相似度閾值：")
        slider_title.setFont(QFont("System UI", 11, QFont.Weight.Medium))

        self.threshold_value_label = QLabel("65%")
        self.threshold_value_label.setMinimumWidth(80)
        self.threshold_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threshold_value_label.setFont(QFont("System UI", 16, QFont.Weight.Bold))

        header_layout.addWidget(slider_title)
        header_layout.addStretch()
        header_layout.addWidget(self.threshold_value_label)

        layout.addWidget(header)

        # 滑桿
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(30, 90)
        self.threshold_slider.setValue(65)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.setMinimumHeight(40)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        self.threshold_slider.setEnabled(False)

        layout.addWidget(self.threshold_slider)

        # 刻度標籤
        scale_widget = QWidget()
        scale_layout = QHBoxLayout(scale_widget)
        scale_layout.setContentsMargins(0, 0, 0, 0)

        scales = ["30%", "40%", "50%", "60%", "70%", "80%", "90%"]
        for scale in scales:
            scale_label = QLabel(scale)
            scale_label.setFont(QFont("System UI", 8))
            scale_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR};")
            scale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scale_layout.addWidget(scale_label, 1)

        layout.addWidget(scale_widget)

        # 初始化樣式
        self.update_slider_style()
        self.update_threshold_value_style(65)

        return container

    def create_threshold_info_card(self):
        """創建閾值信息卡片"""
        info_card = QFrame()
        info_card.setFrameStyle(QFrame.Shape.Box)
        info_card.setStyleSheet(f"""
            QFrame {{
                background-color: #F0F8FF;
                border: 1px solid #B8E0FF;
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(12)

        # 標題
        title_label = QLabel("💡 相似度說明")
        title_label.setFont(QFont("System UI", 11, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; margin-bottom: 5px;")
        info_layout.addWidget(title_label)

        # 提示項目
        self.threshold_tips = [
            ("低相似度 (30-50%)", "找到更多可能相關的內容，適合初步探索", WARNING_COLOR),
            ("中相似度 (50-70%)", "平衡覆蓋率與準確度，適合一般分析", ACCENT_COLOR),
            ("高相似度 (70-90%)", "只顯示高度相關的內容，適合精確匹配", ERROR_COLOR)
        ]

        self.tip_labels = []  # 確保列表已初始化
        for tip_title, tip_text, color in self.threshold_tips:
            tip_widget = QWidget()
            tip_layout = QHBoxLayout(tip_widget)
            tip_layout.setContentsMargins(0, 0, 0, 0)
            tip_layout.setSpacing(10)
            
            # 彩色指示器
            indicator = QLabel("●")
            indicator.setStyleSheet(f"color: {color}; font-size: 14px;")
            indicator.setFixedWidth(20)
            
            # 提示文字
            tip_label = QLabel(f"<b>{tip_title}</b><br><span style='color: {SECONDARY_TEXT_COLOR}; font-size: 9pt;'>{tip_text}</span>")
            tip_label.setWordWrap(True)
            
            tip_layout.addWidget(indicator, 0, Qt.AlignmentFlag.AlignTop)
            tip_layout.addWidget(tip_label, 1)
            
            self.tip_labels.append(tip_widget)
            info_layout.addWidget(tip_widget)

        return info_card

    def create_action_buttons(self):
        """創建行動按鈕"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 15, 0, 0)
        layout.setSpacing(15)
        
        # 主要行動按鈕
        self.analyze_btn = StyledButton("🚀 開始分析", primary=True)
        self.analyze_btn.clicked.connect(self.analyze)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setMinimumHeight(45)
        layout.addWidget(self.analyze_btn)
        
        # 次要行動按鈕
        self.fill_worksheet_btn = StyledButton("📝 填入 Worksheet")
        self.fill_worksheet_btn.clicked.connect(self.fill_worksheet)
        self.fill_worksheet_btn.setEnabled(False)
        self.fill_worksheet_btn.setMinimumHeight(45)
        layout.addWidget(self.fill_worksheet_btn)
        
        return container

    def create_right_panel(self):
        """創建右側結果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 結果組
        result_group = QGroupBox("📊 分析結果")
        result_layout = QVBoxLayout()
        result_layout.setSpacing(15)
        
        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        result_layout.addWidget(self.progress_bar)
        
        # 結果消息
        self.result_message_widget = QWidget()
        result_message_layout = QHBoxLayout(self.result_message_widget)
        result_message_layout.setContentsMargins(10, 10, 10, 10)
        result_message_layout.setSpacing(12)
        
        self.result_icon_label = QLabel()
        self.result_icon_label.setFixedSize(24, 24)
        result_message_layout.addWidget(self.result_icon_label)
        
        self.result_message_text = QLabel()
        self.result_message_text.setFont(QFont("System UI", 11, QFont.Weight.Medium))
        self.result_message_text.setWordWrap(True)
        result_message_layout.addWidget(self.result_message_text, 1)
        
        self.result_message_widget.setVisible(False)
        self.result_message_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CONTENT_BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 5px;
            }}
        """)
        result_layout.addWidget(self.result_message_widget)
        
        # 結果詳情
        self.result_detail = QTextEdit()
        self.result_detail.setReadOnly(True)
        self.result_detail.setPlaceholderText("🔍 分析結果將顯示在這裡...\n\n請先選擇資料夾和條款，然後點擊「開始分析」按鈕。")
        result_layout.addWidget(self.result_detail, 1)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        self.right_panel = panel
        return panel

    def create_status_bar(self):
        """創建狀態欄"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {CONTENT_BG_COLOR}; 
                color: {SECONDARY_TEXT_COLOR};
                font-size: 10pt; 
                border-top: 1px solid {BORDER_COLOR};
                padding: 8px 15px;
            }}
        """)
        self.status_bar.showMessage("🎯 就緒 - 請選擇資料夾開始分析")

    def update_responsive_layout(self):
        """更新響應式佈局"""
        # 添加安全檢查，確保組件已經初始化
        if not hasattr(self, 'main_splitter') or self.main_splitter is None:
            return
            
        current_size = self.get_screen_size_category()
        
        if current_size != self.current_screen_size:
            self.current_screen_size = current_size
            
            if current_size == 'small':
                # 小螢幕：垂直佈局
                self.main_splitter.setOrientation(Qt.Orientation.Vertical)
                self.main_splitter.setSizes([400, 300])
            else:
                # 中大螢幕：水平佈局  
                self.main_splitter.setOrientation(Qt.Orientation.Horizontal)
                if current_size == 'medium':
                    self.main_splitter.setSizes([500, 600])
                else:  # large
                    self.main_splitter.setSizes([650, 750])

    def update_slider_style(self):
        """更新滑桿樣式"""
        if self.threshold_slider.isEnabled():
            self.threshold_slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    height: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {WARNING_COLOR},
                        stop:0.5 {ACCENT_COLOR},
                        stop:1 {ERROR_COLOR});
                    border-radius: 5px;
                }}
                QSlider::handle:horizontal {{
                    background: white;
                    border: 3px solid {ACCENT_COLOR};
                    width: 26px;
                    height: 26px;
                    margin: -10px 0;
                    border-radius: 13px;
                }}
                QSlider::handle:horizontal:hover {{
                    background: {ACCENT_COLOR};
                    border: 3px solid white;
                    box-shadow: 0 0 10px rgba(0,122,255,0.6);
                }}
                QSlider::handle:horizontal:pressed {{
                    background: {ACCENT_PRESSED_COLOR};
                    transform: scale(1.1);
                }}
                QSlider::tick:horizontal {{
                    width: 2px;
                    background: {SECONDARY_TEXT_COLOR};
                }}
            """)
        else:
            self.threshold_slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    height: 10px;
                    background: #E9ECEF;
                    border-radius: 5px;
                }}
                QSlider::handle:horizontal {{
                    background: #F8F9FA;
                    border: 3px solid #CED4DA;
                    width: 26px;
                    height: 26px;
                    margin: -10px 0;
                    border-radius: 13px;
                }}
                QSlider::tick:horizontal {{
                    width: 2px;
                    background: #CED4DA;
                }}
            """)

    def update_threshold_value_style(self, value):
        """根據閾值更新數值標籤的樣式"""
        if value >= 70:
            bg_color = ERROR_COLOR
            text_color = "white"
        elif value >= 50:
            bg_color = ACCENT_COLOR
            text_color = "white"
        else:
            bg_color = WARNING_COLOR
            text_color = "black"
        
        self.threshold_value_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 8px 16px;
                border-radius: 18px;
                font-weight: bold;
                font-size: 16pt;
            }}
        """)
        
        # 更新提示卡片高亮
        if hasattr(self, 'tip_labels') and self.tip_labels:
            for i, tip_widget in enumerate(self.tip_labels):
                if (value < 50 and i == 0) or (50 <= value < 70 and i == 1) or (value >= 70 and i == 2):
                    tip_widget.setStyleSheet(f"""
                        QWidget {{
                            background-color: {self.threshold_tips[i][2]}15;
                            border-radius: 6px;
                            padding: 10px;
                            border: 2px solid {self.threshold_tips[i][2]}40;
                        }}
                    """)
                else:
                    tip_widget.setStyleSheet("QWidget { background-color: transparent; }")

    def on_threshold_changed(self, value):
        """當滑桿值改變時"""
        self.threshold_value = value / 100.0
        self.threshold_value_label.setText(f"{value}%")
        self.update_threshold_value_style(value)
        
        # 自動選擇自訂選項
        if self.threshold_slider.isEnabled() and hasattr(self, 'custom_radio') and not self.custom_radio.isChecked():
            self.custom_radio.setChecked(True)

    def set_threshold_preset(self, value):
        """設定預設閾值"""
        self.threshold_value = value
        self.threshold_slider.setValue(int(value * 100))
        self.threshold_slider.setEnabled(False)
        self.update_slider_style()
        self.on_threshold_changed(int(value * 100))

    def enable_custom_threshold(self):
        """啟用自訂閾值"""
        self.threshold_slider.setEnabled(True)
        self.update_slider_style()
        self.on_threshold_changed(self.threshold_slider.value())

    def populate_requirements_tree(self):
        """填充條款樹狀視圖"""
        self._is_updating_checks = True
        self.requirements_tree.clear()
        self.total_requirements_count = 0
        
        if not self.requirements:
            logger.warning("No requirements loaded to populate the tree.")
            self._is_updating_checks = False
            return

        # 按章節分組
        grouped_reqs = {}
        for req_key in sorted(self.requirements.keys()):
            parts = req_key.split('.')
            if len(parts) >= 2:
                chapter_code = f"{parts[0]}.{parts[1]}"
                if chapter_code not in grouped_reqs:
                    grouped_reqs[chapter_code] = []
                grouped_reqs[chapter_code].append(req_key)
            else:
                logger.warning(f"Requirement key '{req_key}' does not match expected format.")

        # 創建樹狀結構
        chapter_font = QFont(self.font())
        chapter_font.setBold(True)
        chapter_font.setPointSize(int(chapter_font.pointSize() * 1.1))

        for chapter_code in sorted(grouped_reqs.keys()):
            chapter_display_name = self.chapter_names.get(chapter_code, chapter_code)
            
            # 父項目（章節）
            parent_item = QTreeWidgetItem(self.requirements_tree)
            parent_item.setText(0, f"{chapter_code} {chapter_display_name}")
            parent_item.setFont(0, chapter_font)
            parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            parent_item.setCheckState(0, Qt.CheckState.Unchecked)

            # 子項目（具體條款）
            for req_key in sorted(grouped_reqs[chapter_code]):
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, req_key)
                child_item.setData(0, Qt.ItemDataRole.UserRole, req_key)
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child_item.setCheckState(0, Qt.CheckState.Unchecked)
                self.total_requirements_count += 1
                
        self.requirements_tree.expandAll()
        self._is_updating_checks = False

    def on_requirement_item_changed(self, item, column):
        """處理條款選擇變化"""
        if self._is_updating_checks:
            return

        self._is_updating_checks = True
        try:
            check_state = item.checkState(0)
            
            # 如果是父項目，更新所有子項目
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child.checkState(0) != check_state:
                        child.setCheckState(0, check_state)
            
            # 如果是子項目，更新父項目狀態
            elif item.parent():
                parent = item.parent()
                checked_children = sum(1 for i in range(parent.childCount()) 
                                     if parent.child(i).checkState(0) == Qt.CheckState.Checked)
                total_children = parent.childCount()
                
                if checked_children == total_children:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                elif checked_children > 0:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                else:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                    
        finally:
            self._is_updating_checks = False
        
        self.update_selection_count()

    def select_folder(self):
        """選擇分析資料夾"""
        initial_path = str(self.folder_path) if self.folder_path else ""
        folder_str = QFileDialog.getExistingDirectory(
            self, 
            "選擇要分析的資料夾", 
            initial_path
        )
        if folder_str:
            self.folder_path = Path(folder_str)
            self.folder_path_edit.setText(str(self.folder_path))
            self.update_analyze_button_state()
            self.status_bar.showMessage(f"📁 已選擇資料夾: {str(self.folder_path)}")
            logger.info(f"Folder selected: {str(self.folder_path)}")

    def on_model_changed(self, index):
        """模型選擇變化"""
        if index == 0:
            self.model_info.setText("🔤 適用於英文文件的快速分析，使用輕量級模型確保高效能")
        else:
            self.model_info.setText("🌐 支援多語言文件分析，包含中文內容，處理時間稍長但準確度更高")
        logger.info(f"Model changed to: {self.model_combo.currentData()}")

    def select_all_requirements(self):
        """選擇所有條款"""
        self._is_updating_checks = True
        
        # 選中所有項目
        iterator = QTreeWidgetItemIterator(self.requirements_tree)
        while iterator.value():
            item = iterator.value()
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(0, Qt.CheckState.Checked)
            iterator += 1
            
        self._is_updating_checks = False
        self.update_selection_count()

    def select_none_requirements(self):
        """取消選擇所有條款"""
        self._is_updating_checks = True
        
        # 取消選中所有項目
        iterator = QTreeWidgetItemIterator(self.requirements_tree)
        while iterator.value():
            item = iterator.value()
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(0, Qt.CheckState.Unchecked)
            iterator += 1
            
        self._is_updating_checks = False
        self.update_selection_count()

    def update_selection_count(self):
        """更新選擇計數"""
        if not hasattr(self, 'requirements_tree') or not self.requirements_tree:
            return
            
        selected_count = 0
        iterator = QTreeWidgetItemIterator(self.requirements_tree)
        while iterator.value():
            item = iterator.value()
            if item.parent() and item.checkState(0) == Qt.CheckState.Checked:
                selected_count += 1
            iterator += 1
            
        self.selection_count_label.setText(f"✅ 已選擇 {selected_count}/{self.total_requirements_count} 個條款")
        self.update_analyze_button_state()

    def get_selected_requirement_count(self):
        """獲取選中的條款數量"""
        if not hasattr(self, 'requirements_tree') or not self.requirements_tree:
            return 0
            
        selected_count = 0
        iterator = QTreeWidgetItemIterator(self.requirements_tree)
        while iterator.value():
            item = iterator.value()
            if item.parent() and item.checkState(0) == Qt.CheckState.Checked:
                selected_count += 1
            iterator += 1
        return selected_count

    def update_analyze_button_state(self):
        """更新分析按鈕狀態"""
        has_folder = bool(self.folder_path)
        has_selection = self.get_selected_requirement_count() > 0
        self.analyze_btn.setEnabled(has_folder and has_selection)

    def analyze(self):
        """開始分析"""
        if not self.folder_path:
            QMessageBox.warning(self, "⚠️ 提示", "請先選擇分析資料夾。")
            return

        # 獲取選中的條款
        selected_requirements_data = {}
        if hasattr(self, 'requirements_tree') and self.requirements_tree:
            iterator = QTreeWidgetItemIterator(self.requirements_tree)
            while iterator.value():
                item = iterator.value()
                if item.parent() and item.checkState(0) == Qt.CheckState.Checked:
                    req_key = item.data(0, Qt.ItemDataRole.UserRole)
                    if req_key and req_key in self.requirements:
                        normalized_key = re.sub(r"\s+", "", req_key.upper())
                        selected_requirements_data[normalized_key] = self.requirements[req_key]
                iterator += 1
        
        if not selected_requirements_data:
            QMessageBox.warning(self, "⚠️ 提示", "請選擇至少一個條款要求進行分析。")
            return

        # 開始分析
        selected_model = self.model_combo.currentData()
        threshold_info = f"相似度閾值: {int(self.threshold_value * 100)}%"
        logger.info(f"Starting analysis with model: {selected_model}, {len(selected_requirements_data)} requirements, threshold: {self.threshold_value}")
        
        self.analyzer = Analyzer(model_name=selected_model)
        self.analyze_btn.setEnabled(False)
        self.fill_worksheet_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不確定進度
        self.progress_bar.setFormat("🔄 正在分析中...")
        self.result_message_widget.setVisible(False)
        self.result_detail.clear()
        self.status_bar.showMessage(f"🔄 正在分析中，請稍候... ({threshold_info})")
        
        # 啟動分析執行緒
        self.analysis_thread = AnalysisThread(
            self.analyzer, 
            str(self.folder_path), # Analyzer expects a string path it converts to Path
            selected_requirements_data,
            self.threshold_value
        )
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()

    def on_analysis_finished(self, results):
        """分析完成處理"""
        self.analysis_results = results
        logger.info(f"Analysis finished with {len(results)} results.")
        
        # 更新UI狀態
        self.progress_bar.setVisible(False)
        self.update_analyze_button_state()
        self.fill_worksheet_btn.setEnabled(len(results) > 0)
        self.result_message_widget.setVisible(True)
        
        threshold_info = f"（相似度閾值: {int(self.threshold_value * 100)}%）"
        
        # 設置結果消息
        if results:
            # 成功圖標
            icon_pixmap = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton).pixmap(24, 24)
            self.result_icon_label.setPixmap(icon_pixmap)
            self.result_message_text.setText(f"✅ 分析完成！共找到 {len(results)} 筆符合結果 {threshold_info}")
            self.result_message_text.setStyleSheet(f"color: {SUCCESS_COLOR}; font-weight: 600;")
            self.result_message_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {SUCCESS_COLOR}10;
                    border: 1px solid {SUCCESS_COLOR}40;
                    border-radius: 8px;
                    padding: 5px;
                }}
            """)
        else:
            # 信息圖標
            icon_pixmap = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(24, 24)
            self.result_icon_label.setPixmap(icon_pixmap)
            self.result_message_text.setText(f"ℹ️ 分析完成，未找到符合的內容 {threshold_info}")
            self.result_message_text.setStyleSheet(f"color: {INFO_COLOR}; font-weight: 600;")
            self.result_message_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {INFO_COLOR}10;
                    border: 1px solid {INFO_COLOR}40;
                    border-radius: 8px;
                    padding: 5px;
                }}
            """)

        # 顯示詳細結果
        self.display_analysis_results(results)
        
        # 更新狀態欄
        if results:
            self.status_bar.showMessage(f"✅ 分析完成 - 找到 {len(results)} 筆結果. 結果保存在 {str(Config.ANALYSIS_OUTPUT)}", 8000)
        else:
            self.status_bar.showMessage(f"ℹ️ 分析完成 - 未找到符合結果，建議調整條件", 8000)

    def display_analysis_results(self, results):
        """顯示分析結果詳情"""
        if results:
            # 生成結果HTML
            html_content = self.generate_results_html(results)
            self.result_detail.setHtml(html_content)
        else:
            # 顯示建議
            self.result_detail.setHtml(f"""
            <div style="padding: 20px; text-align: center; color: {SECONDARY_TEXT_COLOR};">
                <h3 style="color: {INFO_COLOR};">📝 未找到符合的內容</h3>
                <p style="line-height: 1.6; margin: 15px 0;">請嘗試以下方法來改善分析結果：</p>
                <ul style="text-align: left; line-height: 1.8; max-width: 500px; margin: 0 auto;">
                    <li><b>🎯 降低相似度閾值</b> - 擴大搜尋範圍，找到更多潛在相關內容</li>
                    <li><b>📄 確認文件內容</b> - 檢查文件是否與選擇的條款相關</li>
                    <li><b>🔄 嘗試不同模型</b> - 多語言模型可能對中文內容有更好的理解</li>
                    <li><b>📁 檢查文件格式</b> - 確保使用支援的格式（DOCX、XLSX、PDF）</li>
                    <li><b>📋 選擇更多條款</b> - 增加條款範圍可能提高匹配機會</li>
                </ul>
            </div>
            """)

    def generate_results_html(self, results):
        """生成結果HTML內容"""
        html = f"""
        <div style="font-family: 'System UI', Arial, sans-serif; line-height: 1.6;">
            <div style="background: linear-gradient(135deg, {ACCENT_COLOR}15, {SUCCESS_COLOR}15); 
                        padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h2 style="color: {TEXT_COLOR}; margin: 0 0 10px 0;">📊 分析結果摘要</h2>
                <p style="color: {SECONDARY_TEXT_COLOR}; margin: 5px 0;">
                    總共找到 <b style="color: {SUCCESS_COLOR};">{len(results)}</b> 筆符合的內容<br>
                    相似度閾值: <b>{int(self.threshold_value * 100)}%</b>
                </p>
            </div>
        """
        
        # 按條款分組結果
        req_groups = {}
        for result in results:
            req = result.get("requirement", "未知條款")
            if req not in req_groups:
                req_groups[req] = []
            req_groups[req].append(result)
        
        # 顯示每個條款的結果
        for req_key in sorted(req_groups.keys()):
            items = req_groups[req_key]
            html += f"""
            <div style="background-color: {CONTENT_BG_COLOR}; border: 1px solid {BORDER_COLOR}; 
                        border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <h3 style="color: {ACCENT_COLOR}; margin: 0 0 15px 0;">
                    🎯 {req_key} 
                    <span style="color: {SECONDARY_TEXT_COLOR}; font-size: 0.8em; font-weight: normal;">
                        (找到 {len(items)} 筆)
                    </span>
                </h3>
            """
            
            # 顯示前5筆結果
            for i, item in enumerate(items[:5]):
                similarity = item.get('similarity', 0)
                if isinstance(similarity, float):
                    similarity_str = f"{similarity:.1%}"
                    similarity_color = ERROR_COLOR if similarity >= 0.8 else ACCENT_COLOR if similarity >= 0.6 else WARNING_COLOR
                else:
                    similarity_str = "N/A"
                    similarity_color = SECONDARY_TEXT_COLOR
                
                snippet = item.get('snippet', 'N/A')
                source_file = item.get('source_file', 'N/A')
                
                # 文件名處理
                if source_file != 'N/A':
                    # source_file is already a string from Analyzer results, which itself ensures it's a string
                    file_name = Path(source_file).name
                else:
                    file_name = 'N/A'
                
                html += f"""
                <div style="background-color: #F8F9FA; border-left: 4px solid {similarity_color}; 
                            padding: 12px; margin: 8px 0; border-radius: 0 4px 4px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 600; color: {TEXT_COLOR};">#{i+1}</span>
                        <span style="background-color: {similarity_color}; color: white; 
                                     padding: 2px 8px; border-radius: 12px; font-size: 0.9em; font-weight: 600;">
                            {similarity_str}
                        </span>
                    </div>
                    <p style="margin: 5px 0; color: {SECONDARY_TEXT_COLOR}; font-size: 0.9em;">
                        📁 <b>來源:</b> {file_name}
                    </p>
                    <p style="margin: 8px 0 0 0; color: {TEXT_COLOR}; 
                              background-color: white; padding: 10px; border-radius: 4px; 
                              border: 1px solid {BORDER_COLOR};">
                        <b>內容:</b> {snippet[:200]}{'...' if len(snippet) > 200 else ''}
                    </p>
                </div>
                """
            
            # 如果有更多結果
            if len(items) > 5:
                html += f"""
                <p style="text-align: center; color: {SECONDARY_TEXT_COLOR}; 
                          font-style: italic; margin-top: 15px;">
                    ⋯ 還有 {len(items) - 5} 筆結果未完整顯示
                </p>
                """
            
            html += "</div>"
        
        html += "</div>"
        return html

    def on_analysis_error(self, error_msg):
        """分析錯誤處理"""
        logger.error(f"Analysis error: {error_msg}")
        
        # 更新UI狀態
        self.progress_bar.setVisible(False)
        self.update_analyze_button_state()
        self.fill_worksheet_btn.setEnabled(False)
        self.result_message_widget.setVisible(True)
        
        # 錯誤圖標和消息
        icon_pixmap = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical).pixmap(24, 24)
        self.result_icon_label.setPixmap(icon_pixmap)
        self.result_message_text.setText("❌ 分析過程中發生錯誤")
        self.result_message_text.setStyleSheet(f"color: {ERROR_COLOR}; font-weight: 600;")
        self.result_message_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {ERROR_COLOR}10;
                border: 1px solid {ERROR_COLOR}40;
                border-radius: 8px;
                padding: 5px;
            }}
        """)
        
        # 顯示錯誤詳情
        self.result_detail.setHtml(f"""
        <div style="padding: 20px; color: {ERROR_COLOR};">
            <h3>❌ 分析錯誤</h3>
            <p style="background-color: #FFF5F5; padding: 15px; border-radius: 6px; 
                      border: 1px solid {ERROR_COLOR}40; line-height: 1.6;">
                <b>錯誤詳情:</b><br>
                <code style="font-family: monospace; background-color: white; 
                             padding: 2px 4px; border-radius: 3px;">{error_msg}</code>
            </p>
            <p style="color: {SECONDARY_TEXT_COLOR}; margin-top: 15px;">
                <b>建議解決方法:</b><br>
                • 檢查所選資料夾是否包含有效的文件<br>
                • 確認模型文件是否完整<br>
                • 重新啟動應用程式再試<br>
                • 如問題持續，請聯繫技術支援
            </p>
        </div>
        """)
        
        # 顯示錯誤對話框
        QMessageBox.critical(self, "❌ 分析錯誤", f"分析過程中發生錯誤：\n\n{error_msg}")
        self.status_bar.showMessage("❌ 分析失敗", 8000)

    def fill_worksheet(self):
        """填入工作表"""
        if not self.analysis_results:
            QMessageBox.information(self, "ℹ️ 提示", "請先執行分析並取得結果。")
            return

        self.fill_worksheet_btn.setEnabled(False)
        self.status_bar.showMessage("📝 正在填入 Worksheet...")

        try:
            # Assuming WorksheetUpdater is updated to use Config.ANALYSIS_OUTPUT and Config.WORKSHEET_FILE directly
            # or that it will be refactored to accept Path objects if needed.
            # The current call in the provided code is WorksheetUpdater.update_worksheet()
            # If it were to take paths:
            # success, message = WorksheetUpdater.update_worksheet(Config.ANALYSIS_OUTPUT, Config.WORKSHEET_FILE)
            # For now, sticking to the existing call signature from the provided code.
            success, message = WorksheetUpdater.update_worksheet()
            if success:
                QMessageBox.information(self, "✅ 成功", f"📝 {message}\nWorksheet 已更新: {str(Config.WORKSHEET_FILE)}")
                self.status_bar.showMessage(f"✅ Worksheet 填入完成: {str(Config.WORKSHEET_FILE)}", 8000)
            else:
                QMessageBox.warning(self, "⚠️ 失敗", f"📝 {message}")
                self.status_bar.showMessage("⚠️ Worksheet 填入失敗", 8000)
        except Exception as e:
            logger.error(f"Error filling worksheet: {e}", exc_info=True)
            QMessageBox.critical(self, "❌ 錯誤", f"填入 Worksheet 時發生錯誤:\n\n{e}\nWorksheet路徑: {str(Config.WORKSHEET_FILE)}")
            self.status_bar.showMessage("❌ Worksheet 填入時發生錯誤", 8000)
        finally:
            self.fill_worksheet_btn.setEnabled(True)

    def resizeEvent(self, event):
        """視窗大小改變事件"""
        super().resizeEvent(event)
        
        # 添加安全檢查，確保組件已經初始化完成
        if hasattr(self, 'main_splitter') and self.main_splitter is not None:
            # 使用 QTimer 延遲執行，避免頻繁調用
            if not hasattr(self, '_resize_timer'):
                self._resize_timer = QTimer()
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self.update_responsive_layout)
            
            self._resize_timer.stop()
            self._resize_timer.start(50)  # 50ms 延遲

    def closeEvent(self, event):
        """視窗關閉事件"""
        try:
            # 停止分析執行緒
            if hasattr(self, 'analysis_thread') and self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.terminate()
                self.analysis_thread.wait(3000)  # 等待最多 3 秒
            
            # 清理計時器
            if hasattr(self, '_resize_timer'):
                self._resize_timer.stop()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            event.accept()


if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    
    # 設置應用程式屬性
    app.setApplicationName("IEC 62443-2-4 符合性分析工具")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Security Analysis Tools")
    
    # 創建並顯示主視窗
    window = ConformityAnalysisWindow()
    window.show()
    
    sys.exit(app.exec())