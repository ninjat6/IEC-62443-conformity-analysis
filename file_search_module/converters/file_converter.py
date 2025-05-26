import html
import chardet
import win32com.client
import pythoncom
import logging
from pathlib import Path # Added
from PyPDF2 import PdfReader
import openpyxl

# Configure logging (can be moved to a central logger utility if available)
# Using a format that includes filename and line number for better debugging.
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s")

def convert_file_to_html(file_path_str: str) -> Path | None:
    """
    Converts various file types to HTML format.
    Supported formats: DOCX, TXT, PDF, XLSX, HTML.
    Args:
        file_path_str: String representation of the absolute path to the file.
    Returns:
        A Path object to the converted HTML file, or the original Path object if already HTML.
        Returns None if the file doesn't exist or conversion fails.
    """
    file_path_obj = Path(file_path_str).resolve()

    if not file_path_obj.exists():
        logging.error(f"File not found: {str(file_path_obj)}")
        return None

    ext = file_path_obj.suffix.lower().lstrip('.')
    # Output HTML file will be in the same directory as the source file
    html_file_path = file_path_obj.with_name(f"{file_path_obj.stem}_converted.html")

    try:
        if ext in ["html", "htm"]:
            logging.info(f"File is already HTML: {str(file_path_obj)}")
            return file_path_obj  # Return original Path object
        elif ext == "docx":
            _convert_docx_to_html(file_path_obj, html_file_path)
        elif ext == "txt":
            _convert_txt_to_html(file_path_obj, html_file_path)
        elif ext == "pdf":
            _convert_pdf_to_html(file_path_obj, html_file_path)
        elif ext == "xlsx":
            _convert_xlsx_to_html(file_path_obj, html_file_path)
        else:
            logging.error(f"Unsupported file format for conversion: {str(file_path_obj)}")
            return None
        
        if html_file_path.exists():
            logging.info(f"Successfully converted {str(file_path_obj)} to {str(html_file_path)}")
            return html_file_path
        else:
            # This case should ideally be covered by exceptions in helper functions
            logging.error(f"Converted HTML file not found after attempting conversion: {str(html_file_path)}")
            return None
            
    except Exception as e:
        logging.error(f"Failed to convert file {str(file_path_obj)}: {e}", exc_info=True)
        return None

def _convert_docx_to_html(docx_path_obj: Path, html_path_obj: Path):
    """Converts DOCX to HTML using win32com."""
    pythoncom.CoInitialize()
    word = None
    doc = None
    created_new_instance = False

    # win32com expects absolute string paths
    docx_abs_str = str(docx_path_obj.resolve())
    html_abs_str = str(html_path_obj.resolve())

    try:
        try:
            word = win32com.client.GetActiveObject("Word.Application")
            logging.info(f"Attached to existing Word instance for {docx_abs_str}.")
        except:
            word = win32com.client.Dispatch("Word.Application")
            created_new_instance = True
            logging.info(f"Created new Word instance for {docx_abs_str}.")

        word.Visible = False
        doc = word.Documents.Open(docx_abs_str, ReadOnly=True)
        doc.SaveAs(html_abs_str, FileFormat=8)  # 8 = wdFormatHTML (Filtered HTML)
        logging.info(f"DOCX conversion successful: {html_abs_str}")

    except Exception as e:
        logging.error(f"Failed to convert DOCX {docx_abs_str} to HTML {html_abs_str}: {e}", exc_info=True)
        raise  # Re-raise to be caught by the main convert_file_to_html
    finally:
        if doc:
            doc.Close(False)
        if created_new_instance and word:
            word.Quit()
        # According to MSDN, CoUninitialize should be called for each successful call to CoInitialize.
        # However, in scripts, it's often omitted or managed by the Python COM library wrapper upon exit.
        # If issues arise with Word instances not closing, explicit CoUninitialize might be needed.
        # pythoncom.CoUninitialize() 

def _convert_txt_to_html(txt_path_obj: Path, html_path_obj: Path):
    """Converts TXT to HTML, detecting encoding."""
    try:
        with open(txt_path_obj, "rb") as f:
            raw_data = f.read()
        
        detected = chardet.detect(raw_data)
        encoding = detected.get("encoding", "utf-8") if detected and detected['confidence'] and detected['confidence'] > 0.5 else "utf-8"
        if encoding is None: encoding = "utf-8" # Fallback if chardet returns None for encoding
        logging.info(f"Detected encoding for {str(txt_path_obj)}: {encoding} (Confidence: {detected.get('confidence') if detected else 'N/A'})")
        
        text = raw_data.decode(encoding, errors="replace") # Use 'replace' for robustness
        
        html_content = f"<html><head><meta charset='utf-8'></head><body><pre>{html.escape(text)}</pre></body></html>"
        with open(html_path_obj, "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"TXT conversion successful: {str(html_path_obj)}")
    except Exception as e:
        logging.error(f"Failed to convert TXT {str(txt_path_obj)} to HTML: {e}", exc_info=True)
        raise

def _convert_pdf_to_html(pdf_path_obj: Path, html_path_obj: Path):
    """Converts PDF to HTML using PyPDF2 (text extraction wrapped in <pre>)."""
    try:
        reader = PdfReader(pdf_path_obj) # PdfReader accepts Path objects
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages if page.extract_text())
        
        html_content = f"<html><head><meta charset='utf-8'></head><body><pre>{html.escape(all_text)}</pre></body></html>"
        with open(html_path_obj, "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"PDF conversion successful: {str(html_path_obj)}")
    except Exception as e:
        logging.error(f"Failed to convert PDF {str(pdf_path_obj)} to HTML: {e}", exc_info=True)
        raise

def _convert_xlsx_to_html(xlsx_path_obj: Path, html_path_obj: Path):
    """Converts XLSX to HTML, rendering each sheet as a table."""
    try:
        wb = openpyxl.load_workbook(xlsx_path_obj, read_only=True, data_only=True) # openpyxl accepts Path
        html_parts = []

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            html_parts.append(f"<h2>Sheet: {html.escape(sheet.title)}</h2>")
            table_content = ["<table>"]
            for row in sheet.iter_rows(values_only=True):
                table_content.append("<tr>")
                for cell_value in row:
                    cell_str = str(cell_value) if cell_value is not None else ""
                    table_content.append(f"<td>{html.escape(cell_str)}</td>")
                table_content.append("</tr>")
            table_content.append("</table>")
            html_parts.append("".join(table_content))

        html_body = "".join(html_parts)
        html_content = f"<html><head><meta charset='utf-8'><style>table, th, td {{border: 1px solid black; border-collapse: collapse; padding: 5px;}}</style></head><body>{html_body}</body></html>"
        with open(html_path_obj, "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"XLSX conversion successful: {str(html_path_obj)}")
    except Exception as e:
        logging.error(f"Failed to convert XLSX {str(xlsx_path_obj)} to HTML: {e}", exc_info=True)
        raise
