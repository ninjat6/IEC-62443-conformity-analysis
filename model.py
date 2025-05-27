# model.py
# This script serves as a developer utility. Its primary purpose is to facilitate
# the pre-downloading of all sentence-transformer models that are defined as supported
# in the application's configuration (`conformity_analysis_module.config.config.Config.SUPPORTED_MODELS`).
# Running this script ensures that all necessary models are cached locally, which can be
# useful for setting up a development environment or for preparing a deployment package
# where models should be included or readily available without requiring download on first run by end-users.

# It leverages the centralized ModelManager from the `conformity_analysis_module.core.model_manager`,
# which handles the actual logic for downloading, caching, and validating models.
# This script is not intended to be part of the main packaged application's GUI flow
# but rather as a standalone tool for developers.

import logging # Used for basic logging setup if the main application's logger isn't active.
from conformity_analysis_module.config.config import Config # To access the list of supported models.
from conformity_analysis_module.core.model_manager import ModelManager # The core class for model operations.

# Note: The previous, script-specific model download logic (like REQUIRED_MODELS list,
# download_model_if_needed, and ensure_models_are_downloaded functions that might have
# existed in older versions of this file) has been removed. All such functionality
# is now centralized within the ModelManager class, making this script a simple
# consumer of ModelManager.

if __name__ == '__main__':
    # This block executes only when the script is run directly (e.g., `python model.py`).
    
    # Sets up basic logging for this script execution. This is important because
    # ModelManager itself uses logging. If the main application's logger (which might
    # be more complex, e.g., writing to files) isn't initialized when this script runs,
    # this basicConfig ensures that messages from ModelManager (and this script)
    # are visible on the console.
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Get a specific logger instance for this script's own messages, distinct from ModelManager's logger if needed.
    logger = logging.getLogger(__name__) 

    def console_progress_callback(message: str):
        """
        A simple callback function to print progress messages to the console.
        This function is passed to ModelManager's methods that support progress reporting.
        It helps in monitoring the status of model downloads and checks when running this script.
        A distinct prefix "DOWNLOAD_SCRIPT_PROGRESS:" is used for messages from this callback
        to differentiate them from ModelManager's internal log messages if both are outputting
        to the same console.
        """
        logger.info(f"DOWNLOAD_SCRIPT_PROGRESS: {message}")

    logger.info("Starting developer script to ensure all models are downloaded...")
    
    # Instantiate the ModelManager. This object will be used to manage model operations.
    manager = ModelManager()
    
    # Call the `ensure_all_models_available` method of ModelManager.
    # This method iterates through all models defined in `Config.SUPPORTED_MODELS`,
    # checks if they are valid in the local cache, and downloads/repairs them if necessary.
    # The `console_progress_callback` is passed to provide real-time feedback on the console.
    all_models_ready = manager.ensure_all_models_available(progress_callback=console_progress_callback)
    
    # Report the overall result of the operation.
    if all_models_ready:
        logger.info("All supported models have been checked and are available in the local cache.")
    else:
        logger.error("One or more models could not be made available. Please check the logs above for specific error messages.")
    
    logger.info("Developer model download script finished.")