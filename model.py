from sentence_transformers import SentenceTransformer
import os

# 確保模型目錄存在
os.makedirs('models', exist_ok=True)

# 下載原有模型
if not os.path.exists('models/all-MiniLM-L12-v2'):
    print("正在下載 all-MiniLM-L12-v2 模型...")
    model1 = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
    model1.save('models/all-MiniLM-L12-v2')
    print("模型已儲存至 models/all-MiniLM-L12-v2")

# 下載新模型
if not os.path.exists('models/paraphrase-multilingual-MiniLM-L12-v2'):
    print("正在下載 paraphrase-multilingual-MiniLM-L12-v2 模型...")
    model2 = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    model2.save('models/paraphrase-multilingual-MiniLM-L12-v2')
    print("模型已儲存至 models/paraphrase-multilingual-MiniLM-L12-v2")