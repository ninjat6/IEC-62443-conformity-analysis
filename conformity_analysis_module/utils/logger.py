# utils/logger.py
import logging
# path_utils.py is assumed to be in PYTHONPATH (e.g., project root)
from path_utils import get_log_file_path

# The get_log_file_path() function (via get_log_dir()) ensures the log directory exists.
# No need for Config.ensure_dir(Config.LOG_DIR) or direct Config import for path.

logger = logging.getLogger("ConformityAnalysis")

# Use the timestamped log file path from path_utils
log_file = get_log_file_path()

logging.basicConfig(
    filename=str(log_file), # Ensure path is a string
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Optionally, log the path of the current log file
logger.info(f"Logging to file: {log_file}")