import sys
from pathlib import Path
import appdirs # Add this to requirements.txt if not already there
from datetime import datetime

APP_NAME = "IEC62443Tool"
APP_AUTHOR = "CyberAI"

def _ensure_dir_exists(dir_path: Path) -> None:
    """Ensures the given directory exists."""
    dir_path.mkdir(parents=True, exist_ok=True)

def get_app_data_dir() -> Path:
    """Gets the user-specific data directory for the application."""
    path = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    _ensure_dir_exists(path)
    return path

def get_models_base_dir() -> Path:
    """Gets the base directory where models are stored."""
    path = get_app_data_dir() / "models"
    _ensure_dir_exists(path)
    return path

def get_specific_model_dir(model_name: str) -> Path:
    """Gets the directory for a specific model. e.g., models/all-MiniLM-L12-v2/."""
    path = get_models_base_dir() / model_name
    _ensure_dir_exists(path)
    return path

def get_log_dir() -> Path:
    """Gets the user-specific log directory for the application."""
    path = Path(appdirs.user_log_dir(APP_NAME, APP_AUTHOR))
    _ensure_dir_exists(path)
    return path

def get_log_file_path() -> Path:
    """Gets the path for a new, timestamped log file."""
    log_dir = get_log_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return log_dir / f"{timestamp}.log" # Changed from YYYY-MM-DD.log to include time, avoiding overwrites for same-day runs

def get_reports_dir() -> Path:
    """Gets the default directory for user-generated reports/outputs."""
    path = Path.home() / "Documents" / "IEC62443-Reports"
    _ensure_dir_exists(path)
    return path

def get_cache_dir() -> Path:
    """Gets the user-specific cache directory for the application."""
    path = Path(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR))
    _ensure_dir_exists(path)
    return path

def get_bundled_resource_path(relative_path: str) -> Path:
    """
    Gets the absolute path to a bundled resource.
    'relative_path' should be the path of the resource relative
    to the bundle's root (e.g., 'assets/icons/my_icon.png').
    """
    if getattr(sys, 'frozen', False):
        # We are running in a bundle
        base_path = Path(sys._MEIPASS)
    else:
        # We are running in a normal Python environment
        # Assume resources are in a 'bundled_assets' directory at the project root for development
        base_path = Path(__file__).resolve().parent / "bundled_assets"
    
    resource_path = (base_path / relative_path).resolve()
    if not resource_path.exists() and not getattr(sys, 'frozen', False) :
        # Fallback for development if bundled_assets doesn't exist, try relative to project root directly
        # This might be useful if resources are not yet copied to a simulated bundle structure
        alt_base_path = Path(__file__).resolve().parent 
        resource_path = (alt_base_path / relative_path).resolve()
        # It's important that for actual bundled app testing, resources are correctly placed by PyInstaller

    return resource_path

# Example of how to potentially structure for development vs. frozen:
# If in development, you might have your assets in './assets' relative to project root.
# PyInstaller would be configured to put 'assets' folder into the root of the bundle.
# So, get_bundled_resource_path("assets/my_icon.png") would work if
# - In dev: project_root/assets/my_icon.png exists (adjust base_path logic for dev)
# - In frozen: _MEIPASS/assets/my_icon.png exists

# For development, the above `get_bundled_resource_path` assumes that
# if not frozen, resources are located relative to the `path_utils.py` file's parent (project root)
# in a subdirectory named `bundled_assets`.
# If your actual development resource structure is different (e.g. just `project_root/assets`),
# adjust the `else` block's `base_path` for `get_bundled_resource_path` accordingly.
# For instance, if `path_utils.py` is at the root, and assets are in `project_root/assets`:
# base_path = Path(__file__).resolve().parent  # This will be project_root
# then call get_bundled_resource_path("assets/icons/my_icon.png")

if __name__ == '__main__':
    print(f"User Data Dir (App Data): {get_app_data_dir()}")
    print(f"Models Base Dir: {get_models_base_dir()}")
    print(f"Specific Model Dir (Example): {get_specific_model_dir('example_model')}")
    print(f"Log Dir: {get_log_dir()}")
    print(f"Current Log File Path: {get_log_file_path()}")
    print(f"Reports (Outputs) Dir: {get_reports_dir()}")
    print(f"Cache Dir: {get_cache_dir()}")
    # To test get_bundled_resource_path, you'd need a file like './bundled_assets/test.txt'
    # or adjust the path based on your project structure.
    # print(f"Test Bundled Resource (dev): {get_bundled_resource_path('test_file.txt')}")
