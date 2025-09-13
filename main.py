# main.py
import sys
# Ensure conformity_analysis_module is in the Python path
# This is typically handled by PyInstaller's pathex or running from project root in dev.
from conformity_analysis_module.main import ConformityAnalysis
from conformity_analysis_module.utils.logger import logger # For any root level logging if needed

def main():
    try:
        logger.info("Application starting via root main.py...")
        # This will now trigger model checks within ConformityAnalysis.__init__
        app_instance = ConformityAnalysis()
        app_instance.run()
    except RuntimeError as e:
        # Catch critical errors during ConformityAnalysis init (e.g., model loading failures)
        logger.critical(f"Critical application error during startup: {e}", exc_info=True)
        # If QApplication hasn't started, simple print. If it might have, a QMessageBox would be better
        # but requires QApplication to be instantiated. For now, this will log and exit.
        print(f"A critical error occurred: {e}. Please check the logs for more details.", file=sys.stderr)
        sys.exit(1) # Exit with an error code
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}. Please check the logs.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Setup basic logging here if the module logger isn't configured early enough
    # from conformity_analysis_module.utils.logger import setup_logging
    # setup_logging() # Call if you have a centralized setup function

    main()
