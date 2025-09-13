# conformity_analysis_module/config/config.py
from pathlib import Path
# Assuming path_utils.py is in the project root and accessible in PYTHONPATH
from path_utils import get_log_dir, get_bundled_resource_path, get_cache_dir, get_reports_dir, get_models_base_dir, get_specific_model_dir

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

    # Model Management
    # MODEL_BASE_DIR defines the root directory where all sentence-transformer models
    # will be cached locally. This path is determined by `path_utils.get_models_base_dir()`,
    # which typically uses `appdirs` to find a user-specific, OS-appropriate cache directory.
    # For example, on Linux, this might be '~/.cache/IEC62443Tool/models'.
    MODEL_BASE_DIR = get_models_base_dir() 
    
    # GET_SPECIFIC_MODEL_DIR is a function (imported from path_utils) that, when called
    # with a model's short name (e.g., "all-MiniLM-L12-v2"), returns the full path
    # to the directory where that specific model's files are (or will be) stored.
    # This path is typically `MODEL_BASE_DIR / model_short_name`.
    GET_SPECIFIC_MODEL_DIR = get_specific_model_dir 

    # SUPPORTED_MODELS is a list of dictionaries, each defining a sentence-transformer model
    # that the application knows how to use.
    # - "name": (str) A short, unique internal name for the model. This is used by
    #             ModelManager to create the subdirectory for this model's cache
    #             (e.g., MODEL_BASE_DIR / "all-MiniLM-L12-v2"). It's also used as the
    #             identifier when requesting a model from ModelManager or Analyzer.
    # - "display_name": (str) A user-friendly name for the model, intended for display
    #                     in graphical user interfaces (e.g., a dropdown menu for model selection).
    # - "hf_identifier": (str) The full model identifier as used on the Hugging Face Hub
    #                      (e.g., "sentence-transformers/all-MiniLM-L12-v2"). This is used
    #                      by ModelManager to download the model files.
    SUPPORTED_MODELS = [
        {
            "name": "all-MiniLM-L12-v2", 
            "display_name": "🔤 all-MiniLM-L12-v2 (Default English)", 
            "hf_identifier": "sentence-transformers/all-MiniLM-L12-v2" 
        },
        {
            "name": "paraphrase-multilingual-MiniLM-L12-v2",
            "display_name": "🌐 paraphrase-multilingual-MiniLM-L12-v2 (Multilingual)",
            "hf_identifier": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        }
    ]

    @staticmethod
    def ensure_dir(directory: Path):
        # This method is now less critical if path_utils functions ensure dirs,
        # but can be kept for other uses or as a safeguard.
        directory.mkdir(parents=True, exist_ok=True)