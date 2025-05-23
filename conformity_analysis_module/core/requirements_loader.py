# core/requirements_loader.py
import json
from conformity_analysis_module.utils.logger import logger
from conformity_analysis_module.config import Config

class RequirementsLoader:
    @staticmethod
    def load():
        try:
            with open(Config.REQUIREMENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"無法載入條款要求檔案: {e}")
            return {}