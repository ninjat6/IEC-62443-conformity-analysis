# IEC 62443-2-4 Conformity Analysis Tool

This tool assists in analyzing documents for conformity with the IEC 62443-2-4 standard. It uses sentence-transformer models to compare text snippets from input documents against the requirements specified in the standard.

## Features

*   Processes DOCX, XLSX, and PDF files.
*   Uses semantic similarity to find relevant text for each IEC 62443-2-4 requirement.
*   Allows selection of different sentence-transformer models.
*   Generates analysis results in JSON format.
*   Provides an option to fill an Excel worksheet based on the analysis results.
*   Responsive GUI built with PyQt6.
*   Handles model downloading and caching.

## Project Structure

(Key directories and files - this can be expanded)

```
.
├── main.py                             # Main application entry point
├── IEC62443Tool.spec                   # PyInstaller specification file
├── requirements.txt                    # Python dependencies
├── path_utils.py                       # Utilities for path management (cache, logs, etc.)
├── conformity_analysis_module/         # Core logic for conformity analysis
│   ├── __init__.py
│   ├── analyzer.py                     # Performs the text comparison and analysis
│   ├── config/
│   │   └── config.py                   # Application configuration (paths, models)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── file_processor.py           # Handles text extraction from files
│   │   ├── model_manager.py            # Manages downloading and caching of models
│   │   └── requirements_loader.py      # Loads IEC 62443-2-4 requirements
│   ├── data/
│   │   └── requirements_cn.json        # IEC 62443-2-4 requirements data
│   │   └── keywords.json               # Keywords for SP folder detection
│   ├── gui/
│   │   └── main_window.py              # Main application window UI
│   ├── template/
│   │   └── IEC62443_2_4d_2024-worksheet.xlsx # Template for results output
│   └── utils/
│       └── logger.py                   # Logging setup
├── file_search_module/                 # Module for file search UI components (if separate)
│   └── ...
└── resources/                          # Bundled resources like icons, templates (alternative location)
    └── ...
```

## Installation & Setup

(Instructions for setting up a development environment)

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application (Development)

```bash
python main.py
```

## Model Management in the Packaged Application

This section describes how the packaged application (e.g., `IEC62443Tool.exe`) handles the language models required for analysis.

**1. Initial Application Startup (Packaged `.exe`):**
When you run the packaged application for the first time, it will automatically attempt to download all supported sentence-transformer models listed in its configuration. This process occurs *before the main application window appears*. A progress dialog will be displayed to show the status of these downloads. This initial setup requires an active internet connection. If any model is already cached and valid, it will be skipped. If a cached model is found to be corrupted, it will be re-downloaded.

**2. Caching:**
Downloaded models are cached in a user-specific directory on your computer. This allows the application to access them quickly on subsequent uses without re-downloading. The typical cache locations are:
*   **Windows:** `C:\Users\<YourUser>\AppData\Local\CyberAI\IEC62443Tool\models`
*   **Linux:** `~/.local/share/CyberAI/IEC62443Tool/models`
*   **macOS:** `~/Library/Application Support/CyberAI/IEC62443Tool/models`
(Please replace `<YourUser>` with your actual username.) The `CyberAI\IEC62443Tool` part corresponds to the `APP_AUTHOR` and `APP_NAME` defined in the application's path utilities.

**3. Subsequent Runs & Offline Use:**
Once all models have been successfully downloaded and cached during the initial startup, the application will load them from this local storage for all analysis tasks. This means that after the initial setup, the application and its analysis features can be used offline, without an active internet connection, as long as the cached models remain valid.

**4. Model Repair:**
The application includes a validation check for cached models (specifically for `config.json`). If it detects that a model's core configuration file is missing or corrupted during the initial startup check (or when a model is specifically requested by the Analyzer if not pre-checked), it will attempt to re-download that model from the Hugging Face Hub to repair it. This repair process also requires an active internet connection and will be shown in the startup progress dialog.

**5. Storage Considerations:**
Sentence-transformer models can vary in size. Typically, each model might consume a few hundred megabytes of disk space (e.g., `all-MiniLM-L12-v2` is around 230MB, `paraphrase-multilingual-MiniLM-L12-v2` is around 470MB). Please ensure you have adequate free space in the cache directory location, as the application will attempt to download all supported models.

**6. Developer Pre-Caching Script:**
For developers, or for preparing an environment where initial online downloads by the packaged `.exe` are undesirable, all supported models can be pre-downloaded and cached by running the following script from the project root:
```bash
python model.py
```
This script uses the same `ModelManager` as the main application and will download all models defined in `Config.SUPPORTED_MODELS` to the correct local cache directory. Progress will be displayed in the console. Running this script before building the `.exe` or distributing the application can simplify the first-run experience for end-users if the models are pre-cached on their system or if the cache directory can be pre-populated.

## Building the Executable

This project uses PyInstaller to package the application into a single executable.

1.  **Ensure PyInstaller is installed:**
    ```bash
    pip install pyinstaller
    ```
2.  **Navigate to the project root directory.**
3.  **Run PyInstaller with the spec file:**
    ```bash
    pyinstaller IEC62443Tool.spec
    ```
    This will create a `dist` folder containing the executable (`IEC62443Tool.exe` on Windows or `IEC62443Tool` on Linux/macOS).

**Note on the `.spec` file:**
The `IEC62443Tool.spec` file is configured to:
*   Bundle `main.py` as the entry point.
*   Include necessary data files (like `requirements_cn.json`, `keywords.json`, and the Excel template) in the correct locations within the bundle.
*   Include UI icons.
*   List hidden imports that PyInstaller's static analysis might miss, which are crucial for libraries like `sentence_transformers`, `transformers`, `torch`, `PyQt6`, `huggingface_hub`, and `appdirs`.
*   Create a windowed (no-console) application.
*   Optionally use UPX for compression (if `upx=True` is set and UPX is available).

If you modify dependencies or add new data files, you might need to update the `hiddenimports` or `datas` sections in the `.spec` file accordingly.

## Logging

Log files are stored in a user-specific log directory:
*   Windows: `C:\Users\<YourUser>\AppData\Local\CyberAI\IEC62443Tool\Logs`
*   Linux: `~/.cache/CyberAI/IEC62443Tool/log` (or `~/.local/state/CyberAI/IEC62443Tool/log` depending on `appdirs` version and system)
*   macOS: `~/Library/Logs/CyberAI/IEC62443Tool`

Each run of the application creates a new timestamped log file.

## Contributing

(Contributions are welcome. Please follow standard fork-and-pull-request workflow.)

## License

(Specify your project's license, e.g., MIT, Apache 2.0)
```
