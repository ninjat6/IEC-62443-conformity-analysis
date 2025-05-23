# 在 config.py 中添加此函數
import os
import sys

def resource_path(relative_path):
    """獲取資源的絕對路徑，適用於開發環境和 PyInstaller 打包後的環境"""
    if getattr(sys, 'frozen', False):
        # 如果是在打包的應用程式中運行
        base_path = sys._MEIPASS
    else:
        # 如果是在開發環境中運行
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class Config:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    LOG_DIR = os.path.join(ROOT_DIR, "log")
    
    # 使用 resource_path 處理需要打包的資源路徑
    REQUIREMENTS_FILE = resource_path(os.path.join("..", "requirements_cn.json"))
    ANALYSIS_OUTPUT = os.path.join(ROOT_DIR, "analysis_results.json")
    WORKSHEET_FILE = resource_path(os.path.join("..", "template", "IEC62443_2_4d_2024-worksheet.xlsx"))
    DOCX_CACHE_FILE = os.path.join(ROOT_DIR, "docx_contents.json")

    @staticmethod
    def ensure_dir(directory):
        if not os.path.exists(directory):
            os.makedirs(directory)