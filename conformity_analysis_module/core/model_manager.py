# conformity_analysis_module/core/model_manager.py
# This module is responsible for managing the download, caching, and validation of
# sentence-transformer models used in the conformity analysis.
import json
from pathlib import Path
from huggingface_hub import snapshot_download
try:
    # Try the newer import path first (for huggingface_hub >= 0.20)
    from huggingface_hub.utils.errors import RepositoryNotFoundError
except ModuleNotFoundError:
    # Fallback to the older import path (for huggingface_hub < 0.20)
    from huggingface_hub.utils._errors import RepositoryNotFoundError

from conformity_analysis_module.config.config import Config
try:
    from conformity_analysis_module.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    # Basic config if project logger not found, for direct script run or testing
    if not logger.hasHandlers(): # Avoid adding multiple handlers if already configured
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ModelManager:
    """
    Manages the download, caching, and validation of sentence-transformer models.
    It uses a predefined list of supported models from the application's configuration
    and ensures that these models are available locally for the Analyzer.
    """
    def __init__(self):
        """
        Initializes the ModelManager.
        - Sets up the base directory for storing models from Config.
        - Loads the list of supported models from Config.
        - Ensures the base model directory exists, creating it if necessary.
        """
        self.models_base_dir = Config.MODEL_BASE_DIR
        self.supported_models = Config.SUPPORTED_MODELS
        # Ensure the main directory for storing all models exists.
        if not self.models_base_dir.exists():
            self.models_base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created models base directory: {self.models_base_dir}")

    def _get_model_info(self, model_name_or_hf_id: str) -> dict | None:
        """
        Retrieves the configuration details for a given model name or Hugging Face ID.
        This is a helper method to find a model's information from the `SUPPORTED_MODELS` list.

        Args:
            model_name_or_hf_id: The short name (e.g., "all-MiniLM-L12-v2") or
                                 the full Hugging Face identifier (e.g., "sentence-transformers/all-MiniLM-L12-v2").

        Returns:
            A dictionary containing the model's information if found, otherwise None.
        """
        for model_info in self.supported_models:
            # Check if the provided identifier matches either the short name or the HF ID.
            if model_info["name"] == model_name_or_hf_id or \
               model_info["hf_identifier"] == model_name_or_hf_id:
                return model_info
        logger.warning(f"Model info not found for '{model_name_or_hf_id}' in Config.SUPPORTED_MODELS.")
        return None

    def download_model(self, model_name: str) -> Path | None:
        """
        Downloads a specified model from Hugging Face Hub to a local cache directory.

        Args:
            model_name: The short name of the model to download (must be defined in Config.SUPPORTED_MODELS).

        Returns:
            A Path object to the local directory of the downloaded model if successful, otherwise None.
        """
        model_info = self._get_model_info(model_name)
        if not model_info:
            logger.error(f"Cannot download model: '{model_name}' is not defined in Config.SUPPORTED_MODELS.")
            return None

        hf_identifier = model_info["hf_identifier"] # Full Hugging Face ID for download.
        # Determine the specific local directory for this model using its short name.
        local_model_dir = Config.GET_SPECIFIC_MODEL_DIR(model_info["name"])

        # Although snapshot_download can create the directory, we log its creation explicitly if it doesn't exist.
        if not local_model_dir.exists():
            local_model_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created local directory for model '{model_name}': {local_model_dir}")

        logger.info(f"Attempting to download/update model '{hf_identifier}' to '{local_model_dir}'...")
        try:
            # Use huggingface_hub's snapshot_download to fetch the model files.
            snapshot_download(
                repo_id=hf_identifier,
                local_dir=local_model_dir,
                # local_dir_use_symlinks=False is generally safer for PyInstaller bundles,
                # ensuring actual files are copied rather than symlinks that might break.
                local_dir_use_symlinks=False,
                resume_download=True, # Allows resuming interrupted downloads.
            )
            logger.info(f"Model '{hf_identifier}' downloaded/updated successfully at '{local_model_dir}'.")
            return local_model_dir
        except RepositoryNotFoundError:
            # Specific error if the model ID doesn't exist on Hugging Face Hub.
            logger.error(f"Model repository not found on Hugging Face Hub: '{hf_identifier}'.")
        except Exception as e:
            # Catch-all for other potential errors during download (network issues, disk space, etc.).
            logger.error(f"An error occurred while downloading model '{hf_identifier}': {e}", exc_info=True)
        return None

    # This method is part of the ModelManager class.
    def is_model_valid(self, model_name: str) -> bool:
        """
        Validates if a cached model is likely usable by SentenceTransformer.
        Checks for the presence and integrity of 'config.json' and essential keys within it.
        This is a crucial step because a partially downloaded or corrupted model cache
        can lead to runtime errors when SentenceTransformer tries to load it.

        Args:
            model_name: The short name of the model (e.g., "all-MiniLM-L12-v2")
                        as defined in Config.SUPPORTED_MODELS.

        Returns:
            True if the model appears valid (config.json exists and contains 'model_type'), False otherwise.
        """
        model_info = self._get_model_info(model_name)
        if not model_info:
            logger.error(f"Cannot validate model: '{model_name}' is not defined in Config.SUPPORTED_MODELS.")
            return False

        # Get the expected local directory for the model.
        local_model_dir = Config.GET_SPECIFIC_MODEL_DIR(model_info["name"])

        # Check if the model directory itself exists.
        if not local_model_dir.exists():
            logger.warning(f"Validation failed: Model directory does not exist for '{model_name}' at {local_model_dir}.")
            return False

        # Check for the presence of 'config.json', a key file for transformer models.
        config_file_path = local_model_dir / "config.json"
        if not config_file_path.is_file():
            logger.warning(f"Validation failed for '{model_name}': 'config.json' is missing in {local_model_dir}.")
            return False

        # Try to load 'config.json' and check its content.
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Validation failed for '{model_name}': 'config.json' is not valid JSON.")
            return False
        except Exception as e:
            logger.warning(f"Validation failed for '{model_name}': Error reading 'config.json': {e}", exc_info=True)
            return False

        # Check for the 'model_type' key, which is essential for SentenceTransformer to identify the model architecture.
        # The absence of this key often indicates an incomplete or incorrect model download.
        if "model_type" not in config_data:
            logger.warning(f"Validation failed for '{model_name}': 'model_type' key missing in 'config.json'.")
            return False
        
        # Further checks could be added here (e.g., for 'pytorch_model.bin', 'tokenizer.json'),
        # but 'config.json' and 'model_type' are good primary indicators of a potentially valid cache.
        # The original problem this method solves was related to 'config.json' issues.
        # Example:
        # if not (local_model_dir / "pytorch_model.bin").is_file():
        #    logger.warning(f"Validation failed for '{model_name}': 'pytorch_model.bin' is missing.")
        #    return False

        logger.info(f"Model '{model_name}' at '{local_model_dir}' passed basic validation (config.json checks).")
        return True

    # This method is part of the ModelManager class.
    def ensure_model_available(self, model_name: str) -> Path | None:
        """
        Ensures a specific model is available and valid in the local cache.
        If the model is not found locally, or if it's found but deemed invalid
        (e.g., missing 'config.json'), it attempts to download (or re-download) it.
        This is the primary method clients should use to get a model path.

        Args:
            model_name: The short name of the model (e.g., "all-MiniLM-L12-v2")
                        as defined in Config.SUPPORTED_MODELS.

        Returns:
            A Path object to the valid local model directory if successful, otherwise None.
        """
        # First, verify if the requested model_name is among the supported models.
        model_info = self._get_model_info(model_name)
        if not model_info:
            # _get_model_info already logs a warning if model_name is not in SUPPORTED_MODELS.
            logger.error(f"Cannot ensure model availability: '{model_name}' is not a supported model name.")
            return None

        # Determine the expected local directory using the model's short name from model_info.
        local_model_dir = Config.GET_SPECIFIC_MODEL_DIR(model_info["name"])

        # Check if the model is already cached and valid.
        # The is_model_valid method handles logging for various invalid states.
        if self.is_model_valid(model_name):
            logger.info(f"Model '{model_name}' is already available and valid at '{local_model_dir}'.")
            return local_model_dir
        else:
            # If the model is not valid or not present, attempt to download it.
            # is_model_valid would have logged the reason for invalidity.
            logger.warning(f"Model '{model_name}' found invalid or incomplete. Attempting repair via (re)download.")
            # download_model will handle the download process and related logging.
            return self.download_model(model_name)

if __name__ == '__main__':
    # This section is for basic testing and demonstration if the script is run directly.
    # It's useful for verifying model downloading and validation logic independently.
    # Ensure logger is minimally configured if this script is run directly (e.g., for testing).
    if not logger.hasHandlers():
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Directly testing ModelManager...")
    manager = ModelManager() # Instantiate the manager.

    # Check if there are any models defined in the configuration to test with.
    if Config.SUPPORTED_MODELS:
        # Select the first model from the configuration for testing.
        test_model_name = Config.SUPPORTED_MODELS[0]["name"]
        logger.info(f"Attempting to download test model: {test_model_name} from {Config.SUPPORTED_MODELS[0]['hf_identifier']}")
        
        # Attempt to download the selected test model.
        downloaded_path = manager.download_model(test_model_name)
        if downloaded_path and downloaded_path.exists():
            logger.info(f"Test model '{test_model_name}' available at: {downloaded_path}")
            logger.info(f"Contents of {downloaded_path} (first 5 items):")
            # List a few items from the downloaded directory to confirm content.
            for i, item in enumerate(downloaded_path.iterdir()):
                if i < 5:
                    logger.info(f"  - {item.name}")
                else:
                    logger.info(f"  ... and more.")
                    break
            
            # Validate the downloaded model.
            logger.info(f"Validating the downloaded model: {test_model_name}")
            is_valid = manager.is_model_valid(test_model_name)
            if is_valid:
                logger.info(f"Model '{test_model_name}' is valid.")
            else:
                logger.error(f"Model '{test_model_name}' is NOT valid.")
        else:
            logger.error(f"Failed to download or find test model: {test_model_name}")
        
        # Test validation on a model name that is not in the supported list.
        # This checks the robustness of _get_model_info and is_model_valid.
        logger.info("Attempting to validate a non-supported model name 'non_existent_model_for_validation'...")
        manager.is_model_valid("non_existent_model_for_validation")

        # Test validation on a scenario where a model directory might exist but is empty or malformed.
        if Config.SUPPORTED_MODELS: # Re-check, as the outer 'if' might not have run if no models were configured.
            dummy_model_name_for_test = Config.SUPPORTED_MODELS[0]["name"] # Use a real model's name for structure.
            # Create a unique name for a dummy/broken model directory for testing purposes.
            dummy_broken_model_name = dummy_model_name_for_test + "_broken_test"
            dummy_model_dir_for_test = Config.GET_SPECIFIC_MODEL_DIR(dummy_broken_model_name)
            dummy_model_dir_for_test.mkdir(parents=True, exist_ok=True) # Create an empty directory.
            logger.info(f"Created dummy directory for validation test: {dummy_model_dir_for_test}")
            
            # To make `_get_model_info` recognize this dummy model for the test,
            # we temporarily add its info to the manager's list of supported models.
            # This is a testing hack; ideally, is_model_valid might accept a direct path
            # or be refactored for more direct unit testing of broken states.
            original_supported_models = manager.supported_models[:] # Create a shallow copy to restore later.
            manager.supported_models.append({"name": dummy_broken_model_name, "hf_identifier": "dummy/broken-test-model"})
            
            logger.info(f"Testing validation on an empty directory for model '{dummy_broken_model_name}'")
            is_dummy_valid = manager.is_model_valid(dummy_broken_model_name)
            if not is_dummy_valid:
                logger.info(f"Correctly identified '{dummy_broken_model_name}' as invalid (as expected for an empty dir).")
            else:
                logger.error(f"Incorrectly identified '{dummy_broken_model_name}' as valid.")
            
            # Clean up: Restore the original list of supported models.
            manager.supported_models = original_supported_models
            # Optionally, remove the created dummy directory:
            # import shutil; shutil.rmtree(dummy_model_dir_for_test)
        
        # Test the main public method 'ensure_model_available'.
        logger.info("\n--- Testing ensure_model_available ---")
        if Config.SUPPORTED_MODELS: # Check again, as the list might be empty.
            test_model_name_for_ensure = Config.SUPPORTED_MODELS[0]["name"]
            
            # Scenario 1: Ensure the model is available.
            # This should trigger download if not present, or validate if already cached.
            logger.info(f"Scenario 1: Ensuring '{test_model_name_for_ensure}' is available (first time or already valid).")
            model_path = manager.ensure_model_available(test_model_name_for_ensure)
            if model_path:
                logger.info(f"Model '{test_model_name_for_ensure}' is available at {model_path}. Validation passed or model (re)downloaded.")
            else:
                logger.error(f"Failed to ensure model '{test_model_name_for_ensure}' is available.")

            # Scenario 2: Simulate a broken model (e.g., missing config.json) and test if 'ensure_model_available' repairs it.
            # This relies on the model being available from Scenario 1 or a previous test run.
            logger.info(f"Scenario 2: Simulating a broken '{test_model_name_for_ensure}' and then ensuring its availability.")
            if model_path and model_path.exists(): # Check if model_path was successfully obtained.
                config_path = model_path / "config.json"
                if config_path.exists():
                    logger.info(f"Temporarily breaking model by renaming '{config_path.name}' in {model_path}")
                    broken_config_path = model_path / "config.json.broken_test_ensure" # Use a unique name
                    try:
                        config_path.rename(broken_config_path) # "Break" the model by renaming config.json.
                        
                        logger.info(f"Calling ensure_model_available for the 'broken' model '{test_model_name_for_ensure}'.")
                        # This should detect the model is invalid and trigger a re-download.
                        fixed_model_path = manager.ensure_model_available(test_model_name_for_ensure)
                        
                        if fixed_model_path and (fixed_model_path / "config.json").exists():
                            logger.info(f"Model '{test_model_name_for_ensure}' was successfully repaired/re-downloaded to {fixed_model_path}.")
                        else:
                            logger.error(f"Failed to repair/re-download model '{test_model_name_for_ensure}'.")
                        
                        # Clean up: Restore the renamed config file if it's still there and the main one isn't (e.g. if re-download failed).
                        # If re-download succeeded, the new config.json will be present.
                        if broken_config_path.exists() and not config_path.exists():
                           broken_config_path.rename(config_path)
                           logger.info(f"Restored '{config_path.name}' from '{broken_config_path.name}'.")
                        elif not broken_config_path.exists() and config_path.exists(): # Re-download successful
                            logger.info(f"Re-downloaded model replaced the broken config. '{config_path.name}' is present.")
                            if broken_config_path.exists(): # Should not happen if re-download worked over it
                                broken_config_path.unlink() # Clean up the .broken_test_ensure file
                                
                    except Exception as e:
                        logger.error(f"Error during simulation of broken model for ensure_model_available test: {e}", exc_info=True)
                        # Attempt to restore if broken_config_path exists from the failed attempt
                        if broken_config_path.exists() and not config_path.exists():
                           broken_config_path.rename(config_path)
                           logger.info(f"Restored '{config_path.name}' from '{broken_config_path.name}' after error.")
                else:
                    logger.warning(f"Cannot simulate broken model for ensure_model_available: config.json not found at {config_path} (model might not have been downloaded).")
            else:
                logger.warning(f"Cannot simulate broken model for ensure_model_available: path {model_path} does not exist (model might not have been downloaded initially).")
        else:
            logger.warning("No models defined in Config.SUPPORTED_MODELS to test ensure_model_available with.")
    else:
        logger.warning("No models defined in Config.SUPPORTED_MODELS to test with.")
