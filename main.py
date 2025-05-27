# main.py
import sys
from PyQt6.QtWidgets import QApplication
# Refactored to use fully qualified absolute path
from editors.excel_editor import ExcelEditor 

def main():
    app = QApplication(sys.argv)
    window = ExcelEditor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
