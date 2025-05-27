# conformity_analysis_module/core/model_manager.py
# This module is responsible for managing the download, caching, and validation of
# sentence-transformer models used in the conformity analysis.
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer # Ensure this import is present
# from huggingface_hub import snapshot_download # This line will be removed
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

    # (Inside ModelManager class)
    def download_model(self, model_name: str, progress_callback: callable = None) -> Path | None:
        """
        Downloads a model specified by its short name. This method uses SentenceTransformer
        to first load the model from Hugging Face (which handles the actual download to
        SentenceTransformer's own cache or uses an existing cache if the model was previously
        downloaded by SentenceTransformer for any reason). Then, it uses `model.save()`
        to copy the essential model files to the application's specific local cache directory
        (`local_model_dir`). The `model.save()` method is beneficial as it typically saves
        only the necessary components (e.g., configs, PyTorch model, tokenizer files),
        potentially resulting in a smaller storage footprint than the full Hugging Face cache.

        Args:
            model_name: The short name of the model (e.g., "all-MiniLM-L12-v2") as defined
                        in Config.SUPPORTED_MODELS.
            progress_callback: An optional callable that accepts a string message. It's used
                               to report progress and status updates (e.g., to a GUI dialog).
                               Messages include creation of cache directory, download initiation,
                               saving process, success, or error details.

        Returns:
            Path to the application-specific local model directory if download and save
            are successful, None otherwise.
        """
        model_info = self._get_model_info(model_name)
        if not model_info:
            err_msg = f"Cannot download model: '{model_name}' is not defined in Config.SUPPORTED_MODELS."
            logger.error(err_msg)
            if progress_callback: # Notify callback about the failure.
                progress_callback(err_msg)
            return None

        hf_identifier = model_info["hf_identifier"] # Full Hugging Face ID for downloading.
        # Target directory within the application's managed cache.
        local_model_dir = Config.GET_SPECIFIC_MODEL_DIR(model_info["name"])

        # Ensure the target directory for our application's cache exists.
        if not local_model_dir.exists():
            local_model_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created local directory for model '{model_name}': {local_model_dir}")
            if progress_callback:
                progress_callback(f"Created cache directory: {local_model_dir}")
        
        msg_downloading = f"Downloading model '{hf_identifier}' via SentenceTransformer library..."
        logger.info(msg_downloading)
        if progress_callback: # Report download initiation.
            progress_callback(msg_downloading)

        try:
            # Step 1: Load the model using SentenceTransformer.
            # This will download the model from Hugging Face Hub to SentenceTransformer's
            # internal cache if not already present there, or use its existing cache.
            # This step ensures all necessary files are fetched from the Hub.
            model = SentenceTransformer(hf_identifier) 

            msg_saving = f"Saving model '{hf_identifier}' to application cache '{local_model_dir}'..."
            logger.info(msg_saving)
            if progress_callback: # Report that the model is now being saved to our specific location.
                progress_callback(msg_saving)
            
            # Step 2: Save the loaded model to our application-specific directory.
            # The `model.save()` method is designed to save only the essential files
            # needed to run the model (e.g., config files, model weights, tokenizer files),
            # which can be more disk-space efficient than copying the entire Hugging Face cache directory.
            model.save(str(local_model_dir))
            
            msg_success = f"Model '{hf_identifier}' downloaded and saved successfully to '{local_model_dir}'."
            logger.info(msg_success)
            if progress_callback: # Report successful completion.
                progress_callback(msg_success)
            return local_model_dir
            
        except RepositoryNotFoundError: # Specific error for non-existent models on HF Hub.
            err_msg = f"Model repository not found on Hugging Face Hub: '{hf_identifier}'."
            logger.error(err_msg)
            if progress_callback:
                progress_callback(err_msg)
        except Exception as e: # Catch other potential errors (network, disk space, etc.).
            err_msg = f"An error occurred while downloading/saving model '{hf_identifier}': {e}"
            logger.error(err_msg, exc_info=True)
            if progress_callback:
                progress_callback(f"{err_msg} - Check logs for details.")
        
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
    def ensure_model_available(self, model_name: str, progress_callback: callable = None) -> Path | None:
        """
        Ensures a specific model (defined by its short name) is available and valid in the
        application's local cache. This is the primary method other parts of the application
        should use to get a model path before attempting to load it.

        The process is:
        1. Check if the model is supported (defined in Config.SUPPORTED_MODELS).
        2. Check if the model is already locally cached and valid using `is_model_valid()`.
           - If valid, its local path is returned, and `progress_callback` is notified.
        3. If not valid or not present, attempt to download (or re-download) it using `download_model()`.
           - `download_model` itself uses `progress_callback` for detailed download status.
           - `progress_callback` is also notified that a repair/download is being attempted.

        Args:
            model_name: The short name of the model (e.g., "all-MiniLM-L12-v2").
            progress_callback: An optional callable for status updates. It's passed down
                               to `download_model` if a download is necessary.

        Returns:
            Path to the valid local model directory if successful, None otherwise.
        """
        model_info = self._get_model_info(model_name)
        if not model_info:
            err_msg = f"Cannot ensure model availability: '{model_name}' is not a supported model name."
            logger.error(err_msg)
            if progress_callback: # Notify callback about the failure to find model in config.
                progress_callback(err_msg)
            return None

        local_model_dir = Config.GET_SPECIFIC_MODEL_DIR(model_info["name"])

        if self.is_model_valid(model_name): # Check validity (and existence).
            msg_valid = f"Model '{model_name}' is already available and valid at '{local_model_dir}'."
            logger.info(msg_valid)
            if progress_callback: # Notify callback that model is ready.
                progress_callback(msg_valid)
            return local_model_dir
        else:
            # If model is not valid (or not found by is_model_valid), attempt download.
            # is_model_valid would have logged the specific reason for invalidity.
            msg_repair = f"Model '{model_name}' found invalid or incomplete. Attempting repair via (re)download."
            logger.warning(msg_repair)
            if progress_callback: # Notify callback about the download attempt.
                progress_callback(msg_repair)
            # Pass the progress_callback to download_model for detailed download progress.
            return self.download_model(model_name, progress_callback=progress_callback)

    # (Inside ModelManager class)
    def ensure_all_models_available(self, progress_callback: callable = None) -> bool:
        """
        Iterates through all models listed in `Config.SUPPORTED_MODELS` and ensures each
        one is available and valid in the local cache using `ensure_model_available`.
        This is useful for pre-downloading all models or for a startup check.

        Args:
            progress_callback: An optional callable for status updates. It's passed down
                               to `ensure_model_available` (and thus to `download_model`)
                               for each model being processed.

        Returns:
            True if all supported models are successfully made available and are valid,
            False if any model fails the process.
        """
        all_successful = True # Flag to track overall success.
        logger.info("Starting check for all supported models...")
        if progress_callback: # Notify callback about the start of the overall process.
            progress_callback("Starting check for all supported models...")

        for model_info in self.supported_models:
            model_name = model_info["name"]
            msg_checking = f"Processing model: {model_name} (ID: {model_info['hf_identifier']})"
            logger.info(msg_checking)
            if progress_callback: # Notify callback about which model is currently being processed.
                progress_callback(msg_checking)

            # Call ensure_model_available for each model. This method handles validation,
            # download if needed, and uses the progress_callback for its own detailed updates.
            if not self.ensure_model_available(model_name, progress_callback=progress_callback):
                # If ensure_model_available returns None, it means that model could not be
                # made available (either validation failed after attempts or download failed).
                err_msg = f"Failed to ensure model '{model_name}' is available. Check logs for details."
                logger.error(err_msg)
                # No specific progress_callback here as ensure_model_available (and download_model)
                # would have already reported the specific failure reason.
                all_successful = False # Mark that at least one model failed.
            else:
                # If ensure_model_available succeeded, it would have already called the progress_callback
                # with "Model '...' is already available and valid" or with download success messages.
                # We can add a summary message here if desired.
                if progress_callback:
                     progress_callback(f"Model '{model_name}' successfully processed and available.")


        final_msg = "All supported models check completed."
        if all_successful:
            final_msg += " All models are now available and valid."
        else:
            final_msg += " One or more models could not be made available. Please review messages above and logs."
        
        logger.info(final_msg)
        if progress_callback: # Notify callback about the overall result.
            progress_callback(final_msg)
            
        return all_successful

if __name__ == '__main__':
    # This section is for basic testing and demonstration if the script is run directly.
    # It's useful for verifying model downloading and validation logic independently.
    # Ensure logger is minimally configured if this script is run directly (e.g., for testing).
    if not logger.hasHandlers():
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Directly testing ModelManager...")
    manager = ModelManager() # Instantiate the manager.

    # (Inside if __name__ == '__main__' block)
    # ...
    def print_progress(message: str):
        print(f"Progress: {message}")

    # Check if there are any models defined in the configuration to test with.
    if Config.SUPPORTED_MODELS:
        # Select the first model from the configuration for testing.
        test_model_name = Config.SUPPORTED_MODELS[0]["name"]
        # logger.info(f"Attempting to download test model: {test_model_name} from {Config.SUPPORTED_MODELS[0]['hf_identifier']}")
        
        # Attempt to download the selected test model.
        # downloaded_path = manager.download_model(test_model_name)
        logger.info(f"Attempting to download test model: {test_model_name} with progress callback")
        downloaded_path = manager.download_model(test_model_name, progress_callback=print_progress)
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
            model_path = manager.ensure_model_available(test_model_name_for_ensure, progress_callback=print_progress)
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
                        fixed_model_path = manager.ensure_model_available(test_model_name_for_ensure, progress_callback=print_progress)
                        
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

        # (At the end of the if __name__ == '__main__' block)
        logger.info("\n--- Testing ensure_all_models_available ---")
        all_models_ready = manager.ensure_all_models_available(progress_callback=print_progress)
        if all_models_ready:
            logger.info("All supported models successfully ensured.")
        else:
            logger.error("Failed to ensure all supported models.")
    else:
        logger.warning("No models defined in Config.SUPPORTED_MODELS to test with.")
