from pathlib import Path # Ensure Path is imported if not already via path_utils
from sentence_transformers import SentenceTransformer
# path_utils.py is assumed to be in PYTHONPATH (e.g., project root)
from path_utils import get_specific_model_dir 
# get_models_base_dir is not strictly needed here if get_specific_model_dir creates parent dirs

REQUIRED_MODELS = [
    {"id": "sentence-transformers/all-MiniLM-L12-v2", "local_name": "all-MiniLM-L12-v2"},
    {"id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "local_name": "paraphrase-multilingual-MiniLM-L12-v2"},
]

def download_model_if_needed(model_id: str, local_name: str, progress_callback=None) -> bool:
    """
    Downloads a single model if it doesn't exist locally.
    
    Args:
        model_id (str): The Hugging Face model ID (e.g., 'sentence-transformers/all-MiniLM-L12-v2').
        local_name (str): The local directory name to save the model under (e.g., 'all-MiniLM-L12-v2').
        progress_callback (optional): A function to call with progress updates (receives a string message).

    Returns:
        bool: True if a download was attempted (successfully or not), False if the model already existed.
              Note: If download fails, an exception is raised.
    
    Raises:
        Exception: If there's an error during model download or saving.
    """
    model_path: Path = get_specific_model_dir(local_name) # get_specific_model_dir returns Path

    if not model_path.exists():
        msg_downloading = f"正在下載 {model_id} 模型至 {str(model_path)}..."
        print(msg_downloading)
        if progress_callback:
            progress_callback(msg_downloading)
        
        try:
            model = SentenceTransformer(model_id)
            # Ensure parent directories for model_path are created by get_specific_model_dir
            model.save(str(model_path)) # SentenceTransformer.save() expects a string path
            
            msg_saved = f"模型 {model_id} 已儲存至 {str(model_path)}"
            print(msg_saved)
            if progress_callback:
                progress_callback(msg_saved)
            return True # Download attempted and (presumably) succeeded
        except Exception as e:
            msg_error = f"下載或儲存模型 {model_id} 時發生錯誤: {e}"
            print(msg_error)
            if progress_callback:
                progress_callback(msg_error)
            raise # Re-raise the exception to signal failure to the caller
    else:
        msg_exists = f"模型 {local_name} 已存在於 {str(model_path)}"
        print(msg_exists)
        if progress_callback:
            progress_callback(msg_exists)
        return False # Model already exists, no download attempted

def ensure_models_are_downloaded(progress_callback=None):
    """
    Ensures all models defined in REQUIRED_MODELS are downloaded if they don't already exist.
    
    Args:
        progress_callback (optional): A function to call with progress updates.
    """
    all_models_ok = True
    for model_info in REQUIRED_MODELS:
        model_id = model_info["id"]
        local_name = model_info["local_name"]
        try:
            print(f"檢查模型: {local_name} (ID: {model_id})")
            if progress_callback:
                progress_callback(f"正在檢查模型: {local_name}...")
            
            download_model_if_needed(model_id, local_name, progress_callback)
            
            # Brief confirmation after check/download attempt for this model
            # (more detailed messages come from download_model_if_needed)
            if progress_callback:
                progress_callback(f"模型 {local_name} 檢查完畢。")

        except Exception as e:
            all_models_ok = False
            # Error message already printed by download_model_if_needed or its call
            # Additional context for this higher-level function
            err_msg = f"確保模型 {model_id} (本機名稱: {local_name}) 可用時發生嚴重錯誤: {e}"
            print(err_msg)
            if progress_callback:
                progress_callback(err_msg)
            # Depending on application policy, one might choose to stop here or continue.
            # For now, it continues with other models.
    
    if all_models_ok:
        final_msg = "所有必要模型均已檢查並準備就緒。"
        print(final_msg)
        if progress_callback:
            progress_callback(final_msg)
    else:
        final_msg = "部分模型未能成功下載或驗證，請檢查上述錯誤訊息。"
        print(final_msg)
        if progress_callback:
            progress_callback(final_msg)


if __name__ == '__main__':
    # Example of using a simple print function as a progress callback
    def console_progress_callback(message: str):
        print(f"MAIN_APP_PROGRESS: {message}")

    print("正在檢查並下載所有必要的模型...")
    ensure_models_are_downloaded(progress_callback=console_progress_callback)
    print("模型檢查流程完成。")