import os
import re
import sys
import chardet
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

class HtmlViewer(QWidget):
    def __init__(self, html_file: str, search_keyword: str = ""):
        super().__init__()
        self.search_keyword = search_keyword
        self.setWindowTitle("HTML Viewer - iOS 風格搜尋與懸浮效果")
        self.setGeometry(100, 100, 900, 700)
        layout = QVBoxLayout()
        self.web_view = QWebEngineView()
        
        if not os.path.isfile(html_file):
            QMessageBox.critical(self, "錯誤", f"文件未找到: {html_file}")
            sys.exit(1)
        
        modified_html = self.modify_html(html_file)
        base_url = QUrl.fromLocalFile(os.path.abspath(html_file))
        self.web_view.setHtml(modified_html, base_url)
        
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("🔍 在頁面中搜尋")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                border-radius: 15px;
                padding: 8px 15px;
                border: 1px solid #CCC;
                font-size: 16px;
                background-color: #F5F5F7;
            }
        """)
        self.search_bar.returnPressed.connect(self.search_text)
        self.search_btn = QPushButton("🔍 搜尋")
        self.search_btn.setStyleSheet(self.button_style())
        self.search_btn.clicked.connect(self.search_text)
        self.prev_btn = QPushButton("⬆️ 上一個")
        self.prev_btn.setStyleSheet(self.button_style())
        self.prev_btn.clicked.connect(lambda: self.search_text(backward=True))
        self.next_btn = QPushButton("⬇️ 下一個")
        self.next_btn.setStyleSheet(self.button_style())
        self.next_btn.clicked.connect(lambda: self.search_text(backward=False))
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.prev_btn)
        search_layout.addWidget(self.next_btn)
        
        layout.addLayout(search_layout)
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        
        self.web_view.loadFinished.connect(self.on_load_finished)
    
    def on_load_finished(self):
        if self.search_keyword:
            self.search_bar.setText(self.search_keyword)
            QTimer.singleShot(500, self.search_text)
    
    def search_text(self, backward=False):
        keyword = self.search_bar.text().strip()
        if not keyword:
            return
        options = QWebEnginePage.FindFlag(0)
        if backward:
            options |= QWebEnginePage.FindFlag.FindBackward
        self.web_view.page().findText(keyword, options)
    
    def modify_html(self, html_file):
        with open(html_file, "rb") as file:
            raw_data = file.read()
        m = re.search(rb'<meta[^>]*charset=["\']?([^>"\']+)', raw_data, re.IGNORECASE)
        if m:
            encoding = m.group(1).decode('ascii', errors='ignore').strip().lower()
        else:
            encoding = chardet.detect(raw_data)["encoding"]
        encoding = encoding or "utf-8"
        try:
            html_content = raw_data.decode(encoding, errors="ignore")
        except Exception:
            html_content = raw_data.decode("utf-8", errors="ignore")
        html_content = re.sub(r'(?i)<meta\s+[^>]*charset=["\']?[^>]+>', '', html_content)
        head_injection = '''<meta charset="utf-8">'''
        html_content = re.sub(r'(?i)(<head[^>]*>)', r'\1' + head_injection, html_content, count=1)
        html_content = self.replace_vml_with_img(html_content)
        return html_content
    
    def replace_vml_with_img(self, html_content):
        pattern = re.compile(
            r'<v:shape [^>]*style=[\'"]([^\'"]+)[\'"][^>]*>'
            r'\s*<v:imagedata src=[\'"]([^\'"]+)[\'"] o:title=[\'"]([^\'"]*)[\'"]\s*/>\s*</v:shape>',
            re.IGNORECASE
        )
        def vml_to_img(match):
            style = match.group(1)
            src = match.group(2)
            alt = match.group(3)
            width_match = re.search(r'width:\s*([\d.]+)px', style)
            height_match = re.search(r'height:\s*([\d.]+)px', style)
            width = f'width="{width_match.group(1)}px"' if width_match else ''
            height = f'height="{height_match.group(1)}px"' if height_match else ''
            return f'<img src="{src}" alt="{alt}" {width} {height}>'
        return pattern.sub(vml_to_img, html_content)
    
    def button_style(self):
        return '''
            QPushButton {
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 14px;
                background-color: #007AFF;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #005EB8;
            }
            QPushButton:pressed {
                background-color: #004499;
            }
        '''
