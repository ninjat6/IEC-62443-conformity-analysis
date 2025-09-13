# file_search_module/converters/__init__.py
from .file_converter import convert_file_to_html
from .docx_converter import convert_docx_to_html

__all__ = [
    "convert_file_to_html",
    "convert_docx_to_html"
]
