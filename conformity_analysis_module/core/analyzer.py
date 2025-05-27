# core/analyzer.py
import json
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from conformity_analysis_module.core.file_processor import FileProcessor
from conformity_analysis_module.utils.logger import logger
from conformity_analysis_module.config import Config
from .model_manager import ModelManager

class Analyzer:
    def __init__(self, model_identifier='all-MiniLM-L12-v2'):
        """
        Initializes the Analyzer with a specified sentence-transformer model.

        The initialization process involves:
        1. Instantiating a ModelManager.
        2. Using the ModelManager to ensure the specified `model_identifier` is available
           and valid in the local cache. The ModelManager will handle downloading or
           repairing the model if necessary.
        3. Loading the validated model path into a SentenceTransformer instance.
        4. If the model cannot be made available or loaded, a RuntimeError is raised,
           signaling a critical failure that the calling code (e.g., the GUI) must handle.

        Args:
            model_identifier (str): The short name of the model to be used for analysis.
                                    This identifier must correspond to one of the "name"
                                    fields in `Config.SUPPORTED_MODELS`.
                                    Defaults to 'all-MiniLM-L12-v2'.

        Raises:
            RuntimeError: If the specified model cannot be made available by ModelManager
                          (e.g., download fails, validation fails after download) or if
                          SentenceTransformer fails to load the model from the validated path.
                          This error indicates that the Analyzer cannot perform its duties
                          and should be handled by the calling code (e.g., by informing the
                          user that analysis cannot proceed).
        """
        self.model_manager = ModelManager() # Instantiate the manager responsible for model fetching and validation.
        
        # The `model_identifier` parameter is expected to be one of the short names
        # (e.g., "all-MiniLM-L12-v2") defined in `Config.SUPPORTED_MODELS`.
        logger.info(f"Initializing Analyzer with model identifier: {model_identifier}")
        
        # `ensure_model_available` checks local cache validity and downloads/updates if needed.
        # It returns the path to the valid model directory or None if it fails.
        valid_model_path = self.model_manager.ensure_model_available(model_identifier)

        if valid_model_path:
            logger.info(f"Loading SentenceTransformer model '{model_identifier}' from validated path: {valid_model_path}")
            try:
                # Dynamically import SentenceTransformer here to ensure it's only imported when needed
                # and to potentially catch import errors if the environment is severely broken,
                # though pip dependencies should handle this.
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(str(valid_model_path)) # Load the model.
                logger.info(f"Model '{model_identifier}' loaded successfully into Analyzer.")
            except Exception as e:
                # This is a critical failure: the model was validated by ModelManager,
                # but SentenceTransformer still failed to load it.
                logger.critical(f"CRITICAL: Failed to load SentenceTransformer model from '{valid_model_path}' even after validation/download. Error: {e}", exc_info=True)
                # Raising RuntimeError here is important because the Analyzer cannot function
                # without a model. The calling code (e.g., GUI) must catch this and handle it gracefully,
                # for instance, by disabling analysis features and notifying the user.
                raise RuntimeError(f"Failed to initialize SentenceTransformer model '{model_identifier}' after ensuring availability. Check logs.") from e
        else:
            # This is also a critical failure: ModelManager could not provide a valid model path.
            # This could be due to network issues, disk space problems, or the model being unsupported.
            logger.critical(f"CRITICAL: Model '{model_identifier}' could not be made available by ModelManager. Analyzer cannot function.")
            # Similar to the above, this RuntimeError must be handled by the caller.
            raise RuntimeError(f"Model '{model_identifier}' not available. Check logs for details (e.g., network issues, disk space, unsupported model).")
        
    def analyze(self, folder_path: str, requirements: dict, threshold: float = 0.65):
        base_path = Path(folder_path)
        results = []
        requirement_embeddings = {}
        
        # 首先檢測資料夾結構
        self._detect_sp_folders(base_path)
        logger.info(f"偵測到的SP子資料夾: {list(self.sp_folders.keys())}")
        
        # 對每個條款進行向量編碼
        for req_key, req_text in requirements.items():
            try:
                requirement_embeddings[req_key] = self.model.encode(req_text, convert_to_tensor=True)
            except Exception as e:
                logger.error(f"計算條款 {req_key} 向量時發生錯誤: {e}")
        
        # 根據條款項目分組處理
        requirements_by_sp = self._group_requirements_by_sp(requirements)
        
        # 針對每個SP組別，只處理對應資料夾中的文件
        for sp_group, sp_requirements in requirements_by_sp.items():
            if sp_group in self.sp_folders:
                # 該SP有對應的資料夾
                sp_folder_name = self.sp_folders[sp_group]
                sp_folder_path = base_path / sp_folder_name
                logger.info(f"處理 {sp_group} 條款，使用資料夾 {sp_folder_path}")
                
                # 處理該SP資料夾下的所有文件
                sp_results = self._process_folder_for_sp(
                    sp_folder_path, 
                    sp_requirements, 
                    {k: requirement_embeddings[k] for k in sp_requirements if k in requirement_embeddings},
                    {k: requirements[k] for k in sp_requirements},
                    threshold)
                results.extend(sp_results)
            else:
                # 該SP沒有對應資料夾，從主資料夾處理
                logger.info(f"找不到 {sp_group} 對應的資料夾，從主資料夾處理")
                sp_requirements_dict = {key: requirements[key] for key in sp_requirements}
                sp_results = self._process_folder_without_sp(
                    base_path, 
                    sp_requirements_dict,
                    {k: requirement_embeddings[k] for k in sp_requirements if k in requirement_embeddings},
                    threshold)
                results.extend(sp_results)
        
        # 保存結果到JSON - 確保所有結果都是可序列化的
        with Config.ANALYSIS_OUTPUT.open('w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        logger.info(f"分析完成，共找到 {len(results)} 筆符合結果")
        return results
    
    def _detect_sp_folders(self, base_path: Path):
        """偵測資料夾中是否有SP.XX格式的子資料夾"""
        self.sp_folders = {}
        sp_pattern = re.compile(r'^SP\.(\d{2})$', re.IGNORECASE)
        
        # 列出主資料夾下的所有項目
        try:
            for item_path in base_path.iterdir():
                if item_path.is_dir():
                    # 檢查是否符合SP.XX格式
                    match = sp_pattern.match(item_path.name)
                    if match:
                        sp_number = match.group(1)
                        sp_key = f"SP.{sp_number}"
                        self.sp_folders[sp_key] = item_path.name # Store only the name
        except Exception as e:
            logger.error(f"偵測SP資料夾時發生錯誤: {e}")
    
    def _group_requirements_by_sp(self, requirements: dict) -> dict:
        """將條款依SP分組"""
        requirements_by_sp = {}
        
        for req_key in requirements.keys():
            # 提取SP部分 (例如 SP.01.01BR -> SP.01)
            match = re.match(r'(SP\.\d{2})', req_key)
            if match:
                sp_group = match.group(1)
                if sp_group not in requirements_by_sp:
                    requirements_by_sp[sp_group] = []
                requirements_by_sp[sp_group].append(req_key)
        
        return requirements_by_sp
    
    def _process_folder_for_sp(self, folder_path: Path, requirement_keys: list, req_embeddings: dict, req_texts: dict, threshold: float):
        """處理特定SP資料夾的文件"""
        results = []
        
        # 遍歷資料夾中的所有檔案
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower().lstrip('.')
                if ext not in ['docx', 'xlsx', 'pdf']:
                    continue
                
                logger.info(f"處理檔案: {str(file_path)}")
                snippets = FileProcessor.extract_text_snippets(str(file_path))
                if not snippets:
                    continue
                
                try:
                    snippet_embeddings = self.model.encode(snippets, convert_to_tensor=True)
                except Exception as e:
                    logger.error(f"計算檔案 {str(file_path)} 中片段向量時發生錯誤: {e}")
                    continue
                
                # 比對該SP組的所有條款
                for req_key, req_embedding in req_embeddings.items():
                    if req_key not in requirement_keys: # Ensure we only process relevant keys for this SP
                        continue
                    try:
                        # 計算相似度並轉換為 numpy 數組
                        cosine_scores = util.cos_sim(req_embedding, snippet_embeddings)[0].cpu().numpy()
                    except Exception as e:
                        logger.error(f"計算相似度時發生錯誤: {e}")
                        continue
                    
                    # 篩選相似度達到閾值的片段
                    for idx, score in enumerate(cosine_scores):
                        if score >= threshold:
                            # 確保所有數據都是 JSON 可序列化的
                            results.append({
                                "requirement": req_key,
                                "requirement_text": req_texts[req_key],
                                "snippet": snippets[idx],
                                "similarity": float(score),  # 確保轉換為 Python float
                                "source_file": str(file_path)
                            })
        
        return results
    
    def _process_folder_without_sp(self, base_path: Path, requirements: dict, req_embeddings: dict, threshold: float):
        """當沒有找到對應SP資料夾時，從主資料夾處理"""
        results = []
        
        processed_sp_folder_names = set(self.sp_folders.values())

        for file_path in base_path.rglob('*'):
            if not file_path.is_file():
                continue

            # Check if the file is within any of the detected SP subfolders
            try:
                # Check if any part of the file's path relative to base_path is a processed SP folder name
                # e.g. if file_path is /base/SP.01/doc.docx, and SP.01 is a processed_sp_folder_name
                # then relative_parts will be ('SP.01', 'doc.docx')
                # and 'SP.01' is in processed_sp_folder_names
                relative_parts = file_path.relative_to(base_path).parts
                if any(part in processed_sp_folder_names for part in relative_parts[:-1]): # Check parent directories
                    continue
            except ValueError: # file_path is not under base_path, should not happen with rglob from base_path
                logger.warning(f"File {file_path} not relative to {base_path}, skipping SP folder check.")
                pass

            ext = file_path.suffix.lower().lstrip('.')
            if ext not in ['docx', 'xlsx', 'pdf']:
                continue
            
            logger.info(f"處理檔案 (主資料夾): {str(file_path)}")
            snippets = FileProcessor.extract_text_snippets(str(file_path))
            if not snippets:
                continue
            
            try:
                snippet_embeddings = self.model.encode(snippets, convert_to_tensor=True)
            except Exception as e:
                logger.error(f"計算檔案 {str(file_path)} 中片段向量時發生錯誤: {e}")
                continue
            
            for req_key, req_embedding in req_embeddings.items():                        
                try:
                    # 計算相似度並轉換為 numpy 數組
                    cosine_scores = util.cos_sim(req_embedding, snippet_embeddings)[0].cpu().numpy()
                except Exception as e:
                    logger.error(f"計算相似度時發生錯誤: {e}")
                    continue
                
                for idx, score in enumerate(cosine_scores):
                    if score >= threshold:
                        # 確保所有數據都是 JSON 可序列化的
                        results.append({
                            "requirement": req_key,
                            "requirement_text": requirements[req_key],
                            "snippet": snippets[idx],
                            "similarity": float(score),  # 確保轉換為 Python float
                            "source_file": str(file_path)
                        })
        
        return results
