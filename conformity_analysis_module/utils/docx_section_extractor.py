# utils/docx_section_extractor.py
import re
import os
import json
import chardet
import pythoncom
import win32com.client as win32
from .logger import logger
from conformity_analysis_module.config import Config

class DocxSectionExtractor:
    def __init__(self, docx_path):
        self.docx_path = os.path.abspath(docx_path)
        self.cache_file = Config.DOCX_CACHE_FILE
        self.txt_content = self.load_docx_content()

    def load_docx_content(self):
        cache = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}
        if self.docx_path in cache:
            return cache[self.docx_path]
        else:
            temp_txt = os.path.join(Config.ROOT_DIR, "temp_output.txt")
            self.docx_to_txt(self.docx_path, temp_txt)
            encoding = self.detect_encoding(temp_txt)
            with open(temp_txt, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            cache[self.docx_path] = content
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=4)
            if os.path.exists(temp_txt):
                os.remove(temp_txt)
            return content

    def detect_encoding(self, file_path):
        with open(file_path, 'rb') as f:
            raw_data = f.read(1024)
        result = chardet.detect(raw_data)
        return result.get("encoding", "utf-8")

    def docx_to_txt(self, docx_path, txt_path):
        pythoncom.CoInitialize()  # 確保 COM 物件初始化

        word = None
        doc = None
        created_new_instance = False  # 紀錄是否新建了 Word 進程

        try:
            try:
                # 嘗試取得已開啟的 Word 應用程式
                word = win32.GetActiveObject("Word.Application")
            except:
                # 若沒有開啟的 Word，則新建一個 Word 進程
                word = win32.Dispatch("Word.Application")
                created_new_instance = True
            
            word.Visible = False  # 讓 Word 可見（避免背景執行影響用戶）

            # 開啟 DOCX 文件
            doc = word.Documents.Open(os.path.abspath(docx_path), ReadOnly=True)
            
            # 另存新檔為 TXT（FileFormat=2 代表純文字格式）
            doc.SaveAs(os.path.abspath(txt_path), FileFormat=2)
            
        except Exception as e:
            logger.error(f"轉換 Word 檔案失敗: {e}")
        
        finally:
            if doc:
                doc.Close(SaveChanges=False)  # 只關閉該文件，不儲存變更
            if created_new_instance:  
                word.Quit()  # 只在新建 Word 進程時關閉 Word

    def get_section_number(self, target_text):
        section_stack = []
        numeric_list_stack = []
        alpha_list_stack = []

        section_pattern = re.compile(r'^(?P<num>\d+(?:\.\d+)*\.?)\s+')
        list_pattern1 = re.compile(r'^\s*\((?P<num>\d+)\)\s+')
        list_pattern2 = re.compile(r'^\s*(?P<num>[A-Z])\.\s+')

        lines = self.txt_content.splitlines()
        final_section = ""

        for line in lines:
            section_match = section_pattern.match(line)
            if section_match:
                num_str = section_match.group('num').rstrip('.')
                level = num_str.count('.') + 1
                while len(section_stack) > level:
                    section_stack.pop()
                section_stack.append(num_str)
                numeric_list_stack.clear()
                alpha_list_stack.clear()

            num_list_match = list_pattern1.match(line)
            if num_list_match:
                list_num = num_list_match.group('num')
                numeric_list_stack.append(f"({list_num})")
                alpha_list_stack.clear()

            alpha_list_match = list_pattern2.match(line)
            if alpha_list_match:
                list_letter = alpha_list_match.group('num')
                alpha_list_stack.append(f"{list_letter}.")

            if target_text in line:
                numeric_item = numeric_list_stack.pop(-1) if numeric_list_stack else ""
                alpha_item = alpha_list_stack.pop(-1) if alpha_list_stack else ""
                hierarchical = section_stack.pop() if section_stack else ""
                final_section = hierarchical + " " + numeric_item + " " + alpha_item + " "
                break

        return final_section