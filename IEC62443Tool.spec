# IEC62443Tool.spec

import sys
sys.setrecursionlimit(5000) # Standard PyInstaller recursion limit increase

# Project root directory 
# Assumes this .spec file is in the project root, and main.py is also in the project root.
# Modules like conformity_analysis_module, utils, etc., should be subdirectories here.
project_root = '.' # Defines the root directory of the project.

a = Analysis(
    ['main.py'], # Entry point of the application.
    # `pathex`: A list of paths where PyInstaller will look for imported modules, similar to PYTHONPATH.
    # Here, it's set to the project_root, allowing PyInstaller to find modules within the project.
    pathex=[project_root],
    binaries=[], # List of non-Python libraries (e.g., .dll, .so) to include.
    # `datas`: A list of tuples specifying non-binary files to be included in the bundle.
    # Each tuple is (source_path, destination_in_bundle).
    # - `source_path`: Path to the file or directory on the build system.
    # - `destination_in_bundle`: Path to the directory where these files will be placed
    #                            within the bundled application (relative to the bundle's root).
    # Example: ('path/to/icon.png', 'assets') will copy icon.png into an 'assets' folder in the bundle.
    # The paths here are relative to the `project_root`.
    datas=[
        # Bundling requirements JSON for the conformity analysis module.
        ('conformity_analysis_module/requirements_cn.json', 'conformity_analysis_module'),
        # Bundling the Excel template.
        ('conformity_analysis_module/template/IEC62443_2_4d_2024-worksheet.xlsx', 'conformity_analysis_module/template'),
        # Bundling keywords data.
        ('conformity_analysis_module/data/keywords.json', 'conformity_analysis_module/data'),
        # Bundling UI icons for the file search module.
        ('file_search_module/ui/icons/docx_icon.png', 'file_search_module/ui/icons'),
        ('file_search_module/ui/icons/pdf_icon.png', 'file_search_module/ui/icons'),
        ('file_search_module/ui/icons/txt_icon.png', 'file_search_module/ui/icons'),
        ('file_search_module/ui/icons/xlsx_icon.png', 'file_search_module/ui/icons')
    ],
    # `hiddenimports`: A list of modules that PyInstaller's static analysis might not detect,
    # but are necessary for the application to run. This is common for plugins, dynamically
    # imported modules, or modules imported via `__import__` or `importlib`.
    # Including these explicitly ensures they are part of the bundle.
    hiddenimports=[
        'PyQt6.sip',      # PyQt6 specific, often needed for core functionality.
        'PyQt6.QtSvg',    # For SVG image support in PyQt.
        'PyQt6.QtGui',    # Core GUI functionalities for PyQt.
        'PyQt6.QtWidgets',# Widgets for PyQt.
        'PyQt6.QtCore',   # Core non-GUI functionalities for PyQt.
        'appdirs',        # Used by `path_utils.py` to determine user-specific data/cache directories.
                          # Important for storing models and logs in standard locations.
        'huggingface_hub', # Core library for interacting with Hugging Face Hub, used by ModelManager.
        'huggingface_hub.utils', # Utilities for huggingface_hub.
        'huggingface_hub.file_download', # Specifically for model downloading.
        'sentence_transformers', # The main library for sentence embeddings.
                                 # PyInstaller might miss some of its dynamically loaded components.
        'transformers',   # Underlying library for sentence_transformers, handles model architectures.
        'transformers.models', # Specific submodules of transformers.
        'transformers.modeling_utils', # Often needed for model loading and utilities.
        'torch',          # PyTorch, a core dependency for sentence_transformers and transformers.
                          # PyInstaller needs to find all its components.
        'torch.nn.modules.module', # Sometimes specific torch modules are missed.
        # 'torchvision', # Example: Likely not needed for these types of models.
        # 'torchaudio',  # Example: Likely not needed.
        'sklearn.utils._typedefs', # Scikit-learn utilities, might be implicitly used.
        'sklearn.utils._heap',     # For scikit-learn's PriorityQueue.
        'sklearn.utils._sorting',
        'sklearn.utils._vector_sentinel',
        'jsonschema',     # For JSON schema validation, potentially used by huggingface_hub or other libs.
        'logging.handlers', # If using advanced logging handlers like RotatingFileHandler.
        'openpyxl',       # For reading/writing Excel files (e.g., the worksheet).
        'numpy',          # Core numerical library, dependency for many ML/data libraries.
        'pandas',         # If pandas is used directly or indirectly for data manipulation.
        'PIL.Image',      # Pillow library, if used for image handling (e.g., by PyQt for some icon formats).
        # Ensure all necessary sub-modules for sentence_transformers are included:
        'tokenizers',     # Used by transformers for text tokenization.
        'safetensors',    # For loading models stored in the .safetensors format.
        'packaging',      # Often a dependency of huggingface libs for version handling.
        'packaging.version',
        'packaging.specifiers',
        'filelock',       # Used by huggingface_hub for managing concurrent access to cached files.
        'certifi'         # Provides SSL certificates; crucial for HTTPS requests (e.g., model downloads).
                          # Often needs to be explicitly included for bundled apps.
    ],
    hookspath=[], # Paths to custom PyInstaller hook files, if any.
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [], # This is for collected_files, kept empty for one-file bundle generally
    name='IEC62443Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, # Whether to strip symbols from the executable (can sometimes make debugging harder).
    # `upx=True`: Enables UPX compression for the executable, making it smaller.
    # Can sometimes cause issues with antivirus software or on specific systems.
    # Set to `False` if the bundled application fails to start or behaves unexpectedly.
    upx=True, 
    upx_exclude=[], # List of files to exclude from UPX compression.
    runtime_tmpdir=None, # Specifies a temporary directory for one-file executables. `None` lets PyInstaller manage it.
    # `console=False`: Creates a windowed (GUI) application. No console window will appear when run.
    # Set to `True` for debugging console output or if it's a command-line application.
    console=False, 
    disable_windowed_traceback=False, # If True, tracebacks in windowed mode are not shown in a dialog.
    target_arch=None, # `None` means auto-detect architecture (e.g., x86_64). Can be set explicitly.
    codesign_identity=None, # For macOS code signing.
    entitlements_file=None, # For macOS entitlements.
    # `icon`: Path to an application icon file (.ico on Windows, .icns on macOS).
    # Example: icon='assets/app_icon.ico'
    # Currently `None`, so a default system icon will be used.
    icon=None 
)

# For one-folder bundle, you might use a COLLECT step instead of or after EXE:
# coll = COLLECT(exe,
#                a.binaries,
#                a.zipfiles,
#                a.datas,
#                strip=False,
#                upx=True,
#                upx_exclude=[],
#                name='IEC62443Tool_folder')
