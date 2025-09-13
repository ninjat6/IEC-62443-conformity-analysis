# file_search_module/converters/docx_converter.py
import pythoncom # type: ignore
import win32com.client # type: ignore
import logging
from pathlib import Path

logger = logging.getLogger(__name__) # Use a module-specific logger

def convert_docx_to_html(docx_path_obj: Path, html_path_obj: Path):
    """Converts DOCX to HTML using win32com."""
    # Ensure CoInitialize is called for the current thread
    try:
        pythoncom.CoInitialize()
        co_initialized = True
    except pythoncom.com_error: # pywintypes.com_error
        # Already initialized in this thread (RPC_E_CHANGED_MODE)
        co_initialized = False
        logger.debug("COM already initialized in this thread.")


    word = None
    doc = None
    created_new_instance = False

    docx_abs_str = str(docx_path_obj.resolve())
    html_abs_str = str(html_path_obj.resolve())

    try:
        try:
            word = win32com.client.GetActiveObject("Word.Application")
            logger.info(f"Attached to existing Word instance for {docx_abs_str}.")
        except Exception: # Broad exception as pywintypes.com_error might not be directly importable easily
            word = win32com.client.Dispatch("Word.Application")
            created_new_instance = True
            logger.info(f"Created new Word instance for {docx_abs_str}.")

        word.Visible = False
        doc = word.Documents.Open(docx_abs_str, ReadOnly=True)
        doc.SaveAs(html_abs_str, FileFormat=8)  # 8 = wdFormatHTML (Filtered HTML)
        logger.info(f"DOCX conversion successful: {html_abs_str}")

    except Exception as e:
        logger.error(f"Failed to convert DOCX {docx_abs_str} to HTML {html_abs_str}: {e}", exc_info=True)
        raise
    finally:
        if doc:
            doc.Close(False)
        if created_new_instance and word:
            word.Quit()
        # Only uninitialize if CoInitialize was called successfully in this function scope by this function
        # This is tricky because other parts of app might use COM.
        # A more robust solution might involve a COM context manager if heavy COM use.
        # For now, let's uninitialize if we initialized.
        if co_initialized:
            pythoncom.CoUninitialize()
