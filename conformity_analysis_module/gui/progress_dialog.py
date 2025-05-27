# conformity_analysis_module/gui/progress_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QApplication, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

class ModelDownloadProgressDialog(QDialog):
    # Signal to request closing the dialog, can be emitted when process is done or failed
    request_close = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Download Progress")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        # Make it modal so the user can't interact with other (non-existent) windows
        self.setModal(True) 

        layout = QVBoxLayout(self)

        self.progress_text_edit = QTextEdit()
        self.progress_text_edit.setReadOnly(True)
        layout.addWidget(self.progress_text_edit)

        # Optional: A button to close if something goes wrong and we need user ack
        # For now, we'll close it programmatically.
        # self.close_button = QPushButton("Close")
        # self.close_button.clicked.connect(self.accept) # or self.reject
        # self.close_button.setEnabled(False) # Enable on error/completion
        # layout.addWidget(self.close_button)
        
        self.request_close.connect(self.accept) # Connect signal to accept (close)

    def update_progress(self, message: str):
        self.progress_text_edit.append(message)
        QApplication.processEvents() # Process events to keep UI responsive

    def log_message(self, message: str): # Alias for clarity if used from non-progress contexts
        self.update_progress(message)

    def mark_finished(self, success: bool):
        if success:
            self.progress_text_edit.append("\nAll models processed successfully.")
        else:
            self.progress_text_edit.append("\nSome models could not be processed. Please check logs for details.")
        # self.close_button.setEnabled(True) # If we had a manual close button
        # Optionally, auto-close after a delay or keep open until user clicks (if button added)
        # For now, emitting request_close to allow programmatic closing.
        self.request_close.emit()


if __name__ == '__main__':
    # Example usage for testing the dialog directly
    import sys
    app = QApplication(sys.argv)
    dialog = ModelDownloadProgressDialog()

    # Simulate progress updates
    dialog.update_progress("Starting download for model A...")
    dialog.update_progress("Model A downloaded.")
    dialog.update_progress("Starting download for model B...")
    dialog.update_progress("Model B downloaded.")
    dialog.mark_finished(True) # Will emit request_close, dialog.accept() is called

    # If using exec_() it would normally block here until dialog is accepted/rejected.
    # Since mark_finished calls self.accept() via signal, it would close.
    # dialog.exec() # For modal execution
    
    # For non-modal testing or if closed programmatically:
    dialog.show() 
    # In a real app, something external would call dialog.request_close.emit() or dialog.accept()
    # For this test, it closes due to mark_finished -> request_close.emit() -> self.accept()
    sys.exit(app.exec())
