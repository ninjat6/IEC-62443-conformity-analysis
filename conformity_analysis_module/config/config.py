# conformity_analysis_module/config/config.py
from pathlib import Path
# Assuming path_utils.py is in the project root and accessible in PYTHONPATH
from path_utils import get_log_dir, get_bundled_resource_path, get_cache_dir, get_reports_dir

# The old resource_path function is removed.

class Config:
    # ROOT_DIR points to the root of the 'conformity_analysis_module'.
    # This might still be useful for module-specific relative paths not covered by path_utils.
    ROOT_DIR = Path(__file__).resolve().parent.parent 
    
    LOG_DIR = get_log_dir()
    
    # Bundled resources - paths are relative to project root or bundled_assets for get_bundled_resource_path
    REQUIREMENTS_FILE = get_bundled_resource_path("conformity_analysis_module/requirements_cn.json")
    WORKSHEET_FILE = get_bundled_resource_path("conformity_analysis_module/template/IEC62443_2_4d_2024-worksheet.xlsx")
    
    # Output/Cache directories
    ANALYSIS_OUTPUT = get_reports_dir() / "analysis_results.json"
    DOCX_CACHE_FILE = get_cache_dir() / "docx_contents.json"

    @staticmethod
    def ensure_dir(directory: Path):
        # This method is now less critical if path_utils functions ensure dirs,
        # but can be kept for other uses or as a safeguard.
        directory.mkdir(parents=True, exist_ok=True)