# core/file_processor.py
import os
import docx
import openpyxl
import PyPDF2
from conformity_analysis_module.utils.logger import logger

class FileProcessor:
    @staticmethod
    def extract_text_from_docx(file_path):
        snippets = []
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    snippets.append(text)
        except Exception as e:
            logger.error(f"處理 DOCX 檔案 {file_path} 時發生錯誤: {e}")
        return snippets

    @staticmethod
    def extract_text_from_xlsx(file_path):
        snippets = []
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            for sheet in wb:
                for row in sheet.iter_rows(values_only=True):
                    row_text = " ".join(str(cell) for cell in row if cell is not None).strip()
                    if row_text:
                        snippets.append(row_text)
        except Exception as e:
            logger.error(f"處理 XLSX 檔案 {file_path} 時發生錯誤: {e}")
        return snippets

    @staticmethod
    def extract_text_from_pdf(file_path):
        snippets = []
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        for line in text.split('\n'):
                            line = line.strip()
                            if line:
                                snippets.append(line)
        except Exception as e:
            logger.error(f"處理 PDF 檔案 {file_path} 時發生錯誤: {e}")
        return snippets

    @staticmethod
    def extract_text_snippets(file_path):
        ext = file_path.lower().split('.')[-1]
        if ext == 'docx':
            return FileProcessor.extract_text_from_docx(file_path)
        elif ext == 'xlsx':
            return FileProcessor.extract_text_from_xlsx(file_path)
        elif ext == 'pdf':
            return FileProcessor.extract_text_from_pdf(file_path)
        else:
            return []