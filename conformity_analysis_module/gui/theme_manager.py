# gui/theme_manager.py
"""
主題管理器：支援淺色/深色模式切換
"""

import platform
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings, QObject, pyqtSignal


class ThemeManager(QObject):
    """
    主題管理器 (單例模式)

    功能：
    - 淺色/深色模式切換
    - 自動偵測系統主題
    - 儲存使用者偏好設定
    """

    theme_changed = pyqtSignal(str)  # 主題變更信號

    LIGHT_THEME = {
        'name': 'light',
        'bg': '#F8F9FA',
        'content_bg': '#FFFFFF',
        'text': '#212529',
        'secondary_text': '#6C757D',
        'border': '#DDE1E6',
        'accent': '#007AFF',
        'accent_hover': '#005ECB',
        'accent_pressed': '#004BA0',
        'success': '#198754',
        'warning': '#FFC107',
        'error': '#DC3545',
        'info': '#17A2B8',
        'disabled_bg': '#E9ECEF',
        'disabled_text': '#ADB5BD',
        'hover_bg': '#F1F3F5',
        'pressed_bg': '#E9ECEF',
        'scrollbar_bg': '#F1F3F5',
        'scrollbar_handle': '#C1C7CD',
        'input_bg': '#FFFFFF',
        'card_shadow': 'rgba(0, 0, 0, 0.08)',
    }

    DARK_THEME = {
        'name': 'dark',
        'bg': '#121212',
        'content_bg': '#1E1E1E',
        'text': '#E0E0E0',
        'secondary_text': '#A0A0A0',
        'border': '#333333',
        'accent': '#0A84FF',
        'accent_hover': '#409CFF',
        'accent_pressed': '#0066CC',
        'success': '#32D74B',
        'warning': '#FFD60A',
        'error': '#FF453A',
        'info': '#64D2FF',
        'disabled_bg': '#2C2C2C',
        'disabled_text': '#5C5C5C',
        'hover_bg': '#2A2A2A',
        'pressed_bg': '#3A3A3A',
        'scrollbar_bg': '#1E1E1E',
        'scrollbar_handle': '#4A4A4A',
        'input_bg': '#2C2C2C',
        'card_shadow': 'rgba(0, 0, 0, 0.3)',
    }

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True

        self.settings = QSettings("IEC62443", "ConformityAnalysis")
        saved_theme = self.settings.value("theme", "")

        if saved_theme:
            self._current_theme = saved_theme
        else:
            # 自動偵測系統主題
            self._current_theme = self._detect_system_theme()

    def _detect_system_theme(self) -> str:
        """偵測系統主題"""
        system = platform.system()

        if system == 'Windows':
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return 'light' if value == 1 else 'dark'
            except Exception:
                pass
        elif system == 'Darwin':  # macOS
            try:
                import subprocess
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True, text=True
                )
                return 'dark' if 'Dark' in result.stdout else 'light'
            except Exception:
                pass

        return 'light'  # 預設淺色

    @property
    def current_theme(self) -> str:
        """取得當前主題名稱"""
        return self._current_theme

    def get_theme(self) -> dict:
        """取得當前主題配色"""
        return self.DARK_THEME if self._current_theme == 'dark' else self.LIGHT_THEME

    def get_color(self, key: str) -> str:
        """取得特定顏色值"""
        return self.get_theme().get(key, '#000000')

    def set_theme(self, theme_name: str) -> None:
        """設定主題"""
        if theme_name not in ('light', 'dark'):
            return

        self._current_theme = theme_name
        self.settings.setValue("theme", theme_name)
        self._apply_stylesheet()
        self.theme_changed.emit(theme_name)

    def toggle_theme(self) -> str:
        """切換主題"""
        new_theme = 'light' if self._current_theme == 'dark' else 'dark'
        self.set_theme(new_theme)
        return new_theme

    def is_dark(self) -> bool:
        """是否為深色模式"""
        return self._current_theme == 'dark'

    def _apply_stylesheet(self) -> None:
        """套用全域樣式表"""
        app = QApplication.instance()
        if not app:
            return

        theme = self.get_theme()
        stylesheet = self._generate_stylesheet(theme)
        app.setStyleSheet(stylesheet)

    def _generate_stylesheet(self, theme: dict) -> str:
        """生成 QSS 樣式表"""
        return f'''
            /* 全域設定 */
            QMainWindow, QWidget {{
                background-color: {theme['bg']};
                color: {theme['text']};
                font-family: "Segoe UI", "Microsoft JhengHei", sans-serif;
            }}

            /* 分組框 */
            QGroupBox {{
                font-size: 11pt;
                font-weight: 500;
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: {theme['content_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 8px;
                background-color: {theme['content_bg']};
                color: {theme['secondary_text']};
                font-weight: 600;
            }}

            /* 按鈕 */
            QPushButton {{
                background-color: {theme['content_bg']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 500;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {theme['hover_bg']};
                border-color: {theme['accent']};
            }}
            QPushButton:pressed {{
                background-color: {theme['pressed_bg']};
            }}
            QPushButton:disabled {{
                background-color: {theme['disabled_bg']};
                color: {theme['disabled_text']};
                border-color: {theme['border']};
            }}

            /* 主要按鈕 */
            QPushButton[primary="true"] {{
                background-color: {theme['accent']};
                color: white;
                border: none;
            }}
            QPushButton[primary="true"]:hover {{
                background-color: {theme['accent_hover']};
            }}
            QPushButton[primary="true"]:pressed {{
                background-color: {theme['accent_pressed']};
            }}

            /* 樹狀視圖 */
            QTreeWidget {{
                background-color: {theme['content_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 5px;
                outline: none;
                font-size: 10pt;
            }}
            QTreeWidget::item {{
                padding: 8px 5px;
                color: {theme['text']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QTreeWidget::item:selected {{
                background-color: {theme['accent']};
                color: white;
            }}
            QTreeWidget::item:hover:!selected {{
                background-color: {theme['hover_bg']};
            }}

            /* 文字編輯框 */
            QTextEdit {{
                background-color: {theme['content_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'SF Mono', 'Monaco', monospace;
                font-size: 10pt;
                color: {theme['text']};
            }}

            /* 下拉選單 */
            QComboBox {{
                background-color: {theme['content_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 20px;
                font-size: 10pt;
                color: {theme['text']};
            }}
            QComboBox:hover {{
                border-color: {theme['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['content_bg']};
                border: 1px solid {theme['border']};
                selection-background-color: {theme['accent']};
                selection-color: white;
            }}

            /* 進度條 */
            QProgressBar {{
                background-color: {theme['disabled_bg']};
                border: none;
                border-radius: 4px;
                text-align: center;
                font-size: 9pt;
                color: {theme['secondary_text']};
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: {theme['accent']};
                border-radius: 4px;
            }}

            /* 核取方塊 */
            QCheckBox {{
                spacing: 8px;
                font-size: 10pt;
                color: {theme['text']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {theme['secondary_text']};
                border-radius: 4px;
                background-color: {theme['content_bg']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme['accent']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme['accent']};
                border-color: {theme['accent']};
            }}

            /* 輸入框 */
            QLineEdit {{
                padding: 10px 12px;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                background-color: {theme['input_bg']};
                color: {theme['text']};
                font-size: 10pt;
                min-height: 16px;
            }}
            QLineEdit:focus {{
                border-color: {theme['accent']};
            }}
            QLineEdit:read-only {{
                background-color: {theme['hover_bg']};
                color: {theme['secondary_text']};
            }}

            /* 單選按鈕 */
            QRadioButton {{
                spacing: 10px;
                font-size: 10pt;
                color: {theme['text']};
                padding: 4px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {theme['secondary_text']};
                border-radius: 9px;
                background-color: {theme['content_bg']};
            }}
            QRadioButton::indicator:hover {{
                border-color: {theme['accent']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {theme['accent']};
                border-color: {theme['accent']};
            }}

            /* 滾動條 */
            QScrollBar:vertical {{
                background-color: {theme['scrollbar_bg']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme['scrollbar_handle']};
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme['secondary_text']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}

            QScrollBar:horizontal {{
                background-color: {theme['scrollbar_bg']};
                height: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {theme['scrollbar_handle']};
                border-radius: 6px;
                min-width: 20px;
                margin: 2px;
            }}

            /* 分割器 */
            QSplitter::handle {{
                background: {theme['bg']};
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
                background: {theme['border']};
            }}
            QSplitter::handle:pressed {{
                background: {theme['accent']};
            }}

            /* 狀態列 */
            QStatusBar {{
                background-color: {theme['content_bg']};
                color: {theme['secondary_text']};
                font-size: 10pt;
                border-top: 1px solid {theme['border']};
                padding: 8px 15px;
            }}

            /* 標籤 */
            QLabel {{
                color: {theme['text']};
                font-size: 10pt;
            }}

            /* 滾動區域 */
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}

            /* 訊息框 */
            QMessageBox {{
                background-color: {theme['content_bg']};
            }}
            QMessageBox QLabel {{
                color: {theme['text']};
            }}

            /* 選單 */
            QMenu {{
                background-color: {theme['content_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 20px;
                border-radius: 4px;
                color: {theme['text']};
            }}
            QMenu::item:selected {{
                background-color: {theme['accent']};
                color: white;
            }}

            /* 工具提示 */
            QToolTip {{
                background-color: {theme['content_bg']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 5px 10px;
            }}

            /* 滑桿 */
            QSlider::groove:horizontal {{
                height: 10px;
                background: {theme['disabled_bg']};
                border-radius: 5px;
            }}
            QSlider::handle:horizontal {{
                background: {theme['content_bg']};
                border: 3px solid {theme['accent']};
                width: 26px;
                height: 26px;
                margin: -10px 0;
                border-radius: 13px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {theme['accent']};
                border: 3px solid {theme['content_bg']};
            }}
        '''

    def apply_theme(self) -> None:
        """套用當前主題"""
        self._apply_stylesheet()


# 全域便捷函數
def get_theme_manager() -> ThemeManager:
    """取得主題管理器實例"""
    return ThemeManager()


def get_color(key: str) -> str:
    """取得顏色值"""
    return get_theme_manager().get_color(key)


def is_dark_mode() -> bool:
    """是否為深色模式"""
    return get_theme_manager().is_dark()
