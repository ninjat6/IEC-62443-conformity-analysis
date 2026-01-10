# dialogs/floating_dialog.py

import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget, QGridLayout,
    QLabel, QPushButton, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QSettings
from widgets.draggable_label import DraggableLabel
from utils.text_splitter import TextSplitter  # 引入文字分離工具

class FloatingDialog(QDialog):
    """
    浮動對話框：
    - 當 json_data 為 None 且 multi_level 為 True 時，會進入多階層瀏覽模式，
      先顯示指定 WORD 檔根目錄下的各階層資料夾按鈕。
    - 當有 json_data 時，則直接以 DraggableLabel 顯示 JSON 資料。
    - 同時支援呼叫 TextSplitter.process_file 處理檔案產生 JSON，
      並動態更新介面。
    """
    def __init__(self, json_data=None, parent=None, multi_level=False):
        super().__init__(parent)
        self.json_data = json_data
        self.multi_level = multi_level
        self.current_folder = None
        self.in_file_list_mode = False

        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("Draggable JSON Elements (Floating)")
        self.setGeometry(300, 300, 600, 500)

        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.scroll_area.setWidget(self.content_widget)

        self.labels = []

        # 根據模式決定初始介面
        if self.multi_level and self.json_data is None:
            self.init_multi_level_ui()
        else:
            self.display_json_data(self.json_data)

        self.adjust_labels_on_resize()

    def init_multi_level_ui(self):
        """
        初始化多階層瀏覽介面：顯示指定 WORD 根目錄下所有子資料夾按鈕
        """
        self.clear_grid_layout(self.grid_layout)
        self.labels = []
        self.current_folder = None
        self.in_file_list_mode = False

        # 從設定讀取 WORD 檔根目錄，若無則請使用者選擇
        settings = QSettings("IEC62443", "ConformityAnalysis")
        self.word_root = settings.value("word_root_path", "")

        if not self.word_root or not os.path.isdir(self.word_root):
            # 顯示選擇資料夾按鈕
            select_btn = QPushButton("📁 選擇 WORD 檔案目錄...")
            select_btn.clicked.connect(self._select_word_root)
            self.grid_layout.addWidget(select_btn, 0, 0)

            hint_label = QLabel("請選擇包含 WORD 檔案的根目錄")
            hint_label.setStyleSheet("color: #666;")
            self.grid_layout.addWidget(hint_label, 1, 0)
            return

        subfolders = [entry.name for entry in os.scandir(self.word_root) if entry.is_dir()]
        subfolders.sort()

        if not subfolders:
            label = QLabel("未找到任何階層資料夾。")
            self.grid_layout.addWidget(label, 0, 0)
            return

        for idx, folder in enumerate(subfolders):
            btn = QPushButton(folder)
            # 避免 lambda 閉包問題，使用預設參數
            btn.clicked.connect(lambda _, f=folder: self.show_files_in_stage(f))
            self.grid_layout.addWidget(btn, idx // 3, idx % 3)

    def show_files_in_stage(self, folder_name):
        """
        顯示指定階層資料夾中的檔案（支援 .doc、.docx、.xlsx）
        """
        self.clear_grid_layout(self.grid_layout)
        self.labels = []
        self.in_file_list_mode = True
        self.current_folder = folder_name

        stage_path = os.path.join(self.word_root, folder_name)
        if not os.path.isdir(stage_path):
            label = QLabel(f"找不到資料夾：{stage_path}")
            self.grid_layout.addWidget(label, 0, 0)
            return

        files = []
        for entry in os.scandir(stage_path):
            if entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in ['.doc', '.docx', '.xlsx']:
                    files.append(entry.name)
        files.sort()

        if not files:
            label = QLabel(f"{folder_name} 資料夾內沒有可處理的檔案。")
            self.grid_layout.addWidget(label, 0, 0)
            return

        # 返回按鈕：回到階層清單
        back_btn = QPushButton("← Back (Stages)")
        back_btn.clicked.connect(self.init_multi_level_ui)
        self.grid_layout.addWidget(back_btn, 0, 0)

        row_start = 1
        for i, fname in enumerate(files):
            btn = QPushButton(fname)
            btn.clicked.connect(lambda _, fn=fname, sp=stage_path: self.run_file_processor(sp, fn))
            self.grid_layout.addWidget(btn, (i + row_start) // 3, (i + row_start) % 3)

    def _select_word_root(self):
        """讓使用者選擇 WORD 檔案根目錄"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "選擇 WORD 檔案目錄",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            # 儲存設定
            settings = QSettings("IEC62443", "ConformityAnalysis")
            settings.setValue("word_root_path", folder)
            # 重新初始化介面
            self.init_multi_level_ui()

    def _get_output_dir(self):
        """取得輸出目錄，若不存在則建立"""
        # 使用專案內的 resources/output_json 目錄
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "resources", "output_json")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def run_file_processor(self, folder_path, filename):
        """
        呼叫 TextSplitter.process_file 處理檔案，
        產生中英文 JSON，並以英文 JSON 更新介面
        """
        input_path = os.path.join(folder_path, filename)
        output_dir = self._get_output_dir()
        try:
            # 呼叫 utils/text_splitter.py 中的 process_file 方法
            result = TextSplitter.process_file(input_path, output_dir)
            english_json_path = result.get("english_json")
            if not english_json_path or not os.path.exists(english_json_path):
                QMessageBox.warning(self, "Error", f"找不到英文 JSON：\n{english_json_path}")
                return
            with open(english_json_path, "r", encoding="utf-8") as f:
                new_json_data = json.load(f)
            self.display_json_data(new_json_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"處理檔案時發生錯誤：\n{str(e)}")

    def display_json_data(self, json_data):
        """
        將 JSON 資料清單以 DraggableLabel 呈現，並在多階層模式下提供返回檔案清單的按鈕。
        """
        self.clear_grid_layout(self.grid_layout)
        self.labels = []
        self.json_data = json_data if json_data else []
        self.in_file_list_mode = False

        if self.multi_level and self.current_folder:
            back_btn = QPushButton("← Back (File List)")
            back_btn.clicked.connect(lambda: self.show_files_in_stage(self.current_folder))
            self.grid_layout.addWidget(back_btn, 0, 0)
            start_row = 1
        else:
            start_row = 0

        if not isinstance(self.json_data, list) or not self.json_data:
            label = QLabel("No JSON data available.")
            self.grid_layout.addWidget(label, start_row, 0)
            return

        for index, item in enumerate(self.json_data):
            label = DraggableLabel(item, item)
            self.labels.append(label)
            row = (index + start_row) // 5
            col = (index + start_row) % 5
            self.grid_layout.addWidget(label, row, col)

        self.adjust_labels_on_resize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_labels_on_resize()

    def adjust_labels_on_resize(self):
        """
        根據對話框寬度動態調整每個 DraggableLabel 的尺寸
        """
        dialog_width = self.width()
        label_width = max((dialog_width - 100) // 5, 100)
        label_height = 50
        for lbl in self.labels:
            lbl.set_size(label_width, label_height)

    @staticmethod
    def clear_grid_layout(grid_layout):
        """
        清除 grid_layout 內所有 widget 以便重新排版
        """
        while grid_layout.count():
            item = grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
