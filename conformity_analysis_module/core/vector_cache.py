# core/vector_cache.py
"""
向量快取機制：避免重複編碼相同文件，提升分析效能
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Optional, List, Any
from datetime import datetime

from conformity_analysis_module.utils.logger import logger


class VectorCache:
    """
    向量快取管理器

    功能：
    - 根據檔案內容雜湊快取向量
    - 檔案修改後自動失效
    - 支援持久化儲存
    """

    def __init__(self, cache_dir: str = None):
        """
        初始化快取管理器

        Args:
            cache_dir: 快取目錄路徑，預設為專案下的 .vector_cache
        """
        if cache_dir is None:
            # 預設放在專案根目錄下
            base_dir = Path(__file__).parent.parent.parent
            cache_dir = base_dir / ".vector_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()

        # 統計資訊
        self.hits = 0
        self.misses = 0

    def _load_index(self) -> dict:
        """載入快取索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"載入快取索引失敗: {e}")
                return {}
        return {}

    def _save_index(self) -> None:
        """儲存快取索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存快取索引失敗: {e}")

    def _get_file_hash(self, file_path: str) -> str:
        """
        計算檔案內容的 MD5 雜湊

        使用檔案大小 + 修改時間作為快速判斷，
        只有在需要驗證時才計算完整雜湊
        """
        try:
            stat = os.stat(file_path)
            # 使用檔案路徑 + 大小 + 修改時間作為快速雜湊
            quick_hash = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(quick_hash.encode()).hexdigest()
        except Exception as e:
            logger.error(f"計算檔案雜湊失敗 {file_path}: {e}")
            return ""

    def _get_cache_path(self, file_hash: str) -> Path:
        """取得快取檔案路徑"""
        return self.cache_dir / f"{file_hash}.pkl"

    def get(self, file_path: str) -> Optional[Any]:
        """
        取得快取的向量

        Args:
            file_path: 原始檔案路徑

        Returns:
            快取的向量資料，若無快取則返回 None
        """
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return None

        # 檢查索引
        if file_hash not in self.index:
            self.misses += 1
            return None

        # 檢查快取檔案是否存在
        cache_path = self._get_cache_path(file_hash)
        if not cache_path.exists():
            # 索引存在但快取檔案不存在，清理索引
            del self.index[file_hash]
            self._save_index()
            self.misses += 1
            return None

        # 載入快取
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            self.hits += 1
            logger.debug(f"快取命中: {file_path}")
            return data
        except Exception as e:
            logger.warning(f"載入快取失敗 {file_path}: {e}")
            self.misses += 1
            return None

    def set(self, file_path: str, vectors: Any, snippets: List[str] = None) -> None:
        """
        儲存向量到快取

        Args:
            file_path: 原始檔案路徑
            vectors: 向量資料 (tensor 或 numpy array)
            snippets: 對應的文字片段（可選）
        """
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return

        cache_path = self._get_cache_path(file_hash)

        try:
            # 將 tensor 轉換為 numpy 以便序列化
            if hasattr(vectors, 'cpu'):
                vectors = vectors.cpu().numpy()

            cache_data = {
                'vectors': vectors,
                'snippets': snippets,
                'file_path': file_path,
                'cached_at': datetime.now().isoformat()
            }

            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)

            # 更新索引
            self.index[file_hash] = {
                'file_path': file_path,
                'cached_at': cache_data['cached_at'],
                'snippet_count': len(snippets) if snippets else 0
            }
            self._save_index()

            logger.debug(f"已快取: {file_path}")

        except Exception as e:
            logger.error(f"儲存快取失敗 {file_path}: {e}")

    def invalidate(self, file_path: str) -> None:
        """
        使特定檔案的快取失效

        Args:
            file_path: 檔案路徑
        """
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return

        # 刪除快取檔案
        cache_path = self._get_cache_path(file_hash)
        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception as e:
                logger.error(f"刪除快取檔案失敗: {e}")

        # 從索引移除
        if file_hash in self.index:
            del self.index[file_hash]
            self._save_index()

        logger.debug(f"已失效快取: {file_path}")

    def clear(self) -> None:
        """清除所有快取"""
        try:
            # 刪除所有 .pkl 檔案
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()

            # 清空索引
            self.index = {}
            self._save_index()

            # 重設統計
            self.hits = 0
            self.misses = 0

            logger.info("已清除所有向量快取")

        except Exception as e:
            logger.error(f"清除快取失敗: {e}")

    def get_stats(self) -> dict:
        """取得快取統計資訊"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        # 計算快取大小
        cache_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.pkl"))

        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cached_files': len(self.index),
            'cache_size_mb': f"{cache_size / 1024 / 1024:.2f} MB"
        }

    def get_cached_files(self) -> List[str]:
        """取得所有已快取的檔案路徑"""
        return [info['file_path'] for info in self.index.values()]


# 全域快取實例（單例模式）
_global_cache: Optional[VectorCache] = None


def get_vector_cache() -> VectorCache:
    """取得全域快取實例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = VectorCache()
    return _global_cache
