# utils/docx_section_extractor.py
import re
import json
import chardet
import pythoncom
import win32com.client as win32
from pathlib import Path
from conformity_analysis_module.utils.logger import logger # Corrected logger import
# Assuming path_utils.py is in the project root and accessible in PYTHONPATH
from path_utils import get_cache_dir

class DocxSectionExtractor:
    def __init__(self, docx_path_str: str): # Expect a string path
        # Convert input string path to an absolute Path object
        self.docx_path_obj = Path(docx_path_str).resolve()
        self.docx_path_str = str(self.docx_path_obj) # Store string version for cache key if needed
        
        self.cache_dir = get_cache_dir() # Get cache directory via path_utils
        self.cache_file = self.cache_dir / "docx_contents.json" # Define cache file path
        
        # Ensure cache directory exists (though get_cache_dir should handle its own root)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.txt_content = self._load_docx_content()

    def _load_docx_content(self):
        cache = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Cache file {self.cache_file} is corrupted. Creating new cache.")
                cache = {}
        
        # Use the string representation of the resolved path as the cache key
        if self.docx_path_str in cache:
            logger.info(f"Loading DOCX content from cache for: {self.docx_path_str}")
            return cache[self.docx_path_str]
        else:
            logger.info(f"Cache miss for: {self.docx_path_str}. Converting DOCX to text.")
            # Temporary text file will also be in the cache directory
            temp_txt_path = self.cache_dir / f"temp_{self.docx_path_obj.name}.txt"
            
            self._docx_to_txt(str(self.docx_path_obj), str(temp_txt_path)) # Pass string paths to COM interop
            
            content = ""
            if temp_txt_path.exists():
                encoding = self._detect_encoding(str(temp_txt_path)) # Pass string path
                try:
                    with open(temp_txt_path, 'r', encoding=encoding, errors='replace') as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Error reading temporary text file {temp_txt_path}: {e}")
                
                # Update cache
                cache[self.docx_path_str] = content
                try:
                    with open(self.cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, ensure_ascii=False, indent=4)
                    logger.info(f"Saved new content for {self.docx_path_str} to cache.")
                except Exception as e:
                    logger.error(f"Error writing to cache file {self.cache_file}: {e}")

                # Clean up temporary file
                try:
                    temp_txt_path.unlink(missing_ok=True) # Use missing_ok=True for robustness
                    logger.info(f"Removed temporary file: {temp_txt_path}")
                except Exception as e:
                    logger.error(f"Error removing temporary file {temp_txt_path}: {e}")
            else:
                logger.warning(f"Temporary text file {temp_txt_path} was not created during DOCX conversion.")
            return content

    def _detect_encoding(self, file_path_str: str) -> str: # Expects string path
        try:
            with open(file_path_str, 'rb') as f:
                raw_data = f.read(1024) # Read first 1KB for detection
            result = chardet.detect(raw_data)
            encoding = result.get("encoding", "utf-8") if result else "utf-8"
            logger.info(f"Detected encoding for {file_path_str}: {encoding} (confidence: {result.get('confidence') if result else 'N/A'})")
            return encoding
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path_str}: {e}. Defaulting to utf-8.")
            return "utf-8"

    def _docx_to_txt(self, docx_path_str: str, txt_path_str: str): # Expects string paths
        pythoncom.CoInitialize()
        word = None
        doc = None
        created_new_instance = False

        try:
            try:
                word = win32.GetActiveObject("Word.Application")
                logger.info("Attached to existing Word instance.")
            except:
                word = win32.Dispatch("Word.Application")
                created_new_instance = True
                logger.info("Created new Word instance.")
            
            word.Visible = False

            # win32com expects absolute string paths
            abs_docx_path = str(Path(docx_path_str).resolve())
            abs_txt_path = str(Path(txt_path_str).resolve())

            logger.info(f"Opening DOCX: {abs_docx_path}")
            doc = word.Documents.Open(abs_docx_path, ReadOnly=True)
            
            logger.info(f"Saving as TXT: {abs_txt_path}")
            doc.SaveAs(abs_txt_path, FileFormat=2) # FileFormat=2 is plain text
            
        except Exception as e:
            logger.error(f"Error converting Word file {docx_path_str} to {txt_path_str}: {e}")
        finally:
            if doc:
                doc.Close(SaveChanges=False)
                logger.info(f"Closed DOCX document: {docx_path_str}")
            if created_new_instance and word: # Ensure word object exists
                word.Quit()
                logger.info("Quit newly created Word instance.")
            # pythoncom.CoUninitialize() # Generally not needed if CoInitialize is per-thread / per-call

    def extract_sections(self, target_text: str) -> str: # Renamed from get_section_number for clarity
        # This method's logic for parsing text content remains unchanged.
        # It operates on self.txt_content which is already loaded.
        section_stack = []
        numeric_list_stack = []
        alpha_list_stack = []

        section_pattern = re.compile(r'^(?P<num>\d+(?:\.\d+)*\.?)\s+')
        list_pattern1 = re.compile(r'^\s*\((?P<num>\d+)\)\s+') # e.g., (1)
        list_pattern2 = re.compile(r'^\s*(?P<num>[a-zA-Z])\.\s+') # e.g., A. or a. (now case-insensitive)

        lines = self.txt_content.splitlines() if self.txt_content else []
        final_section_parts = [] # Store parts of the section string

        for line_number, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for section headers (e.g., 1.2.3)
            section_match = section_pattern.match(line_stripped)
            if section_match:
                num_str = section_match.group('num').rstrip('.')
                current_level = num_str.count('.') 
                
                # Adjust stack based on current section level
                while len(section_stack) > current_level:
                    section_stack.pop()
                
                if len(section_stack) == current_level: # Sibling or new sub-level
                    section_stack.append(num_str)
                elif len(section_stack) < current_level : # Skipped a level, append intermediate? Or just current
                    # This case might need more sophisticated handling if levels can be skipped.
                    # For now, assume continuous levels or direct sub-levels.
                     section_stack.append(num_str) # Add current if stack is shorter
                else: # Should not happen if logic above is correct
                    section_stack = [num_str] # Reset stack if level is 0 or unexpected

                numeric_list_stack.clear() # Reset list numbering
                alpha_list_stack.clear()
                logger.debug(f"Line {line_number+1}: Section match: {num_str}, Stack: {section_stack}")

            # Check for numeric list items (e.g., (1))
            num_list_match = list_pattern1.match(line_stripped)
            if num_list_match:
                list_num_str = f"({num_list_match.group('num')})"
                numeric_list_stack = [list_num_str] # Assuming simple, non-nested numeric lists for now
                alpha_list_stack.clear() # Reset alpha list
                logger.debug(f"Line {line_number+1}: Numeric list match: {list_num_str}, Stack: {numeric_list_stack}")
            
            # Check for alphabetical list items (e.g., A.)
            alpha_list_match = list_pattern2.match(line_stripped)
            if alpha_list_match:
                list_alpha_str = f"{alpha_list_match.group('num')}."
                # If there's an active numeric list, this is a sub-item
                if numeric_list_stack:
                     alpha_list_stack = [list_alpha_str] # Simple, non-nested alpha for now
                else: # If no numeric list, maybe it's a primary alpha list (treat similar to numeric)
                    numeric_list_stack = [list_alpha_str] # Store in numeric_list_stack for simplicity here
                    alpha_list_stack.clear()
                logger.debug(f"Line {line_number+1}: Alpha list match: {list_alpha_str}, Stack: {alpha_list_stack if numeric_list_stack else numeric_list_stack}")

            if target_text in line:
                logger.info(f"Target text '{target_text}' found in line: '{line_stripped}'")
                if section_stack:
                    final_section_parts.append(section_stack[-1]) # Last main section
                if numeric_list_stack:
                    final_section_parts.append(numeric_list_stack[-1]) # Current numeric/alpha item
                if alpha_list_stack and numeric_list_stack: # Only if alpha is sub-item of numeric
                    final_section_parts.append(alpha_list_stack[-1]) # Current alpha sub-item
                
                logger.debug(f"Final section parts for target: {final_section_parts}")
                break # Found target, construct section string

        return " ".join(filter(None, final_section_parts)).strip()