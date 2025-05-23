from file_search_module.ui.file_searcher import FileSearcher

class FileSearchApp(FileSearcher):
    """
    FileSearchApp 為整合所有功能的主要入口，
    其他程式只需引用此類別，即可啟動完整的文件搜尋工具。
    """
    def __init__(self):
        super().__init__()
