# core/analyzer.py
import os
import json
import re
from sentence_transformers import SentenceTransformer, util
from conformity_analysis_module.core.file_processor import FileProcessor
from conformity_analysis_module.core.vector_cache import get_vector_cache
from conformity_analysis_module.core.hybrid_retriever import HybridRetriever
from conformity_analysis_module.utils.logger import logger
from conformity_analysis_module.config import Config


class Analyzer:
    def __init__(self, model_name='models/all-MiniLM-L12-v2', use_cache=True,
                 use_hybrid=False, bm25_weight=0.3, sbert_weight=0.7):
        """
        初始化分析器

        Args:
            model_name: SBERT 模型名稱
            use_cache: 是否啟用向量快取
            use_hybrid: 是否使用混合檢索 (BM25 + SBERT)
            bm25_weight: BM25 權重 (use_hybrid=True 時有效)
            sbert_weight: SBERT 權重 (use_hybrid=True 時有效)
        """
        self.model = SentenceTransformer(model_name)
        self.sp_folders = {}  # 存儲SP子資料夾映射
        self.use_cache = use_cache
        self.cache = get_vector_cache() if use_cache else None
        self.use_hybrid = use_hybrid
        self.bm25_weight = bm25_weight
        self.sbert_weight = sbert_weight
        self.hybrid_retriever = None

        if use_hybrid:
            self.hybrid_retriever = HybridRetriever(
                self.model, bm25_weight, sbert_weight
            )
        
    def analyze(self, folder_path, requirements, threshold=0.65,
                progress_callback=None, cancelled_check=None):
        """
        執行符合性分析

        Args:
            folder_path: 分析資料夾路徑
            requirements: 條款字典
            threshold: 相似度閾值
            progress_callback: 進度回調函數 (current, total, stage_name)
            cancelled_check: 取消檢查函數，返回 True 表示已取消

        Returns:
            分析結果列表
        """
        results = []
        requirement_embeddings = {}

        def report_progress(current, total, stage):
            if progress_callback:
                progress_callback(current, total, stage)

        def is_cancelled():
            return cancelled_check() if cancelled_check else False

        # 階段 1: 掃描資料夾結構 (0-5%)
        report_progress(0, 100, "📂 掃描資料夾結構...")
        if is_cancelled():
            return []

        self._detect_sp_folders(folder_path)
        logger.info(f"偵測到的SP子資料夾: {list(self.sp_folders.keys())}")

        # 階段 2: 編碼條款向量 (5-15%)
        report_progress(5, 100, "📋 編碼條款向量...")
        if is_cancelled():
            return []

        total_reqs = len(requirements)
        for idx, (req_key, req_text) in enumerate(requirements.items()):
            if is_cancelled():
                return []
            try:
                requirement_embeddings[req_key] = self.model.encode(req_text, convert_to_tensor=True)
                progress = 5 + int(10 * (idx + 1) / total_reqs)
                report_progress(progress, 100, f"📋 編碼條款 ({idx + 1}/{total_reqs})")
            except Exception as e:
                logger.error(f"計算條款 {req_key} 向量時發生錯誤: {e}")

        # 階段 3: 統計需處理的檔案數量
        report_progress(15, 100, "📊 統計檔案數量...")
        requirements_by_sp = self._group_requirements_by_sp(requirements)

        # 計算總檔案數
        total_files = self._count_files(folder_path, requirements_by_sp)
        processed_files = 0

        # 針對每個SP組別，只處理對應資料夾中的文件 (15-90%)
        for sp_group, sp_requirements in requirements_by_sp.items():
            if sp_group in self.sp_folders:
                # 該SP有對應的資料夾
                sp_folder = self.sp_folders[sp_group]
                sp_folder_path = os.path.join(folder_path, sp_folder)
                logger.info(f"處理 {sp_group} 條款，使用資料夾 {sp_folder_path}")
                
                # 處理該SP資料夾下的所有文件
                sp_results, files_done = self._process_folder_for_sp(
                    sp_folder_path,
                    sp_requirements,
                    {k: requirement_embeddings[k] for k in sp_requirements if k in requirement_embeddings},
                    {k: requirements[k] for k in sp_requirements},
                    threshold,
                    lambda f: self._report_file_progress(
                        report_progress, processed_files + f, total_files
                    ),
                    is_cancelled
                )
                results.extend(sp_results)
                processed_files += files_done
            else:
                # 該SP沒有對應資料夾，從主資料夾處理
                logger.info(f"找不到 {sp_group} 對應的資料夾，從主資料夾處理")
                sp_requirements_dict = {key: requirements[key] for key in sp_requirements}
                sp_results, files_done = self._process_folder_without_sp(
                    folder_path,
                    sp_requirements_dict,
                    {k: requirement_embeddings[k] for k in sp_requirements if k in requirement_embeddings},
                    threshold,
                    lambda f: self._report_file_progress(
                        report_progress, processed_files + f, total_files
                    ),
                    is_cancelled
                )
                results.extend(sp_results)
                processed_files += files_done

        # 階段 4: 過濾與儲存結果 (90-100%)
        report_progress(90, 100, "✨ 過濾與儲存結果...")

        # 保存結果到JSON - 確保所有結果都是可序列化的
        with open(Config.ANALYSIS_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        # 輸出快取統計
        if self.use_cache and self.cache:
            stats = self.cache.get_stats()
            logger.info(f"快取統計: 命中 {stats['hits']} 次, 未命中 {stats['misses']} 次, 命中率 {stats['hit_rate']}")

        logger.info(f"分析完成，共找到 {len(results)} 筆符合結果")
        return results

    def _count_files(self, folder_path, requirements_by_sp):
        """計算需處理的檔案總數"""
        total = 0
        counted_folders = set()

        for sp_group in requirements_by_sp.keys():
            if sp_group in self.sp_folders:
                sp_folder_path = os.path.join(folder_path, self.sp_folders[sp_group])
                if sp_folder_path not in counted_folders:
                    counted_folders.add(sp_folder_path)
                    for root, _, files in os.walk(sp_folder_path):
                        for file in files:
                            ext = file.lower().split('.')[-1]
                            if ext in ['docx', 'xlsx', 'pdf']:
                                total += 1
            else:
                # 主資料夾（排除SP子資料夾）
                if folder_path not in counted_folders:
                    counted_folders.add(folder_path)
                    for root, _, files in os.walk(folder_path):
                        skip = any(sp in root for sp in self.sp_folders.values())
                        if skip:
                            continue
                        for file in files:
                            ext = file.lower().split('.')[-1]
                            if ext in ['docx', 'xlsx', 'pdf']:
                                total += 1
        return max(total, 1)  # 避免除以零

    def _report_file_progress(self, report_progress, current_file, total_files):
        """回報檔案處理進度（15-90%範圍）"""
        progress = 15 + int(75 * current_file / total_files)
        report_progress(progress, 100, f"📄 處理檔案 ({current_file}/{total_files})")

    def _get_embeddings_with_cache(self, file_path: str, snippets: list):
        """
        取得文件片段的向量，優先使用快取

        Args:
            file_path: 檔案路徑
            snippets: 文字片段列表

        Returns:
            向量 tensor
        """
        if self.use_cache and self.cache:
            # 嘗試從快取取得
            cached = self.cache.get(file_path)
            if cached is not None:
                cached_snippets = cached.get('snippets', [])
                # 驗證快取的片段與當前片段一致
                if cached_snippets == snippets:
                    import torch
                    vectors = cached['vectors']
                    # 轉回 tensor
                    if not isinstance(vectors, torch.Tensor):
                        vectors = torch.tensor(vectors)
                    return vectors

        # 快取未命中，重新計算
        embeddings = self.model.encode(snippets, convert_to_tensor=True)

        # 存入快取
        if self.use_cache and self.cache:
            self.cache.set(file_path, embeddings, snippets)

        return embeddings

    def _match_with_hybrid(self, req_key: str, req_text: str, snippets: list,
                           threshold: float, file_path: str) -> list:
        """
        使用混合檢索匹配條款與片段

        Args:
            req_key: 條款編號
            req_text: 條款文字
            snippets: 文字片段列表
            threshold: 相似度門檻
            file_path: 來源檔案路徑

        Returns:
            匹配結果列表
        """
        results = []

        # 建立片段索引
        self.hybrid_retriever.index(snippets)

        # 執行混合搜尋
        search_results = self.hybrid_retriever.search(
            req_text,
            top_k=len(snippets),
            threshold=threshold
        )

        for result in search_results:
            results.append({
                "requirement": req_key,
                "requirement_text": req_text,
                "snippet": result['document'],
                "similarity": result['score'],
                "sbert_score": result['sbert_score'],
                "bm25_score": result['bm25_score'],
                "source_file": file_path
            })

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
    
    def _process_folder_for_sp(self, folder_path, requirement_keys, req_embeddings,
                                req_texts, threshold, progress_callback=None, cancelled_check=None):
        """處理特定SP資料夾的文件"""
        results = []
        files_processed = 0

        def is_cancelled():
            return cancelled_check() if cancelled_check else False

        # 遍歷資料夾中的所有檔案
        for root, _, files in os.walk(folder_path):
            for file in files:
                if is_cancelled():
                    return results, files_processed

                file_path = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                if ext not in ['docx', 'xlsx', 'pdf']:
                    continue

                logger.info(f"處理檔案: {file_path}")
                snippets = FileProcessor.extract_text_snippets(file_path)

                files_processed += 1
                if progress_callback:
                    progress_callback(files_processed)

                if not snippets:
                    continue

                # 根據模式選擇處理方式
                if self.use_hybrid and self.hybrid_retriever:
                    # 混合檢索模式
                    for req_key in req_embeddings.keys():
                        try:
                            hybrid_results = self._match_with_hybrid(
                                req_key, req_texts[req_key], snippets, threshold, file_path
                            )
                            results.extend(hybrid_results)
                        except Exception as e:
                            logger.error(f"混合檢索時發生錯誤: {e}")
                else:
                    # 純語意檢索模式
                    try:
                        # 使用快取機制取得向量
                        snippet_embeddings = self._get_embeddings_with_cache(file_path, snippets)
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

        return results, files_processed
    
    def _process_folder_without_sp(self, folder_path, requirements, req_embeddings,
                                     threshold, progress_callback=None, cancelled_check=None):
        """當沒有找到對應SP資料夾時，從主資料夾處理"""
        results = []
        files_processed = 0

        def is_cancelled():
            return cancelled_check() if cancelled_check else False

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
                if is_cancelled():
                    return results, files_processed

                file_path = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                if ext not in ['docx', 'xlsx', 'pdf']:
                    continue

                logger.info(f"處理檔案: {file_path}")
                snippets = FileProcessor.extract_text_snippets(file_path)

                files_processed += 1
                if progress_callback:
                    progress_callback(files_processed)

                if not snippets:
                    continue

                # 根據模式選擇處理方式
                if self.use_hybrid and self.hybrid_retriever:
                    # 混合檢索模式
                    for req_key in req_embeddings.keys():
                        try:
                            hybrid_results = self._match_with_hybrid(
                                req_key, requirements[req_key], snippets, threshold, file_path
                            )
                            results.extend(hybrid_results)
                        except Exception as e:
                            logger.error(f"混合檢索時發生錯誤: {e}")
                else:
                    # 純語意檢索模式
                    try:
                        # 使用快取機制取得向量
                        snippet_embeddings = self._get_embeddings_with_cache(file_path, snippets)
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

        return results, files_processed