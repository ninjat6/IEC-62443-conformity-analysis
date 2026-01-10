# core/hybrid_retriever.py
"""
Hybrid RAG: 結合 BM25 (詞頻) 與 SBERT (語意) 的混合檢索機制
"""

import re
import math
from collections import Counter
from typing import List, Tuple, Dict, Optional
import numpy as np


class BM25:
    """
    BM25 (Best Matching 25) 演算法實作

    用於基於詞頻的文字相似度計算，
    作為語意搜尋的補充，提升關鍵詞匹配能力。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        初始化 BM25

        Args:
            k1: 詞頻飽和參數 (預設 1.5)
            b: 文件長度正規化參數 (預設 0.75)
        """
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_lens: List[int] = []
        self.avgdl: float = 0.0
        self.n_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """
        簡易分詞：支援中英文混合

        Args:
            text: 輸入文字

        Returns:
            分詞結果列表
        """
        # 將文字轉小寫
        text = text.lower()

        # 使用正則表達式分割，保留中文字符和英文單詞
        # 匹配：中文字符 | 英文單詞 | 數字
        tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+|[\d]+', text)

        # 過濾太短的 token
        tokens = [t for t in tokens if len(t) > 1 or '\u4e00' <= t <= '\u9fff']

        return tokens

    def fit(self, documents: List[str]) -> None:
        """
        建立 BM25 索引

        Args:
            documents: 文件列表
        """
        self.corpus = []
        self.doc_freqs = {}
        self.doc_lens = []

        # 分詞並計算文件頻率
        for doc in documents:
            tokens = self._tokenize(doc)
            self.corpus.append(tokens)
            self.doc_lens.append(len(tokens))

            # 計算每個詞在多少文件中出現
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.n_docs = len(documents)
        self.avgdl = sum(self.doc_lens) / self.n_docs if self.n_docs > 0 else 0

        # 計算 IDF
        self._calc_idf()

    def _calc_idf(self) -> None:
        """計算逆文件頻率 (IDF)"""
        for word, freq in self.doc_freqs.items():
            # 使用 Robertson-Sparck Jones IDF 公式
            idf = math.log((self.n_docs - freq + 0.5) / (freq + 0.5) + 1)
            self.idf[word] = idf

    def get_scores(self, query: str) -> np.ndarray:
        """
        計算查詢與所有文件的 BM25 分數

        Args:
            query: 查詢字串

        Returns:
            每個文件的 BM25 分數陣列
        """
        query_tokens = self._tokenize(query)
        scores = np.zeros(self.n_docs)

        for token in query_tokens:
            if token not in self.idf:
                continue

            idf = self.idf[token]

            for idx, doc_tokens in enumerate(self.corpus):
                if not doc_tokens:
                    continue

                # 計算詞頻
                tf = doc_tokens.count(token)
                doc_len = self.doc_lens[idx]

                # BM25 公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                scores[idx] += idf * numerator / denominator

        return scores

    def get_top_n(self, query: str, n: int = 10) -> List[Tuple[int, float]]:
        """
        取得前 N 個最相關的文件

        Args:
            query: 查詢字串
            n: 返回數量

        Returns:
            (文件索引, 分數) 的列表
        """
        scores = self.get_scores(query)
        top_indices = np.argsort(scores)[::-1][:n]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]


class HybridRetriever:
    """
    混合檢索器：結合 BM25 與 SBERT

    透過加權組合兩種檢索方式的分數，
    同時獲得關鍵詞匹配和語意理解的優勢。
    """

    def __init__(self, sbert_model, bm25_weight: float = 0.3, sbert_weight: float = 0.7):
        """
        初始化混合檢索器

        Args:
            sbert_model: SentenceTransformer 模型實例
            bm25_weight: BM25 分數權重 (預設 0.3)
            sbert_weight: SBERT 分數權重 (預設 0.7)
        """
        self.sbert_model = sbert_model
        self.bm25 = BM25()
        self.bm25_weight = bm25_weight
        self.sbert_weight = sbert_weight

        self.documents: List[str] = []
        self.document_embeddings = None

    def index(self, documents: List[str]) -> None:
        """
        建立文件索引

        Args:
            documents: 文件列表
        """
        self.documents = documents

        # 建立 BM25 索引
        self.bm25.fit(documents)

        # 建立 SBERT 向量索引
        if documents:
            self.document_embeddings = self.sbert_model.encode(
                documents,
                convert_to_tensor=True,
                show_progress_bar=False
            )

    def search(self, query: str, top_k: int = 10, threshold: float = 0.0) -> List[Dict]:
        """
        執行混合搜尋

        Args:
            query: 查詢字串
            top_k: 返回結果數量
            threshold: 分數門檻

        Returns:
            搜尋結果列表，每個元素包含:
            - index: 文件索引
            - document: 文件內容
            - score: 混合分數
            - bm25_score: BM25 分數
            - sbert_score: SBERT 分數
        """
        if not self.documents:
            return []

        # 計算 BM25 分數
        bm25_scores = self.bm25.get_scores(query)

        # 正規化 BM25 分數 (0-1)
        bm25_max = bm25_scores.max() if bm25_scores.max() > 0 else 1
        bm25_normalized = bm25_scores / bm25_max

        # 計算 SBERT 分數
        from sentence_transformers import util
        query_embedding = self.sbert_model.encode(query, convert_to_tensor=True)
        sbert_scores = util.cos_sim(query_embedding, self.document_embeddings)[0].cpu().numpy()

        # 組合分數
        hybrid_scores = (
            self.bm25_weight * bm25_normalized +
            self.sbert_weight * sbert_scores
        )

        # 排序並過濾
        indices = np.argsort(hybrid_scores)[::-1]

        results = []
        for idx in indices[:top_k]:
            score = float(hybrid_scores[idx])
            if score < threshold:
                continue

            results.append({
                'index': int(idx),
                'document': self.documents[idx],
                'score': score,
                'bm25_score': float(bm25_normalized[idx]),
                'sbert_score': float(sbert_scores[idx])
            })

        return results

    def search_batch(self, queries: List[str], top_k: int = 10,
                     threshold: float = 0.0) -> Dict[str, List[Dict]]:
        """
        批次搜尋

        Args:
            queries: 查詢列表
            top_k: 每個查詢返回的結果數量
            threshold: 分數門檻

        Returns:
            查詢結果字典 {query: results}
        """
        results = {}
        for query in queries:
            results[query] = self.search(query, top_k, threshold)
        return results
