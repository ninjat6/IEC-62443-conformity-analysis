# conformity_analysis_module/core/keyword_analyzer.py
import json
import re
from pathlib import Path
# Assuming path_utils.py is in the project root and accessible in PYTHONPATH
from path_utils import get_bundled_resource_path
from conformity_analysis_module.utils.logger import logger
# Config import removed as Config.ROOT_DIR is no longer used for default path

class KeywordAnalyzer:
    """
    關鍵詞分析器 - 分析證據內容中的關鍵詞匹配數量並識別引用文件
    """
    
    def __init__(self, keywords_file=None):
        # 設定關鍵詞檔案路徑
        if keywords_file is None:
            # Default path using get_bundled_resource_path
            self.keywords_file = get_bundled_resource_path("conformity_analysis_module/data/keywords.json")
        else:
            # If keywords_file is provided, assume it's an absolute path (string or Path object)
            self.keywords_file = Path(keywords_file)
        
        # 載入關鍵詞和同義詞
        self._load_keywords()
    
    def _load_keywords(self):
        """載入關鍵詞和同義詞定義"""
        try:
            if self.keywords_file.exists():
                with open(self.keywords_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.keywords = data.get('keywords', {})
                self.synonyms = data.get('synonyms', {})
            else:
                # 如果檔案不存在，使用空字典並記錄警告
                logger.warning(f"關鍵詞檔案 {self.keywords_file} 不存在")
                self.keywords = {}
                self.synonyms = {}
        except Exception as e:
            logger.error(f"載入關鍵詞檔案時發生錯誤: {e}")
            self.keywords = {}
            self.synonyms = {}
    
    def analyze(self, analysis_results, min_score=2):
        """
        分析結果中的關鍵詞匹配
        
        Args:
            analysis_results (list): 分析結果列表
            min_score (int): 最低分數閾值
            
        Returns:
            list: 增強的分析結果，按關鍵詞匹配分數降序排序
        """
        enhanced_results = []
        
        # 收集所有源文件，用於後續參考文件檢查
        all_source_files = []
        for result in analysis_results:
            if "source_file" in result and result["source_file"] not in all_source_files:
                all_source_files.append(result["source_file"])
        
        # 遍歷每個分析結果
        for result in analysis_results:
            requirement = result.get('requirement', '')
            snippet = result.get('snippet', '')
            
            # 獲取該條款的關鍵詞
            if requirement in self.keywords:
                keywords = self.keywords[requirement]
                
                # 計算關鍵詞分數
                matched_keywords, score = self._calculate_score(snippet, keywords)
                
                # 如果分數達到閾值，則保留並增強結果
                if score >= min_score:
                    enhanced_result = result.copy()
                    enhanced_result['keyword_score'] = score
                    enhanced_result['matched_keywords'] = matched_keywords
                    
                    # 識別引用的文件
                    enhanced_result['referenced_files'] = self.extract_referenced_files(
                        snippet, all_source_files)
                    
                    enhanced_results.append(enhanced_result)
        
        # 根據關鍵詞分數排序 (降序)
        enhanced_results.sort(key=lambda x: x.get('keyword_score', 0), reverse=True)
        
        return enhanced_results
    
    def _calculate_score(self, text, keywords):
        """
        計算文本中關鍵詞的匹配分數
        
        Args:
            text (str): 要分析的文本
            keywords (list): 關鍵詞列表
            
        Returns:
            tuple: (匹配的關鍵詞列表, 總分數)
        """
        score = 0
        matched_keywords = []
        processed_synonyms = set()  # 追蹤已處理的同義詞
        
        for keyword in keywords:
            # 檢查關鍵詞是否出現在文本中
            if re.search(rf'\b{keyword}\b', text, re.IGNORECASE) or keyword in text:
                # 檢查此關鍵詞是否有同義詞
                if keyword in self.synonyms:
                    # 將關鍵詞和其同義詞轉換為不可變集合，用於去重
                    synonym_group = frozenset([keyword] + self.synonyms[keyword])
                    
                    # 如果此同義詞組尚未處理過
                    if synonym_group not in processed_synonyms:
                        processed_synonyms.add(synonym_group)
                        score += 1  # 只加一分
                        matched_keywords.append(keyword)
                        
                        # 將所有出現在關鍵詞列表中的同義詞加入匹配列表
                        for synonym in self.synonyms[keyword]:
                            if synonym in keywords and synonym not in matched_keywords:
                                matched_keywords.append(synonym)
                else:
                    # 非同義詞，直接加分
                    score += 1
                    matched_keywords.append(keyword)
        
        return matched_keywords, score
    
    def extract_referenced_files(self, snippet, all_source_files):
        """
        從證據內容中提取引用的文件
        
        Args:
            snippet (str): 證據內容
            all_source_files (list): 所有源文件列表
            
        Returns:
            list: 引用的文件列表 (完整路徑)
        """
        referenced_files = []
        
        # 尋找【文件編號 文件名稱】格式的引用
        references = re.findall(r'【([^】]+)】', snippet)
        
        for ref in references:
            # 更寬鬆的匹配模式，允許編號後沒有空格和後續文字
            match = re.match(r'([A-Z]+-\d+-\d+)(?:[A-Za-z])?(?:\s+(.*))?', ref)
            if match:
                ref_code = match.group(1)  # 只取基本編號部分 (如 CS-2-03)
                print(f"找到引用: {ref}, 提取編號: {ref_code}")

                # 尋找匹配的源文件
                for source_file in all_source_files: # source_file is a string path
                    file_name = Path(source_file).name
                    file_name_without_ext = Path(file_name).stem # Use Path(file_name) as file_name is now just the name string
                    
                    # 從文件名中提取基本編號
                    file_match = re.search(r'([A-Z]+-\d+-\d+)[A-Za-z]?', file_name_without_ext)
                
                    if file_match:
                        file_code = file_match.group(1)
                        print(f"匹配檔案: {file_name}, 提取編號: {file_code}")

                        # 比較基本編號
                        if ref_code == file_code:
                            referenced_files.append(source_file)
                            break
        
        return referenced_files