from PyQt6.QtCore import Qt, pyqtSlot, QThread
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QListWidget, QListWidgetItem, QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QProgressBar, QMenuBar, QMenu, QStatusBar, QScrollArea
)

from file_search_module.ui.results_container import ResultsContainer
from file_search_module.ui.result_card import ResultCard
from file_search_module.search.search_worker import SearchWorker
from file_search_module.converters.file_converter import convert_file_to_html
from file_search_module.viewers.html_viewer import HtmlViewer

class FileSearcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("最完美頂級UI - 文件內容搜尋工具 (RWD 版)")
        self.adjust_window_size()
        self.search_worker = None
        self.worker_thread = None
        self.open_viewers = []  # 避免檢視器被 GC 回收
        self.init_menu()
        self.init_status_bar()
        self.init_ui()
    
    def adjust_window_size(self):
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        w = int(screen_geo.width() * 0.8)
        h = int(screen_geo.height() * 0.8)
        x = (screen_geo.width() - w) // 2
        y = (screen_geo.height() - h) // 2
        self.setGeometry(x, y, w, h)
    
    def init_menu(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        file_menu = QMenu("檔案", self)
        menu_bar.addMenu(file_menu)
        about_action = QAction("關於", self)
        about_action.triggered.connect(self.show_about_dialog)
        file_menu.addAction(about_action)
        exit_action = QAction("離開", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
    
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_widget.setLayout(main_layout)
        
        # 左側選單區
        self.left_frame = QFrame()
        self.left_frame.setObjectName("LeftFrame")
        left_layout = QVBoxLayout()
        self.left_frame.setLayout(left_layout)
        self.conversation_list = QListWidget()
        items = ["SP.01", "SP.02", "SP.03", "SP.04", "SP.05", "SP.06", "SP.07", "SP.08", "SP.09", "SP.10", "SP.11", "SP.12"]
        for text in items:
            self.conversation_list.addItem(QListWidgetItem(text))
        left_layout.addWidget(self.conversation_list)
        
        # 右側搜尋與結果展示區
        self.right_frame = QFrame()
        self.right_frame.setObjectName("RightFrame")
        right_layout = QVBoxLayout(self.right_frame)
        self.right_frame.setLayout(right_layout)
        
        # 搜尋列
        top_search_bar = QFrame()
        top_search_bar.setObjectName("TopSearchBar")
        top_layout = QHBoxLayout(top_search_bar)
        top_layout.setContentsMargins(10, 10, 10, 10)
        self.folder_path = QLineEdit()
        self.folder_path.setPlaceholderText("請選擇或輸入想要搜尋的資料夾路徑...")
        self.browse_button = QPushButton("瀏覽")
        self.browse_button.clicked.connect(self.browse_folder)
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("輸入關鍵字...")
        self.search_button = QPushButton("搜尋")
        self.search_button.clicked.connect(self.start_search)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_search)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("尚未開始...")
        top_layout.addWidget(self.folder_path)
        top_layout.addWidget(self.browse_button)
        top_layout.addWidget(self.keyword_input)
        top_layout.addWidget(self.search_button)
        top_layout.addWidget(self.cancel_button)
        top_layout.addWidget(self.progress_bar)
        right_layout.addWidget(top_search_bar)
        
        # 搜尋結果標題
        title_label = QLabel("搜尋結果：")
        font_title = QFont()
        font_title.setPointSize(14)
        font_title.setBold(True)
        title_label.setFont(font_title)
        right_layout.addWidget(title_label)
        
        # 結果捲動區
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 使用自訂 ResultsContainer 替代一般 QWidget
        self.results_container = ResultsContainer()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(10, 10, 10, 10)
        self.results_layout.setSpacing(10)
        scroll_area.setWidget(self.results_container)
        right_layout.addWidget(scroll_area)
        
        main_layout.addWidget(self.left_frame, 2)
        main_layout.addWidget(self.right_frame, 8)
        
        # 全域 StyleSheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ECECF1;
            }
            #LeftFrame {
                background-color: #F7F7F9;
                border-right: 1px solid #DDDDDD;
            }
            QListWidget {
                border: none;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #DCECFD;
                color: #000000;
            }
            #RightFrame {
                background-color: #FFFFFF;
            }
            #TopSearchBar {
                background-color: #F3F3F3;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #5E9EFF;
                color: #ffffff;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #4A8DF8;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                min-width: 120px;
            }
            QProgressBar::chunk {
                background-color: #4A8DF8;
                border-radius: 4px;
            }
            #ResultCard {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            #ResultCard[hover="true"] {
                background-color: #EEF9FF;
                border: 1px solid #BBDFFF;
            }
        """)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if folder:
            self.folder_path.setText(folder)
    
    def start_search(self):
        folder = self.folder_path.text().strip()
        keyword = self.keyword_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "警告", "請先選擇資料夾！")
            return
        if not keyword:
            QMessageBox.warning(self, "警告", "請輸入關鍵字！")
            return
        
        # 清除舊結果
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("搜尋中...")
        self.search_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        self.worker_thread = QThread()
        self.search_worker = SearchWorker(folder, keyword)
        self.search_worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.search_worker.start_search)
        self.search_worker.progress_update.connect(self.update_progress_bar)
        self.search_worker.search_finished.connect(self.on_search_finished)
        self.search_worker.error_occurred.connect(self.show_error_message)
        self.search_worker.file_matches_found.connect(
            lambda path, lines: self.on_file_matches_found(path, lines, keyword)
        )
        self.worker_thread.start()
    
    def cancel_search(self):
        if self.search_worker:
            self.search_worker.cancel_search()  # 讓 Worker 內部實作「停止」的邏輯
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread.deleteLater()
            self.search_worker.deleteLater()
            self.worker_thread = None
            self.search_worker = None

        self.progress_bar.setFormat("搜尋已取消")
        self.progress_bar.setValue(0)
        self.search_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    @pyqtSlot(int)
    def update_progress_bar(self, value):
        if self.search_worker and self.search_worker.total_files > 0:
            total = self.search_worker.total_files
            percent = int(value / total * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"正在搜尋... ({value}/{total})")
        else:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("找不到可搜尋的檔案！")
    
    @pyqtSlot(str)
    def on_search_finished(self, message):
        self.progress_bar.setFormat(message)
        self.search_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread.deleteLater()
        
        if self.search_worker:
            self.search_worker.deleteLater()
        
        self.worker_thread = None
        self.search_worker = None

    
    def on_file_matches_found(self, file_path, lines, keyword):
        for line in lines:
            card = ResultCard(file_path, line, keyword, parent=self.results_container)
            card.cardDoubleClicked.connect(self.open_file_viewer)
            self.results_layout.addWidget(card)
    
    @pyqtSlot(str, str)
    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)
    
    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "關於本工具",
            "這是結合 RWD 理念的最完美頂級UI文件搜尋工具示範。\n"
            "點擊搜尋結果卡片可進一步開啟文件內容檢視器，\n"
            "並自動高亮搜尋關鍵字。\n"
            "支援 TXT, PDF, DOCX, XLSX, HTML 文件全文搜尋。"
        )
    
    def open_file_viewer(self, file_path, search_keyword):
        html_file = convert_file_to_html(file_path)
        if not html_file:
            QMessageBox.warning(self, "轉換錯誤", f"無法轉換檔案: {file_path}")
            return
        viewer = HtmlViewer(html_file, search_keyword)
        viewer.show()
        self.open_viewers.append(viewer)