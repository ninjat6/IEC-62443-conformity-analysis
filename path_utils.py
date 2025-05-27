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
    """
    Gets the user-specific data directory for the application using `appdirs`.
    This directory is OS-appropriate (e.g., ~/.local/share/IEC62443Tool on Linux,
    C:\\Users\\<User>\\AppData\\Local\\CyberAI\\IEC62443Tool on Windows).
    It serves as the root for storing persistent application data like models, cache, logs (though logs might use user_log_dir).
    """
    path = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    _ensure_dir_exists(path)
    return path

def get_models_base_dir() -> Path:
    """
    Gets the base directory where sentence-transformer models are stored locally.
    This directory is a subdirectory named "models" within the application's
    user-specific data directory (obtained via `get_app_data_dir()`).
    For example, on Linux: ~/.local/share/IEC62443Tool/models/
    This function ensures the "models" directory exists.
    """
    path = get_app_data_dir() / "models"
    _ensure_dir_exists(path)
    return path

def get_specific_model_dir(model_name: str) -> Path:
    """
    Gets the directory path for a specific sentence-transformer model.
    The path is constructed by appending the `model_name` as a subdirectory
    to the `get_models_base_dir()`.
    For example, if `model_name` is "all-MiniLM-L12-v2", this function might return:
    ~/.local/share/IEC62443Tool/models/all-MiniLM-L12-v2/
    This function ensures the specific model's directory exists.

    Args:
        model_name (str): The short name of the model (e.g., "all-MiniLM-L12-v2").

    Returns:
        Path: The absolute path to the specific model's directory.
    """
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
    This function is crucial for accessing files that are packaged *with* the application
    by PyInstaller (e.g., UI icons, templates, default configuration files).

    When the application is "frozen" (i.e., bundled by PyInstaller into an executable),
    these resources are typically extracted to a temporary directory referenced by `sys._MEIPASS`.
    This function correctly resolves paths for both frozen (bundled) and normal (development) execution modes.

    It's important to distinguish these bundled resources from user-generated data or
    externally downloaded files (like sentence-transformer models), which are stored in
    user-specific directories (e.g., obtained via `get_app_data_dir()` or `get_cache_dir()`).

    Args:
        relative_path (str): The path of the resource relative to what PyInstaller
                             considers the root of the bundled data. For example, if
                             PyInstaller is configured to include an 'assets/icons' folder,
                             you might pass 'assets/icons/my_icon.png'.

    Returns:
        Path: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # We are running in a bundle (frozen by PyInstaller).
        # `sys._MEIPASS` points to the temporary directory where bundled files are extracted.
        base_path = Path(sys._MEIPASS)
    else:
        # We are running in a normal Python environment (development mode).
        # For development, resources are assumed to be in a 'bundled_assets' directory
        # at the project root. This path is relative to this `path_utils.py` file.
        # Adjust this if your development resource structure is different.
        base_path = Path(__file__).resolve().parent / "bundled_assets"
    
    resource_path = (base_path / relative_path).resolve()

    # Fallback for development if 'bundled_assets' structure is not used or path is incorrect.
    # Tries to resolve relative to the project root directly.
    # This can be helpful during development before all resources are finalized in the
    # 'bundled_assets' structure or if paths in PyInstaller spec vs. dev differ.
    if not resource_path.exists() and not getattr(sys, 'frozen', False):
        # Assumes path_utils.py is in the project root for this fallback.
        # If path_utils.py is nested, (Path(__file__).resolve().parent.parent) might be needed.
        alt_base_path = Path(__file__).resolve().parent 
        resource_path = (alt_base_path / relative_path).resolve()
        # For the final bundled application, it's critical that the PyInstaller .spec file
        # correctly lists data files and their destinations in the bundle, matching
        # the `relative_path` used here.

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
