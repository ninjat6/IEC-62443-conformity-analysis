# utils/logger.py
import logging
import os
from conformity_analysis_module.config import Config

Config.ensure_dir(Config.LOG_DIR)
logger = logging.getLogger("ConformityAnalysis")
logging.basicConfig(
    filename=os.path.join(Config.LOG_DIR, "conformity_analysis.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)