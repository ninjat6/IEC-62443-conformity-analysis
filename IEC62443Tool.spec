# IEC62443Tool.spec
# 基於 requirements.txt 的實際依賴進行優化

import sys
sys.setrecursionlimit(5000) # Standard PyInstaller recursion limit increase

# Project root directory 
project_root = '.'

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[], 
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
    hiddenimports=[
        # PyQt6 GUI framework - 基於你的實際版本
        'PyQt6.sip',
        'PyQt6.QtSvg',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtWebEngineWidgets',  # 基於 PyQt6-WebEngine
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtPrintSupport',
        
        # Windows COM support (重要！用於 Word 文檔處理) - 基於 pywin32
        'win32com.client',
        'win32com.client.gencache',
        'pythoncom',
        'pywintypes',
        'win32api',
        'win32con',
        'win32gui',
        
        # File encoding detection (重要！日誌顯示使用了)
        'chardet',
        'chardet.universaldetector',
        
        # Document processing - 基於你的實際依賴
        'docx',               # python-docx 庫
        'docx.document',
        'docx.shared',
        'PyPDF2',             # PDF processing
        'PyPDF2.errors',
        'lxml',               # XML processing
        'lxml.etree',
        
        # Path and file utilities
        'appdirs',
        'pathlib',            # 雖然是標準庫，但明確包含
        
        # Machine Learning and NLP - 基於你的實際依賴
        'huggingface_hub',
        'huggingface_hub.utils',
        'huggingface_hub.file_download',
        'huggingface_hub.constants',
        'sentence_transformers',
        'sentence_transformers.util',
        'sentence_transformers.models',
        'transformers',
        'transformers.models',
        'transformers.modeling_utils',
        'transformers.tokenization_utils',
        'transformers.tokenization_utils_base',
        'transformers.utils',
        
        # PyTorch - 版本 2.6.0
        'torch',
        'torch.nn.modules.module',
        'torch._C',
        'torch.cuda',
        'torch.utils',
        
        # Tokenization - 版本 0.21.0
        'tokenizers',
        'tokenizers.implementations',
        'tokenizers.models',
        
        # Model serialization - 版本 0.5.2
        'safetensors',
        'safetensors.torch',
        
        # Scientific computing - 基於你的版本
        'numpy',              # 1.26.4
        'scipy',              # 1.11.4
        'scipy.spatial.distance',
        
        # Scikit-learn - 版本 1.4.2
        'sklearn.utils._typedefs',
        'sklearn.utils._heap',
        'sklearn.utils._sorting',
        'sklearn.utils._vector_sentinel',
        'sklearn.metrics.pairwise',
        
        # Excel/Office file processing - 基於 openpyxl 3.1.5
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'openpyxl.utils',
        'et_xmlfile',         # openpyxl 依賴
        
        # Image processing (for GUI icons) - 基於 Pillow 11.1.0
        'PIL.Image',
        'PIL.ImageQt',
        'PIL._imaging',
        
        # Validation and serialization - 基於你的依賴
        'yaml',               # PyYAML 6.0.2
        'yaml.loader',
        'yaml.dumper',
        
        # Networking and security - 基於你的版本
        'certifi',            # 2025.1.31
        'urllib3',            # 2.3.0
        'requests',           # 2.32.3
        'requests.adapters',
        
        # Utilities - 基於你的依賴
        'packaging',          # 24.2
        'packaging.version',
        'packaging.specifiers',
        'filelock',           # 3.17.0
        'tqdm',               # 4.67.1 - Progress bars
        'joblib',             # 1.4.2
        
        # Regex processing - 版本 2024.11.6
        'regex',
        
        # Template engine - Jinja2 3.1.5
        'jinja2',
        'jinja2.ext',
        'markupsafe',         # MarkupSafe 3.0.2
        
        # Logging
        'logging.handlers',
        
        # System utilities
        'threading',
        'concurrent.futures',
        'multiprocessing',
        
        # tkinter 相關（用於文件對話框）
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.constants',
        'tkinter.commondialog',
    ],
    hookspath=[], 
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型庫以減小文件大小
        'matplotlib',         # 沒在 requirements.txt 中，且不需要繪圖
        'pytest',            # 測試框架
        'IPython',           # Jupyter 相關
        'jupyter',
        'notebook',
        # 注意: 保留 tkinter (用戶有使用) 和 unittest (sklearn 需要)
        'doctest',           # 文檔測試可以排除
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],                       # 空的！改為 onedir 模式
    exclude_binaries=True,    # 關鍵！將二進制文件分離
    name='IEC62443Tool',
    debug=False,              # 發布版本設為 False
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # 建議先設為 False，避免防毒軟體誤報
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # GUI 應用程式
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None                 # 可以加入你的應用程式圖標
)

# 新增 COLLECT 階段 - 創建 onedir 輸出
coll = COLLECT(
    exe,
    a.binaries,               # 將二進制文件放在 _internal 文件夾
    a.zipfiles,               # 將 zip 文件分離
    a.datas,                  # 將數據文件分離
    strip=False,
    upx=False,                # 同樣建議關閉 UPX 壓縮
    upx_exclude=[],
    name='IEC62443Tool'       # 最終文件夾名稱
)