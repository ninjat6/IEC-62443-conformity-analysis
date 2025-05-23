# main.py
import sys
from PyQt6.QtWidgets import QApplication
from editors.excel_editor import ExcelEditor

def main():
    app = QApplication(sys.argv)
    window = ExcelEditor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
