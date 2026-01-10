# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IEC 62443-2-4 Conformity Analysis Tool - A PyQt6-based desktop application that performs automated compliance analysis of documents against the IEC 62443-2-4 industrial control system security standard using SBERT (Sentence-BERT) semantic similarity and BM25 keyword matching.

**Current Status:** 70-75% complete (Phases 0-3 implemented)

**Language Context:**
- Application UI and requirements are in **Chinese (Traditional/Simplified)**
- Requirements data files use Chinese text (`requirements_cn.json`)
- User-facing text is in Chinese
- Code comments and variable names are in English
- When modifying requirements or keywords, preserve Chinese character encoding (UTF-8)

## Quick Reference

| I need to... | Command / File |
|--------------|----------------|
| Run the app | `python main.py` |
| Run analysis only | `python -m conformity_analysis_module.main` |
| Download models | `python model.py` |
| Check logs | `log/conformity_analysis.log` |
| Clear cache | `rm -rf .vector_cache/` |
| Add requirement | `conformity_analysis_module/data/requirements_cn.json` |
| Add keywords | `conformity_analysis_module/data/keywords.json` |
| Modify analysis logic | `conformity_analysis_module/core/analyzer.py` |
| Change UI | `conformity_analysis_module/gui/main_window.py` |
| Adjust BM25/SBERT weights | `conformity_analysis_module/core/hybrid_retriever.py:45` |

## Before You Start

**Critical Rules:**
1. **Always read files before modifying** - Never propose changes to code you haven't read
2. **Test via GUI** - No unit tests exist; validate all changes through the application
3. **Preserve Chinese text** - Requirements and keywords files contain Chinese; maintain UTF-8 encoding
4. **Respect threading** - Never call analyzer on main thread (see Threading Model section)
5. **Clear vector cache** when debugging embedding issues: `rm -rf .vector_cache/`

**Entry Points:**
- `python main.py` - Full application (Excel editor + Analysis + File Search)
- `python -m conformity_analysis_module.main` - Analysis module only
- `python model.py` - Download/verify SBERT models

## Common Commands

### Setup and Installation
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download SBERT models (first-time setup, ~500MB)
python model.py
```

### Running the Application
```bash
# Launch main application (Excel Editor + Conformity Analysis)
python main.py

# Run conformity analysis module directly
python -m conformity_analysis_module.main
```

### Development and Debugging
```bash
# Check logs for debugging
cat log/conformity_analysis.log  # Unix
type log\conformity_analysis.log  # Windows

# Clear vector cache (forces re-embedding)
rm -rf .vector_cache/  # Unix
rmdir /s .vector_cache  # Windows

# Verify models downloaded
python model.py

# Check analysis results
cat analysis_results.json | jq '.[] | select(.similarity > 0.7)'  # Unix
```

## Architecture

### High-Level Structure

The application has **3 main functional areas**:

1. **Conformity Analysis Engine** (`conformity_analysis_module/`) - Semantic compliance analysis
2. **File Search Module** (`file_search_module/`) - Document keyword search
3. **Excel Editor** (`editors/excel_editor.py`) - Main entry point and JSON/Excel editing

### Core Analysis Flow

```
Document Files (DOCX/PDF/XLSX)
    ↓
FileProcessor (extracts text)
    ↓
Analyzer (SBERT embeddings + cosine similarity)
    ↓
VectorCache (caches embeddings with hash-based invalidation)
    ↓
HybridRetriever (optional: BM25 + SBERT weighted combination)
    ↓
KeywordAnalyzer (post-processing with synonyms)
    ↓
WorksheetUpdater (generates Excel conformity report)
```

### Key Components

#### Analysis Engine (`conformity_analysis_module/core/`)

- **`analyzer.py`**: Main analysis orchestrator
  - Uses `sentence-transformers` for semantic embeddings
  - Supports hybrid mode (BM25 + SBERT)
  - Multi-threaded analysis with progress callbacks
  - Cancellation support via `cancelled_check` callback

- **`file_processor.py`**: Document text extraction
  - DOCX: `python-docx` library
  - XLSX: `openpyxl` library
  - PDF: `PyPDF2` library
  - Encoding detection with `chardet`

- **`vector_cache.py`**: Performance optimization
  - Caches SBERT embeddings to `.vector_cache/` directory
  - File hash-based invalidation (detects content changes)
  - Singleton pattern via `get_vector_cache()`

- **`hybrid_retriever.py`**: Enhanced matching
  - BM25: Keyword-based scoring (k1=1.5, b=0.75)
  - SBERT: Semantic similarity
  - Default weights: 30% BM25, 70% SBERT
  - Handles Chinese/English tokenization

- **`requirements_loader.py`**: Loads IEC 62443-2-4 requirements
  - Source: `conformity_analysis_module/data/requirements_cn.json`
  - Format: `{"SP.01.01 BR": "requirement text", ...}`

- **`worksheet_updater.py`**: Excel report generation
  - Template: `resources/templates/IEC62443_2_4d_2024-worksheet.xlsx`
  - Populates conformity statements and evidence

#### GUI Layer (`conformity_analysis_module/gui/`)

- **`main_window.py`** (1856 lines - LARGE FILE)
  - Primary analysis UI
  - Uses `AnalysisThread` (QThread) for background processing
  - Progress tracking via `progress` signal (current, total, stage_name)
  - Features: folder selection, requirement tree, threshold slider, result filtering, dashboard

- **`theme_manager.py`**: Dark/light theme management
  - Singleton pattern
  - Auto-detects system theme (Windows Registry, macOS defaults)
  - Persists preference via `QSettings`

- **`result_filter_panel.py`**: Result filtering UI
  - Filters by: keyword search, chapter (SP.01-SP.12), similarity threshold
  - Sorting: by requirement, similarity (asc/desc), filename

- **`compliance_dashboard.py`**: Visual statistics
  - Stat cards: total requirements, matched, missing, avg similarity
  - Chapter progress bars with color coding

### Threading Model

**Critical:** Analysis runs on background thread to prevent UI freezing

```python
class AnalysisThread(QThread):
    progress = pyqtSignal(int, int, str)  # current, total, stage
    finished = pyqtSignal(list)           # results
    error = pyqtSignal(str)               # error message

    def run(self):
        results = self.analyzer.analyze(
            folder_path, requirements, threshold,
            progress_callback=lambda c, t, s: self.progress.emit(c, t, s),
            cancelled_check=self.is_cancelled
        )
        self.finished.emit(results)
```

**Connect signals in main window:**
- `progress` → update progress bar
- `finished` → display results and dashboard
- `error` → show error dialog

### Configuration System

All paths configured in `conformity_analysis_module/config/config.py`:
- **Requirements**: `data/requirements_cn.json` (Chinese requirement text)
- **Keywords**: `data/keywords.json` (Chinese keywords + synonyms)
- **Template**: `resources/templates/IEC62443_2_4d_2024-worksheet.xlsx`
- **Cache**: `.vector_cache/` (auto-created)
- **Logs**: `log/conformity_analysis.log`
- **Output**: `analysis_results.json`

Use `Config.ROOT_DIR` for all path operations. Never hardcode paths.

### Data Formats

#### Requirements JSON (`requirements_cn.json`)
```json
{
  "SP.01.01 BR": "服務提供商應建立一套可供資產擁有者驗證的流程...",
  "SP.01.01 RE(1)": "服務提供商應建立一套可供資產擁有者執行的流程...",
  ...
}
```

#### Keywords JSON (`keywords.json`)
```json
{
  "keywords": {
    "SP.01.01BR": ["資產擁有者", "人員", "要求", "規範", ...]
  },
  "synonyms": {
    "要求": ["規範", "規定"],
    "流程": ["程序", "過程"]
  }
}
```

#### Analysis Results (`analysis_results.json`)
```json
[
  {
    "requirement": "SP.01.01 BR",
    "requirement_text": "服務提供商應建立...",
    "snippet": "matched document snippet",
    "similarity": 0.85,
    "source_file": "/path/to/document.docx"
  },
  ...
]
```

## Common Development Tasks

### Testing Changes
Since no unit tests exist, validate changes by:
1. Run `python main.py`
2. Click "Conformity Analysis" button
3. Select test folder with sample DOCX/PDF/XLSX files
4. Run analysis with different thresholds (50%, 65%, 80%)
5. Verify results display correctly
6. Check `log/conformity_analysis.log` for errors

### Adding New Requirements
1. Edit `conformity_analysis_module/data/requirements_cn.json`
2. Add entry: `"SP.XX.YY ZZ": "中文要求文字..."`
3. Update `keywords.json` with relevant Chinese keywords
4. If adding new chapter (SP.13+), update:
   - `conformity_analysis_module/gui/main_window.py:169-174` - CHAPTERS constant
   - `conformity_analysis_module/gui/compliance_dashboard.py` - CHAPTERS list
   - `conformity_analysis_module/gui/result_filter_panel.py` - chapter filter combo

### Modifying Analysis Behavior

**Threshold logic:** `conformity_analysis_module/core/analyzer.py:314`
```python
def analyze(self, folder_path, requirements, threshold=0.65):
    # Modify threshold logic here
    matches = [r for r in results if r['similarity'] >= threshold]
```

**File format support:** `conformity_analysis_module/core/file_processor.py:85`
```python
def extract_text_from_file(self, file_path):
    ext = file_path.suffix.lower()

    # Add new format handler
    if ext == '.odt':
        return self._extract_from_odt(file_path)
```

**BM25/SBERT weights:** `conformity_analysis_module/core/hybrid_retriever.py:45`
```python
# Adjust weights (must sum to 1.0)
bm25_weight = 0.3
sbert_weight = 0.7
```

### Debugging Analysis Issues
```bash
# Enable detailed logging (if implemented)
export LOG_LEVEL=DEBUG  # Linux/macOS
set LOG_LEVEL=DEBUG     # Windows

# Clear vector cache (forces re-embedding)
rm -rf .vector_cache/

# Verify models downloaded
python model.py

# Check analysis results
cat analysis_results.json | jq '.[] | select(.similarity > 0.7)'
```

### UI Threading Rules (CRITICAL)

**Never** call analyzer directly from main thread - UI will freeze:

```python
# ❌ WRONG - blocks UI
results = self.analyzer.analyze(folder, reqs, threshold)

# ✅ CORRECT - use QThread
self.analysis_thread = AnalysisThread(self.analyzer, folder, reqs, threshold)
self.analysis_thread.finished.connect(self.on_analysis_finished)
self.analysis_thread.start()
```

### Signal/Slot Connections

Progress updates require 3-parameter signal:

```python
# In AnalysisThread
self.progress.emit(current_count, total_count, "Processing files...")

# In MainWindow
def on_analysis_progress(self, current, total, stage_name):
    self.progress_bar.setValue(current)
    self.progress_bar.setFormat(f"{stage_name} ({current}%)")
```

### Code Style Conventions
- Use type hints for public methods
- Keep Chinese text in data files, not hardcoded in Python
- Log in English, UI text in Chinese
- Prefer `pathlib.Path` over `os.path`

## What NOT to Do

1. **Don't add backwards-compatibility code** - No legacy versions to support; just update the code directly
2. **Don't create abstraction layers prematurely** - Keep it simple; the codebase is straightforward
3. **Don't refactor large files without asking** - `main_window.py` is 1856 lines but functional
4. **Don't add English requirements** - This tool is specifically for Chinese IEC 62443-2-4 implementation
5. **Don't commit vector cache** - `.vector_cache/` is in `.gitignore` for a reason
6. **Don't remove Win32 code** - Some users need Windows-specific DOCX section extraction
7. **Don't add type stubs for third-party libraries** - Not in scope
8. **Don't over-engineer** - Simple, working code is better than complex abstractions

## Important Implementation Details

### SBERT Model Selection

Two models are supported (downloaded via `model.py`):

1. **`all-MiniLM-L12-v2`**: Fast, English-optimized, lightweight (default)
2. **`paraphrase-multilingual-MiniLM-L12-v2`**: Better Chinese support, slower

Selection in GUI: `ConformityAnalysisWindow.model_combo`

### Similarity Threshold Presets

Default threshold: 0.65 (65%)

- **Strict (80%)**: High precision, fewer results
- **Standard (65%)**: Balanced (default)
- **Loose (50%)**: High recall, more noise
- **Custom**: User-defined via slider (30-90%)

### Vector Cache Mechanism

- **Location**: `.vector_cache/` directory
- **Index**: `index.json` maps file paths to cache entries
- **Cache key**: `{filename}_{file_hash}.pkl`
- **Invalidation**: File hash mismatch triggers re-embedding
- **Performance gain**: ~10x speedup on repeated analysis

Example cache entry:
```json
{
  "C:\\path\\to\\document.docx": {
    "cache_file": "document_abc123def.pkl",
    "file_hash": "abc123def456...",
    "timestamp": "2024-01-10T12:00:00"
  }
}
```

### Hybrid Retrieval Weights

When `use_hybrid=True` in Analyzer:

- **BM25 weight**: 0.3 (keyword matching importance)
- **SBERT weight**: 0.7 (semantic similarity importance)
- **Total score**: `(bm25_score × 0.3) + (sbert_score × 0.7)`

Adjust in `conformity_analysis_module/core/analyzer.py` or `hybrid_retriever.py:45`

### File Processing Limitations

- **DOCX**: Requires Win32 COM for section extraction (`pywin32` dependency)
- **PDF**: Text extraction only (no OCR for scanned PDFs)
- **XLSX**: Reads all sheets, concatenates cells
- **TXT**: UTF-8/GBK/GB2312 encoding detection

**Windows-only feature**: DOCX section extraction via `conformity_analysis_module/utils/docx_section_extractor.py`

### Known Limitations

**Testing:**
- No unit tests - validate changes manually through GUI
- No CI/CD pipeline

**Architecture:**
- `conformity_analysis_module/gui/main_window.py` is large (1856 lines) but functional - avoid refactoring without clear benefit
- No plugin system for custom analysis algorithms

**Cross-Platform:**
- DOCX section extraction requires Windows (pywin32 dependency)
- macOS and Linux: Use alternative document structure or skip section extraction

**Performance:**
- No log rotation - `log/conformity_analysis.log` can grow large
- First analysis slow - subsequent runs use vector cache (~10x speedup)

**Priority for improvements:**
1. Add basic unit tests for core modules (analyzer, file_processor)
2. Extract reusable components from main_window.py
3. Add progress/error recovery for long analyses

**Completed Improvements (Phases 0-3):**
- ✅ Hard-coded paths removed (now uses QSettings)
- ✅ UTF-16 encoding issue in requirements.txt fixed
- ✅ File processor consolidated (v1/v2/v3 merged)
- ✅ Vector caching implemented
- ✅ Determinate progress bar with file counting
- ✅ Analysis cancellation mechanism
- ✅ Hybrid RAG (BM25 + SBERT)
- ✅ Dark/light theme support (`Ctrl+T` to toggle)
- ✅ Result filtering and sorting
- ✅ Click-to-open source files
- ✅ Compliance dashboard with statistics
- ✅ Keyboard shortcuts

## Common Errors and Solutions

### `ModuleNotFoundError: No module named 'conformity_analysis_module'`
**Cause:** Running from wrong directory or PYTHONPATH not set
**Solution:**
```bash
cd IEC-62443-conformity-analysis  # Ensure in correct directory
python main.py  # Not python ../main.py
```

### Analysis hangs at "Processing files..."
**Cause:** Analyzer called on main thread
**Solution:** Check Threading Model section - must use AnalysisThread

### `UnicodeDecodeError` when loading requirements
**Cause:** File encoding changed from UTF-8
**Solution:** Ensure all JSON files are UTF-8 encoded
```bash
file -I conformity_analysis_module/data/requirements_cn.json
# Should show: charset=utf-8
```

### Vector cache grows very large
**Cause:** Many documents analyzed without cleanup
**Solution:** Safe to delete `.vector_cache/` - will regenerate
```bash
du -sh .vector_cache/  # Check size
rm -rf .vector_cache/  # Clear cache
```

### GUI doesn't update during analysis
**Cause:** Forgot to emit progress signals
**Solution:** Ensure `progress_callback` called in analysis loop

### Models not found or download fails
**Cause:** Network issues or incorrect model path
**Solution:**
```bash
python model.py  # Re-download models
# Check: models/ directory should contain subdirectories
```

### `ImportError: pywin32` on macOS/Linux
**Cause:** Windows-specific dependency in cross-platform code
**Solution:** DOCX section extraction is optional - code should handle ImportError gracefully

## File Locations Reference

| Component | File Path |
|-----------|-----------|
| Main entry point | `main.py` |
| Model downloader | `model.py` |
| Core analyzer | `conformity_analysis_module/core/analyzer.py` |
| Main analysis UI | `conformity_analysis_module/gui/main_window.py` |
| Requirements data | `conformity_analysis_module/data/requirements_cn.json` |
| Keywords data | `conformity_analysis_module/data/keywords.json` |
| Excel template | `resources/templates/IEC62443_2_4d_2024-worksheet.xlsx` |
| Vector cache | `.vector_cache/index.json` |
| Logs | `log/conformity_analysis.log` |
| Analysis output | `analysis_results.json` |

## Keyboard Shortcuts

Available in `ConformityAnalysisWindow`:

- **Ctrl+O**: Open folder for analysis
- **F5**: Start analysis
- **Escape**: Cancel running analysis
- **Ctrl+A**: Select all requirements
- **Ctrl+Shift+A**: Deselect all requirements
- **Ctrl+T**: Toggle dark/light theme
- **F1**: Show help dialog

## Dependencies

**Key dependencies** (see `requirements.txt` for complete list with versions):

**ML/NLP:** sentence-transformers, torch, transformers, scikit-learn
**GUI:** PyQt6, PyQt6-WebEngine
**Document Processing:** python-docx, openpyxl, PyPDF2, pywin32 (Windows only)
**Utilities:** chardet, numpy, lxml

Total: 63 packages

**Installation:**
```bash
pip install -r requirements.txt
python model.py  # Download SBERT models (~500MB)
```

## Platform-Specific Notes

### Windows
- Full functionality including DOCX section extraction via pywin32
- File paths use backslashes
- Open files via `os.startfile()`

### macOS
- DOCX section extraction unavailable (pywin32 not supported)
- Open files via `subprocess.run(['open', path])`

### Linux
- DOCX section extraction unavailable
- Open files via `subprocess.run(['xdg-open', path])`

## Performance Considerations

- **First analysis**: Slow (downloads models, generates embeddings)
- **Subsequent analysis**: ~10x faster (vector cache)
- **Large documents**: Progress bar tracks file-by-file processing
- **Memory usage**: ~500MB-2GB depending on model and document count
- **Cancellation**: Graceful via `cancelled_check()` polling in analysis loops

## Debugging Tips

1. **Check logs**: `log/conformity_analysis.log` contains detailed trace
2. **Verify cache**: `.vector_cache/index.json` shows cached files
3. **Clear cache**: Delete `.vector_cache/` to force re-embedding
4. **Model issues**: Re-run `python model.py` to re-download
5. **Encoding errors**: Check file encoding with `chardet` library
6. **Thread errors**: Ensure signals connected before `thread.start()`
7. **Chinese text issues**: Verify UTF-8 encoding in all data files

## References

- **Parent documentation**: See `../IEC62443-2-4_完整技術文件_v2.0.md` for technical analysis
- **Development phases**: See `../CLAUDE_CODE_開發指令.md` for phased tasks and verification
- **Expert review**: See `../IEC62443-2-4_專家評估意見_v1.0.md` for professional assessment
