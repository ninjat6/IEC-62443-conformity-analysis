# dialogs/floating_dialog.py
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget, QGridLayout,
    QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from widgets.draggable_label import DraggableLabel
from utils.file_processor import FileProcessor  # 引入檔案處理工具
# Assuming path_utils.py is in the project root and accessible in PYTHONPATH
from path_utils import get_reports_dir
from utils.logger import logger # Assuming logger is set up in utils

class FloatingDialog(QDialog):
    """
    浮動對話框：
    - 當 json_data 為 None 且 multi_level 為 True 時，會進入多階層瀏覽模式，
      先顯示指定 WORD 檔根目錄下的各階層資料夾按鈕。
    - 當有 json_data 時，則直接以 DraggableLabel 顯示 JSON 資料。
    - 同時支援呼叫 FileProcessor.process_file 處理檔案產生 JSON，
      並動態更新介面。
    """
    def __init__(self, json_data=None, parent=None, multi_level=False, 
                 word_root_dir_str: str = None, default_output_dir_str: str = None):
        super().__init__(parent)
        self.json_data = json_data
        self.multi_level = multi_level
        self.current_stage_name = None # Stores the name of the current stage folder
        self.in_file_list_mode = False

        # Initialize word_root path
        if word_root_dir_str:
            self.word_root = Path(word_root_dir_str).resolve()
            logger.info(f"FloatingDialog: Using provided Word source directory: {self.word_root}")
        else:
            self.word_root = Path.home() / "Documents" / "IEC62443_Word_Sources"
            logger.info(f"FloatingDialog: Word source directory not provided. Defaulting to: {self.word_root}. This should ideally be user-configurable.")
        self.word_root.mkdir(parents=True, exist_ok=True)

        # Initialize output_dir path
        if default_output_dir_str:
            self.output_dir = Path(default_output_dir_str).resolve()
            logger.info(f"FloatingDialog: Using provided output directory: {self.output_dir}")
        else:
            self.output_dir = get_reports_dir() / "Processed_JSONs"
            logger.info(f"FloatingDialog: Output directory not provided. Defaulting to: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

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

        if self.multi_level and self.json_data is None:
            self.init_multi_level_ui()
        else:
            self.display_json_data(self.json_data)

        self.adjust_labels_on_resize()

    def init_multi_level_ui(self):
        """
        初始化多階層瀏覽介面：顯示 WORD 根目錄下所有子資料夾按鈕
        """
        self.clear_grid_layout(self.grid_layout)
        self.labels = []
        self.current_stage_name = None
        self.in_file_list_mode = False

        if not self.word_root.is_dir():
            msg = f"Word source directory not found or is not a directory: {self.word_root}"
            logger.error(msg)
            label = QLabel(msg)
            self.grid_layout.addWidget(label, 0, 0)
            return

        subfolders = []
        try:
            for entry in self.word_root.iterdir():
                if entry.is_dir():
                    subfolders.append(entry.name)
        except Exception as e:
            logger.error(f"Error scanning word_root directory {self.word_root}: {e}")
            QMessageBox.critical(self, "Error", f"Could not read Word source directory: {e}")
            return
            
        subfolders.sort()

        if not subfolders:
            label = QLabel(f"未找到任何階層資料夾於: {self.word_root}")
            self.grid_layout.addWidget(label, 0, 0)
            return

        for idx, folder_name_str in enumerate(subfolders):
            btn = QPushButton(folder_name_str)
            btn.clicked.connect(lambda _, f=folder_name_str: self.show_files_in_stage(f))
            self.grid_layout.addWidget(btn, idx // 3, idx % 3)

    def show_files_in_stage(self, folder_name_str: str): # folder_name_str is just the name, not full path
        """
        顯示指定階層資料夾中的檔案（支援 .doc、.docx、.xlsx）
        """
        self.clear_grid_layout(self.grid_layout)
        self.labels = []
        self.in_file_list_mode = True
        self.current_stage_name = folder_name_str # Store the name of the stage

        stage_path_obj = self.word_root / folder_name_str
        if not stage_path_obj.is_dir():
            msg = f"找不到資料夾：{stage_path_obj}"
            logger.error(msg)
            label = QLabel(msg)
            self.grid_layout.addWidget(label, 0, 0)
            return

        files = []
        try:
            for entry in stage_path_obj.iterdir():
                if entry.is_file():
                    # Suffix includes the dot, e.g., ".docx"
                    ext = entry.suffix.lower()
                    if ext in ['.doc', '.docx', '.xlsx']:
                        files.append(entry.name) # Store only the filename string
        except Exception as e:
            logger.error(f"Error scanning stage directory {stage_path_obj}: {e}")
            QMessageBox.critical(self, "Error", f"Could not read stage directory: {e}")
            return
            
        files.sort()

        if not files:
            label = QLabel(f"{folder_name_str} 資料夾內沒有可處理的檔案。")
            self.grid_layout.addWidget(label, 0, 0)
            return

        back_btn = QPushButton("← Back (Stages)")
        back_btn.clicked.connect(self.init_multi_level_ui)
        self.grid_layout.addWidget(back_btn, 0, 0)

        row_start = 1
        for i, fname_str in enumerate(files):
            btn = QPushButton(fname_str)
            # Pass stage_path_obj (Path object) and fname_str (string)
            btn.clicked.connect(lambda _, fn=fname_str, sp=stage_path_obj: self.run_file_processor(sp, fn))
            self.grid_layout.addWidget(btn, (i + row_start) // 3, (i + row_start) % 3)

    def run_file_processor(self, current_stage_path_obj: Path, filename_str: str):
        """
        呼叫 FileProcessor.process_file 處理檔案，
        產生中英文 JSON，並以英文 JSON 更新介面
        """
        input_path_obj = current_stage_path_obj / filename_str
        
        try:
            logger.info(f"Processing file: {input_path_obj} with output to {self.output_dir}")
            # FileProcessor.process_file will be refactored later.
            # For now, assume it might still expect string paths.
            result = FileProcessor.process_file(str(input_path_obj), str(self.output_dir))
            
            english_json_path_str = result.get("english_json")
            if not english_json_path_str:
                QMessageBox.warning(self, "Error", "英文 JSON 路徑未返回。")
                return

            english_json_path_obj = Path(english_json_path_str)
            if not english_json_path_obj.exists():
                QMessageBox.warning(self, "Error", f"找不到英文 JSON：\n{english_json_path_str}")
                return
            
            with open(english_json_path_obj, "r", encoding="utf-8") as f: # open() supports Path
                new_json_data = json.load(f)
            self.display_json_data(new_json_data)
        except Exception as e:
            logger.error(f"Error processing file {input_path_obj}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"處理檔案 '{filename_str}' 時發生錯誤：\n{str(e)}")

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
