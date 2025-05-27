# IEC62443Tool.spec

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_NAME = "IEC62443Tool"
# SPECPATH is a variable injected by PyInstaller, representing the directory of the spec file.
PROJECT_ROOT = Path(SPECPATH).resolve() # CORRECTED LINE

# --- Collect data files ---
app_data_files = [
    (str(PROJECT_ROOT / 'file_search_module/ui/icons'), 'file_search_module/ui/icons'),
    (str(PROJECT_ROOT / 'conformity_analysis_module/template'), 'conformity_analysis_module/template'),
    (str(PROJECT_ROOT / 'resources/templates'), 'resources/templates'), # Consolidate if duplicate
    (str(PROJECT_ROOT / 'conformity_analysis_module/data'), 'conformity_analysis_module/data'),
    (str(PROJECT_ROOT / 'conformity_analysis_module/requirements_cn.json'), 'conformity_analysis_module'),
    (str(PROJECT_ROOT / 'resources/output_json/all_documents.json'), 'resources/output_json'), # If bundled
    (str(PROJECT_ROOT / 'requirements.txt'), '.'),
]

# Add data files for specific problematic libraries
app_data_files += collect_data_files('sentence_transformers')
app_data_files += collect_data_files('transformers')
app_data_files += collect_data_files('torch') 
app_data_files += collect_data_files('PyQt6', include_py_files=False)


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
        'PyQt6.QtNetwork', 
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtGui', 
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'win32com',
        'win32com.client',
        'sentence_transformers',
        'transformers',
        'torch',
        'scipy.special._cdflib', 
        'sklearn.utils._weight_vector',
        'rapidfuzz', 
    ] + collect_submodules('PyQt6.QtWebEngineCore') + collect_submodules('file_search_module.converters'), 
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [], 
    [], 
    [], 
    name=APP_NAME + "-App", 
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # Changed UPX to False
    upx_exclude=[],
    runtime_tmpdir=None, # Confirmed runtime_tmpdir=None
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Using a plausible icon path, ensure app_icon.ico exists or use a valid one
    icon=str(PROJECT_ROOT / 'file_search_module/ui/icons/app_icon.ico') 
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False, # Changed UPX to False
    upx_exclude=[],
    name=APP_NAME
)
