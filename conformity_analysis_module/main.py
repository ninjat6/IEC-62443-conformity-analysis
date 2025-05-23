# conformity_analysis_module/main.py
import sys
import os
from PyQt6.QtWidgets import QApplication
from conformity_analysis_module.gui.main_window import ConformityAnalysisWindow

# 將專案根目錄加入 sys.path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

class ConformityAnalysis:
    """
    ConformityAnalysis 是整合所有功能的主要入口，
    其他程式只需實例化此類別並呼叫 run()，即可啟動完整的文件搜尋工具。
    """
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = ConformityAnalysisWindow()

    def run(self):
        """啟動應用程式"""
        self.window.show()
        sys.exit(self.app.exec())

# 僅在獨立執行時啟動
if __name__ == "__main__":
    app = ConformityAnalysis()
    app.run()