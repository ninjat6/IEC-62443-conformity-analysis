import os
import html
import chardet
import win32com.client
import pythoncom
import logging
from PyPDF2 import PdfReader
import openpyxl

# 設定 logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def convert_file_to_html(file_path):
    """
    根據文件類型，將文件轉換為 HTML 格式
    支援格式: DOCX, TXT, PDF, XLSX, HTML
    """
    if not os.path.exists(file_path):
        logging.error(f"錯誤: 無法找到文件 {file_path}")
        return None

    ext = file_path.lower().rsplit('.', 1)[-1]
    base = os.path.splitext(file_path)[0]
    html_file = os.path.abspath(base + "_converted.html")

    try:
        if ext in ["html", "htm"]:
            return file_path  # 如果本來就是 HTML，直接返回
        elif ext == "docx":
            convert_docx_to_html(file_path, html_file)
        elif ext == "txt":
            convert_txt_to_html(file_path, html_file)
        elif ext == "pdf":
            convert_pdf_to_html(file_path, html_file)
        elif ext == "xlsx":
            convert_xlsx_to_html(file_path, html_file)
        else:
            logging.error(f"不支援的文件格式: {file_path}")
            return None
        return html_file
    except Exception as e:
        logging.error(f"轉換文件失敗: {file_path}, 錯誤: {e}")
        return None

def convert_docx_to_html(docx_path, html_path):
    """
    將 DOCX 轉換為 HTML
    """
    pythoncom.CoInitialize()
    word = None
    doc = None
    created_new_instance = False  # 紀錄是否新建了 Word 進程

    try:
        docx_path = os.path.abspath(docx_path)
        html_path = os.path.abspath(html_path)

        try:
            word = win32com.client.GetActiveObject("Word.Application")  # 取得現有的 Word 進程
        except:
            word = win32com.client.Dispatch("Word.Application")  # 開啟新的 Word 進程
            created_new_instance = True

        word.Visible = False  # 不顯示 Word 介面
        doc = word.Documents.Open(docx_path, ReadOnly=True)  # 以唯讀模式開啟
        doc.SaveAs(html_path, FileFormat=8)  # 8 = wdFormatHTML
        doc.Close(False)  # 只關閉該文件，不關閉 Word
        logging.info(f"DOCX 轉換完成: {html_path}")

    except Exception as e:
        logging.error(f"轉換 DOCX 失敗: {e}")

    finally:
        if created_new_instance:  
            word.Quit()  # 只在新建 Word 進程時關閉 Word

def convert_txt_to_html(txt_path, html_path):
    """
    將 TXT 轉換為 HTML
    """
    try:
        with open(txt_path, "rb") as f:
            raw_data = f.read()
        encoding = chardet.detect(raw_data).get("encoding", "utf-8")
        text = raw_data.decode(encoding, errors="ignore")
        
        html_content = f"<html><head><meta charset='utf-8'></head><body><pre>{html.escape(text)}</pre></body></html>"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logging.info(f"TXT 轉換完成: {html_path}")

    except Exception as e:
        logging.error(f"轉換 TXT 失敗: {e}")

def convert_pdf_to_html(pdf_path, html_path):
    """
    將 PDF 轉換為 HTML
    """
    try:
        reader = PdfReader(pdf_path)
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        
        html_content = f"<html><head><meta charset='utf-8'></head><body><pre>{html.escape(all_text)}</pre></body></html>"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logging.info(f"PDF 轉換完成: {html_path}")

    except Exception as e:
        logging.error(f"轉換 PDF 失敗: {e}")

def convert_xlsx_to_html(xlsx_path, html_path):
    """
    將 XLSX 轉換為 HTML
    """
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        all_text = []

        for sheet in wb:
            all_text.append(f"<h2>Sheet: {sheet.title}</h2>")
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(str(cell) for cell in row if cell is not None)
                all_text.append(f"<p>{html.escape(row_text)}</p>")

        html_content = f"<html><head><meta charset='utf-8'></head><body>{''.join(all_text)}</body></html>"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logging.info(f"XLSX 轉換完成: {html_path}")

    except Exception as e:
        logging.error(f"轉換 XLSX 失敗: {e}")
