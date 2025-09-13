# gui/__init__.py
# This file can be empty or export names from this package.

from .main_window import ConformityAnalysisWindow
from .progress_dialog import ModelDownloadProgressDialog # Add this line

__all__ = ['ConformityAnalysisWindow', 'ModelDownloadProgressDialog']