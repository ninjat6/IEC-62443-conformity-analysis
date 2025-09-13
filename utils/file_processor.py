# utils/file_processor.py

from docx import Document # type: ignore
from openpyxl import load_workbook # type: ignore
import json
import re
import subprocess
import tempfile
from pathlib import Path
import shutil # For copying files

class FileProcessor:
    """處理檔案並分割中英文內容的工具類"""

    @staticmethod
    def clean_line_chinese(line: str) -> str:
        """
        清理單行內容，保留：
          1. 中文（含數字）
          2. 全部字母皆大寫、且長度 >= 2 的英文單字（例如 TIRI、CPU、ABC）
          3. TIRI/IEC 編號（如 TIRI-E-1-0-001, IEC62443-2-4:2015）
          4. 符號 - : / 、（與中文、數字並存時可保留）
        """
        line = line.strip()
        if not line:
            return ""

        protected = {}

        # 1) 保護 TIRI 文件編號
        doc_nums = re.findall(r'TIRI-[A-Z]-\d-\d-\d{3}', line)
        for i, num in enumerate(doc_nums):
            key = f"{{DOC{i}}}"
            protected[key] = num
            line = line.replace(num, key)

        # 2) 保護 IEC 編號
        iec_pat = r'(IEC\s*\d+(?:-\d+)*(?::\d+)?(?:-\d+)?)'
        iec_nums = re.findall(iec_pat, line)
        for i, num in enumerate(iec_nums):
            key = f"{{IEC{i}}}"
            protected[key] = num.replace(' ', '')
            line = line.replace(num, key)

        # 3) 若冒號前無中文，則只保留冒號後（原需求）
        if re.search(r'[：:]', line):
            parts = re.split(r'[：:]', line, 1)
            if len(parts) == 2:
                if not re.search(r'[\u4e00-\u9fff]', parts[0]):
                    line = parts[1].strip()
                else:
                    line = parts[0].strip() + "：" + parts[1].strip()

        # 4) 用正則一次性擷取 token
        pattern = r'[\u4e00-\u9fff0-9\-\:\/、]+|[A-Z]{2,}|\{DOC\d+\}|\{IEC\d+\}'
        tokens = re.findall(pattern, line)
        if not tokens:
            return ""

        new_line = " ".join(tokens)

        # 5) 還原 placeholder
        for ph, val in protected.items():
            new_line = new_line.replace(ph, val)

        return new_line.strip()

    @staticmethod
    def clean_line_english(line: str) -> str:
        """
        清理單行內容，保留英文（含大小寫）、數字、及 TIRI/IEC 編號；移除中文。
        """
        line = line.strip()
        if not line:
            return ""

        # 若沒任何英文字母/數字/TIRI/IEC，就視為非英文
        if not re.search(r'[a-zA-Z0-9]|TIRI-|IEC', line):
            return ""

        protected = {}

        # 1) 保護 TIRI 文件編號
        doc_nums = re.findall(r'TIRI-[A-Z]-\d-\d-\d{3}', line)
        for i, num in enumerate(doc_nums):
            key = f"{{DOCENG{i}}}"
            protected[key] = num
            line = line.replace(num, key)

        # 2) 保護 IEC
        iec_nums = re.findall(r'IEC\s*\d+(?:-\d+)*(?:-\d+)?', line)
        for i, num in enumerate(iec_nums):
            key = f"{{IECENG{i}}}"
            protected[key] = num.replace(' ', '')
            line = line.replace(num, key)

        # 移除所有中文（含中文標點）
        line = re.sub(r'[\u4e00-\u9fff]', '', line)
        # 轉換常見中文標點
        line = line.replace('：', ':').replace('，', ',')
        line = line.replace('（', '(').replace('）', ')')

        # 合併多重空白
        line = re.sub(r'\s+', ' ', line).strip()

        # 還原 placeholder
        for placeholder, original_str in protected.items():
            line = line.replace(placeholder, original_str)

        if not re.search(r'[a-zA-Z0-9]|TIRI-|IEC', line):
            return ""

        return line

    @staticmethod
    def _split_text_advanced(text: str): # Made private as it's a helper
        """
        將整份文本逐行分割，分別產生「中文清單」與「英文清單」。
        """
        lines = text.split('\n')
        chinese_content = []
        english_content = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            c_line = FileProcessor.clean_line_chinese(line)
            if c_line:
                chinese_content.append(c_line)

            e_line = FileProcessor.clean_line_english(line)
            if e_line:
                english_content.append(e_line)

        # 去重且保序
        def deduplicate_preserve_order(items):
            seen = set()
            result = []
            for x in items:
                if x not in seen:
                    seen.add(x)
                    result.append(x)
            return result

        chinese_content = deduplicate_preserve_order(chinese_content)
        english_content = deduplicate_preserve_order(english_content)

        return chinese_content, english_content

    @staticmethod
    def _split_docx_to_json(input_path_obj: Path, output_chinese_path_obj: Path, output_english_path_obj: Path):
        """處理 Word 文件 (.docx) -> 生成中英文 JSON"""
        # Existence check done by caller (process_file)
        try:
            doc = Document(input_path_obj) # docx.Document accepts Path objects
            text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())

            chinese_content, english_content = FileProcessor._split_text_advanced(text)

            output_chinese_path_obj.parent.mkdir(parents=True, exist_ok=True)
            output_english_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(output_chinese_path_obj, 'w', encoding='utf-8') as ch_file:
                json.dump(chinese_content, ch_file, ensure_ascii=False, indent=4)

            with open(output_english_path_obj, 'w', encoding='utf-8') as en_file:
                json.dump(english_content, en_file, ensure_ascii=False, indent=4)

            return {
                "chinese_json": str(output_chinese_path_obj), # Return strings for external compatibility
                "english_json": str(output_english_path_obj)
            }
        except Exception as e:
            raise Exception(f"處理 DOCX 檔案 {str(input_path_obj)} 時發生錯誤：{str(e)}")

    @staticmethod
    def _split_xlsx_to_json(input_path_obj: Path, output_chinese_path_obj: Path, output_english_path_obj: Path):
        """處理 Excel 文件 -> 生成中英文 JSON"""
        # Existence check done by caller (process_file)
        try:
            workbook = load_workbook(input_path_obj) # load_workbook accepts Path objects
            sheet = workbook.active

            text_lines = []
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    line_str = " ".join(str(cell) for cell in row if cell is not None)
                    text_lines.append(line_str)

            text = "\n".join(text_lines)
            chinese_content, english_content = FileProcessor._split_text_advanced(text)

            output_chinese_path_obj.parent.mkdir(parents=True, exist_ok=True)
            output_english_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(output_chinese_path_obj, 'w', encoding='utf-8') as ch_file:
                json.dump(chinese_content, ch_file, ensure_ascii=False, indent=4)

            with open(output_english_path_obj, 'w', encoding='utf-8') as en_file:
                json.dump(english_content, en_file, ensure_ascii=False, indent=4)

            return {
                "chinese_json": str(output_chinese_path_obj), # Return strings
                "english_json": str(output_english_path_obj)
            }
        except Exception as e:
            raise Exception(f"處理 XLSX 檔案 {str(input_path_obj)} 時發生錯誤：{str(e)}")

    @staticmethod
    def _convert_doc_to_docx(input_path_obj: Path) -> Path:
        """
        若為 .doc 檔，透過 LibreOffice（或 unoconv）將其轉換為 .docx。
        回傳轉檔後的 .docx Path。若失敗則拋出例外。
        """
        input_stem = input_path_obj.stem
        # Create a temporary .docx file path in the same directory as the input .doc file for the copy
        # This is not ideal for a library function but matches original behavior.
        # A better approach might be to use a user's temp dir or app's cache dir.
        temp_docx_output_path = input_path_obj.with_name(f"{input_stem}.temp_converted.docx")

        try:
            with tempfile.TemporaryDirectory() as tmpdir_str:
                tmpdir_path = Path(tmpdir_str)
                # LibreOffice expects string paths
                subprocess.run([
                    "soffice", "--headless", "--convert-to", "docx", 
                    "--outdir", tmpdir_str, str(input_path_obj)
                ], check=True, capture_output=True, text=True) # Added capture_output and text for better error info
                
                # LibreOffice 轉檔後檔名與原檔相同但副檔名改為 docx
                converted_filename = f"{input_stem}.docx"
                converted_path_in_tmp = tmpdir_path / converted_filename
                
                if not converted_path_in_tmp.exists():
                    raise FileNotFoundError(f"LibreOffice 轉檔失敗，找不到: {str(converted_path_in_tmp)}")

                # Copy the converted file from tmpdir to temp_docx_output_path
                shutil.copy(converted_path_in_tmp, temp_docx_output_path)

            if not temp_docx_output_path.exists(): # Check if copy succeeded
                raise FileNotFoundError(f"找不到轉檔後的檔案: {str(temp_docx_output_path)}")

            return temp_docx_output_path

        except subprocess.CalledProcessError as e:
            error_message = f".doc 轉 .docx 失敗 for {str(input_path_obj)}: {str(e)}\n"
            if e.stdout:
                error_message += f"Stdout: {e.stdout}\n"
            if e.stderr:
                error_message += f"Stderr: {e.stderr}\n"
            raise Exception(error_message)
        except Exception as e: # Catch other errors like FileNotFoundError
            raise Exception(f"Error during .doc to .docx conversion for {str(input_path_obj)}: {str(e)}")


    @staticmethod
    def process_file(input_path_str: str, output_dir_str: str) -> dict:
        """
        處理檔案的主要方法：
        1. 檢查檔案存在
        2. 判斷副檔名
        3. 呼叫對應方法（doc/docx / xlsx），輸出中文與英文 JSON
        Returns a dictionary with paths to the generated JSON files (as strings).
        """
        input_path_obj = Path(input_path_str).resolve()
        output_dir_obj = Path(output_dir_str).resolve()

        if not input_path_obj.exists():
            raise FileNotFoundError(f"找不到輸入檔案：{str(input_path_obj)}")

        output_dir_obj.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

        file_stem = input_path_obj.stem
        output_chinese_path_obj = output_dir_obj / f"{file_stem}_chinese.json"
        output_english_path_obj = output_dir_obj / f"{file_stem}_english.json"

        # Suffix includes the dot, e.g., ".docx"
        ext = input_path_obj.suffix.lower()
        
        processed_input_path = input_path_obj # Path to be processed (might be converted .doc)
        temporary_docx_to_delete: Path | None = None

        if ext == '.doc':
            try:
                processed_input_path = FileProcessor._convert_doc_to_docx(input_path_obj)
                temporary_docx_to_delete = processed_input_path # Mark for deletion
                ext = '.docx' # Update ext for further processing
            except Exception as e:
                # If .doc to .docx conversion fails, re-raise to be caught by caller.
                raise Exception(f"Failed to convert .doc to .docx: {str(input_path_obj)} - Error: {e}")

        try:
            if ext == '.docx':
                return FileProcessor._split_docx_to_json(processed_input_path,
                                                         output_chinese_path_obj,
                                                         output_english_path_obj)
            elif ext == '.xlsx':
                return FileProcessor._split_xlsx_to_json(processed_input_path, # processed_input_path is original for xlsx
                                                         output_chinese_path_obj,
                                                         output_english_path_obj)
            else:
                raise ValueError(f"不支援的檔案格式 '{ext}'。僅支援 .doc, .docx 和 .xlsx 格式。")
        finally:
            if temporary_docx_to_delete and temporary_docx_to_delete.exists():
                try:
                    temporary_docx_to_delete.unlink()
                except Exception as e:
                    # Log error during temp file deletion, but don't let it hide original error
                    print(f"Warning: Failed to delete temporary .docx file {str(temporary_docx_to_delete)}: {e}")


if __name__ == "__main__":
    """
    若要從命令列執行:
    python file_processor.py <input_file_path> <output_dir>
    """
    import sys
    if len(sys.argv) < 3:
        print("Usage: python utils/file_processor.py <input_file_path> <output_dir>")
        sys.exit(1)

    # Use Path for command line arguments
    in_path_obj = Path(sys.argv[1])
    out_dir_obj = Path(sys.argv[2])

    try:
        # Pass strings to the public API as per its defined contract
        result = FileProcessor.process_file(str(in_path_obj), str(out_dir_obj))
        print("Process success:", result)
    except Exception as e:
        print("Error:", e, file=sys.stderr) # Print errors to stderr
        sys.exit(1)
