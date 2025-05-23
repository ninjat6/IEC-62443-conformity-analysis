# core/analyzer.py
import os
import json
import re
from sentence_transformers import SentenceTransformer, util
from conformity_analysis_module.core.file_processor import FileProcessor
from conformity_analysis_module.utils.logger import logger
from conformity_analysis_module.config import Config

class Analyzer:
    def __init__(self, model_name='models/all-MiniLM-L12-v2'):
        self.model = SentenceTransformer(model_name)
        self.sp_folders = {}  # 存儲SP子資料夾映射
        
    def analyze(self, folder_path, requirements, threshold=0.65):
        results = []
        requirement_embeddings = {}
        
        # 首先檢測資料夾結構
        self._detect_sp_folders(folder_path)
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
                sp_folder = self.sp_folders[sp_group]
                sp_folder_path = os.path.join(folder_path, sp_folder)
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
                    folder_path, 
                    sp_requirements_dict,
                    {k: requirement_embeddings[k] for k in sp_requirements if k in requirement_embeddings},
                    threshold)
                results.extend(sp_results)
        
        # 保存結果到JSON - 確保所有結果都是可序列化的
        with open(Config.ANALYSIS_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        logger.info(f"分析完成，共找到 {len(results)} 筆符合結果")
        return results
    
    def _detect_sp_folders(self, folder_path):
        """偵測資料夾中是否有SP.XX格式的子資料夾"""
        self.sp_folders = {}
        sp_pattern = re.compile(r'^SP\.(\d{2})$', re.IGNORECASE)
        
        # 列出主資料夾下的所有項目
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    # 檢查是否符合SP.XX格式
                    match = sp_pattern.match(item)
                    if match:
                        sp_number = match.group(1)
                        sp_key = f"SP.{sp_number}"
                        self.sp_folders[sp_key] = item
        except Exception as e:
            logger.error(f"偵測SP資料夾時發生錯誤: {e}")
    
    def _group_requirements_by_sp(self, requirements):
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
    
    def _process_folder_for_sp(self, folder_path, requirement_keys, req_embeddings, req_texts, threshold):
        """處理特定SP資料夾的文件"""
        results = []
        
        # 遍歷資料夾中的所有檔案
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                if ext not in ['docx', 'xlsx', 'pdf']:
                    continue
                
                logger.info(f"處理檔案: {file_path}")
                snippets = FileProcessor.extract_text_snippets(file_path)
                if not snippets:
                    continue
                
                try:
                    snippet_embeddings = self.model.encode(snippets, convert_to_tensor=True)
                except Exception as e:
                    logger.error(f"計算檔案 {file_path} 中片段向量時發生錯誤: {e}")
                    continue
                
                # 比對該SP組的所有條款
                for req_key, req_embedding in req_embeddings.items():
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
                                "source_file": file_path
                            })
        
        return results
    
    def _process_folder_without_sp(self, folder_path, requirements, req_embeddings, threshold):
        """當沒有找到對應SP資料夾時，從主資料夾處理"""
        results = []
        
        for root, _, files in os.walk(folder_path):
            # 跳過已知的SP子資料夾
            skip_folder = False
            for sp_folder in self.sp_folders.values():
                if sp_folder in root:
                    skip_folder = True
                    break
            
            if skip_folder:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                if ext not in ['docx', 'xlsx', 'pdf']:
                    continue
                
                logger.info(f"處理檔案: {file_path}")
                snippets = FileProcessor.extract_text_snippets(file_path)
                if not snippets:
                    continue
                
                try:
                    snippet_embeddings = self.model.encode(snippets, convert_to_tensor=True)
                except Exception as e:
                    logger.error(f"計算檔案 {file_path} 中片段向量時發生錯誤: {e}")
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
                                "source_file": file_path
                            })
        
        return results