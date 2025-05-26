# IEC62443Tool.spec

import sys
from pathlib import Path

# Assuming path_utils.py is in the project root and can be imported
# This is for getting resource paths during spec file generation if needed,
# but primarily paths are relative to the spec file or app root.
# import path_utils

APP_NAME = "IEC62443Tool"
# SPECPATH is a variable injected by PyInstaller, representing the directory of the spec file.
# This is the most reliable way to get the project root if the spec file is at the root.
PROJECT_ROOT = Path(SPECPATH).resolve()

# --- Collect data files ---
# The 'datas' list should contain tuples of (source_path_on_disk, destination_in_bundle)
# Destination is relative to the bundle's root directory (sys._MEIPASS)

app_data_files = [
    # Icons for file_search_module
    (str(PROJECT_ROOT / 'file_search_module/ui/icons'), 'file_search_module/ui/icons'),

    # Templates
    (str(PROJECT_ROOT / 'conformity_analysis_module/template'), 'conformity_analysis_module/template'),
    # Consolidate if this is a duplicate or different:
    (str(PROJECT_ROOT / 'resources/templates'), 'resources/templates'),

    # Default JSON data
    (str(PROJECT_ROOT / 'conformity_analysis_module/data'), 'conformity_analysis_module/data'),
    (str(PROJECT_ROOT / 'conformity_analysis_module/requirements_cn.json'), 'conformity_analysis_module'),
    # Add other requirements_*.json files if they are dynamically loaded by name
    # e.g., (str(PROJECT_ROOT / 'conformity_analysis_module/requirements.json'), 'conformity_analysis_module'),

    # Assuming 'all_documents.json' is a bundled resource:
    (str(PROJECT_ROOT / 'resources/output_json/all_documents.json'), 'resources/output_json'),
    
    # Requirements.txt (for reference or potential future use, not for pip install by user)
    (str(PROJECT_ROOT / 'requirements.txt'), '.'),

    # If model.py or path_utils.py are not automatically picked up as main scripts/imports,
    # they might need to be included if they have data or are entry points for hooks.
    # Typically, PyInstaller handles .py files that are part of the import graph.
]

# --- PyInstaller Analysis ---
a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=app_data_files,
    hiddenimports=[
        'appdirs',
        'packaging',
        'packaging.requirements',
        'packaging.version',
        'packaging.specifiers',
        'PyQt6.sip',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'win32com', # For pywin32
        'win32com.client',
        # Add other hidden imports based on testing/warnings from PyInstaller
        # e.g., for sentence_transformers, torch, transformers if issues arise
        'sentence_transformers',
        'transformers',
        'torch',
        'sklearn.utils._weight_vector', # Common scikit-learn hidden import
    ],
    hookspath=[], # PyInstaller will find pyinstaller-hooks-contrib
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None, # No encryption
    noarchive=False
)

# --- PyInstaller Bundle ---
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [], # Merged
    name=f"{APP_NAME}-App", # Changed name of the executable
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # UPX compression, if available on system
    upx_exclude=[],
    runtime_tmpdir=None, # Default tmpdir behavior
    console=False, # True for console debugging, False for GUI app
    disable_windowed_traceback=False,
    target_arch=None, # Auto-detect architecture
    codesign_identity=None, # For macOS signing
    entitlements_file=None, # For macOS entitlements
    # icon='path/to/your/app.ico' # Add an application icon for Windows
)

coll = COLLECT( # For one-dir mode
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME
)

# For one-file mode, you would use:
# bundle = BUNDLE(coll, name=f'{APP_NAME}.app', ...) # For macOS .app
# For Windows one-file, the EXE itself is the primary output.
